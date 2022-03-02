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
"""Standard Tanjun client."""
from __future__ import annotations

__all__: list[str] = [
    "Client",
    "ClientCallbackNames",
    "MessageAcceptsEnum",
    "PrefixGetterSig",
    "as_loader",
    "as_unloader",
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
import pathlib
import typing
import warnings
from collections import abc as collections

import alluka
import hikari
from hikari import traits as hikari_traits

from . import abc as tanjun_abc
from . import context
from . import dependencies
from . import errors
from . import hooks
from . import utilities

if typing.TYPE_CHECKING:
    import types

    _CheckSigT = typing.TypeVar("_CheckSigT", bound=tanjun_abc.CheckSig)
    _ClientT = typing.TypeVar("_ClientT", bound="Client")
    _ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound=tanjun_abc.ListenerCallbackSig)
    _MetaEventSigT = typing.TypeVar("_MetaEventSigT", bound=tanjun_abc.MetaEventSig)
    _PrefixGetterSigT = typing.TypeVar("_PrefixGetterSigT", bound="PrefixGetterSig")
    _T = typing.TypeVar("_T")

    class _AutocompleteContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun_abc.Client,
            interaction: hikari.AutocompleteInteraction,
            *,
            future: typing.Optional[asyncio.Future[hikari.api.InteractionAutocompleteBuilder]] = None,
        ) -> context.AutocompleteContext:
            raise NotImplementedError

    class _MenuContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun_abc.Client,
            interaction: hikari.CommandInteraction,
            *,
            default_to_ephemeral: bool = False,
            future: typing.Optional[
                asyncio.Future[
                    typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]
                ]
            ] = None,
            on_not_found: typing.Optional[
                collections.Callable[[tanjun_abc.MenuContext], collections.Awaitable[None]]
            ] = None,
        ) -> context.MenuContext:
            raise NotImplementedError

    class _MessageContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun_abc.Client,
            content: str,
            message: hikari.Message,
            *,
            triggering_name: str = "",
            triggering_prefix: str = "",
        ) -> context.MessageContext:
            raise NotImplementedError

    class _SlashContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun_abc.Client,
            interaction: hikari.CommandInteraction,
            *,
            default_to_ephemeral: bool = False,
            future: typing.Optional[
                asyncio.Future[
                    typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]
                ]
            ] = None,
            on_not_found: typing.Optional[
                collections.Callable[[tanjun_abc.SlashContext], collections.Awaitable[None]]
            ] = None,
        ) -> context.SlashContext:
            raise NotImplementedError


PrefixGetterSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, collections.Iterable[str]]]
"""Type hint of a callable used to get the prefix(es) for a specific guild.

This should be an asynchronous callable which returns an iterable of strings.

.. note::
    While dependency injection is supported for this, the first positional
    argument will always be a `tanjun.abc.MessageContext`.
"""

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun.clients")
_MENU_TYPES = frozenset((hikari.CommandType.MESSAGE, hikari.CommandType.USER))


class _LoaderDescriptor(tanjun_abc.ClientLoader):  # Slots mess with functools.update_wrapper
    def __init__(
        self,
        callback: typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun_abc.Client], None]],
        standard_impl: bool,
    ) -> None:
        self._callback = callback
        self._must_be_std = standard_impl
        functools.update_wrapper(self, callback)

    @property
    def has_load(self) -> bool:
        return True

    @property
    def has_unload(self) -> bool:
        return False

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._callback(*args, **kwargs)

    def load(self, client: tanjun_abc.Client, /) -> bool:
        if self._must_be_std:
            if not isinstance(client, Client):
                raise ValueError("This loader requires instances of the standard Client implementation")

            self._callback(client)

        else:
            typing.cast("collections.Callable[[tanjun_abc.Client], None]", self._callback)(client)

        return True

    def unload(self, _: tanjun_abc.Client, /) -> bool:
        return False


class _UnloaderDescriptor(tanjun_abc.ClientLoader):  # Slots mess with functools.update_wrapper
    def __init__(
        self,
        callback: typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun_abc.Client], None]],
        standard_impl: bool,
    ) -> None:
        self._callback = callback
        self._must_be_std = standard_impl
        functools.update_wrapper(self, callback)

    @property
    def has_load(self) -> bool:
        return False

    @property
    def has_unload(self) -> bool:
        return True

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self._callback(*args, **kwargs)

    def load(self, _: tanjun_abc.Client, /) -> bool:
        return False

    def unload(self, client: tanjun_abc.Client, /) -> bool:
        if self._must_be_std:
            if not isinstance(client, Client):
                raise ValueError("This unloader requires instances of the standard Client implementation")

            self._callback(client)

        else:
            typing.cast("collections.Callable[[tanjun_abc.Client], None]", self._callback)(client)

        return True


@typing.overload
def as_loader(
    callback: collections.Callable[[Client], None], /, *, standard_impl: typing.Literal[True] = True
) -> collections.Callable[[Client], None]:
    ...


@typing.overload
def as_loader(
    callback: collections.Callable[[tanjun_abc.Client], None], /, *, standard_impl: typing.Literal[False]
) -> collections.Callable[[tanjun_abc.Client], None]:
    ...


def as_loader(
    callback: typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun_abc.Client], None]],
    /,
    *,
    standard_impl: bool = True,
) -> typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun_abc.Client], None]]:
    """Mark a callback as being used to load Tanjun components from a module.

    .. note::
        This is only necessary if you wish to use `tanjun.Client.load_modules`.

    Parameters
    ----------
    callback : collections.abc.Callable[[tanjun.abc.Client], None]]
        The callback used to load Tanjun components from a module.

        This should take one argument of type `Client` (or `tanjun.abc.Client`
        if `standard_impl` is `False`), return nothing and will be expected
        to initiate and add utilities such as components to the provided client.
    standard_impl : bool
        Whether this loader should only allow instances of `Client` as opposed
        to `tanjun.abc.Client`.

        Defaults to `True`.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.Client], None]]
        The decorated load callback.
    """
    return _LoaderDescriptor(callback, standard_impl)


@typing.overload
def as_unloader(
    callback: collections.Callable[[Client], None], /, *, standard_impl: typing.Literal[True] = True
) -> collections.Callable[[Client], None]:
    ...


@typing.overload
def as_unloader(
    callback: collections.Callable[[tanjun_abc.Client], None], /, *, standard_impl: typing.Literal[False]
) -> collections.Callable[[tanjun_abc.Client], None]:
    ...


def as_unloader(
    callback: typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun_abc.Client], None]],
    /,
    *,
    standard_impl: bool = True,
) -> typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun_abc.Client], None]]:
    """Mark a callback as being used to unload a module's utilities from a client.

    .. note::
        This is the inverse of `as_loader` and is only necessary if you wish
        to use the `tanjun.Client.unload_module` or
        `tanjun.Client.reload_module`.

    Parameters
    ----------
    callback : collections.abc.Callable[[tanjun.Client], None]]
        The callback used to unload Tanjun components from a module.

        This should take one argument of type `Client` (or `tanjun.abc.Client`
        if `standard_impl` is `False`), return nothing and will be expected
        to remove utilities such as components from the provided client.
    standard_impl : bool
        Whether this unloader should only allow instances of `Client` as
        opposed to `tanjun.abc.Client`.

        Defaults to `True`.

    Returns
    -------
    collections.abc.Callable[[tanjun.Client], None]]
        The decorated unload callback.
    """
    return _UnloaderDescriptor(callback, standard_impl)


ClientCallbackNames = tanjun_abc.ClientCallbackNames
"""Alias of `tanjun.abc.ClientCallbackNames`."""


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
        type[hikari.message_events.MessageCreateEvent] | None
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
    client: Client,
    callback: tanjun_abc.MetaEventSig,
    args: tuple[str, ...],
) -> None:
    try:
        await client.injector.call_with_async_di(callback, *args)

    except Exception as exc:
        _LOGGER.error("Client callback raised exception", exc_info=exc)


async def on_parser_error(ctx: tanjun_abc.Context, error: errors.ParserError) -> None:
    """Handle message parser errors.

    This is the default message parser error hook included by `Client`.
    """
    await ctx.respond(error.message)


def _cmp_command(builder: typing.Optional[hikari.api.CommandBuilder], command: hikari.PartialCommand) -> bool:
    if not builder or builder.id is not hikari.UNDEFINED and builder.id != command.id or builder.type != command.type:
        return False

    default_perm = builder.default_permission if builder.default_permission is not hikari.UNDEFINED else True
    if default_perm is not command.default_permission:
        return False

    if isinstance(command, hikari.SlashCommand):
        assert isinstance(builder, hikari.api.SlashCommandBuilder)
        if builder.name != command.name or builder.description != command.description:
            return False

        command_options = command.options or ()
        if len(builder.options) != len(command_options):
            return False

        return all(builder_option == option for builder_option, option in zip(builder.options, command_options))

    return True


class _StartDeclarer:
    __slots__ = ("client", "command_ids", "guild_id", "message_ids", "user_ids", "__weakref__")

    def __init__(
        self,
        client: Client,
        guild_id: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]],
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]],
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]],
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]],
    ) -> None:
        self.client = client
        self.command_ids = command_ids
        self.guild_id = guild_id
        self.message_ids = message_ids
        self.user_ids = user_ids

    async def __call__(self) -> None:
        try:
            await self.client.declare_global_commands(
                self.command_ids, message_ids=self.message_ids, user_ids=self.user_ids, guild=self.guild_id, force=False
            )
        finally:
            self.client.remove_client_callback(ClientCallbackNames.STARTING, self)


class Client(tanjun_abc.Client):
    """Tanjun's standard `tanjun.abc.Client` implementation.

    This implementation supports dependency injection for checks, command
    callbacks, prefix getters and event listeners. For more information on how
    this works see `alluka`.

    .. note::
        By default this client includes a parser error handling hook which will
        by overwritten if you call `Client.set_hooks`.
    """

    __slots__ = (
        "_accepts",
        "_auto_defer_after",
        "_cache",
        "_cached_application_id",
        "_checks",
        "_client_callbacks",
        "_components",
        "_defaults_to_ephemeral",
        "_make_autocomplete_context",
        "_make_menu_context",
        "_make_message_context",
        "_make_slash_context",
        "_events",
        "_grab_mention_prefix",
        "_hooks",
        "_menu_hooks",
        "_menu_not_found",
        "_slash_hooks",
        "_slash_not_found",
        "_injector",
        "_is_closing",
        "_listeners",
        "_loop",
        "_message_hooks",
        "_metadata",
        "_modules",
        "_path_modules",
        "_prefix_getter",
        "_prefixes",
        "_rest",
        "_server",
        "_shards",
        "_voice",
    )

    def __init__(
        self,
        rest: hikari.api.RESTClient,
        *,
        cache: typing.Optional[hikari.api.Cache] = None,
        events: typing.Optional[hikari.api.EventManager] = None,
        server: typing.Optional[hikari.api.InteractionServer] = None,
        shards: typing.Optional[hikari.ShardAware] = None,
        voice: typing.Optional[hikari.api.VoiceComponent] = None,
        event_managed: bool = False,
        injector: typing.Optional[alluka.abc.Client] = None,
        mention_prefix: bool = False,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        _stack_level: int = 0,
    ) -> None:
        """Initialise a Tanjun client.

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
        voice : hikari.api.voice.VoiceComponent
            The Hikari voice component this will use if applicable.
        event_managed : bool
            Whether or not this client is managed by the event manager.

            An event managed client will be automatically started and closed based
            on Hikari's lifetime events.

            Defaults to `False` and can only be passed as `True` if `event_manager`
            is also provided.
        injector : alluka.abc.Client | None
            The alluka client this should use for dependency injection.

            If not provided then the client will initialise its own DI client.
        mention_prefix : bool
            Whether or not mention prefixes should be automatically set when this
            client is first started.

            Defaults to `False` and it should be noted that this only applies to
            message commands.
        declare_global_commands : hikari.SnowflakeishSequence[hikari.PartialGuild] | hikari.Snowflakeish | hikari.PartialGuild | bool
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally. This can be useful for testing/debug purposes as slash
            commands may take up to an hour to propagate globally but will
            immediately propagate when set on a specific guild.
        set_global_commands : hikari.Snowflakeish | hikari.PartialGuild | bool
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand]] | None
            If provided, a mapping of top level command names to IDs of the
            existing commands to update.

            This will be used for all application commands but in cases where
            commands have overlapping names, `message_ids` and `user_ids` will
            take priority over this for their relevant command type.

            This field is complementary to `declare_global_commands` and, while it
            isn't necessarily required, this will in some situations help avoid
            permissions which were previously set for a command from being lost
            after a rename.

            This currently isn't supported when multiple guild IDs are passed for
            `declare_global_commands`.
        message_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.

        Raises
        ------
        ValueError
            Raises for the following reasons:
            * If `event_managed` is `True` when `event_manager` is `None`.
            * If `command_ids` is passed when multiple guild ids are provided for `declare_global_commands`.
            * If `command_ids` is passed when `declare_global_commands` is `False`.
        """  # noqa: E501 - line too long
        # InjectorClient.__init__
        super().__init__()
        if _LOGGER.isEnabledFor(logging.INFO):
            _LOGGER.info(
                "%s initialised with the following components: %s",
                "Event-managed client" if event_managed else "Client",
                ", ".join(
                    name
                    for name, value in [
                        ("cache", cache),
                        ("event manager", events),
                        ("interaction server", server),
                        ("rest", rest),
                        ("shard manager", shards),
                    ]
                    if value
                ),
            )

        if not events and not server:
            _LOGGER.warning(
                "Client initiaited without an event manager or interaction server, "
                "automatic command dispatch will be unavailable."
            )

        self._accepts = MessageAcceptsEnum.ALL if events else MessageAcceptsEnum.NONE
        self._auto_defer_after: typing.Optional[float] = 2.0
        self._cache = cache
        self._cached_application_id: typing.Optional[hikari.Snowflake] = None
        self._checks: list[tanjun_abc.CheckSig] = []
        self._client_callbacks: dict[str, list[tanjun_abc.MetaEventSig]] = {}
        self._components: dict[str, tanjun_abc.Component] = {}
        self._defaults_to_ephemeral: bool = False
        self._make_autocomplete_context: _AutocompleteContextMakerProto = context.AutocompleteContext
        self._make_menu_context: _MenuContextMakerProto = context.MenuContext
        self._make_message_context: _MessageContextMakerProto = context.MessageContext
        self._make_slash_context: _SlashContextMakerProto = context.SlashContext
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self._hooks: typing.Optional[tanjun_abc.AnyHooks] = hooks.AnyHooks().set_on_parser_error(on_parser_error)
        self._menu_hooks: typing.Optional[tanjun_abc.MenuHooks] = None
        self._menu_not_found: typing.Optional[str] = "Command not found"
        self._slash_hooks: typing.Optional[tanjun_abc.SlashHooks] = None
        self._slash_not_found: typing.Optional[str] = self._menu_not_found
        # TODO: test coverage
        self._injector = injector or alluka.Client()
        self._is_closing = False
        self._listeners: dict[
            type[hikari.Event],
            dict[tanjun_abc.ListenerCallbackSig, alluka.abc.AsyncSelfInjecting[tanjun_abc.ListenerCallbackSig]],
        ] = {}
        self._loop: typing.Optional[asyncio.AbstractEventLoop] = None
        self._message_hooks: typing.Optional[tanjun_abc.MessageHooks] = None
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._modules: dict[str, types.ModuleType] = {}
        self._path_modules: dict[pathlib.Path, types.ModuleType] = {}
        self._prefix_getter: typing.Optional[PrefixGetterSig] = None
        self._prefixes: list[str] = []
        self._rest = rest
        self._server = server
        self._shards = shards
        self._voice = voice

        if event_managed:
            if not events:
                raise ValueError("Client cannot be event managed without an event manager")

            events.subscribe(hikari.StartingEvent, self._on_starting_event)
            events.subscribe(hikari.StoppingEvent, self._on_stopping_event)

        (
            self.set_type_dependency(tanjun_abc.Client, self)
            .set_type_dependency(Client, self)
            .set_type_dependency(type(self), self)
            .set_type_dependency(hikari.api.RESTClient, rest)
            .set_type_dependency(type(rest), rest)
        )
        if cache:
            self.set_type_dependency(hikari.api.Cache, cache).set_type_dependency(type(cache), cache)

        if events:
            self.set_type_dependency(hikari.api.EventManager, events).set_type_dependency(type(events), events)

        if server:
            self.set_type_dependency(hikari.api.InteractionServer, server).set_type_dependency(type(server), server)

        if shards:
            self.set_type_dependency(hikari.ShardAware, shards).set_type_dependency(type(shards), shards)

        if voice:
            self.set_type_dependency(hikari.api.VoiceComponent, voice).set_type_dependency(type(voice), voice)

        dependencies.set_standard_dependencies(self)
        self._schedule_startup_registers(
            set_global_commands,
            declare_global_commands,
            command_ids,
            message_ids=message_ids,
            user_ids=user_ids,
            _stack_level=_stack_level,
        )

    def _schedule_startup_registers(
        self,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        _stack_level: int = 0,
    ) -> None:

        if set_global_commands:
            warnings.warn(
                "The `set_global_commands` argument is deprecated since v2.1.1a1. "
                "Use `declare_global_commands` instead.",
                DeprecationWarning,
                stacklevel=3 + _stack_level,
            )

        declare_global_commands = declare_global_commands or set_global_commands
        if isinstance(declare_global_commands, collections.Sequence):
            if command_ids and len(declare_global_commands) > 1:
                raise ValueError(
                    "Cannot provide specific command_ids while automatically "
                    "declaring commands marked as 'global' in multiple-guilds on startup"
                )

            for guild in declare_global_commands:
                _LOGGER.info("Registering startup command declarer for %s guild", guild)
                self.add_client_callback(
                    ClientCallbackNames.STARTING,
                    _StartDeclarer(self, guild, command_ids=command_ids, message_ids=message_ids, user_ids=user_ids),
                )

        elif isinstance(declare_global_commands, bool):
            if declare_global_commands:
                _LOGGER.info("Registering startup command declarer for global commands")
                if not command_ids and not message_ids and not user_ids:
                    _LOGGER.warning(
                        "No command IDs passed for startup command declarer, this could lead to previously set "
                        "command permissions being lost when commands are renamed."
                    )

                self.add_client_callback(
                    ClientCallbackNames.STARTING,
                    _StartDeclarer(
                        self, hikari.UNDEFINED, command_ids=command_ids, message_ids=message_ids, user_ids=user_ids
                    ),
                )

            elif command_ids:
                raise ValueError("Cannot pass command IDs when not declaring global commands")

        else:
            self.add_client_callback(
                ClientCallbackNames.STARTING,
                _StartDeclarer(
                    self, declare_global_commands, command_ids=command_ids, message_ids=message_ids, user_ids=user_ids
                ),
            )

    @classmethod
    def from_gateway_bot(
        cls,
        bot: hikari.GatewayBotAware,
        /,
        *,
        event_managed: bool = True,
        injector: typing.Optional[alluka.abc.Client] = None,
        mention_prefix: bool = False,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
    ) -> Client:
        """Build a `Client` from a `hikari.traits.GatewayBotAware` instance.

        Notes
        -----
        * This implicitly defaults the client to human only mode.
        * This sets type dependency injectors for the hikari traits present in
          `bot` (including `hikari.traits.GatewayBotAware`).
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
        injector : alluka.abc.Client | None
            The alluka client this should use for dependency injection.

            If not provided then the client will initialise its own DI client.
        mention_prefix : bool
            Whether or not mention prefixes should be automatically set when this
            client is first started.

            Defaults to `False` and it should be noted that this only applies to
            message commands.
        declare_global_commands : hikari.SnowflakeishSequence[hikari.PartialGuild] | hikari.Snowflakeish | hikari.PartialGuild | bool
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally. This can be useful for testing/debug purposes as slash
            commands may take up to an hour to propagate globally but will
            immediately propagate when set on a specific guild.
        set_global_commands : hikari.Snowflakeish | hikari.PartialGuild | bool
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of top level command names to IDs of the commands to update.

            This field is complementary to `declare_global_commands` and, while it
            isn't necessarily required, this will in some situations help avoid
            permissions which were previously set for a command from being lost
            after a rename.

            This currently isn't supported when multiple guild IDs are passed for
            `declare_global_commands`.
        message_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        """  # noqa: E501 - line too long
        return (
            cls(
                rest=bot.rest,
                cache=bot.cache,
                events=bot.event_manager,
                shards=bot,
                voice=bot.voice,
                event_managed=event_managed,
                injector=injector,
                mention_prefix=mention_prefix,
                declare_global_commands=declare_global_commands,
                set_global_commands=set_global_commands,
                command_ids=command_ids,
                message_ids=message_ids,
                user_ids=user_ids,
                _stack_level=1,
            )
            .set_human_only()
            .set_hikari_trait_injectors(bot)
        )

    @classmethod
    def from_rest_bot(
        cls,
        bot: hikari.RESTBotAware,
        /,
        *,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        injector: typing.Optional[alluka.abc.Client] = None,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
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
        declare_global_commands : hikari.SnowflakeishSequence[hikari.PartialGuild] | hikari.Snowflakeish | hikari.PartialGuild | bool
            Whether or not to automatically set global slash commands when this
            client is first started. Defaults to `False`.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally. This can be useful for testing/debug purposes as slash
            commands may take up to an hour to propagate globally but will
            immediately propagate when set on a specific guild.
        injector : alluka.abc.Client | None
            The alluka client this should use for dependency injection.

            If not provided then the client will initialise its own DI client.
        set_global_commands : hikari.Snowflakeish | hikari.PartialGuild | bool
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids : collections.abc.Mapping[str, hikari.Snowflakeis | hikari.PartialCommand] | None
            If provided, a mapping of top level command names to IDs of the
            existing commands to update.

            This will be used for all application commands but in cases where
            commands have overlapping names, `message_ids` and `user_ids` will
            take priority over this for their relevant command type.

            This field is complementary to `declare_global_commands` and, while it
            isn't necessarily required, this will in some situations help avoid
            permissions which were previously set for a command from being lost
            after a rename.

            This currently isn't supported when multiple guild IDs are passed for
            `declare_global_commands`.
        message_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids : collections.abc.Mapping[str, hikari.Snowflakeish | hikari.PartialCommand] | None
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        """  # noqa: E501 - line too long
        return cls(
            rest=bot.rest,
            server=bot.interaction_server,
            declare_global_commands=declare_global_commands,
            injector=injector,
            set_global_commands=set_global_commands,
            command_ids=command_ids,
            message_ids=message_ids,
            user_ids=user_ids,
            _stack_level=1,
        ).set_hikari_trait_injectors(bot)

    async def __aenter__(self) -> Client:
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: typing.Optional[type[BaseException]],
        exc: typing.Optional[BaseException],
        exc_traceback: typing.Optional[types.TracebackType],
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
    def injector(self) -> alluka.abc.Client:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._injector

    @property
    def is_human_only(self) -> bool:
        """Whether this client is only executing for non-bot/webhook users messages."""
        return _check_human in self._checks

    @property
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._cache

    @property
    def checks(self) -> collections.Collection[tanjun_abc.CheckSig]:
        """Collection of the level `tanjun.abc.Context` checks registered to this client.

        .. note::
            These may be taking advantage of the standard dependency injection.
        """
        return self._checks.copy()

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
        return utilities.CastedView(
            self._listeners,
            lambda x: [callback.callback for callback in x.values()],
        )

    @property
    def is_alive(self) -> bool:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._loop is not None

    @property
    def loop(self) -> typing.Optional[asyncio.AbstractEventLoop]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._loop

    @property
    def hooks(self) -> typing.Optional[tanjun_abc.AnyHooks]:
        """Top level `tanjun.abc.AnyHooks` set for this client.

        These are called during both message, menu and slash command execution.
        """
        return self._hooks

    @property
    def menu_hooks(self) -> typing.Optional[tanjun_abc.MenuHooks]:
        """Top level `tanjun.abc.MenuHooks` set for this client.

        These are only called during menu command execution.
        """
        return self._menu_hooks

    @property
    def message_hooks(self) -> typing.Optional[tanjun_abc.MessageHooks]:
        """Top level `tanjun.abc.MessageHooks` set for this client.

        These are only called during message command execution.
        """
        return self._message_hooks

    @property
    def slash_hooks(self) -> typing.Optional[tanjun_abc.SlashHooks]:
        """Top level `tanjun.abc.SlashHooks` set for this client.

        These are only called during slash command execution.
        """
        return self._slash_hooks

    @property
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._metadata

    @property
    def prefix_getter(self) -> typing.Optional[PrefixGetterSig]:
        """Prefix getter method set for this client.

        For more information on this callback's signature see `PrefixGetter`.
        """
        return self._prefix_getter

    @property
    def prefixes(self) -> collections.Collection[str]:
        """Collection of the standard prefixes set for this client."""
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
    def shards(self) -> typing.Optional[hikari.ShardAware]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._shards

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._voice

    async def _on_starting_event(self, _: hikari.StartingEvent, /) -> None:
        await self.open()

    async def _on_stopping_event(self, _: hikari.StoppingEvent, /) -> None:
        await self.close()

    async def clear_application_commands(
        self,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        if application is None:
            application = self._cached_application_id or await self.fetch_rest_application_id()

        await self._rest.set_application_commands(application, (), guild=guild)

    async def set_global_commands(
        self,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        force: bool = False,
    ) -> collections.Sequence[hikari.PartialCommand]:
        """Alias of `Client.declare_global_commands`.

        .. deprecated:: v2.1.1a1
            Use `Client.declare_global_commands` instead.
        """
        warnings.warn(
            "The `Client.set_global_commands` method has been deprecated since v2.1.1a1. "
            "Use `Client.declare_global_commands` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.declare_global_commands(application=application, guild=guild, force=force)

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
        # <<inherited docstring from tanjun.abc.Client>>.
        commands = itertools.chain(
            self.iter_slash_commands(global_only=True), self.iter_menu_commands(global_only=True)
        )
        return await self.declare_application_commands(
            commands,
            command_ids,
            application=application,
            guild=guild,
            message_ids=message_ids,
            user_ids=user_ids,
            force=force,
        )

    @typing.overload
    async def declare_application_command(
        self,
        command: tanjun_abc.BaseSlashCommand,
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.SlashCommand:
        ...

    @typing.overload
    async def declare_application_command(
        self,
        command: tanjun_abc.MenuCommand[typing.Any, typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.ContextMenuCommand:
        ...

    @typing.overload
    async def declare_application_command(
        self,
        command: tanjun_abc.AppCommand[typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        ...

    async def declare_application_command(
        self,
        command: tanjun_abc.AppCommand[typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        # <<inherited docstring from tanjun.abc.Client>>.
        builder = command.build()
        application = application or self._cached_application_id or await self.fetch_rest_application_id()

        if command_id:
            if isinstance(builder, hikari.api.SlashCommandBuilder):
                description: hikari.UndefinedOr[str] = builder.description
                options: hikari.UndefinedOr[collections.Sequence[hikari.CommandOption]] = builder.options

            else:
                description = hikari.UNDEFINED
                options = hikari.UNDEFINED

            response = await self._rest.edit_application_command(
                application,
                command_id,
                guild=guild,
                name=builder.name,
                description=description,
                options=options,
            )

        else:
            if isinstance(builder, hikari.api.SlashCommandBuilder):
                response = await self._rest.create_slash_command(
                    application,
                    guild=guild,
                    name=builder.name,
                    description=builder.description,
                    options=builder.options,
                )

            elif isinstance(builder, hikari.api.ContextMenuCommandBuilder):
                response = await self._rest.create_context_menu_command(
                    application,
                    builder.type,
                    builder.name,
                    guild=guild,
                    default_permission=builder.default_permission,
                )

            else:
                raise NotImplementedError(f"Unknown command builder type {builder.type}.")

        if not guild:
            command.set_tracked_command(response)  # TODO: is this fine?

        return response

    async def declare_application_commands(
        self,
        commands: collections.Iterable[tanjun_abc.AppCommand[typing.Any]],
        /,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        force: bool = False,
    ) -> collections.Sequence[hikari.PartialCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        command_ids = command_ids or {}
        names_to_commands: dict[tuple[hikari.CommandType, str], tanjun_abc.AppCommand[typing.Any]] = {}
        conflicts: set[tuple[hikari.CommandType, str]] = set()
        builders: dict[tuple[hikari.CommandType, str], hikari.api.CommandBuilder] = {}
        message_count = 0
        slash_count = 0
        user_count = 0

        for command in commands:
            key = (command.type, command.name)
            names_to_commands[key] = command
            if key in builders:
                conflicts.add(key)

            builder = command.build()
            command_id = None
            if builder.type is hikari.CommandType.USER:
                user_count += 1
                if user_ids:
                    command_id = user_ids.get(command.name)

            elif builder.type is hikari.CommandType.MESSAGE:
                message_count += 1
                if message_ids:
                    command_id = message_ids.get(command.name)

            elif builder.type is hikari.CommandType.SLASH:
                slash_count += 1

            if command_id := (command_id or command_ids.get(command.name)):
                builder.set_id(hikari.Snowflake(command_id))

            builders[key] = builder

        if conflicts:
            raise ValueError(
                "Couldn't declare commands due to conflicts. The following command names have more than one command "
                "registered for them " + ", ".join(f"{type_}:{name}" for type_, name in conflicts)
            )

        if message_count > 5:
            raise ValueError("You can only declare up to 5 top level message context menus in a guild or globally")

        if slash_count > 100:
            raise ValueError("You can only declare up to 100 top level slash commands in a guild or globally")

        if user_count > 5:
            raise ValueError("You can only declare up to 5 top level message context menus in a guild or globally")

        if not application:
            application = self._cached_application_id or await self.fetch_rest_application_id()

        target_type = "global" if guild is hikari.UNDEFINED else f"guild {int(guild)}"

        if not force:
            registered_commands = await self._rest.fetch_application_commands(application, guild=guild)
            if len(registered_commands) == len(builders) and all(
                _cmp_command(builders.get((c.type, c.name)), c) for c in registered_commands
            ):
                _LOGGER.info(
                    "Skipping bulk declare for %s application commands since they're already declared", target_type
                )
                return registered_commands

        _LOGGER.info("Bulk declaring %s %s application commands", len(builders), target_type)
        responses = await self._rest.set_application_commands(application, list(builders.values()), guild=guild)

        for response in responses:
            if not guild:
                names_to_commands[(response.type, response.name)].set_tracked_command(response)  # TODO: is this fine?

            if (expected_id := command_ids.get(response.name)) and hikari.Snowflake(expected_id) != response.id:
                _LOGGER.warning(
                    "ID mismatch found for %s %s command %r, expected %s but got %s. "
                    "This suggests that any previous permissions set for this command will have been lost.",
                    target_type,
                    response.type,
                    response.name,
                    expected_id,
                    response.id,
                )

        _LOGGER.info("Successfully declared %s (top-level) %s commands", len(responses), target_type)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Declared %s command ids; %s",
                target_type,
                ", ".join(f"{response.type}-{response.name}: {response.id}" for response in responses),
            )

        return responses

    def set_auto_defer_after(self: _ClientT, time: typing.Optional[float], /) -> _ClientT:
        """Set when this client should automatically defer execution of commands.

        .. warning::
            If `time` is set to `None` then automatic deferrals will be disabled.
            This may lead to unexpected behaviour.

        Parameters
        ----------
        time : float | None
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
        Self
            This component to enable method chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_hikari_trait_injectors(self: _ClientT, bot: hikari.RESTAware, /) -> _ClientT:
        """Set type based dependency injection based on the hikari traits found in `bot`.

        This is a short hand for calling `Client.add_type_dependency` for all
        the hikari trait types `bot` is valid for with bot.

        Parameters
        ----------
        bot : hikari.RESTAware
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
        message : str | None
            The message to respond with when an interaction command isn't found.
        """
        return self.set_menu_not_found(message).set_slash_not_found(message)

    def set_menu_not_found(self: _ClientT, message: typing.Optional[str], /) -> _ClientT:
        """Set the response message for when a menu command is not found.


        .. warning::
            Setting this to `None` may lead to unexpected behaviour (especially
            when the client is still set to auto-defer interactions) and should
            only be done if you know what you're doing.

        Parameters
        ----------
        message : str | None
            The message to respond with when a menu command isn't found.
        """
        self._menu_not_found = message
        return self

    def set_slash_not_found(self: _ClientT, message: typing.Optional[str], /) -> _ClientT:
        """Set the response message for when a slash command is not found.

        .. warning::
            Setting this to `None` may lead to unexpected behaviour (especially
            when the client is still set to auto-defer interactions) and should
            only be done if you know what you're doing.

        Parameters
        ----------
        message : str | None
            The message to respond with when a slash command isn't found.
        """
        self._slash_not_found = message
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

    def set_autocomplete_ctx_maker(
        self: _ClientT, maker: _AutocompleteContextMakerProto = context.AutocompleteContext, /
    ) -> _ClientT:
        """Set the autocomplete context maker to use when creating contexts.

        .. warning::
            The caller must return an instance of `tanjun.context.AutocompleteContext`
            rather than just any implementation of the AutocompleteContext abc
            due to this client relying on implementation detail of
            `tanjun.context.AutocompleteContext`.

        Parameters
        ----------
        maker : _AutocompleteContextMakerProto
            The autocomplete context maker to use.

            This is a callback which should match the signature of
            `tanjun.context.AutocompleteContext.__init__` and return
            an instance of `tanjun.context.AutocompleteContext`.

            This defaults to `tanjun.context.AutocompleteContext`.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._make_autocomplete_context = maker
        return self

    def set_menu_ctx_maker(self: _ClientT, maker: _MenuContextMakerProto = context.MenuContext, /) -> _ClientT:
        """Set the autocomplete context maker to use when creating contexts.

        .. warning::
            The caller must return an instance of `tanjun.context.MenuContext`
            rather than just any implementation of the MenuContext abc
            due to this client relying on implementation detail of
            `tanjun.context.MenuContext`.

        Parameters
        ----------
        maker : _MenuContextMakerProto
            The autocomplete context maker to use.

            This is a callback which should match the signature of
            `tanjun.context.MenuContext.__init__` and return
            an instance of `tanjun.context.MenuContext`.

            This defaults to `tanjun.context.MenuContext`.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._make_menu_context = maker
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

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._make_message_context = maker
        return self

    def set_metadata(self: _ClientT, key: typing.Any, value: typing.Any, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._metadata[key] = value
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

        Returns
        -------
        Self
            This component to enable method chaining.
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
            self.add_check(_check_human)

        else:
            try:
                self.remove_check(_check_human)
            except ValueError:
                pass

        return self

    def add_check(self: _ClientT, check: tanjun_abc.CheckSig, /) -> _ClientT:
        """Add a generic check to this client.

        This will be applied to both message and slash command execution.

        Parameters
        ----------
        check : tanjun.abc.CheckSig
            The check to add. This may be either synchronous or asynchronous
            and must take one positional argument of type `tanjun.abc.Context`
            with dependency injection being supported for its keyword arguments.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        if check not in self._checks:
            self._checks.append(check)

        return self

    def remove_check(self: _ClientT, check: tanjun_abc.CheckSig, /) -> _ClientT:
        """Remove a check from the client.

        Parameters
        ----------
        check : tanjun.abc.CheckSig
            The check to remove.

        Raises
        ------
        ValueError
            If the check was not previously added.
        """
        self._checks.remove(check)
        return self

    def with_check(self, check: _CheckSigT, /) -> _CheckSigT:
        """Add a check to this client through a decorator call.

        Parameters
        ----------
        check : tanjun.abc.CheckSig
            The check to add. This may be either synchronous or asynchronous
            and must take one positional argument of type `tanjun.abc.Context`
            with dependency injection being supported for its keyword arguments.

        Returns
        -------
        tanjun.abc.CheckSig
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

        if self._loop:
            self._loop.create_task(component.open())
            self._loop.create_task(self.dispatch_client_callback(ClientCallbackNames.COMPONENT_ADDED, component))

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

        if self._loop:
            self._loop.create_task(component.close(unbind=True))
            self._loop.create_task(
                self.dispatch_client_callback(ClientCallbackNames.COMPONENT_REMOVED, stored_component)
            )

        else:
            stored_component.unbind_client(self)

        return self

    def remove_component_by_name(self: _ClientT, name: str, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self.remove_component(self._components[name])

    def add_client_callback(
        self: _ClientT, name: typing.Union[str, tanjun_abc.ClientCallbackNames], callback: tanjun_abc.MetaEventSig, /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        try:
            if callback in self._client_callbacks[name]:
                return self

            self._client_callbacks[name].append(callback)
        except KeyError:
            self._client_callbacks[name] = [callback]

        return self

    async def dispatch_client_callback(
        self, name: typing.Union[str, tanjun_abc.ClientCallbackNames], /, *args: typing.Any
    ) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        if callbacks := self._client_callbacks.get(name):
            calls = (_wrap_client_callback(self, callback, args) for callback in callbacks)
            await asyncio.gather(*calls)

    def get_client_callbacks(
        self, name: typing.Union[str, tanjun_abc.ClientCallbackNames], /
    ) -> collections.Collection[tanjun_abc.MetaEventSig]:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        if result := self._client_callbacks.get(name):
            return result.copy()

        return ()

    def remove_client_callback(
        self: _ClientT, name: typing.Union[str, tanjun_abc.ClientCallbackNames], callback: tanjun_abc.MetaEventSig, /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        self._client_callbacks[name].remove(callback)
        if not self._client_callbacks[name]:
            del self._client_callbacks[name]

        return self

    def with_client_callback(
        self, name: typing.Union[str, tanjun_abc.ClientCallbackNames], /
    ) -> collections.Callable[[_MetaEventSigT], _MetaEventSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: _MetaEventSigT, /) -> _MetaEventSigT:
            self.add_client_callback(name, callback)
            return callback

        return decorator

    def add_listener(
        self: _ClientT, event_type: type[hikari.Event], callback: tanjun_abc.ListenerCallbackSig, /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        injected = self.injector.as_async_self_injecting(callback)
        try:
            if callback in self._listeners[event_type]:
                return self

            self._listeners[event_type][callback] = injected

        except KeyError:
            self._listeners[event_type] = {callback: injected}

        if self._loop and self._events:
            self._events.subscribe(event_type, injected.__call__)

        return self

    def remove_listener(
        self: _ClientT, event_type: type[hikari.Event], callback: tanjun_abc.ListenerCallbackSig, /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        callbacks = self._listeners[event_type]

        try:
            registered_callback = callbacks.pop(callback)
        except KeyError:
            raise ValueError(callback) from None

        if not callbacks:
            del self._listeners[event_type]

        if self._loop and self._events:
            self._events.unsubscribe(event_type, registered_callback.__call__)

        return self

    def with_listener(
        self, event_type: type[hikari.Event], /
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: _ListenerCallbackSigT, /) -> _ListenerCallbackSigT:
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
        prefixes : collections.abc.Iterable[str] | str
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
        getter : PrefixGetterSig | None
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
        self._prefix_getter = getter
        return self

    def with_prefix_getter(self, getter: _PrefixGetterSigT, /) -> _PrefixGetterSigT:
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
        PrefixGetterSig
            The registered callback.
        """
        self.set_prefix_getter(getter)
        return getter

    def iter_commands(self) -> collections.Iterator[tanjun_abc.ExecutableCommand[tanjun_abc.Context]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain(
            self.iter_menu_commands(global_only=False),
            self.iter_message_commands(),
            self.iter_slash_commands(global_only=False),
        )

    @typing.overload
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[  # noqa: A002 - Shadowing a builtin name.
            typing.Literal[hikari.CommandType.MESSAGE]
        ] = None,
    ) -> collections.Iterator[tanjun_abc.MenuCommand[typing.Any, typing.Literal[hikari.CommandType.MESSAGE]]]:
        ...

    @typing.overload
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[typing.Literal[hikari.CommandType.USER]] = None,  # noqa: A002 - Shadowing a builtin name.
    ) -> collections.Iterator[tanjun_abc.MenuCommand[typing.Any, typing.Literal[hikari.CommandType.USER]]]:
        ...

    @typing.overload
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[  # noqa: A002 - Shadowing a builtin name.
            typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER]
        ] = None,
    ) -> collections.Iterator[tanjun_abc.MenuCommand[typing.Any, typing.Any]]:
        ...

    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[  # noqa: A002 - Shadowing a builtin name.
            typing.Literal[hikari.CommandType.MESSAGE, hikari.CommandType.USER]
        ] = None,
    ) -> collections.Iterator[tanjun_abc.MenuCommand[typing.Any, typing.Any]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        if global_only:
            return filter(lambda c: c.is_global, self.iter_menu_commands(global_only=False, type=type))

        if type:
            if type not in _MENU_TYPES:
                raise ValueError("Command type filter must be USER or MESSAGE")

            return filter(lambda c: c.type == type, self.iter_menu_commands(global_only=global_only, type=None))

        return itertools.chain.from_iterable(component.menu_commands for component in self.components)

    def iter_message_commands(self) -> collections.Iterator[tanjun_abc.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(component.message_commands for component in self.components)

    def iter_slash_commands(self, *, global_only: bool = False) -> collections.Iterator[tanjun_abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        if global_only:
            return filter(lambda c: c.is_global, self.iter_slash_commands(global_only=False))

        return itertools.chain.from_iterable(component.slash_commands for component in self.components)

    def check_message_name(
        self, name: str, /
    ) -> collections.Iterator[tuple[str, tanjun_abc.MessageCommand[typing.Any]]]:
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
            for prefix in await ctx.call_with_async_di(self._prefix_getter, ctx):
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
        callback: collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]],
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
        if not self._loop:
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

            for event_type_, listeners in self._listeners.items():
                for listener in listeners.values():
                    self._try_unsubscribe(self._events, event_type_, listener.__call__)

        if deregister_listeners and self._server:
            self._server.set_listener(hikari.CommandInteraction, None)
            self._server.set_listener(hikari.AutocompleteInteraction, None)

        await asyncio.gather(*(component.close() for component in self._components.copy().values()))

        self._loop = None
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
        if self._loop:
            raise RuntimeError("Client is already alive")

        self._loop = asyncio.get_running_loop()
        self._is_closing = False
        await self.dispatch_client_callback(ClientCallbackNames.STARTING)

        if self._grab_mention_prefix:
            user: typing.Optional[hikari.OwnUser] = None
            if self._cache:
                user = self._cache.get_me()

            if not user and (user_cache := self.get_type_dependency(dependencies.SingleStoreCache[hikari.OwnUser])):
                user = await user_cache.get(default=None)

            if not user:
                user = await self._rest.fetch_my_user()

            for prefix in f"<@{user.id}>", f"<@!{user.id}>":
                if prefix not in self._prefixes:
                    self._prefixes.append(prefix)

            self._grab_mention_prefix = False

        await asyncio.gather(*(component.open() for component in self._components.copy().values()))

        if register_listeners and self._events:
            if event_type := self._accepts.get_event_type():
                self._events.subscribe(event_type, self.on_message_create_event)

            self._events.subscribe(hikari.InteractionCreateEvent, self.on_interaction_create_event)

            for event_type_, listeners in self._listeners.items():
                for listener in listeners.values():
                    self._events.subscribe(event_type_, listener.__call__)

        if register_listeners and self._server:
            self._server.set_listener(hikari.CommandInteraction, self.on_command_interaction_request)
            self._server.set_listener(hikari.AutocompleteInteraction, self.on_autocomplete_interaction_request)

        self._loop.create_task(self.dispatch_client_callback(ClientCallbackNames.STARTED))

    async def fetch_rest_application_id(self) -> hikari.Snowflake:
        """Fetch the ID of the application this client is linked to.

        Returns
        -------
        hikari.Snowflake
            The application ID of the application this client is linked to.
        """
        if self._cached_application_id:
            return self._cached_application_id

        application_cache = self.get_type_dependency(
            dependencies.SingleStoreCache[hikari.Application]
        ) or self.get_type_dependency(dependencies.SingleStoreCache[hikari.AuthorizationApplication])
        if application_cache and (application := await application_cache.get(default=None)):
            self._cached_application_id = application.id
            return application.id

        if self._rest.token_type == hikari.TokenType.BOT:
            self._cached_application_id = hikari.Snowflake(await self._rest.fetch_application())

        else:
            self._cached_application_id = hikari.Snowflake((await self._rest.fetch_authorization()).application)

        return self._cached_application_id

    def set_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.AnyHooks], /) -> _ClientT:
        """Set the general command execution hooks for this client.

        The callbacks within this hook will be added to every slash and message
        command execution started by this client.

        Parameters
        ----------
        hooks : tanjun.abc.AnyHooks | None
            The general command execution hooks to set for this client.

            Passing `None` will remove all hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._hooks = hooks
        return self

    def set_menu_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.MenuHooks], /) -> _ClientT:
        """Set the menu command execution hooks for this client.

        The callbacks within this hook will be added to every menu command
        execution started by this client.

        Parameters
        ----------
        hooks : tanjun.abc.MenuHooks | None
            The menu context specific command execution hooks to set for this
            client.

            Passing `None` will remove the hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._menu_hooks = hooks
        return self

    def set_slash_hooks(self: _ClientT, hooks: typing.Optional[tanjun_abc.SlashHooks], /) -> _ClientT:
        """Set the slash command execution hooks for this client.

        The callbacks within this hook will be added to every slash command
        execution started by this client.

        Parameters
        ----------
        hooks : tanjun.abc.SlashHooks | None
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
        hooks : tanjun.abc.MessageHooks | None
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

    def _call_loaders(
        self, module_path: typing.Union[str, pathlib.Path], loaders: list[tanjun_abc.ClientLoader], /
    ) -> None:
        found = False
        for loader in loaders:
            if loader.load(self):
                found = True

        if not found:
            raise errors.ModuleMissingLoaders(f"Didn't find any loaders in {module_path}", module_path)

    def _call_unloaders(
        self, module_path: typing.Union[str, pathlib.Path], loaders: list[tanjun_abc.ClientLoader], /
    ) -> None:
        found = False
        for loader in loaders:
            if loader.unload(self):
                found = True

        if not found:
            raise errors.ModuleMissingLoaders(f"Didn't find any unloaders in {module_path}", module_path)

    def _load_module(
        self, module_path: typing.Union[str, pathlib.Path]
    ) -> collections.Generator[collections.Callable[[], types.ModuleType], types.ModuleType, None]:
        if isinstance(module_path, str):
            if module_path in self._modules:
                raise errors.ModuleStateConflict(f"module {module_path} already loaded", module_path)

            _LOGGER.info("Loading from %s", module_path)
            module = yield lambda: importlib.import_module(module_path)

            with _WrapLoadError(errors.FailedModuleLoad):
                self._call_loaders(module_path, _get_loaders(module, module_path))

            self._modules[module_path] = module

        else:
            if module_path in self._path_modules:
                raise errors.ModuleStateConflict(f"Module at {module_path} already loaded", module_path)

            _LOGGER.info("Loading from %s", module_path)
            module = yield lambda: _get_path_module(module_path)

            with _WrapLoadError(errors.FailedModuleLoad):
                self._call_loaders(module_path, _get_loaders(module, module_path))

            self._path_modules[module_path] = module

    def load_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path]) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        for module_path in modules:
            if isinstance(module_path, pathlib.Path):
                module_path = _normalize_path(module_path)

            generator = self._load_module(module_path)
            load_module = next(generator)
            with _WrapLoadError(errors.FailedModuleLoad):
                module = load_module()

            try:
                generator.send(module)
            except StopIteration:
                pass
            else:
                raise RuntimeError("Generator didn't finish")

        return self

    async def load_modules_async(self, *modules: typing.Union[str, pathlib.Path]) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        loop = asyncio.get_running_loop()
        for module_path in modules:
            if isinstance(module_path, pathlib.Path):
                module_path = await loop.run_in_executor(None, _normalize_path, module_path)

            generator = self._load_module(module_path)
            load_module = next(generator)
            with _WrapLoadError(errors.FailedModuleLoad):
                module = await loop.run_in_executor(None, load_module)

            try:
                generator.send(module)
            except StopIteration:
                pass
            else:
                raise RuntimeError("Generator didn't finish")

    def unload_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path]) -> _ClientT:
        # <<inherited docstring from tanjun.ab.Client>>.
        for module_path in modules:
            if isinstance(module_path, str):
                modules_dict: dict[typing.Any, types.ModuleType] = self._modules

            else:
                modules_dict = self._path_modules
                module_path = _normalize_path(module_path)

            module = modules_dict.get(module_path)
            if not module:
                raise errors.ModuleStateConflict(f"Module {module_path!s} not loaded", module_path)

            _LOGGER.info("Unloading from %s", module_path)
            with _WrapLoadError(errors.FailedModuleUnload):
                self._call_unloaders(module_path, _get_loaders(module, module_path))

            del modules_dict[module_path]

        return self

    def _reload_module(
        self, module_path: typing.Union[str, pathlib.Path]
    ) -> collections.Generator[collections.Callable[[], types.ModuleType], types.ModuleType, None]:
        if isinstance(module_path, str):
            old_module = self._modules.get(module_path)

            def load_module() -> types.ModuleType:
                assert old_module
                return importlib.reload(old_module)

            modules_dict: dict[typing.Any, types.ModuleType] = self._modules

        else:
            old_module = self._path_modules.get(module_path)

            def load_module() -> types.ModuleType:
                assert isinstance(module_path, pathlib.Path)
                return _get_path_module(module_path)

            modules_dict = self._path_modules

        if not old_module:
            raise errors.ModuleStateConflict(f"Module {module_path} not loaded", module_path)

        _LOGGER.info("Reloading %s", module_path)

        old_loaders = _get_loaders(old_module, module_path)
        # We assert that the old module has unloaders early to avoid unnecessarily
        # importing the new module.
        if not any(loader.has_unload for loader in old_loaders):
            raise errors.ModuleMissingLoaders(f"Didn't find any unloaders in old {module_path}", module_path)

        module = yield load_module

        loaders = _get_loaders(module, module_path)

        # We assert that the new module has loaders early to avoid unnecessarily
        # unloading then rolling back when we know it's going to fail to load.
        if not any(loader.has_load for loader in loaders):
            raise errors.ModuleMissingLoaders(f"Didn't find any loaders in new {module_path}", module_path)

        with _WrapLoadError(errors.FailedModuleUnload):
            # This will never raise MissingLoaders as we assert this earlier
            self._call_unloaders(module_path, old_loaders)

        try:
            # This will never raise MissingLoaders as we assert this earlier
            self._call_loaders(module_path, loaders)
        except Exception as exc:
            self._call_loaders(module_path, old_loaders)
            raise errors.FailedModuleLoad from exc
        else:
            modules_dict[module_path] = module

    def reload_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path]) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        for module_path in modules:
            if isinstance(module_path, pathlib.Path):
                module_path = _normalize_path(module_path)

            generator = self._reload_module(module_path)
            load_module = next(generator)
            with _WrapLoadError(errors.FailedModuleLoad):
                module = load_module()

            try:
                generator.send(module)
            except StopIteration:
                pass
            else:
                raise RuntimeError("Generator didn't finish")

        return self

    async def reload_modules_async(self, *modules: typing.Union[str, pathlib.Path]) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        loop = asyncio.get_running_loop()
        for module_path in modules:
            if isinstance(module_path, pathlib.Path):
                module_path = await loop.run_in_executor(None, _normalize_path, module_path)

            generator = self._reload_module(module_path)
            load_module = next(generator)
            with _WrapLoadError(errors.FailedModuleLoad):
                module = await loop.run_in_executor(None, load_module)

            try:
                generator.send(module)

            except StopIteration:
                pass

            else:
                raise RuntimeError("Generator didn't finish")

    def set_type_dependency(self: _ClientT, type_: type[_T], value: _T, /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.set_type_dependency(type_, value)
        return self

    def get_type_dependency(self, type_: type[_T], /) -> typing.Union[_T, alluka.abc.Undefined]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._injector.get_type_dependency(type_)

    def remove_type_dependency(self: _ClientT, type_: type[typing.Any], /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.remove_type_dependency(type_)
        return self

    def set_callback_override(
        self: _ClientT, callback: alluka.abc.CallbackSig[_T], override: alluka.abc.CallbackSig[_T], /
    ) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.set_callback_override(callback, override)
        return self

    def get_callback_override(
        self, callback: alluka.abc.CallbackSig[_T], /
    ) -> typing.Optional[alluka.abc.CallbackSig[_T]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._injector.get_callback_override(callback)

    def remove_callback_override(self: _ClientT, callback: alluka.abc.CallbackSig[_T], /) -> _ClientT:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.remove_callback_override(callback)
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

        ctx = self._make_message_context(client=self, content=event.message.content, message=event.message)
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

    def _get_menu_hooks(self) -> typing.Optional[set[tanjun_abc.MenuHooks]]:
        hooks: typing.Optional[set[tanjun_abc.MenuHooks]] = None
        if self._hooks and self._menu_hooks:
            hooks = {self._hooks, self._menu_hooks}

        elif self._hooks:
            hooks = {self._hooks}

        elif self._menu_hooks:
            hooks = {self._menu_hooks}

        return hooks

    async def _on_menu_not_found(self, ctx: tanjun_abc.MenuContext) -> None:
        await self.dispatch_client_callback(ClientCallbackNames.MENU_COMMAND_NOT_FOUND, ctx)
        if self._menu_not_found and not ctx.has_responded:
            await ctx.create_initial_response(self._menu_not_found)

    async def _on_slash_not_found(self, ctx: tanjun_abc.SlashContext) -> None:
        await self.dispatch_client_callback(ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)
        if self._slash_not_found and not ctx.has_responded:
            await ctx.create_initial_response(self._slash_not_found)

    async def on_gateway_autocomplete_create(self, interaction: hikari.AutocompleteInteraction, /) -> None:
        """Execute command autocomplete based on a received gateway interaction create.

        Parameters
        ----------
        interaction : hikari.CommandInteraction
            The interaction to execute a command based on.
        """
        ctx = self._make_autocomplete_context(self, interaction)
        for component in self._components.values():
            if coro := component.execute_autocomplete(ctx):
                await coro
                return

    async def on_gateway_command_create(self, interaction: hikari.CommandInteraction, /) -> None:
        """Execute an app command based on a received gateway interaction create.

        Parameters
        ----------
        interaction : hikari.CommandInteraction
            The interaction to execute a command based on.
        """
        if interaction.command_type is hikari.CommandType.SLASH:
            ctx: typing.Union[context.MenuContext, context.SlashContext] = self._make_slash_context(
                client=self,
                interaction=interaction,
                on_not_found=self._on_slash_not_found,
                default_to_ephemeral=self._defaults_to_ephemeral,
            )
            hooks: typing.Union[set[tanjun_abc.MenuHooks], set[tanjun_abc.SlashHooks], None] = self._get_slash_hooks()

        elif interaction.command_type in _MENU_TYPES:
            ctx = self._make_menu_context(
                client=self,
                interaction=interaction,
                on_not_found=self._on_menu_not_found,
                default_to_ephemeral=self._defaults_to_ephemeral,
            )
            hooks = self._get_menu_hooks()

        else:
            raise RuntimeError(f"Unknown command type {interaction.command_type}")

        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        try:
            if not await self.check(ctx):
                raise errors.HaltExecution

            for component in self._components.values():
                # This is set on each iteration to ensure that any component
                # state which was set to this isn't propagated to other components.
                ctx.set_ephemeral_default(self._defaults_to_ephemeral)
                if ctx.type is hikari.CommandType.SLASH:
                    assert isinstance(ctx, tanjun_abc.SlashContext)
                    coro = await component.execute_slash(ctx, hooks=typing.cast("set[tanjun_abc.SlashHooks]", hooks))

                else:
                    assert isinstance(ctx, tanjun_abc.MenuContext)
                    coro = await component.execute_menu(ctx, hooks=typing.cast("set[tanjun_abc.MenuHooks]", hooks))

                if coro:
                    return await coro

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            await ctx.respond(exc.message)
            return

        await ctx.mark_not_found()

    async def on_interaction_create_event(self, event: hikari.InteractionCreateEvent, /) -> None:
        """Handle a gateway interaction create event.

        .. note::
            This will execute application commands and autocomplete interactions.

        Parameters
        ----------
        event : hikari.events.interaction_events.InteractionCreateEvent
            The event to execute commands based on.
        """
        if event.interaction.type is hikari.InteractionType.APPLICATION_COMMAND:
            assert isinstance(event.interaction, hikari.CommandInteraction)
            return await self.on_gateway_command_create(event.interaction)

        if event.interaction.type is hikari.InteractionType.AUTOCOMPLETE:
            assert isinstance(event.interaction, hikari.AutocompleteInteraction)
            return await self.on_gateway_autocomplete_create(event.interaction)

    async def on_autocomplete_interaction_request(
        self, interaction: hikari.AutocompleteInteraction, /
    ) -> hikari.api.InteractionAutocompleteBuilder:
        """Execute a command autocomplete based on received REST requests.

        Parameters
        ----------
        interaction : hikari.AutocompleteInteraction
            The interaction to execute autocomplete based on.

        Returns
        -------
        hikari.api.InteractionAutocompleteBuilder
            The initial response to send back to Discord.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[hikari.api.InteractionAutocompleteBuilder] = loop.create_future()
        ctx = self._make_autocomplete_context(self, interaction, future=future)

        for component in self._components.values():
            if coro := component.execute_autocomplete(ctx):
                loop.create_task(coro)
                return await future

        raise RuntimeError(f"Autocomplete not found for {interaction!r}")

    async def on_command_interaction_request(
        self, interaction: hikari.CommandInteraction, /
    ) -> typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]:
        """Execute an app command based on received REST requests.

        Parameters
        ----------
        interaction : hikari.CommandInteraction
            The interaction to execute a command based on.

        Returns
        -------
        hikari.api.InteractionMessageBuilder | hikari.api.InteractionDeferredBuilder
            The initial response to send back to Discord.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future[
            typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]
        ] = loop.create_future()

        if interaction.command_type is hikari.CommandType.SLASH:
            ctx: typing.Union[context.MenuContext, context.SlashContext] = self._make_slash_context(
                client=self,
                interaction=interaction,
                on_not_found=self._on_slash_not_found,
                default_to_ephemeral=self._defaults_to_ephemeral,
                future=future,
            )
            hooks: typing.Union[set[tanjun_abc.MenuHooks], set[tanjun_abc.SlashHooks], None] = self._get_slash_hooks()

        elif interaction.command_type in _MENU_TYPES:
            ctx = self._make_menu_context(
                client=self,
                interaction=interaction,
                on_not_found=self._on_menu_not_found,
                default_to_ephemeral=self._defaults_to_ephemeral,
                future=future,
            )
            hooks = self._get_menu_hooks()

        else:
            raise RuntimeError(f"Unknown command type {interaction.command_type}")

        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        try:
            if not await self.check(ctx):
                raise errors.HaltExecution

            for component in self._components.values():
                # This is set on each iteration to ensure that any component
                # state which was set to this isn't propagated to other components.
                ctx.set_ephemeral_default(self._defaults_to_ephemeral)
                if ctx.type is hikari.CommandType.SLASH:
                    assert isinstance(ctx, tanjun_abc.SlashContext)
                    coro = await component.execute_slash(ctx, hooks=typing.cast("set[tanjun_abc.SlashHooks]", hooks))

                else:
                    assert isinstance(ctx, tanjun_abc.MenuContext)
                    coro = await component.execute_menu(ctx, hooks=typing.cast("set[tanjun_abc.MenuHooks]", hooks))

                if coro:
                    loop.create_task(coro)
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


def _normalize_path(path: pathlib.Path) -> pathlib.Path:
    try:  # TODO: test behaviour around this
        path = path.expanduser()
    except RuntimeError:
        pass  # A home directory couldn't be resolved, so we'll just use the path as-is.

    return path.resolve()


def _get_loaders(
    module: types.ModuleType, module_path: typing.Union[str, pathlib.Path], /
) -> list[tanjun_abc.ClientLoader]:
    exported = getattr(module, "__all__", None)
    if exported is not None and isinstance(exported, collections.Iterable):
        _LOGGER.debug("Scanning %s module based on its declared __all__)", module_path)
        exported = typing.cast("collections.Iterable[typing.Any]", exported)
        iterator = (getattr(module, name, None) for name in exported if isinstance(name, str))

    else:
        _LOGGER.debug("Scanning all public members on %s", module_path)
        iterator = (
            member
            for name, member in inspect.getmembers(module)
            if not name.startswith("_") or name.startswith("__") and name.endswith("__")
        )

    return [value for value in iterator if isinstance(value, tanjun_abc.ClientLoader)]


def _get_path_module(module_path: pathlib.Path, /) -> types.ModuleType:
    module_name = module_path.name.rsplit(".", 1)[0]
    spec = importlib_util.spec_from_file_location(module_name, module_path)

    # https://github.com/python/typeshed/issues/2793
    if not spec or not isinstance(spec.loader, importlib_abc.Loader):
        raise ModuleNotFoundError(f"Module not found at {module_path}", name=module_name, path=str(module_path))

    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _WrapLoadError:
    __slots__ = ("_error",)

    def __init__(self, error: collections.Callable[[], Exception], /) -> None:
        self._error = error

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: typing.Optional[type[BaseException]],
        exc: typing.Optional[BaseException],
        exc_tb: typing.Optional[types.TracebackType],
    ) -> None:
        if exc and isinstance(exc, Exception) and not isinstance(exc, errors.ModuleMissingLoaders):
            raise self._error() from exc  # noqa: R102 unnecessary parenthesis on raised exception
