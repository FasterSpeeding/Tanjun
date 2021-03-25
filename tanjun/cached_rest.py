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

__all__: typing.Sequence[str] = ["CachedREST"]

import asyncio
import datetime
import time
import typing

from hikari import applications
from hikari import channels
from hikari import errors
from hikari import snowflakes

from tanjun import traits as tanjun_traits

if typing.TYPE_CHECKING:
    import types

    from hikari import emojis
    from hikari import guilds
    from hikari import invites
    from hikari import messages
    from hikari import traits as hikari_traits
    from hikari import users


KeyT = typing.TypeVar("KeyT")
ValueT = typing.TypeVar("ValueT")
OrFuture = typing.Union[ValueT, "asyncio.Future[ValueT]"]


class _TimeLimitedMapping(typing.MutableMapping[KeyT, ValueT]):
    __slots__: typing.Sequence[str] = ("_data", "_expiry")

    def __init__(self, expire_delta: datetime.timedelta, /) -> None:
        self._data: typing.Dict[KeyT, typing.Tuple[float, ValueT]] = {}
        self._expiry = expire_delta.total_seconds()

    def __delitem__(self, key: KeyT, /) -> None:
        del self._data[key]
        self.gc()

    def __getitem__(self, key: KeyT, /) -> ValueT:
        self.gc()
        return self._data[key][1]

    def __iter__(self) -> typing.Iterator[KeyT]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __setitem__(self, key: KeyT, value: ValueT, /) -> None:
        self.gc()

        # Seeing as we rely on insertion order in _garbage_collect, we have to make sure that each item is added to
        # the end of the dict.
        if key in self:
            del self[key]

        self._data[key] = (time.perf_counter(), value)

    def clear(self) -> None:
        self._data.clear()

    def copy(self) -> typing.Dict[KeyT, ValueT]:
        self.gc()
        return {key: value for key, (_, value) in self._data.items()}

    def gc(self) -> None:
        current_time = time.perf_counter()
        for key, value in self._data.copy().items():
            if current_time - value[0] < self._expiry:
                break

            del self._data[key]


class _TimeLimitedFutureMapping(_TimeLimitedMapping[KeyT, "asyncio.Future[ValueT]"]):
    __slots__: typing.Sequence[str] = ()

    def set_future(self, key: KeyT, future: typing.Awaitable[ValueT], /) -> asyncio.Future[ValueT]:
        future = self[key] = asyncio.create_task(future)
        return future


class _TimeLimitedOrFutureMapping(_TimeLimitedMapping[KeyT, OrFuture[ValueT]]):
    __slots__: typing.Sequence[str] = ()

    def set_future(self, key: KeyT, future: typing.Awaitable[ValueT], /) -> asyncio.Future[ValueT]:
        future = self[key] = asyncio.create_task(future)
        return future


class _ErrorManager:
    __slots__: typing.Sequence[str] = ()

    def __enter__(self) -> _ErrorManager:
        return self

    @typing.overload
    def __exit__(
        self,
        exception_type: None,
        exception: None,
        exception_traceback: None,
    ) -> typing.Optional[bool]:
        raise NotImplementedError

    @typing.overload
    def __exit__(
        self,
        exception_type: typing.Type[BaseException],
        exception: BaseException,
        exception_traceback: types.TracebackType,
    ) -> typing.Optional[bool]:
        raise NotImplementedError

    def __exit__(
        self,
        exception_type: typing.Optional[typing.Type[BaseException]],
        exception: typing.Optional[BaseException],
        exception_traceback: typing.Optional[types.TracebackType],
    ) -> typing.Optional[bool]:
        if exception_type is None:
            return None

        if (
            issubclass(exception_type, errors.HTTPResponseError)
            # We don't want to cache rate-limit errors and RateLimitTooLongError isn't a HTTPResponseError error.
            and exception_type is not errors.RateLimitedError
            # We don't expected internal server errors to repeat.
            and not issubclass(exception_type, errors.InternalServerError)
        ):
            return True  # suppress the error

        return False  # re-raise the error


ERROR_MANAGER: typing.Final[_ErrorManager] = _ErrorManager()


class SingleValueResource(typing.Generic[ValueT]):
    __slots__: typing.Sequence[str] = ("_expire", "_time", "_value")

    def __init__(self, expire: datetime.timedelta, /) -> None:
        self._expire = expire.total_seconds()
        self._time = 0.0
        self._value: typing.Optional[asyncio.Future[ValueT]] = None

    def clear(self) -> None:
        self._value = None
        self._time = 0.0

    def gc(self) -> None:
        if time.perf_counter() - self._time >= self._expire:
            self._value = None
            self._time = 0.0

    def get(self) -> typing.Optional[asyncio.Future[ValueT]]:
        self.gc()
        return self._value

    def set(self, value: typing.Awaitable[ValueT], /) -> asyncio.Future[ValueT]:
        self._time = time.perf_counter()
        self._value = asyncio.create_task(value)
        return self._value


class CachedREST(tanjun_traits.CachedREST):
    __slots__: typing.Sequence[str] = (
        "_application_store",
        "_channel_store",
        "_emoji_store",
        "_guild_store",
        "_invite_store",
        "_me_store",
        "_member_store",
        "_message_store",
        "_rest",
        "_role_store",
        "_user_store",
    )

    _application_store: SingleValueResource[applications.Application]
    _channel_store: _TimeLimitedFutureMapping[snowflakes.Snowflake, channels.PartialChannel]
    _emoji_store: _TimeLimitedOrFutureMapping[snowflakes.Snowflake, emojis.KnownCustomEmoji]
    _guild_store: _TimeLimitedFutureMapping[snowflakes.Snowflake, guilds.RESTGuild]
    _invite_store: _TimeLimitedFutureMapping[str, invites.Invite]
    _me_store: SingleValueResource[users.OwnUser]
    _member_store: _TimeLimitedFutureMapping[str, guilds.Member]
    _message_store: _TimeLimitedFutureMapping[snowflakes.Snowflake, messages.Message]
    _role_store: _TimeLimitedOrFutureMapping[snowflakes.Snowflake, typing.Sequence[guilds.Role]]
    _user_store: _TimeLimitedOrFutureMapping[snowflakes.Snowflake, users.User]

    def __init__(
        self,
        rest: hikari_traits.RESTAware,
        /,
        *,
        application_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        channel_expire: datetime.timedelta = datetime.timedelta(seconds=5),  # Permission related
        emoji_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        guild_expire: datetime.timedelta = datetime.timedelta(seconds=30),
        invite_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        me_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        member_expire: datetime.timedelta = datetime.timedelta(seconds=5),  # Permission related
        message_expire: datetime.timedelta = datetime.timedelta(seconds=10),
        role_expire: datetime.timedelta = datetime.timedelta(seconds=5),  # Permission related
        user_expire: datetime.timedelta = datetime.timedelta(seconds=60),
    ) -> None:
        self._application_store = SingleValueResource(application_expire)
        self._channel_store = _TimeLimitedFutureMapping(channel_expire)
        self._emoji_store = _TimeLimitedOrFutureMapping(emoji_expire)
        self._guild_store = _TimeLimitedFutureMapping(guild_expire)
        self._invite_store = _TimeLimitedFutureMapping(invite_expire)
        self._me_store = SingleValueResource(me_expire)
        self._member_store = _TimeLimitedFutureMapping(member_expire)
        self._message_store = _TimeLimitedFutureMapping(message_expire)
        self._rest = rest
        self._role_store = _TimeLimitedOrFutureMapping(role_expire)
        self._user_store = _TimeLimitedOrFutureMapping(user_expire)

    def clear(self) -> None:
        self._application_store.clear()
        self._channel_store.clear()
        self._emoji_store.clear()
        self._guild_store.clear()
        self._invite_store.clear()
        self._me_store.clear()
        self._member_store.clear()
        self._message_store.clear()
        self._role_store.clear()
        self._user_store.clear()

    def gc(self) -> None:
        self._application_store.gc()
        self._channel_store.gc()
        self._emoji_store.gc()
        self._guild_store.gc()
        self._invite_store.gc()
        self._me_store.gc()
        self._member_store.gc()
        self._message_store.gc()
        self._role_store.gc()
        self._user_store.gc()

    async def fetch_application(self) -> applications.Application:
        if application := self._application_store.get():
            with ERROR_MANAGER:
                return await application

            self._application_store.clear()  # type: ignore[unreachable]

        fetched_application = await self._application_store.set(self._rest.rest.fetch_application())

        if fetched_application.team:
            self._user_store.update(fetched_application.team.members)

        else:
            self._user_store[fetched_application.owner.id] = fetched_application.owner

        return fetched_application

    async def fetch_channel(
        self, channel: snowflakes.SnowflakeishOr[channels.PartialChannel], /
    ) -> channels.PartialChannel:
        channel = snowflakes.Snowflake(channel)
        if cached_channel := self._channel_store.get(channel):
            with ERROR_MANAGER:
                return await cached_channel

            self._channel_store.pop(channel, None)  # type: ignore[unreachable]

        fetched_channel = await self._channel_store.set_future(channel, self._rest.rest.fetch_channel(channel))
        if isinstance(fetched_channel, channels.DMChannel):
            self._user_store[fetched_channel.recipient.id] = fetched_channel.recipient

        elif isinstance(fetched_channel, channels.GroupDMChannel):
            self._user_store.update(fetched_channel.recipients)

        return fetched_channel

    async def fetch_emoji(
        self,
        guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
        emoji: snowflakes.SnowflakeishOr[emojis.CustomEmoji],
        /,
    ) -> emojis.KnownCustomEmoji:
        emoji = snowflakes.Snowflake(emoji)
        if isinstance(cached_emoji := self._emoji_store.get(emoji), asyncio.Future):
            with ERROR_MANAGER:
                return await cached_emoji

            self._emoji_store.pop(emoji, None)  # type: ignore[unreachable]

        elif cached_emoji:
            return cached_emoji

        fetched_emoji = await self._emoji_store.set_future(emoji, self._rest.rest.fetch_emoji(guild, emoji))

        if fetched_emoji.user:
            self._user_store[fetched_emoji.user.id] = fetched_emoji.user

        return fetched_emoji

    async def fetch_guild(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild], /) -> guilds.RESTGuild:
        guild = snowflakes.Snowflake(guild)
        if cached_guild := self._guild_store.get(guild):
            with ERROR_MANAGER:
                return await cached_guild

            self._guild_store.pop(guild, None)  # type: ignore[unreachable]

        fetched_guild = await self._guild_store.set_future(guild, self._rest.rest.fetch_guild(guild))
        self._emoji_store.update(fetched_guild.emojis)
        self._role_store[guild] = list(fetched_guild.roles.values())
        return fetched_guild

    async def fetch_invite(self, invite: typing.Union[str, invites.Invite], /) -> invites.Invite:
        invite_code = invite if isinstance(invite, str) else invite.code
        if cached_invite := self._invite_store.get(invite_code):
            with ERROR_MANAGER:
                return await cached_invite

            self._invite_store.pop(invite_code, None)  # type: ignore[unreachable]

        fetched_invite = await self._invite_store.set_future(invite_code, self._rest.rest.fetch_invite(invite_code))
        if fetched_invite.target_user:
            self._user_store[fetched_invite.target_user.id] = fetched_invite.target_user

        if fetched_invite.inviter:
            self._user_store[fetched_invite.inviter.id] = fetched_invite.inviter

        return fetched_invite

    async def fetch_member(
        self,
        guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
        user: snowflakes.SnowflakeishOr[users.User],
        /,
    ) -> guilds.Member:
        guild = snowflakes.Snowflake(guild)
        user = snowflakes.Snowflake(user)
        cache_id = f"{guild}:{user}"
        if cached_member := self._member_store.get(cache_id):
            with ERROR_MANAGER:
                return await cached_member

            self._member_store.pop(cache_id, None)  # type: ignore[unreachable]

        fetched_member = await self._member_store.set_future(cache_id, self._rest.rest.fetch_member(guild, user))
        self._user_store[user] = fetched_member.user
        return fetched_member

    async def fetch_message(
        self,
        channel: snowflakes.SnowflakeishOr[channels.PartialChannel],
        message: snowflakes.SnowflakeishOr[messages.Message],
        /,
    ) -> messages.Message:
        channel = snowflakes.Snowflake(channel)
        message = snowflakes.Snowflake(message)
        if isinstance(cached_message := self._message_store.get(message), asyncio.Future):
            with ERROR_MANAGER:
                return await cached_message

            self._message_store.pop(message, None)  # type: ignore[unreachable]

        return await self._message_store.set_future(message, self._rest.rest.fetch_message(channel, message))

    async def fetch_my_user(self) -> users.OwnUser:
        if me := self._me_store.get():
            with ERROR_MANAGER:
                return await me

            self._me_store.clear()  # type: ignore[unreachable]

        user = await self._rest.rest.fetch_my_user()
        self._user_store[user.id] = user
        return user

    async def fetch_role(
        self,
        guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
        role: snowflakes.SnowflakeishOr[guilds.PartialRole],
        /,
    ) -> guilds.Role:
        role = snowflakes.Snowflake(role)

        for fetched_role in await self.fetch_roles(guild):
            if fetched_role.id == role:
                return fetched_role

        raise LookupError("Couldn't find role")

    async def fetch_roles(
        self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild], /
    ) -> typing.Sequence[guilds.Role]:
        guild = snowflakes.Snowflake(guild)
        if isinstance(cached_roles := self._role_store.get(guild), asyncio.Future):
            with ERROR_MANAGER:
                return await cached_roles

            self._role_store.pop(guild, None)  # type: ignore[unreachable]

        elif cached_roles:
            return cached_roles

        fetched_roles = await self._role_store.set_future(guild, self._rest.rest.fetch_roles(guild))
        return fetched_roles

    async def fetch_user(self, user: snowflakes.SnowflakeishOr[users.User]) -> users.User:
        user = snowflakes.Snowflake(user)
        if isinstance(cached_user := self._user_store.get(user), asyncio.Future):
            with ERROR_MANAGER:
                return await cached_user

            self._user_store.pop(user, None)  # type: ignore[unreachable]

        elif cached_user:
            return cached_user

        return await self._user_store.set_future(user, self._rest.rest.fetch_user(user))
