# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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

import alluka
import hikari
from hikari import snowflakes

from tanjun import _internal
from tanjun import abc as tanjun

if typing.TYPE_CHECKING:
    import asyncio
    import datetime
    from collections import abc as collections

    _ValueT = typing.TypeVar("_ValueT", int, float, str)


_MAX_CHOICES = 25


class AutocompleteContext(alluka.BasicContext, tanjun.AutocompleteContext):
    """Standard implementation of an autocomplete context."""

    __slots__ = ("_command_name", "_focused", "_future", "_has_responded", "_interaction", "_options", "_tanjun_client")

    def __init__(
        self,
        client: tanjun.Client,
        interaction: hikari.AutocompleteInteraction,
        *,
        future: asyncio.Future[hikari.api.InteractionAutocompleteBuilder] | None = None,
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
        super().__init__(client.injector)
        self._tanjun_client = client
        self._future = future
        self._has_responded = False
        self._interaction = interaction

        focused: hikari.AutocompleteInteractionOption | None = None
        self._options: dict[str, hikari.AutocompleteInteractionOption] = {}
        command_name, options = _internal.flatten_options(interaction.command_name, interaction.options)
        for option in options:
            self._options[option.name] = option
            if option.is_focused:
                focused = self._options[option.name]

        assert focused is not None
        self._command_name = command_name
        self._focused = focused
        (
            self._set_type_special_case(AutocompleteContext, self)._set_type_special_case(  # noqa: SLF001
                tanjun.AutocompleteContext, self
            )
        )

    @property
    def author(self) -> hikari.User:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.user

    @property
    def channel_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.channel_id

    @property
    def cache(self) -> hikari.api.Cache | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client.cache

    @property
    def client(self) -> tanjun.Client:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client

    @property
    def triggering_name(self) -> str:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._command_name

    @property
    def created_at(self) -> datetime.datetime:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.created_at

    @property
    def events(self) -> hikari.api.EventManager | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client.events

    @property
    def focused(self) -> hikari.AutocompleteInteractionOption:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._focused

    @property
    def guild_id(self) -> hikari.Snowflake | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.guild_id

    @property
    def member(self) -> hikari.Member | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.member

    @property
    def server(self) -> hikari.api.InteractionServer | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client.server

    @property
    def rest(self) -> hikari.api.RESTClient:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client.rest

    @property
    def shard(self) -> hikari.api.GatewayShard | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        if not self._tanjun_client.shards:
            return None

        if self.guild_id is not None:
            shard_id = snowflakes.calculate_shard_id(self._tanjun_client.shards, self.guild_id)

        else:
            shard_id = 0

        return self._tanjun_client.shards.shards[shard_id]

    @property
    def shards(self) -> hikari.ShardAware | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client.shards

    @property
    def voice(self) -> hikari.api.VoiceComponent | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._tanjun_client.voice

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

    async def fetch_guild(self) -> hikari.Guild | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return await self._interaction.fetch_guild()

    def get_channel(self) -> hikari.TextableGuildChannel | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.get_channel()

    def get_guild(self) -> hikari.Guild | None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        return self._interaction.get_guild()

    async def set_choices(
        self,
        choices: collections.Mapping[str, _ValueT] | collections.Iterable[tuple[str, _ValueT]] = (),
        /,
        **kwargs: _ValueT,
    ) -> None:
        # <<inherited docstring from tanjun.abc.AutocompleteContext>>.
        if self._has_responded:
            error_message = "Cannot set choices after responding"
            raise RuntimeError(error_message)

        choices = dict(choices, **kwargs)
        if len(choices) > _MAX_CHOICES:
            error_message = f"Cannot set more than {_MAX_CHOICES} choices"
            raise ValueError(error_message)

        self._has_responded = True
        choice_objects = [
            hikari.impl.AutocompleteChoiceBuilder(name=name, value=value) for name, value in choices.items()
        ]

        if self._future:
            self._future.set_result(self._interaction.build_response(choice_objects))

        else:
            await self._interaction.create_response(choice_objects)
