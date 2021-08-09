import hikari

import tanjun

component = tanjun.Component()


@component.with_command
@tanjun.as_slash_command("test", "Lower level command which takes advantage of slash command specific impl detail")
async def test_command(ctx: tanjun.traits.SlashContext) -> None:
    # Since the SlashContext.respond can't have `flags` as an argument
    # providing the flags for the initial response requires lower level usage.
    await ctx.create_initial_response("I'm sorry, Dave", flags=hikari.MessageFlag.EPHEMERAL, tts=True)
    # Since the SlashContext.respond can't have `attachments` as an argument,
    # providing attachments requires impl detail specific and lower level usage.
    await ctx.create_followup(
        "I'm afraid I can't do that",
        attachments=[hikari.URL("https://cdn.discordapp.com/emojis/520742867933724676.png?v=1")],
    )


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


top_group = component.with_slash_command(tanjun.slash_command_group("places", "get info about places"))
nested_group = top_group.with_command(tanjun.slash_command_group("hi", "say hello or something!"))
# While slash command groups may be nested, this only works up to one level.


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


# Here we define a loader which can be used to easily load this example
# components into a bot from a link (assuming the environment has all the
# right configurations setup.)
@tanjun.as_loader
def load_examples(client: tanjun.traits.Client) -> None:
    client.add_component(component.copy())
