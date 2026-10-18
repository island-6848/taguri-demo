// #101: 「次回は○月○日 4 時台（日本時間）」は crawl-time.js の 1 つの決まりから作る。探すの依頼済みは、
// 控えにある依頼の日から「まだ更新が来ていない」と「更新のあとも公演一覧に無い」を分けて書く。
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {CRAWL_UTC_HOUR, CRAWL_UTC_MINUTE, nextCrawl, lastCrawlDone, crawlsSince, crawlLabel, crawlSearch} from '../src/crawl-time.js';
import {setup, step, signIn} from './screens/harness.js';

test('the crawl time is the one in the catalog workflow (17 19 * * * UTC = 4:17 JST)', () => {
  const yml = readFileSync(new URL('../../tools/taguri/deploy/github-actions/catalog.yml', import.meta.url), 'utf8');
  const crons = [...yml.matchAll(/cron:\s*'(\d+) (\d+) /g)].map(m => [Number(m[2]), Number(m[1])]);
  assert.ok(crons.length);
  for (const c of crons) assert.deepEqual(c, [CRAWL_UTC_HOUR, CRAWL_UTC_MINUTE]);
});

test('next and last crawl, counted in JST', () => {
  const t = s => Date.parse(s);
  assert.equal(crawlLabel(nextCrawl(t('2026-10-18T10:00:00Z'))), '10月19日 4時台（日本時間）');   // 19:00 JST
  assert.equal(crawlLabel(nextCrawl(t('2026-10-18T18:00:00Z'))), '10月19日 4時台（日本時間）');   // 3:00 JST
  assert.equal(crawlLabel(nextCrawl(t('2026-10-18T19:30:00Z'))), '10月20日 4時台（日本時間）');   // 4:30 JST
  assert.equal(crawlLabel(nextCrawl(t('2026-12-31T20:00:00Z'))), '1月2日 4時台（日本時間）');
  // 予定から 6 時間たつまでは、その回は済んでいないとみなす
  assert.equal(lastCrawlDone(t('2026-10-18T22:00:00Z')), t('2026-10-17T19:17:00Z'));
  assert.equal(lastCrawlDone(t('2026-10-19T02:00:00Z')), t('2026-10-18T19:17:00Z'));
  assert.equal(crawlsSince(t('2026-10-18T10:00:00Z'), t('2026-10-18T22:00:00Z')), 0);
  assert.equal(crawlsSince(t('2026-10-18T10:00:00Z'), t('2026-10-19T02:00:00Z')), 1);
  assert.equal(crawlsSince(t('2026-10-16T10:00:00Z'), t('2026-10-19T02:00:00Z')), 3);
  assert.equal(crawlsSince(t('2026-10-17T19:17:00Z'), t('2026-10-19T02:00:00Z')), 1);
});

test('#101: while the crawl does not read requests yet, the screens do not promise a search', async () => {
  assert.equal(crawlSearch.requests, false);
  const {env, sqlite} = setup();
  try {
    const cookie = await signIn(env);
    const q = 'どこにも無い舞台';
    const url = '/api/screen/search?q=' + encodeURIComponent(q);
    const before = (await step(env, cookie, {get: url})).body.body_html;
    assert.match(before, /依頼された題名を毎日の更新で探す段はまだ準備中で、いまは探されません/);
    const asked = await step(env, cookie, {post: '/api/search_request', body: {q, source: 'search'}});
    assert.equal(asked.status, 200);
    assert.match(asked.body.message, /^依頼を控えました。依頼された題名を毎日の更新で探す段はまだ準備中/);
    const pending = (await step(env, cookie, {get: url})).body.body_html;
    assert.match(pending, /「どこにも無い舞台」は10月12日に依頼を控えました。<b>ただ、依頼された題名を毎日の更新で探す段はまだ準備中で、まだ探していません。<\/b>/);
    assert.match(pending, /公演一覧そのものは毎日更新しています（次回は10月13日 4時台（日本時間））/);
    assert.doesNotMatch(pending, /毎日 4 時台|翌日|探します<\/b>/);
    const reg = (await step(env, cookie, {get: '/api/screen/register'})).body.body_html;
    assert.match(reg, /いまは探されません/);
  } finally { sqlite.close(); }
});

test('#101: once the crawl reads requests, the next run is dated and later runs say the stage is still missing', async () => {
  const {env, sqlite} = setup();
  crawlSearch.requests = true;
  try {
    const cookie = await signIn(env);
    const q = 'どこにも無い舞台';
    const url = '/api/screen/search?q=' + encodeURIComponent(q);
    // harness の時計は 2026-10-12 03:00 UTC（日本時間 12:00）
    const before = (await step(env, cookie, {get: url})).body.body_html;
    assert.match(before, /次の更新（次回は10月13日 4時台（日本時間））で CoRich から探すよう頼めます/);
    const asked = await step(env, cookie, {post: '/api/search_request', body: {q, source: 'search'}});
    assert.equal(asked.status, 200);
    assert.match(asked.body.message, /次回は10月13日 4時台（日本時間）の更新で/);
    const pending = (await step(env, cookie, {get: url})).body.body_html;
    assert.match(pending, /10月12日に、CoRich から探すよう依頼済みです。<b>次回は10月13日 4時台（日本時間）の更新で探します<\/b>/);
    assert.doesNotMatch(pending, /毎日 4 時台|翌日/);
    // 2 回の更新のあと（10/14 12:00 JST）
    env.CLOCK = {...env.CLOCK, now: Date.parse('2026-10-14T03:00:00Z')};
    const later = (await step(env, cookie, {get: url})).body.body_html;
    assert.match(later, /そのあと更新が 2 回ありましたが、<b>まだたぐりの公演一覧に入っていません。<\/b>/);
    assert.match(later, /いまは記録していないので、この画面では分かりません/);
    assert.match(later, /次回は10月15日 4時台（日本時間）の更新です/);
    const reg = (await step(env, cookie, {get: '/api/screen/register'})).body.body_html;
    assert.match(reg, /次の更新（次回は10月15日 4時台（日本時間））で探します/);
  } finally { crawlSearch.requests = false; sqlite.close(); }
});
