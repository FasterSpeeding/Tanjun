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
import hikari
import pytest

import tanjun


class TestOwners:
    @pytest.mark.parametrize("value", [0, -1.0, datetime.timedelta(seconds=-2)])
    def test_init_with_invalid_expire_after(self, value: typing.Union[int, float, datetime.timedelta]):
        with pytest.raises(ValueError, match="Expire after must be greater than 0 seconds"):
            tanjun.dependencies.Owners(expire_after=-1)

    @pytest.mark.asyncio()
    async def test_check_ownership_when_user_in_owner_ids(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED

        result = await check.check_ownership(mock_client, mock.Mock(id=7634))

        assert result is True
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_not_falling_back_to_application(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634], fallback_to_application=False)
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED

        result = await check.check_ownership(mock_client, mock.Mock(id=54123123))

        assert result is False
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_async_cache_and_application_owner(self):
        check = tanjun.dependencies.Owners(owners=[432, 1221])
        application = mock.Mock(owner=mock.Mock(id=4442322), team=None)
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value = application
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = mock_cache

        result = await check.check_ownership(mock_client, mock.Mock(id=4442322))

        assert result is True
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )
        mock_cache.get.assert_awaited_once_with(default=None)

    @pytest.mark.asyncio()
    async def test_check_ownership_when_async_cache_but_not_application_owner(self):
        check = tanjun.dependencies.Owners(owners=[234321123, 5432123])
        application = mock.Mock(owner=mock.Mock(id=12345322), team=None)
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value = application
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = mock_cache

        result = await check.check_ownership(mock_client, mock.Mock(id=234123321))

        assert result is False
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )
        mock_cache.get.assert_awaited_once_with(default=None)

    @pytest.mark.asyncio()
    async def test_check_ownership_when_when_async_cache_and_application_team_member(self):
        check = tanjun.dependencies.Owners(owners=[6543456, 345234])
        application = mock.Mock(
            owner=mock.Mock(id=65456234), team=mock.Mock(members={8656: mock.Mock(), 55555544444: mock.Mock()})
        )
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value = application
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = mock_cache

        result = await check.check_ownership(mock_client, mock.Mock(id=55555544444))

        assert result is True
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )
        mock_cache.get.assert_awaited_once_with(default=None)

    @pytest.mark.asyncio()
    async def test_check_ownership_when_async_cache_but_not_team_member(self):
        check = tanjun.dependencies.Owners(owners=[87456234123, 12365234])

        application = mock.Mock(
            owner=mock.Mock(id=322332232), team=mock.Mock(members={43123: mock.Mock(), 321145: mock.Mock()})
        )
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value = application
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = mock_cache

        result = await check.check_ownership(mock_client, mock.Mock(id=322332232))

        assert result is False
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )
        mock_cache.get.assert_awaited_once_with(default=None)

    @pytest.mark.asyncio()
    async def test_check_ownership_when_async_cache_returns_none_application_owner(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value = None
        application = mock.Mock(owner=mock.Mock(id=654234), team=None)
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = mock_cache
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=654234))

        assert result is True
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )
        mock_cache.get.assert_awaited_once_with(default=None)
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_check_ownership_when_token_type_is_not_bot(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        mock_client.rest.token_type = hikari.TokenType.BEARER

        result = await check.check_ownership(mock_client, mock.Mock(id=54123123))

        assert result is False
        mock_client.rest.fetch_application.assert_not_called()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )

    @pytest.mark.asyncio()
    async def test_check_ownership_when_application_owner(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        application = mock.Mock(owner=mock.Mock(id=654234), team=None)
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=654234))

        assert result is True
        mock_client.rest.fetch_application.assert_awaited_once_with()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )

    @pytest.mark.asyncio()
    async def test_check_ownership_when_not_application_owner(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        application = mock.Mock(owner=mock.Mock(id=654234), team=None)
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=666663333696969))

        assert result is False
        mock_client.rest.fetch_application.assert_awaited_once_with()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )

    @pytest.mark.asyncio()
    async def test_check_ownership_when_application_team_member(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        application = mock.Mock(
            owner=mock.Mock(id=654234), team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()})
        )
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=64123))

        assert result is True
        mock_client.rest.fetch_application.assert_awaited_once_with()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )

    @pytest.mark.asyncio()
    async def test_check_ownership_when_not_team_member(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        application = mock.Mock(
            owner=mock.Mock(id=654234), team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()})
        )
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        result = await check.check_ownership(mock_client, mock.Mock(id=654234))

        assert result is False
        mock_client.rest.fetch_application.assert_awaited_once_with()
        mock_client.get_type_dependency.assert_called_once_with(
            tanjun.dependencies.SingleStoreCache[hikari.Application]
        )

    @pytest.mark.asyncio()
    async def test_check_ownership_application_caching_behaviour(self):
        check = tanjun.dependencies.Owners(owners=[123, 7634])
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        application = mock.Mock(
            owner=mock.Mock(id=654234), team=mock.Mock(members={54123: mock.Mock(), 64123: mock.Mock()})
        )
        mock_client.rest.fetch_application = mock.AsyncMock(return_value=application)
        mock_client.rest.token_type = hikari.TokenType.BOT

        results = await asyncio.gather(*(check.check_ownership(mock_client, mock.Mock(id=64123)) for _ in range(0, 20)))

        assert all(result is True for result in results)
        mock_client.rest.fetch_application.assert_awaited_once_with()

    @pytest.mark.parametrize("expire_after", [datetime.timedelta(seconds=60), 60, 60.0])
    @pytest.mark.asyncio()
    async def test_check_ownership_application_expires_cache(
        self, expire_after: typing.Union[float, int, datetime.timedelta]
    ):
        check = tanjun.dependencies.Owners(expire_after=expire_after)
        mock_client = mock.Mock(tanjun.Client)
        mock_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
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
