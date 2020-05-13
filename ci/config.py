import pathlib


REQUIREMENTS = pathlib.Path("requirements.txt")
DEV_REQUIREMENTS = pathlib.Path("dev-requirements.txt")
FULL_REQUIREMENTS = (REQUIREMENTS, DEV_REQUIREMENTS)

MAIN_PACKAGE = pathlib.Path("tanjun")
TEST_PACKAGE = pathlib.Path("tests")
CI_PACKAGE = pathlib.Path("ci")

ARTIFACT_DIRECTORY = pathlib.Path("public")
DOCUMENTATION_DIRECTORY = pathlib.Path("docs")

PYLINT_CONFIG = pathlib.Path("pylint.ini")
