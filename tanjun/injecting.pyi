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
    "cache_callback",
    "CallbackSig",
    "Getter",
    "Undefined",
    "UNDEFINED",
    "UndefinedOr",
    "injected",
    "Injected",
    "InjectorClient",
    "Injectable",
]

import abc
import typing
from collections import abc as collections

from . import conversion
from . import traits as tanjun_traits

_BaseInjectableValueT = typing.TypeVar("_BaseInjectableValueT", bound=BaseInjectableValue[typing.Any])
_T = typing.TypeVar("_T")
_InjectorClientT = typing.TypeVar("_InjectorClientT", bound=InjectorClient)
_ValueT = typing.TypeVar("_ValueT", bound=typing.Union[float, int, str])
CallbackSig = collections.Callable[..., tanjun_traits.MaybeAwaitableT[_T]]

class Getter(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    callback: collections.Callable[
        [tanjun_traits.Context], typing.Union[InjectableValue[_T], collections.Callable[[tanjun_traits.Context], _T]]
    ]
    name: str
    is_injecting: bool
    @typing.overload
    def __init__(
        self,
        callback: collections.Callable[[tanjun_traits.Context], InjectableValue[_T]],
        name: str,
        /,
        *,
        injecting: typing.Literal[True] = ...,
    ) -> None: ...
    @typing.overload
    def __init__(
        self,
        callback: collections.Callable[[tanjun_traits.Context], _T],
        name: str,
        /,
        *,
        injecting: typing.Literal[False],
    ) -> None: ...

class Undefined:
    def __bool__(self) -> typing.Literal[False]: ...
    def __new__(cls) -> Undefined: ...

UNDEFINED: typing.Final[Undefined]
UndefinedOr = typing.Union[Undefined, _T]

def check_injecting(callback: CallbackSig[typing.Any], /) -> bool: ...

_TypeT = type[_T]

class Injected(typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    callback: UndefinedOr[collections.Callable[[], tanjun_traits.MaybeAwaitableT[_T]]]
    type: UndefinedOr[_TypeT[_T]]
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
async def resolve_getters(
    ctx: tanjun_traits.Context, getters: collections.Iterable[Getter[typing.Any]]
) -> collections.Mapping[str, typing.Any]: ...

class InjectorClient:
    __slots__: typing.Union[str, collections.Iterable[str]]
    def __init__(self, client: tanjun_traits.Client, /) -> None: ...
    def add_type_dependency(
        self: _InjectorClientT, type_: type[_T], callback: CallbackSig[_T], /
    ) -> _InjectorClientT: ...
    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[CallbackSig[_T]]: ...
    def remove_type_dependency(self, type_: type[_T], callback: CallbackSig[_T], /) -> None: ...
    def add_callable_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT: ...
    def get_callable_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackSig[_T]]: ...
    def remove_callable_override(self, callback: CallbackSig[_T], /) -> None: ...
    def resolve_callback_to_getters(
        self, callback: CallbackSig[typing.Any], /
    ) -> collections.Iterator[Getter[typing.Any]]: ...

class Injectable(abc.ABC):
    __slots__: typing.Union[str, collections.Iterable[str]]
    @property
    @abc.abstractmethod
    def needs_injector(self) -> bool: ...
    @abc.abstractmethod
    def set_injector(self, client: InjectorClient, /) -> None: ...

class BaseInjectableValue(Injectable, typing.Generic[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    callback: CallbackSig[_T]
    injector: typing.Optional[InjectorClient]
    is_async: typing.Optional[bool]
    def __init__(self, callback: CallbackSig[_T], *, injector: typing.Optional[InjectorClient] = ...) -> None: ...
    def __eq__(self, other: typing.Any) -> bool: ...
    def __hash__(self) -> int: ...
    @property
    def needs_injector(self) -> bool: ...
    def copy(self: _BaseInjectableValueT) -> _BaseInjectableValueT: ...
    def set_injector(self, client: InjectorClient) -> None: ...
    async def call(self, *args: typing.Any, ctx: tanjun_traits.Context) -> _T: ...

class InjectableValue(BaseInjectableValue[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    async def __call__(self, ctx: tanjun_traits.Context, /) -> _T: ...

class InjectableCheck(BaseInjectableValue[bool]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool: ...

class InjectableConverter(BaseInjectableValue[_T]):
    __slots__: typing.Union[str, collections.Iterable[str]]
    async def __call__(self, value: conversion.ArgumentT, ctx: tanjun_traits.Context, /) -> _T: ...

def cache_callback(callback: CallbackSig[_T], /) -> collections.Callable[..., collections.Awaitable[_T]]: ...
