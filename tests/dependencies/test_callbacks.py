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
from unittest import mock

import hikari
import pytest

import tanjun


@pytest.mark.asyncio()
async def test_fetch_my_user_when_cached():
    mock_client = mock.Mock()
    mock_cache = mock.AsyncMock()

    result = await tanjun.dependencies.fetch_my_user(mock_client, me_cache=mock_cache)

    assert result is mock_client.cache.get_me.return_value
    mock_client.cache.get_me.assert_called_once_with()
    mock_client.rest.fetch_my_user.assert_not_called()
    mock_cache.get.assert_not_called()


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cached_but_async_cache_returns():
    mock_client = mock.Mock()
    mock_client.cache.get_me.return_value = None
    mock_cache = mock.AsyncMock()

    result = await tanjun.dependencies.fetch_my_user(mock_client, me_cache=mock_cache)

    assert result is mock_cache.get.return_value
    mock_client.cache.get_me.assert_called_once_with()
    mock_client.rest.fetch_my_user.assert_not_called()
    mock_cache.get.assert_awaited_once_with(default=None)


@pytest.mark.asyncio()
async def test_fetch_my_user_when_no_cache_but_async_cache_returns():
    mock_client = mock.Mock()
    mock_client.cache = None
    mock_cache = mock.AsyncMock()

    result = await tanjun.dependencies.fetch_my_user(mock_client, me_cache=mock_cache)

    assert result is mock_cache.get.return_value
    mock_client.rest.fetch_my_user.assert_not_called()
    mock_cache.get.assert_awaited_once_with(default=None)


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cached_token_type_isnt_bot():
    mock_client = mock.Mock()
    mock_client.rest.token_type = hikari.TokenType.BEARER
    mock_client.cache.get_me.return_value = None

    with pytest.raises(
        RuntimeError, match="Cannot fetch current user with a REST client that's bound to a client credentials token"
    ):
        await tanjun.dependencies.fetch_my_user(mock_client, me_cache=None)

    mock_client.cache.get_me.assert_called_once_with()
    mock_client.rest.fetch_my_user.assert_not_called()


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cache_bound_and_async_cache_returns_none_falls_back_to_rest():
    mock_client = mock.Mock()
    mock_client.rest.token_type = hikari.TokenType.BOT
    mock_client.rest.fetch_my_user = mock.AsyncMock(return_value=mock.Mock())
    mock_cache = mock.AsyncMock()
    mock_cache.get.return_value = None
    mock_client.cache = None

    result = await tanjun.dependencies.fetch_my_user(mock_client, me_cache=mock_cache)

    assert result is mock_client.rest.fetch_my_user.return_value
    mock_client.rest.fetch_my_user.assert_called_once_with()
    mock_cache.get.assert_awaited_once_with(default=None)


@pytest.mark.asyncio()
async def test_fetch_my_user_when_not_cache_bound_and_not_async_cache_falls_back_to_rest():
    mock_client = mock.Mock()
    mock_client.rest.token_type = hikari.TokenType.BOT
    mock_client.rest.fetch_my_user = mock.AsyncMock(return_value=mock.Mock())
    mock_client.cache = None

    result = await tanjun.dependencies.fetch_my_user(mock_client, me_cache=None)

    assert result is mock_client.rest.fetch_my_user.return_value
    mock_client.rest.fetch_my_user.assert_called_once_with()
