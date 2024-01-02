# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2024, Faster Speeding
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
"""Dependency used for managing localising strings around interactions commands."""
from __future__ import annotations

__all__: list[str] = ["AbstractLocaliser", "AbstractLocalizer", "BasicLocaliser", "BasicLocalizer"]

import abc
import re
import typing

import hikari

from .._internal import localisation

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from typing_extensions import Self

    from .. import abc as tanjun


_CHECK_NAME_PATTERN = re.compile(r"^(?P<command_type>[^:]+):(?P<command_name>[^:]+):check:(?P<check_name>.+)$")
_DYNAMIC = "*"


class AbstractLocaliser(abc.ABC):
    """Abstract class of a string localiser."""

    __slots__ = ()

    @abc.abstractmethod
    def get_all_variants(self, identifier: str, /, **kwargs: typing.Any) -> collections.Mapping[str, str]:
        """Get all the localisation variants for an identifier."""

    @abc.abstractmethod
    def localise(self, identifier: str, tag: str, /, **kwargs: typing.Any) -> typing.Optional[str]:
        """Localise a string with the given identifier and arguments.

        Parameters
        ----------
        identifier
            The unique identifier of the string to localise.

            This may be in any format but the formats used by the standard
            implementations can be found at [client-localiser][].
        tag
            The "IETF lang tag" to localise the string to.

            This should usually be a [hikari.Locale][hikari.locales.Locale].
        **kwargs
            Key-word arguments to pass to the string as format args.

        Returns
        -------
        str
            The localised string.
        """

    def localize(self, identifier: str, tag: str, /, **kwargs: typing.Any) -> typing.Optional[str]:
        """Alias for `AbstractLocaliser.localise`."""
        return self.localise(identifier, tag, **kwargs)


AbstractLocalizer = AbstractLocaliser
"""Alias of [AbstractLocaliser][tanjun.dependencies.AbstractLocaliser]."""

_EMPTY_DICT: dict[str, str] = {}


class BasicLocaliser(AbstractLocaliser):
    """Standard implementation of `AbstractLocaliser` with only basic text mapping support."""

    __slots__ = ("_dynamic_tags", "_tags")

    def __init__(self) -> None:
        """Initialise a new `BasicLocaliser`."""
        self._dynamic_tags: dict[str, dict[str, str]] = {}
        self._tags: dict[str, dict[str, str]] = {}

    def add_to_client(self, client: tanjun.Client, /) -> None:
        """Add this global localiser to a tanjun client.

        !!! note
            This registers the manager as a type dependency to let Tanjun use it.

        Parameters
        ----------
        client
            The client to add this global localiser to.
        """
        client.set_type_dependency(AbstractLocalizer, self)

    def _get_dynamic(self, identifier: str, /) -> typing.Optional[dict[str, str]]:
        if self._dynamic_tags and (match := _CHECK_NAME_PATTERN.fullmatch(identifier)):
            command_type, _, check_name = match.groups()
            return self._dynamic_tags.get(f"{command_type}:*:check:{check_name}")

        return None  # MyPy compat

    def get_all_variants(self, identifier: str, /, **kwargs: typing.Any) -> collections.Mapping[str, str]:
        # <<inherited docstring from AbstractLocaliser>>.
        results = (self._get_dynamic(identifier) or _EMPTY_DICT) | self._tags.get(identifier, _EMPTY_DICT)
        if results and kwargs:
            results = {name: value.format(**kwargs) for name, value in results.items()}

        results.pop("default", None)
        return results

    def localise(self, identifier: str, tag: str, /, **kwargs: typing.Any) -> typing.Optional[str]:
        # <<inherited docstring from AbstractLocaliser>>.
        if (tag_values := self._tags.get(identifier)) and (string := tag_values.get(tag)):
            return string.format(**kwargs)

        if (tag_values := self._get_dynamic(identifier)) and (string := tag_values.get(tag)):
            return string.format(**kwargs)

        return None  # MyPy compat

    def set_variants(
        self, identifier: str, variants: typing.Optional[collections.Mapping[str, str]] = None, /, **other_variants: str
    ) -> Self:
        """Set the variants for a localised field.

        Parameters
        ----------
        identifier
            Identifier of the field to set the localised variants for.

            This may be in any format but the formats used by the standard
            implementations can be found at [client-localiser][].
        variants
            Mapping of [hikari.Locale][hikari.locales.Locale]s to the
            localised values.

        Returns
        -------
        Self
            The localiser object to enable chained calls.
        """
        all_variants = {_normalise_key(key): value for key, value in other_variants.items()}
        if variants:
            all_variants.update(variants)

        dynamic_match = _CHECK_NAME_PATTERN.fullmatch(identifier)
        if not dynamic_match:
            self._tags[identifier] = all_variants
            return self

        command_type, command_name, check_name = dynamic_match.groups()
        if command_type == _DYNAMIC:
            for command_type in localisation.COMMAND_TYPES:
                self.set_variants(f"{command_type}:{command_name}:check:{check_name}", all_variants)

        elif command_name == _DYNAMIC:
            self._dynamic_tags[identifier] = all_variants

        else:
            self._tags[identifier] = all_variants

        return self


def _normalise_key(key: str, /) -> str:
    try:
        return hikari.Locale[key.upper()]

    except KeyError:
        return key


BasicLocalizer = BasicLocaliser
"""Alias of [BasicLocaliser][tanjun.dependencies.BasicLocaliser]."""
