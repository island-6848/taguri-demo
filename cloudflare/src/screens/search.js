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
import {loadDeclared, buckets, nz} from './lists.js';
import {stageInfo, fallbackTemplate} from './fallback.js';
import {runRange, periodStart} from './reminder.js';

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
  const {results} = await ctx.db.prepare(`SELECT s.stage_id, s.title, s.entry, s.start, s.end, c.ws FROM rec_stage s
    LEFT JOIN rec_card c ON c.stage_id=s.stage_id AND c.ver=(SELECT v FROM rec_meta WHERE k='rec_card')
    WHERE s.ver=(SELECT v FROM rec_meta WHERE k='current') AND (s.end='' OR s.end>=?)${idxWhere}`)
    .bind(ctx.today, ...(key ? [key, key, key, key] : [])).all();
  for (const r of results) {
    let e = {};
    try { e = JSON.parse(r.entry || '{}') || {}; } catch { /* no entry */ }
    out.set(String(r.stage_id), {...e, period: e.period || slashed(r.start, r.end), title: r.title, stage_id: String(r.stage_id), _ws: r.ws ? r.ws.split('\n') : []});
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
/** Coming stages counted by month, without a word: only the dates are read (no entry JSON to parse). */
async function upcomingMonths(ctx) {
  const [idx, cat] = await ctx.db.batch([
    ctx.db.prepare("SELECT stage_id, start, end FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND (end='' OR end>=?)").bind(ctx.today),
    ctx.db.prepare("SELECT id, date, json_extract(metadata,'$.end_date') AS end FROM catalogue WHERE date>=? AND COALESCE(json_extract(metadata,'$.end_date'), date)>=?").bind(since(ctx.today), ctx.today)]);
  const rows = new Map(idx.results.map(r => [String(r.stage_id), {period: slashed(r.start, r.end)}]));
  for (const r of cat.results) if (!rows.has(String(r.id))) rows.set(String(r.id), {period: slashed(r.date, r.end || r.date)});
  return {counts: monthCounts([...rows.values()], ctx.today), n: rows.size};
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
<p class="lead">お気に入りに登録すると、<b>この名前の公演がこれから始まるときに、
件数の制限も条件も付けずに新着へ出ます。</b>いま探している名前を、ここから登録できます。</p>
${out.slice(0, 8).join('')}</div>`;
}

/** app._upcoming_hits: [html, names, n, {month: n} of the stages the word hits (empty without a word), stages the word hits in any month] */
export async function upcomingHits(ctx, q, ym, b, top = 8) {
  const rows = await upcoming(ctx, q);
  const state = new Map();
  for (const [k, lab] of [['tracking', '追いかけています（興味ありと答えました）'], ['owned', '観る予定です（すでに持っていると答えました）'], ['others', '興味なしと答えました']])
    for (const r of b[k]) for (const sid of r.sids || [r.stage_id]) state.set(sid, lab);
  const tracking = new Set(b.tracking.flatMap(r => r.sids || [r.stage_id]));
  const hits = [];
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
  const names = hits.flatMap(h => h[3]);
  // 言葉で引いたときの月ごとの数（カレンダーも当たった公演だけを数える。月の指定より前の全部）
  const matched = q ? rows.filter(c => hitUpcoming(q, c, c._ws)[0]) : rows;
  const counts = q ? monthCounts(matched, ctx.today) : {};
  if (!hits.length) return ['', [], 0, counts, matched.length];
  const show = hits.slice(0, top);
  const {html, posters} = await cardTemplates(ctx.db, show.map(h => h[0]));
  // カードがまだ無い公演（新しい公演など）は、一覧と索引の中身から描く（fallback.js）
  const bare = show.map(h => h[0]).filter(sid => !html.has(sid));
  if (bare.length) for (const [sid, st] of await stageInfo(ctx.db, bare)) html.set(sid, fallbackTemplate(st));
  const cards = show.filter(h => html.has(h[0])).map(([sid, , why]) => {
    const st = state.get(sid);
    const w = why + (st ? `<li class="rs state">${E(st)}</li>` : '');
    const pic = posters.get(sid);
    return compose(html.get(sid), sid, tracking.has(sid) ? 'interest' : 'recommend', {top: w, poster: pic ? cardPoster(pic) : ''});
  });
  const tail = hits.length <= top ? '' : `<p class="lead">見つかったのは ${hits.length} 件で、上演日の近い ${top} 件を表示しています。<b>残りは`
    + (!q ? '言葉を入れると絞り込めます' : '言葉を変えると出てきます') + '</b>（人名・団体名・劇場名など）。</p>';
  const head = ym ? `${ym.slice(0, 4)} 年 ${Number(ym.slice(5, 7))} 月に観られる公演` : 'これから観られる公演';
  const order = ym ? 'この月に始まる公演を先に、すでに続いている公演を後に（終わりの近い順）並べています。' : '上演日の近い順です。';
  return [`<h2>${E(head)} ${hits.length} 件</h2><p class="lead">${order}順位は付けていません。<b>ここから「興味あり」を押すと、追いかけている一覧に入ります。</b></p>${tail}${cards.join('')}`, names, hits.length, counts, matched.length];
}

/** app._request_query */
function requestQuery(q) {
  const w = String(q || '').normalize('NFKC').replace(/\s+/gu, ' ').trim();
  if (Array.from(w).length < 2 || Array.from(w).length > 60 || Array.from(titleKey(w)).length < 2) return '';
  if ([...w].some(c => c.charCodeAt(0) < 32) || w.includes('://') || w.includes('@') || w.toLowerCase().includes('www.')) return '';
  return w;
}
const MAX_REQUESTS = 30;
/** app._web_hits for the public service: ask the next daily run instead of searching now. */
async function webHits(ctx, q) {
  if (!requestQuery(q)) return '<p class="note">たぐりの公演一覧から検索できます。</p>';
  const have = await ctx.db.prepare('SELECT 1 FROM search_request WHERE user_id=? AND qkey=?').bind(ctx.uid, titleKey(requestQuery(q))).first();
  if (have) return `<div class="webq" id="web"><p class="lead">「${E(q)}」は、次の更新（毎日 4 時台）で CoRich から探すよう頼んであります。見つかれば、翌日からここに出ます。</p></div>`;
  return `<div class="webq" id="web"><p class="lead">その場では CoRich を検索せず、毎日の更新で集めた公演から探します。<b>そこに無い公演は、次の更新で CoRich から探すよう頼めます。</b>見つかれば、翌日からこの画面と「手で足す」の候補に出ます。</p>`
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
  if (!Object.keys(nPast).length && !nNone && !Object.keys(upCounts).length) return '';
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
  const tabs = indexTabs([['past', '観た記録', ws.length], ['up', 'これから観られる公演', nUp]], side, k => `/search?t=__TAGURI_TOKEN__&amp;cal=${k}${qs}#cal`, 'どちらのカレンダーを見るか');
  const lead = side === 'up'
    ? '<b>これから観られる公演を、月から探せます。</b>数字はその月に観られる公演の数です（上演期間がその月にかかっているもの）。<b>件数が多い月は、言葉と一緒に使うと絞れます。</b>'
    : '<b>観た記録を、観た月から探せます。</b>数字はその月に観た作品の数です。押すと、その月の記録が下に出ます。';
  const only = q ? `<b>「${E(q)}」に当たったものだけを数えています。</b>` : '';
  return `<div class="cal" id="cal">
${tabs}
<div class="idxsheet loose"><p class="mnow">${only}${lead}</p>
${rows ? `<div class="cal-grid"><span class="cal-y"></span>${head}${rows}</div>` : `<p class="empty">${side === 'up' ? 'これから観られる公演は、いま手元にありません。' : 'まだ観た記録がありません。「これから観られる公演」の札から、月で探せます。'}</p>`}
${none}</div></div>`;
}

async function foundRows(ctx, ws, people, whyOf = () => '') {
  const labels = await stageLabels(ctx, ws.map(w => w.stage_id));
  const files = await posterFiles(ctx, ws);
  const scale = await scaleOf(ctx);
  return ws.map(w => recRow({...w, people: people[w.work_key] || [], synopsis: ''},
    {poster: posterHtml(w, files), rateAlways: true, editable: true, label: labels[w.stage_id] || '', extra: whyOf(w), scale})).join('');
}

export async function searchScreen(params, ctx) {
  const q = params.get('q') || '';
  let ym = params.get('ym') || '';
  ym = ym === 'none' || /^20\d\d-\d{2}$/.test(ym) ? ym : '';
  const ws = await loadWorks(ctx);
  // Without a choice, a person with no dated records starts on the coming stages.
  const side = params.get('cal') === 'up' || (!params.get('cal') && !ws.some(w => !w.unseen && (w.first_date || '').length >= 7)) ? 'up' : 'past';
  const people = await peopleByKey(ctx, ws);
  const months = await upcomingMonths(ctx);
  const nPeople = ws.filter(w => (people[w.work_key] || []).length).length;
  const note = `<p class="note"><b>出演者や題材で探せるのは、公演ページを見つけられた記録だけです</b>（観た記録では ${nPeople} 作品／全 ${ws.length} 作品）。ほかの記録は題名で探せます。</p>`;
  const form = `<form class="fav-add" method="get" action="/search">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<input type="text" name="q" value="${E(q)}" size="28" placeholder="人名・団体・題材・題名">
<button type="submit">${ico('search')}探す</button></form>`;
  const head = `<h1>探す</h1>
<p class="lede">人名・団体・題材・題名で、<b>これから観られる公演 ${months.n} 件と観た記録の両方から探します。</b>見つけたものには、この画面のまま答えられます。これから観られる公演には「興味あり」を、観た記録には評価と感想を付けられます。</p>${form}${note}`;
  const seen = ws.filter(w => !w.unseen);
  let cal = monthGrid(seen, months.counts, months.n, side, ym, q);
  const b = await buckets(ctx);
  if (!q) {
    let body;
    if (side === 'up') {
      const [upHtml] = await upcomingHits(ctx, '', ym, b);
      body = ym ? upHtml : '<p class="empty">上のカレンダーから月を選ぶと、その月に観られる公演が出ます。</p>';
    } else if (!ym) {
      body = '<p class="empty">上のカレンダーから月を選ぶと、その月に観た記録が出ます。これから観られる公演は、言葉を入れて引いてください。</p>';
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
  const [upHtml, upNames, nUp, upCounts, nUpAll] = await upcomingHits(ctx, q, side === 'up' ? ym : '', b);
  names.push(...upNames);
  // 言葉が入っているときは、下の札とカレンダーも当たったものだけを数える（起案者の指示 2026-10-17
  // 「ワードが入って検索されてるなら、次のところも該当件数のみ表示されるようにして」）
  cal = monthGrid(hits.map(([w]) => w), upCounts, nUpAll, side, ym, q);
  const web = await webHits(ctx, q);
  const dec = await loadDeclared(ctx);
  let body;
  if (!hits.length && !nUp) {
    const narrowed = ym && side === 'up' ? `<b>いまは ${ym.slice(0, 4)} 年 ${Number(ym.slice(5, 7))} 月に絞っています。</b>ほかの月にはあるかもしれません。カレンダーの月を押し直すか、<a href="/search?t=__TAGURI_TOKEN__&amp;cal=up&amp;q=${E(q)}">月の指定を外して</a>お試しください。<br>` : '';
    body = `<p class="empty">${narrowed}手元には、これから観られる公演にも観た記録にも見つかりませんでした。<b>公演ページを見つけられなかった記録は、出演者や題材では探せません。</b>その場合は題名で探してください。</p>` + web + cal;
  } else if (!hits.length) {
    body = searchFollow(dec, names) + upHtml + '<h2>観た記録</h2><p class="empty">観た記録の中には見つかりませんでした。</p>' + web + cal;
  } else {
    const nUn = hits.filter(([w]) => !w.verdict).length;
    const lead = `<h2>観た記録 ${hits.length} 件</h2>` + (nUn ? `<p class="lead">このうち ${nUn} 件はまだ評価が付いていません。<b>この場で${{marks4: ' ◎○△× ', stars5: '★', stars11: '★'}[await scaleOf(ctx)] || '評価'}を押せます。</b></p>`
      : '<p class="lead">評価を付け直すことも、感想を足すこともできます。</p>');
    const why = new Map(hits.map(([w, h]) => [w.work_key, h]));
    body = searchFollow(dec, names) + upHtml + lead + await foundRows(ctx, hits.map(([w]) => w), people, w => why.get(w.work_key)) + web + cal;
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
  return {body: {ok: true, query: w, message: '次の更新（毎日 4 時台）で CoRich から探します。見つかれば、翌日からこの画面と「手で足す」の候補に出ます。'}};
}

export const searchScreens = {screens: {search: searchScreen}, actions: {search_request: searchRequestAction}};
