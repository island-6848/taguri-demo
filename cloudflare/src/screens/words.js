// 眺める の「ことばの雲」── 観た舞台のあらすじによく出てくる言葉（起案者の指示 2026-10-24
// 「眺めるページにワードクラウドを表示したい。自分の過去の観た舞台のあらすじからつくる」、見本を見て「OK」）。
//
// 語を切り出す Intl.Segmenter は辞書を引くぶん重いので、Worker（CPU 10 ミリ秒）では動かさない。
// Worker はあらすじの本文を `#figs-src` に入れるだけで、ここ（figs.js から呼ばれ、ブラウザで動く）が
// 数えて並べる。D1 にも Worker の環境にも触らない（scripts/sync_figs.py が public/figs/ へ写す）。
import {E} from './py.js';
import {h2} from './icons.js';

/** あらすじを取れた公演がこれより少ないと、雲は偶然の 1〜2 語で埋まるので出さない */
export const MIN_STAGES = 5;
const TOP = 45;
// どのあらすじにも出る言葉・宣伝の決まり文句は、その人の傾向を表さないので外す
const STOP = new Set(('公演 舞台 上演 作品 物語 演出 出演 劇団 本作 今回 世界 人々 再演 初演 新作 作家 脚本 芝居 演劇 予定 開催 '
  + '会場 劇場 東京 大阪 日本 時代 自分 彼女 人生 二人 一人 存在 最後 最初 全く 様々 互い 自ら 代表 活躍 最高 最新 必見 注目 '
  + '待望 話題 共演 主演 原作 音楽 楽曲 披露 魅力 感動 本格 全国 各地 今年 昨年 当時 現在 一方 一緒 一番 毎日 '
  + 'ステージ シリーズ ミュージカル キャスト スタッフ チケット').split(' '));
// 漢字だけ・片仮名だけ（3 字以上）の語に絞る。品詞を引けないので、送り仮名の付く動詞・形容詞と
// 「と共に」のような言い回しを、この形で落とす（見本で「暮らす」「立ち上がる」が大きく出たため）
const NOUNISH = /^(?:[一-鿿々]+|[゠-ヿ]{3,})$/u;
const ENT = {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' '};

/** 実体参照を戻し、括弧の中（多くは役者の名前）と URL を除く */
export function clean(s) {
  return String(s || '')
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => (e[0] !== '#' ? ENT[e.toLowerCase()] ?? m
      : String.fromCodePoint(parseInt(e[1] === 'x' || e[1] === 'X' ? e.slice(2) : e.slice(1), e[1] === 'x' || e[1] === 'X' ? 16 : 10) || 32)))
    .replace(/[（(][^（()）]{0,40}[）)]/g, ' ').replace(/https?:\/\/\S+/g, ' ');
}

/**
 * [[語, 出てきた公演の数], …]（多い順・同数は五十音順、上位 TOP 語）。1 つの公演のあらすじに
 * 何度出ても 1 と数える ── 長いあらすじ 1 本が雲を占めないように
 */
export function countWords(synopses, Segmenter = globalThis.Intl?.Segmenter) {
  if (!Segmenter) return [];
  const seg = new Segmenter('ja', {granularity: 'word'});
  const df = new Map();
  for (const s of synopses) {
    const seen = new Set();
    for (const {segment: w, isWordLike} of seg.segment(clean(s))) {
      if (isWordLike && w.length >= 2 && NOUNISH.test(w) && !STOP.has(w)) seen.add(w);
    }
    for (const w of seen) df.set(w, (df.get(w) || 0) + 1);
  }
  const all = [...df];
  // 2 公演以上に出た語だけにする。ただし語が少ない人は 1 公演の語も残す（雲が空にならないように）
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

/** 「ことばの雲」の枠。syn: あらすじの本文の並び、nSeen: 観た公演の数、width: 置く画面の幅 */
export function panel(syn, nSeen, width = 760, Segmenter = undefined) {
  const head = h2('chart', 'ことばの雲 ── 観た舞台のあらすじから', syn.length ? `<span class="badge part">${syn.length} 公演のあらすじ</span>` : '');
  if (syn.length < MIN_STAGES) {
    return `<section class="card wide wcard">${head}
<p class="empty">あらすじを取れた公演がまだ ${syn.length} 公演なので、雲を描いていません（${MIN_STAGES} 公演から描きます）。
観た公演の記録を公演の一覧と結び付けると、その公演のあらすじが使われます。</p></section>`;
  }
  const words = countWords(syn, Segmenter);
  if (!words.length) return '';
  const W = Math.max(280, Math.min(Math.round(width), 760)), H = Math.round(W * (W < 500 ? 0.95 : 0.55));
  const placed = layout(words, W, H);
  const texts = placed.map(p => `<text class="w${tone(p.rank)}" x="${(p.x + 3).toFixed(1)}" y="${(p.y + p.size * 0.9).toFixed(1)}" font-size="${p.size}">`
    + `<title>${E(p.word)}：${p.n} 公演のあらすじに出てくる</title>${E(p.word)}</text>`).join('');
  // 置いた語の外枠で切り抜く（渦巻きは横長に広がるので、上下に空きが残らないように）
  const pad = 8, x0 = Math.max(0, Math.min(...placed.map(p => p.x)) - pad), y0 = Math.max(0, Math.min(...placed.map(p => p.y)) - pad);
  const x1 = Math.min(W, Math.max(...placed.map(p => p.x + p.w)) + pad), y1 = Math.min(H, Math.max(...placed.map(p => p.y + p.h)) + pad);
  const vb = [x0, y0, x1 - x0, y1 - y0].map(v => Math.round(v)).join(' ');
  const top = words[0];
  return `<section class="card wide wcard">${head}
<p class="lead"><b>観た舞台のあらすじに、よく出てくる言葉です。</b>大きいほど多くの公演に出てきます（1 つの公演では何度出てきても 1 回と数えます）。
いちばん多いのは <b>「${E(top[0])}」の ${top[1]} 公演</b>です。</p>
<svg class="wcloud" viewBox="${vb}" width="100%" style="max-width:${Math.round(x1 - x0)}px" role="img" aria-label="${E('あらすじによく出てくる言葉: ' + words.slice(0, 10).map(w => w[0]).join('、'))}">${texts}</svg>
<p class="note">観た ${nSeen} 公演のうち、あらすじを取れた ${syn.length} 公演から作っています。人の名前と、「公演」「舞台」のようにどの公演にも出る言葉は除いています。</p></section>`;
}
