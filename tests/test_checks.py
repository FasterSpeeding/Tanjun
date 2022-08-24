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

import functools
import itertools
import operator
import typing
from collections import abc as collections
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


@pytest.mark.asyncio()
class TestOwnerCheck:
    async def test(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = True
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error=TypeError, error_message="yeet", halt_execution=True)

        result = await check(mock_context, mock_dependency)

        assert result is True
        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message=None)

        result = await check(mock_context, mock_dependency)

        assert result is False
        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error=MockException, error_message="hi")

        with pytest.raises(MockException):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message="aye")

        with pytest.raises(tanjun.errors.CommandError, match="aye"):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_halt_execution(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock()
        check = tanjun.checks.OwnerCheck(error_message="eeep", halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)


@pytest.mark.asyncio()
class TestNsfwCheck:
    async def test_when_is_dm(self):
        mock_context = mock.Mock(guild_id=None)
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.NsfwCheck(error=TypeError, error_message="meep", halt_execution=True)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_not_called()
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    async def test(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.NsfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    async def test_when_async_cache_raises_not_found(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.EntryNotFound
        check = tanjun.checks.NsfwCheck(error_message=None)

        with pytest.raises(tanjun.dependencies.EntryNotFound):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    async def test_when_not_cache_bound_and_async_cache_hit(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = True
        check = tanjun.checks.NsfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    async def test_when_not_found_in_cache_and_async_cache_hit(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = None
        check = tanjun.checks.NsfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    async def test_when_not_cache_bound(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.NsfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=None)

        assert result is True
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    async def test_when_not_found_in_cache(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.NsfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)

    async def test_when_false(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = None
        check = tanjun.checks.NsfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=None)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    async def test_when_false_when_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = None
        check = tanjun.checks.NsfwCheck(error=MockException, error_message="nye")

        with pytest.raises(MockException):
            await check(mock_context, channel_cache=None)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    async def test_when_false_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = False
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.NsfwCheck(error_message="meow me")

        with pytest.raises(tanjun.errors.CommandError, match="meow me"):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    async def test_when_false_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=False)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.NsfwCheck(error_message="yeet", halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)


@pytest.mark.asyncio()
class TestSfwCheck:
    async def test_when_is_dm(self):
        mock_context = mock.Mock(guild_id=None)
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.SfwCheck(error=ValueError, error_message="lll", halt_execution=True)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_not_called()
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    async def test(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = False
        mock_cache = mock.AsyncMock()
        check = tanjun.checks.SfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    async def test_when_not_cache_bound_and_async_cache_hit(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = False
        check = tanjun.checks.SfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    async def test_when_not_found_in_cache_and_async_cache_hit(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_cache = mock.AsyncMock()
        mock_cache.get.return_value.is_nsfw = None
        check = tanjun.checks.SfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is True
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_called_once_with(mock_context.channel_id)

    async def test_when_not_cache_bound(self):
        mock_context = mock.Mock(cache=None, rest=mock.AsyncMock())
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        check = tanjun.checks.SfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=None)

        assert result is False
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)

    async def test_when_not_found_in_cache(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.SfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=mock_cache)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)

    async def test_when_is_nsfw(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        check = tanjun.checks.SfwCheck(error_message=None)

        result = await check(mock_context, channel_cache=None)

        assert result is False
        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    async def test_when_is_nsfw_and_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        check = tanjun.checks.SfwCheck(error=MockException, error_message="bye")

        with pytest.raises(MockException):
            await check(mock_context, channel_cache=None)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()

    async def test_when_is_nsfw_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.cache.get_guild_channel.return_value.is_nsfw = True
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.SfwCheck(error_message="meow me")

        with pytest.raises(tanjun.errors.CommandError, match="meow me"):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_not_called()
        mock_cache.get.assert_not_called()

    async def test_when_is_nsfw_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.return_value = mock.Mock(hikari.GuildChannel, is_nsfw=True)
        mock_cache = mock.AsyncMock()
        mock_cache.get.side_effect = tanjun.dependencies.CacheMissError
        check = tanjun.checks.SfwCheck(error_message="yeet", halt_execution=True)

        with pytest.raises(tanjun.errors.HaltExecution):
            await check(mock_context, channel_cache=mock_cache)

        mock_context.cache.get_guild_channel.assert_called_once_with(mock_context.channel_id)
        mock_context.rest.fetch_channel.assert_awaited_once_with(mock_context.channel_id)
        mock_cache.get.assert_awaited_once_with(mock_context.channel_id)


class TestDmCheck:
    def test_for_dm(self):
        check = tanjun.checks.DmCheck(error=ValueError, error_message="meow", halt_execution=True)
        assert check(mock.Mock(guild_id=None)) is True

    def test_for_guild(self):
        assert tanjun.checks.DmCheck(error_message=None)(mock.Mock(guild_id=3123)) is False

    def test_for_guild_when_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        check = tanjun.checks.DmCheck(error=MockException, error_message="meow")

        with pytest.raises(MockException):
            assert check(mock.Mock(guild_id=3123))

    def test_for_guild_when_halt_execution(self):
        with pytest.raises(tanjun.HaltExecution):
            assert tanjun.checks.DmCheck(error_message="beep", halt_execution=True)(mock.Mock(guild_id=3123))

    def test_for_guild_when_error_message(self):
        with pytest.raises(tanjun.CommandError, match="message"):
            assert tanjun.checks.DmCheck(error_message="message")(mock.Mock(guild_id=3123))


class TestGuildCheck:
    def test_for_guild(self):
        check = tanjun.checks.GuildCheck(error=IndentationError, error_message="meow", halt_execution=True)

        assert check(mock.Mock(guild_id=123123)) is True

    def test_for_dm(self):
        assert tanjun.checks.GuildCheck(error_message=None)(mock.Mock(guild_id=None)) is False

    def test_for_dm_when_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        check = tanjun.checks.GuildCheck(error=MockException, error_message="meep")

        with pytest.raises(MockException):
            assert check(mock.Mock(guild_id=None))

    def test_for_dm_when_halt_execution(self):
        with pytest.raises(tanjun.HaltExecution):
            tanjun.checks.GuildCheck(error_message="beep", halt_execution=True)(mock.Mock(guild_id=None))

    def test_for_dm_when_error_message(self):
        with pytest.raises(tanjun.CommandError, match="hi"):
            tanjun.checks.GuildCheck(error_message="hi")(mock.Mock(guild_id=None))


def _perm_combos(perms: hikari.Permissions) -> collections.Iterator[hikari.Permissions]:
    for index in range(1, len(perms) + 1):
        yield from (functools.reduce(operator.ior, v) for v in itertools.combinations(perms, index))


MISSING_PERMISSIONS = (
    ("required_perms", "actual_perms", "missing_perms"),
    [
        (
            hikari.Permissions.all_permissions() & ~hikari.Permissions.ADMINISTRATOR,
            hikari.Permissions.all_permissions()
            & ~hikari.Permissions.CREATE_INSTANT_INVITE
            & ~hikari.Permissions.MANAGE_GUILD,
            hikari.Permissions.CREATE_INSTANT_INVITE | hikari.Permissions.MANAGE_GUILD,
        ),
        (
            _p := hikari.Permissions.REQUEST_TO_SPEAK
            | hikari.Permissions.SEND_MESSAGES_IN_THREADS
            | hikari.Permissions.CONNECT
            | hikari.Permissions.CHANGE_NICKNAME,
            hikari.Permissions.KICK_MEMBERS | hikari.Permissions.DEAFEN_MEMBERS | hikari.Permissions.SEND_MESSAGES,
            _p,
        ),
        (
            hikari.Permissions.ADD_REACTIONS
            | hikari.Permissions.CHANGE_NICKNAME
            | hikari.Permissions.CONNECT
            | hikari.Permissions.EMBED_LINKS,
            hikari.Permissions.EMBED_LINKS
            | hikari.Permissions.MANAGE_EMOJIS_AND_STICKERS
            | hikari.Permissions.MANAGE_ROLES,
            hikari.Permissions.ADD_REACTIONS | hikari.Permissions.CONNECT | hikari.Permissions.CHANGE_NICKNAME,
        ),
        (
            hikari.Permissions.all_permissions() & ~hikari.Permissions.ADMINISTRATOR,
            hikari.Permissions.all_permissions()
            & ~hikari.Permissions.MODERATE_MEMBERS
            & ~hikari.Permissions.ATTACH_FILES,
            hikari.Permissions.MODERATE_MEMBERS | hikari.Permissions.ATTACH_FILES,
        ),
        (
            _p := hikari.Permissions.ADD_REACTIONS
            | hikari.Permissions.SEND_MESSAGES
            | hikari.Permissions.ATTACH_FILES
            | hikari.Permissions.ATTACH_FILES,
            hikari.Permissions.KICK_MEMBERS
            | hikari.Permissions.DEAFEN_MEMBERS
            | hikari.Permissions.SEND_MESSAGES_IN_THREADS,
            _p,
        ),
        (
            hikari.Permissions.SEND_MESSAGES_IN_THREADS
            | hikari.Permissions.SEND_MESSAGES
            | hikari.Permissions.BAN_MEMBERS
            | hikari.Permissions.CREATE_PRIVATE_THREADS,
            hikari.Permissions.SEND_MESSAGES_IN_THREADS
            | hikari.Permissions.MANAGE_CHANNELS
            | hikari.Permissions.MANAGE_GUILD
            | hikari.Permissions.BAN_MEMBERS,
            hikari.Permissions.SEND_MESSAGES | hikari.Permissions.CREATE_PRIVATE_THREADS,
        ),
    ],
)

INVALID_DM_PERMISSIONS = (
    "required_perms",
    [
        v if i % 2 else v | hikari.Permissions.SEND_MESSAGES
        # a few guild-only permissions
        for i, v in enumerate(
            _perm_combos(
                hikari.Permissions.ADMINISTRATOR
                | hikari.Permissions.BAN_MEMBERS
                | hikari.Permissions.MANAGE_EMOJIS_AND_STICKERS
            )
        )
    ],
)

MISSING_DM_PERMISSIONS = (
    ("required_perms", "missing_perms"),
    [
        (
            hikari.Permissions.all_permissions(),
            hikari.Permissions.all_permissions() & ~tanjun.permissions.DM_PERMISSIONS,
        ),
        (
            _p := hikari.Permissions.MANAGE_CHANNELS
            | hikari.Permissions.MANAGE_EMOJIS_AND_STICKERS
            | hikari.Permissions.KICK_MEMBERS,
            _p,
        ),
        (
            hikari.Permissions.ADD_REACTIONS | hikari.Permissions.MANAGE_GUILD | hikari.Permissions.CONNECT,
            hikari.Permissions.MANAGE_GUILD | hikari.Permissions.CONNECT,
        ),
    ],
)


PERMISSIONS = (
    ("required_perms", "actual_perms"),
    [
        (
            p := hikari.Permissions.ADD_REACTIONS | hikari.Permissions.USE_EXTERNAL_EMOJIS,
            p | hikari.Permissions.ADMINISTRATOR,
        ),
        (p := hikari.Permissions.ATTACH_FILES | hikari.Permissions.BAN_MEMBERS, p),
        (p := hikari.Permissions.CHANGE_NICKNAME, p),
        (hikari.Permissions.all_permissions(), hikari.Permissions.all_permissions()),
        (
            p := hikari.Permissions.all_permissions()
            & ~hikari.Permissions.ADD_REACTIONS
            & ~hikari.Permissions.ATTACH_FILES,
            p,
        ),
        (hikari.Permissions.NONE, hikari.Permissions.ADD_REACTIONS | hikari.Permissions.CREATE_INSTANT_INVITE),
    ],
)

DM_PERMISSIONS = ("required_perms", list(_perm_combos(tanjun.permissions.DM_PERMISSIONS)))


@pytest.mark.asyncio()
class TestAuthorPermissionCheck:
    @pytest.mark.parametrize(*PERMISSIONS)
    async def test(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock()
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock.Mock(), halt_execution=True)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.member, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock()
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(
            tanjun.permissions,
            "fetch_permissions",
            return_value=actual_perms,
        ) as fetch_permissions:
            result = await check(mock_context)

        assert result is False
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.member, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock()
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context)

        mock_error_callback.assert_called_once_with(missing_perms)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.member, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock()
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message="yeet feet")

        with pytest.raises(tanjun.CommandError, match="yeet feet"), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.member, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock()
        check = tanjun.checks.AuthorPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.member, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_for_interaction_member(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(member=mock.Mock(hikari.InteractionMember, permissions=actual_perms))
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock.Mock(), halt_execution=True)

        result = await check(mock_context)

        assert result is True

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(member=mock.Mock(hikari.InteractionMember, permissions=actual_perms))
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message=None)

        result = await check(mock_context)

        assert result is False

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(member=mock.Mock(hikari.InteractionMember, permissions=actual_perms))
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError):
            await check(mock_context)

        mock_error_callback.assert_called_once_with(missing_perms)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(member=mock.Mock(hikari.InteractionMember, permissions=actual_perms))
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message="yeet feet")

        with pytest.raises(tanjun.CommandError, match="yeet feet"):
            await check(mock_context)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(member=mock.Mock(hikari.InteractionMember, permissions=actual_perms))
        check = tanjun.checks.AuthorPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution):
            await check(mock_context)

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_for_guild_user(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock.Mock(), halt_execution=True)

        with mock.patch.object(
            tanjun.permissions, "fetch_everyone_permissions", return_value=actual_perms
        ) as fetch_everyone_permissions:
            result = await check(mock_context)

        assert result is True
        fetch_everyone_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.guild_id, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_guild_user_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(
            tanjun.permissions, "fetch_everyone_permissions", return_value=actual_perms
        ) as fetch_everyone_permissions:
            result = await check(mock_context)

        assert result is False
        fetch_everyone_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.guild_id, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_guild_user_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(
            tanjun.permissions, "fetch_everyone_permissions", return_value=actual_perms
        ) as fetch_everyone_permissions:
            await check(mock_context)

        mock_error_callback.assert_called_once_with(missing_perms)
        fetch_everyone_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.guild_id, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_guild_user_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message="beat yo meow")

        with pytest.raises(tanjun.CommandError, match="beat yo meow"), mock.patch.object(
            tanjun.permissions, "fetch_everyone_permissions", return_value=actual_perms
        ) as fetch_everyone_permissions:
            await check(mock_context)

        fetch_everyone_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.guild_id, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_guild_user_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_everyone_permissions", return_value=actual_perms
        ) as fetch_everyone_permissions:
            await check(mock_context)

        fetch_everyone_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.guild_id, channel=mock_context.channel_id
        )

    @pytest.mark.parametrize(*DM_PERMISSIONS)
    async def test_for_dm(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(guild_id=None, member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock.Mock(), halt_execution=True)

        result = await check(mock_context)

        assert result is True

    @pytest.mark.parametrize(*INVALID_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(guild_id=None, member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message=None)

        result = await check(mock_context)

        assert result is False

    @pytest.mark.parametrize(*MISSING_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(guild_id=None, member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError):
            await check(mock_context)

        mock_error_callback.assert_called_once_with(missing_perms)

    @pytest.mark.parametrize(*INVALID_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms_and_error_message(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(guild_id=None, member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, error_message="aye lmao")

        with pytest.raises(tanjun.CommandError, match="aye lmao"):
            await check(mock_context)

    @pytest.mark.parametrize(*INVALID_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms_and_halt_execution(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(guild_id=None, member=None)
        check = tanjun.checks.AuthorPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution):
            await check(mock_context)


@pytest.mark.asyncio()
class TestOwnPermissionCheck:
    @pytest.mark.parametrize(*PERMISSIONS)
    async def test(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_when_no_cache(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_when_no_async_cache(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=None, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_when_no_caches(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=None, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is False
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        mock_error_callback.assert_called_once_with(missing_perms)
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message="meow meow")

        with pytest.raises(tanjun.CommandError, match="meow meow"), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.rest.fetch_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id)

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_for_cached_member(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.cache.get_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_cached_member_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is False
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.cache.get_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_cached_member_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        mock_error_callback.assert_called_once_with(missing_perms)
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.cache.get_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_cached_member_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message="meowth")

        with pytest.raises(tanjun.CommandError, match="meowth"), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.cache.get_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_cached_member_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_context.cache.get_member.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_for_async_cached_member(self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_member_cache.get_from_guild.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_async_cached_member_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(tanjun.permissions, "fetch_permissions", return_value=actual_perms) as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is False
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_member_cache.get_from_guild.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_async_cached_member_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        mock_error_callback.assert_called_once_with(missing_perms)
        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_member_cache.get_from_guild.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_async_cached_member_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message="nom")

        with pytest.raises(tanjun.CommandError, match="nom"), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_member_cache.get_from_guild.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_async_cached_member_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_permissions", return_value=actual_perms
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_awaited_once_with(
            mock_context.client, mock_member_cache.get_from_guild.return_value, channel=mock_context.channel_id
        )
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, mock_own_user)
        mock_member_cache.get_from_guild.assert_awaited_once_with(mock_context.guild_id, mock_own_user.id, default=None)
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.SlashContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions") as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.SlashContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(tanjun.permissions, "fetch_permissions") as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is False
        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(tanjun.abc.SlashContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(tanjun.permissions, "fetch_permissions") as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        mock_error_callback.assert_called_once_with(missing_perms)
        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.SlashContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message="bees")

        with pytest.raises(tanjun.CommandError, match="bees"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.SlashContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*DM_PERMISSIONS)
    async def test_for_dm(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=None)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms)

        with mock.patch.object(tanjun.permissions, "fetch_permissions") as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is True
        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*INVALID_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=None)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message=None)

        with mock.patch.object(tanjun.permissions, "fetch_permissions") as fetch_permissions:
            result = await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        assert result is False
        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms_and_error_callback(
        self, required_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        class StubError(Exception):
            ...

        mock_error_callback = mock.Mock(side_effect=StubError)
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=None)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error=mock_error_callback)

        with pytest.raises(StubError), mock.patch.object(tanjun.permissions, "fetch_permissions") as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        mock_error_callback.assert_called_once_with(missing_perms)
        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*INVALID_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms_and_error_message(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=None)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, error_message="beep")

        with pytest.raises(tanjun.CommandError, match="beep"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*INVALID_DM_PERMISSIONS)
    async def test_for_dm_when_missing_perms_and_halt_execution(self, required_perms: hikari.Permissions):
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=None)
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(required_perms, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()


def test_with_dm_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(
            error=None, error_message="Command can only be used in DMs", halt_execution=False
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_dm_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        result = tanjun.checks.with_dm_check(error=mock_error_callback, error_message="message", halt_execution=True)(
            command
        )

        assert result is command
        command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(
            error=mock_error_callback,
            error_message="message",
            halt_execution=True,
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_dm_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(dm_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(
            error=None, error_message="Command can only be used in DMs", halt_execution=False
        )


def test_with_dm_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(
            error=None, error_message="Command can only be used in DMs", halt_execution=False
        )


def test_with_dm_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.MessageCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(
            error=None, error_message="Command can only be used in DMs", halt_execution=False
        )


def test_with_dm_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "DmCheck") as dm_check:
        assert tanjun.checks.with_dm_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(dm_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(dm_check.return_value)
        dm_check.assert_called_once_with(
            error=None, error_message="Command can only be used in DMs", halt_execution=False
        )


def test_with_guild_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(
            error=None, error_message="Command can only be used in guild channels", halt_execution=False
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_guild_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert (
            tanjun.checks.with_guild_check(error=mock_error_callback, error_message="eee", halt_execution=True)(command)
            is command
        )

        command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(error=mock_error_callback, error_message="eee", halt_execution=True)
        command.wrapped_command.add_check.assert_not_called()


def test_with_guild_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(guild_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(
            error=None, error_message="Command can only be used in guild channels", halt_execution=False
        )


def test_with_guild_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(
            error=None, error_message="Command can only be used in guild channels", halt_execution=False
        )


def test_with_guild_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(
            error=None, error_message="Command can only be used in guild channels", halt_execution=False
        )


def test_with_guild_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "GuildCheck") as guild_check:
        assert tanjun.checks.with_guild_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(guild_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(guild_check.return_value)
        guild_check.assert_called_once_with(
            error=None, error_message="Command can only be used in guild channels", halt_execution=False
        )


def test_with_nsfw_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "NsfwCheck", return_value=mock.AsyncMock()) as nsfw_check:
        assert tanjun.checks.with_nsfw_check(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in NSFW channels", halt_execution=False
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_nsfw_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.checks, "NsfwCheck", return_value=mock.AsyncMock()) as nsfw_check:
        result = tanjun.checks.with_nsfw_check(
            error=mock_error_callback, error_message="banned!!!", halt_execution=True
        )(command)

        assert result is command
        command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(error=mock_error_callback, error_message="banned!!!", halt_execution=True)
        command.wrapped_command.add_check.assert_not_called()


def test_with_nsfw_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "NsfwCheck") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(nsfw_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in NSFW channels", halt_execution=False
        )


def test_with_nsfw_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "NsfwCheck") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in NSFW channels", halt_execution=False
        )


def test_with_nsfw_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "NsfwCheck") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in NSFW channels", halt_execution=False
        )


def test_with_nsfw_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "NsfwCheck") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(nsfw_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(nsfw_check.return_value)
        nsfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in NSFW channels", halt_execution=False
        )


def test_with_sfw_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "SfwCheck", return_value=mock.AsyncMock()) as sfw_check:
        assert tanjun.checks.with_sfw_check(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in SFW channels", halt_execution=False
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_sfw_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.checks, "SfwCheck", return_value=mock.AsyncMock()) as sfw_check:
        result = tanjun.checks.with_sfw_check(error=mock_error_callback, error_message="bango", halt_execution=True)(
            command
        )

        assert result is command
        command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(error=mock_error_callback, error_message="bango", halt_execution=True)
        command.wrapped_command.add_check.assert_not_called()


def test_with_sfw_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "SfwCheck") as sfw_check:
        assert tanjun.checks.with_sfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(sfw_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in SFW channels", halt_execution=False
        )


def test_with_sfw_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "SfwCheck") as sfw_check:
        assert tanjun.checks.with_sfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in SFW channels", halt_execution=False
        )


def test_with_sfw_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "SfwCheck") as sfw_check:
        assert tanjun.checks.with_sfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in SFW channels", halt_execution=False
        )


def test_with_sfw_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "SfwCheck") as sfw_check:
        assert tanjun.checks.with_sfw_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(sfw_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(sfw_check.return_value)
        sfw_check.assert_called_once_with(
            error=None, error_message="Command can only be used in SFW channels", halt_execution=False
        )


def test_with_owner_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "OwnerCheck") as owner_check:
        assert tanjun.checks.with_owner_check(command) is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(
            error=None, error_message="Only bot owners can use this command", halt_execution=False
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_owner_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()
    mock_check = object()
    with mock.patch.object(tanjun.checks, "OwnerCheck", return_value=mock_check) as owner_check:
        result = tanjun.checks.with_owner_check(
            error=mock_error_callback,
            error_message="dango",
            halt_execution=True,
        )(command)
        assert result is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(error=mock_error_callback, error_message="dango", halt_execution=True)
        command.wrapped_command.add_check.assert_not_called()


def test_with_owner_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "OwnerCheck") as owner_check:
        assert tanjun.checks.with_owner_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(owner_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(
            error=None, error_message="Only bot owners can use this command", halt_execution=False
        )


def test_with_owner_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "OwnerCheck") as owner_check:
        assert tanjun.checks.with_owner_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(
            error=None, error_message="Only bot owners can use this command", halt_execution=False
        )


def test_with_owner_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "OwnerCheck") as owner_check:
        assert tanjun.checks.with_owner_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(
            error=None, error_message="Only bot owners can use this command", halt_execution=False
        )


def test_with_owner_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "OwnerCheck") as owner_check:
        assert tanjun.checks.with_owner_check(follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(owner_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(owner_check.return_value)
        owner_check.assert_called_once_with(
            error=None, error_message="Only bot owners can use this command", halt_execution=False
        )


def test_with_author_permission_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        result = tanjun.checks.with_author_permission_check(435213)(command)

        assert result is command
        command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(
            435213,
            error=None,
            error_message="You don't have the permissions required to use this command",
            halt_execution=False,
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_author_permission_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        result = tanjun.checks.with_author_permission_check(
            435213, error=mock_error_callback, error_message="bye", halt_execution=True
        )(command)

        assert result is command
        command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(
            435213, error=mock_error_callback, error_message="bye", halt_execution=True
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_author_permission_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        assert tanjun.checks.with_author_permission_check(435213, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(author_permission_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(author_permission_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(
            435213,
            error=None,
            error_message="You don't have the permissions required to use this command",
            halt_execution=False,
        )


def test_with_author_permission_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        assert tanjun.checks.with_author_permission_check(435213, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(
            435213,
            error=None,
            error_message="You don't have the permissions required to use this command",
            halt_execution=False,
        )


def test_with_author_permission_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        assert tanjun.checks.with_author_permission_check(435213, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(
            435213,
            error=None,
            error_message="You don't have the permissions required to use this command",
            halt_execution=False,
        )


def test_with_author_permission_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck") as author_permission_check:
        assert tanjun.checks.with_author_permission_check(435213, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(author_permission_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(author_permission_check.return_value)
        author_permission_check.assert_called_once_with(
            435213,
            error=None,
            error_message="You don't have the permissions required to use this command",
            halt_execution=False,
        )


def test_with_own_permission_check(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)

    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        result = tanjun.checks.with_own_permission_check(5412312)(command)

        assert result is command
        command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(
            5412312,
            error=None,
            error_message="Bot doesn't have the permissions required to run this command",
            halt_execution=False,
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_own_permission_check_with_keyword_arguments(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.SlashCommand)
    mock_error_callback = mock.Mock()

    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        result = tanjun.checks.with_own_permission_check(
            5412312, error=mock_error_callback, error_message="hi", halt_execution=True
        )(command)

        assert result is command
        command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(
            5412312, error=mock_error_callback, error_message="hi", halt_execution=True
        )
        command.wrapped_command.add_check.assert_not_called()


def test_with_own_permission_check_when_follow_wrapping(command: mock.Mock):
    command.wrapped_command = mock.Mock(
        tanjun.MessageCommand, wrapped_command=mock.Mock(tanjun.SlashCommand, wrapped_command=None)
    )
    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        assert tanjun.checks.with_own_permission_check(5412312, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(own_permission_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(own_permission_check.return_value)
        command.wrapped_command.wrapped_command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(
            5412312,
            error=None,
            error_message="Bot doesn't have the permissions required to run this command",
            halt_execution=False,
        )


def test_with_own_permission_check_when_follow_wrapping_and_not_wrapping(command: mock.Mock):
    command.wrapped_command = None
    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        assert tanjun.checks.with_own_permission_check(5412312, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(
            5412312,
            error=None,
            error_message="Bot doesn't have the permissions required to run this command",
            halt_execution=False,
        )


def test_with_own_permission_check_when_follow_wrapping_and_unsupported_command():
    command = mock.Mock(tanjun.abc.SlashCommand)
    command.add_check.return_value = command
    with pytest.raises(AttributeError):
        command.wrapped_command

    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        assert tanjun.checks.with_own_permission_check(5412312, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(
            5412312,
            error=None,
            error_message="Bot doesn't have the permissions required to run this command",
            halt_execution=False,
        )


def test_with_own_permission_check_when_follow_wrapping_and_wrapping_unsupported_command(command: mock.Mock):
    command.wrapped_command = mock.Mock(tanjun.abc.SlashCommand)
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command

    with mock.patch.object(tanjun.checks, "OwnPermissionCheck") as own_permission_check:
        assert tanjun.checks.with_own_permission_check(5412312, follow_wrapped=True)(command) is command

        command.add_check.assert_called_once_with(own_permission_check.return_value)
        command.wrapped_command.add_check.assert_called_once_with(own_permission_check.return_value)
        own_permission_check.assert_called_once_with(
            5412312,
            error=None,
            error_message="Bot doesn't have the permissions required to run this command",
            halt_execution=False,
        )


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
    check = tanjun.checks.any_checks(
        mock_check_1, mock_check_2, mock_check_3, error=TypeError, error_message="hi", halt_execution=True
    )

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
    check = tanjun.checks.any_checks(
        mock_check_1, mock_check_2, mock_check_3, error=ValueError, error_message="hi", halt_execution=True
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
async def test_any_checks_when_check_passes():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_check_4 = mock.Mock()
    mock_check_5 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.FailedCheck, False, True])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        mock_check_4,
        mock_check_5,
        error=ValueError,
        error_message="hi",
        halt_execution=True,
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
async def test_any_checks_when_all_fail_and_error():
    class MockException(Exception):
        def __init__(self):
            ...

    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock()
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[False, tanjun.FailedCheck, False])
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error=MockException, error_message="hi")

    with pytest.raises(MockException):
        await check(mock_context)

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
    check = tanjun.checks.any_checks(mock_check_1, mock_check_2, mock_check_3, error_message="dab", halt_execution=True)

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
    mock_command.add_check.return_value = mock_command
    mock_error_callback = mock.Mock()

    class MockError(Exception):
        ...

    with mock.patch.object(tanjun.checks, "any_checks") as any_checks:
        result = tanjun.checks.with_any_checks(
            mock_check_1,
            mock_check_2,
            mock_check_3,
            suppress=(MockError,),
            error=mock_error_callback,
            error_message="yay catgirls",
            halt_execution=True,
        )(mock_command)

    assert result is mock_command
    mock_command.add_check.assert_called_once_with(any_checks.return_value)
    any_checks.assert_called_once_with(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error=mock_error_callback,
        error_message="yay catgirls",
        suppress=(MockError,),
        halt_execution=True,
    )
