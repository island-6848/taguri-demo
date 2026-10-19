import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const source = readFileSync(new URL('../../web/app.js', import.meta.url), 'utf8');
const settle = () => new Promise(resolve => setTimeout(resolve, 0));

test('register keeps the selected production for repeated attendance, clears dates, and keeps failed inputs', async () => {
  const start = source.indexOf('    const g = b.closest(".add-work");', source.indexOf('} else if (b.dataset.addWork)'));
  const end = source.indexOf('  } else if (b.dataset.addFound)', start);
  const run = new Function('b', 'post', 'document', 'askMerge', 'waitJob', 'let sugSeq = 0, sugTimer = null;\n' + source.slice(start, end));
  const field = value => ({value, focus() {this.focused = true}});
  const result = {replaceChildren(...children) {this.children = children}, hidden: true};
  const fields = {'#w-title': field('同じ作品'), '#w-stage': field('99'), '#w-venue': field('劇場'), '#w-date': field('2026-01-02'),
    '#w-time': field('14:00'), '.said': {textContent: ''}, '[data-register-repeat]:checked': {checked: true}};
  const g = {dataset: {registerSingle: '1'}, querySelector: s => fields[s], parentElement: {querySelector: () => result, querySelectorAll: () => []}};
  const b = {closest: () => g};
  const doc = {createElement: () => ({}), getElementById: () => ({replaceChildren() {}})};
  const posts = [];
  const post = async (path, body) => {posts.push(body); return {stage_id: '99', similar: []}};
  const wait = () => assert.fail('must not reload');
  run(b, post, doc, () => {}, wait); await settle();
  assert.equal(fields['#w-title'].value, '同じ作品'); assert.equal(fields['#w-stage'].value, '99'); assert.equal(fields['#w-venue'].value, '劇場');
  assert.equal(fields['#w-date'].value, ''); assert.equal(fields['#w-time'].value, ''); assert.ok(fields['#w-date'].focused);
  assert.equal(result.children[1].href, '/rate/unrated'); assert.ok(posts[0].repeat);
  fields['#w-date'].value = '2026-01-02'; fields['#w-time'].value = '19:00';
  run(b, post, doc, () => {}, wait); await settle();
  assert.equal(posts[1].title, posts[0].title); assert.equal(posts[1].time, '19:00'); assert.equal(b.disabled, false);
  fields['#w-date'].value = '2026-01-03';
  run(b, async () => null, doc, () => {}, wait); await settle();
  assert.equal(fields['#w-date'].value, '2026-01-03'); assert.equal(fields['#w-title'].value, '同じ作品'); assert.equal(b.disabled, false);
  fields['[data-register-repeat]:checked'] = null;
  run(b, post, doc, () => {}, wait); await settle();
  assert.equal(fields['#w-title'].value, ''); assert.equal(fields['#w-stage'].value, ''); assert.equal(fields['#w-venue'].value, '');
});

test('detail dialog sends the chosen schedule precision without turning the filter into attendance', async () => {
  const start = source.indexOf('function registerSearchDialog('), end = source.indexOf('\nfunction sugWatch()', start);
  const make = new Function('document', 'fetch', 'sugRender', 'API_BASE', 'T', source.slice(start, end) + '\nreturn registerSearchDialog;');
  const handlers = {}, status = {}, button = {}, box = {replaceChildren() {}}, close = {};
  const fields = Object.fromEntries(['q', 'group', 'venue', 'schedule_precision', 'schedule_year', 'schedule_month', 'schedule_day'].map(k => {
    const label = {};
    return [k, {value: k === 'schedule_precision' ? 'none' : '', focus() {}, closest: () => label,
      addEventListener: (type, fn) => {handlers[k + '-' + type] = fn}}];
  }));
  const form = {elements: fields,
    querySelector: () => button, addEventListener: (type, fn) => {handlers[type] = fn}};
  const selectors = {'form': form, '.rs-status': status, '.rs-results': box, '[data-rs-close]': {addEventListener: (type, fn) => {close[type] = fn}}};
  const dialog = {dataset: {}, isConnected: true, setAttribute() {}, querySelector: s => selectors[s],
    addEventListener(type, fn) {handlers['dialog-' + type] = fn}, showModal() {this.open = true}, close() {this.open = false; handlers['dialog-close']()}, remove() {this.isConnected = false}};
  const doc = {querySelector: () => null, createElement: () => dialog, getElementById: id => ({value: id === 'w-title' ? '演劇' : '2026-01-02'}), body: {append() {}}};
  let request, rows, failing = false;
  const open = make(doc, async url => {request = new URL(url, 'https://taguri.test'); if (failing) throw Error('通信失敗'); return {ok: true, json: async () => ({rows: [{kind: 'stage', title: '演劇の夜', stage_id: '99', date: ''}]})}}, (_, got) => {rows = got}, '', 'token');
  const trigger = {isConnected: true, focus() {this.focused = true}}; open(trigger);
  assert.ok(dialog.open); assert.equal(request, undefined);
  assert.ok(fields.schedule_year.disabled); assert.ok(fields.schedule_month.disabled); assert.ok(fields.schedule_day.disabled);
  form.elements.group.value = '劇団甲'; form.elements.venue.value = '東京劇場';
  fields.schedule_precision.value = 'month'; handlers['schedule_precision-change']();
  fields.schedule_month.value = '10'; fields.schedule_year.value = '2026';
  assert.ok(!fields.schedule_month.disabled); assert.ok(fields.schedule_year.disabled); assert.ok(fields.schedule_day.disabled);
  assert.equal(fields.schedule_month.closest('label').hidden, false);
  const event = {preventDefault() {}, stopPropagation() {}};
  await handlers.submit(event);
  assert.equal(request.searchParams.get('advanced'), '1'); assert.equal(request.searchParams.get('group'), '劇団甲');
  assert.equal(request.searchParams.get('venue'), '東京劇場'); assert.equal(rows[0].date, ''); assert.equal(button.disabled, false);
  assert.equal(request.searchParams.get('schedule_precision'), 'month'); assert.equal(request.searchParams.get('schedule_month'), '10');
  assert.ok(!request.searchParams.has('schedule_year')); assert.ok(!request.searchParams.has('date'));
  fields.schedule_precision.value = 'date'; handlers['schedule_precision-change'](); fields.schedule_day.value = '19';
  await handlers.submit(event);
  assert.equal(request.searchParams.get('schedule_year'), '2026'); assert.equal(request.searchParams.get('schedule_day'), '19');
  assert.equal(rows[0].date, '');
  fields.schedule_precision.value = 'none'; handlers['schedule_precision-change'](); await handlers.submit(event);
  assert.ok(!request.searchParams.has('schedule_month')); assert.ok(!request.searchParams.has('schedule_day'));
  failing = true; await handlers.submit(event); assert.match(status.textContent, /通信失敗/); assert.equal(button.disabled, false);
  close.click(); assert.ok(!dialog.open); assert.ok(trigger.focused);
});
