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
"""Message command implementation."""
from __future__ import annotations

__all__: list[str] = ["MessageContext"]

import asyncio
import datetime
import logging
import typing

import hikari

from .. import abc as tanjun
from . import base

if typing.TYPE_CHECKING:
    from collections import abc as collections

    from typing_extensions import Self


_LOGGER = logging.getLogger("hikari.tanjun.context")


def _delete_after_to_float(delete_after: typing.Union[datetime.timedelta, float, int]) -> float:
    return delete_after.total_seconds() if isinstance(delete_after, datetime.timedelta) else float(delete_after)


class MessageContext(base.BaseContext, tanjun.MessageContext):
    """Standard implementation of a command context as used within Tanjun."""

    __slots__ = (
        "_command",
        "_content",
        "_initial_response_id",
        "_last_response_id",
        "_register_task",
        "_response_lock",
        "_message",
        "_triggering_name",
        "_triggering_prefix",
    )

    def __init__(
        self,
        client: tanjun.Client,
        content: str,
        message: hikari.Message,
        register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
        *,
        triggering_name: str = "",
        triggering_prefix: str = "",
    ) -> None:
        """Initialise a message command context.

        Parameters
        ----------
        client
            The client to use for sending messages.
        content
            The content of the message (minus any matched prefix and name).
        message
            The message that triggered the command.
        register_task
            Callback used to register long-running tasks spawned by this context.
        triggering_name
            The name of the command that triggered this context.
        triggering_prefix
            The prefix that triggered this context.
        """
        if message.content is None:
            raise ValueError("Cannot spawn context with a content-less message.")

        super().__init__(client)
        self._command: typing.Optional[tanjun.MessageCommand[typing.Any]] = None
        self._content = content
        self._initial_response_id: typing.Optional[hikari.Snowflake] = None
        self._last_response_id: typing.Optional[hikari.Snowflake] = None
        self._register_task = register_task
        self._response_lock = asyncio.Lock()
        self._message = message
        self._triggering_name = triggering_name
        self._triggering_prefix = triggering_prefix
        self._set_type_special_case(tanjun.MessageContext, self)._set_type_special_case(MessageContext, self)

    def __repr__(self) -> str:
        return f"MessageContext <{self._message!r}, {self._command!r}>"

    @property
    def author(self) -> hikari.User:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._message.author

    @property
    def channel_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._message.channel_id

    @property
    def command(self) -> typing.Optional[tanjun.MessageCommand[typing.Any]]:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        return self._command

    @property
    def content(self) -> str:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        return self._content

    @property
    def created_at(self) -> datetime.datetime:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._message.created_at

    @property
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._message.guild_id

    @property
    def has_responded(self) -> bool:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._initial_response_id is not None

    @property
    def is_human(self) -> bool:
        # <<inherited docstring from tanjun.abc.Context>>.
        return not self._message.author.is_bot and self._message.webhook_id is None

    @property
    def member(self) -> typing.Optional[hikari.Member]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._message.member

    @property
    def message(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        return self._message

    @property
    def triggering_name(self) -> str:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._triggering_name

    @property
    def triggering_prefix(self) -> str:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        return self._triggering_prefix

    def set_command(self, command: typing.Optional[tanjun.MessageCommand[typing.Any]], /) -> Self:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        self._assert_not_final()
        if command:
            # TODO: command group?
            self._set_type_special_case(tanjun.ExecutableCommand, command)._set_type_special_case(
                tanjun.MessageCommand, command
            )

        elif self._command:
            self._remove_type_special_case(tanjun.ExecutableCommand)._remove_type_special_case(tanjun.MessageCommand)

        self._command = command
        return self

    def set_content(self, content: str, /) -> Self:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        self._assert_not_final()
        self._content = content
        return self

    def set_triggering_name(self, name: str, /) -> Self:
        # <<inherited docstring from tanjun.abc.MessageContext>>.
        self._assert_not_final()
        self._triggering_name = name
        return self

    def set_triggering_prefix(self, triggering_prefix: str, /) -> Self:
        """Set the triggering prefix for this context.

        Parameters
        ----------
        triggering_prefix
            The triggering prefix to set.

        Returns
        -------
        Self
            This context to allow for chaining.
        """
        self._assert_not_final()
        self._triggering_prefix = triggering_prefix
        return self

    async def delete_initial_response(self) -> None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._initial_response_id is None:
            raise LookupError("Context has no initial response")

        await self._client.rest.delete_message(self._message.channel_id, self._initial_response_id)

    async def delete_last_response(self) -> None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._last_response_id is None:
            raise LookupError("Context has no previous responses")

        await self._client.rest.delete_message(self._message.channel_id, self._last_response_id)

    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        delete_after = _delete_after_to_float(delete_after) if delete_after is not None else None
        if self._initial_response_id is None:
            raise LookupError("Context has no initial response")

        message = await self.rest.edit_message(
            self._message.channel_id,
            self._initial_response_id,
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )
        if delete_after is not None:
            self._register_task(asyncio.create_task(self._delete_after(delete_after, message)))

        return message

    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        delete_after = _delete_after_to_float(delete_after) if delete_after is not None else None
        if self._last_response_id is None:
            raise LookupError("Context has no previous tracked response")

        message = await self.rest.edit_message(
            self._message.channel_id,
            self._last_response_id,
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )

        if delete_after is not None:
            self._register_task(asyncio.create_task(self._delete_after(delete_after, message)))

        return message

    async def fetch_initial_response(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._initial_response_id is not None:
            return await self.client.rest.fetch_message(self._message.channel_id, self._initial_response_id)

        raise LookupError("No initial response found for this context")

    async def fetch_last_response(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._last_response_id is not None:
            return await self.client.rest.fetch_message(self._message.channel_id, self._last_response_id)

        raise LookupError("No responses found for this context")

    @staticmethod
    async def _delete_after(delete_after: float, message: hikari.Message) -> None:
        await asyncio.sleep(delete_after)
        try:
            await message.delete()
        except hikari.NotFoundError as exc:
            _LOGGER.debug("Failed to delete response message after %.2f seconds", delete_after, exc_info=exc)

    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = True,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        reply: typing.Union[bool, hikari.SnowflakeishOr[hikari.PartialMessage], hikari.UndefinedType] = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        mentions_reply: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        delete_after = _delete_after_to_float(delete_after) if delete_after is not None else None
        async with self._response_lock:
            message = await self._message.respond(
                content=content,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                tts=tts,
                reply=reply,
                mentions_everyone=mentions_everyone,
                mentions_reply=mentions_reply,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )
            self._last_response_id = message.id
            if self._initial_response_id is None:
                self._initial_response_id = message.id

            if delete_after is not None:
                self._register_task(asyncio.create_task(self._delete_after(delete_after, message)))

            return message
