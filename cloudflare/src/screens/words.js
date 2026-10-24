// 眺める の「ことばの雲」── 観た舞台のあらすじから読み取ったタグ（題材の語）を、付いている公演の数で大きさを変えて並べる。
// はじめは観た舞台のあらすじの本文を語に切って数えていた（起案者の指示 2026-10-24「眺めるページにワードクラウドを表示したい。
// 自分の過去の観た舞台のあらすじからつくる」）。同じ日に「ワードクラウドはあらすじ抽出でタグに出ている単語リストから構成してほしい」
// で、カードのあらすじの下にハッシュタグで出ている語（records.tagsFor）から作るように変えた。
//
// Worker は公演ごとのタグの並びを `#figs-src` に入れるだけで、ここ（figs.js から呼ばれ、ブラウザで動く）が数えて並べる。
// D1 にも Worker の環境にも触らない（scripts/sync_figs.py が public/figs/ へ写す）。
import {E} from './py.js';
import {h2} from './icons.js';

/** タグのある公演がこれより少ないと、雲は偶然の 1〜2 語で埋まるので出さない */
export const MIN_STAGES = 5;
const TOP = 45;

/**
 * [[語, 付いている公演の数], …]（多い順・同数は五十音順、上位 TOP 語）。tags は公演ごとのタグの並び。
 * 1 つの公演に同じ語が 2 度あっても 1 と数える。2 公演以上に付いた語だけにするが、語が少ない人は 1 公演の語も残す
 */
export function countTags(tags) {
  const df = new Map();
  for (const list of tags) {
    for (const w of new Set((list || []).map(x => String(x || '').trim()).filter(Boolean))) df.set(w, (df.get(w) || 0) + 1);
  }
  const all = [...df];
  const kept = all.filter(([, n]) => n >= 2);
  return (kept.length >= 12 ? kept : all)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ja')).slice(0, TOP);
}

/**
 * 大きい語から中央に置き、渦巻きに沿って重ならない場所を探す。文字の幅は 1 字 = 字の大きさで見積もる
 * （仮名・漢字はほぼ全角。canvas で測らないので Node の試験でも同じ並びになる）
 */
export function layout(words, W, H) {
  const narrow = W < 500, lo = narrow ? 11 : 13, span = narrow ? 22 : 31, step = narrow ? 1.4 : 2.2;
  const hiN = Math.sqrt(words[0]?.[1] || 1), loN = Math.sqrt(words[words.length - 1]?.[1] || 1);
  const placed = [];
  const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  words.forEach(([word, n], rank) => {
    const size = Math.round(lo + (hiN === loN ? 0.5 : (Math.sqrt(n) - loN) / (hiN - loN)) * span);
    const w = [...word].length * size + 6, h = size * 1.15;
    for (let t = 0; t < 4000; t++) {
      const a = t * 0.35, r = step * a;
      const box = {x: W / 2 + r * Math.cos(a) * 1.7 - w / 2, y: H / 2 + r * Math.sin(a) - h / 2, w, h};
      if (box.x < 0 || box.y < 0 || box.x + w > W || box.y + h > H || placed.some(p => hit(p, box))) continue;
      placed.push({...box, word, n, size, rank});
      break;
    }
  });
  return placed;
}

const tone = rank => (rank < 3 ? 0 : rank < 12 ? 1 : rank < 25 ? 2 : 3);

/** 「ことばの雲」の枠。tags: 公演ごとのタグの並び（タグのある公演だけ）、nSeen: 観た公演の数、width: 置く画面の幅 */
export function panel(tags, nSeen, width = 760) {
  const head = h2('chart', 'ことばの雲 ── 観た舞台のタグから', tags.length ? `<span class="badge part">${tags.length} 公演のタグ</span>` : '');
  if (tags.length < MIN_STAGES) {
    return `<section class="card wide wcard">${head}
<p class="empty">あらすじのタグがある公演がまだ ${tags.length} 公演なので、雲を描いていません（${MIN_STAGES} 公演から描きます）。
観た公演の記録を公演の一覧と結び付けると、その公演のあらすじのタグが使われます。</p></section>`;
  }
  const words = countTags(tags);
  if (!words.length) return '';
  const W = Math.max(280, Math.min(Math.round(width), 760)), H = Math.round(W * (W < 500 ? 0.95 : 0.55));
  const placed = layout(words, W, H);
  const texts = placed.map(p => `<text class="w${tone(p.rank)}" x="${(p.x + 3).toFixed(1)}" y="${(p.y + p.size * 0.9).toFixed(1)}" font-size="${p.size}">`
    + `<title>#${E(p.word)}：${p.n} 公演に付いている</title>${E(p.word)}</text>`).join('');
  // 置いた語の外枠で切り抜く（渦巻きは横長に広がるので、上下に空きが残らないように）
  const pad = 8, x0 = Math.max(0, Math.min(...placed.map(p => p.x)) - pad), y0 = Math.max(0, Math.min(...placed.map(p => p.y)) - pad);
  const x1 = Math.min(W, Math.max(...placed.map(p => p.x + p.w)) + pad), y1 = Math.min(H, Math.max(...placed.map(p => p.y + p.h)) + pad);
  const vb = [x0, y0, x1 - x0, y1 - y0].map(v => Math.round(v)).join(' ');
  const top = words[0];
  return `<section class="card wide wcard">${head}
<p class="lead"><b>観た舞台のあらすじから読み取ったタグです。</b>大きいほど多くの公演に付いています。
いちばん多いのは <b>「${E(top[0])}」の ${top[1]} 公演</b>です。</p>
<svg class="wcloud" viewBox="${vb}" width="100%" style="max-width:${Math.round(x1 - x0)}px" role="img" aria-label="${E('あらすじのタグ: ' + words.slice(0, 10).map(w => w[0]).join('、'))}">${texts}</svg>
<p class="note">観た ${nSeen} 公演のうち、あらすじのタグがある ${tags.length} 公演から作っています。</p></section>`;
}
