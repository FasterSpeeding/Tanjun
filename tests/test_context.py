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

# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

import asyncio
import types
import typing
from unittest import mock

import hikari
import pytest
from hikari import traits

import tanjun

_T = typing.TypeVar("_T")


def stub_class(
    cls: type[_T], *, clear_init: bool = False, slots: bool = True, impl_abstract: bool = True, **namespace: typing.Any
) -> type[_T]:
    if namespace:
        namespace["__slots__"] = ()

    if clear_init:
        namespace["__init__"] = lambda self: None

    if impl_abstract:
        for name in getattr(cls, "__abstractmethods__", None) or ():
            if name not in namespace:
                namespace[name] = mock.MagicMock()

    new_cls = types.new_class(cls.__name__, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)


@pytest.fixture()
def mock_client() -> tanjun.abc.Client:
    return mock.MagicMock(tanjun.abc.Client, rest=mock.AsyncMock(hikari.api.RESTClient))


@pytest.fixture()
def mock_component() -> tanjun.abc.Component:
    return mock.MagicMock(tanjun.abc.Component)


class TestBaseContext:
    @pytest.fixture()
    def context(
        self, mock_client: tanjun.abc.Client, mock_component: tanjun.abc.Component
    ) -> tanjun.context.BaseContext:
        return stub_class(tanjun.context.BaseContext)(mock_client, mock.Mock(), component=mock_component)

    def test_cache_property(self, context: tanjun.abc.Context, mock_client: tanjun.abc.Client):
        assert context.cache is mock_client.cache

    def test_client_property(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert context.client is mock_client

    def test_component_property(self, context: tanjun.context.BaseContext, mock_component: tanjun.abc.Component):
        assert context.component is mock_component

    def test_events_proprety(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert context.events is mock_client.events

    def test_server_property(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert context.server is mock_client.server

    def test_rest_property(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert context.rest is mock_client.rest

    def test_shards_property(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert context.shards is mock_client.shards

    def test_finalise(self, context: tanjun.context.BaseContext):
        context.finalise()
        assert context._final is True

    def test_set_component(self, context: tanjun.context.BaseContext):
        component = mock.Mock()

        assert context.set_component(component) is context

        assert context.component is component

    def test_set_component_when_final(self, context: tanjun.context.BaseContext):
        component = mock.Mock()
        context.finalise()

        with pytest.raises(TypeError):
            context.set_component(component)

        assert context.component is not component

    def test_get_channel(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert mock_client.cache is not None
        assert context.get_channel() is mock_client.cache.get_guild_channel.return_value
        mock_client.cache.get_guild_channel.assert_called_once_with(context.channel_id)

    def test_get_channel_when_cacheless(self, mock_component: tanjun.abc.Component):
        context = stub_class(tanjun.context.BaseContext, guild_id=None)(
            mock.Mock(cache=None), mock.Mock(), component=mock_component
        )

        assert context.get_channel() is None

    def test_get_guild(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        assert mock_client.cache is not None
        assert context.get_guild() is mock_client.cache.get_guild.return_value
        mock_client.cache.get_guild.assert_called_once_with(context.guild_id)

    def test_get_guild_when_cacheless(self, mock_component: tanjun.abc.Component):
        context = stub_class(tanjun.context.BaseContext, guild_id=None)(
            mock.Mock(cache=None), mock.Mock(), component=mock_component
        )

        assert context.get_guild() is None

    def test_get_guild_when_dm_bound(self, mock_component: tanjun.abc.Component):
        mock_client = mock.MagicMock()
        context = stub_class(tanjun.context.BaseContext, guild_id=None)(
            mock_client, mock.Mock(), component=mock_component
        )

        assert context.get_guild() is None
        mock_client.cache.get_guild.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_channel(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        result = await context.fetch_channel()

        assert result is mock_client.rest.fetch_channel.return_value
        mock_client.rest.fetch_channel.assert_called_once_with(context.channel_id)

    @pytest.mark.asyncio()
    async def test_fetch_guild(self, context: tanjun.context.BaseContext, mock_client: tanjun.abc.Client):
        result = await context.fetch_guild()

        assert result is mock_client.rest.fetch_guild.return_value
        mock_client.rest.fetch_guild.assert_called_once_with(context.guild_id)

    @pytest.mark.asyncio()
    async def test_fetch_guild_when_dm_bound(
        self, mock_client: tanjun.abc.Client, mock_component: tanjun.abc.Component
    ):
        context = stub_class(tanjun.context.BaseContext, guild_id=None)(
            mock_client, mock.Mock(), component=mock_component
        )

        result = await context.fetch_guild()

        assert result is None
        mock_client.rest.fetch_guild.assert_not_called()


class TestMessageContext:
    @pytest.fixture()
    def context(self, mock_client: tanjun.abc.Client) -> tanjun.MessageContext:
        return tanjun.MessageContext(
            mock_client,
            mock.Mock(),
            "hi there",
            mock.AsyncMock(),
            command=mock.Mock(),
            component=mock.Mock(),
            triggering_name="bonjour",
            triggering_prefix="bonhoven",
        )

    def test___repr__(self, context: tanjun.MessageContext):
        assert repr(context) == f"MessageContext <{context.message!r}, {context.command!r}>"

    def test_author_property(self, context: tanjun.MessageContext):
        assert context.author is context.message.author

    def test_channel_id_property(self, context: tanjun.MessageContext):
        assert context.channel_id is context.message.channel_id

    def test_created_at_property(self, context: tanjun.MessageContext):
        assert context.created_at is context.message.created_at

    def test_guild_id_property(self, context: tanjun.MessageContext):
        assert context.guild_id is context.message.guild_id

    def test_has_responded_property(self, context: tanjun.MessageContext):
        assert context.has_responded is False

    def test_has_responded_property_when_initial_repsonse_id_set(self, context: tanjun.MessageContext):
        context._initial_response_id = hikari.Snowflake(321123)

        assert context.has_responded is True

    def test_is_human_property(self, context: tanjun.MessageContext):
        context.message.author = mock.Mock(is_bot=False)
        context.message.webhook_id = None

        assert context.is_human is True

    def test_is_human_property_when_is_bot(self, context: tanjun.MessageContext):
        context.message.author = mock.Mock(is_bot=True)
        context.message.webhook_id = None

        assert context.is_human is False

    def test_is_human_property_when_is_webhook(self, context: tanjun.MessageContext):
        context.message.author = mock.Mock(is_bot=False)
        context.message.webhook_id = hikari.Snowflake(123321)

        assert context.is_human is False

    def test_member_property(self, context: tanjun.MessageContext):
        assert context.member is context.message.member

    def test_message_property(self, context: tanjun.MessageContext):
        assert context.message is context._message

    def test_shard_property(self, context: tanjun.MessageContext):
        mock_shard = mock.Mock()
        context._client = mock.Mock(
            shards=mock.MagicMock(spec=traits.ShardAware, shard_count=5, shards={2: mock_shard})
        )
        context._message = mock.Mock(guild_id=123321123312)

        assert context.shard is mock_shard

    def test_shard_property_when_dm(self, context: tanjun.MessageContext):
        mock_shard = mock.Mock()
        context._client = mock.Mock(shards=mock.Mock(shards={0: mock_shard}))
        context._message = mock.Mock(guild_id=None)

        assert context.shard is mock_shard

    def test_shard_property_when_no_shards(self, context: tanjun.MessageContext):
        context._client = mock.Mock(shards=None)

        assert context.shard is None

    def test_set_command(self, context: tanjun.MessageContext):
        mock_command = mock.Mock()

        assert context.set_command(mock_command) is context

        assert context.command is mock_command

    def test_set_command_when_finalised(self, context: tanjun.MessageContext):
        context.finalise()
        mock_command = mock.Mock()

        with pytest.raises(TypeError):
            context.set_command(mock_command)

        assert context.command is not mock_command

    def test_set_content(self, context: tanjun.MessageContext):
        assert context.set_content("hi") is context
        assert context.content == "hi"

    def test_set_content_when_finalised(self, context: tanjun.MessageContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.set_content("hi")

        assert context.content != "hi"

    def test_set_triggering_name(self, context: tanjun.MessageContext):
        assert context.set_triggering_name("bonjour") is context

        assert context.triggering_name == "bonjour"

    def test_set_triggering_name_when_finalised(self, context: tanjun.MessageContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.set_triggering_name("bonjour2")

        assert context.triggering_name != "bonjour2"

    def test_set_triggering_prefix(self, context: tanjun.MessageContext):
        assert context.set_triggering_prefix("bonhoven") is context

        assert context.triggering_prefix == "bonhoven"

    def test_set_triggering_prefix_when_finalised(self, context: tanjun.MessageContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.set_triggering_prefix("bonhoven2")

        assert context.triggering_prefix != "bonhoven2"

    @pytest.mark.asyncio()
    async def test_delete_initial_response(self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client):
        context._initial_response_id = hikari.Snowflake(32123)

        await context.delete_initial_response()

        mock_client.rest.delete_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_delete_initial_response_when_no_initial_response(
        self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client
    ):
        with pytest.raises(LookupError):
            await context.delete_initial_response()

        mock_client.rest.delete_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_delete_last_response(self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client):
        context._last_response_id = hikari.Snowflake(32123)

        await context.delete_last_response()

        mock_client.rest.delete_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_delete_last_response_when_no_response(
        self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client
    ):
        with pytest.raises(LookupError):
            await context.delete_last_response()

        mock_client.rest.delete_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_initial_response(self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client):
        context._initial_response_id = hikari.Snowflake(32123)
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.edit_initial_response(
            "hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[
                321243,
            ],
        )

        mock_client.rest.edit_message.assert_awaited_once_with(
            context.message.channel_id,
            32123,
            content="hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[
                321243,
            ],
        )

    @pytest.mark.asyncio()
    async def test_edit_initial_response_when_no_initial_response(
        self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client
    ):
        with pytest.raises(LookupError):
            await context.edit_initial_response("hi")

        mock_client.rest.edit_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_last_response(self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client):
        context._last_response_id = hikari.Snowflake(32123)
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.edit_last_response(
            "hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[
                321243,
            ],
        )

        mock_client.rest.edit_message.assert_awaited_once_with(
            context.message.channel_id,
            32123,
            content="hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[
                321243,
            ],
        )

    @pytest.mark.asyncio()
    async def test_edit_last_response_when_no_last_response(
        self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client
    ):
        with pytest.raises(LookupError):
            await context.edit_last_response("hi")

        mock_client.rest.edit_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_initial_response(self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client):
        context._initial_response_id = hikari.Snowflake(32123)

        message = await context.fetch_initial_response()

        assert message is mock_client.rest.fetch_message.return_value
        mock_client.rest.fetch_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_fetch_initial_response_when_no_initial_response(
        self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client
    ):
        with pytest.raises(LookupError):
            await context.fetch_initial_response()

        mock_client.rest.fetch_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_last_response(self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client):
        context._last_response_id = hikari.Snowflake(32123)

        message = await context.fetch_last_response()

        assert message is mock_client.rest.fetch_message.return_value
        mock_client.rest.fetch_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_fetch_last_response_when_no_last_response(
        self, context: tanjun.MessageContext, mock_client: tanjun.abc.Client
    ):
        context._last_response_id = None
        with pytest.raises(LookupError):
            await context.fetch_last_response()

        mock_client.rest.fetch_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_respond(self, context: tanjun.MessageContext):
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.respond(
            "hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            tts=True,
            nonce="nonce",
            reply=432123,
            mentions_everyone=False,
            mentions_reply=True,
            user_mentions=[123, 321],
            role_mentions=[555, 444],
        )

        context.message.respond.assert_awaited_once_with(
            content="hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            tts=True,
            nonce="nonce",
            reply=432123,
            mentions_everyone=False,
            mentions_reply=True,
            user_mentions=[123, 321],
            role_mentions=[555, 444],
        )
        assert context._last_response_id == context.message.respond.return_value.id
        assert context._initial_response_id == context.message.respond.return_value.id

    @pytest.mark.asyncio()
    async def test_respond_when_initial_response_id_already_set(self, context: tanjun.MessageContext):
        context._initial_response_id = hikari.Snowflake(32123)

        await context.respond("hi")

        context._initial_response_id == 32123


class TestSlashContext:
    @pytest.fixture()
    def context(self, mock_client: tanjun.abc.Client) -> tanjun.SlashContext:
        return tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.AsyncMock(),
            command=mock.Mock(),
            component=mock.Mock(),
            not_found_message="hi",
        )

    def test_author_property(self, context: tanjun.SlashContext):
        assert context.author is context.interaction.user

    def test_channel_id_property(self, context: tanjun.SlashContext):
        assert context.channel_id is context.interaction.channel_id

    def test_client_property(self, context: tanjun.abc.Context, mock_client: tanjun.abc.Client):
        assert context.client is mock_client

    def test_created_at_property(self, context: tanjun.SlashContext):
        assert context.created_at is context.interaction.created_at

    def test_guild_id_property(self, context: tanjun.SlashContext):
        assert context.guild_id is context.interaction.guild_id

    def test_has_been_deferred_property(self, context: tanjun.SlashContext):
        assert context.has_been_deferred is context._has_been_deferred

    def test_has_responded_property(self, context: tanjun.SlashContext):
        assert context.has_responded is context._has_responded

    def test_is_human_property(self, context: tanjun.SlashContext):
        assert context.is_human is True

    def test_member_property(self, context: tanjun.SlashContext):
        assert context.member is context.interaction.member

    def test_triggering_name_property(self, context: tanjun.SlashContext):
        assert context.triggering_name is context.interaction.command_name

    def test_interaction_property(self, context: tanjun.SlashContext):
        assert context.interaction is context._interaction

    @pytest.mark.asyncio()
    async def test__auto_defer_property(self, mock_client: tanjun.abc.Client):
        context = stub_class(tanjun.SlashContext, defer=mock.AsyncMock())(
            mock_client,
            mock.AsyncMock(),
            mock.Mock(),
            command=mock.Mock(),
            component=mock.Mock(),
            not_found_message="hi",
        )

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._auto_defer(0.1)

            sleep.assert_awaited_once_with(0.1)
            context.defer.assert_awaited_once_with()

    def test_cancel_defer(self, context: tanjun.SlashContext):
        context._defer_task = mock.Mock()

        context.cancel_defer()

        context._defer_task.cancel.assert_called_once_with()

    def test_cancel_defer_when_no_active_task(self, context: tanjun.SlashContext):
        context._defer_task = None
        context.cancel_defer()

    @pytest.mark.parametrize(("flags", "result"), [(hikari.UNDEFINED, hikari.MessageFlag.NONE), (6666, 6666)])
    def test__get_flags(self, context: tanjun.SlashContext, flags: hikari.UndefinedOr[int], result: int):
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
        self, context: tanjun.SlashContext, flags: hikari.UndefinedOr[int], result: int
    ):
        context.set_ephemeral_default(True)

        assert context._get_flags(flags) == result

    def test_get_response_future(self, context: tanjun.SlashContext):
        with mock.patch.object(asyncio, "get_running_loop") as get_running_loop:
            result = context.get_response_future()

            get_running_loop.assert_called_once_with()
            get_running_loop.return_value.create_future.assert_called_once_with()
            assert result is get_running_loop.return_value.create_future.return_value

    def test_get_response_future_when_future_already_exists(self, context: tanjun.SlashContext):
        mock_future = mock.Mock()
        context._response_future = mock_future

        with mock.patch.object(asyncio, "get_running_loop") as get_running_loop:
            result = context.get_response_future()

            assert result is mock_future
            get_running_loop.assert_not_called()

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_mark_not_found_with_not_found_message_for_rest_interaction(self, context: tanjun.SlashContext):
        context._response_future = mock.Mock()
        context._has_responded = False
        context._has_been_deferred = False
        context._not_found_message = "bye"

        await context.mark_not_found(flags=777)

        context._response_future.set_result.assert_called_once_with(
            context.interaction.build_response().set_flags(777).set_content("bye")
        )
        context.interaction.create_initial_response.assert_not_called()
        context.interaction.edit_initial_response.assert_not_called()

    @pytest.mark.asyncio()
    async def test_mark_not_found_with_not_found_message_for_gateway_interaction(self, context: tanjun.SlashContext):
        context._has_responded = False
        context._has_been_deferred = False
        context._response_future = None
        context._not_found_message = "hi"

        await context.mark_not_found(flags=555)

        context.interaction.create_initial_response.assert_awaited_once_with(
            hikari.ResponseType.MESSAGE_CREATE, content="hi", flags=555
        )
        context.interaction.edit_initial_response.assert_not_called()

    @pytest.mark.asyncio()
    async def test_mark_not_found_with_not_found_message_when_deferred(self, context: tanjun.SlashContext):
        context._response_future = mock.Mock()
        context._has_responded = False
        context._has_been_deferred = True
        context._not_found_message = "hi"

        await context.mark_not_found()

        context._response_future.set_result.assert_not_called()
        context.interaction.create_initial_response.assert_not_called()
        context.interaction.edit_initial_response.assert_awaited_once_with(content="hi")

    @pytest.mark.asyncio()
    async def test_mark_not_found_with_not_found_message_when_already_responded(self, context: tanjun.SlashContext):
        context._response_future = mock.Mock()
        context._has_responded = True
        context._has_been_deferred = False
        context._not_found_message = "hi"

        await context.mark_not_found()

        context._response_future.set_result.assert_not_called()
        context.interaction.create_initial_response.assert_not_called()
        context.interaction.edit_initial_response.assert_not_called()

    @pytest.mark.asyncio()
    async def test_mark_not_found_with_not_found_message_no_message(self, context: tanjun.SlashContext):
        context._response_future = mock.Mock()
        context._has_responded = False
        context._has_been_deferred = False
        context._not_found_message = None

        await context.mark_not_found()

        context._response_future.set_result.assert_not_called()
        context.interaction.create_initial_response.assert_not_called()
        context.interaction.edit_initial_response.assert_not_called()

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.parametrize(
        ("state", "flags"), [(True, hikari.MessageFlag.EPHEMERAL), (False, hikari.MessageFlag.NONE)]
    )
    @pytest.mark.asyncio()
    async def test_mark_not_found_defaults_flags(
        self, context: tanjun.SlashContext, state: bool, flags: hikari.MessageFlag
    ):
        context._response_future = mock.Mock()
        context._has_responded = False
        context._has_been_deferred = False
        context._not_found_message = "bye"
        context.set_ephemeral_default(state)

        await context.mark_not_found()

        context._response_future.set_result.assert_called_once_with(
            context.interaction.build_response().set_flags(flags).set_content("bye")
        )

    def test_start_defer_timer(self, mock_client: tanjun.abc.Client):
        context = stub_class(tanjun.SlashContext, _auto_defer=mock.Mock())(
            mock_client,
            mock.AsyncMock(),
            mock.Mock(),
            command=mock.Mock(),
            component=mock.Mock(),
            not_found_message="hi",
        )

        with mock.patch.object(asyncio, "create_task") as create_task:
            context.start_defer_timer(534123)

            context._auto_defer.assert_called_once_with(534123)
            create_task.assert_called_once_with(context._auto_defer.return_value)
            assert context._defer_task is create_task.return_value

    def test_start_defer_timer_when_already_started(self, context: tanjun.SlashContext):
        context._defer_task = mock.Mock()

        with pytest.raises(RuntimeError):
            context.start_defer_timer(321)

    def test_start_defer_timer_when_finalised(self, context: tanjun.SlashContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.start_defer_timer(123)

    def test_set_command(self, context: tanjun.SlashContext):
        mock_command = mock.Mock()

        assert context.set_command(mock_command) is context

        assert context.command is mock_command

    def test_set_command_when_finalised(self, context: tanjun.SlashContext):
        context.finalise()
        mock_command = mock.Mock()

        with pytest.raises(TypeError):
            context.set_command(mock_command)

        assert context.command is not mock_command

    def test_set_ephemeral_default(self, context: tanjun.SlashContext):
        assert context.set_ephemeral_default(True) is context
        assert context.defaults_to_ephemeral is True

    def test_set_ephemeral_default_when_finalised(self, context: tanjun.SlashContext):
        context.finalise()
        with pytest.raises(TypeError):
            context.set_ephemeral_default(True)

        assert context.defaults_to_ephemeral is False

    @pytest.mark.skip(reason="not implemented")
    async def test_defer_cancels_defer_when_not_in_defer_task(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    async def test_defer_doesnt_cancel_defer_when_in_deffer_task(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_followup(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_for_gateway_interaction(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_for_rest_interaction(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_when_already_responded(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_create_initial_response_when_deferred(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.asyncio()
    async def test_delete_initial_response(self, context: tanjun.SlashContext):
        await context.delete_initial_response()

        context.interaction.delete_initial_response.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_edit_initial_response(self, context: tanjun.SlashContext):
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.edit_initial_response(
            "bye",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=False,
            mentions_everyone=True,
            user_mentions=[123],
            role_mentions=[444],
        )

        context.interaction.edit_initial_response.assert_awaited_once_with(
            content="bye",
            attachment=mock_attachment,
            attachments=mock_attachments,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=False,
            mentions_everyone=True,
            user_mentions=[123],
            role_mentions=[444],
        )

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_edit_last_response(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.asyncio()
    async def test_fetch_initial_response(self, context: tanjun.SlashContext):
        assert await context.fetch_initial_response() is context.interaction.fetch_initial_response.return_value
        context.interaction.fetch_initial_response.assert_awaited_once_with()

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_fetch_last_response(self, context: tanjun.SlashContext):
        ...

    @pytest.mark.skip(reason="not implemented")
    @pytest.mark.asyncio()
    async def test_respond(self, context: tanjun.SlashContext):
        ...
