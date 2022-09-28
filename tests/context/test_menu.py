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

from unittest import mock

import hikari
import pytest

import tanjun


class TestMenuContext:
    @pytest.fixture()
    def mock_client(self) -> tanjun.Client:
        return mock.AsyncMock(tanjun.Client)

    @pytest.fixture()
    def mock_interaction(self) -> hikari.CommandInteraction:
        return mock.Mock()

    @pytest.fixture()
    def context(
        self, mock_client: tanjun.Client, mock_interaction: hikari.CommandInteraction
    ) -> tanjun.context.MenuContext:
        return tanjun.context.MenuContext(mock_client, mock_interaction, mock.Mock())

    def test_command_property(self, mock_client: tanjun.Client, mock_interaction: hikari.CommandInteraction):
        context = tanjun.context.MenuContext(mock_client, mock_interaction, mock.Mock())

        assert context.command is None

    def test_target_id_property_when_user_menu(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {12354123: mock.Mock()}
        mock_interaction.resolved.messages = {}

        assert context.target_id == 12354123

    def test_target_id_property_when_message_menu(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {}
        mock_interaction.resolved.messages = {65123123: mock.Mock()}

        assert context.target_id == 65123123

    def test_target_id_property_when_unknown_menu_type(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {}
        mock_interaction.resolved.messages = {}

        with pytest.raises(RuntimeError, match="Unknown menu type"):
            context.target_id

    def test_target_property_when_user_menu(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        mock_user = mock.Mock()
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {54123543: mock_user}
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.messages = {}

        assert context.target is mock_user

    def test_target_property_when_user_menu_and_member(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        mock_member = mock.Mock()
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {54123543: mock.Mock()}
        mock_interaction.resolved.members = {54123543: mock_member}
        mock_interaction.resolved.messages = {}

        assert context.target is mock_member

    def test_target_property_when_message_menu(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        mock_message = mock.Mock()
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {}
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.messages = {651234: mock_message}

        assert context.target is mock_message

    def test_target_property_when_unknown_menu_type(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction.resolved, mock.Mock)
        mock_interaction.resolved.users = {}
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.messages = {}

        with pytest.raises(RuntimeError, match="Unknown menu type"):
            context.target

    def test_triggering_name_property(self, context: tanjun.context.menu.MenuContext):
        assert context.triggering_name is context.interaction.command_name

    @pytest.mark.parametrize("command_type", [hikari.CommandType.MESSAGE, hikari.CommandType.USER])
    def test_type_property(
        self,
        context: tanjun.context.MenuContext,
        mock_interaction: hikari.CommandInteraction,
        command_type: hikari.CommandType,
    ):
        mock_interaction.command_type = command_type

        assert context.type is mock_interaction.command_type

    @pytest.mark.asyncio()
    async def test_mark_not_found(self):
        on_not_found = mock.AsyncMock()
        context = tanjun.context.MenuContext(
            mock.Mock(), mock.Mock(options=None), mock.Mock(), on_not_found=on_not_found
        )

        await context.mark_not_found()

        on_not_found.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test_mark_not_found_when_no_callback(self):
        context = tanjun.context.MenuContext(mock.Mock(), mock.Mock(options=None), mock.Mock(), on_not_found=None)

        await context.mark_not_found()

    @pytest.mark.asyncio()
    async def test_mark_not_found_when_already_marked_as_not_found(self):
        on_not_found = mock.AsyncMock()
        context = tanjun.context.MenuContext(
            mock.Mock(), mock.Mock(options=None), mock.Mock(), on_not_found=on_not_found
        )
        await context.mark_not_found()
        on_not_found.reset_mock()

        await context.mark_not_found()

        on_not_found.assert_not_called()

    def test_set_command(self, context: tanjun.context.MenuContext):
        mock_command = mock.Mock()

        result = context.set_command(mock_command)

        assert context.command is mock_command
        assert result is context

    def test_resolve_to_member(self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction):
        mock_member = mock.Mock()
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {123534: mock_member}
        mock_interaction.resolved.users = {123534: mock.Mock()}

        result = context.resolve_to_member()

        assert result is mock_member

    def test_resolve_to_member_when_not_user_type(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {}

        with pytest.raises(TypeError, match="Cannot resolve message menu context to a user"):
            context.resolve_to_member()

    def test_resolve_to_member_when_user_but_no_member(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {1235432: mock.Mock()}

        with pytest.raises(LookupError, match="User isn't in the current guild"):
            context.resolve_to_member()

    def test_resolve_to_member_when_user_but_no_member_and_default(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {1235432: mock.Mock()}
        mock_default = mock.Mock()

        result = context.resolve_to_member(default=mock_default)

        assert result is mock_default

    def test_resolve_to_message(self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction):
        mock_message = mock.Mock()
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.messages = {3421123: mock_message}

        result = context.resolve_to_message()

        assert result is mock_message

    def test_resolve_to_message_when_not_message_type(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.messages = {}

        with pytest.raises(TypeError, match="Cannot resolve user menu context to a message"):
            context.resolve_to_message()

    def test_resolve_to_user(self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction):
        mock_user = mock.Mock()
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {4132123: mock_user}

        result = context.resolve_to_user()

        assert result is mock_user

    def test_resolve_to_user_when_member(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        mock_member = mock.Mock()
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {123534: mock_member}
        mock_interaction.resolved.users = {123534: mock.Mock()}

        result = context.resolve_to_user()

        assert result is mock_member

    def test_resolve_to_user_when_not_user_type(
        self, context: tanjun.context.MenuContext, mock_interaction: hikari.CommandInteraction
    ):
        assert isinstance(mock_interaction, mock.Mock)
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {}

        with pytest.raises(TypeError, match="Cannot resolve message menu context to a user"):
            context.resolve_to_user()
