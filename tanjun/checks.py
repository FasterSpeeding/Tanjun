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
    "OwnerCheck",
    "NsfwCheck",
    "SfwCheck",
    "DmCheck",
    "GuildCheck",
    "AuthorPermissionCheck",
    "OwnPermissionCheck",
    "with_check",
    "with_dm_check",
    "with_guild_check",
    "with_nsfw_check",
    "with_sfw_check",
    "with_owner_check",
    "with_author_permission_check",
    "with_own_permission_check",
]

import typing
from collections import abc as collections

import hikari

from . import dependencies
from . import errors
from . import injecting
from . import utilities

if typing.TYPE_CHECKING:
    from . import abc as tanjun_abc


CommandT = typing.TypeVar("CommandT", bound="tanjun_abc.ExecutableCommand[typing.Any]")
# This errors on earlier 3.9 releases when not quotes cause dumb handling of the [CommandT] list
CallbackReturnT = typing.Union[CommandT, "collections.Callable[[CommandT], CommandT]"]
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
        if result := await self.descriptor.resolve_with_command_context(ctx, ctx):
            return result

        raise errors.FailedCheck


def _optional_kwargs(
    command: typing.Optional[CommandT], check: tanjun_abc.CheckSig, /
) -> typing.Union[CommandT, collections.Callable[[CommandT], CommandT]]:
    if command:
        return command.add_check(check)

    return lambda c: c.add_check(check)


class _Check:
    __slots__ = ("_error_message", "_halt_execution")

    def __init__(
        self,
        error_message: typing.Optional[str],
        halt_execution: bool,
    ) -> None:
        self._error_message = error_message
        self._halt_execution = halt_execution

    def _handle_result(self, result: bool) -> bool:
        if not result:
            if self._error_message:
                raise errors.CommandError(self._error_message) from None
            if self._halt_execution:
                raise errors.HaltExecution from None

        return result


class OwnerCheck(_Check):
    __slots__ = ()

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = "Only bot owners can use this command",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        dependency: dependencies.AbstractOwnerCheck = injecting.injected(type=dependencies.AbstractOwnerCheck),
    ) -> bool:
        return self._handle_result(await dependency.check_ownership(ctx.client, ctx.author))


async def _get_is_nsfw(ctx: tanjun_abc.Context, /, *, dm_default: bool) -> bool:
    channel: typing.Optional[hikari.PartialChannel] = None
    if ctx.cache and (channel := ctx.cache.get_guild_channel(ctx.channel_id)):
        return channel.is_nsfw or False

    channel = await ctx.rest.fetch_channel(ctx.channel_id)
    return channel.is_nsfw or False if isinstance(channel, hikari.GuildChannel) else dm_default


class NsfwCheck(_Check):
    __slots__ = ()

    def __init__(
        self,
        error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message, halt_execution)

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return self._handle_result(await _get_is_nsfw(ctx, dm_default=True))


class SfwCheck(_Check):
    __slots__ = ()

    def __init__(
        self,
        error_message: typing.Optional[str] = "Command can only be used in SFW channels",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message, halt_execution)

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return self._handle_result(not await _get_is_nsfw(ctx, dm_default=False))


class DmCheck(_Check):
    __slots__ = ()

    def __init__(
        self,
        error_message: typing.Optional[str] = "Command can only be used in DMs",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message, halt_execution)

    def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return self._handle_result(ctx.guild_id is None)


class GuildCheck(_Check):
    __slots__ = ()

    def __init__(
        self,
        error_message: typing.Optional[str] = "Command can only be used in guild channels",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message, halt_execution)

    def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return self._handle_result(ctx.guild_id is not None)


class AuthorPermissionCheck(_Check):
    __slots__ = ("permissions",)

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = "You don't have the permissions required to use this command",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message=error_message, halt_execution=halt_execution)
        self.permissions = permissions

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        if not ctx.member:
            # If there's no member when this is within a guild then it's likely
            # something like a webhook or guild visitor with no real permissions
            # outside of some basic set of send messages
            if ctx.guild_id:
                permissions = await utilities.fetch_everyone_permissions(
                    ctx.client, ctx.guild_id, channel=ctx.channel_id
                )

            else:
                permissions = utilities.DM_PERMISSIONS

        elif isinstance(ctx.member, hikari.InteractionMember):
            permissions = ctx.member.permissions

        else:
            permissions = await utilities.fetch_permissions(ctx.client, ctx.member, channel=ctx.channel_id)

        return self._handle_result((self.permissions & permissions) == self.permissions)


class OwnPermissionCheck(_Check):
    __slots__ = ("permissions",)

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = "Bot doesn't have the permissions required to run this command",
        halt_execution: bool = False,
    ) -> None:
        super().__init__(error_message=error_message, halt_execution=halt_execution)
        self.permissions = permissions

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        /,
        my_user: hikari.OwnUser = injecting.injected(callback=dependencies.make_lc_resolver(hikari.OwnUser)),
    ) -> bool:
        if ctx.guild_id is None:
            permissions = utilities.DM_PERMISSIONS

        elif ctx.cache and (member := ctx.cache.get_member(ctx.guild_id, my_user)):
            permissions = await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        else:
            try:
                member = await ctx.rest.fetch_member(ctx.guild_id, my_user.id)

            except hikari.NotFoundError:
                # If we're not in the Guild then we have to assume the application
                # if still in there and that we likely won't be able to do anything.
                # TODO: re-visit this later.
                return self._handle_result(False)

            permissions = await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        return self._handle_result((permissions & self.permissions) == self.permissions)


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
    return _optional_kwargs(command, DmCheck(halt_execution=halt_execution, error_message=error_message))


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
    return _optional_kwargs(command, GuildCheck(halt_execution=halt_execution, error_message=error_message))


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
    return _optional_kwargs(command, NsfwCheck(halt_execution=halt_execution, error_message=error_message))


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
    return _optional_kwargs(command, SfwCheck(halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_owner_check(command: CommandT, /) -> CommandT:
    ...


@typing.overload
def with_owner_check(
    *,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    halt_execution: bool = False,
) -> collections.Callable[[CommandT], CommandT]:
    ...


def with_owner_check(
    command: typing.Optional[CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    halt_execution: bool = False,
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
    return _optional_kwargs(command, OwnerCheck(halt_execution=halt_execution, error_message=error_message))


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
        OwnPermissionCheck(permissions, halt_execution=halt_execution, error_message=error_message)
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
