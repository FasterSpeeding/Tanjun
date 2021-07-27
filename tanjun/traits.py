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

__all__: typing.Sequence[str] = [
    "CheckSig",
    "CheckSigT",
    "ClientCallbackNames",
    "Context",
    "Hooks",
    "MetaEventSig",
    "MetaEventSigT",
    "AnyHooks",
    "MessageHooks",
    "InteractionHooks",
    "ExecutableCommand",
    "InteractionCommand",
    "InteractionCommandT",
    "InteractionCommandGroup",
    "InteractionContext",
    "MessageCommand",
    "MessageCommandT",
    "MessageCommandGroup",
    "MessageContext",
    "Component",
    "Client",
]

import abc
import enum
import typing

import hikari

if typing.TYPE_CHECKING:
    from hikari import traits as hikari_traits
    from hikari.api import event_manager as event_manager_api


_T = typing.TypeVar("_T")


ContextT = typing.TypeVar("ContextT", bound="Context")
ContextT_contra = typing.TypeVar("ContextT_contra", bound="Context", contravariant=True)
MetaEventSig = typing.Callable[..., typing.Union[None, typing.Awaitable[None]]]
MetaEventSigT = typing.TypeVar("MetaEventSigT", bound="MetaEventSig")
InteractionCommandT = typing.TypeVar("InteractionCommandT", bound="InteractionCommand")
MessageCommandT = typing.TypeVar("MessageCommandT", bound="MessageCommand")


CommandCallbackSig = typing.Callable[..., typing.Awaitable[None]]
"""Type hint of the callback a `Command` instance will operate on.

This will be called when executing a command and will need to take at least one
positional argument of type `Context` where any other required or optional
keyword or positional arguments will be based on the parser instance for the
command if applicable.

!!! note
    This will have to be asynchronous.
"""


CheckSig = typing.Callable[..., typing.Union[bool, typing.Awaitable[bool]]]
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


class Context(abc.ABC):
    """Interface for the context of a command execution."""

    __slots__: typing.Sequence[str] = ()

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
        """The Tanjun `Client` implementation this context was spawned by.

        Returns
        -------
        Client
            The Tanjun `Client` implementation this context was spawned by.
        """

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        """Object of the `Component` this context is bound to.

        Returns
        -------
        typing.Optional[Component[ContextT]]
            The component this context is bound to.

            !!! note
                This will only be `None` before this has been bound to a
                specific command but never during command execution nor checks.
        """

    @property  # TODO: can we somehow have this always be present on the command execution facing interface
    @abc.abstractmethod
    def command(self: ContextT) -> typing.Optional[ExecutableCommand[ContextT]]:
        """Object of the command this context is bound to.

        Returns
        -------
        typing.Optional[ExecutableCommand[ContextT]]
            The command this context is bound to.

            !!! note
                This will only be `None` before this has been bound to a
                specific command but never during command execution.
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
        raise NotImplementedError

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
        """The command name this execution was triggered with.

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
    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:  # TODO: or raise?
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
        attachments: hikari.UndefinedOr[typing.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        attachments: hikari.UndefinedOr[typing.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
    async def fetch_initial_response(self) -> typing.Optional[hikari.Message]:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_last_response(self) -> typing.Optional[hikari.Message]:
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def command(self) -> typing.Optional[MessageCommand]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def content(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def message(self) -> hikari.Message:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def triggering_prefix(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        raise NotImplementedError

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
        attachments: hikari.UndefinedOr[typing.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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


class InteractionContext(Context, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def command(self) -> typing.Optional[InteractionCommand]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def interaction(self) -> hikari.CommandInteraction:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[hikari.InteractionMember]:
        raise NotImplementedError

    @abc.abstractmethod
    def set_ephemeral_default(self: _T, state: bool, /) -> _T:
        raise NotImplementedError

    async def defer(
        self, flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[typing.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        # component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        # components: hikari.UndefinedOr[
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
        #     typing.Sequence[hikari.api.ComponentBuilder]
        # ] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[typing.Sequence[hikari.Embed]] = hikari.UNDEFINED,
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
    __slots__: typing.Sequence[str] = ()

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
        hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_post_execution(
        self,
        ctx: ContextT_contra,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_pre_execution(
        self,
        ctx: ContextT_contra,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_success(
        self,
        ctx: ContextT_contra,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError


AnyHooks = Hooks[Context]
MessageHooks = Hooks[MessageContext]
InteractionHooks = Hooks[InteractionContext]


class ExecutableCommand(abc.ABC, typing.Generic[ContextT]):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def callback(self) -> CommandCallbackSig:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def checks(self) -> typing.Collection[CheckSig]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def hooks(self) -> typing.Optional[Hooks[ContextT]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_hooks(self: _T, _: typing.Optional[Hooks[ContextT]], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def add_check(self: _T, check: CheckSig, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_check(self, check: CheckSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self, ctx: ContextT, /, *, hooks: typing.Optional[typing.MutableSet[Hooks[ContextT]]] = None
    ) -> None:
        raise NotImplementedError


class InteractionCommand(ExecutableCommand[InteractionContext], abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        raise NotImplementedError

    @property
    def is_global(self) -> bool:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Optional[InteractionCommandGroup]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def tracked_command(self) -> typing.Optional[hikari.Command]:
        raise NotImplementedError

    @abc.abstractmethod
    def build(self) -> hikari.api.CommandBuilder:
        raise NotImplementedError

    @abc.abstractmethod
    async def check_context(self, ctx: InteractionContext, /) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self,
        ctx: InteractionContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[typing.MutableSet[Hooks[InteractionContext]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set_tracked_command(self: _T, _: typing.Optional[hikari.Command], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[InteractionCommandGroup], /) -> _T:
        raise NotImplementedError


class InteractionCommandGroup(InteractionCommand, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def commands(self) -> typing.Collection[InteractionCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_command(self, command: InteractionCommand, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_command(self, command: InteractionCommand, /) -> None:
        raise NotImplementedError


class MessageCommand(ExecutableCommand[MessageContext], abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def names(self) -> typing.Collection[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Optional[MessageCommandGroup]:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[MessageCommandGroup], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def add_name(self: _T, name: str, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_name(self, name: str, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T, *, parent: typing.Optional[MessageCommandGroup] = None) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    async def check_context(self, ctx: MessageContext, /, *, name_prefix: str = "") -> typing.Optional[str]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_name(self, name: str, /) -> typing.Optional[str]:
        raise NotImplementedError


class MessageCommandGroup(MessageCommand, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def commands(self) -> typing.Collection[MessageCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_command(self: _T, command: MessageCommand, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_command(self, command: MessageCommand, /) -> None:
        raise NotImplementedError


class Component(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def client(self) -> typing.Optional[Client]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def interaction_commands(self) -> typing.Collection[InteractionCommand]:
        raise NotImplementedError

    @property
    def message_commands(self) -> typing.Collection[MessageCommand]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def listeners(
        self,
    ) -> typing.Collection[typing.Tuple[typing.Type[hikari.Event], event_manager_api.CallbackT[typing.Any]]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    def add_interaction_command(self: _T, command: InteractionCommand, /) -> _T:
        raise NotImplementedError

    def remove_interaction_command(self, command: InteractionCommand, /) -> None:
        raise NotImplementedError

    @typing.overload
    def with_interaction_command(self, command: InteractionCommandT, /) -> InteractionCommandT:
        ...

    @typing.overload
    def with_interaction_command(
        self, *, copy: bool = False
    ) -> typing.Callable[[InteractionCommandT], InteractionCommandT]:
        ...

    def with_interaction_command(
        self, command: InteractionCommandT = ..., /, *, copy: bool = False
    ) -> typing.Union[InteractionCommandT, typing.Callable[[InteractionCommandT], InteractionCommandT]]:
        raise NotImplementedError

    def add_message_command(self: _T, command: MessageCommand, /) -> _T:
        raise NotImplementedError

    def remove_message_command(self, command: MessageCommand, /) -> None:
        raise NotImplementedError

    @typing.overload
    def with_message_command(self, command: MessageCommandT, /) -> MessageCommandT:
        ...

    @typing.overload
    def with_message_command(self, *, copy: bool = False) -> typing.Callable[[MessageCommandT], MessageCommandT]:
        ...

    def with_message_command(
        self, command: MessageCommandT = ..., /, *, copy: bool = False
    ) -> typing.Union[MessageCommandT, typing.Callable[[MessageCommandT], MessageCommandT]]:
        raise NotImplementedError

    def add_listener(
        self: _T,
        event: typing.Type[event_manager_api.EventT_inv],
        listener: event_manager_api.CallbackT[event_manager_api.EventT_inv],
        /,
    ) -> _T:
        raise NotImplementedError

    def remove_listener(
        self,
        event: typing.Type[event_manager_api.EventT_inv],
        listener: event_manager_api.CallbackT[event_manager_api.EventT_inv],
        /,
    ) -> None:
        raise NotImplementedError

    # TODO: make event optional?
    def with_listener(
        self, event_type: typing.Type[event_manager_api.EventT_inv]
    ) -> typing.Callable[
        [event_manager_api.CallbackT[event_manager_api.EventT_inv]],
        event_manager_api.CallbackT[event_manager_api.EventT_inv],
    ]:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def unbind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async callback typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    @abc.abstractmethod
    def check_message_context(
        self, ctx: MessageContext, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[typing.Tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> typing.Iterator[typing.Tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_interaction(
        self,
        ctx: InteractionContext,
        /,
        *,
        hooks: typing.Optional[typing.MutableSet[InteractionHooks]] = None,
    ) -> typing.Optional[typing.Awaitable[None]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_message(
        self, ctx: MessageContext, /, *, hooks: typing.Optional[typing.MutableSet[MessageHooks]] = None
    ) -> bool:
        raise NotImplementedError


class ClientCallbackNames(str, enum.Enum):
    CLOSED = "closed"
    CLOSING = "closing"
    INTERACTION_COMMAND_NOT_FOUND = "interaction_command_not_found"
    MESSAGE_COMMAND_NOT_FOUND = "message_command_not_found"
    STARTED = "started"
    STARTING = "startup"


class Client(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def components(self) -> typing.Collection[Component]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def prefixes(self) -> typing.Collection[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        raise NotImplementedError

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
    def get_client_callbacks(self, event_name: str, /) -> typing.Collection[MetaEventSig]:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_client_callback(self, event_name: str, callback: MetaEventSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_client_callback(self, event_name: str, /) -> typing.Callable[[MetaEventSigT], MetaEventSigT]:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async callback typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    @abc.abstractmethod
    def check_message_context(self, ctx: MessageContext, /) -> typing.AsyncIterator[typing.Tuple[str, MessageCommand]]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> typing.Iterator[typing.Tuple[str, MessageCommand]]:
        raise NotImplementedError
