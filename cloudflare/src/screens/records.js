// 記録を見返す: the material the three screens share (app._records_base) and the screens
// themselves (起案者の指示 2026-10-14「残りの画面も順に移して」).
import {loadWorks} from './works.js';
import {peopleByKey, recordsLede} from './diary.js';
import {autoLink, pastStages} from './autolink.js';
import {loadDeclared} from './lists.js';
import {strip} from './py.js';
import {body as traceBody} from './trace.js';
import {panel as chroniclePanel} from './chronicle.js';

const GRADES = ['◎', '○', '△', '×'];
const norm = s => strip(String(s || '').normalize('NFKC'));
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/** Theatre (劇場) of the linked stages, normalised like measure_nets.norm. */
async function venuesOf(ctx, sids) {
  const want = [...new Set(sids.filter(Boolean))], out = {};
  for (let i = 0; i < want.length; i += 90) {
    const part = want.slice(i, i + 90);
    const {results} = await ctx.db.prepare(`SELECT stage_id, entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) { try { const v = norm((JSON.parse(r.entry || '{}').fields || {})['劇場'] || ''); if (v) out[r.stage_id] = v; } catch { /* no fields */ } }
  }
  const past = await pastStages(ctx.db, want.filter(s => !out[s]));
  for (const [sid, p] of Object.entries(past)) if (p.venue) out[sid] = norm(p.venue);
  return out;
}

/**
 * measure_nets.load_rated for a public user (manual works only): the rated works with
 * the credits of their linked stage plus the hand-entered ones.
 */
export async function ratedRows(ctx, ws) {
  const rated = ws.filter(w => GRADES.includes(w.verdict));
  const people = await peopleByKey(ctx, rated);
  const venues = await venuesOf(ctx, rated.map(w => w.stage_id));
  return rated.map(w => ({key: w.work_key, title: w.title, date: w.first_date || '', verdict: w.verdict, stage_id: w.stage_id || '',
    times: w.times || 1, people: (people[w.work_key] || []).slice().sort((a, b) => cmp(a[0], b[0]) || cmp(a[1], b[1])),
    venues: venues[w.stage_id] ? [venues[w.stage_id]] : [], manual: true}));
}

/** app._records_base */
export async function recordsBase(ctx) {
  await autoLink(ctx);
  const ws = await loadWorks(ctx);
  const seen = ws.filter(w => !w.unseen);
  return {ws, seen, rated: await ratedRows(ctx, seen), nSkip: ws.length - seen.length,
    nRated: seen.filter(w => w.verdict).length, nNotes: seen.filter(w => strip(w.note_impression || '')).length};
}

export async function traceScreen(params, ctx) {
  const d = await recordsBase(ctx);
  let main;
  try {
    main = traceBody(d.rated, params.get('name') || '', params.get('via') || '', await loadDeclared(ctx));
  } catch {
    main = '<section class="card"><p class="empty">この線は、いまの記録では組めませんでした。観た公演が増えると出るようになります。</p></section>';
  }
  const body = `<h1>たどる ── 1 つの名前をたどる</h1>
${recordsLede(d)}
<p class="lede">名前を1つ選ぶと、<b>その名前をいつ知って、何につながったか</b>が出ます。何本観たか、どの劇場が多いかは「眺める」で見られます。</p>
${main}`;
  return {title: 'たどる', body_html: body};
}

export async function chronicleScreen(_params, ctx) {
  const d = await recordsBase(ctx);
  const main = chroniclePanel(d.seen, d.rated) || '<section class="card"><p class="empty">まだ年表を描けるだけの記録がありません。上演日の分かる記録が増えると出るようになります。</p></section>';
  return {title: '観劇史年表', body_html: `<h1>観劇史年表 ── 何が始まった年か</h1>
${recordsLede(d)}
${main}`};
}

export const recordScreens = {screens: {trace: traceScreen, chronicle: chronicleScreen}, actions: {}};
