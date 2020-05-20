from __future__ import annotations

__all__ = ["Executable"]

import abc
import typing

if typing.TYPE_CHECKING:
    from . import commands as commands_  # pylint: disable=cyclic-import


class Executable(abc.ABC):
    """A base class that all executable classes will inherit from.

    A few example of these are `tanjun.clusters.Cluster` and
    `tanjun.commands.Command`.
    """

    @abc.abstractmethod
    async def execute(
        self, ctx: commands_.Context, *, hooks: typing.Optional[typing.Sequence[commands_.Hooks]] = None
    ) -> bool:
        """
        Used to execute an entity based on a `tanjun.commands.Context` object.

        Parameters
        ----------
        ctx : tanjun.commands.Context
            The Context object to execute this executable with.
        hooks : typing.Sequence[tanjun.commands.Hooks], optional
            Any additional command hooks that should be executed along with any
            other hooks assigned to this executable.
        """
