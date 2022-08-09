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

import enum
import typing
from collections import abc as collections
from unittest import mock

import alluka
import hikari
import pytest

import tanjun
from tanjun import annotations


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
    @annotations.with_annotated_args
    @tanjun.as_slash_command("meow", "nyaa")
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context, injected: alluka.Injected[int], other_injected: str = alluka.inject(type=str)
    ) -> None:
        ...

    assert command.build().options == []
    assert command._tracked_options == {}
    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_with_no_annotations_but_message_parser_already_set():
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context, injected: alluka.Injected[int], other_injected: str = alluka.inject(type=str)
    ) -> None:
        ...

    command.set_parser(tanjun.ShlexParser())

    annotations.with_annotated_args(command)

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


def test_with_with_std_range():
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
    assert argument.max_value == 344
    assert argument.min_value == 123

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value == 5567
    assert option.min_value == 22


def test_with_std_slice():
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
    assert argument.max_value == 652
    assert argument.min_value == 324

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default == 44
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value == 554
    assert option.min_value == 444


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
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        nope: typing.Annotated[type_cls, annotations.Choices(choices), "default"],
        boo: typing.Annotated[type_cls, annotations.Choices(choices), "be"] = "hi",
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


def test_choices_and_mixed_values():
    ...


def test_with_generic_float_choices():
    class Choices(float, enum.Enum):
        Foo = 123.321
        Bar = 543.123
        Blam = 432.123
        Ok = 43.34

    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        nom: typing.Annotated[annotations.Choices[Choices], "description"],
        boom: typing.Annotated[annotations.Choices[Choices], "bag"] = Choices.Blam,
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
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nom"
    assert tracked_option.name == "nom"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["boom"]
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is Choices.Blam
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
    assert argument.converters == [Choices]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value is None
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "boom"
    assert option.names == ["--boom"]
    assert option.converters == [Choices]
    assert option.default is Choices.Blam
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_generic_int_choices():
    class Choices(int, enum.Enum):
        Fooman = 321
        Batman = 123
        Bazman = 0

    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        nat: typing.Annotated[annotations.Choices[Choices], "meow"],
        bag: typing.Annotated[annotations.Choices[Choices], "bagette"] = Choices.Bazman,
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
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nat"
    assert tracked_option.name == "nat"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["bag"]
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is Choices.Bazman
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
    assert argument.converters == [Choices]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value is None
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "bag"
    assert option.names == ["--bag"]
    assert option.converters == [Choices]
    assert option.default is Choices.Bazman
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_generic_str_choices():
    class Choices(str, enum.Enum):
        Meow = "ok"
        Bro = "no"
        Sis = "pls"
        Catgirl = "uwu"

    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        ny: typing.Annotated[annotations.Choices[Choices], "fat"],
        aa: typing.Annotated[annotations.Choices[Choices], "bat"] = Choices.Sis,
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
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is tanjun.commands.slash.UNDEFINED_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "ny"
    assert tracked_option.name == "ny"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["aa"]
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is Choices.Sis
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
    assert argument.converters == [Choices]
    assert argument.default is tanjun.parsing.UNDEFINED
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.max_value is None
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "aa"
    assert option.names == ["--aa"]
    assert option.converters == [Choices]
    assert option.default is Choices.Sis
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_generic_choices_when_enum_isnt_int_str_or_float():
    class Choices(enum.Enum):
        ...

    with pytest.raises(ValueError, match="Enum must be a subclsas of str, float or int"):
        annotations.Choices[Choices]


def test_with_converted():
    ...


def test_with_generic_converted():
    ...


def test_with_flag():
    empty_value = mock.Mock()

    @annotations.with_annotated_args
    @tanjun.as_message_command("meow")
    async def callback(
        ctx: tanjun.abc.MessageContext,
        eep: typing.Annotated[
            annotations.Int, annotations.Flag(aliases=("--hi", "--bye"), empty_value=empty_value, default=1231)
        ] = 545454,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert len(callback.parser.arguments) == 0
    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "eep"
    assert option.names == ["--eep", "--hi", "--bye"]
    assert option.converters == [int]
    assert option.default == 1231
    assert option.empty_value is empty_value
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_flag_inferred_default():
    @annotations.with_annotated_args
    @tanjun.as_message_command("meow")
    async def callback(
        ctx: tanjun.abc.MessageContext,
        eep: typing.Annotated[annotations.Int, annotations.Flag(aliases=("--hi", "--bye"))] = 123,
    ) -> None:
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert len(callback.parser.arguments) == 0
    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "eep"
    assert option.names == ["--eep", "--hi", "--bye"]
    assert option.converters == [int]
    assert option.default == 123
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


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


def test_with_greedy():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
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
    assert argument.max_value is None
    assert argument.min_value is None


def test_with_generic_greedy():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
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
    assert argument.max_value is None
    assert argument.min_value is None


def test_with_max():
    ...


@pytest.mark.parametrize(
    ("value", "converter", "otype"), [(543, int, hikari.OptionType.INTEGER), (234.432, float, hikari.OptionType.FLOAT)]
)
def test_with_generic_max(
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
            channel_types=None,
            description="eee",
            is_required=True,
            min_value=None,
            max_value=value,
        ),
        hikari.CommandOption(
            type=otype,
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
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value == value
    assert option.min_value is None


def test_with_max_when_not_valid_for_type():
    ...


def test_with_min():
    ...


@pytest.mark.parametrize(
    ("value", "converter", "otype"), [(123, int, hikari.OptionType.INTEGER), (123.321, float, hikari.OptionType.FLOAT)]
)
def test_with_generic_min(
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
            channel_types=None,
            description="bee",
            is_required=True,
            min_value=value,
            max_value=None,
        ),
        hikari.CommandOption(
            type=otype,
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
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value == value


def test_with_min_when_not_valid_for_type():
    ...


def test_with_overridden_name():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
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
    assert argument.max_value is None
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--meep-meep"]
    assert option.converters == []
    assert option.default == "meowow"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_individually_overridden_name():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
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
    assert argument.max_value is None
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--boop-oop"]
    assert option.converters == []
    assert option.default == "meowow"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_overridden_slash_name():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
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
    assert argument.max_value is None
    assert argument.min_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "nya"
    assert option.names == ["--nya"]
    assert option.converters == []
    assert option.default == "meow"
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value is None
    assert option.min_value is None


def test_with_overridden_message_name():
    @tanjun.annotations.with_annotated_args(follow_wrapped=True)
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
    assert option.max_value is None
    assert option.min_value is None


def test_with_ranged():
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
    assert argument.max_value == 55
    assert argument.min_value == 44

    assert len(callback.wrapped_command.parser.options) == 1

    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default == 5
    assert option.empty_value is tanjun.parsing.UNDEFINED
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
def test_with_generic_ranged(
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
            channel_types=None,
            description="meow",
            is_required=True,
            min_value=min_value,
            max_value=max_value,
        ),
        hikari.CommandOption(
            type=otype,
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
    assert option.empty_value is tanjun.parsing.UNDEFINED
    assert option.is_multi is False
    assert option.max_value == max_value
    assert option.min_value == min_value


def test_with_snowflake_or():
    ...


def test_with_generic_snowflake_or_for_channel():
    ...


def test_with_generic_snowflake_or_for_member():
    ...


def test_with_generic_snowflake_or_for_mentionable():
    ...


def test_with_generic_snowflake_or_for_role():
    ...


def test_with_generic_snowflake_or_for_user():
    ...


def test_with_generic_snowflake_or():
    ...


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
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        foo: typing.Annotated[annotations.Channel, annotations.TheseChannels(*channel_types), "meow"],
        bar: typing.Annotated[
            typing.Optional[annotations.Channel], annotations.TheseChannels(*channel_types), "boom"
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
