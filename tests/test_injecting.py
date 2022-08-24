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

# pyright: reportPrivateUsage=none

from unittest import mock

import alluka

import tanjun


def test_as_self_injecting():
    mock_callback = mock.Mock()
    mock_client = mock.Mock()

    result = tanjun.injecting.as_self_injecting(mock_client)(mock_callback)

    assert result.callback is mock_callback
    assert result._client is mock_client.injector


def test_aliases():
    assert set(tanjun.injecting.__all__) == {
        "AbstractInjectionContext",
        "BasicInjectionContext",
        "CallbackSig",
        "Injected",
        "InjectorClient",
        "SelfInjectingCallback",
        "UNDEFINED",
        "Undefined",
        "UndefinedOr",
        "as_self_injecting",
        "inject",
        "injected",
    }
    assert tanjun.injecting.SelfInjectingCallback is alluka.AsyncSelfInjecting
    assert tanjun.injecting.BasicInjectionContext is alluka.BasicContext
    assert tanjun.injecting.InjectorClient is alluka.Client
    assert tanjun.injecting.Injected is alluka.Injected
    assert tanjun.injecting.inject is alluka.inject
    assert tanjun.injecting.injected is alluka.inject
    assert tanjun.injecting.UNDEFINED is alluka.abc.UNDEFINED
    assert tanjun.injecting.CallbackSig is alluka.abc.CallbackSig
    assert tanjun.injecting.AbstractInjectionContext is alluka.abc.Context
    assert tanjun.injecting.Undefined is alluka.abc.Undefined
