# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020, Faster Speeding
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
    "argument",
    "greedy_argument",
    "multi_argument",
    "option",
    "multi_option",
    "Argument",
    "Option",
    "ShlexParser",
    "parser_descriptor",
    "with_parser",
    "generate_parameters",
    "verify_parameters",
]

import asyncio
import copy
import itertools
import shlex
import typing

from hikari import undefined

from tanjun import conversion
from tanjun import errors
from tanjun import traits

_CommandT = typing.TypeVar("_CommandT", bound=traits.CommandDescriptor)
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
        self.__arg_buffer: typing.MutableSequence[str] = []
        self.__last_name: typing.Optional[str] = None
        self.__options_buffer: typing.MutableSequence[typing.Tuple[str, typing.Optional[str]]] = []
        self.__shlex = shlex.shlex(content, posix=True)
        self.__shlex.whitespace = " "
        self.__shlex.whitespace_split = True

    def collect_raw_options(self) -> typing.Mapping[str, typing.Sequence[typing.Optional[str]]]:
        results: typing.MutableMapping[str, typing.MutableSequence[typing.Optional[str]]] = {}

        while (option_ := self.next_raw_option()) is not None:
            name, value = option_

            if name not in results:
                results[name] = []

            results[name].append(value)

        return results

    def iter_raw_arguments(self) -> typing.Iterator[str]:
        while (argument_ := self.next_raw_argument()) is not None:
            yield argument_

    def next_raw_argument(self) -> typing.Optional[str]:
        if self.__arg_buffer:
            return self.__arg_buffer.pop(0)

        while isinstance(value := self.__seek_shlex(), tuple):
            self.__options_buffer.append(value)

        return value

    def next_raw_option(self) -> typing.Optional[typing.Tuple[str, typing.Optional[str]]]:
        if self.__options_buffer:
            return self.__options_buffer.pop(0)

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
    ctx: traits.Context, option_: traits.Option, value: typing.Optional[typing.Any], /
) -> typing.Any:
    if value is not None:
        return await option_.convert(ctx, value)

    if option_.empty_value is not traits.UNDEFINED_DEFAULT:
        return option_.empty_value

    raise errors.NotEnoughArgumentsError(f"Option '{option_.key} cannot be empty.", option_)


class SemanticShlex(ShlexTokenizer):
    __slots__: typing.Sequence[str] = ("__ctx",)

    def __init__(self, ctx: traits.Context, /) -> None:
        super().__init__(ctx.content)
        self.__ctx = ctx

    async def get_arguments(self, arguments: typing.Sequence[traits.Argument], /) -> typing.MutableSequence[typing.Any]:
        results: typing.MutableSequence[typing.Any] = []
        for argument_ in arguments:
            results.append(await self.__process_argument(argument_))

            if argument_.flags.get(GREEDY) or argument_.flags.get(MULTI):
                break  # Multi and Greedy parameters should always be the last parameter.

        return results

    async def get_options(self, options: typing.Sequence[traits.Option], /) -> typing.MutableMapping[str, typing.Any]:
        raw_options = self.collect_raw_options()
        results = asyncio.gather(*map(lambda option_: self.__process_option(option_, raw_options), options))
        return dict(zip((option_.key for option_ in options), await results))

    async def __process_argument(self, argument_: traits.Parameter) -> typing.Any:
        if argument_.flags.get(GREEDY) and (value := " ".join(self.iter_raw_arguments())):
            return await argument_.convert(self.__ctx, value)

        if argument_.flags.get(MULTI) and (values := list(self.iter_raw_arguments())):
            return await asyncio.gather(*(argument_.convert(self.__ctx, value) for value in values))

        # If the previous two statements failed on getting raw arguments then this will as well.
        if (optional_value := self.next_raw_argument()) is not None:
            return await argument_.convert(self.__ctx, optional_value)

        if argument_.default is not traits.UNDEFINED_DEFAULT:
            return argument_.default

        # If this is reached then no value was found.
        raise errors.NotEnoughArgumentsError(f"Missing value for required argument '{argument_.key}'", argument_)

    async def __process_option(
        self, option_: traits.Option, raw_options: typing.Mapping[str, typing.Sequence[typing.Optional[str]]]
    ) -> typing.Any:
        values_iter = itertools.chain.from_iterable(raw_options[name] for name in option_.names if name in raw_options)
        is_multi = option_.flags.get(MULTI, False)
        if is_multi and (values := list(values_iter)):
            return asyncio.gather(*(_covert_option_or_empty(self.__ctx, option_, value) for value in values))

        if not is_multi and (value := next(values_iter, undefined.UNDEFINED)) is not undefined.UNDEFINED:
            if next(values_iter, undefined.UNDEFINED) is not undefined.UNDEFINED:
                raise errors.TooManyArgumentsError(f"Option `{option_.key}` can only take a single value", option_)

            return await _covert_option_or_empty(self.__ctx, option_, value)

        if option_.default is not traits.UNDEFINED_DEFAULT:
            return option_.default

        # If this is reached then no value was found.
        raise errors.NotEnoughArgumentsError(f"Missing required option `{option_.key}`", option_)


def argument(
    key: str,
    /,
    converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
    *,
    default: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[_CommandT], _CommandT]:
    def decorator(command: _CommandT, /) -> _CommandT:
        if command.parser is None:
            raise ValueError("Cannot add a parameter to a command client without a parser.")

        argument_ = Argument(key, converters=converters, default=default, flags=flags)
        command.parser.add_parameter(argument_)
        return command

    return decorator


def greedy_argument(
    key: str,
    /,
    converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
    *,
    default: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[_CommandT], _CommandT]:
    if flags is None:
        flags = {}

    flags[GREEDY] = True
    return argument(key, converters=converters, default=default, flags=flags)


def multi_argument(
    key: str,
    /,
    converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
    *,
    default: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[_CommandT], _CommandT]:
    if flags is None:
        flags = {}

    flags[MULTI] = True
    return argument(key, converters=converters, default=default, flags=flags)


def option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
    default: typing.Any,
    empty_value: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[_CommandT], _CommandT]:
    def decorator(command: _CommandT) -> _CommandT:
        if command.parser is None:
            raise ValueError("Cannot add an option to a command client without a parser.")

        option_ = Option(
            key, name, *names, converters=converters, default=default, empty_value=empty_value, flags=flags,
        )
        command.parser.add_parameter(option_)
        return command

    return decorator


def multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
    default: typing.Any,
    empty_value: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
    flags: typing.Optional[typing.MutableMapping[str, typing.Any]] = None,
) -> typing.Callable[[_CommandT], _CommandT]:
    if flags is None:
        flags = {}

    flags[MULTI] = True
    return option(key, name, *names, converters=converters, default=default, empty_value=empty_value, flags=flags)


class _Parameter(traits.Parameter):
    __slots__: typing.Sequence[str] = ("_converters", "default", "_flags", "key")

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
        default: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    ) -> None:
        self._converters: typing.Optional[typing.MutableSequence[traits.ConverterT]] = None
        self.default = default
        self._flags = dict(flags) if flags else {}
        self.key = key

        if key.startswith("-"):
            raise ValueError("parameter key cannot start with `-`")

        if converters is not None:
            for converter in converters:
                self.add_converter(converter)

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.key}>"

    @property
    def converters(self) -> typing.Optional[typing.Sequence[traits.ConverterT]]:
        return tuple(self._converters) if self._converters is not None else None

    @property
    def flags(self) -> typing.MutableMapping[str, typing.Any]:
        return self._flags

    def add_converter(self, converter: traits.ConverterT, /) -> None:
        if self._converters is None:
            self._converters = []

        # Some builtin types like `bool` and `bytes` are overridden here for the sake of convenience.
        self._converters.append(conversion.override_builtin_type(converter))

    def remove_converter(self, converter: traits.ConverterT, /) -> None:
        if self._converters is None:
            raise ValueError("No converters set")

        self._converters.remove(converter)

        if not self._converters:
            self._converters = None

    def bind_client(self, client: traits.Client, /) -> None:
        if not self._converters:
            return

        for converter in self._converters:
            if isinstance(converter, (traits.Converter, traits.StatelessConverter)):
                converter.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        if not self._converters:
            return

        for converter in self._converters:
            if isinstance(converter, (traits.Converter, traits.StatelessConverter)):
                converter.bind_component(component)

    async def convert(self, ctx: traits.Context, value: str) -> typing.Any:
        if self._converters is None:
            return value

        sources: typing.MutableSequence[ValueError] = []
        for converter in self._converters:
            try:
                if hasattr(converter, "convert"):
                    converter = typing.cast("traits.Converter[typing.Any]", converter)
                    result = await converter.convert(ctx, value)
                    return result

                converter = typing.cast("typing.Callable[[str], typing.Any]", converter)
                return converter(value)

            except ValueError as exc:
                sources.append(exc)

        raise errors.ConversionError(self, sources)


class Argument(_Parameter, traits.Argument):
    __slots__: typing.Sequence[str] = ()

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
        default: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    ) -> None:
        if flags and MULTI in flags and GREEDY in flags:
            raise ValueError("Argument cannot be both greed and multi.")

        super().__init__(key, converters=converters, default=default, flags=flags)

    def __copy__(self) -> Argument:
        return Argument(self.key, converters=self._converters, default=self.default, flags=dict(self._flags))


class Option(_Parameter, traits.Option):
    __slots__: typing.Sequence[str] = ("empty_value", "names")

    def __init__(
        self,
        key: str,
        name: str,
        *names: str,
        converters: typing.Optional[typing.Iterable[traits.ConverterT]] = None,
        default: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
        empty_value: typing.Union[typing.Any, traits.UndefinedDefault] = traits.UNDEFINED_DEFAULT,
    ) -> None:
        names = [name, *names]

        if not all(n.startswith("-") for n in names):
            raise ValueError("All option names must start with `-`")

        if flags and GREEDY in flags:
            raise ValueError("Option cannot be greedy")

        self.empty_value = empty_value
        self.names = names
        super().__init__(key, converters=converters, default=default, flags=flags)

    def __copy__(self) -> Option:
        # TODO: this will error if there's no set names.
        return Option(
            self.key,
            *self.names,
            converters=self._converters,
            default=self.default,
            flags=dict(self._flags),
            empty_value=self.empty_value,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.key}, {self.names}>"


class ShlexParser(traits.Parser):
    __slots__: typing.Sequence[str] = ("_arguments", "_options")

    def __init__(self, *, parameters: typing.Optional[typing.Iterable[traits.Parameter]] = None) -> None:
        self._arguments: typing.MutableSequence[traits.Argument] = []
        self._options: typing.MutableSequence[traits.Option] = []

        if parameters is not None:
            self.set_parameters(parameters)

    @property
    def parameters(self) -> typing.Sequence[traits.Parameter]:
        return (*self._arguments, *self._options)

    def add_parameter(self, parameter_: traits.Parameter, /) -> None:
        if isinstance(parameter_, traits.Option):
            self._options.append(parameter_)

        else:
            self._arguments.append(parameter_)
            found_final_argument = False

            for argument_ in self._arguments:
                if found_final_argument:
                    del self._arguments[-1]
                    raise ValueError("Multi or greedy argument must be the last argument")

                found_final_argument = MULTI in argument_.flags or GREEDY in argument_.flags

    def remove_parameter(self, parameter_: traits.Parameter, /) -> None:
        if isinstance(parameter_, traits.Option):
            self._options.remove(parameter_)

        else:
            self._arguments.remove(parameter_)

    def set_parameters(self, parameters: typing.Iterable[traits.Parameter], /) -> None:
        self._arguments = []
        self._options = []

        for parameter_ in parameters:
            self.add_parameter(parameter_)

    def bind_client(self, client: traits.Client, /) -> None:
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_client(client)

    def bind_component(self, component: traits.Component, /) -> None:
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_component(component)

    async def parse(
        self, ctx: traits.Context, /
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        parser = SemanticShlex(ctx)
        arguments = await parser.get_arguments(self._arguments)
        options = await parser.get_options(self._options)
        return arguments, options


class ParserDescriptor(traits.ParserDescriptor):
    __slots__: typing.Sequence[str] = ("_parameters",)

    def __init__(self, *, parameters: typing.Optional[typing.Iterable[traits.Parameter]] = None) -> None:
        self._parameters = list(parameters) if parameters else []

    def add_parameter(self, parameter: traits.Parameter, /) -> None:
        self._parameters.append(parameter)

    def set_parameters(self, parameters: typing.Iterable[traits.Parameter], /) -> None:
        self._parameters = list(parameters)

    def build_parser(self, component: traits.Component, /) -> ShlexParser:
        parser = ShlexParser(parameters=map(copy.copy, self._parameters))
        parser.bind_component(component)
        return parser


def parser_descriptor(*, parameters: typing.Optional[typing.Iterable[traits.Parameter]] = None) -> ParserDescriptor:
    return ParserDescriptor(parameters=parameters)


def with_parser(cls: _CommandT) -> _CommandT:
    cls.parser = parser_descriptor()
    return cls


def generate_parameters(command: _CommandT, /, *, ignore_self: bool) -> _CommandT:
    # TODO: implement this to enable generating parameters from a function's signature.
    if command.parser is None:
        raise RuntimeError("Cannot generate parameters for a command with no parser")

    if command.function is None:
        raise RuntimeError("Cannot generate parameters for a command with no function")

    raise NotImplementedError


def verify_parameters(command: _CommandT, /) -> _CommandT:
    # TODO: implement this to verify the parameters of a command against the function signature
    return command
