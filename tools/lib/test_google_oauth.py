"""ローカルの OAuth コールバック画面が、URL の値を HTML として出さないことの検査（#180）。

手元のループバックに受け口を立て、そこへ送るだけ。Google へは通信しない。

    python3 tools/lib/test_google_oauth.py
"""
from __future__ import annotations

import sys
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import google_oauth as G                                            # noqa: E402

ATTACK = "<img src=x onerror=alert(1)>"


class CallbackTest(unittest.TestCase):
    def _get(self, query: dict):
        G._CallbackHandler.code = G._CallbackHandler.error = None
        server = HTTPServer(("127.0.0.1", 0), G._CallbackHandler)
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()
        url = f"http://127.0.0.1:{server.server_port}/?{urllib.parse.urlencode(query)}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(url, timeout=10) as r:
                return r.read().decode("utf-8"), r.headers
        finally:
            t.join(10)
            server.server_close()

    def test_error_is_escaped(self):
        body, _ = self._get({"error": ATTACK})
        self.assertNotIn("<img", body)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", body)
        # 呼び出し元（ターミナルの表示）には元の値を渡す
        self.assertEqual(G._CallbackHandler.error, ATTACK)

    def test_headers_forbid_scripts_and_caching(self):
        _, headers = self._get({"error": "access_denied"})
        self.assertIn("default-src 'none'", headers.get("Content-Security-Policy", ""))
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")


if __name__ == "__main__":
    unittest.main()
