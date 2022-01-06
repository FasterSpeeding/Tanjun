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

# pyright: reportPrivateUsage=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

import asyncio
import datetime
import types
import typing
from collections import abc as collections
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
    assert isinstance(result, tanjun.IntervalSchedule)


class TestIntervalSchedule:
    def test_callback_property(self):
        mock_callback = mock.Mock()
        interval = tanjun.IntervalSchedule(mock_callback, 123)

        assert interval.callback is mock_callback

    def test_is_alive(self):
        assert tanjun.IntervalSchedule(mock.Mock(), 34123).is_alive is False

    def test_is_alive_when_is_alive(self):
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock.Mock()

        assert interval.is_alive is True

    @pytest.mark.parametrize("interval", [datetime.timedelta(seconds=652134), 652134, 652134.0])
    def test_interval_property(self, interval: typing.Union[int, float, datetime.timedelta]):
        interval_ = tanjun.IntervalSchedule(mock.Mock(), interval)

        assert interval_.interval == datetime.timedelta(seconds=652134)

    def test_iteration_count_property(self):
        assert tanjun.IntervalSchedule(mock.Mock(), 123).iteration_count == 0

    @pytest.mark.asyncio()
    async def test___call___(self):
        mock_callback = mock.AsyncMock()
        interval = tanjun.IntervalSchedule(
            typing.cast(collections.Callable[..., collections.Awaitable[None]], mock_callback), 123
        )

        await interval(123, 543, sex="OK", boo="31123")

        mock_callback.assert_awaited_once_with(123, 543, sex="OK", boo="31123")

    def test_copy(self):
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        result = interval.copy()

        assert result.callback is interval.callback
        assert result.interval is interval.interval
        assert result.iteration_count is interval.iteration_count
        assert result is not interval

    def test_copy_when_schedule_is_active(self):
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock.Mock()

        with pytest.raises(RuntimeError, match="Cannot copy an active schedule"):
            interval.copy()

    def test_load_into_component(self):
        mock_component = mock.Mock(tanjun.Component)
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        interval.load_into_component(mock_component)

        mock_component.add_schedule.assert_called_once_with(interval)

    def test_load_into_component_when_no_add_schedule_method(self):
        mock_component = mock.Mock(object)
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        interval.load_into_component(mock_component)

    def test_set_start_callback(self):
        mock_callback = mock.Mock()
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        result = interval.set_start_callback(mock_callback)

        assert result is interval
        assert interval._start_callback
        assert interval._start_callback.callback is mock_callback

    def test_set_stop_callback(self):
        mock_callback = mock.Mock()
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        result = interval.set_stop_callback(mock_callback)

        assert result is interval
        assert interval._stop_callback
        assert interval._stop_callback.callback is mock_callback

    @pytest.mark.asyncio()
    async def test__wrap_callback(self):
        mock_client = mock.Mock()
        mock_callback = mock.AsyncMock()
        stop = mock.Mock()
        interval: tanjun.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"stop": stop}),
        )(mock.Mock(), 123)

        with mock.patch.object(tanjun.injecting, "BasicInjectionContext") as injection_context:
            await interval._wrap_callback(mock_client, mock_callback)

        mock_callback.resolve.assert_awaited_once_with(injection_context.return_value)
        stop.assert_not_called()

    @pytest.mark.asyncio()
    async def test__wrap_callback_when_fatal_exception(self):
        ...

    @pytest.mark.asyncio()
    async def test__wrap_callback_when_ignored_exception(self):
        ...

    @pytest.mark.asyncio()
    async def test__wrap_callback_when_exception(self):
        ...

    @pytest.mark.asyncio()
    async def test__loop(self):
        ...

    @pytest.mark.asyncio()
    async def test__loop_and_start_and_stop_callbacks_set(self):
        ...

    def test_start(self):
        mock_client = mock.Mock()
        loop_method = mock.Mock()
        interval: tanjun.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.IntervalSchedule[typing.Any],),
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
        interval: tanjun.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"_loop": loop_method}),
        )(mock.Mock(), 123)

        interval.start(mock_client, loop=mock_loop)

        assert interval._task is mock_loop.create_task.return_value
        mock_loop.create_task.assert_called_once_with(loop_method.return_value)

    def test_start_when_passed_event_loop_isnt_active(self):
        mock_loop = mock.Mock()
        mock_loop.is_running.return_value = False
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        with pytest.raises(RuntimeError, match="Event loop is not running"):
            interval.start(mock.Mock(), loop=mock_loop)

        assert interval._task is None

    def test_start_when_already_active(self):
        mock_task = mock.Mock()
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock_task

        with pytest.raises(RuntimeError, match="Cannot start an active schedule"):
            interval.start(mock.Mock())

        assert interval._task is mock_task

    def test_stop(self):
        mock_task = mock.Mock()
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)
        interval._task = mock_task

        interval.stop()

        mock_task.cancel.assert_called_once_with()
        assert interval._task is None

    def test_stop_when_not_active(self):
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        with pytest.raises(RuntimeError, match="Interval schedule is not running"):
            interval.stop()

    def test_with_start_callback(self):
        set_start_callback = mock.Mock()
        interval: tanjun.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"set_start_callback": set_start_callback}),
        )(mock.Mock(), 123)
        mock_callback = mock.Mock()

        result = interval.with_start_callback(mock_callback)

        assert result is mock_callback
        set_start_callback.assert_called_once_with(mock_callback)

    def test_with_stop_callback(self):
        set_stop_callback = mock.Mock()
        interval: tanjun.IntervalSchedule[typing.Any] = types.new_class(
            "StubIntervalSchedule",
            (tanjun.IntervalSchedule[typing.Any],),
            exec_body=lambda ns: ns.update({"set_stop_callback": set_stop_callback}),
        )(mock.Mock(), 123)
        mock_callback = mock.Mock()

        result = interval.with_stop_callback(mock_callback)

        assert result is mock_callback
        set_stop_callback.assert_called_once_with(mock_callback)

    def test_set_ignored_exceptions(self):
        mock_exception: typing.Any = mock.Mock()
        mock_other_exception: typing.Any = mock.Mock()
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        interval.set_ignored_exceptions(mock_exception, mock_other_exception)

        assert interval._ignored_exceptions == (mock_exception, mock_other_exception)

    def test_set_fatal_exceptions(self):
        mock_exception: typing.Any = mock.Mock()
        mock_other_exception: typing.Any = mock.Mock()
        interval = tanjun.IntervalSchedule(mock.Mock(), 123)

        interval.set_fatal_exceptions(mock_exception, mock_other_exception)

        assert interval._fatal_exceptions == (mock_exception, mock_other_exception)
