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
import pathlib
import sys

import nox

sys.path.append(str(pathlib.Path().absolute()))

DEV_REQUIREMENTS = [
    # Temporarily assume #msater for hikari and yuyo
    "git+https://github.com/FasterSpeeding/hikari.git@task/api-impl-export",
    "git+https://github.com/FasterSpeeding/Yuyo.git@task/cache-and-list",
    "-r",
    "requirements.txt",
    "-r",
    "dev-requirements.txt",
]
PYTHON_VERSIONS = ["3.9", "3.10"]  # TODO: @nox.session(python=["3.6", "3.7", "3.8"])?
REFORMAT_DIRECTORIES = ["./examples", "noxfile.py", "./tanjun", "./tests"]
TANJUN_DIR = "./tanjun"


def install_dev_requirements(session: nox.Session) -> None:
    session.install("--upgrade", "wheel")
    session.install("--upgrade", *DEV_REQUIREMENTS)


@nox.session(name="reformat-code", reuse_venv=True)
def reformat_code(session: nox.Session) -> None:
    install_dev_requirements(session)
    session.run("black", *REFORMAT_DIRECTORIES)
    session.run("isort", *REFORMAT_DIRECTORIES)


@nox.session(reuse_venv=True)
def lint(session: nox.Session) -> None:
    install_dev_requirements(session)
    session.run("flake8", "./tanjun", "./tests")
    session.run("codespell", *REFORMAT_DIRECTORIES)


@nox.session(name="type-check", reuse_venv=True)
def type_check(session: nox.Session) -> None:
    install_dev_requirements(session)
    session.run("pyright")


@nox.session(reuse_venv=True)
def test(session: nox.Session) -> None:
    install_dev_requirements(session)
    session.install(".", "--no-deps")
    # TODO: can import-mode be specified in the config.
    session.run("pytest", "--import-mode", "importlib")
