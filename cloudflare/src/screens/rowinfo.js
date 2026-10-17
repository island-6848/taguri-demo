// 評価一覧・未評価・日記帳の 1 件（row.recRow）に、つながった公演の団体・会場・作り手・あらすじを添える。
// 起案者の指示 2026-10-18「評価一覧や日記帳のカードもおすすめと揃えて」── おすすめのカードと同じく、
// 作・原作・脚本・演出（と設定で選んだ役職）の名前と、囲んだあらすじを出す。形を作るのは画面（web/app.js の compactRows）。
// サービス版（Worker）だけの欄なので、Python との比べ（test/screens.test.js）からは外す。
// 読むのは 1 枚に出す分（SHEET_TOP 件）の公演だけ: stageInfo（公演・一覧・手で直した欄）、カード（rec_card）の
// あらすじ、過去の公演（past_stage）の会場。どれも stage_id の主キーで引くので、1 枚で数十行の読み取りに収まる。
import {E} from './py.js';
import {stageInfo} from './fallback.js';
import {pastStages} from './autolink.js';

// 作り手の役職の並び（画面の CREDIT_BASE・CREDIT_OPTIONS と同じ順）。ほかの役職はその後ろに名前の順で並べる
const ROLE_ORDER = ['作', '原作', '脚本', '演出', '出演', '翻訳', '音楽', '作曲', '振付'];
// 公演の欄（entry.fields）にしか無い作り手を拾う役職
const FIELD_ROLES = ['作', '原作', '脚本', '演出', '翻訳', '音楽', '作曲', '振付'];
const unE = s => s.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');

/** stage_id -> あらすじ（カードの本文）。stageInfo に無い公演の分だけ引く。 */
async function cardSynopses(db, sids) {
  const out = new Map();
  for (let i = 0; i < sids.length; i += 90) {
    const part = sids.slice(i, i + 90);
    let results = [];
    try {
      ({results} = await db.prepare(`SELECT stage_id,html FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all());
    } catch { return out; }
    for (const r of results) {
      const m = /<p class="txt">([\s\S]*?)<\/p>/.exec(r.html || '');
      if (m) out.set(String(r.stage_id), unE(m[1]).trim());
    }
  }
  return out;
}

/** [[役職, 名前]] を役職ごとにまとめる（同じ名前は 1 回）。欄にしか無い役職は欄から足す。 */
export function creditRows(people, fields = {}) {
  const by = new Map();
  for (const [role, name] of people || []) {
    const r = String(role || ''), n = String(name || '').trim();
    if (!r || r.startsWith('#') || !n) continue;
    if (!by.has(r)) by.set(r, []);
    if (!by.get(r).includes(n)) by.get(r).push(n);
  }
  for (const r of FIELD_ROLES) {
    if (by.has(r) || typeof fields[r] !== 'string') continue;
    const names = fields[r].split(/[、,，／/\n]+/).map(s => s.trim()).filter(Boolean);
    if (names.length) by.set(r, names);
  }
  const rank = r => { const i = ROLE_ORDER.indexOf(r); return i < 0 ? ROLE_ORDER.length : i; };
  return [...by].sort((a, b) => rank(a[0]) - rank(b[0]) || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
}

/**
 * work_key -> {grp, venue, synopsis, credits, url, page} for the rows on this sheet. people: diary.peopleByKey の結果
 * （手で入れた作り手も入っている）。つながった公演が無く、出すものも無い記録は入れない。
 */
export async function rowInfos(ctx, ws, people = {}) {
  const sids = [...new Set(ws.map(w => w.stage_id).filter(Boolean).map(String))];
  const info = sids.length ? await stageInfo(ctx.db, sids) : new Map();
  const past = await pastStages(ctx.db, sids.filter(s => !info.has(s)));
  const cards = await cardSynopses(ctx.db, sids.filter(s => !(info.get(s)?.synopsis || '').trim()));
  const out = {};
  for (const w of ws) {
    const sid = String(w.stage_id || '');
    const s = info.get(sid) || {}, p = past[sid] || {};
    const credits = creditRows(people[w.work_key] || [], s.fields || {});
    const synopsis = String(s.synopsis || cards.get(sid) || '').trim();
    const venue = s.venue ? s.venue + (s.pref ? `（${s.pref}）` : '') : p.venue ? p.venue + (p.pref ? `（${p.pref}）` : '') : '';
    if (!sid && !credits.length) continue;
    // 公式サイト（公演の欄の URL）。無ければ公演の情報を取ったページ（stage.corich.jp。stage_id はその番号）
    const url = /^https?:\/\//.test(s.url || '') ? s.url : '';
    const page = !url && /^\d+$/.test(sid) ? `https://stage.corich.jp/stage/${sid}` : '';
    out[w.work_key] = {grp: s.group || p.grp || '', venue, synopsis, credits, url, page};
  }
  return out;
}

/**
 * The block recRow puts in place of the plain あらすじ・出演 lines. Without the screen's script it reads as
 * those lines (the same .cast / .syn classes); app.js turns it into the recommend card's lead box.
 */
export function rinfoHtml(info, venue, times) {
  const cast = info.credits.length ? `<div class="cast">${info.credits.map(([r, ns]) =>
    `<div class="cr"><span class="cl">${E(r)}</span><span class="cv">${ns.map(E).join('、')}</span></div>`).join('')}</div>` : '';
  const syn = info.synopsis ? `<div class="syn"><p class="txt">${E(info.synopsis)}</p>`
    + '<button class="mrb" data-more="1">続きを読む</button></div>' : '';
  return `<div class="rinfo" data-grp="${E(info.grp)}" data-venue="${E(venue || info.venue)}" data-times="${E(times)}"`
    + (info.url ? ` data-url="${E(info.url)}"` : info.page ? ` data-page="${E(info.page)}"` : '') + '>'
    + `${cast}${syn}<!--/rinfo--></div>`;
}
