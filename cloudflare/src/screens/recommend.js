// 今週のおすすめ: the recommend screen and the three-choice writes (react), answered by
// the Worker from D1 (起案者の指示 2026-10-14「おすすめの画面を移して」).
//
// Not a byte-for-byte port of app._recommend_body. The ranking is the Worker's
// (src/recommend.js, checked against user_recommender by test_recommend_index.py),
// computed from the user's works / favourites / reactions in D1. The cards are
// rendered once a day by the Python screen itself (scripts/build_cards.py,
// render_recommend.ticket) and stored in rec_card; here only the rank, the
// reasons (reason_rows) and the poster are filled in. Left out for now: the map
// above the prefecture chips, the 効かせ方 sliders (weight_form, its write is
// not ported), 出さない語 and the impression re-ranking.
import {scoreFromIndex, d1Access, seedsFromFavourites, gradeOf} from '../recommend.js';
import {chooseVariant} from '../reco-gate.js';
import {E, ValueError} from './py.js';
import {loadWorks} from './works.js';
import {compose, cardTemplates, posterHtml} from './cards.js';
import {loadDeclared, loadDeclined, nameHits, KINDS} from './lists.js';

export const TOP = 15;
// Groups kept per user between requests: enough to fill 15 cards in any one prefecture.
const KEEP = 400;
const VERSION = 'screen-v1';
export const PREFS = ['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
  '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
  '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県',
  '岐阜県', '静岡県', '愛知県', '三重県',
  '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
  '鳥取県', '島根県', '岡山県', '広島県', '山口県',
  '徳島県', '香川県', '愛媛県', '高知県',
  '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'];
const PREFS_KEY = 'recommend_prefs';
const ROLE_SRC = '公演ページのクレジット';
const KIND_LABEL = {'#形式': '形式', '#原作': '原作', '#翻訳': '', '#会場': '劇場', '#値段': '料金帯', '#題材': '題材'};
const KIND_SRC = {'#形式': '公演名とクレジット', '#会場': '公演ページの劇場', '#値段': '公演ページの料金'};
const WORKS_SHOWN = 3;
const MARK_ORDER = {'◎': 0, '○': 1, '△': 2, '×': 3};

const ICO = {search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM16.2 16.2 21 21'};
const ico = (name, size = 16) => `<svg class="ico " viewBox="0 0 24 24" width="${size}" height="${size}"`
  + ` fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"`
  + ` aria-hidden="true"><path d="${ICO[name]}"/></svg>`;
const pad2 = n => String(n).padStart(2, '0');
const chunks = (xs, n) => Array.from({length: Math.ceil(xs.length / n)}, (_, i) => xs.slice(i * n, i * n + n));

/** The user's rated works as the recommender reads them, with their linked stage's credits. */
async function ratedWorks(ctx, access) {
  const works = (await loadWorks(ctx)).filter(w => !w.unseen && w.stage_id && gradeOf(w.verdict));
  const {results} = await ctx.db.prepare("SELECT work_key, updated_at FROM works WHERE user_id=? AND verdict IS NOT NULL AND verdict<>''").bind(ctx.uid).all();
  const updated = new Map(results.map(r => [r.work_key, r.updated_at]));
  const people = await access.peopleFor([...new Set(works.map(w => w.stage_id))]);
  return works.map(w => ({key: w.work_key, title: w.title, stage_id: w.stage_id, verdict: w.verdict,
    date: w.last_date || w.first_date || '', aspects: w.aspects || '', updated_at: updated.get(w.work_key) || '',
    people: people.get(w.stage_id) || []}));
}

/** measure_nets.person_titles: (role, person) -> titles, ◎ first, newest first within a mark. */
function personTitles(rated) {
  const acc = new Map();
  for (const r of rated) {
    if (!(r.verdict in MARK_ORDER) || !r.title) continue;
    for (const [role, person] of r.people) {
      const k = role + '\t' + person;
      if (!acc.has(k)) acc.set(k, []);
      acc.get(k).push([MARK_ORDER[r.verdict], r.date, r.title]);
    }
  }
  const out = new Map();
  for (const [k, rows] of acc) {
    rows.sort((a, b) => (a[0] - b[0]) || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0));
    out.set(k, [...new Set(rows.map(r => r[2]))]);
  }
  return out;
}

const worksText = (titles, n) => {
  if (!titles?.length) return `（履歴 ${Math.trunc(n)} 本）`;
  const rest = titles.length - WORKS_SHOWN;
  return '（' + titles.slice(0, WORKS_SHOWN).map(t => `『${E(t)}』`).join('・') + (rest > 0 ? ` ほか ${rest} 本` : '') + '）';
};

/** render_recommend.reason_rows for the Worker's reasons (people, then kinds of show). */
export function reasonRows(group, titles) {
  const out = [];
  for (const [, role, person, n] of group.parts.slice(0, 4)) {
    out.push(`<li class="rs b"><span class="net">人物</span>${E(role)} <b>${E(person)}</b>`
      + `<span class="n">${worksText(titles.get(role + '\t' + person), n)}</span>`
      + `<span class="src">［出典: ${E(ROLE_SRC)}］</span>`
      + `<button class="rsx" data-word="${E(person)}" title="この人物を理由に出さない">✕</button></li>`);
  }
  for (const [, axis, tag, n] of group.kinds.slice(0, 2)) {
    const label = Object.hasOwn(KIND_LABEL, axis) ? KIND_LABEL[axis] : axis.replace(/^#+/, '');
    out.push(`<li class="rs c k"><span class="net">種類</span>${label ? E(label) + ' ' : ''}<b>${E(tag)}</b>`
      + `<span class="n">${worksText(titles.get(axis + '\t' + tag), n)}</span>`
      + `<span class="src">［出典: ${E(KIND_SRC[axis] || ROLE_SRC)}］</span></li>`);
  }
  return out.length ? out.join('') : '<li class="rs none">理由を出せていません</li>';
}

/** Stages the user has answered (interest / not interested / owned): out of the recommendations. */
async function answered(ctx) {
  const {results} = await ctx.db.prepare('SELECT DISTINCT stage_id FROM reaction WHERE user_id=? AND (interest IS NOT NULL OR owned=1)').bind(ctx.uid).all();
  return new Set(results.map(r => r.stage_id));
}

/**
 * Ranked productions for the user, one slot each, with every venue of the production
 * (stage_id, pref, start) so a prefecture filter can pick the venue. Cached in rec_cache
 * until the index, the date, or the user's works / favourites / reactions change.
 */
export async function rankedGroups(ctx) {
  const db = ctx.db;
  const ver = (await db.prepare("SELECT v FROM rec_meta WHERE k='current'").first())?.v;
  if (!ver) return {ready: false, groups: [], titles: new Map()};
  const st = await db.prepare(`SELECT (SELECT count(*) FROM works WHERE user_id=?1) AS wn, (SELECT max(updated_at) FROM works WHERE user_id=?1) AS wm,
    (SELECT count(*) FROM reaction WHERE user_id=?1) AS an, (SELECT max(updated_at) FROM reaction WHERE user_id=?1) AS am,
    (SELECT count(*) FROM favourites WHERE user_id=?1) AS fn, (SELECT count(*) FROM merges WHERE user_id=?1) AS mn,
    (SELECT count(*) FROM excluded WHERE user_id=?1) AS xn,
    (SELECT max(updated_at) FROM app_setting WHERE user_id=?1 AND key IN ('declared','declined')) AS dm,
    (SELECT v FROM rec_meta WHERE k='rec_card') AS cv`).bind(ctx.uid).first();
  const stamp = [VERSION, ver, ctx.today, st.wn, st.wm, st.an, st.am, st.fn, st.mn, st.xn, st.dm, st.cv].join('|');
  const access = d1Access(db, ver);
  const cached = await db.prepare('SELECT body FROM rec_cache WHERE user_id=? AND stamp=?').bind(ctx.uid, stamp).first();
  if (cached) {
    const body = JSON.parse(cached.body);
    return {...body, titles: new Map(body.titles), cached: true};
  }
  const rated = await ratedWorks(ctx, access);
  const gate = chooseVariant(rated);
  const declared = await loadDeclared(ctx);
  const favourites = KINDS.flatMap(kind => (declared[kind] || []).map(name => ({name, kind}))).slice(0, 200);
  const {seeds, skip} = await seedsFromFavourites(access, favourites);
  // Stages of a registered name are お気に入り, stages of a word not to show are left out
  // (app._rebucket): neither is ranked here.
  const {hits, declined} = await nameHits(ctx, declared, await loadDeclined(ctx));
  const ranked = await scoreFromIndex({...access, rated: gate.aspects ? rated : rated.map(r => ({...r, aspects: []})),
    multipliers: gate.multipliers, today: ctx.today, seeds, skip});
  const done = await answered(ctx);
  // One slot per production (collapse_tours), after answered stages are left out.
  const byTour = new Map();
  for (const c of ranked) {
    if (done.has(c.stage_id) || hits.has(c.stage_id) || declined.has(c.stage_id)) continue;
    const key = c.tour || 'stage:' + c.stage_id;
    if (!byTour.has(key)) byTour.set(key, {stage_id: c.stage_id, tour: c.tour || '', parts: c.parts, kinds: c.kinds, b: c.b});
  }
  const groups = [...byTour.values()];
  const kept = groups.slice(0, KEEP);
  // Every venue of the kept productions (the index groups a tour by rec_stage.tour).
  const venues = new Map();
  const tours = [...new Set(kept.map(g => g.tour).filter(Boolean))];
  for (const part of chunks(tours, 90)) {
    const {results} = await db.prepare(`SELECT stage_id,tour,start,end,entry FROM rec_stage WHERE ver=? AND tour IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all();
    for (const r of results) {
      if (r.end && r.end < ctx.today) continue;
      if (!venues.has(r.tour)) venues.set(r.tour, []);
      venues.get(r.tour).push({stage_id: r.stage_id, pref: JSON.parse(r.entry || '{}').pref || '', start: r.start || ''});
    }
  }
  const lone = kept.filter(g => !g.tour).map(g => g.stage_id);
  const prefOf = new Map();
  for (const part of chunks(lone, 90)) {
    const {results} = await db.prepare(`SELECT stage_id,start,entry FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all();
    for (const r of results) prefOf.set(r.stage_id, {stage_id: r.stage_id, pref: JSON.parse(r.entry || '{}').pref || '', start: r.start || ''});
  }
  for (const g of kept) {
    const vs = g.tour ? (venues.get(g.tour) || []) : [prefOf.get(g.stage_id)].filter(Boolean);
    g.venues = vs.length ? vs : [{stage_id: g.stage_id, pref: '', start: ''}];
    // Answered venues of the production stay out too (the answer is copied to the tour).
    g.venues = g.venues.filter(v => v.stage_id === g.stage_id || !done.has(v.stage_id));
  }
  const titles = personTitles(rated);
  const body = {ready: true, ver, n_rated: rated.length, n_scored: groups.length, groups: kept,
    titles: [...titles].filter(([k]) => kept.some(g => g.parts.slice(0, 4).some(p => p[1] + '\t' + p[2] === k) || g.kinds.slice(0, 2).some(p => p[1] + '\t' + p[2] === k)))};
  await db.prepare('INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET stamp=excluded.stamp,body=excluded.body,created_at=excluded.created_at')
    .bind(ctx.uid, stamp, JSON.stringify(body), Math.floor(ctx.now / 1000)).run();
  return {...body, titles: new Map(body.titles), cached: false};
}

/** render_recommend.filtered: the shown venue of each production, and how many matched. */
export function filtered(groups, prefs, top = TOP) {
  if (!prefs.length) return {rows: groups.slice(0, top).map(g => ({...g, shown: g.stage_id})), hit: groups.length};
  const keep = new Set(prefs);
  const out = [];
  for (const g of groups) {
    const hit = g.venues.filter(v => keep.has(v.pref));
    if (!hit.length) continue;
    const v = hit.reduce((a, b) => ((b.start || '9999') < (a.start || '9999') ? b : a));
    out.push({...g, shown: v.stage_id});
  }
  return {rows: out.slice(0, top), hit: out.length};
}

export function prefCounts(groups) {
  const n = {};
  for (const g of groups) for (const p of new Set(g.venues.map(v => v.pref).filter(Boolean))) n[p] = (n[p] || 0) + 1;
  return n;
}

const PREF_NOTE = `都道府県は<b>いくつでも同時に選べます</b>。選んだ県で観られる公演を、好みに合いそうな順に <b>${TOP} 件</b>まで表示します。数字は、その県で観られる件数です。<b>選ばなければ全国です。</b>ツアーで来る公演も入ります。本拠地が他県でも、選んだ県の会場に来る公演は、その会場の日程で表示します。`;
/** render_recommend.pref_form (without the map: prefmap.panel is not ported yet). */
export function prefForm(counts, prefs, action = '/recommend') {
  const keep = new Set(prefs);
  const chips = PREFS.filter(p => counts[p]).map(p => `<label class="pchip${keep.has(p) ? ' on' : ''}">`
    + `<input type="checkbox" name="pref" value="${E(p)}"${keep.has(p) ? ' checked' : ''}>`
    + `<span class="pl">${E(p)}</span><span class="pn">${counts[p]}</span></label>`).join('');
  const now = !keep.size ? '全国' : PREFS.filter(p => keep.has(p)).join('・') + `（${keep.size} 県）`;
  return `<form class="pfil" method="get" action="${E(action)}">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<input type="hidden" name="f" value="1">

<details class="pbox">
<summary>${ico('search', 15)}観に行ける場所で絞り込む ── いまは<b>${E(now)}</b></summary>
<p class="lead">${PREF_NOTE}</p>

<div class="pchips">${chips}</div>
<div class="pfoot"><button type="submit">${ico('search')}この都道府県で絞り込む</button>
<a class="pall" href="${E(action)}?t=__TAGURI_TOKEN__&amp;f=1">全国に戻す</a></div>
</details></form>`;
}

/** The chosen prefectures: a submitted form (?f=1) saves them, otherwise the saved ones. */
async function prefsFor(params, ctx) {
  if (params.has('f')) {
    const prefs = PREFS.filter(p => params.getAll('pref').includes(p)).slice(0, 47);
    if (prefs.length) {
      await ctx.db.prepare('INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at')
        .bind(ctx.uid, PREFS_KEY, JSON.stringify(prefs), new Date(ctx.now).toISOString()).run();
    } else {
      await ctx.db.prepare('DELETE FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, PREFS_KEY).run();
    }
    return prefs;
  }
  const row = await ctx.db.prepare('SELECT value FROM app_setting WHERE user_id=? AND key=?').bind(ctx.uid, PREFS_KEY).first();
  try { return PREFS.filter(p => JSON.parse(row?.value || '[]').includes(p)); } catch { return []; }
}

/** The cards of these rows, rank from `first`; rows without a card yet are left out. */
export async function cardsHtml(ctx, rows, titles, first = 1) {
  const {html, posters} = await cardTemplates(ctx.db, rows.flatMap(r => [r.shown, r.stage_id]));
  const out = [];
  let rank = first;
  for (const r of rows) {
    const card = html.get(r.shown);
    if (!card) continue;
    const pic = posters.get(r.shown) || posters.get(r.stage_id);
    out.push(compose(card, r.shown, 'recommend', {rank: rank++, why: reasonRows(r, titles), poster: pic ? posterHtml(pic) : ''}));
  }
  return out;
}

/** app.unrated_ends: the dates unrated works ended (no titles), for the nudge in app.js. */
async function unratedEnds(ctx) {
  return (await loadWorks(ctx)).filter(w => !w.verdict && !w.unseen && w.last_date && w.last_date <= ctx.today)
    .map(w => w.last_date).sort();
}

export async function recommendScreen(params, ctx) {
  const prefs = await prefsFor(params, ctx);
  const data = await rankedGroups(ctx);
  const nCand = Number((await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='catalogue_upcoming'").first())?.v || 0);
  const {rows, hit} = filtered(data.groups, prefs);
  const cards = await cardsHtml(ctx, rows, data.titles);
  const where = prefs.length <= 3 ? prefs.join('・') : `${prefs[0]}ほか ${prefs.length - 1} 県`;
  let head, lede;
  if (!prefs.length && !cards.length) {
    head = '今週のおすすめはありません';
    lede = `<p class="pnow">これから観られる公演 ${nCand} 件のうち、好みに合いそうだと判断できたものはありませんでした。おすすめは、観た公演に付けた ◎ から作り手の名簿を作って出しています。<a href="/rate?t=__TAGURI_TOKEN__">観た公演の評価</a>で ◎ を付けるか、<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に見逃したくない名前を登録してください。登録した名前の公演は、観た記録が無くても出ます。</p>`;
  } else if (!prefs.length) {
    head = `今週のおすすめ ${cards.length} 件`;
    lede = `<p class="lede">これから観られる公演 ${nCand} 件のうち、好みに合いそうだと判断できたのは ${data.n_scored} 件でした。上位 ${cards.length} 件を表示しています。答え済みの公演は、この一覧から外して下にまとめてあります。</p>`;
  } else if (!cards.length) {
    head = `${where}のおすすめはありません`;
    lede = `<p class="pnow">これから観られる公演 ${nCand} 件のうち、<b>${E(where)}</b>で観られるものはありませんでした。ほかの都道府県を選ぶか、全国に戻してください。</p>`;
  } else {
    const tail = hit > cards.length ? `好みに合いそうな順に、上位 ${cards.length} 件を表示しています（残り ${hit - cards.length} 件は出していません）。` : `${cards.length} 件すべてを表示しています。`;
    head = `${where}のおすすめ ${cards.length} 件`;
    lede = `<p class="pnow"><b>${E(where)}</b>で観られる公演のうち、好みに合いそうだと判断できたのは ${hit} 件でした。${tail}</p>`;
  }
  const nInterest = (await ctx.db.prepare('SELECT count(DISTINCT stage_id) AS n FROM reaction WHERE user_id=? AND interest=1 AND COALESCE(owned,0)=0').bind(ctx.uid).first())?.n || 0;
  const notes = `<p class="note">現在のあなたの評価 ${data.n_rated || 0} 作品から計算しています。評価の変更・取り消しは、次におすすめを開くと反映されます。</p>`;
  const nSyn = cards.filter(h => /<div class="syn( doubt)?"/.test(h)).length;
  const limits = cards.length ? `<p class="note toinfo"><b>この ${cards.length} 件で、出せていない情報です。</b><br>
・<b>チケットの販売期限と、販売終了・完売</b>：手元に情報がないので表示できません。
残っているかどうかは公式サイトで確認してください<br>
・<b>あらすじ</b>：${nSyn}/${cards.length} 件で表示できました。残りは公演のページに載っていませんでした<br>
・<b>まだ答えていない公演は、次回も候補に残ります。</b>
評価・公演情報・設定が変わると、順位も変わることがあります</p>` : '';
  const body = `<h1>${E(head)}</h1>
${lede}
${notes}
<div class="fil2">${prefForm(prefCounts(data.groups), prefs)}</div>
${cards.join('')}
<p class="lede">気になった公演で「興味あり」を押すと、
<a href="/recommend/interest?t=__TAGURI_TOKEN__">「興味あり」（いま ${nInterest} 件）</a>に移ります。</p>
${limits}`;
  return {title: '今週のおすすめ', body_html: body, unrated_ends: await unratedEnds(ctx)};
}

// ---------------------------------------------------------------- react (serve.on_react)
const REACT = {owned: {owned: 1}, interest: {interest: 1}, nointerest: {interest: 0}};

async function reactRow(ctx, stageId, cols, source) {
  const label = ctx.today;
  const v = {interest: null, owned: null, note: null, note_no: null, ...cols};
  await ctx.db.prepare(`INSERT INTO reaction(user_id,label,stage_id,interest,owned,note,note_no,source,updated_at) VALUES(?,?,?,?,?,?,?,?,?)
    ON CONFLICT(user_id,label,stage_id) DO UPDATE SET interest=COALESCE(excluded.interest,reaction.interest), owned=COALESCE(excluded.owned,reaction.owned),
    note=COALESCE(excluded.note,reaction.note), note_no=COALESCE(excluded.note_no,reaction.note_no), source=excluded.source, updated_at=excluded.updated_at`)
    .bind(ctx.uid, label, stageId, v.interest, v.owned, v.note, v.note_no, source, new Date(ctx.now).toISOString()).run();
}

/** serve.fill_slot: the next card in place of the one answered, honouring the saved prefectures. */
async function fillSlot(ctx, shown, pressed) {
  if (!shown.length) return {html: '', left: 0, said: ''};
  const prefs = await prefsFor(new URLSearchParams(), ctx);
  const data = await rankedGroups(ctx);
  const {rows} = filtered(data.groups, prefs, 1e6);
  const seen = new Set([...shown.map(String), String(pressed)]);
  const rest = rows.filter(r => !seen.has(String(r.stage_id)) && !seen.has(String(r.shown)));
  if (!rest.length) return {html: '', left: 0, said: '記録しました。入れ替える候補はもうありません（好みに合いそうだと判断できた分は出し切りました）。'};
  const [card] = await cardsHtml(ctx, rest.slice(0, 1), data.titles, shown.length + 1);
  return {html: card || '', left: rest.length,
    said: `記録しました。入れ替わりに 1 件を下に足しました（まだ出していない候補が ${rest.length - 1} 件あります）。`};
}

export async function reactAction(b, ctx) {
  const stageId = String(b.stage_id ?? ''), value = String(b.value ?? '');
  if (b.fill_only) {
    if (!stageId) throw new ValueError('stage_id が要る');
    const shown = (Array.isArray(b.shown) ? b.shown : []).slice(0, 120).map(x => String(x).slice(0, 20));
    return {body: {ok: true, stage_id: stageId, fill: await fillSlot(ctx, shown, stageId)}};
  }
  const given = {};
  for (const k of ['note', 'note_no']) if (b[k] !== undefined && b[k] !== null) given[k] = String(b[k]).slice(0, 2000);
  if (!stageId || !/^[A-Za-z0-9_-]{1,40}$/.test(stageId) || (!Object.hasOwn(REACT, value) && !Object.keys(given).length))
    throw new ValueError('stage_id と、value（owned / interest / nointerest）か理由が要る');
  await reactRow(ctx, stageId, {...(REACT[value] || {}), ...given}, 'screen');
  if (Object.hasOwn(REACT, value) && Array.isArray(b.siblings)) {
    // The same answer for the production's other venues (the card's data-tours); notes stay on the pressed one.
    for (const sid of b.siblings.slice(0, 40).map(String).filter(s => /^\d+$/.test(s) && s !== stageId))
      await reactRow(ctx, sid, REACT[value], 'screen_tour');
  }
  const out = {ok: true, stage_id: stageId, value, note: 'note' in given, note_no: 'note_no' in given};
  if (Object.hasOwn(REACT, value) && !b.nofill) {
    const shown = (Array.isArray(b.shown) ? b.shown : []).slice(0, 120).map(x => String(x).slice(0, 20));
    out.fill = await fillSlot(ctx, shown, stageId);
  }
  return {body: out};
}

export const recommendScreens = {
  screens: {recommend: recommendScreen},
  actions: {react: reactAction},
};
