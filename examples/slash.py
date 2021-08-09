import tanjun

component = tanjun.Component()
top_group = component.with_slash_command(tanjun.slash_command_group("test", "testicles"))
nested_group = top_group.with_command(tanjun.slash_command_group("op", "heeey, sexy ladies!"))
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
