"""Client for the TP-Link M7350 local web interface."""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from .codec import Base64JsonCodec, Codec, CodecError, EncryptedJsonCodec, JsonObject
from .status import DEFAULT_RATE_UNIT, summarize_status


class M7350Error(RuntimeError):
    """Base exception for client failures."""


class M7350AuthError(M7350Error):
    """Raised when authentication fails or a token is missing."""


@dataclass(slots=True)
class M7350Client:
    """Small programmatic client for the router's local CGI endpoints."""

    host: str = "http://192.168.0.1"
    password: str | None = None
    codec: Codec = field(default_factory=Base64JsonCodec)
    timeout: float = 10.0
    token: str | None = None
    nonce: str | None = None
    rsa_public_key: str | None = None
    rsa_modulus: str | None = None
    sequence_number: str | None = None
    support_gdpr: bool | None = None

    AUTHENTICATOR = "authenticator"
    WEB_SERVER = "webServer"

    ACTION_LOAD = 0
    ACTION_LOGIN = 1
    ACTION_GET_ATTEMPT = 2
    ACTION_LOGOUT = 3
    ACTION_FEATURE_LIST = 5

    def __post_init__(self) -> None:
        self.host = self.host.rstrip("/") + "/"

    def load_auth(self) -> JsonObject:
        """Load nonce and crypto/session parameters from auth_cgi."""

        data = self.call(self.AUTHENTICATOR, self.ACTION_LOAD, authenticated=False)
        self.nonce = _optional_str(data.get("nonce"))
        self.rsa_public_key = _optional_str(data.get("rsaPubKey"))
        self.rsa_modulus = _optional_str(data.get("rsaMod"))
        self.sequence_number = _optional_str(data.get("seqNum"))
        return data

    def login(self, password: str | None = None) -> str:
        """Login and return the router token.

        Older firmware accepts MD5("<password>:<nonce>") in the login payload.
        Newer encrypted firmware may require an encrypted codec.
        """

        password = password if password is not None else self.password
        if not password:
            raise M7350AuthError("password is required")
        if not self.nonce:
            self.load_auth()
        if not self.nonce:
            raise M7350AuthError("router did not provide an auth nonce")
        if self.support_gdpr is None:
            self.support_gdpr = self._supports_gdpr()
        if self.support_gdpr:
            if not self.rsa_modulus or not self.rsa_public_key or self.sequence_number is None:
                raise M7350AuthError("router did not provide encrypted-login parameters")
            self.codec = EncryptedJsonCodec(
                password=password,
                rsa_modulus=self.rsa_modulus,
                rsa_public_key=self.rsa_public_key,
                sequence_number=int(self.sequence_number),
            )

        digest = hashlib.md5(f"{password}:{self.nonce}".encode()).hexdigest()
        data = self.call(
            self.AUTHENTICATOR,
            self.ACTION_LOGIN,
            {"digest": digest},
            authenticated=False,
            login=True,
        )

        if data.get("result") != 0:
            raise M7350AuthError(f"login failed with result {data.get('result')}")

        token = _optional_str(data.get("token"))
        if not token:
            raise M7350AuthError("login response did not contain a token")
        self.token = token
        return token

    def feature_list(self) -> JsonObject:
        """Fetch unauthenticated router feature flags."""

        return self.call(self.WEB_SERVER, self.ACTION_FEATURE_LIST, authenticated=False)

    def logout(self) -> JsonObject:
        """Logout and clear the local token."""

        data = self.call(self.AUTHENTICATOR, self.ACTION_LOGOUT)
        self.token = None
        return data

    def status(self, *, summarize: bool = False, rate_unit: str = DEFAULT_RATE_UNIT) -> JsonObject:
        """Fetch the data backing `settings.html#Status`."""

        data = self.call("status", 0)
        if summarize:
            return summarize_status(data, rate_unit=rate_unit)
        return data

    def _supports_gdpr(self) -> bool:
        data = self.feature_list()
        others = data.get("others")
        return bool(isinstance(others, dict) and others.get("supportGDPR"))

    def call(
        self,
        module: str,
        action: int,
        data: JsonObject | None = None,
        *,
        authenticated: bool = True,
        login: bool = False,
    ) -> JsonObject:
        """Call `auth_cgi` or `web_cgi` with a TP-Link module/action payload."""

        payload: JsonObject = {"module": module, "action": action}
        if data:
            payload.update(data)
        if authenticated:
            if not self.token:
                raise M7350AuthError("no token available; call login() first")
            payload["token"] = self.token

        endpoint = "cgi-bin/auth_cgi" if module == self.AUTHENTICATOR else "cgi-bin/web_cgi"
        return self._post(endpoint, payload, login=login)

    def _post(self, endpoint: str, payload: JsonObject, *, login: bool = False) -> JsonObject:
        body = self.codec.encode(payload, login=login).encode()

        try:
            text = self._raw_post(endpoint, body)
        except OSError as exc:
            raise M7350Error(f"cannot reach router at {self.host}: {exc}") from exc

        try:
            return self.codec.decode(text, login=login)
        except CodecError as exc:
            raise M7350Error(f"cannot decode response from {endpoint}: {exc}") from exc

    def _raw_post(self, endpoint: str, body: bytes) -> str:
        base = urlsplit(self.host)
        if base.scheme not in {"http", ""}:
            raise M7350Error(f"unsupported URL scheme for router host: {base.scheme}")

        host = base.hostname
        if not host:
            raise M7350Error(f"invalid router host: {self.host}")
        port = base.port or 80
        path_prefix = base.path.rstrip("/")
        path = f"{path_prefix}/{endpoint}" if path_prefix else f"/{endpoint}"
        host_header = f"{host}:{port}" if port != 80 else host
        header = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "User-Agent: tplink-m7350/0\r\n"
            "Accept: */*\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "\r\n"
        ).encode()

        with socket.create_connection((host, port), timeout=self.timeout) as connection:
            connection.settimeout(self.timeout)
            connection.sendall(header + body)
            response = _read_http_response(connection)

        return _decode_http_response(bytes(response), endpoint)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _decode_http_response(response: bytes, endpoint: str) -> str:
    header_bytes, separator, body = response.partition(b"\r\n\r\n")
    if not separator:
        raise M7350Error(f"invalid HTTP response from {endpoint}")

    header_lines = header_bytes.decode(errors="replace").split("\r\n")
    status_line = header_lines[0] if header_lines else ""
    parts = status_line.split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise M7350Error(f"invalid HTTP status from {endpoint}: {status_line}")

    status = int(parts[1])
    text = body.decode(errors="replace")
    if status >= 400:
        raise M7350Error(f"HTTP {status} from {endpoint}: {text[:200]}")
    return text


def _read_http_response(connection: socket.socket) -> bytes:
    response = bytearray()
    header_end = -1
    content_length: int | None = None

    while True:
        chunk = connection.recv(65536)
        if not chunk:
            break
        response.extend(chunk)

        if header_end < 0:
            header_end = response.find(b"\r\n\r\n")
            if header_end >= 0:
                content_length = _response_content_length(response[:header_end])

        if header_end >= 0 and content_length is not None:
            body_start = header_end + 4
            if len(response) - body_start >= content_length:
                break

    return bytes(response)


def _response_content_length(headers: bytes) -> int | None:
    for line in headers.decode(errors="replace").split("\r\n")[1:]:
        name, separator, value = line.partition(":")
        if separator and name.strip().lower() == "content-length":
            try:
                return int(value.strip())
            except ValueError:
                return None
    return None


def pretty_json(data: JsonObject) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
