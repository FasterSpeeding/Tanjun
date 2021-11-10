# -*- coding: utf-8 -*-
# cython: language_level=3
# Tanjun Examples - A collection of examples for Tanjun.
# Written in 2021 by Lucina Lucina@lmbyrne.dev
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain worldwide.
# This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <https://creativecommons.org/publicdomain/zero/1.0/>.
"""Examples of how hooks may be used within a bot with a focus on error handling."""
import typing

import hikari

import tanjun

# While this example uses AnyHooks (which are hooks that can be used between
# both the slash command and message command flows in a similar fashion to
# checks which take `tanjun.abc.Context`), there's also `tanjun.SlashChecks`
# and `tanjun.MessageChecks` which are specialised for the relevant flows.
hooks = tanjun.AnyHooks()


@hooks.with_on_error
async def on_error(ctx: tanjun.abc.Context, exc: Exception) -> typing.Optional[bool]:
    """General error handler.

    This will be called on all errors raised during execution except errors
    derived from and including the following errors: `tanjun.CommandError`,
    `tanjun.HaltExecution` and `tanjun.ParserError`.

    To handle parser errors see `tanjun.Hooks.with_on_parser_error`.

    This must have take following positional arguments and return type:

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The command context this error was raised for.
    exc : Exception
        The error which was raised.

    Returns
    -------
    typing.Optional[bool]
        The return type indicates whether this hook wants the error to be
        suppressed where `True` indicates that it should be suppressed,
        `False` indicates that it should be re-raised and `None` indicates
        no decision.

        This value will be considered along with the results of any other hooks
        being called during execution by a majority rule system and if all
        hooks return `None` then the error will be raised.
    """


@hooks.with_on_parser_error
async def on_parser_error(ctx: tanjun.abc.Context, exc: tanjun.ParserError) -> None:
    """Parser error handler.

    This will be called on all parser errors raised during execution.

    It should be noted that `tanjun.Client` comes with a default parser error
    handler and calling `Client.set_hooks` will remove said handler.

    This must have the following positional arguments and return type:

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The command context this error was raised for.
    exc : Exception
        The parser error which was raised.

    Returns
    -------
    None
        Unlike general error handlers, parser errors are always suppressed if
        they're handled by a hook.
    """


@hooks.with_on_success
async def on_success(ctx: tanjun.abc.Context) -> None:
    """On success error hook.

    This will be called after a command has finished execution without raising
    any errors.

    This must have the following positional arguments and return None:

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The context of the passed command
    """


@hooks.with_post_execution
async def post_execution(ctx: tanjun.abc.Context) -> None:
    """Post-execution hook.

    This will be called after a command has finished executing regardless of
    whether it errors or passed.

    This must have the following positional arguments and return None:

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The context being executed.
    """


@hooks.with_pre_execution
async def pre_execution(ctx: tanjun.abc.Context) -> None:
    """Pre-execution hook.

    This will be called before a command has been executed.

    This must have the following positional arguments and return None:

    Parameters
    ----------
    ctx : tanjun.abc.Context
        The context being executed.
    """


# Note that these can also be set using chained "set" methods as shown below.

hooks = (
    tanjun.AnyHooks()
    .add_on_parser_error(on_parser_error)
    .add_on_error(on_error)
    .add_on_success(on_success)
    .add_pre_execution(pre_execution)
    .add_post_execution(post_execution)
)


# AnyHooks, MessageHooks and SlashHooks may be added to commands (and command groups):


@hooks.add_to_command  # Through a decorator call
@tanjun.as_slash_command("name", "description")
async def slash_command(ctx: tanjun.abc.Context) -> None:
    ...


slash_command.set_hooks(hooks)  # or using a chainable method on the command.
# Where the hooks added to a specific command will only ever be called for said command.

# Components:


component = tanjun.Component().set_hooks(hooks)
# Where hooks set with Component.set_hooks will be called for all commands
# within the component but hooks set with `set_message_hooks` and `set_slash_hooks`
# will only be run for the message commands or slash commands within the component.


# and Clients:

bot = hikari.GatewayBot("TOKEN")
client = tanjun.Client.from_gateway_bot(bot).set_hooks(hooks)
# Where hooks set with Component.set_hooks will be called for all commands
# within the client's components but hooks set with `set_message_hooks` and `set_slash_hooks`
# will only be run for the message commands or slash commands within the client's components.
