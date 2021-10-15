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
from unittest import mock

import hikari
import pytest

import tanjun


class TestOwnerCheck:
    @pytest.mark.asyncio()
    async def test_check_ownership_when_user_in_owner_ids(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()

        result = await check.check_ownership(mock_client, mock.Mock(id=7634))

        assert result is True
        mock_client.rest.fetch_application.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_not_falling_back_to_application(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634], fallback_to_application=False)
        mock_client = mock.Mock()

        result = await check.check_ownership(mock_client, mock.Mock(id=54123123))

        assert result is False
        mock_client.rest.fetch_application.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_token_type_is_not_bot(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()
        mock_client.rest.token_type = hikari.TokenType.BEARER

        result = await check.check_ownership(mock_client, mock.Mock(id=54123123))

        assert result is False
        mock_client.rest.fetch_application.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_application_owner(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()
        application = mock.Mock(owner=mock.Mock(id=654234), team=None)
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=654234))

        assert result is True
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_not_application_owner(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()
        application = mock.Mock(owner=mock.Mock(id=654234), team=None)
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=666663333696969))

        assert result is False
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_application_team_member(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()
        application = mock.Mock(
            owner=mock.Mock(id=654234), team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()})
        )
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=64123))

        assert result is True
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_not_team_member(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()
        application = mock.Mock(
            owner=mock.Mock(id=654234), team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()})
        )
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=654234))

        assert result is False
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_check_ownership_application_caching_behaviour(self):
        check = tanjun.dependencies.OwnerCheck(owners=[123, 7634])
        mock_client = mock.Mock()
        application = mock.Mock(
            owner=mock.Mock(id=654234), team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()})
        )
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        results = await asyncio.gather(*(check.check_ownership(mock_client, mock.Mock(id=64123)) for _ in range(0, 20)))

        assert all(result is True for result in results)
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_check_ownership_application_expires_cache(self):
        check = tanjun.dependencies.OwnerCheck(expire_after=datetime.timedelta(seconds=60))
        mock_client = mock.Mock()
        application_1 = mock.Mock(team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()}))
        application_2 = mock.Mock(team=mock.Mock(members={64123: mock.Mock()}))
        mock_client.rest.fetch_application = mock.AsyncMock(side_effect=[application_1, application_2])
        mock_client.rest.token_type = hikari.TokenType.BOT

        with mock.patch.object(time, "monotonic", side_effect=[123.123, 184.5123, 184.6969, 185.6969]):
            result = await check.check_ownership(mock_client, mock.Mock(id=64123))

            assert result is True
            mock_client.rest.fetch_application.assert_awaited_once_with()

            result = await check.check_ownership(mock_client, mock.Mock(id=54123))

            assert result is False
            mock_client.rest.fetch_application.assert_has_calls([mock.call(), mock.call()])


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


@pytest.mark.asyncio()
async def test_fetch_my_user_when_cached():
    mock_client = mock.Mock()

    result = await tanjun.dependencies.fetch_my_user(mock_client)

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
        await tanjun.dependencies.fetch_my_user(mock_client)

    mock_client.cache.get_me.assert_called_once_with()
    mock_client.rest.fetch_my_user.assert_not_called()


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cache_bound_falls_back_to_rest():
    mock_client = mock.Mock()
    mock_client.rest.token_type = hikari.TokenType.BOT
    mock_client.rest.fetch_my_user = mock.AsyncMock(return_value=mock.Mock())
    mock_client.cache = None

    result = await tanjun.dependencies.fetch_my_user(mock_client)

    assert result is mock_client.rest.fetch_my_user.return_value
    mock_client.rest.fetch_my_user.assert_called_once_with()


def test_set_standard_dependencies():
    mock_client = mock.Mock()
    mock_client.set_type_dependency.return_value = mock_client
    stack = contextlib.ExitStack()
    owner_check = stack.enter_context(mock.patch.object(tanjun.dependencies, "OwnerCheck"))
    lazy_constant = stack.enter_context(mock.patch.object(tanjun.dependencies, "LazyConstant"))

    with stack:
        tanjun.dependencies.set_standard_dependencies(mock_client)

    owner_check.assert_called_once_with()
    lazy_constant.assert_called_once_with(tanjun.dependencies.fetch_my_user)
    lazy_constant.__getitem__.assert_called_once_with(hikari.OwnUser)
    mock_client.set_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.AbstractOwnerCheck, owner_check.return_value),
            mock.call(lazy_constant.__getitem__.return_value, lazy_constant.return_value),
        ]
    )


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
