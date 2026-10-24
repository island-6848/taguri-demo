// 探す: app._search_body ported to the Worker (起案者の指示 2026-10-14「残りの画面も順に移して」),
// and the search_request write.
//
// Same layout and words. Where Python reads files on the server, the Worker reads D1:
// the coming stages are every stage of the index (rec_stage) that has not ended, plus the
// delivered catalogue's stages the index does not have yet — with or without a prebuilt card
// (起案者の指示 2026-10-17「カードがない新しい公演も検索で出るようにして」; a stage without a
// card is drawn by fallback.fallbackTemplate). They are matched in SQL first (instr over the
// texts) and then checked here like app._hit_upcoming; a work's people come from its linked
// stage (diary.peopleByKey).
// Not available: the subject words of the works seen (themes.jsonl of the rated side is
// the owner's batch output) and the live CoRich search (the public service asks the next
// daily run instead, as the Python service does).
import {scaleOf} from './grade.js';
import {E, ValueError} from './py.js';
import {ico, h2} from './icons.js';
import {compose, cardTemplates, posterHtml as cardPoster} from './cards.js';
import {recRow, stageLabels} from './row.js';
import {posterHtml, posterFiles, indexTabs} from './rate.js';
import {peopleByKey} from './diary.js';
import {parseCredits} from './credits.js';
import {loadWorks, titleKey} from './works.js';
import {loadDeclared, buckets, nz, pastFromIndex} from './lists.js';
import {titleKey as indexKey, titlePrefixes, pastByPrefix} from '../stage-search.js';
import {stageInfo, fallbackTemplate} from './fallback.js';
import {tourBlock} from './schedule.js';
import {withTour} from './recommend.js';
import {runRange, periodStart} from './reminder.js';
import {nextCrawl, crawlsSince, crawlLabel, jstDay, crawlSearch} from '../crawl-time.js';

const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
// 波ダッシュの揺れ（〜 U+301C と ～ U+FF5E など）は NFKC でも 1 つにならない。取得元は「ふぉ～ゆ～」、
// 打つと「ふぉ〜ゆ〜」になりやすい（起案者の検索 2026-10-17 で 0 件だった）ので、どれも ~ にそろえて比べる
const WAVES = /[\u301c\uff5e\u223c\u2053\u02dc]/gu;
const fold = s => String(s || '').normalize('NFKC').replace(WAVES, '~');
/** render_recommend._norm (plus the wave dashes folded) */
const norm = s => fold(String(s || '').replace(/\s+/gu, ''));
/** The SQL side of `fold` for a column (NFKC already turns ～ into ~ in the prebuilt texts, not in entry JSON). */
const sqlFold = col => `replace(replace(replace(${col},'〜','~'),'～','~'),'∼','~')`;
const chunks = (xs, n) => Array.from({length: Math.ceil(xs.length / n)}, (_, i) => xs.slice(i * n, i * n + n));
const DATE_RE = /(20\d\d)\/(\d{1,2})\/(\d{1,2})/g;

/** app._period_months */
function periodMonths(period, cap = 18) {
  const ms = [...String(period || '').matchAll(DATE_RE)];
  if (!ms.length) return [];
  const a = Number(ms[0][1]) * 12 + Number(ms[0][2]) - 1;
  let b = Number(ms.at(-1)[1]) * 12 + Number(ms.at(-1)[2]) - 1;
  b = Math.max(a, Math.min(b, a + cap));
  return Array.from({length: b - a + 1}, (_, i) => a + i).map(k => `${String(Math.floor(k / 12)).padStart(4, '0')}-${String(k % 12 + 1).padStart(2, '0')}`);
}

/** app._hit_why for a work seen: [html, names] */
function hitWhy(q, w, people) {
  const key = norm(q);
  const who = (people || []).filter(([, person]) => norm(person).includes(key));
  const why = [];
  if (norm(w.title).includes(key)) why.push(['題名', '']);
  for (const [role, person] of who.slice(0, 6)) why.push([role, person]);
  if (!why.length) return ['', []];
  const body = why.map(([k, v]) => (v ? `<span class="hw"><span class="k">${E(k)}</span>${E(v)}</span>` : `<span class="hw">${E(k)}</span>`)).join('');
  return [`<div class="hitwhy"><span class="hl">ヒットした箇所：</span>${body}</div>`, why.filter(([k]) => k !== '題名' && k !== '題材')];
}

/** app._hit_upcoming: [html, names] */
function hitUpcoming(q, c, themes) {
  const key = norm(q);
  const why = [], names = [];
  if (norm(c.title).includes(key)) why.push(['題名', '']);
  if (norm(c.group).includes(key)) { why.push(['団体', c.group || '']); names.push(['団体', c.group || '']); }
  for (const [role, person] of parseCredits(c.fields || {})) if (norm(person).includes(key)) { why.push([role, person]); names.push([role, person]); }
  // 名前の後ろの括弧（所属。例「越岡裕貴（ふぉ～ゆ～）」）は名前の読み取りで外れるので、欄の文そのものでも当てる。
  // 出すのは当たった区切り（、・改行）の 1 つ
  if (why.length === (norm(c.title).includes(key) ? 1 : 0) + (norm(c.group).includes(key) ? 1 : 0)) {
    for (const [field, text] of Object.entries(c.fields || {})) {
      const part = String(text || '').split(/[、,，\n]/).map(x => x.trim()).find(x => norm(x).includes(key));
      if (part) why.push([field, part.slice(0, 40)]);
    }
  }
  const th = (themes || []).filter(t => norm(t).includes(key));
  if (th.length) { why.push(['題材', th.slice(0, 4).join('・')]); names.push(...th.map(t => ['題材', t])); }
  if (norm(c.theater).includes(key)) why.push(['劇場', c.theater || '']);
  if (!why.length) return ['', []];
  const seen = new Set(), out = [];
  for (const [k, v] of why) {
    const s = k + '\u0000' + v;
    if (seen.has(s)) continue;
    seen.add(s);
    out.push(v ? `<li class="rs found"><span class="net">${E(k)}</span>${E(v)}</li>` : `<li class="rs found"><span class="net">${E(k)}</span></li>`);
  }
  return [out.slice(0, 6).join(''), names];
}

const slashed = (a, b) => (a ? `${a.replaceAll('-', '/')} ～ ${(b || a).replaceAll('-', '/')}` : '');
// 一覧（catalogue）は終わった公演の行も残るので、初日が 1 年以内の行だけを日付の索引で読む（D1 の読み取りを抑える）
const CATALOGUE_SINCE_DAYS = 366;
const since = today => new Date(Date.parse(today + 'T00:00:00Z') - CATALOGUE_SINCE_DAYS * 86400000).toISOString().slice(0, 10);

/**
 * The coming stages, with or without a card: the index's stages that have not ended, then the
 * catalogue's that the index does not have yet. `q` narrows them in SQL (folded, lower-cased).
 */
async function upcoming(ctx, q = '') {
  const key = q ? nz(fold(q)) : '';
  const out = new Map();
  const idxWhere = key ? ` AND (instr(${sqlFold('c.blob')},?)>0 OR instr(${sqlFold('c.ws')},?)>0 OR instr(${sqlFold('lower(s.entry)')},?)>0 OR instr(${sqlFold('lower(s.title)')},?)>0)` : '';
  const {results} = await ctx.db.prepare(`SELECT s.stage_id, s.title, s.entry, s.start, s.end, s.tour, c.ws FROM rec_stage s
    LEFT JOIN rec_card c ON c.stage_id=s.stage_id AND c.ver=(SELECT v FROM rec_meta WHERE k='rec_card')
    WHERE s.ver=(SELECT v FROM rec_meta WHERE k='current') AND (s.end='' OR s.end>=?)${idxWhere}`)
    .bind(ctx.today, ...(key ? [key, key, key, key] : [])).all();
  for (const r of results) {
    let e = {};
    try { e = JSON.parse(r.entry || '{}') || {}; } catch { /* no entry */ }
    out.set(String(r.stage_id), {...e, period: e.period || slashed(r.start, r.end), title: r.title, stage_id: String(r.stage_id), _tour: r.tour || '', _ws: r.ws ? r.ws.split('\n') : []});
  }
  // 索引に入る前の新しい公演（毎日の一覧の配達には入っている）
  const catWhere = key ? ` AND (instr(${sqlFold('lower(title)')},?)>0 OR instr(${sqlFold('lower(metadata)')},?)>0)` : '';
  let cat = [];
  try {
    ({results: cat} = await ctx.db.prepare(`SELECT c.id, c.title, c.date, c.venue, c.metadata, vp.pref AS vpref FROM catalogue c LEFT JOIN venue_pref vp ON vp.venue=c.venue
      WHERE c.date>=? AND COALESCE(json_extract(c.metadata,'$.end_date'), c.date)>=?${catWhere}`).bind(since(ctx.today), ctx.today, ...(key ? [key, key] : [])).all());
  } catch { cat = []; }
  for (const r of cat) {
    const sid = String(r.id);
    if (out.has(sid)) continue;
    let m = {};
    try { m = JSON.parse(r.metadata || '{}') || {}; } catch { /* no metadata */ }
    const end = /^\d{4}-\d{2}-\d{2}$/.test(m.end_date || '') ? m.end_date : r.date;
    out.set(sid, {stage_id: sid, title: r.title, period: slashed(r.date, end), theater: r.venue || '', venue: r.venue || '', pref: r.vpref || '',
      group: m.group || '', fields: m.fields && typeof m.fields === 'object' ? m.fields : {}, _ws: Array.isArray(m.words) ? m.words.map(String) : []});
  }
  return [...out.values()];
}

/** {month: stages} of these stages, from this month on (app._up_month_counts). */
function monthCounts(rows, today) {
  const now = today.slice(0, 7), out = {};
  for (const r of rows) for (const m of periodMonths(r.period)) if (m >= now) out[m] = (out[m] || 0) + 1;
  return out;
}
/**
 * Coming stages counted by month, without a word: only the dates are read (no entry JSON to parse).
 * 誰が開いても同じ数なので、索引の版・一覧の配達・日付ごとに 1 度だけ数えて rec_meta に置く（compare.population と同じ形）。
 * 前は探すを開くたびにこれからの公演を全部（約 5,100 行）読んでいた（issue #242、D1 の 1 日の読み出しの無料枠）
 */
async function upcomingMonths(ctx) {
  const {results: meta} = await ctx.db.prepare("SELECT k, v FROM rec_meta WHERE k IN ('current','catalogue_delivered','search_months')").all();
  const m = Object.fromEntries(meta.map(r => [r.k, r.v]));
  const stamp = `${m.current || ''}|${m.catalogue_delivered || ''}|${ctx.today}`;
  if (m.search_months) { try { const p = JSON.parse(m.search_months); if (p.stamp === stamp) return {counts: p.counts, n: p.n}; } catch { /* count again */ } }
  const counted = await countUpcomingMonths(ctx);
  try {
    await ctx.db.prepare("INSERT INTO rec_meta(k,v) VALUES('search_months',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(JSON.stringify({stamp, ...counted})).run();
  } catch { /* 書けなくても数は出す（保存の上限など） */ }
  return counted;
}
async function countUpcomingMonths(ctx) {
  const [idx, cat] = await ctx.db.batch([
    ctx.db.prepare("SELECT stage_id, start, end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND (end='' OR end>=?)").bind(ctx.today),
    ctx.db.prepare("SELECT id, date, json_extract(metadata,'$.end_date') AS end FROM catalogue WHERE date>=? AND COALESCE(json_extract(metadata,'$.end_date'), date)>=?").bind(since(ctx.today), ctx.today)]);
  const rows = new Map(idx.results.map(r => [String(r.stage_id), {period: slashed(r.start, r.end)}]));
  for (const r of cat.results) if (!rows.has(String(r.id))) rows.set(String(r.id), {period: slashed(r.date, r.end || r.date)});
  return {counts: monthCounts([...rows.values()], ctx.today), n: rows.size};
}

// ---------------------------------------------------------------- 過去の公演（2019 年〜）
// 起案者の指示（2026-10-17）「『探す』で興味ありにもお気に入りにも観たわけでもないけど、過去の公演表示させることできる？」
// →「ボタン 2 つで入れて」: 観た（日記帳に足して公演に結び付ける）／観ればよかった（見逃した公演の一覧）。
// 引き方は 2 つだけ（どちらも past_stage を全部は読まない）: 題名の先頭一致（tkey の索引。「舞台」などの頭の語の後ろも）と、人・団体の名前の
// 完全一致（R2 の名前の索引 pastidx、lists.pastFromIndex）。途中の語や、名前の後ろの括弧（所属）では当たらない
// 見つかった過去の公演は全部出す（起案者の指示 2026-10-19「検索結果、新しい順から15件表示するのではなく、ちゃんと全件表示して」。
// 前は新しい順に 15 件まで）。題名で引く行は、短い言葉で何千行も読まないよう PAST_TITLE_ROWS 行まで（D1 の読み取りの無料枠。
// 1 回の検索で多くて 600 行）。それを越えたときは、そう書く
const PAST_TITLE_ROWS = 1000;
// 見つかった分は全部たどれるよう、ページ送りを付ける（起案者の指示 2026-10-19「ちゃんと全件表示して。サーバーで問題があるならページ送りを
// つけて」）。これから観られる公演はカード（1 枚ごとに D1 を読み、組み立てに Worker の CPU を使う）なので 1 ページ UP_PER 件、
// 過去の公演は文字だけの行なので 1 ページ PAST_PER 件
export const UP_PER = 5, PAST_PER = 5;   // 起案者の指示 2026-10-19「『これから観られる公演』『過去の公演』は 5 件ずつ表示し、ページ送りで最後までたどる」
/** 「← 前の n 件 ／ p / last ページ ／ 次の n 件 →」。href(p) はそのページへの道 */
export function pagerHtml(total, per, page, href) {
  const last = Math.max(1, Math.ceil(total / per));
  if (last <= 1 || !href) return '';
  return `<div class="mfoot">${page > 1 ? `<a class="mpage" href="${href(page - 1)}">← 前の ${per} 件</a>` : '<span class="mpage off">最初のページです</span>'}`
    + `<span class="mp">${page} / ${last} ページ</span>`
    + `${page < last ? `<a class="mpage" href="${href(page + 1)}">次の ${Math.min(per, total - page * per)} 件 →</a>` : '<span class="mpage off">これで最後です</span>'}</div>`;
}
const md = d => (/^\d{4}-\d{2}-\d{2}$/.test(d || '') ? `${d.slice(0, 4)}/${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}` : '');

export async function pastHits(ctx, q, ws, page = 1, href = null) {
  const linked = new Set(ws.map(w => w.stage_id).filter(Boolean).map(String));
  const rows = new Map();
  let capped = false;
  const add = (r, why) => {
    const sid = String(r.stage_id);
    if (!r.end || r.end >= ctx.today || linked.has(sid)) return;
    const had = rows.get(sid);
    if (had) { if (!had.why.includes(why)) had.why.push(why); } else rows.set(sid, {...r, stage_id: sid, why: [why]});
  };
  const k = indexKey(q);
  if (Array.from(k).length >= 2) {
    // 「舞台」「ミュージカル」など題名の頭に付く語の後ろも先頭一致で引く（stage-search.titlePrefixes、起案者の指摘 2026-10-19）
    const results = await pastByPrefix(ctx.db, 'stage_id,title,tkey,start,end,venue,grp', titlePrefixes(k), PAST_TITLE_ROWS);
    capped = results.length >= PAST_TITLE_ROWS;
    for (const r of results) add(r, '題名');
  }
  for (const key of [...new Set([nz(q), nz(fold(q))])].filter(x => Array.from(x).length >= 2)) {
    for (const r of (await pastFromIndex(ctx, key)) || []) add(r, '出演・作り手・団体');
  }
  // ツアーは 1 行に（お気に入りのハッシュタグの画面と同じ: 題名の鍵と団体が同じ行をまとめる）
  const groups = new Map();
  for (const r of rows.values()) {
    const g = (r.tkey || nz(r.title)) + '\u0000' + nz(r.grp);
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(r);
  }
  const prods = [...groups.values()].map(g => {
    g.sort((a, b) => cmp(a.start, b.start));
    const venues = [...new Set(g.map(r => r.venue).filter(Boolean))];
    return {sid: g[0].stage_id, title: g[0].title, grp: g[0].grp || '', start: g[0].start, end: g.map(r => r.end).sort().at(-1),
      where: venues.length > 1 ? `${venues[0]} ほか ${venues.length - 1} 会場` : (venues[0] || ''), why: [...new Set(g.flatMap(r => r.why))],
      legs: g.map(r => ({sid: r.stage_id, start: r.start || '', end: r.end || '', venue: r.venue || ''}))};
  }).sort((a, b) => cmp(b.start, a.start));
  if (!prods.length) return ['', 0];
  const {results: miss} = await ctx.db.prepare('SELECT title FROM missed WHERE user_id=?').bind(ctx.uid).all();
  const missed = new Set(miss.map(m => indexKey(m.title)));
  const last = Math.max(1, Math.ceil(prods.length / PAST_PER));
  page = Math.min(Math.max(1, page), last);
  const li = prods.slice((page - 1) * PAST_PER, page * PAST_PER).map(p => {
    const run = p.start === p.end ? md(p.start) : `${md(p.start)}〜${md(p.end)}`;
    const isMissed = missed.has(indexKey(p.title));
    // 観た日の欄: 1 日だけの公演はその日を入れておく。期間の外は選べない（min/max）
    const one = p.start === p.end ? p.start : '';
    // ツアーは劇場ごとに公演が別（stage_id が違う）。観た日からその日に上演していた劇場を選び直す（画面の app.js）。
    // 日が重なる劇場が 2 つあるときや、日を入れる前は、ここで選べる（起案者の指摘 2026-10-18「適切な観劇日を入れても
    // 観劇した劇場がその日と対応しない」── 前は代表の 1 劇場にしか結び付かなかった）
    const legSel = p.legs.length > 1 ? `<label>劇場 <select name="stage">${p.legs.map(l =>
      `<option value="${E(l.sid)}" data-start="${E(l.start)}" data-end="${E(l.end)}" data-venue="${E(l.venue)}">${E(l.venue || '劇場不明')}（${E(l.start === l.end ? md(l.start) : `${md(l.start)}〜${md(l.end)}`)}）</option>`).join('')}</select></label>` : '';
    const seenForm = `<div class="past-seen" hidden><label>観た日 <input type="date" name="date" value="${E(one)}" min="${E(p.start || '')}" max="${E(p.end || '')}" required></label>`
      + `${legSel}<label>開演 <input type="time" name="time" step="60"></label><button type="button" data-past="seen-save">観劇記録に追加</button></div>`;
    return `<li class="pastrow" data-stage="${E(p.sid)}" data-title="${E(p.title)}">
<div class="past-t"><b>${E(p.title)}</b>${p.grp ? `<span class="past-g">${E(p.grp)}</span>` : ''}</div>
<div class="past-w">${E(run)}${p.where ? '・' + E(p.where) : ''}</div>
<div class="past-why">ヒットした箇所：${p.why.map(E).join('・')}</div>
<div class="past-btns"><button type="button" data-past="seen">観た</button>`
      + `<button type="button" data-past="missed"${isMissed ? ' disabled' : ''}>${isMissed ? '行けばよかったに入っています' : '行けばよかった'}</button></div>${seenForm}<span class="said"></span></li>`;
  }).join('');
  const more = capped ? `<p class="lead">題名で当たる公演が多いので、題名の順に ${PAST_TITLE_ROWS} 公演までを読んで出しています。言葉を足すと絞れます。</p>` : '';
  return [`<h2>過去の公演（2019 年〜） ${prods.length} 件</h2>
<p class="lead">終わった公演のうち、まだ日記帳に無いものです。<b>「観た」</b>を押して観た日を入れると、観劇記録に追加して、その公演と結び付けます。開演の時刻も入れられます。<b>「行けばよかった」</b>を押すと、見逃した公演の一覧に入ります。
題名は先頭から一致するもの、人・団体は名前全体が一致するものを探しています。</p>${more}<ul class="pastlist" id="past-hits">${li}</ul>${pagerHtml(prods.length, PAST_PER, page, href)}`, prods.length];
}

/** app._search_follow */
function searchFollow(dec, names) {
  const have = new Set(Object.entries(dec).flatMap(([k, ns]) => ns.map(n => k + '\u0000' + norm(n))));
  const seen = new Set(), out = [];
  for (const [role, name] of names) {
    const kind = role === '題材' ? '題材' : '人';
    if (have.has(kind + '\u0000' + norm(name)) || seen.has(kind + '\u0000' + name)) continue;
    seen.add(kind + '\u0000' + name);
    out.push(`<div class="prom"><span class="k">${E(kind)}</span><span class="w">${E(name)}</span>`
      + `<button data-fav="promote" data-kind="${E(kind)}" data-name="${E(name)}">これは追う</button><span class="said"></span></div>`);
  }
  if (!out.length) return '';
  return `<div class="card">${h2('star', 'この名前を追いますか？', `<span class="badge part">${out.length} 件</span>`)}
<p class="lead">お気に入りに登録すると、<b>これから始まるこの名前の公演が、
件数の制限も条件も付けずにお気に入りの新着に出ます。</b>いま探している名前を、ここから登録できます。</p>
${out.slice(0, 8).join('')}</div>`;
}

/** The card's other venues (data-tours): answering the card gives them the same answer (screens/recommend.reactAction). */
const withSiblings = (card, sibs) => {
  const v = E(sibs.filter(x => /^\d+$/.test(x)).join(','));
  return /<article class="ticket [^"]*" data-stage="[^"]*" data-tours="[^"]*"/.test(card)
    ? card.replace(/(<article class="ticket [^"]*" data-stage="[^"]*") data-tours="[^"]*"/, (m, a) => `${a} data-tours="${v}"`)
    : card.replace(/(<article class="ticket [^"]*" data-stage="[^"]*")/, (m, a) => `${a} data-tours="${v}"`);
};

/** app._upcoming_hits: [html, names, n, {month: n} of the stages the word hits (empty without a word), stages the word hits in any month] */
export async function upcomingHits(ctx, q, ym, b, top = UP_PER, page = 1, href = null) {
  const rows = await upcoming(ctx, q);
  const state = new Map();
  for (const [k, lab] of [['tracking', '追いかけています（興味ありと答えました）'], ['owned', '観る予定です（すでに持っていると答えました）'], ['others', '興味なしと答えました']])
    for (const r of b[k]) for (const sid of r.sids || [r.stage_id]) state.set(sid, r.dismissed ? '候補から消しました' : r.cantgo ? '行けないと答えました' : lab);
  const tracking = new Set(b.tracking.flatMap(r => r.sids || [r.stage_id]));
  let hits = [];
  for (const c of rows) {
    if (ym && !periodMonths(c.period).includes(ym)) continue;
    const [why, names] = q ? hitUpcoming(q, c, c._ws) : [`<li class="rs found"><span class="net">上演</span>${E(runRange(c.period, ctx.today) || c.period || '')}</li>`, []];
    if (why) hits.push([c.stage_id, c, why, names]);
  }
  if (ym) {
    const key = x => {
      const st = periodStart(x[1].period) || '9999';
      const ends = [...String(x[1].period || '').matchAll(DATE_RE)];
      const en = ends.length ? `${ends.at(-1)[1]}-${ends.at(-1)[2].padStart(2, '0')}-${ends.at(-1)[3].padStart(2, '0')}` : '9999';
      return st.slice(0, 7) === ym ? [0, st] : [1, en];
    };
    hits.sort((p, q2) => { const a = key(p), c2 = key(q2); return (a[0] - c2[0]) || cmp(a[1], c2[1]); });
  } else {
    hits.sort((p, q2) => cmp(periodStart(p[1].period) || '9999', periodStart(q2[1].period) || '9999'));
  }
  // ツアーは 1 枚にまとめる（起案者の指示 2026-10-20「ツアーがバラバラに出ていて、バラバラに興味ありを押せるようになってしまってる。
  // まとめて」）。索引の同じ tour（おすすめと同じ束ね方）、索引に無い新しい公演は題名と団体で束ねる。並びの先頭（いちばん早い会場）を
  // 代表にし、ほかの会場はカードの日程とボタン（data-tours。答えると全会場に同じ答えが付く）に入れる
  const groupKey = c => c._tour || 't:' + indexKey(c.title || '') + '\u0000' + nz(c.group || '');
  const byGroup = new Map();
  for (const h of hits) {
    const k = groupKey(h[1]);
    if (byGroup.has(k)) { byGroup.get(k).sids.push(String(h[0])); byGroup.get(k).names.push(...h[3]); continue; }
    byGroup.set(k, {h, sids: [String(h[0])], names: [...h[3]]});
  }
  const venuesOf = new Map([...byGroup.values()].map(g => [String(g.h[0]), g.sids]));
  hits = [...byGroup.values()].map(g => [g.h[0], g.h[1], g.h[2], g.names]);
  const names = hits.flatMap(h => h[3]);
  // 言葉で引いたときの月ごとの数（カレンダーも当たった公演だけを数える。月の指定より前の全部）
  const matched = q ? rows.filter(c => hitUpcoming(q, c, c._ws)[0]) : rows;
  const counts = q ? monthCounts(matched, ctx.today) : {};
  if (!hits.length) return ['', [], 0, counts, matched.length];
  const lastUp = Math.max(1, Math.ceil(hits.length / top));
  page = Math.min(Math.max(1, page), lastUp);
  const show = hits.slice((page - 1) * top, page * top);
  const {html, posters} = await cardTemplates(ctx.db, show.map(h => h[0]));
  // カードがまだ無い公演（新しい公演など）は、一覧と索引の中身から描く（fallback.js）
  const bare = show.map(h => h[0]).filter(sid => !html.has(sid));
  if (bare.length) for (const [sid, st] of await stageInfo(ctx.db, bare)) html.set(sid, fallbackTemplate(st));
  // 日程は、おすすめと同じ会場ごとの行（「このおすすめの日程」の札は使わない。起案者の指示 2026-10-17）
  // ツアーのほかの会場は、索引の同じ tour の公演（rec_stage.tour）
  const ids = show.map(h => String(h[0]));
  const tourOf = new Map(), byTour = new Map();
  if (ids.length) {
    const {results} = await ctx.db.prepare(`SELECT stage_id, tour FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${ids.map(() => '?').join(',')})`).bind(...ids).all();
    for (const r of results) if (r.tour) tourOf.set(String(r.stage_id), r.tour);
    const tours = [...new Set(tourOf.values())];
    if (tours.length) {
      const {results: sib} = await ctx.db.prepare(`SELECT stage_id, tour FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND tour IN (${tours.map(() => '?').join(',')})`).bind(...tours).all();
      for (const r of sib) { if (!byTour.has(r.tour)) byTour.set(r.tour, []); byTour.get(r.tour).push(String(r.stage_id)); }
    }
  }
  const tourSids = new Map(ids.map(sid => [sid, [sid, ...(venuesOf.get(sid) || []), ...(byTour.get(tourOf.get(sid)) || [])]]));
  const info = await stageInfo(ctx.db, [...tourSids.values()].flat());
  const cards = show.filter(h => html.has(h[0])).map(([sid, , why]) => {
    const all = [...new Set(tourSids.get(String(sid)))];
    // 答えはどの会場に付いていても、そのツアーの答え
    const st = all.map(x => state.get(x)).find(Boolean);
    const w = why + (st ? `<li class="rs state">${E(st)}</li>` : '');
    const pic = posters.get(sid) || all.map(x => posters.get(x)).find(Boolean);
    const card = compose(html.get(sid), sid, all.some(x => tracking.has(x)) ? 'interest' : 'recommend', {top: w, poster: pic ? cardPoster(pic) : ''});
    return withSiblings(withTour(card, tourBlock(all.map(x => info.get(x)).filter(Boolean), sid, ctx.today)), all.filter(x => x !== String(sid)));
  });
  const tail = '';
  const pager = pagerHtml(hits.length, top, page, href);
  const head = ym ? `${ym.slice(0, 4)} 年 ${Number(ym.slice(5, 7))} 月に観られる公演` : '今後の公演';
  const order = ym ? 'この月に始まる公演を先に並べ、そのあとに、すでに始まっている公演を終わりの近い順に並べています。' : '上演日の近い順に並べています。';
  return [`<h2>${E(head)} ${hits.length} 件</h2><p class="lead">${order}順位は付けていません。<b>ここから「興味あり」を押すと、「興味あり」の一覧に入ります。</b></p>${tail}<div id="up-hits">${cards.join('')}</div>${pager}`, names, hits.length, counts, matched.length];
}

/** app._request_query */
function requestQuery(q) {
  const w = String(q || '').normalize('NFKC').replace(/\s+/gu, ' ').trim();
  if (Array.from(w).length < 2 || Array.from(w).length > 60 || Array.from(titleKey(w)).length < 2) return '';
  if ([...w].some(c => c.charCodeAt(0) < 32) || w.includes('://') || w.includes('@') || w.toLowerCase().includes('www.')) return '';
  return w;
}
const MAX_REQUESTS = 30;
/**
 * app._web_hits for the public service: ask the next daily run instead of searching now.
 * 依頼のあとの様子（#101）: 控えにあるのは依頼した日（search_request.created_at）だけで、取得が探したか・
 * 見つからなかったか・失敗したかは D1 に記録していない。なので「依頼した」「そのあと更新が n 回あった」までを書き、
 * 分からないことは分からないと書く。次回の日時は crawl-time.js の 1 つの決まりから作る。
 */
async function webHits(ctx, q, found = 0) {
  if (!requestQuery(q)) return '<p class="note">たぐりの公演一覧から検索できます。</p>';
  const next = crawlLabel(nextCrawl(ctx.now));
  const manual = '観た公演なら、<a href="/register?t=__TAGURI_TOKEN__">観劇記録を追加</a>で題名と日付を手で入れても記録できます。';
  const have = await ctx.db.prepare('SELECT created_at FROM search_request WHERE user_id=? AND qkey=?').bind(ctx.uid, titleKey(requestQuery(q))).first();
  if (have) {
    const at = Date.parse(have.created_at);
    const asked = Number.isFinite(at) ? `${jstDay(at)}に` : '';
    let lead;
    if (!crawlSearch.requests) {
      lead = `「${E(q)}」は${asked}依頼を控えました。<b>ただ、依頼された題名を毎日の更新で探す段はまだ準備中で、まだ探していません。</b>`
        + `準備ができたら、そのあとの更新で探します。公演一覧そのものは毎日更新しています（次回は${next}）。${manual}`;
    } else {
      const n = Number.isFinite(at) ? crawlsSince(at, ctx.now) : 0;
      lead = n === 0
        ? `「${E(q)}」は${asked}、CoRich から探すよう依頼済みです。<b>次回は${next}の更新で探します</b>（更新は遅れることがあります）。見つかれば、その更新のあとからこの画面と「手で足す」の候補に出ます。`
        : `「${E(q)}」は${asked}依頼済みです。そのあと更新が ${n} 回ありましたが、${found ? 'ここに出ている公演のほかには' : ''}<b>まだたぐりの公演一覧に入っていません。</b>`
          + '探して見つからなかったのか、まだ順番が来ていないのか（1 回に探す件数には上限があります）、探せなかったのかは、いまは記録していないので、この画面では分かりません。'
          + `次回は${next}の更新です。副題や団体名を外して短くすると見つかることがあります。${manual}`;
    }
    return `<div class="webq" id="web"><p class="lead">${lead}</p></div>`;
  }
  const ask = crawlSearch.requests
    ? `<b>そこに無い公演は、次の更新（次回は${next}）で CoRich から探すよう頼めます。</b>見つかれば、その更新のあとからこの画面と「手で足す」の候補に出ます。`
    : `そこに無い公演は、探してほしいと依頼を控えておけます。<b>ただ、依頼された題名を毎日の更新で探す段はまだ準備中で、いまは探されません。</b>${manual}`;
  return `<div class="webq" id="web"><p class="lead">この画面はその場では CoRich を検索せず、毎日の更新で集めた公演から探します。${ask}</p>`
    + `<button type="button" data-search-request="${E(q)}" data-source="search">${ico('search')}「${E(q)}」を次の更新で探してもらう</button><span class="said"></span></div>`;
}

/** app._month_grid */
function monthGrid(ws, upCounts, nUp, side, sel, q = '') {
  const nPast = {};
  let nNone = 0;
  for (const w of ws) { const d = (w.first_date || '').slice(0, 7); if (d.length === 7) nPast[d] = (nPast[d] || 0) + 1; else nNone += 1; }
  const n = side === 'up' ? upCounts : nPast;
  // The calendar goes only when neither side has anything: a new account has no records
  // yet, and hiding it then also hid the tab to the coming stages (起案者の指摘 2026-10-14
  // 「『探す』にあったカレンダーが消えてる」).
  // 言葉が入っているときは、当たらなくても札（0 件）を残す（どちらにも無いことが見て分かるように）
  if (!q && !Object.keys(nPast).length && !nNone && !Object.keys(upCounts).length) return '';
  const years = [...new Set(Object.keys(n).map(k => k.slice(0, 4)))].sort();
  if (side !== 'up') years.reverse();
  const top = Object.keys(n).length ? Math.max(...Object.values(n)) : 1;
  const head = Array.from({length: 12}, (_, i) => `<span class="mh">${i + 1}</span>`).join('');
  const qs = q ? `&amp;q=${E(q)}` : '';
  const rows = years.map(y => `<span class="cal-y">${E(y)}</span>` + Array.from({length: 12}, (_, i) => {
    const ym = `${y}-${String(i + 1).padStart(2, '0')}`, c = n[ym] || 0;
    if (!c) return '<span class="cal-c off" aria-hidden="true"></span>';
    const lv = c * 3 <= top ? 1 : c * 3 <= top * 2 ? 2 : 3;
    return `<a class="cal-c l${lv}${ym === sel ? ' on' : ''}" href="/search?t=__TAGURI_TOKEN__&amp;cal=${E(side)}${qs}&amp;ym=${ym}#cal" aria-label="${y} 年 ${i + 1} 月 ${c} 件">${c}</a>`;
  }).join('')).join('');
  const none = nNone === 0 || side === 'up' ? '' : `<a class="cal-none${sel === 'none' ? ' on' : ''}" href="/search?t=__TAGURI_TOKEN__&amp;ym=none#cal">上演日が分からない記録<span class="mn">${nNone}</span></a>`;
  const tabs = indexTabs([['past', '観た記録', ws.length], ['up', '今後の公演', nUp]], side, k => `/search?t=__TAGURI_TOKEN__&amp;cal=${k}${qs}#cal`, 'どちらのカレンダーを見るか');
  const lead = side === 'up'
    ? '<b>今後の公演を、月から探せます。</b>数字は、上演期間がその月にかかっている公演の数です。<b>件数が多い月は、言葉と組み合わせると絞り込めます。</b>'
    : '<b>観た記録を、観た月から探せます。</b>数字はその月に観た作品の数です。押すと、その月の記録が下に出ます。';
  const only = q ? `<b>「${E(q)}」に当たったものだけを数えています。</b>` : '';
  return `<div class="cal" id="cal">
${tabs}
<div class="idxsheet loose"><p class="mnow">${only}${lead}</p>
${rows ? `<div class="cal-grid"><span class="cal-y"></span>${head}${rows}</div>` : `<p class="empty">${q ? (side === 'up' ? `「${E(q)}」に当たる、今後の公演はありません。` : `「${E(q)}」に当たる観た記録はありません。`) : side === 'up' ? '今後の公演は、いま手元にありません。' : 'まだ観た記録がありません。「今後の公演」のタブを押すと、月から公演を探せます。'}</p>`}
${none}</div></div>`;
}

async function foundRows(ctx, ws, people, whyOf = () => '') {
  const labels = await stageLabels(ctx, ws.map(w => w.stage_id));
  const files = await posterFiles(ctx, ws);
  const scale = await scaleOf(ctx);
  return ws.map(w => recRow({...w, people: people[w.work_key] || [], synopsis: ''},
    {poster: posterHtml(w, files), rateAlways: true, editable: true, label: labels[w.stage_id] || '', extra: whyOf(w), scale})).join('');
}

/** ページ送りで差し替える一覧の枠（web/app.js の hitPartPage） */
const hitPart = (key, html) => (html ? `<section class="hitpart" data-part="${key}">${html}</section>` : '');

export async function searchScreen(params, ctx) {
  const q = params.get('q') || '';
  let ym = params.get('ym') || '';
  ym = ym === 'none' || /^20\d\d-\d{2}$/.test(ym) ? ym : '';
  const ws = await loadWorks(ctx);
  // Without a choice, a person with no dated records starts on the coming stages.
  const side = params.get('cal') === 'up' || (!params.get('cal') && !ws.some(w => !w.unseen && (w.first_date || '').length >= 7)) ? 'up' : 'past';
  const pageOf = k => Math.max(1, Number.parseInt(params.get(k) || '1', 10) || 1);
  const upPage = pageOf('up'), pastPage = pageOf('pp');
  // ページ送りの道: いまの言葉・月・カレンダーの側はそのまま、ページだけを変える（#up-hits・#past-hits で一覧の頭へ）
  const pageHref = (key, anchor) => n => {
    const u = new URLSearchParams(params);
    u.delete('t'); u.delete('part'); u.set(key, String(n));
    return `/search?t=__TAGURI_TOKEN__&amp;${E(u.toString()).replace(/&amp;amp;/g, '&amp;')}#${anchor}`;
  };
  // 「次の 5 件」は、その一覧だけを作って返す（part=up・pp。画面は枠 .hitpart だけを差し替える。起案者の指摘 2026-10-19
  // 「いちいち画面全部を再読込する必要ある？その部分だけ読み込めないの？」）。ほかの一覧・カレンダー・ウェブの検索は読まない
  const part = params.get('part');
  if (part === 'pp' && q) return {title: '探す', body_html: hitPart('pp', (await pastHits(ctx, q, ws, pastPage, pageHref('pp', 'past-hits')))[0])};
  if (part === 'up') {
    const [upHtml] = await upcomingHits(ctx, q, q ? (side === 'up' ? ym : '') : ym, await buckets(ctx), UP_PER, upPage, pageHref('up', 'up-hits'));
    return {title: '探す', body_html: hitPart('up', upHtml)};
  }
  const people = await peopleByKey(ctx, ws);
  const months = await upcomingMonths(ctx);
  const nPeople = ws.filter(w => (people[w.work_key] || []).length).length;
  const note = `<p class="note"><b>出演者や題材で探せるのは、公演ページを見つけられた記録だけです</b>（観た記録 ${ws.length} 作品のうち ${nPeople} 作品）。ほかの記録は題名で探せます。</p>`;
  const form = `<form class="fav-add" method="get" action="/search">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<label class="fld" for="search-q"><span class="fl">人名・団体・題材・題名<small class="req">必須</small></span><input type="text" id="search-q" name="q" value="${E(q)}" size="28" placeholder="例：シェイクスピア・劇団四季・家族"></label>
<button type="submit">${ico('search')}探す</button></form>`;
  const head = `<h1>探す</h1>
<p class="lede">人名・団体・題材・題名で、<b>今後の公演 ${months.n} 件と観た記録の両方から探します。</b>見つけたものには、この画面から直接答えられます。今後の公演には「興味あり」を押せて、観た記録には評価と感想を付けられます。</p>${form}${note}`;
  const seen = ws.filter(w => !w.unseen);
  let cal = monthGrid(seen, months.counts, months.n, side, ym, q);
  const b = await buckets(ctx);
  if (!q) {
    let body;
    if (side === 'up') {
      const [upHtml] = await upcomingHits(ctx, '', ym, b, UP_PER, upPage, pageHref('up', 'up-hits'));
      body = ym ? hitPart('up', upHtml) : '<p class="empty">上のカレンダーから月を選ぶと、その月に観られる公演が出ます。</p>';
    } else if (!ym) {
      body = '<p class="empty">上のカレンダーから月を選ぶと、その月に観た記録が出ます。今後の公演は言葉を入れて探してください。</p>';
    } else {
      const hit = (ym === 'none' ? seen.filter(w => (w.first_date || '').length < 7) : seen.filter(w => (w.first_date || '').slice(0, 7) === ym))
        .sort((x, y) => cmp(y.first_date || '', x.first_date || ''));
      const where = ym === 'none' ? '上演日が分からない記録' : `${ym.slice(0, 4)} 年 ${Number(ym.slice(5, 7))} 月に観た記録`;
      const lead = ym === 'none' ? '<p class="lead"><b>上演日が入っていない記録です。</b>各行の「公演詳細を直す」から日付を入れると、カレンダーから探せるようになります。</p>' : '';
      body = !hit.length ? `<h2>${E(where)}</h2><p class="empty">この月の記録はありません。</p>` : `<h2>${E(where)} ${hit.length} 件</h2>${lead}` + await foundRows(ctx, hit, people);
    }
    return {title: '探す', body_html: head + cal + body};
  }
  const hits = [], names = [];
  for (const w of ws) {
    const [why, found] = hitWhy(q, w, people[w.work_key]);
    if (why) { hits.push([w, why]); names.push(...found); }
  }
  hits.sort((x, y) => cmp(y[0].first_date || '', x[0].first_date || ''));
  const [upHtml, upNames, nUp, upCounts, nUpAll] = await upcomingHits(ctx, q, side === 'up' ? ym : '', b, UP_PER, upPage, pageHref('up', 'up-hits'));
  names.push(...upNames);
  // 言葉が入っているときは、下の札とカレンダーも当たったものだけを数える（起案者の指示 2026-10-17
  // 「ワードが入って検索されてるなら、次のところも該当件数のみ表示されるようにして」）
  cal = monthGrid(hits.map(([w]) => w), upCounts, nUpAll, side, ym, q);
  const dec = await loadDeclared(ctx);
  const [pastOnly, nPast] = await pastHits(ctx, q, ws, pastPage, pageHref('pp', 'past-hits'));
  const pastHtml = pastOnly && hitPart('pp', pastOnly);
  const web = await webHits(ctx, q, nUp + nPast);
  let body;
  if (!hits.length && !nUp && !nPast) {
    const narrowed = ym && side === 'up' ? `<b>いまは ${ym.slice(0, 4)} 年 ${Number(ym.slice(5, 7))} 月に絞っています。</b>ほかの月にはあるかもしれません。カレンダーで別の月を押すか、<a href="/search?t=__TAGURI_TOKEN__&amp;cal=up&amp;q=${E(q)}">月の指定を外して</a>お試しください。<br>` : '';
    body = `<p class="empty">${narrowed}手元には、今後の公演にも観た記録にも見つかりませんでした。<b>公演ページを見つけられなかった記録は、出演者や題材では探せません。</b>その場合は題名で探してください。</p>` + web + cal;
  } else if (!hits.length) {
    body = searchFollow(dec, names) + hitPart('up', upHtml) + '<h2>観た記録</h2><p class="empty">観た記録の中には見つかりませんでした。</p>' + pastHtml + web + cal;
  } else {
    const nUn = hits.filter(([w]) => !w.verdict).length;
    const lead = `<h2>観た記録 ${hits.length} 件</h2>` + (nUn ? `<p class="lead">このうち ${nUn} 件はまだ評価が付いていません。<b>この場で${{marks4: ' ◎○△× ', stars5: '★', stars11: '★'}[await scaleOf(ctx)] || '評価'}を押せます。</b></p>`
      : '<p class="lead">評価を付け直すことも、感想を足すこともできます。</p>');
    const why = new Map(hits.map(([w, h]) => [w.work_key, h]));
    body = searchFollow(dec, names) + hitPart('up', upHtml) + lead + await foundRows(ctx, hits.map(([w]) => w), people, w => why.get(w.work_key)) + pastHtml + web + cal;
  }
  return {title: '探す', body_html: head + body};
}

/** app.add_search_request: remember a title to look for in the next daily run (newest MAX_REQUESTS kept). */
async function searchRequestAction(b, ctx) {
  const w = requestQuery(b.q ?? '');
  if (!w) throw new ValueError('探す題名を 2〜60 文字で入れてください');
  const source = ['search', 'hand', 'missed'].includes(String(b.source)) ? String(b.source) : 'search';
  await ctx.db.batch([
    ctx.db.prepare('INSERT INTO search_request(user_id,qkey,query,source,created_at) VALUES(?,?,?,?,?) ON CONFLICT(user_id,qkey) DO UPDATE SET created_at=excluded.created_at, query=excluded.query')
      .bind(ctx.uid, titleKey(w), w, source, new Date(ctx.now).toISOString()),
    ctx.db.prepare('DELETE FROM search_request WHERE user_id=? AND qkey NOT IN (SELECT qkey FROM search_request WHERE user_id=? ORDER BY created_at DESC LIMIT ?)')
      .bind(ctx.uid, ctx.uid, MAX_REQUESTS)]);
  const message = crawlSearch.requests
    ? `依頼しました。次回は${crawlLabel(nextCrawl(ctx.now))}の更新で CoRich から探します（遅れることがあります）。見つかれば、その更新のあとからこの画面と「手で足す」の候補に出ます。`
    : '依頼を控えました。依頼された題名を毎日の更新で探す段はまだ準備中で、準備ができたら探します。観た公演なら、題名と日付を手で入れても記録できます。';
  return {body: {ok: true, query: w, message}};
}

export const searchScreens = {screens: {search: searchScreen}, actions: {search_request: searchRequestAction}};
