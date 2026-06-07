"""Client for the TP-Link M7350 local web interface."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, build_opener

from .codec import Base64JsonCodec, Codec, CodecError, JsonObject
from .status import summarize_status


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
    _opener: Any = field(init=False, repr=False)

    AUTHENTICATOR = "authenticator"
    WEB_SERVER = "webServer"

    ACTION_LOAD = 0
    ACTION_LOGIN = 1
    ACTION_GET_ATTEMPT = 2
    ACTION_LOGOUT = 3

    def __post_init__(self) -> None:
        self.host = self.host.rstrip("/") + "/"
        self._opener = build_opener()

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

    def logout(self) -> JsonObject:
        """Logout and clear the local token."""

        data = self.call(self.AUTHENTICATOR, self.ACTION_LOGOUT)
        self.token = None
        return data

    def status(self, *, summarize: bool = False) -> JsonObject:
        """Fetch the data backing `settings.html#Status`."""

        data = self.call("status", 0)
        if summarize:
            return summarize_status(data)
        return data

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
        request = Request(
            urljoin(self.host, endpoint),
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "*/*",
            },
            method="POST",
        )

        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                text = response.read().decode(errors="replace")
        except HTTPError as exc:
            raise M7350Error(f"HTTP {exc.code} from {endpoint}") from exc
        except URLError as exc:
            raise M7350Error(f"cannot reach router at {self.host}: {exc.reason}") from exc

        try:
            return self.codec.decode(text, login=login)
        except CodecError as exc:
            raise M7350Error(f"cannot decode response from {endpoint}: {exc}") from exc


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def pretty_json(data: JsonObject) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
