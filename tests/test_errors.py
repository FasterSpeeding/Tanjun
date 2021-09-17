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

# pyright: reportIncompatibleMethodOverride=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

from unittest import mock

import pytest

import tanjun


class TestMissingDependencyError:
    def test__init__(self):
        assert tanjun.MissingDependencyError("foo").message == "foo"


class TestCommandError:
    def test__init__(self):
        assert tanjun.CommandError("foo").message == "foo"

    def test__init__when_no_message(self):
        with pytest.raises(ValueError, match="Response message must have at least 1 character."):
            tanjun.CommandError("")

    @pytest.mark.parametrize("message", ["i" * 2001, "a" * 2010])
    def test__init___when_message_len_out_of_bounds(self, message: str):
        with pytest.raises(ValueError, match="Error message cannot be over 2_000 characters long."):
            tanjun.CommandError(message)

    def test__str__(self):
        assert str(tanjun.CommandError("bar")) == "bar"


class TestParserError:
    def test__init__(self):
        error = tanjun.ParserError("bank", "no u")

        assert error.message == "bank"
        assert error.parameter == "no u"

    def test__str__(self):
        assert str(tanjun.ParserError("bankette", "now2")) == "bankette"


class TestConversionError:
    def test__init__(self):
        mock_error = mock.Mock()

        error = tanjun.ConversionError("bankettete", "aye", [mock_error])

        assert error.message == "bankettete"
        assert error.parameter == "aye"
        assert error.errors == (mock_error,)


class TestNotEnoughArgumentsError:
    def test__init__(self):
        error = tanjun.NotEnoughArgumentsError("aye", "naye")

        assert error.message == "aye"
        assert error.parameter == "naye"


class TestTooManyArgumentsError:
    def test__init__(self):
        error = tanjun.TooManyArgumentsError("blank", "fama")

        assert error.message == "blank"
        assert error.parameter == "fama"
