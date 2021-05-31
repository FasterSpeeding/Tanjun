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

__all__: typing.Sequence[str] = ["as_loader", "Client"]

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
        "_grab_mention_prefix",
        "hooks",
        "_metadata",
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
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        mention_prefix: bool = True,
        modules: typing.Optional[typing.Iterable[typing.Union[pathlib.Path, str]]] = None,
        prefixes: typing.Optional[typing.Iterable[str]] = None,
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

        self._checks: typing.Set[traits.CheckT] = {self.check_human, *(checks or ())}
        self._cache = cache
        self._components: typing.Set[traits.Component] = set()
        self._events = events
        self._grab_mention_prefix = mention_prefix
        self.hooks = hooks
        self._metadata: typing.Dict[typing.Any, typing.Any] = {}
        self._prefixes = set(prefixes) if prefixes else set()
        self._rest = rest
        self._shards = shard
        self._events.event_manager.subscribe(lifetime_events.StartingEvent, self._on_starting_event)
        self._events.event_manager.subscribe(lifetime_events.StoppingEvent, self._on_stopping_event)

        if modules:
            self.load_from_modules(modules)

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

    def add_check(self, check: traits.CheckT, /) -> None:
        self._checks.add(check)

    def remove_check(self, check: traits.CheckT, /) -> None:
        self._checks.remove(check)

    async def check(self, ctx: traits.Context, /) -> bool:
        return await utilities.gather_checks(utilities.await_if_async(check, ctx) for check in self._checks)

    def add_component(self, component: traits.Component, /) -> None:
        component.bind_client(self)
        self._components.add(component)

    def remove_component(self, component: traits.Component, /) -> None:
        self._components.remove(component)

    def add_prefix(self, prefix: str, /) -> None:
        self._prefixes.add(prefix)

    def remove_prefix(self, prefix: str, /) -> None:
        self._prefixes.remove(prefix)

    async def check_context(self, ctx: traits.Context, /) -> typing.AsyncIterator[traits.FoundCommand]:
        async for value in utilities.async_chain(component.check_context(ctx) for component in self._components):
            yield value

    @staticmethod
    def check_human(ctx: traits.Context, /) -> bool:
        return not ctx.message.author.is_bot and ctx.message.webhook_id is None

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        yield from itertools.chain.from_iterable(component.check_name(name) for component in self._components)

    async def check_prefix(self, content: str, /) -> typing.Optional[str]:
        for prefix in self._prefixes:
            if content.startswith(prefix):
                return prefix

        return None

    async def close(self, *, deregister_listener: bool = True) -> None:
        await asyncio.gather(*(component.close() for component in self._components))

        if deregister_listener:
            self._events.event_manager.unsubscribe(message_events.MessageCreateEvent, self.on_message_create)

    async def open(self, *, register_listener: bool = True) -> None:
        await asyncio.gather(*(component.open() for component in self._components))

        if self._grab_mention_prefix:
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

            self._grab_mention_prefix = False
            self._prefixes.add(f"<@{user.id}>")
            self._prefixes.add(f"<@!{user.id}>")

        if register_listener:
            self._events.event_manager.subscribe(message_events.MessageCreateEvent, self.on_message_create)

    def load_from_modules(self, modules: typing.Iterable[typing.Union[str, pathlib.Path]]) -> None:
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

    async def on_message_create(self, event: message_events.MessageCreateEvent) -> None:
        if event.message.content is None:
            return

        if (prefix := await self.check_prefix(event.message.content)) is None:
            return

        content = event.message.content.lstrip()[len(prefix) :].lstrip()
        ctx = context.Context(self, content=content, message=event.message, triggering_prefix=prefix)

        if not await self.check(ctx):
            return

        if self.hooks:
            hooks = {self.hooks}

        else:
            hooks = set()

        for component in self._components:
            if await component.execute(ctx, hooks=hooks):
                break
