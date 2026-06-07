"""Status helpers for values shown on `settings.html#Status`."""

from __future__ import annotations

from typing import Any

from .codec import JsonObject


CONNECT_STATUS = {
    0: "Disabled",
    1: "Disconnected",
    2: "Connecting",
    3: "Disconnecting",
    4: "Connected",
}

NETWORK_TYPE = {
    0: "No Service",
    1: "GSM",
    2: "WCDMA",
    3: "LTE",
    4: "TD-SCDMA",
    5: "CDMA 1x",
    6: "CDMA 1x Ev-Do",
    7: "LTE+",
}

RATE_UNIT_AUTO = "auto"
RATE_UNIT_BPS = "B/s"
RATE_UNIT_KBPS = "KB/s"
RATE_UNIT_MBPS = "MB/s"
DEFAULT_RATE_UNIT = RATE_UNIT_KBPS
RATE_UNITS = (RATE_UNIT_AUTO, RATE_UNIT_BPS, RATE_UNIT_KBPS, RATE_UNIT_MBPS)


def summarize_status(data: JsonObject, *, rate_unit: str = DEFAULT_RATE_UNIT) -> JsonObject:
    """Extract the main visible Status page values from a raw status response."""

    rate_unit = normalize_rate_unit(rate_unit)
    wan = _dict(data.get("wan"))
    wlan = _dict(data.get("wlan"))
    devices = _dict(data.get("connectedDevices"))

    return {
        "connection": {
            "status": CONNECT_STATUS.get(wan.get("connectStatus"), wan.get("connectStatus")),
            "networkType": NETWORK_TYPE.get(wan.get("networkType"), wan.get("networkType")),
            "band": wan.get("band"),
            "rsrp": _with_unit(wan.get("rsrp"), "dBm"),
            "rsrq": _with_unit(wan.get("rsrq"), "dB"),
            "snr": _snr(wan.get("snr")),
            "rssi": _with_unit(wan.get("rssi"), "dBm"),
            "ipv4": wan.get("ipv4"),
            "ipv6": wan.get("ipv6"),
        },
        "wifi": {
            "ssid": wlan.get("ssid"),
            "security": "Not secured" if wlan.get("mode") == 0 else "Secured",
            "band": "5GHz" if wlan.get("bandType") == 1 else "2.4GHz",
            "currentClients": devices.get("number"),
        },
        "statistics": {
            "totalUsed": _bytes(wan.get("totalStatistics")),
            "dailyUsed": _bytes(wan.get("dailyStatistics")),
            "upstreamRate": _speed(wan.get("txSpeed"), rate_unit),
            "downstreamRate": _speed(wan.get("rxSpeed"), rate_unit),
        },
    }


def normalize_rate_unit(value: str | None) -> str:
    """Normalize user-configurable speed display units."""

    if not value:
        return DEFAULT_RATE_UNIT

    normalized = value.strip().lower().replace(" ", "")
    aliases = {
        "auto": RATE_UNIT_AUTO,
        "b": RATE_UNIT_BPS,
        "b/s": RATE_UNIT_BPS,
        "byte/s": RATE_UNIT_BPS,
        "bytes/s": RATE_UNIT_BPS,
        "kb": RATE_UNIT_KBPS,
        "kbs": RATE_UNIT_KBPS,
        "kb/s": RATE_UNIT_KBPS,
        "kib/s": RATE_UNIT_KBPS,
        "mb": RATE_UNIT_MBPS,
        "mbs": RATE_UNIT_MBPS,
        "mb/s": RATE_UNIT_MBPS,
        "mib/s": RATE_UNIT_MBPS,
    }

    try:
        return aliases[normalized]
    except KeyError as exc:
        allowed = ", ".join(RATE_UNITS)
        raise ValueError(f"invalid rate unit {value!r}; expected one of: {allowed}") from exc


def _dict(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _with_unit(value: Any, unit: str) -> str | None:
    if value is None:
        return None
    return f"{value}{unit}"


def _snr(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{float(value) / 10:g}dB"
    except (TypeError, ValueError):
        return str(value)


def _bytes(value: Any) -> JsonObject:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return {"value": value, "unit": None}

    units = ["Bytes", "KB", "MB", "GB"]
    unit_index = 0
    while amount >= 1024 and unit_index < len(units) - 1:
        amount /= 1024
        unit_index += 1
    return {"value": _trim(amount), "unit": units[unit_index]}


def _speed(value: Any, unit: str) -> JsonObject:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return {"value": value, "unit": None}

    if unit == RATE_UNIT_AUTO:
        unit = RATE_UNIT_BPS
        if amount > 1024:
            amount /= 1024
            unit = RATE_UNIT_KBPS
    elif unit == RATE_UNIT_BPS:
        pass
    elif unit == RATE_UNIT_KBPS:
        amount /= 1024
    elif unit == RATE_UNIT_MBPS:
        amount /= 1024 * 1024
    else:
        unit = normalize_rate_unit(unit)
        return _speed(value, unit)

    return {"value": _trim(amount), "unit": unit}


def _trim(value: float) -> float | int:
    rounded = round(value, 2)
    return int(rounded) if rounded.is_integer() else rounded
