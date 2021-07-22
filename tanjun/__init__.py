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

__all__: typing.Sequence[str] = [
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
    "AcceptsEnum",
    "as_loader",
    "Client",
    "PrefixGetterSig",
    # commands.py
    "as_interaction_command",
    "as_message_command",
    "as_message_command_group",
    "InteractionCommand",
    "MessageCommand",
    "MessageCommandGroup",
    # components.py
    "components",
    "Component",
    # context.py
    "context",
    "MessageContext",
    "InteractionContext",
    # conversion.py
    "conversion",
    "ChannelConverter",
    "ColorConverter",
    "EmojiConverter",
    "GuildConverter",
    "InviteConverter",
    "MemberConverter",
    "PresenceConverter",
    "RoleConverter",
    "SnowflakeConverter",
    "UserConverter",
    "VoiceStateConverter",
    # errors.py
    "errors",
    "CommandError",
    "ConversionError",
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
    "ErrorHookSig",
    "Hooks",
    "HookSig",
    "ParserHookSig",
    "PreExecutionHookSig",
    # injector.py
    "injector",
    "cache_callback",
    "CallbackSig",
    "Getter",
    "Undefined",
    "UNDEFINED",
    "UndefinedOr",
    "injected",
    "Injected",
    "InjectorClient",
    "Injectable",
    # parsing.py
    "parsing",
    "Argument",
    "Option",
    "ShlexParser",
    "verify_parameters",
    "with_argument",
    "with_greedy_argument",
    "with_multi_argument",
    "with_option",
    "with_multi_option",
    "with_parser",
    "with_typed_parameters",
    # traits.py
    "traits",
]

import typing

from tanjun import traits
from tanjun.checks import *
from tanjun.clients import *
from tanjun.commands import *
from tanjun.components import *
from tanjun.context import *
from tanjun.conversion import *
from tanjun.errors import *
from tanjun.hooks import *
from tanjun.injector import *
from tanjun.parsing import *

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
