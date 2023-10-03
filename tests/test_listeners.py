import inspect
import sys
import typing

import hikari
import mock
import pytest

import tanjun


class TestEventListener:
    def test_init(self):
        async def callback(foo) -> None:  # type: ignore
            ...

        event_listener = tanjun.listeners.EventListener(callback, hikari.ShardEvent, hikari.GuildEvent)

        assert event_listener.callback == callback
        assert event_listener.event_types == (hikari.ShardEvent, hikari.GuildEvent)

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

    def test_callback_property(self):
        mock_callback = mock.Mock()
        event_listener = tanjun.listeners.EventListener(mock_callback, hikari.GuildEvent)

        assert event_listener.callback is mock_callback

    def test_event_types_property(self):
        mock_callback = mock.Mock()
        event_listener = tanjun.listeners.EventListener(mock_callback, hikari.GuildEvent, hikari.ShardEvent)

        assert event_listener.event_types == (hikari.GuildEvent, hikari.ShardEvent)

    @pytest.mark.asyncio
    async def test__call__(self):
        mock_callback = mock.AsyncMock()

        event_listener = tanjun.listeners.EventListener(mock_callback, hikari.ShardEvent)
        await event_listener("testing", a="test")

        mock_callback.assert_awaited_once_with("testing", a="test")
