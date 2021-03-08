import time
import typing

import tanjun
from examples import example_config


class BasicComponent(tanjun.Component):
    def __init__(self, *args: typing.Any, config: example_config.ExampleConfig, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        # Here we would want to set attributes used for initialising a database connection.
        self.config = config

    async def open(self) -> None:
        ...  # Here we would want to initialise a database connection for use in the note commands.
        await super().open()

    async def close(self) -> None:
        ...  # Here we would close our database connection.
        await super().close()

    @tanjun.as_command("ping")
    async def ping(self, ctx: tanjun.traits.Context, /) -> None:
        # As a note, for brevity any hidden Discord REST error handling logic hasn't been included here.
        # For more information on how Discord REST errors may be handled see
        # https://fasterspeeding.github.io/Yuyo/backoff.html
        start_time = time.perf_counter()
        message = await ctx.message.reply(content="Nyaa master!!!")
        time_taken = (time.perf_counter() - start_time) * 1_000
        heartbeat_latency = ctx.shard.heartbeat_latency * 1_000
        await message.edit(f"PONG\n - REST: {time_taken:.0f}ms\n - Gateway: {heartbeat_latency:.0f}ms")

    @tanjun.as_group("note", "notes")
    async def note(self, ctx: tanjun.traits.Context) -> None:
        await ctx.message.reply("You have zero notes")

    @tanjun.with_greedy_argument("value")
    @tanjun.with_argument("name")
    @note.with_command("add", "create")
    async def note_add(self, ctx: tanjun.traits.Context, name: str, value: str) -> None:
        ...  # Actual implementation
        await ctx.message.reply(f"Added {name} note")

    @tanjun.with_option("force", "--force", "-f", converters=(bool,), default=False)
    @tanjun.with_argument("name")
    @note.with_command("remove", "delete")
    async def note_remove(self, ctx: tanjun.traits.Context, name: str, force: bool) -> None:
        ...  # Actual implementation
        await ctx.message.reply(f"Removed {name} note")
