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

* An alternative implementation for slash commands (which relies more on
  documentation parsing) can be found at <https://github.com/thesadru/tanchi>.
"""
from __future__ import annotations

__all__: list[str] = [
    "Attachment",
    "Bool",
    "Channel",
    "Choices",
    "Color",
    "Colour",
    "Converted",
    "Datetime",
    "Default",
    "Flag",
    "Float",
    "Greedy",
    "Int",
    "Length",
    "Max",
    "Member",
    "Mentionable",
    "Min",
    "Name",
    "Positional",
    "Ranged",
    "Role",
    "Snowflake",
    "SnowflakeOr",
    "Str",
    "TheseChannels",
    "User",
    "with_annotated_args",
]

import abc
import enum
import itertools
import operator
import sys
import types
import typing
import warnings
from collections import abc as collections

import hikari

from . import _internal
from . import conversion
from . import parsing
from ._internal.vendor import inspect
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


class _ConfigIdentifier(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def set_config(self, config: _ArgConfig, /) -> None:
        raise NotImplementedError


class _OptionMarker(_ConfigIdentifier):
    __slots__ = ("_type",)

    def __init__(self, type_: typing.Any, /) -> None:
        self._type = type_

    @property
    def type(self) -> typing.Any:
        return self._type

    def set_config(self, config: _ArgConfig, /) -> None:
        # Ignore this if a TypeOveride has been found as it takes priority.
        if config.option_type is None:
            config.option_type = self._type


Attachment = typing.Annotated[hikari.Attachment, _OptionMarker(hikari.Attachment)]
"""An argument which accepts a file.

!!! warning
    This is currently only supported for slash commands.
"""

Bool = typing.Annotated[bool, _OptionMarker(bool)]
"""An argument which takes a bool-like value."""

Channel = typing.Annotated[hikari.PartialChannel, _OptionMarker(hikari.PartialChannel)]
"""An argument which takes a channel."""

Float = typing.Annotated[float, _OptionMarker(float)]
"""An argument which takes a floating point number."""

Int = typing.Annotated[int, _OptionMarker(int)]
"""An argument which takes an integer."""

Member = typing.Annotated[hikari.Member, _OptionMarker(hikari.Member)]
"""An argument which takes a guild member."""

Mentionable = typing.Annotated[typing.Union[hikari.User, hikari.Role], _OptionMarker(_MentionableUnion)]
"""An argument which takes a user or role."""

Role = typing.Annotated[hikari.Role, _OptionMarker(hikari.Role)]
"""An argument which takes a role."""

Str = typing.Annotated[str, _OptionMarker(str)]
"""An argument which takes string input."""

User = typing.Annotated[hikari.User, _OptionMarker(hikari.User)]
"""An argument which takes a user."""


class _ChoicesMeta(abc.ABCMeta):
    def __getitem__(cls, enum_: type[_EnumT], /) -> type[_EnumT]:
        if issubclass(enum_, int):
            type_ = int
            choices = Choices(enum_.__members__)

        elif issubclass(enum_, str):
            type_ = str
            choices = Choices(enum_.__members__)

        elif issubclass(enum_, float):
            type_ = float
            choices = Choices(enum_.__members__)

        else:
            raise ValueError("Enum must be a subclsas of str, float or int")

        # TODO: do we want to wrap the convert callback to give better failed parse messages?
        return typing.cast(type[_EnumT], typing.Annotated[enum_, choices, Converted(enum_), _TypeOverride(type_)])


class Choices(_ConfigIdentifier, metaclass=_ChoicesMeta):
    """Assign up to 25 choices for a slash command option.

    !!! warning
        This is currently ignored for message commands and is only
        valid for string, integer and float options.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("beep", "meow")
    async def command(
        ctx: tanjun.abc.Context,
        location: Annotated[Int, "where do you live?", Choices("London", "Paradise", "Nowhere")],
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
            of `tuple[name, value]` or a sequence of choice values.
        **kwargs
            Choice values.
        """
        if isinstance(mapping, collections.Sequence):
            self._choices: dict[str, _ChoiceUnion] = dict(
                (value if isinstance(value, tuple) else (str(value), value) for value in mapping), **kwargs
            )

        else:
            self._choices = dict(mapping, **kwargs)

    @property
    def choices(self) -> collections.Mapping[str, _ChoiceUnion]:
        """Mapping of up to 25 choices for the slash command option."""
        return self._choices

    def set_config(self, config: _ArgConfig, /) -> None:
        config.choices = self._choices


class _ConvertedMeta(abc.ABCMeta):
    def __getitem__(cls, converters: typing.Union[_ConverterSig[_T], tuple[_ConverterSig[_T]]], /) -> type[_T]:
        if not isinstance(converters, tuple):
            converters = (converters,)

        return typing.Annotated[typing.Any, Converted(*converters)]


class Converted(_ConfigIdentifier, metaclass=_ConvertedMeta):
    """Marked an argument as type [Str][tanjun.annotations.Str] with converters.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("beep", "boop")
    async def command(
        ctx: tanjun.abc.SlashContext,
        argument: Annotated[Str, Converted(callback, other_callback), "description"]
        other_argument: Annotated[Converted[callback, other_callback], "description"],
    )
    ```
    """

    # Where `Converted[...]` follows the same semantics as Converted's `__init__`.

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

    def set_config(self, config: _ArgConfig, /) -> None:
        config.converters = self._converters


Color = Converted[conversion.to_color]
"""An argument which takes a color."""

Colour = Color
"""An argument which takes a colour."""

Datetime = Converted[conversion.to_datetime]
"""An argument which takes a datetime."""

Snowflake = Converted[conversion.parse_snowflake]
"""An argument which takes a snowflake."""


class _DefaultMeta(abc.ABCMeta):
    def __getitem__(cls, value: typing.Union[type[_T], tuple[type[_T], _T]], /) -> type[_T]:
        if isinstance(value, tuple):
            type_ = value[0]
            return typing.cast(type[_T], typing.Annotated[type_, Default(value[1])])

        type_ = typing.cast(type[_T], value)
        return typing.cast(type[_T], typing.Annotated[type_, Default()])


class Default(_ConfigIdentifier, metaclass=_DefaultMeta):
    """Explicitly configure an argument's default.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        argument: Annotated[Str, Default(""), "description"],
        other_argument: Annotated[Default[Str, ""], "description"],
    ) -> None:
        ...
    ```

    ```py
    @with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        required_argument: Annotated[Default[Str], "description"] = "yeet",
        other_required: Annotated[Int, Default(), "description"] = 123,
    ) -> None:
        ...
    ```

    Passing an empty [Default][tanjun.annotations.Default] allows you to mark
    an argument that's optional in the signature as being a required option.
    """

    __slots__ = ("_default",)

    def __init__(self, default: typing.Union[typing.Any, parsing.UndefinedT] = parsing.UNDEFINED, /) -> None:
        """Initialise a default.

        Parameters
        ----------
        default
            The argument's default.

            If left as [tanjun.parsing.UNDEFINED][] then the argument will be
            required regardless of the signature default.
        """
        self._default = default

    @property
    def default(self) -> typing.Union[typing.Any, parsing.UndefinedT]:
        """The option's default.

        This will override the default in the signature for this parameter.
        """
        return self._default

    def set_config(self, config: _ArgConfig, /) -> None:
        config.default = self._default


class Flag(_ConfigIdentifier):
    """Mark an argument as a flag/option for message command parsing.

    This indicates that the argument should be specified by name (e.g. `--name`)
    rather than positionally for message parsing and doesn't effect slash
    command options.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_message_command("message")
    async def command(
        ctx: tanjun.abc.MessageContext,
        flag_value: Annotated[Bool, Flag(empty_value=True, aliases=("-f",))] = False,
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ("_aliases", "_default", "_empty_value")

    def __init__(
        self,
        *,
        aliases: typing.Optional[collections.Sequence[str]] = None,
        default: typing.Union[typing.Any, parsing.UndefinedT] = parsing.UNDEFINED,
        empty_value: typing.Union[parsing.UndefinedT, typing.Any] = parsing.UNDEFINED,
    ) -> None:
        """Create a flag instance.

        Parameters
        ----------
        aliases
            Other names the flag may be triggered by.

            This does not override the argument's name.
        default
            Deprecated argument used to specify the option's default.

            Use [Default][tanjun.annotations.Default] instead.
        empty_value
            Value to pass for the argument if the flag is provided without a value.

            If left undefined then an explicit value will always be needed.
        """
        if default is not parsing.UNDEFINED:
            warnings.warn(
                "Flag.__init__'s `default` argument is deprecated, use Default instead", category=DeprecationWarning
            )

        self._aliases = aliases
        self._default = default
        self._empty_value = empty_value

    @property
    def aliases(self) -> typing.Optional[collections.Sequence[str]]:
        """The aliases set for this flag.

        These do not override the flag's name.
        """
        return self._aliases

    @property
    def default(self) -> typing.Union[typing.Any, parsing.UndefinedT]:
        """The flag's default.

        If not specified then the default in the signature for this argument
        will be used.
        """
        warnings.warn("Flag.default is deprecated", category=DeprecationWarning)
        return self._default

    @property
    def empty_value(self) -> typing.Union[parsing.UndefinedT, typing.Any]:
        """The value to pass for the argument if the flag is provided without a value.

        If this is undefined then a value will always need to be passed for the flag.
        """
        return self._empty_value

    def set_config(self, config: _ArgConfig, /) -> None:
        if self._default is not parsing.UNDEFINED:
            config.default = self._default

        config.aliases = self._aliases or config.aliases
        config.empty_value = self._empty_value
        config.is_positional = False


class _PositionalMeta(abc.ABCMeta):
    def __getitem__(cls, type_: type[_T], /) -> type[_T]:
        return typing.cast(type[_T], typing.Annotated[type_, Positional()])


class Positional(_ConfigIdentifier, metaclass=_PositionalMeta):
    """Mark an argument as being passed positionally for message command parsing.

    Arguments will be positional by default (unless it has a default) and this
    allows for marking positional arguments as optional.

    This only effects message option parsing.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_message_command("message")
    async def command(
        ctx: tanjun.abc.MessageContext,
        positional_arg: Positional[Str] = None,
        other_positional_arg: Annotated[Str, Positional()] = None,
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ()

    def __init__(self) -> None:
        """Create a positional instance."""

    def set_config(self, config: _ArgConfig, /) -> None:
        config.is_positional = True


class _GreedyMeta(abc.ABCMeta):
    def __getitem__(cls, type_: type[_T], /) -> type[_T]:
        return typing.cast(type[_T], typing.Annotated[type_, Greedy()])


class Greedy(_ConfigIdentifier, metaclass=_GreedyMeta):
    """Mark an argument as "greedy" for message command parsing.

    This means that it'll consume the rest of the positional arguments,
    can only be applied to one positional argument and is no-op for slash
    commands and flags.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_message_command("message")
    async def command(
        ctx: tanjun.abc.MessageContext,
        greedy_arg: Greedy[Str],
        other_greedy_arg: Annotated[Str, Greedy()],
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ()

    def set_config(self, config: _ArgConfig, /) -> None:
        config.is_greedy = True


class _LengthMeta(abc.ABCMeta):
    def __getitem__(cls, value: typing.Union[int, tuple[int, int]], /) -> type[str]:
        if isinstance(value, int):
            obj = Length(value)

        else:
            obj = Length(*value)

        return typing.Annotated[Str, obj]


class Length(_ConfigIdentifier, metaclass=_LengthMeta):
    """Define length restraints for a string option.

    !!! note
        Length constraints are applied before conversion for slash commands
        but after conversion for message commands.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("meow", "blam")
    async def command(
        ctx: tanjun.abc.Context,
        max_and_min: typing.Annotated[Str, Length(123, 321)],
        max_only: typing.Annotated[Str, Length(123)],
        generic_max_and_min: typing.Annotated[Length[5, 13], "meow"],
        generic_max_only: typing.Annotated[Length[21], "meow"],
    ) -> None:
        raise NotImplementedError
    ```

    where `Length[...]` follows the same semantics as Length's `__init__`.

    ```py
    @with_annotated_args
    @tanjun.as_slash_command("meow", "description")
    async def command(
        ctx: tanjun.abc.SlashContext,
        argument: Annotated[Str, range(5, 100), "description"],
        other_argument: Annotated[Str, 4:64, "description"],
    ) -> None:
        raise NotImplementedError
    ```

    Alternatively, the slice syntax and `range` may be used to set the length
    restraints for a string argument (where the start is inclusive and stop is
    exclusive). These default to a min_length of `0` if the start isn't
    specified and ignores any specified step.
    """

    __slots__ = ("_min_length", "_max_length")

    @typing.overload
    def __init__(self, max_length: int, /) -> None:
        ...

    @typing.overload
    def __init__(self, min_length: int, max_length: int, /) -> None:
        ...

    def __init__(self, min_or_max_length: int, max_length: typing.Optional[int] = None, /) -> None:
        """Initialise a length constraint.

        Parameters
        ----------
        min_or_max_length
            If `max_length` is left as [None][] then this will be used as the
            maximum length and the minimum length will be `0`.
        max_length
            The maximum length this string argument can be.

            If not specified then `min_or_max_length` will be used as the max
            length.
        """
        if max_length is None:
            self._min_length = 0
            self._max_length = min_or_max_length

        else:
            self._min_length = min_or_max_length
            self._max_length = max_length

    @property
    def min_length(self) -> int:
        """The minimum length of this string option."""
        return self._min_length

    @property
    def max_length(self) -> int:
        """The maximum length of this string option."""
        return self._max_length

    def set_config(self, config: _ArgConfig, /) -> None:
        config.min_length = self._min_length
        config.max_length = self._max_length


class _MaxMeta(abc.ABCMeta):
    def __getitem__(cls, value: _NumberT, /) -> type[_NumberT]:
        if isinstance(value, int):
            return typing.Annotated[Int, Max(value)]

        return typing.Annotated[Float, Max(value)]


class Max(_ConfigIdentifier, metaclass=_MaxMeta):
    """Inclusive maximum value for a [Float][tanjun.annotations.Float] or [Int][tanjun.annotations.Int] argument.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("beep", "meow")
    async def command(
        ctx: tanjun.abc.Context,
        age: Annotated[Int, Max(130), "How old are you?"],
        number: Annotated[Max[130.2], "description"],
    ) -> None:
        raise NotImplementedError
    ```

    The option's type will be inferred from the passed value when using
    [Max][tanjun.annotations.Max] as a generic type hint (e.g. `Max[18]`).
    """

    __slots__ = ("_value",)

    def __init__(self, value: typing.Union[int, float], /) -> None:
        """Create an argument maximum value.

        Parameters
        ----------
        value
            The maximum allowed value allowed for an argument.
        """
        self._value = value

    @property
    def value(self) -> typing.Union[int, float]:
        """The maximum allowed value."""
        return self._value

    def set_config(self, config: _ArgConfig, /) -> None:
        config.max_value = self._value


class _MinMeta(abc.ABCMeta):
    def __getitem__(cls, value: _NumberT, /) -> type[_NumberT]:
        if isinstance(value, int):
            return typing.Annotated[Int, Min(value)]

        return typing.Annotated[Float, Min(value)]


class Min(_ConfigIdentifier, metaclass=_MinMeta):
    """Inclusive minimum value for a [Float][tanjun.annotations.Float] or [Int][tanjun.annotations.Int] argument.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("beep", "meow")
    async def command(
        ctx: tanjun.abc.Context,
        age: Annotated[Int, Min(13), "How old are you?"],
        number: Annotated[Min[13.9], "description"],
    ) -> None:
        raise NotImplementedError
    ```

    The option's type is be inferred from the passed value when using
    [Min][tanjun.annotations.Min] as a generic type hint (e.g. `Min[69.4]`).
    """

    __slots__ = ("_value",)

    def __init__(self, value: typing.Union[int, float], /) -> None:
        """Create an argument minimum value.

        Parameters
        ----------
        value
            The minimum value allowed for an argument.
        """
        self._value = value

    @property
    def value(self) -> typing.Union[int, float]:
        """The minimum allowed  value."""
        return self._value

    def set_config(self, config: _ArgConfig, /) -> None:
        config.min_value = self._value


class Name(_ConfigIdentifier):
    """Override the inferred name used to declare an option.

    Examples
    --------
    ```py
    @with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("meow", "nyaa")
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context,
        resource_type: Annotated[Str, Name("type"), "The type of resource to get."],
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ("_message_name", "_slash_name")

    def __init__(
        self,
        both: typing.Optional[str] = None,
        /,
        *,
        message: typing.Optional[str] = None,
        slash: typing.Optional[str] = None,
    ) -> None:
        """Create an argument name override.

        Parameters
        ----------
        both
            If provided, the name to use for this option in message and slash
            commands.

            This will be reformatted a bit for message commands (prefixed with
            `--` and `.replace("_", "-")`) and is only used for message flag
            options.
        message
            The name to use for this option in message commands.

            This takes priority over `both`, is not reformatted and only is
            only used for flag options.
        slash
            The name to use for this option in slash commands.

            This takes priority over `both`.
        """
        if both and not message:
            message = "--" + both.replace("_", "-")

        self._message_name = message
        self._slash_name = slash or both

    @property
    def message_name(self) -> typing.Optional[str]:
        """The name to use for this option in message commands."""
        return self._message_name

    @property
    def slash_name(self) -> typing.Optional[str]:
        """The name to use for this option in slash commands."""
        return self._slash_name

    def set_config(self, config: _ArgConfig, /) -> None:
        config.slash_name = self._slash_name or config.slash_name
        config.message_name = self._message_name or config.message_name


class _RangedMeta(abc.ABCMeta):
    def __getitem__(cls, range_: tuple[_NumberT, _NumberT], /) -> type[_NumberT]:
        # This better matches how type checking (well pyright at least) will
        # prefer to go to float if either value is float.
        if isinstance(range_[0], float) or isinstance(range_[1], float):
            return typing.Annotated[Float, Ranged(range_[0], range_[1])]

        return typing.Annotated[Int, Ranged(range_[0], range_[1])]


class Ranged(_ConfigIdentifier, metaclass=_RangedMeta):
    """Declare the range limit for an `Int` or `Float` argument.

    Examples
    --------
    ```py
    @with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("meow", "nyaa")
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context,
        number_arg: Annotated[Int, Ranged(0, 69), "description"],
        other_number_arg: Annotated[Ranged[13.69, 420.69], "description"],
    ) -> None:
        raise NotImplementedError
    ```

    The option's type is inferred from whether integers or floats are passed
    when using [Ranged][tanjun.annotations.Ranged] as a generic type hint (e.g.
    `Ranged[123, 666]`).

    ```py
    @with_annotated_args
    @tanjun.as_slash_command("meow", "description")
    async def command(
        ctx: tanjun.abc.SlashContext,
        float_value: Annotated[Float, 1.5:101.5, "description"],
        int_value: Annotated[Int, range(5, 100), "description"],
    ) -> None:
        raise NotImplementedError
    ```

    Alternatively, the slice syntax and `range` may be used to set the range
    for a float or integer argument (where the start is inclusive and stop is
    exclusive). These default to a min_value of `0` if the start isn't
    specified and ignores any specified step.
    """

    __slots__ = ("_max_value", "_min_value")

    def __init__(self, min_value: typing.Union[int, float], max_value: typing.Union[int, Float], /) -> None:
        """Create an argument range limit.

        Parameters
        ----------
        min_value
            The minimum allowed value for this argument.
        max_value
            The maximum allowed value for this argument.
        """
        self._max_value = max_value
        self._min_value = min_value

    @property
    def max_value(self) -> typing.Union[int, float]:
        """The maximum allowed value for this argument."""
        return self._max_value

    @property
    def min_value(self) -> typing.Union[int, float]:
        """The minimum allowed value for this argument."""
        return self._min_value

    def set_config(self, config: _ArgConfig, /) -> None:
        config.max_value = self._max_value
        config.min_value = self._min_value


# _MESSAGE_ID_ONLY
_SNOWFLAKE_PARSERS: dict[type[typing.Any], collections.Callable[[str], hikari.Snowflake]] = {
    hikari.Member: conversion.parse_user_id,
    hikari.PartialChannel: conversion.parse_channel_id,
    hikari.User: conversion.parse_user_id,
    hikari.Role: conversion.parse_role_id,
}


class _SnowflakeOrMeta(abc.ABCMeta):
    def __getitem__(cls, type_: type[_T], /) -> type[typing.Union[hikari.Snowflake, _T]]:
        for entry in _snoop_annotation_args(type_):
            if not isinstance(entry, _OptionMarker):
                continue

            try:
                parser = _SNOWFLAKE_PARSERS[entry.type]

            except (KeyError, TypeError):  # Also catch unhashable
                pass

            else:
                descriptor = SnowflakeOr(parse_id=parser)
                break

        else:
            descriptor = SnowflakeOr()

        return typing.cast(
            type[typing.Union[hikari.Snowflake, _T]],
            typing.Annotated[typing.Union[hikari.Snowflake, type_], descriptor],
        )


class SnowflakeOr(_ConfigIdentifier, metaclass=_SnowflakeOrMeta):
    """Mark an argument as taking an object or its ID.

    This allows for the argument to be declared as taking the object for slash
    commands without requiring that the message command equivalent fetch the
    object each time for the following types:

    * [User][tanjun.annotations.User]
    * [Role][tanjun.annotations.Role]
    * [Member][tanjun.annotations.Member]
    * [Channel][tanjun.annotations.Channel]
    * [Mentionable][tanjun.annotations.Mentionable]

    Examples
    --------
    ```py
    @with_annotated_args(follow_wrapped=True)
    @tanjun.as_slash_command("meow", "nyaa")
    @tanjun.as_message_command("meow")
    async def command(
        ctx: tanjun.abc.Context,
        user: Annotated[User, SnowflakeOr(parse_id=parse_user_id), "The user to target."],

        # The `parse_id` callback is automatically set to the mention format for
        # the specified for the passed type if applicable when using SnowflakeOr
        # as a generic type-hint.
        role: Annotated[Optional[SnowflakeOr[Role]], "The role to target."] = None,
    ) -> None:
        user_id = hikari.Snowflake(user)
    ```
    """

    __slots__ = ("_parse_id",)

    def __init__(self, *, parse_id: collections.Callable[[str], hikari.Snowflake] = conversion.parse_snowflake) -> None:
        """Create a snowflake or argument marker.

        Parameters
        ----------
        parse_id
            The function used to parse the argument's ID.

            This can be used to restrain this to only accepting certain mention
            formats.
        """
        self._parse_id = parse_id

    @property
    def parse_id(self) -> collections.Callable[[str], hikari.Snowflake]:
        """Callback used to parse this argument's ID."""
        return self._parse_id

    def set_config(self, config: _ArgConfig, /) -> None:
        config.snowflake_converter = self._parse_id


class _TypeOverride(_ConfigIdentifier):
    __slots__ = ("_override",)

    def __init__(self, override: type[typing.Any], /) -> None:
        self._override = override

    def set_config(self, config: _ArgConfig, /) -> None:
        config.option_type = self._override


class _TheseChannelsMeta(abc.ABCMeta):
    def __getitem__(
        cls, value: typing.Union[_ChannelTypeIsh, collections.Collection[_ChannelTypeIsh]], /
    ) -> type[hikari.PartialChannel]:
        if not isinstance(value, collections.Collection):
            value = (value,)

        return typing.Annotated[Channel, TheseChannels(*value)]


class TheseChannels(_ConfigIdentifier, metaclass=_TheseChannelsMeta):
    """Declare the type of channels a slash command partial channel argument can target.

    This is no-op for message commands and will not restrain the argument right now.
    """

    __slots__ = ("_channel_types",)

    def __init__(
        self,
        channel_type: _ChannelTypeIsh,
        /,
        *other_types: _ChannelTypeIsh,
    ) -> None:
        """Create a slash command argument channel restraint.

        Parameters
        ----------
        channel_type
            A channel type to restrain this argument by.
        *other_types
            Other channel types to restrain this argument by.
        """
        self._channel_types = (channel_type, *other_types)

    @property
    def channel_types(self) -> collections.Sequence[_ChannelTypeIsh]:
        """Sequence of the channel types this is constrained by."""
        return self._channel_types

    def set_config(self, config: _ArgConfig, /) -> None:
        config.channel_types = self._channel_types


def _ensure_value(name: str, type_: type[_T], value: typing.Optional[typing.Any]) -> typing.Optional[_T]:
    if value is None or isinstance(value, type_):
        return value

    raise ValueError(
        f"{name.capitalize()} value of type {type(value).__name__} is not valid for a {type_.__name__} argument"
    )


def _ensure_values(
    name: str, type_: type[_T], mapping: typing.Optional[collections.Mapping[str, typing.Any]], /
) -> typing.Optional[collections.Mapping[str, _T]]:
    if not mapping:
        return None

    for value in mapping.values():
        if not isinstance(value, type_):
            raise ValueError(
                f"{name.capitalize()} of type {type(value).__name__} is not valid for a {type_.__name__} argument"
            )

    return typing.cast(collections.Mapping[str, _T], mapping)


_OPTION_TYPE_TO_CONVERTERS: dict[type[typing.Any], tuple[_ConverterSig[typing.Any], ...]] = {
    hikari.Attachment: NotImplemented,
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


_MESSAGE_ID_ONLY: frozenset[type[typing.Any]] = frozenset(
    [hikari.User, hikari.Role, hikari.Member, hikari.PartialChannel, _MentionableUnion]
)


class _ArgConfig:
    __slots__ = (
        "aliases",
        "channel_types",
        "choices",
        "converters",
        "default",
        "description",
        "empty_value",
        "is_greedy",
        "is_positional",
        "key",
        "min_length",
        "max_length",
        "min_value",
        "max_value",
        "message_name",
        "option_type",
        "range_or_slice",
        "range_or_slice_is_finalised",
        "slash_name",
        "snowflake_converter",
    )

    def __init__(self, key: str, default: typing.Any, /) -> None:
        self.aliases: typing.Optional[collections.Sequence[str]] = None
        self.channel_types: typing.Optional[collections.Sequence[_ChannelTypeIsh]] = None
        self.choices: typing.Optional[collections.Mapping[str, _ChoiceUnion]] = None
        self.converters: typing.Optional[collections.Sequence[_ConverterSig[typing.Any]]] = None
        self.default: typing.Any = default
        self.description: typing.Optional[str] = None
        self.empty_value: typing.Union[parsing.UndefinedT, typing.Any] = parsing.UNDEFINED
        self.is_greedy: bool = False
        self.is_positional: typing.Optional[bool] = None
        self.key: str = key
        self.min_length: typing.Optional[int] = None
        self.max_length: typing.Optional[int] = None
        self.min_value: typing.Union[float, int, None] = None
        self.max_value: typing.Union[float, int, None] = None
        self.message_name: str = "--" + key.replace("_", "-")
        self.option_type: typing.Optional[type[typing.Any]] = None
        self.range_or_slice: typing.Union[range, slice, None] = None
        self.slash_name: str = key
        self.snowflake_converter: typing.Optional[collections.Callable[[str], hikari.Snowflake]] = None

    def finalise_slice(self) -> None:
        if not self.range_or_slice:
            return

        self.range_or_slice_is_finalised = True
        # Slice's attributes are all Any so we need to cast to int.
        if self.range_or_slice.step is None or operator.index(self.range_or_slice.step) > 0:
            min_value = operator.index(self.range_or_slice.start) if self.range_or_slice.start is not None else 0
            max_value = operator.index(self.range_or_slice.stop) - 1
        else:
            # start will have to have been specified for this to be reached.
            min_value = operator.index(self.range_or_slice.stop) - 1
            max_value = operator.index(self.range_or_slice.start)

        if self.option_type is str:
            self.min_length = min_value
            self.max_length = max_value

        elif self.option_type is int or self.option_type is float:
            self.min_value = min_value
            self.max_value = max_value

    def to_message_option(self, command: message.MessageCommand[typing.Any], /) -> None:
        if self.converters:
            converters = self.converters

        elif self.option_type:
            if self.snowflake_converter and self.option_type in _MESSAGE_ID_ONLY:
                converters = (self.snowflake_converter,)

            elif (converters_ := _OPTION_TYPE_TO_CONVERTERS[self.option_type]) is not NotImplemented:
                converters = converters_

            else:
                return

        else:
            return

        if command.parser:
            if not isinstance(command.parser, parsing.AbstractOptionParser):
                raise TypeError("Expected parser to be an instance of tanjun.parsing.AbstractOptionParser")

            parser = command.parser

        else:
            parser = parsing.ShlexParser()
            command.set_parser(parser)

        if self.is_positional or (self.is_positional is None and self.default is parsing.UNDEFINED):
            parser.add_argument(
                self.key,
                converters=converters,
                default=self.default,
                greedy=self.is_greedy,
                min_length=self.min_length,
                max_length=self.max_length,
                min_value=self.min_value,
                max_value=self.max_value,
            )

        else:
            if self.default is parsing.UNDEFINED:
                raise ValueError(f"Flag argument {self.key!r} must have a default")

            parser.add_option(
                self.key,
                self.message_name,
                *self.aliases or (),
                converters=converters,
                default=self.default,
                empty_value=self.empty_value,
                min_length=self.min_length,
                max_length=self.max_length,
                min_value=self.min_value,
                max_value=self.max_value,
            )

    def _slash_default(self) -> typing.Any:
        return slash.UNDEFINED_DEFAULT if self.default is parsing.UNDEFINED else self.default

    def to_slash_option(self, command: slash.SlashCommand[typing.Any], /) -> None:
        option_type = self.option_type
        if not option_type and self.converters:
            option_type = str

        if option_type:
            if not self.description:
                raise ValueError(f"Missing description for argument {self.key!r}")

            self.SLASH_OPTION_ADDER[option_type](self, command, self.description)

    SLASH_OPTION_ADDER: dict[
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
            choices=_ensure_values("choice", float, self.choices),  # TODO: can we pass ints here as well?
            converters=self.converters or (),
            default=self._slash_default(),
            key=self.key,
            min_value=self.min_value,  # TODO: explicitly cast to float?
            max_value=self.max_value,
        ),
        int: lambda self, c, d: c.add_int_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", int, self.choices),
            converters=self.converters or (),
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
            min_length=self.min_length,
            max_length=self.max_length,
        ),
        hikari.User: lambda self, c, d: c.add_user_option(
            self.slash_name, d, default=self._slash_default(), key=self.key
        ),
    }


def _snoop_annotation_args(type_: typing.Any) -> collections.Iterator[typing.Any]:
    origin = typing.get_origin(type_)
    if origin is typing.Annotated:
        args = typing.get_args(type_)
        yield from _snoop_annotation_args(args[0])
        yield from args[1:]

    elif origin in _UnionTypes:
        yield from itertools.chain.from_iterable(map(_snoop_annotation_args, typing.get_args(type_)))


def _annotated_args(command: _CommandUnionT, /, *, follow_wrapped: bool = False) -> _CommandUnionT:
    try:
        signature = inspect.signature(command.callback, eval_str=True)
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
        for sub_command in _internal.collect_wrapped(command):
            if isinstance(sub_command, message.MessageCommand):
                message_commands.append(sub_command)

            elif isinstance(sub_command, slash.SlashCommand):
                slash_commands.append(sub_command)

    for parameter in signature.parameters.values():
        if parameter.annotation is parameter.empty:
            continue

        arg_config = _ArgConfig(
            parameter.name, parsing.UNDEFINED if parameter.default is parameter.empty else parameter.default
        )
        for arg in _snoop_annotation_args(parameter.annotation):
            if isinstance(arg, _ConfigIdentifier):
                arg.set_config(arg_config)

            elif isinstance(arg, str):
                arg_config.description = arg

            elif isinstance(arg, (range, slice)):
                arg_config.range_or_slice = arg

        arg_config.finalise_slice()
        if arg_config.option_type or arg_config.converters:
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
        * [tanjun.annotations.Color][]/[tanjun.annotations.Colour][]
        * [tanjun.annotations.Datetime][]
        * [tanjun.annotations.Float][]
        * [tanjun.annotations.Int][]
        * [tanjun.annotations.Member][]
        * [tanjun.annotations.Mentionable][]
        * [tanjun.annotations.Role][]
        * [tanjun.annotations.Snowflake][]
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

    2. By assigning [tanjun.annotations.Converted][]...

        Either as one of the other arguments to [typing.Annotated][]

        ```py
        @tanjun.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("e")
        @tanjun.as_slash_command("e", "description")
        async def command(
            ctx: tanjun.abc.SlashContext,
            value: Annotated[OtherType, Converted(parse_value), "description"],
        ) -> None:
            raise NotImplementedError
        ```

        or as the type hint

        ```py
        @tanjun.with_annotated_args(follow_wrapped=True)
        @tanjun.as_message_command("e")
        @tanjun.as_slash_command("e", "description")
        async def command(
            ctx: tanjun.abc.SlashContext,
            value: Annotated[Converted[CustomType.from_str], "description"],
        ) -> None:
            raise NotImplementedError
        ```

    It should be noted that wrapping in [typing.Annotated][] isn't necessary for
    message commands options as they don't have descriptions.

    ```py
    async def message_command(
        ctx: tanjun.abc.MessageContext,
        name: Str,
        converted: Converted[Type.from_str],
        enable: typing.Optional[Bool] = None,
    ) -> None:
        ...
    ```

    Parameters
    ----------
    command : tanjun.SlashCommand | tanjun.MessageCommand
        The message or slash command to set the arguments for.
    follow_wrapped
        Whether this should also set the arguments on any other command objects
        this wraps in a decorator call chain.

    Returns
    -------
    tanjun.SlashCommand | tanjun.MessageCommand
        The command object to enable using this as a decorator.
    """
    if not command:
        return lambda c: _annotated_args(c, follow_wrapped=follow_wrapped)

    return _annotated_args(command, follow_wrapped=follow_wrapped)
