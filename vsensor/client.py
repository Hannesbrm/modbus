"""High level client for VSensor devices."""

from __future__ import annotations

import logging
import os
import struct
from typing import Literal, Optional

from . import registers as REG  # register constants are 1-based
from .config import Config
from .errors import VSensorError
from .models import Mode, Telemetry
from .transport import FakeTransport, RTUTransport, Transport

logger = logging.getLogger(__name__)

FLOAT_FORMATS: dict[int, tuple[Literal["big", "little"], Literal["big", "little"]]] = {
    0: ("big", "big"),
    1: ("little", "big"),
    2: ("big", "little"),
    3: ("little", "little"),
}


class VSensorClient:
    """Client providing typed access to a VSensor via Modbus."""

    def __init__(self, cfg: Optional[Config] = None, transport: Optional[Transport] = None) -> None:
        self.cfg = cfg or Config.from_env()
        self.transport = transport
        ff = FLOAT_FORMATS.get(self.cfg.float_format, FLOAT_FORMATS[1])
        self.byteorder, self.wordorder = ff

    def connect(self) -> None:
        """Initialise the transport lazily."""
        if self.transport is not None:
            return
        if os.getenv("VSENSOR_SIM") or os.getenv("VSENSOR_FAKE"):
            self.transport = FakeTransport(self.cfg)
        else:
            self.transport = RTUTransport(self.cfg)

    @staticmethod
    def _r(addr_1_based: int) -> int:
        """Convert 1-based register address to 0-based."""
        return addr_1_based - 1

    # ---- Low level ----
    def _ensure_transport(self) -> Transport:
        if self.transport is None:
            raise VSensorError("not connected")
        return self.transport

    def read_u16(self, addr_1_based: int) -> int:
        regs = self._ensure_transport().read_holding_registers(self._r(addr_1_based), 1)
        return int(regs[0])

    def write_u16(self, addr_1_based: int, value: int) -> None:
        self._ensure_transport().write_register(self._r(addr_1_based), int(value))

    def read_float(self, addr_1_based: int) -> float:
        for _ in range(3):
            regs = self._ensure_transport().read_holding_registers(self._r(addr_1_based), 2)
            if len(regs) >= 2:
                return self._unpack_float(regs)
        raise VSensorError("invalid float response")

    def write_float(self, addr_1_based: int, value: float) -> None:
        regs = self._pack_float(value)
        self._ensure_transport().write_registers(self._r(addr_1_based), regs)

    # ---- High level ----
    def read_pressure(self) -> float:
        return self.read_float(REG.PRESSURE_PA)

    def read_output(self) -> float:
        return self.read_float(REG.OUTPUT_PERCENT)

    def read_auto_setpoint(self) -> float:
        return self.read_float(REG.AUTO_SETPOINT)

    def set_auto_setpoint(self, value: float) -> None:
        self.write_float(REG.AUTO_SETPOINT, value)

    def read_mode(self) -> Mode:
        return Mode(self.read_u16(REG.MODE))

    def set_mode(self, value: Mode) -> None:
        self.write_u16(REG.MODE, int(value))

    def read_telemetry(self) -> Telemetry:
        return Telemetry(
            pressure_pa=self.read_pressure(),
            output_percent=self.read_output(),
            auto_setpoint=self.read_auto_setpoint(),
            mode=self.read_mode(),
        )

    def close(self) -> None:
        """Close the underlying transport."""
        if self.transport is not None:
            self.transport.close()

    def _unpack_float(self, regs: list[int]) -> float:
        words = regs if self.wordorder == "big" else list(reversed(regs))
        raw = b"".join(int(w).to_bytes(2, self.byteorder) for w in words)
        fmt = ">" if self.byteorder == "big" else "<"
        return float(struct.unpack(fmt + "f", raw)[0])

    def _pack_float(self, value: float) -> list[int]:
        fmt = ">" if self.byteorder == "big" else "<"
        raw = struct.pack(fmt + "f", float(value))
        words = [int.from_bytes(raw[i : i + 2], self.byteorder) for i in (0, 2)]
        if self.wordorder == "little":
            words.reverse()
        return words
