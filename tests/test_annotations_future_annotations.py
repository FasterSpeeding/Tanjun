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
from __future__ import annotations as _

import enum
import inspect
import re
import sys
import typing
from collections import abc as collections
from unittest import mock

import alluka
import hikari
import pytest

import tanjun
from tanjun import annotations

# pyright: reportPrivateUsage=none


def test_where_no_signature():
    with pytest.raises(ValueError, match=".+"):
        inspect.Signature.from_callable(int)

    command = tanjun.as_message_command("command")(
        tanjun.as_slash_command("command", "description")(int)  # type: ignore
    )

    annotations.with_annotated_args(command)

    assert command.parser is None
    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert command.wrapped_command.build().options == []
    assert command.wrapped_command._tracked_options == {}


def test_where_no_signature_with_parser_already_set():
    with pytest.raises(ValueError, match=".+"):
        inspect.Signature.from_callable(int)

    command = tanjun.as_message_command("command")(
        tanjun.as_slash_command("command", "description")(int)  # type: ignore
    ).set_parser(tanjun.ShlexParser())

    annotations.with_annotated_args(command)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert command.parser.arguments == []
    assert command.parser.options == []
    assert command.wrapped_command.build().options == []
    assert command.wrapped_command._tracked_options == {}


def test_with_message_command_and_incompatible_parser_set():
    mock_parser = mock.Mock(tanjun.abc.MessageParser)

    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.MessageContext, foo: annotations.Int):
        ...

    command.set_parser(mock_parser)

    with pytest.raises(TypeError, match="Expected parser to be an instance of tanjun.parsing.AbstractOptionParser"):
        annotations.with_annotated_args(command)


def test_with_nested_message_command_and_incompatible_parser_set():
    mock_parser = mock.Mock(tanjun.abc.MessageParser)

    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("command", "description")
    async def command(ctx: tanjun.abc.MessageContext, foo: typing.Annotated[annotations.Int, "desc"]):
        ...

    command.set_parser(mock_parser)

    with pytest.raises(TypeError, match="Expected parser to be an instance of tanjun.parsing.AbstractOptionParser"):
        annotations.with_annotated_args(follow_wrapped=True)(command)


def test_with_no_annotations():
    @annotations.with_annotated_args  # pyright: ignore [ reportUnknownArgumentType ]
    @tanjun.as_slash_command("meow", "nyaa")
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context,
        injected: alluka.Injected[int],
        yeat,  # type: ignore
        other_injected: str = alluka.inject(type=str),
    ) -> None:
        ...

    assert command.build().options == []
    assert command._tracked_options == {}
    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_with_no_annotations_but_message_parser_already_set():
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context,
        injected: alluka.Injected[int],
        beat,  # type: ignore
        other_injected: str = alluka.inject(type=str),
    ) -> None:
        ...

    command.set_parser(tanjun.ShlexParser())

    annotations.with_annotated_args(command)  # pyright: ignore [ reportUnknownArgumentType ]

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert command.parser.arguments == []
    assert command.parser.options == []


def test_with_slash_command_missing_option_description():
    @tanjun.as_slash_command("meep", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        meow: typing.Annotated[annotations.Bool, "ok"],
        miss: annotations.Str,
        nyaa: typing.Annotated[annotations.Channel, "bye"],
    ) -> None:
        ...

    with pytest.raises(ValueError, match="Missing description for argument 'miss'"):
        annotations.with_annotated_args(callback)


def test_when_wrapping_slash_but_not_follow_wrapped():
    @annotations.with_annotated_args
    @tanjun.as_message_command("meep")
    @tanjun.as_slash_command("boop", "description")
    async def command(
        ctx: tanjun.abc.Context,
        field: typing.Annotated[annotations.Int, "description"],
        other_field: typing.Annotated[annotations.Str, "yo"] = "",
    ):
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)
    assert command.parser.arguments
    assert command.parser.options
    assert command.wrapped_command.build().options == []
    assert command.wrapped_command._tracked_options == {}


def test_when_wrapping_message_but_not_follow_wrapped():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("boop", "description")
    @tanjun.as_message_command("meep")
    async def command(ctx: tanjun.abc.Context, field: typing.Annotated[annotations.Int, "description"]):
        ...

    assert command.build().options
    assert command._tracked_options
    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_when_wrapping_message_but_not_follow_wrapped_parser_already_set():
    @tanjun.as_slash_command("boop", "description")
    @tanjun.as_message_command("meep")
    async def command(ctx: tanjun.abc.Context, field: typing.Annotated[annotations.Int, "description"]):
        ...

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    command.wrapped_command.set_parser(tanjun.ShlexParser())

    annotations.with_annotated_args(command)

    assert command.build().options
    assert command._tracked_options
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)
    assert command.wrapped_command.parser.arguments == []
    assert command.wrapped_command.parser.options == []


def test_when_follow_wrapping_and_wrapping_unsupported_command():
    async def mock_callback(
        ctx: tanjun.abc.MessageContext,
        value: annotations.Str,
        other_value: annotations.Bool = False,
    ) -> None:
        ...

    command = tanjun.as_message_command("beep")(mock.Mock(tanjun.abc.SlashCommand, callback=mock_callback))
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command  # type: ignore

    annotations.with_annotated_args(follow_wrapped=True)(command)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 1
    assert len(command.parser.options) == 1


def test_with_with_std_range():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Int, range(123, 345), "nyaa"],
        other_value: typing.Annotated[annotations.Int, range(22, 5568), "sex"] = 44,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="value",
            channel_types=None,
            description="nyaa",
            is_required=True,
            min_value=123,
            max_value=344,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            channel_types=None,
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
    assert argument.min_value == 123
    assert argument.max_value == 344

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 22
    assert option.max_value == 5567


def test_with_with_backwards_std_range():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Int, range(542, 111, -1), "nyaa"],
        other_value: typing.Annotated[annotations.Int, range(3334, 43, -1), "sex"] = 44,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="value",
            channel_types=None,
            description="nyaa",
            is_required=True,
            min_value=110,
            max_value=542,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            channel_types=None,
            description="sex",
            is_required=False,
            min_value=42,
            max_value=3334,
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
    assert argument.min_value == 110
    assert argument.max_value == 542

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 42
    assert option.max_value == 3334


def test_with_std_slice():
    @annotations.with_annotated_args(follow_wrapped=True)
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
            channel_types=None,
            description="meow",
            is_required=True,
            min_value=324,
            max_value=652,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            channel_types=None,
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
    assert argument.min_value == 324
    assert argument.max_value == 652

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 444
    assert option.max_value == 554


def test_with_backwards_std_slice():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Int, 444:233:-1, "meow"],
        other_value: typing.Annotated[annotations.Int, 664:422:-1, "blam"] = 44,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="value",
            channel_types=None,
            description="meow",
            is_required=True,
            min_value=232,
            max_value=444,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            channel_types=None,
            description="blam",
            is_required=False,
            min_value=421,
            max_value=664,
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
    assert argument.min_value == 232
    assert argument.max_value == 444

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 421
    assert option.max_value == 664


_ChoiceT = typing.TypeVar("_ChoiceT", str, int, float)


@pytest.mark.parametrize(
    ("type_cls", "option_type", "choices", "result"),
    [
        # With choices dict
        (
            annotations.Int,
            hikari.OptionType.INTEGER,
            {"pico": 4, "nano": 33, "micro": 69, "milli": 420},
            [
                hikari.CommandChoice(name="pico", value=4),
                hikari.CommandChoice(name="nano", value=33),
                hikari.CommandChoice(name="micro", value=69),
                hikari.CommandChoice(name="milli", value=420),
            ],
        ),
        (
            annotations.Str,
            hikari.OptionType.STRING,
            {"Great": "man", "Amazon": "rainforest", "Go": "home", "Yeet": "beep"},
            [
                hikari.CommandChoice(name="Great", value="man"),
                hikari.CommandChoice(name="Amazon", value="rainforest"),
                hikari.CommandChoice(name="Go", value="home"),
                hikari.CommandChoice(name="Yeet", value="beep"),
            ],
        ),
        (
            annotations.Float,
            hikari.OptionType.FLOAT,
            {"Small": 6.9420, "medium": 69.420, "large": 240.69},
            [
                hikari.CommandChoice(name="Small", value=6.9420),
                hikari.CommandChoice(name="medium", value=69.420),
                hikari.CommandChoice(name="large", value=240.69),
            ],
        ),
        # With sequence of choice tuples
        (
            annotations.Int,
            hikari.OptionType.INTEGER,
            [("Beep", 541234), ("Boop", 12343), ("Boom", 3433), ("Nyaa", 1919191), ("Slutty", 696969)],
            [
                hikari.CommandChoice(name="Beep", value=541234),
                hikari.CommandChoice(name="Boop", value=12343),
                hikari.CommandChoice(name="Boom", value=3433),
                hikari.CommandChoice(name="Nyaa", value=1919191),
                hikari.CommandChoice(name="Slutty", value=696969),
            ],
        ),
        (
            annotations.Str,
            hikari.OptionType.STRING,
            [("Halo", "yeet"), ("Catgirl", "neko"), ("Meow", "slutty"), ("Trans", "gender")],
            [
                hikari.CommandChoice(name="Halo", value="yeet"),
                hikari.CommandChoice(name="Catgirl", value="neko"),
                hikari.CommandChoice(name="Meow", value="slutty"),
                hikari.CommandChoice(name="Trans", value="gender"),
            ],
        ),
        (
            annotations.Float,
            hikari.OptionType.FLOAT,
            [("Happy", 0.0), ("Sad", 99.999), ("where", 39393.2)],
            [
                hikari.CommandChoice(name="Happy", value=0.0),
                hikari.CommandChoice(name="Sad", value=99.999),
                hikari.CommandChoice(name="where", value=39393.2),
            ],
        ),
        # With sequence of choice values
        (
            annotations.Int,
            hikari.OptionType.INTEGER,
            [123, 543, 234, 765, 876],
            [
                hikari.CommandChoice(name="123", value=123),
                hikari.CommandChoice(name="543", value=543),
                hikari.CommandChoice(name="234", value=234),
                hikari.CommandChoice(name="765", value=765),
                hikari.CommandChoice(name="876", value=876),
            ],
        ),
        (
            annotations.Str,
            hikari.OptionType.STRING,
            ["hi", "bye", "meow", "nyaa", "trans"],
            [
                hikari.CommandChoice(name="hi", value="hi"),
                hikari.CommandChoice(name="bye", value="bye"),
                hikari.CommandChoice(name="meow", value="meow"),
                hikari.CommandChoice(name="nyaa", value="nyaa"),
                hikari.CommandChoice(name="trans", value="trans"),
            ],
        ),
        (
            annotations.Float,
            hikari.OptionType.FLOAT,
            [543.1234, 123.654, 123.543, 123.432],
            [
                hikari.CommandChoice(name="543.1234", value=543.1234),
                hikari.CommandChoice(name="123.654", value=123.654),
                hikari.CommandChoice(name="123.543", value=123.543),
                hikari.CommandChoice(name="123.432", value=123.432),
            ],
        ),
    ],
)
def test_choices(
    type_cls: type[_ChoiceT],
    option_type: hikari.OptionType,
    choices: collections.Sequence[_ChoiceT],
    result: collections.Sequence[hikari.CommandChoice],
):
    global choices_
    global type_cls_
    choices_ = choices
    type_cls_ = type_cls

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        nope: typing.Annotated[type_cls_, annotations.Choices(choices_), "default"],
        boo: typing.Annotated[type_cls_, annotations.Choices(choices_), "be"] = "hi",
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type,
            name="nope",
            channel_types=None,
            description="default",
            is_required=True,
            choices=result,
        ),
        hikari.CommandOption(
            type=option_type,
            name="boo",
            channel_types=None,
            description="be",
            is_required=False,
            choices=result,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["nope"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is (option_type is hikari.OptionType.FLOAT)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nope"
    assert tracked_option.name == "nope"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["boo"]
    assert tracked_option.converters == []
    assert tracked_option.default == "hi"
    assert tracked_option.is_always_float is (option_type is hikari.OptionType.FLOAT)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "boo"
    assert tracked_option.name == "boo"
    assert tracked_option.type is option_type


@pytest.mark.parametrize(
    ("type_", "type_repr", "choices", "mismatched_type"),
    [
        (annotations.Int, int, [123, 321, 432.234, 543, "ok"], float),
        (annotations.Int, int, [4312, 123, "123", 432, 453, 123.321], str),
        (annotations.Str, str, ["hi", "bye", 123.321, "meow", 123], float),
        (annotations.Str, str, ["nyaa", "backup", 123, "bonk", 123.321], int),
        (annotations.Float, float, [123.321, 432.1234, "meow", 123], str),
        (annotations.Float, float, [123.321, 432.234, 312, 321.123, "ok"], int),
        (annotations.Int, int, [("nyaa", 123), ("meow", 4312), ("nap", 432.234), ("bep", "123")], float),
        (annotations.Int, int, [("meep", 123), ("blam", 3411), ("baguette", "blam"), ("bye", 123.321)], str),
        (annotations.Str, str, [("tell", "me"), ("y", "ain't"), ("nothing", -1.2), ("a", 30)], float),
        (annotations.Str, str, [("i", "am"), ("going", "very"), ("insane", 4), ("u", 2.0)], int),
        (annotations.Float, float, [("tell", 123.321), ("meow", "hi"), ("no", 123)], str),
        (annotations.Float, float, [("eep", 123.321), ("beep", 234.432), ("boom", 1), ("bye", "o")], int),
        (annotations.Int, int, {"bye": 1, "go": 2, "be": 3.3, "eep": "a"}, float),
        (annotations.Int, int, {"ea": 1, "meow": 2, "me": "ow", "nyaa": 2.2}, str),
        (annotations.Str, str, {"strings": "4", "every": 1.1, "bye": 4}, float),
        (annotations.Str, str, {"str": "eep", "beep": "boop", "lol": 23, "meow": 32.23}, int),
        (annotations.Float, float, {"float": 0.2, "my": 2.3, "boat": "pls", "uwu": 2}, str),
        (annotations.Float, float, {"meow": 123.321, "meep": 1, "beep": "ok"}, int),
    ],
)
def test_choices_and_mixed_values(
    type_: type[_ChoiceT],
    type_repr: type[_ChoiceT],
    choices: typing.Union[
        collections.Sequence[_ChoiceT], collections.Sequence[tuple[str, _ChoiceT]], collections.Mapping[str, _ChoiceT]
    ],
    mismatched_type: type[typing.Any],
):
    global choices_
    global type__
    choices_ = choices
    type__ = type_

    @tanjun.as_slash_command("command", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        nom: typing.Annotated[type__, annotations.Choices(choices_), "description"],  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        ValueError, match=f"Choice of type {mismatched_type.__name__} is not valid for a {type_repr.__name__} argument"
    ):
        annotations.with_annotated_args(callback)


def test_with_generic_float_choices():
    global Choices1

    class Choices1(float, enum.Enum):
        Foo = 123.321
        Bar = 543.123
        Blam = 432.123
        Ok = 43.34

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        nom: typing.Annotated[annotations.Choices[Choices1], "description"],
        boom: typing.Annotated[annotations.Choices[Choices1], "bag"] = Choices1.Blam,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="nom",
            channel_types=None,
            description="description",
            is_required=True,
            choices=[
                hikari.CommandChoice(name="Foo", value=123.321),
                hikari.CommandChoice(name="Bar", value=543.123),
                hikari.CommandChoice(name="Blam", value=432.123),
                hikari.CommandChoice(name="Ok", value=43.34),
            ],
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="boom",
            channel_types=None,
            description="bag",
            is_required=False,
            choices=[
                hikari.CommandChoice(name="Foo", value=123.321),
                hikari.CommandChoice(name="Bar", value=543.123),
                hikari.CommandChoice(name="Blam", value=432.123),
                hikari.CommandChoice(name="Ok", value=43.34),
            ],
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["nom"]
    assert tracked_option.converters == [Choices1]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nom"
    assert tracked_option.name == "nom"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["boom"]
    assert tracked_option.converters == [Choices1]
    assert tracked_option.default is Choices1.Blam
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "boom"
    assert tracked_option.name == "boom"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "nom"
    assert argument.converters == [Choices1]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "boom"
    assert option.names == ["--boom"]
    assert option.converters == [Choices1]
    assert option.default is Choices1.Blam
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_int_choices():
    global Choices2

    class Choices2(int, enum.Enum):
        Fooman = 321
        Batman = 123
        Bazman = 0

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        nat: typing.Annotated[annotations.Choices[Choices2], "meow"],
        bag: typing.Annotated[annotations.Choices[Choices2], "bagette"] = Choices2.Bazman,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="nat",
            channel_types=None,
            description="meow",
            is_required=True,
            choices=[
                hikari.CommandChoice(name="Fooman", value=321),
                hikari.CommandChoice(name="Batman", value=123),
                hikari.CommandChoice(name="Bazman", value=0),
            ],
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="bag",
            channel_types=None,
            description="bagette",
            is_required=False,
            choices=[
                hikari.CommandChoice(name="Fooman", value=321),
                hikari.CommandChoice(name="Batman", value=123),
                hikari.CommandChoice(name="Bazman", value=0),
            ],
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["nat"]
    assert tracked_option.converters == [Choices2]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nat"
    assert tracked_option.name == "nat"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["bag"]
    assert tracked_option.converters == [Choices2]
    assert tracked_option.default is Choices2.Bazman
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bag"
    assert tracked_option.name == "bag"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "nat"
    assert argument.converters == [Choices2]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "bag"
    assert option.names == ["--bag"]
    assert option.converters == [Choices2]
    assert option.default is Choices2.Bazman
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_str_choices():
    global Choices3

    class Choices3(str, enum.Enum):
        Meow = "ok"
        Bro = "no"
        Sis = "pls"
        Catgirl = "uwu"

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        ny: typing.Annotated[annotations.Choices[Choices3], "fat"],
        aa: typing.Annotated[annotations.Choices[Choices3], "bat"] = Choices3.Sis,
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="ny",
            channel_types=None,
            description="fat",
            is_required=True,
            choices=[
                hikari.CommandChoice(name="Meow", value="ok"),
                hikari.CommandChoice(name="Bro", value="no"),
                hikari.CommandChoice(name="Sis", value="pls"),
                hikari.CommandChoice(name="Catgirl", value="uwu"),
            ],
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="aa",
            channel_types=None,
            description="bat",
            is_required=False,
            choices=[
                hikari.CommandChoice(name="Meow", value="ok"),
                hikari.CommandChoice(name="Bro", value="no"),
                hikari.CommandChoice(name="Sis", value="pls"),
                hikari.CommandChoice(name="Catgirl", value="uwu"),
            ],
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["ny"]
    assert tracked_option.converters == [Choices3]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "ny"
    assert tracked_option.name == "ny"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["aa"]
    assert tracked_option.converters == [Choices3]
    assert tracked_option.default is Choices3.Sis
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "aa"
    assert tracked_option.name == "aa"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "ny"
    assert argument.converters == [Choices3]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "aa"
    assert option.names == ["--aa"]
    assert option.converters == [Choices3]
    assert option.default is Choices3.Sis
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_choices_when_enum_has_no_other_base():
    class Choices(enum.Enum):
        ...

    with pytest.raises(ValueError, match="Enum must be a subclsas of str, float or int"):
        annotations.Choices[Choices]


def test_with_generic_choices_when_enum_isnt_int_str_or_float():
    class Choices(bytes, enum.Enum):
        ...

    with pytest.raises(ValueError, match="Enum must be a subclsas of str, float or int"):
        annotations.Choices[Choices]


def test_with_converted():
    global mock_callback_1
    global mock_callback_2
    global mock_callback_3
    mock_callback_1 = mock.Mock()
    mock_callback_2 = mock.Mock()
    mock_callback_3 = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("nyaa", "meow")
    @tanjun.as_message_command("nyaa")
    async def command(
        ctx: tanjun.abc.Context,
        boo: typing.Annotated[annotations.Str, annotations.Converted(mock_callback_1, mock_callback_2), "description"],
        bam: typing.Annotated[typing.Optional[annotations.Int], annotations.Converted(mock_callback_3), "nom"] = None,
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="boo",
            channel_types=None,
            description="description",
            is_required=True,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="bam",
            channel_types=None,
            description="nom",
            is_required=False,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["boo"]
    assert tracked_option.converters == [mock_callback_1, mock_callback_2]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "boo"
    assert tracked_option.name == "boo"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["bam"]
    assert tracked_option.converters == [mock_callback_3]
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bam"
    assert tracked_option.name == "bam"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "boo"
    assert argument.converters == [mock_callback_1, mock_callback_2]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "bam"
    assert option.names == ["--bam"]
    assert option.converters == [mock_callback_3]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_converted():
    global mock_callback_1
    global mock_callback_2
    global mock_callback_3
    mock_callback_1 = mock.Mock()
    mock_callback_2 = mock.Mock()
    mock_callback_3 = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("nyaa", "meow")
    @tanjun.as_message_command("nyaa")
    async def command(
        ctx: tanjun.abc.Context,
        boo: typing.Annotated[annotations.Converted[mock_callback_1, mock_callback_2], "description"],  # type: ignore
        bam: typing.Annotated[annotations.Converted[mock_callback_3], "nom"] = None,
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="boo",
            channel_types=None,
            description="description",
            is_required=True,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="bam",
            channel_types=None,
            description="nom",
            is_required=False,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["boo"]
    assert tracked_option.converters == [mock_callback_1, mock_callback_2]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "boo"
    assert tracked_option.name == "boo"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["bam"]
    assert tracked_option.converters == [mock_callback_3]
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bam"
    assert tracked_option.name == "bam"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "boo"
    assert argument.converters == [mock_callback_1, mock_callback_2]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "bam"
    assert option.names == ["--bam"]
    assert option.converters == [mock_callback_3]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, argument: typing.Annotated[annotations.Str, annotations.Default("nyaa"), "meow"]
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="argument",
            channel_types=None,
            description="meow",
            is_required=False,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["argument"]
    assert tracked_option.converters == []
    assert tracked_option.default == "nyaa"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "argument"
    assert tracked_option.name == "argument"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)
    assert len(command.wrapped_command.parser.arguments) == 0
    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "argument"
    assert option.names == ["--argument"]
    assert option.converters == []
    assert option.default == "nyaa"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        argument: typing.Annotated[annotations.Default[annotations.Str, "nyaa"], "meow"],  # noqa: F821
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="argument",
            channel_types=None,
            description="meow",
            is_required=False,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["argument"]
    assert tracked_option.converters == []
    assert tracked_option.default == "nyaa"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "argument"
    assert tracked_option.name == "argument"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)
    assert len(command.wrapped_command.parser.arguments) == 0
    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "argument"
    assert option.names == ["--argument"]
    assert option.converters == []
    assert option.default == "nyaa"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_default_overriding_signature_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        argument: typing.Annotated[annotations.Default[annotations.Str, "yeet"], "meow"] = "m",  # noqa: F821
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="argument",
            channel_types=None,
            description="meow",
            is_required=False,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["argument"]
    assert tracked_option.converters == []
    assert tracked_option.default == "yeet"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "argument"
    assert tracked_option.name == "argument"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)
    assert len(command.wrapped_command.parser.arguments) == 0
    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "argument"
    assert option.names == ["--argument"]
    assert option.converters == []
    assert option.default == "yeet"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_default_unsetting_signature_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, argument: typing.Annotated[annotations.Default[annotations.Str], "meow"] = "m"
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="argument",
            channel_types=None,
            description="meow",
            is_required=True,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["argument"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "argument"
    assert tracked_option.name == "argument"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)
    assert len(command.wrapped_command.parser.arguments) == 1
    assert len(command.wrapped_command.parser.options) == 0
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "argument"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None


def test_with_flag():
    global empty_value
    empty_value = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("meow")
    @tanjun.as_slash_command("beep", "boop")
    async def callback(
        ctx: tanjun.abc.MessageContext,
        meep: typing.Annotated[annotations.Str, annotations.Flag(), "bb"] = "",
        eep: typing.Annotated[
            annotations.Int, annotations.Flag(aliases=("--hi", "--bye"), empty_value=empty_value), "b"
        ] = 545454,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)
    assert len(callback.parser.arguments) == 0
    assert len(callback.parser.options) == 2
    option = callback.parser.options[0]
    assert option.key == "meep"
    assert option.names == ["--meep"]
    assert option.converters == []
    assert option.default == ""
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None
    option = callback.parser.options[1]
    assert option.key == "eep"
    assert option.names == ["--eep", "--hi", "--bye"]
    assert option.converters == [int]
    assert option.default == 545454
    assert option.empty_value is empty_value
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="meep",
            channel_types=None,
            description="bb",
            is_required=False,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="eep",
            channel_types=None,
            description="b",
            is_required=False,
        ),
    ]
    assert len(callback.wrapped_command._tracked_options) == 2
    option = callback.wrapped_command._tracked_options["meep"]
    assert option.default == ""
    option = callback.wrapped_command._tracked_options["eep"]
    assert option.default == 545454


def test_with_flag_and_deprecated_default():
    with pytest.warns(
        DeprecationWarning, match=re.escape("Flag.__init__'s `default` argument is deprecated, use Default instead")
    ):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("meow")
        @tanjun.as_slash_command("beep", "boop")
        async def callback(
            ctx: tanjun.abc.MessageContext,
            eep: typing.Annotated[annotations.Int, annotations.Flag(default=1231), "b"] = 545454,
        ) -> None:
            ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)
    assert len(callback.parser.arguments) == 0
    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "eep"
    assert option.default == 1231

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="eep",
            channel_types=None,
            description="b",
            is_required=False,
        )
    ]
    assert len(callback.wrapped_command._tracked_options) == 1
    option = callback.wrapped_command._tracked_options["eep"]
    assert option.default == 1231


def test_with_flag_and_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("meow")
    @tanjun.as_slash_command("ea", "meow")
    async def callback(
        ctx: tanjun.abc.Context,
        eep: typing.Annotated[annotations.Int, annotations.Flag(aliases=("--hi", "--bye")), "a"] = 123,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)
    assert len(callback.parser.arguments) == 0
    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "eep"
    assert option.names == ["--eep", "--hi", "--bye"]
    assert option.converters == [int]
    assert option.default == 123
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="eep",
            channel_types=None,
            description="a",
            is_required=False,
        )
    ]
    assert len(callback.wrapped_command._tracked_options) == 1
    option = callback.wrapped_command._tracked_options["eep"]
    assert option.default == 123


def test_with_flag_missing_default():
    @tanjun.as_message_command("meow")
    async def callback(
        ctx: tanjun.abc.MessageContext,
        noooo: typing.Annotated[annotations.Int, annotations.Flag()],
        eep: typing.Annotated[annotations.Int, annotations.Flag(aliases=("--hi",))] = 123,
    ) -> None:
        ...

    with pytest.raises(ValueError, match="Flag argument 'noooo' must have a default"):
        annotations.with_annotated_args(callback)


def test_with_positional():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("name")
    @tanjun.as_slash_command("boop", "description")
    async def callback(
        ctx: tanjun.abc.Context, beep: typing.Annotated[annotations.Str, annotations.Positional(), "eat"]
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)
    assert len(callback.parser.arguments) == 1
    assert len(callback.parser.options) == 0
    option = callback.parser.arguments[0]
    assert option.key == "beep"
    assert option.converters == []
    assert option.default is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="beep",
            channel_types=None,
            description="eat",
            is_required=True,
        )
    ]
    assert len(callback.wrapped_command._tracked_options) == 1
    option = callback.wrapped_command._tracked_options["beep"]
    assert option.default is tanjun.commands.slash.UNDEFINED_DEFAULT


def test_with_greedy():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        meep: typing.Annotated[annotations.Int, annotations.Greedy()],
    ):
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "meep"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None


def test_with_generic_greedy():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        meep: annotations.Greedy[annotations.Str],
    ):
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "meep"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None


def test_with_length():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Str, annotations.Length(123), "nom"],
        other_value: typing.Annotated[typing.Optional[annotations.Str], annotations.Length(5544), "meow"] = None,
    ) -> None:
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="value",
            channel_types=None,
            description="nom",
            is_required=True,
            min_length=0,
            max_length=123,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="other_value",
            channel_types=None,
            description="meow",
            is_required=False,
            min_length=0,
            max_length=5544,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length == 0
    assert argument.max_length == 123
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == []
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_length == 0
    assert option.max_length == 5544
    assert option.min_value is None
    assert option.max_value is None


def test_with_length_when_min_specificed():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Str, annotations.Length(43, 5444), "nom"],
        other_value: typing.Annotated[typing.Optional[annotations.Str], annotations.Length(32, 4343), "meow"] = None,
    ) -> None:
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="value",
            channel_types=None,
            description="nom",
            is_required=True,
            min_length=43,
            max_length=5444,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="other_value",
            channel_types=None,
            description="meow",
            is_required=False,
            min_length=32,
            max_length=4343,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length == 43
    assert argument.max_length == 5444
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == []
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_length == 32
    assert option.max_length == 4343
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_length():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Length[123], "nom"],
        other_value: typing.Annotated[typing.Optional[annotations.Length[5544]], "meow"] = None,
    ) -> None:
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="value",
            channel_types=None,
            description="nom",
            is_required=True,
            min_length=0,
            max_length=123,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="other_value",
            channel_types=None,
            description="meow",
            is_required=False,
            min_length=0,
            max_length=5544,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length == 0
    assert argument.max_length == 123
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == []
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_length == 0
    assert option.max_length == 5544
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_length_when_min_specificed():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Length[43, 5444], "nom"],
        other_value: typing.Annotated[typing.Optional[annotations.Length[32, 4343]], "meow"] = None,
    ) -> None:
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="value",
            channel_types=None,
            description="nom",
            is_required=True,
            min_length=43,
            max_length=5444,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="other_value",
            channel_types=None,
            description="meow",
            is_required=False,
            min_length=32,
            max_length=4343,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length == 43
    assert argument.max_length == 5444
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == []
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_length == 32
    assert option.max_length == 4343
    assert option.min_value is None
    assert option.max_value is None


@pytest.mark.parametrize(
    ("type_", "value", "raw_type", "option_type"),
    [
        (annotations.Int, 543, int, hikari.OptionType.INTEGER),
        (annotations.Float, 234.432, float, hikari.OptionType.FLOAT),
    ],
)
def test_with_max(
    type_: type[typing.Union[int, float]],
    value: typing.Union[int, float],
    raw_type: type[typing.Any],
    option_type: hikari.OptionType,
):
    global type__
    global value_
    type__ = type_
    value_ = value

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        bee: typing.Annotated[type__, annotations.Max(value_), "eee"],  # type: ignore
        yeet_no: typing.Annotated[typing.Union[type__, None], annotations.Max(value_), "eep"] = None,  # type: ignore
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type,
            name="bee",
            channel_types=None,
            description="eee",
            is_required=True,
            min_value=None,
            max_value=value,
        ),
        hikari.CommandOption(
            type=option_type,
            name="yeet_no",
            channel_types=None,
            description="eep",
            is_required=False,
            min_value=None,
            max_value=value,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["bee"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is (raw_type is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bee"
    assert tracked_option.name == "bee"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["yeet_no"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is (raw_type is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "yeet_no"
    assert tracked_option.name == "yeet_no"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "bee"
    assert argument.converters == [raw_type]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value == value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "yeet_no"
    assert option.names == ["--yeet-no"]
    assert option.converters == [raw_type]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value == value


@pytest.mark.parametrize(
    ("value", "converter", "option_type"),
    [(543, int, hikari.OptionType.INTEGER), (234.432, float, hikari.OptionType.FLOAT)],
)
def test_with_generic_max(
    value: typing.Union[int, float], converter: typing.Union[type[int], type[float]], option_type: hikari.OptionType
):
    global value_
    value_ = value

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[annotations.Max[value_], "eee"],
        other_number: typing.Annotated[annotations.Max[value_], "eep"] = 54234,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type,
            name="number",
            channel_types=None,
            description="eee",
            is_required=True,
            min_value=None,
            max_value=value,
        ),
        hikari.CommandOption(
            type=option_type,
            name="other_number",
            channel_types=None,
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
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 54234
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value == value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default == 54234
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value == value


def test_with_max_when_float_for_int():
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context, value: typing.Annotated[annotations.Int, annotations.Max(123.312), "description"]
    ) -> None:
        ...

    with pytest.raises(ValueError, match="Max value of type float is not valid for a int argument"):
        annotations.with_annotated_args(follow_wrapped=True)(callback)


def test_with_max_when_int_for_float():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Float, annotations.Max(432), "description"],
        other_value: typing.Annotated[typing.Union[annotations.Float, bool], annotations.Max(5431), "meow"] = False,
    ) -> None:
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="value",
            channel_types=None,
            description="description",
            is_required=True,
            min_value=None,
            max_value=432,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="other_value",
            channel_types=None,
            description="meow",
            is_required=False,
            min_value=None,
            max_value=5431,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is False
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [float]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value == 432

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default is False
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value == 5431


@pytest.mark.parametrize(
    ("type_", "raw_type", "option_type", "value"),
    [
        (annotations.Int, int, hikari.OptionType.INTEGER, 123),
        (annotations.Float, float, hikari.OptionType.FLOAT, 321.123),
    ],
)
def test_with_min(
    type_: type[typing.Union[int, float]],
    raw_type: type[typing.Union[int, float]],
    option_type: hikari.OptionType,
    value: typing.Union[int, float],
):
    global type__
    global value_
    type__ = type_
    value_ = value

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[type__, annotations.Max(value_), "eee"],  # type: ignore
        other_number: typing.Annotated[type__, annotations.Max(value_), "eep"] = 54234,  # type: ignore
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type,
            name="number",
            channel_types=None,
            description="eee",
            is_required=True,
            min_value=None,
            max_value=value,
        ),
        hikari.CommandOption(
            type=option_type,
            name="other_number",
            channel_types=None,
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
    assert tracked_option.is_always_float is (raw_type is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 54234
    assert tracked_option.is_always_float is (raw_type is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [raw_type]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value == value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [raw_type]
    assert option.default == 54234
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value == value


@pytest.mark.parametrize(
    ("value", "converter", "option_type"),
    [(123, int, hikari.OptionType.INTEGER), (123.321, float, hikari.OptionType.FLOAT)],
)
def test_with_generic_min(
    value: typing.Union[int, float], converter: typing.Union[type[int], type[float]], option_type: hikari.OptionType
):
    global value_
    value_ = value

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[annotations.Min[value_], "bee"],
        other_number: typing.Annotated[annotations.Min[value_], "buzz"] = 321,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type,
            name="number",
            channel_types=None,
            description="bee",
            is_required=True,
            min_value=value,
            max_value=None,
        ),
        hikari.CommandOption(
            type=option_type,
            name="other_number",
            channel_types=None,
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
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 321
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value == value
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default == 321
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == value
    assert option.max_value is None


def test_with_min_when_float_for_int():
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context, value: typing.Annotated[annotations.Int, annotations.Min(234.432), "description"]
    ) -> None:
        ...

    with pytest.raises(ValueError, match="Min value of type float is not valid for a int argument"):
        annotations.with_annotated_args(follow_wrapped=True)(callback)


def test_with_min_when_int_for_float():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Float, annotations.Min(12333), "description"],
        other_value: typing.Annotated[typing.Union[annotations.Float, bool], annotations.Min(44444), "meow"] = False,
    ) -> None:
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="value",
            channel_types=None,
            description="description",
            is_required=True,
            min_value=12333,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="other_value",
            channel_types=None,
            description="meow",
            is_required=False,
            min_value=44444,
            max_value=None,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is False
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [float]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value == 12333
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default is False
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 44444
    assert option.max_value is None


def test_with_overridden_name():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        nyaa: typing.Annotated[annotations.Int, annotations.Name("boop"), "Nope"],
        meow: typing.Annotated[annotations.Str, annotations.Name("meep_meep"), "Description"] = "meowow",
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="boop",
            channel_types=None,
            description="Nope",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="meep_meep",
            channel_types=None,
            description="Description",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["boop"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nyaa"
    assert tracked_option.name == "boop"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["meep_meep"]
    assert tracked_option.converters == []
    assert tracked_option.default == "meowow"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow"
    assert tracked_option.name == "meep_meep"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "nyaa"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--meep-meep"]
    assert option.converters == []
    assert option.default == "meowow"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_individually_overridden_name():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        nyaa: typing.Annotated[annotations.Int, annotations.Name("nom", slash="oop"), "Nope"],
        meow: typing.Annotated[
            annotations.Str, annotations.Name("nom2", slash="n", message="--boop-oop"), "Description"
        ] = "meowow",
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="oop",
            channel_types=None,
            description="Nope",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="n",
            channel_types=None,
            description="Description",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["oop"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nyaa"
    assert tracked_option.name == "oop"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["n"]
    assert tracked_option.converters == []
    assert tracked_option.default == "meowow"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow"
    assert tracked_option.name == "n"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "nyaa"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--boop-oop"]
    assert option.converters == []
    assert option.default == "meowow"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_overridden_slash_name():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        necc: typing.Annotated[annotations.Int, annotations.Name(slash="nom"), "EEEE"],
        nya: typing.Annotated[annotations.Str, annotations.Name(slash="sex"), "AAAA"] = "meow",
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="nom",
            channel_types=None,
            description="EEEE",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="sex",
            channel_types=None,
            description="AAAA",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["nom"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "necc"
    assert tracked_option.name == "nom"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["sex"]
    assert tracked_option.converters == []
    assert tracked_option.default == "meow"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nya"
    assert tracked_option.name == "sex"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "necc"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "nya"
    assert option.names == ["--nya"]
    assert option.converters == []
    assert option.default == "meow"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_overridden_message_name():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        meow_meow: typing.Annotated[annotations.Str, annotations.Name(message="--blam-blam"), "Description"] = "neko",
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="meow_meow",
            channel_types=None,
            description="Description",
            is_required=False,
            min_value=None,
            max_value=None,
        )
    ]

    assert len(callback._tracked_options) == 1
    tracked_option = callback._tracked_options["meow_meow"]
    assert tracked_option.converters == []
    assert tracked_option.default == "neko"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow_meow"
    assert tracked_option.name == "meow_meow"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 0
    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow_meow"
    assert option.names == ["--blam-blam"]
    assert option.converters == []
    assert option.default == "neko"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_ranged():
    @annotations.with_annotated_args(follow_wrapped=True)
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
            channel_types=None,
            description="meow",
            is_required=True,
            min_value=44,
            max_value=55,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="other_value",
            channel_types=None,
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
    assert argument.min_value == 44
    assert argument.max_value == 55

    assert len(callback.wrapped_command.parser.options) == 1

    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default == 5
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 5433
    assert option.max_value == 6524.32


@pytest.mark.parametrize(
    ("min_value", "max_value", "converter", "option_type"),
    [
        (123.132, 321, float, hikari.OptionType.FLOAT),
        (123, 321, int, hikari.OptionType.INTEGER),
        (431, 1232.321, float, hikari.OptionType.FLOAT),
        (452.432, 55234.2134, float, hikari.OptionType.FLOAT),
    ],
)
def test_with_generic_ranged(
    min_value: typing.Union[float, int],
    max_value: typing.Union[float, int],
    converter: typing.Union[type[float], type[int]],
    option_type: hikari.OptionType,
):
    global min_value_
    global max_value_
    min_value_ = min_value
    max_value_ = max_value

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[annotations.Ranged[min_value_, max_value_], "meow"],
        other_number: typing.Annotated[annotations.Ranged[min_value_, max_value_], "nom"] = 443,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type,
            name="number",
            channel_types=None,
            description="meow",
            is_required=True,
            min_value=min_value,
            max_value=max_value,
        ),
        hikari.CommandOption(
            type=option_type,
            name="other_number",
            channel_types=None,
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
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default == 443
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value == min_value
    assert argument.max_value == max_value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default == 443
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == min_value
    assert option.max_value == max_value


def test_with_snowflake_or():
    global mock_callback
    mock_callback = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.Role, annotations.SnowflakeOr(parse_id=mock_callback), "se"],
        value_2: typing.Annotated[typing.Optional[annotations.User], annotations.SnowflakeOr(), "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.ROLE,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.USER

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [mock_callback]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_snowflake]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_channel():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.SnowflakeOr[annotations.Channel], "se"],
        value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Channel]], "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_channel_id]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_channel_id]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_member():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.SnowflakeOr[annotations.Member], "se"],
        value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Member]], "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.USER

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_user_id]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_mentionable():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.SnowflakeOr[annotations.Mentionable], "se"],
        value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Mentionable]], "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.MENTIONABLE,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.MENTIONABLE,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_snowflake]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_snowflake]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_role():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.SnowflakeOr[annotations.Role], "se"],
        value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Role]], "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.ROLE,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.ROLE,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.ROLE

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_role_id]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_role_id]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_user():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.SnowflakeOr[annotations.User], "se"],
        value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.User]], "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.USER

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_user_id]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("yeet", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        value: typing.Annotated[annotations.SnowflakeOr[annotations.Bool], "se"],
        value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Bool]], "x"] = None,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.BOOLEAN,
            name="value",
            channel_types=None,
            description="se",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.BOOLEAN,
            name="value_2",
            channel_types=None,
            description="x",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(callback.wrapped_command._tracked_options) == 2
    tracked_option = callback.wrapped_command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.to_bool]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.to_bool]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None


@pytest.mark.parametrize(
    ("channel_types", "expected_types"),
    [
        (
            (hikari.TextableGuildChannel, hikari.ChannelType.GUILD_STAGE),
            {
                hikari.ChannelType.GUILD_TEXT,
                hikari.ChannelType.GUILD_NEWS,
                hikari.ChannelType.GUILD_VOICE,
                hikari.ChannelType.GUILD_STAGE,
            },
        ),
        (
            types := (hikari.ChannelType.GUILD_TEXT, hikari.ChannelType.GUILD_VOICE, hikari.ChannelType.GROUP_DM),
            set(types),
        ),
        (
            (hikari.GuildVoiceChannel, hikari.DMChannel, hikari.GuildTextChannel),
            {hikari.ChannelType.GUILD_VOICE, hikari.ChannelType.DM, hikari.ChannelType.GUILD_TEXT},
        ),
    ],
)
def test_with_these_channels(
    channel_types: collections.Sequence[typing.Union[hikari.ChannelType, type[hikari.PartialChannel]]],
    expected_types: set[hikari.ChannelType],
):
    global channel_types_
    channel_types_ = channel_types

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        foo: typing.Annotated[annotations.Channel, annotations.TheseChannels(*channel_types_), "meow"],
        bar: typing.Annotated[
            typing.Optional[annotations.Channel], annotations.TheseChannels(*channel_types_), "boom"
        ] = None,
    ):
        ...

    assert len(command.build().options) == 2
    option = command.build().options[0]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "foo"
    assert option.description == "meow"
    assert option.is_required is True
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == len(expected_types)
    assert set(option.channel_types) == expected_types

    option = command.build().options[1]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "bar"
    assert option.description == "boom"
    assert option.is_required is False
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == len(expected_types)
    assert set(option.channel_types) == expected_types

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["foo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "foo"
    assert tracked_option.name == "foo"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["bar"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bar"
    assert tracked_option.name == "bar"
    assert tracked_option.type is hikari.OptionType.CHANNEL


def test_with_generic_these_channels():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        bb: typing.Annotated[annotations.TheseChannels[hikari.GuildChannel], "nep"],
        bat: typing.Annotated[
            typing.Optional[annotations.TheseChannels[hikari.GuildVoiceChannel, hikari.PrivateChannel]], "bip"
        ] = None,
    ):
        ...

    assert len(command.build().options) == 2
    option = command.build().options[0]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "bb"
    assert option.description == "nep"
    assert option.is_required is True
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == 5
    assert set(option.channel_types) == {
        hikari.ChannelType.GUILD_CATEGORY,
        hikari.ChannelType.GUILD_NEWS,
        hikari.ChannelType.GUILD_STAGE,
        hikari.ChannelType.GUILD_TEXT,
        hikari.ChannelType.GUILD_VOICE,
    }

    option = command.build().options[1]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "bat"
    assert option.description == "bip"
    assert option.is_required is False
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == 3
    assert set(option.channel_types) == {
        hikari.ChannelType.DM,
        hikari.ChannelType.GROUP_DM,
        hikari.ChannelType.GUILD_VOICE,
    }

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["bb"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bb"
    assert tracked_option.name == "bb"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["bat"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bat"
    assert tracked_option.name == "bat"
    assert tracked_option.type is hikari.OptionType.CHANNEL


def test_for_attachment_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Attachment, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Attachment, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.ATTACHMENT,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.ATTACHMENT,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert command.parser is None

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT


def test_for_bool_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Bool, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Bool, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.to_bool]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.conversion.to_bool]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.BOOLEAN,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.BOOLEAN,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.BOOLEAN


def test_for_channel_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Channel, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Channel, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.to_channel]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.conversion.to_channel]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.CHANNEL


def test_for_float_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Float, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Float, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [float]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [float]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.FLOAT


def test_for_int_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Int, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Int, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [int]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [int]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.INTEGER


def test_for_member_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Member, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Member, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.to_member]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.conversion.to_member]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.USER


def test_for_mentionable_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Mentionable, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Mentionable, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.to_user, tanjun.conversion.to_role]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.conversion.to_user, tanjun.conversion.to_role]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.MENTIONABLE,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.MENTIONABLE,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE


def test_for_role_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Role, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Role, str], "feet"] = "ok",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.to_role]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.conversion.to_role]
    assert option.default == "ok"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.ROLE,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.ROLE,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "ok"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.ROLE


def test_for_str_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Str, "yeet"],
        arg_2: typing.Annotated[typing.Union[bool, annotations.Str], "feet"] = False,
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == []
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == []
    assert option.default is False
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is False
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.STRING


def test_for_user_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.User, "yeet"],
        arg_2: typing.Annotated[typing.Union[str, annotations.User], "feet"] = "bye",
    ) -> None:
        ...

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.to_user]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.conversion.to_user]
    assert option.default == "bye"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value is None
    assert option.max_value is None

    assert command.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="arg",
            channel_types=None,
            description="yeet",
            is_required=True,
            min_value=None,
            max_value=None,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.USER,
            name="arg_2",
            channel_types=None,
            description="feet",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command.wrapped_command._tracked_options) == 2
    tracked_option = command.wrapped_command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default == "bye"
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.USER


def test_when_annotated_not_top_level():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        *,
        value: typing.Union[typing.Annotated[annotations.Positional[annotations.Str], "nyaa"], bool] = False,
        other_value: typing.Optional[typing.Annotated[annotations.Ranged[123, 432], "meow"]] = None,
    ) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="value",
            description="nyaa",
            is_required=False,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            description="meow",
            is_required=False,
            min_value=123,
            max_value=432,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is False
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == []
    assert argument.default is False
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 123
    assert option.max_value == 432


if sys.version_info >= (3, 10):

    def test_when_annotated_not_top_level_3_10_union():
        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def command(
            ctx: tanjun.abc.Context,
            *,
            value: typing.Annotated[annotations.Positional[annotations.Str], "nyaa"] | bool = False,
            other_value: typing.Annotated[annotations.Ranged[123, 432], "meow"] | None = None,
        ) -> None:
            raise NotImplementedError

        assert command.build().options == [
            hikari.CommandOption(
                type=hikari.OptionType.STRING,
                name="value",
                description="nyaa",
                is_required=False,
            ),
            hikari.CommandOption(
                type=hikari.OptionType.INTEGER,
                name="other_value",
                description="meow",
                is_required=False,
                min_value=123,
                max_value=432,
            ),
        ]

        assert len(command._tracked_options) == 2
        tracked_option = command._tracked_options["value"]
        assert tracked_option.converters == []
        assert tracked_option.default is False
        assert tracked_option.is_always_float is False
        assert tracked_option.is_only_member is False
        assert tracked_option.key == "value"
        assert tracked_option.name == "value"
        assert tracked_option.type is hikari.OptionType.STRING

        tracked_option = command._tracked_options["other_value"]
        assert tracked_option.converters == []
        assert tracked_option.default is None
        assert tracked_option.is_always_float is False
        assert tracked_option.is_only_member is False
        assert tracked_option.key == "other_value"
        assert tracked_option.name == "other_value"
        assert tracked_option.type is hikari.OptionType.INTEGER

        assert isinstance(command.wrapped_command, tanjun.MessageCommand)
        assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

        assert len(command.wrapped_command.parser.arguments) == 1
        argument = command.wrapped_command.parser.arguments[0]
        assert argument.key == "value"
        assert argument.converters == []
        assert argument.default is False
        assert argument.is_greedy is False
        assert argument.is_multi is False
        assert argument.min_value is None
        assert argument.max_value is None

        assert len(command.wrapped_command.parser.options) == 1
        option = command.wrapped_command.parser.options[0]
        assert option.key == "other_value"
        assert option.names == ["--other-value"]
        assert option.converters == [int]
        assert option.default is None
        assert option.empty_value is tanjun.parsing.UNDEFINED
        assert option.is_multi is False
        assert option.min_value == 123
        assert option.max_value == 432


def test_when_annotated_handles_unions():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        *,
        value: typing.Annotated[typing.Union[annotations.Positional[annotations.Str], bool], "nyaa"] = False,
        other_value: typing.Annotated[typing.Optional[annotations.Ranged[123, 432]], "meow"] = None,
    ) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="value",
            description="nyaa",
            is_required=False,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            description="meow",
            is_required=False,
            min_value=123,
            max_value=432,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is False
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == []
    assert argument.default is False
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is None
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.min_value == 123
    assert option.max_value == 432


if sys.version_info >= (3, 10):

    def test_when_annotated_handles_3_10_unions():
        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def command(
            ctx: tanjun.abc.Context,
            *,
            value: typing.Annotated[annotations.Positional[annotations.Str] | bool, "nyaa"] = False,
            other_value: typing.Annotated[annotations.Ranged[123, 432] | None, "meow"] = None,
        ) -> None:
            raise NotImplementedError

        assert command.build().options == [
            hikari.CommandOption(
                type=hikari.OptionType.STRING,
                name="value",
                description="nyaa",
                is_required=False,
            ),
            hikari.CommandOption(
                type=hikari.OptionType.INTEGER,
                name="other_value",
                description="meow",
                is_required=False,
                min_value=123,
                max_value=432,
            ),
        ]

        assert len(command._tracked_options) == 2
        tracked_option = command._tracked_options["value"]
        assert tracked_option.converters == []
        assert tracked_option.default is False
        assert tracked_option.is_always_float is False
        assert tracked_option.is_only_member is False
        assert tracked_option.key == "value"
        assert tracked_option.name == "value"
        assert tracked_option.type is hikari.OptionType.STRING

        tracked_option = command._tracked_options["other_value"]
        assert tracked_option.converters == []
        assert tracked_option.default is None
        assert tracked_option.is_always_float is False
        assert tracked_option.is_only_member is False
        assert tracked_option.key == "other_value"
        assert tracked_option.name == "other_value"
        assert tracked_option.type is hikari.OptionType.INTEGER

        assert isinstance(command.wrapped_command, tanjun.MessageCommand)
        assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

        assert len(command.wrapped_command.parser.arguments) == 1
        argument = command.wrapped_command.parser.arguments[0]
        assert argument.key == "value"
        assert argument.converters == []
        assert argument.default is False
        assert argument.is_greedy is False
        assert argument.is_multi is False
        assert argument.min_value is None
        assert argument.max_value is None

        assert len(command.wrapped_command.parser.options) == 1
        option = command.wrapped_command.parser.options[0]
        assert option.key == "other_value"
        assert option.names == ["--other-value"]
        assert option.converters == [int]
        assert option.default is None
        assert option.empty_value is tanjun.parsing.UNDEFINED
        assert option.is_multi is False
        assert option.min_value == 123
        assert option.max_value == 432
