import {test} from 'node:test';
import assert from 'node:assert/strict';
import {originalUI,isOriginalRoute} from '../src/original-ui.js';
import worker from '../src/worker.js';
test('all original screen names are transported without changing fragment HTML',async()=>{
 const names=['recommend','reminder','interest','favourites','calendar','tickets','rate','unrated','notes','register','records','trace','chronicle','works','search','settings','start'];
 for(const name of names) {
  const html='<h1>元の画面</h1><div class="card">変更しない本文</div>';
  const r=await originalUI(new Request(`https://taguri.example/api/screen/${name}?y=2026`,{headers:{cookie:'tg_session='+'a'.repeat(43)+'; taguri_session=private-d1-session'}}),async(url,options)=>{
   assert.equal(url,`https://taguri-demo.onrender.com/api/screen/${name}?y=2026`);
   assert.equal(options.headers.get('cookie'),'tg_session='+'a'.repeat(43));
   return Response.json({ok:true,body_html:html,demo_mode:true});
  });
  assert.equal((await r.json()).body_html,html);assert.equal(r.headers.get('cache-control'),'private, no-store');
 }
});
test('original saves retain the body; foreign origins cannot write',async()=>{
 const body=JSON.stringify({work_key:'作品#2026-01-01',verdict:'◎'});
 const req=new Request('https://taguri.example/api/rate',{method:'POST',headers:{origin:'https://taguri.example','content-type':'application/json'},body});
 const r=await originalUI(req,async(url,options)=>{assert.equal(url,'https://taguri-demo.onrender.com/api/rate');assert.equal(options.headers.get('origin'),'https://taguri-demo.onrender.com');assert.equal(new TextDecoder().decode(options.body),body);return Response.json({ok:true});});
 assert.equal(r.status,200);
 const bad=await originalUI(new Request('https://taguri.example/api/rate',{method:'POST',headers:{origin:'https://evil.example'},body:'{}'}),()=>{throw Error('Must not contact upstream');});assert.equal(bad.status,403);
});
test('session cookies and redirects stay on this site; global backups are not exposed',async()=>{
 const r=await originalUI(new Request('https://taguri.example/recover'),async()=>new Response('restore',{status:302,headers:{location:'https://taguri-demo.onrender.com/settings','set-cookie':'tg_session='+'b'.repeat(43)+'; Domain=taguri-demo.onrender.com; Path=/; HttpOnly; SameSite=None; Secure'}}));
 assert.equal(r.headers.get('location'),'/settings');assert.ok(!r.headers.get('set-cookie').includes('Domain='));assert.match(r.headers.get('set-cookie'),/SameSite=Strict/);
 for(const path of ['/data.zip','/export.json','/api/screen/unknown']) {const denied=await originalUI(new Request('https://taguri.example'+path),()=>{throw Error('No unsafe upstream');});assert.ok(denied.status>=400);}
 assert.equal(isOriginalRoute('/rate'),false);
});
test('D1 migration API and its records stay accessible after restoring the original frontend',async()=>{
 const result=await worker.fetch(new Request('https://taguri.example/migration-api/register',{method:'POST',headers:{origin:'https://taguri.example','content-type':'application/json'},body:'{}'}),{ORIGINAL_UI_BRIDGE:'true',ALLOW_REGISTRATION:'false'});
 assert.equal(result.status,503);assert.match((await result.json()).error,/新規登録/);
});
