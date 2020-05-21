from __future__ import annotations

__all__ = []

import abc
import inspect
import shlex
import typing
import distutils.util

import attr
from hikari.internal import conversions

from . import converters as converters_
from . import errors

# pylint: disable=ungrouped-imports
if typing.TYPE_CHECKING:
    from hikari.clients import components as components_

    from . import commands as commands_  # pylint: disable=cyclic-import
# pylint: enable=ungrouped-imports


# We override NoneType with None as typing wrappers will contain NoneType but generally we'll want to hand around the
# None singleton.
BUILTIN_OVERRIDES = {bool: distutils.util.strtobool, type(None): None}

# typing.Optional just resolves to typing.Union[type, NoneType]
SUPPORTED_TYPING_WRAPPERS = (typing.Union,)  # TODO: support Sequence

POSITIONAL_TYPES = (
    inspect.Parameter.VAR_POSITIONAL,
    inspect.Parameter.POSITIONAL_ONLY,
)


@attr.attrs(init=True, kw_only=True, slots=False)
class AbstractParameter:
    converters: typing.Tuple[typing.Union[typing.Callable, converters_.AbstractConverter], ...] = attr.attr(
        factory=tuple
    )
    default: typing.Optional[typing.Any] = attr.attr(default=None)
    empty_default: typing.Optional[typing.Any] = attr.attr(default=None)
    flags: typing.Mapping[str, typing.Any] = attr.attr(factory=dict)
    key: str = attr.attr()
    names: typing.Optional[typing.Tuple[str]] = attr.attr(default=None)

    @abc.abstractmethod
    def components_hook(self, ctx: components_.Components) -> None:
        ...

    @abc.abstractmethod
    def convert(self, ctx: commands_.Context, value: str) -> typing.Any:
        ...


NO_DEFAULT = object()

EMPTY_FIELD = object()  # TODO: use this


@attr.attrs(slots=True, init=False)
class Parameter(AbstractParameter):
    def __init__(
        self,
        key: str,
        *,
        names: typing.Optional[typing.Tuple[str]] = None,
        converters: typing.Optional[
            typing.Tuple[typing.Union[typing.Callable, converters_.AbstractConverter], ...]
        ] = None,
        default: typing.Any = NO_DEFAULT,
        empty_default: typing.Any = NO_DEFAULT,
        **flags: typing.Any,
    ):
        super().__init__(
            converters=converters or (),
            default=default,
            empty_default=empty_default,
            flags=flags,
            key=key,
            names=names,
        )
        # While it may be tempting to have validation here, parameter validation should be attached to the parser
        # implementation rather than the parameters themselves.

    def components_hook(self, components: components_.Components) -> None:
        converters: typing.MutableSequence[typing.Union[typing.Callable, converters_.AbstractConverter]] = []
        for converter in self.converters:
            if custom_converter := converters_.AbstractConverter.get_converter_from_type(converter):
                if custom_converter.verify_intents(components):
                    converters.append(custom_converter)
                elif custom_converter.missing_intents_default:
                    converters.append(custom_converter.missing_intents_default)
            else:
                converters.append(BUILTIN_OVERRIDES.get(converter, converter))
        self.converters = tuple(converters)

    def convert(self, ctx: commands_.Context, value: str) -> typing.Any:
        if value in (self.default, self.empty_default):
            return value

        failed = []
        for converter in self.converters:
            try:
                #  TODO: use the function signature to work out if it requires ctx or not?
                if isinstance(converter, converters_.AbstractConverter):
                    return converter.convert(ctx, value)
                return converter(value)  # TODO: converter.__expected_exceptions__?
            except ValueError as exc:  # TODO: more exceptions?
                failed.append(exc)
        if failed:
            raise errors.ConversionError(
                msg=f"Invalid value for argument '{self.key}'", parameter=self, origins=tuple(failed)
            ) from failed[0]
        return value


def parameter(cls: typing.Type[AbstractParameter] = Parameter, **kwargs: typing.Any):
    def decorator(func):
        if not hasattr(func, "__parameters__"):
            func.__parameters__ = []
        func.__parameters__.append(cls(**kwargs))
        return func

    return decorator


@attr.attrs(init=True, repr=False, slots=False, kw_only=True)
class AbstractCommandParser(abc.ABC):
    flags: typing.Mapping[str, typing.Any] = attr.attrib(factory=dict)
    parameters: typing.Tuple[AbstractParameter, ...] = attr.attrib(factory=dict)

    @abc.abstractmethod
    def components_hook(self, components: components_.Components) -> None:
        ...

    @abc.abstractmethod
    def parse(
        self, ctx: commands_.Context
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.MutableMapping[str, typing.Any]]:
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
    _parameter_arguments: typing.Mapping[str]
    _parameter_options: typing.MutableMapping[str, AbstractParameter]  # TODO: consolidate the parse methods str to str?
    _shlex: shlex.shlex
    signature: inspect.Signature = attr.attrib()

    def __init__(
        self, func: typing.Callable[[...], typing.Coroutine[typing.Any, typing.Any, typing.Any]], **flags: typing.Any,
    ) -> None:
        super().__init__(parameters={}, flags=flags)
        self._parameter_options = {}
        self._shlex = shlex.shlex("", posix=True)
        self._shlex.commenters = ""
        self._shlex.whitespace = "\t\r\n "
        self._shlex.whitespace_split = True
        self.signature = conversions.resolve_signature(func)
        # Remove the `ctx` arg for now, `self` should be trimmed by the command object itself.
        self.trim_parameters(1)
        if hasattr(func, "__parameters__"):
            self.set_parameters(func.__parameters__)

    def components_hook(self, components: components_.Components) -> None:
        if not self.parameters and components.config.set_parameters_from_annotations:
            self.set_parameters_from_annotations(self.signature)
        for param in self.parameters:
            param.components_hook(components)

    def low_level_parse(  # TODO: consilidate or separate, should this just return "Empty field objects"
        self, args: typing.Sequence[str],  # TODO:  and raise ValueErrors while beings separate from the main parser
    ) -> typing.Tuple[typing.Sequence[str], typing.Mapping[str, typing.Optional[typing.Sequence[str]]]]:
        arguments = iter(self._parameter_arguments)
        key = None
        keyword_fields: typing.MutableMapping[str, typing.Optional[typing.MutableSequence[str]]] = {}
        positional_fields: typing.MutableSequence[str] = []
        for i, value in enumerate(args):
            if value.startswith("-"):
                if not key:
                    key = value
                    param = self._parameter_options.get(key)
                    output_key = param.key if param else key
                    continue

                if output_key in keyword_fields:  # TODO: duplicated logic
                    raise errors.ConversionError(
                        msg="Cannot pass a a valueless parameter multiple times.", parameter=param
                    )
                if param.empty_default is NO_DEFAULT:
                    raise errors.ConversionError(msg=f"Parameter {output_key} cannot be empty.", parameter=param)
                keyword_fields[output_key] = [param.empty_default]
                key = value
                continue

            if not key and arguments is not None:
                try:
                    key = output_key = next(arguments)
                except StopIteration:
                    arguments = None

            if not key:
                positional_fields.append(value)
                continue

            if output_key not in keyword_fields:
                keyword_fields[output_key] = []
            elif keyword_fields[output_key] is None:
                raise errors.ConversionError(msg="Cannot pass a a valueless parameter multiple times.", parameter=param)
            keyword_fields[output_key].append(value)
            key = None

        if key is not None:
            if output_key in keyword_fields:  # TODO: duplicated logic
                raise errors.ConversionError(msg="Cannot pass a a valueless parameter multiple times.", parameter=param)
            if param.empty_default is NO_DEFAULT:
                raise errors.ConversionError(f"Parameter {output_key} cannot be empty.", parameter=param)
            keyword_fields[output_key] = [param.empty_default]

        return positional_fields, keyword_fields

    def parse(
        self, ctx: commands_.Context
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        args: typing.MutableSequence[typing.Any] = []
        kwargs: typing.MutableMapping[str, typing.Any] = {}
        # If we push an empty string to shlex then iterate over shlex, it'll try to get input from sys.stdin, causing
        # the client to hang.
        if ctx.content:
            self._shlex.push_source(ctx.content)
            self._shlex.state = " "
        try:
            arguments, values = self.low_level_parse(list(self._shlex) if ctx.content else [])
        except ValueError as exc:  # TODO: more errors?
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
            if kind is inspect.Parameter.VAR_POSITIONAL:  # TODO: is this overriding parameter defined behaviour?
                args.extend(param.convert(ctx, value) for value in arguments)
                continue

            # VAR_POSITIONAL parameters should default to an empty tuple anyway.
            if (value := values.get(param.key)) is None and param.default is NO_DEFAULT:
                raise errors.ConversionError(msg=f"Missing required argument `{param.key}`", parameter=param)

            if value is None:
                value = param.default
            # elif value and value[0] is EMPTY_FIELD:  # TODO: keep this?
            #     if not param.empty_default:
            #         raise errors.ConversionError(f"Parameter {param.key} cannot be empty.", parameter=param)

            #     value = param.empty_default
            else:
                value = [param.convert(ctx, v) for v in value]
                multiple = param.flags.get("multiple", False)
                if len(value) > 1 and not multiple:  # TODO: this lol
                    raise errors.ConversionError(f"Cannot pass field {param.key} multiple times.", parameter=param)
                if not multiple:
                    value = value[0]

            if kind in POSITIONAL_TYPES:
                args.append(value)
            else:
                kwargs[param.key] = value
        return args, kwargs

    def set_parameters(self, parameters: typing.Sequence[AbstractParameter]) -> None:
        self.parameters = tuple(parameters)
        arguments = []
        options = {}
        for param in parameters:
            self._validate_parameter(param)
            if param.default is not NO_DEFAULT or param.flags.get("greedy"):
                for name in param.names:
                    options[name] = param
            else:
                arguments.append(param.key)
        self._parameter_arguments = tuple(arguments)
        self._parameter_options = options
        self.validate_signature(self.signature)

    def set_parameters_from_annotations(self, signature: inspect.Signature) -> None:
        greedy_name = self.flags.get("greedy")
        parameters = []
        if greedy_name and greedy_name not in signature.parameters:
            raise IndexError(f"Greedy name {greedy_name!r} not found in {signature}.")

        # We set the converter's bool flag to False until it gets resolved with components later on.
        for key, value in signature.parameters.items():
            if isinstance(value.annotation, str):
                raise ValueError("Cannot get parameters from a signature that includes forward reference annotations.")

            converters = ()
            # typing.wraps should convert None to NoneType.
            if origin := typing.get_origin(value.annotation):
                if origin not in SUPPORTED_TYPING_WRAPPERS:  # TODO: support Sequence like for parameter.multiple
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
            raise ValueError(f"Too many greedy arguments set for {type(self).__name__}.")
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
