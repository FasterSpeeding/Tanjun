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
"""Implementation of a hot-reloader for Tanjun"""
from __future__ import annotations

__all__: list[str] = []

import asyncio
import datetime
import importlib.util
import logging
import pathlib
import typing
from collections import abc as collections

import alluka

from .. import abc as tanjun
from .. import errors

if typing.TYPE_CHECKING:
    import typing_extensions

    _P = typing_extensions.ParamSpec("_P")

_LOGGER = logging.getLogger("hikari.tanjun.reloader")

_DirectoryEntry = typing.Union[tuple[str, set[str]], tuple[None, set[pathlib.Path]]]
_ReloaderT = typing.TypeVar("_ReloaderT", bound="Reloader")
_T = typing.TypeVar("_T")


def _print_task_exc(
    callback: collections.Callable[_P, collections.Awaitable[_T]], /
) -> collections.Callable[_P, collections.Coroutine[typing.Any, typing.Any, _T]]:
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        try:
            return await callback(*args, **kwargs)

        except Exception as exc:
            _LOGGER.exception("Reloader crashed", exc_info=exc)
            raise exc from None

    return wrapper


class _PyPathInfo:
    __slots__ = ("sys_path", "last_modified_at")

    def __init__(self, sys_path: pathlib.Path, /, *, last_modified_at: typing.Optional[int] = None) -> None:
        self.sys_path = sys_path
        self.last_modified_at = last_modified_at


def _scan_one(path: pathlib.Path, /) -> typing.Optional[int]:
    try:
        return path.stat().st_mtime_ns

    except FileNotFoundError:  # TODO: catch other errors here like perm errors
        return None


async def _load_module(client: tanjun.Client, path: typing.Union[str, pathlib.Path], /) -> bool:
    try:
        await client.reload_modules_async(path)
        return True

    except errors.ModuleStateConflict:
        pass

    except Exception as exc:
        _LOGGER.exception(f"Failed to reload module {path}", exc_info=exc)
        return False

    try:
        await client.load_modules_async(path)
        return True

    except errors.ModuleStateConflict:
        pass

    except Exception as exc:
        _LOGGER.exception(f"Failed to reload module {path}", exc_info=exc)
        return False


class Reloader:
    __slots__ = (
        "_directories",
        "_interval",
        "_py_paths",
        "_py_path_to_sys_path",
        "_sys_paths",
        "_task",
        "_waiting_for_py",
        "_waiting_for_sys",
    )

    def __init__(
        self, *, interval: typing.Union[int, float, datetime.timedelta] = datetime.timedelta(microseconds=500000)
    ) -> None:
        if isinstance(interval, datetime.timedelta):
            interval = interval.total_seconds()

        else:
            interval = float(interval)

        self._directories: dict[pathlib.Path, _DirectoryEntry] = {}
        self._interval = interval

        self._py_paths: dict[str, _PyPathInfo] = {}
        """Dict of module paths to info of the modules being targeted."""

        self._sys_paths: dict[pathlib.Path, typing.Optional[int]] = {}
        """Dict of system paths to info of files being targeted."""

        self._task: typing.Optional[asyncio.Task[None]] = None

        self._waiting_for_py: dict[str, int] = {}
        """Dict of module paths to the new edit time of a module that's scheduled for a reload."""

        self._waiting_for_sys: dict[pathlib.Path, int] = {}
        """Dict of system paths to the new edit time of a module that's scheduled for a reload."""

    def add_to_client(self: _ReloaderT, client: tanjun.Client, /) -> _ReloaderT:
        (
            client.add_client_callback(tanjun.ClientCallbackNames.STARTED, self.start)
            .add_client_callback(tanjun.ClientCallbackNames.CLOSING, self.stop)
            .set_type_dependency(Reloader, self)
        )
        return self

    async def add_modules_async(self: _ReloaderT, *paths: typing.Union[str, pathlib.Path]) -> _ReloaderT:
        py_paths, sys_paths = await asyncio.get_running_loop().run_in_executor(None, _add_modules, paths)
        self._py_paths.update(py_paths)
        self._sys_paths.update((key, None) for key in sys_paths)
        return self

    def add_modules(self: _ReloaderT, *paths: typing.Union[str, pathlib.Path]) -> _ReloaderT:
        py_paths, sys_paths = _add_modules(paths)
        self._py_paths.update(py_paths)
        self._sys_paths.update((key, None) for key in sys_paths)
        return self

    def _add_directory_paths(self, paths: list[pathlib.Path], namespace: typing.Optional[str], /) -> _DirectoryEntry:
        if namespace is None:
            for path in paths:
                self._sys_paths[path] = None

            return (namespace, set(paths))

        results = (namespace, set[str]())
        names = results[1]
        for path in paths:
            name = _to_namespace(namespace, path)
            self._py_paths[name] = _PyPathInfo(path)
            names.add(name)

        return results

    async def add_directory_async(
        self: _ReloaderT, directory: typing.Union[str, pathlib.Path], /, *, namespace: typing.Optional[str] = None
    ) -> _ReloaderT:
        path, info = await asyncio.get_running_loop().run_in_executor(None, _add_directory, directory, namespace)
        self._directories[path] = self._add_directory_paths(info, namespace)
        return self

    def add_directory(
        self: _ReloaderT, directory: typing.Union[str, pathlib.Path], /, *, namespace: typing.Optional[str] = None
    ) -> _ReloaderT:
        path, info = _add_directory(directory, namespace)
        self._add_directory_paths(info, namespace)
        self._directories[path] = self._add_directory_paths(info, namespace)
        return self

    def _scan(self) -> tuple[dict[str, int], dict[pathlib.Path, int]]:
        for path, directory in self._directories.items():
            if directory[0] is None:
                current_paths = set(map(pathlib.Path.absolute, path.glob("*.py")))
                for old_path in directory[1] - current_paths:
                    del self._sys_paths[old_path]

                for new_path in current_paths - directory[1]:
                    self._sys_paths[new_path] = None

            else:
                current_paths = {_to_namespace(directory[0], path): path for path in path.glob("*.py")}
                for old_path in directory[1] - current_paths.keys():
                    del self._py_paths[old_path]

                for new_path in current_paths.keys() - directory[1]:
                    self._py_paths[new_path] = _PyPathInfo(current_paths[new_path])

        py_results = {
            path: result for path, sys_path in self._py_paths.items() if (result := _scan_one(sys_path.sys_path))
        }
        sys_results = {path: result for path in self._sys_paths if (result := _scan_one(path))}
        return py_results, sys_results

    async def scan(self, client: tanjun.Client, /) -> None:
        loop = asyncio.get_running_loop()
        py_paths, sys_paths = await loop.run_in_executor(None, self._scan)

        # TODO: do we want the wait_for to be on a quicker schedule
        for path, value in py_paths.items():
            if tracked_value := self._waiting_for_py.get(path):
                if value == tracked_value:
                    del self._waiting_for_py[path]
                    await _load_module(client, path)
                    self._py_paths[path].last_modified_at = value

                else:
                    self._waiting_for_py[path] = value

            elif not (path_info := self._py_paths.get(path)) or path_info.last_modified_at != value:
                self._waiting_for_py[path] = value

        for path, value in sys_paths.items():
            if tracked_value := self._waiting_for_sys.get(path):
                if value == tracked_value:
                    del self._waiting_for_sys[path]
                    await _load_module(client, path)
                    self._sys_paths[path] = value

                else:
                    self._waiting_for_sys[path] = tracked_value

            elif (new_value := self._sys_paths.get(path)) is None or new_value != value:
                self._waiting_for_sys[path] = value

    @_print_task_exc
    async def _loop(self, client: tanjun.Client, /) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self.scan(client)

    def stop(self) -> None:
        if not self._task:
            raise RuntimeError("Reloader not running")

        self._task.cancel()
        self._task = None

    def start(self, client: alluka.Injected[tanjun.Client]) -> None:
        if self._task:
            raise RuntimeError("Reloader already started")

        self._task = asyncio.create_task(self._loop(client))


def _to_namespace(namespace: str, path: pathlib.Path) -> str:
    return namespace + "." + path.name.removesuffix(".py")


def _add_directory(
    directory: typing.Union[str, pathlib.Path], namespace: typing.Optional[str]
) -> tuple[pathlib.Path, list[pathlib.Path]]:
    directory = pathlib.Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"{directory} does not exist")

    return directory.absolute(), list(map(pathlib.Path.absolute, directory.glob("*.py")))


def _add_modules(paths: tuple[typing.Union[str, pathlib.Path]]) -> tuple[dict[str, _PyPathInfo], list[pathlib.Path]]:
    py_paths: dict[str, _PyPathInfo] = {}
    sys_paths: list[pathlib.Path] = []

    for raw_path in paths:
        if isinstance(raw_path, pathlib.Path):
            if not raw_path.exists():
                raise FileNotFoundError(raw_path)

            sys_paths.append(raw_path)

        else:
            spec = importlib.util.find_spec(raw_path)
            if not spec or not spec.has_location or not spec.origin:
                raise ValueError(f"{raw_path} is not a valid module path")

            path = pathlib.Path(spec.origin).resolve()
            if not path.exists():
                raise FileNotFoundError(f"{path} not found for module {raw_path}")

            py_paths[raw_path] = _PyPathInfo(path)

    return py_paths, sys_paths
