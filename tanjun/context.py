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

__all__: typing.Sequence[str] = ["IntegrationContext", "MessageContext"]

import typing

from hikari import snowflakes
from hikari import undefined

from tanjun import traits

if typing.TYPE_CHECKING:
    from hikari import channels
    from hikari import embeds as embeds_
    from hikari import files
    from hikari import guilds
    from hikari import messages
    from hikari import traits as hikari_traits
    from hikari import users
    from hikari.api import shard as shard_
    from hikari.api import special_endpoints
    from hikari.interactions import commands as command_interactions

    _MessageContextT = typing.TypeVar("_MessageContextT", bound="MessageContext")


class MessageContext(traits.MessageContext):
    """Standard implementation of a command context as used within Tanjun."""

    __slots__: typing.Sequence[str] = (
        "_client",
        "_command",
        "_component",
        "_content",
        "_message",
        "_rest",
        "_triggering_name",
        "_triggering_prefix",
        "_shard",
    )

    def __init__(
        self,
        client: traits.Client,
        /,
        content: str,
        message: messages.Message,
        *,
        command: typing.Optional[traits.MessageCommand] = None,
        triggering_name: str = "",
        triggering_prefix: str = "",
    ) -> None:
        if message.content is None:
            raise ValueError("Cannot spawn context with a content-less message.")

        self._client = client
        self._command = command
        self._component: typing.Optional[traits.Component] = None
        self._content = content
        self._message = message
        self._triggering_name = triggering_name
        self._triggering_prefix = triggering_prefix

    def __repr__(self) -> str:
        return f"Context <{self._message!r}, {self._command!r}>"

    @property
    def author(self) -> users.User:
        return self._message.author

    @property
    def cache_service(self) -> typing.Optional[hikari_traits.CacheAware]:
        return self._client.cache_service

    @property
    def channel_id(self) -> snowflakes.Snowflake:
        return self._message.channel_id

    @property
    def client(self) -> traits.Client:
        return self._client

    @property
    def command(self) -> typing.Optional[traits.MessageCommand]:
        return self._command

    @property
    def component(self) -> typing.Optional[traits.Component]:
        return self._component

    @property
    def content(self) -> str:
        return self._content

    @property
    def event_service(self) -> typing.Optional[hikari_traits.EventManagerAware]:
        return self._client.event_service

    @property
    def guild_id(self) -> typing.Optional[snowflakes.Snowflake]:
        return self._message.guild_id

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
    def rest_service(self) -> hikari_traits.RESTAware:
        return self._client.rest_service

    @property
    def server_service(self) -> typing.Optional[hikari_traits.InteractionServerAware]:
        return self._client.server_service

    @property
    def shard_service(self) -> typing.Optional[hikari_traits.ShardAware]:
        return self._client.shard_service

    @property
    def shard(self) -> typing.Optional[shard_.GatewayShard]:
        if not self._client.shard_service:
            return None

        if self._message.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._client.shard_service, self._message.guild_id)

        else:
            shard_id = 0

        return self._client.shard_service.shards[shard_id]

    def set_command(self: _MessageContextT, command: traits.MessageCommand, /) -> _MessageContextT:
        self._command = command
        return self

    def set_component(self: _MessageContextT, component: typing.Optional[traits.Component], /) -> _MessageContextT:
        self._component = component
        return self

    def set_content(self: _MessageContextT, content: str, /) -> _MessageContextT:
        self._content = content
        return self

    def set_triggering_name(self: _MessageContextT, name: str, /) -> _MessageContextT:
        self._triggering_name = name
        return self

    def set_triggering_prefix(self: _MessageContextT, triggering_prefix: str, /) -> _MessageContextT:
        self._triggering_prefix = triggering_prefix
        return self

    async def fetch_channel(self) -> channels.PartialChannel:
        return await self._client.rest_service.rest.fetch_channel(self._message.channel_id)

    async def fetch_guild(self) -> typing.Optional[guilds.Guild]:  # TODO: or raise?
        if self._message.guild_id is not None:
            return await self._client.rest_service.rest.fetch_guild(self._message.guild_id)

        return None

    def get_channel(self) -> typing.Optional[channels.PartialChannel]:
        if self._client.cache_service:
            return self._client.cache_service.cache.get_guild_channel(self._message.channel_id)

        return None

    def get_guild(self) -> typing.Optional[guilds.Guild]:
        if self._message.guild_id is not None and self._client.cache_service:
            return self._client.cache_service.cache.get_guild(self._message.guild_id)

        return None

    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: bool = True,
        attachment: undefined.UndefinedOr[files.Resourceish] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        component: undefined.UndefinedOr[special_endpoints.ComponentBuilder] = undefined.UNDEFINED,
        components: undefined.UndefinedOr[typing.Sequence[special_endpoints.ComponentBuilder]] = undefined.UNDEFINED,
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
        return await self._message.respond(
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
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


class IntegrationContext(traits.InteractionContext):
    __slots__: typing.Sequence[str] = ("_client", "_interaction")

    def __init__(
        self,
        client: traits.Client,
        /,
        interaction: command_interactions.CommandInteraction,
    ) -> None:
        self._client = client
        self._interaction = interaction

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
    def is_human(self) -> typing.Literal[True]:
        return True

    @property
    def member(self) -> typing.Optional[guilds.Member]:
        return self._interaction.member

    @property
    def triggering_name(self) -> str:
        return self._interaction.command_name

    @property
    def interaction(self) -> command_interactions.CommandInteraction:
        return self._interaction

    async def fetch_channel(self) -> channels.PartialChannel:
        return await self._client.rest_service.rest.fetch_channel(self._interaction.channel_id)

    async def fetch_guild(self) -> typing.Optional[guilds.Guild]:  # TODO: or raise
        if self._interaction.guild_id is not None:
            return await self._client.rest_service.rest.fetch_guild(self._interaction.guild_id)

        return None

    def get_channel(self) -> typing.Optional[channels.PartialChannel]:
        if self._client.cache_service:
            return self._client.cache_service.cache.get_guild_channel(self._interaction.channel_id)

        return None

    def get_guild(self) -> typing.Optional[guilds.Guild]:
        if self._interaction.guild_id is not None and self._client.cache_service:
            return self._client.cache_service.cache.get_guild(self._interaction.guild_id)

        return None

    @typing.overload
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: typing.Literal[False] = False,
        component: undefined.UndefinedOr[special_endpoints.ComponentBuilder] = undefined.UNDEFINED,
        components: undefined.UndefinedOr[typing.Sequence[special_endpoints.ComponentBuilder]] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        flags: typing.Union[int, messages.MessageFlag, undefined.UndefinedType] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
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
        wait_for_result: typing.Literal[True],
        component: undefined.UndefinedOr[special_endpoints.ComponentBuilder] = undefined.UNDEFINED,
        components: undefined.UndefinedOr[typing.Sequence[special_endpoints.ComponentBuilder]] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        flags: typing.Union[int, messages.MessageFlag, undefined.UndefinedType] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
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
        wait_for_result: bool = False,
        component: undefined.UndefinedOr[special_endpoints.ComponentBuilder] = undefined.UNDEFINED,
        components: undefined.UndefinedOr[typing.Sequence[special_endpoints.ComponentBuilder]] = undefined.UNDEFINED,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        flags: typing.Union[int, messages.MessageFlag, undefined.UndefinedType] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> typing.Optional[messages.Message]:
        raise NotImplementedError
