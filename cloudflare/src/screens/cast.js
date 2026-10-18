// render_recommend.split_names: a credits field cut into names in their order
// (the lead first), without "ほか" and the like, and without guide texts and URLs in place of names
// (「スタッフ欄をご覧ください。」, measure_nets.is_guide / credits.isGuide; 起案者の指示 2026-10-18).
import {isGuide, URL_RE} from './credits.js';
const NAME_SEP = /[、，,／/\n\r\t]+|\s{2,}/u;
const ETC = new Set(['他', 'ほか', 'ほか出演者', '他多数']);
// Python's str.strip() whitespace, then the ideographic space.
const strip = s => s.replace(/^[\s\u001c-\u001f\u0085]+|[\s\u001c-\u001f\u0085]+$/gu, '').replace(/^　+|　+$/gu, '');
export function splitNames(raw) {
  const out = [];
  for (let x of String(raw || '').replace(URL_RE, '').split(NAME_SEP)) {
    x = strip(x);
    if (!x || ETC.has(x) || Array.from(x).length > 40 || isGuide(x)) continue;
    if (!out.includes(x)) out.push(x);
  }
  return out;
}
