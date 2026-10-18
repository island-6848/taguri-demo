// Request bodies are read with the cap applied while streaming (issue #123).
import test from 'node:test';
import assert from 'node:assert/strict';
import {readCapped} from '../src/body-limit.js';
import {readInput} from '../src/screens/index.js';

// A body of `count` chunks of `size` bytes; records how many bytes were pulled and whether
// the reader was cancelled.
function streamed(count, size, headers = {}) {
  const seen = {pulled: 0, cancelled: false};
  let i = 0;
  const body = new ReadableStream({
    pull(controller) {
      if (i++ >= count) { controller.close(); return; }
      const chunk = new Uint8Array(size).fill(0x20);   // spaces: valid JSON whitespace
      seen.pulled += size;
      controller.enqueue(chunk);
    },
    cancel() { seen.cancelled = true; },
  }, {highWaterMark: 0});
  const request = new Request('https://x/api/rate', {method: 'POST', body, headers, duplex: 'half'});
  return {request, seen};
}

test('readCapped stops at the first chunk past the cap and cancels the stream', async () => {
  const {request, seen} = streamed(16, 4096);
  assert.equal(await readCapped(request, 8192), null);
  assert.ok(seen.cancelled);
  assert.ok(seen.pulled <= 8192 + 4096, `pulled ${seen.pulled}`);
});

test('readCapped returns the bytes up to and including the cap', async () => {
  const {request} = streamed(2, 4096);
  assert.equal((await readCapped(request, 8192)).length, 8192);
  assert.equal((await readCapped(new Request('https://x/', {method: 'POST'}), 10)).length, 0);
});

test('readInput: no Content-Length and a large body is 413 without reading it all', async () => {
  const {request, seen} = streamed(16, 4096);
  const r = await readInput(request, 'rate');
  assert.equal(r.status, 413);
  assert.ok(seen.cancelled);
  assert.ok(seen.pulled < 65536, `pulled ${seen.pulled}`);
});

test('readInput: a Content-Length smaller than the real body does not lift the cap', async () => {
  const {request, seen} = streamed(16, 4096, {'content-length': '10'});
  assert.equal((await readInput(request, 'rate')).status, 413);
  assert.ok(seen.cancelled);
});

test('readInput: the account screen allows 64 KB, not more', async () => {
  const ok = JSON.stringify({icon: 'a'.repeat(65536 - 11)});
  assert.equal(new TextEncoder().encode(ok).length, 65536);
  const r = await readInput(new Request('https://x/', {method: 'POST', body: ok}), 'account');
  assert.equal(r.input.icon.length, 65536 - 11);
  const {request, seen} = streamed(17, 4096);
  assert.equal((await readInput(request, 'account')).status, 413);
  assert.ok(seen.cancelled);
  // other screens keep the 8 KB cap
  assert.equal((await readInput(new Request('https://x/', {method: 'POST', body: ok}), 'rate')).status, 413);
});

test('readInput: a body exactly at 8 KB is read', async () => {
  const body = JSON.stringify({a: 'b'.repeat(8192 - 8)});
  assert.equal(new TextEncoder().encode(body).length, 8192);
  assert.equal((await readInput(new Request('https://x/', {method: 'POST', body}), 'rate')).input.a.length, 8184);
});
