from __future__ import annotations

__all__ = [
    "AbstractCommand",
    "AbstractCommandGroup",
    "Command",
    "CommandGroup",
    "Context",
    "ExecutableCommand",
    "HookLikeT",
    "Hooks",
    "TriggerTypes",
]

import abc
import asyncio
import contextlib
import enum
import inspect
import logging
import types
import typing

import attr
from hikari import errors as hikari_errors
from hikari.internal import more_collections

from tanjun import bases
from tanjun import parser as _parser
from tanjun import errors

# pylint: disable=ungrouped-imports
if typing.TYPE_CHECKING:
    from hikari import messages as _messages
    from hikari.clients import components as _components
    from hikari.clients import shards as _shards

    from tanjun import clusters as _clusters  # pylint: disable=cyclic-import

    CheckLikeT = typing.Callable[["Context"], typing.Union[bool, typing.Coroutine[typing.Any, typing.Any, bool]]]
    CommandFunctionT = typing.Callable[[...], typing.Coroutine[typing.Any, typing.Any, None]]
# pylint: enable=ungrouped-imports


class TriggerTypes(enum.Enum):
    PREFIX = enum.auto()
    MENTION = enum.auto()  # TODO: trigger commands with a mention


@attr.attrs(init=True, kw_only=True, slots=True)
class Context:
    content: str = attr.attrib()

    components: _components.Components = attr.attrib()

    message: _messages.Message = attr.attrib()
    """The message that triggered this command."""

    trigger: str = attr.attrib()
    """The string prefix or mention that triggered this command."""

    trigger_type: TriggerTypes = attr.attrib()
    """The mention or prefix that triggered this event."""

    triggering_name: str = attr.attrib(default=None)
    """The command alias that triggered this command."""

    command: AbstractCommand = attr.attrib(default=None)

    @property
    def cluster(self) -> _clusters.AbstractCluster:
        return self.command.cluster

    def prune_content(self, length: int) -> None:
        self.content = self.content[length:]

    def set_command_trigger(self, trigger: str) -> None:
        self.triggering_name = trigger

    def set_command(self, command: AbstractCommand) -> None:
        self.command = command

    @property
    def shard(self) -> typing.Optional[_shards.ShardClient]:
        return self.components.shards.get(self.shard_id, None)

    @property
    def shard_id(self) -> int:
        return (self.message.guild_id >> 22) % self.components.shards[0].shard_count if self.message.guild_id else 0


ConversionHookT = typing.Callable[  # TODO: are non-async hooks valid?
    [Context, errors.ConversionError], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
ErrorHookT = typing.Callable[
    [Context, BaseException], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]
]
HookLikeT = typing.Callable[[Context], typing.Union[typing.Coroutine[typing.Any, typing.Any, None], None]]
PreExecutionHookT = typing.Callable[[Context, ...], typing.Union[typing.Coroutine[typing.Any, typing.Any, bool], bool]]


@attr.attrs(init=True, kw_only=True, slots=True)
class Hooks:  # TODO: this
    pre_execution: PreExecutionHookT = attr.attrib(default=None)
    post_execution: HookLikeT = attr.attrib(default=None)
    on_conversion_error: ConversionHookT = attr.attrib(default=None)
    on_error: ErrorHookT = attr.attrib(default=None)
    on_success: HookLikeT = attr.attrib(default=None)
    on_ratelimit: HookLikeT = attr.attrib(default=None)  # TODO: implement?

    def set_pre_execution(self, hook: PreExecutionHookT) -> PreExecutionHookT:
        if self.pre_execution:
            raise ValueError("Pre-execution hook already set.")  # TODO: value error?
        self.pre_execution = hook
        return hook

    def set_post_execution(self, hook: HookLikeT) -> HookLikeT:  # TODO: better typing
        if self.post_execution:
            raise ValueError("Post-execution hook already set.")
        self.post_execution = hook
        return hook

    def set_on_conversion_error(self, hook: ConversionHookT) -> ConversionHookT:
        if self.on_conversion_error:
            raise ValueError("On conversion error hook already set.")
        self.on_conversion_error = hook
        return hook

    def set_on_error(self, hook: ErrorHookT) -> ErrorHookT:
        if self.on_error:
            raise ValueError("On error hook already set.")
        self.on_error = hook
        return hook

    def set_on_success(self, hook: HookLikeT) -> HookLikeT:
        if self.on_success:
            raise ValueError("On success hook already set.")
        self.on_success = hook
        return hook

    async def trigger_pre_execution_hooks(
        self, ctx: Context, *args, extra_hooks: typing.Optional[typing.Sequence[Hooks]] = None, **kwargs,
    ) -> bool:
        result = True
        if self.pre_execution:
            result = self.pre_execution(ctx, *args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result

        extra_hooks = extra_hooks or more_collections.EMPTY_SEQUENCE
        external_results = await asyncio.gather(
            *(hook.trigger_pre_execution_hooks(ctx, *args, **kwargs, extra_hooks=None) for hook in extra_hooks)
        )
        return result and all(external_results)

    async def trigger_on_conversion_error_hooks(
        self,
        ctx: Context,
        exception: errors.ConversionError,
        *,
        extra_hooks: typing.Optional[typing.Sequence[Hooks]] = None,
    ) -> None:
        if self.on_conversion_error:
            result = self.on_conversion_error(ctx, exception)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

        for hook in extra_hooks or more_collections.EMPTY_SEQUENCE:
            if hook.on_conversion_error:
                asyncio.create_task(hook.trigger_on_conversion_error_hooks(ctx, exception))

    async def trigger_error_hooks(
        self, ctx: Context, exception: BaseException, *, extra_hooks: typing.Optional[typing.Sequence[Hooks]] = None,
    ) -> None:
        if self.on_error:
            result = self.on_error(ctx, exception)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

        for hook in extra_hooks or more_collections.EMPTY_SEQUENCE:
            if hook.on_error:
                asyncio.create_task(hook.trigger_error_hooks(ctx, exception))

    async def trigger_on_success_hooks(
        self, ctx: Context, *, extra_hooks: typing.Optional[typing.Sequence[Hooks]] = None,
    ) -> None:
        if self.on_success:
            result = self.on_success(ctx)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

        for hook in extra_hooks or more_collections.EMPTY_SEQUENCE:
            asyncio.create_task(hook.trigger_on_success_hooks(ctx))

    async def trigger_post_execution_hooks(
        self, ctx: Context, *, extra_hooks: typing.Optional[typing.Sequence[Hooks]] = None,
    ) -> None:
        if self.post_execution:
            result = self.post_execution(ctx)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

        for hook in extra_hooks or more_collections.EMPTY_SEQUENCE:
            if hook.post_execution:
                asyncio.create_task(hook.trigger_post_execution_hooks(ctx))


@attr.attrs(init=True, kw_only=True, slots=False)
class ExecutableCommand(bases.Executable, abc.ABC):
    hooks: Hooks = attr.attrib(factory=Hooks)

    triggers: typing.Tuple[str, ...] = attr.attrib()
    """The triggers used to activate this command in chat along with a prefix."""

    @abc.abstractmethod
    def __call__(self, *args, **kwargs) -> typing.Coroutine[typing.Any, typing.Any, typing.Any]:
        ...

    @abc.abstractmethod
    async def check(self, ctx: Context) -> bool:
        """
        Used to check if this entity should be executed based on a Context.

        Args:
            ctx:
                The :class:`Context` object to check.

        Returns:
            The :class:`bool` of whether this executable is a match for the given context.
        """

    @abc.abstractmethod
    def check_prefix(self, content: str) -> typing.Optional[str]:
        ...

    @abc.abstractmethod
    def check_prefix_from_context(self, ctx: Context) -> typing.Optional[str]:
        ...

    @abc.abstractmethod
    def deregister_check(self, check: CheckLikeT) -> None:
        ...

    @abc.abstractmethod
    async def execute(
        self, ctx: Context, *, hooks: typing.Optional[typing.Sequence[Hooks]] = None
    ) -> typing.Literal[True]:
        ...

    @abc.abstractmethod
    def register_check(self, check: CheckLikeT) -> None:
        ...


@attr.attrs(init=True, kw_only=True)
class AbstractCommand(ExecutableCommand, abc.ABC):

    meta: typing.MutableMapping[typing.Any, typing.Any] = attr.attrib(factory=dict)

    level: int = attr.attrib()
    """The user access level that'll be required to execute this command, defaults to 0."""

    parser: typing.Optional[_parser.AbstractCommandParser]

    @abc.abstractmethod
    def bind_cluster(self, cluster: _clusters.AbstractCluster) -> None:
        ...

    @property
    @abc.abstractmethod
    def cluster(self) -> typing.Optional[_clusters.AbstractCluster]:
        ...

    @property
    @abc.abstractmethod
    def docstring(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod  # TODO: differentiate between command and command group.
    def _create_parser(
        self, func: typing.Callable[[...], typing.Coroutine[typing.Any, typing.Any, typing.Any]], **kwargs: typing.Any
    ) -> typing.Optional[_parser.AbstractCommandParser]:
        ...


# TODO: be more consistent with "func", "function", etc etc  # TODO: does this have to be separate?
def _generate_trigger(function: typing.Optional[CommandFunctionT] = None) -> str:
    """Get a trigger for this command based on it's function's name."""
    return function.__name__.replace("_", " ")


async def _run_checks(ctx: Context, checks: typing.Sequence[CheckLikeT]) -> None:
    failed: typing.MutableSequence[typing.Tuple[CheckLikeT, typing.Optional[Exception]]] = []
    for check in checks:
        try:
            result = check(ctx)
            if asyncio.iscoroutine(result):
                result = await result
        except Exception as exc:
            failed.append((check, exc))
        else:
            if not result:
                failed.append((check, None))

    if failed:
        raise errors.FailedCheck(tuple(failed))


@attr.attrs(init=False, slots=True, repr=False)
class Command(AbstractCommand):
    _checks: typing.MutableSequence[CheckLikeT]

    _func: CommandFunctionT = attr.attrib()

    logger: logging.Logger

    _cluster: typing.Optional[_clusters.AbstractCluster] = attr.attrib(default=None)

    def __init__(
        self,
        func: typing.Optional[CommandFunctionT],
        trigger: typing.Optional[str] = None,
        /,
        *,
        aliases: typing.Optional[typing.Sequence[str]] = None,
        hooks: typing.Optional[Hooks] = None,
        level: int = 0,
        meta: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
        cluster: typing.Optional[_clusters.AbstractCluster] = None,
        greedy: typing.Optional[str] = None,
    ) -> None:
        if trigger is None:
            trigger = _generate_trigger(func)
        super().__init__(
            hooks=hooks or Hooks(),
            level=level,
            meta=meta or {},
            triggers=tuple(
                trig for trig in (trigger, *(aliases or more_collections.EMPTY_COLLECTION)) if trig is not None
            ),
        )
        self.logger = logging.getLogger(type(self).__qualname__)
        self._checks = []
        self._func = func
        self.parser = self._create_parser(self._func, greedy=greedy)
        if cluster:
            self.bind_cluster(cluster)

    def __call__(self, *args, **kwargs) -> typing.Coroutine[typing.Any, typing.Any, typing.Any]:
        return self._func(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Command({'|'.join(self.triggers)})"

    def bind_cluster(self, cluster: _clusters.AbstractCluster) -> None:
        # This ensures that the cluster will always be passed-through as `self`.
        self._func = types.MethodType(self._func, cluster)
        self._cluster = cluster
        # Now that we know self will automatically be passed, we need to trim the parameters again.
        self.parser.trim_parameters(1)
        # Before the parser can be used, we need to resolve it's converters and check them against the bot's declared
        # gateway intents.
        self.parser.components_hook(cluster.components)

    async def check(self, ctx: Context) -> None:
        return await _run_checks(ctx, self._checks)

    def check_prefix(self, content: str) -> typing.Optional[str]:
        for trigger in self.triggers:
            if content.startswith(trigger):
                return trigger
        return None

    def check_prefix_from_context(self, ctx: Context) -> typing.Optional[str]:
        return self.check_prefix(ctx.content)

    @property
    def cluster(self) -> typing.Optional[_clusters.AbstractCluster]:
        return self._cluster

    def deregister_check(self, check: CheckLikeT) -> None:
        try:
            self._checks.remove(check)
        except ValueError:
            raise ValueError("Command Check not found.")

    @property
    def docstring(self) -> str:
        return inspect.getdoc(self._func)

    async def execute(self, ctx: Context, *, hooks: typing.Optional[typing.Sequence[Hooks]] = None) -> bool:
        ctx.set_command(self)
        if self.parser:
            try:
                args, kwargs = self.parser.parse(ctx)
            except errors.ConversionError as exc:
                await self.hooks.trigger_on_conversion_error_hooks(ctx, exc, extra_hooks=hooks)
                self.logger.debug("Command %s raised a Conversion Error: %s", self, exc)
                return True
        else:
            args, kwargs = more_collections.EMPTY_SEQUENCE, more_collections.EMPTY_DICT

        try:
            if await self.hooks.trigger_pre_execution_hooks(ctx, *args, **kwargs, extra_hooks=hooks) is False:
                return True
            await self._func(ctx, *args, **kwargs)
        except errors.CommandError as exc:
            with contextlib.suppress(hikari_errors.HTTPError):  # TODO: better permission handling?
                response = str(exc)
                await ctx.message.reply(content=response if len(response) <= 2000 else response[:1997] + "...")
        except Exception as exc:
            await self.hooks.trigger_error_hooks(ctx, exc, extra_hooks=hooks)
            raise exc
        else:
            await self.hooks.trigger_on_success_hooks(ctx, extra_hooks=hooks)
        finally:
            await self.hooks.trigger_post_execution_hooks(ctx, extra_hooks=hooks)

        return True  # TODO: necessary?

    @property
    def name(self) -> str:
        """Get the name of this command."""
        return self._func.__name__

    def register_check(self, check: CheckLikeT) -> None:
        self._checks.append(check)

    def _create_parser(
        self, func: typing.Callable[[...], typing.Coroutine[typing.Any, typing.Any, typing.Any]], **kwargs: typing.Any
    ) -> _parser.AbstractCommandParser:
        return _parser.CommandParser(func=func, **kwargs)


@attr.attrs(init=True, kw_only=True, slots=False, repr=False)
class AbstractCommandGroup(
    ExecutableCommand, abc.ABC
):  # TODO: use this for typing along sideor just executable command
    commands: typing.MutableSequence[AbstractCommand] = attr.attrib(factory=list)

    master_command: typing.Optional[AbstractCommand] = attr.attrib(default=None)

    @abc.abstractmethod
    def register_command(self, command: AbstractCommand, *, hook: bool = True) -> AbstractCommand:
        ...

    @abc.abstractmethod
    def set_master_command(self, command: AbstractCommand) -> AbstractCommand:
        ...


class CommandGroup(AbstractCommandGroup):
    _cluster: typing.Optional[_clusters.AbstractCluster] = attr.attrib(default=None)

    _checks: typing.MutableSequence[CheckLikeT]

    logger: logging.Logger

    def __init__(
        self,
        name: typing.Optional[str],
        *,
        # ? aliases: typing.Optional[typing.Sequence[str]] = None,
        commands: typing.Sequence[Command] = None,
        hooks: typing.Optional[Hooks] = None,
        level: int = 0,
        master_command: typing.Optional[AbstractCommand] = None,
        meta: typing.Optional[typing.MutableMapping[typing.Any, typing.Any]] = None,
        cluster: typing.Optional[_clusters.AbstractCluster] = None,
    ) -> None:
        super().__init__(
            commands=commands or [],
            triggers=(name,),
            meta=meta or {},
            hooks=hooks or Hooks(),
            level=level,
            master_command=master_command,
        )
        self._checks = []
        self._cluster = cluster
        self.logger = logging.getLogger(type(self).__qualname__)
        self.master_command = master_command

    def __call__(self, *args, **kwargs) -> typing.Coroutine[typing.Any, typing.Any, typing.Any]:
        if self.master_command:
            return self.master_command(*args, **kwargs)
        raise TypeError("Command group without top-level command is not callable.")

    def bind_cluster(self, cluster: _clusters.AbstractCluster) -> None:  # TODO: should this work like this?
        self._cluster = cluster
        if self.master_command:
            self.master_command.bind_cluster(cluster)
        for command in self.commands:
            command.bind_cluster(cluster)

    async def check(self, ctx: Context) -> None:
        return await _run_checks(ctx, self._checks)

    def check_prefix(self, content: str) -> typing.Optional[str]:
        if content.startswith(self.name):
            return self.name
        return None

    def check_prefix_from_context(self, ctx: Context) -> typing.Optional[str]:
        return self.check_prefix(ctx.content)

    @property
    def cluster(self) -> typing.Optional[_clusters.AbstractCluster]:
        return self._cluster

    def deregister_check(self, check: CheckLikeT) -> None:
        try:
            self._checks.remove(check)
        except ValueError:
            raise ValueError("Command Check not found.")

    @property
    def docstring(self) -> str:
        return inspect.getdoc(self)

    async def execute(
        self, ctx: Context, *, hooks: typing.Optional[typing.Sequence[Hooks]] = None
    ) -> typing.Literal[True]:
        hooks = hooks or []
        hooks.append(self.hooks)
        for command in self.commands:
            if await command.check(ctx):
                await command.execute(ctx, hooks=hooks)
                break
        else:
            if self.master_command and await self.master_command.check(ctx):
                await self.master_command.execute(ctx, hooks=hooks)
        return True

    @property
    def name(self) -> str:
        return self.triggers[0]

    def register_check(self, check: CheckLikeT) -> None:
        self._checks.append(check)

    def register_command(self, command: AbstractCommand, *, bind: bool = True) -> AbstractCommand:
        for trigger in command.triggers:
            for reg_command in self.commands:
                if any(trigger == reg_trigger for reg_trigger in reg_command.triggers):
                    raise ValueError(f"Command trigger {trigger} already registered in {reg_command}")
        if bind:
            command.bind_cluster(self._cluster)  # TODO: bind group instead, treat group as cluster?
        self.commands.append(command)
        return command

    def set_master_command(self, command: AbstractCommand) -> AbstractCommand:
        self.master_command = command
        return command
