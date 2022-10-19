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
"""Standard implementation of Tanjun's command execution hook models."""
from __future__ import annotations

__all__: list[str] = ["AnyHooks", "Hooks", "MenuHooks", "MessageHooks", "SlashHooks"]

import asyncio
import copy
import typing
from collections import abc as collections

from . import abc as tanjun
from . import errors

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    _CommandT = typing.TypeVar("_CommandT", bound=tanjun.ExecutableCommand[typing.Any])
    _ErrorHookSigT = typing.TypeVar("_ErrorHookSigT", bound=tanjun.ErrorHookSig)
    _HookSigT = typing.TypeVar("_HookSigT", bound=tanjun.HookSig)
    _HooksT = typing.TypeVar("_HooksT", bound="Hooks[typing.Any]")

_ContextT_contra = typing.TypeVar("_ContextT_contra", bound=tanjun.Context, contravariant=True)


class Hooks(tanjun.Hooks[_ContextT_contra]):
    """Standard implementation of [tanjun.abc.Hooks][] used for command execution.

    This will take either [tanjun.abc.Context][], [tanjun.abc.MessageContext][]
    or [tanjun.abc.SlashContext][] dependent on what its bound by (generic wise).

    !!! note
        This implementation adds a concept of parser errors which won't be
        dispatched to general "error" hooks and do not share the error
        suppression semantics as they favour to always suppress the error
        if a registered handler is found.
    """

    __slots__ = (
        "_error_callbacks",
        "_parser_error_callbacks",
        "_pre_execution_callbacks",
        "_post_execution_callbacks",
        "_success_callbacks",
    )

    def __init__(self) -> None:
        """Initialise a command hook object."""
        self._error_callbacks: list[tanjun.ErrorHookSig] = []
        self._parser_error_callbacks: list[tanjun.HookSig] = []
        self._pre_execution_callbacks: list[tanjun.HookSig] = []
        self._post_execution_callbacks: list[tanjun.HookSig] = []
        self._success_callbacks: list[tanjun.HookSig] = []

    def add_to_command(self, command: _CommandT, /) -> _CommandT:
        """Add this hook object to a command.

        !!! note
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
        command : tanjun.abc.ExecutableCommand
            The command to add the hooks to.

        Returns
        -------
        tanjun.abc.ExecutableCommand
            The command with the hooks added.
        """
        command.set_hooks(self)
        return command

    def copy(self) -> Self:
        """Copy this hook object."""
        return copy.deepcopy(self)  # TODO: maybe don't

    def add_on_error(self, callback: tanjun.ErrorHookSig, /) -> Self:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self._error_callbacks.append(callback)
        return self

    def set_on_error(self, callback: typing.Optional[tanjun.ErrorHookSig], /) -> Self:
        """Set the error callback for this hook object.

        !!! note
            This will not be called for [tanjun.ParserError][]s as these
            are generally speaking expected. To handle those see
            [Hooks.set_on_parser_error][tanjun.hooks.Hooks.set_on_parser_error].

        Parameters
        ----------
        callback
            The callback to set for this hook. This will remove any previously
            set callbacks.

            This callback should take two positional arguments (of type
            [tanjun.abc.Context][] and [Exception][]) and may be either
            synchronous or asynchronous.

            Returning [True][] indicates that the error should be suppressed,
            [False][] that it should be re-raised and [None][] that no decision
            has been made. This will be accounted for along with the decisions
            other error hooks make by majority rule.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._error_callbacks.clear()
        return self.add_on_error(callback) if callback else self

    def with_on_error(self, callback: _ErrorHookSigT, /) -> _ErrorHookSigT:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self.add_on_error(callback)
        return callback

    def add_on_parser_error(self, callback: tanjun.HookSig, /) -> Self:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self._parser_error_callbacks.append(callback)
        return self

    def set_on_parser_error(self, callback: typing.Optional[tanjun.HookSig], /) -> Self:
        """Set the parser error callback for this hook object.

        Parameters
        ----------
        callback
            The callback to set for this hook. This will remove any previously
            set callbacks.

            This callback should take two positional arguments (of type
            [tanjun.abc.Context][] and [tanjun.ParserError][]),
            return [None][] and may be either synchronous or asynchronous.

            It's worth noting that, unlike general error handlers, this will
            always suppress the error.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._parser_error_callbacks.clear()
        return self.add_on_parser_error(callback) if callback else self

    def with_on_parser_error(self, callback: _HookSigT, /) -> _HookSigT:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self.add_on_parser_error(callback)
        return callback

    def add_post_execution(self, callback: tanjun.HookSig, /) -> Self:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self._post_execution_callbacks.append(callback)
        return self

    def set_post_execution(self, callback: typing.Optional[tanjun.HookSig], /) -> Self:
        """Set the post-execution callback for this hook object.

        Parameters
        ----------
        callback
            The callback to set for this hook. This will remove any previously
            set callbacks.

            This callback should take one positional argument (of type
            [tanjun.abc.Context][]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._post_execution_callbacks.clear()
        return self.add_post_execution(callback) if callback else self

    def with_post_execution(self, callback: _HookSigT, /) -> _HookSigT:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self.add_post_execution(callback)
        return callback

    def add_pre_execution(self, callback: tanjun.HookSig, /) -> Self:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self._pre_execution_callbacks.append(callback)
        return self

    def set_pre_execution(self, callback: typing.Optional[tanjun.HookSig], /) -> Self:
        """Set the pre-execution callback for this hook object.

        Parameters
        ----------
        callback
            The callback to set for this hook. This will remove any previously
            set callbacks.

            This callback should take one positional argument (of type
            [tanjun.abc.Context][]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._pre_execution_callbacks.clear()
        return self.add_pre_execution(callback) if callback else self

    def with_pre_execution(self, callback: _HookSigT, /) -> _HookSigT:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self.add_pre_execution(callback)
        return callback

    def add_on_success(self, callback: tanjun.HookSig, /) -> Self:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self._success_callbacks.append(callback)
        return self

    def set_on_success(self, callback: typing.Optional[tanjun.HookSig], /) -> Self:
        """Set the success callback for this hook object.

        Parameters
        ----------
        callback
            The callback to set for this hook. This will remove any previously
            set callbacks.

            This callback should take one positional argument (of type
            [tanjun.abc.Context][]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._success_callbacks.clear()
        return self.add_on_success(callback) if callback else self

    def with_on_success(self, callback: _HookSigT, /) -> _HookSigT:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        self.add_on_success(callback)
        return callback

    async def trigger_error(
        self,
        ctx: _ContextT_contra,
        /,
        exception: Exception,
        *,
        hooks: typing.Optional[collections.Set[tanjun.Hooks[_ContextT_contra]]] = None,
    ) -> int:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        level = 0
        if isinstance(exception, errors.ParserError):
            if self._parser_error_callbacks:
                await asyncio.gather(*(ctx.call_with_async_di(c, ctx, exception) for c in self._parser_error_callbacks))
                level = 100  # We don't want to re-raise a parser error if it was caught

        elif self._error_callbacks:
            results = await asyncio.gather(*(ctx.call_with_async_di(c, ctx, exception) for c in self._error_callbacks))
            level = results.count(True) - results.count(False)

        if hooks:
            level += sum(await asyncio.gather(*(hook.trigger_error(ctx, exception) for hook in hooks)))

        return level

    async def trigger_post_execution(
        self,
        ctx: _ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[tanjun.Hooks[_ContextT_contra]]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        if self._post_execution_callbacks:
            await asyncio.gather(*(ctx.call_with_async_di(c, ctx) for c in self._post_execution_callbacks))

        if hooks:
            await asyncio.gather(*(hook.trigger_post_execution(ctx) for hook in hooks))

    async def trigger_pre_execution(
        self,
        ctx: _ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[tanjun.Hooks[_ContextT_contra]]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        if self._pre_execution_callbacks:
            await asyncio.gather(*(ctx.call_with_async_di(c, ctx) for c in self._pre_execution_callbacks))

        if hooks:
            await asyncio.gather(*(hook.trigger_pre_execution(ctx) for hook in hooks))

    async def trigger_success(
        self,
        ctx: _ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[tanjun.Hooks[_ContextT_contra]]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Hooks>>.
        if self._success_callbacks:
            await asyncio.gather(*(ctx.call_with_async_di(c, ctx) for c in self._success_callbacks))

        if hooks:
            await asyncio.gather(*(hook.trigger_success(ctx) for hook in hooks))


AnyHooks = Hooks[tanjun.Context]
"""Hooks that can be used with any context.

!!! note
    This is shorthand for `Hooks[tanjun.abc.Context]`.
"""

MenuHooks = Hooks[tanjun.MenuContext]
"""Hooks that can be used with a menu context.

!!! note
    This is shorthand for `Hooks[tanjun.abc.MenuContext]`.
"""

MessageHooks = Hooks[tanjun.MessageContext]
"""Hooks that can be used with a message context.

!!! note
    This is shorthand for `Hooks[tanjun.abc.MessageContext]`.
"""

SlashHooks = Hooks[tanjun.SlashContext]
"""Hooks that can be used with a slash context.

!!! note
    This is shorthand for `Hooks[tanjun.abc.SlashContext]`.
"""
