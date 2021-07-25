# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
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
from __future__ import annotations

__all__: typing.Sequence[str] = [
    "as_interaction_command",
    "as_message_command",
    "as_message_command_group",
    "InteractionCommand",
    "MessageCommand",
    "MessageCommandGroup",
    "PartialCommand",
]

import copy
import re
import types
import typing

from hikari import errors as hikari_errors
from hikari import snowflakes
from hikari.interactions import commands as command_interactions
from yuyo import backoff

from . import components
from . import errors
from . import hooks as hooks_
from . import injector
from . import traits
from . import utilities

if typing.TYPE_CHECKING:
    from . import parsing

    _InteractionCommandT = typing.TypeVar("_InteractionCommandT", bound="InteractionCommand[typing.Any]")
    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound="MessageCommand[typing.Any]")
    _MessageCommandGroupT = typing.TypeVar("_MessageCommandGroupT", bound="MessageCommandGroup[typing.Any]")
    _PartialCommandT = typing.TypeVar("_PartialCommandT", bound="PartialCommand[typing.Any, typing.Any]")


AnyMessageCommandT = typing.TypeVar("AnyMessageCommandT", bound=traits.MessageCommand)
CommandCallbackSigT = typing.TypeVar("CommandCallbackSigT", bound=traits.CommandCallbackSig)
_EMPTY_DICT: typing.Final[typing.Dict[typing.Any, typing.Any]] = {}
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()
_EMPTY_LIST: typing.Final[typing.List[typing.Any]] = []
_EMPTY_RESOLVED: typing.Final[command_interactions.ResolvedOptionData] = command_interactions.ResolvedOptionData(
    users=_EMPTY_DICT, members=_EMPTY_DICT, roles=_EMPTY_DICT, channels=_EMPTY_DICT
)


class _LoadableInjector(injector.InjectableCheck):
    __slots__: typing.Sequence[str] = ()

    def make_method_type(self, component: traits.Component, /) -> None:
        if isinstance(self.callback, types.MethodType):
            raise ValueError("Callback is already a method type")

        self.callback = types.MethodType(self.callback, component)  # type: ignore[assignment]


class PartialCommand(
    injector.Injectable, traits.ExecutableCommand[traits.ContextT], typing.Generic[CommandCallbackSigT, traits.ContextT]
):
    __slots__: typing.Sequence[str] = (
        "_cached_getters",
        "_callback",
        "_checks",
        "_component",
        "_hooks",
        "_injector",
        "_metadata",
        "_needs_injector",
    )

    def __init__(
        self,
        callback: CommandCallbackSigT,
        /,
        checks: typing.Optional[typing.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.Hooks[traits.ContextT]] = None,
        metadata: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
    ) -> None:
        self._cached_getters: typing.Optional[typing.List[injector.Getter[typing.Any]]] = None
        self._callback: CommandCallbackSigT = callback
        self._checks: typing.Set[injector.InjectableCheck] = (
            set(injector.InjectableCheck(check) for check in checks) if checks else set()
        )
        self._component: typing.Optional[traits.Component] = None
        self._hooks = hooks
        self._injector: typing.Optional[injector.InjectorClient] = None
        self._metadata = dict(metadata) if metadata else {}
        self._needs_injector: typing.Optional[bool] = None

    @property
    def callback(self) -> CommandCallbackSigT:
        return self.callback

    @property
    def checks(self) -> typing.AbstractSet[traits.CheckSig]:
        return {check.callback for check in self._checks}

    @property
    def component(self) -> typing.Optional[traits.Component]:
        return self._component

    @property
    def hooks(self) -> typing.Optional[traits.Hooks[traits.ContextT]]:
        return self._hooks

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def needs_injector(self) -> bool:
        if self._needs_injector is None:
            self._needs_injector = injector.check_injecting(self._callback)

        return self._needs_injector

    if typing.TYPE_CHECKING:
        __call__: CommandCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback(*args, **kwargs)

    def copy(self: _PartialCommandT, *, _new: bool = True) -> _PartialCommandT:
        if not _new:
            self._cached_getters = None
            self._callback = copy.copy(self._callback)
            self._checks = {check.copy() for check in self._checks}
            self._hooks = self._hooks.copy() if self._hooks else None
            self._metadata = self._metadata.copy()
            self._needs_injector = None
            return self

        return copy.copy(self).copy(_new=False)

    def set_hooks(self: _PartialCommandT, hooks: typing.Optional[traits.Hooks[traits.ContextT]], /) -> _PartialCommandT:
        self._hooks = hooks
        return self

    def add_check(self: _PartialCommandT, check: traits.CheckSig, /) -> _PartialCommandT:
        self._checks.add(injector.InjectableCheck(check, injector=self._injector))
        return self

    def remove_check(self, check: traits.CheckSig, /) -> None:
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: traits.CheckSigT, /) -> traits.CheckSigT:
        self._checks.add(_LoadableInjector(check, injector=self._injector))
        return check

    def set_injector(self, client: injector.InjectorClient, /) -> None:
        if self._injector:
            raise RuntimeError("Injector already set")

        self._injector = client

        for check in self._checks:
            check.set_injector(client)

    def bind_client(self, client: traits.Client, /) -> None:
        pass

    def bind_component(self, component: traits.Component, /) -> None:
        self._component = component

    def _get_injection_getters(self) -> typing.Iterable[injector.Getter[typing.Any]]:
        if not self._injector:
            raise ValueError("Cannot execute command without injector client")

        if self._cached_getters is None:
            self._cached_getters = list(self._injector.resolve_callback_to_getters(self._callback))

            if self._needs_injector is None:
                self._needs_injector = bool(self._cached_getters)

        return self._cached_getters

    def make_method_type(self, component: traits.Component, /) -> None:
        if isinstance(self._callback, types.MethodType):
            raise ValueError("Callback is already a method type")

        self._cached_getters = None
        self._callback = types.MethodType(self._callback, component)  # type: ignore[assignment]
        self._needs_injector = None

        for check in self._checks:
            if isinstance(check, _LoadableInjector):
                check.make_method_type(component)


_COMMAND_OPTIONS_TYPES: typing.Final[typing.Set[command_interactions.OptionType]] = {
    command_interactions.OptionType.SUB_COMMAND,
    command_interactions.OptionType.SUB_COMMAND_GROUP,
}
_ICOMMAND_NAME_REG: typing.Final[typing.Pattern[str]] = re.compile(r"^[a-z0-9_-]{1,32}$")


def as_interaction_command(
    name: str, /
) -> typing.Callable[[CommandCallbackSigT], InteractionCommand[CommandCallbackSigT]]:
    def decorator(callback: CommandCallbackSigT, /) -> InteractionCommand[CommandCallbackSigT]:
        return InteractionCommand(callback, name)

    return decorator


class InteractionCommand(PartialCommand[CommandCallbackSigT, traits.InteractionContext], traits.InteractionCommand):
    __slots__: typing.Sequence[str] = ("_name", "_parent", "_tracked_command")

    def __init__(
        self,
        callback: CommandCallbackSigT,
        name: str,
        /,
        *,
        checks: typing.Optional[typing.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.InteractionHooks] = None,
        metadata: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
    ) -> None:
        super().__init__(callback, checks=checks, hooks=hooks, metadata=metadata)
        if not _ICOMMAND_NAME_REG.fullmatch(name):
            raise ValueError("Invalid command name provided, must match the regex `^[a-z0-9_-]{1,32}$`")

        self._name = name
        self._parent: typing.Optional[traits.InteractionCommandGroup] = None
        self._tracked_command: typing.Optional[command_interactions.Command] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent(self) -> typing.Optional[traits.InteractionCommandGroup]:
        return self._parent

    @property
    def tracked_command(self) -> typing.Optional[command_interactions.Command]:
        return self._tracked_command

    def set_parent(
        self: _InteractionCommandT, parent: typing.Optional[traits.InteractionCommandGroup], /
    ) -> _InteractionCommandT:
        self._parent = parent
        return self

    def _process_args(
        self,
        options: typing.Iterable[command_interactions.CommandInteractionOption],
        option_data: command_interactions.ResolvedOptionData,
        /,
    ) -> typing.Dict[str, typing.Any]:
        keyword_args: typing.Dict[str, typing.Any] = {}

        for option in options:
            if option.type in _COMMAND_OPTIONS_TYPES:
                pass

            elif option.type is command_interactions.OptionType.USER:
                assert isinstance(option.value, str)
                user_id = snowflakes.Snowflake(option.value)
                keyword_args[option.name] = option_data.members.get(user_id) or option_data.users[user_id]

            elif option.type is command_interactions.OptionType.CHANNEL:
                assert isinstance(option.value, str)
                keyword_args[option.name] = option_data.channels[snowflakes.Snowflake(option.value)]

            elif option.type is command_interactions.OptionType.ROLE:
                assert isinstance(option.value, str)
                keyword_args[option.name] = option_data.roles[snowflakes.Snowflake(option.value)]

            else:
                keyword_args[option.name] = option.value

        return keyword_args

    async def check_context(self, ctx: traits.MessageContext, /) -> typing.Optional[str]:
        if ctx.content.startswith(self._name) and await utilities.gather_checks(ctx, self._checks):
            return self._name

    async def execute(
        self,
        ctx: traits.InteractionContext,
        /,
        option: typing.Optional[command_interactions.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[typing.MutableSet[traits.InteractionHooks]] = None,
    ) -> None:
        try:
            await (self._hooks or _EMPTY_HOOKS).trigger_pre_execution(ctx, hooks=hooks)

            if option and option.options:
                kwargs = self._process_args(option.options, ctx.interaction.resolved or _EMPTY_RESOLVED)

            elif ctx.interaction.options:
                kwargs = self._process_args(ctx.interaction.options, ctx.interaction.resolved or _EMPTY_RESOLVED)

            else:
                kwargs = _EMPTY_DICT

            if self.needs_injector:
                injected_values = await injector.resolve_getters(ctx, self._get_injection_getters())
                if kwargs is _EMPTY_DICT:
                    kwargs = injected_values

                else:
                    kwargs.update(injected_values)

            await self._callback(ctx, **kwargs)

        except errors.CommandError as exc:
            await ctx.respond(exc.message)

        except errors.HaltExecution:
            return

        except Exception as exc:
            await (self._hooks or _EMPTY_HOOKS).trigger_error(ctx, exc, hooks=hooks)
            raise

        else:
            await (self._hooks or _EMPTY_HOOKS).trigger_success(ctx, hooks=hooks)

        finally:
            await (self._hooks or _EMPTY_HOOKS).trigger_post_execution(ctx, hooks=hooks)


def as_message_command(
    name: str, /, *names: str
) -> typing.Callable[[CommandCallbackSigT], MessageCommand[CommandCallbackSigT]]:
    def decorator(callback: CommandCallbackSigT, /) -> MessageCommand[CommandCallbackSigT]:
        return MessageCommand(callback, name, *names)

    return decorator


def as_message_command_group(
    name: str, /, *names: str
) -> typing.Callable[[CommandCallbackSigT], MessageCommandGroup[CommandCallbackSigT]]:
    def decorator(callback: CommandCallbackSigT, /) -> MessageCommandGroup[CommandCallbackSigT]:
        return MessageCommandGroup(callback, name, *names)

    return decorator


class MessageCommand(PartialCommand[CommandCallbackSigT, traits.MessageContext], traits.MessageCommand):
    __slots__: typing.Sequence[str] = ("_names", "_parent", "_parser")

    def __init__(
        self,
        callback: CommandCallbackSigT,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.MessageHooks] = None,
        metadata: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
        parser: typing.Optional[parsing.AbstractParser] = None,
    ) -> None:
        super().__init__(callback, checks=checks, hooks=hooks, metadata=metadata)
        self._names = {name, *names}
        self._parent: typing.Optional[traits.MessageCommandGroup] = None
        self._parser = parser

    def __repr__(self) -> str:
        return f"Command <{self._names}>"

    @property
    def names(self) -> typing.AbstractSet[str]:
        return self._names.copy()

    @property
    def parent(self) -> typing.Optional[traits.MessageCommandGroup]:
        return self._parent

    @property
    def parser(self) -> typing.Optional[parsing.AbstractParser]:
        return self._parser

    def bind_client(self, client: traits.Client, /) -> None:
        super().bind_client(client)
        if self._parser:
            self._parser.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        super().bind_component(component)
        if self._parser:
            self._parser.bind_component(component)

    def copy(
        self: _MessageCommandT, *, _new: bool = True, parent: typing.Optional[traits.MessageCommandGroup] = None
    ) -> _MessageCommandT:
        if not _new:
            self._names = self._names.copy()
            self._parent = parent
            self._parser = self._parser.copy() if self._parser else None

        return super().copy(_new=_new)

    def set_parent(self: _MessageCommandT, parent: typing.Optional[traits.MessageCommandGroup], /) -> _MessageCommandT:
        self._parent = parent
        return self

    def set_parser(self: _MessageCommandT, parser: typing.Optional[parsing.AbstractParser], /) -> _MessageCommandT:
        self._parser = parser
        return self

    async def check_context(self, ctx: traits.MessageContext, /, *, name_prefix: str = "") -> typing.Optional[str]:
        ctx = ctx.set_command(self)
        if name := self.check_name(ctx.content[len(name_prefix) :].lstrip()):
            if await utilities.gather_checks(ctx, self._checks):
                return name

        ctx.set_command(None)
        return None

    def add_name(self: _MessageCommandT, name: str, /) -> _MessageCommandT:
        self._names.add(name)
        return self

    def check_name(self, name: str, /) -> typing.Optional[str]:
        for own_name in self._names:
            # Here we enforce that a name must either be at the end of content or be followed by a space. This helps
            # avoid issues with ambiguous naming where a command with the names "name" and "names" may sometimes hit
            # the former before the latter when triggered with the latter, leading to the command potentially being
            # inconsistently parsed.
            if name == own_name or name.startswith(own_name) and name[len(own_name)] == " ":
                return own_name

        return None

    def remove_name(self, name: str, /) -> None:
        self._names.remove(name)

    async def execute(
        self,
        ctx: traits.MessageContext,
        /,
        *,
        hooks: typing.Optional[typing.MutableSet[traits.MessageHooks]] = None,
    ) -> None:
        ctx = ctx.set_command(self)
        try:
            await (self._hooks or _EMPTY_HOOKS).trigger_pre_execution(ctx, hooks=hooks)

            if self._parser is not None:
                args, kwargs = await self._parser.parse(ctx)

            else:
                args = _EMPTY_LIST
                kwargs = _EMPTY_DICT

            if self.needs_injector:
                injected_values = await injector.resolve_getters(ctx, self._get_injection_getters())
                if kwargs is _EMPTY_DICT:
                    kwargs = injected_values

                else:
                    kwargs.update(injected_values)

            await self._callback(ctx, *args, **kwargs)

        except errors.CommandError as exc:
            response = exc.message if len(exc.message) <= 2000 else exc.message[:1997] + "..."
            retry = backoff.Backoff(max_retries=5, maximum=2)
            # TODO: preemptive cache based permission checks before throwing to the REST gods.
            async for _ in retry:
                try:
                    await ctx.respond(content=response)

                except (hikari_errors.RateLimitedError, hikari_errors.RateLimitTooLongError) as retry_error:
                    if retry_error.retry_after > 4:
                        raise

                    retry.set_next_backoff(retry_error.retry_after)  # TODO: check if this is too large.

                except hikari_errors.InternalServerError:
                    continue

                except (hikari_errors.ForbiddenError, hikari_errors.NotFoundError):
                    break

                else:
                    break

        except errors.HaltExecution:
            return

        except Exception as exc:
            await (self._hooks or _EMPTY_HOOKS).trigger_error(ctx, exc, hooks=hooks)
            raise

        else:
            # TODO: how should this be handled around CommandError?
            await (self._hooks or _EMPTY_HOOKS).trigger_success(ctx, hooks=hooks)

        finally:
            await (self._hooks or _EMPTY_HOOKS).trigger_post_execution(ctx, hooks=hooks)


class MessageCommandGroup(MessageCommand[CommandCallbackSigT], traits.MessageCommandGroup):
    __slots__: typing.Sequence[str] = ("_commands",)

    def __init__(
        self,
        callback: CommandCallbackSigT,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.MessageHooks] = None,
        metadata: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
        parser: typing.Optional[parsing.AbstractParser] = None,
    ) -> None:
        super().__init__(callback, name, *names, checks=checks, hooks=hooks, metadata=metadata, parser=parser)
        self._commands: typing.Set[traits.MessageCommand] = set()

    def __repr__(self) -> str:
        return f"CommandGroup <{len(self._commands)}: {self._names}>"

    @property
    def commands(self) -> typing.AbstractSet[traits.MessageCommand]:
        return self._commands.copy()

    def copy(
        self: _MessageCommandGroupT, *, _new: bool = True, parent: typing.Optional[traits.MessageCommandGroup] = None
    ) -> _MessageCommandGroupT:
        if not _new:
            self._commands = {command.copy(parent=self) for command in self._commands}

        return super().copy(parent=parent, _new=_new)

    def add_command(self: _MessageCommandGroupT, command: traits.MessageCommand, /) -> _MessageCommandGroupT:
        command.set_parent(self)
        self._commands.add(command)
        return self

    def remove_command(self, command: traits.MessageCommand, /) -> None:
        self._commands.remove(command)
        command.set_parent(None)

    def with_command(self, command: AnyMessageCommandT) -> AnyMessageCommandT:
        self.add_command(command)
        return command

    def bind_client(self, client: traits.Client, /) -> None:
        super().bind_client(client)
        for command in self._commands:
            command.bind_client(client)

    def set_injector(self, client: injector.InjectorClient, /) -> None:
        super().set_injector(client)

        if self._parser and isinstance(self._parser, injector.Injectable):
            self._parser.set_injector(client)

        for command in self._commands:
            if isinstance(command, injector.Injectable):
                command.set_injector(client)

    # I sure hope this plays well with command group recursion cause I am waaaaaaaaaaaaaay too lazy to test that myself.
    async def execute(
        self,
        ctx: traits.MessageContext,
        /,
        *,
        hooks: typing.Optional[typing.MutableSet[traits.MessageHooks]] = None,
    ) -> None:
        if ctx.message.content is None:
            raise ValueError("Cannot execute a command with a contentless message")

        if self._hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._hooks)

        for command in self._commands:
            if name := await command.check_context(ctx):
                # triggering_prefix should never be None here but for the sake of covering all cases if it is then we
                # assume an empty string.
                # If triggering_name is None then we assume an empty string for that as well.
                content = ctx.message.content.lstrip()[len(ctx.triggering_prefix or "") :].lstrip()[
                    len(ctx.triggering_name or "") :
                ]
                space_len = len(content) - len(content.lstrip())
                ctx.set_triggering_name((ctx.triggering_name or "") + (" " * space_len) + name)
                ctx.set_content(ctx.content[space_len + len(name) :].lstrip())
                await command.execute(ctx, hooks=hooks)
                return

        await super().execute(ctx, hooks=hooks)

    def make_method_type(self, component: traits.Component, /) -> None:
        super().make_method_type(component)
        for command in self._commands:
            if isinstance(command, components.LoadableProtocol):
                command.make_method_type(component)
