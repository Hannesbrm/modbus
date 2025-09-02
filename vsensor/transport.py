"""Transport abstraction for Modbus communication."""

from __future__ import annotations

import logging
import threading
from typing import Iterable, List

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.framer.rtu_framer import ModbusRtuFramer

from .config import Config
from .errors import TimeoutError, TransportError

logger = logging.getLogger(__name__)


class Transport:
    """Abstract base class for transport implementations."""

    def read_holding_registers(self, address: int, count: int) -> List[int]:
        raise NotImplementedError

    def write_register(self, address: int, value: int) -> None:
        raise NotImplementedError

    def write_registers(self, address: int, values: Iterable[int]) -> None:
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - default
        """Close transport resources."""


class RTUTransport(Transport):
    """Serial RTU transport based on pymodbus."""

    def __init__(self, cfg: Config) -> None:
        self._client = ModbusSerialClient(
            port=cfg.port,
            baudrate=cfg.baudrate,
            parity=cfg.parity,
            stopbits=cfg.stopbits,
            bytesize=cfg.bytesize,
            timeout=cfg.timeout,
            close_comm_on_error=True,
            framer=ModbusRtuFramer,  # type: ignore[arg-type]
        )
        self._slave_id = cfg.slave_id
        self._lock = threading.Lock()
        self._retries = 3
        if not self._client.connect():
            raise TransportError(f"Serial connection failed on {cfg.port}")

    def _call(self, func, *args, **kwargs):
        for attempt in range(1, self._retries + 1):
            try:
                result = func(*args, **kwargs, slave=self._slave_id)
            except ModbusIOException as exc:
                logger.debug("transport timeout (attempt %s/%s): %s", attempt, self._retries, exc)
                if attempt == self._retries:
                    raise TimeoutError("modbus timeout") from exc
                continue
            except ModbusException as exc:
                logger.debug("transport error (attempt %s/%s): %s", attempt, self._retries, exc)
                if attempt == self._retries:
                    raise TransportError(str(exc)) from exc
                continue
            if result is None:
                if attempt == self._retries:
                    raise TimeoutError("modbus timeout")
                continue
            if result.isError():
                if attempt == self._retries:
                    raise TransportError(str(result))
                continue
            return result
        raise TransportError("modbus error")

    def read_holding_registers(self, address: int, count: int) -> List[int]:
        with self._lock:
            rr = self._call(self._client.read_holding_registers, address=address, count=count)
            return list(rr.registers)

    def write_register(self, address: int, value: int) -> None:
        with self._lock:
            self._call(self._client.write_register, address=address, value=value)

    def write_registers(self, address: int, values: Iterable[int]) -> None:
        with self._lock:
            self._call(self._client.write_registers, address=address, values=list(values))

    def close(self) -> None:
        with self._lock:
            try:
                self._client.close()
            finally:
                pass


class FakeTransport(Transport):
    """In-memory transport used for simulations."""

    def __init__(self, cfg: Config | None = None) -> None:
        self._regs: dict[int, int] = {}
        self._hb = 0

    def read_holding_registers(self, address: int, count: int) -> List[int]:
        try:
            from . import registers as REG
            if address == REG.HEARTBEAT - 1:
                self._hb = (self._hb + 1) & 0xFFFF
                self._regs[address] = self._hb
        except Exception:  # pragma: no cover - optional
            pass
        return [self._regs.get(address + i, 0) for i in range(count)]

    def write_register(self, address: int, value: int) -> None:
        self._regs[address] = int(value)

    def write_registers(self, address: int, values: Iterable[int]) -> None:
        for i, v in enumerate(values):
            self._regs[address + i] = int(v)

    def close(self) -> None:  # pragma: no cover - nothing to do
        pass
