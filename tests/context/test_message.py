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


class TestMessageContext:
    @pytest.fixture()
    def context(self, mock_client: mock.Mock) -> tanjun.context.MessageContext:
        return tanjun.context.MessageContext(
            mock_client,
            "hi there",
            mock.AsyncMock(),
            mock.Mock(),
            triggering_name="bonjour",
            triggering_prefix="bonhoven",
        )

    def test___repr__(self, context: tanjun.context.MessageContext):
        assert repr(context) == f"MessageContext <{context.message!r}, {context.command!r}>"

    def test_author_property(self, context: tanjun.context.MessageContext):
        assert context.author is context.message.author

    def test_channel_id_property(self, context: tanjun.context.MessageContext):
        assert context.channel_id is context.message.channel_id

    def test_created_at_property(self, context: tanjun.context.MessageContext):
        assert context.created_at is context.message.created_at

    def test_guild_id_property(self, context: tanjun.context.MessageContext):
        assert context.guild_id is context.message.guild_id

    def test_has_responded_property(self, context: tanjun.context.MessageContext):
        assert context.has_responded is False

    def test_has_responded_property_when_initial_repsonse_id_set(self, context: tanjun.context.MessageContext):
        context._initial_response_id = hikari.Snowflake(321123)

        assert context.has_responded is True

    def test_is_human_property(self, context: tanjun.context.MessageContext):
        context.message.author = mock.Mock(is_bot=False)
        context.message.webhook_id = None

        assert context.is_human is True

    def test_is_human_property_when_is_bot(self, context: tanjun.context.MessageContext):
        context.message.author = mock.Mock(is_bot=True)
        context.message.webhook_id = None

        assert context.is_human is False

    def test_is_human_property_when_is_webhook(self, context: tanjun.context.MessageContext):
        context.message.author = mock.Mock(is_bot=False)
        context.message.webhook_id = hikari.Snowflake(123321)

        assert context.is_human is False

    def test_member_property(self, context: tanjun.context.MessageContext):
        assert context.member is context.message.member

    def test_message_property(self, context: tanjun.context.MessageContext):
        assert context.message is context._message

    def test_set_command(self, context: tanjun.context.MessageContext):
        mock_command = mock.Mock()

        assert context.set_command(mock_command) is context

        assert context.command is mock_command
        assert context.get_type_dependency(tanjun.abc.ExecutableCommand) is mock_command
        assert context.get_type_dependency(tanjun.abc.MessageCommand) is mock_command

    def test_set_command_when_none(self, context: tanjun.context.MessageContext):
        assert isinstance(context.client.injector.get_type_dependency, mock.Mock)
        context.client.injector.get_type_dependency.return_value = alluka.abc.UNDEFINED
        context.set_command(None)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_dependency(tanjun.abc.ExecutableCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.MessageCommand) is alluka.abc.UNDEFINED

    def test_set_command_when_none_and_previously_set(self, context: tanjun.context.MessageContext):
        assert isinstance(context.client.injector.get_type_dependency, mock.Mock)
        context.client.injector.get_type_dependency.return_value = alluka.abc.UNDEFINED
        mock_command = mock.Mock()
        context.set_command(mock_command)
        context.set_command(None)

        assert context.command is None
        assert context.get_type_dependency(tanjun.abc.ExecutableCommand) is alluka.abc.UNDEFINED
        assert context.get_type_dependency(tanjun.abc.MessageCommand) is alluka.abc.UNDEFINED

    def test_set_command_when_finalised(self, context: tanjun.context.MessageContext):
        context.finalise()
        mock_command = mock.Mock()

        with pytest.raises(TypeError):
            context.set_command(mock_command)

        assert context.command is not mock_command

    def test_set_content(self, context: tanjun.context.MessageContext):
        assert context.set_content("hi") is context
        assert context.content == "hi"

    def test_set_content_when_finalised(self, context: tanjun.context.MessageContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.set_content("hi")

        assert context.content != "hi"

    def test_set_triggering_name(self, context: tanjun.context.MessageContext):
        assert context.set_triggering_name("bonjour") is context

        assert context.triggering_name == "bonjour"

    def test_set_triggering_name_when_finalised(self, context: tanjun.context.MessageContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.set_triggering_name("bonjour2")

        assert context.triggering_name != "bonjour2"

    def test_set_triggering_prefix(self, context: tanjun.context.MessageContext):
        assert context.set_triggering_prefix("bonhoven") is context

        assert context.triggering_prefix == "bonhoven"

    def test_set_triggering_prefix_when_finalised(self, context: tanjun.context.MessageContext):
        context.finalise()

        with pytest.raises(TypeError):
            context.set_triggering_prefix("bonhoven2")

        assert context.triggering_prefix != "bonhoven2"

    @pytest.mark.asyncio()
    async def test_delete_initial_response(self, context: tanjun.context.MessageContext, mock_client: mock.Mock):
        context._initial_response_id = hikari.Snowflake(32123)

        await context.delete_initial_response()

        mock_client.rest.delete_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_delete_initial_response_when_no_initial_response(
        self, context: tanjun.context.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.delete_initial_response()

        mock_client.rest.delete_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_delete_last_response(self, context: tanjun.context.MessageContext, mock_client: mock.Mock):
        context._last_response_id = hikari.Snowflake(32123)

        await context.delete_last_response()

        mock_client.rest.delete_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_delete_last_response_when_no_response(
        self, context: tanjun.context.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.delete_last_response()

        mock_client.rest.delete_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_initial_response(self, mock_client: mock.Mock):
        mock_register_task = mock.Mock()
        mock_delete_after = mock.Mock()
        context = stub_class(
            tanjun.context.MessageContext,
            _delete_after=mock_delete_after,
            args=(mock_client, "e", mock.AsyncMock(), mock_register_task),
        )
        context._initial_response_id = hikari.Snowflake(32123)
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.edit_initial_response(
                "hi",
                attachment=mock_attachment,
                attachments=mock_attachments,
                component=mock_component,
                components=mock_components,
                embed=mock_embed,
                embeds=mock_embeds,
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
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[321243],
        )
        create_task.assert_not_called()
        mock_delete_after.assert_not_called()
        mock_register_task.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_initial_response_when_no_initial_response(
        self, context: tanjun.context.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.edit_initial_response("hi")

        mock_client.rest.edit_message.assert_not_called()

    @pytest.mark.parametrize("delete_after", [datetime.timedelta(seconds=123), 123, 123.0])
    @pytest.mark.asyncio()
    async def test_edit_initial_response_when_delete_after(
        self, delete_after: typing.Union[datetime.timedelta, float, int], mock_client: mock.Mock
    ):
        mock_register_task = mock.Mock()
        mock_delete_after = mock.Mock()
        context = stub_class(
            tanjun.context.MessageContext,
            _delete_after=mock_delete_after,
            args=(mock_client, "e", mock.AsyncMock(), mock_register_task),
        )
        context._initial_response_id = hikari.Snowflake(32123)

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.edit_initial_response("hi", delete_after=delete_after)

        create_task.assert_called_once_with(mock_delete_after.return_value)
        mock_delete_after.assert_called_once_with(123.0, mock_client.rest.edit_message.return_value)
        mock_register_task.assert_called_once_with(create_task.return_value)

    @pytest.mark.asyncio()
    async def test_edit_last_response(self, mock_client: mock.Mock):
        mock_register_task = mock.Mock()
        mock_delete_after = mock.Mock()
        context = stub_class(
            tanjun.context.MessageContext,
            _delete_after=mock_delete_after,
            args=(mock_client, "e", mock.AsyncMock(), mock_register_task),
        )
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
            mentions_everyone=False,
            user_mentions=[123, 321],
            role_mentions=[321243],
        )
        mock_register_task.assert_not_called()
        mock_delete_after.assert_not_called()

    @pytest.mark.asyncio()
    async def test_edit_last_response_when_no_last_response(
        self, context: tanjun.context.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.edit_last_response("hi")

        mock_client.rest.edit_message.assert_not_called()

    @pytest.mark.parametrize("delete_after", [datetime.timedelta(seconds=654), 654, 654.0])
    @pytest.mark.asyncio()
    async def test_edit_last_response_when_delete_after(
        self, mock_client: mock.Mock, delete_after: typing.Union[datetime.timedelta, int, float]
    ):
        mock_register_task = mock.Mock()
        mock_delete_after = mock.Mock()
        context = stub_class(
            tanjun.context.MessageContext,
            _delete_after=mock_delete_after,
            args=(mock_client, "e", mock.AsyncMock(), mock_register_task),
        )
        context._last_response_id = hikari.Snowflake(32123)

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.edit_last_response("hi", delete_after=delete_after)

        create_task.assert_called_once_with(mock_delete_after.return_value)
        mock_delete_after.assert_called_once_with(654.0, mock_client.rest.edit_message.return_value)
        mock_register_task.assert_called_once_with(create_task.return_value)

    @pytest.mark.asyncio()
    async def test_fetch_initial_response(self, context: tanjun.context.MessageContext, mock_client: mock.Mock):
        context._initial_response_id = hikari.Snowflake(32123)

        message = await context.fetch_initial_response()

        assert message is mock_client.rest.fetch_message.return_value
        mock_client.rest.fetch_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_fetch_initial_response_when_no_initial_response(
        self, context: tanjun.context.MessageContext, mock_client: mock.Mock
    ):
        with pytest.raises(LookupError):
            await context.fetch_initial_response()

        mock_client.rest.fetch_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_last_response(self, context: tanjun.context.MessageContext, mock_client: mock.Mock):
        context._last_response_id = hikari.Snowflake(32123)

        message = await context.fetch_last_response()

        assert message is mock_client.rest.fetch_message.return_value
        mock_client.rest.fetch_message.assert_awaited_once_with(context.message.channel_id, 32123)

    @pytest.mark.asyncio()
    async def test_fetch_last_response_when_no_last_response(
        self, context: tanjun.context.MessageContext, mock_client: mock.Mock
    ):
        context._last_response_id = None
        with pytest.raises(LookupError):
            await context.fetch_last_response()

        mock_client.rest.fetch_message.assert_not_called()

    @pytest.mark.asyncio()
    async def test__delete_after(self, context: tanjun.context.MessageContext):
        mock_message = mock.AsyncMock()

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._delete_after(1545.4, mock_message)

            sleep.assert_awaited_once_with(1545.4)
            mock_message.delete.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test__delete_after_handles_not_found_error(self, context: tanjun.context.MessageContext):
        mock_message = mock.AsyncMock()
        mock_message.delete.side_effect = hikari.NotFoundError(url="", headers={}, raw_body=None)

        with mock.patch.object(asyncio, "sleep") as sleep:
            await context._delete_after(1545.4, mock_message)

            sleep.assert_awaited_once_with(1545.4)
            mock_message.delete.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_respond(self):
        mock_delete_after = mock.Mock()
        mock_register_task = mock.Mock()
        context = stub_class(
            tanjun.context.MessageContext,
            _delete_after=mock_delete_after,
            args=(mock.Mock(), "e", mock.AsyncMock(), mock_register_task),
        )
        mock_attachment = mock.Mock()
        mock_attachments = [mock.Mock()]
        mock_component = mock.Mock()
        mock_components = [mock.Mock()]
        mock_embed = mock.Mock()
        mock_embeds = [mock.Mock()]

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.respond(
                "hi",
                attachment=mock_attachment,
                attachments=mock_attachments,
                component=mock_component,
                components=mock_components,
                embed=mock_embed,
                embeds=mock_embeds,
                tts=True,
                reply=432123,
                mentions_everyone=False,
                mentions_reply=True,
                user_mentions=[123, 321],
                role_mentions=[555, 444],
            )

        create_task.assert_not_called()
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
            reply=432123,
            mentions_everyone=False,
            mentions_reply=True,
            user_mentions=[123, 321],
            role_mentions=[555, 444],
        )
        assert context._last_response_id == context.message.respond.return_value.id
        assert context._initial_response_id == context.message.respond.return_value.id
        mock_register_task.assert_not_called()
        mock_delete_after.assert_not_called()

    @pytest.mark.asyncio()
    async def test_respond_when_initial_response_id_already_set(self, context: tanjun.context.MessageContext):
        context._initial_response_id = hikari.Snowflake(32123)

        await context.respond("hi")

        assert context._initial_response_id == 32123

    @pytest.mark.parametrize("delete_after", [datetime.timedelta(seconds=123), 123, 123.0])
    @pytest.mark.asyncio()
    async def test_respond_when_delete_after(self, delete_after: typing.Union[int, float, datetime.timedelta]):
        mock_delete_after = mock.Mock()
        mock_register_task = mock.Mock()
        context = stub_class(
            tanjun.context.MessageContext,
            _delete_after=mock_delete_after,
            args=(mock.Mock(), "e", mock.AsyncMock(), mock_register_task),
        )

        with mock.patch.object(asyncio, "create_task") as create_task:
            await context.respond("hi", delete_after=delete_after)

        assert isinstance(context.message.respond, mock.Mock)
        mock_delete_after.assert_called_once_with(123.0, context.message.respond.return_value)
        create_task.assert_called_once_with(mock_delete_after.return_value)
        mock_register_task.assert_called_once_with(create_task.return_value)
