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
"""Dependency used for managing owner checks."""
from __future__ import annotations

__all__: list[str] = ["AbstractOwners", "Owners"]

import abc
import asyncio
import datetime
import logging
import time
import typing

import hikari

from . import async_cache

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from .. import abc as tanjun


_T = typing.TypeVar("_T")
_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun")


class AbstractOwners(abc.ABC):
    """Interface used to check if a user is deemed to be the bot's "owner"."""

    __slots__ = ()

    @abc.abstractmethod
    async def check_ownership(self, client: tanjun.Client, user: hikari.User, /) -> bool:
        """Check whether this object is owned by the given object.

        Parameters
        ----------
        client
            The Tanjun client this check is being called by.
        user
            The user to check ownership for.

        Returns
        -------
        bool
            Whether the bot is owned by the provided user.
        """


class _CachedValue(typing.Generic[_T]):
    __slots__ = ("_expire_after", "_last_called", "_lock", "_result")

    def __init__(self, *, expire_after: typing.Optional[float]) -> None:
        self._expire_after = expire_after
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


_ApplicationCacheT = async_cache.SingleStoreCache[hikari.Application]


class Owners(AbstractOwners):
    """Default implementation of the owner check interface.

    !!! warning
        `fallback_to_application` is only possible when the REST client
        is bound to a Bot token or if a type dependency is registered for
        `tanjun.dependencies.SingleStoreCache[hikari.Application]`.
    """

    __slots__ = ("_fallback_to_application", "_owner_ids", "_value")

    def __init__(
        self,
        *,
        expire_after: typing.Union[datetime.timedelta, int, float] = datetime.timedelta(minutes=5),
        fallback_to_application: bool = True,
        owners: typing.Optional[hikari.SnowflakeishSequence[hikari.User]] = None,
    ) -> None:
        """Initiate a new owner check dependency.

        Parameters
        ----------
        expire_after
            The amount of time to cache application owner data for in seconds.

            This is only applicable if `rest` is also passed.
        fallback_to_application
            Whether this check should fallback to checking the application's owners
            if the user isn't in `owners`.

            This only works when the bot's rest client is bound to a Bot token or
            if `tanjun.dependencies.SingleStoreCache[hikari.Application]` is available.
        owners
            Sequence of objects and IDs of the users that are allowed to use the
            bot's owners-only commands.
        """
        if isinstance(expire_after, datetime.timedelta):
            expire_after = expire_after.total_seconds()
        else:
            expire_after = float(expire_after)

        if expire_after <= 0:
            raise ValueError("Expire after must be greater than 0 seconds")

        self._fallback_to_application = fallback_to_application
        self._owner_ids = {hikari.Snowflake(id_) for id_ in owners} if owners else set[hikari.Snowflake]()
        self._value = _CachedValue[hikari.Application](expire_after=expire_after)

    async def check_ownership(self, client: tanjun.Client, user: hikari.User, /) -> bool:
        if user.id in self._owner_ids:
            return True

        if not self._fallback_to_application:
            return False

        application_cache = client.get_type_dependency(_ApplicationCacheT)
        if application_cache and (application := await application_cache.get(default=None)):
            return user.id in application.team.members if application.team else user.id == application.owner.id

        if client.rest.token_type is not hikari.TokenType.BOT:
            _LOGGER.warning(
                "Owner checks cannot fallback to application owners when bound to an OAuth2 "
                "client credentials token and may always fail unless bound to a Bot token."
            )
            return False

        application = await self._value.acquire(client.rest.fetch_application)
        return user.id in application.team.members if application.team else user.id == application.owner.id
