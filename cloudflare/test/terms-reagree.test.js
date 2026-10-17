// 規約の版が上がったあと、登録済みの人に同意し直してもらう（src/terms.js agreeAction・needsAgreement）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';
import {TERMS_VERSION} from '../src/terms.js';

test('screens carry terms_update until the user agrees to the current version; a stale version is refused', async () => {
  const {env, sqlite} = setup();
  const a = await signIn(env);
  try {
    sqlite.prepare("UPDATE users SET terms_version='2026-10-18', terms_at=1").run();
    assert.equal((await step(env, a, {get: '/api/screen/rate'})).body.terms_update, TERMS_VERSION);
    const stale = await step(env, a, {post: '/api/agree', body: {agree: '2026-10-18'}});
    assert.equal(stale.status, 400);
    assert.match(stale.body.error, /新しくなりました/);
    const ok = await step(env, a, {post: '/api/agree', body: {agree: TERMS_VERSION}});
    assert.equal(ok.status, 200);
    const row = sqlite.prepare('SELECT terms_version, terms_at FROM users').get();
    assert.equal(row.terms_version, TERMS_VERSION);
    assert.ok(row.terms_at > 1);
    assert.equal((await step(env, a, {get: '/api/screen/rate'})).body.terms_update, undefined);
    // accounts made before agreement was recorded (NULL) are asked too
    sqlite.prepare('UPDATE users SET terms_version=NULL').run();
    assert.equal((await step(env, a, {get: '/api/screen/rate'})).body.terms_update, TERMS_VERSION);
  } finally { sqlite.close(); }
});
