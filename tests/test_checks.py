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

import typing
from unittest import mock

import hikari
import pytest

import tanjun


@pytest.fixture()
def command() -> tanjun.abc.ExecutableCommand[typing.Any]:
    command_ = mock.MagicMock(tanjun.abc.ExecutableCommand)
    command_.add_check.return_value = command_
    return command_


@pytest.fixture()
def context() -> tanjun.abc.Context:
    return mock.MagicMock(tanjun.abc.Context)


class TestOwnerCheck:
    @pytest.mark.asyncio()
    async def test(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = True
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, mock_dependency)

        assert result is True
        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_when_false(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, mock_dependency)

        assert result is False
        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_when_false_and_error_message(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message="aye", halt_execution=False)

        with pytest.raises(tanjun.errors.CommandError, match="aye"):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    @pytest.mark.asyncio()
    async def test_when_false_and_halt_execution(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message=None, halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)


class TestNsfwCheck:
    @pytest.mark.asyncio()
    async def test_when_is_dm(self):
        mock_context = mock.Mock(guild_id=None)
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_not_called()
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_async_cache_raises_not_found(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.EntryNotFound
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        with pytest.raises(tanjun.dependencies.EntryNotFound):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound_and_async_cache_hit(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = True
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_found_in_cache_and_async_cache_hit(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = None
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=None)

        assert result is True
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_found_in_cache(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_false(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = None
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=None)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_false_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = False
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.NsfwCheck(error_message="meow me", halt_execution=False)

        with pytest.raises(tanjun.errors.CommandError, match="meow me"):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_false_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=False)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)


class TestSfwCheck:
    @pytest.mark.asyncio()
    async def test_when_is_dm(self):
        mock_context = mock.Mock(guild_id=None)
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_not_called()
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = False
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound_and_async_cache_hit(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = False
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_found_in_cache_and_async_cache_hit(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = None
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=None)

        assert result is False
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_found_in_cache(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_is_nsfw(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context, channel_cache=None)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_is_nsfw_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.SfwCheck(error_message="meow me", halt_execution=False)

        with pytest.raises(tanjun.errors.CommandError, match="meow me"):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_is_nsfw_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)


class TestDmCheck:
    def test_for_dm(self):
        assert tanjun.checks.DmCheck()(mock.Mock(guild_id=None)) is True

    def test_for_guild(self):
        assert tanjun.checks.DmCheck(halt_execution=False, error_message=None)(mock.Mock(guild_id=3123)) is False

    def test_for_guild_when_halt_execution(self):
        with pytest.raises(tanjun.HaltExecution):
            assert tanjun.checks.DmCheck(halt_execution=True, error_message=None)(mock.Mock(guild_id=3123))

    def test_for_guild_when_error_message(self):
        with pytest.raises(tanjun.CommandError, match="message"):
            assert tanjun.checks.DmCheck(halt_execution=False, error_message="message")(mock.Mock(guild_id=3123))


class TestGuildCheck:
    def test_for_guild(self):
        assert tanjun.checks.GuildCheck()(mock.Mock(guild_id=123123)) is True

    def test_for_dm(self):
        assert tanjun.checks.GuildCheck(halt_execution=False, error_message=None)(mock.Mock(guild_id=None)) is False

    def test_for_dm_when_halt_execution(self):
        with pytest.raises(tanjun.HaltExecution):
            tanjun.checks.GuildCheck(halt_execution=True, error_message=None)(mock.Mock(guild_id=None))

    def test_for_dm_when_error_message(self):
        with pytest.raises(tanjun.CommandError, match="hi"):
            tanjun.checks.GuildCheck(halt_execution=False, error_message="hi")(mock.Mock(guild_id=None))


@pytest.mark.skip(reason="Not Implemented")
class TestAuthorPermissionCheck:
    ...


@pytest.mark.skip(reason="Not Implemented")
class TestOwnPermissionCheck:
    ...


def test_with_dm_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(halt_execution=False, error_message="Command can only be used in DMs")


def test_with_dm_check_with_keyword_arguments(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(halt_execution=True, error_message="message")(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(halt_execution=True, error_message="message")


def test_with_guild_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(
            halt_execution=False, error_message="Command can only be used in guild channels"
        )


def test_with_guild_check_with_keyword_arguments(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(halt_execution=True, error_message="eee")(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(halt_execution=True, error_message="eee")


def test_with_nsfw_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "NsfwCheck", return_value=mock.AsyncMock()) as nsfw_check:
        assert tanjun.checks.with_nsfw_check(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(
            halt_execution=False, error_message="Command can only be used in NSFW channels"
        )


def test_with_nsfw_check_with_keyword_arguments(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "NsfwCheck", return_value=mock.AsyncMock()) as nsfw_check:
        assert tanjun.checks.with_nsfw_check(halt_execution=True, error_message="banned!!!")(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(halt_execution=True, error_message="banned!!!")


def test_with_sfw_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "SfwCheck", return_value=mock.AsyncMock()) as sfw_check:
        assert tanjun.checks.with_sfw_check(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(
            halt_execution=False, error_message="Command can only be used in SFW channels"
        )


def test_with_sfw_check_with_keyword_arguments(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "SfwCheck", return_value=mock.AsyncMock()) as sfw_check:
        assert tanjun.checks.with_sfw_check(halt_execution=True, error_message="bango")(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(halt_execution=True, error_message="bango")


def test_with_owner_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "OwnerCheck") as owner_check:
        assert tanjun.checks.with_owner_check(command) is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(halt_execution=False, error_message="Only bot owners can use this command")


def test_with_owner_check_with_keyword_arguments(command: mock.Mock):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "OwnerCheck", return_value=mock_check) as owner_check:
        result = tanjun.checks.with_owner_check(
            halt_execution=True,
            error_message="dango",
        )(command)
        assert result is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(halt_execution=True, error_message="dango")


def test_with_author_permission_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        assert (
            tanjun.checks.with_author_permission_check(435213, halt_execution=True, error_message="bye")(command)
            is command
        )

        command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(435213, halt_execution=True, error_message="bye")


def test_with_own_permission_check(command: mock.Mock):
    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        assert (
            tanjun.checks.with_own_permission_check(5412312, halt_execution=True, error_message="hi")(command)
            is command
        )

        command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(5412312, halt_execution=True, error_message="hi")


def test_with_check(command: mock.Mock):
    mock_check = mock.Mock()

    result = tanjun.checks.with_check(mock_check)(command)

    assert result is command
    command.add_check.assert_called_once_with(mock_check)


@pytest.mark.asyncio()
async def test_all_checks():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(return_value=True)
    check = tanjun.checks.all_checks(mock_check_1, mock_check_2, mock_check_3)

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_all_checks_when_check_raises():
    class MockError(Exception):
        ...

    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[True, MockError])
    check = tanjun.checks.all_checks(mock_check_1, mock_check_2, mock_check_3)

    with pytest.raises(MockError):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [mock.call(mock_check_1, mock_context), mock.call(mock_check_2, mock_context)]
    )


@pytest.mark.asyncio()
async def test_all_checks_when_first_fails():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(return_value=False)
    check = tanjun.checks.all_checks(mock_check_1, mock_check_2, mock_check_3)

    result = await check(mock_context)

    assert result is False
    mock_context.call_with_async_di.assert_awaited_once_with(mock_check_1, mock_context)


@pytest.mark.asyncio()
async def test_all_checks_when_last_fails():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[True, True, False])
    check = tanjun.checks.all_checks(mock_check_1, mock_check_2, mock_check_3)

    result = await check(mock_context)

    assert result is False
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_all_checks_when_any_check_fails():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_check_4 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[True, False, True, True])
    check = tanjun.checks.all_checks(mock_check_1, mock_check_2, mock_check_3, mock_check_4)

    result = await check(mock_context)

    assert result is False
    mock_context.call_with_async_di.assert_has_awaits(
        [mock.call(mock_check_1, mock_context), mock.call(mock_check_2, mock_context)]
    )


def test_with_all_checks():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_command = mock.Mock()

    with mock.patch.object(tanjun.checks, "all_checks") as all_checks:
        result = tanjun.with_all_checks(mock_check_1, mock_check_2, mock_check_3)(mock_command)

    assert result is mock_command.add_check.return_value
    mock_command.add_check.assert_called_once_with(all_checks.return_value)
    all_checks.assert_called_once_with(mock_check_1, mock_check_2, mock_check_3)


@pytest.mark.asyncio()
async def test_any_checks_when_first_check_passes():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(return_value=True)
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message="hi")

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_awaited_once_with(mock_check_1, mock_context)


@pytest.mark.asyncio()
async def test_any_checks_when_last_check_passes():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.FailedCheck, True])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message="hi")

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_check_passes():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_check_4 = mock.Mock()
    mock_check_5 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.FailedCheck, False, True])
    check = tanjun.checks.any_checks(
        mock_check_1, mock_check_2, mock_check_3, mock_check_4, mock_check_5, error_message="hi"
    )

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
            mock.call(mock_check_4, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.FailedCheck, False])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None)

    result = await check(mock_context)

    assert result is False
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_halt_execution():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, False, tanjun.FailedCheck])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None, halt_execution=True)

    with pytest.raises(tanjun.HaltExecution):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message="aye")

    with pytest.raises(tanjun.CommandError, match="aye"):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_generic_unsuppressed_error_raised():
    class MockError(Exception):
        ...

    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, MockError])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None)

    with pytest.raises(MockError):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [mock.call(mock_check_1, mock_context), mock.call(mock_check_2, mock_context)]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_generic_error_suppressed():
    class MockError(Exception):
        ...

    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, MockError, True])
    check = tanjun.checks.any_checks(
        mock_check_1, mock_check_2, mock_check_3, error_message=None, suppress=(MockError,)
    )

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_halt_execution_not_suppressed():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.HaltExecution])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None, suppress=())

    with pytest.raises(tanjun.HaltExecution):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [mock.call(mock_check_1, mock_context), mock.call(mock_check_2, mock_context)]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_halt_execution_suppressed():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.HaltExecution, True])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None)

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_command_error_not_suppressed():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.CommandError("bye")])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None, suppress=())

    with pytest.raises(tanjun.CommandError, match="bye"):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [mock.call(mock_check_1, mock_context), mock.call(mock_check_2, mock_context)]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_command_error_suppressed():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.CommandError("bye"), True])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message=None)

    result = await check(mock_context)

    assert result is True
    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


def test_with_any_checks():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_command = mock.Mock()

    class MockError(Exception):
        ...

    with mock.patch.object(tanjun.checks, "any_checks") as any_checks:
        result = tanjun.checks.with_any_checks(
            mock_check_1,
            mock_check_2,
            mock_check_3,
            suppress=(MockError,),
            error_message="yay catgirls",
            halt_execution=True,
        )(mock_command)

    assert result is mock_command.add_check.return_value
    mock_command.add_check.assert_called_once_with(any_checks.return_value)
    any_checks.assert_called_once_with(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message="yay catgirls",
        suppress=(MockError,),
        halt_execution=True,
    )
