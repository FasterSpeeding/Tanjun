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
"""Slash command implementation."""
from __future__ import annotations

__all__: list[str] = ["SlashContext", "SlashOption"]

import asyncio
import datetime
import logging
import os
import typing

import hikari

from tanjun import _internal
from tanjun import abc as tanjun

from . import base

if typing.TYPE_CHECKING:
    from collections import abc as collections
    from typing import Self

    _ResponseTypeT = (
        hikari.api.InteractionMessageBuilder
        | hikari.api.InteractionDeferredBuilder
        | hikari.api.InteractionModalBuilder
    )
    _T = typing.TypeVar("_T")
    _OtherT = typing.TypeVar("_OtherT")


_INTERACTION_LIFETIME: typing.Final[datetime.timedelta] = datetime.timedelta(minutes=15)
_LOGGER = logging.getLogger("hikari.tanjun.context")


def _delete_after_to_float(delete_after: datetime.timedelta | float | int, /) -> float:
    return delete_after.total_seconds() if isinstance(delete_after, datetime.timedelta) else float(delete_after)


_SnowflakeOptions = frozenset(
    [
        hikari.OptionType.ATTACHMENT,
        hikari.OptionType.USER,
        hikari.OptionType.MENTIONABLE,
        hikari.OptionType.ROLE,
        hikari.OptionType.CHANNEL,
    ]
)


class SlashOption(tanjun.SlashOption):
    """Standard implementation of the SlashOption interface."""

    __slots__ = ("_option", "_resolved")

    def __init__(self, resolved: hikari.ResolvedOptionData | None, option: hikari.CommandInteractionOption, /) -> None:
        """Initialise a slash option.

        Parameters
        ----------
        resolved
            The resolved option data if applicable.
        option
            The raw interaction option.
        """
        if option.value is None:
            error_message = "Cannot build a slash option with a value-less API representation"
            raise ValueError(error_message)

        self._option = option
        self._resolved = resolved

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        return self._option.name

    @property
    def type(self) -> hikari.OptionType | int:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        return self._option.type

    @property
    def value(self) -> str | int | hikari.Snowflake | bool | float:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        # This is asserted in __init__
        assert self._option.value is not None
        if self._option.type in _SnowflakeOptions:
            return hikari.Snowflake(self._option.value)

        return self._option.value

    def boolean(self) -> bool:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.BOOLEAN:
            return bool(self._option.value)

        error_message = "Option is not a boolean"
        raise TypeError(error_message)

    def float(self) -> float:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.FLOAT:
            assert self._option.value is not None
            return float(self._option.value)

        error_message = "Option is not a float"
        raise TypeError(error_message)

    def integer(self) -> int:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.INTEGER:
            assert self._option.value is not None
            return int(self._option.value)

        error_message = "Option is not an integer"
        raise TypeError(error_message)

    def snowflake(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type in _SnowflakeOptions:
            assert self._option.value is not None
            return hikari.Snowflake(self._option.value)

        error_message = "Option is not a unique resource"
        raise TypeError(error_message)

    def string(self) -> str:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.STRING:
            return str(self._option.value)

        error_message = "Option is not a string"
        raise TypeError(error_message)

    def resolve_value(
        self,
    ) -> hikari.Attachment | hikari.InteractionChannel | hikari.InteractionMember | hikari.Role | hikari.User:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.CHANNEL:
            return self.resolve_to_channel()

        if self._option.type is hikari.OptionType.ROLE:
            return self.resolve_to_role()

        if self._option.type is hikari.OptionType.USER:
            return self.resolve_to_user()

        if self._option.type is hikari.OptionType.ATTACHMENT:
            return self.resolve_to_attachment()

        if self._option.type is hikari.OptionType.MENTIONABLE:
            return self.resolve_to_mentionable()

        error_message = f"Option type {self._option.type} isn't resolvable"
        raise TypeError(error_message)

    def resolve_to_attachment(self) -> hikari.Attachment:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.ATTACHMENT:
            assert self._option.value is not None
            assert self._resolved
            return self._resolved.attachments[hikari.Snowflake(self._option.value)]

        error_message = f"Cannot resolve non-attachment type {self._option.type} to an attachment"
        raise TypeError(error_message)

    def resolve_to_channel(self) -> hikari.InteractionChannel:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        # What does self.value being None mean?
        if self._option.type is hikari.OptionType.CHANNEL:
            assert self._option.value is not None
            assert self._resolved
            return self._resolved.channels[hikari.Snowflake(self._option.value)]

        error_message = f"Cannot resolve non-channel option type {self._option.type} to a channel"
        raise TypeError(error_message)

    @typing.overload
    def resolve_to_member(self) -> hikari.InteractionMember: ...

    @typing.overload
    def resolve_to_member(self, *, default: _T) -> hikari.InteractionMember | _T: ...

    def resolve_to_member(
        self, *, default: _T | _internal.Default = _internal.DEFAULT
    ) -> hikari.InteractionMember | _T:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        # What does self.value being None mean?
        if self._option.type is hikari.OptionType.USER:
            assert self._option.value is not None
            assert self._resolved
            if member := self._resolved.members.get(hikari.Snowflake(self._option.value)):
                return member

            if default is not _internal.DEFAULT:
                return default

            error_message = "User isn't in the current guild"
            raise LookupError(error_message) from None

        if self._option.type is hikari.OptionType.MENTIONABLE:
            assert self._option.value is not None
            assert self._resolved
            target_id = hikari.Snowflake(self._option.value)
            if member := self._resolved.members.get(target_id):
                return member

            if target_id in self._resolved.users:
                if default is not _internal.DEFAULT:
                    return default

                error_message = "User isn't in the current guild"
                raise LookupError(error_message)

        error_message = f"Cannot resolve non-user option type {self._option.type} to a member"
        raise TypeError(error_message)

    def resolve_to_mentionable(self) -> hikari.Role | hikari.User | hikari.Member:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.MENTIONABLE:
            assert self._option.value is not None
            assert self._resolved
            target_id = hikari.Snowflake(self._option.value)
            if role := self._resolved.roles.get(target_id):
                return role

            return self._resolved.members.get(target_id) or self._resolved.users[target_id]

        if self._option.type is hikari.OptionType.USER:
            return self.resolve_to_user()

        if self._option.type is hikari.OptionType.ROLE:
            return self.resolve_to_role()

        error_message = f"Cannot resolve non-mentionable option type {self._option.type} to a mentionable entity."
        raise TypeError(error_message)

    def resolve_to_role(self) -> hikari.Role:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.ROLE:
            assert self._option.value is not None
            assert self._resolved
            return self._resolved.roles[hikari.Snowflake(self._option.value)]

        if self._option.type is hikari.OptionType.MENTIONABLE and self._resolved:
            role = self._resolved.roles.get(hikari.Snowflake(self.value))
            if role:
                return role

        error_message = f"Cannot resolve non-role option type {self._option.type} to a role"
        raise TypeError(error_message)

    def resolve_to_user(self) -> hikari.User | hikari.Member:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.USER:
            assert self._option.value is not None
            assert self._resolved
            user_id = hikari.Snowflake(self._option.value)
            return self._resolved.members.get(user_id) or self._resolved.users[user_id]

        if self._option.type is hikari.OptionType.MENTIONABLE and self._resolved:
            assert self._option.value is not None
            user_id = hikari.Snowflake(self._option.value)
            if result := self._resolved.members.get(user_id) or self._resolved.users.get(user_id):
                return result

        error_message = f"Cannot resolve non-user option type {self._option.type} to a user"
        raise TypeError(error_message)


class AppCommandContext(base.BaseContext, tanjun.AppCommandContext):
    """Base class for interaction-based command contexts."""

    __slots__ = (
        "_defaults_to_ephemeral",
        "_defer_task",
        "_has_been_deferred",
        "_has_responded",
        "_interaction",
        "_last_response_id",
        "_register_task",
        "_response_future",
        "_response_lock",
    )

    def __init__(
        self,
        client: tanjun.Client,
        interaction: hikari.CommandInteraction,
        register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
        *,
        default_to_ephemeral: bool = False,
        future: asyncio.Future[_ResponseTypeT] | None = None,
    ) -> None:
        super().__init__(client)
        self._defaults_to_ephemeral = default_to_ephemeral
        self._defer_task: asyncio.Task[None] | None = None
        self._has_been_deferred = False
        self._has_responded = False
        self._interaction = interaction
        self._last_response_id: hikari.Snowflake | None = None
        self._register_task = register_task
        self._response_future = future
        self._response_lock = asyncio.Lock()
        self._set_type_special_case(tanjun.AppCommandContext, self)

    @property
    def author(self) -> hikari.User:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.user

    @property
    def channel_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.channel_id

    @property
    def client(self) -> tanjun.Client:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._tanjun_client

    @property
    def created_at(self) -> datetime.datetime:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.created_at

    @property
    def defaults_to_ephemeral(self) -> bool:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._defaults_to_ephemeral

    @property
    def expires_at(self) -> datetime.datetime:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        return self.created_at + _INTERACTION_LIFETIME

    @property
    def guild_id(self) -> hikari.Snowflake | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.guild_id

    @property
    def has_been_deferred(self) -> bool:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        return self._has_been_deferred

    @property
    def has_responded(self) -> bool:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._has_responded

    @property
    def is_human(self) -> typing.Literal[True]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return True

    @property
    def member(self) -> hikari.InteractionMember | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.member

    @property
    def interaction(self) -> hikari.CommandInteraction:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        return self._interaction

    async def _auto_defer(self, countdown: int | float, /) -> None:
        await asyncio.sleep(countdown)
        await self.defer()

    def cancel_defer(self) -> None:
        """Cancel the auto-deferral if its active."""
        if self._defer_task:
            self._defer_task.cancel()

    def _get_flags(
        self,
        flags: hikari.UndefinedType | int | hikari.MessageFlag = hikari.UNDEFINED,
        /,
        *,
        ephemeral: bool | None = None,
    ) -> int | hikari.MessageFlag:
        if flags is hikari.UNDEFINED:
            if ephemeral is True or (ephemeral is None and self._defaults_to_ephemeral):
                return hikari.MessageFlag.EPHEMERAL

            return hikari.MessageFlag.NONE

        if ephemeral is True:
            return flags | hikari.MessageFlag.EPHEMERAL

        if ephemeral is False:
            return flags & ~hikari.MessageFlag.EPHEMERAL

        return flags

    def start_defer_timer(self, count_down: int | float, /) -> Self:
        """Start the auto-deferral timer.

        Parameters
        ----------
        count_down
            The number of seconds to wait before automatically deferring the
            interaction.

        Returns
        -------
        Self
            This context to allow for chaining.
        """
        self._assert_not_final()
        if self._defer_task:
            error_message = "Defer timer already set"
            raise RuntimeError(error_message)

        self._defer_task = asyncio.create_task(self._auto_defer(count_down))
        return self

    def set_ephemeral_default(self, state: bool, /) -> Self:  # noqa: FBT001
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        self._assert_not_final()  # TODO: document not final assertions.
        self._defaults_to_ephemeral = state
        return self

    async def defer(
        self,
        *,
        flags: hikari.UndefinedType | int | hikari.MessageFlag = hikari.UNDEFINED,
        ephemeral: bool | None = None,
    ) -> None:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        flags = self._get_flags(flags, ephemeral=ephemeral)
        in_defer_task = self._defer_task and self._defer_task is asyncio.current_task()
        if not in_defer_task:
            self.cancel_defer()

        async with self._response_lock:
            if self._has_been_deferred:
                if in_defer_task:
                    return

                error_message = "Context has already been responded to"
                raise RuntimeError(error_message)

            self._has_been_deferred = True
            if self._response_future:
                self._response_future.set_result(self._interaction.build_deferred_response().set_flags(flags))

            else:
                await self._interaction.create_initial_response(
                    hikari.ResponseType.DEFERRED_MESSAGE_CREATE, flags=flags
                )

    def _validate_delete_after(self, delete_after: float | int | datetime.timedelta, /) -> float:
        delete_after = _delete_after_to_float(delete_after)
        time_left = (_INTERACTION_LIFETIME - (datetime.datetime.now(tz=datetime.UTC) - self.created_at)).total_seconds()
        if delete_after + 10 > time_left:
            error_message = "This interaction will have expired before delete_after is reached"
            raise ValueError(error_message)

        return delete_after

    async def _delete_followup_after(self, delete_after: float, message: hikari.Message, /) -> None:
        await asyncio.sleep(delete_after)
        try:
            await self._interaction.delete_message(message)
        except hikari.NotFoundError as exc:
            _LOGGER.debug("Failed to delete response message after %.2f seconds", delete_after, exc_info=exc)

    async def _create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        ephemeral: bool | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: hikari.UndefinedType | int | hikari.MessageFlag = hikari.UNDEFINED,
    ) -> hikari.Message:
        delete_after = self._validate_delete_after(delete_after) if delete_after is not None else None
        message = await self._interaction.execute(
            content=content,
            attachment=attachment,
            attachments=attachments,
            component=component,
            components=components,
            embed=embed,
            embeds=embeds,
            flags=self._get_flags(flags, ephemeral=ephemeral),
            tts=tts,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )
        self._last_response_id = message.id
        # This behaviour is undocumented and only kept by Discord for "backwards compatibility"
        # but the followup endpoint can be used to create the initial response for slash
        # commands or edit in a deferred response and (while this does lead to some
        # unexpected behaviour around deferrals) should be accounted for.
        self._has_responded = True

        if delete_after is not None:
            self._register_task(asyncio.create_task(self._delete_followup_after(delete_after, message)))

        return message

    async def create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        ephemeral: bool | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: hikari.UndefinedType | int | hikari.MessageFlag = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        async with self._response_lock:
            return await self._create_followup(
                content=content,
                delete_after=delete_after,
                ephemeral=ephemeral,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
                tts=tts,
                flags=flags,
            )

    async def _delete_initial_response_after(self, delete_after: float, /) -> None:
        await asyncio.sleep(delete_after)
        try:
            await self.delete_initial_response()
        except hikari.NotFoundError as exc:
            _LOGGER.debug("Failed to delete response message after %.2f seconds", delete_after, exc_info=exc)

    async def _create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        ephemeral: bool | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        delete_after = self._validate_delete_after(delete_after) if delete_after is not None else None
        if self._has_responded:
            error_message = "Initial response has already been created"
            raise RuntimeError(error_message)

        if self._has_been_deferred:
            error_message = (
                "edit_initial_response must be used to set the initial response after a context has been deferred"
            )
            raise RuntimeError(error_message)

        self.cancel_defer()
        if not self._response_future:
            await self._interaction.create_initial_response(
                response_type=hikari.ResponseType.MESSAGE_CREATE,
                content=content,
                attachment=attachment,
                attachments=attachments,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                flags=self._get_flags(flags, ephemeral=ephemeral),
                tts=tts,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        else:
            attachments, content = _to_list(attachment, attachments, content, _ATTACHMENT_TYPES, "attachment")
            components, content = _to_list(component, components, content, hikari.api.ComponentBuilder, "component")
            embeds, content = _to_list(embed, embeds, content, hikari.Embed, "embed")

            content = str(content) if content is not hikari.UNDEFINED else hikari.UNDEFINED
            # Pyright doesn't properly support attrs and doesn't account for _ being removed from field
            # pre-fix in init.
            result = hikari.impl.InteractionMessageBuilder(
                hikari.ResponseType.MESSAGE_CREATE,
                content,
                attachments=attachments,
                components=components,
                embeds=embeds,
                flags=flags,
                is_tts=tts,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

            self._response_future.set_result(result)

        self._has_responded = True
        if delete_after is not None:
            self._register_task(asyncio.create_task(self._delete_initial_response_after(delete_after)))

    async def create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        ephemeral: bool | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        flags: int | hikari.MessageFlag | hikari.UndefinedType = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Context>>.
        async with self._response_lock:
            await self._create_initial_response(
                delete_after=delete_after,
                ephemeral=ephemeral,
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
                flags=flags,
                tts=tts,
            )

    async def delete_initial_response(self) -> None:
        # <<inherited docstring from tanjun.abc.Context>>.
        await self._interaction.delete_initial_response()
        # If they defer then delete the initial response, this should be treated as having
        # an initial response to allow for followup responses.
        self._has_responded = True

    async def delete_last_response(self) -> None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._last_response_id is None:
            if self._has_responded or self._has_been_deferred:
                await self._interaction.delete_initial_response()
                # If they defer then delete the initial response then this should be treated as having
                # an initial response to allow for followup responses.
                self._has_responded = True
                return

            error_message = "Context has no last response"
            raise LookupError(error_message)

        await self._interaction.delete_message(self._last_response_id)

    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        delete_after = self._validate_delete_after(delete_after) if delete_after is not None else None
        message = await self._interaction.edit_initial_response(
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
        # This will be False if the initial response was deferred with this finishing the referral.
        self._has_responded = True

        if delete_after is not None:
            self._register_task(asyncio.create_task(self._delete_initial_response_after(delete_after)))

        return message

    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedNoneOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedNoneOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._last_response_id:
            delete_after = self._validate_delete_after(delete_after) if delete_after is not None else None
            message = await self._interaction.edit_message(
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
                self._register_task(asyncio.create_task(self._delete_followup_after(delete_after, message)))

            return message

        if self._has_responded or self._has_been_deferred:
            return await self.edit_initial_response(
                delete_after=delete_after,
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

        error_message = "Context has no previous responses"
        raise LookupError(error_message)

    async def fetch_initial_response(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        return await self._interaction.fetch_initial_response()

    async def fetch_last_response(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._last_response_id is not None:
            return await self._interaction.fetch_message(self._last_response_id)

        if self._has_responded:
            return await self.fetch_initial_response()

        error_message = "Context has no previous known responses"
        raise LookupError(error_message)

    async def create_modal_response(
        self,
        title: str,
        custom_id: str,
        /,
        *,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
    ) -> None:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        async with self._response_lock:
            if self._has_responded or self._has_been_deferred:
                error_message = "Initial response has already been created"
                raise RuntimeError(error_message)

            if self._response_future:
                components, _ = _to_list(component, components, None, hikari.api.ComponentBuilder, "component")

                response = hikari.impl.InteractionModalBuilder(title, custom_id, components or [])
                self._response_future.set_result(response)

            else:
                await self._interaction.create_modal_response(
                    title, custom_id, component=component, components=components
                )

            self._has_responded = True

    @typing.overload
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message: ...

    @typing.overload
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message | None: ...

    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        delete_after: datetime.timedelta | float | int | None = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: hikari.SnowflakeishSequence[hikari.PartialUser] | bool | hikari.UndefinedType = hikari.UNDEFINED,
        role_mentions: hikari.SnowflakeishSequence[hikari.PartialRole] | bool | hikari.UndefinedType = hikari.UNDEFINED,
    ) -> hikari.Message | None:
        # <<inherited docstring from tanjun.abc.Context>>.
        async with self._response_lock:
            if self._has_responded:
                return await self._create_followup(
                    content,
                    delete_after=delete_after,
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

            if self._has_been_deferred:
                return await self.edit_initial_response(
                    delete_after=delete_after,
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

            await self._create_initial_response(
                delete_after=delete_after,
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

        if ensure_result:
            return await self._interaction.fetch_initial_response()

        return None  # MyPy compat


_ATTACHMENT_TYPES: tuple[type[typing.Any], ...] = (hikari.files.Resource, *hikari.files.RAWISH_TYPES, os.PathLike)


def _to_list(
    singular: hikari.UndefinedOr[_T],
    plural: hikari.UndefinedOr[collections.Sequence[_T]],
    other: _OtherT,
    type_: type[_T] | tuple[type[_T], ...],
    name: str,
    /,
) -> tuple[hikari.UndefinedOr[list[_T]], hikari.UndefinedOr[_OtherT]]:
    if singular is not hikari.UNDEFINED and plural is not hikari.UNDEFINED:
        error_message = f"Only one of {name} or {name}s may be passed"
        raise ValueError(error_message)

    if singular is not hikari.UNDEFINED:
        return [singular], other

    if plural is not hikari.UNDEFINED:
        return list(plural), other

    if other and isinstance(other, type_):
        return [other], hikari.UNDEFINED

    return hikari.UNDEFINED, other


class SlashContext(AppCommandContext, tanjun.SlashContext):
    """Standard implementation of [tanjun.abc.SlashContext][]."""

    __slots__ = ("_command", "_command_name", "_marked_not_found", "_on_not_found", "_options")

    def __init__(
        self,
        client: tanjun.Client,
        interaction: hikari.CommandInteraction,
        register_task: collections.Callable[[asyncio.Task[typing.Any]], None],
        *,
        default_to_ephemeral: bool = False,
        future: asyncio.Future[_ResponseTypeT] | None = None,
        on_not_found: collections.Callable[[tanjun.SlashContext], collections.Awaitable[None]] | None = None,
    ) -> None:
        """Initialise a slash command context.

        Parameters
        ----------
        client
            The Tanjun client this context is bound to.
        interaction
            The command interaction this context is for.
        register_task
            Callback used to register long-running tasks spawned by this context.
        default_to_ephemeral
            Whether to default to ephemeral responses.
        future
            A future used to set the initial response if this is being called
            through the REST webhook flow.
        on_not_found
            Callback used to indicate no matching command was found.
        """
        super().__init__(client, interaction, register_task, default_to_ephemeral=default_to_ephemeral, future=future)
        self._marked_not_found = False
        self._on_not_found = on_not_found

        self._command: tanjun.BaseSlashCommand | None = None
        command_name, options = _internal.flatten_options(interaction.command_name, interaction.options)
        self._command_name = command_name
        self._options = {option.name: SlashOption(interaction.resolved, option) for option in options}
        (
            self._set_type_special_case(tanjun.SlashContext, self)._set_type_special_case(  # noqa: SLF001
                SlashContext, self
            )
        )

    @property
    def command(self) -> tanjun.BaseSlashCommand | None:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        return self._command

    @property
    def options(self) -> collections.Mapping[str, tanjun.SlashOption]:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        return self._options.copy()

    @property
    def triggering_name(self) -> str:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._command_name

    @property
    def type(self) -> typing.Literal[hikari.CommandType.SLASH]:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        return hikari.CommandType.SLASH

    async def mark_not_found(self) -> None:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        # TODO: assert not finalised?
        if self._on_not_found and not self._marked_not_found:
            self._marked_not_found = True
            await self._on_not_found(self)

    def set_command(self, command: tanjun.BaseSlashCommand | None, /) -> Self:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        self._assert_not_final()
        if command:
            # TODO: command group?
            (
                self._set_type_special_case(tanjun.ExecutableCommand, command)  # noqa: SLF001
                ._set_type_special_case(tanjun.AppCommand, command)
                ._set_type_special_case(tanjun.BaseSlashCommand, command)
                ._set_type_special_case(tanjun.SlashCommand, command)
            )

        elif self._command:
            (
                self._remove_type_special_case(tanjun.ExecutableCommand)  # noqa: SLF001
                ._remove_type_special_case(tanjun.AppCommand)
                ._remove_type_special_case(tanjun.BaseSlashCommand)
                ._remove_type_special_case(tanjun.SlashCommand)
            )

        self._command = command
        return self
