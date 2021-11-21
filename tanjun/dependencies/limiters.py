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
"""Cooldown and concurrency limiter dependencies and pre-execution hooks for commands."""
from __future__ import annotations

__all__: list[str] = [
    "AbstractCooldownManager",
    "BucketResource",
    "CooldownPreExecution",
    "InMemoryCooldownManager",
    "with_cooldown",
]

import abc
import asyncio
import datetime
import enum
import logging
import time
import typing

import hikari

from .. import abc as tanjun_abc
from .. import errors
from .. import hooks
from .. import injecting
from . import owners

if typing.TYPE_CHECKING:
    from collections import abc as collections

    _InMemoryCooldownManagerT = typing.TypeVar("_InMemoryCooldownManagerT", bound="InMemoryCooldownManager")

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun")

CommandT = typing.TypeVar("CommandT", bound="tanjun_abc.ExecutableCommand[typing.Any]")
"""Type variable indicating either `BaseSlashCommand` or `MessageCommand`."""


class AbstractCooldownManager(abc.ABC):
    """Interface used for managing command calldowns."""

    __slots__ = ()

    @abc.abstractmethod
    async def check_cooldown(
        self, bucket_id: str, ctx: tanjun_abc.Context, /, *, increment: bool = False
    ) -> typing.Optional[float]:
        """Check if a bucket is on cooldown for the provided context.

        Parameters
        ----------
        bucket_id : str
            The cooldown bucket to check.
        ctx : tanjun.abc.Context
            The context of the command.

        Other Parameters
        ----------------
        increment : bool
            Whether this cool should increment the bucket's use counter it
            isn't depleted.

        Returns
        -------
        typing.Optional[float]
            When this command will next be usable in the current context if its
            in cooldown else `None`.
        """

    @abc.abstractmethod
    async def increment_cooldown(self, bucket_id: str, ctx: tanjun_abc.Context, /) -> None:
        """Increment the cooldown of a cooldown bucket.

        Parameters
        ----------
        bucket_id : str
            The cooldown bucket's ID.
        ctx : tanjun.abc.Context
            The context of the command.
        """


class BucketResource(int, enum.Enum):
    """Resource target types used within command calldowns and concurrency limiters."""

    USER = 0
    """A per-user cooldown bucket."""

    MEMBER = 1
    """A per-guild member cooldown bucket.

    .. note::
        When executed in a DM this will be per-DM.
    """

    CHANNEL = 2
    """A per-channel cooldown bucket."""

    PARENT_CHANNEL = 3
    """A per-parent channel cooldown bucket.

    .. note::
        For DM channels this will be per-DM, for guild channels with no parents
        this'll be per-guild.
    """

    # CATEGORY = 4
    # """A per-category cooldown bucket.

    # .. note::
    #     For DM channels this will be per-DM, for guild channels with no parent
    #     category this'll be per-guild.
    # """

    TOP_ROLE = 5
    """A per-highest role cooldown bucket.

    .. note::
        When executed in a DM this will be per-DM, with this defaulting to
        targeting the @everyone role if they have no real roles.
    """

    GUILD = 6
    """A per-guild cooldown bucket.

    .. note::
        When executed in a DM this will be per-DM.
    """

    GLOBAL = 7
    """A global cooldown bucket."""


async def _get_ctx_target(ctx: tanjun_abc.Context, type_: BucketResource, /) -> hikari.Snowflake:
    if type_ is BucketResource.USER:
        return ctx.author.id

    if type_ is BucketResource.CHANNEL:
        return ctx.channel_id

    if type_ is BucketResource.PARENT_CHANNEL:
        if ctx.guild_id is None:
            return ctx.channel_id

        if channel := ctx.get_channel():
            return channel.parent_id or ctx.guild_id

        channel = await ctx.fetch_channel()
        assert isinstance(channel, hikari.TextableGuildChannel)
        return channel.parent_id or ctx.guild_id

    # if type_ is BucketResource.CATEGORY:
    #     if ctx.guild_id is None:
    #         return ctx.channel_id

    #     # This resource doesn't include threads so we can safely assume that the parent is a category
    #     if channel := ctx.get_channel():
    #         return channel.parent_id or channel.guild_id

    #     # TODO: threads
    #     channel = await ctx.fetch_channel()  # TODO: couldn't this lead to two requests per command? seems bad
    #     assert isinstance(channel, hikari.TextableGuildChannel)
    #     return channel.parent_id or channel.guild_id

    if type_ is BucketResource.TOP_ROLE:
        if not ctx.guild_id:
            return ctx.channel_id

        # If they don't have a member object but this is in a guild context then we'll have to assume they're
        # @everyone cause they might be a webhook or something.
        if not ctx.member or len(ctx.member.role_ids) <= 1:  # If they only have 1 role ID then this is @everyone.
            return ctx.guild_id

        roles = ctx.member.get_roles() or await ctx.member.fetch_roles()
        return next(iter(sorted(roles, key=lambda r: r.position, reverse=True))).id

    if type_ is BucketResource.GUILD:
        return ctx.guild_id or ctx.channel_id

    raise ValueError(f"Unexpected type {type_}")


class _Cooldown:
    __slots__ = ("counter", "will_reset_after", "resource")

    def __init__(self, resource: _BaseCooldownResource, /) -> None:
        self.counter = 0
        self.will_reset_after = time.monotonic() + resource.reset_after
        self.resource = resource

    def has_expired(self) -> bool:
        return time.monotonic() >= self.will_reset_after

    def increment(self) -> None:
        if self.counter == 0:
            self.will_reset_after = time.monotonic() + self.resource.reset_after

        elif (current_time := time.monotonic()) >= self.will_reset_after:
            self.counter = 0
            self.will_reset_after = current_time + self.resource.reset_after

        self.counter += 1

    def must_wait_until(self) -> typing.Optional[float]:
        if self.counter >= self.resource.limit and (time_left := self.will_reset_after - time.monotonic()) > 0:
            return time_left


class _BaseCooldownResource(abc.ABC):
    __slots__ = ("limit", "reset_after")

    def __init__(self, limit: int, reset_after: float) -> None:
        self.limit = limit
        self.reset_after = reset_after

    @abc.abstractmethod
    async def check(self, ctx: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        raise NotImplementedError

    @abc.abstractmethod
    async def increment(self, ctx: tanjun_abc.Context, /) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def cleanup(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self) -> _BaseCooldownResource:
        raise NotImplementedError


def _check_cooldown_mapping(
    resource: _BaseCooldownResource,
    mapping: dict[hikari.Snowflake, _Cooldown],
    target: hikari.Snowflake,
    increment: bool,
) -> typing.Optional[float]:
    cooldown = mapping.get(target)
    if increment:
        if cooldown:
            wait_until = cooldown.must_wait_until()

        else:
            cooldown = mapping[target] = _Cooldown(resource)
            wait_until = None

        if wait_until is None:
            cooldown.increment()

        return wait_until

    return cooldown.must_wait_until() if cooldown else None


class _CooldownBucket(_BaseCooldownResource):
    __slots__ = ("type", "mapping")

    def __init__(self, resource_type: BucketResource, limit: int, reset_after: float) -> None:
        super().__init__(limit, reset_after)
        self.type = resource_type
        self.mapping: dict[hikari.Snowflake, _Cooldown] = {}

    async def check(self, ctx: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        return _check_cooldown_mapping(self, self.mapping, await _get_ctx_target(ctx, self.type), increment)

    async def increment(self, ctx: tanjun_abc.Context, /) -> None:
        target = await _get_ctx_target(ctx, self.type)
        if not (cooldown := self.mapping.get(target)):
            cooldown = self.mapping[target] = _Cooldown(self)

        cooldown.increment()

    def cleanup(self) -> None:
        for target_id, cooldown in self.mapping.copy().items():
            if cooldown.has_expired():
                del self.mapping[target_id]

    def copy(self) -> _CooldownBucket:
        return _CooldownBucket(resource_type=self.type, limit=self.limit, reset_after=self.reset_after)


class _MemberCooldownResource(_BaseCooldownResource):
    __slots__ = ("dm_fallback", "mapping")

    def __init__(self, limit: int, reset_after: float) -> None:
        super().__init__(limit, reset_after)
        self.dm_fallback: dict[hikari.Snowflake, _Cooldown] = {}
        self.mapping: dict[hikari.Snowflake, dict[hikari.Snowflake, _Cooldown]] = {}

    async def check(self, ctx: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        if not ctx.guild_id:
            return _check_cooldown_mapping(self, self.dm_fallback, ctx.channel_id, increment)

        mapping = self.mapping.get(ctx.guild_id)
        if mapping is None and increment:
            self.mapping[ctx.guild_id] = {}
            mapping = self.mapping[ctx.guild_id]

        return _check_cooldown_mapping(self, mapping, ctx.author.id, increment) if mapping is not None else None

    async def increment(self, ctx: tanjun_abc.Context, /) -> None:
        if not ctx.guild_id:
            cooldown = self.dm_fallback.get(ctx.channel_id)
            if not cooldown:
                cooldown = self.dm_fallback[ctx.channel_id] = _Cooldown(self)

            return cooldown.increment()

        if guild_cooldowns := self.mapping.get(ctx.guild_id):
            cooldown = guild_cooldowns.get(ctx.author.id)
            if not cooldown:
                cooldown = guild_cooldowns[ctx.author.id] = _Cooldown(self)

        else:
            cooldown = _Cooldown(self)
            self.mapping[ctx.guild_id] = {ctx.author.id: cooldown}

        cooldown.increment()

    def cleanup(self) -> None:
        for guild_id, mapping in self.mapping.copy().items():
            for bucket_id, cooldown in mapping.copy().items():
                if cooldown.has_expired():
                    del mapping[bucket_id]

            if not mapping:
                del self.mapping[guild_id]

        for bucket_id, cooldown in self.dm_fallback.copy().items():
            if cooldown.has_expired():
                del self.dm_fallback[bucket_id]

    def copy(self) -> _MemberCooldownResource:
        return _MemberCooldownResource(self.limit, self.reset_after)


class _GlobalCooldownResource(_BaseCooldownResource):
    __slots__ = ("bucket",)

    def __init__(self, limit: int, reset_after: float) -> None:
        super().__init__(limit, reset_after)
        self.bucket = _Cooldown(self)

    async def check(self, _: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        wait_for = self.bucket.must_wait_until()
        if increment and wait_for is None:
            self.bucket.increment()

        return wait_for

    async def increment(self, _: tanjun_abc.Context, /) -> None:
        self.bucket.increment()

    def cleanup(self) -> None:
        pass

    def copy(self) -> _GlobalCooldownResource:
        return _GlobalCooldownResource(self.limit, self.reset_after)


class InMemoryCooldownManager(AbstractCooldownManager):
    """In-memory standard implementation of `AbstractCooldownManager`.

    Examples
    --------
    `InMemoryCooldownManager.set_bucket` may be used to set a cooldown for a
    specific bucket:

    ```py
    (
        InMemoryCooldownManager()
        # Set the default bucket template to a per-user 10 uses per-60 seconds cooldown.
        .set_bucket("default", tanjun.BucketResource.USER, 10, 60)
        # Set the "moderation" bucket to a per-guild 100 uses per-5 minutes cooldown.
        .set_bucket("moderation", tanjun.BucketResource.GUILD, 100, datetime.timedelta(minutes=5))
        .set_bucket()
        # add_to_client will setup the cooldown manager (setting it as an
        # injected dependency and registering callbacks to manage it).
        .add_to_client(client)
    )
    """

    __slots__ = ("_buckets", "_default_bucket_template", "_gc_loop")

    def __init__(self) -> None:
        self._buckets: dict[str, _BaseCooldownResource] = {}
        self._default_bucket_template: _BaseCooldownResource = _CooldownBucket(BucketResource.USER, 2, 5)
        self._gc_loop: typing.Optional[asyncio.Task[None]] = None

    def _get_or_default(self, bucket_id: str, /) -> _BaseCooldownResource:
        if bucket := self._buckets.get(bucket_id):
            return bucket

        _LOGGER.info("No route found for {bucket_id}, falling back to 'default' bucket.")
        bucket = self._buckets[bucket_id] = self._default_bucket_template.copy()
        return bucket

    async def _gc(self) -> None:
        while True:
            await asyncio.sleep(10)
            for bucket in self._buckets.values():
                bucket.cleanup()

    def add_to_client(self, client: injecting.InjectorClient, /) -> None:
        """Add this cooldown manager to a tanjun client.

        .. note::
            This registers the manager as a type dependency and manages opening
            and closing the manager based on the client's life cycle.

        Parameters
        ----------
        client : tanjun.abc.Client
            The client to add this cooldown manager to.
        """
        client.set_type_dependency(AbstractCooldownManager, self)
        # TODO: the injection client should be upgraded to the abstract Client.
        assert isinstance(client, tanjun_abc.Client)
        client.add_client_callback(tanjun_abc.ClientCallbackNames.STARTING, self.open)
        client.add_client_callback(tanjun_abc.ClientCallbackNames.CLOSING, self.close)
        if client.is_alive:
            assert client.loop is not None
            self.open(_loop=client.loop)

    async def check_cooldown(
        self, bucket_id: str, ctx: tanjun_abc.Context, /, *, increment: bool = False
    ) -> typing.Optional[float]:
        if increment:
            return await self._get_or_default(bucket_id).check(ctx, increment=increment)

        bucket = self._buckets.get(bucket_id)
        return await bucket.check(ctx, increment=increment) if bucket else None

    def increment_cooldown(
        self, bucket_id: str, ctx: tanjun_abc.Context, /
    ) -> collections.Coroutine[typing.Any, typing.Any, None]:
        return self._get_or_default(bucket_id).increment(ctx)

    def close(self) -> None:
        """Stop the event manager.

        Raises
        ------
        RuntimeError
            If the event manager is not running.
        """
        if not self._gc_loop:
            raise RuntimeError("Cooldown manager is not active")

        self._gc_loop.cancel()
        self._gc_loop = None

    def open(self, *, _loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the event manager.

        Raises
        ------
        RuntimeError
            If the event manager is already running.
            If called in a thread with no running event loop.
        """
        if self._gc_loop:
            raise RuntimeError("Cooldown manager is already running")

        self._gc_loop = (_loop or asyncio.get_running_loop()).create_task(self._gc())

    def set_bucket(
        self: _InMemoryCooldownManagerT,
        bucket_id: str,
        resource_type: BucketResource,
        limit: int,
        reset_after: typing.Union[int, float, datetime.timedelta],
    ) -> _InMemoryCooldownManagerT:
        """Set the cooldown for a specific bucket.

        Parameters
        ----------
        bucket_id : str
            The ID of the bucket to set the cooldown for.

            ..  note::
                "default" is a special bucket that is as a template used when
                the bucket ID isn't found.
        resource_type : tanjun.BucketResource
            The type of resource to use for the cooldown.
        limit : int
            The number of uses per cooldown period.
        reset_after : int, float, datetime.timedelta
            The cooldown period.

        Returns
        -------
        Self
            This cooldown manager to allow chaining.

        Raises
        ------
        ValueError
            If an invalid resource type is given.
            If reset_after or limit are negative, 0 or invalid.
            if limit is less 0 or negative.
        """
        if isinstance(reset_after, datetime.timedelta):
            reset_after = reset_after.total_seconds()
        else:
            reset_after = float(reset_after)

        if reset_after <= 0:
            raise ValueError("reset_after must be greater than 0 seconds")

        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        if resource_type is BucketResource.MEMBER:
            bucket = _MemberCooldownResource(limit, reset_after)

        elif resource_type is BucketResource.GLOBAL:
            bucket = _GlobalCooldownResource(limit, reset_after)

        else:
            bucket = _CooldownBucket(resource_type, limit, reset_after)

        self._buckets[bucket_id] = bucket
        if bucket_id == "default":
            self._default_bucket_template = bucket.copy()

        return self


class CooldownPreExecution:
    """Pre-execution hook used to manage a command's cooldowns.

    To avoid race-conditions this handles both erroring when the bucket is hit
    instead and incrementing the bucket's use counter.

    Parameters
    ----------
    bucket_id : str
        The cooldown bucket's ID.

    Other Parameters
    ----------------
    error_message : str
        The error message to send in response as a command error if the check fails.

        Defaults to f"Please wait {cooldown:0.2f} seconds before using this command again".
    owners_exempt : bool
        Whether owners should be exempt from the cooldown.

        Defaults to `True`.
    """

    __slots__ = ("_bucket_id", "_error_message", "_owners_exempt")

    def __init__(
        self,
        bucket_id: str,
        /,
        *,
        error_message: str = "Please wait {cooldown:0.2f} seconds before using this command again",
        owners_exempt: bool = True,
    ) -> None:
        self._bucket_id = bucket_id
        self._error_message = error_message
        self._owners_exempt = owners_exempt

    async def __call__(
        self,
        ctx: tanjun_abc.Context,
        cooldowns: AbstractCooldownManager = injecting.inject(type=AbstractCooldownManager),
        # TODO: default to None for the owner check as this should only require
        # the owner check dependency if owner_exempt is True.
        owner_check: owners.AbstractOwnerCheck = injecting.inject(type=owners.AbstractOwnerCheck),
    ) -> None:
        if self._owners_exempt and await owner_check.check_ownership(ctx.client, ctx.author):
            return

        if wait_for := await cooldowns.check_cooldown(self._bucket_id, ctx, increment=True):
            raise errors.CommandError(self._error_message.format(cooldown=wait_for))


def with_cooldown(
    bucket_id: str,
    /,
    *,
    error_message: str = "Please wait {cooldown:0.2f} seconds before using this command again",
    owners_exempt: bool = True,
) -> typing.Callable[[CommandT], CommandT]:
    """Add a pre-execution hook used to manage a command's cooldown through a decorator call.

    .. warning::
        Cooldowns will only work if there's a setup injected `AbstractCooldownManager`
        dependency with `InMemoryCooldownManager` being usable as a standard in-memory
        cooldown manager.

    Parameters
    ----------
    bucket_id : str
        The cooldown bucket's ID.

    Other Parameters
    ----------------
    error_message : str
        The error message to send in response as a command error if the check fails.

        Defaults to f"Please wait {cooldown:0.2f} seconds before using this command again".
    owners_exempt : bool
        Whether owners should be exempt from the cooldown.

        Defaults to `True`.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]
        A decorator that adds a `CooldownPreExecution` hook to the command.
    """

    def decorator(command: CommandT, /) -> CommandT:
        hooks_ = command.hooks
        if not hooks_:
            hooks_ = hooks.AnyHooks()
            command.set_hooks(hooks_)

        hooks_.add_pre_execution(
            CooldownPreExecution(bucket_id, error_message=error_message, owners_exempt=owners_exempt)
        )
        return command

    return decorator
