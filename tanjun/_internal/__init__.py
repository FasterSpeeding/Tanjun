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
"""Internal utility classes and functions used by Tanjun."""
from __future__ import annotations

__all__: list[str] = []

import asyncio
import copy as copy_
import enum
import functools
import itertools
import logging
import operator
import sys
import types
import typing
from collections import abc as collections

import hikari

from .. import errors
from .vendor import inspect

if typing.TYPE_CHECKING:
    import typing_extensions

    from .. import abc as tanjun

    _T = typing.TypeVar("_T")
    _P = typing_extensions.ParamSpec("_P")

    _ContextT = typing.TypeVar("_ContextT", bound=tanjun.Context)
    _CoroT = collections.Coroutine[typing.Any, typing.Any, _T]
    _TreeT = dict[
        typing.Union[str, "_IndexKeys"],
        typing.Union["_TreeT", list[tuple[list[str], tanjun.MessageCommand[typing.Any]]]],
    ]


_KeyT = typing.TypeVar("_KeyT")
_OtherT = typing.TypeVar("_OtherT")

_LOGGER = logging.getLogger("hikari.tanjun")

if sys.version_info >= (3, 10):
    UnionTypes = frozenset((typing.Union, types.UnionType))

else:
    UnionTypes = frozenset((typing.Union,))


class _DefaultEnum(enum.Enum):
    VALUE = object()


DEFAULT = _DefaultEnum.VALUE
"""Internal singleton used to signify when a value wasn't provided."""

Default = typing.Literal[_DefaultEnum.VALUE]
"""The type of `DEFAULT`."""


async def _execute_check(ctx: _ContextT, callback: tanjun.CheckSig[_ContextT], /) -> bool:
    if result := await ctx.call_with_async_di(callback, ctx):
        return result

    raise errors.FailedCheck


async def gather_checks(ctx: _ContextT, checks: collections.Iterable[tanjun.CheckSig[_ContextT]], /) -> bool:
    """Gather a collection of checks.

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The context to check.
    checks : collections.abc.Iterable[tanjun.abc.CheckSig]
        An iterable of injectable checks.

    Returns
    -------
    bool
        Whether all the checks passed or not.
    """
    try:
        await asyncio.gather(*(_execute_check(ctx, check) for check in checks))

    except errors.FailedCheck:
        return False

    else:
        # InjectableCheck will raise FailedCheck if a false is received so if
        # we get this far then it's True.
        return True


_EMPTY_BUFFER: dict[typing.Any, typing.Any] = {}


class CastedView(collections.Mapping[_KeyT, _OtherT]):
    """Utility class for exposing an immutable casted view of a dict."""

    __slots__ = ("_buffer", "_cast", "_raw_data")

    def __init__(self, raw_data: dict[_KeyT, _T], cast: collections.Callable[[_T], _OtherT], /) -> None:
        self._buffer: dict[_KeyT, _OtherT] = {} if raw_data else _EMPTY_BUFFER
        self._cast = cast
        self._raw_data = raw_data

    def __getitem__(self, key: _KeyT, /) -> _OtherT:
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


def get_kwargs(callback: collections.Callable[..., typing.Any], /) -> typing.Union[list[str], None]:
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
    if origin in UnionTypes:
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
    collections.Sequence[type[hikari.events.base_events.Event]]
        Sequence of the listener types for this callback.

    Raises
    ------
    ValueError
        If the callback's first argument isn't positional or doesn't have
        a type hint.
    TypeError
        If the callback's first positional argument doesn't have any
        [hikari.Event][hikari.events.base_events.Event] subclasses in it.
    """
    try:
        signature = inspect.Signature.from_callable(callback, eval_str=True)
    except ValueError:  # Callback has no signature
        raise ValueError("Missing event type") from None

    parameter = next(iter(signature.parameters.values()), None)
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


def log_task_exc(
    message: str, /
) -> collections.Callable[[collections.Callable[_P, collections.Awaitable[_T]]], collections.Callable[_P, _CoroT[_T]]]:
    """Log the exception when a task raises instead of leaving it up to the gods."""

    def decorator(
        callback: collections.Callable[_P, collections.Awaitable[_T]], /
    ) -> collections.Callable[_P, _CoroT[_T]]:
        @functools.wraps(callback)
        async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
            try:
                return await callback(*args, **kwargs)

            except Exception as exc:
                _LOGGER.exception(message, exc_info=exc)
                raise

        return wrapper

    return decorator


class _WrappedProto(typing.Protocol):
    wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]]


def _has_wrapped(value: typing.Any, /) -> typing_extensions.TypeGuard[_WrappedProto]:
    try:
        value.wrapped_command

    except AttributeError:
        return False

    return True


def collect_wrapped(command: tanjun.ExecutableCommand[typing.Any], /) -> list[tanjun.ExecutableCommand[typing.Any]]:
    """Collect all the commands a command object has wrapped in a decorator call chain..

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


def apply_to_wrapped(
    command: tanjun.ExecutableCommand[typing.Any],
    callback: collections.Callable[[tanjun.ExecutableCommand[typing.Any]], object],
    return_value: _T,
    /,
    *,
    follow_wrapped: bool = True,
) -> _T:
    """Apply a callback to all the commands in a decorator call chain.

    Parameters
    ----------
    command
        The top-level command object.
    callback
        Callback each wrapped command should be passed to.
    return_value
        Value to return from this function call.
    follow_wrapped
        Whether this should apply the callback to wrapped commands.
    """
    callback(command)

    if follow_wrapped:
        for wrapped in collect_wrapped(command):
            callback(wrapped)

    return return_value


_OptionT = typing.TypeVar("_OptionT", bound=hikari.CommandInteractionOption)
SUB_COMMAND_OPTION_TYPES: typing.Final[frozenset[hikari.OptionType]] = frozenset(
    [hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP]
)


def flatten_options(
    name: str, options: typing.Optional[collections.Sequence[_OptionT]], /
) -> tuple[str, collections.Sequence[_OptionT]]:
    """Flatten the options of a slash/autocomplete interaction.

    Parameters
    ----------
    options
        The options to flatten.

    Returns
    -------
    tuple[str, collections.abc.Sequence[_OptionT]]
        The full triggering command name and a sequence of the actual command options.
    """
    while options and (first_option := options[0]).type in SUB_COMMAND_OPTION_TYPES:
        name = f"{name} {first_option.name}"
        options = typing.cast("collections.Sequence[_OptionT]", first_option.options)

    return name, options or ()


CHANNEL_TYPES: dict[type[hikari.PartialChannel], set[hikari.ChannelType]] = {
    hikari.GuildTextChannel: {hikari.ChannelType.GUILD_TEXT},
    hikari.DMChannel: {hikari.ChannelType.DM},
    hikari.GuildVoiceChannel: {hikari.ChannelType.GUILD_VOICE},
    hikari.GroupDMChannel: {hikari.ChannelType.GROUP_DM},
    hikari.GuildCategory: {hikari.ChannelType.GUILD_CATEGORY},
    hikari.GuildNewsChannel: {hikari.ChannelType.GUILD_NEWS},
    hikari.GuildStageChannel: {hikari.ChannelType.GUILD_STAGE},
    hikari.GuildNewsThread: {hikari.ChannelType.GUILD_NEWS_THREAD},
    hikari.GuildPublicThread: {hikari.ChannelType.GUILD_PUBLIC_THREAD},
    hikari.GuildPrivateThread: {hikari.ChannelType.GUILD_PRIVATE_THREAD},
    hikari.GuildForumChannel: {hikari.ChannelType.GUILD_FORUM},
}
"""Mapping of hikari channel classes to the raw channel types which are compatible for it."""


for _channel_cls, _types in CHANNEL_TYPES.copy().items():
    for _mro_type in _channel_cls.mro():
        if isinstance(_mro_type, type) and issubclass(_mro_type, hikari.PartialChannel):
            try:
                CHANNEL_TYPES[_mro_type].update(_types)
            except KeyError:
                CHANNEL_TYPES[_mro_type] = _types.copy()

# This isn't a base class but it should still act like an indicator for any channel type.
CHANNEL_TYPES[hikari.InteractionChannel] = CHANNEL_TYPES[hikari.PartialChannel]


def parse_channel_types(*channel_types: typing.Union[type[hikari.PartialChannel], int]) -> list[hikari.ChannelType]:
    """Parse a channel types collection to a list of channel type integers."""
    types_iter = itertools.chain.from_iterable(
        (hikari.ChannelType(type_),) if isinstance(type_, int) else CHANNEL_TYPES[type_] for type_ in channel_types
    )

    try:
        return list(dict.fromkeys(types_iter))

    except KeyError as exc:
        raise ValueError(f"Unknown channel type {exc.args[0]}") from exc


_CHANNEL_TYPE_REPS: dict[hikari.ChannelType, str] = {
    hikari.ChannelType.GUILD_TEXT: "Text",
    hikari.ChannelType.DM: "DM",
    hikari.ChannelType.GUILD_VOICE: "Voice",
    hikari.ChannelType.GROUP_DM: "Group DM",
    hikari.ChannelType.GUILD_CATEGORY: "Category",
    hikari.ChannelType.GUILD_NEWS: "News",
    hikari.ChannelType.GUILD_STAGE: "Stage",
    hikari.ChannelType.GUILD_NEWS_THREAD: "News Thread",
    hikari.ChannelType.GUILD_PUBLIC_THREAD: "Public Thread",
    hikari.ChannelType.GUILD_PRIVATE_THREAD: "Private Thread",
    hikari.ChannelType.GUILD_FORUM: "Forum",
}
_UNKNOWN_CHANNEL_REPR = "Unknown"


def repr_channel(channel_type: hikari.ChannelType, /) -> str:
    """Get a text repr of a channel type."""
    return _CHANNEL_TYPE_REPS.get(channel_type, _UNKNOWN_CHANNEL_REPR)


def cmp_command(
    cmd: typing.Union[hikari.PartialCommand, hikari.api.CommandBuilder],
    other: typing.Union[hikari.PartialCommand, hikari.api.CommandBuilder, None],
    /,
) -> bool:
    """Compare application command objects and command builders."""
    if not other or other.type != cmd.type:
        return False

    dm_enabled = True if cmd.is_dm_enabled is hikari.UNDEFINED else cmd.is_dm_enabled
    other_dm_enabled = True if other.is_dm_enabled is hikari.UNDEFINED else other.is_dm_enabled
    default_perms = cmd.default_member_permissions or hikari.Permissions.NONE
    other_default_perms = other.default_member_permissions or hikari.Permissions.NONE

    if dm_enabled is not other_dm_enabled or default_perms != other_default_perms:
        return False

    # name doesn't need to be checked as `builder` will be `None` if that didn't match.
    if cmd.name_localizations != other.name_localizations:
        return False

    if isinstance(cmd, (hikari.SlashCommand, hikari.api.SlashCommandBuilder)):
        assert isinstance(other, (hikari.SlashCommand, hikari.api.SlashCommandBuilder))
        if cmd.description != other.description or cmd.description_localizations != other.description_localizations:
            return False

        opts = cmd.options or ()
        other_opts = other.options or ()
        return len(opts) == len(other_opts) and all(itertools.starmap(operator.eq, zip(opts, other_opts)))

    return True


def cmp_all_commands(
    commands: collections.Collection[typing.Union[hikari.PartialCommand, hikari.api.CommandBuilder]],
    other: collections.Mapping[
        tuple[hikari.CommandType, str], typing.Union[hikari.PartialCommand, hikari.api.CommandBuilder]
    ],
    /,
) -> bool:
    """Compare two sets of command objects/builders."""
    return len(commands) == len(other) and all(cmp_command(c, other.get((c.type, c.name))) for c in commands)


class _IndexKeys(enum.Enum):
    COMMANDS = enum.auto()
    PARENT = enum.auto()


class MessageCommandIndex:
    """A searchable message command index."""

    __slots__ = ("commands", "is_strict", "names_to_commands", "search_tree")

    def __init__(
        self,
        strict: bool,
        /,
        *,
        commands: typing.Optional[list[tanjun.MessageCommand[typing.Any]]] = None,
        names_to_commands: typing.Optional[dict[str, tuple[str, tanjun.MessageCommand[typing.Any]]]] = None,
        search_tree: typing.Optional[_TreeT] = None,
    ) -> None:
        """Initialise a message command index.

        Parameters
        ----------
        strict
            Whether the index should be strict about command names.

            Command names must be (case-insensitively) unique in a strict index and
            must not contain spaces.
        """
        self.commands = commands or []
        self.is_strict = strict
        self.names_to_commands = names_to_commands or {}
        self.search_tree = search_tree or {}

    def add(self, command: tanjun.MessageCommand[typing.Any], /) -> bool:
        """Add a command to the index.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        bool
            Whether the command was added.

            If this is [False][] then the command was already in the index.

        Raises
        ------
        ValueError
            If the command name is invalid or already in the index.
        """
        if command in self.commands:
            return False

        if self.is_strict:
            if any(" " in name for name in command.names):
                raise ValueError("Command name cannot contain spaces in a strict collection")

            names = list(filter(None, command.names))
            insensitive_names = [name.casefold() for name in command.names]
            if name_conflicts := self.names_to_commands.keys() & insensitive_names:
                raise ValueError(
                    "Sub-command names must be (case-insensitively) unique in a strict collection. "
                    "The following conflicts were found " + ", ".join(name_conflicts)
                )

            # Case insensitive keys are used here as a subsequent check against the original
            # name can be used for case-sensitive lookup.
            self.names_to_commands.update((key, (name, command)) for key, name in zip(insensitive_names, names))

        else:  # strict indexes avoid using the search tree all together.
            # This needs to be explicitly typed for MyPy.
            node: typing.Union[_TreeT, list[tuple[list[str], tanjun.MessageCommand[typing.Any]]]]
            for name in filter(None, command.names):
                node = self.search_tree
                # The search tree is kept case-insensitive as a check against the actual name
                # can be used to ensure case-sensitivity.
                for chars in name.casefold().split(" "):
                    try:
                        node = node[chars]

                    except KeyError:
                        new_node: _TreeT = {_IndexKeys.PARENT: node}
                        node[chars] = node = new_node

                    assert isinstance(node, dict)

                # A case-preserved variant of the name is stored alongside the command
                # for case-sensitive lookup
                # This is split into a list of words to avoid mult-spaces failing lookup.
                name_parts = name.split(" ")
                try:
                    commands = node[_IndexKeys.COMMANDS]
                    assert isinstance(commands, list)
                    commands.append((name_parts, command))
                except KeyError:
                    node[_IndexKeys.COMMANDS] = [(name_parts, command)]

        self.commands.append(command)
        return True

    def copy(self, *, parent: typing.Optional[tanjun.MessageCommandGroup[typing.Any]] = None) -> MessageCommandIndex:
        """In-place copy the index and its contained commands.

        Parameters
        ----------
        parent
            The parent message command group of the copied index.

        Returns
        -------
        MessageCommandIndex
            The copied index.
        """
        commands = {command: command.copy(parent=parent) for command in self.commands}
        memo = {id(command): new_command for command, new_command in commands.items()}
        return MessageCommandIndex(
            self.is_strict,
            commands=list(commands.values()),
            names_to_commands={
                key: (name, commands[command]) for key, (name, command) in self.names_to_commands.items()
            },
            search_tree=copy_.deepcopy(self.search_tree, memo),
        )

    def find(
        self, content: str, case_sensitive: bool, /
    ) -> collections.Iterator[tuple[str, tanjun.MessageCommand[typing.Any]]]:
        """Find commands in the index.

        Parameters
        ----------
        content
            The content to search for.
        case_sensitive
            Whether the search should be case-sensitive.

        Yields
        ------
        tuple[str, tanjun.abc.MessageCommand[typing.Any]]
            A tuple of the matching name and command.
        """
        if self.is_strict:
            name = content.split(" ", 1)[0]
            # A case-insensitive key is used to allow for both the case-sensitive and case-insensitive
            # cases to be covered.
            command = self.names_to_commands.get(name.casefold())
            if command and (not case_sensitive or command[0] == name):
                yield name, command[1]

            # strict indexes avoid using the search tree all together.
            return

        # This needs to be explicitly typed for MyPy.
        node: typing.Union[_TreeT, list[tuple[list[str], tanjun.MessageCommand[typing.Any]]]]
        node = self.search_tree
        segments: list[tuple[int, list[tuple[list[str], tanjun.MessageCommand[typing.Any]]]]] = []
        split = content.split(" ")
        for index, chars in enumerate(split):
            try:
                node = node[chars.casefold()]

            except KeyError:
                break

            else:
                assert isinstance(node, dict)
                if entries := node.get(_IndexKeys.COMMANDS):
                    assert isinstance(entries, list)
                    segments.append((index, entries))

        for index, segment in reversed(segments):
            name_parts = split[: index + 1]
            name = " ".join(name_parts)
            if case_sensitive:
                yield from ((name, c) for n, c in segment if n == name_parts)

            else:
                yield from ((name, c) for _, c in segment)

    def remove(self, command: tanjun.MessageCommand[typing.Any], /) -> None:
        """Remove a command from the index.

        Parameters
        ----------
        command
            The command to remove.

        Raises
        ------
        ValueError
            If the command is not in the index.
        """
        self.commands.remove(command)

        if self.is_strict:
            for name in map(str.casefold, filter(None, command.names)):
                if (entry := self.names_to_commands.get(name)) and entry[1] == command:
                    del self.names_to_commands[name]

            # strict indexes avoid using the search tree all together.
            return

        # This needs to be explicitly typed for MyPy.
        node: typing.Union[_TreeT, list[tuple[list[str], tanjun.MessageCommand[typing.Any]]]]
        for name in filter(None, command.names):
            nodes: list[tuple[str, _TreeT]] = []
            node = self.search_tree
            for chars in name.casefold().split(" "):
                try:
                    node = node[chars]

                except KeyError:
                    # The command is not in the index and we want to skip the "else" statement.
                    break

                else:
                    assert isinstance(node, dict)
                    nodes.append((chars, node))

            else:
                # If it didn't break out of the for chars loop then the command is in here.
                name_parts = name.split(" ")
                entries = node[_IndexKeys.COMMANDS]
                assert isinstance(entries, list)
                entries.remove((name_parts, command))  # Remove the command from the last node.
                if not node[_IndexKeys.COMMANDS]:
                    del node[_IndexKeys.COMMANDS]

                # Otherwise, we need to remove the node from the tree.
                for chars, node in reversed(nodes):
                    if len(node) > 1:
                        # If the node is not empty then we're done.
                        continue

                    parent = node.get(_IndexKeys.PARENT)
                    if not parent:
                        break

                    assert isinstance(parent, dict)
                    del parent[chars]
