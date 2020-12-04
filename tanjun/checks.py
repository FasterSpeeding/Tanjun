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

__all__: typing.Sequence[str] = [
    "dm_only",
    "guild_only",
    "nsfw_only",
    "sfw_only",
    "owner_only",
    "requires_author_permissions",
    "requires_bot_permissions",
]

import abc
import asyncio
import typing

from hikari import channels
from hikari import errors as hikari_errors
from hikari import guilds
from hikari import permissions as permissions_
from hikari.events import member_events
from yuyo import backoff

from tanjun import utilities

if typing.TYPE_CHECKING:
    from hikari import applications
    from hikari import snowflakes
    from hikari import traits as hikari_traits
    from hikari import users

    from tanjun import traits as tanjun_traits


CommandT = typing.TypeVar("CommandT", bound="tanjun_traits.CommandDescriptor")


class ApplicationOwnerCheck:
    __slots__: typing.Sequence[str] = ("_application", "_client", "_fetch_task", "_lock")

    def __init__(self) -> None:
        self._application: typing.Optional[applications.Application] = None
        self._client: typing.Optional[tanjun_traits.Client] = None
        self._fetch_task: typing.Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        if ctx.client:
            self._client = ctx.client

        return await self.check(ctx)

    @staticmethod
    async def _fetch_application(rest: hikari_traits.RESTAware, /) -> applications.Application:  # type: ignore[return]
        retry = backoff.Backoff()
        async for _ in retry:
            try:
                return await rest.rest.fetch_application()

            except hikari_errors.RateLimitedError as exc:
                retry.set_next_backoff(exc.retry_after)

            except hikari_errors.InternalServerError:
                continue

    async def _fetch_loop(self) -> None:
        while True:
            # Update the application every 30 minutes.
            await asyncio.sleep(1_800)
            if self._client:
                try:
                    self._application = await self._fetch_application(self._client.rest_service)

                except hikari_errors.ForbiddenError:
                    pass

    async def _get_application(self, ctx: tanjun_traits.Context, /) -> applications.Application:
        if not self._application:
            async with self._lock:
                if self._application:
                    return self._application

                self._application = await self._fetch_application(ctx.client.rest_service)

                if not self._fetch_task:
                    self._fetch_task = asyncio.create_task(self._fetch_loop())

        return self._application

    async def check(self, ctx: tanjun_traits.Context, /) -> bool:
        application = await self._get_application(ctx)

        if not application.team and application.owner:
            return ctx.message.author.id == application.owner.id

        return bool(application.team and ctx.message.author.id in application.team.members)

    def close(self) -> None:
        if self._fetch_task:
            self._fetch_task.cancel()
            self._fetch_task = None

    async def open(self, client: tanjun_traits.Client, /) -> None:
        self.close()
        self._client = client
        self._fetch_task = asyncio.create_task(self._fetch_loop())

    async def update(self, *, rest: typing.Optional[hikari_traits.RESTAware] = None) -> None:
        if not rest and self._client:
            rest = self._client.rest_service

        elif not rest:
            raise ValueError("REST client must be provided when trying to update a closed application owner check.")

        self._application = await self._fetch_application(rest)


async def nsfw_check(ctx: tanjun_traits.Context, /) -> bool:
    channel: typing.Optional[channels.PartialChannel] = None
    if ctx.client.cache_service:
        channel = ctx.client.cache_service.cache.get_guild_channel(ctx.message.channel_id)

    if not channel:
        retry = backoff.Backoff(maximum=5, max_retries=4)
        channel = await utilities.fetch_resource(retry, ctx.message.fetch_channel)

    return channel.is_nsfw or False if isinstance(channel, channels.GuildChannel) else True


async def sfw_check(ctx: tanjun_traits.Context, /) -> bool:
    return not await nsfw_check(ctx)


def dm_check(ctx: tanjun_traits.Context, /) -> bool:
    return ctx.message.guild_id is None


def guild_check(ctx: tanjun_traits.Context, /) -> bool:
    return not dm_check(ctx)


class PermissionCheck(abc.ABC):
    __slots__: typing.Sequence[str] = ("permissions",)

    def __init__(self, permissions: permissions_.Permissions, /) -> None:
        self.permissions = permissions

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        return (self.permissions & await self.get_permissions(ctx)) == self.permissions

    @abc.abstractmethod
    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> permissions_.Permissions:
        raise NotImplementedError


class AuthorPermissionCheck(PermissionCheck):
    __slots__: typing.Sequence[str] = ()

    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> permissions_.Permissions:
        if not ctx.message.member:
            return utilities.ALL_PERMISSIONS

        return await utilities.calculate_permissions(ctx.client, ctx.message.member, channel=ctx.message.channel_id)


class BotPermissionsCheck(PermissionCheck):
    __slots__: typing.Sequence[str] = ("_lock", "_me" "_members")

    def __init__(self, permissions: permissions_.Permissions, /) -> None:
        super().__init__(permissions)
        self._lock = asyncio.Lock()
        self._me: typing.Optional[users.User] = None
        self._members: typing.MutableMapping[snowflakes.Snowflake, guilds.Member] = {}

    async def on_member_event(self, event: member_events.MemberEvent, /) -> None:
        if event.user_id != (await self._get_user(event.app, event.app)):
            return

        if isinstance(event, (member_events.MemberUpdateEvent, member_events.MemberCreateEvent)):
            self._members[event.user_id] = event.member

        elif event.user_id in self._members:
            del self._members[event.user_id]

    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> permissions_.Permissions:
        if ctx.message.guild_id is None:
            return utilities.ALL_PERMISSIONS

        member = await self._get_member(ctx)
        return await utilities.calculate_permissions(ctx.client, member, channel=ctx.message.channel_id)

    async def _get_member(self, ctx: tanjun_traits.Context, /) -> guilds.Member:
        if ctx.message.guild_id is None:
            raise RuntimeError("Cannot get member for a DM Channel")

        if member := self._members.get(ctx.message.guild_id):
            return member

        user = await self._get_user(ctx.client.cache_service, ctx.client.rest_service)

        if ctx.client.cache_service and (
            member := ctx.client.cache_service.cache.get_member(ctx.message.guild_id, user.id)
        ):
            return member

        retry = backoff.Backoff(maximum=5, max_retries=4)
        return await utilities.fetch_resource(
            retry, ctx.client.rest_service.rest.fetch_member, ctx.message.guild_id, user.id,
        )

    async def _get_user(
        self, cache_service: typing.Optional[hikari_traits.CacheAware], rest_service: hikari_traits.RESTAware, /
    ) -> users.User:
        if not self._me:
            async with self._lock:
                if self._me:
                    return self._me

                if cache_service and (user := cache_service.cache.get_me()):
                    self._me = user

                else:
                    retry = backoff.Backoff(maximum=5, max_retries=4)
                    raw_user = await utilities.fetch_resource(retry, rest_service.rest.fetch_my_user)
                    self._me = raw_user

        return self._me


def dm_only(command: CommandT, /) -> CommandT:
    command.add_check(guild_check)
    return command


def guild_only(command: CommandT, /) -> CommandT:
    command.add_check(dm_check)
    return command


def nsfw_only(command: CommandT, /) -> CommandT:
    command.add_check(nsfw_check)
    return command


def sfw_only(command: CommandT, /) -> CommandT:
    command.add_check(sfw_check)
    return command


def owner_only(command: CommandT, /) -> CommandT:
    command.add_check(ApplicationOwnerCheck())
    return command


def requires_author_permissions(permissions: permissions_.Permissions, /) -> typing.Callable[[CommandT], CommandT]:
    def decorator(command: CommandT, /) -> CommandT:
        command.add_check(AuthorPermissionCheck(permissions))
        return command

    return decorator


def requires_bot_permissions(permissions: permissions_.Permissions, /) -> typing.Callable[[CommandT], CommandT]:
    def decorator(command: CommandT, /) -> CommandT:
        command.add_check(BotPermissionsCheck(permissions))
        return command

    return decorator
