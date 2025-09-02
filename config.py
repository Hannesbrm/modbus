import os
from typing import Any


def _int(env: str, default: int) -> int:
    try:
        return int(os.getenv(env, default))
    except Exception:
        return default


def load_config() -> dict[str, Any]:
    return {
        # Serial
        "PORT": os.getenv("VSENSOR_PORT", "COM6" if os.name == "nt" else "/dev/ttyUSB0"),
        "BAUD": _int("VSENSOR_BAUD", 9600),
        "PARITY": os.getenv("VSENSOR_PARITY", "N"),
        "STOPBITS": _int("VSENSOR_STOPBITS", 1),
        "BYTESIZE": _int("VSENSOR_BYTESIZE", 8),
        "TIMEOUT": float(os.getenv("VSENSOR_TIMEOUT", "1.5")),
        "SLAVE_ID": _int("VSENSOR_SLAVE_ID", 1),
        "FLOAT_FORMAT": _int("VSENSOR_FLOAT_FORMAT", 1),
        # App
        "POLL_INTERVAL_SEC": float(os.getenv("POLL_INTERVAL_SEC", "1.0")),
    }
