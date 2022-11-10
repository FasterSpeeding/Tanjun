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

from . import _internal
from . import abc as tanjun
from . import dependencies
from . import errors
from . import permissions
from ._internal import cache
from ._internal import localisation

if typing.TYPE_CHECKING:

    class _AnyCallback(typing.Protocol):
        async def __call__(
            self,
            ctx: tanjun.Context,
            /,
            localiser: typing.Optional[dependencies.AbstractLocaliser] = None,
        ) -> bool:
            raise NotImplementedError


_CommandT = typing.TypeVar("_CommandT", bound="tanjun.ExecutableCommand[typing.Any]")
# This errors on earlier 3.9 releases when not quotes cause dumb handling of the [_CommandT] list
_CallbackReturnT = typing.Union[_CommandT, "collections.Callable[[_CommandT], _CommandT]"]


def _add_to_command(command: _CommandT, check: tanjun.CheckSig, follow_wrapped: bool) -> _CommandT:
    if follow_wrapped:
        for wrapped in _internal.collect_wrapped(command):
            wrapped.add_check(check)

    return command.add_check(check)


def _optional_kwargs(
    command: typing.Optional[_CommandT],
    check: tanjun.CheckSig,
    follow_wrapped: bool,
) -> typing.Union[_CommandT, collections.Callable[[_CommandT], _CommandT]]:
    if command:
        return _add_to_command(command, check, follow_wrapped)

    return lambda c: _add_to_command(c, check, follow_wrapped)


class _Check:
    __slots__ = ("_error", "_error_message", "_halt_execution", "_localise_id", "__weakref__")

    def __init__(
        self,
        error: typing.Optional[collections.Callable[..., Exception]],
        error_message: typing.Union[str, collections.Mapping[str, str], None],
        halt_execution: bool,
        /,
        *,
        id_name: typing.Optional[str] = None,
    ) -> None:
        self._error = error
        self._error_message = localisation.MaybeLocalised("error_message", error_message) if error_message else None
        self._halt_execution = halt_execution
        self._localise_id = f"tanjun.{id_name or type(self).__name__}"

    def _handle_result(
        self,
        ctx: tanjun.Context,
        result: bool,
        localiser: typing.Optional[dependencies.AbstractLocaliser] = None,
        /,
        *args: typing.Any,
    ) -> bool:
        if not result:
            if self._error:
                raise self._error(*args) from None
            if self._halt_execution:
                raise errors.HaltExecution from None
            if self._error_message:
                message = self._error_message.localise(ctx, localiser, "check", self._localise_id)
                raise errors.CommandError(message) from None

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
        error_message: typing.Union[str, collections.Mapping[str, str], None] = "Only bot owners can use this command",
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

            This supports [localisation][] and uses the check name
            `"tanjun.OwnerCheck"` for global overrides.
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
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        return self._handle_result(ctx, await dependency.check_ownership(ctx.client, ctx.author), localiser)


async def _get_is_nsfw(ctx: tanjun.Context, /, *, dm_default: bool) -> bool:
    if ctx.guild_id is None:
        return dm_default

    return (await cache.get_perm_channel(ctx.client, ctx.channel_id)).is_nsfw or False


class NsfwCheck(_Check):
    """Standard NSFW check callback registered by [tanjun.with_nsfw_check][].

    This check will only pass if the current channel is NSFW.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Union[
            str, collections.Mapping[str, str], None
        ] = "Command can only be used in NSFW channels",
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

            This supports [localisation][] and uses the check name
            `"tanjun.NsfwCheck"` for global overrides.
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
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        return self._handle_result(ctx, await _get_is_nsfw(ctx, dm_default=True), localiser)


class SfwCheck(_Check):
    """Standard SFW check callback registered by [tanjun.with_sfw_check][].

    This check will only pass if the current channel is SFW.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Union[
            str, collections.Mapping[str, str], None
        ] = "Command can only be used in SFW channels",
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

            This supports [localisation][] and uses the check name
            `"tanjun.SfwCheck"` for global overrides.
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
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        return self._handle_result(ctx, not await _get_is_nsfw(ctx, dm_default=False), localiser)


class DmCheck(_Check):
    """Standard DM check callback registered by [tanjun.with_dm_check][].

    This check will only pass if the current channel is a DM channel.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in DMs",
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

            This supports [localisation][] and uses the check name
            `"tanjun.DmCheck"` for global overrides.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    def __call__(
        self,
        ctx: tanjun.Context,
        /,
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        return self._handle_result(ctx, ctx.guild_id is None, localiser)


class GuildCheck(_Check):
    """Standard guild check callback registered by [tanjun.with_guild_check][].

    This check will only pass if the current channel is in a guild.
    """

    __slots__ = ()

    def __init__(
        self,
        *,
        error: typing.Optional[collections.Callable[[], Exception]] = None,
        error_message: typing.Union[
            str, collections.Mapping[str, str], None
        ] = "Command can only be used in guild channels",
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

            This supports [localisation][] and uses the check name
            `"tanjun.GuildCheck"` for global overrides.
        halt_execution
            Whether this check should raise [tanjun.HaltExecution][] to
            end the execution search when it fails instead of returning [False][].

            This takes priority over `error_message`.
        """
        super().__init__(error, error_message, halt_execution)

    def __call__(
        self,
        ctx: tanjun.Context,
        /,
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        return self._handle_result(ctx, ctx.guild_id is not None, localiser)


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
        error_message: typing.Union[
            str, collections.Mapping[str, str], None
        ] = "You don't have the permissions required to use this command",
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

            This supports [localisation][] and uses the check name
            `"tanjun.AuthorPermissionCheck"` for global overrides.
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
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        if not ctx.member:
            # If there's no member when this is within a guild then it's likely
            # something like a webhook or guild visitor with no real permissions
            # outside of some basic set of send messages.
            if ctx.guild_id:
                perms = await permissions.fetch_everyone_permissions(ctx.client, ctx.guild_id, channel=ctx.channel_id)

            else:
                perms = permissions.DM_PERMISSIONS

        elif isinstance(ctx.member, hikari.InteractionMember):
            # Luckily, InteractionMember.permissions already handles the
            # implicit owner and admin permission special casing for us.
            perms = ctx.member.permissions

        else:
            perms = await permissions.fetch_permissions(ctx.client, ctx.member, channel=ctx.channel_id)

        missing_perms = ~perms & self._permissions
        return self._handle_result(ctx, missing_perms is hikari.Permissions.NONE, localiser, missing_perms)


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
        error_message: typing.Union[
            str, collections.Mapping[str, str], None
        ] = "Bot doesn't have the permissions required to run this command",
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

            This supports [localisation][] and uses the check name
            `"tanjun.OwnPermissionCheck"` for global overrides.
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
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
        my_user: hikari.OwnUser = dependencies.inject_lc(hikari.OwnUser),
        member_cache: alluka.Injected[_MemberCacheT] = None,
    ) -> bool:
        if ctx.guild_id is None:
            perms = permissions.DM_PERMISSIONS

        elif isinstance(ctx, tanjun.AppCommandContext):
            assert ctx.interaction.app_permissions is not None
            perms = ctx.interaction.app_permissions

        elif ctx.cache and (member := ctx.cache.get_member(ctx.guild_id, my_user)):
            perms = await permissions.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        else:
            member = await member_cache.get_from_guild(ctx.guild_id, my_user.id, default=None) if member_cache else None
            member = member or await ctx.rest.fetch_member(ctx.guild_id, my_user.id)
            perms = await permissions.fetch_permissions(ctx.client, member, channel=ctx.channel_id)

        missing_perms = ~perms & self._permissions
        return self._handle_result(ctx, missing_perms is hikari.Permissions.NONE, localiser, missing_perms)


@typing.overload
def with_dm_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_dm_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in DMs",
    follow_wrapped: bool = False,
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_dm_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in DMs",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.DmCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
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
        command, DmCheck(error=error, halt_execution=halt_execution, error_message=error_message), follow_wrapped
    )


@typing.overload
def with_guild_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_guild_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[
        str, collections.Mapping[str, str], None
    ] = "Command can only be used in guild channels",
    follow_wrapped: bool = False,
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_guild_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[
        str, collections.Mapping[str, str], None
    ] = "Command can only be used in guild channels",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.GuildCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
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
        command, GuildCheck(error=error, halt_execution=halt_execution, error_message=error_message), follow_wrapped
    )


@typing.overload
def with_nsfw_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_nsfw_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in NSFW channels",
    follow_wrapped: bool = False,
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_nsfw_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in NSFW channels",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.NsfwCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
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
        command, NsfwCheck(error=error, halt_execution=halt_execution, error_message=error_message), follow_wrapped
    )


@typing.overload
def with_sfw_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_sfw_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in SFW channels",
    follow_wrapped: bool = False,
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_sfw_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Command can only be used in SFW channels",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.SfwCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
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
        command, SfwCheck(error=error, halt_execution=halt_execution, error_message=error_message), follow_wrapped
    )


@typing.overload
def with_owner_check(command: _CommandT, /) -> _CommandT:
    ...


@typing.overload
def with_owner_check(
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Only bot owners can use this command",
    follow_wrapped: bool = False,
    halt_execution: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    ...


def with_owner_check(
    command: typing.Optional[_CommandT] = None,
    /,
    *,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None] = "Only bot owners can use this command",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.OwnerCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
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
        command, OwnerCheck(error=error, halt_execution=halt_execution, error_message=error_message), follow_wrapped
    )


def with_author_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error: typing.Optional[collections.Callable[[hikari.Permissions], Exception]] = None,
    error_message: typing.Union[
        str, collections.Mapping[str, str], None
    ] = "You don't have the permissions required to use this command",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.AuthorPermissionCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: _add_to_command(
        command,
        AuthorPermissionCheck(permissions, error=error, halt_execution=halt_execution, error_message=error_message),
        follow_wrapped,
    )


def with_own_permission_check(
    permissions: typing.Union[hikari.Permissions, int],
    *,
    error: typing.Optional[collections.Callable[[hikari.Permissions], Exception]] = None,
    error_message: typing.Union[
        str, collections.Mapping[str, str], None
    ] = "Bot doesn't have the permissions required to run this command",
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.OwnPermissionCheck"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
    halt_execution
        Whether this check should raise [tanjun.HaltExecution][] to
        end the execution search when it fails instead of returning [False][].

        This takes priority over `error_message`.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: _add_to_command(
        command,
        OwnPermissionCheck(permissions, error=error, halt_execution=halt_execution, error_message=error_message),
        follow_wrapped,
    )


def with_check(
    check: tanjun.CheckSig, /, *, follow_wrapped: bool = False
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a generic check to a command.

    Parameters
    ----------
    check
        The check to add to this command.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A command decorator callback which adds the check.
    """
    return lambda command: _add_to_command(command, check, follow_wrapped)


class _AllChecks:
    __slots__ = ("_checks", "__weakref__")

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
    follow_wrapped: bool = False,
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
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.Context], collections.abc.Coroutine[typing.Any, typing.Any, bool]]
        A check which will pass if all of the provided check callbacks pass.
    """
    return lambda c: _add_to_command(c, all_checks(check, *checks), follow_wrapped)


class _AnyChecks(_Check):
    __slots__ = ("_checks", "_suppress")

    def __init__(
        self,
        checks: list[tanjun.CheckSig],
        error: typing.Optional[collections.Callable[[], Exception]],
        error_message: typing.Union[str, collections.Mapping[str, str], None],
        halt_execution: bool,
        suppress: tuple[type[Exception], ...],
    ) -> None:
        super().__init__(error, error_message, halt_execution, id_name="any_check")
        self._checks = checks
        self._suppress = suppress

    async def __call__(
        self,
        ctx: tanjun.Context,
        /,
        localiser: alluka.Injected[typing.Optional[dependencies.AbstractLocaliser]] = None,
    ) -> bool:
        for check in self._checks:
            try:
                if await ctx.call_with_async_di(check, ctx):
                    return True

            except errors.FailedCheck:
                pass

            except self._suppress:
                pass

        return self._handle_result(ctx, False, localiser)


def any_checks(
    check: tanjun.CheckSig,
    /,
    *checks: tanjun.CheckSig,
    error: typing.Optional[collections.Callable[[], Exception]] = None,
    error_message: typing.Union[str, collections.Mapping[str, str], None],
    halt_execution: bool = False,
    suppress: tuple[type[Exception], ...] = (errors.CommandError, errors.HaltExecution),
) -> _AnyCallback:
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

        This supports [localisation][] and uses the check name
        `"tanjun.any_check"` for global overrides.
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
    error_message: typing.Union[str, collections.Mapping[str, str], None],
    follow_wrapped: bool = False,
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

        This supports [localisation][] and uses the check name
        `"tanjun.any_check"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
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
    return lambda c: _add_to_command(
        c,
        any_checks(
            check, *checks, error=error, error_message=error_message, halt_execution=halt_execution, suppress=suppress
        ),
        follow_wrapped,
    )
