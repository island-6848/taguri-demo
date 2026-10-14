// 評価の段階: ◎○△× (4 段階) か、星 5 段階 ("n/5")。
//
// 起案者の指示（2026-10-14）「星5段階を初期設定にして。言葉の案は逆に決めないほうがいい
// んじゃない？勝手に個人が思ってる尺度でつけていっても、位置zに直すんだよね」
// (docs/knowledge: dec-star-default)。推薦は評価を本人の中での位置に直すので
// (recommend.gradeOf / personValues)、星の意味は人ごとに違ってよく、段階に言葉は添えない。
//
// まだ ◎○△× で 1 件も評価していない人は星、すでに ◎○△× で付けている人はそのまま
// ◎○△×（1 人の記録に 2 つの段階を混ぜない）。保存は "n/5"（例 "4/5"）で、表示は ★n。
// 色・並び・「最上位」の判定は、星を ◎○△× の側に読み替えて使う（★3 は真ん中で、どちらでもない）。
import {E} from './py.js';

export const MARKS = ['◎', '○', '△', '×'];
export const STARS = ['5/5', '4/5', '3/5', '2/5', '1/5'];          // 高い順（並べるとき）
const STAR = /^([1-5])\/5$/;
const STAR_AS_MARK = {5: '◎', 4: '○', 3: '', 2: '△', 1: '×'};

export const isStar = v => STAR.test(String(v ?? ''));
/** What a saved rating shows as: ◎ as is, "4/5" as ★4. */
export const gradeText = v => (isStar(v) ? '★' + String(v).slice(0, 1) : String(v ?? ''));
/** A star read as the mark on the same side (for colours and "liked"); ★3 is ''. */
export const markOf = v => (isStar(v) ? STAR_AS_MARK[String(v).slice(0, 1)] : String(v ?? ''));
/** The top of its scale (◎ or ★5). */
export const isTop = v => v === '◎' || v === '5/5';

/** 'marks' if the user has rated with ◎○△×, else 'stars' (the default). Cached on ctx. */
export async function scaleOf(ctx) {
  if (ctx._scale) return ctx._scale;
  const row = await ctx.db.prepare(`SELECT 1 AS x FROM works WHERE user_id=? AND verdict IN ('◎','○','△','×') LIMIT 1`).bind(ctx.uid).first();
  ctx._scale = row ? 'marks' : 'stars';
  return ctx._scale;
}

/** The rating buttons: ◎○△×, or ★1〜★5 (low to high, as star ratings are read). */
export function gradeButtons(scale) {
  if (scale !== 'stars') return MARKS.map(g => `<button data-v="${g}">${g}</button>`).join('');
  return [...STARS].reverse().map(g => `<button class="star" data-v="${g}" aria-label="星 ${g.slice(0, 1)}">${E(gradeText(g))}</button>`).join('');
}
