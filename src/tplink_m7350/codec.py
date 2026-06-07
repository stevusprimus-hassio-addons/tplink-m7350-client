"""Request/response codecs used by the TP-Link web CGI endpoints."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Protocol


JsonObject = dict[str, Any]


class CodecError(RuntimeError):
    """Raised when a router payload cannot be encoded or decoded."""


class Codec(Protocol):
    """Encode/decode one CGI request mode."""

    def encode(self, payload: JsonObject, *, login: bool = False) -> str:
        """Return the request body sent to a CGI endpoint."""

    def decode(self, text: str, *, login: bool = False) -> JsonObject:
        """Decode a response body from a CGI endpoint."""


@dataclass(slots=True)
class Base64JsonCodec:
    """Codec for the older/plain TP-Link JSON wrapper.

    The browser JavaScript sends JSON as:
        {"data": base64(utf8(json_payload))}
    and decodes responses the same way for most non-auth endpoints.
    """

    def encode(self, payload: JsonObject, *, login: bool = False) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return json.dumps({"data": base64.b64encode(raw).decode()}, separators=(",", ":"))

    def decode(self, text: str, *, login: bool = False) -> JsonObject:
        text = text.strip()
        if not text:
            raise CodecError("empty response")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict) and "data" not in parsed:
            return parsed

        if isinstance(parsed, dict) and isinstance(parsed.get("data"), str):
            encoded = parsed["data"]
        else:
            encoded = text

        try:
            decoded = base64.b64decode(encoded).decode()
            result = json.loads(decoded)
        except Exception as exc:  # noqa: BLE001 - normalize parse/decode errors
            raise CodecError(f"cannot decode base64 JSON response: {exc}") from exc

        if not isinstance(result, dict):
            raise CodecError("decoded response is not a JSON object")
        return result


@dataclass(slots=True)
class UnsupportedEncryptedCodec:
    """Placeholder for the newer AES/signature mode used by recent firmware."""

    reason: str = "encrypted TP-Link CGI mode is not implemented yet"

    def encode(self, payload: JsonObject, *, login: bool = False) -> str:
        raise CodecError(self.reason)

    def decode(self, text: str, *, login: bool = False) -> JsonObject:
        raise CodecError(self.reason)

