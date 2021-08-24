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
"""Utility used for handling automatic back-off.

This can be used to cover cases such as hitting rate-limits and failed requests.
"""

from __future__ import annotations

__all__: typing.Sequence[str] = ["Backoff", "ErrorManager"]

import asyncio
import typing

from hikari.impl import rate_limits

if typing.TYPE_CHECKING:
    import types


ErrorManagerT = typing.TypeVar("ErrorManagerT", bound="ErrorManager")


class Backoff:
    """Used to exponentially backoff asynchronously.

    This class acts as an asynchronous iterator and can be iterated over to
    provide implicit backoff where for every iteration other than the first
    this will either back off for the time passed to `Backoff.set_next_backoff`
    if applicable or a time calculated exponentially.

    Other Parameters
    ----------------
    max_retries : typing.Optional[builtins.int]
        The maximum amount of times this should iterate for between resets.
        If left as `builtins.None` then this iterator will be unlimited.
        This must be greater than or equal to 1.
    base : builtins.float
        The base to use. Defaults to `2.0`.
    maximum : builtins.float
        The max value the backoff can be in a single iteration. Anything above
        this will be capped to this base value plus random jitter.
    jitter_multiplier : builtins.float
        The multiplier for the random jitter. Defaults to `1.0`.
        Set to `0` to disable jitter.
    initial_increment : builtins.int
        The initial increment to start at. Defaults to `0`.

    Raises
    ------
    ValueError
        If an `builtins.int` that's too big to be represented as a
        `builtins.float` or a non-finite value is passed in place of a field
        that's annotated as `builtins.float` or if `max_retries` is less than 1.

    Examples
    --------
    An example of using this class as an asynchronous iterator may look like
    the following

    ```py
    # While we can directly do `async for _ in Backoff()`, by assigning it to a
    # variable we allow ourself to provide a specific backoff time in some cases.
    backoff = Backoff()
    async for _ in backoff:
        try:
            message = await bot.rest.fetch_message(channel_id, message_id)
        except errors.RateLimitedError as exc:
            # If we have a specific backoff time then set it for the next iteration
            backoff.set_next_backoff(exc.retry_after)
        except errors.InternalServerError:
            # Else let the iterator calculate an exponential backoff before the next loop.
            pass
        else:
            # We need to break out of the iterator to make sure it doesn't backoff again.
            # Alternatively `Backoff.finish()` can be called to break out of the loop.
            break
    ```

    Alternatively you may want to explicitly call `Backoff.backoff`, a
    alternative of the previous example which uses `Backoff.backoff` may
    look like the following

    ```py
    backoff = Backoff()
    message: typing.Optional[messages.Message] = None
    while not message:
        try:
            message = await bot.rest.fetch_message(channel_id, message_id)
        except errors.RateLimitedError as exc:
            # If we have a specific backoff time then set it for the next iteration.
            await backoff.backoff(exc.retry_after)
        except errors.InternalServerError:
            # Else let the iterator calculate an exponential backoff before the next loop.
            await backoff.backoff()
    ```
    """

    __slots__ = ("_backoff", "_finished", "_max_retries", "_next_backoff", "_retries", "_started")

    def __init__(
        self,
        max_retries: typing.Optional[int] = None,
        *,
        base: float = 2.0,
        maximum: float = 64.0,
        jitter_multiplier: float = 1.0,
        initial_increment: int = 0,
    ) -> None:
        if max_retries is not None and max_retries < 1:
            raise ValueError("max_retries must be greater than 1")

        self._backoff = rate_limits.ExponentialBackOff(
            base=base, maximum=maximum, jitter_multiplier=jitter_multiplier, initial_increment=initial_increment
        )
        self._finished = False
        self._max_retries = max_retries
        self._next_backoff: typing.Optional[float] = None
        self._retries = 0
        self._started = False

    def __aiter__(self) -> Backoff:
        return self

    async def __anext__(self) -> None:
        if self._finished or self.is_depleted:
            self._finished = False
            raise StopAsyncIteration

        # We don't want to backoff on the first iteration.
        if not self._started:
            self._started = True
            return

        backoff_: float
        if self._next_backoff is None:
            backoff_ = next(self._backoff)
        else:
            backoff_ = self._next_backoff
            self._next_backoff = None

        self._retries += 1
        await asyncio.sleep(backoff_)

    @property
    def is_depleted(self) -> bool:
        """Whether "max_retries" has been reached.

        This can be used to workout whether the loop was explicitly broken out
        of using `Backoff.finish`/`break` or if it hit "max_retries".

        Returns
        -------
        bool
            If "max_retries" has been hit.
        """
        return self._max_retries is not None and self._max_retries == self._retries

    async def backoff(self, backoff_: typing.Optional[float], /) -> None:
        """Sleep for the provided backoff or for the next exponent.

        This provides an alternative to iterating over this class.

        Parameters
        ----------
        backoff_ : typing.Optional[float]
            The time this should backoff for. If left as `builtins.None` then
            this will back off for the last time provided with
            `Backoff.set_next_backoff` if available or the next exponential time.
        """
        self._started = True
        if backoff_ is None and self._next_backoff is not None:
            backoff_ = self._next_backoff
            self._next_backoff = None

        elif backoff_ is None:
            backoff_ = next(self._backoff)

        await asyncio.sleep(backoff_)

    def finish(self) -> None:
        """Mark the iterator as finished to break out of the current loop."""
        self._finished = True

    def reset(self) -> None:
        """Reset the backoff to it's original state to reuse it."""
        self._backoff.reset()
        self._finished = False
        self._next_backoff = None
        self._retries = 0
        self._started = False

    def set_next_backoff(self, backoff_: float, /) -> None:
        """Specify a backoff time for the next iteration or `Backoff.backoff` call.

        If this is called then the exponent won't be increased for this iteration.

        !!! note
            Calling this multiple times in a single iteration will overwrite any
            previously set next backoff.
        """
        # TODO: maximum?
        self._next_backoff = backoff_


class ErrorManager:
    """A context manager provided to allow for more concise error handling with `Backoff`.

    Other Parameters
    ----------------
    *rules : typing.Tuple[typing.Iterable[typing.Type[BaseException]], typing.Callable[[typing.Any], typing.Optional[bool]]]
        Rules to initiate this error context manager with.

        These are each a 2-length tuple where the tuple[0] is an
        iterable of types of the exceptions this rule should apply to
        and tuple[1] is the rule's callback function.

        The callback function will be called with the raised exception when it
        matches one of the passed exceptions for the relevant rule and may
        raise, return `builtins.True` to indicate that the current error should
        be raised outside of the context manager or
        `builtins.False`/`builtins.None` to suppress the current error.

    Examples
    --------
    The following is an example of using `ErrorManager` alongside `Backoff`
    in-order to handle the exceptions which may be raised while trying to
    reply to a message.

    ```py
    retry = Backoff()
    # Rules can either be passed to `ErrorManager`'s initiate as variable arguments
    # or one at a time to `ErrorManager.with_rule` through possibly chained-calls.
    error_handler = (
        # For the 1st rule we catch two errors which would indicate the bot
        # no-longer has access to the target channel and break out of the
        # retry loop using `Backoff.retry`.
        ErrorManager(((errors.NotFoundError, errors.ForbiddenError), lambda _: retry.finish()))
            # For the 2nd rule we catch rate limited errors and set their
            # `retry` value as the next backoff time before suppressing the
            # error to allow this to retry the request.
            .with_rule((errors.RateLimitedError,), lambda exc: retry.set_next_backoff(exc.retry_after))
            # For the 3rd rule we suppress the internal server error to allow
            # backoff to reach the next retry and exponentially backoff as we
            # don't have any specific retry time for this error.
            .with_rule((errors.InternalServerError,), lambda _: False)
    )
    async for _ in retry:
        # We entre this context manager each iteration to catch errors before
        # they cause us to break out of the `Backoff` loop.
        with error_handler:
            await message.respond("General Kenobi")
            # We need to break out of `retry` if this request succeeds.
            break
    ```
    """

    __slots__ = ("_rules",)

    def __init__(
        self,
        *rules: typing.Tuple[
            typing.Iterable[typing.Type[BaseException]], typing.Callable[[typing.Any], typing.Optional[bool]]
        ],
    ) -> None:
        self._rules = {(tuple(exceptions), callback) for exceptions, callback in rules}

    def __enter__(self) -> ErrorManager:
        return self

    def __exit__(
        self,
        exception_type: typing.Optional[typing.Type[BaseException]],
        exception: typing.Optional[BaseException],
        exception_traceback: typing.Optional[types.TracebackType],
    ) -> typing.Optional[bool]:
        if exception_type is None:
            return None

        assert exception is not None  # This shouldn't ever be None when exception_type isn't None.
        for rule, callback in self._rules:
            if issubclass(exception_type, rule):
                # For this context manager's rules we switch up how returns are handled to let the rules prevent
                # exceptions from being raised outside of the context by default by having `None` and `False` both
                # indicate don't re-raise (suppress) and `True` indicate that it should re-raise.
                return not callback(exception)

        return False

    def clear_rules(self) -> None:
        """Clear the rules registered with this handler."""
        self._rules.clear()

    def with_rule(
        self: ErrorManagerT,
        exceptions: typing.Iterable[typing.Type[BaseException]],
        result: typing.Callable[[typing.Any], typing.Optional[bool]],
    ) -> ErrorManagerT:
        """Add a rule to this exception context manager.

        Parameters
        ----------
        exceptions : typing.Iterable[typing.Type[builtins.BaseException]]
            An iterable of types of the exceptions this rule should apply to.
        result : typing.Callable[[typing.Any], typing.Optional[builtins.bool]]
            The function called with the raised exception when it matches one
            of the passed `exceptions`.
            This may raise, return `builtins.True` to indicate that the current
            error should be raised outside of the context manager or
            `builtins.False`/`builtins.None` to suppress the current error.

        Returns
        -------
        ErrorManager
            This returns the handler a rule was being added to in-order to
            allow for chained calls.
        """
        self._rules.add((tuple(exceptions), result))
        return self
