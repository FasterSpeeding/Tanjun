# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
"""Functions and classes used to enable more Discord oriented argument converters."""
from __future__ import annotations

__all__: list[str] = [
    "ToChannel",
    "ToEmoji",
    "ToGuild",
    "ToInvite",
    "ToInviteWithMetadata",
    "ToMember",
    "ToMessage",
    "ToPresence",
    "ToRole",
    "ToUser",
    "ToVoiceState",
    "from_datetime",
    "parse_channel_id",
    "parse_emoji_id",
    "parse_message_id",
    "parse_role_id",
    "parse_snowflake",
    "parse_user_id",
    "search_channel_ids",
    "search_emoji_ids",
    "search_role_ids",
    "search_snowflakes",
    "search_user_ids",
    "to_bool",
    "to_channel",
    "to_color",
    "to_colour",
    "to_datetime",
    "to_emoji",
    "to_guild",
    "to_invite",
    "to_invite_with_metadata",
    "to_member",
    "to_message",
    "to_presence",
    "to_role",
    "to_snowflake",
    "to_user",
    "to_voice_state",
]

import datetime
import functools
import logging
import operator
import re
import typing
import urllib.parse as urlparse
from collections import abc as collections

import alluka
import hikari
import typing_extensions

from . import _internal
from . import abc as tanjun
from .dependencies import async_cache

if typing.TYPE_CHECKING:
    from . import parsing

    _PartialChannelT = typing.TypeVar("_PartialChannelT", bound=hikari.PartialChannel)


_SnowflakeIsh = typing.Union[str, int]
_ValueT = typing.TypeVar("_ValueT")
_LOGGER = logging.getLogger("hikari.tanjun.conversion")


class BaseConverter:
    """Base class for the standard converters.

    !!! warning
        Inheriting from this is completely unnecessary and should be avoided
        for people using the library unless they know what they're doing.

    This is detail of the standard implementation and isn't guaranteed to work
    between implementations but will work for implementations which provide
    the standard dependency injection or special cased support for these.

    While it isn't necessary to subclass this to implement your own converters
    since dependency injection can be used to access fields like the current Context,
    this class introduces some niceties around stuff like state warnings.
    """

    __slots__ = ("__weakref__",)

    @property
    @typing_extensions.deprecated("Use .caches instead")
    def async_caches(self) -> collections.Sequence[typing.Any]:
        """Deprecated property."""
        return list({v[0] for v in self.caches})

    @property
    @typing_extensions.deprecated("Use .caches instead")
    def cache_components(self) -> hikari.api.CacheComponents:
        """Deprecated property."""
        if self.caches:
            return functools.reduce(operator.ior, (v[1] for v in self.caches))

        return hikari.api.CacheComponents.NONE

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        """Caches the converter takes advantage of.

        This returns a tuple of async cache types and the relevant cache components
        which will be needed if said async cache isn't implemented.

        !!! note
            Unless [BaseConverter.requires_cache][tanjun.conversion.BaseConverter.requires_cache]
            is [True][], these cache components aren't necessary but simply
            avoid the converter from falling back to REST requests.
        """
        return []

    @property
    @typing_extensions.deprecated("Use .caches instead")
    def intents(self) -> hikari.Intents:
        """Deprecated property."""
        if self.caches:
            return functools.reduce(operator.ior, (v[2] for v in self.caches))

        return hikari.Intents.NONE

    @property
    def requires_cache(self) -> bool:
        """Whether this converter relies on the relevant cache stores to work.

        If this is [True][] then this converter will not function properly
        in an environment
        [BaseConverter.intents][tanjun.conversion.BaseConverter.intents] or
        [BaseConverter.cache_components][tanjun.conversion.BaseConverter.cache_components]
        isn't satisfied and will never fallback to REST requests.
        """
        return False

    def check_client(self, client: tanjun.Client, parent_name: str, /) -> None:
        """Check that this converter will work with the given client.

        This never raises any errors but simply warns the user if the converter
        is not compatible with the given client.

        Parameters
        ----------
        client
            The client to check against.
        parent_name
            The name of the converter's parent, used for warning messages.
        """
        enabled_components = client.cache and client.cache.settings.components or hikari.api.CacheComponents.NONE
        enabled_intents = client.shards.intents if client.shards else hikari.Intents.NONE
        missing_components = hikari.api.CacheComponents.NONE
        needed_intents = hikari.Intents.NONE
        for cache_dep_type, component, intents in self.caches:
            if client.injector.get_type_dependency(cache_dep_type, default=None) is not None:
                continue

            needed_intents |= intents
            if current_missing := component & ~enabled_components:
                missing_components |= current_missing

        if missing_components:
            if self.requires_cache:
                _LOGGER.warning(
                    "Converter %r (registered with %s) will fail without the following cache components: %s",
                    self,
                    parent_name,
                    missing_components,
                )

            else:
                _LOGGER.info(
                    "Converter %r (registered with %s) may not perform "
                    "optimally without the following cache components: %s",
                    self,
                    parent_name,
                    missing_components,
                )

        if missing_intents := needed_intents & ~enabled_intents:
            if self.requires_cache:
                _LOGGER.warning(
                    "Converter %r (registered with %s) will fail without the following intents: %s",
                    self,
                    parent_name,
                    missing_intents,
                )

            else:
                _LOGGER.info(
                    "Converter %r (registered with %s) may not perform as expected without the following intents: %s",
                    self,
                    parent_name,
                    missing_intents,
                )


_DmCacheT = async_cache.SfCache[hikari.DMChannel]
_GuildChannelCacheT = async_cache.SfCache[hikari.PermissibleGuildChannel]
_ThreadCacheT = async_cache.SfCache[hikari.GuildThreadChannel]


class ToChannel(BaseConverter):
    """Standard converter for channels mentions/IDs.

    For a standard instance of this see [to_channel][tanjun.conversion.to_channel].
    """

    __slots__ = ("_allowed_types", "_allowed_types_repr", "_dms_enabled", "_guilds_enabled", "_threads_enabled")

    def __init__(
        self,
        *,
        allowed_types: typing.Optional[collections.Collection[typing.Union[type[hikari.PartialChannel], int]]] = None,
        include_dms: bool = True,
    ) -> None:
        """Initialise a to channel converter.

        Parameters
        ----------
        allowed_types
            Collection of channel types and classes to allow.

            If this is [None][] then all channel types will be allowed.
        include_dms
            Whether to include DM channels in the results.

            May lead to a lot of extra fallbacks to REST requests if
            the client doesn't have a registered async cache for DMs.
        """
        allowed_types_ = _internal.parse_channel_types(*allowed_types or ())
        dm_types = _internal.CHANNEL_TYPES[hikari.PrivateChannel]

        if not include_dms:
            if allowed_types is None:
                allowed_types = _internal.CHANNEL_TYPES[hikari.PartialChannel].difference(dm_types)
                allowed_types_ = list(allowed_types)

            else:
                for channel_type in dm_types:
                    try:
                        allowed_types_.remove(channel_type)
                    except ValueError:
                        pass

        self._allowed_types = set(allowed_types_) if allowed_types is not None else None
        self._dms_enabled = include_dms and (
            self._allowed_types is None or any(map(self._allowed_types.__contains__, dm_types))
        )
        self._guilds_enabled = self._allowed_types is None or any(
            map(self._allowed_types.__contains__, _internal.CHANNEL_TYPES[hikari.PermissibleGuildChannel])
        )
        self._threads_enabled = self._allowed_types is None or any(
            map(self._allowed_types.__contains__, _internal.CHANNEL_TYPES[hikari.GuildThreadChannel])
        )

        if not allowed_types_:
            self._allowed_types_repr = ""

        elif len(allowed_types_) == 1:
            self._allowed_types_repr = _internal.repr_channel(allowed_types_[0])

        else:
            self._allowed_types_repr = ", ".join(map(_internal.repr_channel, allowed_types_[:-1]))
            self._allowed_types_repr += f" and {_internal.repr_channel(allowed_types_[-1])}"

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        results: list[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]] = []

        if self._guilds_enabled:
            results.append((_GuildChannelCacheT, hikari.api.CacheComponents.GUILD_CHANNELS, hikari.Intents.GUILDS))

        if self._dms_enabled:
            results.append((_DmCacheT, hikari.api.CacheComponents.NONE, hikari.Intents.NONE))

        if self._threads_enabled:
            results.append((_ThreadCacheT, hikari.api.CacheComponents.NONE, hikari.Intents.GUILDS))

        return results

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    def _assert_type(self, channel: _PartialChannelT, /) -> _PartialChannelT:
        if self._allowed_types is not None and channel.type not in self._allowed_types:
            raise ValueError(
                f"Only the following channel types are allowed for this argument: {self._allowed_types_repr}"
            )

        return channel

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_GuildChannelCacheT]] = None,
        dm_cache: alluka.Injected[typing.Optional[_DmCacheT]] = None,
        thread_cache: alluka.Injected[typing.Optional[_ThreadCacheT]] = None,
    ) -> hikari.PartialChannel:
        channel_id = parse_channel_id(argument, message="No valid channel mention or ID found")
        if ctx.cache and (channel_ := ctx.cache.get_guild_channel(channel_id)):
            return self._assert_type(channel_)

        # Ensure bool for MyPy compat
        no_guild_channel = bool(
            (cache or not self._guilds_enabled)
            and (thread_cache or not self._threads_enabled)
            and (dm_cache or not self._dms_enabled)
        )
        if cache:
            try:
                return self._assert_type(await cache.get(channel_id))

            except async_cache.EntryNotFound:
                pass

            except async_cache.CacheMissError:
                no_guild_channel = False

        if thread_cache and self._threads_enabled:
            try:
                return self._assert_type(await thread_cache.get(channel_id))

            except async_cache.EntryNotFound:
                pass

            except async_cache.CacheMissError:
                no_guild_channel = False

        if dm_cache and self._dms_enabled:
            try:
                return self._assert_type(await dm_cache.get(channel_id))

            except async_cache.EntryNotFound:
                pass

            except async_cache.CacheMissError:
                no_guild_channel = False

        if not no_guild_channel:
            try:
                return self._assert_type(await ctx.rest.fetch_channel(channel_id))

            except hikari.NotFoundError:
                pass

        raise ValueError("Couldn't find channel")


@typing_extensions.deprecated("Use ToChannel instead")
class ChannelConverter(ToChannel):
    """Deprecated alias of [ToChannel][tanjun.conversion.ToChannel]."""

    __slots__ = ()


_EmojiCacheT = async_cache.SfCache[hikari.KnownCustomEmoji]


class ToEmoji(BaseConverter):
    """Standard converter for custom emojis.

    For a standard instance of this see [to_emoji][tanjun.conversion.to_emoji].

    !!! note
        If you just want to convert inpute to a
        [hikari.Emoji][hikari.emojis.Emoji],
        [hikari.CustomEmoji][hikari.emojis.CustomEmoji] or
        [hikari.UnicodeEmoji][hikari.emojis.UnicodeEmoji] without making any
        cache or REST calls then you can just use the relevant
        [Emoji.parse][hikari.emojis.Emoji.parse],
        [CustomEmoji.parse][hikari.emojis.CustomEmoji.parse] or
        [UnicodeEmoji.parse][hikari.emojis.UnicodeEmoji.parse] methods.
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [(_EmojiCacheT, hikari.api.CacheComponents.EMOJIS, hikari.Intents.GUILD_EMOJIS | hikari.Intents.GUILDS)]

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_EmojiCacheT]] = None,
    ) -> hikari.KnownCustomEmoji:
        emoji_id = parse_emoji_id(argument, message="No valid emoji or emoji ID found")

        if ctx.cache and (emoji := ctx.cache.get_emoji(emoji_id)):
            return emoji

        if cache:
            try:
                return await cache.get(emoji_id)

            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find emoji") from None

            except async_cache.CacheMissError:
                pass

        if ctx.guild_id:
            try:
                return await ctx.rest.fetch_emoji(ctx.guild_id, emoji_id)

            except hikari.NotFoundError:
                pass

        raise ValueError("Couldn't find emoji")


@typing_extensions.deprecated("Use ToEmoji")
class EmojiConverter(ToEmoji):
    """Deprecated alias of [ToEmoji][tanjun.conversion.ToEmoji]."""

    __slots__ = ()


_GuildCacheT = async_cache.SfCache[hikari.Guild]


class ToGuild(BaseConverter):
    """Standard converter for guilds.

    For a standard instance of this see [to_guild][tanjun.conversion.to_guild].
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [(_GuildCacheT, hikari.api.CacheComponents.GUILDS, hikari.Intents.GUILDS)]

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_GuildCacheT]] = None,
    ) -> hikari.Guild:
        guild_id = parse_snowflake(argument, message="No valid guild ID found")
        if ctx.cache and (guild := ctx.cache.get_guild(guild_id)):
            return guild

        if cache:
            try:
                return await cache.get(guild_id)

            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find guild") from None

            except async_cache.CacheMissError:
                pass

        try:
            return await ctx.rest.fetch_guild(guild_id)

        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find guild")


@typing_extensions.deprecated("Use ToGuild")
class GuildConverter(ToGuild):
    """Deprecated alias of [ToGuild][tanjun.conversion.ToGuild]."""

    __slots__ = ()


_InviteCacheT = async_cache.AsyncCache[str, hikari.InviteWithMetadata]


class ToInvite(BaseConverter):
    """Standard converter for invites."""

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [(_InviteCacheT, hikari.api.CacheComponents.INVITES, hikari.Intents.GUILD_INVITES)]

    async def __call__(
        self,
        argument: str,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_InviteCacheT]] = None,
    ) -> hikari.Invite:
        if ctx.cache and (invite := ctx.cache.get_invite(argument)):
            return invite

        if cache:
            try:
                return await cache.get(argument)

            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find invite") from None

            except async_cache.CacheMissError:
                pass

        try:
            return await ctx.rest.fetch_invite(argument)
        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find invite")


@typing_extensions.deprecated("Use ToInvite")
class InviteConverter(ToInvite):
    """Deprecated alias of [ToInvite][tanjun.conversion.ToInvite]."""

    __slots__ = ()


class ToInviteWithMetadata(BaseConverter):
    """Standard converter for invites with metadata.

    For a standard instance of this see
    [to_invite_with_metadata][tanjun.conversion.to_invite_with_metadata].

    !!! note
        Unlike [InviteConverter][tanjun.conversion.InviteConverter], this
        converter is cache dependent.
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [(_InviteCacheT, hikari.api.CacheComponents.INVITES, hikari.Intents.GUILD_INVITES)]

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return True

    async def __call__(
        self,
        argument: str,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_InviteCacheT]] = None,
    ) -> hikari.InviteWithMetadata:
        if ctx.cache and (invite := ctx.cache.get_invite(argument)):
            return invite

        if cache and (invite := await cache.get(argument)):
            return invite

        raise ValueError("Couldn't find invite")


@typing_extensions.deprecated("Use ToInviteWithMetadata")
class InviteWithMetadataConverter(ToInviteWithMetadata):
    """Deprecated alias of [ToInviteWithMetadata][tanjun.conversion.ToInviteWithMetadata]."""

    __slots__ = ()


_MemberCacheT = async_cache.SfGuildBound[hikari.Member]


class ToMember(BaseConverter):
    """Standard converter for guild members.

    For a standard instance of this see [to_member][tanjun.conversion.to_member].

    This converter allows both mentions, raw IDs and partial usernames/nicknames
    and only works within a guild context.
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [
            (_MemberCacheT, hikari.api.CacheComponents.MEMBERS, hikari.Intents.GUILD_MEMBERS | hikari.Intents.GUILDS)
        ]

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_MemberCacheT]] = None,
    ) -> hikari.Member:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a member from a DM channel")

        try:
            user_id = parse_user_id(argument, message="No valid user mention or ID found")

        except ValueError:
            if isinstance(argument, str):
                try:
                    return (await ctx.rest.search_members(ctx.guild_id, argument))[0]

                except (hikari.NotFoundError, IndexError):
                    pass

        else:
            if ctx.cache and (member := ctx.cache.get_member(ctx.guild_id, user_id)):
                return member

            if cache:
                try:
                    return await cache.get_from_guild(ctx.guild_id, user_id)

                except async_cache.EntryNotFound:
                    raise ValueError("Couldn't find member in this guild") from None

                except async_cache.CacheMissError:
                    pass

            try:
                return await ctx.rest.fetch_member(ctx.guild_id, user_id)

            except hikari.NotFoundError:
                pass

        raise ValueError("Couldn't find member in this guild")


@typing_extensions.deprecated("Use ToMember")
class MemberConverter(ToMember):
    """Deprecated alias of [ToMember][tanjun.conversion.ToMember]."""

    __slots__ = ()


_PresenceCacheT = async_cache.SfGuildBound[hikari.MemberPresence]


class ToPresence(BaseConverter):
    """Standard converter for presences.

    For a standard instance of this see [to_presence][tanjun.conversion.to_presence].

    This converter is cache dependent and only works in a guild context.
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [
            (
                _PresenceCacheT,
                hikari.api.CacheComponents.PRESENCES,
                hikari.Intents.GUILD_PRESENCES | hikari.Intents.GUILDS,
            )
        ]

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return True

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_PresenceCacheT]] = None,
    ) -> hikari.MemberPresence:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a presence from a DM channel")

        user_id = parse_user_id(argument, message="No valid member mention or ID found")
        if ctx.cache and (presence := ctx.cache.get_presence(ctx.guild_id, user_id)):
            return presence

        if cache and (presence := await cache.get_from_guild(ctx.guild_id, user_id, default=None)):
            return presence

        raise ValueError("Couldn't find presence in current guild")


@typing_extensions.deprecated("Use ToPresence")
class PresenceConverter(ToPresence):
    """Deprecated alias of [ToPresence][tanjun.conversion.ToPresence]."""

    __slots__ = ()


_RoleCacheT = async_cache.SfCache[hikari.Role]


class ToRole(BaseConverter):
    """Standard converter for guild roles.

    For a standard instance of this see [to_role][tanjun.conversion.to_role].
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        return [(_RoleCacheT, hikari.api.CacheComponents.ROLES, hikari.Intents.GUILDS)]

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_RoleCacheT]] = None,
    ) -> hikari.Role:
        role_id = parse_role_id(argument, message="No valid role mention or ID found")
        if ctx.cache and (role := ctx.cache.get_role(role_id)):
            return role

        if cache:
            try:
                return await cache.get(role_id)

            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find role") from None

            except async_cache.CacheMissError:
                pass

        if ctx.guild_id:
            for role in await ctx.rest.fetch_roles(ctx.guild_id):
                if role.id == role_id:
                    return role

        raise ValueError("Couldn't find role")


@typing_extensions.deprecated("Use ToRole")
class RoleConverter(ToRole):
    """Deprecated alias of [ToRole][tanjun.conversion.ToRole]."""

    __slots__ = ()


_UserCacheT = async_cache.SfCache[hikari.User]


class ToUser(BaseConverter):
    """Standard converter for users.

    For a standard instance of this see [to_user][tanjun.conversion.to_user].
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [(_UserCacheT, hikari.api.CacheComponents.NONE, hikari.Intents.GUILDS | hikari.Intents.GUILD_MEMBERS)]

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_UserCacheT]] = None,
    ) -> hikari.User:
        # TODO: search by name if this is a guild context
        user_id = parse_user_id(argument, message="No valid user mention or ID found")
        if ctx.cache and (user := ctx.cache.get_user(user_id)):
            return user

        if cache:
            try:
                return await cache.get(user_id)

            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find user") from None

            except async_cache.CacheMissError:
                pass

        try:
            return await ctx.rest.fetch_user(user_id)

        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find user")


@typing_extensions.deprecated("Use ToUser")
class UserConverter(ToUser):
    """Deprecated alias of [ToUser][tanjun.conversion.ToUser]."""

    __slots__ = ()


_MessageCacheT = async_cache.SfCache[hikari.Message]


class ToMessage(BaseConverter):
    """Standard converter for messages.

    For a standard instance of this see [to_message][tanjun.conversion.to_message].
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [
            (
                _MessageCacheT,
                hikari.api.CacheComponents.MESSAGES,
                hikari.Intents.GUILD_MESSAGES | hikari.Intents.DM_MESSAGES,
            )
        ]

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_MessageCacheT]] = None,
    ) -> hikari.Message:
        channel_id, message_id = parse_message_id(argument)
        if ctx.cache and (message := ctx.cache.get_message(message_id)):
            return message

        if cache:
            try:
                return await cache.get(message_id)

            except async_cache.EntryNotFound:
                raise ValueError("Couldn't find message") from None

            except async_cache.CacheMissError:
                pass

        try:
            return await ctx.rest.fetch_message(channel_id or ctx.channel_id, message_id)

        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find message")


_VoiceStateCacheT = async_cache.SfGuildBound[hikari.VoiceState]


class ToVoiceState(BaseConverter):
    """Standard converter for voice states.

    For a standard instance of this see [to_voice_state][tanjun.conversion.to_voice_state].

    !!! note
        This converter is cache dependent and only works in a guild context.
    """

    __slots__ = ()

    @property
    def caches(self) -> collections.Sequence[tuple[typing.Any, hikari.api.CacheComponents, hikari.Intents]]:
        # <<inherited docstring from BaseConverter>>.
        return [
            (
                _VoiceStateCacheT,
                hikari.api.CacheComponents.VOICE_STATES,
                hikari.Intents.GUILD_VOICE_STATES | hikari.Intents.GUILDS,
            )
        ]

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return True

    async def __call__(
        self,
        argument: _SnowflakeIsh,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_VoiceStateCacheT]] = None,
    ) -> hikari.VoiceState:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a voice state from a DM channel")

        user_id = parse_user_id(argument, message="No valid user mention or ID found")

        if ctx.cache and (state := ctx.cache.get_voice_state(ctx.guild_id, user_id)):
            return state

        if cache and (state := await cache.get_from_guild(ctx.guild_id, user_id, default=None)):
            return state

        raise ValueError("Voice state couldn't be found for current guild")


@typing_extensions.deprecated("Use ToVoiceState")
class VoiceStateConverter(ToVoiceState):
    """Deprecated alias of [ToVoiceState][tanjun.conversion.ToVoiceState]."""

    __slots__ = ()


class _IDMatcherSigProto(typing.Protocol):
    def __call__(self, value: _SnowflakeIsh, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        raise NotImplementedError


def _make_snowflake_parser(regex: re.Pattern[str], /) -> _IDMatcherSigProto:
    def parse(value: _SnowflakeIsh, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        """Parse a snowflake from a string or int value.

        !!! note
            This only allows the relevant entity's mention format if applicable.

        Parameters
        ----------
        value
            The value to parse (this argument can only be passed positionally).
        message
            The error message to raise if the value cannot be parsed.

        Returns
        -------
        hikari.snowflakes.Snowflake
            The parsed snowflake.

        Raises
        ------
        ValueError
            If the value cannot be parsed.
        """
        result: typing.Optional[hikari.Snowflake] = None
        if isinstance(value, int) or value.isdigit():
            result = hikari.Snowflake(value)

        else:
            capture = next(regex.finditer(value), None)
            result = hikari.Snowflake(capture.groups()[0]) if capture else None

        # We should also range check the provided ID.
        if result is not None and _range_check(result):
            return result

        raise ValueError(message) from None

    return parse


_IDSearcherSig = collections.Callable[[_SnowflakeIsh], list[hikari.Snowflake]]


def _range_check(snowflake: hikari.Snowflake, /) -> bool:
    return snowflake.min() <= snowflake <= snowflake.max()


def _make_snowflake_searcher(regex: re.Pattern[str], /) -> _IDSearcherSig:
    def parse(value: _SnowflakeIsh, /) -> list[hikari.Snowflake]:
        """Get the snowflakes in a string.

        !!! note
            This only allows the relevant entity's mention format if applicable.

        Parameters
        ----------
        value
            The value to parse (this argument can only be passed positionally).

        Returns
        -------
        list[hikari.snowflakes.Snowflake]
            List of the IDs found in the string.
        """
        if isinstance(value, str):
            if value.isdigit() and _range_check(result := hikari.Snowflake(value)):
                return [result]

            results = filter(_range_check, (hikari.Snowflake(match.groups()[0]) for match in regex.finditer(value)))
            other_ids_iter = map(hikari.Snowflake, filter(str.isdigit, value.split()))
            return [*results, *filter(_range_check, other_ids_iter)]  # pyright: ignore[reportGeneralTypeIssues]

        try:
            result = hikari.Snowflake(value)

        except ValueError:
            return []

        if _range_check(result):
            return [result]

        return []

    return parse


_SNOWFLAKE_REGEX = re.compile(r"<[@&?!#a]{0,3}(?::\w+:)?(\d+)>")
parse_snowflake: _IDMatcherSigProto = _make_snowflake_parser(_SNOWFLAKE_REGEX)
"""Parse a snowflake from a string or int value.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).
message : str
    The error message to raise if the value cannot be parsed.

Returns
-------
hikari.Snowflake
    The parsed snowflake.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_snowflakes: _IDSearcherSig = _make_snowflake_searcher(_SNOWFLAKE_REGEX)
"""Get the snowflakes in a string.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).

Returns
-------
list[hikari.Snowflake]
    List of the snowflakes in the string.
"""

_CHANNEL_ID_REGEX = re.compile(r"<#(\d+)>")
parse_channel_id: _IDMatcherSigProto = _make_snowflake_parser(_CHANNEL_ID_REGEX)
"""Parse a channel ID from a string or int value.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).
message : str
    The error message to raise if the value cannot be parsed.

Returns
-------
hikari.Snowflake
    The parsed channel ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_channel_ids: _IDSearcherSig = _make_snowflake_searcher(_CHANNEL_ID_REGEX)
"""Get the channel IDs in a string.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).

Returns
-------
list[hikari.Snowflake]
    List of the channel IDs in the string.
"""

_EMOJI_ID_REGEX = re.compile(r"<a?:\w+:(\d+)>")
parse_emoji_id: _IDMatcherSigProto = _make_snowflake_parser(_EMOJI_ID_REGEX)
"""Parse an Emoji ID from a string or int value.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).
message : str
    The error message to raise if the value cannot be parsed.

    Defaults to "No valid mention or ID found".

Returns
-------
hikari.Snowflake
    The parsed Emoji ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_emoji_ids: _IDSearcherSig = _make_snowflake_searcher(_EMOJI_ID_REGEX)
"""Get the emoji IDs in a string.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).

Returns
-------
list[hikari.Snowflake]
    List of the emoji IDs in the string.
"""

_ROLE_ID_REGEX = re.compile(r"<@&(\d+)>")
parse_role_id: _IDMatcherSigProto = _make_snowflake_parser(_ROLE_ID_REGEX)
"""Parse a role ID from a string or int value.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).
message : str
    The error message to raise if the value cannot be parsed.

    Defaults to "No valid mention or ID found".

Returns
-------
hikari.Snowflake
    The parsed role ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_role_ids: _IDSearcherSig = _make_snowflake_searcher(_ROLE_ID_REGEX)
"""Get the role IDs in a string.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).

Returns
-------
list[hikari.Snowflake]
    List of the role IDs in the string.
"""

_USER_ID_REGEX = re.compile(r"<@!?(\d+)>")
parse_user_id: _IDMatcherSigProto = _make_snowflake_parser(_USER_ID_REGEX)
"""Parse a user ID from a string or int value.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).
message : str
    The error message to raise if the value cannot be parsed.

    Defaults to "No valid mention or ID found".

Returns
-------
hikari.Snowflake
    The parsed user ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_user_ids: _IDSearcherSig = _make_snowflake_searcher(_USER_ID_REGEX)
"""Get the user IDs in a string.

Parameters
----------
value : str | int | float
    The value to parse (this argument can only be passed positionally).

Returns
-------
list[hikari.Snowflake]
    List of the user IDs in the string.
"""

_MESSAGE_LINK_REGEX = re.compile(r"(\d+|@me)/(\d+)/(\d+)")


def parse_message_id(
    value: _SnowflakeIsh, /, *, message: str = "No valid message link or ID found"
) -> tuple[typing.Optional[hikari.Snowflake], hikari.Snowflake]:
    """Parse a user ID from a string or int value.

    Parameters
    ----------
    value
        The value to parse (this argument can only be passed positionally).
    message
        The error message to raise if the value cannot be parsed.

    Returns
    -------
    tuple[hikari.snowflakes.Snowflake | None, hikari.snowflakes.Snowflake]
        The parsed channel and message IDs.

    Raises
    ------
    ValueError
        If the value cannot be parsed.
    """
    channel_id: typing.Optional[hikari.Snowflake] = None
    message_id: typing.Optional[hikari.Snowflake] = None

    if isinstance(value, int) or value.isdigit():
        message_id = hikari.Snowflake(value)

    else:
        capture = next(_MESSAGE_LINK_REGEX.finditer(value), None)
        if capture:
            channel_id = hikari.Snowflake(capture[2])
            message_id = hikari.Snowflake(capture[3])

    # We should also range check the provided ID.
    if channel_id is not None and not _range_check(channel_id):
        raise ValueError(message) from None

    if message_id is not None and _range_check(message_id):
        return channel_id, message_id

    raise ValueError(message) from None


def _build_url_parser(callback: collections.Callable[[str], _ValueT], /) -> collections.Callable[[str], _ValueT]:
    def parse(value: str, /) -> _ValueT:
        """Convert an argument to a [urllib.parse][] type.

        Parameters
        ----------
        value
            The value to parse (this argument can only be passed positionally).

        Returns
        -------
        _ValueT
            The parsed URL.

        Raises
        ------
        ValueError
            If the argument couldn't be parsed.
        """
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1]

        return callback(value)

    return parse


defragment_url: collections.Callable[[str], urlparse.DefragResult] = _build_url_parser(urlparse.urldefrag)
"""Convert an argument to a defragmented URL.

Parameters
----------
value : str
    The value to parse (this argument can only be passed positionally).

Returns
-------
urllib.parse.DefragResult
    The parsed URL.

Raises
------
ValueError
    If the argument couldn't be parsed.
"""

parse_url: collections.Callable[[str], urlparse.ParseResult] = _build_url_parser(urlparse.urlparse)
"""Convert an argument to a parsed URL.

Parameters
----------
value : str
    The value to parse (this argument can only be passed positionally).

Returns
-------
urllib.parse.ParseResult
    The parsed URL.

Raises
------
ValueError
    If the argument couldn't be parsed.
"""


split_url: collections.Callable[[str], urlparse.SplitResult] = _build_url_parser(urlparse.urlsplit)
"""Convert an argument to a split URL.

Parameters
----------
value : str
    The value to parse (this argument can only be passed positionally).

Returns
-------
urllib.parse.SplitResult
    The split URL.

Raises
------
ValueError
    If the argument couldn't be parsed.
"""

_DATETIME_REGEX = re.compile(r"<-?t:(\d+)(?::\w)?>")


def to_datetime(value: str, /) -> datetime.datetime:
    """Parse a datetime from Discord's datetime format.

    More information on this format can be found at
    <https://discord.com/developers/docs/reference#message-formatting-timestamp-styles>

    Parameters
    ----------
    value
        The value to parse.

    Returns
    -------
    datetime.datetime
        The parsed datetime.

    Raises
    ------
    ValueError
        If the value cannot be parsed.
    """
    try:
        timestamp = int(next(_DATETIME_REGEX.finditer(value)).groups()[0])

    except StopIteration:
        raise ValueError("Not a valid datetime") from None

    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


_VALID_DATETIME_STYLES = frozenset(("t", "T", "d", "D", "f", "F", "R"))


@typing.overload
def from_datetime(value: datetime.timedelta, /) -> str:
    ...


@typing.overload
def from_datetime(value: datetime.datetime, /, *, style: str = "f") -> str:
    ...


def from_datetime(value: typing.Union[datetime.datetime, datetime.timedelta], /, *, style: str = "f") -> str:
    """Format a datetime as Discord's datetime format.

    More information on this format can be found at
    <https://discord.com/developers/docs/reference#message-formatting-timestamp-styles>

    Parameters
    ----------
    value
        The datetime to format.

        If a timedelta is passed here then this is treated as a date that's
        relative to the current time.
    style
        The style to use.

        The valid styles can be found at
        <https://discord.com/developers/docs/reference#message-formatting-formats>.

        This is always "R" when `value` is a [datetime.timedelta][].

    Returns
    -------
    str
        The formatted datetime.

    Raises
    ------
    ValueError
        If the provided datetime is timezone naive.
        If an invalid style is provided.
    """
    if isinstance(value, datetime.timedelta):
        return from_datetime(datetime.datetime.now(tz=datetime.timezone.utc) + value, style="R")

    if style not in _VALID_DATETIME_STYLES:
        raise ValueError(f"Invalid style: {style}")

    if value.tzinfo is None:
        raise ValueError("Cannot convert naive datetimes, please specify a timezone.")

    return f"<t:{round(value.timestamp())}:{style}>"


_YES_VALUES = frozenset(("y", "yes", "t", "true", "on", "1"))
_NO_VALUES = frozenset(("n", "no", "f", "false", "off", "0"))


def to_bool(value: str, /) -> bool:
    """Convert user string input into a boolean value.

    Parameters
    ----------
    value
        The value to convert.

    Returns
    -------
    bool
        The converted value.

    Raises
    ------
    ValueError
        If the value cannot be converted.
    """
    value = value.lower().strip()
    if value in _YES_VALUES:
        return True

    if value in _NO_VALUES:
        return False

    raise ValueError(f"Invalid bool value `{value}`")


def to_color(argument: _SnowflakeIsh, /) -> hikari.Color:
    """Convert user input to a [hikari.Color][hikari.colors.Color] object."""
    if isinstance(argument, str):
        values = argument.split(" ")
        if all(value.isdigit() for value in values):
            if len(values) == 1:
                return hikari.Color.of(int(values[0]))

            return hikari.Color.of(list(map(int, values)))

        if len(values) == 1:
            return hikari.Color.of(values[0])

        raise ValueError("Not a valid color representation")  # noqa: TC004

    return hikari.Color.of(argument)


_TYPE_OVERRIDES: dict[typing.Any, collections.Callable[[str], typing.Any]] = {
    bool: to_bool,
    bytes: lambda d: bytes(d, "utf-8"),
    bytearray: lambda d: bytearray(d, "utf-8"),
    datetime.datetime: to_datetime,
    hikari.Snowflake: parse_snowflake,
    urlparse.DefragResult: defragment_url,
    urlparse.ParseResult: parse_url,
    urlparse.SplitResult: split_url,
}


def override_type(cls: parsing.ConverterSig[typing.Any], /) -> parsing.ConverterSig[typing.Any]:  # noqa: D103
    return _TYPE_OVERRIDES.get(cls, cls)


to_channel: typing.Final[ToChannel] = ToChannel()
"""Convert user input to a [hikari.PartialChannel][hikari.channels.PartialChannel] object."""

to_colour: typing.Final[collections.Callable[[_SnowflakeIsh], hikari.Color]] = to_color
"""Convert user input to a [hikari.Color][hikari.colors.Color] object."""

to_emoji: typing.Final[ToEmoji] = ToEmoji()
"""Convert user input to a cached [hikari.KnownCustomEmoji][hikari.emojis.KnownCustomEmoji] object.

!!! note
    If you just want to convert input to a [hikari.Emoji][hikari.emojis.Emoji],
    [hikari.CustomEmoji][hikari.emojis.CustomEmoji] or
    [hikari.UnicodeEmoji][hikari.emojis.UnicodeEmoji] without making any cache
    or REST calls then you can just use the relevant
    [Emoji.parse][hikari.emojis.Emoji.parse],
    [CustomEmoji.parse][hikari.emojis.CustomEmoji.parse] or
    [UnicodeEmoji.parse][hikari.emojis.UnicodeEmoji.parse] methods.
"""

to_guild: typing.Final[ToGuild] = ToGuild()
"""Convert user input to a [hikari.Guild][hikari.guilds.Guild] object."""

to_invite: typing.Final[ToInvite] = ToInvite()
"""Convert user input to a cached [hikari.InviteWithMetadata][hikari.invites.InviteWithMetadata] object."""

to_invite_with_metadata: typing.Final[ToInviteWithMetadata] = ToInviteWithMetadata()
"""Convert user input to a [hikari.Invite][hikari.invites.Invite] object."""

to_member: typing.Final[ToMember] = ToMember()
"""Convert user input to a [hikari.Member][hikari.guilds.Member] object."""

to_presence: typing.Final[ToPresence] = ToPresence()
"""Convert user input to a cached [hikari.MemberPresence][hikari.presences.MemberPresence]."""

to_role: typing.Final[ToRole] = ToRole()
"""Convert user input to a [hikari.Role][hikari.guilds.Role] object."""

to_snowflake: typing.Final[collections.Callable[[_SnowflakeIsh], hikari.Snowflake]] = parse_snowflake
"""Convert user input to a [hikari.Snowflake][hikari.snowflakes.Snowflake].

!!! note
    This also range validates the input.
"""

to_user: typing.Final[ToUser] = ToUser()
"""Convert user input to a [hikari.User][hikari.users.User] object."""

to_message: typing.Final[ToMessage] = ToMessage()
"""Convert user input to a [hikari.Message][hikari.messages.Message] object."""

to_voice_state: typing.Final[ToVoiceState] = ToVoiceState()
"""Convert user input to a cached [hikari.VoiceState][hikari.voices.VoiceState]."""
