# -*- coding: utf-8 -*-
# cython: language_level=3
# Tanjun Examples - A collection of examples for Tanjun.
# Written in 2021 by Lucina Lucina@lmbyrne.dev
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain worldwide.
# This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along with this software.
# If not, see <https://creativecommons.org/publicdomain/zero/1.0/>.
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
