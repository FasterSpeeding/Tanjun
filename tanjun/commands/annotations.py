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
"""Parameter annotation based strategy for declaring command arguments.

Community Resources:
* An alternative implementation which relies more on documentation parsing
  can be found at https://github.com/thesadru/tanchi.
"""
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

_ChoiceUnion = typing.Union[int, float, str]
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
"""An argument which accepts a file.

!!! warning
    Currently, this is only supported for slash commands.
"""

Bool = typing.Annotated[bool, _OPTION_MARKER]
"""An argument which takes a bool-like value."""

Channel = typing.Annotated[hikari.PartialChannel, _OPTION_MARKER]
"""An argument which takes a channel."""

Float = typing.Annotated[float, _OPTION_MARKER]
"""An argument which takes a floating point number."""

Int = typing.Annotated[int, _OPTION_MARKER]
"""An argument which takes an integer."""

Member = typing.Annotated[hikari.Member, _OPTION_MARKER]
"""An argument which takes a guild member."""

Mentionable = typing.Annotated[typing.Union[hikari.User, hikari.Role], _OPTION_MARKER]
"""An argument which takes a user or role."""

Role = typing.Annotated[hikari.Role, _OPTION_MARKER]
"""An argument which takes a role."""

Str = typing.Annotated[str, _OPTION_MARKER]
"""An argument which takes string input."""

User = typing.Annotated[hikari.User, _OPTION_MARKER]
"""An argument which takes a user."""


class Max:
    """Inclusive maximum value for a [Float][] or [Int][] argument.

    Examples
    --------
    ```py
    @annotations.with_annotated_args
    @tanjun.as_slash_command("beep", "meow")
    async def command(
        ctx: tanjun.abc.Context,
        age: Annotated[annotations.Int, Max(130), Min(13)],
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ("_value",)

    def __init__(self, value: typing.Union[int, float], /) -> None:
        self._value = value

    @property
    def value(self) -> typing.Union[int, float]:
        """The maximum value."""
        return self._value


class Min:
    """Inclusive minimum value for a [Float][] or [Int][] argument.

    Examples
    --------
    ```py
    @annotations.with_annotated_args
    @tanjun.as_slash_command("beep", "meow")
    async def command(
        ctx: tanjun.abc.Context,
        age: Annotated[annotations.Int, "How old are you?", Max(130), Min(13)],
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ("_value",)

    def __init__(self, value: typing.Union[int, float], /) -> None:
        self._value = value

    @property
    def value(self) -> typing.Union[int, float]:
        """The minimum value."""
        return self._value


class Choices:
    """Assign up to 25 choices for a slash command option.

    !!! warning
        This is currently ignored for message commands.

    Examples
    --------
    ```py
    @annotations.with_annotated_args
    @tanjun.as_slash_command("beep", "meow")
    async def command(
        ctx: tanjun.abc.Context,
        location: Annotated[annotations.Int, "where do you live?", Choices("London", "Paradise", "Nowhere")]
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ("_choices",)

    def __init__(
        self,
        mapping: typing.Union[
            collections.Mapping[str, _ChoiceT],
            collections.Sequence[tuple[str, _ChoiceT]],
            collections.Sequence[_ChoiceT],
        ] = (),
        /,
        **kwargs: _ChoiceT,
    ) -> None:
        """Create a choices instance.

        Parameters
        ----------
        mapping
            Either a mapping of names to the choices values or a sequence
            of `tuple[name, value]` or a sequence of string values.
        """
        if isinstance(mapping, collections.Sequence):
            mapping_ = (value if isinstance(value, tuple) else (str(value), value) for value in mapping)

        else:
            mapping_ = mapping

        self._choices: dict[str, _ChoiceUnion] = dict(mapping_, **kwargs)

    @property
    def choices(self) -> collections.Mapping[str, _ChoiceUnion]:
        """Mapping of up to 25 choices for the slash command option."""
        return self._choices


class Converted:
    """Marked an argument as type [Str][] with converters."""

    __slots__ = ("_converters",)

    def __init__(self, converter: _ConverterSig, /, *other_converters: _ConverterSig) -> None:
        """Create a converted instance.

        Parameters
        ----------
        converter
            The first converter this argument should use to handle values passed to it
            during parsing.

            Only the first converter to pass will be used.
        other_converters
            Other first converter(s) this argument should use to handle values passed to it
            during parsing.

            Only the first converter to pass will be used.
        """
        self._converters = [converter, *other_converters]

    @property
    def converters(self) -> collections.Sequence[_ConverterSig]:
        """A sequence of the converters."""
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
    str: (),
    hikari.User: (conversion.to_user,),
}


@dataclasses.dataclass
class _ArgConfig:
    name: str
    default: typing.Any
    channel_types: typing.Optional[list[type[hikari.PartialChannel]]] = None
    choices: typing.Optional[collections.Mapping[str, _ChoiceUnion]] = None
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
    """Set a command's arguments based on its signature.

    To declare arguments a you will have to do one of two things:

    1. Using any of the following types as an argument's type-hint (this may be
        the first argument to [typing.Annotated][]) will mark it as injected:

        * [tanjun.annotations.Bool][]
        * [tanjun.annotations.Channel][]
        * [tanjun.annotations.Float][]
        * [tanjun.annotations.Int][]
        * [tanjun.annotations.Member][]
        * [tanjun.annotations.Mentionable][]
        * [tanjun.annotations.Role][]
        * [tanjun.annotations.Str][]
        * [tanjun.annotations.User][]

    ```py
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.SlashContext,

        # Here the option's descrition is passed as a string to Annotated,
        # this is neccessary for slash commands but ignored for message commands.
        name: Annotated[Str, "The character's name"],

        # `= False` declares this field as optional, with it defaulting to `False`
        # if not specified.
        lawyer: Annotated[Bool, "Whether they're a lawyer"] = False,
    ) -> None:
        raise NotImplementedError
    ```

    2. By passing [tanjun.annotations.Converted][] as one of the other arguments to
        [typing.Annotaed][] to declare it as a string option with converters.

    ```py
    async def command(
        ctx: tanjun.abc.SlashContext,
        value: Annotated[CustomType, Converted(CustomType.from_str)],
    ) -> None:
        raise NotImplementedError
    ```

    It should be noted that wrapping in [typing.Annotated][] isn't neccesary for
    message commands as message command arguments don't have descriptions.

    ```py
    async def message_command(
        ctx: tanjun.abc.MessageContext,
        enable: typing.Optional[Bool] = None,
        name: typing.Optional[Str] = None,
    ) -> None:
        ...
    ```

    Parameters
    ----------
    command : tanjun.SlashCommand | tanjun.MessageCommand
        The message or slash command to set the arguments for.

    Returns
    -------
    tanjun.SlashCommand | tanjun.MessageCommand
        The command object to enable using this as a decorator.
    """
    try:
        signature = inspect.signature(command.callback, follow_wrapped=True)
    except ValueError:  # If we can't inspect it then we have to assume this is a NO
        # As a note, this fails on some "signature-less" builtin functions/types like str.
        return command

    is_slash = isinstance(command, slash.SlashCommand)

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

        if is_slash:
            assert isinstance(command, slash.SlashCommand)
            arg_config.to_slash_option(command)

        else:
            assert isinstance(command, message.MessageCommand)
            arg_config.to_message_option(command)

    return command
