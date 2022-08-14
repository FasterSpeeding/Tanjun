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
from __future__ import annotations

import inspect
import sys
import typing
from unittest import mock

import hikari
import pytest

import tanjun


class TestClient:
    def test_with_listener_no_provided_event(self):
        async def callback(foo) -> None:  # type: ignore
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        with pytest.raises(ValueError, match="Missing event argument annotation"):
            client.with_listener()(callback)

        add_listener_.assert_not_called()

    def test_with_listener_no_provided_event_callback_has_no_signature(self):
        with pytest.raises(ValueError, match=".+"):
            inspect.Signature.from_callable(int)

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        with pytest.raises(ValueError, match="Missing event type"):
            client.with_listener()(int)  # type: ignore

        add_listener_.assert_not_called()

    def test_with_listener_with_type_hint(self):
        async def callback(event: hikari.BanCreateEvent) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanCreateEvent, callback)

    def test_with_listener_with_type_hint_in_annotated(self):
        async def callback(event: typing.Annotated[hikari.BanCreateEvent, 123, 321]) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanCreateEvent, callback)

    def test_with_listener_with_positional_only_type_hint(self):
        async def callback(event: hikari.BanDeleteEvent, /) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanDeleteEvent, callback)

    def test_with_listener_with_var_positional_type_hint(self):
        async def callback(*event: hikari.BanEvent) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_called_once_with(hikari.BanEvent, callback)

    def test_with_listener_with_type_hint_union(self):
        async def callback(event: typing.Union[hikari.RoleEvent, typing.Literal["ok"], hikari.GuildEvent, str]) -> None:
            ...

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_has_calls(
            [
                mock.call(hikari.RoleEvent, callback),
                mock.call(hikari.GuildEvent, callback),
            ]
        )

    def test_with_listener_with_type_hint_union_nested_annotated(self):
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

        add_listener_ = mock.Mock()

        class StubClient(tanjun.Client):
            add_listener = add_listener_

        client = StubClient(mock.Mock())

        result = client.with_listener()(callback)

        assert result is callback
        add_listener_.assert_has_calls(
            [
                mock.call(hikari.RoleEvent, callback),
                mock.call(hikari.ReactionDeleteEvent, callback),
                mock.call(hikari.GuildEvent, callback),
            ]
        )

    # These tests covers syntax which was introduced in 3.10
    if sys.version_info >= (3, 10):

        def test_with_listener_with_type_hint_310_union(self):
            async def callback(event: hikari.ShardEvent | typing.Literal[""] | hikari.VoiceEvent | str) -> None:
                ...

            add_listener_ = mock.Mock()

            class StubClient(tanjun.Client):
                add_listener = add_listener_

            client = StubClient(mock.Mock())

            result = client.with_listener()(callback)

            assert result is callback
            add_listener_.assert_has_calls(
                [
                    mock.call(hikari.ShardEvent, callback),
                    mock.call(hikari.VoiceEvent, callback),
                ]
            )

        def test_with_listener_with_type_hint_310_union_nested_annotated(self):
            async def callback(
                event: typing.Annotated[
                    typing.Annotated[hikari.BanEvent | hikari.GuildEvent, 123, 321] | hikari.InviteEvent,
                    True,
                    "meow",
                ]
            ) -> None:
                ...

            add_listener_ = mock.Mock()

            class StubClient(tanjun.Client):
                add_listener = add_listener_

            client = StubClient(mock.Mock())

            result = client.with_listener()(callback)

            assert result is callback
            add_listener_.assert_has_calls(
                [
                    mock.call(hikari.BanEvent, callback),
                    mock.call(hikari.GuildEvent, callback),
                    mock.call(hikari.InviteEvent, callback),
                ]
            )
