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

__all__: list[str] = [
    "CallbackReturnT",
    "CommandT",
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
from collections import abc as collections

import hikari
from yuyo import backoff

from . import errors
from . import utilities

if typing.TYPE_CHECKING:

    from . import traits as tanjun_traits


CommandT = typing.TypeVar("CommandT", bound="tanjun_traits.ExecutableCommand[typing.Any]")
CallbackReturnT = typing.Union[CommandT, collections.Callable[[CommandT], CommandT]]
"""Type hint for the return value of decorators which optionally take keyword arguments.

Examples
--------
Decorator functions with this as their return type may either be used as a
decorator directly without being explicitly called:

```python
@with_dm_check
@as_command("foo")
def foo_command(self, ctx: Context) -> None:
    raise NotImplemented
```

Or may be called with the listed other parameters as keyword arguments
while decorating a function.

```python
@with_dm_check(end_execution=True)
@as_command("foo")
def foo_command(self, ctx: Context) -> None:
    raise NotImplemented
```
"""


def _wrap_with_kwargs(
    command: typing.Optional[CommandT],
    callback: collections.Callable[..., typing.Union[bool, collections.Awaitable[bool]]],
    /,
    **kwargs: typing.Any,
) -> CallbackReturnT[CommandT]:
    if command:
        if kwargs:
            return command.add_check(lambda ctx: callback(ctx, **kwargs))

        return command.add_check(callback)

    return lambda command_: command_.add_check(lambda ctx: callback(ctx, **kwargs))


class ApplicationOwnerCheck:
    __slots__: tuple[str, ...] = ("_application", "_end_execution", "_expire", "_lock", "_owner_ids", "_time")

    def __init__(
        self,
        *,
        end_execution: bool = False,
        expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
        owner_ids: typing.Optional[collections.Iterable[hikari.SnowflakeishOr[hikari.User]]] = None,
    ) -> None:
        self._application: typing.Optional[hikari.Application] = None
        self._end_execution = end_execution
        self._expire = expire_delta.total_seconds()
        self._lock = asyncio.Lock()
        self._owner_ids = tuple(hikari.Snowflake(id_) for id_ in owner_ids) if owner_ids else ()
        self._time = 0.0

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        return await self.check(ctx)

    @property
    def _is_expired(self) -> bool:
        return time.perf_counter() - self._time >= self._expire

    async def _try_fetch(self, rest: hikari.api.RESTClient, /) -> hikari.Application:  # type: ignore[return]
        retry = backoff.Backoff()
        async for _ in retry:
            try:
                self._application = await rest.fetch_application()  # TODO: or fetch authroization
                return self._application

            except (hikari.RateLimitedError, hikari.RateLimitTooLongError) as exc:
                retry.set_next_backoff(exc.retry_after)

            except hikari.InternalServerError:
                continue

    async def _get_application(self, ctx: tanjun_traits.Context, /) -> hikari.Application:
        if self._application and not self._is_expired:
            return self._application

        async with self._lock:
            if self._application and not self._is_expired:
                return self._application

            try:
                application = await ctx.client.rest.fetch_application()
                self._application = application

            except (
                hikari.RateLimitedError,
                hikari.RateLimitTooLongError,
                hikari.InternalServerError,
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

        if application.team:
            result = ctx.author.id in application.team.members

        else:
            result = ctx.author.id == application.owner.id

        if self._end_execution and not result:
            raise errors.HaltExecutionSearch

        return result

    async def update(
        self,
        rest: hikari.api.RESTClient,
        /,
        *,
        timeout: typing.Optional[datetime.timedelta] = datetime.timedelta(seconds=30),
    ) -> None:
        self._time = time.perf_counter()
        await asyncio.wait_for(self._try_fetch(rest), timeout.total_seconds() if timeout else None)


async def nsfw_check(ctx: tanjun_traits.Context, /, *, end_execution: bool = False) -> bool:
    channel: typing.Optional[hikari.PartialChannel] = None
    if ctx.client.cache:
        channel = ctx.client.cache.get_guild_channel(ctx.channel_id)

    if not channel:
        retry = backoff.Backoff(maximum=5, max_retries=4)
        channel = await utilities.fetch_resource(retry, ctx.client.rest.fetch_channel, ctx.channel_id)

    result = channel.is_nsfw or False if isinstance(channel, hikari.GuildChannel) else True

    if end_execution and not result:
        raise errors.HaltExecutionSearch

    return result


async def sfw_check(ctx: tanjun_traits.Context, /, *, end_execution: bool = False) -> bool:
    return not await nsfw_check(ctx, end_execution=end_execution)


def dm_check(ctx: tanjun_traits.Context, /, *, end_execution: bool = False) -> bool:
    result = ctx.guild_id is None

    if end_execution and not result:
        raise errors.HaltExecutionSearch

    return result


def guild_check(ctx: tanjun_traits.Context, /, *, end_execution: bool = False) -> bool:
    return not dm_check(ctx, end_execution=end_execution)


class PermissionCheck(abc.ABC):
    __slots__: tuple[str, ...] = ("_end_execution", "permissions")

    def __init__(self, permissions: typing.Union[hikari.Permissions, int], /, *, end_execution: bool = False) -> None:
        self._end_execution = end_execution
        self.permissions = hikari.Permissions(permissions)

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        result = (self.permissions & await self.get_permissions(ctx)) == self.permissions

        if self._end_execution and not result:
            raise errors.HaltExecutionSearch

        return result

    @abc.abstractmethod
    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> hikari.Permissions:
        raise NotImplementedError


class AuthorPermissionCheck(PermissionCheck):
    __slots__: tuple[str, ...] = ()

    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> hikari.Permissions:
        if not ctx.member:
            return utilities.ALL_PERMISSIONS

        elif isinstance(ctx.member, hikari.InteractionMember):
            return ctx.member.permissions

        return await utilities.fetch_permissions(ctx.client, ctx.member, channel=ctx.channel_id)


class OwnPermissionsCheck(PermissionCheck):
    __slots__: tuple[str, ...] = ("_lock", "_me")

    def __init__(self, permissions: typing.Union[hikari.Permissions, int], /, *, end_execution: bool = False) -> None:
        super().__init__(permissions, end_execution=end_execution)
        self._lock = asyncio.Lock()
        self._me: typing.Optional[hikari.User] = None

    async def get_permissions(self, ctx: tanjun_traits.Context, /) -> hikari.Permissions:
        if ctx.guild_id is None:
            return utilities.ALL_PERMISSIONS

        member = await self._get_member(ctx, ctx.guild_id)
        return await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

    async def _get_member(self, ctx: tanjun_traits.Context, guild_id: hikari.Snowflake, /) -> hikari.Member:
        user = await self._get_user(ctx.client.cache, ctx.client.rest)

        if ctx.client.cache and (member := ctx.client.cache.get_member(guild_id, user.id)):
            return member

        retry = backoff.Backoff(maximum=5, max_retries=4)
        return await utilities.fetch_resource(retry, ctx.client.rest.fetch_member, guild_id, user.id)

    async def _get_user(self, cache: typing.Optional[hikari.api.Cache], rest: hikari.api.RESTClient, /) -> hikari.User:
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


@typing.overload
def with_dm_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_dm_check(*, end_execution: bool = False) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_dm_check(
    command: typing.Optional[CommandT] = None, /, *, end_execution: bool = False
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a DM channel.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    !!! note
        For more information on how this is used with other parameters see
        `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, dm_check, end_execution=end_execution)


@typing.overload
def with_guild_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_guild_check(*, end_execution: bool = False) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_guild_check(
    command: typing.Optional[CommandT] = None, /, *, end_execution: bool = False
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a guild channel.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    !!! note
        For more information on how this is used with other parameters see
        `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, guild_check, end_execution=end_execution)


@typing.overload
def with_nsfw_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_nsfw_check(*, end_execution: bool = False) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_nsfw_check(
    command: typing.Optional[CommandT] = None, /, *, end_execution: bool = False
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a channel that's marked as nsfw.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    !!! note
        For more information on how this is used with other parameters see
        `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, nsfw_check, end_execution=end_execution)


@typing.overload
def with_sfw_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_sfw_check(*, end_execution: bool = False) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_sfw_check(
    command: typing.Optional[CommandT] = None, /, *, end_execution: bool = False
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a channel that's marked as sfw.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    !!! note
        For more information on how this is used with other parameters see
        `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, sfw_check, end_execution=end_execution)


@typing.overload
def with_owner_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_owner_check(
    *,
    end_execution: bool = False,
    expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
    owner_ids: typing.Optional[collections.Iterable[hikari.SnowflakeishOr[hikari.User]]] = None,
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_owner_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    end_execution: bool = False,
    expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
    owner_ids: typing.Optional[collections.Iterable[hikari.SnowflakeishOr[hikari.User]]] = None,
) -> CallbackReturnT[CommandT]:
    """Only let a command run if it's being triggered by one of the bot's owners.

    !!! note
        This is based on the owner(s) of the bot's application and will account
        for team owners as well.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.
    expire_delta: datetime.timedelta
        How long cached application owner data should be cached for.

        Defaults to 5 minutes.
    owner_ids: typing.Optional[collections.abc.Iterable[hikari.snowflakes.SonwflakeishOr[hikari.users.User]]]
        Iterable of objects and IDs of other users to explicitly mark as owners
        for this check.

        !!! note
            This will be used alongside the application's owners.

    !!! note
        For more information on how this is used with other parameters see
        `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(
        command, ApplicationOwnerCheck(end_execution=end_execution, expire_delta=expire_delta, owner_ids=owner_ids)
    )


def with_author_permission_check(
    permissions: typing.Union[hikari.Permissions, int], *, end_execution: bool = False
) -> collections.Callable[[CommandT], CommandT]:
    """Only let a command run if the author has certain permissions in the current channel.

    !!! note
        This will only pass for commands in DMs if `permissions` is valid for
        a DM context (e.g. can't have any moderation permissions)

    Parameters
    ----------
    permissions: typing.Union[hikari.permissions.Permissions, int]
        The permission(s) required for this command to run.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    collections.abc.Callable[[CommandT], CommandT]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(AuthorPermissionCheck(permissions, end_execution=end_execution))


def with_own_permission_check(
    permissions: typing.Union[hikari.Permissions, int], *, end_execution: bool = False
) -> collections.Callable[[CommandT], CommandT]:
    """Only let a command run if we have certain permissions in the current channel.

    !!! note
        This will only pass for commands in DMs if `permissions` is valid for
        a DM context (e.g. can't have any moderation permissions)

    Parameters
    ----------
    permissions: typing.Union[hikari.permissions.Permissions, int]
        The permission(s) required for this command to run.

    Other Parameters
    ----------------
    end_execution: bool
        Whether this check should raise `tanjun.errors.HaltExecutionSearch` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    collections.abc.Callable[[CommandT], CommandT]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(OwnPermissionsCheck(permissions, end_execution=end_execution))


def with_check(check: tanjun_traits.CheckSig, /) -> collections.Callable[[CommandT], CommandT]:
    """Add a generic check to a command.

    Parameters
    ----------
    check : tanjun.traits.CheckSig
        The check to add to this command.

    Returns
    -------
    collections.abc.Callable[[CommandT], CommandT]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(check)
