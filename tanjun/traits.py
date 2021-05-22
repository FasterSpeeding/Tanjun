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
"""Interfaces of the objects used within Tanjun."""
from __future__ import annotations

__all__: typing.Sequence[str] = [
    "LoadableDescriptor",
    "ParserDescriptor",
    "ConverterT",
    "ParserHookT",
    "ErrorHookT",
    "HookT",
    "PreExecutionHookT",
    "CheckT",
    "ValueT_co",
    "Context",
    "Hooks",
    "Executable",
    "FoundCommand",
    "ExecutableCommand",
    "ExecutableCommandGroup",
    "Component",
    "Client",
    "UNDEFINED_DEFAULT",
    "Parameter",
    "Argument",
    "Option",
    "Parser",
]

import abc
import typing

if typing.TYPE_CHECKING:
    from hikari import messages
    from hikari import traits
    from hikari.api import event_manager
    from hikari.api import shard as shard_
    from hikari.events import base_events

    from tanjun import errors

    _T = typing.TypeVar("_T")


# To allow for stateless converters we accept both "Converter[...]" and "Type[StatelessConverter[...]]" where all the
# methods on "Type[StatelessConverter[...]]" need to be classmethods as it will not be initialised before calls are made
# to it.
ConverterT = typing.Callable[[str], typing.Union[typing.Coroutine[typing.Any, typing.Any, typing.Any], typing.Any]]
"""Type hint of a converter used within a parser instance.

This must be a callable or asynchronous callable which takes one position
`builtins.string` argument and returns the resultant value.
"""
# TODO: be more specific about the structure of command functions using a callable protocol

CommandFunctionT = typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]
"""Type hint of the function a `Command` instance will operate on.

This will be called when executing a command and will need to take at least one
positional argument of type `Context` where any other required or optional
keyword or positional arguments will be based on the parser instance for the
command if applicable.

!!! note
    This will have to be asynchronous.
"""

LoadableT = typing.Callable[["Client"], None]
"""Type hint of the function used to load resources into a Tanjun client.

This should take one positional argument of type `Client` and return nothing.
This will be expected to initiate and resources like components to the client
through the use of it's protocol methods.
"""

ParserHookT = typing.Callable[
    ["Context", "errors.ParserError"], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
"""Type hint of the function used as a parser error hook.

This will be called whenever a `tanjun.errors.ParserError` is raised during the
command argument parsing stage, will have to take two positional arguments - of
type `Context` and `tanjun.errors.ParserError` - and may either be a
synchronous or asynchronous function which returns `builtins.None`
"""

ErrorHookT = typing.Callable[
    ["Context", BaseException], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
"""Type hint of the function used as a unexpected command error hook.

This will be called whenever a `builtins.BaseException` is raised during the
execution stage whenever the command function raises any exception except
`tanjun.errors.CommandError`,  will have to take two positional arguments - of
type `Context` and `builtins.BaseException` - and may either be a synchronous
or asynchronous function which returns `builtins.None`
"""

HookT = typing.Callable[["Context"], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]]
"""Type hint of the function used as a general command hook.

This may be called during different stages of command execution (decided by
which hook this is registered as), will have to take one positional argument of
type `Context` and may be a synchronous or asynchronous function which returns
`builtins.None`.
"""

PreExecutionHookT = typing.Callable[["Context"], typing.Union[typing.Coroutine[typing.Any, typing.Any, bool], bool]]
"""Type hint of the function used as a pre-execution command hook.

This will be called before command function is executed, will have to take one
positional argument of type `Context` and may be a synchronous or asynchronous
function which returns `builtins.bool` (where returning `False` may cancel
execution of the current command).
"""

CheckT = typing.Callable[..., typing.Union[bool, typing.Awaitable[bool]]]
"""Type hint of a general context check used with Tanjun `Executable` classes.

This may be registered with a `Executable` to add a rule which decides whether
it should execute for each context passed to it. This should take one positional
argument of type `Context` and may either be a synchronous or asynchronous
function which returns `builtins.bool` where returning `builtins.False` or
raising `tanjun.errors.FailedCheck` will indicate that the current context
shouldn't lead to an execution.
"""

ComponentT_contra = typing.TypeVar("ComponentT_contra", bound="Component", contravariant=True)

UnboundCheckT = typing.Callable[
    ["ComponentT_contra", "Context"], typing.Union[bool, typing.Coroutine[typing.Any, typing.Any, bool]]
]  # TODO: remove this
"""Type hint of a general context check used by Tanjun `Executable` classes.

This is an equivalent to `CheckT` where it's yet to be bound to a `Component`,
used by `CheckDescriptor`.
"""

ValueT_co = typing.TypeVar("ValueT_co", covariant=True)
"""A general type hint used for generic interfaces in Tanjun."""


class LoadableDescriptor(abc.ABC):
    """Descriptor of a function used for loading a lib's resources into a Tanjun instance."""

    __slots__: typing.Sequence[str] = ()

    @property
    def load_function(self) -> LoadableT:
        """Function called to load these resources into a Tanjun client.

        Returns
        -------
        LoadableT
            The load function which should take one argument of type Client and
            return nothing. This should call methods on `Client` in-order to
            load it's pre-prepared resources.
        """
        raise NotImplementedError


class ParserDescriptor(abc.ABC):
    """Descriptor of a parser for command descriptor."""

    __slots__: typing.Sequence[str] = ()

    @property
    def parameters(self) -> typing.Sequence[Parameter]:
        """Get the parameters rules set for this parser descriptor.

        Returns
        -------
        typing.Sequence[Parameter]
            A sequence of the parameters rules set for this parser descriptor.
        """
        raise NotImplementedError

    def add_parameter(self, parameter: Parameter, /) -> None:
        """Add a parameter to the parser's rules.

        !!! note
            For positional arguments this should add from left to right if the
            index isn't explicitly declared.

        Parameters
        ----------
        parameter : Parameter
            The parameter to add.
        """
        raise NotImplementedError

    def set_parameters(self, parameters: typing.Iterable[Parameter], /) -> None:
        """Set the parameters for this parser's rules.

        !!! note
            This will replace any previously set parameters.

        Parameters
        ----------
        parameters : typing.Iterable[Parameter]
            An iterable of the parameters to set for this parser.
        """
        raise NotImplementedError

    def build_parser(self, component: Component, /) -> Parser:
        """Build a parser object from this descriptor.

        Parameters
        ----------
        component : ExecutableCommand
            The component this command is being built for.

        Returns
        -------
        ExecutableCommand
            The command object that was created.
        """
        raise NotImplementedError


class Context(abc.ABC):
    """Traits for the context of a command execution event."""

    __slots__: typing.Sequence[str] = ()

    @property
    def cache_service(self) -> typing.Optional[traits.CacheAware]:
        raise NotImplementedError

    @property
    def client(self) -> Client:
        """The Tanjun `Client` implementation this context was spawned by.

        Returns
        -------
        Client
            The Tanjun `Client` implementation this context was spawned by.
        """
        raise NotImplementedError

    @property
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @component.setter
    def component(self, _: Component, /) -> None:
        raise NotImplementedError

    @property  # TODO: can we somehow have this always be present on the command execution facing interface
    def command(self) -> typing.Optional[ExecutableCommand]:
        raise NotImplementedError

    @command.setter
    def command(self, _: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @property
    def content(self) -> str:
        raise NotImplementedError

    @content.setter
    def content(self, _: str, /) -> None:
        raise NotImplementedError

    @property
    def event_service(self) -> traits.EventManagerAware:
        raise NotImplementedError

    @property
    def message(self) -> messages.Message:
        raise NotImplementedError

    @property
    def rest_service(self) -> traits.RESTAware:
        raise NotImplementedError

    @property
    def shard_service(self) -> traits.ShardAware:
        raise NotImplementedError

    @property
    def shard(self) -> shard_.GatewayShard:
        raise NotImplementedError

    @property
    def triggering_prefix(self) -> str:
        raise NotImplementedError

    @property
    def triggering_name(self) -> str:
        raise NotImplementedError

    @triggering_name.setter
    def triggering_name(self, _: str, /) -> None:
        raise NotImplementedError


class Hooks(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    async def trigger_error(
        self, ctx: Context, /, exception: BaseException, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    async def trigger_parser_error(
        self, ctx: Context, /, exception: errors.ParserError, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    async def trigger_post_execution(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    async def trigger_pre_execution(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> bool:
        raise NotImplementedError

    async def trigger_success(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError


class Executable(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def checks(self) -> typing.AbstractSet[CheckT]:
        raise NotImplementedError

    @property
    def hooks(self) -> typing.Optional[Hooks]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, _: typing.Optional[Hooks]) -> None:
        raise NotImplementedError

    def add_check(self: _T, check: CheckT, /) -> _T:
        raise NotImplementedError

    def remove_check(self, check: CheckT, /) -> None:
        raise NotImplementedError

    def with_check(self, check: CheckT, /) -> CheckT:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    def check_context(self, ctx: Context, /, *, name_prefix: str = "") -> typing.AsyncIterator[FoundCommand]:
        raise NotImplementedError

    def check_name(self, name: str, /) -> typing.Iterator[FoundCommand]:
        raise NotImplementedError

    async def execute(self, ctx: Context, /, *, hooks: typing.Optional[typing.MutableSet[Hooks]] = None) -> bool:
        raise NotImplementedError


class FoundCommand(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def command(self) -> ExecutableCommand:
        raise NotImplementedError

    @command.setter
    def command(self, _: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @name.setter
    def name(self, _: typing.Optional[str], /) -> None:
        raise NotImplementedError


class ExecutableCommand(Executable, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @property
    def function(self) -> CommandFunctionT:
        raise NotImplementedError

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    def names(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    @property
    def parent(self) -> typing.Optional[ExecutableCommandGroup]:
        raise NotImplementedError

    @parent.setter
    def parent(self, _: typing.Optional[ExecutableCommandGroup], /) -> None:
        raise NotImplementedError

    @property
    def parser(self) -> typing.Optional[Parser]:
        raise NotImplementedError

    @parser.setter
    def parser(self, _: typing.Optional[Parser], /) -> None:
        raise NotImplementedError

    def add_name(self: _T, name: str, /) -> _T:
        raise NotImplementedError

    def remove_name(self, name: str, /) -> None:
        raise NotImplementedError

    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError


class ExecutableCommandGroup(ExecutableCommand, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def commands(self) -> typing.AbstractSet[ExecutableCommand]:
        raise NotImplementedError

    def add_command(self: _T, command: ExecutableCommand, /) -> _T:
        raise NotImplementedError

    def remove_command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    def with_command(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[CheckT]] = None,
        hooks: typing.Optional[Hooks] = None,
        parser: typing.Optional[Parser] = None,
    ) -> typing.Callable[[CommandFunctionT], CommandFunctionT]:
        raise NotImplementedError


class Component(Executable, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def client(self) -> typing.Optional[Client]:
        raise NotImplementedError

    @property
    def commands(self) -> typing.AbstractSet[ExecutableCommand]:
        raise NotImplementedError

    @property
    def listeners(
        self,
    ) -> typing.AbstractSet[typing.Tuple[typing.Type[base_events.Event], event_manager.CallbackT[typing.Any]]]:
        raise NotImplementedError

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    def add_command(self: _T, command: ExecutableCommand, /) -> _T:
        raise NotImplementedError

    def remove_command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    def add_listener(
        self: _T, event: typing.Type[base_events.Event], listener: event_manager.CallbackT[typing.Any], /
    ) -> _T:
        raise NotImplementedError

    def remove_listener(
        self, event: typing.Type[base_events.Event], listener: event_manager.CallbackT[typing.Any], /
    ) -> None:
        raise NotImplementedError

    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def open(self) -> None:
        raise NotImplementedError


class Client(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def cache_service(self) -> typing.Optional[traits.CacheAware]:
        raise NotImplementedError

    @property
    def components(self) -> typing.AbstractSet[Component]:
        raise NotImplementedError

    @property
    def event_service(self) -> traits.EventManagerAware:
        raise NotImplementedError

    @property
    def hooks(self) -> typing.Optional[Hooks]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, _: typing.Optional[Hooks]) -> None:
        raise NotImplementedError

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    def prefixes(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    @property
    def rest_service(self) -> traits.RESTAware:
        raise NotImplementedError

    @property
    def shard_service(self) -> traits.ShardAware:
        raise NotImplementedError

    def add_component(self: _T, component: Component, /) -> _T:
        raise NotImplementedError

    def remove_component(self, component: Component, /) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    def check_context(self, ctx: Context, /) -> typing.AsyncIterator[FoundCommand]:
        raise NotImplementedError

    def check_name(self, name: str, /) -> typing.Iterator[FoundCommand]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def open(self) -> None:
        raise NotImplementedError


class UndefinedDefault:
    __slots__: typing.Sequence[str] = ()


UNDEFINED_DEFAULT = UndefinedDefault()
"""A singleton used to represent no default for a parameter."""


class Parameter(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def converters(self) -> typing.Optional[typing.Sequence[ConverterT]]:
        raise NotImplementedError

    @property
    def default(self) -> typing.Union[typing.Any, UndefinedDefault]:
        raise NotImplementedError

    @default.setter
    def default(self, _: typing.Union[typing.Any, UndefinedDefault], /) -> None:
        raise NotImplementedError

    @property
    def flags(self) -> typing.MutableMapping[str, typing.Any]:
        raise NotImplementedError

    @property
    def key(self) -> str:
        raise NotImplementedError

    @key.setter
    def key(self, _: str) -> None:
        raise NotImplementedError

    def add_converter(self, converter: ConverterT, /) -> None:
        raise NotImplementedError

    def remove_converter(self, converter: ConverterT, /) -> None:
        raise NotImplementedError

    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    async def convert(self, ctx: Context, value: str) -> typing.Any:
        raise NotImplementedError


class Argument(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()


class Option(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def empty_value(self) -> typing.Union[typing.Any, UndefinedDefault]:
        raise NotImplementedError

    @empty_value.setter
    def empty_value(self, _: typing.Union[typing.Any, UndefinedDefault], /) -> None:
        raise NotImplementedError

    @property
    def names(self) -> typing.Sequence[str]:
        raise NotImplementedError

    @names.setter
    def names(self, _: typing.Sequence[str], /) -> None:
        raise NotImplementedError


class Parser(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def parameters(self) -> typing.Sequence[Parameter]:
        raise NotImplementedError

    def add_parameter(self, parameter: Parameter, /) -> None:
        raise NotImplementedError

    def remove_parameter(self, parameter: Parameter, /) -> None:
        raise NotImplementedError

    def set_parameters(self, parameters: typing.Iterable[Parameter], /) -> None:
        raise NotImplementedError

    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    async def parse(self, ctx: Context, /) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
        raise NotImplementedError
