// settings.castBlock / cast.splitNames give render_recommend.cast_block's HTML.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {castBlock} from '../src/screens/settings.js';

const CASES = [{}, {'出演': '甲、乙／丙  丁、ほか'}, {'出演': Array.from({length: 15}, (_, i) => `役者${i}`).join('、'), '演出': '演出家 <A>'},
  {'脚本': 'a、b、c、d、e、f、g、h', '作曲': ' 作曲家 ', '照明': '照明家'}, {'出演': '他'},
  // 案内の文・URL は名前として並べない。出演欄が案内の文だけなら出演の行を出さない（起案者の指示 2026-10-18）
  {'出演': 'スタッフ欄をご覧ください。', '演出': '演出家丙'}, {'出演': '詳細は公式サイトにて、https://musical-za.co.jp/'},
  {'出演': '俳優甲、詳細は後日発表、俳優乙', '脚本': '下記スタッフ欄をご参照ください'}];
test('cast block matches render_recommend.cast_block', () => {
  const py = JSON.parse(execFileSync('python3', ['-c', `
import sys, json; sys.path[:0] = ['tools/review', 'tools/taguri']; import render_recommend as RR
print(json.dumps([RR.cast_block({"fields": f}) for f in json.loads(sys.argv[1])], ensure_ascii=False))`, JSON.stringify(CASES)],
  {cwd: new URL('../..', import.meta.url).pathname, encoding: 'utf8'}));
  CASES.forEach((f, i) => assert.equal(castBlock(f), py[i], JSON.stringify(f)));
});

test('a cast field that is only a guide text shows no 出演 row', () => {
  const html = castBlock({'出演': 'スタッフ欄をご覧ください。', '演出': '演出家丙'});
  assert.doesNotMatch(html, /スタッフ欄|<span class="cl">出演<\/span>/);
  assert.match(html, /<span class="cl">演出<\/span><span class="cv">演出家丙<\/span>/);
  assert.match(castBlock({'出演': '俳優甲、詳細は後日発表、俳優乙'}), /<span class="cv">俳優甲、俳優乙<\/span>/);
});
