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

import base64
import importlib
import pathlib
import random
import tempfile
import textwrap
import typing
from unittest import mock

import hikari
import pytest

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


class Test_InjectablePrefixGetter:
    def test(self):
        mock_callback = mock.Mock()

        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as mock_descriptor:
            result = tanjun.clients._InjectablePrefixGetter(mock_callback)

            mock_descriptor.assert_called_once_with(mock_callback)

        assert result.descriptor is mock_descriptor.return_value

    def test_callback_property(self):
        mock_callback = mock.Mock()

        assert tanjun.clients._InjectablePrefixGetter(mock_callback).callback is mock_callback


class Test_InjectableListener:
    @pytest.mark.asyncio()
    async def test(self):
        mock_client = mock.Mock()
        mock_callback = mock.Mock()
        mock_event = mock.Mock()

        with mock.patch.object(
            tanjun.injecting, "CallbackDescriptor", return_value=mock.AsyncMock()
        ) as callback_descriptor:
            converter = tanjun.clients._InjectableListener(mock_client, mock_callback)

            callback_descriptor.assert_called_once_with(mock_callback)

        with mock.patch.object(tanjun.injecting, "BasicInjectionContext") as base_injection_context:
            result = await converter(mock_event)

            base_injection_context.assert_called_once_with(mock_client)

        assert result is None
        callback_descriptor.return_value.resolve.assert_called_once_with(
            base_injection_context.return_value, mock_event
        )


class TestClient:
    @pytest.mark.skip(reason="TODO")
    def test___init__(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test___repr__(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_from_gateway_bot(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_from_rest_bot(self):
        ...

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

        assert client.is_alive is client._is_alive

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

    def test_shards_property(self) -> None:
        mock_shards = mock.Mock()
        client = tanjun.Client(mock.Mock(), shards=mock_shards)

        assert client.shards is mock_shards

    @pytest.mark.asyncio()
    async def test_declare_slash_command_when_command_id_provided(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        mock_command = mock.Mock()

        result = await client.declare_slash_command(mock_command, 123321, application=54123, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            54123,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.create_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_slash_command_when_command_id_provided_and_cached_app_id(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        client._cached_application_id = hikari.Snowflake(54123123)
        mock_command = mock.Mock()

        result = await client.declare_slash_command(mock_command, 123321, guild=65234)

        assert result is rest.edit_application_command.return_value
        rest.edit_application_command.assert_called_once_with(
            54123123,
            123321,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.create_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_slash_command_when_command_id_provided_fetchs_app_id(self):
        fetch_rest_application_id_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            fetch_rest_application_id = fetch_rest_application_id_

        rest = mock.AsyncMock()
        client = StubClient(rest)
        mock_command = mock.Mock()

        result = await client.declare_slash_command(mock_command, 123321, guild=65234)

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
        rest.create_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_slash_command(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        mock_command = mock.Mock()

        result = await client.declare_slash_command(mock_command, application=54123, guild=65234)

        assert result is rest.create_application_command.return_value
        rest.create_application_command.assert_called_once_with(
            54123,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_slash_command_when_cached_app_id(self):
        rest = mock.AsyncMock()
        client = tanjun.Client(rest)
        client._cached_application_id = hikari.Snowflake(54123123)
        mock_command = mock.Mock()

        result = await client.declare_slash_command(mock_command, guild=65234)

        assert result is rest.create_application_command.return_value
        rest.create_application_command.assert_called_once_with(
            54123123,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.asyncio()
    async def test_declare_slash_command_fetchs_app_id(self):
        fetch_rest_application_id_ = mock.AsyncMock()

        class StubClient(tanjun.Client):
            fetch_rest_application_id = fetch_rest_application_id_

        rest = mock.AsyncMock()
        client = StubClient(rest)
        mock_command = mock.Mock()

        result = await client.declare_slash_command(mock_command, guild=65234)

        assert result is rest.create_application_command.return_value
        rest.create_application_command.assert_called_once_with(
            fetch_rest_application_id_.return_value,
            guild=65234,
            name=mock_command.build.return_value.name,
            description=mock_command.build.return_value.description,
            options=mock_command.build.return_value.options,
        )
        fetch_rest_application_id_.assert_called_once_with()
        rest.edit_application_command.assert_not_called()
        mock_command.build.assert_called_once_with()
        mock_command.set_tracked_command.assert_not_called()

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_declare_slash_commands(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_set_hikari_trait_injectors(self):
        ...

    @pytest.mark.skip(reason="TODO")
    async def test_clear_commands(self):
        ...

    @pytest.mark.skip(reason="TODO")
    async def test_set_global_commands(self):
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

        client.remove_check(mock_check)

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
        mock_check_1 = mock.Mock(return_value=True)
        mock_check_2 = mock.AsyncMock(return_value=True)
        mock_check_3 = mock.AsyncMock(return_value=True)
        mock_context = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        assert await client.check(mock_context) is True

        mock_check_1.assert_called_once_with(mock_context)
        mock_check_2.assert_awaited_once_with(mock_context)
        mock_check_3.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_check_when_one_returns_false(self):
        mock_check_1 = mock.Mock(return_value=True)
        mock_check_2 = mock.AsyncMock(return_value=False)
        mock_check_3 = mock.AsyncMock(return_value=True)
        mock_context = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        assert await client.check(mock_context) is False

        mock_check_1.assert_called_once_with(mock_context)
        mock_check_2.assert_awaited_once_with(mock_context)
        mock_check_3.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_check_when_one_raises(self):
        mock_check_1 = mock.Mock(return_value=True)
        mocK_exception = Exception("test")
        mock_check_2 = mock.AsyncMock(side_effect=mocK_exception)
        mock_check_3 = mock.AsyncMock(return_value=True)
        mock_context = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        with pytest.raises(Exception, match="test") as exc:
            await client.check(mock_context)

        assert exc.value is mocK_exception

        mock_check_1.assert_called_once_with(mock_context)
        mock_check_2.assert_awaited_once_with(mock_context)
        mock_check_3.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_check_when_one_raises_failed_check(self):
        mock_check_1 = mock.Mock(return_value=True)
        mock_check_2 = mock.AsyncMock(side_effect=tanjun.FailedCheck())
        mock_check_3 = mock.AsyncMock(return_value=True)
        mock_context = mock.Mock()
        client = tanjun.Client(mock.Mock()).add_check(mock_check_1).add_check(mock_check_2).add_check(mock_check_3)

        assert await client.check(mock_context) is False

        mock_check_1.assert_called_once_with(mock_context)
        mock_check_2.assert_awaited_once_with(mock_context)
        mock_check_3.assert_awaited_once_with(mock_context)

    @pytest.mark.skip(reason="TODO")
    def test_add_component(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_component_when_already_present(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_component_when_add_injector(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_add_component_when_is_alive(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_component(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_component_when_not_present(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_component_when_is_alive(self):
        ...

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

        client.remove_listener(hikari.GuildTypingEvent, mock_callback)

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

    @pytest.mark.skip(reason="TODO")
    def test_remove_listener_when_alive(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_listener_when_alive_and_events(self):
        ...

    @pytest.mark.skip(reason="TODO")
    def test_remove_listener_when_events(self):
        ...

    def test_with_listener(self):
        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())
        mock_callback = mock.Mock()

        result = client.with_listener(hikari.GuildAvailableEvent)(mock_callback)

        assert result is mock_callback
        add_listener_.assert_called_once_with(hikari.GuildAvailableEvent, mock_callback)

    def test_add_prefix(self):
        client = tanjun.Client(mock.Mock())

        result = client.add_prefix("aye")

        assert result is client
        assert "aye" in client.prefixes

    def test_add_prefix_when_already_present(self):
        client = tanjun.Client(mock.Mock()).add_prefix("lmao")

        result = client.add_prefix("lmao")

        assert result is client
        list(client.prefixes).count("lmao") == 1

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

        client.remove_prefix("lmao")

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

    def test_load_modules_with_system_path(self):
        add_component_ = mock.Mock()
        add_client_callback_ = mock.Mock()

        class MockClient(tanjun.Client):
            add_component = add_component_

            add_client_callback = add_client_callback_

        client = MockClient(mock.AsyncMock())

        # A try, finally is used to delete the file rather than relying on delete=True behaviour
        # as on Windows the file cannot be accessed by other processes if delete is True.
        file = tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False)
        path = pathlib.Path(file.name)
        try:
            with file:
                file.write(
                    textwrap.dedent(
                        """
                        import tanjun

                        foo = 5686544536876
                        bar = object()

                        class FullMetal:
                            ...

                        @tanjun.as_loader
                        def load_module(client: tanjun.abc.Client) -> None:
                            assert isinstance(client, tanjun.Client)
                            client.add_component(123)
                            client.add_client_callback(4312)
                    """
                    )
                )
                file.flush()

            client.load_modules(path)

            add_component_.assert_called_once_with(123)
            add_client_callback_.assert_called_once_with(4312)

        finally:
            path.unlink(missing_ok=False)

    def test_load_modules_with_system_path_for_unknown_path(self):
        class MockClient(tanjun.Client):
            add_component = mock.Mock()
            add_client_callback = mock.Mock()

        client = MockClient(mock.AsyncMock())
        random_path = pathlib.Path(base64.urlsafe_b64encode(random.randbytes(64)).decode())

        with pytest.raises(RuntimeError):
            client.load_modules(random_path)

    def test_load_modules_with_python_module_path(self):
        client = tanjun.Client(mock.AsyncMock())

        mock_module = mock.Mock(object=123, foo="ok", loader=mock.Mock(tanjun.clients._LoadableDescriptor), no=object())

        with mock.patch.object(importlib, "import_module", return_value=mock_module) as import_module:
            client.load_modules("okokok.no.u")

            import_module.assert_called_once_with("okokok.no.u")

        mock_module.loader.assert_called_once_with(client)

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
            .set_prefix_getter(mock.AsyncMock())
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_message_create_event_when_custom_prefix_getter_not_found(
        self, command_dispatch_client: tanjun.Client
    ):
        ctx_maker = mock.Mock(return_value=mock.Mock(content="42"))
        prefix_getter = mock.AsyncMock(return_value=["aye", "naye"])
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.message_hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_not_called()
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(
            ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_not_called()
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_awaited_once_with(ctx_maker.return_value, hooks=None)
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_not_called()
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
        mock_event = mock.Mock(message=mock.Mock(content="eye"))

        await command_dispatch_client.on_message_create_event(mock_event)

        ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_awaited_once_with("eee")
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_not_called()
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
        )
        ctx_maker.return_value.set_content.assert_called_once_with("42")
        ctx_maker.return_value.set_triggering_prefix.assert_called_once_with("!")
        command_dispatch_client.check.assert_awaited_once_with(ctx_maker.return_value)
        mock_component_1.execute_message.assert_not_called()
        mock_component_2.execute_message.assert_not_called()
        ctx_maker.return_value.respond.assert_not_called()
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
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
        ctx_maker.return_value.respond.assert_awaited_once_with("eeea")
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
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
        ctx_maker.return_value.respond.assert_not_called()
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
            injection_client=command_dispatch_client,
            content="eye",
            message=mock_event.message,
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
        ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx_maker.return_value
        )

    # Interaction create event

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_interaction.return_value = mock_future()
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.parametrize("interaction_type", [hikari.MessageInteraction])
    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_not_message_interaction(
        self, command_dispatch_client: tanjun.Client, interaction_type: type[hikari.PartialInteraction]
    ):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).add_component(mock_component_1).add_component(
            mock_component_2
        )
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)

        await command_dispatch_client.on_interaction_create_event(mock.Mock(interaction=mock.Mock(interaction_type)))

        mock_ctx_maker.assert_not_called()
        mock_component_1.execute_interaction.assert_not_called()
        mock_component_2.execute_interaction.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_no_interaction_not_found_message(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            None
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_interaction.return_value = mock_future()
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message=None,
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_not_auto_deferring(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(None).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.return_value = None
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_not_called()
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, mock_ctx_maker.return_value
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_no_hooks(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).set_slash_hooks(None).set_hooks(None).add_component(mock_component_1).add_component(
            mock_component_2
        )
        mock_component_1.execute_interaction.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_interaction.return_value = mock_future()
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_component_2.execute_interaction.assert_awaited_once_with(mock_ctx_maker.return_value, hooks=None)
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_only_slash_hooks(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).set_hooks(None).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_interaction.return_value = mock_future()
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.slash_hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_only_generic_hooks(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).set_slash_hooks(None).add_component(mock_component_1).add_component(
            mock_component_2
        )
        mock_component_1.execute_interaction.return_value = None
        mock_future = mock.AsyncMock()
        mock_component_2.execute_interaction.return_value = mock_future()
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks}
        )
        mock_future.assert_awaited_once()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_not_found(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.return_value = None
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, mock_ctx_maker.return_value
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.return_value = None
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.CommandError("3903939")

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_not_called()
        mock_component_2.execute_interaction.assert_not_called()
        mock_ctx_maker.return_value.respond.assert_awaited_once_with("3903939")
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.return_value = None
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.side_effect = tanjun.HaltExecution()

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_not_called()
        mock_component_2.execute_interaction.assert_not_called()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, mock_ctx_maker.return_value
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.side_effect = tanjun.CommandError("123321")
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.respond.assert_awaited_once_with("123321")
        command_dispatch_client.dispatch_client_callback.assert_not_called()
        mock_ctx_maker.return_value.mark_not_found.assert_not_called()
        mock_ctx_maker.return_value.cancel_defer.assert_not_called()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.side_effect = tanjun.HaltExecution
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = True

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_component_2.execute_interaction.assert_awaited_once_with(
            mock_ctx_maker.return_value, hooks={command_dispatch_client.hooks, command_dispatch_client.slash_hooks}
        )
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, mock_ctx_maker.return_value
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    @pytest.mark.asyncio()
    async def test_on_interaction_create_event_when_checks_fail(self, command_dispatch_client: tanjun.Client):
        mock_ctx_maker = mock.Mock(return_value=mock.Mock(respond=mock.AsyncMock(), mark_not_found=mock.AsyncMock()))
        mock_component_1 = mock.AsyncMock(bind_client=mock.Mock())
        mock_component_2 = mock.AsyncMock(bind_client=mock.Mock())
        command_dispatch_client.set_slash_ctx_maker(mock_ctx_maker).set_interaction_not_found(
            "Interaction not found"
        ).set_auto_defer_after(2.2).add_component(mock_component_1).add_component(mock_component_2)
        mock_component_1.execute_interaction.return_value = None
        mock_component_2.execute_interaction.return_value = None
        mock_event = mock.Mock(interaction=mock.Mock(hikari.CommandInteraction))
        assert isinstance(command_dispatch_client.check, mock.AsyncMock)
        assert isinstance(command_dispatch_client.dispatch_client_callback, mock.AsyncMock)
        command_dispatch_client.check.return_value = False

        await command_dispatch_client.on_interaction_create_event(mock_event)

        mock_ctx_maker.assert_called_once_with(
            client=command_dispatch_client,
            injection_client=command_dispatch_client,
            interaction=mock_event.interaction,
            not_found_message="Interaction not found",
        )
        mock_ctx_maker.return_value.start_defer_timer.assert_called_once_with(2.2)
        mock_component_1.execute_interaction.assert_not_called()
        mock_component_2.execute_interaction.assert_not_called()
        mock_ctx_maker.return_value.respond.assert_not_called()
        command_dispatch_client.dispatch_client_callback.assert_awaited_once_with(
            tanjun.ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, mock_ctx_maker.return_value
        )
        mock_ctx_maker.return_value.mark_not_found.assert_awaited_once_with()
        mock_ctx_maker.return_value.cancel_defer.assert_called_once_with()

    # Note, these will likely need to be more integrationy than the above tests to ensure there's no deadlocking
    # behaviour around ctx and its owned future.
    # Interaction create REST request
    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request(self, command_dispatch_client: tanjun.Client):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_no_interaction_not_found_message(
        self, command_dispatch_client: tanjun.Client
    ):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_not_auto_deferring(self, command_dispatch_client: tanjun.Client):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_no_hooks(self, command_dispatch_client: tanjun.Client):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_only_slash_hooks(self, command_dispatch_client: tanjun.Client):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_only_generic_hooks(self, command_dispatch_client: tanjun.Client):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_not_found(self, command_dispatch_client: tanjun.Client):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_checks_raise_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_checks_raise_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_component_raises_command_error(
        self, command_dispatch_client: tanjun.Client
    ):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_component_raises_halt_execution(
        self, command_dispatch_client: tanjun.Client
    ):
        ...

    @pytest.mark.skip(reason="TODO")
    @pytest.mark.asyncio()
    async def test_on_interaction_create_request_when_checks_fail(self, command_dispatch_client: tanjun.Client):
        ...
