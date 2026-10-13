// 裏の答え合わせ (q-hidden-gate): for each user, quietly check whether a
// variant of the scoring rules would have predicted *their own* later
// ratings better than the default, and use it only if it clearly did.
//
// Nothing extra is stored or sent anywhere. The check replays the user's
// ratings in the order they were made, in blocks of BLOCK productions: every
// variant scores a block using only the ratings made before it ("predict,
// then check": docs/knowledge/notes/lit-prequential.md), and the rules that
// put more of the block's pairs in the user's order win the block. A variant
// is used only if it wins clearly more blocks than it loses (one-sided sign
// test, z ≥ 1.96, at least MIN_UNITS deciding blocks; lit-safe-improvement):
// with few ratings everyone keeps the default.
//
// Variants are role-group multipliers on top of person-ordinal-v3, so the
// same index serves them all. They are the choices public data could not
// settle for theatre (eval_design_choices.py): how much kinds of show count,
// and how much the director / writer count compared with the cast.
import {independentRatings, personValues, gradeOf, TOP_N} from './recommend.js';

// Ports of tools/review/recommend2.py ROLE_W / BACKSTAGE_W and
// tools/taguri/app.py ROLE_GROUPS (checked against Python in the test).
export const ROLE_W = {'出演': 1.0, '演出': 0.4, '脚本': 0.4, '作': 0.4, '原作': 0.4, '翻訳': 0.3};
export const BACKSTAGE_W = 0.1;
export const GENRE_W = 1.0;
const GROUPS = {
  cast: ['出演'],
  author: ['演出', '脚本', '作', '原作', '翻訳', '潤色', '構成', '演出・振付'],
  craft: ['美術', '照明', '音響', '映像', '衣裳', '衣装', '振付', '音楽', '作曲', '編曲', '歌唱指導', 'ヘアメイク', 'メイク',
    '小道具', '大道具', '特殊効果', '特効', '方言指導', 'アクション', 'アクション監督', '殺陣', '人形', 'オーケストラ', '演奏', '指揮', '録音', '選曲'],
  stage: ['舞台監督', '技術監督', '演出助手', '舞台監督助手', 'スタッフ', '進行', '舞台美術製作', '大道具製作'],
  produce: ['製作', '制作', 'プロデューサー', 'エグゼクティブプロデューサー', '宣伝', '宣伝美術', '票券', '企画', '広報', '協力', '提携', '主催'],
};
const ROLE_GROUP = new Map(Object.entries(GROUPS).flatMap(([g, roles]) => roles.map(r => [r, g])));
export const groupOf = role => role.startsWith('#') ? 'theme' : (ROLE_GROUP.get(role) || 'other');

export const VARIANTS = {
  base: {},
  kinds_strong: {theme: 2},        // kinds of show weigh 2.0 instead of 1.0
  author_strong: {author: 2.5},    // director / writer weigh as much as the cast
};
export const MIN_UNITS = 6, Z = 1.96, WINDOW = 120, MIN_HISTORY = 5, BLOCK = 6;

/** A production's score from its people and kind tags (user_recommender.b_score). */
export function stageScore(values, people, multipliers = {}) {
  const mult = g => (Object.hasOwn(multipliers, g) ? multipliers[g] : 1.0);
  const parts = [], negative = [], kinds = [];
  for (const [role, person] of people) {
    const v = values.get(role + '\u0000' + person);
    if (!v) continue;
    const w = role.startsWith('#') ? GENRE_W : (Object.hasOwn(ROLE_W, role) ? ROLE_W[role] : BACKSTAGE_W);
    const c = v[1] * (w * mult(groupOf(role)));
    if (!c) continue;
    (role.startsWith('#') ? kinds : c > 0 ? parts : negative).push(c);
  }
  if (!parts.length && !negative.length && !kinds.length) return null;
  parts.sort((a, b) => b - a); negative.sort((a, b) => a - b);
  let pos = 0, neg = 0, ks = 0;
  for (const c of parts.slice(0, TOP_N)) pos += c;
  for (const c of negative.slice(0, TOP_N)) neg += c;
  for (const c of kinds) ks += c;
  return pos + neg + (kinds.length ? ks / kinds.length : 0);
}

/**
 * Which variant to use for this user. `rated`: records with verdict, people,
 * updated_at (same shape as scoreFromIndex). Returns
 * {variant, multipliers, checked: {name: {wins, losses}}}.
 */
export function chooseVariant(rated, {variants = VARIANTS, minUnits = MIN_UNITS, z = Z, window = WINDOW, block = BLOCK} = {}) {
  const ordered = independentRatings(rated).filter(r => (r.people || []).length);
  const names = Object.keys(variants).filter(n => n !== 'base');
  // Unit: a block of `block` productions rated one after another, all
  // scored from the ratings made before the block only, and the pairs inside
  // it the user rated differently (same scale). Scoring both sides of a pair
  // from the same past matters: comparing a production with earlier ones
  // lets the earlier rating leak into the later score. Blocks do not overlap
  // and blocks, not pairs, are counted: pairs sharing a production are far
  // from independent, and counting them (or overlapping units) let users
  // with random ratings pass the test far more often than 1 in 40.
  const tally = Object.fromEntries(names.map(n => [n, {wins: 0, losses: 0}]));
  for (let t = Math.max(MIN_HISTORY, ordered.length - window); t + 1 < ordered.length; t += block) {
    const values = personValues(ordered.slice(0, t));
    const items = ordered.slice(t, t + block).map(r => [r, gradeOf(r.verdict)]);
    const right = mult => {
      const sc = items.map(([r]) => stageScore(values, r.people, mult) ?? 0);
      let n = 0;
      for (let i = 0; i < items.length; i++) {
        for (let j = i + 1; j < items.length; j++) {
          const [[vi, ki], [vj, kj]] = [items[i][1], items[j][1]];
          if (ki !== kj || vi === vj) continue;
          const x = sc[i] - sc[j];
          if (x !== 0 && Math.sign(x) === Math.sign(vi - vj)) n += 1;
        }
      }
      return n;
    };
    const base = right(variants.base || {});
    for (const n of names) {
      const r = right(variants[n]);
      if (r > base) tally[n].wins += 1;
      else if (r < base) tally[n].losses += 1;
    }
  }
  const checked = tally;
  let best = 'base', bestMargin = 0;
  for (const n of names) {
    const {wins, losses} = tally[n];
    const deciding = wins + losses, margin = wins - losses;
    if (deciding >= minUnits && margin >= z * Math.sqrt(deciding) && margin > bestMargin) { best = n; bestMargin = margin; }
  }
  return {variant: best, multipliers: variants[best], checked};
}
