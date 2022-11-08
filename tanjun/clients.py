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
    "InteractionAcceptsEnum",
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
import operator
import pathlib
import typing
import warnings
from collections import abc as collections

import alluka
import hikari
from hikari import traits as hikari_traits

from . import _internal
from . import abc as tanjun
from . import context
from . import dependencies
from . import errors
from . import hooks
from ._internal import localisation

if typing.TYPE_CHECKING:
    import types

    import typing_extensions
    from typing_extensions import Self

    _CheckSigT = typing.TypeVar("_CheckSigT", bound=tanjun.CheckSig)
    _ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound=tanjun.ListenerCallbackSig)
    _MetaEventSigT = typing.TypeVar("_MetaEventSigT", bound=tanjun.MetaEventSig)
    _PrefixGetterSigT = typing.TypeVar("_PrefixGetterSigT", bound="PrefixGetterSig")
    _T = typing.TypeVar("_T")
    _P = typing_extensions.ParamSpec("_P")

    class _AutocompleteContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun.Client,
            interaction: hikari.AutocompleteInteraction,
            *,
            future: typing.Optional[asyncio.Future[hikari.api.InteractionAutocompleteBuilder]] = None,
        ) -> context.AutocompleteContext:
            raise NotImplementedError

    class _MenuContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun.Client,
            interaction: hikari.CommandInteraction,
            register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
            *,
            default_to_ephemeral: bool = False,
            future: typing.Optional[
                asyncio.Future[
                    typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]
                ]
            ] = None,
            on_not_found: typing.Optional[
                collections.Callable[[tanjun.MenuContext], collections.Awaitable[None]]
            ] = None,
        ) -> context.MenuContext:
            raise NotImplementedError

    class _MessageContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun.Client,
            content: str,
            message: hikari.Message,
            register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
            *,
            triggering_name: str = "",
            triggering_prefix: str = "",
        ) -> context.MessageContext:
            raise NotImplementedError

    class _SlashContextMakerProto(typing.Protocol):
        def __call__(
            self,
            client: tanjun.Client,
            interaction: hikari.CommandInteraction,
            register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
            *,
            default_to_ephemeral: bool = False,
            future: typing.Optional[
                asyncio.Future[
                    typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]
                ]
            ] = None,
            on_not_found: typing.Optional[
                collections.Callable[[tanjun.SlashContext], collections.Awaitable[None]]
            ] = None,
        ) -> context.SlashContext:
            raise NotImplementedError


PrefixGetterSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, collections.Iterable[str]]]
"""Type hint of a callable used to get the prefix(es) for a specific guild.

This should be an asynchronous callable which returns an iterable of strings.

!!! note
    While dependency injection is supported for this, the first positional
    argument will always be a [tanjun.abc.MessageContext][].
"""

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun.clients")
_MENU_TYPES = frozenset((hikari.CommandType.MESSAGE, hikari.CommandType.USER))


class _LoaderDescriptor(tanjun.ClientLoader):  # Slots mess with functools.update_wrapper
    def __init__(
        self,
        callback: typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun.Client], None]],
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

    def load(self, client: tanjun.Client, /) -> bool:
        if self._must_be_std:
            if not isinstance(client, Client):
                raise ValueError("This loader requires instances of the standard Client implementation")

            self._callback(client)

        else:
            typing.cast("collections.Callable[[tanjun.Client], None]", self._callback)(client)

        return True

    def unload(self, _: tanjun.Client, /) -> bool:
        return False


class _UnloaderDescriptor(tanjun.ClientLoader):  # Slots mess with functools.update_wrapper
    def __init__(
        self,
        callback: typing.Union[collections.Callable[[Client], None], collections.Callable[[tanjun.Client], None]],
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

    def load(self, _: tanjun.Client, /) -> bool:
        return False

    def unload(self, client: tanjun.Client, /) -> bool:
        if self._must_be_std:
            if not isinstance(client, Client):
                raise ValueError("This unloader requires instances of the standard Client implementation")

            self._callback(client)

        else:
            typing.cast("collections.Callable[[tanjun.Client], None]", self._callback)(client)

        return True


@typing.overload
def as_loader(
    callback: collections.Callable[[Client], None], /, *, standard_impl: typing.Literal[True] = True
) -> collections.Callable[[Client], None]:
    ...


@typing.overload
def as_loader(
    *, standard_impl: typing.Literal[True] = True
) -> collections.Callable[[collections.Callable[[Client], None]], collections.Callable[[Client], None]]:
    ...


@typing.overload
def as_loader(
    callback: collections.Callable[[tanjun.Client], None], /, *, standard_impl: typing.Literal[False]
) -> collections.Callable[[tanjun.Client], None]:
    ...


@typing.overload
def as_loader(
    *, standard_impl: typing.Literal[False]
) -> collections.Callable[[collections.Callable[[tanjun.Client], None]], collections.Callable[[tanjun.Client], None]]:
    ...


def as_loader(
    callback: typing.Union[
        collections.Callable[[tanjun.Client], None], collections.Callable[[Client], None], None
    ] = None,
    /,
    *,
    standard_impl: bool = True,
) -> typing.Union[
    collections.Callable[[tanjun.Client], None],
    collections.Callable[[Client], None],
    collections.Callable[[collections.Callable[[Client], None]], collections.Callable[[Client], None]],
    collections.Callable[[collections.Callable[[tanjun.Client], None]], collections.Callable[[tanjun.Client], None]],
]:
    """Mark a callback as being used to load Tanjun components from a module.

    !!! note
        This is only necessary if you wish to use [tanjun.Client.load_modules][].

    Parameters
    ----------
    callback
        The callback used to load Tanjun components from a module.

        This should take one argument of type [tanjun.Client][] (or
        [tanjun.abc.Client][] if `standard_impl` is [False][]), return nothing
        and will be expected to initiate and add utilities such as components
        to the provided client.
    standard_impl
        Whether this loader should only allow instances of [tanjun.Client][]
        as opposed to [tanjun.abc.Client][].

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.Client], None]]
        The decorated load callback.
    """
    if callback:
        return _LoaderDescriptor(callback, standard_impl)

    def decorator(callback: collections.Callable[[tanjun.Client], None]) -> collections.Callable[[tanjun.Client], None]:
        return _LoaderDescriptor(callback, standard_impl)

    return decorator


@typing.overload
def as_unloader(
    callback: collections.Callable[[Client], None], /, *, standard_impl: typing.Literal[True] = True
) -> collections.Callable[[Client], None]:
    ...


@typing.overload
def as_unloader(
    *, standard_impl: typing.Literal[True] = True
) -> collections.Callable[[collections.Callable[[Client], None]], collections.Callable[[Client], None]]:
    ...


@typing.overload
def as_unloader(
    callback: collections.Callable[[tanjun.Client], None], /, *, standard_impl: typing.Literal[False]
) -> collections.Callable[[tanjun.Client], None]:
    ...


@typing.overload
def as_unloader(
    *, standard_impl: typing.Literal[False]
) -> collections.Callable[[collections.Callable[[tanjun.Client], None]], collections.Callable[[tanjun.Client], None]]:
    ...


def as_unloader(
    callback: typing.Union[
        collections.Callable[[Client], None], collections.Callable[[tanjun.Client], None], None
    ] = None,
    /,
    *,
    standard_impl: bool = True,
) -> typing.Union[
    collections.Callable[[Client], None],
    collections.Callable[[tanjun.Client], None],
    collections.Callable[[collections.Callable[[Client], None]], collections.Callable[[Client], None]],
    collections.Callable[[collections.Callable[[tanjun.Client], None]], collections.Callable[[tanjun.Client], None]],
]:
    """Mark a callback as being used to unload a module's utilities from a client.

    !!! note
        This is the inverse of [tanjun.as_loader][] and is only necessary if
        you wish to use the [tanjun.Client.unload_modules][] or
        [tanjun.Client.reload_modules][].

    Parameters
    ----------
    callback
        The callback used to unload Tanjun components from a module.

        This should take one argument of type [tanjun.Client][] (or
        [tanjun.abc.Client][] if `standard_impl` is [False][]), return nothing
        and will be expected to remove utilities such as components from the
        provided client.
    standard_impl
        Whether this unloader should only allow instances of [tanjun.Client][]
        as opposed to [tanjun.abc.Client][].

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.Client], None]]
        The decorated unload callback.
    """
    if callback:
        return _UnloaderDescriptor(callback, standard_impl)

    def decorator(callback: collections.Callable[[tanjun.Client], None]) -> collections.Callable[[tanjun.Client], None]:
        return _UnloaderDescriptor(callback, standard_impl)

    return decorator


ClientCallbackNames = tanjun.ClientCallbackNames
"""Alias of [tanjun.abc.ClientCallbackNames][]."""


class InteractionAcceptsEnum(enum.IntFlag):
    """The possible configurations for which interaction this client should execute."""

    NONE = 0
    """Set the client to execute no interactions."""

    AUTOCOMPLETE = enum.auto()
    """Execute autocomplete interactions."""

    COMMANDS = enum.auto()
    """Execute command interactions.

    This includes slash command and context menu calls.
    """

    ALL = AUTOCOMPLETE | COMMANDS
    """Execute all the interaction types Tanjun supports."""


class MessageAcceptsEnum(str, enum.Enum):
    """The possible configurations for which events [tanjun.Client][] should execute commands based on."""

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
        type[hikari.events.MessageCreateEvent] | None
            The type object of the MessageCreateEvent class this mode will
            register a listener for.

            This will be [None][] if this mode disables listening to
            message create events.
        """
        return _ACCEPTS_EVENT_TYPE_MAPPING[self]


_ACCEPTS_EVENT_TYPE_MAPPING: dict[MessageAcceptsEnum, typing.Optional[type[hikari.MessageCreateEvent]]] = {
    MessageAcceptsEnum.ALL: hikari.MessageCreateEvent,
    MessageAcceptsEnum.DM_ONLY: hikari.DMMessageCreateEvent,
    MessageAcceptsEnum.GUILD_ONLY: hikari.GuildMessageCreateEvent,
    MessageAcceptsEnum.NONE: None,
}
assert _ACCEPTS_EVENT_TYPE_MAPPING.keys() == set(MessageAcceptsEnum)


def _check_human(ctx: tanjun.Context, /) -> bool:
    return ctx.is_human


async def _wrap_client_callback(
    client: Client,
    callback: tanjun.MetaEventSig,
    args: tuple[str, ...],
) -> None:
    try:
        await client.injector.call_with_async_di(callback, *args)

    except Exception as exc:
        _LOGGER.error("Client callback raised exception", exc_info=exc)


async def on_parser_error(ctx: tanjun.Context, error: errors.ParserError) -> None:
    """Handle message parser errors.

    This is the default message parser error hook included by [tanjun.Client][].
    """
    await ctx.respond(error.message)


def _cmp_command(built: typing.Optional[hikari.api.CommandBuilder], cmd: hikari.PartialCommand) -> bool:
    if not built or built.id is not hikari.UNDEFINED and built.id != cmd.id or built.type != cmd.type:
        return False

    dm_enabled = True if built.is_dm_enabled is hikari.UNDEFINED else built.is_dm_enabled
    default_perms = built.default_member_permissions or hikari.Permissions.NONE
    builder_default_perms = cmd.default_member_permissions or hikari.Permissions.NONE

    if dm_enabled is not cmd.is_dm_enabled or default_perms != builder_default_perms:
        return False

    # name doesn't need to be checked as `builder` will be `None` if that didn't match.
    if built.name_localizations != cmd.name_localizations:
        return False

    if isinstance(cmd, hikari.SlashCommand):
        assert isinstance(built, hikari.api.SlashCommandBuilder)
        if built.description != cmd.description or built.description_localizations != cmd.description_localizations:
            return False

        opts = cmd.options or ()

        return len(built.options) == len(opts) and all(itertools.starmap(operator.eq, zip(built.options, opts)))

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


class Client(tanjun.Client):
    """Tanjun's standard [tanjun.abc.Client][] implementation.

    This implementation supports dependency injection for checks, command
    callbacks, prefix getters and event listeners. For more information on how
    this works see [alluka][].

    When manually managing the lifetime of the client the linked rest app or
    bot must always be started before the Tanjun client.

    !!! note
        By default this client includes a parser error handling hook which will
        by overwritten if you call [tanjun.Client.set_hooks][].
    """

    __slots__ = (
        "_auto_defer_after",
        "_cache",
        "_cached_application_id",
        "_checks",
        "_client_callbacks",
        "_components",
        "_default_app_cmd_permissions",
        "_defaults_to_ephemeral",
        "_dms_enabled_for_app_cmds",
        "_events",
        "_grab_mention_prefix",
        "_hooks",
        "_interaction_accepts",
        "_menu_hooks",
        "_menu_not_found",
        "_slash_hooks",
        "_slash_not_found",
        "_injector",
        "_is_closing",
        "_listeners",
        "_loop",
        "_make_autocomplete_context",
        "_make_menu_context",
        "_make_message_context",
        "_make_slash_context",
        "_message_accepts",
        "_message_hooks",
        "_metadata",
        "_modules",
        "_path_modules",
        "_prefix_getter",
        "_prefixes",
        "_rest",
        "_server",
        "_shards",
        "_tasks",
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

        !!! note
            For a quicker way to initiate this client around a standard bot aware
            client, see [tanjun.Client.from_gateway_bot][] and [tanjun.Client.from_rest_bot][].

        Parameters
        ----------
        rest
            The Hikari REST client this will use.
        cache
            The Hikari cache client this will use if applicable.
        events
            The Hikari event manager client this will use if applicable.

            This is necessary for message command dispatch and will also
            be necessary for interaction command dispatch if `server` isn't
            provided.
        server
            The Hikari interaction server client this will use if applicable.

            This is used for interaction command dispatch if interaction
            events aren't being received from the event manager.
        shards
            The Hikari shard aware client this will use if applicable.
        voice
            The Hikari voice component this will use if applicable.
        event_managed
            Whether or not this client is managed by the event manager.

            An event managed client will be automatically started and closed based
            on Hikari's lifetime events.

            This can only be passed as [True][] if `events` is also provided.
        injector
            The alluka client this should use for dependency injection.

            If not provided then the client will initialise its own DI client.
        mention_prefix
            Whether or not mention prefixes should be automatically set when this
            client is first started.

            It should be noted that this only applies to message commands.
        declare_global_commands
            Whether or not to automatically set global slash commands when this
            client is first started.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally.

            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).
        set_global_commands
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids
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
        message_ids
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.

        Raises
        ------
        ValueError
            Raises for the following reasons:

            * If `event_managed` is `True` when `event_manager` is `None`.
            * If `command_ids` is passed when multiple guild ids are provided for
              `declare_global_commands`.
            * If `command_ids` is passed when `declare_global_commands` is `False`.
        """
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

        self._auto_defer_after: typing.Optional[float] = 2.0
        self._cache = cache
        self._cached_application_id: typing.Optional[hikari.Snowflake] = None
        self._checks: list[tanjun.CheckSig] = []
        self._client_callbacks: dict[str, list[tanjun.MetaEventSig]] = {}
        self._components: dict[str, tanjun.Component] = {}
        self._default_app_cmd_permissions = hikari.Permissions.NONE
        self._defaults_to_ephemeral = False
        self._dms_enabled_for_app_cmds = True
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self._hooks: typing.Optional[tanjun.AnyHooks] = hooks.AnyHooks().set_on_parser_error(on_parser_error)
        self._interaction_accepts = InteractionAcceptsEnum.ALL
        self._menu_hooks: typing.Optional[tanjun.MenuHooks] = None
        self._menu_not_found: typing.Optional[str] = "Command not found"
        self._slash_hooks: typing.Optional[tanjun.SlashHooks] = None
        self._slash_not_found: typing.Optional[str] = self._menu_not_found
        # TODO: test coverage
        self._injector = injector or alluka.Client()
        self._is_closing = False
        self._listeners: dict[
            type[hikari.Event],
            dict[tanjun.ListenerCallbackSig, alluka.abc.AsyncSelfInjecting[tanjun.ListenerCallbackSig]],
        ] = {}
        self._loop: typing.Optional[asyncio.AbstractEventLoop] = None
        self._make_autocomplete_context: _AutocompleteContextMakerProto = context.AutocompleteContext
        self._make_menu_context: _MenuContextMakerProto = context.MenuContext
        self._make_message_context: _MessageContextMakerProto = context.MessageContext
        self._make_slash_context: _SlashContextMakerProto = context.SlashContext
        self._message_accepts = MessageAcceptsEnum.ALL if events else MessageAcceptsEnum.NONE
        self._message_hooks: typing.Optional[tanjun.MessageHooks] = None
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._modules: dict[str, types.ModuleType] = {}
        self._path_modules: dict[pathlib.Path, types.ModuleType] = {}
        self._prefix_getter: typing.Optional[PrefixGetterSig] = None
        self._prefixes: list[str] = []
        self._rest = rest
        self._server = server
        self._shards = shards
        self._tasks: list[asyncio.Task[typing.Any]] = []
        self._voice = voice

        if event_managed:
            if not events:
                raise ValueError("Client cannot be event managed without an event manager")

            events.subscribe(hikari.StartingEvent, self._on_starting)
            events.subscribe(hikari.StoppingEvent, self._on_stopping)

        (
            self.set_type_dependency(tanjun.Client, self)
            .set_type_dependency(Client, self)
            .set_type_dependency(type(self), self)
            .set_type_dependency(hikari.api.RESTClient, rest)
            .set_type_dependency(type(rest), rest)
            ._maybe_set_type_dep(hikari.api.Cache, cache)
            ._maybe_set_type_dep(type(cache), cache)
            ._maybe_set_type_dep(hikari.api.EventManager, events)
            ._maybe_set_type_dep(type(events), events)
            ._maybe_set_type_dep(hikari.api.InteractionServer, server)
            ._maybe_set_type_dep(type(server), server)
            ._maybe_set_type_dep(hikari.ShardAware, shards)
            ._maybe_set_type_dep(type(shards), shards)
            ._maybe_set_type_dep(hikari.api.VoiceComponent, voice)
            ._maybe_set_type_dep(type(voice), voice)
        )

        dependencies.set_standard_dependencies(self)
        self._schedule_startup_registers(
            set_global_commands,
            declare_global_commands,
            command_ids,
            message_ids=message_ids,
            user_ids=user_ids,
            _stack_level=_stack_level,
        )

    def _maybe_set_type_dep(self, type_: type[_T], value: typing.Optional[_T]) -> Self:
        if value is not None:
            self.set_type_dependency(type_, value)

        return self

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

    def _remove_task(self, task: asyncio.Task[typing.Any], /) -> None:
        self._tasks.remove(task)

    def _add_task(self, task: asyncio.Task[typing.Any], /) -> None:
        if not task.done():
            self._tasks.append(task)
            task.add_done_callback(self._remove_task)

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
        """Build a [tanjun.Client][] from a [hikari.traits.GatewayBotAware][] instance.

        !!! note
            This defaults the client to human only mode and sets type
            dependency injectors for the hikari traits present in `bot`
            (including [hikari.traits.GatewayBotAware][]).

        Parameters
        ----------
        bot
            The bot client to build from.

            This will be used to infer the relevant Hikari clients to use.
        event_managed
            Whether or not this client is managed by the event manager.

            An event managed client will be automatically started and closed
            based on Hikari's lifetime events.
        injector
            The alluka client this should use for dependency injection.

            If not provided then the client will initialise its own DI client.
        mention_prefix
            Whether or not mention prefixes should be automatically set when this
            client is first started.

            It should be noted that this only applies to message commands.
        declare_global_commands
            Whether or not to automatically set global slash commands when this
            client is first started.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally.

            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).
        set_global_commands
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids
            If provided, a mapping of top level command names to IDs of the commands to update.

            This field is complementary to `declare_global_commands` and, while it
            isn't necessarily required, this will in some situations help avoid
            permissions which were previously set for a command from being lost
            after a rename.

            This currently isn't supported when multiple guild IDs are passed for
            `declare_global_commands`.
        message_ids
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        """
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
        bot_managed: bool = False,
        declare_global_commands: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialGuild], hikari.SnowflakeishOr[hikari.PartialGuild], bool
        ] = False,
        injector: typing.Optional[alluka.abc.Client] = None,
        set_global_commands: typing.Union[hikari.SnowflakeishOr[hikari.PartialGuild], bool] = False,
        command_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        message_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
        user_ids: typing.Optional[collections.Mapping[str, hikari.SnowflakeishOr[hikari.PartialCommand]]] = None,
    ) -> Client:
        """Build a [tanjun.Client][] from a [hikari.traits.RESTBotAware][] instance.

        !!! note
            This sets type dependency injectors for the hikari traits present in
            `bot` (including [hikari.traits.RESTBotAware][]).

        Parameters
        ----------
        bot
            The bot client to build from.
        declare_global_commands
            Whether or not to automatically set global slash commands when this
            client is first started.

            If one or more guild objects/IDs are passed here then the registered
            global commands will be set on the specified guild(s) at startup rather
            than globally.

            The endpoint this uses has a strict ratelimit which, as of writing,
            only allows for 2 requests per minute (with that ratelimit either
            being per-guild if targeting a specific guild otherwise globally).
        bot_managed
            Whether the client should be managed by the REST bot.

            A REST bot managed client will be automatically started and closed
            based on the REST bot's startup and shutdown callbacks.
        injector
            The alluka client this should use for dependency injection.

            If not provided then the client will initialise its own DI client.
        set_global_commands
            Deprecated as of v2.1.1a1 alias of `declare_global_commands`.
        command_ids
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
        message_ids
            If provided, a mapping of message context menu command names to the
            IDs of existing commands to update.
        user_ids
            If provided, a mapping of user context menu command names to the IDs
            of existing commands to update.
        """
        self = cls(
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

        if bot_managed:
            bot.add_startup_callback(self._on_starting)
            bot.add_shutdown_callback(self._on_stopping)

        return self

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
    def default_app_cmd_permissions(self) -> hikari.Permissions:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._default_app_cmd_permissions

    @property
    def defaults_to_ephemeral(self) -> bool:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._defaults_to_ephemeral

    @property
    def dms_enabled_for_app_cmds(self) -> bool:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._dms_enabled_for_app_cmds

    @property
    def interaction_accepts(self) -> InteractionAcceptsEnum:
        """The types of interactions this client is executing."""
        return self._interaction_accepts

    @property
    def message_accepts(self) -> MessageAcceptsEnum:
        """Type of message create events this command client accepts for execution."""
        return self._message_accepts

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
    def checks(self) -> collections.Collection[tanjun.CheckSig]:
        """Collection of the level [tanjun.abc.Context][] checks registered to this client.

        !!! note
            These may be taking advantage of the standard dependency injection.
        """
        return self._checks.copy()

    @property
    def components(self) -> collections.Collection[tanjun.Component]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._components.copy().values()

    @property
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._events

    @property
    def listeners(
        self,
    ) -> collections.Mapping[type[hikari.Event], collections.Collection[tanjun.ListenerCallbackSig]]:
        return _internal.CastedView(
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
    def hooks(self) -> typing.Optional[tanjun.AnyHooks]:
        """Top level [tanjun.abc.AnyHooks][] set for this client.

        These are called during both message, menu and slash command execution.
        """
        return self._hooks

    @property
    def menu_hooks(self) -> typing.Optional[tanjun.MenuHooks]:
        """Top level [tanjun.abc.MenuHooks][] set for this client.

        These are only called during menu command execution.
        """
        return self._menu_hooks

    @property
    def message_hooks(self) -> typing.Optional[tanjun.MessageHooks]:
        """Top level [tanjun.abc.MessageHooks][] set for this client.

        These are only called during message command execution.
        """
        return self._message_hooks

    @property
    def slash_hooks(self) -> typing.Optional[tanjun.SlashHooks]:
        """Top level [tanjun.abc.SlashHooks][] set for this client.

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

        For more information on this callback's signature see
        [tanjun.clients.PrefixGetterSig][].
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

    async def _on_starting(self, _: typing.Union[hikari.StartingEvent, hikari.RESTBotAware], /) -> None:
        await self.open()

    async def _on_stopping(self, _: typing.Union[hikari.StoppingEvent, hikari.RESTBotAware], /) -> None:
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
        """Alias of [tanjun.Client.declare_global_commands][].

        !!! warning "deprecated"
            Since v2.1.1a1; use [tanjun.Client.declare_global_commands][] instead.
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
        command: tanjun.BaseSlashCommand,
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
        command: tanjun.MenuCommand[typing.Any, typing.Any],
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
        command: tanjun.AppCommand[typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        ...

    async def declare_application_command(
        self,
        command: tanjun.AppCommand[typing.Any],
        /,
        command_id: typing.Optional[hikari.Snowflakeish] = None,
        *,
        application: typing.Optional[hikari.SnowflakeishOr[hikari.PartialApplication]] = None,
        guild: hikari.UndefinedOr[hikari.SnowflakeishOr[hikari.PartialGuild]] = hikari.UNDEFINED,
    ) -> hikari.PartialCommand:
        # <<inherited docstring from tanjun.abc.Client>>.
        application = application or self._cached_application_id or await self.fetch_rest_application_id()
        builder = command.build()
        if builder.default_member_permissions is hikari.UNDEFINED:
            builder.set_default_member_permissions(self.default_app_cmd_permissions)

        if builder.is_dm_enabled is hikari.UNDEFINED:
            builder.set_is_dm_enabled(self.dms_enabled_for_app_cmds)

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
            response = await builder.create(self._rest, application, guild=guild)

        if not guild:
            command.set_tracked_command(response)  # TODO: is this fine?

        return response

    async def declare_application_commands(
        self,
        commands: collections.Iterable[typing.Union[tanjun.AppCommand[typing.Any], hikari.api.CommandBuilder]],
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
        localiser = self._injector.get_type_dependency(dependencies.AbstractLocaliser, default=None)
        command_ids = command_ids or {}
        message_ids = message_ids or {}
        user_ids = user_ids or {}
        names_to_commands: dict[tuple[hikari.CommandType, str], tanjun.AppCommand[typing.Any]] = {}
        conflicts: set[tuple[hikari.CommandType, str]] = set()
        builders: dict[tuple[hikari.CommandType, str], hikari.api.CommandBuilder] = {}
        message_count = 0
        slash_count = 0
        user_count = 0

        for command in commands:
            key = (command.type, command.name)
            if key in builders:
                conflicts.add(key)

            if isinstance(command, tanjun.AppCommand):
                names_to_commands[key] = command
                builder = command.build()

            else:
                builder = command

            command_id = None
            if builder.type is hikari.CommandType.USER:
                user_count += 1
                command_id = user_ids.get(command.name)

            elif builder.type is hikari.CommandType.MESSAGE:
                message_count += 1
                command_id = message_ids.get(command.name)

            elif builder.type is hikari.CommandType.SLASH:
                slash_count += 1

            if command_id := (command_id or command_ids.get(command.name)):
                builder.set_id(hikari.Snowflake(command_id))

            if builder.default_member_permissions is hikari.UNDEFINED:
                builder.set_default_member_permissions(self.default_app_cmd_permissions)

            if builder.is_dm_enabled is hikari.UNDEFINED:
                builder.set_is_dm_enabled(self.dms_enabled_for_app_cmds)

            if localiser:
                localisation.localise_command(builder, localiser)

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

        application = application or self._cached_application_id or await self.fetch_rest_application_id()
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
            if not guild and (command := names_to_commands.get((response.type, response.name))):
                command.set_tracked_command(response)  # TODO: is this fine?

        _LOGGER.info("Successfully declared %s (top-level) %s commands", len(responses), target_type)
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "Declared %s command ids; %s",
                target_type,
                ", ".join(f"{response.type}-{response.name}: {response.id}" for response in responses),
            )

        return responses

    def set_auto_defer_after(self, time: typing.Optional[float], /) -> Self:
        """Set when this client should automatically defer execution of commands.

        !!! warning
            If `time` is set to [None][] then automatic deferrals will be disabled.
            This may lead to unexpected behaviour.

        Parameters
        ----------
        time
            The time in seconds to defer interaction command responses after.
        """
        self._auto_defer_after = float(time) if time is not None else None
        return self

    def set_default_app_command_permissions(self, permissions: typing.Union[int, hikari.Permissions], /) -> Self:
        """Set the default member permissions needed for this client's commands.

        !!! warning
            This may be overridden by guild staff and does not apply to admins.

        Parameters
        ----------
        permissions
            The default member permissions needed for this client's application commands.

            This may be overridden by [tanjun.abc.AppCommand.default_member_permissions][]
            and [tanjun.abc.Component.default_app_cmd_permissions][]; if this is
            left as [None][] then this config will be inherited from the parent
            client.

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._default_app_cmd_permissions = hikari.Permissions(permissions)
        return self

    def set_dms_enabled_for_app_cmds(self, state: bool, /) -> Self:
        """Set whether this clients's commands should be enabled in DMs.

        Parameters
        ----------
        state
            Whether to enable this client's commands in DMs.

            This may be overridden by [tanjun.abc.AppCommand.is_dm_enabled][]
            and [tanjun.abc.Component.dms_enabled_for_app_cmds][]; if this is
            left as [None][] then this config will be inherited from the parent
            client.

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._dms_enabled_for_app_cmds = state
        return self

    def set_ephemeral_default(self, state: bool, /) -> Self:
        """Set whether slash contexts spawned by this client should default to ephemeral responses.

        This defaults to [False][] if not explicitly set.

        Parameters
        ----------
        state
            Whether slash command contexts executed in this client should
            should default to ephemeral.

            This will be overridden by any response calls which specify flags.

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_hikari_trait_injectors(self, bot: hikari.RESTAware, /) -> Self:
        """Set type based dependency injection based on the hikari traits found in `bot`.

        This is a short hand for calling [tanjun.Client.add_type_dependency][] for all
        the hikari trait types `bot` is valid for with bot.

        Parameters
        ----------
        bot
            The hikari client to set dependency injectors for.
        """
        for _, member in inspect.getmembers(hikari_traits):
            if inspect.isclass(member) and isinstance(bot, member):
                self.set_type_dependency(member, bot)

        return self

    def set_interaction_not_found(self, message: typing.Optional[str], /) -> Self:
        """Set the response message for when an interaction command is not found.

        !!! warning
            Setting this to [None][] may lead to unexpected behaviour (especially
            when the client is still set to auto-defer interactions) and should
            only be done if you know what you're doing.

        Parameters
        ----------
        message
            The message to respond with when an interaction command isn't found.
        """
        return self.set_menu_not_found(message).set_slash_not_found(message)

    def set_menu_not_found(self, message: typing.Optional[str], /) -> Self:
        """Set the response message for when a menu command is not found.

        !!! warning
            Setting this to [None][] may lead to unexpected behaviour (especially
            when the client is still set to auto-defer interactions) and should
            only be done if you know what you're doing.

        Parameters
        ----------
        message
            The message to respond with when a menu command isn't found.
        """
        self._menu_not_found = message
        return self

    def set_slash_not_found(self, message: typing.Optional[str], /) -> Self:
        """Set the response message for when a slash command is not found.

        !!! warning
            Setting this to [None][] may lead to unexpected behaviour (especially
            when the client is still set to auto-defer interactions) and should
            only be done if you know what you're doing.

        Parameters
        ----------
        message
            The message to respond with when a slash command isn't found.
        """
        self._slash_not_found = message
        return self

    def set_interaction_accepts(self, accepts: InteractionAcceptsEnum, /) -> Self:
        """Set the kind of interactions this client should execute.

        Parameters
        ----------
        accepts
            Bitfield of the interaction types this client should execute.

        Raises
        ------
        RuntimeError
            If called while the client is running.
        """
        if self._loop:
            raise RuntimeError("Cannot change this config while the client is running")

        self._interaction_accepts = accepts
        return self

    def set_message_accepts(self, accepts: MessageAcceptsEnum, /) -> Self:
        """Set the kind of messages commands should be executed based on.

        Parameters
        ----------
        accepts
            The type of messages commands should be executed based on.

        Raises
        ------
        RuntimeError
            If called while the client is running.
        ValueError
            If `accepts` is set to anything other than [tanjun.clients.MessageAcceptsEnum.NONE][]
            when the client doesn't have a linked event manager.
        """
        if accepts.get_event_type() and not self._events:
            raise ValueError("Cannot set accepts level on a client with no event manager")

        if self._loop:
            raise RuntimeError("Cannot change this config while the client is running")

        self._message_accepts = accepts
        return self

    def set_autocomplete_ctx_maker(
        self, maker: _AutocompleteContextMakerProto = context.AutocompleteContext, /
    ) -> Self:
        """Set the autocomplete context maker to use when creating contexts.

        !!! warning
            The caller must return an instance of [tanjun.context.AutocompleteContext][]
            rather than just any implementation of the AutocompleteContext abc
            due to this client relying on implementation detail of
            [tanjun.context.AutocompleteContext][].

        Parameters
        ----------
        maker
            The autocomplete context maker to use.

            This is a callback which should match the signature of
            [tanjun.context.AutocompleteContext.__init__][] and return
            an instance of [tanjun.context.AutocompleteContext][].

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._make_autocomplete_context = maker
        return self

    def set_menu_ctx_maker(self, maker: _MenuContextMakerProto = context.MenuContext, /) -> Self:
        """Set the autocomplete context maker to use when creating contexts.

        !!! warning
            The caller must return an instance of [tanjun.context.MenuContext][]
            rather than just any implementation of the MenuContext abc
            due to this client relying on implementation detail of
            [tanjun.context.MenuContext][].

        Parameters
        ----------
        maker
            The autocomplete context maker to use.

            This is a callback which should match the signature of
            [tanjun.context.MenuContext.__init__][] and return
            an instance of [tanjun.context.MenuContext][].

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._make_menu_context = maker
        return self

    def set_message_ctx_maker(self, maker: _MessageContextMakerProto = context.MessageContext, /) -> Self:
        """Set the message context maker to use when creating context for a message.

        !!! warning
            The caller must return an instance of [tanjun.context.MessageContext][]
            rather than just any implementation of the MessageContext abc due to
            this client relying on implementation detail of
            [tanjun.context.MessageContext][].

        Parameters
        ----------
        maker
            The message context maker to use.

            This is a callback which should match the signature of
            [tanjun.context.MessageContext.__init__][] and return an instance
            of [tanjun.context.MessageContext][].

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._make_message_context = maker
        return self

    def set_metadata(self, key: typing.Any, value: typing.Any, /) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._metadata[key] = value
        return self

    def set_slash_ctx_maker(self, maker: _SlashContextMakerProto = context.SlashContext, /) -> Self:
        """Set the slash context maker to use when creating context for a slash command.

        !!! warning
            The caller must return an instance of [tanjun.context.SlashContext][]
            rather than just any implementation of the SlashContext abc due to
            this client relying on implementation detail of
            [tanjun.context.SlashContext][].

        Parameters
        ----------
        maker
            The slash context maker to use.

            This is a callback which should match the signature of
            [tanjun.context.SlashContext.__init__][] and return an instance
            of [tanjun.context.SlashContext][].

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._make_slash_context = maker
        return self

    def set_human_only(self, value: bool = True) -> Self:
        """Set whether or not message commands execution should be limited to "human" users.

        !!! note
            This doesn't apply to interaction commands as these can only be
            triggered by a "human" (normal user account).

        Parameters
        ----------
        value
            Whether or not message commands execution should be limited to "human" users.

            Passing [True][] here will prevent message commands from being executed
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

    def add_check(self, check: tanjun.CheckSig, /) -> Self:
        """Add a generic check to this client.

        This will be applied to both message and slash command execution.

        Parameters
        ----------
        check
            The check to add. This may be either synchronous or asynchronous
            and must take one positional argument of type [tanjun.abc.Context][]
            with dependency injection being supported for its keyword arguments.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        if check not in self._checks:
            self._checks.append(check)

        return self

    def remove_check(self, check: tanjun.CheckSig, /) -> Self:
        """Remove a check from the client.

        Parameters
        ----------
        check
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
            and must take one positional argument of type [tanjun.abc.Context][]
            with dependency injection being supported for its keyword arguments.

        Returns
        -------
        tanjun.abc.CheckSig
            The added check.
        """
        self.add_check(check)
        return check

    async def check(self, ctx: tanjun.Context, /) -> bool:
        return await _internal.gather_checks(ctx, self._checks)

    def add_component(self, component: tanjun.Component, /) -> Self:
        """Add a component to this client.

        Parameters
        ----------
        component
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

        if self._loop:
            self._add_task(self._loop.create_task(component.open()))
            self._add_task(
                self._loop.create_task(self.dispatch_client_callback(ClientCallbackNames.COMPONENT_ADDED, component))
            )

        return self

    def get_component_by_name(self, name: str, /) -> typing.Optional[tanjun.Component]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._components.get(name)

    def remove_component(self, component: tanjun.Component, /) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        stored_component = self._components.get(component.name)
        if not stored_component or stored_component != component:
            raise ValueError(f"The component {component!r} is not registered.")

        del self._components[component.name]

        if self._loop:
            self._add_task(self._loop.create_task(component.close(unbind=True)))
            self._add_task(
                self._loop.create_task(
                    self.dispatch_client_callback(ClientCallbackNames.COMPONENT_REMOVED, stored_component)
                )
            )

        else:
            stored_component.unbind_client(self)

        return self

    def remove_component_by_name(self, name: str, /) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self.remove_component(self._components[name])

    def add_client_callback(
        self, name: typing.Union[str, tanjun.ClientCallbackNames], callback: tanjun.MetaEventSig, /
    ) -> Self:
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
        self, name: typing.Union[str, tanjun.ClientCallbackNames], /, *args: typing.Any
    ) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        if callbacks := self._client_callbacks.get(name):
            calls = (_wrap_client_callback(self, callback, args) for callback in callbacks)
            await asyncio.gather(*calls)

    def get_client_callbacks(
        self, name: typing.Union[str, tanjun.ClientCallbackNames], /
    ) -> collections.Collection[tanjun.MetaEventSig]:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        if result := self._client_callbacks.get(name):
            return result.copy()

        return ()

    def remove_client_callback(
        self, name: typing.Union[str, tanjun.ClientCallbackNames], callback: tanjun.MetaEventSig, /
    ) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        name = name.casefold()
        self._client_callbacks[name].remove(callback)
        if not self._client_callbacks[name]:
            del self._client_callbacks[name]

        return self

    def with_client_callback(
        self, name: typing.Union[str, tanjun.ClientCallbackNames], /
    ) -> collections.Callable[[_MetaEventSigT], _MetaEventSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: _MetaEventSigT, /) -> _MetaEventSigT:
            self.add_client_callback(name, callback)
            return callback

        return decorator

    def add_listener(self, event_type: type[hikari.Event], callback: tanjun.ListenerCallbackSig, /) -> Self:
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

    def remove_listener(self, event_type: type[hikari.Event], callback: tanjun.ListenerCallbackSig, /) -> Self:
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
        self, *event_types: type[hikari.Event]
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT]:
        # <<inherited docstring from tanjun.abc.Client>>.
        def decorator(callback: _ListenerCallbackSigT, /) -> _ListenerCallbackSigT:
            for event_type in event_types or _internal.infer_listener_types(callback):
                self.add_listener(event_type, callback)

            return callback

        return decorator

    def add_prefix(self, prefixes: typing.Union[collections.Iterable[str], str], /) -> Self:
        """Add a prefix used to filter message command calls.

        This will be matched against the first character(s) in a message's
        content to determine whether the message command search stage of
        execution should be initiated.

        Parameters
        ----------
        prefixes
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

    def remove_prefix(self, prefix: str, /) -> Self:
        """Remove a message content prefix from the client.

        Parameters
        ----------
        prefix
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

    def set_prefix_getter(self, getter: typing.Optional[PrefixGetterSig], /) -> Self:
        """Set the callback used to retrieve message prefixes set for the relevant guild.

        Parameters
        ----------
        getter
            The callback which'll be used to retrieve prefixes for the guild a
            message context is from. If [None][] is passed here then the callback
            will be unset.

            This should be an async callback which one argument of type
            [tanjun.abc.MessageContext][] and returns an iterable of string prefixes.
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
            [tanjun.abc.MessageContext][] and returns an iterable of string prefixes.
            Dependency injection is supported for this callback's keyword arguments.

        Returns
        -------
        PrefixGetterSig
            The registered callback.
        """
        self.set_prefix_getter(getter)
        return getter

    def iter_commands(self) -> collections.Iterator[tanjun.ExecutableCommand[tanjun.Context]]:
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
        type: typing.Literal[hikari.CommandType.MESSAGE],  # noqa: A002 - Shadowing a builtin name.
    ) -> collections.Iterator[tanjun.MenuCommand[typing.Any, typing.Literal[hikari.CommandType.MESSAGE]]]:
        ...

    @typing.overload
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Literal[hikari.CommandType.USER],  # noqa: A002 - Shadowing a builtin name.
    ) -> collections.Iterator[tanjun.MenuCommand[typing.Any, typing.Literal[hikari.CommandType.USER]]]:
        ...

    @typing.overload
    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[hikari.CommandType] = None,  # noqa: A002 - Shadowing a builtin name.
    ) -> collections.Iterator[tanjun.MenuCommand[typing.Any, typing.Any]]:
        ...

    def iter_menu_commands(
        self,
        *,
        global_only: bool = False,
        type: typing.Optional[hikari.CommandType] = None,  # noqa: A002 - Shadowing a builtin name.
    ) -> collections.Iterator[tanjun.MenuCommand[typing.Any, typing.Any]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        if global_only:
            return filter(lambda c: c.is_global, self.iter_menu_commands(global_only=False, type=type))

        if type:
            if type not in _MENU_TYPES:
                raise ValueError("Command type filter must be USER or MESSAGE")

            return filter(lambda c: c.type == type, self.iter_menu_commands(global_only=global_only, type=None))

        return itertools.chain.from_iterable(component.menu_commands for component in self.components)

    def iter_message_commands(self) -> collections.Iterator[tanjun.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(component.message_commands for component in self.components)

    def iter_slash_commands(self, *, global_only: bool = False) -> collections.Iterator[tanjun.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        if global_only:
            return filter(lambda c: c.is_global, self.iter_slash_commands(global_only=False))

        return itertools.chain.from_iterable(component.slash_commands for component in self.components)

    def check_message_name(self, name: str, /) -> collections.Iterator[tuple[str, tanjun.MessageCommand[typing.Any]]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(
            component.check_message_name(name) for component in self._components.values()
        )

    def check_slash_name(self, name: str, /) -> collections.Iterator[tanjun.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return itertools.chain.from_iterable(
            component.check_slash_name(name) for component in self._components.values()
        )

    async def _check_prefix(self, ctx: tanjun.MessageContext, /) -> typing.Optional[str]:
        if self._prefix_getter:
            for prefix in await ctx.call_with_async_di(self._prefix_getter, ctx):
                if ctx.content.startswith(prefix):
                    return prefix

        for prefix in self._prefixes:
            if ctx.content.startswith(prefix):
                return prefix

        return None

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
            if event_type := self._message_accepts.get_event_type():
                _try_unsubscribe(self._events, event_type, self.on_message_create_event)

            _try_unsubscribe(self._events, hikari.InteractionCreateEvent, self.on_interaction_create_event)

            for event_type_, listeners in self._listeners.items():
                for listener in listeners.values():
                    _try_unsubscribe(self._events, event_type_, listener.__call__)

        if deregister_listeners and self._server:
            _try_deregister_listener(self._server, hikari.CommandInteraction, self.on_command_interaction_request)
            _try_deregister_listener(
                self._server, hikari.AutocompleteInteraction, self.on_autocomplete_interaction_request
            )

        await asyncio.gather(*(component.close() for component in self._components.copy().values()))

        self._loop = None
        await self.dispatch_client_callback(ClientCallbackNames.CLOSED)
        self._is_closing = False

    async def open(self, *, register_listeners: bool = True) -> None:
        """Start the client.

        If `mention_prefix` was passed to [tanjun.Client.__init__][] or
        [tanjun.Client.from_gateway_bot][] then this function may make a fetch request
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

        if register_listeners and self._server:
            if self._interaction_accepts & InteractionAcceptsEnum.COMMANDS:
                self._server.set_listener(hikari.CommandInteraction, self.on_command_interaction_request)

            if self._interaction_accepts & InteractionAcceptsEnum.AUTOCOMPLETE:
                self._server.set_listener(hikari.AutocompleteInteraction, self.on_autocomplete_interaction_request)

            if self._events and (event_type := self._message_accepts.get_event_type()):
                self._events.subscribe(event_type, self.on_message_create_event)

        elif register_listeners and self._events:
            if event_type := self._message_accepts.get_event_type():
                self._events.subscribe(event_type, self.on_message_create_event)

            if self._interaction_accepts:
                self._events.subscribe(hikari.InteractionCreateEvent, self.on_interaction_create_event)

            for event_type_, listeners in self._listeners.items():
                for listener in listeners.values():
                    self._events.subscribe(event_type_, listener.__call__)

        self._add_task(self._loop.create_task(self.dispatch_client_callback(ClientCallbackNames.STARTED)))

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

    def set_hooks(self, hooks: typing.Optional[tanjun.AnyHooks], /) -> Self:
        """Set the general command execution hooks for this client.

        The callbacks within this hook will be added to every slash and message
        command execution started by this client.

        Parameters
        ----------
        hooks
            The general command execution hooks to set for this client.

            Passing [None][] will remove all hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._hooks = hooks
        return self

    def set_menu_hooks(self, hooks: typing.Optional[tanjun.MenuHooks], /) -> Self:
        """Set the menu command execution hooks for this client.

        The callbacks within this hook will be added to every menu command
        execution started by this client.

        Parameters
        ----------
        hooks
            The menu context specific command execution hooks to set for this
            client.

            Passing [None][] will remove the hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._menu_hooks = hooks
        return self

    def set_slash_hooks(self, hooks: typing.Optional[tanjun.SlashHooks], /) -> Self:
        """Set the slash command execution hooks for this client.

        The callbacks within this hook will be added to every slash command
        execution started by this client.

        Parameters
        ----------
        hooks
            The slash context specific command execution hooks to set for this
            client.

            Passing [None][] will remove the hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._slash_hooks = hooks
        return self

    def set_message_hooks(self, hooks: typing.Optional[tanjun.MessageHooks], /) -> Self:
        """Set the message command execution hooks for this client.

        The callbacks within this hook will be added to every message command
        execution started by this client.

        Parameters
        ----------
        hooks
            The message context specific command execution hooks to set for this
            client.

            Passing [None][] will remove all hooks.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        self._message_hooks = hooks
        return self

    def load_directory(
        self,
        directory: typing.Union[str, pathlib.Path],
        /,
        *,
        namespace: typing.Optional[str] = None,
    ) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        paths = _scan_directory(pathlib.Path(directory), namespace)
        for path in paths:
            try:
                self.load_modules(path)
            except errors.ModuleStateConflict:
                pass
            except errors.ModuleMissingLoaders:
                _LOGGER.info("Ignoring load_directory target `%s` with no loaders", path)

        return self

    async def load_directory_async(
        self, directory: typing.Union[str, pathlib.Path], /, *, namespace: typing.Optional[str] = None
    ) -> None:
        # <<inherited docstring from tanjun.abc.Client>>.
        paths = await asyncio.get_running_loop().run_in_executor(
            None, _scan_directory, pathlib.Path(directory), namespace
        )
        for path in paths:
            try:
                await self.load_modules_async(path)
            except errors.ModuleStateConflict:
                pass
            except errors.ModuleMissingLoaders:
                _LOGGER.info("Ignoring load_directory target `%s` with no loaders", path)

    def _call_loaders(
        self, module_path: typing.Union[str, pathlib.Path], loaders: list[tanjun.ClientLoader], /
    ) -> None:
        found = False
        for loader in loaders:
            if loader.load(self):
                found = True

        if not found:
            raise errors.ModuleMissingLoaders(f"Didn't find any loaders in {module_path}", module_path)

    def _call_unloaders(
        self, module_path: typing.Union[str, pathlib.Path], loaders: list[tanjun.ClientLoader], /
    ) -> None:
        found = False
        for loader in loaders:
            if loader.unload(self):
                found = True

        if not found:
            raise errors.ModuleMissingUnloaders(f"Didn't find any unloaders in {module_path}", module_path)

    def _load_module(
        self, module_path: typing.Union[str, pathlib.Path]
    ) -> collections.Generator[collections.Callable[[], types.ModuleType], types.ModuleType, None]:
        if isinstance(module_path, str):
            if module_path in self._modules:
                raise errors.ModuleStateConflict(f"module {module_path} already loaded", module_path)

            _LOGGER.info("Loading from %s", module_path)
            module = yield lambda: importlib.import_module(module_path)

            with _WrapLoadError(errors.FailedModuleLoad, module_path):
                self._call_loaders(module_path, _get_loaders(module, module_path))

            self._modules[module_path] = module

        else:
            if module_path in self._path_modules:
                raise errors.ModuleStateConflict(f"Module at {module_path} already loaded", module_path)

            _LOGGER.info("Loading from %s", module_path)
            module = yield lambda: _get_path_module(module_path)

            with _WrapLoadError(errors.FailedModuleLoad, module_path):
                self._call_loaders(module_path, _get_loaders(module, module_path))

            self._path_modules[module_path] = module

    def load_modules(self, *modules: typing.Union[str, pathlib.Path]) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        for module_path in modules:
            if isinstance(module_path, pathlib.Path):
                module_path = _normalize_path(module_path)

            generator = self._load_module(module_path)
            load_module = next(generator)
            with _WrapLoadError(errors.FailedModuleImport, module_path):
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
            with _WrapLoadError(errors.FailedModuleImport, module_path):
                module = await loop.run_in_executor(None, load_module)

            try:
                generator.send(module)
            except StopIteration:
                pass
            else:
                raise RuntimeError("Generator didn't finish")

    def unload_modules(self, *modules: typing.Union[str, pathlib.Path]) -> Self:
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
            with _WrapLoadError(errors.FailedModuleUnload, module_path):
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
            raise errors.ModuleMissingUnloaders(f"Didn't find any unloaders in old {module_path}", module_path)

        module = yield load_module

        loaders = _get_loaders(module, module_path)

        # We assert that the new module has loaders early to avoid unnecessarily
        # unloading then rolling back when we know it's going to fail to load.
        if not any(loader.has_load for loader in loaders):
            raise errors.ModuleMissingLoaders(f"Didn't find any loaders in new {module_path}", module_path)

        with _WrapLoadError(errors.FailedModuleUnload, module_path):
            # This will never raise MissingLoaders as we assert this earlier
            self._call_unloaders(module_path, old_loaders)

        try:
            # This will never raise MissingLoaders as we assert this earlier
            self._call_loaders(module_path, loaders)
        except Exception as exc:
            self._call_loaders(module_path, old_loaders)
            raise errors.FailedModuleLoad(module_path) from exc
        else:
            modules_dict[module_path] = module

    def reload_modules(self, *modules: typing.Union[str, pathlib.Path]) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        for module_path in modules:
            if isinstance(module_path, pathlib.Path):
                module_path = _normalize_path(module_path)

            generator = self._reload_module(module_path)
            load_module = next(generator)
            with _WrapLoadError(errors.FailedModuleLoad, module_path):
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
            with _WrapLoadError(errors.FailedModuleLoad, module_path):
                module = await loop.run_in_executor(None, load_module)

            try:
                generator.send(module)

            except StopIteration:
                pass

            else:
                raise RuntimeError("Generator didn't finish")

    def set_type_dependency(self, type_: type[_T], value: _T, /) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.set_type_dependency(type_, value)
        return self

    def get_type_dependency(self, type_: type[_T], /) -> typing.Union[_T, alluka.abc.Undefined]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._injector.get_type_dependency(type_)

    def remove_type_dependency(self, type_: type[typing.Any], /) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.remove_type_dependency(type_)
        return self

    def set_callback_override(
        self, callback: alluka.abc.CallbackSig[_T], override: alluka.abc.CallbackSig[_T], /
    ) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.set_callback_override(callback, override)
        return self

    def get_callback_override(
        self, callback: alluka.abc.CallbackSig[_T], /
    ) -> typing.Optional[alluka.abc.CallbackSig[_T]]:
        # <<inherited docstring from tanjun.abc.Client>>.
        return self._injector.get_callback_override(callback)

    def remove_callback_override(self, callback: alluka.abc.CallbackSig[_T], /) -> Self:
        # <<inherited docstring from tanjun.abc.Client>>.
        self._injector.remove_callback_override(callback)
        return self

    async def on_message_create_event(self, event: hikari.MessageCreateEvent, /) -> None:
        """Execute a message command based on a gateway event.

        Parameters
        ----------
        event
            The event to handle.
        """
        if event.message.content is None:
            return

        ctx = self._make_message_context(
            client=self, register_task=self._add_task, content=event.message.content, message=event.message
        )
        if (prefix := await self._check_prefix(ctx)) is None:
            return

        ctx.set_content(ctx.content.lstrip()[len(prefix) :].lstrip()).set_triggering_prefix(prefix)
        hooks: typing.Optional[set[tanjun.MessageHooks]] = None
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
            await exc.send(ctx)
            return

        await self.dispatch_client_callback(ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx)

    def _get_slash_hooks(self) -> typing.Optional[set[tanjun.SlashHooks]]:
        hooks: typing.Optional[set[tanjun.SlashHooks]] = None
        if self._hooks and self._slash_hooks:
            hooks = {self._hooks, self._slash_hooks}

        elif self._hooks:
            hooks = {self._hooks}

        elif self._slash_hooks:
            hooks = {self._slash_hooks}

        return hooks

    def _get_menu_hooks(self) -> typing.Optional[set[tanjun.MenuHooks]]:
        hooks: typing.Optional[set[tanjun.MenuHooks]] = None
        if self._hooks and self._menu_hooks:
            hooks = {self._hooks, self._menu_hooks}

        elif self._hooks:
            hooks = {self._hooks}

        elif self._menu_hooks:
            hooks = {self._menu_hooks}

        return hooks

    async def _on_menu_not_found(self, ctx: tanjun.MenuContext) -> None:
        await self.dispatch_client_callback(ClientCallbackNames.MENU_COMMAND_NOT_FOUND, ctx)
        if self._menu_not_found and not ctx.has_responded:
            await ctx.create_initial_response(self._menu_not_found)

    async def _on_slash_not_found(self, ctx: tanjun.SlashContext) -> None:
        await self.dispatch_client_callback(ClientCallbackNames.SLASH_COMMAND_NOT_FOUND, ctx)
        if self._slash_not_found and not ctx.has_responded:
            await ctx.create_initial_response(self._slash_not_found)

    async def on_gateway_autocomplete_create(self, interaction: hikari.AutocompleteInteraction, /) -> None:
        """Execute command autocomplete based on a received gateway interaction create.

        Parameters
        ----------
        interaction
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
        interaction
            The interaction to execute a command based on.
        """
        if interaction.command_type is hikari.CommandType.SLASH:
            ctx: typing.Union[context.MenuContext, context.SlashContext] = self._make_slash_context(
                client=self,
                interaction=interaction,
                register_task=self._add_task,
                on_not_found=self._on_slash_not_found,
                default_to_ephemeral=self._defaults_to_ephemeral,
            )
            hooks: typing.Union[set[tanjun.MenuHooks], set[tanjun.SlashHooks], None] = self._get_slash_hooks()

        elif interaction.command_type in _MENU_TYPES:
            ctx = self._make_menu_context(
                client=self,
                interaction=interaction,
                register_task=self._add_task,
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
                    assert isinstance(ctx, tanjun.SlashContext)
                    coro = await component.execute_slash(ctx, hooks=typing.cast("set[tanjun.SlashHooks]", hooks))

                else:
                    assert isinstance(ctx, tanjun.MenuContext)
                    coro = await component.execute_menu(ctx, hooks=typing.cast("set[tanjun.MenuHooks]", hooks))

                if coro:
                    try:
                        return await coro
                    finally:
                        ctx.cancel_defer()

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            try:
                await exc.send(ctx)
            finally:
                ctx.cancel_defer()
            return

        try:
            await ctx.mark_not_found()
        finally:
            ctx.cancel_defer()

    async def on_interaction_create_event(self, event: hikari.InteractionCreateEvent, /) -> None:
        """Handle a gateway interaction create event.

        This will execute both application command and autocomplete interactions.

        Parameters
        ----------
        event
            The event to execute commands based on.
        """
        if event.interaction.type is hikari.InteractionType.APPLICATION_COMMAND:
            if self._interaction_accepts & InteractionAcceptsEnum.COMMANDS:
                assert isinstance(event.interaction, hikari.CommandInteraction)
                return await self.on_gateway_command_create(event.interaction)

        elif event.interaction.type is hikari.InteractionType.AUTOCOMPLETE:
            if self._interaction_accepts & InteractionAcceptsEnum.AUTOCOMPLETE:
                assert isinstance(event.interaction, hikari.AutocompleteInteraction)
                return await self.on_gateway_autocomplete_create(event.interaction)

    async def on_autocomplete_interaction_request(
        self, interaction: hikari.AutocompleteInteraction, /
    ) -> hikari.api.InteractionAutocompleteBuilder:
        """Execute a command autocomplete based on received REST requests.

        Parameters
        ----------
        interaction
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
                task = loop.create_task(coro)
                task.add_done_callback(lambda _: future.cancel())
                self._add_task(task)
                return await future

        raise RuntimeError(f"Autocomplete not found for {interaction!r}")

    async def on_command_interaction_request(
        self, interaction: hikari.CommandInteraction, /
    ) -> typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]:
        """Execute an app command based on received REST requests.

        Parameters
        ----------
        interaction
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
                register_task=self._add_task,
                on_not_found=self._on_slash_not_found,
                default_to_ephemeral=self._defaults_to_ephemeral,
                future=future,
            )
            hooks: typing.Union[set[tanjun.MenuHooks], set[tanjun.SlashHooks], None] = self._get_slash_hooks()

        elif interaction.command_type in _MENU_TYPES:
            ctx = self._make_menu_context(
                client=self,
                interaction=interaction,
                register_task=self._add_task,
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
                    assert isinstance(ctx, tanjun.SlashContext)
                    coro = await component.execute_slash(ctx, hooks=typing.cast("set[tanjun.SlashHooks]", hooks))

                else:
                    assert isinstance(ctx, tanjun.MenuContext)
                    coro = await component.execute_menu(ctx, hooks=typing.cast("set[tanjun.MenuHooks]", hooks))

                if coro:
                    task = loop.create_task(coro)
                    task.add_done_callback(lambda _: future.cancel() and ctx.cancel_defer())
                    self._add_task(task)
                    return await future

        except errors.HaltExecution:
            pass

        except errors.CommandError as exc:
            # Under very specific timing there may be another future which could set a result while we await
            # ctx.respond therefore we create a task to avoid any erroneous behaviour from this trying to create
            # another response before it's returned the initial response.
            task = loop.create_task(exc.send(ctx), name=f"{interaction.id} command error responder")
            task.add_done_callback(lambda _: future.cancel() and ctx.cancel_defer())
            self._add_task(task)
            return await future

        task = loop.create_task(ctx.mark_not_found(), name=f"{interaction.id} not found")
        task.add_done_callback(lambda _: future.cancel() and ctx.cancel_defer())
        self._add_task(task)
        return await future


def _scan_directory(path: pathlib.Path, namespace: typing.Optional[str]) -> list[typing.Union[pathlib.Path, str]]:
    if namespace:
        return [namespace + "." + path.name.removesuffix(".py") for path in path.glob("*.py") if path.is_file()]

    return [path for path in path.glob("*.py") if path.is_file()]


def _normalize_path(path: pathlib.Path) -> pathlib.Path:
    try:  # TODO: test behaviour around this
        path = path.expanduser()
    except RuntimeError:
        pass  # A home directory couldn't be resolved, so we'll just use the path as-is.

    return path.resolve()


def _get_loaders(
    module: types.ModuleType, module_path: typing.Union[str, pathlib.Path], /
) -> list[tanjun.ClientLoader]:
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

    return [value for value in iterator if isinstance(value, tanjun.ClientLoader)]


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
    __slots__ = ("_args", "_error", "_kwargs")

    def __init__(
        self,
        error: collections.Callable[_P, Exception],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None:
        self._args = args
        self._error = error
        self._kwargs = kwargs

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type: typing.Optional[type[BaseException]],
        exc: typing.Optional[BaseException],
        exc_tb: typing.Optional[types.TracebackType],
    ) -> None:
        if (
            exc
            and isinstance(exc, Exception)
            and not isinstance(exc, (errors.ModuleMissingLoaders, errors.ModuleMissingUnloaders))
        ):
            raise self._error(*self._args, **self._kwargs) from exc  # noqa: R102


def _try_deregister_listener(
    interaction_server: hikari.api.InteractionServer,
    interaction_type: typing.Any,
    callback: collections.Callable[
        ..., collections.Coroutine[typing.Any, typing.Any, hikari.api.InteractionResponseBuilder]
    ],
) -> None:
    if interaction_server.get_listener(interaction_type) is callback:
        interaction_server.set_listener(interaction_type, None)


def _try_unsubscribe(
    event_manager: hikari.api.EventManager,
    event_type: type[hikari.Event],
    callback: collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]],
) -> None:
    try:
        event_manager.unsubscribe(event_type, callback)
    except (ValueError, LookupError):
        # TODO: add logging here
        pass
