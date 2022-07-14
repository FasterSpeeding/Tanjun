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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.
import asyncio
import datetime
import time
import typing
from unittest import mock

import alluka
import pytest

import tanjun


class TestLazyConstant:
    def test_callback_property(self):
        mock_callback = mock.Mock()

        assert tanjun.LazyConstant(mock_callback).callback is mock_callback

    def test_get_value(self):
        assert tanjun.LazyConstant(mock.Mock()).get_value() is None

    def test_reset(self):
        constant = tanjun.LazyConstant(mock.Mock()).set_value(mock.Mock())

        constant.reset()
        assert constant.get_value() is None

    def test_set_value(self):
        mock_value = mock.Mock()
        constant = tanjun.LazyConstant(mock.Mock())
        constant._lock = mock.Mock()

        result = constant.set_value(mock_value)

        assert result is constant
        assert constant.get_value() is mock_value
        assert constant._lock is None

    def test_set_value_when_value_already_set(self):
        mock_value = mock.Mock()
        constant = tanjun.LazyConstant(mock.Mock()).set_value(mock_value)
        constant._lock = mock.Mock()

        with pytest.raises(RuntimeError, match="Constant value already set."):
            constant.set_value(mock.Mock())

        assert constant.get_value() is mock_value

    @pytest.mark.asyncio()
    async def test_acquire(self):
        with mock.patch.object(asyncio, "Lock") as lock:
            constant = tanjun.LazyConstant(mock.Mock())
            lock.assert_not_called()

            result = constant.acquire()

            lock.assert_called_once_with()
            assert result is lock.return_value

            result = constant.acquire()
            lock.assert_called_once_with()
            assert result is lock.return_value


@pytest.mark.skip(reason="Not Implemented")
@pytest.mark.asyncio()
async def test_make_lc_resolver_when_already_cached():
    ...


@pytest.mark.skip(reason="Not Implemented")
@pytest.mark.asyncio()
async def test_make_lc_resolver():
    ...


def test_inject_lc():
    mock_type: typing.Any = mock.Mock()

    with (
        mock.patch.object(alluka, "inject") as inject,
        mock.patch.object(tanjun.dependencies.data, "make_lc_resolver") as make_lc_resolver,
    ):
        result = tanjun.inject_lc(mock_type)

    assert result is inject.return_value
    inject.assert_called_once_with(callback=make_lc_resolver.return_value)
    make_lc_resolver.assert_called_once_with(mock_type)


@pytest.mark.parametrize("expire_after", [0.0, -1, datetime.timedelta(seconds=-2)])
def test_cache_callback_when_invalid_expire_after(expire_after: typing.Union[float, int, datetime.timedelta]):
    with pytest.raises(ValueError, match="expire_after must be more than 0 seconds"):
        tanjun.dependencies.data.cache_callback(mock.Mock(), expire_after=expire_after)


@pytest.mark.asyncio()
async def test_cache_callback():
    mock_callback = mock.AsyncMock()
    mock_context = mock.AsyncMock()
    cached_callback = tanjun.dependencies.data.cache_callback(mock_callback)

    with mock.patch.object(time, "monotonic"):
        results = await asyncio.gather(
            *(
                cached_callback(1, ctx=mock_context),
                cached_callback(2, ctx=mock.Mock()),
                cached_callback(3, ctx=mock.Mock()),
                cached_callback(4, ctx=mock.Mock()),
                cached_callback(5, ctx=mock.Mock()),
                cached_callback(6, ctx=mock.Mock()),
            )
        )

    mock_context.call_with_async_di.assert_awaited_once_with(mock_callback, 1)
    assert all(r is mock_context.call_with_async_di.return_value for r in results)


@pytest.mark.parametrize("expire_after", [4, 4.0, datetime.timedelta(seconds=4)])
@pytest.mark.asyncio()
async def test_cache_callback_when_expired(expire_after: typing.Union[float, int, datetime.timedelta]):
    mock_callback = mock.AsyncMock()
    mock_first_context = mock.AsyncMock()
    mock_second_context = mock.AsyncMock()
    cached_callback = tanjun.dependencies.data.cache_callback(mock_callback, expire_after=expire_after)

    with mock.patch.object(time, "monotonic", return_value=123.111):
        first_result = await cached_callback(0, ctx=mock_first_context)

    with mock.patch.object(time, "monotonic", return_value=128.11):
        results = await asyncio.gather(
            *(
                cached_callback(1, ctx=mock_second_context),
                cached_callback(2, ctx=mock_second_context),
                cached_callback(3, ctx=mock_second_context),
                cached_callback(4, ctx=mock_second_context),
                cached_callback(5, ctx=mock_second_context),
                cached_callback(6, ctx=mock_second_context),
            )
        )

    mock_first_context.call_with_async_di.assert_awaited_once_with(mock_callback, 0)
    mock_second_context.call_with_async_di.assert_awaited_once_with(mock_callback, 1)
    assert first_result is mock_first_context.call_with_async_di.return_value
    assert all(r is mock_second_context.call_with_async_di.return_value for r in results)
    assert len(results) == 6


@pytest.mark.parametrize("expire_after", [15, 15.0, datetime.timedelta(seconds=15)])
@pytest.mark.asyncio()
async def test_cache_callback_when_not_expired(expire_after: typing.Union[float, int, datetime.timedelta]):
    mock_callback = mock.AsyncMock()
    mock_context = mock.AsyncMock()
    cached_callback = tanjun.dependencies.data.cache_callback(mock_callback, expire_after=expire_after)

    with mock.patch.object(time, "monotonic", return_value=853.123):
        first_result = await cached_callback(0, ctx=mock_context)

    with mock.patch.object(time, "monotonic", return_value=866.123):
        results = await asyncio.gather(
            *(
                cached_callback(1, ctx=mock_context),
                cached_callback(2, ctx=mock_context),
                cached_callback(3, ctx=mock_context),
                cached_callback(4, ctx=mock_context),
                cached_callback(5, ctx=mock_context),
                cached_callback(6, ctx=mock_context),
            )
        )

    mock_context.call_with_async_di.assert_awaited_once_with(mock_callback, 0)
    assert first_result is mock_context.call_with_async_di.return_value
    assert all(r is mock_context.call_with_async_di.return_value for r in results)
    assert len(results) == 6


def test_cached_inject():
    mock_callback = mock.Mock()

    with (
        mock.patch.object(alluka, "inject") as inject,
        mock.patch.object(tanjun.dependencies.data, "cache_callback") as cache_callback,
    ):
        result = tanjun.cached_inject(mock_callback, expire_after=datetime.timedelta(seconds=15))

    assert result is inject.return_value
    inject.assert_called_once_with(callback=cache_callback.return_value)
    cache_callback.assert_called_once_with(mock_callback, expire_after=datetime.timedelta(seconds=15))


def test_cached_inject_with_defaults():
    mock_callback = mock.Mock()

    with (
        mock.patch.object(alluka, "inject") as inject,
        mock.patch.object(tanjun.dependencies.data, "cache_callback") as cache_callback,
    ):
        result = tanjun.cached_inject(mock_callback)

    assert result is inject.return_value
    inject.assert_called_once_with(callback=cache_callback.return_value)
    cache_callback.assert_called_once_with(mock_callback, expire_after=None)
