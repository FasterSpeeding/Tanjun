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
"""Examples of how checks may be used within Tanjun."""

import hikari

import tanjun

from . import protos

MASTER_GUILD = 696969

# Before you go into writing custom checks, you should check out the standard
# checks implemented in `tanjun.checks` to see if anything there meets your
# use case(s).

# In essence a check is just a callback which takes a Context and returns a bool.
#
# As shown below, these may either be synchronous or asynchronous and support
# a number of useful features including dependency injection and specialised behaiour
# through standard errors.


# Here we define a generic check which takes `tanjun.abc.Context` and therefore
# is valid for both the message and rest command flows.
def check(ctx: tanjun.abc.Context) -> bool:
    # As an example, this check only lets a command run if the author's
    # discriminator is even.
    # Since this is pure maths, this can be a synchronous check.
    return int(ctx.author.discriminator) % 2 == 0


# Here we get request an implementation for the database protocol (which will
# have been added to the client with `Client.set_type_dependency`).
#
# It's also worth noting that since this check takes `SlashContext` it is
# therefore only valid for the slash command flow.
async def slash_check(
    ctx: tanjun.abc.SlashContext, db: protos.DatabaseProto = tanjun.inject(type=protos.DatabaseProto)
) -> bool:
    # Here we return `True` (indicating that the command can run) if the
    # user has an account in the database.
    if await db.get_user_info(ctx.author.id):
        return True

    # If they don't then we raise a special error which will be caught
    # by the command handler and displayed to the user.
    raise tanjun.CommandError("You cannot use this command until you have setup an account")


# It's worth noting that since this check takes `MessageContext` it is
# therefore only valid for the message command flow.
async def message_check(ctx: tanjun.abc.MessageContext) -> bool:
    try:
        # Here we check if the command's author is in the hard-coded
        # "master guild".
        await ctx.rest.fetch_member(MASTER_GUILD, ctx.author.id)

    except hikari.NotFoundError:
        # If they are not present then we raise a "HaltExecution" to mark the
        # command as not found, essentially hiding it.
        raise tanjun.HaltExecution from None

    # Otherwise we return `True` (indicating that the command can run).
    return True


# Custom checks can be added to commands as seen below:


@tanjun.with_check(slash_check)  # Using the `with_check` decorator function.
@tanjun.as_slash_command("name", "description")
async def slash_command(ctx: tanjun.abc.SlashContext) -> None:
    raise NotImplementedError


slash_command.add_check(check)  # and using the chainable `add_check` method


# To components as seen below:

component = tanjun.Component().add_check(check)
# Where checks set with Component.add_check will be called for all commands
# within the component.

# and to the client as seen below:

bot = hikari.GatewayBot("TOKEN")
component = tanjun.Client.from_gateway_bot(bot).add_check(check)
# Where checks set with Component.add_check will be called for all commands
# within the client.
