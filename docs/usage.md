# Usage

This guide is not a conclusive list of the features in Tanjun.

You'll want to have some basic understanding of Hikari before you start
using Tanjun. A basic Hikari guide can be found [here](https://hg.cursed.solutions/).

## Starting with Hikari

Tanjun supports both REST server-based application command execution, and
gateway-based message and application command execution. To run Tanjun
you'll want to link it to a Hikari bot.

```py
--8<-- "./docs_src/usage.py:26:31"
```

Here a Tanjun client is linked to a gateway bot instance to enable both
message and application command execution.

There's no need to directly start or stop the Tanjun client as it'll be managed
by lifetime events (unless `event_managed=False` is passed).

`declare_global_commands=True` instructs the client to declare the bot's slash
commands and context menus on startup, and `mention_prefix=True` allows the
bot's message commands to be triggered by starting a command call with `@bot`.

```py
--8<-- "./docs_src/usage.py:35:37"
```

And here a Tanjun client is linked to a REST server bot instance to enable
application command execution.

Unlike when linked to a Gateway bot, `bot_managed=True` must be explicitly
passed to [Client.from_rest_bot][tanjun.clients.Client.from_rest_bot] to
have the client automatically start when the Rest bot starts.

### Client lifetime management

While Hikari's bots provide systems for starting and stopping sub-components,
these aren't cross-compatible nor Tanjun friendly; Tanjun's client callbacks
provide a cross-compatible alternative for these (which also supports dependency
injection).

```py
--8<-- "./docs_src/usage.py:41:50"
```

## Managing bot functionality

[tanjun.Component][tanjun.components.Component] exists as a way to manage and
group bot functionality, storing functionality such as event listeners,
commands, scheduled callbacks, and client callbacks.

```py
--8<-- "./docs_src/usage.py:54:63"
```

The `with_` methods on [Component][tanjun.components.Component] allow
loading functionality like commands, event listeners, and schedules into it
through a decorator call; the relevant `add_` functions allow adding
functionality through chained calls.

```py
--8<-- "./docs_src/usage.py:67:71"
```

Alternatively, functionality which is represented by a dedicated object can be
implicitly loaded from a module's global scope using
[Component.load_from_scope][tanjun.components.Component.load_from_scope]
rather than directly calling `with_` and `add_` methods.

<!-- ### Component lifetimes

[with_on_open][tanjun.components.Component.with_on_open] [with_on_close][tanjun.components.Component.with_on_open] -->

### Loading modules

Components are used to represent the functionality in a Python module.
While [add_component][tanjun.abc.Client.add_component] can be used to directly
add a component to a client, you can also declare "loaders" and "unloaders" for
a module to more ergonomically load this functionality into a client.

```py
--8<-- "./docs_src/usage.py:75:83"
```

You can either declare one or more custom loaders and unloaders as shown above

```py
--8<-- "./docs_src/usage.py:87:89"
```

or use [make_loader][tanjun.components.Component.make_loader] to generate a
loader and unloader for the component.

```py
--8<-- "./docs_src/usage.py:93:97"
```

Modules with loaders can then be loaded into a client by calling
[load_directory][tanjun.abc.Client.load_directory] to load from all the
modules in a directory or [load_modules][tanjun.abc.Client.load_modules] to
load specific modules.

<!-- ### Hot reloading -->

## Declaring commands

Commands need to be in a component for them to be loaded into a client
and may be added to a component either directly using
[Component.add_command][tanjun.components.Component.add_command]/
[Component.with_command][tanjun.components.Component.with_command]
(where add is chainable and with is a decorator callback) or implicitly
using [Component.load_from_scope][tanjun.components.Component.load_from_scope].

All command callbacks must be asynchronous and can use dependency injection.

### Slash commands

```py
--8<-- "./docs_src/usage.py:101:104"
```

Slash commands represent the commands you see when you start typing with "/" in
Discord's message box and have names (which follow the restraints listed in
[Discord's documentation](https://discord.com/developers/docs/interactions/application-commands#application-command-object-application-command-naming))
and descriptions (which can be up to 100 characters long).

There are several different kinds of slash command arguments which all need
a name and description (both of which have the same constraints as the relevant
slash command fields) along with type-specific configuration. These can be
configured using the following decorator functions and their `add_{type}_option`
equivalent chainable methods on [SlashCommand][tanjun.commands.slash.SlashCommand]:

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

Most notably, only string arguments support converters (and the standard
converters found in [tanjun.conversion][]) similarly to message command
arguments.

```py
--8<-- "./docs_src/usage.py:108:118"
```

Slash commands can be stored in groups where the above example will be shown in
the command menu as `"/ding dong"` and `"/ding ding ding"`. Unlike message command
groups, slash command groups cannot be directly called as commands and can only
be nested once. For more information on how slash command groups are configured
see [slash_command_group][tanjun.commands.slash.slash_command_group].

### Message commands

```py
--8<-- "./docs_src/usage.py:122:132"
```

Message commands are triggered based on chat messages where the client's
prefixes and command names are used to match executable message commands
(the above example would match messages starting with `"!meow command"`).
These will only be executed when linked to a gateway bot with the
`MESSAGE_CONTENT` intent declared and when at least 1 prefix is set.

To allow users to trigger a command by mentioning the bot before the command
name (e.g. `@BotGirl meow command`) you can pass `mention_prefix=True` to
either [Client.from_gateway_bot][tanjun.clients.Client.from_gateway_bot] or
[Client.\_\_init\_\_][tanjun.clients.Client.__init__] while creating the bot.
Mention prefixes work even if the `MESSAGE_CONTENT` intent is not declared.

```py
--8<-- "./docs_src/usage.py:136:152"
```

Message command groups are a collection of message commands under a shared name
and (unlike slash commands) can also be directly executed as a command. The above
example would have the following commands: `"!groupy"`, `!"groupy tour"`,
`"!groupy tour de france"` and `"!groupy sus drink"`. For more information
on how message command groups are configured see
[as_message_command_group][tanjun.commands.message.as_message_command_group].


#### Argument parsing

Message command argument parsing always handles string arguments and to declare
parsed arguments you can use one of the `with_option` or `with_argument` methods
in [tanjun.parsing][]; while options are optional arguments that are passed
based on a flag name (e.g. `"--key"`), arguments are passed positionally.
It's worth noting that since decorators are executed from the bottom upwards
positional arguments will follow the same order.

Arguments and options have multiple parsing approaches: Arguments only parse
one value by default; "multi" (can be applied to both) arguments parse multiple
values separately (passed to the function as a list of values); "greedy"
(argument only) arguments parse the remaining positional values as one big
string (including spacing).

The most helpful configuration for options and arguments is converters: these
are callbacks which will be called to try convert an argument's raw value; the
first callback to pass (not raise a [ValueError][]) is used as the value. For
more configuration see [tanjun.parsing][] and for the standard converters see
[tanjun.conversion][].

### Context menus

```py
--8<-- "./docs_src/usage.py:156:164"
```

Context menus represent the application commands shown when you click on a user
or message in Discord and, unlike slash and message commands, do not have
configurable arguments nor groups. For more information on configuring menu
commands see [tanjun.as_message_menu][tanjun.commands.menu.as_message_menu].

### Annotation based command declaration

Previously you've seen how to manually declare command options per command
type, now it's time to go higher.

```py
--8<-- "./docs_src/usage.py:179:194"
```

[tanjun.annotations][] provides a simple way to declare the arguments for both
message and slash commands. While this feature is cross-compatible, there is
one key difference: a description must be included for options when annotating
for a slash command, which is done by passing a string value to
[typing.Annotated][] (as shown above).

This example doesn't demonstrate every feature of this; more information on
how arguments are configured in a command's signature can be found at
[tanjun.annotations][].

### Wrapped commands

When creating multiple command types in a decorator call chain, standard
decorators which can be applied to multiple command types often have a
`follow_wrapped` argument which will apply them to all the compatible
commands in a chain if [True][] is passed for it.

When using `follow_wrapped` the relevant decorator will be applied to all the
compatible `as_{}_command` decorator calls below it in the chain.

```py
--8<-- "./docs_src/usage.py:201:206"
```

While the previous command examples have typed `ctx` as a context type that's
specific to the command type, it's worth noting that
[abc.Context][tanjun.abc.Context] is a shared base for every command context type
and may be used as the type for `ctx` when a callback supports multiple command
types.

## Responding to commands

```py
--8<-- "./docs_src/usage.py:210:223"
```

[Context.respond][tanjun.abc.Context.respond] is used to respond to a command
call, this has a similar signature to Hikari's message respond method but will
only be guaranteed to return a [hikari.Message][hikari.messages.Message] object
when `ensure_result=True` is passed.

### Ephemeral responses

```py
--8<-- "./docs_src/usage.py:227:238"
```

Ephemeral responses are a slash command and context menu exclusive feature which
marks a response as private (so that only the command author can see it) and
temporary. A response can be marked as ephemeral by either passing `ephemeral=True`
to [AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response]
(when initially responding to the slash command) or
[AppCommandContext.create_followup][tanjun.abc.AppCommandContext.create_followup]
(for followup responses).
Alternatively, an ephemeral default can either be set on a client level
(using [Client.set_ephemeral_default][tanjun.clients.Client.set_ephemeral_default]),
component level
(using [Component.set_ephemeral_default][tanjun.components.Component.set_ephemeral_default]),
or for a specific command (by passing `default_to_ephemeral=True` while
creating a command) to have any relevant application command responses default
to ephemeral (including calls to [Context.respond][tanjun.abc.Context.respond]).

### Deferrals

Slash commands and context menus traditionally need to give an initial response
within 3 seconds. If you don't have a response message ready within 3 seconds,
you can defer the first response using
[AppCommandContext.defer][tanjun.abc.AppCommandContext.defer]; the client will
even automatically defer by default if you haven't created an initial response
within a couple of seconds. [Context.respond][tanjun.abc.Context.respond] is
aware of deferrals so you likely won't need to think about automatic deferral,
unless you're using
[AppCommandContext.create_initial_response][tanjun.abc.AppCommandContext.create_initial_response].

A deferral should be finished by editing in the initial response using either
[Context.edit_initial_response][tanjun.abc.Context.edit_initial_response] or
[Context.respond][tanjun.abc.Context.respond] and if you want a deferred
response to be ephemeral you'll have to either pass `ephemeral=True` while
deferring or have the ephemeral default set to [True][].

Automatic deferral can be configured using
[Client.set_auto_defer_after][tanjun.clients.Client.set_auto_defer_after],
and commands can even be configured to always defer when they start executing
by passing `always_defer=True` while creating the command.

## Slash command autocomplete

Autocomplete is a slash command exclusive feature that allows a bot to
dynamically return choice suggestions to a user as they type a string option.

Autocomplete callbacks must be asynchronous and support dependency injection.

```py
--8<-- "./docs_src/usage.py:242:256"
```

To set the results for an autocomplete interaction call
[AutocompleteContext.set_choices][tanjun.abc.AutocompleteContext.set_choices]:
this has a similar signature to [dict][] and takes up to 25 choices (where both
name and value have a limit of up to 100 characters).

Unlike application commands, autocomplete must give a response within 3 seconds
as these do not support deferrals.

## Dependency injection

Tanjun supports type-based dependency injection as a type-safe approach for
handling global state for most of the callbacks it takes (e.g. command
callbacks, checks, hook callbacks, event listeners, schedule callbacks) through
[Alluka][alluka].

```py
--8<-- "./docs_src/usage.py:268:270"
```

Here we set the dependencies for the types `Foo` and `Bar`.

```py
--8<-- "./docs_src/usage.py:274:278"
```

And here we declare a command callback as taking the client set values for
`Foo` and `Bar` as keyword arguments using two different approaches.
Since both arguments don't provide a default, these commands will fail if no
value for `Foo` or `Bar` has been set using
[Client.set_type_dependency][tanjun.abc.Client.set_type_dependency].

A more detailed guide on how this works and the full feature set (e.g. optional
dependencies) can be found [here](https://alluka.cursed.solutions/usage/).
[alluka.abc.Client][] is exposed at [Client.injector][tanjun.abc.Client.injector].

### Standard and special cased injected types.

The following types are registered globally as type dependencies:

* [tanjun.abc.Client][]
* [tanjun.Client][tanjun.clients.Client]
* [tanjun.dependencies.AbstractOwners][] (for use with the standard owner check).
* `tanjun.LazyConstant[hikari.OwnUser]` (for use with `tanjun.inject_lc(hikari.OwnUser)`)
* [hikari.api.RESTClient][hikari.api.rest.RESTClient]
* [hikari.api.Cache][hikari.api.cache.Cache] \*
* [hikari.api.EventManager][hikari.api.event_manager.EventManager] \*
* [hikari.api.InteractionServer][hikari.api.interaction_server.InteractionServer] \*
* [hikari.ShardAware][hikari.traits.ShardAware] \*
* [hikari.api.VoiceComponent][hikari.api.voice.VoiceComponent] \*

\* These type dependencies are only registered if the relevant Hikari component
    was included while creating the [tanjun.Client][tanjun.clients.Client]
    instance.

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
<!-- * [hikari.Event][hikari.events.base_events.Event] TODO: implement this-->

Both [Client.from_gateway_bot][tanjun.clients.Client.from_gateway_bot] and
[Client.from_rest_bot][tanjun.clients.Client.from_rest_bot] register type
dependencies for the relevant [hikari traits][hikari.traits] that the bot is
compatible with. You can get this behaviour after directly initialising
[tanjun.clients.Client][tanjun.Client] without a from method by calling
[Client.set_hikari_trait_injectors][tanjun.clients.Client.set_hikari_trait_injectors]
with the relevant bot object.

## Advanced command flow management

### Checks

Checks are functions that run before command execution to decide whether a
command or group of commands matches a context and should be called with it.

```py
--8<-- "./docs_src/usage.py:282:288"
```

There's a collection of standard checks in [tanjun.checks][] which work
with all the command types. The only optional configuration most users
will care about for the standard checks is the `error_message` argument
which lets you adjust the response messages these send when they fail.

```py
--8<-- "./docs_src/usage.py:301:319"
```

Checks (both custom and standard) can be added to clients, components, and
commands using either the chainable `add_check` method or the decorator
style `with_check` method. The standard checks also provide `with_...`
decorators which can be used to add the check to a command during a decorator
chain. Checks on a client, component, or command group will be used for every
child command.

```py
--8<-- "./docs_src/usage.py:323:327"
```

Custom checks can be made by making a function with either the signature
`def (tanjun.abc.Context, ...) -> bool` or `async def (tanjun.abc.Context, ...) -> bool`
(where [dependency injection][dependency-injection] is supported).  Returning
[True][] indicates that the check passed, and returning [False][] indicates that
the client should continue looking for a matching command as the check failed.
You will probably want to raise [CommandError][tanjun.errors.CommandError] to
end command execution with a response rather than returning [False][].

### Execution hooks

Command hooks are callbacks that are called around command execution, these
are contained within [Hooks][tanjun.hooks.Hooks] objects which may be added
to a command, client, or component using `set_hooks` where hooks on a client,
component or command group will be called for every child command.

There are several different kinds of hooks which all support dependency
injection and may be synchronous or asynchronous:

```py
--8<-- "./docs_src/usage.py:331:335"
```

Pre-execution hooks are called before the execution of a command but after
command matching has finished and all the relevant checks have passed.

```py
--8<-- "./docs_src/usage.py:339:341"
```

Post-execution hooks are called after a command has finished executing,
regardless of whether it passed or failed.

```py
--8<-- "./docs_src/usage.py:345:347"
```

Success hooks are called after a command has finished executing successfully
(without raising any errors).

```py
--8<-- "./docs_src/usage.py:351:353"
```

Error hooks are called when command's execution is ended early by an error raise
that isn't a [ParserError][tanjun.errors.ParserError],
[CommandError][tanjun.errors.CommandError] or
[HaltExecution][tanjun.errors.HaltExecution] (as these are special-cased).

The return value of an error hook is used with other error hook return values
to workout whether the error should be re-raised: [True][] acts as a vote
towards suppressing the error, [False][] acts as a vote towards re-raising the
error and [None][] acts as no vote. In the case of a tie the error will be
re-raised.

```py
--8<-- "./docs_src/usage.py:357:359"
```

Parser error hooks are called when the argument parsing of a message command
failed. Parser errors are never re-raised.

### Concurrency limiter

Concurrency limiters allow you to limit how many calls can be made to a group
of commands concurrently.

```py
--8<-- "./docs_src/usage.py:363:369"
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
--8<-- "./docs_src/usage.py:373:377"
```

And here we use [with_concurrency_limit][tanjun.dependencies.with_concurrency_limit]
to mark these commands as using the `"main_commands"` concurrency limit bucket;
buckets share their limits for a resource across all the commands under it. For
more information on the resources concurrency can be limited by see
[BucketResource][tanjun.dependencies.BucketResource].

### Cooldowns

Cooldowns limit how often a group of commands can be called.

```py
--8<-- "./docs_src/usage.py:381:387"
```

Here [InMemoryCooldownManager][tanjun.dependencies.InMemoryCooldownManager]
will manage the cooldowns for all the commands in this bot instance with
[Manager.set_bucket][tanjun.dependencies.InMemoryCooldownManager.set_bucket]
being called to limit the bucket `"main_commands"` to 5 calls per user every 60 seconds,
[Manager.disable_bucket][tanjun.dependencies.InMemoryCooldownManager.disable_bucket]
being called to ensure that the bucket `"plugin.meta"` has no cooldowns as
unconfigured buckets will default to the configuration for the `"default"` bucket, and
[Manager.add_to_client][tanjun.dependencies.InMemoryCooldownManager.add_to_client]
being used to set this cooldown manager for a client (note that clients can
only have 1 linked cooldown manager).

```py
--8<-- "./docs_src/usage.py:391:395"
```

And here we use [with_cooldown][tanjun.dependencies.with_cooldown]
to mark these commands as using the `"main_commands"` cooldown bucket;
buckets share their cooldowns for a resource across all the commands under it.
For more information on the resources cooldowns can be set for see
[BucketResource][tanjun.dependencies.BucketResource].

## Localisation

[Localisation](https://en.wikipedia.org/wiki/Language_localisation) allows for
tailoring the declarations and responses of slash commands and context menu
commands to match specific regions by providing multiple translations
of a field. Localisation on Discord is limited to the locales Discord supports
(listed at [hikari.Locale][hikari.locales.Locale]).

### Localising command declarations

```py
--8<-- "./docs_src/usage.py:399:401"
```

For fields which support localisation you've previously seen a single string
being passed to them: this value is used as a default for all locales and for
environments which don't support localisation (e.g. message command execution).
But as shown above, you can also pass a dictionary of localised values to these
fields.

### Client localiser

Tanjun also provides an optional global localiser which allows for
setting/overriding the locale-specific variants used for localised fields such
as error message responses and application fields globally.

```py
--8<-- "./docs_src/usage.py:405:417"
```

Specific fields may be overridden by their ID as shown above. There is no
guaranteed format for field IDs but the standard implementations will always
use the following formats unless explicitly overridden:

* Checks and limiters: `f"{command_type}:{command_name}:check:{check_name}"`
* Command descriptions: `f"{command_type}:{command_name}:description"`
* Command names: `f"{command_type}:{command_name}:name"`
* Slash option names: `f"slash:{command_name}:option.name:{option_name}"`
* Slash option descriptions: `f"slash:{command_name}:option.description:{option_name}"`
* Slash option choice names: `f"slash:{command_name}:choice.name:{choice_name}"`

`command_type` may be one of `"message_menu"`, `"slash"` or `"user_menu"`,
`command_name` will be the full name of the command (including parent command
names in the path), and standard check names will always be prefixed with
`"tanjun."`.

It's highly recommended that 3rd party libraries match this format if possible.

### Localising command responses

```py
--8<-- "./docs_src/usage.py:421:440"
```

[tanjun.abc.AppCommandContext.interaction][] (base class for both
[tanjun.abc.SlashContext][] and [tanjun.abc.MenuContext][]) has the fields
`guild_locale` and `locale` which provide the set locale of the guild and the
user triggering the command respectively. This [locale][hikari.locales.Locale]
can be used to localise responses to specific languages within your own code.

<!-- # TODO: some day, document buildings commands using the flient interface -->
