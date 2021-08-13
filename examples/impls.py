# -*- coding: utf-8 -*-
# cython: language_level=3
"""Placeholder for `proto`'s standard implementations including logic for injecting them."""
import typing

import examples.config
import tanjun
from examples import protos


async def connect_to_database(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
    raise NotImplementedError  # this is a stand in for the real implementation which would be imported


class DatabaseImpl:
    def __init__(self, connection: typing.Any) -> None:
        self._conn = connection

    @classmethod
    async def connect(cls, config: examples.config.ExampleConfig = tanjun.injected(type=examples.config.ExampleConfig)):
        return cls(await connect_to_database(password=config.database_password, url=config.database_url))

    async def get_guild_info(self, guild_id: int) -> typing.Optional[protos.GuildConfig]:
        raise NotImplementedError

    async def get_user_info(self, user_id: int) -> typing.Optional[protos.UserInfo]:
        raise NotImplementedError

    async def remove_user(self, user_id: int) -> None:
        raise NotImplementedError
