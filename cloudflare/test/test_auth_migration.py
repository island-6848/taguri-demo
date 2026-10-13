import asyncio, hashlib, json, sys, unittest
from pathlib import Path
from types import SimpleNamespace
from test_full_migration import SQLiteD1, PYTHON
import cloud_auth as auth
sys.path.insert(0,str(PYTHON/'python_modules'))

class Body:
 def __init__(self,data): self.data=data
 def getReader(self): return self
 async def read(self):
  data,self.data=self.data,None
  return SimpleNamespace(done=data is None,value=data)
 async def cancel(self): self.data=None

def request(path='/',value=None,cookie=''):
 return SimpleNamespace(url='https://test.example'+path,method='POST' if value is not None else 'GET',headers={'Cookie':cookie,'Origin':'https://test.example','Content-Type':'application/json','CF-Connecting-IP':'192.0.2.1'},body=Body(json.dumps(value or {}).encode()))

def database():
 db=SQLiteD1()
 for path in [PYTHON.parent/'migrations/0001.sql',PYTHON.parent/'migrations/0002.sql',PYTHON/'auth-schema.sql']: db.con.executescript(path.read_text())
 return db

class AuthTests(unittest.TestCase):
 def test_guest_restore_link_once_and_scoped_delete(self):
  async def scenario():
   db=database();env=SimpleNamespace(DB=db,ALLOW_REGISTRATION='true')
   a=await auth.resolve_account(request(),env);db.invocation();b=await auth.resolve_account(request(),env)
   ca=a['set_cookie'].split(';')[0];cb=b['set_cookie'].split(';')[0]
   db.invocation();status,_,headers=await auth.handle_auth(request('/api/recover',{'code':a['welcome_code']}),env);self.assertEqual(status,200)
   self.assertEqual(await auth.current(request(cookie=headers['Set-Cookie'].split(';')[0]),env),a['user_id'])
   db.invocation();_,linked,_=await auth.handle_auth(request('/api/link/create',{},ca),env)
   db.invocation();self.assertEqual((await auth.handle_auth(request('/api/link/redeem',{'code':linked['code']}),env))[0],200)
   db.invocation()
   with self.assertRaises(auth.AuthError) as e: await auth.handle_auth(request('/api/link/redeem',{'code':linked['code']}),env)
   self.assertEqual(e.exception.status,401)
   db.invocation();self.assertEqual((await auth.handle_auth(request('/api/delete_account',{'confirm':'DELETE','user_id':b['user_id']},ca),env))[0],200)
   self.assertIsNone(await auth.current(request(cookie=ca),env));self.assertEqual(await auth.current(request(cookie=cb),env),b['user_id'])
   self.assertFalse(db.con.execute('SELECT 1 FROM legacy_accounts WHERE user_id=?',(a['user_id'],)).fetchone())
  asyncio.run(scenario())
 def test_expired_and_legacy_cookie_never_create_blank_identity(self):
  async def scenario():
   db=database();env=SimpleNamespace(DB=db,ALLOW_REGISTRATION='true')
   for c,expected in [('taguri_session='+'a'*64,401),('tg_session='+'b'*43,503)]:
    db.invocation()
    with self.assertRaises(auth.AuthError) as e: await auth.resolve_account(request(cookie=c),env)
    self.assertEqual(e.exception.status,expected)
   self.assertEqual(db.con.execute('SELECT count(*) FROM users').fetchone()[0],0)
  asyncio.run(scenario())
 def test_old_code_requires_pepper_and_imported_identity(self):
  async def scenario():
   db=database();env=SimpleNamespace(DB=db,ALLOW_REGISTRATION='true');a=await auth.resolve_account(request(),env);code='a'*26;pepper='12'*32
   db.invocation()
   with self.assertRaises(auth.AuthError) as e: await auth.handle_auth(request('/api/recover',{'code':code}),env)
   self.assertEqual(e.exception.status,503)
   old=hashlib.scrypt(code.encode(),salt=bytes.fromhex(pepper),n=16384,r=8,p=1,dklen=16).hex();db.con.execute('INSERT INTO legacy_user_map VALUES(?,?)',(old,a['user_id']))
   env.LEGACY_AUTH_PEPPER=pepper;env.LEGACY_SCRYPT_ENABLED='true';db.invocation()
   self.assertEqual((await auth.handle_auth(request('/api/recover',{'code':code}),env))[0],200)
   self.assertEqual(db.con.execute('SELECT recovery_hash FROM legacy_recovery').fetchone()[0],auth.digest(code))
  asyncio.run(scenario())
 def test_origin_sql_input_and_throttle(self):
  async def scenario():
   db=database();env=SimpleNamespace(DB=db,ALLOW_REGISTRATION='true');r=request('/api/recover',{'code':'bad'});r.headers['Origin']='https://evil.example'
   with self.assertRaises(auth.AuthError) as e: await auth.handle_auth(r,env)
   self.assertEqual(e.exception.status,403)
   for _ in range(10):
    db.invocation()
    with self.assertRaises(auth.AuthError) as e: await auth.handle_auth(request('/api/recover',{'code':"';DROP TABLE users;--"}),env)
    self.assertEqual(e.exception.status,401)
   db.invocation()
   with self.assertRaises(auth.AuthError) as e: await auth.handle_auth(request('/api/recover',{'code':'bad'}),env)
   self.assertEqual(e.exception.status,429);self.assertEqual(db.con.execute('SELECT count(*) FROM users').fetchone()[0],0)
  asyncio.run(scenario())
 def test_native_96_archive_and_idempotent_conversion(self):
  async def scenario():
   db=database();uid='native-user';db.con.execute('INSERT INTO users VALUES(?,?,0)',(uid,'f'*64))
   for i in range(96): db.con.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?)',(uid,str(i),'公演'+str(i),'2026-10-07','18:00','劇場','◎','秘密感想',12345))
   db.invocation();await auth.provision_native(db,uid);self.assertLessEqual(db.query_count,50)
   from snapshot_store import load
   db.invocation();_,tables=await load(db,uid);self.assertEqual(len(tables['works']['rows']),96);self.assertEqual(len(tables['native_source']['rows']),96)
   archived=json.loads(tables['native_source']['rows'][0]['row_json']);self.assertEqual(archived['note'],'秘密感想');self.assertEqual(archived['updated_at'],12345)
   rows=db.con.execute('SELECT count(*) FROM legacy_rows').fetchone()[0];db.invocation();await auth.provision_native(db,uid);self.assertEqual(db.con.execute('SELECT count(*) FROM legacy_rows').fetchone()[0],rows)
  asyncio.run(scenario())

if __name__=='__main__': unittest.main()
