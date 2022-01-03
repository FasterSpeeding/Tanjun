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

__all__: list[str] = ["AbstractSchedule", "IntervalSchedule"]

import abc
import asyncio
import copy
import datetime
import typing
from collections import abc as collections

from . import injecting

_CallbackSig = collections.Callable[..., collections.Awaitable[None]]
_CallbackSigT = typing.TypeVar("_CallbackSigT", bound=_CallbackSig)
_OtherCallbackT = typing.TypeVar("_OtherCallbackT", bound=_CallbackSig)
_IntervalScheduleT = typing.TypeVar("_IntervalScheduleT", bound="IntervalSchedule[typing.Any]")
_T = typing.TypeVar("_T")


class AbstractSchedule(abc.ABC):
    """Abstract callback schedule class."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CallbackSig:
        """Return the callback attached to the schedule.

        Returns
        -------
        _CallbackSig
            The callback attached to this schedule.

            This should take no-positional arguments and may have injected
            keyword-arguments.
        """

    @property
    @abc.abstractmethod
    def iteration_count(self) -> int:
        """Return the number of times this schedule has run.

        Returns
        -------
        int
            The number of times this schedule has run. Increments after
            the callback is called, regardless if it was successful or not.
        """

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        """Copy the schedule.

        Returns
        -------
        Self
            The copied schedule.

        Raises
        ------
        RuntimeError
            If the schedule is active.
        """

    @abc.abstractmethod
    def start(
        self, client: injecting.InjectorClient, /, *, loop: typing.Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Start the schedule.

        Parameters
        ----------
        tanjun.injecting.InjectorClient
            The injector client calls should be resolved with.

        Other Parameters
        ----------------
        loop : typing.Optional[asyncio.AbstractEventLoop]
            The event loop to use. If not provided, the current event loop will
            be used.

        Raises
        ------
        RuntimeError
            If the scheduled callback is already running.
            If the current or provided event loop isn't running.
        """

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the schedule.

        Raises
        ------
        RuntimeError
            If the scheduled callback isn't running.
        """


class IntervalSchedule(typing.Generic[_CallbackSigT], AbstractSchedule):
    """A callback schedule with an interval between calls.

    Parameters
    ----------
    callback : CallbackSigT
        The callback for the schedule
    interval : typing.Union[datetime.timedelta, int, float]
        The interval between calls. Passed as a timedelta, or a number of seconds.
    max_runs : typing.Optional[int]
        The maximum amount of times the repeater runs. Defaults to no maximum.
    """

    __slots__ = (
        "_callback",
        "_interval",
        "_fatal_exceptions",
        "_ignored_exceptions",
        "_iteration_count",
        "_max_runs",
        "_stop_callback",
        "_start_callback",
        "_task",
    )

    def __init__(
        self,
        callback: _CallbackSigT,
        interval: typing.Union[datetime.timedelta, int, float],
        /,
        *,
        max_runs: typing.Optional[int] = None,
    ) -> None:
        if isinstance(interval, datetime.timedelta):
            self._interval: datetime.timedelta = interval
        else:
            self._interval: datetime.timedelta = datetime.timedelta(seconds=interval)

        self._callback = injecting.CallbackDescriptor[None](callback)
        self._fatal_exceptions: tuple[type[Exception], ...] = ()
        self._ignored_exceptions: tuple[type[Exception], ...] = ()
        self._iteration_count: int = 0
        self._max_runs = max_runs
        self._stop_callback: typing.Optional[injecting.CallbackDescriptor[None]] = None
        self._start_callback: typing.Optional[injecting.CallbackDescriptor[None]] = None
        self._task: typing.Optional[asyncio.Task[None]] = None

    if typing.TYPE_CHECKING:
        __call__: _CallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    @property
    def callback(self) -> _CallbackSigT:
        return typing.cast(_CallbackSigT, self._callback.callback)

    @property
    def interval(self) -> datetime.timedelta:
        """The interval between callback calls."""
        return self._interval

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    def copy(self: _IntervalScheduleT) -> _IntervalScheduleT:
        if self._task:
            raise RuntimeError("Cannot copy an active schedule")

        return copy.copy(self)

    def set_start_callback(self: _IntervalScheduleT, callback: _CallbackSig, /) -> _IntervalScheduleT:
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
        self._start_callback = injecting.CallbackDescriptor(callback)
        return self

    def set_stop_callback(self: _IntervalScheduleT, callback: _CallbackSig, /) -> _IntervalScheduleT:
        """
        Set the callback executed after the repeater is finished.

        Parameters
        ----------
        callback : CallbackSig
            The callback to set.

        Returns
        -------
        IntervalSchedule[CallbackSigT]
            Self
        """
        self._stop_callback = injecting.CallbackDescriptor(callback)
        return self

    async def _wrap_callback(
        self, client: injecting.InjectorClient, callback: injecting.CallbackDescriptor[None], /
    ) -> None:
        try:
            await callback.resolve(injecting.BasicInjectionContext(client))

        except self._fatal_exceptions:
            self.stop()
            raise

        except self._ignored_exceptions:
            pass

    async def _loop(self, client: injecting.InjectorClient, /) -> None:
        event_loop = asyncio.get_running_loop()
        try:
            if self._start_callback:
                await self._wrap_callback(client, self._start_callback)

            while not self._max_runs or self._iteration_count < self._max_runs:
                self._iteration_count += 1
                event_loop.create_task(self._wrap_callback(client, self._callback))
                await asyncio.sleep(self._interval.total_seconds())

        finally:
            if self._stop_callback:
                try:
                    await self._stop_callback.resolve(injecting.BasicInjectionContext(client))
                except self._fatal_exceptions:
                    pass

    def start(
        self, client: injecting.InjectorClient, /, *, loop: typing.Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        if self._task:
            raise RuntimeError("Scheduled callback is already active")

        loop = loop or asyncio.get_running_loop()

        if not loop.is_running():
            raise RuntimeError("Event loop is not running")

        self._task = loop.create_task(self._loop(client))

    def stop(self) -> None:
        if not self._task:
            raise RuntimeError("IntervalSchedule not running")

        self._task.cancel()
        self._task = None

    def with_start_callback(self, callback: _OtherCallbackT, /) -> _OtherCallbackT:
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
            interval=1,
            max_runs=20
        )
        async def repeater():
            global counter
            counter += 1
            print(f"Run #{counter}")


        @repeater.with_start_callback
        async def pre():
            print("pre callback")
        ```
        """
        self.set_start_callback(callback)
        return callback

    def with_stop_callback(self, callback: _OtherCallbackT, /) -> _OtherCallbackT:
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
            interval=1,
            max_runs=20
        )
        async def repeater():
            global counter
            counter += 1
            print(f"Run #{counter}")


        @repeater.with_stop_callback
        async def post():
            print("pre callback")
        ```
        """
        self.set_stop_callback(callback)
        return callback

    def set_ignored_exceptions(self: _IntervalScheduleT, *exceptions: type[Exception]) -> _IntervalScheduleT:
        """
        Set the exceptions that a task will ignore.

        If any of these exceptions are encountered, there will be nothing printed to console.

        Parameters
        ----------
        *exceptions : type[Exception]
            Types of the exceptions to ignore.

        Returns
        -------
        Self
            The repeater object to enable chained calls.
        """
        self._ignored_exceptions = exceptions
        return self

    def set_fatal_exceptions(self: _IntervalScheduleT, *exceptions: type[Exception]) -> _IntervalScheduleT:
        """
        Set the exceptions that will stop a task.

        If any of these exceptions are encountered, the task will stop.

        Parameters
        ----------
        *exceptions : type[Exception]
            Types of the exceptions to stop the task on.

        Returns
        -------
        Self
            The repeater object to enable chianed calls.
        """
        self._fatal_exceptions = exceptions
        return self
