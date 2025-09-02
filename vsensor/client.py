"""High level client for VSensor devices."""

from __future__ import annotations

import logging
import os
from typing import Optional

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

from . import registers as REG  # register constants are 1-based
from .config import Config
from .errors import VSensorError
from .models import Mode, Telemetry
from .transport import FakeTransport, RTUTransport, Transport

logger = logging.getLogger(__name__)

FLOAT_FORMATS = {
    0: (Endian.BIG, Endian.BIG),
    1: (Endian.LITTLE, Endian.BIG),
    2: (Endian.BIG, Endian.LITTLE),
    3: (Endian.LITTLE, Endian.LITTLE),
}


class VSensorClient:
    """Client providing typed access to a VSensor via Modbus."""

    def __init__(self, cfg: Optional[Config] = None, transport: Optional[Transport] = None) -> None:
        self.cfg = cfg or Config.from_env()
        if transport is not None:
            self.transport = transport
        elif os.getenv("VSENSOR_SIM") or os.getenv("VSENSOR_FAKE"):
            self.transport = FakeTransport(self.cfg)
        else:
            self.transport = RTUTransport(self.cfg)
        ff = FLOAT_FORMATS.get(self.cfg.float_format, FLOAT_FORMATS[1])
        self.byteorder, self.wordorder = ff

    @staticmethod
    def _r(addr_1_based: int) -> int:
        """Convert 1-based register address to 0-based."""
        return addr_1_based - 1

    # ---- Low level ----
    def read_u16(self, addr_1_based: int) -> int:
        regs = self.transport.read_holding_registers(self._r(addr_1_based), 1)
        return int(regs[0])

    def write_u16(self, addr_1_based: int, value: int) -> None:
        self.transport.write_register(self._r(addr_1_based), int(value))

    def read_float(self, addr_1_based: int) -> float:
        for _ in range(3):
            regs = self.transport.read_holding_registers(self._r(addr_1_based), 2)
            if len(regs) >= 2:
                dec = BinaryPayloadDecoder.fromRegisters(
                    regs, byteorder=self.byteorder, wordorder=self.wordorder
                )
                return float(dec.decode_32bit_float())
        raise VSensorError("invalid float response")

    def write_float(self, addr_1_based: int, value: float) -> None:
        b = BinaryPayloadBuilder(byteorder=self.byteorder, wordorder=self.wordorder)
        b.add_32bit_float(float(value))
        self.transport.write_registers(self._r(addr_1_based), b.to_registers())

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
        self.transport.close()
