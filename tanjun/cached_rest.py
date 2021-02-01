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
OrFutureT = typing.Union[ValueT, asyncio.Future[ValueT]]


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


class _FailedCallError(Exception):
    __slots__: typing.Sequence[str] = ()


class _ErrorManager:
    __slots__: typing.Sequence[str] = ("_resource",)

    def __init__(self, future: asyncio.Future[typing.Any], /) -> None:
        self._future = future

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
            assert exception is not None
            self._future.set_exception(exception)

        else:
            self._future.set_exception(_FailedCallError())

        return None


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

    def get(self) -> typing.Optional[asyncio.Future[ValueT]]:
        self.gc()
        return self._value

    def set(self, value: asyncio.Future[ValueT], /) -> None:
        self._time = time.perf_counter()
        self._value = value


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
    _channel_store: _TimeLimitedMapping[snowflakes.Snowflake, asyncio.Future[channels.PartialChannel]]
    _emoji_store: _TimeLimitedMapping[snowflakes.Snowflake, OrFutureT[emojis.KnownCustomEmoji]]
    _guild_store: _TimeLimitedMapping[snowflakes.Snowflake, asyncio.Future[guilds.Guild]]
    _invite_store: _TimeLimitedMapping[str, asyncio.Future[invites.Invite]]
    _me_store: SingleValueResource[users.OwnUser]
    _member_store: _TimeLimitedMapping[str, OrFutureT[guilds.Member]]
    _message_store: _TimeLimitedMapping[snowflakes.Snowflake, asyncio.Future[messages.Message]]
    _roles_store: _TimeLimitedMapping[snowflakes.Snowflake, OrFutureT[typing.Sequence[guilds.Role]]]
    _user_store: _TimeLimitedMapping[snowflakes.Snowflake, OrFutureT[users.User]]

    def __init__(
        self,
        rest: hikari_traits.RESTAware,
        /,
        *,
        application_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        channel_expire: datetime.timedelta = datetime.timedelta(seconds=10),
        emoji_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        guild_expire: datetime.timedelta = datetime.timedelta(seconds=30),
        invite_expire: datetime.timedelta = datetime.timedelta(seconds=60),
        me_expire: datetime.timedelta = datetime.timedelta(seconds=120),
        member_expire: datetime.timedelta = datetime.timedelta(seconds=5),
        message_expire: datetime.timedelta = datetime.timedelta(seconds=10),
        role_expire: datetime.timedelta = datetime.timedelta(seconds=10),
        user_expire: datetime.timedelta = datetime.timedelta(seconds=60),
    ) -> None:
        self._application_store = SingleValueResource(application_expire)
        self._channel_store = _TimeLimitedMapping(channel_expire)
        self._emoji_store = _TimeLimitedMapping(emoji_expire)
        self._guild_store = _TimeLimitedMapping(guild_expire)
        self._invite_store = _TimeLimitedMapping(invite_expire)
        self._me_store = SingleValueResource(me_expire)
        self._member_store = _TimeLimitedMapping(member_expire)
        self._message_store = _TimeLimitedMapping(message_expire)
        self._rest = rest
        self._roles_store = _TimeLimitedMapping(role_expire)
        self._user_store = _TimeLimitedMapping(user_expire)

    def clear(self) -> None:
        self._application_store.clear()
        self._channel_store.clear()
        self._emoji_store.clear()
        self._guild_store.clear()
        self._invite_store.clear()
        self._me_store.clear()
        self._member_store.clear()
        self._message_store.clear()
        self._roles_store.clear()
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
        self._roles_store.gc()
        self._user_store.gc()

    async def fetch_application(self) -> applications.Application:
        if application := self._application_store.get():
            try:
                return await application

            except _FailedCallError:
                self._application_store.clear()

        future: asyncio.Future[applications.Application] = asyncio.Future()
        self._application_store.set(future)

        with _ErrorManager(future):
            fetched_application = await self._rest.rest.fetch_application()
            future.set_result(fetched_application)

            if fetched_application.team:
                for user_id, member in fetched_application.team.members.items():
                    self._user_store[user_id] = member.user

            else:
                self._user_store[fetched_application.owner.id] = fetched_application.owner

            return fetched_application

    async def fetch_channel(
        self, channel: snowflakes.SnowflakeishOr[channels.PartialChannel], /
    ) -> channels.PartialChannel:
        channel = snowflakes.Snowflake(channel)
        if cached_channel := self._channel_store.get(channel):
            try:
                return await cached_channel

            except _FailedCallError:
                del self._channel_store[channel]

        future: asyncio.Future[channels.PartialChannel] = asyncio.Future()
        self._channel_store[channel] = future

        with _ErrorManager(future):
            fetched_channel = await self._rest.rest.fetch_channel(channel)
            future.set_result(fetched_channel)
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
            try:
                return await cached_emoji

            except _FailedCallError:
                del self._emoji_store[emoji]

        elif cached_emoji:
            return cached_emoji

        future: asyncio.Future[emojis.KnownCustomEmoji] = asyncio.Future()
        self._emoji_store[emoji] = future

        with _ErrorManager(future):
            fetched_emoji = await self._rest.rest.fetch_emoji(guild, emoji)
            future.set_result(fetched_emoji)

            if fetched_emoji.user:
                self._user_store[fetched_emoji.user.id] = fetched_emoji.user

            return fetched_emoji

    async def fetch_guild(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild], /) -> guilds.Guild:
        guild = snowflakes.Snowflake(guild)
        if cached_guild := self._guild_store.get(guild):
            try:
                return await cached_guild

            except _FailedCallError:
                del self._guild_store[guild]

        future: asyncio.Future[guilds.Guild] = asyncio.Future()
        self._guild_store[guild] = future

        with _ErrorManager(future):
            fetched_guild = await self._rest.rest.fetch_guild(guild)
            future.set_result(fetched_guild)
            self._emoji_store.update(fetched_guild.emojis)
            self._roles_store[guild] = list(fetched_guild.roles.values())
            return fetched_guild

    async def fetch_invite(self, invite: typing.Union[str, invites.Invite], /) -> invites.Invite:
        invite_code = invite if isinstance(invite, str) else invite.code
        if cached_invite := self._invite_store.get(invite_code):
            try:
                return await cached_invite

            except _FailedCallError:
                del self._invite_store[invite_code]

        future: asyncio.Future[invites.Invite] = asyncio.Future()
        self._invite_store[invite_code] = future

        with _ErrorManager(future):
            fetched_invite = await self._rest.rest.fetch_invite(invite_code)
            if fetched_invite.target_user:
                self._user_store[fetched_invite.target_user.id] = fetched_invite.target_user

            if fetched_invite.inviter:
                self._user_store[fetched_invite.inviter.id] = fetched_invite.inviter

            future.set_result(fetched_invite)
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
        if isinstance(cached_member := self._member_store.get(cache_id), asyncio.Future):
            try:
                return await cached_member

            except _FailedCallError:
                del self._member_store[cache_id]

        elif cached_member:
            return cached_member

        future: asyncio.Future[guilds.Member] = asyncio.Future()
        self._member_store[cache_id] = future

        with _ErrorManager(future):
            fetched_member = await self._rest.rest.fetch_member(guild, user)
            future.set_result(fetched_member)
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
            try:
                return await cached_message

            except _FailedCallError:
                del self._message_store[message]

        future: asyncio.Future[messages.Message] = asyncio.Future()
        self._message_store[message] = future

        with _ErrorManager(future):
            fetched_message = await self._rest.rest.fetch_message(channel, message)
            future.set_result(fetched_message)
            return fetched_message

    async def fetch_my_user(self) -> users.OwnUser:
        if me := self._me_store.get():
            try:
                return await me

            except _FailedCallError:
                self._me_store.clear()

        future: asyncio.Future[users.OwnUser] = asyncio.Future()
        self._me_store.set(future)

        with _ErrorManager(future):
            user = await self._rest.rest.fetch_my_user()
            future.set_result(user)
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
        if isinstance(cached_roles := self._roles_store.get(guild), asyncio.Future):
            try:
                return await cached_roles

            except _FailedCallError:
                del self._roles_store[guild]

        elif cached_roles:
            return cached_roles

        future: asyncio.Future[typing.Sequence[guilds.Role]] = asyncio.Future()
        self._roles_store[guild] = future

        with _ErrorManager(future):
            fetched_roles = await self._rest.rest.fetch_roles(guild)
            future.set_result(fetched_roles)
            return fetched_roles

    async def fetch_user(self, user: snowflakes.SnowflakeishOr[users.User]) -> users.User:
        user = snowflakes.Snowflake(user)
        if isinstance(cached_user := self._user_store.get(user), asyncio.Future):
            try:
                return await cached_user

            except _FailedCallError:
                del self._user_store[user]

        elif cached_user:
            return cached_user

        future: asyncio.Future[users.User] = asyncio.Future()
        self._user_store[user] = future

        with _ErrorManager(future):
            fetched_user = await self._rest.rest.fetch_user(user)
            future.set_result(fetched_user)
            return fetched_user
