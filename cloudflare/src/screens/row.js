// One record row of the 評価/日記帳 screens and the pieces it is made of.
// Ports of tools/taguri/app.py (_rec_row, _impression_parts, _stamp,
// _date_parts, _venue_of, _edit_html, _hand_html, stage_label), charts._anchor
// and icons.ico/h2. Each returns exactly the Python HTML.
import {pastStages} from './autolink.js';
import {E, WS, strip, cmp} from './py.js';
import {handCreditCount} from './credits.js';

// ---------------------------------------------------------------- icons.py
const ICONS = {
  star: 'M12 3.8l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM16.2 16.2 21 21',
  check: 'M4.5 12.5 9.5 18 20 6',
};
/** icons.ico */
export function ico(name, size = 16, cls = '') {
  const d = ICONS[name];
  if (!d) throw new Error(`icon ${name} not ported`);
  return `<svg class="ico ${cls}" viewBox="0 0 24 24" width="${size}" height="${size}"`
    + ` fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"`
    + ` stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
}
/** icons.h2 */
export const h2 = (name, text, extra = '') => `<h2>${ico(name, 18)}<span>${text}</span>${extra}</h2>`;

import {anchor} from './anchor.js';
export {anchor};

// ---------------------------------------------------------------- dates, venue, stamp
const WEEK = '月火水木金土日';
/** app._date_parts: (年, 月.日, 曜日), or empty when date.fromisoformat fails. */
export function dateParts(iso) {
  const m = Array.from(iso || '').slice(0, 10).join('').match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return ['', '', ''];
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const dim = [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (y < 1 || mo < 1 || mo > 12 || d < 1 || d > dim[mo - 1]) return ['', '', ''];
  const dt = new Date(0);
  dt.setUTCFullYear(y, mo - 1, d);
  return [String(y), `${mo}.${String(d).padStart(2, '0')}`, WEEK[(dt.getUTCDay() + 6) % 7]];
}

/** app._venue_of (a manual record has no shows, so only its own venue). */
export function venueOf(w) {
  if (strip(w.venue || '')) return strip(w.venue);
  const seen = new Set(), out = [];
  for (const sh of w.shows || []) {
    const v = strip((sh.fixed || {}).venue || sh.venue || '');
    if (v && !seen.has(v)) { seen.add(v); out.push(v); }
  }
  if (!out.length) return '';
  return out.length === 1 ? out[0] : `${out[0]} ほか ${out.length - 1} 会場`;
}
const VENUE_WS = new RegExp(`[${WS}　]+`, 'gu');
/** app._venue_key */
export function venueKey(w) {
  const v = venueOf(w);
  return v ? v.replace(VENUE_WS, '') : 'none';
}

/** app._stamp */
export function stamp(w, v) {
  let sum = 0;
  for (const b of new TextEncoder().encode(w.work_key)) sum += b;
  const rot = (sum % 13) - 6;
  if (!v) {
    return `<span class="stamp none" data-stamp="1" style="--rot:${rot}deg"`
      + ` aria-label="評価はまだ付いていません"></span>`;
  }
  const hold = Array.from(v).length > 1;
  return `<span class="stamp${hold ? ' hold' : ''}" data-stamp="1"`
    + ` style="--rot:${rot}deg">${E(v)}</span>`;
}

// ---------------------------------------------------------------- impression
/** app._impression_parts: [head for the tools line, box under it]. */
export function impressionParts(w) {
  const key = E(w.work_key);
  const note = strip(w.note_impression || '');
  const box = `<div class="inote" hidden><textarea data-note="${key}" rows="2"`
    + ` placeholder="どう感じましたか（任意です。書かなくても記録は残ります）"`
    + `>${E(note)}</textarea><span class="said"></span></div>`;
  if (note) {
    return ['', `<div class="inw"><div class="inr"><span class="inl">感想</span>`
      + `<span class="int">${E(note)}</span>`
      + `<button class="wnb" data-note-open="1">書き直す</button></div>`
      + `${box}</div>`];
  }
  return ['<button class="wnb" data-note-open="1">感想を書く'
    + '<span class="opt">任意</span></button>',
  `<div class="inw">${box}</div>`];
}

/** app._synopsis_html */
function synopsisHtml(text) {
  text = strip(text || '');
  if (!text) return '';
  return `<div class="syn"><p class="txt">${E(text)}</p>`
    + `<button class="mrb" data-more="1">続きを読む</button></div>`;
}

/** render_recommend.CAST_SHOWN */
const CAST_SHOWN = 12;
/** app._cast_html: people is a list of [role, person]. */
function castHtml(people) {
  if (!people || !people.length) return '';
  const cast = [...new Set(people.filter(([r]) => r === '出演').map(([, n]) => n))].sort(cmp);
  const others = {};
  for (const [r, n] of people) if (r === '演出' || r === '脚本') (others[r] ||= []).push(n);
  if (!cast.length && !Object.keys(others).length) return '';
  const rows = [];
  if (cast.length) {
    const head = cast.slice(0, CAST_SHOWN).map(E).join('、');
    const rest = cast.slice(CAST_SHOWN);
    const more = rest.length ? `<span class="rest">、${rest.map(E).join('、')}</span>`
      + `<button class="mrb" data-more="1">ほか ${rest.length} 名を見る</button>` : '';
    rows.push(`<div class="cr"><span class="cl">出演</span><span class="cv">${head}${more}</span></div>`);
  }
  for (const role of ['演出', '脚本']) {
    const ns = [...new Set(others[role] || [])].sort(cmp);
    if (ns.length) rows.push(`<div class="cr"><span class="cl">${E(role)}</span><span class="cv">${ns.map(E).join('、')}</span></div>`);
  }
  return `<div class="cast">${rows.join('')}</div>`;
}

// ---------------------------------------------------------------- the row
/**
 * app._rec_row. Options as in Python (poster, rate_always, editable,
 * rate_reopen, id_suffix); `label` is stage_label(w.stage_id) for the edit box.
 * w.synopsis and w.people (measure_nets.load_rated) are shown when present.
 * `extra` (the search screen) and the per-visit note (only for rows opened
 * from mails, which a public user does not have) are not passed yet.
 */
export function recRow(w, {poster = '', rateAlways = false, editable = false, rateReopen = false, label = '', idSuffix = '', extra = ''} = {}) {
  const v = w.verdict || '';
  const unseen = Boolean(w.unseen);
  let rate;
  if (unseen) {
    rate = `<span class="rb notseen" data-work="${E(w.work_key)}">`
      + `<b class="nsm">行かなかった</b>`
      + `<button data-seen="${E(w.work_key)}">やはり観た</button>`
      + `<span class="said"></span></span>`;
  } else {
    const btns = '<span class="rb" data-work="' + E(w.work_key) + '"'
      + ((!v || rateAlways) ? '' : ' hidden')
      + '>'
      + ['◎', '○', '△', '×'].map(g => `<button data-v="${g}">${g}</button>`).join('')
      + '<span class="said"></span></span>';
    rate = (!v || rateAlways) ? btns
      : rateReopen ? '<button class="wnb" data-rate-open="1">評価を押し直す</button>' + btns : '';
  }
  let times = '';
  if (!unseen) {
    const n = w.times || 1;
    if (w.skipped) times = `${n} 回観た（あと ${w.skipped} 回は行かなかった）`;
    else if (n > 1) times = `${n} 回観た`;
  }
  const where = [venueOf(w), times].filter(x => x).map(x => `<span>${E(x)}</span>`).join(' ');
  const [impHead, impBox] = impressionParts(w);
  const [y, md, wd] = dateParts(w.first_date || '');
  const dt = md
    ? `<span class="dt"><span class="y">${y}</span><span class="md">${md}</span><span class="wd">${wd}</span></span>`
    : '<span class="dt no">上演日が<br>分かりません</span>';
  const pin = poster ? `<span class="pin">${poster}</span>`
    : '<span class="pin"><span class="noposter" aria-hidden="true"></span></span>';
  return `<article class="rec-row${w.suspect ? ' check' : ''}`
    + `${unseen ? ' skipped' : ''}"`
    + ` id="w-${E(anchor(w.work_key))}${E(idSuffix)}"`
    // 評価の「詳細」（気になった所・良かった所。app.js の aspectsPanel が読む）
    + ` data-aspects="${E(w.aspects || '')}">`
    + `<span class="marg">${dt}${unseen ? '' : stamp(w, v)}</span>`
    + `<div class="page">`
    + `<div class="ttl">${E(w.title)}</div>`
    + (where ? `<div class="where">${where}</div>` : '')
    + synopsisHtml(w.synopsis)
    + castHtml(w.people)
    + extra                         // 探す画面の「ヒットした箇所」（題名のすぐ下）
    + ((rate || impHead) ? `<div class="tools">${rate}${impHead}</div>` : '')
    + impBox
    + (editable ? editHtml(w, label) : '')
    + `</div>${pin}</article>`;
}

// ---------------------------------------------------------------- edit box
/** app.HAND_FIELDS */
const HAND_FIELDS = [
  ['出演', '出演者', '1 行に 1 名でも、読点や中黒で区切っても構いません'],
  ['演出', '演出', ''],
  ['脚本', '脚本・原作・翻訳', ''],
  ['スタッフ', 'そのほかの作り手', '「美術：〇〇」のように役職を添えると、役職ごとに数えられます。役職が分からないものは名前だけで構いません'],
];

/** app._hand_html */
function handHtml(w, key) {
  const hand = w.hand || {};
  const hf = hand.fields || {};
  const n = handCreditCount(hf);
  const boxes = HAND_FIELDS.map(([field, label, hint]) =>
    `<label class="hand-f">${E(label)}`
    + (hint ? `<span class="hand-h">${E(hint)}</span>` : '')
    + `<textarea data-hand="${E(field)}" rows="${field === 'スタッフ' ? 3 : 2}"`
    + ` placeholder="">${E(hf[field] || '')}</textarea></label>`).join('');
  // サービス版では、ポスターは手で入れられない（公演の画像は全員で共有する。/api/hand_poster は
  // 移していない）ので、出演者・作り手だけを入れる欄にした（2026-10-14）
  return `<details class="hand" data-work="${key}">
<summary>出演者・作り手を手で入れる${n ? `（${n} 名を入れてあります）` : ''}</summary>
<p class="ed-lead"><b>観た公演が見つからないときは、ここに出演者や作り手を書けます。</b>
書いた名前は、おすすめを作るときに使います。観た公演の情報から取れている分は消えず、ここに書いた分が足されます。</p>
${boxes}
<div class="pfoot"><button data-hand-save="${key}">この内容で保存する</button>
 <span class="said"></span></div>
</details>`;
}

/**
 * app._edit_html for a manual record (no shows: purchase-derived rows never
 * exist for public users). Posters: app.poster_of reads image files under
 * data/review/img and the owner's credits.jsonl; the Worker has neither, so a
 * record never has a poster here (as in Python with no image files).
 */
export function editHtml(w, label) {
  // サービス版（Worker）だけの編集欄（起案者の指摘 2026-10-14「公演詳細を編集するところがわかりにくい。
  // おすすめに出る公演と結びつけるとか概念がよくわかんない。『メール本文を見る』ってメール文書を手元に
  // 保存してる？」）。Python の持ち主版にあるメールの機能（抽出結果に戻す・メールの中身を見る）は、
  // サービス版ではメールを保存しないので出さない。言葉は「観た公演の情報とつながる」に寄せた。
  // test/screens.test.js はこの欄を Python との一字一句の比べから外し、ここの形を別に確かめる。
  const key = E(w.work_key);
  const rows = `<div class="ed-show"><span class="ed-lk">観た日・劇場</span><input type="date" data-ed-date="" `
    + `value="${E(w.first_date || '')}">`
    + `<input type="time" data-ed-time="" value="${E(w.time || '')}"`
    + ` aria-label="開演時刻">`
    + `<input type="text" data-ed-venue="" value="${E(w.venue || '')}"`
    + ` placeholder="劇場" size="18"></div>`;
  const mg = w.merged || [];
  const merged = mg.length ? `<button data-unmerge="${key}">まとめた ${mg.length} 件を戻す</button>` : '';
  const skipLead = w.unseen
    ? '<b>この記録には「行かなかった」が付いています。</b>観た本数と図、評価待ちからは外れています。この行の上にある「やはり観た」で戻せます。<br>'
    : '';
  const mgNote = !mg.length ? '' : '<p class="ed-lead">この記録には、同じ公演としてまとめた次の記録が入っています：'
    + mg.slice(0, 4).map(m => `「${E(m.title)}」`).join('、')
    + (mg.length > 4 ? ` ほか ${mg.length - 4} 件` : '') + '。</p>';
  const sid = w.stage_id || '';
  let linkNote;
  if (sid && w.auto_linked) {
    linkNote = '<b>題名と観た日から、観た公演を見つけてつなげました。</b>出演者やあらすじは、この公演のものを使っています。ちがう公演だったら「つながりを外す」を押して、探し直してください。';
  } else if (sid) {
    linkNote = '観た公演の出演者・作り手・あらすじを使っています。おすすめにも、この情報が生きます。';
  } else if (handCreditCount((w.hand || {}).fields || {})) {
    linkNote = '観た公演はまだ見つかっていませんが、下に手で入れた出演者・作り手を使っています。公演が見つかったら、上の欄で選ぶとあらすじも入ります。';
  } else {
    linkNote = '<b>まだ観た公演の情報が見つかっていません。</b>上の欄で題名を探して選ぶと、出演者やあらすじが入り、おすすめにも使えるようになります。見つからないときは、下の「出演者・作り手を手で入れる」から入れられます。';
  }
  const link = `<div class="ed-link" data-work="${key}">`
    + `<span class="ed-lk">観た公演</span>`
    + (sid ? `<span class="ed-lv${w.auto_linked ? ' auto' : ''}">`
      + `${E(label)}</span>`
      + `<button data-unlink="${key}">つながりを外す</button>` : '')
    + `<input type="text" data-lk-q="${key}" size="24" autocomplete="off"`
    + ` value="${E(w.title)}"`
    + ` placeholder="${sid ? 'ほかの公演を探す' : '公演の題名で探す'}">`
    + `<button data-lk-web="${key}">${ico('search')}公演一覧から探す</button>`
    + `<span class="said"></span><div class="lk-sug"></div>`
    + '</div>';
  const pnote = sid
    ? '観た公演のポスターは、まだ手元にありません（公演の情報を取得するときに、一緒に保存します）。'
    : 'ポスターはまだありません。上の欄で観た公演を選ぶと、その公演のポスターが出ます。';
  const posterRow = `<div class="ed-pos"><span class="ed-lk">ポスター</span>`
    + `<span class="ed-pv"><span class="ed-pn"></span></span>`
    + `<span class="ed-m">${pnote}</span></div>`;
  const handBox = handHtml(w, key);
  return `<details class="editor" data-work="${key}">
<summary>記録を直す${mg.length ? `・まとめた ${mg.length} 件` : ''}</summary>
${mgNote}
<p class="ed-lead">題名・観た日・劇場をまちがえて入れたときは、ここで直せます。
<b>観た公演の情報（出演者やあらすじ）とつながっていると、おすすめに使えます。</b></p>
<label class="ed-t">題名
 <input type="text" data-ed-title="${key}" value="${E(w.title)}" size="44"></label>
${rows}
${link}
<p class="ed-lead">${linkNote}</p>
${posterRow}
${handBox}
<div class="ed-btns"><button data-fix="${key}">この内容で保存する</button>
 ${merged}<button class="danger" data-drop="${key}">この記録を取り消す</button>
 <span class="said"></span></div>
<p class="ed-lead">${skipLead}
<b>「この記録を取り消す」は、まちがえて入れた記録を外すときに使います。</b>
取り消した記録は、「設定」の「取り消した記録」から <b>30 日のあいだ</b>戻せます。30 日たつと自動で消えます。</p>
<!--/editor--></details>`;
}

/**
 * app.stage_label for the given stage ids: "題名／劇場／日付" from the public
 * catalogue (the stage_label table, built by scripts/build_stage_labels.py).
 */
export async function stageLabels(ctx, sids) {
  const want = [...new Set(sids.filter(Boolean))];
  const out = {}, got = {};
  // D1 binds at most 100 parameters per statement.
  for (let i = 0; i < want.length; i += 90) {
    const part = want.slice(i, i + 90);
    const {results} = await ctx.db.prepare(
      `SELECT stage_id, label FROM stage_label WHERE ver=(SELECT v FROM rec_meta WHERE k='stage_label')`
      + ` AND stage_id IN (${part.map(() => '?').join(',')})`).bind(...part).all();
    for (const r of results) got[r.stage_id] = r.label;
  }
  // Past stages (past_stage) are labelled the same way: 題名／劇場／初日.
  const past = await pastStages(ctx.db, want.filter(s => !got[s]));
  for (const [sid, p] of Object.entries(past)) got[sid] = [p.title, p.venue, p.start].filter(Boolean).join('／');
  for (const sid of want) out[sid] = got[sid] || `公演 ${sid}（手元のデータに見当たりません）`;
  return out;
}
