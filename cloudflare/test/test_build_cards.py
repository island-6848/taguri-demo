"""build_cards: the stored card is render_recommend.card with three markers, so the
Worker's recommend screen shows what the Python screen showed."""
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


class CardTest(unittest.TestCase):
    def setUp(self):
        self.pool = UR.candidate_pool({}, CAT.CANDIDATES)
        self.cards = BC.build(self.pool, {}, TODAY)

    def test_only_stages_not_over(self):
        self.assertEqual(sorted(self.cards), ["101", "102", "106"])

    def test_filled_card_is_the_python_card(self):
        c = BC.stage_dicts(self.pool, {}, TODAY)["101"]
        filled = (self.cards["101"].replace(BC.RANK_MARK, "03")
                  .replace(BC.WHY_MARK, '<li class="rs none">理由を出せていません</li>')
                  .replace(BC.POSTER_MARK, ""))
        self.assertEqual(filled, RR.card(3, c))
        self.assertEqual(self.cards["101"].count(BC.WHY_MARK), 1)

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
