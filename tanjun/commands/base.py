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
"""Standard base mplementation for Tanjun's command objects."""
from __future__ import annotations

__all__: list[str] = ["PartialCommand"]

import copy
import typing
from collections import abc as collections

from .. import abc
from .. import components

if typing.TYPE_CHECKING:
    _CheckSigT = typing.TypeVar("_CheckSigT", bound=abc.CheckSig)
    _PartialCommandT = typing.TypeVar("_PartialCommandT", bound="PartialCommand[typing.Any]")


_ContextT = typing.TypeVar("_ContextT", bound="abc.Context")


class PartialCommand(abc.ExecutableCommand[_ContextT], components.AbstractComponentLoader):
    """Base class for the standard ExecutableCommand implementations."""

    __slots__ = ("_checks", "_component", "_hooks", "_metadata")

    def __init__(self) -> None:
        self._checks: list[abc.CheckSig] = []
        self._component: typing.Optional[abc.Component] = None
        self._hooks: typing.Optional[abc.Hooks[_ContextT]] = None
        self._metadata: dict[typing.Any, typing.Any] = {}

    @property
    def checks(self) -> collections.Collection[abc.CheckSig]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._checks.copy()

    @property
    def component(self) -> typing.Optional[abc.Component]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._component

    @property
    def hooks(self) -> typing.Optional[abc.Hooks[_ContextT]]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._hooks

    @property
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._metadata

    def copy(self: _PartialCommandT, *, _new: bool = True) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if not _new:
            self._checks = [copy.copy(check) for check in self._checks]
            self._hooks = self._hooks.copy() if self._hooks else None
            self._metadata = self._metadata.copy()
            return self

        return copy.copy(self).copy(_new=False)

    def set_hooks(self: _PartialCommandT, hooks: typing.Optional[abc.Hooks[_ContextT]], /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._hooks = hooks
        return self

    def set_metadata(self: _PartialCommandT, key: typing.Any, value: typing.Any, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._metadata[key] = value
        return self

    def add_check(self: _PartialCommandT, check: abc.CheckSig, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if check not in self._checks:
            self._checks.append(check)

        return self

    def remove_check(self: _PartialCommandT, check: abc.CheckSig, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._checks.remove(check)
        return self

    def with_check(self, check: _CheckSigT, /) -> _CheckSigT:
        self.add_check(check)
        return check

    def bind_client(self: _PartialCommandT, client: abc.Client, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self

    def bind_component(self: _PartialCommandT, component: abc.Component, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._component = component
        return self
