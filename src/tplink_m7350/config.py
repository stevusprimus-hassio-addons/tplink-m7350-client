"""Configuration helpers for local CLI usage."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .status import DEFAULT_RATE_UNIT, normalize_rate_unit


PASSWORD_KEYS = ("TPLINK_M7350_PASSWORD", "TPLINK_PASSWORD", "ROUTER_PASSWORD")
HOST_KEYS = ("TPLINK_M7350_IP", "TPLINK_M7350_HOST", "TPLINK_HOST", "ROUTER_HOST")
PORT_KEYS = ("TPLINK_M7350_PORT", "TPLINK_PORT", "ROUTER_PORT")
RATE_UNIT_KEYS = ("TPLINK_M7350_RATE_UNIT", "TPLINK_RATE_UNIT", "ROUTER_RATE_UNIT")
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


def read_host(
    cli_host: str | None,
    dotenv_path: str | Path = ".env",
    cli_port: str | int | None = None,
) -> str:
    """Return the router host URL from CLI, environment, `.env`, or default."""

    port = read_port(cli_port, dotenv_path)

    if cli_host:
        return normalize_host(cli_host, port=port)

    for key in HOST_KEYS:
        value = os.environ.get(key)
        if value:
            return normalize_host(value, port=port)

    dotenv = load_dotenv(dotenv_path)
    for key in HOST_KEYS:
        value = dotenv.get(key)
        if value:
            return normalize_host(value, port=port)

    return normalize_host(DEFAULT_HOST, port=port)


def read_port(cli_port: str | int | None, dotenv_path: str | Path = ".env") -> int | None:
    """Return the configured router HTTP port."""

    if cli_port:
        return normalize_port(cli_port)

    for key in PORT_KEYS:
        value = os.environ.get(key)
        if value:
            return normalize_port(value)

    dotenv = load_dotenv(dotenv_path)
    for key in PORT_KEYS:
        value = dotenv.get(key)
        if value:
            return normalize_port(value)

    return None


def read_rate_unit(cli_rate_unit: str | None, dotenv_path: str | Path = ".env") -> str:
    """Return the status speed display unit from CLI, environment, `.env`, or default."""

    if cli_rate_unit:
        return normalize_rate_unit(cli_rate_unit)

    for key in RATE_UNIT_KEYS:
        value = os.environ.get(key)
        if value:
            return normalize_rate_unit(value)

    dotenv = load_dotenv(dotenv_path)
    for key in RATE_UNIT_KEYS:
        value = dotenv.get(key)
        if value:
            return normalize_rate_unit(value)

    return DEFAULT_RATE_UNIT


def normalize_host(value: str, *, port: str | int | None = None) -> str:
    """Normalize a bare router IP/host into an HTTP URL."""

    host = value.strip().rstrip("/")
    if not host:
        host = DEFAULT_HOST
    if "://" not in host:
        host = f"http://{host}"

    normalized_port = normalize_port(port) if port else None
    if normalized_port is None:
        return host

    parts = urlsplit(host)
    if parts.port is not None:
        return host

    netloc = parts.hostname or parts.netloc
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if parts.username or parts.password:
        auth = parts.username or ""
        if parts.password:
            auth = f"{auth}:{parts.password}"
        netloc = f"{auth}@{netloc}"
    netloc = f"{netloc}:{normalized_port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def normalize_port(value: str | int) -> int:
    """Validate and normalize a TCP port value."""

    try:
        port = int(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"invalid port {value!r}; expected 1-65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError(f"invalid port {value!r}; expected 1-65535")
    return port


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
