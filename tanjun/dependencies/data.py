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
"""Dependency utilities used for managing data."""
from __future__ import annotations

__all__: list[str] = ["LazyConstant", "cache_callback", "cached_inject", "inject_lc", "make_lc_resolver"]

import asyncio
import datetime
import time
import typing

import alluka

if typing.TYPE_CHECKING:
    import contextlib
    from collections import abc as collections

    from typing_extensions import Self

_T = typing.TypeVar("_T")


class LazyConstant(typing.Generic[_T]):
    """Injected type used to hold and generate lazy constants.

    !!! note
        To easily resolve this type use [inject_lc][tanjun.dependencies.inject_lc].
    """

    __slots__ = ("_callback", "_lock", "_value")

    def __init__(self, callback: alluka.abc.CallbackSig[_T], /) -> None:
        """Initiate a new lazy constant.

        Parameters
        ----------
        callback
            Callback used to resolve this to a constant value.

            This supports dependency injection and may either be sync or asynchronous.
        """
        self._callback = callback
        self._lock: typing.Optional[asyncio.Lock] = None
        self._value: typing.Optional[_T] = None

    @property
    def callback(
        self,
    ) -> typing.Union[
        collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, _T]], collections.Callable[..., _T]
    ]:
        """Descriptor of the callback used to get this constant's initial value."""
        return self._callback

    def get_value(self) -> typing.Optional[_T]:
        """Get the value of this constant if set, else [None][]."""
        return self._value

    def reset(self) -> Self:
        """Clear the internally stored value."""
        self._lock = None
        self._value = None
        return self

    def set_value(self, value: _T, /) -> Self:
        """Set the constant value.

        Parameters
        ----------
        value
            The value to set.

        Raises
        ------
        RuntimeError
            If the constant has already been set.
        """
        if self._value is not None:
            raise RuntimeError("Constant value already set.")

        self._value = value
        self._lock = None
        return self

    def acquire(self) -> contextlib.AbstractAsyncContextManager[typing.Any]:
        """Acquire this lazy constant as an asynchronous lock.

        This is used to ensure that the value is only generated once
        and should be kept acquired until
        [LazyConstant.set_value][tanjun.dependencies.LazyConstant.set_value]
        has been called.

        Returns
        -------
        contextlib.AbstractAsyncContextManager[typing.Any]
            Context manager that can be used to acquire the lock.
        """
        if not self._lock:
            # Error if this is called outside of a running event loop.
            asyncio.get_running_loop()
            self._lock = asyncio.Lock()

        return self._lock


def make_lc_resolver(
    type_: type[_T], /
) -> collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, _T]]:
    """Make an injected callback which resolves a LazyConstant.

    !!! note
        This is internally used by [inject_lc][tanjun.dependencies.inject_lc].

    !!! note
        For this to work, a [LazyConstant][tanjun.dependencies.LazyConstant]
        must've been set as a type dependency for the passed `type_`.

    Parameters
    ----------
    type_
        The type of the constant to resolve.

    Returns
    -------
    collections.abc.Callable[..., collections.abc.Coroutine[typing.Any, typing.Any, _T]]
        An injected callback used to resolve the LazyConstant.
    """

    async def resolve(
        *,
        # TODO: switch to using Injected here, the type var currently breaks pyright compat cause pyright bug.
        # This bug is caused by both this module and alluka.Injected using a typevar called "_T"
        ctx: alluka.abc.Context = alluka.inject(type=alluka.abc.Context),
        # LazyConstant gets type arguments at runtime and Injected can't be used here as that'd fail to
        # resolve.
        constant: LazyConstant[_T] = alluka.inject(type=LazyConstant[type_]),
    ) -> _T:
        """Resolve a lazy constant."""
        if (value := constant.get_value()) is not None:
            return value

        async with constant.acquire():
            if (value := constant.get_value()) is not None:
                return value

            result = await ctx.call_with_async_di(constant.callback)
            constant.set_value(result)
            return result

    return resolve


def inject_lc(type_: type[_T], /) -> _T:
    """Make a LazyConstant injector.

    This acts like [alluka.inject][] and the result of it
    should also be assigned to a parameter's default to be used.

    !!! note
        For this to work, a [LazyConstant][tanjun.dependencies.LazyConstant]
        must've been set as a type dependency for the passed `type_`.

    Parameters
    ----------
    type_
        The type of the constant to resolve.

    Returns
    -------
    alluka.InjectedDescriptor[_T]
        Injector used to resolve the LazyConstant.

    Example
    -------
    ```py
    @component.with_command
    @tanjun.as_message_command
    async def command(
        ctx: tanjun.abc.MessageCommand,
        application: hikari.Application = tanjun.inject_lc(hikari.Application)
    ) -> None:
        raise NotImplementedError

    ...

    async def resolve_app(
        client: tanjun.abc.Client = tanjun.inject(type=tanjun.abc.Client)
    ) -> hikari.Application:
        raise NotImplementedError

    tanjun.Client.from_gateway_bot(...).set_type_dependency(
        tanjun.LazyConstant[hikari.Application] = tanjun.LazyConstant(resolve_app)
    )
    ```
    """
    return alluka.inject(callback=make_lc_resolver(type_))


class _CacheCallback(typing.Generic[_T]):
    __slots__ = ("_callback", "_expire_after", "_last_called", "_lock", "_result", "__weakref__")

    def __init__(
        self,
        callback: alluka.abc.CallbackSig[_T],
        /,
        *,
        expire_after: typing.Union[int, float, datetime.timedelta, None],
    ) -> None:
        self._callback = callback
        self._last_called: typing.Optional[float] = None
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Union[_T, alluka.abc.Undefined] = alluka.abc.UNDEFINED
        if expire_after is None:
            pass
        elif isinstance(expire_after, datetime.timedelta):
            expire_after = expire_after.total_seconds()
        else:
            expire_after = float(expire_after)

        if expire_after is not None and expire_after <= 0:
            raise ValueError("expire_after must be more than 0 seconds")

        self._expire_after = expire_after

    @property
    def _has_expired(self) -> bool:
        return self._expire_after is not None and (
            not self._last_called or self._expire_after <= (time.monotonic() - self._last_called)
        )

    async def __call__(
        self,
        # Positional arg(s) may be guaranteed under some contexts so we want to pass those through.
        *args: typing.Any,
        # TODO: switch to using Injected here, the type var currently breaks pyright compat cause pyright bug.
        # This bug is caused by both this module and alluka.Injected using a typevar called "_T"
        ctx: alluka.abc.Context = alluka.inject(type=alluka.abc.Context),
    ) -> _T:
        if self._result is not alluka.abc.UNDEFINED and not self._has_expired:
            assert not isinstance(self._result, alluka.abc.Undefined)
            return self._result

        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._result is not alluka.abc.UNDEFINED and not self._has_expired:
                assert not isinstance(self._result, alluka.abc.Undefined)
                return self._result

            self._result = await ctx.call_with_async_di(self._callback, *args)
            self._last_called = time.monotonic()
            # This is set to None afterwards to ensure that it isn't persisted between loops.
            self._lock = None
            return self._result


def cache_callback(
    callback: alluka.abc.CallbackSig[_T], /, *, expire_after: typing.Union[int, float, datetime.timedelta, None] = None
) -> collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, _T]]:
    """Cache the result of a callback within a dependency injection context.

    !!! note
        This is internally used by [cached_inject][tanjun.dependencies.cached_inject].

    Parameters
    ----------
    callback
        The callback to cache the result of.
    expire_after
        The amount of time to cache the result for in seconds.

        Leave this as [None][] to cache for the runtime of the application.

    Returns
    -------
    collections.abc.Callable[..., collections.abc.Corouting[typing.Any, typing.Any, _T]]
        A callback which will cache the result of the given callback after the
        first call.

    Raises
    ------
    ValueError
        If expire_after is not a valid value.
        If expire_after is not less than or equal to 0 seconds.
    """
    return _CacheCallback(callback, expire_after=expire_after)


def cached_inject(
    callback: alluka.abc.CallbackSig[_T], /, *, expire_after: typing.Union[float, int, datetime.timedelta, None] = None
) -> _T:
    """Inject a callback with caching.

    This acts like [alluka.inject][] and the result of it
    should also be assigned to a parameter's default to be used.

    Example
    -------
    ```py
    async def resolve_database(
        client: tanjun.abc.Client = tanjun.inject(type=tanjun.abc.Client)
    ) -> Database:
        raise NotImplementedError

    @tanjun.as_message_command("command name")
    async def command(
        ctx: tanjun.abc.Context, db: Database = tanjun.cached_inject(resolve_database)
    ) -> None:
        raise NotImplementedError
    ```

    Parameters
    ----------
    callback
        The callback to inject.
    expire_after
        The amount of time to cache the result for in seconds.

        Leave this as [None][] to cache for the runtime of the application.

    Returns
    -------
    alluka.InjectedDescriptor[_T]
        Injector used to resolve the cached callback.

    Raises
    ------
    ValueError
        If expire_after is not a valid value.
        If expire_after is not less than or equal to 0 seconds.
    """
    return alluka.inject(callback=cache_callback(callback, expire_after=expire_after))
