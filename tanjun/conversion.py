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

import abc
import datetime
import logging
import operator
import re
import typing
import urllib.parse as urlparse
from collections import abc as collections

import alluka
import hikari

from . import abc as tanjun
from .dependencies import async_cache

if typing.TYPE_CHECKING:
    from . import parsing


_ArgumentT = typing.Union[str, int, float]
_ValueT = typing.TypeVar("_ValueT")
_LOGGER = logging.getLogger("hikari.tanjun.conversion")


class BaseConverter(abc.ABC):
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
    @abc.abstractmethod
    def async_caches(self) -> collections.Sequence[typing.Any]:
        """Collection of the asynchronous caches that this converter relies on.

        This will only be necessary if the suggested intents or cache_components
        aren't enabled for a converter which requires cache.
        """

    @property
    @abc.abstractmethod
    def cache_components(self) -> hikari.api.CacheComponents:
        """Cache component(s) the converter takes advantage of.

        !!! note
            Unless [tanjun.conversion.BaseConverter.requires_cache][] is [True][],
            these cache components aren't necessary but simply avoid the converter
            from falling back to REST requests.

        This will be [hikari.api.config.CacheComponents.NONE][] if the converter doesn't
        make cache calls.
        """

    @property
    @abc.abstractmethod
    def intents(self) -> hikari.Intents:
        """Gateway intents this converter takes advantage of.

        !!! note
            This field is supplementary to [tanjun.conversion.BaseConverter.cache_components][]
            and is used to detect when the relevant component might not
            actually be being kept up to date or filled by gateway events.

            Unless [tanjun.conversion.BaseConverter.requires_cache][] is [True][],
            these intents being disabled won't stop this converter from working as
            it'll still fall back to REST requests.
        """

    @property
    @abc.abstractmethod
    def requires_cache(self) -> bool:
        """Whether this converter relies on the relevant cache stores to work.

        If this is [True][] then this converter will not function properly
        in an environment [tanjun.conversion.BaseConverter.intents][] or
        [tanjun.conversion.BaseConverter.cache_components][] isn't satisfied
        and will never fallback to REST requests.
        """

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
        if not client.cache and any(
            client.get_type_dependency(cls) is alluka.abc.UNDEFINED for cls in self.async_caches
        ):
            if self.requires_cache:
                _LOGGER.warning(
                    f"Converter {self!r} registered with {parent_name} will always fail with a stateless client.",
                )

            elif self.cache_components:
                _LOGGER.warning(
                    f"Converter {self!r} registered with {parent_name} may not perform optimally in a stateless client.",
                )

        # elif missing_components := (self.cache_components & ~client.cache.components):
        #     _LOGGER.warning(

        if client.shards and (missing_intents := self.intents & ~client.shards.intents):
            _LOGGER.warning(
                f"Converter {self!r} registered with {parent_name} may not perform as expected "
                f"without the following intents: {missing_intents}",
            )


_DmCacheT = async_cache.SfCache[hikari.DMChannel]
_GuildChannelCacheT = async_cache.SfCache[hikari.PermissibleGuildChannel]
_ThreadCacheT = async_cache.SfCache[hikari.GuildThreadChannel]


# TODO: GuildChannelConverter
class ToChannel(BaseConverter):
    """Standard converter for channels mentions/IDs.

    For a standard instance of this see [tanjun.conversion.to_channel][].
    """

    __slots__ = ("_include_dms",)

    def __init__(self, *, include_dms: bool = True) -> None:
        """Initialise a to channel converter.

        Parameters
        ----------
        include_dms
            Whether to include DM channels in the results.

            May lead to a lot of extra fallbacks to REST requests if
            the client doesn't have a registered async cache for DMs.
        """
        self._include_dms = include_dms

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_GuildChannelCacheT, _DmCacheT, _ThreadCacheT)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.GUILD_CHANNELS

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_GuildChannelCacheT]] = None,
        dm_cache: alluka.Injected[typing.Optional[_DmCacheT]] = None,
        thread_cache: alluka.Injected[typing.Optional[_ThreadCacheT]] = None,
    ) -> hikari.PartialChannel:
        channel_id = parse_channel_id(argument, message="No valid channel mention or ID found")
        if ctx.cache and (channel_ := ctx.cache.get_guild_channel(channel_id)):
            return channel_

        no_guild_channel = cache and thread_cache and dm_cache
        if cache:
            try:
                return await cache.get(channel_id)

            except async_cache.EntryNotFound:
                pass

            except async_cache.CacheMissError:
                no_guild_channel = False

        if thread_cache:
            try:
                return await thread_cache.get(channel_id)

            except async_cache.EntryNotFound:
                pass

            except async_cache.CacheMissError:
                no_guild_channel = False

        if dm_cache and self._include_dms:
            try:
                return await dm_cache.get(channel_id)

            except async_cache.EntryNotFound:
                pass

            except async_cache.CacheMissError:
                no_guild_channel = False

        if not no_guild_channel:
            try:
                channel = await ctx.rest.fetch_channel(channel_id)
                if self._include_dms or isinstance(channel, hikari.GuildChannel):
                    return channel

            except hikari.NotFoundError:
                pass

        raise ValueError("Couldn't find channel")


ChannelConverter = ToChannel
"""Deprecated alias of [tanjun.conversion.ToChannel][]."""

_EmojiCacheT = async_cache.SfCache[hikari.KnownCustomEmoji]


class ToEmoji(BaseConverter):
    """Standard converter for custom emojis.

    For a standard instance of this see [tanjun.conversion.to_emoji][].

    !!! note
        If you just want to convert inpute to a [hikari.emojis.Emoji][],
        [hikari.emojis.CustomEmoji][] or [hikari.emojis.UnicodeEmoji][] without
        making any cache or REST calls then you can just use the relevant
        [Emoji.parse][hikari.emojis.Emoji.parse],
        [CustomEmoji.parse][hikari.emojis.CustomEmoji.parse] or
        [UnicodeEmoji.parse][hikari.emojis.UnicodeEmoji.parse] methods.
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_EmojiCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.EMOJIS

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_EMOJIS | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
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


EmojiConverter = ToEmoji
"""Deprecated alias of [tanjun.conversion.ToEmoji][]."""


_GuildCacheT = async_cache.SfCache[hikari.Guild]


class ToGuild(BaseConverter):
    """Stanard converter for guilds.

    For a standard instance of this see [tanjun.conversion.to_guild][].
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_GuildCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.GUILDS

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
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


GuildConverter = ToGuild
"""Deprecated alias of [tanjun.conversion.ToGuild][]."""

_InviteCacheT = async_cache.AsyncCache[str, hikari.InviteWithMetadata]


class ToInvite(BaseConverter):
    """Standard converter for invites."""

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_InviteCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.INVITES

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_INVITES

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_InviteCacheT]] = None,
    ) -> hikari.Invite:
        if not isinstance(argument, str):
            raise ValueError(f"`{argument}` is not a valid invite code")

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


InviteConverter = ToInvite
"""Deprecated alias of [tanjun.conversion.ToInvite][]."""


class ToInviteWithMetadata(BaseConverter):
    """Standard converter for invites with metadata.

    For a standard instance of this see [tanjun.conversion.to_invite_with_metadata][].

    !!! note
        Unlike [tanjun.conversion.InviteConverter][], this converter is cache dependent.
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_InviteCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.INVITES

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_INVITES

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return True

    async def __call__(
        self,
        argument: _ArgumentT,
        /,
        ctx: alluka.Injected[tanjun.Context],
        *,
        cache: alluka.Injected[typing.Optional[_InviteCacheT]] = None,
    ) -> hikari.InviteWithMetadata:
        if not isinstance(argument, str):
            raise ValueError(f"`{argument}` is not a valid invite code")

        if ctx.cache and (invite := ctx.cache.get_invite(argument)):
            return invite

        if cache and (invite := await cache.get(argument)):
            return invite

        raise ValueError("Couldn't find invite")


InviteWithMetadataConverter = ToInviteWithMetadata
"""Deprecated alias of [tanjun.conversion.ToInviteWithMetadata][]."""


_MemberCacheT = async_cache.SfGuildBound[hikari.Member]


class ToMember(BaseConverter):
    """Standard converter for guild members.

    For a standard instance of this see [tanjun.conversion.to_member][].

    This converter allows both mentions, raw IDs and partial usernames/nicknames
    and only works within a guild context.
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_MemberCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.MEMBERS

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_MEMBERS | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
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


MemberConverter = ToMember
"""Deprecated alias of [tanjun.conversion.ToMember][]."""

_PresenceCacheT = async_cache.SfGuildBound[hikari.MemberPresence]


class ToPresence(BaseConverter):
    """Standard converter for presences.

    For a standard instance of this see [tanjun.conversion.to_presence][].

    This converter is cache dependent and only works in a guild context.
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_PresenceCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.PRESENCES

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_PRESENCES | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return True

    async def __call__(
        self,
        argument: _ArgumentT,
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


PresenceConverter = ToPresence
"""Deprecated alias of [tanjun.conversion.ToPresence][]."""

_RoleCacheT = async_cache.SfCache[hikari.Role]


class ToRole(BaseConverter):
    """Standard converter for guild roles.

    For a standard instance of this see [tanjun.conversion.to_role][].
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_RoleCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.ROLES

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
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


RoleConverter = ToRole
"""Deprecated alias of [tanjun.conversion.ToRole][]."""

_UserCacheT = async_cache.SfCache[hikari.User]


class ToUser(BaseConverter):
    """Standard converter for users.

    For a standard instance of this see [tanjun.conversion.to_user][].
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_UserCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.NONE

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILDS | hikari.Intents.GUILD_MEMBERS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
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


UserConverter = ToUser
"""Deprecated alias of [tanjun.conversion.ToUser][]."""


_MessageCacheT = async_cache.SfCache[hikari.Message]


class ToMessage(BaseConverter):
    """Standard converter for messages.

    For a standard instance of this see [tanjun.conversion.to_message][].
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_MessageCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.MESSAGES

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_MESSAGES | hikari.Intents.DM_MESSAGES

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return False

    async def __call__(
        self,
        argument: _ArgumentT,
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

    For a standard instance of this see [tanjun.conversion.to_voice_state][].

    !!! note
        This converter is cache dependent and only works in a guild context.
    """

    __slots__ = ()

    @property
    def async_caches(self) -> collections.Sequence[typing.Any]:
        # <<inherited docstring from BaseConverter>>.
        return (_VoiceStateCacheT,)

    @property
    def cache_components(self) -> hikari.api.CacheComponents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.api.CacheComponents.VOICE_STATES

    @property
    def intents(self) -> hikari.Intents:
        # <<inherited docstring from BaseConverter>>.
        return hikari.Intents.GUILD_VOICE_STATES | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        # <<inherited docstring from BaseConverter>>.
        return True

    async def __call__(
        self,
        argument: _ArgumentT,
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


VoiceStateConverter = ToVoiceState
"""Deprecated alias of [tanjun.conversion.ToVoiceState][]."""


class _IDMatcherSigProto(typing.Protocol):
    def __call__(self, value: _ArgumentT, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        raise NotImplementedError


def _make_snowflake_parser(regex: re.Pattern[str], /) -> _IDMatcherSigProto:
    def parse(value: _ArgumentT, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
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
        hikari.Snowflake
            The parsed snowflake.

        Raises
        ------
        ValueError
            If the value cannot be parsed.
        """
        result: typing.Optional[hikari.Snowflake] = None
        if isinstance(value, str):
            if value.isdigit():
                result = hikari.Snowflake(value)

            else:
                capture = next(regex.finditer(value), None)
                result = hikari.Snowflake(capture.groups()[0]) if capture else None

        else:
            try:
                # Technically passing a float here is invalid (typing wise)
                # but we handle that by catching TypeError
                result = hikari.Snowflake(operator.index(typing.cast(int, value)))

            except (TypeError, ValueError):
                pass

        # We should also range check the provided ID.
        if result is not None and _range_check(result):
            return result

        raise ValueError(message) from None

    return parse


_IDSearcherSig = collections.Callable[[_ArgumentT], list[hikari.Snowflake]]


def _range_check(snowflake: hikari.Snowflake, /) -> bool:
    return snowflake.min() <= snowflake <= snowflake.max()


def _make_snowflake_searcher(regex: re.Pattern[str], /) -> _IDSearcherSig:
    def parse(value: _ArgumentT, /) -> list[hikari.Snowflake]:
        """Get the snowflakes in a string.

        !!! note
            This only allows the relevant entity's mention format if applicable.

        Parameters
        ----------
        value
            The value to parse (this argument can only be passed positionally).

        Returns
        -------
        list[hikari.Snowflake]
            List of the IDs found in the string.
        """
        if isinstance(value, str):
            if value.isdigit() and _range_check(result := hikari.Snowflake(value)):
                return [result]

            results = filter(
                _range_check, map(hikari.Snowflake, (match.groups()[0] for match in regex.finditer(value)))
            )
            return [*results, *filter(_range_check, map(hikari.Snowflake, filter(str.isdigit, value.split())))]

        try:
            # Technically passing a float here is invalid (typing wise)
            # but we handle that by catching TypeError
            result = hikari.Snowflake(operator.index(typing.cast(int, value)))

        except (TypeError, ValueError):
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
    value: _ArgumentT,
    /,
    *,
    message: str = "No valid message link or ID found",
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
    tuple[hikari.Snowflake | None, hikari.Snowflake]
        The parsed channel and message IDs.

    Raises
    ------
    ValueError
        If the value cannot be parsed.
    """
    channel_id: typing.Optional[hikari.Snowflake] = None
    message_id: typing.Optional[hikari.Snowflake] = None

    if isinstance(value, str):
        if value.isdigit():
            message_id = hikari.Snowflake(value)

        else:
            capture = next(_MESSAGE_LINK_REGEX.finditer(value), None)
            if capture:
                channel_id = hikari.Snowflake(capture[2])
                message_id = hikari.Snowflake(capture[3])

    else:
        try:
            # Technically passing a float here is invalid (typing wise)
            # but we handle that by catching TypeError
            message_id = hikari.Snowflake(operator.index(typing.cast(int, value)))

        except (TypeError, ValueError):
            pass

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


def from_datetime(value: datetime.datetime, /, *, style: str = "f") -> str:
    """Format a datetime as Discord's datetime format.

    More information on this format can be found at
    <https://discord.com/developers/docs/reference#message-formatting-timestamp-styles>

    Parameters
    ----------
    value
        The datetime to format.
    style
        The style to use.

        The valid styles can be found at
        <https://discord.com/developers/docs/reference#message-formatting-formats>.

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


def to_color(argument: _ArgumentT, /) -> hikari.Color:
    """Convert user input to a [hikari.colors.Color][] object."""
    if isinstance(argument, str):
        values = argument.split(" ")
        if all(value.isdigit() for value in values):
            if len(values) == 1:
                return hikari.Color.of(int(values[0]))

            return hikari.Color.of(list(map(int, values)))

        if len(values) == 1:
            return hikari.Color.of(values[0])

        raise ValueError("Not a valid color representation")

    return hikari.Color.of(argument)


_TYPE_OVERRIDES: dict[collections.Callable[..., typing.Any], collections.Callable[[str], typing.Any]] = {
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
"""Convert user input to a [hikari.channels.PartialChannel][] object."""

to_colour: typing.Final[collections.Callable[[_ArgumentT], hikari.Color]] = to_color
"""Convert user input to a [hikari.colors.Color][] object."""

to_emoji: typing.Final[ToEmoji] = ToEmoji()
"""Convert user input to a cached [hikari.emojis.KnownCustomEmoji][] object.

!!! note
    If you just want to convert inpute to a [hikari.emojis.Emoji][],
    [hikari.emojis.CustomEmoji][] or [hikari.emojis.UnicodeEmoji][] without
    making any cache or REST calls then you can just use the relevant
    [hikari.emojis.Emoji.parse][], [hikari.emojis.CustomEmoji.parse][] or
    [hikari.emojis.UnicodeEmoji.parse][] methods.
"""

to_guild: typing.Final[ToGuild] = ToGuild()
"""Convert user input to a [hikari.guilds.Guild][] object."""

to_invite: typing.Final[ToInvite] = ToInvite()
"""Convert user input to a cached [hikari.invites.InviteWithMetadata][] object."""

to_invite_with_metadata: typing.Final[ToInviteWithMetadata] = ToInviteWithMetadata()
"""Convert user input to a [hikari.invites.Invite][] object."""

to_member: typing.Final[ToMember] = ToMember()
"""Convert user input to a [hikari.guilds.Member][] object."""

to_presence: typing.Final[ToPresence] = ToPresence()
"""Convert user input to a cached [hikari.presences.MemberPresence][]."""

to_role: typing.Final[ToRole] = ToRole()
"""Convert user input to a [hikari.guilds.Role][] object."""

to_snowflake: typing.Final[collections.Callable[[_ArgumentT], hikari.Snowflake]] = parse_snowflake
"""Convert user input to a [hikari.snowflakes.Snowflake][].

!!! note
    This also range validates the input.
"""

to_user: typing.Final[ToUser] = ToUser()
"""Convert user input to a [hikari.users.User][] object."""

to_message: typing.Final[ToMessage] = ToMessage()
"""Convert user input to a [hikari.messages.Message][] object."""

to_voice_state: typing.Final[ToVoiceState] = ToVoiceState()
"""Convert user input to a cached [hikari.voices.VoiceState][]."""
