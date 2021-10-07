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
"""Example of how to run a standard Tanjun client instance with a RESTBot."""
import asyncio

import hikari

import tanjun
from examples import config
from examples import impls
from examples import protos


async def run() -> None:
    loaded_config = config.ExampleConfig.load()
    # While a BOT token is assumed in this example, a client credentials OAuth2
    # token can also be used with Tanjun but this may limit functionality.
    bot = hikari.RESTBot(loaded_config.bot_token, hikari.TokenType.BOT)
    database = impls.DatabaseImpl()
    client = (
        # Passing True for declare_global_commands here instructs the client to
        # declare the slash commands within it which are marked as "global" during
        # the first startup.
        # A guild ID may also be passed here to instruct it to just declare the
        # global commands for that guild, this can be helpful for debug purposes.
        tanjun.Client.from_rest_bot(bot, declare_global_commands=True)
        # Unlike a gateway bot bound client, only slash commands will be automatically
        # executed by a client that's bound to a rest bot.
        .load_modules("examples.slash_component")
        .set_type_dependency(config.ExampleConfig, loaded_config)
        .set_type_dependency(protos.DatabaseProto, database)
        # Here we use client callbacks to manage the database, STOPPING can also be used to stop it.
        .add_client_callback(tanjun.ClientCallbackNames.STARTING, database.connect)
    )
    # Unlike with a gateway bot, for RESTBots hikari has no lifetime event
    # dispatch which can be used to implicitly startup and close the Tanjun
    # client. Instead, we must directly startup and close Tanjun.
    await bot.start()

    # Note that starting a Tanjun client before the relevant bot may lead
    # to erroneous behaviour as it won't be able to make any requests.

    # While this example uses the client as a context manager to implicitly start
    # and close it, the `open` and `close` methods can alternatively be used to the same effect.
    async with client:
        await bot.join()  # This waits until the bot is closed before closing Tanjun by exiting the context manager.


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
