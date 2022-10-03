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

import hikari

from tanjun.dependencies import locales


class TestBasicLocaliser:
    def test_get_all_variants(self):
        localiser = locales.BasicLocaliser().set_variants(
            "yeet",
            {
                hikari.Locale.BG: "BIGGIE CHEESE",
                hikari.Locale.CS: "COMPUTER SENTIENT",
                hikari.Locale.EN_GB: "no",
            },
            DE="yeet",
            boom="NO",
        )

        assert localiser.get_all_variants("yeet") == {
            hikari.Locale.BG: "BIGGIE CHEESE",
            hikari.Locale.CS: "COMPUTER SENTIENT",
            hikari.Locale.EN_GB: "no",
            "DE": "yeet",
            "boom": "NO",
        }

    def test_get_all_variants_ignores_default(self):
        ...

    def test_get_all_variants_when_format(self):
        ...

    def test_get_all_variants_when_format_ignores_default(self):
        ...

    def test_get_all_variants_when_not_known(self):
        assert locales.BasicLocaliser().get_all_variants("nope") == {}

    def test_localise(self):
        ...

    def test_localise_when_format(self):
        ...

    def test_localise_when_tag_unknown(self):
        ...

    def test_localise_when_id_unknown(self):
        ...

    def test_localize(self):
        ...

    def test_localize_when_format(self):
        ...

    def test_localize_when_tag_unknown(self):
        ...

    def test_localize_when_id_unknown(self):
        ...
