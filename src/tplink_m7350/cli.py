"""Command-line entry point for quick router experiments."""

from __future__ import annotations

import argparse
import getpass

from .client import M7350Client, pretty_json
from .config import read_host, read_password, read_rate_unit
from .status import RATE_UNITS


def main() -> int:
    parser = argparse.ArgumentParser(prog="tplink-m7350")
    parser.add_argument("--host")
    parser.add_argument("--password")
    parser.add_argument("--env-file", default=".env")

    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("load-auth")
    subcommands.add_parser("login")
    status = subcommands.add_parser("status")
    status.add_argument("--raw", action="store_true")
    status.add_argument("--rate-unit", choices=RATE_UNITS)

    call = subcommands.add_parser("call")
    call.add_argument("module")
    call.add_argument("action", type=int)
    call.add_argument("--no-auth", action="store_true")

    args = parser.parse_args()
    host = read_host(args.host, args.env_file)
    password = read_password(args.password, args.env_file)
    rate_unit = read_rate_unit(getattr(args, "rate_unit", None), args.env_file)
    client = M7350Client(host=host, password=password)

    if args.command == "load-auth":
        print(pretty_json(client.load_auth()))
        return 0

    if args.command == "login":
        password = password or getpass.getpass("Router password: ")
        print(client.login(password))
        return 0

    if args.command == "status":
        password = password or getpass.getpass("Router password: ")
        client.login(password)
        print(pretty_json(client.status(summarize=not args.raw, rate_unit=rate_unit)))
        return 0

    if args.command == "call":
        if not args.no_auth:
            password = password or getpass.getpass("Router password: ")
            client.login(password)
        print(pretty_json(client.call(args.module, args.action, authenticated=not args.no_auth)))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
