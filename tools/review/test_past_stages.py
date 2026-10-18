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
        # あらすじの 2 周目が書く先（読み取り待ち・題材の表）も作り物の場所にする
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "credits"))
        import extract_theme_llm as EX
        self.EX, self._ex = EX, (EX.OUT, EX.QUEUE, EX.QUEUE_PROMPT)
        EX.OUT, EX.QUEUE, EX.QUEUE_PROMPT = d / "themes.jsonl", d / "queue.jsonl", d / "prompt.txt"

    def tearDown(self):
        self.EX.OUT, self.EX.QUEUE, self.EX.QUEUE_PROMPT = self._ex
        self.tmp.cleanup()

    def test_second_pass_queues_story_text_for_the_reader(self):
        story = "<p>" + "ある家族が、古い家を手放す日の朝に集まり、それぞれの思い出を語り合う物語。" * 12 + "</p>"
        P.PAST.mkdir(parents=True)
        P.ROWS.write_text("".join(json.dumps({"stage_id": s, "title": t}, ensure_ascii=False) + "\n"
                                  for s, t in (("30", "夜の果て"), ("20", "短い話"), ("10", "読んだ話"))), encoding="utf-8")
        P.save_progress({"done": True, "cursor": 1})
        # 10 はこれからの公演だったときに読んである
        self.EX.OUT.write_text(json.dumps({"side": "candidate", "id": "10", "synopsis": "x", "elements": []}) + "\n", encoding="utf-8")
        pages = {30: f"<html><body>{story}</body></html>", 20: "<html><body><p>出演：山田太郎、鈴木花子、佐藤一郎ほか</p></body></html>"}
        seen = []
        got = P.run([], limit=10, since="2019-01-01", stop_after=5, max_minutes=0,
                    fetch=lambda sid: (seen.append(sid), pages[sid])[1])
        self.assertEqual(seen, [30, 20])
        self.assertEqual((got["stories"]["queued"], got["stories"]["short"], got["stories"]["left"]), (1, 1, 0))
        q = [json.loads(x) for x in self.EX.QUEUE.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(x["side"], x["id"], x["prompt_version"]) for x in q], [("past", "30", self.EX.PROMPT_VERSION)])
        self.assertIn("ある家族が", q[0]["text"])
        short = [json.loads(x) for x in self.EX.OUT.read_text(encoding="utf-8").splitlines()][-1]
        self.assertEqual((short["side"], short["id"], short["model"], short["reason"]), ("past", "20", "rule", "本文が短い"))
        # 2 回目は何も読まない（済み）
        P.run([], limit=10, since="2019-01-01", stop_after=5, max_minutes=0, fetch=lambda sid: (seen.append(sid), pages[sid])[1])
        self.assertEqual(seen, [30, 20])

    def test_daily_run_shares_its_time_with_the_stories_before_the_list_is_done(self):
        story = "<p>" + "ある家族が、古い家を手放す日の朝に集まり、それぞれの思い出を語り合う物語。" * 12 + "</p>"
        pages = {30: page("夜の果て", "2024/03/01 〜 2024/03/10") + story, 20: page("名もなき町", "2022/7/1 〜 2022/7/3") + story}
        seen = []
        got = P.run([20, 30], limit=10, since="2019-01-01", stop_after=5, max_minutes=60,
                    fetch=lambda sid: (seen.append(sid), pages[sid])[1])
        self.assertEqual(got["kept"], 2)                  # 一覧は 6 枚まで（10 の 6 割）なので 2 枚とも読む
        self.assertEqual(got["stories"]["queued"], 2)     # 残り 4 枚の枠で、いま読んだ公演のあらすじも積む
        self.assertEqual(seen, [30, 20, 30, 20])

    def test_second_pass_waits_while_the_queue_is_full(self):
        P.PAST.mkdir(parents=True)
        P.ROWS.write_text(json.dumps({"stage_id": "30", "title": "夜の果て"}) + "\n", encoding="utf-8")
        P.save_progress({"done": True})
        old, P.STORY_QUEUE_MAX = P.STORY_QUEUE_MAX, 1
        try:
            self.EX.QUEUE.write_text(json.dumps({"side": "past", "id": "99", "text": "x"}) + "\n", encoding="utf-8")
            got = P.run([], limit=10, since="2019-01-01", stop_after=5, max_minutes=0, fetch=lambda sid: self.fail("read"))
            self.assertEqual((got["stories"]["queued"], got["stories"]["left"]), (0, 1))
        finally:
            P.STORY_QUEUE_MAX = old

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
