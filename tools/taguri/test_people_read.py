"""「この図から分かること」（people.py の規則の読み）の検査。LLM は呼ばない。

Run: python3 tools/taguri/test_people_read.py
（Worker 側の同じ規則は cloudflare/test/people.test.js が Python の出力と突き合わせる）
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "review"), str(HERE.parents[1] / "cloudflare" / "test" / "screens")]
import people as PE                                                   # noqa: E402
import people_fixture as FX                                           # noqa: E402

CASES = {"main": FX.main_case, "tiny": FX.tiny_case, "split": FX.split_case,
         "undated": FX.undated_case, "years": FX.years_case}


def facts_of(rated):
    g = PE.build(rated)
    tl = PE.timeline(rated, g, {p: i for i, p in enumerate(g["core"])})
    return g, PE.read_facts(rated, g, PE.components(g), tl)


def base(**kw):
    f = {"n_core": 9, "bundles": [9], "top": {"name": "甲", "role": "出演", "works": 5, "splits": 0},
         "bridge": None, "pair": None, "merge": None, "started": None, "recent": None, "long": None,
         "mix": {"n": 9, "makers": 2}}
    f.update(kw)
    return f


class PeopleReadTests(unittest.TestCase):
    def test_no_llm(self):
        self.assertNotIn("llm_gemini", sys.modules)
        self.assertFalse(hasattr(PE, "ask") or hasattr(PE, "PROMPT") or hasattr(PE, "READ_SCHEMA"))

    def test_names_only_from_network_and_polite(self):
        for name, mk in CASES.items():
            rated = mk()
            g, f = facts_of(rated)
            said = [f["top"]["name"]]
            said += [f["bridge"]["name"]] if f["bridge"] else []
            said += [f["pair"][k] for k in "abc" if f["pair"] and f["pair"][k]]
            said += [f["long"]["name"]] if f["long"] else []
            said += [p for p, _n in f["recent"]["people"]] if f["recent"] else []
            for p in said:
                self.assertIn(p, g["nodes"], name)
            lines = PE.reading(f)
            self.assertGreaterEqual(len(lines), 2, name)
            self.assertLessEqual(len(lines), 2 + PE.READ_PICK, name)
            for s in lines:
                self.assertRegex(s, r"(です|ます|ました)。$", name)
                self.assertIsNone(re.search(r"クラスタ|ノード|エッジ|おそらく|かもしれません", s), s)

    def test_panel_carries_reading_for_everyone(self):
        rated = FX.main_case()
        for owner in (True, False):
            html = PE.panel(rated, owner=owner)
            self.assertIn("<h3>この図から分かること</h3>", html)
            self.assertNotIn("data-pread", html)
        self.assertEqual(PE.panel(rated, owner=True), PE.panel(rated, owner=False))

    def test_years_rules(self):
        _g, f = facts_of(FX.years_case())
        self.assertEqual(f["top"]["name"], "長い人")
        self.assertEqual(f["long"], {"name": "甲", "first": 2016, "last": 2022})
        self.assertEqual(f["recent"], {"from": 2021, "people": [["新人A", 2], ["新人B", 2]]})
        self.assertIsNone(f["bridge"])

    def test_bridge_and_merge_in_main(self):
        _g, f = facts_of(FX.main_case())
        self.assertEqual(f["bridge"]["name"], "高橋 &lt;健&gt;")
        self.assertEqual(f["merge"]["sizes"], [28, 10])
        text = "".join(PE.reading(f))
        self.assertIn("高橋 &lt;健&gt;さんを外すと、つながりが 2 つに分かれます。", text)
        self.assertIn("「もう一つの橋」", text)

    def test_scores_choose(self):
        f = base(bridge={"name": "乙", "splits": 3, "people": 4},
                 pair={"a": "丙", "b": "丁", "w": 2, "c": "", "m": 0},
                 started={"date": "2020-01-02", "title": "はじまり"},
                 long={"name": "戊", "first": 2015, "last": 2022},
                 recent={"from": 2021, "people": [["己", 3]]})
        self.assertEqual([PE.READ_SCORE(k, f) for k in ("bridge", "pair", "long", "recent", "started")],
                         [85, 60, 75, 50, 30])
        out = PE.reading(f)
        self.assertEqual(len(out), 5)
        self.assertTrue(out[2].startswith("乙さんを外すと"))
        self.assertTrue(out[3].startswith("丙さんと丁さんは 2 本で"))
        self.assertTrue(out[4].startswith("戊さんは 2015 年から 2022 年まで、8 年"))
        self.assertEqual(PE.READ_SCORE("started", dict(f, merge={"date": "2021-01-01", "title": "x",
                                                                 "sizes": [3, 2]})), 0)
        self.assertTrue(PE.reading(base(top={"name": "甲", "role": "出演", "works": 5, "splits": 2}))[1]
                        .endswith("外すとつながりが 2 つに分かれる人でもあります。"))
        self.assertEqual(PE.reading(base(top=None)), [])

    def test_mix_wording(self):
        last = lambda m: PE.reading(base(n_core=10, mix={"n": 10, "makers": m}))[-1]  # noqa: E731
        self.assertIn("みな出演者です", last(0))
        self.assertIn("ほとんどが出演者です", last(1))
        self.assertIn("出演が 8 名、作り手（演出・脚本ほか）が 2 名です", last(2))
        self.assertIn("作り手の名前もよく重なっています", last(4))


if __name__ == "__main__":
    unittest.main()
