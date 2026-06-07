"""Print the TP-Link M7350 Status page values as JSON.

Run from the project root:
    PYTHONPATH=src .venv/bin/python examples/status.py
"""

from __future__ import annotations

import json
from pathlib import Path

from tplink_m7350 import M7350Client
from tplink_m7350.config import read_host, read_password


ENV_FILE = Path(__file__).with_name(".env")


def main() -> int:
    client = M7350Client(host=read_host(None, ENV_FILE), password=read_password(None, ENV_FILE))
    client.login()
    print(json.dumps(client.status(summarize=True), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
