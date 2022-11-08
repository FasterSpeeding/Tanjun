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
import typing
from unittest import mock

import alluka
import freezegun
import hikari
import pytest

import tanjun
from tanjun.context import base as base_context


@pytest.mark.parametrize(
    ("resource_type", "mock_ctx", "expected"),
    [
        (tanjun.BucketResource.USER, mock.Mock(author=mock.Mock(id=123321)), 123321),
        (tanjun.BucketResource.CHANNEL, mock.Mock(channel_id=43433123), 43433123),
        (tanjun.BucketResource.GUILD, mock.Mock(guild_id=65123), 65123),
        (tanjun.BucketResource.GUILD, mock.Mock(guild_id=None, channel_id=611223), 611223),
    ],
)
@pytest.mark.asyncio()
async def test__get_ctx_target(resource_type: tanjun.BucketResource, mock_ctx: tanjun.abc.Context, expected: int):
    assert await tanjun.dependencies.limiters._get_ctx_target(mock_ctx, resource_type) == expected


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_and_cache_result():
    mock_context = mock.Mock()
    mock_context.get_channel.return_value = mock.Mock(parent_id=5132, id=123321)

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == 5132
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_not_called()
    mock_context.get_type_dependency.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_and_cache_result_has_no_parent():
    mock_context = mock.Mock()
    mock_context.get_channel.return_value = mock.Mock(parent_id=None, id=6534234)

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == mock_context.guild_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_not_called()
    mock_context.get_type_dependency.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_when_async_channel_cache_returns():
    mock_channel_cache = mock.AsyncMock()
    mock_channel_cache.get.return_value = mock.Mock(parent_id=3421123, id=123321)
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.get_type_dependency.return_value = mock_channel_cache

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == 3421123
    mock_context.get_channel.assert_called_once_with()
    mock_channel_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)
    mock_context.fetch_channel.assert_not_called()
    mock_context.get_type_dependency.assert_called_once_with(
        tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]
    )


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_when_async_channel_cache_returns_has_no_parent():
    mock_channel_cache = mock.AsyncMock()
    mock_channel_cache.get.return_value = mock.Mock(parent_id=None, id=123)
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.get_type_dependency.return_value = mock_channel_cache

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == mock_context.guild_id
    mock_context.get_channel.assert_called_once_with()
    mock_channel_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)
    mock_context.fetch_channel.assert_not_called()
    mock_context.get_type_dependency.assert_called_once_with(
        tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]
    )


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_when_async_thread_cache_returns():
    mock_channel_cache = mock.AsyncMock()
    mock_channel_cache.get.return_value = None
    mock_thread_cache = mock.AsyncMock()
    mock_thread_cache.get.return_value = mock.Mock(parent_id=432453, id=123321)
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.get_type_dependency.side_effect = [mock_channel_cache, mock_thread_cache]

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == 432453
    mock_context.get_channel.assert_called_once_with()
    mock_channel_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)
    mock_thread_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)
    mock_context.fetch_channel.assert_not_called()
    mock_context.get_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]),
            mock.call(tanjun.dependencies.SfCache[hikari.GuildThreadChannel]),
        ]
    )


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_when_async_caches_returns_none_falls_back_to_rest():
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.fetch_channel = mock.AsyncMock(
        return_value=mock.Mock(hikari.GuildChannel, parent_id=4365123, id=123321)
    )
    mock_channel_cache = mock.AsyncMock()
    mock_channel_cache.get.return_value = None
    mock_thread_cache = mock.AsyncMock()
    mock_thread_cache.get.return_value = None
    mock_context.get_type_dependency.side_effect = [mock_channel_cache, mock_thread_cache]

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == 4365123
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_awaited_once()
    mock_context.get_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]),
            mock.call(tanjun.dependencies.SfCache[hikari.GuildThreadChannel]),
        ]
    )
    mock_channel_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)
    mock_thread_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_when_async_caches_returns_none_falls_back_to_rest_has_no_parent():
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.fetch_channel = mock.AsyncMock(return_value=mock.Mock(hikari.GuildChannel, parent_id=None, id=123))
    mock_channel_cache = mock.AsyncMock()
    mock_channel_cache.get.return_value = None
    mock_thread_cache = mock.AsyncMock()
    mock_thread_cache.get.return_value = None
    mock_context.get_type_dependency.side_effect = [mock_channel_cache, mock_thread_cache]

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == mock_context.guild_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_awaited_once()
    mock_context.get_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]),
            mock.call(tanjun.dependencies.SfCache[hikari.GuildThreadChannel]),
        ]
    )
    mock_channel_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)
    mock_thread_cache.get.assert_awaited_once_with(mock_context.channel_id, default=None)


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_and_no_async_caches_falls_back_to_rest():
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.fetch_channel = mock.AsyncMock(
        return_value=mock.Mock(hikari.GuildChannel, parent_id=1235234, id=123321)
    )
    mock_context.get_type_dependency.return_value = alluka.abc.UNDEFINED

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == 1235234
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_awaited_once()
    mock_context.get_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]),
            mock.call(tanjun.dependencies.SfCache[hikari.GuildThreadChannel]),
        ]
    )


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_and_no_async_caches_falls_back_to_rest_has_no_parent():
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.get_channel.return_value = None
    mock_context.fetch_channel = mock.AsyncMock(return_value=mock.Mock(hikari.GuildChannel, parent_id=None, id=123))
    mock_context.get_type_dependency.return_value = alluka.abc.UNDEFINED

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result == mock_context.guild_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_awaited_once()
    mock_context.get_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.SfCache[hikari.PermissibleGuildChannel]),
            mock.call(tanjun.dependencies.SfCache[hikari.GuildThreadChannel]),
        ]
    )


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_and_dm_bound():
    mock_context = mock.Mock(guild_id=None)

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result is mock_context.channel_id


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role():
    mock_roles = [
        mock.Mock(id=123321, position=555),
        mock.Mock(id=42123, position=56),
        mock.Mock(id=4234, position=333),
        mock.Mock(id=4354, position=0),
        mock.Mock(id=4123, position=11),
    ]
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.member.role_ids = [123, 312]
    mock_context.member.get_roles = mock.Mock(return_value=mock_roles)
    mock_context.member.fetch_roles = mock.AsyncMock()

    assert await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE) == 123321

    mock_context.member.get_roles.assert_called_once_with()
    mock_context.member.fetch_roles.assert_not_called()
    mock_context.get_type_dependency.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_and_async_cache():
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.member.role_ids = [674345, 123876, 7643, 9999999]
    mock_context.member.get_roles = mock.Mock(return_value=[])
    mock_cache = mock.AsyncMock()
    mock_cache.get.side_effect = [
        mock.Mock(position=42),
        mock.Mock(id=994949, position=7634),
        tanjun.dependencies.EntryNotFound,
        mock.Mock(position=23),
    ]
    mock_context.get_type_dependency.return_value = mock_cache

    assert await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE) == 994949

    mock_context.member.get_roles.assert_called_once_with()
    mock_context.member.fetch_roles.assert_not_called()
    mock_context.get_type_dependency.assert_called_once_with(tanjun.dependencies.SfCache[hikari.Role])
    mock_cache.get.assert_has_awaits([mock.call(674345), mock.call(123876), mock.call(7643), mock.call(9999999)])


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_falls_back_to_rest_when_async_cache_raises_cache_miss():
    mock_roles = [
        mock.Mock(id=123321, position=42),
        mock.Mock(id=123322, position=43),
        mock.Mock(id=431, position=6969),
        mock.Mock(id=111, position=0),
        mock.Mock(id=4123, position=6959),
    ]
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.member.role_ids = [123, 312, 654]
    mock_context.member.get_roles = mock.Mock(return_value=[])
    mock_context.member.fetch_roles = mock.AsyncMock(return_value=mock_roles)
    mock_cache = mock.AsyncMock()
    mock_cache.get.side_effect = [mock.Mock(), tanjun.dependencies.CacheMissError]
    mock_context.get_type_dependency.return_value = mock_cache

    assert await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE) == 431

    mock_context.member.get_roles.assert_called_once_with()
    mock_context.member.fetch_roles.assert_awaited_once_with()
    mock_context.get_type_dependency.assert_called_once_with(tanjun.dependencies.SfCache[hikari.Role])
    mock_cache.get.assert_has_awaits([mock.call(123), mock.call(312)])


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_falls_back_to_rest():
    mock_roles = [
        mock.Mock(id=123321, position=42),
        mock.Mock(id=123322, position=43),
        mock.Mock(id=431, position=6969),
        mock.Mock(id=111, position=0),
        mock.Mock(id=4123, position=6959),
    ]
    mock_context = mock.Mock(base_context.BaseContext)
    mock_context.member.role_ids = [123, 312]
    mock_context.member.get_roles = mock.Mock(return_value=[])
    mock_context.member.fetch_roles = mock.AsyncMock(return_value=mock_roles)
    mock_context.get_type_dependency.return_value = alluka.abc.UNDEFINED

    assert await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE) == 431

    mock_context.member.get_roles.assert_called_once_with()
    mock_context.member.fetch_roles.assert_awaited_once_with()
    mock_context.get_type_dependency.assert_called_once_with(tanjun.dependencies.SfCache[hikari.Role])


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_when_dm_bound():
    mock_context = mock.Mock(guild_id=None)

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE)

    assert result is mock_context.channel_id


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_when_no_member_in_guild():
    mock_context = mock.Mock(guild_id=654124, member=None)

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE)

    assert result == 654124
    mock_context.get_type_dependency.assert_not_called()


@pytest.mark.parametrize("role_ids", [[123321], []])
@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_when_no_roles_or_only_1_role(role_ids: list[int]):
    mock_context = mock.Mock(guild_id=123312)
    mock_context.member.role_ids = role_ids

    result = await tanjun.dependencies.limiters._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE)

    assert result == 123312
    mock_context.get_type_dependency.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_unexpected_type():
    with pytest.raises(ValueError, match="Unexpected type 1"):
        await tanjun.dependencies.limiters._get_ctx_target(mock.Mock(), tanjun.BucketResource.MEMBER)


class Test_Cooldown:
    def test_has_expired_property(self):
        with freezegun.freeze_time(auto_tick_seconds=3):
            cooldown = tanjun.dependencies.limiters._Cooldown(limit=1, reset_after=datetime.timedelta(seconds=60))

            assert cooldown.has_expired() is False

    def test_has_expired_property_when_has_expired(self):
        with freezegun.freeze_time(auto_tick_seconds=30):
            cooldown = tanjun.dependencies.limiters._Cooldown(
                limit=1, reset_after=datetime.timedelta(seconds=26, milliseconds=500)
            )

            assert cooldown.has_expired() is True

    def test_increment(self):
        with freezegun.freeze_time(datetime.datetime(2016, 3, 2, 12, 4, 5), auto_tick_seconds=5):
            cooldown = tanjun.dependencies.limiters._Cooldown(
                limit=5, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
            )
            cooldown.counter = 2

            cooldown.increment()

            assert cooldown.counter == 3
            assert cooldown.resets_at == datetime.datetime(2016, 3, 2, 12, 5, 14, 420000, tzinfo=datetime.timezone.utc)

    def test_increment_when_counter_is_0(self):
        with freezegun.freeze_time(datetime.datetime(2014, 1, 2, 12, 4, 5), auto_tick_seconds=1):
            cooldown = tanjun.dependencies.limiters._Cooldown(limit=5, reset_after=datetime.timedelta(seconds=69))

            cooldown.increment()

            assert cooldown.counter == 1
            assert cooldown.resets_at == datetime.datetime(2014, 1, 2, 12, 5, 15, tzinfo=datetime.timezone.utc)

    def test_increment_when_counter_is_at_limit(self):
        with freezegun.freeze_time(datetime.datetime(2014, 1, 2, 12, 4, 5), auto_tick_seconds=1):
            cooldown = tanjun.dependencies.limiters._Cooldown(limit=5, reset_after=datetime.timedelta(seconds=69))
            cooldown.counter = 5

            cooldown.increment()

            assert cooldown.counter == 5
            assert cooldown.resets_at == datetime.datetime(2014, 1, 2, 12, 5, 14, tzinfo=datetime.timezone.utc)

    def test_increment_when_passed_reset_after(self):
        with freezegun.freeze_time(datetime.datetime(2014, 1, 2, 12, 4, 5), auto_tick_seconds=2):
            cooldown = tanjun.dependencies.limiters._Cooldown(limit=5, reset_after=datetime.timedelta(seconds=2))
            cooldown.counter = 2

            cooldown.increment()

            assert cooldown.counter == 1
            assert cooldown.resets_at == datetime.datetime(2014, 1, 2, 12, 4, 9, tzinfo=datetime.timezone.utc)

    def test_increment_when_limit_is_negeative_1(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(limit=-1, reset_after=datetime.timedelta(seconds=-1))
        cooldown.resets_at = datetime.datetime(2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        cooldown.counter = 123

        result = cooldown.increment()

        assert result is cooldown
        assert cooldown.counter == 123
        assert cooldown.resets_at == datetime.datetime(2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)

    def test_must_wait_until(self):
        with freezegun.freeze_time(datetime.datetime(2014, 1, 2, 12, 4, 5), auto_tick_seconds=3):
            cooldown = tanjun.dependencies.limiters._Cooldown(
                reset_after=datetime.timedelta(seconds=10, milliseconds=5), limit=3
            )
            cooldown.counter = 3

            assert cooldown.must_wait_until() == datetime.datetime(
                2014, 1, 2, 12, 4, 15, 5000, tzinfo=datetime.timezone.utc
            )

    def test_must_wait_until_when_resource_limit_not_hit(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(reset_after=datetime.timedelta(seconds=2), limit=3)
        cooldown.counter = 2

        assert cooldown.must_wait_until() is None

    def test_must_wait_until_when_reset_after_reached(self):
        with freezegun.freeze_time(datetime.datetime(2014, 1, 5, 12, 4, 5), auto_tick_seconds=5):
            cooldown = tanjun.dependencies.limiters._Cooldown(reset_after=datetime.timedelta(seconds=5), limit=3)
            cooldown.counter = 3

            assert cooldown.must_wait_until() is None

    def test_must_wait_until_when_limit_is_negative_1(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(reset_after=datetime.timedelta(seconds=64), limit=-1)
        cooldown.counter = 55

        assert cooldown.must_wait_until() is None


class Test_FlatResource:
    @pytest.mark.asyncio()
    async def test_try_into_inner(self):
        mock_resource_maker = mock.Mock()
        mock_resource = mock.Mock()
        bucket = tanjun.dependencies.limiters._FlatResource(tanjun.BucketResource.USER, mock_resource_maker)
        bucket.mapping[hikari.Snowflake(321123)] = mock_resource
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(321123)

        result = await bucket.try_into_inner(mock_context)

        assert result is mock_resource
        mock_resource_maker.assert_not_called()
        assert bucket.mapping[hikari.Snowflake(321123)] is mock_resource

    @pytest.mark.asyncio()
    async def test_try_into_inner_when_resource_doesnt_exist(self):
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._FlatResource(tanjun.BucketResource.USER, mock_resource_maker)
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(123321)

        result = await bucket.try_into_inner(mock_context)

        assert result is None
        mock_resource_maker.assert_not_called()
        assert hikari.Snowflake(123321) not in bucket.mapping

    @pytest.mark.asyncio()
    async def test_into_inner(self):
        mock_resource_maker = mock.Mock()
        mock_resource = mock.Mock()
        bucket = tanjun.dependencies.limiters._FlatResource(tanjun.BucketResource.USER, mock_resource_maker)
        bucket.mapping[hikari.Snowflake(3333)] = mock_resource
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(3333)

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource
        mock_resource_maker.assert_not_called()
        assert bucket.mapping[hikari.Snowflake(3333)] is mock_resource

    @pytest.mark.asyncio()
    async def test_into_inner_creates_new_resource(self):
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._FlatResource(tanjun.BucketResource.USER, mock_resource_maker)
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(123)

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource_maker.return_value
        mock_resource_maker.assert_called_once_with()
        assert bucket.mapping[hikari.Snowflake(123)] is mock_resource_maker.return_value

    def test_cleanup(self):
        mock_cooldown_1 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_2 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_3 = mock.Mock(has_expired=mock.Mock(return_value=False))
        bucket = tanjun.dependencies.limiters._FlatResource(tanjun.BucketResource.USER, mock.Mock())
        bucket.mapping = {
            hikari.Snowflake(123312): mock_cooldown_1,
            hikari.Snowflake(4321123): mock.Mock(has_expired=mock.Mock(return_value=True)),
            hikari.Snowflake(54123): mock_cooldown_2,
            hikari.Snowflake(222): mock.Mock(has_expired=mock.Mock(return_value=True)),
            hikari.Snowflake(654124): mock_cooldown_3,
            hikari.Snowflake(123321): mock.Mock(has_expired=mock.Mock(return_value=True)),
        }

        bucket.cleanup()

        assert bucket.mapping == {
            hikari.Snowflake(123312): mock_cooldown_1,
            hikari.Snowflake(54123): mock_cooldown_2,
            hikari.Snowflake(654124): mock_cooldown_3,
        }

    def test_copy(self):
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._FlatResource(tanjun.BucketResource.PARENT_CHANNEL, mock_resource_maker)
        bucket.mapping[hikari.Snowflake(321123)] = mock.Mock()

        new_bucket = bucket.copy()

        assert new_bucket is not bucket
        assert new_bucket.resource is bucket.resource
        assert new_bucket.make_resource is mock_resource_maker
        assert new_bucket.mapping == {}


class Test_MemberResource:
    @pytest.mark.asyncio()
    async def test_into_inner(self) -> None:
        mock_resource_maker = mock.Mock()
        mock_resource = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.mapping[hikari.Snowflake(654123)] = {hikari.Snowflake(3333): mock_resource}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(654123))
        mock_context.author.id = hikari.Snowflake(3333)

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource
        mock_resource_maker.assert_not_called()
        assert bucket.mapping[hikari.Snowflake(654123)] == {hikari.Snowflake(3333): mock_resource}

    @pytest.mark.asyncio()
    async def test_into_inner_when_member_not_found(self) -> None:
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.mapping[hikari.Snowflake(65234234)] = {hikari.Snowflake(123321): mock.Mock()}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(65234234))
        mock_context.author.id = hikari.Snowflake(123542)

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource_maker.return_value
        mock_resource_maker.assert_called_once_with()
        assert bucket.mapping[hikari.Snowflake(65234234)][hikari.Snowflake(123542)] is mock_resource_maker.return_value

    @pytest.mark.asyncio()
    async def test_into_inner_when_guild_not_found(self) -> None:
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        mock_context = mock.Mock(guild_id=hikari.Snowflake(123123))
        mock_context.author.id = hikari.Snowflake(32212)

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource_maker.return_value
        mock_resource_maker.assert_called_once_with()
        assert bucket.mapping[hikari.Snowflake(123123)] == {hikari.Snowflake(32212): mock_resource_maker.return_value}

    @pytest.mark.asyncio()
    async def test_into_inner_when_dm_bound(self) -> None:
        mock_resource_maker = mock.Mock()
        mock_resource = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.dm_fallback[hikari.Snowflake(1233214)] = mock_resource
        mock_context = mock.Mock(guild_id=None, channel_id=hikari.Snowflake(1233214))

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource
        mock_resource_maker.assert_not_called()
        assert bucket.dm_fallback[hikari.Snowflake(1233214)] is mock_resource

    @pytest.mark.asyncio()
    async def test_into_inner_when_dm_bound_and_user_not_found(self) -> None:
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        mock_context = mock.Mock(guild_id=None, channel_id=hikari.Snowflake(123312))

        result = await bucket.into_inner(mock_context)

        assert result is mock_resource_maker.return_value
        mock_resource_maker.assert_called_once_with()
        assert bucket.dm_fallback[hikari.Snowflake(123312)] is mock_resource_maker.return_value

    @pytest.mark.asyncio()
    async def test_try_into_inner(self) -> None:
        mock_resource_maker = mock.Mock()
        mock_resource = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.mapping[hikari.Snowflake(222222)] = {hikari.Snowflake(666666): mock_resource}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(222222))
        mock_context.author.id = hikari.Snowflake(666666)

        result = await bucket.try_into_inner(mock_context)

        assert result is mock_resource
        mock_resource_maker.assert_not_called()
        assert bucket.mapping[hikari.Snowflake(222222)] == {hikari.Snowflake(666666): mock_resource}

    @pytest.mark.asyncio()
    async def test_try_into_inner_when_member_not_found(self) -> None:
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.mapping[hikari.Snowflake(652134)] = {hikari.Snowflake(123321): mock.Mock()}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(652134))
        mock_context.author.id = hikari.Snowflake(43213)

        result = await bucket.try_into_inner(mock_context)

        assert result is None
        mock_resource_maker.assert_not_called()
        assert hikari.Snowflake(43213) not in bucket.mapping[hikari.Snowflake(652134)]

    @pytest.mark.asyncio()
    async def test_try_into_inner_when_guild_not_found(self) -> None:
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        mock_context = mock.Mock(guild_id=hikari.Snowflake(4234))
        mock_context.author.id = hikari.Snowflake(123321)

        result = await bucket.try_into_inner(mock_context)

        assert result is None
        mock_resource_maker.assert_not_called()
        assert hikari.Snowflake(4234) not in bucket.mapping

    @pytest.mark.asyncio()
    async def test_try_into_inner_when_dm_bound(self) -> None:
        mock_resource_maker = mock.Mock()
        mock_resource = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.dm_fallback[hikari.Snowflake(76345)] = mock_resource
        mock_context = mock.Mock(guild_id=None, channel_id=hikari.Snowflake(76345))

        result = await bucket.try_into_inner(mock_context)

        assert result is mock_resource
        mock_resource_maker.assert_not_called()
        assert bucket.dm_fallback[hikari.Snowflake(76345)] is mock_resource

    @pytest.mark.asyncio()
    async def test_try_into_inner_when_dm_bound_and_user_not_found(self) -> None:
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        mock_context = mock.Mock(guild_id=None, channel_id=hikari.Snowflake(555555))

        result = await bucket.try_into_inner(mock_context)

        assert result is None
        mock_resource_maker.assert_not_called()
        assert hikari.Snowflake(555555) not in bucket.dm_fallback

    def test_cleanup(self):
        mock_cooldown_1 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_2 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_3 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_dm_cooldown_1 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_dm_cooldown_2 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_dm_cooldown_3 = mock.Mock(has_expired=mock.Mock(return_value=False))
        bucket = tanjun.dependencies.limiters._MemberResource(mock.Mock())
        bucket.mapping = {
            hikari.Snowflake(54123): {
                hikari.Snowflake(123312): mock_cooldown_1,
                hikari.Snowflake(4321123): mock.Mock(has_expired=mock.Mock(return_value=True)),
                hikari.Snowflake(54123): mock_cooldown_2,
            },
            hikari.Snowflake(666): {
                hikari.Snowflake(4321123): mock.Mock(has_expired=mock.Mock(return_value=True)),
            },
            hikari.Snowflake(6512312): {
                hikari.Snowflake(222): mock.Mock(has_expired=mock.Mock(return_value=True)),
                hikari.Snowflake(654124): mock_cooldown_3,
                hikari.Snowflake(123321): mock.Mock(has_expired=mock.Mock(return_value=True)),
            },
        }
        bucket.dm_fallback = {
            hikari.Snowflake(231123): mock.Mock(has_expired=mock.Mock(return_value=True)),
            hikari.Snowflake(696969): mock_dm_cooldown_1,
            hikari.Snowflake(3214312): mock.Mock(has_expired=mock.Mock(return_value=True)),
            hikari.Snowflake(969696): mock_dm_cooldown_2,
            hikari.Snowflake(123321123): mock.Mock(has_expired=mock.Mock(return_value=True)),
            hikari.Snowflake(42069): mock_dm_cooldown_3,
        }

        bucket.cleanup()

        assert bucket.mapping == {
            hikari.Snowflake(54123): {
                hikari.Snowflake(123312): mock_cooldown_1,
                hikari.Snowflake(54123): mock_cooldown_2,
            },
            hikari.Snowflake(6512312): {hikari.Snowflake(654124): mock_cooldown_3},
        }
        assert bucket.dm_fallback == {
            hikari.Snowflake(696969): mock_dm_cooldown_1,
            hikari.Snowflake(969696): mock_dm_cooldown_2,
            hikari.Snowflake(42069): mock_dm_cooldown_3,
        }

    def test_copy(self):
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._MemberResource(mock_resource_maker)
        bucket.mapping[hikari.Snowflake(321123)] = mock.Mock()
        bucket.dm_fallback[hikari.Snowflake(541123)] = mock.Mock()

        new_bucket = bucket.copy()

        assert new_bucket is not bucket
        assert new_bucket.make_resource is mock_resource_maker
        assert new_bucket.mapping == {}
        assert new_bucket.dm_fallback == {}


class Test_GlobalResource:
    @pytest.mark.asyncio()
    async def test_into_inner(self):
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._GlobalResource(mock_resource_maker)

        assert await bucket.into_inner(mock.Mock()) is mock_resource_maker.return_value
        assert await bucket.into_inner(mock.Mock()) is mock_resource_maker.return_value
        mock_resource_maker.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_try_into_inner(self):
        mock_resource_maker = mock.Mock()
        bucket = tanjun.dependencies.limiters._GlobalResource(mock_resource_maker)

        assert await bucket.try_into_inner(mock.Mock()) is mock_resource_maker.return_value
        assert await bucket.try_into_inner(mock.Mock()) is mock_resource_maker.return_value
        mock_resource_maker.assert_called_once_with()

    def test_cleanup(self):
        tanjun.dependencies.limiters._GlobalResource(mock.Mock()).cleanup()

    def test_copy(self):
        mock_resource_1 = mock.Mock()
        mock_resource_2 = mock.Mock()
        mock_resource_maker = mock.Mock(side_effect=[mock_resource_1, mock_resource_2])
        bucket = tanjun.dependencies.limiters._GlobalResource(mock_resource_maker)
        bucket.bucket.increment()

        new_bucket = bucket.copy()

        assert new_bucket is not bucket
        assert new_bucket.make_resource is mock_resource_maker
        assert new_bucket.bucket is mock_resource_2
        assert new_bucket.make_resource is mock_resource_maker
        mock_resource_maker.assert_has_calls([mock.call(), mock.call()])

        assert bucket.bucket is mock_resource_1


class TestInMemoryCooldownManager:
    @pytest.mark.asyncio()
    async def test__gc(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_bucket_1 = mock.Mock()
        mock_bucket_2 = mock.Mock()
        mock_bucket_3 = mock.Mock()
        manager._buckets = {"e": mock_bucket_1, "a": mock_bucket_2, "f": mock_bucket_3}
        mock_error = Exception("test")

        with mock.patch.object(asyncio, "sleep", side_effect=[None, None, mock_error]) as sleep:
            with pytest.raises(Exception) as exc_info:  # noqa: PT011, PT012
                await asyncio.wait_for(manager._gc(), timeout=0.5)

                assert exc_info.value is mock_error
                sleep.assert_has_awaits([mock.call(10), mock.call(10), mock.call(10)])

        mock_bucket_1.cleanup.assert_has_calls([mock.call(), mock.call()])
        mock_bucket_2.cleanup.assert_has_calls([mock.call(), mock.call()])
        mock_bucket_3.cleanup.assert_has_calls([mock.call(), mock.call()])

    def test_add_to_client(self):
        mock_client = mock.Mock(tanjun.Client, is_alive=False)
        mock_open = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryCooldownManager):
            open = mock_open

        manager = StubManager()
        manager.add_to_client(mock_client)

        mock_client.add_client_callback.assert_has_calls(
            [
                mock.call(tanjun.abc.ClientCallbackNames.STARTING, manager.open),
                mock.call(tanjun.abc.ClientCallbackNames.CLOSING, manager.close),
            ]
        )
        mock_open.assert_not_called()

    def test_add_to_client_when_client_is_active(self):
        mock_client = mock.Mock(tanjun.Client, is_alive=True)
        mock_open = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryCooldownManager):
            open = mock_open

        manager = StubManager()
        manager.add_to_client(mock_client)

        mock_client.add_client_callback.assert_has_calls(
            [
                mock.call(tanjun.abc.ClientCallbackNames.STARTING, manager.open),
                mock.call(tanjun.abc.ClientCallbackNames.CLOSING, manager.close),
            ]
        )
        mock_open.assert_called_once_with(_loop=mock_client.loop)

    @pytest.mark.asyncio()
    async def test_check_cooldown(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock(try_into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.try_into_inner.return_value
        manager._buckets["ok"] = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=False)

        assert result is mock_bucket.try_into_inner.return_value.must_wait_until.return_value
        mock_bucket.try_into_inner.assert_awaited_once_with(mock_context)
        mock_inner.must_wait_until.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_try_into_inner_returns_none(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock(try_into_inner=mock.AsyncMock(return_value=None))
        manager._buckets["ok"] = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=False)

        assert result is None
        mock_bucket.try_into_inner.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_increment(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.increment.return_value = mock_bucket.into_inner.return_value
        mock_inner.must_wait_until.return_value = None
        manager._buckets["ok"] = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=True)

        assert result is None
        mock_bucket.into_inner.assert_awaited_once_with(mock_context)
        mock_inner.increment.assert_called_once_with()
        mock_inner.must_wait_until.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_increment_and_must_wait_until_returns_time(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.increment.return_value = mock_inner
        manager._buckets["ok"] = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=True)

        assert result is mock_inner.must_wait_until.return_value
        mock_bucket.into_inner.assert_awaited_once_with(mock_context)
        mock_inner.increment.assert_not_called()
        mock_inner.must_wait_until.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_falls_back_to_default_when_increment_creates_new_bucket(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock()
        mock_bucket.copy.return_value = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.copy.return_value.into_inner.return_value
        mock_inner.increment.return_value = mock_inner
        mock_inner.must_wait_until.return_value = None

        manager._default_bucket_template = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=True)

        assert result is None
        assert manager._buckets["ok"] is mock_bucket.copy.return_value
        mock_bucket.copy.assert_called_once_with()
        mock_bucket.copy.return_value.into_inner.assert_awaited_once_with(mock_context)
        mock_inner.increment.assert_called_once_with()
        mock_inner.must_wait_until.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_falls_back_to_default_when_increment_creates_new_bucket_when_wait_until_returns_time(
        self,
    ):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock()
        mock_bucket.copy.return_value = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.copy.return_value.into_inner.return_value
        mock_inner.increment.return_value = mock_inner

        manager._default_bucket_template = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=True)

        assert result is mock_inner.must_wait_until.return_value
        assert manager._buckets["ok"] is mock_bucket.copy.return_value
        mock_bucket.copy.assert_called_once_with()
        mock_bucket.copy.return_value.into_inner.assert_awaited_once_with(mock_context)
        mock_inner.increment.assert_not_called()
        mock_inner.must_wait_until.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_increment_cooldown(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        manager._buckets["catgirl neko"] = mock_bucket

        result = await manager.increment_cooldown("catgirl neko", mock_context)

        assert result is None
        mock_bucket.into_inner.assert_awaited_once_with(mock_context)
        mock_inner.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_increment_cooldown_falls_back_to_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock()
        mock_bucket.copy.return_value.into_inner = mock.AsyncMock(return_value=mock.Mock())
        mock_inner = mock_bucket.copy.return_value.into_inner.return_value
        manager._default_bucket_template = mock_bucket

        result = await manager.increment_cooldown("69", mock_context)

        assert result is None
        assert manager._buckets["69"] is mock_bucket.copy.return_value
        mock_bucket.copy.assert_called_once_with()
        mock_bucket.copy.return_value.into_inner.assert_awaited_once_with(mock_context)
        mock_inner.increment.assert_called_once_with()

    def test_close(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_gc_task = mock.Mock()
        manager._gc_task = mock_gc_task

        manager.close()

        mock_gc_task.cancel.assert_called_once_with()

    def test_close_when_not_active(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with pytest.raises(RuntimeError, match="Cooldown manager is not active"):
            manager.close()

    def test_open(self):
        mock_gc = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryCooldownManager):
            _gc = mock_gc

        manager = StubManager()

        with mock.patch.object(asyncio, "get_running_loop") as get_running_loop:
            manager.open()

            assert manager._gc_task is get_running_loop.return_value.create_task.return_value
            get_running_loop.assert_called_once_with()
            get_running_loop.return_value.create_task.assert_called_once_with(mock_gc.return_value)
            mock_gc.assert_called_once_with()

    def test_open_with_passed_through_loop(self):
        mock_gc = mock.Mock()
        mock_loop = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryCooldownManager):
            _gc = mock_gc

        manager = StubManager()

        manager.open(_loop=mock_loop)

        assert manager._gc_task is mock_loop.create_task.return_value
        mock_loop.create_task.assert_called_once_with(mock_gc.return_value)
        mock_gc.assert_called_once_with()

    def test_open_when_already_active(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._gc_task = mock.Mock()

        with pytest.raises(RuntimeError, match="Cooldown manager is already running"):
            manager.open()

    def test_disable_bucket(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        default_bucket = manager._default_bucket_template

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.disable_bucket("kitten")

            assert result is manager
            assert manager._buckets["kitten"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is default_bucket
            cooldown_bucket.return_value.copy.assert_not_called()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == -1
            assert cooldown.reset_after == datetime.timedelta(-1)

    def test_disable_bucket_when_is_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.disable_bucket("default")

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is cooldown_bucket.return_value.copy.return_value
            cooldown_bucket.return_value.copy.assert_called_once_with()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == -1
            assert cooldown.reset_after == datetime.timedelta(-1)

    @pytest.mark.parametrize(
        "resource_type",
        [
            tanjun.BucketResource.USER,
            tanjun.BucketResource.CHANNEL,
            tanjun.BucketResource.PARENT_CHANNEL,
            tanjun.BucketResource.TOP_ROLE,
            tanjun.BucketResource.GUILD,
        ],
    )
    def test_set_bucket(self, resource_type: tanjun.BucketResource):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        default_bucket = manager._default_bucket_template

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("gay catgirl", resource_type, 123, 43.123)

            assert result is manager
            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is default_bucket
            cooldown_bucket.return_value.copy.assert_not_called()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 2
            assert len(cooldown_bucket.call_args.kwargs) == 0
            assert cooldown_bucket.call_args.args[0] is resource_type

            cooldown_maker = cooldown_bucket.call_args.args[1]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == 123
            assert cooldown.reset_after == datetime.timedelta(seconds=43, milliseconds=123)

    @pytest.mark.parametrize("reset_after", [datetime.timedelta(seconds=69), 69, 69.0])
    def test_set_bucket_handles_different_reset_after_types(
        self, reset_after: typing.Union[datetime.timedelta, int, float]
    ):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("gay catgirl", tanjun.BucketResource.USER, 444, reset_after)

            assert result is manager
            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 2
            assert len(cooldown_bucket.call_args.kwargs) == 0
            assert cooldown_bucket.call_args.args[0] is tanjun.BucketResource.USER

            cooldown_maker = cooldown_bucket.call_args.args[1]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == 444
            assert cooldown.reset_after == datetime.timedelta(seconds=69)

    def test_set_bucket_for_member_resource(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies.limiters, "_MemberResource") as cooldown_bucket:
            result = manager.set_bucket("meowth", tanjun.BucketResource.MEMBER, 64, 42.0)

            assert result is manager
            assert manager._buckets["meowth"] is cooldown_bucket.return_value
            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == 64
            assert cooldown.reset_after == datetime.timedelta(seconds=42.0)

    def test_set_bucket_for_global_resource(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.set_bucket("meow", tanjun.BucketResource.GLOBAL, 420, 69.420)

            assert result is manager
            assert manager._buckets["meow"] is cooldown_bucket.return_value
            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == 420
            assert cooldown.reset_after == datetime.timedelta(seconds=69, milliseconds=420)

    def test_set_bucket_when_is_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("default", tanjun.BucketResource.USER, 777, 666.0)

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is cooldown_bucket.return_value.copy.return_value
            cooldown_bucket.return_value.copy.assert_called_once_with()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 2
            assert len(cooldown_bucket.call_args.kwargs) == 0
            assert cooldown_bucket.call_args.args[0] is tanjun.BucketResource.USER

            cooldown_maker = cooldown_bucket.call_args.args[1]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._Cooldown)
            assert cooldown.limit == 777
            assert cooldown.reset_after == datetime.timedelta(seconds=666)

    @pytest.mark.parametrize("reset_after", [datetime.timedelta(seconds=-42), -431, -0.123])
    def test_set_bucket_when_reset_after_is_negative(self, reset_after: typing.Union[datetime.timedelta, float, int]):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with pytest.raises(ValueError, match="reset_after must be greater than 0 seconds"):
            manager.set_bucket("gay catgirl", tanjun.BucketResource.USER, 123, reset_after)

    def test_set_bucket_when_limit_is_negative(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with pytest.raises(ValueError, match="limit must be greater than 0"):
            manager.set_bucket("gay catgirl", tanjun.BucketResource.USER, -123, 43.123)


class TestCooldownPreExecution:
    @pytest.mark.asyncio()
    async def test_call(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "yuri catgirls", owners_exempt=False, error=mock.Mock()
        )
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = None
        mock_owner_check = mock.AsyncMock()

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("yuri catgirls", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri catgirls", owners_exempt=True, error=mock.Mock())
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = True

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_not_called()
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_but_owner_check_is_none(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri catgirls", owners_exempt=True, error=mock.Mock())
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = None

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=None)

        mock_cooldown_manager.check_cooldown.assert_called_once_with("yuri catgirls", mock_context, increment=True)
        assert pre_execution._owners_exempt is False

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_and_not_owner(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls", owners_exempt=True, error=mock.Mock())
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = None
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_until(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2012, 1, 14, 12, 1, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(
            tanjun.CommandError, match="This command is currently in cooldown. Try again <t:1326542469:R>."
        ):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_until_and_error_callback(self):
        class MockException(Exception):
            ...

        mock_error_callback = mock.Mock(return_value=MockException())
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True, error=mock_error_callback)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2012, 1, 14, 12, 1, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(MockException):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)
        mock_error_callback.assert_called_once_with(
            "yuri", datetime.datetime(2012, 1, 14, 12, 1, 9, 420000, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.asyncio()
    async def test_call_when_wait_until(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls yuri", owners_exempt=False)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(
            tanjun.CommandError, match="This command is currently in cooldown. Try again <t:1452946089:R>."
        ):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_localised(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet",
                hikari.Locale.FR: "eep",
                hikari.Locale.ES_ES: "i am {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.ES_ES
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="i am <t:1452946089:R> meow"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_localised_but_not_app_command_defaults(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.FR: "eep",
                "default": "meow meow {cooldown} nyaa",
                hikari.Locale.ES_ES: "i am {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="meow meow <t:1452946089:R> nyaa"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_localised_defaults(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.IT: "epic {cooldown} stones",
                hikari.Locale.FR: "meow meow {cooldown} nyaa",
                hikari.Locale.ES_ES: "i am {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.HR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="epic <t:1452946089:R> stones"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_with_until_localised_by_localiser(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet",
                hikari.Locale.FR: "eep",
                hikari.Locale.ES_ES: "i am {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.FR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown",
            {hikari.Locale.BG: "yeep", hikari.Locale.FR: "i am {cooldown} nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match="i am <t:1452946089:R> nyaa"):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_localised_but_localiser_not_found(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet",
                hikari.Locale.FR: "eep",
                hikari.Locale.ES_ES: "meow {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.ES_ES
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown",
            {hikari.Locale.BG: "yeep", hikari.Locale.FR: "i am {cooldown} nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match="meow <t:1452946089:R> meow"):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_defaults_with_localiser(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet",
                hikari.Locale.FR: "eep",
                "default": "echo echo {cooldown} foxtrot",
                hikari.Locale.ES_ES: "meow {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.PT_BR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown",
            {hikari.Locale.BG: "yeep", hikari.Locale.FR: "i am {cooldown} nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match="echo echo <t:1452946089:R> foxtrot"):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_and_error_callback(self):
        class MockException(Exception):
            ...

        mock_error_callback = mock.Mock(return_value=MockException())
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri", owners_exempt=False, error=mock_error_callback
        )
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = datetime.datetime(
            2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(MockException):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()
        mock_error_callback.assert_called_once_with(
            "catgirls yuri", datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )


def test_with_cooldown():
    mock_command = mock.Mock()
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution:
        tanjun.with_cooldown(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)

    mock_command.wrapped_command.hooks.add_pre_execution.assert_not_called()
    mock_command.wrapped_command.set_hooks.assert_not_called()


def test_with_cooldown_when_no_set_hooks():
    mock_command = mock.Mock(hooks=None)
    mock_error_callback = mock.Mock()

    with (
        mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution,
        mock.patch.object(tanjun.hooks, "AnyHooks") as any_hooks,
    ):
        tanjun.with_cooldown(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.set_hooks.assert_called_once_with(any_hooks.return_value)
        any_hooks.return_value.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
        any_hooks.assert_called_once_with()

    mock_command.wrapped_command.hooks.add_pre_execution.assert_not_called()
    mock_command.wrapped_command.set_hooks.assert_not_called()


def test_with_cooldown_when_follow_wrapping():
    mock_command = mock.Mock()
    mock_command.wrapped_command.hooks = None
    mock_command.wrapped_command.wrapped_command.hooks = None
    mock_command.wrapped_command.wrapped_command.wrapped_command.wrapped_command = None
    mock_hooks_1 = mock.Mock()
    mock_hooks_2 = mock.Mock()
    mock_error_callback = mock.Mock()

    with (
        mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution,
        mock.patch.object(tanjun.hooks, "AnyHooks", side_effect=[mock_hooks_1, mock_hooks_2]) as any_hooks,
    ):
        tanjun.with_cooldown(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

    any_hooks.assert_has_calls([mock.call(), mock.call()])
    mock_hooks_1.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
    mock_hooks_2.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
    mock_pre_execution.assert_called_once_with(
        "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
    )
    mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
    mock_command.wrapped_command.set_hooks.assert_called_once_with(mock_hooks_1)
    mock_command.wrapped_command.wrapped_command.set_hooks.assert_called_once_with(mock_hooks_2)
    mock_command.wrapped_command.wrapped_command.wrapped_command.hooks.add_pre_execution.assert_called_once_with(
        mock_pre_execution.return_value
    )


def test_with_cooldown_when_follow_wrapping_and_not_wrapping():
    mock_command = mock.Mock(wrapped_command=None)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution:
        tanjun.with_cooldown(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)


def test_with_cooldown_when_follow_wrapping_and_unsupported_command():
    mock_command = mock.Mock(tanjun.abc.SlashCommand)
    mock_error_callback = mock.Mock()
    with pytest.raises(AttributeError):
        mock_command.wrapped_command

    with mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution:
        tanjun.with_cooldown(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)


def test_with_cooldown_when_follow_wrapping_and_wrapping_unsupported_command():
    mock_command = mock.Mock(wrapped_command=mock.Mock(tanjun.abc.SlashCommand))
    mock_error_callback = mock.Mock()
    with pytest.raises(AttributeError):
        mock_command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution:
        tanjun.with_cooldown(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error=mock_error_callback, error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
        mock_command.wrapped_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)


class Test_ConcurrencyLimit:
    def test_acquire(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)

        result = limit.acquire()

        assert result is True
        assert limit.counter == 1

    def test_acquire_when_couldnt_acquire(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)
        limit.counter = 2

        result = limit.acquire()

        assert result is False
        assert limit.counter == 2

    def test_acquire_when_limit_is_negative_1(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(-1)
        limit.counter = 2

        result = limit.acquire()

        assert result is True
        assert limit.counter == 2

    def test_release(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)
        limit.counter = 2

        limit.release()

        assert limit.counter == 1

    def test_release_when_not_acquired(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)

        with pytest.raises(RuntimeError, match="Cannot release a limit that has not been acquired"):
            limit.release()

    def test_release_when_limit_is_negative_1(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(-1)
        limit.counter = 0

        limit.release()

        assert limit.counter == 0

    def test_has_expired(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)
        limit.counter = 1

        assert limit.has_expired() is False

    def test_has_expired_when_has_expired(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)
        limit.counter = 0

        assert limit.has_expired() is True


class TestInMemoryConcurrencyLimiter:
    @pytest.mark.asyncio()
    async def test__gc(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        mock_bucket_1 = mock.Mock()
        mock_bucket_2 = mock.Mock()
        mock_bucket_3 = mock.Mock()
        manager._buckets = {"e": mock_bucket_1, "a": mock_bucket_2, "f": mock_bucket_3}
        mock_error = Exception("test")

        with mock.patch.object(asyncio, "sleep", side_effect=[None, None, mock_error]) as sleep:
            with pytest.raises(Exception) as exc_info:  # noqa: PT011, PT012
                await asyncio.wait_for(manager._gc(), timeout=0.5)

                assert exc_info.value is mock_error
                sleep.assert_has_awaits([mock.call(10), mock.call(10), mock.call(10)])

        mock_bucket_1.cleanup.assert_has_calls([mock.call(), mock.call()])
        mock_bucket_2.cleanup.assert_has_calls([mock.call(), mock.call()])
        mock_bucket_3.cleanup.assert_has_calls([mock.call(), mock.call()])

    def test_add_to_client(self):
        mock_client = mock.Mock(tanjun.Client, is_alive=False)
        mock_open = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryConcurrencyLimiter):
            open = mock_open

        manager = StubManager()
        manager.add_to_client(mock_client)

        mock_client.add_client_callback.assert_has_calls(
            [
                mock.call(tanjun.abc.ClientCallbackNames.STARTING, manager.open),
                mock.call(tanjun.abc.ClientCallbackNames.CLOSING, manager.close),
            ]
        )
        mock_open.assert_not_called()

    def test_add_to_client_when_client_is_active(self):
        mock_client = mock.Mock(tanjun.Client, is_alive=True)
        mock_open = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryConcurrencyLimiter):
            open = mock_open

        manager = StubManager()
        manager.add_to_client(mock_client)

        mock_client.add_client_callback.assert_has_calls(
            [
                mock.call(tanjun.abc.ClientCallbackNames.STARTING, manager.open),
                mock.call(tanjun.abc.ClientCallbackNames.CLOSING, manager.close),
            ]
        )
        mock_open.assert_called_once_with(_loop=mock_client.loop)

    def test_close(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        mock_gc_task = mock.Mock()
        manager._gc_task = mock_gc_task

        manager.close()

        mock_gc_task.cancel.assert_called_once_with()

    def test_close_when_not_active(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()

        with pytest.raises(RuntimeError, match="Concurrency manager is not active"):
            manager.close()

    def test_open(self):
        mock_gc = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryConcurrencyLimiter):
            _gc = mock_gc

        manager = StubManager()

        with mock.patch.object(asyncio, "get_running_loop") as get_running_loop:
            manager.open()

            assert manager._gc_task is get_running_loop.return_value.create_task.return_value
            get_running_loop.assert_called_once_with()
            get_running_loop.return_value.create_task.assert_called_once_with(mock_gc.return_value)
            mock_gc.assert_called_once_with()

    def test_open_with_passed_through_loop(self):
        mock_gc = mock.Mock()
        mock_loop = mock.Mock()

        class StubManager(tanjun.dependencies.InMemoryConcurrencyLimiter):
            _gc = mock_gc

        manager = StubManager()

        manager.open(_loop=mock_loop)

        assert manager._gc_task is mock_loop.create_task.return_value
        mock_loop.create_task.assert_called_once_with(mock_gc.return_value)
        mock_gc.assert_called_once_with()

    def test_open_when_already_active(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        manager._gc_task = mock.Mock()

        with pytest.raises(RuntimeError, match="Concurrency manager is already running"):
            manager.open()

    @pytest.mark.asyncio()
    async def test_try_acquire(self):
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.acquire.return_value = True
        mock_context = mock.Mock()
        manager = tanjun.InMemoryConcurrencyLimiter()
        manager._buckets["aye"] = mock_bucket

        result = await manager.try_acquire("aye", mock_context)

        assert result is True
        mock_bucket.into_inner.assert_called_once_with(mock_context)
        mock_inner.acquire.assert_called_once_with()
        assert manager._acquiring_ctxs[("aye", mock_context)] is mock_inner

    @pytest.mark.asyncio()
    async def test_try_acquire_when_failed_to_acquire(self):
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.acquire.return_value = False
        mock_context = mock.Mock()
        manager = tanjun.InMemoryConcurrencyLimiter()
        manager._buckets["nya"] = mock_bucket

        result = await manager.try_acquire("nya", mock_context)

        assert result is False
        mock_bucket.into_inner.assert_called_once_with(mock_context)
        mock_inner.acquire.assert_called_once_with()
        assert ("nya", mock_context) not in manager._acquiring_ctxs

    @pytest.mark.asyncio()
    async def test_try_acquire_for_already_acquired_context(self):
        mock_bucket = mock.Mock()
        mock_context = mock.Mock()
        mock_limiter = mock.Mock()
        manager = tanjun.InMemoryConcurrencyLimiter()
        manager._buckets["ayee"] = mock_bucket
        manager._acquiring_ctxs[("ayee", mock_context)] = mock_limiter

        result = await manager.try_acquire("ayee", mock_context)

        assert result is True
        mock_bucket.into_inner.assert_not_called()
        mock_limiter.acquire.assert_not_called()
        assert manager._acquiring_ctxs[("ayee", mock_context)] is mock_limiter

    @pytest.mark.asyncio()
    async def test_try_acquire_falls_back_to_default_bucket(self):
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.acquire.return_value = True
        mock_bucket_template = mock.Mock()
        mock_bucket_template.copy.return_value = mock_bucket
        mock_context = mock.Mock()
        manager = tanjun.InMemoryConcurrencyLimiter()
        manager._default_bucket_template = mock_bucket_template

        result = await manager.try_acquire("yeet", mock_context)

        assert result is True
        mock_bucket_template.copy.assert_called_once_with()
        mock_bucket.into_inner.assert_called_once_with(mock_context)
        mock_inner.acquire.assert_called_once_with()
        assert manager._acquiring_ctxs[("yeet", mock_context)] is mock_inner
        assert manager._buckets["yeet"] is mock_bucket

    @pytest.mark.asyncio()
    async def test_release(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        mock_context = mock.Mock()
        mock_limiter = mock.Mock()
        manager._acquiring_ctxs[("nya", mock_context)] = mock_limiter

        await manager.release("nya", mock_context)

        assert ("nya", mock_context) not in manager._acquiring_ctxs
        mock_limiter.release.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_release_for_unknown_context(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        mock_context = mock.Mock()

        await manager.release("meow", mock_context)

    def test_disable_bucket(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        default_bucket = manager._default_bucket_template

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.disable_bucket("kitty cat")

            assert result is manager
            assert manager._buckets["kitty cat"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is default_bucket
            cooldown_bucket.return_value.copy.assert_not_called()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._ConcurrencyLimit)
            assert cooldown.limit == -1

    def test_disable_bucket_when_is_default(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.disable_bucket("default")

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is cooldown_bucket.return_value.copy.return_value
            cooldown_bucket.return_value.copy.assert_called_once_with()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._ConcurrencyLimit)
            assert cooldown.limit == -1

    @pytest.mark.parametrize(
        "resource_type",
        [
            tanjun.BucketResource.USER,
            tanjun.BucketResource.CHANNEL,
            tanjun.BucketResource.PARENT_CHANNEL,
            tanjun.BucketResource.TOP_ROLE,
            tanjun.BucketResource.GUILD,
        ],
    )
    def test_set_bucket(self, resource_type: tanjun.BucketResource):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        default_bucket = manager._default_bucket_template

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("gay catgirl", resource_type, 321)

            assert result is manager
            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is default_bucket
            cooldown_bucket.return_value.copy.assert_not_called()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 2
            assert len(cooldown_bucket.call_args.kwargs) == 0
            assert cooldown_bucket.call_args.args[0] is resource_type

            cooldown_maker = cooldown_bucket.call_args.args[1]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._ConcurrencyLimit)
            assert cooldown.limit == 321

    def test_set_bucket_for_member_resource(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()

        with mock.patch.object(tanjun.dependencies.limiters, "_MemberResource") as cooldown_bucket:
            result = manager.set_bucket("meowth", tanjun.BucketResource.MEMBER, 69)

            assert result is manager
            assert manager._buckets["meowth"] is cooldown_bucket.return_value
            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._ConcurrencyLimit)
            assert cooldown.limit == 69

    def test_set_bucket_for_global_resource(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.set_bucket("meow", tanjun.BucketResource.GLOBAL, 42069)

            assert result is manager
            assert manager._buckets["meow"] is cooldown_bucket.return_value
            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 1
            assert len(cooldown_bucket.call_args.kwargs) == 0

            cooldown_maker = cooldown_bucket.call_args.args[0]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._ConcurrencyLimit)
            assert cooldown.limit == 42069

    def test_set_bucket_when_is_default(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("default", tanjun.BucketResource.USER, 697)

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is cooldown_bucket.return_value.copy.return_value
            cooldown_bucket.return_value.copy.assert_called_once_with()

            assert cooldown_bucket.call_count == 1
            assert len(cooldown_bucket.call_args.args) == 2
            assert len(cooldown_bucket.call_args.kwargs) == 0
            assert cooldown_bucket.call_args.args[0] is tanjun.BucketResource.USER

            cooldown_maker = cooldown_bucket.call_args.args[1]
            cooldown = cooldown_maker()
            assert isinstance(cooldown, tanjun.dependencies.limiters._ConcurrencyLimit)
            assert cooldown.limit == 697

    def test_set_bucket_when_limit_is_negative(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()

        with pytest.raises(ValueError, match="limit must be greater than 0"):
            manager.set_bucket("gay catgirl", tanjun.BucketResource.USER, -1)


class TestConcurrencyPreExecution:
    @pytest.mark.asyncio()
    async def test_call(self):
        mock_context = mock.Mock()
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = True
        hook = tanjun.dependencies.ConcurrencyPreExecution("bucket boobs", error=KeyError)

        await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket boobs", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails(self):
        mock_context = mock.Mock()
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        hook = tanjun.dependencies.ConcurrencyPreExecution("bucket catgirls", error_message="an error message")

        with pytest.raises(tanjun.CommandError, match="an error message"):
            await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_localised(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="yeetus beatus")
        mock_context.interaction.locale = hikari.Locale.HU
        mock_context.type = hikari.CommandType.MESSAGE
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        hook = tanjun.dependencies.ConcurrencyPreExecution(
            "bucket catgirls",
            error_message={
                hikari.Locale.DA: "an error message",
                hikari.Locale.EN_GB: "owowowo",
                hikari.Locale.HU: "meow nyaa",
            },
        )

        with pytest.raises(tanjun.CommandError, match="meow nyaa"):
            await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_localised_but_not_app_command_defaults(self):
        mock_context = mock.Mock(tanjun.abc.Context, triggering_name="yeetus beatus")
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        hook = tanjun.dependencies.ConcurrencyPreExecution(
            "bucket catgirls",
            error_message={
                hikari.Locale.DA: "egg egg egg",
                "default": "i am the egg",
                hikari.Locale.EN_GB: "owowowo",
                hikari.Locale.HU: "meow nyaa",
            },
        )

        with pytest.raises(tanjun.CommandError, match="i am the egg"):
            await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_localised_defaults(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="yeetus beatus")
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.type = hikari.CommandType.MESSAGE
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        hook = tanjun.dependencies.ConcurrencyPreExecution(
            "bucket catgirls",
            error_message={
                hikari.Locale.DA: "an error message",
                "default": "definitely not a default",
                hikari.Locale.HU: "meow nyaa",
            },
        )

        with pytest.raises(tanjun.CommandError, match="definitely not a default"):
            await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_localised_by_localiser(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="epic flintstones")
        mock_context.interaction.locale = hikari.Locale.DA
        mock_context.type = hikari.CommandType.MESSAGE
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:epic flintstones:check:tanjun.concurrency",
            {
                hikari.Locale.DA: "multiple messages",
                hikari.Locale.EN_GB: "ear",
                hikari.Locale.BG: "neat",
            },
        )
        hook = tanjun.dependencies.ConcurrencyPreExecution(
            "bucket catgirls",
            error_message={
                hikari.Locale.DA: "meow meow",
                hikari.Locale.BG: "definitely not a default",
                hikari.Locale.HU: "meow nyaa",
            },
        )

        with pytest.raises(tanjun.CommandError, match="multiple messages"):
            await hook(mock_context, mock_limiter, localiser=localiser)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_localised_but_localiser_not_found(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="epic flintstones")
        mock_context.interaction.locale = hikari.Locale.EN_GB
        mock_context.type = hikari.CommandType.MESSAGE
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:epic flintstones:check:tanjun.concurrency",
            {hikari.Locale.EN_GB: "ear", hikari.Locale.BG: "neat", hikari.Locale.DA: "meow meow"},
        )
        hook = tanjun.dependencies.ConcurrencyPreExecution(
            "bucket catgirls",
            error_message={
                hikari.Locale.DA: "multiple messages",
                hikari.Locale.BG: "definitely not a default",
                hikari.Locale.HU: "meow nyaa",
            },
        )

        with pytest.raises(tanjun.CommandError, match="ear"):
            await hook(mock_context, mock_limiter, localiser=localiser)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_defaults_with_localiser(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="epic flintstones")
        mock_context.interaction.locale = hikari.Locale.JA
        mock_context.type = hikari.CommandType.MESSAGE
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:epic flintstones:check:tanjun.concurrency",
            {hikari.Locale.EN_GB: "ear", hikari.Locale.BG: "neat", hikari.Locale.DA: "meow meow"},
        )
        hook = tanjun.dependencies.ConcurrencyPreExecution(
            "bucket catgirls",
            error_message={
                hikari.Locale.DA: "multiple messages",
                "default": "deeper meaning than i am",
                hikari.Locale.BG: "definitely not a default",
                hikari.Locale.HU: "meow nyaa",
            },
        )

        with pytest.raises(tanjun.CommandError, match="deeper meaning than i am"):
            await hook(mock_context, mock_limiter, localiser=localiser)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails_and_error_callback(self):
        class MockException(Exception):
            ...

        mock_concurrency_callback = mock.Mock(return_value=MockException())

        mock_context = mock.Mock()
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.return_value = False
        hook = tanjun.dependencies.ConcurrencyPreExecution("bucket catgirls", error=mock_concurrency_callback)

        with pytest.raises(MockException):
            await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket catgirls", mock_context)
        mock_concurrency_callback.assert_called_once_with("bucket catgirls")


class TestConcurrencyPostExecution:
    @pytest.mark.asyncio()
    async def test_call(self):
        mock_context = mock.Mock()
        mock_limiter = mock.AsyncMock()
        hook = tanjun.dependencies.ConcurrencyPostExecution("aye bucket")

        await hook(mock_context, mock_limiter)

        mock_limiter.release.assert_awaited_once_with("aye bucket", mock_context)


def test_with_concurrency_limit():
    mock_command = mock.Mock()
    mock_command.hooks.add_pre_execution.return_value = mock_command.hooks
    mock_command.hooks.add_post_execution.return_value = mock_command.hooks
    mock_error_callback = mock.Mock()

    with (
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPreExecution") as pre_execution,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPostExecution") as post_execution,
    ):
        result = tanjun.with_concurrency_limit("bucket me", error=mock_error_callback, error_message="aye message")(
            mock_command
        )

    assert result is mock_command
    mock_command.hooks.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_command.hooks.add_post_execution.assert_called_once_with(post_execution.return_value)
    pre_execution.assert_called_once_with("bucket me", error=mock_error_callback, error_message="aye message")
    post_execution.assert_called_once_with("bucket me")
    mock_command.wrapped_command.hooks.add_pre_execution.assert_not_called()
    mock_command.wrapped_command.hooks.add_post_execution.assert_not_called()
    mock_command.wrapped_command.set_hooks.assert_not_called()


def test_with_concurrency_limit_makes_new_hooks():
    mock_command = mock.Mock(hooks=None)
    mock_error_callback = mock.Mock()

    with (
        mock.patch.object(tanjun.hooks, "AnyHooks") as any_hooks,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPreExecution") as pre_execution,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPostExecution") as post_execution,
    ):
        any_hooks.return_value.add_pre_execution.return_value = any_hooks.return_value
        any_hooks.return_value.add_post_execution.return_value = any_hooks.return_value

        result = tanjun.with_concurrency_limit("bucket me", error=mock_error_callback, error_message="aye message")(
            mock_command
        )

    assert result is mock_command
    any_hooks.assert_called_once_with()
    mock_command.set_hooks.assert_called_once_with(any_hooks.return_value)
    any_hooks.return_value.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    any_hooks.return_value.add_post_execution.assert_called_once_with(post_execution.return_value)
    pre_execution.assert_called_once_with("bucket me", error=mock_error_callback, error_message="aye message")
    post_execution.assert_called_once_with("bucket me")
    mock_command.wrapped_command.hooks.add_pre_execution.assert_not_called()
    mock_command.wrapped_command.hooks.add_post_execution.assert_not_called()
    mock_command.wrapped_command.set_hooks.assert_not_called()


def test_with_concurrency_limit_when_follow_wrapping():
    mock_command = mock.Mock()
    mock_command.hooks.add_pre_execution.return_value = mock_command.hooks
    mock_command.hooks.add_post_execution.return_value = mock_command.hooks
    mock_command.wrapped_command.hooks = None
    mock_command.wrapped_command.wrapped_command.hooks.add_pre_execution.return_value = (
        mock_command.wrapped_command.wrapped_command.hooks
    )
    mock_command.wrapped_command.wrapped_command.hooks.add_post_execution.return_value = (
        mock_command.wrapped_command.wrapped_command.hooks
    )
    mock_command.wrapped_command.wrapped_command.wrapped_command.hooks = None
    mock_command.wrapped_command.wrapped_command.wrapped_command.wrapped_command = None
    mock_hooks_1 = mock.Mock()
    mock_hooks_2 = mock.Mock()
    mock_hooks_1.add_pre_execution.return_value = mock_hooks_1
    mock_hooks_1.add_post_execution.return_value = mock_hooks_1
    mock_hooks_2.add_pre_execution.return_value = mock_hooks_2
    mock_hooks_2.add_post_execution.return_value = mock_hooks_2
    mock_error_callback = mock.Mock()

    with (
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPreExecution") as pre_execution,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPostExecution") as post_execution,
        mock.patch.object(tanjun.hooks, "AnyHooks", side_effect=[mock_hooks_1, mock_hooks_2]) as any_hooks,
    ):
        result = tanjun.with_concurrency_limit(
            "bucket me", error=mock_error_callback, error_message="aye message", follow_wrapped=True
        )(mock_command)

    assert result is mock_command
    any_hooks.assert_has_calls([mock.call(), mock.call()])
    mock_command.hooks.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_command.hooks.add_post_execution.assert_called_once_with(post_execution.return_value)
    mock_command.wrapped_command.set_hooks.assert_called_once_with(mock_hooks_1)
    mock_hooks_1.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_hooks_1.add_post_execution.assert_called_once_with(post_execution.return_value)
    mock_command.wrapped_command.wrapped_command.hooks.add_pre_execution.assert_called_once_with(
        pre_execution.return_value
    )
    mock_command.wrapped_command.wrapped_command.hooks.add_post_execution.assert_called_once_with(
        post_execution.return_value
    )
    mock_command.wrapped_command.wrapped_command.wrapped_command.set_hooks.assert_called_once_with(mock_hooks_2)
    mock_hooks_2.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_hooks_2.add_post_execution.assert_called_once_with(post_execution.return_value)
    pre_execution.assert_called_once_with("bucket me", error=mock_error_callback, error_message="aye message")
    post_execution.assert_called_once_with("bucket me")


def test_with_concurrency_limit_when_follow_wrapping_and_not_wrapping():
    mock_command = mock.Mock(wrapped_command=None)
    mock_command.hooks.add_pre_execution.return_value = mock_command.hooks
    mock_command.hooks.add_post_execution.return_value = mock_command.hooks
    mock_error_callback = mock.Mock()

    with (
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPreExecution") as pre_execution,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPostExecution") as post_execution,
    ):
        result = tanjun.with_concurrency_limit(
            "bucket me", error=mock_error_callback, error_message="aye message", follow_wrapped=True
        )(mock_command)

    assert result is mock_command
    mock_command.hooks.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_command.hooks.add_post_execution.assert_called_once_with(post_execution.return_value)
    pre_execution.assert_called_once_with("bucket me", error=mock_error_callback, error_message="aye message")
    post_execution.assert_called_once_with("bucket me")


def test_with_concurrency_limit_when_follow_wrapping_and_unsupported_command():
    mock_command = mock.Mock(tanjun.abc.ExecutableCommand)
    mock_command.hooks.add_pre_execution.return_value = mock_command.hooks
    mock_command.hooks.add_post_execution.return_value = mock_command.hooks
    mock_error_callback = mock.Mock()
    with pytest.raises(AttributeError):
        mock_command.wrapped_command

    with (
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPreExecution") as pre_execution,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPostExecution") as post_execution,
    ):
        result = tanjun.with_concurrency_limit(
            "bucket me", error=mock_error_callback, error_message="aye message", follow_wrapped=True
        )(mock_command)

    assert result is mock_command
    mock_command.hooks.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_command.hooks.add_post_execution.assert_called_once_with(post_execution.return_value)
    pre_execution.assert_called_once_with("bucket me", error=mock_error_callback, error_message="aye message")
    post_execution.assert_called_once_with("bucket me")


def test_with_concurrency_limit_when_follow_wrapping_and_wrapping_unsupported_command():
    mock_command = mock.Mock(wrapped_command=mock.Mock(tanjun.abc.SlashCommand))
    mock_command.hooks.add_pre_execution.return_value = mock_command.hooks
    mock_command.hooks.add_post_execution.return_value = mock_command.hooks
    mock_command.wrapped_command.hooks.add_pre_execution.return_value = mock_command.wrapped_command.hooks
    mock_command.wrapped_command.hooks.add_post_execution.return_value = mock_command.wrapped_command.hooks
    mock_error_callback = mock.Mock()
    with pytest.raises(AttributeError):
        mock_command.wrapped_command.wrapped_command

    with (
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPreExecution") as pre_execution,
        mock.patch.object(tanjun.dependencies.limiters, "ConcurrencyPostExecution") as post_execution,
    ):
        result = tanjun.with_concurrency_limit(
            "bucket me", error=mock_error_callback, error_message="aye message", follow_wrapped=True
        )(mock_command)

    assert result is mock_command
    mock_command.hooks.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_command.hooks.add_post_execution.assert_called_once_with(post_execution.return_value)
    mock_command.wrapped_command.hooks.add_pre_execution.assert_called_once_with(pre_execution.return_value)
    mock_command.wrapped_command.hooks.add_post_execution.assert_called_once_with(post_execution.return_value)
    pre_execution.assert_called_once_with("bucket me", error=mock_error_callback, error_message="aye message")
    post_execution.assert_called_once_with("bucket me")
