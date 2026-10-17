// src/screens/storyline.js gives storyline.panel's HTML for the same rated rows.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {panel} from '../src/screens/storyline.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/storyline_fixture.py')], {encoding: 'utf8', maxBuffer: 1 << 26}));

test('人の流れ matches storyline.panel', () => {
  fx.cases.forEach((c, i) => {
    const got = panel(c.rated, c.min_times);
    if (got !== c.html) {
      let k = 0; while (k < got.length && got[k] === c.html[k]) k++;
      assert.fail(`case ${i} (min_times ${c.min_times}): differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${c.html.slice(Math.max(0, k - 100), k + 120)}`);
    }
  });
});

// 名前や題名に「</script>」があっても、図のデータの <script> がそこで閉じない（安全の点検 2026-10-17）
test('a name or title with </script> stays inside the data block', () => {
  const evil = '</script><img src=x onerror=alert(1)>';
  const rated = [0, 1, 2, 3, 4].map(k => ({key: `x${k}#2024-0${k + 1}-01`, title: `${evil}${k}`, date: `2024-0${k + 1}-01`, verdict: '◎',
    people: [['出演', evil], ['出演', '乙'], ['出演', '丙']], venues: []}));
  const html = panel(rated, 2);
  const data = /<script id="sl-data" type="application\/json">([\s\S]*?)<\/script>/.exec(html);
  assert.ok(data, 'the data block is there');
  assert.doesNotMatch(data[1], /</);
  assert.equal(JSON.parse(data[1]).lines.some(l => l.name === evil), true);
  assert.doesNotMatch(html, /<img src=x/);
});
