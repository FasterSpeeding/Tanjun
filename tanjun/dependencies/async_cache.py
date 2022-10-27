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
r"""Interface for an optional asynchronous gateway cache dependency.

This allows you to share data between instances using something like a redis cache
(for example) and will be used by standard Tanjun components as well as
extensions if implemented.

!!! note
    While there aren't any standard implementations for these interfaces, a
    Redis implementation of this for the types found in Hikari's gateway cache
    can be found in [hikari-sake](https://github.com/FasterSpeeding/Sake)
    \>=v1.0.1a1 (exposed by [sake.redis.ResourceClient.add_to_tanjun][]).

Tanjun will use the following type dependencies for these interfaces if they are
registered with the client:

* `AsyncCache[str, hikari.InviteWithMetadata]`
* `SfCache[hikari.PermissibleGuildChannel]`
* `SfCache[hikari.GuildThreadChannel]`
* `SfCache[hikari.KnownCustomEmoji]`
* `SfCache[hikari.Guild]`
* `SfCache[hikari.Role]`
* `SfCache[hikari.User]`
* `SfGuildBound[hikari.Member]`
* `SfGuildBound[hikari.MemberPresence]`
* `SfGuildBound[hikari.VoiceState]`
* `SfGuildBound[hikari.Role]`
* `SingleStoreCache[hikari.OwnUser]`
* `SingleStoreCache[hikari.Application]`
* `SingleStoreCache[hikari.AuthorizationApplication]`
"""
from __future__ import annotations

__all__: list[str] = [
    "AsyncCache",
    "CacheIterator",
    "CacheMissError",
    "ChannelBoundCache",
    "EntryNotFound",
    "GuildBoundCache",
    "SfCache",
    "SfChannelBound",
    "SfGuildBound",
    "SingleStoreCache",
]

import abc
import typing

import hikari

from .. import errors

_DefaultT = typing.TypeVar("_DefaultT")
_KeyT = typing.TypeVar("_KeyT")
_ValueT = typing.TypeVar("_ValueT")


class CacheMissError(errors.TanjunError):
    """Raised when an entry isn't found in the cache.

    !!! note
        [EntryNotFound][tanjun.dependencies.EntryNotFound] inherits from this
        error and will only be raised if the cache knows that the entry
        doesn't exist.
    """


class EntryNotFound(CacheMissError):
    """Raised when an entry does not exist.

    !!! note
        This is a specialisation of [CacheMissError][tanjun.dependencies.CacheMissError]
        which indicates that the cache is sure that the entry doesn't exist.
    """


class CacheIterator(hikari.LazyIterator[_ValueT]):
    """Abstract interface of a cache resource asynchronous iterator.

    For more information on how this is used, see the documentation for
    [hikari.iterators.LazyIterator][].
    """

    __slots__ = ()

    @abc.abstractmethod
    async def len(self) -> int:
        """Get the length of the target resource.

        !!! note
            Unlike [tanjun.dependencies.CacheIterator.count][], this method
            will not deplete the iterator.

        Returns
        -------
        int
            The length of the targeted resource.
        """


class SingleStoreCache(abc.ABC, typing.Generic[_ValueT]):
    """Abstract interface of a cache which stores one resource.

    !!! note
        This is mostly just for the [hikari.users.OwnUser][] cache store.
    """

    __slots__ = ()

    @abc.abstractmethod
    async def get(self, *, default: _DefaultT = ...) -> typing.Union[_ValueT, _DefaultT]:
        """Get the entry.

        Parameters
        ----------
        default
            The default value to return if an entry wasn't found.

            If provided then no errors will be raised when no entry is found.

        Returns
        -------
        _ValueT | _DefaultT
            The found entry or the default if any was provided.

        Raises
        ------
        CacheMissError
            If the entry wasn't found.

            This won't be raised if `default` is passed.
        EntryNotFound
            If the entry wasn't found and the the entry definitely doesn't exist.

            This won't be raised if `default` is passed.

            This is a specialisation of `CacheMissError` and thus may be
            caught as `CacheMissError and otherwise would need to be before
            `CacheMissError` in a try, multiple catch statement.
        """


class AsyncCache(abc.ABC, typing.Generic[_KeyT, _ValueT]):
    """Abstract interface of a cache which stores globally identifiable resources.

    !!! note
        This will never be implemented for resources such as [hikari.guilds.Member][]
        and [hikari.presences.MemberPresence][] which are only unique per-parent resource.
    """

    __slots__ = ()

    @abc.abstractmethod
    async def get(self, key: _KeyT, /, *, default: _DefaultT = ...) -> typing.Union[_ValueT, _DefaultT]:
        """Get an entry from this cache by ID.

        Parameters
        ----------
        key
            Unique key of the entry to get; this will often be a snowflake.
        default
            The default value to return if an entry wasn't found.

            If provided then no errors will be raised when no entry is found.

        Returns
        -------
        _ValueT | _DefaultT
            The found entry or the default if any was provided.

        Raises
        ------
        CacheMissError
            If the entry wasn't found.

            This won't be raised if `default` is passed.
        EntryNotFound
            If the entry wasn't found and the the entry definitely doesn't exist.

            This won't be raised if `default` is passed.

            This is a specialisation of `CacheMissError` and thus may be
            caught as `CacheMissError and otherwise would need to be before
            `CacheMissError` in a try, multiple catch statement.
        """

    @abc.abstractmethod
    def iter_all(self) -> CacheIterator[_ValueT]:
        """Asynchronously iterate over the globally cached entries for this resource.

        !!! note
            For more information on how this is used, see the documentation for
            [hikari.iterators.LazyIterator][].

        Returns
        -------
        CacheIterator[_ValueT]
            An asynchronous iterator of the entries cached globally for this resource.
        """


SfCache = AsyncCache[hikari.Snowflakeish, _ValueT]
"""Alias of [tanjun.dependencies.AsyncCache][] where the key is a snowflake."""


class ChannelBoundCache(abc.ABC, typing.Generic[_KeyT, _ValueT]):
    """Abstract interface of a cache which stores channel-bound resources."""

    __slots__ = ()

    @abc.abstractmethod
    async def get_from_channel(
        self, channel_id: hikari.Snowflakeish, key: _KeyT, /, *, default: _DefaultT = ...
    ) -> typing.Union[_ValueT, _DefaultT]:
        """Get an entry from this cache for a specific channel by ID.

        Parameters
        ----------
        channel_id
            ID of the channel to get an entry for.
        key
            Unique key of the entry to get; this will usually be a snowflake.
        default
            The default value to return if an entry wasn't found.

            If provided then no errors will be raised when no entry is found.

        Returns
        -------
        _ValueT | _DefaultT
            The found entry or the default if any was provided.

        Raises
        ------
        CacheMissError
            If the entry wasn't found.

            This won't be raised if `default` is passed.
        EntryNotFound
            If the entry wasn't found and the the entry definitely doesn't exist.

            This won't be raised if `default` is passed.

            This is a specialisation of `CacheMissError` and thus may be
            caught as `CacheMissError and otherwise would need to be before
            `CacheMissError` in a try, multiple catch statement.
        """

    @abc.abstractmethod
    def iter_for_channel(self, channel_id: hikari.Snowflakeish, /) -> CacheIterator[_ValueT]:
        """Asynchronously iterate over the entries entries cached for a channel.

        Parameters
        ----------
        channel_id
            ID of the channel to iterate over the entries cached for.

        Returns
        -------
        CacheIterator[_ValueT]
            An asynchronous iterator of the entries cached for the specified channel.
        """

    @abc.abstractmethod
    def iter_all(self) -> CacheIterator[_ValueT]:
        """Asynchronously iterate over the globally cached entries for this resource.

        !!! note
            For more information on how this is used, see the documentation for
            [hikari.iterators.LazyIterator][].

        Returns
        -------
        CacheIterator[_ValueT]
            An asynchronous iterator of the entries cached globally for this resource.
        """


SfChannelBound = ChannelBoundCache[hikari.Snowflakeish, _ValueT]
"""Alias of [tanjun.dependencies.ChannelBoundCache][] where the key is a snowflake."""


class GuildBoundCache(abc.ABC, typing.Generic[_KeyT, _ValueT]):
    """Abstract interface of a cache which stores guild-bound resources."""

    __slots__ = ()

    @abc.abstractmethod
    async def get_from_guild(
        self, guild_id: hikari.Snowflakeish, key: _KeyT, /, *, default: _DefaultT = ...
    ) -> typing.Union[_ValueT, _DefaultT]:
        """Get an entry from this cache for a specific guild by ID.

        Parameters
        ----------
        guild_id
            ID of the guild to get an entry for.
        key
            Unique key of the entry to get; this will usually be a snowflake.
        default
            The default value to return if an entry wasn't found.

            If provided then no errors will be raised when no entry is found.

        Returns
        -------
        _ValueT | _DefaultT
            The found entry or the default if any was provided.

        Raises
        ------
        CacheMissError
            If the entry wasn't found.

            This won't be raised if `default` is passed.
        EntryNotFound
            If the entry wasn't found and the the entry definitely doesn't exist.

            This won't be raised if `default` is passed.

            This is a specialisation of `CacheMissError` and thus may be
            caught as `CacheMissError and otherwise would need to be before
            `CacheMissError` in a try, multiple catch statement.
        """

    @abc.abstractmethod
    def iter_for_guild(self, guild_id: hikari.Snowflakeish, /) -> CacheIterator[_ValueT]:
        """Asynchronously iterate over the entries entries cached for a guild.

        !!! note
            For more information on how this is used, see the documentation for
            [hikari.iterators.LazyIterator][].

        Parameters
        ----------
        guild_id
            ID of the guild to iterate over the entries cached for.

        Returns
        -------
        CacheIterator[_ValueT]
            An asynchronous iterator of the entries cached for the specified guild.
        """

    @abc.abstractmethod
    def iter_all(self) -> CacheIterator[_ValueT]:
        """Asynchronously iterate over the globally cached entries for this resource.

        !!! note
            For more information on how this is used, see the documentation for
            [hikari.iterators.LazyIterator][].

        Returns
        -------
        CacheIterator[_ValueT]
            An asynchronous iterator of the entries cached globally for this resource.
        """


SfGuildBound = GuildBoundCache[hikari.Snowflakeish, _ValueT]
"""Alias of [tanjun.dependencies.GuildBoundCache][] where the key is a snowflake."""
