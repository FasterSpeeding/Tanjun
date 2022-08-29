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

# pyright: reportIncompatibleMethodOverride=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.

from unittest import mock

import hikari
import pytest

import tanjun


class TestCommandError:
    def test_init_dunder_method(self):
        mock_attachment = mock.Mock()
        mock_component = mock.Mock()
        mock_embed = mock.Mock()

        error = tanjun.CommandError(
            "moon",
            delete_after=555,
            attachments=[mock_attachment],
            components=[mock_component],
            embeds=[mock_embed],
            mentions_everyone=False,
            user_mentions=[2332],
            role_mentions=[6534],
        )

        assert error.content == "moon"
        assert error.attachments == [mock_attachment]
        assert error.components == [mock_component]
        assert error.delete_after == 555
        assert error.embeds == [mock_embed]
        assert error.mentions_everyone is False
        assert error.user_mentions == [2332]
        assert error.role_mentions == [6534]

    def test_init_dunder_method_for_singular_fields(self):
        mock_attachment = mock.Mock()
        mock_component = mock.Mock()
        mock_embed = mock.Mock()

        error = tanjun.CommandError(attachment=mock_attachment, component=mock_component, embed=mock_embed)

        assert error.attachments == [mock_attachment]
        assert error.components == [mock_component]
        assert error.embeds == [mock_embed]

    def test_init_dunder_method_for_partial(self):
        error = tanjun.CommandError()

        assert error.content is hikari.UNDEFINED
        assert error.attachments is hikari.UNDEFINED
        assert error.components is hikari.UNDEFINED
        assert error.delete_after is None
        assert error.embeds is hikari.UNDEFINED
        assert error.mentions_everyone is hikari.UNDEFINED
        assert error.role_mentions is hikari.UNDEFINED
        assert error.user_mentions is hikari.UNDEFINED

    def test_init_dunder_method_when_both_attachment_and_attachments_passed(self):
        with pytest.raises(ValueError, match="Cannot specify both attachment and attachments"):
            tanjun.CommandError(attachment=mock.Mock(), attachments=[mock.Mock()])

    def test_init_dunder_method_when_both_component_and_components_passed(self):
        with pytest.raises(ValueError, match="Cannot specify both component and components"):
            tanjun.CommandError(component=mock.Mock(), components=[mock.Mock()])

    def test_init_dunder_method_when_both_embed_and_embeds_passed(self):
        with pytest.raises(ValueError, match="Cannot specify both embed and embeds"):
            tanjun.CommandError(embed=mock.Mock(), embeds=[mock.Mock()])

    def test_str_dunder_method(self):
        assert str(tanjun.CommandError("bar")) == "bar"

    @pytest.mark.asyncio()
    async def test_send(self):
        error = tanjun.CommandError()
        mock_context = mock.AsyncMock()

        result = await error.send(mock_context)

        assert result is mock_context.respond.return_value
        mock_context.respond.assert_awaited_once_with(
            content=hikari.UNDEFINED,
            attachments=hikari.UNDEFINED,
            components=hikari.UNDEFINED,
            delete_after=None,
            embeds=hikari.UNDEFINED,
            ensure_result=False,
            mentions_everyone=hikari.UNDEFINED,
            role_mentions=hikari.UNDEFINED,
            user_mentions=hikari.UNDEFINED,
        )

    @pytest.mark.asyncio()
    async def test_send_when_all_fields(self):
        mock_attachment = mock.Mock()
        mock_component = mock.Mock()
        mock_embed = mock.Mock()
        error = tanjun.CommandError(
            "hello",
            attachments=[mock_attachment],
            components=[mock_component],
            delete_after=53,
            embeds=[mock_embed],
            mentions_everyone=True,
            role_mentions=[123, 431],
            user_mentions=[666, 555],
        )
        mock_context = mock.AsyncMock()

        result = await error.send(mock_context, ensure_result=True)

        assert result is mock_context.respond.return_value
        mock_context.respond.assert_awaited_once_with(
            content="hello",
            attachments=[mock_attachment],
            components=[mock_component],
            delete_after=53,
            embeds=[mock_embed],
            ensure_result=True,
            mentions_everyone=True,
            role_mentions=[123, 431],
            user_mentions=[666, 555],
        )


class TestParserError:
    def test__init__(self):
        error = tanjun.ParserError("bank", "no u")

        assert error.message == "bank"
        assert error.parameter == "no u"

    def test__str__(self):
        assert str(tanjun.ParserError("bankette", "now2")) == "bankette"


class TestConversionError:
    def test__init__(self):
        mock_error = mock.Mock()

        error = tanjun.ConversionError("bankettete", "aye", [mock_error])

        assert error.message == "bankettete"
        assert error.parameter == "aye"
        assert error.errors == (mock_error,)


class TestNotEnoughArgumentsError:
    def test__init__(self):
        error = tanjun.NotEnoughArgumentsError("aye", "naye")

        assert error.message == "aye"
        assert error.parameter == "naye"


class TestTooManyArgumentsError:
    def test__init__(self):
        error = tanjun.TooManyArgumentsError("blank", "fama")

        assert error.message == "blank"
        assert error.parameter == "fama"


class TestModuleMissingLoaders:
    def test___init__(self):
        error = tanjun.ModuleMissingLoaders("foo", "bar")

        assert error.message == "foo"
        assert error.path == "bar"


class TestModuleMissingUnloaders:
    def test___init__(self):
        error = tanjun.ModuleMissingUnloaders("beep", "boop")

        assert error.message == "beep"
        assert error.path == "boop"


class TestModuleStateConflict:
    def test___init__(self):
        error = tanjun.ModuleStateConflict("esxd", "dsaasd")

        assert error.message == "esxd"
        assert error.path == "dsaasd"


class TestFailedModuleLoad:
    def test___init__(self):
        error = tanjun.FailedModuleLoad("beat/my/boobs")

        assert error.path == "beat/my/boobs"


class TestFailedModuleUnload:
    def test___init__(self):
        error = tanjun.FailedModuleUnload("yeet/ok")

        assert error.path == "yeet/ok"
