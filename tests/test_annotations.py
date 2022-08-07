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

import typing

import hikari
import pytest

import tanjun
from tanjun import annotations


def test_with_annotated_args_with_message_command():
    ...


def test_with_annotated_args_with_message_command_and_incompatible_parser_set():
    ...


def test_with_annotated_args_with_slash_command():
    ...


def test_with_annotated_args_with_slash_command_missing_option_description():
    ...


def test_with_annotated_args_with_std_range():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Int, range(123, 345), "nyaa"],
        other_value: typing.Annotated[annotations.Int, 22:5568, "sex"] = 44,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="value",
            description="nyaa",
            is_required=True,
            min_value=123,
            max_value=344,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            description="sex",
            is_required=False,
            min_value=22,
            max_value=5567,
        ),
    ]

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value == 344
    assert argument.min_value == 123

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.is_multi is False
    assert option.max_value == 5567
    assert option.min_value == 22


def test_with_annotated_args_with_std_slice():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Int, 324:653, "meow"],
        other_value: typing.Annotated[annotations.Int, 444:555, "blam"] = 44,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="value",
            description="meow",
            is_required=True,
            min_value=324,
            max_value=652,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            description="blam",
            is_required=False,
            min_value=444,
            max_value=554,
        ),
    ]

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value == 652
    assert argument.min_value == 324

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.is_multi is False
    assert option.max_value == 554
    assert option.min_value == 444


def test_with_annotated_args_with_no_annotations():
    ...


def test_with_annotated_args_with_defaultless_flag_argument():
    ...


def test_with_annotated_args_shorthand_generics():
    ...


def test_with_annotated_args_generic_choices_overrides_type():
    ...


def test_with_annotated_args_with_ranged():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Int, annotations.Ranged(44, 55), "meow"],
        other_value: typing.Annotated[annotations.Float, annotations.Ranged(5433, 6524.32), "bye bye"] = 5,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="value",
            description="meow",
            is_required=True,
            min_value=44,
            max_value=55,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="other_value",
            description="bye bye",
            is_required=False,
            min_value=5433,
            max_value=6524.32,
        ),
    ]

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value == 55
    assert argument.min_value == 44

    assert len(callback.wrapped_command.parser.options) == 1

    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default == 5
    assert option.is_multi is False
    assert option.max_value == 6524.32
    assert option.min_value == 5433


@pytest.mark.parametrize(
    ("min_value", "max_value", "converter", "otype"),
    [
        (123.132, 321, float, hikari.OptionType.FLOAT),
        (123, 321, int, hikari.OptionType.INTEGER),
        (431, 1232.321, float, hikari.OptionType.FLOAT),
        (452.432, 55234.2134, float, hikari.OptionType.FLOAT),
    ],
)
def test_with_annotated_args_with_generic_ranged(
    min_value: typing.Union[float, int],
    max_value: typing.Union[float, int],
    converter: typing.Union[type[float], type[int]],
    otype: hikari.OptionType,
):
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[annotations.Ranged[min_value, max_value], "meow"],
        other_number: typing.Annotated[annotations.Ranged[min_value, max_value], "nom"] = 443,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=otype,
            name="number",
            description="meow",
            is_required=True,
            min_value=min_value,
            max_value=max_value,
        ),
        hikari.CommandOption(
            type=otype,
            name="other_number",
            description="nom",
            is_required=False,
            min_value=min_value,
            max_value=max_value,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is otype

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 443
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is otype

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value == max_value
    assert argument.min_value == min_value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default == 443
    assert option.is_multi is False
    assert option.max_value == max_value
    assert option.min_value == min_value


def test_with_annotated_args_ranged_when_not_valid_for_type():
    ...


def test_with_annotated_args_with_min():
    ...


@pytest.mark.parametrize(
    ("value", "converter", "otype"), [(123, int, hikari.OptionType.INTEGER), (123.321, float, hikari.OptionType.FLOAT)]
)
def test_with_annotated_args_with_generic_min(
    value: typing.Union[int, float], converter: typing.Union[type[int], type[float]], otype: hikari.OptionType
):
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[annotations.Min[value], "bee"],
        other_number: typing.Annotated[annotations.Min[value], "buzz"] = 321,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=otype,
            name="number",
            description="bee",
            is_required=True,
            min_value=value,
            max_value=None,
        ),
        hikari.CommandOption(
            type=otype,
            name="other_number",
            description="buzz",
            is_required=False,
            min_value=value,
            max_value=None,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is otype

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 321
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is otype

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value is None
    assert argument.min_value == value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default == 321
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value == value


def test_with_annotated_args_with_min_when_not_valid_for_type():
    ...


def test_with_annotated_args_with_max():
    ...


@pytest.mark.parametrize(
    ("value", "converter", "otype"), [(543, int, hikari.OptionType.INTEGER), (234.432, float, hikari.OptionType.FLOAT)]
)
def test_with_annotated_args_with_generic_max(
    value: typing.Union[int, float], converter: typing.Union[type[int], type[float]], otype: hikari.OptionType
):
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[annotations.Max[value], "eee"],
        other_number: typing.Annotated[annotations.Max[value], "eep"] = 54234,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=otype,
            name="number",
            description="eee",
            is_required=True,
            min_value=None,
            max_value=value,
        ),
        hikari.CommandOption(
            type=otype,
            name="other_number",
            description="eep",
            is_required=False,
            min_value=None,
            max_value=value,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is otype

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 54234
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is otype

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value == value
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default == 54234
    assert option.is_multi is False
    assert option.max_value == value
    assert option.min_value is None


def test_with_annotated_args_with_max_when_not_valid_for_type():
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
