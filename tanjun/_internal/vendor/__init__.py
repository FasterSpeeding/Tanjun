from __future__ import annotations

__all__ = ["inspect"]

import sys


if sys.version_info >= (3, 10):
    import inspect

else:
    from . import inspect
