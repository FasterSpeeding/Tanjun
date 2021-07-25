import typing

import hikari

import tanjun
from examples import config
from examples import impls
from examples import protos


async def get_prefix(
    ctx: tanjun.traits.MessageContext, database: protos.DatabaseProto = tanjun.injected(type=protos.DatabaseProto)
) -> typing.Sequence[str]:
    if ctx.guild_id and (guild_info := await database.get_guild_info(ctx.guild_id)):
        return guild_info.prefixes

    return ()


def run() -> None:
    loaded_config = config.ExampleConfig.load()
    bot = hikari.GatewayBot(loaded_config.bot_token)
    (
        tanjun.Client.from_gateway_bot(bot)
        .load_modules("examples.complex_component")
        .load_modules("examples.basic_component")
        .add_prefix(loaded_config.prefix)
        .set_prefix_getter(get_prefix)
        .add_type_dependency(config.ExampleConfig, lambda: loaded_config)
        .add_type_dependency(protos.DatabaseProto, tanjun.cache_callback(impls.DatabaseImpl.connect))
    )
    bot.run()
