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
    "FoundMessageCommand",
    "MessageCommand",
    "MessageCommandGroup",
    "Component",
    "Client",
    "UndefinedDefaultT",
    "UNDEFINED_DEFAULT",
    "Parameter",
    "Argument",
    "Option",
    "Parser",
    "CachedREST",
]

import abc
import typing

from hikari import undefined

if typing.TYPE_CHECKING:
    from hikari import applications
    from hikari import channels
    from hikari import embeds as embeds_
    from hikari import emojis
    from hikari import files
    from hikari import guilds
    from hikari import invites
    from hikari import messages
    from hikari import snowflakes
    from hikari import traits
    from hikari import users
    from hikari.api import event_manager
    from hikari.api import shard as shard_
    from hikari.api import special_endpoints
    from hikari.events import base_events
    from hikari.interactions import commands as command_interactions

    from tanjun import errors

    _T = typing.TypeVar("_T")
    _ExecutableT = typing.TypeVar("_ExecutableT", bound="Executable")
    _HooksT = typing.TypeVar("_HooksT", bound="Hooks")
    _Parser = typing.TypeVar("_Parser", bound="Parser")
    _ParameterT = typing.TypeVar("_ParameterT", bound="Parameter")


CommandT_co = typing.TypeVar("CommandT_co", bound="Executable[Context]", covariant=True)
ContextT = typing.TypeVar("ContextT", bound="Context")
ContextT_contra = typing.TypeVar("ContextT_contra", bound="Context", contravariant=True)

# To allow for stateless converters we accept both "Converter[...]" and "Type[StatelessConverter[...]]" where all the
# methods on "Type[StatelessConverter[...]]" need to be classmethods as it will not be initialised before calls are made
# to it.
ConverterSig = typing.Callable[..., typing.Union[typing.Awaitable[typing.Any], typing.Any]]
"""Type hint of a converter used within a parser instance.

This must be a callable or asynchronous callable which takes one position
`builtins.string` argument and returns the resultant value.
"""
# TODO: be more specific about the structure of command functions using a callable protocol

InteractionCommandFunctionSig = typing.Callable[
    ..., typing.Coroutine[typing.Any, typing.Any, typing.Optional["special_endpoints.InteractionResponseBuilder"]]
]

# TODO: MessageCommandFunctionT vs InteractionCommandFunctionT
MessageCommandFunctionSig = typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, None]]
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
    def author(self) -> users.User:
        raise NotImplementedError

    @property
    def channel_id(self) -> snowflakes.Snowflake:
        raise NotImplementedError

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
    def command(self: ContextT) -> typing.Optional[Executable[ContextT]]:
        raise NotImplementedError

    @command.setter
    def command(self: ContextT, _: Executable[ContextT], /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def event_service(self) -> typing.Optional[traits.EventManagerAware]:
        raise NotImplementedError

    @property
    def guild_id(self) -> typing.Optional[snowflakes.Snowflake]:
        raise NotImplementedError

    @property
    def is_human(self) -> bool:
        raise NotImplementedError

    @property
    def member(self) -> typing.Optional[guilds.Member]:
        raise NotImplementedError

    # TODO: rename to server_app
    @property
    @abc.abstractmethod
    def server_service(self) -> typing.Optional[traits.InteractionServerAware]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def rest_service(self) -> traits.RESTAware:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard_service(self) -> typing.Optional[traits.ShardAware]:
        raise NotImplementedError

    @property
    def triggering_name(self) -> str:
        raise NotImplementedError

    # async def edit_response(self) -> messages.Message:
    #     raise NotImplementedError

    async def fetch_channel(self) -> channels.PartialChannel:
        raise NotImplementedError

    async def fetch_guild(self) -> typing.Optional[guilds.Guild]:  # TODO: or raise?
        raise NotImplementedError

    # async def fetch_response(self) -> messages.Message:
    #     raise NotImplementedError

    def get_channel(self) -> typing.Optional[channels.PartialChannel]:
        raise NotImplementedError

    def get_guild(self) -> typing.Optional[guilds.Guild]:
        raise NotImplementedError

    async def execute(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        # attachment: undefined.UndefinedOr[files.Resourceish] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> typing.Optional[messages.Message]:
        raise NotImplementedError


class MessageContext(Context, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def command(self) -> typing.Optional[MessageCommand]:
        raise NotImplementedError

    @command.setter
    def command(self, _: MessageCommand, /) -> None:
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
    def message(self) -> messages.Message:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def shard(self) -> typing.Optional[shard_.GatewayShard]:
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

    async def execute(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        attachment: undefined.UndefinedOr[files.Resourceish] = undefined.UNDEFINED,
        attachments: undefined.UndefinedOr[typing.Sequence[files.Resourceish]] = undefined.UNDEFINED,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        nonce: undefined.UndefinedOr[str] = undefined.UNDEFINED,
        reply: undefined.UndefinedOr[snowflakes.SnowflakeishOr[messages.PartialMessage]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        mentions_reply: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
    ) -> messages.Message:
        raise NotImplementedError


class InteractionContext(Context, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def command(self) -> typing.Optional[InteractionCommand]:
        raise NotImplementedError

    @command.setter
    def command(self, _: InteractionCommand, /) -> None:
        raise NotImplementedError

    @property
    def interaction(self) -> command_interactions.CommandInteraction:
        raise NotImplementedError

    @property
    def result(self) -> typing.Optional[special_endpoints.InteractionResponseBuilder]:
        raise NotImplementedError

    @result.setter
    def result(self, _: typing.Optional[special_endpoints.InteractionResponseBuilder], /) -> None:
        raise NotImplementedError

    # TODO: somehow let it default to ack with message or just ack on a command basis for non-fast commands
    async def execute(
        self,
        content: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        *,
        tts: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        # TODO: attachment
        embed: undefined.UndefinedOr[embeds_.Embed] = undefined.UNDEFINED,
        embeds: undefined.UndefinedOr[typing.Sequence[embeds_.Embed]] = undefined.UNDEFINED,
        mentions_everyone: undefined.UndefinedOr[bool] = undefined.UNDEFINED,
        user_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[users.PartialUser], bool]
        ] = undefined.UNDEFINED,
        role_mentions: undefined.UndefinedOr[
            typing.Union[snowflakes.SnowflakeishSequence[guilds.PartialRole], bool]
        ] = undefined.UNDEFINED,
        with_source: bool = False,
    ) -> None:
        raise NotImplementedError


class Hooks(abc.ABC, typing.Generic[ContextT_contra]):
    __slots__: typing.Sequence[str] = ()

    @abc.abstractmethod
    def copy(self: _HooksT) -> _HooksT:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_error(
        self,
        ctx: ContextT_contra,
        /,
        exception: BaseException,
        *,
        hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_parser_error(
        self,
        ctx: ContextT_contra,
        /,
        exception: errors.ParserError,
        hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_post_execution(
        self, ctx: ContextT_contra, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_pre_execution(
        self, ctx: ContextT_contra, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None
    ) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def trigger_success(
        self, ctx: ContextT_contra, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks[ContextT_contra]]] = None
    ) -> None:
        raise NotImplementedError


class Executable(abc.ABC, typing.Generic[ContextT]):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def checks(self) -> typing.AbstractSet[CheckSig]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def hooks(self) -> typing.Optional[Hooks[ContextT]]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, _: typing.Optional[Hooks[ContextT]]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _ExecutableT) -> _ExecutableT:
        raise NotImplementedError

    @abc.abstractmethod
    def add_check(self, check: CheckSig[ContextT], /) -> None:
        raise NotImplementedError

    def remove_check(self, check: CheckSig[ContextT], /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def with_check(self, check: CheckSig[ContextT], /) -> CheckSig[ContextT]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self, ctx: ContextT, /, *, hooks: typing.Optional[typing.MutableSet[Hooks[ContextT]]] = None
    ) -> bool:
        raise NotImplementedError


# This doesn't apply to interaction commands as they only have one name
class FoundMessageCommand(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def command(self) -> MessageCommand:
        raise NotImplementedError

    @command.setter  # TODO: is this still necessary?
    def command(self, _: MessageCommand, /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @name.setter  # TODO: can we remove stuff like this from the public interface?
    def name(self, _: typing.Optional[str], /) -> None:
        raise NotImplementedError


class InteractionCommand(Executable[InteractionContext], abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @property
    def function(self) -> InteractionCommandFunctionT:
        raise NotImplementedError

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def parent(self) -> typing.Optional[InteractionCommandGroup]:
        raise NotImplementedError

    @parent.setter
    def parent(self, _: typing.Optional[InteractionCommandGroup], /) -> None:
        raise NotImplementedError

    @property
    def tracked_command(self) -> typing.Optional[command_interactions.Command]:
        raise NotImplementedError

    @tracked_command.setter
    def tracked_command(self, _: command_interactions.Command, /) -> None:
        raise NotImplementedError


class InteractionCommandGroup(InteractionCommand, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    def commands(self) -> typing.AbstractSet[InteractionCommand]:
        raise NotImplementedError

    def add_command(self, command: InteractionCommand, /) -> None:
        raise NotImplementedError

    def remove_command(self, command: InteractionCommand, /) -> None:
        raise NotImplementedError

    def with_command(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[CheckT]] = None,
        hooks: typing.Optional[Hooks[InteractionContext]] = None,
    ) -> typing.Callable[[InteractionCommandFunctionT], InteractionCommandFunctionT]:
        raise NotImplementedError


class MessageCommand(Executable[MessageContext], abc.ABC):
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
    def parent(self) -> typing.Optional[MessageCommandGroup]:
        raise NotImplementedError

    @parent.setter
    def parent(self, _: typing.Optional[MessageCommandGroup], /) -> None:
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

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    def check_context(
        self, ctx: MessageContext, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[FoundMessageCommand]:
        raise NotImplementedError

    def check_name(self, name: str, /) -> typing.Iterator[FoundMessageCommand]:
        raise NotImplementedError


class MessageCommandGroup(MessageCommand, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def commands(self) -> typing.AbstractSet[MessageCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_command(self: _T, command: MessageCommand, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_command(self, command: MessageCommand, /) -> None:
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


class Component(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def client(self) -> typing.Optional[Client]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def interaction_commands(self) -> typing.AbstractSet[InteractionCommand]:
        raise NotImplementedError

    @property
    def message_commands(self) -> typing.AbstractSet[MessageCommand]:
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
    def bind_client(self, client: Client, /) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    def check_message_context(
        self, ctx: MessageContext, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[FoundMessageCommand]:
        raise NotImplementedError

    def check_message_name(self, name: str, /) -> typing.Iterator[FoundMessageCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def open(self) -> None:
        raise NotImplementedError

    async def execute_interaction(
        self,
        ctx: InteractionContext,
        /,
        *,
        hooks: typing.Optional[typing.MutableSet[Hooks[InteractionContext]]] = None,
    ) -> bool:
        raise NotImplementedError

    async def execute_message(
        self, ctx: MessageContext, /, *, hooks: typing.Optional[typing.MutableSet[Hooks[MessageContext]]] = None
    ) -> bool:
        raise NotImplementedError


class Client(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def cached_rest(self) -> CachedREST:
        raise NotImplementedError

    # TODO: rename to cache_app
    @property
    def cache_service(self) -> typing.Optional[traits.CacheAware]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def components(self) -> typing.AbstractSet[Component]:
        raise NotImplementedError

    # TODO: rename to dispatch_app
    @property
    @abc.abstractmethod
    def event_service(self) -> typing.Optional[traits.EventManagerAware]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def prefixes(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    # TODO: rename to rest_app
    @property
    @abc.abstractmethod
    def rest_service(self) -> traits.RESTAware:
        raise NotImplementedError

    # TODO: rename to server_app
    @property
    @abc.abstractmethod
    def server_service(self) -> typing.Optional[traits.InteractionServerAware]:
        raise NotImplementedError

    # TODO: rename to shard_app
    @property
    @abc.abstractmethod
    def shard_service(self) -> typing.Optional[traits.ShardAware]:
        raise NotImplementedError

    @abc.abstractmethod
    def add_component(self: _T, component: Component, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_component(self, component: Component, /) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    # @abc.abstractmethod
    # def check_message_context(self, ctx: MessageContext, /) -> typing.AsyncIterator[FoundMessageCommand]:
    #     raise NotImplementedError

    @abc.abstractmethod
    def check_message_name(self, name: str, /) -> typing.Iterator[FoundMessageCommand]:
        raise NotImplementedError

    @abc.abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def open(self) -> None:
        raise NotImplementedError


class UndefinedDefaultT:
    __singleton: typing.Optional[UndefinedDefaultT] = None

    def __new__(cls) -> UndefinedDefaultT:
        if cls.__singleton is None:
            cls.__singleton = super().__new__(cls)

        return cls.__singleton

    def __repr__(self) -> str:
        return "NOTHING"

    def __bool__(self) -> typing.Literal[False]:
        return False


UNDEFINED_DEFAULT = UndefinedDefaultT()
"""A singleton used to represent no default for a parameter."""


class Parameter(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def converters(self) -> typing.Optional[typing.Sequence[ConverterSig]]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def default(self) -> typing.Union[typing.Any, UndefinedDefaultT]:
        raise NotImplementedError

    @default.setter
    def default(self, _: typing.Union[typing.Any, UndefinedDefaultT], /) -> None:
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
    async def convert(self, ctx: MessageContext, value: str) -> typing.Any:
        raise NotImplementedError


class Argument(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()


class Option(Parameter, abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def empty_value(self) -> typing.Union[typing.Any, UndefinedDefaultT]:
        raise NotImplementedError

    @empty_value.setter
    def empty_value(self, _: typing.Union[typing.Any, UndefinedDefaultT], /) -> None:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def names(self) -> typing.Sequence[str]:
        raise NotImplementedError

    @names.setter  # TODO: what?
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
    async def parse(
        self, ctx: MessageContext, /
    ) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
        raise NotImplementedError


class CachedREST(abc.ABC):
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

    async def fetch_guild(self, guild: snowflakes.SnowflakeishOr[guilds.PartialGuild], /) -> guilds.RESTGuild:
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
