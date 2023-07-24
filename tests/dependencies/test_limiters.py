# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
import re
import typing

import alluka
import freezegun
import hikari
import mock
import pytest

import tanjun
from tanjun.context import base as base_context


def _now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class TestAbstractCooldownManager:
    @pytest.mark.asyncio()
    async def test_increment_cooldown(self):
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        mock_context = mock.Mock()

        with pytest.warns(DeprecationWarning):
            await manager.increment_cooldown("catgirl neko", mock_context)

        mock_try_acquire.assert_awaited_once_with("catgirl neko", mock_context)
        mock_release.assert_awaited_once_with("catgirl neko", mock_context)

    @pytest.mark.asyncio()
    async def test_increment_cooldown_when_resource_depleted(self):
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.CooldownDepleted(None))
        mock_release = mock.AsyncMock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        mock_context = mock.Mock()

        with pytest.warns(DeprecationWarning):
            await manager.increment_cooldown("catgirl neko", mock_context)

        mock_try_acquire.assert_awaited_once_with("catgirl neko", mock_context)
        mock_release.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire(self):
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        async with manager.acquire("buuuuu", mock_ctx, error=mock_error_callback):
            mock_try_acquire.assert_awaited_once_with("buuuuu", mock_ctx)
            mock_release.assert_not_awaited()

        mock_try_acquire.assert_awaited_once_with("buuuuu", mock_ctx)
        mock_release.assert_awaited_once_with("buuuuu", mock_ctx)
        mock_error_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_ended_by_raise(self):
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        with pytest.raises(RuntimeError, match="bye"):  # noqa: PT012
            async with manager.acquire("buuuuu", mock_ctx, error=mock_error_callback):
                mock_try_acquire.assert_awaited_once_with("buuuuu", mock_ctx)
                mock_release.assert_not_called()

                raise RuntimeError("bye")

        mock_try_acquire.assert_awaited_once_with("buuuuu", mock_ctx)
        mock_release.assert_awaited_once_with("buuuuu", mock_ctx)
        mock_error_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_errors(self):
        mock_try_acquire = mock.AsyncMock(
            side_effect=tanjun.dependencies.CooldownDepleted(
                datetime.datetime(2023, 5, 19, 21, 20, 28, 782112, tzinfo=datetime.timezone.utc)
            )
        )
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        with pytest.raises(tanjun.CommandError) as exc:  # noqa: PT012
            async with manager.acquire("mooo", mock_ctx):
                pytest.fail("Should never be reached")

        assert exc.value.content == "This command is currently in cooldown. Try again <t:1684531229:R>."
        mock_try_acquire.assert_awaited_once_with("mooo", mock_ctx)
        mock_release.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_errors_with_unknown_wait_until(self):
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.CooldownDepleted(None))
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        with pytest.raises(tanjun.CommandError) as exc:  # noqa: PT012
            async with manager.acquire("mooo", mock_ctx):
                pytest.fail("Should never be reached")

        assert exc.value.content == "This command is currently in cooldown."
        mock_try_acquire.assert_awaited_once_with("mooo", mock_ctx)
        mock_release.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_custom_error(self):
        expected_datetime = datetime.datetime(2023, 7, 19, 21, 20, 28, 782112, tzinfo=datetime.timezone.utc)
        expected_error = Exception("It's 5 nights at Fred bear's")
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.CooldownDepleted(expected_datetime))
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock(side_effect=expected_error)

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        with pytest.raises(Exception, match="It's 5 nights at Fred bear's") as exc:  # noqa: PT012
            async with manager.acquire("ooop", mock_ctx, error=mock_error_callback):
                pytest.fail("Should never be reached")

        assert exc.value is expected_error
        mock_try_acquire.assert_awaited_once_with("ooop", mock_ctx)
        mock_release.assert_not_called()
        mock_error_callback.assert_called_once_with(expected_datetime)

    @pytest.mark.asyncio()
    async def test_acquire_when_already_acquired(self):
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()
        acquire = manager.acquire("oop", mock_ctx)

        async with acquire:
            mock_try_acquire.assert_awaited_once_with("oop", mock_ctx)
            mock_release.assert_not_called()

            with pytest.raises(RuntimeError, match="Already acquired"):  # noqa: PT012
                async with acquire:
                    pytest.fail("Should never be reached")

        mock_try_acquire.assert_awaited_once_with("oop", mock_ctx)
        mock_release.assert_awaited_once_with("oop", mock_ctx)
        mock_error_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_release_when_not_acquired(self):
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()

        class CooldownManager(tanjun.dependencies.AbstractCooldownManager):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release
            check = check_cooldown = mock.AsyncMock()

        manager = CooldownManager()

        acquire = manager.acquire("oop", mock_ctx)

        with pytest.raises(RuntimeError, match="Not acquired"):
            await acquire.__aexit__(None, None, None)

        mock_try_acquire.assert_not_called()
        mock_release.assert_not_called()
        mock_error_callback.assert_not_called()


class TestAbstractConcurrencyLimiter:
    @pytest.mark.asyncio()
    async def test_acquire(self):
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()

        class ConcurrencyLimiter(tanjun.dependencies.AbstractConcurrencyLimiter):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release

        limiter = ConcurrencyLimiter()

        async with limiter.acquire("oooooo", mock_ctx, error=mock_error_callback):
            mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
            mock_release.assert_not_called()

        mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
        mock_release.assert_awaited_once_with("oooooo", mock_ctx)
        mock_error_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_ended_by_raise(self):
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()

        class ConcurrencyLimiter(tanjun.dependencies.AbstractConcurrencyLimiter):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release

        limiter = ConcurrencyLimiter()

        with pytest.raises(RuntimeError, match="yeet"):  # noqa: PT012
            async with limiter.acquire("oooooo", mock_ctx, error=mock_error_callback):
                mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
                mock_release.assert_not_called()

                raise RuntimeError("yeet")

        mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
        mock_release.assert_awaited_once_with("oooooo", mock_ctx)
        mock_error_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_errors(self):
        mock_ctx = mock.Mock()
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.ResourceDepleted)
        mock_release = mock.AsyncMock()

        class ConcurrencyLimiter(tanjun.dependencies.AbstractConcurrencyLimiter):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release

        limiter = ConcurrencyLimiter()

        with pytest.raises(tanjun.CommandError) as exc:  # noqa: PT012
            async with limiter.acquire("oooooo", mock_ctx):
                pytest.fail("Should never be reached")

        assert exc.value.content == "This resource is currently busy; please try again later."
        mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
        mock_release.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_custom_error(self):
        mock_ctx = mock.Mock()
        expected_error = Exception("P music")
        mock_error_callback = mock.Mock(side_effect=expected_error)
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.ResourceDepleted)
        mock_release = mock.AsyncMock()

        class ConcurrencyLimiter(tanjun.dependencies.AbstractConcurrencyLimiter):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release

        limiter = ConcurrencyLimiter()

        with pytest.raises(Exception, match="P music") as exc:  # noqa: PT012
            async with limiter.acquire("oooooo", mock_ctx, error=mock_error_callback):
                pytest.fail("Should never be reached")

        assert exc.value is expected_error
        mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
        mock_release.assert_not_called()

    @pytest.mark.asyncio()
    async def test_acquire_when_already_acquired(self):
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()

        class ConcurrencyLimiter(tanjun.dependencies.AbstractConcurrencyLimiter):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release

        limiter = ConcurrencyLimiter()
        acquire = limiter.acquire("oooooo", mock_ctx, error=mock_error_callback)

        async with acquire:
            mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
            mock_release.assert_not_called()

            with pytest.raises(RuntimeError, match="Already acquired"):  # noqa: PT012
                async with acquire:
                    pytest.fail("Should never be reached")

        mock_try_acquire.assert_awaited_once_with("oooooo", mock_ctx)
        mock_release.assert_awaited_once_with("oooooo", mock_ctx)
        mock_error_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_release_when_not_acquired(self):
        mock_ctx = mock.Mock()
        mock_error_callback = mock.Mock()
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()

        class ConcurrencyLimiter(tanjun.dependencies.AbstractConcurrencyLimiter):
            __slots__ = ()

            try_acquire = mock_try_acquire
            release = mock_release

        limiter = ConcurrencyLimiter()
        acquire = limiter.acquire("oooooo", mock_ctx, error=mock_error_callback)

        with pytest.raises(RuntimeError, match="Not acquired"):
            await acquire.__aexit__(None, None, None)

        mock_try_acquire.assert_not_called()
        mock_release.assert_not_called()
        mock_error_callback.assert_not_called()


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
    with pytest.raises(ValueError, match="Unexpected type BucketResource.MEMBER"):
        await tanjun.dependencies.limiters._get_ctx_target(mock.Mock(), tanjun.BucketResource.MEMBER)


class TestCooldown:
    def test_has_expired_property(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(limit=1, reset_after=datetime.timedelta(seconds=60))

        cooldown.increment(mock.Mock())

        assert cooldown.has_expired() is False

    def test_has_expired_property_after_unlock(self):
        mock_ctx = mock.Mock()
        cooldown = tanjun.dependencies.limiters._Cooldown(limit=1, reset_after=datetime.timedelta(seconds=60))

        cooldown.increment(mock_ctx)
        cooldown.unlock(mock_ctx)

        assert cooldown.has_expired() is False

    def test_has_expired_property_when_has_expired(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=1, reset_after=datetime.timedelta(seconds=26, milliseconds=500)
        )

        assert cooldown.has_expired() is True

    def test_has_expired_property_when_tracking_expired_acquires(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=1, reset_after=datetime.timedelta(seconds=26, milliseconds=500)
        )
        now = _now()
        cooldown.resets = [
            now - datetime.timedelta(seconds=3, milliseconds=500),
            now - datetime.timedelta(seconds=1, milliseconds=500),
        ]

        assert cooldown.has_expired() is True

    def test_check_clears_old_releases(self):
        now = _now()
        mock_ctx_1 = mock.Mock()
        mock_ctx_2 = mock.Mock()
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=6, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )
        cooldown.resets = [
            now - datetime.timedelta(seconds=20, milliseconds=580),
            now - datetime.timedelta(seconds=5, milliseconds=580),
            now + datetime.timedelta(seconds=25, milliseconds=420),
            now + datetime.timedelta(seconds=37, milliseconds=420),
        ]
        cooldown.locked = {mock_ctx_1, mock_ctx_2}

        cooldown.check()

        assert cooldown.locked == {mock_ctx_1, mock_ctx_2}
        assert cooldown.resets == [
            now + datetime.timedelta(seconds=25, milliseconds=420),
            now + datetime.timedelta(seconds=37, milliseconds=420),
        ]

    def test(self):
        now = _now()
        mock_ctx = mock.Mock()
        mock_other_ctx = mock.Mock()
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=5, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )
        cooldown.resets = [
            now + datetime.timedelta(seconds=59, milliseconds=420),
            now + datetime.timedelta(seconds=64, milliseconds=420),
        ]
        cooldown.locked.add(mock_other_ctx)

        cooldown.increment(mock_ctx)

        assert cooldown.locked == {mock_ctx, mock_other_ctx}
        assert cooldown.resets == [
            now + datetime.timedelta(seconds=59, milliseconds=420),
            now + datetime.timedelta(seconds=64, milliseconds=420),
        ]
        assert cooldown.check()

    def test_when_counter_no_ctxs_tracked(self):
        mock_ctx = mock.Mock()
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=5, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )

        cooldown.increment(mock_ctx)

        assert cooldown.locked == {mock_ctx}
        assert cooldown.resets == []
        assert cooldown.check()

    def test_when_counter_is_at_limit(self):
        now = _now()
        mock_ctx = mock.Mock()
        mock_ctx_1 = mock.Mock()
        mock_ctx_2 = mock.Mock()
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=5, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )
        cooldown.resets = [
            now + datetime.timedelta(seconds=59, milliseconds=420),
            now + datetime.timedelta(seconds=64, milliseconds=420),
        ]
        cooldown.locked = {mock_ctx_1, mock_ctx_2}

        cooldown.increment(mock_ctx)

        with pytest.raises(tanjun.dependencies.CooldownDepleted) as exc:
            assert cooldown.check()

        assert exc.value.wait_until == now + datetime.timedelta(seconds=59, milliseconds=420)
        assert cooldown.locked == {mock_ctx, mock_ctx_1, mock_ctx_2}
        assert cooldown.resets == [
            now + datetime.timedelta(seconds=59, milliseconds=420),
            now + datetime.timedelta(seconds=64, milliseconds=420),
        ]

    def test_when_counter_is_at_limit_from_only_locks(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=5, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )
        cooldown.increment(mock.Mock())
        cooldown.increment(mock.Mock())
        cooldown.increment(mock.Mock())
        cooldown.increment(mock.Mock())
        cooldown.increment(mock.Mock())

        with pytest.raises(tanjun.dependencies.CooldownDepleted) as exc:
            assert cooldown.check()

        assert exc.value.wait_until is None

    def test_when_counter_is_at_limit_from_only_unlocked_tracks(self):
        now = _now()
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=5, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )
        cooldown.resets = [
            now + datetime.timedelta(seconds=34, milliseconds=420),
            now + datetime.timedelta(seconds=46, milliseconds=420),
            now + datetime.timedelta(seconds=49, milliseconds=420),
            now + datetime.timedelta(seconds=59, milliseconds=420),
            now + datetime.timedelta(seconds=64, milliseconds=420),
        ]

        with pytest.raises(tanjun.dependencies.CooldownDepleted) as exc:
            assert cooldown.check()

        assert exc.value.wait_until == now + datetime.timedelta(seconds=34, milliseconds=420)

    def test_when_limit_is_negeative_1(self):
        cooldown = tanjun.dependencies.limiters._Cooldown(
            limit=-1, reset_after=datetime.timedelta(seconds=69, milliseconds=420)
        )

        cooldown.increment(mock.Mock())

        assert cooldown.locked == set()
        assert cooldown.resets == []
        assert cooldown.has_expired() is True
        assert cooldown.check()


class TestFlatResource:
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


class TestMemberResource:
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
            hikari.Snowflake(666): {hikari.Snowflake(4321123): mock.Mock(has_expired=mock.Mock(return_value=True))},
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


class TestGlobalResource:
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
            with pytest.raises(Exception, match=".*") as exc_info:
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
            open = mock_open  # noqa: VNE003

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
            open = mock_open  # noqa: VNE003

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
    async def test_try_acquire(self):
        mock_bucket = mock.AsyncMock()
        mock_ctx = mock.Mock()
        inner = mock_bucket.into_inner.return_value = mock.Mock()
        inner.check.return_value = inner.increment.return_value = inner
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._buckets["yeet me"] = mock_bucket

        await manager.try_acquire("yeet me", mock_ctx)

        mock_bucket.into_inner.assert_awaited_once_with(mock_ctx)
        inner.check.assert_called_once_with()
        inner.increment.assert_called_once_with(mock_ctx)
        assert manager._acquiring_ctxs[("yeet me", mock_ctx)] == inner

    @pytest.mark.asyncio()
    async def test_try_acquire_dedupes(self):
        mock_bucket = mock.AsyncMock()
        mock_ctx = mock.Mock()
        inner = mock_bucket.into_inner.return_value = mock.Mock()
        inner.check.return_value = inner.increment.return_value = inner
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._buckets["yeet me"] = mock_bucket

        await manager.try_acquire("yeet me", mock_ctx)
        await manager.try_acquire("yeet me", mock_ctx)

        mock_bucket.into_inner.assert_awaited_once_with(mock_ctx)
        inner.check.assert_called_once_with()
        inner.increment.assert_called_once_with(mock_ctx)
        assert manager._acquiring_ctxs[("yeet me", mock_ctx)] == inner

    @pytest.mark.asyncio()
    async def test_try_acquire_when_depleted(self):
        expected_error = tanjun.dependencies.CooldownDepleted(None)
        mock_bucket = mock.AsyncMock()
        mock_ctx = mock.Mock()
        inner = mock_bucket.into_inner.return_value = mock.Mock()
        inner.check.side_effect = expected_error
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._buckets["yeet me"] = mock_bucket

        with pytest.raises(tanjun.dependencies.CooldownDepleted) as exc:
            await manager.try_acquire("yeet me", mock_ctx)

        assert exc.value is expected_error
        mock_bucket.into_inner.assert_awaited_once_with(mock_ctx)
        inner.check.assert_called_once_with()
        inner.increment.assert_not_called()
        assert ("yeet me", mock_ctx) not in manager._acquiring_ctxs

    @pytest.mark.asyncio()
    async def test_try_acquire_falls_back_to_default(self):
        manager = tanjun.dependencies.InMemoryCooldownManager().set_bucket(
            "default", tanjun.dependencies.BucketResource.CHANNEL, 543, datetime.timedelta(50)
        )

        await manager.try_acquire("bucko", mock.Mock())

        assert isinstance(manager._buckets["bucko"], tanjun.dependencies.limiters._FlatResource)
        assert manager._buckets["bucko"].resource is tanjun.dependencies.BucketResource.CHANNEL
        bucket = manager._buckets["bucko"].make_resource()
        assert bucket.limit == 543
        assert bucket.reset_after == datetime.timedelta(50)

    @pytest.mark.asyncio()
    async def test_try_acquire_with_custom_bucket(self):
        mock_bucket = mock.AsyncMock()
        mock_context = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager().set_custom_bucket(mock_bucket, "meow meow")

        await manager.try_acquire("meow meow", mock_context)

        mock_bucket.try_acquire.assert_awaited_once_with("meow meow", mock_context)

    @pytest.mark.asyncio()
    async def test_release(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()
        mock_ctx = mock.Mock()
        mock_inner = mock.Mock()
        manager._acquiring_ctxs[("interesting!", mock_ctx)] = mock_inner

        await manager.release("interesting!", mock_ctx)

        assert ("interesting!", mock_ctx) not in manager._acquiring_ctxs
        mock_inner.unlock.assert_called_once_with(mock_ctx)

    @pytest.mark.asyncio()
    async def test_release_when_not_tracked(self):
        manager = tanjun.dependencies.InMemoryCooldownManager()

        with pytest.raises(tanjun.dependencies.ResourceNotTracked):
            await manager.release("oop", mock.Mock())

    @pytest.mark.asyncio()
    async def test_release_with_custom_bucket(self):
        mock_bucket = mock.AsyncMock()
        mock_context = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager().set_custom_bucket(mock_bucket, "meowers meowers")

        await manager.release("meowers meowers", mock_context)

        mock_bucket.release.assert_awaited_once_with("meowers meowers", mock_context)

    @pytest.mark.asyncio()
    async def test_check_cooldown(self):
        mock_bucket = mock.AsyncMock()
        mock_bucket.into_inner.return_value = mock.Mock()
        mock_ctx = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._buckets["echo"] = mock_bucket

        with pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("echo", mock_ctx)

        assert result is None
        mock_bucket.into_inner.assert_awaited_once_with(mock_ctx)
        mock_bucket.into_inner.return_value.check.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_for_acquired_context(self):
        mock_resource = mock.Mock()
        mock_ctx = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._acquiring_ctxs["mortal", mock_ctx] = mock_resource

        with pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("mortal", mock_ctx)

        assert result is None
        mock_resource.check.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_cooldown_depleted(self):
        date = _now()
        mock_bucket = mock.AsyncMock()
        mock_bucket.into_inner.return_value.check = mock.Mock(side_effect=tanjun.dependencies.CooldownDepleted(date))
        mock_ctx = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._buckets["meep"] = mock_bucket

        with pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("meep", mock_ctx)

        assert result is date
        mock_bucket.into_inner.assert_awaited_once_with(mock_ctx)
        mock_bucket.into_inner.return_value.check.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_for_acquired_context_when_cooldown_depleted(self):
        date = _now()
        mock_resource = mock.Mock()
        mock_resource.check.side_effect = tanjun.dependencies.CooldownDepleted(date)
        mock_ctx = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._acquiring_ctxs[("eeep", mock_ctx)] = mock_resource

        with pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("eeep", mock_ctx)

        assert result is date
        mock_resource.check.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_cooldown_depleted_unknown_wait_until(self):
        mock_bucket = mock.AsyncMock()
        mock_bucket.into_inner.return_value.check = mock.Mock(side_effect=tanjun.dependencies.CooldownDepleted(None))
        mock_ctx = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._buckets["flirt"] = mock_bucket

        date = datetime.datetime(2022, 5, 27, 23, 2, 40, 527391, tzinfo=datetime.timezone.utc)
        with freezegun.freeze_time(date), pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("flirt", mock_ctx)

        assert result == datetime.datetime(2022, 5, 27, 23, 3, 40, 527391, tzinfo=datetime.timezone.utc)
        mock_bucket.into_inner.assert_awaited_once_with(mock_ctx)
        mock_bucket.into_inner.return_value.check.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_for_acquired_context_when_cooldown_depleted_unknown_wait_until(self):
        mock_resource = mock.Mock()
        mock_resource.check.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_ctx = mock.Mock()
        manager = tanjun.dependencies.InMemoryCooldownManager()
        manager._acquiring_ctxs[("mother", mock_ctx)] = mock_resource

        date = datetime.datetime(2021, 5, 27, 23, 2, 40, 527391, tzinfo=datetime.timezone.utc)
        with freezegun.freeze_time(date), pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("mother", mock_ctx)

        assert result == datetime.datetime(2021, 5, 27, 23, 3, 40, 527391, tzinfo=datetime.timezone.utc)
        mock_resource.check.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_increment(self):
        mock_try_acquire = mock.AsyncMock()
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()

        class CooldownManager(tanjun.InMemoryCooldownManager):
            try_acquire = mock_try_acquire
            release = mock_release

        manager = CooldownManager()

        with pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("yeet", mock_ctx, increment=True)

        assert result is None
        mock_try_acquire.assert_awaited_once_with("yeet", mock_ctx)
        mock_release.assert_awaited_once_with("yeet", mock_ctx)

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_increment_and_cooldown_depleted(self):
        date = _now()
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.CooldownDepleted(date))
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()

        class CooldownManager(tanjun.InMemoryCooldownManager):
            try_acquire = mock_try_acquire
            release = mock_release

        manager = CooldownManager()

        with pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("yeet", mock_ctx, increment=True)

        assert result is date
        mock_try_acquire.assert_awaited_once_with("yeet", mock_ctx)
        mock_release.assert_not_called()

    @pytest.mark.asyncio()
    async def test_check_cooldown_when_increment_and_cooldown_depleted_with_unknown_wait_until(self):
        mock_try_acquire = mock.AsyncMock(side_effect=tanjun.dependencies.CooldownDepleted(None))
        mock_release = mock.AsyncMock()
        mock_ctx = mock.Mock()

        class CooldownManager(tanjun.InMemoryCooldownManager):
            try_acquire = mock_try_acquire
            release = mock_release

        manager = CooldownManager()

        date = datetime.datetime(2023, 5, 27, 23, 2, 40, 527391, tzinfo=datetime.timezone.utc)
        with freezegun.freeze_time(date), pytest.warns(DeprecationWarning, match="Use .acquire and .release"):
            result = await manager.check_cooldown("yeet", mock_ctx, increment=True)

        assert result == datetime.datetime(2023, 5, 27, 23, 3, 40, 527391, tzinfo=datetime.timezone.utc)
        mock_try_acquire.assert_awaited_once_with("yeet", mock_ctx)
        mock_release.assert_not_called()

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
        default_bucket = manager._default_bucket

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.disable_bucket("kitten")

            assert result is manager
            assert manager._buckets["kitten"] is cooldown_bucket.return_value
            assert manager._default_bucket is default_bucket

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

            manager._default_bucket("echo")

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._buckets["echo"] is cooldown_bucket.return_value

            assert cooldown_bucket.call_count == 2
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
        default_bucket = manager._default_bucket

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("gay catgirl", resource_type, 123, 43.123)

            assert result is manager
            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            assert manager._default_bucket is default_bucket

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

            manager._default_bucket("yeet")

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._buckets["yeet"] is cooldown_bucket.return_value

            assert cooldown_bucket.call_count == 2
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
        mock_cooldown_manager.try_acquire.return_value = None
        mock_owner_check = mock.AsyncMock()

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("yuri catgirls", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri catgirls", owners_exempt=True, error=mock.Mock())
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = True

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_not_called()
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_but_owner_check_is_none(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri catgirls", owners_exempt=True, error=mock.Mock())
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.return_value = None

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=None)

        mock_cooldown_manager.try_acquire.assert_called_once_with("yuri catgirls", mock_context)
        assert pre_execution._owners_exempt is False

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_and_not_owner(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls", owners_exempt=True, error=mock.Mock())
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.return_value = None
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls", mock_context)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_until(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2012, 1, 14, 12, 1, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(
            tanjun.CommandError, match="This command is currently in cooldown. Try again <t:1326542469:R>."
        ):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("yuri", mock_context)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_until_with_unknown_date(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(tanjun.CommandError, match="This command is currently in cooldown."):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("yuri", mock_context)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_until_and_error_callback(self):
        class MockException(Exception):
            ...

        mock_error_callback = mock.Mock(return_value=MockException())
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True, error=mock_error_callback)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2012, 1, 14, 12, 1, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(MockException):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("yuri", mock_context)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)
        mock_error_callback.assert_called_once_with(
            "yuri", datetime.datetime(2012, 1, 14, 12, 1, 9, 420000, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.asyncio()
    async def test_call_when_owners_exempt_still_leads_to_wait_until_and_error_callback_with_unknown_date(self):
        class MockException(Exception):
            ...

        mock_error_callback = mock.Mock(return_value=MockException())
        pre_execution = tanjun.dependencies.CooldownPreExecution("yuri", owners_exempt=True, error=mock_error_callback)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        mock_owner_check.check_ownership.return_value = False

        with pytest.raises(MockException):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("yuri", mock_context)
        mock_owner_check.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)
        mock_error_callback.assert_called_once_with("yuri", None)

    @pytest.mark.asyncio()
    async def test_call_when_wait_until(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls yuri", owners_exempt=False)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(
            tanjun.CommandError, match="This command is currently in cooldown. Try again <t:1452946089:R>."
        ):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_custom_message(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri", owners_exempt=False, error_message="Boopity boop {cooldown}."
        )
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="Boopity boop <t:1452946089:R>."):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="i am <t:1452946089:R> meow"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="meow meow <t:1452946089:R> nyaa"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="epic <t:1452946089:R> stones"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_wait_until_localised_by_localiser(self):
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
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

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
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

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
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

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
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
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(
            datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(MockException):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()
        mock_error_callback.assert_called_once_with(
            "catgirls yuri", datetime.datetime(2016, 1, 16, 12, 8, 9, 420000, tzinfo=datetime.timezone.utc)
        )

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution("catgirls yuri", owners_exempt=False)
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="This command is currently in cooldown."):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_custom_default(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri", owners_exempt=False, error_message="Boopers {cooldown}."
        )
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match=re.escape("Boopers ???.")):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_custom_message(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri", owners_exempt=False, unknown_message="Meep moop."
        )
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="Meep moop."):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_localised(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            unknown_message={hikari.Locale.CS: "yeet", hikari.Locale.FR: "eep", hikari.Locale.ES_ES: "i am meow"},
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.ES_ES
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="i am meow"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_localised_but_not_app_command_defaults(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            unknown_message={hikari.Locale.FR: "eep", "default": "meow meow nyaa", hikari.Locale.ES_ES: "i am meow"},
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="meow meow nyaa"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_localised_defaults(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            unknown_message={
                hikari.Locale.IT: "epic stones",
                hikari.Locale.FR: "meow meow nyaa",
                hikari.Locale.ES_ES: "i am meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.HR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match="epic stones"):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_localised_by_localiser(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            unknown_message={hikari.Locale.CS: "yeet", hikari.Locale.FR: "eep", hikari.Locale.ES_ES: "i am meow"},
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.FR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown_unknown",
            {hikari.Locale.BG: "yeep", hikari.Locale.FR: "i am nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match="i am nyaa"):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_localised_but_localiser_not_found(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            unknown_message={hikari.Locale.CS: "yeet", hikari.Locale.FR: "eep", hikari.Locale.ES_ES: "meow meow"},
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.ES_ES
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown_unknown",
            {hikari.Locale.BG: "yeep", hikari.Locale.FR: "i am nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match="meow meow"):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_defaults_with_localiser(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet",
                hikari.Locale.FR: "eep",
                "default": "echo echo foxtrot",
                hikari.Locale.ES_ES: "meow meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.PT_BR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown_unknown",
            {hikari.Locale.BG: "yeep", hikari.Locale.FR: "i am nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match="echo echo foxtrot"):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_fallback_localised(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet {cooldown}",
                hikari.Locale.FR: "eep {cooldown}",
                hikari.Locale.ES_ES: "i am meow {cooldown}",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.ES_ES
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match=re.escape("i am meow ???")):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_fallback_localised_but_not_app_command_defaults(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.FR: "eep {cooldown}",
                "default": "meow meow nyaa {cooldown}",
                hikari.Locale.ES_ES: "i am meow {cooldown}",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match=re.escape("meow meow nyaa ???")):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_fallback_localised_defaults(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.IT: "epic stones {cooldown}",
                hikari.Locale.FR: "meow meow nyaa {cooldown}",
                hikari.Locale.ES_ES: "i am meow {cooldown}",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.HR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(tanjun.CommandError, match=re.escape("epic stones ???")):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_fallback_localised_by_localiser(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet {cooldown}",
                hikari.Locale.FR: "eep {cooldown}",
                hikari.Locale.ES_ES: "i am meow {cooldown}",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.FR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown",
            {hikari.Locale.BG: "yeep {cooldown}", hikari.Locale.FR: "i am nyaa {cooldown}"},
        )

        with pytest.raises(tanjun.CommandError, match=re.escape("i am nyaa ???")):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_fallback_localised_but_localiser_not_found(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet {cooldown}",
                hikari.Locale.FR: "eep {cooldown}",
                hikari.Locale.ES_ES: "meow {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.ES_ES
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown",
            {hikari.Locale.BG: "yeep {cooldown}", hikari.Locale.FR: "i am {cooldown} nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match=re.escape("meow ??? meow")):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_fallback_defaults_with_localiser(self):
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri",
            error_message={
                hikari.Locale.CS: "yeet {cooldown}",
                hikari.Locale.FR: "eep {cooldown}",
                "default": "echo echo {cooldown} foxtrot",
                hikari.Locale.ES_ES: "meow {cooldown} meow",
            },
            owners_exempt=False,
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eep meow nyaa")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.PT_BR
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:eep meow nyaa:check:tanjun.cooldown",
            {hikari.Locale.BG: "yeep {cooldown}", hikari.Locale.FR: "i am {cooldown} nyaa"},
        )

        with pytest.raises(tanjun.CommandError, match=re.escape("echo echo ??? foxtrot")):
            await pre_execution(
                mock_context, cooldowns=mock_cooldown_manager, localiser=localiser, owner_check=mock_owner_check
            )

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()

    @pytest.mark.asyncio()
    async def test_call_when_unknown_wait_until_and_error_callback(self):
        class MockException(Exception):
            ...

        mock_error_callback = mock.Mock(return_value=MockException())
        pre_execution = tanjun.dependencies.CooldownPreExecution(
            "catgirls yuri", owners_exempt=False, error=mock_error_callback
        )
        mock_context = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.try_acquire.side_effect = tanjun.dependencies.CooldownDepleted(None)
        mock_owner_check = mock.AsyncMock()

        with pytest.raises(MockException):
            await pre_execution(mock_context, cooldowns=mock_cooldown_manager, owner_check=mock_owner_check)

        mock_cooldown_manager.try_acquire.assert_awaited_once_with("catgirls yuri", mock_context)
        mock_owner_check.check_ownership.assert_not_called()
        mock_error_callback.assert_called_once_with("catgirls yuri", None)


class TestCooldownPostExecution:
    @pytest.mark.asyncio()
    async def test_call(self):
        mock_ctx = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        post_execution = tanjun.dependencies.CooldownPostExecution("blam")

        await post_execution(mock_ctx, cooldowns=mock_cooldown_manager)

        mock_cooldown_manager.release.assert_awaited_once_with("blam", mock_ctx)

    @pytest.mark.asyncio()
    async def test_call_when_not_tracked(self):
        mock_ctx = mock.Mock()
        mock_cooldown_manager = mock.AsyncMock()
        mock_cooldown_manager.side_effect = tanjun.dependencies.ResourceNotTracked()
        post_execution = tanjun.dependencies.CooldownPostExecution("blam")

        await post_execution(mock_ctx, cooldowns=mock_cooldown_manager)

        mock_cooldown_manager.release.assert_awaited_once_with("blam", mock_ctx)


def test_with_cooldown():
    mock_command = mock.Mock()
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.dependencies.limiters, "CooldownPreExecution") as mock_pre_execution:
        tanjun.with_cooldown(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            owners_exempt=False,
            unknown_message="op",
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            owners_exempt=False,
            unknown_message="op",
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
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            owners_exempt=False,
            unknown_message="op op",
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            owners_exempt=False,
            unknown_message="op op",
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
            unknown_message="meow",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

    any_hooks.assert_has_calls([mock.call(), mock.call()])
    mock_hooks_1.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
    mock_hooks_2.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
    mock_pre_execution.assert_has_calls(
        [
            mock.call(
                "catgirl x catgirl",
                error=mock_error_callback,
                error_message="pussy cat pussy cat",
                unknown_message="meow",
                owners_exempt=False,
            )
        ]
        * 4
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
            unknown_message="odd",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            unknown_message="odd",
            owners_exempt=False,
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
            unknown_message="biggy",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

        mock_pre_execution.assert_called_once_with(
            "catgirl x catgirl",
            error=mock_error_callback,
            error_message="pussy cat pussy cat",
            unknown_message="biggy",
            owners_exempt=False,
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
            unknown_message="cab",
            follow_wrapped=True,
            owners_exempt=False,
        )(mock_command)

        mock_pre_execution.assert_has_calls(
            [
                mock.call(
                    "catgirl x catgirl",
                    error=mock_error_callback,
                    error_message="pussy cat pussy cat",
                    unknown_message="cab",
                    owners_exempt=False,
                )
            ]
            * 2
        )
        mock_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)
        mock_command.wrapped_command.hooks.add_pre_execution.assert_called_once_with(mock_pre_execution.return_value)


class TestConcurrencyLimit:
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

        limit.release("", mock.Mock())

        assert limit.counter == 1

    def test_release_when_not_acquired(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(2)

        with pytest.raises(RuntimeError, match="Cannot release a limit that has not been acquired"):
            limit.release("", mock.Mock())

    def test_release_when_limit_is_negative_1(self):
        limit = tanjun.dependencies.limiters._ConcurrencyLimit(-1)
        limit.counter = 0

        limit.release("", mock.Mock())

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
            with pytest.raises(Exception, match=".*") as exc_info:
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
            open = mock_open  # noqa: VNE003

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
            open = mock_open  # noqa: VNE003

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

        await manager.try_acquire("aye", mock_context)

        mock_bucket.into_inner.assert_called_once_with(mock_context)
        mock_inner.acquire.assert_called_once_with()
        assert manager._acquiring_ctxs[("aye", mock_context)] is mock_inner

    @pytest.mark.asyncio()
    async def test_try_acquire_with_custom_bucket(self):
        ...

    @pytest.mark.asyncio()
    async def test_try_acquire_when_failed_to_acquire(self):
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.acquire.return_value = False
        mock_context = mock.Mock()
        manager = tanjun.InMemoryConcurrencyLimiter()
        manager._buckets["nya"] = mock_bucket

        with pytest.raises(tanjun.dependencies.ResourceDepleted):
            await manager.try_acquire("nya", mock_context)

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

        await manager.try_acquire("ayee", mock_context)

        mock_bucket.into_inner.assert_not_called()
        mock_limiter.acquire.assert_not_called()
        assert manager._acquiring_ctxs[("ayee", mock_context)] is mock_limiter

    @pytest.mark.asyncio()
    async def test_try_acquire_falls_back_to_default_bucket(self):
        mock_bucket = mock.Mock(into_inner=mock.AsyncMock(return_value=mock.Mock()))
        mock_inner: typing.Any = mock_bucket.into_inner.return_value
        mock_inner.acquire.return_value = True
        mock_context = mock.Mock()
        manager = tanjun.InMemoryConcurrencyLimiter()
        manager._default_bucket = lambda name: manager._buckets.__setitem__(name, mock_bucket)

        await manager.try_acquire("yeet", mock_context)

        mock_bucket.into_inner.assert_called_once_with(mock_context)
        mock_inner.acquire.assert_called_once_with()
        assert manager._acquiring_ctxs[("yeet", mock_context)] is mock_inner
        assert manager._buckets["yeet"] is mock_bucket

    @pytest.mark.asyncio()
    async def test_release_with_custom_bucket(self):
        ...

    @pytest.mark.asyncio()
    async def test_release(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        mock_context = mock.Mock()
        mock_limiter = mock.Mock()
        manager._acquiring_ctxs[("nya", mock_context)] = mock_limiter

        await manager.release("nya", mock_context)

        assert ("nya", mock_context) not in manager._acquiring_ctxs
        mock_limiter.release.assert_called_once_with("nya", mock_context)

    @pytest.mark.asyncio()
    async def test_release_for_unknown_context(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        mock_context = mock.Mock()

        with pytest.raises(tanjun.dependencies.ResourceNotTracked):
            await manager.release("meow", mock_context)

    def test_disable_bucket(self):
        manager = tanjun.dependencies.InMemoryConcurrencyLimiter()
        default_bucket = manager._default_bucket

        with mock.patch.object(tanjun.dependencies.limiters, "_GlobalResource") as cooldown_bucket:
            result = manager.disable_bucket("kitty cat")

            assert result is manager
            assert manager._buckets["kitty cat"] is cooldown_bucket.return_value
            assert manager._default_bucket is default_bucket

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

            manager._default_bucket("bruce")

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._buckets["bruce"] is cooldown_bucket.return_value

            assert cooldown_bucket.call_count == 2
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
        default_bucket = manager._default_bucket

        with mock.patch.object(tanjun.dependencies.limiters, "_FlatResource") as cooldown_bucket:
            result = manager.set_bucket("gay catgirl", resource_type, 321)

            assert result is manager
            assert manager._buckets["gay catgirl"] is cooldown_bucket.return_value
            assert manager._default_bucket is default_bucket

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

            manager._default_bucket("beep")

            assert result is manager
            assert manager._buckets["default"] is cooldown_bucket.return_value
            assert manager._buckets["beep"] is cooldown_bucket.return_value

            assert cooldown_bucket.call_count == 2
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
        hook = tanjun.dependencies.ConcurrencyPreExecution("bucket boobs", error=KeyError)

        await hook(mock_context, mock_limiter)

        mock_limiter.try_acquire.assert_awaited_once_with("bucket boobs", mock_context)

    @pytest.mark.asyncio()
    async def test_call_when_acquire_fails(self):
        mock_context = mock.Mock()
        mock_limiter = mock.AsyncMock()
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:epic flintstones:check:tanjun.concurrency",
            {hikari.Locale.DA: "multiple messages", hikari.Locale.EN_GB: "ear", hikari.Locale.BG: "neat"},
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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
        mock_limiter.try_acquire.side_effect = tanjun.dependencies.ResourceDepleted
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

    @pytest.mark.asyncio()
    async def test_call_when_resource_not_tracked(self):
        mock_context = mock.Mock()
        mock_limiter = mock.AsyncMock(side_effect=tanjun.dependencies.ResourceNotTracked)
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
    pre_execution.assert_has_calls(
        [
            mock.call("bucket me", error=mock_error_callback, error_message="aye message"),
            mock.call("bucket me", error=mock_error_callback, error_message="aye message"),
            mock.call("bucket me", error=mock_error_callback, error_message="aye message"),
            mock.call("bucket me", error=mock_error_callback, error_message="aye message"),
        ]
    )
    post_execution.assert_has_calls(
        [mock.call("bucket me"), mock.call("bucket me"), mock.call("bucket me"), mock.call("bucket me")]
    )


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
    pre_execution.assert_has_calls(
        [
            mock.call("bucket me", error=mock_error_callback, error_message="aye message"),
            mock.call("bucket me", error=mock_error_callback, error_message="aye message"),
        ]
    )
    post_execution.assert_has_calls([mock.call("bucket me"), mock.call("bucket me")])
