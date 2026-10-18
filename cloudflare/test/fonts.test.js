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
  assert.deepEqual([...families].sort(), ['Sawarabi Gothic', 'Zen Kaku Gothic New']);
  assert.ok(urls.length > 300, `${urls.length} files`);
  assert.deepEqual(urls.filter(u => !existsSync(pub(u))), []);
});

// 指定は 5 か所だったが、「評価しない」（.rb button.nograde）は星の右端の ✕（.rb .gclr、記号なので書体を決めない）に替わった
// （起案者の指示 2026-10-18「『評価しない』のボタンじゃなくて、星の右端に✕ボタンをつけることでnullにできるようにして」）
test('only the four named parts use the accent font', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const uses = [...css.matchAll(/([^{}]+)\{[^}]*font-family:var\(--font-accent\)/g)].map(m => m[1]);
  assert.equal(uses.length, 1);
  for (const sel of ['.sitebtn', '.sale .pill', '.ftag', '.rs .net']) assert.ok(uses[0].includes(sel), sel);
  assert.doesNotMatch(uses[0], /nograde|gclr/);
  assert.doesNotMatch(css, /--font-(action|round)/);
});
