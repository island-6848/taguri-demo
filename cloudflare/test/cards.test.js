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
