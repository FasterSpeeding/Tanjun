import pathlib
import runpy
import sys

sys.path.append(str(pathlib.Path().absolute()))


root_dir = pathlib.Path("ci")
for file in root_dir.rglob("*"):
    if file.is_file() and file.name.endswith("nox.py"):
        runpy.run_path(str(file))
