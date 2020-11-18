# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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
from __future__ import annotations

__all__: typing.Sequence[str] = ["IsApplicationOwner"]

import asyncio
import typing

from hikari import errors
from yuyo import backoff

if typing.TYPE_CHECKING:
    from hikari import applications
    from hikari import traits as hikari_traits

    from tanjun import context
    from tanjun import traits


class IsApplicationOwner:
    __slots__: typing.Sequence[str] = ("_application", "_client", "_fetch_task", "_lock")

    def __init__(self) -> None:
        self._application: typing.Optional[applications.Application] = None
        self._client: typing.Optional[traits.Client] = None
        self._fetch_task: typing.Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()

    async def __call__(self, ctx: context.Context, /) -> bool:
        if ctx.client is not None:
            self._client = ctx.client

        return await self.check(ctx)

    @staticmethod
    async def _fetch_application(rest: hikari_traits.RESTAware, /) -> applications.Application:  # type: ignore[return]
        retry = backoff.Backoff()
        async for _ in retry:
            try:
                return await rest.rest.fetch_application()

            except errors.RateLimitedError as exc:
                retry.set_next_backoff(exc.retry_after)

            except errors.InternalServerError:
                continue

    async def _fetch_loop(self) -> None:
        while True:
            # Update the application every 30 minutes.
            await asyncio.sleep(1_800)
            if self._client is not None:
                try:
                    self._application = await self._fetch_application(self._client.rest)

                except errors.ForbiddenError:
                    pass

    async def _get_application(self, ctx: context.Context, /) -> applications.Application:
        if self._application is None:
            async with self._lock:
                # MYPY doesn't understand that a variable's scope might change during a yield.
                if self._application:
                    return self._application  # type: ignore[unreachable]

                self._application = await self._fetch_application(ctx.client.rest)

                if self._fetch_task is None:
                    self._fetch_task = asyncio.create_task(self._fetch_loop())

        return self._application

    async def check(self, ctx: context.Context, /) -> bool:
        application = await self._get_application(ctx)

        if not application.team and application.owner:
            return ctx.message.author.id == application.owner.id

        return bool(application.team and ctx.message.author.id in application.team.members)

    def close(self) -> None:
        if self._fetch_task is not None:
            self._fetch_task.cancel()
            self._fetch_task = None

    async def open(self, client: traits.Client, /) -> None:
        self.close()
        self._client = client
        self._fetch_task = asyncio.create_task(self._fetch_loop())

    async def update(self, *, rest: typing.Optional[hikari_traits.RESTAware] = None) -> None:
        if not rest and self._client:
            rest = self._client.rest

        elif not rest:
            raise ValueError("REST client must be provided when trying to update a closed application owner check.")

        self._application = await self._fetch_application(rest)
