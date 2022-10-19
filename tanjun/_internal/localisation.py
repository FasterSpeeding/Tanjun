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
"""Internal utility classes and functions used for localisation."""
from __future__ import annotations

__all__: list[str] = []

import itertools
import typing
from collections import abc as collections

import hikari

from .. import _internal
from .. import abc as tanjun
from .. import dependencies

if typing.TYPE_CHECKING:
    from typing_extensions import Self


class MaybeLocalised:
    """Class used for handling name and description localisation."""

    __slots__ = ("default_value", "_field_name", "id", "localised_values")

    def __init__(
        self,
        field_name: str,
        field: typing.Union[str, collections.Mapping[str, str], collections.Iterable[tuple[str, str]]],
        /,
    ) -> None:
        """Initialise an instance of MaybeLocalised.

        Parameters
        ----------
        field_name
            Name of the field being localised.

            This is used in raised exceptions.
        field
            The string value(s) to use for this value.

            If a [str][] is passed here then this will be used as the default
            value and the field's id for overloading it with the localiser.

            When a mapping is passed here, this should be a mapping of locales
            to values. If an "id" fieldis included then this will be used as the
            id for overloading it with the localiser and the first real value
            will be used as the default value.

        Raises
        ------
        RuntimeError
            If no default value is provided when `filed` is a mapping.
        """
        self._field_name = field_name
        if isinstance(field, str):
            self.default_value = field
            self.id: typing.Optional[str] = None
            self.localised_values: dict[str, str] = {}

        else:
            self.localised_values = dict(field)
            self.id = self.localised_values.pop("id", None)
            entry = self.localised_values.pop("default", None)
            if entry is None:
                entry = next(iter(self.localised_values.values()), None)

            if entry is None:
                raise RuntimeError(f"No default {field_name} given")

            self.default_value = entry

    def _values(self) -> collections.Iterable[str]:
        return itertools.chain((self.default_value,), self.localised_values.values())

    def localise(
        self,
        ctx: tanjun.Context,
        localiser: typing.Optional[dependencies.AbstractLocaliser],
        field_type: _NamedFields,
        field_name: str,
        /,
        **kwargs: typing.Any,
    ) -> str:
        """Get the localised value for a context.

        Parameters
        ----------
        ctx
            The context to localise for.
        localiser
            The localiser to use for localising the response,
            if applicable.
        field_type
            The type of field being localised.
        field_name
            Name of the field being localised.

        Returns
        -------
        str
            The localised value or the default value.
        """
        if (self.localised_values or localiser) and isinstance(ctx, tanjun.AppCommandContext):
            if localiser:
                localise_id = self.id or to_localise_id(
                    _TYPE_TO_STR[ctx.type], ctx.triggering_name, field_type, field_name
                )
                if field := localiser.localise(localise_id, ctx.interaction.locale, **kwargs):
                    return field

            return self.localised_values.get(ctx.interaction.locale, self.default_value).format(**kwargs)

        return self.default_value.format(**kwargs)

    def assert_matches(
        self, pattern: str, match: collections.Callable[[str], bool], /, *, lower_only: bool = False
    ) -> Self:
        """Assert that all the values in this match a localised pattern.

        Parameters
        ----------
        pattern
            A string representation of the pattern for use in raised exceptions.
        match
            Pattern match callback.
        lower_only
            Whether this should also assert that all values are considered
            lowercase.
        """
        for value in self._values():
            if not match(value):
                raise ValueError(
                    f"Invalid {self._field_name} provided, {value!r} doesn't match the required regex `{pattern}`"
                )

            if lower_only and value.lower() != value:
                raise ValueError(f"Invalid {self._field_name} provided, {value!r} must be lowercase")

        return self

    def assert_length(self, min_length: int, max_length: int, /) -> Self:
        """Assert that all the lengths in this are within a certain inclusive range.

        Parameters
        ----------
        min_length
            The inclusive minimum length for this.
        max_length
            The inclusive maximum length for this.

        Raises
        ------
        ValueError
            If any of the lengths in this are outside of the provided range.
        """
        lengths = sorted(map(len, self._values()))
        real_min_len = lengths[0]
        real_max_len = lengths[-1]

        if real_max_len > max_length:
            raise ValueError(
                f"{self._field_name.capitalize()} must be less than or equal to {max_length} characters in length"
            )

        if real_min_len < min_length:
            raise ValueError(
                f"{self._field_name.capitalize()} must be greater than or equal to {min_length} characters in length"
            )

        return self


_CommandTypes = typing.Literal["message_menu", "slash", "user_menu"]
_TYPE_TO_STR: dict[hikari.CommandType, _CommandTypes] = {
    hikari.CommandType.MESSAGE: "message_menu",
    hikari.CommandType.SLASH: "slash",
    hikari.CommandType.USER: "user_menu",
}
_NamedFields = typing.Literal["check", "option.description", "option.name"]
_UnnamedFields = typing.Literal["description", "name"]
_FieldType = typing.Union[_NamedFields, _UnnamedFields]


@typing.overload
def to_localise_id(
    command_type: _CommandTypes,
    command_name: str,
    field_type: _NamedFields,
    field_name: str,
    /,
) -> str:
    ...


@typing.overload
def to_localise_id(
    command_type: _CommandTypes,
    command_name: str,
    field_type: _UnnamedFields,
    field_name: typing.Literal[None] = None,
    /,
) -> str:
    ...


def to_localise_id(
    command_type: _CommandTypes,
    command_name: str,
    field_type: _FieldType,
    field_name: typing.Optional[str] = None,
    /,
) -> str:
    """Generate an ID for a localised field.

    Parameters
    ----------
    command_type
        The type of command this field is attached to.
    command_name
        Name of the command this field is attached to.
    field_type
        The type of field this localisation ID is for.
    field_name
        Name of the field this localisation ID is for.

        This doesn't apply to command names and descriptions.

    Returns
    -------
    str
        The generated localied field ID.
    """
    if field_name:
        if field_type == "name" or field_type == "description":
            raise RuntimeError(f"Field_name must not be provided for {field_type} fields")

        return f"{command_type}:{command_name}:{field_type}:{field_name}"

    if field_type != "name" and field_type != "description":
        raise RuntimeError(f"Field_name must be provided for {field_type} fields")

    return f"{command_type}:{command_name}:{field_type}"


def localise_command(cmd_builder: hikari.api.CommandBuilder, localiser: dependencies.AbstractLocaliser, /) -> None:
    """Localise the fields for a command builder.

    Parameters
    ----------
    cmd_builder
        The application command builder to localise the fields for.
    localiser
        The abstract localiser to localise fields with.
    """
    localise_type = _TYPE_TO_STR[cmd_builder.type]
    names = dict(cmd_builder.name_localizations)
    names.update(localiser.get_all_variants(to_localise_id(localise_type, cmd_builder.name, "name")))
    cmd_builder.set_name_localizations(names)

    if isinstance(cmd_builder, hikari.api.SlashCommandBuilder):
        descriptions = dict(cmd_builder.description_localizations)
        descriptions.update(localiser.get_all_variants(to_localise_id(localise_type, cmd_builder.name, "description")))
        cmd_builder.set_description_localizations(descriptions)

        for option in cmd_builder.options:
            _localise_slash_option(option, cmd_builder.name, localiser)


def _localise_slash_option(
    option: hikari.CommandOption, name: str, localiser: dependencies.AbstractLocaliser, /
) -> None:
    if option.type in _internal.SUB_COMMAND_OPTION_TYPES:
        name = f"{name} {option.name}"
        name_variants = localiser.get_all_variants(to_localise_id("slash", name, "name"))
        description_variants = localiser.get_all_variants(to_localise_id("slash", name, "description"))

    else:
        name_variants = localiser.get_all_variants(to_localise_id("slash", name, "option.name", option.name))
        description_variants = localiser.get_all_variants(
            to_localise_id("slash", name, "option.description", option.name)
        )

    option.name_localizations = dict(option.name_localizations)
    option.name_localizations.update(name_variants)
    option.description_localizations = dict(option.description_localizations)
    option.description_localizations.update(description_variants)

    if option.options:
        for option in option.options:
            _localise_slash_option(option, name, localiser)
