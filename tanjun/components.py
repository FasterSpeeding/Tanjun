# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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
import copy
import inspect
import itertools
import logging
import typing
import uuid
from collections import abc as collections

import hikari

from . import _internal
from . import abc as tanjun

if typing.TYPE_CHECKING:
    from typing import Self

    from . import schedules as schedules_

    _AppCommandContextT = typing.TypeVar("_AppCommandContextT", bound=tanjun.AppCommandContext)
    _BaseSlashCommandT = typing.TypeVar("_BaseSlashCommandT", bound=tanjun.BaseSlashCommand)
    _CheckSigT = typing.TypeVar("_CheckSigT", bound=tanjun.AnyCheckSig)
    _EventT = typing.TypeVar("_EventT", bound=hikari.Event)
    _ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound=tanjun.ListenerCallbackSig[typing.Any])
    _MenuCommandT = typing.TypeVar("_MenuCommandT", bound=tanjun.MenuCommand[typing.Any, typing.Any])
    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound=tanjun.MessageCommand[typing.Any])
    _MetaEventSigT = typing.TypeVar("_MetaEventSigT", bound=tanjun.MetaEventSig)
    _OnCallbackSigT = typing.TypeVar("_OnCallbackSigT", bound="OnCallbackSig")
    _ScheduleT = typing.TypeVar("_ScheduleT", bound=schedules_.AbstractSchedule)

    _CommandT = typing.TypeVar("_CommandT", bound="tanjun.ExecutableCommand[typing.Any]")
    # Pyright bug doesn't accept Var = Class | Class as a type
    _WithCommandReturnSig = typing.Union[_CommandT, "collections.Callable[[_CommandT], _CommandT]"]  # noqa: UP007

_LOGGER = logging.getLogger("hikari.tanjun.components")

OnCallbackSig = collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None] | None]
"""Type hint of a on_open or on_close component callback.

This represents the signatures `def (...) -> None` and `async def (...) -> None`
where dependency injection is supported.
"""


class AbstractComponentLoader(abc.ABC):
    """Abstract interface used for loading utility into a standard [Component][tanjun.Component]."""

    __slots__ = ()

    @abc.abstractmethod
    def load_into_component(self, component: tanjun.Component, /) -> None:
        """Load the object into the component.

        Parameters
        ----------
        component
            The component this object should be loaded into.
        """


def _with_command(
    add_command: collections.Callable[[_CommandT], Component],
    maybe_command: _CommandT | None,
    /,
    *,
    copy: bool = False,
    follow_wrapped: bool = False,
) -> _WithCommandReturnSig[_CommandT]:
    def decorator(command: _CommandT, /, *, _recursing: bool = False) -> _CommandT:
        return _internal.apply_to_wrapped(
            command,
            lambda c: add_command(typing.cast("_CommandT", c.copy() if copy else c)),
            command,
            follow_wrapped=follow_wrapped,
        )

    return decorator(maybe_command) if maybe_command else decorator


def _filter_scope(scope: collections.Mapping[str, typing.Any], /) -> collections.Iterator[typing.Any]:
    return (value for key, value in scope.items() if not key.startswith("_"))


class _ComponentManager(tanjun.ClientLoader):
    __slots__ = ("_component", "_copy")

    def __init__(self, component: Component, *, copy: bool) -> None:
        self._component = component
        self._copy = copy

    @property
    def has_load(self) -> bool:
        return True

    @property
    def has_unload(self) -> bool:
        return True

    def load(self, client: tanjun.Client, /) -> bool:
        client.add_component(self._component.copy() if self._copy else self._component)
        return True

    def unload(self, client: tanjun.Client, /) -> bool:
        client.remove_component_by_name(self._component.name)
        return True


# TODO: do we want to setup a custom equality and hash here to make it easier to unload components?
class Component(tanjun.Component):
    """Standard implementation of [tanjun.abc.Component][].

    This is a collcetion of commands (both message and slash), hooks and listener
    callbacks which can be added to a generic client.

    !!! note
        This implementation supports dependency injection for its checks,
        command callbacks and listeners when linked to a client which
        supports dependency injection.
    """

    __slots__ = (
        "_checks",
        "_client",
        "_client_callbacks",
        "_default_app_cmd_permissions",
        "_defaults_to_ephemeral",
        "_dms_enabled_for_app_cmds",
        "_hooks",
        "_is_case_sensitive",
        "_listeners",
        "_loop",
        "_menu_commands",
        "_menu_hooks",
        "_message_commands",
        "_message_hooks",
        "_metadata",
        "_name",
        "_on_close",
        "_on_open",
        "_schedules",
        "_slash_commands",
        "_slash_hooks",
        "_tasks",
    )

    def __init__(self, *, name: str | None = None, strict: bool = False) -> None:
        """Initialise a new component.

        Parameters
        ----------
        name
            The component's identifier.

            If not provided then this will be a random string.
        strict
            Whether this component should use a stricter (more optimal) approach
            for message command search.

            When this is [True][], message command names will not be allowed to contain
            spaces and will have to be unique to one command within the component.
        """
        self._checks: list[tanjun.AnyCheckSig] = []
        self._client: tanjun.Client | None = None
        self._client_callbacks: dict[str, list[tanjun.MetaEventSig]] = {}
        self._default_app_cmd_permissions: hikari.Permissions | None = None
        self._defaults_to_ephemeral: bool | None = None
        self._dms_enabled_for_app_cmds: bool | None = None
        self._hooks: tanjun.AnyHooks | None = None
        self._is_case_sensitive: bool | None = None
        self._listeners: dict[type[hikari.Event], list[tanjun.ListenerCallbackSig[typing.Any]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._menu_commands: dict[tuple[hikari.CommandType, str], tanjun.MenuCommand[typing.Any, typing.Any]] = {}
        self._menu_hooks: tanjun.MenuHooks | None = None
        self._message_commands = _internal.MessageCommandIndex(strict=strict)
        self._message_hooks: tanjun.MessageHooks | None = None
        self._metadata: dict[typing.Any, typing.Any] = {}
        self._name = name or str(uuid.uuid4())
        self._on_close: list[OnCallbackSig] = []
        self._on_open: list[OnCallbackSig] = []
        self._schedules: list[schedules_.AbstractSchedule] = []
        self._slash_commands: dict[str, tanjun.BaseSlashCommand] = {}
        self._slash_hooks: tanjun.SlashHooks | None = None
        self._tasks: list[asyncio.Task[typing.Any]] = []

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.checks=}, {self.hooks=}, {self.slash_hooks=}, {self.message_hooks=})"

    @property
    def is_case_sensitive(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._is_case_sensitive

    @property
    def checks(self) -> collections.Collection[tanjun.AnyCheckSig]:
        """Collection of the checks being run against every command execution in this component."""
        return self._checks.copy()

    @property
    def client(self) -> tanjun.Client | None:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._client

    @property
    def default_app_cmd_permissions(self) -> hikari.Permissions | None:
        return self._default_app_cmd_permissions

    @property
    def defaults_to_ephemeral(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._defaults_to_ephemeral

    @property
    def dms_enabled_for_app_cmds(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._dms_enabled_for_app_cmds

    @property
    def hooks(self) -> tanjun.AnyHooks | None:
        """The general command hooks set for this component, if any."""
        return self._hooks

    @property
    def menu_hooks(self) -> tanjun.MenuHooks | None:
        """The menu command hooks set for this component, if any."""
        return self._menu_hooks

    @property
    def message_hooks(self) -> tanjun.MessageHooks | None:
        """The message command hooks set for this component, if any."""
        return self._message_hooks

    @property
    def slash_hooks(self) -> tanjun.SlashHooks | None:
        """The slash command hooks set for this component, if any."""
        return self._slash_hooks

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._loop

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._name

    @property
    def schedules(self) -> collections.Collection[schedules_.AbstractSchedule]:
        """Collection of the schedules registered to this component."""
        return self._schedules

    @property
    def slash_commands(self) -> collections.Collection[tanjun.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._slash_commands.copy().values()

    @property
    def menu_commands(self) -> collections.Collection[tanjun.MenuCommand[typing.Any, typing.Any]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._menu_commands.copy().values()

    @property
    def message_commands(self) -> collections.Collection[tanjun.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._message_commands.commands.copy()

    @property
    def listeners(
        self,
    ) -> collections.Mapping[type[hikari.Event], collections.Collection[tanjun.ListenerCallbackSig[typing.Any]]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _internal.CastedView(self._listeners, lambda x: x.copy())

    @property
    def metadata(self) -> dict[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._metadata

    def _remove_task(self, task: asyncio.Task[typing.Any], /) -> None:
        self._tasks.remove(task)

    def _add_task(self, task: asyncio.Task[typing.Any], /) -> None:
        if not task.done():
            self._tasks.append(task)
            task.add_done_callback(self._remove_task)

    def copy(self) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        inst = copy.copy(self)
        inst._checks = [copy.copy(check) for check in self._checks]  # noqa: SLF001
        inst._slash_commands = {name: command.copy() for name, command in self._slash_commands.items()}  # noqa: SLF001
        inst._hooks = self._hooks.copy() if self._hooks else None  # noqa: SLF001
        inst._listeners = {  # noqa: SLF001
            event: [copy.copy(listener) for listener in listeners] for event, listeners in self._listeners.items()
        }
        inst._message_commands = self._message_commands.copy()  # noqa: SLF001
        inst._metadata = self._metadata.copy()  # noqa: SLF001
        inst._schedules = [schedule.copy() for schedule in self._schedules] if self._schedules else []  # noqa: SLF001
        return inst

    @typing.overload
    def load_from_scope(self, *, scope: collections.Mapping[str, typing.Any] | None = None) -> Self: ...

    @typing.overload
    def load_from_scope(self, *, include_globals: bool = False) -> Self: ...

    def load_from_scope(
        self, *, include_globals: bool = False, scope: collections.Mapping[str, typing.Any] | None = None
    ) -> Self:
        """Load entries such as top-level commands into the component from the calling scope.

        !!! note
            This will load schedules which support and commands
            [AbstractComponentLoader][tanjun.components.AbstractComponentLoader]
            (all standard implementations support this) and will ignore commands
            which are owned by command groups.

        !!! note
            This will detect entries from the calling scope which implement
            [AbstractComponentLoader][tanjun.components.AbstractComponentLoader]
            unless `scope` is passed but this isn't possible in a stack-less
            python implementation; in stack-less environments the scope will
            have to be explicitly passed as `scope`.

        Parameters
        ----------
        include_globals
            Whether to include global variables (along with local) while
            detecting from the calling scope.

            This cannot be [True][] when `scope` is provided and will only ever
            be needed when the local scope is different from the global scope.
        scope
            The scope to detect entries which implement
            [AbstractComponentLoader][tanjun.components.AbstractComponentLoader]
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
                error_message = (
                    "Stackframe introspection is not supported in this runtime. Please explicitly pass `scope`."
                )
                raise RuntimeError(error_message)

            values_iter = _filter_scope(stack.f_back.f_locals)
            if include_globals:
                values_iter = itertools.chain(values_iter, _filter_scope(stack.f_back.f_globals))

        elif include_globals:
            error_message = "Cannot specify include_globals as True when scope is passed"
            raise ValueError(error_message)

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

    def set_case_sensitive(self, state: bool | None, /) -> Self:
        """Set whether this component defaults to being case sensitive for component.

        Parameters
        ----------
        state
            Whether this component's message commands should be matched
            case-sensitively.

            If this is left as [None][] then the client's case-sensitive
            setting will be used.
        """
        self._is_case_sensitive = state
        return self

    def set_default_app_command_permissions(self, permissions: int | hikari.Permissions | None, /) -> Self:
        """Set the default member permissions needed for this component's commands.

        !!! warning
            This may be overridden by guild staff and does not apply to admins.

        Parameters
        ----------
        permissions
            The default member permissions needed for this component's application commands.

            If this is left as [None][] then this config will be inherited from
            the parent client.

            This may be overridden by
            [AppCommand.default_member_permissions][tanjun.abc.AppCommand.default_member_permissions]
            and if this is left as [None][] then this config will be inherited
            from the parent client.

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._default_app_cmd_permissions = hikari.Permissions(permissions) if permissions is not None else None
        return self

    def set_dms_enabled_for_app_cmds(self, state: bool | None, /) -> Self:
        """Set whether this component's commands should be enabled in DMs.

        Parameters
        ----------
        state
            Whether to enable this component's commands in DMs.

            This may be overridden by
            [AppCommand.is_dm_enabled][tanjun.abc.AppCommand.is_dm_enabled]
            and if this is left as [None][] then this config will be inherited
            from the parent client.

        Returns
        -------
        Self
            This client to enable method chaining.
        """
        self._dms_enabled_for_app_cmds = state
        return self

    def set_ephemeral_default(self, state: bool | None, /) -> Self:
        """Set whether slash contexts executed in this component should default to ephemeral responses.

        Parameters
        ----------
        state
            Whether slash command contexts executed in this component should
            should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to [None][] will let the default set on the parent
            client propagate and decide the ephemeral default behaviour.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_metadata(self, key: typing.Any, value: typing.Any, /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._metadata[key] = value
        return self

    def set_hooks(self, hooks: tanjun.AnyHooks | None, /) -> Self:
        """Set hooks to be called during the execution of all of this component's commands.

        Parameters
        ----------
        hooks
            The command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._hooks = hooks
        return self

    def set_menu_hooks(self, hooks: tanjun.MenuHooks | None, /) -> Self:
        """Set hooks to be called during the execution of this component's menu commands.

        Parameters
        ----------
        hooks
            The menu command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._menu_hooks = hooks
        return self

    def set_message_hooks(self, hooks: tanjun.MessageHooks | None, /) -> Self:
        """Set hooks to be called during the execution of this component's message commands.

        Parameters
        ----------
        hooks
            The message command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._message_hooks = hooks
        return self

    def set_slash_hooks(self, hooks: tanjun.SlashHooks | None, /) -> Self:
        """Set hooks to be called during the execution of this component's slash commands.

        Parameters
        ----------
        hooks
            The slash command hooks to set.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        self._slash_hooks = hooks
        return self

    def add_check(self, *checks: tanjun.AnyCheckSig) -> Self:
        """Add a command check to this component to be used for all its commands.

        Parameters
        ----------
        *checks
            The checks to add.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        for check in checks:
            if check not in self._checks:
                self._checks.append(check)

        return self

    def remove_check(self, check: tanjun.AnyCheckSig, /) -> Self:
        """Remove a command check from this component.

        Parameters
        ----------
        check
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

    def add_client_callback(self, name: str | tanjun.ClientCallbackNames, /, *callbacks: tanjun.MetaEventSig) -> Self:
        """Add a client callback.

        Parameters
        ----------
        name
            The name this callback is being registered to.

            This is case-insensitive.
        *callbacks
            The callbacks to register.

            These may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.

        Returns
        -------
        Self
            The client instance to enable chained calls.
        """
        name = name.lower()
        for callback in callbacks:
            try:
                if callback in self._client_callbacks[name]:
                    continue

            except KeyError:
                self._client_callbacks[name] = [callback]

            else:
                self._client_callbacks[name].append(callback)

            if self._client:
                self._client.add_client_callback(name, callback)

        return self

    def get_client_callbacks(
        self, name: str | tanjun.ClientCallbackNames, /
    ) -> collections.Collection[tanjun.MetaEventSig]:
        """Get a collection of the callbacks registered for a specific name.

        Parameters
        ----------
        name
            The name to get the callbacks registered for.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Collection[MetaEventSig]
            Collection of the callbacks for the provided name.
        """
        name = name.lower()
        return self._client_callbacks.get(name) or ()

    def remove_client_callback(self, name: str, callback: tanjun.MetaEventSig, /) -> None:
        """Remove a client callback.

        Parameters
        ----------
        name
            The name this callback is being registered to.

            This is case-insensitive.
        callback
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
        name = name.lower()
        self._client_callbacks[name].remove(callback)
        if not self._client_callbacks[name]:
            del self._client_callbacks[name]

        if self._client:
            self._client.remove_client_callback(name, callback)

    def with_client_callback(
        self, name: str | tanjun.ClientCallbackNames, /
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
        name
            The name this callback is being registered to.

            This is case-insensitive.

        Returns
        -------
        collections.abc.Callable[[tanjun.abc.MetaEventSig], tanjun.abc.MetaEventSig]
            Decorator callback used to register the client callback.

            This may be sync or async and must return None. The positional and
            keyword arguments a callback should expect depend on implementation
            detail around the `name` being subscribed to.
        """

        def decorator(callback: _MetaEventSigT, /) -> _MetaEventSigT:
            self.add_client_callback(name, callback)
            return callback

        return decorator

    def add_command(self, command: tanjun.ExecutableCommand[typing.Any], /) -> Self:
        """Add a command to this component.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The current component to allow for chaining.
        """
        if isinstance(command, tanjun.MessageCommand):
            self.add_message_command(command)

        elif isinstance(command, tanjun.BaseSlashCommand):
            self.add_slash_command(command)

        elif isinstance(command, tanjun.MenuCommand):
            self.add_menu_command(command)

        else:
            error_message = (
                "Unexpected object passed, expected a MenuCommand, "
                f"MessageCommand or BaseSlashCommand but got {type(command)}"
            )
            raise TypeError(error_message)

        return self

    def remove_command(self, command: tanjun.ExecutableCommand[typing.Any], /) -> Self:
        """Remove a command from this component.

        Parameters
        ----------
        command
            The command to remove.

        Returns
        -------
        Self
            This component to enable method chaining.
        """
        if isinstance(command, tanjun.MessageCommand):
            self.remove_message_command(command)

        elif isinstance(command, tanjun.BaseSlashCommand):
            self.remove_slash_command(command)

        elif isinstance(command, tanjun.MenuCommand):
            self.remove_menu_command(command)

        else:
            error_message = (
                f"Unexpected object passed, expected a MessageCommand or BaseSlashCommand but got {type(command)}"
            )
            raise TypeError(error_message)

        return self

    @typing.overload
    def with_command(self, command: _CommandT, /) -> _CommandT: ...

    @typing.overload
    def with_command(
        self, /, *, copy: bool = False, follow_wrapped: bool = False
    ) -> collections.Callable[[_CommandT], _CommandT]: ...

    def with_command(
        self, command: _CommandT | None = None, /, *, copy: bool = False, follow_wrapped: bool = False
    ) -> _WithCommandReturnSig[_CommandT]:
        """Add a command to this component through a decorator call.

        Examples
        --------
        This may be used inconjunction with [tanjun.as_slash_command][]
        and [tanjun.as_message_command][].

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
        copy
            Whether to copy the command before adding it to this component.
        follow_wrapped
            Whether to also add any commands `command` wraps in a decorator
            call chain.

        Returns
        -------
        tanjun.abc.ExecutableCommand
            The added command.
        """
        return _with_command(self.add_command, command, copy=copy, follow_wrapped=follow_wrapped)

    def add_menu_command(self, command: tanjun.MenuCommand[typing.Any, typing.Any], /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        key = (command.type, command.name)
        if self._menu_commands.get(key) == command:
            return self

        command.bind_component(self)

        if self._client:
            command.bind_client(self._client)

        self._menu_commands[key] = command
        return self

    def remove_menu_command(self, command: tanjun.MenuCommand[typing.Any, typing.Any], /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        try:
            del self._menu_commands[(command.type, command.name)]
        except KeyError:
            error_message = f"Command {command.name} not found"
            raise ValueError(error_message) from None

        return self

    @typing.overload
    def with_menu_command(self, command: _MenuCommandT, /) -> _MenuCommandT: ...

    @typing.overload
    def with_menu_command(self, /, *, copy: bool = False) -> collections.Callable[[_MenuCommandT], _MenuCommandT]: ...

    def with_menu_command(
        self, command: _MenuCommandT | None = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_MenuCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_menu_command, command, copy=copy)

    def add_slash_command(self, command: tanjun.BaseSlashCommand, /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._slash_commands.get(command.name) == command:
            return self

        command.bind_component(self)

        if self._client:
            command.bind_client(self._client)

        self._slash_commands[command.name] = command
        return self

    def remove_slash_command(self, command: tanjun.BaseSlashCommand, /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        try:
            del self._slash_commands[command.name]
        except KeyError:
            error_message = f"Command {command.name} not found"
            raise ValueError(error_message) from None

        return self

    @typing.overload
    def with_slash_command(self, command: _BaseSlashCommandT, /) -> _BaseSlashCommandT: ...

    @typing.overload
    def with_slash_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_BaseSlashCommandT], _BaseSlashCommandT]: ...

    def with_slash_command(
        self, command: _BaseSlashCommandT | None = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_BaseSlashCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_slash_command, command, copy=copy)

    def add_message_command(self, command: tanjun.MessageCommand[typing.Any], /) -> Self:
        """Add a message command to the component.

        Parameters
        ----------
        command
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
        if self._message_commands.add(command):
            if self._client:
                command.bind_client(self._client)

            command.bind_component(self)

        return self

    def remove_message_command(self, command: tanjun.MessageCommand[typing.Any], /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._message_commands.remove(command)
        return self

    @typing.overload
    def with_message_command(self, command: _MessageCommandT, /) -> _MessageCommandT: ...

    @typing.overload
    def with_message_command(
        self, /, *, copy: bool = False
    ) -> collections.Callable[[_MessageCommandT], _MessageCommandT]: ...

    def with_message_command(
        self, command: _MessageCommandT | None = None, /, *, copy: bool = False
    ) -> _WithCommandReturnSig[_MessageCommandT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return _with_command(self.add_message_command, command, copy=copy)

    def add_listener(self, event: type[_EventT], /, *callbacks: tanjun.ListenerCallbackSig[_EventT]) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        for listener in callbacks:
            try:
                if listener in self._listeners[event]:
                    continue

            except KeyError:
                self._listeners[event] = [listener]

            else:
                self._listeners[event].append(listener)

            if self._client:
                self._client.add_listener(event, listener)

        return self

    def remove_listener(self, event: type[_EventT], listener: tanjun.ListenerCallbackSig[_EventT], /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        self._listeners[event].remove(listener)
        if not self._listeners[event]:
            del self._listeners[event]

        if self._client:
            self._client.remove_listener(event, listener)

        return self

    def with_listener(
        self, *event_types: type[hikari.Event]
    ) -> collections.Callable[[_ListenerCallbackSigT], _ListenerCallbackSigT]:
        # <<inherited docstring from tanjun.abc.Component>>.
        def decorator(callback: _ListenerCallbackSigT, /) -> _ListenerCallbackSigT:
            for event_type in event_types or _internal.infer_listener_types(callback):
                self.add_listener(event_type, callback)

            return callback

        return decorator

    def add_on_close(self, *callbacks: OnCallbackSig) -> Self:
        """Add a close callback to this component.

        !!! note
            Unlike the closing and closed client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        *callbacks
            The close callbacks to add to this component.

            This should take no positional arguments, return [None][] and may
            take use injected dependencies.

        Returns
        -------
        Self
            The component object to enable call chaining.
        """
        self._on_close.extend(callbacks)
        return self

    def with_on_close(self, callback: _OnCallbackSigT, /) -> _OnCallbackSigT:
        """Add a close callback to this component through a decorator call.

        !!! note
            Unlike the closing and closed client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        callback : OnCallbackSig
            The close callback to add to this component.

            This should take no positional arguments, return [None][] and may
            request injected dependencies.

        Returns
        -------
        OnCallbackSig
            The added close callback.
        """
        self.add_on_close(callback)
        return callback

    def add_on_open(self, *callbacks: OnCallbackSig) -> Self:
        """Add a open callback to this component.

        !!! note
            Unlike the starting and started client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        *callbacks
            The open callbacks to add to this component.

            These should take no positional arguments, return [None][] and may
            request injected dependencies.

        Returns
        -------
        Self
            The component object to enable call chaining.
        """
        self._on_open.extend(callbacks)
        return self

    def with_on_open(self, callback: _OnCallbackSigT, /) -> _OnCallbackSigT:
        """Add a open callback to this component through a decorator call.

        !!! note
            Unlike the starting and started client callbacks, this is only
            called for the current component's lifetime and is guaranteed to be
            called regardless of when the component was added to a client.

        Parameters
        ----------
        callback : OnCallbackSig
            The open callback to add to this component.

            This should take no positional arguments, return [None][] and may
            take use injected dependencies.

        Returns
        -------
        OnCallbackSig
            The added open callback.
        """
        self.add_on_open(callback)
        return callback

    def bind_client(self, client: tanjun.Client, /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._client:
            error_message = "Client already set"
            raise RuntimeError(error_message)

        self._client = client
        for message_command in self._message_commands.commands:
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

    def unbind_client(self, client: tanjun.Client, /) -> Self:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not self._client or self._client != client:
            error_message = "Component isn't bound to this client"
            raise RuntimeError(error_message)

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

    async def _check_context(self, ctx: tanjun.Context, /) -> bool:
        return await _internal.gather_checks(ctx, self._checks)

    async def _check_message_context(
        self, ctx: tanjun.MessageContext, /
    ) -> collections.AsyncIterator[tuple[str, tanjun.MessageCommand[typing.Any]]]:
        ctx.set_component(self)
        checks_run = False
        case_sensitive = self._is_case_sensitive
        if case_sensitive is None:
            case_sensitive = ctx.client.is_case_sensitive

        for name, command in self.check_message_name(ctx.content, case_sensitive=case_sensitive):
            if not checks_run:
                if not await self._check_context(ctx):
                    return

                checks_run = True

            if await command.check_context(ctx):
                yield name, command

        ctx.set_component(None)

    def check_message_name(
        self, content: str, /, *, case_sensitive: bool = True
    ) -> collections.Iterator[tuple[str, tanjun.MessageCommand[typing.Any]]]:
        # <<inherited docstring from tanjun.abc.Component>>.
        return self._message_commands.find(content, case_sensitive=case_sensitive)

    def check_slash_name(self, name: str, /) -> collections.Iterator[tanjun.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.Component>>.
        if command := self._slash_commands.get(name):
            yield command

    def execute_autocomplete(
        self, ctx: tanjun.AutocompleteContext, /
    ) -> collections.Coroutine[typing.Any, typing.Any, None] | None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if command := self._slash_commands.get(ctx.interaction.command_name):
            return command.execute_autocomplete(ctx)

        return None  # MyPy compat

    async def _execute_app(
        self,
        ctx: _AppCommandContextT,
        command: tanjun.AppCommand[_AppCommandContextT] | None,
        /,
        *,
        hooks: collections.MutableSet[tanjun.Hooks[_AppCommandContextT]] | None = None,
        other_hooks: tanjun.Hooks[_AppCommandContextT] | None = None,
    ) -> collections.Coroutine[typing.Any, typing.Any, None] | None:
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
        self, ctx: tanjun.MenuContext, /, *, hooks: collections.MutableSet[tanjun.MenuHooks] | None = None
    ) -> collections.Coroutine[typing.Any, typing.Any, collections.Coroutine[typing.Any, typing.Any, None] | None]:
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
        self, ctx: tanjun.SlashContext, /, *, hooks: collections.MutableSet[tanjun.SlashHooks] | None = None
    ) -> collections.Coroutine[typing.Any, typing.Any, collections.Coroutine[typing.Any, typing.Any, None] | None]:
        # <<inherited docstring from tanjun.abc.Component>>.
        command = self._slash_commands.get(ctx.interaction.command_name)
        if command:
            if command.defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(command.defaults_to_ephemeral)

            elif self._defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(self._defaults_to_ephemeral)

        return self._execute_app(ctx, command, hooks=hooks, other_hooks=self._slash_hooks)

    async def execute_message(
        self, ctx: tanjun.MessageContext, /, *, hooks: collections.MutableSet[tanjun.MessageHooks] | None = None
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

    def add_schedule(self, schedule: schedules_.AbstractSchedule, /) -> Self:
        """Add a schedule to the component.

        Parameters
        ----------
        schedule
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

    def remove_schedule(self, schedule: schedules_.AbstractSchedule, /) -> Self:
        """Remove a schedule from the component.

        Parameters
        ----------
        schedule
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
        if self._loop and schedule.is_alive:
            self._add_task(self._loop.create_task(schedule.stop()))

        self._schedules.remove(schedule)
        return self

    def with_schedule(self, schedule: _ScheduleT, /) -> _ScheduleT:
        """Add a schedule to the component through a decorator call.

        Example
        -------
        This may be used in conjunction with [tanjun.as_interval][] or
        [tanjun.as_time_schedule][].

        ```py
        @component.with_schedule
        @tanjun.as_interval(60)
        async def my_schedule():
            print("I'm running every minute!")
        ```

        Parameters
        ----------
        schedule : tanjun.schedules.AbstractSchedule
            The schedule to add.

        Returns
        -------
        tanjun.schedules.AbstractSchedule
            The added schedule.
        """
        self.add_schedule(schedule)
        return schedule

    async def close(self, *, unbind: bool = False) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if not self._loop:
            error_message = "Component isn't active"
            raise RuntimeError(error_message)

        assert self._client

        self._loop = None
        await asyncio.gather(*(schedule.stop() for schedule in self._schedules if schedule.is_alive))
        await asyncio.gather(*(self._client.injector.call_with_async_di(callback) for callback in self._on_close))
        if unbind:
            self.unbind_client(self._client)

    async def open(self) -> None:
        # <<inherited docstring from tanjun.abc.Component>>.
        if self._loop:
            error_message = "Component is already active"
            raise RuntimeError(error_message)

        if not self._client:
            error_message = "Client isn't bound yet"
            raise RuntimeError(error_message)

        self._loop = asyncio.get_running_loop()
        await asyncio.gather(*(self._client.injector.call_with_async_di(callback) for callback in self._on_open))

        for schedule in self._schedules:
            schedule.start(self._client.injector, loop=self._loop)

    def make_loader(self, *, copy: bool = True) -> tanjun.ClientLoader:
        """Make a loader/unloader for this component.

        This enables loading, unloading and reloading of this component into a
        client by targeting the module using
        [Client.load_modules][tanjun.abc.Client.load_modules],
        [Client.unload_modules][tanjun.abc.Client.unload_modules] and
        [Client.reload_modules][tanjun.abc.Client.reload_modules].

        Parameters
        ----------
        copy
            Whether to copy the component before loading it into a client.

        Returns
        -------
        tanjun.abc.ClientLoader
            The loader for this component.
        """
        return _ComponentManager(self, copy=copy)
