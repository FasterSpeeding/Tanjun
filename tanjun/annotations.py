# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
r"""Parameter annotation based strategy for declaring slash and message command arguments.

[with_annotated_args][tanjun.annotations.with_annotated_args] should be used to
parse the options for both message commands and slash commands.
`follow_wrapped=True` should be passed if you want this to parse options for
all the commands being declared in a decorator call chain.

This implementation exposes 3 ways to mark an argument as a command option:

1. Using any of the following types as an argument's type-hint (this may
    be as the first argument to [typing.Annotated][]) will mark it as a
    command argument:

    * [annotations.Attachment][tanjun.annotations.Attachment]\*
    * [annotations.Bool][tanjun.annotations.Bool]
    * [annotations.Channel][tanjun.annotations.Channel]
    * [annotations.InteractionChannel][tanjun.annotations.InteractionChannel]\*
    * [annotations.Color][tanjun.annotations.Color]/[annotations.Colour][tanjun.annotations.Colour]
    * [annotations.Datetime][tanjun.annotations.Datetime]
    * [annotations.Float][tanjun.annotations.Float]
    * [annotations.Int][tanjun.annotations.Int]
    * [annotations.Member][tanjun.annotations.Member]
    * [annotations.InteractionMember][tanjun.annotations.InteractionMember]\*
    * [annotations.Mentionable][tanjun.annotations.Mentionable]
    * [annotations.Role][tanjun.annotations.Role]
    * [annotations.Snowflake][tanjun.annotations.Snowflake]
    * [annotations.Str][tanjun.annotations.Str]
    * [annotations.User][tanjun.annotations.User]

    \* These types are specific to slash commands and will raise an exception
        when set for a message command's parameter which has no real default.

    ```py
    @tanjun.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("name")
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,

        # Here the option's description is passed as a string to Annotated:
        # this is necessary for slash commands but ignored for message commands.
        name: Annotated[Str, "The character's name"],

        # `= False` declares this field as optional, with it defaulting to `False`
        # if not specified.
        lawyer: Annotated[Bool, "Whether they're a lawyer"] = False,
    ) -> None:
        raise NotImplementedError
    ```

    When doing this the following objects can be included in a field's
    annotations to add extra configuration:

    * [annotations.Default][tanjun.annotations.Default]
        Set the default for an option in the annotations (rather than using
        the argument's actual default).
    * [annotations.Flag][tanjun.annotations.Flag]
        Mark an option as being a flag option for message commands.
    * [annotations.Greedy][tanjun.annotations.Greedy]
        Mark an option as consuming the rest of the provided positional
        values for message commands.
    * [annotations.Length][tanjun.annotations.Length]
        Set the length restraints for a string option.
    * [annotations.Min][tanjun.annotations.Min]
        Set the minimum valid size for float and integer options.
    * [annotations.Max][tanjun.annotations.Max]
        Set the maximum valid size for float and integer options.
    * [annotations.Name][tanjun.annotations.Name]
        Override the option's name.
    * [annotations.Positional][tanjun.annotations.Positional]
        Mark optional arguments as positional for message commands.
    * [annotations.Ranged][tanjun.annotations.Ranged]
        Set range constraints for float and integer options.
    * [annotations.SnowflakeOr][tanjun.annotations.SnowflakeOr]
        Indicate that a role, user, channel, member, role, or mentionable
        option should be left as the ID for message commands.
    * [annotations.TheseChannels][tanjun.annotations.TheseChannels]
        Constrain the valid channel types for a channel option.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        name: Annotated[Str, Length(1, 20)],
        channel: Annotated[Role | hikari.Snowflake | None, SnowflakeOr()] = None,
    ) -> None:
        raise NotImplementedError
    ```

    It should be noted that wrapping in [typing.Annotated][] isn't necessary for
    message commands options as they don't have descriptions.

    ```py
    async def message_command(
        ctx: tanjun.abc.MessageContext,
        name: Str,
        value: Str,
        enable: typing.Optional[Bool] = None,
    ) -> None:
        raise NotImplementedError
    ```

2. By assigning [tanjun.Converted][tanjun.annotations.Converted] as one of
    the other arguments to [typing.Annotated][]:

    ```py
    @tanjun.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("e")
    @tanjun.as_slash_command("e", "description")
    async def command(
        ctx: tanjun.abc.Context,
        value: Annotated[ParsedType, Converted(parse_value), "description"],
    ) -> None:
        raise NotImplementedError
    ```

    When doing this the option type will be `str`.

3. By using any of the following default descriptors as the argument's
    default:

    * [annotations.attachment_field][tanjun.annotations.attachment_field]\*
    * [annotations.bool_field][tanjun.annotations.bool_field]
    * [annotations.channel_field][tanjun.annotations.channel_field]
    * [annotations.float_field][tanjun.annotations.float_field]
    * [annotations.int_field][tanjun.annotations.int_field]
    * [annotations.member_field][tanjun.annotations.member_field]
    * [annotations.mentionable_field][tanjun.annotations.mentionable_field]
    * [annotations.role_field][tanjun.annotations.role_field]
    * [annotations.str_field][tanjun.annotations.str_field]
    * [annotations.user_field][tanjun.annotations.user_field]

    \* These are specific to slash commands and will raise an exception
        when set for a message command's parameter which has no real default.

    ```py
    @tanjun.with_annotated_args(follow_wrapped=True)
    @tanjun.as_message_command("e")
    @tanjun.as_slash_command("e", "description")
    async def command(
        ctx: tanjun.abc.Context,
        user_field: hikari.User | None = annotations.user_field(default=None),
        field: bool = annotations.bool_field(default=False, empty_value=True),
    ) -> None:
        raise NotImplementedError
    ```

A [typing.TypedDict][] can be used to declare multiple options by
typing the passed `**kwargs` dict as it using [typing.Unpack][].
These options can be marked as optional using [typing.NotRequired][],
`total=False` or [Default][tanjun.annotations.Default].

```py
class CommandOptions(typing.TypedDict):
    argument: Annotated[Str, "A required string argument"]
    other: NotRequired[Annotated[Bool, "An optional string argument"]]

@tanjun.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("name")
@tanjun.as_slash_command("name", "description")
async def command(
    ctx: tanjun.abc.Context, **kwargs: Unpack[CommandOptions],
) -> None:
    raise NotImplementedError
```

Community Resources:

* An extended implementation of this which parses callback docstrings to get the
  descriptions for slash commands and their options can be found in
  <https://github.com/FasterSpeeding/Tan-chan>.
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
    "InteractionChannel",
    "InteractionMember",
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
    "attachment_field",
    "bool_field",
    "channel_field",
    "float_field",
    "int_field",
    "member_field",
    "mentionable_field",
    "role_field",
    "str_field",
    "user_field",
    "with_annotated_args",
]

import abc
import dataclasses
import datetime
import enum
import itertools
import operator
import typing
import warnings
from collections import abc as collections

import hikari
import typing_extensions

from . import _internal
from . import abc as tanjun
from . import conversion
from . import parsing
from ._internal.vendor import inspect
from .commands import message
from .commands import slash

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    _T = typing.TypeVar("_T")
    _OtherT = typing.TypeVar("_OtherT")
    _P = typing_extensions.ParamSpec("_P")
    __ConverterSig = collections.Callable[
        typing_extensions.Concatenate[str, _P], typing.Union[collections.Coroutine[typing.Any, typing.Any, _T], _T]
    ]
    _ConverterSig = __ConverterSig[..., _T]
    _ChannelTypeIsh = typing.Union[type[hikari.PartialChannel], int]
    _ChoiceUnion = typing.Union[int, float, str]
    _ChoiceT = typing.TypeVar("_ChoiceT", int, float, str)
    _CommandUnion = typing.Union[slash.SlashCommand[typing.Any], message.MessageCommand[typing.Any]]
    _CommandUnionT = typing.TypeVar("_CommandUnionT", bound=_CommandUnion)
    _EnumT = typing.TypeVar("_EnumT", bound="enum.Enum")
    _NumberT = typing.TypeVar("_NumberT", float, int)


_MentionableUnion = typing.Union[hikari.User, hikari.Role]


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
        config.set_option_type(self._type)


Attachment = typing.Annotated[hikari.Attachment, _OptionMarker(hikari.Attachment)]
"""Type-hint for marking an argument which accepts a file.

!!! warning
    This is currently only supported for slash commands.
"""

Bool = typing.Annotated[bool, _OptionMarker(bool)]
"""Type-hint for marking an argument which takes a bool-like value."""

Channel = typing.Annotated[hikari.PartialChannel, _OptionMarker(hikari.PartialChannel)]
"""Type-hint for marking an argument which takes a channel.

[hikari.InteractionChannel][hikari.interactions.base_interactions.InteractionChannel]
will be passed for options typed as this when being called as a slash command.
"""

InteractionChannel = typing.Annotated[hikari.InteractionChannel, _OptionMarker(hikari.InteractionChannel)]
"""Type-hint for marking an argument which takes a channel with interaction specific metadata.

!!! warning
    This is only supported for slash commands and will not work for message
    commands (unlike [annotations.Channel][tanjun.annotations.Channel]).
"""

Float = typing.Annotated[float, _OptionMarker(float)]
"""Type-hint for marking an argument which takes a floating point number."""

Int = typing.Annotated[int, _OptionMarker(int)]
"""Type-hint for marking an argument which takes an integer."""

Member = typing.Annotated[hikari.Member, _OptionMarker(hikari.Member)]
"""Type-hint for marking an argument which takes a guild member.

[hikari.InteractionMember][hikari.interactions.base_interactions.InteractionMember]
will be passed for options typed as this when being called as a slash command.
"""

InteractionMember = typing.Annotated[hikari.InteractionMember, _OptionMarker(hikari.InteractionMember)]
"""Type-hint for marking an argument which takes an interactio.

!!! warning
    This is only supported for slash commands and will not work for message
    commands (unlike [annotations.Member][tanjun.annotations.Member]).
"""

Mentionable = typing.Annotated[typing.Union[hikari.User, hikari.Role], _OptionMarker(_MentionableUnion)]
"""Type-hint for marking an argument which takes a user or role."""

Role = typing.Annotated[hikari.Role, _OptionMarker(hikari.Role)]
"""Type-hint for marking an argument which takes a role."""

Str = typing.Annotated[str, _OptionMarker(str)]
"""Type-hint for marking an argument which takes string input."""

User = typing.Annotated[hikari.User, _OptionMarker(hikari.User)]
"""Type-hint for marking an argument which takes a user."""


@dataclasses.dataclass()
class _Field(_ConfigIdentifier):
    __slots__ = (
        "_channel_types",
        "_choices",
        "_default",
        "_description",
        "_empty_value",
        "_is_greedy",
        "_is_positional",
        "_message_names",
        "_min_length",
        "_max_length",
        "_min_value",
        "_max_value",
        "_option_type",
        "_slash_name",
        "_snowflake_converter",
        "_str_converters",
    )

    _channel_types: collections.Sequence[_ChannelTypeIsh]
    _choices: typing.Optional[collections.Mapping[str, _ChoiceUnion]]
    _default: typing.Any
    _description: str
    _empty_value: typing.Any
    _is_greedy: typing.Optional[bool]
    _is_positional: typing.Optional[bool]
    _message_names: collections.Sequence[str]
    _min_length: typing.Union[int, None]
    _max_length: typing.Union[int, None]
    _min_value: typing.Union[int, float, None]
    _max_value: typing.Union[int, float, None]
    _option_type: typing.Any
    _slash_name: str
    _snowflake_converter: typing.Optional[collections.Callable[[str], hikari.Snowflake]]
    _str_converters: collections.Sequence[_ConverterSig[typing.Any]]

    # TODO: _float_converter, _int_converter

    @classmethod
    def new(
        cls,
        option_type: type[_T],
        /,
        *,
        channel_types: collections.Sequence[_ChannelTypeIsh] = (),
        choices: typing.Optional[collections.Mapping[str, _ChoiceUnion]] = None,
        default: typing.Any = tanjun.NO_DEFAULT,
        description: str = "",
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        greedy: typing.Optional[bool] = None,
        message_names: collections.Sequence[str] = (),
        min_length: typing.Union[int, None] = None,
        max_length: typing.Union[int, None] = None,
        min_value: typing.Union[int, float, None] = None,
        max_value: typing.Union[int, float, None] = None,
        positional: typing.Optional[bool] = None,
        slash_name: str = "",
        snowflake_converter: typing.Optional[collections.Callable[[str], hikari.Snowflake]] = None,
        str_converters: typing.Union[_ConverterSig[typing.Any], collections.Sequence[_ConverterSig[typing.Any]]] = (),
    ) -> _T:
        if not isinstance(str_converters, collections.Sequence):
            str_converters = (str_converters,)

        return typing.cast(
            "_T",
            cls(
                _channel_types=channel_types,
                _choices=choices,
                _default=default,
                _description=description,
                _empty_value=empty_value,
                _is_greedy=greedy,
                _is_positional=positional,
                _message_names=message_names,
                _min_length=min_length,
                _max_length=max_length,
                _min_value=min_value,
                _max_value=max_value,
                _option_type=option_type,
                _slash_name=slash_name,
                _snowflake_converter=snowflake_converter,
                _str_converters=str_converters,
            ),
        )

    def set_config(self, config: _ArgConfig, /) -> None:
        config.channel_types = self._channel_types or config.channel_types
        config.choices = self._choices or config.choices

        if self._default is not tanjun.NO_DEFAULT:
            config.default = self._default

        config.description = self._description or config.description

        if self._empty_value is not tanjun.NO_DEFAULT:
            config.empty_value = self._empty_value

        if self._is_greedy is not None:
            config.is_greedy = self._is_greedy

        if self._is_positional is not None:
            config.is_positional = self._is_positional

        if self._message_names:
            config.main_message_name = self._message_names[0]
            config.message_names = self._message_names

        if self._min_length is not None:
            config.min_length = self._min_length

        if self._max_length is not None:
            config.max_length = self._max_length

        if self._min_value is not None:
            config.min_value = self._min_value

        if self._max_value is not None:
            config.max_value = self._max_value

        config.set_option_type(self._option_type)
        config.slash_name = self._slash_name or config.slash_name
        config.snowflake_converter = self._snowflake_converter or config.snowflake_converter
        config.str_converters = self._str_converters or config.str_converters


def attachment_field(
    *, default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT, description: str = "", slash_name: str = ""
) -> typing.Union[hikari.Attachment, _T]:
    """Mark a parameter as an attachment option using a descriptor.

    !!! warning
        This is currently only supported for slash commands.

    Examples
    --------
    ```py
    async def command(
        ctx: tanjun.abc.SlashContext,
        field: hikari.Attachment | None = annotations.attachment_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
    description
        The option's description.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(hikari.Attachment, default=default, description=description, slash_name=slash_name)


def bool_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[bool, _T]:
    """Mark a parameter as a bool option using a descriptor.

    Examples
    --------
    ```py
    async def command(
        ctx: tanjun.abc.SlashContext,
        field: bool | None = annotations.bool_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        bool,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        positional=positional,
        slash_name=slash_name,
    )


@typing.overload
def channel_field(
    *,
    channel_types: collections.Sequence[_ChannelTypeIsh] = (),
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[False] = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.PartialChannel, _T]:
    ...


@typing.overload
def channel_field(
    *,
    channel_types: collections.Sequence[_ChannelTypeIsh] = (),
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[True],
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.PartialChannel, hikari.Snowflake, _T]:
    ...


def channel_field(
    *,
    channel_types: collections.Sequence[_ChannelTypeIsh] = (),
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: bool = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.PartialChannel, hikari.Snowflake, _T]:
    """Mark a parameter as a channel option using a descriptor.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: hikari.PartialChannel | None = annotations.channel_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    channel_types
        Sequence of the channel types allowed for this option.

        If left as an empty sequence then all channel types will be allowed.
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    or_snowflake
        Whether this should just pass the parsed channel ID as a
        [hikari.Snowflake][hikari.snowflakes.Snowflake] for message command
        calls.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        hikari.PartialChannel,
        channel_types=channel_types,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        snowflake_converter=conversion.parse_channel_id if or_snowflake else None,
        positional=positional,
        slash_name=slash_name,
    )


def float_field(
    *,
    choices: typing.Optional[collections.Mapping[str, float]] = None,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    min_value: typing.Optional[float] = None,
    max_value: typing.Optional[float] = None,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[float, _T]:
    """Mark a parameter as a float option using a descriptor.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: float | None = annotations.float_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    choices
        A mapping of up to 25 names to the choices values for this option.

        This is ignored for message command parsing.
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    min_value
        The minimum allowed value for this argument.
    max_value
        The maximum allowed value for this argument.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        float,
        choices=choices,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        min_value=min_value,
        max_value=max_value,
        positional=positional,
        slash_name=slash_name,
    )


def int_field(
    *,
    choices: typing.Optional[collections.Mapping[str, int]] = None,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    min_value: typing.Optional[int] = None,
    max_value: typing.Optional[int] = None,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[int, _T]:
    """Mark a parameter as a int option using a descriptor.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: int | None = annotations.int_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    choices
        A mapping of up to 25 names to the choices values for this option.

        This is ignored for message command parsing.
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    min_value
        The minimum allowed value for this argument.
    max_value
        The maximum allowed value for this argument.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        int,
        choices=choices,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        min_value=min_value,
        max_value=max_value,
        positional=positional,
        slash_name=slash_name,
    )


@typing.overload
def member_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[False] = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.Member, _T]:
    ...


@typing.overload
def member_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[True],
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.Member, hikari.Snowflake, _T]:
    ...


def member_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: bool = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.Member, hikari.Snowflake, _T]:
    """Mark a parameter as a guild member option using a descriptor.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: hikari.Member | None = annotations.member_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    or_snowflake
        Whether this should just pass the parsed user ID as a
        [hikari.Snowflake][hikari.snowflakes.Snowflake] for message command
        calls.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        hikari.Member,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        snowflake_converter=conversion.parse_user_id if or_snowflake else None,
        positional=positional,
        slash_name=slash_name,
    )


@typing.overload
def mentionable_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[False] = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.User, hikari.Role, _T]:
    ...


@typing.overload
def mentionable_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[True],
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.User, hikari.Role, hikari.Snowflake, _T]:
    ...


def mentionable_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: bool = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.User, hikari.Role, hikari.Snowflake, _T]:
    """Mark a parameter as a "mentionable" option using a descriptor.

    Mentionable options allow both user and roles.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: hikari.Role | hikari.User | None = annotations.mentionable_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    or_snowflake
        Whether this should just pass the parsed ID as a
        [hikari.Snowflake][hikari.snowflakes.Snowflake] for message command
        calls.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        _MentionableUnion,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        snowflake_converter=conversion.to_snowflake if or_snowflake else None,
        positional=positional,
        slash_name=slash_name,
    )


@typing.overload
def role_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[False] = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.Role, _T]:
    ...


@typing.overload
def role_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[True],
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.Role, hikari.Snowflake, _T]:
    ...


def role_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: bool = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.Role, hikari.Snowflake, _T]:
    """Mark a parameter as a guild role option using a descriptor.

    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: hikari.Role | None = annotations.role_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    or_snowflake
        Whether this should just pass the parsed role ID as a
        [hikari.Snowflake][hikari.snowflakes.Snowflake] for message command
        calls.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        hikari.Role,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        snowflake_converter=conversion.parse_role_id if or_snowflake else None,
        positional=positional,
        slash_name=slash_name,
    )


@typing.overload
def str_field(
    *,
    choices: typing.Optional[collections.Mapping[str, str]] = None,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    min_length: typing.Union[int, None] = None,
    max_length: typing.Union[int, None] = None,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[str, _T]:
    ...


@typing.overload
def str_field(
    *,
    choices: typing.Optional[collections.Mapping[str, str]] = None,
    converters: typing.Union[_ConverterSig[_OtherT], collections.Sequence[_ConverterSig[_OtherT]]],
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    min_length: typing.Union[int, None] = None,
    max_length: typing.Union[int, None] = None,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[_OtherT, _T]:
    ...


def str_field(
    *,
    choices: typing.Optional[collections.Mapping[str, str]] = None,
    converters: typing.Union[_ConverterSig[_OtherT], collections.Sequence[_ConverterSig[_OtherT]]] = (),
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    min_length: typing.Union[int, None] = None,
    max_length: typing.Union[int, None] = None,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[str, _T, _OtherT]:
    """Mark a parameter as a string option using a descriptor.

    Examples
    --------
    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: str | None = annotations.str_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    choices
        A mapping of up to 25 names to the choices values for this option.

        This is ignored for message command parsing.
    converters
        The option's converters.

        This may be either one or multiple converter callbacks used to
        convert the option's value to the final form.
        If no converters are provided then the raw value will be passed.

        Only the first converter to pass will be used.
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    min_length
        The minimum length this argument can be.
    max_length
        The maximum length this string argument can be.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        str,
        choices=choices,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        min_length=min_length,
        max_length=max_length,
        positional=positional,
        slash_name=slash_name,
        str_converters=converters,
    )


@typing.overload
def user_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[False] = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.User, _T]:
    ...


@typing.overload
def user_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: typing.Literal[True],
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.User, hikari.Snowflake, _T]:
    ...


def user_field(
    *,
    default: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    description: str = "",
    empty_value: typing.Union[_T, tanjun.NoDefault] = tanjun.NO_DEFAULT,
    greedy: typing.Optional[bool] = None,
    message_names: collections.Sequence[str] = (),
    or_snowflake: bool = False,
    positional: typing.Optional[bool] = None,
    slash_name: str = "",
) -> typing.Union[hikari.User, hikari.Snowflake, _T]:
    """Mark a parameter as a user option using a descriptor.

    Examples
    --------
    ```py
    async def command(
        ctx: tanjun.abc.Context,
        field: hikari.User | None = annotations.user_field(default=None),
    ) -> None:
        ...
    ```

    Parameters
    ----------
    default : typing.Any
        Default value to pass if this option wasn't provided.

        If not passed then this option will be required.
        Otherwise, this will mark the option as being a flag for message
        commands unless `positional=False` is also passed.
    description
        The option's description.
    empty_value : typing.Any
        Value to pass when this is used as a message flag without a value
        (i.e. `--name`).

        If not passed then a value will be required and is ignored unless
        `default` is also passed.
    greedy
        Whether this option should be marked as "greedy" form message command
        parsing.

        A greedy option will consume the rest of the positional arguments.
        This can only be applied to one positional argument and is no-op for
        slash commands and flags.
    message_names
        The names this option may be triggered by as a message command flag
        option.

        These must all be prefixed with `"-"` and are ignored unless `default`
        is also passed.
    or_snowflake
        Whether this should just pass the parsed user ID as a
        [hikari.Snowflake][hikari.snowflakes.Snowflake] for message command
        calls.
    positional
        Whether this should be a positional argument.

        Arguments will be positional by default unless `default` is provided.
    slash_name
        The name to use for this option in slash commands.
    """
    return _Field.new(
        hikari.User,
        default=default,
        description=description,
        empty_value=empty_value,
        greedy=greedy,
        message_names=message_names,
        snowflake_converter=conversion.parse_user_id if or_snowflake else None,
        positional=positional,
        slash_name=slash_name,
    )


class _FloatEnumConverter(_ConfigIdentifier):
    """Specialised converters for float enum choices."""

    __slots__ = ("_enum",)

    def __init__(self, enum: collections.Callable[[float], typing.Any]) -> None:
        self._enum = enum

    def set_config(self, config: _ArgConfig, /) -> None:
        config.float_converter = self._enum


class _IntEnumConverter(_ConfigIdentifier):
    """Specialised converters for int enum choices."""

    __slots__ = ("_enum",)

    def __init__(self, enum: collections.Callable[[int], typing.Any]) -> None:
        self._enum = enum

    def set_config(self, config: _ArgConfig, /) -> None:
        config.int_converter = self._enum


class _EnumConverter(_ConfigIdentifier):
    __slots__ = ("_converter",)

    def __init__(self, enum: collections.Callable[[str], enum.Enum], /) -> None:
        self._converter = enum

    def set_config(self, config: _ArgConfig, /) -> None:
        config.str_converters = [self._converter]


class _ChoicesMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Choices(...) to Annotated")
    def __getitem__(cls, enum_: type[_EnumT], /) -> type[_EnumT]:
        if issubclass(enum_, float):
            type_ = float
            choices = Choices(enum_.__members__)
            converter = _FloatEnumConverter(enum_)

        elif issubclass(enum_, int):
            type_ = int
            choices = Choices(enum_.__members__)
            converter = _IntEnumConverter(enum_)

        elif issubclass(enum_, str):
            type_ = str
            choices = Choices(enum_.__members__)
            converter = None

        else:
            raise TypeError("Enum must be a subclass of str, float or int")

        # TODO: do we want to wrap the convert callback to give better failed parse messages?
        return typing.cast(
            "type[_EnumT]", typing.Annotated[enum_, choices, converter, _EnumConverter(enum_), _OptionMarker(type_)]
        )


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
    @typing_extensions.deprecated("Pass Converted(...) to Annotated")
    def __getitem__(cls, converters: typing.Union[_ConverterSig[_T], tuple[_ConverterSig[_T]]], /) -> type[_T]:
        if not isinstance(converters, tuple):
            converters = (converters,)

        return typing.cast("type[_T]", typing.Annotated[typing.Any, Converted(*converters)])


class Converted(_ConfigIdentifier, metaclass=_ConvertedMeta):
    """Marked an argument as type [Str][tanjun.annotations.Str] with converters.

    Examples
    --------
    ```py
    @with_annotated_args
    @tanjun.as_slash_command("beep", "boop")
    async def command(
        ctx: tanjun.abc.SlashContext,
        argument: Annotated[OtherType, Converted(callback, other_callback), "description"]
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ("_converters",)

    def __init__(self, converter: _ConverterSig[typing.Any], /, *other_converters: _ConverterSig[typing.Any]) -> None:
        """Create a converted instance.

        Parameters
        ----------
        converter : collections.abc.Callable[[str, ...], collections.Coroutine[Any, Any, Any] | Any]
            The first converter this argument should use to handle values passed to it
            during parsing.

            Only the first converter to pass will be used.
        *other_converters : collections.abc.Callable[[str, ...], collections.Coroutine[Any, Any, Any] | Any]
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
        config.str_converters = self._converters
        config.set_option_type(str)


Color = typing.Annotated[hikari.Color, Converted(conversion.to_color)]
"""An argument which takes a color."""

Colour = Color
"""An argument which takes a colour."""

Datetime = typing.Annotated[datetime.datetime, Converted(conversion.to_datetime)]
"""An argument which takes a datetime."""

Snowflake = typing.Annotated[hikari.Snowflake, Converted(conversion.parse_snowflake)]
"""An argument which takes a snowflake."""


class _DefaultMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Default(...) to Annotated")
    def __getitem__(cls, value: typing.Union[type[_T], tuple[type[_T], _T]], /) -> type[_T]:
        if isinstance(value, tuple):
            type_ = value[0]
            return typing.Annotated[type_, Default(value[1])]

        type_ = typing.cast("type[_T]", value)
        return typing.Annotated[type_, Default()]


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
    ) -> None:
        raise NotImplementedError
    ```

    ```py
    @with_annotated_args
    @tanjun.as_slash_command("name", "description")
    async def command(
        ctx: tanjun.abc.Context,
        required_argument: Annotated[Int, Default(), "description"] = 123,
    ) -> None:
        raise NotImplementedError
    ```

    Passing an empty [Default][tanjun.annotations.Default] allows you to mark
    an argument that's optional in the signature as being a required option.
    """

    __slots__ = ("_default",)

    def __init__(self, default: typing.Any = tanjun.NO_DEFAULT, /) -> None:
        """Initialise a default.

        Parameters
        ----------
        default
            The argument's default.

            If left as [tanjun.abc.NO_DEFAULT][] then the argument will be
            required regardless of the signature default.
        """
        self._default = default

    @property
    def default(self) -> typing.Any:
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

    @typing.overload
    def __init__(
        self, *, aliases: typing.Optional[collections.Sequence[str]] = None, empty_value: typing.Any = tanjun.NO_DEFAULT
    ) -> None:
        ...

    @typing_extensions.deprecated("Use annotations.Default instead of the default arg")
    @typing.overload
    def __init__(
        self,
        *,
        aliases: typing.Optional[collections.Sequence[str]] = None,
        default: typing.Any = tanjun.NO_DEFAULT,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
    ) -> None:
        ...

    def __init__(
        self,
        *,
        aliases: typing.Optional[collections.Sequence[str]] = None,
        default: typing.Any = tanjun.NO_DEFAULT,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
    ) -> None:
        """Create a flag instance.

        Parameters
        ----------
        aliases
            Other names the flag may be triggered by.

            This does not override the argument's name and all the aliases must
            be prefixed with `"-"`.
        empty_value
            Value to pass for the argument if the flag is provided without a value.

            If left undefined then an explicit value will always be needed.

            [tanjun.abc.NO_PASS][] is not supported for this.
        """
        if default is not tanjun.NO_DEFAULT:
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
    @typing_extensions.deprecated("Use annotations.Default instead of the default arg")
    def default(self) -> typing.Any:
        """The flag's default.

        If not specified then the default in the signature for this argument
        will be used.
        """
        return self._default

    @property
    def empty_value(self) -> typing.Any:
        """The value to pass for the argument if the flag is provided without a value.

        If this is [tanjun.abc.NO_DEFAULT][] then a value will be required
        for this flag.
        """
        return self._empty_value

    def set_config(self, config: _ArgConfig, /) -> None:
        if self._default is not tanjun.NO_DEFAULT:
            config.default = self._default

        if self._aliases:
            config.message_names = [config.main_message_name, *self._aliases]

        config.empty_value = self._empty_value
        config.is_positional = False


class _PositionalMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Positional(...) to Annotated")
    def __getitem__(cls, type_: type[_T], /) -> type[_T]:
        return typing.Annotated[type_, Positional()]


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
        positional_arg: Annotated[Str, Positional()] = None,
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ()

    def set_config(self, config: _ArgConfig, /) -> None:
        config.is_positional = True


class _GreedyMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Greedy(...) to Annotated")
    def __getitem__(cls, type_: type[_T], /) -> type[_T]:
        return typing.Annotated[type_, Greedy()]


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
        greedy_arg: Annotated[Str, Greedy()],
        other_greedy_arg: Annotated[Str, Greedy()],
    ) -> None:
        raise NotImplementedError
    ```
    """

    __slots__ = ()

    def set_config(self, config: _ArgConfig, /) -> None:
        config.is_greedy = True


class _LengthMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Length(...) to Annotated")
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
    ) -> None:
        raise NotImplementedError
    ```

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

            Otherwise this will be the minimum length this string option can be.
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
        # TODO: validate this is only set for str options


class _MaxMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Max(...) to Annotated")
    def __getitem__(cls, value: _NumberT, /) -> type[_NumberT]:
        if isinstance(value, int):
            return typing.cast("type[_NumberT]", typing.Annotated[Int, Max(value)])

        return typing.cast("type[_NumberT]", typing.Annotated[Float, Max(value)])


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
        number: Annotated[Float, Max(130.2), "description"],
    ) -> None:
        raise NotImplementedError
    ```
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
    @typing_extensions.deprecated("Pass Min(...) to Annotated")
    def __getitem__(cls, value: _NumberT, /) -> type[_NumberT]:
        if isinstance(value, int):
            return typing.cast("type[_NumberT]", typing.Annotated[Int, Min(value)])

        return typing.cast("type[_NumberT]", typing.Annotated[Float, Min(value)])


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
        number: Annotated[Float, Min(13.9), "description"],
    ) -> None:
        raise NotImplementedError
    ```
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

        if self._message_name:
            config.main_message_name = self._message_name
            config.message_names = [self._message_name, *config.message_names[1:]]


class _RangedMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass Ranged(...) to Annotated")
    def __getitem__(cls, range_: tuple[_NumberT, _NumberT], /) -> type[_NumberT]:
        # This better matches how type checking (well pyright at least) will
        # prefer to go to float if either value is float.
        if isinstance(range_[0], float) or isinstance(range_[1], float):
            return typing.cast("type[_NumberT]", typing.Annotated[Float, Ranged(range_[0], range_[1])])

        return typing.cast("type[_NumberT]", typing.Annotated[Int, Ranged(range_[0], range_[1])])


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
        other_number_arg: Annotated[Float, Ranged(13.69, 420.69), "description"],
    ) -> None:
        raise NotImplementedError
    ```

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
    @typing_extensions.deprecated("Pass SnowflakeOr(...) to Annotated")
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
            "type[typing.Union[hikari.Snowflake, _T]]",
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


class _TheseChannelsMeta(abc.ABCMeta):
    @typing_extensions.deprecated("Pass TheseChannels(...) to Annotated")
    def __getitem__(
        cls, value: typing.Union[_ChannelTypeIsh, collections.Collection[_ChannelTypeIsh]], /
    ) -> type[hikari.PartialChannel]:
        if not isinstance(value, collections.Collection):
            value = (value,)

        return typing.Annotated[Channel, TheseChannels(*value)]


class TheseChannels(_ConfigIdentifier, metaclass=_TheseChannelsMeta):
    """Restrain the type of channels a channel argument can target."""

    __slots__ = ("_channel_types",)

    def __init__(self, channel_type: _ChannelTypeIsh, /, *other_types: _ChannelTypeIsh) -> None:
        """Create a channel argument restraint.

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


def _ensure_value(name: str, type_: type[_T], value: typing.Optional[typing.Any], /) -> typing.Optional[_T]:
    if value is None or isinstance(value, type_):
        return value

    raise TypeError(
        f"{name.capitalize()} value of type {type(value).__name__} is not valid for a {type_.__name__} argument"
    )


def _ensure_values(
    name: str, type_: type[_T], mapping: typing.Optional[collections.Mapping[str, typing.Any]], /
) -> typing.Optional[collections.Mapping[str, _T]]:
    if not mapping:
        return None

    for value in mapping.values():
        if not isinstance(value, type_):
            raise TypeError(
                f"{name.capitalize()} of type {type(value).__name__} is not valid for a {type_.__name__} argument"
            )

    return typing.cast("collections.Mapping[str, _T]", mapping)


_OPTION_TYPE_TO_CONVERTERS: dict[typing.Any, tuple[collections.Callable[..., typing.Any], ...]] = {
    hikari.Attachment: NotImplemented,  # This isn't supported for message commands right now.
    bool: (conversion.to_bool,),
    hikari.PartialChannel: NotImplemented,  # This is special-cased down the line.
    hikari.InteractionChannel: NotImplemented,  # This isn't supported for message commands.
    float: (float,),
    int: (int,),
    hikari.Member: (conversion.to_member,),
    hikari.InteractionMember: NotImplemented,  # This isn't supported for message commands.
    _MentionableUnion: (conversion.to_user, conversion.to_role),
    hikari.Role: (conversion.to_role,),
    str: (),
    hikari.User: (conversion.to_user,),
}


_MESSAGE_ID_ONLY: frozenset[typing.Any] = frozenset(
    [hikari.User, hikari.Role, hikari.Member, hikari.PartialChannel, _MentionableUnion]
)


class _ArgConfig:
    __slots__ = (
        "channel_types",
        "choices",
        "default",
        "description",
        "empty_value",
        "float_converter",
        "has_natural_default",
        "int_converter",
        "is_greedy",
        "is_positional",
        "key",
        "main_message_name",
        "min_length",
        "max_length",
        "min_value",
        "max_value",
        "message_names",
        "option_type",
        "range_or_slice",
        "slash_name",
        "snowflake_converter",
        "str_converters",
    )

    def __init__(self, key: str, default: typing.Any, /, *, description: typing.Optional[str]) -> None:
        self.channel_types: collections.Sequence[_ChannelTypeIsh] = ()
        self.choices: typing.Optional[collections.Mapping[str, _ChoiceUnion]] = None
        self.default: typing.Any = default
        self.description: typing.Optional[str] = description
        self.empty_value: typing.Any = tanjun.NO_DEFAULT
        self.float_converter: typing.Optional[collections.Callable[[float], typing.Any]] = None
        self.has_natural_default: bool = default is tanjun.NO_PASS
        self.int_converter: typing.Optional[collections.Callable[[int], typing.Any]] = None
        # The float and int converters are just for Choices[Enum].
        self.is_greedy: typing.Optional[bool] = None
        self.is_positional: typing.Optional[bool] = None
        self.key: str = key
        self.main_message_name: str = "--" + key.replace("_", "-")
        self.min_length: typing.Optional[int] = None
        self.max_length: typing.Optional[int] = None
        self.min_value: typing.Union[float, int, None] = None
        self.max_value: typing.Union[float, int, None] = None
        self.message_names: collections.Sequence[str] = [self.main_message_name]
        self.option_type: typing.Optional[typing.Any] = None
        self.range_or_slice: typing.Union[range, slice, None] = None
        self.slash_name: str = key
        self.snowflake_converter: typing.Optional[collections.Callable[[str], hikari.Snowflake]] = None
        self.str_converters: collections.Sequence[_ConverterSig[typing.Any]] = ()

    def set_option_type(self, option_type: typing.Any, /) -> None:
        if self.option_type is not None and option_type != self.option_type:
            raise RuntimeError(
                f"Conflicting option types of {self.option_type} and {option_type} found for {self.key!r} parameter"
            )

        self.option_type = option_type

    def from_annotation(self, annotation: typing.Any, /) -> Self:
        for arg in _snoop_annotation_args(annotation):
            if isinstance(arg, _ConfigIdentifier):
                arg.set_config(self)

            elif not self.description and isinstance(arg, str):
                self.description = arg

            elif isinstance(arg, (range, slice)):
                self.range_or_slice = arg

        return self

    def finalise_slice(self) -> Self:
        if not self.range_or_slice:
            return self

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

        return self

    def add_to_msg_cmds(self, commands: collections.Sequence[message.MessageCommand[typing.Any]], /) -> Self:
        if not commands:
            return self

        if self.str_converters:
            converters = self.str_converters

        elif self.option_type:
            if self.snowflake_converter and self.option_type in _MESSAGE_ID_ONLY:
                converters = (self.snowflake_converter,)

            elif (converters_ := _OPTION_TYPE_TO_CONVERTERS[self.option_type]) is not NotImplemented:
                converters = converters_

            elif self.option_type is hikari.PartialChannel:
                converters = (conversion.ToChannel(allowed_types=self.channel_types or None),)

            elif not self.has_natural_default:
                raise RuntimeError(f"{self.option_type!r} is not supported for message commands")

            else:
                # If there is a real default then this should just be left to always default
                # for better interoperability.
                return self

        else:
            return self

        for command in commands:
            if command.parser:
                if not isinstance(command.parser, parsing.AbstractOptionParser):
                    raise TypeError("Expected parser to be an instance of tanjun.parsing.AbstractOptionParser")

                parser = command.parser

            else:
                parser = parsing.ShlexParser()
                command.set_parser(parser)

            if self.is_positional or (self.is_positional is None and self.default is tanjun.NO_DEFAULT):
                parser.add_argument(
                    self.key,
                    converters=converters,
                    default=self.default,
                    greedy=False if self.is_greedy is None else self.is_greedy,
                    min_length=self.min_length,
                    max_length=self.max_length,
                    min_value=self.min_value,
                    max_value=self.max_value,
                )

            elif self.default is tanjun.NO_DEFAULT:
                raise ValueError(f"Flag argument {self.key!r} must have a default")

            else:
                parser.add_option(
                    self.key,
                    *self.message_names,
                    converters=converters,
                    default=self.default,
                    empty_value=self.empty_value,
                    min_length=self.min_length,
                    max_length=self.max_length,
                    min_value=self.min_value,
                    max_value=self.max_value,
                )

        return self

    def add_to_slash_cmds(self, commands: collections.Sequence[slash.SlashCommand[typing.Any]], /) -> Self:
        if self.option_type:
            option_adder = self.SLASH_OPTION_ADDER[self.option_type]
            for command in commands:
                if not self.description:
                    raise ValueError(f"Missing description for argument {self.key!r}")

                option_adder(self, command, self.description)

        return self

    SLASH_OPTION_ADDER: dict[
        typing.Any, collections.Callable[[Self, slash.SlashCommand[typing.Any], str], slash.SlashCommand[typing.Any]]
    ] = {
        hikari.Attachment: lambda self, c, d: c.add_attachment_option(
            self.slash_name, d, default=self.default, key=self.key
        ),
        bool: lambda self, c, d: c.add_bool_option(self.slash_name, d, default=self.default, key=self.key),
        hikari.PartialChannel: lambda self, c, d: c.add_channel_option(
            self.slash_name, d, default=self.default, key=self.key, types=self.channel_types or None
        ),
        float: lambda self, c, d: c.add_float_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", float, self.choices),  # TODO: can we pass ints here as well?
            converters=self.float_converter or (),
            default=self.default,
            key=self.key,
            min_value=self.min_value,  # TODO: explicitly cast to float?
            max_value=self.max_value,
        ),
        int: lambda self, c, d: c.add_int_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", int, self.choices),
            converters=self.int_converter or (),
            default=self.default,
            key=self.key,
            min_value=_ensure_value("min", int, self.min_value),
            max_value=_ensure_value("max", int, self.max_value),
        ),
        hikari.Member: lambda self, c, d: c.add_member_option(self.slash_name, d, default=self.default, key=self.key),
        _MentionableUnion: lambda self, c, d: c.add_mentionable_option(
            self.slash_name, d, default=self.default, key=self.key
        ),
        hikari.Role: lambda self, c, d: c.add_role_option(self.slash_name, d, default=self.default, key=self.key),
        str: lambda self, c, d: c.add_str_option(
            self.slash_name,
            d,
            choices=_ensure_values("choice", str, self.choices),
            converters=self.str_converters,
            default=self.default,
            key=self.key,
            min_length=self.min_length,
            max_length=self.max_length,
        ),
        hikari.User: lambda self, c, d: c.add_user_option(self.slash_name, d, default=self.default, key=self.key),
    }

    SLASH_OPTION_ADDER[hikari.InteractionChannel] = SLASH_OPTION_ADDER[hikari.PartialChannel]
    SLASH_OPTION_ADDER[hikari.InteractionMember] = SLASH_OPTION_ADDER[hikari.Member]


_WRAPPER_TYPES = {typing_extensions.Required, typing_extensions.NotRequired}


def _snoop_annotation_args(type_: typing.Any, /) -> collections.Iterator[typing.Any]:
    origin = typing_extensions.get_origin(type_)
    if origin is typing.Annotated:
        args = typing_extensions.get_args(type_)
        yield from _snoop_annotation_args(args[0])
        yield from args[1:]

    elif origin in _internal.UnionTypes:
        yield from itertools.chain.from_iterable(map(_snoop_annotation_args, typing_extensions.get_args(type_)))

    elif origin in _WRAPPER_TYPES:
        yield from _snoop_annotation_args(typing_extensions.get_args(type_)[0])


def parse_annotated_args(
    command: typing.Union[slash.SlashCommand[typing.Any], message.MessageCommand[typing.Any]],
    /,
    *,
    descriptions: typing.Optional[collections.Mapping[str, str]] = None,
    follow_wrapped: bool = False,
) -> None:
    """Set a command's arguments based on its signature.

    For more information on how this works see
    [with_annotated_args][tanjun.annotations.with_annotated_args] which acts as
    the decorator equivalent of this. The only difference is function allows
    passing a mapping of argument descriptions.

    Parameters
    ----------
    command
        The message or slash command to set the arguments for.
    descriptions
        Mapping of descriptions to use for this command's slash command options.

        If an option isn't included here then this will default back to getting
        the description from its annotation.
    follow_wrapped
        Whether this should also set the arguments on any other command objects
        this wraps in a decorator call chain.
    """
    try:
        signature = inspect.signature(command.callback, eval_str=True)
    except ValueError:  # If we can't inspect it then we have to assume this is a NO
        # As a note, this fails on some "signature-less" builtin functions/types like str.
        return

    descriptions = descriptions or {}
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

        if parameter.kind is not parameter.VAR_KEYWORD:
            if parameter.default is not parameter.empty and isinstance(parameter.default, _ConfigIdentifier):
                arg = _ArgConfig(parameter.name, tanjun.NO_DEFAULT, description=descriptions.get(parameter.name))
                parameter.default.set_config(arg)

            else:
                default = tanjun.NO_DEFAULT if parameter.default is parameter.empty else tanjun.NO_PASS
                arg = _ArgConfig(parameter.name, default, description=descriptions.get(parameter.name))

            (
                arg.from_annotation(parameter.annotation)
                .finalise_slice()
                .add_to_msg_cmds(message_commands)
                .add_to_slash_cmds(slash_commands)
            )
            continue

        if typing_extensions.get_origin(parameter.annotation) is not typing_extensions.Unpack:
            continue

        typed_dict = typing_extensions.get_args(parameter.annotation)[0]
        if not typing_extensions.is_typeddict(typed_dict):
            continue

        for name, annotation in typing_extensions.get_type_hints(typed_dict, include_extras=True).items():
            default = tanjun.NO_PASS if name in typed_dict.__optional_keys__ else tanjun.NO_DEFAULT
            (
                _ArgConfig(name, default, description=descriptions.get(name))
                .from_annotation(annotation)
                .finalise_slice()
                .add_to_msg_cmds(message_commands)
                .add_to_slash_cmds(slash_commands)
            )

    return


@typing.overload
def with_annotated_args(command: _CommandUnionT, /) -> _CommandUnionT:
    ...


@typing.overload
def with_annotated_args(*, follow_wrapped: bool = False) -> collections.Callable[[_CommandUnionT], _CommandUnionT]:
    ...


def with_annotated_args(
    command: typing.Optional[_CommandUnionT] = None, /, *, follow_wrapped: bool = False
) -> typing.Union[_CommandUnionT, collections.Callable[[_CommandUnionT], _CommandUnionT]]:
    r"""Set a command's arguments based on its signature.

    For more information on how this works see [tanjun.annotations][].

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

        def decorator(command: _CommandUnionT, /) -> _CommandUnionT:
            parse_annotated_args(command, follow_wrapped=follow_wrapped)
            return command

        return decorator

    parse_annotated_args(command, follow_wrapped=follow_wrapped)
    return command
