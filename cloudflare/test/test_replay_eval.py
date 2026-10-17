"""tools/review/replay_eval.py: 控えからの集計（real-data-eval-plan §8）。"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "review"))
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
        r = self.run_on(rows("a", [(1, 0.9), (0, 0.1), (0, 0.2)]), "logged")["reminder"]
        self.assertTrue(str(r["p_sign"]).startswith("まだ"))

    def test_counts(self):
        sql = rows("a", [(1, 0.9), (0, 0.1)], "screen") + "INSERT INTO rec_shown VALUES('a','2026-10-17','recommend','[]',NULL,'x');\n"
        c = self.run_on(sql, "counts")
        self.assertEqual((c["users"], c["answers"], c["answers_with_score"], c["answers_reminder"], c["shown_rows"]), (1, 2, 2, 0, 1))


if __name__ == "__main__":
    unittest.main()
