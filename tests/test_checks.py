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
from tanjun._internal import cache


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

    async def test_when_false_and_error_message_dict(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.JA
        check = tanjun.checks.OwnerCheck(
            error_message={hikari.Locale.EN_GB: "aye", hikari.Locale.HR: "eepers", hikari.Locale.JA: "yeet"}
        )

        with pytest.raises(tanjun.errors.CommandError, match="yeet"):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message_dict_but_not_app_command(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.Context)
        check = tanjun.checks.OwnerCheck(
            error_message={
                hikari.Locale.CS: "meow",
                "default": "meep",
                hikari.Locale.FI: "eep",
            }
        )

        with pytest.raises(tanjun.errors.CommandError, match="meep"):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message_dict_defaults(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.FR
        check = tanjun.checks.OwnerCheck(
            error_message={hikari.Locale.EN_US: "catgirl moment", hikari.Locale.HR: "eepers", hikari.Locale.JA: "yeet"}
        )

        with pytest.raises(tanjun.errors.CommandError, match="catgirl moment"):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message_dict_explicit_default(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.FR
        check = tanjun.checks.OwnerCheck(
            error_message={
                hikari.Locale.EN_US: "catgirl moment",
                hikari.Locale.HR: "eepers",
                "default": "epic default",
                hikari.Locale.JA: "yeet",
            }
        )

        with pytest.raises(tanjun.errors.CommandError, match="epic default"):
            await check(mock_context, mock_dependency)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message_localiser(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eepers creepers")
        mock_context.type = hikari.CommandType.MESSAGE
        mock_context.interaction.locale = hikari.Locale.JA
        check = tanjun.checks.OwnerCheck(
            error_message={hikari.Locale.EN_GB: "aye", hikari.Locale.HR: "eepers", hikari.Locale.JA: "yeet"}
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:eepers creepers:check:tanjun.OwnerCheck", {hikari.Locale.DE: "oop", hikari.Locale.JA: "nyaa"}
        )

        with pytest.raises(tanjun.errors.CommandError, match="nyaa"):
            await check(mock_context, mock_dependency, localiser=localiser)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message_localiser_overridden_id(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eepers creepers")
        mock_context.type = hikari.CommandType.MESSAGE
        mock_context.interaction.locale = hikari.Locale.JA
        check = tanjun.checks.OwnerCheck(
            error_message={
                hikari.Locale.EN_GB: "aye",
                hikari.Locale.HR: "eepers",
                hikari.Locale.JA: "yeet",
                "id": "meeeeeow",
            }
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "message_menu:eepers creepers:check:tanjun.OwnerCheck",
                {hikari.Locale.DE: "oop", hikari.Locale.JA: "nyaa"},
            )
            .set_variants(
                "meeeeeow", {hikari.Locale.CS: "aaaaa", hikari.Locale.JA: "cup of isis", hikari.Locale.DA: "noooo"}
            )
        )

        with pytest.raises(tanjun.errors.CommandError, match="cup of isis"):
            await check(mock_context, mock_dependency, localiser=localiser)

        mock_dependency.check_ownership.assert_awaited_once_with(mock_context.client, mock_context.author)

    async def test_when_false_and_error_message_localiser_defaults(self):
        mock_dependency = mock.AsyncMock()
        mock_dependency.check_ownership.return_value = False
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="eepers creepers")
        mock_context.type = hikari.CommandType.MESSAGE
        mock_context.interaction.locale = hikari.Locale.FR
        check = tanjun.checks.OwnerCheck(
            error_message={
                hikari.Locale.EN_GB: "aye",
                "default": "defo",
                hikari.Locale.HR: "eepers",
                hikari.Locale.JA: "yeet",
            }
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:eepers creepers:check:tanjun.OwnerCheck", {hikari.Locale.DE: "oop", hikari.Locale.JA: "nyaa"}
        )

        with pytest.raises(tanjun.errors.CommandError, match="defo"):
            await check(mock_context, mock_dependency, localiser=localiser)

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
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(error=TypeError, error_message="meep", halt_execution=True)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            result = await check(mock_context)

        assert result is True
        get_perm_channel.assert_not_called()

    async def test(self):
        mock_context = mock.Mock()
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(error_message=None)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            result = await check(mock_context)

        assert result is True
        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false(self):
        mock_context = mock.Mock(client=tanjun.Client(mock.AsyncMock(), cache=mock.Mock()))
        check = tanjun.checks.NsfwCheck(error_message=None)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=None)) as get_perm_channel:
            result = await check(mock_context)

        assert result is False
        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_when_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        mock_context = mock.Mock(client=tanjun.Client(mock.AsyncMock(), cache=mock.Mock()))
        check = tanjun.checks.NsfwCheck(error=MockException, error_message="nye")

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=None)) as get_perm_channel:
            with pytest.raises(MockException):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(error_message="meow me")

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="meow me"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_dict(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.HU
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={hikari.Locale.DE: "oh", hikari.Locale.HU: "no", hikari.Locale.EN_GB: "meow"}
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="no"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_dict_but_not_app_command(self):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={
                hikari.Locale.DE: "op",
                "default": "defaulted",
                hikari.Locale.HU: "no",
                hikari.Locale.EN_GB: "meow",
            }
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="defaulted"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_dict_defaults(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.DA
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={
                hikari.Locale.DE: "default default default",
                hikari.Locale.HU: "no",
                hikari.Locale.EN_GB: "meow",
            }
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="default default default"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_dict_explicit_default(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.DA
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={
                hikari.Locale.DE: "default default default",
                "default": "real default",
                hikari.Locale.HU: "no",
                hikari.Locale.EN_GB: "meow",
            }
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="real default"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_localiser(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="meow meow")
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.EN_GB
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={
                hikari.Locale.DE: "default default default",
                hikari.Locale.HU: "no",
                hikari.Locale.EN_GB: "meow",
            }
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "user_menu:meow meow:check:tanjun.NsfwCheck",
            {hikari.Locale.CS: "n", hikari.Locale.EN_GB: "override", hikari.Locale.FI: "i'm finished"},
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="override"):
                await check(mock_context, localiser=localiser)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_localiser_overridden_id(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="meow meow")
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.EN_GB
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={
                hikari.Locale.DE: "default default default",
                hikari.Locale.HU: "no",
                "id": "cthulhu calls",
                hikari.Locale.EN_GB: "meow",
            }
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "user_menu:meow meow:check:tanjun.NsfwCheck",
                {hikari.Locale.CS: "n", hikari.Locale.EN_GB: "override", hikari.Locale.FI: "i'm finished"},
            )
            .set_variants("cthulhu calls", {hikari.Locale.EN_GB: "wowzer Fred, I'm gay", hikari.Locale.CS: "meow"})
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="wowzer Fred, I'm gay"):
                await check(mock_context, localiser=localiser)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_error_message_localiser_defaults(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="meow meow")
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(
            error_message={
                hikari.Locale.DE: "default default default",
                hikari.Locale.HU: "no",
                hikari.Locale.EN_GB: "meow",
            }
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "user_menu:meow meow:check:tanjun.NsfwCheck",
                {hikari.Locale.CS: "n", hikari.Locale.EN_GB: "override", hikari.Locale.FI: "i'm finished"},
            )
            .set_variants("cthulhu calls", {hikari.Locale.EN_GB: "wowzer Fred, I'm gay", hikari.Locale.CS: "meow"})
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="default default default"):
                await check(mock_context, localiser=localiser)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_false_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.NsfwCheck(error_message="yeet", halt_execution=True)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            with pytest.raises(tanjun.errors.HaltExecution):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)


@pytest.mark.asyncio()
class TestSfwCheck:
    async def test_when_is_dm(self):
        mock_context = mock.Mock(guild_id=None)
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(error=ValueError, error_message="lll", halt_execution=True)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            result = await check(mock_context)

        assert result is True
        get_perm_channel.assert_not_called()

    async def test(self):
        mock_context = mock.Mock()
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(error_message=None)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=False)) as get_perm_channel:
            result = await check(mock_context)

        assert result is True
        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw(self):
        mock_context = mock.Mock(client=tanjun.Client(mock.AsyncMock(), cache=mock.Mock()))
        check = tanjun.checks.SfwCheck(error_message=None)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            result = await check(mock_context)

        assert result is False
        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error(self):
        class MockException(Exception):
            def __init__(self):
                ...

        mock_context = mock.Mock(client=tanjun.Client(mock.AsyncMock(), cache=mock.Mock()))
        check = tanjun.checks.SfwCheck(error=MockException, error_message="bye")

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(MockException):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message(self):
        mock_context = mock.Mock()
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(error_message="meow me")

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="meow me"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_dict(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.DA
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={hikari.Locale.BG: "oooooo", hikari.Locale.DA: "moooo", hikari.Locale.EN_GB: "pussy cat"}
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="moooo"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_dict_but_not_app_command(self):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={
                hikari.Locale.BG: "oooooo",
                "default": "bye bye",
                hikari.Locale.DA: "moooo",
                hikari.Locale.EN_GB: "pussy cat",
            }
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="bye bye"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_dict_defaults(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={hikari.Locale.BG: "oooooo", hikari.Locale.DA: "moooo", hikari.Locale.EN_GB: "pussy cat"}
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="oooooo"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_dict_explicit_default(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={
                hikari.Locale.BG: "oooooo",
                hikari.Locale.DA: "moooo",
                hikari.Locale.EN_GB: "pussy cat",
                "default": "oh no",
            }
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="oh no"):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_localiser(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="oh no girl")
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.DA
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={hikari.Locale.BG: "oooooo", hikari.Locale.DA: "moooo", hikari.Locale.EN_GB: "pussy cat"}
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "user_menu:oh no girl:check:tanjun.SfwCheck", {hikari.Locale.DA: "real value", hikari.Locale.BG: "op"}
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="real value"):
                await check(mock_context, localiser=localiser)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_localiser_overridden_id(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="oh no girl")
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.EN_GB
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={
                hikari.Locale.BG: "oooooo",
                hikari.Locale.DA: "moooo",
                "id": "meow meow meow meow",
                hikari.Locale.EN_GB: "pussy cat",
            }
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "user_menu:oh no girl:check:tanjun.SfwCheck",
                {
                    hikari.Locale.EN_GB: "You can sail the seven seas and find",
                    hikari.Locale.EN_US: "Love is a place you'll never see",
                },
            )
            .set_variants(
                "meow meow meow meow",
                {
                    hikari.Locale.EN_GB: "Passing you like a summer breeze",
                    hikari.Locale.EN_US: "You feel life has no other reason to be",
                },
            )
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="Passing you like a summer breeze"):
                await check(mock_context, localiser=localiser)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_error_message_localiser_defaults(self):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="oh no girl")
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.DE
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(
            error_message={
                hikari.Locale.JA: "years of meows",
                hikari.Locale.DA: "moooo",
                "id": "meow meow meow meow",
                hikari.Locale.EN_GB: "pussy cat",
            }
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "user_menu:oh no girl:check:tanjun.SfwCheck",
                {
                    hikari.Locale.EN_GB: "You can sail the seven seas and find",
                    hikari.Locale.EN_US: "Love is a place you'll never see",
                },
            )
            .set_variants(
                "meow meow meow meow",
                {
                    hikari.Locale.EN_GB: "Passing you like a summer breeze",
                    hikari.Locale.EN_US: "You feel life has no other reason to be",
                },
            )
        )

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.CommandError, match="years of meows"):
                await check(mock_context, localiser=localiser)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)

    async def test_when_is_nsfw_and_halt_execution(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.client = tanjun.Client(mock.AsyncMock(), cache=mock.Mock())
        check = tanjun.checks.SfwCheck(error_message="yeet", halt_execution=True)

        with mock.patch.object(cache, "get_perm_channel", return_value=mock.Mock(is_nsfw=True)) as get_perm_channel:
            with pytest.raises(tanjun.errors.HaltExecution):
                await check(mock_context)

        get_perm_channel.assert_awaited_once_with(mock_context.client, mock_context.channel_id)


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
        mock_context = mock.Mock(guild_id=3123)

        with pytest.raises(MockException):
            assert check(mock_context)

    def test_for_guild_when_halt_execution(self):
        check = tanjun.checks.DmCheck(error_message="beep", halt_execution=True)
        mock_context = mock.Mock(guild_id=3123)

        with pytest.raises(tanjun.HaltExecution):
            assert check(mock_context)

    def test_for_guild_when_error_message(self):
        check = tanjun.checks.DmCheck(error_message="message")
        mock_context = mock.Mock(guild_id=3123)

        with pytest.raises(tanjun.CommandError, match="message"):
            assert check(mock_context)

    def test_for_guild_when_error_message_dict(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.ES_ES: "weeb girl",
                hikari.Locale.EN_US: "tax girl",
                hikari.Locale.EN_GB: "tea girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=3123)
        mock_context.interaction.locale = hikari.Locale.EN_US

        with pytest.raises(tanjun.CommandError, match="tax girl"):
            assert check(mock_context)

    def test_for_guild_when_error_message_dict_but_not_app_command(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.ES_ES: "weeb girl",
                "default": "weeby girl",
                hikari.Locale.EN_US: "tax girl",
                hikari.Locale.EN_GB: "tea girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=3123)

        with pytest.raises(tanjun.CommandError, match="weeby girl"):
            assert check(mock_context)

    def test_for_guild_when_error_message_dict_defaults(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.EN_GB: "tea girl",
                hikari.Locale.EN_US: "tax girl",
                hikari.Locale.ES_ES: "weeb girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=3123)
        mock_context.interaction.locale = hikari.Locale.FR

        with pytest.raises(tanjun.CommandError, match="tea girl"):
            assert check(mock_context)

    def test_for_guild_when_error_message_dict_explicit_default(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.EN_GB: "tea girl",
                hikari.Locale.EN_US: "tax girl",
                "default": "man girl",
                hikari.Locale.ES_ES: "weeb girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=3123)
        mock_context.interaction.locale = hikari.Locale.FR

        with pytest.raises(tanjun.CommandError, match="man girl"):
            assert check(mock_context)

    def test_for_guild_when_error_message_localiser(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.EN_GB: "tea girl",
                hikari.Locale.EN_US: "tax girl",
                hikari.Locale.ES_ES: "weeb girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=3123, triggering_name="girl girl")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.EN_GB
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:girl girl:check:tanjun.DmCheck",
            {hikari.Locale.DE: "beer girl", hikari.Locale.EN_GB: "me girl", hikari.Locale.JA: "anime girl"},
        )

        with pytest.raises(tanjun.CommandError, match="me girl"):
            assert check(mock_context, localiser=localiser)

    def test_for_guild_when_error_message_localiser_overridden_id(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.EN_GB: "tea girl",
                hikari.Locale.EN_US: "tax girl",
                "id": "girl girl",
                hikari.Locale.ES_ES: "weeb girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=3123, triggering_name="girl girl")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.EN_GB
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "slash:girl girl:check:tanjun.DmCheck",
                {hikari.Locale.DE: "beer girl", hikari.Locale.EN_GB: "me girl", hikari.Locale.JA: "anime girl"},
            )
            .set_variants(
                "girl girl",
                {hikari.Locale.EN_GB: "my girl", hikari.Locale.ZH_CN: "camp girl", hikari.Locale.ZH_TW: "real girl"},
            )
        )

        with pytest.raises(tanjun.CommandError, match="my girl"):
            assert check(mock_context, localiser=localiser)

    def test_for_guild_when_error_message_localiser_defaults(self):
        check = tanjun.checks.DmCheck(
            error_message={
                hikari.Locale.ES_ES: "weeb girl",
                hikari.Locale.EN_GB: "tea girl",
                hikari.Locale.EN_US: "tax girl",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=3123, triggering_name="girl girl")
        mock_context.type = hikari.CommandType.SLASH
        mock_context.interaction.locale = hikari.Locale.ZH_TW
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:girl girl:check:tanjun.DmCheck",
            {hikari.Locale.DE: "beer girl", hikari.Locale.EN_GB: "me girl", hikari.Locale.JA: "anime girl"},
        )

        with pytest.raises(tanjun.CommandError, match="weeb girl"):
            assert check(mock_context, localiser=localiser)


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
        check = tanjun.checks.GuildCheck(error_message="beep", halt_execution=True)
        mock_context = mock.Mock(guild_id=None)

        with pytest.raises(tanjun.HaltExecution):
            check(mock_context)

    def test_for_dm_when_error_message(self):
        check = tanjun.checks.GuildCheck(error_message="hi")
        mock_context = mock.Mock(guild_id=None)

        with pytest.raises(tanjun.CommandError, match="hi"):
            check(mock_context)

    def test_for_dm_when_error_message_dict(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.EN_GB: "hi",
                hikari.Locale.EN_US: r"\*shoots\*",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=None)
        mock_context.interaction.locale = hikari.Locale.JA

        with pytest.raises(tanjun.CommandError, match="Konnichiwa"):
            check(mock_context)

    def test_for_dm_when_error_message_dict_but_not_app_command(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.EN_US: "*shoots*",
                "default": "*heals*",
                hikari.Locale.EN_GB: "hi",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.Context, guild_id=None)

        with pytest.raises(tanjun.CommandError, match=r"\*heals\*"):
            check(mock_context)

    def test_for_dm_when_error_message_dict_defaults(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.SV_SE: "Blåhaj my beloved",
                hikari.Locale.EN_GB: "hi",
                hikari.Locale.EN_US: r"\*shoots\*",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=None)
        mock_context.interaction.locale = hikari.Locale.FR

        with pytest.raises(tanjun.CommandError, match="Blåhaj my beloved"):
            check(mock_context)

    def test_for_dm_when_error_message_dict_explicit_default(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.SV_SE: "Blåhaj my beloved",
                "default": "nyaa",
                hikari.Locale.EN_GB: "hi",
                hikari.Locale.EN_US: r"\*shoots\*",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=None)
        mock_context.interaction.locale = hikari.Locale.FR

        with pytest.raises(tanjun.CommandError, match="nyaa"):
            check(mock_context)

    def test_for_dm_when_error_message_localiser(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.SV_SE: "Blåhaj my beloved",
                hikari.Locale.EN_GB: "hi",
                hikari.Locale.EN_US: r"\*shoots\*",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=None, triggering_name="blue shark uwu")
        mock_context.type = hikari.CommandType.MESSAGE
        mock_context.interaction.locale = hikari.Locale.EN_GB
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:blue shark uwu:check:tanjun.GuildCheck",
            {hikari.Locale.BG: "background", hikari.Locale.EN_GB: "Please uwu me"},
        )

        with pytest.raises(tanjun.CommandError, match="Please uwu me"):
            check(mock_context, localiser=localiser)

    def test_for_dm_when_error_message_localiser_overridden_id(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.SV_SE: "Blåhaj my beloved",
                hikari.Locale.EN_GB: "hi",
                "id": "cabbage pfp",
                hikari.Locale.EN_US: r"\*shoots\*",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=None, triggering_name="blue shark uwu")
        mock_context.type = hikari.CommandType.MESSAGE
        mock_context.interaction.locale = hikari.Locale.EN_GB
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "message_menu:blue shark uwu:check:tanjun.GuildCheck",
                {hikari.Locale.BG: "background", hikari.Locale.EN_GB: "Please uwu me"},
            )
            .set_variants("cabbage pfp", {hikari.Locale.EN_GB: "Blåhaj fan 69"})
        )

        with pytest.raises(tanjun.CommandError, match="Blåhaj fan 69"):
            check(mock_context, localiser=localiser)

    def test_for_dm_when_error_message_localiser_defaults(self):
        check = tanjun.checks.GuildCheck(
            error_message={
                hikari.Locale.SV_SE: "Blåhaj my beloved",
                hikari.Locale.EN_GB: "hi",
                hikari.Locale.EN_US: r"\*shoots\*",
                hikari.Locale.JA: "Konnichiwa",
            }
        )
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, guild_id=None, triggering_name="blue shark uwu")
        mock_context.type = hikari.CommandType.MESSAGE
        mock_context.interaction.locale = hikari.Locale.EN_GB
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:blue shark uwu:check:tanjun.GuildCheck",
            {hikari.Locale.BG: "background", hikari.Locale.EN_GB: "Please uwu me"},
        )

        with pytest.raises(tanjun.CommandError, match="Please uwu me"):
            check(mock_context, localiser=localiser)


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
    async def test_when_missing_perms_and_error_message_dict(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock()
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms, error_message={hikari.Locale.BG: "yeet", "default": "moop"}
        )

        with pytest.raises(tanjun.CommandError, match="moop"), mock.patch.object(
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
    async def test_for_interaction_member_when_missing_perms_and_error_message_dict(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(
            tanjun.abc.AppCommandContext, member=mock.Mock(hikari.InteractionMember, permissions=actual_perms)
        )
        mock_context.interaction.locale = hikari.Locale.EN_US
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms,
            error_message={hikari.Locale.EN_GB: "Feet are not", hikari.Locale.EN_US: "ok", hikari.Locale.JA: "STOP"},
        )

        with pytest.raises(tanjun.CommandError, match="ok"):
            await check(mock_context)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_message_dict_defaults(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(
            tanjun.abc.AppCommandContext, member=mock.Mock(hikari.InteractionMember, permissions=actual_perms)
        )
        mock_context.interaction.locale = hikari.Locale.FR
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms,
            error_message={hikari.Locale.EN_GB: "Feet are not", hikari.Locale.EN_US: "ok", hikari.Locale.JA: "STOP"},
        )

        with pytest.raises(tanjun.CommandError, match="Feet are not"):
            await check(mock_context)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_message_dict_explicit_default(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(
            tanjun.abc.AppCommandContext, member=mock.Mock(hikari.InteractionMember, permissions=actual_perms)
        )
        mock_context.interaction.locale = hikari.Locale.FR
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms,
            error_message={
                hikari.Locale.EN_GB: "Feet are not",
                hikari.Locale.EN_US: "ok",
                hikari.Locale.JA: "STOP",
                "default": "catgirls",
            },
        )

        with pytest.raises(tanjun.CommandError, match="catgirls"):
            await check(mock_context)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_message_localiser(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(
            tanjun.abc.AppCommandContext,
            member=mock.Mock(hikari.InteractionMember, permissions=actual_perms),
            triggering_name="rawr xd",
        )
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.JA
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms,
            error_message={hikari.Locale.EN_GB: "Feet are not", hikari.Locale.EN_US: "ok", hikari.Locale.JA: "STOP"},
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "user_menu:rawr xd:check:tanjun.AuthorPermissionCheck",
            {hikari.Locale.DA: "das is good", hikari.Locale.JA: "meowers"},
        )

        with pytest.raises(tanjun.CommandError, match="meowers"):
            await check(mock_context, localiser=localiser)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_message_localiser_overridden_id(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(
            tanjun.abc.AppCommandContext,
            member=mock.Mock(hikari.InteractionMember, permissions=actual_perms),
            triggering_name="rawr xd",
        )
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.JA
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms,
            error_message={
                hikari.Locale.EN_GB: "Feet are not",
                "id": "cool id nyaa",
                hikari.Locale.EN_US: "ok",
                hikari.Locale.JA: "STOP",
            },
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "user_menu:rawr xd:check:tanjun.AuthorPermissionCheck",
                {hikari.Locale.DA: "das is good", hikari.Locale.EN_GB: "meowers"},
            )
            .set_variants("cool id nyaa", {hikari.Locale.JA: "meow", hikari.Locale.CS: "echo"})
        )

        with pytest.raises(tanjun.CommandError, match="meow"):
            await check(mock_context, localiser=localiser)

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_member_when_missing_perms_and_error_message_localiser_defaults(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(
            tanjun.abc.AppCommandContext,
            member=mock.Mock(hikari.InteractionMember, permissions=actual_perms),
            triggering_name="rawr xd",
        )
        mock_context.type = hikari.CommandType.USER
        mock_context.interaction.locale = hikari.Locale.CS
        check = tanjun.checks.AuthorPermissionCheck(
            required_perms,
            error_message={
                hikari.Locale.EN_GB: "Feet are not",
                "default": "eepers",
                "id": "cool id nyaa",
                hikari.Locale.EN_US: "ok",
                hikari.Locale.JA: "STOP",
            },
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "user_menu:rawr xd:check:tanjun.AuthorPermissionCheck",
                {hikari.Locale.DA: "das is good", hikari.Locale.EN_GB: "meowers"},
            )
            .set_variants("cool id nyaa", {hikari.Locale.EN_GB: "meow", hikari.Locale.DE: "echo"})
        )

        with pytest.raises(tanjun.CommandError, match="eepers"):
            await check(mock_context, localiser=localiser)

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
    async def test_when_missing_perms_and_error_message_dict(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.Context)
        mock_context.cache.get_member.return_value = None
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        mock_member_cache.get_from_guild.return_value = None
        check = tanjun.checks.OwnPermissionCheck(
            required_perms, error_message={hikari.Locale.DE: "meow meow", "default": "bye meow"}
        )

        with pytest.raises(tanjun.CommandError, match="bye meow"), mock.patch.object(
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
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
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
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
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
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
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
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
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
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message_dict(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.interaction.locale = hikari.Locale.EN_GB
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(
            required_perms,
            error_message={hikari.Locale.DE: "bees", hikari.Locale.EN_GB: "hip", hikari.Locale.EN_US: "to bee"},
        )

        with pytest.raises(tanjun.CommandError, match="hip"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message_dict_defaults(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(
            required_perms,
            error_message={hikari.Locale.DE: "bees", hikari.Locale.EN_GB: "hip", hikari.Locale.EN_US: "to bee"},
        )

        with pytest.raises(tanjun.CommandError, match="bees"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message_dict_explicit_default(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
        mock_context.interaction.app_permissions = actual_perms
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.rest = mock.AsyncMock()
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(
            required_perms,
            error_message={
                hikari.Locale.DE: "bees",
                hikari.Locale.EN_GB: "hip",
                "default": "inject me uwu",
                hikari.Locale.EN_US: "to bee",
            },
        )

        with pytest.raises(tanjun.CommandError, match="inject me uwu"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message_localiser(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="meow command")
        mock_context.interaction.app_permissions = actual_perms
        mock_context.interaction.locale = hikari.Locale.EN_US
        mock_context.rest = mock.AsyncMock()
        mock_context.type = hikari.CommandType.MESSAGE
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(
            required_perms,
            error_message={hikari.Locale.DE: "bees", hikari.Locale.EN_GB: "hip", hikari.Locale.EN_US: "to bee"},
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:meow command:check:tanjun.OwnPermissionCheck",
            {hikari.Locale.EN_GB: "no", hikari.Locale.EN_US: "girls"},
        )

        with pytest.raises(tanjun.CommandError, match="girls"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, localiser=localiser, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message_localiser_overridden_id(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="meow command")
        mock_context.interaction.app_permissions = actual_perms
        mock_context.interaction.locale = hikari.Locale.EN_US
        mock_context.rest = mock.AsyncMock()
        mock_context.type = hikari.CommandType.MESSAGE
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(
            required_perms,
            error_message={
                hikari.Locale.DE: "bees",
                hikari.Locale.EN_GB: "hip",
                "id": "yuri",
                hikari.Locale.EN_US: "to bee",
            },
        )
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants(
                "message_menu:meow command:check:tanjun.OwnPermissionCheck",
                {hikari.Locale.EN_GB: "no", hikari.Locale.EN_US: "girls"},
            )
            .set_variants("yuri", {hikari.Locale.EN_US: "uwu owo"})
        )

        with pytest.raises(tanjun.CommandError, match="uwu owo"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, localiser=localiser, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_error_message_localiser_defaults(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="meow command")
        mock_context.interaction.app_permissions = actual_perms
        mock_context.interaction.locale = hikari.Locale.FR
        mock_context.rest = mock.AsyncMock()
        mock_context.type = hikari.CommandType.MESSAGE
        mock_own_user = mock.Mock()
        mock_member_cache = mock.AsyncMock()
        check = tanjun.checks.OwnPermissionCheck(
            required_perms,
            error_message={
                hikari.Locale.DE: "bees",
                hikari.Locale.EN_GB: "hip",
                "default": "meow-nyon",
                hikari.Locale.EN_US: "to bee",
            },
        )
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:meow command:check:tanjun.OwnPermissionCheck",
            {hikari.Locale.EN_GB: "no", hikari.Locale.EN_US: "girls"},
        )

        with pytest.raises(tanjun.CommandError, match="meow-nyon"), mock.patch.object(
            tanjun.permissions, "fetch_permissions"
        ) as fetch_permissions:
            await check(mock_context, localiser=localiser, member_cache=mock_member_cache, my_user=mock_own_user)

        fetch_permissions.assert_not_called()
        mock_context.cache.get_member.assert_not_called()
        mock_member_cache.get_from_guild.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()

    @pytest.mark.parametrize(*MISSING_PERMISSIONS)
    async def test_for_interaction_context_with_app_permissions_when_missing_perms_and_halt_execution(
        self, required_perms: hikari.Permissions, actual_perms: hikari.Permissions, missing_perms: hikari.Permissions
    ):
        mock_context = mock.Mock(tanjun.abc.AppCommandContext)
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
async def test_any_checks_when_all_fail_and_error_message_dict():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext)
    mock_context.interaction.locale = hikari.Locale.DA
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={hikari.Locale.CS: "meow", hikari.Locale.DA: "op", hikari.Locale.EN_GB: "oooooooh"},
    )

    with pytest.raises(tanjun.CommandError, match="op"):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message_dict_but_not_app_command():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext)
    mock_context.interaction.locale = hikari.Locale.LT
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={
            hikari.Locale.CS: "meow",
            hikari.Locale.DA: "op",
            "default": "justice!!!",
            hikari.Locale.EN_GB: "oooooooh",
        },
    )

    with pytest.raises(tanjun.CommandError, match="justice!!!"):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message_dict_defaults():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext)
    mock_context.interaction.locale = hikari.Locale.FR
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={hikari.Locale.CS: "meow", hikari.Locale.DA: "op", hikari.Locale.EN_GB: "oooooooh"},
    )

    with pytest.raises(tanjun.CommandError, match="meow"):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message_dict_explicit_default():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext)
    mock_context.interaction.locale = hikari.Locale.FR
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={
            hikari.Locale.CS: "meow",
            hikari.Locale.DA: "op",
            hikari.Locale.EN_GB: "oooooooh",
            "default": "catgirl token",
        },
    )

    with pytest.raises(tanjun.CommandError, match="catgirl token"):
        await check(mock_context)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message_localiser():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="catgirl bot")
    mock_context.type = hikari.CommandType.SLASH
    mock_context.interaction.locale = hikari.Locale.EN_GB
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={hikari.Locale.CS: "meow", hikari.Locale.DA: "op", hikari.Locale.EN_GB: "oooooooh"},
    )
    localiser = tanjun.dependencies.BasicLocaliser().set_variants(
        "slash:catgirl bot:check:tanjun.any_check", {hikari.Locale.EN_GB: "Bark bark", hikari.Locale.DA: "germany"}
    )

    with pytest.raises(tanjun.CommandError, match="Bark bark"):
        await check(mock_context, localiser=localiser)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message_localiser_overridden_id():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="catgirl bot")
    mock_context.type = hikari.CommandType.SLASH
    mock_context.interaction.locale = hikari.Locale.EN_GB
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={
            hikari.Locale.CS: "meow",
            hikari.Locale.DA: "op",
            "id": "meme girl",
            hikari.Locale.EN_GB: "oooooooh",
        },
    )
    localiser = (
        tanjun.dependencies.BasicLocaliser()
        .set_variants(
            "slash:catgirl bot:check:tanjun.any_check", {hikari.Locale.EN_GB: "Bark bark", hikari.Locale.DA: "germany"}
        )
        .set_variants("meme girl", {hikari.Locale.FI: "finish", hikari.Locale.EN_GB: "useless token"})
    )

    with pytest.raises(tanjun.CommandError, match="useless token"):
        await check(mock_context, localiser=localiser)

    mock_context.call_with_async_di.assert_has_awaits(
        [
            mock.call(mock_check_1, mock_context),
            mock.call(mock_check_2, mock_context),
            mock.call(mock_check_3, mock_context),
        ]
    )


@pytest.mark.asyncio()
async def test_any_checks_when_all_fail_and_error_message_localiser_defaults():
    mock_check_1 = mock.Mock()
    mock_check_2 = mock.Mock()
    mock_check_3 = mock.Mock()
    mock_context = mock.Mock(tanjun.abc.AppCommandContext, triggering_name="catgirl bot")
    mock_context.type = hikari.CommandType.SLASH
    mock_context.interaction.locale = hikari.Locale.JA
    mock_context.call_with_async_di = mock.AsyncMock(side_effect=[tanjun.FailedCheck, False, False])
    check = tanjun.checks.any_checks(
        mock_check_1,
        mock_check_2,
        mock_check_3,
        error_message={
            hikari.Locale.CS: "meow",
            "default": "i'm finished finally",
            hikari.Locale.DA: "op",
            hikari.Locale.EN_GB: "oooooooh",
        },
    )
    localiser = tanjun.dependencies.BasicLocaliser().set_variants(
        "slash:catgirl bot:check:tanjun.any_check", {hikari.Locale.EN_GB: "Bark bark", hikari.Locale.DA: "germany"}
    )

    with pytest.raises(tanjun.CommandError, match="i'm finished finally"):
        await check(mock_context, localiser=localiser)

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
