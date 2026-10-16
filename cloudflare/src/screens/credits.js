// Reading credit fields into (role, person) pairs: a port of
// tools/review/measure_nets.parse_credits and the helpers it uses. Python's
// re on str treats \s as Unicode whitespace and \d as any Nd digit; the
// patterns below spell those out (WS, \p{Nd}) and use the u flag so that
// lengths count code points as Python does.
import {WS, cmp} from './py.js';

/** str.strip(chars) */
function stripChars(s, chars) {
  const a = Array.from(s);
  let i = 0, j = a.length;
  while (i < j && chars.includes(a[i])) i++;
  while (j > i && chars.includes(a[j - 1])) j--;
  return a.slice(i, j).join('');
}
const WS_CHARS = new RegExp(`^[${WS}]$`, 'u');
const isSpace = ch => WS_CHARS.test(ch);
/** str.strip() / str.rstrip() */
const pyStrip = s => { const a = Array.from(s); let i = 0, j = a.length; while (i < j && isSpace(a[i])) i++; while (j > i && isSpace(a[j - 1])) j--; return a.slice(i, j).join(''); };
const pyRstrip = s => { const a = Array.from(s); let j = a.length; while (j > 0 && isSpace(a[j - 1])) j--; return a.slice(0, j).join(''); };

/** str.splitlines() */
export function splitlines(s) {
  const parts = String(s).split(/\r\n|[\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]/u);
  if (parts.length && parts[parts.length - 1] === '') parts.pop();
  return parts;
}

/** measure_nets.norm */
export const norm = s => pyStrip(String(s || '').normalize('NFKC'));

const S = `[${WS}]`, NS = `[^${WS}]`;
const PAREN = /[（(][^）)]*[）)]/gu;
const SPLIT = /[、,，／/\n]/gu;
const MIDDOT_KANJI = /(?<=[一-龥])・(?=[一-龥])/gu;
const PAIRS = new RegExp(`([^${WS}　：:]{1,12})[：:][${WS}　]*([^：:]{2,40}?)(?=(?:[^${WS}　：:]{1,12}[：:])|$)`, 'gu');
const BRACKET = new RegExp(`[【［《]${S}*([^】］》]{1,12})${S}*[】］》]${S}*([^【［《\\n]{2,60})`, 'gu');
const ROLE_LINE = new RegExp(`^([^${WS}　]{1,14})[${WS}　]+(.+)$`, 'u');
const NOT_NAME = new RegExp(`(\\p{Nd}{4}年|\\p{Nd}+月|\\p{Nd}+日|[都道府県]${S}|劇場|ホール|シアター|`
  + `^[▶●○・\\-—=]|^[A-Z ]{3,}$|上演|公演$|チケット|料金)`, 'u');
// measure_nets._ROLE_PREFIX: 役職の語の後ろに区切りがあるときだけ外す（「作間龍斗」を「間龍斗」にしない）
const ROLE_PREFIX = new RegExp(`^(脚色|翻訳|上演台本|原案|原作|作|演出|振付|訳)[${WS}　:：・=|]+`, 'u');
// `.*$` in Python also stops before a final newline.
const NOTE = /[※*＊][^\n]*(?=\n?$)/u;
const LEAD_TAG = new RegExp(`^[【［《][^】］》]{1,20}[】］》][${WS}　]*`, 'u');
const HEAD = new RegExp(`^[${WS}　]*([^${WS}　：:]{2,14})[：:][${WS}　]*$`, 'u');

/** measure_nets.ROLE_ALIAS */
const ROLE_ALIAS = {'作': '脚本', '訳': '翻訳', '舞台美術': '美術', '衣装': '衣裳',
  '照明デザイン': '照明', '音響効果': '音響', '美術デザイン': '美術'};
/** measure_nets.ROLE_VOCAB */
export const ROLE_VOCAB = new Set([
  '出演', '脚本', '作', '演出', '翻訳', '原作', '原案', '脚色', '上演台本', '訳',
  '音楽', '作曲', '編曲', '音楽監督', '振付', '美術', '舞台美術', '照明', '音響',
  '衣裳', '衣装', 'ヘアメイク', 'メイク', '舞台監督', '演出助手', '舞台監督助手',
  '宣伝美術', '宣伝写真', '写真', '映像', '制作', 'プロデューサー', '企画', '主催',
  '技術監督', '小道具', '大道具', '殺陣', '方言指導', '歌唱指導', '演奏', '指揮',
  '宣伝', '票券', '協力', '製作', '指導', 'コーディネーター', 'オーケストラ',
  'アクション', 'マジック', 'マニピュレーター', 'ピアノ', '台本', '作詞', '潤色',
  'オペレーション', 'デスク', 'プロダクション', 'コンダクター', 'コーディネート',
]);
const len = s => Array.from(s).length;
/** max(words, key=len). Python iterates a set in hash order, so a tie between
 * two words of the same length has no fixed answer there; the code-point
 * smaller one is taken here. Only roles depend on it, never names. */
const longest = words => words.reduce((best, w) => (len(w) > len(best) || (len(w) === len(best) && cmp(w, best) < 0)) ? w : best);

/** measure_nets._clean_role */
export function cleanRole(role) {
  let r = stripChars(norm(role), '　 :：・');
  r = pyStrip(r.replace(/^[■□●◆○◇\-—─・*]+/u, ''));
  r = pyStrip(r.replace(/(デザイン|プラン|ﾃﾞｻﾞｲﾝ)$/u, ''));
  if (ROLE_VOCAB.has(r)) return r;
  const head = [...ROLE_VOCAB].filter(v => r.startsWith(v));
  if (head.length) return longest(head);
  const hit = [...ROLE_VOCAB].filter(v => r.includes(v));
  if (hit.length) return longest(hit);
  return 'スタッフ';
}

/** measure_nets._names */
export function names(text) {
  const out = [];
  text = String(text || '').replace(NOTE, '');
  text = text.replace(PAREN, '');
  for (const part of text.replace(SPLIT, '\n').replace(MIDDOT_KANJI, '\n').split('\n')) {
    let n = norm(part);
    n = n.replace(LEAD_TAG, '');
    // 「役名：名前」「アンサンブル：名前」は、コロンの後ろだけが名前（measure_nets._names と同じ、q-credit-part-names）
    if (n.includes(':')) n = n.slice(n.lastIndexOf(':') + 1);
    n = stripChars(n.replace(ROLE_PREFIX, ''), '　 :：・');
    n = n.replace(new RegExp(`[${WS}　]`, 'gu'), '');
    if (!n || /[【】［］《》]/u.test(n) || ROLE_VOCAB.has(n)) continue;
    if (len(n) >= 2 && len(n) <= 20 && !NOT_NAME.test(n)) out.push(n);
  }
  return out;
}

/** measure_nets.canon_role */
export const canonRole = role => { const r = norm(role); return ROLE_ALIAS[r] ?? r; };

/** measure_nets.parse_credits: sorted, de-duplicated (role, person) pairs. */
export function parseCredits(fields) {
  const out = [];
  const str = v => (v === undefined || v === null || v === '') ? '' : String(v);
  for (const role of ['出演', '脚本', '演出']) {
    for (const n of names(str(fields[role]))) out.push([canonRole(role), n]);
  }
  let last = '';
  for (const raw of splitlines(str(fields['スタッフ']))) {
    const line = pyRstrip(raw);
    if (!pyStrip(line) || NOT_NAME.test(norm(line))) continue;
    const brackets = [...norm(line).matchAll(BRACKET)];
    if (brackets.length) {
      for (const [, role, body] of brackets) {
        last = cleanRole(role);
        for (const n of names(body)) out.push([canonRole(last), n]);
      }
      continue;
    }
    const head = norm(line).match(HEAD);
    if (head) { last = cleanRole(head[1]); continue; }
    const pairs = [...norm(line).matchAll(PAIRS)];
    if (pairs.length) {
      for (const [, role, body] of pairs) {
        last = cleanRole(role);
        for (const n of names(body)) out.push([canonRole(last), n]);
      }
      continue;
    }
    const m = line.match(ROLE_LINE);
    let body;
    if (m && !line.startsWith('　') && !line.startsWith(' ')) { last = cleanRole(m[1]); body = m[2]; } else body = line;
    for (const n of names(body)) out.push([canonRole(last) || 'スタッフ', n]);
  }
  const seen = new Map();
  for (const p of out) seen.set(p[0] + '\u0000' + p[1], p);
  return [...seen.values()].sort((a, b) => cmp(a[0], b[0]) || cmp(a[1], b[1]));
}

/** app.hand_credit_count: people (not role/person pairs) the roster gets. */
export function handCreditCount(fields) {
  if (!fields || !Object.keys(fields).length) return 0;
  return new Set(parseCredits(fields).map(p => p[1])).size;
}
