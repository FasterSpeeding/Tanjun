# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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

__all__: typing.Sequence[str] = [
    "CommandError",
    "ConversionError",
    "NotEnoughArgumentsError",
    "TooManyArgumentsError",
    "ParserError",
    "TanjunError",
]

import typing

from tanjun import traits


class TanjunError(Exception):
    __slots__: typing.Sequence[str] = ()


class CommandError(TanjunError):
    __slots__: typing.Sequence[str] = ("message",)

    # None or empty string == no response
    message: typing.Optional[str]

    def __init__(self, message: typing.Optional[str], /) -> None:
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.message}>"

    def __str__(self) -> str:
        return self.message or ""


class ParserError(TanjunError, ValueError):
    __slots__: typing.Sequence[str] = ("message", "parameter")

    message: str
    parameter: typing.Optional[traits.Parameter]

    def __init__(self, message: str, parameter: typing.Optional[traits.Parameter], /) -> None:
        self.message = message
        self.parameter = parameter

    def __str__(self) -> str:
        return self.message


class ConversionError(ParserError):
    __slots__: typing.Sequence[str] = ("errors",)

    errors: typing.Sequence[ValueError]
    parameter: traits.Parameter

    def __init__(self, parameter: traits.Parameter, errors: typing.Iterable[ValueError], /) -> None:
        option_or_argument = "option" if isinstance(parameter, traits.Option) else "argument"
        super().__init__(f"Couldn't convert {option_or_argument} '{parameter.key}'", parameter)
        self.errors = tuple(errors)


class NotEnoughArgumentsError(ParserError):
    __slots__: typing.Sequence[str] = ()

    parameter: traits.Parameter

    def __init__(self, message: str, parameter: traits.Parameter, /) -> None:
        super().__init__(message, parameter)


class TooManyArgumentsError(ParserError):
    __slots__: typing.Sequence[str] = ()

    parameter: traits.Parameter

    def __init__(self, message: str, parameter: traits.Parameter, /) -> None:
        super().__init__(message, parameter)
