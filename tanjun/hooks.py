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
from __future__ import annotations

__all__: list[str] = ["AnyHooks", "ErrorHookSig", "Hooks", "HookSig", "MessageHooks", "ParserHookSig", "SlashHooks"]

import asyncio
import copy
import typing
from collections import abc as collections

from . import abc
from . import errors
from . import utilities

if typing.TypeVar:
    _HooksT = typing.TypeVar("_HooksT", bound="Hooks[typing.Any]")

CommandT = typing.TypeVar("CommandT", bound=abc.ExecutableCommand[typing.Any])

ParserHookSig = collections.Callable[[abc.ContextT, errors.ParserError], abc.MaybeAwaitableT[None]]
"""Type hint of the callback used as a parser error hook.

This will be called whenever a `tanjun.errors.ParserError` is raised during the
command argument parsing stage, will have to take two positional arguments - of
type `tanjun.abc.Context` and `tanjun.errors.ParserError` - and may either be
a synchronous or asynchronous callback which returns `None`
"""

ErrorHookSig = collections.Callable[[abc.ContextT, BaseException], abc.MaybeAwaitableT[typing.Optional[bool]]]
"""Type hint of the callback used as a unexpected command error hook.

This will be called whenever a `BaseException` is raised during the
execution stage whenever the command callback raises any exception except
`tanjun.errors.CommandError`,  will have to take two positional arguments - of
type `tanjun.abc.Context` and `BaseException` - and may either be a
synchronous or asynchronous callback which returns `None`
"""

HookSig = collections.Callable[[abc.ContextT], abc.MaybeAwaitableT[None]]
"""Type hint of the callback used as a general command hook.

This may be called during different stages of command execution (decided by
which hook this is registered as), will have to take one positional argument of
type `tanjun.abc.Context` and may be a synchronous or asynchronous callback
which returns `None`.
"""


class Hooks(abc.Hooks[abc.ContextT_contra]):
    """Standard implementation of `tanjun.abc.Hooks` used for command execution.

    .. note::
        This implementation adds a concept of parser errors which won't be
        dispatched to general "error" hooks and do not share the error
        suppression semantics as they favour to always suppress the error
        if a registered handler is found.
    """

    __slots__ = ("_error", "_parser_error", "_pre_execution", "_post_execution", "_success")

    def __init__(self) -> None:
        self._error: typing.Optional[ErrorHookSig[abc.ContextT_contra]] = None
        self._parser_error: typing.Optional[ParserHookSig[abc.ContextT_contra]] = None
        self._pre_execution: typing.Optional[HookSig[abc.ContextT_contra]] = None
        self._post_execution: typing.Optional[HookSig[abc.ContextT_contra]] = None
        self._success: typing.Optional[HookSig[abc.ContextT_contra]] = None

    def __repr__(self) -> str:
        return (
            f"Hooks <{self._error!r}, {self._parser_error!r}, {self._pre_execution!r}, "
            f"{self._post_execution!r}, {self._success!r}>"
        )

    def add_to_command(self, command: CommandT, /) -> CommandT:
        """Add this hook object to a command.

        .. note::
            This will likely override any previously added hooks.

        Examples
        --------
        This method may be used as a command decorator:

        ```py
        @standard_hooks.add_to_command
        @as_message_command("command")
        async def command_command(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You've called a command!")
        ```

        Parameters
        ----------
        command : tanjun.abc.ExecutableCommand[typing.Any]
            The command to add the hooks to.

        Returns
        -------
        tanjun.abc.ExecutableCommand[typing.Any]
            The command with the hooks added.
        """
        command.set_hooks(self)
        return command

    def copy(self: _HooksT) -> _HooksT:
        """Copy this hook object."""
        return copy.deepcopy(self)

    def set_on_error(self: _HooksT, hook: typing.Optional[ErrorHookSig[abc.ContextT_contra]], /) -> _HooksT:
        self._error = hook
        return self

    def with_on_error(self, hook: ErrorHookSig[abc.ContextT_contra], /) -> ErrorHookSig[abc.ContextT_contra]:
        self.set_on_error(hook)
        return hook

    def set_on_parser_error(self: _HooksT, hook: typing.Optional[ParserHookSig[abc.ContextT_contra]], /) -> _HooksT:
        self._parser_error = hook
        return self

    def with_on_parser_error(self, hook: ParserHookSig[abc.ContextT_contra], /) -> ParserHookSig[abc.ContextT_contra]:
        self.set_on_parser_error(hook)
        return hook

    def set_post_execution(self: _HooksT, hook: typing.Optional[HookSig[abc.ContextT_contra]], /) -> _HooksT:
        self._post_execution = hook
        return self

    def with_post_execution(self, hook: HookSig[abc.ContextT_contra], /) -> HookSig[abc.ContextT_contra]:
        self.set_post_execution(hook)
        return hook

    def set_pre_execution(self: _HooksT, hook: typing.Optional[HookSig[abc.ContextT_contra]], /) -> _HooksT:
        self._pre_execution = hook
        return self

    def with_pre_execution(self, hook: HookSig[abc.ContextT_contra], /) -> HookSig[abc.ContextT_contra]:
        self.set_pre_execution(hook)
        return hook

    def set_on_success(self: _HooksT, hook: typing.Optional[HookSig[abc.ContextT_contra]], /) -> _HooksT:
        self._success = hook
        return self

    def with_on_success(self, hook: HookSig[abc.ContextT_contra], /) -> HookSig[abc.ContextT_contra]:
        self.set_on_success(hook)
        return hook

    async def trigger_error(
        self,
        ctx: abc.ContextT_contra,
        /,
        exception: BaseException,
        *,
        hooks: typing.Optional[collections.Set[abc.Hooks[abc.ContextT_contra]]] = None,
    ) -> int:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        level = 0
        if isinstance(exception, errors.ParserError):
            if self._parser_error:
                await utilities.await_if_async(self._parser_error, ctx, exception)
                level = 100  # We don't want to re-raise a parser error if it was caught

        elif self._error:
            result = await utilities.await_if_async(self._error, ctx, exception)
            if result is True:
                level += 1
            elif result is False:
                level -= 1

        if hooks:
            level += sum(await asyncio.gather(*(hook.trigger_error(ctx, exception) for hook in hooks)))

        return level

    async def trigger_post_execution(
        self,
        ctx: abc.ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[abc.Hooks[abc.ContextT_contra]]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        if self._post_execution:
            await utilities.await_if_async(self._post_execution, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_post_execution(ctx) for hook in hooks))

    async def trigger_pre_execution(
        self,
        ctx: abc.ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[abc.Hooks[abc.ContextT_contra]]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        if self._pre_execution:
            await utilities.await_if_async(self._pre_execution, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_pre_execution(ctx) for hook in hooks))

    async def trigger_success(
        self,
        ctx: abc.ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[abc.Hooks[abc.ContextT_contra]]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        if self._success:
            await utilities.await_if_async(self._success, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_success(ctx) for hook in hooks))


AnyHooks = Hooks[abc.Context]
"""Hooks that can be used with any context.

.. note::
    This is shorthand for Hooks[tanjun.abc.Context].
"""

MessageHooks = Hooks[abc.MessageContext]
"""Hooks that can be used with a message context.

.. note::
    This is shorthand for Hooks[tanjun.abc.MessageContext].
"""

SlashHooks = Hooks[abc.SlashContext]
"""Hooks that can be used with a slash context.

.. note::
    This is shorthand for Hooks[tanjun.abc.SlashContext].
"""
