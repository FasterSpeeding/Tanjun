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
