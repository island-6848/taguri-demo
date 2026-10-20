"""deliver_past: only new lines are sent, the budget caps a day, rows load into past_stage."""
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / 'scripts' / 'deliver_past.py'
MIGRATION = HERE.parent / 'migrations' / '0012.sql'
SYNOPSIS = HERE.parent / 'migrations' / '0036.sql'

ROWS = [
    {"stage_id": "30", "title": "夜の果て", "start": "2024-03-01", "end": "2024-03-10", "theater": "本多劇場",
     "group": "劇団あおば", "pref": "東京都", "fields": {"出演": "山田太郎、鈴木花子", "演出": "佐藤一郎"}},
    {"stage_id": "20", "title": "O'Neill の夜\u2028第二部", "start": "2022-07-01", "end": "2022-07-03", "fields": {}},
]


def run(*args):
    return json.loads(subprocess.run([sys.executable, str(SCRIPT), *args], check=True,
                                     capture_output=True, text=True).stdout.strip().splitlines()[-1]) \
        if args[0] == 'build' else subprocess.run([sys.executable, str(SCRIPT), *args], check=True)


class DeliverPastTest(unittest.TestCase):
    def test_incremental_upload(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / 'past').mkdir()
            (d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in ROWS) + '\n',
                                                     encoding='utf-8')
            con = sqlite3.connect(d / 'd1.db')
            con.executescript('CREATE TABLE works(user_id TEXT, work_key TEXT, title TEXT, first_date TEXT, stage_id TEXT);')
            con.executescript(MIGRATION.read_text(encoding='utf-8'))
            con.executescript(SYNOPSIS.read_text(encoding='utf-8'))
            first = run('build', '--data', t, '--out', str(d / 'out'), '--budget', '3')   # one row: the row, its key index and the tkey index
            self.assertEqual((first['rows'], first['left']), (1, 1))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            # Not committed yet: the same row is built again (a failed upload is retried).
            self.assertEqual(run('build', '--data', t, '--out', str(d / 'out'), '--budget', '3')['delivered_before'], 0)
            run('commit', '--data', t, '--out', str(d / 'out'))
            second = run('build', '--data', t, '--out', str(d / 'out'))
            self.assertEqual((second['rows'], second['left'], second['delivered_before']), (1, 0, 1))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            got = dict(con.execute('SELECT stage_id, tkey FROM past_stage').fetchall())
            self.assertEqual(got, {'30': '夜の果て', '20': 'oneillの夜第二部'})
            people = json.loads(con.execute("SELECT people FROM past_stage WHERE stage_id='30'").fetchone()[0])
            self.assertIn(['出演', '山田太郎'], people)
            cols = [r[1] for r in con.execute('PRAGMA table_info(works)')]
            self.assertIn('stage_auto', cols)
            self.assertIn('stage_off', cols)


    def test_kind_tags_and_resend_of_rows_sent_before(self):
        # 前の形（rev 1、名前だけ）で 2 行とも送ってあった。新しい形では種類の言葉も入り、送り直しは people だけの UPDATE
        rows = ROWS + [{"stage_id": "40", "title": "ミュージカル 春の歌", "start": "2023-04-01", "end": "2023-04-02",
                        "fields": {"出演": "田中一", "原作": "山本二『春の歌』（小説）"}}]
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / 'past').mkdir()
            (d / 'd1').mkdir()
            (d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')
            (d / 'd1' / 'past_delivered.json').write_text('{"lines": 3}', encoding='utf-8')
            con = sqlite3.connect(d / 'd1.db')
            con.executescript('CREATE TABLE works(user_id TEXT, work_key TEXT, title TEXT, first_date TEXT, stage_id TEXT);')
            con.executescript(MIGRATION.read_text(encoding='utf-8'))
            con.executescript(SYNOPSIS.read_text(encoding='utf-8'))
            for r in rows:
                con.execute("INSERT INTO past_stage(stage_id,title,tkey,people) VALUES(?,?,?,'[]')", (r["stage_id"], r["title"], r["title"]))
            first = run('build', '--data', t, '--out', str(d / 'out'), '--budget', '4')     # 2 行分の UPDATE（1 行 2 と見る）
            self.assertEqual((first['updated'], first['rows'], first['to_refresh']), (2, 0, 1))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            run('commit', '--data', t, '--out', str(d / 'out'))
            second = run('build', '--data', t, '--out', str(d / 'out'))
            self.assertEqual((second['updated'], second['rows'], second['to_refresh']), (1, 0, 0))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            run('commit', '--data', t, '--out', str(d / 'out'))
            self.assertEqual(run('build', '--data', t, '--out', str(d / 'out'))['updated'], 0)
            people = {sid: json.loads(p) for sid, p in con.execute('SELECT stage_id, people FROM past_stage')}
            self.assertIn(['出演', '山田太郎'], people['30'])
            self.assertIn(['#形式', 'ミュージカル'], people['40'])
            self.assertIn(['#原作', '小説原作'], people['40'])
            # 題名・tkey は送り直しで変えない
            self.assertEqual(con.execute("SELECT title FROM past_stage WHERE stage_id='40'").fetchone()[0], 'ミュージカル 春の歌')


    def test_themes_read_later_are_added_to_rows_sent_before(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for sub in ('past', 'd1', 'credits'):
                (d / sub).mkdir()
            (d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in ROWS) + '\n', encoding='utf-8')
            con = sqlite3.connect(d / 'd1.db')
            con.executescript('CREATE TABLE works(user_id TEXT, work_key TEXT, title TEXT, first_date TEXT, stage_id TEXT);')
            con.executescript(MIGRATION.read_text(encoding='utf-8'))
            con.executescript(SYNOPSIS.read_text(encoding='utf-8'))
            run('build', '--data', t, '--out', str(d / 'out'))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            run('commit', '--data', t, '--out', str(d / 'out'))
            self.assertEqual(run('build', '--data', t, '--out', str(d / 'out'))['updated'], 0)
            # あとから 30 のあらすじが読めた
            (d / 'credits' / 'themes.jsonl').write_text(json.dumps({"side": "past", "id": "30", "synopsis": "家族の話",
                "elements": [{"word": "家族"}, {"word": "喪失"}]}, ensure_ascii=False) + '\n', encoding='utf-8')
            got = run('build', '--data', t, '--out', str(d / 'out'))
            self.assertEqual((got['updated'], got['rows'], got['with_themes']), (1, 0, 1))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            run('commit', '--data', t, '--out', str(d / 'out'))
            self.assertEqual(run('build', '--data', t, '--out', str(d / 'out'))['updated'], 0)      # 1 度だけ
            people = json.loads(con.execute("SELECT people FROM past_stage WHERE stage_id='30'").fetchone()[0])
            self.assertIn(['#題材', '家族'], people)
            self.assertIn(['出演', '山田太郎'], people)
            # 日記帳に出すあらすじも入る（migrations/0036）
            self.assertEqual(con.execute("SELECT synopsis FROM past_stage WHERE stage_id='30'").fetchone()[0], '家族の話')
            self.assertEqual(con.execute("SELECT synopsis FROM past_stage WHERE stage_id='20'").fetchone()[0], '')


class TitleKeyTest(unittest.TestCase):
    def test_the_key_comes_from_the_title_without_crown_and_subtitle(self):
        # 題名は冠名・サブタイトル込みで出し、自動の結び付け・候補の頭の一致に使う鍵はタイトルだけ（dec-title-crown-subtitle）
        sys.path.insert(0, str(SCRIPT.parent))
        import deliver_past as DP
        row = DP.row_values({"stage_id": "40", "title": "特別公演 熱海殺人事件", "title_main": "熱海殺人事件", "fields": {}})
        self.assertEqual(row[1:3], ("特別公演 熱海殺人事件", "熱海殺人事件"))
        # 前に取った行（title_main が無い）は題名から
        self.assertEqual(DP.row_values({"stage_id": "41", "title": "夜の果て", "fields": {}})[2], "夜の果て")


class RetitleDeliveryTest(unittest.TestCase):
    def test_rows_sent_before_get_their_crowned_title_once(self):
        # 送り済みの行の題名を、読み直した題名（冠名・サブタイトル込み）に UPDATE する。鍵（tkey）は変えない
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / 'past').mkdir()
            rows = [dict(ROWS[0]), {"stage_id": "50", "title": "熱海殺人事件", "start": "2024-01-01", "end": "2024-01-02", "fields": {}}]
            write = lambda rs: (d / 'past' / 'stages.jsonl').write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rs) + '\n', encoding='utf-8')  # noqa: E731
            write(rows)
            con = sqlite3.connect(d / 'd1.db')
            con.executescript('CREATE TABLE works(user_id TEXT, work_key TEXT, title TEXT, first_date TEXT, stage_id TEXT);')
            con.executescript(MIGRATION.read_text(encoding='utf-8'))
            con.executescript(SYNOPSIS.read_text(encoding='utf-8'))
            run('build', '--data', t, '--out', str(d / 'out'))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            run('commit', '--data', t, '--out', str(d / 'out'))
            # 取得が題名を読み直した（50 は冠名あり、30 は冠名なし）
            rows[0].update(title_main=rows[0]["title"])
            rows[1].update(title="特別公演 熱海殺人事件", title_main="熱海殺人事件")
            write(rows)
            got = run('build', '--data', t, '--out', str(d / 'out'))
            self.assertEqual((got['retitled'], got['rows']), (1, 0))
            con.executescript((d / 'out' / 'past-upload.sql').read_text(encoding='utf-8'))
            self.assertEqual(con.execute("SELECT title, tkey FROM past_stage WHERE stage_id='50'").fetchone(), ("特別公演 熱海殺人事件", "熱海殺人事件"))
            run('commit', '--data', t, '--out', str(d / 'out'))
            self.assertEqual(run('build', '--data', t, '--out', str(d / 'out'))['retitled'], 0)    # 送った行は二度送らない


class StatementSizeTest(unittest.TestCase):
    def test_statements_fit_d1_in_bytes(self):
        # 2026-10-14: 文字数で数えていたので、日本語の多い 7,016 行が SQLITE_TOOBIG で断られた
        sys.path.insert(0, str(HERE.parent / 'scripts'))
        import build_recommend_index as BI
        rows = [(str(i), '夜の果ての劇場' * 20, '出演' * 300) for i in range(400)]
        stmts = BI._inserts('past_stage', 'stage_id,title,people', rows)
        self.assertGreater(len(stmts), 1)
        self.assertTrue(all(len(x.encode('utf-8')) <= BI.MAX_STATEMENT_BYTES for x in stmts))
        self.assertEqual(sum(x.count("('") for x in stmts), 400)


if __name__ == '__main__':
    unittest.main()
