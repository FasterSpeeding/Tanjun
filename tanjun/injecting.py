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
"""Logic and data classes used within the standard Tanjun implementation to enable dependency injection."""
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
import asyncio
import collections.abc as collections
import copy
import inspect
import time
import typing
import warnings

from . import abc as tanjun_abc
from . import errors

if typing.TYPE_CHECKING:
    import datetime

    _BaseInjectableCallbackT = typing.TypeVar("_BaseInjectableCallbackT", bound="BaseInjectableCallback[typing.Any]")
    _CallbackDescriptorT = typing.TypeVar("_CallbackDescriptorT", bound="CallbackDescriptor[typing.Any]")

_InjectorClientT = typing.TypeVar("_InjectorClientT", bound="InjectorClient")
_T = typing.TypeVar("_T")
CallbackSig = collections.Callable[..., tanjun_abc.MaybeAwaitableT[_T]]
"""Type-hint of a injector callback.

.. note::
    Dependency dependency injection is recursively supported, meaning that the
    keyword arguments for a dependency callback may also ask for dependencies
    themselves.

This may either be a synchronous or asynchronous function with dependency
injection being available for the callback's keyword arguments but dynamically
returning either an awaitable or raw value may lead to errors.

Dependent on the context positional arguments may also be proivded.
"""


class Undefined:
    """Class/type of `UNDEFINED`."""

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
"""Singleton value used within dependency injection to indicate that a value is undefined."""
UndefinedOr = typing.Union[Undefined, _T]
"""Type-hint generic union used to indicate that a value may be undefined or `_T`."""


class AbstractInjectionContext(abc.ABC):
    """Abstract interface of an injection context."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def injection_client(self) -> InjectorClient:
        """Injection client this context is bound to.

        Returns
        -------
        InjectorClient
            The injection client this context is bound to.
        """

    @abc.abstractmethod
    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None:
        """Cache the result of a callback within the scope of this context.

        Parameters
        ----------
        callback : CallbackSig[_T]
            The callback to cache the result of.
        value : _T
            The value to cache.
        """

    @abc.abstractmethod
    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]:
        """Get the cached result of a callback.

        Parameters
        ----------
        callback : CallbackSig[_T]
            The callback to get the cached result of.

        Returns
        -------
        UndefinedOr[_T]
            The cached result of the callback, or `UNDEFINED` if the callback
            has not been cached within this context.
        """

    @abc.abstractmethod
    def get_type_special_case(self, type_: type[_T], /, *, include_client: bool = True) -> UndefinedOr[_T]:
        """Get a special-case value for a type.

        .. note:
            Client set types should override this.

        Parameters
        ----------
        type_ : type[_T]
            The type to get a special-case value for.

        Other Parameters
        ----------------
        include_client : bool
            Whether to fallback to the client's special-cases.

        Returns
        -------
        UndefinedOr[_T]
            The special-case value, or `UNDEFINED` if the type is not supported
            by this context.
        """


class BasicInjectionContext(AbstractInjectionContext):
    """Basic implementation of a `AbstractInjectionContext`.

    Parameters
    ----------
    client : InjectorClient
        The injection client this context is bound to.
    """

    __slots__ = ("_injection_client", "_result_cache", "_special_case_types")

    def __init__(self, client: InjectorClient, /) -> None:
        self._injection_client = client
        self._result_cache: dict[CallbackSig[typing.Any], typing.Any] = {}
        self._special_case_types: dict[type[typing.Any], typing.Any] = {
            AbstractInjectionContext: self,
            BasicInjectionContext: self,
            type(self): self,
        }

    @property
    def injection_client(self) -> InjectorClient:
        # <<inherited docstring from tanjun.injecting.AbstractInjectionContext>>.
        return self._injection_client

    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None:
        # <<inherited docstring from tanjun.injecting.AbstractInjectionContext>>.
        self._result_cache[callback] = value

    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]:
        # <<inherited docstring from tanjun.injecting.AbstractInjectionContext>>.
        return self._result_cache.get(callback, UNDEFINED)

    def get_type_special_case(self, type_: type[_T], /, *, include_client: bool = True) -> UndefinedOr[_T]:
        # <<inherited docstring from tanjun.injecting.AbstractInjectionContext>>.
        if (value := self._special_case_types.get(type_, UNDEFINED)) is not UNDEFINED:
            return value

        if include_client:
            return self._injection_client.get_type_special_case(type_)

        return UNDEFINED

    def set_type_special_case(self, type_: type[_T], value: _T, /) -> None:
        self._special_case_types[type_] = value

    def remove_type_special_case(self, type_: type[typing.Any], /) -> None:
        del self._special_case_types[type_]


class CallbackDescriptor(typing.Generic[_T]):
    __slots__ = ("_callback", "_descriptors", "_is_async")

    def __init__(self, callback: CallbackSig[_T], /) -> None:
        self._callback = callback
        self._is_async: typing.Optional[bool] = None
        try:
            parameters = inspect.signature(callback).parameters.items()
        except ValueError:  # If we can't inspect it then we have to assume this is a NO
            # As a note, this fails on some "signature-less" builtin functions/types like str.
            self._descriptors: dict[str, Descriptor[typing.Any]] = {}
            return

        descriptors: dict[str, Descriptor[typing.Any]] = {}
        for name, parameter in parameters:
            if parameter.default is parameter.empty or not isinstance(parameter.default, Injected):
                continue

            if parameter.kind is parameter.POSITIONAL_ONLY:
                raise ValueError("Injected positional only arguments are not supported")

            if parameter.default.callback is not None:
                descriptors[name] = Descriptor(callback=parameter.default.callback)

            else:
                assert parameter.default.type is not None
                descriptors[name] = Descriptor(type=parameter.default.type)

        self._descriptors = descriptors

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __eq__(self, other: typing.Any) -> bool:
        return bool(self._callback == other)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __hash__(self) -> int:
        return hash(self._callback)

    @property
    def callback(self) -> CallbackSig[_T]:
        return self._callback

    @property
    def needs_injector(self) -> bool:
        return bool(self._descriptors)

    def copy(self: _CallbackDescriptorT, *, _new: bool = True) -> _CallbackDescriptorT:
        if not _new:
            self._callback = copy.copy(self._callback)
            return self

        return copy.copy(self).copy(_new=False)

    async def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, /, *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        if self.needs_injector:
            if isinstance(ctx, AbstractInjectionContext):
                return await self.resolve(ctx, *args, **kwargs)

        return await self.resolve_without_injector(*args, **kwargs)

    async def resolve_without_injector(self, *args: typing.Any, **kwargs: typing.Any) -> _T:
        if self.needs_injector:
            raise RuntimeError("This callback cannot be called without dependency injection")

        result = self._callback(*args, **kwargs)

        if self._is_async is None:
            self._is_async = isinstance(result, collections.Awaitable)

        if self._is_async:
            assert isinstance(result, collections.Awaitable)
            return typing.cast(_T, await result)

        return typing.cast(_T, result)

    async def resolve(self, ctx: AbstractInjectionContext, /, *args: typing.Any, **kwargs: typing.Any) -> _T:
        if override := ctx.injection_client.get_callback_override(self._callback):
            return await override.resolve(ctx, *args, **kwargs)

        if (result := ctx.get_cached_result(self._callback)) is not UNDEFINED:
            assert not isinstance(result, Undefined)
            return result

        if self.needs_injector:
            sub_results = {name: await descriptor.resolve(ctx) for name, descriptor in self._descriptors.items()}
            result = self._callback(*args, **sub_results, **kwargs)

            if self._is_async is None:
                self._is_async = isinstance(result, collections.Awaitable)

            if self._is_async:
                assert isinstance(result, collections.Awaitable)
                result = await result

        else:
            result = await self.resolve_without_injector(*args, **kwargs)

        ctx.cache_result(self._callback, result)
        return typing.cast(_T, result)


class TypeDescriptor(typing.Generic[_T]):
    __slots__ = ("_type",)

    def __init__(self, type_: _TypeT[_T], /) -> None:
        self._type = type_

    @property
    def type(self) -> _TypeT[_T]:
        return self._type  # type: ignore # TODO: pyright bug

    async def resolve_with_command_context(self, ctx: tanjun_abc.Context, /) -> _T:
        if isinstance(ctx, AbstractInjectionContext):
            return await self.resolve(ctx)

        raise RuntimeError("Type injector cannot be resolved without anm injection client")

    async def resolve(self, ctx: AbstractInjectionContext, /) -> _T:
        if dependency := ctx.injection_client.get_type_dependency(self._type):
            if (cached_result := ctx.get_cached_result(dependency.callback)) is not UNDEFINED:
                assert not isinstance(cached_result, Undefined)
                return cached_result

            result = await dependency.resolve(ctx)
            ctx.cache_result(dependency.callback, result)
            return result

        if (special_case := ctx.get_type_special_case(self._type)) is not UNDEFINED:
            assert not isinstance(special_case, Undefined)
            return special_case

        raise errors.MissingDependencyError(f"Couldn't resolve injected type {self._type} to actual value") from None


class Descriptor(typing.Generic[_T]):
    __slots__ = ("_callback", "_type")

    def __init__(
        self,
        *,
        callback: typing.Optional[CallbackSig[_T]] = None,
        type: typing.Optional[_TypeT[_T]] = None,  # noqa A002
    ) -> None:
        if callback is None:
            if type is None:
                raise ValueError("Either callback or type must be specified")

            self._callback: typing.Optional[CallbackDescriptor[_T]] = None
            self._type: typing.Optional[TypeDescriptor[_T]] = TypeDescriptor(type)
            return

        if type is not None:
            raise ValueError("Only one of type or callback should be passed")

        self._callback = CallbackDescriptor(callback)
        self._type = None

    @property
    def callback(self) -> typing.Optional[CallbackSig[_T]]:
        return self._callback.callback if self._callback else None

    @property
    def needs_injector(self) -> bool:
        # Type injectors always need the injector as of present
        return self._callback.needs_injector if self._callback else True

    @property
    def type(self) -> typing.Optional[_TypeT[typing.Any]]:
        return self._type.type if self._type else None

    async def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, /, *args: typing.Any, **kwargs: typing.Any
    ) -> _T:
        if self._type:
            if args or kwargs:
                raise ValueError("*args and **kwargs cannot be passed for a type descriptor")

            return await self._type.resolve_with_command_context(ctx)

        assert self._callback
        return await self._callback.resolve_with_command_context(ctx, *args, **kwargs)

    async def resolve_without_injector(self, *args: typing.Any, **kwargs: typing.Any) -> _T:
        if not self._callback:
            raise RuntimeError("Type injector cannot be resolved without an injector present")

        return await self._callback.resolve_without_injector(*args, **kwargs)

    async def resolve(self, ctx: AbstractInjectionContext, /, *args: typing.Any, **kwargs: typing.Any) -> _T:
        if self._type:
            if args or kwargs:
                raise ValueError("**args and **kwargs cannot be passed for a type descriptor")

            return await self._type.resolve(ctx)

        assert self._callback
        return await self._callback.resolve(ctx, *args, **kwargs)


_TypeT = type[_T]


class Injected(typing.Generic[_T]):
    __slots__ = ("callback", "type")

    def __init__(
        self,
        *,
        callback: typing.Optional[CallbackSig[_T]] = None,
        type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
    ) -> None:  # TODO: add default/factory to this?
        if callback is None and type is None:
            raise ValueError("Must specify one of `callback` or `type`")

        if callback is not None and type is not None:
            raise ValueError("Only one of `callback` or `type` can be specified")

        self.callback = callback
        self.type = type


def injected(
    *,
    callback: typing.Optional[CallbackSig[_T]] = None,
    type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
) -> Injected[_T]:
    """Decare a keyword-argument as requiring an injected dependency.

    Parameters
    ----------
    callback : typing.Optional[CallbackSig[_T]]
        The callback to use to resolve the dependency.

        If this callback has no type dependencies then this will still work
        without an injection context but this can be overridden using
        `InjectionClient.set_callback_override`.
    type : typing.Optional[type[_T]]
        The type of the dependency to resolve.

        Unlike `callback`, `type` is resolved using the injection client and
        therefore requires that dependency injection is implemented on a context
        level.

    Raises
    ------
    ValueError
        If both `callback` and `type` are specified or if neither is specified.
    """
    return Injected(callback=callback, type=type)  # type: ignore  # TODO: This is a pyright bug


class InjectorClient:
    """Dependency injection client used by Tanjun's standard implementation."""

    __slots__ = ("_callback_overrides", "_special_case_types", "_type_dependencies")

    def __init__(self) -> None:
        self._callback_overrides: dict[CallbackSig[typing.Any], CallbackDescriptor[typing.Any]] = {}
        self._special_case_types: typing.Dict[type[typing.Any], typing.Any] = {InjectorClient: self, type(self): self}
        self._type_dependencies: dict[type[typing.Any], CallbackDescriptor[typing.Any]] = {}

    def add_type_dependency(self: _InjectorClientT, type_: type[_T], callback: CallbackSig[_T], /) -> _InjectorClientT:
        """Alias for `InjectorClient.set_type_dependency`.

        .. deprecated:: v2.0.0a2
            Use `InjectorClient.set_type_dependency`.

            This will be removed 1 month after the release of v2.0.0a2.
        """
        warnings.warn(
            "`InjectorClient.add_type_dependency` is deprecated and marked for removal a"
            " month after the release of v2.0.0a2. Use `InjectorClient.set_type_dependency`.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.set_type_dependency(type_, callback)  # type: ignore  # pyright bug

    def set_type_dependency(self: _InjectorClientT, type_: type[_T], callback: CallbackSig[_T], /) -> _InjectorClientT:
        """Set a callback to be called to resolve a injected type.

        Parameters
        ----------
        callback: CallbackSig[_T]
            The callback to use to resolve the dependency.

            If this callback has no type dependencies then this will still work
            without an injection context but this can be overridden using
            `InjectionClient.set_callback_override`.
        type_: type[_T]
            The type of the dependency to resolve.

            Unlike `callback`, `type` is resolved using the injection client and
            therefore requires that dependency injection is implemented on a context
            level.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        ValueError
            If both `callback` and `type` are specified or if neither is specified.
        """
        self._type_dependencies[type_] = CallbackDescriptor(callback)
        return self

    def get_type_dependency(self, type_: type[_T], /) -> typing.Optional[CallbackDescriptor[_T]]:
        """Get the callback associated with an injected type.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        Optional[CallbackDescriptor[_T]]
            The callback to use during type resolution if set, else `None`.
        """
        return self._type_dependencies.get(type_)

    def remove_type_dependency(self, type_: type[typing.Any], /) -> None:
        del self._type_dependencies[type_]

    def get_type_special_case(self, type_: type[_T], /) -> UndefinedOr[_T]:
        return self._special_case_types.get(type_, UNDEFINED)

    def set_type_special_case(
        self: _InjectorClientT, type_: type[_T], value: _T, /
    ) -> _InjectorClientT:  # TODO: rename to add_type_special_case
        self._special_case_types[type_] = value
        return self

    def remove_type_special_case(self, type_: type[typing.Any], /) -> None:
        del self._special_case_types[type_]

    def add_callback_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT:
        """Alias for `InjectorClient.set_callback_override`.

        .. deprecated:: v2.0.0a2
            Use `InjectorClient.set_callback_override`.

            This will be removed 1 month after the release of v2.0.0a2.
        """
        warnings.warn(
            "`InjectorClient.add_callback_override` is deprecated and marked for removal a"
            " month after the release of v2.0.0a2. Use `InjectorClient.set_callback_override`.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return self.set_callback_override(callback, override)

    def set_callback_override(
        self: _InjectorClientT, callback: CallbackSig[_T], override: CallbackSig[_T], /
    ) -> _InjectorClientT:
        """Override a specific injected callback.

        .. note::
            This does not effect the callbacks set for type injectors.

        Parameters
        ----------
        callback: CallbackSig[_T]
            The injected callback to override.
        override: CallbackSig[_T]
            The callback to use instead.

        Returns
        -------
        Self
            The client instance to allow chaining.
        """
        self._callback_overrides[callback] = CallbackDescriptor(override)
        return self

    def get_callback_override(self, callback: CallbackSig[_T], /) -> typing.Optional[CallbackDescriptor[_T]]:
        return self._callback_overrides.get(callback)

    def remove_callback_override(self, callback: CallbackSig[_T], /) -> None:
        del self._callback_overrides[callback]


class BaseInjectableCallback(typing.Generic[_T]):
    __slots__ = ("_descriptor",)

    def __init__(self, callback: CallbackSig[_T], /) -> None:
        self._descriptor: CallbackDescriptor[_T] = CallbackDescriptor(callback)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __eq__(self, other: typing.Any) -> bool:
        return bool(self.callback == other)

    # This is delegated to the callback in-order to delegate set/list behaviour for this class to the callback.
    def __hash__(self) -> int:
        return hash(self.callback)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.callback!r})"

    @property
    def callback(self) -> CallbackSig[_T]:
        return self._descriptor.callback

    @property
    def descriptor(self) -> CallbackDescriptor[_T]:
        return self._descriptor

    @property
    def needs_injector(self) -> bool:
        return self._descriptor.needs_injector

    def copy(self: _BaseInjectableCallbackT, *, _new: bool = True) -> _BaseInjectableCallbackT:
        if not _new:
            self._descriptor = self._descriptor.copy()
            return self

        return copy.copy(self).copy(_new=False)

    def overwrite_callback(self, callback: CallbackSig[_T], /) -> None:
        self._descriptor = CallbackDescriptor(callback)


class _CacheCallback(typing.Generic[_T]):
    __slots__ = ("_callback", "_expire_after", "_last_called", "_lock", "_result")

    def __init__(self, callback: CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta]) -> None:
        self._callback = CallbackDescriptor(callback)
        self._expire_after = expire_after.total_seconds() if expire_after else None
        self._last_called: typing.Optional[float] = None
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Union[_T, Undefined] = UNDEFINED

    @property
    def _has_expired(self) -> bool:
        return self._expire_after is not None and (
            not self._last_called or self._expire_after <= (time.monotonic() - self._last_called)
        )

    async def __call__(
        self,
        # Positional arg(s) may be guaranteed under some contexts so we want to pass those through.
        *args: typing.Any,
        ctx: AbstractInjectionContext = Injected(type=AbstractInjectionContext),  # type: ignore[assignment]
    ) -> _T:
        if self._result is not UNDEFINED and not self._has_expired:
            assert not isinstance(self._result, Undefined)
            return self._result

        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._has_expired:
                self._last_called = time.monotonic()
                self._result = await self._callback.resolve(ctx, *args)
                return self._result

            if self._result is not UNDEFINED:
                assert not isinstance(self._result, Undefined)
                return self._result

            self._last_called = time.monotonic()
            self._result = await self._callback.resolve(ctx, *args)
            return self._result


def cache_callback(
    callback: CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta] = None
) -> collections.Callable[..., collections.Awaitable[_T]]:
    """Cache the result of a callback within a dependency injection context.

    This is useful for dependencies which will always resolve to the same value
    but are expensive to execute (e.g. they make a request or start a client
    connection).

    Parameters
    ----------
    callback : CallbackSig[_T]
        The callback to cache the result of.

    Other Parameters
    ----------------
    expire_after : typing.Optional[datetime.timedelta]
        The amount of time to cache the result for.

        Leave this as `None` to cache for the runtime of the application.

    Returns
    -------
    Callable[..., Awaitable[_T]]
        A callback which will cache the result of the given callback after the
        first call.
    """
    return _CacheCallback(callback, expire_after=expire_after)
