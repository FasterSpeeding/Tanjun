from __future__ import annotations

import typing

from . import clients

class Dependency(typing.TypedDict):
    name: str
    version: str


class Tanjun(typing.TypedDict):
    message_accepts: clients.MessageAcceptsEnum
    prefixes: list[str]
    set_global_commands: typing.Union[bool, int, str]



class Config(typing.TypedDict):
    dependencies: dict[str, dict[str, Dependency]]
    modules: list[str]
    tanjun: Tanjun


@classmethod
def from_raw(data: dict[str, typing.Any], /) -> Config:
    dependencies = data.pop("dependencies", None) or {}

    if not isinstance(dependencies, dict):
        raise TypeError(f"dependencies must be a dict, not {type(dependencies)}")

    modules = data.pop("modules", None) or []

    if not isinstance(modules, list):
        raise TypeError("modules must be a list or strings")

    for module in modules:
        if not isinstance(module, str):
            raise TypeError(f"Expected strings in modules, got {type(module)}")

    tanjun_data = data.pop("tanjun", None) or {}
    if not isinstance(tanjun_data, dict):
        raise TypeError(f"tanjun must be a dict, not {type(tanjun_data)}")


    raw_message_accepts = tanjun_data.pop("message_accepts", clients.MessageAcceptsEnum.ALL)
    try:
        message_accepts = clients.MessageAcceptsEnum(raw_message_accepts.upper())
    except ValueError:
        possible_names = ", ".join(map(str, list(clients.MessageAcceptsEnum)))
        raise ValueError(f"Expected one of {possible_names} for tanjun.message_accepts but got {raw_message_accepts}") from None

    tanjun = Tanjun(**tanjun_data, message_accepts=message_accepts)
    return Config(**data, dependencies=dependencies, modules=modules, tanjun=tanjun)


