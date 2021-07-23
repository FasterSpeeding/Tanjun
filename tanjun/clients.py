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

__all__: typing.Sequence[str] = ["AcceptsEnum", "as_loader", "Client", "LoadableSig", "PrefixGetterSig"]

import asyncio
import enum
import functools
import importlib
import importlib.abc as importlib_abc
import importlib.util as importlib_util
import inspect
import itertools
import typing

from hikari import errors as hikari_errors
from hikari import traits as hikari_traits
from hikari.events import interaction_events
from hikari.events import lifetime_events
from hikari.events import message_events
from hikari.interactions import commands
from yuyo import backoff

from tanjun import context
from tanjun import injector
from tanjun import traits as tanjun_traits
from tanjun import utilities

if typing.TYPE_CHECKING:
    import pathlib
    import types

    from hikari import users
    from hikari.api import cache as cache_api
    from hikari.api import event_manager as event_manager_api
    from hikari.api import interaction_server as interaction_server_api
    from hikari.api import rest as rest_api

    _ClientT = typing.TypeVar("_ClientT", bound="Client")

LoadableSig = typing.Callable[["Client"], None]
"""Type hint of the function used to load resources into a Tanjun client.

This should take one positional argument of type `Client` and return nothing.
This will be expected to initiate and resources like components to the client
through the use of it's protocol methods.
"""

PrefixGetterSig = typing.Callable[[tanjun_traits.Context], typing.Awaitable[typing.Iterable[str]]]
"""Type hint of a callable used to get the prefix(es) for a specific guild.

This should be an asynchronous callable which takes one positional argument of
type `tanjun.traits.Context` and returns an iterable of strings.
"""


class _LoadableDescriptor:  # Slots mess with functools.update_wrapper
    def __init__(self, function: LoadableSig, /) -> None:
        self._function = function
        functools.update_wrapper(self, function)

    def __call__(self, client: Client, /) -> None:
        self._function(client)


def as_loader(function: LoadableSig, /) -> LoadableSig:
    """Mark a function as being used to load Tanjun utilities from a module.

    Parameters
    ----------
    function : LoadableSig
        The function used to load Tanjun utilities from the a module. This
        should take one argument of type `tanjun.traits.Client`, return nothing
        and will be expected to initiate and add utilities such as components
        to the provided client using it's protocol methods.

    Returns
    -------
    LoadableSig
        The decorated load function.
    """
    return _LoadableDescriptor(function)


class AcceptsEnum(str, enum.Enum):
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

            This will be `builtins.None` if this mode disables listening to
            message create events/
        """
        return _ACCEPTS_EVENT_TYPE_MAPPING[self]


_ACCEPTS_EVENT_TYPE_MAPPING: typing.Dict[
    AcceptsEnum, typing.Optional[typing.Type[message_events.MessageCreateEvent]]
] = {
    AcceptsEnum.ALL: message_events.MessageCreateEvent,
    AcceptsEnum.DM_ONLY: message_events.DMMessageCreateEvent,
    AcceptsEnum.GUILD_ONLY: message_events.GuildMessageCreateEvent,
    AcceptsEnum.NONE: None,
}


def _check_human(ctx: tanjun_traits.Context, /) -> bool:
    return ctx.is_human


class Client(injector.InjectorClient, tanjun_traits.Client):
    __slots__: typing.Sequence[str] = (
        "_accepts",
        "_cache",
        "_checks",
        "_components",
        "_events",
        "_grab_mention_prefix",
        "_hooks",
        "_interaction_hooks",
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
    ) -> None:
        # TODO: logging or something to indicate this is running statelessly rather than statefully.
        # TODO: warn if server and dispatch both None but don't error

        # TODO: separate slash and gateway checks?
        self._accepts = AcceptsEnum.ALL if events else AcceptsEnum.NONE
        self._checks: typing.Set[injector.InjectableCheck] = set()
        self._cache = cache
        self._components: typing.Set[tanjun_traits.Component] = set()
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self._hooks: typing.Optional[tanjun_traits.AnyHooks] = None
        self._interaction_hooks: typing.Optional[tanjun_traits.InteractionHooks] = None
        self._message_hooks: typing.Optional[tanjun_traits.MessageHooks] = None
        self._metadata: typing.Dict[typing.Any, typing.Any] = {}
        self._prefix_getter: typing.Optional[PrefixGetterSig] = None
        self._prefixes: typing.Set[str] = set()
        self._rest = rest
        self._server = server
        self._shards = shard
        self.set_human_only(True)

        if event_managed or event_managed is None and self._events:
            if not self._events:
                raise ValueError("Client cannot be event managed without an event manager")

            self._events.subscribe(lifetime_events.StartingEvent, self._on_starting_event)
            self._events.subscribe(lifetime_events.StoppingEvent, self._on_stopping_event)

        # InjectorClient.__init__
        super().__init__(self)

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

    @classmethod
    def from_gateway_bot(
        cls,
        bot: hikari_traits.GatewayBotAware,
        /,
        *,
        event_managed: bool = True,
        mention_prefix: bool = False,
    ) -> Client:
        client = cls(
            rest=bot.rest,
            cache=bot.cache,
            events=bot.event_manager,
            shard=bot,
            event_managed=event_managed,
            mention_prefix=mention_prefix,
        )
        return client.add_hikari_trait_injectors(bot)

    @classmethod
    def from_rest_bot(cls, bot: hikari_traits.RESTBotAware, /) -> Client:
        client = cls(rest=bot.rest, server=bot.interaction_server)
        return client.add_hikari_trait_injectors(bot)

    @property
    def accepts(self) -> AcceptsEnum:
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
    def message_hooks(self) -> typing.Optional[tanjun_traits.MessageHooks]:
        return self._message_hooks

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def prefix_getter(self) -> typing.Optional[PrefixGetterSig]:
        return self._prefix_getter

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

    async def _on_starting_event(self, _: lifetime_events.StartingEvent, /) -> None:
        await self.open()

    async def _on_stopping_event(self, _: lifetime_events.StoppingEvent, /) -> None:
        await self.close()

    def add_hikari_trait_injectors(self: _ClientT, bot: hikari_traits.RESTAware, /) -> _ClientT:
        for _, member in inspect.getmembers(hikari_traits):
            if inspect.isclass(member) and isinstance(bot, member):
                self.add_type_dependency(member, lambda: bot)

        return self

    def set_accepts(self: _ClientT, accepts: AcceptsEnum, /) -> _ClientT:
        if accepts.get_event_type() and not self._events:
            raise ValueError("Cannot set accepts level on a client with no event manager")

        self._accepts = accepts
        return self

    def set_human_only(self: _ClientT, value: bool = True) -> _ClientT:
        if value:
            self.add_check(injector.InjectableCheck(_check_human, injector=self))

        else:
            try:
                self.remove_check(_check_human)
            except ValueError:
                pass

        return self

    def add_check(self: _ClientT, check: tanjun_traits.CheckSig, /) -> _ClientT:
        self._checks.add(injector.InjectableCheck(check, injector=self))
        return self

    def remove_check(self, check: tanjun_traits.CheckSig, /) -> None:
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: tanjun_traits.CheckSigT, /) -> tanjun_traits.CheckSigT:
        self.add_check(check)
        return check

    async def check(self, ctx: tanjun_traits.Context, /) -> bool:
        return await utilities.gather_checks(self._checks, ctx)

    def add_component(self: _ClientT, component: tanjun_traits.Component, /) -> _ClientT:
        if isinstance(component, injector.Injectable):
            component.set_injector(self)

        component.bind_client(self)
        self._components.add(component)
        return self

    def remove_component(self, component: tanjun_traits.Component, /) -> None:
        self._components.remove(component)

    def add_listener(
        self: _ClientT,
        event: typing.Type[event_manager_api.EventT_inv],
        listener: event_manager_api.CallbackT[event_manager_api.EventT_inv],
        /,
    ) -> _ClientT:
        if self._events:
            self._events.subscribe(event, listener)

        return self

    def remove_listener(
        self,
        event: typing.Type[event_manager_api.EventT_inv],
        listener: event_manager_api.CallbackT[event_manager_api.EventT_inv],
        /,
    ) -> None:
        if self._events:
            self._events.unsubscribe(event, listener)

    # TODO: make event optional?
    def with_listener(
        self, event: typing.Type[event_manager_api.EventT_inv]
    ) -> typing.Callable[
        [event_manager_api.CallbackT[event_manager_api.EventT_inv]],
        event_manager_api.CallbackT[event_manager_api.EventT_inv],
    ]:
        def add_listener_(
            listener: event_manager_api.CallbackT[event_manager_api.EventT_inv],
        ) -> event_manager_api.CallbackT[event_manager_api.EventT_inv]:
            self.add_listener(event, listener)
            return listener

        return add_listener_

    def add_prefix(self: _ClientT, prefixes: typing.Union[typing.Iterable[str], str], /) -> _ClientT:
        if isinstance(prefixes, str):
            self._prefixes.add(prefixes)

        else:
            self._prefixes.update(prefixes)

        return self

    def remove_prefix(self, prefix: str, /) -> None:
        self._prefixes.remove(prefix)

    def set_prefix_getter(self: _ClientT, getter: typing.Optional[PrefixGetterSig], /) -> _ClientT:
        self._prefix_getter = getter
        return self

    # TODO: use generic callable type var here instead?
    def with_prefix_getter(self, getter: PrefixGetterSig) -> PrefixGetterSig:
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
        await asyncio.gather(*(component.close() for component in self._components))

        if deregister_listener and self._events:
            if event_type := self._accepts.get_event_type():
                self._try_unsubscribe(self._events, event_type, self.on_message_create_event)

            self._try_unsubscribe(
                self._events, interaction_events.InteractionCreateEvent, self.on_interaction_create_event
            )

            if self._server:
                self._server.set_listener(commands.CommandInteraction, None)

    async def open(self, *, register_listener: bool = True) -> None:
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

        await asyncio.gather(*(component.open() for component in self._components))

        if register_listener and self._events:
            if event_type := self._accepts.get_event_type():
                self._events.subscribe(event_type, self.on_message_create_event)

            self._events.subscribe(interaction_events.InteractionCreateEvent, self.on_interaction_create_event)

        if self._server:
            self._server.set_listener(commands.CommandInteraction, self.on_interaction_create_request)

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

    async def on_message_create_event(self, event: message_events.MessageCreateEvent) -> None:
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

        for component in self._components:
            if await component.execute_message(ctx, hooks=hooks):
                break

    async def on_interaction_create_event(self, event: interaction_events.InteractionCreateEvent, /) -> None:
        if not isinstance(event.interaction, commands.CommandInteraction):
            return

        ctx = context.InteractionContext(self, event.interaction).start_defer_timer(2.5)
        hooks: typing.Optional[typing.Set[tanjun_traits.InteractionHooks]] = None
        if self._hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._hooks)

        if self._interaction_hooks:
            if not hooks:
                hooks = set()

            hooks.add(self._interaction_hooks)

        for component in self._components:
            if await component.execute_interaction(ctx, hooks=hooks):
                break

    async def on_interaction_create_request(
        self, interaction: commands.CommandInteraction, /
    ) -> typing.Union[context.ResponseTypeT]:
        ctx = context.InteractionContext(self, interaction).start_defer_timer(2.5)
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
        for component in self._components:
            if await component.execute_interaction(ctx, hooks=hooks):
                break

        return await future
