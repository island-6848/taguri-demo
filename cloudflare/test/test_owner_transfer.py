import asyncio, hashlib, json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path
from test_full_migration import PYTHON,SQLiteD1
sys.path.insert(0,str(PYTHON.parent/'scripts'))
from prepare_legacy_migration import prepare
from snapshot_store import load,keyed_rows
class OwnerTests(unittest.TestCase):
 def source(self,folder):
  path=Path(folder)/'old.db';c=sqlite3.connect(path);c.executescript('CREATE TABLE works(user_id TEXT,id TEXT,note TEXT,PRIMARY KEY(user_id,id));CREATE TABLE extra(user_id TEXT,blob BLOB);CREATE TABLE shared(x TEXT);');c.executemany('INSERT INTO works VALUES(?,?,?)',[('local','1','owner'),('guest','1','guest')]);c.execute('INSERT INTO extra VALUES(?,?)',('local',b'\x00\xff'));c.execute("INSERT INTO shared VALUES('secret-shared')");c.commit();c.close();return path
 def test_explicit_transfer_rekeys_all_rows_and_checksums_and_conflict_rollback(self):
  with tempfile.TemporaryDirectory() as folder:
   path=self.source(folder);code='e'*64;before=hashlib.sha256(path.read_bytes()).hexdigest()
   with self.assertRaises(ValueError):prepare(path,'local','owner-new')
   with self.assertRaises(ValueError):prepare(path,'guest','owner-new',True,code)
   with self.assertRaises(ValueError):prepare(path,'guest','different')
   ordinary=prepare(path,'guest','guest');self.assertFalse(ordinary['owner_identity_transfer'])
   manifest=prepare(path,'local','owner-new',True,code);self.assertNotIn(code,json.dumps(manifest));self.assertEqual(manifest['commands'][0]['params'][1],hashlib.sha256(code.encode()).hexdigest());self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
   self.assertEqual(manifest['shared_tables_not_imported'][0]['table'],'shared');self.assertNotIn('secret-shared',json.dumps(manifest))
   async def scenario():
    db=SQLiteD1();db.con.executescript((PYTHON.parent/'migrations/0001.sql').read_text());commands=lambda:[db.prepare(c['sql']).bind(*c['params']) for c in manifest['commands']]
    await db.batch(commands());_,tables=await load(db,'owner-new')
    for name,table in tables.items():
     self.assertTrue(all(r['user_id']=='owner-new' for r in table['rows']));self.assertEqual(len(table['rows']),manifest['counts'][name]);encoded=json.dumps(table['rows'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode();self.assertEqual(hashlib.sha256(encoded).hexdigest(),manifest['sha256'][name]);self.assertNotEqual(manifest['sha256'][name],manifest['source_sha256'][name]);stored={r['row_key']:r['row_json'] for r in db.con.execute('SELECT row_key,row_json FROM legacy_rows WHERE table_name=?',(name,))};self.assertEqual(stored,keyed_rows(table))
    existing=list(db.con.execute('SELECT * FROM legacy_rows'))
    with self.assertRaises(sqlite3.IntegrityError):await db.batch(commands())
    self.assertEqual(list(db.con.execute('SELECT * FROM legacy_rows')),existing);self.assertEqual(db.con.execute('SELECT count(*) FROM users').fetchone()[0],1)
   asyncio.run(scenario())
 def test_cli_credential_private_no_overwrite_and_failed_pair_creation_cleanup(self):
  with tempfile.TemporaryDirectory() as folder:
   path=self.source(folder);out=Path(folder)/'manifest.json';cred=Path(folder)/'recovery.json';cmd=[sys.executable,str(PYTHON.parent/'scripts/prepare_legacy_migration.py'),'--db',str(path),'--user-id','local','--target-user-id','owner-new','--owner-transfer','--output',str(out),'--owner-recovery-output',str(cred)]
   r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);value=json.loads(cred.read_text());code=value['recovery_code'];self.assertNotIn(code,out.read_text()+r.stdout+r.stderr);self.assertEqual(out.stat().st_mode&0o777,0o600);self.assertEqual(cred.stat().st_mode&0o777,0o600);self.assertEqual(json.loads(out.read_text())['commands'][0]['params'][1],hashlib.sha256(code.encode()).hexdigest())
   original=(out.read_bytes(),cred.read_bytes());r=subprocess.run(cmd,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertEqual((out.read_bytes(),cred.read_bytes()),original)
   out.unlink();r=subprocess.run(cmd,capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists());self.assertEqual(cred.read_bytes(),original[1])
