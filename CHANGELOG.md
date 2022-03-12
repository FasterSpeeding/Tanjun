# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.3a1] - 2022-03-12
### Added
- Slash command "attachment" options.

## [2.4.2a1] - 2022-03-04
### Fixed
- Add weakref slot to BaseConverter to improve standard converter compatibility with Alluka.
- Type compatibility with InteractionMessageBuilder when making the initial response as a REST bot.
- No longer duplicate embeds on slash create initial response for REST bots.
- `has_responded` is now only set to `True` for slash command contexts after the
  `create_initial_response` passes, avoiding issues where error logic calling `ctx.respond` after
  a call to `create_initial_response` failed would try to create a followup and 404.
- Further resolve Paths in module loading logic:
  * User relative paths (`~`) can now be passed.
  * It now normalises path (so separators), avoiding the same path but with different separators being registered multiple times.
  * It now normalises symlinks, avoiding the same module being registered multiple times through different symlinks.

## [2.4.1a1] - 2022-02-25
### Added
- Alluka's dependency injection interface(s) have been upgraded to the standard Client interface
  and Context interfaces.
- Standard message converter.

### Changed
- `Coroutine` is now used instead of `Awaitable` for callback signature return types to account
  for refactors made to DI logic in Alluka.
- The dependency injection implementation has been moved to <https://github.com/FasterSpeeding/Alluka>
  and any new DI features may be indicated there rather than on Tanjun's (Note, DI is still supported)
  changelog.
- Callbacks with invalid dependency injection declarations (are declaring a positional-only argument
  as needing DI) now won't error until they're called with DI.

### Fixed
- Duplication detection while checking for commands with overlapping names on declare.
- Relaxed menu command name validation to allow special characters and mixed cases.

### Removed
- `tanjun.injecting.TypeDescriptor` and `tanjun.injecting.CallbackDescriptor` as these couldn't be
  kept through the Alluka refactor.
- `needs_injection` attributes.

### Deprecated
- `tanjun.injecting` now only consists of deprecated aliases to Alluka types, with the only
  `tanjun.inject` and `tanjun.injected` being left as not deprecated for the sake of ease of use.

## [2.4.0a1] - 2022-02-11
### Added
- `ephemeral` keyword-argument to `SlashContext`'s `create_initial_response`, `create_follow_up`
  and `defer` methods as a shorthand for including `1 << 6` in the passed flags.
- Context menu command support.
- Slash command autocomplete support.
- `shard` is now a property on all contexts.

### Changed
- `ShlexParser` no-longer treats `'` as a quote.
- Command objects can now be passed directly to `SlashCommand.__init__` and `MessageCommand.__init__`.
- The search snowflake conversion functions now return lists of snowflakes instead of iterators.
- `tanjun.components` has been split into a directory of the same name with the structure
  `tanjun.components.slash`, `tanjun.components.message`, `tanjun.components.base` and
  `tanjun.components.menu`.
- `tanjun.commands` has been split into a directory of the same name with the structure
  `tanjun.commands.slash`, `tanjun.commands.message`, `tanjun.commands.base` and `tanjun.commands.menu`.
- Bumped the minimum hikari version to `hikari~=2.0.0.dev106`.

### Fixed
- False-positive cache warnings from the standard converters.
- Mishandled edge cases for to_color.
- Mishandling of greedy arguments as reported by #200

## [2.3.1a1] - 2022-01-27
### Added
- `SlashContext.boolean`, `SlashContext.float`, `SlashContext.integer`, `SlashContext.snowflake`
  and `SlashContext.string` methods as short hands for asserting the option type and ensuring type
  safety.
- A `MessageParser` standard abc.
- `Client.set_metadata`, `Component.set_metadata` and `ExecutableCommand.set_metadata` fluent
  methods to allow for chaining metadata setting.
- Complementary `Client.load_modules_async` and `Client.reload_modules_async` methods which execute
  blocking file access operations in asyncio's threadpool executor.
- The module load, unload and reload methods now raise `FailedModuleLoad` and `FailedModuleUnload`
  to relay errors raised by the target module or its (un)loaders.
- `max_value` and `min_value` options for message command option parser options and arguments.

### Changed
- `SlashContext.value` now returns `hikari.Snowflake` for object IDs.
- `reload_modules` will now try to rollback a module if it failed to load before raising
  and avoid trying to reload a module all together if no loaders or unloaders are found.

### Fixed
- `Context.get_channel` no longer raises an assertion error if the cache returns `None`.
- Schedules are now stopped if they are removed from a component while active.
- Schedules will no-longer raise a RuntimeError while closing a component if they were stopped before
  before hand.

## [2.3.0a1] - 2022-01-13
### Added
- Scheduled callback interface and interval implementation to the standard component implementation.
- `always_defer` option to slash commands (not including groups).
- `tanjun.MessageCommand` is now callable like `tanjun.SlashCommand`.
- `MessageContext.respond` is now typed as allowing `bool` for the `reply` argument.
- `min_value` and `max_value` option for int and float slash command options.

### Changed
- Bumped the minimum hikari version to hikari~=2.0.0.dev105.
- `delete_after` is now ignored for ephemeral responses instead of leading to a 404.
- Renamed the standard conversion classes to fit the naming convention `To{Type}` (while leaving the
  old names in as deprecated aliases) + added them to doc coverage/`conversion.__all__` by their new
  names.

### Fixed
- The client level ephemeral default is now respected for REST-based slash command execution.
- The client now waits until a component has been closed before "unbinding" it when the component is
  removed from an active client.
  This should fix previous behaviour where trying to remove a component from an active client would
  lead to an error being raised.

### Removed
- Redundant checks, hooks and metadata keyword-arguments from the standard `MessageCommand`,
  `MessageCommandGroup`, `SlashCommandGroup` and `SlashCommand` implementations' `__init__`s;
  these should be set using methods/decorators.
- Redundant hook and check keyword-arguments from the standard `Client` impl; these should be set using
  methods.
- The use of star imports in `tanjun.__init__` and `tanjun.dependencies.__init__` meaning that now only
  the documented types and attributes for these modules (whatever's in the `__all__`) may be accessed
  directly on them now.
- `tanjun.MessageContext`, `tanjun.SlashContext` and `tanjun.Context` are no-longer exported on the top
  level as in most cases their abc equivalent should be used.

## [2.2.3a1] - 2022-01-06
### Added
- The interface for a generic (type-based) asynchronous cache dependency.

  While this doesn't introduce any new implementation(s), this interface has been integrated into
  Tanjun (based on Hikari types) in places which are currently making cache/REST calls and can be used to
  better integrate 3rd-party caches with Tanjun.

  Redis based implementations of this for the types found in Hikari's gateway cache interface can be found
  in [hikari-sake](https://github.com/FasterSpeeding/Sake) \>=v1.0.1a1 (exposed by
  `RedisResource.add_to_tanjun`).

### Removed
- `BaseConverter.convert` in-favour of having each standard converter directly implement `__call__`.
- `tanjun.conversion.InjectableConverter`.
- `InjectionContext.get_type_special_case` in favour of a `get_type_dependency` method which tries the
  context's client before returning the special case if registered.

## [2.2.2a1] - 2021-12-26
### Added
- Type based dependency injection now has ergonomic Union support.
  This means that for `inject(type=Union[A, B, C])`/`inject(type=A | B | C)` the dependency injector will
  try to find registered type injectors for `A`, `B` then `C` after trying to find a dependency injector
  for the literal Union.
- Type based dependency injection now has support for defaults through unions with `None` and `Optional`.
  This means that, for `inject(type=Union[A, B, None])`/`inject(type=A | B | None)` and
  `inject(type=Optional[A])`, if no registered implementations are found for the relevant types then `None`
  will be injected for the relevant argument.

### Changed
- Message command parser arguments are now passed by keyword instead of positionally.
- Cooldown checks can now run without a present AbstractOwners implementation.

### Fixed
- The cooldown manager now increments the internal counter after checking for cooldown rather than before.
  The old behaviour resulted in the last valid call to a bucket being ratelimited therefore essentially making
  the real-world limit `limit-1`.

## [2.2.1a1] - 2021-11-30
### Added
- Concurrency limiter dependency (in a similar style to cooldowns).
- `disable_bucket` method to the in-memory concurrency and cooldown manager impls.
- `any_checks`/`with_any_checks` and `all_checks`/`with_all_checks` functions for more garnular check
  flow control. `any_checks` passes if any of the provided checks pass and `all_checks` passes if all
  the provided checks pass while both ensure the checks are run sequentially rather than concurrently.
- `as_slash_command`, `as_message_command` and `as_message_command_group` now support decorating Command
  instances.

### Changed
- `cached_inject` and `cache_callback` now both accept `float` and `int` seconds for `expire_after`.
- `Owners.__init__` now accepts `float` and `int` seconds for `expire_after`.
- Renamed `tanjun.dependencies.owners.OwnerCheck` and `tanjun.dependencies.owners.AbstractOwnerCheck`
  to `Owners` and `AbstractOwners` respectively.
- `InMemoryConcurrencyLimiter.set_bucket`'s parameters are now positional only.
- Updated application command name and option name checking to allow for all unicode \w characters
  rather than just ASCII.
- `@with_parser` now errors if a parser is already set.
- `with_option` and `with_argument` command parser decorators now implicitly set shlex parser if not set.

### Removed
- `TanjunWarning` and `StateWarning`.

## [2.2.0a1] - 2021-11-23
### Added
- Upgraded `is_alive` attribute to the Client abstract interface.
- Upgraded `clear_application_commands`, `declare_global_commands`, `declare_slash_command` and
  `declare_slash_commands` to the Client abstract interface.
- `Client.dispatch_client_callback` and `ClientCallbackNames` to the abstract interface.
- Client and Component are now bound to a specific event loop with said loop being exposed by a `loop` property.
- `BaseSlashCommand.tracked_command`.
- Upgraded `load_modules`, `unload_modules` and `reload_modules` to the Client abstract interface.
- `Component.make_loader` shorthand method for making a module loader and unloader for a component.
- `tanjun.abc.ClientLoader` to make loaders more standard and easier to custom implement.
- Command cooldowns.

### Changed
- Renamed `Client.clear_commands` to `Client.clear_application_commands`.
- Renamed `declare_slash_command` and `declare_slash_commands` to `declare_application_command` and
  `declare_application_commands` respectively.
- Renamed `Client.detect_commands` to `Client.load_from_scope`.
- Restructured LoadableProtocol for re-use in `Client.load_from_scope` and rename to `ComponentLoader`.

### Fixed
- Don't include the "tracked command ID" in slash command group builders as this leads to mis-matching ID
  errors while declaring.

### Removed
- BaseSlashCommand.tracked_command_id is no-longer used in command builders and cannot passed to
  `as_slash_command`, `slash_command_group`, `SlashCommand.__init__` and `SlashCommandGroup.__init__`
  as `command_id` anymore.
- `load_from_attributes` behaviour from the standard Component implementation.

## [2.1.4a1] - 2021-11-15
### Added
- `injecting.SelfInjectingCallback` and `tanjun.as_self_injecting` to let users make a callback self-injecting
  by linking it to a client instance. This should make it easier to use Tanjun's dependency injection
  externally.
- Dependency injection support for hook callbacks.
- `voice` property to Context and Client.
- `Component.detect_commands` for auto-loading commands from the current scope.
- `delete_after` option to context response methods.
- `expires_at` property to SlashContext.

### Changed
- `Hooks` can now contain multiple callbacks per hook type.
- `load_from_attributes` now defaults to `False` in `Component.__init__`.

### Fixed
- `SlashContext.respond` trying to edit in the initial response instead of create a follow up
  if a deferred initial response was deleted.

### Removed
- `injecting.BaseInjectableCallback` and other private extensions of this as these cases could
  easily be achieved with `SelfInjectingCallback` and `CallbackDescriptor`.

## [2.1.3a1] - 2021-11-02
### Added
- `tanjun.dependencies.inject_lc(Type)` which is a shorthand for
  `tanjun.injected(callback=tanjun.make_lc_resolver(Type))`.
- `tanjun.dependencies.cached_inject(...)` which is a shorthand for
  `tanjun.injected(callback=tanjun.cache_callback(...))`.
- `tanjun.inject` which is identical to `tanjun.injecting.injected` but does not replace it.

### Changed
- Added USE_EXTERNAL_STICKERS to DM permissions.
- `Client.listeners` now returns a sequence of callbacks rather than descriptors.

### Fixed
- Removed `cache_callback` from injecting.pyi.
- Some bodged logging calls in declare_slash_commands which weren't providing the right amont of format args.
- Options not being sorted for slash commands within a command group.
- Stop shlex from treating stuff after a `#` as a comment.

## [2.1.2a1] - 2021-10-15
### Added
- `Client.iter_commands`, `Client.iter_message_commands` and `Client.iter_slash_commands`.
- Ephemeral default is now applicable at a client and component level with it defaulting to `None` on
  components, this will propagate down from the client to the command being executed with each level
  having the option to override its state or leave it as is.
- `OwnerCheck` now relies on a standard dependency (which can easily be overridden) for its actual logic.

### Changed
- SlashCommand's ephemeral default now defaults to `None` indicating that the parent entity's state should
  be used.
- Check functions such as `nsfw_check`, `sfw_check`, `dm_check`, `guild_check` have been replaced with
  check classes (NsfwCheck, SfwCheck, DmCheck, GuildCheck).
- Renamed `ApplicationOwnerCheck` to `OwnerCheck`.
- Renamed `OwnPermissionsCheck` to `OwnPermissionCheck`.
- Moved `cache_callback` from `tanjun.injecting` to `tanjun.dependencies`.

### Deprecated
- Passing Iterable[tuple[str, value]] as choices to the slash command options has been deprecated
  in favour of Mapping[str, value].

### Fixed
- `MessageContext` not being passed to the prefix getter as the only positional argument.
- `Client.remove_component_by_name`.

### Removed
- `tanjun.abc.ExecutableCommand.execute` and `check_context` as this doesn't work typing wise.
  This doesn't effect the implementations nor full command types.
- Base `PermissionsCheck` class.

## [2.1.1a1] - 2021-10-09
### Added
- `ShlexParser.add_option` and `add_argument` methods which mirror the behaviour of `with_option` and `with_argument`
- Fluent interface coverage has been increased to now include remove methods and parsing interfaces.
- Support for specifying which channel types you want with slash channel type options.
- `custom_ids` argument to both `Client.declare_global_commands`, `Client.__init__` and
  `Client.declare_slash_commands` to allow specifying the IDs of commands which are being updated.
- `Client.remove_component_by_name` and `get_component_by_name`.
- `Client.unload_modules` and `Client.reload_modules` to unload and reload from modules which also declare
  a unloader.
- `tanjun.as_unloader` decorator to enable declaring unloaders for modules.
- Let a Sequence of guild ids/objects be passed for `Client.__init__`'s declare_global_commands parameter
  (although custom_ids isn't supported in this instance).
- Client now enforces that all registered component names are unique within the client.

### Changed
- Bumped minimum hikari version to 2.0.0.dev103.
- The default parser error handler is now set as Client.hooks (not Client.message_hooks) meaning that it
  runs for all commands not just message commands.
- Replace `conversion.ColorConverter` and `conversion.SnowflakeConverter` with `to_snowflake` and `to_color`
  pure function implementations.
- `Client.load_modules` now errors if no loader descriptor is found.

### Deprecated
- Calling set_tracked_command with a command ID.
- Passing command_id to `SlashCommand.__init__`, `SlashCommandGroup.__init__`, `as_slash_command` and
  `as_slash_command_group`.
- Renamed `set_global_commands` (both the Client method and init parameter) to declare_global_commands.

### Removed
- `add_converter` and `remove_converter` from Parameter.
- the `BaseConverter` classes are no-longer included in `conversion.__all__` meaning that they are no-longer
  documented.

## [2.1.0a1] - 2021-10-02
### Added
- Adding an option to SlashCommand will now raise if the name is invalid (doesn't match the names regex).
- Validation to slash command classes.
- Special case type injector handling for the client itself.

### Changed
- Breaking: `Client.set_type_dependency` now takes a literal value rather than a callback.
- `Client.declare_slash_commands` and `Client.set_global_commands` now check if the target resource's commands
  match the commands to be declared before actually declaring them unless `force` is set to `True`. This
  helps avoid issues with ratelimiting.
- Client level special cased type injectors are now handled as normal type injectors which are just implicitly
  set from the start.
- `Client.load_modules` now respects `__all__` if present.

### Fixed
- Small change to help MyPy better understand protocol behaviour.
- `SlashContext.mark_not_found` and `cancel_defer` are actually called if the command was not found in the REST flow.

### Removed
- `Client.add_type_dependency` and `Client.add_callback_override`
- Special case type dependency methods have been removed/hidden.
- `pass_as_kwarg` option from slash command artificial member options as the always member constraint cannot
  be present without pass_as_kwarg behaviour.

## [2.0.1a1.post1] - 2021-09-26
### Fixed
- Trailing `:` on a type: ignore comment which broke MyPy compatibility.

## [2.0.1a1] - 2021-09-25
### Added
- Default client level message parser error handling hook.
- Component arguments to the relevant context create message methods.

### Changed
- Bumped minimum Hikari version to 2.0.0.dev102.
- Consistently raise ValueError instead of LookupErrors in places where a value is being removed.
- `Context.fetch_channel` and `Context.get_channel` now return TextableChannel and TextableGuildChannel
  respectively.

### Fixed
- Actually call `Command.bind_client` and bind_component in the component add command methods and
  specifically `SlashCommand.bind_client` in `Component.bind_client`.
- Return the command object from `Component.with_command methods`.
- Automatic deferral is now also cancelled in `SlashContext.create_initial_response`.
- `SlashContext.edit_last_response` can now be used to edit a deferred response.
- Small typing fixes made while setting pyright to strict.

### Removed
- suppress_exceptions from `Client.dispatch_client_callback` cause it was poorly implemented and didn't make sense.

## [2.0.0a4] - 2021-09-17
### Added
- `expire_after` argument to `tanjun.injecting.cached_callback`.
- snowflake "search" functions and from_datetime to conversion.
- the snowflake "parse" methods are now exported by conversion.
- `BaseConverter.requires_cache` and `cache_components` properties + check_client method to allow for
  warning if a converter might not run as expected under the provided client (e.g. intent or state issues).

### Changed
- renamed "conversion.parse_datetime" to "conversion.to_datetime".
- `Client.__init__` now allows `hikari.SnowflakeishOr[hikari.PartialGuild] | None` for set_global_commands.

### Removed
- BaseConverter.bind_client, bind_component, get_from_type, implementations, cache_bound, is_inheritable
  and types methods/properties as these were part of an old system which assumed these would be inferred
  from types which is no longer the case.

### Fixed
- A failed startup set global commands call will no longer lead to it retrying on the next startup.
- Component level check errors not being caught when executing interactions.
- The internal state for whether a SlashContext has had it's initial response made or not not being set by
  SlashContext.mark_not_found.
- Client.on_interaction_create_request not awaiting the client level checks.

## [2.0.0a3.post1] - 2021-09-11
### Changed
- Client.add_listener is now fluent.

### Fixed
- Bug around registering wrapped listeners where Hikari doesn't allow async callable objects to be registered.

## [2.0.0a3] - 2021-09-10
### Added
- Add `always_float` keyword argument to with_float_slash_option.
- SlashContext.options mapping plus a resolvable option type to allow for more easily getting slash command
  options without relying on passed keyword arguments.
- Automatic type injector special casing for components and commands within a command context.
- Split up tanjun.commands.SlashCommand.add_option into specific methods.
- Add `pass_as_kwarg` keyword argument to with slash option decorators with True default.

### Changed
- Renamed `Client.__init__` "shard" arg to "shards".
- Annotate implimation functions/properties which return collections as returning `collections.abc.Collection`
  instead of their implemation specific subclass of Collcetion.
- Standard checks now have the same defaults as their with_* counterparts.

### Fixed
- Bug around checks not being respected if they returned False.
- Client level check errors not being caught during execution.
- Don't erroneously dispatch message command not found callbacks when a component's execution returns true
- Don't fall back to normal command search in "strict" components and message command groups.
- Edit the command if command_id is passed to declare_slash_command instead of creating a new command.
- Missing call to checks in interaction request handler logic.

### Removed
- Client.check_message_context and Component.check_message_context.
- tanjun.commands.SlashCommand.add_option.

## [2.0.0a2] - 2021-09-07
### Added
- Float slash command option type.
- Component add and remove client callbacks.
- Event listeners are now loaded into Client by Components and support dependency injection.
- Add/with and remove listener methods had to be added to the Client to support this.
- Exported the parsing, commands and utilities modules on a top level (thus also adding them to the generated docs).
- Allow for overriding the standard client's context builders.
- Add default_permission argument to slash command types.
- Dependency injection support to client callbacks.
- Injection type special casing is more granular on a context to context basis now rather than top level hardcoded.
- Injection.Descriptor, TypeDescriptor and CallbackDescriptor replaced the Getter and InjectableValue classes.

### Changed
- Component.listeners and Client.listeners now return Mapping[type[Event], Collection[Callback]].
- Dependency injection on a lower level has been restructured to remove any reliance on tanjun.abc.Context.
  This means introducing an abstract injection context and implementing it with the standard context and a more
  basic impl.
- More strictly use properties instead of public instance variables in injection implementation.
- Dependency injection now caches the results of callbacks within the scope of an execution context.
- Renamed the InjectedValue classes to InjectedCallbacks.
- Return CallbackDescriptors from InjectionClient.get_type_dependency and get_callback_override instead of
  pure callbacks.
- Use Optional instead of UndefinedOr in injecting module where possible (e.g. the Injected callback and type fields).
- Process injected callbacks when they're first handled (passed to CallbackDescriptor) than when they're first called
  This lowers the amount of external caching needed.

### Deprecated
- InjectionClient/Client .add_type_dependency and add_callback_override have been deprecated in favour of
  set_type_dependency and set_callback_override and are scheduled to be removed a month after v2.0.0a2 is released.

### Removed
- injecting.Getter and injecting.InjectableValue.
- set_injector methods as the injection client is now passed around as part of a context.
- injection.resolve_getters (this logic is now on the descriptors).

### Fixed
- Doc typo and export fixes.
- Fix handling of ctx.content and ctx.triggering_nameand in MessageCommandGroup to account for doubly nested command groups.
- Fix double-calling command group checks instead of calling the command group checks then the sub-command's check.

## [2.0.0a1] - 2021-08-30
### Added
- For a TLDR of how Tanjun's interface looks after these changes see the examples
  https://github.com/FasterSpeeding/Tanjun/blob/v2.0.0a1/examples/
- Full slash command functionality, this includes new decorators for setting slash command specific options and slash
  command + command group declaration and execution. Some examples of this may be found at
  https://github.com/FasterSpeeding/Tanjun/blob/v2.0.0a1/examples/slash_component.py
- Dependency injection, this feature is in it's early days and under documented but is still partially documented by
  the examples at https://github.com/FasterSpeeding/Tanjun/blob/v2.0.0a1/examples/ . For now this only covers command
  callback, check (on both commands and components) and converter execution plus calls to the prefix getter functions
  (since it's limited to calls which take a Context for the initial implementation).
- Increased test and documentation coverage.
- Add the ability to set a custom prefix getter function.
- Switched over to pdoc from pdoc3 for doc generation.
- Added more extensive examples .
- Add rest fallbacks to the standard converters where possible.
- Fix some bugs with the standard checks.
- Introduce a flag for setting which message commands the standard client should accept for execution.
- Add client callback functions to allow for better integration between hikari's RESTBot and GatewayBot plus collecting
  runtime metadata.
- Added proxy methods and properties to the Context abcs to allow for calls when using the base Context abc.
- Add state tracking to Context to allow for similar functionality between the slash and message command flows when it
  comes to dealing with responses (e.g. initial and last response logic).
- Introduced a proper nox framework for running checks and CI tasks.
- Switched over to just importing the top level `hikari` module when possible to simplify imports.
- Replaced MYPY with pyright as the standard type checker.
- Switch over to relative imports.
- Switched away from setuptools to pep 621 with flit for defining the library and it's metadata (including
  requirements).
- Moved the project metadata duner properties direcltly to `tanjun` (from `tanjun.about.py`).

### Changed
- Dropped support for python 3.8 in-order to switch over to using collection.abc generic classes due to this being more
  forward compatible.
- Move away from enforcing subclassing behaviour in-favour of builder objects ~~you can still use subclassing behaviour
  in places but don't tell anybody I told you that~~.
- Consistency fix by ensuring functions are always called "callback".
- Add `error_message` and `half_execution` arguments to the standard checks to allow commands to more granularly define
  the behaviour for when they fail plus default them to having them send an error message when they fail if they were
  added to a command through a decorator call as this works better with the slash command flow and is better UX (a
  response explaining why it didn't work is better than no response).
- Renamed `tanjun.traits` to `tanjun.abc`.
- Replaced strategy of inferring other hikari client traits from the first arg parsed to `Client.__init__` with having
  the init explicitly take in each trait it needs as a separate argument while having shortcut `from_gateway_bot` and
  `from_rest_bot` classmethods for building the standard client from hikari's "bot" traits.
- Only default to setting `set_human_only(True)` in `Client.from_gateway_bot`.
- API overhall around commands and context, this involved making a lot of classes and type hints generic to allow
  for the slash context and message context to be interchaingable under the right circumstances.
- Made the callback signatures more generic for commands and converters to allow for implementations to introduce
  features like dependency injection.

### Removed
- Removed a lot of impl specific setting and with methods from the abstract interfaces to avoid

[Unreleased]: https://github.com/FasterSpeeding/Tanjun/compare/v2.4.3a1...HEAD
[2.4.3a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.4.2a1...v2.4.3a1
[2.4.2a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.4.1a1...v2.4.2a1
[2.4.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.4.0a1...v2.4.1a1
[2.4.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.3.0a1...v2.4.0a1
[2.3.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.3.0a1...v2.3.1a1
[2.3.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.2.2a1...v2.3.0a1
[2.2.3a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.2.2a1...v2.2.3a1
[2.2.2a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.2.1a1...v2.2.2a1
[2.2.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.2.0a1...v2.2.1a1
[2.2.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.4a1...v2.2.0a1
[2.1.4a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.3a1...v2.1.4a1
[2.1.3a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.2a1...v2.1.3a1
[2.1.2a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.1a1...v2.1.2a1
[2.1.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.0a1...v2.1.1a1
[2.1.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.1a1...v2.1.0a1
[2.0.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a4...v2.0.1a1
[2.0.0a4]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a3...v2.0.0a4
[2.0.0a3]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a2...v2.0.0a3
[2.0.0a2]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a1...v2.0.0a2
[2.0.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/1.0.1a5...v2.0.0a1
