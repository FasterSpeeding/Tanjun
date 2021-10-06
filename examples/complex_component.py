# -*- coding: utf-8 -*-
# cython: language_level=3
# Tanjun Examples - A collection of examples for Tanjun.
# Written in 2021 by Lucina Lucina@lmbyrne.dev
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain worldwide.
# This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <https://creativecommons.org/publicdomain/zero/1.0/>.
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
