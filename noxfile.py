# -*- coding: utf-8 -*-
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
from __future__ import annotations

import itertools
import pathlib
import re
import shutil
from collections import abc as collections

import nox

nox.options.sessions = [
    "reformat",
    "verify-markup",
    "flake8",
    "spell-check",
    "slot-check",
    "type-check",
    "test",
    "verify-types",
]
GENERAL_TARGETS = ["./noxfile.py", "./tests"]
TOP_LEVEL_TARGETS = ["./tanjun", "./tests", "./noxfile.py"]
_BLACKLISTED_TARGETS = re.compile("^_internal/vendor/.*\\.py")
for path in pathlib.Path("./tanjun").glob("**/*.py"):
    if not _BLACKLISTED_TARGETS.match(str(path.relative_to("./tanjun")).replace("\\", "/")):
        GENERAL_TARGETS.append(str(path))


_DEV_DEP_DIR = pathlib.Path("./dev-requirements")


def _dev_dep(*values: str) -> collections.Iterator[str]:
    return itertools.chain.from_iterable(("-r", str(_DEV_DEP_DIR / f"{value}.txt")) for value in values)


def _tracked_files(session: nox.Session, *, ignore_vendor: bool = False) -> collections.Iterable[str]:
    if ignore_vendor:
        return (path for path in _tracked_files(session) if "tanjun/_internal/vendor/" not in path)

    output = session.run("git", "ls-files", external=True, log=False, silent=True)
    assert isinstance(output, str)
    return output.splitlines()


def install_requirements(session: nox.Session, *requirements: str, first_call: bool = True) -> None:
    # --no-install --no-venv leads to it trying to install in the global venv
    # as --no-install only skips "reused" venvs and global is not considered reused.
    if not _try_find_option(session, "--skip-install", when_empty="True"):
        if first_call:
            session.install("--upgrade", "wheel")

        session.install("--upgrade", *map(str, requirements))

    elif "." in requirements:
        session.install("--upgrade", "--force-reinstall", "--no-dependencies", ".")


def _try_find_option(session: nox.Session, name: str, *other_names: str, when_empty: str | None = None) -> str | None:
    args_iter = iter(session.posargs)
    names = {name, *other_names}

    for arg in args_iter:
        if arg in names:
            return next(args_iter, when_empty)


@nox.session(venv_backend="none")
def cleanup(session: nox.Session) -> None:
    """Cleanup any temporary files made in this project by its nox tasks."""
    import shutil

    # Remove directories
    for raw_path in ["./dist", "./site", "./.nox", "./.pytest_cache", "./tanjun.egg-info", "./coverage_html"]:
        path = pathlib.Path(raw_path)
        try:
            shutil.rmtree(str(path.absolute()))

        except Exception as exc:
            session.warn(f"[ FAIL ] Failed to remove '{raw_path}': {exc!s}")

        else:
            session.log(f"[  OK  ] Removed '{raw_path}'")

    # Remove individual files
    for raw_path in ["./.coverage", "./coverage_html.xml"]:
        path = pathlib.Path(raw_path)
        try:
            path.unlink()

        except Exception as exc:
            session.warn(f"[ FAIL ] Failed to remove '{raw_path}': {exc!s}")

        else:
            session.log(f"[  OK  ] Removed '{raw_path}'")


@nox.session(name="freeze-dev-deps", reuse_venv=True)
def freeze_dev_deps(session: nox.Session) -> None:
    """Upgrade the dev dependencies."""
    install_requirements(session, *_dev_dep("publish"))
    for path in pathlib.Path("./dev-requirements/").glob("*.in"):
        session.run(
            "pip-compile-cross-platform",
            "-o",
            str(path.with_name(path.name.removesuffix(".in") + ".txt")),
            "--min-python-version",
            "3.9",
            str(path),
        )


@nox.session(name="generate-docs", reuse_venv=True)
def generate_docs(session: nox.Session) -> None:
    """Generate docs for this project using Mkdoc."""
    install_requirements(session, *_dev_dep("docs"))
    output_directory = _try_find_option(session, "-o", "--output") or "./site"
    session.run("mkdocs", "build", "-d", output_directory)
    for path in ("./CHANGELOG.md", "./README.md"):
        shutil.copy(path, pathlib.Path(output_directory) / path)


@nox.session(reuse_venv=True)
def flake8(session: nox.Session) -> None:
    """Run this project's modules against the pre-defined flake8 linters."""
    install_requirements(session, *_dev_dep("flake8"))
    session.log("Running flake8")
    session.run("pflake8", *GENERAL_TARGETS, log=False)


@nox.session(reuse_venv=True, name="slot-check")
def slot_check(session: nox.Session) -> None:
    """Check this project's slotted classes for common mistakes."""
    install_requirements(session, ".", *_dev_dep("lint"))
    session.run("slotscheck", "-m", "tanjun")


@nox.session(reuse_venv=True, name="spell-check")
def spell_check(session: nox.Session) -> None:
    """Check this project's text-like files for common spelling mistakes."""
    install_requirements(session, *_dev_dep("lint"))
    session.log("Running codespell")
    session.run(
        "codespell", *_tracked_files(session, ignore_vendor=True), "--ignore-regex", "TimeSchedule|Nd", log=False
    )


@nox.session(reuse_venv=True)
def build(session: nox.Session) -> None:
    """Build this project using flit."""
    install_requirements(session, *_dev_dep("publish"))
    session.log("Starting build")
    session.run("flit", "build")


@nox.session(name="verify-markup", reuse_venv=True)
def verify_markup(session: nox.Session):
    """Verify the syntax of the repo's markup files."""
    install_requirements(session, ".", *_dev_dep("lint"))
    tracked_files = list(_tracked_files(session))

    session.log("Running pre_commit_hooks.check_toml")
    session.run(
        "python",
        "-m",
        "pre_commit_hooks.check_toml",
        *(path for path in tracked_files if path.endswith(".toml")),
        success_codes=[0, 1],
        log=False,
    )

    session.log("Running pre_commit_hooks.check_yaml")
    session.run(
        "python",
        "-m",
        "pre_commit_hooks.check_yaml",
        *(path for path in tracked_files if path.endswith(".yml") or path.endswith(".yaml")),
        success_codes=[0, 1],
        log=False,
    )


@nox.session(reuse_venv=True)
def publish(session: nox.Session, env: dict[str, str] | None = None) -> None:
    """Publish this project to pypi."""
    install_requirements(session, *_dev_dep("publish"))
    install_requirements(session, ".", first_call=False)
    session.run("flit", "publish", env=env)


@nox.session(name="test-publish", reuse_venv=True)
def test_publish(session: nox.Session) -> None:
    """Publish this project to test pypi."""
    publish(session, env={"FLIT_INDEX_URL": "https://test.pypi.org/legacy/"})


@nox.session(reuse_venv=True)
def reformat(session: nox.Session) -> None:
    """Reformat this project's modules to fit the standard style."""
    install_requirements(session, *_dev_dep("reformat"))
    session.run("black", *TOP_LEVEL_TARGETS)
    session.run("isort", *TOP_LEVEL_TARGETS)
    session.run("pycln", *TOP_LEVEL_TARGETS)

    tracked_files = list(_tracked_files(session, ignore_vendor=True))
    py_files = [path for path in tracked_files if re.fullmatch(r"^tanjun\/.+.pyi?$", path)]

    session.log("Running sort-all")
    session.run("sort-all", *py_files, success_codes=[0, 1], log=False)

    session.log("Running pre_commit_hooks.end_of_file_fixer")
    session.run("python", "-m", "pre_commit_hooks.end_of_file_fixer", *tracked_files, success_codes=[0, 1], log=False)

    session.log("Running pre_commit_hooks.trailing_whitespace_fixer")
    session.run(
        "python", "-m", "pre_commit_hooks.trailing_whitespace_fixer", *tracked_files, success_codes=[0, 1], log=False
    )


@nox.session(reuse_venv=True)
def test(session: nox.Session) -> None:
    """Run this project's tests using pytest."""
    install_requirements(session, ".", *_dev_dep("tests"))
    # TODO: can import-mode be specified in the config.
    session.run("pytest", "-n", "auto", "--import-mode", "importlib")


@nox.session(name="test-coverage", reuse_venv=True)
def test_coverage(session: nox.Session) -> None:
    """Run this project's tests while recording test coverage."""
    install_requirements(session, ".", *_dev_dep("tests"))
    # TODO: can import-mode be specified in the config.
    # https://github.com/nedbat/coveragepy/issues/1002
    session.run(
        "pytest", "-n", "auto", "--cov=tanjun", "--cov-report", "html:coverage_html", "--cov-report", "xml:coverage.xml"
    )


def _run_pyright(session: nox.Session, *args: str) -> None:
    if _try_find_option(session, "--force-env", when_empty="True"):
        session.env["PYRIGHT_PYTHON_GLOBAL_NODE"] = "off"

    if version := _try_find_option(session, "--pyright-version"):
        session.env["PYRIGHT_PYTHON_FORCE_VERSION"] = version

    session.run("python", "-m", "pyright", "--version")
    session.run("python", "-m", "pyright", *args)


@nox.session(name="type-check", reuse_venv=True)
def type_check(session: nox.Session) -> None:
    """Statically analyse and veirfy this project using Pyright."""
    install_requirements(session, ".", *_dev_dep("nox", "tests", "type-checking"))
    _run_pyright(session)
    # TODO: add allowed to fail MyPy call once it stops giving an insane amount of false-positives


@nox.session(name="verify-types", reuse_venv=True)
def verify_types(session: nox.Session) -> None:
    """Verify the "type completeness" of types exported by the library using Pyright."""
    install_requirements(session, ".", *_dev_dep("type-checking"))
    _run_pyright(session, "--verifytypes", "tanjun")
