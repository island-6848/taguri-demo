// 利用者ごとに LLM を呼ばない（起案者の指示 2026-10-18「ユーザーが莫大に増えたとき困る。限界までルールベースで、
// 最小限 Claude を呼ぶかたち」）。Worker（利用者の要求ごとに動くもの）は LLM の API を呼ばない。
// LLM が読むのは公演ごとに 1 回の、あらすじの読み取りだけ（運営者の Claude の定期実行。取得側の data/credits）。
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync, statSync} from 'node:fs';
import {join} from 'node:path';

const root = new URL('../src/', import.meta.url).pathname;
const files = dir => readdirSync(dir).flatMap(n => (statSync(join(dir, n)).isDirectory() ? files(join(dir, n)) : [join(dir, n)]));
const LLM_HOSTS = /generativelanguage\.googleapis\.com|api\.anthropic\.com|api\.openai\.com|aiplatform\.googleapis\.com|bedrock-runtime/i;

test('the Worker never calls an LLM API (nothing per user goes to an LLM)', () => {
  for (const f of files(root).filter(f => f.endsWith('.js'))) {
    assert.doesNotMatch(readFileSync(f, 'utf8'), LLM_HOSTS, `${f.slice(root.length)} が LLM の API を呼んでいる`);
  }
  assert.doesNotMatch(readFileSync(new URL('../wrangler.jsonc', import.meta.url), 'utf8'), /"ai"\s*:/, 'Workers AI の結び付けがある');
});
