# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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

__all__: typing.Sequence[str] = []

import abc
import inspect
import re
import typing

from hikari import channels
from hikari import colors
from hikari import emojis
from hikari import guilds
from hikari import intents as intents_
from hikari import snowflakes
from hikari import users

from tanjun import traits

_ValueT = typing.TypeVar("_ValueT", covariant=True)


class BaseConverter(abc.ABC, typing.Generic[_ValueT], traits.Converter[_ValueT]):
    __implementations: typing.MutableSet[typing.Type[BaseConverter[typing.Type[typing.Any]]]] = set()

    @classmethod
    def bind_component(cls, client: traits.Client, _: traits.Component, /) -> None:
        if cls.cache_bound() and not client.cache:
            raise ValueError("Cache bound converter cannot be used with a cache-less client")

        # TODO: intents checks.

    @classmethod
    def get_from_type(
        cls, type_: typing.Type[_ValueT]
    ) -> typing.Optional[typing.Type[BaseConverter[typing.Type[_ValueT]]]]:
        for converter in cls.__implementations:
            if converter.is_inheritable() and issubclass(type_, converter.types()):
                return converter

            if not converter.is_inheritable() and type_ in converter.types():
                return converter

        return None

    @classmethod
    def implementations(cls) -> typing.MutableSet[typing.Type[BaseConverter[typing.Type[typing.Any]]]]:
        return cls.__implementations

    @classmethod
    @abc.abstractmethod
    def cache_bound(cls) -> bool:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def convert(cls, ctx: traits.Context, argument: str, /) -> _ValueT:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def intents(cls) -> intents_.Intents:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def is_inheritable(cls) -> bool:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def types(cls) -> typing.Tuple[typing.Type[typing.Any], ...]:
        raise NotImplementedError


class ColorConverter(BaseConverter[colors.Color]):
    @classmethod
    def cache_bound(cls) -> bool:
        return False

    @classmethod
    async def convert(cls, _: traits.Context, argument: str, /) -> typing.Any:
        values = argument.split(" ")
        if all(value.isdigit() for value in values):
            return colors.Color.of(*map(int, values))

        return colors.Color.of(*values)

    @classmethod
    def intents(cls) -> intents_.Intents:
        return intents_.Intents.NONE

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> typing.Tuple[typing.Type[typing.Any], ...]:
        return (colors.Color,)


class _BaseSnowflakeParser:
    @classmethod
    @abc.abstractmethod
    def regex(cls) -> typing.Pattern[str]:
        raise NotImplementedError

    @classmethod
    def match_id(cls, value: str) -> snowflakes.Snowflake:
        if value.isdigit():
            return snowflakes.Snowflake(value)

        if results := cls.regex().findall(value):
            return snowflakes.Snowflake(results[0])

        raise ValueError("No valid mention or ID found")


class _SnowflakeParser(_BaseSnowflakeParser):
    _pattern = re.compile(r"<[@&?!#]{1,3}(\d+)>")

    @classmethod
    def regex(cls) -> typing.Pattern[str]:
        return cls._pattern


class _ChannelIDParser(_BaseSnowflakeParser):
    _pattern = re.compile(r"<#(\d+)>")

    @classmethod
    def regex(cls) -> typing.Pattern[str]:
        return cls._pattern


class _EmojiIDParser(_BaseSnowflakeParser):
    _pattern = re.compile(r"<a?:\w+:(\d+)>")

    @classmethod
    def regex(cls) -> typing.Pattern[str]:
        return cls._pattern


class _UserIDParser(_BaseSnowflakeParser):
    _pattern = re.compile(r"<@!?(\d+)>")

    @classmethod
    def regex(cls) -> typing.Pattern[str]:
        return cls._pattern


class SnowflakeConverter(BaseConverter[snowflakes.Snowflake]):
    @classmethod
    def cache_bound(cls) -> bool:
        return False

    @classmethod
    async def convert(cls, _: traits.Context, argument: str, /) -> snowflakes.Snowflake:
        return _SnowflakeParser.match_id(argument)

    @classmethod
    def intents(cls) -> intents_.Intents:
        return intents_.Intents.NONE

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> typing.Tuple[typing.Type[typing.Any], ...]:
        return (snowflakes.Snowflake,)


class ChannelConverter(BaseConverter[channels.GuildChannel]):
    @classmethod
    def cache_bound(cls) -> bool:
        return True

    @classmethod
    async def convert(cls, ctx: traits.Context, argument: str, /) -> channels.GuildChannel:
        channel_id = _ChannelIDParser.match_id(argument)
        assert ctx.client.cache is not None

        if channel := ctx.client.cache.cache.get_guild_channel(channel_id):
            return channel

        raise ValueError("Couldn't find channel")

    @classmethod
    def intents(cls) -> intents_.Intents:
        return intents_.Intents.GUILDS

    @classmethod
    def is_inheritable(cls) -> bool:
        return True

    @classmethod
    def types(cls) -> typing.Tuple[typing.Type[typing.Any], ...]:
        return (channels.GuildChannel,)


class EmojiConverter(BaseConverter[emojis.KnownCustomEmoji]):
    @classmethod
    def cache_bound(cls) -> bool:
        return True

    @classmethod
    async def convert(cls, ctx: traits.Context, argument: str, /) -> emojis.KnownCustomEmoji:
        emoji_id = _EmojiIDParser.match_id(argument)
        assert ctx.client.cache is not None

        if emoji := ctx.client.cache.cache.get_emoji(emoji_id):
            return emoji

        raise ValueError("Couldn't find emoji")

    @classmethod
    def intents(cls) -> intents_.Intents:
        return intents_.Intents.GUILD_EMOJIS

    @classmethod
    def is_inheritable(cls) -> bool:
        return True

    @classmethod
    def types(cls) -> typing.Tuple[typing.Type[typing.Any], ...]:
        return (emojis.CustomEmoji,)


class UserConverter(BaseConverter[users.User]):
    @classmethod
    def cache_bound(cls) -> bool:
        return True

    @classmethod
    async def convert(cls, ctx: traits.Context, argument: str, /) -> users.User:
        user_id = _UserIDParser.match_id(argument)
        assert ctx.client.cache is not None

        if user := ctx.client.cache.cache.get_user(user_id):
            return user

        raise ValueError("Couldn't find user")

    @classmethod
    def intents(cls) -> intents_.Intents:
        return intents_.Intents.GUILD_MEMBERS

    @classmethod
    def is_inheritable(cls) -> bool:
        return False

    @classmethod
    def types(cls) -> typing.Tuple[typing.Type[typing.Any], ...]:
        return (users.User,)


class MemberConverter(BaseConverter[guilds.Member]):
    @classmethod
    def cache_bound(cls) -> bool:
        return True

    @classmethod
    async def convert(cls, ctx: traits.Context, argument: str, /) -> guilds.Member:
        if ctx.message.guild_id is None:
            raise ValueError("Cannot get a member from a DM channel")

        member_id = _UserIDParser.match_id(argument)
        assert ctx.client.cache is not None

        if member := ctx.client.cache.cache.get_member(ctx.message.guild_id, member_id):
            return member

        raise ValueError("Couldn't find member in this guild")


for cls in vars().copy().values():
    if inspect.isclass(cls) and issubclass(cls, BaseConverter):
        BaseConverter.implementations().add(cls)
