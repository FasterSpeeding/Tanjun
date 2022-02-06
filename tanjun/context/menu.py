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
"""Standard menu command execution context implementations."""
from __future__ import annotations

__all__: list[str] = []

import typing

from .. import abc
from . import slash
import hikari

if typing.TYPE_CHECKING:
    import asyncio
    from collections import abc as collections


    from .. import injecting

    _T = typing.TypeVar("_T")
    _MenuContextT = typing.TypeVar("_MenuContextT", bound="MenuContext")
    _ResponseTypeT = typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]


class MenuContext(slash.AppCommandContext, abc.MenuContext):
    """Standard menu command execution context."""

    __slots__ = ("_command",)

    def __init__(
        self,
        client: abc.Client,
        injection_client: injecting.InjectorClient,
        interaction: hikari.CommandInteraction,
        *,
        command: typing.Optional[abc.MenuCommand[typing.Any, typing.Any]] = None,
        component: typing.Optional[abc.Component] = None,
        default_to_ephemeral: bool = False,
        future: typing.Optional[asyncio.Future[_ResponseTypeT]] = None,
        on_not_found: typing.Optional[
            collections.Callable[[slash.AppCommandContext], collections.Awaitable[None]]
        ] = None,
    ) -> None:
        super().__init__(
            client,
            injection_client,
            interaction,
            component=component,
            default_to_ephemeral=default_to_ephemeral,
            future=future,
            on_not_found=on_not_found,
        )
        self._command = command

    @property
    def command(self) -> typing.Optional[abc.MenuCommand[typing.Any, typing.Any]]:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        return self._command

    @property
    def target_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        mapping = self._interaction.resolved.users or self._interaction.resolved.messages

        if not mapping:
            raise RuntimeError("Unknown menu type")

        return next(iter(mapping.keys()))

    @property
    def target(self) -> typing.Union[hikari.InteractionMember, hikari.User, hikari.Message]:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        mapping = self._interaction.resolved.users or self._interaction.resolved.messages

        if not mapping:
            raise RuntimeError("Unknown menu type")

        return next(iter(mapping.values()))

    @property
    def type(self) -> typing.Literal[hikari.CommandType.USER, hikari.CommandType.MESSAGE]:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        if self._interaction.resolved.users:
            return hikari.CommandType.USER

        if self._interaction.resolved.messages:
            return hikari.CommandType.MESSAGE

        raise NotImplementedError

    def set_command(
        self: _MenuContextT, command: typing.Optional[abc.MenuCommand[typing.Any, typing.Any]], /
    ) -> _MenuContextT:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        self._command = command
        return self

    @typing.overload
    def resolve_to_member(self) -> hikari.InteractionMember:
        ...

    @typing.overload
    def resolve_to_member(self, *, default: _T) -> typing.Union[hikari.InteractionMember, _T]:
        ...

    def resolve_to_member(self, *, default: _T = ...) -> typing.Union[hikari.InteractionMember, _T]:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        if self._interaction.resolved.members:
            return next(iter(self._interaction.resolved.members.values()))

        if self._interaction.resolved.users:
            if default is not ...:
                return default

            raise LookupError("User isn't in the current guild") from None

        raise TypeError("Cannot resolve user message menu context to a member")

    def resolve_to_message(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        if self._interaction.resolved.messages:
            return next(iter(self._interaction.resolved.messages.values()))

        raise TypeError("Cannot resolve user menu context to a message")

    def resolve_to_user(self) -> typing.Union[hikari.User, hikari.Member]:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        if self._interaction.resolved.users:
            return next(iter(self._interaction.resolved.members.values()))

        raise TypeError("Cannot resolve message menu context to a user")
