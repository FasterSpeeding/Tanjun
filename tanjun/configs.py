from __future__ import annotations

__all__ = ["CommandConfig", "ParserConfig", "ClientConfig", "VALID_CLIENTS"]

import typing

import attr
from hikari import bases
from hikari.clients import bot_base
from hikari.clients import configs
from hikari.clients import stateless
from hikari.internal import marshaller


VALID_CLIENTS = ["hikari.clients.stateless.StatelessBot"]


@marshaller.marshallable()
@attr.s(slots=False, kw_only=True)
class CommandConfig:
    access_levels: typing.MutableMapping[bases.Snowflake, int] = marshaller.attrib(
        deserializer=lambda levels: {bases.Snowflake(sn): int(level) for sn, level in levels.items()},
        if_undefined=list,
        factory=list,
    )
    bot_client: bot_base.BotBase = marshaller.attrib(
        deserializer=marshaller.dereference_handle,
        if_undefined=lambda: stateless.StatelessBot,
        default=stateless.StatelessBot,
    )

    #   @bot_client.validator  # TODO: validation here
    #   def _bot_client_validator(self, _, value):  # pylint:disable=unused-argument
    #       if isinstance(value, str) and value not in VALID_CLIENTS:
    #           raise ValueError(f"Invalid `bot_client` passed, must be one of {VALID_CLIENTS}")

    prefixes: typing.Sequence[str] = marshaller.attrib(
        deserializer=lambda prefixes: [str(prefix) for prefix in prefixes], if_undefined=list, factory=list
    )
    modules: typing.Sequence[str] = marshaller.attrib(deserializer=list, if_undefined=list, factory=list)


@marshaller.marshallable()
@attr.s(slots=False, kw_only=True)
class ParserConfig:
    set_parameters_from_annotations: bool = marshaller.attrib(
        deserializer=bool, default=True, if_undefined=lambda: True
    )


@marshaller.marshallable()
@attr.s(slots=False, kw_only=True)
class ClientConfig(configs.BotConfig, CommandConfig, ParserConfig):
    ...
