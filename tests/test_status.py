import unittest

from tplink_m7350.status import summarize_status


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


if __name__ == "__main__":
    unittest.main()
