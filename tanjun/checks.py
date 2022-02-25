# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2022, Faster Speeding
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
    "AuthorPermissionCheck",
    "DmCheck",
    "GuildCheck",
    "NsfwCheck",
    "OwnPermissionCheck",
    "OwnerCheck",
    "SfwCheck",
    "all_checks",
    "any_checks",
    "with_all_checks",
    "with_any_checks",
    "with_author_permission_check",
    "with_check",
    "with_dm_check",
    "with_guild_check",
    "with_nsfw_check",
    "with_own_permission_check",
    "with_owner_check",
    "with_sfw_check",
]

import typing
from collections import abc as collections

import alluka
import hikari

from . import abc as tanjun_abc
from . import dependencies
from . import errors
from . import utilities

_CommandT = typing.TypeVar("_CommandT", bound="tanjun_abc.ExecutableCommand[typing.Any]")
# This errors on earlier 3.9 releases when not quotes cause dumb handling of the [_CommandT] list
_CallbackReturnT = typing.Union[_CommandT, "collections.Callable[[_CommandT], _CommandT]"]


def _optional_kwargs(
    command: typing.Optional[_CommandT], check: tanjun_abc.CheckSig, /
) -> typing.Union[_CommandT, collections.Callable[[_CommandT], _CommandT]]:
    if command:
        return command.add_check(check)

    return lambda c: c.add_check(check)


class _Check:
    __slots__ = ("_error_message", "_halt_execution", "__weakref__")

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
    """Standard owner check callback registered by `with_owner_check`.

    This check will only pass if the author of the command is a bot owner.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = "Only bot owners can use this command",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a owner check.

        .. note::
            error_message takes priority over halt_execution.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "Only bot owners can use this command" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        dependency: dependencies.AbstractOwners = alluka.inject(type=dependencies.AbstractOwners),
    ) -> bool:
        return self._handle_result(await dependency.check_ownership(ctx.client, ctx.author))


_GuildChannelCacheT = typing.Optional[dependencies.SfCache[hikari.GuildChannel]]


async def _get_is_nsfw(
    ctx: tanjun_abc.Context,
    /,
    *,
    dm_default: bool,
    channel_cache: _GuildChannelCacheT,
) -> bool:
    if ctx.guild_id is None:
        return dm_default

    channel: typing.Optional[hikari.PartialChannel] = None
    if ctx.cache and (channel := ctx.cache.get_guild_channel(ctx.channel_id)):
        return channel.is_nsfw or False

    if channel_cache:
        try:
            return (await channel_cache.get(ctx.channel_id)).is_nsfw or False

        except dependencies.EntryNotFound:
            raise

        except dependencies.CacheMissError:
            pass

    channel = await ctx.rest.fetch_channel(ctx.channel_id)
    assert isinstance(channel, hikari.GuildChannel)
    return channel.is_nsfw or False


class NsfwCheck(_Check):
    """Standard NSFW check callback registered by `with_nsfw_check`.

    This check will only pass if the current channel is NSFW.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a NSFW check.

        .. note::
            error_message takes priority over halt_execution.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "Command can only be used in NSFW channels" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        /,
        channel_cache: _GuildChannelCacheT = alluka.inject(type=_GuildChannelCacheT),
    ) -> bool:
        return self._handle_result(await _get_is_nsfw(ctx, dm_default=True, channel_cache=channel_cache))


class SfwCheck(_Check):
    """Standard SFW check callback registered by `with_sfw_check`.

    This check will only pass if the current channel is SFW.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = "Command can only be used in SFW channels",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a SFW check.

        .. note::
            error_message takes priority over halt_execution.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "Command can only be used in SFW channels" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        /,
        channel_cache: _GuildChannelCacheT = alluka.inject(type=_GuildChannelCacheT),
    ) -> bool:
        return self._handle_result(not await _get_is_nsfw(ctx, dm_default=False, channel_cache=channel_cache))


class DmCheck(_Check):
    """Standard DM check callback registered by `with_dm_check`.

    This check will only pass if the current channel is a DM channel.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = "Command can only be used in DMs",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a DM check.

        .. note::
            error_message takes priority over halt_execution.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "Command can only be used in DMs" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message, halt_execution)

    def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return self._handle_result(ctx.guild_id is None)


class GuildCheck(_Check):
    """Standard guild check callback registered by `with_guild_check`.

    This check will only pass if the current channel is in a guild.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error_message: typing.Optional[str] = "Command can only be used in guild channels",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a guild check.

        .. note::
            error_message takes priority over halt_execution.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "Command can only be used in guild channels" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message, halt_execution)

    def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        return self._handle_result(ctx.guild_id is not None)


class AuthorPermissionCheck(_Check):
    """Standard author permission check callback registered by `with_author_permission_check`.

    This check will only pass if the current author has the specified permission.
    """

    __slots__ = ("_permissions",)

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = "You don't have the permissions required to use this command",
        halt_execution: bool = False,
    ) -> None:
        """Initialise an author permission check.

        .. note::
            error_message takes priority over halt_execution.

        Parameters
        ----------
        permissions: hikari.Permissions | int
            The permission(s) required for this command to run.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "You don't have the permissions required to use this command" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message=error_message, halt_execution=halt_execution)
        self._permissions = permissions

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        if not ctx.member:
            # If there's no member when this is within a guild then it's likely
            # something like a webhook or guild visitor with no real permissions
            # outside of some basic set of send messages.
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

        return self._handle_result((self._permissions & permissions) == self._permissions)


class OwnPermissionCheck(_Check):
    """Standard own permission check callback registered by `with_own_permission_check`.

    This check will only pass if the current bot user has the specified permission.
    """

    __slots__ = ("_permissions",)

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error_message: typing.Optional[str] = "Bot doesn't have the permissions required to run this command",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a own permission check.

        .. note::
            error_message takes priority over halt_execution.

        Parameters
        ----------
        permissions: hikari.Permissions | int
            The permission(s) required for this command to run.

        Other Parameters
        ----------------
        error_message : str | None
            The error message to send in response as a command error if the check fails.

            Defaults to "Bot doesn't have the permissions required to run this command" and setting this to `None`
            will disable the error message allowing the command search to continue.
        halt_execution : bool
            Whether this check should raise `tanjun.errors.HaltExecution` to
            end the execution search when it fails instead of returning `False`.

            Defaults to `False`.
        """
        super().__init__(error_message=error_message, halt_execution=halt_execution)
        self._permissions = permissions

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        /,
        my_user: hikari.OwnUser = dependencies.inject_lc(hikari.OwnUser),
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
                # is still in there and that we likely won't be able to do anything.
                # TODO: re-visit this later.
                return self._handle_result(False)

            permissions = await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        return self._handle_result((permissions & self._permissions) == self._permissions)


@typing.overload
def with_dm_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_dm_check(
    *, error_message: typing.Optional[str] = "Command can only be used in DMs", halt_execution: bool = False
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_dm_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in DMs",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a DM channel.

    .. note::
        `error_message` takes priority over `halt_execution`.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in DMs" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, DmCheck(halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_guild_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_guild_check(
    *, error_message: typing.Optional[str] = "Command can only be used in guild channels", halt_execution: bool = False
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_guild_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in guild channels",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a guild channel.

    .. note::
        `error_message` takes priority over `halt_execution`.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in guild channels" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    tanjun.abc.ExecutableCommanmd
        The command this check was added to.
    """
    return _optional_kwargs(command, GuildCheck(halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_nsfw_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_nsfw_check(
    *, error_message: typing.Optional[str] = "Command can only be used in NSFW channels", halt_execution: bool = False
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_nsfw_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a channel that's marked as nsfw.

    .. note::
        `error_message` takes priority over `halt_execution`.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in NSFW channels" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, NsfwCheck(halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_sfw_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_sfw_check(
    *,
    error_message: typing.Optional[str] = "Command can only be used in SFW channels",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_sfw_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Command can only be used in SFW channels",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a channel that's marked as sfw.

    .. note::
        `error_message` takes priority over `halt_execution`.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        Defaults to "Command can only be used in SFW channels" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, SfwCheck(halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_owner_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_owner_check(
    *,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_owner_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run if it's being triggered by one of the bot's owners.

    .. note::
        `error_message` takes priority over `halt_execution`.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.

    Other Parameters
    ----------------
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        Defaults to "Only bot owners can use this command" and setting this to `None`
        will disable the error message allowing the command search to continue.
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, OwnerCheck(halt_execution=halt_execution, error_message=error_message))


def with_author_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error_message: typing.Optional[str] = "You don't have the permissions required to use this command",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Only let a command run if the author has certain permissions in the current channel.

    Parameters
    ----------
    permissions: hikari.Permissions | int
        The permission(s) required for this command to run.

    Other Parameters
    ----------------
    error_message : str | None
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
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
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
) -> collections.Callable[[_CommandT], _CommandT]:
    """Only let a command run if we have certain permissions in the current channel.

    Parameters
    ----------
    permissions: hikari.Permissions | int
        The permission(s) required for this command to run.

    Other Parameters
    ----------------
    error_message : str | None
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
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(
        OwnPermissionCheck(permissions, halt_execution=halt_execution, error_message=error_message)
    )


def with_check(check: tanjun_abc.CheckSig, /) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a generic check to a command.

    Parameters
    ----------
    check : tanjun.abc.CheckSig
        The check to add to this command.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(check)


class _AllChecks(_Check):
    __slots__ = ("_checks",)

    def __init__(self, checks: list[tanjun_abc.CheckSig]) -> None:
        self._checks = checks

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        for check in self._checks:
            if not await ctx.call_with_async_di(check, ctx):
                return False

        return True


def all_checks(
    check: tanjun_abc.CheckSig,
    /,
    *checks: tanjun_abc.CheckSig,
) -> collections.Callable[[tanjun_abc.Context], collections.Coroutine[typing.Any, typing.Any, bool]]:
    """Combine multiple check callbacks into a check which will only pass if all the callbacks pass.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check : typing_abc.CheckSig
        The first check callback to combine.
    *checks : typing_abc.CheckSig
        Additional check callbacks to combine.

    Returns
    -------
    collections.abc.Callable[[tanjun_abc.Context], collections.abc.Coroutine[typing.Any, typing.Any, bool]]
        A check which will pass if all of the provided check callbacks pass.
    """
    return _AllChecks([check, *checks])


def with_all_checks(
    check: tanjun_abc.CheckSig,
    /,
    *checks: tanjun_abc.CheckSig,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a check which will pass if all the provided checks pass through a decorator call.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check : typing_abc.CheckSig
        The first check callback to combine.
    *checks : typing_abc.CheckSig
        Additional check callbacks to combine.

    Returns
    -------
    collections.abc.Callable[[tanjun_abc.Context], collections.abc.Coroutine[typing.Any, typing.Any, bool]]
        A check which will pass if all of the provided check callbacks pass.
    """
    return lambda c: c.add_check(all_checks(check, *checks))


class _AnyChecks(_Check):
    __slots__ = ("_checks", "_suppress", "_error_message", "_halt_execution")

    def __init__(
        self,
        checks: list[tanjun_abc.CheckSig],
        suppress: tuple[type[Exception], ...],
        error_message: typing.Optional[str],
        halt_execution: bool,
    ) -> None:
        self._checks = checks
        self._suppress = suppress
        self._error_message = error_message
        self._halt_execution = halt_execution

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        for check in self._checks:
            try:
                if await ctx.call_with_async_di(check, ctx):
                    return True

            except errors.FailedCheck:
                pass

            except self._suppress:
                pass

        if self._error_message is not None:
            raise errors.CommandError(self._error_message)
        if self._halt_execution:
            raise errors.HaltExecution

        return False


def any_checks(
    check: tanjun_abc.CheckSig,
    /,
    *checks: tanjun_abc.CheckSig,
    suppress: tuple[type[Exception], ...] = (errors.CommandError, errors.HaltExecution),
    error_message: typing.Optional[str],
    halt_execution: bool = False,
) -> collections.Callable[[tanjun_abc.Context], collections.Coroutine[typing.Any, typing.Any, bool]]:
    """Combine multiple checks into a check which'll pass if any of the callbacks pass.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check : typing_abc.CheckSig
        The first check callback to combine.
    *checks : typing_abc.CheckSig
        Additional check callbacks to combine.
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        This takes priority over `halt_execution`.

    Other Parameters
    ----------------
    suppress : tuple[type[Exception], ...]
        Tuple of the exceptions to suppress when a check fails.

        Defaults to (`tanjun.errors.CommandError`, `tanjun.errors.HaltExecution`).
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    collections.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A decorator which adds the generated check to a command.
    """
    return _AnyChecks([check, *checks], suppress, error_message, halt_execution)


def with_any_checks(
    check: tanjun_abc.CheckSig,
    /,
    *checks: tanjun_abc.CheckSig,
    suppress: tuple[type[Exception], ...] = (errors.CommandError, errors.HaltExecution),
    error_message: typing.Optional[str],
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a check which'll pass if any of the provided checks pass through a decorator call.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check : typing_abc.CheckSig
        The first check callback to combine.
    *checks : typing_abc.CheckSig
        Additional check callbacks to combine.
    error_message : str | None
        The error message to send in response as a command error if the check fails.

        This takes priority over `halt_execution`.

    Other Parameters
    ----------------
    suppress : tuple[type[Exception], ...]
        Tuple of the exceptions to suppress when a check fails.

        Defaults to (`tanjun.errors.CommandError`, `tanjun.errors.HaltExecution`).
    halt_execution : bool
        Whether this check should raise `tanjun.errors.HaltExecution` to
        end the execution search when it fails instead of returning `False`.

        Defaults to `False`.

    Returns
    -------
    collections.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A decorator which adds the generated check to a command.
    """
    return lambda c: c.add_check(
        any_checks(check, *checks, suppress=suppress, error_message=error_message, halt_execution=halt_execution)
    )
