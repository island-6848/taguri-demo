"""The comparison script must measure correctly: checked on a tiny made-up set."""
import importlib.util
import random
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("E", Path(__file__).with_name("eval_person_reco.py"))
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


class MetricTest(unittest.TestCase):
    test = [("a", 5), ("b", 4), ("c", 2), ("d", 5), ("e", 1)]

    def test_perfect_and_reversed(self):
        perfect = E.evaluate_one(lambda m: dict(self.test)[m], self.test, random.Random(0))
        self.assertEqual(perfect["auc_top"], 1.0)
        self.assertAlmostEqual(perfect["ndcg10"], 1.0)
        reverse = E.evaluate_one(lambda m: -dict(self.test)[m], self.test, random.Random(0))
        self.assertEqual(reverse["auc_top"], 0.0)

    def test_unscored_is_neutral(self):
        # Negative scores go below unknown movies, positive above.
        res = E.evaluate_one(lambda m: {"a": 1.0, "e": -1.0}.get(m), self.test, random.Random(0))
        self.assertEqual(res["coverage"], 0.4)
        self.assertEqual(res["auc_scored"], 1.0)


class MethodTest(unittest.TestCase):
    people = {"m1": [("actor", "A")], "m2": [("actor", "A")], "m3": [("actor", "B")],
              "m4": [("actor", "B")], "m5": [("actor", "C")]}

    def test_graded_uses_low_ratings_relative_to_the_user(self):
        # A lenient user: 5 is usual, 4 means "less". A's movie should rank above B's.
        history = [("m1", 5), ("m3", 4), ("m5", 5)]
        f = E.graded(history, self.people)
        self.assertGreater(f("m2"), 0)
        self.assertLess(f("m4"), 0)
        # The current method only sees the top grade, so B's movie is merely unscored.
        g = E.b0_current(history, self.people)
        self.assertIsNone(g("m4"))

    def test_current_needs_top_grade(self):
        f = E.b0_current([("m1", 4), ("m3", 3)], self.people)
        self.assertIsNone(f("m2"))           # no ◎ at all: nothing to recommend
        f = E.b0_relative_top([("m1", 4), ("m3", 3)], self.people)
        self.assertIsNotNone(f("m2"))        # the user's own top grade counts


if __name__ == "__main__":
    unittest.main()
