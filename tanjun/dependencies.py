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
"""Default dependency classes used within Tanjun and their abstract interfaces."""
from __future__ import annotations

__all__: list[str] = [
    "AbstractCooldownManager",
    "AbstractOwnerCheck",
    "cache_callback",
    "cached_inject",
    "CommandT",
    "CooldownPreExecution",
    "CooldownResource",
    "LazyConstant",
    "InMemoryCooldownManager",
    "inject_lc",
    "make_lc_resolver",
    "OwnerCheck",
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

from . import abc as tanjun_abc
from . import errors
from . import hooks
from . import injecting

if typing.TYPE_CHECKING:
    import contextlib
    from collections import abc as collections

    _InMemoryCooldownManagerT = typing.TypeVar("_InMemoryCooldownManagerT", bound="InMemoryCooldownManager")
    _LazyConstantT = typing.TypeVar("_LazyConstantT", bound="LazyConstant[typing.Any]")

_T = typing.TypeVar("_T")
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


class CooldownResource(int, enum.Enum):
    """Cooldown resource types."""

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

    CATEGORY = 4
    """A per-category cooldown bucket.

    .. note::
        For DM channels this will be per-DM, for guild channels with no parent
        category this'll be per-guild.
    """

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


class _Cooldown:
    __slots__ = ("counter", "will_reset_after", "resource")

    def __init__(self, resource: _BaseCooldownResource, /) -> None:
        self.counter = 0
        self.will_reset_after = -1.0
        self.resource = resource

    def has_expired(self) -> bool:
        return time.monotonic() >= self.will_reset_after

    def increment(self) -> None:
        if self.counter == 0:
            self.will_reset_after = time.monotonic() + self.resource.reset_after

        elif (current_time := time.monotonic()) >= self.will_reset_after:
            self.counter == 0
            self.will_reset_after = current_time + self.resource.reset_after

        self.counter += 1

    def must_wait_until(self) -> typing.Optional[float]:
        if self.counter >= self.resource.limit and (time_left := self.will_reset_after - time.monotonic()) > 0:
            return time_left


class _BaseCooldownResource:
    __slots__ = ("limit", "reset_after")

    def __init__(self, limit: int, reset_after: typing.Union[int, float, datetime.timedelta]) -> None:
        self.limit = limit
        if isinstance(reset_after, datetime.timedelta):
            self.reset_after = reset_after.total_seconds()
        else:
            self.reset_after = float(reset_after)

    async def check(self, ctx: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        raise NotImplementedError

    async def increment(self, ctx: tanjun_abc.Context, /) -> None:
        raise NotImplementedError

    def cleanup(self) -> None:
        raise NotImplementedError

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
        if not cooldown:
            cooldown = mapping[target] = _Cooldown(resource)

        wait_until = cooldown.must_wait_until()
        if wait_until is not None:
            cooldown.increment()

        return wait_until

    return cooldown.must_wait_until() if cooldown else None


class _CooldownBucket(_BaseCooldownResource):
    __slots__ = ("type", "mapping")

    def __init__(
        self,
        resource_type: CooldownResource,
        limit: int,
        reset_after: typing.Union[int, float, datetime.timedelta],
    ) -> None:
        super().__init__(limit, reset_after)
        self.type = resource_type
        self.mapping: dict[hikari.Snowflake, _Cooldown] = {}

    async def check(self, ctx: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        return _check_cooldown_mapping(self, self.mapping, await self._get_target(ctx), increment)

    async def increment(self, ctx: tanjun_abc.Context, /) -> None:
        target = await self._get_target(ctx)
        if not (cooldown := self.mapping.get(target)):
            cooldown = self.mapping[target] = _Cooldown(self)

        cooldown.increment()

    async def _get_target(self, ctx: tanjun_abc.Context, /) -> hikari.Snowflake:
        if self.type is CooldownResource.USER:
            return ctx.author.id

        if self.type is CooldownResource.CHANNEL:
            return ctx.channel_id

        if self.type is CooldownResource.PARENT_CHANNEL:
            if ctx.guild_id is None:
                return ctx.channel_id

            if channel := ctx.get_channel():
                return channel.parent_id or channel.guild_id

            channel = await ctx.fetch_channel()  # TODO: couldn't this lead to two requests per command? seems bad
            assert isinstance(channel, hikari.TextableGuildChannel)
            return channel.parent_id or channel.guild_id

        if self.type is CooldownResource.CATEGORY:
            if ctx.guild_id is None:
                return ctx.channel_id

            # This resource doesn't include threads so we can safely assume that the parent is a category
            if channel := ctx.get_channel():
                return channel.parent_id or channel.guild_id

            # TODO: threads
            channel = await ctx.fetch_channel()  # TODO: couldn't this lead to two requests per command? seems bad
            assert isinstance(channel, hikari.TextableGuildChannel)
            return channel.parent_id or channel.guild_id

        if self.type is CooldownResource.TOP_ROLE:
            if not ctx.member:
                return ctx.channel_id

            if not ctx.member.role_ids:
                return ctx.member.guild_id

            # TODO: couldn't this lead to two requests per command? seems bad
            roles = ctx.member.get_roles() or await ctx.member.fetch_roles()
            return next(iter(sorted(roles, key=lambda r: r.position, reverse=True))).id

        if self.type is CooldownResource.GUILD:
            return ctx.guild_id or ctx.channel_id

        raise RuntimeError(f"Unexpected type {self.type}")

    def cleanup(self) -> None:
        for bucket_id, cooldown in self.mapping.copy().items():
            if cooldown.has_expired():
                del self.mapping[bucket_id]

    def copy(self) -> _CooldownBucket:
        return _CooldownBucket(resource_type=self.type, limit=self.limit, reset_after=self.reset_after)


class _MemberCooldownResource(_BaseCooldownResource):
    __slots__ = ("dm_fallback", "mapping")

    def __init__(
        self,
        limit: int,
        reset_after: typing.Union[int, float, datetime.timedelta],
    ) -> None:
        super().__init__(limit, reset_after)
        self.dm_fallback: dict[hikari.Snowflake, _Cooldown]
        self.mapping: dict[hikari.Snowflake, dict[hikari.Snowflake, _Cooldown]] = {}

    async def check(self, ctx: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        if not ctx.guild_id:
            return _check_cooldown_mapping(self, self.dm_fallback, ctx.author.id, increment)

        mapping = self.mapping.get(ctx.guild_id)
        if mapping is None and increment:
            self.mapping[ctx.guild_id] = {}
            mapping = self.mapping[ctx.guild_id]

        return _check_cooldown_mapping(self, mapping, ctx.author.id, increment) if mapping is not None else None

    async def increment(self, ctx: tanjun_abc.Context, /) -> None:
        if not ctx.guild_id:
            cooldown = self.dm_fallback.get(ctx.author.id)
            if not cooldown:
                cooldown = self.dm_fallback[ctx.author.id] = _Cooldown(self)

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
    __slots__ = ("_bucket",)

    def __init__(
        self,
        limit: int,
        reset_after: typing.Union[int, float, datetime.timedelta],
    ) -> None:
        super().__init__(limit, reset_after)
        self._bucket = _Cooldown(self)

    async def check(self, _: tanjun_abc.Context, /, *, increment: bool = False) -> typing.Optional[float]:
        wait_for = self._bucket.must_wait_until()
        if increment and wait_for is not None:
            self._bucket.increment()

        return wait_for

    async def increment(self, _: tanjun_abc.Context, /) -> None:
        self._bucket.increment()

    def cleanup(self) -> None:
        pass

    def copy(self) -> _GlobalCooldownResource:
        return _GlobalCooldownResource(self.limit, self.reset_after)


class InMemoryCooldownManager(AbstractCooldownManager):
    """In-memory standard implementation of `AbstractCooldownManager`."""

    __slots__ = ("_buckets", "_default_bucket_template", "_gc_loop")

    def __init__(self) -> None:
        self._buckets: dict[str, _BaseCooldownResource] = {}
        self._default_bucket_template: _BaseCooldownResource = _CooldownBucket(CooldownResource.USER, 5, 10)
        self._gc_loop: typing.Optional[asyncio.Task[None]] = None

    def _get_bucket(self, bucket_id: str, /) -> _BaseCooldownResource:
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

    def _on_starting(
        self,
        client: tanjun_abc.Client = injecting.inject(type=tanjun_abc.Client),
        injection_client: injecting.InjectorClient = injecting.inject(type=injecting.InjectorClient),
    ) -> None:
        # If this isn't registered as a type dependency then it was presumably
        # replaced and shouldn't start
        if (_ := injection_client.get_type_dependency(AbstractCooldownManager)) is not self:
            client.remove_client_callback(tanjun_abc.ClientCallbackNames.STARTING, self.open)
            try:
                client.remove_client_callback(tanjun_abc.ClientCallbackNames.CLOSING, self.close)
            except (KeyError, ValueError):
                pass

        else:
            self.open()

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
        if client.loop:
            self.open(_loop=client.loop)

    def check_cooldown(
        self, bucket_id: str, ctx: tanjun_abc.Context, /, *, increment: bool = False
    ) -> collections.Coroutine[typing.Any, typing.Any, typing.Optional[float]]:
        return self._get_bucket(bucket_id).check(ctx, increment=increment)

    def increment_cooldown(
        self, bucket_id: str, ctx: tanjun_abc.Context, /
    ) -> collections.Coroutine[typing.Any, typing.Any, None]:
        return self._get_bucket(bucket_id).increment(ctx)

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
        """
        if self._gc_loop:
            raise RuntimeError("Cooldown manager is already running")

        self._gc_loop = (_loop or asyncio.get_event_loop()).create_task(self._gc())

    def set_bucket(
        self: _InMemoryCooldownManagerT,
        bucket_id: str,
        resource_type: CooldownResource,
        limit: int,
        reset_after: typing.Union[int, float, datetime.timedelta],
    ) -> _InMemoryCooldownManagerT:
        if resource_type is CooldownResource.MEMBER:
            bucket = _MemberCooldownResource(limit, reset_after)

        elif resource_type is CooldownResource.GLOBAL:
            bucket = _GlobalCooldownResource(limit, reset_after)

        else:
            bucket = _CooldownBucket(resource_type, limit, reset_after)

        self._buckets[bucket_id] = bucket
        if bucket_id == "default":
            self._default_bucket_template = bucket.copy()

        return self


class AbstractOwnerCheck(abc.ABC):
    """Interface used to check if a user is deemed to be the bot's "owner"."""

    __slots__ = ()

    @abc.abstractmethod
    async def check_ownership(self, client: tanjun_abc.Client, user: hikari.User, /) -> bool:
        """Check whether this object is owned by the given object.

        Parameters
        ----------
        client : tanjun.abc.Client
            The Tanjun client this check is being called by.
        user : hikari.User
            The user to check ownership for.

        Returns
        -------
        bool
            Whether the bot is owned by the provided user.
        """


class _CachedValue(typing.Generic[_T]):
    __slots__ = ("_expire_after", "_last_called", "_lock", "_result")

    def __init__(self, *, expire_after: typing.Optional[datetime.timedelta]) -> None:
        self._expire_after = expire_after.total_seconds() if expire_after else None
        self._last_called: typing.Optional[float] = None
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Optional[_T] = None

    @property
    def _has_expired(self) -> bool:
        return self._expire_after is not None and (
            not self._last_called or self._expire_after <= (time.monotonic() - self._last_called)
        )

    async def acquire(self, callback: collections.Callable[[], collections.Awaitable[_T]], /) -> _T:
        if self._result is not None and not self._has_expired:
            return self._result

        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._result is not None and not self._has_expired:
                return self._result

            self._result = await callback()
            self._last_called = time.monotonic()
            # This is set to None afterwards to ensure that it isn't persisted between loops.
            self._lock = None
            return self._result


class OwnerCheck(AbstractOwnerCheck):
    """Default implementation of the owner check interface.

    .. warning::
        `fallback_to_application` is only possible when the REST client
        is bound to a Bot token.
    """

    __slots__ = ("_expire_after", "_fallback_to_application", "_owner_ids", "_value")

    def __init__(
        self,
        *,
        expire_after: datetime.timedelta = datetime.timedelta(minutes=5),
        fallback_to_application: bool = True,
        owners: typing.Optional[hikari.SnowflakeishSequence[hikari.User]] = None,
    ) -> None:
        """Initiate a new owner check dependency.

        Other Parameters
        ----------------
        expire_after : datetime.timedelta
            The amount of time to cache application owner data for.

            This defaults to 5 minutes and is only applicable if `rest` is also
            passed.
        fallback_to_application : bool
            Whether this check should fallback to checking the application's owners
            if the user isn't in `owners.

            This only works when the bot's rest client is bound to a Bot token.
        owners : typing.Optional[hikari.SnowflakeishSequence[hikari.User]]
            Sequence of objects and IDs of the users that are allowed to use the
            bot's "owners".
        """
        self._expire_after = expire_after
        self._fallback_to_application = fallback_to_application
        self._owner_ids = {hikari.Snowflake(id_) for id_ in owners} if owners else set[hikari.Snowflake]()
        self._value = _CachedValue[hikari.Application](expire_after=expire_after)

    async def check_ownership(self, client: tanjun_abc.Client, user: hikari.User, /) -> bool:
        if user.id in self._owner_ids:
            return True

        if not self._fallback_to_application:
            return False

        if client.rest.token_type is not hikari.TokenType.BOT:
            _LOGGER.warning(
                "Owner checks cannot fallback to application owners when bound to an OAuth2 "
                "client credentials token and may always fail unless bound to a Bot token."
            )
            return False

        application = await self._value.acquire(client.rest.fetch_application)
        return user.id in application.team.members if application.team else user.id == application.owner.id


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
        owner_check: AbstractOwnerCheck = injecting.inject(type=AbstractOwnerCheck),
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

    .. note::
        The cooldown's bucket should be configured on the client's injected
        cooldown manager impl with the standard manager being
        `InMemoryCooldownManager`.

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


class LazyConstant(typing.Generic[_T]):
    """Injected type used to hold and generate lazy constants.

    .. note::
        To easily resolve this type use `inject_lc`.
    """

    __slots__ = ("_callback", "_lock", "_value")

    def __init__(self, callback: collections.Callable[..., tanjun_abc.MaybeAwaitableT[_T]], /) -> None:
        """Initiate a new lazy constant.

        Parameters
        ----------
        callback : collections.abc.Callable[..., tanjun.abc.MaybeAwaitable[_T]]
            Callback used to resolve this to a constant value.

            This supports dependency injection and may either be sync or asynchronous.
        """
        self._callback = injecting.CallbackDescriptor(callback)
        self._lock: typing.Optional[asyncio.Lock] = None
        self._value: typing.Optional[_T] = None

    @property
    def callback(self) -> injecting.CallbackDescriptor[_T]:
        """Descriptor of the callback used to get this constant's initial value."""
        return self._callback

    def get_value(self) -> typing.Optional[_T]:
        """Get the value of this constant if set, else `None`."""
        return self._value

    def reset(self: _LazyConstantT) -> _LazyConstantT:
        """Clear the internally stored value."""
        self._value = None
        return self

    def set_value(self: _LazyConstantT, value: _T, /) -> _LazyConstantT:
        """Set the constant value.

        Parameters
        ----------
        value : _T
            The value to set.

        Raises
        ------
        RuntimeError
            If the constant has already been set.
        """
        if self._value is not None:
            raise RuntimeError("Constant value already set.")

        self._value = value
        self._lock = None
        return self

    def acquire(self) -> contextlib.AbstractAsyncContextManager[typing.Any]:
        """Acquire this lazy constant to's asynchronous lock.

        This is used to ensure that the value is only generated once
        and should be kept acquired until `LazyConstant.set_value` is called.

        Returns
        -------
        contextlib.AbstractAsyncContextManager[typing.Any]
            Context manager that can be used to acquire the lock.
        """
        if not self._lock:
            # Error if this is called outside of a running event loop.
            asyncio.get_running_loop()
            self._lock = asyncio.Lock()

        return self._lock


def make_lc_resolver(type_: type[_T], /) -> collections.Callable[..., collections.Awaitable[_T]]:
    """Make an injected callback which resolves a LazyConstant.

    Notes
    -----
    * This is internally used by `inject_lc`.
    * For this to work, a `LazyConstant` must've been set as a type
      dependency for the passed `type_`.

    Parameters
    ----------
    type_ : type[_T]
        The type of the constant to resolve.

    Returns
    -------
    collections.abc.Callable[..., collections.abc.Awaitable[_T]]
        An injected callback used to resolve the LazyConstant.
    """

    async def resolve(
        constant: LazyConstant[_T] = injecting.inject(type=LazyConstant[type_]),
        ctx: injecting.AbstractInjectionContext = injecting.inject(type=injecting.AbstractInjectionContext),
    ) -> _T:
        """Resolve a lazy constant."""
        if (value := constant.get_value()) is not None:
            return value

        async with constant.acquire():
            if (value := constant.get_value()) is not None:
                return value

            result = await constant.callback.resolve(ctx)
            constant.set_value(result)
            return result

    return resolve


def inject_lc(type_: type[_T], /) -> _T:
    """Make a LazyConstant injector.

    This acts like `tanjun.injecting.inject` and the result of it
    should also be assigned to a parameter's default to be used.

    .. note::
        For this to work, a `LazyConstant` must've been set as a type
        dependency for the passed `type_`.

    Parameters
    ----------
    type_ : type[_T]
        The type of the constant to resolve.

    Returns
    -------
    tanjun.injecting.Injected[_T]
        Injector used to resolve the LazyConstant.

    Example
    -------
    ```py
    @component.with_command
    @tanjun.as_message_command
    async def command(
        ctx: tanjun.abc.MessageCommand,
        application: hikari.Application = tanjun.inject_lc(hikari.Application)
    ) -> None:
        raise NotImplementedError

    ...

    async def resolve_app(
        client: tanjun.abc.Client = tanjun.inject(type=tanjun.abc.Client)
    ) -> hikari.Application:
        raise NotImplementedError

    tanjun.Client.from_gateway_bot(...).set_type_dependency(
        tanjun.LazyConstant[hikari.Application] = tanjun.LazyConstant(resolve_app)
    )
    ```
    """
    return injecting.inject(callback=make_lc_resolver(type_))


async def fetch_my_user(
    client: tanjun_abc.Client = injecting.inject(type=tanjun_abc.Client),
) -> hikari.OwnUser:
    """Fetch the current user from the client's cache or rest client.

    .. note::
        This is used in the standard `LazyConstant[hikari.OwnUser]`
        dependency.

    Parameters
    ----------
    client : tanjun.abc.Client
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

    if client.rest.token_type is not hikari.TokenType.BOT:
        raise RuntimeError("Cannot fetch current user with a REST client that's bound to a client credentials token")

    return await client.rest.fetch_my_user()


def set_standard_dependencies(client: injecting.InjectorClient, /) -> None:
    """Set the standard dependencies for Tanjun.

    Parameters
    ----------
    client: tanjun.injecting.InjectorClient
        The injector client to set the standard dependencies on.
    """
    InMemoryCooldownManager().add_to_client(client)
    (
        (
            client.set_type_dependency(AbstractOwnerCheck, OwnerCheck()).set_type_dependency(
                LazyConstant[hikari.OwnUser], LazyConstant(fetch_my_user)
            )
        )
    )


class _CacheCallback(typing.Generic[_T]):
    __slots__ = ("_callback", "_expire_after", "_last_called", "_lock", "_result")

    def __init__(
        self, callback: injecting.CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta]
    ) -> None:
        self._callback = injecting.CallbackDescriptor(callback)
        self._expire_after = expire_after.total_seconds() if expire_after else None
        self._last_called: typing.Optional[float] = None
        self._lock: typing.Optional[asyncio.Lock] = None
        self._result: typing.Union[_T, injecting.Undefined] = injecting.UNDEFINED

    @property
    def _has_expired(self) -> bool:
        return self._expire_after is not None and (
            not self._last_called or self._expire_after <= (time.monotonic() - self._last_called)
        )

    async def __call__(
        self,
        # Positional arg(s) may be guaranteed under some contexts so we want to pass those through.
        *args: typing.Any,
        ctx: injecting.AbstractInjectionContext = injecting.inject(type=injecting.AbstractInjectionContext),
    ) -> _T:
        if self._result is not injecting.UNDEFINED and not self._has_expired:
            assert not isinstance(self._result, injecting.Undefined)
            return self._result

        if not self._lock:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._result is not injecting.UNDEFINED and not self._has_expired:
                assert not isinstance(self._result, injecting.Undefined)
                return self._result

            self._result = await self._callback.resolve(ctx, *args)
            self._last_called = time.monotonic()
            # This is set to None afterwards to ensure that it isn't persisted between loops.
            self._lock = None
            return self._result


def cache_callback(
    callback: injecting.CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta] = None
) -> collections.Callable[..., collections.Awaitable[_T]]:
    """Cache the result of a callback within a dependency injection context.

    .. note::
        This is internally used by `cached_inject`.

    Parameters
    ----------
    callback : CallbackSig[_T]
        The callback to cache the result of.

    Other Parameters
    ----------------
    expire_after : typing.Optional[datetime.timedelta]
        The amount of time to cache the result for.

        Leave this as `None` to cache for the runtime of the application.

    Returns
    -------
    Callable[..., Awaitable[_T]]
        A callback which will cache the result of the given callback after the
        first call.
    """
    return _CacheCallback(callback, expire_after=expire_after)


def cached_inject(
    callback: injecting.CallbackSig[_T], /, *, expire_after: typing.Optional[datetime.timedelta] = None
) -> _T:
    """Inject a callback with caching.

    This acts like `tanjun.injecting.inject` and the result of it
    should also be assigned to a parameter's default to be used.

    Parameters
    ----------
    callback : CallbackSig[_T]
        The callback to inject.

    Other Parameters
    ----------------
    expire_after : typing.Optional[datetime.timedelta]
        The amount of time to cache the result for.

        Leave this as `None` to cache for the runtime of the application.

    Returns
    -------
    tanjun.injecting.Injected[_T]
        Injector used to resolve the cached callback.

    Example
    -------
    ```py
    async def resolve_database(
        client: tanjun.abc.Client = tanjun.inject(type=tanjun.abc.Client)
    ) -> Database:
        raise NotImplementedError

    @tanjun.as_message_command("command name")
    async def command(
        ctx: tanjun.abc.Context, db: Database = tanjun.cached_inject(resolve_database)
    ) -> None:
        raise NotImplementedError
    """
    return injecting.inject(callback=cache_callback(callback, expire_after=expire_after))
