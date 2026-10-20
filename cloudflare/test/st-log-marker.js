// システムテスト SC-06-01（docs/system-test-spec.md、S08）: 感想・Cookie・復旧コードが Worker のログに出ない。
// 本物の workerd（wrangler dev・まっさらな手元の D1）で、目印の文字列（TD-04）を感想・題名・劇場・お気に入りの
// 名前・修正依頼に入れて操作し、wrangler の出力を全部集めて探す。本番には繋がない。
//
//   cd cloudflare && node test/st-log-marker.js        # 出力の写しは $ST_LOG（既定は一時フォルダ）
//
// npm test には入れない（wrangler dev を起動し、30 秒ほどかかる）。手順書 P-07 の 3 で流す。
import {spawn, execFileSync} from 'node:child_process';
import {mkdtempSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {randomBytes} from 'node:crypto';
import {TERMS_VERSION} from '../src/terms.js';

const CF = new URL('..', import.meta.url).pathname;
const PORT = Number(process.env.ST_PORT || 8798), BASE = `http://127.0.0.1:${PORT}`;
const STATE = mkdtempSync(join(tmpdir(), 'taguri-st-log-d1-'));
const LOG = process.env.ST_LOG || join(STATE, 'wrangler.log');
const MARK = `STMARK-${new Date().toISOString().slice(0, 10)}-${randomBytes(4).toString('hex')}`;
const env = {...process.env, WRANGLER_SEND_METRICS: 'false', CI: '1'};

execFileSync('npx', ['wrangler', 'd1', 'migrations', 'apply', 'taguri-demo', '--local', '--persist-to', STATE], {cwd: CF, env, stdio: 'ignore'});
// 中継は切る（Render に要求を飛ばさない）
const server = spawn('npx', ['wrangler', 'dev', '--ip', '127.0.0.1', '--port', String(PORT), '--persist-to', STATE, '--var', 'ORIGINAL_UI_BRIDGE:false', '--log-level', 'debug'],
  {cwd: CF, env, detached: true, stdio: ['ignore', 'pipe', 'pipe']});
let logs = '';
for (const s of [server.stdout, server.stderr]) s.on('data', d => { logs += d.toString(); });

const call = (path, body, cookie = '') => fetch(BASE + path, body === undefined ? {headers: {cookie}} :
  {method: 'POST', headers: {origin: BASE, 'content-type': 'application/json', cookie}, body: JSON.stringify(body)});
const results = [];
const check = (name, ok, detail = '') => { results.push({name, ok, detail}); };
let code = 1;
try {
  let ready = false;
  for (let i = 0; i < 60 && !ready; i++) {
    if (server.exitCode !== null) throw new Error('wrangler dev が止まった:\n' + logs.slice(-3000));
    try { ready = (await fetch(BASE + '/api/health')).ok; } catch {}
    if (!ready) await new Promise(r => setTimeout(r, 1000));
  }
  if (!ready) throw new Error('wrangler dev が立ち上がらない:\n' + logs.slice(-3000));

  const reg = await call('/migration-api/register', {agree: TERMS_VERSION});
  const cookie = reg.headers.get('set-cookie').split(';')[0];
  const {recovery_code} = await reg.json();
  const sessionValue = cookie.split('=')[1];
  const steps = [
    ['/api/add_work', {title: `題 ${MARK}`, date: '2026-08-01', venue: `劇場 ${MARK}`}],
    ['/api/favourite', {action: 'add', kind: '人', name: `俳優 ${MARK}`}],
    ['/api/fix_request', {stage_id: '101', kind: '料金', message: `直して ${MARK}`}],
    ['/api/account', {display_name: MARK.slice(0, 30)}],
  ];
  const added = await (await call(...steps[0], cookie)).json();
  check('記録を足せた', Boolean(added.work_key), JSON.stringify(added).slice(0, 200));
  await call('/api/note', {work_key: added.work_key, note_impression: `感想 ${MARK}`}, cookie);
  for (const s of steps.slice(1)) await call(...s, cookie);
  await call('/api/recover', {code: '0'.repeat(64)});                  // 違う復旧コード（失敗のログ）
  await call('/api/recover', {code: recovery_code});                   // 正しい復旧コード
  await call('/api/note', {work_key: 'no-such-key', note_impression: `感想 ${MARK}`}, cookie);   // 失敗する書き込み
  for (const name of ['rate', 'works', 'notes', 'account', 'favourites']) await call(`/api/screen/${name}`, undefined, cookie);
  await new Promise(r => setTimeout(r, 1500));                        // ログが出きるのを待つ

  check('目印（感想・題名・劇場・お気に入り・修正依頼・表示名）がログに無い', !logs.includes(MARK), MARK);
  check('復旧コードがログに無い', !logs.includes(recovery_code));
  check('セッションの値がログに無い', !logs.includes(sessionValue));
  check('Cookie の見出しがログに無い', !/cookie:\s*\S/i.test(logs));
  // 要求の行が全部ログにあること（無ければ、探す先を間違えていて、上の確かめは何も見ていない）
  const lines = ['POST /migration-api/register 200', 'POST /api/add_work 200', 'POST /api/note 200', 'POST /api/recover 401', 'POST /api/note 400', 'GET /api/screen/rate 200'];
  const missing = lines.filter(l => !logs.includes(l));
  check('操作の要求の行がログにある（このログで探してよい）', missing.length === 0, missing.join(', '));
  code = results.every(r => r.ok) ? 0 : 1;
} catch (e) {
  results.push({name: '流せた', ok: false, detail: e.message.slice(0, 2000)});
} finally {
  try { process.kill(-server.pid, 'SIGTERM'); } catch {}
  writeFileSync(LOG, logs);
}
for (const r of results) console.log(`${r.ok ? 'OK' : 'NG'}  ${r.name}${r.detail && !r.ok ? '  ' + r.detail : ''}`);
console.log(`ログの写し: ${LOG}`);
process.exit(code);
