"""Feedback-loop acceptance tests using temporary DB/catalog and real HTTP.

No synthetic fixture result is evidence of real recommendation accuracy.
Run: python tools/taguri/test_user_recommendation.py
"""
from __future__ import annotations

import copy
import datetime
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_demo_stability import DemoStabilityTests, APP, R, FB
import measure_nets as M
import user_recommender as UR


def candidate(sid, person, *, day="2099/12/01", title=None, group="検査用団体"):
    return {"stage_id": str(sid), "title": title or "検査公演" + str(sid),
            "group": group, "theater": "検査用劇場", "pref": "東京都",
            "period": day + " - " + day, "fields": {"出演": person}}


class FeedbackLoopTests(DemoStabilityTests):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = R.DB.parent.parent
        data = root / "data/review"
        data.mkdir(parents=True)
        cls.catalog = [candidate(101, "俳優甲"), candidate(102, "俳優乙"),
                       candidate(103, "俳優丙"), candidate(104, "俳優甲", day="2000/01/01")]
        (data / "candidates.jsonl").write_text(
            "\n".join(json.dumps(c, ensure_ascii=False) for c in cls.catalog))
        for name in ("favourites", "calendar", "picked"):
            path = data / (name + ".jsonl")
            path.write_text("")
        cls.stack.enter_context(patch.object(M, "ROOT", root))
        cls.stack.enter_context(patch.object(M, "CREDITS", root / "missing-credits.jsonl"))
        for attr, name in (("CAND", "candidates"), ("FAV", "favourites"),
                           ("CALENDAR", "calendar"), ("PICKED", "picked")):
            cls.stack.enter_context(patch.object(APP.DG, attr, data / (name + ".jsonl")))
        owner = candidate(999, "他人の俳優")
        owner.update(b=99, c=99, s=99, strong=99, why_b=[[99, "出演", "他人の俳優", 99]])
        cls.raw = {"ranked": [owner], "recommend": [owner], "n_cand": 1, "n_scored": 1}
        cls.stack.enter_context(patch.object(APP.RR, "load", return_value=(cls.raw, [])))
        cls.stack.enter_context(patch.object(APP, "_overlay_themes", side_effect=lambda d: d))
        cls.stack.enter_context(patch.object(APP, "_upcoming_index", return_value={
            "rows": {c["stage_id"]: c for c in cls.catalog}}))

    def setUp(self):
        with R.connect() as con:
            for table in ("works", "excluded", "hand_credits"):
                con.execute("DELETE FROM " + table)
            for table in ("rank_weight", "app_setting"):
                if con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone():
                    con.execute("DELETE FROM " + table)
        with FB.connect() as con:
            for table in ("reaction", "ticket"):
                con.execute("DELETE FROM " + table)
        self.srv.screen_cache.clear()

    def add_rating(self, title, person, verdict, *, user=0, stage_id=""):
        status, result = self.request("/api/add_work", user=user, body={
            "title": title, "date": "2020-01-01"})
        self.assertEqual(status, 200, result)
        key = result["work_key"]
        if person:
            status, result = self.request("/api/hand_credits", user=user,
                body={"work_key": key, "fields": {"出演": person}})
            self.assertEqual(status, 200, result)
        if stage_id:
            status, result = self.request("/api/link_stage", user=user,
                body={"work_key": key, "stage_id": stage_id})
            self.assertEqual(status, 200, result)
        status, result = self.request("/api/rate", user=user,
            body={"work_key": key, "verdict": verdict})
        self.assertEqual(status, 200, result)
        return key

    def history(self, *, user=0):
        key = self.add_rating("甲の過去", "俳優甲", "◎", user=user)
        self.add_rating("乙の過去", "俳優乙", "×", user=user)
        self.add_rating("丙の過去", "俳優丙", "△", user=user)
        return key

    def load(self, user=0):
        return APP._load(self.users[user][0])[0]

    def test_rating_change_recomputes_score_and_reasons_only_for_writer(self):
        key = self.history()
        self.history(user=1)
        before_other = self.load(1)
        before = self.load()
        self.assertEqual(before["recommend"][0]["stage_id"], "101")
        self.assertEqual(before["recommend"][0]["why_b"][0][2], "俳優甲")
        status, result = self.request("/api/rate", body={"work_key": key, "verdict": "×"})
        self.assertEqual(status, 200)
        self.assertEqual(result["recommendation"]["status"], "on_next_read")
        after = self.load()
        # person-graded-v2 reads grades relative to the user: with ×, ×, △ the
        # △ production is this user's best, so its actor is the only one
        # recommended; the actors of the two × productions are not.
        self.assertEqual([c["stage_id"] for c in after["recommend"]], ["103"])
        self.assertEqual(after["recommend"][0]["why_b"][0][2], "俳優丙")
        self.assertEqual(self.load(1), before_other)

    def test_clearing_and_dropping_remove_old_positive_signal(self):
        key = self.history()
        for verdict in ("まだ判断できない", "◎"):
            self.request("/api/rate", body={"work_key": key, "verdict": verdict})
            if verdict != "◎":
                self.assertFalse(any(c["stage_id"] == "101" for c in self.load()["recommend"]))
        status, result = self.request("/api/drop_work", body={"work_key": key})
        self.assertEqual(status, 200, result)
        # Without the ◎ record, the △ production is the user's best (v2).
        self.assertEqual([c["stage_id"] for c in self.load()["recommend"]], ["103"])
        status, result = self.request("/api/restore_work", body={"key": key})
        self.assertEqual(status, 200, result)
        self.assertEqual(self.load()["recommend"][0]["stage_id"], "101")

    def test_link_and_unlink_change_available_person_material(self):
        key = self.add_rating("情報がない記録", "", "◎")
        self.add_rating("乙の記録", "俳優乙", "×")
        self.add_rating("丙の記録", "俳優丙", "×")
        self.assertEqual(self.load()["recommend"], [])
        self.request("/api/link_stage", body={"work_key": key, "stage_id": "104"})
        self.assertEqual(self.load()["recommend"][0]["stage_id"], "101")
        self.request("/api/link_stage", body={"work_key": key, "stage_id": ""})
        self.assertEqual(self.load()["recommend"], [])

    def test_real_screen_ignores_stale_fragment_and_owner_scores(self):
        self.history()
        raw = copy.deepcopy(self.raw)
        uid = self.users[0][0]
        self.srv.screen_cache_set(uid, "recommend|", {"body_html": "STALE_OWNER"})
        status, result = self.request("/api/screen/recommend")
        self.assertEqual(status, 200, result)
        self.assertIn("俳優甲", result["body_html"])
        self.assertNotIn("STALE_OWNER", result["body_html"])
        self.assertNotIn("他人の俳優", result["body_html"])
        self.assertEqual(self.raw, raw)

    def test_expired_owned_interested_and_favorite_constraints(self):
        self.history()
        self.assertNotIn("104", [c["stage_id"] for c in self.load()["recommend"]])
        status, result = self.request("/api/react", body={"stage_id": "101", "value": "interest"})
        self.assertEqual(status, 200, result)
        d = self.load()
        self.assertEqual(d["recommend"], [])
        self.assertEqual(d["tracking"][0]["stage_id"], "101")

    def test_react_saves_first_and_fills_separately(self):
        # 記録と入れ替わりの 1 枚を別の要求に分けた（起案者の指摘 2026-10-14「書き込みがこんなに遅いのはなぜ？」）
        self.history()
        status, result = self.request("/api/react", body={"stage_id": "101", "value": "interest",
                                                          "nofill": True, "siblings": []})
        self.assertEqual(status, 200, result)
        self.assertNotIn("fill", result)
        self.assertEqual(self.load()["tracking"][0]["stage_id"], "101")
        status, result = self.request("/api/react", body={"stage_id": "101", "fill_only": True, "shown": ["101"]})
        self.assertEqual(status, 200, result)
        self.assertIn("fill", result)
        self.assertEqual(self.load()["tracking"][0]["stage_id"], "101")    # fill_only は何も書かない

    def test_provenance_is_per_field_and_survives_reopening(self):
        uid = self.users[0][0]
        APP.seed_demo_works(uid)
        with R.connect() as con:
            key, before = next(iter(R.read_works(con, user_id=uid).items()))
        self.assertEqual(before["verdict_source"], "demo")
        APP.save_work_field(uid, key, note="本人の感想")
        with R.connect() as con:
            row = R.read_works(con, user_id=uid)[key]
        self.assertEqual((row["verdict_source"], row["note_source"]), ("demo", "user"))
        APP.save_work_field(uid, key, verdict="◎")
        with R.connect() as con:
            row = R.read_works(con, user_id=uid)[key]
        self.assertEqual((row["verdict_source"], row["note_source"]), ("user", "user"))
        self.assertEqual(row["note_impression"], "本人の感想")

    def test_foreign_work_cannot_be_rated(self):
        key = self.history()
        status, _ = self.request("/api/rate", user=1, body={"work_key": key, "verdict": "◎"})
        self.assertEqual(status, 400)

    def test_favorites_weights_and_pref_filter_use_current_user(self):
        self.history()
        uid = self.users[0][0]
        APP.save_declared(uid, {"人": ["俳優甲"]})
        d = self.load()
        self.assertEqual(d["recommend"], [])
        self.assertEqual(d["favourites"][0]["stage_id"], "101")
        APP.save_declared(uid, {})
        APP.save_weights(uid, {"cast": "off"})
        self.assertEqual(self.load()["recommend"], [])
        APP.save_weights(uid, {"cast": "mid"})
        d = self.load()
        self.assertEqual(d["recommend"][0]["stage_id"], "101")
        self.assertEqual(APP.RR.filtered(d, ["大阪府"]), ([], 0))

    def test_note_edit_preserves_demo_rating_origin(self):
        uid = self.users[0][0]
        APP.seed_demo_works(uid)
        with R.connect() as con:
            key = next(iter(R.read_works(con, user_id=uid)))
        self.request("/api/note", body={"work_key": key, "note_impression": "自分の言葉"})
        with R.connect() as con:
            row = R.read_works(con, user_id=uid)[key]
        self.assertEqual(row["verdict_source"], "demo")
        self.assertEqual(row["note_source"], "user")


class ScoringTests(unittest.TestCase):
    def prepare(self, rated, cands):
        return UR.prepare({}, cands, rated, multipliers={}, role_group=APP.group_of,
                          today=datetime.date(2026, 10, 12))

    def test_repeated_production_does_not_inflate_evidence(self):
        rows = [{"key": str(i), "stage_id": "1", "date": "2020-01-01",
                 "verdict": "◎", "people": [("出演", "俳優甲")]} for i in range(15)]
        rows.append({"key": "other", "verdict": "×", "people": []})
        d = self.prepare(rows, [candidate(101, "俳優甲")])
        self.assertEqual(d["profile"]["n_rated"], 2)
        self.assertEqual(d["ranked"][0]["why_b"][0][3], 1)

    def test_full_parts_top_three_and_catalog_beyond_common_top(self):
        names = ["俳優" + c for c in "甲乙丙丁戊己庚辛"]
        rows = [{"key": n, "verdict": "◎", "people": [("出演", n)]} for n in names]
        rows += [{"key": str(i), "verdict": "×", "people": []} for i in range(20)]
        d = self.prepare(rows, [candidate(101, "、".join(names))])
        c = d["ranked"][0]
        self.assertEqual(len(c["person_parts"]), 8)
        self.assertEqual(len(c["why_b"]), 6)
        # v3: the strongest 3 people, plus the mean of the kind-of-show tags
        # (here 「オリジナル」, shared by the ◎ records that have credits).
        kinds = c["why_kind"]
        self.assertEqual([k[1:3] for k in kinds], [["#原作", "オリジナル"]])
        self.assertAlmostEqual(c["b"], sum(p[0] for p in c["person_parts"][:3]) + kinds[0][0])

    def test_no_history_does_not_inherit_owner_ranking(self):
        d = self.prepare([], [candidate(101, "俳優甲")])
        d = UR.finish(d, top=15, weights={})
        self.assertEqual(d["recommend"], [])
        self.assertEqual(len(d["unscored"]), 1)

    def test_all_negative_history_has_no_prior_only_recommendations(self):
        rows = [{"key": "one", "verdict": "×", "people": [("出演", "俳優甲")]}]
        d = UR.finish(self.prepare(rows, [candidate(101, "俳優甲")]), top=15, weights={})
        self.assertEqual(d["recommend"], [])

    def test_tours_share_one_slot_and_preserve_theaters(self):
        rows = [{"key": "one", "verdict": "◎", "people": [("出演", "俳優甲")]},
                {"key": "two", "verdict": "×", "people": []}]
        cands = [candidate(101, "俳優甲", title="同じツアー"),
                 candidate(102, "俳優甲", title="同じツアー")]
        cands[1]["pref"] = "大阪府"
        d = UR.finish(self.prepare(rows, cands), top=15, weights={})
        self.assertEqual(len(d["recommend"]), 1)
        rows, n = APP.RR.filtered(d, ["大阪府"])
        self.assertEqual(n, 1)
        self.assertEqual(rows[0]["stage_id"], "102")



class KindOfShowTests(unittest.TestCase):
    """person-ordinal-v3: kinds of show (form, source, venue) from the title,
    credits and venue; a user who rates musicals higher than usual gets
    upcoming musicals raised, even with no shared people."""

    def test_genres(self):
        """起案者の指示 2026-10-16「おすすめ理由に2.5次元として出してほしい」「宝塚は宝塚ってジャンルかな」"""
        G = UR.genres
        self.assertEqual(G("勝者と敗者", "劇団「ハイキュー!!」製作委員会", "古舘春一 「ハイキュー!!」（集英社ジャンプコミックス刊）"), ["2.5次元"])
        self.assertEqual(G("舞台『刀剣乱舞』陽伝", "舞台『刀剣乱舞』製作委員会"), ["2.5次元"])
        self.assertEqual(G("あんさんぶるスターズ!!THE STAGE", "あんステ製作委員会"), ["2.5次元"])
        self.assertEqual(G("舞台「呪術廻戦」-渋谷事変", "舞台「呪術廻戦」製作委員会"), ["2.5次元"])
        # 漫画が原作でも宝塚は宝塚。スタッフ欄に宝塚歌劇団とあるだけの公演は宝塚にしない（主催だけを見る）
        self.assertEqual(G("ポーの一族", "宝塚歌劇団", "萩尾望都「ポーの一族」（小学館フラワーコミックス）"), ["宝塚"])
        # 製作委員会でも、戯曲名だけの題名・ふつうの題名は 2.5次元にしない
        self.assertEqual(G("「飛龍伝」「幕末純情伝」", "つかこうへい革命ミュージカル製作委員会"), [])
        self.assertEqual(G("HUNGER", "HUNGER製作委員会"), [])
        self.assertEqual(G("サボテンの微笑み", "キューブ"), [])
        self.assertIn(("#ジャンル", "宝塚"), UR.stage_tags("エリザベート", [], [("演出", "甲")], group="宝塚歌劇団"))

    def test_forms_2026_10_19(self):
        """形式の分け方（起案者の指示 2026-10-19「その分け方で移行」）: 能・狂言・歌舞伎・文楽・落語・寄席・バレエ・ダンス・オペラ・
        お笑い・ミュージカルを分け、どれにも当たらなければ演劇（札なし）。題名で決まらなければ劇場・主催の名前、オペラ劇場は役職で見る。"""
        F = UR.form_of
        self.assertEqual(F("二〇二六年 正月公演", ["セルリアンタワー能楽堂"]), "能・狂言")
        self.assertEqual(F("能を知る会"), "能・狂言")
        self.assertEqual(F("可能性の舞台"), "")
        self.assertEqual(F("四月大歌舞伎", ["歌舞伎座"]), "歌舞伎")
        self.assertEqual(F("華氏マイナス320°", ["大阪新歌舞伎座"]), "")
        self.assertEqual(F("令和8年4月文楽公演"), "文楽")
        self.assertEqual(F("令和8年5月上方演芸特選会", ["国立文楽劇場・小ホール"]), "落語・寄席")
        self.assertEqual(F("桂宮治 独演会"), "落語・寄席")
        self.assertEqual(F("声が走る。浪曲が走る。"), "落語・寄席")
        self.assertEqual(F("ルル", ["新国立劇場 オペラ劇場"], {"指揮", "演出"}), "オペラ")
        self.assertEqual(F("ライモンダ", ["新国立劇場 オペラ劇場"], {"指揮", "振付"}), "バレエ")
        self.assertEqual(F("新「コッペリア」", ["東京バレエ団"]), "バレエ")
        self.assertEqual(F("エリザベート", ["宝塚大劇場", "宝塚歌劇団"]), "")
        self.assertEqual(F("漫才ライブ"), "お笑い")
        self.assertIn(("#形式", "能・狂言"), UR.stage_tags("青山能〈4月〉1部", ["銕仙会能楽研修所"], []))

    def test_student_theatre(self):
        """大学演劇・高校演劇（起案者の指示 2026-10-19「大学演劇とか高校演劇もあるな」）はジャンル。主催の名前で見る。"""
        G = UR.genres
        self.assertEqual(G("BLOOM", "明治大学ミュージカル研究会"), ["大学演劇"])
        self.assertEqual(G("夏の夜の夢", "東京都立総合芸術高等学校舞台表現科"), ["高校演劇"])
        self.assertEqual(G("高校演劇[小劇場]桜まつり", "渡辺源四郎商店"), ["高校演劇"])
        self.assertEqual(G("琉球芸能 特別公演", "京都芸術大学 舞台芸術研究センター"), [])
        self.assertEqual(G("大学生の恋", "劇団X"), [])
        tags = UR.stage_tags("BLOOM", [], [("出演", "甲")], group="明治大学ミュージカル研究会")
        self.assertIn(("#形式", "ミュージカル"), tags)
        self.assertIn(("#ジャンル", "大学演劇"), tags)
        self.assertIn("#ジャンル", UR.CONTENT_AXES)

    def test_tags_from_title_credits_and_venue(self):
        T = UR.stage_tags
        # 劇場は種類にしない（起案者 2026-10-17「ただ会場で出てくるのは不要」）
        self.assertEqual(T("ミュージカル『夏』", ["劇場A"], [("出演", "甲")]),
                         [("#原作", "オリジナル"), ("#形式", "ミュージカル")])
        self.assertEqual(T("夏の夜", [], [("翻訳", "乙"), ("音楽", "丙")]),
                         [("#原作", "オリジナル"), ("#形式", "音楽劇"), ("#翻訳", "翻訳劇")])
        # 原作の種類は欄の書き添えから読む。読めないときは種類を付けない（「原作もの」とは言わない。起案者 2026-10-16）
        self.assertEqual(T("朗読劇『夜』", [], [("原作", "丁")]), [("#形式", "朗読")])
        self.assertEqual(T("朗読劇『夜』", [], [("原作", "丁")], source="丁『夜』（集英社ジャンプコミックス刊）"),
                         [("#ジャンル", "2.5次元"), ("#原作", "漫画原作"), ("#形式", "朗読")])
        self.assertEqual(UR.source_kinds("映画『髪結いの亭主』（監督＝パトリス・ルコント）"), ["映画原作"])
        self.assertEqual(UR.source_kinds("池井戸 潤「民王」（文春文庫／角川文庫）"), ["小説原作"])
        self.assertEqual(UR.source_text({"スタッフ": "振付原案：甲\n原作：乙「夜」（講談社文庫）"}), "乙「夜」（講談社文庫）")
        self.assertEqual(T("", [], []), [])          # nothing known, nothing guessed

    def test_kind_preference_reaches_shows_without_shared_people(self):
        rows = [{"key": f"m{i}", "verdict": "◎", "title": f"ミュージカル{i}", "people": [("出演", f"甲{i}")]}
                for i in range(3)]
        rows += [{"key": f"p{i}", "verdict": "×", "title": f"芝居{i}", "people": [("出演", f"乙{i}")]}
                 for i in range(3)]
        cands = [dict(candidate(201, "知らない人"), title="ミュージカル新作"),
                 dict(candidate(202, "別の知らない人"), title="芝居の新作")]
        d = UR.finish(ScoringTests.prepare(self, rows, cands), top=15, weights={})
        self.assertEqual([c["stage_id"] for c in d["recommend"]], ["201"])
        self.assertEqual(d["recommend"][0]["why_kind"][-1][1:3], ["#形式", "ミュージカル"])

    def test_rating_order_not_equal_steps(self):
        # Only the order within the user's ratings matters: ◎ > ○ > × and
        # 4/5 > 3/5 > 1/5 give the same values.
        a = [{"key": "1", "verdict": "◎", "people": [("出演", "甲")]},
             {"key": "2", "verdict": "○", "people": [("出演", "乙")]},
             {"key": "3", "verdict": "×", "people": [("出演", "丙")]}]
        b = [dict(r, verdict=v) for r, v in zip(a, ("4/5", "3/5", "1/5"))]
        self.assertEqual(UR.person_values(a)[0], UR.person_values(b)[0])


class FavouriteSeedTests(unittest.TestCase):
    """Favourites as fading pseudo ratings (q-favourites-seed)."""

    seeds = [{"stage_id": "s1", "people": [["出演", "推し"], ["出演", "共演者"], ["#形式", "ミュージカル"]]}]

    def test_seed_reaches_co_workers_and_kinds_not_the_favourite(self):
        values, _ = UR.person_values([], self.seeds, {"推し"})
        self.assertNotIn(("出演", "推し"), values)
        n, v = values[("出演", "共演者")]
        self.assertEqual(n, 0)                       # n counts the user's own ratings only
        # お気に入りの種は FAV_SEED_W 倍の重さ（起案者の指示 2026-10-18「お気に入り＞興味あり」）
        W = UR.FAV_SEED_W
        self.assertAlmostEqual(v, W * UR.SEED_Z / (W + 3))
        self.assertGreater(values[("#形式", "ミュージカル")][1], 0)

    def test_seed_fades_as_ratings_come_in(self):
        other = [{"key": f"r{i}", "verdict": "○", "people": [["出演", f"別人{i}"]]} for i in range(9)]
        early = UR.person_values([], self.seeds, {"推し"})[0][("出演", "共演者")][1]
        later = UR.person_values(other, self.seeds, {"推し"})[0][("出演", "共演者")][1]
        W = UR.FAV_SEED_W
        self.assertAlmostEqual(later, (3 / 12) * W * UR.SEED_Z / ((3 / 12) * W + 3))
        # 評価 9 件で、種の値は (3/12·W + 3) / (3/12·(W + 3)) 分の 1 に薄まる（W = 1 で 3.25、W = 2 で 2.8）
        self.assertAlmostEqual(early / later, ((3 / 12) * W + 3) / ((3 / 12) * (W + 3)))
        self.assertLess(later, early / 2.5)

    def test_no_seeds_changes_nothing(self):
        rated = [{"key": "a", "verdict": "◎", "people": [["出演", "甲"]]},
                 {"key": "b", "verdict": "×", "people": [["出演", "甲"], ["出演", "乙"]]}]
        self.assertEqual(UR.person_values(rated)[0], UR.person_values(rated, [], set())[0])


class AspectTests(unittest.TestCase):
    """気になった所: a low rating lands on the roles the aspects point at."""

    def rated(self, aspects):
        people = [["出演", "役者"], ["演出", "演出家"], ["脚本", "作家"], ["#値段", "1万3千円以上"], ["#会場", "大劇場"]]
        low = {"key": "low", "verdict": "×", "people": people, "aspects": aspects}
        others = [{"key": f"o{i}", "verdict": "○", "people": [["出演", f"別人{i}"]]} for i in range(3)]
        return UR.person_values([low] + others)[0]

    def test_no_aspect_lands_on_everyone(self):
        v = self.rated([])
        self.assertLess(v[("出演", "役者")][1], 0)
        self.assertEqual(v[("出演", "役者")][1], v[("演出", "演出家")][1])

    def test_price_lowers_the_price_band_not_the_people(self):
        v = self.rated(["price"])
        self.assertEqual(v[("出演", "役者")][1], 0)
        self.assertEqual(v[("脚本", "作家")][1], 0)
        self.assertLess(v[("#値段", "1万3千円以上")][1], 0)
        self.assertEqual(v[("#会場", "大劇場")][1], 0)

    def test_acting_lands_on_the_cast_and_only_slightly_on_the_director(self):
        v = self.rated(["acting"])
        cast, director = v[("出演", "役者")][1], v[("演出", "演出家")][1]
        self.assertAlmostEqual(director, 0.2 * cast)
        self.assertEqual(v[("脚本", "作家")][1], 0)

    def test_several_aspects_take_the_largest_share(self):
        v = self.rated(["story", "acting"])
        self.assertAlmostEqual(v[("演出", "演出家")][1], 0.5 * v[("脚本", "作家")][1])
        self.assertEqual(v[("出演", "役者")][1], v[("脚本", "作家")][1])

    def test_a_high_rating_is_not_redistributed(self):
        hi = {"key": "hi", "verdict": "◎", "people": [["出演", "役者"]], "aspects": ["price"]}
        lo = {"key": "lo", "verdict": "×", "people": [["出演", "別人"]]}
        self.assertGreater(UR.person_values([hi, lo])[0][("出演", "役者")][1], 0)

    def test_unknown_codes_are_ignored_and_text_is_accepted(self):
        self.assertEqual(UR.aspect_codes("venue,xx,price"), ["price", "venue"])

    def rated_high(self, aspects):
        people = [["出演", "役者"], ["演出", "演出家"], ["脚本", "作家"]]
        high = {"key": "high", "verdict": "◎", "people": people, "aspects": aspects}
        others = [{"key": f"o{i}", "verdict": "△", "people": [["出演", f"別人{i}"]]} for i in range(3)]
        return UR.person_values([high] + others)[0]

    def test_a_high_rating_lands_on_what_was_good(self):
        v = self.rated_high(["+acting", "story"])
        cast, director, writer = v[("出演", "役者")][1], v[("演出", "演出家")][1], v[("脚本", "作家")][1]
        self.assertGreater(cast, 0)
        self.assertEqual(writer, 0)                         # good acting, troubled story
        self.assertAlmostEqual(director, cast * 0.2 * (1 - 0.5))

    def test_a_low_rating_spares_what_was_good(self):
        v = self.rated(["story", "+acting"])
        writer = v[("脚本", "作家")][1]
        self.assertLess(writer, 0)
        self.assertEqual(v[("出演", "役者")][1], 0)
        self.assertAlmostEqual(v[("演出", "演出家")][1], writer * 0.5 * (1 - 0.2))

    def test_good_and_trouble_codes_are_read_apart(self):
        self.assertEqual(UR.parse_aspects("price,+acting,+xx"), (["price"], ["acting"]))
        self.assertEqual(UR.aspect_codes(["+price"]), [])

    # 5 段階と「この作品には無い」（起案者の指示 2026-10-18「最低限5段階くらいほしい」「なかったときは✕で要素を消せるように」）
    def test_five_levels_and_not_in_this_production_are_read(self):
        self.assertEqual(UR.aspect_levels("++acting,+story,price,--venue,~music,xx,~xx"),
                         {"acting": 2, "story": 1, "price": -1, "venue": -2, "music": 0})
        self.assertEqual(UR.parse_aspects("++acting,--story,~music"), (["story"], ["acting"]))
        # the 3-level text (良かった・気になった) reads as やや好き 1・やや好みではない −1
        self.assertEqual(UR.aspect_levels("price,+acting"), {"price": -1, "acting": 1})

    def test_not_in_this_production_is_left_out(self):
        self.assertEqual(self.rated(["~music", "~dance"]), self.rated([]))
        self.assertEqual(self.rated(["acting", "~music"]), self.rated(["acting"]))

    # 好き・好みではない（±2）は、その項目の役職の人に ASPECT_STRONG（1.5）倍効く（起案者の指示 2026-10-18「詳細評価の
    # とてもを推薦の効き方も強めてほしい。該当する人をちょっと重くするとか」）。±1 だけの記録は前と同じ
    def test_a_strong_mark_weighs_its_people_a_little_more(self):
        self.assertEqual(UR.ASPECT_STRONG, 1.5)
        plain, strong = self.rated(["acting"]), self.rated(["--acting"])
        self.assertAlmostEqual(strong[("出演", "役者")][1], 1.5 * plain[("出演", "役者")][1])
        self.assertAlmostEqual(strong[("演出", "演出家")][1], 1.5 * plain[("演出", "演出家")][1])
        self.assertEqual(strong[("脚本", "作家")][1], 0)
        hi_plain, hi_strong = self.rated_high(["+acting"]), self.rated_high(["++acting"])
        self.assertAlmostEqual(hi_strong[("出演", "役者")][1], 1.5 * hi_plain[("出演", "役者")][1])
        # beside a ±1 mark, the ±2 one's people get more
        v = self.rated(["--story", "acting"])
        self.assertAlmostEqual(v[("出演", "役者")][1] * 1.5, v[("脚本", "作家")][1])

    def test_a_strong_mark_on_the_other_side_takes_away_more_but_never_flips(self):
        v = self.rated_high(["+acting", "--story"])
        cast, director = v[("出演", "役者")][1], v[("演出", "演出家")][1]
        self.assertAlmostEqual(director, cast * 0.2 * (1 - 0.5 * 1.5))
        # 演出・振付: 1.0 from direction (main) and 1.5 from a strong dance mark (other) -> nothing, not below 0
        self.assertEqual(UR.aspect_share(["direction"], ["dance"], "演出・振付", False, {"direction": -1, "dance": 2}), 0.0)

    def test_plus_minus_one_records_score_as_before(self):
        # the share of every ±1 record is the share without levels (the 3-level rule)
        for t, g in ((["story"], ["acting"]), (["price", "venue"], []), ([], ["music", "dance"])):
            lv = {**{c: -1 for c in t}, **{c: 1 for c in g}}
            for role in ("出演", "演出", "脚本", "振付", "#値段"):
                for pos in (True, False):
                    self.assertEqual(UR.aspect_share(t, g, role, pos, lv), UR.aspect_share(t, g, role, pos))

    def test_saved_codes_match_the_recommender(self):
        import rate_performances as R
        self.assertEqual(list(R.ASPECT_CODES), list(UR.ASPECTS))
        self.assertEqual(R.clean_aspects(["venue", "price"]), "price,venue")
        self.assertEqual(R.clean_aspects("+acting,venue"), "venue,+acting")
        self.assertEqual(R.clean_aspects(["~dance", "++acting", "price", "--story", "+venue"]),
                         "price,+venue,--story,++acting,~dance")
        for bad in (["もやもや"], ["+もやもや"], ["acting", "+acting"], ["++acting", "~acting"], ["---acting"], ["+++acting"]):
            with self.assertRaises(ValueError):
                R.clean_aspects(bad)

    def test_saving_a_rating_keeps_aspects_unless_given(self):
        import sqlite3
        import rate_performances as R
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        R._widen_attendance_key(con)
        con.executescript(R.SCHEMA)
        for step in (R._add_stage_id, R._add_venue, R._add_time, R._scope_by_user, R._add_input_sources, R._add_aspects):
            step(con)
        work = {"work_key": "k", "title": "t", "first_date": "2026-01-01", "last_date": "2026-01-01",
                "times": 1, "bucket": "past"}
        R.save_work(con, work, {"verdict": "△", "aspects": ["venue", "price"]}, user_id="u")
        R.save_work(con, work, {"verdict": "×"}, user_id="u")
        self.assertEqual(R.read_works(con, user_id="u")["k"]["aspects"], "price,venue")
        R.save_work(con, work, {"verdict": "×", "aspects": []}, user_id="u")
        self.assertEqual(R.read_works(con, user_id="u")["k"]["aspects"], "")

    def test_price_band(self):
        self.assertEqual(UR.price_band(["一般 7,800円 / 学生 4,000円"]), "5千〜9千円")
        self.assertEqual(UR.price_band(["S席 13,000円"]), "1万3千円以上")
        self.assertEqual(UR.price_band(["無料", ""]), "")
        # 料金帯は理由にも点数にも使わない（起案者の指示 2026-10-16）
        self.assertFalse([t for t in UR.stage_tags("舞台", [], [], ["3,500円"]) if t[0] == "#値段"])


if __name__ == "__main__":
    unittest.main()
