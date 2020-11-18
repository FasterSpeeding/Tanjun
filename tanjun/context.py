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

__all__: typing.Sequence[str] = ["Context"]

import typing

from tanjun import traits

if typing.TYPE_CHECKING:
    from hikari import messages
    from hikari import traits as hikari_traits


class Context(traits.Context):
    __slots__: typing.Sequence[str] = (
        "_client",
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
        triggering_name: typing.Optional[str] = None,
        triggering_prefix: typing.Optional[str] = None,
    ) -> None:
        if message.content is None:
            raise ValueError("Cannot spawn context with a contentless message.")

        self._client = client
        self.content = content
        self._message = message
        self.triggering_name = triggering_name
        self.triggering_prefix = triggering_prefix

    @property
    def client(self) -> traits.Client:
        return self._client

    @property
    def cache(self) -> typing.Optional[hikari_traits.CacheAware]:
        return self._client.cache

    @property
    def dispatcher(self) -> hikari_traits.DispatcherAware:
        return self._client.dispatch

    @property
    def message(self) -> messages.Message:
        return self._message

    @property
    def rest(self) -> hikari_traits.RESTAware:
        return self._client.rest

    # @property
    # def shard(self) -> shard_.GatewayShard:
    #     return self._shard
