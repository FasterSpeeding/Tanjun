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
"""Interfaces of the objects and clients used within Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "AnyHooks",
    "AppCommand",
    "AppCommandContext",
    "AutocompleteCallbackSig",
    "AutocompleteContext",
    "AutocompleteOption",
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
    "MenuCommand",
    "MenuCommandCallbackSig",
    "MenuContext",
    "MenuHooks",
    "MessageCommand",
    "MessageCommandGroup",
    "MessageContext",
    "MessageHooks",
    "MetaEventSig",
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

    _AutocompleteValueT = typing.TypeVar("_AutocompleteValueT", int, str, float)
    _BaseSlashCommandT = typing.TypeVar("_BaseSlashCommandT", bound="BaseSlashCommand")
    _ClientT = typing.TypeVar("_ClientT", bound="Client")
    _ContextT = typing.TypeVar("_ContextT", bound="Context")
    _ErrorHookSigT = typing.TypeVar("_ErrorHookSigT", bound="ErrorHookSig")
    _HookSigT = typing.TypeVar("_HookSigT", bound="HookSig")
    _ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound="ListenerCallbackSig")
    _MenuCommandT = typing.TypeVar("_MenuCommandT", bound="MenuCommand[typing.Any, typing.Any]")
    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound="MessageCommand[typing.Any]")
    _MetaEventSigT = typing.TypeVar("_MetaEventSigT", bound="MetaEventSig")

_T = typing.TypeVar("_T")
_AppCommandContextT = typing.TypeVar("_AppCommandContextT", bound="AppCommandContext")
_CommandCallbackSigT = typing.TypeVar("_CommandCallbackSigT", bound="CommandCallbackSig")
_ContextT_co = typing.TypeVar("_ContextT_co", covariant=True, bound="Context")
_ContextT_contra = typing.TypeVar("_ContextT_contra", bound="Context", contravariant=True)
_CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
_MenuCommandCallbackSigT = typing.TypeVar("_MenuCommandCallbackSigT", bound="MenuCommandCallbackSig")
_MenuTypeT = typing.TypeVar(
    "_MenuTypeT", typing.Literal[hikari.CommandType.USER], typing.Literal[hikari.CommandType.MESSAGE]
)


AutocompleteCallbackSig = collections.Callable[..., collections.Awaitable[None]]
"""Type hint of the callback an autocomplete callback should have.

This will be called when handling autocomplete and should be an asynchronous
callback which two positional arguments of type `AutocompleteContext` and
`str | int | float` (with the 2nd argument type being decided by the
autocomplete type), returns `None` and may use dependency injection.
"""


CheckSig = typing.Union[collections.Callable[..., _CoroT[bool]], collections.Callable[..., bool]]
"""Type hint of a general context check used with Tanjun `ExecutableCommand` classes.

This may be registered with a `ExecutableCommand` to add a rule which decides whether
it should execute for each context passed to it. This should take one positional
argument of type `Context` and may either be a synchronous or asynchronous
callback which returns `bool` where returning `False` or
raising `tanjun.errors.FailedCheck` will indicate that the current context
shouldn't lead to an execution.
"""

CommandCallbackSig = collections.Callable[..., collections.Awaitable[None]]
"""Type hint of the callback a `Command` instance will operate on.

This will be called when executing a command and will need to take one
positional argument of type `Context` where any other required or optional
keyword arguments will be based on the parser instance for the command if
applicable and dependency injection.

.. note::
    This will have to be asynchronous.
"""


ErrorHookSig = typing.Union[
    collections.Callable[..., typing.Optional[bool]], collections.Callable[..., _CoroT[typing.Optional[bool]]]
]
"""Type hint of the callback used as a unexpected command error hook.

This will be called whenever an unexpected `Exception` is raised during the
execution stage of a command (not including expected `tanjun.errors.TanjunError`).

This should take two positional arguments - of type `tanjun.abc.Context` and
`Exception` - and may be either a synchronous or asynchronous callback which
returns `bool` or `None` and may take advantage of dependency injection.

`True` is returned to indicate that the exception should be suppressed and
`False` is returned to indicate that the exception should be re-raised.
"""


HookSig = typing.Union[collections.Callable[..., None], collections.Callable[..., _CoroT[None]]]
"""Type hint of the callback used as a general command hook.

.. note::
    This may be asynchronous or synchronous, dependency injection is supported
    for this callback's keyword arguments and the positional arguments which
    are passed dependent on the type of hook this is being registered as.
"""

ListenerCallbackSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]]
"""Type hint of a hikari event manager callback.

This is guaranteed one positional arg of type `hikari.Event` regardless
of implementation and must be a coruotine function which returns `None`.
"""

MenuCommandCallbackSig = collections.Callable[..., collections.Awaitable[None]]
"""Type hint of a context menu command callback.

This is guaranteed two positional; arguments of type `tanjun.abc.MenuContext`
and either `tanjun.abc.User` | `tanjun.abc.InteractionMember` and/or
`tanjun.abc.Message` dependent on the type(s) of menu this is.
"""

MetaEventSig = typing.Union[collections.Callable[..., _CoroT[None]], collections.Callable[..., None]]
"""Type hint of a client callback.

The positional arguments this is guaranteed depend on the event name its being
subscribed to (more information the standard client callbacks can be found at
`ClientCallbackNames`) and may be either synchronous or asynchronous but must
return `None`.
"""


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
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        """Hikari cache instance this context's command client was initialised with."""

    @property
    @abc.abstractmethod
    def client(self) -> Client:
        """Tanjun `Client` implementation this context was spawned by."""

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        """Object of the `Component` this context is bound to.

        .. note::
            This will only be `None` before this has been bound to a
            specific command but never during command execution nor checks.
        """

    @property  # TODO: can we somehow have this always be present on the command execution facing interface
    @abc.abstractmethod
    def command(self: _ContextT) -> typing.Optional[ExecutableCommand[_ContextT]]:
        """Object of the command this context is bound to.

        .. note::
            This will only be `None` before this has been bound to a
            specific command but never during command execution.
        """

    @property
    @abc.abstractmethod
    def created_at(self) -> datetime.datetime:
        """When this context was created."""

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        """Object of the event manager this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        """ID of the guild this command was executed in.

        Will be `None` for all DM command executions.
        """

    @property
    @abc.abstractmethod
    def has_responded(self) -> bool:
        """Whether an initial response has been made for this context."""

    @property
    @abc.abstractmethod
    def is_human(self) -> bool:
        """Whether this command execution was triggered by a human.

        Will be `False` for bot and webhook triggered commands.
        """

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[hikari.Member]:
        """Guild member object of this command's author.

        Will be `None` for DM command executions.
        """

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        """Object of the Hikari interaction server provided for this context's client."""

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        """Shard that triggered the context.

        .. note::
            This will be `None` if `ctx.shards` is also `None`.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[hikari.ShardAware]:
        """Object of the Hikari shard manager this context's client was initialised with."""

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
        """Object of the Hikari voice component this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        """Command name this execution was triggered with."""

    @abc.abstractmethod
    def set_component(self: _T, _: typing.Optional[Component], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_channel(self) -> hikari.TextableChannel:
        """Fetch the channel the context was invoked in.

        .. note::
            This performs an API call. Consider using `Context.get_channel`
            if you have `hikari.config.CacheComponents.GUILD_CHANNELS` cache component enabled.

        Returns
        -------
        hikari.TextableChannel
            The textable DM or guild channel the context was invoked in.

        Raises
        ------
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.ForbiddenError
            If you are missing the `READ_MESSAGES` permission in the channel.
        hikari.NotFoundError
            If the channel is not found.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:
        """Fetch the guild the context was invoked in.

        .. note::
            This performs an API call. Consider using `Context.get_guild`
            if you have `hikari.config.CacheComponents.GUILDS` cache component enabled.

        Returns
        -------
        hikari.Guild | None
            An optional guild the context was invoked in.
            `None` will be returned if the context was invoked in a DM channel.

        Raises
        ------
        hikari.ForbiddenError
            If you are not part of the guild.
        hikari.NotFoundError
            If the guild is not found.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    def get_channel(self) -> typing.Optional[hikari.TextableGuildChannel]:
        """Retrieve the channel the context was invoked in from the cache.

        .. note::
            This method requires the `hikari.config.CacheComponents.GUILD_CHANNELS` cache component.

        Returns
        -------
        hikari.TextableGuildChannel | None
            An optional guild channel the context was invoked in.
            `None` will be returned if the channel was not found or if it
            is DM channel.
        """

    @abc.abstractmethod
    def get_guild(self) -> typing.Optional[hikari.Guild]:
        """Fetch the guild that the context was invoked in.

        .. note::
            This method requires `hikari.config.CacheComponents.GUILDS` cache component enabled.

        Returns
        -------
        hikari.Guild | None
            An optional guild the context was invoked in.
            `None` will be returned if the guild was not found.
        """

    @abc.abstractmethod
    async def delete_initial_response(self) -> None:
        """Delete the initial response after invoking this context.

        Raises
        ------
        LookupError, hikari.NotFoundError
            The last context has no initial response.
        """

    @abc.abstractmethod
    async def delete_last_response(self) -> None:
        """Delete the last response after invoking this context.

        Raises
        ------
        LookupError, hikari.NotFoundError
            The last context has no responses.
        """

    @abc.abstractmethod
    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Edit the initial response for this context.

        Parameters
        ----------
        content : typing.Any | hikari.UNDEFINED
            The content to edit the initial response with.

            If provided, the message contents. If
            `hikari.UNDEFINED`, then nothing will be sent
            in the content. Any other value here will be cast to a
            `str`.

            If this is a `hikari.Embed` and no `embed` nor `embeds` kwarg
            is provided, then this will instead update the embed. This allows
            for simpler syntax when sending an embed alone.

            Likewise, if this is a `hikari.Resource`, then the
            content is instead treated as an attachment if no `attachment` and
            no `attachments` kwargs are provided.

        Other Parameters
        ----------------
        delete_after : datetime.timedelta | float | int | None
            If provided, the seconds after which the response message should be deleted.

            .. note::
                Slash command responses can only be deleted within 14 minutes of the
                command being received.

            .. note::
                Since (as of writing) ephemeral responses cannot be deleted by the bot,
                this is ignored for ephemeral slash command responses.
        attachment : hikari.Resourceish | hikari.UNDEFINED
            A singular attachment to edit the initial response with.
        attachments : collections.abc.Sequence[hikari.Resourceish] | hikari.UNDEFINED
            A sequence of attachments to edit the initial response with.
        component : hikari.UndefinedNoneOr[hikari.api.ComponentBuilder]
            If provided, builder object of the component to set for this message.
            This component will replace any previously set components and passing
            `None` will remove all components.
        components : hikari.UndefinedNoneOr[collections.abc.Sequence[hikari.api.ComponentBuilder]]
            If provided, a sequence of the component builder objects set for
            this message. These components will replace any previously set
            components and passing `None` or an empty sequence will
            remove all components.
        embed : hikari.Embed | hikari.UNDEFINED
            An embed to replace the initial response with.
        embeds : collections.abc.Sequence[hikari.Embed] | hikari.UNDEFINED
            A sequence of embeds to replace the initial response with.
        replace_attachments : bool
            Whether to replace the attachments of the response or not. Default to `False`.
        mentions_everyone : bool | hikari.UNDEFINED
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions : hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.
            Alternatively this may be a collection of
            `hikari.Snowflake`, or `hikari.PartialUser`
            derivatives to enforce mentioning specific users.
        role_mentions : hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.
            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialRole` derivatives to enforce mentioning
            specific roles.

        Notes
        -----
        Attachments can be passed as many different things, to aid in
        convenience.
        * If a `pathlib.PurePath` or `str` to a valid URL, the
            resource at the given URL will be streamed to Discord when
            sending the message. Subclasses of
            `hikari.WebResource` such as
            `hikari.URL`,
            `hikari.Attachment`,
            `hikari.Emoji`,
            `EmbedResource`, etc will also be uploaded this way.
            This will use bit-inception, so only a small percentage of the
            resource will remain in memory at any one time, thus aiding in
            scalability.
        * If a `hikari.Bytes` is passed, or a `str`
            that contains a valid data URI is passed, then this is uploaded
            with a randomized file name if not provided.
        * If a `hikari.File`, `pathlib.PurePath` or
            `str` that is an absolute or relative path to a file
            on your file system is passed, then this resource is uploaded
            as an attachment using non-blocking code internally and streamed
            using bit-inception where possible. This depends on the
            type of `concurrent.futures.Executor` that is being used for
            the application (default is a thread pool which supports this
            behaviour).

        Returns
        -------
        hikari.Message
            The message that has been edited.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.
            If `delete_after` would be more than 14 minutes after the slash
            command was called.
        TypeError
            If both `attachment` and `attachments` are specified.
        hikari.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; too many components.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.NotFoundError
            If the channel is not found.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Edit the last response for this context.

        Parameters
        ----------
        content : typing.Any | hikari.UNDEFINED
            The content to edit the last response with.

            If provided, the message contents. If
            `hikari.UNDEFINED`, then nothing will be sent
            in the content. Any other value here will be cast to a
            `str`.

            If this is a `hikari.Embed` and no `embed` nor `embeds` kwarg
            is provided, then this will instead update the embed. This allows
            for simpler syntax when sending an embed alone.

            Likewise, if this is a `hikari.Resource`, then the
            content is instead treated as an attachment if no `attachment` and
            no `attachments` kwargs are provided.

        Other Parameters
        ----------------
        delete_after : datetime.timedelta | float | int | None
            If provided, the seconds after which the response message should be deleted.

            .. note::
                Slash command responses can only be deleted within 14 minutes of the
                command being received.

            .. note::
                Since (as of writing) ephemeral responses cannot be deleted by the bot,
                this is ignored for ephemeral slash command responses.
        attachment : hikari.Resourceish | hikari.UNDEFINED
            A singular attachment to edit the last response with.
        attachments : collections.abc.Sequence[hikari.Resourceish] | hikari.UNDEFINED
            A sequence of attachments to edit the last response with.
        component : hikari.UndefinedNoneOr[hikari.api.ComponentBuilder]
            If provided, builder object of the component to set for this message.
            This component will replace any previously set components and passing
            `None` will remove all components.
        components : hikari.UndefinedNoneOr[collections.abc.Sequence[hikari.api.ComponentBuilder]]
            If provided, a sequence of the component builder objects set for
            this message. These components will replace any previously set
            components and passing `None` or an empty sequence will
            remove all components.
        embed : hikari.Embed | hikari.UNDEFINED
            An embed to replace the last response with.
        embeds : collections.abc.Sequence[hikari.Embed] | hikari.UNDEFINED
            A sequence of embeds to replace the last response with.
        replace_attachments : bool
            Whether to replace the attachments of the response or not. Default to `False`.
        mentions_everyone : bool | hikari.UNDEFINED
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions : hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or `hikari.PartialUser`
            derivatives to enforce mentioning specific users.
        role_mentions : hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialRole` derivatives to enforce mentioning
            specific roles.

        Notes
        -----
        Attachments can be passed as many different things, to aid in
        convenience.
        * If a `pathlib.PurePath` or `str` to a valid URL, the
            resource at the given URL will be streamed to Discord when
            sending the message. Subclasses of
            `hikari.WebResource` such as
            `hikari.URL`,
            `hikari.Attachment`,
            `hikari.Emoji`,
            `EmbedResource`, etc will also be uploaded this way.
            This will use bit-inception, so only a small percentage of the
            resource will remain in memory at any one time, thus aiding in
            scalability.
        * If a `hikari.Bytes` is passed, or a `str`
            that contains a valid data URI is passed, then this is uploaded
            with a randomized file name if not provided.
        * If a `hikari.File`, `pathlib.PurePath` or
            `str` that is an absolute or relative path to a file
            on your file system is passed, then this resource is uploaded
            as an attachment using non-blocking code internally and streamed
            using bit-inception where possible. This depends on the
            type of `concurrent.futures.Executor` that is being used for
            the application (default is a thread pool which supports this
            behaviour).

        Returns
        -------
        hikari.Message
            The message that has been edited.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.
            If `delete_after` would be more than 14 minutes after the slash
            command was called.
        TypeError
            If both `attachment` and `attachments` are specified.
        hikari.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; too many components.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.NotFoundError
            If the channel is not found.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def fetch_initial_response(self) -> hikari.Message:
        """Fetch the initial response for this context.

        Raises
        ------
        LookupError, hikari.NotFoundError
            The response was not found.
        """

    @abc.abstractmethod
    async def fetch_last_response(self) -> hikari.Message:
        """Fetch the last response for this context.

        Raises
        ------
        LookupError, hikari.NotFoundError
            The response was not found.
        """

    @typing.overload
    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[False] = False,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
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
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        ...

    @abc.abstractmethod
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> typing.Optional[hikari.Message]:
        """Respond to this context.

        Parameters
        ----------
        content : typing.Any | hikari.UNDEFINED
            The content to respond with.

            If provided, the message contents. If
            `hikari.UNDEFINED`, then nothing will be sent
            in the content. Any other value here will be cast to a
            `str`.

            If this is a `hikari.Embed` and no `embed` nor `embeds` kwarg
            is provided, then this will instead update the embed. This allows
            for simpler syntax when sending an embed alone.

            Likewise, if this is a `hikari.Resource`, then the
            content is instead treated as an attachment if no `attachment` and
            no `attachments` kwargs are provided.

        Other Parameters
        ----------------
        ensure_result : bool
            Ensure that this call will always return a message object.

            If `True` then this will always return `hikari.Message`, otherwise
            this will return `Optional[hikari.Message]`.

            It's worth noting that, under certain scenarios within the slash
            command flow, this may lead to an extre request being made.
        delete_after : datetime.timedelta | float | int | None
            If provided, the seconds after which the response message should be deleted.

            .. note::
                Slash command responses can only be deleted within 14 minutes of the
                command being received.

            .. note::
                Since (as of writing) ephemeral responses cannot be deleted by the bot,
                this is ignored for ephemeral slash command responses.
        component : hikari.api.ComponentBuilder | hikari.UNDEFINED
            If provided, builder object of the component to include in this response.
        components : collections.abc.Sequence[hikari.api.ComponentBuilder] | hikari.UNDEFINED
            If provided, a sequence of the component builder objects to include
            in this response.
        embed : hikari.Embed | hikari.UNDEFINED
            An embed to respond with.
        embeds : collections.abc.Sequence[hikari.Embed] | hikari.UNDEFINED
            A sequence of embeds to respond with.
        mentions_everyone : bool | hikari.UNDEFINED
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions : hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or `hikari.PartialUser`
            derivatives to enforce mentioning specific users.
        role_mentions : hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialRole` derivatives to enforce mentioning
            specific roles.

        Returns
        -------
        hikari.Message | None
            The message that has been created if it was immedieatly available or
            `ensure_result` was set to `True`, else `None`.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.
            If `delete_after` would be more than 14 minutes after the slash
            command was called.
        TypeError
            If both `attachment` and `attachments` are specified.
        hikari.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; too many components.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.NotFoundError
            If the channel is not found.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """


class MessageContext(Context, abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> typing.Optional[MessageCommand[typing.Any]]:
        """Command that was invoked.

        .. note::
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

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        """Command name that triggered the context."""

    @abc.abstractmethod
    def set_command(self: _T, _: typing.Optional[MessageCommand[typing.Any]], /) -> _T:
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
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        nonce: hikari.UndefinedOr[str] = hikari.UNDEFINED,
        reply: typing.Union[bool, hikari.SnowflakeishOr[hikari.PartialMessage], hikari.UndefinedType] = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Respond to this context.

        Parameters
        ----------
        content : typing.Any | hikari.UNDEFINED
            The content to respond with.

            If provided, the message contents. If
            `hikari.UNDEFINED`, then nothing will be sent
            in the content. Any other value here will be cast to a
            `str`.

            If this is a `hikari.Embed` and no `embed` nor `embeds` kwarg
            is provided, then this will instead update the embed. This allows
            for simpler syntax when sending an embed alone.

            Likewise, if this is a `hikari.Resource`, then the
            content is instead treated as an attachment if no `attachment` and
            no `attachments` kwargs are provided.

        Other Parameters
        ----------------
        ensure_result : bool
            Ensure this method call will return a message object.

            This does nothing for message command contexts as the result w ill
            always be immedieatly available.
        delete_after : datetime.timedelta | float | int | None
            If provided, the seconds after which the response message should be deleted.
        tts : bool | hikari.UNDEFINED
            Whether to respond with tts/text to speech or no.
        reply : bool | hikari.Snowflakeish | hikari.PartialMessage | hikari.UNDEFINED
            Whether to reply instead of sending the content to the context.

            Defaults to `hikari.UNDEFINED`.
            Passing `True` here indicates a reply to `MessageContext.message`.
        nonce : str | hikari.UNDEFINED
            The nonce that validates that the message was sent.
        attachment : hikari.Resourceish | hikari.UNDEFINED
            A singular attachment to respond with.
        attachments : collections.abc.Sequence[hikari.Resourceish] | hikari.UNDEFINED
            A sequence of attachments to respond with.
        component : hikari.api.ComponentBuilder | hikari.UNDEFINED
            If provided, builder object of the component to include in this message.
        components : collections.abc.Sequence[hikari.api.ComponentBuilder] | hikari.UNDEFINED
            If provided, a sequence of the component builder objects to include
            in this message.
        embed : hikari.Embed | hikari.UNDEFINED
            An embed to respond with.
        embeds : collections.abc.Sequence[hikari.Embed] | hikari.UNDEFINED
            A sequence of embeds to respond with.
        mentions_everyone : bool | hikari.UNDEFINED
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions : hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or `hikari.PartialUser`
            derivatives to enforce mentioning specific users.
        role_mentions : hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.
            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialRole` derivatives to enforce mentioning
            specific roles.

        Notes
        -----
        Attachments can be passed as many different things, to aid in
        convenience.
        * If a `pathlib.PurePath` or `str` to a valid URL, the
            resource at the given URL will be streamed to Discord when
            sending the message. Subclasses of
            `hikari.WebResource` such as
            `hikari.URL`,
            `hikari.Attachment`,
            `hikari.Emoji`,
            `EmbedResource`, etc will also be uploaded this way.
            This will use bit-inception, so only a small percentage of the
            resource will remain in memory at any one time, thus aiding in
            scalability.
        * If a `hikari.Bytes` is passed, or a `str`
            that contains a valid data URI is passed, then this is uploaded
            with a randomized file name if not provided.
        * If a `hikari.File`, `pathlib.PurePath` or
            `str` that is an absolute or relative path to a file
            on your file system is passed, then this resource is uploaded
            as an attachment using non-blocking code internally and streamed
            using bit-inception where possible. This depends on the
            type of `concurrent.futures.Executor` that is being used for
            the application (default is a thread pool which supports this
            behaviour).

        Returns
        -------
        hikari.Message
            The message that has been created.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If the interaction will have expired before `delete_after` is reached.
        TypeError
            If both `attachment` and `attachments` are specified.
        hikari.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no attachments or embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; too many attachments; attachments that are too large;
            invalid image URLs in embeds; if `reply` is not found or not in the
            same channel as `channel`; too many components.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.ForbiddenError
            If you are missing the `SEND_MESSAGES` in the channel or the
            person you are trying to message has the DM's disabled.
        hikari.NotFoundError
            If the channel is not found.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
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
    def type(self) -> typing.Union[hikari.OptionType, int]:
        """Type of this option."""

    @property
    @abc.abstractmethod
    def value(self) -> typing.Union[str, hikari.Snowflake, int, bool, float]:
        """Value provided for this option.

        .. note::
            For discord entity option types (user, member, channel and role)
            this will be the entity's ID.
        """

    @abc.abstractmethod
    def boolean(self) -> bool:
        """Get the boolean value of this option.

        Raises
        ------
        TypeError
            If `SlashOption.type` is not BOOLEAN.
        """

    @abc.abstractmethod
    def float(self) -> float:
        """Get the float value of this option.

        Raises
        ------
        TypeError
            If `SlashOption.type` is not FLOAT.
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
            If `SlashOption.type` is not INTEGER.
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
            If `SlashOption.type` is not one of CHANNEL, MENTIONABLE, ROLE
            or USER.
        """

    @abc.abstractmethod
    def string(self) -> str:
        """Get the string value of this option.

        Raises
        ------
        TypeError
            If `SlashOption.type` is not STRING.
        """

    @abc.abstractmethod
    def resolve_value(
        self,
    ) -> typing.Union[hikari.Attachment, hikari.InteractionChannel, hikari.InteractionMember, hikari.Role, hikari.User]:
        """Resolve this option to an object value.

        Returns
        -------
        hikari.Attachment | hikari.InteractionChannel | hikari.InteractionMember | hikari.Role | hikari.User
            The object value of this option.

        Raises
        ------
        TypeError
            If the option isn't resolvable.
        """

    @abc.abstractmethod
    def resolve_to_attachment(self) -> hikari.Attachment:
        """Resolve this option to a channel object.

        Returns
        -------
        hikari.Attachment
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
        hikari.InteractionChannel
            The channel object.

        Raises
        ------
        TypeError
            If the option is not a channel.
        """

    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T = ...) -> typing.Union[hikari.InteractionMember, _T]:
        """Resolve this option to a member object.

        Other Parameters
        ----------------
        default:
            The default value to return if this option cannot be resolved.

            If this is not provided, this method will raise a `TypeError` if
            this option cannot be resolved.

        Returns
        -------
        hikari.InteractionMember | _T
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
    def resolve_to_mentionable(self) -> typing.Union[hikari.Role, hikari.User, hikari.Member]:
        """Resolve this option to a mentionable object.

        Returns
        -------
        hikari.Role | hikari.User | hikari.Member
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
        hikari.Role
            The role object.

        Raises
        ------
        TypeError
            If the option is not a role.

            This includes mentionable options which point towards a user.
        """

    @abc.abstractmethod
    def resolve_to_user(self) -> typing.Union[hikari.User, hikari.Member]:
        """Resolve this option to a user object.

        .. note::
            This will resolve to a `hikari.Member` first if the relevant
            command was executed within a guild and the option targeted one of
            the guild's members, otherwise it will resolve to `hikari.User`.

            It's also worth noting that hikari.Member inherits from hikari.User
            meaning that the return value of this can always be treated as a
            user.

        Returns
        -------
        hikari.User | hikari.Member
            The user object.

        Raises
        ------
        TypeError
            If the option is not a user.

            This includes mentionable options which point towards a role.
        """


class AutocompleteOption(SlashOption, abc.ABC):
    """Interface for an auto-complete option."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def is_focused(self) -> bool:
        """Whether this is the option being autocompleted."""


class AppCommandContext(Context, abc.ABC):
    """Base class for application command contexts."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        """Whether the context is marked as defaulting to ephemeral response.

        This effects calls to `SlashContext.create_followup`,
        `SlashContext.create_initial_response`, `SlashContext.defer` and
        `SlashContext.respond` unless the `flags` field is provided for the
        methods which support it.
        """

    @property
    @abc.abstractmethod
    def expires_at(self) -> datetime.datetime:
        """When this application command context expires.

        After this time is reached, the message/response methods on this
        context will always raise `hikari.errors.NotFoundError`.
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
        """

    @property
    @abc.abstractmethod
    def interaction(self) -> hikari.CommandInteraction:
        """Interaction this context is for."""

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[hikari.InteractionMember]:
        """Object of the member that triggered this command if this is in a guild."""

    @property
    @abc.abstractmethod
    def type(self) -> hikari.CommandType:
        """Type of application command this context is for."""

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
        self,
        *,
        ephemeral: bool = False,
        flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED,
    ) -> None:
        """Defer the initial response for this context.

        .. note::
            The ephemeral state of the first response is decided by whether the
            deferral is ephemeral.

        Other Parameters
        ----------------
        ephemeral : bool
            Whether the deferred response should be ephemeral.

            Passing `True` here is a shorthand for including `1 << 64` in the
            passed flags.
        flags : hikari.UNDEFINED | int | hikari.MessageFlag
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
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        ephemeral: bool = False,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED,
    ) -> hikari.Message:
        """Create a followup response for this context.

        .. warning::
            Calling this on a context which hasn't had an initial response yet
            will lead to a `hikari.NotFoundError` being raised.

        Parameters
        ----------
        content : typing.Any | hikari.UNDEFINED
            If provided, the message contents. If
            `hikari.UNDEFINED`, then nothing will be sent
            in the content. Any other value here will be cast to a
            `str`.

            If this is a `hikari.Embed` and no `embed` kwarg is
            provided, then this will instead update the embed. This allows for
            simpler syntax when sending an embed alone.

            Likewise, if this is a `hikari.Resource`, then the
            content is instead treated as an attachment if no `attachment` and
            no `attachments` kwargs are provided.

        Other Parameters
        ----------------
        delete_after : datetime.timedelta | float | int | None
            If provided, the seconds after which the response message should be deleted.

            .. note::
                Slash command responses can only be deleted within 14 minutes of the
                command being received.

            .. note::
                Since (as of writing) ephemeral responses cannot be deleted by the bot,
                this is ignored for ephemeral slash command responses.
        ephemeral : bool
            Whether the deferred response should be ephemeral.

            Passing `True` here is a shorthand for including `1 << 64` in the
            passed flags.
        attachment : hikari.Resourceish | hikari.UNDEFINED
            If provided, the message attachment. This can be a resource,
            or string of a path on your computer or a URL.
        attachments : collections.abc.Sequence[hikari.Resourceish] | hikari.UNDEFINED
            If provided, the message attachments. These can be resources, or
            strings consisting of paths on your computer or URLs.
        component : hikari.api.ComponentBuilder | hikari.UNDEFINED
            If provided, builder object of the component to include in this message.
        components : collections.abc.Sequence[hikari.api.ComponentBuilder] | hikari.UNDEFINED
            If provided, a sequence of the component builder objects to include
            in this message.
        embed : hikari.Embed | hikari.UNDEFINED
            If provided, the message embed.
        embeds : collections.abc.Sequence[hikari.Embed] | hikari.UNDEFINED
            If provided, the message embeds.
        mentions_everyone : bool | hikari.UNDEFINED
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions : hikari.SnowflakeishSequence[hikari.PartialUser] | bool] | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialUser` derivatives to enforce mentioning
            specific users.
        role_mentions : hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UNDEFINED
            If provided, and `True`, all mentions will be parsed.
            If provided, and `False`, no mentions will be parsed.
            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialRole` derivatives to enforce mentioning
            specific roles.
        tts : bool | hikari.UNDEFINED
            If provided, whether the message will be sent as a TTS message.
        flags : hikari.UNDEFINED | int | hikari.MessageFlag
            The flags to set for this response.

            As of writing this can only flag which can be provided is EPHEMERAL,
            other flags are just ignored.

        Returns
        -------
        hikari.Message
            The created message object.

        Raises
        ------
        hikari.NotFoundError
            If the current interaction is not found or it hasn't had an initial
            response yet.
        hikari.BadRequestError
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
        TypeError
            If both `attachment` and `attachments` are specified.
        """

    @abc.abstractmethod
    async def create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        ephemeral: bool = False,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        flags: typing.Union[int, hikari.MessageFlag, hikari.UndefinedType] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        """Create the initial response for this context.

        .. warning::
            Calling this on a context which already has an initial
            response will result in this raising a `hikari.NotFoundError`.
            This includes if the REST interaction server has already responded
            to the request and deferrals.

        Other Parameters
        ----------------
        delete_after : datetime.timedelta | float | int | None
            If provided, the seconds after which the response message should be deleted.

            .. note::
                Slash command responses can only be deleted within 14 minutes of the
                command being received.

            .. note::
                Since (as of writing) ephemeral responses cannot be deleted by the bot,
                this is ignored for ephemeral slash command responses.
        ephemeral : bool
            Whether the deferred response should be ephemeral.

            Passing `True` here is a shorthand for including `1 << 64` in the
            passed flags.
        content : typing.Any | hikari.UNDEFINED
            If provided, the message contents. If
            `hikari.UNDEFINED`, then nothing will be sent
            in the content. Any other value here will be cast to a
            `str`.

            If this is a `hikari.Embed` and no `embed` nor `embeds` kwarg
            is provided, then this will instead update the embed. This allows
            for simpler syntax when sending an embed alone.
        component : hikari.api.ComponentBuilder | hikari.UNDEFINED
            If provided, builder object of the component to include in this message.
        components : collections.abc.Sequence[hikari.api.ComponentBuilder] | hikari.UNDEFINED
            If provided, a sequence of the component builder objects to include
            in this message.
        embed : hikari.Embed | hikari.UNDEFINED
            If provided, the message embed.
        embeds : collections.abc.Sequence[hikari.Embed] | hikari.UNDEFINED
            If provided, the message embeds.
        flags : int | hikari.MessageFlag | hikari.UNDEFINED
            If provided, the message flags this response should have.

            As of writing the only message flag which can be set here is
            `hikari.MessageFlag.EPHEMERAL`.
        tts : bool | hikari.UNDEFINED
            If provided, whether the message will be read out by a screen
            reader using Discord's TTS (text-to-speech) system.
        mentions_everyone : bool | hikari.UNDEFINED
            If provided, whether the message should parse @everyone/@here
            mentions.
        user_mentions : hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UNDEFINED
            If provided, and `True`, all user mentions will be detected.
            If provided, and `False`, all user mentions will be ignored
            if appearing in the message body.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialUser` derivatives to enforce mentioning
            specific users.
        role_mentions : hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UNDEFINED
            If provided, and `True`, all role mentions will be detected.
            If provided, and `False`, all role mentions will be ignored
            if appearing in the message body.

            Alternatively this may be a collection of
            `hikari.Snowflake`, or
            `hikari.PartialRole` derivatives to enforce mentioning
            specific roles.

        Raises
        ------
        ValueError
            If more than 100 unique objects/entities are passed for
            `role_mentions` or `user_mentions`.

            If the interaction will have expired before `delete_after` is reached.
        TypeError
            If both `embed` and `embeds` are specified.
        hikari.BadRequestError
            This may be raised in several discrete situations, such as messages
            being empty with no embeds; messages with more than
            2000 characters in them, embeds that exceed one of the many embed
            limits; invalid image URLs in embeds.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.NotFoundError
            If the interaction is not found or if the interaction's initial
            response has already been created.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """


class MenuContext(AppCommandContext, abc.ABC):
    """Interface of a menu command context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def command(self) -> typing.Optional[MenuCommand[typing.Any, typing.Any]]:
        """Command that was invoked.

        .. note::
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
    def target(self) -> typing.Union[hikari.InteractionMember, hikari.User, hikari.Message]:
        """Object of the entity this menu targets."""

    @property
    @abc.abstractmethod
    def type(self) -> typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER]:
        """The type of context menu this context is for."""

    @abc.abstractmethod
    def set_command(self: _T, _: typing.Optional[MenuCommand[typing.Any, typing.Any]], /) -> _T:
        """Set the command for this context.

        Parameters
        ----------
        command : MenuCommand | None
            The command this context is for.
        """

    @typing.overload
    @abc.abstractmethod
    def resolve_to_member(self) -> hikari.InteractionMember:
        ...

    @typing.overload
    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T) -> typing.Union[hikari.InteractionMember, _T]:
        ...

    @abc.abstractmethod
    def resolve_to_member(self, *, default: _T = ...) -> typing.Union[hikari.InteractionMember, _T]:
        """Resolve a user context menu context to a member object.

        Returns
        -------
        hikari.Member
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
        hikari.Message
            The resolved message.

        Raises
        ------
        TypeEror
        if the context is not for a message menu.
        """

    @abc.abstractmethod
    def resolve_to_user(self) -> typing.Union[hikari.User, hikari.Member]:
        """Resolve a user context menu context to a user object.

        Returns
        -------
        hikari.User | hikari.Member
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
    def command(self) -> typing.Optional[BaseSlashCommand]:
        """Command that was invoked.

        .. note::
            This should always be set during command check execution and command
            hook execution but isn't guaranteed for client callbacks nor
            component/client checks.
        """

    @property
    @abc.abstractmethod
    def options(self) -> collections.Mapping[str, SlashOption]:
        """Mapping of option names to the values provided for them."""

    @abc.abstractmethod
    def set_command(self: _T, _: typing.Optional[BaseSlashCommand], /) -> _T:
        """Set the command for this context.

        Parameters
        ----------
        command : BaseSlashCommand | None
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
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        """Hikari cache instance this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def client(self) -> Client:
        """Tanjun `Client` implementation this context was spawned by."""

    @property
    @abc.abstractmethod
    def created_at(self) -> datetime.datetime:
        """When this context was created.

        .. note::
            This will either refer to a message or integration's creation date.
        """

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        """Object of the event manager this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def focused(self) -> AutocompleteOption:
        """The option being autocompleted."""

    @property
    @abc.abstractmethod
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        """ID of the guild this autocomplete was triggered in.

        Will be `None` for all DM autocomplete executions.
        """

    @property
    @abc.abstractmethod
    def member(self) -> typing.Optional[hikari.Member]:
        """Guild member object of this autocomplete's author.

        Will be `None` for DM autocomplete executions.
        """

    @property
    @abc.abstractmethod
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        """Object of the Hikari interaction server provided for this context's client."""

    @property
    @abc.abstractmethod
    def rest(self) -> hikari.api.RESTClient:
        """Object of the Hikari REST client this context's client was initialised with."""

    @property
    @abc.abstractmethod
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        """Shard that triggered the context.

        .. note::
            This will be `None` if `ctx.shards` is also `None`.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[hikari.ShardAware]:
        """Object of the Hikari shard manager this context's client was initialised with."""

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
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
    def options(self) -> collections.Mapping[str, AutocompleteOption]:
        """Mapping of option names to the values provided for them."""

    @abc.abstractmethod
    async def fetch_channel(self) -> hikari.TextableChannel:
        """Fetch the channel the context was invoked in.

        .. note::
            This performs an API call. Consider using `Context.get_channel`
            if you have `hikari.config.CacheComponents.GUILD_CHANNELS` cache component enabled.

        Returns
        -------
        hikari.TextableChannel
            The textable DM or guild channel the context was invoked in.

        Raises
        ------
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.ForbiddenError
            If you are missing the `READ_MESSAGES` permission in the channel.
        hikari.NotFoundError
            If the channel is not found.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:
        """Fetch the guild the context was invoked in.

        .. note::
            This performs an API call. Consider using `Context.get_guild`
            if you have `hikari.config.CacheComponents.GUILDS` cache component enabled.

        Returns
        -------
        hikari.Guild | None
            An optional guild the context was invoked in.
            `None` will be returned if the context was invoked in a DM channel.

        Raises
        ------
        hikari.ForbiddenError
            If you are not part of the guild.
        hikari.NotFoundError
            If the guild is not found.
        hikari.UnauthorizedError
            If you are unauthorized to make the request (invalid/missing token).
        hikari.RateLimitTooLongError
            Raised in the event that a rate limit occurs that is
            longer than `max_rate_limit` when making a request.
        hikari.RateLimitedError
            Usually, Hikari will handle and retry on hitting
            rate-limits automatically. This includes most bucket-specific
            rate-limits and global rate-limits. In some rare edge cases,
            however, Discord implements other undocumented rules for
            rate-limiting, such as limits per attribute. These cannot be
            detected or handled normally by Hikari due to their undocumented
            nature, and will trigger this exception if they occur.
        hikari.InternalServerError
            If an internal error occurs on Discord while handling the request.
        """

    @abc.abstractmethod
    def get_channel(self) -> typing.Optional[hikari.TextableGuildChannel]:
        """Retrieve the channel the context was invoked in from the cache.

        .. note::
            This method requires the `hikari.config.CacheComponents.GUILD_CHANNELS` cache component.

        Returns
        -------
        hikari.TextableGuildChannel | None
            An optional guild channel the context was invoked in.
            `None` will be returned if the channel was not found or if it
            is DM channel.
        """

    @abc.abstractmethod
    def get_guild(self) -> typing.Optional[hikari.Guild]:
        """Fetch the guild that the context was invoked in.

        .. note::
            This method requires `hikari.config.CacheComponents.GUILDS` cache component enabled.

        Returns
        -------
        hikari.Guild | None
            An optional guild the context was invoked in.
            `None` will be returned if the guild was not found.
        """

    @abc.abstractmethod
    async def set_choices(
        self,
        choices: typing.Union[
            collections.Mapping[str, _AutocompleteValueT], collections.Iterable[tuple[str, _AutocompleteValueT]]
        ] = ...,
        /,
        **kwargs: _AutocompleteValueT,
    ) -> None:
        """Set the choices for this autocomplete.

        .. note::
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
    def copy(self: _T) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def add_on_error(self: _T, callback: ErrorHookSig, /) -> _T:
        """Add an error callback to this hook object.

        .. note::
            This won't be called for expected `tanjun.TanjunError` derived errors.

        Parameters
        ----------
        callback : ErrorHookSig
            The callback to add to this hook.

            This callback should take two positional arguments (of type
            `tanjun.abc.Context` and `Exception`) and may be either
            synchronous or asynchronous.

            Returning `True` indicates that the error should be suppressed,
            `False` that it should be re-raised and `None` that no decision has
            been made. This will be accounted for along with the decisions
            other error hooks make by majority rule.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @abc.abstractmethod
    def with_on_error(self, callback: _ErrorHookSigT, /) -> _ErrorHookSigT:
        """Add an error callback to this hook object through a decorator call.

        .. note::
            This won't be called for expected `tanjun.TanjunError` derived errors.

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
            `tanjun.abc.Context` and `Exception`) and may be either
            synchronous or asynchronous.

            Returning `True` indicates that the error shoul be suppressed,
            `False` that it should be re-raised and `None` that no decision
            has been made. This will be accounted for along with the decisions
            other error hooks make by majority rule.

        Returns
        -------
        ErrorHookSig
            The hook callback which was added.
        """

    @abc.abstractmethod
    def add_on_parser_error(self: _T, callback: HookSig, /) -> _T:
        """Add a parser error callback to this hook object.

        Parameters
        ----------
        callback : HookSig
            The callback to add to this hook.

            This callback should take two positional arguments (of type
            `tanjun.abc.Context` and `tanjun.errors.ParserError`),
            return `None` and may be either synchronous or asynchronous.

            It's worth noting that this unlike general error handlers, this will
            always suppress the error.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @abc.abstractmethod
    def with_on_parser_error(self, callback: _HookSigT, /) -> _HookSigT:
        """Add a parser error callback to this hook object through a decorator call.

        Examples
        --------
        ```py
        hooks = AnyHooks()

        @hooks.with_on_parser_error
        async def on_parser_error(ctx: tanjun.abc.Context, error: tanjun.errors.ParserError) -> None:
            await ctx.respond(f"You gave invalid input: {error}")
        ```

        Parameters
        ----------
        callback : HookSig
            The parser error callback to add to this hook.

            This callback should take two positional arguments (of type
            `tanjun.abc.Context` and `tanjun.errors.ParserError`),
            return `None` and may be either synchronous or asynchronous.

        Returns
        -------
        HookSig
            The callback which was added.
        """

    @abc.abstractmethod
    def add_post_execution(self: _T, callback: HookSig, /) -> _T:
        """Add a post-execution callback to this hook object.

        Parameters
        ----------
        callback : HookSig
            The callback to add to this hook.

            This callback should take one positional argument (of type
            `tanjun.abc.Context`), return `None` and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @abc.abstractmethod
    def with_post_execution(self, callback: _HookSigT, /) -> _HookSigT:
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
            `tanjun.abc.Context`), return `None` and may be either
            synchronous or asynchronous.

        Returns
        -------
        HookSig
            The post-execution callback which was seaddedt.
        """

    @abc.abstractmethod
    def add_pre_execution(self: _T, callback: HookSig, /) -> _T:
        """Add a pre-execution callback for this hook object.

        Parameters
        ----------
        callback : HookSig
            The callback to add to this hook.

            This callback should take one positional argument (of type
            `tanjun.abc.Context`), return `None` and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @abc.abstractmethod
    def with_pre_execution(self, callback: _HookSigT, /) -> _HookSigT:
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
            `tanjun.abc.Context`), return `None` and may be either
            synchronous or asynchronous.

        Returns
        -------
        HookSig
            The pre-execution callback which was added.
        """

    @abc.abstractmethod
    def add_on_success(self: _T, callback: HookSig, /) -> _T:
        """Add a success callback to this hook object.

        Parameters
        ----------
        callback : HookSig
            The callback to add to this hook.

            This callback should take one positional argument (of type
            `tanjun.abc.Context`), return `None` and may be either
            synchronous or asynchronous.

        Returns
        -------
        Self
            The hook object to enable method chaining.
        """

    @abc.abstractmethod
    def with_on_success(self, callback: _HookSigT, /) -> _HookSigT:
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
            `tanjun.abc.Context`), return `None` and may be either
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
        /,
        exception: Exception,
        *,
        hooks: typing.Optional[collections.Set[Hooks[_ContextT_contra]]] = None,
    ) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_post_execution(
        self,
        ctx: _ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[Hooks[_ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_pre_execution(
        self,
        ctx: _ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[Hooks[_ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_success(
        self,
        ctx: _ContextT_contra,
        /,
        *,
        hooks: typing.Optional[collections.Set[Hooks[_ContextT_contra]]] = None,
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
    def checks(self) -> collections.Collection[CheckSig]:
        """Collection of checks that must be met before the command can be executed."""

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        """Component that the command is registered with."""

    @property
    @abc.abstractmethod
    def hooks(self) -> typing.Optional[Hooks[_ContextT_co]]:
        """Hooks that are triggered when the command is executed."""

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Mutable mapping of metadata set for this command.

        .. note::
            Any modifications made to this mutable mapping will be preserved by
            the command.
        """

    @abc.abstractmethod
    def bind_client(self: _T, client: Client, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self: _T, component: Component, /) -> _T:
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
    def set_hooks(self: _T, _: typing.Optional[Hooks[_ContextT_co]], /) -> _T:
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
    def remove_check(self: _T, check: CheckSig, /) -> _T:
        """Remove a check from the command.

        Parameters
        ----------
        check : CheckSig
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
    def set_metadata(self: _T, key: typing.Any, value: typing.Any, /) -> _T:
        """Set a field in the command's metadata.

        Parameters
        ----------
        key : typing.Any
            Metadata key to set.
        value : typing.Any
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
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        """Whether contexts executed by this command should default to ephemeral responses.

        This effects calls to `SlashContext.create_followup`,
        `SlashContext.create_initial_response`, `SlashContext.defer` and
        `SlashContext.respond` unless the `flags` field is provided for the
        methods which support it.

        Returns
        -------
        bool
            Whether calls to this command should default to ephemeral mode.

            If this is `None` then the default from the parent command(s),
            component or client is used.
        """

    @property
    @abc.abstractmethod
    def is_global(self) -> bool:
        """Whether the command should be declared globally or not.

        .. warning::
            For commands within command groups the state of this flag
            is inherited regardless of what it's set as on the child command.
        """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the command."""

    @property
    def tracked_command(self) -> typing.Optional[hikari.PartialCommand]:
        """Object of the actual command this object tracks if set."""

    @property
    @abc.abstractmethod
    def tracked_command_id(self) -> typing.Optional[hikari.Snowflake]:
        """ID of the actual command this object tracks if set."""

    @property
    @abc.abstractmethod
    def type(self) -> hikari.CommandType:
        """The type of this application command."""

    @abc.abstractmethod
    def build(self) -> hikari.api.CommandBuilder:
        """Get a builder object for this command.

        Returns
        -------
        hikari.api.CommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
        """

    @abc.abstractmethod
    async def check_context(self, ctx: _AppCommandContextT, /) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self,
        ctx: _AppCommandContextT,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[Hooks[_AppCommandContextT]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set_tracked_command(self: _T, command: hikari.PartialCommand, /) -> _T:
        """Set the global command this tracks.

        Parameters
        ----------
        command : hikari.PartialCommand
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
    def parent(self) -> typing.Optional[SlashCommandGroup]:
        """Object of the group this command is in."""

    @property
    def tracked_command(self) -> typing.Optional[hikari.SlashCommand]:
        """Object of the actual command this object tracks if set."""

    @property
    @abc.abstractmethod
    def type(self) -> typing.Literal[hikari.CommandType.SLASH]:
        """The type of this command."""

    @abc.abstractmethod
    def build(self) -> hikari.api.SlashCommandBuilder:
        """Get a builder object for this command.

        Returns
        -------
        hikari.api.SlashCommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
        """

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[SlashCommandGroup], /) -> _T:
        raise NotImplementedError

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
        ...

    async def execute_autocomplete(
        self,
        ctx: AutocompleteContext,
        /,
        option: typing.Optional[hikari.AutocompleteInteractionOption] = None,
    ) -> None:
        ...


class SlashCommand(BaseSlashCommand, abc.ABC, typing.Generic[_CommandCallbackSigT]):
    """A command that can be executed in a slash context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CommandCallbackSigT:
        """Callback which is called during execution."""

    @property
    @abc.abstractmethod
    def float_autocompletes(self) -> collections.Mapping[str, AutocompleteCallbackSig]:
        """Collection of the float option autocompletes."""

    @property
    @abc.abstractmethod
    def int_autocompletes(self) -> collections.Mapping[str, AutocompleteCallbackSig]:
        """Collection of the integer option autocompletes."""

    @property
    @abc.abstractmethod
    def str_autocompletes(self) -> collections.Mapping[str, AutocompleteCallbackSig]:
        """Collection of the string option autocompletes."""


class MenuCommand(AppCommand[MenuContext], typing.Generic[_MenuCommandCallbackSigT, _MenuTypeT]):
    """A contextmenu command."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _MenuCommandCallbackSigT:
        """Callback which is called during execution."""

    @property
    @abc.abstractmethod
    def type(self) -> _MenuTypeT:
        """The menu type(s) this is for."""

    @property
    @abc.abstractmethod
    def tracked_command(self) -> typing.Optional[hikari.ContextMenuCommand]:
        """Object of the actual command this object tracks if set."""

    @abc.abstractmethod
    def build(self) -> hikari.api.ContextMenuCommandBuilder:
        """Get a builder object for this command.

        Returns
        -------
        hikari.api.ContextMenuCommandBuilder
            A builder object for this command. Use to declare this command on
            globally or for a specific guild.
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
        """Collection of the commands in this group."""

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
    def remove_command(self: _T, command: BaseSlashCommand, /) -> _T:
        """Remove a command from this group.

        Parameters
        ----------
        command : BaseSlashCommand
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
        command : BaseSlashCommand
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
    def bind_client(self: _T, client: Client, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self: _T, component: Component, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        """Copy the parser.

        Returns
        -------
        Self
            A copy of the parser.
        """

    @abc.abstractmethod
    async def parse(self, ctx: MessageContext, /) -> dict[str, typing.Any]:
        """Parse a message context.

        .. warning::
            This relies on the prefix and command name(s) having been removed
            from `tanjun.abc.MessageContext.content`

        Parameters
        ----------
        ctx : tanjun.abc.MessageContext
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


class MessageCommand(ExecutableCommand[MessageContext], abc.ABC, typing.Generic[_CommandCallbackSigT]):
    """Standard interface of a message command."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def callback(self) -> _CommandCallbackSigT:
        """Callback which is called during execution.

        .. note::
            For command groups, this is called when none of the inner-commands
            matches the message.
        """

    @property
    @abc.abstractmethod
    def names(self) -> collections.Collection[str]:
        """Collection of this command's names."""

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Optional[MessageCommandGroup[typing.Any]]:
        """Parent group of this command if applicable."""

    @property
    @abc.abstractmethod
    def parser(self) -> typing.Optional[MessageParser]:
        """Parser for this command."""

    @abc.abstractmethod
    def set_parent(self: _T, _: typing.Optional[MessageCommandGroup[typing.Any]], /) -> _T:
        """Set the parent of this command.

        Parameters
        ----------
        parent : MessageCommandGroup[typing.Any] | None
            The parent of this command.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """

    @abc.abstractmethod
    def set_parser(self: _T, _: MessageParser, /) -> _T:
        """Set the for this message command.

        Parameters
        ----------
        parser : MessageParser
            The parser to set.

        Returns
        -------
        Self
            The command instance to enable chained calls.
        """

    @abc.abstractmethod
    def copy(self: _T, *, parent: typing.Optional[MessageCommandGroup[typing.Any]] = None) -> _T:
        """Create a copy of this command.

        Other Parameters
        ----------------
        parent : MessageCommandGroup[tping.Any] | None
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
        self, ctx: MessageContext, /, *, hooks: typing.Optional[collections.MutableSet[Hooks[MessageContext]]] = None
    ) -> None:
        raise NotImplementedError


class MessageCommandGroup(MessageCommand[_CommandCallbackSigT], abc.ABC):
    """Standard interface of a message command group."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def commands(self) -> collections.Collection[MessageCommand[typing.Any]]:
        """Collection of the commands in this group.

        .. note::
            This may include command groups.
        """

    @abc.abstractmethod
    def add_command(self: _T, command: MessageCommand[typing.Any], /) -> _T:
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
    def remove_command(self: _T, command: MessageCommand[typing.Any], /) -> _T:
        """Remove a command from this group.

        Parameters
        ----------
        command : MessageCommand
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

    This is a collection of message and slash commands, and listeners
    with logic for command search + execution and loading the listeners
    into a tanjun client.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def client(self) -> typing.Optional[Client]:
        """Tanjun client this component is bound to."""

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        """Whether slash contexts executed in this component should default to ephemeral responses.

        This effects calls to `SlashContext.create_followup`,
        `SlashContext.create_initial_response`, `SlashContext.defer` and
        `SlashContext.respond` unless the `flags` field is provided for the
        methods which support it.

        Notes
        -----
        * This may be overridden by `BaseSlashCommand.defaults_to_ephemeral`.
        * This only effects slash command execution.
        * If this is `None` then the default from the parent client is used.
        """

    @property
    @abc.abstractmethod
    def loop(self) -> typing.Optional[asyncio.AbstractEventLoop]:
        """The asyncio loop this client is bound to if it has been opened."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Component's unique identifier.

        .. note::
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
    def listeners(self) -> collections.Mapping[type[hikari.Event], collections.Collection[ListenerCallbackSig]]:
        """Mapping of event types to the listeners registered for them in this component."""

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Mutable mapping of the metadata set for this component.

        .. note::
            Any modifications made to this mutable mapping will be preserved by
            the component.
        """

    @abc.abstractmethod
    def set_metadata(self: _T, key: typing.Any, value: typing.Any, /) -> _T:
        """Set a field in the component's metadata.

        Parameters
        ----------
        key : typing.Any
            Metadata key to set.
        value : typing.Any
            Metadata value to set.

        Returns
        -------
        Self
            The component instance to enable chained calls.
        """

    @abc.abstractmethod
    def add_menu_command(self: _T, command: MenuCommand[typing.Any, typing.Any], /) -> _T:
        """Add a menu command to this component.

        Parameters
        ----------
        command : MenuCommand
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_menu_command(self: _T, command: MenuCommand[typing.Any, typing.Any], /) -> _T:
        """Remove a menu command from this component.

        Parameters
        ----------
        command : MenuCommand
            Object of the menu command to remove.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @typing.overload
    @abc.abstractmethod
    def with_menu_command(self, command: _MenuCommandT, /) -> _MenuCommandT:
        ...

    @typing.overload
    @abc.abstractmethod
    def with_menu_command(self, /, *, copy: bool = False) -> collections.Callable[[_MenuCommandT], _MenuCommandT]:
        ...

    @abc.abstractmethod
    def with_menu_command(
        self, command: typing.Optional[_MenuCommandT] = None, /, *, copy: bool = False
    ) -> typing.Union[_MenuCommandT, collections.Callable[[_MenuCommandT], _MenuCommandT]]:
        """Add a menu command to this component through a decorator call.

        Parameters
        ----------
        command : MenuCommand
            The command to add.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it.

        Returns
        -------
        MenuCommand
            The added command.
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
    def remove_slash_command(self: _T, command: BaseSlashCommand, /) -> _T:
        """Remove a slash command from this component.

        Parameters
        ----------
        command : BaseSlashCommand
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
    def with_slash_command(self, command: _BaseSlashCommandT, /) -> _BaseSlashCommandT:
        ...

    @typing.overload
    @abc.abstractmethod
    def with_slash_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_BaseSlashCommandT], _BaseSlashCommandT]:
        ...

    @abc.abstractmethod
    def with_slash_command(
        self, command: _BaseSlashCommandT = ..., /, *, copy: bool = False
    ) -> typing.Union[_BaseSlashCommandT, collections.Callable[[_BaseSlashCommandT], _BaseSlashCommandT]]:
        """Add a slash command to this component through a decorator call.

        Parameters
        ----------
        command : BaseSlashCommand
            The command to add.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it.

        Returns
        -------
        BaseSlashCommand
            The added command.
        """

    @abc.abstractmethod
    def add_message_command(self: _T, command: MessageCommand[typing.Any], /) -> _T:
        """Add a message command to this component.

        Parameters
        ----------
        command : MessageCommand[typing.Any]
            The command to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_message_command(self: _T, command: MessageCommand[typing.Any], /) -> _T:
        """Remove a message command from this component.

        Parameters
        ----------
        command : MessageCommand[typing.Any]
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
    def with_message_command(self, command: _MessageCommandT, /) -> _MessageCommandT:
        ...

    @typing.overload
    @abc.abstractmethod
    def with_message_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_MessageCommandT], _MessageCommandT]:
        ...

    @abc.abstractmethod
    def with_message_command(
        self, command: _MessageCommandT = ..., /, *, copy: bool = False
    ) -> typing.Union[_MessageCommandT, collections.Callable[[_MessageCommandT], _MessageCommandT]]:
        """Add a message command to this component through a decorator call.

        Parameters
        ----------
        command : MessageCommand
            The command to add.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it.

        Returns
        -------
        MessageCommand
            The added command.
        """

    @abc.abstractmethod
    def add_listener(self: _T, event: type[hikari.Event], listener: ListenerCallbackSig, /) -> _T:
        """Add a listener to this component.

        Parameters
        ----------
        event : type[hikari.Event]
            The event to listen for.
        listener : ListenerCallbackSig
            The listener to add.

        Returns
        -------
        Self
            The component to enable chained calls.
        """

    @abc.abstractmethod
    def remove_listener(self: _T, event: type[hikari.Event], listener: ListenerCallbackSig, /) -> _T:
        """Remove a listener from this component.

        Parameters
        ----------
        event : type[hikari.Event]
            The event to listen for.
        listener : ListenerCallbackSig
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

    # TODO: make event optional?
    @abc.abstractmethod
    def with_listener(
        self, event_type: type[hikari.Event]
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT,]:
        """Add a listener to this component through a decorator call.

        Parameters
        ----------
        event_type : type[hikari.Event]
            The event to listen for.

        Returns
        -------
        collections.abc.Callable[[ListenerCallbackSig], ListenerCallbackSig]
            Decorator callback which takes listener to add.
        """

    @abc.abstractmethod
    def bind_client(self: _T, client: Client, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def unbind_client(self: _T, client: Client, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, MessageCommand[typing.Any]]]:
        """Check whether a name matches any of this component's registered message commands.

        Notes
        -----
        * This only checks for name matches against the top level command and
          will not account for sub-commands.
        * Dependent on implementation detail this may partial check name against
          command names using name.startswith(command_name), hence why it
          also returns the name a command was matched by.

        Parameters
        ----------
        name : str
            The name to check for command matches.

        Returns
        -------
        collections.abc.Iterator[tuple[str, MessageCommand[typing.Any]]]
            Iterator of tuples of command name matches to the relevant message
            command objects.
        """

    @abc.abstractmethod
    def check_slash_name(self, name: str, /) -> collections.Iterator[BaseSlashCommand]:
        """Check whether a name matches any of this component's registered slash commands.

        .. note::
            This won't check for sub-commands and will expect `name` to simply be
            the top level command name.

        Parameters
        ----------
        name : str
            The name to check for command matches.

        Returns
        -------
        collections.abc.Iterator[BaseSlashCommand]
            An iterator of the matching slash commands.
        """

    @abc.abstractmethod
    def execute_autocomplete(
        self,
        ctx: AutocompleteContext,
        /,
    ) -> typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]:
        """Execute an autocomplete context.

        .. note::
            Unlike the other execute methods, this shouldn't be expected to
            raise `tanjun.errors.HaltExecution` nor `tanjun.errors.CommandError`.

        Parameters
        ----------
        ctx : AutocompleteContext
            The context to execute.

        Returns
        -------
        collections.abc.Coroutine[typing.Any, typing.Any, None] | None
            Awaitable used to wait for the command execution to finish.

            This may be awaited or left to run as a background task.

            If this is `None` then the client should carry on its search for a
            component with a matching autocomplete.
        """

    @abc.abstractmethod
    async def execute_menu(
        self,
        ctx: MenuContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[MenuHooks]] = None,
    ) -> typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]:
        """Execute a menu context.

        Parameters
        ----------
        ctx : MenuContext
            The context to execute.

        Other Parameters
        ----------------
        hooks : collections.abc.MutableSet[MenuHooks] | None
            Set of hooks to include in this command execution.

        Returns
        -------
        collections.abc.Coroutine[typing.Any, typing.Any, None] | None
            Awaitable used to wait for the command execution to finish.

            This may be awaited or left to run as a background task.

            If this is `None` then the client should carry on its search for a
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
        self,
        ctx: SlashContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[SlashHooks]] = None,
    ) -> typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]:
        """Execute a slash context.

        Parameters
        ----------
        ctx : SlashContext
            The context to execute.

        Other Parameters
        ----------------
        hooks : collections.abc.MutableSet[SlashHooks] | None
            Set of hooks to include in this command execution.

        Returns
        -------
        collections.abc.Coroutine[typing.Any, typing.Any, None] | None
            Awaitable used to wait for the command execution to finish.

            This may be awaited or left to run as a background task.

            If this is `None` then the client should carry on its search for a
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
        self, ctx: MessageContext, /, *, hooks: typing.Optional[collections.MutableSet[MessageHooks]] = None
    ) -> bool:
        """Execute a message context.

        Parameters
        ----------
        ctx : MessageContext
            The context to execute.

        Other Parameters
        ----------------
        hooks : collections.abc.MutableSet[MessageHooks] | None
            Set of hooks to include in this command execution.

        Returns
        -------
        bool
            Whether a message command was executed in this component with the
            provided context.

            If `False` then the client should carry on its search for a
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

        Other Parameters
        ----------------
        unbind : bool
            Whether to unbind from the client after this is closed.

            Defaults to `False`.

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

    These should be dispatched by all `Client` implementations.
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

    .. warning::
        This event isn't dispatched for components which were registered while
        the client is inactive.

    The first positional argument is the `tanjun.abc.Component` being added.
    """

    COMPONENT_REMOVED = "component_removed"
    """Called when a component is added to an active client.

    .. warning::
        This event isn't dispatched for components which were removed while
        the client is inactive.

    The first positional argument is the `tanjun.abc.Component` being removed.
    """

    MENU_COMMAND_NOT_FOUND = "menu_command_not_found"
    """Called when a menu command is not found.

    `tanjun.abc.MenuContext` is provided as the first positional argument.
    """

    MESSAGE_COMMAND_NOT_FOUND = "message_command_not_found"
    """Called when a message command is not found.

    `tanjun.abc.MessageContext` is provided as the first positional argument.
    """

    SLASH_COMMAND_NOT_FOUND = "slash_command_not_found"
    """Called when a slash command is not found.

    `tanjun.abc.SlashContext` is provided as the first positional argument.
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
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        """Hikari cache instance this command client was initialised with."""

    @property
    @abc.abstractmethod
    def components(self) -> collections.Collection[Component]:
        """Collection of the components this command client is using."""

    @property
    @abc.abstractmethod
    def defaults_to_ephemeral(self) -> bool:
        """Whether slash contexts spawned by this client should default to ephemeral responses.

        This effects calls to `SlashContext.create_followup`,
        `SlashContext.create_initial_response`, `SlashContext.defer` and
        `SlashContext.respond` unless the `flags` field is provided for the
        methods which support it.

        Notes
        -----
        * This may be overridden by `BaseSlashCommand.defaults_to_ephemeral`
          and `Component.defaults_to_ephemeral`.
        * This defaults to `False`.
        * This only effects slash command execution.
        """

    @property
    @abc.abstractmethod
    def events(self) -> typing.Optional[hikari.api.EventManager]:
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

    @property  # TODO: switch over to a mapping of event to collection cause convenience
    @abc.abstractmethod
    def listeners(self) -> collections.Mapping[type[hikari.Event], collections.Collection[ListenerCallbackSig]]:
        """Mapping of event types to the listeners registered in this client."""

    @property
    @abc.abstractmethod
    def loop(self) -> typing.Optional[asyncio.AbstractEventLoop]:
        """The loop this client is bound to if it's alive."""

    @property
    @abc.abstractmethod
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        """Mutable mapping of the metadata set for this client.

        .. note::
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
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        """Object of the Hikari interaction server provided for this client.

        This is used for executing slash commands if set.
        """

    @property
    @abc.abstractmethod
    def shards(self) -> typing.Optional[hikari.ShardAware]:
        """Object of the Hikari shard manager this client was initialised with."""

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
        """Object of the Hikari voice component this client was initialised with."""

    @abc.abstractmethod
    async def clear_application_commands(
        self,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> None:
        """Clear the commands declared either globally or for a specific guild.

        .. note::
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Other Parameters
        ----------------
        application : hikari.snowflakes.Snowflakeish | hikari.PartialApplication | None
            The application to clear commands for.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : hikari.snowflakes.Snowflakeish | hikari.PartialGuild | hikari.UNDEFINED
            Object or ID of the guild to clear commands for.

            If left as `None` global commands will be cleared.
        """

    @abc.abstractmethod
    async def declare_global_commands(
        self,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        force: bool = False,
    ) -> collections.Sequence[hikari.PartialCommand]:
        """Set the global application commands for a bot based on the loaded components.

        .. warning::
            This will overwrite any previously set application commands and
            only targets commands marked as global.

        Notes
        -----
        * The endpoint this uses has a strict ratelimit which, as of writing,
          only allows for 2 requests per minute (with that ratelimit either
          being per-guild if targeting a specific guild otherwise globally).
        * Setting a specific `guild` can be useful for testing/debug purposes
          as slash commands may take up to an hour to propagate globally but
          will immediately propagate when set on a specific guild.

        Other Parameters
        ----------------
        command_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of top level command names to IDs of the
            existing commands to update.

            This will be used for all application commands but in cases where
            commands have overlapping names, `message_ids` and `user_ids` will
            take priority over this for their relevant command type.
        application : hikari.snowflakes.Snowflakeish | hikari.PartialApplication | None
            Object or ID of the application to set the global commands for.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : hikari.snowflakes.Snowflakeish | hikari.PartialGuild | None
            Object or ID of the guild to set the global commands to.

            If left as `None` global commands will be set.
        message_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        force : bool
            Force this to declare the commands regardless of whether or not
            they match the current state of the declared commands.

            Defaults to `False`. This default behaviour helps avoid issues with the
            2 request per minute (per-guild or globally) ratelimit and the other limit
            of only 200 application command creates per day (per guild or globally).

        Returns
        -------
        collections.abc.Sequence[hikari..Command]
            API representations of the set commands.
        """

    @typing.overload
    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: BaseSlashCommand,
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.SlashCommand:
        ...

    @typing.overload
    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: MenuCommand[typing.Any, typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.ContextMenuCommand:
        ...

    @typing.overload
    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: AppCommand[typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        ...

    @abc.abstractmethod
    async def declare_application_command(
        self,
        command: AppCommand[typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        """Declare a single slash command for a bot.

        .. warning::
            Providing `command_id` when updating a command helps avoid any
            permissions set for the command being lose (e.g. when changing the
            command's name).

        Parameters
        ----------
        command : AppCommand
            The command to register.

        Other Parameters
        ----------------
        application : hikari.snowflakes.Snowflakeish | hikari.PartialApplication | None
            The application to register the command with.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        command_id : hikari.snowflakes.Snowflakeish | None
            ID of the command to update.
        guild : hikari.snowflakes.Snowflakeish | hikari.PartialGuild | None
            Object or ID of the guild to register the command with.

            If left as `None` then the command will be registered globally.

        Returns
        -------
        hikari.PartialCommand
            API representation of the command that was registered.
        """

    @abc.abstractmethod
    async def declare_application_commands(
        self,
        commands: collections.Iterable[AppCommand[typing.Any]],
        /,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        force: bool = False,
    ) -> collections.Sequence[hikari.PartialCommand]:
        """Declare a collection of slash commands for a bot.

        .. note::
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Parameters
        ----------
        commands : collections.abc.Iterable[AppCommand]
            Iterable of the commands to register.

        Other Parameters
        ----------------
        command_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of top level command names to IDs of the
            existing commands to update.

            This will be used for all application commands but in cases where
            commands have overlapping names, `message_ids` and `user_ids` will
            take priority over this for their relevant command type.

            While optional, this can be helpful when updating commands as
            providing the current IDs will prevent changes such as renames from
            leading to other state set for commands (e.g. permissions) from
            being lost.
        application : hikari.snowflakes.Snowflakeish | hikari.PartialApplication | None
            The application to register the commands with.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : hikari.snowflakes.Snowflakeish | hikari.PartialGuild | None
            Object or ID of the guild to register the commands with.

            If left as `None` then the commands will be registered globally.
        message_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        force : bool
            Force this to declare the commands regardless of whether or not
            they match the current state of the declared commands.

            Defaults to `False`. This default behaviour helps avoid issues with the
            2 request per minute (per-guild or globally) ratelimit and the other limit
            of only 200 application command creates per day (per guild or globally).

        Returns
        -------
        collections.abc.Sequence[hikari.PartialCommand]
            API representations of the commands which were registered.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If conflicting command names are found (multiple commanbds have the same top-level name).
            * If more than 100 top-level commands are passed.
        """

    @abc.abstractmethod
    def set_metadata(self: _T, key: typing.Any, value: typing.Any, /) -> _T:
        """Set a field in the client's metadata.

        Parameters
        ----------
        key : typing.Any
            Metadata key to set.
        value : typing.Any
            Metadata value to set.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    def add_component(self: _T, component: Component, /) -> _T:
        """Add a component to this client.

        Parameters
        ----------
        component: Component
            The component to move to this client.

        Returns
        -------
        Self
            The client instance to allow chained calls.
        """

    @abc.abstractmethod
    def get_component_by_name(self, name: str, /) -> typing.Optional[Component]:
        """Get a component from this client by name.

        Parameters
        ----------
        name : str
            Name to get a component by.

        Returns
        -------
        Component | None
            The component instance if found, else `None`.
        """

    @abc.abstractmethod
    def remove_component(self: _T, component: Component, /) -> _T:
        """Remove a component from this client.

        This will unsubscribe any client callbacks, commands and listeners
        registered in the provided component.

        Parameters
        ----------
        component: Component
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
    def remove_component_by_name(self: _T, name: str, /) -> _T:
        """Remove a component from this client by name.

        This will unsubscribe any client callbacks, commands and listeners
        registered in the provided component.

        Parameters
        ----------
        name: str
            Name of the component to remove from this client.

        Raises
        ------
        KeyError
            If the provided component name isn't found.
        """

    @abc.abstractmethod
    def add_client_callback(self: _T, name: typing.Union[str, ClientCallbackNames], callback: MetaEventSig, /) -> _T:
        """Add a client callback.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name this callback is being registered to.

            This is case-insensitive.
        callback : MetaEventSig
            The callback to register.

            This may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    async def dispatch_client_callback(
        self, name: typing.Union[str, ClientCallbackNames], /, *args: typing.Any
    ) -> None:
        """Dispatch a client callback.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name of the callback to dispatch.

        Other Parameters
        ----------------
        *args : typing.Any
            Positional arguments to pass to the callback(s).

        Raises
        ------
        KeyError
            If no callbacks are registered for the given name.
        """

    @abc.abstractmethod
    def get_client_callbacks(
        self, name: typing.Union[str, ClientCallbackNames], /
    ) -> collections.Collection[MetaEventSig]:
        """Get a collection of the callbacks registered for a specific name.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name to get the callbacks registered for.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Collection[MetaEventSig]
            Collection of the callbacks for the provided name.
        """

    @abc.abstractmethod
    def remove_client_callback(self: _T, name: typing.Union[str, ClientCallbackNames], callback: MetaEventSig, /) -> _T:
        """Remove a client callback.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name this callback is being registered to.

            This is case-insensitive.
        callback : MetaEventSig
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
        self, name: typing.Union[str, ClientCallbackNames], /
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
        name : str | ClientCallbackNames
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
    def add_listener(self: _T, event_type: type[hikari.Event], callback: ListenerCallbackSig, /) -> _T:
        """Add a listener to the client.

        Parameters
        ----------
        event_type : type[hikari.Event]
            The event type to add a listener for.
        callback: ListenerCallbackSig
            The callback to register as a listener.

            This callback must be a coroutine function which returns `None` and
            always takes one positional arg of type `hikari.Event`
            regardless of client implementation detail.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """

    @abc.abstractmethod
    def remove_listener(self: _T, event_type: type[hikari.Event], callback: ListenerCallbackSig, /) -> _T:
        """Remove a listener from the client.

        Parameters
        ----------
        event_type : type[hikari.Event]
            The event type to remove a listener for.
        callback: ListenerCallbackSig
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
        self, event_type: type[hikari.Event], /
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
        event_type : type[hikari.Event]
            The event type to listener for.

        Returns
        -------
        collections.abc.Callable[[ListenerCallbackSig], ListenerCallbackSig]
            Decorator callback used to register the event callback.

            The callback must be a coroutine function which returns `None` and
            always takes at least one positional arg of type `hikari.Event`
            regardless of client implementation detail.
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
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[  # noqa: A002 - Shadowing a builtin name.
            typing.Literal[hikari.CommandType.MESSAGE]
        ] = None,
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Literal[hikari.CommandType.MESSAGE]]]:
        ...

    @typing.overload
    @abc.abstractmethod
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[typing.Literal[hikari.CommandType.USER]] = None,  # noqa: A002 - Shadowing a builtin name.
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Literal[hikari.CommandType.USER]]]:
        ...

    @typing.overload
    @abc.abstractmethod
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[  # noqa: A002 - Shadowing a builtin name.
            typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER]
        ] = None,
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Any]]:
        ...

    @abc.abstractmethod
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[  # noqa: A002 - Shadowing a builtin name.
            typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER]
        ] = None,
    ) -> collections.Iterator[MenuCommand[typing.Any, typing.Any]]:
        """Iterator over the menu commands registered to this client.

        Other Parameters
        ----------------
        global_only : bool
            Whether to only iterate over global menu commands.
        type : typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER] | None
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

        Other Parameters
        ----------------
        global_only : bool
            Whether to only iterate over global slash commands.

        Returns
        -------
        collections.abc.Iterator[BaseSlashCommand]
            Iterator of the slash commands registered to this client.
        """

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, MessageCommand[typing.Any]]]:
        """Check whether a message command name is present in the current client.

        .. note::
            Dependent on implementation this may partial check name against the
            message command's name based on command_name.startswith(name).

        Parameters
        ----------
        name : str
            The name to match commands against.

        Returns
        -------
        collections.abc.Iterator[tuple[str, MessageCommand]]
            Iterator of the matched command names to the matched message command objects.
        """

    @abc.abstractmethod
    def check_slash_name(self, name: str, /) -> collections.Iterator[BaseSlashCommand]:
        """Check whether a slash command name is present in the current client.

        .. note::
            This won't check the commands within command groups.

        Parameters
        ----------
        name : str
            Name to check against.

        Returns
        -------
        collections.abc.Iterator[BaseSlashCommand]
            Iterator of the matched slash command objects.
        """

    @abc.abstractmethod
    def load_modules(self: _T, *modules: typing.Union[str, pathlib.Path]) -> _T:
        """Load entities into this client from modules based on present loaders.

        .. note::
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
        loader = tanjun.Component("trans component").load_from_scope().make_loader()
        ```

        Parameters
        ----------
        *modules : str | pathlib.Path
            Path(s) of the modules to load from.

            When `str` this will be treated as a normal import path which is
            absolute (`"foo.bar.baz"`). It's worth noting that absolute module
            paths may be imported from the current location if the top level
            module is a valid module file or module directory in the current
            working directory.

            When `pathlib.Path` the module will be imported directly from
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
            The source error can be found at `tanjun.errors.FailedModuleLoad.__source__`.
        tanjun.errors.ModuleStateConflict
            If the module is already loaded.
        tanjun.errors.ModuleMissingLoaders
            If no loaders are found in the module.
        ModuleNotFoundError
            If the module is not found.
        """

    @abc.abstractmethod
    async def load_modules_async(self, *modules: typing.Union[str, pathlib.Path]) -> None:
        """Asynchronous variant of `Client.load_modules`.

        Unlike `Client.load_modules`, this method will run blocking code in a
        background thread.

        For more information on the behaviour of this method see the
        documentation for `Client.load_modules`.
        """

    @abc.abstractmethod
    def unload_modules(self: _T, *modules: typing.Union[str, pathlib.Path]) -> _T:
        """Unload entities from this client based on unloaders in one or more modules.

        .. note::
            If an `__all__` is present in the target module then it will be
            used to find unloaders.

        Examples
        --------
        For this to work the module has to have at least one unloading enabled
        `tanjun.abc.ClientLoader` present.

        ```py
        @tanjun.as_unloader
        def unload_component(client: tanjun.Client) -> None:
            client.remove_component_by_name(component.name)
        ```

        or

        ```py
        # as_loader's returned ClientLoader handles both loading and unloading.
        loader = tanjun.Component("trans component").load_from_scope().as_loader(unload_component)
        ```

        Parameters
        ----------
        *modules: str | pathlib.Path
            Path of one or more modules to unload.

            These should be the same path(s) which were passed to `load_module`.

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        tanjun.errors.ModuleStateConflict
            If the module hasn't been loaded.
        tanjun.errors.ModuleMissingLoaders
            If no unloaders are found in the module.
        tanjun.errors.FailedModuleUnload
            If the old version of a module failed to unload.

            This indicates that one of its unloaders raised. The source
            error can be found at `tanjun.errors.FailedModuleUnload.__source__`.
        """

    @abc.abstractmethod
    def reload_modules(self: _T, *modules: typing.Union[str, pathlib.Path]) -> _T:
        """Reload entities in this client based on the loaders in loaded module(s).

        .. note::
            If an `__all__` is present in the target module then it will be
            used to find loaders and unloaders.

        Examples
        --------
        For this to work the module has to have at least one ClientLoader
        which handles loading and one which handles unloading present.

        Parameters
        ----------
        *modules: str | pathlib.Path
            Paths of one or more module to unload.

            These should be the same paths which were passed to `load_module`.

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        tanjun.errors.FailedModuleLoad
            If the new version of a module failed to load.

            This includes if it failed to import or if one of its loaders raised.
            The source error can be found at `tanjun.errors.FailedModuleLoad.__source__`.
        tanjun.errors.FailedModuleUnload
            If the old version of a module failed to unload.

            This indicates that one of its unloaders raised. The source
            error can be found at `tanjun.errors.FailedModuleUnload.__source__`.
        tanjun.errors.ModuleStateConflict
            If the module hasn't been loaded.
        tanjun.errors.ModuleMissingLoaders
            If no unloaders are found in the current state of the module.
            If no loaders are found in the new state of the module.
        ModuleNotFoundError
            If the module can no-longer be found at the provided path.
        """

    @abc.abstractmethod
    async def reload_modules_async(self, *modules: typing.Union[str, pathlib.Path]) -> None:
        """Asynchronous variant of `Client.reload_modules`.

        Unlike `Client.reload_modules`, this method will run blocking code in a
        background thread.

        For more information on the behaviour of this method see the
        documentation for `Client.reload_modules`.
        """

    @abc.abstractmethod
    def set_type_dependency(self: _ClientT, type_: type[_T], value: _T, /) -> _ClientT:
        """Set a callback to be called to resolve a injected type.

        Parameters
        ----------
        type_: type[_T]
            The type of the dependency to add an implementation for.
        value: _T
            The value of the dependency.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> typing.Union[_T, alluka.Undefined]:
        """Get the implementation for an injected type.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        _T | alluka.abc.Undefined
            The resolved type if found, else `Undefined`.
        """

    @abc.abstractmethod
    def remove_type_dependency(self: _ClientT, type_: type[typing.Any], /) -> _ClientT:
        """Remove a type dependency.

        Parameters
        ----------
        type_: type
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
    def set_callback_override(
        self: _ClientT, callback: alluka.CallbackSig[_T], override: alluka.CallbackSig[_T], /
    ) -> _ClientT:
        """Override a specific injected callback.

        Parameters
        ----------
        callback: alluka.abc.CallbackSig[_T]
            The injected callback to override.
        override: alluka.abc.CallbackSig[_T]
            The callback to use instead.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """

    @abc.abstractmethod
    def get_callback_override(self, callback: alluka.CallbackSig[_T], /) -> typing.Optional[alluka.CallbackSig[_T]]:
        """Get the override for a specific injected callback.

        Parameters
        ----------
        callback : alluka.abc.CallbackSig[_T]
            The injected callback to get the override for.

        Returns
        -------
        alluka.abc.CallbackSig[_T] | None
            The override if found, else `None`.
        """

    @abc.abstractmethod
    def remove_callback_override(self: _ClientT, callback: alluka.CallbackSig[_T], /) -> _ClientT:
        """Remove a callback override.

        Parameters
        ----------
        callback: alluka.abc.CallbackSig
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
        client : Client
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
        client : Client
            The client to unload commands and listeners from.

        Returns
        -------
        bool
            Whether anything was unloaded.
        """
