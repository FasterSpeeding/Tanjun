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
"""Standard command execution context implementations."""
from __future__ import annotations

__all__: list[str] = ["MessageContext", "ResponseTypeT", "SlashContext", "SlashOption"]

import asyncio
import typing

import hikari
from hikari import snowflakes

from . import abc as tanjun_abc
from . import injecting

if typing.TYPE_CHECKING:
    import datetime
    from collections import abc as collections

    from hikari import traits as hikari_traits

    _BaseContextT = typing.TypeVar("_BaseContextT", bound="BaseContext")
    _MessageContextT = typing.TypeVar("_MessageContextT", bound="MessageContext")
    _SlashContextT = typing.TypeVar("_SlashContextT", bound="SlashContext")
    _T = typing.TypeVar("_T")

ResponseTypeT = typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]


class BaseContext(injecting.BasicInjectionContext, tanjun_abc.Context):
    """Base class for all standard context implementations."""

    __slots__ = ("_client", "_component", "_final")

    def __init__(
        self,
        client: tanjun_abc.Client,
        injection_client: injecting.InjectorClient,
        *,
        component: typing.Optional[tanjun_abc.Component] = None,
    ) -> None:
        # injecting.BasicInjectionContext.__init__
        super().__init__(injection_client)
        self._client = client
        self._component = component
        self._final = False
        self._set_type_special_case(tanjun_abc.Context, self)
        self._set_type_special_case(BaseContext, self)
        self._set_type_special_case(type(self), self)

    @property
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        return self._client.cache

    @property
    def client(self) -> tanjun_abc.Client:
        return self._client

    @property
    def component(self) -> typing.Optional[tanjun_abc.Component]:
        return self._component

    @property
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        return self._client.events

    @property
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        return self._client.server

    @property
    def rest(self) -> hikari.api.RESTClient:
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

    def set_component(self: _BaseContextT, component: typing.Optional[tanjun_abc.Component], /) -> _BaseContextT:
        self._assert_not_final()
        if component:
            self._set_type_special_case(tanjun_abc.Component, component)
            self._set_type_special_case(type(component), component)

        elif (component_case := self.get_type_special_case(tanjun_abc.Component)) is not injecting.UNDEFINED:
            assert not isinstance(component_case, injecting.Undefined)
            self._remove_type_special_case(tanjun_abc.Component)
            self._remove_type_special_case(type(component_case))

        self._component = component
        return self

    def get_channel(self) -> typing.Optional[hikari.TextableGuildChannel]:
        if self._client.cache:
            channel = self._client.cache.get_guild_channel(self.channel_id)
            assert isinstance(channel, hikari.TextableGuildChannel)
            return channel

        return None

    def get_guild(self) -> typing.Optional[hikari.Guild]:
        if self.guild_id is not None and self._client.cache:
            return self._client.cache.get_guild(self.guild_id)

        return None

    async def fetch_channel(self) -> hikari.TextableChannel:
        channel = await self._client.rest.fetch_channel(self.channel_id)
        assert isinstance(channel, hikari.TextableChannel)
        return channel

    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:  # TODO: or raise?
        if self.guild_id is not None:
            return await self._client.rest.fetch_guild(self.guild_id)

        return None


class MessageContext(BaseContext, tanjun_abc.MessageContext):
    """Standard implementation of a command context as used within Tanjun."""

    __slots__ = (
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
        client: tanjun_abc.Client,
        injection_client: injecting.InjectorClient,
        content: str,
        message: hikari.Message,
        *,
        command: typing.Optional[tanjun_abc.MessageCommand] = None,
        component: typing.Optional[tanjun_abc.Component] = None,
        triggering_name: str = "",
        triggering_prefix: str = "",
    ) -> None:
        if message.content is None:
            raise ValueError("Cannot spawn context with a content-less message.")

        super().__init__(client, injection_client, component=component)
        self._command = command
        self._content = content
        self._initial_response_id: typing.Optional[hikari.Snowflake] = None
        self._last_response_id: typing.Optional[hikari.Snowflake] = None
        self._response_lock = asyncio.Lock()
        self._message = message
        self._triggering_name = triggering_name
        self._triggering_prefix = triggering_prefix
        self._set_type_special_case(tanjun_abc.MessageContext, self)
        self._set_type_special_case(MessageContext, self)
        self._set_type_special_case(type(self), self)

    def __repr__(self) -> str:
        return f"MessageContext <{self._message!r}, {self._command!r}>"

    @property
    def author(self) -> hikari.User:
        return self._message.author

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self._message.channel_id

    @property
    def command(self) -> typing.Optional[tanjun_abc.MessageCommand]:
        return self._command

    @property
    def content(self) -> str:
        return self._content

    @property
    def created_at(self) -> datetime.datetime:
        return self._message.created_at

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        return self._message.guild_id

    @property
    def has_responded(self) -> bool:
        return self._initial_response_id is not None

    @property
    def is_human(self) -> bool:
        return not self._message.author.is_bot and self._message.webhook_id is None

    @property
    def member(self) -> typing.Optional[hikari.Member]:
        return self._message.member

    @property
    def message(self) -> hikari.Message:
        return self._message

    @property
    def triggering_name(self) -> str:
        return self._triggering_name

    @property
    def triggering_prefix(self) -> str:
        return self._triggering_prefix

    @property
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        if not self._client.shards:
            return None

        if self._message.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._client.shards, self._message.guild_id)

        else:
            shard_id = 0

        return self._client.shards.shards[shard_id]

    def set_command(self: _MessageContextT, command: typing.Optional[tanjun_abc.MessageCommand], /) -> _MessageContextT:
        self._assert_not_final()
        self._command = command
        if command:
            self._set_type_special_case(tanjun_abc.ExecutableCommand, command)
            self._set_type_special_case(tanjun_abc.MessageCommand, command)
            self._set_type_special_case(type(command), command)

        elif (command_case := self.get_type_special_case(tanjun_abc.ExecutableCommand)) is not injecting.UNDEFINED:
            assert not isinstance(command_case, injecting.Undefined)
            self._remove_type_special_case(tanjun_abc.ExecutableCommand)
            self._remove_type_special_case(tanjun_abc.MessageCommand)  # TODO: command group?
            self._remove_type_special_case(type(command_case))

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
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        if self._initial_response_id is None:
            raise LookupError("Context has no initial response")

        return await self.rest.edit_message(
            self._message.channel_id,
            self._initial_response_id,
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        if self._last_response_id is None:
            raise LookupError("Context has no previous tracked response")

        return await self.rest.edit_message(
            self._message.channel_id,
            self._last_response_id,
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

    async def fetch_initial_response(self) -> hikari.Message:
        if self._initial_response_id is not None:
            return await self.client.rest.fetch_message(self._message.channel_id, self._initial_response_id)

        raise LookupError("No initial response found for this context")

    async def fetch_last_response(self) -> hikari.Message:
        if self._last_response_id is not None:
            return await self.client.rest.fetch_message(self._message.channel_id, self._last_response_id)

        raise LookupError("No responses found for this context")

    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = True,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        nonce: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        reply: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialMessage]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        async with self._response_lock:
            message = await self._message.respond(
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
            self._last_response_id = message.id
            if self._initial_response_id is None:
                self._initial_response_id = message.id

            return message


class SlashOption(tanjun_abc.SlashOption):
    __slots__ = ("_interaction", "_option")

    def __init__(self, interaction: hikari.CommandInteraction, option: hikari.CommandInteractionOption, /):
        if option.value is None:
            raise ValueError("Cannot build a slash option with a value-less API representation")

        self._interaction = interaction
        self._option = option

    @property
    def name(self) -> str:
        return self._option.name

    @property
    def type(self) -> typing.Union[hikari.OptionType, int]:
        return self._option.type

    @property
    def value(self) -> typing.Union[str, int, bool, float]:
        # This is asserted in __init__
        assert self._option.value is not None
        return self._option.value

    def resolve_value(
        self,
    ) -> typing.Union[hikari.InteractionChannel, hikari.InteractionMember, hikari.Role, hikari.User]:
        if self._option.type is hikari.OptionType.CHANNEL:
            return self.resolve_to_channel()

        if self._option.type is hikari.OptionType.ROLE:
            return self.resolve_to_role()

        if self._option.type is hikari.OptionType.USER:
            return self.resolve_to_user()

        if self._option.type is hikari.OptionType.MENTIONABLE:
            return self.resolve_to_mentionable()

        raise TypeError(f"Option type {self._option.type} isn't resolvable")

    def resolve_to_channel(self) -> hikari.InteractionChannel:
        # What does self.value being None mean?
        if self._option.type is hikari.OptionType.CHANNEL:
            assert self._interaction.resolved
            return self._interaction.resolved.channels[hikari.Snowflake(self.value)]

        raise TypeError(f"Cannot resolve non-channel option type {self._option.type} to a user")

    @typing.overload
    def resolve_to_member(self) -> hikari.InteractionMember:
        ...

    @typing.overload
    def resolve_to_member(self, *, default: _T) -> typing.Union[hikari.InteractionMember, _T]:
        ...

    def resolve_to_member(self, *, default: _T = ...) -> typing.Union[hikari.InteractionMember, _T]:
        # What does self.value being None mean?
        if self._option.type is hikari.OptionType.USER:
            assert self._interaction.resolved
            if member := self._interaction.resolved.members.get(hikari.Snowflake(self.value)):
                return member

            if default is not ...:
                return default

            raise LookupError("User isn't in the current guild") from None

        if self._option.type is hikari.OptionType.MENTIONABLE:
            target_id = hikari.Snowflake(self.value)
            assert self._interaction.resolved
            if member := self._interaction.resolved.members.get(target_id):
                return member

            if target_id in self._interaction.resolved.users:
                if default is not ...:
                    return default

                raise LookupError("User isn't in the current guild")

        raise TypeError(f"Cannot resolve non-user option type {self._option.type} to a member")

    def resolve_to_mentionable(self) -> typing.Union[hikari.Role, hikari.User, hikari.Member]:
        if self._option.type is hikari.OptionType.MENTIONABLE:
            target_id = hikari.Snowflake(self.value)
            assert self._interaction.resolved
            if role := self._interaction.resolved.roles.get(target_id):
                return role

            return self._interaction.resolved.members.get(target_id) or self._interaction.resolved.users[target_id]

        if self._option.type is hikari.OptionType.USER:
            return self.resolve_to_user()

        if self._option.type is hikari.OptionType.ROLE:
            return self.resolve_to_role()

        raise TypeError(f"Cannot resolve non-mentionable option type {self._option.type} to a mentionable entity.")

    def resolve_to_role(self) -> hikari.Role:
        if self._option.type is hikari.OptionType.ROLE:
            assert self._interaction.resolved
            return self._interaction.resolved.roles[hikari.Snowflake(self.value)]

        if self._option.type is hikari.OptionType.MENTIONABLE:
            assert self._interaction.resolved
            if role := self._interaction.resolved.roles.get(hikari.Snowflake(self.value)):
                return role

        raise TypeError(f"Cannot resolve non-role option type {self._option.type} to a role")

    def resolve_to_user(self) -> typing.Union[hikari.User, hikari.Member]:
        if self._option.type is hikari.OptionType.USER:
            assert self._interaction.resolved
            user_id = hikari.Snowflake(self.value)
            return self._interaction.resolved.members.get(user_id) or self._interaction.resolved.users[user_id]

        if self._option.type is hikari.OptionType.MENTIONABLE:
            assert self._interaction.resolved
            user_id = hikari.Snowflake(self.value)
            if result := self._interaction.resolved.members.get(user_id) or self._interaction.resolved.users.get(
                user_id
            ):
                return result

        raise TypeError(f"Cannot resolve non-user option type {self._option.type} to a user")


_COMMAND_OPTION_TYPES: typing.Final[frozenset[hikari.OptionType]] = frozenset(
    [hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP]
)


class SlashContext(BaseContext, tanjun_abc.SlashContext):
    __slots__ = (
        "_command",
        "_defaults_to_ephemeral",
        "_defer_task",
        "_has_been_deferred",
        "_has_responded",
        "_interaction",
        "_last_response_id",
        "_marked_not_found",
        "_on_not_found",
        "_options",
        "_response_future",
        "_response_lock",
    )

    def __init__(
        self,
        client: tanjun_abc.Client,
        injection_client: injecting.InjectorClient,
        interaction: hikari.CommandInteraction,
        *,
        command: typing.Optional[tanjun_abc.BaseSlashCommand] = None,
        component: typing.Optional[tanjun_abc.Component] = None,
        default_to_ephemeral: bool = False,
        on_not_found: typing.Optional[collections.Callable[[SlashContext], collections.Awaitable[None]]] = None,
    ) -> None:
        super().__init__(client, injection_client, component=component)
        self._command = command
        self._defaults_to_ephemeral = default_to_ephemeral
        self._defer_task: typing.Optional[asyncio.Task[None]] = None
        self._has_been_deferred = False
        self._has_responded = False
        self._interaction = interaction
        self._last_response_id: typing.Optional[hikari.Snowflake] = None
        self._marked_not_found = False
        self._on_not_found = on_not_found
        self._response_future: typing.Optional[asyncio.Future[ResponseTypeT]] = None
        self._response_lock = asyncio.Lock()
        self._set_type_special_case(tanjun_abc.SlashContext, self)
        self._set_type_special_case(SlashContext, self)
        self._set_type_special_case(type(self), self)

        options = interaction.options
        while options and (first_option := options[0]).type in _COMMAND_OPTION_TYPES:
            options = first_option.options

        if options:
            self._options = {option.name: SlashOption(interaction, option) for option in options}

        else:
            self._options = {}

    @property
    def author(self) -> hikari.User:
        return self._interaction.user

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self._interaction.channel_id

    @property
    def client(self) -> tanjun_abc.Client:
        return self._client

    @property
    def command(self) -> typing.Optional[tanjun_abc.BaseSlashCommand]:
        return self._command

    @property
    def created_at(self) -> datetime.datetime:
        return self._interaction.created_at

    @property
    def defaults_to_ephemeral(self) -> bool:
        return self._defaults_to_ephemeral

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        return self._interaction.guild_id

    @property
    def has_been_deferred(self) -> bool:
        return self._has_been_deferred

    @property
    def has_responded(self) -> bool:
        return self._has_responded

    @property
    def is_human(self) -> typing.Literal[True]:
        return True

    @property
    def member(self) -> typing.Optional[hikari.InteractionMember]:
        return self._interaction.member

    @property
    def triggering_name(self) -> str:
        # TODO: account for command groups
        return self._interaction.command_name

    @property
    def interaction(self) -> hikari.CommandInteraction:
        return self._interaction

    @property
    def options(self) -> collections.Mapping[str, tanjun_abc.SlashOption]:
        return self._options.copy()

    async def _auto_defer(self, countdown: typing.Union[int, float], /) -> None:
        await asyncio.sleep(countdown)
        await self.defer()

    def cancel_defer(self) -> None:
        if self._defer_task:
            self._defer_task.cancel()

    def _get_flags(
        self, flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED
    ) -> typing.Union[hikari.UndefinedType, int, hikari.MessageFlag]:
        if flags is hikari.UNDEFINED:
            return hikari.MessageFlag.EPHEMERAL if self._defaults_to_ephemeral else hikari.MessageFlag.NONE

        return flags

    def get_response_future(self) -> asyncio.Future[ResponseTypeT]:
        if not self._response_future:
            self._response_future = asyncio.get_running_loop().create_future()

        return self._response_future

    async def mark_not_found(self) -> None:
        if self._on_not_found and not self._marked_not_found:
            self._marked_not_found = True
            await self._on_not_found(self)

    def start_defer_timer(self: _SlashContextT, count_down: typing.Union[int, float], /) -> _SlashContextT:
        self._assert_not_final()
        if self._defer_task:
            raise RuntimeError("Defer timer already set")

        self._defer_task = asyncio.create_task(self._auto_defer(count_down))
        return self

    def set_command(self: _SlashContextT, command: typing.Optional[tanjun_abc.BaseSlashCommand], /) -> _SlashContextT:
        self._assert_not_final()
        self._command = command
        if command:
            self._set_type_special_case(tanjun_abc.ExecutableCommand, command)
            self._set_type_special_case(tanjun_abc.BaseSlashCommand, command)
            self._set_type_special_case(tanjun_abc.SlashCommand, command)
            self._set_type_special_case(type(command), command)

        elif (command_case := self.get_type_special_case(tanjun_abc.ExecutableCommand)) is not injecting.UNDEFINED:
            assert not isinstance(command_case, injecting.Undefined)
            self._remove_type_special_case(tanjun_abc.ExecutableCommand)
            self._remove_type_special_case(tanjun_abc.BaseSlashCommand)
            self._remove_type_special_case(tanjun_abc.SlashCommand)  # TODO: command group?
            self._remove_type_special_case(type(command_case))

        return self

    def set_ephemeral_default(self: _SlashContextT, state: bool, /) -> _SlashContextT:
        self._assert_not_final()
        self._defaults_to_ephemeral = state
        return self

    async def defer(
        self, flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED
    ) -> None:
        flags = self._get_flags(flags)
        in_defer_task = self._defer_task and self._defer_task is asyncio.current_task()
        if not in_defer_task:
            self.cancel_defer()

        async with self._response_lock:
            if self._has_been_deferred:
                if in_defer_task:
                    return

                raise RuntimeError("Context has already been responded to")

            self._has_been_deferred = True
            if self._response_future:
                self._response_future.set_result(self._interaction.build_deferred_response().set_flags(flags))

            else:
                await self._interaction.create_initial_response(
                    hikari.ResponseType.DEFERRED_MESSAGE_CREATE, flags=flags
                )

    async def create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED,
    ) -> hikari.Message:
        async with self._response_lock:
            message = await self._interaction.execute(
                content=content,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                flags=self._get_flags(flags),
                tts=tts,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )
            self._last_response_id = message.id
            return message

    async def _create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
        flags: typing.Union[int, hikari.MessageFlag, hikari.UndefinedType] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        flags = self._get_flags(flags)
        if self._has_responded:
            raise RuntimeError("Initial response has already been created")

        if self._has_been_deferred:
            raise RuntimeError(
                "edit_initial_response must be used to set the initial response after a context has been deferred"
            )

        self.cancel_defer()
        self._has_responded = True
        if not self._response_future:
            await self._interaction.create_initial_response(
                response_type=hikari.ResponseType.MESSAGE_CREATE,
                content=content,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                flags=flags,
                tts=tts,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        else:
            if component and components:
                raise ValueError("Only one of component or components may be passed")

            if embed and embeds:
                raise ValueError("Only one of embed or embeds may be passed")

            if component:
                assert not isinstance(component, hikari.UndefinedType)
                components = (component,)

            if embed:
                assert not isinstance(embed, hikari.UndefinedType)
                embeds = (embed,)

            content = str(content) if content is not hikari.UNDEFINED else hikari.UNDEFINED
            # Pyright doesn't properly support attrs and doesn't account for _ being removed from field
            # pre-fix in init.
            result = hikari.impl.InteractionMessageBuilder(
                type=hikari.ResponseType.MESSAGE_CREATE,  # type: ignore
                content=content,  # type: ignore
                components=components,  # type: ignore
                embeds=embeds,  # type: ignore
                flags=flags,  # type: ignore
                is_tts=tts,  # type: ignore
                mentions_everyone=mentions_everyone,  # type: ignore
                user_mentions=user_mentions,  # type: ignore
                role_mentions=role_mentions,  # type: ignore
            )  # type: ignore
            if embeds is not hikari.UNDEFINED:
                for embed in embeds:
                    result.add_embed(embed)

            self._response_future.set_result(result)

    async def create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
        flags: typing.Union[int, hikari.MessageFlag, hikari.UndefinedType] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        async with self._response_lock:
            await self._create_initial_response(
                content=content,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
                flags=flags,
                tts=tts,
            )

    async def delete_initial_response(self) -> None:
        await self._interaction.delete_initial_response()

    async def delete_last_response(self) -> None:
        if self._last_response_id is None:
            if self._has_responded:
                await self._interaction.delete_initial_response()
                return

            raise LookupError("Context has no last response")

        await self._interaction.delete_message(self._last_response_id)

    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        result = await self._interaction.edit_initial_response(
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )
        self._has_responded = True
        return result

    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        if self._last_response_id:
            return await self._interaction.edit_message(
                self._last_response_id,
                content=content,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                replace_attachments=replace_attachments,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        if self._has_responded or self._has_been_deferred:
            return await self.edit_initial_response(
                content=content,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                replace_attachments=replace_attachments,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        raise LookupError("Context has no previous responses")

    async def fetch_initial_response(self) -> hikari.Message:
        return await self._interaction.fetch_initial_response()

    async def fetch_last_response(self) -> hikari.Message:
        if self._last_response_id is not None:
            return await self._interaction.fetch_message(self._last_response_id)

        if self._has_responded:
            return await self.fetch_initial_response()

        raise LookupError("Context has no previous known responses")

    @typing.overload
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[False] = False,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> typing.Optional[hikari.Message]:
        ...

    @typing.overload
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        ...

    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> typing.Optional[hikari.Message]:
        async with self._response_lock:
            if self._has_responded:
                message = await self._interaction.execute(
                    content,
                    component=component,
                    components=components,
                    embed=embed,
                    embeds=embeds,
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )
                self._last_response_id = message.id
                return message

            if self._has_been_deferred:
                return await self.edit_initial_response(
                    content=content,
                    component=component,
                    components=components,
                    embed=embed,
                    embeds=embeds,
                    mentions_everyone=mentions_everyone,
                    user_mentions=user_mentions,
                    role_mentions=role_mentions,
                )

            await self._create_initial_response(
                content=content,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        if ensure_result:
            return await self._interaction.fetch_initial_response()
