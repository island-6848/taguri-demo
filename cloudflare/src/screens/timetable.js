// 観劇の時間割 ── 何曜日の、昼（マチネ）と夜（ソワレ）のどちらに観ているか（起案者の指示 2026-10-16
// 「時間割から実装してよい」、dec-records-viz-picks）。年輪が「何年のどの季節か」を見せるのに対し、
// こちらは「1 週間のどこで観るか」。観た回は、行った日が過ぎたチケット（ticket）と、日記帳の観た日（works）から数える。
import {E} from './py.js';
import {h2} from './icons.js';

export const DAYS = ['月', '火', '水', '木', '金', '土', '日'];
export const SLOTS = [['m', 'マチネ', '17 時より前'], ['s', 'ソワレ', '17 時から'], ['u', '時刻なし', '開演時刻が分からない回']];
const SOIREE_FROM = 17 * 60;

/** 0 = 月 … 6 = 日 of a YYYY-MM-DD date (null if not a date). */
export function weekday(date) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(date || ''));
  if (!m) return null;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  // 13 月・32 日のような日付は Date が翌月へ繰り越すので、元に戻るかで確かめる
  if (Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== m[0]) return null;
  return (d.getUTCDay() + 6) % 7;
}

/** 'm' (before 17:00), 's' (from 17:00) or 'u' (no time). */
export function slotOf(time) {
  const m = /^(\d{1,2}):(\d{2})/.exec(String(time || '').trim());
  if (!m) return 'u';
  return +m[1] * 60 + +m[2] < SOIREE_FROM ? 'm' : 's';
}

/**
 * The visits: every ticket whose day has come (a ticket is one visit, with its curtain time),
 * then each seen work's first and last day that no ticket of that day stands for.
 * `tickets`: [{date, time}], `works`: [{first_date, last_date, time}].
 */
export function visits(tickets, works, today) {
  const out = [], ticketDays = new Set();
  for (const t of tickets) {
    if (!t.date || t.date > today) continue;
    out.push({date: t.date, time: t.time || ''});
    ticketDays.add(t.date);
  }
  for (const w of works) {
    const days = [...new Set([w.first_date, w.last_date].filter(d => d && d <= today))];
    for (const d of days) {
      if (ticketDays.has(d)) continue;
      // The work's own time is the curtain of the day it was entered for (the first one).
      out.push({date: d, time: d === w.first_date ? (w.time || '') : ''});
    }
  }
  return out.filter(v => weekday(v.date) !== null);
}

/** Cells of shade: 0 (none) … 4, by the share of the busiest cell. */
const level = (n, max) => (n ? Math.max(1, Math.ceil((4 * n) / max)) : 0);

/** The panel (empty string when there is nothing to show). */
export function timetablePanel(vs) {
  if (!vs.length) return '';
  const grid = new Map();
  for (const v of vs) {
    const k = weekday(v.date) + '|' + slotOf(v.time);
    grid.set(k, (grid.get(k) || 0) + 1);
  }
  const cell = (d, s) => grid.get(d + '|' + s) || 0;
  const max = Math.max(...grid.values());
  const timed = vs.filter(v => slotOf(v.time) !== 'u').length;
  // The busiest weekday × matinée/soirée (ties: earlier in the week, matinée first).
  let best = null;
  for (let d = 0; d < 7; d++) for (const [s] of SLOTS.slice(0, 2)) if (cell(d, s) && (!best || cell(d, s) > best[2])) best = [d, s, cell(d, s)];
  const slotName = s => SLOTS.find(x => x[0] === s)[1];
  const rows = DAYS.map((name, d) => {
    const cells = SLOTS.map(([s, label]) => {
      const n = cell(d, s);
      return `<td class="tt-c tt-${level(n, max)}${s === 'u' ? ' tt-u' : ''}" title="${E(name)}曜 ${E(label)}：${n} 回"><span class="tt-n">${n || '·'}</span>`
        + `<span class="sr">${E(name)}曜 ${E(label)} ${n} 回</span></td>`;
    }).join('');
    const total = SLOTS.reduce((a, [s]) => a + cell(d, s), 0);
    return `<tr${d >= 5 ? ' class="tt-we"' : ''}><th scope="row">${E(name)}</th>${cells}<td class="tt-t">${total}</td></tr>`;
  }).join('');
  const head = SLOTS.map(([, label, hint]) => `<th scope="col" title="${E(hint)}">${E(label)}</th>`).join('');
  const lead = best
    ? `いちばん多いのは <b>${E(DAYS[best[0]])}曜の${E(slotName(best[1]))}（${best[2]} 回）</b>です。`
    : '開演時刻の分かる回がまだありません。';
  return `<section class="card">
${h2('clock', '観劇の時間割 ── 1 週間のどこで観ているか', `<span class="badge part">${vs.length} 回</span>`)}
<p class="lead">観た回を、曜日と開演の時刻（17 時より前がマチネ、17 時からがソワレ）で数えています。${lead}
開演時刻が分かるのは <b>${vs.length} 回のうち ${timed} 回</b>で、チケットか日記帳に時刻を入れた回です。</p>
<table class="tt" aria-label="観劇の時間割。行が曜日、列がマチネ・ソワレ・時刻なし、数は観た回数">
<thead><tr><th></th>${head}<th scope="col">計</th></tr></thead>
<tbody>${rows}</tbody></table>
</section>`;
}

/** The visits of the user: their tickets whose day has come and their seen works. */
export async function timetableFor(ctx, seen, today) {
  const {results} = await ctx.db.prepare('SELECT date, time FROM ticket WHERE user_id=? AND date<=?').bind(ctx.uid, today).all();
  return timetablePanel(visits(results, seen, today));
}
