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
    "ApplicationOwnerCheck",
    "nsfw_check",
    "sfw_check",
    "dm_check",
    "guild_check",
    "PermissionCheck",
    "AuthorPermissionCheck",
    "OwnPermissionsCheck",
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
import dataclasses
import datetime
import time
import typing
from collections import abc as collections

import hikari

from . import _backoff as backoff
from . import errors
from . import injecting
from . import utilities

if typing.TYPE_CHECKING:
    from . import abc as tanjun_abc


CommandT = typing.TypeVar("CommandT", bound="tanjun_abc.ExecutableCommand[typing.Any]")
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
@with_dm_check(halt_execution=True)
@as_command("foo")
def foo_command(self, ctx: Context) -> None:
    raise NotImplemented
```
"""


class InjectableCheck(injecting.BaseInjectableCallback[bool]):
    __slots__ = ()

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return await self.descriptor.resolve_with_command_context(ctx, ctx)


@dataclasses.dataclass(frozen=True)
class _WrappedKwargs:
    callback: tanjun_abc.CheckSig
    _kwargs: dict[str, typing.Any]

    def __call__(self, ctx: tanjun_abc.Context, /) -> tanjun_abc.MaybeAwaitableT[bool]:
        return self.callback(ctx, **self._kwargs)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __eq__(self, other: typing.Any) -> bool:
        return bool(self.callback == other)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __hash__(self) -> int:
        return hash(self.callback)


def _wrap_with_kwargs(
    command: typing.Optional[CommandT],
    callback: tanjun_abc.CheckSig,
    /,
    **kwargs: typing.Any,
) -> CallbackReturnT[CommandT]:
    if command:
        if kwargs:
            return command.add_check(_WrappedKwargs(callback, kwargs))

        return command.add_check(callback)

    return lambda command_: command_.add_check(_WrappedKwargs(callback, kwargs))


def _handle_result(value: bool, error_message: typing.Optional[str], halt_execution: bool, /) -> bool:
    if not value:
        if error_message:
            raise errors.CommandError(error_message)
        if halt_execution:
            raise errors.HaltExecution

    return value


class ApplicationOwnerCheck:
    __slots__ = ("_application", "_error_message", "_expire", "_halt_execution", "_lock", "_owner_ids", "_time")

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = None,
        expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
        halt_execution: bool = False,
        owner_ids: typing.Optional[collections.Iterable[hikari.SnowflakeishOr[hikari.User]]] = None,
    ) -> None:
        self._application: typing.Optional[hikari.Application] = None
        self._error_message = error_message
        self._expire = expire_delta.total_seconds()
        self._halt_execution = halt_execution
        self._lock = asyncio.Lock()
        self._owner_ids = tuple(hikari.Snowflake(id_) for id_ in owner_ids) if owner_ids else ()
        self._time = 0.0

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
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

    async def _get_application(self, ctx: tanjun_abc.Context, /) -> hikari.Application:
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
        client: tanjun_abc.Client,
        /,
        *,
        timeout: typing.Optional[datetime.timedelta] = datetime.timedelta(seconds=30),
    ) -> None:
        try:
            await self.update(client.rest, timeout=timeout)

        except asyncio.TimeoutError:
            pass

    async def check(self, ctx: tanjun_abc.Context, /) -> bool:
        if ctx.author.id in self._owner_ids:
            return True

        application = await self._get_application(ctx)

        if application.team:
            result = ctx.author.id in application.team.members

        else:
            result = ctx.author.id == application.owner.id

        return _handle_result(result, self._error_message, self._halt_execution)

    async def update(
        self,
        rest: hikari.api.RESTClient,
        /,
        *,
        timeout: typing.Optional[datetime.timedelta] = datetime.timedelta(seconds=30),
    ) -> None:
        self._time = time.perf_counter()
        await asyncio.wait_for(self._try_fetch(rest), timeout.total_seconds() if timeout else None)


async def _get_is_nsfw(ctx: tanjun_abc.Context, /) -> bool:
    channel: typing.Optional[hikari.PartialChannel] = None
    if ctx.client.cache:
        channel = ctx.client.cache.get_guild_channel(ctx.channel_id)

    if not channel:
        retry = backoff.Backoff(maximum=5, max_retries=4)
        channel = await utilities.fetch_resource(retry, ctx.client.rest.fetch_channel, ctx.channel_id)

    return channel.is_nsfw or False if isinstance(channel, hikari.GuildChannel) else True


async def nsfw_check(
    ctx: tanjun_abc.Context,
    /,
    *,
    error_message: typing.Optional[str] = None,
    halt_execution: bool = False,
) -> bool:

    return _handle_result(await _get_is_nsfw(ctx), error_message, halt_execution)


async def sfw_check(
    ctx: tanjun_abc.Context,
    /,
    *,
    error_message: typing.Optional[str] = None,
    halt_execution: bool = False,
) -> bool:
    return _handle_result(not await _get_is_nsfw(ctx), error_message, halt_execution)


def dm_check(
    ctx: tanjun_abc.Context,
    /,
    *,
    error_message: typing.Optional[str] = None,
    halt_execution: bool = False,
) -> bool:
    return _handle_result(ctx.guild_id is None, error_message, halt_execution)


def guild_check(
    ctx: tanjun_abc.Context,
    /,
    *,
    error_message: typing.Optional[str] = None,
    halt_execution: bool = False,
) -> bool:
    return _handle_result(ctx.guild_id is not None, error_message, halt_execution)


class PermissionCheck(abc.ABC):
    __slots__ = ("_halt_execution", "_error_message", "permissions")

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = None,
        halt_execution: bool = False,
    ) -> None:
        self._halt_execution = halt_execution
        self._error_message = error_message
        self.permissions = hikari.Permissions(permissions)

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        result = (self.permissions & await self.get_permissions(ctx)) == self.permissions
        return _handle_result(result, self._error_message, self._halt_execution)

    @abc.abstractmethod
    async def get_permissions(self, ctx: tanjun_abc.Context, /) -> hikari.Permissions:
        raise NotImplementedError


class AuthorPermissionCheck(PermissionCheck):
    __slots__ = ()

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = None,
        halt_execution: bool = False,
    ) -> None:
        super().__init__(permissions, error_message=error_message, halt_execution=halt_execution)

    async def get_permissions(self, ctx: tanjun_abc.Context, /) -> hikari.Permissions:
        if not ctx.member:
            # If there's no member when this is within a guild then it's likely
            # something like a webhook or guild visitor with no real permissions
            # outside of some basic set of send messages
            if ctx.guild_id:
                return await utilities.fetch_everyone_permissions(ctx.client, ctx.guild_id, channel=ctx.channel_id)

            return utilities.DM_PERMISSIONS

        if isinstance(ctx.member, hikari.InteractionMember):
            return ctx.member.permissions

        return await utilities.fetch_permissions(ctx.client, ctx.member, channel=ctx.channel_id)


class OwnPermissionsCheck(PermissionCheck):
    __slots__ = ("_lock", "_me")

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = None,
        halt_execution: bool = False,
    ) -> None:
        super().__init__(permissions, error_message=error_message, halt_execution=halt_execution)
        self._lock = asyncio.Lock()
        self._me: typing.Optional[hikari.User] = None

    async def get_permissions(self, ctx: tanjun_abc.Context, /) -> hikari.Permissions:
        if ctx.guild_id is None:
            return utilities.DM_PERMISSIONS

        member = await self._get_member(ctx, ctx.guild_id)
        return await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

    async def _get_member(self, ctx: tanjun_abc.Context, guild_id: hikari.Snowflake, /) -> hikari.Member:
        user = self._me or await self._get_user(ctx.client.cache, ctx.client.rest)

        if ctx.client.cache and (member := ctx.client.cache.get_member(guild_id, user.id)):
            return member

        retry = backoff.Backoff(maximum=5, max_retries=4)
        return await utilities.fetch_resource(retry, ctx.client.rest.fetch_member, guild_id, user.id)

    async def _get_user(self, cache: typing.Optional[hikari.api.Cache], rest: hikari.api.RESTClient, /) -> hikari.User:
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
def with_dm_check(
    *, error_message: typing.Optional[str] = "Command can only be used in DMs", halt_execution: bool = False
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_dm_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in DMs",
    halt_execution: bool = False,
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a DM channel.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in DMs" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Notes
    -----
    * error_message takes priority over halt_execution.
    * For more information on how this is used with other parameters see
      `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, dm_check, halt_execution=halt_execution, error_message=error_message)


@typing.overload
def with_guild_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_guild_check(
    *, error_message: typing.Optional[str] = "Command can only be used in guild channels", halt_execution: bool = False
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_guild_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in guild channels",
    halt_execution: bool = False,
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a guild channel.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in guild channels" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Notes
    -----
    * error_message takes priority over halt_execution.
    * For more information on how this is used with other parameters see
      `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, guild_check, halt_execution=halt_execution, error_message=error_message)


@typing.overload
def with_nsfw_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_nsfw_check(
    *, error_message: typing.Optional[str] = "Command can only be used in NSFW channels", halt_execution: bool = False
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_nsfw_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
    halt_execution: bool = False,
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a channel that's marked as nsfw.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in NSFW channels" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Notes
    -----
    * error_message takes priority over halt_execution.
    * For more information on how this is used with other parameters see
      `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, nsfw_check, halt_execution=halt_execution, error_message=error_message)


@typing.overload
def with_sfw_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_sfw_check(
    *,
    error_message: typing.Optional[str] = "Command can only be used in SFW channels",
    halt_execution: bool = False,
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_sfw_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in SFW channels",
    halt_execution: bool = False,
) -> CallbackReturnT[CommandT]:
    """Only let a command run in a channel that's marked as sfw.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in SFW channels" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Notes
    -----
    * error_message takes priority over halt_execution.
    * For more information on how this is used with other parameters see
      `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(command, sfw_check, halt_execution=halt_execution, error_message=error_message)


@typing.overload
def with_owner_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_owner_check(
    *,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
    halt_execution: bool = False,
    owner_ids: typing.Optional[collections.Iterable[hikari.SnowflakeishOr[hikari.User]]] = None,
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_owner_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    expire_delta: datetime.timedelta = datetime.timedelta(minutes=5),
    halt_execution: bool = False,
    owner_ids: typing.Optional[collections.Iterable[hikari.SnowflakeishOr[hikari.User]]] = None,
) -> CallbackReturnT[CommandT]:
    """Only let a command run if it's being triggered by one of the bot's owners.

    Parameters
    ----------
    command : typing.Optional[CommandT]
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "Only bot owners can use this command" and setting this to `None`
        will disable the error message allowing the command search to continue.
    expire_delta: datetime.timedelta
        How long cached application owner data should be cached for.

        Defaults to 5 minutes.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.
    owner_ids: typing.Optional[collections.abc.Iterable[hikari.snowflakes.SonwflakeishOr[hikari.users.User]]]
        Iterable of objects and IDs of other users to explicitly mark as owners
        for this check.

    Notes
    -----
    * Any provided `owner_ids` will be used alongside the application's owners.
    * This is based on the owner(s) of the bot's application and will account
      for team owners as well.
    * error_message takes priority over halt_execution.
    * For more information on how this is used with other parameters see
      `CallbackReturnT`.

    Returns
    -------
    CallbackReturnT[CommandT]
        The command this check was added to.
    """
    return _wrap_with_kwargs(
        command,
        ApplicationOwnerCheck(
            halt_execution=halt_execution, error_message=error_message, expire_delta=expire_delta, owner_ids=owner_ids
        ),
    )


def with_author_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error_message: typing.Optional[str] = "You don't have the permissions required to use this command",
    halt_execution: bool = False,
) -> collections.Callable[[CommandT], CommandT]:
    """Only let a command run if the author has certain permissions in the current channel.

    Parameters
    ----------
    permissions: typing.Union[hikari.permissions.Permissions, int]
        The permission(s) required for this command to run.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "You don't have the permissions required to use this command" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Notes
    -----
    * error_message takes priority over halt_execution.
    * This will only pass for commands in DMs if `permissions` is valid for
      a DM context (e.g. can't have any moderation permissions)

    Returns
    -------
    collections.abc.Callable[[CommandT], CommandT]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(
        AuthorPermissionCheck(permissions, halt_execution=halt_execution, error_message=error_message)
    )


def with_own_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error_message: typing.Optional[str] = "Bot doesn't have the permissions required to run this command",
    halt_execution: bool = False,
) -> collections.Callable[[CommandT], CommandT]:
    """Only let a command run if we have certain permissions in the current channel.

    Parameters
    ----------
    permissions: typing.Union[hikari.permissions.Permissions, int]
        The permission(s) required for this command to run.

    Other Parameters
    ----------------
    error_message : typing.Optional[str]
        The error message to send in response as a command error if the check fails.

        Defaults to "Bot doesn't have the permissions required to run this command" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Notes
    -----
    * error_message takes priority over halt_execution.
    * This will only pass for commands in DMs if `permissions` is valid for
      a DM context (e.g. can't have any moderation permissions)

    Returns
    -------
    collections.abc.Callable[[CommandT], CommandT]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(
        OwnPermissionsCheck(permissions, halt_execution=halt_execution, error_message=error_message)
    )


def with_check(check: tanjun_abc.CheckSig, /) -> collections.Callable[[CommandT], CommandT]:
    """Add a generic check to a command.

    Parameters
    ----------
    check : tanjun.abc.CheckSig
        The check to add to this command.

    Returns
    -------
    collections.abc.Callable[[CommandT], CommandT]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(check)
