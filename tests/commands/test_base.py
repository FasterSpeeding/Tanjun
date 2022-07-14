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
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import types
import typing
from collections import abc as collections
from unittest import mock

import pytest

from tanjun.commands import base as base_command

_T = typing.TypeVar("_T")


def stub_class(
    cls: typing.Type[_T],
    /,
    args: collections.Sequence[typing.Any] = (),
    kwargs: typing.Optional[collections.Mapping[str, typing.Any]] = None,
    **namespace: typing.Any,
) -> _T:
    namespace["__slots__"] = ()

    for name in getattr(cls, "__abstractmethods__", None) or ():
        if name not in namespace:
            namespace[name] = mock.MagicMock()

    name = origin.__name__ if (origin := getattr(cls, "__origin__", None)) else cls.__name__
    new_cls = types.new_class(name, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)(*args, **kwargs or {})


class TestPartialCommand:
    @pytest.fixture()
    def command(self) -> base_command.PartialCommand[typing.Any]:
        fields: dict[str, typing.Any] = {}
        for name in base_command.PartialCommand.__abstractmethods__:
            fields[name] = mock.MagicMock()

        return types.new_class(
            "PartialCommand", (base_command.PartialCommand[typing.Any],), exec_body=lambda body: body.update(fields)
        )()

    def test_metadata_property(self, command: base_command.PartialCommand[typing.Any]):
        assert command.metadata is command._metadata

    def test_copy(self, command: base_command.PartialCommand[typing.Any]):
        mock_check = mock.MagicMock()
        command._checks = [mock_check]
        command._hooks = mock.Mock()
        mock_metadata = mock.Mock()
        command._metadata = mock_metadata

        new_command = command.copy()

        assert new_command is not command
        assert new_command._checks == [mock_check]
        assert new_command._checks[0] is not mock_check
        assert new_command._hooks is command._hooks.copy.return_value
        assert new_command._metadata is mock_metadata.copy.return_value

    def test_set_hooks(self, command: base_command.PartialCommand[typing.Any]):
        mock_hooks = mock.Mock()

        assert command.set_hooks(mock_hooks) is command
        assert command.hooks is mock_hooks

    def test_set_metadata(self, command: base_command.PartialCommand[typing.Any]):
        key = mock.Mock()
        value = mock.Mock()

        result = command.set_metadata(key, value)

        assert result is command
        assert command.metadata[key] is value

    def test_add_check(self, command: base_command.PartialCommand[typing.Any]):
        mock_check = mock.Mock()

        assert command.add_check(mock_check) is command

        assert command.checks == [mock_check]

    def test_add_check_when_already_present(self, command: base_command.PartialCommand[typing.Any]):
        mock_check = mock.Mock()

        assert command.add_check(mock_check).add_check(mock_check) is command

        assert list(command.checks).count(mock_check) == 1

    def test_remove_check(self, command: base_command.PartialCommand[typing.Any]):
        def mock_check() -> bool:
            raise NotImplementedError

        command.add_check(mock_check)

        result = command.remove_check(mock_check)

        assert result is command
        assert command.checks == []

    def test_with_check(self, command: base_command.PartialCommand[typing.Any]):
        mock_check = mock.Mock()
        add_check = mock.Mock()
        command = stub_class(base_command.PartialCommand, add_check=add_check)

        assert command.with_check(mock_check) is mock_check
        add_check.assert_called_once_with(mock_check)

    def test_with_check_when_already_present(self, command: base_command.PartialCommand[typing.Any]):
        def mock_check() -> bool:
            raise NotImplementedError

        command.add_check(mock_check).with_check(mock_check)
        assert command.with_check(mock_check) is mock_check

        assert list(command.checks).count(mock_check) == 1

    def test_bind_client(self, command: base_command.PartialCommand[typing.Any]):
        command.bind_client(mock.Mock())

    def test_bind_component(self, command: base_command.PartialCommand[typing.Any]):
        mock_component = mock.Mock()

        command.bind_component(mock_component)

        assert command.component is mock_component
