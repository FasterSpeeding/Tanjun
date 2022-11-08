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
"""Utility classes for making cache calls."""
from __future__ import annotations

import hikari

from .. import abc as tanjun
from ..dependencies import async_cache

_ChannelCacheT = async_cache.SfCache[hikari.PermissibleGuildChannel]
_ThreadCacheT = async_cache.SfCache[hikari.GuildThreadChannel]
_THREAD_CHANNEL_TYPES = frozenset(
    (
        hikari.ChannelType.GUILD_NEWS_THREAD,
        hikari.ChannelType.GUILD_PUBLIC_THREAD,
        hikari.ChannelType.GUILD_PRIVATE_THREAD,
    )
)


async def get_perm_channel(client: tanjun.Client, channel_id: hikari.Snowflake, /) -> hikari.PermissibleGuildChannel:
    """Get the permissionable channel for a channel.

    This will resolve threads to their parent channel.

    Parameters
    ----------
    client
        The client to use to get the channel.
    channel_id
        ID of the target channel

    Returns
    -------
    hikari.channels.PermissibleGuildChannel
        The permissible guild channel.
    """
    if client.cache and (channel := client.cache.get_guild_channel(channel_id)):
        return channel

    thread_cache = client.injector.get_type_dependency(_ThreadCacheT)
    if thread_cache and (thread := await thread_cache.get(channel_id, default=None)):
        if client.cache and (channel := client.cache.get_guild_channel(thread.parent_id)):
            return channel

        channel_id = thread.parent_id

    channel_cache = client.injector.get_type_dependency(_ChannelCacheT, default=None)
    if channel_cache and (channel := await channel_cache.get(channel_id, default=None)):
        return channel

    channel = await client.rest.fetch_channel(channel_id)
    if channel.type not in _THREAD_CHANNEL_TYPES:
        assert isinstance(channel, hikari.PermissibleGuildChannel)
        return channel

    assert isinstance(channel, hikari.GuildChannel)
    assert channel.parent_id is not None
    if client.cache and (channel_ := client.cache.get_guild_channel(channel.parent_id)):
        return channel_

    if channel_cache and (channel_ := await channel_cache.get(channel.parent_id, default=None)):
        return channel_

    channel = await client.rest.fetch_channel(channel.parent_id)
    assert isinstance(channel, hikari.PermissibleGuildChannel)
    return channel
