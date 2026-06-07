import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tplink_m7350.config import (
    load_dotenv,
    normalize_host,
    normalize_port,
    read_host,
    read_password,
    read_rate_unit,
)


class ConfigTests(unittest.TestCase):
    def test_load_dotenv_reads_password(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TPLINK_M7350_PASSWORD='secret value' # local password\n")

            self.assertEqual(load_dotenv(path)["TPLINK_M7350_PASSWORD"], "secret value")

    def test_read_password_prefers_cli_value(self):
        with patch.dict(os.environ, {"TPLINK_M7350_PASSWORD": "from-env"}, clear=False):
            self.assertEqual(read_password("from-cli"), "from-cli")

    def test_read_password_uses_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('TPLINK_M7350_PASSWORD="from-file"\n')

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(read_password(None, path), "from-file")

    def test_normalize_host_accepts_bare_ip(self):
        self.assertEqual(normalize_host("192.168.0.1"), "http://192.168.0.1")

    def test_normalize_host_adds_configured_port(self):
        self.assertEqual(normalize_host("192.168.0.1", port=8080), "http://192.168.0.1:8080")

    def test_normalize_host_preserves_explicit_port(self):
        self.assertEqual(
            normalize_host("http://192.168.0.1:8080", port=80),
            "http://192.168.0.1:8080",
        )

    def test_normalize_port_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            normalize_port("70000")

    def test_read_host_uses_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TPLINK_M7350_IP=192.168.0.1\n")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(read_host(None, path), "http://192.168.0.1")

    def test_read_host_uses_env_file_port(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TPLINK_M7350_IP=192.168.0.1\nTPLINK_M7350_PORT=8080\n")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(read_host(None, path), "http://192.168.0.1:8080")

    def test_read_host_prefers_cli_value(self):
        with patch.dict(os.environ, {"TPLINK_M7350_IP": "192.168.0.1"}, clear=False):
            self.assertEqual(read_host("http://router.local"), "http://router.local")

    def test_read_rate_unit_uses_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TPLINK_M7350_RATE_UNIT=auto\n")

            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(read_rate_unit(None, path), "auto")

    def test_read_rate_unit_prefers_cli_value(self):
        with patch.dict(os.environ, {"TPLINK_M7350_RATE_UNIT": "B/s"}, clear=False):
            self.assertEqual(read_rate_unit("MB/s"), "MB/s")


if __name__ == "__main__":
    unittest.main()
