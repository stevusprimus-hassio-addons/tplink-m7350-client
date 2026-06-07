"""Configuration helpers for local CLI usage."""

from __future__ import annotations

import os
from pathlib import Path


PASSWORD_KEYS = ("TPLINK_M7350_PASSWORD", "TPLINK_PASSWORD", "ROUTER_PASSWORD")
HOST_KEYS = ("TPLINK_M7350_IP", "TPLINK_M7350_HOST", "TPLINK_HOST", "ROUTER_HOST")
DEFAULT_HOST = "http://192.168.0.1"


def load_dotenv(path: str | Path = ".env") -> dict[str, str]:
    """Load simple KEY=VALUE pairs from a dotenv file.

    This intentionally supports only the common local-dev subset: blank lines,
    comments, optional `export`, and single/double quoted values.
    """

    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in dotenv_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_comment(value.strip())
        values[key] = _strip_quotes(value)
    return values


def read_password(cli_password: str | None, dotenv_path: str | Path = ".env") -> str | None:
    """Return the router password from CLI, environment, or `.env`."""

    if cli_password:
        return cli_password

    for key in PASSWORD_KEYS:
        value = os.environ.get(key)
        if value:
            return value

    dotenv = load_dotenv(dotenv_path)
    for key in PASSWORD_KEYS:
        value = dotenv.get(key)
        if value:
            return value

    return None


def read_host(cli_host: str | None, dotenv_path: str | Path = ".env") -> str:
    """Return the router host URL from CLI, environment, `.env`, or default."""

    if cli_host:
        return normalize_host(cli_host)

    for key in HOST_KEYS:
        value = os.environ.get(key)
        if value:
            return normalize_host(value)

    dotenv = load_dotenv(dotenv_path)
    for key in HOST_KEYS:
        value = dotenv.get(key)
        if value:
            return normalize_host(value)

    return DEFAULT_HOST


def normalize_host(value: str) -> str:
    """Normalize a bare router IP/host into an HTTP URL."""

    host = value.strip().rstrip("/")
    if not host:
        return DEFAULT_HOST
    if "://" not in host:
        host = f"http://{host}"
    return host


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _strip_comment(value: str) -> str:
    in_quote: str | None = None
    for index, char in enumerate(value):
        if char in {"'", '"'}:
            in_quote = None if in_quote == char else char
        elif char == "#" and in_quote is None:
            return value[:index].rstrip()
    return value
