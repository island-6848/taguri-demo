// 取り消した記録: 30 日たっても戻さなければ消す（works.expireDropped）、「いますぐ消す」はその場で消す。
// 起案者の指示（2026-10-14）「取り消した記録は30日以内に復元されなかったら自動的に削除して」
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

const count = (sqlite, key) => sqlite.prepare('SELECT COUNT(*) n FROM works WHERE work_key=?').get(key).n;

test('a record dropped over 30 days ago is deleted; a newer drop stays and can be restored', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const old = (await step(env, a, {post: '/api/add_work', body: {title: '古く外した舞台', date: '2026-08-01'}})).body.work_key;
    const fresh = (await step(env, a, {post: '/api/add_work', body: {title: '最近外した舞台', date: '2026-08-02'}})).body.work_key;
    for (const k of [old, fresh]) assert.equal((await step(env, a, {post: '/api/drop_work', body: {work_key: k}})).status, 200);
    sqlite.prepare("UPDATE excluded SET updated_at='2000-01-01 00:00:00' WHERE uid=?").run(`work:${old}`);
    const settings = (await step(env, a, {get: '/api/screen/settings'})).body.body_html;
    assert.match(settings, /30 日たっても戻さなかった記録は、自動で消します/);
    assert.doesNotMatch(settings.slice(settings.indexOf('取り消した記録'), settings.indexOf('行かなかった公演')), /メール/);
    await step(env, a, {get: '/api/screen/unrated'});
    assert.equal(count(sqlite, old), 0);
    assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM excluded WHERE uid=?').get(`work:${old}`).n, 0);
    assert.equal(count(sqlite, fresh), 1);
    assert.equal((await step(env, a, {post: '/api/restore_work', body: {key: fresh}})).status, 200);
    assert.match((await step(env, a, {get: '/api/screen/unrated'})).body.body_html, /最近外した舞台/);
  } finally { sqlite.close(); }
});

test('いますぐ消す deletes the record at once', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    const k = (await step(env, a, {post: '/api/add_work', body: {title: 'すぐ消す舞台', date: '2026-08-01'}})).body.work_key;
    await step(env, a, {post: '/api/drop_work', body: {work_key: k}});
    assert.equal((await step(env, a, {post: '/api/purge_work', body: {key: k}})).status, 200);
    assert.equal(count(sqlite, k), 0);
    assert.doesNotMatch((await step(env, a, {get: '/api/screen/settings'})).body.body_html, /すぐ消す舞台/);
    assert.equal((await step(env, a, {post: '/api/restore_work', body: {key: k}})).status, 400);
  } finally { sqlite.close(); }
});

test('the record editor speaks plainly and keeps no mail', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    await step(env, a, {post: '/api/add_work', body: {title: '編集を見る舞台', date: '2026-08-01'}});
    const html = (await step(env, a, {get: '/api/screen/unrated'})).body.body_html;
    assert.match(html, /<summary>記録を直す/);
    assert.match(html, /観た公演/);
    assert.match(html, /<!--\/editor--><\/details>/);
    assert.doesNotMatch(html, /data-mail|data-unfix|ed-mail|メール本文/);
    assert.match(html, /30 日/);
  } finally { sqlite.close(); }
});
