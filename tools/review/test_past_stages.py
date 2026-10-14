#!/usr/bin/env python3
"""fetch_past_stages の試験（ネットには出ない。公演ページは作り物）。

    python3 tools/review/test_past_stages.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_past_stages as P  # noqa: E402


def page(title: str, period: str, cast: str = "山田太郎 鈴木花子") -> str:
    return (f"<html><head><title>{title} | 演劇・ミュージカル等のクチコミ&チケット予約★CoRich舞台芸術!</title></head>"
            f'<body><p class="group">劇団あおば</p><p class="theater">本多劇場<span class="pref">(東京都)</span></p>'
            f"<table><tr><th>期間</th><td>{period}</td></tr><tr><th>出演</th><td>{cast}</td></tr>"
            f"<tr><th>料金</th><td>4,500円</td></tr></table></body></html>")


class PastStagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        P.PAST = d / "past"
        P.ROWS = P.PAST / "stages.jsonl"
        P.PROGRESS = P.PAST / "progress.json"
        P.CANDIDATES = d / "candidates.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self):
        return [json.loads(x) for x in P.ROWS.read_text(encoding="utf-8").splitlines() if x.strip()]

    def test_span(self):
        self.assertEqual(P.span("2023/05/10 〜 2023/05/20"), ("2023-05-10", "2023-05-20"))
        self.assertEqual(P.span("2023/12/28 〜 2024/1/7"), ("2023-12-28", "2024-01-07"))
        self.assertEqual(P.span("未定"), ("", ""))

    def test_reads_newest_first_and_keeps_only_matching_fields(self):
        pages = {30: page("夜の果て", "2024/03/01 (金) 〜 2024/03/10 (日)"),
                 20: page("名もなき町", "2022/7/1 〜 2022/7/3"),
                 10: page("古い話", "2018/01/05 〜 2018/01/08")}
        seen = []
        got = P.run([10, 20, 30], limit=2, since="2019-01-01", stop_after=5, max_minutes=0,
                    fetch=lambda sid: (seen.append(sid), pages[sid])[1])
        self.assertEqual(seen, [30, 20])
        self.assertEqual(got["kept"], 2)
        r = self.rows()[0]
        self.assertEqual((r["stage_id"], r["title"], r["start"], r["end"]), ("30", "夜の果て", "2024-03-01", "2024-03-10"))
        self.assertEqual((r["group"], r["theater"], r["pref"]), ("劇団あおば", "本多劇場", "東京都"))
        self.assertIn("出演", r["fields"])
        self.assertNotIn("料金", r["fields"])     # 照合に要らない欄は持たない
        # 2 回目は続きから（読んだ番号より小さいものだけ）
        P.run([10, 20, 30], limit=5, since="2019-01-01", stop_after=5, max_minutes=0,
              fetch=lambda sid: (seen.append(sid), pages[sid])[1])
        self.assertEqual(seen, [30, 20, 10])
        self.assertEqual([r["stage_id"] for r in self.rows()], ["30", "20"])   # 2018 年の公演は残さない

    def test_stops_after_a_run_of_old_stages(self):
        pages = {i: page(f"古い{i}", "2017/01/05 〜 2017/01/08") for i in range(1, 10)}
        got = P.run(list(range(1, 10)), limit=100, since="2019-01-01", stop_after=3, max_minutes=0,
                    fetch=lambda sid: pages[sid])
        self.assertTrue(got["done"])
        self.assertEqual(got["read"], 3)
        again = P.run(list(range(1, 10)), limit=100, since="2019-01-01", stop_after=3, max_minutes=0,
                      fetch=lambda sid: pages[sid])
        self.assertEqual(again["read"], 0)        # 読み終わったら何もしない

    def test_skips_known_and_unreadable_pages(self):
        P.CANDIDATES.write_text(json.dumps({"stage_id": "3"}) + "\n", encoding="utf-8")

        def fetch(sid):
            if sid == 2:
                raise OSError("404")
            return page(f"題名{sid}", "2025/01/01 〜 2025/01/02")
        seen = []
        got = P.run([1, 2, 3], limit=10, since="2019-01-01", stop_after=5, max_minutes=0,
                    fetch=lambda sid: (seen.append(sid), fetch(sid))[1])
        self.assertEqual(seen, [2, 1])            # 3 は毎日の一覧にあるので読まない
        self.assertEqual(got["skipped"], 1)
        self.assertEqual([r["stage_id"] for r in self.rows()], ["1"])


if __name__ == "__main__":
    unittest.main()
