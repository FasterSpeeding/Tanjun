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
"""Internal utility classes and functions used by Tanjun."""
from __future__ import annotations

import copy as copy_
import typing
from collections import abc as collections

from . import abc

_COMMAND_TREE_KEY = "comm ands"


class MessageCommandIndex:
    __slots__ = ("commands", "is_strict", "names_to_commands", "search_tree")

    def __init__(
        self,
        strict: bool,
        /,
        *,
        commands: typing.Optional[list[abc.MessageCommand[typing.Any]]] = None,
        names_to_commands: typing.Optional[dict[str, tuple[str, abc.MessageCommand[typing.Any]]]] = None,
        search_tree: typing.Optional[dict[str, typing.Any]] = None,
    ) -> None:
        self.commands = commands or []
        self.is_strict = strict
        self.names_to_commands = names_to_commands or {}
        self.search_tree = search_tree or {}

    def add(self, command: abc.MessageCommand[typing.Any], /) -> bool:
        if command in self.commands:
            return False

        if self.is_strict:
            if any(" " in name for name in command.names):
                raise ValueError("Command name cannot contain spaces for this component implementation")

            names = list(command.names)
            insensive_names = [name.casefold() for name in command.names]
            if name_conflicts := self.names_to_commands.keys() & insensive_names:
                raise ValueError(
                    "Sub-command names must be (case-insensitively) unique in a strict component. "
                    "The following conflicts were found " + ", ".join(name_conflicts)
                )

            self.names_to_commands.update((key, (name, command)) for key, name in zip(names, insensive_names))

        else:
            for name in filter(None, command.names):
                node = self.search_tree
                for chars in filter(None, name.casefold().split()):
                    try:
                        node = node[chars]

                    except KeyError:
                        node = node[chars] = {}

                try:
                    node[_COMMAND_TREE_KEY].append((name, command))
                except KeyError:
                    node[_COMMAND_TREE_KEY] = [(name, command)]

        self.commands.append(command)
        return True

    def copy(self) -> MessageCommandIndex:
        commands = {command: command.copy() for command in self.commands}
        memo = {id(command): new_command for command, new_command in commands.items()}
        return MessageCommandIndex(
            self.is_strict,
            commands=list(commands.values()),
            names_to_commands={
                key: (name, commands[command]) for key, (name, command) in self.names_to_commands.items()
            },
            search_tree=copy_.deepcopy(self.search_tree, memo),
        )

    def find(
        self, content: str, case_sensitive: bool, /
    ) -> collections.Iterator[tuple[str, abc.MessageCommand[typing.Any]]]:
        if self.is_strict:
            name = content.split(" ", 1)[0]
            if command := self.names_to_commands.get(name.casefold()):
                if not case_sensitive or command[0] == name:
                    yield name, command[1]

            return

        node = self.search_tree
        segments: list[str] = []
        for chars in content.split():
            try:
                node = node[chars.casefold()]
                segments.append(chars)

            except KeyError:
                break

        if not segments:
            return

        for index in reversed(range(1, len(segments))):
            commands = node.get(_COMMAND_TREE_KEY)
            if not commands:
                continue

            name = " ".join(segments[:index])
            if case_sensitive:
                yield from ((name, c) for n, c in commands if n == name)

            else:
                yield from ((name, c) for c in commands)

    def remove(self, command: abc.MessageCommand[typing.Any], /) -> None:
        self.commands.remove(command)

        if self.is_strict:
            for name in map(str.casefold, command.names):
                if (entry := self.names_to_commands.get(name)) and entry[1] == command:
                    del self.names_to_commands[name]

            return

        for name in filter(None, command.names):
            nodes: list[tuple[str, dict[str, typing.Any]]] = []
            node = self.search_tree
            for chars in filter(None, name.casefold().split()):
                try:
                    node = node[chars]
                    nodes.append((chars, node))

                except KeyError:
                    break

            else:
                last_node = nodes[-1][1]
                last_node[_COMMAND_TREE_KEY].remove((name, command))
                if not last_node[_COMMAND_TREE_KEY]:
                    del last_node[_COMMAND_TREE_KEY]

                nodes_iter = reversed(nodes)
                # Next is used to skip the last node since it has no child.
                next(nodes_iter)

                for (child_char, _), (_, node) in zip(reversed(nodes), nodes_iter):
                    del node[child_char]

                    if node:
                        break
