"""Request/response codecs used by the TP-Link web CGI endpoints."""

from __future__ import annotations

import base64
import json
import hashlib
import os
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


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


@dataclass(slots=True)
class EncryptedJsonCodec:
    """Codec for the newer TP-Link AES/RSA signed CGI mode."""

    password: str
    rsa_modulus: str
    rsa_public_key: str
    sequence_number: int
    username: str = "admin"
    key: str = ""
    iv: str = ""
    password_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.key:
            self.key = secrets.token_hex(8)
        if not self.iv:
            self.iv = secrets.token_hex(8)
        self.password_hash = hashlib.md5(f"{self.username}{self.password}".encode()).hexdigest()

    def encode(self, payload: JsonObject, *, login: bool = False) -> str:
        raw = json.dumps(payload, separators=(",", ":"))
        encrypted = _aes_cbc_encrypt(raw, self.key, self.iv)
        sign = self._signature(self.sequence_number + len(encrypted), include_aes=login)
        return json.dumps({"data": encrypted, "sign": sign}, separators=(",", ":"))

    def decode(self, text: str, *, login: bool = False) -> JsonObject:
        text = text.strip()
        if not text:
            raise CodecError("empty response")

        decrypted = _aes_cbc_decrypt(text, self.key, self.iv)
        try:
            result = json.loads(decrypted)
        except json.JSONDecodeError as exc:
            raise CodecError(f"cannot parse decrypted JSON: {exc}") from exc
        if not isinstance(result, dict):
            raise CodecError("decrypted response is not a JSON object")
        return result

    def _signature(self, sequence_number: int, *, include_aes: bool) -> str:
        if include_aes:
            message = f"key={self.key}&iv={self.iv}&h={self.password_hash}&s={sequence_number}"
        else:
            message = f"h={self.password_hash}&s={sequence_number}"
        return _rsa_encrypt_chunks(message, self.rsa_modulus, self.rsa_public_key)


def _aes_cbc_encrypt(text: str, key: str, iv: str) -> str:
    padder = PKCS7(128).padder()
    padded = padder.update(text.encode()) + padder.finalize()
    encryptor = _aes_cipher(key, iv).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(encrypted).decode()


def _aes_cbc_decrypt(text: str, key: str, iv: str) -> str:
    try:
        encrypted = base64.b64decode(text)
        decryptor = _aes_cipher(key, iv).decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        decrypted = unpadder.update(padded) + unpadder.finalize()
    except Exception as exc:  # noqa: BLE001 - normalize crypto/decode errors
        raise CodecError(f"cannot decrypt AES-CBC payload: {exc}") from exc
    return decrypted.decode()


def _aes_cipher(key: str, iv: str) -> Cipher:
    try:
        return Cipher(algorithms.AES(key.encode()), modes.CBC(iv.encode()))
    except ValueError as exc:
        raise CodecError(f"invalid AES key/IV: {exc}") from exc


def _rsa_encrypt_chunks(message: str, modulus_hex: str, exponent_hex: str) -> str:
    modulus = int(modulus_hex, 16)
    exponent = int(exponent_hex, 16)
    key_bytes = (modulus.bit_length() + 7) // 8
    max_chunk = key_bytes - 11
    encoded = message.encode()
    chunks = [encoded[index : index + max_chunk] for index in range(0, len(encoded), max_chunk)]
    return "".join(_rsa_encrypt_chunk(chunk, modulus, exponent, key_bytes) for chunk in chunks)


def _rsa_encrypt_chunk(message: bytes, modulus: int, exponent: int, key_bytes: int) -> str:
    if len(message) > key_bytes - 11:
        raise CodecError("RSA message chunk is too large")

    padding_length = key_bytes - len(message) - 3
    padding = bytearray()
    while len(padding) < padding_length:
        candidate = os.urandom(padding_length - len(padding))
        padding.extend(byte for byte in candidate if byte != 0)

    block = b"\x00\x02" + bytes(padding[:padding_length]) + b"\x00" + message
    encrypted = pow(int.from_bytes(block, "big"), exponent, modulus)
    return f"{encrypted:0{key_bytes * 2}x}"
