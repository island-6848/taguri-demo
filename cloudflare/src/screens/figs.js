// 眺める の重い 2 枚（人の流れ・相関図）は、ブラウザで組み立てる。
//
// Worker Free は 1 回の要求に CPU 10 ミリ秒しか使えない（workers-free-cpu-10ms）。
// 人の流れ（StoryFlow の掃きと詰め）は重い記録で温まっていても約 12 ミリ秒、最初の 1 回は
// 約 80 ミリ秒かかった（dec-records-worker）。そこで Worker は記録（評価した作品と作り手）を
// `#figs-src` に入れて置き場所 `[data-fig]` だけを返し、この module が同じ panel() を
// ブラウザで動かして置き場所を埋める。中身は Python と一字一句同じ（storyline.test.js・
// people.test.js）。この module と import 先は scripts/sync_figs.py が public/figs/ へ写す
// （静的ファイルは Worker の要求にも CPU にも数えられない）。
import {panel as storyline} from './storyline.js';
import {panel as people} from './people.js';
import {panel as words} from './words.js';

// 2 つ目の引数は `#figs-src` の中身全部と、置き場所の幅（ことばの雲が文字の大きさを決めるのに使う）
export const FIGS = {storyline: rated => (rated.length ? storyline(rated) : ''), people: rated => people(rated),
  words: (_rated, src, width) => words(src.tags || [], src.nSeen || 0, width)};

/** Fill every `[data-fig]` under root from `#figs-src`. Returns how many were drawn. */
export function fill(root) {
  const src = root.querySelector('#figs-src');
  if (!src) return 0;
  let data, rated;
  try { data = JSON.parse(src.textContent) || {}; rated = data.rated || []; } catch { return 0; }
  let n = 0;
  for (const box of root.querySelectorAll('[data-fig]')) {
    const make = FIGS[box.dataset.fig];
    let html = '';
    // 枠の左右の余白（約 40px）を引いた幅。測れない所（試験）では既定の幅
    const width = (box.parentElement?.clientWidth || 800) - 40;
    try { html = make ? make(rated, data, width) : ''; } catch { html = ''; }   // **落ちても画面の残りは出す**
    if (html.trim()) n++;
    box.outerHTML = html;
  }
  return n;
}
