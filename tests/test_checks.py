import datetime

import mock
import pytest
from hikari import permissions

import tanjun


@pytest.fixture()
def command():
    command_ = mock.Mock(tanjun.abc.ExecutableCommand)
    command_.add_check.return_value = command_
    return command_


@pytest.fixture()
def context():
    return mock.Mock(tanjun.abc.Context)


class TestApplicationOwnerCheck:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_nsfw_check(context):
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_sfw_check(context):
    ...


def test_dm_check_for_dm(context):
    context.guild_id = None
    assert tanjun.checks.dm_check(context) is True


def test_dm_check_for_guild(context):
    context.guild_id = 3123
    assert tanjun.checks.dm_check(context, halt_execution=False, error_message=None) is False


def test_dm_check_for_guild_when_halt_execution(context):
    context.guild_id = 3123

    with pytest.raises(tanjun.HaltExecution):
        assert tanjun.checks.dm_check(context, halt_execution=True, error_message=None)


def test_dm_check_for_guild_when_error_message(context):
    context.guild_id = 3123
    with pytest.raises(tanjun.CommandError):
        assert tanjun.checks.dm_check(context, halt_execution=False, error_message="message")


def test_guild_check_for_guild(context):
    context.guild_id = 123123
    assert tanjun.checks.guild_check(context) is True


def test_guild_check_for_dm(context):
    context.guild_id = None
    assert tanjun.checks.guild_check(context, halt_execution=False, error_message=None) is False


def test_guild_check_for_dm_when_halt_execution(context):
    context.guild_id = None
    with pytest.raises(tanjun.HaltExecution):
        tanjun.checks.guild_check(context, halt_execution=True, error_message=None)


def test_guild_check_for_dm_when_error_message(context):
    context.guild_id = None
    with pytest.raises(tanjun.CommandError):
        tanjun.checks.guild_check(context, halt_execution=False, error_message="hi")


class TestPermissionCheck:
    @pytest.fixture()
    def permission_check_cls(self):
        class Check(tanjun.checks.PermissionCheck):
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

    @pytest.mark.asyncio()
    async def test___call___when_missing_permissions_and_halt_execution(self, permission_check_cls, context):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(16)
        check = permission_check_cls(422, halt_execution=True)

        with pytest.raises(tanjun.HaltExecution):
            await check(context)

        check.get_permissions.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test___call___when_missing_permissions_and_error_message(self, permission_check_cls, context):
        permission_check_cls.get_permissions.return_value = permissions.Permissions(16)
        check = permission_check_cls(422, error_message="hi")

        with pytest.raises(tanjun.CommandError):
            await check(context)

        check.get_permissions.assert_awaited_once_with(context)


class TestAuthorPermissionCheck:
    ...


class TestOwnPermissionsCheck:
    ...


def test_with_dm_check(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "dm_check") as dm_check:
        assert tanjun.checks.with_dm_check(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is dm_check.return_value

        command.add_check.assert_called_once()
        dm_check.assert_called_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in DMs"
        )


def test_with_dm_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "dm_check") as dm_check:
        assert tanjun.checks.with_dm_check(halt_execution=True, error_message="message")(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is dm_check.return_value

        command.add_check.assert_called_once()
        dm_check.assert_called_once_with(mock_ctx, halt_execution=True, error_message="message")


def test_with_guild_check(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "guild_check") as guild_check:
        assert tanjun.checks.with_guild_check(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is guild_check.return_value

        command.add_check.assert_called_once()
        guild_check.assert_called_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in guild channels"
        )


def test_with_guild_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "guild_check") as guild_check:
        assert tanjun.checks.with_guild_check(halt_execution=True, error_message="eee")(command) is command
        assert command.add_check.mock_calls[0].args[0](mock_ctx) is guild_check.return_value

        command.add_check.assert_called_once()
        guild_check.assert_called_once_with(mock_ctx, halt_execution=True, error_message="eee")


@pytest.mark.asyncio()
async def test_with_nsfw_check(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "nsfw_check") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is nsfw_check.return_value

        command.add_check.assert_called_once()
        nsfw_check.assert_awaited_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in NSFW channels"
        )


@pytest.mark.asyncio()
async def test_with_nsfw_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "nsfw_check") as nsfw_check:
        assert tanjun.checks.with_nsfw_check(halt_execution=True, error_message="banned!!!")(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is nsfw_check.return_value

        command.add_check.assert_called_once()
        nsfw_check.assert_awaited_once_with(mock_ctx, halt_execution=True, error_message="banned!!!")


@pytest.mark.asyncio()
async def test_with_sfw_check(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "sfw_check") as sfw_check:
        assert tanjun.checks.with_sfw_check(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is sfw_check.return_value

        command.add_check.assert_called_once()
        sfw_check.assert_awaited_once_with(
            mock_ctx, halt_execution=False, error_message="Command can only be used in SFW channels"
        )


@pytest.mark.asyncio()
async def test_sfw_check_with_keyword_arguments(command):
    mock_ctx = object()
    with mock.patch.object(tanjun.checks, "sfw_check") as sfw_check:
        assert tanjun.checks.with_sfw_check(halt_execution=True, error_message="bango")(command) is command
        assert await command.add_check.mock_calls[0].args[0](mock_ctx) is sfw_check.return_value

        command.add_check.assert_called_once()
        sfw_check.assert_awaited_once_with(mock_ctx, halt_execution=True, error_message="bango")


def test_with_owner_check(command):
    with mock.patch.object(tanjun.checks, "ApplicationOwnerCheck") as ApplicationOwnerCheck:
        assert tanjun.checks.with_owner_check(command) is command

        command.add_check.assert_called_once_with(ApplicationOwnerCheck.return_value)
        ApplicationOwnerCheck.assert_called_once_with(
            halt_execution=False,
            error_message="Only bot owners can use this command",
            expire_delta=datetime.timedelta(minutes=5),
            owner_ids=None,
        )


def test_with_owner_check_with_keyword_arguments(command):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "ApplicationOwnerCheck", return_value=mock_check):
        result = tanjun.checks.with_owner_check(
            halt_execution=True,
            error_message="dango",
            expire_delta=datetime.timedelta(minutes=10),
            owner_ids=(123,),
        )(command)
        assert result is command

        command.add_check.assert_called_once()
        tanjun.checks.ApplicationOwnerCheck.assert_called_once_with(
            halt_execution=True, error_message="dango", expire_delta=datetime.timedelta(minutes=10), owner_ids=(123,)
        )


def test_with_author_permission_check(command):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "AuthorPermissionCheck", return_value=mock_check):
        assert (
            tanjun.checks.with_author_permission_check(435213, halt_execution=True, error_message="bye")(command)
            is command
        )

        command.add_check.assert_called_once_with(mock_check)
        tanjun.checks.AuthorPermissionCheck.assert_called_once_with(435213, halt_execution=True, error_message="bye")


def test_with_own_permission_check(command):
    mock_check = object()
    with mock.patch.object(tanjun.checks, "OwnPermissionsCheck", return_value=mock_check):
        assert (
            tanjun.checks.with_own_permission_check(5412312, halt_execution=True, error_message="hi")(command)
            is command
        )

        command.add_check.assert_called_once_with(mock_check)
        tanjun.checks.OwnPermissionsCheck.assert_called_once_with(5412312, halt_execution=True, error_message="hi")
