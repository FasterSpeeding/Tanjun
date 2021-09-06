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

import datetime
import typing
from unittest import mock

import pytest
from hikari import permissions

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


class TestApplicationOwnerCheck:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_nsfw_check():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_sfw_check():
    ...


def test_dm_check_for_dm():
    assert tanjun.checks.dm_check(mock.Mock(guild_id=None)) is True


def test_dm_check_for_guild():
    assert tanjun.checks.dm_check(mock.Mock(guild_id=3123), halt_execution=False, error_message=None) is False


def test_dm_check_for_guild_when_halt_execution():
    with pytest.raises(tanjun.HaltExecution):
        assert tanjun.checks.dm_check(mock.Mock(guild_id=3123), halt_execution=True, error_message=None)


def test_dm_check_for_guild_when_error_message():
    with pytest.raises(tanjun.CommandError):
        assert tanjun.checks.dm_check(mock.Mock(guild_id=3123), halt_execution=False, error_message="message")


def test_guild_check_for_guild():
    assert tanjun.checks.guild_check(mock.Mock(guild_id=123123)) is True


def test_guild_check_for_dm():
    assert tanjun.checks.guild_check(mock.Mock(guild_id=None), halt_execution=False, error_message=None) is False


def test_guild_check_for_dm_when_halt_execution():
    with pytest.raises(tanjun.HaltExecution):
        tanjun.checks.guild_check(mock.Mock(guild_id=None), halt_execution=True, error_message=None)


def test_guild_check_for_dm_when_error_message():
    with pytest.raises(tanjun.CommandError):
        tanjun.checks.guild_check(mock.Mock(guild_id=None), halt_execution=False, error_message="hi")


class TestPermissionCheck:
    @pytest.fixture()
    def permission_check_cls(self) -> type[tanjun.checks.PermissionCheck]:
        class Check(tanjun.checks.PermissionCheck):
            get_permissions = mock.AsyncMock()  # type: ignore

        return Check

    @pytest.mark.asyncio()
    async def test___call___when_matched(
        self, permission_check_cls: type[tanjun.checks.PermissionCheck], context: tanjun.abc.Context
    ):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(75)
        check = permission_check_cls(permissions.Permissions(11))

        assert await check(context) is True
        check.get_permissions.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test___call___when_missing_permissions(
        self, permission_check_cls: type[tanjun.checks.PermissionCheck], context: tanjun.abc.Context
    ):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(16)
        check = permission_check_cls(422)

        assert await check(context) is False
        check.get_permissions.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test___call___when_missing_permissions_and_halt_execution(
        self, permission_check_cls: type[tanjun.checks.PermissionCheck], context: tanjun.abc.Context
    ):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(16)
        check = permission_check_cls(422, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution):
            await check(context)

        check.get_permissions.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test___call___when_missing_permissions_and_error_message(
        self, permission_check_cls: type[tanjun.checks.PermissionCheck], context: tanjun.abc.Context
    ):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(16)
        check = permission_check_cls(422, error_message="hi")

        with pytest.raises(tanjun.CommandError):
            await check(context)

        check.get_permissions.assert_awaited_once_with(context)


class TestAuthorPermissionCheck:
    ...


class TestOwnPermissionsCheck:
    ...


def test_with_dm_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "dm_check") as dm_check:
        assert tanjun.checks.with_dm_check(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is dm_check.return_value

        command.add_check.assert_called_once()
        dm_check.assert_called_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in DMs"
        )


def test_with_dm_check_with_keyword_arguments(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "dm_check") as dm_check:
        assert tanjun.checks.with_dm_check(halt_execution=True, error_message="message")(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is dm_check.return_value

        command.add_check.assert_called_once()
        dm_check.assert_called_once_with(mock_ctx, halt_execution=True, error_message="message")


def test_with_guild_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "guild_check") as guild_check:
        assert tanjun.checks.with_guild_check(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is guild_check.return_value

        command.add_check.assert_called_once()
        guild_check.assert_called_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in guild channels"
        )


def test_with_guild_check_with_keyword_arguments(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "guild_check") as guild_check:
        assert tanjun.checks.with_guild_check(halt_execution=True, error_message="eee")(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is guild_check.return_value

        command.add_check.assert_called_once()
        guild_check.assert_called_once_with(mock_ctx, halt_execution=True, error_message="eee")


@pytest.mark.asyncio()
async def test_with_nsfw_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "nsfw_check") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is nsfw_check.return_value

        command.add_check.assert_called_once()
        nsfw_check.assert_awaited_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in NSFW channels"
        )


@pytest.mark.asyncio()
async def test_with_nsfw_check_with_keyword_arguments(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "nsfw_check") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(halt_execution=True, error_message="banned!!!")(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is nsfw_check.return_value

        command.add_check.assert_called_once()
        nsfw_check.assert_awaited_once_with(mock_ctx, halt_execution=True, error_message="banned!!!")


@pytest.mark.asyncio()
async def test_with_sfw_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "sfw_check") as sfw_check:
        assert tanjun.checks.with_sfw_check(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is sfw_check.return_value

        command.add_check.assert_called_once()
        sfw_check.assert_awaited_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in SFW channels"
        )


@pytest.mark.asyncio()
async def test_sfw_check_with_keyword_arguments(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "sfw_check") as sfw_check:
        assert tanjun.checks.with_sfw_check(halt_execution=True, error_message="bango")(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is sfw_check.return_value

        command.add_check.assert_called_once()
        sfw_check.assert_awaited_once_with(mock_ctx, halt_execution=True, error_message="bango")


def test_with_owner_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    with mock.patch.object(tanjun.checks, "ApplicationOwnerCheck") as ApplicationOwnerCheck:
        assert tanjun.checks.with_owner_check(command) is command

        command.add_check.assert_called_once_with(ApplicationOwnerCheck.return_value)
        ApplicationOwnerCheck.assert_called_once_with(
            halt_execution=False,
            error_message="Only bot owners can use this command",
            expire_delta=datetime.timedelta(minutes=5),
            owner_ids=None,
        )


def test_with_owner_check_with_keyword_arguments(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "ApplicationOwnerCheck", return_value=mock_check) as ApplicationOwnerCheck:
        result = tanjun.checks.with_owner_check(
            halt_execution=True,
            error_message="dango",
            expire_delta=datetime.timedelta(minutes=10),
            owner_ids=(123,),
        )(command)
        assert result is command

        command.add_check.assert_called_once()
        ApplicationOwnerCheck.assert_called_once_with(
            halt_execution=True, error_message="dango", expire_delta=datetime.timedelta(minutes=10), owner_ids=(123,)
        )


def test_with_author_permission_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck", return_value=mock_check) as AuthorPermissionCheck:
        assert (
            tanjun.checks.with_author_permission_check(435213, halt_execution=True, error_message="bye")(command)
            is command
        )

        command.add_check.assert_called_once_with(mock_check)
        AuthorPermissionCheck.assert_called_once_with(435213, halt_execution=True, error_message="bye")


def test_with_own_permission_check(command: tanjun.abc.ExecutableCommand[typing.Any]):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "OwnPermissionsCheck", return_value=mock_check) as OwnPermissionsCheck:
        assert (
            tanjun.checks.with_own_permission_check(5412312, halt_execution=True, error_message="hi")(command)
            is command
        )

        command.add_check.assert_called_once_with(mock_check)
        OwnPermissionsCheck.assert_called_once_with(5412312, halt_execution=True, error_message="hi")
