"""check_service.py: サービス版の外からの見張り（S22）。通信はせず、応答を差し替えて確かめる。"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_service as CS                                            # noqa: E402

BASE = "https://app.example"
GOOD = json.dumps({"ok": True, "free_tier": {"r2_reads_month": 10, "r2_reads_cap": 100}}).encode()


def server(**over):
    """path -> (status, body, seconds)。"""
    routes = {"/api/health": (200, GOOD, 0.2), "/about": (200, b"", 0.1), "/login": (200, b"", 0.1), **over}
    return lambda url, timeout: routes[url[len(BASE):]]


class CheckServiceTest(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(CS.check(BASE, fetch=server(), sleep=lambda s: None), [])

    def test_down_health_or_page_is_reported(self):
        got = CS.check(BASE, fetch=server(**{"/api/health": (0, b"", 30.0), "/login": (500, b"", 0.1)}), sleep=lambda s: None)
        self.assertIn("/api/health が 応答なし", got)
        self.assertIn("/login が 500", got)

    def test_health_without_ok_and_slow(self):
        got = CS.check(BASE, fetch=server(**{"/api/health": (200, b'{"ok": false}', 12.0)}), sleep=lambda s: None)
        self.assertEqual(got, ["/api/health が ok を返さない", "/api/health が遅い（12.0 秒）"])

    def test_free_tier_over_eighty_percent(self):
        body = json.dumps({"ok": True, "free_tier": {"r2_reads_month": 80, "r2_reads_cap": 100}}).encode()
        got = CS.check(BASE, fetch=server(**{"/api/health": (200, body, 0.2)}), sleep=lambda s: None)
        self.assertEqual(len(got), 1)
        self.assertIn("8 割", got[0])

    def test_one_blip_does_not_alert_but_a_lasting_fault_does(self):
        calls = {"n": 0}
        good = server()

        def flaky(url, timeout):
            if url.endswith("/api/health"):
                calls["n"] += 1
                if calls["n"] == 1:
                    return (0, b"", 30.0)
            return good(url, timeout)
        waits = []
        self.assertEqual(CS.check(BASE, fetch=flaky, sleep=waits.append), [])
        self.assertEqual(waits, [30.0])
        waits.clear()
        self.assertTrue(CS.check(BASE, fetch=server(**{"/about": (503, b"", 0.1)}), sleep=waits.append))
        self.assertEqual(len(waits), 2)


if __name__ == "__main__":
    unittest.main()
