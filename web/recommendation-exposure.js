/* Shared by public SPA and local HTML. Contact is a proxy, never proof of reading. */
(function (global) {
  "use strict";
  function create(options) {
    const o = options || {}, doc = o.document || global.document;
    const IO = o.IntersectionObserver || global.IntersectionObserver;
    const MO = o.MutationObserver || global.MutationObserver;
    const later = o.setTimeout || global.setTimeout.bind(global);
    const cancel = o.clearTimeout || global.clearTimeout.bind(global);
    const now = o.now || (() => global.performance.now());
    const makeId = o.id || (() => {
      const bytes = new Uint8Array(18); global.crypto.getRandomValues(bytes);
      return Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
    });
    const send = o.send || (() => Promise.resolve(false));
    let root = null, vid = "", observer = null, mutations = null, active = false;
    const states = new Map(), visits = new Map(), contacted = new Set();
    function blocked() {
      return doc.visibilityState !== "visible" || Boolean(doc.querySelector('.tg-welcome, dialog[open], [aria-modal="true"]'));
    }
    function reset(s) { if (s.timer !== null) cancel(s.timer); s.timer = null; s.since = null; s.visible = false; }
    function pause() {
      if (observer) observer.disconnect(); observer = null;
      states.forEach(reset);
    }
    function stop() {
      active = false; pause();
      if (mutations) mutations.disconnect(); mutations = null;
      states.clear(); visits.clear(); contacted.clear(); root = null;
    }
    function begin(pid, source) {
      if (!visits.has(pid)) {
        const visit = vid;
        const promise = Promise.resolve().then(() => active && visit === vid ? send("/api/recommendation/visit", {
          presentation_id: pid, visit_id: visit, source
        }) : false).catch(() => false);
        visits.set(pid, promise);
      }
      return visits.get(pid);
    }
    function observe() {
      if (!active || blocked() || !IO) { pause(); return; }
      if (!observer) observer = new IO(entries => {
        for (const entry of entries) {
          const s = Array.from(states.values()).find(x => x.target === entry.target);
          if (!s || contacted.has(s.sid)) continue;
          if (!entry.isIntersecting || entry.intersectionRatio < 0.5 || blocked()) { reset(s); continue; }
          s.visible = true;
          if (s.since !== null) continue;
          s.since = now();
          s.timer = later(() => {
            s.timer = null;
            if (!active || blocked() || !s.visible || !s.card.isConnected || now() - s.since < 1000) return;
            const visit = vid;
            contacted.add(s.sid);
            begin(s.pid, s.source).then(ok => {
              // A navigation during the async visit request must not log stale contact.
              if (!ok || !active || visit !== vid || blocked() || !s.card.isConnected) return;
              return send("/api/recommendation/contact", {presentation_id: s.pid, visit_id: visit, stage_id: s.sid});
            }).catch(() => {});
          }, 1000);
        }
      }, {threshold: [0, 0.5]});
      states.forEach(s => { if (s.target && !contacted.has(s.sid)) observer.observe(s.target); });
    }
    function refresh(nextRoot, source) {
      if (!active) return;
      const scan = nextRoot || root;
      scan.querySelectorAll('.ticket.recommend').forEach(card => {
        const owner = card.closest('[data-exposure-presentation]');
        const pid = owner && owner.dataset.exposurePresentation, sid = card.dataset.stage;
        if (!pid || !sid) return;
        let s = states.get(card);
        const img = card.querySelector('.pcol img');
        // Loading images are not counted; failed/missing posters use the title.
        const target = img && !img.complete ? null : (img && img.naturalWidth > 0 ? img : card.querySelector('h3'));
        if (!s) {
          s = {card, pid, sid, source: source || "fill", target, timer: null, since: null, visible: false};
          states.set(card, s); begin(pid, s.source);
          if (img) { img.addEventListener('load', () => refresh(root, source)); img.addEventListener('error', () => refresh(root, source)); }
        } else if (s.target !== target) {
          reset(s); if (observer && s.target) observer.unobserve(s.target); s.target = target;
        }
      });
      for (const [card, s] of states) if (!card.isConnected) { reset(s); if (observer && s.target) observer.unobserve(s.target); states.delete(card); }
      observe();
    }
    function mount(nextRoot, source) {
      stop(); root = nextRoot; vid = makeId(); active = true;
      refresh(root, source || "network");
      if (MO) { mutations = new MO(() => { if (blocked()) pause(); else refresh(root, "fill"); }); mutations.observe(doc.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['open', 'aria-modal']}); }
    }
    doc.addEventListener('visibilitychange', () => { if (!active) return; if (blocked()) pause(); else refresh(root, "fill"); });
    if (global.addEventListener) {
      global.addEventListener('pagehide', () => { active = false; pause(); });
      global.addEventListener('pageshow', e => { if (e.persisted && root) mount(root, "cache"); });
    }
    return {mount, stop, refresh};
  }
  let current = null;
  global.TaguriExposure = {
    create,
    start(root, source, send) {
      if (!current) current = create({send: send || (async (path, body) => {
        const response = await global.fetch(path, {method: 'POST', credentials: 'include', headers: {
          'Content-Type': 'application/json', 'X-Taguri-Token': '__TAGURI_TOKEN__'
        }, body: JSON.stringify(body)});
        const result = await response.json(); return response.ok && result.ok === true;
      })});
      current.mount(root, source);
    },
    stop() { if (current) current.stop(); },
    refresh(root, source) { if (current) current.refresh(root, source); }
  };
})(typeof window !== 'undefined' ? window : globalThis);
