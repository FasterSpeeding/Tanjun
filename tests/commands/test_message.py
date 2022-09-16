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

# pyright: reportIncompatibleMethodOverride=none
# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import inspect
import types
import typing
from collections import abc as collections
from unittest import mock

import hikari
import pytest

import tanjun
from tanjun import _internal
from tanjun.commands import base as base_command

_T = typing.TypeVar("_T")


def stub_class(
    cls: typing.Type[_T],
    /,
    args: collections.Sequence[typing.Any] = (),
    kwargs: typing.Optional[collections.Mapping[str, typing.Any]] = None,
    **namespace: typing.Any,
) -> _T:
    namespace["__slots__"] = ()

    for name in getattr(cls, "__abstractmethods__", None) or ():
        if name not in namespace:
            namespace[name] = mock.MagicMock()

    name = origin.__name__ if (origin := getattr(cls, "__origin__", None)) else cls.__name__
    new_cls = types.new_class(name, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)(*args, **kwargs or {})


def test_as_message_command():
    mock_callback = mock.Mock()
    command = tanjun.as_message_command("a", "b")(mock_callback)

    assert command.names == ["a", "b"]
    assert command.callback is mock_callback
    assert command.wrapped_command is None


@pytest.mark.parametrize(
    "other_command",
    [
        tanjun.SlashCommand[typing.Any](mock.Mock(), "e", "a"),
        tanjun.MessageCommand[typing.Any](mock.Mock(), "b"),
        tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "a"),
    ],
)
def test_as_message_command_when_wrapping_command(
    other_command: typing.Union[
        tanjun.SlashCommand[typing.Any],
        tanjun.MessageCommand[typing.Any],
        tanjun.MenuCommand[typing.Any, typing.Any],
    ]
):
    command = tanjun.as_message_command("a", "b")(other_command)

    assert command.wrapped_command is other_command
    assert command.callback is other_command.callback


def test_as_message_command_group():
    mock_callback = mock.Mock()
    command = tanjun.as_message_command_group("c", "b", strict=True)(mock_callback)

    assert command.names == ["c", "b"]
    assert command.is_strict is True
    assert command.callback is mock_callback
    assert command.wrapped_command is None


@pytest.mark.parametrize(
    "other_command",
    [
        tanjun.SlashCommand[typing.Any](mock.Mock(), "e", "a"),
        tanjun.MessageCommand[typing.Any](mock.Mock(), "b"),
        tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "a"),
    ],
)
def test_as_message_command_group_when_wrapping_command(
    other_command: typing.Union[
        tanjun.SlashCommand[typing.Any],
        tanjun.MessageCommand[typing.Any],
        tanjun.MenuCommand[typing.Any, typing.Any],
    ]
):
    command = tanjun.as_message_command_group("c", "b", strict=True)(other_command)

    assert command.wrapped_command is other_command
    assert command.callback is other_command.callback


class TestMessageCommand:
    @pytest.mark.parametrize(
        "inner_command",
        [
            tanjun.SlashCommand[typing.Any](mock.Mock(), "a", "b"),
            tanjun.MessageCommand[typing.Any](mock.Mock(), "a"),
            tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "e"),
        ],
    )
    def test___init___when_command_object(
        self,
        inner_command: typing.Union[
            tanjun.SlashCommand[tanjun.abc.CommandCallbackSig],
            tanjun.MenuCommand[typing.Any, typing.Any],
        ],
    ):
        assert tanjun.MessageCommand(inner_command, "woow").callback is inner_command.callback

    @pytest.mark.skip(reason="TODO")
    def test___repr__(self):
        ...

    @pytest.mark.asyncio()
    async def test___call__(self):
        mock_callback = mock.AsyncMock()
        command = tanjun.MessageCommand[typing.Any](mock_callback, "yee", "nsoosos")

        await command(65123, "okokok", a="odoosd", gf=435123)  # type: ignore

        mock_callback.assert_awaited_once_with(65123, "okokok", a="odoosd", gf=435123)

    def test_callback_property(self):
        mock_callback = mock.Mock()

        assert tanjun.MessageCommand(mock_callback, "yee", "nsoosos").callback is mock_callback

    def test_names_property(self):
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc")

        assert command.names == ["aaaaa", "bbbbb", "ccccc"]

    def test_parent_property(self):
        mock_parent = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parent(mock_parent)

        assert command.parent is mock_parent

    def test_parser_property(self):
        mock_parser = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parser(mock_parser)

        assert command.parser is mock_parser

    def test_set_parser(self):
        @tanjun.as_message_command("meow")
        async def command(ctx: tanjun.abc.MessageContext, name: str, value: int, beep: bool):
            ...

        parser = tanjun.parsing.ShlexParser().validate_arg_keys("other", ["name", "value"])
        command.set_parser(parser)
        tanjun.with_argument("name")(command)
        tanjun.with_option("value", "--value", default=None)(command)
        tanjun.with_argument("beep")(command)

    def test_set_parser_when_no_signature(self):
        with pytest.raises(ValueError, match=".+"):
            inspect.Signature.from_callable(int)

        command: tanjun.MessageCommand[typing.Any] = tanjun.MessageCommand(int, "name")  # type: ignore

        tanjun.with_option("meow", "--nyaa", default=123)(command)
        tanjun.with_argument("meow")(command)

    def test_set_parser_when_invalid_argument_key(self):
        @tanjun.as_message_command("meow")
        async def meow_command(ctx: tanjun.abc.MessageContext, *args: str, name: str):
            ...

        parser = tanjun.parsing.ShlexParser().validate_arg_keys("other", ["name", "beep"])
        meow_command.set_parser(parser)

        with pytest.raises(ValueError, match="'beep' is not a valid keyword argument for meow_command"):
            tanjun.with_argument("beep")(meow_command)

    def test_set_parser_when_invalid_option_key(self):
        @tanjun.as_message_command("meow")
        async def command_name(ctx: tanjun.abc.MessageContext, *args: str, name: str):
            ...

        parser = tanjun.parsing.ShlexParser().validate_arg_keys("other", ["name", "nock"])
        command_name.set_parser(parser)

        with pytest.raises(ValueError, match="'nock' is not a valid keyword argument for command_name"):
            tanjun.with_option("nock", "--nock", default=123)(command_name)

    def test_set_parser_when_invalid_key_but_not_validating(self):
        @tanjun.as_message_command("meow", validate_arg_keys=False)
        async def command(ctx: tanjun.abc.MessageContext, name: str):
            ...

        tanjun.with_option("meow", "--nyaa", default=123)(command)
        tanjun.with_argument("meow")(command)

    def test_set_parser_when_invalid_argument_key_added_afterwards(self):
        @tanjun.with_argument("name")
        @tanjun.as_message_command("meow")
        async def next_command(ctx: tanjun.abc.MessageContext, name: str):
            ...

        with pytest.raises(ValueError, match="'se' is not a valid keyword argument for next_command"):
            tanjun.with_argument("se")(next_command)

    def test_set_parser_when_invalid_option_key_added_afterwards(self):
        @tanjun.with_option("name", "--name", default="")
        @tanjun.as_message_command("meow")
        async def nyaa_command(ctx: tanjun.abc.MessageContext, name: str):
            ...

        with pytest.raises(ValueError, match="'boop' is not a valid keyword argument for nyaa_command"):
            tanjun.with_option("boop", "--boop", default=123)(nyaa_command)

    def test_set_parser_when_invalid_option_key_added_afterwards_but_not_validating(self):
        @tanjun.with_argument("blam")
        @tanjun.with_option("name", "--name", default="")
        @tanjun.as_message_command("meow", validate_arg_keys=False)
        async def command(ctx: tanjun.abc.MessageContext, name: str, blam: int):
            ...

        tanjun.with_option("boop", "--boop", default=123)(command)
        tanjun.with_argument("not_a_name")(command)

    def test_set_parser_when_argument_key_invalid_for_other_linked_callback(self):
        @tanjun.as_message_command("name", "description")
        async def command(ctx: tanjun.abc.MessageContext, name: str, meow: str, meowed: str):
            ...

        parser = tanjun.parsing.ShlexParser()
        parser.validate_arg_keys("test_callback", ["meow", "bye"])
        tanjun.with_argument("meow")(command.set_parser(parser))

        with pytest.raises(ValueError, match="'meowed' is not a valid keyword argument for test_callback"):
            tanjun.with_argument("meowed")(command)

    def test_set_parser_when_option_key_invalid_for_other_linked_callback(self):
        @tanjun.as_message_command("name", "description")
        async def command(ctx: tanjun.abc.MessageContext, name: str, eep: str, nyaned: bool):
            ...

        parser = tanjun.parsing.ShlexParser()
        parser.validate_arg_keys("test_callback", ["eep", "e"])
        tanjun.with_option("eep", "--eep", default=None)(command.set_parser(parser))

        with pytest.raises(ValueError, match="'nyaned' is not a valid keyword argument for test_callback"):
            tanjun.with_option("nyaned", "--nyaned", default=123)(command)

    def test_set_parser_when_existing_argument_not_valid_for_callback(self):
        @tanjun.as_message_command("name", "description")
        async def eep_command(ctx: tanjun.abc.MessageContext, name: str, meow: str, meowed: str):
            ...

        parser = tanjun.parsing.ShlexParser().add_argument("meow").add_argument("meowed").add_argument("namer")

        with pytest.raises(ValueError, match="'namer' is not a valid keyword argument for eep_command"):
            eep_command.set_parser(parser)

    def test_set_parser_when_existing_option_not_valid_for_callback(self):
        @tanjun.as_message_command("name", "description")
        async def test_command(ctx: tanjun.abc.MessageContext, name: str, eep: str, nyaned: bool):
            ...

        parser = (
            tanjun.parsing.ShlexParser()
            .add_option("eep", "--eep", default=None)
            .add_option("nyaned", "--nyaned", default=None)
            .add_option("bang", "--bang", default=123)
        )

        with pytest.raises(ValueError, match="'bang' is not a valid keyword argument for test_command"):
            test_command.set_parser(parser)

    def test_set_parser_when_callback_has_no_name(self):
        class OtherCallback:
            async def __call__(self, ctx: tanjun.abc.Context, name: str, beep: int) -> None:
                ...

        other_callback = OtherCallback()
        assert not hasattr(other_callback, "__name__")
        parser = tanjun.parsing.ShlexParser()
        tanjun.MessageCommand(other_callback, "name", validate_arg_keys=True).set_parser(parser)

        with pytest.raises(ValueError, match=f"'boop' is not a valid keyword argument for {repr(other_callback)}"):
            parser.add_argument("boop")

    def test_bind_client(self):
        mock_client = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc")

        with mock.patch.object(base_command.PartialCommand, "bind_client") as bind_client:
            command.bind_client(mock_client)

            bind_client.assert_called_once_with(mock_client)

    def test_bind_client_when_has_parser(self):
        mock_client = mock.Mock()
        mock_parser = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parser(mock_parser)

        with mock.patch.object(base_command.PartialCommand, "bind_client") as bind_client:
            command.bind_client(mock_client)

            bind_client.assert_called_once_with(mock_client)

        mock_parser.bind_client.assert_called_once_with(mock_client)

    def test_bind_component(self):
        mock_component = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc")

        with mock.patch.object(base_command.PartialCommand, "bind_component") as bind_component:
            command.bind_component(mock_component)

            bind_component.assert_called_once_with(mock_component)

    def test_bind_component_when_has_parser(self):
        mock_component = mock.Mock()
        mock_parser = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parser(mock_parser)

        with mock.patch.object(base_command.PartialCommand, "bind_component") as bind_component:
            command.bind_component(mock_component)

            bind_component.assert_called_once_with(mock_component)

        mock_parser.bind_component.assert_called_once_with(mock_component)

    @pytest.mark.skip(reason="TODO")
    def test_copy(self):
        ...

    @pytest.mark.asyncio()
    async def test_check_context(self):
        mock_callback = mock.Mock()
        mock_other_callback = mock.Mock()
        mock_context = mock.Mock()

        command = (
            tanjun.MessageCommand[typing.Any](mock.Mock(), "yee", "nsoosos")
            .add_check(mock_callback)
            .add_check(mock_other_callback)
        )

        with mock.patch.object(_internal, "gather_checks", new=mock.AsyncMock()) as gather_checks:
            result = await command.check_context(mock_context)

            gather_checks.assert_awaited_once_with(mock_context, [mock_callback, mock_other_callback])

        assert result is gather_checks.return_value
        mock_context.set_command.assert_has_calls([mock.call(command), mock.call(None)])

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_execute(self):
        ...

    def test_load_into_component(self):
        mock_component = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "yee", "nsoosos")

        command.load_into_component(mock_component)

        mock_component.add_message_command.assert_called_once_with(command)

    def test_load_into_component_when_wrapped_command_set(self):
        mock_component = mock.Mock()
        mock_other_command = mock.Mock()
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "yee", "nsoosos")
        command._wrapped_command = mock_other_command

        command.load_into_component(mock_component)

        mock_component.add_message_command.assert_called_once_with(command)
        mock_other_command.load_into_component.assert_not_called()

    def test_load_into_component_when_wrapped_command_is_loadable(self):
        mock_component = mock.Mock()
        mock_other_command = mock.Mock(tanjun.components.AbstractComponentLoader)
        command = tanjun.MessageCommand[typing.Any](mock.Mock(), "yee", "nsoosos")
        command._wrapped_command = mock_other_command

        command.load_into_component(mock_component)

        mock_component.add_message_command.assert_called_once_with(command)
        mock_other_command.load_into_component.assert_called_once_with(mock_component)


class TestMessageCommandGroup:
    @pytest.mark.skip(reason="TODO")
    def test___repr__(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_commands_property(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_is_strict_property(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_copy(self):
        ...

    def test_add_command(self):
        mock_command = mock.Mock()
        command_group = tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos")

        result = command_group.add_command(mock_command)

        assert result is command_group
        mock_command.set_parent.assert_called_once_with(command_group)
        assert mock_command in command_group.commands

    def test_add_command_when_already_present(self):
        mock_command = mock.Mock()
        command_group = tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos")

        result = command_group.add_command(mock_command).add_command(mock_command)

        assert result is command_group
        assert list(command_group.commands).count(mock_command) == 1

    def test_add_command_when_strict(self):
        mock_command = mock.Mock(names={"a", "b"})
        command_group = tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos", strict=True)

        result = command_group.add_command(mock_command)

        assert result is command_group
        mock_command.set_parent.assert_called_once_with(command_group)
        assert mock_command in command_group.commands

    def test_add_command_when_strict_and_space_in_any_name(self):
        command_group = tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos", strict=True)

        with pytest.raises(
            ValueError, match="Sub-command names may not contain spaces in a strict message command group"
        ):
            command_group.add_command(mock.Mock(names={"a space", "b"}))

    def test_add_command_when_strict_and_conflicts_found(self):
        command_group = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos", strict=True)
            .add_command(mock.Mock(names={"aaa", "b"}))
            .add_command(mock.Mock(names={"fsa", "dsaasd"}))
        )

        with pytest.raises(
            ValueError,
            match="Sub-command names must be unique in a strict message command group. "
            "The following conflicts were found (?:aaa, dsaasd)|(?:dsaasd, aaa)",
        ):
            command_group.add_command(mock.Mock(names={"aaa", "dsaasd"}))

    def test_as_sub_command(self):
        async def mock_callback(ctx: tanjun.abc.MessageContext) -> None:
            raise NotImplementedError

        command_group = tanjun.MessageCommandGroup(mock.Mock(), "meow")

        result = command_group.as_sub_command("neco")(mock_callback)

        assert result.names == ["neco"]
        assert result._arg_names is not None

    def test_as_sub_command_with_optional_args(self):
        async def mock_callback(ctx: tanjun.abc.MessageContext) -> None:
            raise NotImplementedError

        command_group = tanjun.MessageCommandGroup(mock.Mock(), "meow")

        result = command_group.as_sub_command("neco", "nyan", validate_arg_keys=False)(mock_callback)

        assert result.names == ["neco", "nyan"]
        assert result._arg_names is None

    def test_as_sub_group(self):
        async def mock_callback(ctx: tanjun.abc.MessageContext) -> None:
            raise NotImplementedError

        command_group = tanjun.MessageCommandGroup(mock.Mock(), "meow")

        result = command_group.as_sub_group("n")(mock_callback)

        assert result.names == ["n"]
        assert result.is_strict is False
        assert result._arg_names is not None

    def test_as_sub_group_with_optional_args(self):
        async def mock_callback(ctx: tanjun.abc.MessageContext) -> None:
            raise NotImplementedError

        command_group = tanjun.MessageCommandGroup(mock.Mock(), "meow")

        result = command_group.as_sub_group("now", "viet", "namm", strict=True, validate_arg_keys=False)(mock_callback)

        assert result.names == ["now", "viet", "namm"]
        assert result.is_strict is True
        assert result._arg_names is None

    def test_remove_command(self):
        mock_command = mock.Mock()
        command_group = tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "a", "b").add_command(mock_command)

        result = command_group.remove_command(mock_command)

        assert result is command_group
        assert mock_command not in command_group.commands

    def test_remove_command_when_strict(self):
        mock_command = mock.Mock(names={"abba", "bba", "dadaba"})
        mock_other_command = mock.Mock(names={"dada"})
        command_group = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "a", "b", strict=True)
            .add_command(mock_command)
            .add_command(mock_other_command)
        )

        result = command_group.remove_command(mock_command)

        assert result is command_group
        assert mock_command not in command_group.commands
        assert command_group._names_to_commands == {"dada": mock_other_command}

    def test_with_command(self):
        add_command = mock.Mock()
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any], add_command=add_command, args=(mock.Mock(), "a", "b")
        )
        mock_command = mock.Mock()

        result = command.with_command(mock_command)

        assert result is mock_command
        add_command.assert_called_once_with(mock_command)

    def test_bind_client(self):
        mock_command_1 = mock.Mock()
        mock_command_2 = mock.Mock()
        mock_command_3 = mock.Mock()
        command = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "a", "b")
            .add_command(mock_command_1)
            .add_command(mock_command_2)
            .add_command(mock_command_3)
        )
        mock_client = mock.Mock()

        with mock.patch.object(tanjun.MessageCommand, "bind_client") as bind_client:
            command.bind_client(mock_client)

            bind_client.assert_called_once_with(mock_client)

        mock_command_1.bind_client.assert_called_once_with(mock_client)
        mock_command_2.bind_client.assert_called_once_with(mock_client)
        mock_command_3.bind_client.assert_called_once_with(mock_client)

    def test_bind_component(self):
        mock_command_1 = mock.Mock()
        mock_command_2 = mock.Mock()
        mock_command_3 = mock.Mock()
        command = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "a", "b")
            .add_command(mock_command_1)
            .add_command(mock_command_2)
            .add_command(mock_command_3)
        )
        mock_component = mock.Mock()

        with mock.patch.object(tanjun.MessageCommand, "bind_component") as bind_component:
            command.bind_component(mock_component)

            bind_component.assert_called_once_with(mock_component)

        mock_command_1.bind_component.assert_called_once_with(mock_component)
        mock_command_2.bind_component.assert_called_once_with(mock_component)
        mock_command_3.bind_component.assert_called_once_with(mock_component)

    def test_find_command(self):
        mock_command_1 = mock.Mock(names={"i am", "sexy", "jk", "unless"})
        mock_command_2 = mock.Mock(names={"i", "owo uwu", "no u"})
        command_group = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos")
            .add_command(mock_command_1)
            .add_command(mock.Mock(names={"ok boomer", "no u"}))
            .add_command(mock_command_2)
            .add_command(mock.Mock(names={"go home", "no u"}))
        )

        results = set(command_group.find_command("i am going home now"))

        assert results == {("i", mock_command_2), ("i am", mock_command_1)}

    def test_find_command_when_strict(self):
        mock_command_1 = mock.Mock(names={"ok", "no"})
        command_group = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos", strict=True)
            .add_command(mock_command_1)
            .add_command(mock.Mock(names={"boomer"}))
            .add_command(mock.Mock(names={"go"}))
        )

        results = list(command_group.find_command("ok i am going home now"))

        assert results == [("ok", mock_command_1)]

    def test_find_command_when_strict_and_unknown_name(self):
        command_group = (
            tanjun.MessageCommandGroup[typing.Any](mock.Mock(), "yee", "nsoosos", strict=True)
            .add_command(mock.Mock(names={"ok", "no"}))
            .add_command(mock.Mock(names={"boomer"}))
            .add_command(mock.Mock(names={"go"}))
        )

        results = list(command_group.find_command("nobob i am going home now"))

        assert results == []

    @pytest.mark.asyncio()
    async def test_execute_no_message_content(self):
        mock_context = mock.Mock()
        mock_context.message.content = None
        command_group = tanjun.MessageCommandGroup[typing.Any](mock.AsyncMock(), "hi", "nsoosos")

        with pytest.raises(ValueError, match="Cannot execute a command with a content-less message"):
            await command_group.execute(mock_context)

    @pytest.mark.asyncio()
    async def test_execute(self):
        mock_command_1 = mock.AsyncMock()
        mock_command_1.check_context.return_value = False
        mock_command_2 = mock.AsyncMock()
        mock_command_2.check_context.return_value = True
        mock_command_3 = mock.AsyncMock()
        mock_command_3.check_context.return_value = True
        mock_hooks = mock.Mock()
        mock_context = mock.Mock(content="baka desu-ga hi", triggering_name="go home")
        mock_attached_hooks = mock.Mock()
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any],
            find_command=mock.Mock(
                return_value=iter(
                    [("onii-chan>////<", mock_command_1), ("baka", mock_command_2), ("nope", mock_command_3)]
                )
            ),
            args=(mock.AsyncMock(), "a", "b"),
        ).set_hooks(mock_attached_hooks)

        await command.execute(mock_context, hooks={typing.cast(tanjun.abc.MessageHooks, mock_hooks)})

        mock_context.set_content.assert_called_once_with("desu-ga hi")
        mock_context.set_triggering_name.assert_called_once_with("go home baka")
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_3.check_context.assert_not_called()
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_called_once_with(mock_context, hooks={mock_hooks, mock_attached_hooks})
        mock_command_3.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_no_pass_through_hooks(self):
        mock_command_1 = mock.AsyncMock()
        mock_command_1.check_context.return_value = False
        mock_command_2 = mock.AsyncMock()
        mock_command_2.check_context.return_value = True
        mock_command_3 = mock.AsyncMock()
        mock_command_3.check_context.return_value = True
        mock_context = mock.Mock(content="baka desu-ga hi", triggering_name="go home")
        mock_attached_hooks = mock.Mock()
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any],
            find_command=mock.Mock(
                return_value=iter(
                    [("onii-chan>////<", mock_command_1), ("baka", mock_command_2), ("nope", mock_command_3)]
                )
            ),
            args=(mock.AsyncMock(), "a", "b"),
        ).set_hooks(mock_attached_hooks)

        await command.execute(mock_context)

        mock_context.set_content.assert_called_once_with("desu-ga hi")
        mock_context.set_triggering_name.assert_called_once_with("go home baka")
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_3.check_context.assert_not_called()
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_called_once_with(mock_context, hooks={mock_attached_hooks})
        mock_command_3.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_no_hooks(self):
        mock_command_1 = mock.AsyncMock()
        mock_command_1.check_context.return_value = False
        mock_command_2 = mock.AsyncMock()
        mock_command_2.check_context.return_value = True
        mock_command_3 = mock.AsyncMock()
        mock_command_3.check_context.return_value = True
        mock_context = mock.Mock(content="baka desu-ga hi", triggering_name="go home")
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any],
            find_command=mock.Mock(
                return_value=iter(
                    [("onii-chan>////<", mock_command_1), ("baka", mock_command_2), ("nope", mock_command_3)]
                )
            ),
            args=(mock.AsyncMock(), "a", "b"),
        )
        await command.execute(mock_context)

        mock_context.set_content.assert_called_once_with("desu-ga hi")
        mock_context.set_triggering_name.assert_called_once_with("go home baka")
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_3.check_context.assert_not_called()
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_called_once_with(mock_context, hooks=None)
        mock_command_3.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_falls_back_to_own_callback(self):
        mock_command_1 = mock.AsyncMock()
        mock_command_1.check_context.return_value = False
        mock_command_2 = mock.AsyncMock()
        mock_command_2.check_context.return_value = False
        mock_hooks = mock.Mock()
        mock_context = mock.Mock(content="baka desu-ga hi", triggering_name="go home")
        mock_attached_hooks = mock.Mock()
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any],
            find_command=mock.Mock(return_value=iter([("onii-chan>////<", mock_command_1), ("baka", mock_command_2)])),
            args=(mock.AsyncMock(), "a", "b"),
        ).set_hooks(mock_attached_hooks)

        with mock.patch.object(tanjun.commands.MessageCommand, "execute", new=mock.AsyncMock()) as mock_execute:
            await command.execute(mock_context, hooks={typing.cast(tanjun.abc.MessageHooks, mock_hooks)})

            mock_execute.assert_called_once_with(mock_context, hooks={mock_hooks, mock_attached_hooks})

        mock_context.set_content.assert_not_called()
        mock_context.set_triggering_name.assert_not_called()
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_falls_back_to_own_callback_no_pass_through_hooks(self):
        mock_command_1 = mock.AsyncMock()
        mock_command_1.check_context.return_value = False
        mock_command_2 = mock.AsyncMock()
        mock_command_2.check_context.return_value = False
        mock_context = mock.Mock(content="baka desu-ga hi", triggering_name="go home")
        mock_attached_hooks = mock.Mock()
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any],
            find_command=mock.Mock(return_value=iter([("onii-chan>////<", mock_command_1), ("baka", mock_command_2)])),
            args=(mock.AsyncMock(), "a", "b"),
        ).set_hooks(mock_attached_hooks)

        with mock.patch.object(tanjun.commands.MessageCommand, "execute", new=mock.AsyncMock()) as mock_execute:
            await command.execute(mock_context)

            mock_execute.assert_called_once_with(mock_context, hooks={mock_attached_hooks})

        mock_context.set_content.assert_not_called()
        mock_context.set_triggering_name.assert_not_called()
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_falls_back_to_own_callback_no_hooks(self):
        mock_command_1 = mock.AsyncMock()
        mock_command_1.check_context.return_value = False
        mock_command_2 = mock.AsyncMock()
        mock_command_2.check_context.return_value = False
        mock_context = mock.Mock(content="baka desu-ga hi", triggering_name="go home")
        command = stub_class(
            tanjun.MessageCommandGroup[typing.Any],
            find_command=mock.Mock(return_value=iter([("onii-chan>////<", mock_command_1), ("baka", mock_command_2)])),
            args=(mock.AsyncMock(), "a", "b"),
        )

        with mock.patch.object(tanjun.commands.MessageCommand, "execute", new=mock.AsyncMock()) as mock_execute:
            await command.execute(mock_context)

            mock_execute.assert_called_once_with(mock_context, hooks=None)

        mock_context.set_content.assert_not_called()
        mock_context.set_triggering_name.assert_not_called()
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_not_called()
