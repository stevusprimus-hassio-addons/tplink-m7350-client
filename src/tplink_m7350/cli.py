"""Command-line entry point for quick router experiments."""

from __future__ import annotations

import argparse
import getpass

from .client import M7350Client, pretty_json
from .config import read_password


def main() -> int:
    parser = argparse.ArgumentParser(prog="tplink-m7350")
    parser.add_argument("--host", default="http://192.168.0.1")
    parser.add_argument("--password")
    parser.add_argument("--env-file", default=".env")

    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("load-auth")
    subcommands.add_parser("login")

    call = subcommands.add_parser("call")
    call.add_argument("module")
    call.add_argument("action", type=int)
    call.add_argument("--no-auth", action="store_true")

    args = parser.parse_args()
    password = read_password(args.password, args.env_file)
    client = M7350Client(host=args.host, password=password)

    if args.command == "load-auth":
        print(pretty_json(client.load_auth()))
        return 0

    if args.command == "login":
        password = password or getpass.getpass("Router password: ")
        print(client.login(password))
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
