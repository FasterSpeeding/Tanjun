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
"""A way to add repeating tasks to Tanjun bots."""
from __future__ import annotations

__all__: list[str] = ["AbstractRepeater", "CallbackSig", "CallbackSigT", "Repeater"]

import abc
import asyncio
import datetime
import typing

CallbackSig = typing.Callable[..., typing.Awaitable[typing.Any]]
CallbackSigT = typing.TypeVar("CallbackSigT", bound=CallbackSig)


class AbstractRepeater(abc.ABC):
    @property
    @abc.abstractmethod
    def iteration_count(self) -> int:
        """Return the number of times this repeater has run.

        Returns
        -------
        int
            The number of times this repeater has run. Increments after
            the callback is called, regardless if it was successful or not.
        """

    @abc.abstractmethod
    def start(self) -> asyncio.Task[None]:
        """
        Start the repeater.

        Returns
        -------
        asyncio.Task
            The task running the actual repeating loop.
        """

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the repeater."""

    @property
    @abc.abstractmethod
    def callback(self) -> CallbackSig:
        """Return the callback attached to the repeater.

        Returns
        -------
        typing.Callable[..., typing.Awaitable[typing.Any]]
            The callback attached to this repeater
        """


class Repeater(typing.Generic[CallbackSigT], AbstractRepeater):
    """A repeater whose callback is called with a specified delay.

    Parameters
    ----------
    callback : CallbackSigT
        The callback for the repeater
    delay : typing.Union[datetime.timedelta, int, float]
        The delay between callback calls. Passed as a timedelta, or a number of seconds.
    max_runs : typing.Optional[int]
        The maximum amount of times the repeater runs. Defaults to no maximum.
    event_loop : typing.Optional[asyncio.AbstractEventLoop]
        The event loop the repeater runs on. Defaults to `asyncio.get_event_loop()`
    """

    def __init__(
        self,
        /,
        callback: CallbackSigT,
        *,
        delay: typing.Union[datetime.timedelta, int, float],
        max_runs: typing.Optional[int] = None,
        event_loop: typing.Optional[asyncio.AbstractEventLoop] = None,
    ):
        if isinstance(delay, datetime.timedelta):
            self._delay: datetime.timedelta = delay
        else:
            self._delay: datetime.timedelta = datetime.timedelta(seconds=delay)
        self._max_runs: typing.Optional[int] = max_runs
        self._event_loop = event_loop or asyncio.get_event_loop()
        self._callback: CallbackSig = callback
        self._pre_callback: typing.Optional[CallbackSig] = None
        self._post_callback: typing.Optional[CallbackSig] = None
        self._iteration_count: int = 0
        self._ignored_exceptions: typing.List[type[Exception]] = []
        self._fatal_exceptions: typing.List[type[Exception]] = []
        self._task: typing.Optional[asyncio.Task[None]] = None

    def __call__(self, *args: list[typing.Any], **kwargs: dict[typing.Any, typing.Any]):
        return self._callback(*args, **kwargs)

    def set_pre_callback(self, callback: CallbackSigT) -> Repeater[CallbackSigT]:
        """
        Set the callback executed before the repeater starts to run.

        Parameters
        ----------
        callback : typing.Callable[..., typing.Awaitable[typing.Any]]
            The callback to set.

        Returns
        -------
        Repeater[CallbackSigT]
            Self
        """
        self._pre_callback = callback
        return self

    def set_post_callback(self, callback: CallbackSigT) -> Repeater[CallbackSigT]:
        """
        Set the callback executed after the repeater is finished.

        Parameters
        ----------
        callback : typing.Callable[..., typing.Awaitable[typing.Any]]
            The callback to set.

        Returns
        -------
        Repeater[CallbackSigT]
            Self
        """
        self._post_callback = callback
        return self

    async def _wrapped_coro(self):
        try:
            await self._callback()
        except Exception as e:  # noqa - I have to
            if type(e) in self._fatal_exceptions:
                self.stop()
                raise
            if type(e) not in self._ignored_exceptions:
                raise

    async def _loop(self):
        if self._pre_callback:
            await self._pre_callback()
        while not self._max_runs or self._iteration_count < self._max_runs:
            self._iteration_count += 1
            self._event_loop.create_task(self._wrapped_coro())
            await asyncio.sleep(self._delay.total_seconds())
        if self._post_callback:
            await self._post_callback()

    @property
    def delay(self) -> datetime.timedelta:
        """Return the delay between callback calls.

        Returns
        -------
        datetime.timedelta:
            The delay between calls
        """
        return self._delay

    def start(self) -> asyncio.Task[None]:
        if self._task is not None and not self._task.done():
            raise RuntimeError("Repeater already running")
        self._task = self._event_loop.create_task(self._loop())
        return self._task

    def stop(self) -> None:
        if self._task is None or self._task.done():
            raise RuntimeError("Repeater not running")
        self._task.cancel()
        if self._post_callback:
            self._event_loop.create_task(self._post_callback())

    @property
    def callback(self) -> CallbackSig:
        return self._callback

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    def with_pre_callback(self, callback: CallbackSig) -> CallbackSig:
        self._pre_callback = callback
        return callback

    def with_post_callback(self, callback: CallbackSig) -> CallbackSig:
        self._post_callback = callback
        return callback
