from typing import Any, Callable
from typing_extensions import ParamSpec, Concatenate


P = ParamSpec("P")
MyAlias = Callable[Concatenate[int, P], Any]

x: MyAlias[...]
