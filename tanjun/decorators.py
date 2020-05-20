import typing

from hikari.events import base as base_events

from . import commands as commands


# TODO: here or commands


def group(
    name: str,
    *,
    group_class: typing.Type[commands.AbstractCommandGroup] = commands.CommandGroup,
    command_class: typing.Type[commands.AbstractCommand] = commands.Command,
    **kwargs,
):  # TODO: test this
    def decorator(coro_fn):
        return group_class(name=name, master_command=command_class(coro_fn, name=""), **kwargs)

    return decorator


def event(event_: base_events.HikariEvent):  # TODO: typing annotation support
    def decorator(coro_fn):
        coro_fn.__event__ = event_
        return coro_fn

    return decorator


def command(__arg=..., *, cls: typing.Type[commands.AbstractCommand] = commands.Command, **kwargs):
    def decorator(coro_fn):
        return cls(coro_fn, **kwargs)

    return decorator if __arg is ... else decorator(__arg)
