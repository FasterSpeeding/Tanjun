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
import asyncio
import collections.abc as collections
import copy
import inspect
import typing

import hikari
from hikari import traits as hikari_traits

from . import abc as tanjun_abc
from . import conversion
from . import errors

if typing.TYPE_CHECKING:
    _BaseInjectableValueT = typing.TypeVar("_BaseInjectableValueT", bound="BaseInjectableValue[typing.Any]")

_InjectorClientT = typing.TypeVar("_InjectorClientT", bound="InjectorClient")
_T = typing.TypeVar("_T")
CallbackSig = collections.Callable[..., tanjun_abc.MaybeAwaitableT[_T]]


class Getter(typing.Generic[_T]):
    __slots__ = ("callback", "is_injecting", "name")

    @typing.overload
    def __init__(
        self,
        callback: collections.Callable[[tanjun_abc.Context], InjectableValue[_T]],
        name: str,
        /,
        *,
        injecting: typing.Literal[True] = True,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        callback: collections.Callable[[tanjun_abc.Context], _T],
        name: str,
        /,
        *,
        injecting: typing.Literal[False],
    ) -> None:
        ...

    def __init__(
        self,
        callback: collections.Callable[[tanjun_abc.Context], typing.Union[_T, InjectableValue[_T]]],
        name: str,
        /,
        *,
        injecting: bool = True,
    ) -> None:
        self.callback = callback
        self.is_injecting = injecting
        self.name = name


class Undefined:
    __instance: Undefined

    def __bool__(self) -> typing.Literal[False]:
        return False

    def __new__(cls) -> Undefined:
        try:
            return cls.__instance

        except AttributeError:
            new = super().__new__(cls)
            assert isinstance(new, Undefined)
            cls.__instance = new
            return cls.__instance


UNDEFINED: typing.Final[Undefined] = Undefined()
UndefinedOr = typing.Union[Undefined, _T]


def check_injecting(callback: CallbackSig[typing.Any], /) -> bool:
    try:
        parameters = inspect.signature(callback).parameters.values()
    except ValueError:  # If we can't inspect it then we have to assume this is a NO
        return False
    else:
        return any(isinstance(parameter.default, Injected) for parameter in parameters)


_TypeT = type[_T]


class Injected(typing.Generic[_T]):
    __slots__ = ("callback", "type")

    def __init__(
        self,
        *,
        callback: UndefinedOr[CallbackSig[_T]] = UNDEFINED,
        type: UndefinedOr[_TypeT[_T]] = UNDEFINED,  # noqa: A002
    ) -> None:  # TODO: add default/factory to this?
        if callback is UNDEFINED and type is UNDEFINED:
            raise ValueError("Must specify one of `callback` or `type`")

        if callback is not UNDEFINED and type is not UNDEFINED:
            raise ValueError("Only one of `callback` or `type` can be specified")

        self.callback = callback
        self.type = type


def injected(
    *,
    callback: UndefinedOr[CallbackSig[_T]] = UNDEFINED,
    type: UndefinedOr[_TypeT[_T]] = UNDEFINED,  # noqa: A002
) -> Injected[_T]:
    return Injected(callback=callback, type=type)


async def resolve_getters(
    ctx: tanjun_abc.Context, getters: collections.Iterable[Getter[typing.Any]]
) -> collections.Mapping[str, typing.Any]:
    results: dict[str, typing.Any] = {}

    for getter in getters:
        result = getter.callback(ctx)
        if not getter.is_injecting:
            assert not isinstance(result, InjectableValue)
            results[getter.name] = result
            continue

        else:
            assert isinstance(result, InjectableValue)
            results[getter.name] = await result(ctx)

    return results


class InjectorClient:
    __slots__ = ("_callback_overrides", "_client", "_type_dependencies")

    def __init__(self, client: tanjun_abc.Client, /) -> None:
        self._callback_overrides: dict[CallbackSig[typing.Any], InjectableValue[typing.Any]] = {}
        self._client = client
        self._type_dependencies: dict[type[typing.Any], InjectableValue[typing.Any]] = {}

    def add_type_dependency(self: _InjectorClientT, type_: type[_T], callback: CallbackSig[_T], /) -> _InjectorClientT:
        self._type_dependencies[type_] = InjectableValue(callback, injector=self)
        return self

    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[CallbackSig[_T]]:
        return self._type_dependencies.get(type_, UNDEFINED)

    def remove_type_dependency(self, type_: type[_T], callback: CallbackSig[_T], /) -> None:
        del self._type_dependencies[type_]

    def add_callable_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT:
        self._callback_overrides[callback] = InjectableValue(override, injector=self)
        return self

    def get_callable_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackSig[_T]]:
        return self._callback_overrides.get(callback)

    def remove_callable_override(self, callback: CallbackSig[_T], /) -> None:
        del self._callback_overrides[callback]

    def _make_callback_getter(self, callback: CallbackSig[_T], name: str, /) -> Getter[_T]:
        default = InjectableValue(callback, injector=self)

        def get(_: tanjun_abc.Context) -> InjectableValue[_T]:
            return self._callback_overrides.get(callback, default)

        return Getter(get, name, injecting=True)

    def _make_type_getter(self, type_: type[_T], name: str, /) -> Getter[_T]:
        for match, function in _TYPE_SPECIAL_CASES.items():
            if inspect.isclass(match) and issubclass(type_, match):

                def get_special_cased(ctx: tanjun_abc.Context) -> _T:
                    if (result := self._type_dependencies.get(type_, ...)) is not ...:
                        return typing.cast(_T, result)

                    if (result := function(ctx, self)) is not UNDEFINED:
                        return typing.cast(_T, result)

                    raise errors.MissingDependencyError(
                        f"Couldn't resolve injected type {type_} to actual value"
                    ) from None

                return Getter(get_special_cased, name, injecting=False)

        def get_injectable(_: tanjun_abc.Context) -> InjectableValue[_T]:
            try:
                return self._type_dependencies[type_]

            except KeyError:
                raise errors.MissingDependencyError(f"Couldn't resolve injected type {type_} to actual value") from None

        return Getter(get_injectable, name, injecting=True)

    def resolve_callback_to_getters(
        self, callback: CallbackSig[typing.Any], /
    ) -> collections.Iterator[Getter[typing.Any]]:
        try:
            parameters = inspect.signature(callback).parameters.items()
        except ValueError:  # If we can't inspect it then we have to assume this is a NO
            return

        for name, parameter in parameters:
            if parameter.default is parameter.empty:
                continue

            if not isinstance(parameter.default, Injected):
                continue

            if parameter.kind is parameter.POSITIONAL_ONLY:
                raise ValueError("Injected positional only arguments are not supported")

            if parameter.default.callback is not UNDEFINED:
                assert not isinstance(parameter.default.callback, Undefined)
                yield self._make_callback_getter(parameter.default.callback, name)

            else:
                assert not isinstance(parameter.default.type, Undefined)
                yield self._make_type_getter(parameter.default.type, name)


_TYPE_SPECIAL_CASES: dict[
    type[typing.Any],
    collections.Callable[[tanjun_abc.Context, InjectorClient], UndefinedOr[typing.Any]],
] = {
    tanjun_abc.Client: lambda ctx, _: ctx.client,
    tanjun_abc.Component: lambda ctx, _: ctx.component or UNDEFINED,
    tanjun_abc.Context: lambda ctx, _: ctx,
    InjectorClient: lambda _, cli: cli,
    hikari.api.Cache: lambda ctx, _: ctx.cache or UNDEFINED,
    hikari.api.RESTClient: lambda ctx, _: ctx.rest,
    hikari_traits.ShardAware: lambda ctx, _: ctx.shards or UNDEFINED,
    hikari.api.EventManager: lambda ctx, _: ctx.events or UNDEFINED,
    hikari.api.InteractionServer: lambda ctx, _: ctx.server or UNDEFINED,
}


class Injectable(abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def needs_injector(self) -> bool:
        ...

    @abc.abstractmethod
    def set_injector(self, client: InjectorClient, /) -> None:
        ...


class BaseInjectableValue(Injectable, typing.Generic[_T]):
    __slots__ = ("callback", "_cached_getters", "injector", "is_async", "_needs_injector")

    def __init__(self, callback: CallbackSig[_T], *, injector: typing.Optional[InjectorClient] = None) -> None:
        self._cached_getters: typing.Optional[list[Getter[typing.Any]]] = None
        self.callback = callback
        self.injector = injector
        self.is_async: typing.Optional[bool] = None
        self._needs_injector = check_injecting(self.callback)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __eq__(self, other: typing.Any) -> bool:
        return bool(self.callback == other)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __hash__(self) -> int:
        return hash(self.callback)

    @property
    def needs_injector(self) -> bool:
        return self._needs_injector

    def copy(self: _BaseInjectableValueT, *, _new: bool = True) -> _BaseInjectableValueT:
        if not _new:
            self._cached_getters = None
            self.callback = copy.copy(self.callback)
            self.is_async = None
            return self

        return copy.copy(self).copy(_new=False)

    def set_injector(self, client: InjectorClient, /) -> None:
        if self.injector:
            raise RuntimeError("Injector already set for this check")

        self.injector = client

    async def call(self, *args: typing.Any, ctx: tanjun_abc.Context) -> _T:
        if self._needs_injector:
            if self.injector is None:
                raise RuntimeError("Cannot call this injectable callback before the injector has been set")

            if self._cached_getters is None:
                self._cached_getters = list(self.injector.resolve_callback_to_getters(self.callback))

            result = self.callback(*args, **await resolve_getters(ctx, self._cached_getters))

        else:
            result = self.callback(*args)

        if self.is_async is None:
            self.is_async = isinstance(result, collections.Awaitable)

        if self.is_async:
            assert isinstance(result, collections.Awaitable)
            return typing.cast(_T, await result)

        return typing.cast(_T, result)


class InjectableValue(BaseInjectableValue[_T]):
    __slots__ = ()

    async def __call__(self, ctx: tanjun_abc.Context, /) -> _T:
        return await self.call(ctx=ctx)


class InjectableCheck(BaseInjectableValue[bool]):
    __slots__ = ()

    async def __call__(self, ctx: tanjun_abc.Context, /) -> bool:
        if result := await self.call(ctx, ctx=ctx):
            return result

        raise errors.FailedCheck


class InjectableConverter(BaseInjectableValue[_T]):
    __slots__ = ("_is_base_converter",)

    def __init__(self, callback: CallbackSig[_T], *, injector: typing.Optional[InjectorClient] = None) -> None:
        super().__init__(callback, injector=injector)
        self._is_base_converter = isinstance(self.callback, conversion.BaseConverter)

    async def __call__(self, value: conversion.ArgumentT, ctx: tanjun_abc.Context, /) -> _T:
        if self._is_base_converter:
            assert isinstance(self.callback, conversion.BaseConverter)
            return typing.cast(_T, await self.callback(value, ctx))

        return await self.call(value, ctx=ctx)


class _CacheCallback(typing.Generic[_T]):
    __slots__ = ("_callback", "_lock", "_result")

    def __init__(self, callback: CallbackSig[_T], /) -> None:
        self._callback = callback
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Union[_T, Undefined] = UNDEFINED

    async def __call__(
        self,
        # Positional arg(s) may be guaranteed under some contexts so we want to pass those through.
        *args: typing.Any,
        ctx: tanjun_abc.Context = Injected(type=tanjun_abc.Context),  # type: ignore[assignment]
        injector: InjectorClient = Injected(type=InjectorClient),  # type: ignore[assignment]
    ) -> _T:
        if self._result is not UNDEFINED:
            assert not isinstance(self._result, Undefined)
            return self._result

        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._result is not UNDEFINED:
                assert not isinstance(self._result, Undefined)
                return self._result

            getters = injector.resolve_callback_to_getters(self._callback)
            temp_result = self._callback(*args, **await resolve_getters(ctx, getters))

            if isinstance(temp_result, collections.Awaitable):
                self._result = typing.cast(_T, await temp_result)
            else:
                self._result = temp_result

        return self._result


def cache_callback(callback: CallbackSig[_T], /) -> collections.Callable[..., collections.Awaitable[_T]]:
    return _CacheCallback(callback)
