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
"""Basic usage of Tanjun's message command system."""
import time

import tanjun

component = tanjun.Component()


@component.with_command
@tanjun.as_message_command("ping")
async def ping(ctx: tanjun.abc.Context, /) -> None:
    start_time = time.perf_counter()
    await ctx.respond(content="Nyaa master!!!")
    time_taken = (time.perf_counter() - start_time) * 1_000
    heartbeat_latency = ctx.shards.heartbeat_latency * 1_000 if ctx.shards else float("NAN")
    await ctx.edit_last_response(f"PONG\n - REST: {time_taken:.0f}ms\n - Gateway: {heartbeat_latency:.0f}ms")


@tanjun.as_message_command_group("note", "notes")
async def note(ctx: tanjun.abc.Context) -> None:
    await ctx.respond("You have zero notes")


@note.with_command
@tanjun.with_greedy_argument("value")
@tanjun.with_argument("name")
@tanjun.as_message_command("add", "create")
async def note_add(ctx: tanjun.abc.Context, name: str, value: str) -> None:
    ...  # Actual implementation
    await ctx.respond(f"Added {name} note with value {value}")


@note.with_command
@tanjun.with_option("force", "--force", "-f", converters=(bool,), default=False)
@tanjun.with_argument("name")
@tanjun.as_message_command("remove", "delete")
async def note_remove(ctx: tanjun.abc.Context, name: str, force: bool) -> None:
    ...  # Actual implementation
    await ctx.respond(f"Force removed {name} note" if force else f"Removed {name} note")


# Here we define a loader which can be used to load this example
# components into a bot from a link (assuming the environment has all the
# right configurations setup).
#
# Alternatively component.make_loader() can be used as a shorthand for both
# as_loader and as_unloader.
@tanjun.as_loader
def load_examples(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())


# Here we define an unloader which can be used to unload and reload
# this example components in a bot from a link.
#
# Alternatively component.make_loader() can be used as a shorthand for both
# as_loader and as_unloader.
@tanjun.as_unloader
def unload_examples(client: tanjun.Client) -> None:
    # Since there's no guarantee the stored component will still be the
    # same as component, we remove it by name.
    client.remove_component_by_name(component.name)
