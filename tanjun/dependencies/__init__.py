# -*- coding: utf-8 -*-
# cython: language_level=3
# BSD 3-Clause License
#
# Copyright (c) 2020-2021, Faster Speeding
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
"""Default dependency utilities used within Tanjun and their abstract interfaces."""
from __future__ import annotations

__all__: list[str] = [
    # __init__.py
    "set_standard_dependencies",
    # callbacks.py
    "fetch_my_user",
    # data.py
    "cache_callback",
    "cached_inject",
    "LazyConstant",
    "inject_lc",
    "make_lc_resolver",
    # limiters.py
    "AbstractConcurrencyLimiter",
    "AbstractCooldownManager",
    "BucketResource",
    "ConcurrencyPreExecution",
    "ConcurrencyPostExecution",
    "CooldownPreExecution",
    "InMemoryConcurrencyLimiter",
    "InMemoryCooldownManager",
    "with_concurrency_limit",
    "with_cooldown",
    # owners.py
    "AbstractOwners",
    "Owners",
]

import hikari

from .. import injecting
from .callbacks import *
from .data import *
from .limiters import *
from .owners import *


def set_standard_dependencies(client: injecting.InjectorClient, /) -> None:
    """Set the standard dependencies for Tanjun.

    Parameters
    ----------
    client: tanjun.injecting.InjectorClient
        The injector client to set the standard dependencies on.
    """
    client.set_type_dependency(AbstractOwners, Owners()).set_type_dependency(
        LazyConstant[hikari.OwnUser], LazyConstant(fetch_my_user)
    )
