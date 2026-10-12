"""感想→特徴への好み→推薦の回帰テスト。実データ・ネットワークは使わない。

    python3 tools/taguri/test_impression_preferences.py
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/taguri"), str(ROOT / "tools/review")]
import impression_preferences as IP
import app as APP
import net_c as C
import rate_performances as R
import feedback as FB
import render_recommend as RR
import recommend2 as RC2
import hand_themes as HT
import user_recommender as UR


def work(key="w", note="家族の描写がよかった。", **kwargs):
    return {"work_key": key, "title": "観た作品", "first_date": "2020-01-01",
            "stage_id": "past", "note_impression": note, **kwargs}


def theme(*words):
    return {"elements": [{"word": w, "kind": "題材"} for w in words]}


def candidate(sid, words, strong=1, s=1):
    return {"stage_id": sid, "title": sid, "themes": words, "strong": strong,
            "s": s, "b": .1 if strong else 0, "c": 0,
            "total": .1 if strong else 0,
            "why_b": [[.1, "出演", "テスト出演者", 2]] if strong else [], "why_c": [], "a": [],
            "period": "2099/01/01 (木) 〜 2099/01/02 (金)"}


class ExtractionTests(unittest.TestCase):
    def values(self, note, words=("家族", "恋愛")):
        return {s["feature"]: s["value"] for s in IP.extract(note, list(words))}

    def test_mixed_aspects(self):
        self.assertEqual(self.values("家族の描写がよかったけど、恋愛は苦手だった。"),
                         {"家族": 1, "恋愛": -1})

    def test_two_aspects_without_punctuation(self):
        self.assertEqual(self.values("家族は好きで恋愛は苦手だった"), {"家族": 1, "恋愛": -1})

    def test_negation(self):
        for phrase in ("面白くなかった", "好きではない", "好きじゃなかった", "楽しめなかった"):
            with self.subTest(phrase=phrase):
                self.assertEqual(self.values("恋愛は" + phrase), {"恋愛": -1})

    def test_double_negation_is_held(self):
        self.assertEqual(self.values("家族は苦手ではない。恋愛が好きじゃないわけではない。"), {})

    def test_weak_positive(self):
        self.assertEqual(self.values("家族の描写は悪くなかった。"), {"家族": .5})

    def test_uncertain(self):
        for phrase in ("家族は好きかもしれない", "家族は面白かったとは思わない"):
            self.assertEqual(self.values(phrase), {})

    def test_overall_verdict_is_not_all_features(self):
        self.assertEqual(self.values("面白かった。最高だった！"), {})

    def test_emotion_is_not_dislike(self):
        self.assertEqual(self.values("家族の別れが悲しかった。恋愛に苦しくなった。"), {})

    def test_reported_dialogue_is_not_preference(self):
        self.assertEqual(self.values("登場人物が『恋愛は嫌い』と言った。"), {})

    def test_unregistered_feature_is_not_learned(self):
        self.assertEqual(self.values("恋愛が好き", ("家族",)), {})

    def test_evaluation_of_a_different_subject_is_not_attached(self):
        self.assertEqual(self.values("家族の話で演技がよかった。"), {})

    def test_aliases(self):
        self.assertEqual(self.values("会話の掛け合いが面白かった。", ("会話劇",)),
                         {"会話の掛け合い": 1})

    def test_different_features_are_not_substring_matched(self):
        profile = IP.build_profile([work(note="恋愛が好き")], {("rated", "w"): theme("恋愛")})
        self.assertEqual(IP.score(["恋愛が多い"], profile), (0, []))


class ProfileTests(unittest.TestCase):
    def test_repetition_within_work_is_one_vote(self):
        rows = [work(note="家族が好き。家族が好き。", times=10)]
        p = IP.build_profile(rows, {("rated", "w"): theme("家族")})
        self.assertEqual(p["家族"]["count"], 1)
        self.assertEqual(p["家族"]["weight"], .25)

    def test_more_works_strengthen_evidence(self):
        rows = [work(key=str(i)) for i in range(5)]
        p = IP.build_profile(rows, {("candidate", "past"): theme("家族")})
        self.assertEqual(p["家族"]["count"], 5)
        self.assertGreater(p["家族"]["weight"], .25)

    def test_conflicting_assessments_in_one_work_are_held(self):
        p = IP.build_profile([work(note="家族は好き。家族は苦手。")], {("rated", "w"): theme("家族")})
        self.assertEqual(p, {})

    def test_unseen_work_is_not_used(self):
        self.assertEqual(IP.build_profile([work(unseen=True)], {("rated", "w"): theme("家族")}), {})

    def test_rating_does_not_override_aspect(self):
        p = IP.build_profile([work(verdict="×")], {("rated", "w"): theme("家族")})
        self.assertGreater(p["家族"]["weight"], 0)

    def test_bounded_even_with_many_tags(self):
        rows = [work(key=str(i), note="家族が好き。恋愛が好き。喜劇が好き。友情が好き。") for i in range(100)]
        p = IP.build_profile(rows, {("candidate", "past"): theme("家族", "恋愛", "喜劇", "友情")})
        adjustment, why = IP.score(["家族", "恋愛", "喜劇", "友情"], p)
        self.assertLessEqual(abs(adjustment), IP.WEIGHT)
        self.assertLessEqual(len(why), IP.TOP_N)


class RankingTests(unittest.TestCase):
    def test_positive_and_negative_change_actual_order(self):
        p = IP.build_profile([work(note="家族が好き。恋愛が苦手。")], {("rated", "w"): theme("家族", "恋愛")})
        data = {"ranked": [candidate("romance", ["恋愛"], s=1.5), candidate("family", ["家族"], s=.5)]}
        original = copy.deepcopy(data)
        out = IP.rerank(data, p)
        self.assertEqual([c["stage_id"] for c in out["ranked"]], ["family", "romance"])
        self.assertLess(out["ranked"][1]["impression_score"], 0)
        self.assertEqual(data, original)

    def test_material_missing_is_neutral(self):
        p = IP.build_profile([work()], {("rated", "w"): theme("家族")})
        self.assertEqual(IP.score([], p), (0, []))

    def test_new_candidate_can_be_recommended_by_features(self):
        p = IP.build_profile([work()], {("rated", "w"): theme("家族")})
        out = IP.rerank({"ranked": [], "unscored": [candidate("new", ["家族"], 0, 0)]}, p)
        self.assertEqual(out["recommend"][0]["stage_id"], "new")
        self.assertTrue(out["recommend"][0]["why_impression"])

    def test_empty_or_disabled_profile_preserves_ranking(self):
        data = {"ranked": [candidate("first", [], 2), candidate("second", ["家族"])],
                "unscored": [candidate("new", ["家族"], 0, 0)]}
        p = IP.build_profile([work()], {("rated", "w"): theme("家族")})
        for profile, multiplier in (({}, 1), (p, 0)):
            out = IP.rerank(data, profile, multiplier=multiplier)
            self.assertEqual([c["stage_id"] for c in out["ranked"]], ["first", "second"])
            self.assertEqual(len(out["unscored"]), 1)

    def test_other_buckets_unchanged(self):
        data = {"ranked": [], **{k: [candidate(k, ["家族"])] for k in
                               ("others", "owned", "tracking", "favourites", "declined", "started")}}
        p = IP.build_profile([work()], {("rated", "w"): theme("家族")})
        self.assertEqual({k: v for k, v in IP.rerank(data, p).items() if k in data}, data)

    def test_explanation_uses_and_escapes_evidence(self):
        p = IP.build_profile([work(title="<script>作品</script>", note="家族が好き<script>。")],
                             {("rated", "w"): theme("家族")})
        c = IP.rerank({"ranked": [candidate("next", ["家族"])]}, p)["recommend"][0]
        with patch.object(RR, "synopsis_source", return_value=("公演情報", False)):
            html = RR.reason_rows(c)
        self.assertIn("あなたの感想", html)
        self.assertIn("家族が好き", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("0.25", html)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        for obj, attr, value in ((R, "DB", tmp / "ratings.db"), (FB, "DB", tmp / "ratings.db"),
                                 (APP, "DB", tmp / "ratings.db"), (R, "SRC", tmp / "purchases.jsonl"),
                                 (APP, "ROOT", tmp), (HT, "FILE", tmp / "hand.json")):
            self.stack.enter_context(patch.object(obj, attr, value))
        self.themes = {("candidate", "past"): theme("家族", "恋愛"),
                       ("candidate", "family"): theme("家族"),
                       ("candidate", "romance"): theme("恋愛")}
        self.stack.enter_context(patch.object(C, "load_themes", return_value=self.themes))
        self.stack.enter_context(patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")))
        self.stack.enter_context(patch.object(APP, "_auto_own_from_mail"))
        self.stack.enter_context(patch.object(APP, "waiting_rows", return_value=[]))
        self.stack.enter_context(patch.object(APP, "_upcoming_index", return_value={"rows": {}}))
        self.stack.enter_context(patch.object(APP, "_is_owner", return_value=False))
        self.stack.enter_context(patch.object(APP.IM, "by_person", return_value={}))
        self.raw = {"ranked": [candidate("romance", ["恋愛"], s=1.5), candidate("family", ["家族"], s=.5)],
                    "recommend": [candidate("romance", ["恋愛"], s=1.5)]}
        self.stack.enter_context(patch.object(RR, "load", side_effect=lambda: (copy.deepcopy(self.raw), [])))
        # This suite isolates saved impression integration from the separately
        # tested live person scorer. Its prepared boundary includes zero-score rows.
        self.stack.enter_context(patch.object(UR, "prepare", side_effect=lambda *a, **k: {
            **copy.deepcopy(self.raw), "ranked": copy.deepcopy(
                self.raw.get("ranked", []) + self.raw.get("unscored", []))}))
        for user in ("alice", "bob"):
            APP.add_work(user, "観た作品", "2020-01-01", stage_id="past")

    def key(self, user):
        return APP._works(user)[0]["work_key"]

    def ids(self, user):
        return [r["stage_id"] for r in APP._load(user)[0]["ranked"]]

    def test_save_edit_delete_and_user_isolation(self):
        APP.save_work_field("alice", self.key("alice"), note="家族が好き。恋愛が苦手。")
        APP.save_work_field("bob", self.key("bob"), note="恋愛が好き。家族が苦手。")
        self.assertEqual(self.ids("alice"), ["family", "romance"])
        self.assertEqual(self.ids("bob"), ["romance", "family"])
        for part in APP._load("alice")[0]["recommend"][0]["why_impression"]:
            self.assertNotIn("恋愛が好き", part["evidence"]["quote"])
        APP.save_work_field("alice", self.key("alice"), note="恋愛が好き。家族が苦手。")
        self.assertEqual(self.ids("alice"), ["romance", "family"])
        APP.save_work_field("alice", self.key("alice"), note="")
        self.assertEqual(self.ids("alice"), ["romance", "family"])
        self.assertFalse(APP._load("alice")[0]["recommend"][0]["why_impression"])

    def test_theme_off_disables_preference(self):
        APP.save_work_field("alice", self.key("alice"), note="家族が好き")
        APP.save_weight("alice", "theme", "off")
        self.assertEqual(self.ids("alice"), ["romance", "family"])
        self.assertFalse(APP._load("alice")[0]["recommend"][0]["why_impression"])

    def test_owner_does_not_fall_back_to_stale_quotes(self):
        stale = {"テスト出演者": [{"work_key": "stale", "title": "古い作品", "date": "", "times": 1,
                                 "note": "削除した感想"}]}
        with patch.object(APP, "_is_owner", return_value=True), patch.object(RR, "NOTES_BY_PERSON", stale):
            data = APP._load("alice")[0]
            html = RR.reason_rows(data["ranked"][0])
        self.assertNotIn("削除した感想", html)

    def test_future_record_is_not_used(self):
        con = R.connect()
        with con:
            con.execute("UPDATE works SET first_date='2099-01-01' WHERE user_id='alice'")
        con.close()
        APP.save_work_field("alice", self.key("alice"), note="家族が好き")
        self.assertEqual(self.ids("alice"), ["romance", "family"])

    def test_new_unscored_candidate_and_reaction_routing(self):
        self.raw = {"ranked": [], "recommend": [],
                    "unscored": [candidate("family", ["家族"], 0, 0)]}
        APP.save_work_field("alice", self.key("alice"), note="家族が好き")
        self.assertEqual(self.ids("alice"), ["family"])
        con = FB.connect()
        with con:
            FB.react(con, "test", "family", interest=0, user_id="alice")
        con.close()
        self.assertEqual(self.ids("alice"), [])
        self.assertEqual(APP._load("alice")[0]["others"][0]["stage_id"], "family")

    def test_feature_only_tour_promotion_keeps_one_slot_and_all_venues(self):
        first = candidate("tour-one", ["家族"], 0, 0)
        second = candidate("tour-two", ["家族"], 0, 0)
        for item, venue in ((first, "東京劇場"), (second, "大阪劇場")):
            item.update(title="同じ制作", group="同じ団体", theater=venue,
                        fields={"出演": "同じ出演者"})
        for item in (first, second):
            self.themes[("candidate", item["stage_id"])] = theme("家族")
        self.raw = {"ranked": [], "unscored": [first, second]}
        APP.save_work_field("alice", self.key("alice"), note="家族が好き")
        result = APP._load("alice")[0]
        self.assertEqual(len(result["recommend"]), 1)
        self.assertEqual(result["n_scored"], 1)
        representative = result["recommend"][0]
        self.assertEqual({representative["stage_id"], *[t["stage_id"] for t in representative["tours"]]},
                         {"tour-one", "tour-two"})
        self.assertEqual({representative["theater"], *[t["theater"] for t in representative["tours"]]},
                         {"東京劇場", "大阪劇場"})

    def test_same_title_different_producers_remain_separate_after_promotion(self):
        rows = [candidate("producer-a", ["家族"], 0, 0), candidate("producer-b", ["家族"], 0, 0)]
        for row, group in zip(rows, ("甲団体", "乙団体")):
            row.update(title="同じ題名", group=group, fields={"出演": "同じ出演者"})
        for item in rows:
            self.themes[("candidate", item["stage_id"])] = theme("家族")
        self.raw = {"ranked": [], "unscored": rows}
        APP.save_work_field("alice", self.key("alice"), note="家族が好き")
        self.assertEqual(set(self.ids("alice")), {"producer-a", "producer-b"})

    def test_candidate_batch_keeps_unscored_features(self):
        tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        path = tmp / "candidates.jsonl"
        path.write_text(json.dumps({**candidate("family", ["家族"], 0, 0),
                                    "fields": {}, "theater": "劇場", "pref": "東京都"},
                                   ensure_ascii=False) + "\n", encoding="utf-8")
        output = tmp / "recommend.json"
        with contextlib.ExitStack() as stack:
            for attr in ("FAV", "CALENDAR", "PICKED"):
                stack.enter_context(patch.object(RC2, attr, tmp / (attr + ".jsonl")))
            stack.enter_context(patch.object(RC2, "CAND", path))
            stack.enter_context(patch.object(RC2.M, "load_rated", return_value=[]))
            stack.enter_context(patch.object(RC2.RC1, "load_declined", return_value=[]))
            stack.enter_context(patch.object(sys, "argv", ["recommend2.py", "--today", "2026-10-12",
                                                          "--no-snapshot", "--out", str(output)]))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            self.assertEqual(RC2.main(), 0)
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["recommend"], [])
        self.assertEqual(data["unscored"][0]["themes"], ["家族"])
        self.raw = data
        APP.save_work_field("alice", self.key("alice"), note="家族が好き")
        self.assertEqual(self.ids("alice"), ["family"])


if __name__ == "__main__":
    unittest.main()
