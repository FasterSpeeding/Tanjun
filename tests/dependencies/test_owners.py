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
import datetime
import time
import typing
from unittest import mock

import hikari
import pytest

import tanjun


class TestOwnerCheck:
    @pytest.mark.parametrize("value", [0, -1.0, datetime.timedelta(seconds=-2)])
    def test_init_with_invalid_expire_after(self, value: typing.Union[int, float, datetime.timedelta]):
        with pytest.raises(ValueError, match="Expire after must be greater than 0 seconds"):
            tanjun.OwnerCheck(expire_after=-1)

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
