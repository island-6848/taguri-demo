#!/usr/bin/env python3
"""カレンダーから入った公演の出演・スタッフを、公式サイトから取る（2026-10-14 の指摘）。

    python3 tools/taguri/test_calendar_credits.py

通信はしない。公式サイトのページを差し替えて、トップに名前が無いときに同じサイトの
「キャスト」「スタッフ」のページを辿ること、別のサイトや投稿サイトへは行かないことを確かめる。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "credits"))
import fetch_stage_calendar as CAL                                 # noqa: E402
import fetch_official_credits as OF_REAL                           # noqa: E402

TOP = """<html><body><h1>Wゲーム</h1><p>12/10〜12/20 本多劇場</p>
<a href="/stage/cast.html">キャスト・スタッフ</a>
<a href="https://other.example/ad">広告</a></body></html>"""
CAST = """<html><body><h2>キャスト・スタッフ</h2>
<p>出演：甲野一郎　乙川花子</p><p>作：丙田三郎</p><p>演出：丁谷四郎</p></body></html>"""


class FakeOF:
    """fetch_official_credits の取得だけを差し替え、読み取り（roles_in など）は本物を使う。"""
    to_text = staticmethod(OF_REAL.to_text)
    roles_in = staticmethod(OF_REAL.roles_in)
    links = staticmethod(OF_REAL.links)

    def __init__(self, pages):
        self.pages, self.asked = pages, []

    def get(self, url):
        self.asked.append(url)
        return self.pages.get(url, ""), ""


class CalendarCreditsTest(unittest.TestCase):
    def test_follows_the_cast_page_on_the_same_site(self):
        of = FakeOF({"https://kato.example/w/": TOP, "https://kato.example/stage/cast.html": CAST})
        got = CAL.credits_from(of, "https://kato.example/w/")
        self.assertIn("甲野一郎", got.get("出演", ""))
        self.assertEqual(got.get("演出"), "丁谷四郎")
        self.assertNotIn("https://other.example/ad", of.asked)       # 別のサイトへは行かない

    def test_top_page_with_names_is_enough(self):
        of = FakeOF({"https://a.example/": CAST})
        got = CAL.credits_from(of, "https://a.example/")
        self.assertEqual(got.get("演出"), "丁谷四郎")
        self.assertEqual(of.asked, ["https://a.example/"])          # 辿らない

    def test_unreachable_site_gives_nothing(self):
        self.assertEqual(CAL.credits_from(FakeOF({}), "https://gone.example/"), {})

    def test_social_links_are_not_followed(self):
        for u in ("https://x.com/kato_office", "https://www.instagram.com/p/1", "https://mobile.twitter.com/a"):
            self.assertTrue(CAL._social(u), u)
        self.assertFalse(CAL._social("https://www.katoken.example/"))
        rows = [{"fields": {"公式／劇場サイト": "https://x.com/kato_office"}}]
        CAL.add_credits(rows, jobs=1, limit=0)                        # 辿る先が無いので通信しない
        self.assertEqual(rows[0]["fields"], {"公式／劇場サイト": "https://x.com/kato_office"})


if __name__ == "__main__":
    unittest.main()
