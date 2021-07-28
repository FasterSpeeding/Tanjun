# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import annotations

__all__: list[str] = [
    "ChannelConverter",
    "ColorConverter",
    "EmojiConverter",
    "GuildConverter",
    "InviteConverter",
    "MemberConverter",
    "PresenceConverter",
    "RoleConverter",
    "SnowflakeConverter",
    "UserConverter",
    "VoiceStateConverter",
]

import abc
import datetime
import distutils.util
import inspect
import re
import typing
import urllib.parse
import warnings

import hikari

from . import errors

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from . import parsing
    from . import traits

_ValueT = typing.TypeVar("_ValueT")


class BaseConverter(typing.Generic[_ValueT], abc.ABC):
    __slots__: tuple[str, ...] = ()
    __implementations: set[type[BaseConverter[type[typing.Any]]]] = set()

    async def __call__(self, argument: str, ctx: traits.Context) -> _ValueT:
        return await self.convert(ctx, argument)

    def bind_client(self, client: traits.Client, /) -> None:
        cache_bound = self.cache_bound
        if cache_bound and not client.cache:
            warnings.warn(
                f"Registered converter {self!r} will always fail with a stateless client.",
                category=errors.StateWarning,
            )
            return

        if cache_bound and client.shards:  # TODO: alternative message when not state bound and wrong intents
            required_intents = self.intents
            if (required_intents & client.shards.intents) != required_intents:
                warnings.warn(
                    f"Registered converter {type(self).__name__!r} will not run as expected "
                    f"when {required_intents!r} intent(s) are not declared",
                    category=errors.StateWarning,
                )

    def bind_component(self, _: traits.Component, /) -> None:
        pass

    @classmethod
    def get_from_type(cls, type_: type[_ValueT], /) -> typing.Optional[type[BaseConverter[type[_ValueT]]]]:
        for converter in cls.__implementations:
            is_inheritable = converter.is_inheritable()
            if is_inheritable and issubclass(type_, converter.types()):
                return converter

            if not is_inheritable and type_ in converter.types():
                return converter

        return None

    @classmethod
    def implementations(cls) -> collections.MutableSet[type[BaseConverter[type[typing.Any]]]]:
        return cls.__implementations

    @property
    @abc.abstractmethod
    def cache_bound(self) -> bool:  # TODO: replace with cache components
        raise NotImplementedError

    @abc.abstractmethod
    async def convert(self, ctx: traits.Context, argument: str, /) -> _ValueT:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def intents(self) -> hikari.Intents:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def is_inheritable(cls) -> bool:  # TODO: will this ever actually work when true?
        raise NotImplementedError  # or do we want to assert specific idk channel types

    @classmethod
    @abc.abstractmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        raise NotImplementedError


class ChannelConverter(BaseConverter[hikari.GuildChannel]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.GuildChannel:
        if ctx.client.cache:
            channel_id = parse_channel_id(argument, message="No valid channel mention or ID  found")
            if channel := ctx.client.cache.get_guild_channel(channel_id):
                return channel

        raise ValueError("Couldn't find channel")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS

    @classmethod
    def is_inheritable(cls) -> bool:
        return True

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.GuildChannel,)


class ColorConverter(BaseConverter[hikari.Color]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return False

    async def convert(self, _: traits.Context, argument: str, /) -> typing.Any:
        values = argument.split(" ")
        if all(value.isdigit() for value in values):
            return hikari.Color.of(*map(int, values))

        return hikari.Color.of(*values)

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.NONE

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.Color,)


class EmojiConverter(BaseConverter[hikari.KnownCustomEmoji]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.KnownCustomEmoji:
        if ctx.client.cache:
            emoji_id = parse_emoji_id(argument, message="No valid emoji or emoji ID found")
            if emoji := ctx.client.cache.get_emoji(emoji_id):
                return emoji

        raise ValueError("Couldn't find emoji")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_EMOJIS

    @classmethod
    def is_inheritable(cls) -> bool:
        return True

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.CustomEmoji,)


class GuildConverter(BaseConverter[hikari.GatewayGuild]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.GatewayGuild:
        if ctx.client.cache:
            guild_id = parse_snowflake(argument, message="No valid guild ID found")
            if guild := ctx.client.cache.get_guild(guild_id):
                return guild

        raise ValueError("Couldn't find guild")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS

    @classmethod
    def is_inheritable(cls) -> bool:
        return True

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.Guild,)


class InviteConverter(BaseConverter[hikari.InviteWithMetadata]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.InviteWithMetadata:
        if ctx.client.cache:
            if invite := ctx.client.cache.get_invite(argument):
                return invite

        raise ValueError("Couldn't find invite")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_INVITES

    @classmethod
    def is_inheritable(cls) -> bool:
        return True

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.Invite,)


class MemberConverter(BaseConverter[hikari.Member]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.Member:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a member from a DM channel")

        if ctx.client.cache:
            member_id = parse_user_id(argument, message="No valid user mention or ID found")
            if member := ctx.client.cache.get_member(ctx.guild_id, member_id):
                return member

        raise ValueError("Couldn't find member in this guild")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_MEMBERS

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.Member,)


class PresenceConverter(BaseConverter[hikari.MemberPresence]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.MemberPresence:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a presence from a DM channel")

        if ctx.client.cache:
            user_id = parse_user_id(argument, message="No valid member mention or ID  found")
            if user := ctx.client.cache.get_presence(ctx.guild_id, user_id):
                return user

        raise ValueError("Couldn't find presence in current guild")


class RoleConverter(BaseConverter[hikari.Role]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.Role:
        if ctx.client.cache:
            role_id = parse_role_id(argument, message="No valid role mention or ID  found")
            if role := ctx.client.cache.get_role(role_id):
                return role

        raise ValueError("Couldn't find role")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.Role,)


class _IDMatcher(typing.Protocol):
    def __call__(self, value: str, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        raise NotImplementedError


def make_snowflake_parser(regex: re.Pattern[str], /) -> _IDMatcher:
    def parse(value: str, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        result: typing.Optional[hikari.Snowflake] = None
        value = value.strip()
        if value.isdigit():
            result = hikari.Snowflake(value)

        else:
            try:
                result = hikari.Snowflake(next(regex.finditer(value)).groups()[0])

            except StopIteration:
                pass

        # We should also range check the provided ID.
        if result is not None and hikari.Snowflake.min() <= result <= hikari.Snowflake.max():
            return result

        raise ValueError(message) from None

    return parse


parse_snowflake = make_snowflake_parser(re.compile(r"<[@&?!#a]{0,3}(?::\w+:)?(\d+)>"))
parse_channel_id = make_snowflake_parser(re.compile(r"<#(\d+)>"))
parse_emoji_id = make_snowflake_parser(re.compile(r"<a?:\w+:(\d+)>"))
parse_role_id = make_snowflake_parser(re.compile(r"<@&(\d+)>"))
parse_user_id = make_snowflake_parser(re.compile(r"<@!?(\d+)>"))


class SnowflakeConverter(BaseConverter[hikari.Snowflake]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return False

    async def convert(self, _: traits.Context, argument: str, /) -> hikari.Snowflake:
        return parse_snowflake(argument, message="No valid ID found")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.NONE

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.Snowflake,)


class UserConverter(BaseConverter[hikari.User]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.User:
        if ctx.client.cache:
            user_id = parse_user_id(argument, message="No valid user mention or ID  found")
            if user := ctx.client.cache.get_user(user_id):
                return user

        raise ValueError("Couldn't find user")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_MEMBERS

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.User,)


class VoiceStateConverter(BaseConverter[hikari.VoiceState]):
    __slots__: tuple[str, ...] = ()

    @property
    def cache_bound(self) -> bool:
        return True

    async def convert(self, ctx: traits.Context, argument: str, /) -> hikari.VoiceState:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a voice state from a DM channel")

        if ctx.client.cache:
            user_id = parse_user_id(argument, message="No valid user mention or ID  found")
            if user := ctx.client.cache.get_voice_state(ctx.guild_id, user_id):
                return user

        raise ValueError("Voice state couldn't be found for current guild")

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_VOICE_STATES

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> tuple[type[typing.Any], ...]:
        return (hikari.VoiceState,)


for _cls in vars().copy().values():
    if inspect.isclass(_cls) and issubclass(_cls, BaseConverter):
        BaseConverter.implementations().add(_cls)

del _cls


def _build_url_parser(callback: collections.Callable[[str], _ValueT], /) -> collections.Callable[[str], _ValueT]:
    def parse(value: str, /) -> _ValueT:
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1]

        return callback(value)

    return parse


defragment_url = _build_url_parser(urllib.parse.urldefrag)
parse_url = _build_url_parser(urllib.parse.urlparse)
split_url = _build_url_parser(urllib.parse.urlsplit)


_DATETIME_REGEX = re.compile(r"<-?t:(\d+)(?::\w)?>")


def convert_datetime(value: str, /) -> datetime.datetime:
    try:
        timestamp = int(next(_DATETIME_REGEX.finditer(value)).groups()[0])

    except StopIteration:
        raise ValueError("Not a valid datetime")

    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


_TYPE_OVERRIDES: dict[collections.Callable[..., typing.Any], collections.Callable[[str], typing.Any]] = {
    bool: distutils.util.strtobool,
    bytes: lambda d: bytes(d, "utf-8"),
    bytearray: lambda d: bytearray(d, "utf-8"),
    datetime.datetime: convert_datetime,
    hikari.Snowflake: parse_snowflake,
    urllib.parse.DefragResult: defragment_url,
    urllib.parse.ParseResult: parse_url,
    urllib.parse.SplitResult: split_url,
}


def override_type(cls: parsing.ConverterSig, /) -> parsing.ConverterSig:
    return _TYPE_OVERRIDES.get(cls, cls)
