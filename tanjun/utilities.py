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

__all__: typing.Sequence[str] = ["async_chain", "await_if_async", "gather_checks"]

import asyncio
import typing

_ValueT = typing.TypeVar("_ValueT")


async def async_chain(iterable: typing.Iterable[typing.AsyncIterable[_ValueT]]) -> typing.AsyncIterator[_ValueT]:
    for async_iterable in iterable:
        async for value in async_iterable:
            yield value


async def await_if_async(value: typing.Union[_ValueT, typing.Awaitable[_ValueT]]) -> _ValueT:
    if isinstance(value, typing.Awaitable):
        # For some reason MYPY thinks this returns typing.Any
        return typing.cast(_ValueT, await value)

    return value


class _FailedCheck(RuntimeError):
    ...


async def _wrap_check(check: typing.Awaitable[bool]) -> bool:
    if not await check:
        raise _FailedCheck

    return True


async def gather_checks(checks: typing.Iterable[typing.Awaitable[bool]]) -> bool:
    try:
        results = await asyncio.gather(*map(_wrap_check, checks))
        # min can't take an empty sequence so we need to have a special case for if no-checks
        # are passed.
        return bool(min(results)) if results else True

    except _FailedCheck:
        return False
