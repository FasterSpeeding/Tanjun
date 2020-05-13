import typing

from hikari.events import base as _base_events

from tanjun import commands as _commands


# TODO: here or commands


def group(
    name: str,
    *,
    group_class: typing.Type[_commands.AbstractCommandGroup] = _commands.CommandGroup,
    command_class: typing.Type[_commands.AbstractCommand] = _commands.Command,
    **kwargs,
):  # TODO: test this
    def decorator(coro_fn):
        return group_class(name=name, master_command=command_class(coro_fn, name=""), **kwargs)

    return decorator


def event(event_: _base_events.HikariEvent):  # TODO: typing annotation support
    def decorator(coro_fn):
        coro_fn.__event__ = event_
        return coro_fn

    return decorator


def command(__arg=..., *, cls: typing.Type[_commands.AbstractCommand] = _commands.Command, **kwargs):
    def decorator(coro_fn):
        return cls(coro_fn, **kwargs)

    return decorator if __arg is ... else decorator(__arg)
