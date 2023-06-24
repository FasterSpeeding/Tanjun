# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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

import inspect
import sys
import typing

import hikari
import pytest

import tanjun


class TestEventListener:
    def test_init_with_listener_no_provided_event(self):
        async def callback(foo) -> None:  # type: ignore
            ...

        with pytest.raises(ValueError, match="Missing event argument annotation"):
            tanjun.listeners.EventListener(callback)  # pyright: ignore[reportUnknownArgumentType]

    def test_init_with_listener_no_provided_event_callback_has_no_signature(self):
        with pytest.raises(ValueError, match=".+"):
            inspect.Signature.from_callable(int)

        with pytest.raises(ValueError, match="Missing event type"):
            tanjun.listeners.EventListener(int)  # type: ignore

    def test_init_with_listener_with_type_hint(self):
        async def callback(event: hikari.BanCreateEvent) -> None:
            ...

        event_listener = tanjun.listeners.EventListener(callback)

        assert event_listener.callback is callback
        assert event_listener.event_types == [hikari.BanCreateEvent]

    def test_init_with_listener_with_type_hint_in_annotated(self):
        async def callback(event: typing.Annotated[hikari.BanCreateEvent, 123, 321]) -> None:
            ...

        event_listener = tanjun.listeners.EventListener(callback)

        assert event_listener.callback is callback
        assert event_listener.event_types == [hikari.BanCreateEvent]

    def test_init_with_listener_with_positional_only_type_hint(self):
        async def callback(event: hikari.BanDeleteEvent, /) -> None:
            ...

        event_listener = tanjun.listeners.EventListener(callback)

        assert event_listener.callback is callback
        assert event_listener.event_types == [hikari.BanDeleteEvent]

    def test_init_with_listener_with_var_positional_type_hint(self):
        async def callback(*event: hikari.BanEvent) -> None:
            ...

        event_listener = tanjun.listeners.EventListener(callback)

        assert event_listener.callback is callback
        assert event_listener.event_types == [hikari.BanEvent]

    def test_init_with_listener_with_type_hint_union(self):
        async def callback(event: typing.Union[hikari.RoleEvent, typing.Literal["ok"], hikari.GuildEvent, str]) -> None:
            ...

        event_listener = tanjun.listeners.EventListener(callback)

        assert event_listener.callback is callback
        assert event_listener.event_types == [hikari.RoleEvent, hikari.GuildEvent]

    def test_init_with_listener_with_type_hint_union_nested_annotated(self):
        async def callback(
            event: typing.Annotated[
                typing.Union[
                    typing.Annotated[typing.Union[hikari.RoleEvent, hikari.ReactionDeleteEvent], 123, 321],
                    hikari.GuildEvent,
                ],
                True,
                "meow",
            ]
        ) -> None:
            ...

        event_listener = tanjun.listeners.EventListener(callback)

        assert event_listener.callback is callback
        assert event_listener.event_types == [hikari.RoleEvent, hikari.ReactionDeleteEvent, hikari.GuildEvent]

    # These tests covers syntax which was introduced in 3.10
    if sys.version_info >= (3, 10):

        def test_init_with_listener_with_type_hint_310_union(self):
            async def callback(event: hikari.ShardEvent | typing.Literal[""] | hikari.VoiceEvent | str) -> None:
                ...

            event_listener = tanjun.listeners.EventListener(callback)

            assert event_listener.callback is callback
            assert event_listener.event_types == [hikari.ShardEvent, hikari.VoiceEvent]

        def test_init_with_listener_with_type_hint_310_union_nested_annotated(self):
            async def callback(
                event: typing.Annotated[
                    typing.Annotated[hikari.BanEvent | hikari.GuildEvent, 123, 321] | hikari.InviteEvent, True, "meow"
                ]
            ) -> None:
                ...

            event_listener = tanjun.listeners.EventListener(callback)

            assert event_listener.callback is callback
            assert event_listener.event_types == [hikari.BanEvent, hikari.GuildEvent, hikari.InviteEvent]
