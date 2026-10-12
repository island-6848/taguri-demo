"""探しても見つからない公演を「次の更新で探してもらう」流れの検査。

一時 DB と、実際の HTTP の解釈・振り分けを通す（外部への通信はしない）。
    python3 tools/taguri/test_search_requests.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_demo_stability as DS                                     # noqa: E402
import fetch_requests as FR                                          # noqa: E402
import stage_search as SS                                            # noqa: E402

APP, R = DS.APP, DS.R
PATH = "/api/catalog/search-requests"


class SearchRequests(unittest.TestCase):
    # 依頼と登録名を取得処理へ渡すのはサービス版だけ（デモ版は docs/editions.md の切り分けで断る）
    setUpClass = classmethod(DS.service_setup)
    tearDownClass = classmethod(DS.service_teardown)
    request = DS.DemoStabilityTests.request

    def setUp(self):
        with R.connect() as con:
            con.executescript(APP.SEARCH_REQUEST_SCHEMA)
            con.execute("DELETE FROM search_request")

    def test_request_is_saved_and_bad_titles_are_refused(self):
        status, body = self.request("/api/search_request", body={"q": "るつぼ", "source": "search"})
        self.assertEqual(status, 200, body)
        self.assertIn("次の更新", body["message"])
        self.assertTrue(APP.has_search_request(self.users[0][0], "るつぼ"))
        self.assertFalse(APP.has_search_request(self.users[1][0], "るつぼ"))   # 他人の依頼は見えない
        for bad in ("あ", "https://example.com/x", "x" * 61):
            self.assertEqual(self.request("/api/search_request", body={"q": bad})[0], 400, bad)

    def test_each_user_keeps_at_most_the_cap(self):
        uid = self.users[0][0]
        for i in range(APP.MAX_REQUESTS_PER_USER + 5):
            APP.add_search_request(uid, f"検査の題名{i:02d}")
        with R.connect() as con:
            n = con.execute("SELECT COUNT(*) FROM search_request WHERE user_id=?", (uid,)).fetchone()[0]
        self.assertEqual(n, APP.MAX_REQUESTS_PER_USER)

    def test_missed_title_is_requested_automatically(self):
        status, _ = self.request("/api/missed", body={"title": "見逃した芝居"})
        self.assertEqual(status, 200)
        self.assertTrue(APP.has_search_request(self.users[0][0], "見逃した芝居"))

    def test_requests_are_merged_without_user_ids_and_old_ones_drop(self):
        APP.add_search_request(self.users[0][0], "るつぼ  The Crucible")
        APP.add_search_request(self.users[1][0], "るつぼ The Crucible", "hand")
        APP.add_search_request(self.users[1][0], "古い依頼の題名")
        old = (datetime.datetime.now() - datetime.timedelta(days=40)).astimezone().isoformat(timespec="seconds")
        with R.connect() as con:
            con.execute("UPDATE search_request SET created_at=? WHERE query=?", (old, "古い依頼の題名"))
        got = APP.aggregate_search_requests()
        self.assertEqual([g["query"] for g in got], ["るつぼ The Crucible"])
        self.assertEqual(got[0]["users"], 2)
        self.assertEqual(got[0]["sources"], ["hand", "search"])
        blob = json.dumps(got, ensure_ascii=False)
        for uid, _ in self.users:
            self.assertNotIn(uid, blob)

    def test_endpoint_requires_the_token(self):
        APP.add_search_request(self.users[0][0], "るつぼ")
        with patch.dict(os.environ, {"TAGURI_NAMES_TOKEN": ""}):
            self.assertEqual(self.request(PATH)[0], 404)
        with patch.dict(os.environ, {"TAGURI_NAMES_TOKEN": "tok"}):
            self.assertEqual(self.request(PATH, extra={"Authorization": "Bearer no"})[0], 403)
            status, body = self.request(PATH, extra={"Authorization": "Bearer tok"})
        self.assertEqual(status, 200)
        self.assertEqual(body["version"], "search-requests-v1")
        self.assertEqual(body["requests"][0]["query"], "るつぼ")

    def test_search_page_offers_the_request_for_visitors(self):
        uid = self.users[0][0]
        html = APP._web_hits(uid, "るつぼ", False)
        self.assertIn('data-search-request="るつぼ"', html)
        APP.add_search_request(uid, "るつぼ")
        self.assertIn("頼んであります", APP._web_hits(uid, "るつぼ", False))

    def test_found_shows_appear_in_hand_add_candidates(self):
        picked = APP.ROOT / "data" / "review" / "picked.jsonl"
        picked.parent.mkdir(parents=True, exist_ok=True)
        picked.write_text(json.dumps({"stage_id": "777", "title": "るつぼ The Crucible",
                                      "period": "2026/03/14〜2026/03/29", "theater": "東京芸術劇場"},
                                     ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            APP.reset_caches()
            rows = APP._suggest_pool(self.users[0][0])
            self.assertTrue(any(r.get("stage_id") == "777" for r in rows))
        finally:
            picked.unlink()
            APP.reset_caches()


class Fetcher(unittest.TestCase):
    """手元の取得処理の選び方と書き込み（外部へは行かない）。"""

    def test_choose_skips_recent_and_orders_by_age_and_users(self):
        today = datetime.date(2026, 10, 12)
        cache = {R.title_key("最近探した"): {"at": "2026-10-10"},
                 R.title_key("前に探した"): {"at": "2026-09-01"}}
        reqs = [{"query": "最近探した", "users": 9}, {"query": "前に探した", "users": 1},
                {"query": "初めての題名", "users": 1}, {"query": "人気の題名", "users": 5}]
        self.assertEqual(FR.choose(reqs, cache, today, 10), ["人気の題名", "初めての題名", "前に探した"])
        self.assertEqual(FR.choose(reqs, cache, today, 1), ["人気の題名"])

    def test_main_adds_new_shows_and_remembers_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            found = {"q": "るつぼ", "error": "", "rows": [
                {"stage_id": "1", "title": "るつぼ（既にある）", "period": ""},
                {"stage_id": "2", "title": "るつぼ The Crucible", "period": "2026/03/14〜2026/03/29"}]}
            with patch.object(FR, "load_requests", return_value=[{"query": "るつぼ", "users": 1},
                                                                 {"query": "見つからない題名", "users": 1}]), \
                 patch.object(FR, "CACHE", tmp / "cache.json"), \
                 patch.object(FR, "known_ids", return_value={"1"}), \
                 patch.object(SS, "PICKED", tmp / "picked.jsonl"), \
                 patch.object(SS, "search_full", side_effect=lambda q, limit=6:
                              found if q == "るつぼ" else {"q": q, "error": "", "rows": []}), \
                 patch.object(sys, "argv", ["fetch_requests.py", "--today", "2026-10-12"]):
                self.assertEqual(FR.main(), 0)
            rows = [json.loads(l) for l in (tmp / "picked.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([r["stage_id"] for r in rows], ["2"])
            self.assertEqual(rows[0]["source"], "頼まれて探した")
            cache = json.loads((tmp / "cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cache[R.title_key("見つからない題名")]["found"], 0)   # 見つからなくても控える

    def test_url_defaults_to_the_names_server(self):
        with patch.object(FR, "REQUESTS_URL", ""), \
             patch.dict(os.environ, {"TAGURI_NAMES_URL": "https://x.invalid/api/catalog/favourite-names"}):
            self.assertEqual(FR.requests_url(), "https://x.invalid/api/catalog/search-requests")


if __name__ == "__main__":
    unittest.main()
