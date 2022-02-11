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

import re
import typing
from unittest import mock

import hikari
import pytest

import tanjun


def test_as_message_menu():
    mock_callback = mock.Mock()

    command = tanjun.as_message_menu("eat", always_defer=True, default_to_ephemeral=False, is_global=False)(
        mock_callback
    )

    assert isinstance(command, tanjun.MenuCommand)
    assert command.type is hikari.CommandType.MESSAGE
    assert command.name == "eat"
    assert command._always_defer is True
    assert command.defaults_to_ephemeral is False
    assert command.is_global is False
    assert command.callback is mock_callback
    assert command._wrapped_command is None


def test_as_message_menu_with_defaults():
    mock_callback = mock.Mock()

    command = tanjun.as_message_menu("yeet")(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.type is hikari.CommandType.MESSAGE
    assert command.name == "yeet"
    assert command._always_defer is False
    assert command.defaults_to_ephemeral is None
    assert command.is_global is True
    assert command.callback is mock_callback
    assert command._wrapped_command is None


@pytest.mark.parametrize(
    "other_command",
    [
        tanjun.SlashCommand(mock.Mock(), "e", "a"),
        tanjun.MessageCommand(mock.Mock(), "b"),
        tanjun.MessageCommandGroup(mock.Mock(), "b"),
        tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "a"),
    ],
)
def test_as_message_menu_when_wrapping_command(
    other_command: typing.Union[
        tanjun.SlashCommand[typing.Any],
        tanjun.MessageCommand[typing.Any],
        tanjun.MessageCommandGroup[typing.Any],
        tanjun.MenuCommand[typing.Any, typing.Any],
    ]
):
    command = tanjun.as_message_menu("c")(other_command)

    assert command.type is hikari.CommandType.MESSAGE
    assert command.callback is other_command.callback
    assert command._wrapped_command is other_command
    assert isinstance(command, tanjun.MenuCommand)


def test_as_user_menu():
    mock_callback = mock.Mock()

    command = tanjun.as_user_menu("uoy", always_defer=True, default_to_ephemeral=False, is_global=False)(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.type is hikari.CommandType.USER
    assert command.name == "uoy"
    assert command._always_defer is True
    assert command.defaults_to_ephemeral is False
    assert command.is_global is False
    assert command.callback is mock_callback
    assert command._wrapped_command is None


def test_as_user_menu_with_defaults():
    mock_callback = mock.Mock()

    command = tanjun.as_user_menu("you")(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.type is hikari.CommandType.USER
    assert command.name == "you"
    assert command._always_defer is False
    assert command.defaults_to_ephemeral is None
    assert command.is_global is True
    assert command.callback is mock_callback
    assert command._wrapped_command is None


@pytest.mark.parametrize(
    "other_command",
    [
        tanjun.SlashCommand(mock.Mock(), "e", "a"),
        tanjun.MessageCommand(mock.Mock(), "b"),
        tanjun.MessageCommandGroup(mock.Mock(), "b"),
        tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "a"),
    ],
)
def test_as_user_menu_when_wrapping_command(
    other_command: typing.Union[
        tanjun.SlashCommand[typing.Any],
        tanjun.MessageCommand[typing.Any],
        tanjun.MessageCommandGroup[typing.Any],
        tanjun.MenuCommand[typing.Any, typing.Any],
    ]
):
    command = tanjun.as_user_menu("c")(other_command)

    assert command.type is hikari.CommandType.USER
    assert command.callback is other_command.callback
    assert command._wrapped_command is other_command
    assert isinstance(command, tanjun.MenuCommand)


_INVALID_NAMES = ["a" * 33, "", "'#'#42123"]


class TestMenuCommand:
    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test__init__with_invalid_name(self, name: str):
        with pytest.raises(
            ValueError,
            match=f"Invalid name provided, {name!r} doesn't match the required regex " + re.escape(r"`^\w{1,32}$`"),
        ):
            tanjun.commands.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, name)

    def test__init__when_name_isnt_lowercase(self):
        with pytest.raises(ValueError, match="Invalid name provided, 'EAttststs' must be lowercase"):
            tanjun.commands.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "EAttststs")

    @pytest.mark.parametrize(
        "inner_command",
        [
            tanjun.SlashCommand(mock.Mock(), "a", "b"),
            tanjun.MessageCommand(mock.Mock(), "a"),
            tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "e"),
        ],
    )
    def test___init___when_command_object(
        self,
        inner_command: typing.Union[
            tanjun.SlashCommand[tanjun.abc.CommandCallbackSig], tanjun.MessageCommand[tanjun.abc.CommandCallbackSig]
        ],
    ):
        assert tanjun.MenuCommand(inner_command, hikari.CommandType.MESSAGE, "woow").callback is inner_command.callback

    def test_callback_property(self):
        mock_callback = mock.Mock()
        command = tanjun.MenuCommand(mock_callback, hikari.CommandType.MESSAGE, "a")

        assert command.callback is mock_callback

    def test_defaults_to_ephemeral_property(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "a", default_to_ephemeral=True)

        assert command.defaults_to_ephemeral is True

    def test_defaults_to_ephemeral_property_when_unset(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "a")

        assert command.defaults_to_ephemeral is None

    def test_is_global_property(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "a", is_global=False)

        assert command.is_global is False

    def test_is_global_property_when_default(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "a")

        assert command.is_global is True

    def test_name_property(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "uwu")

        assert command.name == "uwu"

    def test_tracked_command_property(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "uwu")

        assert command.tracked_command is None

    def test_tracked_command_id_property(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "uwu")

        assert command.tracked_command_id is None

    @pytest.mark.parametrize("command_type", [hikari.CommandType.MESSAGE, hikari.CommandType.USER])
    def test_type_property(self, command_type: hikari.CommandType):
        command = tanjun.MenuCommand(mock.Mock(), command_type, "uwu")  # type: ignore

        assert command.type is command_type

    def test_build(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.USER, "owo")

        builder = command.build()

        assert builder.name == "owo"
        assert builder.type is hikari.CommandType.USER
        assert builder.id is hikari.UNDEFINED
        assert builder.default_permission is True

    def test_build_when_all_fields_set(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "pat", default_permission=False)

        builder = command.build()

        assert builder.name == "pat"
        assert builder.type is hikari.CommandType.MESSAGE
        assert builder.id is hikari.UNDEFINED
        assert builder.default_permission is False

    def test_set_tracked_command(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "pat")
        mock_command = mock.Mock(hikari.ContextMenuCommand)

        result = command.set_tracked_command(mock_command)

        assert result is command
        assert command.tracked_command is mock_command
        assert command.tracked_command_id is mock_command.id

    def test_set_ephemeral_default(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "pat")

        result = command.set_ephemeral_default(True)

        assert result is command
        assert command.defaults_to_ephemeral is True

    @pytest.mark.asyncio()
    async def test_check_context(self):
        mock_callback = mock.Mock()
        mock_other_callback = mock.Mock()
        mock_context = mock.Mock()
        mock_checks = [mock.Mock(), mock.Mock()]

        with mock.patch.object(tanjun.checks, "InjectableCheck", side_effect=mock_checks.copy()) as injectable_check:
            command = (
                tanjun.MenuCommand(mock.Mock(), hikari.CommandType.USER, "pat")
                .add_check(mock_callback)
                .add_check(mock_other_callback)
            )

            injectable_check.call_args_list == [mock.call(mock_callback), mock.call(mock_other_callback)]

        with mock.patch.object(tanjun.utilities, "gather_checks", new=mock.AsyncMock()) as gather_checks:
            result = await command.check_context(mock_context)

            gather_checks.assert_awaited_once_with(mock_context, mock_checks)

        assert result is gather_checks.return_value
        mock_context.set_command.assert_has_calls([mock.call(command), mock.call(None)])

    @pytest.mark.skip(reason="TODO")
    def test_copy(self):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_execute(self):
        ...

    def test_load_into_component(self):
        command = tanjun.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "pat")
        mock_component = mock.Mock()

        command.load_into_component(mock_component)

        mock_component.add_menu_command.assert_called_once_with(command)

    def test_load_into_component_when_wrapped_command(self):
        mock_other_command = mock.Mock()
        command = tanjun.MenuCommand(
            mock.Mock(), hikari.CommandType.MESSAGE, "pat", _wrapped_command=mock_other_command
        )
        mock_component = mock.Mock()

        command.load_into_component(mock_component)

        mock_component.add_menu_command.assert_called_once_with(command)
        mock_other_command.load_into_component.assert_not_called()

    def test_load_into_component_when_wrapped_command_is_loader(self):
        mock_other_command = mock.Mock(tanjun.components.AbstractComponentLoader)
        command = tanjun.MenuCommand(
            mock.Mock(), hikari.CommandType.MESSAGE, "pat", _wrapped_command=mock_other_command
        )
        mock_component = mock.Mock()

        command.load_into_component(mock_component)

        mock_component.add_menu_command.assert_called_once_with(command)
        mock_other_command.load_into_component.assert_called_once_with(mock_component)
