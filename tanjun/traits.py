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
    "ConverterSig",
    "CheckSig",
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
    "CachedREST",
]

import abc
import typing

if typing.TYPE_CHECKING:
    from hikari import applications
    from hikari import channels
    from hikari import emojis
    from hikari import guilds
    from hikari import invites
    from hikari import messages
    from hikari import snowflakes
    from hikari import traits
    from hikari import users
    from hikari.api import event_manager
    from hikari.api import shard as shard_
    from hikari.events import base_events

    from tanjun import errors

    _T = typing.TypeVar("_T")
    _ExecutableT = typing.TypeVar("_ExecutableT", bound="Executable")
    _HooksT = typing.TypeVar("_HooksT", bound="Hooks")
    _Parser = typing.TypeVar("_Parser", bound="Parser")
    _ParameterT = typing.TypeVar("_ParameterT", bound="Parameter")


# To allow for stateless converters we accept both "Converter[...]" and "Type[StatelessConverter[...]]" where all the
# methods on "Type[StatelessConverter[...]]" need to be classmethods as it will not be initialised before calls are made
# to it.
ConverterSig = typing.Callable[..., typing.Union[typing.Awaitable[typing.Any], typing.Any]]
"""Type hint of a converter used within a parser instance.

This must be a callable or asynchronous callable which takes one position
`builtins.string` argument and returns the resultant value.
"""
# TODO: be more specific about the structure of command functions using a callable protocol

CommandFunctionSig = typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]
"""Type hint of the function a `Command` instance will operate on.

This will be called when executing a command and will need to take at least one
positional argument of type `Context` where any other required or optional
keyword or positional arguments will be based on the parser instance for the
command if applicable.

!!! note
    This will have to be asynchronous.
"""


CheckSig = typing.Callable[..., typing.Union[bool, typing.Awaitable[bool]]]
"""Type hint of a general context check used with Tanjun `Executable` classes.

This may be registered with a `Executable` to add a rule which decides whether
it should execute for each context passed to it. This should take one positional
argument of type `Context` and may either be a synchronous or asynchronous
function which returns `builtins.bool` where returning `builtins.False` or
raising `tanjun.errors.FailedCheck` will indicate that the current context
shouldn't lead to an execution.
"""
CheckSigT = typing.TypeVar("CheckSigT", bound=CheckSig)

ComponentT_contra = typing.TypeVar("ComponentT_contra", bound="Component", contravariant=True)

ValueT_co = typing.TypeVar("ValueT_co", covariant=True)
"""A general type hint used for generic interfaces in Tanjun."""


class Context(abc.ABC):
    """Traits for the context of a command execution event."""

    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def cache_service(self) -> typing.Optional[traits.CacheAware]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def client(self) -> Client:
        """The Tanjun `Client` implementation this context was spawned by.

        Returns
        -------
        Client
            The Tanjun `Client` implementation this context was spawned by.
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @component.setter
    def component(self, _: Component, /) -> None:
        raise NotImplementedError

    @property  # TODO: can we somehow have this always be present on the command execution facing interface
    @abc.abstractmethod
    def command(self) -> typing.Optional[ExecutableCommand]:
        raise NotImplementedError

    @command.setter
    def command(self, _: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def content(self) -> str:
        raise NotImplementedError

    @content.setter
    def content(self, _: str, /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def event_service(self) -> traits.EventManagerAware:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def message(self) -> messages.Message:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def rest_service(self) -> traits.RESTAware:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard_service(self) -> traits.ShardAware:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard(self) -> shard_.GatewayShard:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def triggering_prefix(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def triggering_name(self) -> str:
        raise NotImplementedError

    @triggering_name.setter
    def triggering_name(self, _: str, /) -> None:
        raise NotImplementedError


class Hooks(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @abc.abstractmethod
    def copy(self: _HooksT) -> _HooksT:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_error(
        self, ctx: Context, /, exception: BaseException, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_parser_error(
        self,
        ctx: Context,
        /,
        exception: errors.ParserError,
        hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_post_execution(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_pre_execution(
        self,
        ctx: Context,
        /,
        *,
        hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_success(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError


class Executable(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def checks(self) -> typing.AbstractSet[CheckSig]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def hooks(self) -> typing.Optional[Hooks]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, _: typing.Optional[Hooks]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_check(self: _T, check: CheckSig, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _ExecutableT) -> _ExecutableT:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_check(self, check: CheckSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_check(self, check: CheckSigT, /) -> CheckSigT:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    @abc.abstractmethod
    def check_context(self, ctx: Context, /, *, name_prefix: str = "") -> typing.AsyncIterator[FoundCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_name(self, name: str, /) -> typing.Iterator[FoundCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(self, ctx: Context, /, *, hooks: typing.Optional[typing.MutableSet[Hooks]] = None) -> bool:
        raise NotImplementedError


class FoundCommand(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def command(self) -> ExecutableCommand:
        raise NotImplementedError

    @command.setter
    def command(self, _: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @name.setter
    def name(self, _: typing.Optional[str], /) -> None:
        raise NotImplementedError


class ExecutableCommand(Executable, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def function(self) -> CommandFunctionSig:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def names(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Optional[ExecutableCommandGroup]:
        raise NotImplementedError

    @parent.setter
    def parent(self, _: typing.Optional[ExecutableCommandGroup], /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def parser(self) -> typing.Optional[Parser]:
        raise NotImplementedError

    @parser.setter
    def parser(self, _: typing.Optional[Parser], /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_name(self: _T, name: str, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_name(self, name: str, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _ExecutableT, parent: typing.Optional[ExecutableCommandGroup], /) -> _ExecutableT:
        raise NotImplementedError


class ExecutableCommandGroup(ExecutableCommand, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def commands(self) -> typing.AbstractSet[ExecutableCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_command(self: _T, command: ExecutableCommand, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_command(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[CheckSig]] = None,
        hooks: typing.Optional[Hooks] = None,
        parser: typing.Optional[Parser] = None,
    ) -> typing.Callable[[CommandFunctionSig], CommandFunctionSig]:
        raise NotImplementedError


class Component(Executable, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def client(self) -> typing.Optional[Client]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def commands(self) -> typing.AbstractSet[ExecutableCommand]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def listeners(
        self,
    ) -> typing.AbstractSet[typing.Tuple[typing.Type[base_events.Event], event_manager.CallbackT[typing.Any]]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_command(self: _T, command: ExecutableCommand, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_listener(
        self: _T, event: typing.Type[base_events.Event], listener: event_manager.CallbackT[typing.Any], /
    ) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_listener(
        self, event: typing.Type[base_events.Event], listener: event_manager.CallbackT[typing.Any], /
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def open(self) -> None:
        raise NotImplementedError


class Client(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def cache_service(self) -> typing.Optional[traits.CacheAware]:
        raise NotImplementedError

    @property
    def cached_rest(self) -> CachedREST:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def components(self) -> typing.AbstractSet[Component]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def event_service(self) -> traits.EventManagerAware:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def hooks(self) -> typing.Optional[Hooks]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, _: typing.Optional[Hooks]) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def prefixes(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def rest_service(self) -> traits.RESTAware:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard_service(self) -> traits.ShardAware:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component(self: _T, component: Component, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_component(self, component: Component, /) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    @abc.abstractmethod
    def check_context(self, ctx: Context, /) -> typing.AsyncIterator[FoundCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    def check_name(self, name: str, /) -> typing.Iterator[FoundCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def open(self) -> None:
        raise NotImplementedError


class UndefinedDefault:
    __slots__: typing.Sequence[str] = ()


UNDEFINED_DEFAULT = UndefinedDefault()
"""A singleton used to represent no default for a parameter."""


class Parameter(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def converters(self) -> typing.Optional[typing.Sequence[ConverterSig]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def default(self) -> typing.Union[typing.Any, UndefinedDefault]:
        raise NotImplementedError

    @default.setter
    def default(self, _: typing.Union[typing.Any, UndefinedDefault], /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def flags(self) -> typing.MutableMapping[str, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def key(self) -> str:
        raise NotImplementedError

    @key.setter
    def key(self, _: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def add_converter(self, converter: ConverterSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _ParameterT) -> _ParameterT:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_converter(self, converter: ConverterSig, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def convert(self, ctx: Context, value: str) -> typing.Any:
        raise NotImplementedError


class Argument(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()


class Option(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def empty_value(self) -> typing.Union[typing.Any, UndefinedDefault]:
        raise NotImplementedError

    @empty_value.setter
    def empty_value(self, _: typing.Union[typing.Any, UndefinedDefault], /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def names(self) -> typing.Sequence[str]:
        raise NotImplementedError

    @names.setter
    def names(self, _: typing.Sequence[str], /) -> None:
        raise NotImplementedError


class Parser(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def parameters(self) -> typing.Sequence[Parameter]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_parameter(self, parameter: Parameter, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _Parser) -> _Parser:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_parameter(self, parameter: Parameter, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parameters(self, parameters: typing.Iterable[Parameter], /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def parse(self, ctx: Context, /) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
        raise NotImplementedError


class CachedREST(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    def clear(self) -> None:
        raise NotImplementedError

    def gc(self) -> None:
        raise NotImplementedError

    async def fetch_application(self) -> applications.Application:
        raise NotImplementedError

    async def fetch_channel(
        self, channel: snowflakes.SnowflakeishOr[channels.PartialChannel], /
    ) -> channels.PartialChannel:
        raise NotImplementedError

    async def fetch_emoji(
        self,
        guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
        emoji: snowflakes.SnowflakeishOr[emojis.CustomEmoji],
        /,
    ) -> emojis.KnownCustomEmoji:
        raise NotImplementedError

    async def fetch_guild(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild], /) -> guilds.Guild:
        raise NotImplementedError

    async def fetch_invite(self, invite: typing.Union[str, invites.Invite], /) -> invites.Invite:
        raise NotImplementedError

    async def fetch_member(
        self,
        guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
        user: snowflakes.SnowflakeishOr[users.User],
        /,
    ) -> guilds.Member:
        raise NotImplementedError

    async def fetch_message(
        self,
        channel: snowflakes.SnowflakeishOr[channels.PartialChannel],
        message: snowflakes.SnowflakeishOr[messages.Message],
        /,
    ) -> messages.Message:
        raise NotImplementedError

    async def fetch_my_user(self) -> users.OwnUser:
        raise NotImplementedError

    async def fetch_role(
        self,
        guild: snowflakes.SnowflakeishOr[guilds.PartialGuild],
        role: snowflakes.SnowflakeishOr[guilds.PartialRole],
        /,
    ) -> guilds.Role:
        raise NotImplementedError

    async def fetch_roles(
        self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild], /
    ) -> typing.Sequence[guilds.Role]:
        raise NotImplementedError

    async def fetch_user(self, user: snowflakes.SnowflakeishOr[users.User]) -> users.User:
        raise NotImplementedError
