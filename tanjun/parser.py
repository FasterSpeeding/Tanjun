from __future__ import annotations

__all__ = []

import abc
import inspect
import re
import shlex
import typing
import distutils.util

import attr
import click
from hikari import bases
from hikari import channels
from hikari import colors
from hikari import emojis
from hikari import errors as hikari_errors
from hikari import guilds
from hikari import intents
from hikari import messages
from hikari import users
from hikari.internal import conversions
from hikari.internal import helpers
from hikari.internal import more_collections


from tanjun import errors

# pylint: disable=ungrouped-imports
if typing.TYPE_CHECKING:
    import enum as _enum

    from hikari.clients import components as _components

    from tanjun import commands as _commands  # pylint: disable=cyclic-import
# pylint: enable=ungrouped-imports


def calculate_missing_flags(value: _enum.IntFlag, required: _enum.IntFlag) -> _enum.IntFlag:
    origin_enum = type(required)
    missing = origin_enum(0)
    for flag in origin_enum.__members__.values():
        if (flag & required) == flag and (flag & value) != flag:
            missing |= flag
    return missing


class AbstractConverter(abc.ABC):
    _converter_implementations: typing.MutableSequence[typing.Tuple[AbstractConverter, typing.Tuple[typing.Type, ...]]]
    inheritable: bool
    missing_intents_default: typing.Optional[AbstractConverter]
    _required_intents: intents.Intent

    def __init_subclass__(cls, **kwargs):
        types = kwargs.pop("types", more_collections.EMPTY_SEQUENCE)
        super().__init_subclass__(**kwargs)
        if not types:
            return

        if not hasattr(AbstractConverter, "_converter_implementations"):
            AbstractConverter._converter_implementations = []

        for base_type in types:
            if AbstractConverter.get_converter_from_name(base_type.__name__):
                #  get_from_name avoids it throwing errors on an inheritable overlapping with a non-inheritable
                raise RuntimeError(f"Type {base_type} already registered.")
            #  TODO: make sure no overlap between inheritables while allowing overlap between inheritable and non-inheritables
        # TODO: ditch heritability?

        AbstractConverter._converter_implementations.append((cls(), tuple(types)))
        # Prioritize non-inheritable converters over inheritable ones.
        AbstractConverter._converter_implementations.sort(key=lambda entry: entry[0].inheritable, reverse=False)

    @abc.abstractmethod
    def __init__(
        self,
        inheritable: bool,
        missing_intents_default: typing.Optional[AbstractConverter],
        required_intents: intents.Intent,
    ) -> None:
        self.inheritable = inheritable
        self.missing_intents_default = missing_intents_default  # TODO: get_converter_from_type?
        self._required_intents = required_intents

    def __call__(self, *args, **kwargs) -> typing.Any:
        return self.convert(*args, **kwargs)

    @abc.abstractmethod  # These shouldn't be making requests therefore there is no need for async.
    def convert(self, ctx: _commands.Context, argument: str) -> typing.Any:  # Cache only
        ...

    def verify_intents(self, components: _components.Components) -> bool:
        failed = []
        for shard in components.shards.values():
            if shard.intents is not None and (self._required_intents & shard.intents) != self._required_intents:
                failed[shard.shard_id] = calculate_missing_flags(self._required_intents, shard.intents)
        if failed:
            message = (
                f"Missing intents required for {self.__class__.__name__} converter being used on shards. "
                "This will default to pass-through or be ignored."
            )
            helpers.warning(message, category=hikari_errors.IntentWarning, stack_level=4)  # Todo: stack_level
            return False
        return True

    @classmethod
    def get_converter_from_type(cls, argument_type: typing.Type) -> typing.Optional[AbstractConverter]:
        for converter, types in cls._converter_implementations:
            if not converter.inheritable and argument_type not in types:
                continue
            if converter.inheritable and inspect.isclass(argument_type) and not issubclass(argument_type, types):
                continue

            return converter

    @classmethod
    def get_converter_from_name(cls, name: str) -> typing.Optional[AbstractConverter]:
        for converter, types in cls._converter_implementations:
            if any(base_type.__name__ == name for base_type in types):
                return converter


class ColorConverter(AbstractConverter, types=(colors.Color,)):
    def __init__(self):
        super().__init__(inheritable=False, missing_intents_default=None, required_intents=intents.Intent(0))

    def convert(self, _: _commands.Context, argument: str) -> typing.Any:
        values = argument.split(" ")
        if all(value.isdigit() for value in values):
            values = (int(value) for value in values)

        return colors.Color.of(*values)


class BaseIDConverter(AbstractConverter, abc.ABC):
    _id_regex: re.Pattern

    def __init__(
        self,
        compiled_regex: re.Pattern,
        inheritable: bool = True,
        missing_intents_default: typing.Optional[AbstractConverter] = None,
        required_intents: intents.Intent = intents.Intent(0),
    ) -> None:
        super().__init__(
            inheritable=inheritable, missing_intents_default=missing_intents_default, required_intents=required_intents
        )
        if not isinstance(compiled_regex, re.Pattern):
            raise TypeError(f"Expected a compiled re.Pattern for `compiled_regex` but got {compiled_regex}")
        self._id_regex = compiled_regex

    def _match_id(self, value: str) -> bases.Snowflake:
        if value.isdigit():
            return bases.Snowflake(value)
        if result := self._id_regex.findall(value):
            return bases.Snowflake(result[0])
        raise ValueError("Invalid mention or ID passed.")  # TODO: return None or raise ValueError here?


class ChannelIDConverter(BaseIDConverter):
    def __init__(
        self,
        compiled_regex: typing.Optional[re.Pattern] = None,
        inheritable: bool = True,
        missing_intents_default: typing.Optional[AbstractConverter] = None,
        required_intents: intents.Intent = intents.Intent(0),
    ) -> None:
        super().__init__(
            compiled_regex=compiled_regex if compiled_regex else re.compile(r"<#(\d+)>"),
            inheritable=inheritable,
            missing_intents_default=missing_intents_default,
            required_intents=required_intents,
        )

    def convert(self, _: _commands.Context, argument: str) -> bases.Snowflake:
        return self._match_id(argument)


class ChannelConverter(ChannelIDConverter, types=(channels.PartialChannel,)):
    def __init__(self):
        super().__init__(
            inheritable=True, missing_intents_default=ChannelIDConverter(), required_intents=intents.Intent.GUILDS,
        )

    def convert(self, ctx: _commands.Context, argument: str) -> channels.PartialChannel:
        if match := self._match_id(argument):
            return ctx.fabric.state_registry.get_mandatory_channel_by_id(match)  # TODO: cache


class EmojiIDConverter(BaseIDConverter):
    def __init__(
        self,
        compiled_regex: typing.Optional[re.Pattern] = None,
        inheritable: bool = True,
        missing_intents_default: typing.Optional[AbstractConverter] = None,
        required_intents: intents.Intent = intents.Intent(0),
    ) -> None:
        super().__init__(
            compiled_regex=compiled_regex if compiled_regex else re.compile(r"<a?:\w+:(\d+)>"),
            inheritable=inheritable,
            missing_intents_default=missing_intents_default,
            required_intents=required_intents,
        )


class GuildEmojiConverter(EmojiIDConverter, types=(emojis.GuildEmoji,)):
    ...


class SnowflakeConverter(BaseIDConverter, types=(bases.Snowflake,)):  # TODO: bases.Unique, ?
    def __init__(
        self,
        compiled_regex: typing.Optional[re.Pattern] = None,
        inheritable: bool = True,
        missing_intents_default: typing.Optional[AbstractConverter] = None,
        required_intents: intents.Intent = intents.Intent(0),
    ) -> None:
        super().__init__(
            compiled_regex=compiled_regex if compiled_regex else re.compile(r"<[@&?!#]{1,3}(\d+)>"),
            inheritable=inheritable,
            missing_intents_default=missing_intents_default,
            required_intents=required_intents,
        )

    def convert(self, ctx: _commands.Context, argument: str) -> bases.Snowflake:
        if match := self._match_id(argument):
            return match
        raise ValueError("Invalid mention or ID supplied.")


class UserConverter(BaseIDConverter, types=(users.User,)):
    def __init__(
        self,
        compiled_regex: typing.Optional[re.Pattern] = None,
        inheritable: bool = False,
        missing_intents_default: typing.Optional[AbstractConverter] = None,
        required_intents: intents.Intent = intents.Intent.GUILD_MEMBERS,
    ) -> None:  # TODO: Intent.GUILD_MEMBERS and/or intents.GUILD_PRESENCES?
        super().__init__(
            compiled_regex=compiled_regex if compiled_regex else re.compile(r"<@!?(\d+)>"),
            inheritable=inheritable,
            missing_intents_default=missing_intents_default or SnowflakeConverter(),  # TODO: user ID converter?
            required_intents=required_intents,
        )

    def convert(self, ctx: _commands.Context, argument: str) -> users.User:
        if match := self._match_id(argument):
            return ctx.fabric.state_registry.get_mandatory_user_by_id(match)


class MemberConverter(UserConverter, types=(guilds.GuildMember,)):
    def convert(self, ctx: _commands.Context, argument: str) -> guilds.GuildMember:
        if not ctx.message.guild:
            raise ValueError("Cannot get a member from a DM channel.")  # TODO: better error and error

        if match := self._match_id(argument):
            return ctx.fabric.state_registry.get_mandatory_member_by_id(match, ctx.message.guild_id)


class MessageConverter(SnowflakeConverter, types=(messages.Message,)):
    def __init__(self) -> None:  # TODO: message cache checks?
        super().__init__(
            inheritable=False, missing_intents_default=SnowflakeConverter(), required_intents=intents.Intent(0)
        )

    def convert(self, ctx: _commands.Context, argument: str) -> messages.Message:
        message_id = super().convert(ctx, argument)
        return ctx.fabric.state_registry.get_mandatory_message_by_id(message_id, ctx.message.channel_id)
        #  TODO: state and error handling?


# We override NoneType with None as typing wrappers will contain NoneType but generally we'll want to hand around the
# None singleton.
BUILTIN_OVERRIDES = {bool: distutils.util.strtobool, type(None): None}

SUPPORTED_TYPING_WRAPPERS = (typing.Union,)  # typing.Optional just resolves to typing.Union[type, NoneType]

POSITIONAL_TYPES = (
    inspect.Parameter.VAR_POSITIONAL,
    inspect.Parameter.POSITIONAL_ONLY,
)


@attr.attrs(init=True, kw_only=True, slots=False)
class AbstractParameter:
    converters: typing.Tuple[typing.Union[typing.Callable, AbstractConverter], ...] = attr.attr(factory=tuple)
    default: typing.Optional[typing.Any] = attr.attr(default=None)
    flags: typing.Mapping[str, typing.Any] = attr.attr(factory=dict)
    key: str = attr.attr()
    names: typing.Optional[typing.Tuple[str]] = attr.attr(default=None)

    @abc.abstractmethod
    def components_hook(self, ctx: _components.Components) -> None:
        ...

    @abc.abstractmethod
    def convert(self, ctx: _commands.Context, value: str) -> typing.Any:
        ...


NO_DEFAULT = object()


@attr.attrs(slots=True, init=False)
class Parameter(AbstractParameter):
    def __init__(
        self,
        key: str,
        *,
        names: typing.Optional[typing.Tuple[str]] = None,
        converters: typing.Optional[typing.Tuple[typing.Union[typing.Callable, AbstractConverter], ...]] = None,
        default: typing.Any = NO_DEFAULT,
        **flags: typing.Any,
    ):
        super().__init__(
            converters=converters or (), default=default, flags=flags, key=key, names=names,
        )
        # While it may be tempting to have validation here, parameter validation should be attached to the parser
        # implementation rather than the parameters themselves.

    def components_hook(self, components: _components.Components) -> None:
        converters: typing.Sequence[typing.Union[typing.Callable, AbstractConverter]] = []
        for converter in self.converters:
            if custom_converter := AbstractConverter.get_converter_from_type(converter):
                if custom_converter.verify_intents(components):
                    converters.append(custom_converter)
                elif custom_converter.missing_intents_default:
                    converters.append(custom_converter.missing_intents_default)
            else:
                converters.append(BUILTIN_OVERRIDES.get(converter, converter))
        self.converters = tuple(converters)

    def convert(self, ctx: _commands.Context, value: str) -> typing.Any:
        failed = []
        for converter in self.converters:
            try:
                #  TODO: use the function signature to work out if it requires ctx or not?
                if isinstance(converter, AbstractConverter):
                    return converter.convert(ctx, value)
                else:
                    return converter(value)  # TODO: converter.__expected_exceptions__?
            except ValueError as exc:  # TODO: more exceptions?
                failed.append(exc)
        if failed:
            raise errors.ConversionError(
                msg=f"Invalid value for argument '{self.key}'", parameter=self, origins=tuple(failed)
            ) from failed[0]
        return value

    @property
    def is_greedy(self) -> bool:
        return self.flags.get("greedy", False)


def parameter(key, *, cls: typing.Type[AbstractParameter] = Parameter, **kwargs):
    def decorator(func):
        if not hasattr(func, "__parameters__"):
            func.__parameters__ = {}
        func.__parameters__[key] = cls(**kwargs)
        return func

    return decorator


@attr.attrs(init=True, repr=False, slots=False, kw_only=True)
class AbstractCommandParser(abc.ABC):
    flags: typing.Mapping[str, typing.Any] = attr.attrib(factory=dict)
    parameters: typing.Tuple[AbstractParameter, ...] = attr.attrib(factory=dict)

    @abc.abstractmethod
    def components_hook(self, components: _components.Components) -> None:
        ...

    @abc.abstractmethod
    def parse(self, ctx: _commands.Context) -> typing.MutableMapping[str, typing.Any]:
        ...

    @abc.abstractmethod
    def set_parameters(self, parameters: typing.Sequence[AbstractParameter]) -> None:
        ...

    @abc.abstractmethod
    def set_parameters_from_annotations(self, func: typing.Callable) -> None:
        ...

    @abc.abstractmethod
    def trim_parameters(self, to_trim: int) -> None:
        """
        Trim parameters from our list, will usually be `1` to trim `context`
        or `2` to trim both the `self` and `context` arguments.

        Arguments:
            to_trim:
                The :class:`int` amount of parameters to trim.

        Raises:
            KeyError:
                If the `to_trim` passed is higher than the amount of known parameters.
        """

    @abc.abstractmethod
    def validate_signature(self, signature: inspect.Signature) -> None:
        ...


@attr.attrs(init=False, slots=True)
class CommandParser(AbstractCommandParser):
    _option_parser: typing.Optional[click.OptionParser] = attr.attrib()
    _shlex: shlex.shlex
    signature: inspect.Signature = attr.attrib()

    def __init__(
        self, func: typing.Callable[[...], typing.Coroutine[typing.Any, typing.Any, typing.Any]], **flags: typing.Any,
    ) -> None:
        super().__init__(parameters={}, flags=flags)
        self._option_parser = None
        self._shlex = shlex.shlex("", posix=True)
        self._shlex.commenters = ""
        self._shlex.whitespace = "\t\r\n "
        self._shlex.whitespace_split = True
        self.signature = conversions.resolve_signature(func)
        # Remove the `ctx` arg for now, `self` should be trimmed by the command object itself.
        self.trim_parameters(1)
        if hasattr(func, "__parameters__"):
            self.set_parameters(func.__parameters__)

    def components_hook(self, components: _components.Components) -> None:
        if not self.parameters and components.config.set_parameters_from_annotations:
            self.set_parameters_from_annotations(self.signature)
        for param in self.parameters:
            param.components_hook(components)

    def parse(
        self, ctx: _commands.Context
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.MutableMapping[str, typing.Any]]:
        args: typing.MutableSequence[typing.Any] = []
        kwargs: typing.MutableMapping[str, typing.Any] = {}
        # If we push an empty string to shlex then iterate over shlex, it'll try to get input from sys.stdin, causing
        # the client to hang.
        if ctx.content:
            self._shlex.push_source(ctx.content)
            self._shlex.state = " "
        try:
            values, arguments, _ = self._option_parser.parse_args(list(self._shlex) if ctx.content else [])
        # ValueError catches unclosed quote errors from shlex.
        except (click.exceptions.BadOptionUsage, ValueError) as exc:  # TODO: more errors?
            raise errors.ConversionError(msg=str(exc), origins=(exc,)) from exc  # TODO: better message?

        for param in self.parameters:
            kind = self.signature.parameters[param.key]
            # greedy and VAR_POSITIONAL should be exclusive anyway
            if param.flags.get("greedy", False):  # TODO: enforce greedy isn't empty resource.
                result = param.convert(ctx, " ".join(arguments))
                if kind in POSITIONAL_TYPES:
                    args.append(result)
                else:
                    kwargs[param.key] = result
                arguments = []
                continue

            # If we reach a VAR_POSITIONAL parameter then we want to consume all of the positional arguments.
            if kind is inspect.Parameter.VAR_POSITIONAL:
                args.extend(param.convert(ctx, value) for value in arguments)
                continue

            # VAR_POSITIONAL parameters should default to an empty tuple anyway.
            if (value := values.get(param.key)) is None and param.default is NO_DEFAULT:
                raise errors.ConversionError(msg=f"Missing required argument `{param.key}`", parameter=param)

            if value is None:
                value = param.default
            else:
                value = param.convert(ctx, value)

            if kind in POSITIONAL_TYPES:
                args.append(value)
            else:
                kwargs[param.key] = value
        return args, kwargs

    def set_parameters(self, parameters: typing.Sequence[AbstractParameter]) -> None:
        self.parameters = tuple(parameters)
        # We can't clear the parser so each time we have to just replace it.
        option_parser = click.OptionParser()
        # As this doesn't handle defaults, we have to do that ourselves.
        option_parser.ignore_unknown_options = True
        for param in parameters:
            self._validate_parameter(param)
            if param.default is NO_DEFAULT and not param.flags.get("greedy"):
                option_parser.add_argument(param.key)
            else:
                option_parser.add_option(param.names, param.key)
        self._option_parser = option_parser
        self.validate_signature(self.signature)

    def set_parameters_from_annotations(self, signature: inspect.Signature) -> None:
        greedy_name = self.flags.get("greedy")
        parameters = []
        if greedy_name and greedy_name not in signature.parameters:
            raise IndexError(f"Greedy name {greedy_name} not found in {signature}.")

        # We set the converter's bool flag to False until it gets resolved with components later on.
        for key, value in signature.parameters.items():
            if isinstance(value.annotation, str):
                raise ValueError(f"Cannot get parameters from a signature that includes forward reference annotations.")
            converters = ()
            # typing.wraps should convert None to NoneType.
            if origin := typing.get_origin(value.annotation):
                if origin not in SUPPORTED_TYPING_WRAPPERS:
                    raise ValueError(f"Typing wrapper `{origin}` is not supported by this parser.")
                converters = tuple(arg for arg in typing.get_args(value.annotation) if arg is not type(None))
            elif value.annotation not in (inspect.Parameter.empty, type(None)):
                converters = (value.annotation,)
            default = NO_DEFAULT if value.default is inspect.Parameter.empty else value.default
            greedy = greedy_name == key
            parameters.append(
                Parameter(
                    converters=converters,
                    default=default,
                    greedy=greedy,
                    key=key,
                    names=(f"--{key.replace('_', '-')}",) if default is not NO_DEFAULT or greedy else None,
                )
            )
        self.set_parameters(parameters)

    def trim_parameters(self, to_trim: int) -> None:
        parameters = list(self.signature.parameters.values())
        try:
            self.signature = self.signature.replace(parameters=parameters[to_trim:])
        except KeyError:
            raise KeyError("Missing required parameter (likely `self` or `ctx`).")

        parameter_names = (param.name for param in parameters[:to_trim])
        new_parameters = None
        for param in self.parameters:
            if param.key in parameter_names:
                if new_parameters is None:
                    new_parameters = list(self.parameters)
                new_parameters.remove(param)

        if new_parameters is not None:
            self.parameters = tuple(new_parameters)

    def _validate_parameter(self, param: AbstractParameter) -> None:
        if param.default is not NO_DEFAULT or param.flags.get("greedy", False):
            if not all(name.startswith("-") for name in param.names):
                raise ValueError("Names for optional arguments must start with `-`")
            if not param.names:
                raise TypeError(f"Missing names for optional parameter {self}")
        elif param.names:
            raise TypeError("Required arguments cannot have assigned names.")

    def validate_signature(self, signature: inspect.Signature) -> None:
        if sum(param.flags.get("greedy", False) for param in self.parameters) > 1:
            raise ValueError(f"Too many greedy arguments set for {self.__class__.__name__}.")
            # TODO: better error message.
        contains_greedy = any(param.flags.get("greedy", False) for param in self.parameters)
        found_greedy = False

        for value in self.parameters:
            greedy = value.flags.get("greedy", False)
            if value.key not in signature.parameters:
                raise ValueError(f"{value.key} parameter not found in {signature}")
            kind = signature.parameters[value.key].kind
            if kind is inspect.Parameter.VAR_POSITIONAL and contains_greedy:
                raise TypeError("The greedy argument and *arg are mutually exclusive.")
            if found_greedy and kind in POSITIONAL_TYPES:
                raise TypeError("Positional arguments after a greedy argument aren't supported by this parser.")
            if kind is inspect.Parameter.VAR_KEYWORD:
                raise TypeError("**kwargs are not supported by this parser.")
            if value.default is NO_DEFAULT and kind is inspect.Parameter.KEYWORD_ONLY and not greedy:
                raise TypeError(f"Keyword only argument {value.key} needs a default.")
            # if value.default is not NO_DEFAULT and kind is inspect.Parameter.POSITIONAL_ONLY:
            #     raise TypeError(f"Positional only argument {value.key} cannot have a default.")
            found_greedy = greedy
