// 書体の決まり（web/fonts.css）がどの頁にも届き、指している字のファイルが全部あること。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';

const pub = p => new URL('../public/' + p, import.meta.url).pathname;

test('every page loads fonts.css', () => {
  for (const page of ['index.html', 'login.html', 'terms.html', 'privacy.html', 'oauth-calendar.html']) {
    const html = readFileSync(pub(page), 'utf8');
    assert.match(html, /<link rel="stylesheet" href="\/fonts\.css">/, page);
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

// 起案者の指示（2026-10-18）「おすすめ理由に出てくる丸枠のなかに入ってる『人物』とか『種類』の文字だけ丸ゴシックにして」:
// .rs .net はさわらびゴシックから Zen丸ゴシック 700 に移した。ほかの 4 か所はさわらびゴシックのまま
test('only the four named parts use the accent font', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const uses = [...css.matchAll(/([^{}]+)\{[^}]*font-family:var\(--font-accent\)/g)].map(m => m[1]);
  assert.equal(uses.length, 1);
  for (const sel of ['.sitebtn', '.sale .pill', '.ftag', '.rb button.nograde']) assert.ok(uses[0].includes(sel), sel);
  assert.ok(!uses[0].includes('.rs .net'));
  assert.doesNotMatch(css, /--font-(action|round)/);
});

test('only the reason labels (.rs .net) use Zen Maru Gothic 700', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const uses = [...css.matchAll(/([^{}]+)\{([^}]*font-family:var\(--font-maru\)[^}]*)\}/g)];
  assert.equal(uses.length, 1);
  assert.equal(uses[0][1].replace(/\/\*[\s\S]*?\*\//g, '').trim(), 'html:not([data-font="default"]) .rs .net');
  assert.match(uses[0][2], /font-weight:700!important/);
  assert.match(css, /--font-maru:"Zen Maru Gothic"/);
  const maru = [...css.matchAll(/@font-face \{ font-family: 'Zen Maru Gothic';[^}]*\}/g)].map(m => m[0]);
  assert.ok(maru.length > 50 && maru.every(f => f.includes('font-weight: 700')), `${maru.length} faces`);
});
