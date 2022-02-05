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
"""Manager which keeps tasks in-scope and alive until they are finished."""
from __future__ import annotations

__all__: list[str] = ["AbstractTaskManager", "TaskManager"]

import abc
import asyncio
import typing
from collections import abc as collections

if typing.TYPE_CHECKING:
    import typing_extensions

    _P = typing_extensions.ParamSpec("_P")


class AbstractTaskManager(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def add_task(
        self,
        callback: collections.Callable[_P, collections.Awaitable[typing.Any]],
        task_id: typing.Optional[str] = None,
        task_group: typing.Optional[str] = None,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> str:
        ...




class TaskManager(AbstractTaskManager):
    __slots__ = ("_loop", "_tasks")

    def __init__(self) -> None:
        self._loop: typing.Optional[asyncio.Task[None]]
        self._tasks: typing.List[asyncio.Task[None]] = []
