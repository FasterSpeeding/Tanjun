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
"""Standard implementation of Tanjun's command objects."""
from __future__ import annotations

__all__: list[str] = ["as_message_menu", "as_user_menu", "MenuCommand"]

import typing

from .. import abc
from .. import components
from .. import utilities
from . import base
from . import slash

if typing.TYPE_CHECKING:
    from collections import abc as collections

    _MenuCommandT = typing.TypeVar("_MenuCommandT", bound="MenuCommand[typing.Any, typing.Any]")

import hikari

_MenuCommandCallbackSigT = typing.TypeVar("_MenuCommandCallbackSigT", bound="abc.MenuCommandCallbackSig")
_MenuTypeT = typing.TypeVar(
    "_MenuTypeT", typing.Literal[hikari.CommandType.USER], typing.Literal[hikari.CommandType.MESSAGE]
)


def as_message_menu(
    name: str, /, *, default_to_ephemeral: typing.Optional[bool] = None, is_global: bool = True
) -> collections.Callable[
    [_MenuCommandCallbackSigT], MenuCommand[_MenuCommandCallbackSigT, typing.Literal[hikari.CommandType.MESSAGE]]
]:
    return lambda callback: MenuCommand(
        callback,
        hikari.CommandType.MESSAGE,
        name,
        default_to_ephemeral=default_to_ephemeral,
        is_global=is_global,
    )


def as_user_menu(
    name: str, /, *, default_to_ephemeral: typing.Optional[bool] = None, is_global: bool = True
) -> collections.Callable[
    [_MenuCommandCallbackSigT], MenuCommand[_MenuCommandCallbackSigT, typing.Literal[hikari.CommandType.USER]]
]:
    return lambda callback: MenuCommand(
        callback,
        hikari.CommandType.USER,
        name,
        default_to_ephemeral=default_to_ephemeral,
        is_global=is_global,
    )


class MenuCommand(base.PartialCommand[abc.MenuContext], abc.MenuCommand[_MenuCommandCallbackSigT, _MenuTypeT]):
    """Base class used for the standard slash command implementations."""

    __slots__ = (
        "_callback",
        "_default_permission",
        "_defaults_to_ephemeral",
        "_description",
        "_is_global",
        "_name",
        "_parent",
        "_tracked_command",
        "_type",
        "_wrapped_command",
    )

    def __init__(
        self,
        callback: _MenuCommandCallbackSigT,
        type_: _MenuTypeT,
        name: str,
        /,
        *,
        default_permission: bool = True,
        default_to_ephemeral: typing.Optional[bool] = None,
        is_global: bool = True,
        _wrapped_command: typing.Optional[abc.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        super().__init__()
        slash.validate_name(name)
        if isinstance(callback, (abc.MenuCommand, abc.MessageCommand, abc.SlashCommand)):
            callback = typing.cast(_MenuCommandCallbackSigT, callback.callback)

        self._callback = callback
        self._default_permission = default_permission
        self._defaults_to_ephemeral = default_to_ephemeral
        self._is_global = is_global
        self._name = name
        self._parent: typing.Optional[abc.SlashCommandGroup] = None
        self._tracked_command: typing.Optional[hikari.ContextMenuCommand] = None
        self._type = type_
        self._wrapped_command = _wrapped_command

    @property
    def callback(self) -> _MenuCommandCallbackSigT:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._callback

    @property
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._defaults_to_ephemeral

    @property
    def is_global(self) -> bool:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._is_global

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._name

    @property
    def tracked_command(self) -> typing.Optional[hikari.ContextMenuCommand]:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._tracked_command

    @property
    def tracked_command_id(self) -> typing.Optional[hikari.Snowflake]:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        return self._tracked_command.id if self._tracked_command else None

    @property
    def type(self) -> _MenuTypeT:
        return self._type

    def build(self) -> hikari.api.ContextMenuCommandBuilder:
        return hikari.impl.ContextMenuCommandBuilder(self._type, self._name).set_default_permission(
            self._default_permission
        )

    def set_tracked_command(self: _MenuCommandT, command: hikari.ContextMenuCommand, /) -> _MenuCommandT:
        """Set the the global command this should be tracking.

        Parameters
        ----------
        command : hikari.SlashCommand
            object of the global command this should be tracking.

        Returns
        -------
        SelfT
            This command instance for chaining.
        """
        self._tracked_command = command
        return self

    def set_ephemeral_default(self: _MenuCommandT, state: typing.Optional[bool], /) -> _MenuCommandT:
        """Set whether this command's responses should default to ephemeral.

        Parameters
        ----------
        bool | None
            Whether this command's responses should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to `None` will let the default set on the parent
            command(s), component or client propagate and decide the ephemeral
            default for contexts used by this command.

        Returns
        -------
        SelfT
            This command to allow for chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    async def check_context(self, ctx: abc.MenuContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.MenuCommand>>.
        ctx.set_command(self)
        result = await utilities.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    def copy(
        self: _MenuCommandT, *, _new: bool = True, parent: typing.Optional[abc.SlashCommandGroup] = None
    ) -> _MenuCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if not _new:
            self._parent = parent
            return super().copy(_new=_new)

        return super().copy(_new=_new)

    async def execute(
        self, ctx: abc.MenuContext, /, *, hooks: typing.Optional[collections.MutableSet[abc.MenuHooks]] = None
    ) -> None:
        raise NotImplementedError

    def load_into_component(self, component: abc.Component, /) -> None:
        # <<inherited docstring from tanjun.components.load_into_component>>.
        component.add_menu_command(self)
        if self._wrapped_command and isinstance(self._wrapped_command, components.AbstractComponentLoader):
            self._wrapped_command.load_into_component(component)
