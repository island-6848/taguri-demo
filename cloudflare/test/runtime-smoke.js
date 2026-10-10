// Run against local workerd/D1 only. Never point this script at a public account.
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const base='http://127.0.0.1:8787';
const server=spawn('npx',['wrangler','dev','--ip','127.0.0.1','--port','8787'],{detached:true,stdio:['ignore','pipe','pipe'],env:{...process.env,WRANGLER_SEND_METRICS:'false'}});
let logs='';for(const stream of [server.stdout,server.stderr])stream.on('data',data=>{logs=(logs+data.toString()).slice(-6000);});
async function request(path,value,cookie='') {
 return fetch(`${base}/api/${path}`,value===undefined?{headers:{cookie}}:{method:'POST',headers:{origin:base,'Content-Type':'application/json',cookie},body:JSON.stringify(value)});
}
try {
 let ready=false;
 for(let i=0;i<60;i++) {
  if(server.exitCode!==null)throw new Error(`Wrangler exited: ${logs}`);
  try{const r=await fetch(base);if(r.ok){ready=true;break;}}catch{}
  await new Promise(resolve=>setTimeout(resolve,1000));
 }
 assert.ok(ready,`Local worker did not start: ${logs}`);
 const registered=await request('register',{});assert.equal(registered.status,200);
 const cookie=registered.headers.get('set-cookie').split(';')[0];assert.match(registered.headers.get('set-cookie'),/HttpOnly; Secure; SameSite=Strict/);
 const {recovery_code}=await registered.json();
 const fixture=JSON.parse(readFileSync(new URL('../../tools/taguri/demo_purchase_works.json',import.meta.url)));
 for(let i=0;i<fixture.length;i+=10) {
  const response=await request('import',{version:2,records:fixture.slice(i,i+10).map((r,j)=>({...r,id:`test-${i+j}`})),favourites:[],reactions:[]},cookie);
  assert.equal(response.status,200,await response.text());
 }
 const state=await (await request('state',undefined,cookie)).json();assert.equal(state.records.length,96);
 const updated=await request('record',{...state.records[0],rating:'◎',note:'local persistence check'},cookie);assert.equal(updated.status,200);
 assert.equal((await request('favourite',{kind:'人',name:'作者'},cookie)).status,200);
 assert.equal((await request('reaction',{stage_id:'test-stage',status:'interest'},cookie)).status,200);
 const recovered=await request('recover',{code:recovery_code});assert.equal(recovered.status,200);
 const restored=await (await request('state',undefined,recovered.headers.get('set-cookie').split(';')[0])).json();
 assert.equal(restored.records[0].rating,'◎');assert.equal(restored.records[0].note,'local persistence check');assert.equal(restored.favourites[0].name,'作者');assert.equal(restored.reactions[0].status,'interest');
 const other=await request('register',{});assert.equal(other.status,200);
 const otherState=await (await request('state',undefined,other.headers.get('set-cookie').split(';')[0])).json();assert.equal(otherState.records.length,0);assert.equal(otherState.reactions.length,0);
 assert.equal((await request('record',{title:'bad',date:'2026-01-01'})).status,401);
 console.log('Local workerd/D1: 96-record import, rating, note, favourites, reactions, recovery and account isolation passed.');
} finally {
 try{process.kill(-server.pid,'SIGTERM');}catch(e){if(e.code!=='ESRCH')throw e;}
 await new Promise(resolve=>{if(server.exitCode!==null)resolve();else {const timeout=setTimeout(()=>{try{process.kill(-server.pid,'SIGKILL');}catch{}resolve();},3000);server.once('exit',()=>{clearTimeout(timeout);resolve();});}});
}
