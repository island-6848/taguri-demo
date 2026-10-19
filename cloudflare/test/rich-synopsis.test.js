// 書式つきのあらすじ（起案者の指示 2026-10-19「凝ってるものはそのまま入力できるようにしたい（中央寄せとか、書体変更のやつ）」）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {RICH, richHtml, richText, synBlock, mergeInfo} from '../src/screens/override.js';

test('only the allowed tags and classes are kept; scripts, styles, events and links are dropped', () => {
  const v = RICH + '<p class="ta-center ff-mincho evil">春の<b>夜</b>に</p><script>alert(1)</script><div style="color:red" onclick="x()">二人は<a href="javascript:x">出会う</a></div><img src=x onerror=y><p class=fs-l>&lt;終&gt;';
  assert.equal(richHtml(v), '<p class="ta-center ff-mincho">春の<b>夜</b>に</p><div>二人は出会う</div><p class="fs-l">&lt;終&gt;</p>');
  assert.equal(richText(v), '春の夜に\n二人は出会う\n<終>');
});

test('the block shows the rich html; other screens get the plain text', () => {
  const ov = {synopsis: RICH + '<p class="ta-center">中央の<br>一行</p>', themes: null};
  const b = synBlock('1', ov);
  assert.match(b, /<div class="txt rich"><p class="ta-center">中央の<br>一行<\/p><\/div>/);
  assert.equal(mergeInfo({title: 't'}, {...ov, info: {}}).synopsis, '中央の\n一行');
  // 書式の無いあらすじは、これまでどおり <p class="txt">
  assert.match(synBlock('1', {synopsis: 'ふつうの文', themes: null}), /<p class="txt">ふつうの文<\/p>/);
});
