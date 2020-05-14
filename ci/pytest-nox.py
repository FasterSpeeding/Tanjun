import nox.sessions

from ci import config


@nox.session(reuse_venv=True)
def pytest(session: nox.sessions.Session) -> None:
    session.install("-r", str(config.REQUIREMENTS), "-r", str(config.DEV_REQUIREMENTS))
    session.run(
        "python",
        "-m",
        "pytest",
        "-c",
        str(config.PYTEST_CONFIG),
        "-r",
        "a",
        "-n",
        "auto",
        "--cov",
        str(config.MAIN_PACKAGE),
        "--cov-config",
        str(config.COVERAGE_CONFIG),
        "--cov-report",
        "term",
        "--showlocals",
        str(config.TEST_PACKAGE),
    )
