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
"""A collection of common standard checks designed for Tanjun commands."""

from __future__ import annotations

__all__: typing.Sequence[str] = [
    "with_check",
    "with_dm_check",
    "with_guild_check",
    "with_nsfw_check",
    "with_sfw_check",
    "with_owner_check",
    "with_author_permission_check",
    "with_own_permission_check",
]

import abc
import asyncio
import datetime
import time
import typing

from hikari import channels
from hikari import errors as hikari_errors
from hikari import guilds
from hikari import permissions as permissions_
from hikari import snowflakes
from hikari.interactions import bases as base_interactions
from yuyo import backoff

from tanjun import utilities

if typing.TYPE_CHECKING:
    from hikari import applications
    from hikari import users
    from hikari.api import cache as cache_api
    from hikari.api import rest as rest_api

    from tanjun import traits as tanjun_traits

CommandT = typing.TypeVar("CommandT", bound="tanjun_traits.ExecutableCommand[typing.Any]")


class ApplicationOwnerCheck:
    __slots__: typing.Sequence[str] = ("_application", "_expire", "_lock", "_owner_ids", "_time")

    def __init__(
        self,
        *,
        expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
        owner_ids: typing.Optional[typing.Iterable[snowflakes.SnowflakeishOr[users.User]]] = None,
    ) -> None:
        self._application: typing.Optional[applications.Application] = None
        self._expire = expire_delta.total_seconds()
        self._lock = asyncio.Lock()
        self._owner_ids = tuple(snowflakes.Snowflake(id_) for id_ in owner_ids) if owner_ids else ()
        self._time = 0.0

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        return await self.check(ctx)

    @property
    def _is_expired(self) -> bool:
        return time.perf_counter() - self._time >= self._expire

    async def _try_fetch(self, rest: rest_api.RESTClient, /) -> applications.Application:  # type: ignore[return]
        retry = backoff.Backoff()
        async for _ in retry:
            try:
                self._application = await rest.fetch_application()  # TODO: or fetch authroization
                return self._application

            except (hikari_errors.RateLimitedError, hikari_errors.RateLimitTooLongError) as exc:
                retry.set_next_backoff(exc.retry_after)

            except hikari_errors.InternalServerError:
                continue

    async def _get_application(self, ctx: tanjun_traits.Context, /) -> applications.Application:
        if self._application and not self._is_expired:
            return self._application

        async with self._lock:
            if self._application and not self._is_expired:
                return self._application

            try:
                application = await ctx.client.rest.fetch_application()
                self._application = application

            except (
                hikari_errors.RateLimitedError,
                hikari_errors.RateLimitTooLongError,
                hikari_errors.InternalServerError,
            ):
                # If we can't fetch this information straight away and don't have a stale state to go off then we
                # have to retry before returning.
                if not self._application:
                    application = await asyncio.wait_for(self._try_fetch(ctx.client.rest), 10)

                # Otherwise we create a task to ensure that we will still try to refresh the stored state in the future
                # while returning the stale state to ensure that the command execution doesn't stall.
                else:
                    asyncio.create_task(asyncio.wait_for(self._try_fetch(ctx.client.rest), self._expire * 0.80))
                    application = self._application

            self._time = time.perf_counter()

        return application

    def close(self) -> None:
        ...  # This is only left in to match up with the `open` method.

    async def open(
        self,
        client: tanjun_traits.Client,
        /,
        *,
        timeout: typing.Optional[datetime.timedelta] = datetime.timedelta(seconds=30),
    ) -> None:
        try:
            await self.update(client.rest, timeout=timeout)

        except asyncio.TimeoutError:
            pass

    async def check(self, ctx: tanjun_traits.Context, /) -> bool:
        if ctx.author.id in self._owner_ids:
            return True

        application = await self._get_application(ctx)

        if not application.team:
            return ctx.author.id == application.owner.id

        return ctx.author.id in application.team.members

    async def update(
        self,
        rest: rest_api.RESTClient,
        /,
        *,
        timeout: typing.Optional[datetime.timedelta] = datetime.timedelta(seconds=30),
    ) -> None:
        self._time = time.perf_counter()
        await asyncio.wait_for(self._try_fetch(rest), timeout.total_seconds() if timeout else None)


async def nsfw_check(ctx: tanjun_traits.Context, /) -> bool:
    channel: typing.Optional[channels.PartialChannel] = None
    if ctx.client.cache:
        channel = ctx.client.cache.get_guild_channel(ctx.channel_id)

    if not channel:
        retry = backoff.Backoff(maximum=5, max_retries=4)
        channel = await utilities.fetch_resource(retry, ctx.client.rest.fetch_channel, ctx.channel_id)

    return channel.is_nsfw or False if isinstance(channel, channels.GuildChannel) else True


async def sfw_check(ctx: tanjun_traits.Context, /) -> bool:
    return not await nsfw_check(ctx)


def dm_check(ctx: tanjun_traits.Context, /) -> bool:
    return ctx.guild_id is None


def guild_check(ctx: tanjun_traits.Context, /) -> bool:
    return not dm_check(ctx)


class PermissionCheck(abc.ABC):
    __slots__: typing.Sequence[str] = ("permissions",)

    def __init__(self, permissions: typing.Union[permissions_.Permissions, int], /) -> None:
        self.permissions = permissions_.Permissions(permissions)

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        return (self.permissions & await self.get_permissions(ctx)) == self.permissions

    @abc.abstractmethod
    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> permissions_.Permissions:
        raise NotImplementedError


class AuthorPermissionCheck(PermissionCheck):
    __slots__: typing.Sequence[str] = ()

    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> permissions_.Permissions:
        if not ctx.member:
            return utilities.ALL_PERMISSIONS

        elif isinstance(ctx.member, base_interactions.InteractionMember):
            return ctx.member.permissions

        return await utilities.fetch_permissions(ctx.client, ctx.member, channel=ctx.channel_id)


class OwnPermissionsCheck(PermissionCheck):
    __slots__: typing.Sequence[str] = ("_lock", "_me")

    def __init__(self, permissions: typing.Union[permissions_.Permissions, int], /) -> None:
        super().__init__(permissions)
        self._lock = asyncio.Lock()
        self._me: typing.Optional[users.User] = None

    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> permissions_.Permissions:
        if ctx.guild_id is None:
            return utilities.ALL_PERMISSIONS

        member = await self._get_member(ctx, ctx.guild_id)
        return await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

    async def _get_member(self, ctx: tanjun_traits.Context, guild_id: snowflakes.Snowflake, /) -> guilds.Member:
        user = await self._get_user(ctx.client.cache, ctx.client.rest)

        if ctx.client.cache and (member := ctx.client.cache.get_member(guild_id, user.id)):
            return member

        retry = backoff.Backoff(maximum=5, max_retries=4)
        return await utilities.fetch_resource(retry, ctx.client.rest.fetch_member, guild_id, user.id)

    async def _get_user(self, cache: typing.Optional[cache_api.Cache], rest: rest_api.RESTClient, /) -> users.User:
        if not self._me:
            async with self._lock:
                if self._me:
                    return self._me

                if cache and (user := cache.get_me()):
                    self._me = user

                else:
                    retry = backoff.Backoff(maximum=5, max_retries=4)
                    raw_user = await utilities.fetch_resource(retry, rest.fetch_my_user)
                    self._me = raw_user

        return self._me


def with_dm_check(command: CommandT, /) -> CommandT:
    """Only let a command run in a DM channel.

    Parameters
    ----------
    command : CommandT
        The command to add this check to.

    Returns
    -------
    CommandT
        The command this check was added to.
    """
    command.add_check(dm_check)
    return command


def with_guild_check(command: CommandT, /) -> CommandT:
    """Only let a command run in a guild channel.

    Parameters
    ----------
    command : CommandT
        The command to add this check to.

    Returns
    -------
    CommandT
        The command this check was added to.
    """
    command.add_check(guild_check)
    return command


def with_nsfw_check(command: CommandT, /) -> CommandT:
    """Only let a command run in a channel that's marked as nsfw.

    Parameters
    ----------
    command : CommandT
        The command to add this check to.

    Returns
    -------
    CommandT
        The command this check was added to.
    """
    command.add_check(nsfw_check)
    return command


def with_sfw_check(command: CommandT, /) -> CommandT:
    """Only let a command run in a channel that's marked as sfw.

    Parameters
    ----------
    command : CommandT
        The command to add this check to.

    Returns
    -------
    CommandT
        The command this check was added to.
    """
    command.add_check(sfw_check)
    return command


def with_owner_check(command: CommandT, /) -> CommandT:
    """Only let a command run if it's being triggered by one of the bot's owners.

    !!! note
        This is based on the owner(s) of the bot's application and will account
        for team owners as well.

    Parameters
    ----------
    command : CommandT
        The command to add this check to.

    Returns
    -------
    CommandT
        The command this check was added to.
    """
    command.add_check(ApplicationOwnerCheck())
    return command


def with_author_permission_check(
    permissions: typing.Union[permissions_.Permissions, int], /
) -> typing.Callable[[CommandT], CommandT]:
    """Only let a command run if the author has certain permissions in the current channel.

    !!! note
        This will always pass for commands triggered in DM channels.

    Parameters
    ----------
    permissions: typing.Union[hikari.permissions.Permissions, int]
        The permission(s) required for this command to run.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]
        A command decorator function which adds the check.
    """

    def decorator(command: CommandT, /) -> CommandT:
        command.add_check(AuthorPermissionCheck(permissions))
        return command

    return decorator


def with_own_permission_check(
    permissions: typing.Union[permissions_.Permissions, int], /
) -> typing.Callable[[CommandT], CommandT]:
    """Only let a command run if we have certain permissions in the current channel.

    !!! note
        This will always pass for commands triggered in DM channels.

    Parameters
    ----------
    permissions: typing.Union[hikari.permissions.Permissions, int]
        The permission(s) required for this command to run.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]
        A command decorator function which adds the check.
    """

    def decorator(command: CommandT, /) -> CommandT:
        command.add_check(OwnPermissionsCheck(permissions))
        return command

    return decorator


def with_check(check: tanjun_traits.CheckSig, /) -> typing.Callable[[CommandT], CommandT]:
    """Add a generic check to a command.

    Parameters
    ----------
    check : tanjun.traits.CheckSig
        The check to add to this command.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]
        A command decorator function which adds the check.
    """

    def decorator(command: CommandT, /) -> CommandT:
        command.add_check(check)
        return command

    return decorator
