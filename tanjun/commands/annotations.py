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
"""Parameter annotation based strategy for declaring command arguments."""
from __future__ import annotations

__all__: list[str] = [
    "Attachment",
    "Bool",
    "Channel",
    "Choices",
    "Converted",
    "Float",
    "Int",
    "Max",
    "Member",
    "Mentionable",
    "Min",
    "Role",
    "Str",
    "User",
    "with_annotated_args",
]

import dataclasses
import typing
from collections import abc as collections

import hikari

from .. import conversion
from .. import parsing
from .._vendor import inspect
from . import message
from . import slash

_ChoiceT = typing.TypeVar("_ChoiceT", int, float, str)
_CommandUnion = typing.Union[slash.SlashCommand[typing.Any], message.MessageCommand[typing.Any]]
_CommandUnionT = typing.TypeVar("_CommandUnionT", bound=_CommandUnion)
_ConverterSig = typing.Union[
    collections.Callable[[str], typing.Any],
    collections.Callable[[str], collections.Coroutine[typing.Any, typing.Any, typing.Any]],
]
_T = typing.TypeVar("_T")

_OPTION_MARKER = object()

Attachment = typing.Annotated[hikari.Attachment, _OPTION_MARKER]
Bool = typing.Annotated[bool, _OPTION_MARKER]
Channel = typing.Annotated[hikari.PartialChannel, _OPTION_MARKER]
Float = typing.Annotated[float, _OPTION_MARKER]
Int = typing.Annotated[int, _OPTION_MARKER]
Member = typing.Annotated[hikari.Member, _OPTION_MARKER]
Mentionable = typing.Annotated[typing.Union[hikari.User, hikari.Role], _OPTION_MARKER]
Role = typing.Annotated[hikari.Role, _OPTION_MARKER]
Str = typing.Annotated[str, _OPTION_MARKER]
User = typing.Annotated[hikari.User, _OPTION_MARKER]


class Max:
    __slots__ = ("_value",)

    def __init__(self, value: typing.Union[int, float], /) -> None:
        self._value = value

    @property
    def value(self) -> typing.Union[int, float]:
        return self._value


class Min:
    __slots__ = ("_value",)

    def __init__(self, value: typing.Union[int, float], /) -> None:
        self._value = value

    @property
    def value(self) -> typing.Union[int, float]:
        return self._value


class Choices:
    __slots__ = ("_choices",)

    def __init__(
        self,
        mapping: typing.Union[collections.Mapping[str, _ChoiceT], collections.Iterable[tuple[str, _ChoiceT]]] = (),
        /,
        **kwargs: _ChoiceT,
    ) -> None:
        self._choices = dict(mapping or (), **kwargs)

    @property
    def choices(self) -> collections.Mapping[str, typing.Union[int, str, float]]:
        return self._choices


class Converted:
    __slots__ = ("_converters",)

    def __init__(
        self,
        converters: collections.Iterable[_ConverterSig],
        /,
    ) -> None:
        self._converters = list(converters)

    @property
    def converters(self) -> collections.Sequence[_ConverterSig]:
        return self._converters


def _ensure_value(name: str, type_: type[_T], value: typing.Optional[typing.Any]) -> typing.Optional[_T]:
    if value is None or isinstance(value, type_):
        return value

    raise ValueError(f"{name.capitalize()} value of type {type(value)} is not valid for an {type_.__name__} argument")


def _ensure_values(
    name: str, type_: type[_T], mapping: typing.Optional[collections.Mapping[str, typing.Any]], /
) -> typing.Optional[collections.Mapping[str, _T]]:
    if not mapping:
        return None

    for value in mapping.values():
        if not isinstance(value, type_):
            raise ValueError(f"{name.capitalize()} of type {type(value)} is not valid for a {type_.__name__} argument")

    return typing.cast(collections.Mapping[str, _T], mapping)


_OPTION_TYPE_TO_CONVERTER: dict[type[typing.Any], tuple[_ConverterSig, ...]] = {
    # hikari.Attachment: NotImplemented,
    bool: (conversion.to_bool,),
    hikari.PartialChannel: (conversion.to_channel,),
    float: (float,),
    int: (int,),
    hikari.Member: (conversion.to_member,),
    typing.Union[hikari.User, hikari.Role]: (conversion.to_user, conversion.to_role),
    hikari.Role: (conversion.to_role,),
    str: (str,),
    hikari.User: (conversion.to_user,),
}


@dataclasses.dataclass
class _ArgConfig:
    name: str
    default: typing.Any
    channel_types: typing.Optional[list[type[hikari.PartialChannel]]] = None
    choices: typing.Optional[collections.Mapping[str, typing.Union[str, int, float]]] = None
    converters: typing.Optional[collections.Sequence[_ConverterSig]] = None
    description: typing.Optional[str] = None
    max_value: typing.Union[float, int, None] = None
    min_value: typing.Union[float, int, None] = None
    option_type: typing.Optional[type[typing.Any]] = None

    def to_message_option(self, command: message.MessageCommand[typing.Any], /) -> None:
        if self.converters:
            converters = self.converters

        elif self.option_type:
            converters = _OPTION_TYPE_TO_CONVERTER[self.option_type]

        else:
            return

        if command.parser:
            if not isinstance(command.parser, parsing.AbstractOptionParser):
                raise TypeError("Expected parser to be an instance of tanjun.parsing.AbstractOptionParser")

            parser = command.parser

        else:
            parser = parsing.ShlexParser()
            command.set_parser(parser)

        if self.default is inspect.Parameter.empty:
            parser.add_argument(
                self.name,
                converters=converters,
                min_value=self.min_value,
                max_value=self.max_value,
            )

        else:
            parser.add_option(
                self.name,
                "--" + self.name.replace("_", "-"),
                converters=converters,
                default=self.default,
                min_value=self.min_value,
                max_value=self.max_value,
            )

    def _slash_default(self) -> typing.Any:
        return slash.UNDEFINED_DEFAULT if self.default is inspect.Parameter.empty else self.default

    def to_slash_option(self, command: slash.SlashCommand[typing.Any], /) -> None:
        option_type = self.option_type
        if not option_type and self.converters:
            option_type = str

        if option_type:
            if not self.description:
                raise RuntimeError("Missing slash command description")

            self._SLASH_OPTION_ADDER[option_type](self, command, self.description)

    _SLASH_OPTION_ADDER: dict[
        type[typing.Any],
        collections.Callable[[_ArgConfig, slash.SlashCommand[typing.Any], str], slash.SlashCommand[typing.Any]],
    ] = {
        hikari.Attachment: lambda self, c, d: c.add_attachment_option(self.name, d, default=self._slash_default()),
        bool: lambda self, c, d: c.add_bool_option(self.name, d, default=self._slash_default()),
        hikari.PartialChannel: lambda self, c, d: c.add_channel_option(self.name, d, default=self._slash_default()),
        float: lambda self, c, d: c.add_float_option(
            self.name,
            d,
            choices=_ensure_values("choice", float, self.choices),
            default=self._slash_default(),
            min_value=_ensure_value("min", float, self.min_value),
            max_value=_ensure_value("max", float, self.max_value),
        ),
        int: lambda self, c, d: c.add_int_option(
            self.name,
            d,
            choices=_ensure_values("choice", int, self.choices),
            default=self._slash_default(),
            min_value=_ensure_value("min", int, self.min_value),
            max_value=_ensure_value("max", int, self.max_value),
        ),
        hikari.Member: lambda self, c, d: c.add_member_option(self.name, d, default=self._slash_default()),
        typing.Union[hikari.User, hikari.Role]: lambda self, c, d: c.add_mentionable_option(
            self.name, d, default=self._slash_default()
        ),
        hikari.Role: lambda self, c, d: c.add_role_option(self.name, d, default=self._slash_default()),
        str: lambda self, c, d: c.add_str_option(
            self.name,
            d,
            choices=_ensure_values("choice", str, self.choices),
            converters=self.converters or (),
            default=self._slash_default(),
        ),
        hikari.User: lambda self, c, d: c.add_user_option(self.name, d, default=self._slash_default()),
    }


def with_annotated_args(command: _CommandUnionT, /) -> _CommandUnionT:
    try:
        signature = inspect.signature(command.callback, follow_wrapped=True)
    except ValueError:  # If we can't inspect it then we have to assume this is a NO
        # As a note, this fails on some "signature-less" builtin functions/types like str.
        return command

    for parameter in signature.parameters.values():
        if parameter.annotation is parameter.empty or typing.get_origin(parameter.annotation) is not typing.Annotated:
            continue

        arg_config = _ArgConfig(parameter.name, parameter.default)
        args = typing.get_args(parameter.annotation)
        for arg in args[1:]:
            if arg is _OPTION_MARKER:
                arg_config.option_type = args[0]

            elif isinstance(arg, Choices):
                arg_config.choices = arg.choices

            elif isinstance(arg, Converted):
                arg_config.converters = arg.converters

            elif isinstance(arg, str):
                arg_config.description = arg

            elif isinstance(arg, Max):
                arg_config.max_value = arg.value

            elif isinstance(arg, Min):
                arg_config.min_value = arg.value

            elif isinstance(arg, slice):
                raise NotImplementedError("A5 said 'scary'")

            elif isinstance(arg, range):
                raise NotImplementedError("A5 said 'scary'")

        if isinstance(command, slash.SlashCommand):
            arg_config.to_slash_option(command)

        else:
            arg_config.to_message_option(command)

    return command
