"""eval_favourite_seed must pick favourites and apply seeds as described."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("F", Path(__file__).with_name("eval_favourite_seed.py"))
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)

PEOPLE = {"m1": [("actor", "A"), ("actor", "B")], "m2": [("actor", "A")], "m3": [("actor", "C")],
          "m4": [("actor", "C")], "m5": [("actor", "B"), ("actor", "D")]}


class FavouriteSeedEvalTest(unittest.TestCase):
    def test_favourites_are_people_with_two_or_more_top_ratings(self):
        aside = [("m1", 5), ("m2", 5), ("m3", 5), ("m4", 3)]
        self.assertEqual(F.favourites(aside, PEOPLE), [("actor", "A")])

    def test_seed_reaches_co_workers_but_not_the_favourite_and_fades(self):
        s = {"z": 1.0, "K": 3, "own": False}
        f0 = F.scorer([], ["m1"], [("actor", "A")], PEOPLE, {}, s)
        self.assertGreater(f0("m5"), 0)          # B worked with A
        self.assertIsNone(f0("m2"))              # only A: left out
        history = [("m3", 5), ("m4", 1), ("m3", 5)]
        self.assertLess(F.scorer(history, ["m1"], [("actor", "A")], PEOPLE, {}, s)("m5"), f0("m5"))

    def test_zero_seed_is_the_plain_scorer(self):
        s = {"z": 0.0, "K": 3, "own": False}
        self.assertIsNone(F.scorer([], ["m1"], [("actor", "A")], PEOPLE, {}, s)("m5"))


if __name__ == "__main__":
    unittest.main()
