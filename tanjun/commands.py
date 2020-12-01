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

import types
import typing

from hikari import errors as hikari_errors
from hikari import undefined
from yuyo import backoff

from tanjun import errors
from tanjun import hooks as hooks_
from tanjun import parsing
from tanjun import traits
from tanjun import utilities


class FoundCommand(traits.FoundCommand):
    __slots__: typing.Sequence[str] = ("command", "name", "prefix")

    def __init__(self, command_: traits.ExecutableCommand, name: str) -> None:
        self.command = command_
        self.name = name


class Command(traits.ExecutableCommand):
    __slots__: typing.Sequence[str] = (
        "_checks",
        "_component",
        "_function",
        "hooks",
        "_meta",
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
        parser: undefined.UndefinedNoneOr[traits.Parser] = undefined.UNDEFINED,
    ) -> None:
        self._checks = set(checks) if checks else set()
        self._component: typing.Optional[traits.Component] = None
        self._function = function
        self.hooks: traits.Hooks = hooks or hooks_.Hooks()
        self._meta: typing.MutableMapping[typing.Any, typing.Any] = {}
        self._names = {name, *names}
        self.parent: typing.Optional[traits.ExecutableCommandGroup] = None
        self.parser = parser if parser is not undefined.UNDEFINED else parsing.ShlexParser()

    async def __call__(self, ctx: traits.Context, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return await self._function(ctx, *args, **kwargs)

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
        return self._meta

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
            if await utilities.gather_checks(utilities.await_if_async(check(ctx)) for check in self._checks):
                yield found

    def add_name(self, name: str, /) -> None:
        self._names.add(name)

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        for own_name in self._names:
            if name.startswith(own_name):
                yield FoundCommand(self, own_name)
                break

    def remove_name(self, name: str, /) -> None:
        self._names.remove(name)

    def bind_client(self, client: traits.Client, /) -> None:
        if self.parser:
            self.parser.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        self._component = component
        self._function = types.MethodType(self._function, component)

        if self.parser:
            self.parser.bind_component(component)

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
                    await ctx.message.reply(content=response)

                except hikari_errors.RateLimitedError as retry_error:
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

    def group(
        self,
        *,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
    ) -> CommandGroup:
        command_group = CommandGroup(*self._names, checks=checks, hooks=hooks, top_command=self)
        self.parent = command_group
        self._names.clear()
        return command_group


class CommandGroup(traits.ExecutableCommandGroup):
    __slots__: typing.Sequence[str] = (
        "_checks",
        "_commands",
        "_component",
        "hooks",
        "_meta",
        "_names",
        "parent",
        "_top_command",
    )

    def __init__(
        self,
        name: str,
        /,
        *names: str,
        checks: typing.Optional[typing.Iterable[traits.CheckT]] = None,
        hooks: typing.Optional[traits.Hooks] = None,
        top_command: typing.Optional[traits.ExecutableCommand] = None,
    ) -> None:
        self._checks = set(checks) if checks else set()
        self._commands: typing.MutableSet[traits.ExecutableCommand] = set()
        self._component: typing.Optional[traits.Component] = None
        self.hooks = hooks
        self._meta: typing.MutableMapping[typing.Any, typing.Any] = {}
        self._names = {name, *names}
        self.parent: typing.Optional[traits.ExecutableCommandGroup] = None
        self._top_command = top_command

    async def __call__(self, ctx: traits.Context, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if self._top_command is None or not self._top_command.function:
            raise RuntimeError("Cannot call a command group without a top level command")

        return await self._top_command.function(ctx, *args, **kwargs)

    def __repr__(self) -> str:
        command_len = len(self._commands)

        if self._top_command:
            command_len += 1

        return f"CommandGroup <{command_len}: {self._names}>"

    @property
    def checks(self) -> typing.AbstractSet[traits.CheckT]:
        return frozenset(self._checks)

    @property
    def commands(self) -> typing.AbstractSet[traits.ExecutableCommand]:
        return frozenset(self._commands)

    @property
    def component(self) -> typing.Optional[traits.Component]:
        return self._component

    @property
    def function(self) -> None:
        return None

    @property
    def metadata(self) -> typing.MutableMapping[typing.Any, typing.Any]:
        return self._meta

    @property
    def top_command(self) -> typing.Optional[traits.ExecutableCommand]:
        return self._top_command

    @top_command.setter
    def top_command(self, top_command: typing.Optional[traits.ExecutableCommand]) -> None:
        raise NotImplementedError

    @property
    def names(self) -> typing.AbstractSet[str]:
        return frozenset(self._names)

    @property
    def parser(self) -> None:
        return None

    @parser.setter
    def parser(self, parser: typing.Optional[traits.Parser], /) -> typing.NoReturn:
        raise ValueError("Cannot add set a parser on a command group")

    def add_check(self, check: traits.CheckT, /) -> None:
        self._checks.add(check)

    def remove_check(self, check: traits.CheckT, /) -> None:
        self._checks.remove(check)

    def with_check(self, check: traits.CheckT, /) -> traits.CheckT:
        self.add_check(check)
        return check

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
        parser: undefined.UndefinedNoneOr[traits.Parser] = undefined.UNDEFINED,
    ) -> typing.Callable[[traits.CommandFunctionT], traits.CommandFunctionT]:
        def decorator(function: traits.CommandFunctionT, /) -> traits.CommandFunctionT:
            command = Command(function, name, *names, checks=checks, hooks=hooks, parser=parser)
            command.parent = self
            self.add_command(command)
            return function

        return decorator

    def add_name(self, name: str, /) -> None:
        self._names.add(name)

    def remove_name(self, name: str, /) -> None:
        self._names.remove(name)

    def bind_client(self, client: traits.Client, /) -> None:
        if self._top_command:
            self._top_command.bind_client(client)

        for command in self._commands:
            command.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        self._component = component
        if self._top_command:
            self._top_command.bind_component(component)

        for command in self._commands:
            command.bind_component(component)

    async def check_context(
        self, ctx: traits.Context, /, *, name_prefix: str = ""
    ) -> typing.AsyncIterator[traits.FoundCommand]:
        if result := next(self.check_name(ctx.content[len(name_prefix) :].lstrip()), None):
            if await utilities.gather_checks(utilities.await_if_async(check(ctx)) for check in self._checks):
                yield result

    def check_name(self, name: str, /) -> typing.Iterator[traits.FoundCommand]:
        for own_name in self._names:
            if name.startswith(own_name):
                yield FoundCommand(self, own_name)
                break

    # I sure hope this plays well with command group recursion cause I am waaaaaaaaaaaaaay too lazy to test that myself.
    async def execute(
        self, ctx: traits.Context, /, *, hooks: typing.Optional[typing.MutableSet[traits.Hooks]] = None
    ) -> bool:
        if self.hooks and hooks:
            hooks.add(self.hooks)

        elif self.hooks:
            hooks = {self.hooks}

        for command in self._commands:
            async for result in command.check_context(ctx):
                assert ctx.message.content is not None
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

        if self._top_command:
            # Seeing as we don't care for the top command's own name(s) we specifically only run it's checks here.
            if await utilities.gather_checks(
                utilities.await_if_async(check(ctx)) for check in self._top_command.checks
            ):
                await self._top_command.execute(ctx, hooks=hooks)

        return True
