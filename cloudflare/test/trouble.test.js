// 思わぬ失敗のとき、Cloudflare の英語の 1101 ではなく日本語の案内を返す（起案者の指示 2026-10-21「案内入れてよい」）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.js';

const broken = {DB: {prepare() { throw new Error('D1_ERROR: daily limit exceeded'); }, batch() { throw new Error('D1_ERROR'); }},
  ASSETS: {fetch: () => new Response('')}};

test('a page gets a Japanese notice, an API gets JSON, and nothing internal leaks', async () => {
  const page = await worker.fetch(new Request('https://taguri.example/recommend', {headers: {cookie: 'taguri_session=' + 'a'.repeat(64)}}), broken);
  assert.equal(page.status, 503);
  const html = await page.text();
  assert.match(html, /一時的にうまく動いていません/);
  assert.doesNotMatch(html, /D1_ERROR|limit/);
  const api = await worker.fetch(new Request('https://taguri.example/api/screen/recommend', {headers: {cookie: 'taguri_session=' + 'a'.repeat(64)}}), broken);
  assert.equal(api.status, 503);
  const body = await api.json();
  assert.equal(body.ok, false);
  assert.doesNotMatch(JSON.stringify(body), /D1_ERROR/);
});
