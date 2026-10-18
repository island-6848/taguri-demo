// 題材の語彙表（src/vocab/concepts.json）で、お気に入りの題材を下位・関連の言葉に広げる。
// 起案者の指摘（2026-10-18）「科学って幅広くて結構粗い粒度だよね。近未来とか、SF とかも「科学」で
// 引っかかってほしい」。作品側の #題材 は読み取りのままにし、お気に入りの側で広げる（D1 の書き込みが
// 増えず、語彙表を直せば索引を作り直さずに効く）。
//   narrow: その概念と下位すべての言い換え（「科学」→ SF・宇宙・ロボット…）。一種なので、お気に入り一覧にも出す
//   related: 関連の概念とその下位（「科学」→ 近未来）。一種ではないので推薦の種にだけ使う
// 広げた言葉は #題材 の言葉と丸ごと一致したときだけ当てる。部分一致にすると「ループ」が「コーラスグループ」に当たる。
import VOCAB from './vocab/concepts.json' with {type: 'json'};

const nz = s => String(s ?? '').normalize('NFKC').replaceAll(' ', '').replaceAll('　', '').toLowerCase();

const CONCEPTS = VOCAB.concepts;
const byWord = new Map();                 // 正規化した言葉 → それを言い換えに持つ概念
const children = new Map(), related = new Map();
for (const [name, c] of Object.entries(CONCEPTS)) {
  for (const w of [name, ...(c.words || [])]) {
    const k = nz(w);
    if (!byWord.has(k)) byWord.set(k, []);
    byWord.get(k).push(name);
  }
  for (const b of c.broader || []) {
    if (!children.has(b)) children.set(b, []);
    children.get(b).push(name);
  }
  for (const r of c.related || []) {     // 関連は向きを持たない
    for (const [x, y] of [[name, r], [r, name]]) {
      if (!related.has(x)) related.set(x, []);
      related.get(x).push(y);
    }
  }
}

const below = name => {
  const out = new Set(), todo = [name];
  while (todo.length) {
    const n = todo.pop();
    if (out.has(n)) continue;
    out.add(n);
    todo.push(...(children.get(n) || []));
  }
  return out;
};
const wordsOf = names => new Set([...names].flatMap(n => [n, ...(CONCEPTS[n]?.words || [])]).map(nz));

const memo = new Map();
/** 登録した題材の言葉 → {narrow, related}: 正規化した言葉の Set（登録した言葉そのものは含めない）。表に無ければ空。 */
export function themeExpansion(word) {
  const d = nz(word);
  if (memo.has(d)) return memo.get(d);
  const own = new Set((byWord.get(d) || []).flatMap(n => [...below(n)]));
  const rel = new Set();
  for (const n of own) for (const r of related.get(n) || []) for (const x of below(r)) if (!own.has(x)) rel.add(x);
  const narrow = wordsOf(own), relWords = wordsOf(rel);
  narrow.delete(d);
  for (const w of narrow) relWords.delete(w);
  relWords.delete(d);
  const out = {narrow, related: relWords};
  memo.set(d, out);
  return out;
}

/** 表の誤り（存在しない上位・関連、上位の輪）を並べる。試験と見直しの道具が使う。 */
export function vocabProblems() {
  const out = [];
  for (const [name, c] of Object.entries(CONCEPTS))
    for (const r of [...(c.broader || []), ...(c.related || [])]) if (!CONCEPTS[r]) out.push(`${name}: 「${r}」が表に無い`);
  for (const name of Object.keys(CONCEPTS)) {
    const seen = new Set(), todo = [...(CONCEPTS[name].broader || [])];
    while (todo.length) {
      const n = todo.pop();
      if (n === name) { out.push(`${name}: 上位をたどると自分に戻る`); break; }
      if (seen.has(n)) continue;
      seen.add(n);
      todo.push(...(CONCEPTS[n]?.broader || []));
    }
  }
  return out;
}
