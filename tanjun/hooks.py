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
"""Standard implementation of Tanjun's command execution hook models."""
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
type `tanjun.abc.Context` and `tanjun.errors.ParserError` - and may be either
synchronous or asynchronous callback which returns `None`
"""

ErrorHookSig = collections.Callable[[abc.ContextT, Exception], abc.MaybeAwaitableT[typing.Optional[bool]]]
"""Type hint of the callback used as a unexpected command error hook.

This will be called whenever a `Exception` is raised during the
execution stage whenever the command callback raises any exception except
`tanjun.errors.CommandError`,  will have to take two positional arguments - of
type `tanjun.abc.Context` and `Exception` - and may be either a
synchronous or asynchronous callback which returns `bool` or `None`.

`True` is returned to indicate that the exception should be suppressed and
`False` is returned to indicate that the exception should be re-raised.
"""

HookSig = collections.Callable[[abc.ContextT], abc.MaybeAwaitableT[None]]
"""Type hint of the callback used as a general command hook.

This may be called during different stages of command execution (decided by
which hook this is registered as), will have to take one positional argument of
type `tanjun.abc.Context` and may be synchronous or asynchronous callback
which returns `None`.
"""


class Hooks(abc.Hooks[abc.ContextT_contra]):
    """Standard implementation of `tanjun.abc.Hooks` used for command execution.

    `tanjun.abc.ContextT_contra` will either be `tanjun.abc.Context`,
    `tanjun.abc.MessageContext` or `tanjun.abc.SlashContext`.

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

    def set_on_error(self: _HooksT, callback: typing.Optional[ErrorHookSig[abc.ContextT_contra]], /) -> _HooksT:
        """Set the error callback for this hook object.

        .. note::
            This will not be called for `tanjun.errors.ParserError`s as these
            are generally speaking expected. To handle those see
            `Hooks.set_on_parser_error`.

        Parameters
        ----------
        callback : typing.Optional[ErrorHookSig[tanjun.abc.ContextT_contra]]
            The callback to set for this hook, if `None` then any previously set
            callback will be removed.

            This callback should be a callback which takes two positional
            arguments (of type `tanjun.abc.ContextT_contra` and `Exception`) and
            may be either synchronous or asynchronous.

            If this returns `True` then that indicates that this error should
            be suppressed, with `False` indicating that it should be re-raise
            and `None` indicating no decision has been made. This will be
            accounted for along with the decisions the other error hooks make
            by majority rule.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._error = callback
        return self

    def with_on_error(self, callback: ErrorHookSig[abc.ContextT_contra], /) -> ErrorHookSig[abc.ContextT_contra]:
        """Set the error callback for this hook object through a decorator call.

        .. note::
            This will not be called for `tanjun.errors.ParserError`s as these
            are generally speaking expected. To handle those see
            `Hooks.with_on_parser_error`.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_error
        async def on_error(ctx: tanjun.abc.Context, error: Exception) -> bool:
            if isinstance(error, SomeExpectedType):
                await ctx.respond("You dun goofed")
                return True  # Indicating that it should be suppressed.

            await ctx.respond(f"An error occurred: {error}")
            return False  # Indicating that it should be re-raised
        ```

        Parameters
        ----------
        callback : ErrorHookSig[tanjun.abc.ContextT_contra]
            The callback to set for this hook.

            This callback should be a callback which takes two positional
            arguments (of type `tanjun.abc.ContextT_contra` and `Exception`) and
            may be either synchronous or asynchronous.

            If this returns `True` then that indicates that this error should
            be suppressed, with `False` indicating that it should be re-raise
            and `None` indicating no decision has been made. This will be
            accounted for along with the decisions the other error hooks make
            by majority rule.

        Returns
        -------
        ErrorHookSig[tanjun.abc.ContextT_contra]
            The hook callback which was set.
        """
        self.set_on_error(callback)
        return callback

    def set_on_parser_error(self: _HooksT, callback: typing.Optional[ParserHookSig[abc.ContextT_contra]], /) -> _HooksT:
        """Set the parser error callback for this hook object.

        Parameters
        ----------
        callback : typing.Optional[ParserHookSig[tanjun.abc.ContextT_contra]]
            The callback to set for this hook, if `None` then any previously set
            callback will be removed.

            This callback should be a callback which takes two positional
            arguments (of type `tanjun.abc.ContextT_contra` and `tanjun.errors.ParserError`),
            return `None` and may be either synchronous or asynchronous.

            It's worth noting that this unlike general error handlers, this will
            always suppress the error.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._parser_error = callback
        return self

    def with_on_parser_error(
        self, callback: ParserHookSig[abc.ContextT_contra], /
    ) -> ParserHookSig[abc.ContextT_contra]:
        """Set the parser error callback for this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_parser_error
        async def on_parser_error(ctx: tanjun.abc.Context, error: tanjun.errors.ParserError) -> None:
            await ctx.respond(f"You gave invalid input: {error}")
        ```

        Parameters
        ----------
        callback : ParserHookSig[tanjun.abc.ContextT_contra]
            The parser error callback to set for this hook.

            This callback should be a callback which takes two positional
            arguments (of type `tanjun.abc.ContextT_contra` and `tanjun.errors.ParserError`),
            return `None` and may be either synchronous or asynchronous.

        Returns
        -------
        ParserHookSig[tanjun.abc.ContextT_contra]
            The callback which was set.
        """
        self.set_on_parser_error(callback)
        return callback

    def set_post_execution(self: _HooksT, callback: typing.Optional[HookSig[abc.ContextT_contra]], /) -> _HooksT:
        """Set the post-execution callback for this hook object.

        Parameters
        ----------
        callback : typing.Optional[HookSig[tanjun.abc.ContextT_contra]]
            The callback to set for this hook, if `None` then any previously set
            callback will be removed.

            This callback should be a callback which takes one positional
            argument (of type `tanjun.abc.ContextT_contra`), return `None` and
            may be either synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._post_execution = callback
        return self

    def with_post_execution(self, callback: HookSig[abc.ContextT_contra], /) -> HookSig[abc.ContextT_contra]:
        """Set the post-execution callback for this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_post_execution
        async def post_execution(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You did something")
        ```

        Parameters
        ----------
        callback : HookSig[tanjun.abc.ContextT_contra]
            The post-execution callback to set for this hook.

            This callback should be a callback which takes one positional
            argument (of type `tanjun.abc.ContextT_contra`), return `None` and
            may be either synchronous or asynchronous.

        Returns
        -------
        HookSig[tanjun.abc.ContextT_contra]
            The post-execution callback which was set.
        """
        self.set_post_execution(callback)
        return callback

    def set_pre_execution(self: _HooksT, callback: typing.Optional[HookSig[abc.ContextT_contra]], /) -> _HooksT:
        """Set the pre-execution callback for this hook object.

        Parameters
        ----------
        callback : typing.Optional[HookSig[tanjun.abc.ContextT_contra]]
            The callback to set for this hook, if `None` then any previously set
            callback will be removed.

            This callback should be a callback which takes one positional
            argument (of type `tanjun.abc.ContextT_contra`), return `None` and
            may be either synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._pre_execution = callback
        return self

    def with_pre_execution(self, callback: HookSig[abc.ContextT_contra], /) -> HookSig[abc.ContextT_contra]:
        """Set the pre-execution callback for this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_pre_execution
        async def pre_execution(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You did something")
        ```

        Parameters
        ----------
        callback : HookSig[tanjun.abc.ContextT_contra]
            The pre-execution callback to set for this hook.

            This callback should be a callback which takes one positional
            argument (of type `tanjun.abc.ContextT_contra`), return `None` and
            may be either synchronous or asynchronous.

        Returns
        -------
        HookSig[tanjun.abc.ContextT_contra]
            The pre-execution callback which was set.
        """
        self.set_pre_execution(callback)
        return callback

    def set_on_success(self: _HooksT, callback: typing.Optional[HookSig[abc.ContextT_contra]], /) -> _HooksT:
        """Set the success callback for this hook object.

        Parameters
        ----------
        callback : typing.Optional[HookSig[tanjun.abc.ContextT_contra]]
            The callback to set for this hook, if `None` then any previously set
            callback will be removed.

            This callback should be a callback which takes one positional
            argument (of type `tanjun.abc.ContextT_contra`), return `None` and
            may be either synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """
        self._success = callback
        return self

    def with_on_success(self, callback: HookSig[abc.ContextT_contra], /) -> HookSig[abc.ContextT_contra]:
        """Set the success callback for this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_success
        async def on_success(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You did something")
        ```

        Parameters
        ----------
        callback : HookSig[tanjun.abc.ContextT_contra]
            The success callback to set for this hook.

            This callback should be a callback which takes one positional
            argument (of type `tanjun.abc.ContextT_contra`), return `None` and
            may be either synchronous or asynchronous.

        Returns
        -------
        HookSig[tanjun.abc.ContextT_contra]
            The success callback which was set.
        """
        self.set_on_success(callback)
        return callback

    async def trigger_error(
        self,
        ctx: abc.ContextT_contra,
        /,
        exception: Exception,
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
