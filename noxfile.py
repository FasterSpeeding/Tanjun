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
from __future__ import annotations

import pathlib
import tempfile

import nox

nox.options.sessions = ["reformat", "lint", "spell-check", "type-check", "test", "verify-types"]  # type: ignore
GENERAL_TARGETS = ["./examples", "./noxfile.py", "./tanjun", "./tests"]
PYTHON_VERSIONS = ["3.9", "3.10"]  # TODO: @nox.session(python=["3.6", "3.7", "3.8"])?


def install_requirements(session: nox.Session, *other_requirements: str) -> None:
    # --no-install --no-venv leads to it trying to install in the global venv
    # as --no-install only skips "reused" venvs and global is not considered reused.
    if not _try_find_option(session, "--skip-install", when_empty="True"):
        session.install("--upgrade", "wheel")
        session.install("--upgrade", *other_requirements)


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
    for raw_path in ["./dist", "./docs", "./.nox", "./.pytest_cache", "./hikari_tanjun.egg-info", "./coverage_html"]:
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


@nox.session(name="generate-docs", reuse_venv=True)
def generate_docs(session: nox.Session) -> None:
    """Generate docs for this project using Pdoc."""
    install_requirements(session, ".[docs]", "--use-feature=in-tree-build")
    session.log("Building docs into ./docs")
    output_directory = _try_find_option(session, "-o", "--output") or "./docs"
    session.run("pdoc", "--docformat", "numpy", "-o", output_directory, "./tanjun", "-t", "./templates")
    session.log("Docs generated: %s", pathlib.Path("./docs/index.html").absolute())

    if not _try_find_option(session, "-j", "--json", when_empty="true"):
        return

    import httpx

    # Note: this can be linked to a specific hash by adding it between raw and {file.name} as another route segment.
    code = httpx.get(
        "https://gist.githubusercontent.com/FasterSpeeding/19a6d3f44cdd0a1f3b2437a8c5eef07a/raw/json_index_docs.py"
    ).read()

    # This is saved to a temporary file to avoid the source showing up in any of the output.

    # A try, finally is used to delete the file rather than relying on delete=True behaviour
    # as on Windows the file cannot be accessed by other processes if delete is True.
    file = tempfile.NamedTemporaryFile(delete=False)
    try:
        with file:
            file.write(code)

        session.run("python", file.name, "tanjun", "-o", str(pathlib.Path(output_directory) / "search.json"))

    finally:
        pathlib.Path(file.name).unlink(missing_ok=False)


@nox.session(reuse_venv=True)
def lint(session: nox.Session) -> None:
    """Run this project's modules against the pre-defined flake8 linters."""
    install_requirements(session, ".[flake8]", "--use-feature=in-tree-build")
    session.run("flake8", *GENERAL_TARGETS)


@nox.session(reuse_venv=True, name="spell-check")
def spell_check(session: nox.Session) -> None:
    """Check this project's text-like files for common spelling mistakes."""
    install_requirements(session, ".[lint]", "--use-feature=in-tree-build")  # include_standard_requirements=False
    session.run(
        "codespell",
        *GENERAL_TARGETS,
        ".flake8",
        ".gitignore",
        "LICENSE",
        "pyproject.toml",
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "README.md",
        "./github",
        ".pre-commit-config.yaml",
    )


@nox.session(reuse_venv=True)
def build(session: nox.Session) -> None:
    """Build this project using flit."""
    install_requirements(session, "flit")
    session.log("Starting build")
    session.run("flit", "build")


@nox.session(reuse_venv=True)
def publish(session: nox.Session, test: bool = False) -> None:
    """Publish this project to pypi."""
    install_requirements(session, "flit")
    install_requirements(session, ".", "--use-feature=in-tree-build")

    env: dict[str, str] = {}

    if username := _try_find_option(session, "-u", "--username"):
        env["FLIT_USERNAME"] = username

    if password := _try_find_option(session, "-p", "--password"):
        env["FLIT_PASSWORD"] = password

    if index_url := _try_find_option(session, "-i", "--index-url"):
        env["FLIT_INDEX_URL"] = index_url

    elif test:
        env["FLIT_INDEX_URL"] = "https://test.pypi.org/legacy/"

    else:
        env["FLIT_INDEX_URL"] = "https://upload.pypi.org/legacy/"

    session.log("Initiating TestPYPI upload" if test else "Initiating PYPI upload")
    session.run("flit", "publish", env=env)


@nox.session(name="test-publish", reuse_venv=True)
def test_publish(session: nox.Session) -> None:
    """Publish this project to test pypi."""
    publish(session, test=True)


@nox.session(reuse_venv=True)
def reformat(session: nox.Session) -> None:
    """Reformat this project's modules to fit the standard style."""
    install_requirements(session, ".[reformat]", "--use-feature=in-tree-build")  # include_standard_requirements=False
    session.run("black", *GENERAL_TARGETS)
    session.run("isort", *GENERAL_TARGETS)
    session.run("sort-all", *map(str, pathlib.Path("./tanjun/").glob("**/*.py")), success_codes=[0, 1])


@nox.session(reuse_venv=True)
def test(session: nox.Session) -> None:
    """Run this project's tests using pytest."""
    install_requirements(session, ".[tests]", "--use-feature=in-tree-build")
    # TODO: can import-mode be specified in the config.
    session.run("pytest", "-n", "auto", "--import-mode", "importlib")


@nox.session(name="test-coverage", reuse_venv=True)
def test_coverage(session: nox.Session) -> None:
    """Run this project's tests while recording test coverage."""
    install_requirements(session, ".[tests]", "--use-feature=in-tree-build")
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
    install_requirements(
        session, ".[tests, type_checking]", "--use-feature=in-tree-build", "-r", "nox-requirements.txt"
    )
    _run_pyright(session)


@nox.session(name="verify-types", reuse_venv=True)
def verify_types(session: nox.Session) -> None:
    """Verify the "type completeness" of types exported by the library using Pyright."""
    install_requirements(session, ".[type_checking]", "--use-feature=in-tree-build")
    _run_pyright(session, "--verifytypes", "tanjun", "--ignoreexternal")


@nox.session(name="check-dependencies")
def check_dependencies(session: nox.Session) -> None:
    """Verify that all the dependencies declared in pyproject.toml are up to date."""
    import httpx

    # Note: this can be linked to a specific hash by adding it between raw and {file.name} as another route segment.
    with httpx.Client() as client:
        requirements = client.get(
            "https://gist.githubusercontent.com/FasterSpeeding/13e3d871f872fa09cf7bdc4144d62b2b/raw/requirements.json"
        ).json()

        # Note: this can be linked to a specific hash by adding it between raw and {file.name} as another route segment.
        code = client.get(
            "https://gist.githubusercontent.com/FasterSpeeding/13e3d871f872fa09cf7bdc4144d62b2b/raw/check_dependency.py"
        ).read()

    install_requirements(session, *requirements)
    # This is saved to a temporary file to avoid the source showing up in any of the output.

    # A try, finally is used to delete the file rather than relying on delete=True behaviour
    # as on Windows the file cannot be accessed by other processes if delete is True.
    file = tempfile.NamedTemporaryFile(delete=False)
    try:
        with file:
            file.write(code)

        session.run("python", file.name)

    finally:
        pathlib.Path(file.name).unlink(missing_ok=False)
