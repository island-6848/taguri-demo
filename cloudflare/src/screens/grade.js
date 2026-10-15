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

/**
 * The rating buttons: ◎○△×, or a row of five stars ☆☆☆☆☆ (起案者の指示 2026-10-14「☆☆☆☆☆みたいなの
 * 表示されてて、自分が思ってる評価のとこ押したらそこまで星の色がつく、みたいなuiにして」).
 * Each star is a button for "n/5"; the ones up to the current rating carry .on (filled ★, style in
 * theme.css), and app.js fills up to the pressed one at once.
 */
export function gradeButtons(scale, current = '') {
  if (scale !== 'stars') return MARKS.map(g => `<button data-v="${g}">${g}</button>`).join('');
  const now = isStar(current) ? Number(String(current).slice(0, 1)) : 0;
  return [1, 2, 3, 4, 5].map(n => `<button class="star${n <= now ? ' on' : ''}" data-v="${n}/5" aria-label="星 ${n}"></button>`).join('');
}
