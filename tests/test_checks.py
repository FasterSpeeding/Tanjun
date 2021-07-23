import mock
import pytest
from hikari import permissions

from tanjun import checks
from tanjun import traits


@pytest.fixture()
def command():
    return mock.Mock(traits.MessageCommand)


@pytest.fixture()
def context():
    return mock.Mock(traits.Context)


class TestApplicationOwnerCheck:
    ...


def test_nsfw_check(context):
    ...


@pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test___call___when_matched(self, permission_check_cls, context):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(75)
        check = permission_check_cls(permissions.Permissions(11))

        assert await check(context) is True
        check.get_permissions.assert_awaited_once_with(context)

    @pytest.mark.asyncio
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
    assert checks.with_dm_check(command) is command
    command.add_check.assert_called_once_with(checks.dm_check)


def test_with_guild_check(command):
    assert checks.with_guild_check(command) is command
    command.add_check.assert_called_once_with(checks.guild_check)


def test_with_nsfw_check(command):
    assert checks.with_nsfw_check(command) is command
    command.add_check.assert_called_once_with(checks.nsfw_check)


def test_sfw_check(command):
    assert checks.with_sfw_check(command) is command
    command.add_check.assert_called_once_with(checks.sfw_check)


def test_with_owner_check(command):
    mock_check = object()
    with mock.patch.object(checks, "ApplicationOwnerCheck", return_value=mock_check):
        assert checks.with_owner_check(command) is command

        command.add_check.assert_called_once_with(mock_check)
        checks.ApplicationOwnerCheck.assert_called_once()


def test_with_author_permission_check(command):
    mock_check = object()
    with mock.patch.object(checks, "AuthorPermissionCheck", return_value=mock_check):
        assert checks.with_author_permission_check(435213)(command) is command

        command.add_check.assert_called_once_with(mock_check)
        checks.AuthorPermissionCheck.assert_called_once_with(435213)


def test_with_own_permission_check(command):
    mock_check = object()
    with mock.patch.object(checks, "OwnPermissionsCheck", return_value=mock_check):
        assert checks.with_own_permission_check(5412312)(command) is command

        command.add_check.assert_called_once_with(mock_check)
        checks.OwnPermissionsCheck.assert_called_once_with(5412312)
