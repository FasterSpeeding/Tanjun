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
    """Base class for the standard ExecutableCommand implementations."""

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
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        return self._callback

    @property
    def checks(self) -> collections.Set[traits.CheckSig]:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        return {check.callback for check in self._checks}

    @property
    def component(self) -> typing.Optional[traits.Component]:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        return self._component

    @property
    def hooks(self) -> typing.Optional[traits.Hooks[traits.ContextT]]:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        return self._hooks

    @property
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        return self._metadata

    @property
    def needs_injector(self) -> bool:
        # <<inherited docstring from tanjun.injecting.Injectable>>.
        if self._needs_injector is None:
            self._needs_injector = injecting.check_injecting(self._callback)

        return self._needs_injector

    if typing.TYPE_CHECKING:
        __call__: CommandCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback(*args, **kwargs)

    def copy(self: _PartialCommandT, *, _new: bool = True) -> _PartialCommandT:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
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
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        self._hooks = hooks
        return self

    def add_check(self: _PartialCommandT, check: traits.CheckSig, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        self._checks.add(injecting.InjectableCheck(check, injector=self._injector))
        return self

    def remove_check(self, check: traits.CheckSig, /) -> None:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        self._checks.remove(check)  # type: ignore[arg-type]

    def with_check(self, check: traits.CheckSigT, /) -> traits.CheckSigT:
        self._checks.add(_LoadableInjector(check, injector=self._injector))
        return check

    def set_injector(self, client: injecting.InjectorClient, /) -> None:
        # <<inherited docstring from tanjun.injecting.Injectable>>.
        if self._injector:
            raise RuntimeError("Injector already set")

        self._injector = client

        for check in self._checks:
            check.set_injector(client)

    def bind_client(self, client: traits.Client, /) -> None:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        pass

    def bind_component(self, component: traits.Component, /) -> None:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        self._component = component

    def _get_injection_getters(self) -> collections.Iterable[injecting.Getter[typing.Any]]:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
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
    name: str,
    description: str,
    /,
    *,
    default_to_ephemeral: bool = False,
    is_global: bool = True,
    sort_options: bool = True,
) -> collections.Callable[[CommandCallbackSigT], SlashCommand[CommandCallbackSigT]]:
    """build a `SlashCommand` by decorating a function.

    Examples
    --------
    ```py
    @as_slash_command("ping", "Get the bot's latency")
    async def ping_command(self, ctx: tanjun.traits.SlashContext) -> None:
        start_time = time.perf_counter()
        await ctx.rest.fetch_my_user()
        time_taken = (time.perf_counter() - start_time) * 1_000
        await ctx.respond(f"PONG\n - REST: {time_taken:.0f}mss")
    ```

    Parameters
    ----------
    name : str
        The command's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The command's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    default_to_ephemeral : bool
        Whether this command's responses should default to ephemeral unless flags
        are set to override this. This defaults to `False`.
    is_global : bool
        Whether this command is a global command. Defaults to `True`.
        !!! note
            Under the current implementation, this is used to determine whether
            the command should be bulk set by `tanjun.Client.set_global_commands`
            or when `set_global_commands` is True
    sort_options : bool
        Whether this command should sort its set options based on whether
        they're required.

        If this is `True` then the options are re-sorted to meet the requirement
        from Discord that required command options be listed before optional
        ones.

    Returns
    -------
    collections.abc.Callable[[CommandCallbackSigT], SlashCommand[CommandCallbackSigT]]
        The decorator callback used to build the command to a `SlashCommand`.
    """
    return lambda c: SlashCommand(
        c, name, description, default_to_ephemeral=default_to_ephemeral, is_global=is_global, sort_options=sort_options
    )


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
    """Add a string option to a slash command.

    Example
    -------
    ```py
    @with_str_slash_option("name", "A name.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, name: str) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    choices : typing.Optional[collections.Iterable[typing.Union[tuple[str, str], str]]]
        The option's choices.

        This may be either one or multiple `tuple[opton_name, option_value]`
        Where both option_name and option_value should be strings of up to 100
        characters.

        !!! note
            As a shorthand, this also supports passing strings in place of
            tuples each string will be used as both the choice's name and value
            (with the name being capitalised).
    converters : typing.Union[collections.Sequence[ConverterSig], ConverterSig, None]
        The option's converters.

        This may be either one or multiple `ConverterSig` callbacks used to
        convert the option's value to the final form.
        If this is `None`, the option will not be converted.

        !!! note
            Only the first converter to pass will be used.
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    new_choices: collections.Iterable[tuple[str, str]] = ()
    if choices is not None:
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
    """Add an integer option to a slash command.

    Example
    -------
    ```py
    @with_int_slash_option("int_value", "Int value.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, int_value: int) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    choices : typing.Optional[collections.Iterable[typing.Union[tuple[str, int]]]]
        The option's choices.

        This may be either one or multiple `tuple[opton_name, option_value]`
        where option_name should be a string of up to 100 characters and
        option_value should be an integer.
    converters : typing.Union[collections.Sequence[ConverterSig], ConverterSig, None]
        The option's converters.

        This may be either one or multiple `ConverterSig` callbacks used to
        convert the option's value to the final form.
        If this is `None`, the option will not be converted.

        !!! note
            Only the first converter to pass will be used.
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
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
    """Add a boolean option to a slash command.

    Example
    -------
    ```py
    @with_bool_slash_option("flag", "Whether this flag should be enabled.", default=False)
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, flag: bool) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_option(name, description, hikari.OptionType.BOOLEAN, default=default)


def with_user_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a user option to a slash command.

    !!! note
        This may result in `hikari.interactions.commands.InteractionMember` or
        `hikari.users.User` if the user isn't in the current guild or if this
        command was executed in a DM channel.

    Example
    -------
    ```py
    @with_channel_slash_option("user", "user to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, user: Union[InteractionMember, User]) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_option(name, description, hikari.OptionType.USER, default=default)


def with_member_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a member option to a slash command.

    !!! note
        This will always result in `hikari.interactions.commands.InteractionMember`.

    Example
    -------
    ```py
    @with_channel_slash_option("member", "member to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, member: hikari.InteractionMember) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_option(name, description, hikari.OptionType.USER, default=default, only_member=True)


def with_channel_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a channel option to a slash command.

    !!! note
        This will always result in `hikari.interactions.commands.InteractionChannel`.

    Example
    -------
    ```py
    @with_channel_slash_option("channel", "channel to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, channel: hikari.InteractionChannel) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Parameters
    ----------
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_option(name, description, hikari.OptionType.CHANNEL, default=default)


def with_role_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a role option to a slash command.

    Example
    -------
    ```py
    @with_role_slash_option("role", "Role to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, role: hikari.Role) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_option(name, description, hikari.OptionType.ROLE, default=default)


def with_mentionable_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = _UNDEFINED_DEFAULT,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a mentionable option to a slash command.

    !!! note
        This may taget roles, guild members or users and results in
        `Union[hikari.User, hikari.InteractionMember, hikari.Role]`.

    Example
    -------
    ```py
    @with_mentionable_slash_option("mentionable", "Mentionable entity to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.traits.SlashContext, mentionable: [Role, InteractionMember, User]) -> None:
        ...
    ```

    Parameters
    ----------
    name : str
        The option's name. This should match the regex `^[a-z0-9_-]{1,32}$`.
    description : str
        The option's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    default : typing.Any
        The option's default value.
        If this is left as undefined then this option will be required.

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
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


_CommandBuilderT = typing.TypeVar("_CommandBuilderT", bound="_CommandBuilder")


class _CommandBuilder(hikari.impl.CommandBuilder):
    __slots__ = ("_has_been_sorted", "_sort_options")

    def __init__(self, name: str, description: str, sort_options: bool) -> None:
        super().__init__(name, description)
        self._has_been_sorted = True
        self._sort_options = sort_options

    def add_option(self: _CommandBuilderT, option: hikari.CommandOption) -> _CommandBuilderT:
        if self._options:
            self._has_been_sorted = False

        return super().add_option(option)  # type: ignore

    def build(self, entity_factory: hikari.api.EntityFactory, /) -> dict[str, typing.Any]:
        if self._sort_options and not self._has_been_sorted:
            required: list[hikari.CommandOption] = []
            not_required: list[hikari.CommandOption] = []
            for option in self._options:
                if option.is_required:
                    required.append(option)
                else:
                    not_required.append(option)

            self._options = [*required, *not_required]
            self._has_been_sorted = True

        return super().build(entity_factory)


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
        sort_options: bool = True,
    ) -> None:
        super().__init__(callback, checks=checks, hooks=hooks, metadata=metadata)
        if not _SCOMMAND_NAME_REG.fullmatch(name):
            raise ValueError("Invalid command name provided, must match the regex `^[a-z0-9_-]{1,32}$`")

        self._builder = _CommandBuilder(name, description, sort_options)
        self._defaults_to_ephemeral = default_to_ephemeral
        self._description = description
        self._is_global = is_global
        self._name = name
        self._parent: typing.Optional[traits.SlashCommandGroup] = None
        self._tracked_command: typing.Optional[hikari.Command] = None
        self._tracked_options: dict[str, _TrackedOption] = {}

    @property
    def defaults_to_ephemeral(self) -> bool:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return self._defaults_to_ephemeral

    @property
    def description(self) -> str:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return self._description

    @property
    def is_global(self) -> bool:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return self._is_global

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return self._name

    @property
    def needs_injector(self) -> bool:
        # <<inherited docstring from tanjun.injecting.Injectable>>.
        return super().needs_injector or any(option.needs_injector for option in self._tracked_options.values())

    def set_injector(self, client: injecting.InjectorClient, /) -> None:
        # <<inherited docstring from tanjun.injecting.Injectable>>.
        super().set_injector(client)
        for option in self._tracked_options.values():
            option.set_injector(client)

    @property
    def parent(self) -> typing.Optional[traits.SlashCommandGroup]:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return self._parent

    @property
    def tracked_command(self) -> typing.Optional[hikari.Command]:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
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
        required = default is _UNDEFINED_DEFAULT
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

    def build(self) -> special_endpoints_api.CommandBuilder:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return self._builder

    def set_ephemeral_default(self: _SlashCommandT, state: bool, /) -> _SlashCommandT:
        """Set whether this command's responses should default to ephemeral.


        Parameters
        ----------
        bool
            Whether this command's responses should default to ephemeral.
            This will be overridden by any response calls which specify flags.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_parent(self: _SlashCommandT, parent: typing.Optional[traits.SlashCommandGroup], /) -> _SlashCommandT:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
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
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        return await utilities.gather_checks(ctx, self._checks)

    async def execute(
        self,
        ctx: traits.SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[traits.SlashHooks]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        own_hooks = self._hooks or _EMPTY_HOOKS
        try:
            await own_hooks.trigger_pre_execution(ctx, hooks=hooks)

            if self._tracked_options:
                options = option.options if option else None
                kwargs = await self._process_args(
                    ctx, options or ctx.interaction.options or _EMPTY_LIST, ctx.interaction.resolved or _EMPTY_RESOLVED
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

        except errors.HaltExecution:
            # Unlike a message command, this won't necessarily reach the client level try except
            # block so we have to handle this here.
            await ctx.mark_not_found()

        except Exception as exc:
            if await own_hooks.trigger_error(ctx, exc, hooks=hooks) <= 0:
                raise

        else:
            await own_hooks.trigger_success(ctx, hooks=hooks)

        finally:
            await own_hooks.trigger_post_execution(ctx, hooks=hooks)

    def set_tracked_command(self: _SlashCommandT, command: typing.Optional[hikari.Command], /) -> _SlashCommandT:
        # <<inherited docstring from tanjun.traits.SlashCommand>>.
        self._tracked_command = command
        self._builder.set_id(command.id if command else hikari.UNDEFINED)
        return self

    def load_into_component(self: _SlashCommandT, component: traits.Component, /) -> typing.Optional[_SlashCommandT]:
        # <<inherited docstring from PartialCommand>>.
        super().load_into_component(component)
        if not self._parent:
            component.add_slash_command(self)
            return self


def as_message_command(
    name: str, /, *names: str
) -> collections.Callable[[CommandCallbackSigT], MessageCommand[CommandCallbackSigT]]:
    """Build a message command from a decorated callback.

    Parameters
    ----------
    name : str
        The command name.

    Other Parameters
    ----------------
    names : str
        Variable positional arguments of other names for the command.

    Returns
    -------
    collections.abc.Callable[[CommandCallbackSigT], MessageCommand[CommandCallbackSigT]]
        Decorator callback used to build a MessageCommand` from the decorated callback.
    """
    return lambda callback: MessageCommand(callback, name, *names)


def as_message_command_group(
    name: str, /, *names: str, strict: bool = False
) -> collections.Callable[[CommandCallbackSigT], MessageCommandGroup[CommandCallbackSigT]]:
    """Build a message command group from a decorated callback.

    Parameters
    ----------
    name : str
        The command name.

    Other Parameters
    ----------------
    names : str
        Variable positional arguments of other names for the command.
    strict : bool
        Whether this command group should only allow commands without spaces in their names.

        This allows for a more optimised command search pattern to be used.

    Returns
    -------
    collections.abc.Callable[[CommandCallbackSigT], MessageCommandGroup[CommandCallbackSigT]]
        Decorator callback used to build a `MessageCommandGroup` from the decorated callback.
    """
    return lambda callback: MessageCommandGroup(callback, name, *names, strict=strict)


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
    # <<inherited docstring from tanjun.traits.MessageCommand>>.
    def names(self) -> collections.Set[str]:
        return self._names.copy()

    @property
    def parent(self) -> typing.Optional[traits.MessageCommandGroup]:
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
        return self._parent

    @property
    def parser(self) -> typing.Optional[parsing.AbstractParser]:
        return self._parser

    def bind_client(self, client: traits.Client, /) -> None:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        super().bind_client(client)
        if self._parser:
            self._parser.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        super().bind_component(component)
        if self._parser:
            self._parser.bind_component(component)

    def copy(
        self: _MessageCommandT, *, _new: bool = True, parent: typing.Optional[traits.MessageCommandGroup] = None
    ) -> _MessageCommandT:
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
        if not _new:
            self._names = self._names.copy()
            self._parent = parent
            self._parser = self._parser.copy() if self._parser else None

        return super().copy(_new=_new)

    def set_parent(self: _MessageCommandT, parent: typing.Optional[traits.MessageCommandGroup], /) -> _MessageCommandT:
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
        self._parent = parent
        return self

    def set_parser(self: _MessageCommandT, parser: typing.Optional[parsing.AbstractParser], /) -> _MessageCommandT:
        self._parser = parser
        return self

    async def check_context(self, ctx: traits.MessageContext, /) -> bool:
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
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
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
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

    def load_into_component(
        self: _MessageCommandT, component: traits.Component, /, *, new: bool = True
    ) -> typing.Optional[_MessageCommandT]:
        # <<inherited docstring from PartialCommand>>.
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
        # <<inherited docstring from tanjun.traits.MessageCommandGroup>>.
        return self._commands.copy()

    @property
    def is_strict(self) -> bool:
        return self._is_strict

    def copy(
        self: _MessageCommandGroupT, *, _new: bool = True, parent: typing.Optional[traits.MessageCommandGroup] = None
    ) -> _MessageCommandGroupT:
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
        if not _new:
            commands = {command: command.copy(parent=self) for command in self._commands}
            self._commands = set(commands.values())
            self._names_to_commands = {name: commands[command] for name, command in self._names_to_commands.items()}

        return super().copy(parent=parent, _new=_new)

    def add_command(self: _MessageCommandGroupT, command: traits.MessageCommand, /) -> _MessageCommandGroupT:
        # <<inherited docstring from tanjun.traits.MessageCommandGroup>>.
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
        # <<inherited docstring from tanjun.traits.MessageCommandGroup>>.
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
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        super().bind_client(client)
        for command in self._commands:
            command.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        # <<inherited docstring from tanjun.traits.ExecutableCommand>>.
        super().bind_component(component)
        for command in self._commands:
            command.bind_component(component)

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
        # <<inherited docstring from tanjun.traits.MessageCommand>>.
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
        # <<inherited docstring from PartialCommand>>.
        super().load_into_component(component, new=new)
        for command in self._commands:
            if isinstance(command, components.LoadableProtocol):
                command.load_into_component(component)

        if not self._parent:
            return self
