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

__all__: list[str] = [
    "AbstractDescriptor",
    "AbstractInjectionContext",
    "as_self_injecting",
    "BasicInjectionContext",
    "CallbackDescriptor",
    "CallbackSig",
    "Undefined",
    "UNDEFINED",
    "UndefinedOr",
    "inject",
    "injected",
    "Injected",
    "InjectorClient",
    "SelfInjectingCallback",
    "TypeDescriptor",
]

import abc
import typing
from collections import abc as collections

from . import abc as tanjun_abc

_BasicInjectionContextT = typing.TypeVar("_BasicInjectionContextT", bound="BasicInjectionContext")
_CallbackDescriptorT = typing.TypeVar("_CallbackDescriptorT", bound="CallbackDescriptor[typing.Any]")
_InjectorClientT = typing.TypeVar("_InjectorClientT", bound="InjectorClient")
_T = typing.TypeVar("_T")
CallbackSig = collections.Callable[..., tanjun_abc.MaybeAwaitableT[_T]]

class Undefined:
    def __bool__(self) -> typing.Literal[False]: ...
    def __new__(cls) -> Undefined: ...

UNDEFINED: typing.Final[Undefined]
UndefinedOr = typing.Union[Undefined, _T]

class AbstractInjectionContext(abc.ABC):
    __slots__: typing.Union[str, collections.Iterable[str]]
    @property
    @abc.abstractmethod
    def injection_client(self) -> InjectorClient: ...
    @abc.abstractmethod
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None: ...
    @abc.abstractmethod
    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]: ...
    @abc.abstractmethod
    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[_T]: ...

class BasicInjectionContext(AbstractInjectionContext):
    __slots__: typing.Union[str, collections.Iterable[str]]
    _special_case_types: dict[type[typing.Any], typing.Any]
    def __init__(self, client: InjectorClient, /) -> None: ...
    @property
    def injection_client(self) -> InjectorClient: ...
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None: ...
    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]: ...
    def get_type_dependency(self, _: type[_T], /) -> UndefinedOr[_T]: ...
    def _set_type_special_case(
        self: _BasicInjectionContextT, type_: type[_T], value: _T, /
    ) -> _BasicInjectionContextT: ...
    def _remove_type_special_case(
        self: _BasicInjectionContextT, type_: type[typing.Any], /
    ) -> _BasicInjectionContextT: ...

class AbstractDescriptor(abc.ABC, typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    @property
    @abc.abstractmethod
    def needs_injector(self) -> bool: ...
    @abc.abstractmethod
    async def resolve_with_command_context(self, ctx: tanjun_abc.Context, /) -> _T: ...
    @abc.abstractmethod
    async def resolve_without_injector(self) -> _T: ...
    @abc.abstractmethod
    async def resolve(self, ctx: AbstractInjectionContext, /) -> _T: ...

class CallbackDescriptor(AbstractDescriptor[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, callback: CallbackSig[_T], /) -> None: ...
    @property
    def callback(self) -> CallbackSig[_T]: ...
    @property
    def needs_injector(self) -> bool: ...
    def copy(self: _CallbackDescriptorT, *, _new: bool = ...) -> _CallbackDescriptorT: ...
    def overwrite_callback(self, callback: CallbackSig[_T], /) -> None: ...
    async def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, /, *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...
    async def resolve_without_injector(self, *args: typing.Any, **kwargs: typing.Any) -> _T: ...
    async def resolve(self, ctx: AbstractInjectionContext, /, *args: typing.Any, **kwargs: typing.Any) -> _T: ...

class SelfInjectingCallback(CallbackDescriptor[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, injector_client: InjectorClient, callback: CallbackSig[_T], /) -> None: ...
    async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None: ...

def as_self_injecting(
    injector_client: InjectorClient, /
) -> collections.Callable[[CallbackSig[_T]], SelfInjectingCallback[_T]]: ...

class TypeDescriptor(AbstractDescriptor[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, type_: _TypeT[_T], /) -> None: ...
    @property
    def needs_injector(self) -> bool: ...
    @property
    def type(self) -> _TypeT[_T]: ...
    async def resolve_with_command_context(self, ctx: tanjun_abc.Context, /) -> _T: ...
    async def resolve_without_injector(self) -> _T: ...
    async def resolve(self, ctx: AbstractInjectionContext, /) -> _T: ...

_TypeT = type[_T]

class Injected(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    callback: typing.Optional[CallbackSig[_T]]
    type: typing.Optional[_TypeT[_T]]
    @typing.overload
    def __init__(self, *, callback: collections.Callable[..., collections.Awaitable[_T]]) -> None: ...
    @typing.overload
    def __init__(self, *, callback: collections.Callable[..., _T]) -> None: ...
    @typing.overload
    def __init__(self, *, type: _TypeT[_T]) -> None: ...

@typing.overload
def inject(*, callback: collections.Callable[..., collections.Awaitable[_T]]) -> _T: ...
@typing.overload
def inject(*, callback: collections.Callable[..., _T]) -> _T: ...
@typing.overload
def inject(*, type: _TypeT[_T]) -> _T: ...
@typing.overload
def injected(*, callback: collections.Callable[..., collections.Awaitable[_T]]) -> _T: ...
@typing.overload
def injected(*, callback: collections.Callable[..., _T]) -> _T: ...
@typing.overload
def injected(*, type: _TypeT[_T]) -> _T: ...

class InjectorClient:
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self) -> None: ...
    def set_type_dependency(self: _InjectorClientT, type_: type[_T], value: _T, /) -> _InjectorClientT: ...
    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[_T]: ...
    def remove_type_dependency(self: _InjectorClientT, type_: type[typing.Any], /) -> _InjectorClientT: ...
    def set_callback_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT: ...
    def get_callback_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackDescriptor[_T]]: ...
    def remove_callback_override(self: _InjectorClientT, callback: CallbackSig[_T], /) -> _InjectorClientT: ...

class _EmptyInjectorClient(InjectorClient):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def set_type_dependency(self: _InjectorClientT, _: type[_T], __: _T, /) -> _InjectorClientT: ...
    def get_type_dependency(self, _: type[typing.Any], /) -> Undefined: ...
    def remove_type_dependency(self: _InjectorClientT, type_: type[typing.Any], /) -> _InjectorClientT: ...
    def set_callback_override(
        self: _InjectorClientT, _: CallbackSig[_T], __: CallbackSig[_T], /
    ) -> _InjectorClientT: ...
    def get_callback_override(self, _: CallbackSig[_T], /) -> None: ...
    def remove_callback_override(self: _InjectorClientT, callback: CallbackSig[_T], /) -> _InjectorClientT: ...

_EMPTY_CLIENT: typing.Final[_EmptyInjectorClient]

class _EmptyContext(AbstractInjectionContext):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self) -> None: ...
    @property
    def injection_client(self) -> InjectorClient: ...
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None: ...
    def get_cached_result(self, _: CallbackSig[typing.Any], /) -> Undefined: ...
    def get_type_dependency(self, _: type[typing.Any], /) -> Undefined: ...
