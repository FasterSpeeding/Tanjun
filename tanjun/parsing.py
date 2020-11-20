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

__all__: typing.Sequence[str] = ["argument", "option", "Parameter", "ShlexParser"]

import asyncio
import itertools
import shlex
import typing

from hikari import undefined

from tanjun import errors
from tanjun import traits


class ShlexTokenizer:
    __slots__: typing.Sequence[str] = ("__arg_buffer", "__last_name", "__options_buffer", "__shlex")

    def __init__(self, content: str, /) -> None:
        self.__arg_buffer: typing.MutableSequence[str] = []
        self.__last_name: typing.Optional[str] = None
        self.__options_buffer: typing.MutableSequence[typing.Tuple[str, typing.Optional[str]]] = []
        self.__shlex = shlex.shlex(content, posix=True)
        self.__shlex.whitespace = " "
        self.__shlex.whitespace_split = True

    def collect_options(self) -> typing.Mapping[str, typing.Sequence[typing.Optional[str]]]:
        results: typing.MutableMapping[str, typing.MutableSequence[typing.Optional[str]]] = {}

        while (option_ := self.next_option()) is not None:
            name, value = option_

            if name not in results:
                results[name] = []

            results[name].append(value)

        return results

    def iter_arguments(self) -> typing.Iterator[str]:
        while (argument_ := self.next_argument()) is not None:
            yield argument_

    def next_argument(self) -> typing.Optional[str]:
        if self.__arg_buffer:
            return self.__arg_buffer.pop(0)

        while isinstance(value := self.__seek_shlex(), tuple):
            self.__options_buffer.append(value)

        return value

    def next_option(self) -> typing.Optional[typing.Tuple[str, typing.Optional[str]]]:
        if self.__options_buffer:
            return self.__options_buffer.pop(0)

        while isinstance(value := self.__seek_shlex(), str):
            self.__arg_buffer.append(value)

        return value

    def __seek_shlex(self) -> typing.Union[str, typing.Tuple[str, typing.Optional[str]], None]:
        option_name = self.__last_name
        for value in self.__shlex:
            is_option = value.startswith("-")
            if is_option and option_name is not None:
                self.__last_name = value
                return (option_name, None)

            if is_option:
                option_name = value
                continue

            if option_name:
                return (option_name, value)

            return value

        if self.__last_name is not None:
            last_name = self.__last_name
            self.__last_name = None
            return (last_name, None)

        return None


async def _convert_or_default_option(
    ctx: traits.Context, option_: traits.Parameter, value: typing.Optional[typing.Any], /
) -> typing.Any:
    if value is not None:
        return await option_.convert(ctx, value)

    if option_.empty_value is not undefined.UNDEFINED:
        return option_.empty_value

    raise errors.ParserError(f"Option '{option_.names[0]} cannot be empty.", option_)


class SemanticShlex(ShlexTokenizer):
    __slots__: typing.Sequence[str] = ("__ctx",)

    def __init__(self, ctx: traits.Context, /) -> None:
        super().__init__(ctx.content)
        self.__ctx = ctx

    async def get_arguments(self, arguments: typing.Sequence[traits.Parameter], /) -> typing.Sequence[typing.Any]:
        results: typing.MutableSequence[typing.Any] = []
        for argument_ in arguments:
            results.append(await self.__process_argument(argument_))

            if argument_.flags.get("greedy") or argument_.flags.get("multi"):
                break  # Multi and Greedy parameters should always be the last parameter.

        return results

    async def get_options(self, options: typing.Sequence[traits.Parameter], /) -> typing.Mapping[str, typing.Any]:
        results: typing.MutableMapping[str, typing.Any] = {}
        raw_options = self.collect_options()
        for option_ in options:
            key = option_.key
            assert key is not None  # This shouldn't ever be None for options
            values_iter = itertools.chain.from_iterable(
                raw_options[name] for name in option_.names if name in raw_options
            )
            is_multi = option_.flags.get("multi", False)
            if is_multi and (values := list(values_iter)):
                results[key] = asyncio.gather(
                    *(_convert_or_default_option(self.__ctx, option_, value) for value in values)
                )

            elif not is_multi and (value := next(values_iter, None)) is not None:
                results[key] = await _convert_or_default_option(self.__ctx, option_, value)

            else:
                results[key] = option_.default  # This shouldn't ever be UNDEFINED for options.

        return results

    async def __process_argument(self, argument_: traits.Parameter) -> typing.Any:
        if argument_.flags.get("greedy") and (value := " ".join(self.iter_arguments())):
            return await argument_.convert(self.__ctx, value)

        if argument_.flags.get("multi") and (values := list(self.iter_arguments())):
            return await asyncio.gather(*(argument_.convert(self.__ctx, value) for value in values))

        # If the previous two statements don't lead to anything being returned then this won't either.
        if (optional_value := self.next_argument()) is not None:
            return await argument_.convert(self.__ctx, optional_value)

        if argument_.default is not undefined.UNDEFINED:
            return argument_.default  # TODO: do we want to allow a default for arguments?

        # If this is reached then no value was found.
        raise errors.ParserError(f"Missing value for required argument '{argument_.names[0]}'", argument_)


def argument(
    name: str,
    converters: typing.Iterable[typing.Union[typing.Callable[[str], typing.Any], traits.Converter[typing.Any]]],
    *,
    default: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
    flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
) -> typing.Callable[[traits.ExecutableCommand], traits.ExecutableCommand]:
    def decorator(command: traits.ExecutableCommand, /) -> traits.ExecutableCommand:
        if command.parser is None:
            raise ValueError("Cannot add a parameter to a command client without a parser.")

        argument_ = Parameter(name, converters=converters, is_option=False, default=default, flags=flags)
        command.parser.add_parameter(argument_)
        return command

    return decorator


def option(
    key: str,
    name: str,
    *names: str,
    converters: typing.Iterable[typing.Union[typing.Callable[[str], typing.Any], traits.Converter[typing.Any]]],
    default: typing.Any,
    empty_value: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
    flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
) -> typing.Callable[[traits.ExecutableCommand], traits.ExecutableCommand]:
    def decorator(command: traits.ExecutableCommand) -> traits.ExecutableCommand:
        if command.parser is None:
            raise ValueError("Cannot add an option to a command client without a parser.")

        option_ = Parameter(
            name,
            *names,
            converters=converters,
            is_option=True,
            default=default,
            empty_value=empty_value,
            flags=flags,
            key=key,
        )
        command.parser.add_parameter(option_)
        return command

    return decorator


class Parameter(traits.Parameter):  # TODO: some logic confirming for optional vs non-optional fields.
    __slots__: typing.Sequence[str] = ("_converters", "default", "empty_value", "_flags", "_is_option", "key", "names")

    def __init__(
        self,
        name: str,
        *names: str,
        converters: typing.Iterable[typing.Union[typing.Callable[[str], typing.Any], traits.Converter[typing.Any]]],
        is_option: bool,
        default: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        empty_value: undefined.UndefinedOr[typing.Any] = undefined.UNDEFINED,
        flags: typing.Optional[typing.Mapping[str, typing.Any]] = None,
        key: typing.Optional[str] = None,
    ) -> None:  # TODO: verify signature
        if not is_option and empty_value is not undefined.UNDEFINED:
            raise ValueError("empty_value cannot be specified for a required argument")

        if not is_option and key is not None:
            raise ValueError("key cannot be specified for a required argument")

        if is_option and key is None:
            raise ValueError("key must be specified for a optional argument")

        self._converters = set(converters)
        self.default = default
        self.empty_value = empty_value
        self._flags = dict(flags) if flags else {}
        self._is_option = is_option
        self.key = key
        self.names = [name, *names]

    @property
    def converters(
        self,
    ) -> typing.AbstractSet[typing.Union[typing.Callable[[str], typing.Any], traits.Converter[typing.Any]]]:
        return frozenset(self._converters)

    @property
    def flags(self) -> typing.MutableMapping[str, typing.Any]:
        return self._flags

    @property
    def is_option(self) -> bool:
        return self._is_option

    def add_converter(
        self, converter: typing.Union[typing.Callable[[str], typing.Any], traits.Converter[typing.Any]], /
    ) -> None:
        self._converters.add(converter)

    def remove_converter(
        self, converter: typing.Union[typing.Callable[[str], typing.Any], traits.Converter[typing.Any]], /
    ) -> None:
        self._converters.remove(converter)

    def bind_component(self, component: traits.Component, /) -> None:
        pass

    async def convert(self, ctx: traits.Context, value: str) -> typing.Any:
        sources: typing.MutableSequence[ValueError] = []
        for converter in self._converters:
            try:
                if isinstance(converter, traits.Converter):
                    return await converter.convert(ctx, value)

                return converter(value)

            except ValueError as exc:
                sources.append(exc)

        raise errors.ConversionError(sources)


class ShlexParser(traits.Parser):
    __slots__: typing.Sequence[str] = ("_arguments", "_options")

    def __init__(self, *, parameters: typing.Optional[typing.Iterable[traits.Parameter]] = None) -> None:
        self._arguments: typing.MutableSequence[traits.Parameter] = []
        self._options: typing.MutableSequence[traits.Parameter] = []

        if parameters is not None:
            self.set_parameters(parameters)

    @property
    def parameters(self) -> typing.Sequence[traits.Parameter]:
        return (*self._arguments, *self._options)

    def add_parameter(self, parameter_: traits.Parameter, /) -> None:
        if parameter_.is_option:
            self._options.append(parameter_)

        else:
            self._arguments.append(parameter_)  # TODO: verify the signature

    def remove_parameter(self, parameter_: traits.Parameter, /) -> None:
        if parameter_.is_option:
            self._options.remove(parameter_)

        else:
            self._arguments.remove(parameter_)  # TODO: verify the signature

    def set_parameters(self, parameters: typing.Iterable[traits.Parameter], /) -> None:
        self._arguments = [parameter_ for parameter_ in parameters if not parameter_.is_option]
        self._options = [parameter_ for parameter_ in parameters if parameter_.is_option]
        # TODO: verify the signature

    def bind_component(self, component: traits.Component, /) -> None:
        pass

    async def parse(
        self, ctx: traits.Context, /
    ) -> typing.Tuple[typing.Sequence[typing.Any], typing.Mapping[str, typing.Any]]:
        parser = SemanticShlex(ctx)

        arguments = await parser.get_arguments(self._arguments)
        options = await parser.get_options(self._options)
        return arguments, options
