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
"""Example basic usage of Tanjun's slash command system."""

# As a note, a slash command context should always be responded to as leaving
# it without a response will leave the command call either marked as loading
# for 15 minutes (if it's been deferred) or marked as failed after
# 3 seconds (by default slash commands are automatically deferred before the
# 3 second expire mark but this doesn't negate the need to give an actual
# response).
#
# For most of these examples `tanjun.abc.SlashContext.respond` is used for
# responding to interactions, this abstracts away the interactions response
# flow by tracking state on the Context object in-order to decide how to
# respond. While the lower level approache may also be used for responding it
# is generally recommended that you use the relevant lower level methods on
# `tanjun.abc.SlashContext` to allow state to still be tracked and ensure
# better compatibility.
import asyncio
import typing

import hikari

import tanjun

component = tanjun.Component()


# Here we declare a command as defaulting to ephemeral, this means that all
# calls made to SlashContext's message creating methods (e.g. respond,
# create_initial_respones and create_followup) will be ephemeral (only visible
# to the user who called the command) unless `flags` is specified. This includes
# calls made by command checks and by the CommandError handler.
@component.with_slash_command
@tanjun.as_slash_command("nsfw", "command description", default_to_ephemeral=True)
async def nsfw_command(ctx: tanjun.abc.Context) -> None:
    # Thanks to default_to_ephemeral=True, this response will be ephemeral.
    await ctx.respond("nsfw stuff")


# While slash command groups may be nested, this only works up to one level.
top_group = component.with_slash_command(tanjun.slash_command_group("places", "get info about places"))
nested_group = top_group.with_command(tanjun.slash_command_group("interaction", "say hello or something!"))


@nested_group.with_command
# This adds a required member option to the command which'll be passed to the
# "member" argument as type hikari.Member.
@tanjun.with_member_slash_option("member", "Option description")
# This adds an optional string option to the command which'll be passed
# to the "name" argument as type str if it was provided else None.
@tanjun.with_str_slash_option("name", "Option description", default=None)
@tanjun.as_slash_command("hi", "command description")
async def hi_command(ctx: tanjun.abc.Context, name: typing.Optional[str], member: hikari.Member) -> None:
    if name:
        await ctx.respond(f"Hi, {name} and {member.username}")

    else:
        await ctx.respond(f"Hi {member.username}")


@top_group.with_command
# Here we add a required string option which'll be convertered to an emoji object.
@tanjun.with_str_slash_option("emoji", "Option description", converters=tanjun.to_emoji)
@tanjun.as_slash_command("japan", "command description")
async def japan_command(ctx: tanjun.abc.Context, emoji: hikari.Emoji) -> None:
    await ctx.respond(f"Nihongo ga dekimasu ka? {emoji}")


@top_group.with_command
@tanjun.as_slash_command("europe", "command description")
async def europe_command(ctx: tanjun.abc.Context) -> None:
    await ctx.respond("I don't know how to describe Europe... small?")


# The previous code leads to top_group having the following structure
#
# places (command group)
# |
# |__ japan (command)
# |
# |__ europe (command)
# |
# |__ interaction (command group)
#    |
#    |__ hi (command)


# For more information on slash command options and converters, see the
# documentation for `tanjun.commands` and `tanjun.converters`.
#
# It's worth noting that converters are only supported for string, integer
# and float options.


@component.with_command
@tanjun.as_slash_command("lower", "Lower level command which takes advantage of slash command specific detail")
async def lower_command(ctx: tanjun.abc.SlashContext) -> None:
    # Since `SlashContext.respond` can't have `flags` as an argument, providing
    # the flags when creating the initial response requires lower level usage.
    #
    # As a note, you can only create the initial response for a slash command
    # context once and any further calls will result in an error being raised.
    # To create follow up responses see `SlashContext.create_followup`.
    #
    # As another note, an initial response for a slash context must be created
    # within 3 seconds of the interaction being received otherwise it will
    # either be automatically deferred or expire (if automatic deferral is
    # disabled). In the case that an interaction is deferred then
    # `SlashContext.edit_initial_response` or `SlashContext.respond` should be
    # used to edit an initial response in. `tanjun.abc.SlashContext.defer` may
    # be used to defer an interaction in the case that automatic deferral is
    # disabled or the response is always going to be deferred.
    await ctx.create_initial_response("I'm sorry, Dave", flags=hikari.MessageFlag.EPHEMERAL, tts=True)

    # Since `SlashContext.respond` can't have attachments as an argument,
    # providing `attachments` requires the usage of slash command specific and
    # lower level detail.
    #
    # As a note, you can only create followup responses after an initial response
    # has been made and any pre-mature calls will result in errors being raised.
    await ctx.create_followup(
        "I'm afraid I can't do that",
        attachments=[hikari.URL("https://cdn.discordapp.com/emojis/520742867933724676.png?v=1")],
    )


# Here's a lower level usage example which explicitly defers the initial response.
# This will have to be done within clients where automatic deferral is disabled
# if a command (including the relevant converters and checks) takes more than 3
# seconds to execute to avoid errenous behaviour.
@component.with_command
@tanjun.as_slash_command("defer", "Lower level command which explicitly defers")
async def defer_command(ctx: tanjun.abc.SlashContext) -> None:
    # Note that if we want the response that's later edited in to be ephemeral
    # then we can pass `flags=hikari.MessageFlags.EPHEMERAL` to `SlashContext.defer`.
    await ctx.defer()
    await asyncio.sleep(5)  # Do some work which may take a while
    # Either edit_initial_response or respond may be used here.
    await ctx.edit_initial_response("Done 👍")


# Here we use make_loader to define a loader which can be used to both load
# and unload and reload this example component into a bot from a link
# (assuming the environment has all the right configurations setup).
#
# Alternatively @tanjun.as_loader and @tanjun.as_unloader can be used
# for more fine-grained control.
load_slash = component.make_loader()
