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


class TitlePartsTest(unittest.TestCase):
    """冠名・タイトル・サブタイトル（起案者の指示 2026-10-20「冠名とサブタイトルもタイトルに含めてほしい」）。
    見出しの形は取得の控えの実物（stage.corich.jp/stage/425300 ほか）と同じ"""

    @staticmethod
    def heading(crown, name, sub):
        h = (f'<div class="mainTitle"><p class="crown">{crown}</p><div class="name"><a href="/stage_main/1">{name}</a></div>'
             f'<p class="subTitle">{sub}</p></div>')
        return h + h.replace('<div class="name">', '<h1 class="name">').replace("</a></div>", "</a></h1>")

    def test_the_row_title_carries_crown_and_subtitle_and_the_key_does_not(self):
        html = page("新喜劇出前ツアー2025", "2025年10月01日 (水) ～ 2025年10月05日 (日)").replace(
            "<body>", "<body>" + self.heading("寛平GMプロデュース公演", "新喜劇出前ツアー2025", "～あなたの肩越しに～"))
        r = P.row_from_html(html, "5001")
        self.assertEqual(r["title"], "寛平GMプロデュース公演 新喜劇出前ツアー2025 ~あなたの肩越しに~")
        self.assertEqual(r["title_main"], "新喜劇出前ツアー2025")

    def test_no_heading_parts_leaves_the_title_as_it_was(self):
        html = page("夏の夜", "2025年10月01日 (水) ～ 2025年10月05日 (日)").replace("<body>", "<body>" + self.heading("", "夏の夜", ""))
        r = P.row_from_html(html, "5002")
        self.assertEqual((r["title"], r["title_main"]), ("夏の夜", "夏の夜"))
        r = P.row_from_html(page("夏の夜", "2025年10月01日 (水)"), "5003")      # 見出しの無い古い形のページ
        self.assertEqual((r["title"], r["title_main"]), ("夏の夜", "夏の夜"))

    def test_a_crown_already_in_the_title_is_not_repeated(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "credits"))
        import fetch_credits as FC
        self.assertEqual(FC.full_title("舞台", "舞台「呪術廻戦」", ""), "舞台「呪術廻戦」")
        self.assertEqual(FC.full_title("創立45周年記念", "鼓童ワン・アース・ツアー2026", ""), "創立45周年記念 鼓童ワン・アース・ツアー2026")


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

    def test_stories_read_this_years_stages_first(self):
        # 起案者の指示（2026-10-19）「2026 年の過去公演とれるところまで取って」。番号の順だと今年の公演が後ろの行に散らばる
        from datetime import date
        story = "<p>" + "ある家族が、古い家を手放す日の朝に集まり、それぞれの思い出を語り合う物語。" * 12 + "</p>"
        this, old = f"{date.today().year}-03-01", "2019-03-01"
        P.PAST.mkdir(parents=True)
        P.ROWS.write_text("".join(json.dumps({"stage_id": s, "title": s, "end": e}) + "\n"
                                  for s, e in (("50", old), ("40", old), ("30", this), ("20", old), ("10", this))), encoding="utf-8")
        p = {"done": True, "story_line": 0}
        seen = []
        got = P.stories(p, limit=3, max_minutes=0, fetch=lambda sid: (seen.append(sid), f"<html><body>{story}</body></html>")[1])
        self.assertEqual(seen, [30, 10, 50])                 # 今年の 2 件を先に、残りの 1 件は順送りで
        self.assertEqual((got["queued"], p["story_line"]), (3, 1))
        got = P.stories(p, limit=10, max_minutes=0, fetch=lambda sid: (seen.append(sid), f"<html><body>{story}</body></html>")[1])
        self.assertEqual(seen[3:], [40, 20])                 # 先に読んだ今年の公演は読み直さない

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

    # 前に取った行の題名に冠名・サブタイトルを足す（起案者の指示 2026-10-20「過去の公演もお願いします」）
    def crowned(self, crown, name, sub=""):
        return (f'<html><head><title>{name} | CoRich</title></head><body><div class="mainTitle"><p class="crown">{crown}</p>'
                f'<h1 class="name"><a href="/stage_main/1">{name}</a></h1><p class="subTitle">{sub}</p></div>'
                "<p>" + "ある家族が、古い家を手放す日の朝に集まり、それぞれの思い出を語り合う物語。" * 12 + "</p></body></html>")

    def test_the_second_pass_also_retitles_the_rows_it_reads(self):
        P.PAST.mkdir(parents=True)
        P.ROWS.write_text("".join(json.dumps({"stage_id": s, "title": t}, ensure_ascii=False) + "\n"
                                  for s, t in (("30", "夜の果て"), ("20", "名もなき町"))), encoding="utf-8")
        p = {"done": True, "story_line": 0}
        pages = {30: self.crowned("特別公演", "夜の果て", "～朝～"), 20: self.crowned("", "名もなき町")}
        got = P.stories(p, limit=10, max_minutes=0, fetch=lambda sid: pages[sid])
        self.assertEqual(got["retitled"], 2)
        self.assertEqual([(r["title"], r["title_main"]) for r in self.rows()],
                         [("特別公演 夜の果て ~朝~", "夜の果て"), ("名もなき町", "名もなき町")])

    def test_rows_the_second_pass_already_passed_are_read_again_in_part_of_the_time(self):
        P.PAST.mkdir(parents=True)
        P.ROWS.write_text("".join(json.dumps({"stage_id": s, "title": t}, ensure_ascii=False) + "\n"
                                  for s, t in (("30", "夜の果て"), ("20", "消えた公演"), ("10", "まだ先"))), encoding="utf-8")
        P.save_progress({"done": True, "story_line": 2})
        self.EX.OUT.write_text("".join(json.dumps({"side": "past", "id": i, "synopsis": "", "elements": []}) + "\n"
                                       for i in ("30", "20", "10")), encoding="utf-8")   # あらすじは 3 件とも済み
        seen = []

        def fetch(sid):
            seen.append(sid)
            if sid == 20:
                raise OSError("404")
            return self.crowned("劇団あおば第3回公演", "夜の果て")
        self.assertEqual(P.retitle_targets(P.load_progress()), 2)      # 2 周目が通り過ぎた 2 行だけ（10 は 2 周目が読む）
        got = P.run([], limit=10, since="2019-01-01", stop_after=5, max_minutes=60, fetch=fetch)
        self.assertEqual(seen, [30, 20])
        self.assertEqual((got["retitle"]["retitled"], got["retitle"]["skipped"], got["retitle"]["left"]), (2, 1, 0))
        self.assertEqual([(r["stage_id"], r["title"], r.get("title_main")) for r in self.rows()],
                         [("30", "劇団あおば第3回公演 夜の果て", "夜の果て"), ("20", "消えた公演", "消えた公演"), ("10", "まだ先", None)])
        # 次の実行: 2 周目があらすじ済みで読まずに通り過ぎた 10 も読み直す。済んだ行（30・20）は二度読まない
        P.run([], limit=10, since="2019-01-01", stop_after=5, max_minutes=60, fetch=fetch)
        self.assertEqual(seen, [30, 20, 10])
        self.assertEqual(P.retitle_targets(P.load_progress()), 0)
        # 時間の決まっていない実行（手で回すとき）では読み直さない
        self.assertEqual(P.run([], limit=10, since="2019-01-01", stop_after=5, max_minutes=0, fetch=fetch).get("retitle"), None)

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
