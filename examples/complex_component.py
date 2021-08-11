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
"""Example component which takes advantage of more complex systems within Tanjun such as dependency injection."""
import tanjun
from examples import protos

component = tanjun.Component()


@component.with_command
@tanjun.with_guild_check
@tanjun.as_message_command("guild")
async def guild_command(
    ctx: tanjun.abc.MessageContext, database: protos.DatabaseProto = tanjun.injected(type=protos.DatabaseProto)
):
    assert ctx.guild_id is not None  # This is checked by the "with_guild_check"
    guild_info = await database.get_guild_info(ctx.guild_id)

    if not guild_info:
        # CommandError's message will be sent as a response message.
        raise tanjun.CommandError("No information stored for the current guild")

    ...  # TODO: implement response


@component.with_command
@tanjun.as_message_command_group("user")
async def user(
    ctx: tanjun.abc.MessageContext, database: protos.DatabaseProto = tanjun.injected(type=protos.DatabaseProto)
) -> None:
    user = await database.get_user_info(ctx.author.id)

    if not user:
        # CommandError's message will be sent as a response message.
        raise tanjun.CommandError("No information stored for you")

    ...  # TODO: implement response


@user.with_command
@tanjun.as_message_command("remove self")
async def remove_self(
    ctx: tanjun.abc.MessageContext, database: protos.DatabaseProto = tanjun.injected(type=protos.DatabaseProto)
) -> None:
    await database.remove_user(ctx.author.id)


# Here we define a loader which can be used to easily load this example
# components into a bot from a link (assuming the environment has all the
# right configurations setup.)
@tanjun.as_loader
def load_examples(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())
