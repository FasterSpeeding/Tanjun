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
"""Standard slash command execution context implementations."""
from __future__ import annotations

__all__: list[str] = ["SlashContext", "SlashOption"]

import asyncio
import datetime
import logging
import typing

import hikari

from .. import abc as tanjun_abc
from . import base

if typing.TYPE_CHECKING:
    from collections import abc as collections

    _AppCommandContextT = typing.TypeVar("_AppCommandContextT", bound="AppCommandContext")
    _ResponseTypeT = typing.Union[hikari.api.InteractionMessageBuilder, hikari.api.InteractionDeferredBuilder]
    _SlashContextT = typing.TypeVar("_SlashContextT", bound="SlashContext")
    _T = typing.TypeVar("_T")

_INTERACTION_LIFETIME: typing.Final[datetime.timedelta] = datetime.timedelta(minutes=15)
_LOGGER = logging.getLogger("hikari.tanjun.context")


def _delete_after_to_float(delete_after: typing.Union[datetime.timedelta, float, int]) -> float:
    return delete_after.total_seconds() if isinstance(delete_after, datetime.timedelta) else float(delete_after)


_SnowflakeOptions = {
    hikari.OptionType.USER,
    hikari.OptionType.MENTIONABLE,
    hikari.OptionType.ROLE,
    hikari.OptionType.CHANNEL,
}


class SlashOption(tanjun_abc.SlashOption):
    """Standard implementation of the SlashOption interface."""

    __slots__ = ("_option", "_resolved")

    def __init__(
        self, resolved: typing.Optional[hikari.ResolvedOptionData], option: hikari.CommandInteractionOption, /
    ):
        if option.value is None:
            raise ValueError("Cannot build a slash option with a value-less API representation")

        self._option = option
        self._resolved = resolved

    @property
    def name(self) -> str:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        return self._option.name

    @property
    def type(self) -> typing.Union[hikari.OptionType, int]:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        return self._option.type

    @property
    def value(self) -> typing.Union[str, int, hikari.Snowflake, bool, float]:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        # This is asserted in __init__
        assert self._option.value is not None
        if self._option.type in _SnowflakeOptions:
            assert self._option.value is not None
            return hikari.Snowflake(self._option.value)

        return self._option.value

    def boolean(self) -> bool:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.BOOLEAN:
            return bool(self._option.value)

        raise TypeError("Option is not a boolean")

    def float(self) -> float:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.FLOAT:
            assert self._option.value is not None
            return float(self._option.value)

        raise TypeError("Option is not a float")

    def integer(self) -> int:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.INTEGER:
            assert self._option.value is not None
            return int(self._option.value)

        raise TypeError("Option is not an integer")

    def snowflake(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type in _SnowflakeOptions:
            assert self._option.value is not None
            return hikari.Snowflake(self._option.value)

        raise TypeError("Option is not a unique resource")

    def string(self) -> str:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self.type is hikari.OptionType.STRING:
            return str(self._option.value)

        raise TypeError("Option is not a string")

    def resolve_value(
        self,
    ) -> typing.Union[hikari.InteractionChannel, hikari.InteractionMember, hikari.Role, hikari.User]:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.CHANNEL:
            return self.resolve_to_channel()

        if self._option.type is hikari.OptionType.ROLE:
            return self.resolve_to_role()

        if self._option.type is hikari.OptionType.USER:
            return self.resolve_to_user()

        if self._option.type is hikari.OptionType.MENTIONABLE:
            return self.resolve_to_mentionable()

        raise TypeError(f"Option type {self._option.type} isn't resolvable")

    def resolve_to_channel(self) -> hikari.InteractionChannel:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        # What does self.value being None mean?
        if self._option.type is hikari.OptionType.CHANNEL:
            assert self._option.value is not None
            assert self._resolved
            return self._resolved.channels[hikari.Snowflake(self._option.value)]

        raise TypeError(f"Cannot resolve non-channel option type {self._option.type} to a channel")

    @typing.overload
    def resolve_to_member(self) -> hikari.InteractionMember:
        ...

    @typing.overload
    def resolve_to_member(self, *, default: _T) -> typing.Union[hikari.InteractionMember, _T]:
        ...

    def resolve_to_member(self, *, default: _T = ...) -> typing.Union[hikari.InteractionMember, _T]:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        # What does self.value being None mean?
        if self._option.type is hikari.OptionType.USER:
            assert self._option.value is not None
            assert self._resolved
            if member := self._resolved.members.get(hikari.Snowflake(self._option.value)):
                return member

            if default is not ...:
                return default

            raise LookupError("User isn't in the current guild") from None

        if self._option.type is hikari.OptionType.MENTIONABLE:
            assert self._option.value is not None
            assert self._resolved
            target_id = hikari.Snowflake(self._option.value)
            if member := self._resolved.members.get(target_id):
                return member

            if target_id in self._resolved.users:
                if default is not ...:
                    return default

                raise LookupError("User isn't in the current guild")

        raise TypeError(f"Cannot resolve non-user option type {self._option.type} to a member")

    def resolve_to_mentionable(self) -> typing.Union[hikari.Role, hikari.User, hikari.Member]:
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

        raise TypeError(f"Cannot resolve non-mentionable option type {self._option.type} to a mentionable entity.")

    def resolve_to_role(self) -> hikari.Role:
        # <<inherited docstring from tanjun.abc.SlashOption>>.
        if self._option.type is hikari.OptionType.ROLE:
            assert self._option.value is not None
            assert self._resolved
            return self._resolved.roles[hikari.Snowflake(self._option.value)]

        if self._option.type is hikari.OptionType.MENTIONABLE and self._resolved:
            if role := self._resolved.roles.get(hikari.Snowflake(self.value)):
                return role

        raise TypeError(f"Cannot resolve non-role option type {self._option.type} to a role")

    def resolve_to_user(self) -> typing.Union[hikari.User, hikari.Member]:
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

        raise TypeError(f"Cannot resolve non-user option type {self._option.type} to a user")


_OptionT = typing.TypeVar("_OptionT", bound=hikari.CommandInteractionOption)
_COMMAND_OPTION_TYPES: typing.Final[frozenset[hikari.OptionType]] = frozenset(
    [hikari.OptionType.SUB_COMMAND, hikari.OptionType.SUB_COMMAND_GROUP]
)


def flatten_options(options: typing.Optional[collections.Sequence[_OptionT]], /) -> collections.Sequence[_OptionT]:
    while options and (first_option := options[0]).type in _COMMAND_OPTION_TYPES:
        options = typing.cast("collections.Sequence[_OptionT]", first_option.options)

    return options or ()


class AppCommandContext(base.BaseContext, tanjun_abc.AppCommandContext):
    """Base class for interaction-based command contexts."""

    __slots__ = (
        "_defaults_to_ephemeral",
        "_defer_task",
        "_has_been_deferred",
        "_has_responded",
        "_interaction",
        "_last_response_id",
        "_response_future",
        "_response_lock",
    )

    def __init__(
        self,
        client: tanjun_abc.Client,
        interaction: hikari.CommandInteraction,
        *,
        default_to_ephemeral: bool = False,
        future: typing.Optional[asyncio.Future[_ResponseTypeT]] = None,
    ) -> None:
        super().__init__(client)
        self._defaults_to_ephemeral = default_to_ephemeral
        self._defer_task: typing.Optional[asyncio.Task[None]] = None
        self._has_been_deferred = False
        self._has_responded = False
        self._interaction = interaction
        self._last_response_id: typing.Optional[hikari.Snowflake] = None
        self._response_future = future
        self._response_lock = asyncio.Lock()
        self._set_type_special_case(tanjun_abc.AppCommandContext, self)

    @property
    def author(self) -> hikari.User:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.user

    @property
    def channel_id(self) -> hikari.Snowflake:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.channel_id

    @property
    def client(self) -> tanjun_abc.Client:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._client

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
    def guild_id(self) -> typing.Optional[hikari.Snowflake]:
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
    def member(self) -> typing.Optional[hikari.InteractionMember]:
        # <<inherited docstring from tanjun.abc.Context>>.
        return self._interaction.member

    @property
    def triggering_name(self) -> str:
        # <<inherited docstring from tanjun.abc.Context>>.
        # TODO: account for command groups
        return self._interaction.command_name

    @property
    def interaction(self) -> hikari.CommandInteraction:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        return self._interaction

    async def _auto_defer(self, countdown: typing.Union[int, float], /) -> None:
        await asyncio.sleep(countdown)
        await self.defer()

    def cancel_defer(self) -> None:
        """Cancel the auto-deferral if its active."""
        if self._defer_task:
            self._defer_task.cancel()

    def _get_flags(
        self, flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED
    ) -> typing.Union[int, hikari.MessageFlag]:
        if flags is hikari.UNDEFINED:
            return hikari.MessageFlag.EPHEMERAL if self._defaults_to_ephemeral else hikari.MessageFlag.NONE

        return flags or hikari.MessageFlag.NONE

    def start_defer_timer(self: _AppCommandContextT, count_down: typing.Union[int, float], /) -> _AppCommandContextT:
        """Start the auto-deferral timer.

        Parameters
        ----------
        count_down : int | float
            The number of seconds to wait before automatically deferring the
            interaction.

        Returns
        -------
        Self
            This context to allow for chaining.
        """
        self._assert_not_final()
        if self._defer_task:
            raise RuntimeError("Defer timer already set")

        self._defer_task = asyncio.create_task(self._auto_defer(count_down))
        return self

    def set_ephemeral_default(self: _AppCommandContextT, state: bool, /) -> _AppCommandContextT:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        self._assert_not_final()  # TODO: document not final assertions.
        self._defaults_to_ephemeral = state
        return self

    async def defer(
        self,
        *,
        flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED,
        ephemeral: bool = False,
    ) -> None:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        else:
            flags = self._get_flags(flags)

        in_defer_task = self._defer_task and self._defer_task is asyncio.current_task()
        if not in_defer_task:
            self.cancel_defer()

        async with self._response_lock:
            if self._has_been_deferred:
                if in_defer_task:
                    return

                raise RuntimeError("Context has already been responded to")

            self._has_been_deferred = True
            if self._response_future:
                self._response_future.set_result(self._interaction.build_deferred_response().set_flags(flags))

            else:
                await self._interaction.create_initial_response(
                    hikari.ResponseType.DEFERRED_MESSAGE_CREATE, flags=flags
                )

    def _validate_delete_after(self, delete_after: typing.Union[float, int, datetime.timedelta]) -> float:
        delete_after = _delete_after_to_float(delete_after)
        time_left = (
            _INTERACTION_LIFETIME - (datetime.datetime.now(tz=datetime.timezone.utc) - self.created_at)
        ).total_seconds()
        if delete_after + 10 > time_left:
            raise ValueError("This interaction will have expired before delete_after is reached")

        return delete_after

    async def _delete_followup_after(self, delete_after: float, message: hikari.Message) -> None:
        await asyncio.sleep(delete_after)
        try:
            await self._interaction.delete_message(message)
        except hikari.NotFoundError as exc:
            _LOGGER.debug("Failed to delete response message after %.2f seconds", delete_after, exc_info=exc)

    async def _create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED,
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
            flags=self._get_flags(flags),
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
        if not self._has_responded:
            self._has_responded = True

        if delete_after is not None and not message.flags & hikari.MessageFlag.EPHEMERAL:
            asyncio.create_task(self._delete_followup_after(delete_after, message))

        return message

    async def create_followup(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        ephemeral: bool = False,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        flags: typing.Union[hikari.UndefinedType, int, hikari.MessageFlag] = hikari.UNDEFINED,
    ) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.AppCommandContext>>.
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        async with self._response_lock:
            return await self._create_followup(
                content=content,
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
                tts=tts,
                flags=flags,
            )

    async def _delete_initial_response_after(self, delete_after: float) -> None:
        await asyncio.sleep(delete_after)
        try:
            await self.delete_initial_response()
        except hikari.NotFoundError as exc:
            _LOGGER.debug("Failed to delete response message after %.2f seconds", delete_after, exc_info=exc)

    async def _create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        flags: typing.Union[int, hikari.MessageFlag, hikari.UndefinedType] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        flags = self._get_flags(flags)
        delete_after = self._validate_delete_after(delete_after) if delete_after is not None else None
        if self._has_responded:
            raise RuntimeError("Initial response has already been created")

        if self._has_been_deferred:
            raise RuntimeError(
                "edit_initial_response must be used to set the initial response after a context has been deferred"
            )

        self.cancel_defer()
        self._has_responded = True
        if not self._response_future:
            await self._interaction.create_initial_response(
                response_type=hikari.ResponseType.MESSAGE_CREATE,
                content=content,
                component=component,
                components=components,
                embed=embed,
                embeds=embeds,
                flags=flags,
                tts=tts,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        else:
            if component and components:
                raise ValueError("Only one of component or components may be passed")

            if embed and embeds:
                raise ValueError("Only one of embed or embeds may be passed")

            if component:
                assert not isinstance(component, hikari.UndefinedType)
                components = (component,)

            if embed:
                assert not isinstance(embed, hikari.UndefinedType)
                embeds = (embed,)

            content = str(content) if content is not hikari.UNDEFINED else hikari.UNDEFINED
            # Pyright doesn't properly support attrs and doesn't account for _ being removed from field
            # pre-fix in init.
            result = hikari.impl.InteractionMessageBuilder(
                type=hikari.ResponseType.MESSAGE_CREATE,  # type: ignore
                content=content,  # type: ignore
                components=components,  # type: ignore
                embeds=embeds,  # type: ignore
                flags=flags,  # type: ignore
                is_tts=tts,  # type: ignore
                mentions_everyone=mentions_everyone,  # type: ignore
                user_mentions=user_mentions,  # type: ignore
                role_mentions=role_mentions,  # type: ignore
            )  # type: ignore
            if embeds is not hikari.UNDEFINED:
                for embed in embeds:
                    result.add_embed(embed)

            self._response_future.set_result(result)

        if delete_after is not None and not flags & hikari.MessageFlag.EPHEMERAL:
            asyncio.create_task(self._delete_initial_response_after(delete_after))

    async def create_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        ephemeral: bool = False,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        flags: typing.Union[int, hikari.MessageFlag, hikari.UndefinedType] = hikari.UNDEFINED,
        tts: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
    ) -> None:
        # <<inherited docstring from tanjun.abc.Context>>.
        if ephemeral:
            flags = (flags or hikari.MessageFlag.NONE) | hikari.MessageFlag.EPHEMERAL

        async with self._response_lock:
            await self._create_initial_response(
                delete_after=delete_after,
                content=content,
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
        # If they defer then delete the initial response then this should be treated as having
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

            raise LookupError("Context has no last response")

        await self._interaction.delete_message(self._last_response_id)

    async def edit_initial_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
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
            replace_attachments=replace_attachments,
            mentions_everyone=mentions_everyone,
            user_mentions=user_mentions,
            role_mentions=role_mentions,
        )
        self._has_responded = True

        if delete_after is not None and not message.flags & hikari.MessageFlag.EPHEMERAL:
            asyncio.create_task(self._delete_initial_response_after(delete_after))

        return message

    async def edit_last_response(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        attachment: hikari.UndefinedOr[hikari.Resourceish] = hikari.UNDEFINED,
        attachments: hikari.UndefinedOr[collections.Sequence[hikari.Resourceish]] = hikari.UNDEFINED,
        component: hikari.UndefinedNoneOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedNoneOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedNoneOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedNoneOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        replace_attachments: bool = False,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
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
                replace_attachments=replace_attachments,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )
            if delete_after is not None and not message.flags & hikari.MessageFlag.EPHEMERAL:
                asyncio.create_task(self._delete_followup_after(delete_after, message))

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
                replace_attachments=replace_attachments,
                mentions_everyone=mentions_everyone,
                user_mentions=user_mentions,
                role_mentions=role_mentions,
            )

        raise LookupError("Context has no previous responses")

    async def fetch_initial_response(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        return await self._interaction.fetch_initial_response()

    async def fetch_last_response(self) -> hikari.Message:
        # <<inherited docstring from tanjun.abc.Context>>.
        if self._last_response_id is not None:
            return await self._interaction.fetch_message(self._last_response_id)

        if self._has_responded:
            return await self.fetch_initial_response()

        raise LookupError("Context has no previous known responses")

    @typing.overload
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[False] = False,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> typing.Optional[hikari.Message]:
        ...

    @typing.overload
    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: typing.Literal[True],
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> hikari.Message:
        ...

    async def respond(
        self,
        content: hikari.UndefinedOr[typing.Any] = hikari.UNDEFINED,
        *,
        ensure_result: bool = False,
        delete_after: typing.Union[datetime.timedelta, float, int, None] = None,
        component: hikari.UndefinedOr[hikari.api.ComponentBuilder] = hikari.UNDEFINED,
        components: hikari.UndefinedOr[collections.Sequence[hikari.api.ComponentBuilder]] = hikari.UNDEFINED,
        embed: hikari.UndefinedOr[hikari.Embed] = hikari.UNDEFINED,
        embeds: hikari.UndefinedOr[collections.Sequence[hikari.Embed]] = hikari.UNDEFINED,
        mentions_everyone: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        user_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialUser], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
        role_mentions: typing.Union[
            hikari.SnowflakeishSequence[hikari.PartialRole], bool, hikari.UndefinedType
        ] = hikari.UNDEFINED,
    ) -> typing.Optional[hikari.Message]:
        # <<inherited docstring from tanjun.abc.Context>>.
        async with self._response_lock:
            if self._has_responded:
                return await self._create_followup(
                    content,
                    delete_after=delete_after,
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


class SlashContext(AppCommandContext, tanjun_abc.SlashContext):
    """Standard implementation of `tanjun.abc.SlashContext`."""

    __slots__ = ("_command", "_marked_not_found", "_on_not_found", "_options")

    def __init__(
        self,
        client: tanjun_abc.Client,
        interaction: hikari.CommandInteraction,
        *,
        default_to_ephemeral: bool = False,
        future: typing.Optional[asyncio.Future[_ResponseTypeT]] = None,
        on_not_found: typing.Optional[
            collections.Callable[[tanjun_abc.SlashContext], collections.Awaitable[None]]
        ] = None,
    ) -> None:
        super().__init__(client, interaction, default_to_ephemeral=default_to_ephemeral, future=future)
        self._marked_not_found = False
        self._on_not_found = on_not_found

        self._command: typing.Optional[tanjun_abc.BaseSlashCommand] = None
        if options := flatten_options(interaction.options):
            self._options = {option.name: SlashOption(interaction.resolved, option) for option in options}

        else:
            self._options = {}

        (self._set_type_special_case(tanjun_abc.SlashContext, self)._set_type_special_case(SlashContext, self))

    @property
    def command(self) -> typing.Optional[tanjun_abc.BaseSlashCommand]:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        return self._command

    @property
    def options(self) -> collections.Mapping[str, tanjun_abc.SlashOption]:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        return self._options.copy()

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

    def set_command(self: _SlashContextT, command: typing.Optional[tanjun_abc.BaseSlashCommand], /) -> _SlashContextT:
        # <<inherited docstring from tanjun.abc.SlashContext>>.
        self._assert_not_final()
        if command:
            # TODO: command group?
            (
                self._set_type_special_case(tanjun_abc.ExecutableCommand, command)
                ._set_type_special_case(tanjun_abc.AppCommand, command)
                ._set_type_special_case(tanjun_abc.BaseSlashCommand, command)
                ._set_type_special_case(tanjun_abc.SlashCommand, command)
            )

        elif self._command:
            (
                self._remove_type_special_case(tanjun_abc.ExecutableCommand)
                ._remove_type_special_case(tanjun_abc.AppCommand)
                ._remove_type_special_case(tanjun_abc.BaseSlashCommand)
                ._remove_type_special_case(tanjun_abc.SlashCommand)
            )

        self._command = command
        return self
