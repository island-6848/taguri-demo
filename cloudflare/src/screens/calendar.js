// 公演カレンダー: stage_calendar.panel / add_ticket_button_html ported to the Worker
// (起案者の指示 2026-10-14「残りの画面も順に移して」). calendar.test.js checks both
// against the Python functions on the same rows and tickets.
import {stageInfo} from './fallback.js';
import {E} from './py.js';
import {ico} from './icons.js';
import {CALENDAR_JS} from './calendar_js.js';
import {periodStart, periodEnd, regionLabel, runRange, workKey} from './reminder.js';
import {PREFS} from './prefs.js';
import {emptyGuide} from './guide.js';
import {buckets} from './lists.js';

export const KINDS = [['owned', 'すでに持っている', 'ticket', 'own'], ['tracking', '興味あり', 'flag', 'trk'], ['favourites', 'お気に入り', 'star', 'fav']];
export const KIND_KEYS = KINDS.map(k => k[0]);
const MAX_MONTHS = 12;
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const D = isoDate => new Date(isoDate + 'T00:00:00Z');
const days = (a, b) => Math.round((D(a) - D(b)) / 86400000);
const mdays = (y, m) => new Date(Date.UTC(y, m, 0)).getUTCDate();
const isoOf = (y, m, d) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const weekday = isoDate => (D(isoDate).getUTCDay() + 6) % 7;          // Python: Monday 0
/** recommend2.run_days */
const runDays = period => { const s = periodStart(period), e = periodEnd(period); return s && e ? days(e, s) + 1 : 0; };

/** render_recommend.period_label */
export function periodLabel(period, nDays) {
  const ms = [...String(period || '').matchAll(/(20\d\d)\/(\d{1,2})\/(\d{1,2})/g)];
  if (!ms.length) return E(period);
  const fs = `${Number(ms[0][2])}/${Number(ms[0][3])}`;
  const last = ms.at(-1);
  if (ms.length === 1 || ms[0][0] === last[0]) return `${fs} のみ・<b>1 日公演</b>`;
  if (nDays <= 1) {
    const a = isoOf(+ms[0][1], +ms[0][2], +ms[0][3]), b = isoOf(+last[1], +last[2], +last[3]);
    nDays = Number.isNaN(D(a).getTime()) || Number.isNaN(D(b).getTime()) ? 0 : days(b, a) + 1;
  }
  return `${fs}〜${Number(last[2])}/${Number(last[3])}${nDays > 1 ? `・${nDays} 日間` : ''}`;
}

/** stage_calendar.rows_of: d = {owned, tracking, favourites}: [{stage_id, title, venue, pref, period}] */
export function rowsOf(d, today, tickets) {
  const out = [], seen = new Set();
  for (const [key, label, icon, cls] of KINDS) {
    for (const c of d[key] || []) {
      const sid = String(c.stage_id || '');
      if (sid && seen.has(sid)) continue;
      const s = periodStart(c.period), e = periodEnd(c.period);
      if (!s || !e || e < today) continue;
      if (sid) seen.add(sid);
      const tk = (tickets.get(sid) || []).filter(t => s <= (t.date || '') && (t.date || '') <= e);
      out.push({sid, title: c.title || '', venue: c.venue || '', pref: c.pref || '', start: s, end: e,
        days: runDays(c.period), period: c.period || '', key, kind: label, icon, cls, tickets: tk});
    }
  }
  return out;
}

const byDay = tk => { const out = new Map(); for (const t of tk) { if (!out.has(t.date)) out.set(t.date, []); out.get(t.date).push(t); } return [...out].sort((a, b) => cmp(a[0], b[0])); };
function goLabel(tk) {
  return byDay(tk).map(([day, g]) => {
    const tms = g.filter(t => t.time).map(t => t.time).join('・');
    return `${Number(day.slice(5, 7))}/${Number(day.slice(8, 10))}` + (tms ? ` ${tms}` : '') + (g.some(t => t.confirmed) ? '' : '（確定前）');
  }).join('・');
}
function points(tk, r, a, row) {
  return byDay(tk).map(([day, g]) => {
    const col = days(day, a) + 2;
    const tms = g.filter(t => t.time).map(t => t.time).join('・');
    const ok = g.some(t => t.confirmed);
    const say = `${Number(day.slice(5, 7))} 月 ${Number(day.slice(8, 10))} 日` + (tms ? ` ${tms}` : '') + ' に行きます'
      + (ok ? '' : '（購入確認メールから読み取りました。まだ確定していません）');
    const cls = 'pt' + (ok ? '' : ' un') + (g.length > 1 ? ' mul' : '');
    return `<span class="${cls}" data-stage="${E(r.sid || '')}" title="${E(say)}" style="grid-column:${col};grid-row:${row}">`
      + `${g.length > 1 ? `<b>${g.length}</b>` : ''}<i class="sr">${E(r.title)}・${E(say)}</i></span>`;
  }).join('');
}
/**
 * stage_calendar._timeline: 今月の 1 日から最後の月の末日までを、1 枚の続いた格子にする。
 * 起案者の指摘（2026-10-15）「月ごとにわけて描画してるけど、月またいでやってる作品が見づらい」。月ごとに
 * 分けると、またぐ公演が月の数だけ別の行に出て、帯も月の端で切れていた。1 枚にすると 1 公演は 1 行・1 本の帯になる。
 * 月の名前は見出しの 1 段目に、月の境目は縦の線で出す。件数は種類の絵記号と数で 1 行にする（「（…）」が折り返していた）。
 */
function timeline(rows, ms, today) {
  const [fy, fm] = ms[0], [ly, lm] = ms.at(-1);
  const a = isoOf(fy, fm, 1), b = isoOf(ly, lm, mdays(ly, lm)), n = days(b, a) + 1;
  // 並びは、上演中（初日が今日まで）を千穐楽の近い順に、そのあとにこれから開く公演を初日の近い順に
  // （起案者の指示 2026-10-24「上演中のものは千秋楽が近いものから順に並べて、そのあとに開幕の初日が近い順に並べて」）。
  // 前は都道府県ごと（2026-08-25「都道府県順に並び変えて」）で、県の中は締切の近い順だった
  const live = r => r.start <= today;
  const hit = rows.filter(r => r.start <= b && r.end >= a)
    .sort((p, q) => (live(q) - live(p)) || (live(p) ? cmp(p.end, q.end) || cmp(p.start, q.start)
      : cmp(p.start, q.start) || cmp(p.end, q.end)) || cmp(p.title, q.title));
  if (!hit.length) return '';
  const tally = KINDS.map(([, lb, icon]) => [lb, icon, hit.filter(r => r.kind === lb).length]).filter(([, , c]) => c)
    .map(([lb, icon, c]) => `<span class="ck">${ico(icon, 12)}<i class="sr">${E(lb)}</i>${c}</span>`).join('');
  const head = `<p class="calcnt"><b>${hit.length} 件</b>${tally}</p>`;
  const iso = i => new Date(D(a).getTime() + i * 86400000).toISOString().slice(0, 10);
  const marks = [], hd = ['<span class="hc" style="grid-row:1/3"></span>'];
  for (let i = 0; i < n; i++) {
    const day = iso(i), wd = weekday(day), dd = Number(day.slice(8, 10));
    if (wd >= 5) marks.push(`<span class="wk ${wd === 6 ? 'sun' : 'sat'}" style="grid-column:${i + 2};grid-row:3/-1"></span>`);
    if (dd === 1) {
      const y = Number(day.slice(0, 4)), m = Number(day.slice(5, 7));
      hd.push(`<span class="mh" style="grid-column:${i + 2}/${i + 2 + mdays(y, m)};grid-row:1"><b>${y} 年 ${m} 月</b></span>`);
      if (i) marks.push(`<span class="ms" style="grid-column:${i + 2};grid-row:1/-1"></span>`);
    }
    const w = '日月火水木金土'[(wd + 1) % 7];
    const cls = 'hd' + ['', '', '', '', '', ' sat', ' sun'][wd] + (day < today ? ' past' : '');
    hd.push(`<span class="${cls}" style="grid-column:${i + 2};grid-row:2"><b>${dd}</b><i>${w}</i></span>`);
  }
  const now = a <= today && today <= b ? `<span class="now" style="grid-column:${days(today, a) + 2};grid-row:1/-1"></span>` : '';
  const body = hit.map((r, k) => {
    const c0 = Math.max(1, days(r.start, a) + 1), c1 = Math.min(n, days(r.end, a) + 1);
    const cl = r.start < a ? ' cl' : '', cr = r.end > b ? ' cr' : '';
    const where = `${r.venue}` + (r.pref && r.pref !== '東京都' ? `（${r.pref}）` : '');
    const sid = r.sid ? ` data-stage="${E(r.sid)}"` : '';
    const here = (r.tickets || []).filter(t => a <= t.date && t.date <= b);
    const go = here.length ? `<em class="go">${E(goLabel(here))} に行きます</em>` : '';
    return `<span class="nm"${sid} style="grid-row:${k + 3}"><b>${E(r.title)}</b>`
      + `<i>${periodLabel(r.period, r.days)}${where ? '・' + E(where) : ''}</i>${go}</span>`
      + `<span class="bar ${r.cls}${cl}${cr}"${sid} style="grid-column:${c0 + 1}/${c1 + 2};grid-row:${k + 3}">`
      + `${ico(r.icon, 13)}<i class="sr">${E(r.kind)}</i></span>` + points(here, r, a, k + 3);
  }).join('');
  return `<div class="mblock">${head}<div class="mscroll"><div class="mgrid tl" data-from="${a}" style="--n:${n};`
    + `grid-template-rows:repeat(${2 + hit.length},auto)">${marks.join('')}${now}${hd.join('')}${body}</div></div></div>`;
}

/** stage_calendar.filter_html; selKinds / selPrefs are null when not chosen. */
function filterHtml(rows, selKinds, selPrefs) {
  const all = new Set(KIND_KEYS);
  const keepK = selKinds ?? all;
  const kindN = Object.fromEntries(KINDS.map(([key]) => [key, rows.filter(r => r.key === key).length]));
  const kindChips = KINDS.map(([key, label, icon]) => `<label class="pchip${keepK.has(key) ? ' on' : ''}">`
    + `<input type="checkbox" name="kind" value="${key}"${keepK.has(key) ? ' checked' : ''}>`
    + `${ico(icon, 13)}<span class="pl">${E(label)}</span><span class="pn">${kindN[key]}</span></label>`).join('');
  const keepP = new Set(selPrefs ?? []);
  const prefN = {};
  for (const r of rows) if (r.pref) prefN[r.pref] = (prefN[r.pref] || 0) + 1;
  const prefChips = PREFS.filter(p => prefN[p]).map(p => `<label class="pchip${keepP.has(p) ? ' on' : ''}">`
    + `<input type="checkbox" name="pref" value="${E(p)}"${keepP.has(p) ? ' checked' : ''}>`
    + `<span class="pl">${E(p)}</span><span class="pn">${prefN[p]}</span></label>`).join('');
  const sameAll = keepK.size === all.size && [...all].every(k => keepK.has(k));
  const nowK = sameAll ? 'すべて' : KINDS.filter(([k]) => keepK.has(k)).map(([, lb]) => lb).join('・') + `（${keepK.size}）`;
  const nowP = !keepP.size ? 'すべて' : PREFS.filter(p => keepP.has(p)).join('・') + `（${keepP.size} 県）`;
  const active = selKinds !== null || keepP.size > 0;
  return `<form class="pfil calfil" method="get" action="/calendar">
<input type="hidden" name="t" value="__TAGURI_TOKEN__">
<details class="pbox"${active ? ' open' : ''}>
<summary>${ico('search', 15)}種類と都道府県で絞り込む（種類：<b>${E(nowK)}</b>・場所：<b>${E(nowP)}</b>）</summary>
<p class="lead">選んだ種類と都道府県の公演だけを、下のカレンダーに表示します。<b>いくつでも同時に選べます。</b>
ページの上の「観劇日を追加する」で選べる公演は、絞り込んでも変わりません。</p>
<div class="pchips">${kindChips}</div>
<div class="pchips">${prefChips}</div>
<div class="pfoot"><button type="submit">${ico('search')}この条件で絞り込む</button>
<a class="pall" href="/calendar?t=__TAGURI_TOKEN__">すべて表示に戻す</a></div>
</details></form>`;
}

/** stage_calendar.panel (no tickets left unplaced: mail import is the owner's only) */
export function panel(d, today, tickets, selKinds = null, selPrefs = null) {
  const rows = rowsOf(d, today, tickets);
  if (!rows.length) return '<p class="empty">カレンダーに表示できる公演がありません。推薦の画面で「興味あり」を押した公演と、お気に入りに登録した名前で見つかった公演が、ここに並びます。</p>';
  const filt = filterHtml(rows, selKinds, selPrefs);
  const keepK = selKinds ?? new Set(KIND_KEYS);
  const view = rows.filter(r => keepK.has(r.key) && (selPrefs === null || selPrefs.has(r.pref)));
  // 都道府県が分からない公演（一覧 catalogue にだけあり、索引に無い公演）は、場所で絞ると出せない。
  // 黙って消すと「絞ったら 0 件」に見えるので、件数を言う（起案者の指摘 2026-10-15「場所絞ったら公演カレンダー0件になる」）
  const nUnknown = selPrefs === null ? 0 : rows.filter(r => keepK.has(r.key) && !r.pref).length;
  const unknown = nUnknown ? `<p class="lead"><b>都道府県が分からない公演が ${nUnknown} 件あり、場所で絞ると表示できません。</b>`
    + `<a href="/calendar?t=__TAGURI_TOKEN__">絞り込みを外す</a>と表示されます。</p>` : '';
  if (!view.length) return `${filt}${unknown}<p class="empty">選んだ条件に一致する公演がありません。<a href="/calendar?t=__TAGURI_TOKEN__">絞り込みを外してください</a>。</p>`;
  let legend = KINDS.map(([, label, icon, cls]) => `<span class="lg"><span class="bar ${cls} sm">${ico(icon, 13)}</span>${E(label)}</span>`).join('');
  legend += '<span class="lg"><span class="bar own sm"><span class="pt"></span></span>行く日</span>'
    + '<span class="lg"><span class="bar own sm"><span class="pt un"></span></span>メールから読み取った回（確定前）</span>';
  const last = view.map(r => r.end).sort().at(-1);
  const ms = [];
  let y = Number(today.slice(0, 4)), m = Number(today.slice(5, 7));
  const [ly, lm] = [Number(last.slice(0, 4)), Number(last.slice(5, 7))];
  while ((y < ly || (y === ly && m <= lm)) && ms.length < MAX_MONTHS) {
    ms.push([y, m]);
    [y, m] = m === 12 ? [y + 1, 1] : [y, m + 1];
  }
  const blocks = timeline(view, ms, today);
  const [lastY, lastM] = ms.at(-1);
  const over = view.filter(r => { const [sy, sm] = [Number(r.start.slice(0, 4)), Number(r.start.slice(5, 7))]; return sy > lastY || (sy === lastY && sm > lastM); });
  const tail = over.length ? `<p class="lead"><b>${over.length} 件は ${MAX_MONTHS} か月より先の公演なので、このカレンダーには表示していません。</b>「おすすめ ▸ 興味あり／お気に入り」の一覧には載っているので、そちらで確認してください。</p>` : '';
  return `${filt}${unknown}<p class="lead toinfo">帯の<b>右端が楽日</b>、つまり締切です。縦にたどると、その日に上演している公演の数を数えられます。<b>土曜は青、日曜は赤</b>で示しています。</p>`
    + `<div class="cal-legend">${legend}</div>`
    + '<p class="calnote toinfo"><b>券を持っている公演は、行く日を入れると、その日が半券の形で帯から抜けて見えます。</b>行く日を入れていない公演は帯だけで表示するので、<b>「この期間のどこかに行く」という意味</b>になります。印の付いていない日が空いているという意味ではありません。</p>'
    + `${blocks}${tail}${CALENDAR_JS}`;
}

/** stage_calendar._ticket_li: 消す口は「この日時を削除」、data-done に消したあとの文（#100）。left: 残る行く日の数 */
function ticketLi(t, loc = '', left = 0) {
  const when = `${t.date}` + (t.time ? ` ${t.time}` : '（時刻を入れていません）');
  const ok = Boolean(t.confirmed);
  const src = ok ? '' : '<i>購入確認メールから</i>';
  const sid = E(String(t.sid || ''));
  const lb = loc ? `<b class="tkloc">${E(loc)}</b> ` : '';
  const md = `${Number(t.date.slice(5, 7))}/${Number(t.date.slice(8, 10))}` + (t.time ? ` ${t.time}` : '');
  const done = `${md} の行く日を削除しました。公演の登録（購入済み・興味あり・お気に入り）は変わりません。` + (left ? `入れてある日は、あと ${left} 件です` : '入れてある日は、もうありません');
  const tip = `この行く日（${md}）だけを消します。購入済み・興味あり・お気に入りの登録は消えません`;
  let btn = `<button data-del="1" data-stage="${sid}" data-date="${E(t.date)}" data-time="${E(t.time)}" title="${E(tip)}" data-done="${E(done)}">この日時を削除</button>`;
  if (!ok) btn = `<button class="go-ok" data-ok="1" data-stage="${sid}" data-date="${E(t.date)}" data-time="${E(t.time)}">確定</button>` + btn;
  return `<li class="${ok ? '' : 'un'}">${lb}<span>${E(when)}${src}</span>${btn}</li>`;
}
/** stage_calendar._own_merged */
function ownMerged(rows) {
  const own = rows.filter(r => r.cls === 'own' || r.tickets.length);
  const groups = new Map();
  for (const r of own) { const k = workKey(r.title, r.sid); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(r); }
  return [...groups.values()].map(g0 => {
    const g = [...g0].sort((a, b) => cmp(a.start, b.start));
    return {...g[0], venues: g, tickets: g.flatMap(r => r.tickets.map(t => ({...t, sid: r.sid}))),
      start: g.map(r => r.start).sort()[0], end: g.map(r => r.end).sort().at(-1), merged: g.length > 1};
  });
}
/** stage_calendar.add_ticket_button_html */
export function addTicketButtonHtml(d, today, tickets) {
  const own = ownMerged(rowsOf(d, today, tickets));
  if (!own.length) return '';
  const opts = [], infos = [];
  for (const r of own) {
    const tag = r.merged ? `（${r.venues.length} 会場）` : '';
    opts.push(`<option value="${E(r.sid)}" data-lo="${r.start}" data-hi="${r.end}">${E(r.title)}${tag}</option>`);
    let sched = '';
    if (r.merged) {
      sched = '<div class="tourfull">' + r.venues.map(v => `<div class="tf-row${v.end < today ? ' done' : ''}">`
        + `<span class="tf-loc">${E(regionLabel(v.pref, v.venue || '会場未定'))}公演</span><span class="tf-when">${E(runRange(v.period, today) || v.period)}</span></div>`).join('') + '</div>';
    }
    const li = r.tickets.map(t => ticketLi(t, r.merged ? regionLabel(r.venues.find(v => v.sid === t.sid)?.pref || '') : '', r.tickets.length - 1)).join('');
    // 日時を直す口は別に無い ── 消してから下の「行く日」「時刻」で入れ直す（#100）
    const have = li ? `<p class="tkihave">入れてある日（日時を直すときは「この日時を削除」で消して、下の「行く日」から入れ直してください）</p><ul class="tklist">${li}</ul>` : '';
    infos.push(`<div class="tkinfo" data-for="${E(r.sid)}" hidden>${sched}${have}</div>`);
  }
  return `<button type="button" class="addtk" data-open-dialog="tkdlg">
${ico('plus', 16)}観劇日を追加する</button>
<dialog id="tkdlg" class="tkdlg">
<form method="dialog" class="tkdform">
<h3>${ico('clock', 16)}観劇日を追加する</h3>
<label>公演<select class="tkd-work">${opts.join('')}</select></label>
<div class="tkinfos">${infos.join('')}</div>
<label>行く日<input type="date" class="tkd-date"></label>
<label>時刻（任意）<input type="time" class="tkd-time"></label>
<div class="tkdfoot"><span class="said"></span>
<button type="button" data-dlg-close="1">閉じる</button>
<button type="button" data-dlg-add="1">この回に行く</button></div>
</form></dialog>`;
}

// ---------------------------------------------------------------- the screen (app._calendar_body)
// The stages' run and place: the recommendation index, else the delivered catalogue
// (fallback.stageInfo). The index is replaced only on days it fits the write budget, so a
// stage the user owns can be missing from it; 購入済み公演 already shows those from the
// catalogue, and the calendar left them out (起案者 2026-10-14「購入済みに作品が入っているのに、
// 公演カレンダーになにも表示されない」).
async function entries(ctx, sids) {
  const out = new Map();
  for (const [sid, s] of await stageInfo(ctx.db, sids)) {
    if (!s.period) continue;
    out.set(sid, {stage_id: sid, title: s.title, period: s.period, venue: s.venue, theater: s.venue, pref: s.pref,
      group: s.group, fields: s.fields, ...(s.url ? {url: s.url} : {})});
  }
  return out;
}

export async function calendarScreen(params, ctx) {
  const b = await buckets(ctx);
  // 「観劇日を追加する」は、購入済の公演のツアーの全会場から日付を選べるようにする（起案者の指摘 2026-10-24「ミス・サイゴン
  // 1月の終わりまでツアーでやってるのに、観劇日を追加しようとしても1月カレンダーが選べなくなってしまってる」）。前は押した会場
  // 1 つの会期だけだった。入れた日は、その日に上演している会場の券になる（lists.ticketAction）。カレンダーの帯は前のまま
  const tourSids = r => (r.sids?.length ? r.sids : [r.stage_id]);
  const sids = [...new Set(['owned', 'tracking', 'favourites'].flatMap(k => b[k].flatMap(r => (k === 'owned' ? tourSids(r) : [r.stage_id]))))];
  const ent = await entries(ctx, sids);
  const d = Object.fromEntries(['owned', 'tracking', 'favourites'].map(k => [k, b[k].map(r => ent.get(r.stage_id)).filter(Boolean)]));
  const dlg = {...d, owned: b.owned.flatMap(r => tourSids(r).map(s => ent.get(s))).filter(Boolean)};
  const kinds = params.getAll('kind').filter(k => KIND_KEYS.includes(k));
  const prefs = params.getAll('pref').filter(p => PREFS.includes(p));
  // 表示できる公演が 1 件も無いときは、説明の文と帯の代わりに、イラスト付きの案内だけを出す（起案者の指示 2026-10-24
  // 「公演カレンダーの初期画面、おすすめと同じようにイラスト付きでページ説明を書いて」。panel は Python の stage_calendar と同じ形のまま）
  if (!rowsOf(d, ctx.today, b.tickets).length) return {title: '公演カレンダー', body_html: `<h1>公演カレンダー</h1>
${emptyGuide('calendar', 'カレンダーに表示できる公演がありません。', '<p>推薦の画面で「興味あり」を押した公演と、お気に入りに関連する公演の情報が表示されます。</p>')}`};
  const body = `<h1>公演カレンダー</h1>
${addTicketButtonHtml(dlg, ctx.today, b.tickets)}
<p class="lede toinfo">券を持っている公演、「興味あり」を押した公演、お気に入りに登録した名前で見つかった公演を、上演期間の帯で並べています。<b>いつまで観られるか</b>が1枚で分かります。券を持っている公演は、行く日を入れるとその日が半券の形で出ます。</p>
${panel(d, ctx.today, b.tickets, kinds.length ? new Set(kinds) : null, prefs.length ? new Set(prefs) : null)}`;
  return {title: '公演カレンダー', body_html: body};
}

export const calendarScreens = {screens: {calendar: calendarScreen}, actions: {}};
