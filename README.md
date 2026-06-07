# tplink-M7350

Small Python client experiments for the TP-Link M7350 local web interface.

## Current Scope

This is a starter client for the local `auth_cgi` / `web_cgi` interface.

Implemented now:

- base64-wrapped JSON request/response codec
- encrypted/signed JSON codec for GDPR-capable firmware
- auth load call: `{"module":"authenticator","action":0}`
- login digest flow using `md5("<password>:<nonce>")`
- local token storage and injection into later request payloads
- Status page helper for `settings.html#Status`
- small CLI for quick experiments

Still to port:

- higher-level helpers for SMS, connection, and reboot actions

Encrypted firmware support uses `cryptography` for AES-CBC.

## Quick Checks

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

## Status Example

Create or edit `examples/.env`:

```sh
TPLINK_M7350_IP=192.168.0.1
TPLINK_M7350_PORT=80
TPLINK_M7350_PASSWORD='your-router-password'
TPLINK_M7350_RATE_UNIT=KB/s
```

Then print the friendly Status JSON:

```sh
PYTHONPATH=src .venv/bin/python examples/status.py
PYTHONPATH=src .venv/bin/python examples/status.py --rate-unit auto
```

`TPLINK_M7350_RATE_UNIT` controls both upstream and downstream rate units.
Allowed values are `auto`, `B/s`, `KB/s`, and `MB/s`; the default is `KB/s`.

## CLI Examples

```sh
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli --env-file examples/.env load-auth
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli --env-file examples/.env login
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli --env-file examples/.env status
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli --env-file examples/.env --port 8080 status
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli --env-file examples/.env status --rate-unit MB/s
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli --env-file examples/.env status --raw
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli call webServer 0 --no-auth
```

The `settings.html#Status` page is backed by:

```json
{"module":"status","action":0}
```

That response contains the connection, Wi-Fi, client count, and traffic statistics
shown on the Status screen.
