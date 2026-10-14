#!/usr/bin/env python3
"""人物の理由に具体的な作品名を出す（起案者の指示 2026-10-14）の試験。

    python3 tools/review/test_reason_works.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_nets as M                                          # noqa: E402
import render_recommend as RR                                     # noqa: E402

KEY = ("出演", "山田太郎")


class ReasonWorksTest(unittest.TestCase):
    def test_titles_in_grade_order_newest_first(self):
        rated = [{"title": "古い◎", "date": "2024-01-01", "verdict": "◎", "people": [KEY]},
                 {"title": "新しい◎", "date": "2025-06-01", "verdict": "◎", "people": [KEY]},
                 {"title": "まる", "date": "2026-01-01", "verdict": "○", "people": [KEY]},
                 {"title": "評価なし", "date": "2026-02-01", "verdict": "", "people": [KEY]}]
        react = {"9": {"interest": 1, "title": "気になる"}, "8": {"interest": 0, "title": "興味なし"}}
        with patch.object(M, "_fields_by_stage", return_value={"9": {"出演": "山田太郎"}, "8": {"出演": "山田太郎"}}):
            got = M.person_titles(rated, react)[KEY]
        self.assertEqual(got, [("新しい◎", "◎"), ("古い◎", "◎"), ("まる", "○"), ("気になる", "興味あり")])

    def test_reason_row_names_works_and_escapes(self):
        c = {"stage_id": "1", "why_b": [[0.1, "出演", "山田太郎", 5], [0.05, "演出", "佐藤", 2]],
             "why_b_works": {"出演\t山田太郎": [["<夜>", "◎"], ["春", "○"], ["冬", "◎"], ["秋", "興味あり"]]}}
        with patch.object(RR, "synopsis_source", return_value=("公演情報", False)):
            html = RR.reason_rows(c)
        self.assertIn("『&lt;夜&gt;』・『春』・『冬』 ほか 1 本", html)
        self.assertNotIn("』◎", html)
        self.assertNotIn("での実績", html)
        self.assertIn("（履歴 2 本）", html)        # 作品名が引けない人は本数で書く


class KindReasonTest(unittest.TestCase):
    """種類だけで上がった公演に「理由を出せていません」を出さない（2026-10-14 の指摘）。"""

    def test_kind_only_show_names_its_kind_and_works(self):
        c = {"stage_id": "1", "why_b": [],
             "why_kind": [[0.2, "#形式", "ミュージカル", 4], [-0.1, "#会場", "本多劇場", 2], [0.05, "#翻訳", "翻訳劇", 1]],
             "why_kind_works": {"#形式\tミュージカル": [["夜", "◎"], ["朝", "○"]]}}
        with patch.object(RR, "synopsis_source", return_value=("公演情報", False)):
            html = RR.reason_rows(c)
        self.assertNotIn("理由を出せていません", html)
        self.assertIn("形式 <b>ミュージカル</b>", html)
        self.assertIn("（『夜』・『朝』）", html)
        self.assertIn("<b>翻訳劇</b><span class=\"n\">（履歴 1 本）", html)
        self.assertNotIn("本多劇場", html)          # 点を下げた種類は理由にしない

    def test_prepare_attaches_titles_to_kinds(self):
        import user_recommender as UR
        rated = [{"key": f"r{i}", "title": f"作品{i}", "date": f"2025-01-0{i}", "verdict": v,
                  "people": [["出演", f"人{i}"]], "stage_id": str(i)} for i, v in ((1, "◎"), (2, "◎"), (3, "×"), (4, "×"))]
        for r in rated[:2]:
            r["title"] = r["title"] + "ミュージカル"
        cand = {"stage_id": "9", "title": "新作ミュージカル", "period": "2099/01/01 ～ 2099/01/05",
                "fields": {"出演": "知らない人"}}
        got = UR.prepare({}, [cand], rated, multipliers={}, role_group=lambda r: "cast")
        c = next(x for x in got["ranked"] if x["stage_id"] == "9") if got.get("ranked") else None
        self.assertIsNotNone(c)
        self.assertEqual(c["why_b"], [])
        self.assertTrue(any(k[1] == "#形式" and k[0] > 0 for k in c["why_kind"]))
        self.assertEqual([t for t, _ in c["why_kind_works"]["#形式\tミュージカル"]], ["作品2ミュージカル", "作品1ミュージカル"])


class PriceTest(unittest.TestCase):
    def test_price_range(self):
        self.assertEqual(RR.price_range("一般 5,000円 学生 3,000円【発売日】2026/09/01"), (3000, 5000))
        self.assertEqual(RR.price_range("前売３５００円／当日４０００円"), (3500, 4000))   # 全角も読む
        self.assertEqual(RR.price_range("¥4,500"), (4500, 4500))
        self.assertEqual(RR.price_range("入場無料（要予約）"), (0, 0))
        self.assertIsNone(RR.price_range("未定"))
        self.assertIsNone(RR.price_range(""))

    def test_ticket_carries_the_range(self):
        self.assertEqual(RR._price_attr({"price": "3,000円"}), ' data-yen="3000-3000"')
        self.assertEqual(RR._price_attr({"price": "料金未定"}), "")


class TicketDetailsTest(unittest.TestCase):
    def test_run_range_and_year(self):
        from datetime import date
        t = date(2026, 10, 14)
        self.assertEqual(RR.run_range("2026/10/24 (金) ～ 2026/10/31 (金)", t), "10/24〜10/31")
        self.assertEqual(RR.run_range("2026/12/28 ～ 2027/1/7", t), "2026/12/28〜2027/1/7")
        self.assertEqual(RR.run_range("2027/1/5 ～ 2027/1/9", t), "2027/1/5〜1/9")
        self.assertEqual(RR.run_range("2026/11/1", t), "11/1")
        self.assertEqual(RR.run_range("未定", t), "")

    def test_sale_goes_to_ticket_page(self):
        self.assertEqual(RR.ticket_url({"price": "5,000円 詳細は https://stage.parco.jp/x 」", "url": "https://o.jp"}),
                         "https://stage.parco.jp/x")
        self.assertEqual(RR.ticket_url({"url": "https://o.jp/show"}),
                         "https://o.jp/show#tickets:~:text=%E3%83%81%E3%82%B1%E3%83%83%E3%83%88")
        self.assertEqual(RR.ticket_url({"url": "https://o.jp/show#ticket"}), "https://o.jp/show#ticket")
        self.assertEqual(RR.ticket_url({"stage_id": "512400"}), "https://stage.corich.jp/stage/512400")
        self.assertIn('rel="noopener noreferrer"', RR.sale_pill({"url": "https://o.jp"}, "発売済み", "ok"))
        self.assertEqual(RR.sale_pill({"url": "javascript:x"}, "発売済み", "ok"), '<span class="pill ok">発売済み</span>')

    def test_limits_note_goes_to_info(self):
        html = RR.limits_html({"recommend": [{"synopsis": ""}]})
        self.assertIn('class="note toinfo"', html)


if __name__ == "__main__":
    unittest.main()
