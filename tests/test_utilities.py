import mock
import pytest

from tanjun import errors
from tanjun import utilities


@pytest.mark.asyncio
async def test_async_chain():
    resources = (
        mock.AsyncMock(return_value=[1, 2, 3]),
        mock.AsyncMock(return_value=[99, 55, 44]),
        mock.AsyncMock(return_value=[444, 333, 222]),
    )

    results = [result async for result in utilities.async_chain(resources)]

    assert results == [1, 2, 3, 99, 55, 44, 444, 333, 222]


@pytest.mark.asyncio
async def test_await_if_async_handles_async_callback():
    mock_result = object()
    callback = mock.AsyncMock(return_value=mock_result)

    assert await utilities.await_if_async(callback) is mock_result


@pytest.mark.asyncio
async def test_await_if_async_handles_sync_callback():
    mock_result = object()
    callback = mock.Mock(return_value=mock_result)

    assert await utilities.await_if_async(callback) is mock_result


@pytest.mark.asyncio
async def test_gather_checks_handles_no_checks():
    assert await utilities.gather_checks(()) is True


@pytest.mark.asyncio
async def test_gather_checks_handles_raised_check():
    check_1 = mock.AsyncMock(return_value=True)
    check_2 = mock.AsyncMock(side_effect=errors.FailedCheck)
    check_3 = mock.AsyncMock()

    assert await utilities.gather_checks((check_1(), check_2(), check_3())) is False

    check_1.assert_awaited_once()
    check_2.assert_awaited_once()
    check_3.assert_awaited_once()


@pytest.mark.asyncio
async def test_gather_checks_handles_false_return():
    check_1 = mock.AsyncMock(return_value=True)
    check_2 = mock.AsyncMock(return_value=False)
    check_3 = mock.AsyncMock()

    assert await utilities.gather_checks((check_1(), check_2(), check_3())) is False

    check_1.assert_awaited_once()
    check_2.assert_awaited_once()
    check_3.assert_awaited_once()


@pytest.mark.asyncio
async def test_gather_checks_handles_raised_check():
    check_1 = mock.AsyncMock(return_value=True)
    check_2 = mock.AsyncMock(return_value=None)
    check_3 = mock.AsyncMock(return_value=True)

    assert await utilities.gather_checks((check_1(), check_2(), check_3())) is True

    check_1.assert_awaited_once()
    check_2.assert_awaited_once()
    check_3.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_resource():
    ...


@pytest.mark.asyncio
async def test_calculate_permissions_for_cached_entities():
    ...


@pytest.mark.asyncio
async def test_calculate_permissions_for_uncached_entities():
    ...


@pytest.mark.asyncio
async def test_calculate_permissions_for_no_cache():
    ...


def test_with_function_wrapping():
    ...


def test_try_find_type_finds_type():
    ...


def test_try_find_type_finds_none():
    ...
