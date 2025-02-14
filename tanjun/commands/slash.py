# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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
import typing
import unicodedata
import warnings
from collections import abc as collections

import hikari
import typing_extensions

from tanjun import _internal
from tanjun import abc as tanjun
from tanjun import components
from tanjun import conversion
from tanjun import errors
from tanjun import hooks as hooks_
from tanjun._internal import localisation

from . import base

if typing.TYPE_CHECKING:
    from typing import Self

    from hikari.api import special_endpoints as special_endpoints_api

    _AnyCallbackSigT = typing.TypeVar("_AnyCallbackSigT", bound=collections.Callable[..., typing.Any])
    _AnyBaseSlashCommandT = typing.TypeVar("_AnyBaseSlashCommandT", bound=tanjun.BaseSlashCommand)
    _SlashCommandT = typing.TypeVar("_SlashCommandT", bound="SlashCommand[typing.Any]")
    _AnyCommandT = (
        tanjun.MenuCommand[_AnyCallbackSigT, typing.Any]
        | tanjun.MessageCommand[_AnyCallbackSigT]
        | tanjun.SlashCommand[_AnyCallbackSigT]
    )

    # Pyright bug doesn't accept Var = Class | Class as a type
    _AnyConverterSig = typing.Union["ConverterSig[float]", "ConverterSig[int]", "ConverterSig[str]"]  # noqa: UP007
    # Pyright bug doesn't accept Var = Class | Class as a type
    _CallbackishT = typing.Union["_SlashCallbackSigT", _AnyCommandT["_SlashCallbackSigT"]]  # noqa: UP007

    _IntAutocompleteSigT = typing.TypeVar("_IntAutocompleteSigT", bound=tanjun.AutocompleteSig[int])
    _FloatAutocompleteSigT = typing.TypeVar("_FloatAutocompleteSigT", bound=tanjun.AutocompleteSig[float])
    _StrAutocompleteSigT = typing.TypeVar("_StrAutocompleteSigT", bound=tanjun.AutocompleteSig[str])


_SlashCallbackSigT = typing.TypeVar("_SlashCallbackSigT", bound=tanjun.SlashCallbackSig)
_ConvertT = typing.TypeVar("_ConvertT", int, float, str)


ConverterSig = collections.Callable[
    typing.Concatenate[_ConvertT, ...], collections.Coroutine[typing.Any, typing.Any, typing.Any] | typing.Any
]
"""Type hint of a slash command option converter.

This represents the signatures `def (int | float | str, ...) -> Any` and
`async def (int | float | str, ...) -> None` where dependency injection is
supported.
"""


_EMPTY_DICT: typing.Final[dict[typing.Any, typing.Any]] = {}
_EMPTY_HOOKS: typing.Final[hooks_.Hooks[typing.Any]] = hooks_.Hooks()

_SCOMMAND_NAME_REG: typing.Final[str] = r"^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$"
_VALID_NAME_UNICODE_CATEGORIES = frozenset(
    (
        # L
        "Lu",
        "Ll",
        "Lt",
        "Lm",
        "Lo",
        # N
        "Nd",
        "Nl",
        "No",
    )
)
_VALID_NAME_CHARACTERS = frozenset(("-", "_"))
_MAX_OPTIONS = 25

_DEVI_FIRST_CHAR = 0x0900
_DEVI_LAST_CHAR = 0x097F
_THAI_FIRST_CHAR = 0x0E00
_THAI_LAST_CHAR = 0x0E7F


def _check_name_char(character: str, /) -> bool:
    # `^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$`
    # * `-_`` is just `-` and `_`
    # * L (all letter characters so "Lu", "Ll", "Lt", "Lm" and "Lo")
    # * N (all numeric characters so "Nd", "Nl" and "No")
    # * Deva: `\u0900-\u097F`  # TODO: Deva extended?
    # * Thai: `\u0E00-\u0E7F`

    return (
        character in _VALID_NAME_CHARACTERS
        or unicodedata.category(character) in _VALID_NAME_UNICODE_CATEGORIES
        or _DEVI_FIRST_CHAR >= (code_point := ord(character)) <= _DEVI_LAST_CHAR
        or _THAI_FIRST_CHAR >= code_point <= _THAI_LAST_CHAR
    )


def _validate_name(name: str, /) -> bool:
    return all(map(_check_name_char, name))


def slash_command_group(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default_member_permissions: hikari.Permissions | int | None = None,
    default_to_ephemeral: bool | None = None,
    dm_enabled: bool | None = None,
    nsfw: bool = False,
    is_global: bool = True,
) -> SlashCommandGroup:
    r"""Create a slash command group.

    !!! note
        Unlike message command groups, slash command groups cannot
        be callable functions themselves.

    !!! warning
        `default_member_permissions`, `dm_enabled` and `is_global` are
        ignored for command groups within other slash command groups.

    !!! note
        Under the standard implementation, `is_global` is used to
        determine whether the command should be bulk set by
        [Client.declare_global_commands][tanjun.abc.Client.declare_global_commands]
        or when `declare_global_commands` is True

    Examples
    --------
    Sub-commands can be added to the created slash command object through
    the following decorator based approach:

    ```python
    help_group = tanjun.slash_command_group("help", "get help")

    @tanjun.with_str_slash_option("command_name", "command name")
    @help_group.as_sub_command("command", "Get help with a command")
    async def help_command_command(ctx: tanjun.abc.SlashContext, command_name: str) -> None:
        ...

    @help_group.as_sub_command("me", "help me")
    async def help_me_command(ctx: tanjun.abc.SlashContext) -> None:
        ...

    component = tanjun.Component().add_slash_command(help_group)
    ```

    Parameters
    ----------
    name
        The name of the command group (supports [localisation][]).

        This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
    description
        The description of the command group (supports [localisation][]).

        This should be inclusively between 1-100 characters in length.
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
    nsfw
        Whether this command should only be accessible in channels marked as
        nsfw.

    Returns
    -------
    SlashCommandGroup
        The command group.

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:

        * If the command name doesn't fit Discord's requirements.
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
        nsfw=nsfw,
    )


# While these overloads may seem redundant/unnecessary, MyPy cannot understand
# this when expressed through `callback: _CallbackIshT[_SlashCallbackSigT]`.
class _AsSlashResultProto(typing.Protocol):
    @typing.overload
    def __call__(self, _: _SlashCallbackSigT, /) -> SlashCommand[_SlashCallbackSigT]: ...

    @typing.overload
    def __call__(self, _: _AnyCommandT[_SlashCallbackSigT], /) -> SlashCommand[_SlashCallbackSigT]: ...


def as_slash_command(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    always_defer: bool = False,
    default_member_permissions: hikari.Permissions | int | None = None,
    default_to_ephemeral: bool | None = None,
    dm_enabled: bool | None = None,
    is_global: bool = True,
    nsfw: bool = False,
    sort_options: bool = True,
    validate_arg_keys: bool = True,
) -> _AsSlashResultProto:
    r"""Build a [SlashCommand][tanjun.SlashCommand] by decorating a function.

    !!! note
        Under the standard implementation, `is_global` is used to
        determine whether the command should be bulk set by
        [Client.declare_global_commands][tanjun.abc.Client.declare_global_commands]
        or when `declare_global_commands` is True

    !!! warning
        `default_member_permissions`, `dm_enabled` and `is_global` are
        ignored for commands within slash command groups.

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
        The command's name (supports [localisation][]).

        This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
    description
        The command's description (supports [localisation][]).

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
    nsfw
        Whether this command should only be accessible in channels marked as
        nsfw.
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
    collections.abc.Callable[[tanjun.abc.SlashCallbackSig], SlashCommand]
        The decorator callback used to make a [SlashCommand][tanjun.SlashCommand].

        This can either wrap a raw command callback or another callable command
        instance (e.g. [tanjun.MenuCommand][], [tanjun.MessageCommand][],
        [SlashCommand][tanjun.SlashCommand]) and will manage loading the other
        command into a component when using
        [Component.load_from_scope][tanjun.components.Component.load_from_scope].

    Raises
    ------
    ValueError
        Raises a value error for any of the following reasons:

        * If the command name doesn't fit Discord's requirements.
        * If the command name has uppercase characters.
        * If the description is over 100 characters long.
    """

    def decorator(callback: _CallbackishT[_SlashCallbackSigT], /) -> SlashCommand[_SlashCallbackSigT]:
        if isinstance(callback, tanjun.MenuCommand | tanjun.MessageCommand | tanjun.SlashCommand):
            wrapped_command = callback
            # Cast needed cause of a pyright bug
            callback = typing.cast("_SlashCallbackSigT", callback.callback)

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
            nsfw=nsfw,
            sort_options=sort_options,
            validate_arg_keys=validate_arg_keys,
            _wrapped_command=wrapped_command,
        )

    return decorator


UNDEFINED_DEFAULT = tanjun.NO_DEFAULT
"""Deprecated alias for `tanjun.abc.NO_DEFAULT`."""


def with_attachment_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add an attachment option to a slash command.

    For more information on this function's parameters see
    [SlashCommand.add_attachment_option][tanjun.SlashCommand.add_attachment_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
        Decorator callback which adds the option to the command.
    """
    return lambda command: command.add_attachment_option(
        name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg
    )


def with_str_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    autocomplete: tanjun.AutocompleteSig[str] | None = None,
    choices: (
        collections.Mapping[str, str] | collections.Sequence[str] | collections.Sequence[hikari.CommandChoice] | None
    ) = None,
    converters: collections.Sequence[ConverterSig[str]] | ConverterSig[str] = (),
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a string option to a slash command.

    For more information on this function's parameters see
    [SlashCommand.add_str_option][tanjun.commands.SlashCommand.add_str_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
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
        min_length=min_length,
        max_length=max_length,
        pass_as_kwarg=pass_as_kwarg,
        _stack_level=1,
    )


def with_int_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    autocomplete: tanjun.AutocompleteSig[int] | None = None,
    choices: collections.Mapping[str, int] | collections.Sequence[hikari.CommandChoice] | None = None,
    converters: collections.Sequence[ConverterSig[int]] | ConverterSig[int] = (),
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add an integer option to a slash command.

    For information on this function's parameters see
    [SlashCommand.add_int_option][tanjun.SlashCommand.add_int_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
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
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    always_float: bool = True,
    autocomplete: tanjun.AutocompleteSig[float] | None = None,
    choices: collections.Mapping[str, float] | collections.Sequence[hikari.CommandChoice] | None = None,
    converters: collections.Sequence[ConverterSig[float]] | ConverterSig[float] = (),
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a float option to a slash command.

    For information on this function's parameters see
    [SlashCommand.add_float_option][tanjun.SlashCommand.add_float_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
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
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a boolean option to a slash command.

    For information on this function's parameters see
    [SlashCommand.add_bool_option][tanjun.SlashCommand.add_bool_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_bool_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


def with_user_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a user option to a slash command.

    For information on this function's parameters see
    [SlashCommand.add_user_option][tanjun.SlashCommand.add_user_option].

    !!! note
        This may result in
        [hikari.InteractionMember][hikari.interactions.base_interactions.InteractionMember]
        or [hikari.User][hikari.users.User] if the user isn't in the current
        guild or if this command was executed in a DM channel.

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_user_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


def with_member_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a member option to a slash command.

    For information on this function's arguments see
    [SlashCommand.add_member_option][tanjun.SlashCommand.add_member_option].

    !!! note
        This will always result in
        [hikari.InteractionMember][hikari.interactions.base_interactions.InteractionMember].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_member_option(name, description, default=default, key=key)


def with_channel_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    types: collections.Collection[type[hikari.PartialChannel] | int] | None = None,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a channel option to a slash command.

    For information on this function's parameters see
    [SlashCommand.add_channel_option][tanjun.SlashCommand.add_channel_option].

    !!! note
        This will always result in
        [hikari.InteractionChannel][hikari.interactions.base_interactions.InteractionChannel].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_channel_option(
        name, description, types=types, default=default, key=key, pass_as_kwarg=pass_as_kwarg
    )


def with_role_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a role option to a slash command.

    For information on this function's parameters see
    [SlashCommand.add_role_option][tanjun.SlashCommand.add_role_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
        Decorator callback which adds the option to the command.
    """
    return lambda c: c.add_role_option(name, description, default=default, key=key, pass_as_kwarg=pass_as_kwarg)


def with_mentionable_slash_option(
    name: str | collections.Mapping[str, str],
    description: str | collections.Mapping[str, str],
    /,
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    key: str | None = None,
    pass_as_kwarg: bool = True,
) -> collections.Callable[[_SlashCommandT], _SlashCommandT]:
    """Add a mentionable option to a slash command.

    For information on this function's arguments see
    [SlashCommand.add_mentionable_option][tanjun.SlashCommand.add_mentionable_option].

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
    collections.abc.Callable[[SlashCommand], SlashCommand]
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
        option_type: hikari.OptionType | int,
        always_float: bool = False,
        converters: list[_AnyConverterSig] | None = None,
        only_member: bool = False,
        default: typing.Any = tanjun.NO_DEFAULT,
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
            if isinstance(converter, conversion.BaseConverter):  # pyright: ignore[reportUnnecessaryIsInstance]
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

        error_message = f"Couldn't convert {self.type} '{self.name}'"
        raise errors.ConversionError(error_message, self.name, errors=exceptions)


class _SlashCommandBuilder(hikari.impl.SlashCommandBuilder):
    __slots__ = ("_has_been_sorted", "_options_dict", "_sort_options")

    def __init__(
        self,
        *,
        name: str,
        name_localizations: collections.Mapping[str, str],
        description: str,
        description_localizations: collections.Mapping[str, str],
        nsfw: hikari.UndefinedOr[bool],
        sort_options: bool,
        id_: hikari.UndefinedOr[hikari.Snowflake] = hikari.UNDEFINED,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            description_localizations=description_localizations,
            id=id_,
            name_localizations=name_localizations,
            is_nsfw=nsfw,
        )
        self._has_been_sorted = True
        self._options_dict: dict[str, hikari.CommandOption] = {}
        self._sort_options = sort_options

    def add_option(self, option: hikari.CommandOption) -> Self:
        if self._options:
            self._has_been_sorted = False

        super().add_option(option)
        self._options_dict[option.name] = option
        return self

    def get_option(self, name: str, /) -> hikari.CommandOption | None:
        return self._options_dict.get(name)

    def sort(self) -> Self:
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
    def copy(self) -> _SlashCommandBuilder:
        builder = _SlashCommandBuilder(
            name=self.name,
            name_localizations=self.name_localizations,
            description=self.description,
            description_localizations=self.description_localizations,
            nsfw=self.is_nsfw,
            sort_options=self._sort_options,
            id_=self.id,
        )

        for option in self.options:
            builder.add_option(copy.copy(option))

        return builder


class BaseSlashCommand(base.PartialCommand[tanjun.SlashContext], tanjun.BaseSlashCommand):
    """Base class used for the standard slash command implementations."""

    __slots__ = (
        "_default_member_permissions",
        "_defaults_to_ephemeral",
        "_descriptions",
        "_is_dm_enabled",
        "_is_global",
        "_is_nsfw",
        "_names",
        "_parent",
        "_tracked_command",
    )

    def __init__(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default_member_permissions: hikari.Permissions | int | None = None,
        default_to_ephemeral: bool | None = None,
        dm_enabled: bool | None = None,
        is_global: bool = True,
        nsfw: bool = False,
    ) -> None:
        super().__init__()
        names = (
            localisation.MaybeLocalised("name", name)
            .assert_length(1, 32)
            .assert_matches(_SCOMMAND_NAME_REG, _validate_name, lower_only=True)
        )
        descriptions = localisation.MaybeLocalised("description", description).assert_length(1, 100)

        if default_member_permissions is not None:
            default_member_permissions = hikari.Permissions(default_member_permissions)

        self._default_member_permissions = default_member_permissions
        self._defaults_to_ephemeral = default_to_ephemeral
        self._descriptions = descriptions
        self._is_dm_enabled = dm_enabled
        self._is_global = is_global
        self._is_nsfw = nsfw
        self._names = names
        self._parent: tanjun.SlashCommandGroup | None = None
        self._tracked_command: hikari.SlashCommand | None = None

    @property
    def default_member_permissions(self) -> hikari.Permissions | None:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._default_member_permissions

    @property
    def defaults_to_ephemeral(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._defaults_to_ephemeral

    @property
    def description(self) -> str:  # TODO: this feels like a mistake
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._descriptions.default_value

    @property
    def description_localisations(self) -> collections.Mapping[str, str]:
        return self._descriptions.localised_values.copy()

    @property
    def is_dm_enabled(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_dm_enabled

    @property
    def is_global(self) -> bool:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_global

    @property
    def is_nsfw(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_nsfw

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._names.default_value

    @property
    def name_localisations(self) -> collections.Mapping[str, str]:
        return self._names.localised_values.copy()

    @property
    def parent(self) -> tanjun.SlashCommandGroup | None:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        return self._parent

    @property
    def tracked_command(self) -> hikari.SlashCommand | None:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._tracked_command

    @property
    def tracked_command_id(self) -> hikari.Snowflake | None:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._tracked_command.id if self._tracked_command else None

    @property
    def type(self) -> typing.Literal[hikari.CommandType.SLASH]:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return hikari.CommandType.SLASH

    def set_tracked_command(self, command: hikari.PartialCommand, /) -> Self:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        if not isinstance(command, hikari.SlashCommand):
            error_message = "The tracked command must be a slash command"
            raise TypeError(error_message)

        self._tracked_command = command
        return self

    def set_ephemeral_default(self, state: bool | None, /) -> Self:
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

    def set_parent(self, parent: tanjun.SlashCommandGroup | None, /) -> Self:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        self._parent = parent
        return self

    async def check_context(self, ctx: tanjun.SlashContext, /) -> bool:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        ctx.set_command(self)
        result = await _internal.gather_checks(ctx, self._checks)
        ctx.set_command(None)
        return result

    def copy(self, *, parent: tanjun.SlashCommandGroup | None = None) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy()
        inst._parent = parent  # noqa: SLF001
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
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default_member_permissions: hikari.Permissions | int | None = None,
        default_to_ephemeral: bool | None = None,
        dm_enabled: bool | None = None,
        is_global: bool = True,
        nsfw: bool = False,
    ) -> None:
        r"""Initialise a slash command group.

        !!! note
            Under the standard implementation, `is_global` is used to
            determine whether the command should be bulk set by
            [Client.declare_global_commands][tanjun.abc.Client.declare_global_commands]
            or when `declare_global_commands` is True

        !!! warning
            `default_member_permissions`, `dm_enabled` and `is_global` are
            ignored for commands groups within another slash command groups.

        Parameters
        ----------
        name
            The name of the command group (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The description of the command group (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
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
        nsfw
            Whether this command should only be accessible in channels marked as
            nsfw.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the command name doesn't fit Discord's requirements.
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
            nsfw=nsfw,
        )
        self._commands: dict[str, tanjun.BaseSlashCommand] = {}

    @property
    def commands(self) -> collections.Collection[tanjun.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.SlashCommandGroup>>.
        return self._commands.copy().values()

    @property
    def is_nsfw(self) -> bool | None:
        # <<inherited docstring from tanjun.abc.AppCommand>>.
        return self._is_nsfw

    def bind_client(self, client: tanjun.Client, /) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_client(client)
        for command in self._commands.values():
            command.bind_client(client)

        return self

    def bind_component(self, component: tanjun.Component, /) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        super().bind_component(component)
        for command in self._commands.values():
            command.bind_component(component)

        return self

    def build(self, *, component: tanjun.Component | None = None) -> special_endpoints_api.SlashCommandBuilder:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        builder = _SlashCommandBuilder(
            name=self._names.default_value,
            name_localizations=self._names.localised_values,
            description=self._descriptions.default_value,
            description_localizations=self._descriptions.localised_values,
            nsfw=self._is_nsfw,
            sort_options=False,
        )

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
                    name_localizations=command_builder.name_localizations,
                    description=command_builder.description,
                    description_localizations=command_builder.description_localizations,
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

    def copy(self, *, parent: tanjun.SlashCommandGroup | None = None) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy(parent=parent)
        inst._commands = {name: command.copy(parent=inst) for name, command in self._commands.items()}  # noqa: SLF001
        return inst

    def add_command(self, command: tanjun.BaseSlashCommand, /) -> Self:
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
            error_message = "Cannot add a slash command group to a nested slash command group"
            raise ValueError(error_message)

        if len(self._commands) == _MAX_OPTIONS:
            error_message = f"Cannot add more than {_MAX_OPTIONS} commands to a slash command group"
            raise ValueError(error_message)

        if command.name in self._commands:
            error_message = f"Command with name {command.name!r} already exists in this group"
            raise ValueError(error_message)

        command.set_parent(self)
        self._commands[command.name] = command
        return self

    def as_sub_command(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_defer: bool = False,
        default_to_ephemeral: bool | None = None,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
    ) -> collections.Callable[[_CallbackishT[_SlashCallbackSigT]], SlashCommand[_SlashCallbackSigT]]:
        r"""Build a [SlashCommand][tanjun.SlashCommand] in this command group by decorating a function.

        !!! note
            If you want your first response to be ephemeral while using
            `always_defer`, you must set `default_to_ephemeral` to `True`.

        Parameters
        ----------
        name
            The command's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The command's description.
            This should be inclusively between 1-100 characters in length.
        always_defer
            Whether the contexts this command is executed with should always be deferred
            before being passed to the command's callback.
        default_to_ephemeral
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as [None][] then the default set on the parent command(s),
            component or client will be in effect.
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
        collections.abc.Callable[[tanjun.abc.SlashCallbackSig], SlashCommand]
            The decorator callback used to make a sub-command.

            This can either wrap a raw command callback or another callable command
            instance (e.g. [tanjun.MenuCommand][], [tanjun.MessageCommand][],
            [SlashCommand][tanjun.SlashCommand]).

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the command name doesn't fit Discord's requirements.
            * If the command name has uppercase characters.
            * If the description is over 100 characters long.
        """

        def decorator(callback: _CallbackishT[_SlashCallbackSigT], /) -> SlashCommand[_SlashCallbackSigT]:
            cmd = as_slash_command(
                name,
                description,
                always_defer=always_defer,
                default_to_ephemeral=default_to_ephemeral,
                sort_options=sort_options,
                validate_arg_keys=validate_arg_keys,
            )(callback)
            self.add_command(cmd)
            return cmd

        return decorator

    def make_sub_group(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default_to_ephemeral: bool | None = None,
    ) -> SlashCommandGroup:
        r"""Create a sub-command group in this group.

        !!! note
            Unlike message command groups, slash command groups cannot
            be callable functions themselves.

        Parameters
        ----------
        name
            The name of the command group (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The description of the command group.
        default_to_ephemeral
            Whether this command's responses should default to ephemeral unless flags
            are set to override this.

            If this is left as [None][] then the default set on the parent command(s),
            component or client will be in effect.

        Returns
        -------
        SlashCommandGroup
            The created sub-command group.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the command name doesn't fit Discord's requirements.
            * If the command name has uppercase characters.
            * If the description is over 100 characters long.
        """
        return self.with_command(slash_command_group(name, description, default_to_ephemeral=default_to_ephemeral))

    def remove_command(self, command: tanjun.BaseSlashCommand, /) -> Self:
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

    def with_command(self, command: _AnyBaseSlashCommandT, /) -> _AnyBaseSlashCommandT:
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
        *,
        option: hikari.CommandInteractionOption | None = None,
        hooks: collections.MutableSet[tanjun.SlashHooks] | None = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        if not option and ctx.interaction.options:
            option = ctx.interaction.options[0]

        elif option and option.options:
            option = option.options[0]

        else:
            error_message = "Missing sub-command option"
            raise RuntimeError(error_message)

        if command := self._commands.get(option.name):
            if command.defaults_to_ephemeral is not None:
                ctx.set_ephemeral_default(command.defaults_to_ephemeral)

            if await command.check_context(ctx):
                await command.execute(ctx, option=option, hooks=hooks)
                return

        await ctx.mark_not_found()

    async def execute_autocomplete(
        self, ctx: tanjun.AutocompleteContext, /, *, option: hikari.AutocompleteInteractionOption | None = None
    ) -> None:
        if not option and ctx.interaction.options:
            option = ctx.interaction.options[0]

        elif option and option.options:
            option = option.options[0]

        else:
            error_message = "Missing sub-command option"
            raise RuntimeError(error_message)

        command = self._commands.get(option.name)
        if not command:
            error_message = f"Sub-command '{option.name}' no found"
            raise RuntimeError(error_message)

        await command.execute_autocomplete(ctx, option=option)


def _assert_in_range(name: str, value: int | None, min_value: int, max_value: int, /) -> None:
    if value is None:
        return

    if value < min_value:
        error_message = f"`{name}` must be greater than or equal to {min_value}"
        raise ValueError(error_message)

    if value > max_value:
        error_message = f"`{name}` must be less than or equal to {max_value}"
        raise ValueError(error_message)


class SlashCommand(BaseSlashCommand, tanjun.SlashCommand[_SlashCallbackSigT]):
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

    # While these overloads may seem redundant/unnecessary, MyPy cannot understand
    # this when expressed through `callback: _CallbackIshT[_SlashCallbackSigT]`.
    @typing.overload
    def __init__(
        self,
        callback: _SlashCallbackSigT,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: hikari.Permissions | int | None = None,
        default_to_ephemeral: bool | None = None,
        dm_enabled: bool | None = None,
        is_global: bool = True,
        nsfw: bool = False,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
        _wrapped_command: tanjun.ExecutableCommand[typing.Any] | None = None,
    ) -> None: ...

    @typing.overload
    def __init__(
        self,
        callback: _AnyCommandT[_SlashCallbackSigT],
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: hikari.Permissions | int | None = None,
        default_to_ephemeral: bool | None = None,
        dm_enabled: bool | None = None,
        is_global: bool = True,
        nsfw: bool = False,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
        _wrapped_command: tanjun.ExecutableCommand[typing.Any] | None = None,
    ) -> None: ...

    def __init__(
        self,
        callback: _CallbackishT[_SlashCallbackSigT],
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_defer: bool = False,
        default_member_permissions: hikari.Permissions | int | None = None,
        default_to_ephemeral: bool | None = None,
        dm_enabled: bool | None = None,
        is_global: bool = True,
        nsfw: bool = False,
        sort_options: bool = True,
        validate_arg_keys: bool = True,
        _wrapped_command: tanjun.ExecutableCommand[typing.Any] | None = None,
    ) -> None:
        r"""Initialise a slash command.

        !!! note
            Under the standard implementation, `is_global` is used to
            determine whether the command should be bulk set by
            [Client.declare_global_commands][tanjun.abc.Client.declare_global_commands]
            or when `declare_global_commands` is True

        !!! warning
            `default_member_permissions`, `dm_enabled` and `is_global` are
            ignored for commands within slash command groups.

        !!! note
            If you want your first response to be ephemeral while using
            `always_defer`, you must set `default_to_ephemeral` to `True`.

        Parameters
        ----------
        callback : tanjun.abc.SlashCallbackSig
            Callback to execute when the command is invoked.

            This should be an asynchronous callback which takes one positional
            argument of type [tanjun.abc.SlashContext][], returns `None` and may use
            dependency injection to access other services.
        name
            The command's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The command's description (supports [localisation][]).

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
        nsfw
            Whether this command should only be accessible in channels marked as
            nsfw.
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

            * If the command name doesn't fit Discord's requirements.
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
            nsfw=nsfw,
        )
        if isinstance(callback, tanjun.MenuCommand | tanjun.MessageCommand | tanjun.SlashCommand):
            # Cast needed cause of a pyright bug
            callback = typing.cast("_SlashCallbackSigT", callback.callback)

        self._always_defer = always_defer
        self._arg_names = _internal.get_kwargs(callback) if validate_arg_keys else None
        self._builder = _SlashCommandBuilder(
            name=self.name,
            name_localizations=self.name_localisations,
            description=self.description,
            description_localizations=self.description_localisations,
            nsfw=nsfw,
            sort_options=sort_options,
        )
        self._callback: _SlashCallbackSigT = callback
        self._client: tanjun.Client | None = None
        self._float_autocompletes: dict[str, tanjun.AutocompleteSig[float]] = {}
        self._int_autocompletes: dict[str, tanjun.AutocompleteSig[int]] = {}
        self._str_autocompletes: dict[str, tanjun.AutocompleteSig[str]] = {}
        self._tracked_options: dict[str, _TrackedOption] = {}
        self._wrapped_command = _wrapped_command

    if typing.TYPE_CHECKING:
        __call__: _SlashCallbackSigT

    else:

        async def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            await self._callback(*args, **kwargs)

    @property
    def callback(self) -> _SlashCallbackSigT:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._callback

    @property
    def float_autocompletes(self) -> collections.Mapping[str, tanjun.AutocompleteSig[float]]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._float_autocompletes.copy()

    @property
    def int_autocompletes(self) -> collections.Mapping[str, tanjun.AutocompleteSig[int]]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._int_autocompletes.copy()

    @property
    def str_autocompletes(self) -> collections.Mapping[str, tanjun.AutocompleteSig[str]]:
        # <<inherited docstring from tanjun.abc.SlashCommand>>.
        return self._str_autocompletes.copy()

    @property
    def wrapped_command(self) -> tanjun.ExecutableCommand[typing.Any] | None:
        """The command object this wraps, if any."""
        return self._wrapped_command

    def bind_client(self, client: tanjun.Client, /) -> Self:
        self._client = client
        super().bind_client(client)
        for option in self._tracked_options.values():
            option.check_client(client)

        return self

    def build(self, *, component: tanjun.Component | None = None) -> special_endpoints_api.SlashCommandBuilder:
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
        self,
        names: localisation.MaybeLocalised,
        descriptions: localisation.MaybeLocalised,
        type_: hikari.OptionType | int = hikari.OptionType.STRING,
        /,
        *,
        always_float: bool = False,
        autocomplete: bool = False,
        channel_types: collections.Sequence[int] | None = None,
        choices: (
            collections.Mapping[str, str | int | float]
            | collections.Sequence[tuple[str, str | int | float]]
            | collections.Sequence[hikari.CommandChoice]
            | None
        ) = None,
        converters: collections.Sequence[_AnyConverterSig] | _AnyConverterSig = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: int | float | None = None,
        max_value: int | float | None = None,
        only_member: bool = False,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self:
        names.assert_length(1, 32).assert_matches(_SCOMMAND_NAME_REG, _validate_name, lower_only=True)
        descriptions.assert_length(1, 100)

        if len(self._builder.options) == _MAX_OPTIONS:
            error_message = f"Slash commands cannot have more than {_MAX_OPTIONS} options"
            raise ValueError(error_message)

        if min_value is not None and max_value is not None and min_value > max_value:
            error_message = "`min_value` cannot be greater than `max_value`"
            raise ValueError(error_message)

        if min_length is not None and max_length is not None and min_length > max_length:
            error_message = "`min_length` cannot be greater than `max_length`"
            raise ValueError(error_message)

        _assert_in_range("min_length", min_length, 0, 6000)
        _assert_in_range("max_length", max_length, 1, 6000)

        key = key or names.default_value
        if self._arg_names is not None and key not in self._arg_names:
            error_message = f"{key!r} is not a valid keyword argument for {self._callback}"
            raise ValueError(error_message)

        type_ = hikari.OptionType(type_)
        if isinstance(converters, collections.Sequence):
            converters = list(converters)

        else:
            converters = [converters]

        if self._client:
            for converter in converters:
                if isinstance(converter, conversion.BaseConverter):  # pyright: ignore[reportUnnecessaryIsInstance]
                    converter.check_client(
                        self._client, f"{self._names.default_value}'s slash option '{names.default_value}'"
                    )

        if choices is None:
            actual_choices: list[hikari.CommandChoice] | None = None

        elif isinstance(choices, collections.Mapping):
            actual_choices = [hikari.CommandChoice(name=name, value=value) for name, value in choices.items()]

        else:
            actual_choices = []
            warned = False
            for choice in choices:
                if isinstance(choice, tuple):
                    if not warned:
                        warned = True
                        warnings.warn(
                            "Passing a sequence of tuples to `choices` is deprecated since 2.1.2a1, "
                            "please pass a mapping instead.",
                            category=DeprecationWarning,
                            stacklevel=2 + _stack_level,
                        )

                    actual_choices.append(hikari.CommandChoice(name=choice[0], value=choice[1]))

                else:
                    actual_choices.append(choice)

        if actual_choices and len(actual_choices) > _MAX_OPTIONS:
            error_message = f"Slash command options cannot have more than {_MAX_OPTIONS} choices"
            raise ValueError(error_message)

        required = default is tanjun.NO_DEFAULT
        self._builder.add_option(
            hikari.CommandOption(
                type=type_,
                name=names.default_value,
                name_localizations=names.localised_values,
                description=descriptions.default_value,
                description_localizations=descriptions.localised_values,
                is_required=required,
                choices=actual_choices,
                channel_types=channel_types,
                min_length=min_length,
                max_length=max_length,
                max_value=max_value,
                min_value=min_value,
                autocomplete=autocomplete,
            )
        )
        if pass_as_kwarg:
            self._tracked_options[names.default_value] = _TrackedOption(
                name=names.default_value,
                option_type=type_,
                always_float=always_float,
                converters=converters,
                default=default,
                key=key,
                only_member=only_member,
            )
        return self

    def add_attachment_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        pass_as_kwarg: bool = True,
    ) -> Self:
        r"""Add an attachment option to the slash command.

        !!! note
            This will result in options of type
            [hikari.Attachment][hikari.messages.Attachment].

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used and the
            `converters` field will be ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.ATTACHMENT,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    @typing.overload
    def add_str_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        autocomplete: tanjun.AutocompleteSig[str] | None = None,
        choices: (
            collections.Mapping[str, str]
            | collections.Sequence[str]
            | collections.Sequence[hikari.CommandChoice]
            | None
        ) = None,
        converters: collections.Sequence[ConverterSig[str]] | ConverterSig[str] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self: ...

    @typing.overload
    @typing_extensions.deprecated("Pass a dict for `choices`, not a sequence of tuples")
    def add_str_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        autocomplete: tanjun.AutocompleteSig[str] | None = None,
        choices: collections.Sequence[tuple[str, str]],
        converters: collections.Sequence[ConverterSig[str]] | ConverterSig[str] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self: ...

    def add_str_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        autocomplete: tanjun.AutocompleteSig[str] | None = None,
        choices: (
            collections.Mapping[str, str]
            | collections.Sequence[str]
            | collections.Sequence[tuple[str, str]]
            | collections.Sequence[hikari.CommandChoice]
            | None
        ) = None,
        converters: collections.Sequence[ConverterSig[str]] | ConverterSig[str] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self:
        r"""Add a string option to the slash command.

        !!! note
            As a shorthand, `choices` also supports passing a list of strings
            rather than a dict of names to values (each string will used as
            both the choice's name and value with the names being capitalised).

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        autocomplete
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [str][].
        choices : collections.abc.Mapping[str, str], collections.abc.Sequence[str] | None
            The option's choices.

            This either a mapping of [option_name, option_value] where both option_name
            and option_value should be strings of up to 100 characters or a sequence
            of strings where the string will be used for both the choice's name and
            value.

            Passing a sequence of tuples here is deprecated.
        converters
            The option's converters.

            This may be either one or multiple converter callbacks used to
            convert the option's value to the final form.
            If no converters are provided then the raw value will be passed.

            Only the first converter to pass will be used.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
        key
            Name of the argument this option's value should be passed to.

            This defaults to the first name provided in `name` and is no-op
            if `pass_as_kwarg` is [False][].
        min_length
            The minimum length of this string.

            This must be greater than or equal to 0, and less than or equal
            to `max_length` and `6000`.
        max_length
            The maximum length of this string.

            This must be greater then or equal to `min_length` and 1, and
            less than or equal to `6000`.
        pass_as_kwarg
            Whether or not to pass this option as a keyword argument to the
            command callback.

            If [False][] is passed here then `default` will only decide whether
            the option is required without the actual value being used and the
            `converters` field will be ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
            * If `min_length` is greater than `max_length`.
            * If `min_length` is less than `0` or greater than `6000`.
            * If `max_length` is less than `1` or greater than `6000`.
        """
        if choices is None or isinstance(choices, collections.Mapping):
            actual_choices: collections.Mapping[str, str] | list[hikari.CommandChoice] | None = choices

        else:
            actual_choices = []
            warned = False
            for choice in choices:
                if isinstance(choice, tuple):
                    if not warned:
                        warnings.warn(
                            "Passing a sequence of tuples for 'choices' is deprecated since 2.1.2a1, "
                            "please pass a mapping instead.",
                            category=DeprecationWarning,
                            stacklevel=2 + _stack_level,
                        )
                        warned = True

                    actual_choices.append(hikari.CommandChoice(name=choice[0], value=choice[1]))

                elif isinstance(choice, hikari.CommandChoice):
                    actual_choices.append(choice)

                else:
                    actual_choices.append(hikari.CommandChoice(name=choice.capitalize(), value=choice))

        names = localisation.MaybeLocalised("name", name)
        descriptions = localisation.MaybeLocalised("description", description)
        self._add_option(
            names,
            descriptions,
            hikari.OptionType.STRING,
            autocomplete=autocomplete is not None,
            choices=actual_choices,
            converters=converters,
            default=default,
            key=key,
            min_length=min_length,
            max_length=max_length,
            pass_as_kwarg=pass_as_kwarg,
        )

        if autocomplete:
            self._str_autocompletes[names.default_value] = autocomplete

        return self

    @typing.overload
    def add_int_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        autocomplete: tanjun.AutocompleteSig[int] | None = None,
        choices: collections.Mapping[str, int] | collections.Sequence[hikari.CommandChoice] | None = None,
        converters: collections.Sequence[ConverterSig[int]] | ConverterSig[int] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self: ...

    @typing.overload
    @typing_extensions.deprecated("Pass a dict for choices, not a sequence of tuples")
    def add_int_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        autocomplete: tanjun.AutocompleteSig[int] | None = None,
        choices: collections.Sequence[tuple[str, int]],
        converters: collections.Sequence[ConverterSig[int]] | ConverterSig[int] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self: ...

    def add_int_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        autocomplete: tanjun.AutocompleteSig[int] | None = None,
        choices: (
            collections.Mapping[str, int]
            | collections.Sequence[tuple[str, int]]
            | collections.Sequence[hikari.CommandChoice]
            | None
        ) = None,
        converters: collections.Sequence[ConverterSig[int]] | ConverterSig[int] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self:
        r"""Add an integer option to the slash command.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        autocomplete
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [int][].
        choices : collections.abc.Mapping[str, int] | None
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

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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
            `converters` field will be ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
            * If `min_value` is greater than `max_value`.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        names = localisation.MaybeLocalised("name", name)
        descriptions = localisation.MaybeLocalised("description", description)
        self._add_option(
            names,
            descriptions,
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
            self._int_autocompletes[names.default_value] = autocomplete

        return self

    @typing.overload
    def add_float_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_float: bool = True,
        autocomplete: tanjun.AutocompleteSig[float] | None = None,
        choices: collections.Mapping[str, float] | collections.Sequence[hikari.CommandChoice] | None = None,
        converters: collections.Sequence[ConverterSig[float]] | ConverterSig[float] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self: ...

    @typing.overload
    @typing_extensions.deprecated("Pass a dict for choices, not a sequence of tuples")
    def add_float_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_float: bool = True,
        autocomplete: tanjun.AutocompleteSig[float] | None = None,
        choices: collections.Sequence[tuple[str, float]],
        converters: collections.Sequence[ConverterSig[float]] | ConverterSig[float] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self: ...

    def add_float_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        always_float: bool = True,
        autocomplete: tanjun.AutocompleteSig[float] | None = None,
        choices: (
            collections.Mapping[str, float]
            | collections.Sequence[tuple[str, float]]
            | collections.Sequence[hikari.CommandChoice]
            | None
        ) = None,
        converters: collections.Sequence[ConverterSig[float]] | ConverterSig[float] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        pass_as_kwarg: bool = True,
        _stack_level: int = 0,
    ) -> Self:
        r"""Add a float option to a slash command.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        always_float
            If this is set to [True][] then the value will always be converted to a
            float (this will happen before it's passed to converters).

            This masks behaviour from Discord where we will either be provided a [float][]
            or [int][] dependent on what the user provided.
        autocomplete
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [float][].
        choices : collections.abc.Mapping[str, float] | None
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

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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
            fields `converters`, and `always_float` will be ignored.

        Returns
        -------
        Self
            The command object for chaining.

        Raises
        ------
        ValueError
            Raises a value error for any of the following reasons:

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
            * If `min_value` is greater than `max_value`.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        names = localisation.MaybeLocalised("name", name)
        descriptions = localisation.MaybeLocalised("description", description)
        self._add_option(
            names,
            descriptions,
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
            self._float_autocompletes[names.default_value] = autocomplete

        return self

    def add_bool_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        pass_as_kwarg: bool = True,
    ) -> Self:
        r"""Add a boolean option to a slash command.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.BOOLEAN,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_user_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        pass_as_kwarg: bool = True,
    ) -> Self:
        r"""Add a user option to a slash command.

        !!! note
            This may result in
            [hikari.InteractionMember][hikari.interactions.base_interactions.InteractionMember]
            or [hikari.User][hikari.users.User] if the user isn't in the
            current guild or if this command was executed in a DM channel.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the option has more than 25 choices.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.USER,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_member_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
    ) -> Self:
        r"""Add a member option to a slash command.

        !!! note
            This will always result in
            [hikari.InteractionMember][hikari.interactions.base_interactions.InteractionMember].

        !!! warning
            Unlike the other options, this is an artificial option which adds
            a restraint to the USER option type and therefore cannot have
            `pass_as_kwarg` set to [False][] as this artificial constraint isn't
            present when its not being passed as a keyword argument.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.USER,
            default=default,
            key=key,
            only_member=True,
        )

    def add_channel_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        types: collections.Collection[type[hikari.PartialChannel] | int] | None = None,
        pass_as_kwarg: bool = True,
    ) -> Self:
        r"""Add a channel option to a slash command.

        !!! note
            This will always result in
            [hikari.InteractionChannel][hikari.interactions.base_interactions.InteractionChannel].

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If an invalid type is passed in `types`.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.CHANNEL,
            channel_types=_internal.parse_channel_types(*types) if types else None,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_role_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        pass_as_kwarg: bool = True,
    ) -> Self:
        r"""Add a role option to a slash command.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.ROLE,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def add_mentionable_option(
        self,
        name: str | collections.Mapping[str, str],
        description: str | collections.Mapping[str, str],
        /,
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        key: str | None = None,
        pass_as_kwarg: bool = True,
    ) -> Self:
        r"""Add a mentionable option to a slash command.

        !!! note
            This may target roles, guild members or users and results in
            `hikari.User | hikari.InteractionMember | hikari.Role`.

        Parameters
        ----------
        name
            The option's name (supports [localisation][]).

            This must fit [discord's requirements](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming).
        description
            The option's description (supports [localisation][]).

            This should be inclusively between 1-100 characters in length.
        default
            The option's default value.

            If this is left as no default then this option will be required.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
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

            * If the option name doesn't fit Discord's requirements.
            * If the option name has uppercase characters.
            * If the option description is over 100 characters in length.
            * If the command already has 25 options.
            * If `name` isn't valid for this command's callback when
              `validate_arg_keys` is [True][].
        """
        return self._add_option(
            localisation.MaybeLocalised("name", name),
            localisation.MaybeLocalised("description", description),
            hikari.OptionType.MENTIONABLE,
            default=default,
            key=key,
            pass_as_kwarg=pass_as_kwarg,
        )

    def set_float_autocomplete(self, name: str, callback: tanjun.AutocompleteSig[float] | None, /) -> Self:
        """Set the autocomplete callback for a float option.

        Parameters
        ----------
        name
            The option's name.

            If localised names were provided for the option then this should
            be the default name.
        callback
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [float][].

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
            error_message = "Option not found"
            raise KeyError(error_message)

        if option.type is not hikari.OptionType.FLOAT:
            error_message = "Option is not a float option"
            raise TypeError(error_message)

        if callback:
            option.autocomplete = True
            self._float_autocompletes[name] = callback

        elif name in self._float_autocompletes:
            option.autocomplete = False
            del self._float_autocompletes[name]

        return self

    def with_float_autocomplete(
        self, name: str, /
    ) -> collections.Callable[[_FloatAutocompleteSigT], _FloatAutocompleteSigT]:
        """Set the autocomplete callback for a float option through a decorator call.

        Parameters
        ----------
        name
            The option's name.

            If localised names were provided for the option then this should
            be the default name.

        Returns
        -------
        Collections.abc.Callable[[tanjun.abc.AutocompleteSig[float]], tanjun.abc.AutocompleteSig[float]]
            Decorator callback used to capture the autocomplete callback.

            More information on the autocomplete signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [float][].

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `float`.
        """

        def decorator(callback: _FloatAutocompleteSigT, /) -> _FloatAutocompleteSigT:
            self.set_float_autocomplete(name, callback)
            return callback

        return decorator

    def set_int_autocomplete(self, name: str, callback: tanjun.AutocompleteSig[int], /) -> Self:
        """Set the autocomplete callback for a string option.

        Parameters
        ----------
        name
            The option's name.

            If localised names were provided for the option then this should
            be the default name.
        callback
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [str][].

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
            error_message = "Option not found"
            raise KeyError(error_message)

        if option.type is not hikari.OptionType.INTEGER:
            error_message = "Option is not a int option"
            raise TypeError(error_message)

        option.autocomplete = True
        self._int_autocompletes[name] = callback
        return self

    def with_int_autocomplete(self, name: str, /) -> collections.Callable[[_IntAutocompleteSigT], _IntAutocompleteSigT]:
        """Set the autocomplete callback for a integer option through a decorator call.

        Parameters
        ----------
        name
            The option's name.

            If localised names were provided for the option then this should
            be the default name.

        Returns
        -------
        Collections.abc.Callable[[tanjun.abc.AutocompleteSig[int]], tanjun.abc.AutocompleteSig[int]]
            Decorator callback used to capture the autocomplete callback.

            More information on the autocomplete signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [int][].

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `int`.
        """

        def decorator(callback: _IntAutocompleteSigT, /) -> _IntAutocompleteSigT:
            self.set_int_autocomplete(name, callback)
            return callback

        return decorator

    def set_str_autocomplete(self, name: str, callback: tanjun.AutocompleteSig[str], /) -> Self:
        """Set the autocomplete callback for a str option.

        Parameters
        ----------
        name
            The option's name.

            If localised names were provided for the option then this should
            be the default name.
        callback
            The autocomplete callback for the option.

            More information on this callback's signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [str][].

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
            error_message = "Option not found"
            raise KeyError(error_message)

        if option.type is not hikari.OptionType.STRING:
            error_message = "Option is not a str option"
            raise TypeError(error_message)

        option.autocomplete = True
        self._str_autocompletes[name] = callback
        return self

    def with_str_autocomplete(self, name: str, /) -> collections.Callable[[_StrAutocompleteSigT], _StrAutocompleteSigT]:
        """Set the autocomplete callback for a string option through a decorator call.

        Parameters
        ----------
        name
            The option's name.

            If localised names were provided for the option then this should
            be the default name.

        Returns
        -------
        Collections.abc.Callable[[tanjun.abc.AutocompleteSig[str]], tanjun.abc.AutocompleteSig[str]]
            Decorator callback used to capture the autocomplete callback.

            More information on the autocomplete signature can be found at
            [tanjun.abc.AutocompleteSig][] and the 2nd positional argument
            should be of type [str][].

        Raises
        ------
        KeyError
            Raises a key error if the option doesn't exist.
        TypeError
            Raises a type error if the option isn't of type `str`.
        """

        def decorator(callback: _StrAutocompleteSigT, /) -> _StrAutocompleteSigT:
            self.set_str_autocomplete(name, callback)
            return callback

        return decorator

    async def _process_args(self, ctx: tanjun.SlashContext, /) -> collections.Mapping[str, typing.Any]:
        keyword_args: dict[
            str, int | float | str | hikari.Attachment | hikari.User | hikari.Role | hikari.InteractionChannel
        ] = {}
        for tracked_option in self._tracked_options.values():
            if not (option := ctx.options.get(tracked_option.name)):
                if tracked_option.default is tanjun.NO_DEFAULT:
                    error_message = (
                        f"Required option {tracked_option.name} is missing data, are you sure your commands"
                        " are up to date?"
                    )
                    raise RuntimeError(error_message)  # TODO: ConversionError?

                if tracked_option.default is not tanjun.NO_PASS:
                    keyword_args[tracked_option.key] = tracked_option.default

            elif option.type is hikari.OptionType.USER:
                member: hikari.InteractionMember | None = None
                if tracked_option.is_only_member and not (member := option.resolve_to_member(default=None)):
                    error_message = f"Couldn't find member for provided user: {option.value}"
                    raise errors.ConversionError(error_message, tracked_option.name)

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
        *,
        option: hikari.CommandInteractionOption | None = None,  # noqa: ARG002
        hooks: collections.MutableSet[tanjun.SlashHooks] | None = None,
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

        await own_hooks.trigger_post_execution(ctx, hooks=hooks)

    async def execute_autocomplete(
        self,
        ctx: tanjun.AutocompleteContext,
        /,
        *,
        option: hikari.AutocompleteInteractionOption | None = None,  # noqa: ARG002
    ) -> None:
        # <<inherited docstring from tanjun.abc.BaseSlashCommand>>.
        if ctx.focused.type is hikari.OptionType.STRING:
            callback = self._str_autocompletes.get(ctx.focused.name)

        elif ctx.focused.type is hikari.OptionType.FLOAT:
            callback = self._float_autocompletes.get(ctx.focused.name)

        elif ctx.focused.type is hikari.OptionType.INTEGER:
            callback = self._int_autocompletes.get(ctx.focused.name)

        else:
            error_message = f"Autocomplete isn't implemented for '{ctx.focused.type}' option yet."
            raise NotImplementedError(error_message)

        if not callback:
            error_message = f"No autocomplete callback found for '{ctx.focused.name}' option"
            raise RuntimeError(error_message)

        await ctx.call_with_async_di(callback, ctx, ctx.focused.value)

    def copy(self, *, parent: tanjun.SlashCommandGroup | None = None) -> Self:
        # <<inherited docstring from tanjun.abc.ExecutableCommand>>.
        inst = super().copy(parent=parent)
        inst._callback = copy.copy(self._callback)  # noqa: SLF001
        return inst
