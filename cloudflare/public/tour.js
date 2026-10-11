"use strict";
/* たぐり ── 初回ガイドツアー。
 *
 * 目的: 「おすすめを開く → 興味ありを押す → 公演カレンダーや日記帳が変わる」という
 * たぐりの循環を、実際の画面を操作しながら一度で掴んでもらう。
 *
 * 作り方の方針:
 *  - app.js には手を入れない。navigate() と fragmentCache は app.js のトップレベルに
 *    あるので、ここから呼ぶだけにする(app.jsより後に読み込むこと)。
 *  - 画面の中身はRenderのAPIが返すHTML断片なので、対象の要素が無くても止まらないように、
 *    見つからなければ中央の説明カードだけを出す。
 *  - 一度終えたら localStorage に覚えて、次から自動では出さない。
 *    いつでも右下の「使い方」から開き直せる。 */
(function () {
  const KEY = "taguri_tour_done_v1";
  const BASE = (typeof REPO_BASE !== "undefined") ? REPO_BASE : "/taguri-demo";

  // 章立て: path=その画面へ移る / sel=光らせる要素(候補を順に試す) / wait="pick"=1件以上押すまで先へ進めない
  const STEPS = [
    {center: true, title: "押すだけで、おすすめが育つ",
     text: "おすすめの公演で「興味あり」を押すと、一覧とカレンダーに載ります。"
         + "実際の画面で試せます。デモなので、押しても大丈夫です。"},
    {path: "/recommend", sel: [".ticket.recommend"],
     title: "今週のおすすめは、1枚が1公演",
     text: "あらすじや出演者のほか、おすすめした理由も書いてあります。気になるかどうかを、ここで決めます。"},
    // **ここで1件も押さずに進むと、この先の画面(興味あり・カレンダー・評価待ち)が
    // 全部0件になる**(起案者の指摘・2026-10-07)。「押さずに次へ」は置かず、
    // 「興味あり」か「すでに持っている」を1件以上押すまで次へ進めない。
    {path: "/recommend", sel: [".ticket.recommend .btns:not([hidden])"], wait: "pick",
     title: "気になる公演に「興味あり」を押しましょう",
     text: "おすすめの公演から、気になるものに「興味あり」を押してください。"
         + "観に行くことが決まっている公演には「すでに持っている」を押します。"},
    {path: "/recommend/interest", fresh: true, sel: [".ticket", ".fav", "#content h1"],
     title: "押した公演は、興味ありの一覧に入ります",
     text: "追いかける公演が、ここに集まります。なぜ気になったかのメモも残せます。"},
    {path: "/calendar", fresh: true, sel: [".bar", ".cal", "#content h1"],
     title: "カレンダーで、いつまで観られるかが分かります",
     text: "上演期間が帯で並びます。券を持っている公演は、行く日も入れられます。"},
    {path: "/rate/unrated", fresh: true, sel: [".wait .rb", ".wait", "#content h1"],
     title: "観たあとは、◎○△×をつけます",
     text: "評価をつけるほど、次のおすすめがあなたの好みに近づきます。"},
    {path: "/records/works", fresh: true, sel: ["#content h1"],
     title: "評価と感想は、日記帳に残ります",
     text: "観劇史年表や「眺める」でも見返せます。記録が増えるほど、おすすめは自分向けになります。"},
    {center: true, last: true, title: "これで一通りです",
     text: "右下の「使い方」から、操作ツアーと説明動画をいつでも開けます。"},
  ];

  let idx = -1, running = false, token = 0;
  let root, spot, card, fab;

  const $ = (s, el) => (el || document).querySelector(s);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const store = {
    get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set() { try { localStorage.setItem(KEY, "1"); } catch (e) { /* 保存できなくても動く */ } },
  };

  function build() {
    root = document.createElement("div");
    root.className = "tgt-root"; root.hidden = true;
    root.innerHTML = '<div class="tgt-spot"></div><div class="tgt-card" role="dialog" aria-live="polite"></div>';
    document.body.appendChild(root);
    spot = $(".tgt-spot", root); card = $(".tgt-card", root);

    fab = document.createElement("div");
    fab.className = "tgt-fab";
    fab.innerHTML = '<button type="button" class="tgt-fab-btn" aria-haspopup="true">使い方</button>'
      + '<div class="tgt-menu" hidden>'
      + '<button type="button" data-tgt="tour">操作ツアーをはじめる</button>'
      + '<button type="button" data-tgt="video">説明動画を見る</button></div>';
    document.body.appendChild(fab);
    const menu = $(".tgt-menu", fab);
    $(".tgt-fab-btn", fab).addEventListener("click", () => { menu.hidden = !menu.hidden; });
    fab.addEventListener("click", ev => {
      const b = ev.target.closest("[data-tgt]"); if (!b) return;
      menu.hidden = true;
      if (b.dataset.tgt === "tour") start(); else openVideo();
    });
    window.addEventListener("resize", follow);
  }

  // 要素が現れるまで待つ(Renderの目覚めに最大25秒かかる)
  async function waitFor(sels, my, ms) {
    const end = Date.now() + (ms || 25000);
    while (Date.now() < end) {
      if (my !== token) return null;
      for (const s of sels) { const e = $(s, $("#content")); if (e) return e; }
      await sleep(250);
    }
    return null;
  }

  let target = null;
  // **枠は画面に固定して置くので、スクロールのたびに置き直す。** スマホでは
  // 指で送ったり、アドレスバーが縮んだりするたびに要素の位置が動き、
  // 枠だけが元の場所に残ってずれていた(起案者の指摘・2026-10-07)。
  // 画像の読み込みで下の要素が動くこともあるので、短い間隔でも置き直す。
  let raf = 0;
  const follow = () => { if (running && !raf) raf = requestAnimationFrame(() => { raf = 0; place(); }); };
  window.addEventListener("scroll", follow, {passive: true, capture: true});
  if (window.visualViewport) window.visualViewport.addEventListener("resize", follow);
  setInterval(follow, 400);
  function place() {
    if (!target || !document.contains(target)) { spot.style.display = "none"; return; }
    const r = target.getBoundingClientRect();
    const pad = 8;
    spot.style.display = "block";
    spot.style.top = (r.top - pad) + "px"; spot.style.left = (r.left - pad) + "px";
    spot.style.width = (r.width + pad * 2) + "px"; spot.style.height = (r.height + pad * 2) + "px";
  }

  function render(step, hasTarget) {
    const n = STEPS.length;
    const dots = STEPS.map((_, i) => '<i class="' + (i === idx ? "on" : "") + '"></i>').join("");
    const waiting = step.wait === "pick";
    card.className = "tgt-card" + (step.center || !hasTarget ? " mid" : "");
    card.innerHTML = '<div class="tgt-dots">' + dots + "</div>"
      + "<h3>" + step.title + "</h3><p>" + step.text + "</p>"
      + (waiting ? '<p class="tgt-hint">' + pickHint() + "</p>" : "")
      + '<div class="tgt-btns">'
      + (step.last ? '<button type="button" data-a="video">説明動画を見る</button>' : '<button type="button" data-a="skip" class="ghost">やめる</button>')
      + (idx > 0 && !step.last ? '<button type="button" data-a="back" class="ghost">戻る</button>' : "")
      // 答えていない公演がもう無い(枠を置く先が無い)ときは、押せないので進ませる
      + (waiting && !picked.size && hasTarget ? ""
         : '<button type="button" data-a="next" class="pri">'
           + (step.last ? "閉じる" : (idx === 0 ? "はじめる" : "次へ")) + "</button>")
      + "</div>";
  }

  async function show(i) {
    const my = ++token;
    idx = i;
    const step = STEPS[i];
    target = null; place();
    root.hidden = false;
    if (step.path) {
      const cur = location.pathname.slice(BASE.length) || "/";
      const same = cur === step.path || (cur === "/" && step.path === "/recommend");
      if (step.fresh && typeof fragmentCache !== "undefined") fragmentCache.clear();   // 押した結果を取り直す
      if (!same || step.fresh) navigate(step.path, "", true);
      await sleep(150);
    }
    render({...step, text: step.text}, false);
    card.classList.add("mid");
    if (step.sel) {
      // 読み込み中の文言を出しておく
      const el = await waitFor(step.sel, my);
      if (my !== token) return;
      if (el) {
        target = el;
        const top = el.getBoundingClientRect().top;
        window.scrollBy({top: top - 90, behavior: "smooth"});
        await sleep(450);
        if (my !== token) return;
      }
      render(step, !!el);
      place();
      if (step.wait === "pick") armPick(my);
    } else {
      render(step, false);
    }
  }

  // **「興味あり」「すでに持っている」を押した公演を数える。** 1件押したら枠と
  // 暗幕を外して、ほかの公演も見ながら押せるようにする。「興味なし」は数えない
  // (押しても、この先の画面には何も載らない)。
  const picked = new Set();
  function pickHint() {
    return picked.size
      ? picked.size + "件に答えました。ほかの公演も見て、気になるものがあれば押してください。"
        + "終わったら「次へ」で、押した公演がどこに載るかを見に行きます。"
      : "1件以上押すと、次へ進めます。";
  }
  function armPick(my) {
    const h = ev => {
      if (my !== token || !running) { document.removeEventListener("click", h, true); return; }
      const b = ev.target.closest && ev.target.closest(".ticket.recommend .btns button[data-v]");
      if (!b || (b.dataset.v !== "interest" && b.dataset.v !== "owned")) return;
      const box = b.closest(".btns");
      picked.add((box && box.dataset.stage) || b);
      target = null; place();
      card.classList.remove("mid");
      render(STEPS[idx], true);
    };
    document.addEventListener("click", h, true);
  }

  function go(d) {
    const next = idx + d;
    if (next < 0) return;
    if (next >= STEPS.length) { finish(); return; }
    show(next);
  }

  function finish() {
    running = false; token++; root.hidden = true; target = null;
    store.set();
  }

  function start() {
    if (running) return;
    running = true;
    // 先頭の画面で始める
    if ((location.pathname.slice(BASE.length) || "/") !== "/recommend" && (location.pathname.slice(BASE.length) || "/") !== "/") {
      navigate("/recommend", "", true);
    }
    show(0);
  }

  function openVideo() {
    const w = document.createElement("div");
    w.className = "tgt-video";
    w.innerHTML = '<div class="tgt-video-box"><button type="button" class="tgt-x" aria-label="閉じる">×</button>'
      + '<video controls autoplay playsinline preload="metadata" src="' + BASE + '/assets/taguri-howto.mp4"></video></div>';
    document.body.appendChild(w);
    const close = () => w.remove();
    w.addEventListener("click", ev => { if (ev.target === w || ev.target.closest(".tgt-x")) close(); });
    document.addEventListener("keydown", function k(ev) {
      if (ev.key === "Escape") { close(); document.removeEventListener("keydown", k); }
    });
  }

  document.addEventListener("click", ev => {
    const b = ev.target.closest && ev.target.closest(".tgt-card [data-a]");
    if (!b) return;
    const a = b.dataset.a;
    if (a === "next") go(1);
    else if (a === "back") go(-1);
    else if (a === "skip") finish();
    else if (a === "video") { finish(); openVideo(); }
  });

  document.addEventListener("keydown", ev => {
    if (running && ev.key === "Escape" && !$(".tgt-video")) finish();
  });

  document.addEventListener("DOMContentLoaded", () => {
    build();
    // 初回だけ自動で始める。復旧コードの案内(.tg-welcome)を閉じてから出す
    if (store.get()) return;
    const path = location.pathname.slice(BASE.length) || "/";
    if (path !== "/" && path !== "/recommend") return;
    (async () => {
      const end = Date.now() + 40000;
      while (Date.now() < end && !$("#content .ticket.recommend")) await sleep(300);
      while ($(".tg-welcome") && Date.now() < end + 120000) await sleep(400);
      if (!store.get() && !running) start();
    })();
  });
})();
