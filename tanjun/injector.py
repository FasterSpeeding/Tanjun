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

__all__: typing.Sequence[str] = [
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
import collections.abc as collections
import copy
import inspect
import typing

from hikari import traits as hikari_traits
from hikari.api import cache as cache_api
from hikari.api import event_manager as event_manager_api
from hikari.api import interaction_server as interaction_server_api
from hikari.api import rest as rest_api

from . import conversion
from . import errors
from . import traits as tanjun_traits

if typing.TYPE_CHECKING:
    _BaseInjectableValueT = typing.TypeVar("_BaseInjectableValueT", bound="BaseInjectableValue[typing.Any]")

_InjectorClientT = typing.TypeVar("_InjectorClientT", bound="InjectorClient")
_T = typing.TypeVar("_T")
CallbackSig = typing.Callable[..., typing.Union[typing.Awaitable[_T], _T]]


class Getter(typing.Generic[_T]):
    __slots__: typing.Sequence[str] = ("callback", "is_injecting", "name")

    @typing.overload
    def __init__(
        self,
        callback: typing.Callable[["tanjun_traits.Context"], InjectableValue[_T]],
        name: str,
        /,
        *,
        injecting: typing.Literal[True] = True,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        callback: typing.Callable[["tanjun_traits.Context"], _T],
        name: str,
        /,
        *,
        injecting: typing.Literal[False],
    ) -> None:
        ...

    def __init__(
        self,
        callback: typing.Callable[[tanjun_traits.Context], typing.Union[_T, InjectableValue[_T]]],
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


class Injected(typing.Generic[_T]):
    __slots__: typing.Sequence[str] = ("callback", "type")

    def __init__(
        self,
        *,
        callback: UndefinedOr[CallbackSig[_T]] = UNDEFINED,
        type: UndefinedOr[typing.Type[_T]] = UNDEFINED,
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
    type: UndefinedOr[typing.Type[_T]] = UNDEFINED,
) -> Injected[_T]:
    return Injected(callback=callback, type=type)


async def resolve_getters(
    ctx: tanjun_traits.Context, getters: typing.Iterable[Getter[typing.Any]]
) -> typing.Mapping[str, typing.Any]:
    results: typing.Dict[str, typing.Any] = {}

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
    __slots__: typing.Sequence[str] = (
        "_callback_overrides",
        "_client",
        "_component_mapping_values",
        "_component_mapping",
        "_type_dependencies",
    )

    def __init__(self, client: tanjun_traits.Client, /) -> None:
        self._callback_overrides: typing.Dict[CallbackSig[typing.Any], InjectableValue[typing.Any]] = {}
        self._client = client
        self._component_mapping_values: typing.Set[tanjun_traits.Component] = set()
        self._component_mapping: typing.Dict[typing.Type[tanjun_traits.Component], tanjun_traits.Component] = {}
        self._type_dependencies: typing.Dict[typing.Type[typing.Any], InjectableValue[typing.Any]] = {}

    def add_type_dependency(
        self: _InjectorClientT, type_: typing.Type[_T], callback: CallbackSig[_T], /
    ) -> _InjectorClientT:
        self._type_dependencies[type_] = InjectableValue(callback, injector=self)
        return self

    def get_type_dependency(self, type_: typing.Type[_T], /) -> UndefinedOr[CallbackSig[_T]]:
        return self._type_dependencies.get(type_, UNDEFINED)

    def add_callable_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT:
        self._callback_overrides[callback] = InjectableValue(override, injector=self)
        return self

    def get_callable_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackSig[_T]]:
        return self._callback_overrides.get(callback)

    def get_component_mapping(self) -> typing.Mapping[typing.Type[tanjun_traits.Component], tanjun_traits.Component]:
        if self._component_mapping_values != self._client.components:
            self._component_mapping.clear()
            self._component_mapping = {type(component): component for component in self._client.components}
            self._component_mapping_values = set(self._client.components)

        return self._component_mapping

    def _make_callback_getter(self, callback: CallbackSig[_T], name: str, /) -> Getter[_T]:
        default = InjectableValue(callback, injector=self)

        def get(_: tanjun_traits.Context) -> InjectableValue[_T]:
            return self._callback_overrides.get(callback, default)

        return Getter(get, name, injecting=True)

    def _make_type_getter(self, type_: typing.Type[_T], name: str, /) -> Getter[_T]:
        for match, function in _TYPE_GETTER_OVERRIDES.items():
            if inspect.isclass(match) and issubclass(type_, match):

                def get_simple(ctx: tanjun_traits.Context) -> _T:
                    if (result := function(ctx, self, type_)) is not UNDEFINED:
                        return typing.cast(_T, result)

                    raise errors.MissingDependencyError(
                        f"Couldn't resolve injected type {type_} to actual value"
                    ) from None

                return Getter(get_simple, name, injecting=False)

        def get_injectable(_: tanjun_traits.Context) -> InjectableValue[_T]:
            try:
                return self._type_dependencies[type_]

            except KeyError:
                raise errors.MissingDependencyError(f"Couldn't resolve injected type {type_} to actual value") from None

        return Getter(get_injectable, name, injecting=True)

    def resolve_callback_to_getters(self, callback: CallbackSig[typing.Any], /) -> typing.Iterator[Getter[typing.Any]]:
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
                assert parameter.default.type is not UNDEFINED
                yield self._make_type_getter(parameter.default.type, name)


_TYPE_GETTER_OVERRIDES: typing.Dict[
    typing.Type[typing.Any],
    typing.Callable[[tanjun_traits.Context, InjectorClient, typing.Type[typing.Any]], UndefinedOr[typing.Any]],
] = {
    tanjun_traits.Client: lambda ctx, _, __: ctx.client,
    tanjun_traits.Component: lambda ctx, cli, type_: cli.get_component_mapping().get(type_, ctx.component) or UNDEFINED,
    tanjun_traits.Context: lambda ctx, _, __: ctx,
    InjectorClient: lambda _, cli, __: cli,
    cache_api.Cache: lambda ctx, _, __: ctx.cache or UNDEFINED,
    rest_api.RESTClient: lambda ctx, _, __: ctx.rest,
    hikari_traits.ShardAware: lambda ctx, _, __: ctx.shards or UNDEFINED,
    event_manager_api.EventManager: lambda ctx, _, __: ctx.events or UNDEFINED,
    interaction_server_api.InteractionServer: lambda ctx, _, __: ctx.server or UNDEFINED,
}


class Injectable(abc.ABC):
    __slots__: typing.Sequence[str] = ()

    @property
    @abc.abstractmethod
    def needs_injector(self) -> bool:
        ...

    @abc.abstractmethod
    def set_injector(self, client: InjectorClient, /) -> None:
        ...


class BaseInjectableValue(Injectable, typing.Generic[_T]):
    __slots__: typing.Sequence[str] = ("callback", "_cached_getters", "injector", "is_async", "_needs_injector")

    def __init__(self, callback: CallbackSig[_T], *, injector: typing.Optional[InjectorClient] = None) -> None:
        self._cached_getters: typing.Optional[typing.List[Getter[typing.Any]]] = None
        self.callback = callback
        self.injector = injector
        self.is_async: typing.Optional[bool] = None
        self._needs_injector = check_injecting(self.callback)

    # This is delegated to the callback callback in-order to delegate set behaviour for this class to the callback.
    def __eq__(self, other: typing.Any) -> bool:
        return bool(self.callback == other)

    # This is delegated to the callback callback in-order to delegate set behaviour for this class to the callback.
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

    async def call(self, *args: typing.Any, ctx: tanjun_traits.Context) -> _T:
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
    __slots__: typing.Sequence[str] = ()

    async def __call__(self, ctx: tanjun_traits.Context, /) -> _T:
        return await self.call(ctx=ctx)


class InjectableCheck(BaseInjectableValue[bool]):
    __slots__: typing.Sequence[str] = ()

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        if result := await self.call(ctx, ctx=ctx):
            return result

        raise errors.FailedCheck()


class InjectableConverter(BaseInjectableValue[_T]):
    __slots__: typing.Sequence[str] = ("_is_base_converter",)

    def __init__(self, callback: CallbackSig[_T], *, injector: typing.Optional[InjectorClient] = None) -> None:
        super().__init__(callback, injector=injector)
        self._is_base_converter = isinstance(self.callback, conversion.BaseConverter)

    async def __call__(self, value: str, ctx: tanjun_traits.Context, /) -> _T:
        if self._is_base_converter:
            assert isinstance(self.callback, conversion.BaseConverter)
            return typing.cast(_T, await self.callback(value, ctx))

        return await self.call(value, ctx=ctx)


class _CacheCallback(typing.Generic[_T]):
    __slots__: typing.Sequence[str] = ("_callback", "_result")

    def __init__(self, callback: CallbackSig[_T], /) -> None:
        self._callback = callback
        self._result: typing.Optional[_T] = None

    async def __call__(
        self,
        # Positional arg(s) may be guaranteed under some contexts so we want to pass those through.
        *args: typing.Any,
        ctx: tanjun_traits.Context = Injected(type=tanjun_traits.Context),  # type: ignore[assignment]
        injector: InjectorClient = Injected(type=InjectorClient),  # type: ignore[assignment]
    ) -> _T:
        if self._result is None:
            getters = injector.resolve_callback_to_getters(self._callback)
            temp_result = self._callback(*args, **await resolve_getters(ctx, getters))

            if isinstance(temp_result, collections.Awaitable):
                self._result = typing.cast(_T, await temp_result)
            else:
                self._result = temp_result

        return self._result


def cache_callback(callback: CallbackSig[_T], /) -> typing.Callable[..., typing.Awaitable[_T]]:
    return _CacheCallback(callback)
