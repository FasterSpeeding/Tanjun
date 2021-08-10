import mock
import pytest

from tanjun import errors
from tanjun import utilities


def async_iter_mock(*values):
    return mock.Mock(__aiter__=mock.Mock(return_value=mock.Mock(__anext__=mock.AsyncMock(side_effect=values))))


@pytest.mark.asyncio()
async def test_async_chain():
    resources = (
        async_iter_mock(1, 2, 3),
        async_iter_mock(99, 55, 44),
        async_iter_mock(444, 333, 222),
    )

    results = [result async for result in utilities.async_chain(resources)]

    assert results == [1, 2, 3, 99, 55, 44, 444, 333, 222]


@pytest.mark.asyncio()
async def test_await_if_async_handles_async_callback():
    mock_result = object()
    callback = mock.AsyncMock(return_value=mock_result)

    assert await utilities.await_if_async(callback) is mock_result


@pytest.mark.asyncio()
async def test_await_if_async_handles_sync_callback():
    mock_result = object()
    callback = mock.Mock(return_value=mock_result)

    assert await utilities.await_if_async(callback) is mock_result


@pytest.mark.asyncio()
async def test_gather_checks_handles_no_checks():
    assert await utilities.gather_checks(object(), ()) is True


@pytest.mark.asyncio()
async def test_gather_checks_handles_faiedl_check():
    mock_ctx = object()
    check_1 = mock.AsyncMock()
    check_2 = mock.AsyncMock(side_effect=errors.FailedCheck)
    check_3 = mock.AsyncMock()

    assert await utilities.gather_checks(mock_ctx, (check_1, check_2, check_3)) is False

    check_1.assert_awaited_once_with(mock_ctx)
    check_2.assert_awaited_once_with(mock_ctx)
    check_3.assert_awaited_once_with(mock_ctx)


@pytest.mark.asyncio()
async def test_gather_checks():
    mock_ctx = object()
    check_1 = mock.AsyncMock()
    check_2 = mock.AsyncMock()
    check_3 = mock.AsyncMock()

    assert await utilities.gather_checks(mock_ctx, (check_1, check_2, check_3)) is True

    check_1.assert_awaited_once_with(mock_ctx)
    check_2.assert_awaited_once_with(mock_ctx)
    check_3.assert_awaited_once_with(mock_ctx)


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_resource():
    ...


@pytest.mark.parametrize(
    ("content", "prefix", "expected_result"),
    [
        ("no go sir", ("no", "home", "blow"), "no"),
        ("hime", ("hi", "hime", "boomer"), "hime"),
        ("boomer", ("boo", "boomer", "no u"), "boomer"),
        ("ok boomer", ("no", "nani"), None),
        ("", ("nannnnni",), None),
        ("ok ok ok", (), None),
    ],
)
def test_match_prefix_names(content, prefix, expected_result):
    assert utilities.match_prefix_names(content, prefix) == expected_result


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions_when_guild_owner():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions_when_admin_role():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions_when_no_channel():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_guild_owner():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_admin_role():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_no_channel():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_channel_object_provided():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_for_uncached_entities():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_for_no_cache():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_everyone_permissions():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_everyone_permissions_admin_role():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_everyone_permissions_no_channel():
    ...


@pytest.mark.asyncio()
async def test_fetch_everyone_permissions():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_admin_role():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_for_uncached_entities():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_for_no_cache():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_no_channel():
    ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_channel_object_provided():
    ...
