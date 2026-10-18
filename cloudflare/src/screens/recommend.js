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
import {scoreFromIndex, d1Access, seedsFromFavourites, gradeOf, MAX_SEED_STAGES, droppedKind, GENRE_AXIS} from '../recommend.js';
import {stageInfo} from './fallback.js';
import {tourBlock} from './schedule.js';
import {parseCredits} from './credits.js';
import {chooseVariant, groupOf, VARIANTS} from '../reco-gate.js';
import {readWeights, multipliersOf, weightForm, weightAction} from './weights.js';
import {E, ValueError} from './py.js';
import {answerSnapshot, recordShown} from './evalrec.js';
import {ico} from './icons.js';
import {loadWorks} from './works.js';
import {castOffOf} from './diary.js';
import {compose, cardTemplates, posterHtml} from './cards.js';
import {PREFS, prefForm, prefsFor, regionCounts, PAGE_PREF_NOTE} from './prefs.js';
export {prefForm, prefsFor};
import {loadDeclared, loadDeclined, loadKindOff, nameHits, KINDS, reactionsOf, declinedBox, kindOffBox} from './lists.js';

export const TOP = 15;
const TIPS = `<section class="card tips">
<h2>おすすめを出すためのワンポイント</h2>
<ol>
<li><b>観た公演を 2 本以上、評価してください。</b>「◎」だけでなく「○」「△」「×」も混ぜて付けるのがコツです。よかった公演といまひとつだった公演の両方があると、どこが好みなのかが分かります。全部「◎」だと、違いが分からず、おすすめが出ません。</li>
<li><b>観た公演は題名と観た日を正しく入れてください。</b>公演の情報（出演者や作り手）が分かると、その人たちの次の公演をおすすめできます。日記帳で「まだどの公演とも結び付いていません」と出る記録は、その欄から観た公演を選んでください。</li>
<li><b>好きな俳優・劇団・作品を「お気に入り」に登録してください。</b>登録した名前の公演は、評価が無くてもすぐ「お気に入り」に出ます。一緒に出ている人の公演もおすすめに出やすくなります。</li>
<li><b>気になる公演に「興味あり」を押してください。</b>観た記録が無くても、押した公演に出ている人や作り手の、ほかの公演がおすすめに出ます。<a href="/search?t=__TAGURI_TOKEN__">探す</a>で題名や人名から探すか、<a href="/recommend/reminder?t=__TAGURI_TOKEN__">開幕リマインド</a>から選ぶのが手軽です。</li>
<li><b>評価が増えるほど、おすすめは増えて、当たりやすくなります。</b>まずは 10 本ほどを目安にどうぞ。</li>
</ol>
<p class="lead"><a href="/rate?t=__TAGURI_TOKEN__">観た公演の評価</a>・<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>・<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>から始められます。</p>
</section>
`;
// 出せる候補にすべて答え終えたとき（起案者の指示 2026-10-17「本当に全部回答しきってオススメに出せるものが
// なくなったときは、『回答ありがとうございました』のイラストを出して。その下にワンポイントアドバイス」）。
// 幕の下りた舞台に花束。色は画面の色（--curtain など）なので、暗い画面でもそのまま読める
const THANKS_ART = `<svg class="thx-art" viewBox="0 0 240 132" width="240" height="132" role="img" aria-label="幕の下りた舞台と花束">
<rect x="8" y="10" width="224" height="10" rx="3" fill="var(--curtain)"/>
<path d="M14 20h106v94c-18 6-40 6-58 0-18 6-34 6-48 0z" fill="var(--curtain)" opacity=".85"/>
<path d="M120 20h106v94c-14 6-30 6-48 0-18 6-40 6-58 0z" fill="var(--curtain)" opacity=".85"/>
<path d="M120 20v94" stroke="var(--surf)" stroke-width="2" opacity=".6"/>
<path d="M40 20v90M66 20v94M92 20v92M148 20v92M174 20v94M200 20v90" stroke="var(--surf)" stroke-width="1.2" opacity=".25"/>
<rect x="4" y="114" width="232" height="12" rx="3" fill="var(--ink2)" opacity=".5"/>
<ellipse cx="120" cy="121" rx="46" ry="5" fill="var(--acc)" opacity=".18"/>
<g transform="translate(120 122)">
<path d="M-4 -24l-6 -12M0 -24v-16M4 -24l6 -12" stroke="var(--mute)" stroke-width="2"/>
<circle cx="-12" cy="-38" r="7" fill="var(--acc)"/><circle cx="-12" cy="-38" r="2.5" fill="var(--surf)"/>
<circle cx="12" cy="-38" r="7" fill="var(--acc)"/><circle cx="12" cy="-38" r="2.5" fill="var(--surf)"/>
<circle cx="0" cy="-44" r="8" fill="var(--acc)"/><circle cx="0" cy="-44" r="3" fill="var(--surf)"/>
<path d="M-13 -26h26l-13 26z" fill="var(--surf)" stroke="var(--ink2)" stroke-width="1.5"/>
<path d="M-6 -14q6 5 12 0" stroke="var(--acc)" stroke-width="2.5" fill="none"/>
</g>
</svg>`;
const THANKS = `<section class="card thx" id="rec-thanks">
${THANKS_ART}
<p class="thx-h">回答ありがとうございました</p>
<p class="thx-s">いまおすすめできる公演には、すべて答えていただきました。</p>
<h2>また おすすめが出るようにするには</h2>
<ol>
<li><b>過去の観劇記録を足す</b>：<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>に観た公演を足すと、その出演者・作り手の公演が候補に入ります。</li>
<li><b>観た公演を評価する</b>：<a href="/rate?t=__TAGURI_TOKEN__">評価</a>が増えるほど、好みに合う公演を見つけやすくなります。</li>
<li><b>お気に入りを登録する</b>：好きな俳優・劇団・作品を<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に入れると、その人たちの公演が出ます。</li>
<li><b>「探す」で興味ありを押す</b>：<a href="/search?t=__TAGURI_TOKEN__">探す</a>で見つけた公演に押した興味ありも、次のおすすめの手がかりになります。</li>
<li><b>使わない言葉・都道府県の設定を見直す</b>：絞り込みを外すと、隠れていた候補が出ます。</li>
<li><b>少し待つ</b>：新しい公演は毎日取り込んでいます。日をおいて開くと、新しい候補が出ていることがあります。</li>
</ol>
</section>
`;
// Groups kept per user between requests: enough to fill 15 cards in any one prefecture.
const KEEP = 400;
// 再生（H5）で 1 つずつ外す部品: 興味ありの配り分け・1 段広げる・並べ直し（spreadLeads）・裏の答え合わせ（chooseVariant）
export const REPLAY_ABLATIONS = ['split', 'expand', 'spread', 'gate'];
const VERSION = 'screen-v22';   // v22: favourite seeds weigh FAV_SEED_W (お気に入り＞興味あり); v21: credits read only where needed (CPU); v20: a production answered under another stage id stays out; v19: same title + (group / venue / a shared person) is one card; v18: one card per title+group (sameProduction); v17: no 出典 on the reasons; v16: #会場 dropped, 行けない (interest=2) as a liked seed; v15: 出さない語 also hits the kind tags; v14: #ジャンル (a genre turned off hides its stages); v13: no 原作「原作もの」 (DROPPED_KEYS); v12: no #値段 (DROPPED_AXES); v11: reasons of answered stages (answered_why); v2: the user's 効かせ方 (rank_weight) and the per-group counts; v3: 興味あり as seeds; v4: diag; v5: 興味あり split (impl-interest-split); v6: by part importance; v7: tiers + トメ; v8: two tiers only; v9: トメ joins the main roles; v10: spread leads + one-step partners
export {PREFS} from './prefs.js';
const KIND_LABEL = {'#形式': '形式', '#原作': '原作', '#翻訳': '', '#原作の国': '原作の国', '#会場': '劇場', '#題材': '題材', '#ジャンル': 'ジャンル'};
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
    return {key: w.work_key, title: w.title, stage_id: w.stage_id, verdict: w.verdict, cast_off: [...off],
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
  const newest = (...vs) => [...last].filter(([, x]) => vs.includes(x)).map(([s]) => String(s)).reverse().slice(0, MAX_SEED_STAGES);
  // 行けない（2）も、気になった公演として興味ありと同じ向きの手がかりにする
  const sids = newest(1, 2), noes = newest(0);
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
  // 出演欄の文（書かれた順・役名・アンサンブルの見出しが残っている）。役柄の重さに使う（recommend.castImportance）。
  const one = s => ({stage_id: s, title: info.get(s)?.title || '', note: notes.get(s)?.note || '',
    cast_text: String(info.get(s)?.fields?.['出演'] || ''), people: people.get(s)});
  return {n: sids.length, seeds: sids.filter(s => people.get(s)?.length).map(one), disliked: noes.filter(s => people.get(s)?.length).map(one)};
}

/** 観た回に出ていなかったと本人が外した出演者（works.cast_off）。1 段広げるときにも戻さない。 */
const castOffKeys = rated => new Set(rated.flatMap(r => (r.cast_off || []).map(n => '出演\u0000' + n)));

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
  // 1 段広げて来た人（scoreFromIndex の via）: 「○○とよく組む人」と書く
  const via = new Map(group.via || []);
  for (const [, role, person, n] of group.parts.slice(0, 4)) {
    const w = via.get(role + '\t' + person);
    out.push(`<li class="rs b"><span class="net">人物</span>${E(role)} <b>${E(person)}</b>`
      + `<span class="n">${w ? `（好きな${E(w)}と同じ公演に関わる人）` : worksText(titles.get(role + '\t' + person), n)}</span>`
      + `<button class="rsx" data-word="${E(person)}" title="この人物を理由に出さない">✕</button></li>`);
  }
  for (const [, axis, tag, n] of group.kinds.filter(k => !droppedKind(k[1], k[2])).slice(0, 2)) {
    // 「漫画原作」のように中身が見出しを含むときは見出しを出さない（「原作 漫画原作」にしない）
    const label0 = Object.hasOwn(KIND_LABEL, axis) ? KIND_LABEL[axis] : axis.replace(/^#+/, '');
    const label = label0 && tag.endsWith(label0) ? '' : label0;
    out.push(`<li class="rs c k"><span class="net">種類</span>${label ? E(label) + ' ' : ''}<b>${E(tag)}</b>`
      + `<span class="n">${worksText(titles.get(axis + '\t' + tag), n)}</span>`
      + `<button class="rsx" data-kindoff="${E(axis + '\t' + tag)}" title="この理由をおすすめに使わない（公演は消さない）">✕</button></li>`);
  }
  return out.length ? out.join('') : '<li class="rs none">理由を出せていません</li>';
}

/** Each item's people without the kind keys the user turned off ('#原作\tオリジナル'; q-kind-reason-off). */
export function withoutKinds(items, off) {
  if (!off.size) return items;
  return items.map(r => ({...r, people: (r.people || []).filter(([role, p]) => !(role.startsWith('#') && off.has(role + '\t' + p)))}));
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
    (SELECT v FROM rec_meta WHERE k='rec_card') AS cv,
    (SELECT v FROM rec_meta WHERE k='index_rev') AS ir`).bind(ctx.uid).first();
  // 索引は差分で入れ、版（ver）は 'live' のまま変わらないので、中身が変わった合図は index_rev（q-index-incremental）。
  // 「使わない」にした種類の理由は中身ごと控えの印に入れる（同じ秒に外して戻しても、控えが古いまま残らない）
  // 出さない語も中身ごと（同じ秒に足して外すと、更新日時だけでは控えが古いまま残る）
  const off = new Set(await loadKindOff(ctx));
  const words = await loadDeclined(ctx);
  const stamp = [VERSION, ver, st.ir || '', ctx.today, st.wn, st.wm, st.an, st.am, st.fn, st.mn, st.xn, st.dm, st.cv, st.km, [...off].sort().join(','),
    [...words].sort().join('\n')].join('|');
  const access = d1Access(db, ver);
  // 部品を外した計算（ctx.ablate）は控えと印が同じなので、控えを読まず、書かない
  const cached = ctx.ablate ? null : await db.prepare('SELECT body FROM rec_cache WHERE user_id=? AND stamp=?').bind(ctx.uid, stamp).first();
  if (cached) {
    const body = JSON.parse(cached.body);
    return {...body, titles: new Map(body.titles), cached: true};
  }
  // 「使わない」にした種類の理由（q-kind-reason-off）は、評価・興味あり・お気に入りのどこからも値を持たせない
  const rated = withoutKinds(await ratedWorks(ctx, access), off);
  // 部品を外した計算（手元の再生 replay_eval.py の H5 だけが ctx.ablate を渡す。本番は渡さないので動きは変わらない）
  const ablate = ctx.ablate || {};
  const gate = ablate.gate ? {multipliers: VARIANTS.base, aspects: true} : chooseVariant(rated);
  // 効かせ方（本人が決めた段）は、裏の答え合わせが選んだ倍率に掛け合わせる。
  // 「効かせない」（0）にした項目は、順位からも理由からも消える（scoreFromIndex は 0 の寄与を捨てる）
  const weights = await readWeights(ctx), own = multipliersOf(weights);
  const multipliers = {...gate.multipliers};
  for (const [g, m] of Object.entries(own)) multipliers[g] = (Object.hasOwn(multipliers, g) ? multipliers[g] : 1.0) * m;
  const declared = await loadDeclared(ctx);
  const favourites = KINDS.flatMap(kind => (declared[kind] || []).map(name => ({name, kind}))).slice(0, 200);
  const fav = await seedsFromFavourites(access, favourites), skip = fav.skip;
  const interest = await interestSeeds(ctx, access), nLiked = interest.n;
  const liked = withoutKinds(interest.seeds, off), disliked = withoutKinds(interest.disliked, off);
  const seeds = withoutKinds(fav.seeds, off);
  // Stages of a registered name are お気に入り, stages of a word not to show are left out
  // (app._rebucket): neither is ranked here.
  const {hits, declined} = await nameHits(ctx, declared, words);
  const ranked = await scoreFromIndex({...access, rated: gate.aspects ? rated : rated.map(r => ({...r, aspects: []})),
    multipliers, today: ctx.today, seeds, skip, liked, disliked, expand: {peopleFor: access.peopleFor, exclude: castOffKeys(rated)}, ablate});
  // app._weight_counts: per group, the candidates it matches (the people and kinds that raised them).
  const wCounts = {};
  for (const c of ranked) {
    const seen = new Set([...c.parts, ...c.kinds].map(p => groupOf(p[1])));
    for (const g of seen) wCounts[g] = (wCounts[g] || 0) + 1;
  }
  const done = await answered(ctx);
  // 理由の ✕ で外したジャンル（2.5次元・宝塚）は、その公演ごと出さない（起案者の指示 2026-10-16
  // 「おすすめ理由に2.5次元として出してほしい。いらない人はそれ✕押せばいい」）。索引の 1 回の読み出しで引く
  const offGenres = [...off].map(k => k.split('\t')).filter(([axis]) => axis === GENRE_AXIS);
  const genreOff = new Set(offGenres.length ? (await access.postingsFor(offGenres)).map(p => String(p[2])) : []);
  // One slot per production (collapse_tours), after answered stages are left out.
  const byTour = new Map();
  for (const c of ranked) {
    if (done.has(c.stage_id) || hits.has(c.stage_id) || declined.has(c.stage_id) || genreOff.has(String(c.stage_id))) continue;
    const key = c.tour || 'stage:' + c.stage_id;
    if (!byTour.has(key)) byTour.set(key, {stage_id: c.stage_id, tour: c.tour || '', parts: c.parts, kinds: c.kinds, b: c.b, ...(c.via ? {via: c.via} : {})});
  }
  const groups = await sameProduction(db, ver, ablate.spread ? [...byTour.values()] : spreadLeads([...byTour.values()]), undefined, [...done]);
  const kept = groups.slice(0, KEEP);
  // Every venue of the kept productions (the index groups a tour by rec_stage.tour).
  const venues = new Map();
  // 同じ公演としてまとめた別の束（sameProduction の aliases）の会場も、残した束の会場に入れる
  const primary = new Map();
  for (const g of kept) for (const t of [g.tour, ...(g.aliases || [])]) if (t && g.tour) primary.set(t, g.tour);
  const tours = [...primary.keys()];
  for (const part of chunks(tours, 90)) {
    const {results} = await db.prepare(`SELECT stage_id,tour,start,end,entry FROM rec_stage WHERE ver=? AND tour IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all();
    for (const r of results) {
      if (r.end && r.end < ctx.today) continue;
      const t = primary.get(r.tour) || r.tour;
      if (!venues.has(t)) venues.set(t, []);
      venues.get(t).push({stage_id: r.stage_id, pref: JSON.parse(r.entry || '{}').pref || '', start: r.start || ''});
    }
  }
  // 束の鍵の無い公演と、同じ公演としてまとめた束の鍵の無い公演（aliasStages）の会場
  const lone = [...new Set(kept.flatMap(g => [...(g.tour ? [] : [g.stage_id]), ...(g.aliasStages || [])]))];
  const prefOf = new Map();
  for (const part of chunks(lone, 90)) {
    const {results} = await db.prepare(`SELECT stage_id,start,entry FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all();
    for (const r of results) prefOf.set(r.stage_id, {stage_id: r.stage_id, pref: JSON.parse(r.entry || '{}').pref || '', start: r.start || ''});
  }
  for (const g of kept) {
    const vs = [...(g.tour ? (venues.get(g.tour) || []) : [prefOf.get(g.stage_id)]), ...(g.aliasStages || []).map(sid => prefOf.get(sid))]
      .filter((v, i, all) => v && all.findIndex(w => w && w.stage_id === v.stage_id) === i);
    g.venues = vs.length ? vs : [{stage_id: g.stage_id, pref: '', start: ''}];
    // Answered venues of the production stay out too (the answer is copied to the tour).
    g.venues = g.venues.filter(v => v.stage_id === g.stage_id || !done.has(v.stage_id));
  }
  const titles = personTitles(rated, liked);
  // 答えた公演の理由（理由を残す前に押した興味ありのため。lists.interestScreen が reaction.why の無い行に使う）。
  // 興味ありの公演は自分自身も種になっているので、作品名からは自分を除いて出す（lists.ownlessWhy）。
  const answeredWhy = ranked.filter(c => done.has(c.stage_id)).slice(0, 200).map(c => [c.stage_id, whyOf(c, titles)]);
  // 推薦が出ないときに本番で何が足りないかを見るための数（画面には出さない。/api/screen/recommend の JSON の diag）。
  const diag = {rated: rated.length, rated_linked: rated.filter(r => r.people.length).length,
    interest: nLiked, interest_with_people: liked.length, favourite_seeds: fav.seeds.length,
    ranked: ranked.length, after_answered: groups.length};
  const body = {ready: true, ver, n_rated: rated.length, n_scored: groups.length, groups: kept, weights, w_counts: wCounts, diag, answered_why: answeredWhy,
    titles: [...titles].filter(([k]) => kept.some(g => g.parts.slice(0, 4).some(p => p[1] + '\t' + p[2] === k) || g.kinds.slice(0, 2).some(p => p[1] + '\t' + p[2] === k)))};
  if (!ctx.ablate) await db.prepare('INSERT INTO rec_cache(user_id,stamp,body,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET stamp=excluded.stamp,body=excluded.body,created_at=excluded.created_at')
    .bind(ctx.uid, stamp, JSON.stringify(body), Math.floor(ctx.now / 1000)).run();
  return {...body, titles: new Map(body.titles), cached: false};
}

/**
 * 同じ公演が 2 枚出ないよう、同じ題名（正規化した tkey）の束を 1 つにまとめる（起案者の指摘 2026-10-18
 * 「同じ公演が重複して2個あるときがある」「ラブ演劇博が2回出る」）。束の鍵（rec_stage.tour）は題名・団体・作り手の
 * 全部から作るので、会場ごとに出演の行が少し違う、団体名の書き方が違う・片方に無い、などで同じ公演が別の束になる。
 * 題名が同じだけでは、同じ時期に別の団体が同じ題名を上演する場合（『ハムレット』など）まで 1 つにしてしまうので、
 * 次のどれかが合うときだけ同じ公演とみなす: 団体が同じか片方に無い・会場が同じ・作り手に同じ人がいる。
 * 先に来た（点の高い）束を残し、後の束の鍵は aliases に入れて会場を合わせる。読むのは残す分（KEEP）の少し先までの主キーの行だけ。
 */
const NO_NAMES = new Set();
const looseVenue = v => String(v || '').normalize('NFKC').replace(/[\s　]+/gu, '');
export function sameStage(a, b) {
  if (a.g === b.g || !a.g || !b.g) return true;
  if (a.th && a.th === b.th) return true;
  for (const n of a.names) if (b.names.has(n)) return true;
  return false;
}
export async function sameProduction(db, ver, groups, limit = Math.ceil(KEEP * 1.5), answered = []) {
  const head = groups.slice(0, limit);
  const info = new Map();
  const want = [...new Set([...head.map(g => String(g.stage_id)), ...answered.map(String)])];
  // まず題名・団体・会場だけを読む。作り手の一覧（credits）は大きく、全部を読んで解くと Worker の CPU の上限
  // （無料枠は 1 回 10 ミリ秒）を越えて画面が読み込めなくなった（起案者の報告 2026-10-18「読み込めませんでした
  // SyntaxError: Unexpected token '<'」）。作り手は、題名が同じで団体も会場も決め手にならない組だけ、あとで読む
  for (const part of chunks(want, 90)) {
    let results = [];
    try {
      ({results} = await db.prepare(`SELECT stage_id,tkey,gkey,json_extract(entry,'$.theater') AS th FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all());
    } catch { return groups; }
    for (const r of results) if (r.tkey) info.set(String(r.stage_id), {t: r.tkey, g: r.gkey || '', th: r.th || '', names: NO_NAMES});
  }
  const perTitle = new Map();
  for (const [sid, me] of info) { if (!perTitle.has(me.t)) perTitle.set(me.t, []); perTitle.get(me.t).push([sid, me]); }
  const needNames = [];
  for (const list of perTitle.values()) {
    if (list.length < 2) continue;
    for (const [, me] of list) me.th = looseVenue(me.th);   // 会場名の表記ゆれ寄せは、同じ題名が 2 つ以上ある組だけ（重い）
    for (const [sid, me] of list) if (me.g && list.some(([o, x]) => o !== sid && x.g && x.g !== me.g && !(me.th && me.th === x.th))) needNames.push(sid);
  }
  for (const part of chunks(needNames, 90)) {
    let results = [];
    try {
      ({results} = await db.prepare(`SELECT stage_id,credits FROM rec_stage WHERE ver=? AND stage_id IN (${part.map(() => '?').join(',')})`).bind(ver, ...part).all());
    } catch { break; }
    for (const r of results) {
      let cr = [];
      try { cr = JSON.parse(r.credits || '[]'); } catch { /* no credits */ }
      info.get(String(r.stage_id)).names = new Set(cr.filter(c => Array.isArray(c) && !String(c[0]).startsWith('#')).map(c => String(c[1])).filter(Boolean));
    }
  }
  const byTitle = new Map(), out = [];
  // 答えた公演（興味あり・興味なし・購入済・行けない）と同じ公演は出さない（起案者の指摘 2026-10-18「1個だけ興味ありにしたら、
  // もう片方がおすすめに出てきた」── 同じ公演が別の番号で 2 つ載っていると、答えた番号だけが外れていた）
  for (const sid of answered) {
    const me = info.get(String(sid));
    if (!me) continue;
    const kept = byTitle.get(me.t) || [];
    kept.push({g: null, me}); byTitle.set(me.t, kept);
  }
  for (const g of head) {
    const me = info.get(String(g.stage_id));
    if (!me) { out.push(g); continue; }
    const kept = byTitle.get(me.t) || [];
    const keep = kept.find(k => sameStage(me, k.me));
    if (keep && !keep.g) continue;      // 答えた公演と同じ公演
    if (keep) {
      if (g.tour && g.tour !== keep.g.tour) keep.g.aliases = [...new Set([...(keep.g.aliases || []), g.tour])];
      if (!g.tour) keep.g.aliasStages = [...new Set([...(keep.g.aliasStages || []), String(g.stage_id)])];
      continue;
    }
    kept.push({g, me}); byTitle.set(me.t, kept);
    out.push(g);
  }
  return [...out, ...groups.slice(limit)];
}

/**
 * 同じ人が理由の公演が並びすぎないよう並べ直す（起案者の指示 2026-10-15、lit-topic-diversification・
 * lit-popularity-bias）。表示の 1 ページ（TOP 件）ごとに、いちばん強い理由の人が同じ公演は LEAD_CAP 件まで。
 * 越えた分は次のページ以降へ回す（消さない）。理由の人がいない公演（種類だけ）は数えない。
 */
export const LEAD_CAP = 2;
export function spreadLeads(groups, top = TOP, cap = LEAD_CAP) {
  const lead = g => (g.parts[0] ? g.parts[0][1] + '\t' + g.parts[0][2] : '');
  const rest = [...groups], out = [];
  let count = new Map();
  while (rest.length) {
    if (out.length % top === 0) count = new Map();
    let i = rest.findIndex(g => !lead(g) || (count.get(lead(g)) || 0) < cap);
    if (i < 0) i = 0;                                   // every one left is capped: keep the order
    const [g] = rest.splice(i, 1);
    if (lead(g)) count.set(lead(g), (count.get(lead(g)) || 0) + 1);
    out.push(g);
  }
  return out;
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
  // 日程（会場ごとの行と公演日時の暦、会場で違う料金）は、会場ごとの公演の情報から組み直す（schedule.js）
  const info = await stageInfo(ctx.db, rows.flatMap(r => [r.shown, ...(r.venues || []).map(v => v.stage_id)]));
  const out = [];
  let rank = first;
  for (const r of rows) {
    const card = html.get(r.shown);
    if (!card) continue;
    const pic = posters.get(r.shown) || posters.get(r.stage_id);
    const sids = [...new Set([r.shown, ...(r.venues || []).map(v => v.stage_id)].map(String))];
    const tour = tourBlock(sids.map(s => info.get(s)).filter(Boolean), r.shown, ctx.today, ctx.prefs || []);
    out.push(withTour(compose(card, r.shown, 'recommend', {rank: rank++, why: reasonRows(r, titles), poster: pic ? posterHtml(pic) : ''}), tour));
  }
  return out;
}

/** The card with its tour block replaced (or put after the run line when the card had none). */
export function withTour(card, {html, perVenuePrice}) {
  if (!html) return card;
  const old = /<div class="tourfull">(?:<div class="tf-row[^"]*">[\s\S]*?<\/div>)*<\/div>/;
  let out = old.test(card) ? card.replace(old, () => html) : card.replace(/(<div class="when">[\s\S]*?<\/div>)/, (m) => m + html);
  // 会場ごとに料金を書いたカードは、販売の札の横の料金（おすすめに出ている会場の分）を重ねない
  if (perVenuePrice) out = out.replace(/<article class="ticket (\w+)"/, (m) => m + ' data-tourprice="1"');
  return out;
}

/** app.unrated_ends: the dates unrated works ended (no titles), for the nudge in app.js. */
async function unratedEnds(ctx) {
  return (await loadWorks(ctx)).filter(w => !w.verdict && !w.unseen && w.last_date && w.last_date <= ctx.today)
    .map(w => w.last_date).sort();
}

export async function recommendScreen(params, ctx) {
  const prefs = await prefsFor(params, ctx);
  ctx.prefs = prefs;   // ツアーの日程で、絞り込んだ県の会場に ★（schedule.tourBlock）
  const data = await rankedGroups(ctx);
  const nCand = Number((await ctx.db.prepare("SELECT v FROM rec_meta WHERE k='catalogue_upcoming'").first())?.v || 0);
  const {rows, hit} = filtered(data.groups, prefs);
  const cards = await cardsHtml(ctx, rows, data.titles);
  // その日に出した公演（測るための記録 rec_shown。新しく出した公演があるときだけ書く）
  if (data.ready) await recordShown(ctx, 'recommend', rows.map(r => r.shown), `${VERSION}|${data.ver || ''}`);
  const where = prefs.length <= 3 ? prefs.join('・') : `${prefs[0]}ほか ${prefs.length - 1} 県`;
  let head, lede;
  // 候補はあったが、すべて答え終えた（新しく使い始めた人の「まだ候補が無い」とは分ける）
  const allAnswered = !cards.length && !data.groups.length && (data.diag?.ranked || 0) > 0;
  if (!prefs.length && allAnswered) {
    head = '今週のおすすめにはすべて答えました';
    lede = '';
  } else if (!prefs.length && !cards.length) {
    head = '今週のおすすめはありません';
    lede = '';
  } else if (!prefs.length) {
    head = `今週のおすすめ ${cards.length} 件`;
    // 件数は 1 行で（起案者の指示 2026-10-17「『埼玉県ほか 3 県／◯件中上位◯件を表示中』に変えて」。全国も同じ形）
    lede = `<p class="rcount"><b>全国</b>／${data.n_scored} 件中 上位 ${cards.length} 件を表示中</p>`;
  } else if (!cards.length) {
    head = `${where}のおすすめはありません`;
    lede = `<p class="rcount">これから観られる公演 ${nCand} 件のうち、<b>${E(where)}</b>で観られるものはありませんでした。ほかの都道府県を選ぶか、全国に戻してください。</p>`;
  } else {
    head = `${where}のおすすめ ${cards.length} 件`;
    lede = `<p class="rcount"><b>${E(where)}</b>／${hit} 件中 上位 ${cards.length} 件を表示中</p>`;
  }
  // 推薦を出すためのワンポイント（起案者の指示 2026-10-14「なにがしたら出るか、使うユーザーが
  // わかりやすい文章で（技術的なことは書かないで）おすすめの初期画面に追加して」）。
  // 条件は new-user-reco-threshold: 公演とつながった記録が 2 件以上で、評価が 2 種類以上。
  // 一覧の途中で答え終えたときは、画面（app.js）がこの控えを最後のカードの下に出す
  const tips = prefs.length ? '' : allAnswered ? THANKS : !cards.length ? TIPS : `<template id="rec-thanks-t">${THANKS}</template>`;
  const nInterest = (await ctx.db.prepare('SELECT count(DISTINCT stage_id) AS n FROM reaction WHERE user_id=? AND interest=1 AND COALESCE(owned,0)=0').bind(ctx.uid).first())?.n || 0;
  const nSyn = cards.filter(h => /<div class="syn( doubt)?"/.test(h)).length;
  const limits = cards.length ? `<p class="note toinfo"><b>この ${cards.length} 件で、出せていない情報です。</b><br>
・<b>チケットの販売期限と、販売終了・完売</b>：手元に情報がないので表示できません。
チケットが残っているかどうかは公式サイトで確認してください<br>
・<b>あらすじ</b>：${nSyn}/${cards.length} 件で表示できました。残りは、まだ読み取りが済んでいないか、公演のページに載っていませんでした<br>
・<b>まだ答えていない公演は、次回も候補に残ります。</b>
評価・公演情報・設定が変わると、順位も変わることがあります</p>` : '';
  // 件数の 1 行は枠に入れず地の文で、「表示の絞り込み」の下に少し空けて置く（起案者の指示 2026-10-18）
  const body = `<h1>${E(head)}</h1>
${tips}<p class="fgh">${ico('light', 15)}<b>おすすめの選び方</b><span>おすすめに表示される結果自体が変わります。</span></p>
<div class="fil2 tune">${weightForm(data.weights || {}, data.w_counts || {})}${declinedBox(await loadDeclined(ctx))}${kindOffBox(await loadKindOff(ctx))}</div>
<p class="fgh">${ico('search', 15)}<b>表示の絞り込み</b><span>おすすめの候補の中から、表示する項目を設定できます。</span></p>
<div class="fil2 narrow">${prefForm(prefCounts(data.groups), prefs, '/recommend', PAGE_PREF_NOTE, {}, regionCounts(data.groups.map(g => ({key: g.stage_id, prefs: g.venues.map(v => v.pref)}))))}</div>
${lede}
${cards.join('')}
<p class="lede">気になった公演で「興味あり」を押すと、
<a href="/recommend/interest?t=__TAGURI_TOKEN__">「興味あり」（いま ${nInterest} 件）</a>に移ります。</p>
${limits}`;
  return {title: '今週のおすすめ', body_html: body, unrated_ends: await unratedEnds(ctx), diag: data.diag || null};
}

// ---------------------------------------------------------------- react (serve.on_react)
// cantgo（行けない）は interest=2: 答えた公演としておすすめから外し、興味ありの一覧には出さず、好みの手がかりには使う
// 押し間違いをその場で直せるように（起案者の指示 2026-10-17）、購入済み以外を押したら購入済みの印を外す（owned=0）
const REACT = {owned: {owned: 1}, interest: {interest: 1, owned: 0}, nointerest: {interest: 0, owned: 0}, cantgo: {interest: 2, owned: 0}};
const FROM = {reminder: 'reminder', search: 'search', favourites: 'favourites'};

async function reactRow(ctx, stageId, cols, source) {
  const label = ctx.today;
  const v = {interest: null, owned: null, note: null, note_no: null, note_pre: null, why: null, rank: null, score: null, ver: null, arm: null, ...cols};
  await ctx.db.prepare(`INSERT INTO reaction(user_id,label,stage_id,interest,owned,note,note_no,note_pre,why,source,updated_at,rank,score,ver,arm) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(user_id,label,stage_id) DO UPDATE SET interest=COALESCE(excluded.interest,reaction.interest), owned=COALESCE(excluded.owned,reaction.owned),
    note=COALESCE(excluded.note,reaction.note), note_no=COALESCE(excluded.note_no,reaction.note_no), note_pre=COALESCE(excluded.note_pre,reaction.note_pre),
    why=COALESCE(excluded.why,reaction.why),
    rank=CASE WHEN excluded.ver IS NOT NULL THEN excluded.rank ELSE reaction.rank END, score=CASE WHEN excluded.ver IS NOT NULL THEN excluded.score ELSE reaction.score END,
    ver=COALESCE(excluded.ver,reaction.ver), arm=COALESCE(excluded.arm,reaction.arm),
    source=CASE WHEN excluded.interest IS NOT NULL OR excluded.owned IS NOT NULL THEN excluded.source ELSE reaction.source END, updated_at=excluded.updated_at`)
    .bind(ctx.uid, label, stageId, v.interest, v.owned, v.note, v.note_no, v.note_pre, v.why, source, new Date(ctx.now).toISOString(), v.rank, v.score, v.ver, v.arm).run();
}

/** The reasons of one ranked production, small enough to keep (the 4 people and 2 kinds reasonRows shows, and their titles). */
export function whyOf(g, titles) {
  const parts = g.parts.slice(0, 4), kinds = g.kinds.slice(0, 2);
  const keys = [...parts, ...kinds].map(p => p[1] + '\t' + p[2]);
  return {parts, kinds, ...(g.via ? {via: g.via} : {}), titles: keys.filter(k => titles.has(k)).map(k => [k, titles.get(k)])};
}

/**
 * 興味ありを押したときに見えていた理由（reaction.why）。押す前のおすすめの控え（rec_cache）は、その画面を
 * 出したときのものなので、印を確かめずに読む（D1 の読み取り 1 行。ticker.js と同じ）。無ければ残さない。
 */
function whySnapshot(body, stageId) {
  if (!body) return null;
  const g = (body.groups || []).find(x => x.stage_id === stageId || (x.venues || []).some(v => v.stage_id === stageId));
  return g ? JSON.stringify(whyOf(g, new Map(body.titles || []))) : null;
}

/** serve.fill_slot: the next card in place of the one answered, honouring the saved prefectures. */
async function fillSlot(ctx, shown, pressed, page = null) {
  if (!shown.length) return {html: '', left: 0, said: ''};
  // そのページで絞った県（画面が URL から送る）。無ければ設定の県
  const prefs = await prefsFor(page ? new URLSearchParams([['f', '1'], ...page.map(p => ['pref', p])]) : new URLSearchParams(), ctx);
  ctx.prefs = prefs;
  const data = await rankedGroups(ctx);
  const {rows} = filtered(data.groups, prefs, 1e6);
  const seen = new Set([...shown.map(String), String(pressed)]);
  // 画面に出ている公演は、どの会場の番号で出ていても足さない（束の代表の会場は、答えるたびの並べ直しで変わる）
  const onScreen = r => [r.stage_id, r.shown, ...(r.venues || []).map(v => v.stage_id)].some(x => seen.has(String(x)));
  const rest = rows.filter(r => !onScreen(r));
  if (!rest.length) return {html: '', left: 0, said: '記録しました。入れ替える候補はもうありません。好みに合いそうだと判断できた分は出し切りました。'};
  const [card] = await cardsHtml(ctx, rest.slice(0, 1), data.titles, shown.length + 1);
  return {html: card || '', left: rest.length,
    said: `記録しました。入れ替わりに 1 件を下に足しました。まだ出していない候補が ${rest.length - 1} 件あります。`};
}

export async function reactAction(b, ctx) {
  const stageId = String(b.stage_id ?? ''), value = String(b.value ?? '');
  if (b.fill_only) {
    if (!stageId) throw new ValueError('stage_id が要る');
    const shown = (Array.isArray(b.shown) ? b.shown : []).slice(0, 120).map(x => String(x).slice(0, 20));
    const page = Array.isArray(b.prefs) ? b.prefs.slice(0, 47).map(x => String(x).slice(0, 8)) : null;
    return {body: {ok: true, stage_id: stageId, fill: await fillSlot(ctx, shown, stageId, page)}};
  }
  const given = {};
  for (const k of ['note', 'note_no', 'note_pre']) if (b[k] !== undefined && b[k] !== null) given[k] = String(b[k]).slice(0, 2000);
  if (!stageId || !/^[A-Za-z0-9_-]{1,40}$/.test(stageId) || (!Object.hasOwn(REACT, value) && !Object.keys(given).length))
    throw new ValueError('stage_id と、value（owned / interest / nointerest / cantgo）か理由が要る');
  // どの画面で答えたか（起案者の指示 2026-10-15: 開幕リマインドから足した興味ありは、おすすめ理由の欄ではなく
  // 「開幕リマインドからの追加」と出す）。画面（app.js）が from を送る。無ければこれまでどおり 'screen'。
  const source = Object.hasOwn(FROM, String(b.from ?? '')) ? FROM[String(b.from)] : 'screen';
  // おすすめの画面で押した興味ありは、そのとき見えていた理由も残す（興味ありの画面で出す。答えた公演は
  // おすすめの計算から外れるので、あとからは作れない）
  // 答えたときの順位・点・版（測るための記録。real-data-eval-plan §5）も、同じ控えの 1 回の読み出しから取る。
  // どの画面で答えても残す（開幕リマインドの答えにも、そのときの点が要る）。理由だけを書き足す行には付けない
  const snap = Object.hasOwn(REACT, value) ? await answerSnapshot(ctx, stageId, VERSION) : {body: null, eval: null};
  const ev = snap.eval || {};
  const why = value === 'interest' && source === 'screen' ? whySnapshot(snap.body, stageId) : null;
  await reactRow(ctx, stageId, {...(REACT[value] || {}), ...given, ...(why ? {why} : {}), ...ev}, source);
  if (Object.hasOwn(REACT, value) && Array.isArray(b.siblings)) {
    // The same answer for the production's other venues (the card's data-tours); notes stay on the pressed one.
    for (const sid of b.siblings.slice(0, 40).map(String).filter(s => /^\d+$/.test(s) && s !== stageId))
      await reactRow(ctx, sid, {...REACT[value], ...(why ? {why} : {}), ...ev}, source + '_tour');
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
