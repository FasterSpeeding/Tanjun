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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.
import asyncio
import contextlib
import datetime
import time
import typing
from unittest import mock

import hikari
import pytest

import tanjun


class TestLazyConstant:
    def test_callback_property(self):
        mock_callback = mock.Mock()
        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as callback_descriptor:

            assert tanjun.LazyConstant(mock_callback).callback is callback_descriptor.return_value
            callback_descriptor.assert_called_once_with(mock_callback)

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
    stack = contextlib.ExitStack()
    inject = stack.enter_context(mock.patch.object(tanjun.injecting, "inject"))
    make_lc_resolver = stack.enter_context(mock.patch.object(tanjun.dependencies.data, "make_lc_resolver"))
    mock_type: type[typing.Any] = mock.Mock()

    with stack:
        result = tanjun.inject_lc(mock_type)

    assert result is inject.return_value
    inject.assert_called_once_with(callback=make_lc_resolver.return_value)
    make_lc_resolver.assert_called_once_with(mock_type)


@pytest.mark.asyncio()
async def test_fetch_my_user_when_cached():
    mock_client = mock.Mock()

    result = await tanjun.dependencies.data.fetch_my_user(mock_client)

    assert result is mock_client.cache.get_me.return_value
    mock_client.cache.get_me.assert_called_once_with()
    mock_client.rest.fetch_my_user.assert_not_called()


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cached_token_type_isnt_bot():
    mock_client = mock.Mock()
    mock_client.rest.token_type = hikari.TokenType.BEARER
    mock_client.cache.get_me.return_value = None

    with pytest.raises(
        RuntimeError, match="Cannot fetch current user with a REST client that's bound to a client credentials token"
    ):
        await tanjun.dependencies.data.fetch_my_user(mock_client)

    mock_client.cache.get_me.assert_called_once_with()
    mock_client.rest.fetch_my_user.assert_not_called()


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cache_bound_falls_back_to_rest():
    mock_client = mock.Mock()
    mock_client.rest.token_type = hikari.TokenType.BOT
    mock_client.rest.fetch_my_user = mock.AsyncMock(return_value=mock.Mock())
    mock_client.cache = None

    result = await tanjun.dependencies.data.fetch_my_user(mock_client)

    assert result is mock_client.rest.fetch_my_user.return_value
    mock_client.rest.fetch_my_user.assert_called_once_with()


@pytest.mark.asyncio()
async def test_cache_callback():
    mock_callback = mock.Mock()
    mock_context = mock.Mock()
    with mock.patch.object(
        tanjun.injecting, "CallbackDescriptor", return_value=mock.Mock(resolve=mock.AsyncMock())
    ) as callback_descriptor:
        cached_callback = tanjun.dependencies.cache_callback(mock_callback)

        callback_descriptor.assert_called_once_with(mock_callback)

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

    callback_descriptor.return_value.resolve.assert_awaited_once_with(mock_context, 1)
    assert len(results) == 6
    assert all(r is callback_descriptor.return_value.resolve.return_value for r in results)


@pytest.mark.asyncio()
async def test_cache_callback_when_expired():
    mock_callback = mock.Mock()
    mock_first_context = mock.Mock()
    mock_second_context = mock.Mock()
    mock_first_result = mock.Mock()
    mock_second_result = mock.Mock()
    with mock.patch.object(
        tanjun.injecting,
        "CallbackDescriptor",
        return_value=mock.Mock(resolve=mock.AsyncMock(side_effect=[mock_first_result, mock_second_result])),
    ) as callback_descriptor:
        cached_callback = tanjun.dependencies.cache_callback(mock_callback, expire_after=datetime.timedelta(seconds=4))

        callback_descriptor.assert_called_once_with(mock_callback)

    with mock.patch.object(time, "monotonic", return_value=123.111):
        first_result = await cached_callback(0, ctx=mock_first_context)

    with mock.patch.object(time, "monotonic", return_value=128.11):
        results = await asyncio.gather(
            *(
                cached_callback(1, ctx=mock_second_context),
                cached_callback(2, ctx=mock.Mock()),
                cached_callback(3, ctx=mock.Mock()),
                cached_callback(4, ctx=mock.Mock()),
                cached_callback(5, ctx=mock.Mock()),
                cached_callback(6, ctx=mock.Mock()),
            )
        )

    callback_descriptor.return_value.resolve.assert_has_awaits(
        [mock.call(mock_first_context, 0), mock.call(mock_second_context, 1)]
    )
    assert first_result is mock_first_result
    assert len(results) == 6
    assert all(r is mock_second_result for r in results)


@pytest.mark.asyncio()
async def test_cache_callback_when_not_expired():
    mock_callback = mock.Mock()
    mock_context = mock.Mock()
    with mock.patch.object(
        tanjun.injecting, "CallbackDescriptor", return_value=mock.Mock(resolve=mock.AsyncMock())
    ) as callback_descriptor:
        cached_callback = tanjun.dependencies.cache_callback(mock_callback, expire_after=datetime.timedelta(seconds=15))

        callback_descriptor.assert_called_once_with(mock_callback)

    with mock.patch.object(time, "monotonic", return_value=853.123):
        first_result = await cached_callback(0, ctx=mock_context)

    with mock.patch.object(time, "monotonic", return_value=866.123):
        results = await asyncio.gather(
            *(
                cached_callback(1, ctx=mock.Mock()),
                cached_callback(2, ctx=mock.Mock()),
                cached_callback(3, ctx=mock.Mock()),
                cached_callback(4, ctx=mock.Mock()),
                cached_callback(5, ctx=mock.Mock()),
                cached_callback(6, ctx=mock.Mock()),
            )
        )

    callback_descriptor.return_value.resolve.assert_awaited_once_with(mock_context, 0)
    assert first_result is callback_descriptor.return_value.resolve.return_value
    assert len(results) == 6
    assert all(r is callback_descriptor.return_value.resolve.return_value for r in results)


def test_cached_inject():
    stack = contextlib.ExitStack()
    inject = stack.enter_context(mock.patch.object(tanjun.injecting, "inject"))
    cache_callback = stack.enter_context(mock.patch.object(tanjun.dependencies.data, "cache_callback"))
    mock_callback = mock.Mock()

    with stack:
        result = tanjun.cached_inject(mock_callback, expire_after=datetime.timedelta(seconds=15))

    assert result is inject.return_value
    inject.assert_called_once_with(callback=cache_callback.return_value)
    cache_callback.assert_called_once_with(mock_callback, expire_after=datetime.timedelta(seconds=15))


def test_cached_inject_with_defaults():
    stack = contextlib.ExitStack()
    inject = stack.enter_context(mock.patch.object(tanjun.injecting, "inject"))
    cache_callback = stack.enter_context(mock.patch.object(tanjun.dependencies.data, "cache_callback"))
    mock_callback = mock.Mock()

    with stack:
        result = tanjun.cached_inject(mock_callback)

    assert result is inject.return_value
    inject.assert_called_once_with(callback=cache_callback.return_value)
    cache_callback.assert_called_once_with(mock_callback, expire_after=None)
