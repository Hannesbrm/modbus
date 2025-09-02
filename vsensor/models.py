"""Data models for the vsensor API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Mode(IntEnum):
    """Operating modes of the sensor."""

    AUTO = 0
    MANUAL = 1


@dataclass
class Telemetry:
    """Basic telemetry values returned by the sensor."""

    pressure_pa: float
    output_percent: float
    auto_setpoint: float
    mode: Mode
