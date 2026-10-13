"""Independent tests. Execute only after the implementation completion gate.

Real SQLite executes the D1 SQL, including JSON_each and transactional CAS;
this is not a substitute for Python Workers/workerd or real-data verification.
"""
import asyncio
import copy
from pathlib import Path
import sqlite3
import sys
import unittest

PYTHON = Path(__file__).resolve().parents[1] / 'python'
sys.path.insert(0, str(PYTHON))
import snapshot_store as store


class Statement:
    def __init__(self, db, sql, args=()):
        self.db, self.sql, self.args = db, sql, args

    def bind(self, *args):
        return Statement(self.db, self.sql, args)

    def execute(self):
        self.db.query_count += 1
        if self.db.query_count > self.db.query_budget:
            raise RuntimeError('D1 query budget exceeded')
        previous = self.db.con.total_changes
        cursor = self.db.con.execute(self.sql, self.args)
        rows = [dict(row) for row in cursor.fetchall()] if cursor.description else []
        return {'results': rows, 'meta': {'changes': self.db.con.total_changes - previous}}

    async def first(self):
        rows = self.execute()['results']
        return rows[0] if rows else None

    async def all(self):
        return self.execute()

    async def run(self):
        return self.execute()


class SQLiteD1:
    def __init__(self):
        self.con = sqlite3.connect(':memory:', isolation_level=None)
        self.con.row_factory = sqlite3.Row
        self.con.execute('PRAGMA foreign_keys=ON')
        self.con.executescript((PYTHON / 'schema.sql').read_text())
        self.query_count, self.query_budget = 0, 50

    def prepare(self, sql):
        return Statement(self, sql)

    async def batch(self, commands):
        self.con.execute('BEGIN')
        try:
            results = [command.execute() for command in commands]
            self.con.execute('COMMIT')
            return results
        except Exception:
            self.con.execute('ROLLBACK')
            raise

    def invocation(self):
        self.query_count = 0


def fixture(uid, count=96):
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE works(user_id TEXT, id TEXT, title TEXT, note TEXT, rating TEXT, bytes BLOB, PRIMARY KEY(user_id,id))')
    con.execute('CREATE TABLE attendance(user_id TEXT, id TEXT, date TEXT, time TEXT, visit_note TEXT, PRIMARY KEY(user_id,id,date,time))')
    con.execute('CREATE TABLE future_fields(user_id TEXT, optional TEXT, number REAL)')
    for i in range(count):
        con.execute('INSERT INTO works VALUES(?,?,?,?,?,?)', (uid, str(i), '公演獅子' + str(i), '<感想>私的', '◎', b'\x00\xff'))
    con.executemany('INSERT INTO attendance VALUES(?,?,?,?,?)', [(uid,'0','2026-10-01','13:00','1回目'), (uid,'0','2026-10-02','18:00','2回目')])
    con.executemany('INSERT INTO future_fields VALUES(?,?,?)', [(uid,None,1.5), (uid,None,1.5)])
    result = store.capture(con, uid)
    con.close()
    return result


class SnapshotTests(unittest.TestCase):
    def test_roundtrip_preserves_all_fields_blob_null_duplicate_and_visits(self):
        original = fixture('A')
        con = store.materialize(original, 'A')
        try:
            self.assertEqual(store.capture(con, 'A'), original)
        finally:
            con.close()

    def test_capture_and_materialize_reject_cross_account(self):
        tables = fixture('A')
        with self.assertRaises(ValueError):
            store.materialize(tables, 'B')
        con = store.materialize(tables, 'A')
        try:
            con.execute("INSERT INTO future_fields VALUES('B','secret',1)")
            with self.assertRaises(ValueError):
                store.capture(con, 'A')
        finally:
            con.close()

    def test_96_records_d1_roundtrip_stays_within_50_query_budget(self):
        async def scenario():
            db = SQLiteD1()
            db.con.execute("INSERT INTO legacy_accounts(user_id) VALUES('A')")
            expected = fixture('A')
            self.assertEqual(await store.save(db,'A',0,expected,{}), 1)
            revision, loaded = await store.load(db,'A')
            self.assertEqual((revision,loaded), (1,expected))
            self.assertLessEqual(db.query_count,50)
            self.assertLess(db.query_count,15)
            db.con.close()
        asyncio.run(scenario())

    def test_conflicting_revision_never_overwrites_winning_write(self):
        async def scenario():
            db = SQLiteD1()
            db.con.execute("INSERT INTO legacy_accounts(user_id) VALUES('A')")
            baseline = fixture('A',1)
            await store.save(db,'A',0,baseline,{})
            winning, losing = copy.deepcopy(baseline), copy.deepcopy(baseline)
            winning['works']['rows'][0]['note'] = 'winner'
            losing['works']['rows'][0]['note'] = 'loser'
            db.invocation()
            self.assertEqual(await store.save(db,'A',1,winning,baseline),2)
            db.invocation()
            with self.assertRaises(store.ConcurrentWrite):
                await store.save(db,'A',1,losing,baseline)
            _, actual = await store.load(db,'A')
            self.assertEqual(actual,winning)
            db.con.close()
        asyncio.run(scenario())

    def test_foreign_rows_fail_before_mutation(self):
        async def scenario():
            db = SQLiteD1()
            db.con.execute("INSERT INTO legacy_accounts(user_id) VALUES('A')")
            with self.assertRaises(ValueError):
                await store.save(db,'A',0,fixture('B',1),{})
            self.assertEqual(db.query_count,0)
            self.assertEqual(db.con.execute("SELECT revision FROM legacy_accounts WHERE user_id='A'").fetchone()[0],0)
            db.con.close()
        asyncio.run(scenario())


if __name__ == '__main__':
    unittest.main()
