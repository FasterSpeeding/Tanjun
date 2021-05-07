# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2021, Faster Speeding
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

__all__: typing.Sequence[str] = ["Context"]

import typing

from hikari import snowflakes

from tanjun import traits

if typing.TYPE_CHECKING:
    from hikari import messages
    from hikari import traits as hikari_traits
    from hikari.api import shard as shard_


class Context(traits.Context):
    """Standard implementation of a command context as used within Tanjun."""

    __slots__: typing.Sequence[str] = (
        "_client",
        "command",
        "content",
        "_message",
        "_rest",
        "triggering_name",
        "triggering_prefix",
        "_shard",
    )

    def __init__(
        self,
        client: traits.Client,
        /,
        content: str,
        message: messages.Message,
        *,
        command: typing.Optional[traits.ExecutableCommand] = None,
        triggering_name: typing.Optional[str] = None,
        triggering_prefix: typing.Optional[str] = None,
    ) -> None:
        if message.content is None:
            raise ValueError("Cannot spawn context with a contentless message.")

        self._client = client
        self.command = command
        self.content = content
        self._message = message
        self.triggering_name = triggering_name
        self.triggering_prefix = triggering_prefix

    def __repr__(self) -> str:
        return f"Context <{self.message!r}, {self.command!r}>"

    @property
    def cache_service(self) -> typing.Optional[hikari_traits.CacheAware]:
        return self._client.cache_service

    @property
    def client(self) -> traits.Client:
        return self._client

    @property
    def event_service(self) -> hikari_traits.EventManagerAware:
        return self._client.event_service

    @property
    def message(self) -> messages.Message:
        return self._message

    @property
    def rest_service(self) -> hikari_traits.RESTAware:
        return self._client.rest_service

    @property
    def shard_service(self) -> hikari_traits.ShardAware:
        return self._client.shard_service

    @property
    def shard(self) -> shard_.GatewayShard:
        if self.message.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self.shard_service, self.message.guild_id)

        else:
            shard_id = 0

        return self.shard_service.shards[shard_id]
