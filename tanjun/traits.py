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

__all__: typing.Sequence[str] = []

import typing

if typing.TYPE_CHECKING:
    from hikari import messages
    from hikari import traits
    from hikari.api import event_dispatcher
    from hikari.api import shard
    from hikari.events import base_events

    from tanjun import errors


ConversionHookT = typing.Callable[
    ["Context", "errors.ConversionError"], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
ErrorHookT = typing.Callable[
    ["Context", BaseException], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
HookT = typing.Callable[["Context"], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]]
PreExecutionHookT = typing.Callable[..., typing.Union[typing.Coroutine[typing.Any, typing.Any, bool], bool]]
CheckT = typing.Callable[["Context"], typing.Union[bool, typing.Coroutine[typing.Any, typing.Any, bool]]]
ValueT = typing.TypeVar("ValueT", covariant=True)


@typing.runtime_checkable
class Context(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    @property
    def client(self) -> Client:
        raise NotImplementedError

    @property
    def command(self) -> ExecutableCommand:
        raise NotImplementedError

    @command.setter
    def command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @property
    def content(self) -> str:
        raise NotImplementedError

    @content.setter
    def content(self, content: str, /) -> None:
        raise NotImplementedError

    @property
    def message(self) -> messages.Message:
        raise NotImplementedError

    @property
    def triggering_prefix(self) -> typing.Optional[str]:
        raise NotImplementedError

    @triggering_prefix.setter
    def triggering_prefix(self, triggering_prefix: str, /) -> None:
        raise NotImplementedError

    @property
    def triggering_name(self) -> typing.Optional[str]:
        raise NotImplementedError

    @triggering_name.setter
    def triggering_name(self, triggering_name: str, /) -> None:
        raise NotImplementedError

    # @property
    # def shard(self) -> shard.GatewayShard:
    #     raise NotImplementedError


@typing.runtime_checkable
class Converter(typing.Protocol[ValueT]):
    __slots__: typing.Sequence[str] = ()

    async def convert(self, ctx: Context, argument: str, /) -> ValueT:
        raise NotImplementedError

    def bind_component(cls, client: Client, component: Component, /) -> None:
        raise NotImplementedError


@typing.runtime_checkable
class Hooks(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    def on_conversion_error(self, hook: typing.Optional[ConversionHookT], /) -> typing.Optional[ConversionHookT]:
        raise NotImplementedError

    def on_error(self, hook: typing.Optional[ErrorHookT], /) -> typing.Optional[ErrorHookT]:
        raise NotImplementedError

    def post_execution(self, hook: typing.Optional[HookT], /) -> typing.Optional[HookT]:
        raise NotImplementedError

    def pre_execution(self, hook: typing.Optional[PreExecutionHookT], /) -> typing.Optional[PreExecutionHookT]:
        raise NotImplementedError

    def on_success(self, hook: typing.Optional[HookT], /) -> typing.Optional[HookT]:
        raise NotImplementedError

    async def trigger_conversion_error(
        self,
        ctx: Context,
        /,
        exception: errors.ConversionError,
        hooks: typing.Optional[typing.AbstractSet[Hooks]] = None,
    ) -> None:
        raise NotImplementedError

    async def trigger_error(
        self, ctx: Context, /, exception: BaseException, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    async def trigger_post_execution(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError

    async def trigger_pre_execution(
        self,
        ctx: Context,
        /,
        *,
        args: typing.Sequence[str],
        kwargs: typing.Mapping[str, typing.Any],
        hooks: typing.Optional[typing.AbstractSet[Hooks]] = None,
    ) -> bool:
        raise NotImplementedError

    async def trigger_success(
        self, ctx: Context, /, *, hooks: typing.Optional[typing.AbstractSet[Hooks]] = None
    ) -> None:
        raise NotImplementedError


@typing.runtime_checkable
class Executable(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    @property
    def hooks(self) -> typing.Optional[Hooks]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, hooks: typing.Optional[Hooks]) -> None:
        raise NotImplementedError

    # As far as MYPY is concerned, unless you explicitly yield within an async function typed as returning an
    # AsyncIterator/AsyncGenerator you are returning an AsyncIterator/AsyncGenerator as the result of a coroutine.
    def check_context(self, ctx: Context, /) -> typing.AsyncIterator[FoundCommand]:
        raise NotImplementedError

    def check_name(self, name: str, /) -> typing.Iterator[FoundCommand]:
        raise NotImplementedError

    # TODO: raise here?
    async def execute(self, ctx: Context, /, *, hooks: typing.Optional[typing.MutableSet[Hooks]] = None) -> bool:
        raise NotImplementedError


@typing.runtime_checkable
class FoundCommand(typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    @property
    def command(self) -> ExecutableCommand:
        raise NotImplementedError

    @command.setter
    def command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @name.setter
    def name(self, name: typing.Optional[str], /) -> None:
        raise NotImplementedError

    @property
    def prefix(self) -> typing.Optional[str]:
        raise NotImplementedError

    @prefix.setter
    def prefix(self, prefix: typing.Optional[str], /) -> None:
        raise NotImplementedError


@typing.runtime_checkable
class ExecutableCommand(Executable, typing.Protocol):
    __slots__: typing.Sequence[str] = ()

    @property
    def component(self) -> typing.Optional[Component]:
        raise NotImplementedError

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        raise NotImplementedError

    @property
    def names(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    def add_name(self, name: str, /) -> None:
        raise NotImplementedError

    def remove_name(self, name: str, /) -> None:
        raise NotImplementedError

    def bind_component(self, component: Component, /) -> None:
        raise NotImplementedError


@typing.runtime_checkable
class Component(Executable, typing.Protocol):
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
    ) -> typing.AbstractSet[typing.Tuple[typing.Type[base_events.Event], event_dispatcher.CallbackT[typing.Any]]]:
        raise NotImplementedError

    def add_command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    def remove_command(self, command: ExecutableCommand, /) -> None:
        raise NotImplementedError

    def add_listener(
        self, event: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any]
    ) -> None:
        raise NotImplementedError

    def remove_listener(
        self, event: typing.Type[base_events.Event], listener: event_dispatcher.CallbackT[typing.Any]
    ) -> None:
        raise NotImplementedError

    def bind_client(self, client: Client) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def open(self) -> None:
        raise NotImplementedError


@typing.runtime_checkable
class Client(typing.Protocol):
    @property
    def cache(self) -> typing.Optional[traits.CacheAware]:
        raise NotImplementedError

    @property
    def components(self) -> typing.AbstractSet[Component]:
        raise NotImplementedError

    @property
    def dispatch(self) -> traits.DispatcherAware:
        raise NotImplementedError

    @property
    def prefixes(self) -> typing.AbstractSet[str]:
        raise NotImplementedError

    @property  # TODO: keep this?
    def rest(self) -> traits.RESTAware:
        raise NotImplementedError

    @property
    def hooks(self) -> typing.Optional[Hooks]:
        raise NotImplementedError

    @hooks.setter
    def hooks(self, hooks: typing.Optional[Hooks]) -> None:
        raise NotImplementedError

    def add_component(self, component: Component, /) -> None:
        raise NotImplementedError

    def remove_component(self, component: Component, /) -> None:
        raise NotImplementedError

    def add_prefix(self, prefix: str, /) -> None:
        raise NotImplementedError

    def remove_prefix(self, prefix: str, /) -> None:
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
