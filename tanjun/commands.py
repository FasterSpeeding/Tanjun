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
"""Standard implementation of Tanjun's command objects."""
from __future__ import annotations

__all__: list[str] = [
    "AnyMessageCommandT",
    "ConverterSig",
    "as_message_command",
    "as_message_command_group",
    "as_slash_command",
    "slash_command_group",
    "MessageCommand",
    "MessageCommandGroup",
    "PartialCommand",
    "BaseSlashCommand",
    "SlashCommand",
    "SlashCommandGroup",
    "with_str_slash_option",
    "with_int_slash_option",
    "with_float_slash_option",
    "with_bool_slash_option",
    "with_role_slash_option",
    "with_user_slash_option",
    "with_member_slash_option",
    "with_channel_slash_option",
    "with_mentionable_slash_option",
]

import copy
import re
import typing
import warnings
from collections import abc as collections

import hikari

from . import abc
from . import checks as checks_
from . import components
from . import conversion
from . import errors
from . import hooks as hooks_
from . import injecting
from . import utilities

if typing.TYPE_CHECKING:
    from hikari.api import special_endpoints as special_endpoints_api

    from . import parsing

    _MessageCommandT = typing.TypeVar("_MessageCommandT", bound="MessageCommand[typing.Any]")
    _MessageCommandGroupT = typing.TypeVar("_MessageCommandGroupT", bound="MessageCommandGroup[typing.Any]")
    _PartialCommandT = typing.TypeVar("_PartialCommandT", bound="PartialCommand[typing.Any]")
    _BaseSlashCommandT = typing.TypeVar("_BaseSlashCommandT", bound="BaseSlashCommand")
    _SlashCommandT = typing.TypeVar("_SlashCommandT", bound="SlashCommand[typing.Any]")
    _SlashCommandGroupT = typing.TypeVar("_SlashCommandGroupT", bound="SlashCommandGroup")


_CallbackishT = typing.Union[
    abc.CommandCallbackSigT,
    abc.MessageCommand[abc.CommandCallbackSigT],
    abc.SlashCommand[abc.CommandCallbackSigT],
]

AnyMessageCommandT = typing.TypeVar("AnyMessageCommandT", bound=abc.MessageCommand[typing.Any])
ConverterSig = collections.Callable[..., abc.MaybeAwaitableT[typing.Any]]
"""Type hint of a converter used for a slash command option."""
_EMPTY_DICT: typing.Final[dict[typing.Any, typing.Any]] = {}
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()


class PartialCommand(abc.ExecutableCommand[abc.ContextT], components.AbstractComponentLoader):
    """Base class for the standard ExecutableCommand implementations."""

    __slots__ = ("_checks", "_component", "_hooks", "_metadata")

    def __init__(self) -> None:
        self._checks: list[checks_.InjectableCheck] = []
        self._component: typing.Optional[abc.Component] = None
        self._hooks: typing.Optional[abc.Hooks[abc.ContextT]] = None
        self._metadata: dict[typing.Any, typing.Any] = {}

    @property
    def checks(self) -> collections.Collection[abc.CheckSig]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return tuple(check.callback for check in self._checks)

    @property
    def component(self) -> typing.Optional[abc.Component]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._component

    @property
    def hooks(self) -> typing.Optional[abc.Hooks[abc.ContextT]]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._hooks

    @property
    def metadata(self) -> collections.MutableMapping[typing.Any, typing.Any]:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self._metadata

    @property
    def needs_injector(self) -> bool:
        # <<inherited docstring from tanjun.injecting.Injectable>>.
        return any(check.needs_injector for check in self._checks)

    def copy(self: _PartialCommandT, *, _new: bool = True) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if not _new:
            self._checks = [check.copy() for check in self._checks]
            self._hooks = self._hooks.copy() if self._hooks else None
            self._metadata = self._metadata.copy()
            return self

        return copy.copy(self).copy(_new=False)

    def set_hooks(self: _PartialCommandT, hooks: typing.Optional[abc.Hooks[abc.ContextT]], /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._hooks = hooks
        return self

    def add_check(self: _PartialCommandT, check: abc.CheckSig, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if check not in self._checks:
            self._checks.append(checks_.InjectableCheck(check))

        return self

    def remove_check(self: _PartialCommandT, check: abc.CheckSig, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._checks.remove(typing.cast("checks_.InjectableCheck", check))
        return self

    def with_check(self, check: abc.CheckSigT, /) -> abc.CheckSigT:
        self.add_check(check)
        return check

    def bind_client(self: _PartialCommandT, client: abc.Client, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        return self

    def bind_component(self: _PartialCommandT, component: abc.Component, /) -> _PartialCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        self._component = component
        return self


_SCOMMAND_NAME_REG: typing.Final[re.Pattern[str]] = re.compile(r"^[\w-]{1,32}$", flags=re.UNICODE)


def _validate_name(name: str) -> None:
    if not _SCOMMAND_NAME_REG.fullmatch(name):
        raise ValueError(f"Invalid name provided, {name!r} doesn't match the required regex `^\\w{{1,32}}$`")

    if name.lower() != name:
        raise ValueError(f"Invalid name provided, {name!r} must be lowercase")


def slash_command_group(
    name: str,
    description: str,
    /,
    *,
    default_permission: bool = True,
    default_to_ephemeral: typing.Optional[bool] = None,
    is_global: bool = True,
) -> SlashCommandGroup:
    r"""Create a slash command group.

    Examples
    --------
    Sub-commands can be added to the created slash command object through
    the following decorator based approach:
    ```python
    help_group = tanjun.slash_command_group("help", "get help")

    @help_group.with_command
    @tanjun.with_str_slash_option("command_name", "command name")
    @tanjun.as_slash_command("command", "Get help with a command")
    async def help_command_command(ctx: tanjun.abc.SlashContext, command_name: str) -> None:
        ...

    @help_group.with_command
    @tanjun.as_slash_command("me", "help me")
    async def help_me_command(ctx: tanjun.abc.SlashContext) -> None:
        ...

    component = tanjun.Component().add_slash_command(help_group)
    ```

    Notes
    -----
    * Unlike message command grups, slash command groups cannot
      be callable functions themselves.
    * Under the standard implementation, `is_global` is used to determine whether
      the command should be bulk set by `tanjun.Client.set_global_commands`
      or when `set_global_commands` is True

    Parameters
    ----------
    name : str
        The name of the command group.

        This must match the regex `^[\w-]{1,32}$` in Unicode mode and be lowercase.
    description : str
        The description of the command group.

    Other Parameters
    ----------------
    default_permission : bool
        Whether this command can be accessed without set permissions.

        Defaults to `True`, meaning that users can access the command by default.
    default_to_ephemeral : typing.Optional[bool]
        Whether this command's responses should default to ephemeral unless flags
        are set to override this.

        If this is left as `None` then the default set on the parent command(s),
        component or client will be in effect.
    is_global : bool
        Whether this command is a global command. Defaults to `True`.

    Returns
    -------
    SlashCommandGroup
        The command group.

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:
        * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
        * If the command name has uppercase characters.
        * If the description is over 100 characters long.
    """
    return SlashCommandGroup(
        name,
        description,
        default_permission=default_permission,
        default_to_ephemeral=default_to_ephemeral,
        is_global=is_global,
    )


def as_slash_command(
    name: str,
    description: str,
    /,
    *,
    always_defer: bool = False,
    default_permission: bool = True,
    default_to_ephemeral: typing.Optional[bool] = None,
    is_global: bool = True,
    sort_options: bool = True,
) -> collections.Callable[[_CallbackishT[abc.CommandCallbackSigT],], SlashCommand[abc.CommandCallbackSigT]]:
    r"""Build a `SlashCommand` by decorating a function.

    .. note::
        Under the standard implementation, `is_global` is used to determine whether
        the command should be bulk set by `tanjun.Client.set_global_commands`
        or when `set_global_commands` is True

    .. warning::
        `default_permission` and `is_global` are ignored for commands within
        slash command groups.

    Examples
    --------
    ```py
    @as_slash_command("ping", "Get the bot's latency")
    async def ping_command(self, ctx: tanjun.abc.SlashContext) -> None:
        start_time = time.perf_counter()
        await ctx.rest.fetch_my_user()
        time_taken = (time.perf_counter() - start_time) * 1_000
        await ctx.respond(f"PONG\n - REST: {time_taken:.0f}mss")
    ```

    Parameters
    ----------
    name : str
        The command's name.

        This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
    description : str
        The command's description.
        This should be inclusively between 1-100 characters in length.

    Other Parameters
    ----------------
    always_defer : bool
        Whether the contexts this command is executed with should always be deferred
        before being passed to the command's callback.

        Defaults to `False`.

        .. note::
            The ephemeral state of the first response is decided by whether the
            deferral is ephemeral.
    default_permission : bool
        Whether this command can be accessed without set permissions.

        Defaults to `True`, meaning that users can access the command by default.
    default_to_ephemeral : typing.Optional[bool]
        Whether this command's responses should default to ephemeral unless flags
        are set to override this.

        If this is left as `None` then the default set on the parent command(s),
        component or client will be in effect.
    is_global : bool
        Whether this command is a global command. Defaults to `True`.
    sort_options : bool
        Whether this command should sort its set options based on whether
        they're required.

        If this is `True` then the options are re-sorted to meet the requirement
        from Discord that required command options be listed before optional
        ones.

    Returns
    -------
    collections.abc.Callable[[_CallbackishT[CommandCallbackSigT]], SlashCommand[CommandCallbackSigT]]
        The decorator callback used to make a `SlashCommand`.

        This can either wrap a raw command callback or another callable command instance
        (e.g. `SlashCommand`, `MessageCommand`, `MessageCommandGroup`) and will manage
        loading the other command into a component when using `tanjun.Component.load_from_scope`.

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:
        * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
        * If the command name has uppercase characters.
        * If the description is over 100 characters long.
    """

    def decorator(callback: _CallbackishT[abc.CommandCallbackSigT], /) -> SlashCommand[abc.CommandCallbackSigT]:
        if isinstance(callback, (abc.SlashCommand, abc.MessageCommand)):
            return SlashCommand(
                callback.callback,
                name,
                description,
                always_defer=always_defer,
                default_permission=default_permission,
                default_to_ephemeral=default_to_ephemeral,
                is_global=is_global,
                sort_options=sort_options,
                _wrapped_command=callback,
            )

        return SlashCommand(
            callback,
            name,
            description,
            always_defer=always_defer,
            default_permission=default_permission,
            default_to_ephemeral=default_to_ephemeral,
            is_global=is_global,
            sort_options=sort_options,
        )

    return decorator


_UNDEFINED_DEFAULT = object()


def with_str_slash_option(
    name: str,
    description: str,
    /,
    *,
    choices: typing.Union[collections.Mapping[str, str], collections.Sequence[str], None] = None,
    converters: typing.Union[collections.Sequence[ConverterSig], ConverterSig] = (),
    default: typing.Any = _UNDEFINED_DEFAULT,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a string option to a slash command.

    For more information on this function's parameters see `SlashCommand.add_str_option`.

    Examples
    --------
    ```py
    @with_str_slash_option("name", "A name.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, name: str) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_str_option(
        name,
        description,
        default=default,
        choices=choices,
        converters=converters,
        pass_as_kwarg=pass_as_kwarg,
        _stack_level=1,
    )


def with_int_slash_option(
    name: str,
    description: str,
    /,
    *,
    choices: typing.Optional[collections.Mapping[str, int]] = None,
    converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
    default: typing.Any = _UNDEFINED_DEFAULT,
    min_value: typing.Optional[int] = None,
    max_value: typing.Optional[int] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add an integer option to a slash command.

    For information on this function's parameters see `SlashCommand.add_int_option`.

    Examples
    --------
    ```py
    @with_int_slash_option("int_value", "Int value.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, int_value: int) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_int_option(
        name,
        description,
        default=default,
        choices=choices,
        converters=converters,
        min_value=min_value,
        max_value=max_value,
        pass_as_kwarg=pass_as_kwarg,
        _stack_level=1,
    )


def with_float_slash_option(
    name: str,
    description: str,
    /,
    *,
    always_float: bool = True,
    choices: typing.Optional[collections.Mapping[str, float]] = None,
    converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
    default: typing.Any = _UNDEFINED_DEFAULT,
    min_value: typing.Optional[float] = None,
    max_value: typing.Optional[float] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a float option to a slash command.

    For information on this function's parameters see `SlashCommand.add_float_option`.

    Examples
    --------
    ```py
    @with_float_slash_option("float_value", "Float value.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, float_value: float) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_float_option(
        name,
        description,
        always_float=always_float,
        default=default,
        choices=choices,
        converters=converters,
        min_value=min_value,
        max_value=max_value,
        pass_as_kwarg=pass_as_kwarg,
        _stack_level=1,
    )


def with_bool_slash_option(
    name: str, description: str, /, *, default: typing.Any = _UNDEFINED_DEFAULT, pass_as_kwarg: bool = True
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a boolean option to a slash command.

    For information on this function's parameters see `SlashContext.add_bool_option`.

    Examples
    --------
    ```py
    @with_bool_slash_option("flag", "Whether this flag should be enabled.", default=False)
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, flag: bool) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_bool_option(name, description, default=default, pass_as_kwarg=pass_as_kwarg)


def with_user_slash_option(
    name: str, description: str, /, *, default: typing.Any = _UNDEFINED_DEFAULT, pass_as_kwarg: bool = True
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a user option to a slash command.

    For information on this function's parameters see `SlashContext.add_user_option`.

    .. note::
        This may result in `hikari.InteractionMember` or
        `hikari.users.User` if the user isn't in the current guild or if this
        command was executed in a DM channel.

    Examples
    --------
    ```py
    @with_user_slash_option("user", "user to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, user: Union[InteractionMember, User]) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_user_option(name, description, default=default, pass_as_kwarg=pass_as_kwarg)


def with_member_slash_option(
    name: str, description: str, /, *, default: typing.Any = _UNDEFINED_DEFAULT
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a member option to a slash command.

    For information on this function's arguments see `SlashCommand.add_member_option`.

    .. note::
        This will always result in `hikari.InteractionMember`.

    Examples
    --------
    ```py
    @with_member_slash_option("member", "member to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, member: hikari.InteractionMember) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_member_option(name, description, default=default)


_channel_types: dict[type[hikari.PartialChannel], set[hikari.ChannelType]] = {
    hikari.GuildTextChannel: {hikari.ChannelType.GUILD_TEXT},
    hikari.DMChannel: {hikari.ChannelType.DM},
    hikari.GuildVoiceChannel: {hikari.ChannelType.GUILD_VOICE},
    hikari.GroupDMChannel: {hikari.ChannelType.GROUP_DM},
    hikari.GuildCategory: {hikari.ChannelType.GUILD_CATEGORY},
    hikari.GuildNewsChannel: {hikari.ChannelType.GUILD_NEWS},
    hikari.GuildStoreChannel: {hikari.ChannelType.GUILD_STORE},
    hikari.GuildStageChannel: {hikari.ChannelType.GUILD_STAGE},
}


for _channel_cls, _types in _channel_types.copy().items():
    for _mro_type in _channel_cls.mro():
        if isinstance(_mro_type, type) and issubclass(_mro_type, hikari.PartialChannel):
            try:
                _channel_types[_mro_type].update(_types)
            except KeyError:
                _channel_types[_mro_type] = _types.copy()


def with_channel_slash_option(
    name: str,
    description: str,
    /,
    *,
    types: collections.Collection[type[hikari.PartialChannel]] | None = None,
    default: typing.Any = _UNDEFINED_DEFAULT,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a channel option to a slash command.

    For information on this function's parameters see `SlashCommand.add_channel_option`.

    .. note::
        This will always result in `hikari..InteractionChannel`.

    Examples
    --------
    ```py
    @with_channel_slash_option("channel", "channel to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, channel: hikari.InteractionChannel) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_channel_option(name, description, types=types, default=default, pass_as_kwarg=pass_as_kwarg)


def with_role_slash_option(
    name: str, description: str, /, *, default: typing.Any = _UNDEFINED_DEFAULT, pass_as_kwarg: bool = True
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a role option to a slash command.

    For information on this function's parameters see `SlashCommand.add_role_option`.

    Examples
    --------
    ```py
    @with_role_slash_option("role", "Role to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, role: hikari.Role) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_role_option(name, description, default=default, pass_as_kwarg=pass_as_kwarg)


def with_mentionable_slash_option(
    name: str, description: str, /, *, default: typing.Any = _UNDEFINED_DEFAULT, pass_as_kwarg: bool = True
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a mentionable option to a slash command.

    For information on this function's arguments see `SlashCommand.add_mentionable_option`.

    .. note::
        This may target roles, guild members or users and results in
        `Union[hikari.User, hikari.InteractionMember, hikari.Role]`.

    Examples
    --------
    ```py
    @with_mentionable_slash_option("mentionable", "Mentionable entity to target.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, mentionable: [Role, InteractionMember, User]) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_mentionable_option(name, description, default=default, pass_as_kwarg=pass_as_kwarg)


def _convert_to_injectable(converter: ConverterSig) -> injecting.CallbackDescriptor[typing.Any]:
    if isinstance(converter, injecting.CallbackDescriptor):
        return typing.cast("injecting.CallbackDescriptor[typing.Any]", converter)

    return injecting.CallbackDescriptor(conversion.override_type(converter))


class _TrackedOption:
    __slots__ = ("converters", "default", "is_always_float", "is_only_member", "name", "type")

    def __init__(
        self,
        *,
        name: str,
        option_type: typing.Union[hikari.OptionType, int],
        always_float: bool = False,
        converters: typing.Optional[list[injecting.CallbackDescriptor[typing.Any]]] = None,
        only_member: bool = False,
        default: typing.Any = _UNDEFINED_DEFAULT,
    ) -> None:
        self.converters = converters or []
        self.default = default
        self.is_always_float = always_float
        self.is_only_member = only_member
        self.name = name
        self.type = option_type

    @property
    def needs_injector(self) -> bool:
        return any(converter.needs_injector for converter in self.converters)

    def check_client(self, client: abc.Client, /) -> None:
        for converter in self.converters:
            if isinstance(converter.callback, conversion.BaseConverter):
                converter.callback.check_client(client, f"{self.name} slash command option")

    async def convert(self, ctx: abc.SlashContext, value: typing.Any, /) -> typing.Any:
        if not self.converters:
            return value

        exceptions: list[ValueError] = []
        for converter in self.converters:
            try:
                return await converter.resolve_with_command_context(ctx, value)

            except ValueError as exc:
                exceptions.append(exc)

        raise errors.ConversionError(f"Couldn't convert {self.type} '{self.name}'", self.name, errors=exceptions)


_CommandBuilderT = typing.TypeVar("_CommandBuilderT", bound="_CommandBuilder")


class _CommandBuilder(hikari.impl.CommandBuilder):
    __slots__ = ("_has_been_sorted", "_sort_options")

    def __init__(
        self,
        name: str,
        description: str,
        sort_options: bool,
        *,
        id: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,  # noqa: A002
    ) -> None:
        super().__init__(name, description, id=id)  # type: ignore
        self._has_been_sorted = True
        self._sort_options = sort_options

    def add_option(self: _CommandBuilderT, option: hikari.CommandOption) -> _CommandBuilderT:
        if self._options:
            self._has_been_sorted = False

        super().add_option(option)
        return self

    def sort(self: _CommandBuilderT) -> _CommandBuilderT:
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

        return self

    def copy(self) -> _CommandBuilder:  # TODO: can we just del _CommandBuilder.__copy__ to go back to the default?
        builder = _CommandBuilder(self.name, self.description, self._sort_options, id=self.id)

        for option in self._options:
            builder.add_option(option)

        return builder


class BaseSlashCommand(PartialCommand[abc.SlashContext], abc.BaseSlashCommand):
    """Base class used for the standard slash command implementations."""

    __slots__ = ("_defaults_to_ephemeral", "_description", "_is_global", "_name", "_parent", "_tracked_command")

    def __init__(
        self,
        name: str,
        description: str,
        /,
        *,
        default_to_ephemeral: typing.Optional[bool] = None,
        is_global: bool = True,
    ) -> None:
        super().__init__()
        _validate_name(name)
        if len(description) > 100:
            raise ValueError("The command description cannot be over 100 characters in length")

        self._defaults_to_ephemeral = default_to_ephemeral
        self._description = description
        self._is_global = is_global
        self._name = name
        self._parent: typing.Optional[abc.SlashCommandGroup] = None
        self._tracked_command: typing.Optional[hikari.Command] = None

    @property
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._defaults_to_ephemeral

    @property
    def description(self) -> str:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._description

    @property
    def is_global(self) -> bool:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._is_global

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._name

    @property
    def parent(self) -> typing.Optional[abc.SlashCommandGroup]:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._parent

    @property
    def tracked_command(self) -> typing.Optional[hikari.Command]:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._tracked_command

    @property
    def tracked_command_id(self) -> typing.Optional[hikari.Snowflake]:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._tracked_command.id if self._tracked_command else None

    def set_tracked_command(self: _BaseSlashCommandT, command: hikari.Command, /) -> _BaseSlashCommandT:
        """Set the the global command this should be tracking.

        Parameters
        ----------
        command : hikari.Command
            object of the global command this should be tracking.

        Returns
        -------
        SelfT
            This command instance for chaining.
        """
        self._tracked_command = command
        return self

    def set_ephemeral_default(self: _BaseSlashCommandT, state: typing.Optional[bool], /) -> _BaseSlashCommandT:
        """Set whether this command's responses should default to ephemeral.

        Parameters
        ----------
        typing.Optional[bool]
            Whether this command's responses should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to `None` will let the default set on the parent
            command(s), component or client propagate and decide the ephemeral
            default for contexts used by this command.

        Returns
        -------
        SelfT
            This command to allow for chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_parent(self: _BaseSlashCommandT, parent: typing.Optional[abc.SlashCommandGroup], /) -> _BaseSlashCommandT:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        self._parent = parent
        return self

    async def check_context(self, ctx: abc.SlashContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        ctx.set_command(self)
        result = await utilities.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    def copy(
        self: _BaseSlashCommandT, *, _new: bool = True, parent: typing.Optional[abc.SlashCommandGroup] = None
    ) -> _BaseSlashCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if not _new:
            self._parent = parent
            return super().copy(_new=_new)

        return super().copy(_new=_new)

    def load_into_component(self, component: abc.Component, /) -> None:
        # <<inherited docstring from tanjun.components.load_into_component>>.
        if not self._parent:
            component.add_slash_command(self)


class SlashCommandGroup(BaseSlashCommand, abc.SlashCommandGroup):
    """Standard implementation of a slash command group.

    .. note::
        Unlike message command grups, slash command groups cannot
        be callable functions themselves.
    """

    __slots__ = ("_commands", "_default_permission")

    def __init__(
        self,
        name: str,
        description: str,
        /,
        *,
        default_to_ephemeral: typing.Optional[bool] = None,
        default_permission: bool = True,
        is_global: bool = True,
    ) -> None:
        r"""Initialise a slash command group.

        .. note::
            Under the standard implementation, `is_global` is used to determine
            whether the command should be bulk set by `tanjun.Client.set_global_commands`
            or when `set_global_commands` is True

        Parameters
        ----------
        name : str
            The name of the command group.

            This must match the regex `^[\w-]{1,32}$` in Unicode mode and be lowercase.
        description : str
            The description of the command group.

        Other Parameters
        ----------------
        default_permission : bool
            Whether this command can be accessed without set permissions.

            Defaults to `True`, meaning that users can access the command by default.
        default_to_ephemeral : typing.Optional[bool]
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as `None` then the default set on the parent command(s),
            component or client will be in effect.
        is_global : bool
            Whether this command is a global command. Defaults to `True`.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the command name has uppercase characters.
            * If the description is over 100 characters long.
        """
        super().__init__(name, description, default_to_ephemeral=default_to_ephemeral, is_global=is_global)
        self._commands: dict[str, abc.BaseSlashCommand] = {}
        self._default_permission = default_permission

    @property
    def commands(self) -> collections.Collection[abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.SlashCommandGroup>>.
        return self._commands.copy().values()

    def build(self) -> special_endpoints_api.CommandBuilder:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        builder = _CommandBuilder(self._name, self._description, False).set_default_permission(self._default_permission)
        for command in self._commands.values():
            option_type = (
                hikari.OptionType.SUB_COMMAND_GROUP
                if isinstance(command, abc.SlashCommandGroup)
                else hikari.OptionType.SUB_COMMAND
            )
            command_builder = command.build()
            builder.add_option(
                hikari.CommandOption(
                    type=option_type,
                    name=command.name,
                    description=command_builder.description,
                    is_required=False,
                    options=command_builder.options,
                )
            )

        return builder

    def copy(
        self: _SlashCommandGroupT, *, _new: bool = True, parent: typing.Optional[abc.SlashCommandGroup] = None
    ) -> _SlashCommandGroupT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if not _new:
            self._commands = {name: command.copy() for name, command in self._commands.items()}
            return super().copy(_new=_new, parent=parent)

        return super().copy(_new=_new, parent=parent)

    def add_command(self: _SlashCommandGroupT, command: abc.BaseSlashCommand, /) -> _SlashCommandGroupT:
        """Add a slash command to this group.

        .. warning::
            Command groups are only supported within top-level groups.

        Parameters
        ----------
        command : tanjun.abc.BaseSlashCommand
            Command to add to this group.

        Returns
        -------
        Self
            Object of this group to enable chained calls.
        """
        if self._parent and isinstance(command, abc.SlashCommandGroup):
            raise ValueError("Cannot add a slash command group to a nested slash command group")

        if len(self._commands) == 25:
            raise ValueError("Cannot add more than 25 commands to a slash command group")

        if command.name in self._commands:
            raise ValueError(f"Command with name {command.name!r} already exists in this group")

        command.set_parent(self)
        self._commands[command.name] = command
        return self

    def remove_command(self: _SlashCommandGroupT, command: abc.BaseSlashCommand, /) -> _SlashCommandGroupT:
        """Remove a command from this group.

        Parameters
        ----------
        command : tanjun.abc.BaseSlashCommand
            Command to remove from this group.

        Returns
        -------
        Self
            Object of this group to enable chained calls.
        """
        del self._commands[command.name]
        return self

    def with_command(self, command: abc.BaseSlashCommandT, /) -> abc.BaseSlashCommandT:
        """Add a slash command to this group through a decorator call.

        Parameters
        ----------
        command : tanjun.abc.BaseSlashCommand
            Command to add to this group.

        Returns
        -------
        tanjun.abc.BaseSlashCommand
            Command which was added to this group.
        """
        self.add_command(command)
        return command

    async def execute(
        self,
        ctx: abc.SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.SlashHooks]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        if not option and ctx.interaction.options:
            option = ctx.interaction.options[0]

        elif option and option.options:
            option = option.options[0]

        else:
            raise RuntimeError("Missing sub-command option")

        if command := self._commands.get(option.name):
            if command.defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(command.defaults_to_ephemeral)

            if await command.check_context(ctx):
                await command.execute(ctx, option=option, hooks=hooks)
                return

        await ctx.mark_not_found()


class SlashCommand(BaseSlashCommand, abc.SlashCommand[abc.CommandCallbackSigT]):
    """Standard implementation of a slash command."""

    __slots__ = ("_always_defer", "_builder", "_callback", "_client", "_tracked_options", "_wrapped_command")

    def __init__(
        self,
        callback: abc.CommandCallbackSigT,
        name: str,
        description: str,
        /,
        *,
        always_defer: bool = False,
        default_permission: bool = True,
        default_to_ephemeral: typing.Optional[bool] = None,
        is_global: bool = True,
        sort_options: bool = True,
        _wrapped_command: typing.Optional[abc.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        r"""Initialise a slash command.

        .. note::
            Under the standard implementation, `is_global` is used to determine whether
            the command should be bulk set by `tanjun.Client.set_global_commands`
            or when `set_global_commands` is True

        .. warning::
            `default_permission` and `is_global` are ignored for commands within
            slash command groups.

        Parameters
        ----------
        callback : collections.abc.Callable[[tanjun.abc.SlashContext, ...], collections.abc.Awaitable[None]]
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type `tanjun.abc.SlashContext`, returns `None` and may use
            dependency injection to access other services.
        name : str
            The command's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The command's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        always_defer : bool
            Whether the contexts this command is executed with should always be deferred
            before being passed to the command's callback.

            Defaults to `False`.

            .. note::
                The ephemeral state of the first response is decided by whether the
                deferral is ephemeral.
        default_permission : bool
            Whether this command can be accessed without set permissions.

            Defaults to `True`, meaning that users can access the command by default.
        default_to_ephemeral : typing.Optional[bool]
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as `None` then the default set on the parent command(s),
            component or client will be in effect.
        is_global : bool
            Whether this command is a global command. Defaults to `True`.
        sort_options : bool
            Whether this command should sort its set options based on whether
            they're required.

            If this is `True` then the options are re-sorted to meet the requirement
            from Discord that required command options be listed before optional
            ones.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the command name has uppercase characters.
            * If the description is over 100 characters long.
        """
        super().__init__(name, description, default_to_ephemeral=default_to_ephemeral, is_global=is_global)

        self._always_defer = always_defer
        self._builder = _CommandBuilder(name, description, sort_options).set_default_permission(default_permission)
        self._callback = injecting.CallbackDescriptor[None](callback)
        self._client: typing.Optional[abc.Client] = None
        self._tracked_options: dict[str, _TrackedOption] = {}
        self._wrapped_command = _wrapped_command

    if typing.TYPE_CHECKING:
        __call__: abc.CommandCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback.callback(*args, **kwargs)

    @property
    def callback(self) -> abc.CommandCallbackSigT:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return typing.cast(abc.CommandCallbackSigT, self._callback.callback)

    @property
    def needs_injector(self) -> bool:
        return (
            self._callback.needs_injector
            or any(option.needs_injector for option in self._tracked_options.values())
            or super().needs_injector
        )

    def bind_client(self: _SlashCommandT, client: abc.Client, /) -> _SlashCommandT:
        self._client = client
        super().bind_client(client)
        for option in self._tracked_options.values():
            option.check_client(client)

        return self

    def build(self) -> special_endpoints_api.CommandBuilder:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._builder.sort().copy()

    def load_into_component(self, component: abc.Component, /) -> None:
        super().load_into_component(component)
        if self._wrapped_command and isinstance(self._wrapped_command, components.AbstractComponentLoader):
            self._wrapped_command.load_into_component(component)

    def _add_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        type_: typing.Union[hikari.OptionType, int] = hikari.OptionType.STRING,
        /,
        *,
        always_float: bool = False,
        channel_types: typing.Optional[collections.Sequence[int]] = None,
        choices: typing.Union[
            collections.Mapping[str, typing.Union[str, int, float]], collections.Sequence[typing.Any], None
        ] = None,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        default: typing.Any = _UNDEFINED_DEFAULT,
        min_value: typing.Union[int, float, None] = None,
        max_value: typing.Union[int, float, None] = None,
        only_member: bool = False,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        _validate_name(name)
        if len(description) > 100:
            raise ValueError("The option description cannot be over 100 characters in length")

        if len(self._builder.options) == 25:
            raise ValueError("Slash commands cannot have more than 25 options")

        if min_value and max_value and min_value > max_value:
            raise ValueError("The min value cannot be greater than the max value")

        type_ = hikari.OptionType(type_)
        if isinstance(converters, collections.Iterable):
            converters_ = list(map(_convert_to_injectable, converters))

        else:
            converters_ = [_convert_to_injectable(converters)]

        if self._client:
            for converter in converters_:
                if isinstance(converter.callback, conversion.BaseConverter):
                    converter.callback.check_client(self._client, f"{self._name}'s slash option '{name}'")

        if choices is None:
            actual_choices: typing.Optional[list[hikari.CommandChoice]] = None

        elif isinstance(choices, collections.Mapping):
            actual_choices = [hikari.CommandChoice(name=name, value=value) for name, value in choices.items()]

        else:
            warnings.warn(
                "Passing a sequence of tuples to `choices` is deprecated since 2.1.2a1, "
                "please pass a mapping instead.",
                category=DeprecationWarning,
                stacklevel=2 + _stack_level,
            )
            actual_choices = [hikari.CommandChoice(name=name, value=value) for name, value in choices]

        if actual_choices and len(actual_choices) > 25:
            raise ValueError("Slash command options cannot have more than 25 choices")

        required = default is _UNDEFINED_DEFAULT
        self._builder.add_option(
            hikari.CommandOption(
                type=type_,
                name=name,
                description=description,
                is_required=required,
                choices=actual_choices,
                channel_types=channel_types,
                min_value=min_value,
                max_value=max_value,
            )
        )
        if pass_as_kwarg:
            self._tracked_options[name] = _TrackedOption(
                name=name,
                option_type=type_,
                always_float=always_float,
                converters=converters_,
                default=default,
                only_member=only_member,
            )
        return self

    def add_str_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        choices: typing.Union[collections.Mapping[str, str], collections.Sequence[str], None] = None,
        converters: typing.Union[collections.Sequence[ConverterSig], ConverterSig] = (),
        default: typing.Any = _UNDEFINED_DEFAULT,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        r"""Add a string option to the slash command.

        .. note::
            As a shorthand, `choices` also supports passing a list of strings
            rather than a dict of names to values (each string will used as
            both the choice's name and value with the names being capitalised).

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        choices : typing.Union[collections.abc.Mapping[str, str], collections.abc.Sequence[str], None]
            The option's choices.

            This either a mapping of [option_name, option_value] where both option_name
            and option_value should be strings of up to 100 characters or a sequence
            of strings where the string will be used for both the choice's name and
            value.
        converters : typing.Union[collections.abc.Sequence[ConverterSig], ConverterSig]
            The option's converters.

            This may be either one or multiple `ConverterSig` callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used and the `coverters` field will be ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
        """
        if choices is None:
            actual_choices = None

        elif isinstance(choices, collections.Mapping):
            actual_choices = choices

        else:
            actual_choices = {}
            warned = False
            for choice in choices:
                if isinstance(choice, tuple):  # type: ignore[unreachable]  # the point of this is for deprecation
                    if not warned:  # type: ignore[unreachable]  # mypy sees `warned = True` and messes up.
                        warnings.warn(
                            "Passing a sequence of tuples for 'choices' is deprecated since 2.1.2a1, "
                            "please pass a mapping instead.",
                            category=DeprecationWarning,
                            stacklevel=2 + _stack_level,
                        )
                        warned = True

                    actual_choices[choice[0]] = choice[1]

                else:
                    actual_choices[choice.capitalize()] = choice

        return self._add_option(
            name,
            description,
            hikari.OptionType.STRING,
            choices=actual_choices,
            converters=converters,
            default=default,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_int_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        choices: typing.Optional[collections.Mapping[str, int]] = None,
        converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
        default: typing.Any = _UNDEFINED_DEFAULT,
        min_value: typing.Optional[int] = None,
        max_value: typing.Optional[int] = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        r"""Add an integer option to the slash command.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        choices : typing.Optional[collections.abc.Mapping[str, int]]
            The option's choices.

            This is a mapping of [option_name, option_value] where option_name
            should be a string of up to 100 characters and option_value should
            be an integer.
        converters : typing.Union[collections.abc.Sequence[ConverterSig], ConverterSig, None]
            The option's converters.

            This may be either one or multiple `ConverterSig` callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        min_value : typing.Optional[int]
            The option's (inclusive) minimum value.

            Defaults to no minimum value.
        max_value : typing.Optional[int]
            The option's (inclusive) maximum value.

            Defaults to no minimum value.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used and the `coverters` field will be ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
            * If `min_value` is greater than `max_value`.
        """
        return self._add_option(
            name,
            description,
            hikari.OptionType.INTEGER,
            choices=choices,
            converters=converters,
            default=default,
            min_value=min_value,
            max_value=max_value,
            pass_as_kwarg=pass_as_kwarg,
            _stack_level=_stack_level + 1,
        )

    def add_float_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        always_float: bool = True,
        choices: typing.Optional[collections.Mapping[str, float]] = None,
        converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
        default: typing.Any = _UNDEFINED_DEFAULT,
        min_value: typing.Optional[float] = None,
        max_value: typing.Optional[float] = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        r"""Add a float option to a slash command.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        always_float : bool
            If this is set to `True` then the value will always be converted to a
            float (this will happen before it's passed to converters).

            This masks behaviour from Discord where we will either be provided a `float`
            or `int` dependent on what the user provided and defaults to `True`.
        choices : typing.Optional[collections.abc.Mapping[str, float]]
            The option's choices.

            This is a mapping of [option_name, option_value] where option_name
            should be a string of up to 100 characters and option_value should
            be a float.
        converters : typing.Union[collections.abc.Sequence[ConverterSig], ConverterSig, None]
            The option's converters.

            This may be either one or multiple `ConverterSig` callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        min_value : typing.Optional[float]
            The option's (inclusive) minimum value.

            Defaults to no minimum value.
        max_value : typing.Optional[float]
            The option's (inclusive) maximum value.

            Defaults to no minimum value.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used and the fields `coverters`, and `always_float` will be
            ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
            * If `min_value` is greater than `max_value`.
        """
        return self._add_option(
            name,
            description,
            hikari.OptionType.FLOAT,
            choices=choices,
            converters=converters,
            default=default,
            min_value=float(min_value) if min_value is not None else None,
            max_value=float(max_value) if max_value is not None else None,
            pass_as_kwarg=pass_as_kwarg,
            always_float=always_float,
            _stack_level=_stack_level + 1,
        )

    def add_bool_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = _UNDEFINED_DEFAULT,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a boolean option to a slash command.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
        """
        return self._add_option(
            name, description, hikari.OptionType.BOOLEAN, default=default, pass_as_kwarg=pass_as_kwarg
        )

    def add_user_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = _UNDEFINED_DEFAULT,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a user option to a slash command.

        .. note::
            This may result in `hikari.InteractionMember` or
            `hikari.users.User` if the user isn't in the current guild or if this
            command was executed in a DM channel.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
        """
        return self._add_option(name, description, hikari.OptionType.USER, default=default, pass_as_kwarg=pass_as_kwarg)

    def add_member_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = _UNDEFINED_DEFAULT,
    ) -> _SlashCommandT:
        r"""Add a member option to a slash command.

        .. note::
            This will always result in `hikari.InteractionMember`.

        .. warning::
            Unlike the other options, this is an artificial option which adds
            a restraint to the USER option type and therefore cannot have
            `pass_as_kwarg` set to `False` as this artificial constaint isn't
            present when its not being passed as a keyword argument.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
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
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
        """
        return self._add_option(name, description, hikari.OptionType.USER, default=default, only_member=True)

    def add_channel_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = _UNDEFINED_DEFAULT,
        types: typing.Optional[collections.Collection[type[hikari.PartialChannel]]] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a channel option to a slash command.

        .. note::
            This will always result in `hikari.InteractionChannel`.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Parameters
        ----------
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        types : typing.Optional[collections.abc.Collection[type[hikari.PartialChannel]]]
            A collection of the channel classes this option should accept.

            If left as `None` or empty then the option will allow all channel types.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If an invalid type is passed in `types`.
        """
        import itertools

        if types:
            try:
                channel_types = list(set(itertools.chain.from_iterable(map(_channel_types.__getitem__, types))))

            except KeyError as exc:
                raise ValueError(f"Unknown channel type {exc.args[0]}") from exc

        else:
            channel_types = None

        return self._add_option(
            name,
            description,
            hikari.OptionType.CHANNEL,
            channel_types=channel_types,
            default=default,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_role_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = _UNDEFINED_DEFAULT,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a role option to a slash command.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
        """
        return self._add_option(name, description, hikari.OptionType.ROLE, default=default, pass_as_kwarg=pass_as_kwarg)

    def add_mentionable_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = _UNDEFINED_DEFAULT,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a mentionable option to a slash command.

        .. note::
            This may target roles, guild members or users and results in
            `Union[hikari.User, hikari.InteractionMember, hikari.Role]`.

        Parameters
        ----------
        name : str
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description : str
            The option's description.
            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        default : typing.Any
            The option's default value.
            If this is left as undefined then this option will be required.
        pass_as_kwarg : bool
            Whether or not to pass this option as a keyword argument to the
            command callback.

            Defaults to `True`. If `False` is passed here then `default` will
            only decide whether the option is required without the actual value
            being used.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:
            * If the option name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
        """
        return self._add_option(
            name, description, hikari.OptionType.MENTIONABLE, default=default, pass_as_kwarg=pass_as_kwarg
        )

    async def _process_args(self, ctx: abc.SlashContext, /) -> collections.Mapping[str, typing.Any]:
        keyword_args: dict[str, typing.Union[int, float, str, hikari.User, hikari.Role, hikari.InteractionChannel]] = {}
        for tracked_option in self._tracked_options.values():
            if not (option := ctx.options.get(tracked_option.name)):
                if tracked_option.default is _UNDEFINED_DEFAULT:
                    raise RuntimeError(  # TODO: ConversionError?
                        f"Required option {tracked_option.name} is missing data, are you sure your commands"
                        " are up to date?"
                    )

                else:
                    keyword_args[tracked_option.name] = tracked_option.default

            elif option.type is hikari.OptionType.USER:
                member: typing.Optional[hikari.InteractionMember] = None
                if tracked_option.is_only_member and not (member := option.resolve_to_member(default=None)):
                    raise errors.ConversionError(
                        f"Couldn't find member for provided user: {option.value}", tracked_option.name
                    )

                keyword_args[option.name] = member or option.resolve_to_user()

            elif option.type is hikari.OptionType.CHANNEL:
                keyword_args[option.name] = option.resolve_to_channel()

            elif option.type is hikari.OptionType.ROLE:
                keyword_args[option.name] = option.resolve_to_role()

            elif option.type is hikari.OptionType.MENTIONABLE:
                member = None
                if tracked_option.is_only_member and not (member := option.resolve_to_member()):
                    raise errors.ConversionError(
                        f"Couldn't find member for provided user: {option.value}", tracked_option.name
                    )

                keyword_args[option.name] = member or option.resolve_to_mentionable()

            else:
                value = option.value
                # To be type safe we obfuscate the fact that discord's double type will provide an int or float
                # depending on the value Discord inputs by always casting to float.
                if tracked_option.type is hikari.OptionType.FLOAT and tracked_option.is_always_float:
                    value = float(value)

                if tracked_option.converters:
                    value = await tracked_option.convert(ctx, option.value)

                keyword_args[option.name] = value

        return keyword_args

    async def execute(
        self,
        ctx: abc.SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.SlashHooks]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        if self._always_defer and not ctx.has_been_deferred and not ctx.has_responded:
            await ctx.defer()

        ctx = ctx.set_command(self)
        own_hooks = self._hooks or _EMPTY_HOOKS
        try:
            await own_hooks.trigger_pre_execution(ctx, hooks=hooks)

            if self._tracked_options:
                kwargs = await self._process_args(ctx)

            else:
                kwargs = _EMPTY_DICT

            await self._callback.resolve_with_command_context(ctx, ctx, **kwargs)

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

    def copy(
        self: _SlashCommandT, *, _new: bool = True, parent: typing.Optional[abc.SlashCommandGroup] = None
    ) -> _SlashCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        if not _new:
            self._callback = copy.copy(self._callback)
            return super().copy(_new=_new, parent=parent)

        return super().copy(_new=_new, parent=parent)


def as_message_command(
    name: str, /, *names: str
) -> collections.Callable[[_CallbackishT[abc.CommandCallbackSigT],], MessageCommand[abc.CommandCallbackSigT]]:
    """Build a message command from a decorated callback.

    Parameters
    ----------
    name : str
        The command name.

    Other Parameters
    ----------------
    *names : str
        Variable positional arguments of other names for the command.

    Returns
    -------
    collections.abc.Callable[[_CallbackishT[CommandCallbackSigT]], MessageCommand[CommandCallbackSigT]]
        The decorator callback used to make a `MessageCommand`.

        This can either wrap a raw command callback or another callable command instance
        (e.g. `SlashCommand`, `MessageCommand`, `MessageCommandGroup`) and will manage
        loading the other command into a component when using `tanjun.Component.load_from_scope`.
    """

    def decorator(
        callback: _CallbackishT[abc.CommandCallbackSigT],
        /,
    ) -> MessageCommand[abc.CommandCallbackSigT]:
        if isinstance(callback, (abc.SlashCommand, abc.MessageCommand)):
            return MessageCommand(callback.callback, name, *names, _wrapped_command=callback)

        return MessageCommand(callback, name, *names)

    return decorator


def as_message_command_group(
    name: str, /, *names: str, strict: bool = False
) -> collections.Callable[[_CallbackishT[abc.CommandCallbackSigT]], MessageCommandGroup[abc.CommandCallbackSigT]]:
    """Build a message command group from a decorated callback.

    Parameters
    ----------
    name : str
        The command name.

    Other Parameters
    ----------------
    *names : str
        Variable positional arguments of other names for the command.
    strict : bool
        Whether this command group should only allow commands without spaces in their names.

        This allows for a more optimised command search pattern to be used and
        enforces that command names are unique to a single command within the group.

    Returns
    -------
    collections.abc.Callable[[_CallbackishT[CommandCallbackSigT]], MessageCommand[CommandCallbackSigT]]
        The decorator callback used to make a `MessageCommandGroup`.

        This can either wrap a raw command callback or another callable command instance
        (e.g. `SlashCommand`, `MessageCommand`, `MessageCommandGroup`) and will manage
        loading the other command into a component when using `tanjun.Component.load_from_scope`.
    """

    def decorator(callback: _CallbackishT[abc.CommandCallbackSigT], /) -> MessageCommandGroup[abc.CommandCallbackSigT]:
        if isinstance(callback, (abc.SlashCommand, abc.MessageCommand)):
            return MessageCommandGroup(callback.callback, name, *names, strict=strict, _wrapped_command=callback)

        return MessageCommandGroup(callback, name, *names, strict=strict)

    return decorator


class MessageCommand(PartialCommand[abc.MessageContext], abc.MessageCommand[abc.CommandCallbackSigT]):
    """Standard implementation of a message command."""

    __slots__ = ("_callback", "_names", "_parent", "_parser", "_wrapped_command")

    def __init__(
        self,
        callback: abc.CommandCallbackSigT,
        name: str,
        /,
        *names: str,
        _wrapped_command: typing.Optional[abc.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        """Initialise a message command.

        Parameters
        ----------
        callback : collections.abc.Callable[[tanjun.abc.MessageContext, ...], collections.abc.Awaitable[None]]
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type `tanjun.abc.MessageContext`, returns `None` and may use
            dependency injection to access other services.
        name : str
            The command name.

        Other Parameters
        ----------------
        *names : str
            Variable positional arguments of other names for the command.
        """
        super().__init__()
        self._callback = injecting.CallbackDescriptor[None](callback)
        self._names = list(dict.fromkeys((name, *names)))
        self._parent: typing.Optional[abc.MessageCommandGroup[typing.Any]] = None
        self._parser: typing.Optional[parsing.AbstractParser] = None
        self._wrapped_command = _wrapped_command

    def __repr__(self) -> str:
        return f"Command <{self._names}>"

    if typing.TYPE_CHECKING:
        __call__: abc.CommandCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback.callback(*args, **kwargs)

    @property
    def callback(self) -> abc.CommandCallbackSigT:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        return typing.cast(abc.CommandCallbackSigT, self._callback.callback)

    @property
    # <<inherited docstring from tanjun.abc.MessageCommand>>.
    def names(self) -> collections.Collection[str]:
        return self._names.copy()

    @property
    def needs_injector(self) -> bool:
        return self._callback.needs_injector

    @property
    def parent(self) -> typing.Optional[abc.MessageCommandGroup[typing.Any]]:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        return self._parent

    @property
    def parser(self) -> typing.Optional[parsing.AbstractParser]:
        return self._parser

    def bind_client(self: _MessageCommandT, client: abc.Client, /) -> _MessageCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_client(client)
        if self._parser:
            self._parser.bind_client(client)

        return self

    def bind_component(self: _MessageCommandT, component: abc.Component, /) -> _MessageCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_component(component)
        if self._parser:
            self._parser.bind_component(component)

        return self

    def copy(
        self: _MessageCommandT,
        *,
        parent: typing.Optional[abc.MessageCommandGroup[typing.Any]] = None,
        _new: bool = True,
    ) -> _MessageCommandT:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        if not _new:
            self._callback = copy.copy(self._callback)
            self._names = self._names.copy()
            self._parent = parent
            self._parser = self._parser.copy() if self._parser else None
            return super().copy(_new=_new)

        return super().copy(_new=_new)

    def set_parent(
        self: _MessageCommandT, parent: typing.Optional[abc.MessageCommandGroup[typing.Any]], /
    ) -> _MessageCommandT:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        self._parent = parent
        return self

    def set_parser(self: _MessageCommandT, parser: typing.Optional[parsing.AbstractParser], /) -> _MessageCommandT:
        self._parser = parser
        return self

    async def check_context(self, ctx: abc.MessageContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        ctx.set_command(self)
        result = await utilities.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    async def execute(
        self,
        ctx: abc.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.MessageHooks]] = None,
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

            await self._callback.resolve_with_command_context(ctx, ctx, **kwargs)

        except errors.CommandError as exc:
            response = exc.message if len(exc.message) <= 2000 else exc.message[:1997] + "..."
            await ctx.respond(content=response)

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

    def load_into_component(self, component: abc.Component, /) -> None:
        # <<inherited docstring from tanjun.components.load_into_component>>.
        if not self._parent:
            component.add_message_command(self)

        if self._wrapped_command and isinstance(self._wrapped_command, components.AbstractComponentLoader):
            self._wrapped_command.load_into_component(component)


class MessageCommandGroup(MessageCommand[abc.CommandCallbackSigT], abc.MessageCommandGroup[abc.CommandCallbackSigT]):
    """Standard implementation of a message command group."""

    __slots__ = ("_commands", "_is_strict", "_names_to_commands")

    def __init__(
        self,
        callback: abc.CommandCallbackSigT,
        name: str,
        /,
        *names: str,
        strict: bool = False,
        _wrapped_command: typing.Optional[abc.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        """Initialise a message command group.

        Parameters
        ----------
        name : str
            The command name.

        Other Parameters
        ----------------
        *names : str
            Variable positional arguments of other names for the command.
        strict : bool
            Whether this command group should only allow commands without spaces in their names.

            This allows for a more optimised command search pattern to be used and
            enforces that command names are unique to a single command within the group.
        """
        super().__init__(callback, name, *names, _wrapped_command=_wrapped_command)
        self._commands: list[abc.MessageCommand[typing.Any]] = []
        self._is_strict = strict
        self._names_to_commands: dict[str, abc.MessageCommand[typing.Any]] = {}

    def __repr__(self) -> str:
        return f"CommandGroup <{len(self._commands)}: {self._names}>"

    @property
    def commands(self) -> collections.Collection[abc.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.MessageCommandGroup>>.
        return self._commands.copy()

    @property
    def is_strict(self) -> bool:
        return self._is_strict

    def copy(
        self: _MessageCommandGroupT,
        *,
        parent: typing.Optional[abc.MessageCommandGroup[typing.Any]] = None,
        _new: bool = True,
    ) -> _MessageCommandGroupT:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        if not _new:
            commands = {command: command.copy(parent=self) for command in self._commands}
            self._commands = list(commands.values())
            self._names_to_commands = {name: commands[command] for name, command in self._names_to_commands.items()}
            return super().copy(parent=parent, _new=_new)

        return super().copy(parent=parent, _new=_new)

    def add_command(self: _MessageCommandGroupT, command: abc.MessageCommand[typing.Any], /) -> _MessageCommandGroupT:
        """Add a command to this group.

        Parameters
        ----------
        command : MessageCommand
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
        if command in self._commands:
            return self

        if self._is_strict:
            if any(" " in name for name in command.names):
                raise ValueError("Sub-command names may not contain spaces in a strict message command group")

            if name_conflicts := self._names_to_commands.keys() & command.names:
                raise ValueError(
                    "Sub-command names must be unique in a strict message command group. "
                    "The following conflicts were found " + ", ".join(name_conflicts)
                )

            self._names_to_commands.update((name, command) for name in command.names)

        command.set_parent(self)
        self._commands.append(command)
        return self

    def remove_command(
        self: _MessageCommandGroupT, command: abc.MessageCommand[typing.Any], /
    ) -> _MessageCommandGroupT:
        # <<inherited docstring from tanjun.abc.MessageCommandGroup>>.
        self._commands.remove(command)
        if self._is_strict:
            for name in command.names:
                if self._names_to_commands.get(name) == command:
                    del self._names_to_commands[name]

        command.set_parent(None)
        return self

    def with_command(self, command: AnyMessageCommandT, /) -> AnyMessageCommandT:
        self.add_command(command)
        return command

    def bind_client(self: _MessageCommandGroupT, client: abc.Client, /) -> _MessageCommandGroupT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_client(client)
        for command in self._commands:
            command.bind_client(client)

        return self

    def bind_component(self: _MessageCommandGroupT, component: abc.Component, /) -> _MessageCommandGroupT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_component(component)
        for command in self._commands:
            command.bind_component(component)

        return self

    def find_command(self, content: str, /) -> collections.Iterable[tuple[str, abc.MessageCommand[typing.Any]]]:
        if self._is_strict:
            name = content.split(" ")[0]
            if command := self._names_to_commands.get(name):
                yield name, command
            return

        for command in self._commands:
            if (name_ := utilities.match_prefix_names(content, command.names)) is not None:
                yield name_, command

    async def execute(
        self,
        ctx: abc.MessageContext,
        /,
        *,
        hooks: typing.Optional[collections.MutableSet[abc.MessageHooks]] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.MessageCommand>>.
        if ctx.message.content is None:
            raise ValueError("Cannot execute a command with a content-less message")

        if self._hooks:
            if hooks is None:
                hooks = set()

            hooks.add(self._hooks)

        for name, command in self.find_command(ctx.content):
            if await command.check_context(ctx):
                content = ctx.content[len(name) :]
                lstripped_content = content.lstrip()
                space_len = len(content) - len(lstripped_content)
                ctx.set_triggering_name(ctx.triggering_name + (" " * space_len) + name)
                ctx.set_content(lstripped_content)
                await command.execute(ctx, hooks=hooks)
                return

        await super().execute(ctx, hooks=hooks)
