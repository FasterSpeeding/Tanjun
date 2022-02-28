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

# pyright: reportUnknownMemberType=none
# pyright: reportPrivateUsage=none
# This leads to too many false-positives around mocks.
from unittest import mock

import hikari

import tanjun


def test_set_standard_dependencies():
    mock_client = mock.Mock(tanjun.Client)
    mock_client.set_type_dependency.return_value = mock_client

    with (
        mock.patch.object(tanjun.dependencies, "Owners") as owner_check,
        mock.patch.object(tanjun.dependencies, "LazyConstant") as lazy_constant,
    ):
        tanjun.dependencies.set_standard_dependencies(mock_client)

    owner_check.assert_called_once_with()
    lazy_constant.__getitem__.return_value.assert_called_once_with(tanjun.dependencies.fetch_my_user)
    lazy_constant.__getitem__.assert_has_calls([mock.call(hikari.OwnUser), mock.call(hikari.OwnUser)])
    mock_client.set_type_dependency.assert_has_calls(
        [
            mock.call(tanjun.dependencies.AbstractOwners, owner_check.return_value),
            mock.call(lazy_constant.__getitem__.return_value, lazy_constant.__getitem__.return_value.return_value),
        ]
    )
