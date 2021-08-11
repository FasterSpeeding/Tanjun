# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
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
"""Example of how to run a standard Tanjun client instance."""
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
    bot = hikari.GatewayBot(loaded_config.bot_token)
    (
        tanjun.Client.from_gateway_bot(bot)
        .load_modules("examples.complex_component")
        .load_modules("examples.basic_component")
        .load_modules("examples.slash_component")
        .add_prefix(loaded_config.prefix)
        .set_prefix_getter(get_prefix)
        .add_type_dependency(config.ExampleConfig, lambda: loaded_config)
        .add_type_dependency(protos.DatabaseProto, tanjun.cache_callback(impls.DatabaseImpl.connect))
    )
    bot.run()
