# -*- coding: utf-8 -*-
# cython: language_level=3
"""Example of how to run a standard Tanjun client instance with a GatewayBot."""
from collections import abc as collections

import hikari

import tanjun
from examples import config
from examples import impls
from examples import protos


async def get_prefix(
    ctx: tanjun.abc.MessageContext, database: protos.DatabaseProto = tanjun.injected(type=protos.DatabaseProto)
) -> collections.Sequence[str]:
    if ctx.guild_id and (guild_info := await database.get_guild_info(ctx.guild_id)):
        return guild_info.prefixes

    return ()


def run() -> None:
    loaded_config = config.ExampleConfig.load()
    # Note that by default `from_gateway_bot` sets `event_managed` to `True`.
    # This means that the client will be implicitly started and stopped
    # based on Hikari's lifetime events.
    #
    # You can alternatively start and stop the Tanjun client yourself
    # by calling `open` and `close` on it or using it as a context manager.
    #
    # Note that starting a Tanjun client before the relevant bot instance
    # may lead to erroneous behaviour as it won't be able to make requests.
    bot = hikari.GatewayBot(loaded_config.bot_token)
    (
        tanjun.Client.from_gateway_bot(bot)
        .load_modules("examples.complex_component")
        # Both slash commands and message commands can be automatically executed
        # by a gateway bot bound client
        .load_modules("examples.message_component")
        .load_modules("examples.slash_component")
        .add_prefix(loaded_config.prefix)
        .set_prefix_getter(get_prefix)
        .set_type_dependency(config.ExampleConfig, lambda: loaded_config)
        .set_type_dependency(protos.DatabaseProto, tanjun.cache_callback(impls.DatabaseImpl.connect))
    )
    bot.run()


if __name__ == "__main__":
    run()
