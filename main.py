"""Deprecated CLI wrapper."""

from __future__ import annotations

import warnings

from vsensor.__main__ import main as _main

warnings.warn(
    "main.py is deprecated; use the 'vsensor' command or 'python -m vsensor'",
    DeprecationWarning,
    stacklevel=2,
)

if __name__ == "__main__":
    _main()
