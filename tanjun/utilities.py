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

__all__: typing.Sequence[str] = [
    "async_chain",
    "await_if_async",
    "gather_checks",
    "ALL_PERMISSIONS",
    "calculate_permissions",
    "fetch_permissions",
    "try_find_type",
]

import asyncio
import functools
import operator
import typing
from collections import abc as collections

from hikari import channels
from hikari import errors as hikari_errors
from hikari import permissions as permissions_
from hikari import snowflakes
from yuyo import backoff

from tanjun import errors as tanjun_errors

if typing.TYPE_CHECKING:
    from hikari import guilds

    from tanjun import injector
    from tanjun import traits as tanjun_traits


_ResourceT = typing.TypeVar("_ResourceT")
_ValueT = typing.TypeVar("_ValueT")


async def async_chain(iterable: typing.Iterable[typing.AsyncIterable[_ValueT]]) -> typing.AsyncIterator[_ValueT]:
    """Make an asynchronous iterator of the elements within multiple asynchronous iterators."""
    for async_iterable in iterable:
        async for value in async_iterable:
            yield value


async def await_if_async(
    callback: typing.Callable[..., typing.Union[_ValueT, typing.Awaitable[_ValueT]]], *args: typing.Any
) -> _ValueT:
    """Resole any awaitable returned by a function call.

    Parameters
    ----------
    callback : typing.Callable[..., typing.Union[_ValueT_co, typing.Awaitable[_ValueT_co]]
        The async or non-async function to call.

    Other Parameters
    ----------------
    *args : typing.Any
        A variable amount of positional arguments to pass through when calling
        `callback`.

    Returns
    -------
    _ValueT_co
        The resolved result of the passed function.
    """
    result = callback(*args)

    if isinstance(result, collections.Awaitable):  # TODO: this is probably slow
        # For some reason MYPY thinks this returns typing.Any
        return typing.cast(_ValueT, await result)

    return result


async def _wrap_check(check: typing.Awaitable[bool]) -> bool:
    # We raise on `False` to let asyncio.gather stop execution on the first failed
    # check rather than waiting for all checks to fail.
    if await check is False:
        raise tanjun_errors.FailedCheck()

    return True


async def gather_checks(checks: typing.Iterable[injector.InjectableCheck], ctx: tanjun_traits.Context) -> bool:
    """Gather a collection of checks.

    Parameters
    ----------
    checks : typing.Iterable[tanjun.injector.InjectableCheck]
        An iterable of injectable checks.
    ctx : tanjun.traits.Context
        The context to check.

    Returns
    -------
    bool
        Whether all the checks passed or not.
    """
    try:
        await asyncio.gather(*(check(ctx) for check in checks))
        # InjectableCheck will raise FailedCheck if a false is received so if
        # we get this far then it's True.
        return True

    except tanjun_errors.FailedCheck:
        return False


async def fetch_resource(
    retry: backoff.Backoff, call: typing.Callable[..., typing.Awaitable[_ResourceT]], *args: typing.Any
) -> _ResourceT:  # TODO: replace this
    """A utility function for retrying a request used by Tanjun internally."""
    retry.reset()
    async for _ in retry:
        try:
            return await call(*args)

        except (hikari_errors.RateLimitedError, hikari_errors.RateLimitTooLongError) as exc:
            if exc.retry_after > 5:
                raise

            retry.set_next_backoff(exc.retry_after)

        except hikari_errors.InternalServerError:
            continue

    else:
        return await call(*args)


ALL_PERMISSIONS = functools.reduce(operator.__xor__, permissions_.Permissions)
"""All of the known permissions based on the linked version of Hikari."""


def _calculate_channel_overwrites(
    channel: channels.GuildChannel, member: guilds.Member, permissions: permissions_.Permissions
) -> permissions_.Permissions:
    if everyone_overwrite := channel.permission_overwrites.get(member.guild_id):
        permissions &= ~everyone_overwrite.deny
        permissions |= everyone_overwrite.allow

    deny = permissions_.Permissions.NONE
    allow = permissions_.Permissions.NONE

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
    roles: typing.Mapping[snowflakes.Snowflake, guilds.Role], member: guilds.Member
) -> permissions_.Permissions:
    permissions = roles[member.guild_id].permissions

    for role in map(roles.get, member.role_ids):
        if role and role.id != member.guild_id:
            permissions |= role.permissions

    return permissions


# TODO: implicitly handle more special cases?
def calculate_permissions(
    member: guilds.Member,
    guild: guilds.Guild,
    roles: typing.Mapping[snowflakes.Snowflake, guilds.Role],
    *,
    channel: typing.Optional[channels.GuildChannel] = None,
) -> permissions_.Permissions:
    """Calculate the permissions a member has within a guild.

    Parameters
    ----------
    member : hikari.guilds.Member
        Object of the member to calculate the permissions for.
    guild : hikari.guilds.Guild
        Object of the guild to calculate their permissions within.
    roles : typing.Mapping[hikari.snowflakes.Snowflake, hikari.guilds.Role]
        Mapping of snowflake IDs to objects of the roles within the target
        guild.

    Other Parameters
    ----------------
    channel : typing.Optional[hikari.channels.GuildChannel]
        Object of the channel to calculate the member's permissions in.

        If this is left as `builtins.None` then this will just calculate their
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


async def fetch_permissions(
    client: tanjun_traits.Client,
    member: guilds.Member,
    /,
    *,
    channel: typing.Optional[snowflakes.SnowflakeishOr[channels.PartialChannel]] = None,
) -> permissions_.Permissions:
    """Calculate the permissions a member has within a guild.

    Parameters
    ----------
    client : tanjun.traits.Client
        The Tanjun client to use for lookups.
    member : hikari.guilds.Member
        The object of the member to calculate the permissions for.

    Other Parameters
    ----------------
    channel : typing.Optional[hikari.snowflakes.SnowflakeishOr[hikari.channels.GuildChannel]]
        The object of ID of the channel to get their permissions in.
        If left as `builtins.None` then this will return their base guild
        permissions.

    !!! note
        This function will fallback to REST requests if cache lookups fail or
        are not possible.

    Returns
    -------
    hikari.permissions.Permissions
        The calculated permissions.
    """
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    retry = backoff.Backoff(maximum=5, max_retries=4)
    guild: typing.Optional[guilds.Guild]
    roles: typing.Optional[typing.Mapping[snowflakes.Snowflake, guilds.Role]] = None
    guild = client.cache_service.cache.get_guild(member.guild_id) if client.cache_service else None
    if not guild:
        guild = await fetch_resource(retry, client.rest_service.rest.fetch_guild, member.guild_id)
        assert guild is not None
        roles = guild.roles

    # Guild owners are implicitly admins.
    if guild.owner_id == member.user.id:
        return ALL_PERMISSIONS

    roles = roles or client.cache_service and client.cache_service.cache.get_roles_view_for_guild(member.guild_id)
    if not roles:
        raw_roles = await fetch_resource(retry, client.rest_service.rest.fetch_roles, member.guild_id)
        roles = {role.id: role for role in raw_roles}

    # Admin permission overrides all overwrites and is only applicable to roles.
    if (permissions := _calculate_role_permissions(roles, member)) & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return permissions

    found_channel: typing.Optional[channels.GuildChannel] = None
    if isinstance(channel, channels.GuildChannel):
        found_channel = channel

    elif client.cache_service:
        found_channel = client.cache_service.cache.get_guild_channel(snowflakes.Snowflake(channel))

    if not found_channel:
        raw_channel = await fetch_resource(retry, client.rest_service.rest.fetch_channel, channel)
        assert isinstance(raw_channel, channels.GuildChannel), "Cannot perform operation on a DM channel."
        found_channel = raw_channel

    if found_channel.guild_id != guild.id:
        raise ValueError("Channel doesn't match up with the member's guild")

    return _calculate_channel_overwrites(found_channel, member, permissions)


def try_find_type(cls: typing.Type[_ValueT], *values: typing.Any) -> typing.Optional[_ValueT]:
    for value in values:
        if isinstance(value, cls):
            return value

    return None
