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

from . import abc as tanjun
from . import dependencies
from . import errors
from . import utilities

_CommandT = typing.TypeVar("_CommandT", bound="tanjun.ExecutableCommand[typing.Any]")
# This errors on earlier 3.9 releases when not quotes cause dumb handling of the [_CommandT] list
_CallbackReturnT = typing.Union[_CommandT, "collections.Callable[[_CommandT], _CommandT]"]


def _optional_kwargs(
    command: typing.Optional[_CommandT], check: tanjun.CheckSig, /
) -> typing.Union[_CommandT, collections.Callable[[_CommandT], _CommandT]]:
    if command:
        return command.add_check(check)

    return lambda c: c.add_check(check)


class _Check:
    __slots__ = ("_error", "_error_message", "_halt_execution", "__weakref__")

    def __init__(
        self,
        error: typing.Optional[collections.Callable[..., Exception]],
        error_message: typing.Optional[str],
        halt_execution: bool,
    ) -> None:
        self._error = error
        self._error_message = error_message
        self._halt_execution = halt_execution

    def _handle_result(self, result: bool, /, *args: typing.Any) -> bool:
        if not result:
            if self._error:
                raise self._error(*args) from None
            if self._halt_execution:
                raise errors.HaltExecution from None
            if self._error_message:
                raise errors.CommandError(self._error_message) from None

        return result


class OwnerCheck(_Check):
    """Standard owner check callback registered by [tanjun.with_owner_check][].

    This check will only pass if the author of the command is a bot owner.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Optional[str] = "Only bot owners can use this command",
        halt_execution: bool = False,
    ) -> None:
        """Initialise an owner check.

        Parameters
        ----------
        error
            Callback used to create a custom error to raise if the check fails.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the
            command search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun.Context,
        dependency: alluka.Injected[dependencies.AbstractOwners],
    ) -> bool:
        return self._handle_result(await dependency.check_ownership(ctx.client, ctx.author))


_GuildChannelCacheT = typing.Optional[dependencies.SfCache[hikari.GuildChannel]]


async def _get_is_nsfw(
    ctx: tanjun.Context,
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
    """Standard NSFW check callback registered by [tanjun.with_nsfw_check][].

    This check will only pass if the current channel is NSFW.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a NSFW check.

        Parameters
        ----------
        error
            Callback used to create a custom error to raise if the check fails.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the command
            search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun.Context,
        /,
        *,
        channel_cache: alluka.Injected[_GuildChannelCacheT] = None,
    ) -> bool:
        return self._handle_result(await _get_is_nsfw(ctx, dm_default=True, channel_cache=channel_cache))


class SfwCheck(_Check):
    """Standard SFW check callback registered by [tanjun.with_sfw_check][].

    This check will only pass if the current channel is SFW.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Optional[str] = "Command can only be used in SFW channels",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a SFW check.

        Parameters
        ----------
        error
            Callback used to create a custom error to raise if the check fails.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the command
            search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    async def __call__(
        self,
        ctx: tanjun.Context,
        /,
        *,
        channel_cache: alluka.Injected[_GuildChannelCacheT] = None,
    ) -> bool:
        return self._handle_result(not await _get_is_nsfw(ctx, dm_default=False, channel_cache=channel_cache))


class DmCheck(_Check):
    """Standard DM check callback registered by [tanjun.with_dm_check][].

    This check will only pass if the current channel is a DM channel.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Optional[str] = "Command can only be used in DMs",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a DM check.

        Parameters
        ----------
        error
            Callback used to create a custom error to raise if the check fails.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the command
            search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    def __call__(self, ctx: tanjun.Context, /) -> bool:
        return self._handle_result(ctx.guild_id is None)


class GuildCheck(_Check):
    """Standard guild check callback registered by [tanjun.with_guild_check][].

    This check will only pass if the current channel is in a guild.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Optional[str] = "Command can only be used in guild channels",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a guild check.

        Parameters
        ----------
        error
            Callback used to create a custom error to raise if the check fails.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the command
            search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    def __call__(self, ctx: tanjun.Context, /) -> bool:
        return self._handle_result(ctx.guild_id is not None)


class AuthorPermissionCheck(_Check):
    """Standard author permission check callback registered by [tanjun.with_author_permission_check][].

    This check will only pass if the current author has the specified permission.
    """

    __slots__ = ("_permissions",)

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error: typing.Optional[collections.Callable[[hikari.Permissions], Exception]] = None,
        error_message: typing.Optional[str] = "You don't have the permissions required to use this command",
        halt_execution: bool = False,
    ) -> None:
        """Initialise an author permission check.

        Parameters
        ----------
        permissions
            The permission(s) required for this command to run.
        error
            Callback used to create a custom error to raise if the check fails.

            This should take 1 positional argument of type [hikari.permissions.Permissions][]
            which represents the missing permissions required for this command to run.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the command
            search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)
        self._permissions = permissions

    async def __call__(self, ctx: tanjun.Context, /) -> bool:
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
            # Luckily, InteractionMember.permissions already handles the
            # implicit owner and admin permssion special casing for us.
            permissions = ctx.member.permissions

        else:
            permissions = await utilities.fetch_permissions(ctx.client, ctx.member, channel=ctx.channel_id)

        missing_permissions = ~permissions & self._permissions
        return self._handle_result(missing_permissions is hikari.Permissions.NONE, missing_permissions)


_MemberCacheT = typing.Optional[dependencies.SfGuildBound[hikari.Member]]


class OwnPermissionCheck(_Check):
    """Standard own permission check callback registered by [tanjun.with_own_permission_check][].

    This check will only pass if the current bot user has the specified permission.
    """

    __slots__ = ("_permissions",)

    def __init__(
        self,
        permissions: typing.Union[hikari.Permissions, int],
        /,
        *,
        error: typing.Optional[collections.Callable[[hikari.Permissions], Exception]] = None,
        error_message: typing.Optional[str] = "Bot doesn't have the permissions required to run this command",
        halt_execution: bool = False,
    ) -> None:
        """Initialise a own permission check.

        Parameters
        ----------
        permissions
            The permission(s) required for this command to run.
        error
            Callback used to create a custom error to raise if the check fails.

            This should take 1 positional argument of type [hikari.permissions.Permissions][]
            which represents the missing permissions required for this command to run.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            Setting this to [None][] will disable the error message allowing the command
            search to continue.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)
        self._permissions = permissions

    async def __call__(
        self,
        ctx: tanjun.Context,
        /,
        *,
        my_user: hikari.OwnUser = dependencies.inject_lc(hikari.OwnUser),
        member_cache: alluka.Injected[_MemberCacheT] = None,
    ) -> bool:
        if ctx.guild_id is None:
            permissions = utilities.DM_PERMISSIONS

        elif ctx.cache and (member := ctx.cache.get_member(ctx.guild_id, my_user)):
            permissions = await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        else:
            try:
                member = await member_cache.get_from_guild(ctx.guild_id, my_user.id) if member_cache else None
            except dependencies.EntryNotFound:
                # If we're not in the Guild then we have to assume the application
                # is still in there and that we likely won't be able to do anything.
                # TODO: re-visit this later.
                return self._handle_result(False, self._permissions)
            except dependencies.CacheMissError:
                member = None

            try:
                member = member or await ctx.rest.fetch_member(ctx.guild_id, my_user.id)

            except hikari.NotFoundError:
                # If we're not in the Guild then we have to assume the application
                # is still in there and that we likely won't be able to do anything.
                # TODO: re-visit this later.
                return self._handle_result(False, self._permissions)

            permissions = await utilities.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        missing_permissions = ~permissions & self._permissions
        return self._handle_result(missing_permissions is hikari.Permissions.NONE, missing_permissions)


@typing.overload
def with_dm_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_dm_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in DMs",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_dm_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in DMs",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a DM channel.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, DmCheck(error=error, halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_guild_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_guild_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in guild channels",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_guild_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in guild channels",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a guild channel.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    tanjun.abc.ExecutableCommanmd
        The command this check was added to.
    """
    return _optional_kwargs(
        command, GuildCheck(error=error, halt_execution=halt_execution, error_message=error_message)
    )


@typing.overload
def with_nsfw_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_nsfw_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_nsfw_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in NSFW channels",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a channel that's marked as nsfw.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, NsfwCheck(error=error, halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_sfw_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_sfw_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in SFW channels",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_sfw_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Command can only be used in SFW channels",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run in a channel that's marked as sfw.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(command, SfwCheck(error=error, halt_execution=halt_execution, error_message=error_message))


@typing.overload
def with_owner_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_owner_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_owner_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str] = "Only bot owners can use this command",
    halt_execution: bool = False,
) -> _CallbackReturnT[_CommandT]:
    """Only let a command run if it's being triggered by one of the bot's owners.

    Parameters
    ----------
    command : tanjun.abc.ExecutableCommand | None
        The command to add this check to.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    tanjun.abc.ExecutableCommand
        The command this check was added to.
    """
    return _optional_kwargs(
        command, OwnerCheck(error=error, halt_execution=halt_execution, error_message=error_message)
    )


def with_author_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error: typing.Optional[collections.Callable[[hikari.Permissions], Exception]] = None,
    error_message: typing.Optional[str] = "You don't have the permissions required to use this command",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Only let a command run if the author has certain permissions in the current channel.

    !!! note
        This will only pass for commands in DMs if `permissions` is valid for
        a DM context (e.g. can't have any moderation permissions)

    Parameters
    ----------
    permissions
        The permission(s) required for this command to run.
    error
        Callback used to create a custom error to raise if the check fails.

        This should take 1 positional argument of type [hikari.permissions.Permissions][]
        which represents the missing permissions required for this command to run.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(
        AuthorPermissionCheck(permissions, error=error, halt_execution=halt_execution, error_message=error_message)
    )


def with_own_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error: typing.Optional[collections.Callable[[hikari.Permissions], Exception]] = None,
    error_message: typing.Optional[str] = "Bot doesn't have the permissions required to run this command",
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Only let a command run if we have certain permissions in the current channel.

    !!! note
        This will only pass for commands in DMs if `permissions` is valid for
        a DM context (e.g. can't have any moderation permissions)

    Parameters
    ----------
    permissions
        The permission(s) required for this command to run.
    error
        Callback used to create a custom error to raise if the check fails.

        This should take 1 positional argument of type [hikari.permissions.Permissions][]
        which represents the missing permissions required for this command to run.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        Setting this to [None][] will disable the error message allowing the command
        search to continue.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(
        OwnPermissionCheck(permissions, error=error, halt_execution=halt_execution, error_message=error_message)
    )


def with_check(check: tanjun.CheckSig, /) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a generic check to a command.

    Parameters
    ----------
    check
        The check to add to this command.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: command.add_check(check)


class _AllChecks:
    __slots__ = ("_checks",)

    def __init__(self, checks: list[tanjun.CheckSig]) -> None:
        self._checks = checks

    async def __call__(self, ctx: tanjun.Context, /) -> bool:
        for check in self._checks:
            if not await ctx.call_with_async_di(check, ctx):
                return False

        return True


def all_checks(
    check: tanjun.CheckSig,
    /,
    *checks: tanjun.CheckSig,
) -> collections.Callable[[tanjun.Context], collections.Coroutine[typing.Any, typing.Any, bool]]:
    """Combine multiple check callbacks into a check which will only pass if all the callbacks pass.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check
        The first check callback to combine.
    *checks
        Additional check callbacks to combine.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.Context], collections.abc.Coroutine[typing.Any, typing.Any, bool]]
        A check which will pass if all of the provided check callbacks pass.
    """
    return _AllChecks([check, *checks])


def with_all_checks(
    check: tanjun.CheckSig,
    /,
    *checks: tanjun.CheckSig,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a check which will pass if all the provided checks pass through a decorator call.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check
        The first check callback to combine.
    *checks
        Additional check callbacks to combine.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.Context], collections.abc.Coroutine[typing.Any, typing.Any, bool]]
        A check which will pass if all of the provided check callbacks pass.
    """
    return lambda c: c.add_check(all_checks(check, *checks))


class _AnyChecks(_Check):
    __slots__ = ("_checks", "_suppress")

    def __init__(
        self,
        checks: list[tanjun.CheckSig],
        error: typing.Optional[collections.Callable[[], Exception]],
        error_message: typing.Optional[str],
        halt_execution: bool,
        suppress: tuple[type[Exception], ...],
    ) -> None:
        super().__init__(error, error_message, halt_execution)
        self._checks = checks
        self._suppress = suppress

    async def __call__(self, ctx: tanjun.Context, /) -> bool:
        for check in self._checks:
            try:
                if await ctx.call_with_async_di(check, ctx):
                    return True

            except errors.FailedCheck:
                pass

            except self._suppress:
                pass

        return self._handle_result(False)


def any_checks(
    check: tanjun.CheckSig,
    /,
    *checks: tanjun.CheckSig,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str],
    halt_execution: bool = False,
    suppress: tuple[type[Exception], ...] = (errors.CommandError, errors.HaltExecution),
) -> collections.Callable[[tanjun.Context], collections.Coroutine[typing.Any, typing.Any, bool]]:
    """Combine multiple checks into a check which'll pass if any of the callbacks pass.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check
        The first check callback to combine.
    *checks
        Additional check callbacks to combine.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.
    suppress
        Tuple of the exceptions to suppress when a check fails.

    Returns
    -------
    collections.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A decorator which adds the generated check to a command.
    """
    return _AnyChecks([check, *checks], error, error_message, halt_execution, suppress)


def with_any_checks(
    check: tanjun.CheckSig,
    /,
    *checks: tanjun.CheckSig,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Optional[str],
    halt_execution: bool = False,
    suppress: tuple[type[Exception], ...] = (errors.CommandError, errors.HaltExecution),
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a check which'll pass if any of the provided checks pass through a decorator call.

    This ensures that the callbacks are run in the order they were supplied in
    rather than concurrently.

    Parameters
    ----------
    check
        The first check callback to combine.
    *checks
        Additional check callbacks to combine.
    error
        Callback used to create a custom error to raise if the check fails.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.
    suppress
        Tuple of the exceptions to suppress when a check fails.

    Returns
    -------
    collections.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A decorator which adds the generated check to a command.
    """
    return lambda c: c.add_check(
        any_checks(
            check, *checks, error=error, error_message=error_message, halt_execution=halt_execution, suppress=suppress
        )
    )
