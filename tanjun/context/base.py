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
"""Base command context implementation."""
from __future__ import annotations

__all__: list[str] = []

import typing

import alluka
import hikari
from hikari import snowflakes

from .. import abc as tanjun

if typing.TYPE_CHECKING:
    from typing_extensions import Self


class BaseContext(alluka.BasicContext, tanjun.Context):
    """Base class for the standard command context implementations."""

    __slots__ = ("_client", "_component", "_final")

    def __init__(self, client: tanjun.Client) -> None:
        super().__init__(client.injector)
        self._client = client
        self._component: typing.Optional[tanjun.Component] = None
        self._final = False
        self._set_type_special_case(tanjun.Context, self)

    @property
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.cache

    @property
    def client(self) -> tanjun.Client:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client

    @property
    def component(self) -> typing.Optional[tanjun.Component]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._component

    @property
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.events

    @property
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.server

    @property
    def rest(self) -> hikari.api.RESTClient:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.rest

    @property
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        # <<inherited docstring from tanjun.abc.Context>>.
        if not self._client.shards:
            return None

        if self.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._client.shards, self.guild_id)

        else:
            shard_id = 0

        return self._client.shards.shards[shard_id]

    @property
    def shards(self) -> typing.Optional[hikari.ShardAware]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.shards

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.voice

    def _assert_not_final(self) -> None:
        if self._final:
            raise TypeError("Cannot modify a finalised context")

    def finalise(self) -> Self:
        """Finalise the context, dis-allowing any further modifications.

        Returns
        -------
        Self
            The context itself to enable chained calls.
        """
        self._final = True
        return self

    def set_component(self, component: typing.Optional[tanjun.Component], /) -> Self:
        # <<inherited docstring from tanjun.abc.Context>>.
        self._assert_not_final()
        if component:
            self._set_type_special_case(tanjun.Component, component)

        elif self._component:
            self._remove_type_special_case(tanjun.Component)

        self._component = component
        return self

    def get_channel(self) -> typing.Optional[hikari.TextableGuildChannel]:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._client.cache:
            channel = self._client.cache.get_guild_channel(self.channel_id)
            assert channel is None or isinstance(channel, hikari.TextableGuildChannel)
            return channel

        return None

    def get_guild(self) -> typing.Optional[hikari.Guild]:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self.guild_id is not None and self._client.cache:
            return self._client.cache.get_guild(self.guild_id)

        return None

    async def fetch_channel(self) -> hikari.TextableChannel:
        # <<inherited docstring from tanjun.abc.Context>>.
        channel = await self._client.rest.fetch_channel(self.channel_id)
        assert isinstance(channel, hikari.TextableChannel)
        return channel

    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:  # TODO: or raise?
        # <<inherited docstring from tanjun.abc.Context>>.
        if self.guild_id is not None:
            return await self._client.rest.fetch_guild(self.guild_id)

        return None
