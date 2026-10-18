// 「観劇記録を追加」の題名の欄に打つと、公演一覧の候補が出る（web/app.js sugWatch）。
// #134 の通し検証で、サービス版では候補が一度も出ないと分かった: 画面の中身は読み込みのあとに fetch で
// 差し込むのに、欄に結ぶのは読み込みのとき 1 度だけで、その時点では欄がまだ無かった。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const APP = readFileSync(new URL('../../web/app.js', import.meta.url), 'utf8');
const body = name => {
  const start = APP.indexOf(`function ${name}(`);
  assert.ok(start >= 0, name);
  let depth = 0;
  for (let i = APP.indexOf('{', start); i < APP.length; i++) {
    if (APP[i] === '{') depth++;
    else if (APP[i] === '}' && --depth === 0) return APP.slice(start, i + 1);
  }
  throw new Error(name);
};

test('every screen put into the page binds the title field, once', () => {
  assert.match(body('renderScreen'), /\bsugWatch\(\)/);
  // 結ぶのは 1 度だけ（同じ欄に 2 度結ぶと、打つたびに候補を 2 回取りに行く）
  const listeners = [];
  const el = () => ({dataset: {}, value: '', addEventListener: (type, fn) => listeners.push(type), replaceChildren() {}});
  const fields = {'w-title': el(), 'sug': el(), 'w-stage': el()};
  const document = {getElementById: id => fields[id] || null};
  const sugWatch = new Function('document', 'sugFetch', `let sugTimer; ${body('sugWatch')}; return sugWatch;`)(document, () => {});
  sugWatch();
  sugWatch();
  assert.deepEqual(listeners, ['input']);
  // 欄の無い画面では何もしない
  const none = new Function('document', `let sugTimer; ${body('sugWatch')}; return sugWatch;`)({getElementById: () => null});
  assert.doesNotThrow(() => none());
});
