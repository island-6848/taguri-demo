"""build_cards: a stored card, filled by `compose`, is render_recommend.ticket in each of
the four lists, so the Worker's screens show what the Python screens showed."""
import datetime
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "screens"))
spec = importlib.util.spec_from_file_location("build_cards", HERE.parent / "scripts" / "build_cards.py")
BC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BC)
import catalogue as CAT                                              # noqa: E402
import render_recommend as RR                                        # noqa: E402
import user_recommender as UR                                        # noqa: E402

TODAY = datetime.date.fromisoformat(CAT.TODAY)
WHY = '<li class="rs b"><span class="net">人物</span>出演 <b>俳優甲</b></li>'
TICKETS = [{"date": "2026-11-02", "time": "18:30", "confirmed": 1},
           {"date": "2026-11-05", "time": "", "confirmed": 0, "sid": "101"}]


class CardTest(unittest.TestCase):
    def setUp(self):
        self.pool = UR.candidate_pool({}, CAT.CANDIDATES)
        self.cards = BC.build(self.pool, {}, TODAY)
        self.stages = BC.stage_dicts(self.pool, {}, TODAY)

    def test_only_stages_not_over(self):
        self.assertEqual(sorted(self.cards), ["101", "102", "106"])

    def test_every_list_gets_the_python_card(self):
        for sid in self.cards:
            c = self.stages[sid]
            t = self.cards[sid]
            self.assertEqual(BC.compose(t, sid, "recommend", rank=3), RR.card(3, c))
            self.assertEqual(BC.compose(t, sid, "recommend", rank=12, why=WHY),
                             RR.card(12, dict(c, why_b=[[1, "出演", "俳優甲", 1]])).replace(
                                 RR.reason_rows(dict(c, why_b=[[1, "出演", "俳優甲", 1]])), WHY))
            self.assertEqual(BC.compose(t, sid, "interest", note="俳優甲 & <乙>"),
                             RR.ticket(c, mode="interest", note="俳優甲 & <乙>"))
            self.assertEqual(BC.compose(t, sid, "interest"), RR.ticket(c, mode="interest"))
            fav = '<li class="rs a">登録した人「俳優甲」の公演です</li>'
            self.assertEqual(BC.compose(t, sid, "favourite", why=fav),
                             RR.ticket(dict(c, a=[]), mode="favourite").replace(RR.declared_rows({}), fav))
            self.assertEqual(BC.compose(t, sid, "owned", mytix=BC.mytix_html(c, TICKETS)),
                             RR.ticket(c, mode="owned", my_tickets=TICKETS))
            self.assertEqual(BC.compose(t, sid, "owned", mytix=BC.mytix_html(c, [])),
                             RR.ticket(c, mode="owned", my_tickets=[]))

    def test_a_tour_lists_every_venue(self):
        pool = dict(self.pool)
        pool["301"] = dict(pool["101"], stage_id="301", theater="劇場Z", pref="大阪府",
                           period="2026/12/01~2026/12/03")
        cards = BC.build(pool, {}, TODAY)
        self.assertIn('data-tours="301"', cards["101"])
        self.assertIn('data-tours="101"', cards["301"])
        self.assertIn("大阪公演", cards["101"])

    def test_versioned_upload(self):
        sql = BC.to_sql(self.cards)
        self.assertTrue(sql[0].startswith("DELETE FROM rec_card WHERE ver="))
        self.assertIn("INSERT INTO rec_meta(k,v) VALUES('rec_card'", sql[-2])
        self.assertTrue(sql[-1].startswith("DELETE FROM rec_card WHERE ver<>"))


if __name__ == "__main__":
    unittest.main()
