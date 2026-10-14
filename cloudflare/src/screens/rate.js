// 評価: rate / unrated / notes screens and the writes made from them.
// Ports of tools/taguri/app.py (_rate_body, _unrated_body, _notes_body, ...),
// the serve.py handlers (on_rate, on_note, on_add_work) and the helpers they
// call in charts.py, render_recommend.py and impressions.py.
import {autoLink} from './autolink.js';
import {E, quote, sortBy, cmp, fmtF, strip, slice, field, qsFirst, qsAll, digitsInt, isdigit, strRepr, localNow, ValueError} from './py.js';
import {loadWorks, similarWorks, titleKey} from './works.js';
import {recRow, venueOf, venueKey, ico, h2, stageLabels} from './row.js';

/** serve.VERDICTS / charts.VERDICT_ORDER */
const VERDICTS = ['◎', '○', '△', '×', 'まだ判断できない'];
/** app.VERDICT_LABEL */
const VERDICT_LABEL = {'◎': 'とても合っていた', '○': '合っていた', '△': 'あまり合わなかった', '×': '合わなかった'};
/** app.SHEET_TOP */
export const SHEET_TOP = 15;

/**
 * app._rate_base: what the three screens count from.
 * Python first calls _load() (scores for the recommend screens); its result is
 * unused here. Its side effect, _promote_owned_tickets (turning ended stages
 * the user marked "owned" into works rows), needs reactions written by the
 * `react` action, which is not ported yet: port it with `react`.
 */
async function rateBase(ctx) {
  await autoLink(ctx);
  const all = await loadWorks(ctx);
  const unrated = all.filter(w => !w.verdict && w.bucket !== 'upcoming' && !w.unseen);
  const nSkip = all.filter(w => w.unseen && !w.verdict && w.bucket !== 'upcoming').length;
  const rated = all.filter(w => w.verdict && !w.unseen);
  const noNote = rated.filter(w => w.verdict === '◎' && !strip(w.note_impression || ''));
  return {all, unrated, rated, noNote, nSkip};
}

// ---------------------------------------------------------------- charts.verdict_panel
const VERDICT_FILL = {'◎': 'var(--pos)', '○': 'var(--pos)', '△': 'var(--neg)', '×': 'var(--neg)'};
const VERDICT_OP = {'◎': '1.0', '○': '0.42', '△': '0.42', '×': '1.0'};   // str(float)
const pct = x => fmtF(x * 100, 0) + '%';                                 // f"{x:.0%}"

/** charts._table */
function table(head, rows) {
  const th = head.map(h => `<th>${E(h)}</th>`).join('');
  const tr = rows.map(r => '<tr>' + r.map(c => `<td>${E(c)}</td>`).join('') + '</tr>').join('');
  return `<details class="tv"><summary>数字で見る</summary>`
    + `<table class="tbl mini"><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></details>`;
}

/** charts.verdict_panel */
function verdictPanel(works) {
  const cnt = {};
  for (const w of works) { const g = w.verdict || '未評価'; cnt[g] = (cnt[g] || 0) + 1; }
  const order = [...VERDICTS.filter(g => cnt[g]), ...(cnt['未評価'] ? ['未評価'] : [])];
  const tot = order.reduce((s, g) => s + cnt[g], 0);
  if (!tot) return '';
  const segs = [], labs = [];
  let x = 0.0;
  for (const g of order) {
    const wpc = cnt[g] / tot * 100.0;
    const fill = VERDICT_FILL[g] || 'var(--unk)';
    const op = VERDICT_OP[g] || '1.0';
    segs.push(`<g class="seg"><title>${E(g)} ── ${cnt[g]} 件（${pct(cnt[g] / tot)}）</title>`
      + `<rect x="${fmtF(x, 3)}%" y="0" width="${fmtF(Math.max(wpc - 0.25, 0.2), 3)}%" height="26"`
      + ` fill="${fill}" fill-opacity="${op}" rx="3"/></g>`);
    if (wpc >= 7) labs.push(`<span class="dl" style="left:${fmtF(x + wpc / 2, 2)}%">${E(g)} <b>${cnt[g]}</b></span>`);
    x += wpc;
  }
  return `<section class="card">
${h2('star', '付けた評価の分布', `<span class="badge part">分母 ${tot} 作品</span>`)}
<p class="lead"><b>基準は「自分に合っていたか」で、作品の出来ではありません。</b>
◎ 側と × 側を左右に分けて置いています。おすすめの材料に数えるのは <b>◎ だけ</b>です。</p>
<div class="dbar"><svg viewBox="0 0 100 26" width="100%" height="26" preserveAspectRatio="none"
 role="img" aria-label="評価の分布">${segs.join('')}</svg>
<div class="dlabs">${labs.join('')}</div></div>
${table(['評価', '件数', '割合'], order.map(g => [g, cnt[g], pct(cnt[g] / tot)]))}</section>`;
}

// ---------------------------------------------------------------- render_recommend
/** render_recommend.index_tabs */
export function indexTabs(items, sel, url, label, showLabel = false) {
  const out = items.map(([k, lab, n]) => {
    const on = k === sel;
    return `<a class="ix${on ? ' on' : ''}"${on ? ' aria-current="page"' : ''}`
      + ` href="${url(k)}">${on ? ico('check', 14, 'ixck') : ''}${E(lab)}<span class="mn">${n}</span></a>`;
  });
  const head = showLabel ? `<span class="idx-lab">${E(label)}</span>` : '';
  return `${head}<nav class="idx" aria-label="${E(label)}">${out.join('')}</nav>`;
}

/** render_recommend.paginate: [rows shown, status sentence, footer]. */
export function paginate(rows, page, per, url, unit = '件') {
  const last = Math.max(1, Math.ceil(rows.length / per));
  page = Math.min(Math.max(page, 1), last);
  const show = rows.slice((page - 1) * per, page * per);
  const first = (page - 1) * per + 1;
  if (last <= 1) return [show, `${rows.length} ${unit}すべてを表示しています。`, ''];
  const now = `<b>${first}〜${first + show.length - 1} ${unit}目</b>を表示しています`
    + `（全 ${rows.length} ${unit}）。<b>残りは下の「次の ${per} ${unit}」で`
    + `見られます。</b> `;
  const prev = page > 1 ? `<a class="mpage" href="${url(page - 1)}">← 前の ${per} ${unit}</a>`
    : `<span class="mpage off">最初のページです</span>`;
  const nxt = page < last ? `<a class="mpage" href="${url(page + 1)}">`
    + `次の ${Math.min(per, rows.length - page * per)} ${unit} →</a>`
    : '<span class="mpage off">これで最後です</span>';
  return [show, now, `<div class="mfoot">${prev}<span class="mp">${page} / ${last} ページ</span>${nxt}</div>`];
}

/** render_recommend._wait_stub */
function waitStub(w) {
  const d = strip(w.first_date || w.last_date || '');
  const m = d.match(/(\p{Nd}{4})[-/](\p{Nd}{1,2})[-/](\p{Nd}{1,2})$/u);
  const [y, md] = m ? [m[1], `${digitsInt(m[2])}/${digitsInt(m[3])}`] : ['', '未定'];
  return `<span class="wstub" aria-hidden="true">`
    + (y ? `<span class="sy">${E(y)}</span>` : '')
    + `<b>${E(md)}</b><span class="sk">${E('上演日')}</span></span>`;
}
/** render_recommend.wait_shell */
const waitShell = (w, body) => `<div class="wait">${waitStub(w)}`
  + `<span class="wperf" aria-hidden="true"></span><div class="wbody">${body}</div></div>`;

// ---------------------------------------------------------------- impressions
const ROUND = 15;
/** impressions._e: html.escape(str(s or "")) */
const e2 = s => E(s || '');
/** impressions._neg_date */
const negDate = d => d ? Array.from(d).map(ch => isdigit(ch) ? String.fromCharCode(57 - digitsInt(ch)) : ch).join('') : '~';
/** impressions._jdate */
function jdate(s) {
  const m = slice(s || '', 0, 10).match(/^(\p{Nd}{4})-(\p{Nd}{1,2})-(\p{Nd}{1,2})$/u);
  return m ? `${digitsInt(m[1])}年${digitsInt(m[2])}月${digitsInt(m[3])}日` : '日付不明';
}
/** impressions.pending(limit=None) */
const pending = works => sortBy(
  works.filter(w => w.verdict === '◎' && !strip(w.note_impression || '') && !w.unseen),
  w => [-(w.times || 1), negDate(w.first_date || '')]);
/** impressions.wait_note_html(open_=True) */
const waitNote = (key, note) => `<div class="wnote">`
  + `<textarea data-note="${e2(key)}" rows="2"`
  + ` placeholder="どう感じましたか（任意）">${e2(note)}</textarea>`
  + `<span class="said"></span></div>`;
/** impressions.pending_html */
function pendingHtml(rows, nAll) {
  const more = nAll > rows.length ? `残りは次の ${nAll - rows.length} 件です。` : '';
  const items = rows.map(w => waitShell(w, `<span class="wt">${e2(w.title)}</span>`
    + `<span class="wm">${e2(jdate(w.first_date))}`
    + ((w.times || 1) > 1 ? `・${w.times} 回観た` : '')
    + '</span>'
    + waitNote(w.work_key, w.note_impression || ''))).join('');
  return `<p class="lead">◎ を付けたのに感想が無い作品が ${nAll} 件あります。`
    + `<b>思い出せるものだけで結構です。</b>${e2(more)}<br>`
    + `一文書いておくと、次に同じ作り手の公演が出てきたときに、`
    + `その言葉をおすすめの理由に添えて出します。</p>`
    + `<div class="waits">${items}</div>`;
}
/** app._pending_notes_html(collapsed=False) */
function pendingNotesHtml(all) {
  const rows = pending(all);
  return rows.length ? pendingHtml(rows.slice(0, ROUND), rows.length) : '';
}

// ---------------------------------------------------------------- app._venue_form
function venueForm(ws, keep, action, hidden) {
  const counts = new Map(), label = new Map();
  for (const w of ws) {
    const k = venueKey(w);
    counts.set(k, (counts.get(k) || 0) + 1);
    if (!label.has(k)) label.set(k, venueOf(w) || '会場が分かりません');
  }
  if (!counts.size) return '';
  const order = sortBy([...counts.keys()].filter(k => k !== 'none'), k => [-counts.get(k), label.get(k)]);
  if (counts.has('none')) order.push('none');
  keep = new Set([...keep].filter(k => counts.has(k)));
  const chips = order.map(k => `<label class="pchip${keep.has(k) ? ' on' : ''}">`
    + `<input type="checkbox" name="venue" value="${E(k)}"${keep.has(k) ? ' checked' : ''}>`
    + `<span class="pl">${E(label.get(k))}</span><span class="pn">${counts.get(k)}</span></label>`).join('');
  const now = !keep.size ? 'すべて' : order.filter(k => keep.has(k)).map(k => label.get(k)).join('・') + `（${keep.size} 会場）`;
  const hiddenIn = hidden.filter(([, hv]) => hv).map(([hk, hv]) => `<input type="hidden" name="${E(hk)}" value="${E(hv)}">`).join('');
  const hiddenQs = hidden.filter(([, hv]) => hv).map(([hk, hv]) => `&amp;${E(hk)}=${E(hv)}`).join('');
  return `<form class="pfil" method="get" action="${E(action)}">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
${hiddenIn}
<details class="pbox">
<summary>${ico('search', 15)}会場で絞り込む ── いまは<b>${E(now)}</b></summary>
<p class="lead">会場は<b>いくつでも同時に選べます</b>。選んだ会場で観た記録だけを表示します。
数字は、いま選んでいる評価・年の中でその会場の件数です。</p>
<div class="pchips">${chips}</div>
<div class="pfoot"><button type="submit">${ico('search')}この会場で絞り込む</button>
<a class="pall" href="${E(action)}?t=__TAGURI_TOKEN__${hiddenQs}">すべての会場に戻す</a></div>
</details></form>`;
}

/** serve._page: ?p= as a number (1-3 digits), else 1. */
export function page(params) {
  const v = qsFirst(params, 'p', '1');
  return /^\p{Nd}{1,3}$/u.test(v) ? digitsInt(v) : 1;
}

/** app._poster_html: no poster files on the Worker (see row.editHtml). */
/**
 * app._poster_html for a public user: the poster of the linked stage when it is
 * in R2 (the D1 table `poster`, written by scripts/deliver_posters.py). Hand
 * posters are off on the public service and the owner's date guess
 * (posters.match) is not ported. `files` is posterFiles(ctx, works).
 */
export const posterHtml = (w, files = {}) => {
  const sid = String(w.stage_id || '');
  const f = sid ? files[sid] : '';
  return f ? `<img class="poster" src="/img/${E(f)}?t=__TAGURI_TOKEN__" alt="" loading="lazy">` : '';
};

/** stage_id -> poster file for the given works (D1 `poster`; empty before migration 0013). */
export async function posterFiles(ctx, works) {
  const ids = [...new Set(works.map(w => String(w.stage_id || '')).filter(Boolean))];
  const out = {};
  for (let i = 0; i < ids.length; i += 90) {
    const part = ids.slice(i, i + 90);
    try {
      const {results} = await ctx.db.prepare(`SELECT stage_id, file FROM poster WHERE stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
      for (const r of results) out[r.stage_id] = r.file;
    } catch { return out; }
  }
  return out;
}

// ---------------------------------------------------------------- screens
/** app._rate_body (GET /api/screen/rate?v=&y=&venue=&p=) */
async function rateScreen(params, ctx) {
  const verdict = qsFirst(params, 'v'), year = qsFirst(params, 'y'), venues = qsAll(params, 'venue');
  const b = await rateBase(ctx);
  const rated = b.rated;
  const verdictFig = verdictPanel(b.all.filter(w => !w.unseen));
  const byFirstDesc = rows => sortBy(rows, w => w.first_date || '', true);
  const byV = Object.fromEntries(VERDICTS.map(g => [g, byFirstDesc(rated.filter(w => w.verdict === g))]));
  const live = VERDICTS.filter(g => byV[g].length);
  const title = '評価一覧';
  if (!live.length) {
    return {title, body_html: `<h1>評価一覧</h1>${verdictFig}<p class="empty">まだ評価が付いた記録はありません。</p>`};
  }
  const sel = (live.includes(verdict) || verdict === 'all') ? verdict : (live.includes('◎') ? '◎' : live[0]);
  const allSorted = byFirstDesc(rated);
  const chips = indexTabs(
    [['all', 'すべて', rated.length],
      ...live.map(g => [g, `${g}${VERDICT_LABEL[g] ? ` ${VERDICT_LABEL[g]}` : ''}`, byV[g].length])],
    sel, g => `/rate?t=__TAGURI_TOKEN__&amp;v=${quote(g)}`, '評価', true);
  const ws = sel === 'all' ? allSorted : byV[sel];

  // Years within the chosen verdict (key: first 4 characters of the date, or 'none').
  const yearOf = w => slice(w.first_date || '', 0, 4);
  const years = new Map();
  for (const w of ws) {
    const y = yearOf(w);
    const k = isdigit(y) ? y : 'none';
    years.set(k, (years.get(k) || 0) + 1);
  }
  const ykeys = [...years.keys()].filter(k => k !== 'none').sort(cmp).reverse();
  if (years.has('none')) ykeys.push('none');
  const ysel = years.has(year) ? year : '';
  const vkeep = new Set(venues.filter(v => v));
  const venueQs = [...vkeep].sort(cmp).map(v => `&amp;venue=${quote(v)}`).join('');
  const yurl = y => `/rate?t=__TAGURI_TOKEN__&amp;v=${quote(sel)}` + (y ? `&amp;y=${quote(y)}` : '') + venueQs;
  const ytabs = indexTabs(
    [['', 'すべての年', ws.length], ...ykeys.map(k => [k, k === 'none' ? '上演日が分からない' : `${k} 年`, years.get(k)])],
    ysel, yurl, '年', true);
  const wsY = !ysel ? ws : ysel === 'none' ? ws.filter(w => !isdigit(yearOf(w))) : ws.filter(w => yearOf(w) === ysel);

  const vform = venueForm(wsY, vkeep, '/rate', [['v', sel], ['y', ysel]]);
  const wsV = !vkeep.size ? wsY : wsY.filter(w => vkeep.has(venueKey(w)));
  const lab = sel === 'all' ? 'すべての評価' : `${sel}${VERDICT_LABEL[sel] ? `（${VERDICT_LABEL[sel]}）` : ''}`;
  const [show, now, foot] = paginate(wsV, page(params), SHEET_TOP,
    pg => `/rate?t=__TAGURI_TOKEN__&amp;v=${quote(sel)}` + (ysel ? `&amp;y=${quote(ysel)}` : '') + venueQs
      + (pg > 1 ? `&amp;p=${pg}` : ''), '作品');
  const files = await posterFiles(ctx, show);
  const rows = show.map(w => recRow(w, {poster: posterHtml(w, files), rateReopen: true})).join('');
  return {title, body_html: `<h1>評価一覧 ── 付けた ${rated.length} 件</h1>
<p class="lede">付けた評価を◎○△×ごとに分けています。<b>基準は「自分に合っていたか」で、作品の出来ではありません。</b>評価は作品ごとに1つです。おすすめは◎を付けた公演の作り手から作るので、<b>ここで答えると次のおすすめが変わります。</b>題名・日付・会場そのものを直したいときは、<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>で直せます。</p>
${verdictFig}
${chips}
${ytabs}
${vform}
<div class="idxsheet">
<p class="mnow"><b>${E(lab)}</b>を付けた作品を、観た日の新しい順に ${now}
ほかの評価は、上のインデックスで切り替えられます。
評価をまたいで続けて読むときは<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>です。</p>
${rows}</div>
${foot}`};
}

/** app._unrated_body (GET /api/screen/unrated) */
async function unratedScreen(_params, ctx) {
  const b = await rateBase(ctx);
  const unrated = sortBy(b.unrated, w => w.first_date || '', true);
  const skipped = !b.nSkip ? '' : `<br><b>「行かなかった」を付けた ${b.nSkip} 件は、`
    + `ここには出していません。</b>`
    + `<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>に残っていますので、`
    + `付け間違えたときはその行の「やはり観た」で戻してください。`;
  const labels = await stageLabels(ctx, unrated.map(w => w.stage_id));
  const files = await posterFiles(ctx, unrated);
  const rows = unrated.map(w => recRow(w, {poster: posterHtml(w, files), rateAlways: true, editable: true, label: labels[w.stage_id] || ''})).join('');
  return {title: '未評価', body_html: `<h1>未評価 ── ${unrated.length} 件</h1>
<p class="lede">評価がまだ付いていない記録です。<b>上演日が分からない記録も含みます。</b>日付がないと上演が終わったか判定できないので、「まだ答えていない」には出てきません。${skipped}<br>
<b>実際には観ていない公演が混じっていたら、各行の「公演詳細を直す」から外せます。</b>券を買って行かなかった公演と、舞台ではない記録は、そこで書き分けられます。どちらも、あとで戻せます。</p>
${rows || '<p class="empty">評価が付いていない記録はありません。</p>'}`};
}

/** app._notes_body (GET /api/screen/notes) */
async function notesScreen(_params, ctx) {
  const b = await rateBase(ctx);
  return {title: '感想', body_html: `<h1>感想 ── ◎ を付けた ${b.noNote.length} 件</h1>
${pendingNotesHtml(b.all)}`};
}

// ---------------------------------------------------------------- writes
/**
 * app.save_work_field for a public user: only manual rows exist, so the row
 * must already be in works (purchase-derived rows are never created here).
 */
async function saveWorkField(ctx, workKey, col, value) {
  const have = await ctx.db.prepare('SELECT 1 FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, workKey).first();
  if (!have) throw new ValueError('その作品は記録に無い');
  const source = col === 'verdict' ? 'verdict_source' : 'note_source';
  await ctx.db.prepare(`UPDATE works SET ${col}=?, ${source}='user', updated_at=? WHERE user_id=? AND work_key=?`)
    .bind(value, localNow(ctx.now), ctx.uid, workKey).run();
}

/** serve.on_rate (POST /api/rate) */
async function rateAction(b, ctx) {
  const workKey = field(b, 'work_key'), verdict = field(b, 'verdict');
  if (!VERDICTS.includes(verdict)) throw new ValueError(`verdict が候補にない: ${strRepr(verdict)}`);
  await saveWorkField(ctx, workKey, 'verdict', verdict);
  return {body: {ok: true, work_key: workKey, verdict, recommendation: {status: 'on_next_read'}}};
}

/** serve.on_note (POST /api/note) */
async function noteAction(b, ctx) {
  const workKey = field(b, 'work_key');
  const note = slice(field(b, 'note_impression'), 0, 4000);
  await saveWorkField(ctx, workKey, 'note_impression', note);
  return {body: {ok: true, work_key: workKey, len: Array.from(note).length}};
}

/** serve.on_add_work + app.add_work (POST /api/add_work) */
async function addWorkAction(b, ctx) {
  const title = slice(strip(field(b, 'title')), 0, 200);
  const date = slice(strip(field(b, 'date')), 0, 10);
  const venue = slice(strip(field(b, 'venue')), 0, 80);
  const time = slice(strip(field(b, 'time')), 0, 5);
  if (!title) throw new ValueError('題名が要る');
  if (date && !/^\p{Nd}{4}-\p{Nd}{2}-\p{Nd}{2}$/u.test(date)) throw new ValueError('日付は YYYY-MM-DD で入れる');
  if (time && !/^\p{Nd}{2}:\p{Nd}{2}$/u.test(time)) throw new ValueError('開演時刻は HH:MM で入れる');
  const stageId = slice(strip(field(b, 'stage_id')), 0, 16);
  if (stageId && !/^\p{Nd}{1,12}$/u.test(stageId)) throw new ValueError('公演の id が数字ではない');
  const key = `${titleKey(title)}#${date || 'undated'}`;
  if (await ctx.db.prepare('SELECT 1 FROM works WHERE user_id=? AND work_key=?').bind(ctx.uid, key).first()) {
    throw new ValueError('その作品はもう登録してある');
  }
  await ctx.db.prepare('INSERT INTO works (user_id, work_key, title, first_date, last_date, times, verdict,'
    + ' chosen, note_impression, note_motive, stage_id, venue, time, updated_at)'
    + " VALUES (?,?,?,?,?,1,NULL,NULL,'','',?,?,?,?)")
    .bind(ctx.uid, key, title, date, date, stageId || null, venue, time, localNow(ctx.now)).run();
  // stage_search.adopt runs only for the owner, and serve._enrich (fetching
  // the stage's material) is skipped on the public service. Instead, a record
  // with a date is linked to the one stage running that day under the same title.
  const linked = stageId ? '' : ((await autoLink(ctx, [key]))[key] || '');
  return {body: {ok: true, work_key: key, stage_id: stageId || linked, adopted: {}, similar: await similarWorks(ctx, title, key)}};
}

export const rateScreens = {
  screens: {rate: rateScreen, unrated: unratedScreen, notes: notesScreen},
  actions: {rate: rateAction, note: noteAction, add_work: addWorkAction},
};
