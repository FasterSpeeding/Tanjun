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
