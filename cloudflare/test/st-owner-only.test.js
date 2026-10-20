// システムテスト SC-08-01（docs/system-test-spec.md、release-readiness の U3）: 持ち主専用の操作
// （年表の作り直し・Gmail の取り込み・人物の読み直し。Python の serve._owner_only）が、サービス版の
// 一般の利用者には使えない。中継（ORIGINAL_UI_BRIDGE）が入っていても切れていても、Render へ渡さずに断り、
// 画面にもその入口を出さない。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, signIn, step} from './screens/harness.js';

const OWNER_ONLY = ['/api/chronicle', '/api/import_mail', '/api/people_read'];
const SCREENS = ['chronicle', 'records', 'account', 'settings', 'register', 'works'];

for (const bridge of ['true', 'false']) {
  test(`SC-08-01: 一般の利用者は持ち主専用の操作を使えない（中継 ${bridge}）`, async () => {
    const {env, sqlite} = setup();
    env.ORIGINAL_UI_BRIDGE = bridge;
    const outbound = [];
    const realFetch = globalThis.fetch;
    globalThis.fetch = async req => { outbound.push(String(req?.url ?? req)); return Response.json({ok: true}); };
    try {
      const a = await signIn(env);
      const before = sqlite.prepare('SELECT COUNT(*) AS n FROM works').get().n;
      for (const path of OWNER_ONLY) {
        const r = await step(env, a, {post: path, body: {}});
        assert.ok(r.status >= 400, `${path} が ${r.status} で通った`);
        assert.notEqual(r.body?.ok, true, path);
      }
      assert.deepEqual(outbound, [], 'Render にも外にも渡さない');
      assert.equal(sqlite.prepare('SELECT COUNT(*) AS n FROM works').get().n, before, '記録は変わらない');
      for (const name of SCREENS) {
        const got = await step(env, a, {get: `/api/screen/${name}`});
        const html = String(got.body?.body_html ?? '');
        for (const path of OWNER_ONLY) assert.ok(!html.includes(path), `${name} の画面に ${path} の入口が出た`);
      }
    } finally {
      globalThis.fetch = realFetch;
    }
  });
}
