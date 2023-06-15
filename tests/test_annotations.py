# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
import inspect
import re
import sys
import typing
from collections import abc as collections

import alluka
import hikari
import mock
import pytest
import typing_extensions

import tanjun
from tanjun import annotations


class TestChoices:
    def test_choices_property(self):
        choices = annotations.Choices({"beep": "boop", "cat": "girls", "are": "sexy"})

        assert choices.choices == {"beep": "boop", "cat": "girls", "are": "sexy"}

    def test_choices_property_for_sequence(self):
        choices = annotations.Choices([("ok", "no"), ("meow", "nyaa")])

        assert choices.choices == {"ok": "no", "meow": "nyaa"}


class TestConverted:
    def test_converters_property(self):
        converter_1 = mock.Mock()
        converter_2 = mock.Mock()
        converter_3 = mock.AsyncMock()
        converters = annotations.Converted(converter_1, converter_2, converter_3)

        assert converters.converters == [converter_1, converter_2, converter_3]


class TestDefault:
    def test_default_property(self):
        value = object()

        default = annotations.Default(value)

        assert default.default is value

    def test_default_property_with_default_value(self):
        default = annotations.Default()

        assert default.default is tanjun.abc.NO_DEFAULT


class TestFlag:
    def test_properties(self):
        flag = annotations.Flag(aliases=("yeet", "meat", "meow"), empty_value="nom")

        assert flag.aliases == ("yeet", "meat", "meow")
        assert flag.empty_value == "nom"

    def test_properties_with_default_values(self):
        flag = annotations.Flag()

        assert flag.aliases is None
        assert flag.empty_value is tanjun.abc.NO_DEFAULT

    def test_deprecated_default(self):
        value = object()

        with pytest.warns(
            DeprecationWarning, match=re.escape("Flag.__init__'s `default` argument is deprecated, use Default instead")
        ):
            flag = annotations.Flag(default=value)  # pyright: ignore[reportDeprecated]

        with pytest.warns(DeprecationWarning, match=re.escape("Use annotations.Default instead of the default arg")):
            assert flag.default is value


class TestLength:
    def test_properties(self):
        length = annotations.Length(321)

        assert length.min_length == 0
        assert length.max_length == 321

    def test_properties_when_min_specified(self):
        length = annotations.Length(554, 6545)

        assert length.min_length == 554
        assert length.max_length == 6545


class TestMax:
    def test_value_property(self):
        max_ = annotations.Max(32221)

        assert max_.value == 32221


class TestMin:
    def test_value_property(self):
        min_ = annotations.Min(3112222)

        assert min_.value == 3112222


class TestName:
    def test_properties_when_both(self):
        names = annotations.Name("meow_ok")

        assert names.message_name == "--meow-ok"
        assert names.slash_name == "meow_ok"

    def test_properties_with_defaults(self):
        names = annotations.Name()
        assert names.message_name is None
        assert names.slash_name is None

    def test_properties_when_different(self):
        names = annotations.Name(message="--__echo", slash="__-nyaa")

        assert names.message_name == "--__echo"
        assert names.slash_name == "__-nyaa"


class TestRanged:
    def test_properties(self):
        ranged = annotations.Ranged(123, 543)

        assert ranged.max_value == 543
        assert ranged.min_value == 123


class TestSnowflakeOr:
    def test_parser_id_property(self):
        mock_callback = mock.Mock()

        snowflake_or = annotations.SnowflakeOr(parse_id=mock_callback)

        assert snowflake_or.parse_id is mock_callback

    def test_parser_id_property_with_default(self):
        snowflake_or = annotations.SnowflakeOr()

        assert snowflake_or.parse_id == tanjun.conversion.parse_snowflake


class TestTheseChannels:
    def test_channel_types_property(self):
        these_channels = annotations.TheseChannels(
            hikari.DMChannel, hikari.GuildChannel, hikari.ChannelType.GUILD_STAGE
        )

        assert these_channels.channel_types == (hikari.DMChannel, hikari.GuildChannel, hikari.ChannelType.GUILD_STAGE)


def test_where_no_signature():
    with pytest.raises(ValueError, match=".+"):
        inspect.Signature.from_callable(int)

    command: tanjun.MessageCommand[typing.Any] = tanjun.as_message_command("command")(
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

    command: tanjun.MessageCommand[typing.Any] = tanjun.as_message_command("command")(
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
    async def command(ctx: tanjun.abc.Context, foo: typing.Annotated[annotations.Int, "desc"]):
        ...

    command.set_parser(mock_parser)

    with pytest.raises(TypeError, match="Expected parser to be an instance of tanjun.parsing.AbstractOptionParser"):
        annotations.parse_annotated_args(command, follow_wrapped=True)


def test_with_no_annotations():
    @annotations.with_annotated_args  # pyright: ignore[reportUnknownArgumentType]
    @tanjun.as_slash_command("meow", "nyaa")
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context,
        injected: alluka.Injected[int],
        yeet,  # type: ignore
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

    annotations.with_annotated_args(command)  # pyright: ignore[reportUnknownArgumentType]

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
        ctx: tanjun.abc.MessageContext, value: annotations.Str, other_value: annotations.Bool = False
    ) -> None:
        ...

    command: tanjun.MessageCommand[typing.Any] = tanjun.as_message_command("beep")(
        mock.Mock(tanjun.abc.SlashCommand, callback=mock_callback)
    )
    with pytest.raises(AttributeError):
        command.wrapped_command.wrapped_command  # type: ignore

    annotations.parse_annotated_args(command, follow_wrapped=True)

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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 123
    assert argument.max_value == 344

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 110
    assert argument.max_value == 542

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 324
    assert argument.max_value == 652

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 232
    assert argument.max_value == 444

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    async def callback(
        ctx: tanjun.abc.Context,
        nope: typing.Annotated[type_cls, annotations.Choices(choices), "default"],
        boo: typing.Annotated[type_cls, annotations.Choices(choices), "be"] = typing.cast("_ChoiceT", "hi"),
    ):
        ...

    assert callback.build().options == [
        hikari.CommandOption(
            type=option_type, name="nope", channel_types=None, description="default", is_required=True, choices=result
        ),
        hikari.CommandOption(
            type=option_type, name="boo", channel_types=None, description="be", is_required=False, choices=result
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["nope"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is (option_type is hikari.OptionType.FLOAT)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nope"
    assert tracked_option.name == "nope"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["boo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    @tanjun.as_slash_command("command", "description")
    async def callback(
        ctx: tanjun.abc.Context, nom: typing.Annotated[type_, annotations.Choices(choices), "description"]
    ) -> None:
        ...

    with pytest.raises(
        TypeError, match=f"Choice of type {mismatched_type.__name__} is not valid for a {type_repr.__name__} argument"
    ):
        annotations.with_annotated_args(callback)


def test_with_generic_float_choices():
    class Choices(float, enum.Enum):
        Foo = 123.321
        Bar = 543.123
        Blam = 432.123
        Ok = 43.34

    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("command", "description")
        @tanjun.as_message_command("command")
        async def callback(
            ctx: tanjun.abc.Context,
            nom: typing.Annotated[annotations.Choices[Choices], "description"],  # type: ignore
            boom: typing.Annotated[annotations.Choices[Choices], "bag"] = Choices.Blam,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nom"
    assert tracked_option.name == "nom"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["boom"]
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "boom"
    assert option.names == ["--boom"]
    assert option.converters == [Choices]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_int_choices():
    class Choices(int, enum.Enum):
        Fooman = 321
        Batman = 123
        Bazman = 0

    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("command", "description")
        @tanjun.as_message_command("command")
        async def callback(
            ctx: tanjun.abc.Context,
            nat: typing.Annotated[annotations.Choices[Choices], "meow"],  # type: ignore
            bag: typing.Annotated[annotations.Choices[Choices], "bagette"] = Choices.Bazman,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nat"
    assert tracked_option.name == "nat"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["bag"]
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "bag"
    assert option.names == ["--bag"]
    assert option.converters == [Choices]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_str_choices():
    class Choices(str, enum.Enum):
        Meow = "ok"
        Bro = "no"
        Sis = "pls"
        Catgirl = "uwu"

    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("command", "description")
        @tanjun.as_message_command("command")
        async def callback(
            ctx: tanjun.abc.Context,
            ny: typing.Annotated[annotations.Choices[Choices], "fat"],  # type: ignore
            aa: typing.Annotated[annotations.Choices[Choices], "bat"] = Choices.Sis,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "ny"
    assert tracked_option.name == "ny"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["aa"]
    assert tracked_option.converters == [Choices]
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "aa"
    assert option.names == ["--aa"]
    assert option.converters == [Choices]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_choices_when_enum_has_no_other_base():
    class Choices(enum.Enum):
        ...

    with pytest.warns(DeprecationWarning), pytest.raises(
        TypeError, match="Enum must be a subclass of str, float or int"
    ):
        annotations.Choices[Choices]


def test_with_generic_choices_when_enum_isnt_int_str_or_float():
    class Choices(bytes, enum.Enum):
        ...

    with pytest.warns(DeprecationWarning), pytest.raises(
        TypeError, match="Enum must be a subclass of str, float or int"
    ):
        annotations.Choices[Choices]


def test_with_converted():
    mock_callback_1 = mock.Mock()
    mock_callback_2 = mock.Mock()
    mock_callback_3 = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("nyaa", "meow")
    @tanjun.as_message_command("nyaa")
    async def command(
        ctx: tanjun.abc.Context,
        boo: typing.Annotated[str, annotations.Converted(mock_callback_1, mock_callback_2), "description"],
        bam: typing.Annotated[
            typing.Optional[int], annotations.Converted(mock_callback_3), "nom"  # noqa: NU002
        ] = None,
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="boo", channel_types=None, description="description", is_required=True
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="bam", channel_types=None, description="nom", is_required=False
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["boo"]
    assert tracked_option.converters == [mock_callback_1, mock_callback_2]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "boo"
    assert tracked_option.name == "boo"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["bam"]
    assert tracked_option.converters == [mock_callback_3]
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "bam"
    assert option.names == ["--bam"]
    assert option.converters == [mock_callback_3]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_converted():
    mock_callback_1 = mock.Mock()
    mock_callback_2 = mock.Mock()
    mock_callback_3 = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("nyaa", "meow")
    @tanjun.as_message_command("nyaa")
    async def command(
        ctx: tanjun.abc.Context,
        boo: typing.Annotated[typing.Any, annotations.Converted(mock_callback_1, mock_callback_2), "description"],
        bam: typing.Annotated[typing.Any, annotations.Converted(mock_callback_3), "nom"] = None,
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="boo", channel_types=None, description="description", is_required=True
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="bam", channel_types=None, description="nom", is_required=False
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["boo"]
    assert tracked_option.converters == [mock_callback_1, mock_callback_2]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "boo"
    assert tracked_option.name == "boo"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["bam"]
    assert tracked_option.converters == [mock_callback_3]
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "bam"
    assert option.names == ["--bam"]
    assert option.converters == [mock_callback_3]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_converted_type_miss_match():
    mock_callback_1 = mock.Mock()

    with pytest.raises(
        RuntimeError,
        match=(
            "Conflicting option types of <class 'hikari.messages.Attachment'> "
            "and <class 'str'> found for 'boo' parameter"
        ),
    ):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("nyaa")
        async def _(
            ctx: tanjun.abc.Context,
            boo: typing.Annotated[annotations.Attachment, annotations.Converted(mock_callback_1)],
        ) -> None:
            ...


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
            type=hikari.OptionType.STRING, name="argument", channel_types=None, description="meow", is_required=False
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
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_default():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def command(
            ctx: tanjun.abc.Context,
            argument: typing.Annotated[
                annotations.Default[annotations.Str, "nyaa"], "meow"  # noqa: F821  # type: ignore
            ],
        ) -> None:
            ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="argument", channel_types=None, description="meow", is_required=False
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
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_default_overriding_signature_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        argument: typing.Annotated[annotations.Str, annotations.Default("yeet"), "meow"] = "m",  # noqa: F821
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="argument", channel_types=None, description="meow", is_required=False
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
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_default_unsetting_signature_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, argument: typing.Annotated[annotations.Str, annotations.Default(), "meow"] = "m"
    ) -> None:
        ...

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="argument", channel_types=None, description="meow", is_required=True
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["argument"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None


def test_with_flag():
    empty_value = mock.Mock()

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("meow")
    @tanjun.as_slash_command("beep", "boop")
    async def callback(
        ctx: tanjun.abc.Context,
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None
    option = callback.parser.options[1]
    assert option.key == "eep"
    assert option.names == ["--eep", "--hi", "--bye"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is empty_value
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="meep", channel_types=None, description="bb", is_required=False
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER, name="eep", channel_types=None, description="b", is_required=False
        ),
    ]
    assert len(callback.wrapped_command._tracked_options) == 2
    option = callback.wrapped_command._tracked_options["meep"]
    assert option.default is tanjun.abc.NO_PASS
    option = callback.wrapped_command._tracked_options["eep"]
    assert option.default is tanjun.abc.NO_PASS


def test_with_flag_and_deprecated_default():
    with pytest.warns(
        DeprecationWarning, match=re.escape("Flag.__init__'s `default` argument is deprecated, use Default instead")
    ):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("meow")
        @tanjun.as_slash_command("beep", "boop")
        async def callback(
            ctx: tanjun.abc.Context,
            eep: typing.Annotated[
                annotations.Int, annotations.Flag(default=1231), "b"  # pyright: ignore[reportDeprecated]
            ] = 545454,
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
            type=hikari.OptionType.INTEGER, name="eep", channel_types=None, description="b", is_required=False
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER, name="eep", channel_types=None, description="a", is_required=False
        )
    ]
    assert len(callback.wrapped_command._tracked_options) == 1
    option = callback.wrapped_command._tracked_options["eep"]
    assert option.default is tanjun.abc.NO_PASS


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
    assert option.default is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="beep", channel_types=None, description="eat", is_required=True
        )
    ]
    assert len(callback.wrapped_command._tracked_options) == 1
    option = callback.wrapped_command._tracked_options["beep"]
    assert option.default is tanjun.abc.NO_DEFAULT


def test_with_generic_positional():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("name")
        @tanjun.as_slash_command("boop", "description")
        async def callback(
            ctx: tanjun.abc.Context, beep: typing.Annotated[annotations.Positional[annotations.Str], "eat"]  # type: ignore
        ) -> None:
            ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert isinstance(callback.wrapped_command, tanjun.SlashCommand)
    assert len(callback.parser.arguments) == 1
    assert len(callback.parser.options) == 0
    option = callback.parser.arguments[0]
    assert option.key == "beep"
    assert option.converters == []
    assert option.default is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None

    assert callback.wrapped_command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="beep", channel_types=None, description="eat", is_required=True
        )
    ]
    assert len(callback.wrapped_command._tracked_options) == 1
    option = callback.wrapped_command._tracked_options["beep"]
    assert option.default is tanjun.abc.NO_DEFAULT


def test_with_greedy():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    async def callback(ctx: tanjun.abc.Context, meep: typing.Annotated[annotations.Int, annotations.Greedy()]):
        ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "meep"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None


def test_with_generic_greedy():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        async def callback(ctx: tanjun.abc.Context, meep: annotations.Greedy[annotations.Str]):  # type: ignore
            ...

    assert isinstance(callback.parser, tanjun.ShlexParser)
    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "meep"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length == 32
    assert option.max_length == 4343
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_length():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.Length[123], "nom"],  # type: ignore
            other_value: typing.Annotated[typing.Optional[annotations.Length[5544]], "meow"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length == 0
    assert option.max_length == 5544
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_length_when_min_specificed():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.Length[43, 5444], "nom"],  # type: ignore
            other_value: typing.Annotated[typing.Optional[annotations.Length[32, 4343]], "meow"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length == 32
    assert option.max_length == 4343
    assert option.min_value is None
    assert option.max_value is None


def test_with_int_max():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        bee: typing.Annotated[annotations.Int, annotations.Max(543), "eee"],
        yeet_no: typing.Annotated[typing.Union[annotations.Int, None], annotations.Max(543), "eep"] = None,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="bee",
            channel_types=None,
            description="eee",
            is_required=True,
            min_value=None,
            max_value=543,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="yeet_no",
            channel_types=None,
            description="eep",
            is_required=False,
            min_value=None,
            max_value=543,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["bee"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bee"
    assert tracked_option.name == "bee"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["yeet_no"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "yeet_no"
    assert tracked_option.name == "yeet_no"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "bee"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value == 543

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "yeet_no"
    assert option.names == ["--yeet-no"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value == 543


def test_with_float_max():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        bee: typing.Annotated[annotations.Float, annotations.Max(234.432), "eee"],
        yeet_no: typing.Annotated[typing.Union[annotations.Float, None], annotations.Max(234.432), "eep"] = None,
    ):
        ...

    assert isinstance(callback.wrapped_command, tanjun.MessageCommand)
    assert isinstance(callback.wrapped_command.parser, tanjun.ShlexParser)
    assert callback.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="bee",
            channel_types=None,
            description="eee",
            is_required=True,
            min_value=None,
            max_value=234.432,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="yeet_no",
            channel_types=None,
            description="eep",
            is_required=False,
            min_value=None,
            max_value=234.432,
        ),
    ]

    assert len(callback._tracked_options) == 2
    tracked_option = callback._tracked_options["bee"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bee"
    assert tracked_option.name == "bee"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["yeet_no"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "yeet_no"
    assert tracked_option.name == "yeet_no"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "bee"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value == 234.432

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "yeet_no"
    assert option.names == ["--yeet-no"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value == 234.432


@pytest.mark.parametrize(
    ("value", "converter", "option_type"),
    [(543, int, hikari.OptionType.INTEGER), (234.432, float, hikari.OptionType.FLOAT)],
)
def test_with_generic_max(
    value: typing.Union[int, float], converter: typing.Union[type[int], type[float]], option_type: hikari.OptionType
):
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("command", "description")
        @tanjun.as_message_command("command")
        async def callback(
            ctx: tanjun.abc.Context,
            number: typing.Annotated[annotations.Max[value], "eee"],  # type: ignore
            other_number: typing.Annotated[annotations.Max[value], "eep"] = 54234,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value == value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value == value


def test_with_max_when_float_for_int():
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context, value: typing.Annotated[annotations.Int, annotations.Max(123.312), "description"]
    ) -> None:
        ...

    with pytest.raises(TypeError, match="Max value of type float is not valid for a int argument"):
        annotations.parse_annotated_args(callback, follow_wrapped=True)


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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value == 432

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context,
        number: typing.Annotated[type_, annotations.Max(value), "eee"],
        other_number: typing.Annotated[type_, annotations.Max(value), "eep"] = 54234,
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is (raw_type is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is (raw_type is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [raw_type]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value == value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [raw_type]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value == value


@pytest.mark.parametrize(
    ("value", "converter", "option_type"),
    [(123, int, hikari.OptionType.INTEGER), (123.321, float, hikari.OptionType.FLOAT)],
)
def test_with_generic_min(
    value: typing.Union[int, float], converter: typing.Union[type[int], type[float]], option_type: hikari.OptionType
):
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("command", "description")
        @tanjun.as_message_command("command")
        async def callback(
            ctx: tanjun.abc.Context,
            number: typing.Annotated[annotations.Min[value], "bee"],  # type: ignore
            other_number: typing.Annotated[annotations.Min[value], "buzz"] = 321,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == value
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value == value
    assert option.max_value is None


def test_with_min_when_float_for_int():
    @tanjun.as_slash_command("command", "description")
    @tanjun.as_message_command("command")
    async def callback(
        ctx: tanjun.abc.Context, value: typing.Annotated[annotations.Int, annotations.Min(234.432), "description"]
    ) -> None:
        ...

    with pytest.raises(TypeError, match="Min value of type float is not valid for a int argument"):
        annotations.parse_annotated_args(callback, follow_wrapped=True)


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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = callback._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_value"
    assert tracked_option.name == "other_value"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 12333
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nyaa"
    assert tracked_option.name == "boop"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["meep_meep"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow"
    assert tracked_option.name == "meep_meep"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "nyaa"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--meep-meep"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nyaa"
    assert tracked_option.name == "oop"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["n"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow"
    assert tracked_option.name == "n"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "nyaa"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--boop-oop"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "necc"
    assert tracked_option.name == "nom"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = callback._tracked_options["sex"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nya"
    assert tracked_option.name == "sex"
    assert tracked_option.type is hikari.OptionType.STRING

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "necc"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "nya"
    assert option.names == ["--nya"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 44
    assert argument.max_value == 55

    assert len(callback.wrapped_command.parser.options) == 1

    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("command", "description")
        @tanjun.as_message_command("command")
        async def callback(
            ctx: tanjun.abc.Context,
            number: typing.Annotated[annotations.Ranged[min_value, max_value], "meow"],  # type: ignore
            other_number: typing.Annotated[annotations.Ranged[min_value, max_value], "nom"] = 443,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "number"
    assert tracked_option.name == "number"
    assert tracked_option.type is option_type

    tracked_option = callback._tracked_options["other_number"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is (converter is float)
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other_number"
    assert tracked_option.name == "other_number"
    assert tracked_option.type is option_type

    assert len(callback.wrapped_command.parser.arguments) == 1
    argument = callback.wrapped_command.parser.arguments[0]
    assert argument.key == "number"
    assert argument.converters == [converter]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == min_value
    assert argument.max_value == max_value

    assert len(callback.wrapped_command.parser.options) == 1
    option = callback.wrapped_command.parser.options[0]
    assert option.key == "other_number"
    assert option.names == ["--other-number"]
    assert option.converters == [converter]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value == min_value
    assert option.max_value == max_value


def test_with_snowflake_or():
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.USER

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [mock_callback]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_snowflake]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_channel():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        @tanjun.as_slash_command("yeet", "description")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.SnowflakeOr[annotations.Channel], "se"],  # type: ignore
            value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Channel]], "x"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_channel_id]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_channel_id]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_member():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        @tanjun.as_slash_command("yeet", "description")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.SnowflakeOr[annotations.Member], "se"],  # type: ignore
            value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Member]], "x"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.USER

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_user_id]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_mentionable():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        @tanjun.as_slash_command("yeet", "description")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.SnowflakeOr[annotations.Mentionable], "se"],  # type: ignore
            value_2: typing.Annotated[
                typing.Optional[annotations.SnowflakeOr[annotations.Mentionable]], "x"  # type: ignore
            ] = None,
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_snowflake]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_snowflake]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_role():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        @tanjun.as_slash_command("yeet", "description")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.SnowflakeOr[annotations.Role], "se"],  # type: ignore
            value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Role]], "x"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.ROLE

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_role_id]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_role_id]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or_for_user():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        @tanjun.as_slash_command("yeet", "description")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.SnowflakeOr[annotations.User], "se"],  # type: ignore
            value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.User]], "x"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.USER

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.conversion.parse_user_id]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_snowflake_or():
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("command")
        @tanjun.as_slash_command("yeet", "description")
        async def callback(
            ctx: tanjun.abc.Context,
            value: typing.Annotated[annotations.SnowflakeOr[annotations.Bool], "se"],  # type: ignore
            value_2: typing.Annotated[annotations.SnowflakeOr[typing.Optional[annotations.Bool]], "x"] = None,  # type: ignore
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = callback.wrapped_command._tracked_options["value_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value_2"
    assert tracked_option.name == "value_2"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    assert len(callback.parser.arguments) == 1
    argument = callback.parser.arguments[0]
    assert argument.key == "value"
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(callback.parser.options) == 1
    option = callback.parser.options[0]
    assert option.key == "value_2"
    assert option.names == ["--value-2"]
    assert option.converters == [tanjun.to_bool]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
                hikari.ChannelType.GUILD_NEWS_THREAD,
                hikari.ChannelType.GUILD_PUBLIC_THREAD,
                hikari.ChannelType.GUILD_PRIVATE_THREAD,
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
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        foo: typing.Annotated[annotations.Channel, annotations.TheseChannels(*channel_types), "meow"],
        bar: typing.Annotated[
            typing.Optional[annotations.Channel], annotations.TheseChannels(*channel_types), "boom"
        ] = None,
    ):
        ...

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.build().options) == 2
    option = command.build().options[0]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "foo"
    assert option.description == "meow"
    assert option.is_required is True
    assert option.min_length is None
    assert option.max_length is None
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
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == len(expected_types)
    assert set(option.channel_types) == expected_types

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["foo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "foo"
    assert tracked_option.name == "foo"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["bar"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bar"
    assert tracked_option.name == "bar"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "foo"
    assert len(argument.converters) == 1
    assert isinstance(argument.converters[0], tanjun.conversion.ToChannel)
    assert argument.converters[0]._allowed_types == expected_types
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "bar"
    assert option.names == ["--bar"]
    assert len(option.converters) == 1
    assert isinstance(option.converters[0], tanjun.conversion.ToChannel)
    assert option.converters[0]._allowed_types == expected_types
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_generic_these_channels():  # noqa: CFQ001
    with pytest.warns(DeprecationWarning):

        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def command(
            ctx: tanjun.abc.Context,
            bb: typing.Annotated[annotations.TheseChannels[hikari.GuildChannel], "nep"],  # type: ignore
            bat: typing.Annotated[
                typing.Optional[annotations.TheseChannels[hikari.GuildVoiceChannel, hikari.PrivateChannel]], "bip"  # type: ignore
            ] = None,
        ):
            ...

    expected_types_1 = {
        hikari.ChannelType.GUILD_CATEGORY,
        hikari.ChannelType.GUILD_NEWS,
        hikari.ChannelType.GUILD_NEWS_THREAD,
        hikari.ChannelType.GUILD_PRIVATE_THREAD,
        hikari.ChannelType.GUILD_PUBLIC_THREAD,
        hikari.ChannelType.GUILD_STAGE,
        hikari.ChannelType.GUILD_TEXT,
        hikari.ChannelType.GUILD_VOICE,
        hikari.ChannelType.GUILD_FORUM,
    }
    expected_types_2 = {hikari.ChannelType.DM, hikari.ChannelType.GROUP_DM, hikari.ChannelType.GUILD_VOICE}

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.build().options) == 2
    option = command.build().options[0]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "bb"
    assert option.description == "nep"
    assert option.is_required is True
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == 9
    assert set(option.channel_types) == expected_types_1

    option = command.build().options[1]
    assert option.type is hikari.OptionType.CHANNEL
    assert option.name == "bat"
    assert option.description == "bip"
    assert option.is_required is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None
    assert option.channel_types
    assert len(option.channel_types) == 3
    assert set(option.channel_types) == expected_types_2

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["bb"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bb"
    assert tracked_option.name == "bb"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["bat"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "bat"
    assert tracked_option.name == "bat"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "bb"
    assert len(argument.converters) == 1
    assert isinstance(argument.converters[0], tanjun.conversion.ToChannel)
    assert argument.converters[0]._allowed_types == expected_types_1
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "bat"
    assert option.names == ["--bat"]
    assert len(option.converters) == 1
    assert isinstance(option.converters[0], tanjun.conversion.ToChannel)
    assert option.converters[0]._allowed_types == expected_types_2
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_for_attachment_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.Attachment, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.Attachment, str], "feet"] = "ok",
    ) -> None:
        ...

    assert command.build().options == [
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

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT

    tracked_option = command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT


def test_for_attachment_option_on_message_command():
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: annotations.Attachment) -> None:
        ...

    with pytest.raises(
        RuntimeError, match="<class 'hikari.messages.Attachment'> is not supported for message commands"
    ):
        annotations.parse_annotated_args(command, follow_wrapped=True)


def test_for_attachment_option_on_message_command_with_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: typing.Optional[annotations.Attachment] = None) -> None:
        ...

    assert command.parser is None


def test_for_attachment_option_on_message_command_with_default_and_pre_set_parser():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.with_parser
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: typing.Optional[annotations.Attachment] = None) -> None:
        ...

    assert isinstance(command.parser, tanjun.parsing.ShlexParser)
    assert not command.parser.options
    assert not command.parser.arguments


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
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.to_bool]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert len(argument.converters) == 1
    assert isinstance(argument.converters[0], tanjun.conversion.ToChannel)
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert len(option.converters) == 1
    assert isinstance(option.converters[0], tanjun.conversion.ToChannel)
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.CHANNEL


def test_for_interaction_channel_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.InteractionChannel, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.InteractionChannel, str], "feet"] = "ok",
    ) -> None:
        ...

    assert command.build().options == [
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

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.CHANNEL


def test_for_interaction_channel_option_on_message_command():
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: annotations.InteractionChannel) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=(
            "<class 'hikari.interactions.base_interactions.InteractionChannel'> "
            "is not supported for message commands"
        ),
    ):
        annotations.parse_annotated_args(command, follow_wrapped=True)


def test_for_interaction_channel_option_on_message_command_with_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: typing.Optional[annotations.InteractionChannel] = None) -> None:
        ...

    assert command.parser is None


def test_for_interaction_channel_option_on_message_command_with_default_and_pre_set_parser():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.with_parser
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: typing.Optional[annotations.InteractionChannel] = None) -> None:
        ...

    assert isinstance(command.parser, tanjun.parsing.ShlexParser)
    assert not command.parser.options
    assert not command.parser.arguments


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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.converters == [tanjun.to_member]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.to_member]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.USER


def test_for_interaction_member_option():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("meow", "nom")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Annotated[annotations.InteractionMember, "yeet"],
        arg_2: typing.Annotated[typing.Union[annotations.InteractionMember, str], "feet"] = "ok",
    ) -> None:
        ...

    assert command.build().options == [
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

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "arg_2"
    assert tracked_option.name == "arg_2"
    assert tracked_option.type is hikari.OptionType.USER


def test_for_interaction_member_option_on_message_command():
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: annotations.InteractionMember) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=(
            "<class 'hikari.interactions.base_interactions.InteractionMember'> is not supported for message commands"
        ),
    ):
        annotations.parse_annotated_args(command, follow_wrapped=True)


def test_for_interaction_member_option_on_message_command_with_default():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: typing.Optional[annotations.InteractionMember] = None) -> None:
        ...

    assert command.parser is None


def test_for_interaction_member_option_on_message_command_with_default_and_pre_set_parser():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.with_parser
    @tanjun.as_message_command("command")
    async def command(ctx: tanjun.abc.Context, arg: typing.Optional[annotations.InteractionMember] = None) -> None:
        ...

    assert isinstance(command.parser, tanjun.parsing.ShlexParser)
    assert not command.parser.options
    assert not command.parser.arguments


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
    assert argument.converters == [tanjun.to_user, tanjun.to_role]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.to_user, tanjun.to_role]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.converters == [tanjun.to_role]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.to_role]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.converters == [tanjun.to_user]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "arg_2"
    assert option.names == ["--arg-2"]
    assert option.converters == [tanjun.to_user]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
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
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command.wrapped_command._tracked_options["arg_2"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
        value: typing.Union[typing.Annotated[annotations.Str, annotations.Positional(), "nyaa"], bool] = False,
        other_value: typing.Optional[typing.Annotated[annotations.Int, "meow"]] = None,
    ) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="value", description="nyaa", is_required=False),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            description="meow",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_PASS
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


if sys.version_info >= (3, 10):

    def test_when_annotated_not_top_level_3_10_union():
        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def command(
            ctx: tanjun.abc.Context,
            *,
            value: typing.Annotated[annotations.Str, annotations.Positional(), "nyaa"] | bool = False,
            other_value: typing.Annotated[annotations.Int, "meow"] | None = None,
        ) -> None:
            raise NotImplementedError

        assert command.build().options == [
            hikari.CommandOption(type=hikari.OptionType.STRING, name="value", description="nyaa", is_required=False),
            hikari.CommandOption(
                type=hikari.OptionType.INTEGER,
                name="other_value",
                description="meow",
                is_required=False,
                min_value=None,
                max_value=None,
            ),
        ]

        assert len(command._tracked_options) == 2
        tracked_option = command._tracked_options["value"]
        assert tracked_option.converters == []
        assert tracked_option.default is tanjun.abc.NO_PASS
        assert tracked_option.is_always_float is False
        assert tracked_option.is_only_member is False
        assert tracked_option.key == "value"
        assert tracked_option.name == "value"
        assert tracked_option.type is hikari.OptionType.STRING

        tracked_option = command._tracked_options["other_value"]
        assert tracked_option.converters == []
        assert tracked_option.default is tanjun.abc.NO_PASS
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
        assert argument.default is tanjun.abc.NO_PASS
        assert argument.is_greedy is False
        assert argument.is_multi is False
        assert argument.min_length is None
        assert argument.max_length is None
        assert argument.min_value is None
        assert argument.max_value is None

        assert len(command.wrapped_command.parser.options) == 1
        option = command.wrapped_command.parser.options[0]
        assert option.key == "other_value"
        assert option.names == ["--other-value"]
        assert option.converters == [int]
        assert option.default is tanjun.abc.NO_PASS
        assert option.empty_value is tanjun.abc.NO_DEFAULT
        assert option.is_multi is False
        assert option.min_length is None
        assert option.max_length is None
        assert option.min_value is None
        assert option.max_value is None


def test_when_annotated_handles_unions():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        *,
        value: typing.Annotated[typing.Union[annotations.Str, bool], annotations.Positional(), "nyaa"] = False,
        other_value: typing.Annotated[typing.Optional[annotations.Int], "meow"] = None,
    ) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="value", description="nyaa", is_required=False),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="other_value",
            description="meow",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["other_value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
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
    assert argument.default is tanjun.abc.NO_PASS
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "other_value"
    assert option.names == ["--other-value"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


if sys.version_info >= (3, 10):

    def test_when_annotated_handles_3_10_unions():
        @annotations.with_annotated_args(follow_wrapped=True)
        @tanjun.as_slash_command("name", "description")
        @tanjun.as_message_command("name")
        async def command(
            ctx: tanjun.abc.Context,
            *,
            value: typing.Annotated[annotations.Str | bool, annotations.Positional(), "nyaa"] = False,
            other_value: typing.Annotated[annotations.Int | None, "meow"] = None,
        ) -> None:
            raise NotImplementedError

        assert command.build().options == [
            hikari.CommandOption(type=hikari.OptionType.STRING, name="value", description="nyaa", is_required=False),
            hikari.CommandOption(
                type=hikari.OptionType.INTEGER,
                name="other_value",
                description="meow",
                is_required=False,
                min_value=None,
                max_value=None,
            ),
        ]

        assert len(command._tracked_options) == 2
        tracked_option = command._tracked_options["value"]
        assert tracked_option.converters == []
        assert tracked_option.default is tanjun.abc.NO_PASS
        assert tracked_option.is_always_float is False
        assert tracked_option.is_only_member is False
        assert tracked_option.key == "value"
        assert tracked_option.name == "value"
        assert tracked_option.type is hikari.OptionType.STRING

        tracked_option = command._tracked_options["other_value"]
        assert tracked_option.converters == []
        assert tracked_option.default is tanjun.abc.NO_PASS
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
        assert argument.default is tanjun.abc.NO_PASS
        assert argument.is_greedy is False
        assert argument.is_multi is False
        assert argument.min_length is None
        assert argument.max_length is None
        assert argument.min_value is None
        assert argument.max_value is None

        assert len(command.wrapped_command.parser.options) == 1
        option = command.wrapped_command.parser.options[0]
        assert option.key == "other_value"
        assert option.names == ["--other-value"]
        assert option.converters == [int]
        assert option.default is tanjun.abc.NO_PASS
        assert option.empty_value is tanjun.abc.NO_DEFAULT
        assert option.is_multi is False
        assert option.min_length is None
        assert option.max_length is None
        assert option.min_value is None
        assert option.max_value is None


def test_parse_annotated_args_with_descriptions_argument():
    @tanjun.as_slash_command("name", "description")
    async def command(ctx: tanjun.abc.Context, *, echo: annotations.Str, foxy: annotations.Int = 232) -> None:
        raise NotImplementedError

    annotations.parse_annotated_args(command, descriptions={"echo": "meow", "foxy": "x3", "unknown": "..."})

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="echo", description="meow", is_required=True),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="foxy",
            description="x3",
            is_required=False,
            min_value=None,
            max_value=None,
        ),
    ]


def test_parse_annotated_args_with_descriptions_argument_overrides_annotation_strings():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        *,
        uwu: typing.Annotated[annotations.Str, "ignore me pls"],
        boxy: typing.Annotated[annotations.Float, "aaaaaaaaaaa"] = 232,
    ) -> None:
        raise NotImplementedError

    annotations.parse_annotated_args(command, descriptions={"uwu": "meower", "boxy": "nuzzle", "unknown": "..."})

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="uwu", description="meower", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.FLOAT, name="boxy", description="nuzzle", is_required=False),
    ]


def test_parse_annotated_args_with_descriptions_argument_for_wrapped_slash_command():
    @tanjun.as_message_command("ignore me")
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, *, ruby: typing.Annotated[annotations.User, "not h"], rebecca: annotations.Str = "h"
    ) -> None:
        raise NotImplementedError

    annotations.parse_annotated_args(
        command, descriptions={"ruby": "shining", "rebecca": "cool gal", "unknown": "..."}, follow_wrapped=True
    )

    assert isinstance(command.wrapped_command, tanjun.SlashCommand)
    assert command.wrapped_command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="ruby", description="shining", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="rebecca", description="cool gal", is_required=False),
    ]


def test_attachment_field():
    @tanjun.as_slash_command("name", "description")
    async def command(ctx: tanjun.abc.Context, field: hikari.Attachment = annotations.attachment_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"field": "eeee"})

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ATTACHMENT, name="field", description="eeee", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["field"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "field"
    assert tracked_option.name == "field"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT


def test_attachment_field_with_config():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        field: typing.Union[hikari.Attachment, int] = annotations.attachment_field(
            description="x", default=7655, slash_name="meow_meow"
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ATTACHMENT, name="meow_meow", description="x", is_required=False)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["meow_meow"]
    assert tracked_option.converters == []
    assert tracked_option.default == 7655
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "field"
    assert tracked_option.name == "meow_meow"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT


def test_attachment_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, fobo: annotations.Bool = annotations.attachment_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=(
            "Conflicting option types of <class 'hikari.messages.Attachment'> "
            "and <class 'bool'> found for 'fobo' parameter"
        ),
    ):
        annotations.parse_annotated_args(command)


def test_attachment_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(
        ctx: tanjun.abc.Context, field: annotations.Attachment = annotations.attachment_field(description="x")
    ) -> None:
        ...


def test_bool_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, field: bool = annotations.bool_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"field": "z"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="field", description="z", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["field"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "field"
    assert tracked_option.name == "field"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "field"
    assert argument.converters == [tanjun.conversion.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_bool_field_with_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        fieldy: typing.Union[bool, None] = annotations.bool_field(
            default=None, description="very descriptive", greedy=True, positional=True, slash_name="nyaa"
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command)

    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 1
    argument = command.parser.arguments[0]
    assert argument.key == "fieldy"
    assert argument.converters == [tanjun.conversion.to_bool]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 0


def test_bool_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, fieldy: bool = annotations.bool_field(default=False)) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "fieldy"
    assert option.names == ["--fieldy"]
    assert option.converters == [tanjun.conversion.to_bool]
    assert option.default is False
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_bool_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        fieldy: typing.Optional[bool] = annotations.bool_field(
            default=None, empty_value=True, message_names=["--meow", "-a", "-b"]
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "fieldy"
    assert option.names == ["--meow", "-a", "-b"]
    assert option.converters == [tanjun.conversion.to_bool]
    assert option.default is None
    assert option.empty_value is True
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_bool_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, me: annotations.Str = annotations.bool_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError, match="Conflicting option types of <class 'bool'> and <class 'str'> found for 'me' parameter"
    ):
        annotations.parse_annotated_args(command)


def test_bool_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.Bool = annotations.bool_field(description="x")) -> None:
        ...


def test_channel_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, meow: hikari.PartialChannel = annotations.channel_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"meow": "sad"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.CHANNEL, name="meow", description="sad", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["meow"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow"
    assert tracked_option.name == "meow"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "meow"
    assert len(argument.converters) == 1
    assert isinstance(argument.converters[0], tanjun.conversion.ToChannel)
    assert argument.converters[0]._allowed_types is None
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_channel_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        meow: typing.Union[hikari.PartialChannel, hikari.Snowflake, None] = annotations.channel_field(
            channel_types=[hikari.PrivateChannel, hikari.ChannelType.GUILD_TEXT],
            default=None,
            description="descript",
            greedy=True,
            or_snowflake=True,
            positional=True,
            slash_name="aaa",
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            channel_types=[hikari.ChannelType.DM, hikari.ChannelType.GROUP_DM, hikari.ChannelType.GUILD_TEXT],
            name="aaa",
            description="descript",
            is_required=False,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["aaa"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meow"
    assert tracked_option.name == "aaa"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "meow"
    assert len(argument.converters) == 1
    assert argument.converters == [tanjun.conversion.parse_channel_id]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_channel_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, meow: typing.Optional[hikari.PartialChannel] = annotations.channel_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--meow"]
    assert len(option.converters) == 1
    assert isinstance(option.converters[0], tanjun.conversion.ToChannel)
    assert option.converters[0]._allowed_types is None
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_channel_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        meow: typing.Union[hikari.PartialChannel, int] = annotations.channel_field(
            channel_types=[hikari.ChannelType.GUILD_CATEGORY, hikari.ChannelType.GUILD_TEXT],
            default=0,
            empty_value=-1,
            message_names=["--momma", "-x", "--dra"],
            or_snowflake=True,
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--momma", "-x", "--dra"]
    assert option.converters == [tanjun.conversion.parse_channel_id]
    assert option.default == 0
    assert option.empty_value == -1
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_channel_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, xf: annotations.Float = annotations.channel_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=(
            "Conflicting option types of <class 'hikari.channels.PartialChannel'> "
            "and <class 'float'> found for 'xf' parameter"
        ),
    ):
        annotations.parse_annotated_args(command)


def test_channel_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(
        ctx: tanjun.abc.Context, field: annotations.Channel = annotations.channel_field(description="x")
    ) -> None:
        ...


def test_float_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, special: float = annotations.float_field()) -> None:
        ...

    annotations.parse_annotated_args(
        command, descriptions={"special": "can't be what you want to be"}, follow_wrapped=True
    )

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT, name="special", description="can't be what you want to be", is_required=True
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["special"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "special"
    assert tracked_option.name == "special"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "special"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_float_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        meowy: typing.Optional[float] = annotations.float_field(
            choices={"meow": 123.321, "ah": 6543.123, "eto...": 56534.2134, "bleh": 123.543},
            default=None,
            description="xxoo",
            greedy=True,
            min_value=12.2,
            max_value=547.5,
            positional=True,
            slash_name="bbbbb",
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="bbbbb",
            description="xxoo",
            choices=[
                hikari.CommandChoice(name="meow", value=123.321),
                hikari.CommandChoice(name="ah", value=6543.123),
                hikari.CommandChoice(name="eto...", value=56534.2134),
                hikari.CommandChoice(name="bleh", value=123.543),
            ],
            is_required=False,
            min_value=12.2,
            max_value=547.5,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["bbbbb"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "meowy"
    assert tracked_option.name == "bbbbb"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "meowy"
    assert len(argument.converters) == 1
    assert argument.converters == [float]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 12.2
    assert argument.max_value == 547.5

    assert len(command.wrapped_command.parser.options) == 0


def test_float_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, meow: typing.Optional[float] = annotations.float_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--meow"]
    assert option.converters == [float]
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_float_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        meow: typing.Optional[float] = annotations.float_field(
            default=None,
            empty_value=69.420,
            message_names=["--yeet", "-e", "--bleh"],
            min_value=543.123,
            max_value=123.543,
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "meow"
    assert option.names == ["--yeet", "-e", "--bleh"]
    assert option.converters == [float]
    assert option.default is None
    assert option.empty_value == 69.420
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value == 543.123
    assert option.max_value == 123.543


def test_float_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, call: annotations.Int = annotations.float_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError, match="Conflicting option types of <class 'float'> and <class 'int'> found for 'call' parameter"
    ):
        annotations.parse_annotated_args(command)


def test_float_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.Float = annotations.float_field(description="x")) -> None:
        ...


def test_int_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, ni: int = annotations.int_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"ni": "wow"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.INTEGER, name="ni", description="wow", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["ni"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "ni"
    assert tracked_option.name == "ni"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "ni"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_int_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        ni: typing.Optional[int] = annotations.int_field(
            choices={"me": 10, "you": 3},
            default=None,
            description="ooooo",
            greedy=True,
            min_value=0,
            max_value=20,
            positional=True,
            slash_name="na",
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            choices=[hikari.CommandChoice(name="me", value=10), hikari.CommandChoice(name="you", value=3)],
            name="na",
            description="ooooo",
            is_required=False,
            min_value=0,
            max_value=20,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["na"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "ni"
    assert tracked_option.name == "na"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "ni"
    assert argument.converters == [int]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 0
    assert argument.max_value == 20

    assert len(command.wrapped_command.parser.options) == 0


def test_int_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, nyaa: typing.Optional[int] = annotations.int_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "nyaa"
    assert option.names == ["--nyaa"]
    assert option.converters == [int]
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_int_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        nyaa: typing.Optional[int] = annotations.int_field(
            default=None, empty_value=0, message_names=["--yee", "-a", "--alias"], min_value=-1, max_value=666
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "nyaa"
    assert option.names == ["--yee", "-a", "--alias"]
    assert option.converters == [int]
    assert option.default is None
    assert option.empty_value == 0
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value == -1
    assert option.max_value == 666


def test_int_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, meow: annotations.Float = annotations.int_field(description="x")
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError, match="Conflicting option types of <class 'int'> and <class 'float'> found for 'meow' parameter"
    ):
        annotations.parse_annotated_args(command)


def test_int_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.Int = annotations.int_field(description="x")) -> None:
        ...


def test_member_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, nope: hikari.Member = annotations.member_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"nope": "wowo"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="nope", description="wowo", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["nope"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "nope"
    assert tracked_option.name == "nope"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "nope"
    assert argument.converters == [tanjun.to_member]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_member_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        nope: typing.Union[hikari.Member, hikari.Snowflake, None] = annotations.member_field(
            default=None, description="fine", greedy=True, or_snowflake=True, positional=True, slash_name="pancake"
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="pancake", description="fine", is_required=False)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["pancake"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "nope"
    assert tracked_option.name == "pancake"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "nope"
    assert argument.converters == [tanjun.conversion.parse_user_id]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_member_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, nep: typing.Optional[hikari.Member] = annotations.member_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "nep"
    assert option.names == ["--nep"]
    assert option.converters == [tanjun.to_member]
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_member_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        nep: typing.Union[hikari.Member, bool, None, hikari.Snowflake] = annotations.member_field(
            default=None, empty_value=False, message_names=["--x", "--ok"], or_snowflake=True
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "nep"
    assert option.names == ["--x", "--ok"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is None
    assert option.empty_value is False
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_member_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, freaky: annotations.User = annotations.member_field(description="x")
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=(
            "Conflicting option types of <class 'hikari.guilds.Member'> "
            "and <class 'hikari.users.User'> found for 'freaky' parameter"
        ),
    ):
        annotations.parse_annotated_args(command)


def test_member_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.Member = annotations.member_field(description="x")) -> None:
        ...


def test_mentionable_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, yes: typing.Union[hikari.User, hikari.Role] = annotations.mentionable_field()
    ) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"yes": "yipee"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.MENTIONABLE, name="yes", description="yipee", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["yes"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "yes"
    assert tracked_option.name == "yes"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "yes"
    assert argument.converters == [tanjun.to_user, tanjun.to_role]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_mentionable_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        idol: typing.Union[hikari.User, hikari.Role, hikari.Snowflake] = annotations.mentionable_field(
            default=hikari.Snowflake(0),
            description="You'll be fine",
            greedy=True,
            or_snowflake=True,
            positional=True,
            slash_name="echo",
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.MENTIONABLE, name="echo", description="You'll be fine", is_required=False
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["echo"]
    assert tracked_option.converters == []
    assert tracked_option.default == 0
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "idol"
    assert tracked_option.name == "echo"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "idol"
    assert argument.converters == [tanjun.to_snowflake]
    assert argument.default == 0
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None


def test_mentionable_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        nep: typing.Union[hikari.User, hikari.Role, None] = annotations.mentionable_field(default=None),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "nep"
    assert option.names == ["--nep"]
    assert option.converters == [tanjun.to_user, tanjun.to_role]
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_mentionable_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        beep: typing.Union[hikari.User, hikari.Role, None, hikari.Snowflake] = annotations.mentionable_field(
            default=hikari.Snowflake(0), empty_value=None, message_names=["--aaa", "-e", "-a"], or_snowflake=True
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "beep"
    assert option.names == ["--aaa", "-e", "-a"]
    assert option.converters == [tanjun.to_snowflake]
    assert option.default == hikari.Snowflake(0)
    assert option.empty_value is None
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_mentionable_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        ghost: annotations.Role = annotations.mentionable_field(description="x"),  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "Conflicting option types of typing.Union[hikari.users.User, hikari.guilds.Role] and "
            "<class 'hikari.guilds.Role'> found for 'ghost' parameter"
        ),
    ):
        annotations.parse_annotated_args(command)


def test_mentionable_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(
        ctx: tanjun.abc.Context, field: annotations.Mentionable = annotations.mentionable_field(description="x")
    ) -> None:
        ...


def test_role_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, arg: hikari.Role = annotations.role_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"arg": "beet"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ROLE, name="arg", description="beet", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["arg"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "arg"
    assert tracked_option.type is hikari.OptionType.ROLE

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.to_role]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_role_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        arg: typing.Union[hikari.Role, hikari.Snowflake, None] = annotations.role_field(
            default=None, description="root", greedy=True, or_snowflake=True, positional=True, slash_name="slap"
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ROLE, name="slap", description="root", is_required=False)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["slap"]
    assert tracked_option.converters == []
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "arg"
    assert tracked_option.name == "slap"
    assert tracked_option.type is hikari.OptionType.ROLE

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "arg"
    assert argument.converters == [tanjun.conversion.parse_role_id]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_role_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, nep: typing.Union[hikari.Role, None] = annotations.role_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "nep"
    assert option.names == ["--nep"]
    assert option.converters == [tanjun.to_role]
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_role_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        scrubs: typing.Union[hikari.Role, hikari.Snowflake, None] = annotations.role_field(
            default=None,
            empty_value=hikari.Snowflake(69),
            message_names=["--name", "--ear", "--nose"],
            or_snowflake=True,
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "scrubs"
    assert option.names == ["--name", "--ear", "--nose"]
    assert option.converters == [tanjun.conversion.parse_role_id]
    assert option.default is None
    assert option.empty_value == hikari.Snowflake(69)
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_role_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, cappy: annotations.Int = annotations.role_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match="Conflicting option types of <class 'hikari.guilds.Role'> and <class 'int'> found for 'cappy' parameter",
    ):
        annotations.parse_annotated_args(command)


def test_role_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.Role = annotations.role_field(description="x")) -> None:
        ...


def test_str_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, field: str = annotations.str_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"field": "root"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="field", description="root", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["field"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "field"
    assert tracked_option.name == "field"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "field"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_str_field_with_config():
    def mock_converter_1(_: str) -> int:
        raise NotImplementedError

    def mock_converter_2(_: str) -> float:
        raise NotImplementedError

    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        field: typing.Union[int, float, None] = annotations.str_field(
            choices={"aaa": "meow", "bbb": "sleep"},
            converters=[mock_converter_1, mock_converter_2],
            default=None,
            description="blam",
            greedy=True,
            min_length=4,
            max_length=69,
            positional=True,
            slash_name="name",
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="name",
            description="blam",
            is_required=False,
            choices=[hikari.CommandChoice(name="aaa", value="meow"), hikari.CommandChoice(name="bbb", value="sleep")],
            min_length=4,
            max_length=69,
        )
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["name"]
    assert tracked_option.converters == [mock_converter_1, mock_converter_2]
    assert tracked_option.default is None
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "field"
    assert tracked_option.name == "name"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "field"
    assert argument.converters == [mock_converter_1, mock_converter_2]
    assert argument.default is None
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length == 4
    assert argument.max_length == 69
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_str_field_with_single_converter():
    def mock_converter(_: str) -> bool:
        raise NotImplementedError

    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, field: bool = annotations.str_field(converters=mock_converter)) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"field": "blam"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="field", description="blam", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["field"]
    assert tracked_option.converters == [mock_converter]

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "field"
    assert argument.converters == [mock_converter]

    assert len(command.wrapped_command.parser.options) == 0


def test_str_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, poison: typing.Union[str, None] = annotations.str_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "poison"
    assert option.names == ["--poison"]
    assert option.converters == []
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_str_field_when_default_marks_as_flag_and_other_config():
    def mock_converter_1(_: str) -> int:
        raise NotImplementedError

    def mock_converter_2(_: str) -> bytes:
        raise NotImplementedError

    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        poison: typing.Union[int, bytes, str, None] = annotations.str_field(
            converters=[mock_converter_1, mock_converter_2],
            default="",
            empty_value=None,
            message_names=["--weird", "-o", "--meow"],
            min_length=10,
            max_length=100,
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "poison"
    assert option.names == ["--weird", "-o", "--meow"]
    assert option.converters == [mock_converter_1, mock_converter_2]
    assert option.default == ""
    assert option.empty_value is None
    assert option.is_multi is False
    assert option.min_length == 10
    assert option.max_length == 100
    assert option.min_value is None
    assert option.max_value is None


def test_str_field_when_default_marks_as_flag_and_single_converter():
    def mock_converter(_: str) -> str:
        raise NotImplementedError

    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        poison: typing.Union[str, None] = annotations.str_field(converters=mock_converter, default=None),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "poison"
    assert option.converters == [mock_converter]


def test_str_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, bust: annotations.Int = annotations.str_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError, match="Conflicting option types of <class 'str'> and <class 'int'> found for 'bust' parameter"
    ):
        annotations.parse_annotated_args(command)


def test_str_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.Str = annotations.str_field(description="x")) -> None:
        ...


def test_user_field():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(ctx: tanjun.abc.Context, of: hikari.User = annotations.user_field()) -> None:
        ...

    annotations.parse_annotated_args(command, descriptions={"of": "foot"}, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="of", description="foot", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_user]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_user_field_with_config():
    @tanjun.as_slash_command("name", "description")
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        scene: typing.Union[hikari.User, hikari.Snowflake] = annotations.user_field(
            default=hikari.Snowflake(0),
            description="gm",
            greedy=True,
            or_snowflake=True,
            positional=True,
            slash_name="easter",
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="easter", description="gm", is_required=False)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["easter"]
    assert tracked_option.converters == []
    assert tracked_option.default == hikari.Snowflake(0)
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "scene"
    assert tracked_option.name == "easter"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "scene"
    assert argument.converters == [tanjun.conversion.parse_user_id]
    assert argument.default == hikari.Snowflake(0)
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_user_field_when_default_marks_as_flag():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context, sl: typing.Union[hikari.User, None] = annotations.user_field(default=None)
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "sl"
    assert option.names == ["--sl"]
    assert option.converters == [tanjun.to_user]
    assert option.default is None
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_user_field_when_default_marks_as_flag_and_other_config():
    @tanjun.as_message_command("name")
    async def command(
        ctx: tanjun.abc.Context,
        ut: typing.Union[hikari.User, None, hikari.Snowflake] = annotations.user_field(
            default=None, empty_value=hikari.Snowflake(4), message_names=["--name", "--allied", "-b"], or_snowflake=True
        ),
    ) -> None:
        ...

    annotations.parse_annotated_args(command, follow_wrapped=True)

    assert isinstance(command.parser, tanjun.ShlexParser)
    assert len(command.parser.arguments) == 0

    assert len(command.parser.options) == 1
    option = command.parser.options[0]
    assert option.key == "ut"
    assert option.names == ["--name", "--allied", "-b"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is None
    assert option.empty_value == hikari.Snowflake(4)
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_user_field_when_type_mismatch():
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context, fed: annotations.Member = annotations.user_field(description="x")  # type: ignore
    ) -> None:
        ...

    with pytest.raises(
        RuntimeError,
        match=(
            "Conflicting option types of <class 'hikari.users.User'> "
            "and <class 'hikari.guilds.Member'> found for 'fed' parameter"
        ),
    ):
        annotations.parse_annotated_args(command)


def test_user_field_when_type_match():
    @annotations.with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def _(ctx: tanjun.abc.Context, field: annotations.User = annotations.user_field(description="x")) -> None:
        ...


def test_with_unpacked_stdlib_typed_dict():
    class TypedDict(typing.TypedDict):
        amber: typing.Annotated[annotations.User, "umfy"]
        candy: str
        detrimental: typing.Annotated[annotations.Bool, "omfy"]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="amber", description="umfy", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="detrimental", description="omfy", is_required=True),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["amber"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "amber"
    assert tracked_option.name == "amber"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command._tracked_options["detrimental"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "detrimental"
    assert tracked_option.name == "detrimental"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 2
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "amber"
    assert argument.converters == [tanjun.to_user]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    argument = command.wrapped_command.parser.arguments[1]
    assert argument.key == "detrimental"
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None


def test_with_unpacked_other_syntax_typed_dict():
    TypedDict = typing_extensions.TypedDict(  # noqa: N806
        "TypedDict",
        {
            "baz": typing_extensions.NotRequired[typing.Annotated[annotations.Float, "eep"]],
            "ban": typing_extensions.Required[typing.Annotated[annotations.Color, "beep"]],
            "pickle": typing.Literal["Candy"],
            "nyaa": typing.Annotated[annotations.Bool, "meow"],
        },
    )

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="ban", description="beep", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="nyaa", description="meow", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.FLOAT, name="baz", description="eep", is_required=False),
    ]

    assert len(command._tracked_options) == 3
    tracked_option = command._tracked_options["baz"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "baz"
    assert tracked_option.name == "baz"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = command._tracked_options["ban"]
    assert tracked_option.converters == [tanjun.to_color]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "ban"
    assert tracked_option.name == "ban"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["nyaa"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "nyaa"
    assert tracked_option.name == "nyaa"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 2
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "ban"
    assert argument.converters == [tanjun.to_color]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    argument = command.wrapped_command.parser.arguments[1]
    assert argument.key == "nyaa"
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "baz"
    assert option.names == ["--baz"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_empty_unpacked_typed_dict():
    class TypedDict(typing_extensions.TypedDict):
        pickle: str

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == []

    assert len(command._tracked_options) == 0

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert not command.wrapped_command.parser


def test_with_empty_unpacked_typed_dict_where_total_is_false():
    class TypedDict(typing_extensions.TypedDict, total=False):
        me: typing.Annotated[annotations.Role, "c"]
        too: typing_extensions.Required[typing.Annotated[annotations.Bool, "b"]]
        nope: str
        three: typing.Annotated[annotations.Str, "a"]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="too", description="b", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.ROLE, name="me", description="c", is_required=False),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="three", description="a", is_required=False),
    ]

    assert len(command._tracked_options) == 3
    tracked_option = command._tracked_options["me"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "me"
    assert tracked_option.name == "me"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = command._tracked_options["too"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "too"
    assert tracked_option.name == "too"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = command._tracked_options["three"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "three"
    assert tracked_option.name == "three"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "too"
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 2
    option = command.wrapped_command.parser.options[0]
    assert option.key == "me"
    assert option.names == ["--me"]
    assert option.converters == [tanjun.to_role]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None

    option = command.wrapped_command.parser.options[1]
    assert option.key == "three"
    assert option.names == ["--three"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_other_args():
    class TypedDict(typing_extensions.TypedDict):
        other: typing_extensions.NotRequired[typing.Annotated[annotations.Int, "bat"]]
        value: typing.Annotated[annotations.User, "meow"]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(
        ctx: tanjun.abc.Context,
        blam: typing.Annotated[annotations.Bool, "sleep"],
        **kwargs: typing_extensions.Unpack[TypedDict],
    ) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="blam", description="sleep", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.USER, name="value", description="meow", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.INTEGER, name="other", description="bat", is_required=False),
    ]

    assert len(command._tracked_options) == 3
    tracked_option = command._tracked_options["blam"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "blam"
    assert tracked_option.name == "blam"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = command._tracked_options["other"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other"
    assert tracked_option.name == "other"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command._tracked_options["value"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "value"
    assert tracked_option.name == "value"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 2
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "blam"
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    argument = command.wrapped_command.parser.arguments[1]
    assert argument.key == "value"
    assert argument.converters == [tanjun.to_user]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "other"
    assert option.names == ["--other"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_attachment():
    class TypedDict(typing_extensions.TypedDict):
        field: typing.Annotated[annotations.Attachment, "meow"]
        other: typing_extensions.NotRequired[typing.Annotated[annotations.Attachment, "nyaa"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ATTACHMENT, name="field", description="meow", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.ATTACHMENT, name="other", description="nyaa", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["field"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "field"
    assert tracked_option.name == "field"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT

    tracked_option = command._tracked_options["other"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "other"
    assert tracked_option.name == "other"
    assert tracked_option.type is hikari.OptionType.ATTACHMENT


def test_with_unpacked_typed_dict_and_bool():
    class TypedDict(typing_extensions.TypedDict):
        fi: typing.Annotated[annotations.Bool, "nn"]
        to: typing_extensions.NotRequired[typing.Annotated[annotations.Bool, "xn"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="fi", description="nn", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.BOOLEAN, name="to", description="xn", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["fi"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "fi"
    assert tracked_option.name == "fi"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    tracked_option = command._tracked_options["to"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "to"
    assert tracked_option.name == "to"
    assert tracked_option.type is hikari.OptionType.BOOLEAN

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "fi"
    assert argument.converters == [tanjun.to_bool]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "to"
    assert option.names == ["--to"]
    assert option.converters == [tanjun.to_bool]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_channel():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Channel, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Channel, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.CHANNEL, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.CHANNEL, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert len(argument.converters) == 1
    assert isinstance(argument.converters[0], tanjun.conversion.ToChannel)
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert len(option.converters) == 1
    assert isinstance(option.converters[0], tanjun.conversion.ToChannel)
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_choices():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Str, annotations.Choices({"hi": "meow", "blam": "xd"}), "maaaa"]
        oo: typing_extensions.NotRequired[
            typing.Annotated[annotations.Int, annotations.Choices({"m": 1, "ddd": 420}), "xat"]
        ]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="of",
            description="maaaa",
            is_required=True,
            choices=[hikari.CommandChoice(name="hi", value="meow"), hikari.CommandChoice(name="blam", value="xd")],
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER,
            name="oo",
            description="xat",
            is_required=False,
            choices=[hikari.CommandChoice(name="m", value=1), hikari.CommandChoice(name="ddd", value=420)],
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_color():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Color, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Color, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == [tanjun.to_color]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == [tanjun.to_color]
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_color]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_color]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_converted():
    mock_callback_1 = mock.Mock()
    mock_callback_2 = mock.Mock()

    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[typing.Any, annotations.Converted(mock_callback_1), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[typing.Any, annotations.Converted(mock_callback_2), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == [mock_callback_1]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == [mock_callback_2]
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [mock_callback_1]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [mock_callback_2]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_datetime():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Datetime, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Datetime, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == [tanjun.to_datetime]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == [tanjun.to_datetime]
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_datetime]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_datetime]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_default():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Int, annotations.Default(0), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Float, annotations.Default(0.1), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.INTEGER, name="of", description="maaaa", is_required=False),
        hikari.CommandOption(type=hikari.OptionType.FLOAT, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default == 0
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default == 0.1
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.options) == 2
    option = command.wrapped_command.parser.options[0]
    assert option.key == "of"
    assert option.names == ["--of"]
    assert option.converters == [int]
    assert option.default == 0
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None

    option = command.wrapped_command.parser.options[1]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [float]
    assert option.default == 0.1
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_flag():
    class TypedDict(typing_extensions.TypedDict):
        of: typing_extensions.NotRequired[
            typing.Annotated[annotations.Int, annotations.Flag(aliases=["-o"], empty_value="aaaa"), "maaaa"]
        ]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.INTEGER, name="of", description="maaaa", is_required=False)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 0

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "of"
    assert option.names == ["--of", "-o"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value == "aaaa"
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_float():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Float, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Float, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.FLOAT, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.FLOAT, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_greedy():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Str, annotations.Greedy(), "maaaa"]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="of", description="maaaa", is_required=True)
    ]

    assert len(command._tracked_options) == 1
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is True
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 0


def test_with_unpacked_typed_dict_and_int():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Int, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Int, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.INTEGER, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.INTEGER, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_interaction_channel():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.InteractionChannel, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.InteractionChannel, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.CHANNEL, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.CHANNEL, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.CHANNEL


def test_with_unpacked_typed_dict_and_interaction_member():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.InteractionMember, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.InteractionMember, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.USER, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.USER


def test_with_unpacked_typed_dict_and_length():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Str, annotations.Length(232), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Str, annotations.Length(4, 128), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.STRING,
            name="of",
            description="maaaa",
            is_required=True,
            min_length=0,
            max_length=232,
        ),
        hikari.CommandOption(
            type=hikari.OptionType.STRING, name="oo", description="xat", is_required=False, min_length=4, max_length=128
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length == 0
    assert argument.max_length == 232
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length == 4
    assert option.max_length == 128
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_max():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Int, annotations.Max(453), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Float, annotations.Max(69.420), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER, name="of", description="maaaa", is_required=True, max_value=453
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT, name="oo", description="xat", is_required=False, max_value=69.420
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value == 453

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value == 69.420


def test_with_unpacked_typed_dict_and_member():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Member, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Member, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.USER, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_member]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_member]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_mentionable():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Mentionable, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Mentionable, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.MENTIONABLE, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.MENTIONABLE, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.MENTIONABLE

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_user, tanjun.to_role]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_user, tanjun.to_role]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_min():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Float, annotations.Min(3.2), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Int, annotations.Min(32), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT, name="of", description="maaaa", is_required=True, min_value=3.2
        ),
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER, name="oo", description="xat", is_required=False, min_value=32
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.INTEGER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 3.2
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [int]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value == 32
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_name():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Float, annotations.Name("hi"), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.User, annotations.Name("nye"), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.FLOAT, name="hi", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.USER, name="nye", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["hi"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "hi"
    assert tracked_option.type is hikari.OptionType.FLOAT

    tracked_option = command._tracked_options["nye"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "nye"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [float]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--nye"]
    assert option.converters == [tanjun.to_user]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_positional():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Int, annotations.Positional(), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Str, annotations.Positional(), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert isinstance(command.parser, tanjun.ShlexParser)

    assert len(command.parser.arguments) == 2
    argument = command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    argument = command.parser.arguments[1]
    assert argument.key == "oo"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_PASS
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.parser.options) == 0


def test_with_unpacked_typed_dict_and_ranged():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Int, annotations.Ranged(4, 64), "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Float, annotations.Ranged(12.21, 54.34), "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.INTEGER, name="of", description="maaaa", is_required=True, min_value=4, max_value=64
        ),
        hikari.CommandOption(
            type=hikari.OptionType.FLOAT,
            name="oo",
            description="xat",
            is_required=False,
            min_value=12.21,
            max_value=54.34,
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.INTEGER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is True
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.FLOAT

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [int]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value == 4
    assert argument.max_value == 64

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [float]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value == 12.21
    assert option.max_value == 54.34


def test_with_unpacked_typed_dict_and_role():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Role, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Role, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ROLE, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.ROLE, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.ROLE

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_role]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_role]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_snowflake():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Snowflake, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Snowflake, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == [tanjun.to_snowflake]
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == [tanjun.to_snowflake]
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_snowflake]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_snowflake]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_snowflake_or():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[
            typing.Union[annotations.Role, hikari.Snowflake],
            annotations.SnowflakeOr(parse_id=tanjun.conversion.parse_role_id),
            "maaaa",
        ]
        oo: typing_extensions.NotRequired[
            typing.Annotated[
                typing.Union[annotations.Member, hikari.Snowflake],
                annotations.SnowflakeOr(parse_id=tanjun.conversion.parse_user_id),
                "xat",
            ]
        ]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.ROLE, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.USER, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.ROLE

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is True
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.conversion.parse_role_id]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.conversion.parse_user_id]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_str():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.Str, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.Str, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.STRING, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.STRING, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.STRING

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.STRING

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == []
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == []
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_these_channels():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[
            annotations.Channel, annotations.TheseChannels(hikari.ChannelType.DM, hikari.GuildThreadChannel), "maaaa"
        ]
        oo: typing_extensions.NotRequired[
            typing.Annotated[annotations.Channel, annotations.TheseChannels(hikari.GuildTextChannel), "xat"]
        ]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            name="of",
            description="maaaa",
            is_required=True,
            channel_types=[
                hikari.ChannelType.DM,
                hikari.ChannelType.GUILD_NEWS_THREAD,
                hikari.ChannelType.GUILD_PUBLIC_THREAD,
                hikari.ChannelType.GUILD_PRIVATE_THREAD,
            ],
        ),
        hikari.CommandOption(
            type=hikari.OptionType.CHANNEL,
            name="oo",
            description="xat",
            is_required=False,
            channel_types=[hikari.ChannelType.GUILD_TEXT],
        ),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.CHANNEL

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert len(argument.converters) == 1
    assert isinstance(argument.converters[0], tanjun.conversion.ToChannel)
    assert argument.converters[0]._allowed_types == {
        hikari.ChannelType.DM,
        hikari.ChannelType.GUILD_NEWS_THREAD,
        hikari.ChannelType.GUILD_PUBLIC_THREAD,
        hikari.ChannelType.GUILD_PRIVATE_THREAD,
    }
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert len(option.converters) == 1
    assert isinstance(option.converters[0], tanjun.conversion.ToChannel)
    assert option.converters[0]._allowed_types == {hikari.ChannelType.GUILD_TEXT}
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_with_unpacked_typed_dict_and_user():
    class TypedDict(typing_extensions.TypedDict):
        of: typing.Annotated[annotations.User, "maaaa"]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.User, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[TypedDict]) -> None:
        raise NotImplementedError

    assert command.build().options == [
        hikari.CommandOption(type=hikari.OptionType.USER, name="of", description="maaaa", is_required=True),
        hikari.CommandOption(type=hikari.OptionType.USER, name="oo", description="xat", is_required=False),
    ]

    assert len(command._tracked_options) == 2
    tracked_option = command._tracked_options["of"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_DEFAULT
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "of"
    assert tracked_option.name == "of"
    assert tracked_option.type is hikari.OptionType.USER

    tracked_option = command._tracked_options["oo"]
    assert tracked_option.converters == []
    assert tracked_option.default is tanjun.abc.NO_PASS
    assert tracked_option.is_always_float is False
    assert tracked_option.is_only_member is False
    assert tracked_option.key == "oo"
    assert tracked_option.name == "oo"
    assert tracked_option.type is hikari.OptionType.USER

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert isinstance(command.wrapped_command.parser, tanjun.ShlexParser)

    assert len(command.wrapped_command.parser.arguments) == 1
    argument = command.wrapped_command.parser.arguments[0]
    assert argument.key == "of"
    assert argument.converters == [tanjun.to_user]
    assert argument.default is tanjun.abc.NO_DEFAULT
    assert argument.is_greedy is False
    assert argument.is_multi is False
    assert argument.min_length is None
    assert argument.max_length is None
    assert argument.min_value is None
    assert argument.max_value is None

    assert len(command.wrapped_command.parser.options) == 1
    option = command.wrapped_command.parser.options[0]
    assert option.key == "oo"
    assert option.names == ["--oo"]
    assert option.converters == [tanjun.to_user]
    assert option.default is tanjun.abc.NO_PASS
    assert option.empty_value is tanjun.abc.NO_DEFAULT
    assert option.is_multi is False
    assert option.min_length is None
    assert option.max_length is None
    assert option.min_value is None
    assert option.max_value is None


def test_ignores_non_typed_dict_class_in_kwargs_unpack():
    class CustomClass:
        of: typing.Annotated[annotations.User, "maaaa"]  # pyright: ignore[reportUninitializedInstanceVariable]
        oo: typing_extensions.NotRequired[typing.Annotated[annotations.User, "xat"]]  # type: ignore

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: typing_extensions.Unpack[CustomClass]) -> None:  # type: ignore
        raise NotImplementedError

    assert command.build().options == []
    assert command._tracked_options == {}

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_ignores_non_unpack_kwargs():
    class TypedDict(typing_extensions.TypedDict):
        meow: typing.Annotated[annotations.User, "maaaa"]
        echo: typing_extensions.NotRequired[typing.Annotated[annotations.User, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs: TypedDict) -> None:
        raise NotImplementedError

    assert command.build().options == []
    assert command._tracked_options == {}

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_ignores_unpack_typed_dict_for_varargs():
    class TypedDict(typing_extensions.TypedDict):
        meow: typing.Annotated[annotations.User, "maaaa"]
        echo: typing_extensions.NotRequired[typing.Annotated[annotations.User, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, *args: typing_extensions.Unpack[TypedDict]) -> None:  # type: ignore
        raise NotImplementedError

    assert command.build().options == []
    assert command._tracked_options == {}

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_ignores_unpack_typed_dict_for_non_var_arg():
    class TypedDict(typing_extensions.TypedDict):
        meow: typing.Annotated[annotations.User, "maaaa"]
        echo: typing_extensions.NotRequired[typing.Annotated[annotations.User, "xat"]]

    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, arg: typing_extensions.Unpack[TypedDict]) -> None:  # type: ignore
        raise NotImplementedError

    assert command.build().options == []
    assert command._tracked_options == {}

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None


def test_ignores_untyped_kwargs():
    @annotations.with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("a", "b")
    @tanjun.as_message_command("x", "3")
    async def command(ctx: tanjun.abc.Context, **kwargs) -> None:  # type: ignore
        raise NotImplementedError

    assert command.build().options == []
    assert command._tracked_options == {}

    assert isinstance(command.wrapped_command, tanjun.MessageCommand)
    assert command.wrapped_command.parser is None
