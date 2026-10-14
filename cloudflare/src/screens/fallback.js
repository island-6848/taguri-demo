// Stages without a prebuilt card (rec_card). The cards are made by the batch, and on
// days its rows do not fit the write budget they are not replaced, so a stage that
// opens soon may be only in the delivered catalogue (開幕リマインド adds those, see
// reminder.openingCandidates). Answering such a stage must still show it in 興味あり
// and keep the answer on 開幕リマインド (起案者の指摘 2026-10-14「開幕リマインドで
// 『興味あり』押して、そのまま開いても 0 件になる」), so its card is drawn here from
// what the catalogue and the index carry: title, run, venue, credits and synopsis.
import {E} from './py.js';
import {ico} from './icons.js';
import {castBlock} from './settings.js';

const PER_QUERY = 90;
const slash = d => String(d || '').replaceAll('-', '/');
const dash = d => String(d || '').replaceAll('/', '-');
const md = d => (d ? `${Number(d.slice(5, 7))}/${Number(d.slice(8, 10))}` : '');

/** stage_id -> {stage_id, title, start, end, venue, pref, group, period, fields, synopsis, url} from catalogue / rec_stage. */
export async function stageInfo(db, sids) {
  const out = new Map();
  const want = [...new Set(sids.filter(Boolean).map(String))];
  for (let i = 0; i < want.length; i += PER_QUERY) {
    const part = want.slice(i, i + PER_QUERY), qs = part.map(() => '?').join(',');
    const [idx, cat] = await db.batch([
      db.prepare(`SELECT stage_id,title,start,end,entry FROM rec_stage WHERE ver=(SELECT v FROM rec_meta WHERE k='current') AND stage_id IN (${qs})`).bind(...part),
      db.prepare(`SELECT id,title,date,venue,url,metadata FROM catalogue WHERE id IN (${qs})`).bind(...part),
    ]);
    for (const r of idx.results) {
      let e = {};
      try { e = JSON.parse(r.entry || '{}') || {}; } catch { /* no entry */ }
      out.set(String(r.stage_id), {stage_id: String(r.stage_id), title: r.title, start: dash(r.start), end: dash(r.end),
        venue: e.theater || e.venue || '', pref: e.pref || '', group: e.group || '', period: e.period || '',
        fields: e.fields || {}, synopsis: '', url: e.url || ''});
    }
    for (const r of cat.results) {
      let m = {};
      try { m = JSON.parse(r.metadata || '{}') || {}; } catch { /* no metadata */ }
      const end = /^\d{4}-\d{2}-\d{2}$/.test(m.end_date || '') ? m.end_date : r.date;
      const have = out.get(String(r.id)) || {};
      out.set(String(r.id), {stage_id: String(r.id), title: have.title || r.title, start: have.start || r.date, end: have.end || end,
        venue: have.venue || r.venue || '', pref: have.pref || '', group: have.group || m.group || '',
        period: have.period || `${slash(r.date)} ～ ${slash(end)}`, fields: Object.keys(have.fields || {}).length ? have.fields : (m.fields || {}),
        synopsis: m.synopsis || '', url: have.url || r.url || ''});
    }
  }
  return out;
}

const safeUrl = u => (/^https?:\/\//.test(String(u || '')) ? String(u) : '');
const range = s => (s.start ? (s.end && s.end !== s.start ? `${md(s.start)}〜${md(s.end)}` : md(s.start)) : '');

/** The parts shown when a row is opened: run, credits and synopsis. */
export function detailHtml(s) {
  const syn = s.synopsis
    ? `<div class="syn"><p class="txt">${E(s.synopsis)}</p><span class="src">［出典: 公演の紹介文］</span></div>`
    : '<div class="syn no">あらすじを取れませんでした</div>';
  const url = safeUrl(s.url);
  return `<div class="when">${E(range(s))}${s.venue ? '・' + E(s.venue) : ''}</div>${castBlock(s.fields || {})}${syn}`
    + (url ? `<p class="dgsite"><a href="${E(url)}" target="_blank" rel="noopener noreferrer">公式サイト</a></p>` : '');
}

/** A card template like rec_card's (the same markers, for cards.compose), drawn from stageInfo. */
export function fallbackTemplate(s, {why = false} = {}) {
  const url = safeUrl(s.url);
  const site = url ? `<a class="sitebtn" href="${E(url)}" target="_blank" rel="noopener noreferrer">${ico('link', 14)}公式サイト</a>` : '';
  const meta = [s.group ? `<span class="grp">${E(s.group)}</span>` : '', E(s.venue || '')].filter(Boolean).join('<span class="sep">／</span>')
    + (s.pref ? `<span class="pref">（${E(s.pref)}）</span>` : '');
  return `<article class="ticket recommend" data-stage="${E(s.stage_id)}" data-tours="">
<div class="stub" aria-hidden="true"><!--mark--><span class="sd"><b>${E(md(s.start))}</b><span class="sk">初日</span></span></div>
<div class="perf" aria-hidden="true"></div>
<div class="body"><div class="pcol"><!--poster-->${site}</div>
<div class="main">
 <h3>${E(s.title)}</h3>
 <div class="meta">${meta}</div>
 <!--mytix-->
 <div class="when">${E(range(s))}</div>
 ${castBlock(s.fields || {})}
 ${s.synopsis ? `<div class="syn"><p class="txt">${E(s.synopsis)}</p><span class="src">［出典: 公演の紹介文］</span></div>` : '<div class="syn no">あらすじを取れませんでした</div>'}
 ${why ? `<div class="whyh">${ico('eye', 14)}<!--whyh--></div><ul class="why"><!--why--></ul>` : ''}
 <div class="act"><!--btns--></div>
 <!--why_note-->
 <!--no_note-->
</div></div></article>`;
}

/** The outer element starting at `start` in html (a <div ...> with nested divs), or ''. */
function block(html, start) {
  const i = html.indexOf(start);
  if (i < 0) return '';
  const tag = /<(\/?)(div|details)\b[^>]*>/g;
  tag.lastIndex = i;
  let depth = 0, m;
  while ((m = tag.exec(html))) {
    depth += m[1] ? -1 : 1;
    if (depth === 0) return html.slice(i, m.index + m[0].length);
  }
  return '';
}

/** The opened parts of a prebuilt card: run and price, sale, credits, synopsis (without the edit form). */
export function detailFromCard(card) {
  const syn = block(card, '<div class="syn').replace(/<details class="handt">[\s\S]*?<\/details>/, '');
  return ['<div class="when">', '<div class="sale">', '<div class="cast">'].map(s => block(card, s)).join('') + syn;
}
