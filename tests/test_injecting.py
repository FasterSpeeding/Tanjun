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

# pyright: reportUnknownMemberType=none
# This leads to too many false-positives around mocks.
import inspect
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

    def test_get_type_special_case(self):
        ctx = tanjun.injecting.BasicInjectionContext(mock.Mock())
        mock_type: type[typing.Any] = mock.Mock()
        mock_value = mock.Mock()
        ctx._set_type_special_case(mock_type, mock_value)

        assert ctx.get_type_special_case(mock_type) is mock_value

    def test_get_type_special_case_when_not_set(self):
        mock_client = mock.Mock()
        mock_type: type[typing.Any] = mock.Mock()
        ctx = tanjun.injecting.BasicInjectionContext(mock_client)

        assert ctx.get_type_special_case(mock_type) is tanjun.injecting.UNDEFINED


class TestCallbackDescriptor:
    def test___init___handles_signature_less_builtin_function(self):
        with pytest.raises(ValueError, match=".*"):
            inspect.signature(str)

        descriptor = tanjun.injecting.CallbackDescriptor(str)
        assert descriptor.callback is str
        assert descriptor.needs_injector is False

    def test___init___errors_on_injected_positional_only_injected_argument(self):
        def foo(self: int = tanjun.injecting.injected(type=int), /) -> None:
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

    def test_needs_injector_property_when_true(self):
        def foo(bar: int = tanjun.injecting.injected(callback=mock.Mock())) -> None:
            ...

        assert tanjun.injecting.CallbackDescriptor(foo).needs_injector is True

    def test_needs_injector_property_when_false(self):
        def foo(bar: int, bat: int = 42) -> None:
            ...

        assert tanjun.injecting.CallbackDescriptor(foo).needs_injector is False

    def test_copy(self):
        mock_callback = mock.MagicMock()
        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)

        result = descriptor.copy()

        assert result.callback == mock_callback
        assert result.callback is not mock_callback

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_needs_injector_and_is_injection_context(self):
        def foo(c: int = tanjun.injecting.injected(type=int)) -> None:
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
        def foo(c: int = tanjun.injecting.injected(type=int)) -> None:
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
    async def test_resolve_without_injector_with_async_method(self):
        mock_callback = mock.AsyncMock()
        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)

        result = await descriptor.resolve_without_injector(1, 2, 3, a=53, g=123, t=123)

        assert result is mock_callback.return_value
        mock_callback.assert_awaited_once_with(1, 2, 3, a=53, g=123, t=123)

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_with_sync_method(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.injecting.CallbackDescriptor(mock_callback)

        result = await descriptor.resolve_without_injector(1, 2, 3, a=53, g=123, t=123)

        assert result is mock_callback.return_value
        mock_callback.assert_called_once_with(1, 2, 3, a=53, g=123, t=123)

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_when_needs_injector(self):
        def foo(i: int = tanjun.injecting.injected(type=int)) -> None:
            ...

        with pytest.raises(RuntimeError):
            await tanjun.injecting.CallbackDescriptor(foo).resolve_without_injector(123)

    @pytest.mark.asyncio()
    async def test_resolve(self):
        result_collector = mock.AsyncMock()
        async_sub_dependency = mock.AsyncMock()
        sub_dependency = mock.Mock()
        mock_type: type[typing.Any] = mock.Mock()
        mock_context = mock.Mock()
        mock_context.injection_client.get_callback_override.return_value = None
        mock_context.get_cached_result.return_value = tanjun.injecting.UNDEFINED
        mock_context.get_type_special_case.return_value = tanjun.injecting.UNDEFINED
        mock_context.injection_client.get_type_dependency.return_value

        def sync_sub_callback() -> typing.Any:
            return sub_dependency()

        def async_sub_callback(sub: typing.Any = tanjun.injected(callback=sync_sub_callback)) -> typing.Any:
            return async_sub_dependency(sub=sub)

        def mock_callback(
            *args: typing.Any,
            ty: typing.Any = tanjun.injected(type=mock_type),
            sub_async: typing.Any = tanjun.injected(callback=async_sub_callback),
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
            ty=mock_context.injection_client.get_type_dependency.return_value,
            sub_async=async_sub_dependency.return_value,
        )
        mock_context.injection_client.get_type_dependency.assert_called_once_with(mock_type)
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

    @pytest.mark.asyncio()
    async def test_resolve_when_injection_not_needed(self):
        mock_callback = mock.Mock()
        resolve_without_injector = mock.AsyncMock()
        descriptor = stub_class(
            tanjun.injecting.CallbackDescriptor[typing.Any], resolve_without_injector=resolve_without_injector
        )(mock_callback)
        mock_context = mock.Mock()
        mock_context.injection_client.get_callback_override.return_value = None
        mock_context.get_cached_result.return_value = tanjun.injecting.UNDEFINED

        result = await descriptor.resolve(mock_context, 123, b=333, c=222)

        assert result is resolve_without_injector.return_value
        mock_context.injection_client.get_callback_override.assert_called_once_with(mock_callback)
        mock_context.get_cached_result.assert_called_once_with(mock_callback)
        mock_callback.assert_not_called()
        mock_context.cache_result.assert_called_once_with(mock_callback, resolve_without_injector.return_value)
        resolve_without_injector.assert_awaited_once_with(123, b=333, c=222)


class TestTypeDescriptor:
    def test_type_property(self):
        mock_type: type[typing.Any] = mock.Mock()

        assert tanjun.injecting.TypeDescriptor(mock_type).type is mock_type

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_injection_context(self):
        mock_type: type[typing.Any] = mock.Mock()
        resolve = mock.AsyncMock()
        descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=resolve)(mock_type)
        mock_context = mock.Mock(tanjun.injecting.AbstractInjectionContext)

        await descriptor.resolve_with_command_context(mock_context)

        resolve.assert_awaited_once_with(mock_context)

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_when_not_injection_context(self):
        mock_type: type[typing.Any] = mock.Mock()
        resolve = mock.AsyncMock()
        descriptor = stub_class(tanjun.injecting.TypeDescriptor[typing.Any], resolve=mock.AsyncMock())(mock_type)

        with pytest.raises(RuntimeError):
            await descriptor.resolve_with_command_context(mock.Mock())

        resolve.assert_not_called()

    def test_resolve(self):
        ctx = mock.Mock()
        ctx.injection_client.get_type_dependency.return_value = mock.AsyncMock()
        mock_type: type[typing.Any] = mock.Mock()

        result = tanjun.injecting.TypeDescriptor(mock_type).resolve(ctx)

        assert result is ctx.injection_client.get_type_dependency.return_value

    def test_resolve_when_special_case_found(self):
        ctx = mock.Mock()
        ctx.injection_client.get_type_dependency = mock.Mock(return_value=tanjun.injecting.UNDEFINED)
        mock_type: type[typing.Any] = mock.Mock()

        result = tanjun.injecting.TypeDescriptor(mock_type).resolve(ctx)

        assert result is ctx.get_type_special_case.return_value
        ctx.injection_client.get_type_dependency.assert_called_once_with(mock_type)
        ctx.get_type_special_case.assert_called_once_with(mock_type)

    def test_resolve_when_not_found(self):
        ctx = mock.Mock(get_type_special_case=mock.Mock(return_value=tanjun.injecting.UNDEFINED))
        ctx.injection_client.get_type_dependency.return_value = tanjun.injecting.UNDEFINED
        mock_type: type[typing.Any] = mock.Mock()

        with pytest.raises(tanjun.MissingDependencyError):
            tanjun.injecting.TypeDescriptor(mock_type).resolve(ctx)

        ctx.injection_client.get_type_dependency.assert_called_once_with(mock_type)
        ctx.get_type_special_case.assert_called_once_with(mock_type)


class TestDescriptor:
    def test___init__when_both_options_provided(self):
        with pytest.raises(ValueError, match="Only one of type or callback should be passed"):
            tanjun.injecting.Descriptor(callback=mock.Mock(), type=mock.Mock())  # type: ignore

    def test___init__when_no_options_provided(self):
        with pytest.raises(ValueError, match="Either callback or type must be specified"):
            tanjun.injecting.Descriptor()  # type: ignore

    def test_callback_property_when_callback_bound(self):
        mock_callback = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(callback=mock_callback)

        assert descriptor.callback is mock_callback

    def test_callback_property_when_type_bound(self):
        mock_type: type[typing.Any] = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(type=mock_type)

        assert descriptor.callback is None

    def test_needs_injector_property_when_callback_bound(self):
        mock_callback = mock.Mock()

        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as callback_descriptor:
            descriptor = tanjun.injecting.Descriptor(callback=mock_callback)

            assert descriptor.needs_injector is callback_descriptor.return_value.needs_injector

    def test_needs_injector_property_when_type_bound(self):
        mock_type: type[typing.Any] = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(type=mock_type)

        assert descriptor.needs_injector is True

    def test_type_property_when_type_bound(self):
        mock_type: type[typing.Any] = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(type=mock_type)

        assert descriptor.type is mock_type

    def test_type_property_when_callback_bound(self):
        descriptor = tanjun.injecting.Descriptor(callback=mock.Mock())

        assert descriptor.type is None

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_for_type_bound_descriptor(self):
        mock_ctx = mock.Mock()
        mock_type: type[typing.Any] = mock.Mock()

        with mock.patch.object(tanjun.injecting, "TypeDescriptor") as type_descriptor:
            descriptor = tanjun.injecting.Descriptor(type=mock_type)

        result = await descriptor.resolve_with_command_context(mock_ctx)

        assert result is type_descriptor.return_value.resolve_with_command_context.return_value
        type_descriptor.return_value.resolve_with_command_context.assert_called_once_with(mock_ctx)

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_for_type_bound_descriptor_when_args_passed(self):
        mock_type: type[typing.Any] = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(type=mock_type)

        with pytest.raises(ValueError, match=r"\*args and \*\*kwargs cannot be passed for a type descriptor"):
            await descriptor.resolve_with_command_context(mock.Mock(), 1)

    @pytest.mark.asyncio()
    async def test_resolve_with_command_context_for_type_bound_descriptor_when_kwargs_passed(self):
        mock_type: type[typing.Any] = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(type=mock_type)

        with pytest.raises(ValueError, match=r"\*args and \*\*kwargs cannot be passed for a type descriptor"):
            await descriptor.resolve_with_command_context(mock.Mock(), a=1)

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_for_callback_bound_descriptor(self):
        with mock.patch.object(
            tanjun.injecting, "CallbackDescriptor", return_value=mock.AsyncMock()
        ) as callback_descriptor:
            descriptor = tanjun.injecting.Descriptor(callback=mock.Mock())

        result = await descriptor.resolve_without_injector(4, 2, 6, a=75, b=123)

        assert result is callback_descriptor.return_value.resolve_without_injector.return_value
        callback_descriptor.return_value.resolve_without_injector.assert_awaited_once_with(4, 2, 6, a=75, b=123)

    @pytest.mark.asyncio()
    async def test_resolve_without_injector_for_type_bound_descriptor(self):
        mock_type: type[typing.Any] = mock.Mock()
        descriptor = tanjun.injecting.Descriptor(type=mock_type)

        with pytest.raises(RuntimeError, match="Type injector cannot be resolved without an injector present"):
            await descriptor.resolve_without_injector()


class TestInjected:
    def test_when_both_fields_provided(self):
        with pytest.raises(ValueError, match="Only one of `callback` or `type` can be specified"):
            tanjun.injecting.Injected(callback=mock.Mock(), type=mock.Mock())  # type: ignore

    def test_when_no_options_provided(self):
        with pytest.raises(ValueError, match="Must specify one of `callback` or `type`"):
            tanjun.injecting.Injected()  # type: ignore


def test_injected_with_callback():
    mock_type: type[typing.Any] = mock.Mock()

    result = tanjun.injecting.injected(type=mock_type)

    assert result.callback is None
    assert result.type is mock_type


def test_injected_with_type():
    mock_callback = mock.Mock()

    result = tanjun.injecting.injected(callback=mock_callback)

    assert result.callback is mock_callback
    assert result.type is None


class TestInjectorClient:
    def test_get_type_dependency(self):
        mock_value = mock.Mock()
        mock_type: type[typing.Any] = mock.Mock()
        client = tanjun.injecting.InjectorClient().set_type_dependency(mock_type, mock_value)

        result = client.get_type_dependency(mock_type)

        assert result is mock_value

    def test_get_type_dependency_for_unknown_dependency(self):
        assert tanjun.injecting.InjectorClient().get_type_dependency(object) is tanjun.UNDEFINED

    def test_remove_type_dependency(self):
        mock_type: type[typing.Any] = mock.Mock()
        client = tanjun.injecting.InjectorClient().set_type_dependency(mock_type, mock.Mock())

        result = client.remove_type_dependency(mock_type)

        assert result is client
        assert client.get_type_dependency(mock_type) is tanjun.UNDEFINED

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


class TestBaseInjectableCallback:
    def test___eq___with_same_function(self):
        mock_callback = mock.Mock()

        assert (tanjun.injecting.BaseInjectableCallback(mock_callback) == mock_callback) is True

    def test___eq___with_different_function(self):
        assert (tanjun.injecting.BaseInjectableCallback(mock.Mock()) == mock.Mock()) is False

    def test___hash___(self):
        mock_callback = mock.Mock()
        assert hash(tanjun.injecting.BaseInjectableCallback(mock_callback)) == hash(mock_callback)

    def test___repr___(self):
        mock_callback = mock.Mock()
        wrapped = tanjun.injecting.BaseInjectableCallback(mock_callback)

        assert repr(wrapped) == f"BaseInjectableCallback({mock_callback!r})"

    def test_callback_property(self):
        mock_callback = mock.Mock()
        assert tanjun.injecting.BaseInjectableCallback(mock_callback).callback is mock_callback

    def test_descriptor_property(self):
        mock_callback = mock.Mock()

        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as callback_descriptor:
            assert tanjun.injecting.BaseInjectableCallback(mock_callback).descriptor is callback_descriptor.return_value

            callback_descriptor.assert_called_once_with(mock_callback)

    def test_needs_injector_property(self):
        mock_callback = mock.Mock()

        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as callback_descriptor:
            result = tanjun.injecting.BaseInjectableCallback(mock_callback)

            assert result.needs_injector is callback_descriptor.return_value.needs_injector
            callback_descriptor.assert_called_once_with(mock_callback)

    def test_copy(self):
        mock_callback = mock.Mock()
        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as callback_descriptor:
            injectable = tanjun.injecting.BaseInjectableCallback(mock_callback)

            callback_descriptor.assert_called_once_with(mock_callback)

        new_injectable = injectable.copy()

        assert new_injectable.callback is callback_descriptor.return_value.copy.return_value.callback
        callback_descriptor.return_value.copy.assert_called_once_with()

    def test_overwrite_callback(self):
        mock_callback = mock.Mock()
        injectable = tanjun.injecting.BaseInjectableCallback(mock.Mock())

        with mock.patch.object(tanjun.injecting, "CallbackDescriptor") as callback_descriptor:
            injectable.overwrite_callback(mock_callback)

            callback_descriptor.assert_called_once_with(mock_callback)

        assert injectable.needs_injector is callback_descriptor.return_value.needs_injector
