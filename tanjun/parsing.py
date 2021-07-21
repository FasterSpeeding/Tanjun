# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import annotations

__all__: typing.Sequence[str] = [
    "Argument",
    "Option",
    "ShlexParser",
    "verify_parameters",
    "with_argument",
    "with_greedy_argument",
    "with_multi_argument",
    "with_option",
    "with_multi_option",
    "with_parser",
    "with_typed_parameters",
]

import asyncio
import copy
import itertools
import shlex
import typing
from collections import abc as collections

from tanjun import conversion
from tanjun import errors
from tanjun import injector as injector_
from tanjun import traits

if typing.TYPE_CHECKING:
    _ParameterT = typing.TypeVar("_ParameterT", bound="_Parameter")
    _ShlexParserT = typing.TypeVar("_ShlexParserT", bound="ShlexParser")

CommandT = typing.TypeVar("CommandT", bound=traits.MessageCommand)
GREEDY = "greedy"
"""Parameter flags key used for marking a parameter as "greedy".

This means that the parameter will take in the rest of the positional
arguments as one value.

!!! note
    This cannot be used in conjunction with "multi" and only applies
    to arguments (not options).
"""
MULTI = "multi"
"""Parameter flags key used for marking a parameter as "multi".

This will result in the parameter always receiving an array of results.

!!! note
    This cannot be used in conjunction with "greedy" and can apply to both
    options and arguments.
"""


class ShlexTokenizer:
    __slots__: typing.Sequence[str] = ("__arg_buffer", "__last_name", "__options_buffer", "__shlex")

    def __init__(self, content: str, /) -> None:
        self.__arg_buffer: typing.List[str] = []
        self.__last_name: typing.Optional[str] = None
        self.__options_buffer: typing.List[typing.Tuple[str, typing.Optional[str]]] = []
        self.__shlex = shlex.shlex(content, posix=True)
        self.__shlex.whitespace = " "
        self.__shlex.whitespace_split = True

    def collect_raw_options(self) -> typing.Mapping[str, typing.Sequence[typing.Optional[str]]]:
        results: typing.Dict[str, typing.List[typing.Optional[str]]] = {}

        while (option := self.next_raw_option()) is not None:
            name, value = option

            if name not in results:
                results[name] = []

            results[name].append(value)

        return results

    def iter_raw_arguments(self) -> typing.Iterator[str]:
        while (argument := self.next_raw_argument()) is not None:
            yield argument

    def next_raw_argument(self) -> typing.Optional[str]:
        if self.__arg_buffer:
            return self.__arg_buffer.pop(0)

        # TODO: this is probably slow
        while isinstance(value := self.__seek_shlex(), tuple):
            self.__options_buffer.append(value)

        return value

    def next_raw_option(self) -> typing.Optional[typing.Tuple[str, typing.Optional[str]]]:
        if self.__options_buffer:
            return self.__options_buffer.pop(0)

        # TODO: this is probably slow
        while isinstance(value := self.__seek_shlex(), str):
            self.__arg_buffer.append(value)

        return value

    def __seek_shlex(self) -> typing.Union[str, typing.Tuple[str, typing.Optional[str]], None]:
        option_name = self.__last_name

        try:
            value = next(self.__shlex)

        except StopIteration:
            if option_name is not None:
                self.__last_name = None
                return (option_name, None)

            return None

        except ValueError as exc:
            raise errors.ParserError(str(exc), None) from exc

        is_option = value.startswith("-")
        if is_option and option_name is not None:
            self.__last_name = value
            return (option_name, None)

        if is_option:
            self.__last_name = value
            return self.__seek_shlex()

        if option_name:
            self.__last_name = None
            return (option_name, value)

        return value


async def _covert_option_or_empty(
    ctx: traits.MessageContext, option: traits.Option, value: typing.Optional[typing.Any], /
) -> typing.Any:
    if value is not None:
        return await option.convert(ctx, value)

    if option.empty_value is not traits.UNDEFINED_DEFAULT:
        return option.empty_value

    raise errors.NotEnoughArgumentsError(f"Option '{option.key} cannot be empty.", option)


class SemanticShlex(ShlexTokenizer):
    __slots__: typing.Sequence[str] = ("__ctx",)

    def __init__(self, ctx: traits.MessageContext, /) -> None:
        super().__init__(ctx.content)
        self.__ctx = ctx

    async def get_arguments(self, arguments: typing.Sequence[traits.Argument], /) -> typing.List[typing.Any]:
        results: typing.List[typing.Any] = []
        for argument in arguments:
            results.append(await self.__process_argument(argument))

            if argument.flags.get(GREEDY) or argument.flags.get(MULTI):
                break  # Multi and Greedy parameters should always be the last parameter.

        return results

    async def get_options(self, options: typing.Sequence[traits.Option], /) -> typing.Dict[str, typing.Any]:
        raw_options = self.collect_raw_options()
        results = asyncio.gather(*map(lambda option: self.__process_option(option, raw_options), options))
        return dict(zip((option.key for option in options), await results))

    async def __process_argument(self, argument: traits.Parameter) -> typing.Any:
        if argument.flags.get(GREEDY) and (value := " ".join(self.iter_raw_arguments())):
            return await argument.convert(self.__ctx, value)

        if argument.flags.get(MULTI) and (values := list(self.iter_raw_arguments())):
            return await asyncio.gather(*(argument.convert(self.__ctx, value) for value in values))

        # If the previous two statements failed on getting raw arguments then this will as well.
        if (optional_value := self.next_raw_argument()) is not None:
            return await argument.convert(self.__ctx, optional_value)

        if argument.default is not traits.UNDEFINED_DEFAULT:
            return argument.default

        # If this is reached then no value was found.
        raise errors.NotEnoughArgumentsError(f"Missing value for required argument '{argument.key}'", argument)

    async def __process_option(
        self, option: traits.Option, raw_options: typing.Mapping[str, typing.Sequence[typing.Optional[str]]]
    ) -> typing.Any:
        values_iter = itertools.chain.from_iterable(raw_options[name] for name in option.names if name in raw_options)
        is_multi = option.flags.get(MULTI, False)
        if is_multi and (values := list(values_iter)):
            return await asyncio.gather(*(_covert_option_or_empty(self.__ctx, option, value) for value in values))

        if not is_multi and (value := next(values_iter, ...)) is not ...:
            if next(values_iter, ...) is not ...:
                raise errors.TooManyArgumentsError(f"Option `{option.key}` can only take a single value", option)

            return await _covert_option_or_empty(self.__ctx, option, value)

        if option.default is not traits.UNDEFINED_DEFAULT:
            return option.default

        # If this is reached then no value was found.
        raise errors.NotEnoughArgumentsError(f"Missing required option `{option.key}`", option)


def with_argument(
    key: str,
    /,
    converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
    *,
    default: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[CommandT], CommandT]:
    """Add an argument to a command or command descriptor through a decorator call.

    !!! info
        Order matters for positional arguments and since decorator execution
        starts at the decorator closest to the command and goes upwards this
        will decide where a positional argument is located in a command's
        signature.

    Parameters
    ----------
    key : str
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's function during execution).
    converters : typing.Union[tanjun.traits.ConverterSig, typing.Iterable[tanjun.traits.ConverterSig], builtins.None]
        The converter(s) this argument should use to handle values passed to it
        during parsing, this may be left as `builtins.None to indicate that
        the raw string value should be returned without conversion.
    default : typing.Any
        The default value of this argument, if left as
        `tanjun.traits.UNDEFINED_DEFAULT` then this will have no default.
    flags : typing.Optional[typing.MutableMapping[str, typing.Any]]
        A mutable mapping of metadata flags to initiate this argument with.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]:
        A command or command descriptor decorator function which will add this
        argument.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_argument("command", converters=(int,), default=42)
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.traits.Context, /, argument: int):
        ...
    ```
    """

    def decorator(command: CommandT, /) -> CommandT:
        if command.parser is None:
            raise ValueError("Cannot add a parameter to a command client without a parser.")

        argument = Argument(key, converters=converters, default=default, flags=flags)
        command.parser.add_parameter(argument)
        return command

    return decorator


def with_greedy_argument(
    key: str,
    /,
    converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
    *,
    default: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[CommandT], CommandT]:
    """Add a greedy argument to a command or command descriptor through a decorator call.

    !!! note
        A greedy argument will consume the remaining positional arguments and pass
        them through to the converters as one joined string while also requiring
        that at least one more positional argument is remaining unless a
        default is set.

    !!! info
        Order matters for positional arguments and since decorator execution
        starts at the decorator closest to the command and goes upwards this
        will decide where a positional argument is located in a command's
        signature.

    Parameters
    ----------
    key : str
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's function during execution).

    Other Parameters
    ----------------
    converters : typing.Union[tanjun.traits.ConverterSig, typing.Iterable[tanjun.traits.ConverterSig], builtins.None]
        The converter(s) this argument should use to handle values passed to it
        during parsing, this may be left as `builtins.None to indicate that
        the raw string value should be returned without conversion.
    default : typing.Any
        The default value of this argument, if left as
        `tanjun.traits.UNDEFINED_DEFAULT` then this will have no default.
    flags : typing.Optional[typing.MutableMapping[str, typing.Any]]
        A mutable mapping of metadata flags to initiate this argument with.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]:
        A command or command descriptor decorator function which will add this
        argument.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_greedy_argument("command", converters=(StringView,))
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.traits.Context, /, argument: StringView):
        ...
    ```
    """
    if flags is None:
        flags = {}

    flags[GREEDY] = True
    return with_argument(key, converters=converters, default=default, flags=flags)


def with_multi_argument(
    key: str,
    /,
    converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
    *,
    default: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[CommandT], CommandT]:
    """Add a greedy argument to a command or command descriptor through a decorator call.

    !!! note
        A multi argument will consume the remaining positional arguments and pass
        them to the converters through multiple calls while also requiring that
        at least one more positional argument is remaining unless a default is
        set and passing through the results to the command's function as a
        sequence.

    !!! info
        Order matters for positional arguments and since decorator execution
        starts at the decorator closest to the command and goes upwards this
        will decide where a positional argument is located in a command's
        signature.

    Parameters
    ----------
    key : str
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's function during execution).

    Other Parameters
    ----------------
    converters : typing.Union[tanjun.traits.ConverterSig, typing.Iterable[tanjun.traits.ConverterSig], builtins.None]
        The converter(s) this argument should use to handle values passed to it
        during parsing, this may be left as `builtins.None to indicate that
        the raw string value should be returned without conversion.
    default : typing.Any
        The default value of this argument, if left as
        `tanjun.traits.UNDEFINED_DEFAULT` then this will have no default.
    flags : typing.Optional[typing.MutableMapping[str, typing.Any]]
        A mutable mapping of metadata flags to initiate this argument with.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]:
        A command or command descriptor decorator function which will add this
        argument.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_multi_argument("command", converters=(int,))
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.traits.Context, /, argument: typing.Sequence[int]):
        ...
    ```
    """
    if flags is None:
        flags = {}

    flags[MULTI] = True
    return with_argument(key, converters=converters, default=default, flags=flags)


# TODO: add default getter
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
    default: typing.Any,
    empty_value: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[CommandT], CommandT]:
    """Add an option to a command or command descriptor through a decorator call.

    Parameters
    ----------
    key : str
        The string identifier of this option which will be used to pass the
        result of this argument to the command's function during execution as
        a keyword argument.
    name : str
        The name of this option used for identifying it in the parsed content.
    default : typing.Any
        The default value of this argument, unlike arguments this is required
        for options.

    Other Parameters
    ----------------
    *names : str
        Other names of this option used for identifying it in the parsed content.
    converters : typing.Union[tanjun.traits.ConverterSig, typing.Iterable[tanjun.traits.ConverterSig], builtins.None]
        The converter(s) this argument should use to handle values passed to it
        during parsing, this may be left as `builtins.None to indicate that
        the raw string value should be returned without conversion.
    empty_value : typing.Any
        The value to use if this option is provided without a value. If left as
        `tanjun.traits.UNDEFINED_DEFAULT` then this option will error if it's
        provided without a value.
    flags : typing.Optional[typing.MutableMapping[str, typing.Any]]
        A mutable mapping of metadata flags to initiate this option with.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]:
        A command or command descriptor decorator function which will add this
        option.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_option("command", converters=(int,), default=42)
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.traits.Context, /, argument: int):
        ...
    ```
    """

    def decorator(command: CommandT) -> CommandT:
        if command.parser is None:
            raise ValueError("Cannot add an option to a command client without a parser.")

        option = Option(key, name, *names, converters=converters, default=default, empty_value=empty_value, flags=flags)
        command.parser.add_parameter(option)
        return command

    return decorator


def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
    default: typing.Any,
    empty_value: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[CommandT], CommandT]:
    """Add an multi-option to a command or command descriptor through a decorator call.

    !!! note
        A multi option will consume all the values provided for an option and
        pass them through to the converters as an array of strings while also
        requiring that at least one value is provided for the option unless
        a default is set.

    Parameters
    ----------
    key : str
        The string identifier of this option which will be used to pass the
        result of this argument to the command's function during execution as
        a keyword argument.
    name : str
        The name of this option used for identifying it in the parsed content.
    default : typing.Any
        The default value of this argument, unlike arguments this is required
        for options.

    Other Parameters
    ----------------
    *names : str
        Other names of this option used for identifying it in the parsed content.
    converters : typing.Union[tanjun.traits.ConverterSig, typing.Iterable[tanjun.traits.ConverterSig], builtins.None]
        The converter(s) this argument should use to handle values passed to it
        during parsing, this may be left as `builtins.None to indicate that
        the raw string value should be returned without conversion.
    empty_value : typing.Any
        The value to use if this option is provided without a value. If left as
        `tanjun.traits.UNDEFINED_DEFAULT` then this option will error if it's
        provided without a value.
    flags : typing.Optional[typing.MutableMapping[str, typing.Any]]
        A mutable mapping of metadata flags to initiate this option with.

    Returns
    -------
    typing.Callable[[CommandT], CommandT]:
        A command or command descriptor decorator function which will add this
        option.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_multi_option("command", converters=(int,), default=())
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.traits.Context, /, argument: typing.Sequence[int]):
        ...
    ```
    """
    if flags is None:
        flags = {}

    flags[MULTI] = True
    return with_option(key, name, *names, converters=converters, default=default, empty_value=empty_value, flags=flags)


class _Parameter(injector_.Injectable, traits.Parameter):
    __slots__: typing.Sequence[str] = (
        "_client",
        "_component",
        "_converters",
        "_default",
        "_flags",
        "_injector",
        "_key",
    )

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
        default: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    ) -> None:
        self._client: typing.Optional[traits.Client] = None
        self._component: typing.Optional[traits.Component] = None
        self._converters: typing.Optional[typing.List[injector_.InjectableConverter[typing.Any]]] = None
        self._default = default
        self._flags = dict(flags) if flags else {}
        self._injector: typing.Optional[injector_.InjectorClient] = None
        self._key = key

        if key.startswith("-"):
            raise ValueError("parameter key cannot start with `-`")

        if converters is not None:
            if isinstance(converters, collections.Iterable):
                for converter in converters:
                    self.add_converter(converter)

            else:
                self.add_converter(converters)

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self._key}>"

    @property
    def converters(self) -> typing.Optional[typing.Sequence[traits.ConverterSig]]:
        return tuple(converter.callback for converter in self._converters) if self._converters is not None else None

    @property
    def default(self) -> typing.Union[typing.Any, traits.UndefinedDefaultT]:
        return self._default

    @property
    def flags(self) -> typing.MutableMapping[str, typing.Any]:
        return self._flags

    @property
    def key(self) -> str:
        return self._key

    @property
    def needs_injector(self) -> bool:
        # TODO: cache this value?
        return any(converter.needs_injector for converter in self._converters) if self._converters else False

    def add_converter(self, converter: traits.ConverterSig, /) -> None:
        if self._converters is None:
            self._converters = []

        if isinstance(converter, conversion.BaseConverter):
            if self._client:
                converter.bind_client(self._client)

            if self._component:
                converter.bind_component(self._component)

        if not isinstance(converter, injector_.InjectableConverter):
            # Some types like `bool` and `bytes` are overridden here for the sake of convenience.
            converter = conversion.override_type(converter)
            converter = injector_.InjectableConverter(converter, injector=self._injector)

        self._converters.append(converter)

    def remove_converter(self, converter: traits.ConverterSig, /) -> None:
        if self._converters is None:
            raise ValueError("No converters set")

        self._converters.remove(converter)  # type: ignore # reportGeneralTypeIssues

        if not self._converters:
            self._converters = None

    def bind_client(self, client: traits.Client, /) -> None:
        if not self._converters:
            return

        self._client = client
        for converter in self._converters:
            if isinstance(converter.callback, conversion.BaseConverter):
                converter.callback.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        if not self._converters:
            return

        self._component = component
        for converter in self._converters:
            if isinstance(converter.callback, conversion.BaseConverter):
                converter.callback.bind_component(component)

    async def convert(self, ctx: traits.Context, value: str) -> typing.Any:
        if self._converters is None:
            return value

        sources: typing.List[ValueError] = []
        for converter in self._converters:
            try:
                return await converter(value, ctx)

            except ValueError as exc:
                sources.append(exc)

        raise errors.ConversionError(self, sources)

    def set_injector(self, client: injector_.InjectorClient, /) -> None:
        if self._injector is not None:
            raise RuntimeError("Injector already set")

        self._injector = client
        if self._converters:
            for converter in self._converters:
                converter.set_injector(client)

    def copy(self: _ParameterT, *, _new: bool = True) -> _ParameterT:
        if not _new:
            self._converters = [converter.copy() for converter in self._converters] if self._converters else None
            self._flags = self._flags.copy()
            return self

        result = copy.copy(self).copy(_new=False)
        return result


class Argument(_Parameter, traits.Argument):
    __slots__: typing.Sequence[str] = ()

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
        default: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    ) -> None:
        if flags and MULTI in flags and GREEDY in flags:
            raise ValueError("Argument cannot be both greed and multi.")

        super().__init__(key, converters=converters, default=default, flags=flags)


class Option(_Parameter, traits.Option):
    __slots__: typing.Sequence[str] = ("_empty_value", "_names")

    def __init__(
        self,
        key: str,
        name: str,
        *names: str,
        converters: typing.Union[typing.Iterable[traits.ConverterSig], traits.ConverterSig, None] = None,
        default: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
        empty_value: typing.Union[typing.Any, traits.UndefinedDefaultT] = traits.UNDEFINED_DEFAULT,
    ) -> None:
        if not name.startswith("-") or not all(n.startswith("-") for n in names):
            raise ValueError("All option names must start with `-`")

        if flags and GREEDY in flags:
            raise ValueError("Option cannot be greedy")

        self._empty_value = empty_value
        self._names = [name, *names]
        super().__init__(key, converters=converters, default=default, flags=flags)

    @property
    def empty_value(self) -> typing.Union[typing.Any, traits.UndefinedDefaultT]:
        return self._empty_value

    @property
    def names(self) -> typing.Sequence[str]:
        return self._names.copy()

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.key}, {self._names}>"


class ShlexParser(injector_.Injectable, traits.Parser):
    """A shlex based `tanjun.traits.Parser` implementation."""

    __slots__: typing.Sequence[str] = ("_arguments", "_client", "_component", "_injector", "_options")

    def __init__(self, *, parameters: typing.Optional[typing.Iterable[traits.Parameter]] = None) -> None:
        self._arguments: typing.List[traits.Argument] = []
        self._client: typing.Optional[traits.Client] = None
        self._component: typing.Optional[traits.Component] = None
        self._injector: typing.Optional[injector_.InjectorClient] = None
        self._options: typing.List[traits.Option] = []

        if parameters is not None:
            self.set_parameters(parameters)

    @property
    def needs_injector(self) -> bool:
        # TODO: cache this value?
        return any(
            isinstance(parameter, injector_.Injectable) and parameter.needs_injector
            for parameter in itertools.chain(self._options, self._arguments)
        )

    @property
    def parameters(self) -> typing.Sequence[traits.Parameter]:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        return (*self._arguments, *self._options)

    def copy(self: _ShlexParserT, *, _new: bool = True) -> _ShlexParserT:
        if not _new:
            self._arguments = [argument.copy() for argument in self._arguments]
            self._options = [option.copy() for option in self._options]
            return self

        return copy.copy(self).copy(_new=False)

    def add_parameter(self, parameter: traits.Parameter, /) -> None:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        if self._injector and isinstance(parameter, injector_.Injectable):
            parameter.set_injector(self._injector)

        if self._client:
            parameter.bind_client(self._client)

        if self._component:
            parameter.bind_component(self._component)

        if isinstance(parameter, traits.Option):
            self._options.append(parameter)

        elif isinstance(parameter, traits.Argument):
            self._arguments.append(parameter)
            found_final_argument = False

            for argument in self._arguments:
                if found_final_argument:
                    del self._arguments[-1]
                    raise ValueError("Multi or greedy argument must be the last argument")

                found_final_argument = MULTI in argument.flags or GREEDY in argument.flags

        else:
            raise ValueError("Invalid type passed")

    def remove_parameter(self, parameter: traits.Parameter, /) -> None:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        if isinstance(parameter, traits.Option):
            self._options.remove(parameter)

        elif isinstance(parameter, traits.Argument):
            self._arguments.remove(parameter)

        else:
            raise ValueError("Invalid type passed")

    def set_injector(self, client: injector_.InjectorClient, /) -> None:
        self._injector = client

        for parameter in itertools.chain(self._options, self._arguments):
            if isinstance(parameter, injector_.Injectable):
                parameter.set_injector(client)

    def set_parameters(self, parameters: typing.Iterable[traits.Parameter], /) -> None:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        self._arguments = []
        self._options = []

        for parameter in parameters:
            self.add_parameter(parameter)

    def bind_client(self, client: traits.Client, /) -> None:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        self._client = client
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        self._component = component
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_component(component)

    async def parse(
        self, ctx: traits.MessageContext, /
    ) -> typing.Tuple[typing.List[typing.Any], typing.Dict[str, typing.Any]]:
        # <<inherited docstring from tanjun.traits.ShlexParser>>.
        parser = SemanticShlex(ctx)
        arguments = await parser.get_arguments(self._arguments)
        options = await parser.get_options(self._options)
        return arguments, options


# Unlike the other decorators in this module, this can only be applied to a command descriptor.
def with_parser(command: CommandT, /) -> CommandT:
    """Add a shlex parser descriptor to a command descriptor."""
    return command.set_parser(ShlexParser())


def with_typed_parameters(command: CommandT, /, *, ignore_self: bool) -> CommandT:
    # TODO: implement this to enable generating parameters from a function's signature.
    if command.parser is None:
        raise RuntimeError("Cannot generate parameters for a command with no parser")

    if command.function is None:
        raise RuntimeError("Cannot generate parameters for a command with no function")

    raise NotImplementedError


def verify_parameters(command: CommandT, /) -> CommandT:
    # TODO: implement this to verify the parameters of a command against the function signature
    return command
