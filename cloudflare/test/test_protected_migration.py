import asyncio, hashlib, json, sqlite3, sys, tempfile, unittest
from pathlib import Path
from test_full_migration import PYTHON,SQLiteD1
sys.path.insert(0,str(PYTHON.parent/'scripts'))
from export_legacy_account import snapshot
from prepare_legacy_migration import prepare
class ProtectedTests(unittest.TestCase):
 def test_read_only_full_snapshot_scoping_and_shared_inventory(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'old.db';con=sqlite3.connect(path);con.executescript('CREATE TABLE works(user_id TEXT,id TEXT,note TEXT,opaque BLOB,PRIMARY KEY(user_id,id));CREATE TABLE shared_secret(x TEXT);');con.executemany('INSERT INTO works VALUES(?,?,?,?)',[('A','1','A秘密',b'\x00\xff'),('B','1','B秘密',b'other')]);con.execute("INSERT INTO shared_secret VALUES('private')");con.commit();con.close();before=hashlib.sha256(path.read_bytes()).hexdigest();result=snapshot(path,'A');self.assertEqual(result['tables']['works']['count'],1);self.assertEqual(result['tables']['works']['rows'][0]['note'],'A秘密');self.assertEqual(result['shared_tables_not_exported'][0]['table'],'shared_secret');self.assertNotIn('B秘密',str(result));self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
   with self.assertRaises(ValueError):prepare(path,'local','local')
   with self.assertRaises(ValueError):prepare(path,'A','B')
   manifest=prepare(path,'A','A');self.assertLessEqual(len(manifest['commands']),40)
   async def apply():
    db=SQLiteD1();db.con.executescript((PYTHON.parent/'migrations/0001.sql').read_text());await db.batch([db.prepare(c['sql']).bind(*c['params']) for c in manifest['commands']]);self.assertEqual(db.con.execute('SELECT count(*) FROM legacy_rows').fetchone()[0],1)
    with self.assertRaises(sqlite3.IntegrityError):await db.batch([db.prepare(c['sql']).bind(*c['params']) for c in manifest['commands']])
    self.assertEqual(db.con.execute('SELECT count(*) FROM legacy_rows').fetchone()[0],1)
   asyncio.run(apply())
 def test_failed_batch_rolls_back_account_schema_and_rows(self):
  async def scenario():
   db=SQLiteD1();db.con.executescript((PYTHON.parent/'migrations/0001.sql').read_text())
   with self.assertRaises(sqlite3.OperationalError):await db.batch([db.prepare('INSERT INTO users VALUES(?,?,0)').bind('A','a'*64),db.prepare('INSERT INTO legacy_accounts(user_id) VALUES(?)').bind('A'),db.prepare('INSERT INTO absent VALUES(?)').bind('bad')])
   self.assertEqual(db.con.execute('SELECT count(*) FROM users').fetchone()[0],0);self.assertEqual(db.con.execute('SELECT count(*) FROM legacy_accounts').fetchone()[0],0)
  asyncio.run(scenario())
