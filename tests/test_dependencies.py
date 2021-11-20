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
    assert await tanjun.dependencies._get_ctx_target(mock_ctx, resource_type) == expected


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel():
    mock_context = mock.Mock()

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result is mock_context.get_channel.return_value.parent_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_defaults_to_guild_id():
    mock_context = mock.Mock()
    mock_context.get_channel.return_value.parent_id = None

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result is mock_context.guild_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_falls_back_to_rest():
    mock_context = mock.Mock()
    mock_context.get_channel.return_value = None
    mock_context.fetch_channel = mock.AsyncMock(return_value=mock.Mock(hikari.TextableGuildChannel))

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result is mock_context.fetch_channel.return_value.parent_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_awaited_once()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_falls_back_to_rest_and_defaults_to_guild_id():
    mock_context = mock.Mock()
    mock_context.get_channel.return_value = None
    mock_context.fetch_channel = mock.AsyncMock(return_value=mock.Mock(hikari.TextableGuildChannel, parent_id=None))

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

    assert result is mock_context.guild_id
    mock_context.get_channel.assert_called_once_with()
    mock_context.fetch_channel.assert_awaited_once()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_parent_channel_and_dm_bound():
    mock_context = mock.Mock(guild_id=None)

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.PARENT_CHANNEL)

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
    mock_context = mock.Mock()
    mock_context.member.role_ids = [123, 312]
    mock_context.member.get_roles = mock.Mock(return_value=mock_roles)
    mock_context.member.fetch_roles = mock.AsyncMock()

    assert await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE) == 123321

    mock_context.member.get_roles.assert_called_once_with()
    mock_context.member.fetch_roles.assert_not_called()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_falls_back_to_rest():
    mock_roles = [
        mock.Mock(id=123321, position=42),
        mock.Mock(id=123322, position=43),
        mock.Mock(id=431, position=6969),
        mock.Mock(id=111, position=0),
        mock.Mock(id=4123, position=6959),
    ]
    mock_context = mock.Mock()
    mock_context.member.role_ids = [123, 312]
    mock_context.member.get_roles = mock.Mock(return_value=[])
    mock_context.member.fetch_roles = mock.AsyncMock(return_value=mock_roles)

    assert await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE) == 431

    mock_context.member.get_roles.assert_called_once_with()
    mock_context.member.fetch_roles.assert_awaited_once_with()


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_when_dm_bound():
    mock_context = mock.Mock(guild_id=None)

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE)

    assert result is mock_context.channel_id


@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_when_no_member_in_guild():
    mock_context = mock.Mock(guild_id=654124, member=None)

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE)

    assert result == 654124


@pytest.mark.parametrize("role_ids", [[123321], []])
@pytest.mark.asyncio()
async def test__get_ctx_target_when_top_role_when_no_roles_or_only_1_role(role_ids: list[int]):
    mock_context = mock.Mock(guild_id=123312)
    mock_context.member.role_ids = role_ids

    result = await tanjun.dependencies._get_ctx_target(mock_context, tanjun.BucketResource.TOP_ROLE)

    assert result == 123312


@pytest.mark.asyncio()
async def test__get_ctx_target_when_unexpected_type():
    with pytest.raises(ValueError, match="Unexpected type 1"):
        await tanjun.dependencies._get_ctx_target(mock.Mock(), tanjun.BucketResource.MEMBER)


class Test_Cooldown:
    def test_has_expired_property(self):
        with mock.patch.object(time, "monotonic", side_effect=[69.0, 72.0]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=60.0))

            assert cooldown.has_expired() is False

    def test_has_expired_property_when_has_expired(self):
        with mock.patch.object(time, "monotonic", side_effect=[69.0, 96.0]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=26.5))

            assert cooldown.has_expired() is True

    def test_increment(self):
        with mock.patch.object(time, "monotonic", side_effect=[50.0, 55.0]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=69.420))
            cooldown.counter = 2

            cooldown.increment()

            assert cooldown.counter == 3
            assert cooldown.will_reset_after == 119.420

    def test_increment_when_counter_is_0(self):
        with mock.patch.object(time, "monotonic", side_effect=[419.0, 420.0]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=69.00))

            cooldown.increment()

            assert cooldown.counter == 1
            assert cooldown.will_reset_after == 489.00

    def test_increment_when_passed_reset_after(self):
        with mock.patch.object(time, "monotonic", side_effect=[419.0, 422.5]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=2.0))
            cooldown.counter = 2

            cooldown.increment()

            assert cooldown.counter == 1
            assert cooldown.will_reset_after == 424.5

    def test_must_wait_until(self):
        with mock.patch.object(time, "monotonic", side_effect=[419.0, 422.0]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=10.5, limit=3))
            cooldown.counter = 3

            assert cooldown.must_wait_until() == 7.5

    def test_must_wait_until_when_resource_limit_not_hit(self):
        cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=2.0, limit=3))
        cooldown.counter = 2

        assert cooldown.must_wait_until() is None

    def test_must_wait_until_when_reset_after_reached(self):
        with mock.patch.object(time, "monotonic", side_effect=[419.0, 425.5]):
            cooldown = tanjun.dependencies._Cooldown(mock.Mock(reset_after=5.0, limit=3))
            cooldown.counter = 3

            assert cooldown.must_wait_until() is None


class Test_CooldownBucket:
    @pytest.mark.asyncio()
    async def test_check(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=None))
        bucket.mapping[hikari.Snowflake(3333)] = mock_cooldown
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(3333)

        result = await bucket.check(mock_context, increment=False)

        assert result is None
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_when_wait_for(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=321.123123123))
        bucket.mapping[hikari.Snowflake(3333)] = mock_cooldown
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(3333)

        result = await bucket.check(mock_context, increment=False)

        assert result is mock_cooldown.must_wait_until.return_value
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_when_no_cooldown(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(3333)

        result = await bucket.check(mock_context, increment=False)

        assert result is None
        assert hikari.Snowflake(3333) not in bucket.mapping

    @pytest.mark.asyncio()
    async def test_check_creates_new_cooldown_when_increment_and_not_present(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(455445)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            result = await bucket.check(mock_context, increment=True)

            cooldown.assert_called_once_with(bucket)

        assert result is None
        cooldown.return_value.must_wait_until.assert_not_called()
        cooldown.return_value.increment.assert_called_once_with()
        assert bucket.mapping[hikari.Snowflake(455445)] is cooldown.return_value

    @pytest.mark.asyncio()
    async def test_check_when_increment(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=None))
        bucket.mapping[hikari.Snowflake(421123)] = mock_cooldown
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(421123)

        result = await bucket.check(mock_context, increment=True)

        assert result is None
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_doesnt_increment_when_wait_until(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=123.321))
        bucket.mapping[hikari.Snowflake(421123)] = mock_cooldown
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(421123)

        result = await bucket.check(mock_context, increment=True)

        assert result is mock_cooldown.must_wait_until.return_value
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_increment(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_cooldown = mock.Mock()
        bucket.mapping[hikari.Snowflake(65234)] = mock_cooldown
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(65234)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_not_called()
            mock_cooldown.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_increment_creates_new_cooldown(self):
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
        mock_context = mock.Mock()
        mock_context.author.id = hikari.Snowflake(321)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_called_once_with(bucket)
            cooldown.return_value.increment.assert_called_once_with()
            assert bucket.mapping[hikari.Snowflake(321)] is cooldown.return_value

    def test_cleanup(self):
        mock_cooldown_1 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_2 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_3 = mock.Mock(has_expired=mock.Mock(return_value=False))
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.USER, 123, 321.123)
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
        bucket = tanjun.dependencies._CooldownBucket(tanjun.BucketResource.PARENT_CHANNEL, 123, 321.123)
        bucket.mapping[hikari.Snowflake(321123)] = mock.Mock()

        new_bucket = bucket.copy()

        assert new_bucket is not bucket
        assert new_bucket.type is bucket.type
        assert new_bucket.reset_after is bucket.reset_after
        assert new_bucket.limit is bucket.limit
        assert new_bucket.mapping == {}


class Test_MemberCooldownResource:
    @pytest.mark.asyncio()
    async def test_check(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=None))
        bucket.mapping[hikari.Snowflake(654123)] = {hikari.Snowflake(3333): mock_cooldown}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(654123))
        mock_context.author.id = hikari.Snowflake(3333)

        result = await bucket.check(mock_context, increment=False)

        assert result is None
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_when_wait_for(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=321.757564646969))
        bucket.mapping[hikari.Snowflake(543)] = {hikari.Snowflake(123): mock_cooldown}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(543))
        mock_context.author.id = hikari.Snowflake(123)

        result = await bucket.check(mock_context, increment=False)

        assert result is mock_cooldown.must_wait_until.return_value
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_when_increment(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=None))
        bucket.mapping[hikari.Snowflake(3123)] = {hikari.Snowflake(123312): mock_cooldown}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(3123))
        mock_context.author.id = hikari.Snowflake(123312)

        result = await bucket.check(mock_context, increment=True)

        assert result is None
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_doesnt_increment_when_wait_for(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=321.324123))
        bucket.mapping[hikari.Snowflake(3123)] = {hikari.Snowflake(123312): mock_cooldown}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(3123))
        mock_context.author.id = hikari.Snowflake(123312)

        result = await bucket.check(mock_context, increment=True)

        assert result is mock_cooldown.must_wait_until.return_value
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_creates_new_cooldown_when_increment(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        bucket.mapping[hikari.Snowflake(4554444445)] = {hikari.Snowflake(123312): mock.Mock()}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(4554444445))
        mock_context.author.id = hikari.Snowflake(555)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            result = await bucket.check(mock_context, increment=True)

            cooldown.assert_called_once_with(bucket)

        assert result is None
        cooldown.return_value.must_wait_until.assert_not_called()
        cooldown.return_value.increment.assert_called_once_with()
        assert bucket.mapping[hikari.Snowflake(4554444445)][hikari.Snowflake(555)] is cooldown.return_value
        assert len(bucket.mapping[hikari.Snowflake(4554444445)]) == 2

    @pytest.mark.asyncio()
    async def test_check_for_new_guild_when_increment(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_context = mock.Mock(guild_id=hikari.Snowflake(543))
        mock_context.author.id = hikari.Snowflake(123)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            result = await bucket.check(mock_context, increment=True)

            cooldown.assert_called_once_with(bucket)

        assert result is None
        cooldown.return_value.must_wait_until.assert_not_called()
        cooldown.return_value.increment.assert_called_once_with()
        assert bucket.mapping[hikari.Snowflake(543)] == {hikari.Snowflake(123): cooldown.return_value}

    @pytest.mark.asyncio()
    async def test_check_dm_fallback(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=None))
        bucket.dm_fallback[hikari.Snowflake(564123123)] = mock_cooldown
        mock_context = mock.Mock(channel_id=hikari.Snowflake(564123123), guild_id=None)

        result = await bucket.check(mock_context, increment=False)

        assert result is None
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_dm_fallback_when_wait_for(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=321.757564646969))
        bucket.dm_fallback[hikari.Snowflake(54123123)] = mock_cooldown
        mock_context = mock.Mock(channel_id=54123123, guild_id=None)

        result = await bucket.check(mock_context, increment=False)

        assert result is mock_cooldown.must_wait_until.return_value
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_dm_fallback_when_increment(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock(must_wait_until=mock.Mock(return_value=None))
        bucket.dm_fallback[hikari.Snowflake(6512312)] = mock_cooldown
        mock_context = mock.Mock(channel_id=hikari.Snowflake(6512312), guild_id=None)

        result = await bucket.check(mock_context, increment=True)

        assert result is None
        mock_cooldown.must_wait_until.assert_called_once_with()
        mock_cooldown.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_dm_fallback_creates_new_cooldown_when_increment(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_context = mock.Mock(channel_id=hikari.Snowflake(959595), guild_id=None)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            result = await bucket.check(mock_context, increment=True)

            cooldown.assert_called_once_with(bucket)

        assert result is None
        cooldown.return_value.must_wait_until.assert_not_called()
        cooldown.return_value.increment.assert_called_once_with()
        assert bucket.dm_fallback[hikari.Snowflake(959595)] is cooldown.return_value

    @pytest.mark.asyncio()
    async def test_increment(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock()
        bucket.mapping[hikari.Snowflake(65123123)] = {hikari.Snowflake(53123): mock_cooldown}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(65123123))
        mock_context.author.id = hikari.Snowflake(53123)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_not_called()
            mock_cooldown.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_increment_creates_new_cooldown(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        bucket.mapping[hikari.Snowflake(696969)] = {hikari.Snowflake(696969): mock.Mock()}
        mock_context = mock.Mock(guild_id=hikari.Snowflake(696969))
        mock_context.author.id = hikari.Snowflake(65123)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_called_once_with(bucket)
            cooldown.return_value.increment.assert_called_once_with()
            assert bucket.mapping[hikari.Snowflake(696969)][hikari.Snowflake(65123)] is cooldown.return_value
            assert len(bucket.mapping[hikari.Snowflake(696969)]) == 2

    @pytest.mark.asyncio()
    async def test_increment_for_new_guild(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_context = mock.Mock(guild_id=hikari.Snowflake(696969))
        mock_context.author.id = hikari.Snowflake(65123)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_called_once_with(bucket)
            cooldown.return_value.increment.assert_called_once_with()
            assert bucket.mapping[hikari.Snowflake(696969)] == {hikari.Snowflake(65123): cooldown.return_value}

    @pytest.mark.asyncio()
    async def test_increment_dm_fallback(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_cooldown = mock.Mock()
        bucket.dm_fallback[hikari.Snowflake(54123)] = mock_cooldown
        mock_context = mock.Mock(channel_id=hikari.Snowflake(54123), guild_id=None)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_not_called()
            mock_cooldown.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_increment_dm_fallback_creates_new_cooldown(self):
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        mock_context = mock.Mock(channel_id=hikari.Snowflake(767676767676), guild_id=None)

        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown:
            await bucket.increment(mock_context)

            cooldown.assert_called_once_with(bucket)
            cooldown.return_value.increment.assert_called_once_with()
            assert bucket.dm_fallback[hikari.Snowflake(767676767676)] is cooldown.return_value

    def test_cleanup(self):
        mock_cooldown_1 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_2 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_cooldown_3 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_dm_cooldown_1 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_dm_cooldown_2 = mock.Mock(has_expired=mock.Mock(return_value=False))
        mock_dm_cooldown_3 = mock.Mock(has_expired=mock.Mock(return_value=False))
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
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
        bucket = tanjun.dependencies._MemberCooldownResource(123, 321.123)
        bucket.mapping[hikari.Snowflake(321123)] = mock.Mock()
        bucket.dm_fallback[hikari.Snowflake(541123)] = mock.Mock()

        new_bucket = bucket.copy()

        assert new_bucket is not bucket
        assert new_bucket.reset_after is bucket.reset_after
        assert new_bucket.limit is bucket.limit
        assert new_bucket.mapping == {}
        assert new_bucket.dm_fallback == {}


class Test_GlobalCooldownResource:
    @pytest.mark.asyncio()
    async def test_check(self):
        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown_cls:
            cooldown_cls.return_value.must_wait_until.return_value = None

            resource = tanjun.dependencies._GlobalCooldownResource(123, 312.123)

        result = await resource.check(mock.Mock())

        assert result is None
        cooldown_cls.assert_called_once_with(resource)
        cooldown_cls.return_value.must_wait_until.assert_called_once_with()
        cooldown_cls.return_value.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_when_increment(self):
        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown_cls:
            cooldown_cls.return_value.must_wait_until.return_value = None

            resource = tanjun.dependencies._GlobalCooldownResource(123, 312.123)

        result = await resource.check(mock.Mock(), increment=True)

        assert result is None
        cooldown_cls.assert_called_once_with(resource)
        cooldown_cls.return_value.must_wait_until.assert_called_once_with()
        cooldown_cls.return_value.increment.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_doesnt_increment_when_wait_until(self):
        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown_cls:
            cooldown_cls.return_value.must_wait_until.return_value = 541.123

            resource = tanjun.dependencies._GlobalCooldownResource(123, 312.123)

        result = await resource.check(mock.Mock(), increment=True)

        assert result is cooldown_cls.return_value.must_wait_until.return_value
        cooldown_cls.assert_called_once_with(resource)
        cooldown_cls.return_value.must_wait_until.assert_called_once_with()
        cooldown_cls.return_value.increment.assert_not_called()

    @pytest.mark.asyncio()
    async def test_increment(self):
        with mock.patch.object(tanjun.dependencies, "_Cooldown") as cooldown_cls:
            cooldown_cls.return_value.must_wait_until.return_value = None

            resource = tanjun.dependencies._GlobalCooldownResource(123, 312.123)

        await resource.increment(mock.Mock())

        cooldown_cls.return_value.increment.assert_called_once_with()

    def test_cleanup(self):
        tanjun.dependencies._GlobalCooldownResource(123, 312.123).cleanup()

    def test_copy(self):
        bucket = tanjun.dependencies._GlobalCooldownResource(123, 321.123)
        bucket.bucket.increment()

        new_bucket = bucket.copy()

        assert new_bucket is not bucket
        assert new_bucket.bucket is not bucket.bucket
        assert new_bucket.bucket.counter is not bucket.bucket.counter
        assert new_bucket.bucket.will_reset_after is not bucket.bucket.will_reset_after
        assert new_bucket.reset_after is bucket.reset_after
        assert new_bucket.limit is bucket.limit


class TestInMemoryCooldownManager:
    @pytest.mark.asyncio()
    async def _gc(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_bucket_1 = mock.Mock()
        mock_bucket_2 = mock.Mock()
        mock_bucket_3 = mock.Mock()
        manager._buckets = {"e": mock_bucket_1, "a": mock_bucket_2, "f": mock_bucket_3}

        await asyncio.wait_for(manager._gc(), timeout=0.1)

        mock_bucket_1.cleanup.assert_called_once_with()
        mock_bucket_2.cleanup.assert_called_once_with()
        mock_bucket_3.cleanup.assert_called_once_with()

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
        mock_bucket = mock.AsyncMock()
        manager._buckets["ok"] = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=True)

        assert result is mock_bucket.check.return_value
        mock_bucket.check.assert_called_once_with(mock_context, increment=True)

    @pytest.mark.asyncio()
    async def test_check_cooldown_falls_back_to_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.AsyncMock()
        manager._buckets["default"] = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=False)

        assert result is None
        assert "ok" not in manager._buckets
        mock_bucket.copy.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_cooldown_falls_back_to_default_when_increment_creates_new_bucket(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock()
        mock_bucket.copy.return_value = mock.AsyncMock()
        manager._default_bucket_template = mock_bucket

        result = await manager.check_cooldown("ok", mock_context, increment=True)

        assert result is mock_bucket.copy.return_value.check.return_value
        assert manager._buckets["ok"] is mock_bucket.copy.return_value
        mock_bucket.copy.assert_called_once_with()
        mock_bucket.copy.return_value.check.assert_called_once_with(mock_context, increment=True)

    @pytest.mark.asyncio()
    async def test_increment_cooldown(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.AsyncMock()
        manager._buckets["catgirl neko"] = mock_bucket

        result = await manager.increment_cooldown("catgirl neko", mock_context)

        assert result is mock_bucket.increment.return_value
        mock_bucket.increment.assert_called_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_increment_cooldown_falls_back_to_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_context = mock.Mock()
        mock_bucket = mock.Mock()
        mock_bucket.copy.return_value = mock.AsyncMock()
        manager._default_bucket_template = mock_bucket

        result = await manager.increment_cooldown("69", mock_context)

        assert result is mock_bucket.copy.return_value.increment.return_value
        assert manager._buckets["69"] is mock_bucket.copy.return_value
        mock_bucket.copy.assert_called_once_with()
        mock_bucket.copy.return_value.increment.assert_called_once_with(mock_context)

    def test_close(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_gc_loop = mock.Mock()
        manager._gc_loop = mock_gc_loop

        manager.close()

        mock_gc_loop.cancel.assert_called_once_with()

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

            assert manager._gc_loop is get_running_loop.return_value.create_task.return_value
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

        assert manager._gc_loop is mock_loop.create_task.return_value
        mock_loop.create_task.assert_called_once_with(mock_gc.return_value)
        mock_gc.assert_called_once_with()

    def test_open_when_already_active(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._gc_loop = mock.Mock()

        with pytest.raises(RuntimeError, match="Cooldown manager is already running"):
            manager.open()

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

        with mock.patch.object(tanjun.dependencies, "_CooldownBucket") as cooldown_bucket:
            manager.set_bucket("gay catgirl", resource_type, 123, 43.123)

            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            cooldown_bucket.assert_called_once_with(resource_type, 123, 43.123)

    @pytest.mark.parametrize("reset_after", [datetime.timedelta(seconds=69), 69, 69.0])
    def test_set_bucket_handles_different_reset_after_types(
        self, reset_after: typing.Union[datetime.timedelta, int, float]
    ):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies, "_CooldownBucket") as cooldown_bucket:
            manager.set_bucket("gay catgirl", tanjun.BucketResource.USER, 444, reset_after)

            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            cooldown_bucket.assert_called_once_with(tanjun.BucketResource.USER, 444, 69)

    def test_set_bucket_for_member_resource(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies, "_MemberCooldownResource") as cooldown_bucket:
            manager.set_bucket("meowth", tanjun.BucketResource.MEMBER, 64, 42.0)

            assert manager._buckets["meowth"] is cooldown_bucket.return_value
            cooldown_bucket.assert_called_once_with(64, 42.0)

    def test_set_bucket_for_global_resource(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies, "_GlobalCooldownResource") as cooldown_bucket:
            manager.set_bucket("meow", tanjun.BucketResource.GLOBAL, 420, 69.420)

            assert manager._buckets["meow"] is cooldown_bucket.return_value
            cooldown_bucket.assert_called_once_with(420, 69.420)

    def test_set_bucket_when_is_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with mock.patch.object(tanjun.dependencies, "_CooldownBucket") as cooldown_bucket:
            manager.set_bucket("default", tanjun.BucketResource.USER, 777, 666.0)

            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._default_bucket_template is cooldown_bucket.return_value.copy.return_value
            cooldown_bucket.assert_called_once_with(tanjun.BucketResource.USER, 777, 666.0)
            cooldown_bucket.return_value.copy.assert_called_once_with()

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
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri catgirls", owners_exempt=False)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = None
        mock_owner_check = mock.AsyncMock()

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("yuri catgirls", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri catgirls", owners_exempt=True)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = True

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_not_called()
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_and_not_owner(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls", owners_exempt=True)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = None
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_for(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = 69.420
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(tanjun.CommandError, match="Please wait 69.42 seconds before using this command again"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_wait_for(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls yuri", owners_exempt=False)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.check_cooldown.return_value = 420.69420
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="Please wait 420.69 seconds before using this command again"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.check_cooldown.assert_awaited_once_with("catgirls yuri", mock_context, increment=True)
        mock_owner_check.check_ownership.assert_not_called()


def test_with_cooldown():
    mock_command = mock.Mock()

    with mock.patch.object(tanjun.dependencies, "CooldownPreExecution") as mock_pre_execution:
        tanjun.with_cooldown("catgirl x catgirl", error_message="pussy cat pussy cat", owners_exempt=False)(
            mock_command
        )

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)


def test_with_cooldown_when_no_set_hooks():
    mock_command = mock.Mock(hooks=None)

    stack = contextlib.ExitStack()
    mock_pre_execution = stack.enter_context(mock.patch.object(tanjun.dependencies, "CooldownPreExecution"))
    any_hooks = stack.enter_context(mock.patch.object(tanjun.hooks, "AnyHooks"))

    with stack:
        tanjun.with_cooldown("catgirl x catgirl", error_message="pussy cat pussy cat", owners_exempt=False)(
            mock_command
        )

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl", error_message="pussy cat pussy cat", owners_exempt=False
        )
        mock_command.set_hooks.assert_called_once_with(any_hooks.return_value)
        any_hooks.return_value.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
        any_hooks.assert_called_once_with()


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


def test_inject_lc():
    stack = contextlib.ExitStack()
    inject = stack.enter_context(mock.patch.object(tanjun.injecting, "inject"))
    make_lc_resolver = stack.enter_context(mock.patch.object(tanjun.dependencies, "make_lc_resolver"))
    mock_type: type[typing.Any] = mock.Mock()

    with stack:
        result = tanjun.inject_lc(mock_type)

    assert result is inject.return_value
    inject.assert_called_once_with(callback=make_lc_resolver.return_value)
    make_lc_resolver.assert_called_once_with(mock_type)


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
    mock_client = mock.Mock(tanjun.Client)
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


def test_cached_inject():
    stack = contextlib.ExitStack()
    inject = stack.enter_context(mock.patch.object(tanjun.injecting, "inject"))
    cache_callback = stack.enter_context(mock.patch.object(tanjun.dependencies, "cache_callback"))
    mock_callback = mock.Mock()

    with stack:
        result = tanjun.cached_inject(mock_callback, expire_after=datetime.timedelta(seconds=15))

    assert result is inject.return_value
    inject.assert_called_once_with(callback=cache_callback.return_value)
    cache_callback.assert_called_once_with(mock_callback, expire_after=datetime.timedelta(seconds=15))


def test_cached_inject_with_defaults():
    stack = contextlib.ExitStack()
    inject = stack.enter_context(mock.patch.object(tanjun.injecting, "inject"))
    cache_callback = stack.enter_context(mock.patch.object(tanjun.dependencies, "cache_callback"))
    mock_callback = mock.Mock()

    with stack:
        result = tanjun.cached_inject(mock_callback)

    assert result is inject.return_value
    inject.assert_called_once_with(callback=cache_callback.return_value)
    cache_callback.assert_called_once_with(mock_callback, expire_after=None)
