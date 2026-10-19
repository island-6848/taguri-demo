import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scheduleFilter} from '../src/screens/schedule-filter.js';

const filter = (precision, parts = {}) => scheduleFilter(new URLSearchParams({schedule_precision: precision,
  ...Object.fromEntries(Object.entries(parts).map(([k, v]) => ['schedule_' + k, String(v)]))}));

test('month and month/day overlap the full run across year boundaries, in any year', () => {
  const january = filter('month', {month: 1});
  assert.ok(january.matches('2025-12-20', '2026-01-10'));
  assert.ok(january.matches('2024-01-31', '2024-02-05'));
  assert.ok(!january.matches('2025-12-01', '2025-12-31'));
  const jan10 = filter('monthday', {month: 1, day: 10});
  assert.ok(jan10.matches('2025-12-20', '2026-01-10'));
  assert.ok(!jan10.matches('2026-01-11', '2026-01-31'));
  assert.ok(!jan10.matches('', ''));
});

test('year, year/month and full date use inclusive run overlap', () => {
  const year = filter('year', {year: 2026});
  assert.deepEqual([year.from, year.to], ['2026-01-01', '2026-12-31']);
  assert.ok(year.matches('2025-12-20', '2026-01-01'));
  assert.ok(!year.matches('2025-01-01', '2025-12-31'));
  const month = filter('yearmonth', {year: 2024, month: 2});
  assert.deepEqual([month.from, month.to], ['2024-02-01', '2024-02-29']);
  assert.ok(month.matches('2024-02-29', '2024-03-03'));
  assert.ok(!month.matches('2025-02-01', '2025-02-28'));
  const date = filter('date', {year: 2026, month: 10, day: 19});
  assert.ok(date.matches('2026-10-01', '2026-10-19'));
  assert.ok(date.matches('2026-10-19', ''));
  assert.ok(!date.matches('2026-10-20', '2026-10-30'));
});

test('annual February 29 matches real leap days including century gaps', () => {
  const leap = filter('monthday', {month: 2, day: 29});
  assert.ok(leap.matches('2024-02-01', '2024-03-01'));
  assert.ok(!leap.matches('2025-02-01', '2025-03-01'));
  assert.ok(leap.matches('2096-03-01', '2104-02-29'));
  assert.ok(!leap.matches('2096-03-01', '2104-02-28'));
});

test('invalid or incomplete schedules fail; irrelevant fields are ignored', () => {
  for (const [mode, parts] of [['month', {}], ['month', {month: 13}], ['monthday', {month: 2, day: 30}],
    ['year', {year: 0}], ['date', {year: 2025, month: 2, day: 29}], ['unknown', {}]]) {
    assert.throws(() => filter(mode, parts), /上演日程/);
  }
  assert.ok(filter('none', {month: 99}).matches('', ''));
  assert.ok(filter('month', {year: 2025, month: 10, day: 99}).matches('2026-10-01', '2026-10-31'));
});
