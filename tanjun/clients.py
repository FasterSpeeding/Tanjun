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

__all__: list[str] = [
    "as_loader",
    "Client",
    "ClientCallbackNames",
    "LoadableSig",
    "MessageAcceptsEnum",
    "PrefixGetterSig",
    "PrefixGetterSigT",
]

import asyncio
import enum
import functools
import importlib
import importlib.abc as importlib_abc
import importlib.util as importlib_util
import inspect
import itertools
import logging
import typing
from collections import abc as collections

import hikari
from hikari import traits as hikari_traits

from . import _backoff as backoff
from . import abc as tanjun_abc
from . import checks
from . import context
from . import errors
from . import injecting
from . import utilities

if typing.TYPE_CHECKING:
    import pathlib
    import types

    _ClientT = typing.TypeVar("_ClientT", bound="Client")
    _T = typing.TypeVar("_T")

    class _MessageContextMakerProto(typing.Protocol):
        def __call__(
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
        ) -> context.MessageContext:
            raise NotImplementedError

    class _SlashContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun_abc.Client,
            injection_client: injecting.InjectorClient,
            interaction: hikari.CommandInteraction,
            *,
            command: typing.Optional[tanjun_abc.BaseSlashCommand] = None,
            component: typing.Optional[tanjun_abc.Component] = None,
            default_to_ephemeral: bool = False,
            not_found_message: typing.Optional[str] = None,
        ) -> context.SlashContext:
            raise NotImplementedError


LoadableSig = collections.Callable[["Client"], None]
"""Type hint of the callback used to load resources into a Tanjun client.

This should take one positional argument of type `Client` and return nothing.
This will be expected to initiate and resources like components to the client
through the use of it's protocol methods.
"""

PrefixGetterSig = collections.Callable[..., collections.Awaitable[collections.Iterable[str]]]
"""Type hint of a callable used to get the prefix(es) for a specific guild.

This should be an asynchronous callable which returns an iterable of strings.

.. note::
    While dependency injection is supported for this, the first positional
    argument will always be a `tanjun.abc.MessageContext`.
"""

PrefixGetterSigT = typing.TypeVar("PrefixGetterSigT", bound="PrefixGetterSig")

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun.clients")


class _LoadableDescriptor:  # Slots mess with functools.update_wrapper
    def __init__(self, callback: LoadableSig, /) -> None:
        self._callback = callback
        functools.update_wrapper(self, callback)

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._callback(*args, **kwargs)


def as_loader(callback: LoadableSig, /) -> LoadableSig:
    """Mark a callback as being used to load Tanjun utilities from a module.

    Parameters
    ----------
    callback : LoadableSig
        The callback used to load Tanjun utilities from a module. This
        should take one argument of type `tanjun.abc.Client`, return nothing
        and will be expected to initiate and add utilities such as components
        to the provided client using it's abstract methods.

    Returns
    -------
    LoadableSig
        The decorated load callback.
    """
    return _LoadableDescriptor(callback)


class ClientCallbackNames(str, enum.Enum):
    """Enum of the client callback names dispatched by the standard `Client`."""

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

    MESSAGE_COMMAND_NOT_FOUND = "message_command_not_found"
    """Called when a message command is not found.

    `tanjun.abc.MessageContext` is provided as the first positional argument.
    """

    SLASH_COMMAND_NOT_FOUND = "slash_command_not_found"
    """Called when a slash command is not found.

    `tanjun.abc.MessageContext` is provided as the first positional argument.
    """

    STARTED = "started"
    """Called when the client has finished starting.

    No positional arguments are provided for this event.
    """

    STARTING = "starting"
    """Called when the client is initially instructed to start.

    No positional arguments are provided for this event.
    """


class MessageAcceptsEnum(str, enum.Enum):
    """The possible configurations for which events `Client` should execute commands based on."""

    ALL = "ALL"
    """Set the client to execute commands based on both DM and guild message create events."""

    DM_ONLY = "DM_ONLY"
    """Set the client to execute commands based only DM message create events."""

    GUILD_ONLY = "GUILD_ONLY"
    """Set the client to execute commands based only guild message create events."""

    NONE = "NONE"
    """Set the client to not execute commands based on message create events."""

    def get_event_type(self) -> typing.Optional[type[hikari.MessageCreateEvent]]:
        """Get the base event type this mode listens to.

        Returns
        -------
        typing.Optional[type[hikari.message_events.MessageCreateEvent]]
            The type object of the MessageCreateEvent class this mode will
            register a listener for.

            This will be `None` if this mode disables listening to
            message create events.
        """
        return _ACCEPTS_EVENT_TYPE_MAPPING[self]


_ACCEPTS_EVENT_TYPE_MAPPING: dict[MessageAcceptsEnum, typing.Optional[type[hikari.MessageCreateEvent]]] = {
    MessageAcceptsEnum.ALL: hikari.MessageCreateEvent,
    MessageAcceptsEnum.DM_ONLY: hikari.DMMessageCreateEvent,
    MessageAcceptsEnum.GUILD_ONLY: hikari.GuildMessageCreateEvent,
    MessageAcceptsEnum.NONE: None,
}


def _check_human(ctx: tanjun_abc.Context, /) -> bool:
    return ctx.is_human


async def _wrap_client_callback(
    callback: injecting.CallbackDescriptor[None],
    ctx: injecting.AbstractInjectionContext,
    args: tuple[str, ...],
    kwargs: dict[str, typing.Any],
    suppress_exceptions: bool,
) -> None:
    try:
        await callback.resolve(ctx, *args, **kwargs)

    except Exception as exc:
        if suppress_exceptions:
            _LOGGER.error("Client callback raised exception", exc_info=exc)

        else:
            raise


class _InjectablePrefixGetter(injecting.BaseInjectableCallback[collections.Iterable[str]]):
    __slots__ = ()

    def __init__(self, callback: PrefixGetterSig, /) -> None:
        super().__init__(callback)

    async def __call__(self, ctx: tanjun_abc.Context, /) -> collections.Iterable[str]:
        return await self.descriptor.resolve_with_command_context(ctx)

    @property
    def callback(self) -> PrefixGetterSig:
        return typing.cast(PrefixGetterSig, self.descriptor.callback)


class _InjectableListener(injecting.BaseInjectableCallback[None]):
    __slots__ = ("_injector_client",)

    def __init__(self, injector_client: injecting.InjectorClient, callback: tanjun_abc.ListenerCallbackSig, /) -> None:
        super().__init__(callback)
        self._injector_client = injector_client

    async def __call__(self, event: hikari.Event) -> None:
        ctx = injecting.BasicInjectionContext(self._injector_client)
        await self.descriptor.resolve(ctx, event)


class Client(injecting.InjectorClient, tanjun_abc.Client):
    """Tanjun's standard `tanjun.abc.Client` implementation.

    This implementation supports dependency injection for checks, command
    callbacks, and prefix getters. For more information on how
    this works see `tanjun.injector`.

    Notes
    -----
    * For a quicker way to initiate this client around a standard bot aware
      client, see `Client.from_gateway_bot` and `Client.from_rest_bot`.
    * The endpoint used by `set_global_commands` has a strict ratelimit which,
      as of writing, only allows for 2 request per minute (with that ratelimit
      either being per-guild if targeting a specific guild otherwise globally).
    * `event_manager` is necessary for message command dispatch and will also
      be necessary for interaction command dispatch if `server` isn't
      provided.
    * `server` is used for interaction command dispatch if interaction
      events aren't being received from the event manager.

    Parameters
    ----------
    rest : hikari.api.rest.RestClient
        The Hikari REST client this will use.

    Other Parameters
    ----------------
    cache : hikari.api.cache.CacheClient
        The Hikari cache client this will use if applicable.
    event_manager : hikari.api.event_manager.EventManagerClient
        The Hikari event manager client this will use if applicable.
    server : hikari.api.interaction_server.InteractionServer
        The Hikari interaction server client this will use if applicable.
    shard : hikari.traits.ShardAware
        The Hikari shard aware client this will use if applicable.
    event_managed : bool
        Whether or not this client is managed by the event manager.

        An event managed client will be automatically started and closed based
        on Hikari's lifetime events.

        Defaults to `False` and can only be passed as `True` if `event_manager`
        is also provided.
    mention_prefix : bool
        Whether or not mention prefixes should be automatically set when this
        client is first started.

        Defaults to `False` and it should be noted that this only applies to
        message commands.
    set_global_commands : typing.Union[hikari.Snowflake, bool]
        Whether or not to automatically set global slash commands when this
        client is first started. Defaults to `False`.

        If a snowflake ID is passed here then the global commands will be
        set on this specific guild at startup rather than globally. This
        can be useful for testing/debug purposes as slash commands may take
        up to an hour to propagate globally but will immediately propagate
        when set on a specific guild.

    Raises
    ------
    ValueError
        If `event_managed` is `True` when `event_manager` is `None`.
    """

    __slots__ = (
        "_accepts",
        "_auto_defer_after",
        "_cache",
        "_cached_application_id",
        "_checks",
        "_client_callbacks",
        "_components",
        "_make_message_context",
        "_make_slash_context",
        "_events",
        "_grab_mention_prefix",
        "_hooks",
        "_interaction_not_found",
        "_slash_hooks",
        "_is_alive",
        "_is_closing",
        "_listeners",
        "_message_hooks",
        "_metadata",
        "_prefix_getter",
        "_prefixes",
        "_rest",
        "_server",
        "_shards",
    )

    def __init__(
        self,
        rest: hikari.api.RESTClient,
        *,
        cache: typing.Optional[hikari.api.Cache] = None,
        events: typing.Optional[hikari.api.EventManager] = None,
        server: typing.Optional[hikari.api.InteractionServer] = None,
        shard: typing.Optional[hikari_traits.ShardAware] = None,
        event_managed: bool = False,
        mention_prefix: bool = False,
        set_global_commands: typing.Union[hikari.Snowflake, bool] = False,
    ) -> None:
        # InjectorClient.__init__
        super().__init__()
        # TODO: logging or something to indicate this is running statelessly rather than statefully.
        # TODO: warn if server and dispatch both None but don't error

        # TODO: separate slash and gateway checks?
        self._accepts = MessageAcceptsEnum.ALL if events else MessageAcceptsEnum.NONE
        self._auto_defer_after: typing.Optional[float] = 2.0
        self._cache = cache
        self._cached_application_id: typing.Optional[hikari.Snowflake] = None
        self._checks: set[checks.InjectableCheck] = set()
        self._client_callbacks: dict[str, set[injecting.CallbackDescriptor[None]]] = {}
        self._components: set[tanjun_abc.Component] = set()
        self._make_message_context: _MessageContextMakerProto = context.MessageContext
        self._make_slash_context: _SlashContextMakerProto = context.SlashContext
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self._hooks: typing.Optional[tanjun_abc.AnyHooks] = None
        self._interaction_not_found: typing.Optional[str] = "Command not found"
        self._slash_hooks: typing.Optional[tanjun_abc.SlashHooks] = None
        self._is_alive = False
        self._is_closing = False
        self._listeners: dict[type[hikari.Event], set[_InjectableListener]] = {}
        self._message_hooks: typing.Optional[tanjun_abc.MessageHooks] = None
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._prefix_getter: typing.Optional[_InjectablePrefixGetter] = None
        self._prefixes: set[str] = set()
        self._rest = rest
        self._server = server
        self._shards = shard

        if event_managed:
            if not events:
                raise ValueError("Client cannot be event managed without an event manager")

            events.subscribe(hikari.StartingEvent, self._on_starting_event)
            events.subscribe(hikari.StoppingEvent, self._on_stopping_event)

        if set_global_commands:

            async def _set_global_commands_next_start() -> None:
                guild = (
                    hikari.UNDEFINED if isinstance(set_global_commands, bool) else hikari.Snowflake(set_global_commands)
                )
                await self.set_global_commands(guild=guild)
                self.remove_client_callback(ClientCallbackNames.STARTING, _set_global_commands_next_start)

            self.add_client_callback(
                ClientCallbackNames.STARTING,
                _set_global_commands_next_start,
            )

        self.set_type_special_case(hikari.api.RESTClient, rest)
        self.set_type_special_case(type(rest), rest)
        if cache:
            self.set_type_special_case(hikari.api.Cache, cache)
            self.set_type_special_case(type(cache), cache)

        if events:
            self.set_type_special_case(hikari.api.EventManager, events)
            self.set_type_special_case(type(events), events)

        if server:
            self.set_type_special_case(hikari.api.InteractionServer, server)
            self.set_type_special_case(type(server), server)

        if shard:
            self.set_type_special_case(hikari_traits.ShardAware, shard)
            self.set_type_special_case(type(shard), shard)

    @classmethod
    def from_gateway_bot(
        cls,
        bot: hikari_traits.GatewayBotAware,
        /,
        *,
        event_managed: bool = True,
        mention_prefix: bool = False,
        set_global_commands: typing.Union[hikari.Snowflake, bool] = False,
    ) -> Client:
        """Build a `Client` from a `hikari.traits.GatewayBotAware` instance.

        Notes
        -----
        * This implicitly defaults the client to human only mode and also
          sets hikari trait injectors based on `bot`.
        * The endpoint used by `set_global_commands` has a strict ratelimit
          which, as of writing, only allows for 2 request per minute (with that
          ratelimit either being per-guild if targeting a specific guild
          otherwise globally).

        Parameters
        ----------
        bot : hikari.traits.GatewayBotAware
            The bot client to build from.

            This will be used to infer the relevant Hikari clients to use.

        Other Parameters
        ----------------
        event_managed : bool
            Whether or not this client is managed by the event manager.

            An event managed client will be automatically started and closed
            based on Hikari's lifetime events.

            Defaults to `True`.
        mention_prefix : bool
            Whether or not mention prefixes should be automatically set when this
            client is first started.

            Defaults to `False` and it should be noted that this only applies to
            message commands.
        set_global_commands : typing.Union[hikari.Snowflake, bool] bool
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If a snowflake ID is passed here then the global commands will be
            set on this specific guild at startup rather than globally. This
            can be useful for testing/debug purposes as slash commands may take
            up to an hour to propagate globally but will immediately propagate
            when set on a specific guild.
        """
        return (
            cls(
                rest=bot.rest,
                cache=bot.cache,
                events=bot.event_manager,
                shard=bot,
                event_managed=event_managed,
                mention_prefix=mention_prefix,
                set_global_commands=set_global_commands,
            )
            .set_human_only()
            .set_hikari_trait_injectors(bot)
        )

    @classmethod
    def from_rest_bot(
        cls,
        bot: hikari_traits.RESTBotAware,
        /,
        set_global_commands: typing.Union[hikari.Snowflake, bool] = False,
    ) -> Client:
        """Build a `Client` from a `hikari.traits.RESTBotAware` instance.

        Notes
        -----
        * This implicitly sets hikari trait injectors based on `bot`.
        * The endpoint used by `set_global_commands` has a strict ratelimit
          which, as of writing, only allows for 2 request per minute (with that
          ratelimit either being per-guild if targeting a specific guild
          otherwise globally).

        Parameters
        ----------
        bot : hikari.traits.RESTBotAware
            The bot client to build from.

        Other Parameters
        ----------------
        set_global_commands : typing.Union[hikari.Snowflake, bool] bool
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If a snowflake ID is passed here then the global commands will be
            set on this specific guild at startup rather than globally. This
            can be useful for testing/debug purposes as slash commands may take
            up to an hour to propagate globally but will immediately propagate
            when set on a specific guild.
        """
        return cls(
            rest=bot.rest, server=bot.interaction_server, set_global_commands=set_global_commands
        ).set_hikari_trait_injectors(bot)

    async def __aenter__(self) -> Client:
        await self.open()
        return self

    async def __aexit__(
        self,
        exception_type: typing.Optional[type[BaseException]],
        exception: typing.Optional[BaseException],
        exception_traceback: typing.Optional[types.TracebackType],
    ) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"CommandClient <{type(self).__name__!r}, {len(self._components)} components, {self._prefixes}>"

    @property
    def message_accepts(self) -> MessageAcceptsEnum:
        """Type of message create events this command client accepts for execution."""
        return self._accepts

    @property
    def is_human_only(self) -> bool:
        """Whether this client is only executing for non-bot/webhook users messages."""
        return _check_human in self._checks  # type: ignore[comparison-overlap]

    @property
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._cache

    @property
    def checks(self) -> collections.Set[tanjun_abc.CheckSig]:
        """Set of the top level `tanjun.abc.Context` checks registered to this client.

        Returns
        -------
        collections.abc.Set[tanjun.abc.CheckSig]
            Set of the `tanjun.abc.Context` based checks registered for
            this client.

            These may be taking advantage of the standard dependency injection.
        """
        return {check.callback for check in self._checks}

    @property
    def components(self) -> collections.Set[tanjun_abc.Component]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._components.copy()

    @property
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._events

    @property
    def listeners(
        self,
    ) -> collections.Mapping[type[hikari.Event], collections.Collection[tanjun_abc.ListenerCallbackSig]]:
        return utilities.CastedView(self._listeners, lambda x: x.copy())

    @property
    def hooks(self) -> typing.Optional[tanjun_abc.AnyHooks]:
        """Top level `tanjun.abc.AnyHooks` set for this client.

        These are called during both message and interaction command execution.

        Returns
        -------
        typing.Optional[tanjun.abc.AnyHooks]
            The top level `tanjun.abc.Context` based hooks set for this
            client if applicable, else `None`.
        """
        return self._hooks

    @property
    def slash_hooks(self) -> typing.Optional[tanjun_abc.SlashHooks]:
        """Top level `tanjun.abc.SlashHooks` set for this client.

        These are only called during interaction command execution.

        Returns
        -------
        typing.Optional[tanjun.abc.SlashHooks]
            The top level `tanjun.abc.SlashContext` based hooks set
            for this client.
        """
        return self._slash_hooks

    @property
    def is_alive(self) -> bool:
        """Whether this client is alive."""
        return self._is_alive

    @property
    def message_hooks(self) -> typing.Optional[tanjun_abc.MessageHooks]:
        """Get the top level `tanjun.abc.MessageHooks` set for this client.

        These are only called during both message command execution.

        Returns
        -------
        typing.Optional[tanjun.abc.MessageHooks]
            The top level `tanjun.abc.MessageContext` based hooks set for
            this client.
        """
        return self._message_hooks

    @property
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._metadata

    @property
    def prefix_getter(self) -> typing.Optional[PrefixGetterSig]:
        """Get the prefix getter method set for this client.

        Returns
        -------
        typing.Optional[PrefixGetterSig]
            The prefix getter method set for this client if applicable,
            else `None`.

            For more information on this callback's signature see `PrefixGetter`.
        """
        return self._prefix_getter.callback if self._prefix_getter else None

    @property
    def prefixes(self) -> collections.Collection[str]:
        """Set of the standard prefixes set for this client.

        Returns
        -------
        collections.abc.Set[str]
            The standard prefixes set for this client.
        """
        return self._prefixes.copy()

    @property
    def rest(self) -> hikari.api.RESTClient:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._rest

    @property
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._server

    @property
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._shards

    async def _on_starting_event(self, _: hikari.StartingEvent, /) -> None:
        await self.open()

    async def _on_stopping_event(self, _: hikari.StoppingEvent, /) -> None:
        await self.close()

    async def declare_slash_command(
        self,
        command: tanjun_abc.BaseSlashCommand,
        /,
        command_id: typing.Optional[hikari.Snowflake] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.Command:
        """Declare a single slash command for a bot.

        Parameters
        ----------
        command : tanjun.abc.BaseSlashCommand
            The command to register.

        Other Parameters
        ----------------
        application : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialApplication]]
            The application to register the command with.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        command_id : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.interactions.commands.Command]]
            Object or ID of the command to update.
        guild : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialGuild]]
            Object or ID of the guild to register the command with.

            If left as `None` then the command will be registered globally.

        Warnings
        --------
        * This ignores any ID that's been set on `tanjun.abc.BaseSlashCommand`.
        * Providing `command_id` when updating a command helps avoid any
          permissions set for the command being lose (e.g. when changing the
          command's name).

        Returns
        -------
        hikari.interactions.commands.Command
            API representation of the command that was registered.
        """
        builder = command.build()
        if command_id:
            response = await self._rest.create_application_command(
                application or self._cached_application_id or await self.fetch_rest_application_id(),
                guild=guild,
                name=builder.name,
                description=builder.description,
                options=builder.options,
            )

        else:
            response = await self._rest.create_application_command(
                application or self._cached_application_id or await self.fetch_rest_application_id(),
                guild=guild,
                name=builder.name,
                description=builder.description,
                options=builder.options,
            )

        if not guild:
            command.set_tracked_command(response)  # TODO: is this fine?
        return response

    async def declare_slash_commands(
        self,
        commands: collections.Iterable[tanjun_abc.BaseSlashCommand],
        /,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> collections.Sequence[hikari.Command]:
        """Declare a collection of slash commands for a bot.

        .. note::
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 request per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Parameters
        ----------
        commands : collections.abc.Iterable[tanjun.abc.BaseSlashCommand]
            Iterable of the commands to register.

        Other Parameters
        ----------------
        application : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialApplication]]
            The application to register the commands with.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialGuild]]
            Object or ID of the guild to register the commands with.

            If left as `None` then the commands will be registered globally.

        Returns
        -------
        collections.abc.Sequence[hikari.interactions.commands.Command]
            API representations of the commands which were registered.
        """
        names_to_commands: dict[str, tanjun_abc.BaseSlashCommand] = {}
        found_top_names: set[str] = set()
        conflicts: set[str] = set()
        builders: list[hikari.api.CommandBuilder] = []

        for command in commands:
            names_to_commands[command.name] = command
            if command.name in found_top_names:
                conflicts.add(command.name)

            found_top_names.add(command.name)
            builders.append(command.build())

        if conflicts:
            raise RuntimeError(
                "Couldn't declare commands due to conflicts. The following command names have more than one command "
                "registered for them " + ", ".join(conflicts)
            )

        if not application:
            application = self._cached_application_id or await self.fetch_rest_application_id()

        responses = await self._rest.set_application_commands(application, builders, guild=guild)
        for response in responses:
            command = names_to_commands[response.name]
            if not guild:
                command.set_tracked_command(response)  # TODO: is this fine?

        return responses

    def set_auto_defer_after(self: _ClientT, time: typing.Optional[float], /) -> _ClientT:
        """Set when this client should automatically defer execution of commands.

        .. warning::
            If `time` is set to `None` then automatic deferrals will be disabled.
            This may lead to unexpected behaviour.

        Parameters
        ----------
        time : typing.Optional[float]
            The time in seconds to defer interaction command responses after.
        """
        self._auto_defer_after = float(time) if time is not None else None
        return self

    def set_hikari_trait_injectors(self: _ClientT, bot: hikari_traits.RESTAware, /) -> _ClientT:
        """Set type based dependency injection based on the hikari traits found in `bot`.

        This is a short hand for calling `Client.add_type_dependency` for all
        the hikari trait types `bot` is valid for with bot.

        Parameters
        ----------
        bot : hikari_traits.RESTAware
            The hikari client to set dependency injectors for.
        """
        for _, member in inspect.getmembers(hikari_traits):
            if inspect.isclass(member) and isinstance(bot, member):
                self.set_type_special_case(member, bot)

        return self

    def set_interaction_not_found(self: _ClientT, message: typing.Optional[str], /) -> _ClientT:
        """Set the response message for when an interaction command is not found.

        .. warning::
            Setting this to `None` may lead to unexpected behaviour (especially
            when the client is still set to auto-defer interactions) and should
            only be done if you know what you're doing.

        Parameters
        ----------
        message : typing.Optional[str]
            The message to respond with when an interaction command isn't found.
        """
        self._interaction_not_found = message
        return self

    def set_message_accepts(self: _ClientT, accepts: MessageAcceptsEnum, /) -> _ClientT:
        """Set the kind of messages commands should be executed based on.

        Parameters
        ----------
        accepts : MessageAcceptsEnum
            The type of messages commands should be executed based on.
        """
        if accepts.get_event_type() and not self._events:
            raise ValueError("Cannot set accepts level on a client with no event manager")

        self._accepts = accepts
        return self

    def set_message_ctx_maker(self: _ClientT, maker: _MessageContextMakerProto = context.MessageContext, /) -> _ClientT:
        """Set the message context maker to use when creating context for a message.

        .. warning::
            The caller must return an instance of `tanjun.context.MessageContext`
            rather than just any implementation of the MessageContext abc due to
            this client relying on implementation detail of
            `tanjun.context.MessageContext`.

        Parameters
        ----------
        maker : _MessageContextMakerProto
            The message context maker to use.

            This is a callback which should match the signature of
            `tanjun.context.MessageContext.__init__` and return an instance
            of `tanjun.context.MessageContext`.

            This defaults to `tanjun.context.MessageContext`.
        """
        self._make_message_context = maker
        return self

    def set_slash_ctx_maker(self: _ClientT, maker: _SlashContextMakerProto = context.SlashContext, /) -> _ClientT:
        """Set the slash context maker to use when creating context for a slash command.

        .. warning::
            The caller must return an instance of `tanjun.context.SlashContext`
            rather than just any implementation of the SlashContext abc due to
            this client relying on implementation detail of
            `tanjun.context.SlashContext`.

        Parameters
        ----------
        maker : _SlashContextMakerProto
            The slash context maker to use.

            This is a callback which should match the signature of
            `tanjun.context.SlashContext.__init__` and return an instance
            of `tanjun.context.SlashContext`.

            This defaults to `tanjun.context.SlashContext`.
        """
        self._make_slash_context = maker
        return self

    def set_human_only(self: _ClientT, value: bool = True) -> _ClientT:
        """Set whether or not message commands execution should be limited to "human" users.

        .. note::
            This doesn't apply to interaction commands as these can only be
            triggered by a "human" (normal user account).

        Parameters
        ----------
        value : bool
            Whether or not message commands execution should be limited to "human" users.

            Passing `True` here will prevent message commands from being executed
            based on webhook and bot messages.
        """
        if value:
            self.add_check(checks.InjectableCheck(_check_human))

        else:
            try:
                self.remove_check(_check_human)
            except ValueError:
                pass

        return self

    async def clear_commands(
        self,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> None:
        """Clear the commands declared either globally or for a specific guild.

        .. note::
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 request per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Other Parameters
        ----------------
        application : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialApplication]]
            The application to clear commands for.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : hikari.UndefinedOr[hikari.snowflakes.SnowflakeishOr[hikari.PartialGuild]]
            Object or ID of the guild to clear commands for.

            If left as `None` global commands will be cleared.
        """
        if application is None:
            application = self._cached_application_id or await self.fetch_rest_application_id()

        await self._rest.set_application_commands(application, (), guild=guild)

    async def set_global_commands(
        self,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> collections.Sequence[hikari.Command]:
        """Set the global application commands for a bot based on the loaded components.

        .. warning::
            This will overwrite any previously set application commands and
            only targets commands marked as global.

        Notes
        -----
        * The endpoint this uses has a strict ratelimit which, as of writing,
          only allows for 2 request per minute (with that ratelimit either
          being per-guild if targeting a specific guild otherwise globally).
        * Setting a specific `guild` can be useful for testing/debug purposes
          as slash commands may take up to an hour to propagate globally but
          will immediately propagate when set on a specific guild.

        Other Parameters
        ----------------
        application : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialApplication]]
            Object or ID of the application to set the global commands for.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : hikari.UndefinedOr[hikari.snowflakes.SnowflakeishOr[hikari.PartialGuild]]
            Object or ID of the guild to set the global commands to.

            If left as `None` global commands will be set.

        Returns
        -------
        collections.abc.Sequence[hikari.interactions.command.Command]
            API representations of the set commands.
        """
        commands = (
            command
            for command in itertools.chain.from_iterable(component.slash_commands for component in self._components)
            if command.is_global
        )
        return await self.declare_slash_commands(commands, application=application, guild=guild)

    def add_check(self: _ClientT, check: tanjun_abc.CheckSig, /) -> _ClientT:
        self._checks.add(checks.InjectableCheck(check))
        return self

    def remove_check(self, check: tanjun_abc.CheckSig, /) -> None:
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: tanjun_abc.CheckSigT, /) -> tanjun_abc.CheckSigT:
        self.add_check(check)
        return check

    async def check(self, ctx: tanjun_abc.Context, /) -> bool:
        return await utilities.gather_checks(ctx, self._checks)

    def add_component(self: _ClientT, component: tanjun_abc.Component, /, *, add_injector: bool = False) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        component.bind_client(self)
        self._components.add(component)

        if add_injector:
            self.set_type_dependency(type(component), lambda: component)

        if self._is_alive:
            asyncio.get_running_loop().create_task(
                self.dispatch_client_callback(ClientCallbackNames.COMPONENT_ADDED, component)
            )

        return self

    def remove_component(self, component: tanjun_abc.Component, /) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._components.remove(component)
        component.unbind_client(self)

        if self._is_alive:
            asyncio.get_running_loop().create_task(
                self.dispatch_client_callback(ClientCallbackNames.COMPONENT_REMOVED, component)
            )

    def add_client_callback(self: _ClientT, event_name: str, callback: tanjun_abc.MetaEventSig, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        descriptor = injecting.CallbackDescriptor(callback)
        event_name = event_name.lower()
        try:
            self._client_callbacks[event_name].add(descriptor)
        except KeyError:
            self._client_callbacks[event_name] = {descriptor}

        return self

    async def dispatch_client_callback(
        self, event_name: str, /, *args: typing.Any, suppress_exceptions: bool = True, **kwargs: typing.Any
    ) -> None:
        event_name = event_name.lower()
        if callbacks := self._client_callbacks.get(event_name):
            calls = (
                _wrap_client_callback(
                    callback, injecting.BasicInjectionContext(self), args, kwargs, suppress_exceptions
                )
                for callback in callbacks
            )
            await asyncio.gather(*calls)

    def get_client_callbacks(self, event_name: str, /) -> collections.Collection[tanjun_abc.MetaEventSig]:
        # <<inherited docstring from tanjun.abc.Client>>.
        event_name = event_name.lower()
        if result := self._client_callbacks.get(event_name):
            return tuple(callback.callback for callback in result)

        return ()

    def remove_client_callback(self, event_name: str, callback: tanjun_abc.MetaEventSig, /) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        event_name = event_name.lower()
        self._client_callbacks[event_name].remove(callback)  # type: ignore
        if not self._client_callbacks[event_name]:
            del self._client_callbacks[event_name]

    def with_client_callback(
        self, event_name: str, /
    ) -> collections.Callable[[tanjun_abc.MetaEventSigT], tanjun_abc.MetaEventSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: tanjun_abc.MetaEventSigT, /) -> tanjun_abc.MetaEventSigT:
            self.add_client_callback(event_name, callback)
            return callback

        return decorator

    def add_listener(self, event_type: type[hikari.Event], callback: tanjun_abc.ListenerCallbackSig, /) -> None:
        injected = _InjectableListener(self, callback)
        try:
            self._listeners[event_type].add(injected)

        except KeyError:
            self._listeners[event_type] = {injected}

        if self._is_alive and self._events:
            self._events.subscribe(event_type, injected)  # TODO: does this work?

    def remove_listener(self, event_type: type[hikari.Event], callback: tanjun_abc.ListenerCallbackSig, /) -> None:
        self._listeners[event_type].remove(callback)  # type: ignore
        if not self._listeners[event_type]:
            del self._listeners[event_type]

        if self._is_alive and self._events:
            self._events.unsubscribe(event_type, callback)  # TODO: does this work?

    def with_listener(
        self, event_type: type[hikari.Event], /
    ) -> collections.Callable[[tanjun_abc.ListenerCallbackSigT], tanjun_abc.ListenerCallbackSigT]:
        def decorator(callback: tanjun_abc.ListenerCallbackSigT, /) -> tanjun_abc.ListenerCallbackSigT:
            self.add_listener(event_type, callback)
            return callback

        return decorator

    def add_prefix(self: _ClientT, prefixes: typing.Union[collections.Iterable[str], str], /) -> _ClientT:
        if isinstance(prefixes, str):
            self._prefixes.add(prefixes)

        else:
            self._prefixes.update(prefixes)

        return self

    def remove_prefix(self, prefix: str, /) -> None:
        self._prefixes.remove(prefix)

    def set_prefix_getter(self: _ClientT, getter: typing.Optional[PrefixGetterSig], /) -> _ClientT:
        self._prefix_getter = _InjectablePrefixGetter(getter) if getter else None
        return self

    def with_prefix_getter(self, getter: PrefixGetterSigT, /) -> PrefixGetterSigT:
        self.set_prefix_getter(getter)
        return getter

    def check_message_context(
        self, ctx: tanjun_abc.MessageContext, /
    ) -> collections.AsyncIterator[tuple[str, tanjun_abc.MessageCommand]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return utilities.async_chain(component.check_message_context(ctx) for component in self._components)

    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, tanjun_abc.MessageCommand]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(component.check_message_name(name) for component in self._components)

    def check_slash_name(self, name: str, /) -> collections.Iterator[tanjun_abc.BaseSlashCommand]:
        return itertools.chain.from_iterable(component.check_slash_name(name) for component in self._components)

    async def _check_prefix(self, ctx: tanjun_abc.MessageContext, /) -> typing.Optional[str]:
        if self._prefix_getter:
            for prefix in await self._prefix_getter(ctx):
                if ctx.content.startswith(prefix):
                    return prefix

        for prefix in self._prefixes:
            if ctx.content.startswith(prefix):
                return prefix

        return None

    def _try_unsubscribe(
        self,
        event_manager: hikari.api.EventManager,
        event_type: type[hikari.Event],
        callback: tanjun_abc.ListenerCallbackSig,
    ) -> None:
        try:
            event_manager.unsubscribe(event_type, callback)
        except (ValueError, LookupError):
            # TODO: add logging here
            pass

    async def close(self, *, deregister_listeners: bool = True) -> None:
        if not self._is_alive:
            raise RuntimeError("Client isn't active")

        if self._is_closing:
            event = asyncio.Event()
            self.add_client_callback(ClientCallbackNames.CLOSED, event.set)
            try:
                await event.wait()
            finally:
                self.remove_client_callback(ClientCallbackNames.CLOSED, event.set)
            return

        self._is_closing = True
        await self.dispatch_client_callback(ClientCallbackNames.CLOSING)
        if deregister_listeners and self._events:
            if event_type := self._accepts.get_event_type():
                self._try_unsubscribe(self._events, event_type, self.on_message_create_event)

            self._try_unsubscribe(self._events, hikari.InteractionCreateEvent, self.on_interaction_create_event)

            for event_type, listeners in self._listeners.items():
                for listener in listeners:
                    self._try_unsubscribe(self._events, event_type, listener)

        if deregister_listeners and self._server:
            self._server.set_listener(hikari.CommandInteraction, None)

        self._is_alive = False
        await self.dispatch_client_callback(ClientCallbackNames.CLOSED)
        self._is_closing = False

    async def open(self, *, register_listeners: bool = True) -> None:
        if self._is_alive:
            raise RuntimeError("Client is already alive")

        self._is_alive = True
        self._is_closing = False
        await self.dispatch_client_callback(ClientCallbackNames.STARTING)
        if self._grab_mention_prefix:
            user: typing.Optional[hikari.User] = None
            if self._cache:
                user = self._cache.get_me()

            if not user:
                retry = backoff.Backoff(max_retries=4, maximum=30)

                async for _ in retry:
                    try:
                        user = await self._rest.fetch_my_user()
                        break

                    except (hikari.RateLimitedError, hikari.RateLimitTooLongError) as exc:
                        if exc.retry_after > 30:
                            raise

                        retry.set_next_backoff(exc.retry_after)

                    except hikari.InternalServerError:
                        continue

                else:
                    user = await self._rest.fetch_my_user()

            self._prefixes.add(f"<@{user.id}>")
            self._prefixes.add(f"<@!{user.id}>")
            self._grab_mention_prefix = False

        if register_listeners and self._events:
            if event_type := self._accepts.get_event_type():
                self._events.subscribe(event_type, self.on_message_create_event)

            self._events.subscribe(hikari.InteractionCreateEvent, self.on_interaction_create_event)

            for event_type, listeners in self._listeners.items():
                for listener in listeners:
                    self._events.subscribe(event_type, listener)

        if register_listeners and self._server:
            self._server.set_listener(hikari.CommandInteraction, self.on_interaction_create_request)

        asyncio.get_running_loop().create_task(self.dispatch_client_callback(ClientCallbackNames.STARTED))

    async def fetch_rest_application_id(self) -> hikari.Snowflake:
        if self._cached_application_id:
            return self._cached_application_id

        if self._rest.token_type == hikari.TokenType.BOT:
            application = await self._rest.fetch_application()

        else:
            application = (await self._rest.fetch_authorization()).application

        self._cached_application_id = hikari.Snowflake(application)
        return self._cached_application_id

    def set_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.AnyHooks], /) -> _ClientT:
        self._hooks = hooks
        return self

    def set_slash_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.SlashHooks], /) -> _ClientT:
        self._slash_hooks = hooks
        return self

    def set_message_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.MessageHooks], /) -> _ClientT:
        self._message_hooks = hooks
        return self

    def load_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path]) -> _ClientT:
        """Load entities into this client from modules based on loadable descriptors.

        Examples
        --------
        For this to work the module has to have at least one `as_loader`
        decorated top level function which takes one positional argument
        of type `Client`.

        ```py
        @tanjun.as_loader
        def load_component(client: tanjun.abc.Client) -> None:
            client.add_component(component.copy())
        ```

        Parameters
        ----------
        *modules
            String path(s) of the modules to load from.

        Returns
        -------
        Self
            This client instance to enable chained calls.
        """
        for module_path in modules:
            if isinstance(module_path, str):
                module = importlib.import_module(module_path)

            else:
                spec = importlib_util.spec_from_file_location(
                    module_path.name.rsplit(".", 1)[0], module_path.absolute()
                )

                # https://github.com/python/typeshed/issues/2793
                if not spec or not isinstance(spec.loader, importlib_abc.Loader):
                    raise RuntimeError(f"Unknown or invalid module provided {module_path}")

                module = importlib_util.module_from_spec(spec)
                spec.loader.exec_module(module)

            found = False
            for _, member in inspect.getmembers(module):
                if isinstance(member, _LoadableDescriptor):
                    member(self)
                    found = True

            if not found:
                _LOGGER.warning("Didn't find any loadable descriptors in %s", module_path)

        return self

    async def on_message_create_event(self, event: hikari.MessageCreateEvent, /) -> None:
        """Execute a message command based on a gateway event.

        Parameters
        ----------
        hikari.events.message_events.MessageCreateEvent
            The event to handle.
        """
        if event.message.content is None:
            return

        ctx = self._make_message_context(
            client=self, injection_client=self, content=event.message.content, message=event.message
        )
        if (prefix := await self._check_prefix(ctx)) is None:
            return

        ctx.set_content(ctx.content.lstrip()[len(prefix) :].lstrip()).set_triggering_prefix(prefix)
        if not await self.check(ctx):
            return

        hooks: typing.Optional[set[tanjun_abc.MessageHooks]] = None
        if self._hooks and self._message_hooks:
            hooks = {self._hooks, self._message_hooks}

        elif self._hooks:
            hooks = {self._hooks}

        elif self._message_hooks:
            hooks = {self._message_hooks}

        try:
            for component in self._components:
                if await component.execute_message(ctx, hooks=hooks):
                    break

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            await ctx.respond(exc.message)
            return

        await self.dispatch_client_callback(ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx)

    def _get_slash_hooks(self) -> typing.Optional[set[tanjun_abc.SlashHooks]]:
        hooks: typing.Optional[set[tanjun_abc.SlashHooks]] = None
        if self._hooks and self._slash_hooks:
            hooks = {self._hooks, self._slash_hooks}

        elif self._hooks:
            hooks = {self._hooks}

        elif self._slash_hooks:
            hooks = {self._slash_hooks}

        return hooks

    async def on_interaction_create_event(self, event: hikari.InteractionCreateEvent, /) -> None:
        """Execute a slash command based on Gateway events.

        .. note::
            Any event where `event.interaction` is not
            `hikari.interactions.commands.CommandInteraction` will be ignored.

        Parameters
        ----------
        event : hikari.events.interaction_events.InteractionCreateEvent
            The event to execute commands based on.
        """
        if not isinstance(event.interaction, hikari.CommandInteraction):
            return

        ctx = self._make_slash_context(
            client=self,
            injection_client=self,
            interaction=event.interaction,
            not_found_message=self._interaction_not_found,
        )
        hooks = self._get_slash_hooks()

        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        try:
            for component in self._components:
                if future := await component.execute_interaction(ctx, hooks=hooks):
                    await future
                    return

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            await ctx.respond(exc.message)
            return

        await self.dispatch_client_callback(ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)
        await ctx.mark_not_found()
        ctx.cancel_defer()

    async def on_interaction_create_request(self, interaction: hikari.CommandInteraction, /) -> context.ResponseTypeT:
        """Execute a slash command based on received REST requests.

        Parameters
        ----------
        interaction : hikari.interactions.commands.CommandInteraction
            The interaction to execute a command based on.

        Returns
        -------
        tanjun.context.ResponseType
            The initial response to send back to Discord.
        """
        ctx = self._make_slash_context(
            client=self, injection_client=self, interaction=interaction, not_found_message=self._interaction_not_found
        )
        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        hooks = self._get_slash_hooks()
        future = ctx.get_response_future()
        try:
            for component in self._components:
                if await component.execute_interaction(ctx, hooks=hooks):
                    return await future

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            # Under very specific timing there may be another future which could set a result while we await
            # ctx.respond therefore we create a task to avoid any erroneous behaviour from this trying to create
            # another response before it's returned the initial response.
            asyncio.get_running_loop().create_task(ctx.respond(exc.message))
            return await future

        async def callback(_: asyncio.Future[None]) -> None:
            await ctx.mark_not_found()
            ctx.cancel_defer()

        asyncio.get_running_loop().create_task(
            self.dispatch_client_callback(ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)
        ).add_done_callback(callback)
        return await future
