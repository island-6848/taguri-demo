// お気に入りの名前を足すと、画面を読み込み直す（web/app.js waitJob）。そのとき開いていた枠（details#names）を
// URL の # で覚えて開き直す決まりだが、開く処理は app.js の読み込みのとき 1 度だけで、画面の中身が入る前に
// 走るので効かず、名前を 1 つ足すたびに枠が畳まれていた（#134 の通し検証）。画面を描いたあとの scrollToHash で開く。
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
const make = document => new Function('document', `${body('scrollToHash')}; return scrollToHash;`)(document);

test('the # of the URL opens the <details> it names after the screen is drawn', () => {
  const scrolled = [];
  const el = {details: {tagName: 'DETAILS', open: false, scrollIntoView() { scrolled.push('names'); }},
    section: {tagName: 'SECTION', scrollIntoView() { scrolled.push('cal'); }}};
  const go = make({getElementById: id => ({names: el.details, cal: el.section})[id] || null});
  go('#names');
  assert.equal(el.details.open, true);
  go('#cal');
  assert.equal(el.section.open, undefined);   // only <details> is opened
  assert.deepEqual(scrolled, ['names', 'cal']);
  assert.doesNotThrow(() => { go('#nothing'); go(''); go(null); });
  // loadScreen calls it after renderScreen, also on the first load (location.hash)
  assert.match(APP, /loadScreen\(path, location\.search\.replace\(\/\^\\\?\/, ""\), location\.hash\)/);
});
