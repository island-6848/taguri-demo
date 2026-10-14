#!/usr/bin/env python3
"""感想のハッシュタグ（hashtags.py・app._hashtags_html）の試験。

    python3 tools/taguri/test_hashtags.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "review"))
import app as APP                                                  # noqa: E402
import hashtags as HT                                              # noqa: E402


class HashtagTest(unittest.TestCase):
    def test_tags_in_text(self):
        self.assertEqual(HT.tags_in("最高 #泣いた ＃また観たい、#ＡＢＣ。#泣いた（#括弧）"),
                         ["泣いた", "また観たい", "ABC", "括弧"])
        self.assertEqual(HT.tags_in("タグなし # 空白"), [])

    def test_counts_and_search(self):
        works = [{"title": "夜", "last_date": "2026-10-01", "verdict": "◎", "note_impression": "#泣いた #会場"},
                 {"title": "<昼>", "last_date": "2026-09-01", "note_impression": "#泣いた"},
                 {"title": "朝", "note_impression": "ふつう"}]
        self.assertEqual(HT.counts(w["note_impression"] for w in works), [("泣いた", 2), ("会場", 1)])
        html = APP._hashtags_html(works, "#泣いた")
        self.assertIn("#泣いた の感想 ── 2 件", html)
        self.assertIn("&lt;昼&gt;", html)                   # 題名は escape する
        self.assertNotIn("<b>朝</b>", html)
        self.assertLess(html.index("<b>夜</b>"), html.index("&lt;昼&gt;"))   # 新しい順
        self.assertIn('class="htag on"', html)


if __name__ == "__main__":
    unittest.main()
