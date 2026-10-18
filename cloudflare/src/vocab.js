// 題材の語彙表（src/vocab/concepts.json）で、お気に入りの題材を下位・関連の言葉に広げる。
// 起案者の指摘（2026-10-18）「科学って幅広くて結構粗い粒度だよね。近未来とか、SF とかも「科学」で
// 引っかかってほしい」。作品側の #題材 は読み取りのままにし、お気に入りの側で広げる（D1 の書き込みが
// 増えず、語彙表を直せば索引を作り直さずに効く）。
//   概念の名前と同義語（same）を登録したとき: その概念と下位すべての言葉に広げる（「科学」→ SF・宇宙・ロボット…）
//   概念の言葉（words）を登録したとき: 同じ概念の言葉どうしは仲間で、一種ではないので関連として扱う（「宇宙人」→ 宇宙船）
//   narrow: 下位の言葉。一種なので、お気に入り一覧にも出す
//   related: 関連の概念とその下位・仲間の言葉。一種ではないので推薦の種にだけ使う
//   weights: 言葉 → 推薦の種の重さ。離れるほど弱い（起案者の指示 2026-10-18「子 0.6、孫 0.35 のような強弱は入れたい」）
// 広げた言葉は #題材 の言葉と丸ごと一致したときだけ当てる。部分一致にすると「ループ」が「コーラスグループ」に当たる。
import VOCAB from './vocab/concepts.json' with {type: 'json'};

const nz = s => String(s ?? '').normalize('NFKC').replaceAll(' ', '').replaceAll('　', '').toLowerCase();

// 下位へ 1 段ごとの重さ（4 段目より下は最後の値）と、関連に掛ける重さ
export const DEPTH_W = [1, 0.6, 0.35, 0.2], RELATED_W = 0.3, RELATED_FROM_DEPTH = 1;
const depthW = d => DEPTH_W[Math.min(d, DEPTH_W.length - 1)];

const CONCEPTS = VOCAB.concepts;
const byName = new Map(), byWord = new Map();   // 正規化した名前・同義語 → 概念／正規化した言葉 → それを持つ概念
const children = new Map(), related = new Map();
const add = (m, k, v) => { if (!m.has(k)) m.set(k, []); m.get(k).push(v); };
for (const [name, c] of Object.entries(CONCEPTS)) {
  for (const w of [name, ...(c.same || [])]) add(byName, nz(w), name);
  for (const w of c.words || []) add(byWord, nz(w), name);
  for (const b of c.broader || []) add(children, b, name);
  for (const r of c.related || []) { add(related, name, r); add(related, r, name); }   // 関連は向きを持たない
}

/** 概念 → 段の数。下位をたどり、同じ概念に別の道で着いたら近いほうを取る。 */
const below = (name, d0 = 0) => {
  const out = new Map([[name, d0]]), todo = [name];
  while (todo.length) {
    const n = todo.shift();
    for (const ch of children.get(n) || []) if (!out.has(ch)) { out.set(ch, out.get(n) + 1); todo.push(ch); }
  }
  return out;
};
const wordsOf = n => [n, ...(CONCEPTS[n]?.same || []), ...(CONCEPTS[n]?.words || [])].map(nz);

const memo = new Map();
/** 登録した題材の言葉 → {narrow, related, weights}（正規化した言葉。登録した言葉そのものは含めない）。表に無ければ空。 */
export function themeExpansion(word) {
  const d = nz(word);
  if (memo.has(d)) return memo.get(d);
  const weights = new Map(), narrow = new Set(), rel = new Set();
  const put = (w, x, isNarrow) => {
    if (w === d) return;
    if (!(weights.get(w) >= x)) weights.set(w, x);
    if (isNarrow) narrow.add(w);
  };
  const own = new Map();                                   // 概念 → 段
  for (const n of byName.get(d) || []) for (const [c, k] of below(n)) if (!(own.get(c) <= k)) own.set(c, k);
  for (const [c, k] of own) for (const w of wordsOf(c)) put(w, depthW(k), true);
  // 関連: 広げた概念のうち 1 段下まで（と、言葉として持つ概念）の関連先とその下位。深い所の関連までたどると、
  // 「科学」→ 終末・ディストピア（孫）〔関連〕戦争 → 戦後 のように、登録した言葉と関係の薄い公演が種になる
  const from = new Set([...[...own].filter(([, k]) => k <= RELATED_FROM_DEPTH).map(([c]) => c), ...(byWord.get(d) || [])]);
  for (const n of from) for (const r of related.get(n) || []) for (const [c, k] of below(r))
    if (!own.has(c)) for (const w of wordsOf(c)) if (!narrow.has(w)) { rel.add(w); put(w, RELATED_W * depthW(k), false); }
  // 仲間: 言葉として登録した概念の、ほかの言葉
  for (const n of byWord.get(d) || []) if (!own.has(n))
    for (const w of wordsOf(n)) if (!narrow.has(w) && w !== d) { rel.add(w); put(w, RELATED_W, false); }
  for (const w of narrow) rel.delete(w);
  const out = {narrow, related: rel, weights};
  memo.set(d, out);
  return out;
}

/** 概念 → 上位の概念と段の数（自分は 0）。別の道で着いたら近いほう。 */
const above = name => {
  const out = new Map([[name, 0]]), todo = [name];
  while (todo.length) {
    const n = todo.shift();
    for (const b of CONCEPTS[n]?.broader || []) if (!out.has(b)) { out.set(b, out.get(n) + 1); todo.push(b); }
  }
  return out;
};

// 下から上への積み上げ（起案者の指示 2026-10-18「仕組みの案の 1,2 どっちもやりたい」）。評価から分かった細かい題材の好み
// （宇宙船・ロボット・タイムスリップ）を、語彙表の上位（SF）へ離れるほど弱く配る。1 つの枝だけで上位を決めると言い過ぎに
// なるので、上位とその下の **ROLLUP_MIN_BRANCHES 個以上の概念** で同じ向きの好みがあるときだけ上位の好みにする
// （Ziegler ら 2004・Kanagal ら 2012 の、分類の木で好みを上へ伝える考え方。dec-theme-rollup）
export const ROLLUP_MIN_BRANCHES = 3;

/**
 * 題材の言葉 → [件数, 値]（personValues の #題材 の行）から、上位の好みを積み上げ、その下の言葉へ広げる。
 * 返すのは 言葉 → [上位の概念の名前, 件数, 値]。値は上位の好み × 離れ具合（DEPTH_W）。
 * **細かい好みが勝つ**: 自分の値を持つ言葉には広げない。上位が二つ以上当たる言葉は、いちばん重いもの（ふつうは近い上位）だけ。
 */
export function rolledThemeWords(themeValues) {
  const agg = new Map();                    // 上位 → 概念 → {d, vs: [値...], n}
  for (const [w, [n, v]] of themeValues) {
    if (!v) continue;
    for (const c of new Set([...(byName.get(w) || []), ...(byWord.get(w) || [])])) {
      for (const [a, d] of above(c)) {
        if (!agg.has(a)) agg.set(a, new Map());
        const m = agg.get(a);
        if (!m.has(c)) m.set(c, {d, vs: [], n: 0});
        m.get(c).vs.push(v); m.get(c).n += n;
      }
    }
  }
  const out = new Map();
  for (const [a, m] of agg) {
    const branch = [...m.values()].map(({d, vs, n}) => [depthW(d) * vs.reduce((x, y) => x + y, 0) / vs.length, n]);
    const pos = branch.filter(([b]) => b > 0).length, neg = branch.filter(([b]) => b < 0).length;
    if (Math.max(pos, neg) < ROLLUP_MIN_BRANCHES || pos === neg) continue;
    const va = branch.reduce((x, [b]) => x + b, 0) / branch.length;
    const n = branch.reduce((x, [, k]) => x + k, 0);
    if (!va) continue;
    const ws = new Map([[nz(a), 1], ...[...themeExpansion(a).weights].filter(([w]) => themeExpansion(a).narrow.has(w))]);
    for (const [w, x] of ws) {
      if (themeValues.has(w)) continue;
      const val = va * x;
      if (!out.has(w) || Math.abs(val) > Math.abs(out.get(w)[2])) out.set(w, [a, n, val]);
    }
  }
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
