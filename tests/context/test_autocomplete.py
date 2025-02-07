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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

from unittest import mock

import hikari
import pytest
from hikari import traits

import tanjun


class TestAutocompleteContext:
    @pytest.fixture
    def mock_client(self) -> tanjun.Client:
        return mock.AsyncMock(tanjun.Client)

    @pytest.fixture
    def mock_interaction(self) -> hikari.AutocompleteInteraction:
        return mock.Mock(options=[mock.Mock(is_focused=True)])

    @pytest.fixture
    def context(
        self, mock_client: tanjun.Client, mock_interaction: hikari.AutocompleteInteraction
    ) -> tanjun.context.AutocompleteContext:
        return tanjun.context.AutocompleteContext(mock_client, mock_interaction)

    def test_author_property(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: hikari.AutocompleteInteraction
    ) -> None:
        assert context.author is mock_interaction.user

    def test_channel_id_property(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: hikari.AutocompleteInteraction
    ) -> None:
        assert context.channel_id is mock_interaction.channel_id

    def test_cache_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.cache is mock_client.cache

    def test_client_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.client is mock_client

    def test_created_at_property(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: hikari.AutocompleteInteraction
    ) -> None:
        assert context.created_at is mock_interaction.created_at

    def test_events_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.events is mock_client.events

    def test_focused_property(self) -> None:
        focused_option = mock.Mock(is_focused=True)
        mock_interaction = mock.Mock(options=[mock.Mock(is_focused=False), focused_option, mock.Mock(is_focused=False)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction)

        assert context.focused is focused_option

    def test_guild_id_property(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: hikari.AutocompleteInteraction
    ) -> None:
        assert context.guild_id is mock_interaction.guild_id

    def test_member_property(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: hikari.AutocompleteInteraction
    ) -> None:
        assert context.member is mock_interaction.member

    def test_server_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.server is mock_client.server

    def test_rest_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.rest is mock_client.rest

    def test_shard_property(
        self,
        context: tanjun.context.AutocompleteContext,
        mock_client: mock.Mock,
        mock_interaction: hikari.AutocompleteInteraction,
    ) -> None:
        mock_shard = mock.Mock()
        mock_client.shards = mock.MagicMock(spec=traits.ShardAware, shard_count=5, shards={2: mock_shard})
        mock_interaction.guild_id = hikari.Snowflake(123321123312)

        assert context.shard is mock_shard

    def test_shard_property_when_dm(
        self,
        context: tanjun.context.AutocompleteContext,
        mock_client: mock.Mock,
        mock_interaction: hikari.AutocompleteInteraction,
    ) -> None:
        mock_shard = mock.Mock()
        mock_client.shards = mock.Mock(shards={0: mock_shard})
        mock_interaction.guild_id = None

        assert context.shard is mock_shard

    def test_shard_property_when_no_shards(self, context: tanjun.context.AutocompleteContext) -> None:
        context._tanjun_client = mock.Mock(shards=None)

        assert context.shard is None

    def test_shards_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.shards is mock_client.shards

    def test_voice_property(self, context: tanjun.context.AutocompleteContext, mock_client: tanjun.Client) -> None:
        assert context.voice is mock_client.voice

    def test_has_responded_property(self, context: tanjun.context.AutocompleteContext) -> None:
        assert context.has_responded is False

    def test_interaction_property(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: hikari.AutocompleteInteraction
    ) -> None:
        assert context.interaction is mock_interaction

    def test_options_property(self) -> None:
        mock_option_1 = mock.Mock()
        mock_option_1.name = "hi"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "bye"
        mock_option_3 = mock.Mock()
        mock_option_3.name = "yoda"
        context = tanjun.context.AutocompleteContext(
            mock.Mock(tanjun.Client), mock.Mock(options=[mock_option_1, mock_option_2, mock_option_3])
        )

        assert context.options == {"hi": mock_option_1, "bye": mock_option_2, "yoda": mock_option_3}

    def test_options_property_for_top_level_command(self, mock_client: mock.Mock) -> None:
        mock_option_1 = mock.Mock(focused=True)
        mock_option_1.name = "hi"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "bye"
        context = tanjun.context.AutocompleteContext(mock_client, mock.Mock(options=[mock_option_1, mock_option_2]))

        assert len(context.options) == 2
        assert context.options["hi"].type is mock_option_1.type
        assert context.options["hi"].value is mock_option_1.value
        assert context.options["hi"].name is mock_option_1.name

        assert context.options["bye"].type is mock_option_2.type
        assert context.options["bye"].value is mock_option_2.value
        assert context.options["bye"].name is mock_option_2.name

    def test_options_property_for_command_group(self, mock_client: mock.Mock) -> None:
        mock_option_1 = mock.Mock(focused=True)
        mock_option_1.name = "kachow"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "nyaa"
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2])
        context = tanjun.context.AutocompleteContext(
            mock_client, mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[group_option])
        )

        assert len(context.options) == 2
        assert context.options["kachow"].type is mock_option_1.type
        assert context.options["kachow"].value is mock_option_1.value
        assert context.options["kachow"].name is mock_option_1.name

        assert context.options["nyaa"].type is mock_option_2.type
        assert context.options["nyaa"].value is mock_option_2.value
        assert context.options["nyaa"].name is mock_option_2.name

    def test_options_property_for_sub_command_group(self, mock_client: mock.Mock) -> None:
        mock_option_1 = mock.Mock(focused=True)
        mock_option_1.name = "meow"
        mock_option_2 = mock.Mock()
        mock_option_2.name = "nya"
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock_option_1, mock_option_2])
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        context = tanjun.context.AutocompleteContext(
            mock_client, mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[group_option])
        )

        assert len(context.options) == 2
        assert context.options["meow"].type is mock_option_1.type
        assert context.options["meow"].value is mock_option_1.value
        assert context.options["meow"].name is mock_option_1.name

        assert context.options["nya"].type is mock_option_2.type
        assert context.options["nya"].value is mock_option_2.value
        assert context.options["nya"].name is mock_option_2.name

    def test_triggering_name_property_for_top_level_command(
        self, context: tanjun.context.autocomplete.AutocompleteContext
    ) -> None:
        assert context.triggering_name is context.interaction.command_name

    def test_triggering_name_property_for_sub_command(self, mock_client: mock.Mock) -> None:
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock.Mock(focused=True)])
        group_option.name = "daniel"
        context = tanjun.context.AutocompleteContext(
            mock_client, mock.Mock(command_name="damn", options=[group_option])
        )

        assert context.triggering_name == "damn daniel"

    def test_triggering_name_property_for_sub_sub_command(self, mock_client: mock.Mock) -> None:
        sub_group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND, options=[mock.Mock(focused=True)])
        sub_group_option.name = "nyaa"
        group_option = mock.Mock(type=hikari.OptionType.SUB_COMMAND_GROUP, options=[sub_group_option])
        group_option.name = "xes"
        context = tanjun.context.AutocompleteContext(
            mock_client, mock.Mock(command_name="meow", options=[group_option])
        )

        assert context.triggering_name == "meow xes nyaa"

    @pytest.mark.asyncio
    async def test_fetch_channel(
        self, context: tanjun.context.AutocompleteContext, mock_interaction: mock.Mock
    ) -> None:
        mock_interaction.fetch_channel = mock.AsyncMock()

        result = await context.fetch_channel()

        assert result is mock_interaction.fetch_channel.return_value
        mock_interaction.fetch_channel.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_fetch_guild(self, context: tanjun.context.AutocompleteContext, mock_interaction: mock.Mock) -> None:
        mock_interaction.fetch_guild = mock.AsyncMock()

        result = await context.fetch_guild()

        assert result is mock_interaction.fetch_guild.return_value
        mock_interaction.fetch_guild.assert_awaited_once_with()

    def test_get_channel(self, context: tanjun.context.AutocompleteContext, mock_interaction: mock.Mock) -> None:
        result = context.get_channel()

        assert result is mock_interaction.get_channel.return_value
        mock_interaction.get_channel.assert_called_once_with()

    def test_get_guild(self, context: tanjun.context.AutocompleteContext, mock_interaction: mock.Mock) -> None:
        result = context.get_guild()

        assert result is mock_interaction.get_guild.return_value
        mock_interaction.get_guild.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_set_choices(self) -> None:
        mock_interaction = mock.AsyncMock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction)
        assert context.has_responded is False

        result = await context.set_choices({"hi": "bye"}, ok="45")

        assert result is None
        assert context.has_responded is True
        mock_interaction.create_response.assert_awaited_once_with(
            [
                hikari.impl.AutocompleteChoiceBuilder(name="hi", value="bye"),
                hikari.impl.AutocompleteChoiceBuilder(name="ok", value="45"),
            ]
        )

    @pytest.mark.asyncio
    async def test_set_choices_when_no_options(self) -> None:
        mock_interaction = mock.AsyncMock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction)

        result = await context.set_choices()

        assert result is None
        mock_interaction.create_response.assert_awaited_once_with([])

    @pytest.mark.asyncio
    async def test_set_choices_when_iterable(self) -> None:
        mock_interaction = mock.AsyncMock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction)

        result = await context.set_choices([("echo", "delta"), ("hi", "bye"), ("goof", "meow")])

        assert result is None
        mock_interaction.create_response.assert_awaited_once_with(
            [
                hikari.impl.AutocompleteChoiceBuilder(name="echo", value="delta"),
                hikari.impl.AutocompleteChoiceBuilder(name="hi", value="bye"),
                hikari.impl.AutocompleteChoiceBuilder(name="goof", value="meow"),
            ]
        )

    @pytest.mark.asyncio
    async def test_set_choices_when_future_based(self) -> None:
        mock_future = mock.Mock()
        mock_interaction = mock.Mock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction, future=mock_future)

        result = await context.set_choices({"meow": "neko", "woof": "borf"}, bark="moo")

        assert result is None
        mock_future.set_result.assert_called_once_with(mock_interaction.build_response.return_value)
        mock_interaction.build_response.assert_called_once_with(
            [
                hikari.impl.AutocompleteChoiceBuilder(name="meow", value="neko"),
                hikari.impl.AutocompleteChoiceBuilder(name="woof", value="borf"),
                hikari.impl.AutocompleteChoiceBuilder(name="bark", value="moo"),
            ]
        )

    @pytest.mark.asyncio
    async def test_set_choices_when_future_based_and_iterable(self) -> None:
        mock_future = mock.Mock()
        mock_interaction = mock.Mock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction, future=mock_future)
        assert context.has_responded is False

        result = await context.set_choices([("japan", "weeb"), ("england", "idk")], usa="lol")

        assert result is None
        mock_future.set_result.assert_called_once_with(mock_interaction.build_response.return_value)
        mock_interaction.build_response.assert_called_once_with(
            [
                hikari.impl.AutocompleteChoiceBuilder(name="japan", value="weeb"),
                hikari.impl.AutocompleteChoiceBuilder(name="england", value="idk"),
                hikari.impl.AutocompleteChoiceBuilder(name="usa", value="lol"),
            ]
        )
        assert context.has_responded is True

    @pytest.mark.asyncio
    async def test_set_choices_when_future_based_and_no_options(self) -> None:
        mock_future = mock.Mock()
        mock_interaction = mock.Mock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction, future=mock_future)

        result = await context.set_choices()

        assert result is None
        mock_future.set_result.assert_called_once_with(mock_interaction.build_response.return_value)
        mock_interaction.build_response.assert_called_once_with([])

    @pytest.mark.asyncio
    async def test_set_choices_when_too_many_options(self) -> None:
        mock_interaction = mock.AsyncMock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction)

        with pytest.raises(ValueError, match="Cannot set more than 25 choices"):
            await context.set_choices({str(v): "a" for v in range(23)}, foo="ok", bar="as", baz="43")

        mock_interaction.create_response.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_choices_when_has_responded(self) -> None:
        mock_interaction = mock.AsyncMock(options=[mock.Mock(is_focused=True)])
        context = tanjun.context.AutocompleteContext(mock.Mock(tanjun.Client), mock_interaction)
        await context.set_choices()
        mock_interaction.create_response.reset_mock()

        with pytest.raises(RuntimeError, match="Cannot set choices after responding"):
            await context.set_choices()

        mock_interaction.create_response.assert_not_called()
