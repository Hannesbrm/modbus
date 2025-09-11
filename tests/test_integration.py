from __future__ import annotations

import os
import threading
import time

import pytest
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ModbusIOException
from pymodbus.server import StartTcpServer

from vsensor.client import VSensorClient
from vsensor.config import Config
from vsensor.transport import Transport

datastore = pytest.importorskip("pymodbus.datastore")
ModbusSequentialDataBlock = datastore.ModbusSequentialDataBlock  # type: ignore[attr-defined]
ModbusServerContext = datastore.ModbusServerContext  # type: ignore[attr-defined]


pytestmark = pytest.mark.hardware

PORT = int(os.getenv("VSENSOR_TEST_PORT", "5020"))


class TcpTransport(Transport):
    def __init__(self, host: str = "localhost", port: int = PORT, slave_id: int = 1) -> None:
        self._client = ModbusTcpClient(host=host, port=port)
        self._client.connect()
        self._slave_id = slave_id
        self._lock = threading.Lock()

    def _call(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs, slave=self._slave_id)
        except (ModbusException, ModbusIOException):
            raise
        if result is None or result.isError():
            raise RuntimeError("modbus error")
        return result

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        with self._lock:
            rr = self._call(self._client.read_holding_registers, address=address, count=count)
            return list(rr.registers)

    def write_register(self, address: int, value: int) -> None:
        with self._lock:
            self._call(self._client.write_register, address=address, value=value)

    def write_registers(self, address: int, values):
        with self._lock:
            self._call(self._client.write_registers, address=address, values=list(values))

    def close(self) -> None:
        with self._lock:
            self._client.close()


def _start_server() -> None:
    store = ModbusSequentialDataBlock(0, [0] * 1000)
    context = ModbusServerContext(slaves=store, single=True)
    StartTcpServer(context=context, address=("localhost", PORT))


def test_integration_roundtrip() -> None:
    thread = threading.Thread(target=_start_server, daemon=True)
    thread.start()
    time.sleep(0.5)
    cfg = Config()
    client = VSensorClient(cfg, transport=TcpTransport())
    client.set_auto_setpoint(42.0)
    assert abs(client.read_auto_setpoint() - 42.0) < 0.001
    client.close()
