"""Deprecated register definitions wrapper."""

from __future__ import annotations

import warnings

from vsensor.registers import *  # noqa: F401,F403

warnings.warn(
    "registers module is deprecated; use vsensor.registers",
    DeprecationWarning,
    stacklevel=2,
)
