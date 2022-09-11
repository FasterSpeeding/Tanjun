# Usage

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
provide a DI and cross-compatible alternative for these.

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

[tanjun.components.Components][] exist as a way to manage and grouping bot
functionality, storing functionality event listeners, commands, scheduled
callbacks and client callbacks.

```py
component = tanjun.Component()

@component.with_command
@tanjun.as_slash_command("name", "description")
async def slash_command(ctx: tanjun.abc.SlashContext) -> None:
    ...

@component.with_command
@tanjun.as_message_command("name")
async def slash_command(ctx: tanjun.abc.SlashContext) -> None:
    ...

@component.with_command
@tanjun.as_slash_command()
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
    raise NotImplemented

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
    .load_module("bot.owner")
)
```

These modules with loaders can then be loaded into a client by calling
[load_directory][tanjun.clients.Client.load_directory] to load from all the
modules in a directory or [load_module][tanjun.clients.Client.load_module] to
load a specific module.

<!-- ### Hot reloading -->

## Declaring commands

### Slash commands

#### Arguments

#### Groups

### Message commands

#### Arguments

#### Groups

### Context menus

Context menus represent and, unlike slash and message commands, do not have
configurable arguments nor groups.

### Slash command autocomplete

### Annotation based command declaration

### Wrapped commands

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
    raise NotImplementedError
```

And here we declare a command callback as taking the declared implementations
of `Foo` and `Bar` as keyword arguments using two different approaches.
Since both arguments provide no default these command calls will fail if no
implementation for `Foo` or `Bar` has been set using `set_type_dependency`.

A more detailed guide on how this works and the full feature set (e.g. optional
dependencies) can be found [https://alluka.cursed.solutions/usage/](here).
[alluka.abc.Client][] is exposed at [tanjun.abc.Client.injector][].

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

Both [tanjun.clients.Client.from_gateway_bot][] and [tanjun.clients.Client.from_rest_bot][]
register type dependencies for the relevant [hikari traits][hikari.traits]
which the bot is compatible with. You can get this behaviour after directly
initialising [tanjun.clients.Client][] without a from method by calling
[tanjun.clients.Client.set_hikari_trait_injectors][] with the relevant bot object.

## Advanced command flow management

### Execution hooks

### Checks

### Limiters
