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
"""Interface and interval implementation for a Tanjun based event listener."""
from __future__ import annotations

__all__: list[str] = ["as_event_listener", "EventListener", "as_client_callback", "ClientCallback"]

import copy
import typing
from collections import abc as collections

from . import _internal
from . import abc as tanjun
from . import components

if typing.TYPE_CHECKING:
    import hikari
    from typing_extensions import Self


_ListenerCallbackSigT = typing.TypeVar("_ListenerCallbackSigT", bound=tanjun.ListenerCallbackSig[typing.Any])
_ClientCallbackSigT = typing.TypeVar("_ClientCallbackSigT", bound=tanjun.MetaEventSig)


def as_event_listener(
    *event_types: type[hikari.Event],
) -> collections.Callable[[_ListenerCallbackSigT], EventListener[_ListenerCallbackSigT]]:
    """Create an event listener through a decorator call.

    Parameters
    ----------
    *event_types
        One or more event types to listen for.

        If none are provided then the event type(s) will be inferred from
        the callback's type-hints.

    Returns
    -------
    collections.abc.Callable[[ListenerCallbackSig], EventListener[ListenerCallbackSigT]]
        Decorator callback which takes listener to add.

    Raises
    ------
    ValueError
        If nothing was passed for `event_types` and no subclasses of
        [hikari.Event][hikari.events.base_events.Event] are found in the
        type-hint for the callback's first argument.
    """
    return lambda callback: EventListener(callback, *event_types)


class EventListener(typing.Generic[_ListenerCallbackSigT], components.AbstractComponentLoader):
    """An event listener.

    This should be loaded into a component using either
    [Component.load_from_scope][tanjun.components.Component.load_from_scope],
    [Component.add_event_listener][tanjun.components.Component.add_event_listener] or
    [Component.with_event_listener][tanjun.components.Component.with_event_listener] and
    will be registered and unregistered with the linked tanjun client.
    """

    __slots__ = ("_callback", "_event_types")

    def __init__(self, callback: _ListenerCallbackSigT, *event_types: type[hikari.Event]) -> None:
        """Initialise the event listener.

        Parameters
        ----------
        event_types
            One or more event types to listen for.

            If none are provided then the event type(s) will be inferred from
            the callback's type-hints.

        Raises
        ------
        ValueError
            If nothing was passed for `event_types` and no subclasses of
            [hikari.Event][hikari.events.base_events.Event] are found in the
            type-hint for the callback's first argument.
        """
        self._callback = callback
        self._event_types = event_types or _internal.infer_listener_types(callback)

    @property
    def callback(self) -> _ListenerCallbackSigT:
        """The callback that will be registered."""
        return self._callback

    @property
    def event_types(self) -> collections.Sequence[type[hikari.Event]]:
        """The event types to register the callback to."""
        return self._event_types

    if typing.TYPE_CHECKING:
        __call__: _ListenerCallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    def copy(self) -> Self:
        """Create a copy the current instance."""
        inst = copy.copy(self)
        self._event_types = copy.copy(self._event_types)
        return inst

    def load_into_component(self, component: tanjun.Component, /) -> None:
        # <<inherited docstring from tanjun.components.AbstractComponentLoader>>.
        for event_type in self.event_types:
            component.add_listener(event_type, self._callback)


@typing.runtime_checkable
class _ClientCallbackComponentProto(typing.Protocol):
    def add_client_callback(
        self, name: typing.Union[str, tanjun.ClientCallbackNames], /, *callbacks: tanjun.MetaEventSig
    ) -> Self:
        raise NotImplementedError


def as_client_callback(
    name: typing.Union[str, tanjun.ClientCallbackNames]
) -> collections.Callable[[_ClientCallbackSigT], ClientCallback[_ClientCallbackSigT]]:
    """Create an event listener through a decorator call.

    Examples
    --------
    ```py
    client = tanjun.Client.from_rest_bot(bot)

    @client.with_client_callback("closed")
    async def on_close() -> None:
        raise NotImplementedError
    ```

    Parameters
    ----------
    name
        The name this callback is being registered to.

        This is case-insensitive.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MetaEventSig], ClientCallback[tanjun.abc.MetaEventSig]]
        Decorator callback used to register the client callback.

        This may be sync or async and must return None. The positional and
        keyword arguments a callback should expect depend on implementation
        detail around the `name` being subscribed to.
    """
    return lambda callback: ClientCallback(callback, name=name)


class ClientCallback(typing.Generic[_ClientCallbackSigT], components.AbstractComponentLoader):
    """A client callback.

    This should be loaded into a component using either
    [Component.load_from_scope][tanjun.components.Component.load_from_scope],
    [Component.add_client_callback][tanjun.components.Component.add_client_callback] or
    [Component.with_client_callback][tanjun.components.Component.with_client_callback] and
    will be registered and unregistered with the linked tanjun client.
    """

    __slots__ = ("_callback", "_name")

    def __init__(
        self, callback: _ClientCallbackSigT, /, *, name: typing.Union[str, tanjun.ClientCallbackNames]
    ) -> None:
        """Initialise the event listener.

        Parameters
        ----------
        name
            The name this callback is being registered to.

            This is case-insensitive
        """
        self._callback = callback
        self._name = name

    @property
    def callback(self) -> _ClientCallbackSigT:
        """The callback that will be registered."""
        return self._callback

    @property
    def name(self) -> typing.Union[str, tanjun.ClientCallbackNames]:
        """The name the callback will be registered to."""
        return self.name

    if typing.TYPE_CHECKING:
        __call__: _ClientCallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    def copy(self) -> Self:
        """Create a copy the current instance."""
        return copy.copy(self)

    def load_into_component(self, component: tanjun.Component, /) -> None:
        # <<inherited docstring from tanjun.components.AbstractComponentLoader>>.
        if isinstance(component, _ClientCallbackComponentProto):
            component.add_client_callback(self._name, self._callback)
