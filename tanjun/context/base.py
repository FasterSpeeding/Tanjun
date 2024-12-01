# BSD 3-Clause License
#
# Copyright (c) 2020-2024, Faster Speeding
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

import hikari
import typing_extensions
from hikari import snowflakes

from tanjun import abc as tanjun

if typing.TYPE_CHECKING:
    from collections import abc as collections
    from typing import Self

    from alluka import abc as alluka

    _T = typing.TypeVar("_T")
    _DefaultT = typing.TypeVar("_DefaultT")


class BaseContext(tanjun.Context):
    """Base class for the standard command context implementations.

    !!! warning "deprecated"
        Using Tanjun contexts as an Alluka context is
        deprecated behaviour and may not behave as expected.
    """

    __slots__ = ("_client", "_component", "_final")

    def __init__(self, client: tanjun.Client, /) -> None:
        self._client = client
        self._component: tanjun.Component | None = None
        self._final = False

    @property
    def cache(self) -> hikari.api.Cache | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.cache

    @property
    def client(self) -> tanjun.Client:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client

    @property
    def component(self) -> tanjun.Component | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._component

    @property
    def events(self) -> hikari.api.EventManager | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.events

    @property
    def server(self) -> hikari.api.InteractionServer | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.server

    @property
    def rest(self) -> hikari.api.RESTClient:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.rest

    @property
    def shard(self) -> hikari.api.GatewayShard | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if not self._client.shards:
            return None

        if self.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._client.shards, self.guild_id)

        else:
            shard_id = 0

        return self._client.shards.shards[shard_id]

    @property
    def shards(self) -> hikari.ShardAware | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.shards

    @property
    def voice(self) -> hikari.api.VoiceComponent | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client.voice

    def _assert_not_final(self) -> None:
        if self._final:
            error_message = "Cannot modify a finalised context"
            raise TypeError(error_message)

    def finalise(self) -> Self:
        """Finalise the context, dis-allowing any further modifications.

        Returns
        -------
        Self
            The context itself to enable chained calls.
        """
        self._final = True
        return self

    def set_component(self, component: tanjun.Component | None, /) -> Self:
        # <<inherited docstring from tanjun.abc.Context>>.
        self._assert_not_final()
        self._component = component
        return self

    def get_channel(self) -> hikari.TextableGuildChannel | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._client.cache:
            channel = self._client.cache.get_guild_channel(self.channel_id)
            assert channel is None or isinstance(channel, hikari.TextableGuildChannel)
            return channel

        return None  # MyPy compat

    def get_guild(self) -> hikari.Guild | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self.guild_id is not None and self._client.cache:
            return self._client.cache.get_guild(self.guild_id)

        return None  # MyPy compat

    async def fetch_channel(self) -> hikari.TextableChannel:
        # <<inherited docstring from tanjun.abc.Context>>.
        channel = await self._client.rest.fetch_channel(self.channel_id)
        assert isinstance(channel, hikari.TextableChannel)
        return channel

    async def fetch_guild(self) -> hikari.Guild | None:  # TODO: or raise?
        # <<inherited docstring from tanjun.abc.Context>>.
        if self.guild_id is not None:
            return await self._client.rest.fetch_guild(self.guild_id)

        return None  # MyPy compat

    @property
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def injection_client(self) -> alluka.Client:
        return self._client.injector

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def cache_result(self, callback: alluka.CallbackSig[_T], value: _T, /) -> None:  # noqa: ARG002
        return None

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def call_with_di(
        self,
        callback: collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, typing.Any]],
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> typing.NoReturn: ...

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T: ...

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def call_with_di(self, callback: collections.Callable[..., _T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        return self._client.injector.call_with_di(callback, *args, **kwargs)

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    async def call_with_async_di(self, callback: alluka.CallbackSig[_T], *args: typing.Any, **kwargs: typing.Any) -> _T:
        return await self._client.injector.call_with_async_di(callback, *args, **kwargs)

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_cached_result(self, callback: alluka.CallbackSig[_T], /) -> _T: ...

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_cached_result(self, callback: alluka.CallbackSig[_T], /, *, default: _DefaultT) -> _T | _DefaultT: ...

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_cached_result(
        self, callback: alluka.CallbackSig[_T],  # noqa: ARG002
        /, *, default: tanjun.NoDefault | _DefaultT = tanjun.NO_DEFAULT
    ) -> _T | _DefaultT:
        if default is tanjun.NO_DEFAULT:
            raise KeyError

        return default

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> _T | _DefaultT: ...

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_type_dependency(
        self, type_: type[_T], /, *, default: tanjun.NoDefault | _DefaultT = tanjun.NO_DEFAULT
    ) -> _T | _DefaultT:
        result: _T | _DefaultT | tanjun.NoDefault = self._client.injector.get_type_dependency(type_, default=default)

        if result is tanjun.NO_DEFAULT:
            raise KeyError

        return result
