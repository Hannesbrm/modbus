"""Deprecated configuration wrapper."""

from __future__ import annotations

import warnings
from dataclasses import asdict

from vsensor.config import Config

warnings.warn(
    "config.load_config is deprecated; use vsensor.config.Config.from_env",
    DeprecationWarning,
    stacklevel=2,
)


def load_config() -> dict[str, object]:
    """Return configuration as dict for backwards compatibility."""
    return asdict(Config.from_env())
