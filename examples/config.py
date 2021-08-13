# -*- coding: utf-8 -*-
# cython: language_level=3
"""Placeholder dataclass config used within the examples."""
# Nothing much to see here, just a example bare minimum config file.
import dataclasses


@dataclasses.dataclass()
class ExampleConfig:
    bot_token: str
    database_password: str
    database_url: str
    prefix: str
    ...

    @classmethod
    def load(cls) -> "ExampleConfig":
        raise NotImplementedError
