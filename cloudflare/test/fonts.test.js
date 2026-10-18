// 書体の決まり（web/fonts.css）がどの頁にも届き、指している字のファイルが全部あること。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';

const pub = p => new URL('../public/' + p, import.meta.url).pathname;

test('every page loads fonts.css and round-text.js', () => {
  for (const page of ['index.html', 'login.html', 'terms.html', 'privacy.html', 'oauth-calendar.html']) {
    const html = readFileSync(pub(page), 'utf8');
    assert.match(html, /<link rel="stylesheet" href="\/fonts\.css">/, page);
    assert.match(html, /<script src="\/round-text\.js"/, page);
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

test('the round rule comes after the action rule so a round button is Zen Maru', () => {
  const css = readFileSync(pub('fonts.css'), 'utf8');
  const action = css.indexOf('font-family:var(--font-action)!important');
  const round = css.indexOf('font-family:var(--font-round)!important');
  assert.ok(action > 0 && round > action);
});
