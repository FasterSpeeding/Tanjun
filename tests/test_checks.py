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


class TestInjectableCheck:
    @pytest.mark.asyncio()
    async def test(self):
        mock_callback = mock.Mock()
        mock_context = mock.Mock()

        with mock.patch.object(
            tanjun.injecting, "CallbackDescriptor", return_value=mock.AsyncMock()
        ) as callback_descriptor:
            check = tanjun.checks.InjectableCheck(mock_callback)

            callback_descriptor.assert_called_once_with(mock_callback)

        result = await check(mock_context)

        assert result is callback_descriptor.return_value.resolve_with_command_context.return_value
        callback_descriptor.return_value.resolve_with_command_context.assert_awaited_once_with(
            mock_context, mock_context
        )

    @pytest.mark.asyncio()
    async def test_when_returns_false(self):
        mock_callback = mock.Mock()
        mock_context = mock.Mock()
        mock_descriptor = mock.AsyncMock()
        mock_descriptor.resolve_with_command_context.return_value = False

        with mock.patch.object(
            tanjun.injecting, "CallbackDescriptor", return_value=mock_descriptor
        ) as callback_descriptor:
            check = tanjun.checks.InjectableCheck(mock_callback)

            callback_descriptor.assert_called_once_with(mock_callback)

        with pytest.raises(tanjun.errors.FailedCheck):
            await check(mock_context)

        mock_descriptor.resolve_with_command_context.assert_awaited_once_with(mock_context, mock_context)


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
    async def test(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_rest_returns_dm(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.DMChannel)
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound_when_not_found_in_cache(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_false(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = None
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_false_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = False
        check = tanjun.checks.NsfwCheck(error_message="meow me", halt_execution=False)

        with pytest.raises(tanjun.errors.CommandError, match="meow me"):
            await check(mock_context)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_false_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=False)
        check = tanjun.checks.NsfwCheck(error_message=None, halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)


class TestSfwCheck:
    @pytest.mark.asyncio()
    async def test(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = False
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=False)
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_rest_returns_dm(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.DMChannel, is_nsfw=False)
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_not_cache_bound_when_not_found_in_cache(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=None)
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    @pytest.mark.asyncio()
    async def test_when_false(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=False)

        result = await check(mock_context)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_false_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        check = tanjun.checks.SfwCheck(error_message="meow me", halt_execution=False)

        with pytest.raises(tanjun.errors.CommandError, match="meow me"):
            await check(mock_context)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_when_false_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.SfwCheck(error_message=None, halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)


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
