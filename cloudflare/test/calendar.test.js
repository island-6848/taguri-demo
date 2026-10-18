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

test('#100 the go-date list says what its delete button removes and what stays', () => {
  const html = addTicketButtonHtml(fx.d, fx.today, new Map(Object.entries(fx.tickets)));
  assert.doesNotMatch(html, />(取り消す|違う)<\/button>/);
  assert.match(html, /入れてある日（日時を直すときは「この日時を削除」で消して、下の「行く日」から入れ直してください）/);
  assert.match(html, /<button data-del="1" data-stage="301" data-date="2026-10-15" data-time="13:00" title="この行く日（10\/15 13:00）だけを消します。購入済み・興味あり・お気に入りの登録は消えません" data-done="10\/15 13:00 の行く日を削除しました。公演の登録（購入済み・興味あり・お気に入り）は変わりません。入れてある日は、あと \d+ 件です">この日時を削除<\/button>/);
  // 確定前の券は「確定」を先に、そのあとに同じ削除の口
  assert.match(html, /<li class="un">.*?>確定<\/button><button data-del="1"[^>]*>この日時を削除<\/button><\/li>/);
  // 最後の 1 つを消すと残りは無い
  const one = addTicketButtonHtml({owned: [{stage_id: '9', title: 'X', period: '2026/10/10 ～ 2026/11/03', pref: '東京都', venue: 'A'}]}, fx.today,
    new Map([['9', [{date: '2026-10-20', time: '', confirmed: 1}]]]));
  assert.match(one, /data-done="10\/20 の行く日を削除しました。公演の登録（購入済み・興味あり・お気に入り）は変わりません。入れてある日は、もうありません"/);
});
