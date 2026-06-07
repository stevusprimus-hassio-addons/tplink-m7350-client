# tplink-M7350

Small Python client experiments for the TP-Link M7350 local web interface.

## Current Scope

This is a starter client for the local `auth_cgi` / `web_cgi` interface.

Implemented now:

- base64-wrapped JSON request/response codec
- auth load call: `{"module":"authenticator","action":0}`
- login digest flow using `md5("<password>:<nonce>")`
- local token storage and injection into later request payloads
- small CLI for quick experiments

Still to port:

- the newer encrypted/signature mode seen in recent firmware HAR captures
- higher-level helpers for SMS, status, connection, and reboot actions

## Quick Checks

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

## CLI Examples

Create a local `.env` file:

```sh
TPLINK_M7350_PASSWORD='your-router-password'
```

```sh
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli load-auth
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli login
PYTHONPATH=src .venv/bin/python -m tplink_m7350.cli call webServer 0 --no-auth
```
