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
import asyncio
import importlib
import inspect
import pathlib
import shutil
import sys
import tempfile
import textwrap
import typing
import uuid
from collections import abc as collections
from unittest import mock

import hikari
import pytest
import typing_extensions

import tanjun


class TestMessageAcceptsEnum:
    @pytest.mark.parametrize(
        ("value", "expected_type"),
        [
            (tanjun.MessageAcceptsEnum.ALL, hikari.MessageCreateEvent),
            (tanjun.MessageAcceptsEnum.DM_ONLY, hikari.DMMessageCreateEvent),
            (tanjun.MessageAcceptsEnum.GUILD_ONLY, hikari.GuildMessageCreateEvent),
            (tanjun.MessageAcceptsEnum.NONE, None),
        ],
    )
    def test_get_event_type(self, value: tanjun.MessageAcceptsEnum, expected_type: typing.Optional[hikari.Event]):
        assert value.get_event_type() == expected_type


class Test_LoaderDescriptor:
    def test_has_load_property(self):
        loader = tanjun.as_loader(mock.Mock())
        assert isinstance(loader, tanjun.clients._LoaderDescriptor)

        assert loader.has_load is True

    def test_has_unload_property(self):
        loader = tanjun.as_loader(mock.Mock())
        assert isinstance(loader, tanjun.clients._LoaderDescriptor)

        assert loader.has_unload is False

    def test___call__(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.as_loader(mock_callback)

        descriptor(1, "3", 3, a=31, e="43")  # type: ignore

        mock_callback.assert_called_once_with(1, "3", 3, a=31, e="43")

    def test_load(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock(tanjun.Client)
        descriptor = tanjun.as_loader(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        result = descriptor.load(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_load_when_called_as_decorator(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock(tanjun.Client)
        descriptor = tanjun.as_loader()(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        result = descriptor.load(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_load_when_called_as_decorator_and_args_passed(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock(tanjun.Client)
        descriptor = tanjun.as_loader(standard_impl=True)(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        result = descriptor.load(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_load_when_must_be_std_and_not_std(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.as_loader(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        with pytest.raises(ValueError, match="This loader requires instances of the standard Client implementation"):
            descriptor.load(mock.Mock())

        mock_callback.assert_not_called()

    def test_load_when_abc_allowed(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock()
        descriptor = tanjun.as_loader(mock_callback, standard_impl=False)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.abc.Client], None])
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        result = descriptor.load(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_load_when_abc_allowed_and_called_as_decorator(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock()
        descriptor = tanjun.as_loader(standard_impl=False)(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.abc.Client], None])
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        result = descriptor.load(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_unload(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.as_loader(mock_callback)
        assert isinstance(descriptor, tanjun.clients._LoaderDescriptor)

        result = descriptor.unload(mock.Mock(tanjun.Client))

        assert result is False
        mock_callback.assert_not_called()


class Test_UnloaderDescriptor:
    def test_has_load_property(self):
        loader = tanjun.as_unloader(mock.Mock())
        assert isinstance(loader, tanjun.clients._UnloaderDescriptor)

        assert loader.has_load is False

    def test_has_unload_property(self):
        loader = tanjun.as_unloader(mock.Mock())
        assert isinstance(loader, tanjun.clients._UnloaderDescriptor)

        assert loader.has_unload is True

    def test___call__(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.as_unloader(mock_callback)

        descriptor(1, "2", 3, a=31, b="312")  # type: ignore

        mock_callback.assert_called_once_with(1, "2", 3, a=31, b="312")

    def test_load(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.as_unloader(mock_callback)
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        result = descriptor.load(mock.Mock(tanjun.Client))

        assert result is False
        mock_callback.assert_not_called()

    def test_unload(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock(tanjun.Client)
        descriptor = tanjun.as_unloader(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        result = descriptor.unload(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_unload_when_called_as_decorator(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock(tanjun.Client)
        descriptor = tanjun.as_unloader()(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        result = descriptor.unload(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_unload_called_as_decorator_and_args_passed(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock(tanjun.Client)
        descriptor = tanjun.as_unloader(standard_impl=True)(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        result = descriptor.unload(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_unload_when_must_be_std_and_not_std(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.as_unloader(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.Client], None])
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        with pytest.raises(ValueError, match="This unloader requires instances of the standard Client implementation"):
            descriptor.unload(mock.Mock())

        mock_callback.assert_not_called()

    def test_unload_when_abc_allowed(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock()
        descriptor = tanjun.as_unloader(mock_callback, standard_impl=False)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.abc.Client], None])
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        result = descriptor.unload(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)

    def test_unload_when_abc_allowed_and_called_as_decorator(self):
        mock_callback = mock.Mock()
        mock_client = mock.Mock()
        descriptor = tanjun.as_unloader(standard_impl=False)(mock_callback)
        typing_extensions.assert_type(descriptor, collections.Callable[[tanjun.abc.Client], None])
        assert isinstance(descriptor, tanjun.clients._UnloaderDescriptor)

        result = descriptor.unload(mock_client)

        assert result is True
        mock_callback.assert_called_once_with(mock_client)


class TestClient:
    @pytest.mark.skip(reason="TODO")
    def test___init__(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_from_gateway_bot(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_from_rest_bot(self):
        ...

    def test_from_rest_bot_when_bot_managed(self):
        mock_bot = mock.Mock()

        client = tanjun.Client.from_rest_bot(mock_bot, bot_managed=True)

        mock_bot.add_startup_callback.assert_called_once_with(client._on_starting)
        mock_bot.add_shutdown_callback.assert_called_once_with(client._on_stopping)

    @pytest.mark.skip(reason="TODO")
    def test___repr__(self):
        ...

    @pytest.mark.asyncio()
    async def test__on_starting(self):
        mock_open = mock.AsyncMock()
        mock_rest = mock.AsyncMock()

        class TestClient(tanjun.Client):
            open = mock_open

        client = TestClient(mock_rest)

        await client._on_starting(mock.Mock())

        mock_open.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test__on_stopping(self):
        mock_close = mock.AsyncMock()
        mock_rest = mock.AsyncMock()

        class TestClient(tanjun.Client):
            close = mock_close

        client = TestClient(mock_rest)

        await client._on_stopping(mock.Mock())

        mock_close.assert_awaited_once_with()

    @pytest.mark.skip(reason="TODO")
    def test__schedule_startup_registers(self):
        ...

    @pytest.mark.asyncio()
    async def test__add_task(self):
        mock_task_1 = mock.Mock()
        mock_task_2 = mock.Mock()
        mock_task_3 = mock.Mock()
        mock_new_task = asyncio.create_task(asyncio.sleep(50))
        client = tanjun.Client(mock.AsyncMock())
        client._tasks = [mock_task_1, mock_task_2, mock_task_3]

        client._add_task(mock_new_task)

        assert client._tasks == [mock_task_1, mock_task_2, mock_task_3, mock_new_task]

        mock_new_task.cancel()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0.1)

        assert client._tasks == [mock_task_1, mock_task_2, mock_task_3]

    @pytest.mark.asyncio()
    async def test__add_task_when_empty(self):
        mock_task = asyncio.create_task(asyncio.sleep(50))
        client = tanjun.Client(mock.AsyncMock())

        client._add_task(mock_task)

        assert client._tasks == [mock_task]

        mock_task.cancel()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0.1)

        assert client._tasks == []

    @pytest.mark.asyncio()
    async def test__add_task_when_task_already_done(self):
        mock_task = asyncio.create_task(asyncio.sleep(50))
        mock_task.cancel()
        # This is done to allow any finished tasks to be removed.
        await asyncio.sleep(0)

        client = tanjun.Client(mock.AsyncMock())

        client._add_task(mock_task)
        assert client._tasks == []

    @pytest.mark.asyncio()
    async def test_context_manager(self):
        open_ = mock.AsyncMock()
        close_ = mock.AsyncMock()

        class MockClient(tanjun.Client):
            open = open_
            close = close_

        async with MockClient(mock.Mock()):
            open_.assert_awaited_once_with()
            close_.assert_not_called()

        open_.assert_awaited_once_with()
        close_.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_async_context_manager(self) -> None:
        open_ = mock.AsyncMock()
        close_ = mock.AsyncMock()

        class StudClient(tanjun.Client):
            __slots__ = ()
            open = open_
            close = close_

        client = StudClient(mock.Mock())
        async with client:
            open_.assert_called_once_with()
            close_.assert_not_called()

        open_.assert_called_once_with()
        close_.assert_called_once_with()

    def test_interaction_accepts_property(self) -> None:
        client = tanjun.Client(mock.Mock()).set_interaction_accepts(tanjun.InteractionAcceptsEnum.COMMANDS)

        assert client.interaction_accepts is tanjun.InteractionAcceptsEnum.COMMANDS

    def test_message_accepts_property(self) -> None:
        client = tanjun.Client(mock.Mock(), events=mock.Mock()).set_message_accepts(tanjun.MessageAcceptsEnum.DM_ONLY)

        assert client.message_accepts is tanjun.MessageAcceptsEnum.DM_ONLY

    def test_is_human_only_property(self) -> None:
        client = tanjun.Client(mock.Mock()).set_human_only(True)

        assert client.is_human_only is True

    def test_cache_property(self) -> None:
        mock_cache = mock.Mock()
        client = tanjun.Client(mock.Mock(), cache=mock_cache)

        assert client.cache is mock_cache

    def test_events_property(self) -> None:
        mock_events = mock.Mock()
        client = tanjun.Client(mock.Mock(), events=mock_events)

        assert client.events is mock_events

    def test_default_app_cmd_permissions_property(self) -> None:
        assert tanjun.Client(mock.Mock()).default_app_cmd_permissions == hikari.Permissions.NONE

    def test_defaults_to_ephemeral_property(self) -> None:
        assert tanjun.Client(mock.Mock()).defaults_to_ephemeral is False

    def test_dms_enabled_for_app_cmds(self) -> None:
        assert tanjun.Client(mock.Mock()).dms_enabled_for_app_cmds is True

    def test_hooks_property(self) -> None:
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock()).set_hooks(mock_hooks)

        assert client.hooks is mock_hooks

    def test_slash_hooks_property(self) -> None:
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock()).set_slash_hooks(mock_hooks)

        assert client.slash_hooks is mock_hooks

    def test_is_alive_property(self) -> None:
        client = tanjun.Client(mock.Mock())

        assert client.is_alive is False

    def test_loop_property(self) -> None:
        mock_loop = mock.Mock()
        client = tanjun.Client(mock.Mock())
        client._loop = mock_loop

        assert client.loop is mock_loop

    def test_message_hooks_property(self) -> None:
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock()).set_message_hooks(mock_hooks)

        assert client.message_hooks is mock_hooks

    def test_metadata_property(self) -> None:
        client = tanjun.Client(mock.Mock())
        client.metadata["a"] = 234
        client.metadata["555"] = 542

        assert client.metadata == {"a": 234, "555": 542}

    def test_prefix_getter_property(self) -> None:
        mock_callback = mock.Mock()
        assert tanjun.Client(mock.Mock()).set_prefix_getter(mock_callback).prefix_getter is mock_callback

    def test_prefix_getter_property_when_no_getter(self) -> None:
        assert tanjun.Client(mock.Mock()).prefix_getter is None

    def test_rest_property(self) -> None:
        mock_rest = mock.Mock()
        client = tanjun.Client(mock_rest)

        assert client.rest is mock_rest

    def test_server_property(self) -> None:
        mock_server = mock.Mock()
        client = tanjun.Client(mock.Mock, server=mock_server)

        assert client.server is mock_server

    def test_server_property_when_none(self) -> None:
        client = tanjun.Client(mock.Mock)

        assert client.server is None

    def test_shards_property(self) -> None:
        mock_shards = mock.Mock()
        client = tanjun.Client(mock.Mock(), shards=mock_shards)

        assert client.shards is mock_shards

    def test_shards_property_when_none(self) -> None:
        client = tanjun.Client(mock.Mock())

        assert client.shards is None

    def test_voice_property(self) -> None:
        mock_voice = mock.Mock()
        client = tanjun.Client(mock.Mock(), voice=mock_voice)

        assert client.voice is mock_voice

    def test_voice_property_when_none(self) -> None:
        client = tanjun.Client(mock.Mock())

        assert client.voice is None

    @pytest.mark.asyncio()
    async def test_declare_application_command_when_command_id_provided(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        rest.edit_application_command.return_value = mock.Mock()
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, 123321, application=54123, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            54123,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.create_slash_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_when_command_id_provided_and_slash_command(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        rest.edit_application_command.return_value = mock.Mock(hikari.SlashCommand)
        mock_command = mock.Mock()

        result = await client.declare_application_command(mock_command, 123321, application=54123, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            54123,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=hikari.UNDEFINED,
            options=hikari.UNDEFINED,
        )
        rest.create_slash_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_when_command_id_provided_for_slash_builder(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        rest.edit_application_command.return_value = mock.Mock(hikari.SlashCommand)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, 123321, application=54123, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            54123,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.create_slash_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_when_command_id_provided_and_cached_app_id(self):
        rest = mock.AsyncMock()
        rest.edit_application_command.return_value = mock.Mock(hikari.SlashCommand)
        client = tanjun.Client(rest)
        client._cached_application_id = hikari.Snowflake(54123123)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, 123321, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            54123123,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.create_slash_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_when_command_id_provided_fetchs_app_id(self):
        fetch_rest_application_id_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            fetch_rest_application_id = fetch_rest_application_id_

        rest = mock.AsyncMock()
        rest.edit_application_command.return_value = mock.Mock(hikari.SlashCommand)
        client = StubClient(rest)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, 123321, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            fetch_rest_application_id_.return_value,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        fetch_rest_application_id_.assert_called_once_with()
        rest.create_slash_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, application=54123, guild=65234)

        assert result is mock_command.build.return_value.create.return_value
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.build.return_value.set_default_member_permissions.assert_not_called()
        mock_command.build.return_value.set_is_dm_enabled.assert_not_called()
        mock_command.build.return_value.create.assert_awaited_once_with(rest, 54123, guild=65234)
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_inherits_config(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest).set_default_app_command_permissions(213321).set_dms_enabled_for_app_cmds(False)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(
            hikari.api.SlashCommandBuilder, default_member_permissions=hikari.UNDEFINED, is_dm_enabled=hikari.UNDEFINED
        )

        result = await client.declare_application_command(mock_command, application=54123, guild=65234)

        assert result is mock_command.build.return_value.create.return_value
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.build.return_value.set_default_member_permissions.assert_called_once_with(213321)
        mock_command.build.return_value.set_is_dm_enabled.assert_called_once_with(False)
        mock_command.build.return_value.create.assert_awaited_once_with(rest, 54123, guild=65234)
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_when_cached_app_id(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        client._cached_application_id = hikari.Snowflake(54123123)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, guild=65234)

        assert result is mock_command.build.return_value.create.return_value
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.build.return_value.create.assert_awaited_once_with(rest, 54123123, guild=65234)
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_application_command_fetchs_app_id(self):
        fetch_rest_application_id_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            fetch_rest_application_id = fetch_rest_application_id_

        rest = mock.AsyncMock()
        client = StubClient(rest)
        mock_command = mock.Mock()
        mock_command.build.return_value = mock.Mock(hikari.api.SlashCommandBuilder)

        result = await client.declare_application_command(mock_command, guild=65234)

        assert result is mock_command.build.return_value.create.return_value
        fetch_rest_application_id_.assert_called_once_with()
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.build.return_value.create.assert_awaited_once_with(
            rest, fetch_rest_application_id_.return_value, guild=65234
        )
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_declare_application_commands(self):
        ...

    def test_set_set_default_app_command_permissions(self):
        client = tanjun.Client(mock.Mock())

        result = client.set_default_app_command_permissions(hikari.Permissions(5421123))

        assert result is client
        assert client.default_app_cmd_permissions == 5421123

    def test_set_default_app_command_permissions(self):
        client = tanjun.Client(mock.Mock())

        result = client.set_dms_enabled_for_app_cmds(False)

        assert result is client
        assert client.dms_enabled_for_app_cmds is False

    @pytest.mark.skip(reason="TODO")
    def test_set_hikari_trait_injectors(self):
        ...

    def test_set_interaction_not_found(self):
        mock_set_menu_not_found = mock.Mock()
        mock_set_slash_not_found = mock.Mock()
        mock_message = mock.Mock()

        class Client(tanjun.Client):
            set_menu_not_found = mock_set_menu_not_found
            set_slash_not_found = mock_set_slash_not_found

        client = Client(mock.Mock())
        mock_set_slash_not_found.return_value = mock_set_menu_not_found.return_value = client

        result = client.set_interaction_not_found(mock_message)

        assert result is client
        mock_set_menu_not_found.assert_called_once_with(mock_message)
        mock_set_slash_not_found.assert_called_once_with(mock_message)

    @pytest.mark.asyncio()
    async def test_set_interaction_accepts_when_running(self):
        client = tanjun.Client(mock.AsyncMock())
        await client.open()

        with pytest.raises(RuntimeError, match="Cannot change this config while the client is running"):
            client.set_interaction_accepts(tanjun.InteractionAcceptsEnum.NONE)

    @pytest.mark.asyncio()
    async def test_set_message_accepts_when_running(self):
        client = tanjun.Client(mock.AsyncMock(), events=mock.Mock())
        await client.open()

        with pytest.raises(RuntimeError, match="Cannot change this config while the client is running"):
            client.set_message_accepts(tanjun.MessageAcceptsEnum.NONE)

    def test_set_metadata(self):
        client = tanjun.Client(mock.Mock())
        key = mock.Mock()
        value = mock.Mock()

        result = client.set_metadata(key, value)

        assert result is client
        assert client.metadata[key] is value

    @pytest.mark.skip(reason="TODO")
    async def test_clear_commands(self):
        ...

    @pytest.mark.skip(reason="TODO")
    async def test_set_global_commands(self):
        ...

    @pytest.mark.skip(reason="TODO")
    async def test_declare_global_commands(self):
        ...

    def test_add_check(self):
        mock_check = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.add_check(mock_check)

        assert result is client
        assert mock_check in client.checks

    def test_add_check_when_already_present(self):
        mock_check = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check)

        result = client.add_check(mock_check)

        assert result is client
        assert list(client.checks).count(mock_check) == 1

    def test_remove_check(self):
        mock_check = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check)

        result = client.remove_check(mock_check)

        assert result is client
        assert mock_check not in client.checks

    def test_remove_check_when_not_present(self):
        mock_check = mock.Mock()
        client = tanjun.Client(mock.Mock())

        with pytest.raises(ValueError, match=".+"):
            client.remove_check(mock_check)

        assert mock_check not in client.checks

    def test_with_check(self):
        mock_check = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.with_check(mock_check)

        assert result is mock_check
        assert result in client.checks

    def test_with_check_when_already_present(self):
        mock_check = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check)

        result = client.with_check(mock_check)

        assert result is mock_check
        assert list(client.checks).count(mock_check) == 1

    @pytest.mark.asyncio()
    async def test_check(self):
        mock_check_1 = mock.Mock()
        mock_check_2 = mock.Mock()
        mock_check_3 = mock.Mock()
        mock_context = mock.Mock()
        mock_context.call_with_async_di = mock.AsyncMock(return_value=True)
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        assert await client.check(mock_context) is True

        mock_context.call_with_async_di.assert_has_awaits(
            [
                mock.call(mock_check_1, mock_context),
                mock.call(mock_check_2, mock_context),
                mock.call(mock_check_3, mock_context),
            ]
        )

    @pytest.mark.asyncio()
    async def test_check_when_one_returns_false(self):
        mock_check_1 = mock.Mock()
        mock_check_2 = mock.Mock()
        mock_check_3 = mock.Mock()
        mock_context = mock.Mock()
        mock_context.call_with_async_di = mock.AsyncMock(side_effect=[True, True, False])
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        assert await client.check(mock_context) is False

        mock_context.call_with_async_di.assert_has_awaits(
            [
                mock.call(mock_check_1, mock_context),
                mock.call(mock_check_2, mock_context),
                mock.call(mock_check_3, mock_context),
            ]
        )

    @pytest.mark.asyncio()
    async def test_check_when_one_raises(self):
        mock_check_1 = mock.Mock()
        mock_check_2 = mock.Mock()
        mock_check_3 = mock.Mock()
        mocK_exception = Exception("test")
        mock_context = mock.Mock()
        mock_context.call_with_async_di = mock.AsyncMock(side_effect=[True, mocK_exception, False])
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        with pytest.raises(Exception, match="test") as exc:
            await client.check(mock_context)

        assert exc.value is mocK_exception

        mock_context.call_with_async_di.assert_has_awaits(
            [
                mock.call(mock_check_1, mock_context),
                mock.call(mock_check_2, mock_context),
                mock.call(mock_check_3, mock_context),
            ]
        )

    @pytest.mark.asyncio()
    async def test_check_when_one_raises_failed_check(self):
        mock_check_1 = mock.Mock()
        mock_check_2 = mock.Mock()
        mock_check_3 = mock.Mock()
        mock_context = mock.Mock()
        mock_context.call_with_async_di = mock.AsyncMock(side_effect=[True, tanjun.FailedCheck(), False])
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        assert await client.check(mock_context) is False

        mock_context.call_with_async_di.assert_has_awaits(
            [
                mock.call(mock_check_1, mock_context),
                mock.call(mock_check_2, mock_context),
                mock.call(mock_check_3, mock_context),
            ]
        )

    @pytest.mark.skip(reason="TODO")
    def test_add_component(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_component_when_already_present(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_component_when_is_alive(self):
        ...

    def test_get_component_by_name(self):
        mock_component = mock.Mock()
        mock_component.name = "vader"
        client = (
            tanjun.Client(mock.Mock())
            .add_component(mock.Mock())
            .add_component(mock_component)
            .add_component(mock.Mock())
        )

        assert client.get_component_by_name("vader") is mock_component

    def test_get_component_by_name_when_not_present(self):
        assert tanjun.Client(mock.AsyncMock()).get_component_by_name("test") is None

    @pytest.mark.skip(reason="TODO")
    def test_remove_component(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_component_when_not_present(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_component_when_is_alive(self):
        ...

    def test_remove_component_by_name(self):
        remove_component_ = mock.Mock()
        mock_add_task = mock.Mock()

        class StubClient(tanjun.Client):
            remove_component = remove_component_
            _add_task = mock_add_task

        mock_component = mock.Mock()
        mock_component.name = "aye"
        client = StubClient(mock.AsyncMock).add_component(mock.Mock()).add_component(mock_component)
        remove_component_.return_value = client

        result = client.remove_component_by_name("aye")

        assert result is client
        remove_component_.assert_called_once_with(mock_component)
        mock_add_task.assert_not_called()

    def test_remove_component_by_name_when_not_present(self):
        client = tanjun.Client(mock.AsyncMock())

        with pytest.raises(KeyError):
            client.remove_component_by_name("nyan")

    @pytest.mark.skip(reason="TODO")
    def test_add_client_callback(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_client_callback_when_already_present(self):
        ...

    @pytest.mark.asyncio()
    async def test_dispatch_client_callback(self):
        ...

    @pytest.mark.asyncio()
    async def test_dispatch_client_callback_when_name_not_found(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_get_client_callbacks(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_get_client_callbacks_when_name_not_found(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_client_callback(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_client_callback_when_name_not_found(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_client_callback_when_callback_not_found(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_client_callback_when_last_callback(self):
        ...

    def test_with_client_callback(self):
        add_client_callback_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_client_callback = add_client_callback_

        client = StubClient(mock.Mock())
        add_client_callback_.reset_mock()
        mock_callback = mock.Mock()

        result = client.with_client_callback("aye")(mock_callback)

        assert result is mock_callback
        add_client_callback_.assert_called_once_with("aye", mock_callback)

    @pytest.mark.skip(reason="TODO")
    def test_add_listener(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_listener_when_already_present(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_listener_when_alive(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_listener_when_alive_and_events(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_listener_when_events(self):
        ...

    def test_remove_listener(self):
        mock_callback = mock.Mock()
        client = (
            tanjun.Client(mock.Mock())
            .add_listener(hikari.GuildTypingEvent, mock_callback)
            .add_listener(hikari.GuildTypingEvent, mock.Mock())
        )

        result = client.remove_listener(hikari.GuildTypingEvent, mock_callback)

        assert result is client
        assert mock_callback not in client.listeners[hikari.GuildTypingEvent]

    def test_remove_listener_when_event_type_not_present(self):
        client = tanjun.Client(mock.Mock())

        with pytest.raises(KeyError):
            client.remove_listener(hikari.GuildTypingEvent, mock.Mock())

    def test_remove_listener_when_callback_not_present(self):
        mock_other_callback = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_listener(hikari.GuildTypingEvent, mock_other_callback)

        with pytest.raises(ValueError, match=".+"):
            client.remove_listener(hikari.GuildTypingEvent, mock.Mock())

        assert client.listeners[hikari.GuildTypingEvent] == [mock_other_callback]

    def test_remove_listener_when_last_listener(self):
        mock_callback = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_listener(hikari.RoleEvent, mock_callback)

        client.remove_listener(hikari.RoleEvent, mock_callback)

        assert hikari.RoleEvent not in client.listeners

    def test_remove_listener_when_alive(self):
        mock_callback = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_listener(hikari.RoleEvent, mock_callback)
        client._loop = mock.Mock()

        client.remove_listener(hikari.RoleEvent, mock_callback)

        assert hikari.RoleEvent not in client.listeners

    def test_remove_listener_when_alive_and_events(self):
        mock_events = mock.Mock()
        mock_injector = mock.Mock()
        mock_callback = mock.Mock()
        client = tanjun.Client(
            mock.Mock(), events=mock_events, event_managed=False, injector=mock_injector
        ).add_listener(hikari.RoleEvent, mock_callback)
        client._loop = mock.Mock()

        client.remove_listener(hikari.RoleEvent, mock_callback)

        assert hikari.RoleEvent not in client.listeners
        mock_events.unsubscribe.assert_called_once_with(
            hikari.RoleEvent, mock_injector.as_async_self_injecting.return_value.__call__
        )

    def test_remove_listener_when_events(self):
        mock_events = mock.Mock()
        mock_callback = mock.Mock()
        client = tanjun.Client(mock.Mock(), events=mock_events, event_managed=False).add_listener(
            hikari.RoleEvent, mock_callback
        )

        client.remove_listener(hikari.RoleEvent, mock_callback)

        assert hikari.RoleEvent not in client.listeners
        mock_events.unsubscribe.assert_not_called()

    def test_with_listener(self):
        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())
        mock_callback = mock.Mock()

        result = client.with_listener(hikari.GuildAvailableEvent)(mock_callback)

        assert result is mock_callback
        add_listener_.assert_called_once_with(hikari.GuildAvailableEvent, mock_callback)

    def test_with_listener_no_provided_event(self):
        async def callback(foo) -> None:  # type: ignore
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        with pytest.raises(ValueError, match="Missing event argument annotation"):
            client.with_listener()(callback)

        add_listener_.assert_not_called()

    def test_with_listener_no_provided_event_callback_has_no_signature(self):
        with pytest.raises(ValueError, match=".+"):
            inspect.Signature.from_callable(int)

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        with pytest.raises(ValueError, match="Missing event type"):
            client.with_listener()(int)  # type: ignore

        add_listener_.assert_not_called()

    def test_with_listener_missing_positional_event_arg(self):
        async def callback(*, event: hikari.Event, **kwargs: str) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        with pytest.raises(ValueError, match="Missing positional event argument"):
            client.with_listener()(callback)

        add_listener_.assert_not_called()

    def test_with_listener_no_args(self):
        async def callback() -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        with pytest.raises(ValueError, match="Missing positional event argument"):
            client.with_listener()(callback)

        add_listener_.assert_not_called()

    def test_with_listener_with_multiple_events(self):
        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())
        mock_callback = mock.Mock()

        result = client.with_listener(hikari.GuildAvailableEvent, hikari.GuildLeaveEvent, hikari.GuildChannelEvent)(
            mock_callback
        )

        assert result is mock_callback
        add_listener_.assert_has_calls(
            [
                mock.call(hikari.GuildAvailableEvent, mock_callback),
                mock.call(hikari.GuildLeaveEvent, mock_callback),
                mock.call(hikari.GuildChannelEvent, mock_callback),
            ]
        )

    def test_with_listener_with_type_hint(self):
        async def callback(event: hikari.BanCreateEvent) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanCreateEvent, callback)

    def test_with_listener_with_type_hint_in_annotated(self):
        async def callback(event: typing.Annotated[hikari.BanCreateEvent, 123, 321]) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanCreateEvent, callback)

    def test_with_listener_with_positional_only_type_hint(self):
        async def callback(event: hikari.BanDeleteEvent, /) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanDeleteEvent, callback)

    def test_with_listener_with_var_positional_type_hint(self):
        async def callback(*event: hikari.BanEvent) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanEvent, callback)

    def test_with_listener_with_type_hint_union(self):
        async def callback(event: typing.Union[hikari.RoleEvent, typing.Literal["ok"], hikari.GuildEvent, str]) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_has_calls(
            [
                mock.call(hikari.RoleEvent, callback),
                mock.call(hikari.GuildEvent, callback),
            ]
        )

    def test_with_listener_with_type_hint_union_nested_annotated(self):
        async def callback(
            event: typing.Annotated[
                typing.Union[
                    typing.Annotated[typing.Union[hikari.RoleEvent, hikari.ReactionDeleteEvent], 123, 321],
                    hikari.GuildEvent,
                ],
                True,
                "meow",
            ]
        ) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_has_calls(
            [
                mock.call(hikari.RoleEvent, callback),
                mock.call(hikari.ReactionDeleteEvent, callback),
                mock.call(hikari.GuildEvent, callback),
            ]
        )

    # These tests covers syntax which was introduced in 3.10
    if sys.version_info >= (3, 10):

        def test_with_listener_with_type_hint_310_union(self):
            async def callback(event: hikari.ShardEvent | typing.Literal[""] | hikari.VoiceEvent | str) -> None:
                ...

            add_listener_ = mock.Mock()

            class StubClient(tanjun.Client):
                add_listener = add_listener_

            client = StubClient(mock.Mock())

            result = client.with_listener()(callback)

            assert result is callback
            add_listener_.assert_has_calls(
                [
                    mock.call(hikari.ShardEvent, callback),
                    mock.call(hikari.VoiceEvent, callback),
                ]
            )

        def test_with_listener_with_type_hint_310_union_nested_annotated(self):
            async def callback(
                event: typing.Annotated[
                    typing.Annotated[hikari.BanEvent | hikari.GuildEvent, 123, 321] | hikari.InviteEvent,
                    True,
                    "meow",
                ]
            ) -> None:
                ...

            add_listener_ = mock.Mock()

            class StubClient(tanjun.Client):
                add_listener = add_listener_

            client = StubClient(mock.Mock())

            result = client.with_listener()(callback)

            assert result is callback
            add_listener_.assert_has_calls(
                [
                    mock.call(hikari.BanEvent, callback),
                    mock.call(hikari.GuildEvent, callback),
                    mock.call(hikari.InviteEvent, callback),
                ]
            )

    def test_add_prefix(self):
        client = tanjun.Client(mock.Mock())

        result = client.add_prefix("aye")

        assert result is client
        assert "aye" in client.prefixes

    def test_add_prefix_when_already_present(self):
        client = tanjun.Client(mock.Mock()).add_prefix("lmao")

        result = client.add_prefix("lmao")

        assert result is client
        assert list(client.prefixes).count("lmao") == 1

    def test_add_prefix_when_iterable(self):
        client = tanjun.Client(mock.Mock())

        result = client.add_prefix(["Grand", "dad", "FNAF"])

        assert result is client
        assert list(client.prefixes).count("Grand") == 1
        assert list(client.prefixes).count("dad") == 1
        assert list(client.prefixes).count("FNAF") == 1

    def test_add_prefix_when_iterable_and_already_present(self):
        client = tanjun.Client(mock.Mock()).add_prefix(["naye", "laala", "OBAMA"])

        result = client.add_prefix(["naye", "OBAMA", "bourg"])

        assert result is client
        assert list(client.prefixes).count("naye") == 1
        assert list(client.prefixes).count("laala") == 1
        assert list(client.prefixes).count("OBAMA") == 1
        assert list(client.prefixes).count("bourg") == 1

    def test_remove_prefix(self):
        client = tanjun.Client(mock.Mock()).add_prefix("lmao")

        result = client.remove_prefix("lmao")

        assert result is client
        assert "lmao" not in client.prefixes

    def test_remove_prefix_when_not_present(self):
        client = tanjun.Client(mock.Mock())

        with pytest.raises(ValueError, match=".+"):
            client.remove_prefix("lmao")

    def test_set_prefix_getter(self):
        mock_getter = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.set_prefix_getter(mock_getter)

        assert result is client
        assert client.prefix_getter is mock_getter

    def test_set_prefix_getter_when_none(self):
        client = tanjun.Client(mock.Mock()).set_prefix_getter(mock.Mock())

        result = client.set_prefix_getter(None)

        assert result is client
        assert client.prefix_getter is None

    def test_with_prefix_getter(self):
        mock_getter = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.with_prefix_getter(mock_getter)

        assert result is mock_getter
        assert client.prefix_getter is mock_getter

    def test_iter_commands(self):
        mock_menu_1 = mock.Mock(is_global=True)
        mock_menu_2 = mock.Mock(is_global=False)
        mock_menu_3 = mock.Mock(is_global=False)

        mock_slash_1 = mock.Mock(is_global=False)
        mock_slash_2 = mock.Mock(is_global=True)
        mock_slash_3 = mock.Mock(is_global=True)

        mock_message_1 = mock.Mock()
        mock_message_2 = mock.Mock()
        mock_message_3 = mock.Mock()
        mock_message_4 = mock.Mock()
        client = (
            tanjun.Client(mock.Mock())
            .add_component(
                mock.Mock(menu_commands=[], message_commands=[mock_message_1], slash_commands=[mock_slash_1])
            )
            .add_component(mock.Mock(menu_commands=[mock_menu_1], message_commands=[mock_message_2], slash_commands=[]))
            .add_component(
                mock.Mock(
                    menu_commands=[], message_commands=[mock_message_3], slash_commands=[mock_slash_2, mock_slash_3]
                )
            )
            .add_component(mock.Mock(menu_commands=[mock_menu_2, mock_menu_3], message_commands=[], slash_commands=[]))
            .add_component(mock.Mock(menu_commands=[], message_commands=[mock_message_4], slash_commands=[]))
        )

        commands = list(client.iter_commands())

        assert commands == [
            mock_menu_1,
            mock_menu_2,
            mock_menu_3,
            mock_message_1,
            mock_message_2,
            mock_message_3,
            mock_message_4,
            mock_slash_1,
            mock_slash_2,
            mock_slash_3,
        ]

    def test_iter_menu_commands(self):
        mock_command_1 = mock.Mock(is_global=True, type=hikari.CommandType.USER)
        mock_command_2 = mock.Mock(is_global=False, type=hikari.CommandType.MESSAGE)
        mock_command_3 = mock.Mock(is_global=False, type=hikari.CommandType.USER)
        mock_command_4 = mock.Mock(is_global=True, type=hikari.CommandType.MESSAGE)
        client = (
            tanjun.Client(mock.Mock)
            .add_component(mock.Mock(menu_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(menu_commands=[]))
            .add_component(mock.Mock(menu_commands=[mock_command_3]))
            .add_component(mock.Mock(menu_commands=[mock_command_4]))
        )

        result = list(client.iter_menu_commands())

        assert result == [mock_command_1, mock_command_2, mock_command_3, mock_command_4]

    def test_iter_menu_commands_when_global_only(self):
        mock_command_1 = mock.Mock(is_global=True, type=hikari.CommandType.USER)
        mock_command_2 = mock.Mock(is_global=False, type=hikari.CommandType.MESSAGE)
        mock_command_3 = mock.Mock(is_global=False, type=hikari.CommandType.USER)
        mock_command_4 = mock.Mock(is_global=True, type=hikari.CommandType.MESSAGE)
        client = (
            tanjun.Client(mock.Mock)
            .add_component(mock.Mock(menu_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(menu_commands=[]))
            .add_component(mock.Mock(menu_commands=[mock_command_3]))
            .add_component(mock.Mock(menu_commands=[mock_command_4]))
        )

        result = list(client.iter_menu_commands(global_only=True))

        assert result == [mock_command_1, mock_command_4]

    def test_iter_menu_commands_when_filtering_for_user(self):
        mock_command_1 = mock.Mock(is_global=True, type=hikari.CommandType.USER)
        mock_command_2 = mock.Mock(is_global=False, type=hikari.CommandType.MESSAGE)
        mock_command_3 = mock.Mock(is_global=False, type=hikari.CommandType.USER)
        mock_command_4 = mock.Mock(is_global=True, type=hikari.CommandType.MESSAGE)
        client = (
            tanjun.Client(mock.Mock)
            .add_component(mock.Mock(menu_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(menu_commands=[]))
            .add_component(mock.Mock(menu_commands=[mock_command_3]))
            .add_component(mock.Mock(menu_commands=[mock_command_4]))
        )

        result = list(client.iter_menu_commands(type=hikari.CommandType.USER))

        assert result == [mock_command_1, mock_command_3]

    def test_iter_menu_commands_when_filtering_for_message(self):
        mock_command_1 = mock.Mock(is_global=True, type=hikari.CommandType.USER)
        mock_command_2 = mock.Mock(is_global=False, type=hikari.CommandType.MESSAGE)
        mock_command_3 = mock.Mock(is_global=False, type=hikari.CommandType.USER)
        mock_command_4 = mock.Mock(is_global=True, type=hikari.CommandType.MESSAGE)
        client = (
            tanjun.Client(mock.Mock)
            .add_component(mock.Mock(menu_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(menu_commands=[]))
            .add_component(mock.Mock(menu_commands=[mock_command_3]))
            .add_component(mock.Mock(menu_commands=[mock_command_4]))
        )

        result = list(client.iter_menu_commands(type=hikari.CommandType.MESSAGE))

        assert result == [mock_command_2, mock_command_4]

    def test_iter_menu_commands_when_filtering_for_user_and_global_only(self):
        mock_command_1 = mock.Mock(is_global=True, type=hikari.CommandType.USER)
        mock_command_2 = mock.Mock(is_global=False, type=hikari.CommandType.MESSAGE)
        mock_command_3 = mock.Mock(is_global=False, type=hikari.CommandType.USER)
        mock_command_4 = mock.Mock(is_global=True, type=hikari.CommandType.MESSAGE)
        client = (
            tanjun.Client(mock.Mock)
            .add_component(mock.Mock(menu_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(menu_commands=[]))
            .add_component(mock.Mock(menu_commands=[mock_command_3]))
            .add_component(mock.Mock(menu_commands=[mock_command_4]))
        )

        result = list(client.iter_menu_commands(type=hikari.CommandType.USER, global_only=True))

        assert result == [mock_command_1]

    def test_iter_menu_commands_when_filtering_for_message_and_global_only(self):
        mock_command_1 = mock.Mock(is_global=True, type=hikari.CommandType.USER)
        mock_command_2 = mock.Mock(is_global=False, type=hikari.CommandType.MESSAGE)
        mock_command_3 = mock.Mock(is_global=False, type=hikari.CommandType.USER)
        mock_command_4 = mock.Mock(is_global=True, type=hikari.CommandType.MESSAGE)
        client = (
            tanjun.Client(mock.Mock)
            .add_component(mock.Mock(menu_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(menu_commands=[]))
            .add_component(mock.Mock(menu_commands=[mock_command_3]))
            .add_component(mock.Mock(menu_commands=[mock_command_4]))
        )

        result = list(client.iter_menu_commands(type=hikari.CommandType.MESSAGE, global_only=True))

        assert result == [mock_command_4]

    def test_iter_message_commands(self):
        mock_command_1 = mock.Mock()
        mock_command_2 = mock.Mock()
        mock_command_3 = mock.Mock()
        mock_command_4 = mock.Mock()
        mock_command_5 = mock.Mock()
        client = (
            tanjun.Client(mock.Mock())
            .add_component(mock.Mock(slash_commands=[]))
            .add_component(mock.Mock(slash_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(slash_commands=[]))
            .add_component(mock.Mock(slash_commands=[mock_command_3, mock_command_4]))
            .add_component(mock.Mock(slash_commands=[mock_command_5]))
        )

        commands = list(client.iter_slash_commands())

        assert commands == [mock_command_1, mock_command_2, mock_command_3, mock_command_4, mock_command_5]

    def test_iter_slash_commands(self):
        mock_command_1 = mock.Mock()
        mock_command_2 = mock.Mock()
        mock_command_3 = mock.Mock()
        mock_command_4 = mock.Mock()
        mock_command_5 = mock.Mock()
        client = (
            tanjun.Client(mock.Mock())
            .add_component(mock.Mock(slash_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(slash_commands=[]))
            .add_component(mock.Mock(slash_commands=[mock_command_3, mock_command_4]))
            .add_component(mock.Mock(slash_commands=[]))
            .add_component(mock.Mock(slash_commands=[mock_command_5]))
        )

        commands = list(client.iter_slash_commands())

        assert commands == [mock_command_1, mock_command_2, mock_command_3, mock_command_4, mock_command_5]

    def test_iter_slash_commands_when_global_only(self):
        mock_command_1 = mock.Mock(is_global=True)
        mock_command_2 = mock.Mock(is_global=True)
        mock_command_3 = mock.Mock(is_global=True)
        mock_command_4 = mock.Mock(is_global=True)
        client = (
            tanjun.Client(mock.Mock())
            .add_component(mock.Mock(slash_commands=[mock_command_1, mock_command_2]))
            .add_component(mock.Mock(slash_commands=[]))
            .add_component(mock.Mock(slash_commands=[mock.Mock(is_global=False), mock.Mock(is_global=False)]))
            .add_component(mock.Mock(slash_commands=[mock.Mock(is_global=False), mock_command_3]))
            .add_component(mock.Mock(slash_commands=[mock_command_4]))
        )

        commands = list(client.iter_slash_commands(global_only=True))

        assert commands == [mock_command_1, mock_command_2, mock_command_3, mock_command_4]

    @pytest.mark.skip(reason="TODO")
    def test_check_message_name(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_check_slash_name(self):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_close(self):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_open(self):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_fetch_rest_application_id(self):
        ...

    def test_set_ephemeral_default(self):
        client = tanjun.Client(mock.Mock())

        result = client.set_ephemeral_default(True)

        assert result is client
        assert client.defaults_to_ephemeral is True

    def test_set_hooks(self):
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.set_hooks(mock_hooks)

        assert result is client
        assert client.hooks is mock_hooks

    def test_set_hooks_when_none(self):
        client = tanjun.Client(mock.Mock()).set_hooks(mock.Mock())

        result = client.set_hooks(None)

        assert result is client
        assert client.hooks is None

    def test_set_menu_hooks(self):
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.set_menu_hooks(mock_hooks)

        assert result is client
        assert client.menu_hooks is mock_hooks

    def test_set_menu_hooks_when_none(self):
        client = tanjun.Client(mock.Mock()).set_menu_hooks(mock.Mock())

        result = client.set_menu_hooks(None)

        assert result is client
        assert client.menu_hooks is None

    def test_set_message_hooks(self):
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.set_message_hooks(mock_hooks)

        assert result is client
        assert client.message_hooks is mock_hooks

    def test_set_message_hooks_when_none(self):
        client = tanjun.Client(mock.Mock()).set_message_hooks(mock.Mock())

        result = client.set_message_hooks(None)

        assert result is client
        assert client.message_hooks is None

    def test_set_slash_hooks(self):
        mock_hooks = mock.Mock()
        client = tanjun.Client(mock.Mock())

        result = client.set_slash_hooks(mock_hooks)

        assert result is client
        assert client.slash_hooks is mock_hooks

    def test_set_slash_hooks_when_none(self):
        client = tanjun.Client(mock.Mock()).set_slash_hooks(mock.Mock())

        result = client.set_slash_hooks(None)

        assert result is client
        assert client.slash_hooks is None

    def test_load_directory(self):
        mock_load_modules = mock.Mock()

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "she.py").write_text("laughs")
            (temp_dir / "so.txt").write_text("hard,")
            (temp_dir / "I.py").write_text("watch")
            (temp_dir / "her.py").write_text("balance")
            (temp_dir / "her").write_text("lose")
            (temp_dir / "dir.py").mkdir()
            (temp_dir / "dir.py" / "sex.py").write_text("yeet")

            client.load_directory(temp_dir)

            mock_load_modules.assert_has_calls(
                [mock.call(temp_dir / "she.py"), mock.call(temp_dir / "I.py"), mock.call(temp_dir / "her.py")],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    def test_load_directory_with_namespace(self):
        mock_load_modules = mock.Mock()

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "So.py").write_text("she'll")
            (temp_dir / "never").write_text("leave")
            (temp_dir / "her.txt").write_text("bedroom")
            (temp_dir / "in.py").write_text("this")
            (temp_dir / "this.py").write_text("community")
            (temp_dir / "dirty.py").mkdir()
            (temp_dir / "dirty.py" / "sexy.py").write_text("yeet")

            client.load_directory(temp_dir, namespace="trans.pride")

            mock_load_modules.assert_has_calls(
                [mock.call("trans.pride.So"), mock.call("trans.pride.in"), mock.call("trans.pride.this")],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    def test_load_directory_when_suppressed_error_raised(self):
        mock_load_modules = mock.Mock(
            side_effect=[tanjun.ModuleMissingLoaders("b", "by"), tanjun.ModuleStateConflict("nyaa.meow", "sleep"), None]
        )

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "So.py").write_text("she'll")
            (temp_dir / "never").write_text("leave")
            (temp_dir / "her.txt").write_text("bedroom")
            (temp_dir / "in.py").write_text("this")
            (temp_dir / "this.py").write_text("community")

            client.load_directory(temp_dir, namespace="trans.pride")

            mock_load_modules.assert_has_calls(
                [mock.call("trans.pride.So"), mock.call("trans.pride.in"), mock.call("trans.pride.this")],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    def test_load_directory_when_fails_to_load(self):
        mock_exc = tanjun.FailedModuleLoad("trans.rights")
        mock_load_modules = mock.Mock(side_effect=[None, mock_exc])

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "So.py").write_text("she'll")
            (temp_dir / "never").write_text("leave")
            (temp_dir / "her.txt").write_text("bedroom")
            (temp_dir / "in.py").write_text("this")

            with pytest.raises(tanjun.FailedModuleLoad) as exc:
                client.load_directory(temp_dir, namespace="trans.pride")

            assert exc.value is mock_exc
            mock_load_modules.assert_has_calls(
                [
                    mock.call("trans.pride.So"),
                    mock.call("trans.pride.in"),
                ],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio()
    async def test_load_directory_async(self):

        mock_load_modules = mock.AsyncMock()

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules_async = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "she.py").write_text("laughs")
            (temp_dir / "so.txt").write_text("hard,")
            (temp_dir / "I.py").write_text("watch")
            (temp_dir / "her.py").write_text("balance")
            (temp_dir / "her").write_text("lose")
            (temp_dir / "dir.py").mkdir()
            (temp_dir / "dir.py" / "sex.py").write_text("yeet")

            await client.load_directory_async(temp_dir)

            mock_load_modules.assert_has_awaits(
                [mock.call(temp_dir / "she.py"), mock.call(temp_dir / "I.py"), mock.call(temp_dir / "her.py")],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio()
    async def test_load_directory_async_with_namespace(self):
        mock_load_modules = mock.AsyncMock()

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules_async = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "So.py").write_text("she'll")
            (temp_dir / "never").write_text("leave")
            (temp_dir / "her.txt").write_text("bedroom")
            (temp_dir / "in.py").write_text("this")
            (temp_dir / "this.py").write_text("community")
            (temp_dir / "dirty.py").mkdir()
            (temp_dir / "dirty.py" / "sexy.py").write_text("yeet")

            await client.load_directory_async(temp_dir, namespace="trans.pride")

            mock_load_modules.assert_has_awaits(
                [mock.call("trans.pride.So"), mock.call("trans.pride.in"), mock.call("trans.pride.this")],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio()
    async def test_load_directory_async_when_suppressed_error_raised(self):
        mock_load_modules = mock.AsyncMock(
            side_effect=[tanjun.ModuleMissingLoaders("b", "by"), tanjun.ModuleStateConflict("nyaa.meow", "sleep"), None]
        )

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules_async = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "So.py").write_text("she'll")
            (temp_dir / "never").write_text("leave")
            (temp_dir / "her.txt").write_text("bedroom")
            (temp_dir / "in.py").write_text("this")
            (temp_dir / "this.py").write_text("community")

            await client.load_directory_async(temp_dir, namespace="trans.pride")

            mock_load_modules.assert_has_awaits(
                [mock.call("trans.pride.So"), mock.call("trans.pride.in"), mock.call("trans.pride.this")],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio()
    async def test_load_directory_async_when_fails_to_load(self):
        mock_exc = tanjun.FailedModuleLoad("trans.rights")
        mock_load_modules = mock.AsyncMock(side_effect=[None, mock_exc])

        class StubClient(tanjun.Client):
            __slots__ = ()

            load_modules_async = mock_load_modules

        client = StubClient(mock.Mock())

        temp_dir = pathlib.Path(tempfile.mkdtemp())
        try:
            (temp_dir / "So.py").write_text("she'll")
            (temp_dir / "never").write_text("leave")
            (temp_dir / "her.txt").write_text("bedroom")
            (temp_dir / "in.py").write_text("this")

            with pytest.raises(tanjun.FailedModuleLoad) as exc:
                await client.load_directory_async(temp_dir, namespace="trans.pride")

            assert exc.value is mock_exc
            mock_load_modules.assert_has_awaits(
                [
                    mock.call("trans.pride.So"),
                    mock.call("trans.pride.in"),
                ],
                any_order=True,
            )

        finally:
            shutil.rmtree(temp_dir)

    @pytest.fixture()
    def file(self) -> collections.Iterator[typing.IO[str]]:
        # A try, finally is used to delete the file rather than relying on delete=True behaviour
        # as on Windows the file cannot be accessed by other processes if delete is True.
        file = tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False)
        try:
            with file:
                yield file

        finally:
            pathlib.Path(file.name).unlink(missing_ok=False)

    def test__load_modules_with_system_path(self, file: typing.IO[str]):
        add_component_ = mock.Mock()
        add_client_callback_ = mock.Mock()

        class MockClient(tanjun.Client):
            add_component = add_component_

            add_client_callback = add_client_callback_

        client = MockClient(mock.AsyncMock())
        file.write(
            textwrap.dedent(
                """
                import tanjun

                @tanjun.as_loader
                def __dunder_loader__(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(5533)
                    client.add_client_callback(554444)

                foo = 5686544536876
                bar = object()

                @tanjun.as_loader
                def load_module(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(123)
                    client.add_client_callback(4312)

                class FullMetal:
                    ...

                @tanjun.as_loader
                def _load_module(client: tanjun.abc.Client) -> None:
                    assert False
                    client.add_component(5432)
                    client.add_client_callback(6543456)
                """
            )
        )
        file.flush()

        generator = client._load_module(pathlib.Path(file.name))
        module = next(generator)()
        try:
            generator.send(module)

        except StopIteration:
            pass

        else:
            pytest.fail("Expected StopIteration")

        add_component_.assert_has_calls([mock.call(5533), mock.call(123)])
        add_client_callback_.assert_has_calls([mock.call(554444), mock.call(4312)])

    def test__load_modules_with_system_path_respects_all(self, file: typing.IO[str]):
        add_component_ = mock.Mock()
        add_client_callback_ = mock.Mock()

        class MockClient(tanjun.Client):
            add_component = add_component_

            add_client_callback = add_client_callback_

        client = MockClient(mock.AsyncMock())
        file.write(
            textwrap.dedent(
                """
                __all__ = ["FullMetal", "load_module", "_priv_load", "bar", "foo","easy", "tanjun", "missing"]
                import tanjun

                foo = 5686544536876
                bar = object()

                @tanjun.as_loader
                def _priv_load(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(777)
                    client.add_client_callback(778)

                class FullMetal:
                    ...

                @tanjun.as_loader
                def load_module(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(123)
                    client.add_client_callback(4312)

                @tanjun.as_loader
                def easy(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(5432)
                    client.add_client_callback(6543456)

                @tanjun.as_loader
                def not_in_all(client: tanjun.abc.Client) -> None:
                    assert False
                """
            )
        )
        file.flush()

        generator = client._load_module(pathlib.Path(file.name))
        module = next(generator)()
        try:
            generator.send(module)

        except StopIteration:
            pass

        else:
            pytest.fail("Expected StopIteration")

        add_component_.assert_has_calls([mock.call(123), mock.call(777), mock.call(5432)])
        add_client_callback_.assert_has_calls([mock.call(4312), mock.call(778), mock.call(6543456)])

    def test__load_modules_with_system_path_when_all_and_no_loaders_found(self, file: typing.IO[str]):
        add_component_ = mock.Mock()
        add_client_callback_ = mock.Mock()

        class MockClient(tanjun.Client):
            add_component = add_component_

            add_client_callback = add_client_callback_

        client = MockClient(mock.AsyncMock())
        file.write(
            textwrap.dedent(
                """
                __all__ = ["tanjun", "foo", "missing", "bar", "load_module", "FullMetal"]

                import tanjun

                foo = 5686544536876
                bar = object()

                def load_module(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(123)
                    client.add_client_callback(4312)

                class FullMetal:
                    ...

                @tanjun.as_loader
                def not_in_all(client: tanjun.abc.Client) -> None:
                    assert False
                """
            )
        )
        file.flush()
        generator = client._load_module(pathlib.Path(file.name))
        module = next(generator)()

        with pytest.raises(tanjun.ModuleMissingLoaders):
            generator.send(module)

    def test__load_modules_with_system_path_when_no_loaders_found(self, file: typing.IO[str]):
        add_component_ = mock.Mock()
        add_client_callback_ = mock.Mock()

        class MockClient(tanjun.Client):
            add_component = add_component_

            add_client_callback = add_client_callback_

        client = MockClient(mock.AsyncMock())
        file.write(
            textwrap.dedent(
                """
                import tanjun

                foo = 5686544536876
                bar = object()

                def load_module(client: tanjun.abc.Client) -> None:
                    assert isinstance(client, tanjun.Client)
                    client.add_component(123)
                    client.add_client_callback(4312)

                class FullMetal:
                    ...
                """
            )
        )
        file.flush()
        generator = client._load_module(pathlib.Path(file.name))
        module = next(generator)()

        with pytest.raises(tanjun.ModuleMissingLoaders):
            generator.send(module)

    def test__load_modules_with_system_path_when_loader_raises(self, file: typing.IO[str]):
        add_component_ = mock.Mock()
        add_client_callback_ = mock.Mock()

        class MockClient(tanjun.Client):
            add_component = add_component_

            add_client_callback = add_client_callback_

        client = MockClient(mock.AsyncMock())
        file.write(
            textwrap.dedent(
                """
                import tanjun

                foo = 5686544536876
                bar = object()

                @tanjun.as_loader
                def load_module(client: tanjun.abc.Client) -> None:
                    raise RuntimeError("Mummy uwu")

                class FullMetal:
                    ...
                """
            )
        )
        file.flush()
        generator = client._load_module(pathlib.Path(file.name))
        module = next(generator)()

        with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
            generator.send(module)

        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert exc_info.value.__cause__.args == ("Mummy uwu",)

    def test__load_modules_with_system_path_when_already_loaded(self, file: typing.IO[str]):
        client = tanjun.Client(mock.AsyncMock())
        file.write(textwrap.dedent("""raise NotImplementedError("This shouldn't ever be imported")"""))
        file.flush()
        path = pathlib.Path(file.name)
        client._path_modules[path] = mock.Mock()
        generator = client._load_module(pathlib.Path(file.name))

        with pytest.raises(tanjun.ModuleStateConflict):
            next(generator)

    def test__load_modules_with_system_path_for_unknown_path(self):
        class MockClient(tanjun.Client):
            add_component = mock.Mock()
            add_client_callback = mock.Mock()

        client = MockClient(mock.AsyncMock())
        random_path = pathlib.Path(uuid.uuid4().hex)
        generator = client._load_module(random_path)
        next_ = next(generator)

        with pytest.raises(ModuleNotFoundError):
            next_()

    def test__load_modules_with_python_module_path(self):
        client = tanjun.Client(mock.AsyncMock())
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True))

        mock_module = mock.Mock(
            object=123,
            foo="ok",
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=False)),
            no=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True)),
            _priv_loader=priv_loader,
            __all__=None,
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            generator = client._load_module("okokok.no.u")
            module = next(generator)()
            try:
                generator.send(module)

            except StopIteration:
                pass

            else:
                pytest.fail("Expected StopIteration")

            import_module.assert_called_once_with("okokok.no.u")

        mock_module.loader.load.assert_called_once_with(client)
        mock_module.other_loader.load.assert_called_once_with(client)
        priv_loader.load.assert_not_called()

    def test__load_modules_with_python_module_path_respects_all(self):
        client = tanjun.Client(mock.AsyncMock())
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True))

        mock_module = mock.Mock(
            object=123,
            foo="ok",
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True)),
            no=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=False)),
            _priv_loader=priv_loader,
            another_loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True)),
            __all__=["loader", "_priv_loader", "another_loader", "missing"],
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            generator = client._load_module("okokok.no.u")
            module = next(generator)()
            try:
                generator.send(module)

            except StopIteration:
                pass

            else:
                pytest.fail("Expected StopIteration")

            import_module.assert_called_once_with("okokok.no.u")

        mock_module.loader.load.assert_called_once_with(client)
        mock_module.other_loader.load.assert_not_called()
        priv_loader.load.assert_called_once_with(client)
        mock_module.another_loader.load.assert_called_once_with(client)

    def test__load_modules_with_python_module_path_when_no_loader_found(self):
        client = tanjun.Client(mock.AsyncMock())
        mock_module = mock.Mock(
            object=123,
            foo="ok",
            no=object(),
            __all__=None,
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=False)),
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            generator = client._load_module("okokok.no.u")
            module = next(generator)()

            with pytest.raises(tanjun.ModuleMissingLoaders):
                generator.send(module)

            import_module.assert_called_once_with("okokok.no.u")

        mock_module.loader.load.assert_called_once_with(client)

    def test__load_modules_with_python_module_path_when_loader_raises(self):
        mock_exception = KeyError("ayayaya")
        mock_module = mock.Mock(
            foo=5686544536876, bar=object(), load_module=mock.Mock(tanjun.abc.ClientLoader, has_load=True)
        )
        mock_module.load_module.load.side_effect = mock_exception

        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=mock_module):
            generator = client._load_module("e")
            module = next(generator)()

            with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
                generator.send(module)

        assert exc_info.value.__cause__ is mock_exception

    def test__load_modules_with_python_module_path_when_already_loaded(self):
        client = tanjun.Client(mock.AsyncMock())
        client._modules["ayayayaya.ok"] = mock.Mock()
        generator = client._load_module("ayayayaya.ok")

        with pytest.raises(tanjun.ModuleStateConflict):
            next(generator)

    def test_load_modules(self):
        mock_path = mock.Mock(pathlib.Path)
        mock_gen_1 = mock.Mock(__next__=mock.Mock())
        mock_gen_1.send.side_effect = StopIteration
        mock_gen_2 = mock.Mock(__next__=mock.Mock())
        mock_gen_2.send.side_effect = StopIteration
        mock__load_module = mock.Mock(side_effect=[mock_gen_1, mock_gen_2])

        class StubClient(tanjun.Client):
            _load_module = mock__load_module

        client = StubClient(mock.AsyncMock())

        result = client.load_modules(mock_path, "ok.no.u")

        assert result is client
        mock__load_module.assert_has_calls(
            [mock.call(mock_path.expanduser.return_value.resolve.return_value), mock.call("ok.no.u")]
        )
        mock_path.expanduser.assert_called_once_with()
        mock_path.expanduser.return_value.resolve.assert_called_once_with()
        mock_gen_1.__next__.assert_called_once_with()
        mock_gen_1.__next__.return_value.assert_called_once_with()
        mock_gen_1.send.assert_called_once_with(mock_gen_1.__next__.return_value.return_value)
        mock_gen_2.__next__.assert_called_once_with()
        mock_gen_2.__next__.return_value.assert_called_once_with()
        mock_gen_2.send.assert_called_once_with(mock_gen_2.__next__.return_value.return_value)

    def test_load_modules_when_module_import_raises(self):
        mock_exception = ValueError("aye")
        mock_gen = mock.Mock(__next__=mock.Mock())
        mock_gen.__next__.return_value.side_effect = mock_exception

        mock__load_module = mock.Mock(return_value=mock_gen)

        class StubClient(tanjun.Client):
            _load_module = mock__load_module

        client = StubClient(mock.AsyncMock())

        with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
            client.load_modules("ok.no.u")

        assert exc_info.value.__cause__ is mock_exception

        mock__load_module.assert_called_once_with("ok.no.u")
        mock_gen.__next__.assert_called_once_with()
        mock_gen.__next__.return_value.assert_called_once_with()
        mock_gen.send.assert_not_called()

    @mock.patch.object(asyncio, "get_running_loop")
    @pytest.mark.asyncio()
    async def test_load_modules_async(self, get_running_loop: mock.Mock):
        mock_executor_result_1 = mock.Mock()
        mock_executor_result_2 = mock.Mock()
        mock_executor_result_3 = mock.Mock()
        get_running_loop.return_value.run_in_executor = mock.AsyncMock(
            side_effect=[mock_executor_result_1, mock_executor_result_2, mock_executor_result_3]
        )
        mock_path = mock.Mock(pathlib.Path)
        mock_gen_1 = mock.Mock(__next__=mock.Mock())
        mock_gen_1.send.side_effect = StopIteration
        mock_gen_2 = mock.Mock(__next__=mock.Mock())
        mock_gen_2.send.side_effect = StopIteration
        mock__load_module = mock.Mock(side_effect=[mock_gen_1, mock_gen_2])

        class StubClient(tanjun.Client):
            _load_module = mock__load_module

        client = StubClient(mock.AsyncMock())

        result = await client.load_modules_async(mock_path, "ok.no.u")

        assert result is None
        mock__load_module.assert_has_calls([mock.call(mock_executor_result_1), mock.call("ok.no.u")])
        mock_gen_1.__next__.assert_called_once_with()
        mock_gen_1.send.assert_called_once_with(mock_executor_result_2)
        mock_gen_2.__next__.assert_called_once_with()
        mock_gen_2.send.assert_called_once_with(mock_executor_result_3)
        get_running_loop.assert_called_once_with()
        get_running_loop.return_value.run_in_executor.assert_has_calls(
            [
                mock.call(None, tanjun.clients._normalize_path, mock_path),
                mock.call(None, mock_gen_1.__next__.return_value),
                mock.call(None, mock_gen_2.__next__.return_value),
            ]
        )

    @mock.patch.object(asyncio, "get_running_loop")
    @pytest.mark.asyncio()
    async def test_load_modules_async_when_module_import_raises(self, get_running_loop: mock.Mock):
        mock_exception = ValueError("aye")
        mock_gen = mock.Mock(__next__=mock.Mock())
        get_running_loop.return_value.run_in_executor = mock.AsyncMock(side_effect=mock_exception)
        mock__load_module = mock.Mock(return_value=mock_gen)

        class StubClient(tanjun.Client):
            _load_module = mock__load_module

        client = StubClient(mock.AsyncMock())

        with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
            await client.load_modules_async("ok.no.u")

        assert exc_info.value.__cause__ is mock_exception

        mock__load_module.assert_called_once_with("ok.no.u")
        mock_gen.__next__.assert_called_once_with()
        get_running_loop.return_value.run_in_executor.assert_called_once_with(None, mock_gen.__next__.return_value)
        mock_gen.send.assert_not_called()

    def test_unload_modules_with_system_path(self):
        priv_unloader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            __dunder_loader__=mock.Mock(tanjun.abc.ClientLoader),
            foo=5686544536876,
            bar=object(),
            unload_module=mock.Mock(tanjun.abc.ClientLoader),
            FullMetal=object,
            _unload_modules=priv_unloader,
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path("aye")
        client._path_modules[path.resolve()] = old_module

        result = client.unload_modules(path)

        assert result is client
        old_module.__dunder_loader__.unload.assert_called_once_with(client)
        old_module.unload_module.unload.assert_called_once_with(client)
        priv_unloader.unload.assert_not_called()
        assert path.resolve() not in client._path_modules

    def test_unload_modules_with_system_path_respects_all(self):
        priv_unload = mock.Mock(tanjun.abc.ClientLoader)
        mock_module = mock.Mock(
            __all__=["FullMetal", "_priv_unload", "unload_module", "_bar", "foo", "load_module", "missing"],
            foo=5686544536876,
            _bar=object(),
            _priv_unload=priv_unload,
            FullMetal=object(),
            unload_module=mock.Mock(tanjun.abc.ClientLoader),
            load_module=mock.Mock(tanjun.abc.ClientLoader),
            not_in_all=mock.Mock(tanjun.abc.ClientLoader),
        )

        path = pathlib.Path("ayeeeee")
        client = tanjun.Client(mock.AsyncMock())
        client._path_modules[path.resolve()] = mock_module

        client.unload_modules(path)

        priv_unload.unload.assert_called_once_with(client)
        mock_module.unload_module.unload.assert_called_once_with(client)
        mock_module.load_module.unload.assert_called_once_with(client)
        mock_module.not_in_all.unload.assert_not_called()
        assert path.resolve() not in client._path_modules

    def test_unload_modules_with_system_path_when_not_loaded(self):
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path("naye")

        with pytest.raises(tanjun.ModuleStateConflict):
            client.unload_modules(path)

        assert path.resolve() not in client._path_modules

    def test_unload_modules_with_system_path_when_no_unloaders_found(self):
        mock_module = mock.Mock(
            foo=5686544536876,
            bar=object(),
            FullMetal=object,
            load_module=mock.Mock(tanjun.abc.ClientLoader, has_unload=False, unload=mock.Mock(return_value=False)),
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path("rewwewew")
        client._path_modules[path.resolve()] = mock_module

        with pytest.raises(tanjun.ModuleMissingUnloaders):
            client.unload_modules(path)

        assert client._path_modules[path.resolve()] is mock_module

    def test_unload_modules_with_system_path_when_all_and_no_unloaders_found(self):
        mock_module = mock.Mock(
            __all__=["FullMetal", "bar", "foo", "load_module", "missing"],
            foo=5686544536876,
            bar=object(),
            FullMetal=int,
            load_module=mock.Mock(tanjun.abc.ClientLoader, has_unload=False, unload=mock.Mock(return_value=False)),
            unload_module=mock.Mock(tanjun.abc.ClientLoader, has_unload=True, unload=mock.Mock(return_value=True)),
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path("./123dsaasd")
        client._path_modules[path.resolve()] = mock_module

        with pytest.raises(tanjun.ModuleMissingUnloaders):
            client.unload_modules(path)

        assert client._path_modules[path.resolve()] is mock_module

    def test_unload_modules_with_system_path_when_unloader_raises(self):
        mock_exception = ValueError("aye")
        mock_module = mock.Mock(
            foo=5686544536876,
            bar=object(),
            FullMetal=str,
            load_module=mock.Mock(tanjun.abc.ClientLoader, has_unload=True, unload=mock.Mock(return_value=True)),
            unload_module=mock.Mock(
                tanjun.abc.ClientLoader, has_unload=True, unload=mock.Mock(side_effect=mock_exception)
            ),
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path("./yeet")
        client._path_modules[path.resolve()] = mock_module

        with pytest.raises(tanjun.FailedModuleUnload) as exc_info:
            client.unload_modules(path)

        assert exc_info.value.__cause__ is mock_exception
        assert client._path_modules[path.resolve()] is mock_module

    def test_unload_modules_with_python_module_path(self):
        client = tanjun.Client(mock.AsyncMock())
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=True))

        mock_module = mock.Mock(
            object=123,
            foo="ok",
            other_loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=True)),
            loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False)),
            no=object(),
            _priv_loader=priv_loader,
            __all__=None,
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            result = client.load_modules("okokok.no").unload_modules("okokok.no")

            import_module.assert_called_once_with("okokok.no")

        assert result is client
        mock_module.other_loader.unload.assert_called_once_with(client)
        mock_module.loader.unload.assert_called_once_with(client)
        priv_loader.unload.assert_not_called()
        assert "okokok.no" not in client._modules

    def test_unload_modules_with_python_module_path_respects_all(self):
        client = tanjun.Client(mock.AsyncMock())
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=True))

        mock_module = mock.Mock(
            object=123,
            foo="ok",
            loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False)),
            no=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=True)),
            _priv_loader=priv_loader,
            another_loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=True)),
            __all__=["loader", "_priv_loader", "another_loader", "missing"],
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            client.load_modules("okokok.no.u")

            import_module.assert_called_once_with("okokok.no.u")

        client.unload_modules("okokok.no.u")

        mock_module.loader.unload.assert_called_once_with(client)
        mock_module.other_loader.assert_not_called()
        priv_loader.unload.assert_called_once_with(client)
        mock_module.another_loader.unload.assert_called_once_with(client)
        assert "okokok.no.u" not in client._modules

    def test_unload_modules_with_python_module_path_when_not_loaded(self):
        client = tanjun.Client(mock.AsyncMock())

        with pytest.raises(tanjun.ModuleStateConflict):
            client.unload_modules("gay.cat")

        assert "gay.cat" not in client._modules

    def test_unload_modules_with_python_module_path_when_no_unloaders_found_and_all(self):
        client = tanjun.Client(mock.AsyncMock())
        other_loader = mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=True))

        mock_module = mock.Mock(
            object=123,
            foo="ok",
            loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False)),
            no=object(),
            other_loader=other_loader,
            __all__=["loader", "missing"],
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            client.load_modules("senpai.uwu")

            with pytest.raises(tanjun.ModuleMissingUnloaders):
                client.unload_modules("senpai.uwu")

            import_module.assert_called_once_with("senpai.uwu")
            other_loader.assert_not_called()

        mock_module.loader.unload.assert_called_once_with(client)
        assert "senpai.uwu" in client._modules

    def test_unload_modules_with_python_module_path_when_no_unloaders_found(self):
        client = tanjun.Client(mock.AsyncMock())

        mock_module = mock.Mock(
            object=123,
            foo="ok",
            loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False)),
            no=object(),
        )

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            client.load_modules("okokok.nok")

            with pytest.raises(tanjun.ModuleMissingUnloaders):
                client.unload_modules("okokok.nok")

            import_module.assert_called_once_with("okokok.nok")

        mock_module.loader.unload.assert_called_once_with(client)
        assert "okokok.nok" in client._modules

    def test_unload_modules_with_python_module_path_when_unloader_raises(self):
        client = tanjun.Client(mock.AsyncMock())
        mock_exception = TypeError("Big shot")
        mock_module = mock.Mock(
            foo=5686544536876,
            bar=object(),
            loader=mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(side_effect=mock_exception)),
        )
        client._modules["ea s"] = mock_module

        with pytest.raises(tanjun.FailedModuleUnload) as exc_info:
            client.unload_modules("ea s")

        assert exc_info.value.__cause__ is mock_exception
        assert client._modules["ea s"] is mock_module
        assert "ea s" in client._modules

    def test__reload_modules_with_python_module_path(self):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False))
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(unload=False)),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
        )
        new_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=False)),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("waifus")

        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_not_called()
        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_not_called()
        new_module.other_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("waifus")
            module = next(generator)()
            try:
                generator.send(module)

            except StopIteration:
                pass

            else:
                pytest.fail("Expected StopIteration")

            reload.assert_called_once_with(old_module)

        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_called_once_with(client)
        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_called_once_with(client)
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_called_once_with(client)
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_called_once_with(client)
        new_module.other_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        assert client._modules["waifus"] is new_module

    def test__reload_modules_with_python_module_path_when_no_unloaders_found(self):
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            load=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True), has_unload=False),
            ok=123,
            naye=object(),
            _priv_loader=priv_loader,
        )
        new_module = mock.Mock(ok=123, loader=mock.Mock(tanjun.abc.ClientLoader))
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("waifus")

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("waifus")
            with pytest.raises(tanjun.ModuleMissingUnloaders):
                next(generator)

            reload.assert_not_called()

        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()
        assert client._modules["waifus"] is old_module

    def test__reload_modules_with_python_module_path_when_no_loaders_found_in_new_module(self):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
        )
        new_module = mock.Mock(
            ok=123,
            naye=object(),
            _priv_loader=priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("yuri.waifus")

        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("yuri.waifus")
            module = next(generator)()

            with pytest.raises(tanjun.ModuleMissingLoaders):
                generator.send(module)

            reload.assert_called_once_with(old_module)

        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        assert client._modules["yuri.waifus"] is old_module

    def test__reload_modules_with_python_module_path_when_all(self):
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            _priv_loader=old_priv_loader,
            __all__=["loader", "other_loader", "ok", "_priv_loader"],
        )
        new_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=priv_loader,
            __all__=["loader", "_priv_loader"],
        )
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("waifus")

        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_called_once_with(client)
        old_priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_not_called()
        new_module.other_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("waifus")
            module = next(generator)()
            try:
                generator.send(module)

            except StopIteration:
                pass

            else:
                pytest.fail("Expected StopIteration")

            reload.assert_called_once_with(old_module)

        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_called_once_with(client)
        old_priv_loader.load.assert_called_once_with(client)
        old_priv_loader.unload.assert_called_once_with(client)
        new_module.loader.load.assert_called_once_with(client)
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_not_called()
        new_module.other_loader.unload.assert_not_called()
        priv_loader.load.assert_called_once_with(client)
        priv_loader.unload.assert_not_called()
        assert client._modules["waifus"] is new_module

    def test__reload_modules_with_python_module_path_when_all_and_no_unloaders_found(self):
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, has_unload=False),
            ok=123,
            naye=object(),
            _priv_loader=priv_loader,
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            __all__=["naye", "loader", "ok"],
        )
        new_module = mock.Mock(loader=mock.Mock(tanjun.abc.ClientLoader, has_unload=False), foo=object())
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("waifus")

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("waifus")

            with pytest.raises(tanjun.ModuleMissingUnloaders):
                next(generator)

            reload.assert_not_called()

        priv_loader.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()
        assert client._modules["waifus"] is old_module

    def test__reload_modules_with_python_module_path_when_all_and_no_loaders_found_in_new_module(self):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
            __all__=["loader", "ok", "naye"],
        )
        new_module = mock.Mock(
            ok=123,
            naye=object(),
            _priv_loader=priv_loader,
            loader=mock.Mock(tanjun.abc.ClientLoader, has_load=True),
            __all__=["ok", "naye"],
        )
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("yuri.waifus")

        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("yuri.waifus")
            module = next(generator)()

            with pytest.raises(tanjun.ModuleMissingLoaders):
                generator.send(module)

            reload.assert_called_once_with(old_module)

        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()
        assert client._modules["yuri.waifus"] is old_module

    def test__reload_modules_with_python_module_path_and_not_loaded(self):
        client = tanjun.Client(mock.AsyncMock())
        generator = client._reload_module("aya.gay.no")

        with pytest.raises(tanjun.ModuleStateConflict):
            next(generator)

        assert "aya.gay.no" not in client._modules

    def test__reload_modules_with_python_module_path_rolls_back_when_new_module_loader_raises(self):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False))
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(unload=False)),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
        )
        mock_exception = KeyError("Aaaaaaaa")
        new_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=False, side_effect=mock_exception)),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())

        with mock.patch.object(importlib, "import_module", return_value=old_module):
            client.load_modules("waifus")

        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_not_called()
        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_not_called()
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_not_called()
        new_module.other_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()

        with mock.patch.object(importlib, "reload", return_value=new_module) as reload:
            generator = client._reload_module("waifus")
            module = next(generator)()

            with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
                generator.send(module)

            assert exc_info.value.__cause__ is mock_exception
            reload.assert_called_once_with(old_module)

        old_module.other_loader.load.assert_has_calls([mock.call(client), mock.call(client)])
        old_module.other_loader.unload.assert_called_once_with(client)
        old_module.loader.load.assert_has_calls([mock.call(client), mock.call(client)])
        old_module.loader.unload.assert_called_once_with(client)
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        new_module.loader.load.assert_called_once_with(client)
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_not_called()
        new_module.other_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        assert client._modules["waifus"] is old_module

    def test__reload_modules_with_system_path(self, file: typing.IO[str]):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(unload=False)),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path(file.name)
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                loader = mock.Mock(tanjun.abc.ClientLoader, has_load=False, load=mock.Mock(return_value=False))
                ok = 123
                naye = object()
                other_loader = mock.Mock(tanjun.abc.ClientLoader, has_load=True)
                _priv_loader = mock.Mock(tanjun.abc.ClientLoader)
                """
            )
        )
        file.flush()

        client._path_modules[path] = old_module

        generator = client._reload_module(path)
        module = next(generator)()
        try:
            generator.send(module)

        except StopIteration:
            pass

        else:
            pytest.fail("Expected StopIteration")

        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_called_once_with(client)
        old_module.loader.load.assert_not_called()
        old_module.loader.unload.assert_called_once_with(client)
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        new_module = client._path_modules[path]
        assert new_module is not old_module
        new_module.loader.load.assert_called_once_with(client)
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_called_once_with(client)
        new_module.other_loader.unload.assert_not_called()
        new_module._priv_loader.load.assert_not_called()
        new_module._priv_loader.unload.assert_not_called()

    def test__reload_modules_with_system_path_when_no_unloaders_found(self, file: typing.IO[str]):
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            load=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(return_value=True), has_unload=False),
            ok=123,
            naye=object(),
            _priv_loader=priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                loader = mock.Mock(
                    tanjun.abc.ClientLoader,
                    load=mock.Mock(side_effect=RuntimeError("This shouldn't be called")),
                )
                """
            )
        )
        file.flush()
        path = pathlib.Path(file.name)
        client._path_modules[path] = old_module
        generator = client._reload_module(path)

        with pytest.raises(tanjun.ModuleMissingUnloaders):
            next(generator)

        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        assert client._path_modules[path] is old_module

    def test__reload_modules_with_system_path_when_no_loaders_found_in_new_module(self, file: typing.IO[str]):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path(file.name)
        client._path_modules[path] = old_module
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                ok = 123
                naye = object()
                loader = mock.Mock(tanjun.abc.ClientLoader, has_load=False)
                _priv_loader = mock.Mock(tanjun.abc.ClientLoader)
                """
            )
        )
        file.flush()
        generator = client._reload_module(path)
        module = next(generator)()

        with pytest.raises(tanjun.ModuleMissingLoaders):
            generator.send(module)

        old_module.loader.load.assert_not_called()
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        assert client._path_modules[path] is old_module

    def test__reload_modules_with_system_path_when_all(self, file: typing.IO[str]):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            _priv_loader=old_priv_loader,
            __all__=["loader", "other_loader", "ok", "_priv_loader"],
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path(file.name)
        client._path_modules[path] = old_module
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                loader = mock.Mock(tanjun.abc.ClientLoader)
                ok = 123
                naye = object()
                other_loader = mock.Mock(tanjun.abc.ClientLoader)
                _priv_loader = mock.Mock(tanjun.abc.ClientLoader)
                __all__ = ["loader", "_priv_loader"]
                """
            )
        )
        file.flush()

        generator = client._reload_module(path)
        module = next(generator)()
        try:
            generator.send(module)

        except StopIteration:
            pass

        else:
            pytest.fail("Expected StopIteration")

        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_called_once_with(client)
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_called_once_with(client)
        new_module = client._path_modules[path]
        assert new_module is not old_module
        new_module.loader.load.assert_called_once_with(client)
        new_module.loader.unload.assert_not_called()
        new_module.other_loader.load.assert_not_called()
        new_module.other_loader.unload.assert_not_called()
        new_module._priv_loader.load.assert_called_once_with(client)
        new_module._priv_loader.unload.assert_not_called()

    def test__reload_modules_with_system_path_when_all_and_no_unloaders_found(self, file: typing.IO[str]):
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, has_unload=False),
            ok=123,
            naye=object(),
            _priv_loader=priv_loader,
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            __all__=["naye", "loader", "ok"],
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path(file.name)
        client._path_modules[path] = old_module
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                loader = mock.Mock(
                    tanjun.abc.ClientLoader,
                    has_unload=False,
                    unload=mock.Mock(side_effect=RuntimeError("This shouldn't ever be called"))
                )
                foo = object()
                """
            )
        )
        file.flush()
        generator = client._reload_module(path)

        with pytest.raises(tanjun.ModuleMissingUnloaders):
            next(generator)

        priv_loader.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        assert client._path_modules[path] is old_module

    def test__reload_modules_with_system_path_when_all_and_no_loaders_found_in_new_module(self, file: typing.IO[str]):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
            __all__=["loader", "ok", "naye"],
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path(file.name)
        client._path_modules[path] = old_module
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                ok = 123
                naye = object()
                _priv_loader = mock.Mock(
                    tanjun.abc.ClientLoader,
                    has_load=True,
                    load=mock.Mock(side_effect=RuntimeError("This shouldn't ever be called"))
                )
                loader = mock.Mock(
                    tanjun.abc.ClientLoader,
                    has_load=True,
                    load=mock.Mock(side_effect=RuntimeError("This shouldn't ever be called"))
                )
                __all__ = ["ok", "naye"]
                """
            )
        )
        file.flush()
        generator = client._reload_module(path)
        module = next(generator)()

        with pytest.raises(tanjun.ModuleMissingLoaders):
            generator.send(module)

        old_module.loader.load.assert_not_called()
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        assert client._path_modules[path] is old_module

    def test__reload_modules_with_system_path_and_not_loaded(self):
        client = tanjun.Client(mock.AsyncMock())
        random_path = pathlib.Path(uuid.uuid4().hex)
        generator = client._reload_module(random_path)

        with pytest.raises(tanjun.ModuleStateConflict):
            next(generator)

        assert random_path not in client._path_modules

    def test__reload_modules_with_system_path_for_unknown_path(self):
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
        )
        client = tanjun.Client(mock.AsyncMock())
        random_path = pathlib.Path(uuid.uuid4().hex)
        client._path_modules[random_path] = old_module
        generator = client._reload_module(random_path)
        next_ = next(generator)

        with pytest.raises(ModuleNotFoundError):
            next_()

        old_module.loader.load.assert_not_called()
        old_module.loader.unload.assert_not_called()
        old_module.other_loader.load.assert_not_called()
        old_module.other_loader.unload.assert_not_called()
        assert random_path in client._path_modules

    def test__reload_modules_with_system_path_rolls_back_when_new_module_loader_raises(self, file: typing.IO[str]):
        old_priv_loader = mock.Mock(tanjun.abc.ClientLoader)
        priv_loader = mock.Mock(tanjun.abc.ClientLoader, unload=mock.Mock(return_value=False))
        old_module = mock.Mock(
            loader=mock.Mock(tanjun.abc.ClientLoader, load=mock.Mock(unload=False)),
            ok=123,
            naye=object(),
            other_loader=mock.Mock(tanjun.abc.ClientLoader),
            _priv_loader=old_priv_loader,
        )
        client = tanjun.Client(mock.AsyncMock())
        path = pathlib.Path(file.name)
        client._path_modules[path] = old_module
        file.write(
            textwrap.dedent(
                """
                from unittest import mock

                import tanjun

                loader = mock.Mock(
                    tanjun.abc.ClientLoader,
                    load=mock.Mock(return_value=False, side_effect=KeyError("Aaaaaaaaaaaaa"))
                )
                ok = 123
                naye = object()
                other_loader = mock.Mock(tanjun.abc.ClientLoader)
                _priv_loader = mock.Mock(tanjun.abc.ClientLoader)
                """
            )
        )
        file.flush()
        generator = client._reload_module(path)
        module = next(generator)()

        with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
            generator.send(module)

        assert isinstance(exc_info.value.__cause__, KeyError)
        assert exc_info.value.__cause__.args == ("Aaaaaaaaaaaaa",)

        old_module.other_loader.load.assert_called_once_with(client)
        old_module.other_loader.unload.assert_called_once_with(client)
        old_module.loader.load.assert_called_once_with(client)
        old_module.loader.unload.assert_called_once_with(client)
        old_priv_loader.load.assert_not_called()
        old_priv_loader.unload.assert_not_called()
        priv_loader.load.assert_not_called()
        priv_loader.unload.assert_not_called()
        assert client._path_modules[path] is old_module

    def test_reload_modules(self):
        mock_path = mock.Mock(pathlib.Path)
        mock_gen_1 = mock.Mock(__next__=mock.Mock())
        mock_gen_1.send.side_effect = StopIteration
        mock_gen_2 = mock.Mock(__next__=mock.Mock())
        mock_gen_2.send.side_effect = StopIteration
        mock__reload_module = mock.Mock(side_effect=[mock_gen_1, mock_gen_2])

        class StubClient(tanjun.Client):
            _reload_module = mock__reload_module

        client = StubClient(mock.AsyncMock())

        result = client.reload_modules(mock_path, "ok.no.u")

        assert result is client
        mock__reload_module.assert_has_calls(
            [mock.call(mock_path.expanduser.return_value.resolve.return_value), mock.call("ok.no.u")]
        )
        mock_path.expanduser.assert_called_once_with()
        mock_path.expanduser.return_value.resolve.assert_called_once_with()
        mock_gen_1.__next__.assert_called_once_with()
        mock_gen_1.__next__.return_value.assert_called_once_with()
        mock_gen_1.send.assert_called_once_with(mock_gen_1.__next__.return_value.return_value)
        mock_gen_2.__next__.assert_called_once_with()
        mock_gen_2.__next__.return_value.assert_called_once_with()
        mock_gen_2.send.assert_called_once_with(mock_gen_2.__next__.return_value.return_value)

    def test_reload_modules_when_module_loader_raises(self):
        mock_exception = TypeError("FOO")
        mock_gen = mock.Mock(__next__=mock.Mock())
        mock_gen.__next__.return_value.side_effect = mock_exception
        mock__reload_module = mock.Mock(return_value=mock_gen)

        class StubClient(tanjun.Client):
            _reload_module = mock__reload_module

        client = StubClient(mock.AsyncMock())

        with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
            client.reload_modules("ok.no.u")

        assert exc_info.value.__cause__ is mock_exception

        mock__reload_module.assert_called_once_with("ok.no.u")
        mock_gen.__next__.assert_called_once_with()
        mock_gen.__next__.return_value.assert_called_once_with()
        mock_gen.send.assert_not_called()

    @mock.patch.object(asyncio, "get_running_loop")
    @pytest.mark.asyncio()
    async def test_reload_modules_async(self, get_running_loop: mock.Mock):
        mock_executor_result_1 = mock.Mock()
        mock_executor_result_2 = mock.Mock()
        mock_executor_result_3 = mock.Mock()
        get_running_loop.return_value.run_in_executor = mock.AsyncMock(
            side_effect=[mock_executor_result_1, mock_executor_result_2, mock_executor_result_3]
        )
        mock_path = mock.Mock(pathlib.Path)
        mock_gen_1 = mock.Mock(__next__=mock.Mock())
        mock_gen_1.send.side_effect = StopIteration
        mock_gen_2 = mock.Mock(__next__=mock.Mock())
        mock_gen_2.send.side_effect = StopIteration
        mock__reload_module = mock.Mock(side_effect=[mock_gen_1, mock_gen_2])

        class StubClient(tanjun.Client):
            _reload_module = mock__reload_module

        client = StubClient(mock.AsyncMock())

        result = await client.reload_modules_async(mock_path, "ok.no.u")

        assert result is None
        mock__reload_module.assert_has_calls([mock.call(mock_executor_result_1), mock.call("ok.no.u")])
        mock_gen_1.__next__.assert_called_once_with()
        mock_gen_1.send.assert_called_once_with(mock_executor_result_2)
        mock_gen_2.__next__.assert_called_once_with()
        mock_gen_2.send.assert_called_once_with(mock_executor_result_3)
        get_running_loop.assert_called_once_with()
        get_running_loop.return_value.run_in_executor.assert_has_calls(
            [
                mock.call(None, tanjun.clients._normalize_path, mock_path),
                mock.call(None, mock_gen_1.__next__.return_value),
                mock.call(None, mock_gen_2.__next__.return_value),
            ]
        )

    @mock.patch.object(asyncio, "get_running_loop")
    @pytest.mark.asyncio()
    async def test_reload_modules_async_when_module_loader_raises(self, get_running_loop: mock.Mock):
        mock_exception = RuntimeError("eeeee")
        get_running_loop.return_value.run_in_executor = mock.AsyncMock(side_effect=mock_exception)
        mock_gen = mock.Mock(__next__=mock.Mock())
        mock__reload_module = mock.Mock(return_value=mock_gen)

        class StubClient(tanjun.Client):
            _reload_module = mock__reload_module

        client = StubClient(mock.AsyncMock())

        with pytest.raises(tanjun.FailedModuleLoad) as exc_info:
            await client.reload_modules_async("ok.no.u")

        assert exc_info.value.__cause__ is mock_exception

        mock__reload_module.assert_called_once_with("ok.no.u")
        mock_gen.__next__.assert_called_once_with()
        mock_gen.send.assert_not_called()
        get_running_loop.assert_called_once_with()
        get_running_loop.return_value.run_in_executor.assert_called_once_with(None, mock_gen.__next__.return_value)

    # Message create event

    @pytest.fixture()
    def command_dispatch_client(self) -> tanjun.Client:
        class StubClient(tanjun.Client):
            check = mock.AsyncMock()
            dispatch_client_callback = mock.AsyncMock()

        return (
            StubClient(mock.AsyncMock())
            .set_hooks(mock.Mock())
            .set_message_hooks(mock.Mock())
            .set_slash_hooks(mock.Mock())
            .set_prefix_getter(None)
            .set_menu_hooks(mock.Mock())
        )

    @pytest.mark.asyncio()
    async def test_on_message_create_event(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_component(mock_component_1).add_component(mock_component_2).add_prefix(
            "!"
        ).set_message_ctx_maker(ctx_maker)
        mock_component_1.execute_message.return_value = True
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_prefix_getter(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        ctx_maker.return_value.call_with_async_di = mock.AsyncMock(return_value=["sex", "!"])
        prefix_getter = mock.Mock()
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_component(mock_component_1).add_component(mock_component_2).add_prefix(
            "aye"
        ).set_message_ctx_maker(ctx_maker).set_prefix_getter(prefix_getter)
        mock_component_1.execute_message.return_value = True
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        ctx_maker.return_value.call_with_async_di.assert_awaited_once_with(prefix_getter, ctx_maker.return_value)

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_no_message_content(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock()
        command_dispatch_client.set_message_ctx_maker(ctx_maker)
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_component(mock_component_1).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)

        await command_dispatch_client.on_message_create_event(mock.Mock(message=mock.Mock(content=None)))

        ctx_maker.assert_not_called()
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_prefix_not_found(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="42"))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_prefix("gay").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        mock_event = mock.Mock(message=mock.Mock(content="eye"))
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_custom_prefix_getter_not_found(
        self, command_dispatch_client: tanjun.Client
    ):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="42"))
        ctx_maker.return_value.call_with_async_di = mock.AsyncMock(return_value=["aye", "naye"])
        prefix_getter = mock.Mock()
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_prefix("gay").set_message_ctx_maker(ctx_maker).set_prefix_getter(
            prefix_getter
        ).add_component(mock_component_1).add_component(mock_component_2)
        mock_event = mock.Mock(message=mock.Mock(content="eye"))
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        ctx_maker.return_value.call_with_async_di.assert_called_once_with(prefix_getter, ctx_maker.return_value)

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_only_message_hooks(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_1.execute_message.return_value = True
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).set_hooks(None).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_only_generic_hooks(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_1.execute_message.return_value = True
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).set_message_hooks(None).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_no_hooks(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_1.execute_message.return_value = True
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).set_hooks(None).set_message_hooks(
            None
        ).add_component(mock_component_1).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(ctx_maker.return_value, hooks=None)
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("eee")
        command_dispatch_client.check.side_effect.send = mock.AsyncMock()
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.check.side_effect.send.assert_awaited_once_with(ctx_maker.return_value)
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.HaltExecution()
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx_maker.return_value
        )

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_checks_returns_false(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = False
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx_maker.return_value
        )

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_1.execute_message.return_value = False
        mock_component_2.execute_message.side_effect = tanjun.CommandError("eeea")
        mock_component_2.execute_message.side_effect.send = mock.AsyncMock()
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.side_effect.send.assert_awaited_once_with(ctx_maker.return_value)
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_1.execute_message.return_value = False
        mock_component_2.execute_message.side_effect = tanjun.HaltExecution
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx_maker.return_value
        )

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_not_found(self, command_dispatch_client: tanjun.Client):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="!  42", respond=mock.AsyncMock()))
        ctx_maker.return_value.set_content.return_value = ctx_maker.return_value
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_1.execute_message.return_value = False
        mock_component_2.execute_message.return_value = False
        command_dispatch_client.add_prefix("!").set_message_ctx_maker(ctx_maker).add_component(
            mock_component_1
        ).add_component(mock_component_2)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
            register_task=command_dispatch_client._add_task,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx_maker.return_value
        )

    # Interaction create event

    @pytest.mark.asyncio()
    async def test__on_menu_not_found(self):
        dispatch_client_callback_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            dispatch_client_callback = dispatch_client_callback_

        client = StubClient(mock.AsyncMock).set_menu_not_found("gay")
        ctx = mock.AsyncMock(has_responded=False)

        await client._on_menu_not_found(ctx)

        ctx.create_initial_response.assert_awaited_once_with("gay")
        dispatch_client_callback_.assert_awaited_once_with(tanjun.ClientCallbackNames.MENU_COMMAND_NOT_FOUND, ctx)

    @pytest.mark.asyncio()
    async def test__on_menu_not_found_when_already_responded(self):
        dispatch_client_callback_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            dispatch_client_callback = dispatch_client_callback_

        client = StubClient(mock.AsyncMock).set_menu_not_found("gay")
        ctx = mock.AsyncMock(has_responded=True)

        await client._on_menu_not_found(ctx)

        ctx.create_initial_response.assert_not_called()
        dispatch_client_callback_.assert_awaited_once_with(tanjun.ClientCallbackNames.MENU_COMMAND_NOT_FOUND, ctx)

    @pytest.mark.asyncio()
    async def test__on_menu_not_found_when_not_found_messages_disabled(self):
        dispatch_client_callback_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            dispatch_client_callback = dispatch_client_callback_

        client = StubClient(mock.AsyncMock).set_menu_not_found(None)
        ctx = mock.AsyncMock(has_responded=False)

        await client._on_menu_not_found(ctx)

        ctx.create_initial_response.assert_not_called()
        dispatch_client_callback_.assert_awaited_once_with(tanjun.ClientCallbackNames.MENU_COMMAND_NOT_FOUND, ctx)

    @pytest.mark.asyncio()
    async def test__on_slash_not_found(self):
        dispatch_client_callback_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            dispatch_client_callback = dispatch_client_callback_

        client = StubClient(mock.AsyncMock).set_interaction_not_found("gay")
        ctx = mock.AsyncMock(has_responded=False)

        await client._on_slash_not_found(ctx)

        ctx.create_initial_response.assert_awaited_once_with("gay")
        dispatch_client_callback_.assert_awaited_once_with(tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)

    @pytest.mark.asyncio()
    async def test__on_slash_not_found_when_already_responded(self):
        dispatch_client_callback_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            dispatch_client_callback = dispatch_client_callback_

        client = StubClient(mock.AsyncMock).set_interaction_not_found("gay")
        ctx = mock.AsyncMock(has_responded=True)

        await client._on_slash_not_found(ctx)

        ctx.create_initial_response.assert_not_called()
        dispatch_client_callback_.assert_awaited_once_with(tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)

    @pytest.mark.asyncio()
    async def test__on_slash_not_found_when_not_found_messages_disabled(self):
        dispatch_client_callback_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            dispatch_client_callback = dispatch_client_callback_

        client = StubClient(mock.AsyncMock).set_interaction_not_found(None)
        ctx = mock.AsyncMock(has_responded=False)

        await client._on_slash_not_found(ctx)

        ctx.create_initial_response.assert_not_called()
        dispatch_client_callback_.assert_awaited_once_with(tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)

    @pytest.mark.asyncio()
    async def test_on_gateway_autocomplete_create(self, command_dispatch_client: tanjun.Client):
        mock_component_1 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_2 = mock.Mock(execute_autocomplete=mock.AsyncMock())
        mock_component_3 = mock.Mock(execute_autocomplete=mock.Mock())
        mock_make_ctx = mock.Mock()
        (
            command_dispatch_client.set_autocomplete_ctx_maker(mock_make_ctx)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .add_component(mock_component_3)
        )
        mock_interaction = mock.Mock()

        result = await command_dispatch_client.on_gateway_autocomplete_create(mock_interaction)

        assert result is None
        mock_component_1.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_2.execute_autocomplete.assert_awaited_once_with(mock_make_ctx.return_value)
        mock_component_3.execute_autocomplete.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_gateway_autocomplete_create_when_not_found(self, command_dispatch_client: tanjun.Client):
        mock_component_1 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_2 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_3 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_make_ctx = mock.Mock()
        (
            command_dispatch_client.set_autocomplete_ctx_maker(mock_make_ctx)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .add_component(mock_component_3)
        )
        mock_interaction = mock.Mock()

        result = await command_dispatch_client.on_gateway_autocomplete_create(mock_interaction)

        assert result is None
        mock_component_1.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_2.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_3.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_slash.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_menu.assert_not_called()
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_ephemeral_default(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found(None)
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .set_ephemeral_default(True)
        )
        mock_component_1.execute_slash.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_slash.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=True,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_not_auto_deferring(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_not_called()
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_no_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_slash_hooks(None)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_slash.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_component_2.execute_slash.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_only_slash_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_slash.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.slash_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_only_generic_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_slash_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_slash.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_not_found(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")
        command_dispatch_client.check.side_effect.send = mock.AsyncMock()

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        command_dispatch_client.check.side_effect.send.assert_awaited_once_with(mock_ctx_maker.return_value)
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.HaltExecution()

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.side_effect = tanjun.CommandError("123321")
        mock_component_2.execute_slash.side_effect.send = mock.AsyncMock()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.side_effect.send.assert_awaited_once_with(mock_ctx_maker.return_value)
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.side_effect = tanjun.HaltExecution
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_slash_command_when_checks_fail(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_slash.return_value = None
        mock_component_2.execute_slash.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = False

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_slash_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_menu.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_slash.assert_not_called()
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_ephemeral_default(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found(None)
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .set_ephemeral_default(True)
        )
        mock_component_1.execute_menu.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_menu.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=True,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_not_auto_deferring(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_not_called()
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_no_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_menu_hooks(None)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_menu.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_component_2.execute_menu.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_only_menu_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_menu.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.menu_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_only_generic_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_menu_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_menu.return_value = mock_future()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_not_found(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")
        command_dispatch_client.check.side_effect.send = mock.AsyncMock()

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        command_dispatch_client.check.side_effect.send.assert_awaited_once_with(mock_ctx_maker.return_value)
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.HaltExecution()

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.side_effect = tanjun.CommandError("123321")
        mock_component_2.execute_menu.side_effect.send = mock.AsyncMock()
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.side_effect.send.assert_awaited_once_with(mock_ctx_maker.return_value)
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.side_effect = tanjun.HaltExecution
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_gateway_command_create_for_menu_command_when_checks_fail(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_component_1.execute_menu.return_value = None
        mock_component_2.execute_menu.return_value = None
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = False

        await command_dispatch_client.on_gateway_command_create(mock_interaction)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            interaction=mock_interaction,
            register_task=command_dispatch_client._add_task,
            on_not_found=command_dispatch_client._on_menu_not_found,
            default_to_ephemeral=False,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_for_command_interaction(self, command_dispatch_client: tanjun.Client):
        mock_event = mock.Mock(
            interaction=mock.Mock(hikari.CommandInteraction, type=hikari.InteractionType.APPLICATION_COMMAND)
        )
        command_dispatch_client.on_gateway_autocomplete_create = mock.AsyncMock()
        command_dispatch_client.on_gateway_command_create = mock.AsyncMock()

        await command_dispatch_client.on_interaction_create_event(mock_event)

        command_dispatch_client.on_gateway_command_create.assert_awaited_once_with(mock_event.interaction)
        command_dispatch_client.on_gateway_autocomplete_create.assert_not_called()

    @pytest.mark.parametrize("allow", [tanjun.InteractionAcceptsEnum.NONE, tanjun.InteractionAcceptsEnum.AUTOCOMPLETE])
    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_for_command_interaction_when_commands_disabled(
        self, command_dispatch_client: tanjun.Client, allow: tanjun.InteractionAcceptsEnum
    ):
        command_dispatch_client.set_interaction_accepts(allow)
        mock_event = mock.Mock(
            interaction=mock.Mock(hikari.CommandInteraction, type=hikari.InteractionType.APPLICATION_COMMAND)
        )
        command_dispatch_client.on_gateway_autocomplete_create = mock.AsyncMock()
        command_dispatch_client.on_gateway_command_create = mock.AsyncMock()

        await command_dispatch_client.on_interaction_create_event(mock_event)

        command_dispatch_client.on_gateway_command_create.assert_not_called()
        command_dispatch_client.on_gateway_autocomplete_create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_for_autocomplete_interaction(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_event = mock.Mock(
            interaction=mock.Mock(hikari.AutocompleteInteraction, type=hikari.InteractionType.AUTOCOMPLETE)
        )
        command_dispatch_client.on_gateway_autocomplete_create = mock.AsyncMock()
        command_dispatch_client.on_gateway_command_create = mock.AsyncMock()

        await command_dispatch_client.on_interaction_create_event(mock_event)

        command_dispatch_client.on_gateway_command_create.assert_not_called()
        command_dispatch_client.on_gateway_autocomplete_create.assert_awaited_once_with(mock_event.interaction)

    @pytest.mark.parametrize("allow", [tanjun.InteractionAcceptsEnum.NONE, tanjun.InteractionAcceptsEnum.COMMANDS])
    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_for_autocomplete_interaction_when_autocomplete_disabled(
        self, command_dispatch_client: tanjun.Client, allow: tanjun.InteractionAcceptsEnum
    ):
        command_dispatch_client.set_interaction_accepts(allow)
        mock_event = mock.Mock(
            interaction=mock.Mock(hikari.AutocompleteInteraction, type=hikari.InteractionType.AUTOCOMPLETE)
        )
        command_dispatch_client.on_gateway_autocomplete_create = mock.AsyncMock()
        command_dispatch_client.on_gateway_command_create = mock.AsyncMock()

        await command_dispatch_client.on_interaction_create_event(mock_event)

        command_dispatch_client.on_gateway_command_create.assert_not_called()
        command_dispatch_client.on_gateway_autocomplete_create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_for_unknown_interaction_type(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_event = mock.Mock(interaction=mock.Mock(hikari.PartialInteraction, type=-1))
        command_dispatch_client.on_gateway_autocomplete_create = mock.AsyncMock()
        command_dispatch_client.on_gateway_command_create = mock.AsyncMock()

        await command_dispatch_client.on_interaction_create_event(mock_event)

        command_dispatch_client.on_gateway_command_create.assert_not_called()
        command_dispatch_client.on_gateway_autocomplete_create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_autocomplete_interaction_request(self, command_dispatch_client: tanjun.Client):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.AutocompleteContext):
            nonlocal task
            assert ctx is mock_make_ctx.return_value
            mock_make_ctx.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_component_1 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_2 = mock.Mock(execute_autocomplete=mock.Mock(side_effect=execution_callback))
        mock_component_3 = mock.Mock(execute_autocomplete=mock.Mock())
        mock_make_ctx = mock.Mock()
        (
            command_dispatch_client.set_autocomplete_ctx_maker(mock_make_ctx)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .add_component(mock_component_3)
        )
        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_interaction = mock.Mock()

        result = await command_dispatch_client.on_autocomplete_interaction_request(mock_interaction)

        assert result is mock_result
        mock_component_1.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_2.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_3.execute_autocomplete.assert_not_called()
        mock_add_task.assert_called_once_with(task)

    @pytest.mark.asyncio()
    async def test_on_autocomplete_interaction_request_when_no_result_set(self, command_dispatch_client: tanjun.Client):
        task = None

        async def execution_callback(ctx: tanjun.abc.AutocompleteContext):
            nonlocal task
            assert ctx is mock_make_ctx.return_value
            task = asyncio.current_task()

        mock_component_1 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_2 = mock.Mock(execute_autocomplete=mock.Mock(side_effect=execution_callback))
        mock_component_3 = mock.Mock(execute_autocomplete=mock.Mock())
        mock_make_ctx = mock.Mock()
        (
            command_dispatch_client.set_autocomplete_ctx_maker(mock_make_ctx)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .add_component(mock_component_3)
        )
        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_interaction = mock.Mock()

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_autocomplete_interaction_request(mock_interaction)

        mock_component_1.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_2.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_3.execute_autocomplete.assert_not_called()
        mock_add_task.assert_called_once_with(task)

    @pytest.mark.asyncio()
    async def test_on_autocomplete_interaction_request_when_not_found(self, command_dispatch_client: tanjun.Client):
        mock_component_1 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_2 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_component_3 = mock.Mock(execute_autocomplete=mock.Mock(return_value=None))
        mock_make_ctx = mock.Mock()
        (
            command_dispatch_client.set_autocomplete_ctx_maker(mock_make_ctx)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .add_component(mock_component_3)
        )
        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_interaction = mock.Mock()

        with pytest.raises(RuntimeError, match="Autocomplete not found for .*"):
            await command_dispatch_client.on_autocomplete_interaction_request(mock_interaction)

        mock_component_1.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_2.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_component_3.execute_autocomplete.assert_called_once_with(mock_make_ctx.return_value)
        mock_add_task.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command(self, command_dispatch_client: tanjun.Client):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.SlashContext, hooks: typing.Optional[tanjun.abc.SlashHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_slash.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_menu.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_future_not_set(
        self, command_dispatch_client: tanjun.Client
    ):
        task = None

        async def execution_callback(ctx: tanjun.abc.SlashContext, hooks: typing.Optional[tanjun.abc.SlashHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_ephemeral_default(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.SlashContext, hooks: typing.Optional[tanjun.abc.SlashHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found(None)
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .set_ephemeral_default(True)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is True
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_not_auto_deferring(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                id=654234123,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_not_called()
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_no_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.SlashContext, hooks: typing.Optional[tanjun.abc.SlashHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_slash_hooks(None)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_component_2.execute_slash.assert_called_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_only_slash_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.SlashContext, hooks: typing.Optional[tanjun.abc.SlashHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_only_generic_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.SlashContext, hooks: typing.Optional[tanjun.abc.SlashHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_slash_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_slash.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_not_found(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_not_found_and_no_result(
        self, command_dispatch_client: tanjun.Client
    ):
        task = None

        async def not_found_callback():
            nonlocal task
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def error_send_callback(ctx: tanjun.abc.Context):
            nonlocal task
            assert ctx is mock_ctx_maker.return_value
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.Mock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")
        command_dispatch_client.check.side_effect.send = error_send_callback

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_checks_raise_command_error_and_result_not_given(
        self, command_dispatch_client: tanjun.Client
    ):
        task = None

        async def error_send_callback(ctx: tanjun.abc.Context):
            nonlocal task
            assert ctx is mock_ctx_maker.return_value
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.Mock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")
        command_dispatch_client.check.side_effect.send = error_send_callback

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.HaltExecution()

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def error_send_callback(ctx: tanjun.abc.Context):
            nonlocal task
            assert ctx is mock_ctx_maker.return_value
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.AsyncMock(side_effect=tanjun.CommandError("123321"))
        )
        mock_component_2.execute_slash.side_effect.send = error_send_callback
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_slash=mock.AsyncMock(side_effect=tanjun.HaltExecution)
        )
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_slash.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_slash_command_when_checks_fail(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.SlashContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.SLASH,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_slash=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.SLASH)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = False

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_slash_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_slash.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command(self, command_dispatch_client: tanjun.Client):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.MenuContext, hooks: typing.Optional[tanjun.abc.MenuHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_1.execute_slash.assert_not_called()
        mock_component_2.execute_menu.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_slash.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_future_not_set(
        self, command_dispatch_client: tanjun.Client
    ):
        task = None

        async def execution_callback(ctx: tanjun.abc.MenuContext, hooks: typing.Optional[tanjun.abc.MenuHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_ephemeral_default(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.MenuContext, hooks: typing.Optional[tanjun.abc.MenuHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found(None)
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
            .set_ephemeral_default(True)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is True
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_not_auto_deferring(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                id=654234123,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_not_called()
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_no_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.MenuContext, hooks: typing.Optional[tanjun.abc.MenuHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(),
            execute_menu=mock.Mock(side_effect=execution_callback),
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_menu_hooks(None)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_component_2.execute_menu.assert_called_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_only_menu_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.MenuContext, hooks: typing.Optional[tanjun.abc.MenuHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_only_generic_hooks(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def execution_callback(ctx: tanjun.abc.MenuContext, hooks: typing.Optional[tanjun.abc.MenuHooks]):
            async def _():
                nonlocal task
                assert ctx is mock_ctx_maker.return_value
                assert hooks is hooks
                mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
                task = asyncio.current_task()

            return _()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.Mock(side_effect=execution_callback)
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .set_menu_hooks(None)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_menu.assert_called_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_not_found(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_not_found_and_no_result(
        self, command_dispatch_client: tanjun.Client
    ):
        task = None

        async def not_found_callback():
            nonlocal task
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def error_send_callback(ctx: tanjun.abc.Context):
            nonlocal task
            assert ctx is mock_ctx_maker.return_value
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.Mock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")
        command_dispatch_client.check.side_effect.send = error_send_callback

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_checks_raise_command_error_and_result_not_given(
        self, command_dispatch_client: tanjun.Client
    ):
        task = None

        async def error_send_callback(ctx: tanjun.abc.Context):
            nonlocal task
            assert ctx is mock_ctx_maker.return_value
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.Mock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")
        command_dispatch_client.check.side_effect.send = error_send_callback

        with pytest.raises(asyncio.CancelledError):
            await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.USER,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.USER)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.HaltExecution()

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def error_send_callback(ctx: tanjun.abc.Context):
            nonlocal task
            assert ctx is mock_ctx_maker.return_value
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=mock.AsyncMock(),
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.AsyncMock(side_effect=tanjun.CommandError("123321"))
        )
        mock_component_2.execute_menu.side_effect.send = error_send_callback
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(
            bind_client=mock.Mock(), execute_menu=mock.AsyncMock(side_effect=tanjun.HaltExecution)
        )
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_component_2.execute_menu.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.menu_hooks}
        )
        mock_add_task.assert_called_once_with(task)
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_command_interaction_request_for_menu_command_when_checks_fail(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_result = mock.Mock()
        task = None

        async def not_found_callback():
            nonlocal task
            mock_ctx_maker.call_args.kwargs["future"].set_result(mock_result)
            task = asyncio.current_task()

        mock_add_task = mock.Mock()
        command_dispatch_client._add_task = mock_add_task
        mock_ctx_maker = mock.Mock(
            return_value=mock.Mock(
                tanjun.context.MenuContext,
                respond=mock.AsyncMock(),
                mark_not_found=not_found_callback,
                type=hikari.CommandType.MESSAGE,
            )
        )
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock(), execute_menu=mock.AsyncMock(return_value=None))
        (
            command_dispatch_client.set_menu_ctx_maker(mock_ctx_maker)
            .set_interaction_not_found("Interaction not found")
            .set_auto_defer_after(2.2)
            .add_component(mock_component_1)
            .add_component(mock_component_2)
        )
        mock_interaction = mock.Mock(hikari.CommandInteraction, command_type=hikari.CommandType.MESSAGE)
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        command_dispatch_client.check.return_value = False

        result = await command_dispatch_client.on_command_interaction_request(mock_interaction)

        assert result is mock_result
        assert not mock_ctx_maker.call_args.args
        assert len(mock_ctx_maker.call_args.kwargs) == 6
        assert mock_ctx_maker.call_args.kwargs["client"] is command_dispatch_client
        assert mock_ctx_maker.call_args.kwargs["interaction"] is mock_interaction
        assert mock_ctx_maker.call_args.kwargs["register_task"] == command_dispatch_client._add_task
        assert mock_ctx_maker.call_args.kwargs["on_not_found"] == command_dispatch_client._on_menu_not_found
        assert mock_ctx_maker.call_args.kwargs["default_to_ephemeral"] is False
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_menu.assert_not_called()
        mock_component_2.execute_menu.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()


def test__normalize_path():
    mock_path = mock.Mock()

    result = tanjun.clients._normalize_path(mock_path)

    assert result is mock_path.expanduser.return_value.resolve.return_value
    mock_path.expanduser.assert_called_once_with()
    mock_path.expanduser.return_value.resolve.assert_called_once_with()


def test__normalize_path_when_expanduser_fails():
    mock_path = mock.Mock()
    mock_path.expanduser.side_effect = RuntimeError

    result = tanjun.clients._normalize_path(mock_path)

    assert result is mock_path.resolve.return_value
    mock_path.expanduser.assert_called_once_with()
    mock_path.resolve.assert_called_once_with()
