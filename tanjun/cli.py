# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2021, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Tanjun's standard command-line interface entry point."""
from __future__ import annotations

__all__: list[str] = ["main"]

import argparse
import asyncio
import pathlib
import re
import typing

import hikari

from . import __version__
from . import clients

module_regex: typing.Final[re.Pattern[str]] = re.compile(r"[\.a-zA-Z_]+")


def _parse_path(value: str) -> typing.Union[str, pathlib.Path]:
    if module_regex.fullmatch(value):
        return value

    return pathlib.Path(value)


def main():
    parser = argparse.ArgumentParser("Tanjun", description="Tanjun command-line interface entry point.")

    parser.add_argument(
        "-v", "--version", action="version", version=f"Tanjun: {__version__}; hikari {hikari.__version__}"
    )
    parser.add_argument(
        "-l",
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level.",
    )
    parser.add_argument("-c", "--config", help="Path to configuration file.", default=None, type=pathlib.Path)
    parser.add_argument(
        "-m",
        "--modules",
        nargs="*",
        help="Modules to load components and dependencies from.",
        type=_parse_path,
        default=(),
    )

    sub_parsers = parser.add_subparsers(help="Startup a standard implementation Hikari bot with tanjun", dest="type")

    gateway_parser = sub_parsers.add_parser("gateway", description="Start a Hikari gateway bot.")
    gateway_parser.add_argument(
        "--intents",
        help="Intents to declare for a gateway bot.",
        default=hikari.Intents.ALL_UNPRIVILEGED,
        type=hikari.Intents,
    )
    gateway_parser.add_argument(
        "--cache-components",
        help="The cache components to enable for a gateway bot.",
        default=hikari.CacheComponents.ALL,
    )

    sub_parsers.add_parser("rest", description="Start a Hikari REST bot.")

    parser.add_argument("token", help="Token to use for authentication.")

    args = parser.parse_args()

    if args.type == "gateway":
        bot = hikari.impl.GatewayBot(
            args.token,
            logs=args.log_level.upper(),
            intents=args.intents,
            cache_settings=hikari.CacheSettings(components=args.cache_components),
        )
        client = clients.Client.from_gateway_bot(bot).load_modules(*args.modules)

        if args.config:
            client.load_metadata_from(args.config)

        bot.run()

    else:
        bot = hikari.impl.RESTBot(args.token, logs=args.log_level.upper())
        client = clients.Client.from_rest_bot(bot).load_modules(*args.modules)

        if args.config:
            client.load_metadata_from(args.config)

        asyncio.run(_run_rest_bot(bot, client))


async def _run_rest_bot(bot: hikari.impl.RESTBot, client: clients.Client, /) -> None:
    await bot.start()
    async with client:
        await bot.join()
