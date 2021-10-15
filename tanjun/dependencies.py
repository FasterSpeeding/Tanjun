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
"""Default dependency classes used within Tanjun and their abstract interfaces."""
from __future__ import annotations

__all__: list[str] = ["AbstractOwnerCheck", "cache_callback", "LazyConstant", "make_lc_resolver", "OwnerCheck"]

import abc
import asyncio
import datetime
import logging
import time
import typing

import hikari

from . import abc as tanjun_abc
from . import injecting

if typing.TYPE_CHECKING:
    import contextlib
    from collections import abc as collections

    _LazyConstantT = typing.TypeVar("_LazyConstantT", bound="LazyConstant[typing.Any]")

_T = typing.TypeVar("_T")
_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun")


class AbstractOwnerCheck(abc.ABC):
    """Interface used to check if a user is deemed to be the bot's "owner"."""

    __slots__ = ()

    @abc.abstractmethod
    async def check_ownership(self, client: tanjun_abc.Client, user: hikari.User, /) -> bool:
        """Check whether this object is owned by the given object.

        Parameters
        ----------
        client : tanjun.abc.Client
            The Tanjun client this check is being called by.
        user : hikari.User
            The user to check ownership for.

        Returns
        -------
        bool
            Whether the bot is owned by the provided user.
        """


class _CachedValue(typing.Generic[_T]):
    __slots__ = ("_expire_after", "_last_called", "_lock", "_result")

    def __init__(self, *, expire_after: typing.Optional[datetime.timedelta]) -> None:
        self._expire_after = expire_after.total_seconds() if expire_after else None
        self._last_called: typing.Optional[float] = None
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Optional[_T] = None

    @property
    def _has_expired(self) -> bool:
        return self._expire_after is not None and (
            not self._last_called or self._expire_after <= (time.monotonic() - self._last_called)
        )

    async def acquire(self, callback: collections.Callable[[], collections.Awaitable[_T]], /) -> _T:
        if self._result is not None and not self._has_expired:
            return self._result

        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._result is not None and not self._has_expired:
                return self._result

            self._result = await callback()
            self._last_called = time.monotonic()
            # This is set to None afterwards to ensure that it isn't persisted between loops.
            self._lock = None
            return self._result


class OwnerCheck(AbstractOwnerCheck):
    """Default implementation of the owner check interface.

    .. warning::
        `fallback_to_application` is only possible when the REST client
        is bound to a Bot token.
    """

    __slots__ = ("_expire_after", "_fallback_to_application", "_owner_ids", "_value")

    def __init__(
        self,
        *,
        expire_after: datetime.timedelta = datetime.timedelta(minutes=5),
        fallback_to_application: bool = True,
        owners: typing.Optional[hikari.SnowflakeishSequence[hikari.User]] = None,
    ) -> None:
        """Initiate a new owner check dependency.

        Other Parameters
        ----------------
        expire_after : datetime.timedelta
            The amount of time to cache application owner data for.

            This defaults to 5 minutes and is only applicable if `rest` is also
            passed.
        fallback_to_application : bool
            Whether this check should fallback to checking the application's owners
            if the user isn't in `owners.

            This only works when the bot's rest client is bound to a Bot token.
        owners : typing.Optional[hikari.SnowflakeishSequence[hikari.User]]
            Sequence of objects and IDs of the users that are allowed to use the
            bot's "owners".
        """
        self._expire_after = expire_after
        self._fallback_to_application = fallback_to_application
        self._owner_ids = {hikari.Snowflake(id_) for id_ in owners} if owners else set[hikari.Snowflake]()
        self._value = _CachedValue[hikari.Application](expire_after=expire_after)

    async def check_ownership(self, client: tanjun_abc.Client, user: hikari.User, /) -> bool:
        if user.id in self._owner_ids:
            return True

        if not self._fallback_to_application:
            return False

        if client.rest.token_type is not hikari.TokenType.BOT:
            _LOGGER.warning(
                "Owner checks cannot fallback to application owners when bound to an OAuth2 "
                "client credentials token and may always fail unless bound to a Bot token."
            )
            return False

        application = await self._value.acquire(client.rest.fetch_application)
        return user.id in application.team.members if application.team else user.id == application.owner.id


class LazyConstant(typing.Generic[_T]):
    """Injected type used to hold and generate lazy constants.

    .. note::
        To quickly resolve this type, use the result of
        `tanjun.make_lc_resolver(_T)` as a callback dependency.
    """

    __slots__ = ("_callback", "_lock", "_value")

    def __init__(self, callback: collections.Callable[..., tanjun_abc.MaybeAwaitableT[_T]], /) -> None:
        """Initiate a new lazy constant.

        Parameters
        ----------
        callback : collections.abc.Callable[..., tanjun.abc.MaybeAwaitable[_T]]
            Callback used to resolve this to a constant value.

            This supports dependency injection and may either be sync or asynchronous.
        """
        self._callback = injecting.CallbackDescriptor(callback)
        self._lock: typing.Optional[asyncio.Lock] = None
        self._value: typing.Optional[_T] = None

    @property
    def callback(self) -> injecting.CallbackDescriptor[_T]:
        """Descriptor of the callback used to get this constant's initial value."""
        return self._callback

    def get_value(self) -> typing.Optional[_T]:
        """Get the value of this constant if set, else `None`."""
        return self._value

    def reset(self: _LazyConstantT) -> _LazyConstantT:
        """Clear the internally stored value."""
        self._value = None
        return self

    def set_value(self: _LazyConstantT, value: _T) -> _LazyConstantT:
        """Set the constant value.

        Parameters
        ----------
        value : _T
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
        """Acquire this lazy constant to's asynchronous lock.

        This is used to ensure that the value is only generated once
        and should be kept acquired until `LazyConstant.set_value` is called.

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


def make_lc_resolver(type_: type[_T], /) -> collections.Callable[..., _T]:
    """Make an injected callback which resolves a LazyConstant.

    .. note::
        For this to work, a `LazyConstant` must've been set as a type
        dependency for the passed `type_`.

    Parameters
    ----------
    constant : type[_T]
        The type of the constant to resolve.

    Returns
    -------
    collections.abc.Callable[..., _T]
        An injected callback used to resolve the LazyConstant.

    Example
    -------
    ```py
    @component.with_command
    @tanjun.as_message_command
    async def command(
        ctx: tanjun.abc.MessageCommand,
        application: hikari.Application = tanjun.injected(
            callback=tanjun.make_lc_resolver(hikari.Application)
        )
    ) -> None:
        raise NotImplementedError

    ...

    async def resolve_app(
        client: tanjun.abc.Client = tanjun.injected(type=tanjun.abc.Client)
    ) -> hikari.Application:
        raise NotImplementedError

    tanjun.Client.from_gateway_bot(...).set_type_dependency(
        tanjun.LazyConstant[hikari.Application] = tanjun.LazyConstant(resolve_app)
    )
    ```
    """

    async def resolve(
        constant: LazyConstant[_T] = injecting.injected(type=LazyConstant[type_]),
        ctx: injecting.AbstractInjectionContext = injecting.injected(type=injecting.AbstractInjectionContext),
    ) -> _T:
        """Resolve a lazy constant."""
        if (value := constant.get_value()) is not None:
            return value

        async with constant.acquire():
            if (value := constant.get_value()) is not None:
                return value

            result = await constant.callback.resolve(ctx)
            constant.set_value(result)
            return result

    return resolve


async def fetch_my_user(
    client: tanjun_abc.Client = injecting.injected(type=tanjun_abc.Client),
) -> hikari.OwnUser:
    """Fetch the current user from the client's cache or rest client.

    .. note::
        This is used in the standard `LazyConstant[hikari.OwnUser]`
        dependency.

    Parameters
    ----------
    client : tanjun.abc.Client
        The client to use to fetch the user.

    Returns
    -------
    hikari.OwnUser
        The current user.

    Raises
    ------
    RuntimeError
        If the cache couldn't be used to get the current user and the REST
        client is not bound to a Bot token.
    """
    if client.cache and (user := client.cache.get_me()):
        return user

    if client.rest.token_type is not hikari.TokenType.BOT:
        raise RuntimeError("Cannot fetch current user with a REST client that's bound to a client credentials token")

    return await client.rest.fetch_my_user()


def set_standard_dependencies(client: injecting.InjectorClient, /) -> None:
    """Set the standard dependencies for Tanjun.

    Parameters
    ----------
    client: tanjun.injecting.InjectorClient
        The injector client to set the standard dependencies on.
    """
    (
        client.set_type_dependency(AbstractOwnerCheck, OwnerCheck()).set_type_dependency(
            LazyConstant[hikari.OwnUser], LazyConstant(fetch_my_user)
        )
    )


class _CacheCallback(typing.Generic[_T]):
    __slots__ = ("_callback", "_expire_after", "_last_called", "_lock", "_result")

    def __init__(
        self, callback: injecting.CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta]
    ) -> None:
        self._callback = injecting.CallbackDescriptor(callback)
        self._expire_after = expire_after.total_seconds() if expire_after else None
        self._last_called: typing.Optional[float] = None
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Union[_T, injecting.Undefined] = injecting.UNDEFINED

    @property
    def _has_expired(self) -> bool:
        return self._expire_after is not None and (
            not self._last_called or self._expire_after <= (time.monotonic() - self._last_called)
        )

    async def __call__(
        self,
        # Positional arg(s) may be guaranteed under some contexts so we want to pass those through.
        *args: typing.Any,
        ctx: injecting.AbstractInjectionContext = injecting.injected(type=injecting.AbstractInjectionContext),
    ) -> _T:
        if self._result is not injecting.UNDEFINED and not self._has_expired:
            assert not isinstance(self._result, injecting.Undefined)
            return self._result

        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._result is not injecting.UNDEFINED and not self._has_expired:
                assert not isinstance(self._result, injecting.Undefined)
                return self._result

            self._result = await self._callback.resolve(ctx, *args)
            self._last_called = time.monotonic()
            # This is set to None afterwards to ensure that it isn't persisted between loops.
            self._lock = None
            return self._result


def cache_callback(
    callback: injecting.CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta] = None
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
