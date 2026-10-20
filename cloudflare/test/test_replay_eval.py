"""tools/review/replay_eval.py: 控えからの集計（real-data-eval-plan §8）。"""
import importlib.util
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import replay_eval  # noqa: E402

SQL = """
CREATE TABLE reaction (user_id TEXT, label TEXT, stage_id TEXT, interest INTEGER, owned INTEGER, note TEXT,
  source TEXT, updated_at TEXT, rank INTEGER, score REAL, ver TEXT, arm TEXT);
CREATE TABLE app_setting (user_id TEXT, key TEXT, value TEXT, updated_at TEXT);
CREATE TABLE rec_shown (user_id TEXT, label TEXT, screen TEXT, ids TEXT, ver TEXT, updated_at TEXT);
"""


def rows(uid, answers, source="reminder"):
    return "".join(f"INSERT INTO reaction VALUES('{uid}','2026-10-17','{i}',{a},0,'感想','{source}','x',{i},{s},'v',NULL);\n"
                   for i, (a, s) in enumerate(answers))


class ReplayEval(unittest.TestCase):
    def run_on(self, sql, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
            f.write(SQL + sql)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                replay_eval.main([f.name, *args])
        finally:
            os.unlink(f.name)
        return json.loads(buf.getvalue())

    def test_logged_auc_leaves_out_opted_out_users_and_shows_the_owner_apart(self):
        good = [(1, 0.9), (1, 0.8), (0, 0.1), (0, 0.2)]
        sql = rows("a", good) + rows("b", good) + rows("me", [(1, 0.1), (0, 0.9), (0, 0.8)]) + rows("out", good)
        sql += "INSERT INTO app_setting VALUES('out','analysis_optout','1','x');\n"
        r = self.run_on(sql, "logged", "--owner", "me", "--min-users", "2")["reminder"]
        self.assertEqual(r["users"], 2)
        self.assertEqual(r["median_auc"], 1.0)
        self.assertEqual(r["owner_auc"], 0.0)
        self.assertAlmostEqual(r["p_sign"], 0.25)

    def test_no_verdict_before_enough_users(self):
        r = self.run_on(rows("a", [(1, 0.9), (0, 0.1), (0, 0.2)]), "logged", "--min-users", "2")["reminder"]
        self.assertTrue(str(r["p_sign"]).startswith("まだ"))

    def test_counts(self):
        sql = rows("a", [(1, 0.9), (0, 0.1)], "screen") + "INSERT INTO rec_shown VALUES('a','2026-10-17','recommend','[]',NULL,'x');\n"
        c = self.run_on(sql, "counts")
        self.assertEqual((c["users"], c["answers"], c["answers_with_score"], c["answers_reminder"], c["shown_rows"]), (1, 2, 2, 0, 1))


def index_sql(path, affil=False):
    """小さな索引: 終わった公演 301（俳優甲）・302（俳優乙）と、これからの 311（俳優甲）・312（俳優乙）・313（俳優丁）。"""
    spec = importlib.util.spec_from_file_location("build_recommend_index", ROOT / "cloudflare" / "scripts" / "build_recommend_index.py")
    BI = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(BI)
    import app as APP  # noqa: E402
    import user_recommender as UR  # noqa: E402
    stage = lambda sid, period, who: {"stage_id": sid, "title": f"舞台{sid}", "group": f"劇団{sid}", "theater": "劇場A",
                                      "pref": "東京都", "period": period, "fields": {"出演": who}}
    cands = [stage("301", "2026/08/01~2026/08/10", "俳優甲"), stage("302", "2026/08/11~2026/08/20", "俳優乙"),
             stage("311", "2026/11/01~2026/11/10", "俳優甲"), stage("312", "2026/11/11~2026/11/20", "俳優乙"),
             stage("313", "2026/11/21~2026/11/30", "俳優丁")]
    if affil:
        cands[0]["fields"]["出演"] = "俳優甲（劇団X）"
        cands.append(stage("314", "2026/11/21~2026/11/30", "俳優戊（劇団X）"))
    pool = UR.candidate_pool({}, cands)
    index = BI.build_index(pool, {c["stage_id"]: c["fields"] for c in cands}, APP.group_of)
    path.write_text("\n".join(BI.to_sql(index, BI.version_of(index))) + "\n", encoding="utf-8")


def backup_sql(path, later_answers, *, rated_at="2026-09-01 10:00:00"):
    """控えの形（全部の migrations の表 ＋ 記録）を SQL の文に書き出す。"""
    db = sqlite3.connect(":memory:")
    for f in sorted((ROOT / "cloudflare" / "migrations").glob("*.sql")):
        db.executescript(f.read_text(encoding="utf-8"))
    db.execute("INSERT INTO users(id,recovery_hash,created_at) VALUES('u','h',1)")
    for key, sid, verdict in (("w1", "301", "◎"), ("w2", "302", "×")):
        db.execute("INSERT INTO works(user_id,work_key,title,first_date,last_date,verdict,updated_at,stage_id) VALUES('u',?,?,?,?,?,?,?)",
                   (key, f"舞台{sid}", "2026-08-05", "2026-08-05", verdict, rated_at, sid))
    for sid, interest, at in later_answers:
        db.execute("INSERT INTO reaction(user_id,label,stage_id,interest,owned,source,updated_at) VALUES('u',?,?,?,0,'reminder',?)",
                   (at[:10], sid, interest, at))
    path.write_text("\n".join(db.iterdump()) + "\n", encoding="utf-8")
    db.close()


class Replay(unittest.TestCase):
    # 最初の答え（10/5、索引に無い公演）の日が最初の区切り。10/10 の 3 件が、その後 7 日の答え
    ANSWERS = [("399", 0, "2026-10-05T01:00:00Z"),
               ("311", 1, "2026-10-10T01:00:00Z"), ("312", 0, "2026-10-10T01:01:00Z"), ("313", 0, "2026-10-10T01:02:00Z")]

    def run_replay(self, answers, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            idx, bk = Path(tmp) / "index.sql", Path(tmp) / "backup.sql"
            index_sql(idx)
            backup_sql(bk, answers, **kw)
            return replay_eval.replay(str(bk), idx, [])

    def test_one_user_is_enough_and_later_answers_do_not_leak(self):
        # 日 t（10/5）までの記録は ◎ 俳優甲・× 俳優乙だけ。10/10 の答え（311 興味あり）は計算に入らないので、
        # 311 は候補に残って 1 位、312・313 は圏外。正例が上なので AUC 1.0
        r = self.run_replay(self.ANSWERS)
        self.assertEqual(r["origins"], 1)
        self.assertEqual(r["answers_ranked_share"], round(1 / 3, 3))
        main = r["reminder"]
        self.assertEqual((main["users"], main["median_auc"]), (1, 1.0))
        self.assertAlmostEqual(main["p_sign_H1"], 0.5)
        self.assertEqual(set(main["H5"]), set(replay_eval.ABLATIONS))
        self.assertEqual(set(main["H6"]), set(replay_eval.TRIALS))
        self.assertEqual(r["gate_affil"]["users"], 0, "five ratings or fewer: the hidden check does not run")
        self.assertEqual(r["other"]["users"], 0)
        self.assertEqual(r["per_origin"], [{"t": "2026-10-05", "users": 1, "answers": 3, "with_ratings": 1, "with_recommendations": 1}])

    def test_trying_the_affiliation_ranks_a_member_of_a_liked_troupe(self):
        # dec-affil-reco: ◎ を付けた 301 の俳優甲は劇団X。これからの 314 の俳優戊も劇団X なので、所属を効かせると
        # 314 が候補に入り（今の計算では圏外）、後で興味ありを押した 314 が、押さなかった 313 より上になる
        with tempfile.TemporaryDirectory() as tmp:
            idx, bk = Path(tmp) / "index.sql", Path(tmp) / "backup.sql"
            index_sql(idx, affil=True)
            backup_sql(bk, [("399", 0, "2026-10-05T01:00:00Z"), ("314", 1, "2026-10-10T01:00:00Z"),
                            ("313", 0, "2026-10-10T01:01:00Z"), ("312", 0, "2026-10-10T01:02:00Z")])
            r = replay_eval.replay(str(bk), idx, [])
        h = r["reminder"]["H6"]["affil"]
        self.assertGreater(h["median_diff"], 0)
        self.assertEqual((h["users_better"], h["users_worse"]), (1, 0))

    def test_ratings_made_after_the_origin_are_cut(self):
        # 評価が答えより後に付いたなら、日 t には評価が無い: 何も出ず、どれも圏外で AUC 0.5
        r = self.run_replay(self.ANSWERS, rated_at="2026-10-12 10:00:00")
        self.assertEqual(r["reminder"]["median_auc"], 0.5)
        self.assertEqual(r["answers_ranked_share"], 0.0)

    def test_owner_is_shown_apart(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx, bk = Path(tmp) / "index.sql", Path(tmp) / "backup.sql"
            index_sql(idx)
            backup_sql(bk, self.ANSWERS)
            r = replay_eval.replay(str(bk), idx, [], owner="u")
        self.assertEqual(r["reminder"]["users"], 0)
        self.assertEqual(r["reminder"]["owner"]["auc"], 1.0)

    def test_ablations_match_the_worker(self):
        js = (ROOT / "cloudflare" / "src" / "screens" / "recommend.js").read_text(encoding="utf-8")
        listed = re.search(r"REPLAY_ABLATIONS = \[([^\]]*)\]", js).group(1)
        self.assertEqual(tuple(re.findall(r"'(\w+)'", listed)), replay_eval.ABLATIONS)

    def test_wilcoxon_and_holm(self):
        self.assertAlmostEqual(replay_eval.wilcoxon_p([0.1, 0.2, 0.3]), 1 / 8)
        self.assertEqual(replay_eval.wilcoxon_p([0, 0]), 1.0)
        self.assertAlmostEqual(replay_eval.wilcoxon_p([0.1, -0.1]), 0.75)
        self.assertEqual(replay_eval.holm({"a": 0.01, "b": 0.04}), {"a": 0.02, "b": 0.04})

    def test_jst_day(self):
        self.assertEqual(replay_eval.jst_day("2026-10-09T16:00:00Z"), "2026-10-10")
        self.assertEqual(replay_eval.jst_day("2026-10-09 23:59:00"), "2026-10-09")
        self.assertEqual(replay_eval.jst_day(1760000000), "2025-10-09")


if __name__ == "__main__":
    unittest.main()


class Materials(unittest.TestCase):
    def test_counts_what_the_ratings_can_learn_from(self):
        # 索引の公演 2 件（◎・×）に、つながっていない評価・過去の公演（名前だけ）・評価なし・観た日が先を足す
        with tempfile.TemporaryDirectory() as tmp:
            idx, bk, past = Path(tmp) / "index.sql", Path(tmp) / "backup.sql", Path(tmp) / "past.sql"
            index_sql(idx)
            backup_sql(bk, Replay.ANSWERS)
            extra = sqlite3.connect(":memory:")
            extra.executescript(bk.read_text(encoding="utf-8"))
            for key, sid, verdict, first, note in (("w3", "", "○", "2026-07-01", ""), ("w4", "901", "4/5", "2026-07-02", "家族の話が好きだった"),
                                                   ("w5", "301", "", "2026-07-03", ""), ("w6", "301", "◎", "2099-01-01", "")):
                extra.execute("INSERT INTO works(user_id,work_key,title,first_date,last_date,verdict,updated_at,stage_id,note_impression) "
                              "VALUES('u',?,?,?,?,?,'2026-09-01 10:00:00',?,?)", (key, key, first, first, verdict, sid, note))
            bk.write_text("\n".join(extra.iterdump()) + "\n", encoding="utf-8")
            extra.close()
            past.write_text("INSERT INTO past_stage(stage_id,title,tkey,people) VALUES('901','昔の舞台','昔の舞台','[[\"出演\", \"俳優戊\"]]');\n", encoding="utf-8")
            m = replay_eval.materials(str(bk), idx, [past], "2026-10-18")
        self.assertEqual(m["records"], 6)
        self.assertEqual(m["rated"], 5)
        self.assertEqual((m["rated_future"], m["rated_unlinked"]), (1, 1))
        self.assertEqual((m["linked_index"], m["linked_past"], m.get("linked_missing", 0)), (2, 1, 0))
        # 種類の言葉は索引の公演（301・302）だけ。過去の公演は名前だけなので、感想はあっても好みの材料にならない
        self.assertEqual((m["with_names"], m.get("with_kinds", 0), m["with_note"], m.get("with_note_and_kinds", 0)), (3, 2, 1, 0))
