// 書体の決まり（web/fonts.css）がどの頁にも届き、指している字のファイルが全部あること。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';

const pub = p => new URL('../public/' + p, import.meta.url).pathname;

test('every page loads fonts.css', () => {
  for (const page of ['index.html', 'login.html', 'terms.html', 'privacy.html', 'oauth-calendar.html']) {
    const html = readFileSync(pub(page), 'utf8');
    assert.match(html, /<link rel="stylesheet" href="\/fonts\.css">/, page);
    // 全角のカッコを表示の直前に半角にする（起案者の指示 2026-10-18）。どの頁も読む
    assert.match(html, /<script src="\/halfwidth\.js"><\/script>/, page);
  }
});

test('each @font-face in fonts.css points at a file that is served', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const urls = [...css.matchAll(/url\((assets\/fonts\/[^)]+)\)/g)].map(m => m[1]);
  const families = new Set([...css.matchAll(/font-family: '([^']+)'/g)].map(m => m[1]));
  assert.deepEqual([...families].sort(), ['Sawarabi Gothic', 'Zen Kaku Gothic New', 'Zen Maru Gothic']);
  assert.ok(urls.length > 400, `${urls.length} files`);
  assert.deepEqual(urls.filter(u => !existsSync(pub(u))), []);
});

// 指定は 5 か所だった。「評価しない」（.rb button.nograde）は星の右端の ✕（.rb .gclr、記号なので書体を決めない）に替わり
// （起案者の指示 2026-10-18「『評価しない』のボタンじゃなくて、星の右端に✕ボタンをつけることでnullにできるようにして」）、
// おすすめ理由の「人物」「形式」（.rs .net）は Zen丸ゴシック 700 に移った（同じ日「…『人物』とか『種類』の文字だけ丸ゴシックにして」）
// 公式サイトの押し口・発売の札は Zen丸ゴシック 700 に移った（起案者の指示 2026-10-18「発売済みなどのマークは…フォントZen丸ゴシックにして」
// 「「公式サイト」って文字と枠線もスミクロにして、Zen丸ゴシック」）。さわらびゴシックはお気に入りの名前の札（.ftag）だけ
test('only the favourite name tags (.ftag) use the accent font', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const uses = [...css.matchAll(/([^{}]+)\{[^}]*font-family:var\(--font-accent\)/g)].map(m => m[1]);
  assert.equal(uses.length, 1);
  assert.ok(uses[0].includes('.ftag'));
  assert.doesNotMatch(uses[0], /nograde|gclr|\.rs \.net|sitebtn|\.pill/);
  assert.doesNotMatch(css, /--font-(action|round)/);
});

test('the reason labels, the official-site button and the sale pill use Zen Maru Gothic 700', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const uses = [...css.matchAll(/([^{}]+)\{([^}]*font-family:var\(--font-maru\)[^}]*)\}/g)];
  assert.equal(uses.length, 1);
  const sel = uses[0][1].replace(/\/\*[\s\S]*?\*\//g, '').trim();
  for (const s of ['.rs .net', '.sitebtn', '.sitelink', '.sale .pill']) assert.ok(sel.includes(s), s);
  assert.match(uses[0][2], /font-weight:700!important/);
  assert.match(css, /--font-maru:"Zen Maru Gothic"/);
  const maru = [...css.matchAll(/@font-face \{ font-family: 'Zen Maru Gothic';[^}]*\}/g)].map(m => m[0]);
  assert.ok(maru.length > 50 && maru.every(f => f.includes('font-weight: 700')), `${maru.length} faces`);
});
