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

import typing
from unittest import mock

import hikari
import pytest

import tanjun
from tanjun import _internal


def test_as_message_menu():
    mock_callback = mock.Mock()

    command = tanjun.as_message_menu(
        "eat",
        always_defer=True,
        default_member_permissions=hikari.Permissions(43123),
        default_to_ephemeral=False,
        dm_enabled=False,
        is_global=False,
    )(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.type is hikari.CommandType.MESSAGE
    assert command.name == "eat"
    assert command._always_defer is True
    assert command.default_member_permissions == hikari.Permissions(43123)
    assert command.defaults_to_ephemeral is False
    assert command.is_dm_enabled is False
    assert command.is_global is False
    assert command.callback is mock_callback
    assert command.wrapped_command is None


def test_as_message_menu_with_defaults():
    mock_callback = mock.Mock()

    command = tanjun.as_message_menu("yeet")(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.callback is mock_callback
    assert command.type is hikari.CommandType.MESSAGE
    assert command.name == "yeet"
    assert command._always_defer is False
    assert command.default_member_permissions is None
    assert command.defaults_to_ephemeral is None
    assert command.is_dm_enabled is None
    assert command.is_global is True
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
def test_as_message_menu_when_wrapping_command(
    other_command: typing.Union[
        tanjun.SlashCommand[typing.Any],
        tanjun.MessageCommand[typing.Any],
        tanjun.MenuCommand[typing.Any, typing.Any],
    ]
):
    command = tanjun.as_message_menu(
        "c",
        always_defer=False,
        default_member_permissions=hikari.Permissions(543123),
        default_to_ephemeral=True,
        dm_enabled=False,
        is_global=True,
    )(other_command)

    assert command._always_defer is False
    assert command.default_member_permissions == 543123
    assert command.defaults_to_ephemeral is True
    assert command.is_dm_enabled is False
    assert command.is_global is True
    assert command.type is hikari.CommandType.MESSAGE
    assert command.callback is other_command.callback
    assert command.wrapped_command is other_command
    assert isinstance(command, tanjun.MenuCommand)


def test_as_user_menu():
    mock_callback = mock.Mock()

    command = tanjun.as_user_menu(
        "uoy",
        always_defer=True,
        default_member_permissions=hikari.Permissions(49494),
        default_to_ephemeral=False,
        dm_enabled=False,
        is_global=False,
    )(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.callback is mock_callback
    assert command.type is hikari.CommandType.USER
    assert command.name == "uoy"
    assert command._always_defer is True
    assert command.default_member_permissions == hikari.Permissions(49494)
    assert command.defaults_to_ephemeral is False
    assert command.is_dm_enabled is False
    assert command.is_global is False
    assert command.callback is mock_callback
    assert command.wrapped_command is None


def test_as_user_menu_with_defaults():
    mock_callback = mock.Mock()

    command = tanjun.as_user_menu("you")(mock_callback)

    assert isinstance(command, tanjun.MenuCommand)
    assert command.type is hikari.CommandType.USER
    assert command.name == "you"
    assert command._always_defer is False
    assert command.default_member_permissions is None
    assert command.defaults_to_ephemeral is None
    assert command.is_dm_enabled is None
    assert command.is_global is True
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
def test_as_user_menu_when_wrapping_command(
    other_command: typing.Union[
        tanjun.SlashCommand[typing.Any],
        tanjun.MessageCommand[typing.Any],
        tanjun.MenuCommand[typing.Any, typing.Any],
    ]
):
    command = tanjun.as_user_menu(
        "c",
        always_defer=True,
        default_member_permissions=hikari.Permissions(4212312),
        default_to_ephemeral=False,
        dm_enabled=True,
        is_global=False,
    )(other_command)

    assert command._always_defer is True
    assert command.default_member_permissions == 4212312
    assert command.defaults_to_ephemeral is False
    assert command.is_dm_enabled is True
    assert command.is_global is False
    assert command.type is hikari.CommandType.USER
    assert command.callback is other_command.callback
    assert command.wrapped_command is other_command
    assert isinstance(command, tanjun.MenuCommand)


class TestMenuCommand:
    def test__init__when_no_names_provided(self):
        with pytest.raises(RuntimeError, match="No default name given"):
            tanjun.commands.MenuCommand(mock.AsyncMock(), hikari.CommandType.USER, {"id": "idea"})

    def test__init__when_name_too_long(self):
        with pytest.raises(
            ValueError,
            match="Name must be less than or equal to 32 characters in length",
        ):
            tanjun.commands.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "x" * 33)

    def test__init__when_localised_name_too_long(self):
        with pytest.raises(
            ValueError,
            match="Name must be less than or equal to 32 characters in length",
        ):
            tanjun.commands.MenuCommand(
                mock.Mock(),
                hikari.CommandType.MESSAGE,
                {hikari.Locale.BG: "year", hikari.Locale.DA: "y" * 33, hikari.Locale.DE: "ein", "default": "meow"},
            )

    def test__init__when_localised_default_name_too_long(self):
        with pytest.raises(
            ValueError,
            match="Name must be less than or equal to 32 characters in length",
        ):
            tanjun.commands.MenuCommand(
                mock.Mock(),
                hikari.CommandType.MESSAGE,
                {hikari.Locale.BG: "year", hikari.Locale.DE: "ein", "default": "meow" * 9},
            )

    def test__init__when_name_too_short(self):
        with pytest.raises(
            ValueError,
            match="Name must be greater than or equal to 1 characters in length",
        ):
            tanjun.commands.MenuCommand(mock.Mock(), hikari.CommandType.MESSAGE, "")

    def test__init__when_localised_name_too_short(self):
        with pytest.raises(
            ValueError,
            match="Name must be greater than or equal to 1 characters in length",
        ):
            tanjun.commands.MenuCommand(
                mock.Mock(),
                hikari.CommandType.MESSAGE,
                {hikari.Locale.BG: "", hikari.Locale.DA: "damn", hikari.Locale.HR: "beep"},
            )

    def test__init__when_localised_default_name_too_short(self):
        with pytest.raises(
            ValueError,
            match="Name must be greater than or equal to 1 characters in length",
        ):
            tanjun.commands.MenuCommand(
                mock.Mock(),
                hikari.CommandType.MESSAGE,
                {hikari.Locale.EN_GB: "great scott", "default": "", hikari.Locale.EL: "beep", hikari.Locale.DA: "boop"},
            )

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
            tanjun.MessageCommand[tanjun.abc.CommandCallbackSig],
            tanjun.MenuCommand[typing.Any, typing.Any],
        ],
    ):
        assert tanjun.MenuCommand(inner_command, hikari.CommandType.MESSAGE, "woow").callback is inner_command.callback

    @pytest.mark.asyncio()
    async def test_call_dunder_method(self):
        mock_callback: typing.Any = mock.AsyncMock()
        command = tanjun.MenuCommand(mock_callback, hikari.CommandType.MESSAGE, "a")

        await command(123, 321, "ea", b=32)

        mock_callback.assert_awaited_once_with(123, 321, "ea", b=32)

    def test_callback_property(self):
        mock_callback = mock.Mock()
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock_callback, hikari.CommandType.MESSAGE, "a")

        assert command.callback is mock_callback

    def test_default_member_permissions_property(self):
        mock_callback = mock.Mock()
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock_callback, hikari.CommandType.MESSAGE, "a", default_member_permissions=hikari.Permissions(6541231)
        )

        assert command.default_member_permissions == 6541231

    def test_defaults_to_ephemeral_property(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.MESSAGE, "a", default_to_ephemeral=True
        )

        assert command.defaults_to_ephemeral is True

    def test_defaults_to_ephemeral_property_when_unset(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "a")

        assert command.defaults_to_ephemeral is None

    def test_is_dm_enabled_property(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.MESSAGE, "a", dm_enabled=False
        )

        assert command.is_dm_enabled is False

    def test_is_global_property(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.MESSAGE, "a", is_global=False
        )

        assert command.is_global is False

    def test_is_global_property_when_default(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "a")

        assert command.is_global is True

    def test_name_properties(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "uwu")

        assert command.name == "uwu"
        assert command.name_localisations == {}
        assert command._names.id is None

    def test_name_properties_when_localised(self):
        command = tanjun.MenuCommand(
            mock.AsyncMock(),
            hikari.CommandType.USER,
            {
                hikari.Locale.BG: "hi",
                hikari.Locale.CS: "Nay",
                "default": "nay",
                "id": "meow",
                hikari.Locale.PT_BR: "yeet",
            },
        )

        assert command.name == "nay"
        assert command.name_localisations == {
            hikari.Locale.BG: "hi",
            hikari.Locale.CS: "Nay",
            hikari.Locale.PT_BR: "yeet",
        }
        assert command._names.id == "meow"

    def test_name_properties_when_localised_implicit_default(self):
        command = tanjun.MenuCommand(
            mock.AsyncMock(), hikari.CommandType.MESSAGE, {hikari.Locale.JA: "Rei", hikari.Locale.DE: "Meow"}
        )

        assert command.name == "Rei"
        assert command.name_localisations == {hikari.Locale.JA: "Rei", hikari.Locale.DE: "Meow"}
        assert command._names.id is None

    def test_name_properties_when_dict_without_localisations(self):
        command = tanjun.MenuCommand(
            mock.AsyncMock(), hikari.CommandType.MESSAGE, {"id": "shinjis_man", "default": "no papa"}
        )

        assert command.name == "no papa"
        assert command.name_localisations == {}
        assert command._names.id == "shinjis_man"

    def test_tracked_command_property(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "uwu")

        assert command.tracked_command is None

    def test_tracked_command_id_property(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "uwu")

        assert command.tracked_command_id is None

    @pytest.mark.parametrize("command_type", [hikari.CommandType.MESSAGE, hikari.CommandType.USER])
    def test_type_property(self, command_type: hikari.CommandType):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), command_type, "uwu")  # type: ignore

        assert command.type is command_type

    def test_build(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.USER, "owo")

        builder = command.build()

        assert builder.name == "owo"
        assert builder.name_localizations == {}
        assert builder.type is hikari.CommandType.USER
        assert builder.id is hikari.UNDEFINED
        assert builder.default_member_permissions is hikari.UNDEFINED
        assert builder.is_dm_enabled is hikari.UNDEFINED

    def test_build_when_all_fields_set(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(),
            hikari.CommandType.MESSAGE,
            "pat",
            default_member_permissions=hikari.Permissions(4123),
            dm_enabled=False,
        ).bind_component(
            mock.Mock(default_app_cmd_permissions=hikari.Permissions(54123123), dms_enabled_for_app_cmds=True)
        )

        builder = command.build(
            component=mock.Mock(default_app_cmd_permissions=hikari.Permissions(341123), dms_enabled_for_app_cmds=True)
        )

        assert builder.name == "pat"
        assert builder.type is hikari.CommandType.MESSAGE
        assert builder.id is hikari.UNDEFINED
        assert builder.default_member_permissions == hikari.Permissions(4123)
        assert builder.is_dm_enabled is False
        assert builder.name_localizations == {}

    def test_build_with_localised_fields(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(),
            hikari.CommandType.USER,
            {hikari.Locale.EN_GB: "yeet", hikari.Locale.FI: "beat", "default": "shinji", hikari.Locale.JA: "Ayanami"},
        )

        builder = command.build()

        assert builder.name == "shinji"
        assert builder.name_localizations == {
            hikari.Locale.EN_GB: "yeet",
            hikari.Locale.FI: "beat",
            hikari.Locale.JA: "Ayanami",
        }

    def test_build_with_localised_fields_and_implicit_default(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(),
            hikari.CommandType.USER,
            {
                hikari.Locale.EN_GB: "yeet",
                hikari.Locale.FI: "beat",
                hikari.Locale.DA: "drum",
                hikari.Locale.JA: "Ayanami",
            },
        )

        builder = command.build()

        assert builder.name == "yeet"
        assert builder.name_localizations == {
            hikari.Locale.EN_GB: "yeet",
            hikari.Locale.FI: "beat",
            hikari.Locale.DA: "drum",
            hikari.Locale.JA: "Ayanami",
        }

    def test_build_with_bound_component_field_inheritance(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.USER, "owo"
        ).bind_component(
            mock.Mock(default_app_cmd_permissions=hikari.Permissions(65412312), dms_enabled_for_app_cmds=True)
        )

        builder = command.build()

        assert builder.name == "owo"
        assert builder.type is hikari.CommandType.USER
        assert builder.id is hikari.UNDEFINED
        assert builder.default_member_permissions == 65412312
        assert builder.is_dm_enabled is True

    def test_build_with_passed_component_field_inheritance(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.USER, "owo"
        ).bind_component(
            mock.Mock(default_app_cmd_permissions=hikari.Permissions(65412312), dms_enabled_for_app_cmds=True)
        )

        builder = command.build(
            component=mock.Mock(
                default_app_cmd_permissions=hikari.Permissions(561234123), dms_enabled_for_app_cmds=False
            )
        )

        assert builder.name == "owo"
        assert builder.type is hikari.CommandType.USER
        assert builder.id is hikari.UNDEFINED
        assert builder.default_member_permissions == 561234123
        assert builder.is_dm_enabled is False

    def test_set_tracked_command(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "pat")
        mock_command = mock.Mock(hikari.ContextMenuCommand)

        result = command.set_tracked_command(mock_command)

        assert result is command
        assert command.tracked_command is mock_command
        assert command.tracked_command_id is mock_command.id

    def test_set_ephemeral_default(self):
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "pat")

        result = command.set_ephemeral_default(True)

        assert result is command
        assert command.defaults_to_ephemeral is True

    @pytest.mark.asyncio()
    async def test_check_context(self):
        mock_callback = mock.Mock()
        mock_other_callback = mock.Mock()
        mock_context = mock.Mock()

        command = (
            tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.USER, "pat")
            .add_check(mock_callback)
            .add_check(mock_other_callback)
        )

        with mock.patch.object(_internal, "gather_checks", new=mock.AsyncMock()) as gather_checks:
            result = await command.check_context(mock_context)

            gather_checks.assert_awaited_once_with(mock_context, [mock_callback, mock_other_callback])

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
        command = tanjun.MenuCommand[typing.Any, typing.Any](mock.Mock(), hikari.CommandType.MESSAGE, "pat")
        mock_component = mock.Mock()

        command.load_into_component(mock_component)

        mock_component.add_menu_command.assert_called_once_with(command)

    def test_load_into_component_when_wrapped_command(self):
        mock_other_command = mock.Mock()
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.MESSAGE, "pat", _wrapped_command=mock_other_command
        )
        mock_component = mock.Mock()

        command.load_into_component(mock_component)

        mock_component.add_menu_command.assert_called_once_with(command)
        mock_other_command.load_into_component.assert_not_called()

    def test_load_into_component_when_wrapped_command_is_loader(self):
        mock_other_command = mock.Mock(tanjun.components.AbstractComponentLoader)
        command = tanjun.MenuCommand[typing.Any, typing.Any](
            mock.Mock(), hikari.CommandType.MESSAGE, "pat", _wrapped_command=mock_other_command
        )
        mock_component = mock.Mock()

        command.load_into_component(mock_component)

        mock_component.add_menu_command.assert_called_once_with(command)
        mock_other_command.load_into_component.assert_called_once_with(mock_component)
