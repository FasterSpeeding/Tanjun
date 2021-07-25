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
    "ConverterSig",
    "CheckSig",
    "CheckSigT",
    "Context",
    "Hooks",
    "MetaEventSig",
    "MetaEventSigT",
    "AnyHooks",
    "MessageHooks",
    "InteractionHooks",
    "ExecutableCommand",
    "InteractionCommand",
    "InteractionCommandGroup",
    "InteractionContext",
    "MessageCommand",
    "MessageCommandGroup",
    "MessageContext",
    "Component",
    "Client",
    "UndefinedDefaultT",
    "UNDEFINED_DEFAULT",
    "Parameter",
    "Argument",
    "Option",
    "Parser",
]

import abc
import typing

from hikari import undefined

if typing.TYPE_CHECKING:
    from hikari import channels
    from hikari import embeds as embeds_
    from hikari import files
    from hikari import guilds
    from hikari import messages
    from hikari import snowflakes
    from hikari import traits
    from hikari import users
    from hikari.api import cache as cache_api
    from hikari.api import event_manager as event_manager_api
    from hikari.api import interaction_server as interaction_server_api
    from hikari.api import rest as rest_api
    from hikari.api import shard as shard_api

    # from hikari.api import special_endpoints as special_endpoints_api
    from hikari.events import base_events
    from hikari.interactions import bases as base_interactions
    from hikari.interactions import commands as command_interactions

    from . import errors

_T = typing.TypeVar("_T")


ContextT = typing.TypeVar("ContextT", bound="Context")
ContextT_contra = typing.TypeVar("ContextT_contra", bound="Context", contravariant=True)
MetaEventSig = typing.Callable[..., typing.Union[None, typing.Awaitable[None]]]
MetaEventSigT = typing.TypeVar("MetaEventSigT", bound="MetaEventSig")

# To allow for stateless converters we accept both "Converter[...]" and "Type[StatelessConverter[...]]" where all the
# methods on "Type[StatelessConverter[...]]" need to be classmethods as it will not be initialised before calls are made
# to it.
ConverterSig = typing.Callable[..., typing.Union[typing.Awaitable[typing.Any], typing.Any]]
"""Type hint of a converter used within a parser instance.

This must be a callable or asynchronous callable which takes one position
`str` argument and returns the resultant value.
"""

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
    def author(self) -> users.User:
        """Object of the user who triggered this command.

        Returns
        -------
        hikari.users.User
            Object of the user who triggered this command.
        """

    @property
    @abc.abstractmethod
    def channel_id(self) -> snowflakes.Snowflake:
        """ID of the channel this command was triggered in.

        Returns
        -------
        hikari.snowflakes.Snowflake
            ID of the channel this command was triggered in.
        """

    @property
    @abc.abstractmethod
    def cache(self) -> typing.Optional[cache_api.Cache]:
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
    def events(self) -> typing.Optional[event_manager_api.EventManager]:
        """Object of the event manager this context's client was initialised with.

        Returns
        -------
        typing.Optional[hikari.event_manager.EventManager]
            The Hikari event manager this context's client was initialised with
            if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def guild_id(self) -> typing.Optional[snowflakes.Snowflake]:
        """ID of the guild this command was executed in.

        Returns
        -------
        typing.Optional[hikari.snowflakes.Snowflake]
            ID of the guild this command was executed in.

            Will be `None` for all DM command executions.
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
    def member(self) -> typing.Optional[guilds.Member]:
        """Guild member object of this command's author.

        Returns
        -------
        typing.Optional[hikari.guilds.Member]
            Guild member object of this command's author.

            Will be `None` for DM command executions.
        """

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[interaction_server_api.InteractionServer]:
        """Object of the Hikari interaction server provided for this context's client.

        Returns
        -------
        typing.Optional[hikari.api.interaction_server.InteractionServer]
            The Hikari interaction server this context's client was initialised
            with if provided, else `None`.
        """

    @property
    @abc.abstractmethod
    def rest(self) -> rest_api.RESTClient:
        """Object of the Hikari REST client this context's client was initialised with.

        Returns
        -------
        hikari.api.rest.RESTClient
            The Hikari REST client this context's client was initialised with.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[traits.ShardAware]:
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
    async def fetch_channel(self) -> channels.PartialChannel:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_guild(self) -> typing.Optional[guilds.Guild]:  # TODO: or raise?
        raise NotImplementedError

    @abc.abstractmethod
    def get_channel(self) -> typing.Optional[channels.PartialChannel]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_guild(self) -> typing.Optional[guilds.Guild]:
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
        raise NotImplementedError

    @abc.abstractmethod
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
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_initial_response(self) -> typing.Optional[messages.Message]:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_last_response(self) -> typing.Optional[messages.Message]:
        raise NotImplementedError

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: typing.Literal[False] = False,
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
    @abc.abstractmethod
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: typing.Literal[True],
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

    @abc.abstractmethod
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: bool = False,
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
    def message(self) -> messages.Message:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard(self) -> typing.Optional[shard_api.GatewayShard]:
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
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: bool = True,
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
        raise NotImplementedError


class InteractionContext(Context, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def command(self) -> typing.Optional[InteractionCommand]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def interaction(self) -> command_interactions.CommandInteraction:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[base_interactions.InteractionMember]:
        raise NotImplementedError

    @abc.abstractmethod
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
        raise NotImplementedError

    @abc.abstractmethod
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
        raise NotImplementedError

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: typing.Literal[False] = False,
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
    @abc.abstractmethod
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: typing.Literal[True],
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

    @abc.abstractmethod
    async def respond(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        wait_for_result: bool = False,
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
    async def trigger_parser_error(
        self,
        ctx: ContextT_contra,
        /,
        exception: errors.ParserError,
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
    def hooks(self) -> typing.Optional[Hooks[ContextT]]:
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
    async def check_context(self, ctx: MessageContext, /) -> typing.Optional[str]:
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
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
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
    def tracked_command(self) -> typing.Optional[command_interactions.Command]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self,
        ctx: ContextT,
        /,
        option: typing.Optional[command_interactions.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[typing.MutableSet[Hooks[ContextT]]] = None,
    ) -> None:
        raise NotImplementedError

    def set_tracked_command(self: _T, _: command_interactions.Command, /) -> _T:
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
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

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

    @property
    @abc.abstractmethod
    def parser(self) -> typing.Optional[Parser]:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[MessageCommandGroup], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parser(self: _T, _: typing.Optional[Parser], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def add_name(self: _T, name: str, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_name(self, name: str, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
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
    ) -> typing.Collection[typing.Tuple[typing.Type[base_events.Event], event_manager_api.CallbackT[typing.Any]]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
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
    ) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute_message(
        self, ctx: MessageContext, /, *, hooks: typing.Optional[typing.MutableSet[MessageHooks]] = None
    ) -> bool:
        raise NotImplementedError


class Client(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def cache(self) -> typing.Optional[cache_api.Cache]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def components(self) -> typing.Collection[Component]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[event_manager_api.EventManager]:
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
    def rest(self) -> rest_api.RESTClient:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[interaction_server_api.InteractionServer]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[traits.ShardAware]:
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


class UndefinedDefaultT:
    __singleton: typing.Optional[UndefinedDefaultT] = None

    def __new__(cls) -> UndefinedDefaultT:
        if cls.__singleton is None:
            cls.__singleton = super().__new__(cls)
            assert isinstance(cls.__singleton, UndefinedDefaultT)

        return cls.__singleton

    def __repr__(self) -> str:
        return "NOTHING"

    def __bool__(self) -> typing.Literal[False]:
        return False


UNDEFINED_DEFAULT = UndefinedDefaultT()
"""A singleton used to represent no default for a parameter."""


class Parameter(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def converters(self) -> typing.Optional[typing.Collection[ConverterSig]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def default(self) -> typing.Union[typing.Any, UndefinedDefaultT]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def flags(self) -> typing.MutableMapping[str, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def key(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def add_converter(self, converter: ConverterSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_converter(self, converter: ConverterSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def convert(self, ctx: MessageContext, value: str) -> typing.Any:
        raise NotImplementedError


class Argument(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()


class Option(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def empty_value(self) -> typing.Union[typing.Any, UndefinedDefaultT]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def names(self) -> typing.Collection[str]:
        raise NotImplementedError


class Parser(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def parameters(self) -> typing.Collection[Parameter]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_parameter(self, parameter: Parameter, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_parameter(self, parameter: Parameter, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parameters(self, _: typing.Iterable[Parameter], /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def parse(
        self, ctx: MessageContext, /
    ) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
        raise NotImplementedError
