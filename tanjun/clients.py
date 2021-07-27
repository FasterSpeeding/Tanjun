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

__all__: typing.Sequence[str] = [
    "as_loader",
    "Client",
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

from hikari import errors as hikari_errors
from hikari import traits as hikari_traits
from hikari.events import interaction_events
from hikari.events import lifetime_events
from hikari.events import message_events
from hikari.interactions import commands
from yuyo import backoff

from . import context
from . import errors as tanjun_errors
from . import injector as injector_
from . import traits as tanjun_traits
from . import utilities

if typing.TYPE_CHECKING:
    import pathlib
    import types

    from hikari import guilds
    from hikari import snowflakes
    from hikari import users
    from hikari.api import cache as cache_api
    from hikari.api import event_manager as event_manager_api
    from hikari.api import interaction_server as interaction_server_api
    from hikari.api import rest as rest_api
    from hikari.api import special_endpoints as special_endpoints_api
    from hikari.interactions import commands as command_interactions

    _ClientT = typing.TypeVar("_ClientT", bound="Client")

LoadableSig = typing.Callable[["Client"], None]
"""Type hint of the callback used to load resources into a Tanjun client.

This should take one positional argument of type `Client` and return nothing.
This will be expected to initiate and resources like components to the client
through the use of it's protocol methods.
"""

PrefixGetterSig = typing.Callable[..., typing.Awaitable[typing.Iterable[str]]]
"""Type hint of a callable used to get the prefix(es) for a specific guild.

This should be an asynchronous callable which returns an iterable of strings.

!!! note
    While dependency injection is supported for this, the first positional
    argument will always be a `tanjun.traits.MessageContext`.
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
        should take one argument of type `tanjun.traits.Client`, return nothing
        and will be expected to initiate and add utilities such as components
        to the provided client using it's abstract methods.

    Returns
    -------
    LoadableSig
        The decorated load callback.
    """
    return _LoadableDescriptor(callback)


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

    def get_event_type(self) -> typing.Optional[typing.Type[message_events.MessageCreateEvent]]:
        """Get the base event type this mode listens to.

        Returns
        -------
        typing.Optional[typing.Type[hikari.message_events.MessageCreateEvent]]
            The type object of the MessageCreateEvent class this mode will
            register a listener for.

            This will be `None` if this mode disables listening to
            message create events/
        """
        return _ACCEPTS_EVENT_TYPE_MAPPING[self]


_ACCEPTS_EVENT_TYPE_MAPPING: typing.Dict[
    MessageAcceptsEnum, typing.Optional[typing.Type[message_events.MessageCreateEvent]]
] = {
    MessageAcceptsEnum.ALL: message_events.MessageCreateEvent,
    MessageAcceptsEnum.DM_ONLY: message_events.DMMessageCreateEvent,
    MessageAcceptsEnum.GUILD_ONLY: message_events.GuildMessageCreateEvent,
    MessageAcceptsEnum.NONE: None,
}


def _check_human(ctx: tanjun_traits.Context, /) -> bool:
    return ctx.is_human


async def _wrap_client_callback(
    callback: tanjun_traits.MetaEventSig,
    args: typing.Tuple[str, ...],
    kwargs: typing.Dict[str, typing.Any],
    suppress_exceptions: bool,
) -> None:
    try:
        result = callback(*args, **kwargs)
        if isinstance(result, collections.Awaitable):
            await result

    except Exception as exc:
        if suppress_exceptions:
            _LOGGER.error("Client callback raised exception", exc_info=exc)

        else:
            raise


class _InjectablePrefixGetter(injector_.BaseInjectableValue[typing.Iterable[str]]):
    __slots__: typing.Sequence[str] = ()

    callback: PrefixGetterSig

    def __init__(
        self, callback: PrefixGetterSig, *, injector: typing.Optional[injector_.InjectorClient] = None
    ) -> None:
        super().__init__(callback, injector=injector)
        self.is_async = True

    async def __call__(self, ctx: tanjun_traits.Context, /) -> typing.Iterable[str]:
        return await self.call(ctx, ctx=ctx)


class Client(injector_.InjectorClient, tanjun_traits.Client):
    __slots__: typing.Sequence[str] = (
        "_accepts",
        "_auto_defer_after",
        "_cache",
        "_checks",
        "_client_callbacks",
        "_components",
        "_events",
        "_grab_mention_prefix",
        "_hooks",
        "_interaction_not_found",
        "_interaction_hooks",
        "_is_alive",
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
        rest: rest_api.RESTClient,
        cache: typing.Optional[cache_api.Cache] = None,
        events: typing.Optional[event_manager_api.EventManager] = None,
        server: typing.Optional[interaction_server_api.InteractionServer] = None,
        shard: typing.Optional[hikari_traits.ShardAware] = None,
        *,
        event_managed: typing.Optional[bool] = None,
        mention_prefix: bool = False,
        set_global_commands: bool = False,
    ) -> None:
        # TODO: logging or something to indicate this is running statelessly rather than statefully.
        # TODO: warn if server and dispatch both None but don't error

        # TODO: separate slash and gateway checks?
        self._accepts = MessageAcceptsEnum.ALL if events else MessageAcceptsEnum.NONE
        self._auto_defer_after: typing.Optional[float] = 2.6
        self._cache = cache
        self._checks: typing.Set[injector_.InjectableCheck] = set()
        self._client_callbacks: typing.Dict[str, typing.Set[tanjun_traits.MetaEventSig]] = {}
        self._components: typing.Set[tanjun_traits.Component] = set()
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self._hooks: typing.Optional[tanjun_traits.AnyHooks] = None
        self._interaction_not_found: typing.Optional[str] = "Command not found"
        self._interaction_hooks: typing.Optional[tanjun_traits.InteractionHooks] = None
        self._is_alive = False
        self._message_hooks: typing.Optional[tanjun_traits.MessageHooks] = None
        self._metadata: typing.Dict[typing.Any, typing.Any] = {}
        self._prefix_getter: typing.Optional[_InjectablePrefixGetter] = None
        self._prefixes: typing.Set[str] = set()
        self._rest = rest
        self._server = server
        self._shards = shard

        if event_managed or event_managed is None and self._events:
            if not self._events:
                raise ValueError("Client cannot be event managed without an event manager")

            self._events.subscribe(lifetime_events.StartingEvent, self._on_starting_event)
            self._events.subscribe(lifetime_events.StoppingEvent, self._on_stopping_event)

        if set_global_commands:
            self.add_client_callback(tanjun_traits.ClientCallbackNames.STARTING, self._set_global_commands_next_start)

        # InjectorClient.__init__
        super().__init__(self)

    @classmethod
    def from_gateway_bot(
        cls,
        bot: hikari_traits.GatewayBotAware,
        /,
        *,
        event_managed: bool = True,
        mention_prefix: bool = False,
        set_global_commands: bool = False,
    ) -> Client:
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
    def from_rest_bot(cls, bot: hikari_traits.RESTBotAware, /, set_global_commands: bool = False) -> Client:
        return cls(
            rest=bot.rest, server=bot.interaction_server, set_global_commands=set_global_commands
        ).set_hikari_trait_injectors(bot)

    async def __aenter__(self) -> Client:
        await self.open()
        return self

    async def __aexit__(
        self,
        exception_type: typing.Optional[typing.Type[BaseException]],
        exception: typing.Optional[BaseException],
        exception_traceback: typing.Optional[types.TracebackType],
    ) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"CommandClient <{type(self).__name__!r}, {len(self._components)} components, {self._prefixes}>"

    @property
    def message_accepts(self) -> MessageAcceptsEnum:
        """The type of message create events this command client accepts for execution."""
        return self._accepts

    @property
    def is_human_only(self) -> bool:
        """Whether this client is only executing for non-bot/webhook users messages."""
        return _check_human in self._checks  # type: ignore[comparison-overlap]

    @property
    def cache(self) -> typing.Optional[cache_api.Cache]:
        return self._cache

    @property
    def checks(self) -> typing.AbstractSet[tanjun_traits.CheckSig]:
        return {check.callback for check in self._checks}

    @property
    def components(self) -> typing.AbstractSet[tanjun_traits.Component]:
        return self._components.copy()

    @property
    def events(self) -> typing.Optional[event_manager_api.EventManager]:
        return self._events

    @property
    def hooks(self) -> typing.Optional[tanjun_traits.AnyHooks]:
        return self._hooks

    @property
    def interaction_hooks(self) -> typing.Optional[tanjun_traits.InteractionHooks]:
        return self._interaction_hooks

    @property
    def is_alive(self) -> bool:
        """Whether this client is alive."""
        return self._is_alive

    @property
    def message_hooks(self) -> typing.Optional[tanjun_traits.MessageHooks]:
        return self._message_hooks

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def prefix_getter(self) -> typing.Optional[PrefixGetterSig]:
        return self._prefix_getter.callback if self._prefix_getter else None

    @property
    def prefixes(self) -> typing.AbstractSet[str]:
        return self._prefixes.copy()

    @property
    def rest(self) -> rest_api.RESTClient:
        return self._rest

    @property
    def server(self) -> typing.Optional[interaction_server_api.InteractionServer]:
        return self._server

    @property
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        return self._shards

    async def _set_global_commands_next_start(self) -> None:
        await self.set_global_commands()
        self.remove_client_callback(tanjun_traits.ClientCallbackNames.STARTING, self._set_global_commands_next_start)

    async def _on_starting_event(self, _: lifetime_events.StartingEvent, /) -> None:
        await self.open()

    async def _on_stopping_event(self, _: lifetime_events.StoppingEvent, /) -> None:
        await self.close()

    def set_auto_defer_after(self: _ClientT, time: typing.Optional[float], /) -> _ClientT:
        """Set when this client should automatically defer execution of commands.

        Parameters
        ----------
        time : typing.Optional[float]
            The time in seconds to defer interaction command responses after.

            !!! note
                If this is set to ``None``, automatic deferals will be disabled.
                This may lead to unexpected behaviour.
        """
        self._auto_defer_after = float(time) if time is not None else None
        return self

    def set_hikari_trait_injectors(self: _ClientT, bot: hikari_traits.RESTAware, /) -> _ClientT:
        for _, member in inspect.getmembers(hikari_traits):
            if inspect.isclass(member) and isinstance(bot, member):
                self.add_type_dependency(member, lambda: bot)

        return self

    def set_interaction_not_found(self: _ClientT, message: typing.Optional[str], /) -> _ClientT:
        """Set the message to be shown when an interaction command is not found."""
        self._interaction_not_found = message
        return self

    def set_message_accepts(self: _ClientT, accepts: MessageAcceptsEnum, /) -> _ClientT:
        if accepts.get_event_type() and not self._events:
            raise ValueError("Cannot set accepts level on a client with no event manager")

        self._accepts = accepts
        return self

    def set_human_only(self: _ClientT, value: bool = True) -> _ClientT:
        if value:
            self.add_check(injector_.InjectableCheck(_check_human, injector=self))

        else:
            try:
                self.remove_check(_check_human)
            except ValueError:
                pass

        return self

    async def set_global_commands(
        self, application: typing.Optional[snowflakes.SnowflakeishOr[guilds.PartialApplication]] = None, /
    ) -> typing.Sequence[command_interactions.Command]:
        if not application:
            try:
                application = await self._rest.fetch_application()

            except hikari_errors.UnauthorizedError:
                application = (await self._rest.fetch_authorization()).application

        found_top_names: typing.Set[str] = set()
        conflicts: typing.Set[str] = set()
        builders: typing.List[special_endpoints_api.CommandBuilder] = []

        for command in itertools.chain.from_iterable(component.interaction_commands for component in self._components):
            if not command.is_global:
                continue

            if command.name in found_top_names:
                conflicts.add(command.name)

            found_top_names.add(command.name)
            builders.append(command.build())

        if conflicts:
            raise RuntimeError(
                "Couldn't set global commands due to conflicts. The following command names have more than one command "
                "registered for them " + ", ".join(conflicts)
            )

        commands = await self._rest.set_application_commands(application, builders)
        names_to_commands = {command.name: command for command in commands}
        for command in itertools.chain.from_iterable(component.interaction_commands for component in self._components):
            if command.is_global:
                command.set_tracked_command(names_to_commands[command.name])

        return commands

    def add_check(self: _ClientT, check: tanjun_traits.CheckSig, /) -> _ClientT:
        self._checks.add(injector_.InjectableCheck(check, injector=self))
        return self

    def remove_check(self, check: tanjun_traits.CheckSig, /) -> None:
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: tanjun_traits.CheckSigT, /) -> tanjun_traits.CheckSigT:
        self.add_check(check)
        return check

    async def check(self, ctx: tanjun_traits.Context, /) -> bool:
        return await utilities.gather_checks(ctx, self._checks)

    def add_component(self: _ClientT, component: tanjun_traits.Component, /) -> _ClientT:
        if isinstance(component, injector_.Injectable):
            component.set_injector(self)

        component.bind_client(self)
        self._components.add(component)
        return self

    def remove_component(self, component: tanjun_traits.Component, /) -> None:
        self._components.remove(component)
        component.unbind_client(self)

    def add_client_callback(self: _ClientT, event_name: str, callback: tanjun_traits.MetaEventSig, /) -> _ClientT:
        event_name = event_name.lower()
        try:
            self._client_callbacks[event_name].add(callback)
        except KeyError:
            self._client_callbacks[event_name] = {callback}

        return self

    async def dispatch_client_callback(
        self, event_name: str, /, *args: typing.Any, suppress_exceptions: bool = True, **kwargs: typing.Any
    ) -> None:
        event_name = event_name.lower()
        if callbacks := self._client_callbacks.get(event_name):
            await asyncio.gather(
                *(_wrap_client_callback(callback, args, kwargs, suppress_exceptions) for callback in callbacks)
            )

    def get_client_callbacks(self, event_name: str, /) -> typing.Collection[tanjun_traits.MetaEventSig]:
        event_name = event_name.lower()
        return self._client_callbacks.get(event_name) or ()

    def remove_client_callback(self, event_name: str, callback: tanjun_traits.MetaEventSig, /) -> None:
        event_name = event_name.lower()
        self._client_callbacks[event_name].remove(callback)
        if not self._client_callbacks[event_name]:
            del self._client_callbacks[event_name]

    def with_client_callback(
        self, event_name: str, /
    ) -> typing.Callable[[tanjun_traits.MetaEventSigT], tanjun_traits.MetaEventSigT]:
        def decorator(callback: tanjun_traits.MetaEventSigT, /) -> tanjun_traits.MetaEventSigT:
            self.add_client_callback(event_name, callback)
            return callback

        return decorator

    def add_prefix(self: _ClientT, prefixes: typing.Union[typing.Iterable[str], str], /) -> _ClientT:
        if isinstance(prefixes, str):
            self._prefixes.add(prefixes)

        else:
            self._prefixes.update(prefixes)

        return self

    def remove_prefix(self, prefix: str, /) -> None:
        self._prefixes.remove(prefix)

    def set_prefix_getter(self: _ClientT, getter: typing.Optional[PrefixGetterSig], /) -> _ClientT:
        self._prefix_getter = _InjectablePrefixGetter(getter, injector=self) if getter else None
        return self

    def with_prefix_getter(self, getter: PrefixGetterSigT, /) -> PrefixGetterSigT:
        self.set_prefix_getter(getter)
        return getter

    def check_message_context(
        self, ctx: tanjun_traits.MessageContext, /
    ) -> typing.AsyncIterator[typing.Tuple[str, tanjun_traits.MessageCommand]]:
        return utilities.async_chain(component.check_message_context(ctx) for component in self._components)

    def check_message_name(self, name: str, /) -> typing.Iterator[typing.Tuple[str, tanjun_traits.MessageCommand]]:
        return itertools.chain.from_iterable(component.check_message_name(name) for component in self._components)

    async def _check_prefix(self, ctx: tanjun_traits.MessageContext, /) -> typing.Optional[str]:
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
        event_manager: event_manager_api.EventManager,
        event_type: typing.Type[event_manager_api.EventT_co],
        callback: event_manager_api.CallbackT[event_manager_api.EventT_co],
    ) -> None:
        try:
            event_manager.unsubscribe(event_type, callback)
        except (ValueError, LookupError):
            # TODO: add logging here
            pass

    async def close(self, *, deregister_listener: bool = True) -> None:
        if not self._is_alive:
            raise RuntimeError("Client isn't active")

        await self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.CLOSING)
        if deregister_listener and self._events:
            if event_type := self._accepts.get_event_type():
                self._try_unsubscribe(self._events, event_type, self.on_message_create_event)

            self._try_unsubscribe(
                self._events, interaction_events.InteractionCreateEvent, self.on_interaction_create_event
            )

            if self._server:
                self._server.set_listener(commands.CommandInteraction, None)
        await self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.CLOSED)

    async def open(self, *, register_listener: bool = True) -> None:
        if self._is_alive:
            raise RuntimeError("Client is already alive")

        await self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.STARTING, suppress_exceptions=False)
        self._is_alive = True
        if self._grab_mention_prefix:
            user: typing.Optional[users.User] = None
            if self._cache:
                user = self._cache.get_me()

            if not user:
                retry = backoff.Backoff(max_retries=4, maximum=30)

                async for _ in retry:
                    try:
                        user = await self._rest.fetch_my_user()
                        break

                    except (hikari_errors.RateLimitedError, hikari_errors.RateLimitTooLongError) as exc:
                        if exc.retry_after > 30:
                            raise

                        retry.set_next_backoff(exc.retry_after)

                    except hikari_errors.InternalServerError:
                        continue

                else:
                    user = await self._rest.fetch_my_user()

            self._prefixes.add(f"<@{user.id}>")
            self._prefixes.add(f"<@!{user.id}>")
            self._grab_mention_prefix = False

        if register_listener and self._events:
            if event_type := self._accepts.get_event_type():
                self._events.subscribe(event_type, self.on_message_create_event)

            self._events.subscribe(interaction_events.InteractionCreateEvent, self.on_interaction_create_event)

        if self._server:
            self._server.set_listener(commands.CommandInteraction, self.on_interaction_create_request)

        asyncio.create_task(
            self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.STARTED, suppress_exceptions=False)
        )

    def set_hooks(self: _ClientT, hooks: typing.Optional[tanjun_traits.AnyHooks], /) -> _ClientT:
        self._hooks = hooks
        return self

    def set_interaction_hooks(self: _ClientT, hooks: typing.Optional[tanjun_traits.InteractionHooks], /) -> _ClientT:
        self._interaction_hooks = hooks
        return self

    def set_message_hooks(self: _ClientT, hooks: typing.Optional[tanjun_traits.MessageHooks], /) -> _ClientT:
        self._message_hooks = hooks
        return self

    def load_modules(self: _ClientT, *modules: typing.Union[str, pathlib.Path]) -> _ClientT:
        for module_path in modules:
            if isinstance(module_path, str):
                module = importlib.import_module(module_path)

            else:
                spec = importlib_util.spec_from_file_location(
                    module_path.name.rsplit(".", 1)[0], str(module_path.absolute())
                )

                # https://github.com/python/typeshed/issues/2793
                if spec and isinstance(spec.loader, importlib_abc.Loader):
                    module = importlib_util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                raise RuntimeError(f"Unknown or invalid module provided {module_path}")

            for _, member in inspect.getmembers(module):
                if isinstance(member, _LoadableDescriptor):
                    member(self)

        return self

    async def on_message_create_event(self, event: message_events.MessageCreateEvent, /) -> None:
        if event.message.content is None:
            return

        ctx = context.MessageContext(self, content=event.message.content, message=event.message)
        if (prefix := await self._check_prefix(ctx)) is None:
            return

        ctx.set_content(ctx.content.lstrip()[len(prefix) :].lstrip()).set_triggering_prefix(prefix)
        if not await self.check(ctx):
            return

        hooks: typing.Optional[typing.Set[tanjun_traits.MessageHooks]] = None
        if self._hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._hooks)

        if self._message_hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._message_hooks)

        try:
            for component in self._components:
                if await component.execute_message(ctx, hooks=hooks):
                    break

        except tanjun_errors.HaltExecutionSearch:
            pass

        await self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.MESSAGE_COMMAND_NOT_FOUND, ctx)

    async def on_interaction_create_event(self, event: interaction_events.InteractionCreateEvent, /) -> None:
        if not isinstance(event.interaction, commands.CommandInteraction):
            return

        ctx = context.InteractionContext(self, event.interaction)

        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        hooks: typing.Optional[typing.Set[tanjun_traits.InteractionHooks]] = None
        if self._hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._hooks)

        if self._interaction_hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._interaction_hooks)

        try:
            for component in self._components:
                if future := await component.execute_interaction(ctx, hooks=hooks):
                    await future

        except tanjun_errors.HaltExecutionSearch:
            pass

        await self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.INTERACTION_COMMAND_NOT_FOUND, ctx)
        if not ctx.has_responded and self._interaction_not_found:
            await ctx.respond(self._interaction_not_found)
        ctx.cancel_defer()

    async def on_interaction_create_request(self, interaction: commands.CommandInteraction, /) -> context.ResponseTypeT:
        ctx = context.InteractionContext(self, interaction)

        if self._auto_defer_after is not None:
            ctx.start_defer_timer(self._auto_defer_after)

        hooks: typing.Optional[typing.Set[tanjun_traits.InteractionHooks]] = None
        if self._hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._hooks)

        if self._interaction_hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._interaction_hooks)

        future = ctx.get_response_future()
        try:
            for component in self._components:
                if await component.execute_interaction(ctx, hooks=hooks):
                    return await future

        except tanjun_errors.HaltExecutionSearch:
            pass

        async def callback(_: asyncio.Future[None]) -> None:
            if not ctx.has_responded and self._interaction_not_found:
                await ctx.respond(self._interaction_not_found)
            ctx.cancel_defer()

        asyncio.create_task(
            self.dispatch_client_callback(tanjun_traits.ClientCallbackNames.INTERACTION_COMMAND_NOT_FOUND, ctx)
        ).add_done_callback(callback)
        return await future
