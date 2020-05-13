from __future__ import annotations

__all__ = [
    "AbstractClient",
    "Client",
]

import abc
import importlib.util
import inspect
import typing

import attr
from hikari.events import message as message_events
from hikari.events import other as other_events

from tanjun import clusters as _clusters
from tanjun import commands
from tanjun import decorators

# pylint: disable=ungrouped-imports
if typing.TYPE_CHECKING:
    from hikari import messages as _messages
    from hikari.clients import components as _components
# pylint: enable=ungrouped-imports


@attr.attrs(init=True, kw_only=True, slots=False)  # TODO: actually don't use attr.attrs for initiation because doc gen
class AbstractClient(abc.ABC):
    """The interfaces that all Client implementations should expose.

    This client should contain the logic for handling command cluster execution
    on relevant events (e.g MESSAGE_CREATE and MESSAGE_EDIT).
    """

    clusters: typing.MutableMapping[str, _clusters.AbstractCluster] = attr.attrib(factory=dict)
    """A mapping of strings to the clusters that this client has loaded."""

    components: _components.Components = attr.attrib()
    """The bot components this client is bound by.

    Contains the master event listeners/dispatchers used for tracking Discord
    gateway events and the config that this client will be using.
    """

    @abc.abstractmethod
    async def check_prefix(self, message: _messages.Message) -> typing.Optional[str]:
        """Get the prefixes for a message.

        !!! note
            By default this will most likely just return the bot's global
            prefixes; to have this check the prefixes for a specific guild
            you will likely want to override the implementation for
            `AbstractClient.get_prefixes` to return both the bot's global
            prefixes along with any prefixes that are relevant for a message.
        """

    @abc.abstractmethod  # TODO: support string?
    async def deregister_cluster(self, cluster: _clusters.AbstractCluster) -> _clusters.AbstractCluster:
        """Remove a cluster from this client.

        Parameters
        ----------
        cluster : tanjun.clusters.AbstractCluster
            The object of the cluster to remove.
        """

    @abc.abstractmethod
    async def get_global_command_from_context(
        self, ctx: commands.Context
    ) -> typing.AsyncIterator[commands.AbstractCommand]:
        """Get a command or command group that matches a given context.

        This will cover all the clusters registered in this client.

        Parameters
        ----------
        ctx : hikari.commands.Context
            The context to get a matching command from.

        Returns
        -------
        typing.AsyncIterator[tanjun.commands.AbstractCommand]
            An async iterator of the commands that matched for the passed
            context, this allows the client to run it's own checks before
            deciding to either execute the command or go onto the next matched
            command.
        """

    @abc.abstractmethod
    def get_global_command_from_name(
        self, content: str
    ) -> typing.Iterator[typing.Tuple[commands.AbstractCommand, str]]:
        """Get a command or command group from a string content.

        This will check for a command's name or a command group's name and
        will cover all this client's registered clusters.

        Parameters
        ----------
        content : str
            The string content to get a command from.

        Returns
        -------
        typing.Iterator[typing.Tuple[commands.AbstractCommand, str]]
        """

    @abc.abstractmethod
    async def get_prefixes(self, message: _messages.Message) -> typing.Sequence[str]:
        """
        Used to get the registered global prefixes and the prefixes a message.

        Parameters
        ----------
        message : tanjun.messages.Message
            The message to get prefixes for.

        Returns
        -------
        typing.Sequence[str]
            A sequence of the prefixes found for this message.

        !!! note
            A command client may default this just returning the bot's global
            prefixes but this is async as to allow an implementation to be
            overloaded to return any prefix relevant for a message (e.g. guild
            or channel prefixes).
        """

    @abc.abstractmethod
    def load_from_modules(self, *modules: str) -> None:
        """Load elements of a bot from a list of modules links.

        Parameters
        ----------
        modules : str
            The paths of the modules to load elements (e.g. clusters and
            commands) from.
        """

    @abc.abstractmethod
    async def register_cluster(
        self, cluster: typing.Union[_clusters.AbstractCluster, typing.Type[_clusters.AbstractCluster]]
    ) -> None:  # TODO: both type and initialised?
        """Register a cluster in this client.

        Parameters
        ----------
        cluster : typing.Union[tanjun.clusters.AbstractCluster, tanjun.clusters.AbstractCluster]
            The class or object of an abstract cluster to register.
        """


class Client(AbstractClient, _clusters.Cluster):
    """
    The central client that all command clusters will be binded to. This extends :class:`hikari.client.Client` and
    handles registering event listeners attached to the loaded clusters and the listener(s) required for commands.

    Note:
        This inherits from :class:`CommandCluster` and can act as an independent Command Cluster for small bots.
    """

    def __init__(
        self,
        components: _components.Components,
        *,
        hooks: typing.Optional[commands.Hooks] = None,
        modules: typing.Sequence[str] = None,
    ) -> None:
        if modules and components.config.modules:
            raise RuntimeError("The `modules` kwarg cannot be passed with a components config that declares modules.")

        AbstractClient.__init__(self, components=components)
        _clusters.Cluster.__init__(self, client=self, components=components, hooks=hooks)
        self.clusters = {}
        self.load_from_modules(*(modules or components.config.modules))

    async def load(self) -> None:
        if not self.started:
            self.logger.debug("Starting up %s cluster.", self.__class__.__name__)
            await super().load()
        for cluster in self.clusters.values():
            if cluster.started:
                continue
            self.logger.debug("Starting up %s cluster.", cluster.__class__.__name__)
            await cluster.load()

    async def check_prefix(self, message: _messages.Message) -> typing.Optional[str]:
        """
        Used to check if a message's content match any currently registered prefix (including any prefixes registered
        for the guild if this is being called from one.

        Args:
            message:
                The :class:`messages.Message` object that we're checking for a prefix in it's content.

        Returns:
            A :class:`str` representation of the triggering prefix if found, else :class:`None`
        """
        trigger_prefix = None
        for prefix in await self.get_prefixes(message):
            if message.content.startswith(prefix):
                trigger_prefix = prefix
                break
        return trigger_prefix

    async def deregister_cluster(self, cluster: _clusters.AbstractCluster) -> _clusters.AbstractCluster:
        cluster = self.clusters.pop(cluster.__class__.__name__)
        await cluster.unload()
        return cluster

    async def get_global_command_from_context(
        self, ctx: commands.Context
    ) -> typing.AsyncIterator[commands.AbstractCommand]:
        for cluster in (self, *self.clusters.values()):
            async for command in cluster.get_command_from_context(ctx):
                yield command

    def get_global_command_from_name(
        self, content: str
    ) -> typing.Iterator[typing.Tuple[commands.AbstractCommand, str]]:
        yield from self.get_command_from_name(content)
        for cluster in (self, *self.clusters.values()):
            yield from cluster.get_command_from_name(content)

    async def get_prefixes(self, message: _messages.Message) -> typing.Sequence[str]:
        return self.components.config.prefixes

    def load_from_modules(self, *modules: str) -> None:
        for module_path in modules:
            module = importlib.util.spec_from_file_location(module_path)
            module.setup(self)

    @decorators.event(message_events.MessageCreateEvent)
    async def on_message_create(self, message: message_events.MessageCreateEvent) -> None:
        """Handles command triggering based on message creation."""
        prefix = await self.check_prefix(message)
        mention = None  # TODO: mention at end of message?
        if prefix or mention:
            command_args = message.content[len(prefix or mention) :]
        else:
            return

        ctx = commands.Context(
            components=self.components,
            content=command_args,
            message=message,
            trigger=prefix or mention,
            trigger_type=commands.TriggerTypes.PREFIX if prefix else commands.TriggerTypes.MENTION,
        )
        for cluster in (self, *self.clusters.values()):
            if await cluster.execute(ctx):
                break

    @decorators.event(other_events.ReadyEvent)
    async def on_ready(self, _: other_events.ReadyEvent) -> None:
        if not self.started:
            await self.load()

    async def register_cluster(
        self, cluster: typing.Union[_clusters.AbstractCluster, typing.Type[_clusters.AbstractCluster]]
    ) -> None:
        if inspect.isclass(cluster):
            cluster = cluster(self, self.components)
        #  TODO: bind client?
        await cluster.load()
        self.clusters[cluster.__class__.__name__] = cluster
