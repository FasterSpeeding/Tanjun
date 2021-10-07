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
"""Standard implementation of message command argument parsing."""
from __future__ import annotations

__all__: list[str] = [
    "AbstractParser",
    "Argument",
    "ConverterSig",
    "Option",
    "Parameter",
    "ParseableProto",
    "ParseableProtoT",
    "ShlexParser",
    "UndefinedDefaultT",
    "UNDEFINED_DEFAULT",
    "with_argument",
    "with_greedy_argument",
    "with_multi_argument",
    "with_option",
    "with_multi_option",
    "with_parser",
]

import abc
import asyncio
import copy
import itertools
import shlex
import typing
from collections import abc as collections

from . import abc as tanjun_abc
from . import conversion
from . import errors

if typing.TYPE_CHECKING:
    _ParameterT = typing.TypeVar("_ParameterT", bound="Parameter")
    _ShlexParserT = typing.TypeVar("_ShlexParserT", bound="ShlexParser")
    _T = typing.TypeVar("_T")


ParseableProtoT = typing.TypeVar("ParseableProtoT", bound="ParseableProto")
"""Generic type hint of `ParseableProto`."""

ConverterSig = collections.Callable[..., tanjun_abc.MaybeAwaitableT[typing.Any]]
"""Type hint of a converter used within a parser instance.

This must be a callable or asynchronous callable which takes one position
`str`, argument and returns the resultant value.
"""


@typing.runtime_checkable
class ParseableProto(typing.Protocol):
    """Protocol of a command which supports this parser interface."""

    # This fucks with MyPy even though at runtime python just straight out ignores slots when considering protocol
    if not typing.TYPE_CHECKING:  # compatibility.
        __slots__ = ()

    @property
    def callback(self) -> tanjun_abc.CommandCallbackSig:
        raise NotImplementedError

    @property
    def parser(self) -> typing.Optional[AbstractParser]:
        raise NotImplementedError

    def set_parser(self: _T, _: typing.Optional[AbstractParser], /) -> _T:
        raise NotImplementedError


class UndefinedDefaultT:
    """Type of the singleton value used for indicating an empty default."""

    __singleton: typing.Optional[UndefinedDefaultT] = None

    def __new__(cls) -> UndefinedDefaultT:
        if cls.__singleton is None:
            cls.__singleton = super().__new__(cls)
            assert isinstance(cls.__singleton, UndefinedDefaultT)

        return cls.__singleton

    def __repr__(self) -> str:
        return "UNDEFINED_DEFAULT"

    def __bool__(self) -> typing.Literal[False]:
        return False


UNDEFINED_DEFAULT = UndefinedDefaultT()
"""A singleton used to represent no default for a parameter."""


class AbstractParser(abc.ABC):
    """Abstract interface of a message content parser."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def parameters(self) -> collections.Sequence[Parameter]:
        raise NotImplementedError

    @abc.abstractmethod  # TODO: these lol
    def add_parameter(self: _T, parameter: typing.Union[Argument, Option], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def remove_parameter(self: _T, parameter: typing.Union[Argument, Option], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def set_parameters(self: _T, parameters: collections.Iterable[typing.Union[Argument, Option]], /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_client(self: _T, client: tanjun_abc.Client, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def bind_component(self: _T, component: tanjun_abc.Component, /) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    def copy(self: _T) -> _T:
        raise NotImplementedError

    @abc.abstractmethod
    async def parse(self, ctx: tanjun_abc.MessageContext, /) -> tuple[list[typing.Any], dict[str, typing.Any]]:
        raise NotImplementedError


class ShlexTokenizer:
    __slots__ = ("__arg_buffer", "__last_name", "__options_buffer", "__shlex")

    def __init__(self, content: str, /) -> None:
        self.__arg_buffer: list[str] = []
        self.__last_name: typing.Optional[str] = None
        self.__options_buffer: list[tuple[str, typing.Optional[str]]] = []
        self.__shlex = shlex.shlex(content, posix=True)
        self.__shlex.whitespace = " "
        self.__shlex.whitespace_split = True

    def collect_raw_options(self) -> collections.Mapping[str, collections.Sequence[typing.Optional[str]]]:
        results: dict[str, list[typing.Optional[str]]] = {}

        while (option := self.next_raw_option()) is not None:
            name, value = option

            if name not in results:
                results[name] = []

            results[name].append(value)

        return results

    def iter_raw_arguments(self) -> collections.Iterator[str]:
        while (argument := self.next_raw_argument()) is not None:
            yield argument

    def next_raw_argument(self) -> typing.Optional[str]:
        if self.__arg_buffer:
            return self.__arg_buffer.pop(0)

        # TODO: this is probably slow
        while isinstance(value := self.__seek_shlex(), tuple):
            self.__options_buffer.append(value)

        return value

    def next_raw_option(self) -> typing.Optional[tuple[str, typing.Optional[str]]]:
        if self.__options_buffer:
            return self.__options_buffer.pop(0)

        # TODO: this is probably slow
        while isinstance(value := self.__seek_shlex(), str):
            self.__arg_buffer.append(value)

        return value

    def __seek_shlex(self) -> typing.Union[str, tuple[str, typing.Optional[str]], None]:
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
    ctx: tanjun_abc.MessageContext, option: Option, value: typing.Optional[typing.Any], /
) -> typing.Any:
    if value is not None:
        return await option.convert(ctx, value)

    if option.empty_value is not UNDEFINED_DEFAULT:
        return option.empty_value

    raise errors.NotEnoughArgumentsError(f"Option '{option.key} cannot be empty.", option.key)


class SemanticShlex(ShlexTokenizer):
    __slots__ = ("__ctx",)

    def __init__(self, ctx: tanjun_abc.MessageContext, /) -> None:
        super().__init__(ctx.content)
        self.__ctx = ctx

    async def get_arguments(self, arguments: collections.Sequence[Argument], /) -> list[typing.Any]:
        results: list[typing.Any] = []
        for argument in arguments:
            results.append(await self.__process_argument(argument))

            if argument.is_greedy or argument.is_multi:
                break  # Multi and Greedy parameters should always be the last parameter.

        return results

    async def get_options(self, options: collections.Sequence[Option], /) -> dict[str, typing.Any]:
        raw_options = self.collect_raw_options()
        results = asyncio.gather(*map(lambda option: self.__process_option(option, raw_options), options))
        return dict(zip((option.key for option in options), await results))

    async def __process_argument(self, argument: Parameter) -> typing.Any:
        if argument.is_greedy and (value := " ".join(self.iter_raw_arguments())):
            return await argument.convert(self.__ctx, value)

        if argument.is_multi and (values := list(self.iter_raw_arguments())):
            return await asyncio.gather(*(argument.convert(self.__ctx, value) for value in values))

        # If the previous two statements failed on getting raw arguments then this will as well.
        if (optional_value := self.next_raw_argument()) is not None:
            return await argument.convert(self.__ctx, optional_value)

        if argument.default is not UNDEFINED_DEFAULT:
            return argument.default

        # If this is reached then no value was found.
        raise errors.NotEnoughArgumentsError(f"Missing value for required argument '{argument.key}'", argument.key)

    async def __process_option(
        self, option: Option, raw_options: collections.Mapping[str, collections.Sequence[typing.Optional[str]]]
    ) -> typing.Any:
        values_iter = itertools.chain.from_iterable(raw_options[name] for name in option.names if name in raw_options)
        if option.is_multi and (values := list(values_iter)):
            return await asyncio.gather(*(_covert_option_or_empty(self.__ctx, option, value) for value in values))

        if not option.is_multi and (value := next(values_iter, ...)) is not ...:
            if next(values_iter, ...) is not ...:
                raise errors.TooManyArgumentsError(f"Option `{option.key}` can only take a single value", option.key)

            return await _covert_option_or_empty(self.__ctx, option, value)

        if option.default is not UNDEFINED_DEFAULT:
            return option.default

        # If this is reached then no value was found.
        raise errors.NotEnoughArgumentsError(f"Missing required option `{option.key}`", option.key)


def with_argument(
    key: str,
    /,
    converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
    *,
    default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
    greedy: bool = False,
    multi: bool = False,
) -> collections.Callable[[ParseableProtoT], ParseableProtoT]:
    """Add an argument to a parsable command through a decorator call.

    .. note::
        Order matters for positional arguments and since decorator execution
        starts at the decorator closest to the command and goes upwards this
        will decide where a positional argument is located in a command's
        signature.

    Parameters
    ----------
    key : str
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's callback during execution).
    converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    default : typing.Any
        The default value of this argument, if left as
        `UNDEFINED_DEFAULT` then this will have no default.
    greedy : bool
        Whether or not this argument should be greedy (meaning that it
        takes in the remaining argument values).
    multi : bool
        Whether this argument can be passed multiple times.

    Returns
    -------
    collections.abc.Callable[[ParseableProtoT], ParseableProtoT]:
        Decorator function for the parsable command this argument is being added to.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_argument("command", converters=int, default=42)
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.abc.Context, /, argument: int):
        ...
    ```
    """

    def decorator(command: ParseableProtoT, /) -> ParseableProtoT:
        if command.parser is None:
            raise ValueError("Cannot add a parameter to a command client without a parser.")

        argument = Argument(key, converters=converters, default=default, greedy=greedy, multi=multi)
        command.parser.add_parameter(argument)
        return command

    return decorator


def with_greedy_argument(
    key: str,
    /,
    converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
    *,
    default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
) -> collections.Callable[[ParseableProtoT], ParseableProtoT]:
    """Add a greedy argument to a parsable command through a decorator call.

    Notes
    -----
    * A greedy argument will consume the remaining positional arguments and pass
      them through to the converters as one joined string while also requiring
      that at least one more positional argument is remaining unless a
      default is set.
    * Order matters for positional arguments and since decorator execution
      starts at the decorator closest to the command and goes upwards this
      will decide where a positional argument is located in a command's
      signature.

    Parameters
    ----------
    key : str
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's callback during execution).

    Other Parameters
    ----------------
    converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    default : typing.Any
        The default value of this argument, if left as
        `UNDEFINED_DEFAULT` then this will have no default.

    Returns
    -------
    collections.abc.Callable[[ParseableProtoT], ParseableProtoT]:
        Decorator function for the parsable command this argument is being added to.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_greedy_argument("command", converters=StringView)
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.abc.Context, /, argument: StringView):
        ...
    ```
    """
    return with_argument(key, converters=converters, default=default, greedy=True)


def with_multi_argument(
    key: str,
    /,
    converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
    *,
    default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
) -> collections.Callable[[ParseableProtoT], ParseableProtoT]:
    """Add a multi-argument to a parsable command through a decorator call.

    Notes
    -----
    * A multi argument will consume the remaining positional arguments and pass
      them to the converters through multiple calls while also requiring that
      at least one more positional argument is remaining unless a default is
      set and passing through the results to the command's callback as a
      sequence.
    * Order matters for positional arguments and since decorator execution
      starts at the decorator closest to the command and goes upwards this
      will decide where a positional argument is located in a command's
      signature.

    Parameters
    ----------
    key : str
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's callback during execution).

    Other Parameters
    ----------------
    converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    default : typing.Any
        The default value of this argument, if left as
        `UNDEFINED_DEFAULT` then this will have no default.

    Returns
    -------
    collections.abc.Callable[[ParseableProtoT], ParseableProtoT]:
        Decorator function for the parsable command this argument is being added to.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_multi_argument("command", converters=int)
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.abc.Context, /, argument: collections.abc.Sequence[int]):
        ...
    ```
    """
    return with_argument(key, converters=converters, default=default, multi=True)


# TODO: add default getter
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
    default: typing.Any,
    empty_value: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
    multi: bool = False,
) -> collections.Callable[[ParseableProtoT], ParseableProtoT]:
    """Add an option to a parsable command through a decorator call.

    Parameters
    ----------
    key : str
        The string identifier of this option which will be used to pass the
        result of this argument to the command's callback during execution as
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
    converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    empty_value : typing.Any
        The value to use if this option is provided without a value. If left as
        `UNDEFINED_DEFAULT` then this option will error if it's
        provided without a value.
    multi : bool
        If this option can be provided multiple times.
        Defaults to `False`.

    Returns
    -------
    collections.abc.Callable[[ParseableProtoT], ParseableProtoT]:
        Decorator function for the parsable command this option is being added to.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_option("command", converters=int, default=42)
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.abc.Context, /, argument: int):
        ...
    ```
    """

    def decorator(command: ParseableProtoT) -> ParseableProtoT:
        if command.parser is None:
            raise ValueError("Cannot add an option to a command client without a parser.")

        option = Option(key, name, *names, converters=converters, default=default, empty_value=empty_value, multi=multi)
        command.parser.add_parameter(option)
        return command

    return decorator


def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
    default: typing.Any,
    empty_value: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
) -> collections.Callable[[ParseableProtoT], ParseableProtoT]:
    """Add an multi-option to a command's parser through a decorator call.

    .. note::
        A multi option will consume all the values provided for an option and
        pass them through to the converters as an array of strings while also
        requiring that at least one value is provided for the option unless
        a default is set.

    Parameters
    ----------
    key : str
        The string identifier of this option which will be used to pass the
        result of this argument to the command's callback during execution as
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
    converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    empty_value : typing.Any
        The value to use if this option is provided without a value. If left as
        `UNDEFINED_DEFAULT` then this option will error if it's
        provided without a value.

    Returns
    -------
    collections.abc.Callable[[ParseableProtoT], ParseableProtoT]:
        Decorator function for the parsable command this option is being added to.

    Examples
    --------
    ```python
    import tanjun

    @tanjun.parsing.with_multi_option("command", converters=int, default=())
    @tanjun.parsing.with_parser
    @tanjun.component.as_message_command("command")
    async def command(self, ctx: tanjun.abc.Context, /, argument: collections.abc.Sequence[int]):
        ...
    ```
    """
    return with_option(key, name, *names, converters=converters, default=default, empty_value=empty_value, multi=True)


class Parameter:
    __slots__ = ("_client", "_component", "_converters", "default", "is_greedy", "is_multi", "_key")

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
        greedy: bool = False,
        multi: bool = False,
    ) -> None:
        self._client: typing.Optional[tanjun_abc.Client] = None
        self._component: typing.Optional[tanjun_abc.Component] = None
        self._converters: list[conversion.InjectableConverter[typing.Any]] = []
        self.default = default
        self.is_greedy = greedy
        self.is_multi = multi
        self._key = key

        if key.startswith("-"):
            raise ValueError("parameter key cannot start with `-`")

        if isinstance(converters, collections.Iterable):
            for converter in converters:
                self._add_converter(converter)

        else:
            self._add_converter(converters)

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self._key}>"

    @property
    def converters(self) -> collections.Sequence[ConverterSig]:
        return tuple(converter.callback for converter in self._converters)

    @property
    def key(self) -> str:
        return self._key

    @property
    def needs_injector(self) -> bool:
        # TODO: cache this value?
        return any(converter.needs_injector for converter in self._converters)

    def _add_converter(self, converter: ConverterSig, /) -> None:
        if isinstance(converter, conversion.BaseConverter):
            if self._client:
                converter.check_client(self._client, f"{self._key} parameter")

        if not isinstance(converter, conversion.InjectableConverter):
            # Some types like `bool` and `bytes` are overridden here for the sake of convenience.
            converter = conversion.override_type(converter)
            converter = conversion.InjectableConverter(converter)

        self._converters.append(converter)

    def bind_client(self, client: tanjun_abc.Client, /) -> None:
        self._client = client
        for converter in self._converters:
            if isinstance(converter.callback, conversion.BaseConverter):
                converter.callback.check_client(client, f"{self._key} parameter")

    def bind_component(self, component: tanjun_abc.Component, /) -> None:
        self._component = component

    async def convert(self, ctx: tanjun_abc.Context, value: str) -> typing.Any:
        if not self._converters:
            return value

        sources: list[ValueError] = []
        for converter in self._converters:
            try:
                return await converter(ctx, value)

            except ValueError as exc:
                sources.append(exc)

        parameter_type = "option" if isinstance(self, Option) else "argument"
        raise errors.ConversionError(f"Couldn't convert {parameter_type} '{self.key}'", self.key, sources)

    def copy(self: _ParameterT, *, _new: bool = True) -> _ParameterT:
        if not _new:
            self._converters = [converter.copy() for converter in self._converters]
            return self

        result = copy.copy(self).copy(_new=False)
        return result


class Argument(Parameter):
    __slots__ = ()

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
        greedy: bool = False,
        multi: bool = False,
    ) -> None:
        if greedy and multi:
            raise ValueError("Argument cannot be both greed and multi.")

        super().__init__(key, converters=converters, default=default, greedy=greedy, multi=multi)


class Option(Parameter):
    __slots__ = ("_empty_value", "is_multi", "_names")

    def __init__(
        self,
        key: str,
        name: str,
        *names: str,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
        empty_value: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
        multi: bool = True,
    ) -> None:
        if not name.startswith("-") or not all(n.startswith("-") for n in names):
            raise ValueError("All option names must start with `-`")

        self._empty_value = empty_value
        self._names = [name, *names]
        super().__init__(key, converters=converters, default=default, multi=multi)

    @property
    def empty_value(self) -> typing.Union[typing.Any, UndefinedDefaultT]:
        return self._empty_value

    @property
    def names(self) -> collections.Sequence[str]:
        return self._names.copy()

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.key}, {self._names}>"


class ShlexParser(AbstractParser):
    """A shlex based `tanjun.abc.Parser` implementation."""

    __slots__ = ("_arguments", "_client", "_component", "_options")

    def __init__(
        self, *, parameters: typing.Optional[collections.Iterable[typing.Union[Argument, Option]]] = None
    ) -> None:
        self._arguments: list[Argument] = []
        self._client: typing.Optional[tanjun_abc.Client] = None
        self._component: typing.Optional[tanjun_abc.Component] = None
        self._options: list[Option] = []

        if parameters is not None:
            self.set_parameters(parameters)

    @property
    def needs_injector(self) -> bool:
        # TODO: cache this value?
        return any(parameter.needs_injector for parameter in itertools.chain(self._options, self._arguments))

    @property
    def parameters(self) -> collections.Sequence[Parameter]:
        # <<inherited docstring from AbstractParser>>.
        return (*self._arguments, *self._options)

    def copy(self: _ShlexParserT, *, _new: bool = True) -> _ShlexParserT:
        if not _new:
            self._arguments = [argument.copy() for argument in self._arguments]
            self._options = [option.copy() for option in self._options]
            return self

        return copy.copy(self).copy(_new=False)

    def add_parameter(self: _ShlexParserT, parameter: typing.Union[Argument, Option], /) -> _ShlexParserT:
        # <<inherited docstring from AbstractParser>>.
        if self._client:
            parameter.bind_client(self._client)

        if self._component:
            parameter.bind_component(self._component)

        if isinstance(parameter, Option):
            self._options.append(parameter)

        else:
            self._arguments.append(parameter)
            found_final_argument = False

            for argument in self._arguments:
                if found_final_argument:
                    del self._arguments[-1]
                    raise ValueError("Multi or greedy argument must be the last argument")

                found_final_argument = argument.is_multi or argument.is_greedy

        return self

    def remove_parameter(self: _ShlexParserT, parameter: typing.Union[Argument, Option], /) -> _ShlexParserT:
        # <<inherited docstring AbstractParser>>.
        if isinstance(parameter, Option):
            self._options.remove(parameter)

        else:
            self._arguments.remove(parameter)

        return self

    def add_argument(
        self: _ShlexParserT,
        key: str,
        /,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        *,
        default: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
        greedy: bool = False,
        multi: bool = False,
    ) -> _ShlexParserT:
        """Add an argument type parameter to the parser..

        .. note::
            Order matters for positional arguments.

        Parameters
        ----------
        key : str
            The string identifier of this argument (may be used to pass the result
            of this argument to the command's callback during execution).
        converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
            The converter(s) this argument should use to handle values passed to it
            during parsing.

            If no converters are provided then the raw string value will be passed.

            Only the first converter to pass will be used.
        default : typing.Any
            The default value of this argument, if left as
            `UNDEFINED_DEFAULT` then this will have no default.
        greedy : bool
            Whether or not this argument should be greedy (meaning that it
            takes in the remaining argument values).
        multi : bool
            Whether this argument can be passed multiple times.

        Returns
        -------
        SelfT
            This parser to enable chained calls.
        """
        return self.add_parameter(Argument(key, converters=converters, default=default, multi=multi, greedy=greedy))

    # TODO: add default getter
    def add_option(
        self: _ShlexParserT,
        key: str,
        name: str,
        /,
        *names: str,
        converters: typing.Union[collections.Iterable[ConverterSig], ConverterSig] = (),
        default: typing.Any,
        empty_value: typing.Union[typing.Any, UndefinedDefaultT] = UNDEFINED_DEFAULT,
        multi: bool = False,
    ) -> _ShlexParserT:
        """Add an option type parameter to this parser.

        Parameters
        ----------
        key : str
            The string identifier of this option which will be used to pass the
            result of this argument to the command's callback during execution as
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
        converters : typing.Union[ConverterSig, collections.abc.Iterable[ConverterSig]]
            The converter(s) this argument should use to handle values passed to it
            during parsing.

            If no converters are provided then the raw string value will be passed.

            Only the first converter to pass will be used.
        empty_value : typing.Any
            The value to use if this option is provided without a value. If left as
            `UNDEFINED_DEFAULT` then this option will error if it's
            provided without a value.
        multi : bool
            If this option can be provided multiple times.
            Defaults to `False`.

        Returns
        -------
        SelfT
            This parser to enable chained calls.
        """
        return self.add_parameter(
            Option(key, name, *names, converters=converters, default=default, empty_value=empty_value, multi=multi)
        )

    def set_parameters(
        self: _ShlexParserT, parameters: collections.Iterable[typing.Union[Argument, Option]], /
    ) -> _ShlexParserT:
        # <<inherited docstring from AbstractParser>>.
        self._arguments = []
        self._options = []

        for parameter in parameters:
            self.add_parameter(parameter)

        return self

    def bind_client(self, client: tanjun_abc.Client, /) -> None:
        # <<inherited docstring from AbstractParser>>.
        self._client = client
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_client(client)

    def bind_component(self, component: tanjun_abc.Component, /) -> None:
        # <<inherited docstring from AbstractParser>>.
        self._component = component
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_component(component)

    async def parse(self, ctx: tanjun_abc.MessageContext, /) -> tuple[list[typing.Any], dict[str, typing.Any]]:
        # <<inherited docstring from AbstractParser>>.
        parser = SemanticShlex(ctx)
        arguments = await parser.get_arguments(self._arguments)
        options = await parser.get_options(self._options)
        return arguments, options


def with_parser(command: ParseableProtoT, /) -> ParseableProtoT:
    """Add a shlex parser command parser to a supported command."""
    return command.set_parser(ShlexParser())
