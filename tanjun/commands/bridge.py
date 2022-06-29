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
"""Helper functions which bridge message and slash commands."""
from __future__ import annotations

__all__: list[str] = []

import typing

from .. import conversion
from .. import parsing
from . import message
from . import slash

_CommandUnion = typing.Union[message.MessageCommand[typing.Any], slash.SlashCommand[typing.Any]]
_CommandT = typing.TypeVar("_CommandT", bound=_CommandUnion)


def add_attachment_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...
    # if isinstance(command, /message.MessageCommand):
    # parsing.with_option()


def add_bool_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...


def add_channel_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...


def add_int_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...


def add_member_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...


def add_str_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
    greedy: bool = False
) -> None:
    ...


def add_role_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...


def add_user_opt(
    command: _CommandUnion,
    name: str,
    /,
    description: str = "",
    default: typing.Any = slash.UNDEFINED_DEFAULT,
    positional: bool = True,
) -> None:
    ...
