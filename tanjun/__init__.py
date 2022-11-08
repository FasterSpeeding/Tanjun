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
"""A flexible command framework designed to extend Hikari.

Examples
--------
A Tanjun client can be quickly initialised from a Hikari gateway bot through
[tanjun.Client.from_gateway_bot][], this enables both slash (interaction) and message
command execution:

```py
bot = hikari.GatewayBot("BOT_TOKEN")

# As a note, unless event_managed=False is passed here then this client
# will be managed based on gateway startup and stopping events.
# mention_prefix=True instructs the client to also set mention prefixes on the
# first startup.
client = tanjun.Client.from_gateway_bot(bot, declare_global_commands=True, mention_prefix=True)

component = tanjun.Component()
client.add_component(component)

# Declare a message command with some basic parser logic.
@component.with_command
@tanjun.with_greedy_argument("name", default="World")
@tanjun.as_message_command("test")
async def test_command(ctx: tanjun.abc.Context, name: str) -> None:
    await ctx.respond(f"Hello, {name}!")

# Declare a ping slash command
@component.with_command
@tanjun.with_user_slash_option("user", "The user facing command option's description", default=None)
@tanjun.as_slash_command("hello", "The command's user facing description")
async def hello(ctx: tanjun.abc.Context, user: hikari.User | None) -> None:
    user = user or ctx.author
    await ctx.respond(f"Hello, {user}!")
```

Alternatively, the client can also be built from a RESTBot but this will only
enable slash (interaction) command execution:

```py
bot = hikari.RESTBot("BOT_TOKEN", "Bot")

# declare_global_commands=True instructs the client to set the global commands
# for the relevant bot on first startup (this will replace any previously
# declared commands).
#
# `bot_managed=True` has to be explicitly passed here to indicate that the client
# should automatically start when the linked REST bot starts.
client = tanjun.Client.from_rest_bot(bot, bot_managed=True, declare_global_commands=True)

# This will load components from modules based on loader functions.
# For more information on this see [tanjun.as_loader][].
client.load_modules("module.paths")

# Thanks to `bot_managed=True`, this will also start the client.
bot.run()
```

For more extensive examples see the
[repository's examples](https://github.com/FasterSpeeding/Tanjun/tree/master/examples).

There are also
[written tutorials](https://patchwork.systems/programming/hikari-discord-bot/index.html)
that cover making a bot from scratch through to advanced concepts like Dependency Injection.
"""
from __future__ import annotations as _

__all__: list[str] = [
    "AnyHooks",
    "BucketResource",
    "Client",
    "ClientCallbackNames",
    "CommandError",
    "Component",
    "ConversionError",
    "FailedCheck",
    "FailedModuleImport",
    "FailedModuleLoad",
    "FailedModuleUnload",
    "HaltExecution",
    "Hooks",
    "HotReloader",
    "InMemoryConcurrencyLimiter",
    "InMemoryCooldownManager",
    "InteractionAcceptsEnum",
    "LazyConstant",
    "MenuCommand",
    "MessageAcceptsEnum",
    "MessageCommand",
    "MessageCommandGroup",
    "MessageHooks",
    "MissingDependencyError",
    "ModuleMissingLoaders",
    "ModuleMissingUnloaders",
    "ModuleStateConflict",
    "NotEnoughArgumentsError",
    "ParserError",
    "ShlexParser",
    "SlashCommand",
    "SlashCommandGroup",
    "SlashHooks",
    "TanjunError",
    "TooManyArgumentsError",
    "abc",
    "annotations",
    "as_interval",
    "as_loader",
    "as_message_command",
    "as_message_command_group",
    "as_message_menu",
    "as_self_injecting",
    "as_slash_command",
    "as_time_schedule",
    "as_unloader",
    "as_user_menu",
    "cached_inject",
    "checks",
    "clients",
    "commands",
    "components",
    "context",
    "conversion",
    "dependencies",
    "errors",
    "hooks",
    "inject",
    "inject_lc",
    "injected",
    "injecting",
    "parsing",
    "permissions",
    "schedules",
    "slash_command_group",
    "to_bool",
    "to_channel",
    "to_color",
    "to_colour",
    "to_datetime",
    "to_emoji",
    "to_guild",
    "to_invite",
    "to_invite_with_metadata",
    "to_member",
    "to_message",
    "to_presence",
    "to_role",
    "to_snowflake",
    "to_user",
    "to_voice_state",
    "utilities",
    "with_all_checks",
    "with_any_checks",
    "with_argument",
    "with_attachment_slash_option",
    "with_author_permission_check",
    "with_bool_slash_option",
    "with_channel_slash_option",
    "with_check",
    "with_concurrency_limit",
    "with_cooldown",
    "with_dm_check",
    "with_float_slash_option",
    "with_greedy_argument",
    "with_guild_check",
    "with_int_slash_option",
    "with_member_slash_option",
    "with_mentionable_slash_option",
    "with_multi_argument",
    "with_multi_option",
    "with_nsfw_check",
    "with_option",
    "with_own_permission_check",
    "with_owner_check",
    "with_parser",
    "with_role_slash_option",
    "with_sfw_check",
    "with_str_slash_option",
    "with_user_slash_option",
]

from alluka import inject
from alluka import inject as injected

from . import abc
from . import annotations
from . import context
from . import permissions
from . import utilities
from .abc import ClientCallbackNames
from .checks import with_all_checks
from .checks import with_any_checks
from .checks import with_author_permission_check
from .checks import with_check
from .checks import with_dm_check
from .checks import with_guild_check
from .checks import with_nsfw_check
from .checks import with_own_permission_check
from .checks import with_owner_check
from .checks import with_sfw_check
from .clients import Client
from .clients import InteractionAcceptsEnum
from .clients import MessageAcceptsEnum
from .clients import as_loader
from .clients import as_unloader
from .commands import MenuCommand
from .commands import MessageCommand
from .commands import MessageCommandGroup
from .commands import SlashCommand
from .commands import SlashCommandGroup
from .commands import as_message_command
from .commands import as_message_command_group
from .commands import as_message_menu
from .commands import as_slash_command
from .commands import as_user_menu
from .commands import slash_command_group
from .commands import with_attachment_slash_option
from .commands import with_bool_slash_option
from .commands import with_channel_slash_option
from .commands import with_float_slash_option
from .commands import with_int_slash_option
from .commands import with_member_slash_option
from .commands import with_mentionable_slash_option
from .commands import with_role_slash_option
from .commands import with_str_slash_option
from .commands import with_user_slash_option
from .components import Component
from .conversion import to_bool
from .conversion import to_channel
from .conversion import to_color
from .conversion import to_colour
from .conversion import to_datetime
from .conversion import to_emoji
from .conversion import to_guild
from .conversion import to_invite
from .conversion import to_invite_with_metadata
from .conversion import to_member
from .conversion import to_message
from .conversion import to_presence
from .conversion import to_role
from .conversion import to_snowflake
from .conversion import to_user
from .conversion import to_voice_state
from .dependencies import BucketResource
from .dependencies import HotReloader
from .dependencies import InMemoryConcurrencyLimiter
from .dependencies import InMemoryCooldownManager
from .dependencies import LazyConstant
from .dependencies import cached_inject
from .dependencies import inject_lc
from .dependencies import with_concurrency_limit
from .dependencies import with_cooldown
from .errors import CommandError
from .errors import ConversionError
from .errors import FailedCheck
from .errors import FailedModuleImport
from .errors import FailedModuleLoad
from .errors import FailedModuleUnload
from .errors import HaltExecution
from .errors import MissingDependencyError
from .errors import ModuleMissingLoaders
from .errors import ModuleMissingUnloaders
from .errors import ModuleStateConflict
from .errors import NotEnoughArgumentsError
from .errors import ParserError
from .errors import TanjunError
from .errors import TooManyArgumentsError
from .hooks import AnyHooks
from .hooks import Hooks
from .hooks import MessageHooks
from .hooks import SlashHooks
from .injecting import as_self_injecting
from .parsing import ShlexParser
from .parsing import with_argument
from .parsing import with_greedy_argument
from .parsing import with_multi_argument
from .parsing import with_multi_option
from .parsing import with_option
from .parsing import with_parser
from .schedules import as_interval
from .schedules import as_time_schedule
