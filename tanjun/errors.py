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
"""The errors and warnings raised within and by Tanjun."""
from __future__ import annotations

__all__: typing.Sequence[str] = [
    "CommandError",
    "ConversionError",
    "FailedCheck",
    "NotEnoughArgumentsError",
    "TooManyArgumentsError",
    "ParserError",
    "TanjunError",
    "TanjunWarning",
    "StateWarning",
]

import typing

from tanjun import traits


class TanjunError(Exception):
    """The base class for all errors raised by Tanjun."""

    __slots__: typing.Sequence[str] = ()


class TanjunWarning(RuntimeWarning):
    """The base class for all warnings raised by Tanjun."""

    __slots__: typing.Sequence[str] = ()


class CommandError(TanjunError):
    """Error raised to end command execution.

    Parameters
    ----------
    message : typing.Optional[str]
        If this is a non-empty string then this message should will be sent as
        a response to the message that triggered the current command otherwise
        `builtins.None` or `""` will silently end command execution.
    """

    __slots__: typing.Sequence[str] = ("message",)

    # None or empty string == no response
    message: typing.Optional[str]
    """The response error message.

    If this is an empty string or `builtins.None` then this will silently end
    command execution otherwise Tanjun will try to send the string message in
    response.
    """

    def __init__(self, message: typing.Optional[str], /) -> None:
        if message and len(message) > 2000:
            raise ValueError("Error message cannot be over 2_000 characters long.")

        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.message}>"

    def __str__(self) -> str:
        return self.message or ""


class FailedCheck(TanjunError, RuntimeError):
    """Error raised as an alternative to returning `False` in a check."""

    __slots__: typing.Sequence[str] = ()


class ParserError(TanjunError, ValueError):
    """Base error raised by a parser or parameter during parsing.

    !!! note
        Other error raised by the parser should subclass this error.

    Parameters
    ----------
    message : str
        String message for this error.
    parameter : typing.Optional[traits.Parameter]
        The parameter which caused this error, should be `builtins.None` if not
        applicable.
    """

    __slots__: typing.Sequence[str] = ("message", "parameter")

    message: str
    """String message for this error.

    !!! note
        This may be used as a command response message.
    """

    parameter: typing.Optional[traits.Parameter]
    """Parameter this was raised for.

    !!! note
        This will be `builtin.None` if it was raised while parsing the provided
        message content.
    """

    def __init__(self, message: str, parameter: typing.Optional[traits.Parameter], /) -> None:
        self.message = message
        self.parameter = parameter

    def __str__(self) -> str:
        return self.message


class ConversionError(ParserError):
    """Error raised by a parser parameter when it failed to converter a value.

    Parameters
    ----------
    parameter : tanjun.traits.Parameter
        The parameter this was raised by.
    errors : typing.Iterable[ValueError]
        An iterable of the source value errors which were raised during conversion/
    """

    __slots__: typing.Sequence[str] = ("errors",)

    errors: typing.Sequence[ValueError]
    """Sequence of the errors that were caught during conversion for this parameter."""

    parameter: traits.Parameter
    """Parameter this error was raised for."""

    def __init__(self, parameter: traits.Parameter, errors: typing.Iterable[ValueError], /) -> None:
        option_or_argument = "option" if isinstance(parameter, traits.Option) else "argument"
        super().__init__(f"Couldn't convert {option_or_argument} '{parameter.key}'", parameter)
        self.errors = tuple(errors)


class NotEnoughArgumentsError(ParserError):
    """Error raised by the parser when not enough arguments are found for a parameter.

    Parameters
    ----------
    parameter : tanjun.traits.Parameter
        The parameter this error was raised for
    """

    __slots__: typing.Sequence[str] = ()

    parameter: traits.Parameter
    """Parameter this error was raised for."""

    def __init__(self, message: str, parameter: traits.Parameter, /) -> None:
        super().__init__(message, parameter)


class TooManyArgumentsError(ParserError):
    """Error raised by the parser when too many arguments are found for a parameter.

    Parameters
    ----------
    parameter : tanjun.traits.Parameter
        The parameter this error was raised for
    """

    __slots__: typing.Sequence[str] = ()

    parameter: traits.Parameter
    """Parameter this error was raised for."""

    def __init__(self, message: str, parameter: traits.Parameter, /) -> None:
        super().__init__(message, parameter)


class StateWarning(RuntimeWarning):
    """Warning raised when a utility is loaded without access to state stores it depends on."""

    __slots__: typing.Sequence[str] = ()
