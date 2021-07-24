import datetime

import  contextlib
import mock
import pytest
from hikari import permissions

from tanjun import checks
from tanjun import traits


@pytest.fixture()
def command():
    command_ =mock.Mock(traits.ExecutableCommand)
    command_.add_check.return_value = command_
    return command_


@pytest.fixture()
def context():
    return mock.Mock(traits.Context)


class TestApplicationOwnerCheck:
    ...


def test_nsfw_check(context):
    ...


@pytest.mark.asyncio()
async def test_sfw_check(context):
    with mock.patch.object(checks, "nsfw_check", new=mock.AsyncMock(return_value=True)):
        assert await checks.sfw_check(context) is False
        checks.nsfw_check.assert_awaited_once_with(context)


def test_dm_check_for_dm(context):
    context.guild_id = None
    assert checks.dm_check(context) is True


def test_dm_check_for_guild(context):
    context.guild_id = 3123
    assert checks.dm_check(context) is False


def test_guild_check_for_guild(context):
    context.guild_id = 123123
    assert checks.guild_check(context) is True


def test_guild_check_for_dm(context):
    context.guild_id = None
    assert checks.guild_check(context) is False


class TestPermissionCheck:
    @pytest.fixture()
    def permission_check_cls(self):
        class Check(checks.PermissionCheck):
            get_permissions = mock.AsyncMock()

        return Check

    @pytest.mark.asyncio()
    async def test___call___when_matched(self, permission_check_cls, context):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(75)
        check = permission_check_cls(permissions.Permissions(11))

        assert await check(context) is True
        check.get_permissions.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test___call___when_missing_permissions(self, permission_check_cls, context):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(16)
        check = permission_check_cls(422)

        assert await check(context) is False
        check.get_permissions.assert_awaited_once_with(context)


class TestAuthorPermissionCheck:
    ...


class TestOwnPermissionsCheck:
    ...


def test_with_dm_check(command):
    mock_ctx = object()
    with mock.patch.object(checks, "dm_check") as dm_check:
        assert checks.with_dm_check(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is dm_check.return_value

        command.add_check.assert_called_once()
        dm_check.assert_called_once_with(mock_ctx, end_execution=False)

def test_with_dm_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(checks, "dm_check") as dm_check:
        assert checks.with_dm_check(end_execution=True)(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is dm_check.return_value

        command.add_check.assert_called_once()
        dm_check.assert_called_once_with(mock_ctx, end_execution=True)


def test_with_guild_check(command):
    mock_ctx = object()
    with mock.patch.object(checks, "guild_check") as guild_check:
        assert checks.with_guild_check(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is guild_check.return_value

        command.add_check.assert_called_once()
        guild_check.assert_called_once_with(mock_ctx, end_execution=False)

def test_with_guild_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(checks, "guild_check") as guild_check:
        assert checks.with_guild_check(end_execution=True)(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is guild_check.return_value

        command.add_check.assert_called_once()
        guild_check.assert_called_once_with(mock_ctx, end_execution=True)



@pytest.mark.asyncio()
async def test_with_nsfw_check(command):
    mock_ctx = object()
    with mock.patch.object(checks, "nsfw_check") as nsfw_check:
        assert checks.with_nsfw_check(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is nsfw_check.return_value

        command.add_check.assert_called_once()
        nsfw_check.assert_awaited_once_with(mock_ctx, end_execution=False)


@pytest.mark.asyncio()
async def test_with_nsfw_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(checks, "nsfw_check") as nsfw_check:
        assert checks.with_nsfw_check(end_execution=True)(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is nsfw_check.return_value

        command.add_check.assert_called_once()
        nsfw_check.assert_awaited_once_with(mock_ctx, end_execution=True)



@pytest.mark.asyncio()
async def test_sfw_check(command):
    mock_ctx = object()
    with mock.patch.object(checks, "sfw_check") as sfw_check:
        assert checks.with_sfw_check(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is sfw_check.return_value

        command.add_check.assert_called_once()
        sfw_check.assert_awaited_once_with(mock_ctx, end_execution=False)

@pytest.mark.asyncio()
async def test_sfw_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(checks, "sfw_check") as sfw_check:
        assert checks.with_sfw_check(end_execution=True)(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is sfw_check.return_value

        command.add_check.assert_called_once()
        sfw_check.assert_awaited_once_with(mock_ctx, end_execution=True)


def test_with_owner_check(command):
    with mock.patch.object(checks, "ApplicationOwnerCheck") as ApplicationOwnerCheck:
        assert checks.with_owner_check(command) is command

        command.add_check.assert_called_once_with(ApplicationOwnerCheck.return_value)
        ApplicationOwnerCheck.assert_called_once_with(
            end_execution=False, expire_delta=datetime.timedelta(minutes=5), owner_ids=None
        )


def test_with_owner_check_with_keyword_arguments(command):
    mock_check = object()
    with mock.patch.object(checks, "ApplicationOwnerCheck", return_value=mock_check):
        assert checks.with_owner_check(end_execution=True, expire_delta=datetime.timedelta(minutes=10), owner_ids=(123,))(command) is command

        command.add_check.assert_called_once()
        checks.ApplicationOwnerCheck.assert_called_once_with(
            end_execution=True, expire_delta=datetime.timedelta(minutes=10), owner_ids=(123,)
        )


def test_with_author_permission_check(command):
    mock_check = object()
    with mock.patch.object(checks, "AuthorPermissionCheck", return_value=mock_check):
        assert checks.with_author_permission_check(435213, end_execution=True)(command) is command

        command.add_check.assert_called_once_with(mock_check)
        checks.AuthorPermissionCheck.assert_called_once_with(435213, end_execution=True)


def test_with_own_permission_check(command):
    mock_check = object()
    with mock.patch.object(checks, "OwnPermissionsCheck", return_value=mock_check):
        assert checks.with_own_permission_check(5412312, end_execution=True)(command) is command

        command.add_check.assert_called_once_with(mock_check)
        checks.OwnPermissionsCheck.assert_called_once_with(5412312, end_execution=True)
