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
"""Aliases of the types and implementations used for dependency injection.

!!! warning "deprecated"
    This module consists solely of deprecated aliases to types and functions
    from the separate `alluka` dependency injection library kept for backwards
    compatibility.
"""
from __future__ import annotations

__all__: list[str] = [
    "AbstractInjectionContext",
    "BasicInjectionContext",
    "CallbackSig",
    "Injected",
    "InjectorClient",
    "SelfInjectingCallback",
    "UNDEFINED",
    "Undefined",
    "UndefinedOr",
    "as_self_injecting",
    "inject",
    "injected",
]

import collections.abc as collections
import typing

import alluka
from alluka import AsyncSelfInjecting as SelfInjectingCallback
from alluka import BasicContext as BasicInjectionContext
from alluka import Client as InjectorClient
from alluka import Injected
from alluka import inject
from alluka import inject as injected
from alluka.abc import UNDEFINED
from alluka.abc import CallbackSig
from alluka.abc import Context as AbstractInjectionContext
from alluka.abc import Undefined

from . import abc as tanjun

_T = typing.TypeVar("_T")
_CallbackSigT = typing.TypeVar("_CallbackSigT", bound=alluka.abc.CallbackSig[typing.Any])

UndefinedOr = typing.Union[Undefined, _T]
"""Type-hint generic union used to indicate that a value may be undefined or `_T`."""


def as_self_injecting(
    client: tanjun.Client, /
) -> collections.Callable[[_CallbackSigT], alluka.AsyncSelfInjecting[_CallbackSigT]]:
    """Make a callback self-inecting by linking it to a client through a decorator call.

    Examples
    --------
    ```py
    def make_callback(client: tanjun.Client) -> collections.abc.Callable[[], int]:
        @tanjun.as_self_injected(client)
        async def get_int_value(
            redis: redis.Client = tanjun.inject(type=redis.Client)
        ) -> int:
            return int(await redis.get('key'))

        return get_int_value
    ```

    Parameters
    ----------
    client : tanjun.abc.Client
        The client to use to resolve dependencies.

    Returns
    -------
    collections.abc.Callable[[alluka.abc.CallbackSig], alluka.AsyncSelfInjecting]
        Decorator callback that returns a self-injecting callback.
    """

    def decorator(callback: _CallbackSigT, /) -> alluka.AsyncSelfInjecting[_CallbackSigT]:
        return alluka.AsyncSelfInjecting(client.injector, callback)

    return decorator
