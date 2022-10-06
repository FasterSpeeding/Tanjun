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
"""Menu command implementations."""
from __future__ import annotations

__all__: list[str] = ["MenuCommand", "as_message_menu", "as_user_menu"]

import typing

from .. import _internal
from .. import abc as tanjun
from .. import components
from .. import errors
from .. import hooks as hooks_
from .._internal import localisation
from . import base

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from typing_extensions import Self

    _CommandT = typing.Union[
        tanjun.MenuCommand["_MenuCommandCallbackSigT", typing.Any],
        tanjun.MessageCommand["_MenuCommandCallbackSigT"],
        tanjun.SlashCommand["_MenuCommandCallbackSigT"],
    ]
    _CallbackishT = typing.Union["_MenuCommandCallbackSigT", _CommandT["_MenuCommandCallbackSigT"]]

import hikari

_MenuCommandCallbackSigT = typing.TypeVar("_MenuCommandCallbackSigT", bound="tanjun.MenuCommandCallbackSig")
_MenuTypeT = typing.TypeVar(
    "_MenuTypeT", typing.Literal[hikari.CommandType.USER], typing.Literal[hikari.CommandType.MESSAGE]
)
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()


def _as_menu(
    name: typing.Union[str, collections.Mapping[str, str]],
    type_: _MenuTypeT,
    always_defer: bool = False,
    default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
    default_to_ephemeral: typing.Optional[bool] = None,
    dm_enabled: typing.Optional[bool] = None,
    is_global: bool = True,
) -> _ResultProto[_MenuTypeT]:
    def decorator(
        callback: _CallbackishT[_MenuCommandCallbackSigT], /
    ) -> MenuCommand[_MenuCommandCallbackSigT, _MenuTypeT]:
        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            wrapped_command = callback
            callback = callback.callback

        else:
            wrapped_command = None

        return MenuCommand(
            callback,
            type_,
            name,
            always_defer=always_defer,
            default_member_permissions=default_member_permissions,
            default_to_ephemeral=default_to_ephemeral,
            dm_enabled=dm_enabled,
            is_global=is_global,
            _wrapped_command=wrapped_command,
        )

    return decorator


class _ResultProto(typing.Protocol[_MenuTypeT]):
    @typing.overload
    def __call__(self, _: _CommandT[_MenuCommandCallbackSigT], /) -> MenuCommand[_MenuCommandCallbackSigT, _MenuTypeT]:
        ...

    @typing.overload
    def __call__(self, _: _MenuCommandCallbackSigT, /) -> MenuCommand[_MenuCommandCallbackSigT, _MenuTypeT]:
        ...

    def __call__(
        self, _: _CallbackishT[_MenuCommandCallbackSigT], /
    ) -> MenuCommand[_MenuCommandCallbackSigT, _MenuTypeT]:
        raise NotImplementedError


def as_message_menu(
    name: typing.Union[str, collections.Mapping[str, str]],
    /,
    *,
    always_defer: bool = False,
    default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
    default_to_ephemeral: typing.Optional[bool] = None,
    dm_enabled: typing.Optional[bool] = None,
    is_global: bool = True,
) -> _ResultProto[typing.Literal[hikari.CommandType.MESSAGE]]:
    """Build a message [tanjun.MenuCommand][] by decorating a function.

    !!! note
        Under the standard implementation, `is_global` is used to determine whether
        the command should be bulk set by [tanjun.Client.declare_global_commands][]
        or when `declare_global_commands` is True

    !!! note
        If you want your first response to be ephemeral while using
        `always_defer`, you must set `default_to_ephemeral` to `True`.

    Examples
    --------
    ```py
    @as_message_menu("message")
    async def message_command(self, ctx: tanjun.abc.MenuContext, message: hikari.Message) -> None:
        await ctx.respond(
            embed=hikari.Embed(title="Message content", description=message.content or "N/A")
        )
    ```

    Parameters
    ----------
    name
        The command's name (supports [localisation][]).

        This must be between 1 and 32 characters in length.
    always_defer
        Whether the contexts this command is executed with should always be deferred
        before being passed to the command's callback.
    default_member_permissions
        Member permissions necessary to utilize this command by default.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    default_to_ephemeral
        Whether this command's responses should default to ephemeral unless flags
        are set to override this.

        If this is left as [None][] then the default set on the parent command(s),
        component or client will be in effect.
    dm_enabled
        Whether this command is enabled in DMs with the bot.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    is_global
        Whether this command is a global command.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MenuCommandCallbackSig], MenuCommand]
        The decorator callback used to make a [tanjun.MenuCommand][].

        This can either wrap a raw command callback or another callable command instance
        (e.g. [tanjun.MenuCommand][], [tanjun.MessageCommand][], [tanjun.SlashCommand][])
        and will manage loading the other command into a component when using
        [tanjun.Component.load_from_scope][].

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:

        * If the command name isn't in the length range of 1 to 32.
        * If the command name has uppercase characters.
    """
    return _as_menu(
        name,
        hikari.CommandType.MESSAGE,
        always_defer=always_defer,
        default_member_permissions=default_member_permissions,
        default_to_ephemeral=default_to_ephemeral,
        dm_enabled=dm_enabled,
        is_global=is_global,
    )


def as_user_menu(
    name: typing.Union[str, collections.Mapping[str, str]],
    /,
    *,
    always_defer: bool = False,
    default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
    default_to_ephemeral: typing.Optional[bool] = None,
    dm_enabled: typing.Optional[bool] = None,
    is_global: bool = True,
) -> _ResultProto[typing.Literal[hikari.CommandType.USER]]:
    """Build a user [tanjun.MenuCommand][] by decorating a function.

    !!! note
        Under the standard implementation, `is_global` is used to determine whether
        the command should be bulk set by [tanjun.Client.declare_global_commands][]
        or when `declare_global_commands` is True

    !!! note
        If you want your first response to be ephemeral while using
        `always_defer`, you must set `default_to_ephemeral` to `True`.

    Examples
    --------
    ```py
    @as_user_menu("user")
    async def user_command(
        self,
        ctx: tanjun.abc.MenuContext,
        user: hikari.User | hikari.InteractionMember,
    ) -> None:
        await ctx.respond(f"Hello {user}")
    ```

    Parameters
    ----------
    name
        The command's name (supports [localisation][]).

        This must be between 1 and 32 characters in length.
    always_defer
        Whether the contexts this command is executed with should always be deferred
        before being passed to the command's callback.
    default_member_permissions
        Member permissions necessary to utilize this command by default.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    default_to_ephemeral
        Whether this command's responses should default to ephemeral unless flags
        are set to override this.

        If this is left as [None][] then the default set on the parent command(s),
        component or client will be in effect.
    dm_enabled
        Whether this command is enabled in DMs with the bot.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    is_global
        Whether this command is a global command.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MenuCommandCallbackSig], MenuCommand]
        The decorator callback used to make a [tanjun.MenuCommand][].

        This can either wrap a raw command callback or another callable command instance
        (e.g. [tanjun.MenuCommand][], [tanjun.MessageCommand][], [tanjun.SlashCommand][])
        and will manage loading the other command into a component when using
        [tanjun.Component.load_from_scope][].

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:

        * If the command name isn't in the length range of 1 to 32.
        * If the command name has uppercase characters.
    """
    return _as_menu(
        name,
        hikari.CommandType.USER,
        always_defer=always_defer,
        default_member_permissions=default_member_permissions,
        default_to_ephemeral=default_to_ephemeral,
        dm_enabled=dm_enabled,
        is_global=is_global,
    )


_VALID_TYPES = frozenset((hikari.CommandType.MESSAGE, hikari.CommandType.USER))


class MenuCommand(base.PartialCommand[tanjun.MenuContext], tanjun.MenuCommand[_MenuCommandCallbackSigT, _MenuTypeT]):
    """Base class used for the standard menu command implementations."""

    __slots__ = (
        "_always_defer",
        "_callback",
        "_default_member_permissions",
        "_defaults_to_ephemeral",
        "_description",
        "_is_dm_enabled",
        "_is_global",
        "_names",
        "_parent",
        "_tracked_command",
        "_type",
        "_wrapped_command",
    )

    @typing.overload
    def __init__(
        self,
        callback: _CommandT[
            _MenuCommandCallbackSigT,
        ],
        type_: _MenuTypeT,
        name: typing.Union[str, collections.Mapping[str, str]],
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        callback: _MenuCommandCallbackSigT,
        type_: _MenuTypeT,
        name: typing.Union[str, collections.Mapping[str, str]],
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    def __init__(
        self,
        callback: _CallbackishT[_MenuCommandCallbackSigT],
        type_: _MenuTypeT,
        name: typing.Union[str, collections.Mapping[str, str]],
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        """Initialise a user or message menu command.

        !!! note
            Under the standard implementation, `is_global` is used to determine whether
            the command should be bulk set by [tanjun.Client.declare_global_commands][]
            or when `declare_global_commands` is True

        !!! note
            If you want your first response to be ephemeral while using
            `always_defer`, you must set `default_to_ephemeral` to `True`.

        Parameters
        ----------
        callback : collections.abc.Callable[[tanjun.abc.MenuContext, ...], collections.abc.Coroutine[Any, ANy, None]]
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type [tanjun.abc.MenuContext][], returns [None][]
            and may use dependency injection to access other services.
        type_ : hikari.commands.CommandType
            The type of menu command this is.

            Only [hikari.commands.CommandType.USER][] and [hikari.commands.CommandType.MESSAGE][]
            are valid here.
        name
            The command's name (supports [localisation][]).

            This must be between 1 and 32 characters in length.
        always_defer
            Whether the contexts this command is executed with should always be deferred
            before being passed to the command's callback.
        default_member_permissions
            Member permissions necessary to utilize this command by default.

            If this is [None][] then the configuration for the parent component or client
            will be used.
        default_to_ephemeral
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as [None][] then the default set on the parent command(s),
            component or client will be in effect.
        dm_enabled
            Whether this command is enabled in DMs with the bot.

            If this is [None][] then the configuration for the parent component or client
            will be used.
        is_global
            Whether this command is a global command.

        Returns
        -------
        collections.abc.Callable[[tanjun.abc.MenuCommandCallbackSig], MenuCommand]
            The decorator callback used to make a [tanjun.MenuCommand][].

            This can either wrap a raw command callback or another callable command instance
            (e.g. [tanjun.MenuCommand][], [tanjun.MessageCommand][], [tanjun.SlashCommand][])
            and will manage loading the other command into a component when using
            [tanjun.Component.load_from_scope][].

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the command name isn't in the length range of 1 to 32.
            * If the command name has uppercase characters.
        """
        super().__init__()
        names = localisation.MaybeLocalised("name", name).assert_length(1, 32)

        if type_ not in _VALID_TYPES:
            raise ValueError("Command type must be message or user")

        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            callback = callback.callback

        if default_member_permissions is not None:
            default_member_permissions = hikari.Permissions(default_member_permissions)

        self._always_defer = always_defer
        self._callback = callback
        self._default_member_permissions = default_member_permissions
        self._defaults_to_ephemeral = default_to_ephemeral
        self._is_dm_enabled = dm_enabled
        self._is_global = is_global
        self._names = names
        self._parent: typing.Optional[tanjun.SlashCommandGroup] = None
        self._tracked_command: typing.Optional[hikari.ContextMenuCommand] = None
        self._type: _MenuTypeT = type_  # MyPy bug causes this to need an explicit annotation.
        self._wrapped_command = _wrapped_command

    if typing.TYPE_CHECKING:
        __call__: _MenuCommandCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback(*args, **kwargs)

    @property
    def callback(self) -> _MenuCommandCallbackSigT:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._callback

    @property
    def default_member_permissions(self) -> typing.Optional[hikari.Permissions]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._default_member_permissions

    @property
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._defaults_to_ephemeral

    @property
    def is_dm_enabled(self) -> typing.Optional[bool]:
        return self._is_dm_enabled

    @property
    def is_global(self) -> bool:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_global

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._names.default_value

    @property
    def name_localisations(self) -> collections.Mapping[str, str]:
        return self._names.localised_values.copy()

    @property
    def tracked_command(self) -> typing.Optional[hikari.ContextMenuCommand]:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._tracked_command

    @property
    def tracked_command_id(self) -> typing.Optional[hikari.Snowflake]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._tracked_command.id if self._tracked_command else None

    @property
    def type(self) -> _MenuTypeT:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._type

    @property
    def wrapped_command(self) -> typing.Optional[tanjun.ExecutableCommand[typing.Any]]:
        """The command object this wraps, if any."""
        return self._wrapped_command

    def build(self, *, component: typing.Optional[tanjun.Component] = None) -> hikari.api.ContextMenuCommandBuilder:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        builder = hikari.impl.ContextMenuCommandBuilder(
            self._type,
            self._names.default_value,
            name_localizations=self._names.localised_values,  # pyright: ignore [ reportGeneralTypeIssues ]
        )

        component = component or self._component
        if self._default_member_permissions is not None:
            builder.set_default_member_permissions(self._default_member_permissions)
        elif component and component.default_app_cmd_permissions is not None:
            builder.set_default_member_permissions(component.default_app_cmd_permissions)

        if self._is_dm_enabled is not None:
            builder.set_is_dm_enabled(self._is_dm_enabled)
        elif component and component.dms_enabled_for_app_cmds is not None:
            builder.set_is_dm_enabled(component.dms_enabled_for_app_cmds)

        return builder

    def set_tracked_command(self, command: hikari.PartialCommand, /) -> Self:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        if not isinstance(command, hikari.ContextMenuCommand):
            raise TypeError("Command must be a ContextMenuCommand")

        self._tracked_command = command
        return self

    def set_ephemeral_default(self, state: typing.Optional[bool], /) -> Self:
        """Set whether this command's responses should default to ephemeral.

        Parameters
        ----------
        state
            Whether this command's responses should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to [None][] will let the default set on the parent
            command(s), component or client propagate and decide the ephemeral
            default for contexts used by this command.

        Returns
        -------
        Self
            This command to allow for chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    async def check_context(self, ctx: tanjun.MenuContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        ctx.set_command(self)
        result = await _internal.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    def copy(self, *, parent: typing.Optional[tanjun.SlashCommandGroup] = None) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy()
        inst._parent = parent
        return inst

    async def execute(
        self, ctx: tanjun.MenuContext, /, *, hooks: typing.Optional[collections.MutableSet[tanjun.MenuHooks]] = None
    ) -> None:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        if self._always_defer and not ctx.has_been_deferred and not ctx.has_responded:
            await ctx.defer()

        ctx = ctx.set_command(self)
        own_hooks = self._hooks or _EMPTY_HOOKS
        try:
            await own_hooks.trigger_pre_execution(ctx, hooks=hooks)

            if self._type is hikari.CommandType.USER:
                value: typing.Union[hikari.Message, hikari.User] = ctx.resolve_to_user()

            else:
                value = ctx.resolve_to_message()

            await ctx.call_with_async_di(self._callback, ctx, value)

        except errors.CommandError as exc:
            await exc.send(ctx)

        except errors.HaltExecution:
            # Unlike a message command, this won't necessarily reach the client level try except
            # block so we have to handle this here.
            await ctx.mark_not_found()

        except Exception as exc:
            if await own_hooks.trigger_error(ctx, exc, hooks=hooks) <= 0:
                raise

        else:
            await own_hooks.trigger_success(ctx, hooks=hooks)

        finally:
            await own_hooks.trigger_post_execution(ctx, hooks=hooks)

    def load_into_component(self, component: tanjun.Component, /) -> None:
        # <<inherited docstring from tanjun.components.load_into_component>>.
        component.add_menu_command(self)
        if self._wrapped_command and isinstance(self._wrapped_command, components.AbstractComponentLoader):
            self._wrapped_command.load_into_component(component)
