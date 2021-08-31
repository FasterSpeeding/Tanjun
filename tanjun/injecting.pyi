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
    "AbstractInjectionContext",
    "BasicInjectionContext",
    "CallbackDescriptor",
    "Descriptor",
    "cache_callback",
    "CallbackSig",
    "Undefined",
    "UNDEFINED",
    "UndefinedOr",
    "injected",
    "Injected",
    "InjectorClient",
    "TypeDescriptor",
]

import abc
import typing
from collections import abc as collections

from . import abc as tanjun_abc
from . import conversion

_BaseInjectableValueT = typing.TypeVar("_BaseInjectableValueT", bound="BaseInjectableValue")
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
    @abc.abstractmethod
    def injection_client(self) -> InjectorClient: ...
    @abc.abstractmethod
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None: ...
    @abc.abstractmethod
    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]: ...
    @abc.abstractmethod
    def get_type_special_case(self, type_: type[_T], /) -> UndefinedOr[_T]: ...

class BasicInjectionContext(AbstractInjectionContext):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, client: InjectorClient, /) -> None: ...
    def injection_client(self) -> InjectorClient: ...
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None: ...
    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]: ...
    def get_type_special_case(self, _: type[_T], /) -> UndefinedOr[_T]: ...

class CallbackDescriptor(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, callback: CallbackSig[_T], /) -> None: ...
    @property
    def callback(self) -> CallbackSig[_T]: ...
    @property
    def needs_injector(self) -> bool: ...
    async def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...
    async def resolve_without_injector(self, *args: typing.Any, **kwargs: typing.Any) -> _T: ...
    async def resolve(self, ctx: AbstractInjectionContext, *args: typing.Any, **kwargs: typing.Any) -> _T: ...

class TypeDescriptor(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, type_: _TypeT[_T], /) -> None: ...
    @property
    def type(self) -> _TypeT[_T]: ...
    async def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...
    @staticmethod
    async def resolve(ctx: AbstractInjectionContext, /) -> _T: ...

class Descriptor(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    @typing.overload
    def __init__(
        self,
        *,
        callback: typing.Optional[CallbackSig[_T]] = None,
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        *,
        type: typing.Optional[_TypeT[_T]] = None,  # noqa A002
    ) -> None: ...
    @property
    def callback(self) -> typing.Optional[CallbackSig[_T]]: ...
    @property
    def needs_injector(self) -> bool: ...
    @property
    def type(self) -> typing.Optional[_TypeT[typing.Any]]: ...
    async def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, *args: typing.Any, **kwargs: typing.Any
    ) -> _T: ...
    async def resolve_without_injector(self, *args: typing.Any, **kwargs: typing.Any) -> _T: ...
    async def resolve(self, ctx: AbstractInjectionContext, *args: typing.Any, **kwargs: typing.Any) -> _T: ...

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
def injected(*, callback: collections.Callable[..., collections.Awaitable[_T]]) -> _T: ...
@typing.overload
def injected(*, callback: collections.Callable[..., _T]) -> _T: ...
@typing.overload
def injected(*, type: _TypeT[_T]) -> _T: ...

class InjectorClient:
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self) -> None: ...
    def add_type_dependency(
        self: _InjectorClientT, type_: type[_T], callback: CallbackSig[_T], /
    ) -> _InjectorClientT: ...
    def get_type_dependency(self, type_: type[_T], /) -> typing.Optional[CallbackSig[_T]]: ...
    def get_type_special_case(self, type_: type[_T], /) -> UndefinedOr[_T]: ...
    def remove_type_dependency(self, type_: type[typing.Any], /) -> None: ...
    def add_callback_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT: ...
    def get_callback_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackSig[_T]]: ...
    def remove_callback_override(self, callback: CallbackSig[_T], /) -> None: ...

class BaseInjectableValue(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, callback: CallbackSig[_T], /) -> None: ...
    def __eq__(self, other: typing.Any) -> bool: ...
    def __hash__(self) -> int: ...
    @property
    def callback(self) -> CallbackSig[_T]: ...
    @property
    def descriptor(self) -> Descriptor[_T]: ...
    @property
    def needs_injector(self) -> bool: ...
    def copy(self: _BaseInjectableValueT) -> _BaseInjectableValueT: ...
    def overwrite_callback(self, callback: CallbackSig[_T], /) -> None: ...

class InjectableValue(BaseInjectableValue[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    async def __call__(self, ctx: tanjun_abc.Context, /) -> _T: ...

class InjectableCheck(BaseInjectableValue[bool]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool: ...

class InjectableConverter(BaseInjectableValue[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    async def __call__(self, value: conversion.ArgumentT, ctx: tanjun_abc.Context, /) -> _T: ...

def cache_callback(callback: CallbackSig[_T], /) -> collections.Callable[..., collections.Awaitable[_T]]: ...
