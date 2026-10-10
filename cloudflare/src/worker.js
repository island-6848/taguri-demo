const MAX_BODY = 262144;
const COOKIE = 'taguri_session';
const TTL = 60 * 60 * 24 * 30;
const json = (value, status = 200, headers = {}) => Response.json(value, {status, headers: {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers}});
const fail = (status, message) => { throw Object.assign(new Error(message), {status}); };
const token = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2,'0')).join('');
const hash = async s => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))), b => b.toString(16).padStart(2,'0')).join('');
const now = () => Math.floor(Date.now() / 1000);
const cookie = value => `${COOKIE}=${value}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${TTL}`;
function string(value, max, required = false) {
  if (typeof value !== 'string' || value.length > max || (required && !value.trim())) fail(400, '入力を確認してください。');
  return value.trim();
}
function record(value) {
  if (!value || typeof value !== 'object') fail(400, '記録を確認してください。');
  const r = {id: string(value.id ?? crypto.randomUUID(), 100, true), title: string(value.title, 500, true), date: string(value.date, 10, true), time: string(value.time ?? '', 5), venue: string(value.venue ?? '', 300), rating: string(value.rating ?? '', 2), note: string(value.note ?? '', 4000)};
  const parsed = new Date(`${r.date}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date) || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0,10) !== r.date) fail(400,'日付を確認してください。');
  if (r.time && !/^([01]\d|2[0-3]):[0-5]\d$/.test(r.time)) fail(400,'時刻を確認してください。');
  if (!['','◎','○','△','×'].includes(r.rating)) fail(400,'評価を確認してください。');
  return r;
}
function favourite(value) {
  const f = {name: string(value?.name, 200, true), kind: string(value?.kind, 20, true)};
  if (!['人','団体','作品','題材'].includes(f.kind)) fail(400, '種類を確認してください。');
  return f;
}
async function body(request) {
  if (!request.headers.get('content-type')?.startsWith('application/json')) fail(415,'JSON形式で送信してください。');
  const reader = request.body?.getReader();
  if (!reader) fail(400,'入力がありません。');
  let size = 0; const chunks = [];
  while (true) { const {done,value} = await reader.read(); if (done) break; size += value.byteLength; if (size > MAX_BODY) { await reader.cancel(); fail(413,'ファイルが大きすぎます。'); } chunks.push(value); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) {bytes.set(chunk,offset); offset += chunk.length;}
  try {return JSON.parse(new TextDecoder().decode(bytes));} catch {fail(400,'JSONを読み取れませんでした。');}
}
async function user(request, db) {
  const raw = request.headers.get('cookie')?.match(/(?:^|;\s*)taguri_session=([a-f0-9]{64})(?:;|$)/)?.[1];
  if (!raw) fail(401,'復旧コードでログインするか、新しく始めてください。');
  const session = await db.prepare('SELECT user_id FROM sessions WHERE hash=? AND expires_at>?').bind(await hash(raw),now()).first();
  if (!session) fail(401,'ログインし直してください。');
  return session.user_id;
}
function upsert(db, uid, r) {
  return db.prepare('INSERT INTO records(user_id,id,title,date,time,venue,rating,note,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,id) DO UPDATE SET title=excluded.title,date=excluded.date,time=excluded.time,venue=excluded.venue,rating=excluded.rating,note=excluded.note,updated_at=excluded.updated_at').bind(uid,r.id,r.title,r.date,r.time,r.venue,r.rating,r.note,now());
}
async function state(db, uid) {
  const result = await db.batch([db.prepare('SELECT id,title,date,time,venue,rating,note FROM records WHERE user_id=? ORDER BY date DESC,id LIMIT 500').bind(uid),db.prepare('SELECT name,kind FROM favourites WHERE user_id=? ORDER BY kind,name LIMIT 200').bind(uid)]);
  return {version:1,records:result[0].results,favourites:result[1].results};
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    try {
      const path = url.pathname; const method = request.method;
      if (method !== 'GET' && method !== 'POST') fail(405,'対応していない操作です。');
      if (method === 'POST' && request.headers.get('origin') !== url.origin) fail(403,'同じサイトから操作してください。');
      if (method === 'GET' && path === '/api/catalogue') {
        // Public catalogue only: never include an owner's ranking or private reasons.
        const rows = await env.DB.prepare('SELECT id,title,date,venue,url FROM catalogue WHERE date>=? ORDER BY date,id LIMIT 100').bind(new Date().toISOString().slice(0,10)).all();
        return json({items:rows.results});
      }
      if (method === 'POST' && ['/api/register','/api/recover'].includes(path)) {
        const input = await body(request);
        let uid; let recovery;
        if (path === '/api/register') {
          if (env.ALLOW_REGISTRATION !== 'true') fail(503,'新規登録を一時停止しています。');
          recovery = token(); uid = crypto.randomUUID();
        } else {
          const code = string(input.code, 80, true).replaceAll('-', '').toLowerCase();
          if (!/^[a-f0-9]{64}$/.test(code)) fail(401,'復旧コードを確認してください。');
          uid = (await env.DB.prepare('SELECT id FROM users WHERE recovery_hash=?').bind(await hash(code)).first())?.id;
          if (!uid) fail(401,'復旧コードを確認してください。');
        }
        const session = token();
        const commands = [];
        if (recovery) commands.push(env.DB.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').bind(uid,await hash(recovery),now()));
        // Delete expired sessions and bound the number of devices per account.
        commands.push(env.DB.prepare('DELETE FROM sessions WHERE user_id=? AND (expires_at<=? OR hash NOT IN (SELECT hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT 9))').bind(uid,now(),uid));
        commands.push(env.DB.prepare('INSERT INTO sessions(hash,user_id,expires_at) VALUES(?,?,?)').bind(await hash(session),uid,now()+TTL));
        await env.DB.batch(commands);
        return json({recovery_code:recovery},200,{'Set-Cookie':cookie(session)});
      }
      const uid = await user(request,env.DB);
      if (method === 'GET' && ['/api/state','/api/export'].includes(path)) return json(await state(env.DB,uid));
      if (method !== 'POST') fail(404,'見つかりませんでした。');
      const input = await body(request);
      if (path === '/api/record') {
        const r = record(input);
        const existing = await env.DB.prepare('SELECT id FROM records WHERE user_id=? AND id=?').bind(uid,r.id).first();
        const count = (await env.DB.prepare('SELECT count(*) AS n FROM records WHERE user_id=?').bind(uid).first()).n;
        if (!existing && count >= 500) fail(409,'記録は500件まで保存できます。');
        await upsert(env.DB,uid,r).run(); return json({record:r});
      }
      if (path === '/api/record/delete') {
        await env.DB.prepare('DELETE FROM records WHERE user_id=? AND id=?').bind(uid,string(input.id,100,true)).run(); return json({ok:true});
      }
      if (path === '/api/favourite') {
        const f = favourite(input);
        if (input.remove === true) await env.DB.prepare('DELETE FROM favourites WHERE user_id=? AND name=? AND kind=?').bind(uid,f.name,f.kind).run();
        else {
          const count = (await env.DB.prepare('SELECT count(*) AS n FROM favourites WHERE user_id=?').bind(uid).first()).n;
          if (count >= 200) fail(409,'お気に入りは200件まで保存できます。');
          await env.DB.prepare('INSERT OR IGNORE INTO favourites(user_id,name,kind) VALUES(?,?,?)').bind(uid,f.name,f.kind).run();
        }
        return json({ok:true});
      }
      if (path === '/api/import') {
        if (input.version !== 1 || !Array.isArray(input.records) || !Array.isArray(input.favourites) || input.records.length > 20 || input.favourites.length > 20) fail(400,'1回に記録20件・お気に入り20件まで取り込めます。');
        const rs = input.records.map(record), fs = input.favourites.map(favourite);
        // Additive import, never erase an existing account or trust input user IDs.
        const existing = await state(env.DB,uid);
        if (new Set([...existing.records.map(r=>r.id),...rs.map(r=>r.id)]).size>500 || new Set([...existing.favourites,...fs].map(f=>JSON.stringify([f.name,f.kind]))).size>200) fail(409,'保存件数の上限を超えています。');
        const commands = [...rs.map(r=>upsert(env.DB,uid,r)),...fs.map(f=>env.DB.prepare('INSERT OR IGNORE INTO favourites(user_id,name,kind) VALUES(?,?,?)').bind(uid,f.name,f.kind))];
        if(commands.length) await env.DB.batch(commands);
        return json({ok:true,imported:rs.length});
      }
      if (path === '/api/logout') {
        const raw = request.headers.get('cookie')?.match(/taguri_session=([a-f0-9]{64})/)?.[1];
        await env.DB.prepare('DELETE FROM sessions WHERE hash=? AND user_id=?').bind(await hash(raw),uid).run();
        return json({ok:true},200,{'Set-Cookie':`${COOKIE}=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0`});
      }
      fail(404,'見つかりませんでした。');
    } catch (error) {
      // Do not expose SQL, private records, or environment configuration.
      return json({error:error.status ? error.message : '保存先に接続できませんでした。時間を置いてもう一度お試しください。'},error.status ?? 503);
    }
  }
};
