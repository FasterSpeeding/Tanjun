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
"""Standard implementation of Tanjun's "components" used to manage separate features within a client."""
from __future__ import annotations

__all__: list[str] = [
    "CommandT",
    "Component",
    "LoadableProtocol",
    "OnCallbackSig",
    "OnCallbackSigT",
    "WithCommandReturnSig",
]

import asyncio
import base64
import copy
import inspect
import itertools
import logging
import random
import typing
from collections import abc as collections

from hikari.events import base_events

from . import abc
from . import checks as checks_
from . import errors
from . import injecting
from . import utilities

if typing.TYPE_CHECKING:
    _ComponentT = typing.TypeVar("_ComponentT", bound="Component")
    _T = typing.TypeVar("_T")


CommandT = typing.TypeVar("CommandT", bound="abc.ExecutableCommand[typing.Any]")
_LOGGER = logging.getLogger("hikari.tanjun.components")
# This errors on earlier 3.9 releases when not quotes cause dumb handling of the [CommandT] list
WithCommandReturnSig = typing.Union[CommandT, "collections.Callable[[CommandT], CommandT]"]

OnCallbackSig = collections.Callable[..., abc.MaybeAwaitableT[None]]
"""Type hint of a on_open or on_close component callback.

These support dependency injection, should expect no positional arguments and
should return `None`.
"""


OnCallbackSigT = typing.TypeVar("OnCallbackSigT", bound=OnCallbackSig)
"""Generic version of `OnCallbackSig`."""


@typing.runtime_checkable
class LoadableProtocol(typing.Protocol):
    """Protocol of an object which can be loaded into a component from an instance variable."""

    # This fucks with MyPy even though at runtime python just straight out ignores slots when considering protocol
    if not typing.TYPE_CHECKING:  # compatibility.
        __slots__ = ()

    def copy(self: _T) -> _T:
        """Copy the object.

        This will be called before load_into_component.

        Returns
        -------
        Self
            The copied object.
        """
        raise NotImplementedError

    def load_into_component(self, component: abc.Component, /) -> typing.Optional[typing.Any]:
        """Load the object into the component.

        Parameters
        ----------
        component : tanjun.abc.Component
            The component this object should be loaded into.

        Returns
        -------
        typing.Optional[typing.Any]
            An object to replace the attribute this object was found at.
            If `None` is returned, the attribute will be left as-is.
        """
        raise NotImplementedError


def _with_command(
    add_command: collections.Callable[[CommandT], Component],
    maybe_command: typing.Optional[CommandT],
    /,
    *,
    copy: bool = False,
) -> WithCommandReturnSig[CommandT]:
    if maybe_command:
        maybe_command = maybe_command.copy() if copy else maybe_command
        add_command(maybe_command)
        return maybe_command

    def decorator(command: CommandT, /) -> CommandT:
        command = command.copy() if copy else command
        add_command(command)
        return command

    return decorator


def _filter_scope(scope: collections.Mapping[str, typing.Any]) -> collections.Iterator[typing.Any]:
    return (value for key, value in scope.items() if not key.startswith("_"))


class _ComponentManager(abc.AbstractLoader):
    __slots__ = ("_component", "_copy")

    def __init__(self, component: Component, copy: bool) -> None:
        self._component = component
        self._copy = copy

    def load(self, client: abc.Client, /) -> bool:
        client.add_component(self._component.copy() if self._copy else self._component)
        return True

    def unload(self, client: abc.Client, /) -> bool:
        client.remove_component_by_name(self._component.name)
        return True


# TODO: do we want to setup a custom equality and hash here to make it easier to unload components?
class Component(abc.Component):
    """Standard implementation of `tanjun.abc.Component`.

    This is a collcetion of commands (both message and slash), hooks and listener
    callbacks which can be added to a generic client.

    .. note::
        This implementation supports dependency injection for its checks,
        command callbacks and listeners when linked to a client which
        supports dependency injection.

    Parameters
    ----------
    checks : typing.Optional[collections.abc.Iterable[abc.CheckSig]]
        Iterable of check callbacks to set for this component, if provided.
    hooks : typing.Optional[tanjun.abc.AnyHooks]
        The hooks this component should add to the execution of all its
        commands (message and slash).
    slash_hooks : typing.Optional[tanjun.abc.SlashHooks]
        The slash hooks this component should add to the execution of its
        slash commands.
    message_hooks : typing.Optional[tanjun.abc.MessageHooks]
        The message hooks this component should add to the execution of its
        message commands.
    name : str
        The component's identifier.

        If not provided then this will be a random string.
    strict : bool
        Whether this component should use a stricter (more optimal) approach
        for message command search.

        When this is `True`, message command names will not be allowed to contain
        spaces and will have to be unique to one command within the component.
    """

    __slots__ = (
        "_checks",
        "_client",
        "_client_callbacks",
        "_defaults_to_ephemeral",
        "_hooks",
        "_is_strict",
        "_listeners",
        "_loop",
        "_message_commands",
        "_message_hooks",
        "_metadata",
        "_name",
        "_names_to_commands",
        "_on_close",
        "_on_open",
        "_slash_commands",
        "_slash_hooks",
    )

    def __init__(
        self,
        *,
        checks: typing.Optional[collections.Iterable[abc.CheckSig]] = None,
        hooks: typing.Optional[abc.AnyHooks] = None,
        slash_hooks: typing.Optional[abc.SlashHooks] = None,
        message_hooks: typing.Optional[abc.MessageHooks] = None,
        name: typing.Optional[str] = None,
        strict: bool = False,
        load_from_attributes: bool = False,
    ) -> None:
        self._checks: list[checks_.InjectableCheck] = (
            [checks_.InjectableCheck(check) for check in dict.fromkeys(checks)] if checks else []
        )
        self._client: typing.Optional[abc.Client] = None
        self._client_callbacks: dict[str, list[abc.MetaEventSig]] = {}
        self._defaults_to_ephemeral: typing.Optional[bool] = None
        self._hooks = hooks
        self._is_strict = strict
        self._listeners: dict[type[base_events.Event], list[abc.ListenerCallbackSig]] = {}
        self._loop: typing.Optional[asyncio.AbstractEventLoop] = None
        self._message_commands: list[abc.MessageCommand] = []
        self._message_hooks = message_hooks
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._name = name or base64.b64encode(random.randbytes(32)).decode()
        self._names_to_commands: dict[str, abc.MessageCommand] = {}
        self._on_close: list[injecting.CallbackDescriptor[None]] = []
        self._on_open: list[injecting.CallbackDescriptor[None]] = []
        self._slash_commands: dict[str, abc.BaseSlashCommand] = {}
        self._slash_hooks = slash_hooks

        if load_from_attributes and type(self) is not Component:  # No need to run this on the base class.
            self._load_from_properties()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.checks=}, {self.hooks=}, {self.slash_hooks=}, {self.message_hooks=})"

    @property
    def checks(self) -> collections.Collection[abc.CheckSig]:
        """Collection of the checks being run against every command execution in this component."""
        return tuple(check.callback for check in self._checks)

    @property
    def client(self) -> typing.Optional[abc.Client]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._client

    @property
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._defaults_to_ephemeral

    @property
    def hooks(self) -> typing.Optional[abc.AnyHooks]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._hooks

    @property
    def loop(self) -> typing.Optional[asyncio.AbstractEventLoop]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._loop

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._name

    @property
    def slash_commands(self) -> collections.Collection[abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._slash_commands.copy().values()

    @property
    def slash_hooks(self) -> typing.Optional[abc.SlashHooks]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._slash_hooks

    @property
    def message_commands(self) -> collections.Collection[abc.MessageCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._message_commands.copy()

    @property
    def message_hooks(self) -> typing.Optional[abc.MessageHooks]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._message_hooks

    @property
    def needs_injector(self) -> bool:
        """Whether any of the checks in this component require dependency injection."""
        return any(check.needs_injector for check in self._checks)

    @property
    def listeners(
        self,
    ) -> collections.Mapping[type[base_events.Event], collections.Collection[abc.ListenerCallbackSig]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return utilities.CastedView(self._listeners, lambda x: x.copy())

    @property
    def metadata(self) -> dict[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._metadata

    def copy(self: _ComponentT, *, _new: bool = True) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not _new:
            self._checks = [check.copy() for check in self._checks]
            self._slash_commands = {name: command.copy() for name, command in self._slash_commands.items()}
            self._hooks = self._hooks.copy() if self._hooks else None
            self._listeners = {
                event: [copy.copy(listener) for listener in listeners] for event, listeners in self._listeners.items()
            }
            commands = {command: command.copy() for command in self._message_commands}
            self._message_commands = list(commands.values())
            self._metadata = self._metadata.copy()
            self._names_to_commands = {name: commands[command] for name, command in self._names_to_commands.items()}
            return self

        return copy.copy(self).copy(_new=False)

    @typing.overload
    def detect_commands(
        self: _ComponentT, *, scope: typing.Optional[collections.Mapping[str, typing.Any]] = None
    ) -> _ComponentT:
        ...

    @typing.overload
    def detect_commands(self: _ComponentT, *, include_globals: bool = False) -> _ComponentT:
        ...

    def detect_commands(
        self: _ComponentT,
        *,
        include_globals: bool = False,
        scope: typing.Optional[collections.Mapping[str, typing.Any]] = None,
    ) -> _ComponentT:
        """Load top-level commands into the component from the calling scope.

        Notes
        -----
        * This will ignore commands which are owned by command groups.
        * This will detect commands from the calling scope unless `scope` is
          passed but this isn't possible in a stack-less python implementation;
          in stack-less environments the scope will have to be explicitly
          passed as `scope`.

        Other Parameters
        ----------------
        include_globals: bool
            Whether to include global variables (along with local) while
            detecting from the calling scope.

            This defaults to `False`, cannot be `True` when `scope` is provided
            and will only ever be needed when the local scope is different
            from the global scope.
        scope : typing.Optional[collections.Mapping[str, typing.Any]]
            The scope to detect commands from.

            This overrides the default usage of stackframe introspection.

        Returns
        -------
        Self
            The current component to allow for chaining.

        Raises
        ------
        RuntimeError
            If this is called in a python implementation which doesn't support
            stack frame inspection when `scope` is not provided.
        ValueError
            If `scope` is provided when `include_globals` is True.
        """
        if scope is None:
            if not (stack := inspect.currentframe()) or not stack.f_back:
                raise RuntimeError(
                    "Stackframe introspection is not supported in this runtime. Please explicitly pass `scope`."
                )

            values_iter = _filter_scope(stack.f_back.f_locals)
            if include_globals:
                values_iter = itertools.chain(values_iter, _filter_scope(stack.f_back.f_globals))

        elif include_globals:
            raise ValueError("Cannot specify include_globals as True when scope is passed")

        else:
            values_iter = _filter_scope(scope)

        _LOGGER.info(
            "Loading commands for %s component from %s parent scope(s)",
            self.name,
            "global and local" if include_globals else "local",
        )
        for value in values_iter:
            if isinstance(value, abc.BaseSlashCommand) and not value.parent:
                self.add_slash_command(value)
            elif isinstance(value, abc.MessageCommand) and not value.parent:
                self.add_message_command(value)

        return self

    # def into_loader()

    def set_ephemeral_default(self: _ComponentT, state: typing.Optional[bool], /) -> _ComponentT:
        """Set whether slash contexts executed in this component should default to ephemeral responses.

        Parameters
        ----------
        typing.Optional[bool]
            Whether slash command contexts executed in this component should
            should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to `None` will let the default set on the parent
            client propagate and decide the ephemeral default behaviour.

        Returns
        -------
        SelfT
            This component to enable method chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_slash_hooks(self: _ComponentT, hooks_: typing.Optional[abc.SlashHooks], /) -> _ComponentT:
        self._slash_hooks = hooks_
        return self

    def set_message_hooks(self: _ComponentT, hooks_: typing.Optional[abc.MessageHooks], /) -> _ComponentT:
        self._message_hooks = hooks_
        return self

    def set_hooks(self: _ComponentT, hooks: typing.Optional[abc.AnyHooks], /) -> _ComponentT:
        self._hooks = hooks
        return self

    def add_check(self: _ComponentT, check: abc.CheckSig, /) -> _ComponentT:
        if check not in self._checks:
            self._checks.append(checks_.InjectableCheck(check))

        return self

    def remove_check(self: _ComponentT, check: abc.CheckSig, /) -> _ComponentT:
        self._checks.remove(typing.cast("checks_.InjectableCheck", check))
        return self

    def with_check(self, check: abc.CheckSigT, /) -> abc.CheckSigT:
        self.add_check(check)
        return check

    def add_client_callback(self: _ComponentT, event_name: str, callback: abc.MetaEventSig, /) -> _ComponentT:
        event_name = event_name.lower()
        try:
            if callback in self._client_callbacks[event_name]:
                return self

            self._client_callbacks[event_name].append(callback)
        except KeyError:
            self._client_callbacks[event_name] = [callback]

        if self._client:
            self._client.add_client_callback(event_name, callback)

        return self

    def get_client_callbacks(self, event_name: str, /) -> collections.Collection[abc.MetaEventSig]:
        event_name = event_name.lower()
        return self._client_callbacks.get(event_name) or ()

    def remove_client_callback(self, event_name: str, callback: abc.MetaEventSig, /) -> None:
        event_name = event_name.lower()
        self._client_callbacks[event_name].remove(callback)
        if not self._client_callbacks[event_name]:
            del self._client_callbacks[event_name]

        if self._client:
            self._client.remove_client_callback(event_name, callback)

    def with_client_callback(self, event_name: str, /) -> collections.Callable[[abc.MetaEventSigT], abc.MetaEventSigT]:
        def decorator(callback: abc.MetaEventSigT, /) -> abc.MetaEventSigT:
            self.add_client_callback(event_name, callback)
            return callback

        return decorator

    def add_command(self: _ComponentT, command: abc.ExecutableCommand[typing.Any], /) -> _ComponentT:
        """Add a command to this component.

        Parameters
        ----------
        command : tanjun.abc.ExecutableCommand[typing.Any]
            The command to add.

        Returns
        -------
        Self
            The current component to allow for chaining.
        """
        if isinstance(command, abc.MessageCommand):
            self.add_message_command(command)

        elif isinstance(command, abc.BaseSlashCommand):
            self.add_slash_command(command)

        else:
            raise ValueError(
                f"Unexpected object passed, expected a MessageCommand or BaseSlashCommand but got {type(command)}"
            )

        return self

    def remove_command(self: _ComponentT, command: abc.ExecutableCommand[typing.Any], /) -> _ComponentT:
        """Remove a command from this component.

        Parameters
        ----------
        command : tanjun.abc.ExecutableCommand[typing.Any]
            The command to remove.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        if isinstance(command, abc.MessageCommand):
            self.remove_message_command(command)

        elif isinstance(command, abc.BaseSlashCommand):
            self.remove_slash_command(command)

        else:
            raise ValueError(
                f"Unexpected object passed, expected a MessageCommand or BaseSlashCommand but got {type(command)}"
            )

        return self

    @typing.overload
    def with_command(self, command: CommandT, /) -> CommandT:
        ...

    @typing.overload
    def with_command(self, *, copy: bool = False) -> collections.Callable[[CommandT], CommandT]:
        ...

    def with_command(
        self, command: typing.Optional[CommandT] = None, /, *, copy: bool = False
    ) -> WithCommandReturnSig[CommandT]:
        """Add a command to this component through a decorator call.

        Parameters
        ----------
        command CommandT
            The command to add to this component.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it to this component.

        Returns
        -------
        CommandT
            The added command.
        """
        return _with_command(self.add_command, command, copy=copy)

    def add_slash_command(self: _ComponentT, command: abc.BaseSlashCommand, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._slash_commands.get(command.name) == command:
            return self

        command.bind_component(self)

        if self._client:
            command.bind_client(self._client)

        self._slash_commands[command.name.casefold()] = command
        return self

    def remove_slash_command(self: _ComponentT, command: abc.BaseSlashCommand, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        try:
            del self._slash_commands[command.name.casefold()]
        except KeyError:
            raise ValueError(f"Command {command.name} not found") from None

        return self

    @typing.overload
    def with_slash_command(self, command: abc.BaseSlashCommandT, /) -> abc.BaseSlashCommandT:
        ...

    @typing.overload
    def with_slash_command(
        self, *, copy: bool = False
    ) -> collections.Callable[[abc.BaseSlashCommandT], abc.BaseSlashCommandT]:
        ...

    def with_slash_command(
        self, command: typing.Optional[abc.BaseSlashCommandT] = None, /, *, copy: bool = False
    ) -> WithCommandReturnSig[abc.BaseSlashCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_slash_command, command, copy=copy)

    def add_message_command(self: _ComponentT, command: abc.MessageCommand, /) -> _ComponentT:
        """Add a message command to the component.

        Parameters
        ----------
        command : tanjun.abc.MessageCommand
            The command to add.

        Returns
        -------
        Self
            The component to allow method chaining.

        Raises
        ------
        ValueError
            If one of the command's name is already registered in a strict
            component.
        """
        if command in self._message_commands:
            return self

        if self._is_strict:
            if any(" " in name for name in command.names):
                raise ValueError("Command name cannot contain spaces for this component implementation")

            if name_conflicts := self._names_to_commands.keys() & command.names:
                raise ValueError(
                    "Sub-command names must be unique in a strict component. "
                    "The following conflicts were found " + ", ".join(name_conflicts)
                )

            self._names_to_commands.update((name, command) for name in command.names)

        self._message_commands.append(command)

        if self._client:
            command.bind_client(self._client)

        command.bind_component(self)
        return self

    def remove_message_command(self: _ComponentT, command: abc.MessageCommand, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._message_commands.remove(command)

        if self._is_strict:
            for name in command.names:
                if self._names_to_commands.get(name) == command:
                    del self._names_to_commands[name]

        return self

    @typing.overload
    def with_message_command(self, command: abc.MessageCommandT, /) -> abc.MessageCommandT:
        ...

    @typing.overload
    def with_message_command(
        self, *, copy: bool = False
    ) -> collections.Callable[[abc.MessageCommandT], abc.MessageCommandT]:
        ...

    def with_message_command(
        self, command: typing.Optional[abc.MessageCommandT] = None, /, *, copy: bool = False
    ) -> WithCommandReturnSig[abc.MessageCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_message_command, command, copy=copy)

    def add_listener(
        self: _ComponentT, event: type[base_events.Event], listener: abc.ListenerCallbackSig, /
    ) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        try:
            if listener in self._listeners[event]:
                return self

            self._listeners[event].append(listener)

        except KeyError:
            self._listeners[event] = [listener]

        if self._client:
            self._client.add_listener(event, listener)

        return self

    def remove_listener(
        self: _ComponentT, event: type[base_events.Event], listener: abc.ListenerCallbackSig, /
    ) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._listeners[event].remove(listener)
        if not self._listeners[event]:
            del self._listeners[event]

        if self._client:
            self._client.remove_listener(event, listener)

        return self

    # TODO: make event optional?
    def with_listener(
        self, event_type: type[base_events.Event]
    ) -> collections.Callable[[abc.ListenerCallbackSigT], abc.ListenerCallbackSigT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        def decorator(callback: abc.ListenerCallbackSigT) -> abc.ListenerCallbackSigT:
            self.add_listener(event_type, callback)
            return callback

        return decorator

    def add_on_close(self: _ComponentT, callback: OnCallbackSig, /) -> _ComponentT:
        """Add a close callback to this component.

        .. note::
            Unlike the closing and closed client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        callback : OnCallbackSig
            The close callback to add to this component.

            This should take no positional arguments, return `None` and may
            take use injected dependencies.

        Returns
        -------
        Self
            The component object to enable call chaining.
        """
        self._on_close.append(injecting.CallbackDescriptor(callback))
        return self

    def with_on_close(self, callback: OnCallbackSigT, /) -> OnCallbackSigT:
        """Add a close callback to this component through a decorator call.

        .. note::
            Unlike the closing and closed client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        callback : OnCallbackSig
            The close callback to add to this component.

            This should take no positional arguments, return `None` and may
            take use injected dependencies.

        Returns
        -------
        OnCallbackSig
            The added close callback.
        """
        self.add_on_close(callback)
        return callback

    def add_on_open(self: _ComponentT, callback: OnCallbackSig, /) -> _ComponentT:
        """Add a open callback to this component.

        .. note::
            Unlike the starting and started client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        callback : OnCallbackSig
            The open callback to add to this component.

            This should take no positional arguments, return `None` and may
            take use injected dependencies.

        Returns
        -------
        Self
            The component object to enable call chaining.
        """
        self._on_open.append(injecting.CallbackDescriptor(callback))
        return self

    def with_on_open(self, callback: OnCallbackSigT, /) -> OnCallbackSigT:
        """Add a open callback to this component through a decorator call.

        .. note::
            Unlike the starting and started client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        callback : OnCallbackSig
            The open callback to add to this component.

            This should take no positional arguments, return `None` and may
            take use injected dependencies.

        Returns
        -------
        OnCallbackSig
            The added open callback.
        """
        self.add_on_open(callback)
        return callback

    def bind_client(self: _ComponentT, client: abc.Client, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._client:
            raise RuntimeError("Client already set")

        self._client = client
        for message_command in self._message_commands:
            message_command.bind_client(client)

        for slash_command in self._slash_commands.values():
            slash_command.bind_client(client)

        for event, listeners in self._listeners.items():
            for listener in listeners:
                self._client.add_listener(event, listener)

        for event_name, callbacks in self._client_callbacks.items():
            for callback in callbacks:
                self._client.add_client_callback(event_name, callback)

        return self

    def unbind_client(self, client: abc.Client, /) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not self._client or self._client != client:
            raise RuntimeError("Component isn't bound to this client")

        for event, listeners in self._listeners.items():
            for listener in listeners:
                try:
                    self._client.remove_listener(event, listener)
                except (LookupError, ValueError):
                    pass

        for event_name, callbacks in self._client_callbacks.items():
            for callback in callbacks:
                try:
                    self._client.remove_client_callback(event_name, callback)
                except (LookupError, ValueError):
                    pass

        self._client = None

    async def _check_context(self, ctx: abc.Context, /) -> bool:
        return await utilities.gather_checks(ctx, self._checks)

    async def _check_message_context(
        self, ctx: abc.MessageContext, /
    ) -> collections.AsyncIterator[tuple[str, abc.MessageCommand]]:
        ctx.set_component(self)

        if self._is_strict:
            name = ctx.content.split(" ", 1)[0]
            command = self._names_to_commands.get(name)
            if command and await self._check_context(ctx) and await command.check_context(ctx):
                yield name, command

            else:
                ctx.set_component(None)

            return

        checks_run = False
        for name, command in self.check_message_name(ctx.content):
            if not checks_run:
                if not await self._check_context(ctx):
                    return

                checks_run = True

            if await command.check_context(ctx):
                yield name, command

        ctx.set_component(None)

    def check_message_name(self, content: str, /) -> collections.Iterator[tuple[str, abc.MessageCommand]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._is_strict:
            name = content.split(" ", 1)[0]
            if command := self._names_to_commands.get(name):
                yield name, command
            return

        for command in self._message_commands:
            if (name := utilities.match_prefix_names(content, command.names)) is not None:
                yield name, command
                # Don't want to match a command multiple times
                continue

    def check_slash_name(self, name: str, /) -> collections.Iterator[abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        if command := self._slash_commands.get(name):
            yield command

    async def _execute_interaction(
        self,
        ctx: abc.SlashContext,
        command: typing.Optional[abc.BaseSlashCommand],
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.SlashHooks]] = None,
    ) -> typing.Optional[collections.Awaitable[None]]:
        try:
            if not command or not await self._check_context(ctx) or not await command.check_context(ctx):
                return None

        except errors.HaltExecution:
            return asyncio.get_running_loop().create_task(ctx.mark_not_found())

        except errors.CommandError as exc:
            await ctx.respond(exc.message)
            return asyncio.get_running_loop().create_future().set_result(None)

        if self._slash_hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._slash_hooks)

        if self._hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._hooks)

        return asyncio.get_running_loop().create_task(command.execute(ctx, hooks=hooks))

    # To ensure that ctx.set_ephemeral_default is called as soon as possible if
    # a match is found the public function is kept sync to avoid yielding
    # to the event loop until after this is set.
    def execute_interaction(
        self,
        ctx: abc.SlashContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.SlashHooks]] = None,
    ) -> collections.Coroutine[typing.Any, typing.Any, typing.Optional[collections.Awaitable[None]]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        command = self._slash_commands.get(ctx.interaction.command_name)
        if command:
            if command.defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(command.defaults_to_ephemeral)

            elif self._defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(self._defaults_to_ephemeral)

        return self._execute_interaction(ctx, command, hooks=hooks)

    async def execute_message(
        self,
        ctx: abc.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.MessageHooks]] = None,
    ) -> bool:
        # <<inherited docstring from tanjun.abc.Component>>.
        async for name, command in self._check_message_context(ctx):
            ctx.set_triggering_name(name)
            ctx.set_content(ctx.content[len(name) :].lstrip())
            ctx.set_component(self)
            # Only add our hooks if we're sure we'll be executing the command here.

            if self._message_hooks:
                if hooks is None:
                    hooks = set()

                hooks.add(self._message_hooks)

            if self._hooks:
                if hooks is None:
                    hooks = set()

                hooks.add(self._hooks)

            await command.execute(ctx, hooks=hooks)
            return True

        ctx.set_component(None)
        return False

    def _load_from_properties(self) -> None:
        for name, member in inspect.getmembers(self):
            if isinstance(member, LoadableProtocol):
                if result := member.copy().load_into_component(self):
                    setattr(self, name, result)

    async def close(self) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not self._loop:
            raise RuntimeError("Component isn't active")

        assert self._client

        self._loop = None
        if isinstance(self._client, injecting.InjectorClient):
            await asyncio.gather(
                *(callback.resolve(injecting.BasicInjectionContext(self._client)) for callback in self._on_close)
            )

        else:
            await asyncio.gather(*(callback.resolve_without_injector() for callback in self._on_close))

    async def open(self) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._loop:
            raise RuntimeError("Component is already active")

        if not self._client:
            raise RuntimeError("Client isn't bound yet")

        self._loop = asyncio.get_running_loop()
        if isinstance(self._client, injecting.InjectorClient):
            await asyncio.gather(
                *(callback.resolve(injecting.BasicInjectionContext(self._client)) for callback in self._on_open)
            )

        else:
            await asyncio.gather(*(callback.resolve_without_injector() for callback in self._on_open))

    def make_loader(self, *, copy: bool = True) -> abc.AbstractLoader:
        """Make a loader/unloader for this component.

        This enables loading, unloading and reloading of this component into a
        client by targeting the module using `tanjun.Client.load_modules`,
        `tanjun.Client.unload_modules` and `tanjun.Client.reload_modules`.

        Other Parameters
        ----------------
        copy: bool
            Whether to copy the component before loading it into a client.

            Defaults to `True`.

        Returns
        -------
        tanjun.abc.AbstractLoader
            The loader for this component.
        """
        return _ComponentManager(self, copy)
