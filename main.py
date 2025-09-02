"""Simple command line interface for the vsensor package."""

from __future__ import annotations

import argparse
import logging

from vsensor.client import VSensorClient
from vsensor.models import Mode

logging.basicConfig(level=logging.INFO)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interact with a VSensor device")
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

    args = parser.parse_args()
    client = VSensorClient()

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


if __name__ == "__main__":
    main()
