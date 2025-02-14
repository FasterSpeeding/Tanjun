# BSD 3-Clause License
#
# Copyright (c) 2020-2025, Faster Speeding
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
    "AbstractOptionParser",
    "Argument",
    "ConverterSig",
    "Option",
    "Parameter",
    "ShlexParser",
    "with_argument",
    "with_greedy_argument",
    "with_multi_argument",
    "with_multi_option",
    "with_option",
    "with_parser",
]

import abc
import asyncio
import copy
import itertools
import shlex
import typing
from collections import abc as collections

import typing_extensions

from . import abc as tanjun
from . import conversion
from . import errors

if typing.TYPE_CHECKING:
    from typing import Self

    _CommandT = typing.TypeVar("_CommandT", bound=tanjun.MessageCommand[typing.Any])
    _T_contra = typing.TypeVar("_T_contra", contravariant=True)

    class _CmpProto(typing.Protocol[_T_contra]):
        def __gt__(self, other: _T_contra, /) -> bool:
            raise NotImplementedError

        def __lt__(self, other: _T_contra, /) -> bool:
            raise NotImplementedError

    class _SizedCmpProto(_CmpProto[_T_contra]):
        def __len__(self) -> int:
            raise NotImplementedError

    _CmpProtoT = typing.TypeVar("_CmpProtoT", bound=_CmpProto[typing.Any])
    # Pyright bug doesn't accept Var = Class | Class as a type
    _MaybeIterable = typing.Union[collections.Iterable["_T"], "_T"]  # noqa: UP007
    _SizedCmpProtoT = typing.TypeVar("_SizedCmpProtoT", bound=_SizedCmpProto[typing.Any])


_T = typing.TypeVar("_T")

ConverterSig = collections.Callable[
    typing.Concatenate[str, ...], collections.Coroutine[typing.Any, typing.Any, _T] | _T
]
"""Type hint of a converter used within a parser instance.

This represents the signatures `def (str, ...) -> Any` and
`async def (str, ...) -> Any` where dependency injection is supported.
"""

UndefinedT = tanjun.NoDefault
"""Deprecated alias of `typing.Literal[tanjun.abc.NO_DEFAULT]`."""

UndefinedDefaultT = UndefinedT
"""Deprecated alias of `typing.Literal[tanjun.abc.NO_DEFAULT]`."""

UNDEFINED = tanjun.NO_DEFAULT
"""Deprecated alias of [tanjun.abc.NO_DEFAULT][]."""

UNDEFINED_DEFAULT = tanjun.NO_DEFAULT
"""Deprecated alias of [tanjun.abc.NO_DEFAULT][]."""


class AbstractOptionParser(tanjun.MessageParser, abc.ABC):
    """Abstract interface of a message content parser."""

    __slots__ = ()

    @property
    @abc.abstractmethod
    def arguments(self) -> collections.Sequence[Argument]:
        """Sequence of the positional arguments registered with this parser."""

    @property
    @abc.abstractmethod
    def options(self) -> collections.Sequence[Option]:
        """Sequence of the named options registered with this parser."""

    @typing.overload
    @abc.abstractmethod
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[typing.Any]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[str]] = (),
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[str] | None = None,
        max_value: _CmpProto[str] | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _SizedCmpProtoT | None = None,
        max_value: _SizedCmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[collections.Sized]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_value: _CmpProtoT | None = None,
        max_value: _CmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    @abc.abstractmethod
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: typing.Any | None = None,
        max_value: typing.Any | None = None,
        multi: bool = False,
    ) -> Self:
        """Add a positional argument type to the parser..

        !!! note
            Order matters for positional arguments.

        Parameters
        ----------
        key
            The string identifier of this argument (may be used to pass the result
            of this argument to the command's callback during execution).
        converters
            The converter(s) this argument should use to handle values passed to it
            during parsing.

            If no converters are provided then the raw string value will be passed.

            Only the first converter to pass will be used.
        default
            The default value of this argument, if left as
            [tanjun.abc.NO_DEFAULT][] then this will have no default.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
        greedy
            Whether or not this argument should be greedy (meaning that it
            takes in the remaining argument values).
        min_length
            Assert that a string argument's length is greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_length
            Assert that a string argument's length is less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        min_value
            Assert that the parsed value(s) for this argument are greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_value
            Assert that the parsed value(s) for this argument are less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        multi
            Whether this argument can be passed multiple times.

        Returns
        -------
        Self
            This parser to enable chained calls.

        Raises
        ------
        ValueError
            If `key` isn't valid for any of the commands this parser is linked
            to where `validate_arg_keys` is [True][].
        """

    @typing.overload
    @abc.abstractmethod
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[typing.Any]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[str]] = (),
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[str] | None = None,
        max_value: _CmpProto[str] | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _SizedCmpProtoT | None = None,
        max_value: _SizedCmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[collections.Sized]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    @abc.abstractmethod
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_value: _CmpProtoT | None = None,
        max_value: _CmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    @abc.abstractmethod
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: typing.Any | None = None,
        max_value: typing.Any | None = None,
        multi: bool = False,
    ) -> Self:
        """Add an named option to this parser.

        Parameters
        ----------
        key
            The string identifier of this option which will be used to pass the
            result of this option to the command's callback during execution as
            a keyword argument.
        name
            The name of this option used for identifying it in the parsed content.
        *names
            Other names of this option used for identifying it in the parsed content.
        default
            The default value of this option, unlike arguments this is required
            for options.
        converters
            The converter(s) this option should use to handle values passed to it
            during parsing.

            If no converters are provided then the raw string value will be passed.

            Only the first converter to pass will be used.
        empty_value
            The value to use if this option is provided without a value.

            If left as [tanjun.abc.NO_DEFAULT][] then this option
            will error if it's provided without a value.

            [tanjun.abc.NO_PASS][] is not supported for this.
        min_length
            Assert that a string argument's length is greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_length
            Assert that a string argument's length is less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        min_value
            Assert that the parsed value(s) for this option are greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_value
            Assert that the parsed value(s) for this option are less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        multi
            If this option can be provided multiple times.

        Returns
        -------
        Self
            This parser to enable chained calls.

        Raises
        ------
        ValueError
            If `key` isn't valid for any of the commands this parser is linked
            to where `validate_arg_keys` is [True][].
        """


@typing_extensions.deprecated("Use AbstractOptionParser")
class AbstractParser(AbstractOptionParser):
    """Deprecated alias of [AbstractOptionParser][tanjun.parsing.AbstractOptionParser]."""

    __slots__ = ()


class _ShlexTokenizer:
    __slots__ = ("__arg_buffer", "__last_name", "__options_buffer", "__shlex")

    def __init__(self, content: str, /) -> None:
        self.__arg_buffer: list[str] = []
        self.__last_name: str | None = None
        self.__options_buffer: list[tuple[str, str | None]] = []
        self.__shlex = shlex.shlex(content, posix=True)
        self.__shlex.commenters = ""
        self.__shlex.quotes = '"'
        self.__shlex.whitespace = " "
        self.__shlex.whitespace_split = True

    def collect_raw_options(self) -> collections.Mapping[str, collections.Sequence[str | None]]:
        results: dict[str, list[str | None]] = {}

        while (option := self.next_raw_option()) is not None:
            name, value = option

            if name not in results:
                results[name] = []

            results[name].append(value)

        return results

    def iter_raw_arguments(self) -> collections.Iterator[str]:
        while (argument := self.next_raw_argument()) is not None:
            yield argument

    def next_raw_argument(self) -> str | None:
        if self.__arg_buffer:
            return self.__arg_buffer.pop(0)

        while (value := self.__seek_shlex()) and value[0] == 1:
            self.__options_buffer.append(value[1])

        return value[1] if value else None

    def next_raw_option(self) -> tuple[str, str | None] | None:
        if self.__options_buffer:
            return self.__options_buffer.pop(0)

        while (value := self.__seek_shlex()) and value[0] == 0:
            self.__arg_buffer.append(value[1])

        return value[1] if value else None

    def __seek_shlex(self) -> tuple[typing.Literal[0], str] | tuple[typing.Literal[1], tuple[str, str | None]] | None:
        option_name = self.__last_name

        try:
            value = next(self.__shlex)

        except StopIteration:
            if option_name is not None:
                self.__last_name = None
                return (1, (option_name, None))

            return None

        except ValueError as exc:
            raise errors.ParserError(str(exc), None) from exc

        is_option = value.startswith("-")
        if is_option and option_name is not None:
            self.__last_name = value
            return (1, (option_name, None))

        if is_option:
            self.__last_name = value
            return self.__seek_shlex()

        if option_name:
            self.__last_name = None
            return (1, (option_name, value))

        return (0, value)


async def _covert_option_or_empty(
    ctx: tanjun.MessageContext, option: Option, value: typing.Any | None, /
) -> typing.Any:
    if value is not None:
        return await option.convert(ctx, value)

    if option.empty_value is not tanjun.NO_DEFAULT:
        return option.empty_value

    error_message = f"Option '{option.key} cannot be empty."
    raise errors.NotEnoughArgumentsError(error_message, option.key)


class _SemanticShlex(_ShlexTokenizer):
    __slots__ = ("__arguments", "__ctx", "__options")

    def __init__(
        self,
        ctx: tanjun.MessageContext,
        arguments: collections.Sequence[Argument],
        options: collections.Sequence[Option],
        /,
    ) -> None:
        super().__init__(ctx.content)
        self.__arguments = arguments
        self.__ctx = ctx
        self.__options = options

    async def parse(self) -> dict[str, typing.Any]:
        raw_options = self.collect_raw_options()
        kwargs: dict[str, typing.Any] = {}

        for option in self.__options:
            values_iter = itertools.chain.from_iterable(
                raw_options[name] for name in option.names if name in raw_options
            )
            if option.is_multi and (values := list(values_iter)):
                kwargs[option.key] = await asyncio.gather(
                    *(_covert_option_or_empty(self.__ctx, option, value) for value in values)
                )

            elif not option.is_multi and (value := next(values_iter, ...)) is not ...:
                if next(values_iter, ...) is not ...:
                    error_message = f"Option `{option.key}` can only take a single value"
                    raise errors.TooManyArgumentsError(error_message, option.key)

                kwargs[option.key] = await _covert_option_or_empty(self.__ctx, option, value)

            elif option.default is tanjun.NO_DEFAULT:
                # If this is reached then no value was found.
                error_message = f"Missing required option `{option.key}`"
                raise errors.NotEnoughArgumentsError(error_message, option.key)

            elif option.default is not tanjun.NO_PASS:
                kwargs[option.key] = option.default

        for argument in self.__arguments:
            if argument.is_greedy and (value := " ".join(self.iter_raw_arguments())):
                kwargs[argument.key] = await argument.convert(self.__ctx, value)

            elif argument.is_multi and (values := list(self.iter_raw_arguments())):
                kwargs[argument.key] = await asyncio.gather(*(argument.convert(self.__ctx, value) for value in values))

            # If the previous two statements failed on getting raw arguments then this will as well.
            elif (optional_value := self.next_raw_argument()) is not None:
                kwargs[argument.key] = await argument.convert(self.__ctx, optional_value)

            elif argument.default is tanjun.NO_DEFAULT:
                # If this is reached then no value was found.
                error_message = f"Missing value for required argument '{argument.key}'"
                raise errors.NotEnoughArgumentsError(error_message, argument.key)

            elif argument.default is not tanjun.NO_PASS:
                kwargs[argument.key] = argument.default

            if argument.is_greedy or argument.is_multi:
                break  # Multi and Greedy parameters should always be the last parameter.

        return kwargs


def _get_or_set_parser(command: tanjun.MessageCommand[typing.Any], /) -> AbstractOptionParser:
    if not command.parser:
        parser = ShlexParser()
        command.set_parser(parser)
        return parser

    if isinstance(command.parser, AbstractOptionParser):
        return command.parser

    error_message = "Expected parser to be an instance of tanjun.parsing.AbstractOptionParser"
    raise TypeError(error_message)


@typing.overload
def with_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[typing.Any]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    greedy: bool = False,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[str]] = (),
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    greedy: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _CmpProto[str] | None = None,
    max_value: _CmpProto[str] | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    greedy: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _SizedCmpProtoT | None = None,
    max_value: _SizedCmpProtoT | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[collections.Sized]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    greedy: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    greedy: bool = False,
    min_value: _CmpProtoT | None = None,
    max_value: _CmpProtoT | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


def with_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    greedy: bool = False,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: typing.Any | None = None,
    max_value: typing.Any | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add an argument to a message command through a decorator call.

    !!! warning
        Since order matters for positional arguments, you'll want to keep in
        mind that decorator execution starts at the decorator closest to the
        command and goes upwards with this deciding where a positional
        argument is located in a command's signature.

    !!! note
        If no parser is explicitly set on the command this is decorating before
        this decorator call then this will set
        [ShlexParser][tanjun.parsing.ShlexParser] as the parser.

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

    Parameters
    ----------
    key
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's callback during execution).
    converters
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    default
        The default value of this argument, if left as
        [tanjun.abc.NO_DEFAULT][] then this will have no default.

        If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
        passed when no value was provided.
    greedy
        Whether or not this argument should be greedy (meaning that it
        takes in the remaining argument values).
    min_length
        Assert that a string argument's length is greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_length
        Assert that a string argument's length is less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    min_value
        Assert that the parsed value(s) for this argument are greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_value
        Assert that the parsed value(s) for this argument are less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.

    multi
        Whether this argument can be passed multiple times.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCommand], tanjun.abc.MessageCommand]:
        Decorator function for the message command this argument is being added to.

    Raises
    ------
    ValueError
        If `key` isn't valid for any of the commands this command's parser is
        linked to where `validate_arg_keys` is [True][].
    """

    def decorator(command: _CommandT, /) -> _CommandT:
        _get_or_set_parser(command).add_argument(
            key,
            converters=converters,
            default=default,
            greedy=greedy,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            multi=multi,
        )
        return command

    return decorator


@typing.overload
def with_greedy_argument(
    key: str, /, converters: _MaybeIterable[ConverterSig[typing.Any]], *, default: typing.Any = tanjun.NO_DEFAULT
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_greedy_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[str]] = (),
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _CmpProto[str] | None = None,
    max_value: _CmpProto[str] | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_greedy_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _SizedCmpProtoT | None = None,
    max_value: _SizedCmpProtoT | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_greedy_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[collections.Sized]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_greedy_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_value: _CmpProtoT | None = None,
    max_value: _CmpProtoT | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


def with_greedy_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: typing.Any | None = None,
    max_value: typing.Any | None = None,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a greedy argument to a message command through a decorator call.

    A greedy argument will consume the remaining positional arguments and pass
    them through to the converters as one joined string while also requiring
    that at least one more positional argument is remaining unless a default is
    set.

    !!! warning
        Since order matters for positional arguments, you'll want to keep in
        mind that decorator execution starts at the decorator closest to the
        command and goes upwards with this deciding where a positional
        argument is located in a command's signature.

    !!! note
        If no parser is explicitly set on the command this is decorating before
        this decorator call then this will set
        [ShlexParser][tanjun.parsing.ShlexParser] as the parser.

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

    Parameters
    ----------
    key
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's callback during execution).
    converters
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    default
        The default value of this argument, if left as
        [tanjun.abc.NO_DEFAULT][] then this will have no default.

        If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
        passed when no value was provided.

        If any converters are provided then this should be compatible
        with the result of them.
    min_length
        Assert that a string argument's length is greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_length
        Assert that a string argument's length is less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    min_value
        Assert that the parsed value(s) for this argument are greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_value
        Assert that the parsed value(s) for this argument are less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCommand], tanjun.abc.MessageCommand]:
        Decorator function for the message command this argument is being added to.

    Raises
    ------
    ValueError
        If `key` isn't valid for any of the commands this command's parser is
        linked to where `validate_arg_keys` is [True][].
    """
    return with_argument(
        key,
        converters=converters,
        default=default,
        greedy=True,
        min_length=min_length,
        max_length=max_length,
        min_value=min_value,
        max_value=max_value,
    )


@typing.overload
def with_multi_argument(
    key: str, /, converters: _MaybeIterable[ConverterSig[typing.Any]], *, default: typing.Any = tanjun.NO_DEFAULT
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[str]] = (),
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _CmpProto[str] | None = None,
    max_value: _CmpProto[str] | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _SizedCmpProtoT | None = None,
    max_value: _SizedCmpProtoT | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[collections.Sized]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_value: _CmpProtoT | None = None,
    max_value: _CmpProtoT | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


def with_multi_argument(
    key: str,
    /,
    converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
    *,
    default: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: typing.Any | None = None,
    max_value: typing.Any | None = None,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add a multi-argument to a message command through a decorator call.

    A multi argument will consume the remaining positional arguments and pass
    them to the converters through multiple calls while also requiring that
    at least one more positional argument is remaining unless a default is
    set and passing through the results to the command's callback as a
    sequence.

    !!! warning
        Since order matters for positional arguments, you'll want to keep in
        mind that decorator execution starts at the decorator closest to the
        command and goes upwards with this deciding where a positional
        argument is located in a command's signature.

    !!! note
        If no parser is explicitly set on the command this is decorating before
        this decorator call then this will set
        [ShlexParser][tanjun.parsing.ShlexParser] as the parser.

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

    Parameters
    ----------
    key
        The string identifier of this argument (may be used to pass the result
        of this argument to the command's callback during execution).
    converters
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    default
        The default value of this argument, if left as
        [tanjun.abc.NO_DEFAULT][] then this will have no default.

        If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
        passed when no value was provided.
    min_length
        Assert that a string argument's length is greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_length
        Assert that a string argument's length is less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    min_value
        Assert that the parsed value(s) for this argument are greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_value
        Assert that the parsed value(s) for this argument are less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCommand], tanjun.abc.MessageCommand]:
        Decorator function for the message command this argument is being added to.

    Raises
    ------
    ValueError
        If `key` isn't valid for any of the commands this command's parser is
        linked to where `validate_arg_keys` is [True][].
    """
    return with_argument(
        key,
        converters=converters,
        default=default,
        min_length=min_length,
        max_length=max_length,
        min_value=min_value,
        max_value=max_value,
        multi=True,
    )


@typing.overload
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[typing.Any]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[str]] = (),
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _CmpProto[str] | None = None,
    max_value: _CmpProto[str] | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _SizedCmpProtoT | None = None,
    max_value: _SizedCmpProtoT | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[collections.Sized]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_value: _CmpProtoT | None = None,
    max_value: _CmpProtoT | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]: ...


# TODO: add default getter
def with_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: typing.Any | None = None,
    max_value: typing.Any | None = None,
    multi: bool = False,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add an option to a message command through a decorator call.

    !!! note
        If no parser is explicitly set on the command this is decorating before
        this decorator call then this will set
        [ShlexParser][tanjun.parsing.ShlexParser] as the parser.

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

    Parameters
    ----------
    key
        The string identifier of this option which will be used to pass the
        result of this argument to the command's callback during execution as
        a keyword argument.
    name
        The name of this option used for identifying it in the parsed content.
    *names
        Other names of this option used for identifying it in the parsed content.
    default
        The default value of this argument, unlike arguments this is required
        for options.
    converters
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    empty_value
        The value to use if this option is provided without a value.

        If left as [tanjun.abc.NO_DEFAULT][] then this option will error if
        it's provided without a value.

        [tanjun.abc.NO_PASS][] is not supported for this.
    min_length
        Assert that a string argument's length is greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_length
        Assert that a string argument's length is less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    min_value
        Assert that the parsed value(s) for this option are greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_value
        Assert that the parsed value(s) for this option are less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    multi
        If this option can be provided multiple times.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCommand], tanjun.abc.MessageCommand]:
        Decorator function for the message command this option is being added to.

    Raises
    ------
    ValueError
        If `key` isn't valid for any of the commands this command's parser is
        linked to where `validate_arg_keys` is [True][].
    """

    def decorator(command: _CommandT, /) -> _CommandT:
        _get_or_set_parser(command).add_option(
            key,
            name,
            *names,
            converters=converters,
            default=default,
            empty_value=empty_value,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            multi=multi,
        )
        return command

    return decorator


@typing.overload
def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[typing.Any]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[str]] = (),
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _CmpProto[str] | None = None,
    max_value: _CmpProto[str] | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: _SizedCmpProtoT | None = None,
    max_value: _SizedCmpProtoT | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[collections.Sized]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


@typing.overload
def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_value: _CmpProtoT | None = None,
    max_value: _CmpProtoT | None = None,
) -> collections.Callable[[_CommandT], _CommandT]: ...


def with_multi_option(
    key: str,
    name: str,
    /,
    *names: str,
    converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
    default: typing.Any,
    empty_value: typing.Any = tanjun.NO_DEFAULT,
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: typing.Any | None = None,
    max_value: typing.Any | None = None,
) -> collections.Callable[[_CommandT], _CommandT]:
    """Add an multi-option to a command's parser through a decorator call.

    A multi option will consume all the values provided for an option and
    pass them through to the converters as an array of strings while also
    requiring that at least one value is provided for the option unless
    a default is set.

    !!! note
        If no parser is explicitly set on the command this is decorating before
        this decorator call then this will set
        [ShlexParser][tanjun.parsing.ShlexParser] as the parser.

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

    Parameters
    ----------
    key
        The string identifier of this option which will be used to pass the
        result of this argument to the command's callback during execution as
        a keyword argument.
    name
        The name of this option used for identifying it in the parsed content.
    *names
        Other names of this option used for identifying it in the parsed content.
    default
        The default value of this argument, unlike arguments this is required
        for options.
    converters
        The converter(s) this argument should use to handle values passed to it
        during parsing.

        If no converters are provided then the raw string value will be passed.

        Only the first converter to pass will be used.
    empty_value
        The value to use if this option is provided without a value.

        If left as [tanjun.abc.NO_DEFAULT][] then this option will error if
        it's provided without a value.

        [tanjun.abc.NO_PASS][] is not supported for this.
    min_length
        Assert that a string argument's length is greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_length
        Assert that a string argument's length is less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    min_value
        Assert that the parsed value(s) for this option are greater than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.
    max_value
        Assert that the parsed value(s) for this option are less than or equal to this.

        If any converters are provided then this should be compatible
        with the result of them.

    Returns
    -------
    collections.abc.Callable[[tanjun.abc.MessageCommand], tanjun.abc.MessageCommand]:
        Decorator function for the message command this option is being added to.

    Raises
    ------
    ValueError
        If `key` isn't valid for any of the commands this command's parser is
        linked to where `validate_arg_keys` is [True][].
    """
    return with_option(
        key,
        name,
        *names,
        converters=converters,
        default=default,
        empty_value=empty_value,
        min_length=min_length,
        max_length=max_length,
        min_value=min_value,
        max_value=max_value,
        multi=True,
    )


class Parameter:
    """Base class for parameters for the standard parser(s)."""

    __slots__ = (
        "_client",
        "_component",
        "_converters",
        "_default",
        "_is_multi",
        "_key",
        "_max_length",
        "_max_value",
        "_min_length",
        "_min_value",
    )

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[typing.Any] | None = None,
        max_value: _CmpProto[typing.Any] | None = None,
        multi: bool = False,
    ) -> None:
        """Initialise a parameter."""
        self._client: tanjun.Client | None = None
        self._component: tanjun.Component | None = None
        self._converters: list[ConverterSig[typing.Any]] = []
        self._default = default
        self._is_multi = multi
        self._key = key
        self._min_length = min_length
        self._max_length = max_length
        self._min_value = min_value
        self._max_value = max_value

        if key.startswith("-"):
            error_message = "parameter key cannot start with `-`"
            raise ValueError(error_message)

        if isinstance(converters, collections.Iterable):
            for converter in converters:
                self._add_converter(converter)

        else:
            self._add_converter(converters)

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self._key}>"

    @property
    def converters(self) -> collections.Sequence[ConverterSig[typing.Any]]:
        """Sequence of the converters registered for this parameter."""
        return self._converters.copy()

    @property
    def default(self) -> typing.Any:
        """The parameter's default.

        If this is [tanjun.abc.NO_DEFAULT][] then this parameter is
        required.

        If this is [tanjun.abc.NO_PASS][] then the parameter won't be
        passed when no value was provided.
        """
        return self._default

    @property
    def is_multi(self) -> bool:
        """Whether this parameter is "multi".

        Multi parameters will be passed a list of all the values provided for
        this parameter (with each entry being converted separately).
        """
        return self._is_multi

    @property
    def min_length(self) -> int | None:
        """If set, this parameters's parsed values will have to have lengths greater than or equal to this.

        If any converters are provided then this should be compatible with the
        result of them.
        """
        return self._min_length

    @property
    def max_length(self) -> int | None:
        """If set, this parameters's parsed values will have to have lengths less than or equal to this.

        If any converters are provided then this should be compatible with the
        result of them.
        """
        return self._max_length

    @property
    def min_value(self) -> _CmpProto[typing.Any] | None:
        """If set, this parameters's parsed values will have to be greater than or equal to this.

        If any converters are provided then this should be compatible with the
        result of them.
        """
        return self._min_value

    @property
    def max_value(self) -> _CmpProto[typing.Any] | None:
        """If set, this parameters's parsed values will have to be less than or equal to this.

        If any converters are provided then this should be compatible with the
        result of them.
        """
        return self._max_value

    @property
    def key(self) -> str:
        """The key of this parameter used to pass the result to the command's callback."""
        return self._key

    def _add_converter(self, converter: ConverterSig[typing.Any], /) -> None:
        if self._client and isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
            converter, conversion.BaseConverter
        ):
            converter.check_client(self._client, f"{self._key} parameter")

        # Some types like `bool` and `bytes` are overridden here for the sake of convenience.
        converter = conversion.override_type(converter)
        self._converters.append(converter)

    def bind_client(self, client: tanjun.Client, /) -> None:
        self._client = client
        for converter in self._converters:
            if isinstance(converter, conversion.BaseConverter):  # pyright: ignore[reportUnnecessaryIsInstance]
                converter.check_client(client, f"{self._key} parameter")

    def bind_component(self, component: tanjun.Component, /) -> None:
        self._component = component

    def _validate(self, value: typing.Any, /) -> None:
        # asserts value >= self._min_value
        if self._min_value is not None and self._min_value > value:
            error_message = f"{self._key!r} must be greater than or equal to {self._min_value!r}"
            raise errors.ConversionError(error_message, self._key)

        # asserts value <= self._max_value
        if self._max_value is not None and self._max_value < value:
            error_message = f"{self._key!r} must be less than or equal to {self._max_value!r}"
            raise errors.ConversionError(error_message, self._key)

        length: int | None = None
        # asserts that len(value) >= self._min_length
        if self._min_length is not None and self._min_length > (length := len(value)):
            error_message = f"{self._key!r} must be longer than {self._min_length - 1}"
            raise errors.ConversionError(error_message, self._key)

        # asserts that len(value) <= self._max_length
        if self._max_length is not None and self._max_length < (len(value) if length is None else length):
            error_message = f"{self._key!r} can't be longer than {self._max_length}"
            raise errors.ConversionError(error_message, self._key)

    async def convert(self, ctx: tanjun.Context, value: str, /) -> typing.Any:
        """Convert the given value to the type of this parameter."""
        if not self._converters:
            self._validate(value)
            return value

        sources: list[ValueError] = []
        for converter in self._converters:
            try:
                result = await ctx.call_with_async_di(converter, value)

            except ValueError as exc:
                sources.append(exc)

            else:
                self._validate(result)
                return result

        parameter_type = "option" if isinstance(self, Option) else "argument"
        error_message = f"Couldn't convert {parameter_type} '{self._key}'"
        raise errors.ConversionError(error_message, self._key, errors=sources)

    def copy(self) -> Self:
        """Copy the parameter.

        Returns
        -------
        Self
            A copy of the parameter.
        """
        inst = copy.copy(self)
        inst._converters = [copy.copy(converter) for converter in self._converters]  # noqa: SLF001
        return inst


class Argument(Parameter):
    """Representation of a positional argument used by the standard parser."""

    __slots__ = ("_is_greedy",)

    def __init__(
        self,
        key: str,
        /,
        *,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[typing.Any] | None = None,
        max_value: _CmpProto[typing.Any] | None = None,
        multi: bool = False,
    ) -> None:
        """Initialise a positional argument.

        Parameters
        ----------
        key
            The string identifier of this argument (may be used to pass the result
            of this argument to the command's callback during execution).
        converters
            The converter(s) this argument should use to handle values passed to it
            during parsing.

            If no converters are provided then the raw string value will be passed.

            Only the first converter to pass will be used.
        default
            The default value of this argument, if left as
            [tanjun.abc.NO_DEFAULT][] then this will have no default.

            If this is [tanjun.abc.NO_PASS][] then the `key` parameter won't be
            passed when no value was provided.
        greedy
            Whether or not this argument should be greedy (meaning that it
            takes in the remaining argument values).
        min_length
            Assert that a string argument's length is greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_length
            Assert that a string argument's length is less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        min_value
            Assert that the parsed value(s) for this option are greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_value
            Assert that the parsed value(s) for this option are less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.

        multi
            Whether this argument can be passed multiple times.
        """
        if greedy and multi:
            error_message = "Argument cannot be both greed and multi."
            raise ValueError(error_message)

        self._is_greedy = greedy
        super().__init__(
            key,
            converters=converters,
            default=default,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            multi=multi,
        )

    @property
    def is_greedy(self) -> bool:
        """Whether this parameter is greedy.

        Greedy parameters will consume the remaining message content as one
        string (with converters also being passed the whole string).

        !!! note
            Greedy and multi parameters cannot be used together.
        """
        return self._is_greedy


class Option(Parameter):
    """Representation of a named optional parameter used by the standard parser."""

    __slots__ = ("_empty_value", "_names")

    def __init__(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[typing.Any] | None = None,
        max_value: _CmpProto[typing.Any] | None = None,
        multi: bool = True,
    ) -> None:
        """Initialise a named optional parameter.

        Parameters
        ----------
        key
            The string identifier of this option which will be used to pass the
            result of this argument to the command's callback during execution as
            a keyword argument.
        name
            The name of this option used for identifying it in the parsed content.
        *names
            Other names of this option used for identifying it in the parsed content.
        default
            The default value of this argument, unlike arguments this is required
            for options.
        converters
            The converter(s) this argument should use to handle values passed to it
            during parsing.

            If no converters are provided then the raw string value will be passed.

            Only the first converter to pass will be used.
        empty_value
            The value to use if this option is provided without a value.

            If left as [tanjun.abc.NO_DEFAULT][] then this option
            will error if it's provided without a value.

            [tanjun.abc.NO_PASS][] is not supported for this.
        min_length
            Assert that a string argument's length is greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_length
            Assert that a string argument's length is less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        min_value
            Assert that the parsed value(s) for this option are greater than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.
        max_value
            Assert that the parsed value(s) for this option are less than or equal to this.

            If any converters are provided then this should be compatible
            with the result of them.

        multi
            If this option can be provided multiple times.
        """
        if not name.startswith("-") or not all(n.startswith("-") for n in names):
            error_message = "All option names must start with `-`"
            raise ValueError(error_message)

        self._empty_value = empty_value
        self._names: list[str] = [name, *names]
        super().__init__(
            key,
            converters=converters,
            default=default,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            multi=multi,
        )

    @property
    def empty_value(self) -> typing.Any:
        """The value to return if the option is empty.

        If this is [tanjun.abc.NO_DEFAULT][] then a value will be
        required for the option.
        """
        return self._empty_value

    @property
    def names(self) -> collections.Sequence[str]:
        """Sequence of the CLI names of this option."""
        return self._names.copy()

    def __repr__(self) -> str:
        return f"{type(self).__name__} <{self.key}, {self._names}>"


class ShlexParser(AbstractOptionParser):
    """A shlex based [AbstractOptionParser][tanjun.parsing.AbstractOptionParser] implementation."""

    __slots__ = ("_arguments", "_callback_arg_names", "_client", "_component", "_options")

    def __init__(self) -> None:
        """Initialise a shlex parser."""
        self._arguments: list[Argument] = []
        self._callback_arg_names: list[tuple[str, collections.Container[str]]] = []
        self._client: tanjun.Client | None = None
        self._component: tanjun.Component | None = None
        self._options: list[Option] = []  # TODO: maybe switch to dict[str, Option] and assert doesn't already exist

    @property
    def arguments(self) -> collections.Sequence[Argument]:
        # <<inherited docstring from AbstractOptionParser>>.
        return self._arguments.copy()

    @property
    def options(self) -> collections.Sequence[Option]:
        # <<inherited docstring from AbstractOptionParser>>.
        return self._options.copy()

    def copy(self) -> Self:
        # <<inherited docstring from AbstractOptionParser>>.
        inst = copy.copy(self)
        inst._arguments = [argument.copy() for argument in self._arguments]  # noqa: SLF001
        inst._options = [option.copy() for option in self._options]  # noqa: SLF001
        return inst

    def _assert_key(self, key: str, /) -> None:
        for callback_name, names in self._callback_arg_names:
            if key not in names:
                error_message = f"{key!r} is not a valid keyword argument for {callback_name}"
                raise ValueError(error_message)

    @typing.overload
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[typing.Any]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[str]] = (),
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[str] | None = None,
        max_value: _CmpProto[str] | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _SizedCmpProtoT | None = None,
        max_value: _SizedCmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[collections.Sized]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_value: _CmpProtoT | None = None,
        max_value: _CmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    def add_argument(
        self,
        key: str,
        /,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        *,
        default: typing.Any = tanjun.NO_DEFAULT,
        greedy: bool = False,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: typing.Any | None = None,
        max_value: typing.Any | None = None,
        multi: bool = False,
    ) -> Self:
        # <<inherited docstring from AbstractOptionParser>>.
        self._assert_key(key)
        argument = Argument(
            key,
            converters=converters,
            default=default,
            greedy=greedy,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            multi=multi,
        )
        if self._client:
            argument.bind_client(self._client)

        if self._component:
            argument.bind_component(self._component)

        for argument_ in self._arguments:
            if argument_.is_multi or argument_.is_greedy:
                error_message = "Multi or greedy argument must be the last argument"
                raise ValueError(error_message)

        self._arguments.append(argument)
        return self

    @typing.overload
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[typing.Any]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[str]] = (),
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _CmpProto[str] | None = None,
        max_value: _CmpProto[str] | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[_SizedCmpProtoT]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: _SizedCmpProtoT | None = None,
        max_value: _SizedCmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[collections.Sized]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        multi: bool = False,
    ) -> Self: ...

    @typing.overload
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[_CmpProtoT]],
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_value: _CmpProtoT | None = None,
        max_value: _CmpProtoT | None = None,
        multi: bool = False,
    ) -> Self: ...

    # TODO: add default getter
    def add_option(
        self,
        key: str,
        name: str,
        /,
        *names: str,
        converters: _MaybeIterable[ConverterSig[typing.Any]] = (),
        default: typing.Any,
        empty_value: typing.Any = tanjun.NO_DEFAULT,
        min_length: int | None = None,
        max_length: int | None = None,
        min_value: typing.Any | None = None,
        max_value: typing.Any | None = None,
        multi: bool = False,
    ) -> Self:
        # <<inherited docstring from AbstractOptionParser>>.
        self._assert_key(key)
        option = Option(
            key,
            name,
            *names,
            converters=converters,
            default=default,
            empty_value=empty_value,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
            multi=multi,
        )

        if self._client:
            option.bind_client(self._client)

        if self._component:
            option.bind_component(self._component)

        self._options.append(option)
        return self

    def bind_client(self, client: tanjun.Client, /) -> Self:
        # <<inherited docstring from AbstractOptionParser>>.
        self._client = client
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_client(client)

        return self

    def bind_component(self, component: tanjun.Component, /) -> Self:
        # <<inherited docstring from AbstractOptionParser>>.
        self._component = component
        for parameter in itertools.chain(self._options, self._arguments):
            parameter.bind_component(component)

        return self

    def parse(
        self, ctx: tanjun.MessageContext, /
    ) -> collections.Coroutine[typing.Any, typing.Any, dict[str, typing.Any]]:
        # <<inherited docstring from AbstractOptionParser>>.
        return _SemanticShlex(ctx, self._arguments, self._options).parse()

    def validate_arg_keys(self, callback_name: str, names: collections.Container[str], /) -> None:
        # <<inherited docstring from AbstractOptionParser>>.
        self._callback_arg_names.append((callback_name, names))

        for parameter in itertools.chain(self._options, self._arguments):
            if parameter.key not in names:
                error_message = f"{parameter.key!r} is not a valid keyword argument for {callback_name}"
                raise ValueError(error_message)


def with_parser(command: _CommandT, /) -> _CommandT:
    """Add a shlex parser command parser to a supported command.

    Example
    -------
    ```py
    @tanjun.with_argument("arg", converters=int)
    @tanjun.with_parser
    @tanjun.as_message_command("hi")
    async def hi(ctx: tanjun.MessageContext, arg: int) -> None:
        ...
    ```

    Parameters
    ----------
    command
        The message command to set the parser on.

    Returns
    -------
    tanjun.abc.MessageCommand
        The command with the parser set.

    Raises
    ------
    ValueError
        If the command already has a parser set.
    """
    if command.parser:
        error_message = "Command already has a parser set"
        raise ValueError(error_message)

    return command.set_parser(ShlexParser())
