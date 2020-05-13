from __future__ import annotations

__all__ = []

import logging
import typing

import click
from hikari.internal import marshaller

from tanjun import client
from tanjun import configs


@click.command()
@click.option(
    "--bot-client", envvar="BOT_CLIENT", help="The Hikari bot client to initiate with.",
)
@click.option(
    "--config", envvar="CONFIG", help="A path to the config to use for initiating the client.", type=click.File(),
)
@click.option("--debug", type=click.BOOL, help="Enable or disable debug mode.")
@click.option(
    "--logger",
    default="INFO",
    envvar="LOGGER",
    help="The logging level to use for this instance",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
@click.option(
    "--modules",
    envvar="MODULES",
    help="Paths to the modules to initialise from.",
    multiple=True,
    type=click.STRING,
    # type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "--token",
    envvar="TOKEN",
    help="The token to use to authenticate with Discord.",
    hide_input=True,
    required=False,
    type=click.STRING,
)
def main(
    bot_client: str, config: click.File, debug: bool, logger: str, modules: typing.Sequence[str], token: str
) -> None:
    logging.basicConfig(
        level=logger,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if config is not None and any(value is not None for value in (bot_client, debug, modules, token)):
        raise RuntimeError("--config cannot be passed along with any other options other than `logger`.")

    if config is None and token is None:
        raise RuntimeError("Cannot startup a command client without a token or config.")

    if config is not None:
        loaded_config = configs.ClientConfig.deserialize(config.read())
        config.close()
        bot_client = loaded_config.bot_client(config=loaded_config)
    else:
        bot_client = marshaller.dereference_handle(
            bot_client if bot_client is not None else "hikari.clients.stateless#StatelessBot"
        )
        bot_client = bot_client(
            config=configs.ClientConfig(token=token, debug=debug if debug is not None else False)
            # TODO:more options
        )

    client.Client(bot_client, modules=modules)
    bot_client.run()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
