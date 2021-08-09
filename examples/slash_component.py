# As a note, a slash command context should always be responded to and leaving
# as leaving it without a response will leave the command call either marked
# as loading for 15 minutes if it's been deferred or marked as failed after
# 3 seconds (by default slash commands are automatically deferred before the
# 3 second expire mark but this doesn't negate the need to give an actual
# response).
#
# For most of these examples `tanjun.traits.SlashContext.respond` is used for
# for responding to interactions, this abstracts away the interactions response
# flow by tracking state on Context object to decide how to respond.
# While the lower level approache may also be used for responding it is
# generally recommended that you use the relevant lower level methods on
# `tanun.traits.SlashContext` to allow state to still be tracked and ensure
# better compatability.
import hikari

import tanjun

component = tanjun.Component()


# Here we declare a command as defaulting to ephemeral,
# This means that all calls made to SlashContext's message creating methods
# (e.g. respond, create_initial_respones and create_followup) will be ephemeral
# unless `flags` is specified (including calls made by command checks and
# the CommandError handler).
@component.with_slash_command
@tanjun.as_slash_command("nsfw", "A NSFW command", default_to_ephemeral=True)
async def nsfw_command(ctx: tanjun.traits.Context) -> None:
    # Thx to default_to_ephemeral=True, this response will be ephemeral
    await ctx.respond("nsfw stuff")


# While slash command groups may be nested, this only works up to one level.
top_group = component.with_slash_command(tanjun.slash_command_group("places", "get info about places"))
nested_group = top_group.with_command(tanjun.slash_command_group("hi", "say hello or something!"))


@nested_group.with_command
@tanjun.with_str_slash_option("name", "Kimi no na wa")
@tanjun.as_slash_command("hi", "hello")
async def test_op_hi_command(ctx: tanjun.traits.Context, name: str) -> None:
    await ctx.respond(f"Hi, {name}")


@top_group.with_command
@tanjun.as_slash_command("japan", "nihon is my city")
async def test_japan_command(ctx: tanjun.traits.Context) -> None:
    await ctx.respond("Nihongo ga dekimasu ka?")


@top_group.with_command
@tanjun.as_slash_command("europe", "IDK how to describe europe... big?")
async def test_europe_command(ctx: tanjun.traits.Context) -> None:
    await ctx.respond("I don't know how to describe europe... big?")


@component.with_command
@tanjun.as_slash_command("lower", "Lower level command which takes advantage of slash command specific impl detail")
async def lower_command(ctx: tanjun.traits.SlashContext) -> None:
    # Since the SlashContext.respond can't have `flags` as an argument
    # providing the flags for the initial response requires lower level usage.
    #
    # As a note, you can only create the initial response for a slash command
    # context once and any further calls will result in an error being raised.
    # to create follow ups see `tanjun.traits.SlashContext.create_followup`.
    #
    # As another note, an initial response for a slash context must be created
    # within 3 seconds of the interaction being received otherwise it  will
    # either be automatically deferred or expire (if automatic deferral is
    # disabled or not enabled). In the case that an interaction is deferred then
    # `tanjun.traits.SlashContext.edit_initial_response` or
    # `tanjun.traits.SlashContext.respond` should be used to edit an initial
    # response in. `tanjun.traits.SlashContext.defer` may be used to
    # defer an interaction in the case that automatic deferral is disabled or
    # the response is always going to be defered.
    await ctx.create_initial_response("I'm sorry, Dave", flags=hikari.MessageFlag.EPHEMERAL, tts=True)

    # Since the SlashContext.respond can't have `attachments` as an argument,
    # providing attachments requires impl detail specific and lower level usage.
    #
    # As a note, you can only create followup responses after an initial response
    # has been made and any pre-mature calls will result in errors being raised.
    await ctx.create_followup(
        "I'm afraid I can't do that",
        attachments=[hikari.URL("https://cdn.discordapp.com/emojis/520742867933724676.png?v=1")],
    )


# Here's another lower level usage example except this one explicitly defers.
# This will have to be done within clients where automatic deferral is disabled
# if a command (including the relevant converters and checks) takes more than 3
# seconds to execute to avoid erronous behaviour.
@component.with_command
@tanjun.as_slash_command("defer", "Lower level command which explicitly defers")
async def defer_command(ctx: tanjun.traits.SlashContext) -> None:
    await ctx.defer()
    ... # Work which may take a while
    # Either edit_initial_response or respond may be used here.
    await ctx.edit_initial_response("Done 👍")


# Here we define a loader which can be used to easily load this example
# components into a bot from a link (assuming the environment has all the
# right configurations setup.)
@tanjun.as_loader
def load_examples(client: tanjun.traits.Client) -> None:
    client.add_component(component.copy())
