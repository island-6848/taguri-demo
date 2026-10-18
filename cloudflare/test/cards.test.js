// src/screens/cards.js fills a stored card exactly as build_cards.compose does, and
// compose equals render_recommend.ticket in every list (test_build_cards.py).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {compose, mytixHtml} from '../src/screens/cards.js';

const here = p => new URL(p, import.meta.url).pathname;
const {golden} = JSON.parse(execFileSync('python3', [here('./screens/recommend_fixture.py')], {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024}));

test('every list gets the same card as the Python screen', () => {
  assert.ok(golden.length >= 12);
  for (const g of golden) {
    const kw = g.mode === 'owned' ? {mytix: mytixHtml(g.sid, g.start, g.end, g.kw.tickets)} : g.kw;
    assert.equal(compose(g.template, g.sid, g.mode, kw), g.html, `${g.sid} ${g.mode} ${JSON.stringify(g.kw)}`);
  }
});

// 起案者の質問 2026-10-18「たまに値段の詳細取得できてない公演があるのはなぜ？」: 作り置きのカードの無い公演の
// カード（fallbackTemplate）にも、公演ページの料金の欄と、絞り込みに使う金額の幅（data-yen）を入れる
test('a card drawn without rec_card carries the price field and data-yen', async () => {
  const {fallbackTemplate} = await import('../src/screens/fallback.js');
  const s = {stage_id: '9', title: '舞台', start: '2026-11-01', end: '2026-11-03', venue: '劇場', fields: {'料金（1枚あたり）': '12,000円 ～ 12,000円\n【発売日】2026/09/01\nS席：12,000円\nA席：8,000円'}};
  const html = fallbackTemplate(s);
  assert.match(html, /<article class="ticket recommend" data-stage="9" data-tours="" data-yen="8000-12000">/);
  assert.match(html, /<span class="price">12,000円 ～ 12,000円\n【発売日】2026\/09\/01\nS席：12,000円\nA席：8,000円<\/span><\/div>/);
  const bare = fallbackTemplate({...s, fields: {}});
  assert.doesNotMatch(bare, /data-yen|class="price"/);
});
