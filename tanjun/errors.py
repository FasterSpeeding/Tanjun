from __future__ import annotations

__all__ = ["CommandClientError", "CommandError", "CommandPermissionError", "ConversionError", "FailedCheck"]

import typing

import attr
from hikari import errors as hikari_errors

if typing.TYPE_CHECKING:
    from hikari import permissions as _permission

    from tanjun import commands as _commands  # pylint: disable=cyclic-import
    from tanjun import parser as _parser  # pylint: disable=cyclic-import


class CommandClientError(hikari_errors.HikariError):
    """A base for all command client errors."""


class CommandPermissionError(CommandClientError):  # TODO: better name and implement
    __slots__ = ("missing_permissions",)

    missing_permissions: _permission.Permission

    def __init__(
        self, required_permissions: _permission.Permission, actual_permissions: _permission.Permission
    ) -> None:
        pass
        # self.missing_permissions =
        # for permission in m


@attr.attrs(init=True, slots=True)
class CommandError(CommandClientError):

    response: str = attr.attrib()
    """The string response that the client should send in chat if it has send messages permission."""

    def __str__(self) -> str:
        return self.response


@attr.attrs(init=True, repr=True, slots=True)
class ConversionError(CommandClientError):
    msg: str = attr.attrib()
    parameter: typing.Optional[_parser.AbstractParameter] = attr.attrib(default=None)
    origins: typing.Tuple[BaseException, ...] = attr.attrib(factory=list)

    def __str__(self) -> str:
        return self.msg


@attr.attrs(init=True, slots=True)
class FailedCheck(CommandClientError):
    checks: typing.Tuple[typing.Tuple[_commands.CheckLikeT, typing.Optional[BaseException]], ...] = attr.attrib()
