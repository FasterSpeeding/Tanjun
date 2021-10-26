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

__all__: list[str] = [
    "AbstractRepeater",
    "CallbackSig",
    "CallbackSigT",
    "Repeater",
    "with_ignored_exceptions",
    "with_fatal_exceptions",
]

import abc
import asyncio
import collections.abc
import datetime
import typing

CallbackSig = collections.abc.Callable[..., collections.abc.Awaitable[None]]
CallbackSigT = typing.TypeVar("CallbackSigT", bound=CallbackSig)


class AbstractRepeater(abc.ABC):
    """Abstract repeater class."""

    __slots__ = ()

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
        CallbackSig
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

    __slots__ = (
        "_max_runs",
        "_event_loop",
        "_callback",
        "_pre_callback",
        "_post_callback",
        "_iteration_count",
        "_ignored_exceptions",
        "_fatal_exceptions",
        "_task",
        "_delay",
    )

    def __init__(
        self,
        callback: CallbackSigT,
        delay: typing.Union[datetime.timedelta, int, float],
        /,
        *,
        max_runs: typing.Optional[int] = None,
        event_loop: typing.Optional[asyncio.AbstractEventLoop] = None,
    ):
        if isinstance(delay, datetime.timedelta):
            self._delay: datetime.timedelta = delay
        else:
            self._delay: datetime.timedelta = datetime.timedelta(seconds=delay)
        self._max_runs = max_runs
        self._event_loop = event_loop
        self._callback = callback
        self._pre_callback: typing.Optional[CallbackSig] = None
        self._post_callback: typing.Optional[CallbackSig] = None
        self._iteration_count: int = 0
        self._ignored_exceptions: list[type[Exception]] = []
        self._fatal_exceptions: list[type[Exception]] = []
        self._task: typing.Optional[asyncio.Task[None]] = None

    if typing.TYPE_CHECKING:
        __call__: CallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback(*args, **kwargs)

    def set_pre_callback(self, callback: CallbackSigT, /) -> Repeater[CallbackSigT]:
        """
        Set the callback executed before the repeater starts to run.

        Parameters
        ----------
        callback : CallbackSig
            The callback to set.

        Returns
        -------
        Self
            The repeater instance to enable chained calls.
        """
        self._pre_callback = callback
        return self

    def set_post_callback(self, callback: CallbackSigT, /) -> Repeater[CallbackSigT]:
        """
        Set the callback executed after the repeater is finished.

        Parameters
        ----------
        callback : CallbackSig
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
        except Exception as e:  # noqa 722 do not use bare except
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
            assert self._event_loop
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
        if not self._event_loop:
            self._event_loop = asyncio.get_running_loop()
        if self._task is not None and not self._task.done():
            raise RuntimeError("Repeater already running")
        self._task = self._event_loop.create_task(self._loop())
        return self._task

    def stop(self) -> None:
        if self._task is None or self._task.done():
            raise RuntimeError("Repeater not running")
        self._task.cancel()
        if self._post_callback:
            assert self._event_loop
            self._event_loop.create_task(self._post_callback())

    @property
    def callback(self) -> CallbackSig:
        return self._callback

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    def with_pre_callback(self, callback: CallbackSig) -> CallbackSig:
        """Set the callback executed before the repeater is finished.

        Parameters
        ----------
        callback : CallbackSig
            The callback to set.

        Returns
        -------
        CallbackSig
            The callback.

        Examples
        --------
        ```py
        @component.with_repeater(
            delay=1,
            max_runs=20
        )
        async def repeater():
            global counter
            counter += 1
            print(f"Run #{counter}")


        @repeater.with_pre_callback
        async def pre():
            print("pre callback")
        ```
        """
        self._pre_callback = callback
        return callback

    def with_post_callback(self, callback: CallbackSig) -> CallbackSig:
        """Set the callback executed after the repeater is finished.

        Parameters
        ----------
        callback : CallbackSig
            The callback to set.

        Returns
        -------
        CallbackSig
            The callback.

        Examples
        --------
        ```py
        @component.with_repeater(
            delay=1,
            max_runs=20
        )
        async def repeater():
            global counter
            counter += 1
            print(f"Run #{counter}")


        @repeater.with_post_callback
        async def post():
            print("pre callback")
        ```
        """
        self._post_callback = callback
        return callback

    def set_ignored_exceptions(self, *exceptions: type[Exception]) -> Repeater[CallbackSigT]:
        """
        Set the exceptions that a task will ignore.

        If any of these exceptions are encountered, there will be nothing printed to console

        Parameters
        ----------
        exceptions : list[type[Exception]]
            List of exception types

        Returns
        -------
        Repeater[CallbackSigT]
            Self
        """
        self._ignored_exceptions = list(exceptions)
        return self

    def set_fatal_exceptions(self, *exceptions: type[Exception]) -> Repeater[CallbackSigT]:
        """
        Set the exceptions that will stop a task.

        If any of these exceptions are encountered, the task will stop.

        Parameters
        ----------
        exceptions : list[type[Exception]]
            List of exception types

        Returns
        -------
        Repeater[CallbackSigT]
            Self
        """
        self._fatal_exceptions = list(exceptions)
        return self


def with_ignored_exceptions(
    *exceptions: type[Exception],
) -> collections.abc.Callable[[Repeater[CallbackSigT]], Repeater[CallbackSigT]]:
    """
    Set the exceptions that a task will ignore.

    If any of these exceptions are encountered, there will be nothing printed to console.

    .. note:: Even if an exception is ignored, it will stop that iteration of the repeater.

    Parameters
    ----------
    exceptions : list[type[Exception]]
        List of exception types

    Examples
    --------
    ```py
    @tanjun.with_ignored_exceptions(ZeroDivisionError)
    @tanjun.as_repeater(seconds=1)
    async def repeater():
        global run_count
        run_count += 1
        print(f"Run #{run_count}")
    ```
    """
    for exception in exceptions:
        exc = typing.cast("type[typing.Any]", exception)
        if not issubclass(exc, Exception):
            raise TypeError(f"Ignored exception must derive from Exception, is {exception.__name__}")  # typing: ignore

    def decorator(repeater: Repeater[CallbackSigT]) -> Repeater[CallbackSigT]:
        repeater.set_ignored_exceptions(*exceptions)
        return repeater

    return decorator


def with_fatal_exceptions(
    *exceptions: type[Exception],
) -> collections.abc.Callable[[Repeater[CallbackSigT]], Repeater[CallbackSigT]]:
    """
    Set the exceptions that will stop a task.

    If any of these exceptions are encountered, the task will stop.

    Parameters
    ----------
    exceptions : list[type[Exception]]
        List of exception types

    Examples
    --------
    ```py
    @tanjun.with_fatal_exceptions(ZeroDivisionError, RuntimeError)
    @tanjun.as_repeater(seconds=1)
    async def repeater():
        global run_count
        run_count += 1
        print(f"Run #{run_count}")
    ```
    """
    for exception in exceptions:
        exc = typing.cast("type[typing.Any]", exception)
        if not issubclass(exc, Exception):
            raise TypeError(f"Fatal exception must derive from Exception, is {exception.__name__}")  # typing: ignore

    def decorator(repeater: Repeater[CallbackSigT]) -> Repeater[CallbackSigT]:
        repeater.set_fatal_exceptions(*exceptions)
        return repeater

    return decorator
