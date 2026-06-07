import unittest

from tplink_m7350.status import normalize_rate_unit, summarize_status


class StatusTests(unittest.TestCase):
    def test_summarize_status_matches_status_page_units(self):
        summary = summarize_status(
            {
                "wan": {
                    "connectStatus": 4,
                    "networkType": 3,
                    "band": 1,
                    "rsrp": -110,
                    "rsrq": -9,
                    "snr": 94,
                    "ipv4": "10.56.84.188",
                    "ipv6": "2a00::1",
                    "totalStatistics": 25857884,
                    "dailyStatistics": 25847400,
                    "txSpeed": 2140,
                    "rxSpeed": 881,
                },
                "wlan": {"ssid": "Garten", "mode": 1, "bandType": 0},
                "connectedDevices": {"number": 3},
            }
        )

        self.assertEqual(summary["connection"]["status"], "Connected")
        self.assertEqual(summary["connection"]["networkType"], "LTE")
        self.assertEqual(summary["connection"]["rsrp"], "-110dBm")
        self.assertEqual(summary["connection"]["snr"], "9.4dB")
        self.assertEqual(summary["wifi"]["ssid"], "Garten")
        self.assertEqual(summary["wifi"]["currentClients"], 3)
        self.assertEqual(summary["statistics"]["totalUsed"]["unit"], "MB")
        self.assertEqual(summary["statistics"]["upstreamRate"]["unit"], "KB/s")
        self.assertEqual(summary["statistics"]["downstreamRate"], {"value": 0.86, "unit": "KB/s"})

    def test_rate_unit_modes(self):
        data = {"wan": {"txSpeed": 2048, "rxSpeed": 2048}}

        self.assertEqual(
            summarize_status(data, rate_unit="auto")["statistics"]["downstreamRate"],
            {"value": 2, "unit": "KB/s"},
        )
        self.assertEqual(
            summarize_status(data, rate_unit="B/s")["statistics"]["downstreamRate"],
            {"value": 2048, "unit": "B/s"},
        )
        self.assertEqual(
            summarize_status(data, rate_unit="KB/s")["statistics"]["downstreamRate"],
            {"value": 2, "unit": "KB/s"},
        )
        self.assertEqual(
            summarize_status(data, rate_unit="MB/s")["statistics"]["downstreamRate"],
            {"value": 0, "unit": "MB/s"},
        )

    def test_normalize_rate_unit_rejects_unknown_values(self):
        with self.assertRaises(ValueError):
            normalize_rate_unit("bananas")


if __name__ == "__main__":
    unittest.main()
