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
"""Manager which keeps tasks in-scope and alive until they are finished."""
from __future__ import annotations

__all__: list[str] = ["AbstractTaskManager", "AsyncioTaskManager"]

import abc
import asyncio
import datetime
import logging
import typing
import uuid
from collections import abc as collections

from .. import abc as tanjun_abc
from .. import injecting

if typing.TYPE_CHECKING:
    import typing_extensions

    _P = typing_extensions.ParamSpec("_P")


_LOGGER = logging.getLogger("tanjun.dependencies.manager")


class AbstractTaskInfo(abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def group_id(self) -> typing.Optional[str]:
        """The group ID of the task."""

    @property
    @abc.abstractmethod
    def started_at(self) -> datetime.datetime:
        """The time at which the task was started."""

    @property
    @abc.abstractmethod
    def task_id(self) -> str:
        """The unique ID of the task."""


class AbstractTaskManager(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    async def add_task(
        self,
        callback: collections.Callable[_P, collections.Awaitable[typing.Any]],
        task_id: typing.Optional[str] = None,
        group_id: typing.Optional[str] = None,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> str:
        ...

    @abc.abstractmethod
    async def get_group(self, task_id: str, /) -> collections.Sequence[AbstractTaskInfo]:
        ...

    @abc.abstractmethod
    async def get_task(self, task_id: str, /) -> typing.Optional[AbstractTaskInfo]:
        ...

    @abc.abstractmethod
    async def stop_group(self, task_id: str, /) -> int:
        ...

    @abc.abstractmethod
    async def stop_task(self, task_id: str, /) -> bool:
        ...

    @abc.abstractmethod
    async def wait_for_task(self, task_id: str, /) -> bool:
        ...


class _TaskData:
    __slots__ = ("group_id", "started_at", "task", "task_id")

    def __init__(self, task_id: str, group_id: typing.Optional[str], task: asyncio.Task[typing.Any], /) -> None:
        self.group_id = group_id
        self.started_at = datetime.datetime.now(tz=datetime.timezone.utc)
        self.task = task
        self.task_id = task_id

    def to_public(self) -> _TaskInfo:
        return _TaskInfo(self)


class _TaskInfo(AbstractTaskInfo):
    __slots__ = "_task_data"

    def __init__(self, data: _TaskData, /) -> None:
        self._task_data = data

    @property
    def group_id(self) -> typing.Optional[str]:
        return self._task_data.group_id

    @property
    def started_at(self) -> datetime.datetime:
        return self._task_data.started_at

    @property
    def task_id(self) -> str:
        return self._task_data.task_id


class AsyncioTaskManager(AbstractTaskManager):
    __slots__ = ("_event_loop", "_groups", "_loop_task", "_tasks")

    def __init__(self) -> None:
        self._event_loop: typing.Optional[asyncio.AbstractEventLoop] = None
        self._groups: dict[str, set[str]] = {}
        self._loop_task: typing.Optional[asyncio.Task[None]]
        self._tasks: dict[str, _TaskData] = {}

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._event_loop:
            return self._event_loop

        raise RuntimeError("Task manager is inactive.")

    async def _loop(self):
        await asyncio.sleep(60)
        for task_id, task_info in self._tasks.copy().items():
            if not task_info.task.done():
                continue

            if exc := task_info.task.exception():
                _LOGGER.error("Task failed with exception", exc_info=exc)

            del self._tasks[task_id]
            if task_info.group_id:
                self._groups[task_info.group_id].remove(task_id)
                if not self._groups[task_info.group_id]:
                    del self._groups[task_info.group_id]

    def add_to_client(self, client: tanjun_abc.Client, /) -> None:
        # TODO: upgrade this to the client
        assert isinstance(client, injecting.InjectorClient)
        (
            client.set_type_dependency(type(self), self)
            .set_type_dependency(AsyncioTaskManager, self)
            .set_type_dependency(AbstractTaskManager, self)
            .add_client_callback(tanjun_abc.ClientCallbackNames.STARTING, self.start)
            .add_client_callback(tanjun_abc.ClientCallbackNames.CLOSING, self.close)
        )

    async def add_task(
        self,
        callback: collections.Callable[_P, collections.Awaitable[typing.Any]],
        task_id: typing.Optional[str] = None,
        group_id: typing.Optional[str] = None,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> str:
        return self.add_task_sync(callback, task_id, group_id, *args, **kwargs)

    def add_task_sync(
        self,
        callback: collections.Callable[_P, collections.Awaitable[typing.Any]],
        task_id: typing.Optional[str] = None,
        group_id: typing.Optional[str] = None,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> str:
        task_id = task_id or str(uuid.uuid4())
        task = self._get_loop().create_task(callback(*args, **kwargs))

        self._tasks[task_id] = _TaskData(task_id, group_id, task)
        if group_id:
            try:
                self._groups[group_id].add(task_id)
            except KeyError:
                self._groups[group_id] = {task_id}

        return task_id

    def get_group_sync(self, group_id: str, /) -> collections.Sequence[AbstractTaskInfo]:
        if task_ids := self._groups.get(group_id):
            return [task.to_public() for task in map(self._tasks.__getitem__, task_ids) if not task.task.done()]

        return []

    async def get_group(self, group_id: str, /) -> collections.Sequence[AbstractTaskInfo]:
        return self.get_group_sync(group_id)

    def get_task_sync(self, task_id: str, /) -> typing.Optional[AbstractTaskInfo]:
        if (task_info := self._tasks.get(task_id)) and not task_info.task.done():
            return task_info.to_public()

    async def get_task(self, task_id: str, /) -> typing.Optional[AbstractTaskInfo]:
        return self.get_task_sync(task_id)

    def stop_group_sync(self, group_id: str, /) -> int:
        result = 0
        if task_ids := self._groups.get(group_id):
            for task in map(self._tasks.__getitem__, task_ids):
                if not task.task.done():
                    task.task.cancel()
                    result += 1

        return result

    async def stop_group(self, group_id: str, /) -> int:
        return self.stop_group_sync(group_id)

    def stop_task_sync(self, task_id: str, /) -> bool:
        if (task_info := self._tasks.get(task_id)) and not task_info.task.done():
            task_info.task.cancel()
            return True

        return False

    async def stop_task(self, task_id: str, /) -> bool:
        return self.stop_task_sync(task_id)

    async def wait_for_task(self, task_id: str, /) -> bool:
        task_info = self._tasks.get(task_id)
        if not task_info or task_info.task.done():
            return False

        try:
            await task_info.task

        except (Exception, asyncio.CancelledError):
            pass

        return True

    async def close(self, force: bool = False) -> None:
        self._get_loop()
        assert self._loop_task
        self._event_loop = None
        self._loop_task.cancel()
        self._loop_task = None

        tasks = (task_info.task for task_info in self._tasks.values())

        if force:
            for task in tasks:
                if task.done() and (exc := task.exception()):
                    _LOGGER.error("Task failed with exception", exc_info=exc)

                else:
                    task.cancel()

        else:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    _LOGGER.error("Task failed with exception", exc_info=result)

        self._tasks.clear()

    def start(self) -> None:
        if self._event_loop:
            raise RuntimeError("Task manager is already active.")

        self._event_loop = asyncio.get_running_loop()
        self._event_loop.create_task(self._loop())
