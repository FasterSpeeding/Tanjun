# Usage

This guide is not a conclusive list of the features in Tanjun.

## Starting with Hikari

Tanjun supports both REST server based application command execution and gateway
based message and application command execution, and to run Tanjun you'll want
to link it to a Hikari bot.

```py
bot = hikari.impl.GatewayBot("TOKEN")
client = tanjun.Client.from_gateway_bot(
    bot, declare_global_commands=True, mention_prefix=True
)

...

bot.run()
```

Here a Tanjun client is linked to a gateway bot instance to enable both
message and application command execution.

There's no need to directly start or stop the Tanjun client as the gateway
bot's lifetime events will manage this by default.

`declare_global_commands=True` instructs the client to declare the slash
commands and context menus for the bot its linked to on startup and
`mention_prefix=True` allows the bot's message commands to be triggered
by starting the command call with `@bot`.

```py
async def main():
    bot = hikari.impl.RESTBot("TOKEN", hikari.TokenType.BOT)
    client = tanjun.Client.from_rest_bot(bot, declare_global_commands=True)

    await bot.start()
    async with client:
        await bot.join()
```

And here a Tanjun client is linked to a rest server bot instance to enable
application command execution.

Since Hikari's RESTBot doesn't have lifetime events, we have to startup and
close Tanjun's client around the rest bot ourselves, with it being important
that the bot is started before Tanjun.

### Client lifetime management

While Hikari's bots provides systems for stating and stopping sub-components,
these aren't cross compatible nor Tanjun friendly and Tanjun's client callbacks
provide a cross-compatible alternative for these which support dependency
injection.

```py
client = tanjun.Client.from_gateway_bot(bot)

@bot.with_client_callback(tanjun.ClientCallbackNames.STARTING)
async def on_starting(client: alluka.Injected[tanjun.abc.Client]) -> None:
    client.set_type_dependency(aiohttp.ClientSession, aiohttp.ClientSession())

async def on_closed(session: alluka.Injected[aiohttp.ClientSession]) -> None:
    await session.close()

bit.add_client_callback(tanjun.ClientCallbackNames.CLOSED, on_closed)
```

## Managing bot functionality

[tanjun.components.Component][] exist as a way to manage and grouping bot
functionality, storing functionality event listeners, commands, scheduled
callbacks and client callbacks.

```py
component = tanjun.Component()

@component.with_command
@tanjun.as_slash_command("name", "description")
async def slash_command(ctx: tanjun.abc.SlashContext) -> None:
    ...

@tanjun.with_listener
async def event_listener(event: hikari.Event) -> None:
    ...
```

The `with_` functions on [Component][tanjun.components.Component] allow
functionality such as commands, event listeners and schedles to be loaded into
a component through a deocrator call and the relevant `add_` functions allow
adding functionality through chained calls.

```py
@tanjun.as_message_command("name")
async def command(ctx: tanjun.abc.MessageContext) -> None:
    ...

component = tanjun.Component().load_from_scope()
```

Alternatively, functionality which is represented by a dedicated object can be
implicitly loaded from a module's global scope using
[load_from_scope][tanjun.components.Component.load_from_scope] rather than
explicitly calling `with_` and `add_` methods.

<!-- ### Component lifetimes

[with_on_open][tanjun.components.Component.with_on_open] [with_on_close][tanjun.components.Component.with_on_open] -->

### Loading modules

Components are usually used to represent the functionality in a single Python
module and, while [add_component][tanjun.abc.Client.add_component] can be used
to directly add a component to a client, you can declare "loaders" and "unloaders"
for a module to ease the flow

```py
component = tanjun.Component().load_from_scope()

@tanjun.as_loader
def load(client: tanjun.Client) -> None:
    client.add_component(component)

@tanjun.as_unloader
def unload(client) -> None:
    client.remove_component(component)
```

either by declaring a custom loader and unloader

```py
component = tanjun.Component().load_from_scope()

loader = component.make_loader()
```

or by using [make_loader][tanjun.components.Component.make_loader] to generate
a loader and unloader for the component.

```py
(
    tanjun.Client.from_gateway_bot(bot)
    .load_directory("./bot/components", namespace="bot.components")
    .load_modules("bot.owner")
)
```

These modules with loaders can then be loaded into a client by calling
[load_directory][tanjun.abc.Client.load_directory] to load from all the
modules in a directory or [load_modules][tanjun.abc.Client.load_modules] to
load a specific module.

<!-- ### Hot reloading -->

## Declaring commands

Commands need to be contained within a component to be loaded into a client
and may either be loaded using
[Component.add_command][tanjun.components.Component.add_command]/
[Component.with_command][tanjun.components.Component.with_command]
(where add is chainable and with is a decorator callback) or implicitly
using [Component.load_from_scope][tanjun.components.Component.load_from_scope].

All command callbacks must be asynchronous and can use dependency injection.

### Slash commands

```py
@tanjun.with_str_slash_option("option", "description")
@tanjun.as_slash_command("name", "description")
async def slash_command(
    ctx: tanjun.abc.SlashContext
) -> None:
    ...
```

Slash commands represent the commands you see when you start typing in the
message box with "/" on Discord and have both names (which follow the
restraints shown in  <https://discord.com/developers/docs/dispatch/field-values#predefined-field-values-accepted-locales>)
and descriptions (which can be up to 100 characters long).

There are several different kinds of slash command arguments which all require
an argument name and description (which follow the sme restraints as
the command name and description) along with type specific configuration and
can be configured using the following or their `add_{type}_option` equivalent
chainable methods on [SlashCommand][tanjun.commands.slash.SlashCommand]:

* [with_attachment_slash_option][tanjun.commands.slash.with_attachment_slash_option]
* [with_bool_slash_option][tanjun.commands.slash.with_bool_slash_option]
* [with_channel_slash_option][tanjun.commands.slash.with_channel_slash_option]
* [with_float_slash_option][tanjun.commands.slash.with_float_slash_option]
* [with_int_slash_option][tanjun.commands.slash.with_int_slash_option]
* [with_member_slash_option][tanjun.commands.slash.with_member_slash_option]
* [with_mentionable_slash_option][tanjun.commands.slash.with_mentionable_slash_option]
* [with_role_slash_option][tanjun.commands.slash.with_role_slash_option]
* [with_str_slash_option][tanjun.commands.slash.with_str_slash_option]
* [with_user_slash_option][tanjun.commands.slash.with_user_slash_option]

Most notably, specifically string arguments support converters (and the
standard converters found in [tanjun.conversion][]) in a similar fashion to
message command arguments.

```py
ding_group = tanjun.slash_command_group("ding", "ding group")


@ding_group.as_sub_command("dong", "dong command")
async def dong_command(ctx: tanjun.abc.SlashContext) -> None:
    ...


ding_ding_group = ding.make_sub_group("ding", "ding ding group")

@ding_ding_group.as_sub_command("ding", "ding ding ding command")
async def ding_command(ctx: tanjun.abc.SlashContext) -> None:
    ...
```

Slash commands can be stored in groups where the above example will be shown in
the command menu as `"ding dong"` and `"ding ding ding"`. Unlike message command
groups, slash command groups cannot be directly called as commands and can only
be nested up once. To see more information on how slash command groups can be
configured see [slash_command_group][tanjun.commands.slash.slash_command_group].

### Message commands

```py
tanjun.Client.from_gateway_bot(gateway_bot).add_prefix("!")

...

@tanjun.with_option("reason", "--reason", "-r", default=None)  # This can be triggered as --reason or -r
@tanjun.with_multi_option("users", "--user", "-u", default=None)  # This can be triggered as --user or -u
@tanjun.with_greedy_argument("content")
@tanjun.with_argument("days", converters=int)
@tanjun.as_message_command("meow command", "description")
async def message_command(
    ctx: tanjun.abc.MessageContext
) -> None
    ...
```

Message commands are executed based on chat messages where any prefixes added
to the client will be used to match for executable message commands (the above
example would match messages starting with `"!meow command"`) and without any
set prefixes message commands just won't execute. Since these are executed
based on messages they can only be executed when linkde to a gateway bot and
require the MESSAGE_CONTENT intent to be declared.

To allow for executing a command by mentioning the bot before the command name
(e.g. `@BotGirl meow command`) you can pass `mention_prefix=True` to either
[Client.from_gateway_bot][tanjun.clients.Client.from_gateway_bot] or
[Client.\_\_init\_\_][tanjun.clients.Client.__init__] while creating the bot.

```py
# prefixes=["!"]

@tanjun.as_message_command_group("groupy")
async def groupy_group(ctx: tanjun.abc.MessageContext)
    ...


@groupy_group.as_sub_command("sus drink")
async def sus_drink_command(ctx: tanjun.abc.MessageContext):
    ...


@groupy_group.as_sub_group("tour")
async def tour_group(ctx: tanjun.abc.MessageContext):
    ...


@tour_group.as_sub_command("de france")
async def de_france_command(ctx:tanjun.abc.MessageContext):
    ...
```

Message command groups are a collection of message commands under a shared name
and (unlike slash commands) can also be directly executed as a command. The above
example would have the following commands: `"!groupy"`, `!"groupy tour"`,
`"groupy tour de france"` and `"groupy sus drink"`. To see more information on
how message command groups can be configured see
[as_message_command_group][tanjun.commands.message.as_message_command_group].


#### Argument parsing

Message command argument parsing always handles string arguments and to declare
parsed arguments you can use one of the `with_option` or `with_argument` methods
in [tanjun.parsing][]; while options are optional arguments which are passed
based on a flag name (e.g. `"--key"`), arguments are passed positonally.
It's worth noting that since decorators are executed from the bottom upwards
positional arguments will follow the same order.

Arguments and options have multiple parsing approaches, by default they just
parse 1 value but "multi" (can be applied to both) indicates that multiple
values should be allowed/parsed with these being passed as a list of values
or greedy (argument only) indicating that an argument should parse the rest
of the positional data as 1 big string which includes spaces.

The most helpful configuration for options and arguments is converters, these
are at one or more callbacks which may be called to try and convert the value
where the result of first which passes (doesn't raise a [ValueError][] will be
used); other configuration can be seen in [tanjun.parsing][] and standard
converters can be found in [tanjun.conversion][].

### Context menus

```py
@component.with_command
@tanjun.as_message_menu("name")
async def message_menu_command(ctx: tanjun.abc.MenuContext, message: hikari.message) -> None:
    ...

@component.with_command
@tanjun.as_user_menu("name")
async def user_menu_command(ctx: tanjun.abc.MenuContext, user: hikari.User) -> None:
    ...
```

Context menus represent the application commands shown when you click on a user
or message in Discord and, unlike slash and message commands, do not have
configurable arguments nor groups. These are created pretty easily as shown
above; for more information on configuring menu commands see
[tanjun.as_message_menu][tanjun.commands.menu.as_message_menu].

### Slash command autocomplete

Autocomplete is a slash command exclusive feature which allows for processing
partial input for string arguments and returning dynamic choices.

Unlike application commands, autocomplete can't defer and must return within 3
seconds. These callbacks must be asynchronous and support dependency injection.

```py
@component.with_command
@tanjun.with_str_slash_option("opt1", "description")
@tanjun.with_str_slash_option("opt2", "description", default=None)
@tanjun.as_slash_command
async def slash_command(
    ctx: tanjun.abc.SlashContext,
    opt1: str,
    opt2: str | None,
) -> None:
    ...


@slash_command.with_str_autocomplete("opt1")
async def opt1_autocomplete(ctx: tanjun.abc.AutocompleteContext, value: str) -> None:
    await ctx.set_choices()


async def opt2_autocomplete(ctx: tanjun.abc.AutocompleteContext, value: str) -> None:
    await ctx.set_choices()


slash_command.set_str_autocomplete("opt2", opt2_autocomplete)
```

### Annotation based command declaration

Previously you've seen how to declare manually declare command options per
command type, now its time to go higher.

```py
from typing import Annotated

import tanjun
from tanjun.annotations import Bool, Ranged, Str, User


@tanjun.with_annotated_args(follow_wrapped=true)
@tanjun.as_slash_command("name", "description")
@tanjun.as_message_command("name")
async def command(
    ctx: tanjun.abc.Context,
    name: Annotated[Str, "description"],
    age: Annotated[Ranged[13, 130], "an int option with a min, max or 13, 130"],
    video: Annotated[Converted[get_video], "a string option which is converted with get_video"],
    user: Annotated[User, "an optional user option which defaults to None"] = None,
    enabled: Annotated[Bool, "an optional bool option which defaults to True"] = True,
) -> None:
    ...
```

[tanjun.with_annotated_args][tanjun.annotations.with_annotated_args] provides
a simple way to declare the arguments for both message and slash commands.
While this feature is cross-compatible there is one key difference, slash
commands specifically require that a description for the option be passed as a
separate string field to [typing.Annotated][] and message commands juts ignore
this description.

The special generic types it offers like [Ranged][tanjun.annotations.Ranged] and
[Converted][tanjun.annotations.Converted] use [typing.Annotated][] to complete
that generic call and can also be passed as arguments to Annotated like
`Annotated[Int, Ranged(13, 130)]` and `Annotated[Str, Converted(get_video)]`.

This example doesn't demonstrate every future of this and more information on
how arguments can be configured through annotations can be seen in
[tanjun.annotations][tanjun.annotations].

### Wrapped commands

When creating multiple command types in a decorator call chain, standard
decorators which can be applied to multiple command types often have a
`follow_wrapped` argument which will apply them to all the compatible
commands in a chain if [True][] is passed for it.

When using `follow_wrapped` the relevant decorator must be above any
`as_{}_command` decorator calls in the chain.

```py
@tanjun.with_annotated_args(follow_wrapped=True)
@tanjun.with_guild_check(follow_wrapped=True)
@tanjun.as_slash_command("name", "description")
@tanjun.as_message_command("name")
async def command(ctx: tanjun.abc.Context) -> None:
    ...
```

It's worth noting that, while the previous command examples have typed `ctx` as
a context type that's specific to the command type,
[abc.Context][tanjun.abc.Context] is the base for all these (except the
autocomplete context) and may be used as the type for `ctx` when a callback
supports multiple command types.

## Dependency injection

Tanjun supports type based dependency injection as a type-safe approach for
handling global state for most of the callbacks it takes (e.g. command
callbacks, checks, hook callbacks, event listeners, schedule callbacks) through
Alluka.

```py
(
    tanjun.Client.from_gateway_bot(bot)
    .set_type_dependency(Foo, Foo())
    .set_type_dependency(Bar, Bar())
)
```

Here we set the dependencies for the types `Foo` and `Bar`.

```py
@tanjun.as_slash_command("name", "description")
async def command(
    ctx: tanjun.abc.SlashContext,
    foo_impl: alluka.Injected[Foo],
    bar_impl: Bar = alluka.inject(type=Bar),
) -> None:
    ...
```

And here we declare a command callback as taking the declared implementations
of `Foo` and `Bar` as keyword arguments using two different approaches.
Since both arguments provide no default these command calls will fail if no
implementation for `Foo` or `Bar` has been set using `set_type_dependency`.

A more detailed guide on how this works and the full feature set (e.g. optional
dependencies) can be found [https://alluka.cursed.solutions/usage/](here).
[alluka.abc.Client][] is exposed at [Client.injector][tanjun.abc.Client.injector].

### Standard and special cased injected types.

The following types are registered globally as type dependencies:

* [tanjun.abc.Client][]
* [tanjun.clients.Client][]
* [tanjun.dependencies.AbstractOwners][] (for use with the standard owner check).
* `tanjun.LazyConstant[hikari.OwnUser]` (for use with `tanjun.inject_lc(hikari.OwnUser)`)
* [hikari.api.rest.RESTClient][]
* [hikari.api.cache.Cache][] \*
* [hikari.api.event_manager.EventManager][] \*
* [hikari.api.interaction_server.InteractionServer][] \*
* [hikari.traits.ShardAware][] \*
* [hikari.api.voice.VoiceComponent][] \*

\* These type dependencies are only registered if the relevant Hikari component
    was included while creating the [tanjun.clients.Client][] instance.

The following type dependencies are available in specific contexts:

* [tanjun.abc.AutocompleteContext][]: slash command autocomplete execution
* [tanjun.abc.AppCommandContext][]: both slash and menu command execution (excluding any checks)
* [tanjun.abc.MenuContext][]: menu command execution
* [tanjun.abc.MessageContext][]: message command execution
* [tanjun.abc.SlashContext][]: slash command execution
<!-- * [tanjun.abc.MenuCommand][]: menu command execution (excluding any checks)
* [tanjun.abc.MessageCommand][]: message command execution (excluding any checks)
* [tanjun.abc.SlashCommand][]: slash command execution (excluding any checks)
TODO: this needs a consistency fix before being documented -->
* [tanjun.abc.Component][]: Command execution (excluding client checks)
<!-- * [hikari.events.base_events.Event][] TODO: implement this-->

Both [Client.from_gateway_bot][tanjun.clients.Client.from_gateway_bot] and
[Client.from_rest_bot][tanjun.clients.Client.from_rest_bot] register type
dependencies for the relevant [hikari traits][hikari.traits] which the bot is
compatible with. You can get this behaviour after directly initialising
[tanjun.clients.Client][tanjun.Client] without a from method by calling
[Client.set_hikari_trait_injectors][tanjun.clients.Client.set_hikari_trait_injectors]
with the relevant bot object.

## Advanced command flow management

### Checks

Checks are simple to understand, they are functions which run before command
execution to decide whether a command or group of commands match a context.

```py
@tanjun.with_guild_check(follow_wrapped=True)
@tanjun.with_author_permission_check(hikari.Permissions.BAN_MEMBERS)
@tanjun.with_own_permission_check(hikari.Permissions.BAN_MEMBERS, follow_wrapped=True)
@tanjun.as_message_command("name")
@tanjun.as_slash_command("name", "description", default_member_permissions=hikari.Permissions.BAN_MEMBERS)
async def command(ctx: tanjun.abc.Context) -> None:
    ...
```

There's a collection of standard checks in [tanjun.checks][] which are all
exported top level and work with all the command types, the only
configuration most users will care about for these is `error_message` argument
which lets you adjust the response these gives when they fail but the
permission checks also need a required permission to be passed positionally.

```py
component = (
    tanjun.Component()
    .add_check(tanjun.GuildCheck())
    .add_check(tanjun.AuthorPermissionCheck(hikari.Permissions.BAN_MEMBER))
    .add_check(tanjun.OwnPermissionCheck(hikari.Permissions.BAN_MEMBER))
)

@component.with_check
async def db_check(ctx: tanjun.abc.Context, db: alluka.Injected[Db]) -> None:
    if (await db..get_user(ctx.author.id)).banned:
        raise tanjun.CommandError("You are banned from using this bot")

    raise False


@tanjun.with_owner_check(follow_wrapped=True)
@tanjun.as_message_command("name")
@tanjun.as_slash_command("name", "description")
async def owner_only_command(ctxL tanjun.abc.Context):
    ...
```

Checks (both custom and standard) can be added to clients, components and
commands using either the chainable `add_check` method or the decorator
style `with_check` method with the standard checks providing `with_...`
decorators which can be applied to commands to add the check and checks
on a client, component or command group will be used for every child
command.

```py
def check(ctx: tanjun.abc.Context) -> bool:
    if ctx.author.discriminator % 2:
        raise tanjun.CommandError("You are not one of the chosen ones")

    return True
```

A custom check can be implemented by making a function with either the signature
`def (tanjun.abc.Context, ...) -> bool` or `async def (tanjun.abc.Context, ...) -> bool`
where [dependency injection][dependency-injection] is supported, returning
`True` indicates that the check passed and returning `False` indicates that the
check failed and the client should continue looking for a matching command. You
will most likely want to raise [CommandError][tanjun.errors.CommandError] to
end command execution with a response rather than carrying on with the command
search.

### Execution hooks

Command hooks are callbacks which are called around command execution, these
are contained within [Hooks][tanjun.hooks.Hooks] objects which may be added
to a command, client or component using `set_hooks` where hooks on a client,
component or command group will be callde for every child command.

There are several different kinds of hooks which all support dependency
injection and may be synchronous or asynchronous:

```py
hooks = tanjun.AnyHooks()

@hooks.with_pre_execution  # hooks.add_pre_execution
async def pre_execution_hook(ctx: tanjun.abc.Context) -> None:
    ...
```

Pre-execution are called before the execution of a command (so after command
matching has finished and all the checks have passed).

```py
@hooks.with_pre_execution  # hooks.add_pre_execution
async def pre_execution_hook(ctx: tanjun.abc.Context) -> None:
    ...
```

Post-executon hooks are called after a command has finished executing,
regardless of whether it passed or failed.

```py
@hooks.with_on_success  # hooks.add_success_hook
async def success_hook(ctx: tanjun.abc.Context) -> None:
    ...
```

Success hooks are called after a command has finished executing, if it
succeeded (didn't raise any errors).

```py
@hooks.with_on_error  # hooks.add_on_error
async def error_hook(ctx: tanjun.abc.Context, error: Exception) -> bool | None:
    ...
```

Error hooks are called when command's execution is ended early by an error raise
which isn't a [ParserError][tanjun.errors.ParserError],
[CommandError][tanjun.errors.CommandError] or
[HaltExecution][tanjun.errors.HaltExecution] (as these are special cased).

```py
@hooks.add_on_parser_error  # hooks.add_on_parser_error
async def parser_error_hook(ctx: tanjun.abc.Context, error: tanjun.ParserError)
```

Parser error hooks are called when the argument parsing of a message command
failed.

### Concurrency limiter

Concurrency limiters allow you to limit how many calls can be made to a group
of commands concurrently.

```py
client = tanjun.Client.from_gateway_bot(bot)
(
    tanjun.InMemoryConcurrencyLimiter()
    .set_bucket("main_commands", tanjun.BucketResource.USER, 2)
    .disable_bucket("plugin.meta")
    .add_to_client(client)
)
```

Here [InMemoryConcurrencyLimiter][tanjun.dependencies.InMemoryConcurrencyLimiter]
will manage the concurrency limits for all the commands in this bot instance with
[Limiter.set_bucket][tanjun.dependencies.InMemoryConcurrencyLimiter.set_bucket]
being called to limit the bucket `"main_commands"` to at most 2 concurrent executions per user,
[Limiter.disable_bucket][tanjun.dependencies.InMemoryConcurrencyLimiter.disable_bucket]
being called to ensure that the bucket `"plugin.meta"` has no concurrency limit
as unconfigured buckets will default to the configuration for the `"default"` bucket, and
[Limiter.add_to_client][tanjun.dependencies.InMemoryConcurrencyLimiter.add_to_client]
being used to set this limiter for a client (note that clients can only have 1
linked limiter).

```py
@tanjun.with_concurrency_limit("main_commands", follow_wrapped=True)
@tanjun.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("name")
@tanjun.as_slash_command("name", "description")
@tanjun.as_user_menu("name")
async def user_command(
    ctx: tanjun.abc.Context,
    user: Annotated[annotations.User, "A user"],
) -> None:
    ...
```

And here we use [with_concurrency_limit][tanjun.dependencies.with_concurrency_limit]
to mark these commands as using the `"main_commands"` concurrency limit bucket;
buckets share their limits for a resource across all the commands under it for,
for more information on the resources concurrency can be limited by see
[BucketResource][tanjun.dependencies.BucketResource].

### Cooldowns

Cooldowns limit how often a group of commands can be called.

```py
client = tanjun.Client.from_gateway_bot(bot)
(
    tanjun.InMemoryCooldownManager()
    .set_bucket("main_commands", tanjun.BucketResource.USER, 5, 60)
    .disable_bucket("plugin.meta")
    .add_to_client(client)
)
```

Here [InMemoryCooldownManager][tanjun.dependencies.InMemoryCooldownManager]
will manage the cooldowns for all the commands in this bot instance with
[Manager.set_bucket][tanjun.dependencies.InMemoryCooldownManager.set_bucket]
being called to limit the bucket `"main_commands"` to 5 calls every 60 seconds per user,
[Manager.disable_bucket][tanjun.dependencies.InMemoryCooldownManager.disable_bucket]
being called to ensure that the bucket `"plugin.meta"` has no cooldowns as
unconfigured buckets will default to the configuration for the `"default"` bucket, and
[Manager.add_to_client][tanjun.dependencies.InMemoryCooldownManager.add_to_client]
being used to set this cooldown manager for a client (note that clients can
only have 1 linked cooldown manager).

```py
@tanjun.with_cooldown("main_commands", follow_wrapped=True)
@tanjun.with_annotated_args(follow_wrapped=True)
@tanjun.as_message_command("name")
@tanjun.as_slash_command("name", "description")
@tanjun.as_user_menu("name")
async def user_command(
    ctx: tanjun.abc.Context,
    user: Annotated[annotations.User, "A user"],
) -> None:
    ...
```

And here we use [with_cooldown][tanjun.dependencies.with_cooldown]
to mark these commands as using the `"main_commands"` cooldown bucket;
buckets share their cooldowns for a resource across all the commands under it,
for more information on the resources cooldowns can be set for
[BucketResource][tanjun.dependencies.BucketResource].

<!-- # TODO: some day, document buildings commands using the flient interface -->
