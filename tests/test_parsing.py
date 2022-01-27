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

import pytest

import tanjun


class TestUndefinedT:
    def test___new__(self):
        assert tanjun.parsing.UndefinedT() is tanjun.parsing.UndefinedT()
        assert tanjun.parsing.UndefinedT() is tanjun.parsing.UNDEFINED
        assert tanjun.parsing.UndefinedT() is tanjun.parsing.UNDEFINED_DEFAULT
        assert tanjun.parsing.UndefinedDefaultT() is tanjun.parsing.UndefinedT()
        assert tanjun.parsing.UndefinedDefaultT() is tanjun.parsing.UNDEFINED
        assert tanjun.parsing.UndefinedDefaultT() is tanjun.parsing.UNDEFINED_DEFAULT
        assert tanjun.parsing.UNDEFINED_DEFAULT is tanjun.parsing.UNDEFINED

    def test___repr__(self):
        assert repr(tanjun.parsing.UNDEFINED) == "UNDEFINED"

    def test___bool__(self):
        assert bool(tanjun.parsing.UNDEFINED) is False


@pytest.mark.skip(reason="TODO")
class Test_ShlexTokenizer:
    ...


@pytest.mark.skip(reason="TODO")
def test__covert_option_or_empty():
    ...


@pytest.mark.skip(reason="TODO")
class Test_SemanticShlex:
    ...


@pytest.mark.skip(reason="TODO")
def test_with_argument():
    ...


@pytest.mark.skip(reason="TODO")
def test_with_greedy_argument():
    ...


@pytest.mark.skip(reason="TODO")
def test_with_multi_argument():
    ...


@pytest.mark.skip(reason="TODO")
def test_with_option():
    ...


@pytest.mark.skip(reason="TODO")
def test_with_multi_option():
    ...


class TestParameter:
    ...


class TestArgument:
    ...


class TestOption:
    ...


class TestShlexParser:
    ...
