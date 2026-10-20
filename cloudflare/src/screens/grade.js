// 評価の段階。本人が設定で選ぶ（図形か星か）。
//
// 起案者の指示（2026-10-14）は次の 3 つ。
// - 「星5段階を初期設定にして。言葉の案は逆に決めないほうがいいんじゃない？勝手に個人が思ってる尺度で
//   つけていっても、位置zに直すんだよね」(docs/knowledge: dec-star-default)
// - 「オーソドックスなのだけ実用化してほしい。2段階（単純に○×）、3段階（○×△）、と11段階（星0.5きざみ）。
//   星にするか図形にするかは自分で選べるようにして」(dec-rating-scales)
// 推薦は評価を本人の中での位置に直して使う（recommend.gradeOf / personValues、段階ごとに別々）。そのため段階が
// 人ごとに違っても、途中で変えても成り立ち、段階に言葉は添えない。
//
// 選べる段階（保存の形）は次の 5 つ。
//   図形: marks2 ○×（"2/2" "1/2"）、marks3 ○△×（"3/3" "2/3" "1/3"）、marks4 ◎○△×（"◎" など。前からの形）
//   星:   stars5 ★1〜★5（"n/5"）、stars11 ★0〜★5 の 0.5 きざみ（"n/11"、★ = (n−1)/2）
// 付けた評価は付けたときの段階のまま残り、表示もその段階で出す（段階を変えても書き換えない）。
// 設定が無ければ、◎○△× で付けたことのある人は marks4、ほかは stars5。
// 色・並び・「最上位」の判定は、段階の中での位置 f（最低 0〜最高 1）で決める。

import {ValueError} from './py.js';

export const MARKS = ['◎', '○', '△', '×'];
export const SCALES = ['marks2', 'marks3', 'marks4', 'stars5', 'stars11'];
export const SCALE_LABEL = {marks2: '○×（2 段階）', marks3: '○△×（3 段階）', marks4: '◎○△×（4 段階）',
  stars5: '★（5 段階）', stars11: '★ 0.5 きざみ（11 段階）'};
const MARK_F = {'◎': 1, '○': 2 / 3, '△': 1 / 3, '×': 0};
const SHAPE = {2: {2: '○', 1: '×'}, 3: {3: '○', 2: '△', 1: '×'}};
const SCALED = /^(\d{1,2})\/(2|3|5|11)$/;

/** [n, L] of a saved "n/L" on a scale this screen offers (2, 3, 5, 11), else null. */
export function parts(v) {
  const m = SCALED.exec(String(v ?? ''));
  if (!m) return null;
  const n = Number(m[1]), L = Number(m[2]);
  return n >= 1 && n <= L ? [n, L] : null;
}
/** A saved "n/L" rating (not ◎○△×). */
export const isScaled = v => parts(v) !== null;
/** A star rating ("n/5" or "n/11"). */
export const isStar = v => { const p = parts(v); return Boolean(p) && (p[1] === 5 || p[1] === 11); };
/** Place within its scale: 0 (lowest) .. 1 (highest), or null for no rating. */
export function frac(v) {
  if (Object.hasOwn(MARK_F, v)) return MARK_F[v];
  const p = parts(v);
  return p ? (p[0] - 1) / (p[1] - 1) : null;
}
const starsOf = (n, L) => (L === 11 ? (n - 1) / 2 : n);
/**
 * 同じ星の数を 1 つの値にそろえる（★ 5 段階の "n/5" を、0.5 きざみの "(2n+1)/11" に）。尺度を途中で変えると、同じ ★5 が
 * "5/5" と "11/11" の 2 通りで残り、評価一覧のタブと分布が 2 つに割れていた（起案者の指摘 2026-10-20「星５がタブ２個に分かれて
 * 表示されてる」）。◎○△× と記号の段階はそのまま
 */
export function sameGrade(v) {
  const p = parts(v);
  return p && p[1] === 5 ? `${2 * p[0] + 1}/11` : v;
}
/** What a saved rating shows as: ◎ / ○ / ★4 / ★3.5. */
export function gradeText(v) {
  const p = parts(v);
  if (!p) return String(v ?? '');
  const [n, L] = p;
  return SHAPE[L] ? SHAPE[L][n] : '★' + starsOf(n, L);
}
/** The side of a rating as a mark (for colours): top ◎, above the middle ○, below △, bottom ×, middle ''. */
export function markOf(v) {
  if (Object.hasOwn(MARK_F, v)) return v;
  const f = frac(v);
  if (f === null) return String(v ?? '');
  return f === 1 ? '◎' : f === 0 ? '×' : f > 0.5 ? '○' : f < 0.5 ? '△' : '';
}
/** The top of its scale (◎, ○ of ○×/○△×, ★5). */
export const isTop = v => frac(v) === 1;

/** Every grade, best first within each scale (the order the rate screen lists them in). */
export const ALL_GRADES = [...MARKS,
  ...[5, 4, 3, 2, 1].map(n => `${n}/5`), ...Array.from({length: 11}, (_, i) => `${11 - i}/11`),
  '3/3', '2/3', '1/3', '2/2', '1/2'];

/** The user's scale: the saved setting, else marks4 if they have rated with ◎○△×, else stars5. Cached on ctx. */
export async function scaleOf(ctx) {
  if (ctx._scale) return ctx._scale;
  const set = await ctx.db.prepare("SELECT value FROM app_setting WHERE user_id=? AND key='rating_scale'").bind(ctx.uid).first();
  if (set && SCALES.includes(set.value)) return (ctx._scale = set.value);
  const row = await ctx.db.prepare(`SELECT 1 AS x FROM works WHERE user_id=? AND verdict IN ('◎','○','△','×') LIMIT 1`).bind(ctx.uid).first();
  return (ctx._scale = row ? 'marks4' : 'stars5');
}

/**
 * The rating buttons for a scale. Shapes are round buttons (as ◎○△× always were). Stars are a row of ☆
 * filled up to the rating (起案者 2026-10-14「☆☆☆☆☆みたいなの表示されてて、自分が思ってる評価のとこ押したら
 * そこまで星の色がつく」): stars5 has one button per star; stars11 a 0 button and two halves per star
 * (left = .5, right = whole), the star filled half or whole (.h / .on). app.js fills at once on a press.
 */
/** 前の「評価しない」の値（rate.VERDICTS の「まだ判断できない」。評価には数えない）。押し口はやめたが、付けた記録はそのまま読む */
export const HOLD = 'まだ判断できない';
/**
 * 星の右端の ✕: 押すと評価を消して未評価に戻す（POST /api/rate {work_key, clear: true}）。起案者の指示 2026-10-18
 * 「『評価しない』のボタンじゃなくて、星の右端に✕ボタンをつけることでnullにできるようにして」（dec-star-clear-x）。
 * 評価が付いているときだけ出す（hidden を app.js の fillStars が外す・付ける）: 付いていない行で押しても何も起きない
 * 押し口が並ぶと「押すと何かが消える」と迷わせ、未評価の一覧では全部の行に ✕ が並んでしまう。✕ は星の後ろ（★n の右）なので、
 * 出たり消えたりしても星の位置は動かない。前の「評価しない」（まだ判断できない）を付けた行にも出し、押せば未評価に戻せる
 */
export const clearButton = current => `<button type="button" class="gclr" data-clear="1" aria-label="評価を消す（未評価に戻す）" title="評価を消す"${current ? '' : ' hidden'}>✕</button>`;
export function gradeButtons(scale, current = '') {
  const btn = (v, text) => `<button data-v="${v}">${text}</button>`;
  if (scale === 'marks2') return btn('2/2', '○') + btn('1/2', '×');
  if (scale === 'marks3') return btn('3/3', '○') + btn('2/3', '△') + btn('1/3', '×');
  // 星のあとに ✕（評価を消す）。星 0 の押し口はやめた（起案者の指示 2026-10-16「星0は不要」）。前に付けた 1/11（★0）はそのまま読める
  const none = clearButton(current);
  if (scale === 'stars5') {
    const now = parts(current)?.[1] === 5 ? parts(current)[0] : 0;
    return [1, 2, 3, 4, 5].map(n => `<button class="star${n <= now ? ' on' : ''}" data-v="${n}/5" aria-label="星 ${n}"></button>`).join('') + none;
  }
  if (scale === 'stars11') {
    const now = parts(current)?.[1] === 11 ? (parts(current)[0] - 1) / 2 : -1;
    return [1, 2, 3, 4, 5].map(k => `<span class="hs${now >= k ? ' on' : now === k - 0.5 ? ' h' : ''}">`
        + `<button class="half l" data-v="${2 * k}/11" aria-label="星 ${k - 0.5}"></button>`
        + `<button class="half r" data-v="${2 * k + 1}/11" aria-label="星 ${k}"></button></span>`).join('') + none;
  }
  return MARKS.map(g => btn(g, g)).join('');
}

/** The 評価の付け方 card on 設定: shapes or stars, and how many steps. */
export function scaleCardHtml(scale, head = `<summary><h2>評価の付け方</h2></summary>`) {
  const opt = s => `<label class="pchip${s === scale ? ' on' : ''}"><input type="radio" name="rscale" value="${s}"${s === scale ? ' checked' : ''}>`
    + `<span class="pl">${SCALE_LABEL[s]}</span></label>`;
  return `<details class="card">${head}
<p class="lead">観た公演に付ける評価の形を選べます。<b>段階の意味は自分の尺度で決めて構いません。</b>おすすめは自分が付けた評価の中で高いか低いかを見て作るので、どの形でも同じように働きます。<br>
<b>形を変えても、これまでに付けた評価はそのまま残ります。</b>表示も付けたときの形のままです。</p>
<form class="pfil" id="scale-setting" onsubmit="return false">
<p class="pgrp"><b>図形</b></p><div class="pchips">${['marks2', 'marks3', 'marks4'].map(opt).join('')}</div>
<p class="pgrp"><b>星</b></p><div class="pchips">${['stars5', 'stars11'].map(opt).join('')}</div>
<div class="pfoot"><button type="button" data-set-scale="1">この形にする</button><span class="said"></span></div>
</form></details>`;
}

/** POST /api/rating_scale {scale} */
export async function scaleAction(b, ctx) {
  const scale = String(b?.scale ?? '');
  if (!SCALES.includes(scale)) throw new ValueError('その形は選べません');
  await ctx.db.prepare("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?, 'rating_scale', ?, datetime('now')) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at")
    .bind(ctx.uid, scale).run();
  return {body: {ok: true, scale}};
}
