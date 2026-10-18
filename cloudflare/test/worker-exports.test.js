// workerd は入り口のモジュール（src/worker.js）の名前付き export をすべて入り口（関数か ExportedHandler）として読む。
// 数や文字を export すると起動しない（2026-10-18、FIREBASE_DELETE_DAYS で runtime-smoke が落ちた）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as mod from '../src/worker.js';

test('every named export of the Worker entry is a function', () => {
  const bad = Object.entries(mod).filter(([k, v]) => k !== 'default' && typeof v !== 'function').map(([k]) => k);
  assert.deepEqual(bad, []);
});
