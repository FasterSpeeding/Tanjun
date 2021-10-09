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
"""Functions and classes used to enable more Discord oriented argument converters."""
from __future__ import annotations

__all__: list[str] = [
    "ArgumentT",
    "from_datetime",
    "parse_snowflake",
    "parse_channel_id",
    "parse_emoji_id",
    "parse_role_id",
    "parse_user_id",
    "search_snowflakes",
    "search_channel_ids",
    "search_emoji_ids",
    "search_role_ids",
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
    "to_presence",
    "to_role",
    "to_snowflake",
    "to_user",
    "to_voice_state",
]

import abc
import datetime
import operator
import re
import typing
import urllib.parse
import warnings
from collections import abc as collections

import hikari

from . import abc as tanjun_abc
from . import errors
from . import injecting

if typing.TYPE_CHECKING:
    from . import parsing

ArgumentT = typing.Union[str, int, float]
_ValueT = typing.TypeVar("_ValueT")


class BaseConverter(typing.Generic[_ValueT], abc.ABC):
    """Base class for the standard converters.

    This is detail of the standard implementation and isn't guaranteed to work
    between implementations but will work for implementations which provide
    the standard dependency injection or special cased support for these.

    While it isn't necessary to subclass this to implement your own converters
    since dependency injection can be used to access fields like the current Context,
    this class introduces some niceties around stuff like state warnings.
    """

    __slots__ = ()

    async def __call__(
        self, argument: ArgumentT, ctx: tanjun_abc.Context = injecting.injected(type=tanjun_abc.Context)
    ) -> _ValueT:
        return await self.convert(ctx, argument)

    @property
    @abc.abstractmethod
    def cache_components(self) -> hikari.CacheComponents:
        """Cache component(s) the converter takes advantage of.

        .. note::
            Unless `BaseConverter.requires_cache` is `True`, these cache components
            aren't necessary but simply avoid the converter from falling back to
            REST requests.

        Returns
        -------
        hikari.CacheComponents
            The cache components the converter takes advantage of.

            This will be `hikari.CacheComponents.NONE` if the converter doesn't
            make cache calls.
        """

    @property
    @abc.abstractmethod
    def intents(self) -> hikari.Intents:
        """Gateway intents this converter takes advantage of.

        .. note::
            This field is supplementary to `BaseConverter.cache_components` and
            is used to detect when the relevant component might not actually be
            being kept up to date or filled by gateway events.

            Unless `BaseConverter.requires_cache` is `True`, these intents being
            disabled won't stop this converter from working as it'll still fall
            back to REST requests.

        Returns
        -------
        hikari.Intents
            Bitwise flag of the intents this converter takes advantage of.
        """

    @property
    @abc.abstractmethod
    def requires_cache(self) -> bool:
        """Whether this converter relies on the relevant cache stores to work.

        Returns
        -------
        bool
            Whether the converter relies on the relevant cache stores to work.

            If this is `True` then this converter will not function properly
            in an environment `BaseConverter.intents` or `BaseConverter.cache_components`
            isn't satisfied and will never fallback to REST requests.
        """

    @abc.abstractmethod
    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> _ValueT:
        """Convert an argument.

        Parameters
        ----------
        ArgumentT
            The argument to convert.

        Returns
        -------
        _ValueT
            The resultant value.

        Raises
        ------
        ValueError
            If the argument couldn't be converted.
        """

    def check_client(self, client: tanjun_abc.Client, parent_name: str, /) -> None:
        """Check that this converter will work with the given client.

        This never raises any errors but simply warns the user if the converter
        is not compatible with the given client.

        Parameters
        ----------
        client : tanjun.abc.Client
            The client to check against.
        parent_name : str
            The name of the converter's parent, used for warning messages.
        """
        if not client.cache:
            if self.requires_cache:
                warnings.warn(
                    f"Converter {self!r} registered with {parent_name} will always fail with a stateless client.",
                    category=errors.StateWarning,
                )

            elif self.cache_components:
                warnings.warn(
                    f"Converter {self!r} registered with {parent_name} may not perform optimally in a stateless client.",
                )

        # elif missing_components := (self.cache_components & ~client.cache.components):
        #     warnings.warn(

        if client.shards and (missing_intents := self.intents & ~client.shards.intents):
            warnings.warn(
                f"Converter {self!r} registered with {parent_name} may not perform as expected "
                f"without the following intents: {missing_intents}",
                category=errors.StateWarning,
            )


class InjectableConverter(injecting.BaseInjectableCallback[_ValueT]):
    """A specialised injectable callback which accounts for special casing `BaseConverter`.

    Parameters
    ----------
    converter : typing.Union[tanjun.injecting.CallbackSig[_ValueT], BaseConverter[_ValueT]]
        The converter callback to use.
    """

    __slots__ = ("_is_base_converter",)

    def __init__(self, callback: typing.Union[injecting.CallbackSig[_ValueT], BaseConverter[_ValueT]], /) -> None:
        super().__init__(callback)
        self._is_base_converter = isinstance(callback, BaseConverter)

    async def __call__(self, ctx: tanjun_abc.Context, value: ArgumentT, /) -> _ValueT:
        if self._is_base_converter:
            assert isinstance(self.descriptor.callback, BaseConverter)
            return typing.cast(_ValueT, await self.descriptor.callback(value, ctx))

        return await self.descriptor.resolve_with_command_context(ctx, value)


class ChannelConverter(BaseConverter[hikari.PartialChannel]):
    """Standard converter for channels mentions/IDs."""

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.GUILD_CHANNELS

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.PartialChannel:
        channel_id = parse_channel_id(argument, message="No valid channel mention or ID  found")
        if ctx.cache and (channel := ctx.cache.get_guild_channel(channel_id)):
            return channel

        try:
            return await ctx.rest.fetch_channel(channel_id)

        except hikari.NotFoundError:
            raise ValueError("Couldn't find channel") from None


class EmojiConverter(BaseConverter[hikari.KnownCustomEmoji]):
    """Standard converter for custom emojis."""

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.EMOJIS

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_EMOJIS | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.KnownCustomEmoji:
        emoji_id = parse_emoji_id(argument, message="No valid emoji or emoji ID found")

        if ctx.cache and (emoji := ctx.cache.get_emoji(emoji_id)):
            return emoji

        if ctx.guild_id:
            try:
                return await ctx.rest.fetch_emoji(ctx.guild_id, emoji_id)

            except hikari.NotFoundError:
                pass

        raise ValueError("Couldn't find emoji")


class GuildConverter(BaseConverter[hikari.Guild]):
    """Stanard converter for guilds."""

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.GUILDS

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.Guild:
        guild_id = parse_snowflake(argument, message="No valid guild ID found")
        if ctx.cache:
            if guild := ctx.cache.get_guild(guild_id):
                return guild

        try:
            return await ctx.rest.fetch_guild(guild_id)

        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find guild")


class InviteConverter(BaseConverter[hikari.Invite]):
    """Standard converter for invites."""

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.INVITES

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_INVITES

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.Invite:
        if not isinstance(argument, str):
            raise ValueError(f"`{argument}` is not a valid invite code")

        if ctx.cache:
            if invite := ctx.cache.get_invite(argument):
                return invite

        try:
            return await ctx.rest.fetch_invite(argument)
        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find invite")


class InviteWithMetadataConverter(BaseConverter[hikari.InviteWithMetadata]):
    """Standard converter for invites with metadata.

    .. note::
        Unlike `InviteConverter`, this converter is cache dependent.
    """

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.INVITES

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_INVITES

    @property
    def requires_cache(self) -> bool:
        return True

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.InviteWithMetadata:
        if not isinstance(argument, str):
            raise ValueError(f"`{argument}` is not a valid invite code")

        if ctx.cache:
            if invite := ctx.cache.get_invite(argument):
                return invite

        raise ValueError("Couldn't find invite")


class MemberConverter(BaseConverter[hikari.Member]):
    """Standard converter for guild members.

    This converter allows both mentions, raw IDs and partial usernames/nicknames
    and only works within a guild context.
    """

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.MEMBERS

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_MEMBERS | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.Member:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a member from a DM channel")

        try:
            member_id = parse_user_id(argument, message="No valid user mention or ID found")

        except ValueError:
            if isinstance(argument, str):
                try:
                    return (await ctx.rest.search_members(ctx.guild_id, argument))[0]

                except (hikari.NotFoundError, IndexError):
                    pass

        else:
            if ctx.cache:
                if member := ctx.cache.get_member(ctx.guild_id, member_id):
                    return member

            try:
                return await ctx.rest.fetch_member(ctx.guild_id, member_id)

            except hikari.NotFoundError:
                pass

        raise ValueError("Couldn't find member in this guild")


class PresenceConverter(BaseConverter[hikari.MemberPresence]):
    """Standard converter for presences.

    This converter is cache dependent and only works in a guild context.
    """

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.PRESENCES

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_PRESENCES | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return True

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.MemberPresence:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a presence from a DM channel")

        if ctx.cache:
            user_id = parse_user_id(argument, message="No valid member mention or ID  found")
            if user := ctx.cache.get_presence(ctx.guild_id, user_id):
                return user

        raise ValueError("Couldn't find presence in current guild")


class RoleConverter(BaseConverter[hikari.Role]):
    """Standard converter for guild roles."""

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.ROLES

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.Role:
        role_id = parse_role_id(argument, message="No valid role mention or ID  found")
        if ctx.cache:
            if role := ctx.cache.get_role(role_id):
                return role

        if ctx.guild_id:
            for role in await ctx.rest.fetch_roles(ctx.guild_id):
                if role.id == role_id:
                    return role

        raise ValueError("Couldn't find role")


class UserConverter(BaseConverter[hikari.User]):
    """Standard converter for users."""

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.NONE

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILDS | hikari.Intents.GUILD_MEMBERS

    @property
    def requires_cache(self) -> bool:
        return False

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.User:
        # TODO: search by name if this is a guild context
        user_id = parse_user_id(argument, message="No valid user mention or ID  found")
        if ctx.cache:
            if user := ctx.cache.get_user(user_id):
                return user

        try:
            return await ctx.rest.fetch_user(user_id)

        except hikari.NotFoundError:
            pass

        raise ValueError("Couldn't find user")


class VoiceStateConverter(BaseConverter[hikari.VoiceState]):
    """Standard converter for voice states.

    .. note::
        This converter is cache dependent and only works in a guild context.
    """

    __slots__ = ()

    @property
    def cache_components(self) -> hikari.CacheComponents:
        return hikari.CacheComponents.VOICE_STATES

    @property
    def intents(self) -> hikari.Intents:
        return hikari.Intents.GUILD_VOICE_STATES | hikari.Intents.GUILDS

    @property
    def requires_cache(self) -> bool:
        return True

    async def convert(self, ctx: tanjun_abc.Context, argument: ArgumentT, /) -> hikari.VoiceState:
        if ctx.guild_id is None:
            raise ValueError("Cannot get a voice state from a DM channel")

        if ctx.cache:
            user_id = parse_user_id(argument, message="No valid user mention or ID  found")
            if user := ctx.cache.get_voice_state(ctx.guild_id, user_id):
                return user

        raise ValueError("Voice state couldn't be found for current guild")


class _IDMatcher(typing.Protocol):
    def __call__(self, value: ArgumentT, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        raise NotImplementedError


def _make_snowflake_parser(regex: re.Pattern[str], /) -> _IDMatcher:
    def parse(value: ArgumentT, /, *, message: str = "No valid mention or ID found") -> hikari.Snowflake:
        """Parse a snowflake from a string or int value.

        .. note::
            This only allows the relevant entity's mention format if applicable.

        Parameters
        ----------
        value: typing.Union[str, int]
            The value to parse (this argument can only be passed positionally).

        Other Parameters
        ----------------
        message: str
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
                result = hikari.Snowflake(operator.index(value))

            except (TypeError, ValueError):
                pass

        # We should also range check the provided ID.
        if result is not None and _range_check(result):
            return result

        raise ValueError(message) from None

    return parse


_IDSearcher = collections.Callable[[ArgumentT], collections.Iterator[hikari.Snowflake]]


def _range_check(snowflake: hikari.Snowflake, /) -> bool:
    return snowflake.min() <= snowflake <= snowflake.max()


def _make_snowflake_searcher(regex: re.Pattern[str], /) -> _IDSearcher:
    def parse(value: ArgumentT, /) -> collections.Iterator[hikari.Snowflake]:
        """Iterate over the snowflakes in a string.

        .. note::
            This only allows the relevant entity's mention format if applicable.

        Parameters
        ----------
        value: typing.Union[str, int]
            The value to parse (this argument can only be passed positionally).

        Returns
        -------
        collections.abc.Iterator[hikari.Snowflake]
            An iterator over the IDs found in the string.
        """
        if isinstance(value, str):
            if value.isdigit() and _range_check(result := hikari.Snowflake(value)):
                yield result

            else:
                yield from filter(
                    _range_check, map(hikari.Snowflake, (match.groups()[0] for match in regex.finditer(value)))
                )

                yield from filter(_range_check, map(hikari.Snowflake, filter(str.isdigit, value.split())))

        else:
            try:
                result = hikari.Snowflake(operator.index(value))

            except (TypeError, ValueError):
                pass

            else:
                if _range_check(result):
                    yield result

    return parse


_SNOWFLAKE_REGEX = re.compile(r"<[@&?!#a]{0,3}(?::\w+:)?(\d+)>")
parse_snowflake: _IDMatcher = _make_snowflake_parser(_SNOWFLAKE_REGEX)
"""Parse a snowflake from a string or int value.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Other Parameters
----------------
message: str
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

search_snowflakes = _make_snowflake_searcher(_SNOWFLAKE_REGEX)
"""Iterate over the snowflakes in a string.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Returns
-------
collections.abc.Iterator[hikari.Snowflake]
    An iterator over the snowflakes in the string.
"""

_CHANNEL_ID_REGEX = re.compile(r"<#(\d+)>")
parse_channel_id: _IDMatcher = _make_snowflake_parser(_CHANNEL_ID_REGEX)
"""Parse a channel ID from a string or int value.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Other Parameters
----------------
message: str
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

search_channel_ids = _make_snowflake_searcher(_CHANNEL_ID_REGEX)
"""Iterate over the channel IDs in a string.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Returns
-------
collections.abc.Iterator[hikari.Snowflake]
    An iterator over the channel IDs in the string.
"""

_EMOJI_ID_REGEX = re.compile(r"<a?:\w+:(\d+)>")
parse_emoji_id: _IDMatcher = _make_snowflake_parser(_EMOJI_ID_REGEX)
"""Parse an Emoji ID from a string or int value.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Other Parameters
----------------
message: str
    The error message to raise if the value cannot be parsed.

Returns
-------
hikari.Snowflake
    The parsed Emoji ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_emoji_ids = _make_snowflake_searcher(_EMOJI_ID_REGEX)
"""Iterate over the emoji IDs in a string.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Returns
-------
collections.abc.Iterator[hikari.Snowflake]
    An iterator over the emoji IDs in the string.
"""

_ROLE_ID_REGEX = re.compile(r"<@&(\d+)>")
parse_role_id: _IDMatcher = _make_snowflake_parser(_ROLE_ID_REGEX)
"""Parse a role ID from a string or int value.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Other Parameters
----------------
message: str
    The error message to raise if the value cannot be parsed.

Returns
-------
hikari.Snowflake
    The parsed role ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_role_ids = _make_snowflake_searcher(_ROLE_ID_REGEX)
"""Iterate over the role IDs in a string.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Returns
-------
collections.abc.Iterator[hikari.Snowflake]
    An iterator over the role IDs in the string.
"""

_USER_ID_REGEX = re.compile(r"<@!?(\d+)>")
parse_user_id: _IDMatcher = _make_snowflake_parser(_USER_ID_REGEX)
"""Parse a user ID from a string or int value.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Other Parameters
----------------
message: str
    The error message to raise if the value cannot be parsed.

Returns
-------
hikari.Snowflake
    The parsed user ID.

Raises
------
ValueError
    If the value cannot be parsed.
"""

search_user_ids = _make_snowflake_searcher(_USER_ID_REGEX)
"""Iterate over the user IDs in a string.

Parameters
----------
value: typing.Union[str, int]
    The value to parse (this argument can only be passed positionally).

Returns
-------
collections.abc.Iterator[hikari.Snowflake]
    An iterator over the user IDs in the string.
"""


def _build_url_parser(callback: collections.Callable[[str], _ValueT], /) -> collections.Callable[[str], _ValueT]:
    def parse(value: str, /) -> _ValueT:
        """Convert an argument to a `urlib.parse` type.

        Parameters
        ----------
        value: str
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


defragment_url = _build_url_parser(urllib.parse.urldefrag)
"""Convert an argument to a defragmented URL.

Parameters
----------
value: str
    The value to parse (this argument can only be passed positionally).

Returns
-------
urlib.parse.DefragResult
    The parsed URL.

Raises
------
ValueError
    If the argument couldn't be parsed.
"""

parse_url = _build_url_parser(urllib.parse.urlparse)
"""Convert an argument to a parsed URL.

Parameters
----------
value: str
    The value to parse (this argument can only be passed positionally).

Returns
-------
urlib.parse.ParseResult
    The parsed URL.

Raises
------
ValueError
    If the argument couldn't be parsed.
"""


split_url = _build_url_parser(urllib.parse.urlsplit)
"""Convert an argument to a split URL.

Parameters
----------
value: str
    The value to parse (this argument can only be passed positionally).

Returns
-------
urlib.parse.SplitResult
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
    https://discord.com/developers/docs/reference#message-formatting-timestamp-styles

    Parameters
    ----------
    value: str
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
    https://discord.com/developers/docs/reference#message-formatting-timestamp-styles

    Parameters
    ----------
    value: datetime.datetime
        The datetime to format.

    Other Parameters
    ----------------
    style: str
        The style to use.

        The valid styles can be found at
        https://discord.com/developers/docs/reference#message-formatting-formats
        and this defaults to `"f"`.

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
    value: str
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


def to_color(argument: ArgumentT, /) -> hikari.Color:
    """Convert user input to a `hikari.colors.Color` object."""
    if isinstance(argument, str):
        values = argument.split(" ")
        if all(value.isdigit() for value in values):
            return hikari.Color.of(*map(int, values))

        return hikari.Color.of(*values)

    return hikari.Color.of(argument)


_TYPE_OVERRIDES: dict[collections.Callable[..., typing.Any], collections.Callable[[str], typing.Any]] = {
    bool: to_bool,
    bytes: lambda d: bytes(d, "utf-8"),
    bytearray: lambda d: bytearray(d, "utf-8"),
    datetime.datetime: to_datetime,
    hikari.Snowflake: parse_snowflake,
    urllib.parse.DefragResult: defragment_url,
    urllib.parse.ParseResult: parse_url,
    urllib.parse.SplitResult: split_url,
}


def override_type(cls: parsing.ConverterSig, /) -> parsing.ConverterSig:
    return _TYPE_OVERRIDES.get(cls, cls)


to_channel: typing.Final[ChannelConverter] = ChannelConverter()
"""Convert user input to a `hikari.channels.PartialChannel` object."""

to_colour: typing.Final[collections.Callable[[ArgumentT], hikari.Color]] = to_color
"""Convert user input to a `hikari.colors.Color` object."""

to_emoji: typing.Final[EmojiConverter] = EmojiConverter()
"""Convert user input to a cached `hikari.emojis.KnownCustomEmoji` object."""

to_guild: typing.Final[GuildConverter] = GuildConverter()
"""Convert user input to a `hikari.guilds.Guild` object."""

to_invite: typing.Final[InviteConverter] = InviteConverter()
"""Convert user input to a cached `hikari.invites.InviteWithMetadata` object."""

to_invite_with_metadata: typing.Final[InviteWithMetadataConverter] = InviteWithMetadataConverter()
"""Convert user input to a `hikari.invites.Invite` object."""

to_member: typing.Final[MemberConverter] = MemberConverter()
"""Convert user input to a `hikari.guilds.Member` object."""

to_presence: typing.Final[PresenceConverter] = PresenceConverter()
"""Convert user input to a cached `hikari.presences.MemberPresence`."""

to_role: typing.Final[RoleConverter] = RoleConverter()
"""Convert user input to a `hikari.guilds.Role` object."""

to_snowflake: typing.Final[collections.Callable[[ArgumentT], hikari.Snowflake]] = parse_snowflake
"""Convert user input to a `hikari.snowflakes.Snowflake`.

.. note::
    This also range validates the input.
"""

to_user: typing.Final[UserConverter] = UserConverter()
"""Convert user input to a `hikari.users.User` object."""

to_voice_state: typing.Final[VoiceStateConverter] = VoiceStateConverter()
"""Convert user input to a cached `hikari.voices.VoiceState`."""
