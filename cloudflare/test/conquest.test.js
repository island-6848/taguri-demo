// 劇場制覇マップ（起案者の指示 2026-10-16「同じ建物の別ホールは分けたほうがいいな。…組み込んで」、mock-theater-conquest）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {venueKey, tally, conquestPanel, fill, POS} from '../src/screens/conquest.js';
import {PREFS} from '../src/screens/prefs.js';
import {setup, step, signIn} from './screens/harness.js';

test('every prefecture has its own tile', () => {
  assert.deepEqual(Object.keys(POS).sort(), [...PREFS].sort());
  const cells = Object.values(POS).map(p => p.join(','));
  assert.equal(new Set(cells).size, 47);
});

test('venue names match the crawler side (deliver_catalogue.venue_key)', () => {
  const names = ['東京芸術劇場　シアターイースト', 'ＰＡＲＣＯ劇場', ' 本多 劇場 ', 'KAAT 神奈川芸術劇場'];
  const py = JSON.parse(execFileSync('python3', ['-c',
    'import sys,json; sys.path.insert(0, sys.argv[1]); import deliver_catalogue as D; print(json.dumps([D.venue_key(n) for n in json.load(sys.stdin)]))',
    new URL('../scripts', import.meta.url).pathname],
  {input: JSON.stringify(names), encoding: 'utf8'}));
  assert.deepEqual(names.map(venueKey), py);
  assert.equal(venueKey('ＰＡＲＣＯ劇場'), 'PARCO劇場');
});

test('a visited venue outside the census still counts, and adds to its prefecture', () => {
  const by = tally([{key: '本多劇場', name: '本多劇場', pref: '東京都'}, {key: '赤坂ACTシアター', name: '赤坂ACTシアター', pref: '東京都'}],
    {'東京都': 500, '大阪府': 139}, new Set(['本多劇場']));
  assert.deepEqual([by['東京都'].names.length, by['東京都'].total], [2, 501]);
  assert.equal(by['大阪府'].total, 139);
  assert.equal(by['沖縄県'].total, 0);
});

test('the panel: counts on the tiles, shades by venues, a list per prefecture', () => {
  const by = tally([{key: 'a', name: '劇場A', pref: '東京都'}], {'東京都': 3}, new Set(['a']));
  const html = conquestPanel(by, ['どこかの劇場']);
  assert.match(html, /劇場制覇マップ/);
  assert.match(html, /行った劇場 <b>1<\/b>（全国 3 のうち）・行った都道府県 <b>1 \/ 47<\/b>/);
  assert.match(html, /<title>東京都：1 \/ 3 か所<\/title>/);
  assert.match(html, />1\/3</);
  assert.match(html, /<summary><b>東京都<\/b>　1\/3 か所<\/summary><ul><li>劇場A<\/li>/);
  assert.match(html, /都道府県が分からない劇場　1 か所/);
  assert.equal(fill(0), 'var(--plane)');
  assert.match(fill(12), /56%/);
  // Before the first delivery of the census there is no denominator: the map shows the visits only.
  assert.match(conquestPanel(tally([{key: 'a', name: '劇場A', pref: '東京都'}], null, new Set())), /<title>東京都：1 か所<\/title>/);
  assert.equal(conquestPanel(tally([], null, new Set())), '');
});

test('眺める shows the map from the diary, with the census as the denominator', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    sqlite.exec("INSERT INTO venue_census(venue,pref) VALUES('本多劇場','東京都'),('ザ・スズナリ','東京都')");
    sqlite.exec(`INSERT INTO rec_meta(k,v) VALUES('venue_counts','{"東京都":2}') ON CONFLICT(k) DO UPDATE SET v=excluded.v`);
    sqlite.exec("INSERT INTO venue_pref(venue,pref) VALUES('赤坂ACTシアター','東京都')");
    for (const [title, venue] of [['観た舞台', '本多 劇場'], ['もう一本', '赤坂ACTシアター'], ['県なし', 'すみだパークスタジオ倉']]) {
      const r = await step(env, a, {post: '/api/add_work', body: {title, date: '2026-08-08', venue}});
      assert.ok(r.body.work_key, JSON.stringify(r.body));
    }
    const html = (await step(env, a, {get: '/api/screen/records'})).body.body_html;
    assert.match(html, /劇場制覇マップ/);
    assert.match(html, /<title>東京都：2 \/ 3 か所<\/title>/);
    assert.match(html, /都道府県が分からない劇場　1 か所/);
  } finally { sqlite.close(); }
});

test('the map grows by year: each venue keeps the first year it was visited', () => {
  const vis = [{key: 'a', name: '劇場A', pref: '東京都', year: 2021}, {key: 'b', name: '劇場B', pref: '大阪府', year: 2024},
    {key: 'c', name: '劇場C', pref: '東京都', year: null}];
  const html = conquestPanel(tally(vis, {'東京都': 3, '大阪府': 2}, new Set(['a', 'b', 'c'])));
  const m = /data-cq="([^"]*)"/.exec(html);
  assert.ok(m, 'two or more years: the slider data is there');
  const g = JSON.parse(m[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>'));
  assert.deepEqual(g.years, [2021, 2024]);
  assert.deepEqual(g.v.filter(([p]) => p === '東京都').map(x => x[1]).sort(), [2021, null]);
  assert.match(html, /<input type="range" min="0" max="2" value="2"/);
  // One year only: nothing to move through.
  assert.doesNotMatch(conquestPanel(tally(vis.slice(0, 1), null, new Set())), /data-cq|type="range"/);
});
