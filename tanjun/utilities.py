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
"""Collection of utility functions used within Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "async_chain",
    "await_if_async",
    "gather_checks",
    "ALL_PERMISSIONS",
    "CastedView",
    "DM_PERMISSIONS",
    "calculate_everyone_permissions",
    "calculate_permissions",
    "fetch_everyone_permissions",
    "fetch_permissions",
    "match_prefix_names",
]

import asyncio
import typing
from collections import abc as collections

import hikari

from . import errors

if typing.TYPE_CHECKING:
    from . import abc
    from . import checks


_KeyT = typing.TypeVar("_KeyT")
_ValueT = typing.TypeVar("_ValueT")


async def async_chain(
    iterable: collections.Iterable[collections.AsyncIterable[_ValueT]],
) -> collections.AsyncIterator[_ValueT]:
    """Make an asynchronous iterator of the elements within multiple asynchronous iterators."""
    for async_iterable in iterable:
        async for value in async_iterable:
            yield value


async def await_if_async(
    callback: collections.Callable[..., abc.MaybeAwaitableT[_ValueT]], /, *args: typing.Any
) -> _ValueT:
    """Resole any awaitable returned by a callback call.

    Parameters
    ----------
    callback : collections.abc.Callable[..., tanjun.abc.MaybeAwaitableT[_ValueT]]
        The async or non-async callback to call.

    Other Parameters
    ----------------
    *args : typing.Any
        A variable amount of positional arguments to pass through when calling
        `callback`.

    Returns
    -------
    _ValueT
        The resolved result of the passed callback.
    """
    result = callback(*args)

    if isinstance(result, collections.Awaitable):  # TODO: this is probably slow
        # For some reason MYPY thinks this returns typing.Any
        return typing.cast(_ValueT, await result)

    return result


async def gather_checks(ctx: abc.Context, checks_: collections.Iterable[checks.InjectableCheck], /) -> bool:
    """Gather a collection of checks.

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The context to check.
    checks : collections.abc.Iterable[tanjun.injecting.InjectableCheck]
        An iterable of injectable checks.

    Returns
    -------
    bool
        Whether all the checks passed or not.
    """
    try:
        await asyncio.gather(*(check(ctx) for check in checks_))
        # InjectableCheck will raise FailedCheck if a false is received so if
        # we get this far then it's True.
        return True

    except errors.FailedCheck:
        return False


def match_prefix_names(content: str, names: collections.Iterable[str], /) -> typing.Optional[str]:
    """Search for a matching name in a string.

    Parameters
    ----------
    content : str
        The string to match names against.
    names : collections.abc.Iterable[str]
        The names to search for.

    Returns
    -------
    typing.Optional[str]
        The name that matched or None if no name matched.
    """
    for name in names:
        # Here we enforce that a name must either be at the end of content or be followed by a space. This helps
        # avoid issues with ambiguous naming where a command with the names "name" and "names" may sometimes hit
        # the former before the latter when triggered with the latter, leading to the command potentially being
        # inconsistently parsed.
        if content == name or content.startswith(name) and content[len(name)] == " ":
            return name


ALL_PERMISSIONS: typing.Final[hikari.Permissions] = hikari.Permissions.all_permissions()
"""All of all the known permissions based on the linked version of Hikari."""

DM_PERMISSIONS: typing.Final[hikari.Permissions] = (
    hikari.Permissions.ADD_REACTIONS
    | hikari.Permissions.VIEW_CHANNEL
    | hikari.Permissions.SEND_MESSAGES
    | hikari.Permissions.EMBED_LINKS
    | hikari.Permissions.ATTACH_FILES
    | hikari.Permissions.READ_MESSAGE_HISTORY
    | hikari.Permissions.USE_EXTERNAL_EMOJIS
    | hikari.Permissions.USE_APPLICATION_COMMANDS
)
"""Bitfield of the permissions which are accessibly within DM channels."""


def _calculate_channel_overwrites(
    channel: hikari.GuildChannel, member: hikari.Member, permissions: hikari.Permissions
) -> hikari.Permissions:
    if everyone_overwrite := channel.permission_overwrites.get(member.guild_id):
        permissions &= ~everyone_overwrite.deny
        permissions |= everyone_overwrite.allow

    deny = hikari.Permissions.NONE
    allow = hikari.Permissions.NONE

    for overwrite in filter(None, map(channel.permission_overwrites.get, member.role_ids)):
        deny |= overwrite.deny
        allow |= overwrite.allow

    permissions &= ~deny
    permissions |= allow

    if member_overwrite := channel.permission_overwrites.get(member.user.id):
        permissions &= ~member_overwrite.deny
        permissions |= member_overwrite.allow

    return permissions


def _calculate_role_permissions(
    roles: collections.Mapping[hikari.Snowflake, hikari.Role], member: hikari.Member
) -> hikari.Permissions:
    permissions = roles[member.guild_id].permissions

    for role in map(roles.get, member.role_ids):
        if role and role.id != member.guild_id:
            permissions |= role.permissions

    return permissions


# TODO: implicitly handle more special cases?
def calculate_permissions(
    member: hikari.Member,
    guild: hikari.Guild,
    roles: collections.Mapping[hikari.Snowflake, hikari.Role],
    *,
    channel: typing.Optional[hikari.GuildChannel] = None,
) -> hikari.Permissions:
    """Calculate the permissions a member has within a guild.

    Parameters
    ----------
    member : hikari.guilds.Member
        Object of the member to calculate the permissions for.
    guild : hikari.guilds.Guild
        Object of the guild to calculate their permissions within.
    roles : collections.abc.Mapping[hikari.snowflakes.Snowflake, hikari.guilds.Role]
        Mapping of snowflake IDs to objects of the roles within the target
        guild.

    Other Parameters
    ----------------
    channel : typing.Optional[hikari.channels.GuildChannel]
        Object of the channel to calculate the member's permissions in.

        If this is left as `None` then this will just calculate their
        permissions on a guild level.

    Returns
    -------
    hikari.permissions.Permission
        Value of the member's permissions either within the guild or specified
        guild channel.
    """
    if member.guild_id != guild.id:
        raise ValueError("Member object isn't from the provided guild")

    # Guild owners are implicitly admins.
    if guild.owner_id == member.user.id:
        return ALL_PERMISSIONS

    # Admin permission overrides all overwrites and is only applicable to roles.
    if (permissions := _calculate_role_permissions(roles, member)) & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return permissions

    return _calculate_channel_overwrites(channel, member, permissions)


async def _fetch_channel(
    client: abc.Client, channel: hikari.SnowflakeishOr[hikari.PartialChannel]
) -> hikari.GuildChannel:
    if isinstance(channel, hikari.GuildChannel):
        return channel

    found_channel = None
    if client.cache:
        found_channel = client.cache.get_guild_channel(hikari.Snowflake(channel))

    if not found_channel:
        raw_channel = await client.rest.fetch_channel(channel)
        assert isinstance(raw_channel, hikari.GuildChannel), "Cannot perform operation on a DM channel."
        found_channel = raw_channel

    return found_channel


async def fetch_permissions(
    client: abc.Client,
    member: hikari.Member,
    /,
    *,
    channel: typing.Optional[hikari.SnowflakeishOr[hikari.PartialChannel]] = None,
) -> hikari.Permissions:
    """Calculate the permissions a member has within a guild.

    .. note::
        This callback will fallback to REST requests if cache lookups fail or
        are not possible.

    Parameters
    ----------
    client : tanjun.abc.Client
        The Tanjun client to use for lookups.
    member : hikari.guilds.Member
        The object of the member to calculate the permissions for.

    Other Parameters
    ----------------
    channel : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.channels.GuildChannel]]
        The object of ID of the channel to get their permissions in.
        If left as `None` then this will return their base guild
        permissions.

    Returns
    -------
    hikari.permissions.Permissions
        The calculated permissions.
    """
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    guild: typing.Optional[hikari.Guild]
    roles: typing.Optional[collections.Mapping[hikari.Snowflake, hikari.Role]] = None
    guild = client.cache.get_guild(member.guild_id) if client.cache else None
    if not guild:
        guild = await client.rest.fetch_guild(member.guild_id)
        roles = guild.roles

    # Guild owners are implicitly admins.
    if guild.owner_id == member.user.id:
        return ALL_PERMISSIONS

    roles = roles or client.cache and client.cache.get_roles_view_for_guild(member.guild_id)
    if not roles:
        raw_roles = await client.rest.fetch_roles(member.guild_id)
        roles = {role.id: role for role in raw_roles}

    # Admin permission overrides all overwrites and is only applicable to roles.
    if (permissions := _calculate_role_permissions(roles, member)) & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return permissions

    channel = await _fetch_channel(client, channel)
    if channel.guild_id != guild.id:
        raise ValueError("Channel doesn't match up with the member's guild")

    return _calculate_channel_overwrites(channel, member, permissions)


def calculate_everyone_permissions(
    everyone_role: hikari.Role,
    /,
    *,
    channel: typing.Optional[hikari.GuildChannel] = None,
) -> hikari.Permissions:
    """Calculate a guild's default permissions within the guild or for a specific channel.

    Parameters
    ----------
    everyone_role : hikari.guilds.Role
        The guild's default @everyone role.

    Other Parameters
    ----------------
    channel : typing.Optional[hikari.channels.GuildChannel]
        The channel to calculate the permissions for.

        If this is left as `None` then this will just calculate the default
        permissions on a guild level.

    Returns
    -------
    hikari.permissions.Permissions
        The calculated permissions.
    """
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    permissions = everyone_role.permissions
    # Admin permission overrides all overwrites and is only applicable to roles.
    if permissions & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return permissions

    if everyone_overwrite := channel.permission_overwrites.get(everyone_role.guild_id):
        permissions &= ~everyone_overwrite.deny
        permissions |= everyone_overwrite.allow

    return permissions


async def fetch_everyone_permissions(
    client: abc.Client,
    guild_id: hikari.Snowflake,
    /,
    *,
    channel: typing.Optional[hikari.SnowflakeishOr[hikari.PartialChannel]] = None,
) -> hikari.Permissions:
    """Calculate the permissions a guild's default @everyone role has within a guild or for a specific channel.

    .. note::
        This callback will fallback to REST requests if cache lookups fail or
        are not possible.

    Parameters
    ----------
    client : tanjun.abc.Client
        The Tanjun client to use for lookups.
    guild_id : hikari.snowflakes.Snowflake
        ID of the guild to calculate the default permissions for.

    Other Parameters
    ----------------
    channel : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.channels.PartialChannel]]
        The channel to calculate the permissions for.

        If this is left as `None` then this will just calculate the default
        permissions on a guild level.


    Returns
    -------
    hikari.permissions.Permissions
        The calculated permissions.
    """
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    role = client.cache.get_role(guild_id) if client.cache else None
    if not role:
        for role in await client.rest.fetch_roles(guild_id):
            if role.id == guild_id:
                break

        else:
            raise RuntimeError("Failed to find guild's @everyone role")

    permissions = role.permissions
    # Admin permission overrides all overwrites and is only applicable to roles.
    if permissions & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return permissions

    channel = await _fetch_channel(client, channel)
    if everyone_overwrite := channel.permission_overwrites.get(guild_id):
        permissions &= ~everyone_overwrite.deny
        permissions |= everyone_overwrite.allow

    return permissions


class CastedView(collections.Mapping[_KeyT, _ValueT]):
    __slots__ = ("_buffer", "_cast", "_raw_data")

    def __init__(self, raw_data: dict[_KeyT, _ValueT], cast: collections.Callable[[_ValueT], _ValueT]) -> None:
        self._buffer: dict[_KeyT, _ValueT] = {}
        self._cast = cast
        self._raw_data = raw_data

    def __getitem__(self, key: _KeyT, /) -> _ValueT:
        try:
            return self._buffer[key]

        except KeyError:
            pass

        entry = self._raw_data[key]
        result = self._cast(entry)
        self._buffer[key] = result
        return result

    def __iter__(self) -> collections.Iterator[_KeyT]:
        return iter(self._raw_data)

    def __len__(self) -> int:
        return len(self._raw_data)
