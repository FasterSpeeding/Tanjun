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
"""Message command implementations."""
from __future__ import annotations

__all__: list[str] = ["MessageCommand", "MessageCommandGroup", "as_message_command", "as_message_command_group"]

import copy
import typing

from .. import _internal
from .. import abc as tanjun
from .. import components
from .. import errors
from .. import hooks as hooks_
from . import base

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from typing_extensions import Self

    _AnyMessageCommandT = typing.TypeVar("_AnyMessageCommandT", bound=tanjun.MessageCommand[typing.Any])
    _AnyCallbackSigT = typing.TypeVar("_AnyCallbackSigT", bound=collections.Callable[..., typing.Any])
    _AnyCommandT = typing.Union[
        tanjun.MenuCommand[_AnyCallbackSigT, typing.Any],
        tanjun.MessageCommand[_AnyCallbackSigT],
        tanjun.SlashCommand[_AnyCallbackSigT],
    ]
    _CallbackishT = typing.Union[_AnyCommandT["_MessageCallbackSigT"], "_MessageCallbackSigT"]
    _OtherCallbackSigT = typing.TypeVar("_OtherCallbackSigT", bound=tanjun.MessageCallbackSig)


_MessageCallbackSigT = typing.TypeVar("_MessageCallbackSigT", bound=tanjun.MessageCallbackSig)
_EMPTY_DICT: typing.Final[dict[typing.Any, typing.Any]] = {}
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()


# While these overloads may seem redundant/unnecessary, MyPy cannot understand
# this when expressed through callback: _CallbackIshT[_MessageCallbackSigT].
class _AsMsgResultProto(typing.Protocol):
    @typing.overload
    def __call__(self, _: _MessageCallbackSigT, /) -> MessageCommand[_MessageCallbackSigT]:
        ...

    @typing.overload
    def __call__(self, _: _AnyCommandT[_MessageCallbackSigT], /) -> MessageCommand[_MessageCallbackSigT]:
        ...


def as_message_command(name: str, /, *names: str, validate_arg_keys: bool = True) -> _AsMsgResultProto:
    """Build a message command from a decorated callback.

    Parameters
    ----------
    name
        The command name.
    *names
        Other names for the command.
    validate_arg_keys
        Whether to validate that option keys match the command callback's signature.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCallbackSig], MessageCommand]
        The decorator callback used to make a [MessageCommand][tanjun.MessageCommand].

        This can either wrap a raw command callback or another callable command
        instance (e.g. [tanjun.MenuCommand][], [MessageCommand][tanjun.MessageCommand],
        [tanjun.SlashCommand][]) and will manage loading the other command into
        a component when using
        [Component.load_from_scope][tanjun.components.Component.load_from_scope].
    """

    def decorator(callback: _CallbackishT[_MessageCallbackSigT], /) -> MessageCommand[_MessageCallbackSigT]:
        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            wrapped_command = callback
            callback = callback.callback

        else:
            wrapped_command = None

        return MessageCommand(
            callback, name, *names, validate_arg_keys=validate_arg_keys, _wrapped_command=wrapped_command
        )

    return decorator


# While these overloads may seem redundant/unnecessary, MyPy cannot understand
# this when expressed through `callback: _CallbackIshT[_MessageCallbackSigT]`.
class _AsGroupResultProto(typing.Protocol):
    @typing.overload
    def __call__(self, _: _MessageCallbackSigT, /) -> MessageCommandGroup[_MessageCallbackSigT]:
        ...

    @typing.overload
    def __call__(self, _: _AnyCommandT[_MessageCallbackSigT], /) -> MessageCommandGroup[_MessageCallbackSigT]:
        ...


def as_message_command_group(
    name: str, /, *names: str, strict: bool = False, validate_arg_keys: bool = True
) -> _AsGroupResultProto:
    """Build a message command group from a decorated callback.

    Parameters
    ----------
    name
        The command name.
    *names
        Other names for the command.
    strict
        Whether this command group should only allow commands without spaces in their names.

        This allows for a more optimised command search pattern to be used and
        enforces that command names are unique to a single command within the group.
    validate_arg_keys
        Whether to validate that option keys match the command callback's signature.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCallbackSig], MessageCommand]
        The decorator callback used to make a [MessageCommandGroup][tanjun.MessageCommandGroup].

        This can either wrap a raw command callback or another callable command
        instance (e.g. [tanjun.MenuCommand][], [MessageCommandGroup][tanjun.MessageCommand],
        [tanjun.SlashCommand][]) and will manage loading the other command into
        a component when using
        [Component.load_from_scope][tanjun.components.Component.load_from_scope].
    """

    def decorator(callback: _CallbackishT[_MessageCallbackSigT], /) -> MessageCommandGroup[_MessageCallbackSigT]:
        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            wrapped_command = callback
            callback = callback.callback

        else:
            wrapped_command = None

        return MessageCommandGroup(
            callback, name, *names, strict=strict, validate_arg_keys=validate_arg_keys, _wrapped_command=wrapped_command
        )

    return decorator


class MessageCommand(base.PartialCommand[tanjun.MessageContext], tanjun.MessageCommand[_MessageCallbackSigT]):
    """Standard implementation of a message command."""

    __slots__ = ("_arg_names", "_callback", "_names", "_parent", "_parser", "_wrapped_command")

    # While these overloads may seem redundant/unnecessary, MyPy cannot understand
    # this when expressed through `callback: _CallbackIshT[_MessageCallbackSigT]`.
    @typing.overload
    def __init__(
        self,
        callback: _MessageCallbackSigT,
        name: str,
        /,
        *names: str,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        callback: _AnyCommandT[_MessageCallbackSigT],
        name: str,
        /,
        *names: str,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    def __init__(
        self,
        callback: _CallbackishT[_MessageCallbackSigT],
        name: str,
        /,
        *names: str,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        """Initialise a message command.

        Parameters
        ----------
        callback : tanjun.abc.MessageCallbackSig
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type [tanjun.abc.MessageContext][], returns [None][]
            and may use dependency injection to access other services.
        name
            The command name.
        *names
            Other names for the command.
        validate_arg_keys
            Whether to validate that option keys match the command callback's signature.
        """
        super().__init__()
        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            callback = callback.callback

        self._arg_names = _internal.get_kwargs(callback) if validate_arg_keys else None
        self._callback: _MessageCallbackSigT = callback
        self._names = list(dict.fromkeys((name, *names)))
        self._parent: typing.Optional[tanjun.MessageCommandGroup[typing.Any]] = None
        self._parser: typing.Optional[tanjun.MessageParser] = None
        self._wrapped_command = _wrapped_command

    def __repr__(self) -> str:
        return f"Command <{self._names}>"

    if typing.TYPE_CHECKING:
        __call__: _MessageCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback(*args, **kwargs)

    @property
    def callback(self) -> _MessageCallbackSigT:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        return self._callback

    @property
    # <<inherited docstring from tanjun.abc.MessageCommand>>.
    def names(self) -> collections.Collection[str]:
        return self._names.copy()

    @property
    def parent(self) -> typing.Optional[tanjun.MessageCommandGroup[typing.Any]]:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        return self._parent

    @property
    def parser(self) -> typing.Optional[tanjun.MessageParser]:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        return self._parser

    @property
    def wrapped_command(self) -> typing.Optional[tanjun.ExecutableCommand[typing.Any]]:
        """The command object this wraps, if any."""
        return self._wrapped_command

    def bind_client(self, client: tanjun.Client, /) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_client(client)
        if self._parser:
            self._parser.bind_client(client)

        return self

    def bind_component(self, component: tanjun.Component, /) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_component(component)
        if self._parser:
            self._parser.bind_component(component)

        return self

    def copy(self, *, parent: typing.Optional[tanjun.MessageCommandGroup[typing.Any]] = None) -> Self:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        inst = super().copy()
        inst._callback = copy.copy(self._callback)
        inst._names = self._names.copy()
        inst._parent = parent
        inst._parser = self._parser.copy() if self._parser else None
        return inst

    def set_parent(self, parent: typing.Optional[tanjun.MessageCommandGroup[typing.Any]], /) -> Self:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        self._parent = parent
        return self

    def set_parser(self, parser: typing.Optional[tanjun.MessageParser], /) -> Self:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        if parser and self._arg_names is not None:
            try:
                name = self.callback.__name__
            except AttributeError:  # Not all callables have names
                name = repr(self.callback)

            parser.validate_arg_keys(name, self._arg_names)

        self._parser = parser
        return self

    async def check_context(self, ctx: tanjun.MessageContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        ctx.set_command(self)
        result = await _internal.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    async def execute(
        self,
        ctx: tanjun.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun.MessageHooks]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        ctx = ctx.set_command(self)
        own_hooks = self._hooks or _EMPTY_HOOKS
        try:
            await own_hooks.trigger_pre_execution(ctx, hooks=hooks)

            if self._parser is not None:
                kwargs = await self._parser.parse(ctx)

            else:
                kwargs = _EMPTY_DICT

            await ctx.call_with_async_di(self._callback, ctx, **kwargs)

        except errors.CommandError as exc:
            await exc.send(ctx)

        except errors.HaltExecution:
            raise

        except Exception as exc:
            if await own_hooks.trigger_error(ctx, exc, hooks=hooks) <= 0:
                raise

        else:
            # TODO: how should this be handled around CommandError?
            await own_hooks.trigger_success(ctx, hooks=hooks)

        finally:
            await own_hooks.trigger_post_execution(ctx, hooks=hooks)

    def load_into_component(self, component: tanjun.Component, /) -> None:
        # <<inherited docstring from tanjun.components.load_into_component>>.
        if not self._parent:
            component.add_message_command(self)

        if self._wrapped_command and isinstance(self._wrapped_command, components.AbstractComponentLoader):
            self._wrapped_command.load_into_component(component)


class MessageCommandGroup(MessageCommand[_MessageCallbackSigT], tanjun.MessageCommandGroup[_MessageCallbackSigT]):
    """Standard implementation of a message command group."""

    __slots__ = ("_commands",)

    # While these overloads may seem redundant/unnecessary, MyPy cannot understand
    # this when expressed through `callback: _CallbackIshT[_MessageCallbackSigT]`.
    @typing.overload
    def __init__(
        self,
        callback: _MessageCallbackSigT,
        name: str,
        /,
        *names: str,
        strict: bool = False,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        callback: _AnyCommandT[_MessageCallbackSigT],
        name: str,
        /,
        *names: str,
        strict: bool = False,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    def __init__(
        self,
        callback: _CallbackishT[_MessageCallbackSigT],
        name: str,
        /,
        *names: str,
        strict: bool = False,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        """Initialise a message command group.

        Parameters
        ----------
        callback : tanjun.abc.MessageCallbackSig
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type [tanjun.abc.MessageContext][], returns [None][]
            and may use dependency injection to access other services.
        name
            The command name.
        *names
            Other names for the command.
        strict
            Whether this command group should only allow commands without spaces in their names.

            This allows for a more optimised command search pattern to be used and
            enforces that command names are unique to a single command within the group.
        validate_arg_keys
            Whether to validate that option keys match the command callback's signature.
        """
        super().__init__(callback, name, *names, validate_arg_keys=validate_arg_keys, _wrapped_command=_wrapped_command)
        self._commands = _internal.MessageCommandIndex(strict)

    def __repr__(self) -> str:
        return f"CommandGroup <{len(self._commands.commands)}: {self._names}>"

    @property
    def commands(self) -> collections.Collection[tanjun.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.MessageCommandGroup>>.
        return self._commands.commands.copy()

    @property
    def is_strict(self) -> bool:
        return self._commands.is_strict

    def copy(self, *, parent: typing.Optional[tanjun.MessageCommandGroup[typing.Any]] = None) -> Self:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        inst = super().copy(parent=parent)
        inst._commands = self._commands.copy(parent=self)
        return inst

    def add_command(self, command: tanjun.MessageCommand[typing.Any], /) -> Self:
        """Add a command to this group.

        Parameters
        ----------
        command
            The command to add.

        Returns
        -------
        Self
            The group instance to enable chained calls.

        Raises
        ------
        ValueError
            If one of the command's names is already registered in a strict
            command group.
        """
        if self._commands.add(command):
            command.set_parent(self)

        return self

    def as_sub_command(
        self, name: str, /, *names: str, validate_arg_keys: bool = True
    ) -> collections.Callable[[_CallbackishT[_OtherCallbackSigT]], MessageCommand[_OtherCallbackSigT]]:
        """Build a message command in this group from a decorated callback.

        Parameters
        ----------
        name
            The command name.
        *names
            Other names for the command.
        validate_arg_keys
            Whether to validate that option keys match the command callback's signature.

        Returns
        -------
        collections.abc.Callable[[tanjun.abc.MessageCallbackSig], MessageCommand]
            The decorator callback used to make a sub-command.

            This can either wrap a raw command callback or another callable command
            instance (e.g. [tanjun.MenuCommand][], [MessageCommand][tanjun.MessageCommand],
            [tanjun.SlashCommand][]).
        """

        def decorator(
            callback: typing.Union[_OtherCallbackSigT, _AnyCommandT[_OtherCallbackSigT]], /
        ) -> MessageCommand[_OtherCallbackSigT]:
            return self.with_command(as_message_command(name, *names, validate_arg_keys=validate_arg_keys)(callback))

        return decorator

    def as_sub_group(
        self, name: str, /, *names: str, strict: bool = False, validate_arg_keys: bool = True
    ) -> collections.Callable[[_CallbackishT[_OtherCallbackSigT]], MessageCommandGroup[_OtherCallbackSigT]]:
        """Build a message command group in this group from a decorated callback.

        Parameters
        ----------
        name
            The command name.
        *names
            Other names for the command.
        strict
            Whether this command group should only allow commands without spaces in their names.

            This allows for a more optimised command search pattern to be used and
            enforces that command names are unique to a single command within the group.
        validate_arg_keys
            Whether to validate that option keys match the command callback's signature.

        Returns
        -------
        collections.abc.Callable[[tanjun.abc.MessageCallbackSig], MessageCommand]
            The decorator callback used to make a sub-command group.

            This can either wrap a raw command callback or another callable command
            instance (e.g. [tanjun.MenuCommand][], [MessageCommand][tanjun.MessageCommand],
            [tanjun.SlashCommand][]).
        """

        def decorator(callback: _CallbackishT[_OtherCallbackSigT], /) -> MessageCommandGroup[_OtherCallbackSigT]:
            return self.with_command(
                as_message_command_group(name, *names, strict=strict, validate_arg_keys=validate_arg_keys)(callback)
            )

        return decorator

    def remove_command(self, command: tanjun.MessageCommand[typing.Any], /) -> Self:
        # <<inherited docstring from tanjun.abc.MessageCommandGroup>>.
        self._commands.remove(command)
        command.set_parent(None)
        return self

    def with_command(self, command: _AnyMessageCommandT, /) -> _AnyMessageCommandT:
        self.add_command(command)
        return command

    def bind_client(self, client: tanjun.Client, /) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_client(client)
        for command in self._commands.commands:
            command.bind_client(client)

        return self

    def bind_component(self, component: tanjun.Component, /) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_component(component)
        for command in self._commands.commands:
            command.bind_component(component)

        return self

    def find_command(
        self, content: str, /, *, case_sensntive: bool = True
    ) -> collections.Iterable[tuple[str, tanjun.MessageCommand[typing.Any]]]:
        return self._commands.find(content, case_sensntive)

    async def execute(
        self,
        ctx: tanjun.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun.MessageHooks]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        if ctx.message.content is None:
            raise ValueError("Cannot execute a command with a content-less message")

        if self._hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._hooks)

        case_sensitive = ctx.client.is_case_sensitive
        if ctx.component and ctx.component.is_case_sensitive is not None:
            case_sensitive = ctx.component.is_case_sensitive

        for name, command in self._commands.find(ctx.content, case_sensitive):
            if await command.check_context(ctx):
                content = ctx.content[len(name) :]
                ctx.set_triggering_name(ctx.triggering_name + " " + name)
                ctx.set_content(content.lstrip())
                await command.execute(ctx, hooks=hooks)
                return

        await super().execute(ctx, hooks=hooks)
