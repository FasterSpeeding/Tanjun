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
"""Interface and interval implementation for a Tanjun based callback scheduler."""
from __future__ import annotations

__all__: list[str] = ["AbstractSchedule", "IntervalSchedule", "as_interval"]

import abc
import asyncio
import copy
import datetime
import typing

from alluka import abc as alluka

from . import components

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from . import abc as tanjun_abc

    _CallbackSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]]
    _IntervalScheduleT = typing.TypeVar("_IntervalScheduleT", bound="IntervalSchedule[typing.Any]")
    _OtherCallbackT = typing.TypeVar("_OtherCallbackT", bound="_CallbackSig")
    _T = typing.TypeVar("_T")

_CallbackSigT = typing.TypeVar("_CallbackSigT", bound="_CallbackSig")


class AbstractSchedule(abc.ABC):
    """Abstract callback schedule class."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CallbackSig:
        """Return the callback attached to the schedule.

        This will be an asynchronous function which takes zero positional
        arguments, returns `None` and may be relying on dependency injection.
        """

    @property
    @abc.abstractmethod
    def is_alive(self) -> bool:
        """Whether the schedule is alive."""

    @property
    @abc.abstractmethod
    def iteration_count(self) -> int:
        """Return the number of times this schedule has run.

        This increments after a call regardless of if it failed.
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
    def start(self, client: alluka.Client, /, *, loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the schedule.

        Parameters
        ----------
        alluka.abc.Client
            The injector client calls should be resolved with.

        Other Parameters
        ----------------
        loop : asyncio.AbstractEventLoop | None
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


@typing.runtime_checkable
class _ComponentProto(typing.Protocol):
    def add_schedule(self, schedule: AbstractSchedule, /) -> typing.Any:
        raise NotImplementedError


def as_interval(
    interval: typing.Union[int, float, datetime.timedelta],
    /,
    *,
    fatal_exceptions: collections.Sequence[type[Exception]] = (),
    ignored_exceptions: collections.Sequence[type[Exception]] = (),
    max_runs: typing.Optional[int] = None,
) -> collections.Callable[[_CallbackSigT], IntervalSchedule[_CallbackSigT]]:
    """Decorator to create an schedule.

    Parameters
    ----------
    interval : int | float | datetime.timedelta
        The callback for the schedule.

        This should be an asynchronous function which takes no positional
        arguments, returns `None` and may use dependency injection.

    Other Parameters
    ----------------
    fatal_exceptions : collections.abc.Sequence[type[Exception]]
        A sequence of exceptions that will cause the schedule to stop if raised
        by the callback, start callback or stop callback.

        Defaults to no exceptions.
    ignored_exceptions : collections.abc.Sequence[type[Exception]]
        A sequence of exceptions that should be ignored if raised by the
        callback, start callback or stop callback.

        Defaults to no exceptions.
    max_runs : int | None
        The maximum amount of times the schedule runs. Defaults to no maximum.

    Returns
    -------
    collections.Callable[[_CallbackSigT], tanjun.scheduling.IntervalSchedule[_CallbackSigT]]
        The decorator used to create the schedule.
    """
    return lambda callback: IntervalSchedule(
        callback,
        interval,
        fatal_exceptions=fatal_exceptions,
        ignored_exceptions=ignored_exceptions,
        max_runs=max_runs,
    )


class IntervalSchedule(typing.Generic[_CallbackSigT], components.AbstractComponentLoader, AbstractSchedule):
    """A callback schedule with an interval between calls."""

    __slots__ = (
        "_callback",
        "_fatal_exceptions",
        "_ignored_exceptions",
        "_interval",
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
        fatal_exceptions: collections.Sequence[type[Exception]] = (),
        ignored_exceptions: collections.Sequence[type[Exception]] = (),
        max_runs: typing.Optional[int] = None,
    ) -> None:
        """Initialise an interval schedule.

        Parameters
        ----------
        callback : collections.abc.Callable[...,  collections.abc.Awaitable[None]]
            The callback for the schedule.

            This should be an asynchronous function which takes no positional
            arguments, returns `None` and may use dependency injection.
        interval : datetime.timedelta | int | float
            The interval between calls. Passed as a timedelta, or a number of seconds.

        Other Parameters
        ----------------
        fatal_exceptions : collections.abc.Sequence[type[Exception]]
            A sequence of exceptions that will cause the schedule to stop if raised
            by the callback, start callback or stop callback.

            Defaults to no exceptions.
        ignored_exceptions : collections.abc.Sequence[type[Exception]]
            A sequence of exceptions that should be ignored if raised by the
            callback, start callback or stop callback.

            Defaults to no exceptions.
        max_runs : int | None
            The maximum amount of times the schedule runs. Defaults to no maximum.
        """
        if isinstance(interval, datetime.timedelta):
            self._interval: datetime.timedelta = interval
        else:
            self._interval = datetime.timedelta(seconds=interval)

        self._callback = callback
        self._fatal_exceptions = tuple(fatal_exceptions)
        self._ignored_exceptions = tuple(ignored_exceptions)
        self._iteration_count: int = 0
        self._max_runs = max_runs
        self._stop_callback: typing.Optional[_CallbackSig] = None
        self._start_callback: typing.Optional[_CallbackSig] = None
        self._task: typing.Optional[asyncio.Task[None]] = None

    @property
    def callback(self) -> _CallbackSigT:
        # <<inherited docstring from IntervalSchedule>>.
        return self._callback

    @property
    def interval(self) -> datetime.timedelta:
        """The interval between scheduled callback calls."""
        return self._interval

    @property
    def is_alive(self) -> bool:
        # <<inherited docstring from IntervalSchedule>>.
        return self._task is not None

    @property
    def iteration_count(self) -> int:
        # <<inherited docstring from IntervalSchedule>>.
        return self._iteration_count

    if typing.TYPE_CHECKING:
        __call__: _CallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    def copy(self: _IntervalScheduleT) -> _IntervalScheduleT:
        # <<inherited docstring from IntervalSchedule>>.
        if self._task:
            raise RuntimeError("Cannot copy an active schedule")

        return copy.copy(self)

    def load_into_component(self, component: tanjun_abc.Component, /) -> None:
        # <<inherited docstring from tanjun.components.AbstractComponentLoader>>.
        if isinstance(component, _ComponentProto):
            component.add_schedule(self)

    def set_start_callback(self: _IntervalScheduleT, callback: _CallbackSig, /) -> _IntervalScheduleT:
        """Set the callback executed before the schedule starts to run.

        Parameters
        ----------
        callback : CallbackSig
            The callback to set.

        Returns
        -------
        Self
            The schedule instance to enable chained calls.
        """
        self._start_callback = callback
        return self

    def set_stop_callback(self: _IntervalScheduleT, callback: _CallbackSig, /) -> _IntervalScheduleT:
        """Set the callback executed after the schedule is finished.

        Parameters
        ----------
        callback : collections.abc.Callable[...,  collections.abc.Awaitable[None]]
            The callback to set.

        Returns
        -------
        Self
            The schedule instance to enable chained calls.
        """
        self._stop_callback = callback
        return self

    async def _execute(self, client: alluka.Client, /) -> None:
        try:
            await client.call_with_async_di(self._callback)

        except self._fatal_exceptions:
            self.stop()
            raise

        except self._ignored_exceptions:
            pass

    async def _loop(self, client: alluka.Client, /) -> None:
        event_loop = asyncio.get_running_loop()
        try:
            if self._start_callback:
                try:
                    await client.call_with_async_di(self._start_callback)

                except self._ignored_exceptions:
                    pass

            while not self._max_runs or self._iteration_count < self._max_runs:
                self._iteration_count += 1
                event_loop.create_task(self._execute(client))
                await asyncio.sleep(self._interval.total_seconds())

        finally:
            self._task = None
            if self._stop_callback:
                try:
                    await client.call_with_async_di(self._stop_callback)

                except self._ignored_exceptions:
                    pass

    def start(self, client: alluka.Client, /, *, loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if self._task:
            raise RuntimeError("Cannot start an active schedule")

        loop = loop or asyncio.get_running_loop()

        if not loop.is_running():
            raise RuntimeError("Event loop is not running")

        self._task = loop.create_task(self._loop(client))

    def stop(self) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if not self._task:
            raise RuntimeError("Schedule is not running")

        self._task.cancel()
        self._task = None

    def with_start_callback(self, callback: _OtherCallbackT, /) -> _OtherCallbackT:
        """Set the callback executed before the schedule is finished/stopped.

        Parameters
        ----------
        callback : collections.abc.Callable[...,  collections.abc.Awaitable[None]]
            The callback to set.

        Returns
        -------
        collections.abc.Callable[...,  collections.abc.Awaitable[None]]
            The added callback.

        Examples
        --------
        ```py
        @component.with_schedule()
        @tanjun.as_interval(1, max_runs=20)
        async def interval():
            global counter
            counter += 1
            print(f"Run #{counter}")

        @interval.with_start_callback
        async def pre():
            print("pre callback")
        ```
        """
        self.set_start_callback(callback)
        return callback

    def with_stop_callback(self, callback: _OtherCallbackT, /) -> _OtherCallbackT:
        """Set the callback executed after the schedule is finished.

        Parameters
        ----------
        callback : collections.abc.Callable[...,  collections.abc.Awaitable[None]]
            The callback to set.

        Returns
        -------
        collections.abc.Callable[...,  collections.abc.Awaitable[None]]
            The added callback.

        Examples
        --------
        ```py
        @component.with_schedule()
        @tanjun.as_interval(1, max_runs=20)
        async def interval():
            global counter
            counter += 1
            print(f"Run #{counter}")


        @interval.with_stop_callback
        async def post():
            print("pre callback")
        ```
        """
        self.set_stop_callback(callback)
        return callback

    def set_ignored_exceptions(self: _IntervalScheduleT, *exceptions: type[Exception]) -> _IntervalScheduleT:
        """Set the exceptions that a schedule will ignore.

        If any of these exceptions are encountered, there will be nothing printed to console.

        Parameters
        ----------
        *exceptions : type[Exception]
            Types of the exceptions to ignore.

        Returns
        -------
        Self
            The schedule object to enable chained calls.
        """
        self._ignored_exceptions = exceptions
        return self

    def set_fatal_exceptions(self: _IntervalScheduleT, *exceptions: type[Exception]) -> _IntervalScheduleT:
        """Set the exceptions that will stop a schedule.

        If any of these exceptions are encountered, the task will stop.

        Parameters
        ----------
        *exceptions : type[Exception]
            Types of the exceptions to stop the task on.

        Returns
        -------
        Self
            The schedule object to enable chianed calls.
        """
        self._fatal_exceptions = exceptions
        return self
