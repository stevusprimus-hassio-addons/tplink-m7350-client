"""Print the TP-Link M7350 Status page values as JSON.

Run from the project root:
    PYTHONPATH=src .venv/bin/python examples/status.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tplink_m7350 import M7350Client
from tplink_m7350.config import read_host, read_password, read_rate_unit
from tplink_m7350.status import RATE_UNITS


ENV_FILE = Path(__file__).with_name(".env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate-unit", choices=RATE_UNITS)
    args = parser.parse_args()

    client = M7350Client(host=read_host(None, ENV_FILE), password=read_password(None, ENV_FILE))
    rate_unit = read_rate_unit(args.rate_unit, ENV_FILE)
    client.login()
    print(json.dumps(client.status(summarize=True, rate_unit=rate_unit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
