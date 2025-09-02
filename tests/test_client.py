from __future__ import annotations

from vsensor.client import VSensorClient
from vsensor.config import Config
from vsensor.transport import Transport
from vsensor import registers as REG


class FakeTransport(Transport):
    def __init__(self) -> None:
        self.regs: dict[int, int] = {}

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        return [self.regs.get(address + i, 0) for i in range(count)]

    def write_register(self, address: int, value: int) -> None:
        self.regs[address] = value

    def write_registers(self, address: int, values):
        for i, v in enumerate(values):
            self.regs[address + i] = v

    def close(self) -> None:
        pass


def test_read_write_float() -> None:
    cfg = Config(float_format=1)
    client = VSensorClient(cfg, transport=FakeTransport())
    client.write_float(REG.AUTO_SETPOINT, 12.34)
    assert abs(client.read_float(REG.AUTO_SETPOINT) - 12.34) < 0.001


def test_endianness() -> None:
    cfg = Config(float_format=2)
    client = VSensorClient(cfg, transport=FakeTransport())
    client.write_float(REG.AUTO_SETPOINT, 1.0)
    assert abs(client.read_float(REG.AUTO_SETPOINT) - 1.0) < 0.001
