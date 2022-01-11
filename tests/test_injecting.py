# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2022, Faster Speeding
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

# pyright: reportPrivateUsage=none
# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.
import inspect
import sys
import types
import typing
from unittest import mock

import pytest

import tanjun

_T = typing.TypeVar("_T")


def stub_class(cls: type[_T], /, **namespace: typing.Any) -> type[_T]:
    namespace["__slots__"] = ()

    for name in getattr(cls, "__abstractmethods__", None) or ():
        if name not in namespace:
            namespace[name] = mock.MagicMock()

    name = origin.__name__ if (origin := getattr(cls, "__origin__", None)) else cls.__name__
    new_cls = types.new_class(name, (cls,), exec_body=lambda body: body.update(namespace))
    return typing.cast(type[_T], new_cls)


class TestUndefined:
    def test_bool_operator(self):
        assert bool(tanjun.injecting.UNDEFINED) is False

    def test_undefined_is_singleton(self):
        assert tanjun.injecting.Undefined() is tanjun.injecting.UNDEFINED
        # flake8 false positive errors about comparing types here
        assert tanjun.injecting.Undefined() is type(tanjun.injecting.UNDEFINED)()  # noqa: E721
        assert tanjun.injecting.Undefined() is tanjun.injecting.Undefined()

    def test_undefined_isnt_just_the_same_as_everything(self):
        for value in [1, ", ", b"ok", None, float("inf")]:
            assert tanjun.injecting.Undefined is not value


class TestBasicInjectionContext:
    def test_injection_client_property(self):
        mock_client = mock.Mock()
        ctx = tanjun.injecting.BasicInjectionContext(mock_client)

        assert ctx.injection_client is mock_client

    def test_get_cached_result(self):
        ctx = tanjun.injecting.BasicInjectionContext(mock.Mock())
        mock_result = mock.Mock()
        mock_callback = mock.Mock()
        ctx.cache_result(mock_callback, mock_result)

        assert ctx.get_cached_result(mock_callback) is mock_result

    def test_get_cached_result_when_not_cached(self):
        ctx = tanjun.injecting.BasicInjectionContext(mock.Mock())
        assert ctx.get_cached_result(mock.Mock()) is tanjun.injecting.UNDEFINED

    def test_get_cached_result_when_not_cached_but_other_callback_result_cached(self):
        ctx = tanjun.injecting.BasicInjectionContext(mock.Mock())
        ctx.cache_result(mock.Mock(), mock.Mock())

        assert ctx.get_cached_result(mock.Mock()) is tanjun.injecting.UNDEFINED

    def test_get_type_dependency_when_special_cased(self):
        ctx = tanjun.injecting.BasicInjectionContext(mock.Mock())
        mock_type: typing.Any = mock.Mock()
        mock_value = mock.Mock()
        ctx._set_type_special_case(mock_type, mock_value)

        assert ctx.get_type_dependency(mock_type) is mock_value

    def test_get_type_dependency(self):
        mock_client = mock.Mock()
        mock_type: typing.Any = mock.Mock()
        ctx = tanjun.injecting.BasicInjectionContext(mock_client)

        result = ctx.get_type_dependency(mock_type)

        assert result is mock_client.get_type_dependency.return_value
        mock_client.get_type_dependency.assert_called_once_with(mock_type)


# TODO: integration tests since we don't cover __init__'s normal behaviour since its kinda hard to
# unit test
class TestCallbackDescriptor:
    @pytest.mark.skip(reason="TODO: not sure how to test this")
    def test___init__(self):
        ...

    def test___init___handles_signature_less_builtin_function(self):
        with pytest.raises(ValueError, match=".*"):
            inspect.signature(str)

        descriptor = tanjun.injecting.CallbackDescriptor(str)
        assert descriptor.callback is str
        assert descriptor.needs_injector is False

    def test___init___errors_on_injected_positional_only_injected_argument(self):
        def foo(self: int = tanjun.inject(type=int), /) -> None:
            ...

        with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
            tanjun.injecting.CallbackDescriptor(foo)

    def test___eq___when_same_function(self):
        mock_callback = mock.Mock()

        assert (tanjun.injecting.CallbackDescriptor(mock_callback) == mock_callback) is True

    def test___eq___when_not_same_function(self):
        assert (tanjun.injecting.CallbackDescriptor(mock.Mock()) == mock.Mock()) is False

    def test___hash__(self):
        mock_callback = mock.Mock()

        assert hash(tanjun.injecting.CallbackDescriptor(mock_callback)) == hash(mock_callback)

    def test_callback_property(self):
        mock_callback = mock.Mock()

        assert tanjun.injecting.CallbackDescriptor(mock_callback).callback is mock_callback

    def test_needs_injector_property_when_no_defaulting_type_injector(self):
        mock_type: typing.Any = mock.Mock()

        def sub_callback(baz: typing.Any = tanjun.inject(type=mock_type)) -> None:
            ...

        def foo(
            bar: typing.Any = tanjun.inject(type=mock_type), bat: typing.Any = tanjun.inject(callback=sub_callback)
        ) -> None:
            ...

        assert tanjun.injecting.CallbackDescriptor(foo).needs_injector is True

    def test_needs_injector_property_no_top_level_descriptors_need_type_injector(self):
        class StubType:
            ...

        def sub_callback(baz: str = tanjun.inject(callback=mock.Mock())) -> None:
            ...

        def foo(
            bar: int = tanjun.inject(callback=mock.Mock()),
            baz: typing.Any = tanjun.inject(callback=sub_callback),
            bam: typing.Any = tanjun.inject(type=typing.Optional[StubType]),
        ) -> None:
            ...

        assert tanjun.injecting.CallbackDescriptor(foo).needs_injector is False

    def test_needs_injector_property_when_no_descriptors(self):
        def foo(bar: int, bat: int = 42) -> None:
            ...

        assert tanjun.injecting.CallbackDescriptor(foo).needs_injector is False

    def test_copy(self):
        mock_callback = mock.MagicMock()
        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)

        result = descriptor.copy()

        assert result.callback == mock_callback
        assert result.callback is not mock_callback

    @pytest.mark.skip(reason="TODO: not sure how to test this")
    def test_overwrite_callback(self):
        ...

    def test_overwrite_callback_handles_signature_less_builtin_function(self):
        def foo(self: int = tanjun.inject(type=int)) -> str:
            ...

        with pytest.raises(ValueError, match=".*"):
            inspect.signature(str)

        descriptor = tanjun.injecting.CallbackDescriptor(foo)

        descriptor.overwrite_callback(str)

        assert descriptor.callback is str
        assert descriptor.needs_injector is False

    def test_overwrite_callback_errors_on_injected_positional_only_injected_argument(self):
        def foo(self: int = tanjun.inject(type=int), /) -> int:
            ...

        descriptor = tanjun.injecting.CallbackDescriptor(int)

        with pytest.raises(ValueError, match="Injected positional only arguments are not supported"):
            descriptor.overwrite_callback(foo)

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_needs_injector_and_is_injection_context(self):
        def foo(c: int = tanjun.inject(type=int)) -> None:
            ...

        resolve = mock.AsyncMock()
        resolve_without_injector = mock.AsyncMock()
        descriptor = stub_class(
            tanjun.injecting.CallbackDescriptor[typing.Any],
            resolve=resolve,
            resolve_without_injector=resolve_without_injector,
        )(foo)
        mock_context = mock.Mock(tanjun.injecting.AbstractInjectionContext)

        await descriptor.resolve_with_command_context(mock_context, 333, 222, 111, b=333, c=222)

        resolve.assert_awaited_once_with(mock_context, 333, 222, 111, b=333, c=222)
        resolve_without_injector.assert_not_called()

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_needs_injector_but_not_injection_context(self):
        def foo(c: int = tanjun.inject(type=int)) -> None:
            ...

        resolve = mock.AsyncMock()
        resolve_without_injector = mock.AsyncMock()
        descriptor = stub_class(
            tanjun.injecting.CallbackDescriptor[typing.Any],
            resolve=resolve,
            resolve_without_injector=resolve_without_injector,
        )(foo)
        mock_context = mock.Mock()

        await descriptor.resolve_with_command_context(mock_context, 123, 432, a=1234, o=4312, i1=123)

        resolve.assert_not_called()
        resolve_without_injector.assert_awaited_once_with(123, 432, a=1234, o=4312, i1=123)

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_not_needs_injector(self):
        resolve = mock.AsyncMock()
        resolve_without_injector = mock.AsyncMock()
        descriptor = stub_class(
            tanjun.injecting.CallbackDescriptor[typing.Any],
            resolve=resolve,
            resolve_without_injector=resolve_without_injector,
        )(mock.Mock())
        mock_context = mock.Mock()

        await descriptor.resolve_with_command_context(mock_context, 5412, by=123, sa=123)

        resolve.assert_not_called()
        resolve_without_injector.assert_awaited_once_with(5412, by=123, sa=123)

    @pytest.mark.asyncio()
    async def test_resolve_without_injector(self):
        mock_resolve = mock.AsyncMock()
        descriptor = stub_class(tanjun.injecting.CallbackDescriptor[typing.Any], resolve=mock_resolve)(mock.Mock())

        with mock.patch.object(tanjun.injecting, "_EmptyContext") as empty_context:
            result = await descriptor.resolve_without_injector(1, 2, 3, a=53, g=123, t=123)

            empty_context.assert_called_once_with()

        assert result is mock_resolve.return_value
        mock_resolve.assert_awaited_once_with(empty_context.return_value, 1, 2, 3, a=53, g=123, t=123)

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_when_needs_injector(self):
        def foo(i: int = tanjun.inject(type=int)) -> None:
            ...

        with pytest.raises(RuntimeError, match="Callback descriptor needs a dependency injection client"):
            await tanjun.injecting.CallbackDescriptor(foo).resolve_without_injector(123)

    @pytest.mark.asyncio()
    async def test_resolve(self):
        result_collector = mock.AsyncMock()
        async_sub_dependency = mock.AsyncMock()
        sub_dependency = mock.Mock()
        mock_type: typing.Any = mock.Mock()
        mock_context = mock.Mock()
        mock_context.injection_client.get_callback_override.return_value = None
        mock_context.get_cached_result.return_value = tanjun.injecting.UNDEFINED

        def sync_sub_callback() -> typing.Any:
            return sub_dependency()

        def async_sub_callback(sub: typing.Any = tanjun.inject(callback=sync_sub_callback)) -> typing.Any:
            return async_sub_dependency(sub=sub)

        def mock_callback(
            *args: typing.Any,
            ty: typing.Any = tanjun.inject(type=mock_type),
            sub_async: typing.Any = tanjun.inject(callback=async_sub_callback),
            **kwargs: typing.Any,
        ) -> typing.Any:
            return result_collector(*args, **kwargs, ty=ty, sub_async=sub_async)

        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)

        result = await descriptor.resolve(mock_context, 123, b=333, c=222)

        assert result is result_collector.return_value

        mock_context.injection_client.get_callback_override.assert_has_calls(
            [mock.call(mock_callback), mock.call(async_sub_callback), mock.call(sync_sub_callback)], any_order=True
        )
        result_collector.assert_awaited_once_with(
            123,
            b=333,
            c=222,
            ty=mock_context.get_type_dependency.return_value,
            sub_async=async_sub_dependency.return_value,
        )
        mock_context.get_type_dependency.assert_called_once_with(mock_type)
        async_sub_dependency.assert_awaited_once_with(sub=sub_dependency.return_value)
        sub_dependency.assert_called_once_with()
        mock_context.get_cached_result.assert_has_calls(
            [
                mock.call(mock_callback),
                mock.call(async_sub_callback),
                mock.call(sync_sub_callback),
            ],
            any_order=True,
        )
        mock_context.cache_result.assert_has_calls(
            [
                mock.call(mock_callback, result_collector.return_value),
                mock.call(async_sub_callback, async_sub_dependency.return_value),
                mock.call(sync_sub_callback, sub_dependency.return_value),
            ],
            any_order=True,
        )

    @pytest.mark.asyncio()
    async def test_resolve_when_overridden(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)
        mock_context = mock.Mock()
        mock_context.injection_client.get_callback_override.return_value.resolve = mock.AsyncMock()

        result = await descriptor.resolve(mock_context, 123, b=333, c=222)

        assert result is mock_context.injection_client.get_callback_override.return_value.resolve.return_value
        mock_context.injection_client.get_callback_override.return_value.resolve.assert_awaited_once_with(
            mock_context, 123, b=333, c=222
        )
        mock_context.injection_client.get_callback_override.assert_called_once_with(mock_callback)
        mock_context.get_cached_result.assert_not_called()
        mock_callback.assert_not_called()
        mock_context.cache_result.assert_not_called()

    @pytest.mark.asyncio()
    async def test_resolve_when_cached(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)
        mock_context = mock.Mock()
        mock_context.injection_client.get_callback_override.return_value = None

        result = await descriptor.resolve(mock_context, 123, b=333, c=222)

        assert result is mock_context.get_cached_result.return_value
        mock_context.injection_client.get_callback_override.assert_called_once_with(mock_callback)
        mock_context.get_cached_result.assert_called_once_with(mock_callback)
        mock_callback.assert_not_called()
        mock_context.cache_result.assert_not_called()


class TestSelfInjectingCallback:
    @pytest.mark.asyncio()
    async def test___call__(self):
        mock_client = mock.Mock()
        mock_resolve = mock.AsyncMock()

        callback = stub_class(tanjun.injecting.SelfInjectingCallback[typing.Any], resolve=mock_resolve)(
            mock_client, mock.Mock()
        )

        with mock.patch.object(tanjun.injecting, "BasicInjectionContext") as base_injection_context:
            result = await callback(123, b=333, c=222)

        assert result is mock_resolve.return_value
        base_injection_context.assert_called_once_with(mock_client)
        mock_resolve.assert_awaited_once_with(base_injection_context.return_value, 123, b=333, c=222)


def test_as_self_injecting():
    mock_callback = mock.Mock()
    mock_client = mock.Mock()

    with mock.patch.object(tanjun.injecting, "SelfInjectingCallback") as self_injecting_callback:
        result = tanjun.injecting.as_self_injecting(mock_client)(mock_callback)

    assert result is self_injecting_callback.return_value
    self_injecting_callback.assert_called_once_with(mock_client, mock_callback)


class TestTypeDescriptor:
    def test_needs_injector_property(self):
        mock_type: typing.Any = mock.Mock()

        assert tanjun.injecting.TypeDescriptor(mock_type).needs_injector is True

    def test_needs_injector_property_with_typing_union(self):
        class StubType:
            ...

        assert tanjun.injecting.TypeDescriptor(typing.Union[StubType, str]).needs_injector is True

    def test_needs_injector_property_with_typing_union_default(self):
        class StubType:
            ...

        assert tanjun.injecting.TypeDescriptor(typing.Union[StubType, None]).needs_injector is False

    # These tests covers syntax which was introduced in 3.10
    if sys.version_info >= (3, 10):

        def test_needs_injector_property_with_types_union(self):
            class StubType:
                ...

            assert tanjun.injecting.TypeDescriptor(StubType | int).needs_injector is True

        def test_needs_injector_property_with_types_union_default(self):
            class StubType:
                ...

            assert tanjun.injecting.TypeDescriptor(StubType | None).needs_injector is False

    def test_type_property(self):
        mock_type: typing.Any = mock.Mock()

        assert tanjun.injecting.TypeDescriptor(mock_type).type is mock_type

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_injection_context(self):
        mock_type: typing.Any = mock.Mock()
        resolve = mock.AsyncMock()
        resolve_without_injector = mock.AsyncMock()
        descriptor = stub_class(
            tanjun.injecting.TypeDescriptor[typing.Any],
            resolve=resolve,
            resolve_without_injector=resolve_without_injector,
        )(mock_type)
        mock_context = mock.Mock(tanjun.injecting.AbstractInjectionContext)

        result = await descriptor.resolve_with_command_context(mock_context)

        assert result is resolve.return_value
        resolve.assert_awaited_once_with(mock_context)
        resolve_without_injector.assert_not_called()

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_not_injection_context(self):
        mock_type: typing.Any = mock.Mock()
        resolve = mock.AsyncMock()
        resolve_without_injector = mock.AsyncMock()
        descriptor = stub_class(
            tanjun.injecting.TypeDescriptor[typing.Any],
            resolve=resolve,
            resolve_without_injector=resolve_without_injector,
        )(mock_type)
        mock_context = mock.Mock()

        result = await descriptor.resolve_with_command_context(mock_context)

        assert result is resolve_without_injector.return_value
        resolve.assert_not_called()
        resolve_without_injector.assert_awaited_once_with()

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_when_not_injection_context(self):
        mock_type: typing.Any = mock.Mock()
        resolve = mock.AsyncMock()
        descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=resolve)(mock_type)

        with pytest.raises(RuntimeError, match="Type descriptor cannot be resolved without an injection client"):
            await descriptor.resolve_without_injector()

        resolve.assert_not_called()

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_when_not_injection_context_and_typing_union(self):
        class StubType:
            ...

        resolve = mock.AsyncMock()
        descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=resolve)(
            typing.Union[StubType, int]
        )

        with pytest.raises(RuntimeError, match="Type descriptor cannot be resolved without an injection client"):
            await descriptor.resolve_without_injector()

        resolve.assert_not_called()

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_when_not_injection_context_and_has_typing_default(self):
        class StubType:
            ...

        resolve = mock.AsyncMock()
        descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=resolve)(typing.Optional[StubType])

        result = await descriptor.resolve_without_injector()

        assert result is None
        resolve.assert_not_called()

    # This test covers syntax which was introduced in 3.10
    if sys.version_info >= (3, 10):

        @pytest.mark.asyncio()
        async def test_resolve_without_injector_when_not_injection_context_and_has_types_union(self):
            class StubType:
                ...

            resolve = mock.AsyncMock()
            descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=resolve)(StubType | int)

            with pytest.raises(RuntimeError, match="Type descriptor cannot be resolved without an injection client"):
                await descriptor.resolve_without_injector()

            resolve.assert_not_called()

        @pytest.mark.asyncio()
        async def test_resolve_without_injector_when_not_injection_context_and_has_types_default(self):
            class StubType:
                ...

            resolve = mock.AsyncMock()
            descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=resolve)(StubType | None)

            result = await descriptor.resolve_without_injector()

            assert result is None
            resolve.assert_not_called()

    @pytest.mark.asyncio()
    async def test_resolve(self):
        ctx = mock.Mock()
        mock_type: typing.Any = mock.Mock()

        result = await tanjun.injecting.TypeDescriptor(mock_type).resolve(ctx)

        assert result is ctx.get_type_dependency.return_value

    @pytest.mark.asyncio()
    async def test_resolve_when_typing_union_but_impl_found_before_trying_union_args(self):
        class StubType1:
            ...

        class StubType2:
            ...

        ctx = mock.Mock()

        result = await tanjun.injecting.TypeDescriptor(typing.Union[StubType1, StubType2]).resolve(ctx)

        assert result is ctx.get_type_dependency.return_value
        ctx.get_type_dependency.assert_called_once_with(typing.Union[StubType1, StubType2])

    @pytest.mark.asyncio()
    async def test_resolve_when_not_found(self):
        ctx = mock.Mock()
        ctx.get_type_dependency.return_value = tanjun.injecting.UNDEFINED
        mock_type: typing.Any = mock.Mock()

        with pytest.raises(tanjun.MissingDependencyError):
            await tanjun.injecting.TypeDescriptor(mock_type).resolve(ctx)

        ctx.get_type_dependency.assert_called_once_with(mock_type)

    # These tests cover syntax which was introduced in 3.10
    if sys.version_info >= (3, 10):

        @pytest.mark.asyncio()
        async def test_resolve_when_types_union(self):
            class StubType1:
                ...

            class StubType2:
                ...

            class StubType3:
                ...

            ctx = mock.Mock()
            mock_result = mock.Mock()
            ctx.get_type_dependency.side_effect = [
                tanjun.injecting.UNDEFINED,
                tanjun.injecting.UNDEFINED,
                mock_result,
            ]

            result = await tanjun.injecting.TypeDescriptor(StubType1 | StubType2 | StubType3).resolve(ctx)

            assert result is mock_result
            ctx.get_type_dependency.assert_has_calls(
                [mock.call(StubType1 | StubType2 | StubType3), mock.call(StubType1), mock.call(StubType2)]
            )

        @pytest.mark.asyncio()
        async def test_resolve_when_types_union_but_impl_found_before_trying_union_args(self):
            class StubType1:
                ...

            class StubType2:
                ...

            ctx = mock.Mock()

            result = await tanjun.injecting.TypeDescriptor(StubType1 | StubType2).resolve(ctx)

            assert result is ctx.get_type_dependency.return_value
            ctx.get_type_dependency.assert_called_once_with(StubType1 | StubType2)

        @pytest.mark.asyncio()
        async def test_resolve_when_types_union_and_not_found(self):
            class StubType1:
                ...

            class StubType2:
                ...

            class StubType3:
                ...

            ctx = mock.Mock()
            ctx.get_type_dependency.return_value = tanjun.injecting.UNDEFINED

            with pytest.raises(tanjun.MissingDependencyError):
                await tanjun.injecting.TypeDescriptor(StubType1 | StubType2 | StubType3).resolve(ctx)

            ctx.get_type_dependency.assert_has_calls([mock.call(StubType1), mock.call(StubType2), mock.call(StubType3)])

        @pytest.mark.asyncio()
        async def test_resolve_when_types_optional_and_not_found(self):
            class StubType:
                ...

            ctx = mock.Mock()
            ctx.get_type_dependency.return_value = tanjun.injecting.UNDEFINED

            result = await tanjun.injecting.TypeDescriptor(StubType | None).resolve(ctx)

            assert result is None
            ctx.get_type_dependency.assert_has_calls([mock.call(StubType | None), mock.call(StubType)])

    @pytest.mark.asyncio()
    async def test_resolve_when_typing_union(self):
        class StubType1:
            ...

        class StubType2:
            ...

        class StubType3:
            ...

        ctx = mock.Mock()
        mock_result = mock.Mock()
        ctx.get_type_dependency.side_effect = [
            tanjun.injecting.UNDEFINED,
            tanjun.injecting.UNDEFINED,
            mock_result,
        ]

        result = await tanjun.injecting.TypeDescriptor(typing.Union[StubType1, StubType2, StubType3]).resolve(ctx)

        assert result is mock_result
        ctx.get_type_dependency.assert_has_calls(
            [mock.call(typing.Union[StubType1, StubType2, StubType3]), mock.call(StubType1), mock.call(StubType2)]
        )

    @pytest.mark.asyncio()
    async def test_resolve_when_typing_union_and_not_found(self):
        class StubType1:
            ...

        class StubType2:
            ...

        class StubType3:
            ...

        ctx = mock.Mock()
        ctx.get_type_dependency.return_value = tanjun.injecting.UNDEFINED

        with pytest.raises(tanjun.MissingDependencyError):
            await tanjun.injecting.TypeDescriptor(typing.Union[StubType1, StubType2, StubType3]).resolve(ctx)

        ctx.get_type_dependency.assert_has_calls([mock.call(StubType1), mock.call(StubType2), mock.call(StubType3)])

    @pytest.mark.asyncio()
    async def test_resolve_when_typing_optional_and_not_found(self):
        class StubType:
            ...

        ctx = mock.Mock()
        ctx.get_type_dependency.return_value = tanjun.injecting.UNDEFINED

        result = await tanjun.injecting.TypeDescriptor(typing.Optional[StubType]).resolve(ctx)

        assert result is None
        ctx.get_type_dependency.assert_has_calls([mock.call(typing.Optional[StubType]), mock.call(StubType)])


class TestInjected:
    def test_when_both_fields_provided(self):
        with pytest.raises(ValueError, match="Only one of `callback` or `type` can be specified"):
            tanjun.inject(callback=mock.Mock(), type=mock.Mock())  # type: ignore

    def test_when_no_options_provided(self):
        with pytest.raises(ValueError, match="Must specify one of `callback` or `type`"):
            tanjun.inject()  # type: ignore


def test_inject_with_callback():
    mock_type: typing.Any = mock.Mock()

    result = tanjun.injecting.inject(type=mock_type)

    assert result.callback is None
    assert result.type is mock_type


def test_inject_with_type():
    mock_callback = mock.Mock()

    result = tanjun.injecting.inject(callback=mock_callback)

    assert result.callback is mock_callback
    assert result.type is None


def test_injected():
    mock_callback = mock.Mock()
    mock_type: typing.Any = mock.Mock()

    with mock.patch.object(tanjun.injecting, "Injected") as injected:
        result = tanjun.inject(callback=mock_callback, type=mock_type)  # type: ignore

    assert result is injected.return_value
    injected.assert_called_once_with(callback=mock_callback, type=mock_type)


class TestInjectorClient:
    def test_get_type_dependency(self):
        mock_value = mock.Mock()
        mock_type: typing.Any = mock.Mock()
        client = tanjun.injecting.InjectorClient().set_type_dependency(mock_type, mock_value)

        result = client.get_type_dependency(mock_type)

        assert result is mock_value

    def test_get_type_dependency_for_unknown_dependency(self):
        assert tanjun.injecting.InjectorClient().get_type_dependency(object) is tanjun.injecting.UNDEFINED

    def test_remove_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        client = tanjun.injecting.InjectorClient().set_type_dependency(mock_type, mock.Mock())

        result = client.remove_type_dependency(mock_type)

        assert result is client
        assert client.get_type_dependency(mock_type) is tanjun.injecting.UNDEFINED

    def test_get_callback_override(self):
        mock_callback = mock.Mock()
        mock_override = mock.Mock()
        client = tanjun.injecting.InjectorClient().set_callback_override(mock_callback, mock_override)

        result = client.get_callback_override(mock_callback)

        assert result
        assert result.callback is mock_override

    def test_get_callback_override_for_unknown_override(self):
        assert tanjun.injecting.InjectorClient().get_callback_override(mock.Mock()) is None

    def test_remove_callback_override(self):
        mock_callback = mock.Mock()
        client = tanjun.injecting.InjectorClient().set_callback_override(mock_callback, mock.Mock())

        result = client.remove_callback_override(mock_callback)

        assert result is client
        assert client.get_callback_override(mock_callback) is None


class Test_EmptyInjectorClient:
    def set_type_dependency(self):
        mock_type: typing.Any = mock.Mock()

        result = tanjun.injecting._EMPTY_CLIENT.set_type_dependency(mock_type, mock.Mock())

        assert result is tanjun.injecting._EMPTY_CLIENT

    def get_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        tanjun.injecting._EMPTY_CLIENT.set_type_dependency(mock_type, mock.Mock())

        result = tanjun.injecting._EMPTY_CLIENT.get_type_dependency(mock_type)

        assert result is tanjun.injecting.UNDEFINED

    def remove_type_dependency(self):
        mock_type: typing.Any = mock.Mock()
        tanjun.injecting._EMPTY_CLIENT.set_type_dependency(mock_type, mock.Mock())

        with pytest.raises(KeyError) as exc_info:
            tanjun.injecting._EMPTY_CLIENT.remove_type_dependency(mock_type)

        assert exc_info.value.args[0] is mock_type

    def set_callback_override(self):
        result = tanjun.injecting._EMPTY_CLIENT.set_callback_override(mock.Mock(), mock.Mock())
        assert result is None

    def get_callback_override(self):
        mock_callback = mock.Mock()
        tanjun.injecting._EMPTY_CLIENT.set_callback_override(mock_callback, mock.Mock())

        result = tanjun.injecting._EMPTY_CLIENT.remove_callback_override(mock_callback)

        assert result is None

    def remove_callback_override(self):
        mock_callback = mock.Mock()
        tanjun.injecting._EMPTY_CLIENT.set_callback_override(mock_callback, mock.Mock())

        with pytest.raises(KeyError) as exc_info:
            tanjun.injecting._EMPTY_CLIENT.remove_callback_override(mock_callback)

        assert exc_info.value.args[0] is mock_callback


class test_EmptyContext:
    def test_injection_client_property(self):
        assert tanjun.injecting._EmptyContext().injection_client is tanjun.injecting._EMPTY_CLIENT

    def cache_result(self) -> None:
        mock_callback = mock.Mock()
        mock_result = mock.Mock()
        ctx = tanjun.injecting._EmptyContext()

        result = ctx.cache_result(mock_callback, mock_result)

        assert result is None
        assert ctx.get_cached_result(mock_callback) is mock_result

    def get_cached_result(self):
        ctx = tanjun.injecting._EmptyContext()

        assert ctx.get_cached_result(mock.Mock()) is tanjun.injecting.UNDEFINED

    def get_cached_result_when_not_found_but_previous_result_set_for_other_callback(self):
        ctx = tanjun.injecting._EmptyContext()
        ctx.cache_result(mock.Mock(), mock.Mock())

        assert ctx.get_cached_result(mock.Mock()) is tanjun.injecting.UNDEFINED

    def get_get_type_dependency(self):
        ctx = tanjun.injecting._EmptyContext()
        mock_type: typing.Any = mock.Mock()

        assert ctx.get_type_dependency(mock_type) is tanjun.injecting.UNDEFINED
