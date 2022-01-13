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

_BasicLocaliserT = typing.TypeVar("_BasicLocaliserT", bound="BasicLocaliser")


class AbstractLocaliser(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def localise(self, tag: str, identifier: str, /, *args: typing.Any, **kwargs: typing.Any) -> typing.Optional[str]:
        """Localise a string with the given identifier and arguments.

        Parameters
        ----------
        tag : str
            The "IETF lang tag" to localise the string to.

            Discord doesn't document this well like at all, nor the standard(s)
            they follow for this, and the cloest you'll get to a conclusive list is
            https://discord.com/developers/docs/dispatch/field-values#predefined-field-values-accepted-locales

            .. note::
                That link may be left out of date due to Discord's lack of care for documenting their API.
        identifier : str
            The unique identifier of the string to localise.
        *args : typing.Any
            Positional arguments to pass to the string as format args.

            .. note::
                Dependent on the implementation, these may be processed before
                being passed to the string.
        **kwargs : typing.Any
            Key-word arguments to pass to the string as format args.

            .. note::
                Dependent on the implementation, these may be processed before
                being passed to the string.

        Returns
        -------
        str
            The localised string.
        """

    def localize(self, tag: str, identifier: str, /, *args: typing.Any, **kwargs: typing.Any) -> typing.Optional[str]:
        """Alias for `AbstractLocaliser.localise`."""
        return self.localise(tag, identifier, *args, **kwargs)

    @abc.abstractmethod
    def get_all_variants(self, identifier: str, /, *args: typing.Any, **kwargs: typing.Any) -> dict[str, str]:
        """Get all the localisation variants for an identifier."""


AbstractLocalizer = AbstractLocaliser
"""Alias of `AbstractLocaliser`."""


class BasicLocaliser(AbstractLocaliser):
    """Standard implementation of `AbstractLocaliser` with only basic text mapping support."""

    __slots__ = ("_tags",)

    def __init__(self) -> None:
        """Initialise a new `BasicLocaliser`."""
        self._tags: dict[str, dict[str, str]] = {}

    def localise(self, tag: str, identifier: str, /, *args: typing.Any, **kwargs: typing.Any) -> typing.Optional[str]:
        # <<inherited docstring from AbstractLocaliser>>.
        if (tag_values := self._tags.get(tag)) and (string := tag_values.get(identifier)):
            return string.format(*args, **kwargs)

    def get_all_variants(self, identifier: str, /, *args: typing.Any, **kwargs: typing.Any) -> dict[str, str]:
        # <<inherited docstring from AbstractLocaliser>>.
        try:
            results = self._tags[identifier]
            if args or kwargs:
                return {name: value.format(*args, **kwargs) for name, value in results.items()}

            return results

        except KeyError:
            return {}


BasicLocalizer = BasicLocaliser
"""Alias of `BasicLocaliser`."""
