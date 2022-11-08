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
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import asyncio
import datetime
import types
import typing
from collections import abc as collections
from unittest import mock

import alluka
import hikari
import pytest

import tanjun

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


@pytest.fixture()
def mock_client() -> tanjun.abc.Client:
    return mock.MagicMock(tanjun.abc.Client, rest=mock.AsyncMock(hikari.api.RESTClient))


@pytest.fixture()
def mock_component() -> tanjun.abc.Component:
    return mock.MagicMock(tanjun.abc.Component)


class TestSlashOption:
    def test_name_property(self):
        mock_option = mock.Mock()

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).name is mock_option.name

    def test_type_property(self):
        mock_option = mock.Mock()

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).type is mock_option.type

    @pytest.mark.parametrize("type_", [hikari.OptionType.STRING, hikari.OptionType.FLOAT, hikari.OptionType.INTEGER])
    def test_value_property(self, type_: hikari.OptionType):
        mock_option = mock.Mock(type=type_)

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).value is mock_option.value

    @pytest.mark.parametrize(
        "type_",
        [hikari.OptionType.CHANNEL, hikari.OptionType.USER, hikari.OptionType.ROLE, hikari.OptionType.MENTIONABLE],
    )
    def test_value_property_for_unique_type(self, type_: hikari.OptionType):
        mock_option = mock.Mock(type=type_, value="123321")

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).value == 123321

    def test_boolean(self):
        mock_option = mock.Mock(type=hikari.OptionType.BOOLEAN, value=True)

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).boolean() is True

    def test_boolean_when_not_bool_type(self):
        with pytest.raises(TypeError, match="Option is not a boolean"):
            assert tanjun.context.SlashOption(mock.Mock(), mock.Mock()).boolean()

    def test_float(self):
        mock_option = mock.Mock(type=hikari.OptionType.FLOAT, value=123.312)

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).float() == 123.312

    def test_float_when_not_float_type(self):
        with pytest.raises(TypeError, match="Option is not a float"):
            assert tanjun.context.SlashOption(mock.Mock(), mock.Mock()).float()

    def test_integer(self):
        mock_option = mock.Mock(type=hikari.OptionType.INTEGER, value=69300)

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).integer() == 69300

    def test_integer_when_not_integer_type(self):
        with pytest.raises(TypeError, match="Option is not an integer"):
            assert tanjun.context.SlashOption(mock.Mock(), mock.Mock()).integer()

    @pytest.mark.parametrize(
        "type_",
        [hikari.OptionType.CHANNEL, hikari.OptionType.USER, hikari.OptionType.ROLE, hikari.OptionType.MENTIONABLE],
    )
    def test_snowflake(self, type_: hikari.OptionType):
        mock_option = mock.Mock(type=type_, value="45123")

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).snowflake() == 45123

    @pytest.mark.parametrize("type_", [hikari.OptionType.STRING, hikari.OptionType.FLOAT, hikari.OptionType.INTEGER])
    def test_snowflake_when_not_unique_type(self, type_: hikari.OptionType):
        mock_option = mock.Mock(type=type_)

        with pytest.raises(TypeError, match="Option is not a unique resource"):
            assert tanjun.context.SlashOption(mock.Mock(), mock_option).snowflake()

    def test_string(self):
        mock_option = mock.Mock(type=hikari.OptionType.STRING, value="hi  meow")

        assert tanjun.context.SlashOption(mock.Mock(), mock_option).string() == "hi  meow"

    def test_string_when_not_str_type(self):
        with pytest.raises(TypeError, match="Option is not a string"):
            assert tanjun.context.SlashOption(mock.Mock(), mock.Mock()).string()

    def test_resolve_value_for_attachment_option(self):
        resolve_to_attachment = mock.Mock()
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_attachment=resolve_to_attachment,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.ATTACHMENT)),
        )

        result = option.resolve_value()

        assert result is resolve_to_attachment.return_value
        resolve_to_attachment.assert_called_once_with()
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_channel_option(self):
        resolve_to_attachment = mock.Mock()
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_attachment=resolve_to_attachment,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.CHANNEL)),
        )

        result = option.resolve_value()

        assert result is resolve_to_channel.return_value
        resolve_to_attachment.assert_not_called()
        resolve_to_channel.assert_called_once_with()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_role_option(self):
        resolve_to_attachment = mock.Mock()
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_attachment=resolve_to_attachment,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.ROLE)),
        )

        result = option.resolve_value()

        assert result is resolve_to_role.return_value
        resolve_to_attachment.assert_not_called()
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_called_once_with()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_user_option(self):
        resolve_to_attachment = mock.Mock()
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_attachment=resolve_to_attachment,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.USER)),
        )

        result = option.resolve_value()

        assert result is resolve_to_user.return_value
        resolve_to_attachment.assert_not_called()
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_called_once_with()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_mentionable_option(self):
        resolve_to_attachment = mock.Mock()
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_attachment=resolve_to_attachment,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.MENTIONABLE)),
        )

        result = option.resolve_value()

        assert result is resolve_to_mentionable.return_value
        resolve_to_attachment.assert_not_called()
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_called_once_with()

    @pytest.mark.parametrize(
        "option_type",
        set(hikari.OptionType).difference(
            {
                hikari.OptionType.ATTACHMENT,
                hikari.OptionType.ROLE,
                hikari.OptionType.USER,
                hikari.OptionType.MENTIONABLE,
                hikari.OptionType.CHANNEL,
            }
        ),
    )
    def test_resolve_value_for_non_resolvable_option(self, option_type: hikari.OptionType):
        option = tanjun.context.SlashOption(mock.Mock(), mock.Mock(type=option_type))

        with pytest.raises(TypeError):
            option.resolve_value()

    def test_resolve_to_attachment(self):
        mock_attachment = mock.Mock()
        mock_resolved = mock.Mock(attachments={696969696: mock_attachment})
        option = tanjun.context.SlashOption(
            mock_resolved, mock.Mock(type=hikari.OptionType.ATTACHMENT, value="696969696")
        )

        value = option.resolve_to_attachment()

        assert value is mock_attachment

    @pytest.mark.parametrize("option_type", set(hikari.OptionType).difference({hikari.OptionType.ATTACHMENT}))
    def test_resolve_to_attachment_for_non_attachment_type(self, option_type: hikari.OptionType):
        option = tanjun.context.SlashOption(mock.Mock(), mock.Mock(type=option_type))

        with pytest.raises(TypeError):
            option.resolve_to_attachment()

    def test_resolve_to_channel(self):
        mock_channel = mock.Mock()
        mock_resolved = mock.Mock(channels={3123321: mock_channel})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.CHANNEL, value="3123321"))

        value = option.resolve_to_channel()

        assert value is mock_channel

    @pytest.mark.parametrize("option_type", set(hikari.OptionType).difference({hikari.OptionType.CHANNEL}))
    def test_resolve_to_channel_for_non_channel_type(self, option_type: hikari.OptionType):
        option = tanjun.context.SlashOption(mock.Mock(), mock.Mock(type=option_type))

        with pytest.raises(TypeError):
            option.resolve_to_channel()

    def test_resolve_to_member(self):
        mock_member = mock.Mock()
        mock_resolved = mock.Mock(members={421123: mock_member})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.USER, value="421123"))

        value = option.resolve_to_member()

        assert value is mock_member

    def test_resolve_to_member_when_user_only(self):
        mock_resolved = mock.Mock(members={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.USER, value="421123"))

        with pytest.raises(LookupError):
            option.resolve_to_member()

    def test_resolve_to_member_when_user_only_and_defaulting(self):
        mock_resolved = mock.Mock(members={})
        mock_result = mock.Mock()
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.USER, value="421123"))

        result = option.resolve_to_member(default=mock_result)

        assert result is mock_result

    def test_resolve_to_member_when_mentionable(self):
        mock_member = mock.Mock()
        mock_resolved = mock.Mock(members={1122: mock_member})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_member()

        assert result is mock_member

    def test_resolve_to_member_when_mentionable_and_user_only(self):
        mock_resolved = mock.Mock(users={1122: mock.Mock()}, members={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        with pytest.raises(LookupError):
            option.resolve_to_member()

    def test_resolve_to_member_when_mentionable_and_user_only_while_defaulting(self):
        mock_resolved = mock.Mock(members={}, users={1122: mock.Mock()})
        mock_default = mock.Mock()
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_member(default=mock_default)

        assert result is mock_default

    def test_resolve_to_member_when_mentionable_but_targets_role(self):
        mock_resolved = mock.Mock(members={}, users={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        with pytest.raises(TypeError):
            option.resolve_to_member(default=mock.Mock())

    @pytest.mark.parametrize(
        "option_type", set(hikari.OptionType).difference({hikari.OptionType.USER, hikari.OptionType.MENTIONABLE})
    )
    def test_resolve_to_member_when_not_member_type(self, option_type: hikari.OptionType):
        option = tanjun.context.SlashOption(mock.Mock(), mock.Mock(type=option_type))

        with pytest.raises(TypeError):
            option.resolve_to_member()

    def test_resolve_to_mentionable_for_role(self):
        mock_role = mock.Mock()
        mock_resolved = mock.Mock(roles={1122: mock_role}, users={}, members={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_mentionable()

        assert result is mock_role

    def test_resolve_to_mentionable_for_member(self):
        mock_member = mock.Mock()
        mock_resolved = mock.Mock(members={1122: mock_member}, roles={}, users={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_mentionable()

        assert result is mock_member

    def test_resolve_to_mentionable_when_user_only(self):
        mock_user = mock.Mock()
        mock_resolved = mock.Mock(users={1122: mock_user}, roles={}, members={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_mentionable()

        assert result is mock_user

    def test_resolve_to_mentionable_for_user_option_type(self):
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.USER)),
        )

        result = option.resolve_to_mentionable()

        assert result is resolve_to_user.return_value
        resolve_to_user.assert_called_once_with()
        resolve_to_role.assert_not_called()

    def test_resolve_to_mentionable_for_role_option_type(self):
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        option = stub_class(
            tanjun.context.SlashOption,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            args=(mock.Mock(), mock.Mock(type=hikari.OptionType.ROLE)),
        )

        result = option.resolve_to_mentionable()

        assert result is resolve_to_role.return_value
        resolve_to_role.assert_called_once_with()
        resolve_to_user.assert_not_called()

    @pytest.mark.parametrize(
        "option_type",
        set(hikari.OptionType).difference(
            {hikari.OptionType.USER, hikari.OptionType.MENTIONABLE, hikari.OptionType.ROLE}
        ),
    )
    def test_resolve_to_mentionable_when_not_mentionable(self, option_type: hikari.OptionType):
        option = tanjun.context.SlashOption(mock.Mock(), mock.Mock(type=option_type))

        with pytest.raises(TypeError):
            option.resolve_to_mentionable()

    def test_resolve_to_role(self):
        mock_role = mock.Mock()
        mock_resolved = mock.Mock(roles={21321: mock_role})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.ROLE, value="21321"))

        result = option.resolve_to_role()

        assert result is mock_role

    def test_resolve_to_role_when_mentionable(self):
        mock_role = mock.Mock()
        mock_resolved = mock.Mock(roles={21321: mock_role})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="21321"))

        result = option.resolve_to_role()

        assert result is mock_role

    def test_resolve_to_role_when_mentionable_but_targets_user(self):
        mock_resolved = mock.Mock(roles={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="21321"))

        with pytest.raises(TypeError):
            option.resolve_to_role()

    @pytest.mark.parametrize(
        "option_type", set(hikari.OptionType).difference({hikari.OptionType.MENTIONABLE, hikari.OptionType.ROLE})
    )
    def test_resolve_to_role_when_not_role(self, option_type: hikari.OptionType):
        mock_interaction = mock.Mock()
        option = tanjun.context.SlashOption(mock_interaction, mock.Mock(type=option_type, value="21321"))

        with pytest.raises(TypeError):
            option.resolve_to_role()

    def test_resolve_to_user(self):
        mock_user = mock.Mock()
        mock_resolved = mock.Mock(users={33333: mock_user}, members={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.USER, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_user

    def test_resolve_to_user_when_member_present(self):
        mock_member = mock.Mock()
        mock_resolved = mock.Mock(members={33333: mock_member}, users={33333: mock.Mock()})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_member

    @pytest.mark.parametrize(
        "option_type", set(hikari.OptionType).difference({hikari.OptionType.USER, hikari.OptionType.MENTIONABLE})
    )
    def test_resolve_to_user_when_not_user(self, option_type: hikari.OptionType):
        mock_interaction = mock.Mock()
        option = tanjun.context.SlashOption(mock_interaction, mock.Mock(type=option_type, value="33333"))

        with pytest.raises(TypeError):
            option.resolve_to_user()

    def test_resolve_to_user_when_mentionable(self):
        mock_user = mock.Mock()
        mock_resolved = mock.Mock(users={33333: mock_user}, members={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_user

    def test_resolve_to_user_when_mentionable_and_member_present(self):
        mock_member = mock.Mock()
        mock_resolved = mock.Mock(members={33333: mock_member}, users={33333: mock.Mock()})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_member

    def test_resolve_to_user_when_mentionable_but_targets_role(self):
        mock_resolved = mock.Mock(members={}, users={})
        option = tanjun.context.SlashOption(mock_resolved, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        with pytest.raises(TypeError):
            option.resolve_to_user()


class TestAppCommandContext:
    @pytest.fixture()
    def context(self, mock_client: mock.Mock) -> tanjun.context.slash.AppCommandContext:
        return stub_class(
            tanjun.context.slash.AppCommandContext,
            type=mock.Mock,
            mark_not_found=mock.AsyncMock(),
            args=(mock_client, mock.AsyncMock(options=None), mock.Mock()),
        )

    def test_author_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.author is context.interaction.user

    def test_channel_id_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.channel_id is context.interaction.channel_id

    def test_client_property(self, context: tanjun.abc.Context, mock_client: mock.Mock):
        assert context.client is mock_client

    def test_created_at_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.created_at is context.interaction.created_at

    def test_expires_at_property(self):
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            type=mock.Mock,
            mark_not_found=mock.AsyncMock(),
            args=(
                mock.Mock(),
                mock.Mock(
                    created_at=datetime.datetime(2021, 11, 15, 5, 42, 6, 445670, tzinfo=datetime.timezone.utc),
                    options=None,
                ),
                mock.Mock(),
            ),
        )

        assert context.expires_at == datetime.datetime(2021, 11, 15, 5, 57, 6, 445670, tzinfo=datetime.timezone.utc)

    def test_guild_id_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.guild_id is context.interaction.guild_id

    def test_has_been_deferred_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.has_been_deferred is context._has_been_deferred

    def test_has_responded_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.has_responded is context._has_responded

    def test_is_human_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.is_human is True

    def test_member_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.member is context.interaction.member

    def test_interaction_property(self, context: tanjun.context.slash.AppCommandContext):
        assert context.interaction is context._interaction

    @pytest.mark.asyncio()
    async def test__auto_defer(self, mock_client: mock.Mock):
        defer = mock.AsyncMock()
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            defer=defer,
            args=(mock_client, mock.Mock(options=None), mock.Mock()),
        )

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._auto_defer(0.1)

            sleep.assert_awaited_once_with(0.1)
            defer.assert_awaited_once_with()

    def test_cancel_defer(self, context: tanjun.context.slash.AppCommandContext):
        context._defer_task = mock.Mock()

        context.cancel_defer()

        context._defer_task.cancel.assert_called_once_with()

    def test_cancel_defer_when_no_active_task(self, context: tanjun.context.slash.AppCommandContext):
        context._defer_task = None
        context.cancel_defer()

    @pytest.mark.parametrize(("flags", "result"), [(hikari.UNDEFINED, hikari.MessageFlag.NONE), (6666, 6666)])
    def test__get_flags(
        self, context: tanjun.context.slash.AppCommandContext, flags: hikari.UndefinedOr[int], result: int
    ):
        context.set_ephemeral_default(False)

        assert context._get_flags(flags) == result

    @pytest.mark.parametrize(
        ("flags", "result"),
        [
            (hikari.UNDEFINED, hikari.MessageFlag.EPHEMERAL),
            (6666, 6666),
            (hikari.MessageFlag.NONE, hikari.MessageFlag.NONE),
        ],
    )
    def test__get_flags_when_defaulting_to_ephemeral(
        self, context: tanjun.context.slash.AppCommandContext, flags: hikari.UndefinedOr[int], result: int
    ):
        context.set_ephemeral_default(True)

        assert context._get_flags(flags) == result

    def test_start_defer_timer(self, mock_client: mock.Mock):
        auto_defer = mock.Mock()
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            _auto_defer=auto_defer,
            args=(mock_client, mock.Mock(options=None), mock.Mock()),
        )

        with mock.patch.object(asyncio, "create_task") as create_task:
            context.start_defer_timer(534123)

            auto_defer.assert_called_once_with(534123)
            create_task.assert_called_once_with(auto_defer.return_value)
            assert context._defer_task is create_task.return_value

    def test_start_defer_timer_when_already_started(self, context: tanjun.context.slash.AppCommandContext):
        context._defer_task = mock.Mock()

        with pytest.raises(RuntimeError):
            context.start_defer_timer(321)

    def test_start_defer_timer_when_finalised(self, context: tanjun.context.slash.AppCommandContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.start_defer_timer(123)

    def test_set_ephemeral_default(self, context: tanjun.context.slash.AppCommandContext):
        assert context.set_ephemeral_default(True) is context
        assert context.defaults_to_ephemeral is True

    def test_set_ephemeral_default_when_finalised(self, context: tanjun.context.slash.AppCommandContext):
        context.finalise()
        with pytest.raises(TypeError):
            context.set_ephemeral_default(True)

        assert context.defaults_to_ephemeral is False

    @pytest.mark.skip(reason="not implemented")
    async def test_defer_cancels_defer_when_not_in_defer_task(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    async def test_defer_doesnt_cancel_defer_when_in_deffer_task(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.asyncio()
    async def test__delete_followup_after(self, context: tanjun.context.slash.AppCommandContext):
        mock_message = mock.Mock()

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._delete_followup_after(543, mock_message)

            sleep.assert_awaited_once_with(543)

        assert isinstance(context.interaction.delete_message, mock.AsyncMock)
        context.interaction.delete_message.assert_awaited_once_with(mock_message)

    @pytest.mark.asyncio()
    async def test__delete_followup_after_handles_not_found_error(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        mock_message = mock.Mock()
        assert isinstance(context.interaction.delete_message, mock.AsyncMock)
        context.interaction.delete_message.side_effect = hikari.NotFoundError(url="", headers={}, raw_body=None)

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._delete_followup_after(543, mock_message)

            sleep.assert_awaited_once_with(543)

        context.interaction.delete_message.assert_awaited_once_with(mock_message)

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_followup(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.asyncio()
    async def test__delete_initial_response_after(self):
        mock_delete_initial_response = mock.AsyncMock()
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            type=mock.Mock(),
            mark_not_found=mock.AsyncMock,
            delete_initial_response=mock_delete_initial_response,
            args=(mock.Mock(), mock.Mock(options=None), mock.Mock()),
        )

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._delete_initial_response_after(123)

            sleep.assert_awaited_once_with(123)
            mock_delete_initial_response.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test__delete_initial_response_after_handles_not_found_error(self):
        mock_delete_initial_response = mock.AsyncMock(
            side_effect=hikari.NotFoundError(url="", headers={}, raw_body=None)
        )
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            delete_initial_response=mock_delete_initial_response,
            args=(mock.Mock(), mock.Mock(options=None), mock.Mock()),
        )

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._delete_initial_response_after(123)

            sleep.assert_awaited_once_with(123)
            mock_delete_initial_response.assert_awaited_once_with()

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_for_gateway_interaction(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_for_rest_interaction(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_when_already_responded(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_when_deferred(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_when_delete_after(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_when_delete_after_will_have_expired(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        ...

    @pytest.mark.asyncio()
    async def test_delete_initial_response(self, context: tanjun.context.slash.AppCommandContext):
        assert context.has_responded is False

        await context.delete_initial_response()

        assert isinstance(context.interaction.delete_initial_response, mock.AsyncMock)
        context.interaction.delete_initial_response.assert_awaited_once_with()
        assert context.has_responded is True

    @pytest.mark.asyncio()
    async def test_edit_initial_response(self, mock_client: mock.Mock):
        mock_interaction = mock.AsyncMock(created_at=datetime.datetime.now(tz=datetime.timezone.utc))
        mock_register_task = mock.Mock()
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            type=mock.Mock(),
            mark_not_found=mock.AsyncMock(),
            args=(mock_client, mock_interaction, mock_register_task),
        )

        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.edit_initial_response(
                "bye",
                attachment=mock_attachment,
                attachments=mock_attachments,
                component=mock_component,
                components=mock_components,
                embed=mock_embed,
                embeds=mock_embeds,
                mentions_everyone=True,
                user_mentions=[123],
                role_mentions=[444],
            )

        mock_interaction.edit_initial_response.assert_awaited_once_with(
            content="bye",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
            embed=mock_embed,
            embeds=mock_embeds,
            mentions_everyone=True,
            user_mentions=[123],
            role_mentions=[444],
        )
        create_task.assert_not_called()
        assert context.has_responded is True
        mock_register_task.assert_not_called()

    @pytest.mark.parametrize("delete_after", [datetime.timedelta(seconds=545), 545, 545.0])
    @pytest.mark.asyncio()
    async def test_edit_initial_response_when_delete_after(
        self, mock_client: mock.Mock, delete_after: typing.Union[datetime.timedelta, int, float]
    ):
        mock_delete_initial_response_after = mock.Mock()
        mock_interaction = mock.AsyncMock(created_at=datetime.datetime.now(tz=datetime.timezone.utc))
        mock_interaction.edit_initial_response.return_value.flags = hikari.MessageFlag.NONE
        mock_register_task = mock.Mock()
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            type=mock.Mock(),
            mark_not_found=mock.AsyncMock(),
            _delete_initial_response_after=mock_delete_initial_response_after,
            args=(mock_client, mock_interaction, mock_register_task),
        )

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.edit_initial_response("bye", delete_after=delete_after)

        mock_delete_initial_response_after.assert_called_once_with(545)
        create_task.assert_called_once_with(mock_delete_initial_response_after.return_value)
        mock_register_task.assert_called_once_with(create_task.return_value)

    @pytest.mark.parametrize("delete_after", [datetime.timedelta(seconds=901), 901, 901.0])
    @pytest.mark.asyncio()
    async def test_edit_initial_response_when_delete_after_will_have_expired(
        self, mock_client: mock.Mock, delete_after: typing.Union[datetime.timedelta, int, float]
    ):
        mock_delete_initial_response_after = mock.Mock()
        mock_register_task = mock.Mock()
        mock_interaction = mock.AsyncMock(created_at=datetime.datetime.now(tz=datetime.timezone.utc))
        context = stub_class(
            tanjun.context.slash.AppCommandContext,
            type=mock.Mock(),
            mark_not_found=mock.AsyncMock(),
            _delete_initial_response_after=mock_delete_initial_response_after,
            args=(mock_client, mock_interaction, mock_register_task),
        )

        with mock.patch.object(asyncio, "create_task") as create_task:
            with pytest.raises(ValueError, match="This interaction will have expired before delete_after is reached"):
                await context.edit_initial_response("bye", delete_after=delete_after)

        mock_delete_initial_response_after.assert_not_called()
        create_task.assert_not_called()
        mock_register_task.assert_not_called()

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_only_initial_response(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_initial_response_deferred(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_only_initial_response_or_deferred_and_delete_after(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_only_initial_response_or_deferred_and_delete_after_will_have_expired(
        self, context: tanjun.context.slash.AppCommandContext
    ):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_multiple_responses(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_no_previous_response(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.asyncio()
    async def test_fetch_initial_response(self, context: tanjun.context.slash.AppCommandContext):
        assert isinstance(context.interaction.fetch_initial_response, mock.AsyncMock)
        assert await context.fetch_initial_response() is context.interaction.fetch_initial_response.return_value
        context.interaction.fetch_initial_response.assert_awaited_once_with()

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_fetch_last_response(self, context: tanjun.context.slash.AppCommandContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_respond(self, context: tanjun.context.slash.AppCommandContext):
        ...


class TestSlashContext:
    @pytest.fixture()
    def context(self, mock_client: mock.Mock) -> tanjun.context.SlashContext:
        return tanjun.context.SlashContext(mock_client, mock.AsyncMock(options=None), mock.Mock())

    @pytest.mark.parametrize("raw_options", [None, []])
    def test_options_property_when_no_options(
        self, mock_client: mock.Mock, raw_options: typing.Optional[list[hikari.OptionType]]
    ):
        context = tanjun.context.SlashContext(
            mock_client, mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=raw_options), mock.Mock()
        )

        assert context.options == {}

    def test_options_property_for_top_level_command(self, mock_client: mock.Mock):
        mock_option_1 = mock.Mock()
        mock_option_1.name = "hi"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "bye"
        context = tanjun.context.SlashContext(
            mock_client,
            mock.Mock(options=[mock_option_1, mock_option_2]),
            mock.Mock(),
        )

        assert len(context.options) == 2
        assert context.options["hi"].type is mock_option_1.type
        assert context.options["hi"].value is mock_option_1.value
        assert context.options["hi"].name is mock_option_1.name
        assert isinstance(context.options["hi"], tanjun.context.SlashOption)

        assert context.options["bye"].type is mock_option_2.type
        assert context.options["bye"].value is mock_option_2.value
        assert context.options["bye"].name is mock_option_2.name
        assert isinstance(context.options["bye"], tanjun.context.SlashOption)

    def test_options_property_for_command_group(self, mock_client: mock.Mock):
        mock_option_1 = mock.Mock()
        mock_option_1.name = "kachow"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "nyaa"
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2])
        context = tanjun.context.SlashContext(mock_client, mock.Mock(options=[group_option]), mock.Mock())

        assert len(context.options) == 2
        assert context.options["kachow"].type is mock_option_1.type
        assert context.options["kachow"].value is mock_option_1.value
        assert context.options["kachow"].name is mock_option_1.name
        assert isinstance(context.options["kachow"], tanjun.context.SlashOption)

        assert context.options["nyaa"].type is mock_option_2.type
        assert context.options["nyaa"].value is mock_option_2.value
        assert context.options["nyaa"].name is mock_option_2.name
        assert isinstance(context.options["nyaa"], tanjun.context.SlashOption)

    @pytest.mark.parametrize("raw_options", [None, []])
    def test_options_property_for_command_group_with_no_sub_option(
        self, mock_client: mock.Mock, raw_options: typing.Optional[list[hikari.OptionType]]
    ):
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=raw_options)
        context = tanjun.context.SlashContext(mock_client, mock.Mock(options=[group_option]), mock.Mock())

        assert context.options == {}

    def test_options_property_for_sub_command_group(self, mock_client: mock.Mock):
        mock_option_1 = mock.Mock()
        mock_option_1.name = "meow"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "nya"
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2])
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        context = tanjun.context.SlashContext(mock_client, mock.Mock(options=[group_option]), mock.Mock())

        assert len(context.options) == 2
        assert context.options["meow"].type is mock_option_1.type
        assert context.options["meow"].value is mock_option_1.value
        assert context.options["meow"].name is mock_option_1.name
        assert isinstance(context.options["meow"], tanjun.context.SlashOption)

        assert context.options["nya"].type is mock_option_2.type
        assert context.options["nya"].value is mock_option_2.value
        assert context.options["nya"].name is mock_option_2.name
        assert isinstance(context.options["nya"], tanjun.context.SlashOption)

    @pytest.mark.parametrize("raw_options", [None, []])
    def test_options_property_for_sub_command_group_with_no_sub_option(
        self, mock_client: mock.Mock, raw_options: typing.Optional[list[hikari.OptionType]]
    ):
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=raw_options)
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        context = tanjun.context.SlashContext(mock_client, mock.Mock(options=[group_option]), mock.Mock())

        assert context.options == {}

    def test_triggering_name_property_for_top_level_command(self, context: tanjun.context.slash.SlashContext):
        assert context.triggering_name is context.interaction.command_name

    def test_triggering_name_property_for_sub_command(self, mock_client: mock.Mock):
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=None)
        group_option.name = "daniel"
        context = tanjun.context.SlashContext(
            mock_client, mock.Mock(command_name="damn", options=[group_option]), mock.Mock()
        )

        assert context.triggering_name == "damn daniel"

    def test_triggering_name_property_for_sub_sub_command(self, mock_client: mock.Mock):
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=None)
        sub_group_option.name = "nyaa"
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        group_option.name = "xes"
        context = tanjun.context.SlashContext(
            mock_client, mock.Mock(command_name="meow", options=[group_option]), mock.Mock()
        )

        assert context.triggering_name == "meow xes nyaa"

    def test_type_property(self, context: tanjun.context.SlashContext):
        assert context.type is hikari.CommandType.SLASH

    @pytest.mark.asyncio()
    async def test_mark_not_found(self):
        on_not_found = mock.AsyncMock()
        context = tanjun.context.SlashContext(
            mock.Mock(), mock.Mock(options=None), mock.Mock(), on_not_found=on_not_found
        )

        await context.mark_not_found()

        on_not_found.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test_mark_not_found_when_no_callback(self):
        context = tanjun.context.SlashContext(mock.Mock(), mock.Mock(options=None), mock.Mock(), on_not_found=None)

        await context.mark_not_found()

    @pytest.mark.asyncio()
    async def test_mark_not_found_when_already_marked_as_not_found(self):
        on_not_found = mock.AsyncMock()
        context = tanjun.context.SlashContext(
            mock.Mock(), mock.Mock(options=None), mock.Mock(), on_not_found=on_not_found
        )
        await context.mark_not_found()
        on_not_found.reset_mock()

        await context.mark_not_found()

        on_not_found.assert_not_called()

    def test_set_command(self, context: tanjun.context.SlashContext):
        mock_command = mock.Mock()

        assert context.set_command(mock_command) is context

        assert context.command is mock_command
        assert context.get_type_dependency(tanjun.abc.ExecutableCommand) is mock_command
        assert context.get_type_dependency(tanjun.abc.AppCommand) is mock_command
        assert context.get_type_dependency(tanjun.abc.BaseSlashCommand) is mock_command
        assert context.get_type_dependency(tanjun.abc.SlashCommand) is mock_command

    def test_set_command_when_none(self, context: tanjun.context.SlashContext):
        assert isinstance(context.injection_client.get_type_dependency, mock.Mock)
        context.injection_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        context.set_command(None)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_dependency(tanjun.abc.ExecutableCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.AppCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.BaseSlashCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.SlashCommand) is alluka.abc.UNDEFINED

    def test_set_command_when_none_and_previously_set(self, context: tanjun.context.SlashContext):
        assert isinstance(context.injection_client.get_type_dependency, mock.Mock)
        context.injection_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        mock_command = mock.Mock()
        context.set_command(mock_command)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_dependency(tanjun.abc.ExecutableCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.AppCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.BaseSlashCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.SlashCommand) is alluka.abc.UNDEFINED

    def test_set_command_when_finalised(self, context: tanjun.context.SlashContext):
        context.finalise()
        mock_command = mock.Mock()

        with pytest.raises(TypeError):
            context.set_command(mock_command)

        assert context.command is not mock_command
