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
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import re
import types
import typing
import warnings
from unittest import mock

import hikari
import pytest

import tanjun

_T = typing.TypeVar("_T")


def stub_class(cls: type[_T], /, **namespace: typing.Any) -> type[_T]:
    namespace["__slots__"] = ()

    for name in getattr(cls, "__abstractmethods__", None) or ():
        if name not in namespace:
            namespace[name] = mock.MagicMock()

    name = origin.__name__ if (origin := getattr(cls, "__origin__", None)) else cls.__name__
    new_cls = types.new_class(name, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)


class Test_LoadableInjector:
    def test_make_method_type(self):
        mock_component = mock.Mock()
        mock_callback = mock.Mock()

        def callback(self: typing.Any):
            return mock_callback(self)

        loadable = tanjun.commands._LoadableInjector(callback)

        loadable.make_method_type(mock_component)
        result = loadable.callback()

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(mock_component)

    def test_make_method_type_when_already_method_type(self):
        class MockLoadableInjector(tanjun.commands._LoadableInjector):
            overwrite_callback = mock.Mock()

        loadable = MockLoadableInjector(mock.Mock(types.MethodType))

        with pytest.raises(ValueError, match="Callback is already a method type"):
            loadable.make_method_type(mock.Mock())


class TestPartialCommand:
    @pytest.fixture()
    def command(self) -> tanjun.commands.PartialCommand[typing.Any]:
        fields: dict[str, typing.Any] = {}
        for name in tanjun.commands.PartialCommand.__abstractmethods__:
            fields[name] = mock.MagicMock()

        return types.new_class(
            "PartialCommand", (tanjun.commands.PartialCommand[typing.Any],), exec_body=lambda body: body.update(fields)
        )()

    def test_metadata_property(self, command: tanjun.commands.PartialCommand[typing.Any]):
        assert command.metadata is command._metadata

    def test_needs_injector_when_any_true(self, command: tanjun.commands.PartialCommand[typing.Any]):
        command._checks = [mock.Mock(needs_injector=False), mock.Mock(needs_injector=True)]
        assert command.needs_injector is True

    def test_needs_injector_when_all_true(self, command: tanjun.commands.PartialCommand[typing.Any]):
        command._checks = [mock.Mock(needs_injector=True), mock.Mock(needs_injector=True)]
        assert command.needs_injector is True

    def test_needs_injector_when_all_false(self, command: tanjun.commands.PartialCommand[typing.Any]):
        command._checks = [mock.Mock(needs_injector=False), mock.Mock(needs_injector=False)]
        assert command.needs_injector is False

    def test_needs_injector_when_empty(self, command: tanjun.commands.PartialCommand[typing.Any]):
        assert command.needs_injector is False

    def test_copy(self, command: tanjun.commands.PartialCommand[typing.Any]):
        mock_check = mock.Mock()
        command._checks = [mock_check]
        command._hooks = mock.Mock()
        mock_metadata = mock.Mock()
        command._metadata = mock_metadata

        new_command = command.copy()

        assert new_command is not command
        new_command._checks == [mock_check.copy.return_value]
        assert new_command._hooks is command._hooks.copy.return_value
        assert new_command._metadata is mock_metadata.copy.return_value

    def test_set_hooks(self, command: tanjun.commands.PartialCommand[typing.Any]):
        mock_hooks = mock.Mock()

        assert command.set_hooks(mock_hooks) is command
        assert command.hooks is mock_hooks

    def test_add_check(self, command: tanjun.commands.PartialCommand[typing.Any]):
        mock_check = mock.Mock()

        assert command.add_check(mock_check) is command

        assert len(command._checks) == 1
        check = next(iter(command._checks))
        assert isinstance(check, tanjun.checks.InjectableCheck)
        assert check.callback is mock_check
        assert command.checks == (mock_check,)

    def test_add_check_when_already_present(self, command: tanjun.commands.PartialCommand[typing.Any]):
        mock_check = mock.Mock()

        assert command.add_check(mock_check).add_check(mock_check) is command

        assert list(command.checks).count(mock_check) == 1

    def test_remove_check(self, command: tanjun.commands.PartialCommand[typing.Any]):
        def mock_check() -> bool:
            raise NotImplementedError

        command._checks = [tanjun.checks.InjectableCheck(mock_check)]

        result = command.remove_check(mock_check)

        assert result is command
        assert command.checks == ()

    def test_with_check(self, command: tanjun.commands.PartialCommand[typing.Any]):
        def mock_check() -> bool:
            raise NotImplementedError

        assert command.with_check(mock_check) is mock_check

        assert len(command._checks) == 1
        check = next(iter(command._checks))
        assert isinstance(check, tanjun.commands._LoadableInjector)
        assert check.callback is mock_check
        assert command.checks == (mock_check,)

    def test_with_check_when_already_present(self, command: tanjun.commands.PartialCommand[typing.Any]):
        def mock_check() -> bool:
            raise NotImplementedError

        command.add_check(mock_check).with_check(mock_check)
        assert command.with_check(mock_check) is mock_check

        assert list(command.checks).count(mock_check) == 1

    def test_bind_client(self, command: tanjun.commands.PartialCommand[typing.Any]):
        command.bind_client(mock.Mock())

    def test_bind_component(self, command: tanjun.commands.PartialCommand[typing.Any]):
        mock_component = mock.Mock()

        command.bind_component(mock_component)

        assert command.component is mock_component

    def test_load_into_component(self, command: tanjun.commands.PartialCommand[typing.Any]):
        mock_check_1 = mock.MagicMock(tanjun.commands._LoadableInjector)
        mock_check_2 = mock.Mock()
        mock_check_3 = mock.MagicMock(tanjun.commands._LoadableInjector)
        mock_component = mock.Mock()
        command._checks = [mock_check_1, mock_check_2, mock_check_3]

        result = command.load_into_component(mock_component)

        assert result is None
        mock_check_1.make_method_type.assert_called_once_with(mock_component)
        mock_check_2.make_method_type.assert_not_called()
        mock_check_3.make_method_type.assert_called_once_with(mock_component)


def test_slash_command_group():
    command = tanjun.slash_command_group(
        "a_name", "very", default_permission=False, default_to_ephemeral=True, is_global=False
    )

    assert command.name == "a_name"
    assert command.description == "very"
    assert command.build().default_permission is False
    assert command.is_global is False
    assert command.defaults_to_ephemeral is True
    assert isinstance(command, tanjun.SlashCommandGroup)


def test_slash_command_group_with_default():
    command = tanjun.slash_command_group("a_name", "very")

    assert command.tracked_command_id is None
    assert command.build().default_permission is True
    assert command.defaults_to_ephemeral is None
    assert command.is_global is True
    assert isinstance(command, tanjun.SlashCommandGroup)


def test_as_slash_command():
    mock_callback = mock.Mock()

    command = tanjun.as_slash_command(
        "a_very",
        "cool name",
        default_permission=False,
        default_to_ephemeral=True,
        is_global=False,
        sort_options=False,
    )(mock_callback)

    assert command.name == "a_very"
    assert command.description == "cool name"
    assert command.build().default_permission is hikari.UNDEFINED
    assert command.defaults_to_ephemeral is True
    assert command.is_global is False
    assert command._builder._sort_options is False
    assert isinstance(command, tanjun.SlashCommand)


def test_as_slash_command_with_defaults():
    mock_callback = mock.Mock()

    command = tanjun.as_slash_command("a_very", "cool name")(mock_callback)

    assert command.tracked_command_id is None
    assert command.build().default_permission is hikari.UNDEFINED
    assert command.defaults_to_ephemeral is None
    assert command.is_global is True
    assert command._builder._sort_options is True
    assert isinstance(command, tanjun.SlashCommand)


def test_with_str_slash_option():
    mock_command = mock.MagicMock()
    mock_converter = mock.Mock()

    result = tanjun.with_str_slash_option(
        "a_name",
        "a_value",
        choices={"Go home": "ok", "no": "u"},
        converters=[mock_converter],
        default="ANY",
        pass_as_kwarg=False,
    )(mock_command)

    assert result is mock_command.add_str_option.return_value
    mock_command.add_str_option.assert_called_once_with(
        "a_name",
        "a_value",
        default="ANY",
        choices={"Go home": "ok", "no": "u"},
        converters=[mock_converter],
        pass_as_kwarg=False,
        _stack_level=1,
    )


def test_with_str_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_str_slash_option("a_name", "a_value")(mock_command)

    assert result is mock_command.add_str_option.return_value
    mock_command.add_str_option.assert_called_once_with(
        "a_name",
        "a_value",
        default=tanjun.commands._UNDEFINED_DEFAULT,
        choices=None,
        converters=(),
        pass_as_kwarg=True,
        _stack_level=1,
    )


def test_with_int_slash_option():
    mock_command = mock.MagicMock()
    mock_converter = mock.Mock()

    result = tanjun.with_int_slash_option(
        "im_con", "con man", choices={"a": 123}, converters=[mock_converter], default=321123, pass_as_kwarg=False
    )(mock_command)

    assert result is mock_command.add_int_option.return_value
    mock_command.add_int_option.assert_called_once_with(
        "im_con",
        "con man",
        choices={"a": 123},
        converters=[mock_converter],
        default=321123,
        pass_as_kwarg=False,
        _stack_level=1,
    )


def test_with_int_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_int_slash_option("im_con", "con man")(mock_command)

    assert result is mock_command.add_int_option.return_value
    mock_command.add_int_option.assert_called_once_with(
        "im_con",
        "con man",
        choices=None,
        converters=(),
        default=tanjun.commands._UNDEFINED_DEFAULT,
        pass_as_kwarg=True,
        _stack_level=1,
    )


def test_with_float_slash_option():
    mock_command = mock.MagicMock()
    mock_converter = mock.Mock()

    result = tanjun.with_float_slash_option(
        "di",
        "ni",
        always_float=False,
        choices={"no": 3.14, "bye": 2.33},
        converters=[mock_converter],
        default=21.321,
        pass_as_kwarg=False,
    )(mock_command)

    assert result is mock_command.add_float_option.return_value
    mock_command.add_float_option.assert_called_once_with(
        "di",
        "ni",
        always_float=False,
        default=21.321,
        choices={"no": 3.14, "bye": 2.33},
        converters=[mock_converter],
        pass_as_kwarg=False,
        _stack_level=1,
    )


def test_with_float_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_float_slash_option("hi", "bye")(mock_command)

    assert result is mock_command.add_float_option.return_value
    mock_command.add_float_option.assert_called_once_with(
        "hi",
        "bye",
        always_float=True,
        default=tanjun.commands._UNDEFINED_DEFAULT,
        choices=None,
        converters=(),
        pass_as_kwarg=True,
        _stack_level=1,
    )


def test_with_bool_slash_option():
    mock_command = mock.MagicMock()

    result = tanjun.with_bool_slash_option("bool", "bool me man", default=False, pass_as_kwarg=False)(mock_command)

    assert result is mock_command.add_bool_option.return_value
    mock_command.add_bool_option.assert_called_once_with("bool", "bool me man", default=False, pass_as_kwarg=False)


def test_with_bool_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_bool_slash_option("bool", "bool me man")(mock_command)

    assert result is mock_command.add_bool_option.return_value
    mock_command.add_bool_option.assert_called_once_with(
        "bool", "bool me man", default=tanjun.commands._UNDEFINED_DEFAULT, pass_as_kwarg=True
    )


def test_with_user_slash_option():
    mock_command = mock.MagicMock()

    result = tanjun.with_user_slash_option("victim", "who're we getting next?", default=123321, pass_as_kwarg=False)(
        mock_command
    )

    assert result is mock_command.add_user_option.return_value
    mock_command.add_user_option.assert_called_once_with(
        "victim", "who're we getting next?", default=123321, pass_as_kwarg=False
    )


def test_with_user_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_user_slash_option("victim", "who're we getting next?")(mock_command)

    assert result is mock_command.add_user_option.return_value
    mock_command.add_user_option.assert_called_once_with(
        "victim", "who're we getting next?", default=tanjun.commands._UNDEFINED_DEFAULT, pass_as_kwarg=True
    )


def test_with_member_slash_option():
    mock_command = mock.MagicMock()

    result = tanjun.with_member_slash_option("no", "hihihi?", default=123321)(mock_command)

    assert result is mock_command.add_member_option.return_value
    mock_command.add_member_option.assert_called_once_with("no", "hihihi?", default=123321)


def test_with_member_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_member_slash_option("no", "hihihi?")(mock_command)

    assert result is mock_command.add_member_option.return_value
    mock_command.add_member_option.assert_called_once_with("no", "hihihi?", default=tanjun.commands._UNDEFINED_DEFAULT)


def test_with_channel_slash_option():
    mock_command = mock.MagicMock()

    result = tanjun.with_channel_slash_option(
        "channel", "channel?", types=(hikari.GuildCategory, hikari.TextableChannel), default=333, pass_as_kwarg=False
    )(mock_command)

    assert result is mock_command.add_channel_option.return_value
    mock_command.add_channel_option.assert_called_once_with(
        "channel", "channel?", types=(hikari.GuildCategory, hikari.TextableChannel), default=333, pass_as_kwarg=False
    )


def test_with_channel_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_channel_slash_option("channel", "channel?")(mock_command)

    assert result is mock_command.add_channel_option.return_value
    mock_command.add_channel_option.assert_called_once_with(
        "channel", "channel?", types=None, default=tanjun.commands._UNDEFINED_DEFAULT, pass_as_kwarg=True
    )


def test_with_role_slash_option():
    mock_command = mock.MagicMock()

    result = tanjun.with_role_slash_option("role", "role?", default=333, pass_as_kwarg=False)(mock_command)

    assert result is mock_command.add_role_option.return_value
    mock_command.add_role_option.assert_called_once_with("role", "role?", default=333, pass_as_kwarg=False)


def test_with_role_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_role_slash_option("role", "role?")(mock_command)

    assert result is mock_command.add_role_option.return_value
    mock_command.add_role_option.assert_called_once_with(
        "role", "role?", default=tanjun.commands._UNDEFINED_DEFAULT, pass_as_kwarg=True
    )


def test_with_mentionable_slash_option():
    mock_command = mock.MagicMock()

    result = tanjun.with_mentionable_slash_option("mentu", "mentu?", default=333, pass_as_kwarg=False)(mock_command)

    assert result is mock_command.add_mentionable_option.return_value
    mock_command.add_mentionable_option.assert_called_once_with("mentu", "mentu?", default=333, pass_as_kwarg=False)


def test_with_mentionable_slash_option_with_defaults():
    mock_command = mock.MagicMock()

    result = tanjun.with_mentionable_slash_option("mentu", "mentu?", pass_as_kwarg=True)(mock_command)

    assert result is mock_command.add_mentionable_option.return_value
    mock_command.add_mentionable_option.assert_called_once_with(
        "mentu", "mentu?", default=tanjun.commands._UNDEFINED_DEFAULT, pass_as_kwarg=True
    )


class Test_TrackedOption:
    def test_init(self):
        mock_converter = mock.Mock()
        option = tanjun.commands._TrackedOption(
            name="name",
            option_type=hikari.OptionType.FLOAT,
            always_float=False,
            converters=[mock_converter],
            only_member=True,
            default="default",
        )

        assert option.name == "name"
        assert option.type is hikari.OptionType.FLOAT
        assert option.is_always_float is False
        assert option.converters == [mock_converter]
        assert option.is_only_member is True
        assert option.default == "default"

    def test_needs_converter_property_when_all_false(self):
        option = tanjun.commands._TrackedOption(
            name="no",
            option_type=hikari.OptionType.INTEGER,
            converters=[
                mock.Mock(needs_injector=False),
                mock.Mock(needs_injector=False),
                mock.Mock(needs_injector=False),
            ],
        )

        assert option.needs_injector is False

    def test_needs_converter_property_when_no_converters(self):
        option = tanjun.commands._TrackedOption(name="no", option_type=hikari.OptionType.FLOAT)

        assert option.needs_injector is False

    def test_needs_converter_property_when_true(self):
        option = tanjun.commands._TrackedOption(
            name="no",
            option_type=hikari.OptionType.FLOAT,
            converters=[
                mock.Mock(needs_injector=True),
                mock.Mock(needs_injector=False),
                mock.Mock(needs_injector=False),
            ],
        )

        assert option.needs_injector is True

    @pytest.mark.asyncio()
    async def test_convert_when_no_converters(self):
        mock_value = mock.Mock()
        option = tanjun.commands._TrackedOption(name="hi", option_type=hikari.OptionType.INTEGER)

        assert await option.convert(mock.Mock(), mock_value) is mock_value

    @pytest.mark.asyncio()
    async def test_convert_when_all_fail(self):
        mock_converter_1 = mock.AsyncMock(side_effect=ValueError())
        mock_converter_2 = mock.AsyncMock(side_effect=ValueError())
        mock_context = mock.Mock()
        mock_value = mock.Mock()
        option = tanjun.commands._TrackedOption(
            name="no", option_type=hikari.OptionType.FLOAT, converters=[mock_converter_1, mock_converter_2]
        )

        with pytest.raises(tanjun.ConversionError) as exc_info:
            await option.convert(mock_context, mock_value)

        assert exc_info.value.parameter == "no"
        assert exc_info.value.message == "Couldn't convert FLOAT 'no'"
        assert exc_info.value.errors == (mock_converter_1.side_effect, mock_converter_2.side_effect)
        mock_converter_1.assert_awaited_once_with(mock_context, mock_value)
        mock_converter_2.assert_awaited_once_with(mock_context, mock_value)

    @pytest.mark.asyncio()
    async def test_convert(self):
        mock_converter_1 = mock.AsyncMock(side_effect=ValueError())
        mock_converter_2 = mock.AsyncMock()
        mock_converter_3 = mock.AsyncMock()
        mock_context = mock.Mock()
        mock_value = mock.Mock()
        option = tanjun.commands._TrackedOption(
            name="no",
            option_type=hikari.OptionType.FLOAT,
            converters=[mock_converter_1, mock_converter_2, mock_converter_3],
        )

        result = await option.convert(mock_context, mock_value)

        assert result is mock_converter_2.return_value
        mock_converter_1.assert_awaited_once_with(mock_context, mock_value)
        mock_converter_2.assert_awaited_once_with(mock_context, mock_value)
        mock_converter_3.assert_not_called()


@pytest.mark.skip(reason="TODO")
class Test_CommandBuilder:
    ...


_INVALID_NAMES = ["a" * 33, "", "'#'#42123", "Dicksy", "MORGAN", "StAnLey"]


class TestBaseSlashCommand:
    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test__init__with_invalid_name(self, name: str):
        with pytest.raises(
            ValueError,
            match=f"Invalid command name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            stub_class(tanjun.BaseSlashCommand)(name, "desccc")

    def test__init__when_description_too_long(self):
        with pytest.raises(
            ValueError,
            match="The command description cannot be over 100 characters in length",
        ):
            stub_class(tanjun.BaseSlashCommand)("gary", "x" * 101)

    def test_defaults_to_ephemeral_property(self):
        command = stub_class(tanjun.BaseSlashCommand)("hi", "no")

        assert command.set_ephemeral_default(True).defaults_to_ephemeral is True

    def test_description_property(self):
        command = stub_class(tanjun.BaseSlashCommand)("hi", "desccc")

        assert command.description == "desccc"

    def test_is_global_property(self):
        command = stub_class(tanjun.BaseSlashCommand)("yeet", "No", is_global=False)

        assert command.is_global is False

    def test_name_property(self):
        command = stub_class(tanjun.BaseSlashCommand)("yee", "nsoosos")

        assert command.name == "yee"

    def test_parent_property(self):
        mock_parent = mock.Mock()
        command = stub_class(tanjun.BaseSlashCommand)("yee", "nsoosos")

        assert command.set_parent(mock_parent).parent is mock_parent

    def test_tracked_command_id_property(self):
        command = stub_class(tanjun.BaseSlashCommand)("yee", "nsoosos")
        mock_command = mock.Mock(hikari.Command, __int__=mock.Mock(return_value=5312123))

        assert command.set_tracked_command(mock_command).tracked_command_id == 5312123

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_check_context(self):
        mock_callback = mock.Mock()
        mock_other_callback = mock.Mock()
        mock_context = mock.Mock()
        mock_checks = [mock.Mock(), mock.Mock()]

        with mock.patch.object(tanjun.checks, "InjectableCheck", side_effect=mock_checks.copy()) as injectable_check:
            command = stub_class(tanjun.BaseSlashCommand)("yee", "nsoosos", checks=[mock_callback, mock_other_callback])

            injectable_check.call_args_list == [mock.call(mock_callback), mock.call(mock_other_callback)]

        with mock.patch.object(tanjun.utilities, "gather_checks", new=mock.AsyncMock()) as gather_checks:
            result = await command.check_context(mock_context)

            gather_checks.assert_awaited_once_with(mock_context, set(mock_checks))

        assert result is gather_checks.return_value
        mock_context.set_command.assert_has_calls([mock.call(command), mock.call(None)])

    @pytest.mark.skip(reason="TODO")
    def test_copy(self):
        mock_parent = mock.MagicMock()
        command = stub_class(tanjun.BaseSlashCommand)("yee", "nsoosos")

        result = command.copy(parent=mock_parent)

        assert result is not command
        assert isinstance(result, tanjun.BaseSlashCommand)
        assert result.parent is mock_parent

    def test_load_into_component_when_no_parent(self):
        mock_component = mock.Mock()
        command = stub_class(tanjun.BaseSlashCommand)("yee", "nsoosos")

        result = command.load_into_component(mock_component)

        assert result is command
        mock_component.add_slash_command.assert_called_once_with(command)


class TestSlashCommandGroup:
    def test_commands_property(self):
        mock_command = mock.Mock()
        mock_other_command = mock.Mock()
        command = tanjun.SlashCommandGroup("yee", "nsoosos").add_command(mock_command).add_command(mock_other_command)

        assert list(command.commands) == [mock_command, mock_other_command]

    def test_build(self):
        mock_command = mock.Mock(tanjun.abc.SlashCommand)
        mock_command_group = mock.Mock(tanjun.abc.SlashCommandGroup)
        command_group = (
            tanjun.SlashCommandGroup("yee", "nsoosos", default_permission=True)
            .add_command(mock_command)
            .add_command(mock_command_group)
        )

        result = command_group.build()

        assert result == (
            tanjun.commands._CommandBuilder("yee", "nsoosos", False)
            .set_default_permission(True)
            .add_option(
                hikari.CommandOption(
                    type=hikari.OptionType.SUB_COMMAND,
                    name=mock_command.name,  # type: ignore
                    description=mock_command.build.return_value.description,  # type: ignore
                    is_required=False,  # type: ignore
                    options=mock_command.build.return_value.options,  # type: ignore
                )
            )
            .add_option(
                hikari.CommandOption(
                    type=hikari.OptionType.SUB_COMMAND_GROUP,
                    name=mock_command_group.name,  # type: ignore
                    description=mock_command_group.build.return_value.description,  # type: ignore
                    is_required=False,  # type: ignore
                    options=mock_command_group.build.return_value.options,  # type: ignore
                )
            )
        )

    def test_build_when_tracked_command_set(self):
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").set_tracked_command(
            mock.Mock(hikari.Command, __int__=mock.Mock(return_value=123))
        )

        result = command_group.build()

        assert result == (
            tanjun.commands._CommandBuilder("yee", "nsoosos", False).set_id(123).set_default_permission(True)
        )

    @pytest.mark.skip(reason="TODO")
    def test_copy(self):
        ...

    def test_add_command(self):
        command_group = tanjun.SlashCommandGroup("yeet", "need")
        mock_command = mock.Mock()

        result = command_group.add_command(mock_command)

        assert result is command_group
        mock_command.set_parent.assert_called_once_with(command_group)
        assert mock_command in command_group.commands

    def test_add_command_when_too_many_commands(self):
        command_group = tanjun.SlashCommandGroup("yeet", "need")
        mock_command = mock.Mock()

        for _ in range(25):
            command_group.add_command(mock.Mock())

        with pytest.raises(ValueError, match="Cannot add more than 25 commands to a slash command group"):
            command_group.add_command(mock_command)

        mock_command.set_parent.assert_not_called()
        assert mock_command not in command_group.commands

    def test_add_command_when_too_many_commands_when_name_already_present(self):
        mock_command = mock.Mock()
        mock_command.name = "yeet"
        command_group = tanjun.SlashCommandGroup("yeet", "need").add_command(mock_command)
        mock_command = mock.Mock()
        mock_command.name = "yeet"

        with pytest.raises(ValueError, match="Command with name 'yeet' already exists in this group"):
            command_group.add_command(mock_command)

        mock_command.set_parent.assert_not_called()
        assert mock_command not in command_group.commands

    def test_add_command_when_nested(self):
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").set_parent(mock.Mock())
        mock_sub_command = mock.Mock(tanjun.abc.SlashCommand)

        result = command_group.add_command(mock_sub_command)

        assert result is command_group
        mock_sub_command.set_parent.assert_called_once_with(command_group)
        assert mock_sub_command in command_group.commands

    def test_add_command_when_attempting_to_double_nest_groups(self):
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").set_parent(mock.Mock())

        with pytest.raises(ValueError, match="Cannot add a slash command group to a nested slash command group"):
            command_group.add_command(mock.Mock(tanjun.abc.SlashCommandGroup))

    def test_remove_command(self):
        mock_sub_command = mock.Mock(tanjun.abc.SlashCommand)
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").set_parent(mock.Mock()).add_command(mock_sub_command)

        result = command_group.remove_command(mock_sub_command)

        assert result is command_group
        assert mock_sub_command not in command_group.commands

    def test_with_command(self):
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").set_parent(mock.Mock())
        mock_sub_command = mock.Mock(tanjun.abc.SlashCommand)

        result = command_group.with_command(mock_sub_command)

        assert result is mock_sub_command
        assert mock_sub_command in command_group.commands

    @pytest.mark.asyncio()
    async def test_execute(self):
        mock_command = mock.AsyncMock(set_parent=mock.Mock(), defaults_to_ephemeral=None)
        mock_command.name = "sex"
        mock_command.check_context.return_value = True
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").add_command(mock_command)
        mock_context = mock.Mock()
        mock_option = mock.Mock()
        mock_option.name = "sex"
        mock_context.interaction.options = [mock_option]
        mock_hooks = mock.Mock()

        await command_group.execute(mock_context, hooks=mock_hooks)

        mock_command.execute.assert_awaited_once_with(mock_context, option=mock_option, hooks=mock_hooks)
        mock_command.check_context.assert_awaited_once_with(mock_context)
        mock_context.set_ephemeral_default.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_when_sub_command_has_ephemeral_default_set(self):
        mock_command = mock.AsyncMock(set_parent=mock.Mock(), defaults_to_ephemeral=True)
        mock_command.name = "sex"
        mock_command.check_context.return_value = True
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").add_command(mock_command)
        mock_context = mock.Mock()
        mock_option = mock.Mock()
        mock_option.name = "sex"
        mock_context.interaction.options = [mock_option]
        mock_hooks = mock.Mock()

        await command_group.execute(mock_context, hooks=mock_hooks)

        mock_command.execute.assert_awaited_once_with(mock_context, option=mock_option, hooks=mock_hooks)
        mock_command.check_context.assert_awaited_once_with(mock_context)
        mock_context.set_ephemeral_default.assert_called_once_with(True)

    @pytest.mark.asyncio()
    async def test_execute_when_not_found(self):
        command_group = stub_class(tanjun.SlashCommandGroup, check_context=mock.AsyncMock(return_value=True))(
            "yee", "nsoosos"
        )
        mock_context = mock.AsyncMock()
        mock_context.interaction.options = [mock.Mock()]

        await command_group.execute(mock_context)

        mock_context.mark_not_found.assert_awaited_once_with()
        mock_context.set_ephemeral_default.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_when_checks_fail(self):
        mock_command = mock.AsyncMock(set_parent=mock.Mock(), defaults_to_ephemeral=None)
        mock_command.name = "sex"
        mock_command.check_context.return_value = False
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").add_command(mock_command)
        mock_context = mock.AsyncMock()
        mock_option = mock.Mock()
        mock_option.name = "sex"
        mock_context.interaction.options = [mock_option]
        mock_hooks = mock.Mock()

        await command_group.execute(mock_context, hooks=mock_hooks)

        mock_command.execute.assert_not_called()
        mock_command.check_context.assert_awaited_once_with(mock_context)
        mock_context.mark_not_found.assert_awaited_once_with()
        mock_context.set_ephemeral_default.assert_not_called()

    @pytest.mark.asyncio()
    async def test_execute_when_nested(self):
        mock_command = mock.AsyncMock(
            check_context=mock.AsyncMock(return_value=True), set_parent=mock.Mock(), defaults_to_ephemeral=None
        )
        mock_command.name = "hi"
        command_group = tanjun.SlashCommandGroup("yee", "nsoosos").add_command(mock_command)
        mock_context = mock.Mock()
        mock_sub_option = mock.Mock()
        mock_sub_option.name = "hi"
        mock_option = mock.Mock(options=[mock_sub_option])
        mock_hooks = mock.Mock()

        await command_group.execute(mock_context, option=mock_option, hooks=mock_hooks)

        mock_command.execute.assert_awaited_once_with(mock_context, option=mock_sub_option, hooks=mock_hooks)
        mock_command.check_context.assert_awaited_once_with(mock_context)
        mock_context.set_ephemeral_default.assert_not_called()

    @pytest.mark.skip(reason="TODO")
    def test_load_into_component(self):
        ...


class TestSlashCommand:
    @pytest.fixture()
    def command(self) -> tanjun.SlashCommand[typing.Any]:
        return tanjun.SlashCommand(mock.AsyncMock(), "yee", "nsoosos")

    @pytest.mark.asyncio()
    async def test___call__(self):
        mock_callback = mock.AsyncMock()
        command = tanjun.SlashCommand(mock_callback, "yee", "nsoosos")

        await command(1, 3, a=4, b=5)  # type: ignore

        mock_callback.assert_awaited_once_with(1, 3, a=4, b=5)

    def test_callback_property(self):
        mock_callback = mock.Mock()
        command = tanjun.SlashCommand(mock_callback, "yee", "nsoosos")

        assert command.callback is mock_callback

    def test_add_str_option(self, command: tanjun.SlashCommand[typing.Any]):
        mock_converter = mock.Mock()
        command.add_str_option(
            "boom", "No u", choices={"Aye": "aye", "Bye man": "bye"}, converters=[mock_converter], default="ayya"
        )

        option = command.build().options[0]
        assert option.name == "boom"
        assert option.description == "No u"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.STRING
        assert option.choices == [
            hikari.CommandChoice(name="Aye", value="aye"),
            hikari.CommandChoice(name="Bye man", value="bye"),
        ]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.STRING
        assert tracked.default == "ayya"
        assert tracked.converters == [mock_converter]
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_str_option_with_choices_list(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_str_option("boom", "No u", choices=["video", "channel", "playlist"])

        option = command.build().options[0]
        assert option.name == "boom"
        assert option.description == "No u"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.STRING
        assert option.choices == [
            hikari.CommandChoice(name="Video", value="video"),
            hikari.CommandChoice(name="Channel", value="channel"),
            hikari.CommandChoice(name="Playlist", value="playlist"),
        ]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.STRING
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_str_option_with_deprecated_choices_tuple_list(self, command: tanjun.SlashCommand[typing.Any]):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            command.add_str_option(
                "boom",
                "No u",
                choices=[("gay", "Gay"), "no", ("lesbian_bi", "Lesbian Bi"), ("transive", "Trans")],  # type: ignore
            )

        option = command.build().options[0]
        assert option.name == "boom"
        assert option.description == "No u"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.STRING
        assert option.choices == [
            hikari.CommandChoice(name="gay", value="Gay"),
            hikari.CommandChoice(name="No", value="no"),
            hikari.CommandChoice(name="lesbian_bi", value="Lesbian Bi"),
            hikari.CommandChoice(name="transive", value="Trans"),
        ]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.STRING
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_str_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_str_option("boom", "No u")

        option = command.build().options[0]
        assert option.name == "boom"
        assert option.description == "No u"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.STRING
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.STRING
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_str_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_str_option("hi", "Nou", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "hi"
        assert option.description == "Nou"
        assert option.type is hikari.OptionType.STRING
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_str_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_str_option(name, "aye")

    def test_test_add_str_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_str_option("boi", "a" * 101)

    def test_test_add_str_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_str_option("namae", "aye")

    def test_test_add_str_option_with_too_many_choices(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(ValueError, match="Slash command options cannot have more than 25 choices"):
            command.add_str_option("namae", "aye", choices={mock.Mock(): mock.Mock() for _ in range(26)})

    def test_add_int_option(self, command: tanjun.SlashCommand[typing.Any]):
        mock_converter = mock.Mock()

        command.add_int_option("see", "seesee", choices={"hi": 1, "no": 21}, converters=[mock_converter], default="nya")

        option = command.build().options[0]
        assert option.name == "see"
        assert option.description == "seesee"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.INTEGER
        assert option.choices == [hikari.CommandChoice(name="hi", value=1), hikari.CommandChoice(name="no", value=21)]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.INTEGER
        assert tracked.default == "nya"
        assert tracked.converters == [mock_converter]
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_int_option_with_deprecated_choices_tuple_list(self, command: tanjun.SlashCommand[typing.Any]):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            command.add_int_option("see", "seesee", choices=[("les", 1), ("g", 43)])  # type: ignore

        option = command.build().options[0]
        assert option.name == "see"
        assert option.description == "seesee"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.INTEGER
        assert option.choices == [hikari.CommandChoice(name="les", value=1), hikari.CommandChoice(name="g", value=43)]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.INTEGER
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_int_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_int_option("e", "a")

        option = command.build().options[0]
        assert option.name == "e"
        assert option.description == "a"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.INTEGER
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.INTEGER
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_int_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_int_option("hiu", "Nouu", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "hiu"
        assert option.description == "Nouu"
        assert option.type is hikari.OptionType.INTEGER
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_int_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_int_option(name, "aye")

    def test_test_add_int_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_int_option("boi", "a" * 101)

    def test_test_add_int_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_int_option("namae", "aye")

    def test_test_add_int_option_with_too_many_choices(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(ValueError, match="Slash command options cannot have more than 25 choices"):
            command.add_int_option("namae", "aye", choices={mock.Mock(): mock.Mock() for _ in range(26)})

    def test_add_float_option(self, command: tanjun.SlashCommand[typing.Any]):
        mock_converter = mock.Mock()
        command.add_float_option(
            "sesese",
            "asasasa",
            choices={"no": 4.4, "ok": 6.9},
            converters=[mock_converter],
            default="eaf",
            always_float=False,
        )

        option = command.build().options[0]
        assert option.name == "sesese"
        assert option.description == "asasasa"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.FLOAT
        assert option.choices == [
            hikari.CommandChoice(name="no", value=4.4),
            hikari.CommandChoice(name="ok", value=6.9),
        ]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.FLOAT
        assert tracked.default == "eaf"
        assert tracked.converters == [mock_converter]
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_float_option_with_deprecated_choices_tuple_list(self, command: tanjun.SlashCommand[typing.Any]):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            command.add_float_option("easy", "aaa", choices=[("blam", 4.20), ("blam2", 6.9)])  # type: ignore

        option = command.build().options[0]
        assert option.name == "easy"
        assert option.description == "aaa"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.FLOAT
        assert option.choices == [
            hikari.CommandChoice(name="blam", value=4.20),
            hikari.CommandChoice(name="blam2", value=6.9),
        ]

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.FLOAT
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is True
        assert tracked.is_only_member is False

    def test_add_float_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_float_option("easy", "aaa")

        option = command.build().options[0]
        assert option.name == "easy"
        assert option.description == "aaa"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.FLOAT
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.FLOAT
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is True
        assert tracked.is_only_member is False

    def test_add_float_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_float_option("123", "321", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "123"
        assert option.description == "321"
        assert option.type is hikari.OptionType.FLOAT
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_float_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_float_option(name, "aye")

    def test_test_add_float_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_float_option("boi", "a" * 101)

    def test_test_add_float_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_float_option("namae", "aye")

    def test_test_add_float_option_with_too_many_choices(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(ValueError, match="Slash command options cannot have more than 25 choices"):
            command.add_float_option("namae", "aye", choices={mock.Mock(): mock.Mock() for _ in range(26)})

    def test_add_bool_option(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_bool_option("eaassa", "saas", default="feel")

        option = command.build().options[0]
        assert option.name == "eaassa"
        assert option.description == "saas"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.BOOLEAN
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.BOOLEAN
        assert tracked.default == "feel"
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_bool_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_bool_option("essssss", "aaaaaaa")

        option = command.build().options[0]
        assert option.name == "essssss"
        assert option.description == "aaaaaaa"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.BOOLEAN
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.BOOLEAN
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_bool_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_bool_option("222", "333", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "222"
        assert option.description == "333"
        assert option.type is hikari.OptionType.BOOLEAN
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_bool_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_bool_option(name, "aye")

    def test_test_add_bool_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_bool_option("boi", "a" * 101)

    def test_test_add_bool_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_bool_option("namae", "aye")

    def test_add_user_option(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_user_option("yser", "nanm", default="nou")

        option = command.build().options[0]
        assert option.name == "yser"
        assert option.description == "nanm"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.USER
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.USER
        assert tracked.default == "nou"
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_user_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_user_option("fafafa", "sfsfsf")

        option = command.build().options[0]
        assert option.name == "fafafa"
        assert option.description == "sfsfsf"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.USER
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.USER
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_user_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_user_option("eee", "333", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "eee"
        assert option.description == "333"
        assert option.type is hikari.OptionType.USER
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_user_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_user_option(name, "aye")

    def test_test_add_user_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_user_option("boi", "a" * 101)

    def test_test_add_user_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_user_option("namae", "aye")

    def test_add_member_option(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_member_option("ddddd", "sssss", default="dsasds")

        option = command.build().options[0]
        assert option.name == "ddddd"
        assert option.description == "sssss"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.USER
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.USER
        assert tracked.default == "dsasds"
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is True

    def test_add_member_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_member_option("asasas", "fdssdddsds")

        option = command.build().options[0]
        assert option.name == "asasas"
        assert option.description == "fdssdddsds"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.USER
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.USER
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is True

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_member_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_member_option(name, "aye")

    def test_test_add_member_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_member_option("boi", "a" * 101)

    def test_test_add_member_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_member_option("namae", "aye")

    def test_add_channel_option(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_channel_option("c", "d", default="eee")

        option = command.build().options[0]
        assert option.name == "c"
        assert option.description == "d"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.CHANNEL
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.CHANNEL
        assert tracked.default == "eee"
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_channel_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_channel_option("channel", "chaaa")

        option = command.build().options[0]
        assert option.name == "channel"
        assert option.description == "chaaa"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.CHANNEL
        assert option.choices is None
        assert option.channel_types is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.CHANNEL
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    @pytest.mark.parametrize(
        ("classes", "int_types"),
        [
            ([hikari.TextableGuildChannel], [hikari.ChannelType.GUILD_TEXT, hikari.ChannelType.GUILD_NEWS]),
            (
                [hikari.TextableGuildChannel, hikari.GuildNewsChannel],
                [hikari.ChannelType.GUILD_TEXT, hikari.ChannelType.GUILD_NEWS],
            ),
            ([hikari.GuildVoiceChannel], [hikari.ChannelType.GUILD_VOICE]),
            (
                [hikari.GuildVoiceChannel, hikari.GuildStageChannel, hikari.GuildNewsChannel],
                [hikari.ChannelType.GUILD_VOICE, hikari.ChannelType.GUILD_NEWS, hikari.ChannelType.GUILD_STAGE],
            ),
            ([], None),
        ],
    )
    def test_add_channel_option_types_behaviour(
        self,
        command: tanjun.SlashCommand[typing.Any],
        classes: list[type[hikari.PartialChannel]],
        int_types: typing.Optional[list[int]],
    ):
        command.add_channel_option("channel", "chaaa", types=classes)

        option = command.build().options[0]
        assert option.channel_types == int_types

    def test_add_channel_option_with_invalid_type(self, command: tanjun.SlashCommand[typing.Any]):
        with pytest.raises(ValueError, match="Unknown channel type <class 'bool'>"):
            command.add_channel_option("channel", "chaaa", types=(bool,))  # type: ignore

    def test_add_channel_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_channel_option("dsds", "www", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "dsds"
        assert option.description == "www"
        assert option.type is hikari.OptionType.CHANNEL
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_channel_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_channel_option(name, "aye")

    def test_test_add_channel_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_channel_option("boi", "a" * 101)

    def test_test_add_channel_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_channel_option("namae", "aye")

    def test_add_role_option(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_role_option("jhjh", "h", default="shera")

        option = command.build().options[0]
        assert option.name == "jhjh"
        assert option.description == "h"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.ROLE
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.ROLE
        assert tracked.default == "shera"
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_role_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_role_option("hhhhh", "h")

        option = command.build().options[0]
        assert option.name == "hhhhh"
        assert option.description == "h"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.ROLE
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.ROLE
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_role_option_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_role_option("22222", "ddddd", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "22222"
        assert option.description == "ddddd"
        assert option.type is hikari.OptionType.ROLE
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_role_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_role_option(name, "aye")

    def test_test_add_role_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_role_option("boi", "a" * 101)

    def test_test_add_role_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_role_option("namae", "aye")

    def test_add_mentionable_option(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_mentionable_option("owo", "iwi", default="ywy")

        option = command.build().options[0]
        assert option.name == "owo"
        assert option.description == "iwi"
        assert option.is_required is False
        assert option.options is None
        assert option.type is hikari.OptionType.MENTIONABLE
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.MENTIONABLE
        assert tracked.default == "ywy"
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_mentionable_option_with_defaults(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_mentionable_option("shera-ra", "hhh")

        option = command.build().options[0]
        assert option.name == "shera-ra"
        assert option.description == "hhh"
        assert option.is_required is True
        assert option.options is None
        assert option.type is hikari.OptionType.MENTIONABLE
        assert option.choices is None

        tracked = command._tracked_options[option.name]
        assert tracked.name == option.name
        assert tracked.type is hikari.OptionType.MENTIONABLE
        assert tracked.default is tanjun.commands._UNDEFINED_DEFAULT
        assert tracked.converters == []
        assert tracked.is_always_float is False
        assert tracked.is_only_member is False

    def test_add_mentionable_option_option_when_not_pass_as_kwarg(self, command: tanjun.SlashCommand[typing.Any]):
        command.add_mentionable_option("333ww", "dsdsds", pass_as_kwarg=False)

        option = command.build().options[0]
        assert option.name == "333ww"
        assert option.description == "dsdsds"
        assert option.type is hikari.OptionType.MENTIONABLE
        assert option.name not in command._tracked_options

    @pytest.mark.parametrize("name", _INVALID_NAMES)
    def test_test_add_mentionable_option_with_invalid_name(self, name: str):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match=f"Invalid command option name provided, {name!r} doesn't match the required regex "
            + re.escape("`^[a-z0-9_-](1, 32)$`"),
        ):
            command.add_mentionable_option(name, "aye")

    def test_test_add_mentionable_option_when_description_too_long(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")

        with pytest.raises(
            ValueError,
            match="The option description cannot be over 100 characters in length",
        ):
            command.add_mentionable_option("boi", "a" * 101)

    def test_test_add_mentionable_option_when_too_many_options(self):
        command = tanjun.SlashCommand(mock.Mock(), "yee", "nsoosos")
        for index in range(25):
            command.add_str_option(str(index), str(index))

        with pytest.raises(
            ValueError,
            match="Slash commands cannot have more than 25 options",
        ):
            command.add_mentionable_option("namae", "aye")

    @pytest.mark.skip(reason="TODO")
    def test_needs_injector_property(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_build(self):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_execute(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_copy(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_load_into_component(self):
        ...


def test_as_message_command():
    mock_callback = mock.Mock()
    command = tanjun.as_message_command("a", "b")(mock_callback)

    assert command.names == ["a", "b"]
    assert command.callback is mock_callback


def test_as_message_command_group():
    mock_callback = mock.Mock()
    command = tanjun.as_message_command_group("c", "b", strict=True)(mock_callback)

    assert command.names == ["c", "b"]
    assert command.is_strict is True
    assert command.callback is mock_callback


class TestMessageCommand:
    @pytest.mark.skip(reason="TODO")
    def test___repr__(self):
        ...

    def test_callback_property(self):
        mock_callback = mock.Mock()

        assert tanjun.MessageCommand(mock_callback, "yee", "nsoosos").callback is mock_callback

    def test_names_property(self):
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc")

        assert command.names == ["aaaaa", "bbbbb", "ccccc"]

    @pytest.mark.skip(reason="TODO")
    def test_needs_injector_property(self):
        ...

    def test_parent_property(self):
        mock_parent = mock.Mock()
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parent(mock_parent)

        assert command.parent is mock_parent

    def test_parser_property(self):
        mock_parser = mock.Mock()
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parser(mock_parser)

        assert command.parser is mock_parser

    def test_bind_client(self):
        mock_client = mock.Mock()
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc")

        with mock.patch.object(tanjun.commands.PartialCommand, "bind_client") as bind_client:
            command.bind_client(mock_client)

            bind_client.assert_called_once_with(mock_client)

    def test_bind_client_when_has_parser(self):
        mock_client = mock.Mock()
        mock_parser = mock.Mock()
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parser(mock_parser)

        with mock.patch.object(tanjun.commands.PartialCommand, "bind_client") as bind_client:
            command.bind_client(mock_client)

            bind_client.assert_called_once_with(mock_client)

        mock_parser.bind_client.assert_called_once_with(mock_client)

    def test_bind_component(self):
        mock_component = mock.Mock()
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc")

        with mock.patch.object(tanjun.commands.PartialCommand, "bind_component") as bind_component:
            command.bind_component(mock_component)

            bind_component.assert_called_once_with(mock_component)

    def test_bind_component_when_has_parser(self):
        mock_component = mock.Mock()
        mock_parser = mock.Mock()
        command = tanjun.MessageCommand(mock.Mock(), "aaaaa", "bbbbb", "ccccc").set_parser(mock_parser)

        with mock.patch.object(tanjun.commands.PartialCommand, "bind_component") as bind_component:
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
        mock_checks = [mock.Mock(), mock.Mock()]

        with mock.patch.object(tanjun.checks, "InjectableCheck", side_effect=mock_checks.copy()) as injectable_check:
            command = tanjun.MessageCommand(mock.Mock(), "yee", "nsoosos", checks=[mock_callback, mock_other_callback])

            injectable_check.call_args_list == [mock.call(mock_callback), mock.call(mock_other_callback)]

        with mock.patch.object(tanjun.utilities, "gather_checks", new=mock.AsyncMock()) as gather_checks:
            result = await command.check_context(mock_context)

            gather_checks.assert_awaited_once_with(mock_context, mock_checks)

        assert result is gather_checks.return_value
        mock_context.set_command.assert_has_calls([mock.call(command), mock.call(None)])

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_execute(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_load_into_component(self):
        ...


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
        command_group = tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos")

        result = command_group.add_command(mock_command)

        assert result is command_group
        mock_command.set_parent.assert_called_once_with(command_group)
        assert mock_command in command_group.commands

    def test_add_command_when_already_present(self):
        mock_command = mock.Mock()
        command_group = tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos")

        result = command_group.add_command(mock_command).add_command(mock_command)

        assert result is command_group
        assert list(command_group.commands).count(mock_command) == 1

    def test_add_command_when_strict(self):
        mock_command = mock.Mock(names={"a", "b"})
        command_group = tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos", strict=True)

        result = command_group.add_command(mock_command)

        assert result is command_group
        mock_command.set_parent.assert_called_once_with(command_group)
        assert mock_command in command_group.commands

    def test_add_command_when_strict_and_space_in_any_name(self):
        command_group = tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos", strict=True)

        with pytest.raises(
            ValueError, match="Sub-command names may not contain spaces in a strict message command group"
        ):
            command_group.add_command(mock.Mock(names={"a space", "b"}))

    def test_add_command_when_strict_and_conflicts_found(self):
        command_group = (
            tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos", strict=True)
            .add_command(mock.Mock(names={"aaa", "b"}))
            .add_command(mock.Mock(names={"fsa", "dsaasd"}))
        )

        with pytest.raises(
            ValueError,
            match="Sub-command names must be unique in a strict message command group. "
            "The following conflicts were found (?:aaa, dsaasd)|(?:dsaasd, aaa)",
        ):
            command_group.add_command(mock.Mock(names={"aaa", "dsaasd"}))

    def test_remove_command(self):
        mock_command = mock.Mock()
        command_group = tanjun.MessageCommandGroup(mock.Mock(), "a", "b").add_command(mock_command)

        result = command_group.remove_command(mock_command)

        assert result is command_group
        assert mock_command not in command_group.commands

    def test_remove_command_when_strict(self):
        mock_command = mock.Mock(names={"abba", "bba", "dadaba"})
        mock_other_command = mock.Mock(names={"dada"})
        command_group = (
            tanjun.MessageCommandGroup(mock.Mock(), "a", "b", strict=True)
            .add_command(mock_command)
            .add_command(mock_other_command)
        )

        result = command_group.remove_command(mock_command)

        assert result is command_group
        assert mock_command not in command_group.commands
        assert command_group._names_to_commands == {"dada": mock_other_command}

    def test_with_command(self):
        add_command = mock.Mock()
        command = stub_class(tanjun.MessageCommandGroup[typing.Any], add_command=add_command)(mock.Mock(), "a", "b")
        mock_command = mock.Mock()

        result = command.with_command(mock_command)

        assert result is mock_command
        add_command.assert_called_once_with(mock_command)

    def test_bind_client(self):
        mock_command_1 = mock.Mock()
        mock_command_2 = mock.Mock()
        mock_command_3 = mock.Mock()
        command = (
            tanjun.MessageCommandGroup(mock.Mock(), "a", "b")
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
            tanjun.MessageCommandGroup(mock.Mock(), "a", "b")
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
            tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos")
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
            tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos", strict=True)
            .add_command(mock_command_1)
            .add_command(mock.Mock(names={"boomer"}))
            .add_command(mock.Mock(names={"go"}))
        )

        results = list(command_group.find_command("ok i am going home now"))

        assert results == [("ok", mock_command_1)]

    def test_find_command_when_strict_and_unknown_name(self):
        command_group = (
            tanjun.MessageCommandGroup(mock.Mock(), "yee", "nsoosos", strict=True)
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
        command_group = tanjun.MessageCommandGroup(mock.AsyncMock(), "hi", "nsoosos")

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
        )(mock.AsyncMock(), "a", "b").set_hooks(mock_attached_hooks)

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
        )(mock.AsyncMock(), "a", "b").set_hooks(mock_attached_hooks)

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
        )(mock.AsyncMock(), "a", "b")

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
        )(mock.AsyncMock(), "a", "b").set_hooks(mock_attached_hooks)

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
        )(mock.AsyncMock(), "a", "b").set_hooks(mock_attached_hooks)

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
        )(mock.AsyncMock(), "a", "b")

        with mock.patch.object(tanjun.commands.MessageCommand, "execute", new=mock.AsyncMock()) as mock_execute:
            await command.execute(mock_context)

            mock_execute.assert_called_once_with(mock_context, hooks=None)

        mock_context.set_content.assert_not_called()
        mock_context.set_triggering_name.assert_not_called()
        mock_command_1.check_context.assert_awaited_once_with(mock_context)
        mock_command_2.check_context.assert_awaited_once_with(mock_context)
        mock_command_1.execute.assert_not_called()
        mock_command_2.execute.assert_not_called()

    @pytest.mark.skip(reason="TODO")
    def test_load_into_component(self):
        ...
