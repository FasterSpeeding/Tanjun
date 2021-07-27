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
from __future__ import annotations

__all__: typing.Sequence[str] = ["InteractionContext", "MessageContext", "ResponseTypeT"]

import asyncio
import typing

from hikari import errors as hikari_errors
from hikari import messages
from hikari import snowflakes
from hikari import undefined
from hikari.api import special_endpoints as special_endpoints_api
from hikari.impl import special_endpoints as special_endpoints_impl
from hikari.interactions import bases as base_interactions

from . import traits

if typing.TYPE_CHECKING:
    from hikari import channels
    from hikari import embeds as embeds_
    from hikari import files
    from hikari import guilds
    from hikari import traits as hikari_traits
    from hikari import users

    # from hikari.api import entity_factory as entity_factory_api
    from hikari.api import cache as cache_api
    from hikari.api import event_manager as event_manager_api
    from hikari.api import interaction_server as interaction_server_api
    from hikari.api import rest as rest_api
    from hikari.api import shard as shard_api
    from hikari.interactions import commands as command_interactions

    _BaseContextT = typing.TypeVar("_BaseContextT", bound="BaseContext")
    _InteractionContextT = typing.TypeVar("_InteractionContextT", bound="InteractionContext")
    _MessageContextT = typing.TypeVar("_MessageContextT", bound="MessageContext")


ResponseTypeT = typing.Union[
    special_endpoints_api.InteractionMessageBuilder, special_endpoints_api.InteractionDeferredBuilder
]


class BaseContext(traits.Context):
    """Base class for all standard context implementations."""

    __slots__: typing.Sequence[str] = ("_client", "_component", "_final")

    def __init__(
        self,
        client: traits.Client,
        /,
        *,
        component: typing.Optional[traits.Component] = None,
    ) -> None:
        self._client = client
        self._component = component
        self._final = False

    @property
    def cache(self) -> typing.Optional[cache_api.Cache]:
        return self._client.cache

    @property
    def client(self) -> traits.Client:
        return self._client

    @property
    def component(self) -> typing.Optional[traits.Component]:
        return self._component

    @property
    def events(self) -> typing.Optional[event_manager_api.EventManager]:
        return self._client.events

    @property
    def server(self) -> typing.Optional[interaction_server_api.InteractionServer]:
        return self._client.server

    @property
    def rest(self) -> rest_api.RESTClient:
        return self._client.rest

    @property
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        return self._client.shards

    def _assert_not_final(self) -> None:
        if self._final:
            raise TypeError("Cannot modify a finalised context")

    def finalise(self: _BaseContextT) -> _BaseContextT:
        self._final = True
        return self

    def set_component(self: _BaseContextT, component: typing.Optional[traits.Component], /) -> _BaseContextT:
        self._assert_not_final()
        self._component = component
        return self

    def get_channel(self) -> typing.Optional[channels.PartialChannel]:
        if self._client.cache:
            return self._client.cache.get_guild_channel(self.channel_id)

        return None

    def get_guild(self) -> typing.Optional[guilds.Guild]:
        if self.guild_id is not None and self._client.cache:
            return self._client.cache.get_guild(self.guild_id)

        return None

    async def fetch_channel(self) -> channels.PartialChannel:
        return await self._client.rest.fetch_channel(self.channel_id)

    async def fetch_guild(self) -> typing.Optional[guilds.Guild]:  # TODO: or raise?
        if self.guild_id is not None:
            return await self._client.rest.fetch_guild(self.guild_id)

        return None


class MessageContext(BaseContext, traits.MessageContext):
    """Standard implementation of a command context as used within Tanjun."""

    __slots__: typing.Sequence[str] = (
        "_command",
        "_content",
        "_initial_response_id",
        "_last_response_id",
        "_response_lock",
        "_message",
        "_triggering_name",
        "_triggering_prefix",
    )

    def __init__(
        self,
        client: traits.Client,
        /,
        content: str,
        message: messages.Message,
        *,
        command: typing.Optional[traits.MessageCommand] = None,
        component: typing.Optional[traits.Component] = None,
        triggering_name: str = "",
        triggering_prefix: str = "",
    ) -> None:
        if message.content is None:
            raise ValueError("Cannot spawn context with a content-less message.")

        super().__init__(client, component=component)
        self._command = command
        self._content = content
        self._initial_response_id: typing.Optional[snowflakes.Snowflake] = None
        self._last_response_id: typing.Optional[snowflakes.Snowflake] = None
        self._response_lock = asyncio.Lock()
        self._message = message
        self._triggering_name = triggering_name
        self._triggering_prefix = triggering_prefix

    def __repr__(self) -> str:
        return f"Context <{self._message!r}, {self._command!r}>"

    @property
    def author(self) -> users.User:
        return self._message.author

    @property
    def channel_id(self) -> snowflakes.Snowflake:
        return self._message.channel_id

    @property
    def command(self) -> typing.Optional[traits.MessageCommand]:
        return self._command

    @property
    def content(self) -> str:
        return self._content

    @property
    def guild_id(self) -> typing.Optional[snowflakes.Snowflake]:
        return self._message.guild_id

    @property
    def has_responded(self) -> bool:
        return self._initial_response_id is not None

    @property
    def is_human(self) -> bool:
        return not self._message.author.is_bot and self._message.webhook_id is None

    @property
    def member(self) -> typing.Optional[guilds.Member]:
        return self._message.member

    @property
    def message(self) -> messages.Message:
        return self._message

    @property
    def triggering_name(self) -> str:
        return self._triggering_name

    @property
    def triggering_prefix(self) -> str:
        return self._triggering_prefix

    @property
    def shard(self) -> typing.Optional[shard_api.GatewayShard]:
        if not self._client.shards:
            return None

        if self._message.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._client.shards, self._message.guild_id)

        else:
            shard_id = 0

        return self._client.shards.shards[shard_id]

    def set_command(self: _MessageContextT, command: typing.Optional[traits.MessageCommand], /) -> _MessageContextT:
        self._assert_not_final()
        self._command = command
        return self

    def set_content(self: _MessageContextT, content: str, /) -> _MessageContextT:
        self._assert_not_final()
        self._content = content
        return self

    def set_triggering_name(self: _MessageContextT, name: str, /) -> _MessageContextT:
        self._assert_not_final()
        self._triggering_name = name
        return self

    def set_triggering_prefix(self: _MessageContextT, triggering_prefix: str, /) -> _MessageContextT:
        self._assert_not_final()
        self._triggering_prefix = triggering_prefix
        return self

    async def delete_initial_response(self) -> None:
        if self._initial_response_id is None:
            raise LookupError("Context has no initial response")

        await self._client.rest.delete_message(self._message.channel_id, self._initial_response_id)

    async def delete_last_response(self) -> None:
        if self._last_response_id is None:
            raise LookupError("Context has no previous responses")

        await self._client.rest.delete_message(self._message.channel_id, self._last_response_id)

    async def edit_initial_response(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        attachment: undefined.UndefinedOr[messages.Attachment] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        if self._initial_response_id is None:
            raise LookupError("Context has no initial response")

        return await self.rest.edit_message(
            self._message.channel_id,
            self._initial_response_id,
            content=content,
            attachment=attachment,
            attachments=attachments,
            # component=component,
            # components=components,
            embed=embed,
            embeds=embeds,
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

    async def edit_last_response(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        attachment: undefined.UndefinedOr[messages.Attachment] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        if self._last_response_id is None:
            raise LookupError("Context has no previous tracked response")

        return await self.rest.edit_message(
            self._message.channel_id,
            self._last_response_id,
            content=content,
            attachment=attachment,
            attachments=attachments,
            # component=component,
            # components=components,
            embed=embed,
            embeds=embeds,
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

    async def fetch_initial_response(self) -> typing.Optional[messages.Message]:
        if self._initial_response_id is not None:
            return await self.client.rest.fetch_message(self._message.channel_id, self._initial_response_id)

    async def fetch_last_response(self) -> typing.Optional[messages.Message]:
        if self._last_response_id is not None:
            return await self.client.rest.fetch_message(self._message.channel_id, self._last_response_id)

    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        ensure_result: bool = True,
        attachment: undefined.UndefinedOr[files.Resourceish] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        nonce: undefined.UndefinedOr[str] = undefined.UNDEFINED,
        reply: undefined.UndefinedOr[snowflakes.SnowflakeishOr[messages.PartialMessage]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        mentions_reply: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        async with self._response_lock:
            message = await self._message.respond(
                content=content,
                attachment=attachment,
                attachments=attachments,
                # component=component,
                # components=components,
                embed=embed,
                embeds=embeds,
                tts=tts,
                nonce=nonce,
                reply=reply,
                mentions_everyone=mentions_everyone,
                mentions_reply=mentions_reply,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )
            self._last_response_id = message.id
            if self._initial_response_id is None:
                self._initial_response_id = message.id

            return message


class InteractionContext(BaseContext, traits.InteractionContext):
    __slots__: typing.Sequence[str] = (
        "_defaults_to_ephemeral",
        "_defer_task",
        "_has_been_deferred",
        "_has_responded",
        "_interaction",
        "_last_response_id",
        "_response_future",
        "_response_lock",
    )

    def __init__(
        self,
        client: traits.Client,
        interaction: command_interactions.CommandInteraction,
        /,
        *,
        default_to_ephemeral: bool = False,
        component: typing.Optional[traits.Component] = None,
    ) -> None:
        super().__init__(client, component=component)
        self._defaults_to_ephemeral = default_to_ephemeral
        self._defer_task: typing.Optional[asyncio.Task[None]] = None
        self._has_been_deferred = False
        self._has_responded = False
        self._interaction = interaction
        self._last_response_id: typing.Optional[snowflakes.Snowflake] = None
        self._response_future: typing.Optional[asyncio.Future[ResponseTypeT]] = None
        self._response_lock = asyncio.Lock()

    @property
    def author(self) -> users.User:
        return self._interaction.user

    @property
    def channel_id(self) -> snowflakes.Snowflake:
        return self._interaction.channel_id

    @property
    def client(self) -> traits.Client:
        return self._client

    @property
    def guild_id(self) -> typing.Optional[snowflakes.Snowflake]:
        return self._interaction.guild_id

    @property
    def has_responded(self) -> bool:
        return self._has_responded

    @property
    def is_human(self) -> typing.Literal[True]:
        return True

    @property
    def member(self) -> typing.Optional[base_interactions.InteractionMember]:
        return self._interaction.member

    @property
    def triggering_name(self) -> str:
        return self._interaction.command_name

    @property
    def interaction(self) -> command_interactions.CommandInteraction:
        return self._interaction

    async def _auto_defer(self, countdown: typing.Union[int, float], /) -> None:
        await asyncio.sleep(countdown)
        try:
            await self.defer()
        except RuntimeError:
            pass

    def cancel_defer(self) -> None:
        if self._defer_task:
            self._defer_task.cancel()

    def get_response_future(self) -> asyncio.Future[ResponseTypeT]:
        self._assert_not_final()
        if not self._response_future:
            self._response_future = asyncio.get_running_loop().create_future()

        return self._response_future

    def start_defer_timer(self: _InteractionContextT, count_down: typing.Union[int, float], /) -> _InteractionContextT:
        self._assert_not_final()
        if self._defer_task:
            raise ValueError("Defer timer already set")

        self._defer_task = asyncio.get_running_loop().create_task(self._auto_defer(count_down))
        return self

    def set_ephemeral_default(self: _InteractionContextT, state: bool, /) -> _InteractionContextT:
        self._defaults_to_ephemeral = state
        return self

    async def defer(
        self, flags: typing.Union[undefined.UndefinedType, int, messages.MessageFlag] = undefined.UNDEFINED
    ) -> None:
        if flags is undefined.UNDEFINED:
            flags = messages.MessageFlag.EPHEMERAL if self._defaults_to_ephemeral else messages.MessageFlag.NONE

        async with self._response_lock:
            if self._has_been_deferred:
                raise RuntimeError("Context has already been responded to")

            self._has_been_deferred = True
            if self._response_future:
                self._response_future.set_result(self.interaction.build_deferred_response().set_flags(flags))

            else:
                await self.interaction.create_initial_response(
                    base_interactions.ResponseType.DEFERRED_MESSAGE_CREATE, flags=flags
                )

    async def create_followup(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        attachment: undefined.UndefinedOr[messages.Attachment] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        flags: typing.Union[undefined.UndefinedType, int, messages.MessageFlag] = undefined.UNDEFINED,
    ) -> messages.Message:
        if flags is undefined.UNDEFINED:
            flags = messages.MessageFlag.EPHEMERAL if self._defaults_to_ephemeral else messages.MessageFlag.NONE

        # TODO: remove once fixed in Hikari
        if embed is not undefined.UNDEFINED:
            if embeds is not undefined.UNDEFINED:
                raise ValueError("Only one of `embed` or `embeds` may be passed")

            embeds = (embed,)

        async with self._response_lock:
            message = await self._interaction.execute(
                content=content,
                attachment=attachment,
                attachments=attachments,
                # component=component,
                # components=components,
                # embed=embed,
                embeds=embeds,
                flags=flags,
                tts=tts,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )
            self._last_response_id = message.id
            return message

    async def create_initial_response(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
        flags: typing.Union[int, messages.MessageFlag, undefined.UndefinedType] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
    ) -> None:
        if flags is undefined.UNDEFINED:
            flags = messages.MessageFlag.EPHEMERAL if self._defaults_to_ephemeral else messages.MessageFlag.NONE

        async with self._response_lock:
            if self._has_responded:
                raise RuntimeError("Initial response has already been created")

            self._has_responded = True
            if not self._response_future:
                await self._interaction.create_initial_response(
                    response_type=base_interactions.ResponseType.MESSAGE_CREATE,
                    content=content,
                    # component=component,
                    # components=components,
                    embed=embed,
                    embeds=embeds,
                    flags=flags,
                    tts=tts,
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )

            else:
                # if component:
                #     assert not isinstance(component, undefined.UndefinedType)
                #     components = (component,)

                if embed:
                    assert not isinstance(embed, undefined.UndefinedType)
                    embeds = (embed,)

                result = special_endpoints_impl.InteractionMessageBuilder(
                    type=base_interactions.ResponseType.MESSAGE_CREATE,
                    content=content,
                    # components=components,
                    embeds=embeds,
                    flags=flags,
                    is_tts=tts,
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )
                if embeds is not undefined.UNDEFINED:
                    for embed in embeds:
                        result.add_embed(embed)

                self._response_future.set_result(result)

    async def delete_initial_response(self) -> None:
        return await self._interaction.delete_initial_response()

    async def delete_last_response(self) -> None:
        if self._last_response_id is None:
            raise LookupError("Context has no last response")

        await self._interaction.delete_message(self._last_response_id)

    async def edit_initial_response(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        attachment: undefined.UndefinedOr[messages.Attachment] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        return await self._interaction.edit_initial_response(
            content=content,
            attachment=attachment,
            attachments=attachments,
            # component=component,
            # components=components,
            embed=embed,
            embeds=embeds,
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

    async def edit_last_response(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        attachment: undefined.UndefinedOr[messages.Attachment] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        if self._last_response_id:
            return await self._interaction.edit_message(
                self._last_response_id,
                content=content,
                attachment=attachment,
                attachments=attachments,
                # component=component,
                # components=components,
                embed=embed,
                embeds=embeds,
                replace_attachments=replace_attachments,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        if self._has_responded:
            return await self._interaction.edit_initial_response(
                content=content,
                attachment=attachment,
                attachments=attachments,
                # component=component,
                # components=components,
                embed=embed,
                embeds=embeds,
                replace_attachments=replace_attachments,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        raise LookupError("Context has no previous responses")

    async def fetch_initial_response(self) -> typing.Optional[messages.Message]:
        try:
            return await self._interaction.fetch_initial_response()

        except hikari_errors.NotFoundError:
            return None

    async def fetch_last_response(self) -> typing.Optional[messages.Message]:
        if self._last_response_id is not None:
            return await self._interaction.fetch_message(self._last_response_id)

        elif self._has_responded:
            return await self.fetch_initial_response()

    @typing.overload
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        ensure_result: typing.Literal[False] = False,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> typing.Optional[messages.Message]:
        ...

    @typing.overload
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        ...

    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        ensure_result: bool = False,
        # component: undefined.UndefinedOr[special_endpoints_api.ComponentBuilder] = undefined.UNDEFINED,
        # components: undefined.UndefinedOr[
        #     typing.Sequence[special_endpoints_api.ComponentBuilder]
        # ] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> typing.Optional[messages.Message]:
        # if component and components:
        #     raise ValueError("Only one of component or components may be passed")

        if embed and embeds:
            raise ValueError("Only one of embed or embeds may be passed")

        await self._response_lock.acquire()
        self._response_lock.release()

        if self._has_responded:
            return await self.create_followup(
                content,
                # component=component,
                # components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        self.cancel_defer()
        if self._has_been_deferred:
            self._has_responded = True
            await self.edit_initial_response(
                content=content,
                # component=component,
                # components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        else:
            await self.create_initial_response(
                content=content,
                # component=component,
                # components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        if ensure_result:
            return await self._interaction.fetch_initial_response()
