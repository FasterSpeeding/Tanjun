# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2022, Faster Speeding
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
import collections.abc as collections
import copy
import inspect
import sys
import types
import typing

from . import abc as tanjun_abc
from . import errors

if typing.TYPE_CHECKING:
    _BasicInjectionContextT = typing.TypeVar("_BasicInjectionContextT", bound="BasicInjectionContext")
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
        """Injection client this context is bound to."""

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
    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[_T]:
        """Get the implementation for an injected type.

        .. note::
            Unlike `InjectionClient.get_type_dependency`, this method may also
            return context specific implementations of a type if the type isn't
            registered with the client.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        UndefinedOr[_T]
            The resolved type if found, else `Undefined`.
        """


class BasicInjectionContext(AbstractInjectionContext):
    """Basic implementation of a `AbstractInjectionContext`."""

    __slots__ = ("_injection_client", "_result_cache", "_special_case_types")

    def __init__(self, client: InjectorClient, /) -> None:
        """Initialise a basic injection context.

        Parameters
        ----------
        client : InjectorClient
            The injection client this context is bound to.
        """
        self._injection_client = client
        self._result_cache: typing.Optional[dict[CallbackSig[typing.Any], typing.Any]] = None
        self._special_case_types: dict[type[typing.Any], typing.Any] = {
            AbstractInjectionContext: self,
            BasicInjectionContext: self,
            type(self): self,
        }

    @property
    def injection_client(self) -> InjectorClient:
        # <<inherited docstring from AbstractInjectionContext>>.
        return self._injection_client

    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None:
        # <<inherited docstring from AbstractInjectionContext>>.
        if self._result_cache is None:
            self._result_cache = {}

        self._result_cache[callback] = value

    def get_cached_result(self, callback: CallbackSig[_T], /) -> UndefinedOr[_T]:
        # <<inherited docstring from AbstractInjectionContext>>.
        return self._result_cache.get(callback, UNDEFINED) if self._result_cache else UNDEFINED

    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[_T]:
        # <<inherited docstring from AbstractInjectionContext>>.
        if (value := self._special_case_types.get(type_, UNDEFINED)) is not UNDEFINED:
            return value

        return self._injection_client.get_type_dependency(type_)

    def _set_type_special_case(self: _BasicInjectionContextT, type_: type[_T], value: _T, /) -> _BasicInjectionContextT:
        self._special_case_types[type_] = value
        return self

    def _remove_type_special_case(self: _BasicInjectionContextT, type_: type[typing.Any], /) -> _BasicInjectionContextT:
        del self._special_case_types[type_]
        return self


class AbstractDescriptor(abc.ABC, typing.Generic[_T]):
    """Abstract class for all injected argument descriptors."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def needs_injector(self) -> bool:
        """Whether this descriptor needs a dependency injection client to run."""

    @abc.abstractmethod
    async def resolve_with_command_context(self, ctx: tanjun_abc.Context, /) -> _T:
        """Try to resolve the descriptor with the given command context.

        Parameters
        ----------
        ctx : tanjun.abc.Context
            The context to resolve the descriptor with.

        Returns
        -------
        _T
            The result to be injected.

        Raises
        ------
        RuntimeError
            If the command context does not have a dependency injection client when
            one is required.
        tanjun.errors.MissingDependencyError
            If the client does not have an implementation of a non-defaulting
            type dependency this descriptor needs.
        """

    @abc.abstractmethod
    async def resolve_without_injector(self) -> _T:
        """Try to resolve this descriptor without a dependency injection client.

        Returns
        -------
        _T
            The result to be injected.

        Raises
        ------
        RuntimeError
            If a dependency injection client is required.
        tanjun.errors.MissingDependencyError
            If the client does not have an implementation of a non-defaulting
            type dependency this descriptor needs.
        """

    @abc.abstractmethod
    async def resolve(self, ctx: AbstractInjectionContext, /) -> _T:
        """Resolve the descriptor with the given dependency injection context.

        Parameters
        ----------
        ctx : tanjun.abc.AbstractInjectionContext
            The context to resolve the type or callback with.

        Returns
        -------
        _T
            The result to be injected.

        Raises
        ------
        tanjun.errors.MissingDependencyError
            If the client does not have an implementation of a non-defaulting
            type dependency this descriptor needs.
        """


class CallbackDescriptor(AbstractDescriptor[_T]):
    """Descriptor of a callback taking advantage of dependency injection.

    This holds metadata and logic necessary for callback injection.
    """

    __slots__ = ("_callback", "_descriptors", "_is_async", "_needs_injector")

    def __init__(self, callback: CallbackSig[_T], /) -> None:
        """Initialise an injected callback descriptor.

        Parameters
        ----------
        callback : CallbackSig[_T]
            The callback to wrap with dependency injection.

        Raises
        ------
        ValueError
            If `callback` has any injected arguments which can only be passed
            positionally.
        """
        self._callback = callback
        self._is_async: typing.Optional[bool] = None
        self._descriptors, self._needs_injector = self._parse_descriptors(callback)

    # This is delegated to the callback to delegate set/list behaviour for this class to the callback.
    def __eq__(self, other: typing.Any) -> bool:
        return bool(self._callback == other)

    # This is delegated to the callback to delegate set/list behaviour for this class to the callback.
    def __hash__(self) -> int:
        return hash(self._callback)

    @property
    def callback(self) -> CallbackSig[_T]:
        """The descriptor's callback."""
        return self._callback

    @property
    def needs_injector(self) -> bool:
        # <<inherited docstring from Descriptor>>.
        return self._needs_injector

    @staticmethod
    def _parse_descriptors(callback: CallbackSig[_T], /) -> tuple[dict[str, AbstractDescriptor[typing.Any]], bool]:
        try:
            parameters = inspect.signature(callback).parameters.items()
        except ValueError:  # If we can't inspect it then we have to assume this is a NO
            # As a note, this fails on some "signature-less" builtin functions/types like str.
            return {}, False

        descriptors: dict[str, AbstractDescriptor[typing.Any]] = {}
        for name, parameter in parameters:
            if parameter.default is parameter.empty or not isinstance(parameter.default, Injected):
                continue

            if parameter.kind is parameter.POSITIONAL_ONLY:
                raise ValueError("Injected positional only arguments are not supported")

            if parameter.default.callback is not None:
                descriptors[name] = CallbackDescriptor(parameter.default.callback)

            else:
                assert parameter.default.type is not None
                descriptors[name] = TypeDescriptor(parameter.default.type)

        return descriptors, any(d.needs_injector for d in descriptors.values())

    def copy(self: _CallbackDescriptorT, *, _new: bool = True) -> _CallbackDescriptorT:
        """Create a copy of this descriptor.

        Returns
        -------
        CallbackDescriptor[_T]
            A copy of this descriptor.
        """
        if not _new:
            self._callback = copy.copy(self._callback)
            return self

        return copy.copy(self).copy(_new=False)

    def overwrite_callback(self, callback: CallbackSig[_T], /) -> None:
        """Overwrite the callback of this descriptor.

        Parameters
        ----------
        callback : CallbackSig[_T]
            The new callback to overwrite with.

        Raises
        ------
        ValueError
            If `callback` has any injected arguments which can only be passed
            positionally.
        """
        self._callback = callback
        self._is_async = None
        self._descriptors, self._needs_injector = self._parse_descriptors(callback)

    def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, /, *args: typing.Any, **kwargs: typing.Any
    ) -> collections.Coroutine[typing.Any, typing.Any, _T]:
        """Try to resolve the callback with the given command context.

        Parameters
        ----------
        ctx : tanjun.abc.Context
            The context to resolve the callback with.
        *args : typing.Any
            The positional arguments to pass to the callback.
        **kwargs : typing.Any
            The keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The callback's result.

        Raises
        ------
        RuntimeError
            If the callback needs a dependency injection client but the
            context does not have one.
        tanjun.errors.MissingDependencyError
            If the callback needs an injected type which isn't present in the
            context or client and doesn't have a set default.
        """
        if self.needs_injector and isinstance(ctx, AbstractInjectionContext):
            return self.resolve(ctx, *args, **kwargs)

        return self.resolve_without_injector(*args, **kwargs)

    def resolve_without_injector(
        self, *args: typing.Any, **kwargs: typing.Any
    ) -> collections.Coroutine[typing.Any, typing.Any, _T]:
        """Try to resolve the callback without a dependency injection client.

        Parameters
        ----------
        *args : typing.Any
            The positional arguments to pass to the callback.
        **kwargs : typing.Any
            The keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The callback's result.

        Raises
        ------
        RuntimeError
            If the callback needs a dependency injection client present.
        """
        if self._needs_injector:
            raise RuntimeError("Callback descriptor needs a dependency injection client")

        return self.resolve(_EmptyContext(), *args, **kwargs)

    async def resolve(self, ctx: AbstractInjectionContext, /, *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Resolve the callback with the given dependency injection context.

        Parameters
        ----------
        ctx : AbstractInjectionContext
            The context to resolve the callback with.
        *args : typing.Any
            The positional arguments to pass to the callback.
        **kwargs : typing.Any
            The keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The callback's result.

        Raises
        ------
        tanjun.errors.MissingDependencyError
            If the callback needs an injected type which isn't present in the
            context or client and doesn't have a set default.
        """
        if override := ctx.injection_client.get_callback_override(self._callback):
            return await override.resolve(ctx, *args, **kwargs)

        if (result := ctx.get_cached_result(self._callback)) is not UNDEFINED:
            assert not isinstance(result, Undefined)
            return result

        sub_results = {name: await descriptor.resolve(ctx) for name, descriptor in self._descriptors.items()}
        result = self._callback(*args, **sub_results, **kwargs)

        if self._is_async is None:
            self._is_async = inspect.isawaitable(result)

        if self._is_async:
            assert inspect.isawaitable(result)
            result = await result

        # TODO: should we avoid caching the result if args/kwargs are passed?
        ctx.cache_result(self._callback, result)
        return typing.cast(_T, result)


class SelfInjectingCallback(CallbackDescriptor[_T]):
    """Class used to make a callback self-injecting by linking it to a client.

    Examples
    --------
    ```py
    async def callback(database: Database = tanjun.inject(type=Database)) -> None:
        await database.do_something()

    ...

    client = tanjun.Client.from_gateway_bot(bot)
    injecting_callback = tanjun.SelfInjectingCallback(callback, client)
    await injecting_callback()
    ```
    """

    __slots__ = ("_client",)

    def __init__(self, injector_client: InjectorClient, callback: CallbackSig[_T], /) -> None:
        """Initialise a self injecting callback.

        Parameters
        ----------
        injector : InjectorClient
            The injection client to use to resolve dependencies.
        callback : CallbackSig[_T]
            The callback to make self-injecting.

        Raises
        ------
        ValueError
            If `callback` has any injected arguments which can only be passed
            positionally.
        """
        super().__init__(callback)
        self._client = injector_client

    async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> _T:
        """Call this callback with the provided arguments + injected arguments.

        Parameters
        ----------
        *args : typing.Any
            The positional arguments to pass to the callback.
        **kwargs : typing.Any
            The keyword arguments to pass to the callback.

        Returns
        -------
        _T
            The callback's result.
        """
        ctx = BasicInjectionContext(self._client)
        return await self.resolve(ctx, *args, **kwargs)


def as_self_injecting(
    injector_client: InjectorClient, /
) -> collections.Callable[[CallbackSig[_T]], SelfInjectingCallback[_T]]:
    """Make a callback self-inecting by linking it to a client through a decorator call.

    Examples
    --------
    ```py
    def make_callback(client: tanjun.Client) -> collections.abc.Callable[[], int]:
        @tanjun.as_self_injected(client)
        async def get_int_value(
            redis: redis.Client = tanjun.inject(type=redis.Client)
        ) -> int:
            return int(await redis.get('key'))

        return get_int_value
    ```

    Parameters
    ----------
    injector_client : InjectorClient
        The injection client to use to resolve dependencies.

    Returns
    -------
    collections.abc.Callable[[CallbackSig[_T]], SelfInjectingCallback[_T]]
    """

    def decorator(callback: CallbackSig[_T], /) -> SelfInjectingCallback[_T]:
        return SelfInjectingCallback(injector_client, callback)

    return decorator


if sys.version_info >= (3, 10):
    _UnionTypes = {typing.Union, types.UnionType}
    _NoneType = types.NoneType

else:
    _UnionTypes = {typing.Union}
    _NoneType = type(None)


class TypeDescriptor(AbstractDescriptor[_T]):
    """Descriptor of an injected type.

    This class holds all the logic for resolving a type with dependency
    injection.
    """

    __slots__ = ("_default", "_type", "_union")

    def __init__(self, type_: _TypeT[_T], /) -> None:
        """Initialise an injected type descriptor.

        Parameters
        ----------
        type_ : type[_T]
            The type to resolve.
        """
        self._default: UndefinedOr[_T] = UNDEFINED
        self._type = type_
        self._union: typing.Optional[list[type[_T]]] = None

        if typing.get_origin(type_) not in _UnionTypes:
            return

        sub_types = list(typing.get_args(type_))
        try:
            sub_types.remove(_NoneType)
        except ValueError:
            pass
        else:
            self._default = typing.cast(_T, None)

        self._union = sub_types

    @property
    def needs_injector(self) -> bool:
        # <<inherited docstring from AbstractDescriptor>>.
        return self._default is UNDEFINED

    @property
    def type(self) -> _TypeT[_T]:
        """The type being injected."""
        return self._type  # type: ignore  # pyright bug?

    def resolve_with_command_context(
        self, ctx: tanjun_abc.Context, /
    ) -> collections.Coroutine[typing.Any, typing.Any, _T]:
        # <<inherited docstring from AbstractDescriptor>>.
        if self.needs_injector and isinstance(ctx, AbstractInjectionContext):
            return self.resolve(ctx)

        return self.resolve_without_injector()

    async def resolve_without_injector(self) -> _T:
        # <<inherited docstring from AbstractDescriptor>>.
        if self._default is not UNDEFINED:
            assert not isinstance(self._default, Undefined)
            return self._default

        raise RuntimeError("Type descriptor cannot be resolved without an injection client")

    async def resolve(self, ctx: AbstractInjectionContext, /) -> _T:
        # <<inherited docstring from AbstractDescriptor>>.
        if (result := ctx.get_type_dependency(self._type)) is not UNDEFINED:
            assert not isinstance(result, Undefined)
            return result

        # We still want to allow for the possibility of a Union being
        # explicitly implemented so we check types within a union
        # after the literal type.
        if self._union:
            for cls in self._union:
                if (result := ctx.get_type_dependency(cls)) is not UNDEFINED:
                    assert not isinstance(result, Undefined)
                    return result

        if self._default is not UNDEFINED:
            assert not isinstance(self._default, Undefined)
            return self._default

        raise errors.MissingDependencyError(f"Couldn't resolve injected type {self._type} to actual value") from None


_TypeT = type[_T]


class Injected(typing.Generic[_T]):
    """Decare a keyword-argument as requiring an injected dependency.

    This is the type returned by `inject`.
    """

    __slots__ = ("callback", "type")

    def __init__(
        self,
        *,
        callback: typing.Optional[CallbackSig[_T]] = None,
        type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
    ) -> None:  # TODO: add default/factory to this?
        """Initialise an injection default descriptor.

        Parameters
        ----------
        callback : typing.Optional[CallbackSig[_T]]
            The callback to use to resolve the dependency.

            If this callback has no type dependencies then this will still work
            without an injection context but this can be overridden using
            `InjectionClient.set_callback_override`.
        type : typing.Optional[type[_T]]
            The type of the dependency to resolve.

            If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
            is passed for `type` then each type in the union will be tried
            separately after the litarl union type is tried, allowing for resolving
            `A | B` to the value set by `set_type_dependency(B, ...)`.

            If a union has `None` as one of its types (including `Optional[T]`)
            then `None` will be passed for the parameter if none of the types could
            be resolved using the linked client.

        Raises
        ------
        ValueError
            If both `callback` and `type` are specified or if neither is specified.
        """
        if callback is None and type is None:
            raise ValueError("Must specify one of `callback` or `type`")

        if callback is not None and type is not None:
            raise ValueError("Only one of `callback` or `type` can be specified")

        self.callback = callback
        self.type = type


def inject(
    *,
    callback: typing.Optional[CallbackSig[_T]] = None,
    type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
) -> Injected[_T]:
    """Decare a keyword-argument as requiring an injected dependency.

    This should be assigned to an arugment's default value.

    Examples
    --------
    ```py
    @tanjun.as_slash_command("name", "description")
    async def command_callback(
        ctx: tanjun.abc.Context,
        # Here we take advantage of scope based special casing which allows
        # us to inject the `Component` type.
        injected_type: tanjun.abc.Component = tanjun.inject(type=tanjun.abc.Component)
        # Here we inject an out-of-scope callback which itself is taking
        # advantage of type injection.
        callback_result: ResultT = tanjun.inject(callback=injected_callback)
    ) -> None:
        raise NotImplementedError
    ```

    Parameters
    ----------
    callback : typing.Optional[CallbackSig[_T]]
        The callback to use to resolve the dependency.

        If this callback has no type dependencies then this will still work
        without an injection context but this can be overridden using
        `InjectionClient.set_callback_override`.
    type : typing.Optional[type[_T]]
        The type of the dependency to resolve.

        If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
        is passed for `type` then each type in the union will be tried
        separately after the litarl union type is tried, allowing for resolving
        `A | B` to the value set by `set_type_dependency(B, ...)`.

        If a union has `None` as one of its types (including `Optional[T]`)
        then `None` will be passed for the parameter if none of the types could
        be resolved using the linked client.

    Raises
    ------
    ValueError
        If both `callback` and `type` are specified or if neither is specified.
    """
    return Injected(callback=callback, type=type)


def injected(
    *,
    callback: typing.Optional[CallbackSig[_T]] = None,
    type: typing.Optional[_TypeT[_T]] = None,  # noqa: A002
) -> Injected[_T]:
    """Alias of `inject`."""
    return inject(callback=callback, type=type)


class InjectorClient:
    """Dependency injection client used by Tanjun's standard implementation."""

    __slots__ = ("_callback_overrides", "_type_dependencies")

    def __init__(self) -> None:
        """Initialise an injector client."""
        self._callback_overrides: dict[CallbackSig[typing.Any], CallbackDescriptor[typing.Any]] = {}
        self._type_dependencies: dict[type[typing.Any], typing.Any] = {InjectorClient: self}

    def set_type_dependency(self: _InjectorClientT, type_: type[_T], value: _T, /) -> _InjectorClientT:
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

        Returns
        -------
        Self
            The client instance to allow chaining.
        """
        self._type_dependencies[type_] = value
        return self

    def get_type_dependency(self, type_: type[_T], /) -> UndefinedOr[_T]:
        """Get the implementation for an injected type.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        UndefinedOr[_T]
            The resolved type if found, else `Undefined`.
        """
        return self._type_dependencies.get(type_, UNDEFINED)

    def remove_type_dependency(self: _InjectorClientT, type_: type[typing.Any], /) -> _InjectorClientT:
        """Remove a type dependency.

        Parameters
        ----------
        type_: type[_T]
            The associated type.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        KeyError
            If `type_` is not registered.
        """
        del self._type_dependencies[type_]
        return self

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
        """Get the set override for a specific injected callback.

        Parameters
        ----------
        callback: CallbackSig[_T]
            The injected callback to get the override for.

        Returns
        -------
        typing.Optional[CallbackDescriptor[_T]]
            The override if found, else `None`.
        """
        return self._callback_overrides.get(callback)

    def remove_callback_override(self: _InjectorClientT, callback: CallbackSig[_T], /) -> _InjectorClientT:
        """Remove a callback override.

        Parameters
        ----------
        callback: CallbackSig[_T]
            The injected callback to remove the override for.

        Returns
        -------
        Self
            The client instance to allow chaining.

        Raises
        ------
        KeyError
            If no override is found for the callback.
        """
        del self._callback_overrides[callback]
        return self


class _EmptyInjectorClient(InjectorClient):
    __slots__ = ()

    def set_type_dependency(self: _InjectorClientT, _: type[_T], __: _T, /) -> _InjectorClientT:
        return self  # NOOP is safer here than NotImplementedError

    def get_type_dependency(self, _: type[typing.Any], /) -> Undefined:
        return UNDEFINED

    def remove_type_dependency(self: _InjectorClientT, type_: type[typing.Any], /) -> _InjectorClientT:
        raise KeyError(type_)

    def set_callback_override(self: _InjectorClientT, _: CallbackSig[_T], __: CallbackSig[_T], /) -> _InjectorClientT:
        return self  # NOOP is safer here than NotImplementedError

    def get_callback_override(self, _: CallbackSig[_T], /) -> None:
        return

    def remove_callback_override(self: _InjectorClientT, callback: CallbackSig[_T], /) -> _InjectorClientT:
        raise KeyError(callback)


_EMPTY_CLIENT = _EmptyInjectorClient()


class _EmptyContext(AbstractInjectionContext):
    __slots__ = ("_result_cache",)

    def __init__(self) -> None:
        self._result_cache: typing.Optional[dict[CallbackSig[typing.Any], typing.Any]] = None

    @property
    def injection_client(self) -> InjectorClient:
        return _EMPTY_CLIENT

    def cache_result(self, callback: CallbackSig[_T], value: _T, /) -> None:
        if self._result_cache is None:
            self._result_cache = {}

        self._result_cache[callback] = value

    def get_cached_result(self, callback: CallbackSig[typing.Any], /) -> Undefined:
        return self._result_cache.get(callback, UNDEFINED) if self._result_cache else UNDEFINED

    def get_type_dependency(self, _: type[typing.Any], /) -> Undefined:
        return UNDEFINED
