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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

from unittest import mock

import pytest

import tanjun


class TestHooks:
    def test___repr__(self):
        on_error = mock.Mock()
        parser_error = mock.Mock()
        pre_execution = mock.Mock()
        post_execution = mock.Mock()
        success = mock.Mock()
        result = (
            tanjun.AnyHooks()
            .set_on_error(on_error)
            .set_on_parser_error(parser_error)
            .set_pre_execution(pre_execution)
            .set_post_execution(post_execution)
            .set_on_success(success)
        )

        assert repr(result) == (
            f"Hooks <{on_error!r}, {parser_error!r}, " f"{pre_execution!r}, {post_execution!r}, {success!r}>"
        )

    def test_add_to_command(self):
        hooks = tanjun.AnyHooks()
        mock_command = mock.Mock()

        assert hooks.add_to_command(mock_command) is mock_command

        mock_command.set_hooks.assert_called_once_with(hooks)

    @pytest.mark.skip(reason="not implemented")
    def test_copy(self):
        hooks = tanjun.AnyHooks()

        result = hooks.copy()

        assert result == hooks
        assert result is not hooks

    def test_set_on_error(self):
        hooks = tanjun.AnyHooks()
        mock_on_error = mock.Mock()

        assert hooks.set_on_error(mock_on_error) is hooks

        assert hooks._error is mock_on_error

    def test_with_on_error(self):
        hooks = tanjun.AnyHooks()
        mock_on_error = mock.Mock()

        assert hooks.with_on_error(mock_on_error) is mock_on_error

        assert hooks._error is mock_on_error

    def test_set_on_parser_error(self):
        hooks = tanjun.AnyHooks()
        mock_on_parser_error = mock.Mock()

        assert hooks.set_on_parser_error(mock_on_parser_error) is hooks

        assert hooks._parser_error is mock_on_parser_error

    def test_with_on_parser_error(self):
        hooks = tanjun.AnyHooks()
        mock_on_parser_error = mock.Mock()

        assert hooks.with_on_parser_error(mock_on_parser_error) is mock_on_parser_error

        assert hooks._parser_error is mock_on_parser_error

    def test_set_post_execution(self):
        hooks = tanjun.AnyHooks()
        mock_post_execution = mock.Mock()

        assert hooks.set_post_execution(mock_post_execution) is hooks

        assert hooks._post_execution is mock_post_execution

    def test_with_post_execution(self):
        hooks = tanjun.AnyHooks()
        mock_post_execution = mock.Mock()

        assert hooks.with_post_execution(mock_post_execution) is mock_post_execution

        assert hooks._post_execution is mock_post_execution

    def test_set_pre_execution(self):
        hooks = tanjun.AnyHooks()
        mock_pre_execution = mock.Mock()

        assert hooks.set_pre_execution(mock_pre_execution) is hooks

        assert hooks._pre_execution is mock_pre_execution

    def test_with_pre_execution(self):
        hooks = tanjun.AnyHooks()
        mock_pre_execution = mock.Mock()

        assert hooks.with_pre_execution(mock_pre_execution) is mock_pre_execution

        assert hooks._pre_execution is mock_pre_execution

    def test_set_on_success(self):
        hooks = tanjun.AnyHooks()
        mock_on_success = mock.Mock()

        assert hooks.set_on_success(mock_on_success) is hooks

        assert hooks._success is mock_on_success

    def test_with_on_success(self):
        hooks = tanjun.AnyHooks()
        mock_on_success = mock.Mock()

        assert hooks.with_on_success(mock_on_success) is mock_on_success

        assert hooks._success is mock_on_success

    @pytest.mark.asyncio()
    async def test_trigger_error_for_parser_error_with_handlers(self):
        mock_callback = mock.AsyncMock()
        mock_other_hook = mock.Mock(trigger_error=mock.AsyncMock(return_value=100))
        mock_context = mock.Mock()
        mock_error = mock.MagicMock(tanjun.ParserError)

        result = (
            await tanjun.AnyHooks()
            .set_on_parser_error(mock_callback)
            .trigger_error(mock_context, mock_error, hooks={mock_other_hook})
        )

        assert result == 200
        mock_callback.assert_awaited_once_with(mock_context, mock_error)
        mock_other_hook.trigger_error.assert_awaited_once_with(mock_context, mock_error)

    @pytest.mark.asyncio()
    async def test_trigger_error_for_parser_error_without_handlers(self):
        result = await tanjun.AnyHooks().trigger_error(mock.Mock(), mock.MagicMock(tanjun.ParserError))

        assert result == 0

    @pytest.mark.asyncio()
    async def test_trigger_error_with_handler(self):
        mock_callback = mock.AsyncMock(return_value=True)
        mock_other_hook = mock.Mock(trigger_error=mock.AsyncMock(return_value=2))
        mock_context = mock.Mock()
        mock_error = mock.Mock()

        result = (
            await tanjun.AnyHooks()
            .set_on_error(mock_callback)
            .trigger_error(mock_context, mock_error, hooks={mock_other_hook})
        )

        assert result == 3
        mock_callback.assert_awaited_once_with(mock_context, mock_error)
        mock_other_hook.trigger_error.assert_awaited_once_with(mock_context, mock_error)

    @pytest.mark.asyncio()
    async def test_trigger_error_without_handler(self):
        result = await tanjun.AnyHooks().trigger_error(mock.Mock(), mock.Mock())

        assert result == 0

    @pytest.mark.asyncio()
    async def test_trigger_post_execution_with_handlers(self):
        mock_callback = mock.AsyncMock()
        mock_other_hook = mock.Mock(trigger_post_execution=mock.AsyncMock())
        mock_context = mock.Mock()

        (
            await tanjun.AnyHooks()
            .set_post_execution(mock_callback)
            .trigger_post_execution(mock_context, hooks={mock_other_hook})
        )

        mock_callback.assert_awaited_once_with(mock_context)
        mock_other_hook.trigger_post_execution.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_trigger_post_execution_without_handlers(self):
        await tanjun.AnyHooks().trigger_post_execution(mock.Mock())

    @pytest.mark.asyncio()
    async def test_trigger_pre_execution_with_handlers(self):
        mock_callback = mock.AsyncMock()
        mock_other_hook = mock.Mock(trigger_pre_execution=mock.AsyncMock())
        mock_context = mock.Mock()

        (
            await tanjun.AnyHooks()
            .set_pre_execution(mock_callback)
            .trigger_pre_execution(mock_context, hooks={mock_other_hook})
        )

        mock_callback.assert_awaited_once_with(mock_context)
        mock_other_hook.trigger_pre_execution.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_trigger_pre_execution_without_handlers(self):
        await tanjun.AnyHooks().trigger_pre_execution(mock.Mock())

    @pytest.mark.asyncio()
    async def test_trigger_success_with_handlers(self):
        mock_callback = mock.AsyncMock()
        mock_other_hook = mock.Mock(trigger_success=mock.AsyncMock())
        mock_context = mock.Mock()

        (await tanjun.AnyHooks().set_on_success(mock_callback).trigger_success(mock_context, hooks={mock_other_hook}))

        mock_callback.assert_awaited_once_with(mock_context)
        mock_other_hook.trigger_success.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_trigger_success_without_handlers(self):
        await tanjun.AnyHooks().trigger_success(mock.Mock())
