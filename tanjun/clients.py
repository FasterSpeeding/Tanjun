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

__all__: typing.Sequence[str] = ["as_loader", "Client", "PrefixGetterT"]

import asyncio
import importlib.util
import inspect
import itertools
import typing

from hikari import errors as hikari_errors
from hikari import traits as hikari_traits
from hikari.events import lifetime_events
from hikari.events import message_events
from yuyo import backoff

from tanjun import context
from tanjun import traits
from tanjun import utilities

if typing.TYPE_CHECKING:
    import pathlib
    import types

    from hikari import users

    ClientT = typing.TypeVar("ClientT", bound="Client")


PrefixGetterT = typing.Callable[[traits.Context], typing.Awaitable[typing.Iterable[str]]]
"""Type hint of a callable used to get the prefix(es) for a specific guild.

This should be an asynchronous callable which takes one positional argument of
type `tanjun.traits.Context` and returns an iterable of strings.
"""


class _LoadableDescriptor(traits.LoadableDescriptor):
    def __init__(self, function: traits.LoadableT, /) -> None:
        self._function = function
        utilities.with_function_wrapping(self, "load_function")

    def __call__(self, client: traits.Client, /) -> None:
        self._function(client)

    @property
    def load_function(self) -> traits.LoadableT:
        return self._function


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
def as_loader(function: traits.LoadableT) -> traits.LoadableT:
    """Mark a function as being used to load Tanjun utilities from a module.

    Parameters
    ----------
    function : traits.LoadableT
        The function used to load Tanjun utilities from the a module. This
        should take one argument of type `tanjun.traits.Client`, return nothing
        and will be expected to initiate and add utilities such as components
        to the provided client using it's protocol methods.

    Returns
    -------
    traits.LoadableT
        The decorated load function.
    """
    return _LoadableDescriptor(function)


class Client(traits.Client):
    __slots__: typing.Sequence[str] = (
        "_cache",
        "_checks",
        "_components",
        "_events",
        "hooks",
        "_metadata",
        "_prefix_getter",
        "_prefixes",
        "_rest",
        "_shards",
    )

    def __init__(
        self,
        events: hikari_traits.EventManagerAware,
        rest: typing.Optional[hikari_traits.RESTAware] = None,
        shard: typing.Optional[hikari_traits.ShardAware] = None,
        cache: typing.Optional[hikari_traits.CacheAware] = None,
        /,
        *,
        event_managed: bool = True,
    ) -> None:
        rest = utilities.try_find_type(hikari_traits.RESTAware, rest, events, shard, cache)
        if not rest:
            raise ValueError("Missing RESTAware client implementation.")

        shard = utilities.try_find_type(hikari_traits.ShardAware, shard, events, rest, cache)
        if not shard:
            raise ValueError("Missing ShardAware client implementation.")

        # Unlike `rest`, no provided Cache implementation just means this runs stateless.
        cache = utilities.try_find_type(hikari_traits.CacheAware, cache, events, rest, shard)
        # TODO: logging or something to indicate this is running statelessly rather than statefully.

        self._checks: typing.Set[traits.CheckT] = {self.check_human}
        self._cache = cache
        self._components: typing.Set[traits.Component] = set()
        self._events = events
        self.hooks: typing.Optional[traits.Hooks] = None
        self._metadata: typing.Dict[typing.Any, typing.Any] = {}
        self._prefix_getter: typing.Optional[PrefixGetterT] = None
        self._prefixes: typing.Set[str] = set()
        self._rest = rest
        self._shards = shard

        if event_managed:
            self._events.event_manager.subscribe(lifetime_events.StartingEvent, self._on_starting_event)
            self._events.event_manager.subscribe(lifetime_events.StoppingEvent, self._on_stopping_event)

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
    def cache_service(self) -> typing.Optional[hikari_traits.CacheAware]:
        return self._cache

    @property
    def checks(self) -> typing.AbstractSet[traits.CheckT]:
        return frozenset(self._checks)

    @property
    def components(self) -> typing.AbstractSet[traits.Component]:
        return frozenset(self._components)

    @property
    def event_service(self) -> hikari_traits.EventManagerAware:
        return self._events

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def prefix_getter(self) -> typing.Optional[PrefixGetterT]:
        return self._prefix_getter

    @property
    def prefixes(self) -> typing.AbstractSet[str]:
        return frozenset(self._prefixes)

    @property
    def rest_service(self) -> hikari_traits.RESTAware:
        return self._rest

    @property
    def shard_service(self) -> hikari_traits.ShardAware:
        return self._shards

    async def _on_starting_event(self, _: lifetime_events.StartingEvent, /) -> None:
        await self.open()

    async def _on_stopping_event(self, _: lifetime_events.StoppingEvent, /) -> None:
        await self.close()

    def add_check(self: ClientT, check: traits.CheckT, /) -> ClientT:
        self._checks.add(check)
        return self

    def remove_check(self, check: traits.CheckT, /) -> None:
        self._checks.remove(check)

    def with_check(self, check: traits.CheckT, /) -> traits.CheckT:
        self.add_check(check)
        return check

    async def check(self, ctx: traits.Context, /) -> bool:
        return await utilities.gather_checks(utilities.await_if_async(check, ctx) for check in self._checks)

    def add_component(self: ClientT, component: traits.Component, /) -> ClientT:
        self.add_component(component)
        return self

    def append_component(self, component: traits.Component, /) -> None:
        self._components.add(component)

    def remove_component(self, component: traits.Component, /) -> None:
        self._components.remove(component)

    def add_prefix(self: ClientT, prefixes: typing.Union[typing.Iterable[str], str], /) -> ClientT:
        if isinstance(prefixes, str):
            self._prefixes.add(prefixes)

        else:
            self._prefixes.update(prefixes)

        return self

    def remove_prefix(self, prefix: str, /) -> None:
        self._prefixes.remove(prefix)

    def set_prefix_getter(self: ClientT, getter: typing.Optional[PrefixGetterT], /) -> ClientT:
        self._prefix_getter = getter
        return self

    async def check_context(self, ctx: traits.Context, /) -> typing.AsyncIterator[traits.FoundCommand]:
        async for value in utilities.async_chain(component.check_context(ctx) for component in self._components):
            yield value

    @staticmethod
    def check_human(ctx: traits.Context, /) -> bool:
        return not ctx.message.author.is_bot and ctx.message.webhook_id is None

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        yield from itertools.chain.from_iterable(component.check_name(name) for component in self._components)

    async def _check_prefix(self, ctx: traits.Context, /) -> typing.Optional[str]:
        if self._prefix_getter:
            for prefix in await self._prefix_getter(ctx):
                if ctx.content.startswith(prefix):
                    return prefix

        for prefix in self._prefixes:
            if ctx.content.startswith(prefix):
                return prefix

        return None

    async def close(self, *, deregister_listener: bool = True) -> None:
        await asyncio.gather(*(component.close() for component in self._components))

        if deregister_listener:
            self._events.event_manager.unsubscribe(message_events.MessageCreateEvent, self.on_message_create)

    async def open(self, *, mention_prefix: bool = True, register_listener: bool = True) -> None:
        if mention_prefix:
            user: typing.Optional[users.User] = None
            if self._cache:
                user = self._cache.cache.get_me()

            if not user:
                retry = backoff.Backoff(max_retries=4, maximum=30)

                async for _ in retry:
                    try:
                        user = await self._rest.rest.fetch_my_user()
                        break

                    except (hikari_errors.RateLimitedError, hikari_errors.RateLimitTooLongError) as exc:
                        if exc.retry_after > 30:
                            raise

                        retry.set_next_backoff(exc.retry_after)

                    except hikari_errors.InternalServerError:
                        continue

                else:
                    user = await self._rest.rest.fetch_my_user()

            self._prefixes.add(f"<@{user.id}>")
            self._prefixes.add(f"<@!{user.id}>")

        await asyncio.gather(*(component.open() for component in self._components))

        if register_listener:
            self._events.event_manager.subscribe(message_events.MessageCreateEvent, self.on_message_create)

    def set_hooks(self: ClientT, hooks: typing.Optional[traits.Hooks], /) -> ClientT:
        self.hooks = hooks
        return self

    def load_modules(self: ClientT, modules: typing.Iterable[typing.Union[str, pathlib.Path]], /) -> ClientT:
        for module_path in modules:
            if isinstance(module_path, str):
                module = importlib.import_module(module_path)

            else:
                spec = importlib.util.spec_from_file_location(
                    module_path.name.rsplit(".", 1)[0], str(module_path.absolute())
                )
                module = importlib.util.module_from_spec(spec)

                # https://github.com/python/typeshed/issues/2793
                if not isinstance(spec.loader, importlib.abc.Loader):
                    raise RuntimeError(f"Invalid module provided {module_path}")

                # The type shedding is wrong here
                spec.loader.exec_module(module)

            for _, member in inspect.getmembers(module):
                if isinstance(member, traits.LoadableDescriptor):
                    member.load_function(self)

        return self

    async def on_message_create(self, event: message_events.MessageCreateEvent) -> None:
        if event.message.content is None:
            return

        ctx = context.Context(self, content=event.message.content, message=event.message)
        if (prefix := await self._check_prefix(ctx)) is None:
            return

        ctx.content = ctx.content.lstrip()[len(prefix) :].lstrip()
        ctx.triggering_prefix = prefix

        if not await self.check(ctx):
            return

        if self.hooks:
            hooks = {self.hooks}

        else:
            hooks = set()

        for component in self._components:
            if await component.execute(ctx, hooks=hooks):
                break
