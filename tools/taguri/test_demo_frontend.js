// Run with: node tools/taguri/test_demo_frontend.js
// Exercise the shipped functions with a small DOM/fetch harness; no browser server.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../web/app.js'), 'utf8');
const cache = source.slice(source.indexOf('const fragmentCache ='), source.indexOf('// **初めての訪問者'));
const post = source.slice(source.indexOf('async function post('), source.indexOf('// 段の名前と札。'));
const restrictions = source.slice(source.indexOf('function applyDemoRestrictions('), source.indexOf('function renderScreen('));
const context = vm.createContext({assert, Date, Map, API_BASE: 'https://api.example', showWelcomeCode() {}});
vm.runInContext(cache + post + restrictions, context);
vm.runInContext(`
  let reply = {ok: true};
  let httpOK = true;
  async function fetch() { return {ok: httpOK, status: 403, json: async () => reply}; }
  const stored = {body_html: "old"};
  async function checkCache() {
    fragmentCacheSet("notes?", stored);
    await post("/api/note", {}, null, null);
    assert.equal(fragmentCacheGet("notes?"), null, "successful save discards stale fragments");
    fragmentCacheSet("notes?", stored);
    await post("/api/hand_theme_refresh", {}, null, null);
    assert.equal(fragmentCacheGet("notes?"), stored, "read-only polling retains fragments");
    httpOK = false;
    await post("/api/note", {}, null, null);
    assert.equal(fragmentCacheGet("notes?"), stored, "failed save retains fragments");
    httpOK = true;
    reply = {ok: false};
    await post("/api/note", {}, null, null);
    assert.equal(fragmentCacheGet("notes?"), stored, "unsuccessful response retains fragments");
  }
  checkCache();
`, context).then(() => {
  vm.runInContext(`
    let replaced = null;
    const editor = {replaceWith(note) { replaced = note; }};
    const upload = {};
    const button = {textContent: "CoRichで検索"};
    const root = {querySelectorAll(selector) {
      return selector === ".handt" ? [editor] : selector.includes("data-hand-img") ? [upload] : [button];
    }};
    const document = {createElement() { return {}; }};
    applyDemoRestrictions(root);
    assert.match(replaced.textContent, /デモ/);
    assert.equal(upload.disabled, true);
    assert.equal(button.textContent, "デモの公演から探す");
  `, context);
  process.stdout.write('7 demo UI/cache assertions passed\n');
}).catch(error => { console.error(error); process.exitCode = 1; });
