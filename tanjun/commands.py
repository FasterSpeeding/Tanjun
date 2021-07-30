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

__all__: list[str] = [
    "AnyMessageCommandT",
    "CommandCallbackSigT",
    "ConverterSig",
    "as_message_command",
    "as_message_command_group",
    "as_slash_command",
    "MessageCommand",
    "MessageCommandGroup",
    "PartialCommand",
    "SlashCommand",
    "with_str_slash_option",
    "with_int_slash_option",
    "with_bool_slash_option",
    "with_role_slash_option",
    "with_user_slash_option",
    "with_member_slash_option",
    "with_channel_slash_option",
    "with_mentionable_slash_option",
]

import copy
import logging
import re
import types
import typing
from collections import abc as collections

import hikari
from yuyo import backoff

from . import components
from . import conversion
from . import errors
from . import hooks as hooks_
from . import injecting
from . import traits
from . import utilities

if typing.TYPE_CHECKING:

    from hikari.api import special_endpoints as special_endpoints_api

    from . import parsing

    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound="MessageCommand[typing.Any]")
    _MessageCommandGroupT = typing.TypeVar("_MessageCommandGroupT", bound="MessageCommandGroup[typing.Any]")
    _PartialCommandT = typing.TypeVar("_PartialCommandT", bound="PartialCommand[typing.Any, typing.Any]")
    _SlashCommandT = typing.TypeVar("_SlashCommandT", bound="SlashCommand[typing.Any]")


AnyMessageCommandT = typing.TypeVar("AnyMessageCommandT", bound=traits.MessageCommand)
CommandCallbackSigT = typing.TypeVar("CommandCallbackSigT", bound=traits.CommandCallbackSig)
ConverterSig = collections.Callable[..., typing.Union[collections.Awaitable[typing.Any], typing.Any]]
"""Type hint of a converter used within a parser instance."""
_EMPTY_DICT: typing.Final[dict[typing.Any, typing.Any]] = {}
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()
_EMPTY_LIST: typing.Final[list[typing.Any]] = []
_EMPTY_RESOLVED: typing.Final[hikari.ResolvedOptionData] = hikari.ResolvedOptionData(
    users=_EMPTY_DICT, members=_EMPTY_DICT, roles=_EMPTY_DICT, channels=_EMPTY_DICT
)
_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun.commands")


class _LoadableInjector(injecting.InjectableCheck):
    __slots__ = ()

    def make_method_type(self, component: traits.Component, /) -> None:
        if isinstance(self.callback, types.MethodType):
            raise ValueError("Callback is already a method type")

        self.callback = types.MethodType(self.callback, component)  # type: ignore[assignment]


class PartialCommand(
    injecting.Injectable,
    traits.ExecutableCommand[traits.ContextT],
    typing.Generic[CommandCallbackSigT, traits.ContextT],
):
    __slots__ = (
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
        checks: typing.Optional[collections.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.Hooks[traits.ContextT]] = None,
        metadata: typing.Optional[collections.MutableMapping[typing.Any, typing.Any]] = None,
    ) -> None:
        self._cached_getters: typing.Optional[list[injecting.Getter[typing.Any]]] = None
        self._callback: CommandCallbackSigT = callback
        self._checks: set[injecting.InjectableCheck] = (
            set(injecting.InjectableCheck(check) for check in checks) if checks else set()
        )
        self._component: typing.Optional[traits.Component] = None
        self._hooks = hooks
        self._injector: typing.Optional[injecting.InjectorClient] = None
        self._metadata = dict(metadata) if metadata else {}
        self._needs_injector: typing.Optional[bool] = None

    @property
    def callback(self) -> CommandCallbackSigT:
        return self._callback

    @property
    def checks(self) -> collections.Set[traits.CheckSig]:
        return {check.callback for check in self._checks}

    @property
    def component(self) -> typing.Optional[traits.Component]:
        return self._component

    @property
    def hooks(self) -> typing.Optional[traits.Hooks[traits.ContextT]]:
        return self._hooks

    @property
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def needs_injector(self) -> bool:
        if self._needs_injector is None:
            self._needs_injector = injecting.check_injecting(self._callback)

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
        self._checks.add(injecting.InjectableCheck(check, injector=self._injector))
        return self

    def remove_check(self, check: traits.CheckSig, /) -> None:
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: traits.CheckSigT, /) -> traits.CheckSigT:
        self._checks.add(_LoadableInjector(check, injector=self._injector))
        return check

    def set_injector(self, client: injecting.InjectorClient, /) -> None:
        if self._injector:
            raise RuntimeError("Injector already set")

        self._injector = client

        for check in self._checks:
            check.set_injector(client)

    def bind_client(self, client: traits.Client, /) -> None:
        pass

    def bind_component(self, component: traits.Component, /) -> None:
        self._component = component

    def _get_injection_getters(self) -> collections.Iterable[injecting.Getter[typing.Any]]:
        if not self._injector:
            raise ValueError("Cannot execute command without injector client")

        if self._cached_getters is None:
            self._cached_getters = list(self._injector.resolve_callback_to_getters(self._callback))

            if self._needs_injector is None:
                self._needs_injector = bool(self._cached_getters)

        return self._cached_getters

    def load_into_component(
        self, component: traits.Component, /
    ) -> typing.Optional[PartialCommand[CommandCallbackSigT, traits.ContextT]]:
        if isinstance(self._callback, types.MethodType):
            raise ValueError("Callback is already a method type")

        self._cached_getters = None
        self._callback = types.MethodType(self._callback, component)  # type: ignore[assignment]
        self._needs_injector = None

        for check in self._checks:
            if isinstance(check, _LoadableInjector):
                check.make_method_type(component)

        return None


_MEMBER_OPTION_TYPES: typing.Final[set[hikari.OptionType]] = {hikari.OptionType.USER, hikari.OptionType.MENTIONABLE}
_OBJECT_OPTION_TYPES: typing.Final[set[hikari.OptionType]] = {
    hikari.OptionType.USER,
    hikari.OptionType.CHANNEL,
    hikari.OptionType.MENTIONABLE,
}
_SUB_COMMAND_OPTIONS_TYPES: typing.Final[set[hikari.OptionType]] = {
    hikari.OptionType.SUB_COMMAND,
    hikari.OptionType.SUB_COMMAND_GROUP,
}
_SCOMMAND_NAME_REG: typing.Final[re.Pattern[str]] = re.compile(r"^[a-z0-9_-]{1,32}$")


def as_slash_command(
    name: str, description: str, /, *, default_to_ephemeral: bool = False, is_global: bool = True
) -> collections.Callable[[CommandCallbackSigT], SlashCommand[CommandCallbackSigT]]:
    def decorator(callback: CommandCallbackSigT, /) -> SlashCommand[CommandCallbackSigT]:
        return SlashCommand(callback, name, description, default_to_ephemeral=default_to_ephemeral, is_global=is_global)

    return decorator


_UNDEFINED_DEFAULT = object()


def with_str_slash_option(
    name: str,
    description: str,
    /,
    *,
    choices: typing.Optional[collections.Iterable[typing.Union[tuple[str, str], str]]] = None,
    converters: typing.Union[collections.Sequence[ConverterSig], ConverterSig, None] = None,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    if choices:
        new_choices = (choice if isinstance(choice, tuple) else (choice.capitalize(), choice) for choice in choices)

    return lambda c: c.add_option(
        name, description, hikari.OptionType.STRING, default=default, choices=new_choices, converters=converters
    )


def with_int_slash_option(
    name: str,
    description: str,
    /,
    *,
    choices: typing.Optional[collections.Iterable[tuple[str, int]]] = None,
    converters: typing.Union[collections.Collection[ConverterSig], ConverterSig, None] = None,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(
        name, description, hikari.OptionType.INTEGER, default=default, choices=choices, converters=converters
    )


def with_bool_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(name, description, hikari.OptionType.BOOLEAN, default=default)


def with_user_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(name, description, hikari.OptionType.USER, default=default)


def with_member_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(name, description, hikari.OptionType.USER, default=default, only_member=True)


def with_channel_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(name, description, hikari.OptionType.CHANNEL, default=default)


def with_role_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(name, description, hikari.OptionType.ROLE, default=default)


def with_mentionable_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    return lambda c: c.add_option(name, description, hikari.OptionType.MENTIONABLE, default=default)


def _convert_to_injectable(converter: ConverterSig) -> injecting.InjectableConverter[typing.Any]:
    if isinstance(converter, injecting.InjectableConverter):
        return typing.cast("injecting.InjectableConverter[typing.Any]", converter)

    return injecting.InjectableConverter(conversion.override_type(converter))


class _TrackedOption(injecting.Injectable):
    __slots__ = ("converters", "default", "is_only_member", "name", "type")

    def __init__(
        self,
        name: str,
        option_type: int,
        converters: list[injecting.InjectableConverter[typing.Any]],
        only_member: bool,
        default: typing.Any = _UNDEFINED_DEFAULT,
    ) -> None:
        self.converters = converters
        self.default = default
        self.is_only_member = only_member
        self.name = name
        self.type = option_type

    @property
    def needs_injector(self) -> bool:
        return any(converter.needs_injector for converter in self.converters)

    async def convert(self, ctx: traits.SlashContext, value: typing.Any, /) -> typing.Any:
        if not self.converters:
            return value

        exceptions: list[ValueError] = []
        for converter in self.converters:
            try:
                return await converter(value, ctx)

            except ValueError as exc:
                exceptions.append(exc)

        raise errors.ConversionError(self.name, f"Couldn't convert {self.type} '{self.name}'", errors=exceptions)

    def set_injector(self, client: injecting.InjectorClient, /) -> None:
        super().set_injector(client)
        for converter in self.converters:
            converter.set_injector(client)


class SlashCommand(PartialCommand[CommandCallbackSigT, traits.SlashContext], traits.SlashCommand):
    __slots__ = (
        "_builder",
        "_defaults_to_ephemeral",
        "_description",
        "_is_global",
        "_name",
        "_parent",
        "_tracked_command",
        "_tracked_options",
    )

    def __init__(
        self,
        callback: CommandCallbackSigT,
        name: str,
        description: str,
        /,
        *,
        default_to_ephemeral: bool = False,
        is_global: bool = True,
        checks: typing.Optional[collections.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.SlashHooks] = None,
        metadata: typing.Optional[collections.MutableMapping[typing.Any, typing.Any]] = None,
    ) -> None:
        super().__init__(callback, checks=checks, hooks=hooks, metadata=metadata)
        if not _SCOMMAND_NAME_REG.fullmatch(name):
            raise ValueError("Invalid command name provided, must match the regex `^[a-z0-9_-]{1,32}$`")

        self._builder = hikari.impl.CommandBuilder(name, description)
        self._defaults_to_ephemeral = default_to_ephemeral
        self._description = description
        self._is_global = is_global
        self._name = name
        self._parent: typing.Optional[traits.SlashCommandGroup] = None
        self._tracked_command: typing.Optional[hikari.Command] = None
        self._tracked_options: dict[str, _TrackedOption] = {}

    @property
    def defaults_to_ephemeral(self) -> bool:
        return self._defaults_to_ephemeral

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_global(self) -> bool:
        return self._is_global

    @property
    def name(self) -> str:
        return self._name

    @property
    def needs_injector(self) -> bool:
        return super().needs_injector or any(option.needs_injector for option in self._tracked_options.values())

    def set_injector(self, client: injecting.InjectorClient, /) -> None:
        super().set_injector(client)
        for option in self._tracked_options.values():
            option.set_injector(client)

    @property
    def parent(self) -> typing.Optional[traits.SlashCommandGroup]:
        return self._parent

    @property
    def tracked_command(self) -> typing.Optional[hikari.Command]:
        return self._tracked_command

    def add_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        type: typing.Union[hikari.OptionType, int] = hikari.OptionType.STRING,
        *,
        choices: typing.Optional[collections.Iterable[tuple[str, typing.Union[str, int, float]]]] = None,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig, None] = None,
        default: typing.Any = _UNDEFINED_DEFAULT,
        only_member: bool = False,
    ) -> _SlashCommandT:
        # TODO: validate name
        type = hikari.OptionType(type)
        if type in _SUB_COMMAND_OPTIONS_TYPES:
            raise NotImplementedError

        if only_member and type not in _MEMBER_OPTION_TYPES:
            raise ValueError("Specifically member may only be set for a USER or MENTIONABLE option")

        if not converters:
            converters = list[injecting.InjectableConverter[typing.Any]]()

        elif isinstance(converters, collections.Iterable):
            converters = list(map(_convert_to_injectable, converters))

        else:
            converters = [_convert_to_injectable(converters)]

        if converters and (type in _OBJECT_OPTION_TYPES or type == hikari.OptionType.BOOLEAN):
            raise ValueError("Converters cannot be provided for bool or object options")

        choices_ = [hikari.CommandChoice(name=name, value=value) for name, value in choices] if choices else None
        required = default is not _UNDEFINED_DEFAULT
        self._builder.add_option(
            hikari.CommandOption(type=type, name=name, description=description, is_required=required, choices=choices_)
        )
        if _SUB_COMMAND_OPTIONS_TYPES:
            self._tracked_options[name] = _TrackedOption(
                name=name,
                option_type=type,
                converters=converters,
                default=default,
                only_member=only_member,
            )
        return self

    # async def add_to_guild(self, guild: hikari.SnowflakeishOr[guilds.PartialGuild], /) -> hikari.Command:
    #     return await self._

    def build(self) -> special_endpoints_api.CommandBuilder:
        return self._builder

    def set_ephemeral_default(self: _SlashCommandT, state: bool, /) -> _SlashCommandT:
        self._defaults_to_ephemeral = state
        return self

    def set_parent(self: _SlashCommandT, parent: typing.Optional[traits.SlashCommandGroup], /) -> _SlashCommandT:
        self._parent = parent
        return self

    async def _process_args(
        self,
        ctx: traits.SlashContext,
        options: collections.Iterable[hikari.CommandInteractionOption],
        option_data: hikari.ResolvedOptionData,
        /,
    ) -> dict[str, typing.Any]:
        keyword_args: dict[str, typing.Any] = {}
        options_dict = {option.name: option for option in options}
        for tracked_option in self._tracked_options.values():
            option = options_dict.get(tracked_option.name)
            if not option or not option.value:
                if tracked_option.default is _UNDEFINED_DEFAULT:
                    # raise errors.ConversionError(
                    #     tracked_option.name,
                    #     "Found value-less or missing option for a option for tracked option with no default"
                    # )
                    raise RuntimeError(
                        "Found value-less or missing option for a option for tracked option with no default"
                    )

                keyword_args[tracked_option.name] = tracked_option.default

            elif option.type is hikari.OptionType.USER:
                user_id = hikari.Snowflake(option.value)
                member = option_data.members.get(user_id)
                if not member and tracked_option.is_only_member:
                    raise errors.ConversionError(
                        tracked_option.name, f"Couldn't find member for provided user: {user_id}"
                    )

                keyword_args[option.name] = member or option_data.users[user_id]

            elif option.type is hikari.OptionType.CHANNEL:
                keyword_args[option.name] = option_data.channels[hikari.Snowflake(option.value)]

            elif option.type is hikari.OptionType.ROLE:
                keyword_args[option.name] = option_data.roles[hikari.Snowflake(option.value)]

            elif option.type is hikari.OptionType.MENTIONABLE:
                id_ = hikari.Snowflake(option.value)
                if role := option_data.roles.get(id_):
                    keyword_args[option.name] = role

                else:
                    member = option_data.members.get(id_)
                    if not member and tracked_option.is_only_member:
                        raise errors.ConversionError(
                            tracked_option.name, f"Couldn't find member for provided user: {id_}"
                        )

                    keyword_args[option.name] = member or option_data.users[id_]

            elif tracked_option.converters:
                keyword_args[option.name] = await tracked_option.convert(ctx, option.value)

            else:
                keyword_args[option.name] = option.value

        return keyword_args

    async def check_context(self, ctx: traits.SlashContext, /) -> bool:
        return await utilities.gather_checks(ctx, self._checks)

    async def execute(
        self,
        ctx: traits.SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[traits.SlashHooks]] = None,
    ) -> None:
        own_hooks = self._hooks or _EMPTY_HOOKS
        try:
            await own_hooks.trigger_pre_execution(ctx, hooks=hooks)

            if option and option.options:
                kwargs = await self._process_args(ctx, option.options, ctx.interaction.resolved or _EMPTY_RESOLVED)

            elif ctx.interaction.options and not option:
                kwargs = await self._process_args(
                    ctx, ctx.interaction.options, ctx.interaction.resolved or _EMPTY_RESOLVED
                )

            else:
                kwargs = _EMPTY_DICT

            if self.needs_injector:
                injected_values = await injecting.resolve_getters(ctx, self._get_injection_getters())
                if kwargs:
                    kwargs.update(injected_values)

                else:
                    kwargs = injected_values

            await self._callback(ctx, **kwargs)

        except errors.CommandError as exc:
            await ctx.respond(exc.message)

        except errors.HaltExecutionSearch:
            await ctx.mark_not_found()
            return

        except Exception as exc:
            if await own_hooks.trigger_error(ctx, exc, hooks=hooks) <= 0:
                raise

        else:
            await own_hooks.trigger_success(ctx, hooks=hooks)

        finally:
            await own_hooks.trigger_post_execution(ctx, hooks=hooks)

    def set_tracked_command(self: _SlashCommandT, command: typing.Optional[hikari.Command], /) -> _SlashCommandT:
        self._tracked_command = command
        self._builder.set_id(command.id if command else hikari.UNDEFINED)
        return self

    def load_into_component(self: _SlashCommandT, component: traits.Component, /) -> typing.Optional[_SlashCommandT]:
        super().load_into_component(component)
        if not self._parent:
            component.add_slash_command(self)
            return self


def as_message_command(
    name: str, /, *names: str
) -> collections.Callable[[CommandCallbackSigT], MessageCommand[CommandCallbackSigT]]:
    def decorator(callback: CommandCallbackSigT, /) -> MessageCommand[CommandCallbackSigT]:
        return MessageCommand(callback, name, *names)

    return decorator


def as_message_command_group(
    name: str, /, *names: str, strict: bool = False
) -> collections.Callable[[CommandCallbackSigT], MessageCommandGroup[CommandCallbackSigT]]:
    def decorator(callback: CommandCallbackSigT, /) -> MessageCommandGroup[CommandCallbackSigT]:
        return MessageCommandGroup(callback, name, *names, strict=strict)

    return decorator


class MessageCommand(PartialCommand[CommandCallbackSigT, traits.MessageContext], traits.MessageCommand):
    __slots__ = ("_names", "_parent", "_parser")

    def __init__(
        self,
        callback: CommandCallbackSigT,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[collections.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.MessageHooks] = None,
        metadata: typing.Optional[collections.MutableMapping[typing.Any, typing.Any]] = None,
        parser: typing.Optional[parsing.AbstractParser] = None,
    ) -> None:
        super().__init__(callback, checks=checks, hooks=hooks, metadata=metadata)
        self._names = {name, *names}
        self._parent: typing.Optional[traits.MessageCommandGroup] = None
        self._parser = parser

    def __repr__(self) -> str:
        return f"Command <{self._names}>"

    @property
    def names(self) -> collections.Set[str]:
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

    async def check_context(self, ctx: traits.MessageContext, /) -> bool:
        ctx = ctx.set_command(self)
        result = await utilities.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    async def execute(
        self,
        ctx: traits.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[traits.MessageHooks]] = None,
    ) -> None:
        ctx = ctx.set_command(self)
        own_hooks = self._hooks or _EMPTY_HOOKS
        try:
            await own_hooks.trigger_pre_execution(ctx, hooks=hooks)

            if self._parser is not None:
                args, kwargs = await self._parser.parse(ctx)

            else:
                args = _EMPTY_LIST
                kwargs = _EMPTY_DICT

            if self.needs_injector:
                injected_values = await injecting.resolve_getters(ctx, self._get_injection_getters())
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

                except (hikari.RateLimitedError, hikari.RateLimitTooLongError) as retry_error:
                    if retry_error.retry_after > 4:
                        raise

                    retry.set_next_backoff(retry_error.retry_after)  # TODO: check if this is too large.

                except hikari.InternalServerError:
                    continue

                except (hikari.ForbiddenError, hikari.NotFoundError):
                    break

                else:
                    break

        except Exception as exc:
            if await own_hooks.trigger_error(ctx, exc, hooks=hooks) <= 0:
                raise

        else:
            # TODO: how should this be handled around CommandError?
            await own_hooks.trigger_success(ctx, hooks=hooks)

        finally:
            await own_hooks.trigger_post_execution(ctx, hooks=hooks)

    def load_into_component(
        self: _MessageCommandT, component: traits.Component, /, *, new: bool = True
    ) -> typing.Optional[_MessageCommandT]:
        super().load_into_component(component)
        if not self._parent:
            component.add_message_command(self)
            return self


class MessageCommandGroup(MessageCommand[CommandCallbackSigT], traits.MessageCommandGroup):
    __slots__ = ("_commands", "_is_strict", "_names_to_commands")

    def __init__(
        self,
        callback: CommandCallbackSigT,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[collections.Iterable[traits.CheckSig]] = None,
        hooks: typing.Optional[traits.MessageHooks] = None,
        metadata: typing.Optional[collections.MutableMapping[typing.Any, typing.Any]] = None,
        strict: bool = False,
        parser: typing.Optional[parsing.AbstractParser] = None,
    ) -> None:
        super().__init__(callback, name, *names, checks=checks, hooks=hooks, metadata=metadata, parser=parser)
        self._commands: set[traits.MessageCommand] = set()
        self._is_strict = strict
        self._names_to_commands: dict[str, traits.MessageCommand] = {}

    def __repr__(self) -> str:
        return f"CommandGroup <{len(self._commands)}: {self._names}>"

    @property
    def commands(self) -> collections.Set[traits.MessageCommand]:
        return self._commands.copy()

    @property
    def is_strict(self) -> bool:
        return self._is_strict

    def copy(
        self: _MessageCommandGroupT, *, _new: bool = True, parent: typing.Optional[traits.MessageCommandGroup] = None
    ) -> _MessageCommandGroupT:
        if not _new:
            commands = {command: command.copy(parent=self) for command in self._commands}
            self._commands = set(commands.values())
            self._names_to_commands = {name: commands[command] for name, command in self._names_to_commands.items()}

        return super().copy(parent=parent, _new=_new)

    def add_command(self: _MessageCommandGroupT, command: traits.MessageCommand, /) -> _MessageCommandGroupT:
        if self._is_strict:
            if any(" " in name for name in command.names):
                raise ValueError("Sub-command names may not contain spaces in a strict message command group")

            for name in command.names:
                if name in self._names_to_commands:
                    _LOGGER.info("Command name %r overwritten in message command group %r", name, self)

                self._names_to_commands[name] = command

        command.set_parent(self)
        self._commands.add(command)
        return self

    def remove_command(self, command: traits.MessageCommand, /) -> None:
        self._commands.remove(command)
        if self._is_strict:
            for name in command.names:
                if self._names_to_commands.get(name) == command:
                    del self._names_to_commands[name]

        command.set_parent(None)

    def with_command(self, command: AnyMessageCommandT, /) -> AnyMessageCommandT:
        self.add_command(command)
        return command

    def bind_client(self, client: traits.Client, /) -> None:
        super().bind_client(client)
        for command in self._commands:
            command.bind_client(client)

    def set_injector(self, client: injecting.InjectorClient, /) -> None:
        super().set_injector(client)

        if self._parser and isinstance(self._parser, injecting.Injectable):
            self._parser.set_injector(client)

        for command in self._commands:
            if isinstance(command, injecting.Injectable):
                command.set_injector(client)

    def find_command(self, content: str, /) -> collections.Iterable[tuple[str, traits.MessageCommand]]:
        if self._is_strict:
            name = content.split(" ")[0]
            if command := self._names_to_commands.get(name):
                yield name, command
                return

        for command in self._commands:
            if (name := utilities.match_prefix_names(content, command.names)) is not None:
                yield name, command

    # I sure hope this plays well with command group recursion cause I am waaaaaaaaaaaaaay too lazy to test that myself.
    async def execute(
        self,
        ctx: traits.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[traits.MessageHooks]] = None,
    ) -> None:
        if ctx.message.content is None:
            raise ValueError("Cannot execute a command with a contentless message")

        if self._hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._hooks)

        for name, command in self.find_command(ctx.content):
            if await command.check_context(ctx):
                content = ctx.message.content.lstrip()[len(ctx.triggering_prefix) :].lstrip()[
                    len(ctx.triggering_name) :
                ]
                space_len = len(content) - len(content.lstrip())
                ctx.set_triggering_name(ctx.triggering_name + (" " * space_len) + name)
                ctx.set_content(ctx.content[space_len + len(name) :].lstrip())
                await command.execute(ctx, hooks=hooks)
                return

        await super().execute(ctx, hooks=hooks)

    def load_into_component(
        self: _MessageCommandGroupT, component: traits.Component, /, *, new: bool = True
    ) -> typing.Optional[_MessageCommandGroupT]:
        super().load_into_component(component, new=new)
        for command in self._commands:
            if isinstance(command, components.LoadableProtocol):
                command.load_into_component(component)

        if not self._parent:
            return self
