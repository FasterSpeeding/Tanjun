# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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
"""Interfaces of the objects and clients used within Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "AnyCheckSig",
    "AnyHooks",
    "AppCommand",
    "AppCommandContext",
    "AutocompleteCallbackSig",
    "AutocompleteContext",
    "AutocompleteSig",
    "BaseSlashCommand",
    "CheckSig",
    "Client",
    "ClientCallbackNames",
    "ClientLoader",
    "CommandCallbackSig",
    "Component",
    "Context",
    "ErrorHookSig",
    "ExecutableCommand",
    "HookSig",
    "Hooks",
    "ListenerCallbackSig",
    "MenuCallbackSig",
    "MenuCommand",
    "MenuCommandCallbackSig",
    "MenuContext",
    "MenuHooks",
    "MessageCommand",
    "MessageCommandGroup",
    "MessageContext",
    "MessageHooks",
    "MetaEventSig",
    "ParserHookSig",
    "SlashCommand",
    "SlashCommandGroup",
    "SlashContext",
    "SlashHooks",
    "SlashOption",
]

import abc
import enum
import typing
from collections import abc as collections

import hikari
from alluka import abc as alluka

if typing.TYPE_CHECKING:
    import asyncio
    import datetime
    import pathlib
    from typing import Self

    from . import errors

    _BaseSlashCommandT = typing.TypeVar("_BaseSlashCommandT", bound="BaseSlashCommand")

    _AnyErrorHookSigT = typing.TypeVar("_AnyErrorHookSigT", bound="ErrorHookSig[typing.Any]")
    _MenuErrorHookSigT = typing.TypeVar("_MenuErrorHookSigT", bound="ErrorHookSig[MenuContext]")
    _MessageErrorHookSigT = typing.TypeVar("_MessageErrorHookSigT", bound="ErrorHookSig[MessageContext]")
    _SlashErrorHookSigT = typing.TypeVar("_SlashErrorHookSigT", bound="ErrorHookSig[SlashContext]")

    _AnyParserHookSigT = typing.TypeVar("_AnyParserHookSigT", bound="ParserHookSig[typing.Any]")
    _MenuParserHookSigT = typing.TypeVar("_MenuParserHookSigT", bound="ParserHookSig[MenuContext]")
    _MessageParserHookSigT = typing.TypeVar("_MessageParserHookSigT", bound="ParserHookSig[MessageContext]")
    _SlashParserHookSigT = typing.TypeVar("_SlashParserHookSigT", bound="ParserHookSig[SlashContext]")

    _AnyHookSigT = typing.TypeVar("_AnyHookSigT", bound="HookSig[typing.Any]")
    _MenuHookSigT = typing.TypeVar("_MenuHookSigT", bound="HookSig[MenuContext]")
    _MessageHookSigT = typing.TypeVar("_MessageHookSigT", bound="HookSig[MessageContext]")
    _SlashHookSigT = typing.TypeVar("_SlashHookSigT", bound="HookSig[SlashContext]")

    _ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound="ListenerCallbackSig[typing.Any]")
    _MenuCommandT = typing.TypeVar("_MenuCommandT", bound="MenuCommand[typing.Any, typing.Any]")
    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound="MessageCommand[typing.Any]")
    _MetaEventSigT = typing.TypeVar("_MetaEventSigT", bound="MetaEventSig")

    _DefaultT = typing.TypeVar("_DefaultT")

_T = typing.TypeVar("_T")
_AppCommandContextT = typing.TypeVar("_AppCommandContextT", bound="AppCommandContext")
_AutocompleteValueT = typing.TypeVar("_AutocompleteValueT", int, str, float)
_ContextT_co = typing.TypeVar("_ContextT_co", covariant=True, bound="Context")
_ContextT_contra = typing.TypeVar("_ContextT_contra", bound="Context", contravariant=True)
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
_MenuTypeT = typing.TypeVar(
    "_MenuTypeT", typing.Literal[hikari.CommandType.USER], typing.Literal[hikari.CommandType.MESSAGE]
)
_MenuValueT = typing.TypeVar("_MenuValueT", hikari.Message, hikari.InteractionMember)

CommandCallbackSig = collections.Callable[..., _CoroT[None]]
"""Deprecated type hint used to represent any command callback."""

MetaEventSig = collections.Callable[..., _CoroT[None] | None]
"""Type hint of a client callback.

The positional arguments this is guaranteed depend on the event name its being
subscribed to (more information the standard client callbacks can be found at
[ClientCallbackNames][tanjun.abc.ClientCallbackNames]) and may be either
synchronous or asynchronous but must return [None][].
"""

_MaybeAwaitable = _CoroT[_T] | _T

AutocompleteSig = collections.Callable[
    typing.Concatenate["AutocompleteContext", _AutocompleteValueT, ...], _CoroT[None]
]
"""Type hint of the signature an autocomplete callback should have.

This represents the signature
`async def (AutocompleteContext, int | str | float) -> None`
where dependency injection is supported.
"""

CheckSig = collections.Callable[typing.Concatenate[_ContextT_contra, ...], _MaybeAwaitable[bool]]
"""Type hint of a generic context check used with Tanjun commands.

This may be registered with a command, client or component to add a rule
which decides whether it should execute for each context passed to it.

This represents the signatures `def (Context, ...) -> bool | None`
and `async def (Context, ...) -> bool | None` where dependency
injection is  supported.

Check callbacks may either return [False][] to indicate that the current
command(s) don't match the context (without stopping execution) or raise
[tanjun.FailedCheck][] to indicate that command execution should be halted
early and marked as not found.
"""

AnyCheckSig = CheckSig["Context"]
"""Type hint of a check callback for any command type."""

MenuCallbackSig = collections.Callable[typing.Concatenate["MenuContext", _MenuValueT, ...], _CoroT[None]]
"""Type hint of a context menu command callback.

This represents the signature
`async def (MenuContext, hikari.Message, ...) -> None` or
`async def (MenuContext, hikari.InteractionMember, ...) ->  None`
where dependency injection is supported.
"""

_CommandCallbackSig = collections.Callable[typing.Concatenate[_ContextT_contra, ...], _CoroT[None]]

MessageCallbackSig = _CommandCallbackSig["MessageContext"]
"""Type hint of a message command callback.

This represents the signature `async def (MessageContext, ...) -> None`
where dependency injection is supported.
"""

SlashCallbackSig = _CommandCallbackSig["SlashContext"]
"""Type hint of a slash command callback.

This represents the signature `async def (SlashContext, ...) -> None`
where dependency injection is supported.
"""

ErrorHookSig = collections.Callable[typing.Concatenate[_ContextT_contra, Exception, ...], _MaybeAwaitable[bool | None]]
"""Type hint of the callback used as a unexpected command error hook.

This will be called whenever an unexpected [Exception][] is raised during the
execution stage of a command (ignoring [tanjun.ParserError][] and expected
[tanjun.TanjunError][] subclasses).

This represents the signatures `def (Context, Exception, ...) -> bool | None`
and `async def (Context, Exception, ...) -> bool | None` where
dependency injection is supported.

[True][] is returned to indicate that the exception should be suppressed and
[False][] is returned to indicate that the exception should be re-raised.
"""

ParserHookSig = collections.Callable[
    typing.Concatenate[_ContextT_contra, "errors.ParserError", ...], _MaybeAwaitable[bool | None]
]
"""Type hint of the callback used as a command parser error hook.

This will be called whenever an parser [ParserError][tanjun.errors.ParserError]
is raised during the execution stage of a command.

This represents the signatures `def (Context, tanjun.ParserError, ...) -> None`
and `async def (Context, tanjun.ParserError, ...) -> None` where
dependency injection is supported.

Parser errors are always suppressed (unlike general errors).
"""

HookSig = collections.Callable[typing.Concatenate[_ContextT_contra, ...], _MaybeAwaitable[None]]
"""Type hint of the callback used as a general command hook.

This represents the signatures `def (Context, ...) -> None` and
`async def (Context, ...) -> None` where dependency injection is
supported.
"""

_EventT = typing.TypeVar("_EventT", bound=hikari.Event)

ListenerCallbackSig = collections.Callable[typing.Concatenate[_EventT, ...], _CoroT[None]]
"""Type hint of a hikari event manager callback.

This represents the signature `async def (hikari.Event, ...) -> None` where
dependency injection is supported.
"""


AutocompleteCallbackSig = AutocompleteSig[_AutocompleteValueT]
"""Deprecated alias of [AutocompleteSig][tanjun.abc.AutocompleteSig]."""

MenuCommandCallbackSig = MenuCallbackSig[_MenuValueT]
"""Deprecated alias of [MenuCallbackSig][tanjun.abc.MenuCallbackSig]."""

_MenuCallbackSigT = typing.TypeVar("_MenuCallbackSigT", bound=MenuCallbackSig[typing.Any])
_MessageCallbackSigT = typing.TypeVar("_MessageCallbackSigT", bound=MessageCallbackSig)
_SlashCallbackSigT = typing.TypeVar("_SlashCallbackSigT", bound=SlashCallbackSig)


class _DefaultFlag(enum.Enum):
    NO_DEFAULT = object()
    NO_PASS = object()  # noqa: PIE796


NO_DEFAULT: NoDefault = _DefaultFlag.NO_DEFAULT
"""Singleton used to mark an argument as having no default."""

NoDefault = typing.Literal[_DefaultFlag.NO_DEFAULT]
"""Type hint of [tanjun.abc.NO_DEFAULT][]."""

NO_PASS = _DefaultFlag.NO_PASS
"""Singleton used to mark an argument as being not passed when it isn't provided."""


class Context(alluka.Context):
    """Interface for the context of a command execution."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def author(self) -> hikari.User:
        """Object of the user who triggered this command."""

    @property
    @abc.abstractmethod
    def channel_id(self) -> hikari.Snowflake:
        """ID of the channel this command was triggered in."""

    @property
    @abc.abstractmethod
    def cache(self) -> hikari.api.Cache | None:
        """Hikari cache instance this context's command client was initialised with."""

    @property
    @abc.abstractmethod
    def client(self) -> Client:
        """Tanjun [Client][tanjun.abc.Client] implementation this context was spawned by."""

    @property
    @abc.abstractmethod
    def component(self) -> Component | None:
        """Object of the [Component][tanjun.abc.Component] this context is bound to.

        !!! note
            This will only be [None][] before this has been bound to a
            specific command but never during command execution nor checks.
        """

    @property  # TODO: can we somehow have this always be present on the command execution facing interface
    @abc.abstractmethod
    def command(self) -> ExecutableCommand[Self] | None:
        """Object of the command this context is bound to.

        !!! note
            This will only be [None][] before this has been bound to a
            specific command but never during command execution.
        """

    @property
    @abc.abstractmethod
    def created_at(self) -> datetime.datetime:
        """When this context was created."""

    @property
    @abc.abstractmethod
    def events(self) -> hikari.api.EventManager | None:
        """Object of the event manager this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def guild_id(self) -> hikari.Snowflake | None:
        """ID of the guild this command was executed in.

        Will be [None][] for all DM command executions.
        """

    @property
    @abc.abstractmethod
    def has_responded(self) -> bool:
        """Whether an initial response has been made for this context."""

    @property
    @abc.abstractmethod
    def is_human(self) -> bool:
        """Whether this command execution was triggered by a human.

        Will be [False][] for bot and webhook triggered commands.
        """

    @property
    @abc.abstractmethod
    def member(self) -> hikari.Member | None:
        """Guild member object of this command's author.

        Will be [None][] for DM command executions.
        """

    @property
    @abc.abstractmethod
    def server(self) -> hikari.api.InteractionServer | None:
        """Object of the Hikari interaction server provided for this context's client."""

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def shard(self) -> hikari.api.GatewayShard | None:
        """Shard that triggered the context.

        !!! note
            This will be [None][] if [Context.shards][tanjun.abc.Context.shards]
            is also [None][].
        """

    @property
    @abc.abstractmethod
    def shards(self) -> hikari.ShardAware | None:
        """Object of the Hikari shard manager this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def voice(self) -> hikari.api.VoiceComponent | None:
        """Object of the Hikari voice component this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        """Command name this execution was triggered with."""

    @abc.abstractmethod
    def set_component(self, component: Component | None, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_channel(self) -> hikari.TextableChannel:
        """Fetch the channel the context was invoked in.

        !!! note
            This performs an API call. Consider using
            [Context.get_channel][tanjun.abc.Context.get_channel]if you have the
            [CacheComponents.GUILD_CHANNELS][hikari.api.config.CacheComponents.GUILD_CHANNELS]
            cache component enabled.

        Returns
        -------
        hikari.channels.TextableChannel
            The textable DM or guild channel the context was invoked in.

        Raises
        ------
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `READ_MESSAGES` permission in the channel.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def fetch_guild(self) -> hikari.Guild | None:
        """Fetch the guild the context was invoked in.

        !!! note
            This performs an API call. Consider using
            [Context.get_guild][tanjun.abc.Context.get_guild] if you have the
            [CacheComponents.GUILDS][hikari.api.config.CacheComponents.GUILDS]
            cache component enabled.

        Returns
        -------
        hikari.guilds.Guild | None
            An optional guild the context was invoked in.
            [None][] will be returned if the context was invoked in a DM channel.

        Raises
        ------
        hikari.errors.ForbiddenError
            If you are not part of the guild.
        hikari.errors.NotFoundError
            If the guild is not found.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    def get_channel(self) -> hikari.TextableGuildChannel | None:
        """Retrieve the channel the context was invoked in from the cache.

        !!! note
            This method requires the
            [CacheComponents.GUILD_CHANNELS][hikari.api.config.CacheComponents.GUILD_CHANNELS]
            cache component.

        Returns
        -------
        hikari.channels.TextableGuildChannel | None
            An optional guild channel the context was invoked in.
            [None][] will be returned if the channel was not found or if it
            is DM channel.
        """

    @abc.abstractmethod
    def get_guild(self) -> hikari.Guild | None:
        """Fetch the guild that the context was invoked in.

        !!! note
            This method requires the
            [CacheComponents.GUILDS][hikari.api.config.CacheComponents.GUILDS]
            cache component.

        Returns
        -------
        hikari.guilds.Guild | None
            An optional guild the context was invoked in.
            [None][] will be returned if the guild was not found.
        """

    @abc.abstractmethod
    async def delete_initial_response(self) -> None:
        """Delete the initial response after invoking this context.

        Raises
        ------
        LookupError, hikari.errors.NotFoundError
            The last context has no initial response.
        """

    @abc.abstractmethod
    async def delete_last_response(self) -> None:
        """Delete the last response after invoking this context.

        Raises
        ------
        LookupError, hikari.errors.NotFoundError
            The last context has no responses.
        """

    @abc.abstractmethod
    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Edit the initial response for this context.

        Parameters
        ----------
        content
            If provided, the message content to edit the initial response with.

            If this is a [hikari.Embed][hikari.embeds.Embed] and no `embed` nor
            `embeds` kwarg is provided, then this will instead update the embed.
            This allows for simpler syntax when sending an embed alone.

            Likewise, if this is a [hikari.Resource][hikari.files.Resource],
            then the content is instead treated as an attachment if no
            `attachment` and no `attachments` kwargs are provided.
        delete_after
            If provided, the seconds after which the response message should be deleted.

            Slash command responses can only be deleted within 15 minutes of
            the command being received.
        attachment
            A singular attachment to edit the initial response with.
        attachments
            A sequence of attachments to edit the initial response with.
        component
            If provided, builder object of the component to set for this message.
            This component will replace any previously set components and passing
            [None][] will remove all components.
        components
            If provided, a sequence of the component builder objects set for
            this message. These components will replace any previously set
            components and passing [None][] or an empty sequence will
            remove all components.
        embed
            An embed to replace the initial response with.
        embeds
            A sequence of embeds to replace the initial response with.
        mentions_everyone
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialUser][hikari.users.PartialUser]
            derivatives to enforce mentioning specific users.
        role_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialRole][hikari.guilds.PartialRole]
            derivatives to enforce mentioning specific roles.

        Returns
        -------
        hikari.messages.Message
            The message that has been edited.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If `delete_after` would be more than 15 minutes after the slash
            command was called.

            If both `attachment` and `attachments` are passed or both `component`
            and `components` are passed or both `embed` and `embeds` are passed.
        hikari.errors.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; too many components.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Edit the last response for this context.

        Parameters
        ----------
        content
            If provided, the content to edit the last response with.

            If this is a [hikari.Embed][hikari.embeds.Embed] and no `embed` nor
            `embeds` kwarg is provided, then this will instead update the embed.
            This allows for simpler syntax when sending an embed alone.

            Likewise, if this is a [hikari.Resource][hikari.files.Resource],
            then the content is instead treated as an attachment if no
            `attachment` and no `attachments` kwargs are provided.
        delete_after
            If provided, the seconds after which the response message should be deleted.

            Slash command responses can only be deleted within 15 minutes of
            the command being received.
        attachment
            A singular attachment to edit the last response with.
        attachments
            A sequence of attachments to edit the last response with.
        component
            If provided, builder object of the component to set for this message.
            This component will replace any previously set components and passing
            [None][] will remove all components.
        components
            If provided, a sequence of the component builder objects set for
            this message. These components will replace any previously set
            components and passing [None][] or an empty sequence will
            remove all components.
        embed
            An embed to replace the last response with.
        embeds
            A sequence of embeds to replace the last response with.
        mentions_everyone
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialUser][hikari.users.PartialUser]
            derivatives to enforce mentioning specific users.
        role_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialRole][hikari.guilds.PartialRole]
            derivatives to enforce mentioning specific roles.

        Returns
        -------
        hikari.messages.Message
            The message that has been edited.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If `delete_after` would be more than 15 minutes after the slash
            command was called.

            If both `attachment` and `attachments` are passed or both `component`
            and `components` are passed or both `embed` and `embeds` are passed.
        hikari.errors.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; too many components.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def fetch_initial_response(self) -> hikari.Message:
        """Fetch the initial response for this context.

        Raises
        ------
        LookupError, hikari.errors.NotFoundError
            The response was not found.
        """

    @abc.abstractmethod
    async def fetch_last_response(self) -> hikari.Message:
        """Fetch the last response for this context.

        Raises
        ------
        LookupError, hikari.errors.NotFoundError
            The response was not found.
        """

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message: ...

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message | None: ...

    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message | None:
        """Respond to this context.

        Parameters
        ----------
        content
            If provided, the message content to respond with.

            If this is a [hikari.Embed][hikari.embeds.Embed] and no `embed` nor
            `embeds` kwarg is provided, then this will instead be treated as an
            embed. This allows for simpler syntax when sending an embed alone.

            Likewise, if this is a [hikari.Resource][hikari.files.Resource],
            then the content is instead treated as an attachment if no
            `attachment` and no `attachments` kwargs are provided.
        ensure_result
            Ensure that this call will always return a message object.

            If [True][] then this will always return
            [hikari.Message][hikari.messages.Message], otherwise this will
            return `hikari.Message | None`.

            It's worth noting that, under certain scenarios within the slash
            command flow, this may lead to an extre request being made.
        delete_after
            If provided, the seconds after which the response message should be deleted.

            Slash command responses can only be deleted within 15 minutes of
            the command being received.
        attachment
            If provided, the message attachment. This can be a resource,
            or string of a path on your computer or a URL.
        attachments
            If provided, the message attachments. These can be resources, or
            strings consisting of paths on your computer or URLs.
        component
            If provided, builder object of the component to include in this response.
        components
            If provided, a sequence of the component builder objects to include
            in this response.
        embed
            An embed to respond with.
        embeds
            A sequence of embeds to respond with.
        mentions_everyone
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialUser][hikari.users.PartialUser]
            derivatives to enforce mentioning specific users.
        role_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialRole][hikari.guilds.PartialRole]
            derivatives to enforce mentioning specific roles.

        Returns
        -------
        hikari.messages.Message | None
            The message that has been created if it was immedieatly available or
            `ensure_result` was set to [True][], else [None][].

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If `delete_after` would be more than 15 minutes after the slash
            command was called.

            If both `attachment` and `attachments` are passed or both `component`
            and `components` are passed or both `embed` and `embeds` are passed.
        hikari.errors.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; too many components.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """


class MessageContext(Context, abc.ABC):
    """Interface of a message command specific context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> MessageCommand[typing.Any] | None:
        """Command that was invoked.

        !!! note
            This is always set during command, command check and parser
            converter execution but isn't guaranteed during client callback
            nor client/component check execution.
        """

    @property
    @abc.abstractmethod
    def content(self) -> str:
        """Content of the context's message minus the triggering name and prefix."""

    @property
    @abc.abstractmethod
    def message(self) -> hikari.Message:
        """Message that triggered the context."""

    @property
    @abc.abstractmethod
    def triggering_prefix(self) -> str:
        """Prefix that triggered the context."""

    @abc.abstractmethod
    def set_command(self, command: MessageCommand[typing.Any] | None, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def set_content(self, content: str, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def set_triggering_name(self, name: str, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = True,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        sticker: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialSticker]] = hikari.UNDEFINED,
        stickers: hikari.UndefinedOr[hikari.SnowflakeishSequence[hikari.PartialSticker]] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        reply: bool | hikari.SnowflakeishOr[hikari.PartialMessage] | hikari.UndefinedType = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Respond to this context.

        Parameters
        ----------
        content
            If provided, the message content to respond with.

            If this is a [hikari.Embed][hikari.embeds.Embed] and no `embed` nor
            `embeds` kwarg is provided, then this will instead be treated as an
            embed. This allows for simpler syntax when sending an embed alone.

            Likewise, if this is a [hikari.Resource][hikari.files.Resource],
            then the content is instead treated as an attachment if no
            `attachment` and no `attachments` kwargs are provided.
        ensure_result
            Ensure this method call will return a message object.

            This does nothing for message command contexts as the result w ill
            always be immedieatly available.
        delete_after
            If provided, the seconds after which the response message should be deleted.
        tts
            Whether to respond with tts/text to speech or no.
        reply
            Whether to reply instead of sending the content to the context.

            Passing [True][] here indicates a reply to
            [MessageContext.message][tanjun.abc.MessageContext.message].
        attachment
            A singular attachment to respond with.
        attachments
            A sequence of attachments to respond with.
        component
            If provided, builder object of the component to include in this message.
        components
            If provided, a sequence of the component builder objects to include
            in this message.
        embed
            An embed to respond with.
        embeds
            A sequence of embeds to respond with.
        sticker
            If provided, the object or ID of a sticker to send on the message.

            As of writing, bots can only send custom stickers from the current guild.
        stickers
            If provided, a sequence of the objects and IDs of up to 3 stickers
            to send on the message.

            As of writing, bots can only send custom stickers from the current guild.
        mentions_everyone
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialUser][hikari.users.PartialUser]
            derivatives to enforce mentioning specific users.
        role_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialRole][hikari.guilds.PartialRole]
            derivatives to enforce mentioning specific roles.

        Returns
        -------
        hikari.messages.Message
            The message that has been created.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If the interaction will have expired before `delete_after` is reached.

            If both `attachment` and `attachments` are passed or both `component`
            and `components` are passed or both `embed` and `embeds` are passed
            or both `sticker` and `stickers` are passed.
        hikari.errors.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; if `reply` is not found or not in the
            same channel as `channel`; too many components.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """


class SlashOption(abc.ABC):
    """Interface of slash command option with extra logic to help resolve it."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of this option."""

    @property
    @abc.abstractmethod
    def type(self) -> hikari.OptionType | int:
        """Type of this option."""

    @property
    @abc.abstractmethod
    def value(self) -> str | hikari.Snowflake | int | bool | float:
        """Value provided for this option.

        !!! note
            For discord entity option types (user, member, channel and role)
            this will be the entity's ID.
        """

    @abc.abstractmethod
    def boolean(self) -> bool:
        """Get the boolean value of this option.

        Raises
        ------
        TypeError
            If [SlashOption.type][tanjun.abc.SlashOption.type] is not BOOLEAN.
        """

    @abc.abstractmethod
    def float(self) -> float:
        """Get the float value of this option.

        Raises
        ------
        TypeError
            If [SlashOption.type][tanjun.abc.SlashOption.type] is not FLOAT.
        ValueError
            If called on the focused option for an autocomplete interaction
            when it's a malformed (incomplete) float.
        """

    @abc.abstractmethod
    def integer(self) -> int:
        """Get the integer value of this option.

        Raises
        ------
        TypeError
            If [SlashOption.type][tanjun.abc.SlashOption.type] is not INTEGER.
        ValueError
            If called on the focused option for an autocomplete interaction
            when it's a malformed (incomplete) integer.
        """

    @abc.abstractmethod
    def snowflake(self) -> hikari.Snowflake:
        """Get the ID of this option.

        Raises
        ------
        TypeError
            If [SlashOption.type][tanjun.abc.SlashOption.type] is not one of
            CHANNEL, MENTIONABLE, ROLE or USER.
        """

    @abc.abstractmethod
    def string(self) -> str:
        """Get the string value of this option.

        Raises
        ------
        TypeError
            If [SlashOption.type][tanjun.abc.SlashOption.type] is not STRING.
        """

    @abc.abstractmethod
    def resolve_value(
        self,
    ) -> hikari.Attachment | hikari.InteractionChannel | hikari.InteractionMember | hikari.Role | hikari.User:
        """Resolve this option to an object value.

        Returns
        -------
        hikari.messages.Attachment | hikari.interactions.base_interactions.InteractionChannel | hikari.interactions.base_interactions.InteractionMember | hikari.guilds.Role | hikari.users.User
            The object value of this option.

        Raises
        ------
        TypeError
            If the option isn't resolvable.
        """  # noqa: E501

    @abc.abstractmethod
    def resolve_to_attachment(self) -> hikari.Attachment:
        """Resolve this option to a channel object.

        Returns
        -------
        hikari.messages.Attachment
            The attachment object.

        Raises
        ------
        TypeError
            If the option is not an attachment.
        """

    @abc.abstractmethod
    def resolve_to_channel(self) -> hikari.InteractionChannel:
        """Resolve this option to a channel object.

        Returns
        -------
        hikari.interactions.base_interactions.InteractionChannel
            The channel object.

        Raises
        ------
        TypeError
            If the option is not a channel.
        """

    @typing.overload
    @abc.abstractmethod
    def resolve_to_member(self) -> hikari.InteractionMember: ...

    @typing.overload
    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T) -> hikari.InteractionMember | _T: ...

    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T = ...) -> hikari.InteractionMember | _T:
        """Resolve this option to a member object.

        Parameters
        ----------
        default
            The default value to return if this option cannot be resolved.

            If this is not provided, this method will raise a `TypeError` if
            this option cannot be resolved.

        Returns
        -------
        hikari.interactions.base_interactions.InteractionMember | _T
            The member object or `default` if it was provided and this option
            was a user type but had no member.

        Raises
        ------
        LookupError
            If no member was found for this option and a `default` wasn't provided.

            This includes if the option is a mentionable type which targets a
            member-less user.

            This could happen if the user isn't in the current guild or if this
            command was executed in a DM and this option should still be resolvable
            to a user.
        TypeError
            If the option is not a user option and a `default` wasn't provided.

            This includes if the option is a mentionable type but doesn't
            target a user.
        """

    @abc.abstractmethod
    def resolve_to_mentionable(self) -> hikari.Role | hikari.User | hikari.Member:
        """Resolve this option to a mentionable object.

        Returns
        -------
        hikari.guilds.Role | hikari.users.User | hikari.guilds.Member
            The mentionable object.

        Raises
        ------
        TypeError
            If the option is not a mentionable, user or role type.
        """

    @abc.abstractmethod
    def resolve_to_role(self) -> hikari.Role:
        """Resolve this option to a role object.

        Returns
        -------
        hikari.guilds.Role
            The role object.

        Raises
        ------
        TypeError
            If the option is not a role.

            This includes mentionable options which point towards a user.
        """

    @abc.abstractmethod
    def resolve_to_user(self) -> hikari.User | hikari.Member:
        """Resolve this option to a user object.

        !!! note
            This will resolve to a [hikari.Member][hikari.guilds.Member] first
            if the relevant command was executed within a guild and the option
            targeted one of the guild's members, otherwise it will resolve to
            [hikari.User][hikari.users.User].

            It's also worth noting that hikari.Member inherits from hikari.User
            meaning that the return value of this can always be treated as a
            user.

        Returns
        -------
        hikari.users.User | hikari.guilds.Member
            The user object.

        Raises
        ------
        TypeError
            If the option is not a user.

            This includes mentionable options which point towards a role.
        """


class AppCommandContext(Context, abc.ABC):
    """Base class for application command contexts."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        """Whether the context is marked as defaulting to ephemeral response.

        This effects calls to
        [AppCommandContext.create_followup][tanjun.abc.AppCommandContext.create_followup],
        [AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response],
        [AppCommandContext.defer][tanjun.abc.AppCommandContext.defer]
        and [AppCommandContext.respond][tanjun.abc.Context.respond]
        unless the `flags` field is provided for the methods which support it.
        """

    @property
    @abc.abstractmethod
    def expires_at(self) -> datetime.datetime:
        """When this application command context expires.

        After this time is reached, the message/response methods on this
        context will always raise
        [hikari.NotFoundError][hikari.errors.NotFoundError].
        """

    @property
    @abc.abstractmethod
    def has_been_deferred(self) -> bool:
        """Whether the initial response for this context has been deferred.

        !!! warning
            If this is [True][] when [AppCommandContext.has_responded][tanjun.abc.Context.has_responded]
            is [False][] then [AppCommandContext.edit_initial_response][tanjun.abc.Context.edit_initial_response]
            will need to be used to create the initial response rather than
            [AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response].
        """

    @property
    @abc.abstractmethod
    def interaction(self) -> hikari.CommandInteraction:
        """Interaction this context is for."""

    @property
    @abc.abstractmethod
    def member(self) -> hikari.InteractionMember | None:
        """Object of the member that triggered this command if this is in a guild."""

    @property
    @abc.abstractmethod
    def type(self) -> hikari.CommandType:
        """Type of application command this context is for."""

    @abc.abstractmethod
    def set_ephemeral_default(self, state: bool, /) -> Self:  # noqa: FBT001
        """Set the ephemeral default state for this context.

        Parameters
        ----------
        state
            The new ephemeral default state.

            If this is [True][] then all calls to the response creating methods
            on this context will default to being ephemeral.
        """

    @abc.abstractmethod
    async def defer(
        self,
        *,
        ephemeral: bool | None = None,
        flags: hikari.UndefinedType | int | hikari.MessageFlag = hikari.UNDEFINED,
    ) -> None:
        """Defer the initial response for this context.

        !!! note
            The ephemeral state of the first response is decided by whether the
            deferral is ephemeral.

        Parameters
        ----------
        ephemeral
            Whether the deferred response should be ephemeral.

            Passing [True][] here is a shorthand for including `1 << 64` in the
            passed flags.
        flags
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
        delete_after: datetime.timedelta | float | int | None = None,
        ephemeral: bool | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: hikari.UndefinedType | int | hikari.MessageFlag = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Create a followup response for this context.

        !!! warning
            Calling this on a context which hasn't had an initial response yet
            will lead to a [hikari.NotFoundError][hikari.errors.NotFoundError]
            being raised.

        Parameters
        ----------
        content
            If provided, the message content to send.

            If this is a [hikari.Embed][hikari.embeds.Embed] and no `embed` nor
            `embeds` kwarg is provided, then this will instead be treated as an
            embed. This allows for simpler syntax when sending an embed alone.

            Likewise, if this is a [hikari.Resource][hikari.files.Resource],
            then the content is instead treated as an attachment if no
            `attachment` and no `attachments` kwargs are provided.
        delete_after
            If provided, the seconds after which the response message should be deleted.

            Slash command responses can only be deleted within 15 minutes of the
            command being received.
        ephemeral
            Whether the deferred response should be ephemeral.

            Passing [True][] here is a shorthand for including `1 << 64` in the
            passed flags.
        attachment
            If provided, the message attachment. This can be a resource,
            or string of a path on your computer or a URL.
        attachments
            If provided, the message attachments. These can be resources, or
            strings consisting of paths on your computer or URLs.
        component
            If provided, builder object of the component to include in this message.
        components
            If provided, a sequence of the component builder objects to include
            in this message.
        embed
            If provided, the message embed.
        embeds
            If provided, the message embeds.
        mentions_everyone
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialUser][hikari.users.PartialUser]
            derivatives to enforce mentioning specific users.
        role_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialRole][hikari.guilds.PartialRole]
            derivatives to enforce mentioning specific roles.
        tts
            If provided, whether the message will be sent as a TTS message.
        flags
            The flags to set for this response.

            As of writing this can only flag which can be provided is EPHEMERAL,
            other flags are just ignored.

        Returns
        -------
        hikari.messages.Message
            The created message object.

        Raises
        ------
        hikari.errors.NotFoundError
            If the current interaction is not found or it hasn't had an initial
            response yet.
        hikari.errors.BadRequestError
            This can be raised if the file is too large; if the embed exceeds
            the defined limits; if the message content is specified only and
            empty or greater than `2000` characters; if neither content, file
            or embeds are specified.
            If any invalid snowflake IDs are passed; a snowflake may be invalid
            due to it being outside of the range of a 64 bit integer.
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions.

            If the interaction will have expired before `delete_after` is reached.

            If both `attachment` and `attachments` are passed or both `component`
            and `components` are passed or both `embed` and `embeds` are passed.
        """

    @abc.abstractmethod
    async def create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        ephemeral: bool | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        """Create the initial response for this context.

        !!! warning
            Calling this on a context which already has an initial response
            will result in this raising a
            [hikari.NotFoundError][hikari.errors.NotFoundError]. This includes
            if the REST interaction server has already responded to the
            request and deferrals.

        Parameters
        ----------
        content
            If provided, the message content to respond with.

            If this is a [hikari.Embed][hikari.embeds.Embed] and no `embed` nor
            `embeds` kwarg is provided, then this will instead be treated as an
            embed. This allows for simpler syntax when sending an embed alone.

            Likewise, if this is a [hikari.Resource][hikari.files.Resource],
            then the content is instead treated as an attachment if no
            `attachment` and no `attachments` kwargs are provided.
        delete_after
            If provided, the seconds after which the response message should be deleted.

            Slash command responses can only be deleted within 15 minutes of the
            command being received.
        ephemeral
            Whether the deferred response should be ephemeral.

            Passing [True][] here is a shorthand for including `1 << 64` in the
            passed flags.
        attachment
            If provided, the message attachment. This can be a resource,
            or string of a path on your computer or a URL.
        attachments
            If provided, the message attachments. These can be resources, or
            strings consisting of paths on your computer or URLs.
        component
            If provided, builder object of the component to include in this message.
        components
            If provided, a sequence of the component builder objects to include
            in this message.
        embed
            If provided, the message embed.
        embeds
            If provided, the message embeds.
        flags
            If provided, the message flags this response should have.

            As of writing the only message flag which can be set here is
            [MessageFlag.EPHEMERAL][hikari.messages.MessageFlag.EPHEMERAL].
        tts
            If provided, whether the message will be read out by a screen
            reader using Discord's TTS (text-to-speech) system.
        mentions_everyone
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialUser][hikari.users.PartialUser]
            derivatives to enforce mentioning specific users.
        role_mentions
            If provided, and [True][], all mentions will be parsed.
            If provided, and [False][], no mentions will be parsed.

            Alternatively this may be a collection of
            [hikari.Snowflake][hikari.snowflakes.Snowflake], or
            [hikari.PartialRole][hikari.guilds.PartialRole]
            derivatives to enforce mentioning specific roles.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If the interaction will have expired before `delete_after` is reached.

            If both `attachment` and `attachments` are passed or both `component`
            and `components` are passed or both `embed` and `embeds` are passed.
        hikari.errors.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; invalid image URLs in embeds.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.NotFoundError
            If the interaction is not found or if the interaction's initial
            response has already been created.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def create_modal_response(
        self,
        title: str,
        custom_id: str,
        /,
        *,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
    ) -> None:
        """Send a modal as the initial response for this context.

        !!! warning
            This must be called as the first response to a context before any
            deferring.

        Parameters
        ----------
        title
            The title that will show up in the modal.
        custom_id
            Developer set custom ID used for identifying interactions with this modal.
        component
            A component builder to send in this modal.
        components
            A sequence of component builders to send in this modal.

        Raises
        ------
        ValueError
            If both `component` and `components` are specified or if none are specified.
        hikari.errors.BadRequestError
            When the requests' data is outside Discord's accept ranges/validation.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.NotFoundError
            If the interaction is not found or if the interaction's initial
            response has already been created or deferred.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """


class MenuContext(AppCommandContext, abc.ABC):
    """Interface of a menu command context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> MenuCommand[typing.Any, typing.Any] | None:
        """Command that was invoked.

        !!! note
            This should always be set during command check execution and command
            hook execution but isn't guaranteed for client callbacks nor
            component/client checks.
        """

    @property
    @abc.abstractmethod
    def target_id(self) -> hikari.Snowflake:
        """ID of the entity this menu command context targets."""

    @property
    @abc.abstractmethod
    def target(self) -> hikari.InteractionMember | hikari.User | hikari.Message:
        """Object of the entity this menu targets."""

    @property
    @abc.abstractmethod
    def type(self) -> typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER]:
        """The type of context menu this context is for."""

    @abc.abstractmethod
    def set_command(self, command: MenuCommand[typing.Any, typing.Any] | None, /) -> Self:
        """Set the command for this context.

        Parameters
        ----------
        command
            The command this context is for.
        """

    @typing.overload
    @abc.abstractmethod
    def resolve_to_member(self) -> hikari.InteractionMember: ...

    @typing.overload
    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T) -> hikari.InteractionMember | _T: ...

    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T = ...) -> hikari.InteractionMember | _T:
        """Resolve a user context menu context to a member object.

        Returns
        -------
        hikari.interactions.base_interactions.InteractionMember
            The resolved member.

        Raises
        ------
        TypeError
            If the context is not a user menu context.
        LookupError
            If the member was not found for this user menu context.

            This will happen if this was executed in a DM or the target
            user isn't in the current guild.
        """

    @abc.abstractmethod
    def resolve_to_message(self) -> hikari.Message:
        """Resolve a message context menu to a message object.

        Returns
        -------
        hikari.messages.Message
            The resolved message.

        Raises
        ------
        TypeError
            if the context is not for a message menu.
        """

    @abc.abstractmethod
    def resolve_to_user(self) -> hikari.User | hikari.Member:
        """Resolve a user context menu context to a user object.

        Returns
        -------
        hikari.users.User | hikari.guilds.Member
            The resolved user.

        Raises
        ------
        TypeError
            If the context is not a user menu context.
        """


class SlashContext(AppCommandContext, abc.ABC):
    """Interface of a slash command specific context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> BaseSlashCommand | None:
        """Command that was invoked.

        !!! note
            This should always be set during command check execution and command
            hook execution but isn't guaranteed for client callbacks nor
            component/client checks.
        """

    @property
    @abc.abstractmethod
    def options(self) -> collections.Mapping[str, SlashOption]:
        """Mapping of option names to the values provided for them."""

    @property
    @abc.abstractmethod
    def type(self) -> typing.Literal[hikari.CommandType.SLASH]:
        """Type of application command this context is for."""

    @abc.abstractmethod
    def set_command(self, command: BaseSlashCommand | None, /) -> Self:
        """Set the command for this context.

        Parameters
        ----------
        command
            The command this context is for.
        """


class AutocompleteContext(alluka.Context):
    """Interface of an autocomplete context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def author(self) -> hikari.User:
        """Object of the user who triggered this autocomplete."""

    @property
    @abc.abstractmethod
    def channel_id(self) -> hikari.Snowflake:
        """ID of the channel this autocomplete was triggered in."""

    @property
    @abc.abstractmethod
    def cache(self) -> hikari.api.Cache | None:
        """Hikari cache instance this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def client(self) -> Client:
        """Tanjun [Client][tanjun.abc.Client] implementation this context was spawned by."""

    @property
    @abc.abstractmethod
    def created_at(self) -> datetime.datetime:
        """When this context was created.

        !!! note
            This will either refer to a message or integration's creation date.
        """

    @property
    @abc.abstractmethod
    def events(self) -> hikari.api.EventManager | None:
        """Object of the event manager this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def focused(self) -> hikari.AutocompleteInteractionOption:
        """The option being autocompleted."""

    @property
    @abc.abstractmethod
    def guild_id(self) -> hikari.Snowflake | None:
        """ID of the guild this autocomplete was triggered in.

        Will be [None][] for all DM autocomplete executions.
        """

    @property
    @abc.abstractmethod
    def member(self) -> hikari.Member | None:
        """Guild member object of this autocomplete's author.

        Will be [None][] for DM autocomplete executions.
        """

    @property
    @abc.abstractmethod
    def server(self) -> hikari.api.InteractionServer | None:
        """Object of the Hikari interaction server provided for this context's client."""

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def shard(self) -> hikari.api.GatewayShard | None:
        """Shard that triggered the context.

        !!! note
            This will be [None][] if [AutocompleteContext.shards][tanjun.abc.AutocompleteContext.shards]
            is also [None][].
        """

    @property
    @abc.abstractmethod
    def shards(self) -> hikari.ShardAware | None:
        """Object of the Hikari shard manager this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def voice(self) -> hikari.api.VoiceComponent | None:
        """Object of the Hikari voice component this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def has_responded(self) -> bool:
        """Whether the choices have been set for this autocomplete."""

    @property
    @abc.abstractmethod
    def interaction(self) -> hikari.AutocompleteInteraction:
        """Interaction this context is for."""

    @property
    @abc.abstractmethod
    def options(self) -> collections.Mapping[str, hikari.AutocompleteInteractionOption]:
        """Mapping of option names to the values provided for them."""

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        """Full command name this autocomplete was triggered for."""

    @abc.abstractmethod
    async def fetch_channel(self) -> hikari.TextableChannel:
        """Fetch the channel the context was invoked in.

        !!! note
            This performs an API call. Consider using
            [AutocompleteContext.get_channel][tanjun.abc.AutocompleteContext.get_channel]
            if you have the
            [CacheComponents.GUILD_CHANNELS][hikari.api.config.CacheComponents.GUILD_CHANNELS]
            cache component enabled.

        Returns
        -------
        hikari.channels.TextableChannel
            The textable DM or guild channel the context was invoked in.

        Raises
        ------
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.ForbiddenError
            If you are missing the `READ_MESSAGES` permission in the channel.
        hikari.errors.NotFoundError
            If the channel is not found.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def fetch_guild(self) -> hikari.Guild | None:
        """Fetch the guild the context was invoked in.

        !!! note
            This performs an API call. Consider using
            [AutocompleteContext.get_guild][tanjun.abc.AutocompleteContext.get_guild]
            if you have the
            [CacheComponents.GUILDS][hikari.api.config.CacheComponents.GUILDS]
            cache component enabled.

        Returns
        -------
        hikari.guilds.Guild | None
            An optional guild the context was invoked in.
            [None][] will be returned if the context was invoked in a DM channel.

        Raises
        ------
        hikari.errors.ForbiddenError
            If you are not part of the guild.
        hikari.errors.NotFoundError
            If the guild is not found.
        hikari.errors.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.errors.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.errors.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    def get_channel(self) -> hikari.TextableGuildChannel | None:
        """Retrieve the channel the context was invoked in from the cache.

        !!! note
            This method requires the
            [CacheComponents.GUILD_CHANNELS][hikari.api.config.CacheComponents.GUILD_CHANNELS]
            cache component.

        Returns
        -------
        hikari.channels.TextableGuildChannel | None
            An optional guild channel the context was invoked in.
            [None][] will be returned if the channel was not found or if it
            is DM channel.
        """

    @abc.abstractmethod
    def get_guild(self) -> hikari.Guild | None:
        """Fetch the guild that the context was invoked in.

        !!! note
            This method requires the
            [CacheComponents.GUILDS][hikari.api.config.CacheComponents.GUILDS]
            cache component.

        Returns
        -------
        hikari.guilds.Guild | None
            An optional guild the context was invoked in.
            [None][] will be returned if the guild was not found.
        """

    @abc.abstractmethod
    async def set_choices(
        self,
        choices: (
            collections.Mapping[str, _AutocompleteValueT] | collections.Iterable[tuple[str, _AutocompleteValueT]]
        ) = ...,
        /,
        **kwargs: _AutocompleteValueT,
    ) -> None:
        """Set the choices for this autocomplete.

        !!! note
            Only up to (and including) 25 choices may be set for an autocomplete.

        Parameters
        ----------
        choices : collections.abc.Mapping[str, str | float | int]
            Mapping of string option names to their values.

            The values should match the focused option's relevant type.
        **kwargs : str | float | int
            Keyword arguments mapping string option names to their values.

            The value should match the focused option's relevant type.

        Raises
        ------
        RuntimeError
            If the context has already had the choices set for it.
        ValueError
            If more than 25 choices are passed.
        """


class Hooks(abc.ABC, typing.Generic[_ContextT_contra]):
    """Interface of a collection of callbacks called during set stage of command execution."""

    __slots__ = ()

    @abc.abstractmethod
    def copy(self) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def add_on_error(self, callback: ErrorHookSig[_ContextT_contra], /) -> Self:
        """Add an error callback to this hook object.

        !!! note
            This won't be called for expected [tanjun.TanjunError][] derived errors.

        Parameters
        ----------
        callback
            The callback to add to this hook.

            This callback should take two positional arguments (of type
            [Context][tanjun.abc.Context] and [Exception][]) and may be either
            synchronous or asynchronous.

            Returning [True][] indicates that the error should be suppressed,
            [False][] that it should be re-raised and [None][] that no decision has
            been made. This will be accounted for along with the decisions
            other error hooks make by majority rule.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def with_on_error(self: AnyHooks, callback: _AnyErrorHookSigT, /) -> _AnyErrorHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_error(self: MenuHooks, callback: _MenuErrorHookSigT, /) -> _MenuErrorHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_error(self: MessageHooks, callback: _MessageErrorHookSigT, /) -> _MessageErrorHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_error(self: SlashHooks, callback: _SlashErrorHookSigT, /) -> _SlashErrorHookSigT: ...

    @abc.abstractmethod
    def with_on_error(self, callback: _AnyErrorHookSigT, /) -> _AnyErrorHookSigT:
        """Add an error callback to this hook object through a decorator call.

        !!! note
            This won't be called for expected [tanjun.TanjunError][] derived errors.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_error
        async def on_error(ctx: tanjun.abc.Context, error: Exception) -> bool:
            if isinstance(error, SomeExpectedType):
                await ctx.respond("You dun goofed")
                return True  # Indicating that it should be suppressed.

            await ctx.respond(f"An error occurred: {error}")
            return False  # Indicating that it should be re-raised
        ```

        Parameters
        ----------
        callback : ErrorHookSig
            The callback to add to this hook.

            This callback should take two positional arguments (of type
            [Context][tanjun.abc.Context] and [Exception][]) and may be either
            synchronous or asynchronous.

            Returning [True][] indicates that the error should be suppressed,
            [False][] that it should be re-raised and [None][] that no decision
            has been made. This will be accounted for along with the decisions
            other error hooks make by majority rule.

        Returns
        -------
        ErrorHookSig
            The hook callback which was added.
        """

    @abc.abstractmethod
    def add_on_parser_error(self, callback: ParserHookSig[_ContextT_contra], /) -> Self:
        """Add a parser error callback to this hook object.

        Parameters
        ----------
        callback
            The callback to add to this hook.

            This callback should take two positional arguments (of type
            [Context][tanjun.abc.Context] and [tanjun.ParserError][]),
            return [None][] and may be either synchronous or asynchronous.

            It's worth noting that this unlike general error handlers, this will
            always suppress the error.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def with_on_parser_error(self: AnyHooks, callback: _AnyParserHookSigT, /) -> _AnyParserHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_parser_error(self: MenuHooks, callback: _MenuParserHookSigT, /) -> _MenuParserHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_parser_error(self: MessageHooks, callback: _MessageParserHookSigT, /) -> _MessageParserHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_parser_error(self: SlashHooks, callback: _SlashParserHookSigT, /) -> _SlashParserHookSigT: ...

    @abc.abstractmethod
    def with_on_parser_error(self, callback: _AnyParserHookSigT, /) -> _AnyParserHookSigT:
        """Add a parser error callback to this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_parser_error
        async def on_parser_error(ctx: tanjun.abc.Context, error: tanjun.ParserError) -> None:
            await ctx.respond(f"You gave invalid input: {error}")
        ```

        Parameters
        ----------
        callback : ParserHookSig
            The parser error callback to add to this hook.

            This callback should take two positional arguments (of type
            [Context][tanjun.abc.Context] and [tanjun.ParserError][]), return
            [None][] and may be either synchronous or asynchronous.

        Returns
        -------
        HookSig
            The callback which was added.
        """

    @abc.abstractmethod
    def add_post_execution(self, callback: HookSig[_ContextT_contra], /) -> Self:
        """Add a post-execution callback to this hook object.

        Parameters
        ----------
        callback
            The callback to add to this hook.

            This callback should take one positional argument (of type
            [Context][tanjun.abc.Context]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def with_post_execution(self: AnyHooks, callback: _AnyHookSigT, /) -> _AnyHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_post_execution(self: MenuHooks, callback: _MenuHookSigT, /) -> _MenuHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_post_execution(self: MessageHooks, callback: _MessageHookSigT, /) -> _MessageHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_post_execution(self: SlashHooks, callback: _SlashHookSigT, /) -> _SlashHookSigT: ...

    @abc.abstractmethod
    def with_post_execution(self, callback: _AnyHookSigT, /) -> _AnyHookSigT:
        """Add a post-execution callback to this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_post_execution
        async def post_execution(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You did something")
        ```

        Parameters
        ----------
        callback : HookSig
            The post-execution callback to add to this hook.

            This callback should take one positional argument (of type
            [Context][tanjun.abc.Context]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        HookSig
            The post-execution callback which was seaddedt.
        """

    @abc.abstractmethod
    def add_pre_execution(self, callback: HookSig[_ContextT_contra], /) -> Self:
        """Add a pre-execution callback for this hook object.

        Parameters
        ----------
        callback
            The callback to add to this hook.

            This callback should take one positional argument (of type
            [Context][tanjun.abc.Context]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def with_pre_execution(self: AnyHooks, callback: _AnyHookSigT, /) -> _AnyHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_pre_execution(self: MenuHooks, callback: _MenuHookSigT, /) -> _MenuHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_pre_execution(self: MessageHooks, callback: _MessageHookSigT, /) -> _MessageHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_pre_execution(self: SlashHooks, callback: _SlashHookSigT, /) -> _SlashHookSigT: ...

    @abc.abstractmethod
    def with_pre_execution(self, callback: _AnyHookSigT, /) -> _AnyHookSigT:
        """Add a pre-execution callback to this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_pre_execution
        async def pre_execution(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You did something")
        ```

        Parameters
        ----------
        callback : HookSig
            The pre-execution callback to add to this hook.

            This callback should take one positional argument (of type
            [Context][tanjun.abc.Context]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        HookSig
            The pre-execution callback which was added.
        """

    @abc.abstractmethod
    def add_on_success(self, callback: HookSig[_ContextT_contra], /) -> Self:
        """Add a success callback to this hook object.

        Parameters
        ----------
        callback
            The callback to add to this hook.

            This callback should take one positional argument (of type
            [Context][tanjun.abc.Context]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def with_on_success(self: AnyHooks, callback: _AnyHookSigT, /) -> _AnyHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_success(self: MenuHooks, callback: _MenuHookSigT, /) -> _MenuHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_success(self: MessageHooks, callback: _MessageHookSigT, /) -> _MessageHookSigT: ...

    @typing.overload
    @abc.abstractmethod
    def with_on_success(self: SlashHooks, callback: _SlashHookSigT, /) -> _SlashHookSigT: ...

    @abc.abstractmethod
    def with_on_success(self, callback: _AnyHookSigT, /) -> _AnyHookSigT:
        """Add a success callback to this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_success
        async def on_success(ctx: tanjun.abc.Context) -> None:
            await ctx.respond("You did something")
        ```

        Parameters
        ----------
        callback : HookSig
            The success callback to add to this hook.

            This callback should take one positional argument (of type
            [Context][tanjun.abc.Context]), return [None][] and may be either
            synchronous or asynchronous.

        Returns
        -------
        HookSig
            The success callback which was added.
        """

    @abc.abstractmethod
    async def trigger_error(
        self,
        ctx: _ContextT_contra,
        exception: Exception,
        /,
        *,
        hooks: collections.Set[Hooks[_ContextT_contra]] | None = None,
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_post_execution(
        self, ctx: _ContextT_contra, /, *, hooks: collections.Set[Hooks[_ContextT_contra]] | None = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_pre_execution(
        self, ctx: _ContextT_contra, /, *, hooks: collections.Set[Hooks[_ContextT_contra]] | None = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_success(
        self, ctx: _ContextT_contra, /, *, hooks: collections.Set[Hooks[_ContextT_contra]] | None = None
    ) -> None:
        raise NotImplementedError


AnyHooks = Hooks[Context]
"""Execution hooks for any context."""

MessageHooks = Hooks[MessageContext]
"""Execution hooks for messages commands."""

MenuHooks = Hooks[MenuContext]
"""Execution hooks for menu commands."""

SlashHooks = Hooks[SlashContext]
"""Execution hooks for slash commands."""


class ExecutableCommand(abc.ABC, typing.Generic[_ContextT_co]):
    """Base class for all commands that can be executed."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def checks(self) -> collections.Collection[CheckSig[_ContextT_co]]:
        """Collection of checks that must be met before the command can be executed."""

    @property
    @abc.abstractmethod
    def component(self) -> Component | None:
        """Component that the command is registered with."""

    @property
    @abc.abstractmethod
    def hooks(self) -> Hooks[_ContextT_co] | None:
        """Hooks that are triggered when the command is executed."""

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Mutable mapping of metadata set for this command.

        !!! note
            Any modifications made to this mutable mapping will be preserved by
            the command.
        """

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self) -> Self:
        """Create a copy of this command.

        Returns
        -------
        Self
            A copy of this command.
        """

    @abc.abstractmethod
    def set_hooks(self, hooks: Hooks[_ContextT_co] | None, /) -> Self:
        """Set the hooks that are triggered when the command is executed.

        Parameters
        ----------
        hooks : Hooks[Context] | None
            The hooks that are triggered when the command is executed.

        Returns
        -------
        Self
            This command to enable chained calls
        """

    @abc.abstractmethod
    def add_check(self, *checks: CheckSig[_ContextT_co]) -> Self:  # TODO: remove or add with_check?
        """Add a check to the command.

        Parameters
        ----------
        *checks
            The checks to add.

        Returns
        -------
        Self
            This command to enable chained calls
        """

    @abc.abstractmethod
    def remove_check(self, check: CheckSig[_ContextT_co], /) -> Self:
        """Remove a check from the command.

        Parameters
        ----------
        check
            The check to remove.

        Raises
        ------
        ValueError
            If the provided check isn't found.

        Returns
        -------
        Self
            This command to enable chained calls
        """

    @abc.abstractmethod
    def set_metadata(self, key: typing.Any, value: typing.Any, /) -> Self:
        """Set a field in the command's metadata.

        Parameters
        ----------
        key
            Metadata key to set.
        value
            Metadata value to set.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """


class AppCommand(ExecutableCommand[_AppCommandContextT]):
    """Base class for all application command classes."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def default_member_permissions(self) -> hikari.Permissions | None:
        """The default guild member permissions required to use this command.

        !!! warning
            This can be overridden by guild staff and does not apply to admins.

        !!! warning
            For commands within command groups the state of this flag
            is inherited regardless of what it's set as on the child command.
        """

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool | None:
        """Whether contexts executed by this command should default to ephemeral responses.

        This effects calls to
        [AppCommandContext.create_followup][tanjun.abc.AppCommandContext.create_followup],
        [AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response],
        [AppCommandContext.defer][tanjun.abc.AppCommandContext.defer] and
        [AppCommandContext.respond][tanjun.abc.Context.respond]
        unless the `flags` field is provided for the methods which support it.

        !!! note
            If this is [None][] then the default from the parent command(s),
            component or client is used.
        """

    @property
    @abc.abstractmethod
    def is_dm_enabled(self) -> bool | None:
        """Whether this command is enabled in DM contexts.

        !!! note
            If this is [None][] then the default from the parent component or
            client is used.

        !!! warning
            For commands within command groups the state of this flag
            is inherited regardless of what it's set as on the child command.
        """

    @property
    @abc.abstractmethod
    def is_global(self) -> bool:
        """Whether the command should be declared globally or not.

        !!! warning
            For commands within command groups the state of this flag
            is inherited regardless of what it's set as on the child command.
        """

    @property
    def is_nsfw(self) -> bool | None:
        """Whether a command should only be accessible in channels marked as NSFW."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the command."""

    @property
    @abc.abstractmethod
    def tracked_command(self) -> hikari.PartialCommand | None:
        """Object of the actual command this object tracks if set."""

    @property
    @abc.abstractmethod
    def tracked_command_id(self) -> hikari.Snowflake | None:
        """ID of the actual command this object tracks if set."""

    @property
    @abc.abstractmethod
    def type(self) -> hikari.CommandType:
        """The type of this application command."""

    @abc.abstractmethod
    def build(self, *, component: Component | None = None) -> hikari.api.CommandBuilder:
        """Get a builder object for this command.

        Parameters
        ----------
        component
            The component to inherit config like `default_member_permissions` and
            `is_dm_enabled` from if not explicitly set on the command.

            This defaults to the command's linked component.

        Returns
        -------
        hikari.api.special_endpoints.CommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
        """

    @abc.abstractmethod
    async def check_context(self, ctx: _AppCommandContextT, /) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self, ctx: _AppCommandContextT, /, *, hooks: collections.MutableSet[Hooks[_AppCommandContextT]] | None = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set_tracked_command(self, command: hikari.PartialCommand, /) -> Self:
        """Set the global command this tracks.

        Parameters
        ----------
        command
            Object of the global command this tracks.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """


class BaseSlashCommand(AppCommand[SlashContext], abc.ABC):
    """Base class for all slash command classes."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def parent(self) -> SlashCommandGroup | None:
        """Object of the group this command is in."""

    @property
    @abc.abstractmethod
    def tracked_command(self) -> hikari.SlashCommand | None:
        """Object of the actual command this object tracks if set."""

    @property
    @abc.abstractmethod
    def type(self) -> typing.Literal[hikari.CommandType.SLASH]:
        """The type of this command."""

    @abc.abstractmethod
    def build(self, *, component: Component | None = None) -> hikari.api.SlashCommandBuilder:
        """Get a builder object for this command.

        Parameters
        ----------
        component
            The component to inherit config like `default_member_permissions` and
            `is_dm_enabled` from if not explicitly set on the command.

            This defaults to the command's linked component.

        Returns
        -------
        hikari.api.special_endpoints.SlashCommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
        """

    @abc.abstractmethod
    def copy(self, *, parent: SlashCommandGroup | None = None) -> Self:
        """Create a copy of this command.

        Parameters
        ----------
        parent
            The parent of the copy.

        Returns
        -------
        Self
            The copy.
        """

    @abc.abstractmethod
    def set_parent(self, parent: SlashCommandGroup | None, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self,
        ctx: SlashContext,
        /,
        *,
        option: hikari.CommandInteractionOption | None = None,
        hooks: collections.MutableSet[SlashHooks] | None = None,
    ) -> None:
        raise NotImplementedError
        ...

    @abc.abstractmethod
    async def execute_autocomplete(
        self, ctx: AutocompleteContext, /, *, option: hikari.AutocompleteInteractionOption | None = None
    ) -> None: ...


class SlashCommand(BaseSlashCommand, abc.ABC, typing.Generic[_SlashCallbackSigT]):
    """A command that can be executed in a slash context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _SlashCallbackSigT:
        """Callback which is called during execution."""

    @property
    @abc.abstractmethod
    def float_autocompletes(self) -> collections.Mapping[str, AutocompleteSig[float]]:
        """Collection of the float option autocompletes."""

    @property
    @abc.abstractmethod
    def int_autocompletes(self) -> collections.Mapping[str, AutocompleteSig[int]]:
        """Collection of the integer option autocompletes."""

    @property
    @abc.abstractmethod
    def str_autocompletes(self) -> collections.Mapping[str, AutocompleteSig[str]]:
        """Collection of the string option autocompletes."""


class MenuCommand(AppCommand[MenuContext], typing.Generic[_MenuCallbackSigT, _MenuTypeT]):
    """A contextmenu command."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _MenuCallbackSigT:
        """Callback which is called during execution."""

    @property
    @abc.abstractmethod
    def type(self) -> _MenuTypeT:
        """The menu type(s) this is for."""

    @property
    @abc.abstractmethod
    def tracked_command(self) -> hikari.ContextMenuCommand | None:
        """Object of the actual command this object tracks if set."""

    @abc.abstractmethod
    def build(self, *, component: Component | None = None) -> hikari.api.ContextMenuCommandBuilder:
        """Get a builder object for this command.

        Parameters
        ----------
        component
            The component to inherit config like `default_member_permissions` and
            `is_dm_enabled` from if not explicitly set on the command.

            This defaults to the command's linked component.

        Returns
        -------
        hikari.api.special_endpoints.ContextMenuCommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
        """


class SlashCommandGroup(BaseSlashCommand, abc.ABC):
    """Standard interface of a slash command group.

    !!! note
        Unlike [MessageCommandGroup][tanjun.abc.MessageCommandGroup], slash
        command groups do not have their own callback.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def commands(self) -> collections.Collection[BaseSlashCommand]:
        """Collection of the commands in this group."""

    @abc.abstractmethod
    def add_command(self, command: BaseSlashCommand, /) -> Self:
        """Add a command to this group.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The command group instance to enable chained calls.
        """

    @abc.abstractmethod
    def remove_command(self, command: BaseSlashCommand, /) -> Self:
        """Remove a command from this group.

        Parameters
        ----------
        command
            The command to remove.

        Raises
        ------
        ValueError
            If the provided command isn't found.

        Returns
        -------
        Self
            The command group instance to enable chained calls.
        """

    @abc.abstractmethod
    def with_command(self, command: _BaseSlashCommandT, /) -> _BaseSlashCommandT:
        """Add a command to this group through a decorator call.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        BaseSlashCommand
            The added command.
        """


class MessageParser(abc.ABC):
    """Base class for a message parser."""

    __slots__ = ()

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self) -> Self:
        """Copy the parser.

        Returns
        -------
        Self
            A copy of the parser.
        """

    @abc.abstractmethod
    async def parse(self, ctx: MessageContext, /) -> dict[str, typing.Any]:
        """Parse a message context.

        !!! warning
            This relies on the prefix and command name(s) having been removed
            from [MessageContext.content][tanjun.abc.MessageContext.content].

        Parameters
        ----------
        ctx
            The message context to parse.

        Returns
        -------
        dict[str, typing.Any]
            Dictionary of argument names to the parsed values for them.

        Raises
        ------
        tanjun.errors.ParserError
            If the message could not be parsed.
        """

    @abc.abstractmethod
    def validate_arg_keys(self, callback_name: str, names: collections.Container[str], /) -> None:
        """Validate that callback's keyword arguments are all valid for this parser.

        Parameters
        ----------
        callback_name
            The callback's name for use in raised errors.
        names
            Key names of the callback's keyword arguments.

        Raises
        ------
        ValueError
            If any of the parameter keys aren't valid for this parser.
        """


class MessageCommand(ExecutableCommand[MessageContext], abc.ABC, typing.Generic[_MessageCallbackSigT]):
    """Standard interface of a message command."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _MessageCallbackSigT:
        """Callback which is called during execution.

        !!! note
            For command groups, this is called when none of the inner-commands
            matches the message.
        """

    @property
    @abc.abstractmethod
    def names(self) -> collections.Collection[str]:
        """Collection of this command's names."""

    @property
    @abc.abstractmethod
    def parent(self) -> MessageCommandGroup[typing.Any] | None:
        """Parent group of this command if applicable."""

    @property
    @abc.abstractmethod
    def parser(self) -> MessageParser | None:
        """Parser for this command."""

    @abc.abstractmethod
    def set_parent(self, parent: MessageCommandGroup[typing.Any] | None, /) -> Self:
        """Set the parent of this command.

        Parameters
        ----------
        parent
            The parent of this command.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """

    @abc.abstractmethod
    def set_parser(self, parser: MessageParser, /) -> Self:
        """Set the for this message command.

        Parameters
        ----------
        parser
            The parser to set.

        Returns
        -------
        Self
            The command instance to enable chained calls.

        Raises
        ------
        ValueError
            If this parser's option keys aren't valid for this command when
            `validate_arg_keys` is [True][].
        """

    @abc.abstractmethod
    def copy(self, *, parent: MessageCommandGroup[typing.Any] | None = None) -> Self:
        """Create a copy of this command.

        Parameters
        ----------
        parent
            The parent of the copy.

        Returns
        -------
        Self
            The copy.
        """

    @abc.abstractmethod
    async def check_context(self, ctx: MessageContext, /) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self, ctx: MessageContext, /, *, hooks: collections.MutableSet[Hooks[MessageContext]] | None = None
    ) -> None:
        raise NotImplementedError


class MessageCommandGroup(MessageCommand[_MessageCallbackSigT], abc.ABC):
    """Standard interface of a message command group."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def commands(self) -> collections.Collection[MessageCommand[typing.Any]]:
        """Collection of the commands in this group.

        !!! note
            This may include command groups.
        """

    @abc.abstractmethod
    def add_command(self, command: MessageCommand[typing.Any], /) -> Self:
        """Add a command to this group.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The group instance to enable chained calls.
        """

    @abc.abstractmethod
    def remove_command(self, command: MessageCommand[typing.Any], /) -> Self:
        """Remove a command from this group.

        Parameters
        ----------
        command
            The command to remove.

        Raises
        ------
        ValueError
            If the provided command isn't found.

        Returns
        -------
        Self
            The group instance to enable chained calls.
        """

    @abc.abstractmethod
    def with_command(self, command: _MessageCommandT, /) -> _MessageCommandT:
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

    This is a collection of message and application commands, and listeners
    with logic for command search + execution and loading the listeners
    into a tanjun client.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def client(self) -> Client | None:
        """Tanjun client this component is bound to."""

    @property
    @abc.abstractmethod
    def default_app_cmd_permissions(self) -> hikari.Permissions | None:
        """Default required guild member permissions for the commands in this component.

        This may be overridden by
        [AppCommand.default_member_permissions][tanjun.abc.AppCommand.default_member_permissions]
        and if this is [None][] then the default from the parent client is used.

        !!! warning
            This may be overridden by guild staff and does not apply to admins.
        """

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool | None:
        """Whether slash contexts executed in this component should default to ephemeral responses.

        This effects calls to
        [AppCommandContext.create_followup][tanjun.abc.AppCommandContext.create_followup],
        [AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response],
        [AppCommandContext.defer][tanjun.abc.AppCommandContext.defer] and
        [AppCommandContext.respond][tanjun.abc.Context.respond]
        unless the `flags` field is provided for the methods which support it.

        !!! note
            This may be overridden by
            [AppCommand.defaults_to_ephemeral][tanjun.abc.AppCommand.defaults_to_ephemeral]
            and only effects slash command execution; if this is [None][] then
            the default from the parent client is used.
        """

    @property
    @abc.abstractmethod
    def dms_enabled_for_app_cmds(self) -> bool | None:
        """Whether application commands in this component should be enabled in DMs.

        !!! note
            This may be overridden by
            [AppCommand.is_dm_enabled][tanjun.abc.AppCommand.is_dm_enabled]
            and if both that and this are [None][] then the default from the
            parent client is used.
        """

    @property
    @abc.abstractmethod
    def is_case_sensitive(self) -> bool | None:
        """Whether this component should treat message command names case sensitive in search.

        If this is `None` then the client's case sensitivity will be used.
        """

    @property
    @abc.abstractmethod
    def loop(self) -> asyncio.AbstractEventLoop | None:
        """The asyncio loop this client is bound to if it has been opened."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Component's unique identifier.

        !!! note
            This will be preserved between copies of a component.
        """

    @property
    @abc.abstractmethod
    def slash_commands(self) -> collections.Collection[BaseSlashCommand]:
        """Collection of the slash commands in this component."""

    @property
    @abc.abstractmethod
    def menu_commands(self) -> collections.Collection[MenuCommand[typing.Any, typing.Any]]:
        """Collection of the menu commands in this component."""

    @property
    @abc.abstractmethod
    def message_commands(self) -> collections.Collection[MessageCommand[typing.Any]]:
        """Collection of the message commands in this component."""

    @property
    @abc.abstractmethod
    def listeners(
        self,
    ) -> collections.Mapping[type[hikari.Event], collections.Collection[ListenerCallbackSig[typing.Any]]]:
        """Mapping of event types to the listeners registered for them in this component."""

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Mutable mapping of the metadata set for this component.

        !!! note
            Any modifications made to this mutable mapping will be preserved by
            the component.
        """

    @abc.abstractmethod
    def set_metadata(self, key: typing.Any, value: typing.Any, /) -> Self:
        """Set a field in the component's metadata.

        Parameters
        ----------
        key
            Metadata key to set.
        value
            Metadata value to set.

        Returns
        -------
        Self
            The component instance to enable chained calls.
        """

    @abc.abstractmethod
    def add_menu_command(self, command: MenuCommand[typing.Any, typing.Any], /) -> Self:
        """Add a menu command to this component.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_menu_command(self, command: MenuCommand[typing.Any, typing.Any], /) -> Self:
        """Remove a menu command from this component.

        Parameters
        ----------
        command
            Object of the menu command to remove.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @typing.overload
    @abc.abstractmethod
    def with_menu_command(self, command: _MenuCommandT, /) -> _MenuCommandT: ...

    @typing.overload
    @abc.abstractmethod
    def with_menu_command(self, /, *, copy: bool = False) -> collections.Callable[[_MenuCommandT], _MenuCommandT]: ...

    @abc.abstractmethod
    def with_menu_command(
        self, command: _MenuCommandT | None = None, /, *, copy: bool = False
    ) -> _MenuCommandT | collections.Callable[[_MenuCommandT], _MenuCommandT]:
        """Add a menu command to this component through a decorator call.

        Parameters
        ----------
        command : MenuCommand
            The command to add.
        copy
            Whether to copy the command before adding it.

        Returns
        -------
        MenuCommand
            The added command.
        """

    @abc.abstractmethod
    def add_slash_command(self, command: BaseSlashCommand, /) -> Self:
        """Add a slash command to this component.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_slash_command(self, command: BaseSlashCommand, /) -> Self:
        """Remove a slash command from this component.

        Parameters
        ----------
        command
            The command to remove.

        Raises
        ------
        ValueError
            If the provided command isn't found.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @typing.overload
    @abc.abstractmethod
    def with_slash_command(self, command: _BaseSlashCommandT, /) -> _BaseSlashCommandT: ...

    @typing.overload
    @abc.abstractmethod
    def with_slash_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_BaseSlashCommandT], _BaseSlashCommandT]: ...

    @abc.abstractmethod
    def with_slash_command(
        self, command: _BaseSlashCommandT | None = None, /, *, copy: bool = False
    ) -> _BaseSlashCommandT | collections.Callable[[_BaseSlashCommandT], _BaseSlashCommandT]:
        """Add a slash command to this component through a decorator call.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to add.
        copy
            Whether to copy the command before adding it.

        Returns
        -------
        BaseSlashCommand
            The added command.
        """

    @abc.abstractmethod
    def add_message_command(self, command: MessageCommand[typing.Any], /) -> Self:
        """Add a message command to this component.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_message_command(self, command: MessageCommand[typing.Any], /) -> Self:
        """Remove a message command from this component.

        Parameters
        ----------
        command
            The command to remove.

        Raises
        ------
        ValueError
            If the provided command isn't found.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @typing.overload
    @abc.abstractmethod
    def with_message_command(self, command: _MessageCommandT, /) -> _MessageCommandT: ...

    @typing.overload
    @abc.abstractmethod
    def with_message_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_MessageCommandT], _MessageCommandT]: ...

    @abc.abstractmethod
    def with_message_command(
        self, command: _MessageCommandT | None = None, /, *, copy: bool = False
    ) -> _MessageCommandT | collections.Callable[[_MessageCommandT], _MessageCommandT]:
        """Add a message command to this component through a decorator call.

        Parameters
        ----------
        command : MessageCommand
            The command to add.
        copy
            Whether to copy the command before adding it.

        Returns
        -------
        MessageCommand
            The added command.
        """

    @abc.abstractmethod
    def add_listener(self, event: type[_EventT], /, *callbacks: ListenerCallbackSig[_EventT]) -> Self:
        """Add a listener to this component.

        Parameters
        ----------
        event : type[hikari.events.base_events.Event]
            The event to listen for.
        *callbacks
            The callbacks to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_listener(self, event: type[_EventT], listener: ListenerCallbackSig[_EventT], /) -> Self:
        """Remove a listener from this component.

        Parameters
        ----------
        event : type[hikari.events.base_events.Event]
            The event to listen for.
        listener
            The listener to remove.

        Raises
        ------
        ValueError
            If the listener is not registered for the provided event.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def with_listener(
        self, *event_types: type[hikari.Event]
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT]:
        """Add a listener to this component through a decorator call.

        Parameters
        ----------
        *event_types
            One or more event types to listen for.

            If none are provided then the event type(s) will be inferred from
            the callback's type-hints.

        Returns
        -------
        collections.abc.Callable[[ListenerCallbackSig], ListenerCallbackSig]
            Decorator callback which takes listener to add.

        Raises
        ------
        ValueError
            If nothing was passed for `event_types` and no subclasses of
            [hikari.Event][hikari.events.base_events.Event] are found in the
            type-hint for the callback's first argument.
        """

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def unbind_client(self, client: Client, /) -> Self:
        raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(
        self, name: str, /, *, case_sensitive: bool = True
    ) -> collections.Iterator[tuple[str, MessageCommand[typing.Any]]]:
        """Check whether a name matches any of this component's registered message commands.

        !!! note
            This only checks for name matches against the top level command and
            will not account for sub-commands.

        !!! note
            Dependent on implementation detail this may partial check name against
            command names using name.startswith(command_name), hence why it
            also returns the name a command was matched by.

        Parameters
        ----------
        name
            The name to check for command matches.
        case_sensitive
            Whether to perform a case-sensitive match.

        Returns
        -------
        collections.abc.Iterator[tuple[str, MessageCommand[typing.Any]]]
            Iterator of tuples of command name matches to the relevant message
            command objects.
        """

    @abc.abstractmethod
    def check_slash_name(self, name: str, /) -> collections.Iterator[BaseSlashCommand]:
        """Check whether a name matches any of this component's registered slash commands.

        !!! note
            This won't check for sub-commands and will expect `name` to simply be
            the top level command name.

        Parameters
        ----------
        name
            The name to check for command matches.

        Returns
        -------
        collections.abc.Iterator[BaseSlashCommand]
            An iterator of the matching slash commands.
        """

    @abc.abstractmethod
    def execute_autocomplete(self, ctx: AutocompleteContext, /) -> _CoroT[None] | None:
        """Execute an autocomplete context.

        !!! note
            Unlike the other execute methods, this shouldn't be expected to
            raise [tanjun.HaltExecution][] nor [tanjun.CommandError][].

        Parameters
        ----------
        ctx
            The context to execute.

        Returns
        -------
        collections.abc.Coroutine[typing.Any, typing.Any, None] | None
            Coroutine used to wait for the command execution to finish.

            This may be awaited or left to run as a background task.

            If this is [None][] then the client should carry on its search for a
            component with a matching autocomplete.
        """

    @abc.abstractmethod
    async def execute_menu(
        self, ctx: MenuContext, /, *, hooks: collections.MutableSet[MenuHooks] | None = None
    ) -> _CoroT[None] | None:
        """Execute a menu context.

        Parameters
        ----------
        ctx
            The context to execute.
        hooks
            Set of hooks to include in this command execution.

        Returns
        -------
        collections.abc.Coroutine[typing.Any, typing.Any, None] | None
            Coroutine used to wait for the command execution to finish.

            This may be awaited or left to run as a background task.

            If this is [None][] then the client should carry on its search for a
            component with a matching command.

        Raises
        ------
        tanjun.errors.CommandError
            To end the command's execution with an error response message.
        tanjun.errors.HaltExecution
            To indicate that the client should stop searching for commands to
            execute with the current context.
        """

    @abc.abstractmethod
    async def execute_slash(
        self, ctx: SlashContext, /, *, hooks: collections.MutableSet[SlashHooks] | None = None
    ) -> _CoroT[None] | None:
        """Execute a slash context.

        Parameters
        ----------
        ctx
            The context to execute.
        hooks
            Set of hooks to include in this command execution.

        Returns
        -------
        collections.abc.Coroutine[typing.Any, typing.Any, None] | None
            Coroutine used to wait for the command execution to finish.

            This may be awaited or left to run as a background task.

            If this is [None][] then the client should carry on its search for a
            component with a matching command.

        Raises
        ------
        tanjun.errors.CommandError
            To end the command's execution with an error response message.
        tanjun.errors.HaltExecution
            To indicate that the client should stop searching for commands to
            execute with the current context.
        """

    @abc.abstractmethod
    async def execute_message(
        self, ctx: MessageContext, /, *, hooks: collections.MutableSet[MessageHooks] | None = None
    ) -> bool:
        """Execute a message context.

        Parameters
        ----------
        ctx
            The context to execute.
        hooks
            Set of hooks to include in this command execution.

        Returns
        -------
        bool
            Whether a message command was executed in this component with the
            provided context.

            If [False][] then the client should carry on its search for a
            component with a matching command.

        Raises
        ------
        tanjun.errors.CommandError
            To end the command's execution with an error response message.
        tanjun.errors.HaltExecution
            To indicate that the client should stop searching for commands to
            execute with the current context.
        """

    @abc.abstractmethod
    async def close(self, *, unbind: bool = False) -> None:
        """Close the component.

        Parameters
        ----------
        unbind
            Whether to unbind from the client after this is closed.

        Raises
        ------
        RuntimeError
            If the component isn't running.
        """

    @abc.abstractmethod
    async def open(self) -> None:
        """Start the component.

        Raises
        ------
        RuntimeError
            If the component is already open.
            If the component isn't bound to a client.
        """


class ClientCallbackNames(str, enum.Enum):
    """Enum of the standard client callback names.

    These should be dispatched by all [Client][tanjun.abc.Client] implementations.
    """

    CLOSED = "closed"
    """Called when the client has finished closing.

    No positional arguments are provided for this event.
    """

    CLOSING = "closing"
    """Called when the client is initially instructed to close.

    No positional arguments are provided for this event.
    """

    COMPONENT_ADDED = "component_added"
    """Called when a component is added to an active client.

    !!! warning
        This event isn't dispatched for components which were registered while
        the client is inactive.

    The first positional argument is the [Component][tanjun.abc.Component]
    being added.
    """

    COMPONENT_REMOVED = "component_removed"
    """Called when a component is added to an active client.

    !!! warning
        This event isn't dispatched for components which were removed while
        the client is inactive.

    The first positional argument is the [Component][tanjun.abc.Component]
    being removed.
    """

    MENU_COMMAND_NOT_FOUND = "menu_command_not_found"
    """Called when a menu command is not found.

    [MenuContext][tanjun.abc.MenuContext] is provided as the first positional
    argument.
    """

    MESSAGE_COMMAND_NOT_FOUND = "message_command_not_found"
    """Called when a message command is not found.

    [MessageContext][tanjun.abc.MessageContext] is provided as the first
    positional argument.
    """

    SLASH_COMMAND_NOT_FOUND = "slash_command_not_found"
    """Called when a slash command is not found.

    [SlashContext][tanjun.abc.SlashContext] is provided as the first positional
    argument.
    """

    STARTED = "started"
    """Called when the client has finished starting.

    No positional arguments are provided for this event.
    """

    STARTING = "starting"
    """Called when the client is initially instructed to start.

    No positional arguments are provided for this event.
    """


class Client(abc.ABC):
    """Abstract interface of a Tanjun client.

    This should manage both message and slash command execution based on the
    provided hikari clients.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def cache(self) -> hikari.api.Cache | None:
        """Hikari cache instance this command client was initialised with."""

    @property
    @abc.abstractmethod
    def components(self) -> collections.Collection[Component]:
        """Collection of the components this command client is using."""

    @property
    @abc.abstractmethod
    def default_app_cmd_permissions(self) -> hikari.Permissions:
        """Default required guild member permissions for the commands in this client.

        This may be overridden by
        [Component.default_app_cmd_permissions][tanjun.abc.Component.default_app_cmd_permissions] and
        [AppCommand.default_member_permissions][tanjun.abc.AppCommand.default_member_permissions];
        this defaults to no
        required permissions.

        !!! warning
            This may be overridden by guild staff and does not apply to admins.
        """

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        """Whether slash contexts spawned by this client should default to ephemeral responses.

        This effects calls to
        [AppCommandContext.create_followup][tanjun.abc.AppCommandContext.create_followup],
        [AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response],
        [AppCommandContext.defer][tanjun.abc.AppCommandContext.defer] and
        [AppCommandContext.respond][tanjun.abc.Context.respond]
        unless the `flags` field is provided for the methods which support it.

        This defaults to [False][].

        !!! note
            This may be overridden by
            [AppCommand.defaults_to_ephemeral][tanjun.abc.AppCommand.defaults_to_ephemeral]
            and [Component.defaults_to_ephemeral][tanjun.abc.Component.defaults_to_ephemeral]
            and only effects slash command execution.
        """

    @property
    @abc.abstractmethod
    def dms_enabled_for_app_cmds(self) -> bool:
        """Whether application commands in this client should be enabled in DMs by default.

        This defaults to [True][].

        !!! note
            This may be overridden by
            [AppCommand.is_dm_enabled][tanjun.abc.AppCommand.is_dm_enabled]
            and [Component.dms_enabled_for_app_cmds][tanjun.abc.Component.dms_enabled_for_app_cmds].
        """

    @property
    @abc.abstractmethod
    def events(self) -> hikari.api.EventManager | None:
        """Object of the event manager this client was initialised with.

        This is used for executing message commands if set.
        """

    @property
    @abc.abstractmethod
    def injector(self) -> alluka.Client:
        """The attached alluka dependency injection client."""

    @property
    @abc.abstractmethod
    def is_alive(self) -> bool:
        """Whether this client is alive."""

    @property
    @abc.abstractmethod
    def is_case_sensitive(self) -> bool:
        """Whether this client should treat message command names case sensitive in search."""

    @property  # TODO: switch over to a mapping of event to collection cause convenience
    @abc.abstractmethod
    def listeners(
        self,
    ) -> collections.Mapping[type[hikari.Event], collections.Collection[ListenerCallbackSig[typing.Any]]]:
        """Mapping of event types to the listeners registered in this client."""

    @property
    @abc.abstractmethod
    def loop(self) -> asyncio.AbstractEventLoop | None:
        """The loop this client is bound to if it's alive."""

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Mutable mapping of the metadata set for this client.

        !!! note
            Any modifications made to this mutable mapping will be preserved by
            the client.
        """

    @property
    @abc.abstractmethod
    def prefixes(self) -> collections.Collection[str]:
        """Collection of the prefixes set for this client.

        These are only use during message command execution to match commands
        to this command client.
        """

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this client was initialised with."""

    @property
    @abc.abstractmethod
    def server(self) -> hikari.api.InteractionServer | None:
        """Object of the Hikari interaction server provided for this client.

        This is used for executing application commands if set.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> hikari.ShardAware | None:
        """Object of the Hikari shard manager this client was initialised with."""

    @property
    @abc.abstractmethod
    def voice(self) -> hikari.api.VoiceComponent | None:
        """Object of the Hikari voice component this client was initialised with."""

    @abc.abstractmethod
    async def clear_application_commands(
        self,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> None:
        """Clear the commands declared either globally or for a specific guild.

        !!! note
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Parameters
        ----------
        application
            The application to clear commands for.

            If left as [None][] then this will be inferred from the authorization
            being used by [Client.rest][tanjun.abc.Client.rest].
        guild
            Object or ID of the guild to clear commands for.

            If left as [None][] global commands will be cleared.
        """

    @abc.abstractmethod
    async def declare_global_commands(
        self,
        command_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]] | None = None,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        message_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]] | None = None,
        user_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]] | None = None,
        force: bool = False,
    ) -> collections.Sequence[hikari.PartialCommand]:
        """Set the global application commands for a bot based on the loaded components.

        !!! warning
            This will overwrite any previously set application commands and
            only targets commands marked as global.

        !!! note
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Parameters
        ----------
        command_ids
            If provided, a mapping of top level command names to IDs of the
            existing commands to update.

            This will be used for all application commands but in cases where
            commands have overlapping names, `message_ids` and `user_ids` will
            take priority over this for their relevant command type.
        application
            Object or ID of the application to set the global commands for.

            If left as [None][] then this will be inferred from the authorization
            being used by [Client.rest][tanjun.abc.Client.rest].
        guild
            Object or ID of the guild to set the global commands to.

            If left as [None][] global commands will be set.
        message_ids
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        force
            Force this to declare the commands regardless of whether or not
            they match the current state of the declared commands.

            The default behaviour helps avoid issues with the 2 request per
            minute (per-guild or globally) ratelimit and the other limit of
            only 200 application command creates per day (per guild or globally).

        Returns
        -------
        collections.abc.Sequence[hikari.commands.PartialCommand]
            API representations of the set commands.
        """

    @typing.overload
    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: BaseSlashCommand,
        /,
        command_id: hikari.Snowflakeish | None = None,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.SlashCommand: ...

    @typing.overload
    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: MenuCommand[typing.Any, typing.Any],
        /,
        command_id: hikari.Snowflakeish | None = None,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.ContextMenuCommand: ...

    @typing.overload
    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: AppCommand[typing.Any],
        /,
        command_id: hikari.Snowflakeish | None = None,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand: ...

    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: AppCommand[typing.Any],
        /,
        command_id: hikari.Snowflakeish | None = None,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        """Declare a single slash command for a bot.

        !!! warning
            Providing `command_id` when updating a command helps avoid any
            permissions set for the command being lose (e.g. when changing the
            command's name).

        Parameters
        ----------
        command
            The command to register.
        application
            The application to register the command with.

            If left as [None][] then this will be inferred from the authorization
            being used by [Client.rest][tanjun.abc.Client.rest].
        command_id
            ID of the command to update.
        guild
            Object or ID of the guild to register the command with.

            If left as [None][] then the command will be registered globally.

        Returns
        -------
        hikari.commands.PartialCommand
            API representation of the command that was registered.
        """

    @abc.abstractmethod
    async def declare_application_commands(
        self,
        commands: collections.Iterable[AppCommand[typing.Any] | hikari.api.CommandBuilder],
        /,
        command_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]] | None = None,
        *,
        application: hikari.SnowflakeishOr[hikari.PartialApplication] | None = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        message_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]] | None = None,
        user_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]] | None = None,
        force: bool = False,
    ) -> collections.Sequence[hikari.PartialCommand]:
        """Declare a collection of slash commands for a bot.

        !!! note
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Parameters
        ----------
        commands
            Iterable of the commands objects or builders to register.
        command_ids
            If provided, a mapping of top level command names to IDs of the
            existing commands to update.

            This will be used for all application commands but in cases where
            commands have overlapping names, `message_ids` and `user_ids` will
            take priority over this for their relevant command type.

            While optional, this can be helpful when updating commands as
            providing the current IDs will prevent changes such as renames from
            leading to other state set for commands (e.g. permissions) from
            being lost.
        application
            The application to register the commands with.

            If left as [None][] then this will be inferred from the authorization
            being used by [Client.rest][tanjun.abc.Client.rest].
        guild
            Object or ID of the guild to register the commands with.

            If left as [None][] then the commands will be registered globally.
        message_ids
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        force
            Force this to declare the commands regardless of whether or not
            they match the current state of the declared commands.

            The default behaviour helps avoid issues with the 2 request per
            minute (per-guild or globally) ratelimit and the other limit of
            only 200 application command creates per day (per guild or globally).

        Returns
        -------
        collections.abc.Sequence[hikari.commands.PartialCommand]
            API representations of the commands which were registered.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If conflicting command names are found (multiple commanbds have the same top-level name).
            * If more than 100 top-level commands are passed.
        """

    @abc.abstractmethod
    def set_metadata(self, key: typing.Any, value: typing.Any, /) -> Self:
        """Set a field in the client's metadata.

        Parameters
        ----------
        key
            Metadata key to set.
        value
            Metadata value to set.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    def add_component(self, component: Component, /) -> Self:
        """Add a component to this client.

        Parameters
        ----------
        component
            The component to move to this client.

        Returns
        -------
        Self
            The client instance to allow chained calls.
        """

    @abc.abstractmethod
    def get_component_by_name(self, name: str, /) -> Component | None:
        """Get a component from this client by name.

        Parameters
        ----------
        name
            Name to get a component by.

        Returns
        -------
        Component | None
            The component instance if found, else [None][].
        """

    @abc.abstractmethod
    def remove_component(self, component: Component, /) -> Self:
        """Remove a component from this client.

        This will unsubscribe any client callbacks, commands and listeners
        registered in the provided component.

        Parameters
        ----------
        component
            The component to remove from this client.

        Raises
        ------
        ValueError
            If the provided component isn't found.

        Returns
        -------
        Self
            The client instance to allow chained calls.
        """

    @abc.abstractmethod
    def remove_component_by_name(self, name: str, /) -> Self:
        """Remove a component from this client by name.

        This will unsubscribe any client callbacks, commands and listeners
        registered in the provided component.

        Parameters
        ----------
        name
            Name of the component to remove from this client.

        Raises
        ------
        KeyError
            If the provided component name isn't found.
        """

    @abc.abstractmethod
    def add_client_callback(self, name: str | ClientCallbackNames, /, *callbacks: MetaEventSig) -> Self:
        """Add a client callback.

        Parameters
        ----------
        name
            The name this callback is being registered to.

            This is case-insensitive.
        *callbacks
            The callbacks to register.

            These may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    async def dispatch_client_callback(self, name: str | ClientCallbackNames, /, *args: typing.Any) -> None:
        """Dispatch a client callback.

        Parameters
        ----------
        name
            The name of the callback to dispatch.
        *args
            Positional arguments to pass to the callback(s).

        Raises
        ------
        KeyError
            If no callbacks are registered for the given name.
        """

    @abc.abstractmethod
    def get_client_callbacks(self, name: str | ClientCallbackNames, /) -> collections.Collection[MetaEventSig]:
        """Get a collection of the callbacks registered for a specific name.

        Parameters
        ----------
        name
            The name to get the callbacks registered for.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Collection[MetaEventSig]
            Collection of the callbacks for the provided name.
        """

    @abc.abstractmethod
    def remove_client_callback(self, name: str | ClientCallbackNames, callback: MetaEventSig, /) -> Self:
        """Remove a client callback.

        Parameters
        ----------
        name
            The name this callback is being registered to.

            This is case-insensitive.
        callback
            The callback to remove from the client's callbacks.

        Raises
        ------
        KeyError
            If the provided name isn't found.
        ValueError
            If the provided callback isn't found.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    def with_client_callback(
        self, name: str | ClientCallbackNames, /
    ) -> collections.Callable[[_MetaEventSigT], _MetaEventSigT]:
        """Add a client callback through a decorator call.

        Examples
        --------
        ```py
        client = tanjun.Client.from_rest_bot(bot)

        @client.with_client_callback("closed")
        async def on_close() -> None:
            raise NotImplementedError
        ```

        Parameters
        ----------
        name
            The name this callback is being registered to.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Callable[[MetaEventSig], MetaEventSig]
            Decorator callback used to register the client callback.

            This may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.
        """

    @abc.abstractmethod
    def add_listener(self, event_type: type[_EventT], /, *callbacks: ListenerCallbackSig[_EventT]) -> Self:
        """Add a listener to the client.

        Parameters
        ----------
        event_type : type[hikari.events.base_events.Event]
            The event type to add a listener for.
        *callbacks
            The callbacks to register as a listener.

            These callbacks must be coroutine functions which returns [None][]
            and always takes one positional arg of the event type passed for
            `event_type` regardless of client implementation detail.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    def remove_listener(self, event_type: type[_EventT], callback: ListenerCallbackSig[_EventT], /) -> Self:
        """Remove a listener from the client.

        Parameters
        ----------
        event_type : type[hikari.events.base_events.Event]
            The event type to remove a listener for.
        callback
            The callback to remove.

        Raises
        ------
        KeyError
            If the provided event type isn't found.
        ValueError
            If the provided callback isn't found.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    def with_listener(
        self, *event_types: type[hikari.Event]
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT]:
        """Add an event listener to this client through a decorator call.

        Examples
        --------
        ```py
        client = tanjun.Client.from_gateway_bot(bot)

        @client.with_listener(hikari.MessageCreateEvent)
        async def on_message_create(event: hikari.MessageCreateEvent) -> None:
            raise NotImplementedError
        ```

        Parameters
        ----------
        *event_types
            One or more event types to listen for.

            If none are provided then the event type(s) will be inferred from
            the callback's type-hints.

        Returns
        -------
        collections.abc.Callable[[ListenerCallbackSig], ListenerCallbackSig]
            Decorator callback used to register the event callback.

            The callback must be a coroutine function which returns [None][] and
            always takes at least one positional arg of type
            [hikari.Event][hikari.events.base_events.Event] regardless of
            client implementation detail.

        Raises
        ------
        ValueError
            If nothing was passed for `event_types` and no subclasses of
            [hikari.Event][hikari.events.base_events.Event] are found in the
            type-hint for the callback's first argument.
        """

    @abc.abstractmethod
    def iter_commands(self) -> collections.Iterator[ExecutableCommand[Context]]:
        """Iterate over all the commands (both message and slash) registered to this client.

        Returns
        -------
        collections.abc.Iterator[ExecutableCommand[Context]]
            Iterator of all the commands registered to this client.
        """

    @typing.overload
    @abc.abstractmethod
    def iter_menu_commands(
        self, *, global_only: bool = False, type: typing.Literal[hikari.CommandType.MESSAGE]
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Literal[hikari.CommandType.MESSAGE]]]: ...

    @typing.overload
    @abc.abstractmethod
    def iter_menu_commands(
        self, *, global_only: bool = False, type: typing.Literal[hikari.CommandType.USER]
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Literal[hikari.CommandType.USER]]]: ...

    @typing.overload
    @abc.abstractmethod
    def iter_menu_commands(
        self, *, global_only: bool = False, type: hikari.CommandType | None = None
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Any]]: ...

    @abc.abstractmethod
    def iter_menu_commands(
        self, *, global_only: bool = False, type: hikari.CommandType | None = None  # noqa: A002
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Any]]:
        """Iterate over the menu commands registered to this client.

        Parameters
        ----------
        global_only
            Whether to only iterate over global menu commands.
        type
            Menu command type to filter by.

        Returns
        -------
        collections.abc.Iterator[MenuCommand]
            Iterator of the menu commands registered to this client.
        """

    @abc.abstractmethod
    def iter_message_commands(self) -> collections.Iterator[MessageCommand[typing.Any]]:
        """Iterate over all the message commands registered to this client.

        Returns
        -------
        collections.abc.Iterator[MessageCommand]
            Iterator of all the message commands registered to this client.
        """

    @abc.abstractmethod
    def iter_slash_commands(self, *, global_only: bool = False) -> collections.Iterator[BaseSlashCommand]:
        """Iterate over all the slash commands registered to this client.

        Parameters
        ----------
        global_only
            Whether to only iterate over global slash commands.

        Returns
        -------
        collections.abc.Iterator[BaseSlashCommand]
            Iterator of the slash commands registered to this client.
        """

    @abc.abstractmethod
    def check_message_name(
        self, name: str, /, *, case_sensitive: bool = True
    ) -> collections.Iterator[tuple[str, MessageCommand[typing.Any]]]:
        """Check whether a message command name is present in the current client.

        !!! note
            Dependent on implementation this may partial check name against the
            message command's name based on command_name.startswith(name).

        Parameters
        ----------
        name
            The name to match commands against.
        case_sensitive
            Whether to match case sensitively.

        Returns
        -------
        collections.abc.Iterator[tuple[str, MessageCommand]]
            Iterator of the matched command names to the matched message command objects.
        """

    @abc.abstractmethod
    def check_slash_name(self, name: str, /) -> collections.Iterator[BaseSlashCommand]:
        """Check whether a slash command name is present in the current client.

        !!! note
            This won't check the commands within command groups.

        Parameters
        ----------
        name
            Name to check against.

        Returns
        -------
        collections.abc.Iterator[BaseSlashCommand]
            Iterator of the matched slash command objects.
        """

    @abc.abstractmethod
    def load_directory(self, directory: str | pathlib.Path, /, *, namespace: str | None = None) -> Self:
        r"""Load entities into this client from the modules in a directory.

        The same loading rules for [Client.load_modules][tanjun.abc.Client.load_modules]
        mostly apply here but modules with no loaders are quietly ignored.

        Parameters
        ----------
        directory
            Name of the directory to load modules from.
        namespace
            The python namespace this directory's modules should be imported
            from, if applicable.

            This work as `{namespace}.{file.name.removesuffix(".py")}` and will
            have the same behaviour as when a [str][] is passed to
            [Client.load_modules][tanjun.abc.Client.load_modules] if passed.

            If left as [None][] then this will have the same behaviour as when
            a [pathlib.Path][] is passed to
            [Client.load_modules][tanjun.abc.Client.load_modules].

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        tanjun.errors.FailedModuleLoad
            If any of the modules in this directory failed to load.

            This includes if it failed to import or if one of its loaders raised.
            The source error can be found at
            [FailedModuleLoad.\_\_cause\_\_][tanjun.errors.FailedModuleLoad.__cause__].

            Modules with no loaders are ignored.
        ModuleNotFoundError
            If any of the modules aren't found.
        """

    @abc.abstractmethod
    async def load_directory_async(self, directory: str | pathlib.Path, /, *, namespace: str | None = None) -> None:
        """Asynchronous variant of [Client.load_directory][tanjun.abc.Client.load_directory].

        Unlike [Client.load_directory][tanjun.abc.Client.load_directory], this
        method will run blocking code in a background thread.

        For more information on the behaviour of this method see the
        documentation for [Client.load_directory][tanjun.abc.Client.load_directory].
        """

    @abc.abstractmethod
    def load_modules(self, *modules: str | pathlib.Path) -> Self:
        r"""Load entities into this client from modules based on present loaders.

        !!! note
            If an `__all__` is present in the target module then it will be
            used to find loaders.

        Examples
        --------
        For this to work the target module has to have at least one loader present.

        ```py
        @tanjun.as_loader
        def load_module(client: tanjun.Client) -> None:
            client.add_component(component.copy())
        ```

        or

        ```py
        loader = tanjun.Component(name="trans component").load_from_scope().make_loader()
        ```

        Parameters
        ----------
        *modules
            Path(s) of the modules to load from.

            When [str][] this will be treated as a normal import path which is
            absolute (`"foo.bar.baz"`). It's worth noting that absolute module
            paths may be imported from the current location if the top level
            module is a valid module file or module directory in the current
            working directory.

            When [pathlib.Path][] the module will be imported directly from
            the given path. In this mode any relative imports in the target
            module will fail to resolve.

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        tanjun.errors.FailedModuleLoad
            If the new version of a module failed to load.

            This includes if it failed to import or if one of its loaders raised.
            The source error can be found at
            [FailedModuleLoad.\_\_cause\_\_][tanjun.errors.FailedModuleLoad.__cause__].
        tanjun.errors.ModuleStateConflict
            If the module is already loaded.
        tanjun.errors.ModuleMissingLoaders
            If no loaders are found in the module.
        ModuleNotFoundError
            If the module is not found.
        """

    @abc.abstractmethod
    async def load_modules_async(self, *modules: str | pathlib.Path) -> None:
        """Asynchronous variant of [Client.load_modules][tanjun.abc.Client.load_modules].

        Unlike [Client.load_modules][tanjun.abc.Client.load_modules], this
        method will run blocking code in a background thread.

        For more information on the behaviour of this method see the
        documentation for [Client.load_modules][tanjun.abc.Client.load_modules].
        """

    @abc.abstractmethod
    def unload_modules(self, *modules: str | pathlib.Path) -> Self:
        r"""Unload entities from this client based on unloaders in one or more modules.

        !!! note
            If an `__all__` is present in the target module then it will be
            used to find unloaders.

        Examples
        --------
        For this to work the module has to have at least one unloading enabled
        [ClientLoader][tanjun.abc.ClientLoader] present.

        ```py
        @tanjun.as_unloader
        def unload_component(client: tanjun.Client) -> None:
            client.remove_component_by_name(component.name)
        ```

        or

        ```py
        # make_loader's returned ClientLoader handles both loading and unloading.
        loader = tanjun.Component(name="trans component").load_from_scope().make_loader()
        ```

        Parameters
        ----------
        *modules
            Path of one or more modules to unload.

            These should be the same path(s) which were passed to
            [Client.load_modules][tanjun.abc.Client.load_modules].

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        tanjun.errors.ModuleStateConflict
            If the module hasn't been loaded.
        tanjun.errors.ModuleMissingUnloaders
            If no unloaders are found in the module.
        tanjun.errors.FailedModuleUnload
            If the old version of a module failed to unload.

            This indicates that one of its unloaders raised. The source error
            can be found at
            [FailedModuleUnload.\_\_cause\_\_][tanjun.errors.FailedModuleUnload.__cause__].
        """

    @abc.abstractmethod
    def reload_modules(self, *modules: str | pathlib.Path) -> Self:
        r"""Reload entities in this client based on the loaders in loaded module(s).

        !!! note
            If an `__all__` is present in the target module then it will be
            used to find loaders and unloaders.

        Examples
        --------
        For this to work the module has to have at least one ClientLoader
        which handles loading and one which handles unloading present.

        Parameters
        ----------
        *modules
            Paths of one or more module to unload.

            These should be the same paths which were passed to
            [Client.load_modules][tanjun.abc.Client.load_modules].

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        tanjun.errors.FailedModuleLoad
            If the new version of a module failed to load.

            This includes if it failed to import or if one of its loaders raised.
            The source error can be found at
            [FailedModuleLoad.\_\_cause\_\_][tanjun.errors.FailedModuleLoad.__cause__].
        tanjun.errors.FailedModuleUnload
            If the old version of a module failed to unload.

            This indicates that one of its unloaders raised. The source
            error can be found at
            [FailedModuleUnload.\_\_cause\_\_][tanjun.errors.FailedModuleUnload.__cause__].
        tanjun.errors.ModuleStateConflict
            If the module hasn't been loaded.
        tanjun.errors.ModuleMissingLoaders
            If no loaders are found in the new state of the module.
        tanjun.errors.ModuleMissingUnloaders
            If no unloaders are found in the current state of the module.
        ModuleNotFoundError
            If the module can no-longer be found at the provided path.
        """

    @abc.abstractmethod
    async def reload_modules_async(self, *modules: str | pathlib.Path) -> None:
        """Asynchronous variant of [Client.reload_modules][tanjun.abc.Client.reload_modules].

        Unlike [Client.reload_modules][tanjun.abc.Client.reload_modules], this
        method will run blocking code in a background thread.

        For more information on the behaviour of this method see the
        documentation for [Client.reload_modules][tanjun.abc.Client.reload_modules].
        """

    @abc.abstractmethod
    def set_type_dependency(self, type_: type[_T], value: _T, /) -> Self:
        """Set a callback to be called to resolve a injected type.

        Parameters
        ----------
        type_
            The type of the dependency to add an implementation for.
        value
            The value of the dependency.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> _T | _DefaultT: ...

    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT = ...) -> _T | _DefaultT:
        """Get the implementation for an injected type.

        Parameters
        ----------
        type_
            The associated type.
        default
            The default value to return if the type is not implemented.

        Returns
        -------
        _T | _DefaultT
            The resolved type if found.

            If the type isn't implemented then the value of `default`
            will be returned if it is provided.

        Raises
        ------
        KeyError
            If no dependency was found when no default was provided.
        """

    @abc.abstractmethod
    def remove_type_dependency(self, type_: type[typing.Any], /) -> Self:
        """Remove a type dependency.

        Parameters
        ----------
        type_
            The associated type.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        KeyError
            If `type` is not registered.
        """

    @abc.abstractmethod
    def set_callback_override(self, callback: alluka.CallbackSig[_T], override: alluka.CallbackSig[_T], /) -> Self:
        """Override a specific injected callback.

        Parameters
        ----------
        callback
            The injected callback to override.
        override
            The callback to use instead.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @abc.abstractmethod
    def get_callback_override(self, callback: alluka.CallbackSig[_T], /) -> alluka.CallbackSig[_T] | None:
        """Get the override for a specific injected callback.

        Parameters
        ----------
        callback
            The injected callback to get the override for.

        Returns
        -------
        alluka.abc.CallbackSig | None
            The override if found, else [None][].
        """

    @abc.abstractmethod
    def remove_callback_override(self, callback: alluka.CallbackSig[_T], /) -> Self:
        """Remove a callback override.

        Parameters
        ----------
        callback
            The injected callback to remove the override for.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        KeyError
            If no override is found for the callback.
        """


class ClientLoader(abc.ABC):
    """Interface of logic used to load and unload components into a generic client."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def has_load(self) -> bool:
        """Whether this loader will load anything."""

    @property
    @abc.abstractmethod
    def has_unload(self) -> bool:
        """Whether this loader will unload anything."""

    @abc.abstractmethod
    def load(self, client: Client, /) -> bool:
        """Load logic into a client instance.

        Parameters
        ----------
        client
            The client to load commands and listeners for.

        Returns
        -------
        bool
            Whether anything was loaded.
        """

    @abc.abstractmethod
    def unload(self, client: Client, /) -> bool:
        """Unload logic from a client instance.

        Parameters
        ----------
        client
            The client to unload commands and listeners from.

        Returns
        -------
        bool
            Whether anything was unloaded.
        """
