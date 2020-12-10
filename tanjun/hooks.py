# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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

__all__: typing.Sequence[str] = ["Hooks"]

import asyncio
import typing

from tanjun import errors
from tanjun import traits
from tanjun import utilities
from tanjun.traits import Context


class Hooks(traits.Hooks):
    __slots__: typing.Sequence[str] = ("_error", "_parser_error", "_pre_execution", "_post_execution", "_success")

    def __init__(
        self,
        *,
        on_error: typing.Optional[traits.ErrorHookT] = None,
        parser_error: typing.Optional[traits.ParserHookT] = None,
        pre_execution: typing.Optional[traits.PreExecutionHookT] = None,
        post_execution: typing.Optional[traits.HookT] = None,
        on_success: typing.Optional[traits.HookT] = None,
    ) -> None:
        self._error = on_error
        self._parser_error = parser_error
        self._pre_execution = pre_execution
        self._post_execution = post_execution
        self._success = on_success

    def __repr__(self) -> str:
        return (
            f"Hooks <{self._error!r}, {self._parser_error!r}, {self._pre_execution!r}, "
            f"{self._post_execution!r}, {self._success!r}>"
        )

    def with_on_error(self, hook: typing.Optional[traits.ErrorHookT], /) -> typing.Optional[traits.ErrorHookT]:
        self._error = hook
        return hook

    def with_on_parser_error(self, hook: typing.Optional[traits.ParserHookT], /) -> typing.Optional[traits.ParserHookT]:
        self._parser_error = hook
        return hook

    def with_post_execution(self, hook: typing.Optional[traits.HookT], /) -> typing.Optional[traits.HookT]:
        self._post_execution = hook
        return hook

    def with_pre_execution(
        self, hook: typing.Optional[traits.PreExecutionHookT], /
    ) -> typing.Optional[traits.PreExecutionHookT]:
        self._pre_execution = hook
        return hook

    def with_on_success(self, hook: typing.Optional[traits.HookT], /) -> typing.Optional[traits.HookT]:
        self._success = hook
        return hook

    async def trigger_error(
        self,
        ctx: Context,
        /,
        exception: BaseException,
        *,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks]] = None,
    ) -> None:  # TODO: return True to indicate "raise" else False or None to suppress
        if self._error:
            await utilities.await_if_async(self._error, ctx, exception)

        if hooks:
            await asyncio.gather(*(hook.trigger_error(ctx, exception) for hook in hooks))

    async def trigger_parser_error(
        self,
        ctx: Context,
        /,
        exception: errors.ParserError,
        hooks: typing.Optional[typing.AbstractSet[traits.Hooks]] = None,
    ) -> None:
        if self._parser_error:
            await utilities.await_if_async(self._parser_error, ctx, exception)

        if hooks:
            await asyncio.gather(*(hook.trigger_parser_error(ctx, exception) for hook in hooks))

    async def trigger_post_execution(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[traits.Hooks]] = None
    ) -> None:
        if self._post_execution:
            await utilities.await_if_async(self._post_execution, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_post_execution(ctx) for hook in hooks))

    async def trigger_pre_execution(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[traits.Hooks]] = None,
    ) -> bool:
        if self._pre_execution and await utilities.await_if_async(self._pre_execution, ctx) is False:
            return False

        if hooks:
            return await utilities.gather_checks(hook.trigger_pre_execution(ctx) for hook in hooks)

        return True

    async def trigger_success(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[traits.Hooks]] = None
    ) -> None:
        if self._success:
            await utilities.await_if_async(self._success, ctx)

        if hooks:
            await asyncio.gather(*(hook.trigger_success(ctx) for hook in hooks))
