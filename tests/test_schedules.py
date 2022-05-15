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

# pyright: reportPrivateUsage=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

import asyncio
import datetime
import functools
import itertools
import time
import traceback
import types
import typing
from collections import abc as collections
from unittest import mock

import alluka
import freezegun
import pytest

import tanjun

_CallbackSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, typing.Any]]
_CallbackSigT = typing.TypeVar("_CallbackSigT", bound=_CallbackSig)
_T = typing.TypeVar("_T")
_TIMEOUT: typing.Final[float] = 10.0


def _chain(data: collections.Iterable[collections.Iterable[_T]]) -> list[_T]:
    return list(itertools.chain.from_iterable(data))


def _print_tb(callback: _CallbackSigT, /) -> _CallbackSigT:
    @functools.wraps(callback)
    async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        try:
            return await callback(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise

    return typing.cast(_CallbackSigT, wrapper)


class _ManualClock:
    def __init__(
        self,
        freeze_time: "freezegun.api.FrozenDateTimeFactory",
        tick_fors: list[datetime.timedelta],
        *,
        interval_ratio: int = 10,
        post_sleep_count: int = 5,
        tick_sleep_count: int = 1,
    ) -> None:
        self._freeze_time = freeze_time
        self._index = -1
        self._interval_ratio = interval_ratio
        self._is_ticking = False
        self._keep_ticking = False
        self._post_sleep_count = post_sleep_count
        self._tasks: list[asyncio.Task[None]] = []
        self._tick_fors = tick_fors
        self._tick_sleep_count = tick_sleep_count

    async def _next_tick(self) -> None:
        index = self._index + 1
        if len(self._tick_fors) == index:
            tick_for = self._tick_fors[-1]
        else:
            tick_for = self._tick_fors[index]
            self._index += 1

        interval = tick_for / self._interval_ratio
        while tick_for > datetime.timedelta():
            for _ in range(self._tick_sleep_count):
                # This lets the event loop run for a bit between ticks.
                await asyncio.sleep(0)

            if tick_for - interval >= datetime.timedelta():
                self._freeze_time.tick(interval)
            else:
                self._freeze_time.tick(tick_for)

            tick_for -= interval

        for _ in range(self._post_sleep_count):
            # This lets the event loop run for a bit between ticks.
            await asyncio.sleep(0)

        if self._keep_ticking:
            self._keep_ticking = False
            return await self._next_tick()

        self._is_ticking = False

    def spawn_ticker(self) -> "_ManualClock":
        if self._is_ticking and self._keep_ticking:
            raise RuntimeError("Already ticking")

        if self._is_ticking:
            self._keep_ticking = True
            return self

        self._is_ticking = True
        self._tasks.append(asyncio.get_running_loop().create_task(_print_tb(self._next_tick)()))
        return self

    def stop_ticker(self) -> None:
        self._tasks[-1].cancel()


def test_as_interval():
    mock_callback = mock.Mock()

    result = tanjun.as_interval(123, fatal_exceptions=[KeyError], ignored_exceptions=[TabError], max_runs=55)(
        mock_callback
    )

    assert result.interval == datetime.timedelta(minutes=2, seconds=3)
    assert result._fatal_exceptions == (KeyError,)
    assert result._ignored_exceptions == (TabError,)
    assert result._max_runs == 55
    assert isinstance(result, tanjun.schedules.IntervalSchedule)


class TestIntervalSchedule:
    def test_callback_property(self):
        mock_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock_callback, 123)

        assert interval.callback is mock_callback

    def test_is_alive(self):
        assert tanjun.schedules.IntervalSchedule(mock.Mock(), 34123).is_alive is False

    def test_is_alive_when_is_alive(self):
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock.Mock()

        assert interval.is_alive is True

    @pytest.mark.parametrize(
        "interval", [datetime.timedelta(days=7, hours=13, minutes=8, seconds=54), 652134, 652134.0]
    )
    def test_interval_property(self, interval: typing.Union[int, float, datetime.timedelta]):
        interval_ = tanjun.schedules.IntervalSchedule(mock.Mock(), interval)

        assert interval_.interval == datetime.timedelta(days=7, hours=13, minutes=8, seconds=54)

    def test_iteration_count_property(self):
        assert tanjun.schedules.IntervalSchedule(mock.Mock(), 123).iteration_count == 0

    @pytest.mark.asyncio()
    async def test_call_dunder_method(self):
        mock_callback = mock.AsyncMock()
        interval = tanjun.schedules.IntervalSchedule(typing.cast("tanjun.schedules._CallbackSig", mock_callback), 123)

        await interval(123, 543, sex="OK", boo="31123")

        mock_callback.assert_awaited_once_with(123, 543, sex="OK", boo="31123")

    def test_copy(self):
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._tasks.append(mock.Mock())

        result = interval.copy()

        assert result.callback is interval.callback
        assert result.interval is interval.interval
        assert result.iteration_count is interval.iteration_count
        assert result._tasks == []
        assert result._tasks is not interval._tasks
        assert result is not interval

    def test_copy_when_schedule_is_active(self):
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock.Mock()

        with pytest.raises(RuntimeError, match="Cannot copy an active schedule"):
            interval.copy()

    def test_load_into_component(self):
        mock_component = mock.Mock(tanjun.Component)
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        interval.load_into_component(mock_component)

        mock_component.add_schedule.assert_called_once_with(interval)

    def test_load_into_component_when_no_add_schedule_method(self):
        mock_component = mock.Mock(object)
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        interval.load_into_component(mock_component)

    def test_set_start_callback(self):
        mock_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        result = interval.set_start_callback(mock_callback)

        assert result is interval
        assert interval._start_callback
        assert interval._start_callback is mock_callback

    def test_set_stop_callback(self):
        mock_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        result = interval.set_stop_callback(mock_callback)

        assert result is interval
        assert interval._stop_callback
        assert interval._stop_callback is mock_callback

    @pytest.mark.asyncio()
    async def test__execute(self):
        mock_client = mock.AsyncMock()
        mock_callback = mock.Mock()
        stop = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"stop": stop}),
        )(mock_callback, 123)

        await interval._execute(mock_client)

        mock_client.call_with_async_di.assert_awaited_once_with(mock_callback)
        stop.assert_not_called()

    @pytest.mark.asyncio()
    async def test__execute_when_fatal_exception(self):
        mock_callback = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_client.call_with_async_di.side_effect = KeyError("hihihiih")
        stop = mock.AsyncMock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"stop": stop}),
        )(mock_callback, 123, fatal_exceptions=[LookupError], ignored_exceptions=[Exception])

        await interval._execute(mock_client)

        mock_client.call_with_async_di.assert_awaited_once_with(mock_callback)
        stop.assert_awaited_once_with()
        assert interval._tasks == []

    @pytest.mark.asyncio()
    async def test__execute_when_ignored_exception(self):
        mock_callback = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_client.call_with_async_di.side_effect = IndexError("hihihiih")
        stop = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"stop": stop}),
        )(mock_callback, 123, fatal_exceptions=[KeyError], ignored_exceptions=[LookupError])

        await interval._execute(mock_client)

        mock_client.call_with_async_di.assert_awaited_once_with(mock_callback)
        stop.assert_not_called()

    @pytest.mark.asyncio()
    async def test__execute_when_exception(self):
        mock_callback = mock.Mock()
        mock_client = mock.AsyncMock()
        error = ValueError("hihihiih")
        mock_client.call_with_async_di.side_effect = error
        stop = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"stop": stop}),
        )(mock_callback, 123, fatal_exceptions=[KeyError], ignored_exceptions=[TypeError])

        await interval._execute(mock_client)

        mock_client.call_with_async_di.assert_awaited_once_with(mock_callback)
        stop.assert_not_called()

    @pytest.mark.timeout(_TIMEOUT)
    @pytest.mark.asyncio()
    async def test__loop(self):
        mock_client = alluka.Client()
        call_times: list[int] = []

        @_print_tb
        async def callback():
            call_times.append(time.time_ns())
            clock.spawn_ticker()

        interval = tanjun.schedules.IntervalSchedule(callback, 5, ignored_exceptions=[LookupError])

        with freezegun.freeze_time(datetime.datetime(2012, 1, 14, 12)) as frozen_time:
            interval.start(mock_client)
            # Note: these have to be at least a microsecond after the target time as
            # the unix event loop won't return the sleep until the target time has passed,
            # not just been reached.
            clock = _ManualClock(frozen_time, [datetime.timedelta(seconds=5, milliseconds=100)]).spawn_ticker()
            await asyncio.sleep(30)
            await interval.stop()
            clock.stop_ticker()

        assert interval._task is None
        assert call_times == [
            1326542405000000000,
            1326542410000000000,
            1326542415000000000,
            1326542420000000000,
            1326542425000000000,
        ]
        assert interval.iteration_count == 5

    @pytest.mark.timeout(_TIMEOUT)
    @pytest.mark.asyncio()
    async def test__loop_when_max_runs(self):
        mock_client = alluka.Client()
        call_times: list[int] = []
        close_event = asyncio.Event()
        close_time: typing.Optional[int] = None

        @_print_tb
        async def callback():
            call_times.append(time.time_ns())
            clock.spawn_ticker()

        @_print_tb
        async def on_stop():
            nonlocal close_time
            close_time = time.time_ns()
            close_event.set()

        interval = tanjun.schedules.IntervalSchedule(
            callback, 3, ignored_exceptions=[LookupError], max_runs=3
        ).set_stop_callback(on_stop)

        with freezegun.freeze_time(datetime.datetime(2012, 4, 11, 12)) as frozen_time:
            interval.start(mock_client)
            # Note: these have to be at least a microsecond after the target time as
            # the unix event loop won't return the sleep until the target time has passed,
            # not just been reached.
            clock = _ManualClock(frozen_time, [datetime.timedelta(seconds=3, milliseconds=300)]).spawn_ticker()
            await close_event.wait()
            assert close_time == 1334145609000000000

        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0)

        assert interval._task is None
        assert interval._tasks == []
        assert call_times == [1334145603000000000, 1334145606000000000, 1334145609000000000]
        assert interval.iteration_count == 3

    @pytest.mark.timeout(_TIMEOUT)
    @pytest.mark.asyncio()
    async def test__loop_when_start_and_stop_callbacks_set(self):
        mock_client = alluka.Client()
        call_times: list[int] = []
        start_time = None
        stop_time = None

        @_print_tb
        async def callback() -> None:
            call_times.append(time.time_ns())
            clock.spawn_ticker()

        @_print_tb
        async def on_start() -> None:
            nonlocal start_time
            start_time = time.time_ns()

        @_print_tb
        async def on_stop() -> None:
            nonlocal stop_time
            stop_time = time.time_ns()
            clock.stop_ticker()

        interval = (
            tanjun.schedules.IntervalSchedule(callback, 7, ignored_exceptions=[LookupError])
            .set_start_callback(on_start)
            .set_stop_callback(on_stop)
        )

        with freezegun.freeze_time(datetime.datetime(2011, 4, 5, 4)) as frozen_time:
            interval.start(mock_client)
            # Note: these have to be at least a microsecond after the target time as
            # the unix event loop won't return the sleep until the target time has passed,
            # not just been reached.
            clock = _ManualClock(frozen_time, [datetime.timedelta(seconds=7, milliseconds=200)]).spawn_ticker()
            await asyncio.sleep(28)
            await interval.stop()
            await asyncio.sleep(0)

        assert interval._task is None
        assert call_times == [1301976007000000000, 1301976014000000000, 1301976021000000000]
        assert start_time == 1301976000000000000
        assert stop_time == 1301976028000000000
        assert interval.iteration_count == 3

    @pytest.mark.parametrize("fatal_exceptions", [[LookupError], []])
    @pytest.mark.asyncio()
    async def test__loop_and_start_raises(self, fatal_exceptions: list[type[Exception]]):
        error = KeyError()
        mock_client = mock.Mock()
        mock_client.call_with_async_di = mock.AsyncMock(side_effect=error)
        mock_client.get_callback_override.return_value = None
        mock_start = mock.Mock()
        mock_execute = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_execute": mock_execute}),
        )(mock.Mock(), 123, ignored_exceptions=[RuntimeError], fatal_exceptions=fatal_exceptions).set_start_callback(
            mock_start
        )
        interval._task = mock.Mock()

        with mock.patch.object(asyncio, "sleep") as sleep:
            await interval._loop(mock_client)

        mock_client.call_with_async_di.assert_awaited_once_with(mock_start)
        mock_execute.assert_not_called()
        sleep.assert_not_called()
        assert interval._task is None

    @pytest.mark.asyncio()
    async def test__loop_and_start_raises_ignored(self):
        mock_client = mock.Mock()
        mock_client.call_with_async_di = mock.AsyncMock(side_effect=KeyError())
        mock_client.get_callback_override.return_value = None
        mock_start = mock.Mock()
        mock_execute = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_execute": mock_execute}),
        )(mock.Mock(), 123, ignored_exceptions=[LookupError]).set_start_callback(mock_start)
        interval._task = mock.Mock()

        with (
            mock.patch.object(asyncio, "sleep", side_effect=asyncio.CancelledError) as sleep,
            pytest.raises(asyncio.CancelledError),
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        mock_client.call_with_async_di.assert_awaited_once_with(mock_start)
        mock_execute.assert_not_called()
        get_running_loop.return_value.create_task.assert_not_called()
        sleep.assert_called_once_with(123.0)

    def test_start(self):
        mock_client = mock.Mock()
        loop_method = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_loop": loop_method}),
        )(mock.Mock(), 123)

        with mock.patch.object(asyncio, "get_running_loop") as get_running_loop:
            interval.start(mock_client)

        assert interval._task is get_running_loop.return_value.create_task.return_value
        assert interval._client is mock_client
        assert interval.is_alive is True
        get_running_loop.return_value.create_task.assert_called_once_with(loop_method.return_value)
        get_running_loop.assert_called_once_with()

    def test_start_when_passed_event_loop(self):
        mock_client = mock.Mock()
        mock_loop = mock.Mock()
        loop_method = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_loop": loop_method}),
        )(mock.Mock(), 123)

        interval.start(mock_client, loop=mock_loop)

        assert interval._task is mock_loop.create_task.return_value
        assert interval._client is mock_client
        assert interval.is_alive is True
        mock_loop.create_task.assert_called_once_with(loop_method.return_value)

    def test_start_when_passed_event_loop_isnt_active(self):
        mock_loop = mock.Mock()
        mock_loop.is_running.return_value = False
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        with pytest.raises(RuntimeError, match="Event loop is not running"):
            interval.start(mock.Mock(), loop=mock_loop)

        assert interval._task is None

    def test_start_when_already_active(self):
        mock_task = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock_task

        with pytest.raises(RuntimeError, match="Cannot start an active schedule"):
            interval.start(mock.Mock())

        assert interval._task is mock_task

    @pytest.mark.asyncio()
    async def test_force_stop(self):
        mock_task = mock.Mock()
        mock_task_1 = asyncio.create_task(asyncio.sleep(2, result=None))
        mock_task_2 = asyncio.create_task(asyncio.sleep(2, result=None))
        mock_task_3 = asyncio.create_task(asyncio.sleep(2, result=None))
        mock_client = mock.AsyncMock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._client = mock_client
        interval._task = mock_task
        interval._add_task(mock_task_1)
        interval._add_task(mock_task_2)
        interval._add_task(mock_task_3)

        interval.force_stop()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0.1)

        mock_task.cancel.assert_called_once_with()
        assert interval.is_alive is False
        assert interval._task is None
        assert interval._tasks == []
        assert mock_task_1.cancelled() is True
        assert mock_task_2.cancelled() is True
        assert mock_task_3.cancelled() is True
        mock_client.call_with_async_di.assert_not_called()

    @pytest.mark.asyncio()
    async def test_force_stop_when_stop_callback_set(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_stop_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123).set_stop_callback(mock_stop_callback)
        interval._client = mock_client
        interval._task = mock_task
        interval._tasks = []

        interval.force_stop()
        # Await the stop callback task.
        await interval._tasks[-1]

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_awaited_once_with(mock_stop_callback)

    @pytest.mark.asyncio()
    async def test_force_stop_when_stop_callback_stop_raises(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_client.call_with_async_di.side_effect = KeyError
        mock_stop_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123).set_stop_callback(mock_stop_callback)
        interval._client = mock_client
        interval._task = mock_task
        interval._add_task(asyncio.create_task(asyncio.sleep(50, result=None)))

        interval.force_stop()
        # Await the stop callback task.
        await interval._tasks[-1]

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_awaited_once_with(mock_stop_callback)

    @pytest.mark.asyncio()
    async def test_force_stop_when_stop_callback_raises_ignored(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_client.call_with_async_di.side_effect = ValueError
        mock_stop_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(
            mock.Mock(), 123, ignored_exceptions=(ValueError,)
        ).set_stop_callback(mock_stop_callback)
        interval._client = mock_client
        interval._task = mock_task
        interval._tasks = []

        interval.force_stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert len(interval._tasks) == 1
        await interval._tasks[0]
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_awaited_once_with(mock_stop_callback)

    @pytest.mark.asyncio()
    async def test_force_stop_when_no_tasks(self):
        mock_task = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._client = mock.AsyncMock()
        interval._task = mock_task
        interval._tasks = []

        interval.force_stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []

    def test_force_stop_when_not_active(self):
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        with pytest.raises(RuntimeError, match="Schedule is not running"):
            interval.force_stop()

    @pytest.mark.asyncio()
    async def test_stop(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_task_1 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        mock_task_2 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        mock_task_3 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._client = mock_client
        interval._task = mock_task
        interval._add_task(mock_task_1)
        interval._add_task(mock_task_2)
        interval._add_task(mock_task_3)

        await interval.stop()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0)

        mock_task.cancel.assert_called_once_with()
        assert interval.is_alive is False
        assert interval._task is None
        assert interval._tasks == []
        assert mock_task_1.result() is None
        assert mock_task_2.result() is None
        assert mock_task_3.result() is None
        mock_client.call_with_async_di.assert_not_called()

    @pytest.mark.asyncio()
    async def test_stop_when_no_tasks(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._client = mock_client
        interval._task = mock_task
        interval._tasks = []

        await interval.stop()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0)

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_not_called()

    @pytest.mark.asyncio()
    async def test_stop_when_some_tasks_time_out(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_task_1 = asyncio.create_task(asyncio.sleep(0.1, result=None))
        mock_task_2 = asyncio.create_task(asyncio.sleep(0.7, result=None))
        mock_task_3 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        mock_task_4 = asyncio.create_task(asyncio.sleep(0.8, result=None))
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._client = mock_client
        interval._task = mock_task
        interval._add_task(mock_task_1)
        interval._add_task(mock_task_2)
        interval._add_task(mock_task_3)
        interval._add_task(mock_task_4)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(interval.stop(), 0.3)

        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0)

        mock_task.cancel.assert_called_once_with()
        assert interval.is_alive is False
        assert interval._task is None
        assert interval._tasks == []
        assert mock_task_1.result() is None
        assert mock_task_2.cancelled() is True
        assert mock_task_3.result() is None
        assert mock_task_4.cancelled() is True
        mock_client.call_with_async_di.assert_not_called()

    @pytest.mark.asyncio()
    async def test_stop_when_stop_callback_stop_set(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_stop_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123).set_stop_callback(mock_stop_callback)
        interval._client = mock_client
        interval._task = mock_task
        interval._tasks = []

        await interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_awaited_once_with(mock_stop_callback)

    @pytest.mark.asyncio()
    async def test_stop_when_stop_callback_stop_raises(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_client.call_with_async_di.side_effect = TypeError
        mock_stop_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123).set_stop_callback(mock_stop_callback)
        interval._client = mock_client
        interval._task = mock_task
        interval._add_task(asyncio.create_task(asyncio.sleep(0.1, result=None)))

        await interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_awaited_once_with(mock_stop_callback)

    @pytest.mark.asyncio()
    async def test_stop_when_stop_callback_raises_ignored(self):
        mock_task = mock.Mock()
        mock_client = mock.AsyncMock()
        mock_client.call_with_async_di.side_effect = RuntimeError
        mock_stop_callback = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(
            mock.Mock(), 123, ignored_exceptions=(RuntimeError,)
        ).set_stop_callback(mock_stop_callback)
        interval._client = mock_client
        interval._task = mock_task
        interval._tasks = []

        await interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None
        assert interval._tasks == []
        mock_client.call_with_async_di.assert_awaited_once_with(mock_stop_callback)

    @pytest.mark.asyncio()
    async def test_stop_when_not_active(self):
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        with pytest.raises(RuntimeError, match="Schedule is not running"):
            await interval.stop()

    def test_with_start_callback(self):
        set_start_callback = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"set_start_callback": set_start_callback}),
        )(mock.Mock(), 123)
        mock_callback = mock.Mock()

        result = interval.with_start_callback(mock_callback)

        assert result is mock_callback
        set_start_callback.assert_called_once_with(mock_callback)

    def test_with_stop_callback(self):
        set_stop_callback = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"set_stop_callback": set_stop_callback}),
        )(mock.Mock(), 123)
        mock_callback = mock.Mock()

        result = interval.with_stop_callback(mock_callback)

        assert result is mock_callback
        set_stop_callback.assert_called_once_with(mock_callback)

    def test_set_ignored_exceptions(self):
        mock_exception: typing.Any = mock.Mock()
        mock_other_exception: typing.Any = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        interval.set_ignored_exceptions(mock_exception, mock_other_exception)

        assert interval._ignored_exceptions == (mock_exception, mock_other_exception)

    def test_set_fatal_exceptions(self):
        mock_exception: typing.Any = mock.Mock()
        mock_other_exception: typing.Any = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        interval.set_fatal_exceptions(mock_exception, mock_other_exception)

        assert interval._fatal_exceptions == (mock_exception, mock_other_exception)


class TestTimeSchedule:
    def test_callback_property(self):
        mock_callback = mock.AsyncMock()
        interval = tanjun.schedules.TimeSchedule(mock_callback)

        assert interval.callback is mock_callback

    def test_is_alive_property(self):
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        assert interval.is_alive is False

    @pytest.mark.asyncio()
    async def test_is_alive_property_when_is_alive(self):
        mock_callback = mock.AsyncMock()
        client = alluka.Client()
        interval = tanjun.schedules.TimeSchedule(mock_callback)

        interval.start(client)

        assert interval.is_alive is True

        interval.force_stop()

    @pytest.mark.parametrize(
        ("kwargs", "expected_message"),
        [
            pytest.param(
                {"months": 0},
                r"months value must be \(inclusively\) between 1 and 12, not 0",
                id="Single month too small",
            ),
            pytest.param(
                {"months": 13},
                r"months value must be \(inclusively\) between 1 and 12, not 13",
                id="Single month too large",
            ),
            pytest.param(
                {"months": [-1, 0, 4, 5]},
                r"months must be \(inclusively\) between 1 and 12, not -1 and 5",
                id="Multiple months too small",
            ),
            pytest.param(
                {"months": [4, 5, 7, 14]},
                r"months must be \(inclusively\) between 1 and 12, not 4 and 14",
                id="Multiple months too large",
            ),
            pytest.param(
                {"months": range(0, 14)},
                r"months must be \(inclusively\) between 1 and 12, not 0 and 13",
                id="Months range out of range",
            ),
            pytest.param(
                {"days": 0},
                r"days value must be \(inclusively\) between 1 and 31, not 0",
                id="Single day too small",
            ),
            pytest.param(
                {"days": 32},
                r"days value must be \(inclusively\) between 1 and 31, not 32",
                id="Single day too large",
            ),
            pytest.param(
                {"days": [-1, 0, 4, 5]},
                r"days must be \(inclusively\) between 1 and 31, not -1 and 5",
                id="Multiple days too small",
            ),
            pytest.param(
                {"days": [4, 5, 7, 32]},
                r"days must be \(inclusively\) between 1 and 31, not 4 and 32",
                id="Multiple days too large",
            ),
            pytest.param(
                {"days": range(0, 34)},
                r"days must be \(inclusively\) between 1 and 31, not 0 and 33",
                id="days range out of range",
            ),
            pytest.param(
                {"days": 0, "weekly": True},
                r"days value must be \(inclusively\) between 1 and 8, not 0",
                id="Single day too small and weekly",
            ),
            pytest.param(
                {"days": 9, "weekly": True},
                r"days value must be \(inclusively\) between 1 and 8, not 9",
                id="Single day too large and weekly",
            ),
            pytest.param(
                {"days": [-1, 0, 4, 5], "weekly": True},
                r"days must be \(inclusively\) between 1 and 8, not -1 and 5",
                id="Multiple days too small and weekly",
            ),
            pytest.param(
                {"days": [4, 5, 7, 9], "weekly": True},
                r"days must be \(inclusively\) between 1 and 8, not 4 and 9",
                id="Multiple days too large and weekly",
            ),
            pytest.param(
                {"days": range(1, 10), "weekly": True},
                r"days must be \(inclusively\) between 1 and 8, not 1 and 9",
                id="days range out of range and weekly",
            ),
            pytest.param(
                {"hours": -1},
                r"hours value must be \(inclusively\) between 0 and 23, not -1",
                id="Single hour too small",
            ),
            pytest.param(
                {"hours": 24},
                r"hours value must be \(inclusively\) between 0 and 23, not 24",
                id="Single hour too large",
            ),
            pytest.param(
                {"hours": [-1, 0, 4, 5]},
                r"hours must be \(inclusively\) between 0 and 23, not -1 and 5",
                id="Multiple hours too small",
            ),
            pytest.param(
                {"hours": [4, 5, 7, 25]},
                r"hours must be \(inclusively\) between 0 and 23, not 4 and 25",
                id="Multiple hours too large",
            ),
            pytest.param(
                {"hours": range(0, 25)},
                r"hours must be \(inclusively\) between 0 and 23, not 0 and 24",
                id="Hours range out of range",
            ),
            pytest.param(
                {"minutes": -1},
                r"minutes value must be \(inclusively\) between 0 and 59, not -1",
                id="Single minute too small",
            ),
            pytest.param(
                {"minutes": 60},
                r"minutes value must be \(inclusively\) between 0 and 59, not 60",
                id="Single minute too large",
            ),
            pytest.param(
                {"minutes": [-1, 0, 4, 5]},
                r"minutes must be \(inclusively\) between 0 and 59, not -1 and 5",
                id="Multiple minutes too small",
            ),
            pytest.param(
                {"minutes": [4, 5, 7, 60]},
                r"minutes must be \(inclusively\) between 0 and 59, not 4 and 60",
                id="Multiple minutes too large",
            ),
            pytest.param(
                {"minutes": range(0, 61)},
                r"minutes must be \(inclusively\) between 0 and 59, not 0 and 60",
                id="Minutes range out of range",
            ),
            #
            pytest.param(
                {"seconds": -1},
                r"seconds value must be \(inclusively\) between 0 and 59, not -1",
                id="Single second too small",
            ),
            pytest.param(
                {"seconds": 60},
                r"seconds value must be \(inclusively\) between 0 and 59, not 60",
                id="Single second too large",
            ),
            pytest.param(
                {"seconds": [-1, 0, 4, 5]},
                r"seconds must be \(inclusively\) between 0 and 59, not -1 and 5",
                id="Multiple seconds too small",
            ),
            pytest.param(
                {"seconds": [4, 5, 7, 60]},
                r"seconds must be \(inclusively\) between 0 and 59, not 4 and 60",
                id="Multiple seconds too large",
            ),
            pytest.param(
                {"seconds": range(0, 61)},
                r"seconds must be \(inclusively\) between 0 and 59, not 0 and 60",
                id="Seconds range out of range",
            ),
        ],
    )
    def test_init_with_out_of_range_value(self, kwargs: dict[str, typing.Any], expected_message: str):
        with pytest.raises(ValueError, match=expected_message):
            tanjun.schedules.TimeSchedule(mock.Mock(), **kwargs)

    @pytest.mark.parametrize(
        ("kwargs", "expected_message"),
        [
            pytest.param({"months": 2.4}, "months value must be an integer, not a float", id="Single month"),
            pytest.param({"months": [4, 6, 7, 3.4, 6]}, "Cannot pass floats for months", id="Multiple months"),
            pytest.param({"days": 5.34}, "days value must be an integer, not a float", id="Single day"),
            pytest.param({"days": [3, 5, 2, 4, 5.34]}, "Cannot pass floats for days", id="Multiple days"),
            pytest.param({"hours": 4.3}, "hours value must be an integer, not a float", id="Single hour"),
            pytest.param({"hours": [3, 5, 2, 4.5, 6]}, "Cannot pass floats for hours", id="Multiple hours"),
            pytest.param({"minutes": 3.5}, "minutes value must be an integer, not a float", id="Single minute"),
            pytest.param({"minutes": [4, 5, 5.6, 6, 7]}, "Cannot pass floats for minutes", id="Multiple minutes"),
            pytest.param({"seconds": 3.5}, "seconds value must be an integer, not a float", id="Single second"),
            pytest.param({"seconds": [3, 4, 5, 6.54, 3]}, "Cannot pass floats for seconds", id="Multiple seconds"),
        ],
    )
    def test_init_when_float_passed(self, kwargs: dict[str, typing.Any], expected_message: str):
        with pytest.raises(ValueError, match=expected_message):
            tanjun.schedules.TimeSchedule(mock.Mock(), **kwargs)

    @pytest.mark.asyncio()
    async def test_call_dunder_method(self):
        mock_callback: typing.Any = mock.AsyncMock()
        interval = tanjun.schedules.TimeSchedule(mock_callback)

        result = await interval(123, "32", a=432, b=123)

        assert result is None
        mock_callback.assert_awaited_once_with(123, "32", a=432, b=123)

    def test_copy(self):
        mock_callback: typing.Any = mock.AsyncMock()
        interval = tanjun.schedules.TimeSchedule(mock_callback)
        interval._tasks.append(mock.Mock())

        result = interval.copy()

        assert result is not interval
        assert result.callback is mock_callback
        assert result._tasks == []
        assert result._tasks is not interval._tasks
        assert result._config == interval._config
        assert result._config is not interval._config

    def test_copy_when_schedule_is_active(self):
        interval = tanjun.schedules.TimeSchedule(mock.Mock())
        interval._task = mock.Mock()

        with pytest.raises(RuntimeError, match="Cannot copy an active schedule"):
            interval.copy()

    def test_load_into_component(self):
        mock_component = mock.Mock(tanjun.Component)
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        interval.load_into_component(mock_component)

        mock_component.add_schedule.assert_called_once_with(interval)

    def test_load_into_component_when_not_loader(self):
        mock_component = mock.Mock(object)
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        interval.load_into_component(mock_component)

    def test_start(self):
        class StubSchedule(tanjun.schedules.TimeSchedule[typing.Any]):
            ...

        mock_client = mock.Mock()
        interval = StubSchedule(mock.AsyncMock())
        interval._loop = mock.Mock()

        with mock.patch.object(asyncio, "get_running_loop") as get_running_loop:
            interval.start(mock_client)

        assert interval._task is get_running_loop.return_value.create_task.return_value
        assert interval.is_alive is True
        get_running_loop.assert_called_once_with()
        get_running_loop.return_value.create_task.assert_called_once_with(interval._loop.return_value)
        interval._loop.assert_called_once_with(mock_client)

    def test_start_when_passed_event_loop(self):
        class StubSchedule(tanjun.schedules.TimeSchedule[typing.Any]):
            ...

        mock_client = mock.Mock()
        mock_loop = mock.Mock()
        interval = StubSchedule(mock.AsyncMock())
        interval._loop = mock.Mock()

        interval.start(mock_client, loop=mock_loop)

        assert interval._task is mock_loop.create_task.return_value
        assert interval.is_alive is True
        mock_loop.create_task.assert_called_once_with(interval._loop.return_value)
        interval._loop.assert_called_once_with(mock_client)

    def test_start_when_passed_event_loop_isnt_active(self):
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())
        mock_loop = mock.Mock()
        mock_loop.is_running.return_value = False

        with pytest.raises(RuntimeError, match="Event loop is not running"):
            interval.start(mock.Mock(), loop=mock_loop)

    @pytest.mark.asyncio()
    async def test_start_when_already_running(self):
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())
        interval.start(mock.Mock())
        try:

            with pytest.raises(RuntimeError, match="Schedule is already running"):
                interval.start(mock.Mock())

        finally:
            interval.force_stop()

    @pytest.mark.asyncio()
    async def test_force_stop(self):
        mock_loop_task = mock.Mock()
        mock_task_1 = asyncio.create_task(asyncio.sleep(60, result=None))
        mock_task_2 = asyncio.create_task(asyncio.sleep(60, result=None))
        mock_task_3 = asyncio.create_task(asyncio.sleep(60, result=None))
        interval = tanjun.schedules.TimeSchedule(mock.Mock())
        interval._task = mock_loop_task
        interval._add_task(mock_task_1)
        interval._add_task(mock_task_2)
        interval._add_task(mock_task_3)

        interval.force_stop()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0)

        assert interval.is_alive is False
        assert interval._task is None
        assert mock_task_1.cancelled() is True
        assert mock_task_2.cancelled() is True
        assert mock_task_3.cancelled() is True

    def test_force_stop_when_no_tasks(self):
        mock_loop_task = mock.Mock()
        interval = tanjun.schedules.TimeSchedule(mock.Mock())
        interval._task = mock_loop_task

        interval.force_stop()

        assert interval.is_alive is False
        assert interval._task is None

    def test_force_stop_when_not_active(self):
        interval = tanjun.schedules.TimeSchedule(mock.Mock())

        with pytest.raises(RuntimeError, match="Schedule is not running"):
            interval.force_stop()

    @pytest.mark.asyncio()
    async def test_stop(self):
        mock_task = mock.Mock()
        mock_task_1 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        mock_task_2 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        mock_task_3 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())
        interval._task = mock_task
        interval._add_task(mock_task_1)
        interval._add_task(mock_task_2)
        interval._add_task(mock_task_3)

        await interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval.is_alive is False
        assert interval._task is None
        assert interval._tasks == []
        assert mock_task_1.result() is None
        assert mock_task_2.result() is None
        assert mock_task_3.result() is None

    @pytest.mark.asyncio()
    async def test_stop_when_some_tasks_time_out(self):
        mock_task = mock.Mock()
        mock_task_1 = asyncio.create_task(asyncio.sleep(0.6, result=None))
        mock_task_2 = asyncio.create_task(asyncio.sleep(0.2, result=None))
        mock_task_3 = asyncio.create_task(asyncio.sleep(0.5, result=None))
        mock_task_4 = asyncio.create_task(asyncio.sleep(0.1, result=None))
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())
        interval._task = mock_task
        interval._add_task(mock_task_1)
        interval._add_task(mock_task_2)
        interval._add_task(mock_task_3)
        interval._add_task(mock_task_4)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(interval.stop(), 0.25)

        mock_task.cancel.assert_called_once_with()
        assert interval.is_alive is False
        assert interval._task is None
        assert interval._tasks == []
        assert mock_task_1.cancelled() is True
        assert mock_task_2.result() is None
        assert mock_task_3.cancelled() is True
        assert mock_task_4.result() is None

    @pytest.mark.asyncio()
    async def test_stop_when_not_running(self):
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        with pytest.raises(RuntimeError, match="Schedule is not running"):
            await interval.stop()

    # Note: these have to be at least a microsecond after the target time as
    # the unix event loop won't return the sleep until the target time has passed,
    # not just been reached.
    @pytest.mark.parametrize(
        ("kwargs", "start", "tick_fors", "sleep_for", "expected_dates"),
        [
            pytest.param(
                {
                    "months": 1,
                    "days": 1,
                    "hours": 0,
                    "minutes": 0,
                    "seconds": 0,
                },
                datetime.datetime(2020, 12, 31, 23, 59, 59),
                [
                    datetime.timedelta(seconds=1, microseconds=500001),
                    datetime.timedelta(days=365),
                    datetime.timedelta(days=365),
                ],
                datetime.timedelta(days=730, seconds=2, microseconds=500001),
                [
                    datetime.datetime(2021, 1, 1, 0, 0, 0, 500001),
                    datetime.datetime(2022, 1, 1, 0, 0, 0, 500001),
                    datetime.datetime(2023, 1, 1, 0, 0, 0, 500001),
                ],
                id="Start of each section",
            ),
            pytest.param(
                {
                    "months": 1,
                    "weekly": True,
                    "days": 1,
                    "hours": 0,
                    "minutes": 0,
                    "seconds": 0,
                },
                datetime.datetime(2066, 12, 31, 23, 59, 59),
                [
                    datetime.timedelta(days=2, seconds=1, microseconds=500001),
                    *(datetime.timedelta(days=7),) * 4,
                    datetime.timedelta(days=336),
                    *(datetime.timedelta(days=7),) * 4,
                ],
                datetime.timedelta(days=394, seconds=2, microseconds=500001),
                [
                    datetime.datetime(2067, 1, 3, 0, 0, 0, 500001),
                    datetime.datetime(2067, 1, 10, 0, 0, 0, 500001),
                    datetime.datetime(2067, 1, 17, 0, 0, 0, 500001),
                    datetime.datetime(2067, 1, 24, 0, 0, 0, 500001),
                    datetime.datetime(2067, 1, 31, 0, 0, 0, 500001),
                    datetime.datetime(2068, 1, 2, 0, 0, 0, 500001),
                    datetime.datetime(2068, 1, 9, 0, 0, 0, 500001),
                    datetime.datetime(2068, 1, 16, 0, 0, 0, 500001),
                    datetime.datetime(2068, 1, 23, 0, 0, 0, 500001),
                    datetime.datetime(2068, 1, 30, 0, 0, 0, 500001),
                ],
                id="Start of each section weekly",
            ),
            # pytest.param(
            #     {
            #         "months": [11, 12],  # This also tests that out-of-month-range date handling works.
            #         "days": 31,
            #         "hours": 23,
            #         "minutes": 59,
            #         "seconds": 59,
            #     },
            #     datetime.datetime(2015, 10, 5, 23, 1, 1),
            #     [
            #         datetime.timedelta(days=87, minutes=58, seconds=58, microseconds=500001),
            #         datetime.timedelta(days=366),
            #         datetime.timedelta(days=1),
            #     ],
            #     datetime.timedelta(days=453, minutes=58, seconds=58, microseconds=500001),
            #     [
            #         datetime.datetime(2015, 12, 31, 23, 59, 59, 500001),
            #         datetime.datetime(2016, 12, 31, 23, 59, 59, 500001),
            #     ],
            #     id="End of each section",
            # ),
            # pytest.param(
            #     {
            #         "months": [11, 12],
            #         "weekly": True,
            #         "days": 31,
            #         "hours": 23,
            #         "minutes": 59,
            #         "seconds": 59,
            #     },
            #     datetime.datetime(2066, 12, 31, 23, 59, 59),
            #     [
            #         datetime.timedelta(days=2, seconds=1, microseconds=500001),
            #         *(datetime.timedelta(days=7),) * 4,
            #         datetime.timedelta(days=336),
            #         *(datetime.timedelta(days=7),) * 4,
            #     ],
            #     datetime.timedelta(days=394, seconds=2, microseconds=500001),
            #     [
            #         datetime.datetime(2067, 1, 3, 0, 0, 0, 500001),
            #         datetime.datetime(2067, 1, 10, 0, 0, 0, 500001),
            #         datetime.datetime(2067, 1, 17, 0, 0, 0, 500001),
            #         datetime.datetime(2067, 1, 24, 0, 0, 0, 500001),
            #         datetime.datetime(2067, 1, 31, 0, 0, 0, 500001),
            #         datetime.datetime(2068, 1, 2, 0, 0, 0, 500001),
            #         datetime.datetime(2068, 1, 9, 0, 0, 0, 500001),
            #         datetime.datetime(2068, 1, 16, 0, 0, 0, 500001),
            #         datetime.datetime(2068, 1, 23, 0, 0, 0, 500001),
            #         datetime.datetime(2068, 1, 30, 0, 0, 0, 500001),
            #     ],
            #     id="End of each section weekly",
            # ),
            pytest.param(
                {},
                datetime.datetime(2011, 1, 4, 11, 57, 10),
                [datetime.timedelta(seconds=50, milliseconds=500, microseconds=1), datetime.timedelta(minutes=1)],
                datetime.timedelta(minutes=6, seconds=30),
                [
                    datetime.datetime(2011, 1, 4, 11, 58, 0, 500001),
                    datetime.datetime(2011, 1, 4, 11, 59, 0, 500001),
                    datetime.datetime(2011, 1, 4, 12, 0, 0, 500001),
                    datetime.datetime(2011, 1, 4, 12, 1, 0, 500001),
                    datetime.datetime(2011, 1, 4, 12, 2, 0, 500001),
                    datetime.datetime(2011, 1, 4, 12, 3, 0, 500001),
                ],
                id="default timing",
            ),
            pytest.param(
                {},
                datetime.datetime(2035, 11, 3, 23, 56, 5),
                [datetime.timedelta(seconds=55, milliseconds=500, microseconds=1), datetime.timedelta(minutes=1)],
                datetime.timedelta(minutes=6, seconds=30),
                [
                    datetime.datetime(2035, 11, 3, 23, 57, 0, 500001),
                    datetime.datetime(2035, 11, 3, 23, 58, 0, 500001),
                    datetime.datetime(2035, 11, 3, 23, 59, 0, 500001),
                    datetime.datetime(2035, 11, 4, 0, 0, 0, 500001),
                    datetime.datetime(2035, 11, 4, 0, 1, 0, 500001),
                    datetime.datetime(2035, 11, 4, 0, 2, 0, 500001),
                ],
                id="default timing bumps year",
            ),
            pytest.param(
                {
                    "months": [7, 4],
                    "days": [14, 7],
                    "hours": [17, 12],
                    "minutes": [55, 22],
                    "seconds": [30, 10],
                },
                datetime.datetime(2016, 3, 4, 10, 40, 30),
                _chain(
                    (
                        d,
                        datetime.timedelta(seconds=20),
                        datetime.timedelta(minutes=32, seconds=40),
                        datetime.timedelta(seconds=20),
                    )
                    for d in (
                        datetime.timedelta(days=34, seconds=6100, microseconds=500001),
                        datetime.timedelta(hours=4, minutes=26, seconds=40),
                        datetime.timedelta(days=6, hours=18, minutes=26, seconds=40),
                        datetime.timedelta(hours=4, minutes=26, seconds=40),
                        datetime.timedelta(days=83, hours=18, minutes=26, seconds=40),
                        datetime.timedelta(hours=4, minutes=26, seconds=40),
                        datetime.timedelta(days=6, hours=18, minutes=26, seconds=40),
                        datetime.timedelta(hours=4, minutes=26, seconds=40),
                    )
                )
                + [
                    datetime.timedelta(days=266, hours=18, minutes=26, seconds=40),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1),
                ],
                datetime.timedelta(days=399, hours=1, minutes=42, seconds=1),
                [
                    *(
                        datetime.datetime(2016, *args, microsecond=500001)
                        for args in itertools.product([4, 7], [7, 14], [12, 17], [22, 55], [10, 30])
                    ),
                    datetime.datetime(2017, 4, 7, 12, 22, 10, 500001),
                    datetime.datetime(2017, 4, 7, 12, 22, 30, 500001),
                ],
                id="all time fields specified",
            ),
            pytest.param(
                {
                    "months": [1, 5, 9],
                    "weekly": True,
                    "days": [3, 5],
                    "hours": [5],
                    "minutes": [45],
                    "seconds": [10],
                },
                datetime.datetime(2069, 3, 5, 5, 45, 10),
                [
                    datetime.timedelta(days=57, microseconds=500001),
                    *(datetime.timedelta(days=2), datetime.timedelta(days=5)) * 4,
                    datetime.timedelta(days=2),
                    datetime.timedelta(days=96),
                    *(datetime.timedelta(days=2), datetime.timedelta(days=5)) * 3,
                    datetime.timedelta(days=2),
                    datetime.timedelta(days=96),
                    *(datetime.timedelta(days=2), datetime.timedelta(days=5)) * 4,
                    datetime.timedelta(days=2),
                ],
                datetime.timedelta(days=333),
                [
                    datetime.datetime(2069, 5, 1, 5, 45, 10, 500001),  # 3rd day
                    datetime.datetime(2069, 5, 3, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 8, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 10, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 15, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 17, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 22, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 24, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 29, 5, 45, 10, 500001),
                    datetime.datetime(2069, 5, 31, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 4, 5, 45, 10, 500001),  # 3rd day
                    datetime.datetime(2069, 9, 6, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 11, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 13, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 18, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 20, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 25, 5, 45, 10, 500001),
                    datetime.datetime(2069, 9, 27, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 1, 5, 45, 10, 500001),  # 3rd day
                    datetime.datetime(2070, 1, 3, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 8, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 10, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 15, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 17, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 22, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 24, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 29, 5, 45, 10, 500001),
                    datetime.datetime(2070, 1, 31, 5, 45, 10, 500001),
                ],
                id="all time fields specified weekly",
            ),
            pytest.param(
                {
                    "months": range(11, 13),
                    "days": [1, 15],
                    "hours": range(7, 5, -1),
                    "minutes": range(3, 1, -1),
                },
                datetime.datetime(2016, 7, 15, 12, 22, 10, 500001),
                _chain(
                    (
                        d,
                        datetime.timedelta(minutes=1),
                        datetime.timedelta(minutes=59),
                        datetime.timedelta(minutes=1),
                    )
                    for d in (
                        datetime.timedelta(days=108, hours=17, minutes=39, seconds=50),
                        datetime.timedelta(days=13, hours=22, minutes=59),
                        datetime.timedelta(days=15, hours=22, minutes=59),
                        datetime.timedelta(days=13, hours=22, minutes=59),
                        datetime.timedelta(days=320, hours=22, minutes=59),
                        datetime.timedelta(days=13, hours=22, minutes=59),
                    )
                )
                + [datetime.timedelta(days=3)],
                datetime.timedelta(days=487, hours=18, minutes=41, seconds=50),
                [
                    *(
                        datetime.datetime(2016, *args, microsecond=500001)
                        for args in itertools.product([11, 12], [1, 15], [6, 7], [2, 3])
                    ),
                    *(
                        datetime.datetime(2017, 11, *args, microsecond=500001)
                        for args in itertools.product([1, 15], [6, 7], [2, 3])
                    ),
                ],
                id="specific months, days, hours and minutes",
            ),
            pytest.param(
                {
                    "months": range(12, 10, -1),
                    "weekly": True,
                    "days": range(3, 5),
                    "hours": range(6, 8),
                    "minutes": range(3, 4),
                },
                datetime.datetime(2019, 5, 1),
                [
                    datetime.timedelta(days=189, hours=6, minutes=3, microseconds=500001),
                    datetime.timedelta(hours=1),
                    datetime.timedelta(hours=23),
                    datetime.timedelta(hours=1),
                    *(
                        datetime.timedelta(days=5, hours=23),
                        datetime.timedelta(hours=1),
                        datetime.timedelta(hours=23),
                        datetime.timedelta(hours=1),
                    )
                    * 7,
                    datetime.timedelta(days=313, hours=23),
                    datetime.timedelta(hours=1),
                    datetime.timedelta(hours=23),
                ],
                datetime.timedelta(days=554, hours=6, minutes=4),
                [
                    datetime.datetime(2019, 11, 6, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 6, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 7, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 7, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 13, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 13, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 14, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 14, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 20, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 20, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 21, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 21, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 27, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 27, 7, 3, 00, 500001),
                    datetime.datetime(2019, 11, 28, 6, 3, 00, 500001),
                    datetime.datetime(2019, 11, 28, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 4, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 4, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 5, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 5, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 11, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 11, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 12, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 12, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 18, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 18, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 19, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 19, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 25, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 25, 7, 3, 00, 500001),
                    datetime.datetime(2019, 12, 26, 6, 3, 00, 500001),
                    datetime.datetime(2019, 12, 26, 7, 3, 00, 500001),
                    datetime.datetime(2020, 11, 4, 6, 3, 00, 500001),
                    datetime.datetime(2020, 11, 4, 7, 3, 00, 500001),
                    datetime.datetime(2020, 11, 5, 6, 3, 00, 500001),
                ],
                id="specific months, days, hours and minutes weekly",
            ),
            # pytest.param(
            #     {
            #         "months": 8,
            #         "days": range(4, 2, -1),  # [4, 3]
            #         "hours": 3,
            #         "seconds": range(5, 9, 2),  # [5, 7]
            #     },
            #     datetime.datetime(3222, 1, 2, 3, microsecond=500001),
            #     [
            #         datetime.timedelta(days=213, seconds=5),
            #         *(datetime.timedelta(seconds=2), datetime.timedelta(seconds=58)) * 115,
            #         datetime.timedelta(seconds=2),
            #         datetime.timedelta(hours=23, minutes=1, seconds=58),
            #         *(datetime.timedelta(seconds=2), datetime.timedelta(seconds=58)) * 115,
            #         datetime.timedelta(seconds=2),
            #         datetime.timedelta(days=363, hours=23, minutes=1, seconds=58),
            #         *(datetime.timedelta(seconds=2), datetime.timedelta(seconds=58)) * 115,
            #         datetime.timedelta(seconds=2),
            #     ],
            #     datetime.timedelta(days=578, minutes=58, seconds=7, microseconds=500001),
            #     [
            #         *(
            #             datetime.datetime(3222, 8, day, 3, minute, second, 500001)
            #             for day, minute, second in itertools.product([3, 4], range(0, 59), [5, 7])
            #         ),
            #         *(
            #             datetime.datetime(3223, 8, 3, 3, minute, second, 500001)
            #             for minute, second in itertools.product(range(0, 59), [5, 7])
            #         ),
            #     ],
            #     id="specific months, days, hours and seconds",
            # ),
            # ("kwargs", "start", "tick_fors", "sleep_for", "expected_dates")  # TODO: test timezone behaviour
            # needs to be singled: days, days weekly, minutes, seconds
            # pytest.param(id="specific months, days, hours and seconds weekly"),  #  backwards range days and seconds
            # pytest.param(id="specific months, days, minutes and seconds"),   # backwards range days
            # pytest.param(id="specific months, days, minutes and seconds weekly"),
            # pytest.param(id="specific months, hours, minutes and seconds"),
            # pytest.param(id="specific months, days and hours"),
            # pytest.param(id="specific months, days and hours weekly"),
            # pytest.param(id="specific months, days and minutes"),
            # pytest.param(id="specific months, days and minutes weekly"),
            # pytest.param(id="specific months, days and seconds"),
            # pytest.param(id="specific months, days and seconds weekly"),
            # pytest.param(id="specific months, hours and minutes"),
            # pytest.param(id="specific months, hours and seconds"),
            # pytest.param(id="specific months, minutes and seconds"),
            # pytest.param(id="specific months and days"),
            # pytest.param(id="specific months and days weekly"),
            # pytest.param(id="specific months and hours"),
            # pytest.param(id="specific months and minutes"),
            # pytest.param(id="specific months and seconds"),
            # pytest.param(id="specific months"),
            # pytest.param(id="specific days, hours minutes and seconds"),
            # pytest.param(id="specific days, hours minutes and seconds weekly"),
            # pytest.param(id="specific days, hours and minutes"),
            # pytest.param(id="specific days, hours and minutes weekly"),
            # pytest.param(id="specific days, hours and seconds"),
            # pytest.param(id="specific days, hours and seconds weekly"),
            # pytest.param(id="specific days, minutes and seconds"),
            # pytest.param(id="specific days, minutes and seconds weekly"),
            # pytest.param(id="specific days and hours"),
            # pytest.param(id="specific days and hours weekly"),
            # pytest.param(id="specific days and minutes"),
            # pytest.param(id="specific days and minutes weekly"),
            # pytest.param(id="specific days and seconds"),
            # pytest.param(id="specific days and seconds weekly"),
            # pytest.param(id="specific days"),
            # pytest.param(id="specific days weekly"),
            # pytest.param(id="specific hours, minutes and seconds"),
            # pytest.param(id="specific hours and minutes"),
            # pytest.param(id="specific hours and seconds"),
            # pytest.param(id="specific hours"),
            # pytest.param(id="specific minutes and seconds"),
            # pytest.param(id="specific minutes"),
            # pytest.param(id="specific seconds"),
        ],
    )
    @pytest.mark.timeout(_TIMEOUT)
    @pytest.mark.asyncio()
    async def test_run(
        self,
        kwargs: dict[str, typing.Any],
        start: datetime.datetime,
        tick_fors: list[datetime.timedelta],
        sleep_for: datetime.timedelta,
        expected_dates: typing.List[datetime.datetime],
    ):
        # Ensure test-data integrity
        assert start < expected_dates[0], "Start must be before expected dates"
        assert sorted(expected_dates) == expected_dates, "Expected dates must be sorted"

        called_at: list[datetime.datetime] = []

        @_print_tb
        async def callback():
            called_at.append(datetime.datetime.now())
            clock.spawn_ticker()

        schedule = tanjun.schedules.as_time_schedule(**kwargs)(callback)

        frozen_time: freezegun.api.FrozenDateTimeFactory
        with freezegun.freeze_time(start, tick=False) as frozen_time:
            clock = _ManualClock(frozen_time, tick_fors)

            schedule.start(alluka.Client())
            clock.spawn_ticker()
            await asyncio.sleep(sleep_for.total_seconds())
            await schedule.stop()
            clock.stop_ticker()

        assert called_at == expected_dates

    @pytest.mark.timeout(_TIMEOUT)
    @pytest.mark.asyncio()
    async def test_error_handling(self):
        called_at: list[datetime.datetime] = []

        @_print_tb
        async def callback() -> None:
            called_at.append(datetime.datetime.now())
            clock.spawn_ticker()
            length = len(called_at)
            if length == 1:
                raise RuntimeError("Not caught")

            if length == 2:
                raise ValueError("Ignored")

            if length == 3:
                raise TypeError("Fatal")

        schedule = (
            tanjun.schedules.as_time_schedule(hours=[4, 6], minutes=30)(callback)
            .set_fatal_exceptions(TypeError)
            .set_ignored_exceptions(ValueError)
        )

        frozen_time: freezegun.api.FrozenDateTimeFactory
        with freezegun.freeze_time(datetime.datetime(2044, 4, 4), tick=False) as frozen_time:
            clock = _ManualClock(
                frozen_time,
                [
                    datetime.timedelta(hours=4, minutes=30, microseconds=500001),
                    datetime.timedelta(hours=2),
                    datetime.timedelta(hours=22),
                ],
            ).spawn_ticker()
            schedule.start(alluka.Client())
            await asyncio.sleep(datetime.timedelta(days=1, seconds=16201).total_seconds())

            clock.stop_ticker()
            assert schedule.is_alive is False

        assert called_at == [
            datetime.datetime(2044, 4, 4, 4, 30, 0, 500001),
            datetime.datetime(2044, 4, 4, 6, 30, 0, 500001),
            datetime.datetime(2044, 4, 5, 4, 30, 0, 500001),
        ]
