import nox

from ci import config


@nox.session
def black(session):
    session.install("black")
    session.run("black", str(config.MAIN_PACKAGE), str(config.CI_PACKAGE))


@nox.session
def black_check(session):
    session.install("black")
    session.run("black", str(config.MAIN_PACKAGE), "--check")
