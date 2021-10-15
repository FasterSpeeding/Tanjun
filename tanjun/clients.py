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
"""Standard Tanjun client."""
from __future__ import annotations

__all__: list[str] = [
    "as_loader",
    "as_unloader",
    "Client",
    "ClientCallbackNames",
    "LoaderSig",
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
import warnings
from collections import abc as collections

import hikari
from hikari import traits as hikari_traits

from . import abc as tanjun_abc
from . import checks
from . import context
from . import dependencies
from . import errors
from . import hooks
from . import injecting
from . import utilities

if typing.TYPE_CHECKING:
    import pathlib
    import types

    _ClientT = typing.TypeVar("_ClientT", bound="Client")

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
            on_not_found: typing.Optional[
                collections.Callable[[context.SlashContext], collections.Awaitable[None]]
            ] = None,
        ) -> context.SlashContext:
            raise NotImplementedError


LoaderSig = collections.Callable[["Client"], None]
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


class _LoaderDescriptor:  # Slots mess with functools.update_wrapper
    def __init__(self, callback: LoaderSig, /) -> None:
        self._callback = callback
        functools.update_wrapper(self, callback)

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._callback(*args, **kwargs)


class _UnloaderDescriptor:  # Slots mess with functools.update_wrapper
    def __init__(self, callback: LoaderSig, /) -> None:
        self._callback = callback
        functools.update_wrapper(self, callback)

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._callback(*args, **kwargs)


def as_loader(callback: LoaderSig, /) -> LoaderSig:
    """Mark a callback as being used to load Tanjun components from a module.

    .. note::
        This is only necessary if you wish to use `tanjun.Client.load_modules`.

    Parameters
    ----------
    callback : LoaderSig
        The callback used to load Tanjun components from a module. This
        should take one argument of type `tanjun.Client`, return nothing
        and will be expected to initiate and add utilities such as components
        to the provided client using it's abstract methods.

    Returns
    -------
    LoaderSig
        The decorated load callback.
    """
    return _LoaderDescriptor(callback)


def as_unloader(callback: LoaderSig, /) -> LoaderSig:
    """Mark a callback as being used to unload a module's utilities from a client.

    ... note::
        This is the inverse of `as_loader` and is only necessary if you wish
        to use the `tanjun.Client.unload_module` or
        `tanjun.Client.reload_module`.

    Parameters
    ----------
    callback : LoaderSig
        The callback used to unload Tanjun utilities from a module. This
        should take one argument of type `tanjun.Client`, return nothing
        and will be expected to remove utilities such as components
        from the provided client using it's abstract methods.

    Returns
    -------
    LoaderSig
        The decorated unload callback.
    """
    return _UnloaderDescriptor(callback)


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
) -> None:
    try:
        await callback.resolve(ctx, *args, **kwargs)

    except Exception as exc:
        _LOGGER.error("Client callback raised exception", exc_info=exc)


class _InjectablePrefixGetter(injecting.BaseInjectableCallback[collections.Iterable[str]]):
    __slots__ = ()

    def __init__(self, callback: PrefixGetterSig, /) -> None:
        super().__init__(callback)

    async def __call__(self, ctx: tanjun_abc.Context, /) -> collections.Iterable[str]:
        return await self.descriptor.resolve_with_command_context(ctx, ctx)

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


async def on_parser_error(ctx: tanjun_abc.Context, error: errors.ParserError) -> None:
    """Handle message parser errors.

    This is the default message parser error hook included by `Client`.
    """
    await ctx.respond(error.message)


def _cmp_command(builder: typing.Optional[hikari.api.CommandBuilder], command: hikari.Command) -> bool:
    if not builder or builder.id is not hikari.UNDEFINED and builder.id != command.id:
        return False

    if builder.name != command.name or builder.description != command.description:
        return False

    default_perm = builder.default_permission if builder.default_permission is not hikari.UNDEFINED else True
    command_options = command.options or ()
    if default_perm is not command.default_permission or len(builder.options) != len(command_options):
        return False

    return all(builder_option == option for builder_option, option in zip(builder.options, command_options))


class _StartDeclarer:
    __slots__ = ("client", "command_ids", "guild_id")

    def __init__(
        self,
        client: Client,
        command_ids: collections.Mapping[str, hikari.SnowflakeishOr[hikari.Command]],
        guild_id: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]],
    ) -> None:
        self.client = client
        self.command_ids = command_ids
        self.guild_id = guild_id

    async def __call__(self) -> None:
        try:
            await self.client.declare_global_commands(self.command_ids, guild=self.guild_id, force=False)
        finally:
            self.client.remove_client_callback(ClientCallbackNames.STARTING, self)


class Client(injecting.InjectorClient, tanjun_abc.Client):
    """Tanjun's standard `tanjun.abc.Client` implementation.

    This implementation supports dependency injection for checks, command
    callbacks, prefix getters and event listeners. For more information on how
    this works see `tanjun.injecting`.

    Notes
    -----
    * For a quicker way to initiate this client around a standard bot aware
      client, see `Client.from_gateway_bot` and `Client.from_rest_bot`.
    * The endpoint used by `declare_global_commands` has a strict ratelimit which,
      as of writing, only allows for 2 requests per minute (with that ratelimit
      either being per-guild if targeting a specific guild otherwise globally).
    * `event_manager` is necessary for message command dispatch and will also
      be necessary for interaction command dispatch if `server` isn't
      provided.
    * `server` is used for interaction command dispatch if interaction
      events aren't being received from the event manager.
    * By default this client includes a parser error handling hook which will
      by overwritten if you call `Client.set_hooks`.

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
    shards : hikari.traits.ShardAware
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
    declare_global_commands : typing.Union[hikari.SnowflakeishSequenceOr[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool]
        Whether or not to automatically set global slash commands when this
        client is first started. Defaults to `False`.

        If one or more guild objects/IDs are passed here then the registered
        global commands will be set on the specified guild(s) at startup rather
        than globally. This can be useful for testing/debug purposes as slash
        commands may take up to an hour to propagate globally but will
        immediately propagate when set on a specific guild.
    set_global_commands : typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool]
        Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
    command_ids : typing.Optional[collections.abc.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]]
        If provided, a mapping of top level command names to IDs of the commands to update.

        This field is complementary to `declare_global_commands` and, while it
        isn't necessarily required, this will in some situations help avoid
        permissions which were previously set for a command from being lost
        after a rename.

        This currently isn't supported when multiple guild IDs are passed for
        `declare_global_commands`.

    Raises
    ------
    ValueError
        Raises for the following reasons:
        * If `event_managed` is `True` when `event_manager` is `None`.
        * If `command_ids` is passed when multiple guild ids are provided for `declare_global_commands`.
        * If `command_ids` is passed when `declare_global_commands` is `False`.
    """  # noqa: E501 - line too long

    __slots__ = (
        "_accepts",
        "_auto_defer_after",
        "_cache",
        "_cached_application_id",
        "_checks",
        "_client_callbacks",
        "_components",
        "_defaults_to_ephemeral",
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
        "_modules",
        "_path_modules",
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
        shards: typing.Optional[hikari_traits.ShardAware] = None,
        event_managed: bool = False,
        mention_prefix: bool = False,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]] = None,
        _stack_level: int = 0,
    ) -> None:
        # InjectorClient.__init__
        super().__init__()
        dependencies.set_standard_dependencies(self)
        # TODO: logging or something to indicate this is running statelessly rather than statefully.
        # TODO: warn if server and dispatch both None but don't error

        # TODO: separate slash and gateway checks?
        self._accepts = MessageAcceptsEnum.ALL if events else MessageAcceptsEnum.NONE
        self._auto_defer_after: typing.Optional[float] = 2.0
        self._cache = cache
        self._cached_application_id: typing.Optional[hikari.Snowflake] = None
        self._checks: list[checks.InjectableCheck] = []
        self._client_callbacks: dict[str, list[injecting.CallbackDescriptor[None]]] = {}
        self._components: dict[str, tanjun_abc.Component] = {}
        self._defaults_to_ephemeral: bool = False
        self._make_message_context: _MessageContextMakerProto = context.MessageContext
        self._make_slash_context: _SlashContextMakerProto = context.SlashContext
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self._hooks: typing.Optional[tanjun_abc.AnyHooks] = hooks.AnyHooks().set_on_parser_error(on_parser_error)
        self._interaction_not_found: typing.Optional[str] = "Command not found"
        self._slash_hooks: typing.Optional[tanjun_abc.SlashHooks] = None
        self._is_alive = False
        self._is_closing = False
        self._listeners: dict[type[hikari.Event], list[_InjectableListener]] = {}
        self._message_hooks: typing.Optional[tanjun_abc.MessageHooks] = None
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._modules: dict[str, types.ModuleType] = {}
        self._path_modules: dict[pathlib.Path, types.ModuleType] = {}
        self._prefix_getter: typing.Optional[_InjectablePrefixGetter] = None
        self._prefixes: list[str] = []
        self._rest = rest
        self._server = server
        self._shards = shards

        if event_managed:
            if not events:
                raise ValueError("Client cannot be event managed without an event manager")

            events.subscribe(hikari.StartingEvent, self._on_starting_event)
            events.subscribe(hikari.StoppingEvent, self._on_stopping_event)

        if set_global_commands:
            warnings.warn(
                "The `set_global_commands` argument is deprecated and will be removed in v2.1.1a1. "
                "Use `declare_global_commands` instead.",
                DeprecationWarning,
                stacklevel=2 + _stack_level,
            )

        declare_global_commands = declare_global_commands or set_global_commands
        command_ids = command_ids or {}
        if isinstance(declare_global_commands, collections.Sequence):
            if command_ids and len(command_ids) > 1:
                raise ValueError("Cannot declare global guilds in multiple-guilds and pass command IDs")

            for guild in declare_global_commands:
                self.add_client_callback(ClientCallbackNames.STARTING, _StartDeclarer(self, command_ids, guild))

        elif isinstance(declare_global_commands, bool):
            if declare_global_commands:
                self.add_client_callback(
                    ClientCallbackNames.STARTING, _StartDeclarer(self, command_ids, hikari.UNDEFINED)
                )

            elif command_ids:
                raise ValueError("Cannot pass command IDs when not declaring global commands")

        else:
            self.add_client_callback(
                ClientCallbackNames.STARTING, _StartDeclarer(self, command_ids, declare_global_commands)
            )

        self.set_type_dependency(tanjun_abc.Client, self)
        self.set_type_dependency(Client, self)
        self.set_type_dependency(type(self), self)
        self.set_type_dependency(hikari.api.RESTClient, rest)
        self.set_type_dependency(type(rest), rest)
        if cache:
            self.set_type_dependency(hikari.api.Cache, cache)
            self.set_type_dependency(type(cache), cache)

        if events:
            self.set_type_dependency(hikari.api.EventManager, events)
            self.set_type_dependency(type(events), events)

        if server:
            self.set_type_dependency(hikari.api.InteractionServer, server)
            self.set_type_dependency(type(server), server)

        if shards:
            self.set_type_dependency(hikari_traits.ShardAware, shards)
            self.set_type_dependency(type(shards), shards)

    @classmethod
    def from_gateway_bot(
        cls,
        bot: hikari_traits.GatewayBotAware,
        /,
        *,
        event_managed: bool = True,
        mention_prefix: bool = False,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]] = None,
    ) -> Client:
        """Build a `Client` from a `hikari.traits.GatewayBotAware` instance.

        Notes
        -----
        * This implicitly defaults the client to human only mode.
        * This sets type dependency injectors for the hikari traits present in
          `bot` (including `hikari.traits.GatewayBotaWARE`).
        * The endpoint used by `declare_global_commands` has a strict ratelimit
          which, as of writing, only allows for 2 requests per minute (with that
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
        declare_global_commands : typing.Union[hikari.SnowflakeishSequenceOr[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool]
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally. This can be useful for testing/debug purposes as slash
            commands may take up to an hour to propagate globally but will
            immediately propagate when set on a specific guild.
        set_global_commands : typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool]
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids : typing.Optional[collections.abc.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]]
            If provided, a mapping of top level command names to IDs of the commands to update.

            This field is complementary to `declare_global_commands` and, while it
            isn't necessarily required, this will in some situations help avoid
            permissions which were previously set for a command from being lost
            after a rename.

            This currently isn't supported when multiple guild IDs are passed for
            `declare_global_commands`.
        """  # noqa: E501 - line too long
        return (
            cls(
                rest=bot.rest,
                cache=bot.cache,
                events=bot.event_manager,
                shards=bot,
                event_managed=event_managed,
                mention_prefix=mention_prefix,
                declare_global_commands=declare_global_commands,
                set_global_commands=set_global_commands,
                command_ids=command_ids,
                _stack_level=1,
            )
            .set_human_only()
            .set_hikari_trait_injectors(bot)
        )

    @classmethod
    def from_rest_bot(
        cls,
        bot: hikari_traits.RESTBotAware,
        /,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]] = None,
    ) -> Client:
        """Build a `Client` from a `hikari.traits.RESTBotAware` instance.

        Notes
        -----
        * This sets type dependency injectors for the hikari traits present in
          `bot` (including `hikari.traits.RESTBotAware`).
        * The endpoint used by `declare_global_commands` has a strict ratelimit
          which, as of writing, only allows for 2 requests per minute (with that
          ratelimit either being per-guild if targeting a specific guild
          otherwise globally).

        Parameters
        ----------
        bot : hikari.traits.RESTBotAware
            The bot client to build from.

        Other Parameters
        ----------------
        declare_global_commands : typing.Union[hikari.SnowflakeishSequenceOr[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool]
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally. This can be useful for testing/debug purposes as slash
            commands may take up to an hour to propagate globally but will
            immediately propagate when set on a specific guild.
        set_global_commands : typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool]
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids : typing.Optional[collections.abc.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]]
            If provided, a mapping of top level command names to IDs of the commands to update.

            This field is complementary to `declare_global_commands` and, while it
            isn't necessarily required, this will in some situations help avoid
            permissions which were previously set for a command from being lost
            after a rename.

            This currently isn't supported when multiple guild IDs are passed for
            `declare_global_commands`.
        """  # noqa: E501 - line too long
        return cls(
            rest=bot.rest,
            server=bot.interaction_server,
            declare_global_commands=declare_global_commands,
            set_global_commands=set_global_commands,
            command_ids=command_ids,
            _stack_level=1,
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
    def defaults_to_ephemeral(self) -> bool:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._defaults_to_ephemeral

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
    def checks(self) -> collections.Collection[tanjun_abc.CheckSig]:
        """Return a collcetion of the level `tanjun.abc.Context` checks registered to this client.

        Returns
        -------
        collections.abc.Collection[tanjun.abc.CheckSig]
            Colleciton of the `tanjun.abc.Context` based checks registered for
            this client.

            These may be taking advantage of the standard dependency injection.
        """
        return tuple(check.callback for check in self._checks)

    @property
    def components(self) -> collections.Collection[tanjun_abc.Component]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._components.copy().values()

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
        collections.abc.Collection[str]
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
        command_id: typing.Optional[hikari.Snowflakeish] = None,
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
        command_id : typing.Optional[hikari.snowflakes.Snowflakeish]
            ID of the command to update.
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
        hikari.Command
            API representation of the command that was registered.
        """
        builder = command.build()
        if command_id:
            response = await self._rest.edit_application_command(
                application or self._cached_application_id or await self.fetch_rest_application_id(),
                command_id,
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
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        force: bool = False,
    ) -> collections.Sequence[hikari.Command]:
        """Declare a collection of slash commands for a bot.

        .. note::
            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).

        Parameters
        ----------
        commands : collections.abc.Iterable[tanjun.abc.BaseSlashCommand]
            Iterable of the commands to register.

        Other Parameters
        ----------------
        command_ids : typing.Optional[collections.abc.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]]
            If provided, a mapping of top level command names to IDs of the existing commands to update.

            While optional, this can be helpful when updating commands as
            providing the current IDs will prevent changes such as renames from
            leading to other state set for commands (e.g. permissions) from
            being lost.
        application : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialApplication]]
            The application to register the commands with.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialGuild]]
            Object or ID of the guild to register the commands with.

            If left as `None` then the commands will be registered globally.
        force : bool
            Force this to declare the commands regardless of whether or not
            they match the current state of the declared commands.

            Defaults to `False`. This default behaviour helps avoid issues with the
            2 request per minute (per-guild or globally) ratelimit and the other limit
            of only 200 application command creates per day (per guild or globally).

        Returns
        -------
        collections.abc.Sequence[hikari.Command]
            API representations of the commands which were registered.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If conflicting command names are found (multiple commanbds have the same top-level name).
            * If more than 100 top-level commands are passed.
        """
        command_ids = command_ids or {}
        names_to_commands: dict[str, tanjun_abc.BaseSlashCommand] = {}
        conflicts: set[str] = set()
        builders: dict[str, hikari.api.CommandBuilder] = {}

        for command in commands:
            names_to_commands[command.name] = command
            if command.name in builders:
                conflicts.add(command.name)

            builder = command.build()
            if command_id := command_ids.get(command.name):
                builder.set_id(hikari.Snowflake(command_id))

            builders[command.name] = builder

        if conflicts:
            raise ValueError(
                "Couldn't declare commands due to conflicts. The following command names have more than one command "
                "registered for them " + ", ".join(conflicts)
            )

        if len(builders) > 100:
            raise ValueError("You can only declare up to 100 top level commands in a guild or globally")

        if not application:
            application = self._cached_application_id or await self.fetch_rest_application_id()

        name = "global" if guild is hikari.UNDEFINED else f"guild {int(guild)}"

        if not force:
            registered_commands = await self._rest.fetch_application_commands(application, guild=guild)
            if len(registered_commands) == len(builders) and all(
                _cmp_command(builders.get(command.name), command) for command in registered_commands
            ):
                _LOGGER.info("Skipping bulk declare for %s slash commands due to them already being set", name)
                return registered_commands

        _LOGGER.info("Bulk declaring %s %s slash commands", len(builders), name)
        responses = await self._rest.set_application_commands(application, list(builders.values()), guild=guild)

        for response in responses:
            if not guild:
                names_to_commands[response.name].set_tracked_command(response)  # TODO: is this fine?

            if (expected_id := command_ids.get(response.name)) and hikari.Snowflake(expected_id) != response.id:
                _LOGGER.warning(
                    "ID mismatch found for %s command %s, expected %s but got %s. "
                    "This suggests that any previous permissions set for this command will have been lost.",
                    name,
                    expected_id,
                    response.id,
                )

        _LOGGER.info("Successfully declared %s (top-level) %s commands", len(responses), name)
        _LOGGER.debug("declared %s command ids: %s", [response.id for response in responses])
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

    def set_ephemeral_default(self: _ClientT, state: bool, /) -> _ClientT:
        """Set whether slash contexts spawned by this client should default to ephemeral responses.

        Parameters
        ----------
        bool
            Whether slash command contexts executed in this component should
            should default to ephemeral.

            This will be overridden by any response calls which specify flags
            and defaults to `False`.

        Returns
        -------
        SelfT
            This component to enable method chaining.
        """
        self._defaults_to_ephemeral = state
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
                self.set_type_dependency(member, bot)

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

    async def clear_commands(  # TODO: better name?
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
        force: bool = False,
    ) -> collections.Sequence[hikari.Command]:
        """Alias of `Client.declare_global_commands`.

        .. deprecated:: v2.1.1a1
            Use `Client.declare_global_commands` instead.
        """
        return await self.declare_global_commands(application=application, guild=guild, force=force)

    async def declare_global_commands(
        self,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        force: bool = False,
    ) -> collections.Sequence[hikari.Command]:
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
        command_ids : typing.Optional[collections.abc.Mapping[str, hikari.SnowflakeishOr[hikari.Command]]]
            If provided, a mapping of top level command names to IDs of the existing commands to update.
        application : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.PartialApplication]]
            Object or ID of the application to set the global commands for.

            If left as `None` then this will be inferred from the authorization
            being used by `Client.rest`.
        guild : hikari.UndefinedOr[hikari.snowflakes.SnowflakeishOr[hikari.PartialGuild]]
            Object or ID of the guild to set the global commands to.

            If left as `None` global commands will be set.
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
        commands = (
            command
            for command in itertools.chain.from_iterable(
                component.slash_commands for component in self._components.values()
            )
            if command.is_global
        )
        return await self.declare_slash_commands(
            commands, command_ids, application=application, guild=guild, force=force
        )

    def add_check(self: _ClientT, check: tanjun_abc.CheckSig, /) -> _ClientT:
        """Add a generic check to this client.

        This will be applied to both message and slash command execution.

        Parameters
        ----------
        check : tanjun_abc.CheckSig
            The check to add. This may be either synchronous or asynchronous
            and must take one positional argument of type `tanjun.abc.Context`
            with dependency injection being supported for its keyword arguments.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        if check not in self._checks:  # type: ignore[arg-type]
            self._checks.append(checks.InjectableCheck(check))

        return self

    def remove_check(self: _ClientT, check: tanjun_abc.CheckSig, /) -> _ClientT:
        """Remove a check from the client.

        Parameters
        ----------
        check : tanjun_abc.CheckSig
            The check to remove.

        Raises
        ------
        ValueError
            If the check was not previously added.
        """
        self._checks.remove(check)  # type: ignore[arg-type]
        return self

    def with_check(self, check: tanjun_abc.CheckSigT, /) -> tanjun_abc.CheckSigT:
        """Add a check to this client through a decorator call.

        Parameters
        ----------
        check : tanjun_abc.CheckSig
            The check to add. This may be either synchronous or asynchronous
            and must take one positional argument of type `tanjun.abc.Context`
            with dependency injection being supported for its keyword arguments.

        Returns
        -------
        tanjun_abc.CheckSig
            The added check.
        """
        self.add_check(check)
        return check

    async def check(self, ctx: tanjun_abc.Context, /) -> bool:
        return await utilities.gather_checks(ctx, self._checks)

    def add_component(self: _ClientT, component: tanjun_abc.Component, /, *, add_injector: bool = False) -> _ClientT:
        """Add a component to this client.

        Parameters
        ----------
        component: Component
            The component to move to this client.

        Returns
        -------
        Self
            The client instance to allow chained calls.

        Raises
        ------
        ValueError
            If the component's name is already registered.
        """
        if component.name in self._components:
            raise ValueError(f"A component named {component.name!r} is already registered.")

        component.bind_client(self)
        self._components[component.name] = component

        if add_injector:
            self.set_type_dependency(type(component), lambda: component)

        if self._is_alive:
            asyncio.get_running_loop().create_task(
                self.dispatch_client_callback(ClientCallbackNames.COMPONENT_ADDED, component)
            )

        return self

    def get_component_by_name(self, name: str, /) -> typing.Optional[tanjun_abc.Component]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._components.get(name)

    def remove_component(self: _ClientT, component: tanjun_abc.Component, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        stored_component = self._components.get(component.name)
        if not stored_component or stored_component != component:
            raise ValueError(f"The component {component!r} is not registered.")

        del self._components[component.name]
        stored_component.unbind_client(self)

        if self._is_alive:
            asyncio.get_running_loop().create_task(
                self.dispatch_client_callback(ClientCallbackNames.COMPONENT_REMOVED, stored_component)
            )

        return self

    def remove_component_by_name(self: _ClientT, name: str, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self.remove_component(self._components[name])

    def add_client_callback(self: _ClientT, name: str, callback: tanjun_abc.MetaEventSig, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        descriptor = injecting.CallbackDescriptor(callback)
        name = name.casefold()
        try:
            if descriptor in self._client_callbacks[name]:
                return self

            self._client_callbacks[name].append(descriptor)
        except KeyError:
            self._client_callbacks[name] = [descriptor]

        return self

    async def dispatch_client_callback(self, name: str, /, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Dispatch a client callback.

        Parameters
        ----------
        name : str
            The name of the callback to dispatch.

        Other Parameters
        ----------------
        *args : typing.Any
            Positional arguments to pass to the callback(s).
        **kwargs : typing.Any
            Keyword arguments to pass to the callback(s).

        Raises
        ------
        KeyError
            If no callbacks are registered for the given name.
        """
        name = name.casefold()
        if callbacks := self._client_callbacks.get(name):
            calls = (
                _wrap_client_callback(callback, injecting.BasicInjectionContext(self), args, kwargs)
                for callback in callbacks
            )
            await asyncio.gather(*calls)

    def get_client_callbacks(self, name: str, /) -> collections.Collection[tanjun_abc.MetaEventSig]:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        if result := self._client_callbacks.get(name):
            return tuple(callback.callback for callback in result)

        return ()

    def remove_client_callback(self: _ClientT, name: str, callback: tanjun_abc.MetaEventSig, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        self._client_callbacks[name].remove(callback)  # type: ignore
        if not self._client_callbacks[name]:
            del self._client_callbacks[name]

        return self

    def with_client_callback(
        self, name: str, /
    ) -> collections.Callable[[tanjun_abc.MetaEventSigT], tanjun_abc.MetaEventSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: tanjun_abc.MetaEventSigT, /) -> tanjun_abc.MetaEventSigT:
            self.add_client_callback(name, callback)
            return callback

        return decorator

    def add_listener(
        self: _ClientT, event_type: type[hikari.Event], callback: tanjun_abc.ListenerCallbackSig, /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        injected = _InjectableListener(self, callback)
        try:
            if callback in self._listeners[event_type]:
                return self

            self._listeners[event_type].append(injected)

        except KeyError:
            self._listeners[event_type] = [injected]

        if self._is_alive and self._events:
            self._events.subscribe(event_type, injected.__call__)

        return self

    def remove_listener(
        self: _ClientT, event_type: type[hikari.Event], callback: tanjun_abc.ListenerCallbackSig, /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        registered_callback = self._listeners[event_type].pop(self._listeners[event_type].index(callback))

        if not self._listeners[event_type]:
            del self._listeners[event_type]

        if self._is_alive and self._events:
            self._events.unsubscribe(event_type, registered_callback.__call__)

        return self

    def with_listener(
        self, event_type: type[hikari.Event], /
    ) -> collections.Callable[[tanjun_abc.ListenerCallbackSigT], tanjun_abc.ListenerCallbackSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: tanjun_abc.ListenerCallbackSigT, /) -> tanjun_abc.ListenerCallbackSigT:
            self.add_listener(event_type, callback)
            return callback

        return decorator

    def add_prefix(self: _ClientT, prefixes: typing.Union[collections.Iterable[str], str], /) -> _ClientT:
        """Add a prefix used to filter message command calls.

        This will be matched against the first character(s) in a message's
        content to determine whether the message command search stage of
        execution should be initiated.

        Parameters
        ----------
        prefixes : typing.Union[collections.abc.Iterable[str], str]
            Either a single string or an iterable of strings to be used as
            prefixes.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        if isinstance(prefixes, str):
            if prefixes not in self._prefixes:
                self._prefixes.append(prefixes)

        else:
            self._prefixes.extend(prefix for prefix in prefixes if prefix not in self._prefixes)

        return self

    def remove_prefix(self: _ClientT, prefix: str, /) -> _ClientT:
        """Remove a message content prefix from the client.

        Parameters
        ----------
        prefix : str
            The prefix to remove.

        Raises
        ------
        ValueError
            If the prefix is not registered with the client.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._prefixes.remove(prefix)
        return self

    def set_prefix_getter(self: _ClientT, getter: typing.Optional[PrefixGetterSig], /) -> _ClientT:
        """Set the callback used to retrieve message prefixes set for the relevant guild.

        Parameters
        ----------
        getter : typing.Optional[PrefixGetterSig]
            The callback which'll be used to retrieve prefixes for the guild a
            message context is from. If `None` is passed here then the callback
            will be unset.

            This should be an async callback which one argument of type
            `tanjun.abc.MessageContext` and returns an iterable of string prefixes.
            Dependency injection is supported for this callback's keyword arguments.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._prefix_getter = _InjectablePrefixGetter(getter) if getter else None
        return self

    def with_prefix_getter(self, getter: PrefixGetterSigT, /) -> PrefixGetterSigT:
        """Set the prefix getter callback for this client through decorator call.

        Examples
        --------
        ```py
        client = tanjun.Client.from_rest_bot(bot)

        @client.with_prefix_getter
        async def prefix_getter(ctx: tanjun.abc.MessageContext) -> collections.abc.Iterable[str]:
            raise NotImplementedError
        ```

        Parameters
        ----------
        getter : PrefixGetterSig
            The callback which'll be  to retrieve prefixes for the guild a
            message event is from.

            This should be an async callback which one argument of type
            `tanjun.abc.MessageContext` and returns an iterable of string prefixes.
            Dependency injection is supported for this callback's keyword arguments.

        Returns
        -------
        PrefixGetterSigT
            The registered callback.
        """
        self.set_prefix_getter(getter)
        return getter

    def iter_commands(self) -> collections.Iterator[tanjun_abc.ExecutableCommand[tanjun_abc.Context]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        slash_commands = self.iter_slash_commands(global_only=False)
        yield from self.iter_message_commands()
        yield from slash_commands

    def iter_message_commands(self) -> collections.Iterator[tanjun_abc.MessageCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(component.message_commands for component in self.components)

    def iter_slash_commands(self, *, global_only: bool = False) -> collections.Iterator[tanjun_abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        if global_only:
            return filter(lambda c: c.is_global, self.iter_slash_commands(global_only=False))

        return itertools.chain.from_iterable(component.slash_commands for component in self.components)

    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, tanjun_abc.MessageCommand]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(
            component.check_message_name(name) for component in self._components.values()
        )

    def check_slash_name(self, name: str, /) -> collections.Iterator[tanjun_abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(
            component.check_slash_name(name) for component in self._components.values()
        )

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
        """Close the client.

        Raises
        ------
        RuntimeError
            If the client isn't running.
        """
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
                    self._try_unsubscribe(self._events, event_type, listener.__call__)

        if deregister_listeners and self._server:
            self._server.set_listener(hikari.CommandInteraction, None)

        self._is_alive = False
        await self.dispatch_client_callback(ClientCallbackNames.CLOSED)
        self._is_closing = False

    async def open(self, *, register_listeners: bool = True) -> None:
        """Start the client.

        If `mention_prefix` was passed to `Client.__init__` or
        `Client.from_gateway_bot` then this function may make a fetch request
        to Discord if it cannot get the current user from the cache.

        Raises
        ------
        RuntimeError
            If the client is already active.
        """
        if self._is_alive:
            raise RuntimeError("Client is already alive")

        self._is_alive = True
        self._is_closing = False
        await self.dispatch_client_callback(ClientCallbackNames.STARTING)

        if self._grab_mention_prefix:
            if self._cache:
                user = self._cache.get_me() or await self._rest.fetch_my_user()
            else:
                user = await self._rest.fetch_my_user()

            for prefix in f"<@{user.id}>", f"<@!{user.id}>":
                if prefix not in self._prefixes:
                    self._prefixes.append(prefix)

            self._grab_mention_prefix = False

        if register_listeners and self._events:
            if event_type := self._accepts.get_event_type():
                self._events.subscribe(event_type, self.on_message_create_event)

            self._events.subscribe(hikari.InteractionCreateEvent, self.on_interaction_create_event)

            for event_type, listeners in self._listeners.items():
                for listener in listeners:
                    self._events.subscribe(event_type, listener.__call__)

        if register_listeners and self._server:
            self._server.set_listener(hikari.CommandInteraction, self.on_interaction_create_request)

        asyncio.get_running_loop().create_task(self.dispatch_client_callback(ClientCallbackNames.STARTED))

    async def fetch_rest_application_id(self) -> hikari.Snowflake:
        """Fetch the application ID of the application this client is linked to.

        Returns
        -------
        hikari.Snowflake
            The application ID of the application this client is linked to.
        """
        if self._cached_application_id:
            return self._cached_application_id

        if self._rest.token_type == hikari.TokenType.BOT:
            application = await self._rest.fetch_application()

        else:
            application = (await self._rest.fetch_authorization()).application

        self._cached_application_id = hikari.Snowflake(application)
        return self._cached_application_id

    def set_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.AnyHooks], /) -> _ClientT:
        """Set the general command execution hooks for this client.

        The callbacks within this hook will be added to every slash and message
        command execution started by this client.

        Parameters
        ----------
        hooks : typing.Optional[tanjun_abc.AnyHooks]
            The general command execution hooks to set for this client.

            Passing `None` will remove all hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._hooks = hooks
        return self

    def set_slash_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.SlashHooks], /) -> _ClientT:
        """Set the slash command execution hooks for this client.

        The callbacks within this hook will be added to every slash command
        execution started by this client.

        Parameters
        ----------
        hooks : typing.Optional[tanjun_abc.SlashHooks]
            The slash context specific command execution hooks to set for this
            client.

            Passing `None` will remove the hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._slash_hooks = hooks
        return self

    def set_message_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.MessageHooks], /) -> _ClientT:
        """Set the message command execution hooks for this client.

        The callbacks within this hook will be added to every message command
        execution started by this client.

        Parameters
        ----------
        hooks : typing.Optional[tanjun_abc.MessageHooks]
            The message context specific command execution hooks to set for this
            client.

            Passing `None` will remove all hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._message_hooks = hooks
        return self

    @staticmethod
    def _iter_module_members(module: types.ModuleType, module_repr: str, /) -> collections.Iterator[typing.Any]:
        exported = getattr(module, "__all__", None)
        if exported is not None and isinstance(exported, collections.Iterable):
            _LOGGER.debug("Scanning %s module based on its declared __all__)", module_repr)
            return (getattr(module, name, None) for name in exported if isinstance(name, str))

        _LOGGER.debug("Scanning all public members on %s", module_repr)
        return (
            member
            for name, member in inspect.getmembers(module)
            if not name.startswith("_") or name.startswith("__") and name.endswith("__")
        )

    def _load_module(self, module: types.ModuleType, module_repr: str) -> None:
        found = False
        for member in self._iter_module_members(module, module_repr):
            if isinstance(member, _LoaderDescriptor):
                member(self)
                found = True

        if not found:
            raise RuntimeError(f"Didn't find any loader descriptors in {module_repr}")

    def load_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path], _log: bool = True) -> _ClientT:
        """Load entities into this client from modules based on loader descriptors.

        .. note::
            If an `__all__` is present in the target module then it will be
            used to find loaders.

        Examples
        --------
        For this to work the module has to have at least one `as_loader`
        decorated top level function which takes one positional argument
        of type `Client`.

        ```py
        @tanjun.as_loader
        def load_module(client: tanjun.Client) -> None:
            client.add_component(component.copy())
        ```

        Parameters
        ----------
        *modules : typing.Union[str, pathlib.Path]
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
        ValueError
            If the module is already loaded.
        RuntimeError
            If no loader descriptors are found in the module.
        ModuleNotFoundError
            If the module is not found.
        """
        for module_path in modules:
            if isinstance(module_path, str):
                if module_path in self._modules:
                    raise ValueError(f"module {module_path} already loaded")

                if _log:
                    _LOGGER.info("Loading from %s", module_path)

                module = importlib.import_module(module_path)
                self._load_module(module, str(module_path))
                self._modules[module_path] = module

            else:
                module_path_abs = module_path.absolute()
                if module_path_abs in self._path_modules:
                    raise ValueError(f"Module at {module_path} already loaded")

                module_name = module_path.name.rsplit(".", 1)[0]
                spec = importlib_util.spec_from_file_location(module_name, module_path_abs)

                # https://github.com/python/typeshed/issues/2793
                if not spec or not isinstance(spec.loader, importlib_abc.Loader):
                    raise ModuleNotFoundError(
                        f"Module not found at {module_path}", name=module_name, path=str(module_path)
                    )

                if _log:
                    _LOGGER.info("Loading from %s", module_path)

                module = importlib_util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._load_module(module, str(module_path))
                self._path_modules[module_path_abs] = module

        return self

    def _unload_module(self, module: types.ModuleType, module_repr: str) -> None:
        found = False
        for member in self._iter_module_members(module, module_repr):
            if isinstance(member, _UnloaderDescriptor):
                member(self)
                found = True

        if not found:
            raise RuntimeError(f"Didn't find any unloaders in {module_repr}")

    def unload_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path], _log: bool = True) -> _ClientT:
        """Unload entities from this client based on unloader descriptors in one or more modules.

        .. note::
            If an `__all__` is present in the target module then it will be
            used to find unloaders.

        Examples
        --------
        For this to work the module has to have at least one `as_unloader`
        decorated top level function which takes one positional argument
        of type `Client`.

        ```py
        @tanjun.as_unloader
        def unload_component(client: tanjun.Client) -> None:
            client.remove_component_by_name(component.name)
        ```

        Parameters
        ----------
        *modules: typing.Union[str, pathlib.Path]
            Path of one or more modules to unload.

            These should be the same path(s) which were passed to `load_module`.

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        ValueError
            If the module hasn't been loaded.
        RuntimeError
            If no unloader descriptors are found in the module.
        """
        for module_path in modules:
            if isinstance(module_path, str):
                module = self._modules.pop(module_path, None)

            else:
                module_path = module_path.absolute()
                module = self._path_modules.pop(module_path, None)

            if not module:
                raise ValueError(f"Module {module_path!s} not loaded")

            if _log:
                _LOGGER.info("Unloading from %s", module_path)

            self._unload_module(module, str(module_path))

        return self

    def reload_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path]) -> _ClientT:
        """Reload entities in this client based on the descriptors in loaded module(s).

        .. note::
            If an `__all__` is present in the target module then it will be
            used to find descriptors.

        Examples
        --------
        For this to work the module has to have at least one `as_loader` and
        one `as_unloader` decorated top level function which each take one
        positional argument of type `Client`.

        Parameters
        ----------
        *modules: typing.Union[str, pathlib.Path]
            Paths of one or more module to unload.

            These  should be the same paths which were passed to `load_module`.

        Returns
        -------
        Self
            This client instance to enable chained calls.

        Raises
        ------
        ValueError
            If the module hasn't been loaded.
        RuntimeError
            If no unloader descriptors are found in the current state of the module.
            If no loader descriptors are found in the new state of the module.
        """
        for module_path in modules:
            if isinstance(module_path, str):
                module = self._modules.pop(module_path, None)
                if not module:
                    raise ValueError(f"Module {module_path} not loaded")

                module_repr = str(module_path)
                _LOGGER.info("Reloading %s", module_repr)
                self._unload_module(module, module_repr)
                module = importlib.reload(module)
                self._load_module(module, module_repr)
                self._modules[module_path] = module

            else:
                _LOGGER.info("Reloading %s", module_path)
                self.unload_modules(module_path, _log=False)
                self.load_modules(module_path, _log=False)

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
        hooks: typing.Optional[set[tanjun_abc.MessageHooks]] = None
        if self._hooks and self._message_hooks:
            hooks = {self._hooks, self._message_hooks}

        elif self._hooks:
            hooks = {self._hooks}

        elif self._message_hooks:
            hooks = {self._message_hooks}

        try:
            if await self.check(ctx):
                for component in self._components.values():
                    if await component.execute_message(ctx, hooks=hooks):
                        return

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

    async def _on_slash_not_found(self, ctx: context.SlashContext) -> None:
        await self.dispatch_client_callback(ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)
        if self._interaction_not_found and not ctx.has_responded:
            await ctx.create_initial_response(self._interaction_not_found)

    async def on_interaction_create_event(self, event: hikari.InteractionCreateEvent, /) -> None:
        """Execute a slash command based on Gateway events.

        .. note::
            Any event where `event.interaction` is not
            `hikari.CommandInteraction` will be ignored.

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
            on_not_found=self._on_slash_not_found,
            default_to_ephemeral=self._defaults_to_ephemeral,
        )
        hooks = self._get_slash_hooks()

        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        try:
            if await self.check(ctx):
                for component in self._components.values():
                    # This is set on each iteration to ensure that any component
                    # state which was set to this isn't propagated to other components.
                    ctx.set_ephemeral_default(self._defaults_to_ephemeral)
                    if future := await component.execute_interaction(ctx, hooks=hooks):
                        await future
                        return

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            await ctx.respond(exc.message)
            return

        await ctx.mark_not_found()

    async def on_interaction_create_request(self, interaction: hikari.CommandInteraction, /) -> context.ResponseTypeT:
        """Execute a slash command based on received REST requests.

        Parameters
        ----------
        interaction : hikari.CommandInteraction
            The interaction to execute a command based on.

        Returns
        -------
        tanjun.context.ResponseType
            The initial response to send back to Discord.
        """
        ctx = self._make_slash_context(
            client=self,
            injection_client=self,
            interaction=interaction,
            on_not_found=self._on_slash_not_found,
            default_to_ephemeral=self._defaults_to_ephemeral,
        )
        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        hooks = self._get_slash_hooks()
        future = ctx.get_response_future()
        try:
            if await self.check(ctx):
                for component in self._components.values():
                    if await component.execute_interaction(ctx, hooks=hooks):
                        return await future

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            # Under very specific timing there may be another future which could set a result while we await
            # ctx.respond therefore we create a task to avoid any erroneous behaviour from this trying to create
            # another response before it's returned the initial response.
            asyncio.get_running_loop().create_task(
                ctx.respond(exc.message), name=f"{interaction.id} command error responder"
            )
            return await future

        asyncio.get_running_loop().create_task(ctx.mark_not_found(), name=f"{interaction.id} not found")
        return await future
