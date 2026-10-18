// 画面の中のリンクのうち、サーバーの別のページ（/login・/terms・/privacy・/migration-data/ など）へ行くものは、
// 画面の中で描かずにブラウザーに任せる（web/app.js isInternalPath）。#134 の通し検証で、アカウントの画面の
// 「アカウントを削除する」（/login?purpose=delete）を押すと「見つかりません」になると分かった。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const APP = readFileSync(new URL('../../web/app.js', import.meta.url), 'utf8');
function body(name) {
  const start = APP.indexOf(`function ${name}(`);
  let depth = 0;
  for (let i = APP.indexOf('{', start); i < APP.length; i++) {
    if (APP[i] === '{') depth++;
    else if (APP[i] === '}' && --depth === 0) return APP.slice(start, i + 1);
  }
  throw new Error(name);
}
const pagePaths = APP.match(/^const PAGE_PATHS = .*$/m)[0];
const isInternalPath = new Function(`${pagePaths}\n${body('isInternalPath')}; return isInternalPath;`)();

test('links to the server pages leave the single-page app; the screens stay inside', () => {
  for (const p of ['/login', '/login/', '/terms', '/privacy', '/about', '/migration-data/', '/oauth/calendar'])
    assert.equal(isInternalPath(p), false, p);
  for (const p of ['/', '/rate', '/recommend/interest', '/records/works', '/account', '/settings', '/search', '/loginx', '/termsheet'])
    assert.equal(isInternalPath(p), true, p);
  for (const p of ['/api/screen/rate', '/img/a.jpg', '/vendor/d3.js', '/export.json']) assert.equal(isInternalPath(p), false, p);
});

test('every server page linked from a screen is one isInternalPath lets go', () => {
  const src = ['account', 'evalrec', 'settings'].map(n => readFileSync(new URL(`../src/screens/${n}.js`, import.meta.url), 'utf8')).join('\n');
  const linked = [...src.matchAll(/href="(\/(?:login|terms|privacy|migration-data)[^"#?]*)/g)].map(m => m[1]);
  assert.ok(linked.length >= 4, linked.join(','));
  for (const p of linked) assert.equal(isInternalPath(p), false, p);
});
