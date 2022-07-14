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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import types
import typing
from collections import abc as collections
from unittest import mock

import alluka
import hikari
import pytest
from hikari import traits

import tanjun
from tanjun.context import base as base_context

_T = typing.TypeVar("_T")


def stub_class(
    cls: typing.Type[_T],
    /,
    args: collections.Sequence[typing.Any] = (),
    kwargs: typing.Optional[collections.Mapping[str, typing.Any]] = None,
    **namespace: typing.Any,
) -> _T:
    namespace["__slots__"] = ()

    for name in getattr(cls, "__abstractmethods__", None) or ():
        if name not in namespace:
            namespace[name] = mock.MagicMock()

    name = origin.__name__ if (origin := getattr(cls, "__origin__", None)) else cls.__name__
    new_cls = types.new_class(name, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)(*args, **kwargs or {})


@pytest.fixture()
def mock_client() -> tanjun.abc.Client:
    return mock.MagicMock(tanjun.abc.Client, rest=mock.AsyncMock(hikari.api.RESTClient))


@pytest.fixture()
def mock_component() -> tanjun.abc.Component:
    return mock.MagicMock(tanjun.abc.Component)


class TestBaseContext:
    @pytest.fixture()
    def context(
        self,
        mock_client: mock.Mock,
    ) -> base_context.BaseContext:
        return stub_class(base_context.BaseContext, args=(mock_client,))

    def test_cache_property(self, context: tanjun.abc.Context, mock_client: mock.Mock):
        assert context.cache is mock_client.cache

    def test_client_property(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert context.client is mock_client

    def test_component_property(self, context: base_context.BaseContext, mock_component: tanjun.abc.Component):
        assert context.component is None

    def test_events_proprety(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert context.events is mock_client.events

    def test_rest_property(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert context.rest is mock_client.rest

    def test_server_property(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert context.server is mock_client.server

    def test_shard_property(self, mock_client: mock.Mock):
        mock_shard = mock.Mock()
        mock_client.shards = mock.MagicMock(spec=traits.ShardAware, shard_count=5, shards={2: mock_shard})
        context = stub_class(base_context.BaseContext, guild_id=hikari.Snowflake(123321123312), args=(mock_client,))

        assert context.shard is mock_shard

    def test_shard_property_when_dm(self, mock_client: mock.Mock):
        mock_shard = mock.Mock()
        mock_client.shards = mock.Mock(shards={0: mock_shard})
        context = stub_class(base_context.BaseContext, guild_id=None, args=(mock_client,))

        assert context.shard is mock_shard

    def test_shard_property_when_no_shards(self, context: tanjun.context.MessageContext):
        context._client = mock.Mock(shards=None)

        assert context.shard is None

    def test_shards_property(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert context.shards is mock_client.shards

    def test_voice_property(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert context.voice is mock_client.voice

    def test_finalise(self, context: base_context.BaseContext):
        context.finalise()
        assert context._final is True

    def test_set_component(self, context: base_context.BaseContext):
        component = mock.Mock()

        assert context.set_component(component) is context

        assert context.component is component
        assert context.get_type_dependency(tanjun.abc.Component) is component

    def test_set_component_when_none_and_previously_set(self, context: base_context.BaseContext):
        assert isinstance(context.injection_client.get_type_dependency, mock.Mock)
        context.injection_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        mock_component = mock.Mock()
        context.set_component(mock_component)
        context.set_component(None)

        assert context.component is None
        assert context.get_type_dependency(tanjun.abc.Component) is alluka.abc.UNDEFINED

    def test_set_component_when_none(self, context: base_context.BaseContext):
        assert isinstance(context.injection_client.get_type_dependency, mock.Mock)
        context.injection_client.get_type_dependency.return_value = alluka.abc.UNDEFINED
        context.set_component(None)
        context.set_component(None)

        assert context.component is None
        assert context.get_type_dependency(tanjun.abc.Component) is alluka.abc.UNDEFINED

    def test_set_component_when_final(self, context: base_context.BaseContext):
        component = mock.Mock()
        context.finalise()

        with pytest.raises(TypeError):
            context.set_component(component)

        assert context.component is not component

    def test_get_channel(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert mock_client.cache is not None
        mock_client.cache.get_guild_channel.return_value = mock.Mock(hikari.TextableGuildChannel)

        assert context.get_channel() is mock_client.cache.get_guild_channel.return_value

        mock_client.cache.get_guild_channel.assert_called_once_with(context.channel_id)

    def test_get_channel_when_cache_returns_none(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert mock_client.cache is not None
        mock_client.cache.get_guild_channel.return_value = None

        assert context.get_channel() is None

        mock_client.cache.get_guild_channel.assert_called_once_with(context.channel_id)

    def test_get_channel_when_cacheless(self):
        context = stub_class(base_context.BaseContext, guild_id=None, args=(mock.Mock(cache=None),))

        assert context.get_channel() is None

    def test_get_guild(self, context: base_context.BaseContext, mock_client: mock.Mock):
        assert mock_client.cache is not None
        assert context.get_guild() is mock_client.cache.get_guild.return_value
        mock_client.cache.get_guild.assert_called_once_with(context.guild_id)

    def test_get_guild_when_cacheless(self):
        context = stub_class(base_context.BaseContext, guild_id=None, args=(mock.Mock(cache=None),))

        assert context.get_guild() is None

    def test_get_guild_when_dm_bound(self):
        mock_client = mock.MagicMock()
        context = stub_class(base_context.BaseContext, guild_id=None, args=(mock_client,))

        assert context.get_guild() is None
        mock_client.cache.get_guild.assert_not_called()

    @pytest.mark.asyncio()
    async def test_fetch_channel(self, context: base_context.BaseContext, mock_client: mock.Mock):
        mock_client.rest.fetch_channel.return_value = mock.Mock(hikari.TextableChannel)

        result = await context.fetch_channel()

        assert result is mock_client.rest.fetch_channel.return_value
        mock_client.rest.fetch_channel.assert_called_once_with(context.channel_id)

    @pytest.mark.asyncio()
    async def test_fetch_guild(self, context: base_context.BaseContext, mock_client: mock.Mock):
        result = await context.fetch_guild()

        assert result is mock_client.rest.fetch_guild.return_value
        mock_client.rest.fetch_guild.assert_called_once_with(context.guild_id)

    @pytest.mark.asyncio()
    async def test_fetch_guild_when_dm_bound(self, mock_client: mock.Mock):
        context = stub_class(base_context.BaseContext, guild_id=None, args=(mock_client,))

        result = await context.fetch_guild()

        assert result is None
        mock_client.rest.fetch_guild.assert_not_called()
