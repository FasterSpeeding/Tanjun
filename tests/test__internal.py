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

# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import typing
from unittest import mock

import pytest

import tanjun
from tanjun import _internal


@pytest.mark.asyncio()
async def test_gather_checks_handles_no_checks():
    mock_ctx = mock.AsyncMock()
    assert await _internal.gather_checks(mock_ctx, ()) is True

    mock_ctx.call_with_async_di.assert_not_called()


@pytest.mark.asyncio()
async def test_gather_checks_handles_failed_check():
    mock_ctx = mock.Mock()
    mock_ctx.call_with_async_di = mock.AsyncMock(side_effect=[True, False, True])
    check_1 = mock.Mock()
    check_2 = mock.Mock()
    check_3 = mock.Mock()

    assert await _internal.gather_checks(mock_ctx, (check_1, check_2, check_3)) is False

    mock_ctx.call_with_async_di.assert_has_awaits(
        [mock.call(check_1, mock_ctx), mock.call(check_2, mock_ctx), mock.call(check_3, mock_ctx)]
    )


@pytest.mark.asyncio()
async def test_gather_checks_handles_check_failed_by_raise():
    mock_ctx = mock.Mock()
    mock_ctx.call_with_async_di = mock.AsyncMock(side_effect=[True, tanjun.FailedCheck, True])
    check_1 = mock.Mock()
    check_2 = mock.Mock()
    check_3 = mock.Mock()

    assert await _internal.gather_checks(mock_ctx, (check_1, check_2, check_3)) is False

    mock_ctx.call_with_async_di.assert_has_awaits(
        [mock.call(check_1, mock_ctx), mock.call(check_2, mock_ctx), mock.call(check_3, mock_ctx)]
    )


@pytest.mark.asyncio()
async def test_gather_checks():
    mock_ctx = mock.Mock()
    mock_ctx.call_with_async_di = mock.AsyncMock(side_effect=[True, True, True])
    check_1 = mock.Mock()
    check_2 = mock.Mock()
    check_3 = mock.Mock()

    assert await _internal.gather_checks(mock_ctx, (check_1, check_2, check_3)) is True

    mock_ctx.call_with_async_di.assert_has_awaits(
        [mock.call(check_1, mock_ctx), mock.call(check_2, mock_ctx), mock.call(check_3, mock_ctx)]
    )


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
    assert _internal.match_prefix_names(content, prefix) == expected_result


class TestCastedView:
    def test___getitem___for_non_existant_entry(self):
        mock_cast = mock.Mock()
        view = _internal.CastedView[typing.Any, typing.Any, typing.Any]({}, mock_cast)

        with pytest.raises(KeyError):
            view["foo"]

        mock_cast.assert_not_called()

    def test___getitem___for_buffered_entry(self):
        mock_cast = mock.Mock()
        mock_value = mock.MagicMock()
        view = _internal.CastedView[typing.Any, str, typing.Any]({"a": "b"}, mock_cast)
        view._buffer["a"] = mock_value

        result = view["a"]

        assert result is mock_value
        mock_cast.assert_not_called()

    def test___getitem___for_not_buffered_entry(self):
        mock_cast = mock.Mock()
        mock_value = mock.MagicMock()
        view = _internal.CastedView[typing.Any, typing.Any, typing.Any]({"a": mock_value}, mock_cast)

        result = view["a"]

        assert result is mock_cast.return_value
        assert view._buffer["a"] is mock_cast.return_value
        mock_cast.assert_called_once_with(mock_value)

    def test___iter__(self):
        mock_iter = mock.Mock(return_value=iter((1, 2, 3)))
        mock_dict = mock.Mock(__iter__=mock_iter)
        view = _internal.CastedView[int, int, typing.Any](mock_dict, mock.Mock())

        assert iter(view) is mock_iter.return_value

    def test___len___(self):
        mock_dict = mock.Mock(__len__=mock.Mock(return_value=43123))
        view = _internal.CastedView[int, int, typing.Any](mock_dict, mock.Mock())

        assert len(view) == 43123
