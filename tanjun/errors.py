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
"""The errors and warnings raised within and by Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "CommandError",
    "ConversionError",
    "HaltExecution",
    "FailedCheck",
    "MissingDependencyError",
    "NotEnoughArgumentsError",
    "TooManyArgumentsError",
    "ParserError",
    "TanjunError",
    "TanjunWarning",
    "StateWarning",
]

import typing

if typing.TYPE_CHECKING:
    from collections import abc as collections


class TanjunError(Exception):
    """The base class for all errors raised by Tanjun."""

    __slots__ = ()


class TanjunWarning(RuntimeWarning):
    """The base class for all warnings raised by Tanjun."""

    __slots__ = ()


class HaltExecution(TanjunError):
    """Error raised while looking for a command in-order to end-execution early.

    For the most part, this will be raised during checks in-order to prevent
    other commands from being tried.
    """

    __slots__ = ()


class MissingDependencyError(TanjunError):
    """Error raised when a dependency couldn't be found."""

    __slots__ = ("message",)

    def __init__(self, message: str) -> None:
        self.message = message


class CommandError(TanjunError):
    """Error raised to end command execution.

    Parameters
    ----------
    message : str
        String message which will be sent as a response to the message
        that triggered the current command.

    Raises
    ------
    ValueError
        Raised when the message is over 2000 characters long or empty.
    """

    __slots__ = ("message",)

    # None or empty string == no response
    message: str
    """The response error message.

    If this is an empty string or `None` then this will silently end
    command execution otherwise Tanjun will try to send the string message in
    response.
    """

    def __init__(self, message: str, /) -> None:
        if len(message) > 2000:
            raise ValueError("Error message cannot be over 2_000 characters long.")

        elif not message:
            raise ValueError("Response message must have at least 1 character.")

        self.message = message

    def __str__(self) -> str:
        return self.message or ""


# TODO: use this
class InvalidCheck(TanjunError, RuntimeError):  # TODO: or/and warning?  # TODO: InvalidCheckError
    """Error raised as an assertion that a check will never pass in the current environment."""

    __slots__ = ()


class FailedCheck(TanjunError, RuntimeError):  # TODO: FailedCheckError
    """Error raised as an alternative to returning `False` in a check."""

    __slots__ = ()


class ParserError(TanjunError, ValueError):
    """Base error raised by a parser or parameter during parsing.

    .. note::
        Expected errors raised by the parser will subclass this error.

    Parameters
    ----------
    message : str
        String message for this error.
    parameter : typing.Optional[str]
        Name of the parameter which caused this error, should be `None` if not
        applicable.
    """

    __slots__ = ("message", "parameter")

    message: str
    """String message for this error.

    .. note::
        This may be used as a command response message.
    """

    parameter: typing.Optional[str]
    """Name of the this was raised for.

    .. note::
        This will be `builtin.None` if it was raised while parsing the provided
        message content.
    """

    def __init__(self, message: str, parameter: typing.Optional[str], /) -> None:
        self.message = message
        self.parameter = parameter

    def __str__(self) -> str:
        return self.message


class ConversionError(ParserError):
    """Error raised by a parser parameter when it failed to converter a value.

    Parameters
    ----------
    parameter : tanjun.abc.Parameter
        The parameter this was raised by.
    errors : collections.abc.Iterable[ValueError]
        An iterable of the source value errors which were raised during conversion/
    """

    __slots__ = ("errors",)

    errors: collections.Sequence[ValueError]
    """Sequence of the errors that were caught during conversion for this parameter."""

    parameter: str
    """Name of the parameter this error was raised for."""

    def __init__(self, message: str, parameter: str, /, errors: collections.Iterable[ValueError] = ()) -> None:
        super().__init__(message, parameter)
        self.errors = tuple(errors)


class NotEnoughArgumentsError(ParserError):
    """Error raised by the parser when not enough arguments are found for a parameter.

    Parameters
    ----------
    parameter : tanjun.abc.Parameter
        The parameter this error was raised for
    """

    __slots__ = ()

    parameter: str
    """Name of the parameter this error was raised for."""

    def __init__(self, message: str, parameter: str, /) -> None:
        super().__init__(message, parameter)


class TooManyArgumentsError(ParserError):
    """Error raised by the parser when too many arguments are found for a parameter.

    Parameters
    ----------
    parameter : tanjun.abc.Parameter
        The parameter this error was raised for
    """

    __slots__ = ()

    parameter: str
    """Name of the parameter this error was raised for."""

    def __init__(self, message: str, parameter: str, /) -> None:
        super().__init__(message, parameter)


class StateWarning(RuntimeWarning):
    """Warning raised when a utility is loaded without access to state stores it depends on."""

    __slots__ = ()
