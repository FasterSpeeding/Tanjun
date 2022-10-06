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

__all__: list[str] = ["AbstractSchedule", "IntervalSchedule", "TimeSchedule", "as_interval", "as_time_schedule"]

import abc
import asyncio
import calendar
import copy
import dataclasses
import datetime
import traceback
import typing
from collections import abc as collections

from alluka import abc as alluka

from . import _internal
from . import components

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    from . import abc as tanjun

    _OtherCallbackT = typing.TypeVar("_OtherCallbackT", bound="_CallbackSig")

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

    @abc.abstractmethod
    def copy(self) -> Self:
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
    def force_stop(self) -> None:
        """Stop the schedule while cancelling any active tasks.

        Raises
        ------
        RuntimeError
            If the schedule is not active.
        """

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the schedule after waiting for any existing tasks to finish.

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

    Examples
    --------

    ```py
    @component.with_schedule
    @tanjun.as_interval(datetime.timedelta(minutes=5))  # This will run every 5 minutes
    async def interval(client: alluka.Injected[tanjun.abc.Client]) -> None:
        ...
    ```

    This should be loaded into a component using either
    [Component.with_schedule][tanjun.components.Component.with_schedule] or
    [Component.load_from_scope][tanjun.components.Component.load_from_scope],
    and will be started and stopped with the linked tanjun client.

    Parameters
    ----------
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

    Returns
    -------
    collections.Callable[[_CallbackSigT], tanjun.scheduling.IntervalSchedule[_CallbackSigT]]
        The decorator used to create the schedule.

        This should be decorating an asynchronous function which takes no
        positional arguments, returns [None][] and may use dependency injection.
    """
    return lambda callback: IntervalSchedule(
        callback,
        interval,
        fatal_exceptions=fatal_exceptions,
        ignored_exceptions=ignored_exceptions,
        max_runs=max_runs,
    )


class IntervalSchedule(typing.Generic[_CallbackSigT], components.AbstractComponentLoader, AbstractSchedule):
    """A callback schedule with an interval between calls.

    This should be loaded into a component using either
    [Component.load_from_scope][tanjun.components.Component.load_from_scope],
    [Component.add_schedule][tanjun.components.Component.add_schedule] or
    [Component.with_schedule][tanjun.components.Component.with_schedule], and
    will be started and stopped with the linked tanjun client.
    """

    __slots__ = (
        "_callback",
        "_client",
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
        self._client: typing.Optional[alluka.Client] = None
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

    def copy(self) -> Self:
        # <<inherited docstring from IntervalSchedule>>.
        if self._task:
            raise RuntimeError("Cannot copy an active schedule")

        inst = copy.copy(self)
        inst._tasks = []
        return inst

    def load_into_component(self, component: tanjun.Component, /) -> None:
        # <<inherited docstring from tanjun.components.AbstractComponentLoader>>.
        if isinstance(component, _ComponentProto):
            component.add_schedule(self)

    def set_start_callback(self, callback: _CallbackSig, /) -> Self:
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

    def set_stop_callback(self, callback: _CallbackSig, /) -> Self:
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
            traceback.print_exc()
            await self.stop()

        except self._ignored_exceptions:
            pass

        except Exception:
            traceback.print_exc()

    def _add_task(self, task: asyncio.Task[None], /) -> None:
        if not task.done():
            task.add_done_callback(self._remove_task)
            self._tasks.append(task)

    def _remove_task(self, task: asyncio.Task[None], /) -> None:
        self._tasks.remove(task)

    @_internal.log_task_exc("Interval schedule crashed")
    async def _loop(self, client: alluka.Client, /) -> None:
        event_loop = asyncio.get_running_loop()
        try:
            if self._start_callback:
                try:
                    await client.call_with_async_di(self._start_callback)

                except self._ignored_exceptions:
                    pass

                except Exception:
                    traceback.print_exc()
                    self._task = None
                    return

            while not self._max_runs or self._iteration_count < self._max_runs:
                await asyncio.sleep(self._interval.total_seconds())
                self._iteration_count += 1
                self._add_task(event_loop.create_task(self._execute(client)))

            self._add_task(event_loop.create_task(self.stop()))

        except Exception:
            traceback.print_exc()

    async def _on_stop(self, client: alluka.Client, /) -> None:
        if self._stop_callback:
            try:
                await client.call_with_async_di(self._stop_callback)

            except self._ignored_exceptions:
                pass

            except Exception:
                traceback.print_exc()

    def start(self, client: alluka.Client, /, *, loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if self._task:
            raise RuntimeError("Cannot start an active schedule")

        loop = loop or asyncio.get_running_loop()

        if not loop.is_running():
            raise RuntimeError("Event loop is not running")

        self._client = client
        self._task = loop.create_task(self._loop(client))

    def force_stop(self) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if not self._task:
            raise RuntimeError("Schedule is not running")

        assert self._client
        client = self._client
        self._client = None
        self._task.cancel()
        self._task = None
        for task in self._tasks.copy():
            task.cancel()

        if self._stop_callback:
            self._add_task(asyncio.create_task(self._on_stop(client)))

    async def stop(self) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if not self._task:
            raise RuntimeError("Schedule is not running")

        assert self._client
        client = self._client
        self._client = None
        self._task.cancel()
        self._task = None
        if not self._tasks:
            await self._on_stop(client)
            return

        current_task = asyncio.current_task()
        tasks = [task for task in self._tasks if task is not current_task]
        try:
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()

            raise

        await self._on_stop(client)

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

    def set_ignored_exceptions(self, *exceptions: type[Exception]) -> Self:
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

    def set_fatal_exceptions(self, *exceptions: type[Exception]) -> Self:
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


def _get_next(target_values: collections.Sequence[int], current_value: int) -> typing.Optional[int]:
    for value in target_values:
        if value > current_value:
            return value

    return None


def _to_sequence(
    values: typing.Union[int, collections.Sequence[int], None], min_: int, max_: int, name: str
) -> typing.Optional[collections.Sequence[int]]:
    if values is None:
        return None

    if isinstance(values, int):
        if values >= max_ or values < min_:
            raise ValueError(f"{name} value must be (inclusively) between {min_} and {max_ - 1}, not {values}")

        return [values]

    if isinstance(values, float):
        raise ValueError(f"{name} value must be an integer, not a float")

    if isinstance(values, range):
        if values.step < 0:
            # Ranges with a positive step will already be sorted so these can be left as-is.
            values = sorted(values)

    elif len(values) == 0:  # Empty sequences should be treated as None.
        # an explicit len check is used here to ensure this case is only ever applied to a sequence.
        return None

    else:
        values = sorted(values)
        if any(isinstance(value, float) for value in values):
            raise ValueError(f"Cannot pass floats for {name}")

    first_entry = values[0]
    last_entry = values[-1]
    if last_entry >= max_ or first_entry < min_:
        raise ValueError(
            f"{name} must be (inclusively) between {min_} and {max_ - 1}, not {first_entry} and {last_entry}"
        )

    return values


@dataclasses.dataclass
class _TimeScheduleConfig:
    __slots__ = ("current_date", "days", "hours", "is_weekly", "minutes", "months", "seconds", "timezone")
    current_date: datetime.datetime
    days: typing.Optional[collections.Sequence[int]]
    hours: collections.Sequence[int]
    is_weekly: bool
    minutes: collections.Sequence[int]
    months: collections.Sequence[int]
    seconds: collections.Sequence[int]
    timezone: typing.Optional[datetime.timezone]


class _Datetime:
    """Class used to calculate the next datetime in a time schedule."""

    __slots__ = ("_config", "_date")

    def __init__(self, config: _TimeScheduleConfig, date: datetime.datetime) -> None:
        """Initialise the class.

        Parameters
        ----------
        config
            The configuration to use.
        """
        self._config = config
        # A half-second offset is used to lower the chances of this triggering early/late.
        #
        # Since datetime.replace and timedelta maths is used to calculate the time,
        # this microsecond offset will persist to the calculated datetime.
        self._date = date.replace(microsecond=500000)

    def next(self) -> datetime.datetime:
        """Get the next datetime which matches the schedule.

        If the current time matches the schedule, this will be skipped.

        Returns
        -------
        datetime.datetime
            The next datetime which matches the schedule.
        """
        if self._date.month not in self._config.months:
            self._next_month()
            return self._date

        if self._config.days:
            day = self._date.isoweekday() if self._config.is_weekly else self._date.day
            if day not in self._config.days:
                self._next_day()
                return self._date

        if self._date.hour not in self._config.hours:
            self._next_hour()
            return self._date

        if self._date.minute not in self._config.minutes:
            self._next_minute()
            return self._date

        self._next_second()
        return self._date

    def _next_month(self) -> Self:
        """Bump this to the next valid month.

        The current month will also be considered.
        """
        if self._date.month in self._config.months:
            return self._next_day()

        month = _get_next(self._config.months, self._date.month)

        if month is None:  # Indicates we've passed the last matching month in this year.
            # So now we jump to the next year.
            self._date = self._date.replace(year=self._date.year + 1, month=1, day=1, hour=0, minute=0, second=0)
            # Then re-calculate.
            return self._next_month()

        self._date = self._date.replace(month=month, day=1, hour=0, minute=0, second=0)
        return self._next_day()

    def _next_day(self) -> Self:
        """Bump this to the next valid day.

        The current day will also be considered.
        """
        if not self._config.days:
            return self._next_hour()

        if not self._config.is_weekly:
            if self._date.day in self._config.days:
                return self._next_hour()

            day = _get_next(self._config.days, self._date.day)
            if day is None:  # Indicates we've passed the last matching day in this week.
                # This implicitly handles flowing to the next year.
                days_to_jump = (calendar.monthrange(self._date.year, self._date.month)[1] - self._date.day) + 1
                self._date = (self._date + datetime.timedelta(days=days_to_jump)).replace(
                    day=1, hour=0, minute=0, second=0
                )
                return self._next_month()

            self._date = self._date.replace(day=day)
            return self._next_hour()

        day = self._date.isoweekday()
        if day in self._config.days:
            return self._next_hour()

        day = _get_next(self._config.days, day)
        current = self._date.year, self._date.month
        if day is None:  # Indicates we've passed the last matching day in this week.
            self._date = (self._date + datetime.timedelta((8 - self._date.isoweekday()))).replace(
                hour=0, minute=0, second=0
            )

            if (self._date.year, self._date.month) != current:
                # Re-calculate if necessary to ensure that this month matches
                # if this jump crossed to a new month or year.
                return self._next_month()

            # Calculate the next matching day in this week.
            return self._next_day()

        self._date = (self._date + datetime.timedelta(days=day - self._date.isoweekday())).replace(
            hour=0, minute=0, second=0
        )
        if (self._date.year, self._date.month) != current:
            # Re-calculate if necessary to ensure that this month matches if
            # this jump crossed to a new month or year.
            return self._next_month()

        return self._next_hour()

    def _next_hour(self) -> Self:
        """Bump this to the next valid hour.

        The current hour will also be considered.
        """
        if self._date.hour in self._config.hours:
            return self._next_minute()

        hour = _get_next(self._config.hours, self._date.hour)

        if hour is None:  # Indicates we've passed the last matching hour in this day.
            # So we need to jump to the next day (while handling flowing to the next month/year).
            self._date = (self._date + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0)
            # Then re-calculate.
            return self._next_month()

        self._date = self._date.replace(hour=hour, minute=0, second=0)
        return self._next_minute()

    def _next_minute(self) -> Self:
        """Bump this to the next valid minute.

        The current minute will also be considered.
        """
        if self._date.minute in self._config.minutes:
            return self._next_second()

        minute = _get_next(self._config.minutes, self._date.minute)

        if minute is None:  # Indicates we've passed the last matching minute in this hour.
            # So we jump to the next hour (while handling flowing to the next day/month/year).
            self._date = (self._date + datetime.timedelta(hours=1)).replace(minute=0, second=0)
            # and then re-calculate.
            return self._next_month()

        self._date = self._date.replace(minute=minute, second=0)
        return self._next_second()

    def _next_second(self) -> Self:
        """Bump this to the next valid second.

        The current second will also be considered.
        """
        if self._date.second in self._config.seconds and self._date != self._config.current_date:
            self._config.current_date = self._date
            return self

        second = _get_next(self._config.seconds, self._date.second)

        if second is None:  # Indicates we've passed the last matching second in this minute.
            # So we jump to the next minute (while handling flowing to the next hour/day/month/year).
            self._date = self._date + datetime.timedelta(seconds=60 - self._date.second)
            # and then re-calculate.
            return self._next_month()

        self._date = self._date.replace(second=second)
        if self._config.current_date == self._date:
            # There's some timing edge-cases where this might trigger before the
            # target time and to avoid that leading to duped-calls we check after calculating.
            return self._next_second()

        self._config.current_date = self._date
        return self


def as_time_schedule(
    *,
    months: typing.Union[int, collections.Sequence[int]] = (),
    weekly: bool = False,
    days: typing.Union[int, collections.Sequence[int]] = (),
    hours: typing.Union[int, collections.Sequence[int]] = (),
    minutes: typing.Union[int, collections.Sequence[int]] = (),
    seconds: typing.Union[int, collections.Sequence[int]] = 0,
    fatal_exceptions: collections.Sequence[type[Exception]] = (),
    ignored_exceptions: collections.Sequence[type[Exception]] = (),
    timezone: typing.Optional[datetime.timezone] = None,
) -> collections.Callable[[_CallbackSigT], TimeSchedule[_CallbackSigT]]:
    """Create a time schedule through a decorator call.

    Examples
    --------

    ```py
    @component.with_schedule

    @tanjun.as_time_schedule(  # This will run every week day at 8:00 and 16:00 UTC.
        minutes=0, hours=[8, 16], days=range(0, 5), weekly=True, timezone=datetime.timezone.utc
    )
    async def interval(client: alluka.Injected[tanjun.abc.Client]) -> None:
        ...
    ```

    This should be loaded into a component using either
    [Component.with_schedule][tanjun.components.Component.with_schedule] or
    [Component.load_from_scope][tanjun.components.Component.load_from_scope],
    and will be started and stopped with the linked tanjun client.

    Parameters
    ----------
    months
        Either one or multiple months the schedule should run on.

        If this is not specified or an empty sequence then the schedule
        will run on all months.
    weekly
        Whether the schedule should run on a weekly basis.
    days
        Either one or multiple days the schedule should run on.

        When `weekly` is [True][], `days` will refer to the days of the week
        (`range(7)`).

        Otherwise this will refer to the days of the month (`range(32)`).
        For months where less than 31 days exist, numbers which are too large
        will be ignored.

        If this is not specified or an empty sequence, then the schedule
        will on all days.
    hours
        Either one or multiple hours the schedule should run on.

        If this is not specified or an empty sequence then the schedule
        will run on all hours.
    minutes
        Either one or multiple minutes the schedule should run on.

        If this is not specified or an empty sequence then the schedule
        will run on all minutes.
    seconds
        Either one or multiple seconds the schedule should run on.

        Defaults to the start of the minute if not specified or an empty
        sequence.
    fatal_exceptions
        A sequence of exceptions that will cause the schedule to stop if raised
        by the callback, start callback or stop callback.
    ignored_exceptions
        A sequence of exceptions that should be ignored if raised by the
        callback, start callback or stop callback.
    timezone
        The timezone to use for the schedule.

        If this is not specified then the system's local timezone will be used.

    Returns
    -------
    collections.Callable[[_CallbackSigT], tanjun.scheduling.TimeSchedule[_CallbackSigT]]
        The decorator used to create the schedule.

        This should be decorating an asynchronous function which takes no
        positional arguments, returns [None][] and may use dependency injection.

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:

        * If months has any values outside the range of `range(1, 13)`.
        * If days has any values outside the range of `range(1, 32)` when
            `weekly` is [False][] or outside the range of `range(1, 7)` when
            `weekly` is [True][].
        * If hours has any values outside the range of `range(0, 24)`.
        * If minutes has any values outside the range of `range(0, 60)`.
        * If seconds has any values outside the range of `range(0, 60)`.
    """
    return lambda callback: TimeSchedule(
        callback,
        months=months,
        weekly=weekly,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        fatal_exceptions=fatal_exceptions,
        ignored_exceptions=ignored_exceptions,
        timezone=timezone,
    )


class TimeSchedule(typing.Generic[_CallbackSigT], components.AbstractComponentLoader, AbstractSchedule):
    """A schedule that runs at specific times.

    This should be loaded into a component using either
    [Component.load_from_scope][tanjun.components.Component.load_from_scope],
    [Component.add_schedule][tanjun.components.Component.add_schedule] or
    [Component.with_schedule][tanjun.components.Component.with_schedule] and
    will be started and stopped with the linked tanjun client.
    """

    __slots__ = ("_callback", "_config", "_fatal_exceptions", "_ignored_exceptions", "_task", "_tasks")

    def __init__(
        self,
        callback: _CallbackSigT,
        /,
        *,
        months: typing.Union[int, collections.Sequence[int]] = (),
        weekly: bool = False,
        days: typing.Union[int, collections.Sequence[int]] = (),
        hours: typing.Union[int, collections.Sequence[int]] = (),
        minutes: typing.Union[int, collections.Sequence[int]] = (),
        seconds: typing.Union[int, collections.Sequence[int]] = 0,
        fatal_exceptions: collections.Sequence[type[Exception]] = (),
        ignored_exceptions: collections.Sequence[type[Exception]] = (),
        timezone: typing.Optional[datetime.timezone] = None,
    ) -> None:
        """Initialise the time schedule.

        Parameters
        ----------
        callback : collections.abc.Callable[...,  collections.abc.Coroutine[Any, Any, None]]
            The callback for the schedule.

            This should be an asynchronous function which takes no positional
            arguments, returns [None][] and may use dependency injection.
        months
            Either one or multiple months the schedule shouldrun on.

            If this is not specified or an empty sequence then the schedule
            will run on all months.
        weekly
            Whether the schedule should run on a weekly basis.
        days
            Either one or multiple days the schedule should run on.

            When `weekly` is [True][], `days` will refer to the days of the week
            (`range(7)`).

            Otherwise this will refer to the days of the month (`range(32)`).
            For months where less than 31 days exist, numbers which are too large
            will be ignored.

            If this is not specified or an empty sequence, then the schedule
            will on all days.
        hours
            Either one or multiple hours the schedule should run on.

            If this is not specified or an empty sequence then the schedule
            will run on all hours.
        minutes
            Either one or multiple minutes the schedule should run on.

            If this is not specified or an empty sequence then the schedule
            will run on all minutes.
        seconds
            Either one or multiple seconds the schedule should run on.

            Defaults to the start of the minute if not specified or an empty
            sequence.
        fatal_exceptions
            A sequence of exceptions that will cause the schedule to stop if raised
            by the callback, start callback or stop callback.
        ignored_exceptions
            A sequence of exceptions that should be ignored if raised by the
            callback, start callback or stop callback.
        timezone
            The timezone to use for the schedule.

            If this is not specified then the system's local timezone will be used.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If months has any values outside the range of `range(1, 13)`.
            * If days has any values outside the range of `range(1, 32)` when
              `weekly` is [False][] or outside the range of `range(1, 8)` when
              `weekly` is [True][].
            * If hours has any values outside the range of `range(0, 24)`.
            * If minutes has any values outside the range of `range(0, 60)`.
            * If seconds has any values outside the range of `range(0, 60)`.
        """
        self._callback = callback

        if weekly:
            actual_days = _to_sequence(days, 1, 9, "days")

        else:
            actual_days = _to_sequence(days, 1, 32, "days")

        self._config = _TimeScheduleConfig(
            current_date=datetime.datetime.min.replace(tzinfo=timezone),
            days=actual_days,
            hours=_to_sequence(hours, 0, 24, "hours") or range(24),
            is_weekly=weekly,
            minutes=_to_sequence(minutes, 0, 60, "minutes") or range(60),
            months=_to_sequence(months, 1, 13, "months") or range(1, 13),
            seconds=_to_sequence(seconds, 0, 60, "seconds") or [0],
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
        return self._task is not None

    if typing.TYPE_CHECKING:
        __call__: _CallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    def copy(self) -> Self:
        # <<inherited docstring from IntervalSchedule>>.
        if self._task:
            raise RuntimeError("Cannot copy an active schedule")

        inst = copy.copy(self)
        self._config = copy.copy(self._config)
        self._config.current_date = datetime.datetime.min.replace(tzinfo=self._config.timezone)
        inst._tasks = []
        return inst

    async def _execute(self, client: alluka.Client, /) -> None:
        try:
            await client.call_with_async_di(self._callback)

        except self._fatal_exceptions:
            traceback.print_exc()
            await self.stop()

        except self._ignored_exceptions:
            pass

        except Exception:
            traceback.print_exc()

    def _add_task(self, task: asyncio.Task[None], /) -> None:
        if not task.done():
            task.add_done_callback(self._remove_task)
            self._tasks.append(task)

    def _remove_task(self, task: asyncio.Task[None], /) -> None:
        self._tasks.remove(task)

    @_internal.log_task_exc("Time schedule crashed")
    async def _loop(self, client: alluka.Client, /) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                current_date = datetime.datetime.now(tz=self._config.timezone)
                next_date = _Datetime(self._config, current_date).next()
                result = next_date - current_date
                await asyncio.sleep(result.total_seconds())
                self._add_task(loop.create_task(self._execute(client)))

        finally:
            self._task = None

    def load_into_component(self, component: tanjun.Component, /) -> None:
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

    def force_stop(self) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if not self._task:
            raise RuntimeError("Schedule is not running")

        self._task.cancel()
        self._task = None
        for task in self._tasks.copy():
            task.cancel()

    async def stop(self) -> None:
        # <<inherited docstring from IntervalSchedule>>.
        if not self._task:
            raise RuntimeError("Schedule is not running")

        self._task.cancel()
        self._task = None
        if not self._tasks:
            return

        current_task = asyncio.current_task()
        tasks = [task for task in self._tasks if task is not current_task]
        try:
            await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()

            raise

    def set_ignored_exceptions(self, *exceptions: type[Exception]) -> Self:
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

    def set_fatal_exceptions(self, *exceptions: type[Exception]) -> Self:
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
