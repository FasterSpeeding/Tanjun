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
# pyright: reportPrivateUsage=none
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


def stub_class(cls: type[_T], /, **namespace: typing.Any) -> type[_T]:
    namespace["__slots__"] = ()

    for name in getattr(cls, "__abstractmethods__", None) or ():
        if name not in namespace:
            namespace[name] = mock.MagicMock()

    name = origin.__name__ if (origin := getattr(cls, "__origin__", None)) else cls.__name__
    new_cls = types.new_class(name, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)


@pytest.fixture()
def mock_client() -> tanjun.abc.Client:
    return mock.MagicMock(tanjun.abc.Client, rest=mock.AsyncMock(hikari.api.RESTClient))


@pytest.fixture()
def mock_component() -> tanjun.abc.Component:
    return mock.MagicMock(tanjun.abc.Component)


class TestBaseContext:
    @pytest.fixture()
    def context(self, mock_client: mock.Mock, mock_component: tanjun.abc.Component) -> tanjun.context.BaseContext:
        return stub_class(tanjun.context.BaseContext)(mock_client, mock.Mock(), component=mock_component)

    def test_cache_property(self, context: tanjun.abc.Context, mock_client: mock.Mock):
        assert context.cache is mock_client.cache

    def test_client_property(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        assert context.client is mock_client

    def test_component_property(self, context: tanjun.context.BaseContext, mock_component: tanjun.abc.Component):
        assert context.component is mock_component

    def test_events_proprety(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        assert context.events is mock_client.events

    def test_server_property(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        assert context.server is mock_client.server

    def test_rest_property(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        assert context.rest is mock_client.rest

    def test_shards_property(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        assert context.shards is mock_client.shards

    def test_finalise(self, context: tanjun.context.BaseContext):
        context.finalise()
        assert context._final is True

    def test_set_component(self, context: tanjun.context.BaseContext):
        component = mock.Mock()

        assert context.set_component(component) is context

        assert context.component is component
        assert context.get_type_special_case(tanjun.abc.Component) is component
        assert context.get_type_special_case(type(component)) is component

    def test_set_component_when_none_and_previously_set(self, context: tanjun.context.BaseContext):
        mock_component = mock.Mock()
        context.set_component(mock_component)
        context.set_component(None)

        assert context.component is None
        assert context.get_type_special_case(tanjun.abc.Component) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(type(mock_component)) is tanjun.injecting.UNDEFINED

    def test_set_component_when_none(self, context: tanjun.context.BaseContext):
        context.set_component(None)
        context.set_component(None)

        assert context.component is None
        assert context.get_type_special_case(tanjun.abc.Component) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(type(tanjun.abc.Component)) is tanjun.injecting.UNDEFINED

    def test_set_component_when_final(self, context: tanjun.context.BaseContext):
        component = mock.Mock()
        context.finalise()

        with pytest.raises(TypeError):
            context.set_component(component)

        assert context.component is not component

    def test_get_channel(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        assert mock_client.cache is not None
        mock_client.cache.get_guild_channel.return_value = mock.Mock(hikari.TextableGuildChannel)

        assert context.get_channel() is mock_client.cache.get_guild_channel.return_value

        mock_client.cache.get_guild_channel.assert_called_once_with(context.channel_id)

    def test_get_channel_when_cacheless(self, mock_component: tanjun.abc.Component):
        context = stub_class(tanjun.context.BaseContext, guild_id=None)(
            mock.Mock(cache=None), mock.Mock(), component=mock_component
        )

        assert context.get_channel() is None

    def test_get_guild(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
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
    async def test_fetch_channel(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        mock_client.rest.fetch_channel.return_value = mock.Mock(hikari.TextableChannel)

        result = await context.fetch_channel()

        assert result is mock_client.rest.fetch_channel.return_value
        mock_client.rest.fetch_channel.assert_called_once_with(context.channel_id)

    @pytest.mark.asyncio()
    async def test_fetch_guild(self, context: tanjun.context.BaseContext, mock_client: mock.Mock):
        result = await context.fetch_guild()

        assert result is mock_client.rest.fetch_guild.return_value
        mock_client.rest.fetch_guild.assert_called_once_with(context.guild_id)

    @pytest.mark.asyncio()
    async def test_fetch_guild_when_dm_bound(self, mock_client: mock.Mock, mock_component: tanjun.abc.Component):
        context = stub_class(tanjun.context.BaseContext, guild_id=None)(
            mock_client, mock.Mock(), component=mock_component
        )

        result = await context.fetch_guild()

        assert result is None
        mock_client.rest.fetch_guild.assert_not_called()


class TestMessageContext:
    @pytest.fixture()
    def context(self, mock_client: mock.Mock) -> tanjun.MessageContext:
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
        assert context.get_type_special_case(tanjun.abc.ExecutableCommand) is mock_command
        assert context.get_type_special_case(tanjun.abc.MessageCommand) is mock_command
        assert context.get_type_special_case(type(mock_command)) is mock_command

    def test_set_command_when_none(self, context: tanjun.MessageContext):
        context.set_command(None)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_special_case(tanjun.abc.ExecutableCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(tanjun.abc.MessageCommand) is tanjun.injecting.UNDEFINED

    def test_set_command_when_none_and_previously_set(self, context: tanjun.MessageContext):
        mock_command = mock.Mock()
        context.set_command(mock_command)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_special_case(tanjun.abc.ExecutableCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(tanjun.abc.MessageCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(type(mock_command)) is tanjun.injecting.UNDEFINED

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
    async def test_delete_initial_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        context._initial_response_id = hikari.Snowflake(32123)

        await context.delete_initial_response()

        mock_client.rest.delete_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_delete_initial_response_when_no_initial_response(
        self, context: tanjun.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.delete_initial_response()

        mock_client.rest.delete_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_delete_last_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        context._last_response_id = hikari.Snowflake(32123)

        await context.delete_last_response()

        mock_client.rest.delete_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_delete_last_response_when_no_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        with pytest.raises(LookupError):
            await context.delete_last_response()

        mock_client.rest.delete_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_initial_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        context._initial_response_id = hikari.Snowflake(32123)
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.edit_initial_response(
            "hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[321243],
        )

        mock_client.rest.edit_message.assert_awaited_once_with(
            context.message.channel_id,
            32123,
            content="hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[321243],
        )

    @pytest.mark.asyncio()
    async def test_edit_initial_response_when_no_initial_response(
        self, context: tanjun.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.edit_initial_response("hi")

        mock_client.rest.edit_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_last_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        context._last_response_id = hikari.Snowflake(32123)
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.edit_last_response(
            "hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[321243],
        )

        mock_client.rest.edit_message.assert_awaited_once_with(
            context.message.channel_id,
            32123,
            content="hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=True,
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[321243],
        )

    @pytest.mark.asyncio()
    async def test_edit_last_response_when_no_last_response(
        self, context: tanjun.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.edit_last_response("hi")

        mock_client.rest.edit_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_initial_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        context._initial_response_id = hikari.Snowflake(32123)

        message = await context.fetch_initial_response()

        assert message is mock_client.rest.fetch_message.return_value
        mock_client.rest.fetch_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_fetch_initial_response_when_no_initial_response(
        self, context: tanjun.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.fetch_initial_response()

        mock_client.rest.fetch_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_last_response(self, context: tanjun.MessageContext, mock_client: mock.Mock):
        context._last_response_id = hikari.Snowflake(32123)

        message = await context.fetch_last_response()

        assert message is mock_client.rest.fetch_message.return_value
        mock_client.rest.fetch_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_fetch_last_response_when_no_last_response(
        self, context: tanjun.MessageContext, mock_client: mock.Mock
    ):
        context._last_response_id = None
        with pytest.raises(LookupError):
            await context.fetch_last_response()

        mock_client.rest.fetch_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_respond(self, context: tanjun.MessageContext):
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.respond(
            "hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
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

        assert isinstance(context.message.respond, mock.Mock)
        context.message.respond.assert_awaited_once_with(
            content="hi",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
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


class TestSlashOption:
    def test_name_property(self):
        mock_option = mock.Mock()

        assert tanjun.SlashOption(mock.Mock(), mock_option).name is mock_option.name

    def test_type_property(self):
        mock_option = mock.Mock()

        assert tanjun.SlashOption(mock.Mock(), mock_option).type is mock_option.type

    def test_value_property(self):
        mock_option = mock.Mock()

        assert tanjun.SlashOption(mock.Mock(), mock_option).value is mock_option.value

    def test_resolve_value_for_channel_option(self):
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.CHANNEL))

        result = option.resolve_value()

        assert result is resolve_to_channel.return_value
        resolve_to_channel.assert_called_once_with()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_role_option(self):
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.ROLE))

        result = option.resolve_value()

        assert result is resolve_to_role.return_value
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_called_once_with()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_user_option(self):
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.USER))

        result = option.resolve_value()

        assert result is resolve_to_user.return_value
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_called_once_with()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_value_for_mentionable_option(self):
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.MENTIONABLE))

        result = option.resolve_value()

        assert result is resolve_to_mentionable.return_value
        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_called_once_with()

    def test_resolve_value_for_non_resolvable_option(self):
        resolve_to_channel = mock.Mock()
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        resolve_to_mentionable = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_channel=resolve_to_channel,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
            resolve_to_mentionable=resolve_to_mentionable,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.INTEGER))

        with pytest.raises(TypeError):
            option.resolve_value()

        resolve_to_channel.assert_not_called()
        resolve_to_role.assert_not_called()
        resolve_to_user.assert_not_called()
        resolve_to_mentionable.assert_not_called()

    def test_resolve_to_channel(self):
        mock_channel = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.channels = {3123321: mock_channel}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.CHANNEL, value="3123321"))

        value = option.resolve_to_channel()

        assert value is mock_channel

    def test_resolve_to_channel_for_non_channel_type(self):
        with pytest.raises(TypeError):
            tanjun.SlashOption(mock.Mock(), mock.Mock(type=hikari.OptionType.ROLE)).resolve_to_channel()

    def test_resolve_to_member(self):
        mock_member = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {421123: mock_member}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.USER, value="421123"))

        value = option.resolve_to_member()

        assert value is mock_member

    def test_resolve_to_member_when_user_only(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.USER, value="421123"))

        with pytest.raises(LookupError):
            option.resolve_to_member()

    def test_resolve_to_member_when_user_only_and_defaulting(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_result = mock.Mock()
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.USER, value="421123"))

        result = option.resolve_to_member(default=mock_result)

        assert result is mock_result

    def test_resolve_to_member_when_mentionable(self):
        mock_member = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {1122: mock_member}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_member()

        assert result is mock_member

    def test_resolve_to_member_when_mentionable_and_user_only(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {1122: mock.Mock()}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        with pytest.raises(LookupError):
            option.resolve_to_member()

    def test_resolve_to_member_when_mentionable_and_user_only_while_defaulting(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {1122: mock.Mock()}
        mock_default = mock.Mock()
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_member(default=mock_default)

        assert result is mock_default

    def test_resolve_to_member_when_mentionable_but_targets_role(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        with pytest.raises(TypeError):
            option.resolve_to_member(default=mock.Mock())

    def test_resolve_to_mentionable_for_role(self):
        mock_role = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.roles = {1122: mock_role}
        mock_interaction.resolved.users = {}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_mentionable()

        assert result is mock_role

    def test_resolve_to_mentionable_for_member(self):
        mock_member = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {1122: mock_member}
        mock_interaction.resolved.roles = {}
        mock_interaction.resolved.users = {}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_mentionable()

        assert result is mock_member

    def test_resolve_to_mentionable_when_user_only(self):
        mock_user = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.roles = {}
        mock_interaction.resolved.users = {1122: mock_user}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="1122"))

        result = option.resolve_to_mentionable()

        assert result is mock_user

    def test_resolve_to_mentionable_for_user_option_type(self):
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.USER))

        result = option.resolve_to_mentionable()

        assert result is resolve_to_user.return_value
        resolve_to_user.assert_called_once_with()
        resolve_to_role.assert_not_called()

    def test_resolve_to_mentionable_for_role_option_type(self):
        resolve_to_role = mock.Mock()
        resolve_to_user = mock.Mock()
        option = stub_class(
            tanjun.SlashOption,
            resolve_to_role=resolve_to_role,
            resolve_to_user=resolve_to_user,
        )(mock.Mock(), mock.Mock(type=hikari.OptionType.ROLE))

        result = option.resolve_to_mentionable()

        assert result is resolve_to_role.return_value
        resolve_to_role.assert_called_once_with()
        resolve_to_user.assert_not_called()

    def test_resolve_to_mentionable_when_not_mentionable(self):
        with pytest.raises(TypeError):
            tanjun.SlashOption(mock.Mock(), mock.Mock(type=hikari.OptionType.INTEGER)).resolve_to_mentionable()

    def test_resolve_to_role(self):
        mock_role = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.roles = {21321: mock_role}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.ROLE, value="21321"))

        result = option.resolve_to_role()

        assert result is mock_role

    def test_resolve_to_role_when_mentionable(self):
        mock_role = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.roles = {21321: mock_role}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="21321"))

        result = option.resolve_to_role()

        assert result is mock_role

    def test_resolve_to_role_when_mentionable_but_targets_user(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.roles = {}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="21321"))

        with pytest.raises(TypeError):
            option.resolve_to_role()

    def test_resolve_to_role_when_not_role(self):
        mock_interaction = mock.Mock()
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.INTEGER, value="21321"))

        with pytest.raises(TypeError):
            option.resolve_to_role()

    def test_resolve_to_user(self):
        mock_user = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {33333: mock_user}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.USER, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_user

    def test_resolve_to_user_when_member_present(self):
        mock_member = mock.Mock()
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {33333: mock_member}
        mock_interaction.resolved.users = {33333: mock.Mock()}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_member

    def test_resolve_to_user_when_not_user(self):
        mock_interaction = mock.Mock()
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.INTEGER, value="33333"))

        with pytest.raises(TypeError):
            option.resolve_to_user()

    def test_resolve_to_user_when_mentionable(self):
        mock_interaction = mock.Mock()
        mock_user = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {33333: mock_user}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_user

    def test_resolve_to_user_when_mentionable_and_member_present(self):
        mock_interaction = mock.Mock()
        mock_member = mock.Mock()
        mock_interaction.resolved.members = {33333: mock_member}
        mock_interaction.resolved.users = {33333: mock.Mock()}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        result = option.resolve_to_user()

        assert result is mock_member

    def test_resolve_to_user_when_mentionable_but_targets_role(self):
        mock_interaction = mock.Mock()
        mock_interaction.resolved.members = {}
        mock_interaction.resolved.users = {}
        option = tanjun.SlashOption(mock_interaction, mock.Mock(type=hikari.OptionType.MENTIONABLE, value="33333"))

        with pytest.raises(TypeError):
            option.resolve_to_user()


class TestSlashContext:
    @pytest.fixture()
    def context(self, mock_client: mock.Mock) -> tanjun.SlashContext:
        return tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.AsyncMock(options=None),
            command=mock.Mock(),
            component=mock.Mock(),
        )

    def test_author_property(self, context: tanjun.SlashContext):
        assert context.author is context.interaction.user

    def test_channel_id_property(self, context: tanjun.SlashContext):
        assert context.channel_id is context.interaction.channel_id

    def test_client_property(self, context: tanjun.abc.Context, mock_client: mock.Mock):
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

    @pytest.mark.parametrize("raw_options", [None, []])
    def test_options_property_when_no_options(
        self, mock_client: mock.Mock, raw_options: typing.Optional[list[hikari.OptionType]]
    ):
        context = tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=raw_options),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        assert context.options == {}

    def test_options_property_for_top_level_command(self, mock_client: mock.Mock):
        mock_option_1 = mock.Mock()
        mock_option_1.name = "hi"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "bye"
        context = tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2]),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        assert len(context.options) == 2
        assert context.options["hi"].type is mock_option_1.type
        assert context.options["hi"].value is mock_option_1.value
        assert context.options["hi"].name is mock_option_1.name
        assert isinstance(context.options["hi"], tanjun.SlashOption)

        assert context.options["bye"].type is mock_option_2.type
        assert context.options["bye"].value is mock_option_2.value
        assert context.options["bye"].name is mock_option_2.name
        assert isinstance(context.options["bye"], tanjun.SlashOption)

    def test_options_property_for_command_group(self, mock_client: mock.Mock):
        mock_option_1 = mock.Mock()
        mock_option_1.name = "kachow"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "nyaa"
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2])
        context = tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[group_option]),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        assert len(context.options) == 2
        assert context.options["kachow"].type is mock_option_1.type
        assert context.options["kachow"].value is mock_option_1.value
        assert context.options["kachow"].name is mock_option_1.name
        assert isinstance(context.options["kachow"], tanjun.SlashOption)

        assert context.options["nyaa"].type is mock_option_2.type
        assert context.options["nyaa"].value is mock_option_2.value
        assert context.options["nyaa"].name is mock_option_2.name
        assert isinstance(context.options["nyaa"], tanjun.SlashOption)

    @pytest.mark.parametrize("raw_options", [None, []])
    def test_options_property_for_command_group_with_no_sub_option(
        self, mock_client: mock.Mock, raw_options: typing.Optional[list[hikari.OptionType]]
    ):
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=raw_options)
        context = tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[group_option]),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        assert context.options == {}

    def test_options_property_for_sub_command_group(self, mock_client: mock.Mock):
        mock_option_1 = mock.Mock()
        mock_option_1.name = "meow"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "nya"
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2])
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        context = tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[group_option]),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        assert len(context.options) == 2
        assert context.options["meow"].type is mock_option_1.type
        assert context.options["meow"].value is mock_option_1.value
        assert context.options["meow"].name is mock_option_1.name
        assert isinstance(context.options["meow"], tanjun.SlashOption)

        assert context.options["nya"].type is mock_option_2.type
        assert context.options["nya"].value is mock_option_2.value
        assert context.options["nya"].name is mock_option_2.name
        assert isinstance(context.options["nya"], tanjun.SlashOption)

    @pytest.mark.parametrize("raw_options", [None, []])
    def test_options_property_for_sub_command_group_with_no_sub_option(
        self, mock_client: mock.Mock, raw_options: typing.Optional[list[hikari.OptionType]]
    ):
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=raw_options)
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        context = tanjun.SlashContext(
            mock_client,
            mock.Mock(),
            mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[group_option]),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        assert context.options == {}

    @pytest.mark.asyncio()
    async def test__auto_defer_property(self, mock_client: mock.Mock):
        defer = mock.AsyncMock()
        context = stub_class(tanjun.SlashContext, defer=defer)(
            mock_client,
            mock.AsyncMock(),
            mock.Mock(options=None),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._auto_defer(0.1)

            sleep.assert_awaited_once_with(0.1)
            defer.assert_awaited_once_with()

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

    @pytest.mark.asyncio()
    async def test_mark_not_found(self):
        on_not_found = mock.AsyncMock()
        context = tanjun.SlashContext(mock.Mock(), mock.Mock(), mock.Mock(options=None), on_not_found=on_not_found)

        await context.mark_not_found()

        on_not_found.assert_awaited_once_with(context)

    @pytest.mark.asyncio()
    async def test_mark_not_found_when_no_callback(self, context: tanjun.SlashContext):
        context = tanjun.SlashContext(mock.Mock(), mock.Mock(), mock.Mock(options=None), on_not_found=None)

        await context.mark_not_found()

    @pytest.mark.asyncio()
    async def test_mark_not_found_when_already_marked_as_not_found(self, context: tanjun.SlashContext):
        on_not_found = mock.AsyncMock()
        context = tanjun.SlashContext(mock.Mock(), mock.Mock(), mock.Mock(options=None), on_not_found=on_not_found)
        await context.mark_not_found()
        on_not_found.reset_mock()

        await context.mark_not_found()

        on_not_found.assert_not_called()

    def test_start_defer_timer(self, mock_client: mock.Mock):
        auto_defer = mock.Mock()
        context = stub_class(tanjun.SlashContext, _auto_defer=auto_defer)(
            mock_client,
            mock.AsyncMock(),
            mock.Mock(options=None),
            command=mock.Mock(),
            component=mock.Mock(),
        )

        with mock.patch.object(asyncio, "create_task") as create_task:
            context.start_defer_timer(534123)

            auto_defer.assert_called_once_with(534123)
            create_task.assert_called_once_with(auto_defer.return_value)
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
        assert context.get_type_special_case(tanjun.abc.ExecutableCommand) is mock_command
        assert context.get_type_special_case(tanjun.abc.BaseSlashCommand) is mock_command
        assert context.get_type_special_case(tanjun.abc.SlashCommand) is mock_command
        assert context.get_type_special_case(type(mock_command)) is mock_command

    def test_set_command_when_none(self, context: tanjun.MessageContext):
        context.set_command(None)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_special_case(tanjun.abc.ExecutableCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(tanjun.abc.BaseSlashCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(tanjun.abc.SlashCommand) is tanjun.injecting.UNDEFINED

    def test_set_command_when_none_and_previously_set(self, context: tanjun.MessageContext):
        mock_command = mock.Mock()
        context.set_command(mock_command)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_special_case(tanjun.abc.ExecutableCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(tanjun.abc.BaseSlashCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(tanjun.abc.SlashCommand) is tanjun.injecting.UNDEFINED
        assert context.get_type_special_case(type(mock_command)) is tanjun.injecting.UNDEFINED

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

        assert isinstance(context.interaction.delete_initial_response, mock.AsyncMock)
        context.interaction.delete_initial_response.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_edit_initial_response(self, context: tanjun.SlashContext):
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        await context.edit_initial_response(
            "bye",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
            embed=mock_embed,
            embeds=mock_embeds,
            replace_attachments=False,
            mentions_everyone=True,
            user_mentions=[123],
            role_mentions=[444],
        )

        assert isinstance(context.interaction.edit_initial_response, mock.AsyncMock)
        context.interaction.edit_initial_response.assert_awaited_once_with(
            content="bye",
            attachment=mock_attachment,
            attachments=mock_attachments,
            component=mock_component,
            components=mock_components,
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
        assert isinstance(context.interaction.fetch_initial_response, mock.AsyncMock)
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
