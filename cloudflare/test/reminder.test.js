// src/screens/reminder.js gives digest.panel's HTML for the same candidates and answers.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel} from '../src/screens/reminder.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/reminder_fixture.py')], {encoding: 'utf8'}));

test('開幕リマインド matches digest.panel', () => {
  for (const c of fx.cases) {
    // 券（owned・tickets）は渡さない: 「直近の観劇予定」の枠は外した（起案者の指示 2026-10-18）
    const got = panel({cands: fx.cands, status: new Map(Object.entries(fx.status)), today: fx.today, prefs: c.prefs, week: c.week});
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`${JSON.stringify(c.prefs)} ${c.week}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 80), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 80), k + 120)}`);
    }
  }
});
