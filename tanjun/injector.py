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
    "CallbackT",
    "GetterCallbackT",
    "Getter",
    "Undefined",
    "UNDEFINED",
    "UndefinedOr",
    "Injected",
    "InjectorClient",
    "Injectable",
]

import abc
import inspect
import typing

from hikari import traits as hikari_traits

from . import errors
from . import traits as tanjun_traits

_InjectorClientT = typing.TypeVar("_InjectorClientT", bound="InjectorClient")
_T = typing.TypeVar("_T")
CallbackT = typing.Callable[..., typing.Union[_T, typing.Awaitable[_T]]]
GetterCallbackT = typing.Callable[[tanjun_traits.Context], CallbackT[_T]]


class Getter(typing.Generic[_T]):
    __slots__: typing.Sequence[str] = ("callback", "is_async", "name", "type")

    def __init__(self, callback: GetterCallbackT[_T], name: str, /) -> None:
        self.callback = callback
        self.is_async: typing.Optional[bool] = None
        self.name = name


class Undefined:
    __instance: Undefined

    def __bool__(self) -> bool:
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


def check_injecting(callback: CallbackT[typing.Any], /) -> bool:
    parameters = inspect.signature(callback).parameters.values()
    return any(isinstance(parameter.default, Injected) for parameter in parameters)


class Injected(typing.Generic[_T]):
    __slots__: typing.Sequence[str] = ("type", "callback")

    def __init__(
        self,
        *,
        callback: UndefinedOr[typing.Callable[[], typing.Union[_T, typing.Awaitable[_T]]]] = UNDEFINED,
        type: UndefinedOr[UndefinedOr[_T]] = UNDEFINED,
    ) -> None:  # TODO: add defaulct/factory to this?
        if callback is UNDEFINED and type is UNDEFINED:
            raise ValueError("Must specify one of `callback` or `type`")

        if callback is not UNDEFINED and type is not UNDEFINED:
            raise ValueError("Only one of `callback` or `type` can be specified")

        self.callback = callback
        self.type = type


async def resolve_getters(
    ctx: tanjun_traits.Context, getters: typing.Iterable[Getter[typing.Any]]
) -> typing.Mapping[str, typing.Any]:
    results: typing.Dict[str, typing.Any] = {}

    for getter in getters:
        result = getter.callback(ctx)()
        if getter.is_async is None:
            getter.is_async = isinstance(result, typing.Awaitable)

        if getter.is_async:
            results[getter.name] = await result

        else:
            results[getter.name] = result

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
        self._callback_overrides: typing.Dict[CallbackT[typing.Any], CallbackT[typing.Any]] = {}
        self._client = client
        self._component_mapping_values: typing.Set[tanjun_traits.Component] = set()
        self._component_mapping: typing.Dict[typing.Type[tanjun_traits.Component], tanjun_traits.Component] = {}
        self._type_dependencies: typing.Dict[typing.Type[typing.Any], CallbackT[typing.Any]] = {}

    def add_type_dependency(
        self: _InjectorClientT, type_: typing.Type[_T], callback: CallbackT[_T], /
    ) -> _InjectorClientT:
        self._type_dependencies[type_] = callback
        return self

    def get_type_dependency(self, type_: typing.Type[_T], /) -> UndefinedOr[CallbackT[_T]]:
        return self._type_dependencies.get(type_, UNDEFINED)

    def add_callable_override(
        self: _InjectorClientT, callback: CallbackT[_T], override: CallbackT[_T], /
    ) -> _InjectorClientT:
        self._callback_overrides[callback] = override
        return self

    def get_callable_override(self, callback: CallbackT[_T], /) -> typing.Optional[CallbackT[_T]]:
        return self._callback_overrides.get(callback)

    def get_component_mapping(self) -> typing.Mapping[typing.Type[tanjun_traits.Component], tanjun_traits.Component]:
        if self._component_mapping_values != self._client.components:
            self._component_mapping.clear()
            self._component_mapping = {type(component): component for component in self._client.components}
            self._component_mapping_values = set(self._client.components)

        return self._component_mapping

    def _make_callback_getter(self, callback: CallbackT[_T], name: str, /) -> Getter[_T]:
        def get(_: tanjun_traits.Context) -> CallbackT[_T]:
            return self._callback_overrides.get(callback, callback)

        return Getter(get, name)

    def _make_type_getter(self, type_: typing.Type[_T], name: str, /) -> Getter[_T]:
        default = None
        for match, function in _TYPE_GETTER_OVERRIDES.items():
            if isinstance(type_, match):
                default = function
                break

        def get(ctx: tanjun_traits.Context) -> CallbackT[_T]:
            try:
                return typing.cast(CallbackT[_T], self._type_dependencies[type_])

            except KeyError:
                if default and (result := default(ctx, self, type_)):
                    return lambda: result

                raise errors.MissingDependencyError(f"Couldn't resolve injected type {type_} to actual value") from None

        return Getter(get, name)

    def resolve_callback_to_getters(self, callback: CallbackT[typing.Any], /) -> typing.Iterator[Getter[typing.Any]]:
        for name, parameter in inspect.signature(callback).parameters.items():
            if parameter.default is parameter.default and not isinstance(parameter.default, Injected):
                continue

            if parameter.kind is parameter.POSITIONAL_ONLY:
                raise ValueError("Injected positional only arguments are not supported")

            if parameter.default.callback is not UNDEFINED:
                yield self._make_callback_getter(parameter.default.callback, name)

            else:
                assert parameter.default.type is not UNDEFINED
                yield self._make_type_getter(parameter.default.type, name)


_TYPE_GETTER_OVERRIDES: typing.Dict[
    typing.Type[typing.Any],
    typing.Callable[[tanjun_traits.Context, InjectorClient, typing.Type[typing.Any]], UndefinedOr[typing.Any]],
] = {
    tanjun_traits.Client: lambda ctx, _, __: ctx.client,
    tanjun_traits.Context: lambda ctx, _, __: ctx,
    InjectorClient: lambda _, cli, __: cli,
    hikari_traits.CacheAware: lambda ctx, _, __: ctx.cache_service or UNDEFINED,
    hikari_traits.RESTAware: lambda ctx, _, __: ctx.rest_service,
    hikari_traits.ShardAware: lambda ctx, _, __: ctx.shard_service or UNDEFINED,
    hikari_traits.EventManagerAware: lambda ctx, _: ctx.event_manager or UNDEFINED,
    tanjun_traits.Component: lambda ctx, cli, type_: cli.get_component_mapping().get(type_, ctx.component) or UNDEFINED,
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


class InjectableCheck(Injectable):
    __slots__: typing.Sequence[str] = ("callback", "_cached_getters", "injector", "is_async", "_needs_injector")

    def __init__(self, callback: CallbackT[bool], *, injector: typing.Optional[InjectorClient] = None) -> None:
        self._cached_getters: typing.Optional[typing.List[Getter[typing.Any]]] = None
        self.callback = callback
        self.injector = injector
        self.is_async: typing.Optional[bool] = None
        self._needs_injector: typing.Optional[bool] = None

    async def __call__(self, ctx: tanjun_traits.Context, /) -> bool:
        if self._needs_injector is None:
            self._needs_injector = bool(self._cached_getters)

        if self._needs_injector:
            if self.injector is None:
                raise RuntimeError("Cannot call an injectable check before the injector has been set")

            if self._cached_getters is None:
                self._cached_getters = list(self.injector.resolve_callback_to_getters(self.callback))

            result = self.callback(ctx, **await resolve_getters(ctx, self._cached_getters))

        else:
            result = self.callback(ctx)

        if self.is_async is None:
            self.is_async = isinstance(result, typing.Awaitable)

        if self.is_async:
            assert isinstance(result, typing.Awaitable)
            result = await result

        else:
            assert isinstance(result, bool)

        return result

    # This is delegated to the callback function in-order to delegate set behaviour for this class to the function.
    def __eq__(self, other: typing.Any) -> bool:
        return self.callback == other

    # This is delegated to the callback function in-order to delegate set behaviour for this class to the function.
    def __hash__(self) -> int:
        return hash(self.callback)

    @property
    def needs_injector(self) -> bool:
        if not self.injector:
            raise ValueError("Need injector to introspect whether it is required")

        if self._needs_injector is None:
            self._needs_injector = check_injecting(self.callback)

        return self._needs_injector

    def set_injector(self, client: InjectorClient) -> None:
        if self.injector:
            raise RuntimeError("Injector already set for this check")

        self.injector = client


def cache_callback(callback: CallbackT[_T]) -> typing.Callable[..., typing.Awaitable[_T]]:
    result: typing.Optional[_T] = None

    async def _get_or_build(
        ctx: tanjun_traits.Context,
        injector: InjectorClient = Injected(type=InjectorClient),
    ) -> _T:
        nonlocal result

        if result is None:
            getters = injector.resolve_callback_to_getters(callback)
            temp_result = callback(**await resolve_getters(ctx, getters))
            result = await temp_result if isinstance(temp_result, typing.Awaitable) else temp_result

        return result

    return _get_or_build
