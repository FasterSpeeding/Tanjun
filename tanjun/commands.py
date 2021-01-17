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

__all__: typing.Sequence[str] = ["Command", "CommandGroup"]

import typing

from hikari import errors as hikari_errors
from yuyo import backoff

from tanjun import errors
from tanjun import hooks as hooks_
from tanjun import traits
from tanjun import utilities


class FoundCommand(traits.FoundCommand):
    __slots__: typing.Sequence[str] = ("command", "name", "prefix")

    def __init__(self, command_: traits.ExecutableCommand, name: str, /) -> None:
        self.command = command_
        self.name = name


class Command(traits.ExecutableCommand):
    __slots__: typing.Sequence[str] = (
        "_checks",
        "_component",
        "_function",
        "hooks",
        "_metadata",
        "_names",
        "parent",
        "parser",
    )

    def __init__(
        self,
        function: traits.CommandFunctionT,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        metadata: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
        parser: typing.Optional[traits.Parser] = None,
    ) -> None:
        self._checks = set(checks) if checks else set()
        self._component: typing.Optional[traits.Component] = None
        self._function = function
        self.hooks: traits.Hooks = hooks or hooks_.Hooks()
        self._metadata = metadata or {}
        self._names = {name, *names}
        self.parent: typing.Optional[traits.ExecutableCommandGroup] = None
        self.parser = parser

    def __repr__(self) -> str:
        return f"Command <{self._names}>"

    @property
    def checks(self) -> typing.AbstractSet[traits.CheckT]:
        return frozenset(self._checks)

    @property
    def component(self) -> typing.Optional[traits.Component]:
        return self._component

    @property
    def function(self) -> traits.CommandFunctionT:
        return self._function

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._metadata

    @property
    def names(self) -> typing.AbstractSet[str]:
        return frozenset(self._names)

    def add_check(self, check: traits.CheckT, /) -> None:
        self._checks.add(check)

    def remove_check(self, check: traits.CheckT, /) -> None:
        self._checks.remove(check)

    def with_check(self, check: traits.CheckT, /) -> traits.CheckT:
        self.add_check(check)
        return check

    async def check_context(
        self, ctx: traits.Context, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[traits.FoundCommand]:
        if found := next(self.check_name(ctx.content[len(name_prefix) :].lstrip()), None):
            if await utilities.gather_checks(utilities.await_if_async(check, ctx) for check in self._checks):
                yield found

    def add_name(self, name: str, /) -> None:
        self._names.add(name)

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        for own_name in self._names:
            # Here we enforce that a name must either be at the end of content or be followed by a space. This helps
            # avoid issues with ambiguous naming where a command with the names "name" and "names" may sometimes hit
            # the former before the latter when triggered with the latter, leading to the command potentially being
            # inconsistently parsed.
            if name.startswith(own_name) and (name == own_name or name[len(own_name)] == " "):
                yield FoundCommand(self, own_name)
                break

    def remove_name(self, name: str, /) -> None:
        self._names.remove(name)

    def bind_client(self, client: traits.Client, /) -> None:
        if self.parser:
            self.parser.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        pass

    async def execute(
        self, ctx: traits.Context, /, *, hooks: typing.Optional[typing.MutableSet[traits.Hooks]] = None
    ) -> bool:
        try:
            if await self.hooks.trigger_pre_execution(ctx, hooks=hooks) is False:
                return True

            if self.parser is not None:
                args, kwargs = await self.parser.parse(ctx)

            else:
                args = []
                kwargs = {}

            await self._function(ctx, *args, **kwargs)

        except errors.CommandError as exc:
            if not exc.message:
                return True

            response = exc.message if len(exc.message) <= 2000 else exc.message[:1997] + "..."
            retry = backoff.Backoff(max_retries=5, maximum=2)
            # TODO: preemptive cache based permission checks before throwing to the REST gods.
            async for _ in retry:
                try:
                    await ctx.message.respond(content=response)

                except (hikari_errors.RateLimitedError, hikari_errors.RateLimitTooLongError) as retry_error:
                    if retry_error.retry_after > 4:
                        raise

                    retry.set_next_backoff(retry_error.retry_after)  # TODO: check if this is too large.

                except hikari_errors.InternalServerError:
                    continue

                except (hikari_errors.ForbiddenError, hikari_errors.NotFoundError):
                    break

                else:
                    break

        except errors.ParserError as exc:
            await self.hooks.trigger_parser_error(ctx, exc, hooks=hooks)

        except Exception as exc:
            await self.hooks.trigger_error(ctx, exc, hooks=hooks)
            raise

        else:
            # TODO: how should this be handled around CommandError?
            await self.hooks.trigger_success(ctx, hooks=hooks)

        finally:
            await self.hooks.trigger_post_execution(ctx, hooks=hooks)

        return True


class CommandGroup(Command, traits.ExecutableCommandGroup):
    __slots__: typing.Sequence[str] = ("_commands",)

    def __init__(
        self,
        function: traits.CommandFunctionT,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        metadata: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
        parser: typing.Optional[traits.Parser] = None,
    ) -> None:
        super().__init__(function, name, *names, checks=checks, hooks=hooks, metadata=metadata, parser=parser)
        self._commands: typing.MutableSet[traits.ExecutableCommand] = set()

    def __repr__(self) -> str:
        return f"CommandGroup <{len(self._commands)}: {self._names}>"

    @property
    def commands(self) -> typing.AbstractSet[traits.ExecutableCommand]:
        return frozenset(self._commands)

    def add_command(self, command: traits.ExecutableCommand, /) -> None:
        command.parent = self
        self._commands.add(command)

    def remove_command(self, command: traits.ExecutableCommand, /) -> None:
        command.parent = None
        self._commands.remove(command)

    def with_command(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        parser: typing.Optional[traits.Parser] = None,
    ) -> typing.Callable[[traits.CommandFunctionT], traits.CommandFunctionT]:
        def decorator(function: traits.CommandFunctionT, /) -> traits.CommandFunctionT:
            self.add_command(Command(function, name, *names, checks=checks, hooks=hooks, parser=parser))
            return function

        return decorator

    def bind_client(self, client: traits.Client, /) -> None:
        super().bind_client(client)
        for command in self._commands:
            command.bind_client(client)

    # I sure hope this plays well with command group recursion cause I am waaaaaaaaaaaaaay too lazy to test that myself.
    async def execute(
        self, ctx: traits.Context, /, *, hooks: typing.Optional[typing.MutableSet[traits.Hooks]] = None
    ) -> bool:
        if ctx.message.content is None:
            raise ValueError("Cannot execute a command with a contentless message")

        if self.hooks and hooks:
            hooks.add(self.hooks)

        elif self.hooks:
            hooks = {self.hooks}

        for command in self._commands:
            async for result in command.check_context(ctx):
                # triggering_prefix should never be None here but for the sake of covering all cases if it is then we
                # assume an empty string.
                # If triggering_name is None then we assume an empty string for that as well.
                content = ctx.message.content.lstrip()[len(ctx.triggering_prefix or "") :].lstrip()[
                    len(ctx.triggering_name or "") :
                ]
                space_len = len(content) - len(content.lstrip())
                ctx.triggering_name = (ctx.triggering_name or "") + (" " * space_len) + result.name
                ctx.content = ctx.content[space_len + len(result.name) :].lstrip()
                await result.command.execute(ctx, hooks=hooks)
                return True

        return await super().execute(ctx, hooks=hooks)
