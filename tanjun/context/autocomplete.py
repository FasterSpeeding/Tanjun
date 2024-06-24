# -*- coding: utf-8 -*-
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
"""Autocomplete context implementation."""
from __future__ import annotations

__all__: list[str] = ["AutocompleteContext"]


import typing

import hikari
import typing_extensions
from hikari import snowflakes

from .. import _internal
from .. import abc as tanjun

if typing.TYPE_CHECKING:
    from alluka import abc as alluka
    import asyncio
    import datetime
    from collections import abc as collections

    _ValueT = typing.TypeVar("_ValueT", int, float, str)
    _T = typing.TypeVar("_T")
    _DefaultT = typing.TypeVar("_DefaultT")


class AutocompleteContext(tanjun.AutocompleteContext):
    """Standard implementation of an autocomplete context.

    !!! warning "deprecated"
        Using Tanjun contexts as an Alluka context is
        deprecated behaviour and may not behave as expected.
    """

    __slots__ = ("_client", "_command_name", "_focused", "_future", "_has_responded", "_interaction", "_options")

    def __init__(
        self,
        client: tanjun.Client,
        interaction: hikari.AutocompleteInteraction,
        *,
        future: typing.Optional[asyncio.Future[hikari.api.InteractionAutocompleteBuilder]] = None,
    ) -> None:
        """Initialise an autocomplete context.

        Parameters
        ----------
        client
            The Tanjun client this context is bound to.
        interaction
            The autocomplete interaction this context is for.
        future
            A future used to set the initial response if this is being called
            through the REST webhook flow.
        """
        self._client = client
        self._future = future
        self._has_responded = False
        self._interaction = interaction

        focused: typing.Optional[hikari.AutocompleteInteractionOption] = None
        self._options: dict[str, hikari.AutocompleteInteractionOption] = {}
        command_name, options = _internal.flatten_options(interaction.command_name, interaction.options)
        for option in options:
            self._options[option.name] = option
            if option.is_focused:
                focused = self._options[option.name]

        assert focused is not None
        self._command_name = command_name
        self._focused = focused

    @property
    def author(self) -> hikari.User:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.user

    @property
    def channel_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.channel_id

    @property
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client.cache

    @property
    def client(self) -> tanjun.Client:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client

    @property
    def triggering_name(self) -> str:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._command_name

    @property
    def created_at(self) -> datetime.datetime:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.created_at

    @property
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client.events

    @property
    def focused(self) -> hikari.AutocompleteInteractionOption:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._focused

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.guild_id

    @property
    def member(self) -> typing.Optional[hikari.Member]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.member

    @property
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client.server

    @property
    def rest(self) -> hikari.api.RESTClient:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client.rest

    @property
    def shard(self) -> typing.Optional[hikari.api.GatewayShard]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        if not self._client.shards:
            return None

        if self.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._client.shards, self.guild_id)

        else:
            shard_id = 0

        return self._client.shards.shards[shard_id]

    @property
    def shards(self) -> typing.Optional[hikari.ShardAware]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client.shards

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._client.voice

    @property
    def has_responded(self) -> bool:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._has_responded

    @property
    def interaction(self) -> hikari.AutocompleteInteraction:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction

    @property
    def options(self) -> collections.Mapping[str, hikari.AutocompleteInteractionOption]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._options.copy()

    async def fetch_channel(self) -> hikari.TextableChannel:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return await self._interaction.fetch_channel()

    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return await self._interaction.fetch_guild()

    def get_channel(self) -> typing.Optional[hikari.TextableGuildChannel]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.get_channel()

    def get_guild(self) -> typing.Optional[hikari.Guild]:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.get_guild()

    async def set_choices(
        self,
        choices: typing.Union[collections.Mapping[str, _ValueT], collections.Iterable[tuple[str, _ValueT]]] = (),
        /,
        **kwargs: _ValueT,
    ) -> None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        if self._has_responded:
            raise RuntimeError("Cannot set choices after responding")

        choices = dict(choices, **kwargs)
        if len(choices) > 25:
            raise ValueError("Cannot set more than 25 choices")

        self._has_responded = True
        choice_objects = [
            hikari.impl.AutocompleteChoiceBuilder(name=name, value=value) for name, value in choices.items()
        ]

        if self._future:
            self._future.set_result(self._interaction.build_response(choice_objects))

        else:
            await self._interaction.create_response(choice_objects)

    @property
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def injection_client(self) -> alluka.Client:
        return self._client.injector

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def cache_result(self, callback: alluka.CallbackSig[_T], value: _T, /) -> None:
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
    def get_cached_result(
        self, callback: alluka.CallbackSig[_T], /, *, default: _DefaultT
    ) -> typing.Union[_T, _DefaultT]: ...

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_cached_result(
        self,
        callback: alluka.CallbackSig[_T],
        /,
        *,
        default: typing.Union[_DefaultT, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    ) -> typing.Union[_T, _DefaultT]:
        if default is tanjun.NO_DEFAULT:
            raise KeyError

        return default

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_type_dependency(self, type_: type[_T], /) -> _T: ...

    @typing.overload
    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_type_dependency(self, type_: type[_T], /, *, default: _DefaultT) -> typing.Union[_T, _DefaultT]: ...

    @typing_extensions.deprecated("Using a Tanjun context as an Alluka context is deprecated")
    def get_type_dependency(
        self, type_: type[_T], /, *, default: typing.Union[_DefaultT, tanjun.NoDefault] = tanjun.NO_DEFAULT
    ) -> typing.Union[_T, _DefaultT]:
        result: typing.Union[_DefaultT, tanjun.NoDefault, _T] = self._client.injector.get_type_dependency(
            type_, default=default
        )

        if result is tanjun.NO_DEFAULT:
            raise KeyError

        return result
