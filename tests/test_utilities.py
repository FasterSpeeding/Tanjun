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

# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import typing
from collections import abc as collections
from unittest import mock

import pytest

import tanjun
from tanjun import utilities

_T = typing.TypeVar("_T")


def async_iter_mock(*values: _T) -> collections.AsyncIterable[_T]:
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
    callback = mock.AsyncMock()

    assert await utilities.await_if_async(callback) is callback.return_value


@pytest.mark.asyncio()
async def test_await_if_async_handles_sync_callback():
    callback = mock.Mock()

    assert await utilities.await_if_async(callback) is callback.return_value


@pytest.mark.asyncio()
async def test_gather_checks_handles_no_checks():
    assert await utilities.gather_checks(mock.Mock(), ()) is True


@pytest.mark.asyncio()
async def test_gather_checks_handles_failed_check():
    mock_ctx = mock.Mock(tanjun.abc.Context)
    check_1 = mock.AsyncMock()
    check_2 = mock.AsyncMock(side_effect=tanjun.FailedCheck)
    check_3 = mock.AsyncMock()

    assert await utilities.gather_checks(mock_ctx, (check_1, check_2, check_3)) is False

    check_1.assert_awaited_once_with(mock_ctx)
    check_2.assert_awaited_once_with(mock_ctx)
    check_3.assert_awaited_once_with(mock_ctx)


@pytest.mark.asyncio()
async def test_gather_checks():
    mock_ctx = mock.Mock()
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
def test_match_prefix_names(content: str, prefix: str, expected_result: typing.Optional[str]):
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


class TestCastedView:
    def test___getitem___for_non_existant_entry(self):
        mock_cast = mock.Mock()
        view = utilities.CastedView[typing.Any, typing.Any]({}, mock_cast)

        with pytest.raises(KeyError):
            view["foo"]

        mock_cast.assert_not_called()

    def test___getitem___for_buffered_entry(self):
        mock_cast = mock.Mock()
        mock_value = mock.MagicMock()
        view = utilities.CastedView[typing.Any, str]({"a": "b"}, mock_cast)
        view._buffer["a"] = mock_value

        result = view["a"]

        assert result is mock_value
        mock_cast.assert_not_called()

    def test___getitem___for_not_buffered_entry(self):
        mock_cast = mock.Mock()
        mock_value = mock.MagicMock()
        view = utilities.CastedView[typing.Any, typing.Any]({"a": mock_value}, mock_cast)

        result = view["a"]

        assert result is mock_cast.return_value
        assert view._buffer["a"] is mock_cast.return_value
        mock_cast.assert_called_once_with(mock_value)

    def test___iter__(self):
        mock_iter = mock.Mock(return_value=iter((1, 2, 3)))
        mock_dict = mock.Mock(__iter__=mock_iter)
        view = utilities.CastedView[int, int](mock_dict, mock.Mock())

        assert iter(view) is mock_iter.return_value

    def test___len___(self):
        mock_dict = mock.Mock(__len__=mock.Mock(return_value=43123))
        view = utilities.CastedView[int, int](mock_dict, mock.Mock())

        assert len(view) == 43123
