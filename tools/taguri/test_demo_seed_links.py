"""見本の記録を推薦の材料にする（公演への結び付け）の検査。

一時 DB・一時の出演者の控えで確かめる（外部への通信はしない）。
    python3 tools/taguri/test_demo_seed_links.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_demo_stability as DS                                     # noqa: E402
import measure_nets as M                                             # noqa: E402

APP, R = DS.APP, DS.R
RATED = next(s for s in APP.DEMO_SEED_WORKS if s["verdict"] == "◎")
OTHER = next(s for s in APP.DEMO_SEED_WORKS if s["verdict"] == "○" and s["title"] != RATED["title"])
EMPTY = next(s for s in APP.DEMO_SEED_WORKS if s["verdict"] == "△")


class DemoSeedLinks(unittest.TestCase):
    setUpClass = classmethod(DS.DemoStabilityTests.setUpClass.__func__)
    tearDownClass = classmethod(DS.DemoStabilityTests.tearDownClass.__func__)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "data" / "credits").mkdir(parents=True)
        self.credits = root / "data" / "credits" / "credits.jsonl"
        rows = [
            # 完全一致・クレジットあり → 結び付く
            {"date": RATED["date"], "mail_title": RATED["title"], "stage_id": "9001",
             "fields": {"出演": "検査の俳優甲、検査の俳優乙", "演出": "検査の演出家"}},
            # 題名が少し違う → 結び付かない（推測しない）
            {"date": OTHER["date"], "mail_title": OTHER["title"] + "（再演）", "stage_id": "9002",
             "fields": {"出演": "別の俳優"}},
            # 完全一致だがクレジットが空 → 材料にならないので結び付けない
            {"date": EMPTY["date"], "mail_title": EMPTY["title"], "stage_id": "9003", "fields": {}},
        ]
        self.credits.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        self.patches = [patch.object(M, "CREDITS", self.credits), patch.object(M, "ROOT", root),
                        patch.object(APP, "ROOT", root)]
        for p in self.patches:
            p.start()
        APP._DEMO_LINKS.update(stamp=None, map={})
        with R.connect() as con:
            con.execute("DELETE FROM works")
            if con.execute("SELECT 1 FROM sqlite_master WHERE name='app_setting'").fetchone():
                con.execute("DELETE FROM app_setting")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        APP._DEMO_LINKS.update(stamp=None, map={})
        self.tmp.cleanup()

    def stage_of(self, uid, s):
        with R.connect() as con:
            return R.read_works(con, user_id=uid)[APP._demo_key(s)]["stage_id"]

    def test_only_exact_matches_with_credits_are_linked(self):
        self.assertEqual(APP.demo_seed_links(), {(RATED["date"], RATED["title"]): "9001"})
        uid = self.users_uid(0)
        self.assertEqual(APP.seed_demo_works(uid), len(APP.DEMO_SEED_WORKS))
        self.assertEqual(self.stage_of(uid, RATED), "9001")
        self.assertIn(self.stage_of(uid, OTHER), (None, ""))
        self.assertIn(self.stage_of(uid, EMPTY), (None, ""))

    def test_linked_seed_feeds_the_roster(self):
        uid = self.users_uid(0)
        APP.seed_demo_works(uid)
        rated = M.load_rated(user_id=uid)
        row = next(r for r in rated if r.get("title") == RATED["title"] or r.get("key") == APP._demo_key(RATED))
        people = {p for _role, p in row.get("people") or []}
        self.assertIn("検査の俳優甲", people)
        roster = M.build_roster(rated, lambda v: float(v == "◎"))
        self.assertGreaterEqual(roster.get(("出演", "検査の俳優甲"), (0, 0))[1], 1)   # ◎ の当たりとして数える

    def test_existing_visitors_are_linked_once_and_unlinks_are_respected(self):
        uid = self.users_uid(1)
        # 結び付けを入れる前に見本が入った訪問者を再現する
        with patch.object(APP, "demo_seed_links", return_value={}):
            APP.seed_demo_works(uid)
        APP._write_setting_json(uid, APP.DEMO_LINK_KEY, None)
        self.assertIn(self.stage_of(uid, RATED), (None, ""))
        self.assertEqual(APP.link_demo_seed(uid), 1)
        self.assertEqual(self.stage_of(uid, RATED), "9001")
        # 本人が結び付けを外したら、開き直しても結び付け直さない
        with R.connect() as con:
            con.execute("UPDATE works SET stage_id=NULL WHERE user_id=? AND work_key=?",
                        (uid, APP._demo_key(RATED)))
        self.assertEqual(APP.link_demo_seed(uid), 0)
        self.assertIn(self.stage_of(uid, RATED), (None, ""))

    def test_seeded_visitor_gets_scored_recommendations(self):
        """見本の ◎ に出ていた俳優の、これからの公演が「今週のおすすめ」に理由つきで出る。"""
        uid = self.users_uid(0)
        APP.seed_demo_works(uid)
        upcoming = {"stage_id": "5001", "title": "検査の新作", "group": "検査団体",
                    "theater": "検査劇場", "pref": "東京都", "period": "2099/12/01 - 2099/12/10",
                    "fields": {"出演": "検査の俳優甲"}}
        with patch.object(APP.RR, "load", return_value=({}, [])), \
             patch.object(APP.DG, "all_candidates", return_value=[upcoming]), \
             patch.object(APP, "_overlay_themes", side_effect=lambda d: d):
            d, _ = APP._load(uid)
        top = d["recommend"][0]
        self.assertEqual(top["stage_id"], "5001")
        self.assertTrue(any("検査の俳優甲" in json.dumps(w, ensure_ascii=False) for w in top.get("why_b") or []))

    def test_owner_is_never_touched(self):
        import auth as AU
        self.assertEqual(APP.link_demo_seed(AU.LOCAL_USER_ID), 0)

    def users_uid(self, i):
        return self.users[i][0]


if __name__ == "__main__":
    unittest.main()
