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
"""Functions used to calculate permissions in Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "ALL_PERMISSIONS",
    "DM_PERMISSIONS",
    "calculate_everyone_permissions",
    "calculate_permissions",
    "fetch_everyone_permissions",
    "fetch_permissions",
]

import typing

import hikari

from ._internal import cache
from .dependencies import async_cache

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from . import abc as tanjun


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
    | hikari.Permissions.USE_EXTERNAL_STICKERS
    | hikari.Permissions.USE_APPLICATION_COMMANDS
)
"""Bitfield of the permissions which are accessibly within DM channels."""

_CHANNEL_SEND_PERMS = ~(
    hikari.Permissions.SEND_TTS_MESSAGES
    | hikari.Permissions.EMBED_LINKS
    | hikari.Permissions.ATTACH_FILES
    | hikari.Permissions.MENTION_ROLES
)


# TODO: which threads are on channels?
_CHANNEL_VIEW_PERMS = ~(
    hikari.Permissions.CREATE_INSTANT_INVITE
    | hikari.Permissions.MANAGE_CHANNELS
    | hikari.Permissions.ADD_REACTIONS
    | hikari.Permissions.SEND_MESSAGES
    | hikari.Permissions.MANAGE_MESSAGES
    | hikari.Permissions.READ_MESSAGE_HISTORY
    | hikari.Permissions.USE_EXTERNAL_EMOJIS  # TODO: does this effect reactions???
    # TODO: technically this is a per-channel perm but that might not be what ppl expect
    | hikari.Permissions.MANAGE_WEBHOOKS
    # TODO: do context menus get blocked if you can't send messages like slash commands
    # also what about buttons?
    | hikari.Permissions.USE_APPLICATION_COMMANDS
    | hikari.Permissions.CREATE_PRIVATE_THREADS
    | hikari.Permissions.USE_EXTERNAL_STICKERS
    | hikari.Permissions.CREATE_PUBLIC_THREADS
    | hikari.Permissions.MODERATE_MEMBERS
    | ~_CHANNEL_SEND_PERMS
)


# TODO: this can't be all right?
_MUTE_PERMISSIONS = hikari.Permissions.VIEW_CHANNEL | hikari.Permissions.READ_MESSAGE_HISTORY

_THREAD_CHANNEL_TYPES = frozenset(
    (
        hikari.ChannelType.GUILD_NEWS_THREAD,
        hikari.ChannelType.GUILD_PUBLIC_THREAD,
        hikari.ChannelType.GUILD_PRIVATE_THREAD,
    )
)
_MOVABLE_CHANNEL_TYPES = frozenset(
    (*_THREAD_CHANNEL_TYPES, hikari.ChannelType.GUILD_VOICE, hikari.ChannelType.GUILD_STAGE)
)


def _normalise_permissions(
    permissions: hikari.Permissions,
    /,
    *,
    member: typing.Optional[hikari.Member] = None,
    channel_type: typing.Union[hikari.ChannelType, int, None] = None,
) -> hikari.Permissions:
    if member and member.communication_disabled_until():
        return permissions & _MUTE_PERMISSIONS

    not_permissions = ~permissions
    if not_permissions & hikari.Permissions.CONNECT:
        pass
        # permissions &= ~hikari.Permissions.MANAGE_CHANNELS
        # TODO: what perms???

    # TODO: how to handle when channel_type is None???

    if not_permissions & hikari.Permissions.VIEW_CHANNEL:
        if channel_type and channel_type not in _MOVABLE_CHANNEL_TYPES:
            permissions &= _CHANNEL_VIEW_PERMS

    else:
        send_perm = (
            hikari.Permissions.SEND_MESSAGES_IN_THREADS
            if channel_type in _THREAD_CHANNEL_TYPES
            else hikari.Permissions.SEND_MESSAGES
        )
        if not_permissions & send_perm:
            permissions &= _CHANNEL_SEND_PERMS

    return permissions


def _calculate_channel_overwrites(
    channel: hikari.PermissibleGuildChannel, member: hikari.Member, permissions: hikari.Permissions, /
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

    return _normalise_permissions(permissions, channel_type=channel.type, member=member)


def _calculate_role_permissions(
    roles: collections.Mapping[hikari.Snowflake, hikari.Role], member: hikari.Member, /
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
    /,
    *,
    channel: typing.Optional[hikari.PermissibleGuildChannel] = None,
) -> hikari.Permissions:
    """Calculate the permissions a member has within a guild.

    Parameters
    ----------
    member
        Object of the member to calculate the permissions for.
    guild
        Object of the guild to calculate their permissions within.
    roles
        Mapping of snowflake IDs to objects of the roles within the target
        guild.
    channel
        Object of the channel to calculate the member's permissions in.

        If this is left as [None][] then this will just calculate their
        permissions on a guild level.

    Returns
    -------
    hikari.Permission
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
        return _normalise_permissions(permissions, member=member)

    return _calculate_channel_overwrites(channel, member, permissions)


async def _fetch_channel(
    client: tanjun.Client, channel: hikari.SnowflakeishOr[hikari.GuildChannel], /
) -> hikari.PermissibleGuildChannel:
    if isinstance(channel, hikari.PermissibleGuildChannel):
        return channel

    # If this is a non-permissible guild object then the assumption is that the parent
    # channel has the perms as this is how it works under the current threads system.
    if isinstance(channel, hikari.GuildChannel) and channel.parent_id:
        channel = channel.parent_id

    return await cache.get_perm_channel(client, hikari.Snowflake(channel))


_GuildCacheT = async_cache.SfCache[hikari.Guild]
_RoleCacheT = async_cache.SfCache[hikari.Role]
_GuldRoleCacheT = async_cache.SfGuildBound[hikari.Role]


async def fetch_permissions(
    client: tanjun.Client,
    member: hikari.Member,
    /,
    *,
    channel: typing.Optional[hikari.SnowflakeishOr[hikari.GuildChannel]] = None,
) -> hikari.Permissions:
    """Calculate the permissions a member has within a guild.

    !!! note
        This callback will fallback to REST requests if cache lookups fail or
        are not possible.

    Parameters
    ----------
    client
        The Tanjun client to use for lookups.
    member
        The object of the member to calculate the permissions for.
    channel
        The object or ID of the channel to get their permissions in.
        If left as [None][] then this will return their base guild
        permissions.

    Returns
    -------
    hikari.Permissions
        The calculated permissions.
    """
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    guild: typing.Optional[hikari.Guild]
    roles: typing.Optional[collections.Mapping[hikari.Snowflake, hikari.Role]] = None
    guild = client.cache.get_guild(member.guild_id) if client.cache else None
    if not guild and (guild_cache := client.get_type_dependency(_GuildCacheT)):
        try:
            guild = await guild_cache.get(member.guild_id)

        except async_cache.EntryNotFound:
            raise

        except async_cache.CacheMissError:
            pass

    if not guild:
        guild = await client.rest.fetch_guild(member.guild_id)
        roles = guild.roles

    # Guild owners are implicitly admins.
    if guild.owner_id == member.user.id:
        return ALL_PERMISSIONS

    roles = roles or client.cache and client.cache.get_roles_view_for_guild(member.guild_id)
    if not roles and (role_cache := client.get_type_dependency(_GuldRoleCacheT)):
        roles = {role.id: role for role in await role_cache.iter_for_guild(member.guild_id)}

    if not roles:
        raw_roles = await client.rest.fetch_roles(member.guild_id)
        roles = {role.id: role for role in raw_roles}

    # Admin permission overrides all overwrites and is only applicable to roles.
    if (permissions := _calculate_role_permissions(roles, member)) & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return _normalise_permissions(permissions, member=member)

    channel = await _fetch_channel(client, channel)
    if channel.guild_id != guild.id:
        raise ValueError("Channel doesn't match up with the member's guild")

    return _calculate_channel_overwrites(channel, member, permissions)


def calculate_everyone_permissions(
    everyone_role: hikari.Role, /, *, channel: typing.Optional[hikari.PermissibleGuildChannel] = None
) -> hikari.Permissions:
    """Calculate a guild's default permissions within the guild or for a specific channel.

    Parameters
    ----------
    everyone_role
        The guild's default @everyone role.
    channel
        The channel to calculate the permissions for.

        If this is left as [None][] then this will just calculate the default
        permissions on a guild level.

    Returns
    -------
    hikari.Permissions
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

    return _normalise_permissions(permissions, channel_type=channel.type if channel else None)


async def fetch_everyone_permissions(
    client: tanjun.Client,
    guild_id: hikari.Snowflake,
    /,
    *,
    channel: typing.Optional[hikari.SnowflakeishOr[hikari.GuildChannel]] = None,
) -> hikari.Permissions:
    """Calculate the permissions a guild's default @everyone role has within a guild or for a specific channel.

    !!! note
        This callback will fallback to REST requests if cache lookups fail or
        are not possible.

    Parameters
    ----------
    client
        The Tanjun client to use for lookups.
    guild_id
        ID of the guild to calculate the default permissions for.
    channel
        The channel to calculate the permissions for.

        If this is left as [None][] then this will just calculate the default
        permissions on a guild level.

    Returns
    -------
    hikari.Permissions
        The calculated permissions.
    """
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    role = client.cache.get_role(guild_id) if client.cache else None
    if not role and (role_cache := client.get_type_dependency(_RoleCacheT)):
        try:
            role = await role_cache.get(guild_id)

        except async_cache.EntryNotFound:
            raise

        except async_cache.CacheMissError:
            pass

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

    return _normalise_permissions(permissions, channel_type=channel.type if channel else None)
