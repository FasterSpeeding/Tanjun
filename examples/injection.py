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
"""Example component which takes advantage of dependency injection."""
import datetime
import typing

import tanjun
from examples import protos

component = tanjun.Component()


@component.with_command
@tanjun.with_guild_check
@tanjun.as_message_command("guild")
async def guild_command(
    # Here we ask for an implementation of the type `DatabaseProto` to be
    # provided as an argument whenever the client calls this command.
    #
    # The implementation for this is provided with Client.set_type_dependency.
    ctx: tanjun.abc.MessageContext,
    database: protos.DatabaseProto = tanjun.inject(type=protos.DatabaseProto),
):
    assert ctx.guild_id is not None  # This is checked by the "with_guild_check"
    guild_info = await database.get_guild_info(ctx.guild_id)

    if not guild_info:
        # HaltExecution will lead to the command being marked as not found,
        # essentially hiding it.
        raise tanjun.HaltExecution

    ...  # TODO: implement response


@component.with_command
@tanjun.as_message_command_group("user")
async def user(
    # Here we ask for an implementation of the type `DatabaseProto` to be
    # provided as an argument whenever the client calls this command.
    #
    # The implementation for this is provided with Client.set_type_dependency.
    ctx: tanjun.abc.MessageContext,
    database: protos.DatabaseProto = tanjun.inject(type=protos.DatabaseProto),
) -> None:
    user = await database.get_user_info(ctx.author.id)

    if not user:
        # CommandError's message will be sent as a response message.
        raise tanjun.CommandError("No information stored for you")

    ...  # TODO: implement response


@user.with_command
@tanjun.as_message_command("remove self")
async def remove_self(
    # Here we ask for an implementation of the type `DatabaseProto` to be
    # provided as an argument whenever the client calls this command.
    #
    # The implementation for this is provided with Client.set_type_dependency.
    ctx: tanjun.abc.MessageContext,
    database: protos.DatabaseProto = tanjun.inject(type=protos.DatabaseProto),
) -> None:
    await database.remove_user(ctx.author.id)


# Since this is being used as an injected callback, we can also ask for an injected type here.
async def _fetch_info(database: protos.DatabaseProto = tanjun.inject(type=protos.DatabaseProto)) -> typing.Any:
    raise NotImplementedError  # This is an example callback and doesn't provide an implementation.


# Since this is being used as an injected callback, we can also ask for an injected type here.
async def _fetch_cachable_info(
    database: protos.DatabaseProto = tanjun.inject(type=protos.DatabaseProto),
) -> typing.Any:
    raise NotImplementedError  # This is an example callback and doesn't provide an implementation.


@component.with_command
@tanjun.as_slash_command("info", "Command description")
async def get_info(
    ctx: tanjun.abc.SlashContext,
    # Here we set _fetch_info as an injected callback.
    #
    # Injected callbacks are callbacks which'll be called before this function is called
    # with the result of it being being passed to the command callback.
    # (note these also support dependency injection).
    info: typing.Any = tanjun.inject(callback=_fetch_info),
    # Here we set _fetch_cachable_info as a cached injected callback.
    #
    # `cached_inject(callback)` is a variant of `inject(callback=callback)`
    # which caches the result of the callback for the provided expire duration.
    cached_info: typing.Any = tanjun.cached_inject(_fetch_cachable_info, expire_after=datetime.timedelta(minutes=30)),
) -> None:
    await ctx.respond(cached_info.format())
    await ctx.respond(info.format())


# Here we define a loader which can be used to easily load this example
# components into a bot from a link (assuming the environment has all the
# right configurations setup.)
@tanjun.as_loader
def load_examples(client: tanjun.Client) -> None:
    client.add_component(component.copy())


# Here we define an unloader which can be used to easily unload and reload
# this example components in a bot from a link.
@tanjun.as_unloader
def unload_examples(client: tanjun.Client) -> None:
    # Since there's no guarantee the stored component will still be the
    # same as component, we remove it by name.
    client.remove_component_by_name(component.name)
