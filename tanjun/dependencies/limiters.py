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
"""Command cooldown and concurrency limiters."""
from __future__ import annotations

__all__: list[str] = [
    "AbstractConcurrencyLimiter",
    "AbstractCooldownManager",
    "BucketResource",
    "ConcurrencyPostExecution",
    "ConcurrencyPreExecution",
    "CooldownPreExecution",
    "InMemoryConcurrencyLimiter",
    "InMemoryCooldownManager",
    "with_concurrency_limit",
    "with_cooldown",
]

import abc
import asyncio
import datetime
import enum
import logging
import typing
from collections import abc as collections

import alluka
import hikari

from .. import _internal
from .. import abc as tanjun
from .. import conversion
from .. import errors
from .. import hooks
from .._internal import localisation
from . import async_cache
from . import locales
from . import owners

if typing.TYPE_CHECKING:
    from typing_extensions import Self

    _CommandT = typing.TypeVar("_CommandT", bound="tanjun.ExecutableCommand[typing.Any]")
    _OtherCommandT = typing.TypeVar("_OtherCommandT", bound="tanjun.ExecutableCommand[typing.Any]")

_LOGGER: typing.Final[logging.Logger] = logging.getLogger("hikari.tanjun")


class AbstractCooldownManager(abc.ABC):
    """Interface used for managing command calldowns."""

    __slots__ = ()

    @abc.abstractmethod
    async def check_cooldown(
        self, bucket_id: str, ctx: tanjun.Context, /, *, increment: bool = False
    ) -> typing.Optional[datetime.datetime]:
        """Check if a bucket is on cooldown for the provided context.

        Parameters
        ----------
        bucket_id
            The cooldown bucket to check.
        ctx
            The context of the command.
        increment
            Whether this call should increment the bucket's use counter if
            it isn't depleted.

        Returns
        -------
        datetime.datetime | None
            When this command will next be usable for the provided context
            if it's in cooldown else [None][].
        """

    @abc.abstractmethod
    async def increment_cooldown(self, bucket_id: str, ctx: tanjun.Context, /) -> None:
        """Increment the cooldown of a cooldown bucket.

        Parameters
        ----------
        bucket_id
            The cooldown bucket's ID.
        ctx
            The context of the command.
        """


class AbstractConcurrencyLimiter(abc.ABC):
    """Interface used for limiting command concurrent usage."""

    __slots__ = ()

    @abc.abstractmethod
    async def try_acquire(self, bucket_id: str, ctx: tanjun.Context, /) -> bool:
        """Try to acquire a concurrency lock on a bucket.

        Parameters
        ----------
        bucket_id
            The concurrency bucket to acquire.
        ctx
            The context to acquire this resource lock with.

        Returns
        -------
        bool
            Whether the lock was acquired.
        """

    @abc.abstractmethod
    async def release(self, bucket_id: str, ctx: tanjun.Context, /) -> None:
        """Release a concurrency lock on a bucket."""


class BucketResource(int, enum.Enum):
    """Resource target types used within command calldowns and concurrency limiters."""

    USER = 0
    """A per-user resource bucket."""

    MEMBER = 1
    """A per-guild member resource bucket.

    When executed in a DM this will be per-DM.
    """

    CHANNEL = 2
    """A per-channel resource bucket."""

    PARENT_CHANNEL = 3
    """A per-parent channel resource bucket.

    For DM channels this will be per-DM, for guild channels with no parents
    this'll be per-guild.
    """

    # CATEGORY = 4
    # """A per-category resource bucket.

    # For DM channels this will be per-DM, for guild channels with no parent
    # category this'll be per-guild.
    # """

    TOP_ROLE = 5
    """A per-highest role resource bucket.

    When executed in a DM this will be per-DM, with this defaulting to
    targeting the @everyone role if they have no real roles.
    """

    GUILD = 6
    """A per-guild resource bucket.

    When executed in a DM this will be per-DM.
    """

    GLOBAL = 7
    """A global resource bucket."""


async def _try_get_role(
    cache: async_cache.SfCache[hikari.Role], role_id: hikari.Snowflake
) -> typing.Optional[hikari.Role]:
    try:
        return await cache.get(role_id)
    except async_cache.EntryNotFound:
        pass


async def _get_ctx_target(ctx: tanjun.Context, type_: BucketResource, /) -> hikari.Snowflake:
    if type_ is BucketResource.USER:
        return ctx.author.id

    if type_ is BucketResource.CHANNEL:
        return ctx.channel_id

    if type_ is BucketResource.PARENT_CHANNEL:
        if ctx.guild_id is None:
            return ctx.channel_id

        if cached_channel := ctx.get_channel():
            return cached_channel.parent_id or ctx.guild_id

        channel_cache = ctx.get_type_dependency(async_cache.SfCache[hikari.PermissibleGuildChannel])
        if channel_cache and (channel_ := await channel_cache.get(ctx.channel_id, default=None)):
            return channel_.parent_id or ctx.guild_id

        thread_cache = ctx.get_type_dependency(async_cache.SfCache[hikari.GuildThreadChannel])
        if thread_cache and (channel_ := await thread_cache.get(ctx.channel_id, default=None)):
            return channel_.parent_id

        channel = await ctx.fetch_channel()
        assert isinstance(channel, hikari.GuildChannel)
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

        # If they don't have a member object but this is in a guild context then we'll have to assume they
        # only have @everyone since they might be a webhook or something.
        if not ctx.member or len(ctx.member.role_ids) <= 1:  # If they only have 1 role ID then this is @everyone.
            return ctx.guild_id

        roles: collections.Iterable[hikari.Role] = ctx.member.get_roles()
        try_rest = not roles
        if try_rest and (role_cache := ctx.get_type_dependency(async_cache.SfCache[hikari.Role])):
            try:
                roles = filter(None, [await _try_get_role(role_cache, role_id) for role_id in ctx.member.role_ids])
                try_rest = False

            except async_cache.CacheMissError:
                pass

        if try_rest:
            roles = await ctx.member.fetch_roles()

        return next(iter(sorted(roles, key=lambda r: r.position, reverse=True))).id

    if type_ is BucketResource.GUILD:
        return ctx.guild_id or ctx.channel_id

    raise ValueError(f"Unexpected type {type_}")


_CooldownT = typing.TypeVar("_CooldownT", bound="_Cooldown")


def _now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class _Cooldown:
    __slots__ = ("counter", "limit", "reset_after", "resets_at")

    def __init__(self, *, limit: int, reset_after: datetime.timedelta) -> None:
        self.counter = 0
        self.limit = limit
        self.reset_after = reset_after
        self.resets_at = _now() + reset_after

    def has_expired(self) -> bool:
        # Expiration doesn't actually matter for cases where the limit is -1.
        return _now() >= self.resets_at

    def increment(self) -> Self:
        # A limit of -1 is special cased to mean no limit, so there's no need to increment the counter.
        if self.limit == -1:
            return self

        if self.counter == 0:
            self.resets_at = _now() + self.reset_after

        elif (current_time := _now()) >= self.resets_at:
            self.counter = 0
            self.resets_at = current_time + self.reset_after

        if self.counter < self.limit:
            self.counter += 1

        return self

    def must_wait_until(self) -> typing.Optional[datetime.datetime]:
        # A limit of -1 is special cased to mean no limit, so we don't need to wait.
        if self.limit == -1:
            return None

        if self.counter >= self.limit and self.resets_at > _now():
            return self.resets_at


class _InnerResourceProto(typing.Protocol):
    def has_expired(self) -> bool:
        raise NotImplementedError


_InnerResourceT = typing.TypeVar("_InnerResourceT", bound=_InnerResourceProto)


class _BaseResource(abc.ABC, typing.Generic[_InnerResourceT]):
    __slots__ = ("make_resource",)

    def __init__(self, make_resource: _InnerResourceSig[_InnerResourceT]) -> None:
        self.make_resource = make_resource

    @abc.abstractmethod
    def cleanup(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self) -> _BaseResource[_InnerResourceT]:
        raise NotImplementedError

    @abc.abstractmethod
    async def into_inner(self, ctx: tanjun.Context, /) -> _InnerResourceT:
        raise NotImplementedError

    @abc.abstractmethod
    async def try_into_inner(self, ctx: tanjun.Context, /) -> typing.Optional[_InnerResourceT]:
        raise NotImplementedError


_InnerResourceSig = collections.Callable[[], _InnerResourceT]


class _FlatResource(_BaseResource[_InnerResourceT]):
    __slots__ = ("mapping", "resource")

    def __init__(self, resource: BucketResource, make_resource: _InnerResourceSig[_InnerResourceT]) -> None:
        super().__init__(make_resource)
        self.mapping: dict[hikari.Snowflake, _InnerResourceT] = {}
        self.resource = resource

    async def try_into_inner(self, ctx: tanjun.Context, /) -> typing.Optional[_InnerResourceT]:
        return self.mapping.get(await _get_ctx_target(ctx, self.resource))

    async def into_inner(self, ctx: tanjun.Context, /) -> _InnerResourceT:
        target = await _get_ctx_target(ctx, self.resource)
        if resource := self.mapping.get(target):
            return resource

        resource = self.mapping[target] = self.make_resource()
        return resource

    def cleanup(self) -> None:
        for target_id, resource in self.mapping.copy().items():
            if resource.has_expired():
                del self.mapping[target_id]

    def copy(self) -> _FlatResource[_InnerResourceT]:
        return _FlatResource(self.resource, self.make_resource)


class _MemberResource(_BaseResource[_InnerResourceT]):
    __slots__ = ("dm_fallback", "mapping")

    def __init__(self, make_resource: _InnerResourceSig[_InnerResourceT]) -> None:
        super().__init__(make_resource)
        self.dm_fallback: dict[hikari.Snowflake, _InnerResourceT] = {}
        self.mapping: dict[hikari.Snowflake, dict[hikari.Snowflake, _InnerResourceT]] = {}

    async def into_inner(self, ctx: tanjun.Context, /) -> _InnerResourceT:
        if not ctx.guild_id:
            if resource := self.dm_fallback.get(ctx.channel_id):
                return resource

            resource = self.dm_fallback[ctx.channel_id] = self.make_resource()
            return resource

        if (guild_mapping := self.mapping.get(ctx.guild_id)) is not None:
            if resource := guild_mapping.get(ctx.author.id):
                return resource

            resource = guild_mapping[ctx.author.id] = self.make_resource()
            return resource

        resource = self.make_resource()
        self.mapping[ctx.guild_id] = {ctx.author.id: resource}
        return resource

    async def try_into_inner(self, ctx: tanjun.Context, /) -> typing.Optional[_InnerResourceT]:
        if not ctx.guild_id:
            return self.dm_fallback.get(ctx.channel_id)

        if guild_mapping := self.mapping.get(ctx.guild_id):
            return guild_mapping.get(ctx.author.id)

    def cleanup(self) -> None:
        for guild_id, mapping in self.mapping.copy().items():
            for bucket_id, resource in mapping.copy().items():
                if resource.has_expired():
                    del mapping[bucket_id]

            if not mapping:
                del self.mapping[guild_id]

        for bucket_id, resource in self.dm_fallback.copy().items():
            if resource.has_expired():
                del self.dm_fallback[bucket_id]

    def copy(self) -> _MemberResource[_InnerResourceT]:
        return _MemberResource(self.make_resource)


class _GlobalResource(_BaseResource[_InnerResourceT]):
    __slots__ = ("bucket",)

    def __init__(self, make_resource: _InnerResourceSig[_InnerResourceT]) -> None:
        super().__init__(make_resource)
        self.bucket = make_resource()

    async def try_into_inner(self, _: tanjun.Context, /) -> typing.Optional[_InnerResourceT]:
        return self.bucket

    async def into_inner(self, _: tanjun.Context, /) -> _InnerResourceT:
        return self.bucket

    def cleanup(self) -> None:
        pass

    def copy(self) -> _GlobalResource[_InnerResourceT]:
        return _GlobalResource(self.make_resource)


def _to_bucket(
    resource: BucketResource, make_resource: _InnerResourceSig[_InnerResourceT]
) -> _BaseResource[_InnerResourceT]:
    if resource is BucketResource.MEMBER:
        return _MemberResource(make_resource)

    if resource is BucketResource.GLOBAL:
        return _GlobalResource(make_resource)

    return _FlatResource(resource, make_resource)


class InMemoryCooldownManager(AbstractCooldownManager):
    """In-memory standard implementation of [AbstractCooldownManager][tanjun.dependencies.AbstractCooldownManager].

    Examples
    --------
    [InMemoryCooldownManager.set_bucket][tanjun.dependencies.InMemoryCooldownManager.set_bucket]
    may be used to set the cooldown for a specific bucket:

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
    ```
    """

    __slots__ = ("_buckets", "_default_bucket_template", "_gc_task")

    def __init__(self) -> None:
        self._buckets: dict[str, _BaseResource[_Cooldown]] = {}
        self._default_bucket_template: _BaseResource[_Cooldown] = _FlatResource(
            BucketResource.USER, lambda: _Cooldown(limit=2, reset_after=datetime.timedelta(seconds=5))
        )
        self._gc_task: typing.Optional[asyncio.Task[None]] = None

    def _get_or_default(self, bucket_id: str, /) -> _BaseResource[_Cooldown]:
        if bucket := self._buckets.get(bucket_id):
            return bucket

        _LOGGER.info("No cooldown found for %r, falling back to 'default' bucket", bucket_id)
        bucket = self._buckets[bucket_id] = self._default_bucket_template.copy()
        return bucket

    async def _gc(self) -> None:
        while True:
            await asyncio.sleep(10)
            for bucket in self._buckets.values():
                bucket.cleanup()

    def add_to_client(self, client: tanjun.Client, /) -> None:
        """Add this cooldown manager to a tanjun client.

        !!! note
            This registers the manager as a type dependency and manages opening
            and closing the manager based on the client's life cycle.

        Parameters
        ----------
        client
            The client to add this cooldown manager to.
        """
        client.set_type_dependency(AbstractCooldownManager, self)
        client.add_client_callback(tanjun.ClientCallbackNames.STARTING, self.open)
        client.add_client_callback(tanjun.ClientCallbackNames.CLOSING, self.close)
        if client.is_alive:
            assert client.loop is not None
            self.open(_loop=client.loop)

    async def check_cooldown(
        self, bucket_id: str, ctx: tanjun.Context, /, *, increment: bool = False
    ) -> typing.Optional[datetime.datetime]:
        # <<inherited docstring from AbstractCooldownManager>>.
        bucket: typing.Optional[_Cooldown]
        if increment:
            bucket = await self._get_or_default(bucket_id).into_inner(ctx)
            if cooldown := bucket.must_wait_until():
                return cooldown

            bucket.increment()
            return None

        if (resource := self._buckets.get(bucket_id)) and (bucket := await resource.try_into_inner(ctx)):
            return bucket.must_wait_until()

    async def increment_cooldown(self, bucket_id: str, ctx: tanjun.Context, /) -> None:
        # <<inherited docstring from AbstractCooldownManager>>.
        (await self._get_or_default(bucket_id).into_inner(ctx)).increment()

    def close(self) -> None:
        """Stop the cooldown manager.

        Raises
        ------
        RuntimeError
            If the cooldown manager is not running.
        """
        if not self._gc_task:
            raise RuntimeError("Cooldown manager is not active")

        self._gc_task.cancel()
        self._gc_task = None

    def open(self, *, _loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the cooldown manager.

        Raises
        ------
        RuntimeError
            If the cooldown manager is already running.
            If called in a thread with no running event loop.
        """
        if self._gc_task:
            raise RuntimeError("Cooldown manager is already running")

        self._gc_task = (_loop or asyncio.get_running_loop()).create_task(self._gc())

    def disable_bucket(self, bucket_id: str, /) -> Self:
        """Disable a cooldown bucket.

        This will stop the bucket from ever hitting a cooldown and also
        prevents the bucket from defaulting.

        !!! note
            "default" is a special `bucket_id` which is used as a template for
            unknown bucket IDs.

        Parameters
        ----------
        bucket_id
            The bucket to disable.

        Returns
        -------
        Self
            This cooldown manager to allow for chaining.
        """
        # A limit of -1 is special cased to mean no limit and reset_after is ignored in this scenario.
        bucket = self._buckets[bucket_id] = _GlobalResource(
            lambda: _Cooldown(limit=-1, reset_after=datetime.timedelta(-1))
        )
        if bucket_id == "default":
            self._default_bucket_template = bucket.copy()

        return self

    def set_bucket(
        self,
        bucket_id: str,
        resource: BucketResource,
        limit: int,
        reset_after: typing.Union[int, float, datetime.timedelta],
        /,
    ) -> Self:
        """Set the cooldown for a specific bucket.

        !!! note
            "default" is a special `bucket_id` which is used as a template for
            unknown bucket IDs.

        Parameters
        ----------
        bucket_id
            The ID of the bucket to set the cooldown for.
        resource
            The type of resource to target for the cooldown.
        limit
            The number of uses per cooldown period.
        reset_after
            The cooldown period.

        Returns
        -------
        Self
            The cooldown manager to allow call chaining.

        Raises
        ------
        ValueError
            If an invalid resource type is given.
            If reset_after or limit are negative, 0 or invalid.
            if limit is less 0 or negative.
        """
        if not isinstance(reset_after, datetime.timedelta):
            reset_after = datetime.timedelta(seconds=reset_after)

        if reset_after <= datetime.timedelta():
            raise ValueError("reset_after must be greater than 0 seconds")

        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        bucket = self._buckets[bucket_id] = _to_bucket(
            BucketResource(resource), lambda: _Cooldown(limit=limit, reset_after=reset_after)
        )
        if bucket_id == "default":
            self._default_bucket_template = bucket.copy()

        return self


class CooldownPreExecution:
    """Pre-execution hook used to manage a command's cooldowns.

    To avoid race-conditions this handles both erroring when the bucket is hit
    instead and incrementing the bucket's use counter.
    """

    __slots__ = ("_bucket_id", "_error", "_error_message", "_owners_exempt", "__weakref__")

    def __init__(
        self,
        bucket_id: str,
        /,
        *,
        error: typing.Optional[collections.Callable[[str, datetime.datetime], Exception]] = None,
        error_message: typing.Union[
            str, collections.Mapping[str, str]
        ] = "This command is currently in cooldown. Try again {cooldown}.",
        owners_exempt: bool = True,
    ) -> None:
        """Initialise a pre-execution cooldown command hook.

        Parameters
        ----------
        bucket_id
            The cooldown bucket's ID.
        error
            Callback used to create a custom error to raise if the check fails.

            This should two arguments one of type [str][] and [datetime.datetime][]
            where the first is the limiting bucket's ID and the second is when said
            bucket can be used again.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if the check fails.

            This supports [localisation][] and uses the check name
            `"tanjun.cooldown"` for global overrides.
        owners_exempt
            Whether owners should be exempt from the cooldown.
        """
        self._bucket_id = bucket_id
        self._error = error
        self._error_message = localisation.MaybeLocalised("error_message", error_message)
        self._owners_exempt = owners_exempt

    async def __call__(
        self,
        ctx: tanjun.Context,
        cooldowns: alluka.Injected[AbstractCooldownManager],
        *,
        localiser: typing.Optional[locales.AbstractLocaliser] = None,
        owner_check: alluka.Injected[typing.Optional[owners.AbstractOwners]],
    ) -> None:
        if self._owners_exempt:
            if not owner_check:
                _LOGGER.info("No `AbstractOwners` dependency found, disabling owner exemption for cooldown check")
                self._owners_exempt = False

            elif await owner_check.check_ownership(ctx.client, ctx.author):
                return

        if wait_until := await cooldowns.check_cooldown(self._bucket_id, ctx, increment=True):
            if self._error:
                raise self._error(self._bucket_id, wait_until) from None

            wait_until_repr = conversion.from_datetime(wait_until, style="R")
            message = self._error_message.localise(ctx, localiser, "check", "tanjun.cooldown", cooldown=wait_until_repr)
            raise errors.CommandError(message)


def with_cooldown(
    bucket_id: str,
    /,
    *,
    error: typing.Optional[collections.Callable[[str, datetime.datetime], Exception]] = None,
    error_message: typing.Union[
        str, collections.Mapping[str, str]
    ] = "This command is currently in cooldown. Try again {cooldown}.",
    follow_wrapped: bool = False,
    owners_exempt: bool = True,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a pre-execution hook used to manage a command's cooldown through a decorator call.

    !!! warning
        Cooldowns will only work if there's a setup injected
        [AbstractCooldownManager][tanjun.dependencies.InMemoryCooldownManager] dependency with
        [InMemoryCooldownManager][tanjun.dependencies.InMemoryCooldownManager]
        being usable as a standard in-memory cooldown manager.

    Parameters
    ----------
    bucket_id
        The cooldown bucket's ID.
    error
        Callback used to create a custom error to raise if the check fails.

        This should two arguments one of type [str][] and [datetime.datetime][]
        where the first is the limiting bucket's ID and the second is when said
        bucket can be used again.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if the check fails.

        This supports [localisation][] and uses the check name
        `"tanjun.cooldown"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.
    owners_exempt
        Whether owners should be exempt from the cooldown.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A decorator that adds a [CooldownPreExecution][tanjun.dependencies.CooldownPreExecution]
        hook to the command.
    """
    pre_execution = CooldownPreExecution(
        bucket_id, error=error, error_message=error_message, owners_exempt=owners_exempt
    )

    def decorator(command: _OtherCommandT, /, *, _recursing: bool = False) -> _OtherCommandT:
        hooks_ = command.hooks
        if not hooks_:
            hooks_ = hooks.AnyHooks()
            command.set_hooks(hooks_)

        hooks_.add_pre_execution(pre_execution)
        if follow_wrapped and not _recursing:
            for wrapped in _internal.collect_wrapped(command):
                decorator(wrapped, _recursing=True)

        return command

    return decorator


class _ConcurrencyLimit:
    __slots__ = ("counter", "limit")

    def __init__(self, limit: int) -> None:
        self.counter = 0
        self.limit = limit

    def acquire(self) -> bool:
        if self.counter < self.limit:
            self.counter += 1
            return True

        # A limit of -1 means unlimited so we don't need to keep count.
        if self.limit == -1:
            return True

        return False

    def release(self) -> None:
        if self.counter > 0:
            self.counter -= 1
            return

        # A limit of -1 means unlimited so we don't need to keep count.
        if self.limit == -1:
            return

        raise RuntimeError("Cannot release a limit that has not been acquired, this should never happen")

    def has_expired(self) -> bool:
        # Expiration doesn't actually matter for cases where the limit is -1.
        return self.counter == 0


class InMemoryConcurrencyLimiter(AbstractConcurrencyLimiter):
    """In-memory standard implementation of [AbstractConcurrencyLimiter][tanjun.dependencies.AbstractConcurrencyLimiter].

    Examples
    --------
    [InMemoryConcurrencyLimiter.set_bucket][tanjun.dependencies.InMemoryConcurrencyLimiter.set_bucket]
    may be used to set the concurrency limits for a specific bucket:

    ```py
    (
        InMemoryConcurrencyLimiter()
        # Set the default bucket template to 10 concurrent uses of the command per-user.
        .set_bucket("default", tanjun.BucketResource.USER, 10)
        # Set the "moderation" bucket with a limit of 5 concurrent uses per-guild.
        .set_bucket("moderation", tanjun.BucketResource.GUILD, 5)
        .set_bucket()
        # add_to_client will setup the concurrency manager (setting it as an
        # injected dependency and registering callbacks to manage it).
        .add_to_client(client)
    )
    ```
    """

    __slots__ = ("_acquiring_ctxs", "_buckets", "_default_bucket_template", "_gc_task")

    def __init__(self) -> None:
        self._acquiring_ctxs: dict[tuple[str, tanjun.Context], _ConcurrencyLimit] = {}
        self._buckets: dict[str, _BaseResource[_ConcurrencyLimit]] = {}
        self._default_bucket_template: _BaseResource[_ConcurrencyLimit] = _FlatResource(
            BucketResource.USER, lambda: _ConcurrencyLimit(limit=1)
        )
        self._gc_task: typing.Optional[asyncio.Task[None]] = None

    async def _gc(self) -> None:
        while True:
            await asyncio.sleep(10)
            for bucket in self._buckets.values():
                bucket.cleanup()

    def add_to_client(self, client: tanjun.Client, /) -> None:
        """Add this concurrency manager to a tanjun client.

        !!! note
            This registers the manager as a type dependency and manages opening
            and closing the manager based on the client's life cycle.

        Parameters
        ----------
        client
            The client to add this concurrency manager to.
        """
        client.set_type_dependency(AbstractConcurrencyLimiter, self)
        client.add_client_callback(tanjun.ClientCallbackNames.STARTING, self.open)
        client.add_client_callback(tanjun.ClientCallbackNames.CLOSING, self.close)
        if client.is_alive:
            assert client.loop is not None
            self.open(_loop=client.loop)

    def close(self) -> None:
        """Stop the concurrency manager.

        Raises
        ------
        RuntimeError
            If the concurrency manager is not running.
        """
        if not self._gc_task:
            raise RuntimeError("Concurrency manager is not active")

        self._gc_task.cancel()
        self._gc_task = None

    def open(self, *, _loop: typing.Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the concurrency manager.

        Raises
        ------
        RuntimeError
            If the concurrency manager is already running.
            If called in a thread with no running event loop.
        """
        if self._gc_task:
            raise RuntimeError("Concurrency manager is already running")

        self._gc_task = (_loop or asyncio.get_running_loop()).create_task(self._gc())

    async def try_acquire(self, bucket_id: str, ctx: tanjun.Context, /) -> bool:
        # <<inherited docstring from AbstractConcurrencyLimiter>>.
        bucket = self._buckets.get(bucket_id)
        if not bucket:
            _LOGGER.info("No concurrency limit found for %r, falling back to 'default' bucket", bucket_id)
            bucket = self._buckets[bucket_id] = self._default_bucket_template.copy()

        # incrementing a bucket multiple times for the same context could lead
        # to weird edge cases based on how we internally track this, so we
        # internally de-duplicate this.
        elif (bucket_id, ctx) in self._acquiring_ctxs:
            return True  # This won't ever be the case if it just had to make a new bucket, hence the elif.

        if result := (limit := await bucket.into_inner(ctx)).acquire():
            self._acquiring_ctxs[(bucket_id, ctx)] = limit

        return result

    async def release(self, bucket_id: str, ctx: tanjun.Context, /) -> None:
        # <<inherited docstring from AbstractConcurrencyLimiter>>.
        if limit := self._acquiring_ctxs.pop((bucket_id, ctx), None):
            limit.release()

    def disable_bucket(self, bucket_id: str, /) -> Self:
        """Disable a concurrency limit bucket.

        This will stop the bucket from ever hitting a concurrency limit
        and also prevents the bucket from defaulting.

        !!! note
            "default" is a special `bucket_id` which is used as a template for
            unknown bucket IDs.

        Parameters
        ----------
        bucket_id
            The bucket to disable.

        Returns
        -------
        Self
            This concurrency manager to allow for chaining.
        """
        bucket = self._buckets[bucket_id] = _GlobalResource(lambda: _ConcurrencyLimit(limit=-1))
        if bucket_id == "default":
            self._default_bucket_template = bucket.copy()

        return self

    def set_bucket(self, bucket_id: str, resource: BucketResource, limit: int, /) -> Self:
        """Set the concurrency limit for a specific bucket.

        !!! note
            "default" is a special `bucket_id` which is used as a template for
            unknown bucket IDs.

        Parameters
        ----------
        bucket_id
            The ID of the bucket to set the concurrency limit for.
        resource
            The type of resource to target for the concurrency limit.
        limit
            The maximum number of concurrent uses to allow.

        Returns
        -------
        Self
            The concurrency manager to allow call chaining.

        Raises
        ------
        ValueError
            If an invalid resource type is given.
            if limit is less 0 or negative.
        """
        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        bucket = self._buckets[bucket_id] = _to_bucket(BucketResource(resource), lambda: _ConcurrencyLimit(limit=limit))
        if bucket_id == "default":
            self._default_bucket_template = bucket.copy()

        return self


class ConcurrencyPreExecution:
    """Pre-execution hook used to acquire a bucket concurrency limiter.

    !!! note
        For a concurrency limiter to work properly, both
        [ConcurrencyPreExecution][tanjun.dependencies.ConcurrencyPreExecution]
        and [ConcurrencyPostExecution][tanjun.dependencies.ConcurrencyPostExecution]
        hooks must be registered for a command scope.
    """

    __slots__ = ("_bucket_id", "_error", "_error_message", "__weakref__")

    def __init__(
        self,
        bucket_id: str,
        /,
        *,
        error: typing.Optional[collections.Callable[[str], Exception]] = None,
        error_message: typing.Union[
            str, collections.Mapping[str, str]
        ] = "This resource is currently busy; please try again later.",
    ) -> None:
        """Initialise a concurrency pre-execution hook.

        Parameters
        ----------
        bucket_id
            The concurrency limit bucket's ID.
        error
            Callback used to create a custom error to raise if the check fails.

            This should two one [str][] argument which is the limiting bucket's ID.

            This takes priority over `error_message`.
        error_message
            The error message to send in response as a command error if this fails
            to acquire the concurrency limit.

            This supports [localisation][] and uses the check name
            `"tanjun.concurrency"` for global overrides.
        """
        self._bucket_id = bucket_id
        self._error = error
        self._error_message = localisation.MaybeLocalised("error_message", error_message)

    async def __call__(
        self,
        ctx: tanjun.Context,
        limiter: alluka.Injected[AbstractConcurrencyLimiter],
        localiser: typing.Optional[locales.AbstractLocaliser] = None,
    ) -> None:
        if not await limiter.try_acquire(self._bucket_id, ctx):
            if self._error:
                raise self._error(self._bucket_id) from None

            message = self._error_message.localise(ctx, localiser, "check", "tanjun.concurrency")
            raise errors.CommandError(message) from None


class ConcurrencyPostExecution:
    """Post-execution hook used to release a bucket concurrency limiter.

    !!! note
        For a concurrency limiter to work properly, both
        [ConcurrencyPreExecution][tanjun.dependencies.ConcurrencyPreExecution]
        and [ConcurrencyPostExecution][tanjun.dependencies.ConcurrencyPostExecution]
        hooks must be registered for a command scope.
    """

    __slots__ = ("_bucket_id", "__weakref__")

    def __init__(self, bucket_id: str, /) -> None:
        """Initialise a concurrency post-execution hook.

        Parameters
        ----------
        bucket_id
            The concurrency limit bucket's ID.
        """
        self._bucket_id = bucket_id

    async def __call__(
        self,
        ctx: tanjun.Context,
        limiter: alluka.Injected[AbstractConcurrencyLimiter],
    ) -> None:
        await limiter.release(self._bucket_id, ctx)


def with_concurrency_limit(
    bucket_id: str,
    /,
    *,
    error: typing.Optional[collections.Callable[[str], Exception]] = None,
    error_message: typing.Union[
        str, collections.Mapping[str, str]
    ] = "This resource is currently busy; please try again later.",
    follow_wrapped: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add the hooks used to manage a command's concurrency limit through a decorator call.

    !!! warning
        Concurrency limiters will only work if there's a setup injected
        [AbstractConcurrencyLimiter][tanjun.dependencies.AbstractConcurrencyLimiter] dependency with
        [InMemoryConcurrencyLimiter][tanjun.dependencies.InMemoryConcurrencyLimiter]
        being usable as a standard in-memory concurrency manager.

    Parameters
    ----------
    bucket_id
        The concurrency limit bucket's ID.
    error
        Callback used to create a custom error to raise if the check fails.

        This should two one [str][] argument which is the limiting bucket's ID.

        This takes priority over `error_message`.
    error_message
        The error message to send in response as a command error if this fails
        to acquire the concurrency limit.

        This supports [localisation][] and uses the check name
        `"tanjun.concurrency"` for global overrides.
    follow_wrapped
        Whether to also add this check to any other command objects this
        command wraps in a decorator call chain.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.ExecutableCommand], tanjun.abc.ExecutableCommand]
        A decorator that adds the concurrency limiter hooks to a command.
    """
    pre_execution = ConcurrencyPreExecution(bucket_id, error=error, error_message=error_message)
    post_execution = ConcurrencyPostExecution(bucket_id)

    def decorator(command: _OtherCommandT, /, *, _recursing: bool = False) -> _OtherCommandT:
        hooks_ = command.hooks
        if not hooks_:
            hooks_ = hooks.AnyHooks()
            command.set_hooks(hooks_)

        hooks_.add_pre_execution(pre_execution).add_post_execution(post_execution)
        if follow_wrapped and not _recursing:
            for wrapped in _internal.collect_wrapped(command):
                decorator(wrapped, _recursing=True)

        return command

    return decorator
