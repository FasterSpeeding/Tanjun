import nox.sessions

from ci import config


SUCCESS_CODES = list(range(0, 256))


@nox.session(reuse_venv=True)
def pylint(session: nox.sessions.Session) -> None:
    session.install("-r", str(config.REQUIREMENTS), "-r", str(config.DEV_REQUIREMENTS))
    session.run("pylint", str(config.MAIN_PACKAGE), "--rcfile", str(config.PYLINT_CONFIG), success_codes=SUCCESS_CODES)
