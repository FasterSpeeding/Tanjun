import nox.sessions

from ci import config


@nox.session(reuse_venv=True)
def black(session: nox.sessions.Session) -> None:
    session.install("black")
    session.run("black", str(config.MAIN_PACKAGE), str(config.CI_PACKAGE))


@nox.session(reuse_venv=True)
def black_check(session: nox.sessions.Session) -> None:
    session.install("black")
    session.run("black", str(config.MAIN_PACKAGE), "--check")
