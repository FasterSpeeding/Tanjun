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
"""Dependency used for managing localising strings around interactions commands."""
from __future__ import annotations

__all__: list[str] = [
    "AbstractLocaliser",
    "AbstractLocalizer",
    "BasicLocaliser",
    "BasicLocalizer",
]

import abc
import typing
from collections import abc as collections

from .. import abc as tanjun

if typing.TYPE_CHECKING:
    from typing_extensions import Self


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

            This should usually be a [hikari.locales.Locale][].
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
"""Alias of `AbstractLocaliser`."""


class BasicLocaliser(AbstractLocaliser):
    """Standard implementation of `AbstractLocaliser` with only basic text mapping support."""

    __slots__ = ("_tags",)

    def __init__(self) -> None:
        """Initialise a new `BasicLocaliser`."""
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

    def get_all_variants(self, identifier: str, /, **kwargs: typing.Any) -> collections.Mapping[str, str]:
        # <<inherited docstring from AbstractLocaliser>>.
        try:
            results = self._tags[identifier]
            if kwargs:
                results = {name: value.format(**kwargs) for name, value in results.items()}

            else:
                results = results.copy()

            results.pop("default", None)
            return results

        except KeyError:
            return {}

    def localise(self, identifier: str, tag: str, /, **kwargs: typing.Any) -> typing.Optional[str]:
        # <<inherited docstring from AbstractLocaliser>>.
        if (tag_values := self._tags.get(identifier)) and (string := tag_values.get(tag)):
            return string.format(**kwargs)

    def set_variants(
        self,
        identifier: str,
        variants: typing.Optional[collections.Mapping[str, str]] = None,
        /,
        **other_variants: str,
    ) -> Self:
        """Set the variants for a localised field.

        Parameters
        ----------
        identifier
            Identifier of the field to set the localised variants for.

            This may be in any format but the formats used by the standard
            implementations can be found at [client-localiser][].
        variants
            Mapping of [hikari.locales.Locale][]s to the localised values.

        Returns
        -------
        Self
            The localiser object to enable chained calls.
        """
        if variants:
            other_variants.update(variants)

        self._tags[identifier] = other_variants
        return self


BasicLocalizer = BasicLocaliser
"""Alias of `BasicLocaliser`."""
