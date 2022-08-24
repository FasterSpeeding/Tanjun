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
"""Slash command implementations."""
from __future__ import annotations

__all__: list[str] = [
    "BaseSlashCommand",
    "ConverterSig",
    "SlashCommand",
    "SlashCommandGroup",
    "UNDEFINED_DEFAULT",
    "as_slash_command",
    "slash_command_group",
    "with_attachment_slash_option",
    "with_bool_slash_option",
    "with_channel_slash_option",
    "with_float_slash_option",
    "with_int_slash_option",
    "with_member_slash_option",
    "with_mentionable_slash_option",
    "with_role_slash_option",
    "with_str_slash_option",
    "with_user_slash_option",
]

import copy
import itertools
import re
import typing
import warnings
from collections import abc as collections

import hikari

from .. import _internal
from .. import abc as tanjun
from .. import components
from .. import conversion
from .. import errors
from .. import hooks as hooks_
from . import base

if typing.TYPE_CHECKING:
    from hikari.api import special_endpoints as special_endpoints_api

    _AutocompleteCallbackSigT = typing.TypeVar("_AutocompleteCallbackSigT", bound=tanjun.AutocompleteCallbackSig)
    _BaseSlashCommandT = typing.TypeVar("_BaseSlashCommandT", bound="BaseSlashCommand")
    _SlashCommandT = typing.TypeVar("_SlashCommandT", bound="SlashCommand[typing.Any]")
    _SlashCommandGroupT = typing.TypeVar("_SlashCommandGroupT", bound="SlashCommandGroup")
    _CommandT = typing.Union[
        tanjun.MenuCommand["_CommandCallbackSigT", typing.Any],
        tanjun.MessageCommand["_CommandCallbackSigT"],
        tanjun.SlashCommand["_CommandCallbackSigT"],
    ]
    _CallbackishT = typing.Union["_CommandCallbackSigT", _CommandT["_CommandCallbackSigT"]]

_SCOMMAND_NAME_REG: typing.Final[re.Pattern[str]] = re.compile(r"^[\w-]{1,32}$", flags=re.UNICODE)
_CommandCallbackSigT = typing.TypeVar("_CommandCallbackSigT", bound=tanjun.CommandCallbackSig)
_EMPTY_DICT: typing.Final[dict[typing.Any, typing.Any]] = {}
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()

ConverterSig = typing.Union[
    collections.Callable[..., collections.Coroutine[typing.Any, typing.Any, typing.Any]],
    collections.Callable[..., typing.Any],
]


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
    default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
    default_to_ephemeral: typing.Optional[bool] = None,
    dm_enabled: typing.Optional[bool] = None,
    is_global: bool = True,
) -> SlashCommandGroup:
    r"""Create a slash command group.

    !!! note
        Unlike message command groups, slash command groups cannot
        be callable functions themselves.

    !!! note
        Under the standard implementation, `is_global` is used to determine whether
        the command should be bulk set by [tanjun.Client.declare_global_commandsadd_command
        or when `declare_global_commands` is True

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

    Parameters
    ----------
    name
        The name of the command group.

        This must match the regex `^[\w-]{1,32}$` in Unicode mode and be lowercase.
    description
        The description of the command group.
    default_member_permissions
        Member permissions necessary to utilize this command by default.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    default_to_ephemeral
        Whether this command's responses should default to ephemeral unless flags
        are set to override this.

        If this is left as [None][] then the default set on the parent command(s),
        component or client will be in effect.
    dm_enabled
        Whether this command is enabled in DMs with the bot.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    is_global
        Whether this command is a global command.

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
        default_member_permissions=default_member_permissions,
        default_to_ephemeral=default_to_ephemeral,
        dm_enabled=dm_enabled,
        is_global=is_global,
    )


class _ResultProto(typing.Protocol):
    @typing.overload
    def __call__(self, _: _CommandT[_CommandCallbackSigT], /) -> SlashCommand[_CommandCallbackSigT]:
        ...

    @typing.overload
    def __call__(self, _: _CommandCallbackSigT, /) -> SlashCommand[_CommandCallbackSigT]:
        ...

    def __call__(self, _: _CallbackishT[_CommandCallbackSigT], /) -> SlashCommand[_CommandCallbackSigT]:
        raise NotImplementedError


def as_slash_command(
    name: str,
    description: str,
    /,
    *,
    always_defer: bool = False,
    default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
    default_to_ephemeral: typing.Optional[bool] = None,
    dm_enabled: typing.Optional[bool] = None,
    is_global: bool = True,
    sort_options: bool = True,
    validate_arg_keys: bool = True,
) -> _ResultProto:
    r"""Build a [tanjun.SlashCommand][] by decorating a function.

    !!! note
        Under the standard implementation, `is_global` is used to determine whether
        the command should be bulk set by [tanjun.Client.declare_global_commands][]
        or when `declare_global_commands` is True

    !!! warning
        `is_global` is ignored for commands within slash command groups.

    !!! note
        If you want your first response to be ephemeral while using
        `always_defer`, you must set `default_to_ephemeral` to `True`.

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
    name
        The command's name.

        This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
    description
        The command's description.
        This should be inclusively between 1-100 characters in length.
    always_defer
        Whether the contexts this command is executed with should always be deferred
        before being passed to the command's callback.
    default_member_permissions
        Member permissions necessary to utilize this command by default.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    default_to_ephemeral
        Whether this command's responses should default to ephemeral unless flags
        are set to override this.

        If this is left as [None][] then the default set on the parent command(s),
        component or client will be in effect.
    dm_enabled
        Whether this command is enabled in DMs with the bot.

        If this is [None][] then the configuration for the parent component or client
        will be used.
    is_global
        Whether this command is a global command.
    sort_options
        Whether this command should sort its set options based on whether
        they're required.

        If this is [True][] then the options are re-sorted to meet the requirement
        from Discord that required command options be listed before optional
        ones.
    validate_arg_keys
        Whether to validate that option keys match the command callback's signature.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.CommandCallbackSig], SlashCommand]
        The decorator callback used to make a [tanjun.SlashCommand][].

        This can either wrap a raw command callback or another callable command instance
        (e.g. [tanjun.MenuCommand][], [tanjun.MessageCommand][] [tanjun.SlashCommand][])
        and will manage loading the other command into a component when using
        [tanjun.Component.load_from_scope][].

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:

        * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
        * If the command name has uppercase characters.
        * If the description is over 100 characters long.
    """

    def decorator(callback: _CallbackishT[_CommandCallbackSigT], /) -> SlashCommand[_CommandCallbackSigT]:
        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            wrapped_command = callback
            callback = callback.callback

        else:
            wrapped_command = None

        return SlashCommand(
            callback,
            name,
            description,
            always_defer=always_defer,
            default_member_permissions=default_member_permissions,
            default_to_ephemeral=default_to_ephemeral,
            dm_enabled=dm_enabled,
            is_global=is_global,
            sort_options=sort_options,
            validate_arg_keys=validate_arg_keys,
            _wrapped_command=wrapped_command,
        )

    return decorator


UNDEFINED_DEFAULT = object()
"""Singleton used for marking slash command defaults as undefined."""


def with_attachment_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add an attachment option to a slash command.

    For more information on this function's parameters see
    [tanjun.SlashCommand.add_attachment_option][].

    Examples
    --------
    ```py
    @with_attachment_slash_option("name", "A name.")
    @as_slash_command("command", "A command")
    async def command(self, ctx: tanjun.abc.SlashContext, name: hikari.Attachment) -> None:
        ...
    ```

    Returns
    -------
    collections.abc.Callable[[_SlashCommandT], _SlashCommandT]
        Decorator callback which adds the option to the command.
    """
    return lambda command: command.add_attachment_option(
        name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg
    )


def with_str_slash_option(
    name: str,
    description: str,
    /,
    *,
    autocomplete: typing.Optional[tanjun.AutocompleteCallbackSig] = None,
    choices: typing.Union[collections.Mapping[str, str], collections.Sequence[str], None] = None,
    converters: typing.Union[collections.Sequence[ConverterSig], ConverterSig] = (),
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a string option to a slash command.

    For more information on this function's parameters see
    [tanjun.commands.SlashCommand.add_str_option][].

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
        autocomplete=autocomplete,
        choices=choices,
        converters=converters,
        default=default,
        key=key,
        pass_as_kwarg=pass_as_kwarg,
        _stack_level=1,
    )


def with_int_slash_option(
    name: str,
    description: str,
    /,
    *,
    autocomplete: typing.Optional[tanjun.AutocompleteCallbackSig] = None,
    choices: typing.Optional[collections.Mapping[str, int]] = None,
    converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    min_value: typing.Optional[int] = None,
    max_value: typing.Optional[int] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add an integer option to a slash command.

    For information on this function's parameters see
    [tanjun.SlashCommand.add_int_option][].

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
        autocomplete=autocomplete,
        default=default,
        choices=choices,
        converters=converters,
        key=key,
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
    autocomplete: typing.Optional[tanjun.AutocompleteCallbackSig] = None,
    choices: typing.Optional[collections.Mapping[str, float]] = None,
    converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    min_value: typing.Optional[float] = None,
    max_value: typing.Optional[float] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a float option to a slash command.

    For information on this function's parameters see
    [tanjun.SlashCommand.add_float_option][].

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
        autocomplete=autocomplete,
        default=default,
        choices=choices,
        converters=converters,
        key=key,
        min_value=min_value,
        max_value=max_value,
        pass_as_kwarg=pass_as_kwarg,
        _stack_level=1,
    )


def with_bool_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a boolean option to a slash command.

    For information on this function's parameters see
    [tanjun.SlashCommand.add_bool_option][].

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
    return lambda c: c.add_bool_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


def with_user_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a user option to a slash command.

    For information on this function's parameters see
    [tanjun.SlashCommand.add_user_option][].

    !!! note
        This may result in [hikari.interactions.base_interactions.InteractionMember][] or
        [hikari.users.User][] if the user isn't in the current guild or if this
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
    return lambda c: c.add_user_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


def with_member_slash_option(
    name: str, description: str, /, *, default: typing.Any = UNDEFINED_DEFAULT, key: typing.Optional[str] = None
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a member option to a slash command.

    For information on this function's arguments see
    [tanjun.SlashCommand.add_member_option][].

    !!! note
        This will always result in [hikari.interactions.base_interactions.InteractionMember][].

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
    return lambda c: c.add_member_option(name, description, default=default, key=key)


_CHANNEL_TYPES: dict[type[hikari.PartialChannel], set[hikari.ChannelType]] = {
    hikari.GuildTextChannel: {hikari.ChannelType.GUILD_TEXT},
    hikari.DMChannel: {hikari.ChannelType.DM},
    hikari.GuildVoiceChannel: {hikari.ChannelType.GUILD_VOICE},
    hikari.GroupDMChannel: {hikari.ChannelType.GROUP_DM},
    hikari.GuildCategory: {hikari.ChannelType.GUILD_CATEGORY},
    hikari.GuildNewsChannel: {hikari.ChannelType.GUILD_NEWS},
    hikari.GuildStageChannel: {hikari.ChannelType.GUILD_STAGE},
}


for _channel_cls, _types in _CHANNEL_TYPES.copy().items():
    for _mro_type in _channel_cls.mro():
        if isinstance(_mro_type, type) and issubclass(_mro_type, hikari.PartialChannel):
            try:
                _CHANNEL_TYPES[_mro_type].update(_types)
            except KeyError:
                _CHANNEL_TYPES[_mro_type] = _types.copy()


def with_channel_slash_option(
    name: str,
    description: str,
    /,
    *,
    types: typing.Optional[collections.Collection[typing.Union[type[hikari.PartialChannel], int]]] = None,
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a channel option to a slash command.

    For information on this function's parameters see
    [tanjun.SlashCommand.add_channel_option][].

    !!! note
        This will always result in [hikari.interactions.command_interactions.InteractionChannel][].

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
    return lambda c: c.add_channel_option(
        name, description, types=types, default=default, key=key, pass_as_kwarg=pass_as_kwarg
    )


def with_role_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a role option to a slash command.

    For information on this function's parameters see
    [tanjun.SlashCommand.add_role_option][].

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
    return lambda c: c.add_role_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


def with_mentionable_slash_option(
    name: str,
    description: str,
    /,
    *,
    default: typing.Any = UNDEFINED_DEFAULT,
    key: typing.Optional[str] = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a mentionable option to a slash command.

    For information on this function's arguments see
    [tanjun.SlashCommand.add_mentionable_option][].

    !!! note
        This may target roles, guild members or users and results in
        `hikari.User | hikari.InteractionMember | hikari.Role`.

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
    return lambda c: c.add_mentionable_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


class _TrackedOption:
    __slots__ = ("converters", "default", "is_always_float", "is_only_member", "key", "name", "type")

    def __init__(
        self,
        *,
        key: str,
        name: str,
        option_type: typing.Union[hikari.OptionType, int],
        always_float: bool = False,
        converters: typing.Optional[list[ConverterSig]] = None,
        only_member: bool = False,
        default: typing.Any = UNDEFINED_DEFAULT,
    ) -> None:
        self.converters = converters or []
        self.default = default
        self.is_always_float = always_float
        self.is_only_member = only_member
        self.key = key
        self.name = name
        self.type = option_type

    def check_client(self, client: tanjun.Client, /) -> None:
        for converter in self.converters:
            if isinstance(converter, conversion.BaseConverter):
                converter.check_client(client, f"{self.name} slash command option")

    async def convert(self, ctx: tanjun.SlashContext, value: typing.Any, /) -> typing.Any:
        if not self.converters:
            return value

        exceptions: list[ValueError] = []
        for converter in self.converters:
            try:
                return await ctx.call_with_async_di(converter, value)

            except ValueError as exc:
                exceptions.append(exc)

        raise errors.ConversionError(f"Couldn't convert {self.type} '{self.name}'", self.name, errors=exceptions)


_SlashCommandBuilderT = typing.TypeVar("_SlashCommandBuilderT", bound="_SlashCommandBuilder")


class _SlashCommandBuilder(hikari.impl.SlashCommandBuilder):
    __slots__ = ("_has_been_sorted", "_options_dict", "_sort_options")

    def __init__(
        self,
        name: str,
        description: str,
        sort_options: bool,
        *,
        id_: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,
    ) -> None:
        super().__init__(name, description, id=id_)  # type: ignore
        self._has_been_sorted = True
        self._options_dict: dict[str, hikari.CommandOption] = {}
        self._sort_options = sort_options

    def add_option(self: _SlashCommandBuilderT, option: hikari.CommandOption) -> _SlashCommandBuilderT:
        if self._options:
            self._has_been_sorted = False

        super().add_option(option)
        self._options_dict[option.name] = option
        return self

    def get_option(self, name: str) -> typing.Optional[hikari.CommandOption]:
        return self._options_dict.get(name)

    def sort(self: _SlashCommandBuilderT) -> _SlashCommandBuilderT:
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

    # TODO: can we just del _SlashCommandBuilder.__copy__ to go back to the default?
    def copy(self, /) -> _SlashCommandBuilder:
        builder = _SlashCommandBuilder(self.name, self.description, self._sort_options, id_=self.id)

        for option in self.options:
            builder.add_option(option)

        return builder


class BaseSlashCommand(base.PartialCommand[tanjun.SlashContext], tanjun.BaseSlashCommand):
    """Base class used for the standard slash command implementations."""

    __slots__ = (
        "_default_member_permissions",
        "_defaults_to_ephemeral",
        "_description",
        "_is_dm_enabled",
        "_is_global",
        "_name",
        "_parent",
        "_tracked_command",
    )

    def __init__(
        self,
        name: str,
        description: str,
        /,
        *,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
    ) -> None:
        super().__init__()
        _validate_name(name)
        if len(description) > 100:
            raise ValueError("The command description cannot be over 100 characters in length")

        if default_member_permissions is not None:
            default_member_permissions = hikari.Permissions(default_member_permissions)

        self._default_member_permissions = default_member_permissions
        self._defaults_to_ephemeral = default_to_ephemeral
        self._description = description
        self._is_dm_enabled = dm_enabled
        self._is_global = is_global
        self._name = name
        self._parent: typing.Optional[tanjun.SlashCommandGroup] = None
        self._tracked_command: typing.Optional[hikari.SlashCommand] = None

    @property
    def default_member_permissions(self) -> typing.Optional[hikari.Permissions]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._default_member_permissions

    @property
    def defaults_to_ephemeral(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._defaults_to_ephemeral

    @property
    def description(self) -> str:  # TODO: this feels like a mistake
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._description

    @property
    def is_dm_enabled(self) -> typing.Optional[bool]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_dm_enabled

    @property
    def is_global(self) -> bool:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_global

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._name

    @property
    def parent(self) -> typing.Optional[tanjun.SlashCommandGroup]:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._parent

    @property
    def tracked_command(self) -> typing.Optional[hikari.SlashCommand]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._tracked_command

    @property
    def tracked_command_id(self) -> typing.Optional[hikari.Snowflake]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._tracked_command.id if self._tracked_command else None

    @property
    def type(self) -> typing.Literal[hikari.CommandType.SLASH]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return hikari.CommandType.SLASH

    def set_tracked_command(self: _BaseSlashCommandT, command: hikari.PartialCommand, /) -> _BaseSlashCommandT:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        if not isinstance(command, hikari.SlashCommand):
            raise TypeError("The tracked command must be a slash command")

        self._tracked_command = command
        return self

    def set_ephemeral_default(self: _BaseSlashCommandT, state: typing.Optional[bool], /) -> _BaseSlashCommandT:
        """Set whether this command's responses should default to ephemeral.

        Parameters
        ----------
        state
            Whether this command's responses should default to ephemeral.
            This will be overridden by any response calls which specify flags.

            Setting this to [None][] will let the default set on the parent
            command(s), component or client propagate and decide the ephemeral
            default for contexts used by this command.

        Returns
        -------
        Self
            This command to allow for chaining.
        """
        self._defaults_to_ephemeral = state
        return self

    def set_parent(
        self: _BaseSlashCommandT, parent: typing.Optional[tanjun.SlashCommandGroup], /
    ) -> _BaseSlashCommandT:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        self._parent = parent
        return self

    async def check_context(self, ctx: tanjun.SlashContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        ctx.set_command(self)
        result = await _internal.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    def copy(
        self: _BaseSlashCommandT, *, parent: typing.Optional[tanjun.SlashCommandGroup] = None
    ) -> _BaseSlashCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy()
        inst._parent = parent
        return inst

    def load_into_component(self, component: tanjun.Component, /) -> None:
        # <<inherited docstring from tanjun.components.load_into_component>>.
        if not self._parent:
            component.add_slash_command(self)


class SlashCommandGroup(BaseSlashCommand, tanjun.SlashCommandGroup):
    """Standard implementation of a slash command group.

    !!! note
        Unlike message command groups, slash command groups cannot
        be callable functions themselves.
    """

    __slots__ = ("_commands",)

    def __init__(
        self,
        name: str,
        description: str,
        /,
        *,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
    ) -> None:
        r"""Initialise a slash command group.

        !!! note
            Under the standard implementation, `is_global` is used to determine
            whether the command should be bulk set by [tanjun.Client.declare_global_commands][]
            or when `declare_global_commands` is True

        Parameters
        ----------
        name
            The name of the command group.

            This must match the regex `^[\w-]{1,32}$` in Unicode mode and be lowercase.
        description
            The description of the command group.
        default_member_permissions
            Member permissions necessary to utilize this command by default.

            If this is [None][] then the configuration for the parent component or client
            will be used.
        default_to_ephemeral
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as [None][] then the default set on the parent command(s),
            component or client will be in effect.
        dm_enabled
            Whether this command is enabled in DMs with the bot.

            If this is [None][] then the configuration for the parent component or client
            will be used.
        is_global
            Whether this command is a global command.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the command name has uppercase characters.
            * If the description is over 100 characters long.
        """
        super().__init__(
            name,
            description,
            default_member_permissions=default_member_permissions,
            default_to_ephemeral=default_to_ephemeral,
            dm_enabled=dm_enabled,
            is_global=is_global,
        )
        self._commands: dict[str, tanjun.BaseSlashCommand] = {}

    @property
    def commands(self) -> collections.Collection[tanjun.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.SlashCommandGroup>>.
        return self._commands.copy().values()

    def build(
        self, *, component: typing.Optional[tanjun.Component] = None
    ) -> special_endpoints_api.SlashCommandBuilder:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        builder = _SlashCommandBuilder(self._name, self._description, False)

        for command in self._commands.values():
            option_type = (
                hikari.OptionType.SUB_COMMAND_GROUP
                if isinstance(command, tanjun.SlashCommandGroup)
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

        component = component or self._component

        if self._default_member_permissions is not None:
            builder.set_default_member_permissions(self._default_member_permissions)
        elif component and component.default_app_cmd_permissions is not None:
            builder.set_default_member_permissions(component.default_app_cmd_permissions)

        if self._is_dm_enabled is not None:
            builder.set_is_dm_enabled(self._is_dm_enabled)
        elif component and component.dms_enabled_for_app_cmds is not None:
            builder.set_is_dm_enabled(component.dms_enabled_for_app_cmds)

        return builder

    def copy(
        self: _SlashCommandGroupT, *, parent: typing.Optional[tanjun.SlashCommandGroup] = None
    ) -> _SlashCommandGroupT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy(parent=parent)
        inst._commands = {name: command.copy(parent=inst) for name, command in self._commands.items()}
        return inst

    def add_command(self: _SlashCommandGroupT, command: tanjun.BaseSlashCommand, /) -> _SlashCommandGroupT:
        """Add a slash command to this group.

        !!! warning
            Command groups are only supported within top-level groups.

        Parameters
        ----------
        command
            Command to add to this group.

        Returns
        -------
        Self
            Object of this group to enable chained calls.
        """
        if self._parent and isinstance(command, tanjun.SlashCommandGroup):
            raise ValueError("Cannot add a slash command group to a nested slash command group")

        if len(self._commands) == 25:
            raise ValueError("Cannot add more than 25 commands to a slash command group")

        if command.name in self._commands:
            raise ValueError(f"Command with name {command.name!r} already exists in this group")

        command.set_parent(self)
        self._commands[command.name] = command
        return self

    def remove_command(self: _SlashCommandGroupT, command: tanjun.BaseSlashCommand, /) -> _SlashCommandGroupT:
        """Remove a command from this group.

        Parameters
        ----------
        command
            Command to remove from this group.

        Returns
        -------
        Self
            Object of this group to enable chained calls.
        """
        del self._commands[command.name]
        return self

    def with_command(self, command: _BaseSlashCommandT, /) -> _BaseSlashCommandT:
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
        ctx: tanjun.SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun.SlashHooks]] = None,
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

    async def execute_autocomplete(
        self,
        ctx: tanjun.AutocompleteContext,
        /,
        option: typing.Optional[hikari.AutocompleteInteractionOption] = None,
    ) -> None:
        if not option and ctx.interaction.options:
            option = ctx.interaction.options[0]

        elif option and option.options:
            option = option.options[0]

        else:
            raise RuntimeError("Missing sub-command option")

        command = self._commands.get(option.name)
        if not command:
            raise RuntimeError(f"Sub-command '{option.name}' no found")

        await command.execute_autocomplete(ctx, option=option)


class SlashCommand(BaseSlashCommand, tanjun.SlashCommand[_CommandCallbackSigT]):
    """Standard implementation of a slash command."""

    __slots__ = (
        "_always_defer",
        "_arg_names",
        "_builder",
        "_callback",
        "_client",
        "_float_autocompletes",
        "_int_autocompletes",
        "_str_autocompletes",
        "_tracked_options",
        "_wrapped_command",
    )

    @typing.overload
    def __init__(
        self,
        callback: _CommandT[_CommandCallbackSigT],
        name: str,
        description: str,
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    @typing.overload
    def __init__(
        self,
        callback: _CommandCallbackSigT,
        name: str,
        description: str,
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        ...

    def __init__(
        self,
        callback: _CallbackishT[_CommandCallbackSigT],
        name: str,
        description: str,
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: typing.Union[hikari.Permissions, int, None] = None,
        default_to_ephemeral: typing.Optional[bool] = None,
        dm_enabled: typing.Optional[bool] = None,
        is_global: bool = True,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
        _wrapped_command: typing.Optional[tanjun.ExecutableCommand[typing.Any]] = None,
    ) -> None:
        r"""Initialise a slash command.

        !!! note
            Under the standard implementation, `is_global` is used to determine whether
            the command should be bulk set by [tanjun.Client.declare_global_commands][]
            or when `declare_global_commands` is True

        !!! warning
            `is_global` is ignored for commands within slash command groups.

        !!! note
            If you want your first response to be ephemeral while using
            `always_defer`, you must set `default_to_ephemeral` to `True`.

        Parameters
        ----------
        callback : collections.abc.Callable[[tanjun.abc.SlashContext, ...], collections.abc.Coroutine[Any, Any, None]]
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type [tanjun.abc.SlashContext][], returns `None` and may use
            dependency injection to access other services.
        name
            The command's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The command's description.
            This should be inclusively between 1-100 characters in length.
        always_defer
            Whether the contexts this command is executed with should always be deferred
            before being passed to the command's callback.
        default_member_permissions
            Member permissions necessary to utilize this command by default.

            If this is [None][] then the configuration for the parent component or client
            will be used.
        default_to_ephemeral
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as [None][] then the default set on the parent command(s),
            component or client will be in effect.
        dm_enabled
            Whether this command is enabled in DMs with the bot.

            If this is [None][] then the configuration for the parent component or client
            will be used.
        is_global
            Whether this command is a global command.
        sort_options
            Whether this command should sort its set options based on whether
            they're required.

            If this is [True][] then the options are re-sorted to meet the requirement
            from Discord that required command options be listed before optional
            ones.
        validate_arg_keys
            Whether to validate that option keys match the command callback's signature.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the command name doesn't match the regex `^[\w-]{1,32}$` (Unicode mode).
            * If the command name has uppercase characters.
            * If the description is over 100 characters long.
        """
        super().__init__(
            name,
            description,
            default_member_permissions=default_member_permissions,
            default_to_ephemeral=default_to_ephemeral,
            dm_enabled=dm_enabled,
            is_global=is_global,
        )
        if isinstance(callback, (tanjun.MenuCommand, tanjun.MessageCommand, tanjun.SlashCommand)):
            callback = callback.callback

        self._always_defer = always_defer
        self._arg_names = _internal.get_kwargs(callback) if validate_arg_keys else None
        self._builder = _SlashCommandBuilder(name, description, sort_options)
        self._callback: _CommandCallbackSigT = callback
        self._client: typing.Optional[tanjun.Client] = None
        self._float_autocompletes: dict[str, tanjun.AutocompleteCallbackSig] = {}
        self._int_autocompletes: dict[str, tanjun.AutocompleteCallbackSig] = {}
        self._str_autocompletes: dict[str, tanjun.AutocompleteCallbackSig] = {}
        self._tracked_options: dict[str, _TrackedOption] = {}
        self._wrapped_command = _wrapped_command

    if typing.TYPE_CHECKING:
        __call__: _CommandCallbackSigT

    else:

        async def __call__(self, *args, **kwargs) -> None:
            await self._callback(*args, **kwargs)

    @property
    def callback(self) -> _CommandCallbackSigT:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._callback

    @property
    def float_autocompletes(self) -> collections.Mapping[str, tanjun.AutocompleteCallbackSig]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._float_autocompletes.copy()

    @property
    def int_autocompletes(self) -> collections.Mapping[str, tanjun.AutocompleteCallbackSig]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._int_autocompletes.copy()

    @property
    def str_autocompletes(self) -> collections.Mapping[str, tanjun.AutocompleteCallbackSig]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._str_autocompletes.copy()

    @property
    def wrapped_command(self) -> typing.Optional[tanjun.ExecutableCommand[typing.Any]]:
        """The command object this wraps, if any."""
        return self._wrapped_command

    def bind_client(self: _SlashCommandT, client: tanjun.Client, /) -> _SlashCommandT:
        self._client = client
        super().bind_client(client)
        for option in self._tracked_options.values():
            option.check_client(client)

        return self

    def build(
        self, *, component: typing.Optional[tanjun.Component] = None
    ) -> special_endpoints_api.SlashCommandBuilder:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        builder = self._builder.sort().copy()

        component = component or self._component
        if self._default_member_permissions is not None:
            builder.set_default_member_permissions(self._default_member_permissions)
        elif component and component.default_app_cmd_permissions is not None:
            builder.set_default_member_permissions(component.default_app_cmd_permissions)

        if self._is_dm_enabled is not None:
            builder.set_is_dm_enabled(self._is_dm_enabled)
        elif component and component.dms_enabled_for_app_cmds is not None:
            builder.set_is_dm_enabled(component.dms_enabled_for_app_cmds)

        return builder

    def load_into_component(self, component: tanjun.Component, /) -> None:
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
        autocomplete: bool = False,
        channel_types: typing.Optional[collections.Sequence[int]] = None,
        choices: typing.Union[
            collections.Mapping[str, typing.Union[str, int, float]], collections.Sequence[typing.Any], None
        ] = None,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        min_value: typing.Union[int, float, None] = None,
        max_value: typing.Union[int, float, None] = None,
        only_member: bool = False,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        if len(description) > 100:
            raise ValueError("The option description cannot be over 100 characters in length")

        if len(self._builder.options) == 25:
            raise ValueError("Slash commands cannot have more than 25 options")

        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("The min value cannot be greater than the max value")

        key = key or name
        _validate_name(name)
        if self._arg_names is not None and key not in self._arg_names:
            raise ValueError(f"{key!r} is not a valid keyword argument for {self._callback}")

        type_ = hikari.OptionType(type_)
        if isinstance(converters, collections.Iterable):
            converters = list(converters)

        else:
            converters = [converters]

        if self._client:
            for converter in converters:
                if isinstance(converter, conversion.BaseConverter):
                    converter.check_client(self._client, f"{self._name}'s slash option '{name}'")

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

        required = default is UNDEFINED_DEFAULT
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
                autocomplete=autocomplete,
            )
        )
        if pass_as_kwarg:
            self._tracked_options[name] = _TrackedOption(
                name=name,
                option_type=type_,
                always_float=always_float,
                converters=converters,
                default=default,
                key=key,
                only_member=only_member,
            )
        return self

    def add_attachment_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add an attachment option to the slash command.

        !!! note
            This will result in options of type [hikari.messages.Attachment][].

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.

        Other Parameters
        ----------------
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used and the
            `coverters` field will be ignored.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            name,
            description,
            hikari.OptionType.ATTACHMENT,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_str_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        autocomplete: typing.Optional[tanjun.AutocompleteCallbackSig] = None,
        choices: typing.Union[collections.Mapping[str, str], collections.Sequence[str], None] = None,
        converters: typing.Union[collections.Sequence[ConverterSig], ConverterSig] = (),
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        r"""Add a string option to the slash command.

        !!! note
            As a shorthand, `choices` also supports passing a list of strings
            rather than a dict of names to values (each string will used as
            both the choice's name and value with the names being capitalised).

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        autocomplete
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [str][].
        choices
            The option's choices.

            This either a mapping of [option_name, option_value] where both option_name
            and option_value should be strings of up to 100 characters or a sequence
            of strings where the string will be used for both the choice's name and
            value.
        converters
            The option's converters.

            This may be either one or multiple converter callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used and the
            `coverters` field will be ignored.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
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

        self._add_option(
            name,
            description,
            hikari.OptionType.STRING,
            autocomplete=autocomplete is not None,
            choices=actual_choices,
            converters=converters,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

        if autocomplete:
            self._str_autocompletes[name] = autocomplete

        return self

    def add_int_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        autocomplete: typing.Optional[tanjun.AutocompleteCallbackSig] = None,
        choices: typing.Optional[collections.Mapping[str, int]] = None,
        converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        min_value: typing.Optional[int] = None,
        max_value: typing.Optional[int] = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        r"""Add an integer option to the slash command.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        autocomplete
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [int][].
        choices
            The option's choices.

            This is a mapping of [option_name, option_value] where option_name
            should be a string of up to 100 characters and option_value should
            be an integer.
        converters
            The option's converters.

            This may be either one or multiple converter callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        min_value
            The option's (inclusive) minimum value.
        max_value
            The option's (inclusive) maximum value.
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used and the
            `coverters` field will be ignored.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        self._add_option(
            name,
            description,
            hikari.OptionType.INTEGER,
            autocomplete=autocomplete is not None,
            choices=choices,
            converters=converters,
            default=default,
            key=key,
            min_value=min_value,
            max_value=max_value,
            pass_as_kwarg=pass_as_kwarg,
            _stack_level=_stack_level + 1,
        )

        if autocomplete:
            self._int_autocompletes[name] = autocomplete

        return self

    def add_float_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        always_float: bool = True,
        autocomplete: typing.Optional[tanjun.AutocompleteCallbackSig] = None,
        choices: typing.Optional[collections.Mapping[str, float]] = None,
        converters: typing.Union[collections.Collection[ConverterSig], ConverterSig] = (),
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        min_value: typing.Optional[float] = None,
        max_value: typing.Optional[float] = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> _SlashCommandT:
        r"""Add a float option to a slash command.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        always_float
            If this is set to [True][] then the value will always be converted to a
            float (this will happen before it's passed to converters).

            This masks behaviour from Discord where we will either be provided a [float][]
            or [int][] dependent on what the user provided.
        autocomplete
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [float][].
        choices
            The option's choices.

            This is a mapping of [option_name, option_value] where option_name
            should be a string of up to 100 characters and option_value should
            be a float.
        converters
            The option's converters.

            This may be either one or multiple converter callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        min_value
            The option's (inclusive) minimum value.
        max_value
            The option's (inclusive) maximum value.
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used and the
            fields `coverters`, and `always_float` will be ignored.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        self._add_option(
            name,
            description,
            hikari.OptionType.FLOAT,
            autocomplete=autocomplete is not None,
            choices=choices,
            converters=converters,
            default=default,
            key=key,
            min_value=float(min_value) if min_value is not None else None,
            max_value=float(max_value) if max_value is not None else None,
            pass_as_kwarg=pass_as_kwarg,
            always_float=always_float,
            _stack_level=_stack_level + 1,
        )

        if autocomplete:
            self._float_autocompletes[name] = autocomplete

        return self

    def add_bool_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a boolean option to a slash command.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            name, description, hikari.OptionType.BOOLEAN, default=default, key=key, pass_as_kwarg=pass_as_kwarg
        )

    def add_user_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a user option to a slash command.

        !!! note
            This may result in [hikari.interactions.base_interactions.InteractionMember][]
            or [hikari.users.User][] if the user isn't in the current guild or if this
            command was executed in a DM channel.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            name, description, hikari.OptionType.USER, default=default, key=key, pass_as_kwarg=pass_as_kwarg
        )

    def add_member_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
    ) -> _SlashCommandT:
        r"""Add a member option to a slash command.

        !!! note
            This will always result in
            [hikari.interactions.base_interactions.InteractionMember][].

        !!! warning
            Unlike the other options, this is an artificial option which adds
            a restraint to the USER option type and therefore cannot have
            `pass_as_kwarg` set to [False][] as this artificial constraint isn't
            present when its not being passed as a keyword argument.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(name, description, hikari.OptionType.USER, default=default, key=key, only_member=True)

    def add_channel_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        types: typing.Optional[collections.Collection[typing.Union[type[hikari.PartialChannel], int]]] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a channel option to a slash command.

        !!! note
            This will always result in
            [hikari.interactions.command_interactions.InteractionChannel][].

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        types
            A collection of the channel classes and types this option should accept.

            If left as [None][] or empty then the option will allow all channel types.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        if types:
            try:
                types_iter = itertools.chain.from_iterable(
                    (type_,) if isinstance(type_, int) else _CHANNEL_TYPES[type_] for type_ in types
                )
                channel_types = list(set(types_iter))

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
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_role_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a role option to a slash command.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            name, description, hikari.OptionType.ROLE, default=default, key=key, pass_as_kwarg=pass_as_kwarg
        )

    def add_mentionable_option(
        self: _SlashCommandT,
        name: str,
        description: str,
        /,
        *,
        default: typing.Any = UNDEFINED_DEFAULT,
        key: typing.Optional[str] = None,
        pass_as_kwarg: bool = True,
    ) -> _SlashCommandT:
        r"""Add a mentionable option to a slash command.

        !!! note
            This may target roles, guild members or users and results in
            `hikari.User | hikari.InteractionMember | hikari.Role`.

        Parameters
        ----------
        name
            The option's name.

            This must match the regex `^[\w-]{1,32}` in Unicode mode and be lowercase.
        description
            The option's description.

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as undefined then this option will be required.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used.

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
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            name, description, hikari.OptionType.MENTIONABLE, default=default, key=key, pass_as_kwarg=pass_as_kwarg
        )

    def set_float_autocomplete(
        self: _SlashCommandT, name: str, callback: typing.Optional[tanjun.AutocompleteCallbackSig], /
    ) -> _SlashCommandT:
        """Set the autocomplete callback for a float option.

        Parameters
        ----------
        name
            The option's name.
        callback
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [float][].

            Passing [None][] here will remove the autocomplete callback for the
            option.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `float`.
        """
        option = self._builder.get_option(name)

        if not option:
            raise KeyError("Option not found")

        if option.type is not hikari.OptionType.FLOAT:
            raise TypeError("Option is not a float option")

        if callback:
            option.autocomplete = True
            self._float_autocompletes[name] = callback

        elif name in self._float_autocompletes:
            option.autocomplete = False
            del self._float_autocompletes[name]

        return self

    def with_float_autocomplete(
        self, name: str, /
    ) -> collections.Callable[[_AutocompleteCallbackSigT], _AutocompleteCallbackSigT]:
        """Set the autocomplete callback for a float option through a decorator call.

        Parameters
        ----------
        name
            The option's name.

        Returns
        -------
        Collections.abc.Callable[[tanjun.abc.AutocompleteCallbackSig], tanjun.abc.AutocompleteCallbackSig]
            Decorator callback used to capture the autocomplete callback.

            More information on the autocomplete signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [float][].

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `float`.
        """

        def decorator(callback: _AutocompleteCallbackSigT, /) -> _AutocompleteCallbackSigT:
            self.set_float_autocomplete(name, callback)
            return callback

        return decorator

    def set_int_autocomplete(
        self: _SlashCommandT, name: str, callback: tanjun.AutocompleteCallbackSig, /
    ) -> _SlashCommandT:
        """Set the autocomplete callback for a string option.

        Parameters
        ----------
        name
            The option's name.
        callback
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [str][].

            Passing [None][] here will remove the autocomplete callback for the
            option.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `str`.
        """
        option = self._builder.get_option(name)

        if not option:
            raise KeyError("Option not found")

        if option.type is not hikari.OptionType.INTEGER:
            raise TypeError("Option is not a int option")

        option.autocomplete = True
        self._int_autocompletes[name] = callback
        return self

    def with_int_autocomplete(
        self, name: str, /
    ) -> collections.Callable[[_AutocompleteCallbackSigT], _AutocompleteCallbackSigT]:
        """Set the autocomplete callback for a integer option through a decorator call.

        Parameters
        ----------
        name
            The option's name.

        Returns
        -------
        Collections.abc.Callable[[tanjun.abc.AutocompleteCallbackSig], tanjun.abc.AutocompleteCallbackSig]
            Decorator callback used to capture the autocomplete callback.

            More information on the autocomplete signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [int][].

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `int`.
        """

        def decorator(callback: _AutocompleteCallbackSigT, /) -> _AutocompleteCallbackSigT:
            self.set_int_autocomplete(name, callback)
            return callback

        return decorator

    def set_str_autocomplete(
        self: _SlashCommandT, name: str, callback: tanjun.AutocompleteCallbackSig, /
    ) -> _SlashCommandT:
        """Set the autocomplete callback for a str option.

        Parameters
        ----------
        name
            The option's name.
        callback
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [str][].

            Passing [None][] here will remove the autocomplete callback for the
            option.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `str`.
        """
        option = self._builder.get_option(name)

        if not option:
            raise KeyError("Option not found")

        if option.type is not hikari.OptionType.STRING:
            raise TypeError("Option is not a str option")

        option.autocomplete = True
        self._str_autocompletes[name] = callback
        return self

    def with_str_autocomplete(
        self, name: str, /
    ) -> collections.Callable[[_AutocompleteCallbackSigT], _AutocompleteCallbackSigT]:
        """Set the autocomplete callback for a string option through a decorator call.

        Parameters
        ----------
        name
            The option's name.

        Returns
        -------
        Collections.abc.Callable[[tanjun.abc.AutocompleteCallbackSig], tanjun.abc.AutocompleteCallbackSig]
            Decorator callback used to capture the autocomplete callback.

            More information on the autocomplete signature can be found at
            [tanjun.abc.AutocompleteCallbackSig][] and the 2nd positional
            argument should be of type [str][].

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `str`.
        """

        def decorator(callback: _AutocompleteCallbackSigT, /) -> _AutocompleteCallbackSigT:
            self.set_str_autocomplete(name, callback)
            return callback

        return decorator

    async def _process_args(self, ctx: tanjun.SlashContext, /) -> collections.Mapping[str, typing.Any]:
        keyword_args: dict[
            str, typing.Union[int, float, str, hikari.Attachment, hikari.User, hikari.Role, hikari.InteractionChannel]
        ] = {}
        for tracked_option in self._tracked_options.values():
            if not (option := ctx.options.get(tracked_option.name)):
                if tracked_option.default is UNDEFINED_DEFAULT:
                    raise RuntimeError(  # TODO: ConversionError?
                        f"Required option {tracked_option.name} is missing data, are you sure your commands"
                        " are up to date?"
                    )

                else:
                    keyword_args[tracked_option.key] = tracked_option.default

            elif option.type is hikari.OptionType.USER:
                member: typing.Optional[hikari.InteractionMember] = None
                if tracked_option.is_only_member and not (member := option.resolve_to_member(default=None)):
                    raise errors.ConversionError(
                        f"Couldn't find member for provided user: {option.value}", tracked_option.name
                    )

                keyword_args[tracked_option.key] = member or option.resolve_to_user()

            elif option.type is hikari.OptionType.CHANNEL:
                keyword_args[tracked_option.key] = option.resolve_to_channel()

            elif option.type is hikari.OptionType.ROLE:
                keyword_args[tracked_option.key] = option.resolve_to_role()

            elif option.type is hikari.OptionType.MENTIONABLE:
                keyword_args[tracked_option.key] = option.resolve_to_mentionable()

            elif option.type is hikari.OptionType.ATTACHMENT:
                keyword_args[tracked_option.key] = option.resolve_to_attachment()

            else:
                value = option.value
                # To be type safe we obfuscate the fact that discord's double type will provide an int or float
                # depending on the value Discord inputs by always casting to float.
                if tracked_option.type is hikari.OptionType.FLOAT and tracked_option.is_always_float:
                    value = float(value)

                if tracked_option.converters:
                    value = await tracked_option.convert(ctx, option.value)

                keyword_args[tracked_option.key] = value

        return keyword_args

    async def execute(
        self,
        ctx: tanjun.SlashContext,
        /,
        option: typing.Optional[hikari.CommandInteractionOption] = None,
        *,
        hooks: typing.Optional[collections.MutableSet[tanjun.SlashHooks]] = None,
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

            await ctx.call_with_async_di(self._callback, ctx, **kwargs)

        except errors.CommandError as exc:
            await exc.send(ctx)

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

    async def execute_autocomplete(
        self,
        ctx: tanjun.AutocompleteContext,
        /,
        option: typing.Optional[hikari.AutocompleteInteractionOption] = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        if ctx.focused.type is hikari.OptionType.STRING:
            callback = self._str_autocompletes.get(ctx.focused.name)

        elif ctx.focused.type is hikari.OptionType.FLOAT:
            callback = self._float_autocompletes.get(ctx.focused.name)

        elif ctx.focused.type is hikari.OptionType.INTEGER:
            callback = self._int_autocompletes.get(ctx.focused.name)

        else:
            raise NotImplementedError(f"Autocomplete isn't implemented for '{ctx.focused.type}' option yet.")

        if not callback:
            raise RuntimeError(f"No autocomplete callback found for '{ctx.focused.name}' option")

        await ctx.call_with_async_di(callback, ctx, ctx.focused.value)

    def copy(self: _SlashCommandT, *, parent: typing.Optional[tanjun.SlashCommandGroup] = None) -> _SlashCommandT:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy(parent=parent)
        inst._callback = copy.copy(self._callback)
        return inst
