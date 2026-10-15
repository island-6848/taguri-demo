// 電光掲示板（画面の上に流す帯）: 今週開幕する公演と、今週のおすすめの上位 3 件。
// 起案者の指示（2026-10-15）「今週開幕する公演を電車の電光掲示板みたいにメニューに流すのはどう？
// あと今週のおすすめ上位3件とな」「つくってみて」(docs/knowledge: dec-ticker)。
//
// どの画面でも出すので軽くする:
// - おすすめは、作り置き（rec_cache）にあるものだけを読む。新しく計算しない（Workers Free の CPU 10 ms）。
// - 開幕は、開幕リマインドと同じ候補（索引＋一覧）から今週の分だけ。答えたかどうかは見ない（見逃し防止）。
// - 観に行ける場所（設定）を選んでいれば、その都道府県と、都道府県の分からない公演に絞る。
// - 画面（app.js）は 10 分使い回し、記録を書いたら捨てる。何も無ければ帯を出さない。
import {openingCandidates, weekRows} from './reminder.js';
import {stageInfo} from './fallback.js';
import {prefsFor} from './prefs.js';

const OPEN_MAX = 10, RECS = 3;
const md = d => (d ? `${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}` : '');
const WD = '日月火水木金土';
const wd = d => WD[new Date(d + 'T00:00:00Z').getUTCDay()];

/** GET /api/screen/ticker -> {ticker: {open: [{stage_id, title, venue, date, label}], recs: [{stage_id, title}]}} */
export async function tickerScreen(_params, ctx) {
  const prefs = await prefsFor(new URLSearchParams(), ctx);
  const rows = weekRows(await openingCandidates(ctx), new Map(), ctx.today, 0)
    .filter(r => !prefs.length || !r.pref || prefs.includes(r.pref));
  const seen = new Set();
  const open = [];
  for (const r of rows) {
    const k = r.title + '\u0000' + r.start;
    if (seen.has(k)) continue;           // one line per production and day (tours)
    seen.add(k);
    open.push({stage_id: r.stage_id, title: r.title || '', venue: r.theater || r.venue || '', date: r.start,
      label: `${md(r.start)}（${wd(r.start)}）`});
    if (open.length >= OPEN_MAX) break;
  }
  let recs = [];
  const cached = await ctx.db.prepare('SELECT body FROM rec_cache WHERE user_id=?').bind(ctx.uid).first();
  if (cached) {
    let body = {};
    try { body = JSON.parse(cached.body) || {}; } catch { /* a broken cache shows no recommendations */ }
    const sids = (body.groups || []).slice(0, RECS).map(g => String(g.stage_id));
    const info = sids.length ? await stageInfo(ctx.db, sids) : new Map();
    recs = sids.map(sid => ({stage_id: sid, title: info.get(sid)?.title || ''})).filter(r => r.title);
  }
  return {title: '電光掲示板', body_html: '', ticker: {open, recs}};
}

export const tickerScreens = {screens: {ticker: tickerScreen}, actions: {}};
