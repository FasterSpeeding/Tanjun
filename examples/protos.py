# -*- coding: utf-8 -*-
# cython: language_level=3
"""Example interfaces used within the examples."""
import typing


class GuildConfig(typing.Protocol):
    @property
    def prefixes(self) -> list[str]:
        raise NotImplementedError


class UserInfo(typing.Protocol):
    ...


class DatabaseProto(typing.Protocol):
    async def get_guild_info(self, guild_id: int) -> typing.Optional[GuildConfig]:
        raise NotImplementedError

    async def get_user_info(self, user_id: int) -> typing.Optional[UserInfo]:
        raise NotImplementedError

    async def remove_user(self, user_id: int) -> None:
        raise NotImplementedError
