"""Command line interface for the vsensor package."""

from __future__ import annotations

import argparse
import logging
from typing import List

from .client import VSensorClient
from .config import Config
from .models import Mode


def main(argv: List[str] | None = None) -> None:
    """Run the vsensor command line interface."""
    logging.basicConfig(level=logging.INFO)
    env_cfg = Config.from_env()

    parser = argparse.ArgumentParser(description="Interact with a VSensor device")
    parser.add_argument(
        "--port",
        default=env_cfg.port,
        help="serial port [env VSENSOR_PORT]",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=env_cfg.baudrate,
        help="baud rate [env VSENSOR_BAUD]",
    )
    parser.add_argument(
        "--slave",
        type=int,
        default=env_cfg.slave_id,
        help="modbus slave id [env VSENSOR_SLAVE_ID]",
    )
    parser.add_argument(
        "--float-format",
        type=int,
        choices=range(4),
        default=env_cfg.float_format,
        help="float register format 0-3 [env VSENSOR_FLOAT_FORMAT]",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    read = sub.add_parser("read", help="read values")
    read.add_argument(
        "what",
        choices=["pressure", "output", "setpoint", "mode", "telemetry"],
        help="value to read",
    )

    setp = sub.add_parser("set", help="set values")
    setp.add_argument("what", choices=["mode", "setpoint"], help="value to set")
    setp.add_argument("value", help="value")

    args = parser.parse_args(argv)

    cfg = Config.from_env()
    cfg.port = args.port
    cfg.baudrate = args.baud
    cfg.slave_id = args.slave
    cfg.float_format = args.float_format

    client = VSensorClient(cfg)

    if args.cmd == "read":
        if args.what == "pressure":
            print(client.read_pressure())
        elif args.what == "output":
            print(client.read_output())
        elif args.what == "setpoint":
            print(client.read_auto_setpoint())
        elif args.what == "mode":
            print(client.read_mode().name)
        else:
            print(client.read_telemetry())
    elif args.cmd == "set":
        if args.what == "mode":
            client.set_mode(Mode(int(args.value)))
        else:
            client.set_auto_setpoint(float(args.value))

    client.close()


if __name__ == "__main__":
    main()
