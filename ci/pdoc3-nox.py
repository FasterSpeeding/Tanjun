import nox

from ci import config


@nox.session()
def pdoc(session):
    session.install("-r", str(config.REQUIREMENTS), "pdoc3==0.8.1")
    session.run(
        "python",
        "-m",
        "pdoc",
        str(config.MAIN_PACKAGE),
        "--html",
        "--output-dir",
        str(config.ARTIFACT_DIRECTORY),
        "--template-dir",
        str(config.DOCUMENTATION_DIRECTORY),
        "--force",
    )
