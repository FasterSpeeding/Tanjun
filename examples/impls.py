# -*- coding: utf-8 -*-
# Tanjun Examples - A collection of examples for Tanjun.
# Written in 2021 by Lucina Lucina@lmbyrne.dev
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain worldwide.
# This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <https://creativecommons.org/publicdomain/zero/1.0/>.
"""Placeholder for `proto`'s standard implementations including logic for injecting them."""
import typing

import examples.config
import tanjun
from examples import protos


async def connect_to_database(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
    raise NotImplementedError  # this is a stand in for the real implementation which would be imported


class DatabaseImpl:
    def __init__(self) -> None:
        self._conn: typing.Any | None = None

    async def connect(self, config: examples.config.ExampleConfig = tanjun.inject(type=examples.config.ExampleConfig)):
        self._conn = await connect_to_database(password=config.database_password, url=config.database_url)

    async def get_guild_info(self, guild_id: int) -> protos.GuildConfig | None:
        raise NotImplementedError

    async def get_user_info(self, user_id: int) -> protos.UserInfo | None:
        raise NotImplementedError

    async def remove_user(self, user_id: int) -> None:
        raise NotImplementedError
