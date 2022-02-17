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

.. deprecated::
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

from . import abc as tanjun_abc

_T = typing.TypeVar("_T")
CallbackSig = alluka.abc.CallbackSig[_T]
"""Type-hint of a injector callback.

.. note::
    Dependency dependency injection is recursively supported, meaning that the
    keyword arguments for a dependency callback may also ask for dependencies
    themselves.

This may either be a synchronous or asynchronous function with dependency
injection being available for the callback's keyword arguments but dynamically
returning either an awaitable or raw value may lead to errors.

Dependent on the context positional arguments may also be proivded.
"""


Undefined = alluka.abc.Undefined
"""Class/type of `UNDEFINED`."""


UNDEFINED: typing.Final[alluka.abc.Undefined] = alluka.abc.UNDEFINED
"""Singleton value used within dependency injection to indicate that a value is undefined."""
UndefinedOr = typing.Union[Undefined, _T]
"""Type-hint generic union used to indicate that a value may be undefined or `_T`."""


AbstractInjectionContext = alluka.abc.Context
"""Abstract interface of an injection context."""


BasicInjectionContext = alluka.abc.Context
"""Basic implementation of a `AbstractInjectionContext`."""


SelfInjectingCallback = alluka.SelfInjecting
"""Class used to make a callback self-injecting by linking it to a client."""


def as_self_injecting(
    client: tanjun_abc.Client, /
) -> collections.Callable[[CallbackSig[_T]], alluka.SelfInjecting[_T]]:
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
    collections.abc.Callable[[CallbackSig[_T]], alluka.SelfInjecting[_T]]
        Decorator callback that returns a self-injecting callback.
    """

    def decorator(callback: CallbackSig[_T], /) -> alluka.SelfInjecting[_T]:
        return alluka.SelfInjecting(client.injector, callback)

    return decorator


Injected = alluka.InjectedDescriptor


inject = alluka.inject
"""Decare a keyword-argument as requiring an injected dependency.

This should be assigned to an arugment's default value.

Examples
--------
```py
@tanjun.as_slash_command("name", "description")
async def command_callback(
    ctx: tanjun.abc.Context,
    # Here we take advantage of scope based special casing which allows
    # us to inject the `Component` type.
    injected_type: tanjun.abc.Component = tanjun.inject(type=tanjun.abc.Component)
    # Here we inject an out-of-scope callback which itself is taking
    # advantage of type injection.
    callback_result: ResultT = tanjun.inject(callback=injected_callback)
) -> None:
    raise NotImplementedError
```

Parameters
----------
callback : CallbackSig[_T] | None
    The callback to use to resolve the dependency.

    If this callback has no type dependencies then this will still work
    without an injection context but this can be overridden using
    `InjectionClient.set_callback_override`.
type : type[_T] | None
    The type of the dependency to resolve.

    If a union (e.g. `typing.Union[A, B]`, `A | B`, `typing.Optional[A]`)
    is passed for `type` then each type in the union will be tried
    separately after the litarl union type is tried, allowing for resolving
    `A | B` to the value set by `set_type_dependency(B, ...)`.

    If a union has `None` as one of its types (including `Optional[T]`)
    then `None` will be passed for the parameter if none of the types could
    be resolved using the linked client.

Raises
------
ValueError
    If both `callback` and `type` are specified or if neither is specified.
"""


injected = inject
"""Alias of `inject`."""


InjectorClient = alluka.Client
"""Dependency injection client used by Tanjun's standard implementation."""
