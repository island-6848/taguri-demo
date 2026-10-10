import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
function setup() {
  const sqlite=new DatabaseSync(':memory:');sqlite.exec(readFileSync(new URL('../migrations/0001.sql',import.meta.url),'utf8'));
  const wrap=(sql,args=[])=>({bind(...values){return wrap(sql,values);},async first(){return sqlite.prepare(sql).get(...args)??null;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async run(){return sqlite.prepare(sql).run(...args);},async execute(){return /^SELECT/.test(sql)?this.all():this.run();}});
  const env={ALLOW_REGISTRATION:'true',DB:{prepare:sql=>wrap(sql),async batch(commands){sqlite.exec('BEGIN');try{const result=[];for(const c of commands)result.push(await c.execute());sqlite.exec('COMMIT');return result;}catch(e){sqlite.exec('ROLLBACK');throw e;}}},ASSETS:{fetch:()=>new Response('static')}};
  const call=(path,value,cookie='',origin='https://taguri.example')=>worker.fetch(new Request(`https://taguri.example/api/${path}`,{method:value===undefined?'GET':'POST',headers:{cookie,origin,'content-type':'application/json'},body:value===undefined?undefined:JSON.stringify(value)}),env);
  return {call,sqlite,env};
}
async function register(call) {const response=await call('register',{});assert.equal(response.status,200);return {cookie:response.headers.get('set-cookie').split(';')[0],...(await response.json())};}
test('records, ratings, favourites persist; recovery restores the same account',async()=>{
  const {call,sqlite}=setup();const a=await register(call);
  assert.match(a.cookie,/taguri_session=/);assert.equal(a.recovery_code.length,64);
  assert.equal((await call('record',{id:'show1',title:'舞台',date:'2026-11-16',time:'13:00',venue:'劇場',rating:'◎',note:'感想'},a.cookie)).status,200);
  await call('favourite',{name:'作者',kind:'人'},a.cookie);
  const recovered=await call('recover',{code:a.recovery_code});assert.equal(recovered.status,200);
  const recoveredCookie=recovered.headers.get('set-cookie').split(';')[0];
  const state=await (await call('state',undefined,recoveredCookie)).json();assert.equal(state.records[0].rating,'◎');assert.equal(state.favourites[0].name,'作者');
  const stored=sqlite.prepare('SELECT hash FROM sessions').get();assert.ok(!stored.hash.includes(a.cookie.split('=')[1]));
  assert.equal((await call('logout',{},a.cookie)).status,200);assert.equal((await call('state',undefined,a.cookie)).status,401);
});
test('other users cannot read, update or delete records; imports ignore supplied user IDs',async()=>{
  const {call}=setup();const a=await register(call),b=await register(call);
  await call('record',{id:'same',title:'秘密',date:'2026-01-01'},a.cookie);
  assert.equal((await (await call('state',undefined,b.cookie)).json()).records.length,0);
  await call('record/delete',{id:'same'},b.cookie);
  await call('import',{version:1,records:[{id:'same',user_id:'other',title:'別の記録',date:'2026-01-02'}],favourites:[]},b.cookie);
  assert.equal((await (await call('state',undefined,a.cookie)).json()).records[0].title,'秘密');
});
test('cross-origin mutations, malformed input and expired sessions fail safely',async()=>{
  const {call,sqlite}=setup();const a=await register(call);
  assert.equal((await call('record',{title:'bad',date:'2026-02-30'},a.cookie)).status,400);
  assert.equal((await call('record',{title:'bad',date:'2026-02-01',time:'25:00'},a.cookie)).status,400);
  assert.equal((await call('register',{},'', 'https://evil.example')).status,403);
  assert.equal((await call('recover',{code:'x'})).status,401);
  assert.equal((await call('record',{title:'bad',date:'2026-02-01',note:'a'.repeat(262145)},a.cookie)).status,413);
  sqlite.exec('UPDATE sessions SET expires_at=0');assert.equal((await call('state',undefined,a.cookie)).status,401);
});
test('batch import validates every item before any write and can be repeated',async()=>{
  const {call}=setup();const a=await register(call);
  const records=Array.from({length:96},(_,i)=>({id:`r${i}`,title:`舞台${i}`,date:'2026-10-24'}));
  assert.equal((await call('import',{version:1,records:[records[0],{title:'bad',date:'no'}],favourites:[]},a.cookie)).status,400);
  assert.equal((await (await call('state',undefined,a.cookie)).json()).records.length,0);
  for(let round=0;round<2;round++)for(let i=0;i<records.length;i+=20)assert.equal((await call('import',{version:1,records:records.slice(i,i+20),favourites:[]},a.cookie)).status,200);
  assert.equal((await (await call('export',undefined,a.cookie)).json()).records.length,96);
});
test('registration can be disabled and catalogue never exposes user data',async()=>{
  const {call,env,sqlite}=setup();env.ALLOW_REGISTRATION='false';assert.equal((await call('register',{})).status,503);
  sqlite.prepare('INSERT INTO catalogue(id,title,date) VALUES(?,?,?)').run('one','作品','2099-01-01');
  const result=await (await call('catalogue')).json();assert.deepEqual(Object.keys(result.items[0]),['id','title','date','venue','url']);
});
