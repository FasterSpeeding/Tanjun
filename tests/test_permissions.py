# -*- coding: utf-8 -*-
# BSD 3-Clause License
#
# Copyright (c) 2020-2024, Faster Speeding
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

# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.

import pytest


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions(): ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions_when_guild_owner(): ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions_when_admin_role(): ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_permissions_when_no_channel(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_guild_owner(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_admin_role(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_no_channel(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_when_channel_object_provided(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_for_uncached_entities(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_permissions_for_no_cache(): ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_everyone_permissions(): ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_everyone_permissions_admin_role(): ...


@pytest.mark.skip(reason="Not implemented")
def test_calculate_everyone_permissions_no_channel(): ...


@pytest.mark.asyncio()
async def test_fetch_everyone_permissions(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_admin_role(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_for_uncached_entities(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_for_no_cache(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_no_channel(): ...


@pytest.mark.skip(reason="Not implemented")
@pytest.mark.asyncio()
async def test_fetch_everyone_permissions_channel_object_provided(): ...
