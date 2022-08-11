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
"""Standard implementations of Tanjun's command objects."""
from __future__ import annotations

__all__: list[str] = [
    "BaseSlashCommand",
    "MenuCommand",
    "MessageCommand",
    "MessageCommandGroup",
    "SlashCommand",
    "SlashCommandGroup",
    "annotations",
    "as_message_command",
    "as_message_command_group",
    "as_message_menu",
    "as_slash_command",
    "as_user_menu",
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

from .menu import MenuCommand
from .menu import as_message_menu
from .menu import as_user_menu
from .message import MessageCommand
from .message import MessageCommandGroup
from .message import as_message_command
from .message import as_message_command_group
from .slash import BaseSlashCommand
from .slash import SlashCommand
from .slash import SlashCommandGroup
from .slash import as_slash_command
from .slash import slash_command_group
from .slash import with_attachment_slash_option
from .slash import with_bool_slash_option
from .slash import with_channel_slash_option
from .slash import with_float_slash_option
from .slash import with_int_slash_option
from .slash import with_member_slash_option
from .slash import with_mentionable_slash_option
from .slash import with_role_slash_option
from .slash import with_str_slash_option
from .slash import with_user_slash_option
