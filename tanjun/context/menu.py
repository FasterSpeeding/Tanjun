# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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
"""Menu context implementation."""
from __future__ import annotations

__all__: list[str] = ["MenuContext"]

import typing

import hikari

from tanjun import _internal
from tanjun import abc as tanjun

from . import slash

if typing.TYPE_CHECKING:
    import asyncio
    from collections import abc as collections
    from typing import Self

    _T = typing.TypeVar("_T")
    _ResponseTypeT = (
        hikari.api.InteractionMessageBuilder
        | hikari.api.InteractionDeferredBuilder
        | hikari.api.InteractionModalBuilder
    )


_VALID_TYPES: frozenset[typing.Literal[hikari.CommandType.USER, hikari.CommandType.MESSAGE]] = frozenset(
    [hikari.CommandType.USER, hikari.CommandType.MESSAGE]
)


class MenuContext(slash.AppCommandContext, tanjun.MenuContext):
    """Standard menu command execution context."""

    __slots__ = ("_command", "_marked_not_found", "_on_not_found")

    def __init__(
        self,
        client: tanjun.Client,
        interaction: hikari.CommandInteraction,
        register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
        *,
        default_to_ephemeral: bool = False,
        future: asyncio.Future[_ResponseTypeT] | None = None,
        on_not_found: collections.Callable[[tanjun.MenuContext], collections.Awaitable[None]] | None = None,
    ) -> None:
        """Initialise a menu command context.

        Parameters
        ----------
        client
            The Tanjun client this context is bound to.
        interaction
            The command interaction this context is for.
        register_task
            Callback used to register long-running tasks spawned by this context.
        future
            A future used to set the initial response if this is being called
            through the REST webhook flow.
        default_to_ephemeral
            Whether to default to ephemeral responses.
        on_not_found
            Callback used to indicate no matching command was found.
        """
        super().__init__(client, interaction, register_task, default_to_ephemeral=default_to_ephemeral, future=future)
        self._command: tanjun.MenuCommand[typing.Any, typing.Any] | None = None
        self._marked_not_found = False
        self._on_not_found = on_not_found
        self._set_type_special_case(tanjun.MenuContext, self)._set_type_special_case(MenuContext, self)  # noqa: SLF001

    @property
    def command(self) -> tanjun.MenuCommand[typing.Any, typing.Any] | None:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        return self._command

    @property
    def target_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        mapping = self._interaction.resolved.users or self._interaction.resolved.messages

        if not mapping:
            error_message = "Unknown menu type"
            raise RuntimeError(error_message)

        return next(iter(mapping.keys()))

    @property
    def target(self) -> hikari.InteractionMember | hikari.User | hikari.Message:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        mapping = (
            self._interaction.resolved.members
            or self._interaction.resolved.users
            or self._interaction.resolved.messages
        )

        if not mapping:
            error_message = "Unknown menu type"
            raise RuntimeError(error_message)

        return next(iter(mapping.values()))

    @property
    def triggering_name(self) -> str:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.command_name

    @property
    def type(self) -> typing.Literal[hikari.CommandType.USER, hikari.CommandType.MESSAGE]:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        command_type = hikari.CommandType(self._interaction.command_type)
        assert command_type in _VALID_TYPES
        return command_type

    async def mark_not_found(self) -> None:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        # TODO: assert not finalised?
        if self._on_not_found and not self._marked_not_found:
            self._marked_not_found = True
            await self._on_not_found(self)

    def set_command(self, command: tanjun.MenuCommand[typing.Any, typing.Any] | None, /) -> Self:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        if command:
            self._set_type_special_case(tanjun.MenuCommand, command)

        elif self._command:
            self._remove_type_special_case(tanjun.MenuContext)

        self._command = command
        return self

    @typing.overload
    def resolve_to_member(self) -> hikari.InteractionMember: ...

    @typing.overload
    def resolve_to_member(self, *, default: _T) -> hikari.InteractionMember | _T: ...

    def resolve_to_member(
        self, *, default: _T | _internal.Default = _internal.DEFAULT
    ) -> hikari.InteractionMember | _T:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        if self._interaction.resolved.members:
            return next(iter(self._interaction.resolved.members.values()))

        if self._interaction.resolved.users:
            if default is not _internal.DEFAULT:
                return default

            error_message = "User isn't in the current guild"
            raise LookupError(error_message)

        error_message = "Cannot resolve message menu context to a user"
        raise TypeError(error_message)

    def resolve_to_message(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        if self._interaction.resolved.messages:
            return next(iter(self._interaction.resolved.messages.values()))

        error_message = "Cannot resolve user menu context to a message"
        raise TypeError(error_message)

    def resolve_to_user(self) -> hikari.User | hikari.Member:
        # <<inherited docstring from tanjun.abc.MenuContext>>.
        assert self._interaction.resolved
        return self.resolve_to_member(default=None) or next(iter(self._interaction.resolved.users.values()))
