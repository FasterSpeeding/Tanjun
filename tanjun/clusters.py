from __future__ import annotations

__all__ = ["AbstractCluster", "Cluster"]

import abc
import inspect
import logging
import typing

import attr

from tanjun import bases
from tanjun import commands as _commands
from tanjun import errors

# pylint: disable=ungrouped-imports
if typing.TYPE_CHECKING:
    from hikari import messages as _messages
    from hikari.clients import components as _components
    from hikari.events import dispatchers as _dispatchers

    from tanjun import client as _client  # pylint: disable=cyclic-import
# pylint: enable=ungrouped-imports


@attr.attrs(init=True, kw_only=True)
class AbstractCluster(bases.Executable):  # TODO: Executable  TODO: proper type annotations
    client: _client.Client = attr.attrib()

    components: _components.Components = attr.attrib()

    hooks: _commands.Hooks = attr.attrib(factory=_commands.Hooks)

    started: bool = attr.attrib()

    @abc.abstractmethod
    async def load(self) -> None:
        ...

    @abc.abstractmethod
    async def unload(self) -> None:
        ...

    # @abc.abstractmethod
    # def bind_client(self, client: CommandClient) -> None:  # TODO: This?
    #     ...

    @abc.abstractmethod
    def get_cluster_event_listeners(self) -> typing.Sequence[typing.Tuple[str, _dispatchers.EventCallbackT]]:
        ...

    @abc.abstractmethod
    async def get_command_from_context(
        self, ctx: _commands.Context
    ) -> typing.AsyncIterator[typing.Tuple[_commands.AbstractCommand, str]]:
        ...

    @abc.abstractmethod
    def get_command_from_name(self, content: str) -> typing.Iterator[typing.Tuple[_commands.AbstractCommand, str]]:
        """
        Get a command based on a message's content (minus prefix) from the loaded commands if any command triggers are
        found in the content.

        Args:
            content:
                The string content to try and find a command for (minus the triggering prefix).

        Returns:
            A :class:`typing.AsyncIterator` of a :class:`typing.Tuple` of a :class:`AbstractCommand`
            derived object and the :class:`str` trigger that was matched.
        """

    @abc.abstractmethod
    def register_command(self, command: _commands.AbstractCommand, *, bind: bool = False) -> None:
        """
        Register a command in this cluster.

        Args:
            func:
                The Coroutine Function to be called when executing this command.
            *aliases:
                More string triggers for this command.
            trigger:
                The string that will be this command's main trigger.
            bind:
                If this command should be binded to the cluster. Meaning that
                self will be passed to it and it will be added as an attribute.
        """

    @abc.abstractmethod
    def deregister_command(self, command: _commands.AbstractCommand) -> None:
        """
        Unregister a command in this cluster.

        Args:
            command:
                The command object to remove.

        Raises:
            ValueError:
                If the passed command object wasn't found.
        """


class Cluster(AbstractCluster):

    commands: typing.MutableSequence[_commands.AbstractCommand]
    """A list of the commands that are loaded in this cluster."""

    logger: logging.Logger
    """The class wide logger."""

    def __init__(
        self,
        client: _client.Client,
        components: _components.Components,
        *,
        hooks: typing.Optional[_commands.Hooks] = None,
    ) -> None:
        AbstractCluster.__init__(
            self, client=client, components=components, hooks=hooks or _commands.Hooks(), started=False
        )
        self.logger = logging.getLogger(type(self).__qualname__)
        self.commands = []
        self.bind_commands()
        self.bind_listeners()

    async def load(self) -> None:
        ...

    async def unload(self) -> None:
        ...

    async def access_check(self, command: _commands.AbstractCommand, message: _messages.Message) -> bool:
        """
        Used to check if a command can be accessed by the calling user and in the calling channel/guild.

        Args:
            command:
                The :class:`AbstractCommand` derived object to check access levels for.
            message:
                The :class:`_messages.Message` object to check access levels for.

        Returns:
            A :class:`bool` representation of whether this command can be accessed.
        """
        return self.components.config.access_levels.get(message.author.id, 0) >= command.level

    def bind_commands(self) -> None:
        """
        Loads any commands that are attached to this class into `cluster_commands`.

        Raises:
            ValueError:
                if the commands for this cluster have already been binded or if any duplicate triggers are found while
                loading commands.
        """
        if self.commands:  # TODO: overwrite commands?
            raise ValueError(
                "Cannot bind commands in cluster '{self.__class__.__name__}' when commands have already been binded."
            )
        for name, command in inspect.getmembers(
            self, predicate=lambda attribute: isinstance(attribute, _commands.AbstractCommand)
        ):
            self.register_command(command, bind=True)
            self.logger.debug(
                "Binded command %s in %s cluster.", command.name, self.__class__.__name__,
            )
        self.commands.sort(key=lambda comm: comm.name, reverse=True)  # TODO: why was this reversed again?

    def bind_listeners(self) -> None:
        """Used to add event listeners from all loaded command clusters to hikari's internal event listener."""
        for _, function in self.get_cluster_event_listeners():
            self.logger.debug(f"Registering %s event listener for command client.", function.__event__)
            self.components.event_dispatcher.add_listener(function.__event__, function)

    def get_cluster_event_listeners(self) -> typing.Sequence[typing.Tuple[str, _dispatchers.EventCallbackT]]:
        """Get a generator of the event listeners attached to this cluster."""
        return inspect.getmembers(self, predicate=lambda obj: hasattr(obj, "__event__"))

    async def execute(
        self, ctx: _commands.Context, *, hooks: typing.Optional[typing.Sequence[_commands.Hooks]] = None
    ) -> bool:
        async for command, trigger in self.get_command_from_context(ctx):
            ctx.set_command_trigger(trigger)
            ctx.prune_content(len(trigger) + 1)  # TODO: no space? also here?
            hooks = hooks or []
            hooks.append(self.hooks)
            await command.execute(ctx, hooks=hooks)
            return True
        return False

    async def get_command_from_context(
        self, ctx: _commands.Context
    ) -> typing.AsyncIterator[typing.Tuple[_commands.AbstractCommand, str]]:
        for command in self.commands:
            if (trigger := command.check_prefix_from_context(ctx)) is None:
                continue

            try:
                await command.check(ctx)
            except errors.FailedCheck:
                continue
            else:
                if await self.access_check(command, ctx.message):
                    yield command, trigger

    def get_command_from_name(self, content: str) -> typing.Iterator[typing.Tuple[_commands.AbstractCommand, str]]:
        for command in self.commands:
            if prefix := command.check_prefix(content):
                yield command, prefix

    def register_command(self, command: _commands.AbstractCommand, *, bind: bool = False) -> None:  # TODO: decorator?
        for trigger in command.triggers:
            if list(self.get_command_from_name(trigger)):
                self.logger.warning(
                    "Possible overlapping trigger '%s' found in %s cluster.", trigger, self.__class__.__name__,
                )
        if bind:
            command.bind_cluster(self)
        self.commands.append(command)

    def deregister_command(self, command: _commands.AbstractCommand) -> None:
        try:
            self.commands.remove(command)
        except ValueError:
            raise ValueError("Invalid command passed for this cluster.") from None
