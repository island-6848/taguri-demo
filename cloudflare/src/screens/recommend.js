// 今週のおすすめ: the recommend screen and the three-choice writes (react), answered by
// the Worker from D1 (起案者の指示 2026-10-14「おすすめの画面を移して」).
//
// Not a byte-for-byte port of app._recommend_body. The ranking is the Worker's
// (src/recommend.js, checked against user_recommender by test_recommend_index.py),
// computed from the user's works / favourites / reactions in D1. The cards are
// rendered once a day by the Python screen itself (scripts/build_cards.py,
// render_recommend.ticket) and stored in rec_card; here only the rank, the
// reasons (reason_rows) and the poster are filled in. The 効かせ方 sliders are
// weights.js. Left out for now: the map above the prefecture chips (no outlines in
// D1), the count of shows a setting hid (w_dropped) and the impression re-ranking.
import {frac} from './grade.js';
import {scoreFromIndex, d1Access, seedsFromFavourites, gradeOf, MAX_SEED_STAGES} from '../recommend.js';
import {stageInfo} from './fallback.js';
import {parseCredits} from './credits.js';
import {chooseVariant, groupOf} from '../reco-gate.js';
import {readWeights, multipliersOf, weightForm, weightAction} from './weights.js';
import {E, ValueError} from './py.js';
import {loadWorks} from './works.js';
import {castOffOf} from './diary.js';
import {compose, cardTemplates, posterHtml} from './cards.js';
import {PREFS, prefForm, prefsFor, regionCounts} from './prefs.js';
export {prefForm, prefsFor};
import {loadDeclared, loadDeclined, nameHits, KINDS, reactionsOf} from './lists.js';

export const TOP = 15;
const TIPS = `<section class="card tips">
<h2>おすすめを出すためのワンポイント</h2>
<ol>
<li><b>観た公演を 2 本以上、評価してください。</b>「◎」だけでなく「○」「△」「×」も混ぜて付けるのがコツです。よかった公演といまひとつだった公演の両方があると、どこが好みなのかが分かります。全部「◎」だと、違いが分からず、おすすめが出ません。</li>
<li><b>観た公演は、題名と観た日を正しく入れてください。</b>公演の情報（出演者や作り手）が分かると、その人たちの次の公演をおすすめできます。日記帳で「まだどの公演とも結び付いていません」と出る記録は、その欄から観た公演を選んでください。</li>
<li><b>好きな俳優・劇団・作品を「お気に入り」に登録してください。</b>登録した名前の公演は、評価が無くてもすぐ「お気に入り」に出ます。一緒に出ている人の公演も、おすすめに出やすくなります。</li>
<li><b>気になる公演に「興味あり」を押してください。</b>観た記録が無くても、押した公演に出ている人や作り手の、ほかの公演がおすすめに出ます。<a href="/recommend/reminder?t=__TAGURI_TOKEN__">開幕リマインド</a>から選ぶのが手軽です。</li>
<li><b>評価が増えるほど、おすすめは増えて、当たりやすくなります。</b>まずは 10 本ほどを目安にどうぞ。</li>
</ol>
<p class="lead"><a href="/rate?t=__TAGURI_TOKEN__">観た公演の評価</a>・<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>・<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>から始められます。</p>
</section>
`;
// Groups kept per user between requests: enough to fill 15 cards in any one prefecture.
const KEEP = 400;
const VERSION = 'screen-v5';   // v2: the user's 効かせ方 (rank_weight) and the per-group counts; v3: 興味あり as seeds; v4: diag; v5: 興味あり split (impl-interest-split)
export {PREFS} from './prefs.js';
const ROLE_SRC = '公演ページのクレジット';
const KIND_LABEL = {'#形式': '形式', '#原作': '原作', '#翻訳': '', '#会場': '劇場', '#値段': '料金帯', '#題材': '題材'};
const KIND_SRC = {'#形式': '公演名とクレジット', '#会場': '公演ページの劇場', '#値段': '公演ページの料金'};
const WORKS_SHOWN = 3;
// Every scale sorts with the marks by its place: the top (◎, ★5, ○ of ○×) first, the bottom last
// (grade.js). 興味あり comes after every rating.
const MARK_ORDER = {'◎': 0, '○': 1, '△': 2, '×': 3, '興味あり': 4};
const markRank = v => (Object.hasOwn(MARK_ORDER, v) ? MARK_ORDER[v] : frac(v) === null ? null : 3 * (1 - frac(v)));

const pad2 = n => String(n).padStart(2, '0');
const chunks = (xs, n) => Array.from({length: Math.ceil(xs.length / n)}, (_, i) => xs.slice(i * n, i * n + n));

/** The user's rated works as the recommender reads them, with their linked stage's credits. */
async function ratedWorks(ctx, access) {
  const works = (await loadWorks(ctx)).filter(w => !w.unseen && w.stage_id && gradeOf(w.verdict));
  const {results} = await ctx.db.prepare("SELECT work_key, updated_at FROM works WHERE user_id=? AND verdict IS NOT NULL AND verdict<>''").bind(ctx.uid).all();
  const updated = new Map(results.map(r => [r.work_key, r.updated_at]));
  const people = await access.peopleFor([...new Set(works.map(w => w.stage_id))]);
  // 観た回に出ていなかった出演者（Wキャスト・休演、works.cast_off）は、この記録の材料から外す。
  return works.map(w => {
    const off = new Set(castOffOf(w));
    return {key: w.work_key, title: w.title, stage_id: w.stage_id, verdict: w.verdict,
      date: w.last_date || w.first_date || '', aspects: w.aspects || '', updated_at: updated.get(w.work_key) || '',
      people: (people.get(w.stage_id) || []).filter(([role, person]) => !(role === '出演' && off.has(person)))};
  });
}

/**
 * 興味ありを押した公演（新しい順に MAX_SEED_STAGES まで）を、お気に入りと同じ仮の ◎（seeds）にする。
 * 起案者の指示（2026-10-15）「一回その案にしてみて」（q-interest-seed）。重みはお気に入りと同じで、
 * 評価が増えるほど薄まる（recommend.personValues の SEED_K / (SEED_K + 評価の数)）。
 * 索引に人物の無い公演（一覧 catalogue にだけある開幕リマインドの公演など）は、出演欄から人物を読む。
 */
async function interestSeeds(ctx, access) {
  // reaction は日ごとの行（label = その日）なので、公演ごとに新しい答えで上書きしてから選ぶ（lists.reactionsOf と同じ）。
  const {results} = await ctx.db.prepare('SELECT stage_id,interest,updated_at FROM reaction WHERE user_id=? AND interest IS NOT NULL ORDER BY updated_at')
    .bind(ctx.uid).all();
  const last = new Map();
  for (const r of results) { last.delete(r.stage_id); last.set(r.stage_id, Number(r.interest)); }
  const newest = v => [...last].filter(([, x]) => x === v).map(([s]) => String(s)).reverse().slice(0, MAX_SEED_STAGES);
  const sids = newest(1), noes = newest(0);
  if (!sids.length) return {seeds: [], disliked: [], n: 0};
  const all = [...sids, ...noes];
  const [people, info] = await Promise.all([access.peopleFor(all), stageInfo(ctx.db, all)]);
  for (const s of all) {
    if (people.get(s)?.length) continue;
    const p = parseCredits(info.get(s)?.fields || {});
    if (p.length) people.set(s, p);
  }
  // 「なぜ気になったか」（reaction.note、任意）。書いてあれば、そこに名前のある人に多めに配る。
  const notes = await reactionsOf(ctx);
  const one = s => ({stage_id: s, title: info.get(s)?.title || '', note: notes.get(s)?.note || '', people: people.get(s)});
  return {n: sids.length, seeds: sids.filter(s => people.get(s)?.length).map(one), disliked: noes.filter(s => people.get(s)?.length).map(one)};
}

/** measure_nets.person_titles: (role, person) -> titles, ◎ first, newest first within a mark. */
function personTitles(rated, liked = []) {
  const acc = new Map();
  // 興味ありを押した公演も、理由の作品名に「興味あり」の印の後ろで並べる（measure_nets.person_titles と同じ）。
  for (const r of [...rated, ...liked.map(s => ({verdict: '興味あり', date: '', title: s.title, people: s.people}))]) {
    if (markRank(r.verdict) === null || !r.title) continue;
    for (const [role, person] of r.people) {
      const k = role + '\t' + person;
      if (!acc.has(k)) acc.set(k, []);
      acc.get(k).push([markRank(r.verdict), r.date, r.title]);
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
  // 評価の無い人（お気に入り・興味ありの仮の ◎ だけで上がった人）は n が 0。「履歴 0 本」と出さない。
  if (!titles?.length) return Math.trunc(n) ? `（履歴 ${Math.trunc(n)} 本）` : '（お気に入り・興味ありの公演から）';
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
    (SELECT max(updated_at) FROM rank_weight WHERE user_id=?1) AS km,
    (SELECT v FROM rec_meta WHERE k='rec_card') AS cv`).bind(ctx.uid).first();
  const stamp = [VERSION, ver, ctx.today, st.wn, st.wm, st.an, st.am, st.fn, st.mn, st.xn, st.dm, st.cv, st.km].join('|');
  const access = d1Access(db, ver);
  const cached = await db.prepare('SELECT body FROM rec_cache WHERE user_id=? AND stamp=?').bind(ctx.uid, stamp).first();
  if (cached) {
    const body = JSON.parse(cached.body);
    return {...body, titles: new Map(body.titles), cached: true};
  }
  const rated = await ratedWorks(ctx, access);
  const gate = chooseVariant(rated);
  // 効かせ方（本人が決めた段）は、裏の答え合わせが選んだ倍率に掛け合わせる。
  // 「効かせない」（0）にした項目は、順位からも理由からも消える（scoreFromIndex は 0 の寄与を捨てる）
  const weights = await readWeights(ctx), own = multipliersOf(weights);
  const multipliers = {...gate.multipliers};
  for (const [g, m] of Object.entries(own)) multipliers[g] = (Object.hasOwn(multipliers, g) ? multipliers[g] : 1.0) * m;
  const declared = await loadDeclared(ctx);
  const favourites = KINDS.flatMap(kind => (declared[kind] || []).map(name => ({name, kind}))).slice(0, 200);
  const fav = await seedsFromFavourites(access, favourites), skip = fav.skip;
  const {seeds: liked, disliked, n: nLiked} = await interestSeeds(ctx, access);
  const seeds = fav.seeds;
  // Stages of a registered name are お気に入り, stages of a word not to show are left out
  // (app._rebucket): neither is ranked here.
  const {hits, declined} = await nameHits(ctx, declared, await loadDeclined(ctx));
  const ranked = await scoreFromIndex({...access, rated: gate.aspects ? rated : rated.map(r => ({...r, aspects: []})),
    multipliers, today: ctx.today, seeds, skip, liked, disliked});
  // app._weight_counts: per group, the candidates it matches (the people and kinds that raised them).
  const wCounts = {};
  for (const c of ranked) {
    const seen = new Set([...c.parts, ...c.kinds].map(p => groupOf(p[1])));
    for (const g of seen) wCounts[g] = (wCounts[g] || 0) + 1;
  }
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
  const titles = personTitles(rated, liked);
  // 推薦が出ないときに本番で何が足りないかを見るための数（画面には出さない。/api/screen/recommend の JSON の diag）。
  const diag = {rated: rated.length, rated_linked: rated.filter(r => r.people.length).length,
    interest: nLiked, interest_with_people: liked.length, favourite_seeds: fav.seeds.length,
    ranked: ranked.length, after_answered: groups.length};
  const body = {ready: true, ver, n_rated: rated.length, n_scored: groups.length, groups: kept, weights, w_counts: wCounts, diag,
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
    lede = '';
  } else if (!prefs.length) {
    head = `今週のおすすめ ${cards.length} 件`;
    lede = `<p class="lede">これから観られる公演 ${nCand} 件のうち、好みに合いそうだと判断できたのは ${data.n_scored} 件でした。上位 ${cards.length} 件を表示しています。答えた公演は、この一覧から外して「興味あり」「購入済み公演」などに移します。</p>`;
  } else if (!cards.length) {
    head = `${where}のおすすめはありません`;
    lede = `<p class="pnow">これから観られる公演 ${nCand} 件のうち、<b>${E(where)}</b>で観られるものはありませんでした。ほかの都道府県を選ぶか、全国に戻してください。</p>`;
  } else {
    const tail = hit > cards.length ? `好みに合いそうな順に、上位 ${cards.length} 件を表示しています（残り ${hit - cards.length} 件は出していません）。` : `${cards.length} 件すべてを表示しています。`;
    head = `${where}のおすすめ ${cards.length} 件`;
    lede = `<p class="pnow"><b>${E(where)}</b>で観られる公演のうち、好みに合いそうだと判断できたのは ${hit} 件でした。${tail}</p>`;
  }
  // 推薦を出すためのワンポイント（起案者の指示 2026-10-14「なにがしたら出るか、使うユーザーが
  // わかりやすい文章で（技術的なことは書かないで）おすすめの初期画面に追加して」）。
  // 条件は new-user-reco-threshold: 公演とつながった記録が 2 件以上で、評価が 2 種類以上。
  const tips = !cards.length && !prefs.length ? TIPS : '';
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
${tips}<div class="fil2">${prefForm(prefCounts(data.groups), prefs, '/recommend', '', {}, regionCounts(data.groups.map(g => ({key: g.stage_id, prefs: g.venues.map(v => v.pref)}))))}${weightForm(data.weights || {}, data.w_counts || {})}</div>
${cards.join('')}
<p class="lede">気になった公演で「興味あり」を押すと、
<a href="/recommend/interest?t=__TAGURI_TOKEN__">「興味あり」（いま ${nInterest} 件）</a>に移ります。</p>
${limits}`;
  return {title: '今週のおすすめ', body_html: body, unrated_ends: await unratedEnds(ctx), diag: data.diag || null};
}

// ---------------------------------------------------------------- react (serve.on_react)
const REACT = {owned: {owned: 1}, interest: {interest: 1}, nointerest: {interest: 0}};

async function reactRow(ctx, stageId, cols, source) {
  const label = ctx.today;
  const v = {interest: null, owned: null, note: null, note_no: null, note_pre: null, ...cols};
  await ctx.db.prepare(`INSERT INTO reaction(user_id,label,stage_id,interest,owned,note,note_no,note_pre,source,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(user_id,label,stage_id) DO UPDATE SET interest=COALESCE(excluded.interest,reaction.interest), owned=COALESCE(excluded.owned,reaction.owned),
    note=COALESCE(excluded.note,reaction.note), note_no=COALESCE(excluded.note_no,reaction.note_no), note_pre=COALESCE(excluded.note_pre,reaction.note_pre),
    source=excluded.source, updated_at=excluded.updated_at`)
    .bind(ctx.uid, label, stageId, v.interest, v.owned, v.note, v.note_no, v.note_pre, source, new Date(ctx.now).toISOString()).run();
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
  for (const k of ['note', 'note_no', 'note_pre']) if (b[k] !== undefined && b[k] !== null) given[k] = String(b[k]).slice(0, 2000);
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

// serve._exposure_event with no exposure store (the public service keeps no telemetry:
// it would spend D1 writes on every card shown). web/recommendation-exposure.js reads
// ok:false as "not recording" and stops posting for that card.
const exposureOff = async () => ({body: {ok: false, disabled: true}});
// serve.on_hand_theme on the public service: stage material is shared, so not editable here.
const handThemeAction = async () => { throw new ValueError('公開版では公演情報の編集はできません'); };

export const recommendScreens = {
  screens: {recommend: recommendScreen},
  actions: {react: reactAction, weight: weightAction, 'recommendation/visit': exposureOff, 'recommendation/contact': exposureOff, hand_theme: handThemeAction},
};
