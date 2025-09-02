"""Configuration handling for vsensor."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


def _get_env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default


@dataclass
class Config:
    """Runtime configuration for the VSensor client."""

    port: str = os.getenv(
        "VSENSOR_PORT", "COM6" if os.name == "nt" else "/dev/ttyUSB0"
    )
    baudrate: int = _get_env_int("VSENSOR_BAUD", 9600)
    parity: str = os.getenv("VSENSOR_PARITY", "N")
    stopbits: int = _get_env_int("VSENSOR_STOPBITS", 1)
    bytesize: int = _get_env_int("VSENSOR_BYTESIZE", 8)
    timeout: float = _get_env_float("VSENSOR_TIMEOUT", 1.5)
    slave_id: int = _get_env_int("VSENSOR_SLAVE_ID", 1)
    float_format: int = _get_env_int("VSENSOR_FLOAT_FORMAT", 1)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls()
