import asyncio, contextlib, importlib, io, json, sys, unittest, zipfile
from types import SimpleNamespace
from unittest.mock import patch
from test_auth_migration import database, request
from test_full_migration import PYTHON
sys.path.insert(0,str(PYTHON/'python_modules'))
import legacy_runtime as runtime
import native_provision
class FakeResponse:
 def __init__(self,body,status=200,headers=None): self.body,self.status,self.headers=body,status,headers or {}
sys.modules['workers']=SimpleNamespace(Response=FakeResponse,WorkerEntrypoint=object,DurableObject=object)
import entry

class RendererTests(unittest.TestCase):
 def test_original_add_rate_note_visit_export_and_failure_rollback(self):
  async def setup():
   db=database();db.con.execute("INSERT INTO users VALUES('A','aaaa',0)");return await native_provision.build_snapshot(db,'A')
  tables=asyncio.run(setup())
  status,body,_,tables=runtime.execute('A',tables,'/api/add_work','POST',json.dumps({'title':'手入力検証','date':'2026-10-07','time':'18:00','venue':'劇場'}).encode());self.assertEqual(status,200)
  key=json.loads(body)['work_key']
  for route,payload in [('rate',{'work_key':key,'verdict':'◎'}),('note',{'work_key':key,'note_impression':'私的感想'}),('visit_note',{'uid':'visit-a','note':'回別メモ'})]:
   status,_,_,tables=runtime.execute('A',tables,'/api/'+route,'POST',json.dumps(payload).encode());self.assertEqual(status,200,route)
  work=tables['works']['rows'][0];self.assertEqual(work['verdict'],'◎');self.assertEqual(work['note_impression'],'私的感想')
  self.assertEqual(tables['visit_note']['rows'][0]['note'],'回別メモ')
  before=tables
  status,_,_,tables=runtime.execute('A',tables,'/api/rate','POST',json.dumps({'work_key':key,'verdict':'INVALID'}).encode());self.assertGreaterEqual(status,400);self.assertEqual(tables,before)
  status,body,_,_=runtime.execute('A',tables,'/export.json');self.assertEqual(status,200);self.assertEqual(json.loads(body)['tables'],tables)
 def test_17_original_screens_nonempty_catalogue_and_private_export(self):
  async def setup():
   db=database();db.con.execute("INSERT INTO users VALUES('A','aaaa',0)");return await native_provision.build_snapshot(db,'A')
  tables=asyncio.run(setup());original=runtime.serve.APP.DB
  for name in sorted(runtime.SCREENS):
   status,body,headers,tables=runtime.execute('A',tables,'/api/screen/'+name)
   self.assertEqual(status,200,(name,body[:300]));payload=json.loads(body);self.assertTrue(payload.get('body_html'),name)
   self.assertEqual(runtime.serve.APP.DB,original)
  status,body,_,_=runtime.execute('A',tables,'/api/screen/recommend');self.assertIn('検証公演獅子',json.loads(body)['body_html'])
  status,body,_,_=runtime.execute('A',tables,'/export.json');self.assertEqual(status,200);self.assertNotIn('recovery_hash',body.decode())
  zipped=entry.archive('A',tables)
  with zipfile.ZipFile(io.BytesIO(zipped)) as z:
   self.assertEqual(z.namelist(),['taguri-export.json']);self.assertEqual(json.loads(z.read(z.namelist()[0]))['tables'],tables)
 def test_preferences_follow_request_and_remain_account_scoped(self):
  async def setup():
   db=database();db.con.execute("INSERT INTO users VALUES('A','aaaa',0)");return await native_provision.build_snapshot(db,'A')
  tables=asyncio.run(setup())
  status,_,_,tables=runtime.execute('A',tables,'/api/screen/recommend?f=1&pref=大阪府');self.assertEqual(status,200)
  setting=[r for r in tables['app_setting']['rows'] if r['key']=='runtime_pref_filter'];self.assertEqual(json.loads(setting[0]['value']),['大阪府'])
  status,body,_,tables=runtime.execute('A',tables,'/api/screen/recommend');self.assertEqual(status,200)
  status,_,_,tables=runtime.execute('A',tables,'/api/pref_setting','POST',json.dumps({'prefs':['東京都']}).encode());self.assertEqual(status,200)
 def test_log_masks_secrets_and_readiness_fails_closed(self):
  async def scenario():
   obj=entry.OriginalRenderer();obj.env=SimpleNamespace(MIGRATION_READY='false');r=request('/api/screen/recommend?token=TOKEN_SECRET');r.headers['Cookie']='taguri_session=COOKIE_SECRET'
   log=io.StringIO()
   with contextlib.redirect_stdout(log): result=await obj.fetch(r)
   self.assertEqual(result.status,503);self.assertNotIn('TOKEN_SECRET',log.getvalue());self.assertNotIn('COOKIE_SECRET',log.getvalue())
   event=json.loads(log.getvalue());self.assertEqual(event['route'],'screen');self.assertIn('duration_ms',event)
   with patch.object(obj,'dispatch',side_effect=RuntimeError('SECRET SQL PRIVATE NOTE')):
    log=io.StringIO()
    with contextlib.redirect_stdout(log): result=await obj.fetch(r)
    self.assertEqual(result.status,503);self.assertNotIn('SECRET',log.getvalue()+result.body)
  asyncio.run(scenario())
 def test_public_fields_theater_tours_prices_credits_and_no_private_notes(self):
  from public_snapshot import PUBLIC_FILES
  sys.path.insert(0,str(PYTHON.parent/'scripts'))
  from build_public_snapshot import clean_fields
  self.assertEqual(clean_fields({'出演':['一郎','二郎'],'演出':'既存名','unknownrole':['PRIVATE']}),{'出演':'一郎、二郎','演出':'既存名'})
  row=json.loads(PUBLIC_FILES['data/review/candidates.jsonl'])
  self.assertEqual(row['theater'],'検証劇場');self.assertEqual(row['price'],'5000円');self.assertEqual(row['onsale'],'発売中')
  self.assertEqual(row['tours'][0]['theater'],'大阪検証劇場');self.assertEqual(row['tours'][0]['price'],'5500円')
  self.assertEqual(row['fields']['出演'],'検証出演者');self.assertNotIn('unknownrole',row['fields']);self.assertNotIn('secret-note',str(PUBLIC_FILES))
  self.assertTrue(entry.metadata(b'{"ok":true}')['persistent_mode'])

if __name__=='__main__': unittest.main()
