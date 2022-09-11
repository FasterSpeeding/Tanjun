# Usage

## Starting with Hikari

Tanjun support both To run Tanjun you'll want to link it to a Hikari bot.

```py
```

```py
```

### Client lifetime management

## Loading resources

### Hot reloading

## Declaring commands

### Slash commands

#### Arguments

### Message commands

#### Arguments

### Context menus

### Slash command autocomplete

### Annotation based command declaration

## Dependency injection

Tanjun supports type based dependency injection as a type-safe approach for
handling global state for most of the callbacks it takes (e.g. command
callbacks, checks, hook callbacks, schedule callbacks) through Alluka.

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
of `Foo` and `Bar` as the keyword arguments `foo_impl` and `bar_impl` using the
two different approaches for marking an argument as injected. Since both
arguments provide no default these command calls will fail if no implementation
for `Foo` or `Bar` is set using `set_type_dependency`.

A more detailed guide on how this works and the full feature set (e.g. optional
dependencies) can be found [https://alluka.cursed.solutions/usage/][here].
[alluka.abc.Client][] is exposed at [tanjun.abc.Client.injector][].

### Standard and special cased injected types.

By standard the following types are registered as type dependencies if they're
available.

* [tanjun.abc.Client][]
* [tanjun.clients.Client][]
* [hikari.api.rest.RESTClient][]
* [hikari.api.cache.Cache][]
* [hikari.api.event_manager.EventManager][]
* [hikari.api.interaction_server.InteractionServer]
* [hikari.traits.ShardAware][]
* [hikari.api.voice.VoiceComponent][]

## Advanced command flow management

### Execution hooks

### Checks

### Limiters
