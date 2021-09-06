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
"""Interfaces of the objects used within Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "BaseSlashCommandT",
    "CheckSig",
    "CheckSigT",
    "Context",
    "Hooks",
    "MetaEventSig",
    "MetaEventSigT",
    "AnyHooks",
    "MessageHooks",
    "SlashHooks",
    "ExecutableCommand",
    "ListenerCallbackSig",
    "ListenerCallbackSigT",
    "MaybeAwaitableT",
    "MessageCommand",
    "MessageCommandT",
    "MessageCommandGroup",
    "MessageContext",
    "BaseSlashCommand",
    "SlashCommand",
    "SlashCommandGroup",
    "SlashContext",
    "Component",
    "Client",
]

import abc
import typing
from collections import abc as collections

import hikari

if typing.TYPE_CHECKING:
    import datetime

    from hikari import traits as hikari_traits


_T = typing.TypeVar("_T")


MaybeAwaitableT = typing.Union[_T, collections.Awaitable[_T]]
"""Type hint for a value which may need to be awaited to be resolved."""

ContextT = typing.TypeVar("ContextT", bound="Context")
ContextT_contra = typing.TypeVar("ContextT_contra", bound="Context", contravariant=True)
MetaEventSig = collections.Callable[..., MaybeAwaitableT[None]]
MetaEventSigT = typing.TypeVar("MetaEventSigT", bound="MetaEventSig")
BaseSlashCommandT = typing.TypeVar("BaseSlashCommandT", bound="BaseSlashCommand")
MessageCommandT = typing.TypeVar("MessageCommandT", bound="MessageCommand")


CommandCallbackSig = collections.Callable[..., collections.Awaitable[None]]
"""Type hint of the callback a `Command` instance will operate on.

This will be called when executing a command and will need to take at least one
positional argument of type `Context` where any other required or optional
keyword or positional arguments will be based on the parser instance for the
command if applicable.

.. note::
    This will have to be asynchronous.
"""


CheckSig = collections.Callable[..., MaybeAwaitableT[bool]]
"""Type hint of a general context check used with Tanjun `ExecutableCommand` classes.

This may be registered with a `ExecutableCommand` to add a rule which decides whether
it should execute for each context passed to it. This should take one positional
argument of type `Context` and may either be a synchronous or asynchronous
callback which returns `bool` where returning `False` or
raising `tanjun.errors.FailedCheck` will indicate that the current context
shouldn't lead to an execution.
"""

CheckSigT = typing.TypeVar("CheckSigT", bound=CheckSig)
"""Generic equivalent of `CheckSig`"""

ListenerCallbackSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]]
"""Type hint of a hikari event manager callback.

This is guaranteed one positional arg of type `hikari.events.Event` regardless
of implementation and must be a coruotine function which returns `None`.
"""

ListenerCallbackSigT = typing.TypeVar("ListenerCallbackSigT", bound=ListenerCallbackSig)
"""Generic equivalent of `ListenerCallbackSig`."""


class Context(abc.ABC):
    """Interface for the context of a command execution."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def author(self) -> hikari.User:
        """Object of the user who triggered this command.

        Returns
        -------
        hikari.users.User
            Object of the user who triggered this command.
        """

    @property
    @abc.abstractmethod
    def channel_id(self) -> hikari.Snowflake:
        """ID of the channel this command was triggered in.

        Returns
        -------
        hikari.snowflakes.Snowflake
            ID of the channel this command was triggered in.
        """

    @property
    @abc.abstractmethod
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        """Hikari cache instance this context's command client was initialised with.

        Returns
        -------
        typing.Optional[hikari.api.cache.Cache]
            Hikari cache instance this context's command client was initialised
            with if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def client(self) -> Client:
        """Tanjun `Client` implementation this context was spawned by.

        Returns
        -------
        Client
            The Tanjun `Client` implementation this context was spawned by.
        """

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        """Object of the `Component` this context is bound to.

        .. note::
            This will only be `None` before this has been bound to a
            specific command but never during command execution nor checks.

        Returns
        -------
        typing.Optional[Component[ContextT]]
            The component this context is bound to.
        """

    @property  # TODO: can we somehow have this always be present on the command execution facing interface
    @abc.abstractmethod
    def command(self: ContextT) -> typing.Optional[ExecutableCommand[ContextT]]:
        """Object of the command this context is bound to.

        .. note::
            This will only be `None` before this has been bound to a
            specific command but never during command execution.

        Returns
        -------
        typing.Optional[ExecutableCommand[ContextT]]
            The command this context is bound to.
        """

    @property
    @abc.abstractmethod
    def created_at(self) -> datetime.datetime:
        """When this context was created.

        Returns
        -------
        datetime.datetime
            When this context was created.
            This will either refer to a message or integration's creation date.
        """

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        """Object of the event manager this context's client was initialised with.

        Returns
        -------
        typing.Optional[hikari.event_manager.EventManager]
            The Hikari event manager this context's client was initialised with
            if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        """ID of the guild this command was executed in.

        Returns
        -------
        typing.Optional[hikari.snowflakes.Snowflake]
            ID of the guild this command was executed in.

            Will be `None` for all DM command executions.
        """

    @property
    @abc.abstractmethod
    def has_responded(self) -> bool:
        """Whether an initial response has been made for this context.

        Returns
        -------
        bool
            Whether an initial response has been made for this context.
        """

    @property
    @abc.abstractmethod
    def is_human(self) -> bool:
        """Whether this command execution was triggered by a human.

        Returns
        -------
        bool
            Whether this command execution was triggered by a human.

            Will be `False` for bot and webhook triggered commands.
        """

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[hikari.Member]:
        """Guild member object of this command's author.

        Returns
        -------
        typing.Optional[hikari.guilds.Member]
            Guild member object of this command's author.

            Will be `None` for DM command executions.
        """

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        """Object of the Hikari interaction server provided for this context's client.

        Returns
        -------
        typing.Optional[hikari.api.interaction_server.InteractionServer]
            The Hikari interaction server this context's client was initialised
            with if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this context's client was initialised with.

        Returns
        -------
        hikari.api.rest.RESTClient
            The Hikari REST client this context's client was initialised with.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        """Object of the Hikari shard manager this context's client was initialised with.

        Returns
        -------
        typing.Optional[hikari.traits.ShardAware]
            The Hikari shard manager this context's client was initialised with
            if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        """Command name this execution was triggered with.

        Returns
        -------
        str
            The command name this execution was triggered with.
        """

    @abc.abstractmethod
    def set_component(self: _T, _: typing.Optional[Component], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_channel(self) -> hikari.PartialChannel:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_channel(self) -> typing.Optional[hikari.PartialChannel]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_guild(self) -> typing.Optional[hikari.Guild]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_initial_response(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_last_response(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        raise NotImplementedError

    @abc.abstractmethod
    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool]
        ] = hikari.UNDEFINED,
        role_mentions: hikari.UndefinedOr[
            typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool]
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_initial_response(self) -> hikari.Message:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_last_response(self) -> hikari.Message:
        raise NotImplementedError

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[False] = False,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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

    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
        raise NotImplementedError


class MessageContext(Context, abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> typing.Optional[MessageCommand]:
        """Command that was invoked.

        Returns
        -------
        typing.Optional[MessageCommand]
            The command that was invoked.

            This is always set during command, command check and parser
            converter execution but isn't guaranteed during client callback
            nor client/component check execution.
        """

    @property
    @abc.abstractmethod
    def content(self) -> str:
        """Content of the context's message minus the triggering name and prefix.

        Returns
        -------
        str
            The content the of the context's message minus the triggering name
            and prefix.
        """

    @property
    @abc.abstractmethod
    def message(self) -> hikari.Message:
        """Message that triggered the context.

        Returns
        -------
        hikari.Message
            The message that triggered the context.
        """

    @property
    @abc.abstractmethod
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        """Shard that triggered the context.

        Returns
        -------
        typing.Optional[hikari.api.GatewayShard]
            The shard that triggered the context if `ctx.shards` is set.
            Otherwise, returns `None`.
        """

    @property
    @abc.abstractmethod
    def triggering_prefix(self) -> str:
        """Prefix that triggered the context.

        Returns
        -------
        str
            The prefix that triggered the context.
        """

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        """Command name that triggered the context.

        Returns
        -------
        str
            The command name that triggered the context.
        """

    @abc.abstractmethod
    def set_command(self: _T, _: typing.Optional[MessageCommand], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_content(self: _T, _: str, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_triggering_name(self: _T, _: str, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = True,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
        raise NotImplementedError


class SlashContext(Context, abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> typing.Optional[BaseSlashCommand]:
        """Command that was invoked.

        Returns
        -------
        typing.Optional[BaseSlashCommand]
            The command that was invoked.

            This should always be set during command, command check execution
            and command hook execution but isn't guaranteed for client callbacks
            nor component/client checks.
        """

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        """Whether the context is marked as defaulting to ephemeral response.

        This effects calls to `SlashContext.create_followup`,
        `SlashContext.create_initial_response`, `SlashContext.defer` and
        `SlashContext.respond` unless the `flags` field is provided for the
        methods which support it.

        Returns
        -------
        bool
            Whether the context is marked as defaulting to ephemeral responses.
        """

    @property
    @abc.abstractmethod
    def has_been_deferred(self) -> bool:
        """Whether the initial response for this context has been deferred.

        .. warning::
            If this is `True` when `SlashContext.has_responded` is `False`
            then `SlashContext.edit_initial_response` will need to be used
            to create the initial response rather than
            `SlashContext.create_initial_response`.

        Returns
        -------
        bool
            Whether the initial response for this context has been deferred.
        """

    @property
    @abc.abstractmethod
    def interaction(self) -> hikari.CommandInteraction:
        """Interaction this context is for.

        Returns
        -------
        hikari.CommandInteraction
            The interaction this context is for.
        """

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[hikari.InteractionMember]:
        """Object of the member that triggered this command if this is in a guild.

        Returns
        -------
        typing.Optional[hikari.InteractionMember]
            The member that triggered this command if this is in a guild.
        """

    @abc.abstractmethod
    def set_command(self: _T, _: typing.Optional[BaseSlashCommand], /) -> _T:
        """Set the command for this context.

        Parameters
        ----------
        command : typing.Optional[BaseSlashCommand]
            The command this context is for.
        """

    @abc.abstractmethod
    def set_ephemeral_default(self: _T, state: bool, /) -> _T:
        """Set the ephemeral default state for this context.

        Parameters
        ----------
        state : bool
            The new ephemeral default state.

            If this is `True` then all calls to the response creating methods
            on this context will default to being ephemeral.
        """

    @abc.abstractmethod
    async def defer(
        self, flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED
    ) -> None:
        """Defer the initial response for this context.

        Other Parameters
        ----------------
        flags : typing.Union[hikari.UndefinedType, int, hikari.MessageFlag]
            The flags to use for the initial response.
        """

    @abc.abstractmethod
    async def mark_not_found(self) -> None:
        """Mark this context as not found.

        Dependent on how the client is configured this may lead to a not found
        response message being sent.
        """

    @abc.abstractmethod
    async def create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
        raise NotImplementedError

    @abc.abstractmethod
    async def create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
        raise NotImplementedError

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[False] = False,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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

    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     collections.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
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
        raise NotImplementedError


class Hooks(abc.ABC, typing.Generic[ContextT_contra]):
    __slots__ = ()

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_error(
        self,
        ctx: ContextT_contra,
        /,
        exception: BaseException,
        *,
        hooks: typing.Optional[collections.Set[Hooks[ContextT_contra]]] = None,
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_post_execution(
        self,
        ctx: ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_pre_execution(
        self,
        ctx: ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_success(
        self,
        ctx: ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError


AnyHooks = Hooks[Context]
"""Execution hooks for any context."""

MessageHooks = Hooks[MessageContext]
"""Execution hooks for messages commands."""

SlashHooks = Hooks[SlashContext]
"""Execution hooks for slash commands."""


class ExecutableCommand(abc.ABC, typing.Generic[ContextT]):
    """Base class for all commands that can be executed."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def checks(self) -> collections.Collection[CheckSig]:
        """Get a collection of checks that must be met before the command can be executed.

        Returns
        -------
        collections.abc.Collection[CheckSig]
            The checks that must be met before the command can be executed.
        """

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        """Component that the command is registered with.

        Returns
        -------
        typing.Optional[Component]
            The component that the command is registered with.
        """

    @property
    @abc.abstractmethod
    def hooks(self) -> typing.Optional[Hooks[ContextT]]:
        """Hooks that are triggered when the command is executed.

        Returns
        -------
        typing.Optional[Hooks[ContextT]]
            The hooks that are triggered when the command is executed if set.
        """

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Get the mutable mapping of metadata set for this command.

        Returns
        -------
        collections.abc.MutableMapping[typing.Any, typing.Any]
            The metadata set for this component.

            Any modifications made to this mutable mapping will be preserved by
            the command.
        """

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        """Create a copy of this command.

        Returns
        -------
        Self
            A copy of this command.
        """

    @abc.abstractmethod
    def set_hooks(self: _T, _: typing.Optional[Hooks[ContextT]], /) -> _T:
        """Set the hooks that are triggered when the command is executed.

        Parameters
        ----------
        hooks : typing.Optional[Hooks[ContextT]]
            The hooks that are triggered when the command is executed.

        Returns
        -------
        Self
            This command to enable chained calls
        """

    @abc.abstractmethod
    def add_check(self: _T, check: CheckSig, /) -> _T:  # TODO: remove or add with_check?
        """Add a check to the command.

        Parameters
        ----------
        check : CheckSig
            The check to add.

        Returns
        -------
        Self
            This command to enable chained calls
        """

    @abc.abstractmethod
    def remove_check(self, check: CheckSig, /) -> None:
        """Remove a check from the command.

        Parameters
        ----------
        check : CheckSig
            The check to remove.
        """

    @abc.abstractmethod
    async def check_context(self, ctx: ContextT, /) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self, ctx: ContextT, /, *, hooks: typing.Optional[collections.MutableSet[Hooks[ContextT]]] = None
    ) -> None:
        raise NotImplementedError


class BaseSlashCommand(ExecutableCommand[SlashContext], abc.ABC):
    """Base class for all slash command classes."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        """Whether calls to this command should default to ephemeral mode.

        This indicates whether calls to `SlashContext.respond`,
        `SlashContext.create_initial_response` and `SlashContext.create_followup`
        on context objects which are linked to this command should default to
        ephemeral unless `flags` is explicitly passed.

        Returns
        -------
        bool
            Whether calls to this command should default to ephemeral mode.
        """

    @property
    @abc.abstractmethod
    def is_global(self) -> bool:
        """Whether the command should be declared globally or not.

        .. warning::
            For commands within command groups the state of this flag
            is inherited regardless of what it's set as on the child command.

        Returns
        -------
        bool
            Whether the command should be declared globally or not.
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the command.

        Returns
        -------
        str
            The name of the command.
        """

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Optional[SlashCommandGroup]:
        """Object of the group this command is in.

        Returns
        -------
        typing.Optional[SlashCommandGroup]
            The group this command is in, if relevant else `None`.
        """

    @property
    @abc.abstractmethod
    def tracked_command_id(self) -> typing.Optional[hikari.Snowflake]:
        """ID of the actual command this object tracks if set.

        This will be used when this command is used in bulk declarations.

        Returns
        -------
        typing.Optional[hikari.snowflakes.Snowflake]
            The ID of the actual command this object tracks.
        """

    @abc.abstractmethod
    def build(self) -> hikari.api.CommandBuilder:
        """Get a builder object for this command.

        Returns
        -------
        hikari.api.special_endpoints.CommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
        """

    @abc.abstractmethod
    async def execute(
        self,
        ctx: SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[SlashHooks]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[SlashCommandGroup], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_tracked_command(self: _T, command: hikari.SnowflakeishOr[hikari.Command], /) -> _T:
        """Set the global command this tracks.

        Parameters
        ----------
        command : hikari.snowflakes.SnowflakeishOr[hikari.interactions.commands.Command]
            Object or ID of the command this tracks.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """


class SlashCommand(BaseSlashCommand, abc.ABC):
    """A command that can be executed in a slash context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> CommandCallbackSig:
        """Get the callback which is called during execution..

        Returns
        -------
        CommandCallbackSig
            The command's callback.
        """


class SlashCommandGroup(BaseSlashCommand, abc.ABC):
    """Standard interface of a slash command group.

    .. note::
        Unlike `MessageCommandGroup`, slash command groups do not have
        their own callback.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def commands(self) -> collections.Collection[BaseSlashCommand]:
        """Get a collection of the commands in this group.

        Returns
        -------
        commands : collections.abc.Collection[BaseSlashCommand]
            The commands in this group.
        """

    @abc.abstractmethod
    def add_command(self: _T, command: BaseSlashCommand, /) -> _T:
        """Add a command to this group.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to add.

        Returns
        -------
        Self
            The command group instance to enable chained calls.
        """

    @abc.abstractmethod
    def remove_command(self, command: BaseSlashCommand, /) -> None:
        """Remove a command from this group.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to remove.
        """

    @abc.abstractmethod
    def with_command(self, command: BaseSlashCommandT, /) -> BaseSlashCommandT:
        """Add a command to this group through a decorator call.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to add.

        Returns
        -------
        BaseSlashCommand
            The added command.
        """


class MessageCommand(ExecutableCommand[MessageContext], abc.ABC):
    """Standard interface of a message command."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> CommandCallbackSig:
        """Get the callback which is called during execution.

        .. note::
            For command groups, this is called when none of the inner-commands
            matches the message.

        Returns
        -------
        CommandCallbackSig
            The callback to call when the command is executed.
        """

    @property
    @abc.abstractmethod
    def names(self) -> collections.Collection[str]:
        """Get a collection of this command's names.

        Returns
        -------
        collections.abc.Collection[str]
            The names of this command.
        """

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Optional[MessageCommandGroup]:
        """Parent group of this command.

        Returns
        -------
        typing.Optional[MessageCommandGroup]
            The parent group of this command if it's owned by a group.
        """

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[MessageCommandGroup], /) -> _T:
        """Set the parent of this command.

        Parameters
        ----------
        parent : typing.Optional[MessageCommandGroup]
            The parent of this command.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """

    @abc.abstractmethod
    def copy(self: _T, *, parent: typing.Optional[MessageCommandGroup] = None) -> _T:
        """Create a copy of this command.

        Other Parameters
        ----------------
        parent : typing.Optional[MessageCommandGroup]
            The parent of the copy.

        Returns
        -------
        Self
            The copy.
        """


class MessageCommandGroup(MessageCommand, abc.ABC):
    """Standard interface of a message command group."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def commands(self) -> collections.Collection[MessageCommand]:
        """Get a collection of the commands in this group.

        .. note::
            This may include command groups.

        Returns
        -------
        commands : collections.abc.Collection[MessageCommand]
            The commands in this group.
        """

    @abc.abstractmethod
    def add_command(self: _T, command: MessageCommand, /) -> _T:
        """Add a command to this group.

        Parameters
        ----------
        command : MessageCommand
            The command to add.

        Returns
        -------
        Self
            The group instance to enable chained calls.
        """

    @abc.abstractmethod
    def remove_command(self, command: MessageCommand, /) -> None:
        """Remove a command from this group.

        Parameters
        ----------
        command : MessageCommand
            The command to remove.
        """

    @abc.abstractmethod
    def with_command(self, command: MessageCommandT, /) -> MessageCommandT:
        """Add a command to this group through a decorator call.

        Parameters
        ----------
        command : MessageCommand
            The command to add.

        Returns
        -------
        MessageCommand
            The added command.
        """


class Component(abc.ABC):
    """Standard interface of a Tanjun component.

    This is a collection of message and slash commands, and listeners
    with logic for command search + execution and loading the listeners
    into a tanjun client.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def client(self) -> typing.Optional[Client]:
        """Tanjun client this component is bound to.

        Returns
        -------
        client : typing.Optional[Client]
            The client this component is bound to.
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Get the component's identifier.

        .. note::
            This will be preserved between copies of a component.

        Returns
        -------
        name : str
            The name of this component.
        """

    @property
    @abc.abstractmethod
    def slash_commands(self) -> collections.Collection[BaseSlashCommand]:
        """Get a collection of the slash commands in this component.

        Returns
        -------
        collections.abc.Collection[BaseSlashCommand]
            The slash commands in this component.
        """

    @property
    @abc.abstractmethod
    def message_commands(self) -> collections.Collection[MessageCommand]:
        """Get a cllection of the message commands in this component.

        Returns
        -------
        collections.abc.Collection[MessageCommand]
            The message commands in this component.
        """

    @property
    @abc.abstractmethod
    def listeners(self) -> collections.Mapping[type[hikari.Event], collections.Collection[ListenerCallbackSig]]:
        """Get a mapping of tuples of event types to the listeners registered for them in this component.

        Returns
        -------
        collections.abc.Mapping[type[hikari.Event], collections.abc.Collection[ListenerCallbackSig]]
            The listeners in this component.
        """

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Get the mutable mapping of the metadata set for this component.

        Returns
        -------
        collections.abc.MutableMapping[typing.Any, typing.Any]
            The metadata set for this component.

            Any modifications made to this mutable mapping will be preserved by
            the component.
        """

    @abc.abstractmethod
    def add_slash_command(self: _T, command: BaseSlashCommand, /) -> _T:
        """Add a slash command to this component.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_slash_command(self, command: BaseSlashCommand, /) -> None:
        """Remove a slash command from this component.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to remove.
        """

    @typing.overload
    @abc.abstractmethod
    def with_slash_command(self, command: BaseSlashCommandT, /) -> BaseSlashCommandT:
        ...

    @typing.overload
    @abc.abstractmethod
    def with_slash_command(self, *, copy: bool = False) -> collections.Callable[[BaseSlashCommandT], BaseSlashCommandT]:
        ...

    @abc.abstractmethod
    def with_slash_command(
        self, command: BaseSlashCommandT = ..., /, *, copy: bool = False
    ) -> typing.Union[BaseSlashCommandT, collections.Callable[[BaseSlashCommandT], BaseSlashCommandT]]:
        """Add a slash command to this component through a decorator call.

        Parameters
        ----------
        command : BaseSlashCommandT
            The command to add.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it.

        Returns
        -------
        BaseSlashCommandT
            The added command.
        """

    @abc.abstractmethod
    def add_message_command(self: _T, command: MessageCommand, /) -> _T:
        """Add a message command to this component.

        Parameters
        ----------
        command : MessageCommand
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_message_command(self, command: MessageCommand, /) -> None:
        """Remove a message command from this component.

        Parameters
        ----------
        command : MessageCommand
            The command to remove.
        """

    @typing.overload
    @abc.abstractmethod
    def with_message_command(self, command: MessageCommandT, /) -> MessageCommandT:
        ...

    @typing.overload
    @abc.abstractmethod
    def with_message_command(self, *, copy: bool = False) -> collections.Callable[[MessageCommandT], MessageCommandT]:
        ...

    @abc.abstractmethod
    def with_message_command(
        self, command: MessageCommandT = ..., /, *, copy: bool = False
    ) -> typing.Union[MessageCommandT, collections.Callable[[MessageCommandT], MessageCommandT]]:
        """Add a message command to this component through a decorator call.

        Parameters
        ----------
        command : MessageCommandT
            The command to add.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it.

        Returns
        -------
        MessageCommandT
            The added command.
        """

    @abc.abstractmethod
    def add_listener(self: _T, event: type[hikari.Event], listener: ListenerCallbackSig, /) -> _T:
        """Add a listener to this component.

        Parameters
        ----------
        event : type[hikari.events.Event]
            The event to listen for.
        listener : ListenerCallbackSig
            The listener to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_listener(self, event: type[hikari.Event], listener: ListenerCallbackSig, /) -> None:
        """Remove a listener from this component.

        Parameters
        ----------
        event : type[hikari.events.Event]
            The event to listen for.
        listener : ListenerCallbackSig
            The listener to remove.
        """

    # TODO: make event optional?
    @abc.abstractmethod
    def with_listener(
        self, event_type: type[hikari.Event]
    ) -> collections.Callable[[ListenerCallbackSigT], ListenerCallbackSigT,]:
        """Add a listener to this component through a decorator call.

        Parameters
        ----------
        event_type : type[hikari.Event]
            The event to listen for.

        Returns
        -------
        collections.Callable[[ListenerCallbackSigT], ListenerCallbackSigT]
            Decorator callback which takes listener to add.
        """

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def unbind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async callback typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    @abc.abstractmethod
    def check_message_context(self, ctx: MessageContext, /) -> collections.AsyncIterator[tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_slash_name(self, content: str, /) -> collections.Iterator[BaseSlashCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_interaction(
        self,
        ctx: SlashContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[SlashHooks]] = None,
    ) -> typing.Optional[collections.Awaitable[None]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_message(
        self, ctx: MessageContext, /, *, hooks: typing.Optional[collections.MutableSet[MessageHooks]] = None
    ) -> bool:
        raise NotImplementedError


class Client(abc.ABC):
    """Abstract interface of a Tanjun client.

    This should manage both message and slash command execution based on the
    provided hikari clients.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        """Hikari cache instance this command client was initialised with.

        Returns
        -------
        typing.Optional[hikari.api.cache.Cache]
            Hikari cache instance this command client was initialised
            with if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def components(self) -> collections.Collection[Component]:
        """Get a collection of the components this command client is using.

        Returns
        -------
        collections.api.Collection[tanjun.traits.Component]
            Collection of the components this command client is using.
        """

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        """Object of the event manager this client was initialised with.

        This is used for executing message commands if set.

        Returns
        -------
        typing.Optional[hikari.event_manager.EventManager]
            The Hikari event manager this client was initialised with
            if provided, else `None`.
        """

    @property  # TODO: switch over to a mapping of event to collection cause convenience
    @abc.abstractmethod
    def listeners(self) -> collections.Mapping[type[hikari.Event], collections.Collection[ListenerCallbackSig]]:
        """Get a mapping of event types to the listeners registered in this client.

        Returns
        -------
        collections.abc.Mapping[type[hikari.Event], collections.abc.Collection[ListenerCallbackSig]]
            The listeners in this component.
        """

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Get the mutable mapping of the metadata set for this client.

        Returns
        -------
        collections.abc.MutableMapping[typing.Any, typing.Any]
            The metadata set for this client.

            Any modifications made to this mutable mapping will be preserved by
            the client.
        """

    @property
    @abc.abstractmethod
    def prefixes(self) -> collections.Collection[str]:
        """Get a collection of the prefixes set for this client.

        These are only use during message command execution to match commands
        to this command client.

        Returns
        -------
        collcetions.abc.Collection[str]
            Collection of the prefixes set for this client.
        """

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this client was initialised with.

        Returns
        -------
        hikari.api.rest.RESTClient
            The Hikari REST client this client was initialised with.
        """

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        """Object of the Hikari interaction server provided for this client.

        This is used for executing slash commands if set.

        Returns
        -------
        typing.Optional[hikari.api.interaction_server.InteractionServer]
            The Hikari interaction server this client was initialised
            with if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        """Object of the Hikari shard manager this client was initialised with.

        Returns
        -------
        typing.Optional[hikari.traits.ShardAware]
            The Hikari shard manager this client was initialised with
            if provided, else `None`.
        """

    @abc.abstractmethod
    def add_component(self: _T, component: Component, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_client_callback(self: _T, event_name: str, callback: MetaEventSig, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def get_client_callbacks(self, event_name: str, /) -> collections.Collection[MetaEventSig]:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_client_callback(self, event_name: str, callback: MetaEventSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_client_callback(self, event_name: str, /) -> collections.Callable[[MetaEventSigT], MetaEventSigT]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_listener(self, event_type: type[hikari.Event], callback: ListenerCallbackSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_listener(self, event_type: type[hikari.Event], callback: ListenerCallbackSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_listener(
        self, event_type: type[hikari.Event], /
    ) -> collections.Callable[[ListenerCallbackSigT], ListenerCallbackSigT]:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async callback typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    @abc.abstractmethod
    def check_message_context(self, ctx: MessageContext, /) -> collections.AsyncIterator[tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_slash_name(self, name: str, /) -> collections.Iterator[BaseSlashCommand]:
        raise NotImplementedError
