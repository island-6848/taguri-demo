// workerd は Worker の入り口のモジュール（src/worker.js）の名前付きの export を、すべて入り口（関数・ExportedHandler）として
// 読む。数や文字の export があると、Worker そのものが起動しない（Uncaught TypeError: Incorrect type for map entry …）。
// 2026-10-18 に `export const FIREBASE_DELETE_DAYS = 30` で runtime-smoke が止まったので、ここで先に見つける。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as mod from '../src/worker.js';

test('every named export of the Worker entry module is a function (workerd reads them as entrypoints)', () => {
  for (const [name, value] of Object.entries(mod)) {
    if (name === 'default') continue;
    assert.equal(typeof value, 'function', `src/worker.js の export ${name} は関数でない（${typeof value}）。export を外すか、別のファイルに移す`);
  }
});
