# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
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

# pyright: reportIncompatibleMethodOverride=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

import datetime
import typing
import urllib.parse
from unittest import mock

import hikari
import pytest

import tanjun


class TestBaseConverter:
    @pytest.mark.asyncio()
    async def test___call__(self):
        convert_ = mock.AsyncMock()

        class StubConverter(tanjun.conversion.BaseConverter[typing.Any]):
            cache_components = mock.Mock()
            intents = mock.Mock()
            requires_cache = mock.Mock()
            convert = convert_

        mock_ctx = mock.Mock()
        converter = StubConverter()

        result = await converter("foo", mock_ctx)

        assert result is convert_.return_value
        convert_.assert_called_once_with(mock_ctx, "foo")

    @pytest.mark.skip(reason="Not finalised yet")
    def test_check_client(self):
        ...

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (tanjun.to_channel, hikari.CacheComponents.GUILD_CHANNELS),
            (tanjun.to_emoji, hikari.CacheComponents.EMOJIS),
            (tanjun.to_guild, hikari.CacheComponents.GUILDS),
            (tanjun.to_invite, hikari.CacheComponents.INVITES),
            (tanjun.to_invite_with_metadata, hikari.CacheComponents.INVITES),
            (tanjun.to_member, hikari.CacheComponents.MEMBERS),
            (tanjun.to_presence, hikari.CacheComponents.PRESENCES),
            (tanjun.to_role, hikari.CacheComponents.ROLES),
            (tanjun.to_user, hikari.CacheComponents.NONE),
            (tanjun.to_voice_state, hikari.CacheComponents.VOICE_STATES),
        ],
    )
    def test_cache_components_property(
        self, obj: tanjun.conversion.BaseConverter[typing.Any], expected: hikari.CacheComponents
    ):
        assert obj.cache_components == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (tanjun.to_channel, hikari.Intents.GUILDS),
            (tanjun.to_emoji, hikari.Intents.GUILDS | hikari.Intents.GUILD_EMOJIS),
            (tanjun.to_guild, hikari.Intents.GUILDS),
            (tanjun.to_invite, hikari.Intents.GUILD_INVITES),
            (tanjun.to_invite_with_metadata, hikari.Intents.GUILD_INVITES),
            (tanjun.to_member, hikari.Intents.GUILDS | hikari.Intents.GUILD_MEMBERS),
            (tanjun.to_presence, hikari.Intents.GUILDS | hikari.Intents.GUILD_PRESENCES),
            (tanjun.to_role, hikari.Intents.GUILDS),
            (tanjun.to_user, hikari.Intents.GUILDS | hikari.Intents.GUILD_MEMBERS),
            (tanjun.to_voice_state, hikari.Intents.GUILDS | hikari.Intents.GUILD_VOICE_STATES),
        ],
    )
    def test_intents_property(self, obj: tanjun.conversion.BaseConverter[typing.Any], expected: hikari.Intents):
        assert obj.intents == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (tanjun.to_channel, False),
            (tanjun.to_emoji, False),
            (tanjun.to_guild, False),
            (tanjun.to_invite, False),
            (tanjun.to_invite_with_metadata, True),
            (tanjun.to_member, False),
            (tanjun.to_presence, True),
            (tanjun.to_role, False),
            (tanjun.to_user, False),
            (tanjun.to_voice_state, True),
        ],
    )
    def test_requires_cache_property(self, obj: tanjun.conversion.BaseConverter[typing.Any], expected: bool):
        assert obj.requires_cache is expected


class TestInjectableConverter:
    @pytest.mark.asyncio()
    async def test___call___when_converter(self):
        convert_ = mock.AsyncMock()

        class StubConverter(tanjun.conversion.BaseConverter[typing.Any]):
            cache_components = mock.Mock()
            intents = mock.Mock()
            requires_cache = mock.Mock()
            convert = convert_

        mock_ctx = mock.Mock()
        callback = StubConverter()
        converter = tanjun.conversion.InjectableConverter(callback)

        result = await converter(mock_ctx, "123")

        assert result is convert_.return_value
        convert_.assert_awaited_once_with(mock_ctx, "123")

    @pytest.mark.asyncio()
    async def test___call__(self):
        mock_callback = mock.Mock()
        mock_ctx = mock.Mock()

        with mock.patch.object(
            tanjun.injecting, "CallbackDescriptor", return_value=mock.AsyncMock()
        ) as CallbackDescriptor:
            converter = tanjun.conversion.InjectableConverter(mock_callback)

        CallbackDescriptor.assert_called_once_with(mock_callback)

        result = await converter(mock_ctx, "123")

        assert result is CallbackDescriptor.return_value.resolve_with_command_context.return_value
        CallbackDescriptor.return_value.resolve_with_command_context.assert_awaited_once_with(mock_ctx, "123")


class TestChannelConverter:
    @pytest.mark.asyncio()
    async def test_convert_when_cached(self):
        mock_context = mock.Mock()

        result = await tanjun.to_channel.convert(mock_context, "123321")

        assert result is mock_context.cache.get_guild_channel.return_value
        mock_context.cache.get_guild_channel.assert_called_once_with(123321)
        mock_context.rest.fetch_channel.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None

        result = await tanjun.to_channel.convert(mock_context, "<#12222>")

        assert result is mock_context.rest.fetch_channel.return_value
        mock_context.cache.get_guild_channel.assert_called_once_with(12222)
        mock_context.rest.fetch_channel.assert_awaited_once_with(12222)

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache = None

        result = await tanjun.to_channel.convert(mock_context, 222)

        assert result is mock_context.rest.fetch_channel.return_value
        mock_context.rest.fetch_channel.assert_awaited_once_with(222)

    @pytest.mark.asyncio()
    async def test_convert_when_not_found(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild_channel.return_value = None
        mock_context.rest.fetch_channel.side_effect = hikari.NotFoundError(url="gey", headers={}, raw_body="")

        with pytest.raises(ValueError, match="Couldn't find channel"):
            await tanjun.to_channel.convert(mock_context, "<#12222>")

        mock_context.cache.get_guild_channel.assert_called_once_with(12222)
        mock_context.rest.fetch_channel.assert_awaited_once_with(12222)


class TestEmojiConverter:
    @pytest.mark.asyncio()
    async def test_convert_when_cached(self):
        mock_context = mock.Mock()

        result = await tanjun.to_emoji.convert(mock_context, "6655")

        assert result is mock_context.cache.get_emoji.return_value
        mock_context.cache.get_emoji.assert_called_once_with(6655)
        mock_context.rest.fetch_emoji.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached_and_guild_bound(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_emoji.return_value = None

        result = await tanjun.to_emoji.convert(mock_context, "<:name:54123>")

        assert result is mock_context.rest.fetch_emoji.return_value
        mock_context.cache.get_emoji.assert_called_once_with(54123)
        mock_context.rest.fetch_emoji.assert_awaited_once_with(mock_context.guild_id, 54123)

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache = None

        result = await tanjun.to_emoji.convert(mock_context, "<a:name:7623421>")

        assert result is mock_context.rest.fetch_emoji.return_value
        mock_context.rest.fetch_emoji.assert_awaited_once_with(mock_context.guild_id, 7623421)

    @pytest.mark.asyncio()
    async def test_convert_when_not_found(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_emoji.return_value = None
        mock_context.rest.fetch_emoji.side_effect = hikari.NotFoundError(url="grey", headers={}, raw_body="")

        with pytest.raises(ValueError, match="Couldn't find emoji"):
            await tanjun.to_emoji.convert(mock_context, 123321)

        mock_context.cache.get_emoji.assert_called_once_with(123321)
        mock_context.rest.fetch_emoji.assert_awaited_once_with(mock_context.guild_id, 123321)

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached_and_not_guild_bound(self):
        mock_context = mock.Mock(guild_id=None)
        mock_context.cache.get_emoji.return_value = None

        with pytest.raises(ValueError, match="Couldn't find emoji"):
            await tanjun.to_emoji.convert(mock_context, 123321)

        mock_context.cache.get_emoji.assert_called_once_with(123321)
        mock_context.rest.fetch_emoji.assert_not_called()


class TestGuildConverter:
    @pytest.mark.asyncio()
    async def test_convert_when_cached(self):
        mock_context = mock.Mock()

        result = await tanjun.to_guild.convert(mock_context, "1234")

        assert result is mock_context.cache.get_guild.return_value
        mock_context.cache.get_guild.assert_called_once_with(1234)
        mock_context.rest.fetch_guild.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild.return_value = None

        result = await tanjun.to_guild.convert(mock_context, 54234)

        assert result is mock_context.rest.fetch_guild.return_value
        mock_context.cache.get_guild.assert_called_once_with(54234)
        mock_context.rest.fetch_guild.assert_awaited_once_with(54234)

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache = None

        result = await tanjun.to_guild.convert(mock_context, 2222)

        assert result is mock_context.rest.fetch_guild.return_value
        mock_context.rest.fetch_guild.assert_awaited_once_with(2222)

    @pytest.mark.asyncio()
    async def test_convert_when_not_found(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_guild.return_value = None
        mock_context.rest.fetch_guild.side_effect = hikari.NotFoundError(url="grey", headers={}, raw_body="")

        with pytest.raises(ValueError, match="Couldn't find guild"):
            await tanjun.to_guild.convert(mock_context, 54234)

        mock_context.cache.get_guild.assert_called_once_with(54234)
        mock_context.rest.fetch_guild.assert_awaited_once_with(54234)


class TestInviteConverter:
    @pytest.mark.asyncio()
    async def test_convert_when_cached(self):
        mock_context = mock.Mock()

        result = await tanjun.to_invite.convert(mock_context, "asdbasd")

        assert result is mock_context.cache.get_invite.return_value
        mock_context.cache.get_invite.assert_called_once_with("asdbasd")
        mock_context.rest.fetch_invite.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_str(self):
        with pytest.raises(ValueError, match="`123` is not a valid invite code"):
            await tanjun.to_invite.convert(mock.Mock(), 123)

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_invite.return_value = None

        result = await tanjun.to_invite.convert(mock_context, "fffff")

        assert result is mock_context.rest.fetch_invite.return_value
        mock_context.cache.get_invite.assert_called_once_with("fffff")
        mock_context.rest.fetch_invite.assert_awaited_once_with("fffff")

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache = None

        result = await tanjun.to_invite.convert(mock_context, "123321")

        assert result is mock_context.rest.fetch_invite.return_value
        mock_context.rest.fetch_invite.assert_awaited_once_with("123321")

    @pytest.mark.asyncio()
    async def test_convert_when_not_found(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_invite.return_value = None
        mock_context.rest.fetch_invite.side_effect = hikari.NotFoundError(url="grey", headers={}, raw_body="")

        with pytest.raises(ValueError, match="Couldn't find invite"):
            await tanjun.to_invite.convert(mock_context, "sasdasd")

        mock_context.cache.get_invite.assert_called_once_with("sasdasd")
        mock_context.rest.fetch_invite.assert_awaited_once_with("sasdasd")


class TestInviteWithMetadataConverter:
    @pytest.mark.asyncio()
    async def test_convert(self):
        mock_context = mock.Mock()

        result = await tanjun.to_invite_with_metadata.convert(mock_context, "asdbasd")

        assert result is mock_context.cache.get_invite.return_value
        mock_context.cache.get_invite.assert_called_once_with("asdbasd")

    @pytest.mark.asyncio()
    async def test_convert_when_not_str(self):
        with pytest.raises(ValueError, match="`432123` is not a valid invite code"):
            await tanjun.to_invite_with_metadata.convert(mock.Mock(), 432123)

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock()
        mock_context.cache.get_invite.return_value = None

        with pytest.raises(ValueError, match="Couldn't find invite"):
            await tanjun.to_invite_with_metadata.convert(mock_context, "dsds")

        mock_context.cache.get_invite.assert_called_once_with("dsds")

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(cache=None)

        with pytest.raises(ValueError, match="Couldn't find invite"):
            await tanjun.to_invite_with_metadata.convert(mock_context, "asdbasd")


class TestMemberConverter:
    @pytest.mark.asyncio()
    async def test_convert_when_in_a_dm(self):
        mock_context = mock.Mock(guild_id=None)

        with pytest.raises(ValueError, match="Cannot get a member from a DM channel"):
            await tanjun.to_member.convert(mock_context, 123)

        mock_context.cache.get_member.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()
        mock_context.rest.search_members.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_id_falls_back_to_lookup_by_name(self):
        mock_context = mock.AsyncMock()
        mock_result = mock.Mock()
        mock_context.rest.search_members.return_value = [mock_result]

        result = await tanjun.to_member.convert(mock_context, "asdbasd")

        assert result is mock_result
        mock_context.cache.get_member.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()
        mock_context.rest.search_members.assert_awaited_once_with(mock_context.guild_id, "asdbasd")

    @pytest.mark.asyncio()
    async def test_convert_when_not_id_falls_back_to_lookup_by_name_returns_nothing(self):
        mock_context = mock.AsyncMock()
        mock_context.rest.search_members.return_value = []

        with pytest.raises(ValueError, match="Couldn't find member in this guild"):
            await tanjun.to_member.convert(mock_context, "asdbasd")

        mock_context.cache.get_member.assert_not_called()
        mock_context.rest.fetch_member.assert_not_called()
        mock_context.rest.search_members.assert_awaited_once_with(mock_context.guild_id, "asdbasd")

    @pytest.mark.asyncio()
    async def test_convert_when_cached(self):
        mock_context = mock.Mock()

        result = await tanjun.to_member.convert(mock_context, "<@54123>")

        assert result is mock_context.cache.get_member.return_value
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, 54123)
        mock_context.rest.fetch_member.assert_not_called()
        mock_context.rest.search_members.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_member.return_value = None

        result = await tanjun.to_member.convert(mock_context, "5123123")

        assert result is mock_context.rest.fetch_member.return_value
        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, 5123123)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, 5123123)
        mock_context.rest.search_members.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache = None

        result = await tanjun.to_member.convert(mock_context, "5123123")

        assert result is mock_context.rest.fetch_member.return_value
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, 5123123)
        mock_context.rest.search_members.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_found(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_member.return_value = None
        mock_context.rest.fetch_member.side_effect = hikari.NotFoundError(url="grey", headers={}, raw_body="")

        with pytest.raises(ValueError, match="Couldn't find member in this guild"):
            await tanjun.to_member.convert(mock_context, "5123123")

        mock_context.cache.get_member.assert_called_once_with(mock_context.guild_id, 5123123)
        mock_context.rest.fetch_member.assert_awaited_once_with(mock_context.guild_id, 5123123)
        mock_context.rest.search_members.assert_not_called()


class TestPresenceConverter:
    @pytest.mark.asyncio()
    async def test_convert(self):
        mock_context = mock.Mock()

        result = await tanjun.to_presence.convert(mock_context, "<@543123>")

        assert result is mock_context.cache.get_presence.return_value
        mock_context.cache.get_presence.assert_called_once_with(mock_context.guild_id, 543123)

    @pytest.mark.asyncio()
    async def test_convert_when_in_a_dm(self):
        with pytest.raises(ValueError, match="Cannot get a presence from a DM channel"):
            await tanjun.to_presence.convert(mock.Mock(guild_id=None), 123)

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock()
        mock_context.cache.get_presence.return_value = None

        with pytest.raises(ValueError, match="Couldn't find presence in current guild"):
            await tanjun.to_presence.convert(mock_context, "<@543123>")

        mock_context.cache.get_presence.assert_called_once_with(mock_context.guild_id, 543123)

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock()
        mock_context.cache = None

        with pytest.raises(ValueError, match="Couldn't find presence in current guild"):
            await tanjun.to_presence.convert(mock_context, "<@543123>")


class TestUserConverter:
    @pytest.mark.asyncio()
    async def test_convert_when_cached(self):
        mock_context = mock.Mock()

        result = await tanjun.to_user.convert(mock_context, "123")

        assert result is mock_context.cache.get_user.return_value
        mock_context.cache.get_user.assert_called_once_with(123)
        mock_context.rest.fetch_user.assert_not_called()

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_user.return_value = None

        result = await tanjun.to_user.convert(mock_context, "55")

        assert result is mock_context.rest.fetch_user.return_value
        mock_context.cache.get_user.assert_called_once_with(55)
        mock_context.rest.fetch_user.assert_awaited_once_with(55)

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache = None

        result = await tanjun.to_user.convert(mock_context, "12343")

        assert result is mock_context.rest.fetch_user.return_value
        mock_context.rest.fetch_user.assert_awaited_once_with(12343)

    @pytest.mark.asyncio()
    async def test_convert_when_not_found(self):
        mock_context = mock.Mock(rest=mock.AsyncMock())
        mock_context.cache.get_user.return_value = None
        mock_context.rest.fetch_user.side_effect = hikari.NotFoundError(url="grey", headers={}, raw_body="")

        with pytest.raises(ValueError, match="Couldn't find user"):
            await tanjun.to_user.convert(mock_context, "55")

        mock_context.cache.get_user.assert_called_once_with(55)
        mock_context.rest.fetch_user.assert_awaited_once_with(55)


class TestVoiceStateConverter:
    @pytest.mark.asyncio()
    async def test_convert(self):
        mock_context = mock.Mock()

        result = await tanjun.to_voice_state.convert(mock_context, "<@453123>")

        assert result is mock_context.cache.get_voice_state.return_value
        mock_context.cache.get_voice_state.assert_called_once_with(mock_context.guild_id, 453123)

    @pytest.mark.asyncio()
    async def test_convert_when_not_cached(self):
        mock_context = mock.Mock()
        mock_context.cache.get_voice_state.return_value = None

        with pytest.raises(ValueError, match="Voice state couldn't be found for current guild"):
            await tanjun.to_voice_state.convert(mock_context, 54123)

        mock_context.cache.get_voice_state.assert_called_once_with(mock_context.guild_id, 54123)

    @pytest.mark.asyncio()
    async def test_convert_when_cacheless(self):
        mock_context = mock.Mock(cache=None)

        with pytest.raises(ValueError, match="Voice state couldn't be found for current guild"):
            await tanjun.to_voice_state.convert(mock_context, 65234)

    @pytest.mark.asyncio()
    async def test_convert_when_in_a_dm(self):
        mock_context = mock.Mock(guild_id=None)

        with pytest.raises(ValueError, match="Cannot get a voice state from a DM channel"):
            await tanjun.to_voice_state.convert(mock_context, 65234)


TOO_LARGE_SF = hikari.Snowflake.max() + 1
TOO_SMALL_SF = hikari.Snowflake.min() - 50


@pytest.mark.parametrize(
    ("value", "result"),
    [
        (123, hikari.Snowflake(123)),
        ("54123", 54123),
        ("<@123321>", 123321),
        ("<@!55555>", 55555),
        ("<#41223>", 41223),
        ("<@&11111>", 11111),
        ("<:gay:543123>", 543123),
        ("<a:yagami:22222>", 22222),
    ],
)
def test_parse_snowflake(value: typing.Union[str, int], result: int):
    assert tanjun.parse_snowflake(value) == result


@pytest.mark.parametrize(
    "value",
    [
        123.321,
        TOO_LARGE_SF,
        TOO_SMALL_SF,
        str(TOO_SMALL_SF),
        str(TOO_LARGE_SF),
        f"<@{TOO_LARGE_SF}>",
        f"<@{TOO_SMALL_SF}",
        "abba",
        "<@>",
        "<@!>",
        "<#>",
        "<@&>",
        "<:sdaqwe:>",
        "<a:123321:>",
        "",
    ],
)
def test_parse_snowflake_with_invalid_value(value: typing.Union[float, int, str]):
    with pytest.raises(ValueError, match="abcas"):
        tanjun.parse_snowflake(value, message="abcas")


def test_search_snowflakes():
    string = (
        f"123 <@!> {TOO_LARGE_SF} <@54123><@!56123><> 123.312 <@> slurp <:shabat>"
        f" <#123321>, sleeper <a:32123> {TOO_SMALL_SF} <:gaaa:431123> <a:344213:43123>"
    )

    assert set(tanjun.search_snowflakes(string)) == {123, 54123, 56123, 123321, 431123, 43123}


@pytest.mark.parametrize(("value", "result"), [("43123", 43123), (1233211, 1233211), ("<#12333>", 12333)])
def test_parse_channel_id(value: typing.Union[str, int], result: int):
    assert tanjun.parse_channel_id(value) == result


@pytest.mark.parametrize(
    "value",
    [
        "<@123>",
        "<!@43123>",
        "<>",
        "<#123",
        "#542>",
        "<123312>",
        "<@&3212>",
        "<:NAME:43123>",
        "<a:NAME:453123>",
        f"<#{TOO_LARGE_SF}>",
        f"<#{TOO_SMALL_SF}>",
        TOO_LARGE_SF,
        TOO_SMALL_SF,
        123.321,
        str(TOO_LARGE_SF),
        str(TOO_SMALL_SF),
    ],
)
def test_parse_channel_id_with_invalid_data(value: typing.Union[str, int, float]):
    with pytest.raises(ValueError, match="a message"):
        tanjun.parse_channel_id(value, message="a message")


def test_search_channel_ids():
    result = tanjun.search_channel_ids(
        f"65423 <#> <> {TOO_LARGE_SF} <#123321><#43123> {TOO_SMALL_SF} 54123 <@1> <@13> <@&32> <a:123:342> <:123:32>"
    )

    assert set(result) == {65423, 123321, 43123, 54123}


@pytest.mark.parametrize(
    ("value", "result"), [("43123", 43123), (1233211, 1233211), ("<a:Name:12333>", 12333), ("<:name:32123>", 32123)]
)
def test_parse_emoji_id(value: typing.Union[str, int], result: int):
    assert tanjun.parse_emoji_id(value) == result


@pytest.mark.parametrize(
    "value",
    [
        TOO_SMALL_SF,
        TOO_LARGE_SF,
        str(TOO_SMALL_SF),
        str(TOO_LARGE_SF),
        f"<a:name:{TOO_LARGE_SF}>",
        f"<:name:{TOO_SMALL_SF}>",
        "",
        "<>",
        "<:sda:3123",
        "a:fdasd:123123>" "<@&123312",
        "<@123321>",
        "<@!43123>",
    ],
)
def test_parse_emoji_id_with_invalid_values(value: typing.Union[str, int, float]):
    with pytest.raises(ValueError, match="a messages"):
        tanjun.parse_emoji_id(value, message="a messages")


def test_search_emoji_ids():
    string = (
        f"<a:{TOO_LARGE_SF}> <:sksks:67234><a:name:32123> 432 <:gaga:4543123> 4231.123 "
        f"<a:{TOO_SMALL_SF}> <@1> <@!2> <@&123312> <#123321>"
    )

    result = tanjun.search_emoji_ids(string)

    assert set(result) == {67234, 32123, 4543123, 432}


@pytest.mark.parametrize(("value", "result"), [("43123", 43123), (1233211, 1233211), ("<@&1234321>", 1234321)])
def test_parse_role_id(value: typing.Union[str, int], result: int):
    assert tanjun.parse_role_id(value) == result


@pytest.mark.parametrize(
    "value",
    [
        TOO_SMALL_SF,
        TOO_LARGE_SF,
        str(TOO_SMALL_SF),
        str(TOO_LARGE_SF),
        f"<@&{TOO_LARGE_SF}>",
        f"<@&{TOO_SMALL_SF}",
        "",
        "<@&>",
        "123321@&>",
        "<@&123",
        "<@!123321>",
        "<@54321>",
        "<#632143>",
        "<:name:32123>",
        "<a:name:432123>",
    ],
)
def test_parse_role_id_with_invalid_values(value: typing.Union[float, int, str]):
    with pytest.raises(ValueError, match="a messaged"):
        tanjun.parse_role_id(value, message="a messaged")


def test_search_role_ids():
    result = tanjun.search_role_ids(
        f"<@&{TOO_SMALL_SF}><@&123321><@&12222> 123 342 <#123> <@5623> <a:s:123> <:vs:123> <@&444> <@&{TOO_SMALL_SF}"
    )

    assert set(result) == {123321, 12222, 123, 342, 444}


@pytest.mark.parametrize(
    ("value", "expected"), [("43123", 43123), ("<@!33333>", 33333), (1233211, 1233211), ("<@1234321>", 1234321)]
)
def test_parse_user_id(value: typing.Union[int, str], expected: int):
    assert tanjun.parse_user_id(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        TOO_SMALL_SF,
        TOO_LARGE_SF,
        str(TOO_SMALL_SF),
        str(TOO_LARGE_SF),
        f"<#{TOO_LARGE_SF}>",
        f"<#{TOO_SMALL_SF}",
        "",
        "<@>",
        "<@!>",
        "<@!123321",
        "@342123>",
        "<#43123>",
        "<@&123321>",
        "<a:oslls:123321>",
        "<:fdas:123>",
    ],
)
def test_parse_user_id_with_invalid_values(value: typing.Union[int, str]):
    with pytest.raises(ValueError, match="a"):
        tanjun.parse_user_id(value, message="a")


def test_search_user_ids():
    string = f"<@{TOO_LARGE_SF}><@123321><@!6743234> 132321 <#123><@&3541234> 3123 <:a:3> <a:v:3> <@65123>"

    result = tanjun.search_user_ids(string)

    assert set(result) == {123321, 6743234, 132321, 3123, 65123}


def test_defragment_url():
    result = tanjun.conversion.defragment_url("https://s//s/s/s/s/d#b")

    assert result == urllib.parse.DefragResult(url="https://s//s/s/s/s/d", fragment="b")  # type: ignore


def test_defragment_url_when_wrapped():
    result = tanjun.conversion.defragment_url("<https://s//s/s/s/s/b#a>")

    assert result == urllib.parse.DefragResult(url="https://s//s/s/s/s/b", fragment="a")  # type: ignore


def test_parse_url():
    result = tanjun.conversion.parse_url("https:/s//s/s/s/s/q")

    assert result == urllib.parse.ParseResult(
        scheme="https", netloc="", path="/s//s/s/s/s/q", params="", query="", fragment=""
    )


def test_parse_url_when_wrapped():
    result = tanjun.conversion.parse_url("<https:/s//s/s/s/s/a>")

    assert result == urllib.parse.ParseResult(
        scheme="https", netloc="", path="/s//s/s/s/s/a", params="", query="", fragment=""
    )


def test_split_url():
    result = tanjun.conversion.split_url("https:/s//s/s/s/s/e")

    assert result == urllib.parse.SplitResult(scheme="https", netloc="", path="/s//s/s/s/s/e", query="", fragment="")


def test_split_url_when_wrapped():
    result = tanjun.conversion.split_url("<https:/s//s/s/s/s/s>")

    assert result == urllib.parse.SplitResult(scheme="https", netloc="", path="/s//s/s/s/s/s", query="", fragment="")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("<t:123321123>", datetime.datetime(1973, 11, 28, 7, 52, 3, tzinfo=datetime.timezone.utc)),
        ("<t:3232133:t>", datetime.datetime(1970, 2, 7, 9, 48, 53, tzinfo=datetime.timezone.utc)),
    ],
)
def test_to_datetime(value: str, expected: datetime.datetime):
    assert tanjun.to_datetime(value) == expected


@pytest.mark.parametrize("value", ["a", "<:123312:f>", "<t::a>", "t:123312:f", "<t:123312:f", "<t:123312:>"])
def test_to_datetime_with_invalid_values(value: str):
    with pytest.raises(ValueError, match="Not a valid datetime"):
        tanjun.to_datetime(value)


def test_from_datetime():
    date = datetime.datetime(2021, 9, 15, 14, 16, 18, 829252, tzinfo=datetime.timezone.utc)

    result = tanjun.from_datetime(date, style="d")

    assert result == "<t:1631715379:d>"


def test_from_datetime_with_default_style():
    date = datetime.datetime(2021, 9, 15, 14, 16, 18, 829252, tzinfo=datetime.timezone.utc)

    result = tanjun.from_datetime(date)

    assert result == "<t:1631715379:f>"


def test_from_datetime_for_naive_datetime():
    date = datetime.datetime.utcnow()

    with pytest.raises(ValueError, match="Cannot convert naive datetimes, please specify a timezone."):
        tanjun.from_datetime(date)


def test_from_datetime_for_invalid_style():
    date = datetime.datetime.now(tz=datetime.timezone.utc)

    with pytest.raises(ValueError, match="Invalid style: granddad"):
        tanjun.from_datetime(date, style="granddad")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("n", False),
        ("N", False),
        ("no", False),
        ("No", False),
        ("f", False),
        ("F", False),
        ("false", False),
        ("False", False),
        ("off", False),
        ("Off", False),
        ("0", False),
        ("y", True),
        ("Y", True),
        ("yes", True),
        ("Yes", True),
        ("t", True),
        ("T", True),
        ("true", True),
        ("True", True),
        ("on", True),
        ("On", True),
        ("1", True),
    ],
)
def test_to_bool(value: str, expected: bool):
    assert tanjun.to_bool(value) is expected


@pytest.mark.parametrize("value", ["Yee", "ye", "nope", "yankee", "", "doodle", "10", "yesno", "noyes"])
def test_to_bool_with_invalid_input(value: str):
    with pytest.raises(ValueError, match=f"Invalid bool value `{value.lower()}`"):
        tanjun.to_bool(value)


def test_to_color():
    with mock.patch.object(hikari.Color, "of") as of:
        result = tanjun.to_color(123)

        assert result is of.return_value
        of.assert_called_once_with(123)


def test_to_color_when_str():
    with mock.patch.object(hikari.Color, "of") as of:
        result = tanjun.to_color("54 23 12")

        assert result is of.return_value
        of.assert_called_once_with(54, 23, 12)


def test_to_color_when_str_of_3_digits():
    with mock.patch.object(hikari.Color, "of") as of:
        result = tanjun.to_color("0x333")

        assert result is of.return_value
        of.assert_called_once_with("0x333")


@pytest.mark.skip(reason="TODO")
def test_override_type():
    ...
