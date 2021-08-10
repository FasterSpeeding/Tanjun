__all__: list[str] = ["stub_class"]

import asyncio
import inspect
import typing
from unittest import mock

_T = typing.TypeVar("_T")


def stub_class(cls: type[_T], *, slots: bool = True, impl_abstract: bool = True, **namespace: typing.Any) -> type[_T]:
    if namespace:
        namespace["__slots__"] = ()

    if impl_abstract:
        for name in getattr(cls, "__abstractmethods__", None) or ():
            if name in namespace:
                continue

            value = getattr(cls, name)
            if asyncio.iscoroutinefunction(value) or inspect.iscoroutinefunction(value):
                namespace[name] = mock.AsyncMock()

            else:
                namespace[name] = mock.MagicMock()

    return type(cls.__name__, (cls,), namespace)
