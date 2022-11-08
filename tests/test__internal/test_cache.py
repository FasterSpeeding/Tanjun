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
# This leads to too many false-positives around mocks.

from unittest import mock

import hikari
import pytest

import tanjun
from tanjun._internal import cache


@pytest.mark.asyncio()
async def test_get_perm_channel_when_hikari_cached_channel():
    mock_cache = mock.Mock()
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.return_value = None
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value = None
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(543123123))

    assert result is mock_cache.get_guild_channel.return_value
    mock_cache.get_guild_channel.assert_called_once_with(543123123)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_hikari_cached_channel_and_other_caches_not_implemented():
    mock_cache = mock.Mock()
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    client = tanjun.Client(mock_rest, cache=mock_cache)

    result = await cache.get_perm_channel(client, hikari.Snowflake(543123123))

    assert result is mock_cache.get_guild_channel.return_value
    mock_cache.get_guild_channel.assert_called_once_with(543123123)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_channel():
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.return_value = None
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value = None
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(34432134))

    assert result is mock_async_channel_cache.get.return_value
    mock_async_channel_cache.get.assert_called_once_with(34432134, default=None)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_channel_and_other_caches_not_implemented():
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_channel_cache = mock.AsyncMock()
    client = tanjun.Client(mock_rest).set_type_dependency(
        tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(34432134))

    assert result is mock_async_channel_cache.get.return_value
    mock_async_channel_cache.get.assert_called_once_with(34432134, default=None)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_channel():
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.return_value = None
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.PermissibleGuildChannel)
    mock_rest.fetch_channel.return_value.type = hikari.ChannelType.GUILD_TEXT
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.return_value = None
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value = None
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(543345543))

    assert result is mock_rest.fetch_channel.return_value
    mock_rest.fetch_channel.assert_awaited_once_with(543345543)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_channel_and_caches_not_implemented():
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.PermissibleGuildChannel)
    mock_rest.fetch_channel.return_value.type = hikari.ChannelType.GUILD_TEXT
    client = tanjun.Client(mock_rest)

    result = await cache.get_perm_channel(client, hikari.Snowflake(234321))

    assert result is mock_rest.fetch_channel.return_value
    mock_rest.fetch_channel.assert_awaited_once_with(234321)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_thread_and_hikari_cached_parent():
    mock_channel = mock.Mock()
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.side_effect = [None, mock_channel]
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.return_value = None
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value.parent_id = 56431234123
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(123312))

    assert result is mock_channel
    mock_async_thread_cache.get.assert_awaited_once_with(123312, default=None)
    mock_cache.get_guild_channel.assert_has_calls([mock.call(123312), mock.call(56431234123)])


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_thread_and_hikari_cached_parent_and_other_caches_not_implemented():
    mock_channel = mock.Mock()
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.side_effect = [None, mock_channel]
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value.parent_id = 56431234123
    client = tanjun.Client(mock_rest, cache=mock_cache).set_type_dependency(
        tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(123312))

    assert result is mock_channel
    mock_async_thread_cache.get.assert_awaited_once_with(123312, default=None)
    mock_cache.get_guild_channel.assert_has_calls([mock.call(123312), mock.call(56431234123)])


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_thread_and_async_cached_parent():
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.return_value = None
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value.parent_id = 7642342
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(5454323123))

    assert result is mock_async_channel_cache.get.return_value
    mock_async_thread_cache.get.assert_awaited_once_with(5454323123, default=None)
    mock_async_channel_cache.get.assert_awaited_once_with(7642342, default=None)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_thread_and_async_cached_parent_and_other_caches_not_implemented():
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = RuntimeError
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value.parent_id = 7642342
    client = (
        tanjun.Client(mock_rest)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(5454323123))

    assert result is mock_async_channel_cache.get.return_value
    mock_async_thread_cache.get.assert_awaited_once_with(5454323123, default=None)
    mock_async_channel_cache.get.assert_awaited_once_with(7642342, default=None)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_thread_and_rest_parent():
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.return_value = None
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.PermissibleGuildChannel)
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.return_value = None
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value.parent_id = 54312343412
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(12365456))

    assert result is mock_rest.fetch_channel.return_value
    mock_async_thread_cache.get.assert_awaited_once_with(12365456, default=None)
    mock_rest.fetch_channel.assert_awaited_once_with(54312343412)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_async_cached_thread_and_rest_parent_and_other_caches_not_implemented():
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.PermissibleGuildChannel)
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value.parent_id = 54312343412
    client = tanjun.Client(mock_rest).set_type_dependency(
        tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(12365456))

    assert result is mock_rest.fetch_channel.return_value
    mock_async_thread_cache.get.assert_awaited_once_with(12365456, default=None)
    mock_rest.fetch_channel.assert_awaited_once_with(54312343412)


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_thread_and_hikari_cached_parent():
    mock_channel = mock.Mock()
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.side_effect = [None, mock_channel]
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.GuildThreadChannel, parent_id=54654234)
    mock_rest.fetch_channel.return_value.type = hikari.ChannelType.GUILD_PUBLIC_THREAD
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.return_value = None
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value = None
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(12312312132))

    assert result is mock_channel
    mock_rest.fetch_channel.assert_awaited_once_with(12312312132)
    mock_cache.get_guild_channel.assert_has_calls([mock.call(12312312132), mock.call(54654234)])


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_thread_and_hikari_cached_parent_and_other_caches_not_implemented():
    mock_channel = mock.Mock()
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.side_effect = [None, mock_channel]
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.GuildThreadChannel, parent_id=54654234)
    mock_rest.fetch_channel.return_value.type = hikari.ChannelType.GUILD_PUBLIC_THREAD
    client = tanjun.Client(mock_rest, cache=mock_cache)

    result = await cache.get_perm_channel(client, hikari.Snowflake(12312312132))

    assert result is mock_channel
    mock_rest.fetch_channel.assert_awaited_once_with(12312312132)
    mock_cache.get_guild_channel.assert_has_calls([mock.call(12312312132), mock.call(54654234)])


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_thread_and_async_cached_parent():
    mock_channel = mock.Mock()
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.return_value = None
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.GuildThreadChannel, parent_id=76656345)
    mock_rest.fetch_channel.return_value.type = hikari.ChannelType.GUILD_PUBLIC_THREAD
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.side_effect = [None, mock_channel]
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value = None
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(4345345))

    assert result is mock_channel
    mock_rest.fetch_channel.assert_awaited_once_with(4345345)
    mock_async_channel_cache.get.assert_has_awaits(
        [mock.call(4345345, default=None), mock.call(76656345, default=None)]
    )


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_thread_and_async_cached_parent_and_other_caches_not_implemented():
    mock_channel = mock.Mock()
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.return_value = mock.Mock(hikari.GuildThreadChannel, parent_id=76656345)
    mock_rest.fetch_channel.return_value.type = hikari.ChannelType.GUILD_PUBLIC_THREAD
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.side_effect = [None, mock_channel]
    client = tanjun.Client(mock_rest).set_type_dependency(
        tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(4345345))

    assert result is mock_channel
    mock_rest.fetch_channel.assert_awaited_once_with(4345345)
    mock_async_channel_cache.get.assert_has_awaits(
        [mock.call(4345345, default=None), mock.call(76656345, default=None)]
    )


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_thread_and_rest_parent():
    mock_channel = mock.Mock(hikari.PermissibleGuildChannel)
    mock_thread = mock.Mock(hikari.GuildThreadChannel, parent_id=342234234)
    mock_thread.type = hikari.ChannelType.GUILD_PUBLIC_THREAD
    mock_cache = mock.Mock()
    mock_cache.get_guild_channel.return_value = None
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = [mock_thread, mock_channel]
    mock_async_channel_cache = mock.AsyncMock()
    mock_async_channel_cache.get.return_value = None
    mock_async_thread_cache = mock.AsyncMock()
    mock_async_thread_cache.get.return_value = None
    client = (
        tanjun.Client(mock_rest, cache=mock_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel], mock_async_channel_cache)
        .set_type_dependency(tanjun.dependencies.SfCache[hikari.GuildThreadChannel], mock_async_thread_cache)
    )

    result = await cache.get_perm_channel(client, hikari.Snowflake(4543123))

    assert result is mock_channel
    mock_rest.fetch_channel.assert_has_awaits([mock.call(4543123), mock.call(342234234)])


@pytest.mark.asyncio()
async def test_get_perm_channel_when_rest_thread_and_rest_parent_and_caches_not_implemented():
    mock_channel = mock.Mock(hikari.PermissibleGuildChannel)
    mock_thread = mock.Mock(hikari.GuildThreadChannel, parent_id=342234234)
    mock_thread.type = hikari.ChannelType.GUILD_PUBLIC_THREAD
    mock_rest = mock.AsyncMock()
    mock_rest.fetch_channel.side_effect = [mock_thread, mock_channel]
    client = tanjun.Client(mock_rest)

    result = await cache.get_perm_channel(client, hikari.Snowflake(4543123))

    assert result is mock_channel
    mock_rest.fetch_channel.assert_has_awaits([mock.call(4543123), mock.call(342234234)])
