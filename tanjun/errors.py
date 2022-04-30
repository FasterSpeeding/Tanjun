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
"""The errors and warnings raised within and by Tanjun."""
from __future__ import annotations

__all__: list[str] = [
    "CommandError",
    "ConversionError",
    "FailedCheck",
    "FailedModuleLoad",
    "FailedModuleUnload",
    "HaltExecution",
    "MissingDependencyError",
    "ModuleMissingLoaders",
    "ModuleStateConflict",
    "NotEnoughArgumentsError",
    "ParserError",
    "TanjunError",
    "TooManyArgumentsError",
]

import typing

import alluka
import hikari

if typing.TYPE_CHECKING:
    import datetime
    import pathlib
    from collections import abc as collections

    from . import abc as tanjun


class TanjunError(Exception):
    """The base class for all errors raised by Tanjun."""


class HaltExecution(TanjunError):
    """Error raised while looking for a command in-order to end-execution early.

    For the most part, this will be raised during checks in-order to prevent
    other commands from being tried.
    """


MissingDependencyError = alluka.MissingDependencyError
"""Type alias of [alluka.MissingDependencyError][]."""


class CommandError(TanjunError):
    """An error which is sent as a response to the command call."""

    # None or empty string == no response
    content: hikari.UndefinedOr[str]
    """The response error message's content."""

    delete_after: typing.Union[datetime.timedelta, float, int, None]
    """The seconds after which the response message should be deleted, if set."""

    components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]]
    """Sequence of the components to be sent as a response to the command."""

    embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]]
    """Sequence of the embeds to be sent as a response to the command."""

    mentions_everyone: hikari.UndefinedOr[bool]
    """Whether or not the response should be allowed to mention `@everyone`/`@here`."""

    user_mentions: typing.Union[hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType]
    """Configuration for the response's allowed user mentions.

    If this is a sequence then the response will only be allowed to mention
    users in the sequence.

    If this is a bool then the response will only be allowed to mention users
    if the value is `True`.
    """

    role_mentions: typing.Union[hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType]
    """Configuration for the response's allowed role mentions.

    If this is a sequence then the response will only be allowed to mention
    roles in the sequence.

    If this is a bool then the response will only be allowed to mention roles
    if the value is `True`.
    """

    def __init__(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> None:
        """Initialise a command error.

        Parameters
        ----------
        content
            String message which will be sent as a response to the command.

        Raises
        ------
        ValueError
            Raised for any of the following reasons:

            * When both `component` and `components` are passed.
            * When both `embed` and `embeds` are passed.
        """
        if component and components:
            raise ValueError("Cannot specify both component and components")

        if embed and embeds:
            raise ValueError("Cannot specify both embed and embeds")

        self.content = content
        self.components = [component] if component else components
        self.delete_after = delete_after
        self.embeds = [embed] if embed else embeds
        self.mentions_everyone = mentions_everyone
        self.role_mentions = role_mentions
        self.user_mentions = user_mentions

    def __str__(self) -> str:
        return self.content or ""

    @typing.overload
    async def send(self, ctx: tanjun.Context, /, *, ensure_result: typing.Literal[True]) -> hikari.Message:
        ...

    @typing.overload
    async def send(self, ctx: tanjun.Context, /, *, ensure_result: bool = False) -> typing.Optional[hikari.Message]:
        ...

    async def send(self, ctx: tanjun.Context, /, *, ensure_result: bool = False) -> typing.Optional[hikari.Message]:
        return await ctx.respond(
            content=self.content,
            components=self.components,
            delete_after=self.delete_after,
            embeds=self.embeds,
            ensure_result=ensure_result,
            mentions_everyone=self.mentions_everyone,
            role_mentions=self.role_mentions,
            user_mentions=self.user_mentions,
        )


# TODO: use this
class InvalidCheck(TanjunError, RuntimeError):  # TODO: or/and warning?  # TODO: InvalidCheckError
    """Error raised as an assertion that a check will never pass in the current environment."""


class FailedCheck(TanjunError, RuntimeError):  # TODO: FailedCheckError
    """Error raised as an alternative to returning `False` in a check."""


class ParserError(TanjunError, ValueError):
    """Base error raised by a parser or parameter during parsing.

    !!! note
        Expected errors raised by the parser will subclass this error.
    """

    message: str
    """String message for this error.

    !!! note
        This may be used as a command response message.
    """

    parameter: typing.Optional[str]
    """Name of the this was raised for.

    !!! note
        This will be [None][] if it was raised while parsing the
        provided message content.
    """

    def __init__(self, message: str, parameter: typing.Optional[str], /) -> None:
        """Initialise a parser error.

        Parameters
        ----------
        message
            String message for this error.
        parameter
            Name of the parameter which caused this error, should be [None][]
            if not applicable.
        """
        self.message = message
        self.parameter = parameter

    def __str__(self) -> str:
        return self.message


class ConversionError(ParserError):
    """Error raised by a parser parameter when it failed to converter a value."""

    errors: collections.Sequence[ValueError]
    """Sequence of the errors that were caught during conversion for this parameter."""

    parameter: str
    """Name of the parameter this error was raised for."""

    def __init__(self, message: str, parameter: str, /, errors: collections.Iterable[ValueError] = ()) -> None:
        """Initialise a conversion error.

        Parameters
        ----------
        parameter
            The parameter this was raised by.
        errors
            An iterable of the source value errors which were raised during conversion.
        """
        super().__init__(message, parameter)
        self.errors = tuple(errors)


class NotEnoughArgumentsError(ParserError):
    """Error raised by the parser when not enough arguments are found for a parameter."""

    parameter: str
    """Name of the parameter this error was raised for."""

    def __init__(self, message: str, parameter: str, /) -> None:
        """Initialise a not enough arguments error.

        Parameters
        ----------
        message
            The error message.
        parameter
            The parameter this error was raised for.
        """
        super().__init__(message, parameter)


class TooManyArgumentsError(ParserError):
    """Error raised by the parser when too many arguments are found for a parameter."""

    parameter: str
    """Name of the parameter this error was raised for."""

    def __init__(self, message: str, parameter: str, /) -> None:
        """Initialise a too many arguments error.

        Parameters
        ----------
        message
            The error message.
        parameter
            The parameter this error was raised for.
        """
        super().__init__(message, parameter)


class ModuleMissingLoaders(RuntimeError, TanjunError):
    """Error raised when a module is missing loaders or unloaders."""

    def __init__(self, message: str, path: typing.Union[str, pathlib.Path], /) -> None:
        self._message = message
        self._path = path

    @property
    def message(self) -> str:
        """The error message."""
        return self._message

    @property
    def path(self) -> typing.Union[str, pathlib.Path]:
        """The path of the module which is missing loaders or unloaders."""
        return self._path


class ModuleStateConflict(ValueError, TanjunError):
    """Error raised when a module cannot be (un)loaded due to a state conflict."""

    def __init__(self, message: str, path: typing.Union[str, pathlib.Path], /) -> None:
        self._message = message
        self._path = path

    @property
    def message(self) -> str:
        """The error message."""
        return self._message

    @property
    def path(self) -> typing.Union[str, pathlib.Path]:
        """The path of the module which caused the error."""
        return self._path


class FailedModuleLoad(TanjunError):
    """Error raised when a module fails to load.

    This may be raised by the module failing to import or by one of
    its loaders erroring.

    This source error can be accessed at
    [FailedModuleLoad.__cause__][tanjun.errors.FailedModuleLoad.__cause__].
    """

    __cause__: Exception
    """The root error."""


class FailedModuleUnload(TanjunError):
    """Error raised when a module fails to unload.

    This may be raised by the module failing to import or by one
    of its unloaders erroring.

    The source error can be accessed at
    [FailedModuleUnload.__cause__][tanjun.errors.FailedModuleUnload.__cause__].
    """

    __cause__: Exception
    """The root error."""
