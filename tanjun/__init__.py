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
    "__git_sha1__",
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
    "Client",
    "ClientCallbackNames",
    "MessageAcceptsEnum",
    # commands.py
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
    # conversion.py
    "conversion",
    "to_channel",
    "to_color",
    "to_colour",
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
    "cache_callback",
    "injected",
    "Injected",
    # parsing.py
    "Argument",
    "Option",
    "ShlexParser",
    "with_argument",
    "with_greedy_argument",
    "with_multi_argument",
    "with_option",
    "with_multi_option",
    "with_parser",
]

from . import abc
from .checks import *
from .clients import *
from .commands import *
from .components import *
from .context import *
from .conversion import *
from .errors import *
from .hooks import *
from .injecting import *
from .parsing import *

__author__ = "Faster Speeding"
__ci__ = ""
__copyright__ = "© 2020-2021 Faster Speeding"
__coverage__ = ""
__docs__ = "https://fasterspeeding.github.io/Tanjun/"
__email__ = "lucina@lmbyrne.dev"
__issue_tracker__ = "https://github.com/FasterSpeeding/Tanjun/issues"
__license__ = "BSD"
__url__ = "https://github.com/FasterSpeeding/Tanjun"
__version__ = "2.0.0a1"
__git_sha1__ = "HEAD"
