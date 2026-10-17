// Person-score recommendations in the Worker (step 2 of moving them off
// Render). A port of score_from_index in scripts/build_recommend_index.py,
// itself checked against tools/review/user_recommender.py (person-ordinal-v3).
// test/recommend.test.js runs this against Python's output on the same
// synthetic catalogue and must agree on stages, order, scores and reasons.
//
// Parity details:
// - Arithmetic is done in the same order and grouping as Python.
// - round(x, 6) == Number(x.toFixed(6)) for these values: both round the exact
//   binary value, and an exact decimal tie at the 7th digit cannot occur.
// - Strings compare by code point, as Python does (not UTF-16 units).

import {titleKey} from './stage-search.js';

export const CONF_K = 3, TOP_N = 3;
export const GRADE_VALUE = {'◎': 4, '○': 3, '△': 2, '×': 1};
export const MIN_LEVELS = 2, MAX_LEVELS = 11;
const SQRT12 = Math.sqrt(12);
// Favourites as pseudo ratings (user_recommender.SEED_Z / SEED_K and
// build_recommend_index.seeds_from_favourites).
export const SEED_Z = 0.4 * SQRT12, SEED_K = 3;
export const SEED_ROLES = ['出演', '演出', '脚本', '作', '原作', '翻訳', '潤色', '構成', '振付', '作曲', '音楽'];
export const SEED_KINDS = ['人', '原作者'], MAX_SEED_FAVS = 20, MAX_SEED_STAGES = 60;
export const SEED_GROUP_KINDS = ['団体', '主催'], SEED_WORK_KINDS = ['作品'], SEED_THEME_KINDS = ['題材'];
export const THEME_AXIS = '#題材';
/**
 * 索引から外した種類（起案者の指示 2026-10-16、dec-source-kind-no-price）。新しい索引には入らないが、
 * 本番の D1 の索引は差分で何日もかけて入れ替わるので、それまで残っている行もここで読まない。
 */
// #会場: 劇場の名前は理由にも点にも使わない（起案者の指示 2026-10-17、dec-drop-venue-kind）
export const DROPPED_AXES = new Set(['#値段', '#会場']);
// 使わなくなった種類の値（「原作もの」→ 漫画原作・小説原作 …、dec-source-kind-no-price）。索引に残っている間も読まない
export const DROPPED_KEYS = new Set(['#原作\u0000原作もの']);
export const droppedKind = (axis, tag) => DROPPED_AXES.has(axis) || DROPPED_KEYS.has(axis + '\u0000' + tag);
/** recommend2.nz: NFKC, no spaces (ASCII or full-width), lower case. */
export const nz = s => String(s ?? '').normalize('NFKC').replaceAll(' ', '').replaceAll('\u3000', '').toLowerCase();
// 詳細 (good / trouble per aspect): user_recommender.ASPECTS (checked against Python in the test).
export const ASPECTS = {
  story: ['話・脚本・構成', {'脚本': 1.0, '作': 1.0, '原作': 1.0, '原案': 1.0, '翻訳': 1.0, '潤色': 1.0, '構成': 1.0,
    '演出': 0.5, '演出・振付': 0.5, '#形式': 0.5, '#原作': 0.5, '#翻訳': 0.5, '#原作の国': 0.5}],
  direction: ['演出・見せ方', {'演出': 1.0, '演出・振付': 1.0, '美術': 0.5, '照明': 0.5, '音響': 0.5, '映像': 0.5, '#形式': 0.5}],
  acting: ['演技・出演', {'出演': 1.0, '演出': 0.2, '演出・振付': 0.2}],
  music: ['歌・音楽', {'作曲': 1.0, '音楽': 1.0, '編曲': 1.0, '音楽監督': 1.0, '歌唱指導': 1.0, '出演': 0.5, '#形式': 0.5}],
  dance: ['ダンス', {'振付': 1.0, '演出・振付': 1.0, '出演': 0.5}],
  design: ['美術・衣裳', {'美術': 1.0, '衣裳': 1.0, '衣装': 1.0, 'ヘアメイク': 1.0, 'メイク': 1.0, '小道具': 1.0, '演出': 0.5}],
  price: ['値段', {'#値段': 1.0}],
  venue: ['会場・座席', {'#会場': 1.0}],
};
/** user_recommender.parse_aspects: [troubles, goods] ("+code" = good), each in ASPECTS order. */
export function parseAspects(value) {
  const given = new Set(Array.isArray(value) ? value : String(value ?? '').split(','));
  const codes = Object.keys(ASPECTS);
  return [codes.filter(c => given.has(c)), codes.filter(c => given.has('+' + c))];
}
/** Canonical text of a record's aspects (troubles, then "+goods"), or null if invalid. */
export function cleanAspects(value) {
  const given = new Set((Array.isArray(value) ? value : String(value ?? '').split(',')).map(String).map(x => x.trim()).filter(Boolean));
  if ([...given].some(g => !Object.hasOwn(ASPECTS, g.replace(/^\+/, '')))) return null;
  const [troubles, goods] = parseAspects([...given]);
  if (troubles.some(c => goods.includes(c))) return null;
  return [...troubles, ...goods.map(c => '+' + c)].join(',');
}
function aspectShare(troubles, goods, role, positive) {
  const [main, other] = positive ? [goods, troubles] : [troubles, goods];
  const top = (codes, dflt) => { let m = -Infinity; for (const c of codes) { const v = Object.hasOwn(ASPECTS[c][1], role) ? ASPECTS[c][1][role] : 0.0; if (v > m) m = v; } return codes.length ? m : dflt; };
  return top(main, 1.0) * (1.0 - top(other, 0.0));
}

/** user_recommender.grade_of: [value, levels] of a saved rating ("◎" or "4/5"), or null. */
export function gradeOf(verdict) {
  if (Object.hasOwn(GRADE_VALUE, verdict)) return [GRADE_VALUE[verdict], 4];
  const m = /^(\d{1,2})\/(\d{1,2})$/.exec(String(verdict ?? ''));
  if (!m) return null;
  const value = Number(m[1]), levels = Number(m[2]);
  return levels >= MIN_LEVELS && levels <= MAX_LEVELS && value >= 1 && value <= levels ? [value, levels] : null;
}
// user_recommender.CONTENT_AXES
export const CONTENT_AXES = ['#形式', '#原作', '#翻訳', '#原作の国', '#題材', '#ジャンル'];
// 大きなくくりのジャンル（user_recommender.GENRE_AXIS）。理由の ✕ で外すと、その公演ごとおすすめから外す
export const GENRE_AXIS = '#ジャンル';
const KEYS_PER_QUERY = 49;     // D1 binds at most 100 parameters: ver + 2 per key
const IDS_PER_QUERY = 98;

// Fast path: k/1e6 is the double nearest to the decimal k·10^-6 (both exact
// integers, IEEE division), i.e. the same as Number(x.toFixed(6)), as long as
// x·1e6 is not within a hair of a .5 boundary; then fall back to toFixed.
const round6 = x => {
  const y = x * 1e6, f = y - Math.floor(y);
  return Math.abs(f - 0.5) < 1e-6 ? Number(x.toFixed(6)) : Math.round(y) / 1e6;
};
export function cmp(a, b) {
  a = String(a); b = String(b);
  if (a === b) return 0;
  let i = 0, j = 0;
  while (i < a.length && j < b.length) {
    const x = a.codePointAt(i), y = b.codePointAt(j);
    if (x !== y) return x < y ? -1 : 1;
    i += x > 0xffff ? 2 : 1; j += y > 0xffff ? 2 : 1;
  }
  return i >= a.length ? -1 : 1;     // the shorter one is a prefix of the other
}
const cmpTuple = (a, b) => { for (let i = 0; i < a.length; i++) { const c = typeof a[i] === 'number' ? (a[i] < b[i] ? -1 : a[i] > b[i] ? 1 : 0) : cmp(a[i], b[i]); if (c) return c; } return 0; };

/** One rating per linked stage (latest), unlinked records by their own key. */
export function independentRatings(rows) {
  const sorted = [...rows].sort((r, s) => cmpTuple([r.updated_at || r.date || '', r.key || ''], [s.updated_at || s.date || '', s.key || '']));
  const grouped = new Map();
  for (const row of sorted) {
    if (!gradeOf(row.verdict)) continue;
    const key = row.stage_id ? 'stage\u0000' + row.stage_id : 'work\u0000' + row.key;
    grouped.set(key, row);         // like a Python dict: a later row keeps the key's first slot
  }
  return [...grouped.values()];
}

/**
 * user_recommender.person_values: (role, person) -> [n, value], where value is
 * Σ z / (n + CONF_K) and z = (grade − the user's mean) / the user's spread
 * (◎○△× = 4/3/2/1). Same float operations in the same order as Python.
 */
// 興味あり（起案者の指示 2026-10-15「1+2+3まとめて入れて」、impl-interest-split）。押すのは 1 回で理由は
// 聞かないので、1 公演ぶんの重さ（評価 1 件と同じ 1）を、その公演の人・種類に割って配る:
// (1) 人・種類に割る（何件にも共通する人・種類だけが積み上がって効く）。人に INTEREST_PEOPLE_SHARE、種類に残り。
//     人の中は役の格（castImportance・CORE_CREATORS、2 段だけ）の割合で割る
// (2) 評価・お気に入りで好きと分かっている人には 1 + INTEREST_PRIOR_BOOST × その値 の割合で多めに配る
// (3) 興味なしの公演にもいる人・種類は、興味ありの件数 /（興味あり＋興味なし）に弱める
// 「なぜ気になったか」に名前が書いてあれば、その人に INTEREST_NOTE_BOOST 倍で配る。
// z はお気に入りと同じ SEED_Z、重みも SEED_K / (SEED_K + 評価の数) で評価が増えるほど薄まる。値は舞台では未検証。
export const INTEREST_PEOPLE_SHARE = 0.5, INTEREST_PRIOR_BOOST = 3, INTEREST_NOTE_BOOST = 5;
// 人の中の配り方（役の格、起案者の指示 2026-10-15）。興味の理由は主演とは限らない（「別に主演が気になるから
// 興味あるわけじゃない」）ので、役の格は弱い歯止めとしてだけ使う（案 B、q-interest-why-unknown）: 主な役と中心の
// 作り手は同じ 1、アンサンブルとそれ以外のスタッフは LESSER_IMPORTANCE 倍。書かれた順で差は付けない。
// トメ（最後に別の行で書かれた人）は、アンサンブルの見出しより後でも主な役に入れる（段の境目の判定にだけ使う）。
// 「なぜ」は、何件にも共通するもの・本人の好み・興味なしとの比べ・理由の名前が推し量る。いつまで使うかは要検証。
// 主な役＝役名つきで書かれた人（役名が 1 人も無ければ「アンサンブル」の見出しより前の人、見出しも無ければ全員）。
export const CORE_CREATORS = new Set(['演出', '脚本', '原作', '作曲', '構成', '音楽', '振付', '翻訳', '潤色', '作詞']);
export const LESSER_IMPORTANCE = 0.3, TOME_MIN = 3;
const nfkc = s => String(s ?? '').normalize('NFKC');
const HEADING = /^(出演|キャスト|cast|アンサンブル|ensemble|[【［][^】］]*[】］])[:：]$/i;
/** 出演者の名前 -> 1（主な役）か LESSER_IMPORTANCE（アンサンブル）。text は公演ページの出演欄そのまま。 */
export function castImportance(text, names) {
  const raw = nfkc(text), out = new Map();
  const ens = raw.search(/アンサンブル|ensemble/i);
  const found = names.map(n => [n, raw.indexOf(nfkc(n))]).filter(([, i]) => i >= 0);
  // 「役名：名前」: 同じ行で、区切りの後ろの語がコロンで終わり、見出し（出演：・アンサンブル：）ではない
  const named = ([, i]) => {
    const part = raw.slice(raw.lastIndexOf('\n', i) + 1, i).replace(/[\s　]+$/u, '').split(/[、,，／/]/u).pop().trim();
    return /[:：]$/.test(part) && !HEADING.test(part);
  };
  const anyNamed = found.some(named);
  for (const f of found) out.set(f[0], (anyNamed ? named(f) : ens < 0 || f[1] < ens) ? 1 : LESSER_IMPORTANCE);
  // トメ（起案者 2026-10-15「トメ使ってもいいとは思う」）: 出演欄のいちばん最後に、ほかの名前と別の行で書かれた人は
  // 大物・ベテランを置く位置なので、アンサンブルの見出しより後でも主な役にする（3 人以上いるときだけ）。
  if (found.length >= TOME_MIN) {
    const [tome, at] = found.reduce((a, b) => (b[1] > a[1] ? b : a));
    const lineStart = raw.lastIndexOf('\n', at) + 1, lineEnd = raw.indexOf('\n', at) < 0 ? raw.length : raw.indexOf('\n', at);
    // 別の行で、ほかの名前も「アンサンブル」の見出しも同じ行に無いこと
    const alone = lineStart > 0 && !(ens >= lineStart && ens < lineEnd)
      && !found.some(([n, i]) => n !== tome && i >= lineStart && i < lineEnd);
    if (alone) out.set(tome, 1);
  }
  // 出演欄に見つからない人は、見つかった人のいちばん軽い重さ（だれも見つからなければ 1）
  const least = found.length ? Math.min(...out.values()) : 1;
  for (const n of names) if (!out.has(n)) out.set(n, least);
  return out;
}
const importanceOf = (role, person, cast) => (role === '出演' ? (cast?.get(person) ?? 1)
  : CORE_CREATORS.has(role) ? 1 : LESSER_IMPORTANCE);
const keyOf = (role, person) => role + '\u0000' + person;
/** One interest stage's share per key ("role\0person"), summing to 1. */
export function interestShares(stage, prior, contrast = new Map(), skip = new Set()) {
  const keys = [...new Set((stage.people || []).filter(([, person]) => !skip.has(person)).map(([role, person]) => keyOf(role, person)))].sort(cmp);
  const note = String(stage.note || '');
  const castNames = [...new Set((stage.people || []).filter(([role]) => role === '出演').map(([, p]) => p))];
  const cast = stage.cast_text ? castImportance(stage.cast_text, castNames) : null;
  const factor = k => {
    const role = k.slice(0, k.indexOf('\u0000')), person = k.slice(k.indexOf('\u0000') + 1);
    let f = (role.startsWith('#') ? 1 : importanceOf(role, person, cast)) * (1 + INTEREST_PRIOR_BOOST * Math.max(prior.get(k)?.[1] || 0, 0));
    if (!role.startsWith('#') && Array.from(person).length >= 2 && note.includes(person)) f *= INTEREST_NOTE_BOOST;
    const [yes, no] = contrast.get(k) || [1, 0];
    return f * (yes / (yes + no));
  };
  const people = keys.filter(k => !k.startsWith('#')), kinds = keys.filter(k => k.startsWith('#'));
  const out = new Map();
  const spread = (ks, total) => {
    const fs = ks.map(factor), sum = fs.reduce((a, b) => a + b, 0);
    if (sum > 0) ks.forEach((k, i) => out.set(k, total * fs[i] / sum));
  };
  if (people.length && kinds.length) { spread(people, INTEREST_PEOPLE_SHARE); spread(kinds, 1 - INTEREST_PEOPLE_SHARE); }
  else spread(people.length ? people : kinds, 1);
  return out;
}
/** key -> [stages answered 興味あり that have it, stages answered 興味なし that have it]. */
export function interestContrast(liked, disliked, skip = new Set()) {
  const out = new Map();
  for (const [list, i] of [[liked, 0], [disliked, 1]]) for (const s of list) {
    for (const k of new Set((s.people || []).filter(([, p]) => !skip.has(p)).map(([r, p]) => keyOf(r, p)))) {
      const c = out.get(k) || [0, 0]; c[i] += 1; out.set(k, c);
    }
  }
  return out;
}

/** 配り分けを外した計算（分析の H5 だけで使う）: 興味ありの 1 公演ぶんを、人と種類に同じだけ割る。 */
function evenShares(stage, skip = new Set()) {
  const keys = [...new Set((stage.people || []).filter(([, person]) => !skip.has(person)).map(([role, person]) => keyOf(role, person)))];
  return new Map(keys.map(k => [k, 1 / keys.length]));
}

// 部品を 1 つずつ外して比べるための旗（docs/research/real-data-eval-plan.md の H5）。分析の再生だけが渡す。
// 既定（{}）では何も外さず、画面の計算は変わらない。split: 興味ありの配り分け（式 10–11）、expand: 1 段広げる（式 12）。
// 並べ直し（式 13）と裏の答え合わせ（式 14–16）は画面の側（spreadLeads・chooseVariant）なので、再生の側で外す
export const ABLATIONS = ['split', 'expand'];

export function personValues(rated, seeds = [], skip = new Set(), liked = [], disliked = [], ablate = {}) {
  // person-ordinal-v3: a rating's place among the user's own ratings on the
  // same scale, ((lower) + ½ (equal)) / n − ½, times √12.
  const byScale = new Map();
  for (const r of rated) {
    const [value, levels] = gradeOf(r.verdict);
    if (!byScale.has(levels)) byScale.set(levels, []);
    byScale.get(levels).push(value);
  }
  const tally = new Map();
  for (const r of rated) {
    const [value, levels] = gradeOf(r.verdict);
    const vals = byScale.get(levels);
    let below = 0, same = 0;
    for (const v of vals) { if (v < value) below += 1; else if (v === value) same += 1; }
    const z = ((below + 0.5 * same) / vals.length - 0.5) * SQRT12;
    const keys = [...new Set((r.people || []).map(([role, person]) => role + '\u0000' + person))].sort(cmp);
    // 詳細: a rating lands mainly on what was good (above the middle) or a
    // trouble (below it), less on what the other side points at.
    const [troubles, goods] = z ? parseAspects(r.aspects) : [[], []];
    const marked = troubles.length || goods.length;
    for (const k of keys) {
      const t = tally.get(k) || [0, 0, 0];
      t[0] += 1; t[1] += marked ? z * aspectShare(troubles, goods, k.slice(0, k.indexOf('\u0000')), z > 0) : z; t[2] += 1.0;
      tally.set(k, t);
    }
  }
  // Seeds: z = SEED_Z with weight w; they add to the weight, not to n.
  const w = SEED_K / (SEED_K + rated.length);
  for (const r of seeds) {
    const keys = [...new Set((r.people || []).filter(([, person]) => !skip.has(person)).map(([role, person]) => role + '\u0000' + person))].sort(cmp);
    for (const k of keys) {
      const t = tally.get(k) || [0, 0, 0];
      t[1] += w * SEED_Z; t[2] += w;
      tally.set(k, t);
    }
  }
  const values = new Map();
  for (const [k, [cnt, sum, wt]] of tally) values.set(k, [cnt, sum / (wt + CONF_K)]);
  if (!liked.length) return values;
  // 興味あり: 評価とお気に入りから分かった値（values）を (2) の手がかりにして、1 公演ぶんを割って足す。
  const contrast = interestContrast(liked, disliked, skip);
  for (const s of liked) {
    for (const [k, share] of ablate.split ? evenShares(s, skip) : interestShares(s, values, contrast, skip)) {
      const t = tally.get(k) || [0, 0, 0];
      t[1] += w * SEED_Z * share; t[2] += w * share;
      tally.set(k, t);
    }
  }
  const out = new Map();
  for (const [k, [cnt, sum, wt]] of tally) out.set(k, [cnt, sum / (wt + CONF_K)]);
  return out;
}

/**
 * Ranked upcoming stages with a positive score, ordered like
 * user_recommender.finish before tour grouping (person-ordinal-v3).
 * postingsFor(keys [[role, person]...]) -> [[role, person, stage_id, role_w, group]...]
 * stagesFor(stageIds) -> Map(stage_id -> {start, end})
 */
// 好きな人とよく組む人へ 1 段だけ広げる（起案者の指示 2026-10-15「同じ人ばかり出るのを和らげる案も進めて」、
// lit-content-overspecialization・lit-live-show-propagation）。値が正の人（上位 EXPAND_PEOPLE 人）が出る
// これからの公演（EXPAND_STAGES まで）で一緒に名前のある人に、その人の値 × EXPAND_WEIGHT を仮に与え、
// その人の別の公演も候補にする。すでに値のある人・お気に入りの名前は除く。理由には「○○と組む」と出す。
// Python の参照実装には無いので、一致試験の経路（expand なし）では動かない。値は舞台では未検証。
export const EXPAND_PEOPLE = 20, EXPAND_STAGES = 60, EXPAND_WEIGHT = 0.3, EXPAND_MIN_SHARED = 1;
export async function scoreFromIndex({postingsFor, stagesFor, rated, multipliers = {}, today, seeds = [], skip = new Set(), liked = [], disliked = [], expand = null, ablate = {}}) {
  rated = independentRatings(rated);
  const values = personValues(rated, seeds, skip, liked, disliked, ablate);
  const seeded = new Set(seeds.map(r => r.stage_id));
  // Everyone with a non-zero value can raise or lower a show.
  // 使わなくなった種類（料金帯 #値段、dec-source-kind-no-price）は、本番の索引に残っている間も点数と理由に使わない
  const keys = [...values.entries()].filter(([k, [, v]]) => v && !droppedKind(...k.split('\u0000'))).map(([k]) => k.split('\u0000')).sort((a, b) => cmpTuple(a, b));
  const byStage = new Map();
  const mult = g => (Object.prototype.hasOwnProperty.call(multipliers, g) ? multipliers[g] : 1.0);
  for (const [role, person, sid, roleW, group] of await postingsFor(keys)) {
    const [n, value] = values.get(role + '\u0000' + person);
    // Same operations and order as Python: value * (role_w * multiplier)
    const contrib = round6(value * (roleW * mult(group)));
    if (contrib) {
      if (!byStage.has(sid)) byStage.set(sid, []);
      byStage.get(sid).push([contrib, role, person, n, group]);
    }
  }
  // 1 段だけ広げる: 好きな人（値が正）が出る公演の共演者・作り手
  const via = new Map();                       // key -> name of the liked person they work with
  if (expand?.peopleFor && !ablate.expand) {
    const top = [...values.entries()].filter(([k, [, v]]) => v > 0 && !k.startsWith('#')).sort((a, b) => (b[1][1] - a[1][1]) || cmp(a[0], b[0])).slice(0, EXPAND_PEOPLE);
    const likedTop = new Map(top.map(([k, [, v]]) => [k, v]));
    const stageLiked = new Map();               // sid -> [[key, v]...] of liked people in it
    for (const [sid, all] of byStage) for (const p of all) {
      const k = p[1] + '\u0000' + p[2];
      if (!likedTop.has(k)) continue;
      if (!stageLiked.has(sid)) stageLiked.set(sid, []);
      stageLiked.get(sid).push([k, likedTop.get(k)]);
    }
    const sids = [...stageLiked].sort((a, b) => (b[1].reduce((s, x) => s + x[1], 0) - a[1].reduce((s, x) => s + x[1], 0)) || cmp(a[0], b[0]))
      .slice(0, EXPAND_STAGES).map(([sid]) => sid);
    const people = sids.length ? await expand.peopleFor(sids) : new Map();
    const partner = new Map();                  // key -> [value, via name, shared stages]
    for (const sid of sids) {
      const [bestKey, bestV] = stageLiked.get(sid).reduce((a, b) => (b[1] > a[1] ? b : a));
      for (const [role, person] of people.get(sid) || []) {
        const k = role + '\u0000' + person;
        if (role.startsWith('#') || values.has(k) || skip.has(person) || expand.exclude?.has(k)) continue;
        const cur = partner.get(k) || [0, '', 0];
        const v = EXPAND_WEIGHT * bestV;
        partner.set(k, [Math.max(cur[0], v), v >= cur[0] ? bestKey.slice(bestKey.indexOf('\u0000') + 1) : cur[1], cur[2] + 1]);
      }
    }
    const pkeys = [...partner].filter(([, [, , n]]) => n >= EXPAND_MIN_SHARED).map(([k]) => k.split('\u0000')).sort((a, b) => cmpTuple(a, b));
    if (pkeys.length) {
      for (const [role, person, sid, roleW, group] of await postingsFor(pkeys)) {
        // 好きな人がすでに出ている公演には足さない（二重に数えない）。広げるのは新しい公演だけ
        if (stageLiked.has(sid)) continue;
        const [value, name] = partner.get(role + '\u0000' + person);
        const contrib = round6(value * (roleW * mult(group)));
        if (!contrib) continue;
        if (!byStage.has(sid)) byStage.set(sid, []);
        byStage.get(sid).push([contrib, role, person, 0, group]);
        via.set(role + '\u0000' + person, name);
      }
    }
  }
  const stages = await stagesFor([...byStage.keys()]);
  const out = [];
  for (const [sid, all] of byStage) {
    const st = stages.get(sid);
    if (seeded.has(sid) || !st || (st.end && st.end < today)) continue;
    if (st.start && st.start <= today) continue;          // already running
    // Kind-of-show tags ("#axis") add their mean; people add the strongest 3
    // up and 3 down (user_recommender.b_score).
    const people = all.filter(p => !p[1].startsWith('#'));
    const kinds = all.filter(p => p[1].startsWith('#')).sort((p, q) => cmp(p[1], q[1]) || cmp(p[2], q[2]));
    const parts = people.filter(p => p[0] > 0).sort((p, q) => (q[0] - p[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]));
    const negative = people.filter(p => p[0] < 0).sort((p, q) => (p[0] - q[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]));
    // Python: sum(positive top 3) + sum(negative top 3) + sum(kinds) / len, each sum from 0.
    let pos = 0, neg = 0, ks = 0;
    for (const p of parts.slice(0, TOP_N)) pos += p[0];
    for (const p of negative.slice(0, TOP_N)) neg += p[0];
    for (const p of kinds) ks += p[0];
    const b = round6(pos + neg + (kinds.length ? ks / kinds.length : 0));
    // A show needs a reason: a person who raised it, or a kind of the show itself
    // (form, source, translation, subject). Venue and price band only re-order:
    // a show with no credits has only those (user_recommender.has_reason).
    if (b <= 0 || !(parts.length || kinds.some(k => k[0] > 0 && CONTENT_AXES.includes(k[1])))) continue;
    // Kinds shown as reasons: the raising ones, kinds of the show itself first.
    const shown = kinds.filter(k => k[0] > 0).sort((p, q) => (CONTENT_AXES.includes(q[1]) - CONTENT_AXES.includes(p[1]))
      || (q[0] - p[0]) || cmp(p[1], q[1]) || cmp(p[2], q[2]));
    const item = {stage_id: sid, b, strong: b, tour: st.tour || '', parts: parts.map(p => p.slice(0, 4)), kinds: shown.map(p => p.slice(0, 4))};
    if (via.size) {
      const w = parts.slice(0, 4).map(p => [p[1] + '\t' + p[2], via.get(p[1] + '\u0000' + p[2])]).filter(([, n]) => n);
      if (w.length) item.via = w;
    }
    out.push(item);
  }
  out.sort((x, y) => (y.strong - x.strong) || (y.b - x.b) || cmp(x.stage_id, y.stage_id));
  return out;
}

/**
 * build_recommend_index.seeds_from_favourites: candidate stages crediting a
 * favourite person / original author, with their people. Returns {seeds, skip}.
 */
export async function seedsFromFavourites({postingsFor, peopleFor, stagesMatching}, favourites) {
  const names = [...new Set(favourites.filter(f => SEED_KINDS.includes(f.kind)).map(f => f.name))].sort(cmp).slice(0, MAX_SEED_FAVS);
  const sids = new Set();
  if (names.length) {
    const keys = names.flatMap(name => SEED_ROLES.map(role => [role, name])).sort(cmpTuple);
    for (const r of await postingsFor(keys)) sids.add(r[2]);
  }
  // Troupes / producers by the producing company, works by the title
  // (recommend2.declared_hits' rules on normalised text).
  const pick = (kinds, norm) => [...new Set(favourites.filter(f => kinds.includes(f.kind)).map(f => norm(f.name)).filter(x => x.length >= 2))].sort(cmp).slice(0, MAX_SEED_FAVS);
  const groups = pick(SEED_GROUP_KINDS, nz), works = pick(SEED_WORK_KINDS, titleKey), subjects = pick(SEED_THEME_KINDS, nz);
  if ((groups.length || works.length || subjects.length) && stagesMatching)
    for (const sid of await stagesMatching(groups, works, subjects)) sids.add(sid);
  const chosen = [...sids].sort(cmp).slice(0, MAX_SEED_STAGES);
  if (!chosen.length) return {seeds: [], skip: new Set(names)};
  const people = await peopleFor(chosen);
  return {seeds: chosen.filter(sid => people.get(sid)?.length).map(sid => ({stage_id: sid, people: people.get(sid)})), skip: new Set(names)};
}

/**
 * build_recommend_index.collapse_ranked: one slot per production (a tour's
 * venues share rec_stage.tour, user_recommender.tour_key), the best-ranked
 * venue first with the others' stage ids in rank order; the first `top`.
 */
export function collapseRanked(ranked, top) {
  const groups = new Map();
  for (const c of ranked) {
    const key = c.tour || 'stage:' + c.stage_id;
    if (groups.has(key)) groups.get(key).tours.push(c.stage_id);
    else groups.set(key, {stage_id: c.stage_id, tours: []});
  }
  return [...groups.values()].slice(0, top);
}

/** The same contract over D1 (or SQLite in tests): the queries the Worker issues. */
export function d1Access(db, ver, counter = {rows: 0, queries: 0}) {
  return {
    counter,
    async postingsFor(keys) {
      const out = [];
      for (let i = 0; i < keys.length; i += KEYS_PER_QUERY) {
        const chunk = keys.slice(i, i + KEYS_PER_QUERY);
        const sql = 'SELECT role,person,stage_id,role_w,role_group FROM rec_credit WHERE ver=? AND (role,person) IN (VALUES '
          + chunk.map(() => '(?,?)').join(',') + ')';
        const {results} = await db.prepare(sql).bind(ver, ...chunk.flat()).all();
        counter.rows += results.length; counter.queries += 1;
        out.push(...results.map(r => [r.role, r.person, r.stage_id, r.role_w, r.role_group]));
      }
      return out;
    },
    async stagesFor(ids) {
      const map = new Map();
      for (let i = 0; i < ids.length; i += IDS_PER_QUERY) {
        const chunk = ids.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare('SELECT stage_id,start,end,tour FROM rec_stage WHERE ver=? AND stage_id IN ('
          + chunk.map(() => '?').join(',') + ')').bind(ver, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, {start: r.start, end: r.end, tour: r.tour});
      }
      return map;
    },
    async stagesMatching(groups, works, subjects = []) {
      const out = new Set();
      // Troupes / works: one pass over this version's stages (no index on these).
      const conds = [...groups.map(() => 'instr(gkey,?)>0'), ...works.map(() => 'instr(tkey,?)>0')];
      if (conds.length) {
        const {results} = await db.prepare(`SELECT stage_id FROM rec_stage WHERE ver=? AND (${conds.join(' OR ')})`).bind(ver, ...groups, ...works).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) out.add(r.stage_id);
      }
      // Subjects: #題材 words that contain the name or are contained in it (net_c.declared_hits).
      if (subjects.length) {
        const cond = subjects.map(() => '(instr(person,?)>0 OR (length(person)>=2 AND instr(?,person)>0))').join(' OR ');
        const {results} = await db.prepare(`SELECT DISTINCT stage_id FROM rec_credit WHERE ver=? AND role=? AND (${cond})`)
          .bind(ver, THEME_AXIS, ...subjects.flatMap(t => [t, t])).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) out.add(r.stage_id);
      }
      return [...out];
    },
    async peopleFor(ids) {
      const map = new Map();
      for (let i = 0; i < ids.length; i += IDS_PER_QUERY) {
        const chunk = ids.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare('SELECT stage_id,people FROM rec_people WHERE ver=? AND stage_id IN ('
          + chunk.map(() => '?').join(',') + ')').bind(ver, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, JSON.parse(r.people));
      }
      // Records linked to a past stage (past_stage, older than the index) bring its credits.
      const rest = ids.filter(s => !map.has(s));
      for (let i = 0; i < rest.length; i += IDS_PER_QUERY) {
        const chunk = rest.slice(i, i + IDS_PER_QUERY);
        let results = [];
        try {
          ({results} = await db.prepare('SELECT stage_id,people FROM past_stage WHERE stage_id IN ('
            + chunk.map(() => '?').join(',') + ')').bind(...chunk).all());
        } catch { break; }
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) map.set(r.stage_id, JSON.parse(r.people));
      }
      return map;
    },
  };
}
