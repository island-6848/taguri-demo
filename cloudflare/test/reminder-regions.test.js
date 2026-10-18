// 開幕リマインド: 地方が違って別の行になった同じ公演は、どちらかで答えたら両方の行に同じ答えを出す（reminder.mergeSiblings）。
// 起案者の指摘 2026-10-18「2回出たのは開幕リマインド。1個だけ興味ありにしたら、もう片方がおすすめに出てきた」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {weekAll} from '../src/screens/reminder.js';

const cand = (stage_id, pref, theater, group) => ({stage_id, title: 'ラブ演劇博', period: '2026/10/20 ～ 2026/10/25', theater, venue: theater, pref, group});

test('rows of one production in two regions both show the answer given to one', () => {
  const cands = [cand('1', '東京都', '劇場A', '実行委員会'), cand('2', '大阪府', '劇場B', ''), cand('3', '福岡県', '劇場C', '別の劇団')];
  const {days} = weekAll(cands, new Map([['1', 'tracking']]), '2026-10-18', [], 0);
  const rows = days.flatMap(([, r]) => r);
  assert.equal(rows.length, 3);                       // 地方ごとの行は分けたまま（2026-08-26 の指示）
  const kind = Object.fromEntries(rows.map(r => [r.stage_id, r.kind_key]));
  assert.equal(kind['2'], 'tracking');                // 団体が無い行 → 同じ公演とみなす
  assert.equal(kind['3'], 'unanswered');              // 別の団体の同じ題名 → 別の公演
});
