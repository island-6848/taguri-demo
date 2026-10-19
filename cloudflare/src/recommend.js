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
import {themeExpansion, rolledThemeWords} from './vocab.js';

export const CONF_K = 3, TOP_N = 3;
export const GRADE_VALUE = {'◎': 4, '○': 3, '△': 2, '×': 1};
export const MIN_LEVELS = 2, MAX_LEVELS = 11;
const SQRT12 = Math.sqrt(12);
// Favourites as pseudo ratings (user_recommender.SEED_Z / SEED_K and
// build_recommend_index.seeds_from_favourites).
export const SEED_Z = 0.4 * SQRT12, SEED_K = 3;
// お気に入りから作る種の重さは、興味あり（1 公演ぶんの重さを人・種類に割って配る）より強くする（起案者の指示 2026-10-18
// 「推薦の強さ、お気に入り＞興味ありにしてほしい」）。お気に入りの種は 1 公演ごとに、そこにいる人それぞれへ w × FAV_SEED_W を足す
export const FAV_SEED_W = 2;
export const SEED_ROLES = ['出演', '演出', '脚本', '作', '原作', '翻訳', '潤色', '構成', '振付', '作曲', '音楽'];
// お気に入りの公演から広げる「関わりのある人」の役職と重み（起案者の指示 2026-10-18「関わりのある人にも度合いがあって、
// 共演者＞演出＞脚本＞＞＞翻訳＞主催＞美術・照明・音響・映像・衣裳・振付くらいだけでいい」、dec-fav-spread-roles）。
// 種の仮の評価 SEED_Z にこの重みを掛ける（値はほぼこの比になる）。表に無い役職（制作・宣伝・進行・その他）からは広げない。
// 公演の種類（#形式・#題材 …）は人ではないので 1 のまま。役職の名前は credits.canonRole の後（作 → 脚本、衣装 → 衣裳）。
// user_recommender.FAV_SPREAD_W と同じ
export const FAV_SPREAD_W = {'出演': 1.0, '演出': 0.7, '演出・振付': 0.7,
  '脚本': 0.5, '作': 0.5, '上演台本': 0.5, '脚色': 0.5, '潤色': 0.5, '構成': 0.5, '原作': 0.5, '原案': 0.5,
  '翻訳': 0.2, '訳': 0.2, '主催': 0.15,
  '美術': 0.1, '舞台美術': 0.1, '照明': 0.1, '音響': 0.1, '映像': 0.1, '衣裳': 0.1, '衣装': 0.1, '振付': 0.1,
  // 作曲・音楽も、美術などと同じ重みで広げる（起案者の答え 2026-10-18「作曲・音楽を広げる元に入れて」）
  '作曲': 0.1, '音楽': 0.1, '音楽監督': 0.1, '編曲': 0.1};
export const favSpread = role => (role.startsWith('#') ? 1.0 : Object.hasOwn(FAV_SPREAD_W, role) ? FAV_SPREAD_W[role] : 0);
/** 登録した人の名前を索引の書き方に寄せる（索引は NFKC で姓名のあいだの空白を詰めてある: measure_nets._names）。 */
export const personKey = s => String(s ?? '').normalize('NFKC').replace(/[\s　]/gu, '');
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
// 詳細の印（user_recommender.ASPECT_MARKS。起案者の指示 2026-10-18「最低限5段階くらいほしい」「なかったときは✕で
// 要素を消せるように」、dec-aspects-five-levels）: "++code" 好き 2、"+code" やや好き 1、"code" やや好みではない −1、
// "--code" 好みではない −2、"~code" この作品には無い（推薦に使わない）。前の 3 段階の形はそのまま読む（同じ日「評価の詳細を
// 5 段階（好みではない〜好き）に変えて」）。
export const ASPECT_MARKS = [['', -1], ['+', 1], ['--', -2], ['++', 2], ['~', 0]];
const MARK_ORDER = ASPECT_MARKS.map(([m]) => m);
/** user_recommender.aspect_token: [mark, code] */
export function aspectToken(g) {
  for (const m of ['++', '--', '+', '~']) if (g.startsWith(m)) return [m, g.slice(m.length)];
  return ['', g];
}
/** user_recommender.aspect_levels: {code: −2..2 (0 = この作品には無い)}, known codes only. */
export function aspectLevels(value) {
  const given = [...new Set((Array.isArray(value) ? value : String(value ?? '').split(',')).map(String))];
  given.sort((x, y) => MARK_ORDER.indexOf(aspectToken(x)[0]) - MARK_ORDER.indexOf(aspectToken(y)[0]));
  const marks = Object.fromEntries(ASPECT_MARKS), out = {};
  for (const g of given) {
    const [m, c] = aspectToken(g);
    if (Object.hasOwn(ASPECTS, c) && !Object.hasOwn(out, c)) out[c] = marks[m];
  }
  return out;
}
/** user_recommender.parse_aspects: [troubles, goods] (good = "+" / "++"), each in ASPECTS order. */
export function parseAspects(value) {
  const lv = aspectLevels(value);
  const codes = Object.keys(ASPECTS);
  return [codes.filter(c => (lv[c] || 0) < 0), codes.filter(c => (lv[c] || 0) > 0)];
}
/** Canonical text of a record's aspects (rate_performances.clean_aspects), or null if invalid. */
export function cleanAspects(value) {
  const given = new Set((Array.isArray(value) ? value : String(value ?? '').split(',')).map(String).map(x => x.trim()).filter(Boolean));
  const marks = {};
  for (const g of given) {
    const [m, c] = aspectToken(g);
    if (!Object.hasOwn(ASPECTS, c)) return null;
    (marks[c] ||= new Set()).add(m);
  }
  if (Object.values(marks).some(x => x.size > 1)) return null;
  return MARK_ORDER.flatMap(m => Object.keys(ASPECTS).filter(c => marks[c]?.has(m)).map(c => m + c)).join(',');
}
// 好き・好みではない（±2）の項目が指す役職には、±1 よりこの倍だけ重く効かせる（user_recommender.ASPECT_STRONG。
// 起案者の指示 2026-10-18「詳細評価のとてもを推薦の効き方も強めてほしい。該当する人をちょっと重くするとか」）
export const ASPECT_STRONG = 1.5;
// user_recommender.aspect_share: ±2 の項目の役職は ASPECT_STRONG 倍（1 を越えてよい）、反対側が引く分は多くて全部。
// ±1 だけの記録（3 段階の記録はすべて）は前と同じ
function aspectShare(troubles, goods, role, positive, lv = {}) {
  const g = c => (Math.abs(lv[c] ?? 1) === 2 ? ASPECT_STRONG : 1.0);
  const [main, other] = positive ? [goods, troubles] : [troubles, goods];
  const top = (codes, dflt) => { let m = -Infinity; for (const c of codes) { const v = (Object.hasOwn(ASPECTS[c][1], role) ? ASPECTS[c][1][role] : 0.0) * g(c); if (v > m) m = v; } return codes.length ? m : dflt; };
  return top(main, 1.0) * (1.0 - Math.min(1.0, top(other, 0.0)));
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

/**
 * One rating per linked stage (latest), unlinked records by their own key. Ordered by when the
 * rating was made (rated_at, #112), else the row's last change (updated_at), else the date seen.
 */
export const ratedTime = r => r.rated_at || r.updated_at || r.date || '';
export function independentRatings(rows) {
  const sorted = [...rows].sort((r, s) => cmpTuple([ratedTime(r), r.key || ''], [ratedTime(s), s.key || '']));
  const grouped = new Map();
  for (const row of sorted) {
    if (!gradeOf(row.verdict)) continue;
    const key = row.stage_id ? 'stage\u0000' + row.stage_id : 'work\u0000' + row.key;
    grouped.set(key, row);         // like a Python dict: a later row keeps the key's first slot
  }
  // 作品ごとに分けた記録（occasion、dec-split-pieces）は、選ばれた観劇の作品をすべて残す（同じ公演の別の観劇は落とす）
  return [...grouped.values()].flatMap(r => (r.occasion ? sorted.filter(x => x.occasion === r.occasion && gradeOf(x.verdict)) : [r]));
}

/**
 * 1 回の観劇で複数の作品を観て、作品ごとに評価した記録（dec-split-pieces、起案者の決定 2026-10-19「0.4にしたい」）。
 * 同じ晩の作品の評価は、演出・劇場・その日の気分が共通なので似る。その似かた（級内相関）を PIECE_RHO と決め打ちし、
 * ある人が出た作品の数 m を、有効な件数 m / (1 + (m − 1)ρ) に縮める（Kish の design effect の形）。人の値には、
 * 出た作品の評価（z）の平均を、この件数ぶんの重みで 1 回だけ足す。10 本すべてに出た人も 2.5 件ぶんを越えない。
 */
export const PIECE_RHO = 0.4;
export const pieceWeight = m => m / (1 + (m - 1) * PIECE_RHO);
/** 評価の件数（作品ごとに分けた観劇は、作品の数によらず 1 件。r.share は 1 / 評価した作品の数） */
export const ratingCount = rated => rated.reduce((n, r) => n + (r.share ?? 1), 0);

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
// (3) 興味なしの公演にもいる人・種類は、割ったあとの分を 興味ありの件数 /（興味あり＋興味なし）倍に弱める（#109）
// 「なぜ気になったか」に名前が好んで書いてあれば（noteNames、打ち消し・比べの文は除く #111）、その人に INTEREST_NOTE_BOOST 倍で配る。
// z はお気に入りと同じ SEED_Z、重みも SEED_K / (SEED_K + 評価の数) で評価が増えるほど薄まる。値は舞台では未検証。
export const INTEREST_PEOPLE_SHARE = 0.5, INTEREST_PRIOR_BOOST = 3, INTEREST_NOTE_BOOST = 5;
// 興味ありの画面の ✕（候補から消す、reaction.interest=4）の負の重さ。興味あり 1 公演と同じ大きさ（起案者 2026-10-18「結構マイナス」）
export const REJECT_W = 1;
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
// 「なぜ気になったか」の文に名前があっても、好んで挙げたとは限らない（#111「俳優Aが理由ではない」「AよりBが気になる」）。
// 文を句点・読点・逆接（けど・のに・でも…）で区切り、名前のある区切りに打ち消し・苦手の語が無く、名前のすぐ後ろが
// 「より」「と比べ」でないときだけ多めに配る。分からないときは配らない（等分のまま）。別の呼び出し（LLM）は使わない。
// 長い名前に含まれる短い名前（「山田」と「山田花子」）は、長い名前の所では数えない
const NOTE_SPLIT = /[。．.!！?？\n、,，;；]|けれども|けれど|けど|のに|ものの|しかし|でも|だが/u;
const NOTE_NEG = /ない|無い|なく|ません|ではな|じゃな|苦手|嫌|きらい|キライ|微妙|いまいち|イマイチ|以外|抜き/u;
const NOTE_LESS = /^(?:さん|くん|君|ちゃん|様|さま|氏)?(?:より|と比べ|と比較|に比べ)/u;
/** The names (of `names`) the note brings up as a reason to be interested; empty when unsure. */
export function noteNames(note, names) {
  const out = new Set();
  const text = nfkc(note);
  if (!text.trim()) return out;
  const cands = [...new Set(names)].filter(n => Array.from(n).length >= 2).map(n => [n, nfkc(n)]).sort((a, b) => b[1].length - a[1].length || cmp(a[0], b[0]));
  for (let clause of text.split(NOTE_SPLIT)) {
    if (!clause || NOTE_NEG.test(clause)) continue;
    for (const [name, n] of cands) {
      let at = clause.indexOf(n), liked = false;
      while (at >= 0) {
        if (!NOTE_LESS.test(clause.slice(at + n.length))) liked = true;
        at = clause.indexOf(n, at + n.length);
      }
      if (liked) out.add(name);
      // 長い名前の所を伏せてから短い名前を探す
      if (clause.includes(n)) clause = clause.split(n).join('\u0000'.repeat(n.length));
    }
  }
  return out;
}
/** One interest stage's share per key ("role\0person"), summing to 1 (less when some keys are also in 興味なし). */
export function interestShares(stage, prior, contrast = new Map(), skip = new Set()) {
  const keys = [...new Set((stage.people || []).filter(([, person]) => !skip.has(person)).map(([role, person]) => keyOf(role, person)))].sort(cmp);
  const named = noteNames(String(stage.note || ''), (stage.people || []).filter(([role]) => !role.startsWith('#')).map(([, p]) => p));
  const castNames = [...new Set((stage.people || []).filter(([role]) => role === '出演').map(([, p]) => p))];
  const cast = stage.cast_text ? castImportance(stage.cast_text, castNames) : null;
  const factor = k => {
    const role = k.slice(0, k.indexOf('\u0000')), person = k.slice(k.indexOf('\u0000') + 1);
    let f = (role.startsWith('#') ? 1 : importanceOf(role, person, cast)) * (1 + INTEREST_PRIOR_BOOST * Math.max(prior.get(k)?.[1] || 0, 0));
    if (!role.startsWith('#') && named.has(person)) f *= INTEREST_NOTE_BOOST;
    return f;
  };
  // (3) 興味なしとの比べは、割ったあとで掛ける（#109）。割る前に掛けると、興味なしにも同じ割合でいる人・種類
  // ばかりの公演（1 人だけ・全員が同じ公演に出ている など）では割り直しで打ち消され、興味なしが何件あっても弱まらなかった。
  // 割ったあとに掛けるので、興味なしの分はこの公演の重さから引かれるだけで、ほかの人・種類へは回らない
  const ratio = k => { const [yes, no] = contrast.get(k) || [1, 0]; return yes / (yes + no); };
  const people = keys.filter(k => !k.startsWith('#')), kinds = keys.filter(k => k.startsWith('#'));
  const out = new Map();
  const spread = (ks, total) => {
    const fs = ks.map(factor), sum = fs.reduce((a, b) => a + b, 0);
    if (sum > 0) ks.forEach((k, i) => out.set(k, total * fs[i] / sum * ratio(k)));
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

// 1 件の評価の人の鍵（重複なし・並べ替え済み）。裏の答え合わせ（reco-gate.chooseVariant）は同じ評価の行で
// personValues を何十回も呼ぶので、行ごとに 1 回だけ作って覚えておく（#138、CPU）。行の people は作り直さない約束
const KEYS_OF = new WeakMap();
const peopleKeys = r => {
  let keys = KEYS_OF.get(r);
  if (!keys) { keys = [...new Set((r.people || []).map(([role, person]) => role + '\u0000' + person))].sort(cmp); KEYS_OF.set(r, keys); }
  return keys;
};

export function personValues(rated, seeds = [], skip = new Set(), liked = [], disliked = [], ablate = {}) {
  // person-ordinal-v3: a rating's place among the user's own ratings on the
  // same scale, ((lower) + ½ (equal)) / n − ½, times √12.
  // 同じ尺度の中の「下の数」と「同じ数」は、値ごとの数から出す（前は 1 件ごとに全件と比べていた。結果は同じ。#138）
  // 作品ごとに分けた観劇の評価は、作品の数で割った重み（r.share）で順位に入れる（オムニバス 1 公演が分母を何件ぶんも動かさない）
  const byScale = new Map();
  for (const r of rated) {
    const [value, levels] = gradeOf(r.verdict);
    if (!byScale.has(levels)) byScale.set(levels, {n: 0, count: new Map()});
    const sc = byScale.get(levels), share = r.share ?? 1;
    sc.n += share; sc.count.set(value, (sc.count.get(value) || 0) + share);
  }
  const rankOf = new Map();                    // levels -> value -> [below, same]
  for (const [levels, {count}] of byScale) {
    const m = new Map();
    for (const v of count.keys()) {
      let below = 0;
      for (const [w, c] of count) if (w < v) below += c;
      m.set(v, [below, count.get(v)]);
    }
    rankOf.set(levels, m);
  }
  const tally = new Map();
  const pieces = new Map();                    // occasion -> key -> [z の和, 出た作品の数]
  for (const r of rated) {
    const [value, levels] = gradeOf(r.verdict);
    const [below, same] = rankOf.get(levels).get(value);
    const z = ((below + 0.5 * same) / byScale.get(levels).n - 0.5) * SQRT12;
    const keys = peopleKeys(r);
    // 詳細: a rating lands mainly on what was good (above the middle) or a
    // trouble (below it), less on what the other side points at.
    const lv = z ? aspectLevels(r.aspects) : {};
    const [troubles, goods] = z ? parseAspects(r.aspects) : [[], []];
    const marked = troubles.length || goods.length;
    if (r.occasion) {
      if (!pieces.has(r.occasion)) pieces.set(r.occasion, new Map());
      const acc = pieces.get(r.occasion);
      for (const k of keys) {
        const a = acc.get(k) || [0, 0];
        a[0] += marked ? z * aspectShare(troubles, goods, k.slice(0, k.indexOf('\u0000')), z > 0, lv) : z; a[1] += 1;
        acc.set(k, a);
      }
      continue;
    }
    for (const k of keys) {
      const t = tally.get(k) || [0, 0, 0];
      t[0] += 1; t[1] += marked ? z * aspectShare(troubles, goods, k.slice(0, k.indexOf('\u0000')), z > 0, lv) : z; t[2] += 1.0;
      tally.set(k, t);
    }
  }
  // 作品ごとに分けた観劇: 人ごとに、出た作品の z の平均を、縮めた件数（pieceWeight）の重みで 1 回だけ足す
  for (const acc of pieces.values()) {
    for (const [k, [sum, m]] of acc) {
      const t = tally.get(k) || [0, 0, 0], wt = pieceWeight(m);
      t[0] += 1; t[1] += (sum / m) * wt; t[2] += wt;
      tally.set(k, t);
    }
  }
  // Seeds: z = SEED_Z with weight w; they add to the weight, not to n.
  const w = SEED_K / (SEED_K + ratingCount(rated));
  for (const r of seeds) {
    const keys = [...new Set((r.people || []).filter(([, person]) => !skip.has(person)).map(([role, person]) => role + '\u0000' + person))].sort(cmp);
    for (const k of keys) {
      const rw = favSpread(k.slice(0, k.indexOf('\u0000')));
      if (!rw) continue;                        // 制作・宣伝・その他の役職からは広げない
      const t = tally.get(k) || [0, 0, 0];
      // 語彙表で広げた題材から拾った公演は、離れるほど弱い（r.w。src/vocab.js）。役職の広げ方の重み（rw）も掛ける
      const sw = r.w ?? 1;
      t[1] += w * FAV_SEED_W * SEED_Z * rw * sw; t[2] += w * FAV_SEED_W * sw;
      tally.set(k, t);
    }
  }
  const values = new Map();
  for (const [k, [cnt, sum, wt]] of tally) values.set(k, [cnt, sum / (wt + CONF_K)]);
  // 興味ありの画面で ✕ を押した公演（disliked のうち strong、reaction.interest=4）は、はっきりした負の手がかり
  const strong = disliked.filter(s => s.strong);
  if (!liked.length && !strong.length) return values;
  // 興味あり: 評価とお気に入りから分かった値（values）を (2) の手がかりにして、1 公演ぶんを割って足す。
  const contrast = interestContrast(liked, disliked, skip);
  for (const s of liked) {
    for (const [k, share] of ablate.split ? evenShares(s, skip) : interestShares(s, values, contrast, skip)) {
      const t = tally.get(k) || [0, 0, 0];
      t[1] += w * SEED_Z * share; t[2] += w * share;
      tally.set(k, t);
    }
  }
  // 起案者の指示 2026-10-18「興味の画面でバツを押された場合は、興味なしか視界にも入れたくないから結構マイナスと判断できる」。
  // 興味あり 1 公演と同じ重さ（REJECT_W）を、向きだけ逆にして人・種類に割る。好きと分かっている人へ多めに配る (2) は
  // 使わない（好きな人ほど強く下げることになる）。ふつうの興味なし（interest=0）は、これまでどおり比べ (3) にだけ使う
  for (const s of strong) {
    for (const [k, share] of interestShares(s, new Map(), new Map(), skip)) {
      const t = tally.get(k) || [0, 0, 0];
      t[1] -= w * SEED_Z * REJECT_W * share; t[2] += w * REJECT_W * share;
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
  // 細かい題材の好みを語彙表の上位へ積み上げ、上位の下の言葉の公演にも効かせる（src/vocab.js rolledThemeWords）。
  // 理由には上位の名前を出す（起案者の指示 2026-10-18「それなら SF って出しちゃっていいよ」）。1 公演 1 つの上位につき 1 回
  if (!ablate.rollup) {
    const themeValues = new Map();
    for (const [k, nv] of values) if (k.startsWith(THEME_AXIS + '\u0000')) themeValues.set(k.slice(THEME_AXIS.length + 1), nv);
    const wider = rolledThemeWords(themeValues);
    if (wider.size) {
      const best = new Map();                 // sid + 上位 -> 寄与
      for (const [, word, sid, roleW, group] of await postingsFor([...wider.keys()].sort(cmp).map(w => [THEME_AXIS, w]))) {
        const [label, n, value] = wider.get(word);
        const contrib = round6(value * (roleW * mult(group)));
        const key = sid + '\u0000' + label;
        if (contrib && !(Math.abs(best.get(key)?.[0] ?? 0) >= Math.abs(contrib))) best.set(key, [contrib, THEME_AXIS, label, n, group, sid]);
      }
      for (const [contrib, role, label, n, group, sid] of [...best.values()].sort((x, y) => cmp(x[5], y[5]) || cmp(x[2], y[2]))) {
        if (!byStage.has(sid)) byStage.set(sid, []);
        // 同じ名前の言葉（「SF」）が公演に付いていて自分の値で効いているなら、上位としては足さない
        if (byStage.get(sid).some(p => p[1] === role && nz(p[2]) === nz(label))) continue;
        byStage.get(sid).push([contrib, role, label, n, group]);
      }
    }
  }
  // 1 段だけ広げる: 好きな人（値が正）が出る公演の共演者・作り手
  const via = new Map();                       // key -> name of the liked person they work with
  if (expand?.peopleFor && !ablate.expand) {
    // 広げる元は、本人が評価した公演・興味ありを押した公演にいる人だけ。お気に入りの公演の共演者などは、それ自体が
    // お気に入りの名前から 1 段広げた人なので、そこからさらに広げると 2 段先になり、理由に登録していない人が
    // 「好きな○○」と出ていた（起案者の指摘 2026-10-18「堂本光一と登録したら『好きな諸鍛冶裕太と同じ公演に関わる人』と出た」）
    const direct = new Set([...rated, ...liked].flatMap(r => (r.people || []).filter(([, p]) => !skip.has(p)).map(([role, p]) => role + '\u0000' + p)));
    const top = [...values.entries()].filter(([k, [, v]]) => v > 0 && !k.startsWith('#') && direct.has(k)).sort((a, b) => (b[1][1] - a[1][1]) || cmp(a[0], b[0])).slice(0, EXPAND_PEOPLE);
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
export async function seedsFromFavourites({postingsFor, peopleFor, stagesMatching, stagesByWords}, favourites) {
  const names = [...new Set(favourites.filter(f => SEED_KINDS.includes(f.kind)).map(f => f.name))].sort(cmp).slice(0, MAX_SEED_FAVS);
  // 「堂本 光一」と空白を入れて登録しても、索引の「堂本光一」で引く（お気に入りの一覧は空白を詰めて当てるので公演が出るのに、
  // 推薦の種は名前そのままで引いていて 0 件になっていた。2026-10-18、fix-fav-only-no-reco）。build_recommend_index と同じ
  const lookup = new Map();                    // 索引で引く名前 -> 登録した名前
  for (const name of names) for (const n of [name, personKey(name)]) if (n && !lookup.has(n)) lookup.set(n, name);
  const sids = new Map(), favOf = new Map();   // stage_id -> 種の重さ（名前で当たったものは 1）／登録した名前（理由に書く）
  const note = (sid, name) => { if (!favOf.has(sid)) favOf.set(sid, new Set()); favOf.get(sid).add(name); };
  const put = (sid, x) => { if (!(sids.get(sid) >= x)) sids.set(sid, x); };
  if (names.length) {
    // 役職で絞った人（f.roles、lists.rolesAllowed。q-favourite-homonym）は、その役職の札だけを引く
    const allowed = new Map(favourites.filter(f => f.roles).map(f => [f.name, f.roles]));
    const fits = (name, role) => { const a = allowed.get(name); return !a || a.has(role); };
    const keys = [...lookup.keys()].flatMap(name => SEED_ROLES.filter(role => fits(lookup.get(name), role)).map(role => [role, name])).sort(cmpTuple);
    for (const r of await postingsFor(keys)) { put(r[2], 1); note(r[2], lookup.get(r[1]) ?? r[1]); }
  }
  // Troupes / producers by the producing company, works by the title
  // (recommend2.declared_hits' rules on normalised text).
  const back = new Map();
  const pick = (kinds, norm) => {
    const out = new Set();
    for (const f of favourites.filter(f => kinds.includes(f.kind))) { const x = norm(f.name); if (x.length >= 2) { out.add(x); if (!back.has(x)) back.set(x, f.name); } }
    return [...out].sort(cmp).slice(0, MAX_SEED_FAVS);
  };
  const groups = pick(SEED_GROUP_KINDS, nz), works = pick(SEED_WORK_KINDS, titleKey), subjects = pick(SEED_THEME_KINDS, nz);
  if ((groups.length || works.length || subjects.length) && stagesMatching) {
    const labels = new Map();
    for (const sid of await stagesMatching(groups, works, subjects, [], labels)) {
      put(sid, 1);
      for (const x of labels.get(sid) || []) note(sid, back.get(x) ?? x);
    }
  }
  // 題材は語彙表で下位と関連にも広げ、#題材 の言葉と丸ごと一致で当てる。重さは離れるほど弱い（src/vocab.js。
  // 「科学」→ SF 0.6・宇宙 0.35・近未来 0.3…）。種の数に上限があるので、重い公演から取る。
  // 広げた言葉で当たった公演も、理由には登録した題材の名前を書く（wideOf: 広げた言葉 -> 登録した題材の語）
  const wider = new Map(), wideOf = new Map();
  for (const t of subjects) for (const [w, x] of themeExpansion(t).weights) {
    if (!(wider.get(w) >= x)) { wider.set(w, x); wideOf.set(w, t); }
  }
  if (wider.size && stagesByWords) {
    const labels = new Map();
    for (const [sid, x] of await stagesByWords(wider, labels)) {
      put(sid, x);
      for (const w of labels.get(sid) || []) { const s = wideOf.get(w) ?? w; note(sid, back.get(s) ?? s); }
    }
  }
  const skip = new Set(lookup.keys());
  const chosen = [...sids].sort((a, b) => (b[1] - a[1]) || cmp(a[0], b[0])).slice(0, MAX_SEED_STAGES);
  if (!chosen.length) return {seeds: [], skip};
  const people = await peopleFor(chosen.map(([sid]) => sid));
  return {seeds: chosen.filter(([sid]) => people.get(sid)?.length)
    .map(([sid, x]) => ({stage_id: sid, people: people.get(sid), fav: [...(favOf.get(sid) || [])].sort(cmp), ...(x < 1 ? {w: x} : {})})), skip};
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

// D1 の .raw() は行を列の並びの配列で返す（列名を毎行持たないので、受け取る JSON が小さく、読むのも速い。#138）。
// 試験の SQLite の代わり（raw の無いもの）では、all() の行を同じ並びの配列にする
const rowsOf = async (stmt, cols) => (typeof stmt.raw === 'function'
  ? stmt.raw()
  : (await stmt.all()).results.map(r => cols.map(c => r[c])));

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
        const results = await rowsOf(db.prepare(sql).bind(ver, ...chunk.flat()), ['role', 'person', 'stage_id', 'role_w', 'role_group']);
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) out.push(r);
      }
      return out;
    },
    async stagesFor(ids) {
      const map = new Map();
      for (let i = 0; i < ids.length; i += IDS_PER_QUERY) {
        const chunk = ids.slice(i, i + IDS_PER_QUERY);
        const results = await rowsOf(db.prepare('SELECT stage_id,start,end,tour FROM rec_stage WHERE ver=? AND stage_id IN ('
          + chunk.map(() => '?').join(',') + ')').bind(ver, ...chunk), ['stage_id', 'start', 'end', 'tour']);
        counter.rows += results.length; counter.queries += 1;
        for (const [sid, start, end, tour] of results) map.set(sid, {start, end, tour});
      }
      return map;
    },
    // labels（任意の Map）: stage_id -> 当たった語（groups・works・subjects・exact の値）。理由に登録した名前を書くため。
    // 読む行は前と同じ（列を 1〜2 つ足すだけ）。exact は語彙表で広げた #題材 の言葉（丸ごと一致）
    async stagesMatching(groups, works, subjects = [], exact = [], labels = null) {
      const out = new Set();
      const label = (sid, x) => { if (!labels) return; if (!labels.has(sid)) labels.set(sid, new Set()); labels.get(sid).add(x); };
      // Troupes / works: one pass over this version's stages (no index on these).
      const conds = [...groups.map(() => 'instr(gkey,?)>0'), ...works.map(() => 'instr(tkey,?)>0')];
      if (conds.length) {
        const {results} = await db.prepare(`SELECT stage_id,gkey,tkey FROM rec_stage WHERE ver=? AND (${conds.join(' OR ')})`).bind(ver, ...groups, ...works).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) {
          out.add(r.stage_id);
          for (const g of groups) if (String(r.gkey || '').includes(g)) label(r.stage_id, g);
          for (const t of works) if (String(r.tkey || '').includes(t)) label(r.stage_id, t);
        }
      }
      // Subjects: #題材 words that contain the name or are contained in it (net_c.declared_hits).
      if (subjects.length) {
        const cond = subjects.map(() => '(instr(person,?)>0 OR (length(person)>=2 AND instr(?,person)>0))').join(' OR ');
        const {results} = await db.prepare(`SELECT DISTINCT stage_id,person FROM rec_credit WHERE ver=? AND role=? AND (${cond})`)
          .bind(ver, THEME_AXIS, ...subjects.flatMap(t => [t, t])).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) {
          out.add(r.stage_id);
          const p = String(r.person || '');
          for (const t of subjects) if (p.includes(t) || (Array.from(p).length >= 2 && t.includes(p))) label(r.stage_id, t);
        }
      }
      for (let i = 0; i < exact.length; i += IDS_PER_QUERY) {
        const chunk = exact.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare(`SELECT DISTINCT stage_id,person FROM rec_credit WHERE ver=? AND role=? AND person IN (${chunk.map(() => '?').join(',')})`)
          .bind(ver, THEME_AXIS, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) { out.add(r.stage_id); label(r.stage_id, String(r.person || '')); }
      }
      return [...out];
    },
    /** #題材 の言葉（丸ごと一致）→ 重さ の Map から、stage_id → 当たった言葉のいちばん重い値。
     *  labels（任意の Map）: stage_id -> 当たった言葉（理由に登録した題材の名前を書くため） */
    async stagesByWords(weights, labels = null) {
      const out = new Map(), words = [...weights.keys()].sort(cmp);
      for (let i = 0; i < words.length; i += IDS_PER_QUERY) {
        const chunk = words.slice(i, i + IDS_PER_QUERY);
        const {results} = await db.prepare(`SELECT stage_id,person FROM rec_credit WHERE ver=? AND role=? AND person IN (${chunk.map(() => '?').join(',')})`)
          .bind(ver, THEME_AXIS, ...chunk).all();
        counter.rows += results.length; counter.queries += 1;
        for (const r of results) {
          const x = weights.get(r.person); if (!(out.get(r.stage_id) >= x)) out.set(r.stage_id, x);
          if (labels) { if (!labels.has(r.stage_id)) labels.set(r.stage_id, new Set()); labels.get(r.stage_id).add(r.person); }
        }
      }
      return out;
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
