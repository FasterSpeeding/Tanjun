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
"""Parameter annotation based strategy for declaring slash and message command arguments.

Community Resources:

* An alternative implementation which relies more on documentation parsing
  can be found at <https://github.com/thesadru/tanchi>.
"""
from __future__ import annotations

__all__: list[str] = [
    "Attachment",
    "Bool",
    "Channel",
    "Choices",
    "Converted",
    "Describe",
    "Float",
    "Int",
    "Max",
    "Member",
    "Mentionable",
    "Min",
    "Name",
    "Ranged",
    "Role",
    "Str",
    "TheseChannels",
    "User",
    "with_annotated_args",
]

import enum
import operator
import sys
import types
import typing
from collections import abc as collections

import hikari

from . import abc as tanjun
from . import conversion
from . import parsing
from ._vendor import inspect
from .commands import menu
from .commands import message
from .commands import slash

if sys.version_info >= (3, 10):
    _UnionTypes = frozenset((typing.Union, types.UnionType))

else:
    _UnionTypes = frozenset((typing.Union,))

_T = typing.TypeVar("_T")
_ChannelTypeIsh = typing.Union[type[hikari.PartialChannel], int]
_ChoiceT = typing.TypeVar("_ChoiceT", int, float, str)
_ChoiceUnion = typing.Union[int, float, str]
_CommandUnion = typing.Union[slash.SlashCommand[typing.Any], message.MessageCommand[typing.Any]]
_CommandUnionT = typing.TypeVar("_CommandUnionT", bound=_CommandUnion)
_ConverterSig = typing.Union[
    collections.Callable[[str], collections.Coroutine[typing.Any, typing.Any, _T]],
    collections.Callable[[str], _T],
]
_EnumT = typing.TypeVar("_EnumT", bound=enum.Enum)
_MentionableUnion = typing.Union[hikari.User, hikari.Role]
_NumberT = typing.TypeVar("_NumberT", float, int)

_OPTION_MARKER = object()

Attachment = typing.Annotated[hikari.Attachment, _OPTION_MARKER]
"""An argument which accepts a file.

!!! warning
    This is currently only supported for slash commands.
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


class _TheseChannelsMeta(type):
    def __getitem__(
        cls, value: typing.Union[_ChannelTypeIsh, collections.Collection[_ChannelTypeIsh]], /
    ) -> type[hikari.PartialChannel]:
        if not isinstance(value, typing.Collection):
            value = (value,)

        return typing.Annotated[hikari.PartialChannel, TheseChannels(*value), _OPTION_MARKER]


class TheseChannels(metaclass=_TheseChannelsMeta):
    __slots__ = ("_channel_types",)

    def __init__(
        self,
        channel_type: _ChannelTypeIsh,
        /,
        *other_types: _ChannelTypeIsh,
    ) -> None:
        self._channel_types = (channel_type, *other_types)

    @property
    def channel_types(self) -> collections.Sequence[_ChannelTypeIsh]:
        return self._channel_types


class _MaxMeta(type):
    def __getitem__(cls, value: _NumberT, /) -> type[_NumberT]:
        type_ = type(value)
        return typing.Annotated[type_, Max(value), _OPTION_MARKER]


class Max(metaclass=_MaxMeta):
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

    Alternatively, the slice syntax and `range` may be used to set the min and
    max values for a float or integesr arguments (where the start is inclusive
    and stop is exclusive). These default to a min_value of `0` if the start
    isn't specified.

    ```py
    @annotations.with_annotated_args
    @tanjun.as_slash_command("meow", "description")
    async def command(
        ctx: tanjun.abc.SlashContext,
        float_value: Annotated[annotations.Float, 1.5:101.5],
        int_value: Annotated[annotations.Int, range(5, 100)],
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


class _MinMeta(type):
    def __getitem__(cls, value: _NumberT, /) -> type[_NumberT]:
        type_ = type(value)
        return typing.Annotated[type_, Min(value), _OPTION_MARKER]


class Min(metaclass=_MinMeta):
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

    Alternatively, the slice syntax and `range` may be used to set the min and
    max values for a float or integesr arguments (where the start is inclusive
    and stop is exclusive). These default to a min_value of `0` if the start
    isn't specified.

    ```py
    @annotations.with_annotated_args
    @tanjun.as_slash_command("meow", "description")
    async def command(
        ctx: tanjun.abc.SlashContext,
        float_value: Annotated[annotations.Float, 1.5:101.5],
        int_value: Annotated[annotations.Int, range(5, 100)],
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


class _RangedMeta(type):
    def __getitem__(cls, range_: tuple[_NumberT, _NumberT], /) -> type[_NumberT]:
        # This better matches how type checking (well pyright at least) will
        # prefer to go to float if either value is float.
        type_ = type(range_[0]) if issubclass(type(range_[0]), float) else type(range_[1])
        return typing.Annotated[type_, Ranged(range_[0], range_[1]), _OPTION_MARKER]


class Ranged(metaclass=_RangedMeta):
    __slots__ = ("_max_value", "_min_value")

    def __init__(self, min_value: typing.Union[int, float], max_value: typing.Union[int, Float], /) -> None:
        self._max_value = max_value
        self._min_value = min_value

    @property
    def max_value(self) -> typing.Union[int, float]:
        return self._max_value

    @property
    def min_value(self) -> typing.Union[int, float]:
        return self._min_value


class _TypeOverride:
    __slots__ = ("_override",)

    def __init__(self, override: type[typing.Any], /) -> None:
        self._override = override

    @property
    def override(self) -> type[typing.Any]:
        return self._override


class _ChoicesMeta(type):
    def __getitem__(cls, enum_: type[_EnumT], /) -> type[_EnumT]:
        if issubclass(enum_, int):
            type_ = int

        elif issubclass(enum_, str):
            type_ = str

        elif issubclass(enum_, float):
            type_ = float

        else:
            raise ValueError("Enum must be a subclsas of str, float or int")

        # TODO: do we want to wrap the convert callback to give better failed parse messages?
        return typing.Annotated[enum_, Choices(enum_.__members__), Converted(enum_), _TypeOverride(type_)]


class Choices(metaclass=_ChoicesMeta):
    """Assign up to 25 choices for a slash command option.

    !!! warning
        This is currently ignored for message commands and is only
        valid for string, integer and float options.

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


class _ConvertedMeta(type):
    def __getitem__(cls, converters: typing.Union[_ConverterSig[_T], tuple[_ConverterSig[_T]]], /) -> type[_T]:
        if not isinstance(converters, tuple):
            converters = (converters,)

        return typing.Annotated[typing.Any, Converted(*converters)]


class Converted(metaclass=_ConvertedMeta):
    """Marked an argument as type [Str][] with converters.

    Examples
    --------
    ```py
    @annotations.with_annotated_args
    @tanjun.as_slash_command("beep", "boop")
    async def command(
        ctx: tanjun.abc.SlashContext,
        value: Converted[callback, other_callback],
    )
    ```
    """

    __slots__ = ("_converters",)

    def __init__(self, converter: _ConverterSig[typing.Any], /, *other_converters: _ConverterSig[typing.Any]) -> None:
        """Create a converted instance.

        Parameters
        ----------
        converter : collections.abc.Callable
            The first converter this argument should use to handle values passed to it
            during parsing.

            Only the first converter to pass will be used.
        *other_converters : collections.abc.Callable
            Other first converter(s) this argument should use to handle values passed to it
            during parsing.

            Only the first converter to pass will be used.
        """
        self._converters = [converter, *other_converters]

    @property
    def converters(self) -> collections.Sequence[_ConverterSig[typing.Any]]:
        """A sequence of the converters."""
        return self._converters


class _DescribeMeta(type):
    def __getitem__(cls, values: tuple[type[_T], str], /) -> type[_T]:
        type_ = values[0]
        return typing.Annotated[type_, values[1]]


class Describe(metaclass=_DescribeMeta):
    __slots__ = ()


class Name:
    __slots__ = ("_message_names", "_slash_name")

    def __init__(
        self,
        both: typing.Optional[str] = None,
        /,
        *,
        message: typing.Union[typing.Optional[str], collections.Sequence[str]] = None,
        slash: typing.Optional[str] = None,
    ) -> None:
        if message and isinstance(message, str):
            message = [message]

        elif both and not message:
            message = "--" + both.replace("_", "-")

        self._message_names = message
        self._slash_name = slash or both

    @property
    def message_names(self) -> typing.Optional[collections.Sequence[str]]:
        return self._message_names

    @property
    def slash_name(self) -> typing.Optional[str]:
        return self._slash_name


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


_OPTION_TYPE_TO_CONVERTERS: dict[type[typing.Any], _ConverterSig[typing.Any]] = {
    # hikari.Attachment: NotImplemented,
    bool: (conversion.to_bool,),
    hikari.PartialChannel: (conversion.to_channel,),
    float: (float,),
    int: (int,),
    hikari.Member: (conversion.to_member,),
    _MentionableUnion: (conversion.to_user, conversion.to_role),
    hikari.Role: (conversion.to_role,),
    str: (),
    hikari.User: (conversion.to_user,),
}


class _ArgConfig:
    __slots__ = (
        "aliases",
        "channel_types",
        "choices",
        "converters",
        "custom_aliases",
        "default",
        "description",
        "key",
        "max_value",
        "message_names",
        "min_value",
        "option_type",
        "slash_name",
    )

    def __init__(self, key: str, default: typing.Any, /) -> None:
        self.aliases: typing.Optional[collections.Sequence[str]] = None
        self.channel_types: typing.Optional[collections.Sequence[_ChannelTypeIsh]] = None
        self.choices: typing.Optional[collections.Mapping[str, _ChoiceUnion]] = None
        self.converters: typing.Optional[collections.Sequence[_ConverterSig[typing.Any]]] = None
        self.custom_aliases = False
        self.default = default
        self.description: typing.Optional[str] = None
        self.key = key
        self.max_value: typing.Union[float, int, None] = None
        self.message_names: collections.Sequence[str] = ["--" + key.replace("_", "-")]
        self.min_value: typing.Union[float, int, None] = None
        self.option_type: typing.Optional[type[typing.Any]] = None
        self.slash_name = key

    def to_message_option(self, command: message.MessageCommand[typing.Any], /) -> None:
        if self.converters:
            converters = self.converters

        elif self.option_type:
            converters = _OPTION_TYPE_TO_CONVERTERS[self.option_type]

        else:
            return

        if command.parser:
            if not isinstance(command.parser, parsing.AbstractOptionParser):
                raise TypeError("Expected parser to be an instance of tanjun.parsing.AbstractOptionParser")

            parser = command.parser

        else:
            parser = parsing.ShlexParser()
            command.set_parser(parser)

        if self.default is inspect.Parameter.empty and not self.custom_aliases:  # TODO: stick with this?
            parser.add_argument(
                self.key,
                converters=converters,
                min_value=self.min_value,
                max_value=self.max_value,
            )

        else:
            parser.add_option(
                self.key,
                *self.message_names,
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
        hikari.Attachment: lambda self, c, d: c.add_attachment_option(
            self.slash_name, d, default=self._slash_default(), key=self.key
        ),
        bool: lambda self, c, d: c.add_bool_option(self.slash_name, d, default=self._slash_default(), key=self.key),
        hikari.PartialChannel: lambda self, c, d: c.add_channel_option(
            self.slash_name, d, default=self._slash_default(), key=self.key, types=self.channel_types
        ),
        float: lambda self, c, d: c.add_float_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", float, self.choices),
            default=self._slash_default(),
            key=self.key,
            min_value=self.min_value,  # TODO: explicitly cast to float?
            max_value=self.max_value,
        ),
        int: lambda self, c, d: c.add_int_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", int, self.choices),
            default=self._slash_default(),
            key=self.key,
            min_value=_ensure_value("min", int, self.min_value),
            max_value=_ensure_value("max", int, self.max_value),
        ),
        hikari.Member: lambda self, c, d: c.add_member_option(
            self.slash_name, d, default=self._slash_default(), key=self.key
        ),
        _MentionableUnion: lambda self, c, d: c.add_mentionable_option(
            self.slash_name, d, default=self._slash_default(), key=self.key
        ),
        hikari.Role: lambda self, c, d: c.add_role_option(
            self.slash_name, d, default=self._slash_default(), key=self.key
        ),
        str: lambda self, c, d: c.add_str_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", str, self.choices),
            converters=self.converters or (),
            default=self._slash_default(),
            key=self.key,
        ),
        hikari.User: lambda self, c, d: c.add_user_option(
            self.slash_name, d, default=self._slash_default(), key=self.key
        ),
    }


def _parse_type(type_: typing.Any) -> typing.Any:
    if typing.get_origin(type_) not in _UnionTypes or type_ == _MentionableUnion:
        return type_

    for sub_type in typing.get_args(type_):
        if typing.get_origin(sub_type) is not typing.Annotated:
            continue

        args = typing.get_args(sub_type)
        if _OPTION_MARKER in args:
            return args[0]

    return type_


def _collect_wrapped(
    command: typing.Union[
        menu.MenuCommand[typing.Any, typing.Any], message.MessageCommand[typing.Any], slash.SlashCommand[typing.Any]
    ]
) -> list[tanjun.ExecutableCommand[typing.Any]]:
    results: list[tanjun.ExecutableCommand[typing.Any]] = []
    wrapped_command = command.wrapped_command

    while wrapped_command:
        results.append(wrapped_command)
        wrapped_command = command.wrapped_command

    return results


def _annotated_args(command: _CommandUnionT, /, *, follow_wrapped: bool = False) -> _CommandUnionT:  # noqa: C901
    try:
        signature = inspect.signature(command.callback, follow_wrapped=True)
    except ValueError:  # If we can't inspect it then we have to assume this is a NO
        # As a note, this fails on some "signature-less" builtin functions/types like str.
        return command

    message_commands: list[message.MessageCommand[typing.Any]] = []
    slash_commands: list[slash.SlashCommand[typing.Any]] = []

    if isinstance(command, slash.SlashCommand):
        slash_commands.append(command)
    else:
        message_commands.append(command)

    if follow_wrapped:
        for sub_command in _collect_wrapped(command):
            if isinstance(sub_command, message.MessageCommand):
                message_commands.append(sub_command)

            elif isinstance(sub_command, slash.SlashCommand):
                slash_commands.append(sub_command)

    for parameter in signature.parameters.values():
        if parameter.annotation is parameter.empty or typing.get_origin(parameter.annotation) is not typing.Annotated:
            continue

        arg_config = _ArgConfig(parameter.name, parameter.default)
        args = typing.get_args(parameter.annotation)
        for arg in args[1:]:
            # Ignore this if a TypeOveride is found as it takes priority.
            if arg is _OPTION_MARKER and arg_config.option_type is None:
                arg_config.option_type = _parse_type(args[0])

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

            elif isinstance(arg, Name):
                arg_config.slash_name = arg.slash_name or arg_config.slash_name
                if arg.message_names is not None:
                    arg_config.message_names = arg.message_names
                    arg_config.custom_aliases = True

            elif isinstance(arg, (range, slice)):
                # Slice's attributes are all Any so we need to cast to int.
                if arg.step is None or operator.index(arg.step) > 0:
                    arg_config.min_value, arg_config.max_value = _slice_to_min_max(arg)

            elif isinstance(arg, TheseChannels):
                arg_config.channel_types = arg.channel_types

            elif isinstance(arg, _TypeOverride):
                arg_config.option_type = arg.override

        for slash_command in slash_commands:
            arg_config.to_slash_option(slash_command)

        for message_command in message_commands:
            arg_config.to_message_option(message_command)

    return command


@typing.overload
def with_annotated_args(command: _CommandUnionT, /) -> _CommandUnionT:
    ...


@typing.overload
def with_annotated_args(*, follow_wrapped: bool = False) -> collections.Callable[[_CommandUnionT], _CommandUnionT]:
    ...


def with_annotated_args(
    command: typing.Optional[_CommandUnionT] = None, /, *, follow_wrapped: bool = False
) -> typing.Union[_CommandUnionT, collections.Callable[[_CommandUnionT], _CommandUnionT]]:
    """Set a command's arguments based on its signature.

    To declare arguments a you will have to do one of two things:

    1. Using any of the following types as an argument's type-hint (this may be
        as the first argument to [typing.Annotated][]) will mark it as injected:

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
        @tanjun.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("name")
        @tanjun.as_slash_command("name", "description")
        async def command(
            ctx: tanjun.abc.SlashContext,

            # Here the option's description is passed as a string to Annotated:
            # this is necessary for slash commands but ignored for message commands.
            name: Annotated[Str, "The character's name"],

            # `= False` declares this field as optional, with it defaulting to `False`
            # if not specified.
            lawyer: Annotated[Bool, "Whether they're a lawyer"] = False,
        ) -> None:
            raise NotImplementedError
        ```

    2. By passing [tanjun.annotations.Converted][] as one of the other arguments to
        [typing.Annotated][] to declare it as a string option with converters.

        ```py
        @tanjun.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("e")
        @tanjun.as_slash_command("e", "description")
        async def command(
            ctx: tanjun.abc.SlashContext,
            value: Annotated[Converted[CustomType.from_str]],
        ) -> None:
            raise NotImplementedError
        ```

        or

        ```py
        @tanjun.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("e")
        @tanjun.as_slash_command("e", "description")
        async def command(
            ctx: tanjun.abc.SlashContext,
            value: Annotated[OtherType, Converted(parse_value)],
        ) -> None:
            raise NotImplementedError
        ```

    It should be noted that wrapping in [typing.Annotated][] isn't necessary for
    message commands options as they don't have descriptions.

    ```py
    async def message_command(
        ctx: tanjun.abc.MessageContext,
        name: Str,
        enable: typing.Optional[Bool] = None,
    ) -> None:
        ...
    ```

    Parameters
    ----------
    command : tanjun.SlashCommand | tanjun.MessageCommand
        The message or slash command to set the arguments for.
    follow_wrapped
        Whether this should also set the arguments for any command objects
        `command` wraps.

    Returns
    -------
    tanjun.SlashCommand | tanjun.MessageCommand
        The command object to enable using this as a decorator.
    """
    if not command:
        return lambda c: _annotated_args(c, follow_wrapped=follow_wrapped)

    return _annotated_args(command, follow_wrapped=follow_wrapped)


def _slice_to_min_max(
    value: typing.Union[range, slice], /
) -> tuple[typing.Union[int, float], typing.Union[int, float]]:
    # Slice's attributes are all Any so we need to cast to int.
    if value.step is None or operator.index(value.step) > 0:
        min_value = operator.index(value.start) if value.start is not None else 0
        max_value = operator.index(value.stop) - 1
    else:
        # start will have to have been specified for this to be reached.
        min_value = operator.index(value.stop) - 1
        max_value = operator.index(value.start)

    return min_value, max_value
