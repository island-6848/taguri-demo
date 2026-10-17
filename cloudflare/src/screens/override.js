// 管理者が手で直した公演の情報（migration 0028 stage_override）を、画面に出すときに重ねる。
// 書くのは手元の管理画面（tools/admin/serve_admin.py）だけで、Worker は読むだけ。
import {E} from './py.js';

/** stage_id -> {synopsis: string|null, themes: string[]|null, info: object} (missing table: empty). */
export async function loadOverrides(db, sids) {
  const out = new Map();
  const want = [...new Set(sids.filter(Boolean).map(String))];
  try {
    for (let i = 0; i < want.length; i += 90) {
      const part = want.slice(i, i + 90);
      const {results} = await db.prepare(`SELECT stage_id,synopsis,themes,info FROM stage_override WHERE stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
      for (const r of results) out.set(String(r.stage_id), {synopsis: r.synopsis ?? null, themes: parseJson(r.themes, null), info: parseJson(r.info, {}) || {}});
    }
  } catch { /* migration 0028 not applied yet */ }
  return out;
}
const parseJson = (s, dflt) => { if (s === null || s === undefined || s === '') return dflt; try { return JSON.parse(s); } catch { return dflt; } };

/** Where the card's あらすじ block <div class="syn…" data-stage="sid"> starts and ends ([start, end) or null). */
function synSpan(html, sid) {
  const open = new RegExp(`<div class="syn[^"]*" data-stage="${sid.replace(/[^\w-]/g, '')}">`).exec(html);
  if (!open) return null;
  const re = /<div\b|<\/div>/g;
  re.lastIndex = open.index + open[0].length;
  let depth = 1, m;
  while ((m = re.exec(html))) {
    depth += m[0] === '</div>' ? -1 : 1;
    if (!depth) return [open.index, m.index + m[0].length];
  }
  return null;
}

/** The あらすじ block from a hand-entered synopsis and/or themes (the card's own text where one is not given). */
export function synBlock(sid, ov, base = {}) {
  const syn = (ov.synopsis ?? base.synopsis ?? '').trim();
  const tags = (ov.themes ?? base.themes ?? []).map(w => String(w).trim()).filter(Boolean);
  const tagHtml = tags.length ? `<div class="tags">${tags.map(w => `<span class="tag">#${E(w)}</span>`).join('')}</div>` : '';
  const cite = '<span class="src">［たぐりの管理者が入れた内容です］</span>';
  if (syn) return `<div class="syn" data-stage="${E(sid)}"><p class="txt">${E(syn)}</p>${tagHtml}${cite}<button class="mrb" data-more="1">続きを読む</button></div>`;
  if (tags.length) return `<div class="syn part" data-stage="${E(sid)}">あらすじは公演ページに載っていません。題材は次のとおりです。${tagHtml}${cite}</div>`;
  return '';
}

const unE = s => s.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

/** The card with its あらすじ block replaced by the hand-entered one (unchanged when nothing was entered). */
export function applySynopsis(html, sid, ov) {
  if (!ov || (ov.synopsis === null && ov.themes === null)) return html;
  const span = synSpan(html, sid);
  const old = span ? html.slice(span[0], span[1]) : '';
  const txt = /<p class="txt">([\s\S]*?)<\/p>/.exec(old);
  const base = {synopsis: txt ? unE(txt[1]) : '', themes: [...old.matchAll(/<span class="tag">#([\s\S]*?)<\/span>/g)].map(m => unE(m[1]))};
  const block = synBlock(sid, ov, base);
  if (span) return html.slice(0, span[0]) + block + html.slice(span[1]);
  // あらすじの枠が無いカード: 出演の欄の後ろ、無ければ本文の終わりに足す
  const at = html.lastIndexOf('</article>');
  return at < 0 ? html + block : html.slice(0, at) + block + html.slice(at);
}

/**
 * カードにあらすじの本文が無いのに、公演一覧（catalogue）には読み取り済みのあらすじがある公演に、その本文を入れる
 * （起案者の質問 2026-10-17「すでにあらすじが取れている公演なのに、各画面に実際の文章が表示されていないのはなぜ？」）。
 * カード（rec_card）は全部を 1 つの版として毎日作り直し、その日の書き込みの枠に入らない日は丸ごと見送る
 * （deliver_catalogue.py）。一覧の行は変わった分だけ先に入るので、あとから読み取ったあらすじは一覧にだけ届き、
 * カードは古いままになることがある。どちらも同じ themes.jsonl（本文に実在するか確かめた分）から来る。
 * html: Map(sid -> card)。手で入れたあらすじ（stage_override）がある公演は触らない。
 */
export async function fillCatalogueSynopsis(db, html, overrides = new Map()) {
  const want = [...html].filter(([sid, h]) => !/<p class="txt">/.test(h) && !(typeof overrides.get(sid)?.synopsis === 'string')).map(([sid]) => sid);
  for (let i = 0; i < want.length; i += 90) {
    const part = want.slice(i, i + 90);
    const {results} = await db.prepare(`SELECT id,metadata FROM catalogue WHERE id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) {
      const syn = String(parseJson(r.metadata, {})?.synopsis || '').trim();
      const sid = String(r.id);
      if (!syn || !html.has(sid)) continue;
      const card = html.get(sid), span = synSpan(card, sid);
      const old = span ? card.slice(span[0], span[1]) : '';
      // 題材のタグと、内容を直す入れ口（details）は、もとの枠のものを残す
      const tags = (/<div class="tags">[\s\S]*?<\/div>/.exec(old) || [''])[0];
      const form = (/<details class="handt">[\s\S]*<\/details>/.exec(old) || [''])[0];
      const block = `<div class="syn" data-stage="${E(sid)}"><p class="txt">${E(syn)}</p>${tags}`
        + `<span class="src">［出典: 公演の紹介文］</span><button class="mrb" data-more="1">続きを読む</button>${form}</div>`;
      if (span) html.set(sid, card.slice(0, span[0]) + block + card.slice(span[1]));
    }
  }
  return html;
}

/** stageInfo's entry with the hand-entered details laid over it. */
export function mergeInfo(s, ov) {
  if (!ov) return s;
  const info = ov.info || {};
  const out = {...s, fields: {...(s.fields || {}), ...(info.fields || {})}};
  for (const k of ['venue', 'pref', 'period', 'url']) if (typeof info[k] === 'string' && info[k]) out[k] = info[k];
  if (typeof ov.synopsis === 'string') out.synopsis = ov.synopsis;
  return out;
}

export const PRICE_FIELD = '料金（1枚あたり）';
/** render_recommend.price_range: the cheapest and dearest ticket in yen, [0, 0] for free, null when unreadable. */
export function priceRange(text) {
  const t = String(text || '').normalize('NFKC').replace(/【発売日】.*?(?=【|$)/gs, ' ');
  const vals = [];
  for (const m of t.matchAll(/(?:[¥￥]\s*([0-9][0-9,]*)|([0-9][0-9,]*)\s*円)/g)) {
    const v = Number((m[1] || m[2]).replace(/,/g, ''));
    if (Number.isFinite(v) && v >= 0 && v <= 100000) vals.push(v);
  }
  if (vals.length) return [Math.min(...vals), Math.max(...vals)];
  return /無料|入場料なし|投げ銭|カンパ/.test(t) ? [0, 0] : null;
}

/** The card with a hand-entered price: the price line and the data-yen used by the price filter. */
export function applyPrice(html, ov) {
  const price = ((ov && ov.info && ov.info.fields) || {})[PRICE_FIELD];
  if (typeof price !== 'string' || !price.trim()) return html;
  let out = html.replace(/<span class="price">[\s\S]*?<\/span>/, `<span class="price">${E(price.trim())}</span>`);
  const r = priceRange(price);
  out = out.replace(/(<article class="ticket[^"]*")( data-yen="[^"]*")?/, (_, a) => a + (r ? ` data-yen="${r[0]}-${r[1]}"` : ''));
  return out;
}
