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

import typing

import pytest


def test_with_annotated_args_with_message_command():
    ...


def test_with_annotated_args_with_message_command_and_incompatible_parser_set():
    ...


def test_with_annotated_args_with_slash_command():
    ...


def test_with_annotated_args_with_slash_command_missing_option_description():
    ...


def test_with_annotated_args_with_range():
    ...


def test_with_annotated_args_with_slice():
    ...


def test_with_annotated_args_with_no_annotations():
    ...


def test_with_annotated_args_with_defaultless_flag_argument():
    ...


def test_with_annotated_args_shorthand_generics():
    ...


def test_with_annotated_args_generic_choices_overrides_type():
    ...


@pytest.mark.parametrize(
    ("min_value", "max_value", "cls"), [(123.132, 321, float), (123, 321, int), (431, 123.321, float)]
)
def test_with_annotated_args_ranged_selects_type(
    min_value: typing.Union[float, int], max_value: typing.Union[float, int], cls: typing.Union[type[float], type[int]]
):
    ...


def test_with_annotated_args_overridden_name():
    ...


def test_with_annotated_args_when_wrapping_slash():
    ...


def test_with_annotated_args_when_wrapping_slash_and_follow_wrapped():
    ...


def test_with_annotated_args_when_wrapping_message():
    ...


def test_with_annotated_args_when_wrapping_message_and_follow_wrapped():
    ...


# choice not str, choice not int, choice not float
# min-max not int, min-max not float
