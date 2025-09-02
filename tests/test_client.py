from __future__ import annotations

import pytest

from vsensor.client import VSensorClient
from vsensor.config import Config
from vsensor.errors import TimeoutError
from vsensor.transport import Transport
from vsensor import registers as REG
from vsensor.models import Mode


class FakeTransport(Transport):
    def __init__(self) -> None:
        self.regs: dict[int, int] = {}
        self.last_address: int | None = None

    def read_holding_registers(self, address: int, count: int) -> list[int]:
        self.last_address = address
        return [self.regs.get(address + i, 0) for i in range(count)]

    def write_register(self, address: int, value: int) -> None:
        self.last_address = address
        self.regs[address] = value

    def write_registers(self, address: int, values):
        self.last_address = address
        for i, v in enumerate(values):
            self.regs[address + i] = v

    def close(self) -> None:
        pass


@pytest.mark.parametrize("fmt", [0, 1, 2, 3])
def test_float_formats(fmt: int) -> None:
    cfg = Config(float_format=fmt)
    client = VSensorClient(cfg, transport=FakeTransport())
    client.write_float(REG.AUTO_SETPOINT, 1.23)
    assert abs(client.read_float(REG.AUTO_SETPOINT) - 1.23) < 0.001


def test_register_address_is_zero_based() -> None:
    ft = FakeTransport()
    client = VSensorClient(Config(), transport=ft)
    ft.regs[REG.MODE - 1] = 1
    client.read_mode()
    assert ft.last_address == REG.MODE - 1


def test_mode_validation() -> None:
    ft = FakeTransport()
    client = VSensorClient(Config(), transport=ft)
    client.set_mode(Mode.MANUAL)
    assert client.read_mode() == Mode.MANUAL


def test_invalid_mode_raises() -> None:
    ft = FakeTransport()
    ft.regs[REG.MODE - 1] = 42
    client = VSensorClient(Config(), transport=ft)
    with pytest.raises(ValueError):
        client.read_mode()


class TimeoutTransport(Transport):
    def read_holding_registers(self, address: int, count: int) -> list[int]:
        raise TimeoutError("boom")

    def write_register(self, address: int, value: int) -> None:
        raise TimeoutError("boom")

    def write_registers(self, address: int, values):
        raise TimeoutError("boom")

    def close(self) -> None:
        pass


def test_timeout_path() -> None:
    client = VSensorClient(Config(), transport=TimeoutTransport())
    with pytest.raises(TimeoutError):
        client.read_pressure()
