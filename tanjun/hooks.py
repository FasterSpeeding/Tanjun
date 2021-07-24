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

__all__: typing.Sequence[str] = ["ErrorHookSig", "Hooks", "HookSig", "ParserHookSig"]

import asyncio
import copy
import typing

from tanjun import errors
from tanjun import traits
from tanjun import utilities

if typing.TypeVar:
    _HooksT = typing.TypeVar("_HooksT", bound="Hooks[typing.Any]")

CommandT = typing.TypeVar("CommandT", bound=traits.ExecutableCommand[typing.Any])

ParserHookSig = typing.Callable[
    ["traits.ContextT", "errors.ParserError"], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
"""Type hint of the callback used as a parser error hook.

This will be called whenever a `tanjun.errors.ParserError` is raised during the
command argument parsing stage, will have to take two positional arguments - of
type `tanjun.traits.Context` and `tanjun.errors.ParserError` - and may either be
a synchronous or asynchronous callback which returns `None`
"""

ErrorHookSig = typing.Callable[
    ["traits.ContextT", BaseException], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
"""Type hint of the callback used as a unexpected command error hook.

This will be called whenever a `BaseException` is raised during the
execution stage whenever the command callback raises any exception except
`tanjun.errors.CommandError`,  will have to take two positional arguments - of
type `tanjun.traits.Context` and `BaseException` - and may either be a
synchronous or asynchronous callback which returns `None`
"""

HookSig = typing.Callable[["traits.ContextT"], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]]
"""Type hint of the callback used as a general command hook.

This may be called during different stages of command execution (decided by
which hook this is registered as), will have to take one positional argument of
type `tanjun.traits.Context` and may be a synchronous or asynchronous callback
which returns `None`.
"""


class Hooks(traits.Hooks[traits.ContextT_contra]):
    __slots__: typing.Sequence[str] = ("_error", "_parser_error", "_pre_execution", "_post_execution", "_success")

    def __init__(self) -> None:
        self._error: typing.Optional[ErrorHookSig[traits.ContextT_contra]] = None
        self._parser_error: typing.Optional[ParserHookSig[traits.ContextT_contra]] = None
        self._pre_execution: typing.Optional[HookSig[traits.ContextT_contra]] = None
        self._post_execution: typing.Optional[HookSig[traits.ContextT_contra]] = None
        self._success: typing.Optional[HookSig[traits.ContextT_contra]] = None

    def __repr__(self) -> str:
        return (
            f"Hooks <{self._error!r}, {self._parser_error!r}, {self._pre_execution!r}, "
            f"{self._post_execution!r}, {self._success!r}>"
        )

    def add_to_command(self, command: CommandT, /) -> CommandT:
        command.set_hooks(self)
        return command

    def copy(self: _HooksT) -> _HooksT:
        return copy.deepcopy(self)

    def set_on_error(self: _HooksT, hook: typing.Optional[ErrorHookSig[traits.ContextT_contra]], /) -> _HooksT:
        self._error = hook
        return self

    def with_on_error(self, hook: ErrorHookSig[traits.ContextT_contra], /) -> ErrorHookSig[traits.ContextT_contra]:
        self.set_on_error(hook)
        return hook

    def set_on_parser_error(self: _HooksT, hook: typing.Optional[ParserHookSig[traits.ContextT_contra]], /) -> _HooksT:
        self._parser_error = hook
        return self

    def with_on_parser_error(
        self, hook: ParserHookSig[traits.ContextT_contra], /
    ) -> ParserHookSig[traits.ContextT_contra]:
        self.set_on_parser_error(hook)
        return hook

    def set_post_execution(self: _HooksT, hook: typing.Optional[HookSig[traits.ContextT_contra]], /) -> _HooksT:
        self._post_execution = hook
        return self

    def with_post_execution(self, hook: HookSig[traits.ContextT_contra], /) -> HookSig[traits.ContextT_contra]:
        self.set_post_execution(hook)
        return hook

    def set_pre_execution(self: _HooksT, hook: typing.Optional[HookSig[traits.ContextT_contra]], /) -> _HooksT:
        self._pre_execution = hook
        return self

    def with_pre_execution(self, hook: HookSig[traits.ContextT_contra], /) -> HookSig[traits.ContextT_contra]:
        self.set_pre_execution(hook)
        return hook

    def set_on_success(self: _HooksT, hook: typing.Optional[HookSig[traits.ContextT_contra]], /) -> _HooksT:
        self._success = hook
        return self

    def with_on_success(self, hook: HookSig[traits.ContextT_contra], /) -> HookSig[traits.ContextT_contra]:
        self.set_on_success(hook)
        return hook

    async def trigger_error(
        self,
        ctx: traits.ContextT_contra,
        /,
        exception: BaseException,
        *,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks[traits.ContextT_contra]]] = None,
    ) -> None:  # TODO: return True to indicate "raise" else False or None to suppress
        if self._error:
            await utilities.await_if_async(self._error, ctx, exception)

        if hooks:
            await asyncio.gather(*(hook.trigger_error(ctx, exception) for hook in hooks))

    async def trigger_parser_error(
        self,
        ctx: traits.ContextT_contra,
        /,
        exception: errors.ParserError,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks[traits.ContextT_contra]]] = None,
    ) -> None:
        if self._parser_error:
            await utilities.await_if_async(self._parser_error, ctx, exception)

        if hooks:
            await asyncio.gather(*(hook.trigger_parser_error(ctx, exception) for hook in hooks))

    async def trigger_post_execution(
        self,
        ctx: traits.ContextT_contra,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks[traits.ContextT_contra]]] = None,
    ) -> None:
        if self._post_execution:
            await utilities.await_if_async(self._post_execution, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_post_execution(ctx) for hook in hooks))

    async def trigger_pre_execution(
        self,
        ctx: traits.ContextT_contra,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks[traits.ContextT_contra]]] = None,
    ) -> None:
        if self._pre_execution:
            await utilities.await_if_async(self._pre_execution, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_post_execution(ctx) for hook in hooks))

    async def trigger_success(
        self,
        ctx: traits.ContextT_contra,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks[traits.ContextT_contra]]] = None,
    ) -> None:
        if self._success:
            await utilities.await_if_async(self._success, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_success(ctx) for hook in hooks))
