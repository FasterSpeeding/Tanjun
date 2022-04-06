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

_CallbackT = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, typing.Any]]
_TIMEOUT: typing.Final[float] = 1


def _print_tb(callback: _CallbackT, /) -> _CallbackT:
    @functools.wraps(callback)
    async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        try:
            return await callback(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise

    return wrapper


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

        # freeze_time.tick(datetime.timedelta(microseconds=1))
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

    assert result.interval == datetime.timedelta(seconds=123)
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

    @pytest.mark.parametrize("interval", [datetime.timedelta(seconds=652134), 652134, 652134.0])
    def test_interval_property(self, interval: typing.Union[int, float, datetime.timedelta]):
        interval_ = tanjun.schedules.IntervalSchedule(mock.Mock(), interval)

        assert interval_.interval == datetime.timedelta(seconds=652134)

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

        result = interval.copy()

        assert result.callback is interval.callback
        assert result.interval is interval.interval
        assert result.iteration_count is interval.iteration_count
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
        error = KeyError("hihihiih")
        mock_client.call_with_async_di.side_effect = error
        stop = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"stop": stop}),
        )(mock_callback, 123, fatal_exceptions=[LookupError], ignored_exceptions=[Exception])

        with pytest.raises(KeyError) as exc_info:
            await interval._execute(mock_client)

        assert exc_info.value is error

        mock_client.call_with_async_di.assert_awaited_once_with(mock_callback)
        stop.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test__execute_when_ignored_exception(self):
        mock_callback = mock.Mock()
        mock_client = mock.AsyncMock()
        error = IndexError("hihihiih")
        mock_client.call_with_async_di.side_effect = error
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

        with pytest.raises(ValueError, match="hihihiih") as exc_info:
            await interval._execute(mock_client)

        assert exc_info.value is error

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
            interval.stop()
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
            close_event.set()
            clock.stop_ticker()
            close_time = time.time_ns()

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

        assert interval._task is None
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
        async def callback():
            call_times.append(time.time_ns())
            clock.spawn_ticker()

        @_print_tb
        async def on_start():
            nonlocal start_time
            start_time = time.time_ns()

        @_print_tb
        async def on_stop():
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
            interval.stop()
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
        mock_client.call_with_async_di = mock.AsyncMock(side_effect=[error, None])
        mock_client.get_callback_override.return_value = None
        mock_start = mock.Mock()
        mock_stop = mock.Mock()
        mock_execute = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = (
            types.new_class(
                "StubIntervalSchedule",
                (tanjun.schedules.IntervalSchedule[typing.Any],),
                exec_body=lambda ns: ns.update({"_execute": mock_execute}),
            )(mock.Mock(), 123, ignored_exceptions=[RuntimeError], fatal_exceptions=fatal_exceptions)
            .set_start_callback(mock_start)
            .set_stop_callback(mock_stop)
        )
        interval._task = mock.Mock()

        with mock.patch.object(asyncio, "sleep") as sleep, pytest.raises(KeyError) as exc_info:
            await interval._loop(mock_client)

        assert exc_info.value is error
        mock_client.call_with_async_di.assert_has_awaits([mock.call(mock_start), mock.call(mock_stop)])
        mock_execute.assert_not_called()
        sleep.assert_not_called()
        assert interval._task is None

    @pytest.mark.asyncio()
    async def test__loop_and_start_raises_ignored(self):
        mock_client = mock.Mock()
        mock_client.call_with_async_di = mock.AsyncMock(side_effect=[KeyError(), None])
        mock_client.get_callback_override.return_value = None
        mock_start = mock.Mock()
        mock_stop = mock.Mock()
        mock_execute = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = (
            types.new_class(
                "StubIntervalSchedule",
                (tanjun.schedules.IntervalSchedule[typing.Any],),
                exec_body=lambda ns: ns.update({"_execute": mock_execute}),
            )(mock.Mock(), 123, ignored_exceptions=[LookupError])
            .set_start_callback(mock_start)
            .set_stop_callback(mock_stop)
        )
        interval._task = mock.Mock()

        with (
            mock.patch.object(asyncio, "sleep", side_effect=asyncio.CancelledError) as sleep,
            pytest.raises(asyncio.CancelledError),
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        mock_client.call_with_async_di.assert_has_awaits([mock.call(mock_start), mock.call(mock_stop)])
        mock_execute.assert_not_called()
        get_running_loop.return_value.create_task.assert_not_called()
        sleep.assert_called_once_with(123.0)
        assert interval._task is None

    @pytest.mark.asyncio()
    async def test__loop_and_stop_raises(self):
        error = RuntimeError()
        mock_client = mock.Mock()
        mock_client.get_callback_override.return_value = None
        mock_client.call_with_async_di = mock.AsyncMock(side_effect=[None, error])
        mock_start = mock.Mock()
        mock_stop = mock.Mock()
        mock_execute = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = (
            types.new_class(
                "StubIntervalSchedule",
                (tanjun.schedules.IntervalSchedule[typing.Any],),
                exec_body=lambda ns: ns.update({"_execute": mock_execute}),
            )(mock.Mock(), 123, ignored_exceptions=[LookupError])
            .set_start_callback(mock_start)
            .set_stop_callback(mock_stop)
        )
        interval._task = mock.Mock()

        with (
            mock.patch.object(asyncio, "sleep", side_effect=asyncio.CancelledError) as sleep,
            pytest.raises(RuntimeError) as exc_info,
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        assert exc_info.value is error
        mock_client.call_with_async_di.assert_has_awaits([mock.call(mock_start), mock.call(mock_stop)])
        mock_execute.assert_not_called()
        get_running_loop.return_value.create_task.assert_not_called()
        sleep.assert_awaited_once_with(123.0)
        assert interval._task is None

    @pytest.mark.asyncio()
    async def test__loop_and_stop_raises_ignored(self):
        mock_client = mock.Mock()
        mock_client.get_callback_override.return_value = None
        mock_client.call_with_async_di = mock.AsyncMock(side_effect=[None, LookupError()])
        mock_start = mock.Mock()
        mock_stop = mock.Mock()
        mock_execute = mock.Mock()
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = (
            types.new_class(
                "StubIntervalSchedule",
                (tanjun.schedules.IntervalSchedule[typing.Any],),
                exec_body=lambda ns: ns.update({"_execute": mock_execute}),
            )(mock.Mock(), 123, ignored_exceptions=[LookupError])
            .set_start_callback(mock_start)
            .set_stop_callback(mock_stop)
        )
        interval._task = mock.Mock()

        with (
            mock.patch.object(asyncio, "sleep", side_effect=asyncio.CancelledError) as sleep,
            pytest.raises(asyncio.CancelledError),
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        mock_client.call_with_async_di.assert_has_awaits([mock.call(mock_start), mock.call(mock_stop)])
        mock_execute.assert_not_called()
        get_running_loop.return_value.create_task.assert_not_called()
        sleep.assert_awaited_once_with(123.0)
        assert interval._task is None

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

    def test_stop(self):
        mock_task = mock.Mock()
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock_task

        interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None

    def test_stop_when_not_active(self):
        interval = tanjun.schedules.IntervalSchedule(mock.Mock(), 123)

        with pytest.raises(RuntimeError, match="Schedule is not running"):
            interval.stop()

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


def test_as_time_schedule():
    ...


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

        interval.stop()

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

        result = interval.copy()

        assert result is not interval
        assert result.callback is mock_callback

    def test_load_into_component(self):
        mock_component = mock.Mock(tanjun.Component)
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        interval.load_into_component(mock_component)

        mock_component.add_schedule.assert_called_once_with(interval)

    def test_load_into_component_when_not_loader(self):
        mock_component = mock.Mock(object)
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        interval.load_into_component(mock_component)

    def test_start_when_passed_event_loop(self):
        class StubSchedule(tanjun.schedules.TimeSchedule):
            ...

        mock_client = mock.Mock()
        mock_loop = mock.Mock()
        interval = StubSchedule(mock.AsyncMock())
        interval._loop = mock.Mock()

        interval.start(mock_client, loop=mock_loop)

        assert interval._task is mock_loop.create_task.return_value
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
            interval.stop()

    def test_stop(self):
        mock_task = mock.Mock()
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())
        interval._task = mock_task

        interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None

    def test_stop_when_not_running(self):
        interval = tanjun.schedules.TimeSchedule(mock.AsyncMock())

        with pytest.raises(RuntimeError, match="Schedule is not running"):
            interval.stop()

    # Note: these have to be at least a microsecond after the target time as
    # the unix event loop won't return the sleep until the target time has passed,
    # not just been reached.
    @pytest.mark.parametrize(
        ("kwargs", "start", "tick_fors", "sleep_for", "expected_dates"),
        [
            pytest.param(
                {},
                datetime.datetime(2011, 1, 4, 11, 57, 10),
                [datetime.timedelta(seconds=50, milliseconds=500, microseconds=1), datetime.timedelta(seconds=60)],
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
                [datetime.timedelta(seconds=55, milliseconds=500, microseconds=1), datetime.timedelta(seconds=60)],
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
                [
                    datetime.timedelta(days=34, seconds=6100, microseconds=500001),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=16000),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(days=6, seconds=66400),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=16000),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(days=83, seconds=66400),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=16000),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(days=6, seconds=66400),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=16000),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(seconds=1960),
                    datetime.timedelta(seconds=20),
                    datetime.timedelta(days=266, seconds=66400),
                    datetime.timedelta(seconds=1),
                ],
                datetime.timedelta(days=399, seconds=6101),
                [
                    datetime.datetime(2016, 4, 7, 12, 22, 10, 500001),
                    datetime.datetime(2016, 4, 7, 12, 22, 30, 500001),
                    datetime.datetime(2016, 4, 7, 12, 55, 10, 500001),
                    datetime.datetime(2016, 4, 7, 12, 55, 30, 500001),
                    datetime.datetime(2016, 4, 7, 17, 22, 10, 500001),
                    datetime.datetime(2016, 4, 7, 17, 22, 30, 500001),
                    datetime.datetime(2016, 4, 7, 17, 55, 10, 500001),
                    datetime.datetime(2016, 4, 7, 17, 55, 30, 500001),
                    datetime.datetime(2016, 4, 14, 12, 22, 10, 500001),
                    datetime.datetime(2016, 4, 14, 12, 22, 30, 500001),
                    datetime.datetime(2016, 4, 14, 12, 55, 10, 500001),
                    datetime.datetime(2016, 4, 14, 12, 55, 30, 500001),
                    datetime.datetime(2016, 4, 14, 17, 22, 10, 500001),
                    datetime.datetime(2016, 4, 14, 17, 22, 30, 500001),
                    datetime.datetime(2016, 4, 14, 17, 55, 10, 500001),
                    datetime.datetime(2016, 4, 14, 17, 55, 30, 500001),
                    datetime.datetime(2016, 7, 7, 12, 22, 10, 500001),
                    datetime.datetime(2016, 7, 7, 12, 22, 30, 500001),
                    datetime.datetime(2016, 7, 7, 12, 55, 10, 500001),
                    datetime.datetime(2016, 7, 7, 12, 55, 30, 500001),
                    datetime.datetime(2016, 7, 7, 17, 22, 10, 500001),
                    datetime.datetime(2016, 7, 7, 17, 22, 30, 500001),
                    datetime.datetime(2016, 7, 7, 17, 55, 10, 500001),
                    datetime.datetime(2016, 7, 7, 17, 55, 30, 500001),
                    datetime.datetime(2016, 7, 14, 12, 22, 10, 500001),
                    datetime.datetime(2016, 7, 14, 12, 22, 30, 500001),
                    datetime.datetime(2016, 7, 14, 12, 55, 10, 500001),
                    datetime.datetime(2016, 7, 14, 12, 55, 30, 500001),
                    datetime.datetime(2016, 7, 14, 17, 22, 10, 500001),
                    datetime.datetime(2016, 7, 14, 17, 22, 30, 500001),
                    datetime.datetime(2016, 7, 14, 17, 55, 10, 500001),
                    datetime.datetime(2016, 7, 14, 17, 55, 30, 500001),
                    datetime.datetime(2017, 4, 7, 12, 22, 10, 500001),
                ],
                id="all time fields specified",
            ),
            # pytest.param(id="all time fields specified weekly"),
            # pytest.param(id="specific months, days, hours and minutes"),
            # pytest.param(id="specific months, days, hours and minutes weekly"),
            # pytest.param(id="specific months, days, hours and seconds"),
            # pytest.param(id="specific months, days, hours and seconds weekly"),
            # pytest.param(id="specific months, days, minutes and seconds"),
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
    # @pytest.mark.timeout(_TIMEOUT)
    @pytest.mark.asyncio()
    async def test_run(
        self,
        kwargs: dict[str, typing.Any],
        start: datetime.datetime,
        tick_fors: list[datetime.timedelta],
        sleep_for: datetime.timedelta,
        expected_dates: typing.List[datetime.datetime],
    ):
        called_at: list[datetime.datetime] = []

        @_print_tb
        async def callback():
            called_at.append(datetime.datetime.now())
            clock.spawn_ticker()

        schedule = tanjun.schedules.TimeSchedule(callback, **kwargs)

        frozen_time: freezegun.api.FrozenDateTimeFactory
        with freezegun.freeze_time(start, tick=False) as frozen_time:
            clock = _ManualClock(frozen_time, tick_fors)

            schedule.start(alluka.Client())
            clock.spawn_ticker()
            await asyncio.sleep(sleep_for.total_seconds())
            schedule.stop()
            clock.stop_ticker()

        assert called_at == expected_dates
