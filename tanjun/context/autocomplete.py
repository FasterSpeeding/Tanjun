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
"""Standard implementation for tanjun's autocomplete context."""
from __future__ import annotations

__all__: list[str] = ["AutocompleteContext"]


import typing

from .. import abc
from .. import injecting
from . import slash

if typing.TYPE_CHECKING:
    import asyncio
    import datetime
    from collections import abc as collections

    import hikari
    from hikari import traits as hikari_traits


_ValueT = typing.TypeVar("_ValueT", int, float, str)

_COMMAND_OPTION_TYPES: typing.Final[frozenset[hikari.OptionType]] = frozenset(
    [hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP]
)


class AutocompleteOption(slash.SlashOption, abc.AutocompleteOption):
    __slots__ = ()

    def __init__(self, resolved: hikari.ResolvedOptionData, option: hikari.AutocompleteInteractionOption, /):
        self._option: hikari.AutocompleteInteractionOption
        super().__init__(resolved, option)

    @property
    def is_focused(self) -> bool:
        return self._option.is_focused


class AutocompleteContext(abc.AutocompleteContext[_ValueT]):
    """Standard implementation of an autocomplete context."""

    __slots__ = ("_client", "_focused", "_future", "_has_responded", "_interaction")

    def __init__(
        self,
        client: abc.Client,
        interaction: hikari.AutocompleteInteraction,
        *,
        future: typing.Optional[asyncio.Future[hikari.api.InteractionAutocompleteBuilder]],
    ) -> None:
        # TODO: upgrade injector client to the abc
        assert isinstance(client, injecting.InjectorClient)
        self._client = client
        self._focused: hikari.AutocompleteInteractionOption
        self._future = future
        self._has_responded = False
        self._interaction = interaction

        options = interaction.options
        print(options)
        while options and (first_option := options[0]).type in _COMMAND_OPTION_TYPES:
            options = first_option.options

        self._options: dict[str, AutocompleteOption] = {}
        if options:
            assert interaction.resolved
            for option in options:
                self._options[option.name] = AutocompleteOption(interaction.resolved, option)
                if option.is_focused:
                    self._focused = option

    @property
    def author(self) -> hikari.User:
        return self._interaction.user

    @property
    def channel_id(self) -> hikari.Snowflake:
        return self._interaction.channel_id

    @property
    def cache(self) -> typing.Optional[hikari.api.Cache]:
        return self._client.cache

    @property
    def client(self) -> abc.Client:
        return self._client

    @property
    def component(self) -> typing.Optional[abc.Component]:
        raise NotImplementedError

    @property
    def created_at(self) -> datetime.datetime:
        return self._interaction.created_at

    @property
    def events(self) -> typing.Optional[hikari.api.EventManager]:
        return self._client.events

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        return self._interaction.guild_id

    @property
    def member(self) -> typing.Optional[hikari.Member]:
        return self._interaction.member

    @property
    def server(self) -> typing.Optional[hikari.api.InteractionServer]:
        return self._client.server

    @property
    def rest(self) -> hikari.api.RESTClient:
        return self._client.rest

    @property
    def shards(self) -> typing.Optional[hikari_traits.ShardAware]:
        return self._client.shards

    @property
    def value(self) -> str:  # TODO: will this ever be float or int?
        return typing.cast(str, self._focused.value)

    @property
    def voice(self) -> typing.Optional[hikari.api.VoiceComponent]:
        return self._client.voice

    @property
    def has_responded(self) -> bool:
        return self._has_responded

    @property
    def interaction(self) -> hikari.AutocompleteInteraction:
        return self._interaction

    @property
    def options(self) -> collections.Mapping[str, AutocompleteOption]:
        return self._options.copy()

    async def fetch_channel(self) -> hikari.TextableChannel:
        return await self._interaction.fetch_channel()

    async def fetch_guild(self) -> typing.Optional[hikari.Guild]:
        return await self._interaction.fetch_guild()

    def get_channel(self) -> typing.Optional[hikari.TextableGuildChannel]:
        return self._interaction.get_channel()

    def get_guild(self) -> typing.Optional[hikari.Guild]:
        return self._interaction.get_guild()

    async def set_choices(
        self,
        choices: typing.Union[collections.Mapping[str, _ValueT], collections.Iterable[tuple[str, _ValueT]]] = ...,
        /,
        **kwargs: _ValueT,
    ) -> None:
        choices = dict(choices, **kwargs)
        if len(choices) > 25:
            raise ValueError("Cannot set more than 25 choices")

        choice_objects = [hikari.CommandChoice(name=name, value=value) for name, value in choices]

        if self._future:
            self._future.set_result(self._interaction.build_response(choice_objects))

        else:
            await self._interaction.create_response(choice_objects)
