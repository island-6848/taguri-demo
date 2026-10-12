/* Independent deterministic tracker tests. Run: node tools/taguri/test_recommendation_exposure.js */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.resolve(__dirname, '../../web/recommendation-exposure.js'), 'utf8');
const context = {window: {}, console};
vm.runInNewContext(code, context);

function fixture() {
  let clock = 0, serial = 0;
  const jobs = new Map(), sent = [], observers = [], mutationObservers = [], listeners = {};
  let cards = [], blocked = false, sendBehavior = () => Promise.resolve(true);
  const doc = {
    visibilityState: 'visible', hidden: false,
    addEventListener: (name, callback) => {listeners[name] = callback;},
    removeEventListener: (name) => {delete listeners[name];},
    querySelector: () => blocked ? {} : null,
    querySelectorAll: () => [],
  };
  class IO {
    constructor(callback, options) {this.callback = callback; this.options = options; this.targets = new Set(); observers.push(this);}
    observe(target) {this.targets.add(target);}
    unobserve(target) {this.targets.delete(target);}
    disconnect() {this.targets.clear();}
  }
  class MO {constructor(callback) {this.callback = callback; mutationObservers.push(this); } observe() {} disconnect() {}}
  const root = {querySelectorAll: () => cards, contains: (el) => cards.includes(el) || cards.some(c => c.major === el), isConnected: true};
  function card(sid = 'stage-a', pid = 'p'.repeat(24), image = true) {
    const container = {dataset: {exposurePresentation: pid}, getAttribute: (key) => key === 'data-exposure-presentation' ? pid : null};
    const events = {};
    const major = {events, isConnected: true, complete: true, naturalWidth: 300, getBoundingClientRect: () => ({width:300,height:400}), addEventListener(name, callback) {events[name] = callback;}, removeEventListener() {}};
    const heading = {isConnected: true};
    const c = {dataset: {stage: sid, stageId: sid, exposurePresentation: pid}, isConnected: true, major, heading,
      getAttribute: (key) => key === 'data-stage' || key === 'data-stage-id' ? sid : key === 'data-exposure-presentation' ? pid : null,
      closest: () => container,
      querySelector: (selector) => selector.includes('img') ? image ? major : null : heading};
    major.closest = () => c; major.parentElement = c;
    return c;
  }
  cards = [card()];
  const tracker = context.window.TaguriExposure.create({document: doc, IntersectionObserver: IO, MutationObserver: MO,
    setTimeout: (fn, ms) => {let key = ++serial; jobs.set(key, {fn, at: clock + ms}); return key;},
    clearTimeout: (key) => jobs.delete(key), now: () => clock,
    send: (route, body) => {sent.push({route, body}); return sendBehavior(route, body);},
    id: () => String(++serial).padStart(24, 'v')});
  function tick(ms) {
    const end = clock + ms;
    while (true) {
      let next = [...jobs].sort((a,b) => a[1].at - b[1].at).find(x => x[1].at <= end);
      if (!next) break;
      clock = next[1].at; jobs.delete(next[0]); next[1].fn();
    }
    clock = end;
  }
  function intersect(ratio, target = cards[0].major) {
    for (const io of observers) if (io.targets.has(target)) io.callback([{target, isIntersecting: ratio > 0, intersectionRatio: ratio}]);
  }
  function hidden(value) {doc.hidden = value; doc.visibilityState = value ? 'hidden' : 'visible'; listeners.visibilitychange?.();}
  function contacts() {return sent.filter(x => x.route.includes('contact'));}
  return {tracker, root, sent, cards, card, tick, intersect, hidden, contacts, observers, jobs,
    setSend: (callback) => {sendBehavior = callback;},
    setBlocked: (value) => {blocked = value; mutationObservers.forEach(m => m.callback());}};
}
const flush = () => new Promise(resolve => setImmediate(resolve));
const tests = [];
function test(name, fn) {tests.push([name, fn]);}
test('major region requires at least 50 percent for uninterrupted 1000ms', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.49); f.tick(2000); await flush(); assert.equal(f.contacts().length, 0);
  f.intersect(.5); f.tick(999); await flush(); assert.equal(f.contacts().length, 0);
  f.tick(1); await flush(); assert.equal(f.contacts().length, 1);
  assert.equal(f.contacts()[0].body.stage_id, 'stage-a');
});
test('leaving viewport resets rather than accumulates dwell time', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.tick(600); f.intersect(.4); f.tick(400);
  f.intersect(.8); f.tick(600); await flush(); assert.equal(f.contacts().length, 0);
  f.tick(400); await flush(); assert.equal(f.contacts().length, 1);
});
test('background pause disconnects and requires a fresh foreground second', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.tick(700); f.hidden(true); f.tick(5000); await flush();
  assert.equal(f.contacts().length, 0);
  f.hidden(false); f.intersect(.8); f.tick(999); await flush(); assert.equal(f.contacts().length, 0);
  f.tick(1); await flush(); assert.equal(f.contacts().length, 1);
});
test('modal or recovery overlay pauses and resets dwell', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.tick(700); f.setBlocked(true); f.tick(5000); await flush();
  assert.equal(f.contacts().length, 0);
  f.setBlocked(false); f.intersect(.8); f.tick(999); await flush(); assert.equal(f.contacts().length, 0);
  f.tick(1); await flush(); assert.equal(f.contacts().length, 1);
});
test('route stop cancels pending contact', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.tick(700); f.tracker.stop(); f.tick(5000); await flush();
  assert.equal(f.contacts().length, 0); assert.equal(f.jobs.size, 0);
});
test('same candidate once per visit, cache revisit gets another visit', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.tick(1000); await flush();
  f.intersect(.1); f.intersect(.8); f.tick(1000); await flush(); assert.equal(f.contacts().length, 1);
  const original = f.contacts()[0].body.visit_id;
  f.tracker.mount(f.root, 'cache'); await flush(); f.intersect(.8); f.tick(1000); await flush();
  assert.equal(f.contacts().length, 2); assert.notEqual(f.contacts()[1].body.visit_id, original);
  assert.equal(f.sent.filter(x => x.route.includes('visit'))[1].body.source, 'cache');
});
test('fill candidate is registered and measured in current visit', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  const added = f.card('stage-fill', 'f'.repeat(24)); f.cards.push(added);
  f.tracker.refresh(f.root, 'fill'); await flush(); f.intersect(.8, added.major); f.tick(1000); await flush();
  assert.equal(f.contacts().length, 1); assert.equal(f.contacts()[0].body.stage_id, 'stage-fill');
  const visits = f.sent.filter(x => x.route.includes('visit'));
  assert.equal(visits[1].body.source, 'fill'); assert.equal(visits[0].body.visit_id, visits[1].body.visit_id);
});
test('detached card is not contacted after timer expires', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.cards[0].isConnected = false; f.tick(1000); await flush();
  assert.equal(f.contacts().length, 0);
});
test('missing poster falls back to heading region', async () => {
  const f = fixture(); f.cards[0] = f.card('no-poster', 'p'.repeat(24), false);
  f.tracker.mount(f.root, 'local'); await flush(); f.intersect(.8, f.cards[0].heading); f.tick(1000); await flush();
  assert.equal(f.contacts().length, 1);
});
test('loading poster is not contacted before image loads', async () => {
  const f = fixture(); f.cards[0].major.complete = false;
  f.tracker.mount(f.root, 'network'); await flush(); f.intersect(.8); f.tick(2000); await flush();
  assert.equal(f.contacts().length, 0);
  f.cards[0].major.complete = true; f.cards[0].major.events.load();
  f.intersect(.8); f.tick(1000); await flush(); assert.equal(f.contacts().length, 1);
});
test('failed image uses heading instead of zero-size poster', async () => {
  const f = fixture(); f.cards[0].major.naturalWidth = 0;
  f.tracker.mount(f.root, 'network'); await flush(); f.intersect(.8); f.tick(1000); await flush();
  assert.equal(f.contacts().length, 0);
  f.intersect(.8, f.cards[0].heading); f.tick(1000); await flush(); assert.equal(f.contacts().length, 1);
});
test('API sends only identifiers and source, excluding content and credentials', async () => {
  const f = fixture(); f.tracker.mount(f.root, 'network'); await flush();
  f.intersect(.8); f.tick(1000); await flush();
  assert.deepEqual(Object.keys(f.sent[0].body).sort(), ['presentation_id', 'source', 'visit_id']);
  assert.deepEqual(Object.keys(f.contacts()[0].body).sort(), ['presentation_id', 'stage_id', 'visit_id']);
});
test('failed telemetry promise does not throw or send contact', async () => {
  const f = fixture(); f.setSend(() => Promise.reject(new Error('offline')));
  f.tracker.mount(f.root, 'network'); await flush(); f.intersect(.8); f.tick(1000); await flush();
  assert.equal(f.contacts().length, 0); f.tracker.stop();
});
test('async visit completion after navigation cannot log stale contact', async () => {
  const f = fixture(); let resolveVisit;
  f.setSend(() => new Promise(resolve => {resolveVisit = resolve;}));
  f.tracker.mount(f.root, 'network'); await flush(); f.intersect(.8); f.tick(1000);
  f.tracker.stop(); resolveVisit(true); await flush(); assert.equal(f.contacts().length, 0);
});
(async () => {
  let failed = 0;
  for (const [name, fn] of tests) {
    try {await fn(); console.log('PASS ' + name);}
    catch (error) {failed++; console.error('FAIL ' + name + '\n' + error.stack);}
  }
  console.log(`${tests.length - failed}/${tests.length} passed`); process.exitCode = failed ? 1 : 0;
})();
