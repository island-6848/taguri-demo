// The recommendation cards rendered by the daily batch (scripts/build_cards.py,
// render_recommend.ticket), filled for one user and one list. `compose` is
// build_cards.compose; test/cards.test.js checks it against the Python output for
// every list (recommend / interest / favourite / owned).
import {E} from './py.js';
import {loadOverrides, applySynopsis, applyPrice, fillCatalogueSynopsis} from './override.js';

const ICONS = {check: 'M4.5 12.5 9.5 18 20 6', plus: 'M12 5v14M5 12h14', eye: 'M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z',
  inbox: 'M3 12h5l1.5 2.5h5L16 12h5M3 12l3-7h12l3 7v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z'};
const ico = (name, size) => `<svg class="ico " viewBox="0 0 24 24" width="${size}" height="${size}" fill="none"`
  + ` stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">`
  + `<path d="${ICONS[name]}"/></svg>`;
export const NO_REASON = '<li class="rs none">理由を出せていません</li>';

/** render_recommend.buttons */
/** 答えた公演は、どの画面でも「回答を直す」1 つにし、押すと三択が開く（起案者の指示 2026-10-14）。 */
export const changeAnswer = sid => '<button class="wnb" data-btns-open="1">回答を直す</button>' + buttons(sid, true);
// 回答（起案者の指示 2026-10-17「興味あり、興味なし、購入済、行けないの 4 択にして」→「行けない、のボタンは
// おすすめページには出さないで。興味あり、のページにつけて」）。行けない＝気にはなるが行けない: おすすめから外し、
// 興味ありの一覧には入れず、好みの手がかり（興味ありと同じ向き）には使う。
// おすすめ・探す・開幕リマインドは 興味あり・興味なし・購入済 の 3 つ。興味ありの一覧は、押してある「興味あり」を
// 除いた 興味なし・購入済・行けない の 3 つを、畳まずにそのまま出す
const LABEL = {interest: '興味あり', nointerest: '興味なし', owned: '購入済', cantgo: '行けない'};
const band = (sid, values, hidden = false) => `<span class="btns"${hidden ? ' hidden' : ''} data-stage="${E(sid)}">`
  + values.map(v => `<button data-v="${v}">${LABEL[v]}</button>`).join('') + '<span class="said"></span></span>';
export const buttons = (sid, hidden = false) => band(sid, ['interest', 'nointerest', 'owned'], hidden);
// 「なぜ気になったか」は、これまで「回答を直す」と一緒に開いていた（起案者 2026-10-15）。その押し口を、名前を変えて残す
export const interestButtons = sid => '<button class="wnb" data-btns-open="1">なぜ気になったか</button>' + band(sid, ['nointerest', 'owned', 'cantgo']);
/** お気に入り: 購入済みにするボタンだけ（起案者の指示 2026-10-15「お気に入りから、購入済みを登録できるようにして」）。 */
export const ownedButton = sid => `<span class="btns" data-stage="${E(sid)}">`
  + '<button data-v="owned">購入済みにする</button><span class="said"></span></span>';
/** お気に入り: 購入済みにした公演は一覧に残し、ボタンの代わりに印を出す（起案者の指示 2026-10-15「購入済み押してもお気に入りから消さないで」）。 */
export const ownedMark = '<span class="owned-mark">購入済みです。<a href="/tickets?t=__TAGURI_TOKEN__">購入済み公演で行く日を入れる</a></span>';

/** render_recommend.why_note */
export function whyNote(sid, note = '', {open = false, ask = false} = {}) {
  const box = `<div class="why-note" data-stage="${E(sid)}"${open ? '' : ' hidden'}>`
    + '<label>なぜ気になったか<span class="opt">任意</span></label>'
    + `<textarea placeholder="例: 作り手30の脚本だから／作品4に興味がある／題材が題材3そう" rows="2">${E(note)}</textarea>`
    + '<div class="wn-foot"><span class="hint">書いた文にある名前は、「お気に入り」に登録する候補として出てきます</span>'
    + '<span class="said"></span></div></div>';
  if (open || !ask) return box;
  const head = note
    ? `<div class="wnr"><span class="wnl">なぜ気になったか</span><span class="wnt">${E(note)}</span><button class="wnb" data-why="1">書き直す</button></div>`
    : '<button class="wnb" data-why="1">なぜ気になったかを書く<span class="opt">任意</span></button>';
  // ふだんは畳み、「回答を直す」で三択と一緒に出す（起案者の指示 2026-10-15「なぜ気になったか？の理由ユーザーに
  // 向けて出す必要ある？…回答を直すのボタンを押したら出るように」。render_recommend.why_note と同じ）
  return `<div class="wnw" hidden>${head}${box}</div>`;
}

/** 購入済み公演: a memo before seeing it (起案者の指示 2026-10-14「購入済みの公演のみ、観る前の感想をメモで書いておけるように」). */
export function preNote(sid, note = '') {
  const has = Boolean(String(note || '').trim());
  const summary = has ? `観る前のメモ<span class="nnv">${E(note)}</span>` : '観る前のメモを書く<span class="opt">任意</span>';
  return `<details class="nn pre" data-stage="${E(sid)}"><summary>${summary}</summary>`
    + `<textarea data-prenote="${E(sid)}" rows="3" placeholder="例: 原作を読んで楽しみにしている／あの役者の新しい一面が見られそう">${E(note)}</textarea>`
    + '<div class="wn-foot"><span class="hint">自分だけのメモです。観たあと、評価を付けるときの手がかりになります</span>'
    + '<span class="said"></span></div></details>';
}

/** render_recommend.no_note */
export function noNote(sid, note = '', hidden = false) {
  const has = Boolean(String(note || '').trim());
  const summary = has ? `見送った理由<span class="nnv">${E(note)}</span>` : '見送った理由を書く<span class="opt">任意</span>';
  return `<details class="nn" data-stage="${E(sid)}"${hidden ? ' hidden' : ''}><summary>${summary}</summary>`
    + `<textarea data-nono="${E(sid)}" rows="2" placeholder="例: 日程が合わない／会場が遠い／予算が合わない／この題材は好みではない">${E(note)}</textarea>`
    + '<div class="wn-foot"><span class="hint">この一覧は消さずに残してあります。理由を書いておくと、あとで「観ればよかった」を拾い直すときに、都合で見送ったものと好みに合わなかったものを見分けられます</span>'
    + '<span class="said"></span></div></details>';
}

/** build_cards.mytix_html: the 行く日 box of an owned stage. `start`/`end` are YYYY-MM-DD. */
export function mytixHtml(sid, start, end, tickets) {
  const rows = tickets.map(t => {
    const tm = t.time ? ` ${E(t.time)}` : '';
    const s = E(String(t.sid || sid)), dd = E(t.date), tt = E(t.time || '');
    const [note, btns] = t.confirmed
      ? ['', `<button data-mt-del="${s}" data-date="${dd}" data-time="${tt}">取り消す</button>`]
      : ['（未確定）', `<button data-mt-ok="${s}" data-date="${dd}" data-time="${tt}">確定する</button>`
        + `<button data-mt-del="${s}" data-date="${dd}" data-time="${tt}">違う</button>`];
    return `<span class="mt-row${t.confirmed ? '' : ' un'}">${Number(t.date.slice(5, 7))}月${Number(t.date.slice(8, 10))}日${tm}${note} ${btns}</span>`;
  }).join('');
  const add = '<span class="mt-add"><input type="date" class="mt-d" aria-label="行く日"'
    + (start ? ` min="${start}"` : '') + (end ? ` max="${end}"` : '') + '>'
    + '<input type="time" class="mt-t" aria-label="時刻（任意）">'
    + `<button data-mt-add="${E(sid)}">${ico('plus', 13)}行く日を追加</button><span class="said"></span></span>`;
  return `<div class="mytix"><b>行く日</b>${rows}${add}</div>`;
}

export const posterHtml = file => `<span class="pwrap"><img class="poster" src="/img/${E(file)}?t=__TAGURI_TOKEN__"`
  + ` alt="" loading="lazy" onload="this.parentElement.classList.add('ld')"`
  + ` onerror="this.parentElement.classList.add('pe');this.nextElementSibling.textContent='読み込めませんでした'">`
  + `<span class="pmsg">読み込み中…</span></span>`;

/** build_cards.compose */
export function compose(template, sid, mode, {rank = null, why = '', poster = '', note = '', mytix = '', top = '', owned = false, origin = '', tags = null} = {}) {
  const mark = {recommend: rank ? `<span class="sn">No.${String(rank).padStart(2, '0')}</span>` : '',
    interest: `<span class="sn done">${ico('check', 15)}</span>`,
    favourite: '<span class="wax" aria-hidden="true"></span>'}[mode] || '';
  const btns = {recommend: buttons(sid),
    interest: interestButtons(sid), owned: changeAnswer(sid), favourite: owned ? ownedMark : ownedButton(sid)}[mode] || '';
  const answer = mode === 'recommend' || mode === 'interest';
  // Functions as replacements: the inserted text is never read as a replacement pattern ($&).
  return template.replace('<article class="ticket recommend"', () => `<article class="ticket ${mode}"`)
    .replace('<!--mark-->', () => mark)
    .replace('<!--whyh-->', () => (mode === 'favourite' ? 'なぜお知らせしているか' : 'おすすめ理由'))
    .replace('<!--why-->', () => why || NO_REASON)
    .replace('<!--poster-->', () => poster)
    .replace('<!--btns-->', () => btns)
    .replace('<!--mytix-->', () => (mode === 'owned' ? mytix : ''))
    .replace('<!--why_note-->', () => (answer ? whyNote(sid, note, {ask: mode === 'interest'}) : ''))
    .replace('<!--no_note-->', () => (answer ? noNote(sid, '', true) : ''))
    .replace('<div class="act"></div>', '').replace('<div class="pcol"></div>', '')
    // 探す: what the words hit, above the card, in place of the reasons (ticket's why_html).
    .replace('</h3>\n \n <div class="meta">', () => (top ? `</h3>\n <div class="whyh top">${ico('eye', 14)}ヒットした箇所：</div><ul class="why top">${top}</ul>\n <div class="meta">` : '</h3>\n \n <div class="meta">'))
    .replace(`<div class="whyh">${ico('eye', 14)}おすすめ理由</div><ul class="why">${why || NO_REASON}</ul>`, () => (top ? '' : `<div class="whyh">${ico('eye', 14)}おすすめ理由</div><ul class="why">${why || NO_REASON}</ul>`))
    // おすすめ以外の画面で足した興味ありは、理由の欄の代わりに足した場所だけを書く
    .replace(origin ? /<div class="whyh">[\s\S]*?<\/ul>/ : /(?!)/, () => `<div class="whyh origin">${ico('inbox', 14)}${E(origin)}</div>`)
    // お気に入り: 「なぜお知らせしているか」の欄の代わりに、当たった名前をハッシュタグで並べる
    // （起案者の指示 2026-10-15「「なぜお知らせしているか」の欄消して…お気に入りって丸で囲んであるところの色で、
    // 理由の人名とか団体とかだけハッシュタグで羅列して」）
    // 購入済み公演: おすすめ理由の欄は出さない（起案者の指示 2026-10-15「購入済み公演のおすすめ理由の欄も消して」）
    .replace(mode === 'owned' ? /<div class="whyh">[\s\S]*?<\/ul>/ : /(?!)/, '')
    .replace(tags ? /<div class="whyh">[\s\S]*?<\/ul>/ : /(?!)/, () => `<div class="favtags">${(tags || []).map(t => `<a class="ftag" href="/recommend/favourites?t=__TAGURI_TOKEN__&amp;n=${encodeURIComponent(t)}">#${E(t)}</a>`).join('')}</div>`);
}

/** Card templates and posters of these stages: Map(sid -> html), Map(sid -> file). */
export async function cardTemplates(db, sids) {
  const html = new Map(), posters = new Map();
  const want = [...new Set(sids.filter(Boolean))];
  for (let i = 0; i < want.length; i += 90) {
    const part = want.slice(i, i + 90), qs = part.map(() => '?').join(',');
    const [cards, pics] = await Promise.all([
      db.prepare(`SELECT stage_id,html FROM rec_card WHERE ver=(SELECT v FROM rec_meta WHERE k='rec_card') AND stage_id IN (${qs})`).bind(...part).all(),
      db.prepare(`SELECT stage_id,file FROM poster WHERE stage_id IN (${qs})`).bind(...part).all()]);
    for (const r of cards.results) html.set(r.stage_id, r.html);
    for (const r of pics.results) posters.set(r.stage_id, r.file);
  }
  // 管理者が手で入れたあらすじ・題材を重ねる（migration 0028、tools/admin）
  const overrides = await loadOverrides(db, [...html.keys()]);
  for (const [sid, ov] of overrides) html.set(sid, applyPrice(applySynopsis(html.get(sid), sid, ov), ov));
  // カードが古くて、あとから読み取ったあらすじが入っていない公演は、公演一覧の本文で埋める
  await fillCatalogueSynopsis(db, html, overrides);
  return {html, posters};
}
