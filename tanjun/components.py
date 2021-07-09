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

__all__: typing.Sequence[str] = ["Component"]

import itertools
import typing

from hikari.events import base_events

from tanjun import injector
from tanjun import traits
from tanjun import utilities

if typing.TYPE_CHECKING:
    from hikari.api import event_manager

    _CommandT = typing.TypeVar("_CommandT", bound=traits.ExecutableCommand)
    _ComponentT = typing.TypeVar("_ComponentT", bound="Component")
    _ValueT = typing.TypeVar("_ValueT")


# This class isn't slotted to let us overwrite command and event methods during initialisation by making sure
# class properties aren't read only
class Component(injector.Injectable, traits.Component):
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
        self._checks = set(injector.InjectableCheck(check) for check in checks) if checks else set()
        self._client: typing.Optional[traits.Client] = None
        self._commands: typing.Set[traits.ExecutableCommand] = set()
        self._hooks = hooks
        self._injector: typing.Optional[injector.InjectorClient] = None
        self._listeners: typing.Set[
            typing.Tuple[typing.Type[base_events.Event], event_manager.CallbackT[typing.Any]]
        ] = set()
        self._metadata: typing.Dict[typing.Any, typing.Any] = {}
        self.started = False

    def __repr__(self) -> str:
        return f"Component <{type(self).__name__}, {len(self._commands)} commands>"

    @property
    def checks(self) -> typing.AbstractSet[traits.CheckT]:
        return {check.callback for check in self._checks}

    @property
    def client(self) -> typing.Optional[traits.Client]:
        return self._client

    @property
    def commands(self) -> typing.AbstractSet[traits.ExecutableCommand]:
        return self._commands.copy()

    @property
    def hooks(self) -> typing.Optional[traits.Hooks]:
        return self._hooks

    # Seeing as this class isn't slotted we cannot overwrite settable properties with instance variables.
    @hooks.setter
    def hooks(self, hooks_: traits.Hooks, /) -> None:
        self._hooks = hooks_

    @property
    def needs_injector(self) -> bool:
        # TODO: cache this value maybe
        if any(check.needs_injector for check in self._checks):
            return True

        return any(isinstance(command, injector.Injectable) and command.needs_injector for command in self._commands)

    @property
    def listeners(
        self,
    ) -> typing.AbstractSet[typing.Tuple[typing.Type[base_events.Event], event_manager.CallbackT[typing.Any]]]:
        return self._listeners.copy()

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    def add_check(self: _ComponentT, check: traits.CheckT, /) -> _ComponentT:
        self._checks.add(injector.InjectableCheck(check, injector=self._injector))
        return self

    def remove_check(self, check: traits.CheckT, /) -> None:
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: traits.CheckT_inv, /) -> traits.CheckT_inv:
        self.add_check(check)
        return check

    def add_command(self: _ComponentT, command: traits.ExecutableCommand, /) -> _ComponentT:
        if self._injector and isinstance(command, injector.Injectable):
            command.set_injector(self._injector)

        self._commands.add(command)
        return self

    def remove_command(self, command: traits.ExecutableCommand, /) -> None:
        self._commands.remove(command)

    def with_command(self, command: _CommandT, /) -> _CommandT:
        self.add_command(command)
        return command

    def add_listener(
        self: _ComponentT, event: typing.Type[base_events.Event], listener: event_manager.CallbackT[typing.Any], /
    ) -> _ComponentT:
        self._listeners.add((event, listener))

        if self.started and self._client:
            self._client.event_service.event_manager.subscribe(event, listener)

        return self

    def remove_listener(
        self, event: typing.Type[base_events.Event], listener: event_manager.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.remove((event, listener))

        if self.started and self._client:
            self._client.event_service.event_manager.unsubscribe(event, listener)

    def with_listener(
        self, event: typing.Type[base_events.Event], /
    ) -> typing.Callable[[event_manager.CallbackT[_ValueT]], event_manager.CallbackT[_ValueT]]:
        def decorator(callback: event_manager.CallbackT[_ValueT], /) -> event_manager.CallbackT[_ValueT]:
            self.add_listener(event, callback)
            return callback

        return decorator

    def set_injector(self, client: injector.InjectorClient, /) -> None:
        if self._injector:
            raise RuntimeError("Injector already set")

        self._injector = client

        for check in self._checks:
            check.set_injector(client)

        for command in self._commands:
            if isinstance(command, injector.Injectable):
                command.set_injector(client)

    def bind_client(self, client: traits.Client, /) -> None:
        if self._client:
            raise RuntimeError("Client already set")

        self._client = client
        for event_, listener in self._listeners:
            self._client.event_service.event_manager.subscribe(event_, listener)

        for command in self._commands:
            command.bind_client(client)

    async def check_context(
        self, ctx: traits.Context, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[traits.FoundCommand]:
        ctx.component = self
        if await utilities.gather_checks(check(ctx) for check in self._checks):
            async for value in utilities.async_chain(
                command.check_context(ctx, name_prefix=name_prefix) for command in self._commands
            ):
                yield value

        ctx.component = None

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        yield from itertools.chain.from_iterable(command.check_name(name) for command in self._commands)

    def _try_unsubscribe(
        self,
        event_type: typing.Type[event_manager.EventT_co],
        callback: event_manager.CallbackT[event_manager.EventT_co],
    ) -> None:
        assert self._client
        try:
            self._client.event_service.event_manager.unsubscribe(event_type, callback)
        except (ValueError, LookupError):
            # TODO: add logging here
            pass

    async def close(self) -> None:
        if not self.started:
            return

        self.started = False
        if self._client:
            for event_, listener in self._listeners:
                self._try_unsubscribe(event_, listener)

    async def open(self) -> None:
        if self.started:
            return

        # This is duplicated between both open and bind_cluster to ensure that these are registered
        # as soon as possible the first time this is binded to a client and that these are
        # re-registered everytime an object is restarted.
        if self._client:
            for event_, listener in self._listeners:
                try:
                    self._try_unsubscribe(event_, listener)
                except (LookupError, ValueError):  # TODO: what does hikari raise?
                    continue

                self._client.event_service.event_manager.subscribe(event_, listener)

        self.started = True

    async def execute(
        self, ctx: traits.Context, /, *, hooks: typing.Optional[typing.MutableSet[traits.Hooks]] = None
    ) -> bool:
        if not self.started:
            return False

        async for result in self.check_context(ctx):
            ctx.triggering_name = result.name
            ctx.content = ctx.content[len(result.name) :].lstrip()
            # Only add our hooks and set command if we're sure we'll be executing the command here.
            ctx.command = result.command

            if self.hooks and hooks:
                hooks.add(self.hooks)

            elif self.hooks:
                hooks = {self.hooks}

            await result.command.execute(ctx, hooks=hooks)
            return True

        return False
