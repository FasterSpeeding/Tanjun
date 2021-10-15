# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2021, Faster Speeding
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
`tanjun.Client.from_gateway_bot`, this enables both slash (interaction) and message
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
@tanjun.with_parser
@tanjun.as_message_command("test")
async def test_command(ctx: tanjun.abc.Context, name: str) -> None:
    await ctx.respond(f"Hello, {name}!")

# Declare a ping slash command
@component.with_command
@tanjun.with_user_slash_option("user", "The user facing command option's description", default=None)
@tanjun.as_slash_command("hello", "The command's user facing description")
async def hello(ctx: tanjun.abc.Context, user: typing.Optional[hikari.User]) -> None:
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
client = tanjun.Client.from_rest_bot(bot, declare_global_commands=True)

# This will load components from modules based on loader functions.
# For more information on this see `tanjun.as_loader`.
client.load_modules("module.paths")

# Note, unlike a gateway bound bot, the rest bot will not automatically start
# itself due to the lack of Hikari lifetime events in this environment and
# will have to be started after the Hikari client.
async def main() -> None:
    await bot.start()
    async with client.open():
        await bot.join()
```

For more extensive examples see the
[repository's examples](https://github.com/FasterSpeeding/Tanjun/tree/master/examples).
"""
from __future__ import annotations

__all__: list[str] = [
    # __init__.py
    "__author__",
    "__ci__",
    "__copyright__",
    "__coverage__",
    "__docs__",
    "__email__",
    "__issue_tracker__",
    "__license__",
    "__url__",
    "__version__",
    # abc.py
    "abc",
    # checks.py
    "checks",
    "with_check",
    "with_dm_check",
    "with_guild_check",
    "with_nsfw_check",
    "with_sfw_check",
    "with_owner_check",
    "with_author_permission_check",
    "with_own_permission_check",
    # clients.py
    "clients",
    "as_loader",
    "as_unloader",
    "Client",
    "ClientCallbackNames",
    "MessageAcceptsEnum",
    # commands.py
    "commands",
    "as_message_command",
    "as_message_command_group",
    "as_slash_command",
    "slash_command_group",
    "MessageCommand",
    "MessageCommandGroup",
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
    # components.py
    "components",
    "Component",
    # context.py
    "context",
    "MessageContext",
    "SlashContext",
    "SlashOption",
    # conversion.py
    "conversion",
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
    "to_presence",
    "to_role",
    "to_snowflake",
    "to_user",
    "to_voice_state",
    # dependencies.py
    "dependencies",
    "cache_callback",
    "LazyConstant",
    "make_lc_resolver",
    # errors.py
    "errors",
    "CommandError",
    "ConversionError",
    "HaltExecution",
    "FailedCheck",
    "MissingDependencyError",
    "NotEnoughArgumentsError",
    "TooManyArgumentsError",
    "ParserError",
    "TanjunError",
    "TanjunWarning",
    "StateWarning",
    # hooks.py
    "hooks",
    "AnyHooks",
    "Hooks",
    "MessageHooks",
    "SlashHooks",
    # injecting.py
    "injecting",
    "injected",
    "Injected",
    # parsing.py
    "parsing",
    "Argument",
    "Option",
    "ShlexParser",
    "with_argument",
    "with_greedy_argument",
    "with_multi_argument",
    "with_option",
    "with_multi_option",
    "with_parser",
    # utilities.py
    "utilities",
]

import typing

from . import abc
from . import utilities
from .checks import *
from .clients import *
from .commands import *
from .components import *
from .context import *
from .conversion import *
from .dependencies import *
from .errors import *
from .hooks import *
from .injecting import *
from .parsing import *

__author__: typing.Final[str] = "Faster Speeding"
__ci__: typing.Final[str] = "https://github.com/FasterSpeeding/Tanjun/actions"
__copyright__: typing.Final[str] = "© 2020-2021 Faster Speeding"
__coverage__: typing.Final[str] = "https://codeclimate.com/github/FasterSpeeding/Tanjun"
__docs__: typing.Final[str] = "https://tanjun.cursed.solutions/"
__email__: typing.Final[str] = "lucina@lmbyrne.dev"
__issue_tracker__: typing.Final[str] = "https://github.com/FasterSpeeding/Tanjun/issues"
__license__: typing.Final[str] = "BSD"
__url__: typing.Final[str] = "https://github.com/FasterSpeeding/Tanjun"
__version__: typing.Final[str] = "2.1.2a1"
