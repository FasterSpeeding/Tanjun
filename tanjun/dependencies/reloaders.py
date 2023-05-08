# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2023, Faster Speeding
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
"""Implementation of a hot reloader for Tanjun."""
from __future__ import annotations

__all__: list[str] = ["HotReloader"]

import asyncio
import dataclasses
import datetime
import importlib
import itertools
import logging
import pathlib
import typing

import alluka
import hikari

from .. import _internal
from .. import abc as tanjun
from .. import errors

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from typing_extensions import Self

    _BuilderDict = dict[tuple[hikari.CommandType, str], hikari.api.CommandBuilder]
    _DirectoryEntry = typing.Union[tuple[str, set[str]], tuple[None, set[pathlib.Path]]]


_PathT = typing.TypeVar("_PathT", str, pathlib.Path)

_LOGGER = logging.getLogger("hikari.tanjun.reloader")


class _PyPathInfo:
    __slots__ = ("sys_path", "last_modified_at")

    def __init__(self, sys_path: pathlib.Path, /, *, last_modified_at: int = -1) -> None:
        self.sys_path = sys_path
        self.last_modified_at = last_modified_at


class HotReloader:
    """Manages hot reloading modules for a Tanjun client..

    !!! warning
        An instance of this can only be linked to 1 client.

    Examples
    --------
    ```py
    client = tanjun.Client.from_gateway_bot(bot)
    (
        tanjun.dependencies.HotReloader()
        .add_modules("python.module.path", pathlib.Path("./module.py"))
        .add_directory("./modules/")
        .add_to_client(client)
    )
    ```
    """

    __slots__ = (
        "_command_task",
        "_commands_guild",
        "_dead_unloads",
        "_declared_builders",
        "_directories",
        "_interval",
        "_py_paths",
        "_py_path_to_sys_path",
        "_redeclare_cmds_after",
        "_scheduled_builders",
        "_sys_paths",
        "_task",
        "_unload_on_delete",
        "_waiting_for_py",
        "_waiting_for_sys",
    )

    def __init__(
        self,
        *,
        commands_guild: typing.Optional[hikari.SnowflakeishOr[hikari.PartialGuild]] = None,
        interval: typing.Union[int, float, datetime.timedelta] = datetime.timedelta(microseconds=500000),
        redeclare_cmds_after: typing.Union[int, float, datetime.timedelta, None] = datetime.timedelta(seconds=10),
        unload_on_delete: bool = True,
    ) -> None:
        r"""Initialise a hot reloader.

        !!! warning
            `redeclare_cmds_after` is not aware of commands declared outside of
            the reloader and will lead to commands being redeclared on startup
            when mixed with [tanjun.clients.Client.\_\_init\_\_][tanjun.clients.Client.__init__]'s
            `declare_global_commands` argument when it is not [None][].

        Parameters
        ----------
        commands_guild
            Object or ID of the guild to declare commands in if `redeclare_cmds_after`
            is not [None][].
        interval
            How often this should scan files and directories for changes in seconds.
        redeclare_cmds_after
            How often to redeclare application commands after a change to the commands
            is detected.

            If [None][] is passed here then this will not redeclare the application's
            commands.
        unload_on_delete
            Whether this should unload modules when their relevant file is deleted.
        """
        if redeclare_cmds_after is None:
            pass

        elif isinstance(redeclare_cmds_after, datetime.timedelta):
            redeclare_cmds_after = redeclare_cmds_after.total_seconds()

        else:
            redeclare_cmds_after = float(redeclare_cmds_after)

        self._command_task: typing.Optional[asyncio.Task[None]] = None
        self._commands_guild: hikari.UndefinedOr[hikari.Snowflake]  # MyPy was resolving this to object cause MyPy
        self._commands_guild = hikari.UNDEFINED if commands_guild is None else hikari.Snowflake(commands_guild)
        self._dead_unloads: set[typing.Union[str, pathlib.Path]] = set()
        """Set of modules which cannot be unloaded."""
        self._declared_builders: _BuilderDict = {}
        """State of the last declared builders."""

        self._directories: dict[pathlib.Path, _DirectoryEntry] = {}
        """Dict of paths to the metadata of tracked directories."""

        self._interval = interval.total_seconds() if isinstance(interval, datetime.timedelta) else float(interval)
        self._py_paths: dict[str, _PyPathInfo] = {}
        """Dict of module paths to info of the modules being targeted."""

        self._redeclare_cmds_after = redeclare_cmds_after
        self._scheduled_builders: _BuilderDict = {}
        """State of the builders to be declared next."""

        self._sys_paths: dict[pathlib.Path, _PyPathInfo] = {}
        """Dict of system paths to info of files being targeted."""

        self._task: typing.Optional[asyncio.Task[None]] = None
        self._unload_on_delete = unload_on_delete

        self._waiting_for_py: dict[str, int] = {}
        """Dict of module paths to the new edit time of a module that's scheduled for a reload."""

        self._waiting_for_sys: dict[pathlib.Path, int] = {}
        """Dict of system paths to the new edit time of a module that's scheduled for a reload."""

    def add_to_client(self, client: tanjun.Client, /) -> None:
        """Add this to a [tanjun.abc.Client][] instance.

        This registers start and closing callbacks which handle the lifetime of
        this and adds this as a type dependency.

        Parameters
        ----------
        client
            The client to link this hot reloader to.
        """
        (
            client.add_client_callback(tanjun.ClientCallbackNames.STARTED, self.start)
            .add_client_callback(tanjun.ClientCallbackNames.CLOSING, self.stop)
            .set_type_dependency(HotReloader, self)
        )
        if client.is_alive and client.loop:
            client.loop.call_soon_threadsafe(self.start, client)

    async def add_modules_async(self, *paths: typing.Union[str, pathlib.Path]) -> Self:
        """Asynchronous variant of [HotReloader.add_modules][tanjun.dependencies.reloaders.HotReloader.add_modules].

        Unlike [HotReloader.add_modules][tanjun.dependencies.reloaders.HotReloader.add_modules],
        this method will run blocking code in a background thread.

        For more information on the behaviour of this method see the
        documentation for [HotReloader.add_modules][tanjun.dependencies.reloaders.HotReloader.add_modules].
        """
        py_paths, sys_paths = await asyncio.get_running_loop().run_in_executor(None, _add_modules, paths)
        self._py_paths.update(py_paths)
        self._sys_paths.update((key, _PyPathInfo(key)) for key in sys_paths)
        return self

    def add_modules(self, *paths: typing.Union[str, pathlib.Path]) -> Self:
        """Add modules for this hot reloader to track.

        Parameters
        ----------
        *paths
            Module paths for this hot reloader to track.

            This has the same behaviour as [tanjun.abc.Client.load_modules][
            for how [pathlib.Path][] and [str][] are treated.

        Raises
        ------
        FileNotFoundError
            If the module's file doesn't exist anymore.
        ModuleNotFoundError
            If the [str][] module path cannot be imported.
        """
        py_paths, sys_paths = _add_modules(paths)
        self._py_paths.update(py_paths)
        self._sys_paths.update((key, _PyPathInfo(key)) for key in sys_paths)
        return self

    async def add_directory_async(
        self, directory: typing.Union[str, pathlib.Path], /, *, namespace: typing.Optional[str] = None
    ) -> Self:
        """Asynchronous variant of [HotReloader.add_directory][tanjun.dependencies.reloaders.HotReloader.add_directory].

        Unlike [HotReloader.add_directory][tanjun.dependencies.reloaders.HotReloader.add_directory],
        this method will run blocking code in a background thread.

        For more information on the behaviour of this method see the
        documentation for [HotReloader.add_directory][tanjun.dependencies.reloaders.HotReloader.add_directory].
        """
        path, info = await asyncio.get_running_loop().run_in_executor(None, _add_directory, directory, namespace)
        self._directories[path] = info
        return self

    def add_directory(
        self, directory: typing.Union[str, pathlib.Path], /, *, namespace: typing.Optional[str] = None
    ) -> Self:
        """Add a directory for this hot reloader to track.

        !!! note
            This will only reload modules directly in the target directory and
            will not scan sub-directories.

        Parameters
        ----------
        directory
            Path of the directory to hot reload.
        namespace
            The python namespace this directory's modules should be imported
            from, if applicable.

            This work as `{namespace}.{file.name.removesuffix(".py")}` and will
            have the same behaviour as when a [str][] is passed to
            [Client.load_modules][tanjun.abc.Client.load_modules] if passed.

            If left as [None][] then this will have the same behaviour as when
            a [pathlib.Path][] is passed to
            [Client.load_modules][tanjun.abc.Client.load_modules].


        Returns
        -------
        Self
            The hot reloader to enable chained calls.

        Raises
        ------
        FileNotFoundError
            If the directory cannot be found
        """
        path, info = _add_directory(directory, namespace)
        self._directories[path] = info
        return self

    async def _load_module(self, client: tanjun.Client, path: typing.Union[str, pathlib.Path], /) -> bool:
        for method in (client.reload_modules_async, client.load_modules_async):
            try:
                await method(path)

            except errors.ModuleStateConflict:
                pass

            except errors.FailedModuleLoad as exc:
                _LOGGER.exception("Failed to load module `%s`", path, exc_info=exc.__cause__)
                return False

            except errors.ModuleMissingLoaders:
                _LOGGER.error("Cannot load module `%s` with no loaders", path)  # noqa: TC400
                return False

            except errors.FailedModuleUnload as exc:
                self._dead_unloads.add(path)
                _LOGGER.exception(
                    "Failed to unload module `%s`; hot reloading is now disabled for this module",
                    path,
                    exc_info=exc.__cause__,
                )
                return False

            except errors.ModuleMissingUnloaders:
                self._dead_unloads.add(path)
                _LOGGER.exception(
                    "Cannot reload module `%s` with no unloaders; hot reloading is now disabled for this module", path
                )
                return False

            else:
                return True

        return False

    def _unload_module(self, client: tanjun.Client, path: typing.Union[str, pathlib.Path], /) -> bool:
        try:
            client.unload_modules(path)

        except errors.ModuleStateConflict:
            return True

        except errors.FailedModuleUnload as exc:
            _LOGGER.exception(
                "Failed to unload module `%s`; hot reloading is now disabled for this module",
                path,
                exc_info=exc.__cause__,
            )

        except errors.ModuleMissingUnloaders:
            _LOGGER.exception(
                "Cannot unload module `%s` with no unloaders; hot reloading is now disabled for this module", path
            )

        else:
            return True

        self._dead_unloads.add(path)
        return False

    def _scan(self) -> _ScanResult:
        result = _ScanResult()
        py_scanner = _PathScanner[str](self._py_paths, self._dead_unloads, result.py_paths, result.removed_py_paths)
        sys_scanner = _PathScanner[pathlib.Path](
            self._sys_paths, self._dead_unloads, result.sys_paths, result.removed_sys_paths
        )

        for path, directory in self._directories.copy().items():
            if directory[0] is None:
                current_paths: set[pathlib.Path] = set(
                    filter(pathlib.Path.is_file, map(pathlib.Path.resolve, path.glob("*.py")))
                )
                sys_scanner.process_directory(
                    current_paths, current_paths.remove, ((v, v) for v in current_paths - directory[1])
                )

            else:
                str_paths = {_to_namespace(directory[0], path): path for path in path.glob("*.py") if path.is_file()}
                py_scanner.process_directory(
                    str_paths, str_paths.__delitem__, ((v, str_paths[v]) for v in str_paths.keys() - directory[1])
                )

        sys_scanner.process()
        py_scanner.process()
        return result

    async def scan(self, client: tanjun.Client, /) -> None:  # TODO: maybe don't load pass the Client here?
        """Manually scan this hot reloader's tracked modules for changes.

        Parameters
        ----------
        client
            The client to reload and unload modules in.
        """
        loop = asyncio.get_running_loop()
        scan_result = await loop.run_in_executor(None, self._scan)
        py_loader = _PathLoader[str](self._waiting_for_py, self._py_paths, self._load_module, self._unload_module)
        sys_loader = _PathLoader[pathlib.Path](
            self._waiting_for_sys, self._sys_paths, self._load_module, self._unload_module
        )

        # TODO: do we want the wait_for to be on a quicker schedule
        await py_loader.process_results(client, scan_result.py_paths.items())
        await sys_loader.process_results(client, scan_result.sys_paths.items())

        if self._unload_on_delete:
            py_loader.remove_results(client, scan_result.removed_py_paths)
            sys_loader.remove_results(client, scan_result.removed_sys_paths)

        if not (py_loader.changed or sys_loader.changed) or self._redeclare_cmds_after is None:
            return

        builders: _BuilderDict = {
            (cmd.type, cmd.name): cmd.build()
            for cmd in list(
                itertools.chain(
                    client.iter_menu_commands(global_only=True), client.iter_slash_commands(global_only=True)
                )
            )
        }
        if self._command_task:
            self._scheduled_builders = builders

        elif builders != self._declared_builders:
            self._scheduled_builders = builders
            self._command_task = loop.create_task(self._declare_commands(client, builders))
            self._command_task.add_done_callback(self._clear_command_task)

    def _clear_command_task(self, _: asyncio.Task[None], /) -> None:
        self._command_task = None

    async def _declare_commands(self, client: tanjun.Client, builders: _BuilderDict, /) -> None:
        assert self._redeclare_cmds_after is not None
        await asyncio.sleep(self._redeclare_cmds_after)

        while True:
            if not _internal.cmp_all_commands(builders.values(), self._scheduled_builders):
                builders = self._scheduled_builders
                try:
                    await asyncio.sleep(self._redeclare_cmds_after)

                except BaseException:
                    self._declared_builders = builders
                    raise

                continue

            if _internal.cmp_all_commands(builders.values(), self._declared_builders):
                return

            try:
                await client.declare_application_commands(builders.values(), guild=self._commands_guild)

            except hikari.RateLimitTooLongError as exc:
                _LOGGER.exception("Timed out on command declare, will try again soon", exc_info=exc)

            except Exception as exc:
                resource = f"guild ({self._command_task})" if self._commands_guild else "global"
                _LOGGER.exception("Failed to declare %s commands", resource, exc_info=exc)
                self._declared_builders = builders
                if _internal.cmp_all_commands(builders.values(), self._scheduled_builders):
                    return

            except BaseException:
                self._declared_builders = builders
                raise

            else:
                self._declared_builders = builders
                if _internal.cmp_all_commands(builders.values(), self._scheduled_builders):
                    return

    @_internal.log_task_exc("Hot reloader crashed")
    async def _loop(self, client: tanjun.Client, /) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self.scan(client)

    def stop(self) -> None:
        """Stop the hot reloader.

        Raises
        ------
        RuntimeError
            If the hot reloader isn't running.
        """
        if not self._task:
            raise RuntimeError("Hot reloader is not running")

        self._task.cancel()
        self._task = None

    def start(self, client: alluka.Injected[tanjun.Client]) -> None:
        """Start the hot reloader.

        Raises
        ------
        RuntimeError
            If the hot reloader is already running.
        """
        if self._task:
            raise RuntimeError("Hot reloader has already been started")

        self._task = asyncio.create_task(self._loop(client))


def _to_namespace(namespace: str, path: pathlib.Path, /) -> str:
    return namespace + "." + path.name.removesuffix(".py")


def _add_directory(
    directory: typing.Union[str, pathlib.Path], namespace: typing.Optional[str], /
) -> tuple[pathlib.Path, _DirectoryEntry]:
    directory = pathlib.Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"{directory} does not exist")

    return directory.resolve(), (namespace, set()) if namespace is None else (namespace, set())


def _add_modules(
    paths: tuple[typing.Union[str, pathlib.Path], ...], /
) -> tuple[dict[str, _PyPathInfo], list[pathlib.Path]]:
    py_paths: dict[str, _PyPathInfo] = {}
    sys_paths: list[pathlib.Path] = []

    for raw_path in paths:
        if isinstance(raw_path, pathlib.Path):
            if not raw_path.exists():
                raise FileNotFoundError(raw_path)

            sys_paths.append(raw_path)

        else:
            module = importlib.import_module(raw_path)
            if not module.__file__:
                raise RuntimeError(f"{raw_path} has no file")

            path = pathlib.Path(module.__file__).resolve()
            if not path.exists():
                raise FileNotFoundError(f"{path} not found for module {raw_path}")

            py_paths[raw_path] = _PyPathInfo(path)

    return py_paths, sys_paths


def _scan_one(path: pathlib.Path, /) -> typing.Optional[int]:
    try:
        return path.stat().st_mtime_ns

    except FileNotFoundError:  # TODO: catch other errors here like perm errors
        return None  # MyPy compat


@dataclasses.dataclass
class _ScanResult:
    py_paths: dict[str, _PyPathInfo] = dataclasses.field(init=False, default_factory=dict)
    removed_py_paths: list[str] = dataclasses.field(init=False, default_factory=list)
    removed_sys_paths: list[pathlib.Path] = dataclasses.field(init=False, default_factory=list)
    sys_paths: dict[pathlib.Path, _PyPathInfo] = dataclasses.field(init=False, default_factory=dict)


@dataclasses.dataclass
class _PathScanner(typing.Generic[_PathT]):
    __slots__ = ("dead_unloads", "global_paths", "removed_paths", "result_paths")

    global_paths: dict[_PathT, _PyPathInfo]
    dead_unloads: set[typing.Union[str, pathlib.Path]]
    result_paths: dict[_PathT, _PyPathInfo]
    removed_paths: list[_PathT]

    def process_directory(
        self,
        current_paths: collections.Collection[_PathT],
        remove_path: collections.Callable[[_PathT], None],
        new_paths: collections.Iterable[tuple[_PathT, pathlib.Path]],
        /,
    ) -> None:
        for path, real_path in new_paths:
            if path in self.dead_unloads:
                continue

            if time := _scan_one(real_path):
                self.result_paths[path] = _PyPathInfo(real_path, last_modified_at=time)

            elif path in current_paths:
                remove_path(path)
                self.removed_paths.append(path)

    def process(self) -> None:
        for path, info in self.global_paths.copy().items():
            if path in self.dead_unloads:
                continue

            if time := _scan_one(info.sys_path):
                self.result_paths[path] = _PyPathInfo(info.sys_path, last_modified_at=time)

            elif info.last_modified_at != -1:
                self.removed_paths.append(path)


@dataclasses.dataclass
class _PathLoader(typing.Generic[_PathT]):
    waiting_for: dict[_PathT, int]
    paths: dict[_PathT, _PyPathInfo]
    load_module: collections.Callable[
        [tanjun.Client, typing.Union[str, pathlib.Path]], collections.Coroutine[typing.Any, typing.Any, bool]
    ]
    unload_module: collections.Callable[[tanjun.Client, typing.Union[str, pathlib.Path]], bool]
    changed: bool = dataclasses.field(default=False, init=False)

    async def process_results(
        self, client: tanjun.Client, results: collections.Iterable[tuple[_PathT, _PyPathInfo]], /
    ) -> None:
        for path, value in results:
            if tracked_value := self.waiting_for.get(path):
                if value.last_modified_at == tracked_value:
                    del self.waiting_for[path]
                    result = await self.load_module(client, path)
                    self.changed = result or self.changed
                    self.paths[path] = value

                else:
                    self.waiting_for[path] = value.last_modified_at

            elif not (path_info := self.paths.get(path)) or path_info.last_modified_at != value.last_modified_at:
                self.waiting_for[path] = value.last_modified_at

    def remove_results(self, client: tanjun.Client, results: collections.Iterable[_PathT], /) -> None:
        for path in results:
            self.unload_module(client, path)
            self.paths[path].last_modified_at = -1
