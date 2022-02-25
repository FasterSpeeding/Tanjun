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
"""Standard implementation of Tanjun's "components" used to manage separate features within a client."""
from __future__ import annotations

__all__: list[str] = ["AbstractComponentLoader", "Component", "OnCallbackSig"]

import abc
import asyncio
import base64
import copy
import inspect
import itertools
import logging
import random
import typing
from collections import abc as collections

from . import abc as tanjun_abc
from . import utilities

if typing.TYPE_CHECKING:
    import hikari

    from . import schedules

    _AppCommandContextT = typing.TypeVar("_AppCommandContextT", bound=tanjun_abc.AppCommandContext)
    _BaseSlashCommandT = typing.TypeVar("_BaseSlashCommandT", bound=tanjun_abc.BaseSlashCommand)
    _CheckSigT = typing.TypeVar("_CheckSigT", bound=tanjun_abc.CheckSig)
    _ComponentT = typing.TypeVar("_ComponentT", bound="Component")
    _ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound=tanjun_abc.ListenerCallbackSig)
    _MenuCommandT = typing.TypeVar("_MenuCommandT", bound=tanjun_abc.MenuCommand[typing.Any, typing.Any])
    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound=tanjun_abc.MessageCommand[typing.Any])
    _MetaEventSigT = typing.TypeVar("_MetaEventSigT", bound=tanjun_abc.MetaEventSig)
    _OnCallbackSigT = typing.TypeVar("_OnCallbackSigT", bound="OnCallbackSig")
    _ScheduleT = typing.TypeVar("_ScheduleT", bound=schedules.AbstractSchedule)


_LOGGER = logging.getLogger("hikari.tanjun.components")
_CommandT = typing.TypeVar("_CommandT", bound="tanjun_abc.ExecutableCommand[typing.Any]")
# This errors on earlier 3.9 releases when not quotes cause dumb handling of the [_CommandT] list
_WithCommandReturnSig = typing.Union[_CommandT, "collections.Callable[[_CommandT], _CommandT]"]

OnCallbackSig = typing.Union[
    collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]], collections.Callable[..., None]
]
"""Type hint of a on_open or on_close component callback.

These support dependency injection, should expect no positional arguments and
should return `None`.
"""


class AbstractComponentLoader(abc.ABC):
    """Abstract interface used for loading utility into a standard `Component`."""

    __slots__ = ()

    @abc.abstractmethod
    def load_into_component(self, component: tanjun_abc.Component, /) -> None:
        """Load the object into the component.

        Parameters
        ----------
        component : tanjun.abc.Component
            The component this object should be loaded into.
        """


def _with_command(
    add_command: collections.Callable[[_CommandT], Component],
    maybe_command: typing.Optional[_CommandT],
    /,
    *,
    copy: bool = False,
) -> _WithCommandReturnSig[_CommandT]:
    if maybe_command:
        maybe_command = maybe_command.copy() if copy else maybe_command
        add_command(maybe_command)
        return maybe_command

    def decorator(command: _CommandT, /) -> _CommandT:
        command = command.copy() if copy else command
        add_command(command)
        return command

    return decorator


def _filter_scope(scope: collections.Mapping[str, typing.Any]) -> collections.Iterator[typing.Any]:
    return (value for key, value in scope.items() if not key.startswith("_"))


class _ComponentManager(tanjun_abc.ClientLoader):
    __slots__ = ("_component", "_copy")

    def __init__(self, component: Component, copy: bool) -> None:
        self._component = component
        self._copy = copy

    @property
    def has_load(self) -> bool:
        return True

    @property
    def has_unload(self) -> bool:
        return True

    def load(self, client: tanjun_abc.Client, /) -> bool:
        client.add_component(self._component.copy() if self._copy else self._component)
        return True

    def unload(self, client: tanjun_abc.Client, /) -> bool:
        client.remove_component_by_name(self._component.name)
        return True


# TODO: do we want to setup a custom equality and hash here to make it easier to unload components?
class Component(tanjun_abc.Component):
    """Standard implementation of `tanjun.abc.Component`.

    This is a collcetion of commands (both message and slash), hooks and listener
    callbacks which can be added to a generic client.

    .. note::
        This implementation supports dependency injection for its checks,
        command callbacks and listeners when linked to a client which
        supports dependency injection.
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
        "_menu_commands",
        "_menu_hooks",
        "_message_commands",
        "_message_hooks",
        "_metadata",
        "_name",
        "_names_to_commands",
        "_on_close",
        "_on_open",
        "_schedules",
        "_slash_commands",
        "_slash_hooks",
    )

    def __init__(self, *, name: typing.Optional[str] = None, strict: bool = False) -> None:
        """Initialise a new component.

        Other Parameters
        ----------------
        name : str
            The component's identifier.

            If not provided then this will be a random string.
        strict : bool
            Whether this component should use a stricter (more optimal) approach
            for message command search.

            When this is `True`, message command names will not be allowed to contain
            spaces and will have to be unique to one command within the component.
        """
        self._checks: list[tanjun_abc.CheckSig] = []
        self._client: typing.Optional[tanjun_abc.Client] = None
        self._client_callbacks: dict[str, list[tanjun_abc.MetaEventSig]] = {}
        self._defaults_to_ephemeral: typing.Optional[bool] = None
        self._hooks: typing.Optional[tanjun_abc.AnyHooks] = None
        self._is_strict = strict
        self._listeners: dict[type[hikari.Event], list[tanjun_abc.ListenerCallbackSig]] = {}
        self._loop: typing.Optional[asyncio.AbstractEventLoop] = None
        self._menu_commands: dict[tuple[hikari.CommandType, str], tanjun_abc.MenuCommand[typing.Any, typing.Any]] = {}
        self._menu_hooks: typing.Optional[tanjun_abc.MenuHooks] = None
        self._message_commands: list[tanjun_abc.MessageCommand[typing.Any]] = []
        self._message_hooks: typing.Optional[tanjun_abc.MessageHooks] = None
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._name = name or base64.b64encode(random.randbytes(32)).decode()
        self._names_to_commands: dict[str, tanjun_abc.MessageCommand[typing.Any]] = {}
        self._on_close: list[OnCallbackSig] = []
        self._on_open: list[OnCallbackSig] = []
        self._schedules: list[schedules.AbstractSchedule] = []
        self._slash_commands: dict[str, tanjun_abc.BaseSlashCommand] = {}
        self._slash_hooks: typing.Optional[tanjun_abc.SlashHooks] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.checks=}, {self.hooks=}, {self.slash_hooks=}, {self.message_hooks=})"

    @property
    def checks(self) -> collections.Collection[tanjun_abc.CheckSig]:
        """Collection of the checks being run against every command execution in this component."""
        return self._checks.copy()

    @property
    def client(self) -> typing.Optional[tanjun_abc.Client]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._client

    @property
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._defaults_to_ephemeral

    @property
    def hooks(self) -> typing.Optional[tanjun_abc.AnyHooks]:
        """The general command hooks set for this component, if any."""
        return self._hooks

    @property
    def menu_hooks(self) -> typing.Optional[tanjun_abc.MenuHooks]:
        """The menu command hooks set for this component, if any."""
        return self._menu_hooks

    @property
    def message_hooks(self) -> typing.Optional[tanjun_abc.MessageHooks]:
        """The message command hooks set for this component, if any."""
        return self._message_hooks

    @property
    def slash_hooks(self) -> typing.Optional[tanjun_abc.SlashHooks]:
        """The slash command hooks set for this component, if any."""
        return self._slash_hooks

    @property
    def loop(self) -> typing.Optional[asyncio.AbstractEventLoop]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._loop

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._name

    @property
    def schedules(self) -> collections.Collection[schedules.AbstractSchedule]:
        """Collection of the schedules registered to this component."""
        return self._schedules

    @property
    def slash_commands(self) -> collections.Collection[tanjun_abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._slash_commands.copy().values()

    @property
    def menu_commands(self) -> collections.Collection[tanjun_abc.MenuCommand[typing.Any, typing.Any]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._menu_commands.copy().values()

    @property
    def message_commands(self) -> collections.Collection[tanjun_abc.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._message_commands.copy()

    @property
    def listeners(
        self,
    ) -> collections.Mapping[type[hikari.Event], collections.Collection[tanjun_abc.ListenerCallbackSig]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return utilities.CastedView(self._listeners, lambda x: x.copy())

    @property
    def metadata(self) -> dict[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._metadata

    def copy(self: _ComponentT, *, _new: bool = True) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not _new:
            self._checks = [copy.copy(check) for check in self._checks]
            self._slash_commands = {name: command.copy() for name, command in self._slash_commands.items()}
            self._hooks = self._hooks.copy() if self._hooks else None
            self._listeners = {
                event: [copy.copy(listener) for listener in listeners] for event, listeners in self._listeners.items()
            }
            commands = {command: command.copy() for command in self._message_commands}
            self._message_commands = list(commands.values())
            self._metadata = self._metadata.copy()
            self._names_to_commands = {name: commands[command] for name, command in self._names_to_commands.items()}
            self._schedules = [schedule.copy() for schedule in self._schedules] if self._schedules else []
            return self

        return copy.copy(self).copy(_new=False)

    @typing.overload
    def load_from_scope(
        self: _ComponentT, *, scope: typing.Optional[collections.Mapping[str, typing.Any]] = None
    ) -> _ComponentT:
        ...

    @typing.overload
    def load_from_scope(self: _ComponentT, *, include_globals: bool = False) -> _ComponentT:
        ...

    def load_from_scope(
        self: _ComponentT,
        *,
        include_globals: bool = False,
        scope: typing.Optional[collections.Mapping[str, typing.Any]] = None,
    ) -> _ComponentT:
        """Load entries such as top-level commands into the component from the calling scope.

        Notes
        -----
        * This will load schedules which support `AbstractComponentLoader`
          (e.g. `tanjun.schedules.IntervalSchedule`).
        * This will ignore commands which are owned by command groups.
        * This will detect entries from the calling scope which implement
          `AbstractComponentLoader` unless `scope` is passed but this isn't possible
          in a stack-less python implementation; in stack-less environments the
          scope will have to be explicitly passed as `scope`.

        Other Parameters
        ----------------
        include_globals: bool
            Whether to include global variables (along with local) while
            detecting from the calling scope.

            This defaults to `False`, cannot be `True` when `scope` is provided
            and will only ever be needed when the local scope is different
            from the global scope.
        scope : collections.Mapping[str, typing.Any] | None
            The scope to detect entries which implement `AbstractComponentLoader`
            from.

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
            if isinstance(value, AbstractComponentLoader):
                value.load_into_component(self)

        return self

    def set_ephemeral_default(self: _ComponentT, state: typing.Optional[bool], /) -> _ComponentT:
        """Set whether slash contexts executed in this component should default to ephemeral responses.

        Parameters
        ----------
        bool | None
            Whether slash command contexts executed in this component should
            should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to `None` will let the default set on the parent
            client propagate and decide the ephemeral default behaviour.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_metadata(self: _ComponentT, key: typing.Any, value: typing.Any, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._metadata[key] = value
        return self

    def set_hooks(self: _ComponentT, hooks: typing.Optional[tanjun_abc.AnyHooks], /) -> _ComponentT:
        """Set hooks to be called during the execution of all of this component's commands.

        Parameters
        ----------
        hooks : tanjun.abc.AnyHooks | None
            The command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._hooks = hooks
        return self

    def set_menu_hooks(self: _ComponentT, hooks_: typing.Optional[tanjun_abc.MenuHooks], /) -> _ComponentT:
        """Set hooks to be called during the execution of this component's menu commands.

        Parameters
        ----------
        hooks : tanjun.abc.MenuHooks | None
            The menu command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._menu_hooks = hooks_
        return self

    def set_message_hooks(self: _ComponentT, hooks_: typing.Optional[tanjun_abc.MessageHooks], /) -> _ComponentT:
        """Set hooks to be called during the execution of this component's message commands.

        Parameters
        ----------
        hooks : tanjun.abc.MessageHooks | None
            The message command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._message_hooks = hooks_
        return self

    def set_slash_hooks(self: _ComponentT, hooks_: typing.Optional[tanjun_abc.SlashHooks], /) -> _ComponentT:
        """Set hooks to be called during the execution of this component's slash commands.

        Parameters
        ----------
        hooks : tanjun.abc.SlashHooks | None
            The slash command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._slash_hooks = hooks_
        return self

    def add_check(self: _ComponentT, check: tanjun_abc.CheckSig, /) -> _ComponentT:
        """Add a command check to this component to be used for all its commands.

        Parameters
        ----------
        tanjun.abc.CheckSig
            The check to add.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        if check not in self._checks:
            self._checks.append(check)

        return self

    def remove_check(self: _ComponentT, check: tanjun_abc.CheckSig, /) -> _ComponentT:
        """Remove a command check from this component.

        Parameters
        ----------
        check : tanjun.abc.CheckSig
            The check to remove.

        Returns
        -------
        Self
            This component to enable method chaining.

        Raises
        ------
        ValueError
            If the check is not registered with this component.
        """
        self._checks.remove(check)
        return self

    def with_check(self, check: _CheckSigT, /) -> _CheckSigT:
        """Add a general command check to this component through a decorator call.

        Parameters
        ----------
        check : tanjun.abc.CheckSig
            The check to add.

        Returns
        -------
        tanjun.abc.CheckSig
            The added check.
        """
        self.add_check(check)
        return check

    def add_client_callback(
        self: _ComponentT,
        event_name: typing.Union[str, tanjun_abc.ClientCallbackNames],
        callback: tanjun_abc.MetaEventSig,
        /,
    ) -> _ComponentT:
        """Add a client callback.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name this callback is being registered to.

            This is case-insensitive.
        callback : MetaEventSigT
            The callback to register.

            This may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
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

    def get_client_callbacks(
        self, event_name: typing.Union[str, tanjun_abc.ClientCallbackNames], /
    ) -> collections.Collection[tanjun_abc.MetaEventSig]:
        """Get a collection of the callbacks registered for a specific name.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name to get the callbacks registered for.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Collection[MetaEventSig]
            Collection of the callbacks for the provided name.
        """
        event_name = event_name.lower()
        return self._client_callbacks.get(event_name) or ()

    def remove_client_callback(self, event_name: str, callback: tanjun_abc.MetaEventSig, /) -> None:
        """Remove a client callback.

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name this callback is being registered to.

            This is case-insensitive.
        callback : MetaEventSigT
            The callback to remove from the client's callbacks.

        Raises
        ------
        KeyError
            If the provided name isn't found.
        ValueError
            If the provided callback isn't found.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        event_name = event_name.lower()
        self._client_callbacks[event_name].remove(callback)
        if not self._client_callbacks[event_name]:
            del self._client_callbacks[event_name]

        if self._client:
            self._client.remove_client_callback(event_name, callback)

    def with_client_callback(
        self, event_name: typing.Union[str, tanjun_abc.ClientCallbackNames], /
    ) -> collections.Callable[[_MetaEventSigT], _MetaEventSigT]:
        """Add a client callback through a decorator call.

        Examples
        --------
        ```py
        client = tanjun.Client.from_rest_bot(bot)

        @client.with_client_callback("closed")
        async def on_close() -> None:
            raise NotImplementedError
        ```

        Parameters
        ----------
        name : str | ClientCallbackNames
            The name this callback is being registered to.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Callable[[MetaEventSigT], MetaEventSigT]
            Decorator callback used to register the client callback.

            This may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.
        """

        def decorator(callback: _MetaEventSigT, /) -> _MetaEventSigT:
            self.add_client_callback(event_name, callback)
            return callback

        return decorator

    def add_command(self: _ComponentT, command: tanjun_abc.ExecutableCommand[typing.Any], /) -> _ComponentT:
        """Add a command to this component.

        Parameters
        ----------
        command : tanjun.abc.ExecutableCommand
            The command to add.

        Returns
        -------
        Self
            The current component to allow for chaining.
        """
        if isinstance(command, tanjun_abc.MessageCommand):
            self.add_message_command(command)

        elif isinstance(command, tanjun_abc.BaseSlashCommand):
            self.add_slash_command(command)

        elif isinstance(command, tanjun_abc.MenuCommand):
            self.add_menu_command(command)

        else:
            raise ValueError(
                "Unexpected object passed, expected a MenuCommand, "
                f"MessageCommand or BaseSlashCommand but got {type(command)}"
            )

        return self

    def remove_command(self: _ComponentT, command: tanjun_abc.ExecutableCommand[typing.Any], /) -> _ComponentT:
        """Remove a command from this component.

        Parameters
        ----------
        command : tanjun.abc.ExecutableCommand
            The command to remove.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        if isinstance(command, tanjun_abc.MessageCommand):
            self.remove_message_command(command)

        elif isinstance(command, tanjun_abc.BaseSlashCommand):
            self.remove_slash_command(command)

        else:
            raise ValueError(
                f"Unexpected object passed, expected a MessageCommand or BaseSlashCommand but got {type(command)}"
            )

        return self

    @typing.overload
    def with_command(self, command: _CommandT, /) -> _CommandT:
        ...

    @typing.overload
    def with_command(self, /, *, copy: bool = False) -> collections.Callable[[_CommandT], _CommandT]:
        ...

    def with_command(
        self, command: typing.Optional[_CommandT] = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_CommandT]:
        """Add a command to this component through a decorator call.

        Examples
        --------
        This may be used inconjunction with `tanjun.as_slash_command`
        and `tanjun.as_message_command`.

        ```py
        @component.with_command
        @tanjun.with_slash_str_option("option_name", "option description")
        @tanjun.as_slash_command("command_name", "command description")
        async def slash_command(ctx: tanjun.abc.Context, arg: str) -> None:
            await ctx.respond(f"Hi {arg}")
        ```

        ```py
        @component.with_command
        @tanjun.with_argument("argument_name")
        @tanjun.as_message_command("command_name")
        async def message_command(ctx: tanjun.abc.Context, arg: str) -> None:
            await ctx.respond(f"Hi {arg}")
        ```

        Parameters
        ----------
        command: tanjun.abc.ExecutableCommand
            The command to add to this component.

        Other Parameters
        ----------------
        copy : bool
            Whether to copy the command before adding it to this component.

        Returns
        -------
        tanjun.abc.ExecutableCommand
            The added command.
        """
        return _with_command(self.add_command, command, copy=copy)

    def add_menu_command(self: _ComponentT, command: tanjun_abc.MenuCommand[typing.Any, typing.Any], /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        key = (command.type, command.name)
        if self._menu_commands.get(key) == command:
            return self

        command.bind_component(self)

        if self._client:
            command.bind_client(self._client)

        self._menu_commands[key] = command
        return self

    def remove_menu_command(
        self: _ComponentT, command: tanjun_abc.MenuCommand[typing.Any, typing.Any], /
    ) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        try:
            del self._menu_commands[(command.type, command.name)]
        except KeyError:
            raise ValueError(f"Command {command.name} not found") from None

        return self

    @typing.overload
    def with_menu_command(self, command: _MenuCommandT, /) -> _MenuCommandT:
        ...

    @typing.overload
    def with_menu_command(self, /, *, copy: bool = False) -> collections.Callable[[_MenuCommandT], _MenuCommandT]:
        ...

    def with_menu_command(
        self, command: typing.Optional[_MenuCommandT] = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_MenuCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_menu_command, command, copy=copy)

    def add_slash_command(self: _ComponentT, command: tanjun_abc.BaseSlashCommand, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        name = command.name.casefold()
        if self._slash_commands.get(name) == command:
            return self

        command.bind_component(self)

        if self._client:
            command.bind_client(self._client)

        self._slash_commands[name] = command
        return self

    def remove_slash_command(self: _ComponentT, command: tanjun_abc.BaseSlashCommand, /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        try:
            del self._slash_commands[command.name.casefold()]
        except KeyError:
            raise ValueError(f"Command {command.name} not found") from None

        return self

    @typing.overload
    def with_slash_command(self, command: _BaseSlashCommandT, /) -> _BaseSlashCommandT:
        ...

    @typing.overload
    def with_slash_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_BaseSlashCommandT], _BaseSlashCommandT]:
        ...

    def with_slash_command(
        self, command: typing.Optional[_BaseSlashCommandT] = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_BaseSlashCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_slash_command, command, copy=copy)

    def add_message_command(self: _ComponentT, command: tanjun_abc.MessageCommand[typing.Any], /) -> _ComponentT:
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

    def remove_message_command(self: _ComponentT, command: tanjun_abc.MessageCommand[typing.Any], /) -> _ComponentT:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._message_commands.remove(command)

        if self._is_strict:
            for name in command.names:
                if self._names_to_commands.get(name) == command:
                    del self._names_to_commands[name]

        return self

    @typing.overload
    def with_message_command(self, command: _MessageCommandT, /) -> _MessageCommandT:
        ...

    @typing.overload
    def with_message_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_MessageCommandT], _MessageCommandT]:
        ...

    def with_message_command(
        self, command: typing.Optional[_MessageCommandT] = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_MessageCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_message_command, command, copy=copy)

    def add_listener(
        self: _ComponentT, event: type[hikari.Event], listener: tanjun_abc.ListenerCallbackSig, /
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
        self: _ComponentT, event: type[hikari.Event], listener: tanjun_abc.ListenerCallbackSig, /
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
        self, event_type: type[hikari.Event]
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        def decorator(callback: _ListenerCallbackSigT) -> _ListenerCallbackSigT:
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
        self._on_close.append(callback)
        return self

    def with_on_close(self, callback: _OnCallbackSigT, /) -> _OnCallbackSigT:
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
        self._on_open.append(callback)
        return self

    def with_on_open(self, callback: _OnCallbackSigT, /) -> _OnCallbackSigT:
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

    def bind_client(self: _ComponentT, client: tanjun_abc.Client, /) -> _ComponentT:
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

    def unbind_client(self: _ComponentT, client: tanjun_abc.Client, /) -> _ComponentT:
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

        return self

    async def _check_context(self, ctx: tanjun_abc.Context, /) -> bool:
        return await utilities.gather_checks(ctx, self._checks)

    async def _check_message_context(
        self, ctx: tanjun_abc.MessageContext, /
    ) -> collections.AsyncIterator[tuple[str, tanjun_abc.MessageCommand[typing.Any]]]:
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

    def check_message_name(
        self, content: str, /
    ) -> collections.Iterator[tuple[str, tanjun_abc.MessageCommand[typing.Any]]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._is_strict:
            name = content.split(" ", 1)[0]
            if command := self._names_to_commands.get(name):
                yield name, command
            return

        for command in self._message_commands:
            if (name_ := utilities.match_prefix_names(content, command.names)) is not None:
                yield name_, command

    def check_slash_name(self, name: str, /) -> collections.Iterator[tanjun_abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        if command := self._slash_commands.get(name):
            yield command

    def execute_autocomplete(
        self,
        ctx: tanjun_abc.AutocompleteContext,
        /,
    ) -> typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        if command := self._slash_commands.get(ctx.interaction.command_name):
            return command.execute_autocomplete(ctx)

    async def _execute_app(
        self,
        ctx: _AppCommandContextT,
        command: typing.Optional[tanjun_abc.AppCommand[_AppCommandContextT]],
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun_abc.Hooks[_AppCommandContextT]]] = None,
        other_hooks: typing.Optional[tanjun_abc.Hooks[_AppCommandContextT]] = None,
    ) -> typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]:
        if not command or not await self._check_context(ctx) or not await command.check_context(ctx):
            return None

        if self._hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._hooks)

        if other_hooks:
            if hooks is None:
                hooks = set()

            hooks.add(other_hooks)

        return command.execute(ctx, hooks=hooks)

    # To ensure that ctx.set_ephemeral_default is called as soon as possible if
    # a match is found the public function is kept sync to avoid yielding
    # to the event loop until after this is set.
    def execute_menu(
        self,
        ctx: tanjun_abc.MenuContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun_abc.MenuHooks]] = None,
    ) -> collections.Coroutine[
        typing.Any, typing.Any, typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]
    ]:
        # <<inherited docstring from tanjun.abc.Component>>.
        command = self._menu_commands.get((ctx.type, ctx.interaction.command_name))
        if command:
            if command.defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(command.defaults_to_ephemeral)

            elif self._defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(self._defaults_to_ephemeral)

        return self._execute_app(ctx, command, hooks=hooks, other_hooks=self._menu_hooks)

    # To ensure that ctx.set_ephemeral_default is called as soon as possible if
    # a match is found the public function is kept sync to avoid yielding
    # to the event loop until after this is set.
    def execute_slash(
        self,
        ctx: tanjun_abc.SlashContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun_abc.SlashHooks]] = None,
    ) -> collections.Coroutine[
        typing.Any, typing.Any, typing.Optional[collections.Coroutine[typing.Any, typing.Any, None]]
    ]:
        # <<inherited docstring from tanjun.abc.Component>>.
        command = self._slash_commands.get(ctx.interaction.command_name)
        if command:
            if command.defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(command.defaults_to_ephemeral)

            elif self._defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(self._defaults_to_ephemeral)

        return self._execute_app(ctx, command, hooks=hooks, other_hooks=self._slash_hooks)

    async def execute_message(
        self,
        ctx: tanjun_abc.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun_abc.MessageHooks]] = None,
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
        for _, member in inspect.getmembers(self):
            if isinstance(member, AbstractComponentLoader):
                member.load_into_component(self)

    def add_schedule(self: _ComponentT, schedule: schedules.AbstractSchedule, /) -> _ComponentT:
        """Add a schedule to the component.

        Parameters
        ----------
        schedule : tanjun.schedules.AbstractSchedule
            The schedule to add.

        Returns
        -------
        Self
            The component itself for chaining.
        """
        if self._client and self._loop:
            schedule.start(self._client.injector, loop=self._loop)

        self._schedules.append(schedule)
        return self

    def remove_schedule(self: _ComponentT, schedule: schedules.AbstractSchedule, /) -> _ComponentT:
        """Remove a schedule from the component.

        Parameters
        ----------
        schedule : tanjun.schedules.AbstractSchedule
            The schedule to remove

        Returns
        -------
        Self
            The component itself for chaining.

        Raises
        ------
        ValueError
            If the schedule isn't registered.
        """
        if schedule.is_alive:
            schedule.stop()

        self._schedules.remove(schedule)
        return self

    def with_schedule(self, schedule: _ScheduleT, /) -> _ScheduleT:
        """Add a schedule to the component through a decorator call.

        Example
        -------
        This may be used in conjunction with `tanjun.as_interval`.

        ```py
        @component.with_schedule
        @tanjun.as_interval(60)
        async def my_schedule():
            print("I'm running every minute!")
        ```

        Parameters
        ----------
        schedule : schedules.AbstractSchedule
            The schedule to add.

        Returns
        -------
        schedules.AbstractSchedule
            The added schedule.
        """
        self.add_schedule(schedule)
        return schedule

    async def close(self, *, unbind: bool = False) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not self._loop:
            raise RuntimeError("Component isn't active")

        assert self._client

        for schedule in self._schedules:
            if schedule.is_alive:
                schedule.stop()

        self._loop = None
        await asyncio.gather(*(self._client.injector.call_with_async_di(callback) for callback in self._on_close))
        if unbind:
            self.unbind_client(self._client)

    async def open(self) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._loop:
            raise RuntimeError("Component is already active")

        if not self._client:
            raise RuntimeError("Client isn't bound yet")

        self._loop = asyncio.get_running_loop()
        await asyncio.gather(*(self._client.injector.call_with_async_di(callback) for callback in self._on_open))

        for schedule in self._schedules:
            schedule.start(self._client.injector, loop=self._loop)

    def make_loader(self, *, copy: bool = True) -> tanjun_abc.ClientLoader:
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
        tanjun.abc.ClientLoader
            The loader for this component.
        """
        return _ComponentManager(self, copy)
