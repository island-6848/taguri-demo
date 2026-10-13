"""検索ページを使わず、サイトマップと公演ページから候補を作る流れの検査（通信はしない）。

    python3 tools/review/test_fetch_candidates_sitemap.py
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_candidates as FCAND                                     # noqa: E402

INDEX = ('<sitemapindex><sitemap><loc>https://stage.corich.jp/sitemaps/sitemap1.xml.gz</loc></sitemap>'
         '<sitemap><loc>https://stage.corich.jp/sitemaps/sitemap2.xml.gz</loc></sitemap>'
         '<sitemap><loc>https://stage.corich.jp/sitemaps/sitemap3.xml.gz</loc></sitemap></sitemapindex>')
SM1 = "".join(f"<url><loc>https://stage.corich.jp/stage/{i}</loc></url>" for i in (10, 20, 30, 40))
SM2 = "<url><loc>https://stage.corich.jp/user/1</loc></url>"


def page(title: str, period: str, pref: str = "東京都", cast: str = "検査の俳優") -> str:
    return (f"<html><head><title>{title} | CoRich舞台芸術！</title></head><body>"
            f'<p class="group"><a href="/troupe/1">検査団体</a></p>'
            f'<p class="theater"><a href="/theater/2">検査劇場</a><span class="pref">（{pref}）</span></p>'
            f"<table><tr><th>期間</th><td> {period} </td></tr>"
            f"<tr><th>劇場</th><td><a href='/theater/2'>検査劇場</a></td></tr>"
            f"<tr><th>出演</th><td>{cast}</td></tr>"
            f"<tr><th>料金（1枚あたり）</th><td>3,000円</td></tr></table></body></html>")


PAGES = {
    "10": page("昔の公演", "2025/01/01 (水) ～ 2025/01/05 (日)"),
    "20": page("最近終わった公演", "2026/09/01 (火) ～ 2026/09/05 (土)"),
    "30": page("これからの公演", "2026/12/04 (金) ～ 2026/12/05 (土)", pref="大阪府"),
    "40": page("もっと先の公演", "2027/01/10 (日) ～ 2027/01/20 (水)"),
    "50": page("新しく出た公演", "2027/02/01 (月) ～ 2027/02/03 (水)"),
}


class SitemapCandidates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.patches = [patch.object(FCAND, "OUT", base / "candidates.jsonl"),
                        patch.object(FCAND, "SCAN", base / "candidates_scan.json")]
        for p in self.patches:
            p.start()
        self.sitemap = {"sitemap1": SM1, "sitemap2": SM2, "sitemap3": ""}
        self.fetched: list[str] = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def fake_fetch(self, url, **kw):
        if url.endswith("sitemap.xml.gz"):
            return gzip.compress(INDEX.encode())
        name = url.rsplit("/", 1)[1].split(".")[0]
        return gzip.compress(self.sitemap[name].encode())

    def fake_get(self, url):
        sid = url.rsplit("/", 1)[1]
        self.fetched.append(sid)
        return PAGES[sid]

    def run_main(self, *args):
        with patch.object(FCAND.PH, "fetch", side_effect=self.fake_fetch), \
             patch.object(FCAND, "get", side_effect=self.fake_get), \
             patch.object(sys, "argv", ["x", "--source", "sitemap", "--today", "2026-10-13",
                                        "--no-synopsis", *args]), \
             patch("sys.stdout"):
            self.assertEqual(FCAND.main(), 0)
        return {json.loads(l)["stage_id"]: json.loads(l)
                for l in FCAND.OUT.read_text(encoding="utf-8").splitlines() if l.strip()}

    def test_first_run_reads_newest_pages_and_keeps_recent_ones(self):
        got = self.run_main("--initial-ids", "3")
        self.assertEqual(sorted(self.fetched), ["20", "30", "40"])     # 新しいほうから 3 件だけ
        self.assertEqual(sorted(got), ["20", "30", "40"])
        self.assertTrue(got["20"]["ended"])
        row = got["30"]
        self.assertEqual((row["title"], row["group"], row["theater"], row["pref"]),
                         ("これからの公演", "検査団体", "検査劇場", "大阪府"))
        self.assertEqual(row["period"], "2026/12/04 〜 2026/12/05")
        self.assertIn("検査の俳優", row["fields"]["出演"])
        scan = json.loads(FCAND.SCAN.read_text(encoding="utf-8"))
        self.assertEqual(scan["max_id"], 40)

    def test_next_run_reads_only_new_ids_and_carries_the_rest(self):
        self.run_main("--initial-ids", "3")
        self.fetched.clear()
        self.sitemap["sitemap1"] = SM1 + "<url><loc>https://stage.corich.jp/stage/50</loc></url>"
        got = self.run_main()
        self.assertEqual(self.fetched, ["50"])                           # 増えた 1 件だけを読む
        self.assertEqual(sorted(got), ["20", "30", "40", "50"])

    def test_search_is_never_used(self):
        with patch.object(FCAND, "listing", side_effect=AssertionError("search used")):
            self.run_main("--initial-ids", "2")


if __name__ == "__main__":
    unittest.main()
