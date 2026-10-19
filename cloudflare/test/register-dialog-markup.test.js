import {test} from 'node:test';
import assert from 'node:assert/strict';
import {registerScreen} from '../src/screens/settings.js';

test('registration HTML contains a complete, initially closed detail-search dialog', async () => {
  const statement = {bind() {return this}, async all() {return {results: []}}};
  const ctx = {db: {prepare: () => statement}, uid: 'fixture', today: '2026-10-19', now: Date.parse('2026-10-19T00:00:00Z')};
  const {body_html: html} = await registerScreen({}, ctx);
  assert.match(html, /data-open-dialog="register-search-dialog"/);
  assert.match(html, /<dialog id="register-search-dialog"[^>]*>/);
  assert.doesNotMatch(html, /<dialog[^>]*\bopen\b/);
  const content = html.slice(html.indexOf('<dialog id="register-search-dialog"'), html.indexOf('</dialog>'));
  for (const name of ['q', 'group', 'venue', 'schedule_year', 'schedule_month', 'schedule_day']) {
    assert.equal((content.match(new RegExp(`name="${name}"`, 'g')) || []).length, 1, name);
  }
  assert.doesNotMatch(content, /schedule_precision|指定の細かさ/);
  for (const part of ['year', 'month', 'day']) {
    const input = content.match(new RegExp(`<input name="schedule_${part}"[^>]*>`))[0];
    assert.doesNotMatch(input, /required|disabled/);
  }
  assert.doesNotMatch(content, /hidden/);
  assert.match(content, /検索する/); assert.match(content, /条件を入れて/); assert.match(content, /rs-results/);
});
