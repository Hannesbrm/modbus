from __future__ import annotations
1: (Endian.Little, Endian.Big), # Little Endian, word swap (häufig bei CMR)
2: (Endian.Big, Endian.Little),# Big Endian, word swap
3: (Endian.Little, Endian.Little) # Little Endian, no swap
}


class VSensorDriver:
def __init__(self, *, port: str, baudrate: int = 9600, parity: str = 'N', stopbits: int = 1,
bytesize: int = 8, timeout: float = 1.0, slave_id: int = 1, float_format: int = 1):
if float_format not in FLOAT_FORMATS:
raise ValueError("float_format must be 0..3")
self.port = port
self.slave_id = slave_id
self.byteorder, self.wordorder = FLOAT_FORMATS[float_format]
self.client = ModbusSerialClient(
port=port, baudrate=baudrate, parity=parity, stopbits=stopbits, bytesize=bytesize, timeout=timeout
)


@classmethod
def from_cfg(cls, cfg: dict) -> "VSensorDriver":
return cls(
port=cfg["PORT"], baudrate=cfg["BAUD"], parity=cfg["PARITY"], stopbits=cfg["STOPBITS"],
bytesize=cfg["BYTESIZE"], timeout=cfg["TIMEOUT"], slave_id=cfg["SLAVE_ID"], float_format=cfg["FLOAT_FORMAT"]
)


def connect(self) -> None:
if not self.client.connect():
raise RuntimeError(f"Serielle Verbindung fehlgeschlagen auf {self.port}")


def close(self) -> None:
with contextlib.suppress(Exception):
self.client.close()


@staticmethod
def _r(addr_1_based: int) -> int:
return addr_1_based - 1


# ---- Low-level ----
def read_u16(self, addr_1_based: int) -> int:
rr = self.client.read_holding_registers(address=self._r(addr_1_based), count=1, slave=self.slave_id)
if rr.isError():
raise RuntimeError(rr)
return int(rr.registers[0])


def write_u16(self, addr_1_based: int, value: int) -> None:
rq = self.client.write_register(address=self._r(addr_1_based), value=int(value), slave=self.slave_id)
if rq.isError():
raise RuntimeError(rq)


def read_float(self, addr_1_based: int) -> float:
rr = self.client.read_holding_registers(address=self._r(addr_1_based), count=2, slave=self.slave_id)
if rr.isError():
raise RuntimeError(rr)
dec = BinaryPayloadDecoder.fromRegisters(rr.registers, byteorder=self.byteorder, wordorder=self.wordorder)
return float(dec.decode_32bit_float())


def write_float(self, addr_1_based: int, value: float) -> None:
b = BinaryPayloadBuilder(byteorder=self.byteorder, wordorder=self.wordorder)
b.add_32bit_float(float(value))
regs = b.to_registers()
rq = self.client.write_registers(address=self._r(addr_1_based), values=regs, slave=self.slave_id)
if rq.isError():
raise RuntimeError(rq)
