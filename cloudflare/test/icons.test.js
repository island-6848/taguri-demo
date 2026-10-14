// src/screens/icons.js carries the same icons as tools/taguri/icons.py.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {P, ALIAS, ico, h2} from '../src/screens/icons.js';

test('icon paths and markup match icons.py', () => {
  const py = JSON.parse(execFileSync('python3', ['-c', `
import sys, json; sys.path.insert(0, 'tools/taguri'); import icons as IC
print(json.dumps({"P": IC.P, "ALIAS": IC.ALIAS, "ico": IC.ico("check", 14, "ixck"), "h2": IC.h2("inbox", "今週", "<b>x</b>")}, ensure_ascii=False))`],
  {cwd: new URL('../..', import.meta.url).pathname, encoding: 'utf8'}));
  assert.deepEqual(P, py.P);
  assert.deepEqual(ALIAS, py.ALIAS);
  assert.equal(ico('check', 14, 'ixck'), py.ico);
  assert.equal(h2('inbox', '今週', '<b>x</b>'), py.h2);
});
