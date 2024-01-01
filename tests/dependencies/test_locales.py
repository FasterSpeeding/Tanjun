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


import hikari
import mock

import tanjun


class TestBasicLocaliser:
    def test_add_to_client(self):
        client = tanjun.Client(mock.AsyncMock())
        localiser = tanjun.dependencies.BasicLocaliser()

        assert localiser.add_to_client(client) is None

        assert client.injector.get_type_dependency(tanjun.dependencies.AbstractLocaliser) is localiser
        assert client.injector.get_type_dependency(tanjun.dependencies.AbstractLocalizer) is localiser

    def test_get_all_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "yeet",
            {hikari.Locale.BG: "BIGGIE CHEESE", hikari.Locale.CS: "COMPUTER SENTIENT", hikari.Locale.EN_GB: "no"},
            DE="yeet",
            boom="NO",
        )

        assert localiser.get_all_variants("yeet") == {
            hikari.Locale.BG: "BIGGIE CHEESE",
            hikari.Locale.CS: "COMPUTER SENTIENT",
            hikari.Locale.EN_GB: "no",
            hikari.Locale.DE: "yeet",
            "boom": "NO",
        }

    def test_get_all_variants_ignores_default(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "ayanami",
            {hikari.Locale.ES_ES: "que?", hikari.Locale.DA: "Danken", "default": "yeet", hikari.Locale.FR: "for real"},
        )

        assert localiser.get_all_variants("ayanami") == {
            hikari.Locale.ES_ES: "que?",
            hikari.Locale.DA: "Danken",
            hikari.Locale.FR: "for real",
        }

    def test_get_all_variants_when_format(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "rei",
            {
                hikari.Locale.DA: "ok {no} meow",
                hikari.Locale.CS: "hikari {meow} nom",
                hikari.Locale.EN_GB: "{no} {meow} uwu me pws",
                hikari.Locale.JA: "bye bye bye",
            },
        )

        assert localiser.get_all_variants("rei", no="123321", meow="6969") == {
            hikari.Locale.DA: "ok 123321 meow",
            hikari.Locale.CS: "hikari 6969 nom",
            hikari.Locale.EN_GB: "123321 6969 uwu me pws",
            hikari.Locale.JA: "bye bye bye",
        }

    def test_get_all_variants_when_not_known(self):
        assert tanjun.dependencies.BasicLocaliser().get_all_variants("nope") == {}

    def test_get_all_variants_for_check_format(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:nyaa:check:DmOnly",
            {hikari.Locale.BG: "BIGGIE CHEESE", hikari.Locale.CS: "COMPUTER SENTIENT", hikari.Locale.EN_GB: "yes"},
            DE="yeet",
            boom="bleep",
        )

        assert localiser.get_all_variants("slash:nyaa:check:DmOnly") == {
            hikari.Locale.BG: "BIGGIE CHEESE",
            hikari.Locale.CS: "COMPUTER SENTIENT",
            hikari.Locale.EN_GB: "yes",
            hikari.Locale.DE: "yeet",
            "boom": "bleep",
        }

    def test_get_all_variants_when_using_global_by_command_type_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "*:commandy:check:OpOpOpOp",
            {"boopers": "boopity", hikari.Locale.BG: "see", hikari.Locale.EN_GB: "noooo"},
            en_us="cows",
            de="meows",
            woof="no",
        )

        assert localiser.get_all_variants("user_menu:commandy:check:OpOpOpOp") == {
            "boopers": "boopity",
            hikari.Locale.BG: "see",
            hikari.Locale.EN_GB: "noooo",
            hikari.Locale.EN_US: "cows",
            hikari.Locale.DE: "meows",
            "woof": "no",
        }
        assert localiser.get_all_variants("slash:commandy:check:OpOpOpOp") == {
            "boopers": "boopity",
            hikari.Locale.BG: "see",
            hikari.Locale.EN_GB: "noooo",
            hikari.Locale.EN_US: "cows",
            hikari.Locale.DE: "meows",
            "woof": "no",
        }
        assert localiser.get_all_variants("message_menu:commandy:check:OpOpOpOp") == {
            "boopers": "boopity",
            hikari.Locale.BG: "see",
            hikari.Locale.EN_GB: "noooo",
            hikari.Locale.EN_US: "cows",
            hikari.Locale.DE: "meows",
            "woof": "no",
        }
        assert localiser.get_all_variants("user_menu:command:check:OpOpOpOp") == {}

    def test_get_all_variants_when_using_global_by_command_name_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "user_menu:*:check:OpOpOpOp", {"fr": "pac", hikari.Locale.FI: "man"}, en_gb="tighty", da="boorf"
        )

        assert localiser.get_all_variants("user_menu:snoop:check:OpOpOpOp") == {
            hikari.Locale.FR: "pac",
            hikari.Locale.FI: "man",
            hikari.Locale.EN_GB: "tighty",
            hikari.Locale.DA: "boorf",
        }
        assert localiser.get_all_variants("user_menu:boop:check:OpOpOpOp") == {
            hikari.Locale.FR: "pac",
            hikari.Locale.FI: "man",
            hikari.Locale.EN_GB: "tighty",
            hikari.Locale.DA: "boorf",
        }
        assert localiser.get_all_variants("message_menu:beep:check:OpOpOpOp") == {}

    def test_get_all_variants_when_using_global_by_command_name_and_type_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "*:*:check:OpOpOpOp", {hikari.Locale.BG: "Big", hikari.Locale.EL: "ELLA"}, es_es="bon", fr="jour"
        )

        assert localiser.get_all_variants("user_menu:barf:check:OpOpOpOp") == {
            hikari.Locale.BG: "Big",
            hikari.Locale.EL: "ELLA",
            hikari.Locale.ES_ES: "bon",
            hikari.Locale.FR: "jour",
        }
        assert localiser.get_all_variants("slash:snork:check:OpOpOpOp") == {
            hikari.Locale.BG: "Big",
            hikari.Locale.EL: "ELLA",
            hikari.Locale.ES_ES: "bon",
            hikari.Locale.FR: "jour",
        }
        assert localiser.get_all_variants("message_menu:boop:check:OpOpOpOp") == {
            hikari.Locale.BG: "Big",
            hikari.Locale.EL: "ELLA",
            hikari.Locale.ES_ES: "bon",
            hikari.Locale.FR: "jour",
        }
        assert localiser.get_all_variants("slash:snoop:check:OpOpOpOp") == {
            hikari.Locale.BG: "Big",
            hikari.Locale.EL: "ELLA",
            hikari.Locale.ES_ES: "bon",
            hikari.Locale.FR: "jour",
        }
        assert localiser.get_all_variants("slash:snork:check:OpOpOp") == {}

    def test_get_all_variants_when_using_global_varients_mixed_with_specific(self):
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants("*:*:check:OpOpOpOp", {hikari.Locale.BG: "op"}, es_es="on")
            .set_variants("user_menu:barf:check:OpOpOpOp", {hikari.Locale.CS: "nooo"})
        )

        assert localiser.get_all_variants("user_menu:barf:check:OpOpOpOp") == {
            hikari.Locale.BG: "op",
            hikari.Locale.ES_ES: "on",
            hikari.Locale.CS: "nooo",
        }
        assert localiser.get_all_variants("slash:snorks:check:OpOpOpOp") == {
            hikari.Locale.BG: "op",
            hikari.Locale.ES_ES: "on",
        }

    def test_localise(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "the end", {hikari.Locale.FI: "bye"}, vi="echo", fi="meow"
        )

        assert localiser.localise("the end", "vi") == "echo"

    def test_localise_when_format(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "ANDER",
            {hikari.Locale.EN_GB: "nyaa", hikari.Locale.FR: "ashley {now}", hikari.Locale.IT: "op"},
            moomin="okokokok",
        )

        assert localiser.localise("ANDER", hikari.Locale.FR, now="444") == "ashley 444"

    def test_localise_when_tag_unknown(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants("NERV", {hikari.Locale.BG: "nom"})

        assert localiser.localise("NERV", hikari.Locale.EN_GB) is None

    def test_localise_when_id_unknown(self):
        assert tanjun.dependencies.BasicLocaliser().localise("foo", hikari.Locale.FR) is None

    def test_localize(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "the end", {hikari.Locale.FI: "bye"}, vi="echo", fi="meow"
        )

        assert localiser.localize("the end", "vi") == "echo"

    def test_localize_when_format(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "ANDER",
            {hikari.Locale.EN_GB: "nyaa", hikari.Locale.FR: "ashley {now}", hikari.Locale.IT: "op"},
            moomin="okokokok",
        )

        assert localiser.localize("ANDER", hikari.Locale.FR, now="444") == "ashley 444"

    def test_localize_when_tag_unknown(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants("NERV", {hikari.Locale.BG: "nom"})

        assert localiser.localize("NERV", hikari.Locale.EN_GB) is None

    def test_localize_when_id_unknown(self):
        assert tanjun.dependencies.BasicLocaliser().localize("foo", hikari.Locale.FR) is None

    def test_localise_for_check_format(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "message_menu:meow:check:tanjun.GuildOnly", {hikari.Locale.FI: "bye"}, vi="beeee", fi="meow"
        )

        assert localiser.localise("message_menu:meow:check:tanjun.GuildOnly", "vi") == "beeee"

    def test_localize_when_using_global_by_command_type_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "*:yeet:check:OpCheck", {hikari.Locale.BG: "nom", hikari.Locale.CS: "book em", hikari.Locale.HI: "."}
        )

        assert localiser.localize("message_menu:yeet:check:OpCheck", hikari.Locale.CS) == "book em"
        assert localiser.localize("slash:yeet:check:OpCheck", hikari.Locale.CS) == "book em"
        assert localiser.localize("user_menu:yeet:check:OpCheck", hikari.Locale.CS) == "book em"
        assert localiser.localize("user_menu:yeetn:check:OpCheck", hikari.Locale.CS) is None

    def test_localize_when_using_global_by_command_name_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "slash:*:check:OpCheck", {hikari.Locale.BG: "nom", hikari.Locale.CS: "book em", hikari.Locale.HI: "."}
        )

        assert localiser.localize("slash:yeet:check:OpCheck", hikari.Locale.CS) == "book em"
        assert localiser.localize("slash:beam:check:OpCheck", hikari.Locale.CS) == "book em"
        assert localiser.localize("slash:heat:check:OpCheck", hikari.Locale.CS) == "book em"
        assert localiser.localize("user_menu:heat:check:OpCheck", hikari.Locale.CS) is None

    def test_localize_when_using_global_by_command_name_and_type_variants(self):
        localiser = tanjun.dependencies.BasicLocaliser().set_variants(
            "*:*:check:OpCheck", {hikari.Locale.DA: "us", hikari.Locale.DE: "board", hikari.Locale.EL: "sleep"}
        )

        assert localiser.localize("message_menu:yeet:check:OpCheck", hikari.Locale.DE) == "board"
        assert localiser.localize("slash:yeet:check:OpCheck", hikari.Locale.DA) == "us"
        assert localiser.localize("slash:yeet:check:OpCheck", hikari.Locale.DE) == "board"
        assert localiser.localize("user_menu:yeet:check:OpCheck", hikari.Locale.DE) == "board"
        assert localiser.localize("user_menu:yeet:check:NotOpCheck", hikari.Locale.DE) is None

        assert localiser.localize("message_menu:meat:check:OpCheck", hikari.Locale.DE) == "board"
        assert localiser.localize("message_menu:meat:check:OpCheck", hikari.Locale.DA) == "us"
        assert localiser.localize("slash:meat:check:OpCheck", hikari.Locale.DE) == "board"
        assert localiser.localize("user_menu:meat:check:OpCheck", hikari.Locale.DE) == "board"
        assert localiser.localize("user_menu:meat:check:NotOpCheck", hikari.Locale.DE) is None

    def test_localize_when_using_global_by_command_name_and_type_variant_as_fallbackd(self):
        localiser = (
            tanjun.dependencies.BasicLocaliser()
            .set_variants("*:*:check:OpCheck", {hikari.Locale.DA: "beep"})
            .set_variants("slash:meep:check:OpCheck", {hikari.Locale.BG: "boop"})
        )

        assert localiser.localize("slash:meep:check:OpCheck", hikari.Locale.DA) == "beep"
        assert localiser.localize("slash:meep:check:OpCheck", hikari.Locale.BG) == "boop"
