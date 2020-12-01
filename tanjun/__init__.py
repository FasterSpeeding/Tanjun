# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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
    # checks.py
    "checks",
    "dm_only",
    "guild_only",
    "nsfw_only",
    "sfw_only",
    "owner_only",
    "requires_author_permissions",
    "requires_bot_permissions",
    # clients.py
    "clients",
    "Client",
    # command.py
    "commands",
    "Command",
    "CommandGroup",
    # components.py
    "components",
    "command",
    "Component",
    "event",
    "group",
    # context.py
    "context",
    "Context",
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
    "NotEnoughArgumentsError",
    "TooManyArgumentsError",
    "ParserError",
    "TanjunError",
    "TanjunWarning",
    "StateWarning",
    # hooks.py
    "hooks",
    "Hooks",
    # parsing.py
    "parsing",
    "argument",
    "greedy_argument",
    "multi_argument",
    "option",
    "multi_option",
    "Argument",
    "Option",
    "ShlexParser",
    "generate_parameters",
    "verify_parameters",
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
from tanjun.parsing import *
