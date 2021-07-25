import hikari

import tanjun
from examples import config
from examples import impls
from examples import protos


def run() -> None:
    loaded_config = config.ExampleConfig.load()
    bot = hikari.GatewayBot(loaded_config.bot_token)
    (
        tanjun.Client.from_gateway_bot(bot)
        .load_modules("examples.complex_component")
        .load_modules("examples.basic_component")
        .add_prefix(loaded_config.prefix)
        .add_type_dependency(config.ExampleConfig, lambda: loaded_config)
        .add_type_dependency(protos.DatabaseProto, tanjun.cache_callback(impls.DatabaseImpl.connect))
    )
    bot.run()
