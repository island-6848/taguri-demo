// 記録を見返す: the material the three screens share (app._records_base) and the screens
// themselves (起案者の指示 2026-10-14「残りの画面も順に移して」).
import {isScaled} from './grade.js';
import {loadWorks} from './works.js';
import {peopleByKey, recordsLede, autoMerge} from './diary.js';
import {autoLink, pastStages} from './autolink.js';
import {strip} from './py.js';
import {panel as chroniclePanel} from './chronicle.js';
<<<<<<< cloudflare/src/screens/records.js
import {spiralPanel, venuePanel} from './charts.js';
import {comparisonPopulation, personalComparison, fourPanels} from './compare-four.js';
=======
import {spiralPanel} from './charts.js';
import {craftRows, panel as comparePanel, popNote, population} from './compare.js';
>>>>>>> /tmp/four-master-0
import {RECORDS_EMPTY} from './diary.js';
import {localNow} from './py.js';
import {timetableFor} from './timetable.js';
import {conquestFor} from './conquest.js';

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
  const rated = ws.filter(w => GRADES.includes(w.verdict) || isScaled(w.verdict));
  const people = await peopleByKey(ctx, rated);
  const venues = await venuesOf(ctx, rated.map(w => w.stage_id));
  return rated.map(w => ({key: w.work_key, title: w.title, date: w.first_date || '', verdict: w.verdict, stage_id: w.stage_id || '',
    times: w.times || 1, people: (people[w.work_key] || []).slice().sort((a, b) => cmp(a[0], b[0]) || cmp(a[1], b[1])),
    venues: venues[w.stage_id] ? [venues[w.stage_id]] : [], manual: true}));
}

/** app._records_base */
export async function recordsBase(ctx) {
  await autoLink(ctx);
  let ws = await loadWorks(ctx);
  if ((await autoMerge(ctx, ws)).length) ws = await loadWorks(ctx);   // 同じ作品の記録を自動でまとめる（diary.autoMerge）
  const seen = ws.filter(w => !w.unseen);
  return {ws, seen, rated: await ratedRows(ctx, seen), nSkip: ws.length - seen.length,
    nRated: seen.filter(w => w.verdict).length, nNotes: seen.filter(w => strip(w.note_impression || '')).length};
}

/** stage_id -> #題材 の言葉（索引 rec_people、無ければ過去の公演 past_stage）。年表の題材に使う（issue #177） */
async function themesOf(ctx, sids) {
  const want = [...new Set(sids.filter(Boolean).map(String))], out = {};
  const pick = (sid, people) => {
    try { const ws = JSON.parse(people || '[]').filter(p => p[0] === '#題材').map(p => p[1]); if (ws.length) out[sid] = ws; } catch { /* broken row */ }
  };
  for (let i = 0; i < want.length; i += 90) {
    const part = want.slice(i, i + 90);
    const {results} = await ctx.db.prepare(`SELECT stage_id, people FROM rec_people WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) pick(r.stage_id, r.people);
  }
  const rest = want.filter(s => !out[s]);
  for (let i = 0; i < rest.length; i += 90) {
    const part = rest.slice(i, i + 90);
    let results = [];
    try { ({results} = await ctx.db.prepare(`SELECT stage_id, people FROM past_stage WHERE stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all()); } catch { break; }
    for (const r of results) pick(r.stage_id, r.people);
  }
  return out;
}

export async function chronicleScreen(_params, ctx) {
  const d = await recordsBase(ctx);
  const themes = await themesOf(ctx, d.rated.map(r => r.stage_id));
  for (const r of d.rated) r.themes = themes[r.stage_id] || [];
  const main = chroniclePanel(d.seen, d.rated) || '<section class="card"><p class="empty">まだ年表を描けるだけの記録がありません。上演日の分かる記録が増えると出るようになります。</p></section>';
  return {title: '観劇史年表', body_html: `<h1>観劇史年表 ── 何が始まった年か</h1>
${recordsLede(d)}
${main}`};
}

const COMPARE_EMPTY = '<p class="pnow">まだ比べられません。'
  + 'ここはこれから観られる公演の一覧と観た記録を並べて差を出す画面なので、'
  + '記録が入ると出るようになります。</p>';
// JSON inside <script>: no "</script>" or "<!--" can end it early.
const scriptJson = x => JSON.stringify(x).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');

/**
 * app._records_body for a visitor (owner=False): 年輪・劇場・人の流れ・相関図 and
 * 比べる. The map is left out (no venue coordinates in D1, Python draws none
 * without them either), and so is 題材の偏り (compare.js says why).
 *
 * 人の流れ and 相関図 are too heavy for the Worker's 10 ms of CPU: the rated rows go
 * to the page in #figs-src and figs.js draws them in the browser into [data-fig]
 * (web/app.js fixupFigs). d3 is loaded by the page itself when #sl-data appears.
 */
export async function recordsScreen(_params, ctx) {
  const d = await recordsBase(ctx);
  let cmpPanels = '';
  if (d.seen.length) {
    try {
      const world = await comparisonPopulation(ctx.db, ctx.today || localNow().slice(0, 10));
      const mine = await personalComparison(ctx, d.seen);
      cmpPanels = fourPanels(mine, world);
    } catch {
      cmpPanels = '<p class="empty">比較データを読み込めませんでした。時間をおいて開き直してください。</p>';
    }
  }
  let timetable = '';
  try { timetable = await timetableFor(ctx, d.seen, localNow().slice(0, 10)); } catch { /* 時間割は無くても画面は出す */ }
  let conquest = '';
  try { conquest = await conquestFor(ctx, d.seen); } catch { /* 制覇マップは無くても画面は出す */ }
  const body = `<h1>眺める ── 図で見る</h1>
${recordsLede(d)}
${d.seen.length ? '' : RECORDS_EMPTY}
<div class="figs">
${spiralPanel(d.seen)}
${timetable}
${conquest}

<div data-fig="storyline"></div>
</div>
<script id="figs-src" type="application/json">${scriptJson({rated: d.rated})}</script>
<h2>比べる ── 掲載公演と自分の観劇</h2>
<p class="lede">クレジット・題材・地域・公演期間を、割合と件数で比べます。</p>
${d.seen.length ? '' : COMPARE_EMPTY}
<div class="figs">${cmpPanels}</div>`;
  return {title: '眺める', body_html: body};
}

export const recordScreens = {screens: {records: recordsScreen, chronicle: chronicleScreen}, actions: {}};
