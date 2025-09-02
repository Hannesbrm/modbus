import contextlib
from typing import Any

from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.framer.rtu_framer import ModbusRtuFramer
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

import registers as REG

FLOAT_FORMATS = {
    0: (Endian.BIG, Endian.BIG),
    1: (Endian.LITTLE, Endian.BIG),
    2: (Endian.BIG, Endian.LITTLE),
    3: (Endian.LITTLE, Endian.LITTLE),
}


class VSensorDriver:
    """Minimaler Treiber für CMR Controls V‑Sensor."""

    def __init__(
        self,
        *,
        port: str,
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        timeout: float = 1.5,
        slave_id: int = 1,
        float_format: int = 1,
    ) -> None:
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate,
            parity=parity,
            stopbits=stopbits,
            bytesize=bytesize,
            timeout=timeout,
            retries=2,
            retry_on_empty=True,
            retry_on_invalid=True,
            close_comm_on_error=True,
            framer=ModbusRtuFramer,
        )
        self.slave_id = slave_id
        self.port = port
        self.float_format = int(float_format)
        self.byteorder, self.wordorder = FLOAT_FORMATS.get(
            self.float_format, FLOAT_FORMATS[1]
        )

    @classmethod
    def from_cfg(cls, cfg: dict[str, Any]) -> "VSensorDriver":
        return cls(
            port=cfg["PORT"],
            baudrate=cfg["BAUD"],
            parity=cfg["PARITY"],
            stopbits=cfg["STOPBITS"],
            bytesize=cfg["BYTESIZE"],
            timeout=cfg["TIMEOUT"],
            slave_id=cfg["SLAVE_ID"],
            float_format=cfg.get("FLOAT_FORMAT", 1),
        )

    def connect(self) -> None:
        if not self.client.connect():
            raise ConnectionError(f"Serielle Verbindung fehlgeschlagen auf {self.port}")

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.client.close()

    @staticmethod
    def _r(addr_1_based: int) -> int:
        """Modbus-Adressen sind 0-basiert."""
        return addr_1_based - 1

    def _call(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except ModbusIOException as exc:
            raise TimeoutError("Modbus Timeout") from exc
        except ModbusException as exc:
            raise RuntimeError(f"Modbus-Fehler: {exc}") from exc
        if result is None:
            raise TimeoutError("Modbus Timeout")
        if result.isError():
            raise RuntimeError(f"Modbus-Fehler: {result}")
        return result

    # ---- Low-level ----
    def read_u16(self, addr_1_based: int) -> int:
        rr = self._call(
            self.client.read_holding_registers,
            address=self._r(addr_1_based),
            count=1,
            slave=self.slave_id,
        )
        return int(rr.registers[0])

    def write_u16(self, addr_1_based: int, value: int) -> None:
        self._call(
            self.client.write_register,
            address=self._r(addr_1_based),
            value=int(value),
            slave=self.slave_id,
        )

    def read_float(self, addr_1_based: int) -> float:
        for _ in range(3):
            rr = self._call(
                self.client.read_holding_registers,
                address=self._r(addr_1_based),
                count=2,
                slave=self.slave_id,
            )
            if getattr(rr, "registers", None) and len(rr.registers) >= 2:
                dec = BinaryPayloadDecoder.fromRegisters(
                    rr.registers, byteorder=self.byteorder, wordorder=self.wordorder
                )
                return float(dec.decode_32bit_float())
        raise RuntimeError("invalid float response")

    def write_float(self, addr_1_based: int, value: float) -> None:
        b = BinaryPayloadBuilder(byteorder=self.byteorder, wordorder=self.wordorder)
        b.add_32bit_float(float(value))
        regs = b.to_registers()
        self._call(
            self.client.write_registers,
            address=self._r(addr_1_based),
            values=regs,
            slave=self.slave_id,
        )

    # ---- High-level convenience methods ----
    def get_pressure_pa(self) -> float:
        return self.read_float(REG.PRESSURE_PA)

    def get_output_percent(self) -> float:
        return self.read_float(REG.OUTPUT_PERCENT)

    def get_auto_setpoint(self) -> float:
        return self.read_float(REG.AUTO_SETPOINT)

    def set_auto_setpoint(self, value: float) -> None:
        self.write_float(REG.AUTO_SETPOINT, value)

    def get_mode(self) -> int:
        return self.read_u16(REG.MODE)

    def set_mode(self, value: int) -> None:
        self.write_u16(REG.MODE, value)
