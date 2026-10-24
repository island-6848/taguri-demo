"""cloudflare/scripts/replay_job.py: Actions の中の再生（D1 と wrangler は差し替える）。"""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
import test_replay_eval as T  # noqa: E402
import replay_job as RJ  # noqa: E402


class ReplayJob(unittest.TestCase):
    def test_summary_has_only_aggregates_and_the_records_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            data = tmp / "data"
            (data / "past").mkdir(parents=True)
            (data / "past" / "stages.jsonl").write_text(json.dumps(
                {"stage_id": "201", "title": "昔の舞台", "start": "2020-01-01", "end": "2020-01-05", "fields": {"出演": "俳優甲"}},
                ensure_ascii=False) + "\n", encoding="utf-8")
            seen = []

            def export(path):
                T.backup_sql(path, T.Replay.ANSWERS)
                seen.append(path)
                return 1

            summary = tmp / "summary.md"
            with mock.patch.object(RJ, "export_records", export), \
                    mock.patch.object(RJ, "build_index", T.index_sql), \
                    mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}), redirect_stdout(io.StringIO()):
                self.assertEqual(RJ.main(["--data", str(data)]), 0)
            text = summary.read_text(encoding="utf-8")
            self.assertIn("推薦の再生", text)
            self.assertIn("AUC の中央値 1.000", text)
            self.assertIn("並べ直し", text)
            self.assertIn("所属（劇団）から推し量る", text)
            self.assertIn("裏の答え合わせ: 所属（劇団）から推し量る（測るだけ）", text)
            # H3（#114）と、索引の載った日（#72。控えが無いので分からないと出す）
            self.assertIn("観る前の点と、観たあとの評価（H3・#114）", text)
            self.assertIn("控え始めに載っていた公演は外せていない", text)
            # 利用者の ID・公演の番号は出さない。書き出した記録は残らない
            self.assertNotIn("'u'", text)
            self.assertNotIn("311", text)
            self.assertFalse(seen[0].exists())

    def test_past_stages_come_from_the_working_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "past").mkdir()
            (data / "past" / "stages.jsonl").write_text(
                '{"stage_id": "201", "title": "昔の舞台", "fields": {"出演": "俳優甲"}}\n{"stage_id": "", "title": "x"}\n', encoding="utf-8")
            out = data / "past.sql"
            self.assertEqual(RJ.past_sql(data, out), 1)
            self.assertIn("INSERT OR REPLACE INTO past_stage", out.read_text(encoding="utf-8"))

    def test_too_many_rows_are_not_read(self):
        with mock.patch.object(RJ.BK, "remote_tables", lambda db: ["works"]), \
                mock.patch.object(RJ.BK, "remote_counts", lambda db, t: {"works": RJ.REPLAY_MAX_ROWS + 1}), \
                mock.patch.object(RJ.BK, "wrangler", side_effect=AssertionError("読まない")):
            with self.assertRaises(SystemExit):
                RJ.export_records(Path("x.sql"))


if __name__ == "__main__":
    unittest.main()
