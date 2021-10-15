# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Now handle when Discord doesn't include boolean options in interaction payloads because they were passed as `False`
  and weight reduction bro.
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

[Unreleased]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.2a1...HEAD
[2.1.2a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.1a1...v2.1.2a1
[2.1.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.1.0a1...v2.1.1a1
[2.1.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.1a1...v2.1.0a1
[2.0.1a1]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a4...v2.0.1a1
[2.0.0a4]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a3...v2.0.0a4
[2.0.0a3]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a2...v2.0.0a3
[2.0.0a2]: https://github.com/FasterSpeeding/Tanjun/compare/v2.0.0a1...v2.0.0a2
[2.0.0a1]: https://github.com/FasterSpeeding/Tanjun/compare/1.0.1a5...v2.0.0a1
