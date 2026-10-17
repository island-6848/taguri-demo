import {DatabaseSync} from 'node:sqlite';
import {readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';
import {TERMS_VERSION} from '../src/terms.js';
function setup() {
  const sqlite=new DatabaseSync(':memory:');for (const file of readdirSync(new URL('../migrations/', import.meta.url)).filter(n => n.endsWith('.sql')).sort())sqlite.exec(readFileSync(new URL(`../migrations/${file}`,import.meta.url),'utf8'));
  const wrap=(sql,args=[])=>({bind(...values){return wrap(sql,values);},async first(){return sqlite.prepare(sql).get(...args)??null;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async run(){return sqlite.prepare(sql).run(...args);},async execute(){return /^SELECT/.test(sql)?this.all():this.run();}});
  const env={ALLOW_REGISTRATION:'true',DB:{prepare:sql=>wrap(sql),async batch(commands){sqlite.exec('BEGIN');try{const result=[];for(const c of commands)result.push(await c.execute());sqlite.exec('COMMIT');return result;}catch(e){sqlite.exec('ROLLBACK');throw e;}}},ASSETS:{fetch:()=>new Response('static')}};
  const call=(path,value,cookie='',origin='https://taguri.example')=>worker.fetch(new Request(`https://taguri.example/api/${path}`,{method:value===undefined?'GET':'POST',headers:{cookie,origin,'content-type':'application/json'},body:value===undefined?undefined:JSON.stringify(value)}),env);
  return {call,sqlite,env};
}
async function register(call) {const response=await call('register',{agree:TERMS_VERSION});assert.equal(response.status,200);return {cookie:response.headers.get('set-cookie').split(';')[0],...(await response.json())};}
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
  const result=await (await call('catalogue')).json();assert.equal(result.items[0].title,'作品');assert.equal(result.items[0].why_b,undefined);assert.equal(result.items[0].note,undefined);
});
test('reactions are scoped, exportable and removable, and imports retain older versions',async()=>{
  const {call}=setup();const a=await register(call),b=await register(call);
  await call('reaction',{stage_id:'s1',status:'interest'},a.cookie);
  assert.equal((await (await call('state',undefined,b.cookie)).json()).reactions.length,0);
  const backup=await (await call('export',undefined,a.cookie)).json();assert.equal(backup.version,2);
  assert.equal((await call('import',backup,b.cookie)).status,200);
  assert.equal((await (await call('state',undefined,b.cookie)).json()).reactions[0].status,'interest');
  await call('reaction',{stage_id:'s1',status:'interest',remove:true},a.cookie);
  assert.equal((await (await call('state',undefined,a.cookie)).json()).reactions.length,0);
  assert.equal((await call('import',{version:1,records:[],favourites:[]},a.cookie)).status,200);
  assert.equal((await call('record',null,a.cookie)).status,400);
});
test('health returns only the delivered catalogue dates and counts, without a login',async()=>{
  const {call,sqlite}=setup();
  assert.deepEqual((await (await call('health')).json()).catalog,{present:false,upcoming:{candidates:0},opening_14d:{index:0,catalogue:0}});
  sqlite.exec("INSERT INTO rec_meta(k,v) VALUES('catalogue_scan','2026-10-13'),('catalogue_delivered','2026-10-13T20:00:00+00:00'),('catalogue_upcoming','1532'),('current','abc')");
  const response=await call('health');assert.equal(response.status,200);
  assert.deepEqual((await response.json()).catalog,{present:true,uploaded_at:'2026-10-13T20:00:00+00:00',scan_date:'2026-10-13',upcoming:{candidates:1532},opening_14d:{index:0,catalogue:0},index_version:'abc'});
});
// 起案者の指示 2026-10-17「規約は新規登録の際に、規約に同意して始める、にチェックボックスいれてもらってから登録できるようにする」
test('a new account needs the current terms agreed, and keeps which version and when', async () => {
  const {call, sqlite} = setup();
  const none = await call('register', {});
  assert.equal(none.status, 400);
  assert.match((await none.json()).error, /同意して始める/);
  assert.equal((await call('register', {agree: '2000-01-01'})).status, 409);
  assert.equal(sqlite.prepare('SELECT count(*) AS n FROM users').get().n, 0);
  await register(call);
  const u = sqlite.prepare('SELECT terms_version, terms_at FROM users').get();
  assert.equal(u.terms_version, TERMS_VERSION);
  assert.ok(u.terms_at > 0);
});
test('the terms and privacy pages open without signing in', async () => {
  const {env} = setup();
  for (const p of ['/terms', '/privacy']) {
    const r = await worker.fetch(new Request('https://taguri.example' + p), env);
    assert.equal(r.status, 200, p);
  }
});
test('the sign-up checkbox, the terms and the privacy page carry the version the server asks for', () => {
  const read = f => readFileSync(new URL(`../public/${f}`, import.meta.url), 'utf8');
  assert.match(read('login.html'), new RegExp(`<input type="checkbox" id="agree" value="${TERMS_VERSION}">`));
  assert.match(read('login.html'), /href="\/terms"[^>]*>利用規約<\/a>と<a href="\/privacy"/);
  for (const f of ['terms.html', 'privacy.html']) assert.match(read(f), new RegExp(`版 ${TERMS_VERSION}`), f);
  assert.match(read('vendor/firebase-login.js'), /taguri_login_agree/);
});
test('the login page puts ログイン above 新規登録, and only the sign-up box has the terms checkbox', () => {
  const html = readFileSync(new URL('../public/login.html', import.meta.url), 'utf8');
  const login = html.indexOf('<section id="login"'), signup = html.indexOf('<section id="signup"');
  assert.ok(login > 0 && signup > login);
  const agree = html.indexOf('id="agree"');
  assert.ok(agree > signup);
  for (const id of ['google-signup', 'email-signup', 'passkey-signup', 'signup-email-form']) assert.ok(html.indexOf(`id="${id}"`) > signup, id);
  for (const id of ['google', 'passkey-login', 'email-form']) { const i = html.indexOf(`id="${id}"`); assert.ok(i > login && i < signup, id); }
  assert.match(readFileSync(new URL('../public/vendor/firebase-login.js', import.meta.url), 'utf8'), /taguri_login_intent/);
});
