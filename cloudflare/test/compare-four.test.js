import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {comparisonPopulation, personalCounts, fourPanels, durationOf, personalComparison} from '../src/screens/compare-four.js';

function database() {
  const sql = new DatabaseSync(':memory:');
  sql.exec(`CREATE TABLE rec_meta(k TEXT PRIMARY KEY,v TEXT); INSERT INTO rec_meta VALUES('current','v1');
    CREATE TABLE rec_stage(ver TEXT,stage_id TEXT,start TEXT,end TEXT,entry TEXT,PRIMARY KEY(ver,stage_id));
    CREATE TABLE rec_people(ver TEXT,stage_id TEXT,people TEXT,PRIMARY KEY(ver,stage_id));
    CREATE TABLE past_stage(stage_id TEXT PRIMARY KEY,start TEXT,end TEXT,pref TEXT,people TEXT,title TEXT,venue TEXT,grp TEXT,synopsis TEXT);`);
  let calls=0;
  const db={prepare(s) { const st=sql.prepare(s);let args=[];const q={bind(...a){args=a;return q},async first(){calls++;return st.get(...args)},async all(){calls++;return {results:st.all(...args)}},async run(){calls++;return st.run(...args)}};return q }};
  const stage=(id,start,end,pref,people,ver='v1')=>{
    sql.prepare('INSERT INTO rec_stage VALUES(?,?,?,?,?)').run(ver,id,start,end,JSON.stringify({pref}));
    sql.prepare('INSERT INTO rec_people VALUES(?,?,?)').run(ver,id,JSON.stringify(people));
  };
  return {sql,db,stage,calls:()=>calls};
}

test('four axes count each eligible work once, including unrated records, and exclude missing metadata per axis',()=>{
  const works=[{work_key:'a',stage_id:'1',times:5},{work_key:'b',stage_id:'2'},{work_key:'c'}, {work_key:'a',stage_id:'1'}, {work_key:'future',unseen:true}];
  const meta={'1':{pref:'東京都',start:'2026-10-01',end:'2026-10-07',people:[['#題材','家族'],['#題材','家族'],['#題材','SF']]},'2':{pref:'海外',start:'2026-02-30',end:'2026-03-01',people:[]}};
  const mine=personalCounts(works,meta,{a:[['翻訳','A'],['翻訳','B']],b:[['出演','C']]});
  assert.equal(mine.total,3);assert.equal(mine.craft.n,2);assert.equal(mine.craft.counts.翻訳,1);
  assert.equal(mine.theme.n,1);assert.equal(mine.theme.counts.家族,1);assert.equal(mine.theme.counts.SF,1);
  assert.equal(mine.region.n,1);assert.equal(mine.region.counts.関東,1);
  assert.equal(mine.duration.n,1);assert.equal(mine.duration.counts['2〜7日'],1);
  for(const [s,e,label] of [['2024-02-29','2024-02-29','1日'],['2026-01-01','2026-01-08','8〜14日'],['2026-01-01','2026-01-15','15〜30日'],['2026-01-01','2026-01-31','31日以上'],['2026-02-30','2026-03-01',''],['2026-10-02','2026-10-01','']])assert.equal(durationOf(s,e),label);
});

test('DB aggregation deduplicates roles/tags, ignores stale versions and invalid dates, and reuses a shared cache',async()=>{
  const {sql,db,stage,calls}=database();
  stage('1','2024-02-29','2024-02-29','東京都',[['翻訳','A'],['翻訳','B'],['#題材','家族'],['#題材','家族']]);
  stage('2','2026-10-01','2026-10-08','大阪府',[['作曲','C'],['#題材','家族'],['#題材','SF']]);
  stage('3','2026-02-30','2026-03-01','海外',[]);
  stage('4','','','',[]);
  stage('old','2026-10-01','2026-10-01','東京都',[['原作','旧']], 'v0');
  const p=await comparisonPopulation(db,'2026-10-19');
  assert.equal(p.total,4);assert.equal(p.craft.n,2);assert.equal(p.craft.counts.翻訳,1);assert.equal(p.craft.counts.原作,undefined);
  assert.equal(p.theme.n,2);assert.equal(p.theme.counts.家族,2);assert.equal(p.theme.counts.SF,1);
  assert.equal(p.region.n,2);assert.equal(p.region.counts.関東,1);assert.equal(p.region.counts.近畿,1);
  assert.equal(p.duration.n,2);assert.equal(p.duration.counts['1日'],1);assert.equal(p.duration.counts['8〜14日'],1);
  const before=calls();assert.deepEqual(await comparisonPopulation(db,'2026-10-19'),p);assert.equal(calls()-before,2);
  assert.notEqual((await comparisonPopulation(db,'2026-10-20')).stamp,p.stamp);
  assert.ok(sql.prepare("SELECT length(v) n FROM rec_meta WHERE k='compare_four'").get().n<12000);
});

test('themes are bounded to the twelve most common DB tags; HTML escapes labels and shows missing-data explanations',async()=>{
  const {db,stage}=database();
  stage('1','2026-10-01','2026-10-03','東京都',Array.from({length:20},(_,i)=>['#題材',String(i).padStart(2,'0')]));
  const p=await comparisonPopulation(db,'2026-10-19');assert.equal(Object.keys(p.theme.counts).length,12);
  p.theme.counts={'<script>alert(1)</script>':1};
  const m=personalCounts([{work_key:'a',stage_id:'1'}],{'1':{people:[['#題材','<script>alert(1)</script>']]}},{});
  const html=fourPanels(m,p);assert.equal((html.match(/data-compare-axis=/g)||[]).length,4);
  assert.ok(!html.includes('<script>'));assert.ok(html.includes('&lt;script&gt;'));assert.ok(html.includes('不明で除外'));assert.ok(html.includes('同じ時期・地域に条件をそろえていません'));
  assert.ok(html.includes('データがまだ足りません'));assert.ok(html.includes('参考値'));
});

test('over-budget snapshots stop before the expensive aggregates and cache the stop for the day',async()=>{
  let expensive=0,writes=0,kept='';
  const db={prepare(s){return {bind(){return this},async first(){if(s.includes("k='current'"))return {v:'v'};if(s.includes("k='compare_four'"))return {v:kept};return {n:5001,pairs:100}},async all(){expensive++;return {results:[]}},async run(){writes++}}}};
  const p=await comparisonPopulation(db,'2026-10-19');assert.equal(p.unavailable,true);assert.equal(expensive,0);assert.equal(writes,1);
});

test('personal metadata and credits use current and past indexed stages, including unrated works',async()=>{
  const {sql,db,stage}=database();
  stage('1','2026-10-01','2026-10-01','東京都',[['翻訳','A'],['#題材','家族']]);
  sql.prepare('INSERT INTO past_stage VALUES(?,?,?,?,?,?,?,?,?)').run('2','2020-01-01','2020-01-31','大阪府',JSON.stringify([['原作','B'],['#題材','歴史']]),'過去','劇場','団体','');
  const works=[{work_key:'a',stage_id:'1'},{work_key:'b',stage_id:'2'}];
  const m=await personalComparison({db},works);
  assert.equal(m.total,2);assert.equal(m.craft.n,2);assert.equal(m.craft.counts.原作,1);
  assert.equal(m.theme.counts.歴史,1);assert.equal(m.region.counts.近畿,1);assert.equal(m.duration.counts['31日以上'],1);
});
