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

__all__: typing.Sequence[str] = ["as_check", "as_command", "as_group", "as_listener", "Component"]

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
class CheckDescriptor(traits.CheckDescriptor[traits.ComponentT]):
    def __init__(self, check: traits.UnboundCheckT[traits.ComponentT], /) -> None:
        self._check = check
        utilities.with_function_wrapping(self, "_check")

    def __call__(self, *args: typing.Any) -> typing.Union[bool, typing.Coroutine[typing.Any, typing.Any, bool]]:
        return self._check(*args)

    @property
    def function(self) -> traits.UnboundCheckT[traits.ComponentT]:
        return self._check

    def build_check(self, component: traits.ComponentT, /) -> traits.CheckT:
        return types.MethodType(self._check, component)


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class CommandDescriptor(traits.CommandDescriptor):
    def __init__(
        self,
        checks: typing.Optional[typing.Iterable[traits.CheckT]],
        function: traits.CommandFunctionT,
        hooks: typing.Optional[traits.Hooks],
        names: typing.Sequence[str],
        parser: typing.Optional[traits.ParserDescriptor],
    ) -> None:
        self._unbound_checks: typing.List[traits.UnboundCheckT[typing.Any]] = []
        self._checks = list(checks) if checks else []
        self._function = function
        self._hooks = hooks
        self._metadata: typing.MutableMapping[typing.Any, typing.Any] = {}
        self._names = list(names)
        self._parser = parser
        utilities.with_function_wrapping(self, "function")

    async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return await self._function(*args, **kwargs)

    def __repr__(self) -> str:
        return f"CommandDescriptor <{self._function, self._names}>"

    @property
    def function(self) -> traits.CommandFunctionT:
        return self._function

    @property
    def is_owned(self) -> bool:
        return False

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

    def with_check(self, check: traits.UnboundCheckT[traits.ComponentT], /) -> traits.UnboundCheckT[traits.ComponentT]:
        self._unbound_checks.append(check)
        return check

    def add_name(self, name: str, /) -> None:
        self._names.append(name)

    def build_command(self, component: traits.Component, /) -> traits.ExecutableCommand:
        checks = self._checks.copy()
        checks.extend(types.MethodType(check, component) for check in self._unbound_checks)
        command = commands.Command(
            types.MethodType(self._function, component),
            *self._names,
            checks=checks,
            hooks=copy.copy(self._hooks),
            metadata=dict(self._metadata),
            parser=self.parser.build_parser(component) if self.parser else None,
        )
        command.bind_component(component)
        return command


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class _OwnedCommandDescriptor(CommandDescriptor):
    @property
    def is_owned(self) -> bool:
        return True


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class CommandGroupDescriptor(CommandDescriptor):
    def __init__(
        self,
        checks: typing.Optional[typing.Iterable[traits.CheckT]],
        function: traits.CommandFunctionT,
        hooks: typing.Optional[traits.Hooks],
        names: typing.Sequence[str],
        parser: typing.Optional[traits.ParserDescriptor],
    ) -> None:
        super().__init__(checks, function, hooks, names, parser)
        self._commands: typing.MutableSequence[CommandDescriptor] = []

    def __repr__(self) -> str:
        return f"CommandGroupDescriptor <{self._function, self._names}, commands: {len(self._commands)}>"

    def build_command(self, component: traits.Component, /) -> traits.ExecutableCommandGroup:
        checks = self._checks.copy()
        checks.extend(types.MethodType(check, component) for check in self._unbound_checks)
        group = commands.CommandGroup(
            types.MethodType(self._function, component),
            *self._names,
            checks=checks,
            hooks=copy.copy(self._hooks),
            metadata=dict(self._metadata),
            parser=self.parser.build_parser(component) if self.parser else None,
        )
        group.bind_component(component)

        for descriptor in self._commands:
            group.add_command(descriptor.build_command(component))

        return group

    def with_command(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        parser: typing.Optional[traits.ParserDescriptor] = None,
    ) -> typing.Callable[[traits.CommandFunctionT], CommandDescriptor]:
        def decorator(function: traits.CommandFunctionT) -> CommandDescriptor:
            descriptor = _OwnedCommandDescriptor(checks, function, hooks, (name, *names), parser)
            self._commands.append(descriptor)
            return descriptor

        return decorator


# This class is left unslotted as to allow it to "wrap" the underlying function
# by overwriting class attributes.
class ListenerDescriptor(traits.ListenerDescriptor):
    def __init__(
        self, event: typing.Type[base_events.Event], function: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._event = event
        self._listener = function
        utilities.with_function_wrapping(self, "function")

    async def __call__(self, *args: typing.Any) -> None:
        return await self._listener(*args)

    def __repr__(self) -> str:
        return f"ListenerDescriptor for {self._event.__name__}: {self._listener}>"

    @property
    def event(self) -> typing.Type[base_events.Event]:
        return self._event

    @property
    def function(self) -> event_dispatcher.CallbackT[typing.Any]:
        return self._listener

    def build_listener(
        self, component: traits.Component, /
    ) -> typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]:
        return self._event, types.MethodType(self._listener, component)


def as_check(check: traits.UnboundCheckT[typing.Any]) -> traits.CheckT:
    """Declare a check descriptor on a component's class.

    The returned descriptor will be loaded into the component it's attached to
    during initialisation.

    Parameters
    ----------
    check : traits.CheckT
        The method to decorate as a check.

    Returns
    -------
    traits.CheckT
        The decorated method.

    Examples
    --------
    ```python
    import tanjun

    class MyComponent(tanjun.components.Component):
        def __init__(self, *args, **kwargs, blacklist) -> None:
            self.blacklist = set(blacklist)

        @tanjun.components.as_check
        def blacklisted_check(self, ctx: tanjun.traits.Context, /) -> None:
            return ctx.message.author.id in self.blacklist
    ```
    """
    return CheckDescriptor(check)


def as_command(
    name: str,
    /,
    *names: str,
    checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
    hooks: typing.Optional[traits.Hooks] = None,
    parser: typing.Optional[traits.ParserDescriptor] = None,
) -> typing.Callable[[traits.CommandFunctionT], CommandDescriptor]:
    """Declare a command descriptor on a component's class.

    The returned descriptor will be loaded into the component it's attached to
    during initialisation.

    Parameters
    ----------
    name : str
        The name for this command.

    Other Parameters
    ----------------
    *names : str
        Additional names for this command passed as variable positional arguments.
    checks : typing.Optional[typing.Iterable[traits.CheckT]]
        An iterable of async or non-async check functions which should take
        one positional argument of type `Context` and return `builtins.bool`
        or raise `tanjun.errors.FailedCheck` where `FailedCheck` or `False` will
        prevent the command from being chosen for execution.
    hooks : typing.Optional[traits.Hooks]
        The execution hooks this command should be calling.
    parser : typing.Optional[traits.ParserDescriptor]
        A descriptor of the parser this command should use.

    Returns
    -------
    typing.Callable[[traits.CommandFunctionT], CommandDescriptor]
        A decorator function for a command function.

    Examples
    --------
    Methods and attributes on the returned descriptor can be modified directly
    or using decorators in-order to fine tune the behaviour of this command
    (e.g. set a parser for the command) as shown below.

    ```python
    import tanjun

    class MyComponent(tanjun.components.Component):
        @tanjun.parsing.with_greedy_argument("content", converters=None)
        @tanjun.parsing.with_parser
        @tanjun.checks.with_owner_check
        @tanjun.components.as_command("echo")
        async def echo_command(self, ctx: tanjun.traits.Context, /, content: str) -> None:
            await ctx.message.respond(content)
    ```
    """

    def decorator(function: traits.CommandFunctionT, /) -> CommandDescriptor:
        return CommandDescriptor(checks, function, hooks, (name, *names), parser)

    return decorator


def as_group(
    name: str,
    /,
    *names: str,
    checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
    hooks: typing.Optional[traits.Hooks] = None,
    parser: typing.Optional[traits.ParserDescriptor] = None,
) -> typing.Callable[[traits.CommandFunctionT], CommandGroupDescriptor]:
    """Declare a command group descriptor on a component's class.

    The returned descriptor will be loaded into the component it's attached to
    during initialisation.

    Parameters
    ----------
    name : str
        The name for this command group.

    Other Parameters
    ----------------
    *names : str
        Additional names for this command group passed as variable positional arguments.
    checks : typing.Optional[typing.Iterable[traits.CheckT]]
        An iterable of async or non-async check functions which should take
        one positional argument of type `Context` and return `builtins.bool`
        or raise `tanjun.errors.FailedCheck` where `FailedCheck` or `False` will
        prevent the command from being chosen for execution.
    hooks : typing.Optional[traits.Hooks]
        The execution hooks this command should be calling.
    parser : typing.Optional[traits.ParserDescriptor]
        A descriptor of the parser this command should use.

    Returns
    -------
    typing.Callable[[traits.CommandFunctionT], CommandGroupDescriptor]
        A decorator function for a command function.

    Examples
    --------
    Methods and attributes on the returned descriptor can be modified directly
    or using decorators in-order to fine tune the behaviour of this command
    (e.g. set a parser for the command) as shown below.

    ```python
    import tanjun

    class MyComponent(tanjun.components.Component):
        @tanjun.parsing.with_greedy_argument("content", converters=None)
        @tanjun.parsing.with_parser
        @tanjun.checks.with_owner_check
        @tanjun.components.as_group("help")
        async def help(self, ctx: tanjun.traits.Context, /, content: str) -> None:
            await ctx.message.respond(f"`{content}` is not a valid help command")
    ```

    The `CommandGroupDescriptor.with_command` can be called on the returned
    descriptor in-order to add sub-commands to this group as shown below.

    ```python
    import tanjun

    class MyComponent(tanjun.components.Component):
        @tanjun.parsing.with_greedy_argument("content", converters=None)
        @tanjun.parsing.with_parser
        @tanjun.components.as_group("help")
        async def help(self, ctx: tanjun.traits.Context, /, content: str) -> None:
            await ctx.message.respond(f"`{content}` is not a valid help command")

        @help.with_command("me")
        async def help_me(self, ctx: tanjun.traits.Context) -> None:
            await ctx.message.respond(f"There is no reset for you, {ctx.message.author}")
    ```
    """

    def decorator(function: traits.CommandFunctionT, /) -> CommandGroupDescriptor:
        return CommandGroupDescriptor(checks, function, hooks, (name, *names), parser)

    return decorator


EventDecoratorT = typing.Callable[
    ["event_dispatcher.CallbackT[event_dispatcher.EventT_inv]"],
    "event_dispatcher.CallbackT[event_dispatcher.EventT_inv]",
]


def as_listener(cls: typing.Type[event_dispatcher.EventT_inv], /) -> EventDecoratorT[event_dispatcher.EventT_inv]:
    """Declare an event listener

    The returned descriptor will be loaded into the component it's attached to
    during initialisation.

    Parameters
    ----------
    cls : typing.Type[hikari.api.event_dispatcher.EventT_inv]
        The Hikari event class this listener should be called for.

    Returns
    -------
    EventDecoratorT[event_dispatcher.EventT_inv]
        The callable event decorator which takes the event's asynchronous
        listener function (with signature {self, event, /}) as it's only
        positional argument and returns a listener descriptor.

    Examples
    --------
    ```python
    from hikari import events
    import tanjun

    class MyComponent(tanjun.components.Component):
        @tanjun.components.as_listener(events.GuildVisibilityEvent)
        async def on_guild_visibility_event(self, event: events.GuildVisibilityEvent) -> None:
            ...
    ```
    """

    def decorator(
        function: event_dispatcher.CallbackT[event_dispatcher.EventT_inv], /
    ) -> event_dispatcher.CallbackT[event_dispatcher.EventT_inv]:
        return ListenerDescriptor(cls, function)

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

    def add_command(self, command: typing.Union[traits.ExecutableCommand, traits.CommandDescriptor], /) -> None:
        command = command.build_command(self) if isinstance(command, traits.CommandDescriptor) else command
        self._commands.add(command)

    def remove_command(self, command: traits.ExecutableCommand, /) -> None:
        self._commands.remove(command)

    def add_listener(
        self, event: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.add((event, listener))

        if self.started and self._client:
            self._client.dispatch_service.dispatcher.subscribe(event, listener)

    def remove_listener(
        self, event: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any], /
    ) -> None:
        self._listeners.remove((event, listener))

        if self.started and self._client:
            self._client.dispatch_service.dispatcher.unsubscribe(event, listener)

    def bind_client(self, client: traits.Client, /) -> None:
        self._client = client
        for event_, listener in self._listeners:
            self._client.dispatch_service.dispatcher.subscribe(event_, listener)

        for command in self._commands:
            command.bind_client(client)

    async def check_context(
        self, ctx: traits.Context, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[traits.FoundCommand]:
        if await utilities.gather_checks(utilities.await_if_async(check, ctx) for check in self._checks):
            async for value in utilities.async_chain(
                command.check_context(ctx, name_prefix=name_prefix) for command in self._commands
            ):
                yield value

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        yield from itertools.chain.from_iterable(command.check_name(name) for command in self._commands)

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
                except (LookupError, ValueError):  # TODO: what does hikari raise?
                    continue

                self._client.dispatch_service.dispatcher.subscribe(event_, listener)

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

    def _load_from_properties(self) -> None:
        for name, member in inspect.getmembers(self):
            if isinstance(member, traits.CommandDescriptor):
                result = member.build_command(self)

                # We don't want to load in commands which belong to a command group here.
                if not member.is_owned:
                    self.add_command(result)

                setattr(self, name, result.function)

            elif isinstance(member, traits.ListenerDescriptor):
                event_, listener = member.build_listener(self)
                self.add_listener(event_, listener)
                setattr(self, name, listener)

            elif isinstance(member, traits.CheckDescriptor):
                check = member.build_check(self)
                self.add_check(check)
                setattr(self, name, check)
