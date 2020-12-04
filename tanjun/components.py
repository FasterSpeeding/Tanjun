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

__all__: typing.Sequence[str] = ["command", "Component", "event", "group"]

import copy
import inspect
import itertools
import types
import typing

from hikari.events import base_events

from tanjun import commands
from tanjun import traits
from tanjun import utilities

if typing.TYPE_CHECKING:
    from hikari.api import event_dispatcher


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class _CommandDescriptor(traits.CommandDescriptor):
    def __init__(
        self,
        checks: typing.Optional[typing.Iterable[traits.CheckT]],
        function: traits.CommandFunctionT,
        hooks: typing.Optional[traits.Hooks],
        names: typing.Sequence[str],
        parser: typing.Optional[traits.ParserDescriptor],
    ) -> None:
        self._checks = list(checks) if checks else []
        self._function = function
        self._hooks = hooks
        self._metadata: typing.MutableMapping[typing.Any, typing.Any] = {}
        self._names = list(names)
        self._parser = parser
        utilities.with_function_wrapping(self, "function")

    async def __call__(self, ctx: traits.Context, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return await self._function(ctx, *args, **kwargs)

    def __repr__(self) -> str:
        return f"CommandDescriptor <{self._function, self._names}>"

    @property
    def function(self) -> traits.CommandFunctionT:
        return self._function

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def parser(self) -> typing.Optional[traits.ParserDescriptor]:
        return self._parser

    @parser.setter
    def parser(self, parser_: typing.Optional[traits.ParserDescriptor]) -> None:
        self._parser = parser_

    def add_check(self, check: traits.CheckT, /) -> None:
        self._checks.append(check)

    def with_check(self, check: traits.CheckT, /) -> traits.CheckT:
        self.add_check(check)
        return check

    def add_name(self, name: str, /) -> None:
        self._names.append(name)

    def build_command(self, component: traits.Component, /) -> traits.ExecutableCommand:
        command_ = commands.Command(
            types.MethodType(self._function, component),
            *self._names,
            checks=self._checks.copy(),
            hooks=copy.copy(self._hooks),
            metadata=dict(self._metadata),
            parser=self.parser.build_parser(component) if self.parser else None,
        )
        command_.bind_component(component)
        return command_


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class _CommandGroupDescriptor(_CommandDescriptor):
    def __init__(
        self,
        checks: typing.Optional[typing.Iterable[traits.CheckT]],
        function: traits.CommandFunctionT,
        hooks: typing.Optional[traits.Hooks],
        names: typing.Sequence[str],
        parser: typing.Optional[traits.ParserDescriptor],
    ) -> None:
        super().__init__(checks, function, hooks, names, parser)
        self._commands: typing.MutableSequence[_CommandDescriptor] = []

    def __repr__(self) -> str:
        return f"CommandGroupDescriptor <{self._function, self._names}, commands: {len(self._commands)}>"

    def build_command(self, component: traits.Component, /) -> traits.ExecutableCommandGroup:
        group_ = commands.CommandGroup(
            types.MethodType(self._function, component),
            *self._names,
            checks=self._checks.copy(),
            hooks=copy.copy(self._hooks),
            metadata=dict(self._metadata),
            parser=self.parser.build_parser(component) if self.parser else None,
        )
        group_.bind_component(component)

        for descriptor in self._commands:
            group_.add_command(descriptor.build_command(component))

        return group_

    def with_command(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        parser: typing.Optional[traits.ParserDescriptor] = None,
    ) -> typing.Callable[[traits.CommandFunctionT], traits.CommandFunctionT]:
        def decorator(function: traits.CommandFunctionT) -> traits.CommandFunctionT:
            self._commands.append(_CommandDescriptor(checks, function, hooks, (name, *names), parser))
            return function

        return decorator


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class _ListenerDescriptor(traits.ListenerDescriptor):
    def __init__(
        self, event_: typing.Type[base_events.Event], function: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self.event = event_
        self.listener = function
        utilities.with_function_wrapping(self, "listener")

    async def __call__(self, event_: base_events.Event, /) -> None:
        return await self.listener(event)

    def __repr__(self) -> str:
        return f"ListenerDescriptor for {self.event.__name__}: {self.listener}>"

    def build_listener(
        self, component: traits.Component, /
    ) -> typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]:
        return self.event, types.MethodType(self.listener, component)


def command(
    name: str,
    /,
    *names: str,
    checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
    hooks: typing.Optional[traits.Hooks] = None,
    parser: typing.Optional[traits.ParserDescriptor] = None,
) -> typing.Callable[[traits.CommandFunctionT], traits.CommandFunctionT]:
    def decorator(function: traits.CommandFunctionT, /) -> traits.CommandFunctionT:
        return _CommandDescriptor(checks, function, hooks, (name, *names), parser)

    return decorator


def group(
    name: str,
    /,
    *names: str,
    checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
    hooks: typing.Optional[traits.Hooks] = None,
    parser: typing.Optional[traits.ParserDescriptor] = None,
) -> typing.Callable[[traits.CommandFunctionT], traits.CommandFunctionT]:
    def decorator(function: traits.CommandFunctionT, /) -> traits.CommandFunctionT:
        return _CommandGroupDescriptor(checks, function, hooks, (name, *names), parser)

    return decorator


def event(
    cls: typing.Type[traits.EventT], /
) -> typing.Callable[[event_dispatcher.CallbackT[traits.EventT]], event_dispatcher.CallbackT[traits.EventT]]:
    def decorator(function: event_dispatcher.CallbackT[traits.EventT], /) -> event_dispatcher.CallbackT[traits.EventT]:
        return _ListenerDescriptor(cls, function)

    return decorator


# This class isn't slotted to let us overwrite command and event methods during initialisation by making sure
# class properties aren't read only
class Component(traits.Component):
    started: bool
    """Whether this component has been "started" yet.

    When this is `builtins.False` executing the cluster will always do nothing.
    """

    def __init__(
        self,
        *,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
    ) -> None:
        self._checks = set(checks) if checks else set()
        self._client: typing.Optional[traits.Client] = None
        self._commands: typing.MutableSet[traits.ExecutableCommand] = set()
        self._hooks = hooks
        self._listeners: typing.MutableSet[
            typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]
        ] = set()
        self._metadata: typing.MutableMapping[typing.Any, typing.Any] = {}
        self.started = False
        self._load_from_properties()

    def __repr__(self) -> str:
        return f"Component <{type(self).__name__}, {len(self._commands)} commands>"

    @property
    def checks(self) -> typing.AbstractSet[traits.CheckT]:
        return frozenset(self._checks)

    @property
    def client(self) -> typing.Optional[traits.Client]:
        return self._client

    @property
    def commands(self) -> typing.AbstractSet[traits.ExecutableCommand]:
        return frozenset(self._commands)

    @property
    def hooks(self) -> typing.Optional[traits.Hooks]:
        return self._hooks

    # Seeing as this class isn't slotted we cannot overwrite settable properties with instance variables.
    @hooks.setter
    def hooks(self, hooks_: traits.Hooks, /) -> None:
        self._hooks = hooks_

    @property
    def listeners(
        self,
    ) -> typing.AbstractSet[typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]]:
        return frozenset(self._listeners)

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    def add_check(self, check: traits.CheckT, /) -> None:
        self._checks.add(check)

    def remove_check(self, check: traits.CheckT, /) -> None:
        self._checks.remove(check)

    def with_check(self, check: traits.CheckT, /) -> traits.CheckT:
        self.add_check(check)
        return check

    def add_command(self, command_: traits.ExecutableCommand, /) -> None:
        self._commands.add(command_)

    def remove_command(self, command_: traits.ExecutableCommand, /) -> None:
        self._commands.remove(command_)

    def add_listener(
        self, event_: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.add((event_, listener))

        if self.started and self._client:
            self._client.dispatch_service.dispatcher.subscribe(event_, listener)

    def remove_listener(
        self, event_: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.remove((event_, listener))

        if self.started and self._client:
            self._client.dispatch_service.dispatcher.unsubscribe(event_, listener)

    def bind_client(self, client: traits.Client, /) -> None:
        self._client = client
        for event_, listener in self._listeners:
            self._client.dispatch_service.dispatcher.subscribe(event_, listener)

        for command_ in self._commands:
            command_.bind_client(client)

    async def check_context(
        self, ctx: traits.Context, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[traits.FoundCommand]:
        if await utilities.gather_checks(utilities.await_if_async(check, ctx) for check in self._checks):
            async for value in utilities.async_chain(
                command_.check_context(ctx, name_prefix=name_prefix) for command_ in self._commands
            ):
                yield value

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        yield from itertools.chain.from_iterable(command_.check_name(name) for command_ in self._commands)

    async def close(self) -> None:
        if not self.started:
            return

        self.started = False
        if self._client:
            for event_, listener in self._listeners:
                self._client.dispatch_service.dispatcher.unsubscribe(event_, listener)

    async def open(self) -> None:
        if self.started:
            return

        # This is duplicated between both open and bind_cluster to ensure that these are registered
        # as soon as possible the first time this is binded to a client and that these are
        # re-registered everytime an object is restarted.
        if self._client:
            for event_, listener in self._listeners:
                try:
                    self._client.dispatch_service.dispatcher.unsubscribe(event_, listener)
                except (KeyError, ValueError, LookupError):  # TODO: what does hikari raise?
                    continue

                self._client.dispatch_service.dispatcher.subscribe(event_, listener)

        self.started = True

    async def execute(
        self, ctx: traits.Context, /, *, hooks: typing.Optional[typing.MutableSet[traits.Hooks]] = None
    ) -> bool:
        if not self.started:
            return False

        async for command_ in self.check_context(ctx):
            ctx.triggering_name = command_.name
            ctx.content = ctx.content[len(command_.name) :].lstrip()
            # Only add our hooks and set command if we're sure we'll be executing the command here.
            ctx.command = command_.command

            if self.hooks and hooks:
                hooks.add(self.hooks)

            elif self.hooks:
                hooks = {self.hooks}

            await command_.command.execute(ctx, hooks=hooks)
            return True

        return False

    def _load_from_properties(self) -> None:
        for name, member in inspect.getmembers(self):
            if isinstance(member, traits.CommandDescriptor):
                result = member.build_command(self)
                self.add_command(result)
                setattr(self, name, result.function)

            elif isinstance(member, traits.ListenerDescriptor):
                event_, listener = member.build_listener(self)
                self.add_listener(event_, listener)
                setattr(self, name, listener)
