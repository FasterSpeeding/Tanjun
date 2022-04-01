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
import dataclasses
import datetime
import time
import typing
from collections import abc as collections

from alluka import abc as alluka

from . import components

if typing.TYPE_CHECKING:
    from . import abc as tanjun_abc

    _DatetimeT = typing.TypeVar("_DatetimeT", bound="_Datetime")
    _IntervalScheduleT = typing.TypeVar("_IntervalScheduleT", bound="IntervalSchedule[typing.Any]")
    _OtherCallbackT = typing.TypeVar("_OtherCallbackT", bound="_CallbackSig")
    _T = typing.TypeVar("_T")
    _TimeSchedule = typing.TypeVar("_TimeSchedule", bound="TimeSchedule[typing.Any]")

_CallbackSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]]
_CallbackSigT = typing.TypeVar("_CallbackSigT", bound="_CallbackSig")


class AbstractSchedule(abc.ABC):
    """Abstract callback schedule class."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CallbackSig:
        """Return the callback attached to the schedule.

        This will be an asynchronous function which takes zero positional
        arguments, returns [None][] and may be relying on dependency injection.
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
        client
            The injector client calls should be resolved with.
        loop
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
    interval
        The callback for the schedule.

        This should be an asynchronous function which takes no positional
        arguments, returns [None][] and may use dependency injection.
    fatal_exceptions
        A sequence of exceptions that will cause the schedule to stop if raised
        by the callback, start callback or stop callback.
    ignored_exceptions
        A sequence of exceptions that should be ignored if raised by the
        callback, start callback or stop callback.
    max_runs
        The maximum amount of times the schedule runs.

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
        "_tasks",
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
        callback : collections.abc.Callable[...,  collections.abc.Coroutine[Any, Any, None]]
            The callback for the schedule.

            This should be an asynchronous function which takes no positional
            arguments, returns [None][] and may use dependency injection.
        interval
            The interval between calls. Passed as a timedelta, or a number of seconds.
        fatal_exceptions
            A sequence of exceptions that will cause the schedule to stop if raised
            by the callback, start callback or stop callback.
        ignored_exceptions
            A sequence of exceptions that should be ignored if raised by the
            callback, start callback or stop callback.
        max_runs
            The maximum amount of times the schedule runs.
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
        self._tasks: list[asyncio.Task[None]] = []

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
        callback
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
        callback
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
                self._tasks.append(event_loop.create_task(self._execute(client)))
                await asyncio.sleep(self._interval.total_seconds())
                self._tasks = [task for task in self._tasks if not task.done()]

        finally:
            self._task = None
            if self._stop_callback:
                try:
                    await client.call_with_async_di(self._stop_callback)

                except self._ignored_exceptions:
                    pass

            self._tasks.clear()

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
        callback : collections.abc.Callable[...,  collections.abc.Coroutine[Any, Any, None]]
            The callback to set.

        Returns
        -------
        collections.abc.Callable[...,  collections.abc.Coroutine[Any, Any, None]]
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
        callback : collections.abc.Callable[...,  collections.abc.Coroutine[Any, Any, None]]
            The callback to set.

        Returns
        -------
        collections.abc.Callable[...,  collections.abc.Coroutine[Any, Any, None]]
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
        *exceptions
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
        *exceptions
            Types of the exceptions to stop the task on.

        Returns
        -------
        Self
            The schedule object to enable chianed calls.
        """
        self._fatal_exceptions = exceptions
        return self


def _to_list(
    values: typing.Union[int, collections.Collection[int], None], min_: int, max_: int, name: str
) -> typing.Optional[list[int]]:
    if values is None:
        return None

    if isinstance(values, int):
        values = [values]

    else:
        values = sorted(set(values))

    for value in values:
        if value > max_ or value < min_:
            raise ValueError(f"{name} value must be between {min_} and {max_}, not {value}")

    return values


def _get_next(target_values: list[int], current_value: int) -> tuple[int, int]:
    for index, value in enumerate(target_values):
        if value > current_value:
            return index, value

    return 0, target_values[0]


@dataclasses.dataclass
class _ScheduleConfig:
    __slots__ = ("days", "hours", "minutes", "months", "seconds", "timezone")
    days: typing.Optional[list[int]]
    hours: typing.Optional[list[int]]
    is_weekly: bool
    minutes: typing.Optional[list[int]]
    months: typing.Optional[list[int]]
    seconds: typing.Optional[list[int]]
    timezone: typing.Optional[datetime.timezone]


class _Datetime:
    __slots__ = ("config", "date")

    def __init__(self, config: _ScheduleConfig):
        self.config = config
        self.date = datetime.datetime.now(tz=config.timezone)

    def next(self) -> datetime.datetime:
        if self.config.months and self.date.month not in self.config.months:
            self.next_month()
            return self.date

        if self.config.days:
            day = self.date.weekday() if self.config.is_weekly else self.date.day
            if day not in self.config.days:
                self.next_day()
                return self.date

        if self.config.hours and self.date.hour not in self.config.hours:
            self.next_hour()
            return self.date

        if self.config.minutes and self.date.minute not in self.config.minutes:
            self.next_minute()
            return self.date

        if self.config.seconds and self.date.second not in self.config.seconds:
            self.next_second()
            return self.date

        raise NotImplementedError("Time schedules with no restrictions are not supported")

    def next_year(self: _DatetimeT) -> _DatetimeT:
        self.date = datetime.datetime(year=self.date.year + 1, month=0, day=0, hour=0, tzinfo=self.config.timezone)
        return self.next_month()

    def next_month(self: _DatetimeT) -> _DatetimeT:
        if not self.config.months or self.date.month in self.config.months:
            return self.next_hour()

        index, month = _get_next(self.config.months, self.date.month)

        if index == 0:
            return self.next_year()

        self.date = self.date.replace(month=month, hour=0, minute=0, second=0, microsecond=0)
        return self.next_hour()

    def next_day(self: _DatetimeT) -> _DatetimeT:
        if not self.config.days:
            return self

        if self.config.is_weekly:
            day = self.date.weekday()

        else:
            day = self.date.day

        if day in self.config.days:
            return self

        index, day = _get_next(self.config.days, day)

        if index == 0:
            if not self.config.is_weekly:
                return self.next_month()

            start_of_next_week = self.date.day + (7 - self.date.weekday())

            try:
                self.date = self.date.replace(day=start_of_next_week, hour=0, minute=0, second=0, microsecond=0)

            except ValueError:
                return self.next_month()

            return self.next_day()

        return self.next_hour()

    def next_hour(self: _DatetimeT) -> _DatetimeT:
        if not self.config.hours or self.date.hour in self.config.hours:
            return self.next_minute()

        index, hour = _get_next(self.config.hours, self.date.hour)

        if index == 0:
            return self.next_day()

        self.date = self.date.replace(hour=hour, minute=0, second=0, microsecond=0)
        return self.next_minute()

    def next_minute(self: _DatetimeT) -> _DatetimeT:
        if not self.config.minutes or self.date.minute in self.config.minutes:
            return self.next_second()

        index, minute = _get_next(self.config.minutes, self.date.minute)

        if index == 0:
            return self.next_minute()

        self.date = self.date.replace(minute=minute, second=0, microsecond=0)
        return self.next_second()

    def next_second(self: _DatetimeT) -> _DatetimeT:
        if not self.config.seconds or self.date.second not in self.config.seconds:
            self.date = self.date.replace(microsecond=0)
            return self

        index, second = _get_next(self.config.seconds, self.date.second)

        if index == 0:
            return self.next_minute()

        self.date = self.date.replace(second=second, microsecond=0)
        return self


class TimeSchedule(typing.Generic[_CallbackSigT], components.AbstractComponentLoader, AbstractSchedule):
    __slots__ = ("_callback", "_fatal_exceptions", "_ignored_exceptions", "_level", "_task", "_tasks")

    def __init__(
        self,
        callback: _CallbackSigT,
        /,
        *,
        months: typing.Union[int, collections.Collection[int], None] = None,
        weekly: bool = False,
        days: typing.Union[int, collections.Collection[int], None] = None,
        hours: typing.Union[int, collections.Collection[int], None] = None,
        minutes: typing.Union[int, collections.Collection[int], None] = None,
        seconds: typing.Union[int, collections.Collection[int], None] = None,
        fatal_exceptions: collections.Sequence[type[Exception]] = (),
        ignored_exceptions: collections.Sequence[type[Exception]] = (),
        timezone: typing.Optional[datetime.timezone] = None,
    ) -> None:
        self._callback = callback

        if not months and not days and not hours and not minutes and not seconds:
            minutes = range(0, 60)

        if weekly:
            days = _to_list(days, 0, 6, "day")

        else:
            days = _to_list(days, 1, 31, "day")

        self._config = _ScheduleConfig(
            days=days,
            hours=_to_list(hours, 0, 23, "hour"),
            is_weekly=weekly,
            minutes=_to_list(minutes, 0, 59, "minute"),
            months=_to_list(months, 1, 12, "month"),
            seconds=_to_list(seconds, 0, 59, "second"),
            timezone=timezone,
        )
        self._fatal_exceptions = tuple(fatal_exceptions)
        self._ignored_exceptions = tuple(ignored_exceptions)
        self._task: typing.Optional[asyncio.Task[None]] = None
        self._tasks: list[asyncio.Task[None]] = []

    @property
    def callback(self) -> _CallbackSigT:
        # <<inherited docstring from IntervalSchedule>>.
        return self._callback

    @property
    def is_alive(self) -> bool:
        # <<inherited docstring from IntervalSchedule>>.
        return False

    if typing.TYPE_CHECKING:
        __call__: _CallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    def copy(self: _TimeSchedule) -> _TimeSchedule:
        # <<inherited docstring from IntervalSchedule>>.
        return copy.copy(self)

    async def _execute(self, client: alluka.Client, /) -> None:
        try:
            await client.call_with_async_di(self._callback)

        except self._fatal_exceptions:
            self.stop()
            raise

        except self._ignored_exceptions:
            pass

    async def _loop(self, client: alluka.Client, /) -> None:
        try:
            while True:
                await asyncio.sleep(time.time() - _Datetime(self._config).next().timestamp())
                self._tasks = [task for task in self._tasks if not task.done()]
                self._tasks.append(asyncio.create_task(self._execute(client)))

        finally:
            self._tasks.clear()

    def load_into_component(self, component: tanjun_abc.Component, /) -> None:
        # <<inherited docstring from tanjun.components.AbstractComponentLoader>>.
        if isinstance(component, _ComponentProto):
            component.add_schedule(self)

    def start(self, client: alluka.Client, /, *, loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if self._task:
            raise RuntimeError("Schedule is already running")

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

    def set_ignored_exceptions(self: _TimeSchedule, *exceptions: type[Exception]) -> _TimeSchedule:
        """Set the exceptions that a schedule will ignore.

        If any of these exceptions are encountered, there will be nothing printed to console.

        Parameters
        ----------
        *exceptions
            Types of the exceptions to ignore.

        Returns
        -------
        Self
            The schedule object to enable chained calls.
        """
        self._ignored_exceptions = exceptions
        return self

    def set_fatal_exceptions(self: _TimeSchedule, *exceptions: type[Exception]) -> _TimeSchedule:
        """Set the exceptions that will stop a schedule.

        If any of these exceptions are encountered, the task will stop.

        Parameters
        ----------
        *exceptions
            Types of the exceptions to stop the task on.

        Returns
        -------
        Self
            The schedule object to enable chianed calls.
        """
        self._fatal_exceptions = exceptions
        return self
