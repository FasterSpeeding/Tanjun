# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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

__all__: typing.Sequence[str] = ["command", "Component", "event"]

import inspect
import itertools
import typing

from hikari import undefined
from hikari.events import base_events

from tanjun import commands
from tanjun import traits
from tanjun import utilities

if typing.TYPE_CHECKING:
    from hikari.api import event_dispatcher


def command(
    name: str,
    /,
    *names: str,
    checks: typing.Optional[typing.Iterable[commands.CheckT]] = None,
    hooks: typing.Optional[traits.Hooks] = None,
    parser: undefined.UndefinedNoneOr[traits.Parser] = undefined.UNDEFINED,
) -> typing.Callable[[commands.CommandFunctionT], commands.Command]:
    def decorator(function: commands.CommandFunctionT, /) -> commands.Command:
        return commands.Command(function, name, *names, checks=checks, hooks=hooks, parser=parser)

    return decorator


def event(
    cls: typing.Type[base_events.Event], /
) -> typing.Callable[[event_dispatcher.CallbackT[typing.Any]], event_dispatcher.CallbackT[typing.Any]]:
    def decorator(function: event_dispatcher.CallbackT[typing.Any], /) -> event_dispatcher.CallbackT[typing.Any]:
        setattr(function, "__event__", cls)
        return function

    return decorator


class Component(traits.Component):
    __slots__: typing.Sequence[str] = ("_client", "_commands", "hooks", "_listeners", "started")

    started: bool
    """Whether this component has been "started" yet.

    When this is `builtins.False` executing the cluster will always do nothing.
    """

    def __init__(self, *, hooks: typing.Optional[traits.Hooks] = None) -> None:
        self._client: typing.Optional[traits.Client] = None
        self._commands: typing.MutableSet[traits.ExecutableCommand] = set()
        self.hooks = hooks
        self._listeners: typing.MutableSet[
            typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]
        ] = set()
        self.started = False

        for name, member in inspect.getmembers(self):
            if isinstance(member, traits.ExecutableCommand):
                member.bind_component(self)
                self.add_command(member)

            elif (event_ := getattr(member, "__event__", None)) is not None:
                member = typing.cast("event_dispatcher.CallbackT[typing.Any]", member)

                if not issubclass(event_, base_events.Event):
                    raise RuntimeError(f"{event_} is not a valid event class.")

                self.add_listener(event_, member)

    @property
    def client(self) -> typing.Optional[traits.Client]:
        return self._client

    @property
    def commands(self) -> typing.AbstractSet[traits.ExecutableCommand]:
        return frozenset(self._commands)

    @property
    def listeners(
        self,
    ) -> typing.AbstractSet[typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]]:
        return frozenset(self._listeners)

    def add_command(self, command_: traits.ExecutableCommand, /) -> None:
        self._commands.add(command_)

    def remove_command(self, command_: traits.ExecutableCommand, /) -> None:
        self._commands.remove(command_)

    def add_listener(
        self, event_: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.add((event_, listener))

        if self.started and self._client:
            self._client.dispatch.dispatcher.subscribe(event_, listener)

    def remove_listener(
        self, event_: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.remove((event_, listener))

        if self.started and self._client:
            self._client.dispatch.dispatcher.unsubscribe(event_, listener)

    def bind_client(self, client: traits.Client, /) -> None:
        self._client = client
        for event_, listener in self._listeners:
            self._client.dispatch.dispatcher.subscribe(event_, listener)

    async def check_context(self, ctx: traits.Context, /) -> typing.AsyncIterator[traits.FoundCommand]:
        async for value in utilities.async_chain(command_.check_context(ctx) for command_ in self._commands):
            yield value

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        yield from itertools.chain.from_iterable(command_.check_name(name) for command_ in self._commands)

    async def close(self) -> None:
        if not self.started:
            return

        self.started = False
        if self._client:
            for event_, listener in self._listeners:
                self._client.dispatch.dispatcher.unsubscribe(event_, listener)

    async def open(self) -> None:
        if self.started:
            return

        # This is duplicated between both open and bind_cluster to ensure that these are registered
        # as soon as possible the first time this is binded to a client and that these are
        # re-registered everytime an object is restarted.
        if self._client:
            for event_, listener in self._listeners:
                try:
                    self._client.dispatch.dispatcher.unsubscribe(event_, listener)
                except (KeyError, ValueError, LookupError):  # TODO: what does hikari raise?
                    continue

                self._client.dispatch.dispatcher.subscribe(event_, listener)

        self.started = True

    async def execute(
        self, ctx: traits.Context, /, *, hooks: typing.Optional[typing.MutableSet[traits.Hooks]] = None
    ) -> bool:
        if not self.started:
            return False

        async for command_ in self.check_context(ctx):
            ctx.triggering_name = command_.name
            ctx.triggering_prefix = command_.prefix
            ctx.content = ctx.content[len(command_.name) :].strip()
            # Only add our hooks and set command if we're sure we'll be executing the command here.
            ctx.command = command_.command

            if self.hooks and hooks:
                hooks.add(self.hooks)

            elif self.hooks:
                hooks = {self.hooks}

            await command_.command.execute(ctx, hooks=hooks)
            return True

        return False
