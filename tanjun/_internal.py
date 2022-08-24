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
"""Internal utility classes and functions used by Tanjun."""
from __future__ import annotations

__all__: list[str] = []

import asyncio
import itertools
import sys
import types
import typing
from collections import abc as collections

import hikari

from . import errors
from ._vendor import inspect

if typing.TYPE_CHECKING:
    import typing_extensions

    from . import abc as tanjun

_KeyT = typing.TypeVar("_KeyT")
_OtherValueT = typing.TypeVar("_OtherValueT")
_ValueT = typing.TypeVar("_ValueT")

if sys.version_info >= (3, 10):
    _UnionTypes = frozenset((typing.Union, types.UnionType))

else:
    _UnionTypes = frozenset((typing.Union,))


async def _execute_check(ctx: tanjun.Context, callback: tanjun.CheckSig, /) -> bool:
    foo = ctx.call_with_async_di(callback, ctx)
    if result := await foo:
        return result

    raise errors.FailedCheck


async def gather_checks(ctx: tanjun.Context, checks: collections.Iterable[tanjun.CheckSig], /) -> bool:
    """Gather a collection of checks.

    Parameters
    ----------
    ctx
        The context to check.
    checks
        An iterable of injectable checks.

    Returns
    -------
    bool
        Whether all the checks passed or not.
    """
    try:
        await asyncio.gather(*(_execute_check(ctx, check) for check in checks))
        # InjectableCheck will raise FailedCheck if a false is received so if
        # we get this far then it's True.
        return True

    except errors.FailedCheck:
        return False


def match_prefix_names(content: str, names: collections.Iterable[str], /) -> typing.Optional[str]:
    """Search for a matching name in a string.

    Parameters
    ----------
    content
        The string to match names against.
    names
        The names to search for.

    Returns
    -------
    str | None
        The name that matched or None if no name matched.
    """
    for name in names:
        # Here we enforce that a name must either be at the end of content or be followed by a space. This helps
        # avoid issues with ambiguous naming where a command with the names "name" and "names" may sometimes hit
        # the former before the latter when triggered with the latter, leading to the command potentially being
        # inconsistently parsed.
        if content == name or content.startswith(name) and content[len(name)] == " ":
            return name


_EMPTY_BUFFER: dict[typing.Any, typing.Any] = {}


class CastedView(collections.Mapping[_KeyT, _OtherValueT], typing.Generic[_KeyT, _ValueT, _OtherValueT]):
    """Utility class for exposing an immutable casted view of a dict."""

    __slots__ = ("_buffer", "_cast", "_raw_data")

    def __init__(self, raw_data: dict[_KeyT, _ValueT], cast: collections.Callable[[_ValueT], _OtherValueT]) -> None:
        self._buffer: dict[_KeyT, _OtherValueT] = {} if raw_data else _EMPTY_BUFFER
        self._cast = cast
        self._raw_data = raw_data

    def __getitem__(self, key: _KeyT, /) -> _OtherValueT:
        try:
            return self._buffer[key]

        except KeyError:
            pass

        entry = self._raw_data[key]
        result = self._cast(entry)
        self._buffer[key] = result
        return result

    def __iter__(self) -> collections.Iterator[_KeyT]:
        return iter(self._raw_data)

    def __len__(self) -> int:
        return len(self._raw_data)


_KEYWORD_TYPES = {inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}


def get_kwargs(callback: collections.Callable[..., typing.Any]) -> list[str] | None:
    """Get a list of the keyword argument names for a callback.

    Parameters
    ----------
    callback
        The callback to get the keyword argument names of.

    Returns
    -------
    list[str] | None
        A list of the keyword argument names for this callback or [None][]
        if this argument takes `**kwargs`.
    """
    names: list[str] = []

    try:
        signature = inspect.Signature.from_callable(callback)

    except ValueError:
        # When "no signature [is] found" for a callback/type, we just don't
        # know what parameters it has so we have to assume var keyword.
        return None

    for parameter in signature.parameters.values():
        if parameter.kind is parameter.VAR_KEYWORD:
            return None

        if parameter.kind in _KEYWORD_TYPES:
            names.append(parameter.name)

    return names


_POSITIONAL_TYPES = {
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL,
}


def _snoop_types(type_: typing.Any, /) -> collections.Iterator[typing.Any]:
    origin = typing.get_origin(type_)
    if origin in _UnionTypes:
        yield from itertools.chain.from_iterable(map(_snoop_types, typing.get_args(type_)))

    elif origin is typing.Annotated:
        yield from _snoop_types(typing.get_args(type_)[0])

    else:
        yield type_


def infer_listener_types(
    callback: collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, None]], /
) -> collections.Sequence[type[hikari.Event]]:
    """Infer the event type(s) of an event listener callback from its annotations.

    Arguments
    ---------
    callback
        The callback to infer the listener types for.

    Returns
    -------
    collections.Sequence[type[hikari.Event]]
        Sequence of the listener types for this callback.

    Raises
    ------
    ValueError
        If the callback's first argument isn't positional or doesn't have
        a type hint.
    TypeError
        If the callback's first positional argument doesn't have any
        [hiari.events.base_events.Event][] subclasses in it.
    """
    try:
        signature = inspect.Signature.from_callable(callback, eval_str=True)
    except ValueError:  # Callback has no signature
        raise ValueError("Missing event type") from None

    try:
        parameter = next(iter(signature.parameters.values()))

    except StopIteration:
        parameter = None

    if not parameter or parameter.kind not in _POSITIONAL_TYPES:
        raise ValueError("Missing positional event argument") from None

    if parameter.annotation is parameter.empty:
        raise ValueError("Missing event argument annotation") from None

    event_types: list[type[hikari.Event]] = []

    for type_ in _snoop_types(parameter.annotation):
        try:
            if issubclass(type_, hikari.Event):
                event_types.append(type_)

        except TypeError:
            pass

    if not event_types:
        raise TypeError(f"No valid event types found in the signature of {callback}") from None

    return event_types


class _WrappedProto(typing.Protocol):
    wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]]


def _has_wrapped(value: typing.Any) -> typing_extensions.TypeGuard[_WrappedProto]:
    try:
        value.wrapped_command

    except AttributeError:
        return False

    return True


def collect_wrapped(command: tanjun.ExecutableCommand[typing.Any]) -> list[tanjun.ExecutableCommand[typing.Any]]:
    """Collect all the commands a command object has wrapped in decorator calls.

    Parameters
    ----------
    command
        The top-level command object.

    Returns
    -------
    list[tanjun.abc.ExecutableCommand[typing.Any]]
        A list of the wrapped commands.
    """
    results: list[tanjun.ExecutableCommand[typing.Any]] = []
    wrapped = command.wrapped_command if _has_wrapped(command) else None

    while wrapped:
        results.append(wrapped)
        wrapped = wrapped.wrapped_command if _has_wrapped(wrapped) else None

    return results
