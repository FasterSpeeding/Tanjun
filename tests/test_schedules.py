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
import types
import typing
from unittest import mock

import pytest

import tanjun


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

    @pytest.mark.asyncio()
    async def test__loop(self):
        mock_client = mock.Mock()
        mock_client.get_callback_override.return_value = None
        mock_result_1 = mock.Mock()
        mock_result_2 = mock.Mock()
        mock_result_3 = mock.Mock()
        mock_result_4 = mock.Mock()
        mock_execute = mock.Mock(side_effect=[mock_result_1, mock_result_2, mock_result_3, mock_result_4, object()])
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_execute": mock_execute}),
        )(mock.Mock(), 123, ignored_exceptions=[LookupError])
        interval._task = mock.Mock()

        with (
            mock.patch.object(asyncio, "sleep", side_effect=[None, None, None, asyncio.CancelledError]) as sleep,
            pytest.raises(asyncio.CancelledError),
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        mock_execute.assert_has_calls([mock.call(mock_client), mock.call(mock_client), mock.call(mock_client)])
        get_running_loop.return_value.create_task.assert_has_calls(
            [mock.call(mock_result_1), mock.call(mock_result_2), mock.call(mock_result_3), mock.call(mock_result_4)]
        )
        sleep.assert_has_calls([mock.call(123.0), mock.call(123.0), mock.call(123.0), mock.call(123.0)])
        assert interval._task is None

    @pytest.mark.asyncio()
    async def test__loop_when_max_runs(self):
        mock_client = mock.Mock()
        mock_client.get_callback_override.return_value = None
        mock_result_1 = mock.Mock()
        mock_result_2 = mock.Mock()
        mock_result_3 = mock.Mock()
        mock_execute = mock.Mock(side_effect=[mock_result_1, mock_result_2, mock_result_3, object()])
        interval: tanjun.schedules.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.schedules.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_execute": mock_execute}),
        )(mock.Mock(), 123, ignored_exceptions=[LookupError], max_runs=3)
        interval._task = mock.Mock()

        with (
            mock.patch.object(asyncio, "sleep") as sleep,
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        mock_execute.assert_has_calls([mock.call(mock_client), mock.call(mock_client), mock.call(mock_client)])
        get_running_loop.return_value.create_task.assert_has_calls(
            [mock.call(mock_result_1), mock.call(mock_result_2), mock.call(mock_result_3)]
        )
        sleep.assert_has_calls([mock.call(123.0), mock.call(123.0), mock.call(123.0)])
        assert interval._task is None

    @pytest.mark.asyncio()
    async def test__loop_and_start_and_stop_callbacks_set(self):
        mock_client = mock.Mock()
        mock_client.get_callback_override.return_value = None
        mock_client.call_with_async_di = mock.AsyncMock()
        mock_start = mock.Mock()
        mock_stop = mock.Mock()
        mock_result_1 = mock.Mock()
        mock_result_2 = mock.Mock()
        mock_result_3 = mock.Mock()
        mock_execute = mock.Mock(side_effect=[mock_result_1, mock_result_2, mock_result_3])
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
            mock.patch.object(asyncio, "sleep", side_effect=[None, None, asyncio.CancelledError]) as sleep,
            pytest.raises(asyncio.CancelledError),
            mock.patch.object(asyncio, "get_running_loop") as get_running_loop,
        ):
            await interval._loop(mock_client)

        mock_execute.assert_has_calls([mock.call(mock_client), mock.call(mock_client), mock.call(mock_client)])
        mock_execute.assert_has_calls([mock.call(mock_client), mock.call(mock_client), mock.call(mock_client)])
        get_running_loop.return_value.create_task.assert_has_calls(
            [mock.call(mock_result_1), mock.call(mock_result_2), mock.call(mock_result_3)]
        )
        sleep.assert_has_calls([mock.call(123.0), mock.call(123.0), mock.call(123.0)])
        assert interval._task is None

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
        mock_execute.assert_called_once_with(mock_client)
        get_running_loop.return_value.create_task.assert_called_once_with(mock_execute.return_value)
        sleep.assert_awaited_once_with(123.0)
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
        mock_execute.assert_called_once_with(mock_client)
        get_running_loop.return_value.create_task.assert_called_once_with(mock_execute.return_value)
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
        mock_execute.assert_called_once_with(mock_client)
        get_running_loop.return_value.create_task.assert_called_once_with(mock_execute.return_value)
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
