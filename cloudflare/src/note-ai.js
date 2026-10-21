// 感想を AI（Claude Haiku 5.5）で読み取り、感想の好み（impression.js）に使う（起案者の指示 2026-10-21「apiの呼び出しが
// 月100$無料らしいので、ユーザが書いた感想をclaudeのapiで分析して推薦に組み込むようにしたい」「感想を送信することに
// チェックした場合のみ可能（設定画面に同意非同意つくって）」「haikuにしたい」、dec-note-ai）。
//
// - 設定の「感想の AI 読み取り」で同意した人（app_setting の note_ai='1'）の感想だけを送る。既定は送らない
// - 送るのは夜の定期実行（worker.js の scheduled）だけ。画面を開いたときには呼ばない。鍵（ANTHROPIC_API_KEY）が無ければ何もしない
// - 送るのは感想の本文と、その公演に付いた種類の言葉（#題材 など。impression.js が見る言葉と同じ）だけ。名前・アカウント・
//   公演名・作品の番号は送らない。答えは「候補の番号と + / -」だけにして、出る言葉の数を抑える
// - 1 つの感想は 1 度だけ読む（文の印 note_hash が変わったときだけ読み直す）。結果は note_ai に置き、推薦の計算は D1 を読むだけ
// - 1 回の問い合わせに 20 件をまとめる。月の言葉の数に上限（NOTE_AI_TOKENS_CAP）を置き、越える月は送らない
import {splitMark} from './x-post.js';
import {CONTENT_AXES} from './recommend.js';
import {ValueError} from './screens/py.js';

export const NOTE_AI_KEY = 'note_ai';
export const NOTE_AI_MODEL = 'claude-haiku-5-5';
export const PROMPT_VER = 'v1';
export const PER_REQUEST = 20;          // 1 回の問い合わせにまとめる感想の数
export const REQUESTS_PER_NIGHT = 10;   // 1 晩の問い合わせの数（1 晩 200 件まで。無料の Worker の外への問い合わせは 1 回 50 まで）
export const NOTE_AI_TOKENS_CAP = 5_000_000;   // 1 か月の入出力の言葉の数（Haiku 5.5 で約 0.6 ドル。月 100 ドルの枠の 1% 未満）
const MIN_CHARS = 8;                    // これより短い感想は送らない（読み取れる特徴がほぼ無い）
const MAX_CANDIDATES = 30;

export const SYSTEM = `観劇の感想から、候補の特徴への評価だけを抜き出す。
入力は 1 行に 1 件、「番号|候補:番号と言葉…|感想:本文」。
出力は 1 行に 1 件、「番号:候補番号と符号」を空白で区切る。符号は + が良かった・好き、- が良くなかった・苦手。
感想にその特徴への評価がはっきり書かれているときだけ出す。触れているだけ・推量・他人の意見は出さない。否定（「〜は良くなかった」「〜ではない」）に注意する。
該当が無ければ「番号:」だけ書く。それ以外の文字は書かない。
例）
入力: 1|候補:1家族 2戦争|感想:家族の話に弱いので泣いた。戦争の場面は長く感じた
出力: 1:1+ 2-`;

/** 感想の文の印（FNV-1a 32 ビット）。出どころの行（X のポスト）を外した本文で取る */
export function noteHash(note) {
  const s = splitMark(note).body.trim();
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h.toString(16).padStart(8, '0');
}

// ---------------------------------------------------------------- 設定（同意・非同意）

export async function consented(ctx) {
  const row = await ctx.db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, NOTE_AI_KEY).first();
  return row?.value === '1';
}

export function consentCardHtml(on, head) {
  return `<details class="card">${head}
<p class="lead"><b>同意すると、書いた感想を AI（Anthropic の Claude）に送り、</b>どの題材・形式などを良いと感じたかを読み取って、おすすめに使います。
送るのは感想の本文と、その公演に付いた題材などの言葉だけです。名前・アカウント・公演名は送りません。
読み取りは夜にまとめて行い、同じ感想は 1 度だけ送ります（書き直したときは読み直します）。<br>
<b>同意しない場合は、感想を AI に送りません。</b>感想はこれまでどおり、たぐりの中の決まりだけで読み取ります。
同意はいつでもやめられ、やめると読み取った結果を消します。<a href="/privacy">プライバシーポリシー</a>の第 5 条にも書いてあります。</p>
<form class="pfil" id="note-ai-setting" data-nosubmit>
<div class="pchips"><label class="pchip${on ? ' on' : ''}"><input type="radio" name="note_ai" value="1"${on ? ' checked' : ''}><span class="pl">同意する（感想を AI に送る）</span></label>
<label class="pchip${on ? '' : ' on'}"><input type="radio" name="note_ai" value="0"${on ? '' : ' checked'}><span class="pl">同意しない（送らない）</span></label></div>
<div class="pfoot"><button type="button" data-set-note-ai="1">これにする</button><span class="said"></span></div>
</form></details>`;
}

/** POST /api/note_ai {on: true|false}。やめるときは読み取った結果と、それを使ったおすすめの控えを消す */
export async function consentAction(b, ctx) {
  if (typeof b?.on !== 'boolean') throw new ValueError('on（true か false）が要る');
  const at = new Date(ctx.now).toISOString();
  const cmds = [ctx.db.prepare('INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at')
    .bind(ctx.uid, NOTE_AI_KEY, b.on ? '1' : '0', at)];
  if (!b.on) cmds.push(ctx.db.prepare('DELETE FROM note_ai WHERE user_id=?').bind(ctx.uid),
    ctx.db.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(ctx.uid));
  await ctx.db.batch(cmds);
  return {body: {ok: true, on: b.on}};
}

// ---------------------------------------------------------------- 推薦の計算から読む

/**
 * 本人が同意していれば、読み取った結果 work_key -> {hash, feats: [[言葉, 1|-1]]}。同意していなければ null。
 * 1 回の読み出し（同意の設定と結果を 1 文で）。impression.impressionAdjust に渡す
 */
export async function noteAiFor(ctx) {
  const {results} = await ctx.db.prepare(`SELECT a.work_key, a.note_hash, a.feats FROM note_ai a
    WHERE a.user_id=?1 AND a.status='ok' AND EXISTS (SELECT 1 FROM app_setting s WHERE s.user_id=?1 AND s.key='${NOTE_AI_KEY}' AND s.value='1')`)
    .bind(ctx.uid).all();
  if (!results.length) return null;
  const out = new Map();
  for (const r of results) {
    try { out.set(r.work_key, {hash: r.note_hash, feats: JSON.parse(r.feats)}); } catch { /* 壊れた行は使わない */ }
  }
  return out;
}

// ---------------------------------------------------------------- 夜の読み取り

/** 1 回の問い合わせの本文（番号は 1 から。候補は番号と言葉をつなげて書く） */
export function buildBatch(items) {
  return items.map((it, i) => `${i + 1}|候補:${it.cands.map((w, j) => `${j + 1}${w}`).join(' ')}|感想:${it.body.replace(/\s+/gu, ' ')}`).join('\n');
}

/** 答えを読む。items と同じ並びで [[言葉, 1|-1]] か null（その番号の行が無い・形が崩れている） */
export function parseBatch(text, items) {
  const out = items.map(() => null);
  for (const line of String(text || '').split('\n')) {
    const m = /^\s*(\d+)\s*[:：](.*)$/u.exec(line);
    if (!m) continue;
    const i = Number(m[1]) - 1;
    if (!(i >= 0 && i < items.length) || out[i]) continue;
    const feats = [], seen = new Set();
    let ok = true;
    for (const tok of m[2].trim().split(/\s+/u).filter(Boolean)) {
      const t = /^(\d+)([+\-＋－])$/u.exec(tok);
      const w = t && items[i].cands[Number(t[1]) - 1];
      if (!w) { ok = false; break; }
      if (seen.has(w)) continue;
      seen.add(w);
      feats.push([w, t[2] === '+' || t[2] === '＋' ? 1 : -1]);
    }
    if (ok) out[i] = feats;
  }
  return out;
}

const month = now => new Date(now).toISOString().slice(0, 7);

/**
 * 読み取る感想を選ぶ: 同意した人の、本文がある・公演に結び付いた記録のうち、まだ読んでいない（文の印が違う・読みの版が違う）もの。
 * 候補の言葉はその公演の種類の言葉（impression.js と同じ CONTENT_AXES の軸）。候補が無い感想は送らずに 'none' にする
 */
export async function pendingNotes(db, limit) {
  // まだ読んでいない・読んだ後に書き直した・読みの版が違う記録だけを D1 で選ぶ（全員の感想を毎晩 Worker で回さない。
  // 無料の Worker は定期実行も CPU 10 ミリ秒まで）。文の印は選んだ分だけ計算し、同じ文なら読み直さない
  const {results} = await db.prepare(`SELECT w.user_id, w.work_key, w.stage_id, w.note_impression, a.note_hash, a.prompt_ver
    FROM app_setting s JOIN works w ON w.user_id=s.user_id
    LEFT JOIN note_ai a ON a.user_id=w.user_id AND a.work_key=w.work_key
    WHERE s.key='${NOTE_AI_KEY}' AND s.value='1' AND trim(COALESCE(w.note_impression,''))<>'' AND COALESCE(w.stage_id,'')<>''
      AND (a.work_key IS NULL OR a.prompt_ver<>?1 OR replace(COALESCE(w.updated_at,''),' ','T')>a.analyzed_at)
    LIMIT ?2`).bind(PROMPT_VER, limit * 2).all();
  const todo = [];
  for (const r of results) {
    const hash = noteHash(r.note_impression);
    if (r.note_hash === hash && r.prompt_ver === PROMPT_VER) continue;
    todo.push({user_id: r.user_id, work_key: r.work_key, stage_id: String(r.stage_id), body: splitMark(r.note_impression).body.trim(), hash, cands: []});
    if (todo.length >= limit) break;
  }
  if (!todo.length) return [];
  // 候補の言葉は、その公演の種類の言葉（impression.js と同じ CONTENT_AXES の軸）。索引（rec_people）に無い公演は
  // 過去の公演（past_stage）から読む（recommend.d1Access.peopleFor と同じ順）。D1 の json_each で軸を絞って読む
  const sids = [...new Set(todo.map(t => t.stage_id))];
  const words = new Map();
  const axes = CONTENT_AXES.map(() => '?').join(',');
  const read = async (from, ids) => {
    for (let i = 0; i < ids.length; i += 80) {
      const part = ids.slice(i, i + 80);
      const {results: rows} = await db.prepare(`SELECT p.stage_id, json_extract(j.value,'$[1]') AS w FROM ${from} p, json_each(p.people) j
        WHERE p.stage_id IN (${part.map(() => '?').join(',')}) AND json_valid(p.people) AND json_extract(j.value,'$[0]') IN (${axes})`
        + (from === 'rec_people' ? " AND p.ver=(SELECT v FROM rec_meta WHERE k='current')" : ''))
        .bind(...part, ...CONTENT_AXES).all();
      for (const r of rows) {
        const sid = String(r.stage_id);
        if (!words.has(sid)) words.set(sid, []);
        if (r.w && !words.get(sid).includes(String(r.w))) words.get(sid).push(String(r.w));
      }
    }
  };
  await read('rec_people', sids);
  const rest = sids.filter(s => !words.has(s));
  if (rest.length) { try { await read('past_stage', rest); } catch { /* past_stage の無い手元の D1 */ } }
  for (const t of todo) t.cands = (words.get(t.stage_id) || []).slice(0, MAX_CANDIDATES);
  return todo;
}

/**
 * 夜の読み取り（worker.js の scheduled から）。client は試験で差し替える（既定は Anthropic の SDK）。
 * 返り値は {sent, saved, stopped}。鍵が無い・同意した人がいない・月の上限を越えた夜は何も送らない
 */
export async function runNoteAi(env, {client = null, now = Date.now()} = {}) {
  if (!env.ANTHROPIC_API_KEY && !client) return {sent: 0, saved: 0, stopped: 'no-key'};
  const db = env.DB;
  const usageKey = `note_ai_tokens:${month(now)}`;
  const used = (await db.prepare('SELECT n FROM usage WHERE k=?').bind(usageKey).first())?.n || 0;
  if (used >= NOTE_AI_TOKENS_CAP) return {sent: 0, saved: 0, stopped: 'cap'};
  const todo = await pendingNotes(db, PER_REQUEST * REQUESTS_PER_NIGHT);
  if (!todo.length) return {sent: 0, saved: 0, stopped: null};
  const at = new Date(now).toISOString();
  const rows = [];                         // [user_id, work_key, hash, feats, status]
  const send = [];
  for (const t of todo) {
    if (!t.cands.length || [...t.body].length < MIN_CHARS) rows.push([t.user_id, t.work_key, t.hash, [], 'none']);
    else send.push(t);
  }
  let sent = 0, tokens = 0, stopped = null;
  if (send.length) {
    // SDK はここで初めて読む（画面の要求ごとの起動に SDK の読み込みを足さない）
    const api = client || new (await import('@anthropic-ai/sdk')).default({apiKey: env.ANTHROPIC_API_KEY, maxRetries: 2});
    for (let i = 0; i < send.length; i += PER_REQUEST) {
      if (used + tokens >= NOTE_AI_TOKENS_CAP) { stopped = 'cap'; break; }
      const items = send.slice(i, i + PER_REQUEST);
      let res;
      try {
        res = await api.messages.create({
          model: NOTE_AI_MODEL,
          max_tokens: 40 * items.length + 64,
          // 番号と符号だけを返す仕事なので考える段を外し、手間は最小にする（Haiku 5.5 は low で disabled を受け付ける）
          thinking: {type: 'disabled'},
          output_config: {effort: 'low'},
          system: SYSTEM,
          messages: [{role: 'user', content: buildBatch(items)}],
        });
      } catch (e) {
        // 回数制限・残高切れ・鍵の誤りなど。続けても同じなので、その夜はやめる（読めなかった感想は次の夜に回る）
        console.error('note_ai', e?.status || '', e?.name || '', String(e?.message || '').slice(0, 200));
        stopped = 'error';
        break;
      }
      sent += 1;
      tokens += (res.usage?.input_tokens || 0) + (res.usage?.output_tokens || 0);
      if (res.stop_reason === 'refusal') {
        for (const it of items) rows.push([it.user_id, it.work_key, it.hash, [], 'refused']);
        continue;
      }
      const text = (res.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n');
      const parsed = parseBatch(text, items);
      items.forEach((it, j) => rows.push([it.user_id, it.work_key, it.hash, parsed[j] || [], parsed[j] ? (parsed[j].length ? 'ok' : 'none') : 'bad']));
    }
  }
  const cmds = rows.map(([uid, wk, hash, feats, status]) => db.prepare(`INSERT INTO note_ai(user_id,work_key,note_hash,feats,status,model,prompt_ver,analyzed_at)
    SELECT ?1,?2,?3,?4,?5,?6,?7,?8 WHERE EXISTS (SELECT 1 FROM app_setting WHERE user_id=?1 AND key='${NOTE_AI_KEY}' AND value='1')
    ON CONFLICT(user_id,work_key) DO UPDATE SET note_hash=excluded.note_hash, feats=excluded.feats, status=excluded.status,
      model=excluded.model, prompt_ver=excluded.prompt_ver, analyzed_at=excluded.analyzed_at`)
    .bind(uid, wk, hash, JSON.stringify(feats), status, NOTE_AI_MODEL, PROMPT_VER, at));
  // 結果が変わった人のおすすめの控えを消し、次に開いたときに計算し直す
  for (const uid of new Set(rows.filter(r => r[4] === 'ok').map(r => r[0]))) cmds.push(db.prepare('DELETE FROM rec_cache WHERE user_id=?').bind(uid));
  if (tokens) cmds.push(db.prepare('INSERT INTO usage(k,n) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET n=n+excluded.n').bind(usageKey, tokens));
  for (let i = 0; i < cmds.length; i += 50) await db.batch(cmds.slice(i, i + 50));
  return {sent, saved: rows.length, stopped};
}
