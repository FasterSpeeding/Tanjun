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
"""Interface for an optional asynchronous gateway cache dependency.

This allows you to share data between instances using something like a redis cache
(for example) and will be used by standard Tanjun components as well as
extensions if implemented.
"""
from __future__ import annotations

__all__: list[str] = [
    "AbstractCache",
    "AbstractChannelBound",
    "AbstractGuildBound",
    "AbstractCacheIterator",
    "EntryDoesNotExist",
    "EntryNotFound",
    "EntryNotKnown",
]

import abc
import typing

import hikari

from .. import errors

_T = typing.TypeVar("_T")


class EntryNotFound(errors.TanjunError):
    """Raised when an entry is not found in the cache.

    .. note::
        Both `EntryDoesNotExist` and `EntryNotKnown` inherit from `EntryNotFound`
        so if you don't care about the semantic difference you can just catch
        `EntryNotFound`.
    """


class EntryNotKnown(EntryNotFound):
    """Raised when an entry is not known to the cache.

    .. note::
        This indicates that the cache doesn't know whether the entry exists.

    .. note::
        Both `EntryDoesNotExist` and `EntryNotKnown` inherit from `EntryNotFound`
        so if you don't care about the semantic difference you can just catch
        `EntryNotFound`.
    """


class EntryDoesNotExist(EntryNotFound):
    """Raised when an entry does not exist.

    .. note::
        This indicates that the cache is sure that the entry doesn't exist.

    .. note::
        Both `EntryDoesNotExist` and `EntryNotKnown` inherit from `EntryNotFound`
        so if you don't care about the semantic difference you can just catch
        `EntryNotFound`.
    """


class AbstractCacheIterator(hikari.LazyIterator[_T]):
    """Abstract interface of a cache resource asynchronous iterator.

    For more information on how this is used, see the documentation for
    `hikari.LazyIterator`.
    """

    __slots__ = ()

    @abc.abstractmethod
    async def len(self) -> int:
        """Get the length of the target resource.

        .. note::
            Unlike `AbstractCacheIterator.count`, this method will not deplete
            the iterator.

        Returns
        -------
        int
            The length of the targeted resource.
        """


class AbstractCache(abc.ABC, typing.Generic[_T]):
    """Abstract interface of a cache which stores globally identifiable resources.

    .. note::
        This will never be implemented for resources such as `hikari.Member`
        and `hikari.Presence` which aren'are only unique per-parent resource.
    """

    __slots__ = ()

    @abc.abstractmethod
    async def get(self, id_: hikari.Snowflakeish, /) -> _T:
        """Get an entry from this cache by ID.

        Parameters
        ----------
        id : hikari.Snowflakeish
            ID of the entry to get.

        Returns
        -------
        _T
            The found entry.

        Raises
        ------
        EntryNotKnown
            If the ID wasn't found.

            .. note::
                If you don't care about the semantic difference between these two
                errors then you can just catch `EntryNotFound`.
        EntryDoesNotExist
            If the ID wasn't found and the the entry definietly doesn't exist.

            .. note::
                If you don't care about the semantic difference between these two
                errors then you can just catch `EntryNotFound`.
        """

    @abc.abstractmethod
    async def iter(self) -> AbstractCacheIterator[_T]:
        """Asynchronously iterate over the globally cached entries for this resource.

        Returns
        -------
        AbstractCacheIterator[_T]
            An asynchronous iterator of the entries cached globally for this resource.

            .. note::
                For more information on how this is used, see the documentation for
                `hikari.LazyIterator`.
        """


class AbstractChannelBound(abc.ABC, typing.Generic[_T]):
    """Abstract interface of a cache which stores channel-bound resources."""

    __slots__ = ()

    @abc.abstractmethod
    async def get_from_channel(self, channel_id: hikari.Snowflakeish, id_: hikari.Snowflakeish, /) -> _T:
        """Get an entry from this cache for a specific channel by ID.

        Parameters
        ----------
        channel_id : hikari.Snowflakeish
            ID of the channel to get an entry for.
        id : hikari.Snowflakeish
            ID of the entry to get.

        Returns
        -------
        _T
            The found entry.

        Raises
        ------
        EntryNotKnown
            If the ID wasn't found.

            .. note::
                If you don't care about the semantic difference between these two
                errors then you can just catch `EntryNotFound`.
        EntryDoesNotExist
            If the ID wasn't found and the the entry definietly doesn't exist.

            .. note::
                If you don't care about the semantic difference between these two
                errors then you can just catch `EntryNotFound`.
        """

    @abc.abstractmethod
    async def iter_for_channel(self, channel_id: hikari.Snowflakeish, /) -> AbstractCacheIterator[_T]:
        """Asynchronously iterate over the entries entries cached for a channel.

        Parameters
        ----------
        channel_id : hikari.Snowflakeish
            ID of the channel to iterate over the entries cached for.

        Returns
        -------
        AbstractCacheIterator[_T]
            An asynchronous iterator of the entries cached for the specified channel.
        """

    @abc.abstractmethod
    async def iter(self) -> AbstractCacheIterator[_T]:
        """Asynchronously iterate over the globally cached entries for this resource.

        Returns
        -------
        AbstractCacheIterator[_T]
            An asynchronous iterator of the entries cached globally for this resource.

            .. note::
                For more information on how this is used, see the documentation for
                `hikari.LazyIterator`.
        """


class AbstractGuildBound(abc.ABC, typing.Generic[_T]):
    """Abstract interface of a cache which stores guild-bound resources."""

    __slots__ = ()

    @abc.abstractmethod
    async def get_from_guild(self, guild_id: hikari.Snowflakeish, id_: hikari.Snowflakeish, /) -> _T:
        """Get an entry from this cache for a specific guild by ID.

        Parameters
        ----------
        guild_id : hikari.Snowflakeish
            ID of the guild to get an entry for.
        id : hikari.Snowflakeish
            ID of the entry to get.

        Returns
        -------
        _T
            The found entry.

        Raises
        ------
        EntryNotKnown
            If the ID wasn't found.

            .. note::
                If you don't care about the semantic difference between these two
                errors then you can just catch `EntryNotFound`.
        EntryDoesNotExist
            If the ID wasn't found and the the entry definietly doesn't exist.

            .. note::
                If you don't care about the semantic difference between these two
                errors then you can just catch `EntryNotFound`.
        """

    @abc.abstractmethod
    async def iter_for_guild(self, guild_id: hikari.Snowflakeish, /) -> AbstractCacheIterator[_T]:
        """Asynchronously iterate over the entries entries cached for a guild.

        Parameters
        ----------
        guild_id : hikari.Snowflakeish
            ID of the guild to iterate over the entries cached for.

        Returns
        -------
        AbstractCacheIterator[_T]
            An asynchronous iterator of the entries cached for the specified guild.

            .. note::
                For more information on how this is used, see the documentation for
                `hikari.LazyIterator`.
        """

    @abc.abstractmethod
    async def iter(self) -> AbstractCacheIterator[_T]:
        """Asynchronously iterate over the globally cached entries for this resource.

        Returns
        -------
        AbstractCacheIterator[_T]
            An asynchronous iterator of the entries cached globally for this resource.

            .. note::
                For more information on how this is used, see the documentation for
                `hikari.LazyIterator`.
        """
