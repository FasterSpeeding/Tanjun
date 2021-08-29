# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0a1] - 2021-08-30
### Added
- For a TLDR of how Tanjun's interface looks after these changes see the examples
  https://github.com/FasterSpeeding/Tanjun/blob/2.0.0a1/examples/
- Full slash command functionality, this includes new decorators for setting slash command specific options and slash
  command + command group declaration and execution. Some examples of this may be found at
  https://github.com/FasterSpeeding/Tanjun/blob/2.0.0a1/examples/slash_component.py
- Dependency injection, this feature is in it's early days and under documented but is still partially documented by
  the examples at https://github.com/FasterSpeeding/Tanjun/blob/2.0.0a1/examples/ . For now this only covers command
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

[Unreleased]: https://github.com/olivierlacan/keep-a-changelog/compare/v2.0.0a1...HEAD
[v2.0.0a1]: https://github.com/olivierlacan/keep-a-changelog/compare/1.0.1a5...v2.0.0a1
