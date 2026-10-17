// 推薦を本番の利用者のデータで測るための記録（docs/research/real-data-eval-plan.md の §5・§7、migrations/0029）。
// - 答えの行に、そのときの順位・点・版を入れる（書き込みは増えない）
// - その日に出した公演の並びを、利用者 × 日 × 画面に 1 行だけ残す（rec_shown）
// - 設定の「推薦の改善の分析に使わない」（app_setting の analysis_optout）を選んだ人の分は、どちらも書かない
import {ValueError} from './py.js';

export const OPTOUT_KEY = 'analysis_optout';
export const SHOWN_KEEP_DAYS = 180;
export const SHOWN_MAX = 300;
// 1 行（利用者 × 日 × 画面）を書き直すのは 1 日にこの回数まで。答えるたびにカードが 1 枚入れ替わるので、
// 上限が無いと答えの数だけ書き込みが増える。2 画面で 1 人 1 日 12 行、300 人で 3,600 行（D1 の 1 日 10 万行の 3.6%）まで
export const SHOWN_WRITES_MAX = 6;
const SCREENS = new Set(['recommend', 'reminder']);

export async function optedOut(ctx) {
  const row = await ctx.db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, OPTOUT_KEY).first();
  return row?.value === '1';
}

/**
 * 答えた公演の順位・点・版（reaction の rank・score・ver）。おすすめの控え（rec_cache）の並びから引く
 * （whySnapshot と同じ 1 行の読み出しに、分析から外れる設定も一緒に読む）。控えが無い・外れる設定なら null。
 */
export async function answerSnapshot(ctx, stageId, screenVersion) {
  const row = await ctx.db.prepare(`SELECT body, (SELECT value FROM app_setting WHERE user_id=?1 AND key='${OPTOUT_KEY}') AS optout
    FROM rec_cache WHERE user_id=?1`).bind(ctx.uid).first();
  if (!row) return {body: null, eval: null};
  const body = JSON.parse(row.body);
  if (row.optout === '1') return {body, eval: null};
  const groups = body.groups || [];
  const i = groups.findIndex(g => g.stage_id === stageId || (g.venues || []).some(v => v.stage_id === stageId));
  const ver = `${screenVersion}|${body.ver || ''}`;
  return {body, eval: i < 0 ? {ver} : {rank: i + 1, score: groups[i].b ?? null, ver}};
}

/**
 * その日に画面に出した stage_id を rec_shown に足す。その日の行が既にあって、新しく出した公演が無ければ書かない
 * （読み出し 1 回だけ）。書き直しは 1 日 SHOWN_WRITES_MAX 回まで。その日の最初の行を書くときに、その人の古い行（SHOWN_KEEP_DAYS 日より前）を消す。
 */
export async function recordShown(ctx, screen, ids, ver = null) {
  if (!SCREENS.has(screen) || !ctx.uid) return false;
  const list = [...new Set(ids.map(String).filter(Boolean))];
  if (!list.length) return false;
  const row = await ctx.db.prepare(`SELECT ids, writes, (SELECT value FROM app_setting WHERE user_id=?1 AND key='${OPTOUT_KEY}') AS optout
    FROM users LEFT JOIN rec_shown ON rec_shown.user_id=users.id AND rec_shown.label=?2 AND rec_shown.screen=?3 WHERE users.id=?1`)
    .bind(ctx.uid, ctx.today, screen).first();
  if (!row || row.optout === '1' || (row.writes || 0) >= SHOWN_WRITES_MAX) return false;
  const had = row.ids ? JSON.parse(row.ids) : [];
  const seen = new Set(had);
  const merged = [...had, ...list.filter(s => !seen.has(s))].slice(0, SHOWN_MAX);
  if (merged.length === had.length) return false;
  const at = new Date(ctx.now).toISOString();
  const put = ctx.db.prepare(`INSERT INTO rec_shown(user_id,label,screen,ids,ver,updated_at) VALUES(?,?,?,?,?,?)
    ON CONFLICT(user_id,label,screen) DO UPDATE SET ids=excluded.ids, ver=excluded.ver, writes=rec_shown.writes+1, updated_at=excluded.updated_at`)
    .bind(ctx.uid, ctx.today, screen, JSON.stringify(merged), ver, at);
  if (row.ids) { await put.run(); return true; }
  const since = new Date(Date.parse(ctx.today + 'T00:00:00Z') - SHOWN_KEEP_DAYS * 86400000).toISOString().slice(0, 10);
  await ctx.db.batch([ctx.db.prepare('DELETE FROM rec_shown WHERE user_id=? AND label<?').bind(ctx.uid, since), put]);
  return true;
}

// ---------------------------------------------------------------- 設定のカード
export function optoutCardHtml(off, head) {
  return `<details class="card">${head}
<p class="lead">答え（興味あり・興味なし・購入済・行けない）・評価・公演の番号を、<b>運営者が手元でまとめて分析し、
おすすめの改善に使うことがあります。</b>感想・メモの本文と名前・メールアドレスは使いません。
結果は、利用者ごとの数（当たりの度合いなど）と全体の分布だけにして、1 人の記録が分かる形では出しません。<br>
<b>ここで「使わない」を選ぶと、分析から外します。</b>おすすめそのものの出し方は、どちらでも変わりません。
<a href="/terms">利用規約</a>の第 7 条と、<a href="/privacy">プライバシーの説明</a>の 4. にも書いてあります。</p>
<form class="pfil" id="analysis-setting" onsubmit="return false">
<div class="pchips"><label class="pchip${off ? '' : ' on'}"><input type="radio" name="analysis" value="0"${off ? '' : ' checked'}><span class="pl">分析に使ってよい</span></label>
<label class="pchip${off ? ' on' : ''}"><input type="radio" name="analysis" value="1"${off ? ' checked' : ''}><span class="pl">推薦の改善の分析に使わない</span></label></div>
<div class="pfoot"><button type="button" data-set-analysis="1">これにする</button><span class="said"></span></div>
</form></details>`;
}

/** POST /api/analysis_optout {off: true|false}。外れるときは、それまでに残した rec_shown も消す */
export async function optoutAction(b, ctx) {
  if (typeof b?.off !== 'boolean') throw new ValueError('off（true か false）が要る');
  const at = new Date(ctx.now).toISOString();
  const cmds = [ctx.db.prepare('INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at')
    .bind(ctx.uid, OPTOUT_KEY, b.off ? '1' : '0', at)];
  if (b.off) cmds.push(ctx.db.prepare('DELETE FROM rec_shown WHERE user_id=?').bind(ctx.uid));
  await ctx.db.batch(cmds);
  return {body: {ok: true, off: b.off}};
}
