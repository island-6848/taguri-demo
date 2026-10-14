// src/screens/calendar.js gives stage_calendar's HTML for the same lists and tickets.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel, addTicketButtonHtml} from '../src/screens/calendar.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/calendar_fixture.py')], {encoding: 'utf8'}));
const same = (got, want, what) => {
  if (got === want) return;
  let k = 0; while (k < got.length && got[k] === want[k]) k++;
  assert.fail(`${what}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 80), k + 120)}\n py: ${want.slice(Math.max(0, k - 80), k + 120)}`);
};

test('公演カレンダー matches stage_calendar', () => {
  const tickets = new Map(Object.entries(fx.tickets));
  for (const c of fx.cases)
    same(panel(fx.d, fx.today, tickets, c.kinds && new Set(c.kinds), c.prefs && new Set(c.prefs)), c.html, JSON.stringify([c.kinds, c.prefs]));
  same(addTicketButtonHtml(fx.d, fx.today, tickets), fx.add, 'add_ticket_button_html');
  same(panel({}, fx.today, new Map()), fx.empty, 'empty');
});
