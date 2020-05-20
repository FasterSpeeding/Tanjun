from __future__ import annotations

__all__ = []

import abc
import inspect
import re
import typing

from hikari import bases
from hikari import channels
from hikari import colors
from hikari import emojis
from hikari import errors as hikari_errors
from hikari import guilds
from hikari import intents
from hikari import messages
from hikari import users
from hikari.internal import helpers
from hikari.internal import more_collections


# pylint: disable=ungrouped-imports
if typing.TYPE_CHECKING:
    import enum as enum_

    from hikari.clients import components as components_

    from . import commands as commands_  # pylint: disable=cyclic-import
# pylint: enable=ungrouped-imports


def calculate_missing_flags(value: enum_.IntFlag, required: enum_.IntFlag) -> enum_.IntFlag:
    originenum_ = type(required)
    missing = originenum_(0)
    for flag in originenum_.__members__.values():
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
    def convert(self, ctx: commands_.Context, argument: str) -> typing.Any:  # Cache only
        ...

    def verify_intents(self, components: components_.Components) -> bool:
        failed = []
        for shard in components.shards.values():
            if shard.intents is not None and (self._required_intents & shard.intents) != self._required_intents:
                failed[shard.shard_id] = calculate_missing_flags(self._required_intents, shard.intents)
        if failed:
            message = (
                f"Missing intents required for {type(self).__name__} converter being used on shards. "
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

    def convert(self, _: commands_.Context, argument: str) -> typing.Any:
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

    def convert(self, _: commands_.Context, argument: str) -> bases.Snowflake:
        return self._match_id(argument)


class ChannelConverter(ChannelIDConverter, types=(channels.PartialChannel,)):
    def __init__(self):
        super().__init__(
            inheritable=True, missing_intents_default=ChannelIDConverter(), required_intents=intents.Intent.GUILDS,
        )

    def convert(self, ctx: commands_.Context, argument: str) -> channels.PartialChannel:
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


class GuildEmojiConverter(EmojiIDConverter, types=(emojis.KnownCustomEmoji,)):
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

    def convert(self, ctx: commands_.Context, argument: str) -> bases.Snowflake:
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

    def convert(self, ctx: commands_.Context, argument: str) -> users.User:
        if match := self._match_id(argument):
            return ctx.fabric.state_registry.get_mandatory_user_by_id(match)


class MemberConverter(UserConverter, types=(guilds.GuildMember,)):
    def convert(self, ctx: commands_.Context, argument: str) -> guilds.GuildMember:
        if not ctx.message.guild:
            raise ValueError("Cannot get a member from a DM channel.")  # TODO: better error and error

        if match := self._match_id(argument):
            return ctx.fabric.state_registry.get_mandatory_member_by_id(match, ctx.message.guild_id)


class MessageConverter(SnowflakeConverter, types=(messages.Message,)):
    def __init__(self) -> None:  # TODO: message cache checks?
        super().__init__(
            inheritable=False, missing_intents_default=SnowflakeConverter(), required_intents=intents.Intent(0)
        )

    def convert(self, ctx: commands_.Context, argument: str) -> messages.Message:
        message_id = super().convert(ctx, argument)
        return ctx.fabric.state_registry.get_mandatory_message_by_id(message_id, ctx.message.channel_id)
        #  TODO: state and error handling?
