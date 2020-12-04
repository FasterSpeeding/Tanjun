# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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
from __future__ import annotations

__all__: typing.Sequence[str] = [
    "async_chain",
    "await_if_async",
    "gather_checks",
    "ALL_PERMISSIONS",
    "calculate_permissions",
    "with_function_wrapping",
]

import asyncio
import typing

from hikari import channels
from hikari import errors as hikari_errors
from hikari import permissions as permissions_
from yuyo import backoff

from tanjun import errors as tanjun_errors

if typing.TYPE_CHECKING:
    from hikari import guilds
    from hikari import snowflakes

    from tanjun import traits as tanjun_traits


_ResourceT = typing.TypeVar("_ResourceT")
_ValueT = typing.TypeVar("_ValueT")


async def async_chain(iterable: typing.Iterable[typing.AsyncIterable[_ValueT]]) -> typing.AsyncIterator[_ValueT]:
    for async_iterable in iterable:
        async for value in async_iterable:
            yield value


async def await_if_async(
    callback: typing.Callable[..., typing.Union[_ValueT, typing.Awaitable[_ValueT]]], *args: typing.Any
) -> _ValueT:
    result = callback(*args)

    if isinstance(result, typing.Awaitable):
        # For some reason MYPY thinks this returns typing.Any
        return typing.cast(_ValueT, await result)

    return result


async def _wrap_check(check: typing.Awaitable[bool]) -> bool:
    if not await check:
        raise tanjun_errors.FailedCheck()

    return True


async def gather_checks(checks: typing.Iterable[typing.Awaitable[bool]]) -> bool:
    try:
        results = await asyncio.gather(*map(_wrap_check, checks))
        # min can't take an empty sequence so we need to have a special case for if no-checks
        # are passed.
        return bool(min(results)) if results else True

    except tanjun_errors.FailedCheck:
        return False


async def fetch_resource(
    retry: backoff.Backoff, call: typing.Callable[..., typing.Awaitable[_ResourceT]], *args: typing.Any
) -> _ResourceT:
    retry.reset()
    async for _ in retry:
        try:
            return await call(*args)

        except hikari_errors.RateLimitedError as exc:
            if exc.retry_after > 5:
                raise

            retry.set_next_backoff(exc.retry_after)

        except hikari_errors.InternalServerError:
            continue

    else:
        return await call(*args)


ALL_PERMISSIONS = permissions_.Permissions.NONE
for _permission in permissions_.Permissions:
    ALL_PERMISSIONS |= _permission

del _permission


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

    for role in filter(None, map(roles.get, member.role_ids)):
        if role.id != member.guild_id:
            permissions |= role.permissions

    return permissions


async def calculate_permissions(
    client: tanjun_traits.Client,
    member: guilds.Member,
    /,
    *,
    channel: typing.Optional[snowflakes.SnowflakeishOr[channels.GuildChannel]],
) -> permissions_.Permissions:
    # The ordering of how this adds and removes permissions does matter.
    # For more information see https://discord.com/developers/docs/topics/permissions#permission-hierarchy.
    retry = backoff.Backoff(maximum=5, max_retries=4)
    found_channel = channel if isinstance(channel, channels.GuildChannel) else None
    guild: typing.Optional[guilds.Guild] = None
    roles: typing.Optional[typing.Mapping[snowflakes.Snowflake, guilds.Role]] = None
    if client.cache_service:
        if not found_channel and channel:
            found_channel = client.cache_service.cache.get_guild_channel(snowflakes.Snowflake(channel))

        guild = client.cache_service.cache.get_guild(member.guild_id)
        roles = client.cache_service.cache.get_roles_view_for_guild(member.guild_id)

    if not guild:
        raw_guild = await fetch_resource(retry, client.rest_service.rest.fetch_guild, member.guild_id)
        guild = raw_guild

    # Guild owners are implicitly admins.
    if guild.owner_id == member.user.id:
        return ALL_PERMISSIONS

    if not roles:
        raw_roles = await fetch_resource(retry, client.rest_service.rest.fetch_roles, member.guild_id)
        roles = {role.id: role for role in raw_roles}

    # Admin permission overrides all overwrites and is only applicable to roles.
    if (permissions := _calculate_role_permissions(roles, member)) & permissions.ADMINISTRATOR:
        return ALL_PERMISSIONS

    if not channel:
        return permissions

    if not found_channel:
        raw_channel = await fetch_resource(retry, client.rest_service.rest.fetch_channel, channel)
        assert isinstance(raw_channel, channels.GuildChannel), "We shouldn't get DM channels in guilds."
        found_channel = raw_channel

    return _calculate_channel_overwrites(found_channel, member, permissions)


def with_function_wrapping(obj: typing.Any, function_field: str, /) -> None:
    obj.__annotations__ = property(lambda self: getattr(self, function_field).__annotations__)
    obj.__doc__ = property(lambda self: getattr(self, function_field).__doc__)
    obj.__module__ = property(lambda self: getattr(self, function_field).__module__)
    obj.__wrapped__ = property(lambda self: getattr(self, function_field).__wrapped__)
