"""Deprecated wrapper for backwards compatibility."""

from __future__ import annotations

import warnings
from typing import Any

from vsensor.client import VSensorClient
from vsensor.config import Config

warnings.warn(
    "modbus_driver.VSensorDriver is deprecated; use vsensor.VSensorClient",
    DeprecationWarning,
    stacklevel=2,
)


class VSensorDriver(VSensorClient):
    """Backward compatible wrapper around :class:`VSensorClient`."""

    @classmethod
    def from_cfg(cls, cfg: dict[str, Any]) -> "VSensorDriver":
        return cls(Config(**cfg))
