# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2022, Faster Speeding
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
"""Callback dependencies used for getting context and client based data."""
from __future__ import annotations

__all__: list[str] = ["fetch_my_user"]

import typing

import alluka
import hikari

from .. import abc as tanjun
from . import async_cache


async def fetch_my_user(
    client: alluka.Injected[tanjun.Client],
    *,
    me_cache: alluka.Injected[typing.Optional[async_cache.SingleStoreCache[hikari.OwnUser]]] = None,
) -> hikari.OwnUser:
    """Fetch the current user from the client's cache or rest client.

    !!! note
        This is used in the standard `LazyConstant[hikari.users.OwnUser]`
        dependency.

    Parameters
    ----------
    client
        The client to use to fetch the user.

    Returns
    -------
    hikari.OwnUser
        The current user.

    Raises
    ------
    RuntimeError
        If the cache couldn't be used to get the current user and the REST
        client is not bound to a Bot token.
    """
    if client.cache and (user := client.cache.get_me()):
        return user

    if me_cache and (user := await me_cache.get(default=None)):
        return user

    if client.rest.token_type is not hikari.TokenType.BOT:
        raise RuntimeError("Cannot fetch current user with a REST client that's bound to a client credentials token")

    return await client.rest.fetch_my_user()
