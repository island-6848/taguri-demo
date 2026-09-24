"use strict";
/* たぐり ── GitHub Pages版フロントエンド (#000009)。
 *
 * Render上のバックエンド(tools/taguri/serve.py + app.py)は今までどおり
 * SQLite書き込み・推薦計算を行う。このファイルは元々app.py内のPython文字列
 * 定数だった SCRIPT/PE.JS/PM.JS をほぼそのまま移植し(下の「=== ported ===」
 * 区画)、その上に薄いSPAシェル(ナビゲーション・ルーター・フラグメント読込)
 * を足しただけである。
 *
 * ポート時の変更点は最小限:
 *  - post()・各fetch呼び出しにAPI_BASEを前置(クロスオリジンなので絶対URLが要る)
 *  - X-Taguri-Tokenヘッダは送らない(demo_modeでは検査されない)
 *  - .syn .mrb のクランプ調整を、フラグメント差し込みのたびに呼べる関数に分離
 */

const API_BASE = "https://taguri-demo.onrender.com";

// --- 画面パス -> APIのスクリーン名。実装済みのものだけ IMPLEMENTED に入れる ---
const SCREENS = {
  "/": "recommend", "/recommend": "recommend",
  "/start": "start",
  "/recommend/reminder": "reminder",
  "/recommend/interest": "interest",
  "/recommend/favourites": "favourites",
  "/calendar": "calendar",
  "/tickets": "tickets",
  "/rate": "rate", "/rate/unrated": "unrated", "/rate/notes": "notes",
  "/register": "register",
  "/records": "records", "/records/trace": "trace",
  "/records/chronicle": "chronicle", "/records/works": "works",
  "/search": "search", "/settings": "settings",
};
// Phase 0-1: おすすめ・興味あり・開幕リマインド・お気に入り・カレンダーを実装。
// 残りは「準備中」を出す(段階移行のためのプレースホルダ)。
const IMPLEMENTED = new Set(["recommend", "interest", "reminder", "favourites", "calendar"]);

// --- NAV(app.py の NAV表と同じデータ) -------------------------------------
const NAV = [[null, "おすすめ", "ticket", [["/recommend", "今週のおすすめ", "ticket"], ["/recommend/reminder", "開幕リマインド", "inbox"], ["/recommend/interest", "興味あり", "flag"], ["/recommend/favourites", "お気に入り", "star"]]], ["/calendar", "公演カレンダー", "calendar", []], ["/tickets", "購入済み公演", "ticket", []], [null, "観た公演の評価", "check", [["/rate", "評価一覧", "check"], ["/rate/unrated", "未評価", "clock"], ["/rate/notes", "感想", "pencil"]]], ["/register", "公演情報の登録", "inbox", []], [null, "記録を見返す", "chart", [["/records", "眺める", "chart"], ["/records/trace", "たどる", "user"], ["/records/chronicle", "観劇史年表", "calendar"], ["/records/works", "日記帳", "book"]]], ["/search", "探す", "search", []], ["/settings", "設定", "gear", []]];

// --- 絵記号(icons.py の P/ALIAS をそのまま) --------------------------------
const ICON_P = {"ticket": "M3 9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2 2 2 0 0 0 0 6 2 2 0 0 1-2 2H5a2 2 0 0 1-2-2 2 2 0 0 0 0-6zM11 7v10", "star": "M12 3.8l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z", "inbox": "M3 12h5l1.5 2.5h5L16 12h5M3 12l3-7h12l3 7v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z", "chart": "M3 20h18M6.5 20v-5M11.5 20V6M16.5 20v-9", "search": "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM16.2 16.2 21 21", "download": "M12 3v12m0 0 4-4m-4 4-4-4M4 20h16", "mail": "M3 6h18v12H3zM3 6.5l9 6.5 9-6.5", "plus": "M12 5v14M5 12h14", "clock": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7.5V12l3.5 2", "pencil": "M4 20h4L18 10l-4-4L4 16zM13.5 6.5l4 4", "tag": "M4 12.5 12.5 4H20v7.5L11.5 20zM16.4 7.6h.01", "image": "M3 5h18v14H3zM3 15.5l5-4 4 3 3-2.5 6 4.5M8 9.5h.01", "user": "M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM4 20c0-3.3 3.6-5 8-5s8 1.7 8 5", "building": "M4 20V6l6-2.5V20M10 20h10V10.5L10 7M13.5 12h.01M13.5 16h.01M17 12h.01M17 16h.01", "book": "M4 5h7v15H4zM13 5h7v15h-7M11 5v15", "light": "M12 3v3.5M12 17.5V21M3 12h3.5M17.5 12H21M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18", "eye": "M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z", "check": "M4.5 12.5 9.5 18 20 6", "flag": "M5 21V4h13l-2.5 4.5L18 13H5", "calendar": "M4 6.5h16V20H4zM4 10.5h16M8.5 3.5v4M15.5 3.5v4", "chevron": "M9.5 5.5 16 12l-6.5 6.5", "network": "M6 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6.9 15.3 10.6 9M17.1 15.3 13.4 9M8 17.3h8", "gear": "M10.6 3.1 13.4 3.1 15.2 6.5 19.0 6.3 20.4 8.8 18.4 12.0 20.4 15.2 19.0 17.7 15.2 17.5 13.4 20.9 10.6 20.9 8.8 17.5 5.0 17.7 3.6 15.2 5.6 12.0 3.6 8.8 5.0 6.3 8.8 6.5ZM12 9.8a2.2 2.2 0 1 0 0 4.4 2.2 2.2 0 0 0 0-4.4z", "link": "M14 4h6v6M20 4 10 14M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5"};
const ICON_ALIAS = {"おすすめ": "ticket", "お気に入り": "star", "登録": "inbox", "記録": "chart", "探す": "search", "書き出す": "download", "暦": "calendar"};
function ico(name, size, cls) {
  size = size || 16; cls = cls || "";
  const d = ICON_P[ICON_ALIAS[name] || name];
  if (!d) return "";
  return '<svg class="ico ' + cls + '" viewBox="0 0 24 24" width="' + size + '" height="' + size
    + '" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
    + 'stroke-linejoin="round" aria-hidden="true"><path d="' + d + '"/></svg>';
}

// --- リポジトリの配信先(GitHub Pagesのプロジェクトサイト)を自動判定 --------
// 先頭セグメントが既知の画面名でなければ、それをリポジトリ名の接頭辞とみなす
// (ローカルでは web/ をサーバのルートに置いて確認するので接頭辞は付かない)。
const TOP_SEGMENTS = new Set(Object.keys(SCREENS).filter(p => p !== "/").map(p => p.split("/")[1]));
function detectRepoBase() {
  const segs = location.pathname.split("/").filter(Boolean);
  if (segs.length === 0 || TOP_SEGMENTS.has(segs[0])) return "";
  return "/" + segs[0];
}
const REPO_BASE = detectRepoBase();

function E(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => (
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}

// --- ナビゲーション(サイドバー)の描画。app.py の layout()/_item/_group と同じ形 ---
function navItemHtml(path, label, icon, kid) {
  return '<a href="' + path + '" class="' + (kid ? "kid" : "") + '" data-path="' + path + '">'
    + ico(icon, kid ? 16 : 18) + E(label) + "</a>";
}
function navGroupHtml(label, icon, kids) {
  return '<details class="grp" data-grp="' + E(label) + '">'
    + '<summary>' + ico(icon, 18) + '<span class="gl">' + E(label) + '</span>'
    + ico("chevron", 14, "cv") + '</summary>'
    + kids.map(c => navItemHtml(c[0], c[1], c[2], true)).join("") + '</details>';
}
function renderNav() {
  return NAV.map(([p, t, k, kids]) => p === null
    ? navGroupHtml(t, k, kids)
    : navItemHtml(p, t, k, false) + kids.map(c => navItemHtml(c[0], c[1], c[2], true)).join("")
  ).join("");
}

// **開閉状態はlocalStorageに覚える**(元のNAV_FOLD_JSと同じ挙動)。
function restoreNavFold() {
  try {
    document.querySelectorAll(".side .grp").forEach(g => {
      const v = localStorage.getItem("taguri.fold." + g.dataset.grp);
      if (v === "1") g.open = false; else if (v === "0") g.open = true;
      g.addEventListener("toggle", () => {
        try { localStorage.setItem("taguri.fold." + g.dataset.grp, g.open ? "0" : "1"); } catch (e) {}
      });
    });
  } catch (e) {}
}

// **現在地をナビとパンくずに反映する。** サーバ側の active_sub 判定と同じ規則。
function crumbsFor(path, title) {
  for (const [, label, , kids] of NAV) {
    if (kids.some(c => c[0] === path)) return [["たぐり", "/"], [label, null], [title, null]];
  }
  return [["たぐり", "/"], [title, null]];
}
function updateNavActive(path) {
  document.querySelectorAll(".side a[data-path]").forEach(a => {
    const on = a.dataset.path === path;
    a.classList.toggle("on", on);
    if (on) {
      const grp = a.closest(".grp");
      if (grp) grp.open = true;
    }
  });
}
function renderCrumbBar(path, title) {
  const nav = document.getElementById("crumbnav");
  if (!nav) return;
  const crumbs = crumbsFor(path, title);
  nav.innerHTML = crumbs.map(([label, href], i) => {
    const last = i === crumbs.length - 1;
    const part = href ? '<a href="' + href + '" data-path="' + href + '">' + E(label) + '</a>'
      : '<span' + (last ? ' aria-current="page"' : '') + '>' + E(label) + '</span>';
    return part + (last ? "" : '<span class="crumbsep" aria-hidden="true">›</span>');
  }).join("");
  document.title = "たぐり ── " + title;
}

// --- フラグメント読み込み ---------------------------------------------------
const contentEl = () => document.getElementById("content");

// **舞台の幕と、開幕準備で動き回る人型のピクトグラム。** 文章で「何をして
// いるか」を語るのではなく、ピクトグラム自身が舞台の上を歩いて回り、
// 立ち止まった先で小道具を手に取る形で見せる(起案者の指示)。枠は持たず、
// 幕もピクトグラムも背景に直接置く。色はサイト基調のえんじ
// (var(--curtain))一色 ── 案内標識のピクトグラムと同じ、顔の無い幾何学的な
// 単色シルエットにした。小道具の細部は背景色を「切り抜く」技法で表す。
function curtainValanceD(w, h, dip, scallops) {
  const seg = w / scallops;
  let d = "M0 " + h;
  for (let i = 0; i < scallops; i++) {
    d += " Q" + (i * seg + seg / 2) + " " + (h + dip) + " " + ((i + 1) * seg) + " " + h;
  }
  return d + " L" + w + " 0 L0 0 Z";
}
const CURTAIN_W = 220, CURTAIN_H = 10;
const CURTAIN_SVG = '<svg class="tg-curtain" viewBox="0 0 ' + CURTAIN_W + ' 74" aria-hidden="true">'
  + '<path class="tg-curtain-leg" d="M6 6C-6 26 0 54 14 70C22 50 14 24 6 6Z"/>'
  + '<path class="tg-curtain-leg" d="M' + (CURTAIN_W - 6) + ' 6C' + (CURTAIN_W + 6) + ' 26 '
  + CURTAIN_W + ' 54 ' + (CURTAIN_W - 14) + ' 70C' + (CURTAIN_W - 22) + ' 50 '
  + (CURTAIN_W - 14) + ' 24 ' + (CURTAIN_W - 6) + ' 6Z"/>'
  + '<path class="tg-curtain-valance" d="' + curtainValanceD(CURTAIN_W, CURTAIN_H, 16, 9) + '"/>'
  + '</svg>';

// **案内標識と同じ、幾何学的な人型ピクトグラム。** 顔・毛など飾りは持たない
// (円+角丸の四角だけの構成)。腕は前へ寄せた角度で固定し、その先(手の
// あたり)に`.tg-prop`が乗るので、小道具は常に手に持っている形になる。
const PICTO_SVG = '<svg viewBox="0 0 64 64" aria-hidden="true">'
  + '<g class="tg-picto">'
  + '<rect x="33" y="37" width="6" height="16" rx="3"/>'
  + '<rect x="25" y="37" width="6" height="16" rx="3"/>'
  + '<rect x="26" y="21" width="12" height="17" rx="5"/>'
  + '<rect class="tg-arm" x="37" y="23" width="6" height="19" rx="3" transform="rotate(-26 40 23)"/>'
  + '<rect class="tg-arm" x="21" y="23" width="6" height="19" rx="3" transform="rotate(26 24 23)"/>'
  + '<circle cx="32" cy="14" r="6"/>'
  + '<circle cx="35" cy="41" r="2.2"/>'
  + '<circle cx="29" cy="41" r="2.2"/>'
  + '<g class="tg-prop"></g>'
  + '</g></svg>';

// **立ち止まった先でする支度。** 持ち替えるだけでなく、段ごとに合った
// 動き(小道具自身のアニメーション)を付ける ── ページをめくる・面を顔に
// 当てる・金槌を振る・針を運針させる・照明を振る。`name`はCSS側で
// `.tg-picto-wrap[data-phase]`のセレクタに使う(style.cssのtg-act-*)。
// 塗りはえんじ色のまま(`tg-cutout`/`tg-stroke`/`tg-beam`で濃淡だけ作る)。
const PHASES = [
  { name: "book", prop:
    '<rect x="29" y="30" width="15" height="11" rx="1.3"/>'                  // 台本
    + '<g class="tg-cutout-line"><line x1="36.5" y1="31.5" x2="36.5" y2="39.5"/>'
    + '<line x1="31" y1="34" x2="35" y2="34"/><line x1="31" y1="37" x2="35" y2="37"/>'
    + '<line x1="38" y1="34" x2="42" y2="34"/><line x1="38" y1="37" x2="42" y2="37"/></g>' },
  { name: "mask", prop:
    '<ellipse cx="37" cy="35" rx="8" ry="9"/>'                                // 面(稽古)
    + '<g class="tg-cutout"><circle cx="34" cy="33" r="1.4"/><circle cx="40" cy="33" r="1.4"/></g>'
    + '<path class="tg-cutout-line" d="M33 39q4 3 8 0"/>' },
  { name: "hammer", prop:
    '<rect x="32" y="27" width="12" height="5" rx="1.4"/>'                    // 金槌(大道具)
    + '<rect x="36.5" y="32" width="3" height="13" rx="1.4"/>' },
  { name: "sewing", prop:
    '<path class="tg-stroke" d="M29 45 43 28"/>'                              // 針と糸(衣装)
    + '<circle class="tg-cutout" cx="43.5" cy="27" r="1.8"/>'
    + '<path class="tg-stroke" d="M29 45q-4 2 -3 7q4-1 5-5"/>' },
  { name: "light", prop:
    '<path d="M31 27h10l4 13H27z"/>'                                        // 照明
    + '<g class="tg-beam"><line x1="29" y1="41" x2="24" y2="49"/>'
    + '<line x1="36" y1="43" x2="36" y2="51"/><line x1="43" y1="41" x2="48" y2="49"/></g>' },
];

const COLD_START_NOTE = "サーバーが眠っていたら起こしています(無料枠なので少し待ちます)…";

function loadingHtml() {
  const picto = PICTO_SVG.replace('<g class="tg-prop"></g>',
    '<g class="tg-prop">' + PHASES[0].prop + '</g>');
  return '<div class="tg-loading">'
    + CURTAIN_SVG
    + '<div class="tg-scene" aria-label="舞台の準備をしているピクトグラムのアニメーション">'
    + '<div class="tg-picto-wrap" data-phase="' + PHASES[0].name + '">' + picto + '</div></div>'
    + '<div class="tg-load-bar"><div class="tg-load-fill"></div></div>'
    + '<p class="tg-load-pct">0%</p>'
    + '<p class="tg-load-note" hidden>' + COLD_START_NOTE + '</p>'
    + '</div>';
}

// **ピクトグラムを舞台の上で歩かせ、立ち止まった先ごとに段(PHASES)を
// 切り替える。** 歩いているあいだは`.walking`で足取りの弾みを速め、
// 止まったら`data-phase`を差し替える ── そのCSSセレクタで小道具ごとの
// 動作アニメーションが決まる(style.cssのtg-act-*)。
// `prefers-reduced-motion`のときは動かさず、中央で静止させる。
function startPictoWalk(scene, wrap, propEl) {
  const reduced = typeof matchMedia === "function"
    && matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) return () => {};
  const waypoints = [0.06, 0.5, 0.94];
  // **ph は1から。** 最初の段(PHASES[0])はloadingHtml()で最初から
  // 出してあるので、最初の到着でまた同じものにすると変わり映えしない。
  let wp = 0, ph = 1, x = 0, stopped = false;
  const timers = [];
  const t = (fn, ms) => { const id = setTimeout(fn, ms); timers.push(id); return id; };

  function step() {
    if (stopped) return;
    const travel = Math.max(0, scene.clientWidth - wrap.offsetWidth);
    const nx = Math.round(waypoints[wp] * travel);
    wrap.style.setProperty("--facing", nx >= x ? 1 : -1);
    wrap.style.setProperty("--x", nx + "px");
    x = nx;
    wrap.classList.add("walking");
    if (propEl) propEl.classList.add("swap");
    t(() => {
      if (stopped) return;
      wrap.classList.remove("walking");
      if (propEl) {
        const phase = PHASES[ph % PHASES.length];
        propEl.innerHTML = phase.prop;
        propEl.classList.remove("swap");
        wrap.dataset.phase = phase.name;
        ph++;
      }
      t(() => { wp = (wp + 1) % waypoints.length; step(); }, 2200);
    }, 700);
  }
  step();
  return () => { stopped = true; timers.forEach(clearTimeout); };
}

// **表示 → ピクトグラムを歩かせる・進捗%を進める → 呼び出し側が止める、
// までを1つにまとめる。** 本当の進み具合(コールドスタートでサーバが
// 起きるまでの時間)は分からないので、経過時間から95%まで滑らかに近づける
// 「気持ちの上では正しい」進捗にする。5秒以上かかっていたら、コールド
// スタートの案内をそっと添える(待たされる理由が分からないと不安になるため)。
function startLoading(el) {
  el.innerHTML = loadingHtml();
  const t0 = performance.now();
  const fill = el.querySelector(".tg-load-fill");
  const pct = el.querySelector(".tg-load-pct");
  const note = el.querySelector(".tg-load-note");
  const scene = el.querySelector(".tg-scene");
  const wrap = el.querySelector(".tg-picto-wrap");
  const propEl = el.querySelector(".tg-prop");

  const stopWalk = (scene && wrap) ? startPictoWalk(scene, wrap, propEl) : () => {};

  const tick = () => {
    if (!fill || !fill.isConnected) return;
    const elapsed = performance.now() - t0;
    const p = Math.min(95, Math.round(95 * (1 - Math.exp(-elapsed / 6000))));
    fill.style.width = p + "%";
    if (pct) pct.textContent = p + "%";
  };
  tick();
  const progressTimer = setInterval(tick, 150);
  const noteTimer = setTimeout(() => { if (note && note.isConnected) note.hidden = false; }, 5000);

  return () => {
    clearInterval(progressTimer);
    clearTimeout(noteTimer);
    stopWalk();
    if (fill && fill.isConnected) {
      fill.style.width = "100%";
      if (pct) pct.textContent = "100%";
    }
  };
}

// **同じ画面(同じパス+検索条件)を、タブを開いている間だけ覚えておく。**
// 起案者の指摘 ──「1回の起動内で同じページにアクセスするなら読み込み時間を
// 短くできないか」。Renderのコールドスタートが終わったあとでも、押すたびに
// 毎回サーバへ取りに行くと同じだけ待たされていた。**書き込み(反応・評価・
// 設定変更など)が起きたら全部消す** ── どの画面の材料が変わったかをここでは
// 判別しないので、安全側に倒して丸ごと作り直す(`post()`から呼ぶ)。
const fragmentCache = new Map();

function renderScreen(el, activePath, d) {
  el.innerHTML = d.body_html;
  renderCrumbBar(activePath, d.title || "");
  updateNavActive(activePath);
  fixupSynClamp(el);
  fixupMonthScroll(el);
  el.querySelectorAll('img[src^="/img/"]').forEach(img => {
    img.src = API_BASE + img.getAttribute("src");
  });
}

async function loadScreen(path, search) {
  const name = SCREENS[path];
  const el = contentEl();
  if (!name) {
    el.innerHTML = "<h1>見つかりません</h1><p>このページはありません。"
      + '<a href="/" data-path="/">おすすめへ戻る</a></p>';
    renderCrumbBar("/", "見つかりません");
    updateNavActive("");
    return;
  }
  if (!IMPLEMENTED.has(name)) {
    el.innerHTML = "<h1>この画面は準備中です</h1>"
      + "<p>GitHub Pages移行はPhase 0(今週のおすすめ)のみ対応しています。"
      + "現行の全画面版は <a href=\"" + API_BASE + path + "\">Renderの旧UI</a> で見られます。</p>";
    renderCrumbBar(path, "準備中");
    updateNavActive(path);
    return;
  }
  // `/` は「今週のおすすめ」と同じ画面の別入口(app.pyのpage_recommendが
  // active_sub="/recommend"を返すのと同じ扱いにする)。
  const activePath = path === "/" ? "/recommend" : path;
  const cacheKey = name + "?" + search;
  const cached = fragmentCache.get(cacheKey);
  if (cached) {
    renderScreen(el, activePath, cached);
    return;
  }
  const stopLoading = startLoading(el);
  let d;
  try {
    const url = API_BASE + "/api/screen/" + name + (search ? "?" + search : "");
    const r = await fetch(url);
    d = await r.json();
    if (!r.ok || !d.ok) throw new Error(d.error || r.status);
  } catch (e) {
    stopLoading();
    el.innerHTML = "<h1>読み込めませんでした</h1><p>" + E(String(e)) + "</p>";
    return;
  }
  stopLoading();
  fragmentCache.set(cacheKey, d);
  renderScreen(el, activePath, d);
}

// --- SPAルーター:内部リンク・GETフォームをその場遷移に変える ----------------
function stripToken(usp) { usp.delete("t"); return usp; }

function navigate(path, search, push) {
  const usp = stripToken(new URLSearchParams(search || ""));
  const qs = usp.toString();
  const display = REPO_BASE + path + (qs ? "?" + qs : "");
  if (push !== false) history.pushState(null, "", display);
  window.scrollTo(0, 0);
  loadScreen(path, qs);
}

function isInternalPath(p) {
  return p.startsWith("/") && !p.startsWith("/img/") && !p.startsWith("/vendor")
    && !p.startsWith("/api/") && !p.startsWith("/export.json") && !p.startsWith("/data.zip");
}

document.addEventListener("click", ev => {
  const a = ev.target.closest("a[href]");
  if (!a) return;
  const href = a.getAttribute("href");
  if (!href || /^[a-z]+:/i.test(href) || href.startsWith("#")) return;
  let path = href.split("#")[0], search = "";
  const qi = path.indexOf("?");
  if (qi >= 0) { search = path.slice(qi + 1); path = path.slice(0, qi); }
  if (!path || !isInternalPath(path)) return;
  ev.preventDefault();
  navigate(path, search);
}, true);

document.addEventListener("submit", ev => {
  const f = ev.target.closest("form");
  if (!f) return;
  const method = (f.getAttribute("method") || "get").toLowerCase();
  if (method !== "get") return;
  const action = f.getAttribute("action") || location.pathname;
  if (!isInternalPath(action)) return;
  ev.preventDefault();
  const usp = new URLSearchParams(new FormData(f));
  navigate(action, usp.toString());
});

window.addEventListener("popstate", () => {
  const path = (location.pathname.slice(REPO_BASE.length) || "/");
  loadScreen(path, location.search.replace(/^\?/, ""));
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelector(".side").insertAdjacentHTML("beforeend", renderNav());
  restoreNavFold();
  const path = (location.pathname.slice(REPO_BASE.length) || "/");
  loadScreen(path, location.search.replace(/^\?/, ""));
});

// =========================================================================
// === ported: 元は tools/taguri/app.py の SCRIPT 文字列定数(操作のJS本体) ===
// =========================================================================

const T = "";
const live = true;  // GitHub Pages版は常にボタンが有効
if (!live) document.querySelectorAll(
    ".btns,.rb,.fav-add,.miss-add,.imp,.add-work,.ed-btns,.sug,.mergeq,.drop-row,"
    + ".ed-link,.ns-body,.wbox,.addtk,.chfoot")
    .forEach(g => g.classList.add("dead"));
const dn = document.querySelector(".dead-note");
if (dn) dn.hidden = live;

// **あらすじが 3 行に収まっているときは「続きを読む」を出さない**（起案者の指示・
// 2026-08-26 ──「あらすじで隠れているものがない場合は『続きを読む』を表示しないで」）。
// **CSS の `line-clamp` だけでは、実際にあふれているかを判定できない**（あふれて
// いるかを問う疑似クラスは無い）ので、描いたあとの高さで判定する ── 畳んだ高さ
// （`clientHeight`）と、全部表示したときの高さ（`scrollHeight`）が同じなら、
// 畳んでも隠れている行は無い。`.cast`（出演者の「ほか N 名」）は件数で出し分けて
// いるので対象にしない ── `.syn .mrb` に絞る。
function fixupSynClamp(root) {
  (root || document).querySelectorAll(".syn .mrb").forEach(b => {
    const t = b.closest(".syn")?.querySelector(".txt");
    if (t && t.scrollHeight <= t.clientHeight + 1) b.style.display = "none";
  });
}
fixupSynClamp(document);

async function post(path, body, group, done) {
  const said = group ? group.querySelector(".said") : null;
  try {
    const r = await fetch(API_BASE + path, {method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)});
    const d = await r.json();
    if (!r.ok) { if (said) said.textContent = "できなかった: " + (d.error || r.status); return null; }
    if (said && done !== null) said.textContent = done || "記録した";
    fragmentCache.clear();  // 書き込みが起きたので、覚えていた画面はすべて古くなる
    return d;
  } catch (e) { if (said) said.textContent = "できなかった: " + e; return null; }
}

// 段の名前と札。**画面に出す言葉は 1 か所（WEIGHT_STEPS）から取る** ──
// 画面の側にも書くと、つまみの位置と札の言葉がずれる
const WSTEPS = ["off", "weak", "mid", "strong", "max"], WLABEL = {"off": "効かせない", "weak": "あまり効かせない", "mid": "ふつう", "strong": "少し強く", "max": "とても強く"};

// **貼った本文からのタグの読み取りは、別スレッドで数十秒かかる。** 押した直後の
// 応答にはまだタグが無いので、届くまで数秒おきに確かめ、届いた枠だけ差し替える ──
// 開き直さないとタグが出ない、という手待ちを無くすためである（起案者の指示・2026-08-26）。
function pollHandTheme(sid, el, tries) {
  if (tries >= 10 || !el.isConnected) return;          // 約 40 秒で諦める
  setTimeout(() => {
    post("/api/hand_theme_refresh", {stage_id: sid}, null, null).then(d => {
      if (!d) return;
      const w = document.createElement("div");
      w.innerHTML = d.html;
      const fresh = w.firstElementChild;
      if (fresh && fresh.querySelector(".tags")) { el.replaceWith(fresh); return; }
      pollHandTheme(sid, el, tries + 1);
    });
  }, 4000);
}

// **つまみを動かしても保存しない。** 変わったのは画面の上だけであることを、
// 札と確定の押し口の色で言う ── 動かしただけで効いたと読まれないためである
document.addEventListener("input", ev => {
  const sl = ev.target.closest && ev.target.closest(".wsl");
  if (!sl) return;
  const row = sl.closest(".wrow"), box = sl.closest(".wbox");
  const step = WSTEPS[+sl.value];
  row.querySelector(".wv").textContent = WLABEL[step];
  row.classList.toggle("off", step === "off");
  box.classList.add("dirty");
  const said = box.querySelector(".wsaid");
  if (said) said.textContent = "まだ確定していません";
});

document.addEventListener("click", ev => {
  if (!live) return;
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.v) {
    const g = b.closest(".btns,.rb");
    const path = g.dataset.stage ? "/api/react" : "/api/rate";
    const body = g.dataset.stage ? {stage_id: g.dataset.stage, value: b.dataset.v}
                                 : {work_key: g.dataset.work, verdict: b.dataset.v};
    // **答えた枠を次の候補で埋めるために、いま出している分を送る**（起案者の指示・
    // 2026-08-24 ──「三択のボタンを押したら、まだ在庫があるなら別の候補に入れ替えて
    // 表示すべきだね」）。**在庫は画面の側にしか無い** ── 何を出しているかを知って
    // いるのは画面だけなので、除く分を送らないと、いま並んでいる 1 枚がもう 1 枚増える。
    // **推薦の枠だけが対象である** ── 興味あり・お気に入りは順位で切った枠ではないので、
    // 埋める先が無い
    const slot = b.closest(".ticket.recommend");
    if (slot) body.shown = [...document.querySelectorAll(".ticket.recommend")]
                             .map(a => a.dataset.stage).filter(Boolean);
    // **もぎれる。** 押した結果が形で分かる（記録できなかったら元に戻す）。
    // **評価待ちの行は ◎○△× を押したときに外れる**（起案者の指示・2026-08-24）──
    // 半券がもぎられるのは劇場に入るときなので、観終わった 1 枚が外れる形にする。
    // 「まだ判断できない」では外さない ── 評価し終わっていない
    const tk = b.closest(".ticket");
    const wt = b.closest(".wait");
    const row = tk || wt;
    const tear = (tk && b.dataset.v === "interest")
              || (wt && "◎○△×".indexOf(b.dataset.v) >= 0);
    if (tear) row.classList.add("torn");
    post(path, body, g).then(d => {
      if (!d) { if (tear) row.classList.remove("torn"); return; }
      g.classList.add("done");
      // **押した評価を、その場で余白に押す**（起案者の指示 ──「一個操作したら適宜
      // リロードしてほしい」の趣旨。ここは読み込み直さずに済む）。**判子が出ないと、
      // 押したのに何も起きていないように見える** ── 以前は評価の字が出るのは次に
      // 開いたときだった。**感想の欄も同時に開く** ── 観た帰りに ◎ を押す瞬間が、
      // いちばん言葉の出てくる瞬間である（焦点を移すのは ◎ のときだけ）
      const rr = b.closest(".rec-row");
      if (rr && rr.querySelector("[data-stamp]")) {
        const st = rr.querySelector("[data-stamp]");
        st.className = "stamp" + (b.dataset.v.length > 1 ? " hold" : "");
        st.textContent = b.dataset.v;
        st.removeAttribute("aria-label");
        const box = rr.querySelector(".inote");
        if (box && !rr.querySelector(".inr")) {
          box.hidden = false;
          if (b.dataset.v === "◎") box.querySelector("textarea").focus();
        }
      }
      if (tk && b.dataset.v === "interest") {
        const wn = tk.querySelector(".why-note");
        if (wn) { wn.hidden = false; wn.querySelector("textarea").focus(); }
      }
      // **評価を押した直後に、感想の欄を開く。** 観た帰りに ◎ を押す瞬間が、いちばん
      // 言葉が出てくる瞬間である。**焦点を移すのは ◎ のときだけ** ── 引用が返るのは
      // ◎ の作品だけなので、× や △ で書くよう促すと返りの無い入力になる
      const wn2 = g.parentElement && g.parentElement.querySelector(".wnote");
      if (wn2) {
        wn2.hidden = false;
        if (b.dataset.v === "◎") wn2.querySelector("textarea").focus();
      }
      // **答えた枠を、次の候補で埋める**（起案者の指示・2026-08-24）。
      //
      // **「すでに持っている」で画面を読み込み直すのをやめた。** 前は 900ms 後に
      // `location.reload()` していた（同日の指示「一個操作したら適宜リロードして
      // ほしい」による）。**撤回の理由は 2 つある** ── ① 読み込み直すと読んでいた
      // 場所を失う。15 枚を上から見ている途中に先頭へ戻される。② 埋めるだけなら
      // 作り直す必要が無い。**「操作した結果がすぐ出る」という元の趣旨は、押した
      // 1 枚に印が付き、入れ替わりの 1 枚がその場で増えることで満たしている。**
      //
      // **押した 1 枚は消さずに残す。** 興味あり・興味なしは直後に理由の欄が開くので、
      // 消すと書いている途中の欄ごと消える。**足す先は一覧のいちばん下** ── 上から
      // 下へ読む画面なので、読み進む先に現れる。点の高い順という並びも壊れない。
      if (d.fill) {
        const said = g.querySelector(".said");
        if (d.fill.said && said) said.textContent = d.fill.said;
        if (d.fill.html) {
          const all = document.querySelectorAll(".ticket.recommend");
          const box = document.createElement("div");
          box.innerHTML = d.fill.html;
          const fresh = box.firstElementChild;
          if (fresh && all.length) {
            fresh.classList.add("filled");
            all[all.length - 1].after(fresh);
            bindNotes(fresh);          // 足した 1 枚の入力欄にも動きを付ける
          }
        }
      }
      // **見送った理由は出すだけで、開かない。** 書く頻度が低い入力なので、
      // 焦点まで移すと「書かないと進めない」ように見える
      if (b.dataset.v === "nointerest") {
        const row = b.closest(".ticket, .fav");
        const nn = row && row.querySelector(".nn");
        if (nn) nn.hidden = false;
      }
    });
  } else if (b.dataset.fav === "add") {
    const g = b.closest(".fav-add"), i = g.querySelector("#fav-name");
    if (!i.value.trim()) return;
    post("/api/favourite", {action: "add", kind: g.querySelector("#fav-kind").value,
      name: i.value.trim()}, g, "登録しました")
      .then(d => { if (d) { i.value = ""; waitJob(g, true); } });
  } else if (b.dataset.fav === "promote") {
    const r = b.closest(".prom");
    post("/api/favourite", {action: "add", kind: b.dataset.kind, name: b.dataset.name}, r,
      "登録しました（この名前の公演は、件数の制限なしに新着に出ます）")
      .then(d => { if (d) { r.classList.add("done"); b.disabled = true; waitJob(r, true); } });
  } else if (b.dataset.fav === "remove") {
    const t = b.closest(".tag");
    post("/api/favourite", {action: "remove", kind: t.dataset.kind, name: t.dataset.name},
      t.parentElement).then(d => { if (d) { t.remove(); waitJob(t.parentElement, true); } });
  } else if (b.dataset.dec === "add") {
    // **出さない語を確定する。** 候補の札から押す道と、自分で打つ道の 2 つがある
    const r = b.closest(".prom"), box = b.closest(".pbox");
    const w = b.dataset.word || (box.querySelector("#dec-word") || {}).value || "";
    if (!w.trim()) return;
    post("/api/decline", {action: "add", word: w.trim()}, r || b.parentElement,
      "出さないことにしました")
      .then(d => { if (d) { if (r) { r.classList.add("done"); b.disabled = true; }
                            waitJob(r || b.parentElement, true); } });
  } else if (b.dataset.dec === "remove") {
    const t = b.closest(".tag");
    post("/api/decline", {action: "remove", word: t.dataset.word}, t.parentElement,
      "戻しました")
      .then(d => { if (d) { t.remove(); waitJob(t.parentElement, true); } });
  } else if (b.classList.contains("rsx")) {
    // **「なぜ出てきたか」の 1 行を消す。**（起案者の指示・2026-08-26 ──
    // 「『なぜ出てきたか』は各項目に×ボタンをつけて不要な推薦は今後消せるように
    // してほしい」）。網 a（申告）は登録を外し、網 b・c（人物・内容）は
    // 「出さない語」に足す ── どちらも既存の口をそのまま呼ぶ。
    // **押した行をその場で消す。** 組み直しは数秒かかるので、消えるまで待たせない
    const li = b.closest("li.rs");
    b.disabled = true;
    const req = b.dataset.kind
      ? post("/api/favourite", {action: "remove", kind: b.dataset.kind, name: b.dataset.name},
             null, null)
      : post("/api/decline", {action: "add", word: b.dataset.word}, null, null);
    req.then(d => { if (d) { li.remove(); waitJob(null, true); } else { b.disabled = false; } });
  } else if (b.dataset.miss) {
    const g = b.closest(".miss-add"), i = g.querySelector("#miss-title");
    if (!i.value.trim()) return;
    // **登録した直後に演者とあらすじを調べに行く。** 終わるまで `waitJob` が
    // 進み具合を見に行き、終わったら読み込み直す ── 押した本人からは、
    // 調べ終わるまで何も起きなかったように見えないようにする。
    // **打っている途中の入力は無い**（欄はここで空にする）ので、読み込み直して困らない
    post("/api/missed", {title: i.value.trim()}, g,
         "登録しました ── 演者とあらすじを調べています…")
      .then(d => { if (d) { i.value = ""; waitJob(g, true); } });
  } else if (b.dataset.imp) {
    const g = b.closest(".imp");
    b.disabled = true;
    // **押した瞬間に帯を出す。** 返事は数百ミリ秒で返るが、そこまで何も動かないと
    // 押せたのかどうかが分からない ── 待ちの形は押した時点から出す
    IMP_T0 = Date.now();
    prog({running: true, step: 1, total: 0, n: 0, name: "購入確認メールを探しています"});
    post("/api/import_mail", {}, g, "取り込みを始めました").then(d => {
      if (!d) { b.disabled = false; return; }
      poll(g, b);
    });
  } else if (b.dataset.reload) {
    // **終わってから、本人が押したときだけ読み込み直す。** 待つ間にこの画面の下で
    // 手入力を書いていることがあるので、勝手に入れ替えない
    b.disabled = true;
    location.reload();
  } else if (b.dataset.addWork) {
    const g = b.closest(".add-work");
    const t = g.querySelector("#w-title"), dt = g.querySelector("#w-date");
    if (!t.value.trim()) return;
    post("/api/add_work", {title: t.value.trim(), date: dt.value,
      venue: g.querySelector("#w-venue").value,
      time: g.querySelector("#w-time").value,
      stage_id: g.querySelector("#w-stage").value}, g, "登録しました（評価待ちに並びます）")
      .then(d => {
        if (!d) return;
        t.value = ""; g.querySelector("#w-stage").value = "";
        document.getElementById("sug").replaceChildren();
        if (askMerge(g.parentElement, d.work_key, d.similar)) return;
        // **材料を取り終えてから作り直す。** すぐ読み込み直すと、取りに行っている
        // 最中の画面（ポスターの無い行）が出て、押した結果が見えない
        waitJob(g, true);
      });
  } else if (b.dataset.addFound) {
    // **探して見つけた、終わった公演を、その場で観た記録として登録する。**
    // 経路は「公演情報の登録」②（手で足す）と同じ /api/add_work（`RR.register_button`）
    const g = b.closest(".act") || b.parentElement;
    b.disabled = true;
    post("/api/add_work", {title: b.dataset.title, date: b.dataset.date,
      venue: b.dataset.venue, stage_id: b.dataset.addFound}, g,
      "登録しました（評価待ちに並びます）")
      .then(d => { if (d) waitJob(g, true); else b.disabled = false; });
  } else if (b.dataset.sugWeb) {
    sugWeb();
  } else if (b.dataset.pick) {
    // **候補を選んだら、そのまま欄に入れる。** 打ち直させない
    const r = b.closest(".sug-row"), g = document.querySelector(".add-work");
    g.querySelector("#w-title").value = r.dataset.title;
    g.querySelector("#w-date").value = r.dataset.date || "";
    g.querySelector("#w-venue").value = r.dataset.venue || "";
    g.querySelector("#w-stage").value = r.dataset.stage || "";
    document.getElementById("sug").replaceChildren();
    g.querySelector(".said").textContent = "候補から入れました。内容を確かめて登録してください";
  } else if (b.dataset.merge) {
    const g = b.closest(".mergeq");
    post("/api/merge_work", {work_key: b.dataset.mergeWork, other: b.dataset.merge}, g,
      null).then(d => {
      if (!d) return;
      g.querySelector(".said").textContent =
        "「" + d.kept_title + "」にまとめました"
        + (d.moved.length ? "（" + d.moved.join("と") + "も移しました）" : "")
        + " ── 画面を読み込み直します";
      setTimeout(() => location.reload(), 1400);
    });
  } else if (b.dataset.mergeNo) {
    const g = b.closest(".mergeq");
    g.querySelector(".said").textContent = "別の公演として、そのままにします";
    g.querySelectorAll("button").forEach(x => x.disabled = true);
    setTimeout(() => location.reload(), 1200);
  } else if (b.dataset.unmerge) {
    const g = b.closest(".ed-btns") || b.parentElement;
    post("/api/merge_work", {work_key: b.dataset.unmerge, unmerge: true}, g,
      "まとめを取り消しました ── 画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 1000); });
  } else if (b.dataset.wsave) {
    // **確定を押したときに 1 回だけ書き、そこで読み込み直す**（起案者の指示・2026-08-24）。
    // つまみを動かすたびに書く形をやめた ── 7 つを続けて動かしたいのに、1 つ動かす
    // ごとに画面が入れ替わってしまう
    const box = b.closest(".wbox"), w = {};
    box.querySelectorAll(".wsl").forEach(sl => {
      w[sl.dataset.weight] = WSTEPS[+sl.value];
    });
    post("/api/weight", {weights: w}, null, null).then(d => {
      const said = box.querySelector(".wsaid");
      if (!d) { if (said) said.textContent = "できなかった"; return; }
      box.classList.remove("dirty");
      if (said) said.textContent = "この効かせ方で読み込み直します…";
      // **押した直後だけは開いたまま戻る。** 「推薦に出なくなった公演が N 件」の
      // 知らせはこの欄の中にあるので、畳んで戻すと押した結果が見えない
      location.hash = "weights";
      setTimeout(() => location.reload(), 500);
    });
  } else if (b.dataset.wreset) {
    const box = b.closest(".wbox"), w = {};
    box.querySelectorAll(".wsl").forEach(sl => { w[sl.dataset.weight] = "mid"; });
    post("/api/weight", {weights: w}, null, null).then(d => {
      if (!d) return;
      location.hash = "weights";
      setTimeout(() => location.reload(), 400);
    });
  } else if (b.dataset.setPref || b.dataset.setPrefAll) {
    // **設定は「押したときに 1 回だけ書く」**（効かせ方と同じ規約）。チェックの
    // 並びは `.pfil` の form が持っているので、そこから読む ── 別の場所に状態を
    // 二重に持たない
    const card = b.closest("#pref-setting");
    const prefs = b.dataset.setPrefAll ? [] :
      [...card.querySelectorAll('input[name="pref"]:checked')].map(i => i.value);
    post("/api/pref_setting", {prefs}, card,
      "保存しました ── 次に開いたときから効きます").then(d => {
      if (d) setTimeout(() => location.reload(), 700);
    });
  } else if (b.dataset.unseen) {
    // **押したら一覧から外れる**（起案者の指示・2026-08-24）。評価待ちを開くたびに
    // 作り直すようにしたので、読み込み直せば実際に消える。**書く欄は開かない操作なので、
    // ここで読み込み直しても入力が消えることはない**
    const g = b.closest(".ns-body") || b.parentElement;
    post("/api/unseen", {work_key: b.dataset.unseen, unseen: true}, g,
      "行かなかったと記録しました ── 一覧から外します")
      .then(d => {
        if (!d) return;
        g.classList.add("done");
        const row = b.closest(".wait, .rec-row");
        if (row) row.classList.add("skipped");
        setTimeout(() => location.reload(), 900);
      });
  } else if (b.dataset.seen) {
    const g = b.closest(".rb") || b.parentElement;
    post("/api/unseen", {work_key: b.dataset.seen, unseen: false}, g,
      "観た公演に戻しました ── 画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 900); });
  } else if (b.dataset.drop) {
    // **2 回押させる。** 取り消しは戻せるが、押し間違いに気づく機会は要る
    const g = b.closest(".ed-btns") || b.parentElement;
    if (b.dataset.armed !== "1") {
      b.dataset.armed = "1";
      b.textContent = "本当に取り消す（あとで戻せます）";
      return;
    }
    post("/api/drop_work", {work_key: b.dataset.drop}, g,
      "取り消しました ── 「取り消した記録」から戻せます")
      .then(d => { if (d) setTimeout(() => location.reload(), 1200); });
  } else if (b.dataset.handtheme) {
    // **入れた内容は、押したときに 1 回だけ送る。** 打っている途中で送ると、
    // 打ち終わる前の断片が推薦の材料に入る
    const g = b.closest(".syn"), v = s => (g.querySelector(s) || {}).value || "";
    const sid = b.dataset.handtheme;
    // **出演者・作り手は役職ごとの欄をまとめて 1 つの fields にする。**
    // 日記帳の「手で入れる」（`data-handSave`）と同じ集め方
    const fields = {};
    g.querySelectorAll(".ht-cast[data-hand]").forEach(t => { fields[t.dataset.hand] = t.value; });
    b.disabled = true; b.textContent = "保存しています…";
    post("/api/hand_theme", {stage_id: sid, words: v(".ht-w"),
                             synopsis: v(".ht-s"), url: v(".ht-u"), fields}, null, null).then(d => {
      if (!d) { b.disabled = false; b.textContent = "保存する"; return; }
      // **押した結果をその場で出す。** あらすじの枠ごと差し替える（`syn_block`）
      const w = document.createElement("div");
      w.innerHTML = d.html;
      const el = w.firstElementChild;
      if (el) {
        if (d.said) {
          const n = document.createElement("p");
          n.className = "hsaid"; n.textContent = d.said;
          el.appendChild(n);
        }
        g.replaceWith(el);
        // **読み取り中なら、開き直させずに自分で拾いに行く。**
        if (d.read) pollHandTheme(sid, el, 0);
      }
    });
  } else if (b.dataset.handSave) {
    // **書いた内容を、押したときに 1 回だけ書く。** 打っている途中で送ると、
    // 名前を打ち終わる前の断片が名簿に入る
    const g = b.closest(".hand"), f = {};
    g.querySelectorAll("[data-hand]").forEach(t => { f[t.dataset.hand] = t.value; });
    post("/api/hand_credits", {work_key: g.dataset.work, fields: f},
         b.closest(".pfoot"), null).then(d => {
      if (!d) return;
      const said = b.closest(".pfoot").querySelector(".said");
      if (said) said.textContent = d.said || "保存しました";
      // **畳んだ見出しの人数も直す。** 開いたまま数だけ古いと、
      // 入ったのがいくつなのか読めない
      const sm = g.querySelector("summary");
      if (sm) sm.textContent = "ポスター・クレジットを手入力する"
        + (d.n ? "（出演者 " + d.n + " 名を入れてあります）" : "");
    });
  } else if (b.dataset.handOff) {
    const g = b.closest(".hand");
    post("/api/hand_poster", {work_key: b.dataset.handOff, drop: true}, g,
      "手で入れたポスターを外しました ── 画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 1000); });
  } else if (b.dataset.lkWeb) {
    // **付け替える欄からも外の公演情報を探せるようにする**（起案者の報告・2026-08-24
    // ──「どれだけ試してもポスターが違ったり、出演者が取得できなかったりした」）。
    // **手元にしか無い公演しか選べなかったので、直せない記録があった** ── 実測で
    // 「ナディラ」「明日、泣けない女 昨日、甘えた男」は候補が 0 件で、外す以外に
    // 押せる口が無かった。**打っている最中には行かない**（押したときだけ・守り 5）
    const i = b.closest(".ed-link").querySelector("[data-lk-q]");
    if (i) lkSearch(i, true, b);
  } else if (b.dataset.link) {
    const g = b.closest(".ed-link");
    post("/api/link_stage", {work_key: g.dataset.work, stage_id: b.dataset.link}, g,
      "結び付けました ── 材料を取りに行きます")
      .then(d => { if (d) waitJob(g, true); });
  } else if (b.dataset.unlink) {
    const g = b.closest(".ed-link");
    post("/api/link_stage", {work_key: b.dataset.unlink, stage_id: ""}, g,
      "結び付けを外しました").then(d => { if (d) setTimeout(() => location.reload(), 1000); });
  } else if (b.dataset.restore) {
    const g = b.parentElement;
    post("/api/restore_work", {key: b.dataset.restore}, g, "戻しました")
      .then(d => { if (d) setTimeout(() => location.reload(), 900); });
  } else if (b.dataset.purge) {
    // **2 回押させる。** 除外そのものは動かないが、「取り消した記録」からは
    // 戻す口ごと消える ── 押し間違いに気づく機会は要る
    const g = b.parentElement;
    if (b.dataset.armed !== "1") {
      b.dataset.armed = "1";
      b.textContent = "本当に完全に取り消す（一覧から消えます）";
      return;
    }
    post("/api/purge_work", {key: b.dataset.purge}, g,
      "完全に取り消しました ── この一覧から消えます")
      .then(d => { if (d) setTimeout(() => location.reload(), 900); });
  } else if (b.dataset.fix) {
    // 公演詳細の直し。**題名は作品ごと、上演日・開演時刻・劇場は回ごとに送る**
    const g = b.closest(".editor");
    const t = g.querySelector("[data-ed-title]");
    const shows = [...g.querySelectorAll(".ed-show")].map(r => ({
      uid: r.dataset.uid || "",
      date: r.querySelector("[data-ed-date]").value,
      time: (r.querySelector("[data-ed-time]") || {}).value,
      venue: (r.querySelector("[data-ed-venue]") || {}).value}));
    b.disabled = true;
    post("/api/fix_work", {work_key: b.dataset.fix, title: t.value, shows},
         g.querySelector(".ed-btns"), null).then(d => {
      b.disabled = false;
      if (!d) return;
      const said = g.querySelector(".ed-btns .said");
      said.textContent = d.n
        ? (d.gone ? "直しました ── この題名は演劇でないものとして候補から外れます"
                  : (d.moved ? "直しました（評価と感想も新しい題名へ引き継ぎました）"
                             : "直しました"))
        : "変わったところはありませんでした";
      // **近い記録があれば、読み込み直す前に聞く。** 読み込み直すと質問ごと消える
      if (askMerge(g, d.work_key || b.dataset.fix, d.similar)) return;
      if (d.n) setTimeout(() => location.reload(), 1200);
    });
  } else if (b.dataset.unfix) {
    const g = b.closest(".editor");
    post("/api/fix_work", {work_key: b.dataset.unfix, clear: true},
         g.querySelector(".ed-btns"), "抽出結果に戻した ── 画面を読み込み直す").then(d => {
      if (d) setTimeout(() => location.reload(), 900);
    });
  } else if (b.dataset.mail) {
    // **メールの中身は押したときに読む。** 一覧を開くだけで 195 通を読むのは無駄で、
    // 本文はどこにも保存しない（企画書 2 章）
    const g = b.closest(".editor"), box = g.querySelector(".ed-mail");
    box.hidden = !box.hidden;
    if (!box.hidden) box.querySelectorAll("[data-hints]").forEach(hints);
  } else if (b.dataset.why) {
    // **追いかけている一覧で、理由を書く／書き直す。** 入力欄を並べない代わりの押し口
    const w = b.closest(".wnw"), wn = w.querySelector(".why-note"), r = w.querySelector(".wnr");
    if (r) r.hidden = true; else b.hidden = true;
    wn.hidden = false;
    wn.querySelector("textarea").focus();
  } else if (b.dataset.noteOpen) {
    // **感想は押してから開く。** 107 行に入力欄を並べると、読みに来た画面が入力用紙になる
    // **押し口は `.inw` の外にも出る。** まだ何も書いていない記録では「感想を書く」が
    // 押し口の列（`.tools`）に並ぶので、行そのものから欄を探す
    const w = b.closest(".inw") || b.closest(".rec-row") || b.closest(".wait");
    const box = w.querySelector(".inote"), r = w.querySelector(".inr");
    if (r) r.hidden = true; else b.hidden = true;
    box.hidden = false;
    box.querySelector("textarea").focus();
  } else if (b.dataset.vnoteOpen) {
    // **「この回のメモ」も、感想と同じ「押してから開く」形にそろえる**（`data-note-open`
    // と同じ判断）
    const w = b.closest(".vnw") || b.closest(".rec-row");
    const box = w.querySelector(".vnote"), r = w.querySelector(".vnr");
    if (r) r.hidden = true; else b.hidden = true;
    box.hidden = false;
    box.querySelector("textarea").focus();
  } else if (b.dataset.rateOpen) {
    // **押してから開く。** 感想の欄と同じ形（`data-note-open`）にそろえてある
    const row = b.closest(".rec-row"), g = row.querySelector(".rb");
    if (g) { g.hidden = false; b.hidden = true; }
  } else if (b.dataset.btnsOpen) {
    // **「興味あり」の三択も、押してから開く**（「評価を押し直す」と同じ形）
    const row = b.closest(".ticket"), g = row.querySelector(".btns");
    if (g) { g.hidden = false; b.hidden = true; }
  } else if (b.dataset.mtAdd) {
    // **カードの中で行く日を追加する**（起案者の指示・2026-08-26 ──「『観劇日を
    // 追加する』のボタンを消して、各公演ごとに観劇日を追加できる欄を設けて
    // ください」）。押し口はこのカードの stage_id を使う ── 別の会場に付けたいときは
    // その会場のカードから入れる
    const box = b.closest(".mytix"), dd = box.querySelector(".mt-d").value,
          tt = box.querySelector(".mt-t").value, said = box.querySelector(".said");
    if (!dd) { said.textContent = "行く日を入れてください"; return; }
    post("/api/ticket", {stage_id: b.dataset.mtAdd, date: dd, time: tt}, box, "記録しました")
      .then(r => { if (r) setTimeout(() => location.reload(), 500); });
  } else if (b.dataset.mtDel || b.dataset.mtOk) {
    // **すでに入れてある行く日の「確定する」「取り消す」。** 押し口自身が持つ
    // stage_id を使う ── 券はカードの代表会場とは違う会場に付いていることがある
    const box = b.closest(".mytix");
    const sid = b.dataset.mtDel || b.dataset.mtOk;
    const body = {stage_id: sid, date: b.dataset.date, time: b.dataset.time,
                  action: b.dataset.mtOk ? "confirm" : "del"};
    post("/api/ticket", body, box,
         body.action === "confirm" ? "確定しました" : "取り消しました")
      .then(r => { if (r) setTimeout(() => location.reload(), 500); });
  } else if (b.dataset.more) {
    // あらすじの続きと、出演者の残り。**同じ押し口で開く**
    (b.closest(".syn") || b.closest(".cast")).classList.toggle("open");
  } else if (b.dataset.close) {
    fetch(API_BASE + "/api/close", {method: "POST", keepalive: true});
    b.textContent = "閉じてよい";
  }
});

// **同じ公演かどうかは、機械が決めずに聞く。**
// 題名が近いだけでは同じ公演とは限らない ── 同じ戯曲の別の上演は題名が完全に一致する。
function askMerge(where, workKey, similar) {
  if (!similar || !similar.length) return false;
  const box = document.createElement("div");
  box.className = "mergeq";
  const h = document.createElement("p");
  // **引用符は単引用符で書く。** この JavaScript は Python の三重引用符の中にあるので、
  // 逆斜線で二重引用符を逃がすと Python 側で逆斜線が外れ、JavaScript が壊れる
  h.innerHTML = '<b>題名の近い記録が ' + similar.length
    + ' 件あります。これと同じ公演ですか？</b><br>'
    + '<span class="mq-note">同じ公演なら、回・評価・感想を 1 つの記録にまとめます。'
    + '別の公演なら、そのままにします（同じ戯曲の別の上演は、題名が同じでも別の公演です）。</span>';
  box.append(h);
  similar.forEach(x => {
    const r = document.createElement("div");
    r.className = "mq-row";
    const d = [x.first_date || "日付不明",
               x.times > 1 ? x.times + " 回観た" : "",
               x.verdict ? "評価 " + x.verdict : "評価はまだ",
               x.mails ? "メール " + x.mails + " 通" : "手で足した記録"]
              .filter(Boolean).join("・");
    r.innerHTML = '<span class="mq-t"></span><span class="mq-m"></span>';
    r.querySelector(".mq-t").textContent = x.title;
    r.querySelector(".mq-m").textContent = d;
    const yes = document.createElement("button");
    yes.textContent = "同じ公演です（まとめる）";
    yes.dataset.merge = x.work_key;
    yes.dataset.mergeWork = workKey;
    r.append(yes);
    box.append(r);
  });
  const foot = document.createElement("div");
  foot.className = "mq-foot";
  const no = document.createElement("button");
  no.textContent = "どれとも別の公演です";
  no.dataset.mergeNo = "1";
  foot.append(no);
  const said = document.createElement("span");
  said.className = "said";
  foot.append(said);
  box.append(foot);
  where.querySelectorAll(".mergeq").forEach(x => x.remove());
  where.append(box);
  box.scrollIntoView({block: "nearest", behavior: "smooth"});
  return true;
}

// **結び付ける公演を探す欄。** 手で足す欄と同じ候補を使う（探し方を 2 通り作らない）。
//
// **引き出しは 2 つある。** 打っている最中は手元だけを引き、「外の公演情報から探す」を
// 押したときだけ外へ行く（守り 5 ── 一覧を眺める操作で外へ要求は出さない）。
// **並べ方は 1 つにまとめてある** ── 同じ題名で手元と外の結果が違う形で出ると、
// どちらが正しいのか確かめようがない。
function lkSay(box, msg) {
  const p = document.createElement("p");
  p.className = "sug-head";
  p.textContent = msg;
  box.append(p);
}

async function lkSearch(i, web, btn) {
  const box = i.parentElement.querySelector(".lk-sug");
  const q = i.value.trim();
  // **後から来た返事で、先の結果を消させない。** 手元の検索（打っている最中・0.2 秒）と
  // 外の検索（押したとき・最大 8 秒）は同じ欄に書くので、**打ってすぐ押すと、遅れて
  // 届いた手元の返事が外の結果を消していた**（実測 ── 見つかった 2 件が
  // 「手元のデータに見つかりませんでした」で上書きされた）。番号を振って、
  // **いちばん新しい検索の返事だけを書く。**
  clearTimeout(i._t);
  const my = i._seq = (i._seq || 0) + 1;
  const fresh = () => i._seq === my;
  if (q.length < 2) {
    box.replaceChildren();
    if (web) lkSay(box, "題名を 2 文字以上入れてから押してください");
    return;
  }
  if (web) {
    box.replaceChildren();
    lkSay(box, "CoRichの公演情報を探しています… 8 秒ほどかかります");
    if (btn) btn.disabled = true;
  }
  let d;
  try {
    const r = await fetch(API_BASE + (web ? "/api/suggest_web?t=" : "/api/suggest?t=")
      + encodeURIComponent(T) + "&q=" + encodeURIComponent(q),
      {headers: {"X-Taguri-Token": T}});
    d = await r.json();
  } catch (e) { d = null; }
  if (btn) btn.disabled = false;
  if (!fresh()) return;
  box.replaceChildren();
  if (!d) { lkSay(box, "探せませんでした"); return; }
  if (d.error) { lkSay(box, d.error); return; }
  const rows = (d.rows || []).filter(x => x.kind === "stage");
  if (!rows.length) {
    // **見つからなかったときに、次に押す口を書く。** 手元に無いことと、公演そのものが
    // 無いことは別である ── 前は「古い公演は入っていません」で終わっていたので、
    // **読んだ人にできることが残っていなかった**
    lkSay(box, web
      ? "「" + q + "」に当たる公演は見つかりませんでした ── 副題や団体名を外して"
        + "短くすると当たることがあります"
      : "手元のデータに見つかりませんでした ── 「CoRichの公演情報から探す」を押してください"
        + "（月 1 回の取り寄せに入っていない公演や、古い公演は手元にありません）");
    return;
  }
  if (web) lkSay(box, "CoRichの公演情報から " + rows.length
    + " 件見つかりました ── 観たものを選んでください。見つからない場合は下の"
    + "「ポスター・クレジットを手入力する」から追加してください。");
  lkRender(box, rows);
}

document.addEventListener("input", ev => {
  const i = ev.target.closest("[data-lk-q]");
  if (!i || !live) return;
  clearTimeout(i._t);
  i._t = setTimeout(() => lkSearch(i, false, null), 220);
});

// **「たどる」の、名前で絞り込む欄。** サーバーには何も送らない ── 85 枚の札は
// すでに手元にあるので、打った文字でその場で出し分けるだけでよい（起案者の指摘・
// 2026-08-26 ──「85名の名前を羅列するってセンスない」への答え）
document.addEventListener("input", ev => {
  const i = ev.target.closest("[data-pk-filter]");
  if (!i) return;
  const q = i.value.trim();
  let shown = 0;
  document.querySelectorAll(".picks .pk").forEach(a => {
    const hit = !q || a.querySelector(".pk-n").textContent.includes(q);
    a.closest("li").hidden = !hit;
    if (hit) shown++;
  });
  const none = document.querySelector(".pk-none");
  if (none) none.hidden = shown > 0;
});

function lkRender(box, rows) {
    // **作品を親、会場ごとの上演を子として並べる**（起案者のイメージ・2026-08-24 ──
    // 「作品ページは親として必ず一個でその下に各地方ごとの子ノード、さらにその下に
    // 観にいった情報の子ノード」）。**取得元は作品の id を持っていない**（会場ごとの
    // 上演に 1 ページ）ので、親はこちらで組んでいる（`work_group`）。
    //
    // **子は畳まない。** 会場ごとに出演者も座組も違いうるので、**どの上演かは本人しか
    // 知らない** ── 親を 1 行にして、その下で会場と日程を選んでもらう。
    const stageRow = (x) => {
      const r = document.createElement("div");
      r.className = "sug-row stage";
      // **手で足す欄と同じ形にする。** ここは「どの公演か」を選ぶ欄なので、
      // **選ぶ手がかりは同じでなければならない** ── 絵が片方にしか無いと、
      // 同じ題名が並んだときに片方でだけ選び分けられることになる
      r.innerHTML = '<span class="sg-p"></span><span class="sg-b">'
        + '<span class="sg-t"></span><span class="sg-m"></span></span>';
      const ph = r.querySelector(".sg-p");
      if (x.poster) {
        const im = document.createElement("img");
        im.src = "/img/" + encodeURIComponent(x.poster) + "?t=" + encodeURIComponent(T);
        im.alt = "";
        im.loading = "lazy";
        ph.append(im);
      } else {
        ph.classList.add("none");
      }
      r.querySelector(".sg-t").textContent = x.title;
      // **観に行った回の数を添える**（木の 3 段目）。すでに記録がある上演は、
      // 「自分が行ったのはこれだ」と分かるいちばん強い手がかりである
      r.querySelector(".sg-m").textContent =
        [x.date, x.venue, x.note].filter(Boolean).join("・")
        + (x.mine ? "／この公演の記録が " + x.mine + " 回あります" : "");
      if (x.mine) r.classList.add("mine");
      const pick = document.createElement("button");
      pick.textContent = "この公演にする";
      pick.dataset.link = x.stage_id;
      r.append(pick);
      return r;
    };
    const order = [], at = {};
    rows.forEach(x => {
      const k = x.wk || x.title;
      if (!(k in at)) { at[k] = []; order.push(k); }
      at[k].push(x);
    });
    order.forEach(k => {
      const xs = at[k];
      if (xs.length === 1) { box.append(stageRow(xs[0])); return; }
      const d = document.createElement("details");
      d.className = "sug-work";
      const sm = document.createElement("summary");
      const mine = xs.reduce((a, x) => a + (x.mine || 0), 0);
      sm.textContent = xs[0].title + "（" + xs.length + " 会場の上演）"
        + (mine ? "── うち " + mine + " 回の記録があります" : "");
      d.append(sm);
      const p = document.createElement("p");
      p.className = "sug-head";
      p.textContent = "観に行った会場と日程を選んでください ──"
        + " 会場ごとに出演者や座組が違うことがあるので、"
        + "別の上演を選ぶと、観ていない公演の作り手が名簿に入ります。";
      d.append(p);
      xs.forEach(x => d.append(stageRow(x)));
      if (mine) d.open = true;
      box.append(d);
    });
}

// **手で足す欄の候補。** すでにある情報を、打っている最中に出す
let sugTimer = null;
function sugWatch() {
  const t = document.getElementById("w-title"), box = document.getElementById("sug");
  if (!t || !box) return;
  t.addEventListener("input", () => {
    document.getElementById("w-stage").value = "";   // 打ち直したら結び付きを外す
    clearTimeout(sugTimer);
    sugTimer = setTimeout(() => sugFetch(t.value, box), 220);
  });
}

async function sugFetch(q, box) {
  if (q.trim().length < 2) { box.replaceChildren(); return; }
  let d;
  try {
    const r = await fetch(API_BASE + "/api/suggest?t=" + encodeURIComponent(T)
      + "&q=" + encodeURIComponent(q), {headers: {"X-Taguri-Token": T}});
    d = await r.json();
  } catch (e) { return; }
  sugRender(box, d.rows, "すでにある情報から選べます（"
    + ((d.rows || []).length) + " 件）");
}

// **手元に無い公演を、押したときだけ外の公演情報から探す。**（起案者の指示・2026-08-24）
//
// **打っている最中には行かない。** 1 つの相手には 1.1 秒に 1 回までを守るので、1 回の
// 検索に 8 秒ほどかかる。文字を打つたびに走らせると打ち直すたびにやり直しになり、
// **待っているのか壊れているのか本人には分からない。** 押した人が待っていると分かる形に
// する（探しているあいだ文を出し、ボタンを押せなくする）。
async function sugWeb() {
  const t = document.getElementById("w-title"), box = document.getElementById("sug");
  const btn = document.querySelector("[data-sug-web]");
  if (!t || !box) return;
  const q = t.value.trim();
  if (q.length < 2) { sugSay(box, "題名を 2 文字以上入れてから押してください", true); return; }
  sugSay(box, "CoRichの公演情報を探しています… 8 秒ほどかかります", true);
  if (btn) btn.disabled = true;
  let d = null;
  try {
    const r = await fetch(API_BASE + "/api/suggest_web?t=" + encodeURIComponent(T)
      + "&q=" + encodeURIComponent(q), {headers: {"X-Taguri-Token": T}});
    d = await r.json();
  } catch (e) { d = null; }
  if (btn) btn.disabled = false;
  if (!d) {
    sugSay(box, "探せませんでした。お手数ですが、手で入れてください", true);
    return;
  }
  if (d.error) { sugSay(box, d.error, true); return; }
  if (!d.rows || !d.rows.length) {
    // **見つからなかったことを、次に何をすればよいかと一緒に出す。**
    // 「0 件」だけでは、打ち間違いなのか無い公演なのか分からない
    sugSay(box, "「" + q + "」に当たる公演は見つかりませんでした ── 副題や団体名を外して"
      + "短くすると当たることがあります。見つからないときは、そのまま手で入れてください", true);
    return;
  }
  sugRender(box, d.rows,
    "CoRichの公演情報から " + d.rows.length + " 件見つかりました ── 観たものを選んでください");
}

function sugSay(box, msg, clear) {
  if (clear) box.replaceChildren();
  const p = document.createElement("p");
  p.className = "sug-head";
  p.textContent = msg;
  box.append(p);
}

// **手元の候補と外の候補を、同じ見た目で並べる。** 選んだあとの動きが同じなので、
// 描き方を 2 通り作ると片方だけ直す事故が起きる
function sugRender(box, rows, headText) {
  box.replaceChildren();
  if (!rows || !rows.length) return;
  sugSay(box, headText, false);
  rows.forEach(x => {
    const r = document.createElement("div");
    r.className = "sug-row " + x.kind;
    r.dataset.title = x.title;
    r.dataset.date = x.date || "";
    r.dataset.venue = x.venue || "";
    r.dataset.stage = x.kind === "stage" ? (x.stage_id || "") : "";
    r.innerHTML = '<span class="sg-p"></span><span class="sg-b">'
      + '<span class="sg-k"></span><span class="sg-t"></span>'
      + '<span class="sg-m"></span></span>';
    // **ポスターは端末内の道からしか出さない。** 手元に無い公演（外から探した分）は
    // 枠だけを置く ── 行の高さが揃わないと、並んだ候補を上から読めない
    const ph = r.querySelector(".sg-p");
    if (x.poster) {
      const im = document.createElement("img");
      im.src = "/img/" + encodeURIComponent(x.poster) + "?t=" + encodeURIComponent(T);
      im.alt = "";
      im.loading = "lazy";
      ph.append(im);
    } else {
      ph.classList.add("none");
    }
    r.querySelector(".sg-k").textContent = x.kind === "record" ? "記録あり" : "公演";
    r.querySelector(".sg-t").textContent = x.title;
    r.querySelector(".sg-m").textContent =
      [x.date, x.venue, x.note].filter(Boolean).join("・");
    if (x.cast) {
      const c = document.createElement("span");
      c.className = "sg-c";
      c.textContent = "出演 " + x.cast;
      r.append(c);
    }
    if (x.kind === "record") {
      const w = document.createElement("span");
      w.className = "sg-dup";
      w.textContent = "すでに記録にあります";
      r.append(w);
    } else {
      const pick = document.createElement("button");
      pick.textContent = "これを使う";
      pick.dataset.pick = "1";
      r.append(pick);
    }
    box.append(r);
  });
}

// 直すための手がかり。**抽出が切った題名の続きは、ほぼ本文に書いてある**
async function hints(box) {
  if (box.dataset.done) return;
  box.dataset.done = "1";
  box.textContent = "メールを読んでいます…";
  try {
    const r = await fetch(API_BASE + "/api/mail_hints?t=" + encodeURIComponent(T)
      + "&uid=" + encodeURIComponent(box.dataset.hints), {headers: {"X-Taguri-Token": T}});
    const d = await r.json();
    box.textContent = "";
    (d.hints || []).forEach(h => {
      const p = document.createElement("div");
      p.textContent = "・" + h;
      box.append(p);
    });
    if (!(d.hints || []).length) box.textContent = "本文に手がかりは見つかりませんでした。";
  } catch (e) {
    box.dataset.done = "";
    box.textContent = "メール本文を読めませんでした（" + e + "）。";
  }
}

// **押した直後に走る取得を、終わるまで見に行く。**
// 起案者の指示（2026-08-24）で、公演を足した・結び付けた・お気に入りに登録した直後に
// 材料を取りに行くようにした。**取ってきたものは、画面を作り直さないと出ない** ──
// 押した本人からは「何も起きなかった」ように見えるので、終わってから読み込み直す。
function waitJob(g, reload) {
  const said = g && g.querySelector(".said");
  const tick = async () => {
    try {
      const r = await fetch(API_BASE + "/api/import_status?t=" + encodeURIComponent(T),
                            {headers: {"X-Taguri-Token": T}});
      const d = await r.json();
      if (said && d.line) said.textContent = d.line;
      if (d.running) { setTimeout(tick, 1200); return; }
      if (reload) {
        // **開いていた道具は、読み込み直しても開いたままにする。** 名前を 1 つ登録する
        // たびに枠が畳まると、2 つめを足すのに毎回開き直すことになる
        const op = document.querySelector("details.pbox[open]");
        if (op && op.id) location.hash = op.id;
        setTimeout(() => location.reload(), 700);
      }
    } catch (e) { if (reload) location.reload(); }
  };
  setTimeout(tick, 400);
}

// 断片で指された道具を開く。**`<details>` は自分では開かない**ので、こちらで開ける
if (location.hash.length > 1) {
  const t = document.getElementById(location.hash.slice(1));
  if (t && t.tagName === "DETAILS") t.open = true;
}

// **押した後に何も動かないのは、効かなかったのと見分けが付かない。**
// 取り込みは数分から数十分かかる（起案者の指示・2026-08-25「経過がわかるバーがほしい」）。
// 出すのは 3 つ ── いま何をしているか、何通のうち何通目か、あとどれくらいか。
//
// **残り時間は、実際に進んだ速さから出す。** 決め打ちの秒数は初回（数千通）と
// 差分（数通）で桁が違うので、当たらない数字を出すことになる。
// **進み始めてすぐは出さない**（数パーセントぶんの速さで割ると何時間にも見える）。
let IMP_T0 = 0;

function impMin(sec) {
  if (sec < 60) return "残り 1 分もかかりません";
  const m = Math.round(sec / 60);
  return m < 60 ? "残り およそ " + m + " 分" : "残り およそ " + Math.round(m / 6) / 10 + " 時間";
}

function prog(d) {
  const bar = document.querySelector("[data-ibar]");
  if (!bar) return;
  bar.hidden = false;
  const done = !d.running, total = +d.total || 0, n = +d.n || 0;
  // **どこまで伸ばすかは、取り込みを見ている側が 3 つの段を通して出している**
  // （`serve._pct`）── 段ごとに数え直すと、段が変わるたびに帯が戻る
  const pct = done ? 100 : Math.max(0, Math.min(99, +d.pct || 0));
  const seek = !done && !total;         // 何通あるかが分かる前
  bar.classList.toggle("iwait", seek);
  bar.classList.toggle("done", done);
  // **探している間は幅を書かない。** 直に書いた指定は規則より強いので、置いたままだと
  // 流れる帯が幅 0 のまま動かない ── 分かった時点で消して、規則に返す
  const fill = bar.querySelector(".ifill");
  if (seek) fill.style.removeProperty("width");
  else fill.style.width = pct + "%";
  bar.setAttribute("aria-valuenow", pct);
  bar.querySelector(".istep").textContent =
    done ? "取り込みが終わりました" : (d.name || "取り込んでいます");
  bar.querySelector(".inum").textContent =
    done ? "" : (total ? n + " / " + total + " 通" : "");
  // **残りは帯の伸びから出す。** 通数から出すと段が変わるたびに分母が変わり、
  // **段の変わり目で残り時間が跳ねる**（段 3 の 1 通目で「残り 40 分」になる）
  const rest = bar.querySelector(".irest");
  if (done || pct < 5 || !IMP_T0) rest.textContent = "";
  else rest.textContent = impMin((Date.now() - IMP_T0) / 1000 / pct * (100 - pct));
  // **終わった段は緑で埋める。** どこまで通ったのかが、止まったときにも残る
  const s = done ? 4 : (+d.step || 1);
  bar.querySelectorAll(".isteps li").forEach((li, i) => {
    li.classList.toggle("on", !done && i + 1 === s);
    li.classList.toggle("fin", i + 1 < s);
  });
}

function poll(g, b) {
  const said = g.querySelector(".said");
  IMP_T0 = IMP_T0 || Date.now();
  const tick = async () => {
    try {
      const r = await fetch(API_BASE + "/api/import_status?t=" + encodeURIComponent(T),
                            {headers: {"X-Taguri-Token": T}});
      const d = await r.json();
      prog(d);
      said.textContent = d.line || "…";
      if (d.running) { setTimeout(tick, 1000); return; }
      b.disabled = false;
      IMP_T0 = 0;
      said.textContent = d.line || "終わりました";
    } catch (e) {
      // **聞きに行けなくても、走っているものは走っている。** 諦めずにもう一度聞く
      setTimeout(tick, 3000);
    }
  };
  tick();
}

// 走っている最中に開き直したときは、そのまま続きから見せる（`app._import_bar`）
{
  const bar = live && document.querySelector("[data-ibar][data-run]");
  if (bar) {
    const g = document.querySelector(".imp");
    if (g) poll(g, g.querySelector("button"));
  }
}

// **入力欄の動きは、後から足した 1 枚にも付ける。**
//
// ボタンは `document` で受けているので足した 1 枚でも効くが、**入力欄は読み込みのときに
// 1 度だけ結んでいた** ── 入れ替わりに差し込んだカードの欄は、書けるのに保存されない
// 欄になる。**2 度結ばないように印を付ける**（同じ blur で 2 回送ることになる）。
function bindNotes(root) {
// 「興味あり」に添えた理由。**離れたときに保存する**（書いている途中で送らない）
root.querySelectorAll(".why-note textarea").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    const g = t.closest(".why-note");
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    post("/api/react", {stage_id: g.dataset.stage, note: t.value}, g,
         "理由を保存した（お気に入りの昇格候補に出る）");
  });
});

// 「興味なし」に添えた見送った理由。**離れたときに保存する**
root.querySelectorAll("textarea[data-nono]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    const g = t.closest(".nn");
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    post("/api/react", {stage_id: g.dataset.stage, note_no: t.value}, g,
         "理由を保存した").then(d => {
      if (!d || !t.value.trim()) return;
      // **畳んだ見出しに書いた文を出す。** 閉じても読めることが、この欄の返りである
      const s = g.querySelector("summary");
      s.textContent = "見送った理由";
      const v = document.createElement("span");
      v.className = "nnv";
      v.textContent = t.value;
      s.append(v);
    });
  });
});

root.querySelectorAll("textarea[data-note]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    // **保存できたことを、書いた欄のそばに出す。** `.rec-row` しか見ていなかったため、
    // 評価待ちの行と溜まった分の束に置いた欄では**保存の合図がどこにも出なかった**
    // （消えたのか保存されたのか分からない入力になる）
    post("/api/note", {work_key: t.dataset.note, note_impression: t.value},
         t.closest(".inote, .wnote, .wait, .rec-row"), "感想を保存した");
  });
});

// **「この回のメモ」も、離れたときに保存する**（感想と同じ形）。推薦には使わない
// 欄なので、送り先も別の口（`/api/visit_note`）にする
root.querySelectorAll("textarea[data-vnote]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    if (!live || t.value === t.dataset.was) return;
    t.dataset.was = t.value;
    post("/api/visit_note", {uid: t.dataset.vnote, note: t.value},
         t.closest(".vnote, .rec-row"), "メモを保存した");
  });
});
}

bindNotes(document);

// **選んだ画像を、その場で端末内に写す。**（起案者の指示・2026-08-24）
// **外へは 1 バイトも出さない** ── 読むのはブラウザが開いたファイルで、送り先は
// 同じ端末で動いているこちらのプロセスだけである（企画書 5 章の守り 5 はそのまま）。
// **押した結果をその場に出す** ── 絵が入れ替わらないと、写せたのかが分からない。
document.addEventListener("change", ev => {
  const i = ev.target.closest("[data-hand-img]");
  if (!i || !live || !i.files || !i.files[0]) return;
  const g = i.closest(".hand"), said = g.querySelector(".hand-p .said");
  const f = i.files[0];
  if (said) said.textContent = "写しています…";
  const rd = new FileReader();
  rd.onerror = () => { if (said) said.textContent = "画像を読めませんでした"; };
  rd.onload = () => {
    post("/api/hand_poster", {work_key: g.dataset.work, image: rd.result}, null, null)
      .then(d => {
        if (!d) { if (said) said.textContent = "入れられませんでした"; return; }
        if (said) said.textContent = d.said || "入れ替えました";
        // **この欄の絵と、記録の側の絵の両方を差し替える**（同じ 1 枚を 2 か所に出している）
        // **名前は中身から作られているので、入れ替えれば URL が変わる**
        // （同じ URL のままだとブラウザが古い絵を出し続ける）
        const url = "/img/" + encodeURIComponent(d.poster) + "?t=" + encodeURIComponent(T);
        g.querySelectorAll(".ed-pv").forEach(pv => {
          pv.replaceChildren();
          const im = document.createElement("img");
          im.src = url;
          im.alt = "";
          pv.append(im);
        });
        setTimeout(() => location.reload(), 1200);
      });
  };
  rd.readAsDataURL(f);
  i.value = "";
});

// **効かせ方の欄は、開いたときは畳んでおく**（起案者の指示・2026-08-24 ──
// 「表示したとき常に開いているので、初期は閉じているようにしてください」）。
// **開くのは、確定か「ふつうに戻す」を押した直後だけである** ── その知らせ
// （推薦から外れた件数）はこの欄の中にしか無いので、畳んで戻すと結果が見えない。
{
  const wb = document.getElementById("weights");
  if (wb && location.hash === "#weights") wb.open = true;
}

// **画面を閉じたら自動で終了する仕組みは撤回した**（起案者の指示・2026-08-27）。
// 「記録を見返す」のような画面を長時間開いたままにする使い方と噛み合わなかった
// （タブを裏に回すとブラウザが定期送信を間引き、まだ見ているのに落ちることがあった）。
// 閉じるのはフッターの「終わる」ボタン（`/api/close`）と `Ctrl-C` に一本化した。
if (live) sugWatch();

// === ported: tools/taguri/people.py の PE.JS(相関図パネル) ===

(() => {
  const box = document.querySelector("[data-pnet]");
  if (!box) return;
  const src = box.querySelector("[data-pnet-data]");
  let D;
  try { D = JSON.parse(src.textContent); } catch (e) { return; }
  const svg = box.querySelector("svg"), tip = box.querySelector("[data-ptip]");
  const said = document.querySelector("[data-psaid]");
  const N = D.nodes, EG = D.edges, W = D.w, H = D.h, PAD = D.pad;
  const nd = [...svg.querySelectorAll(".nd")];
  const ln = [...svg.querySelectorAll(".ed line")];
  const tx = [...svg.querySelectorAll(".nl")];
  const gN = new Map(nd.map(g => [+g.dataset.i, g]));
  const gT = new Map(tx.map(t => [+t.dataset.i, t]));
  const hullG = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.insertBefore(hullG, svg.firstChild);

  // 隣り合う人。**外した人を通る道は数えない**（束が割れるかの判定に使う）
  const adj = N.map(() => []);
  EG.forEach(([a, b]) => { adj[a].push(b); adj[b].push(a); });

  const P = N.map(n => ({x: n.x, y: n.y, vx: 0, vy: 0, r: n.r, fix: false}));
  let out = -1;              // 外している人（-1 は誰も外していない）
  let lit = -1;              // 浮かせている人
  let drag = -1;
  // **まだ観ていない人。** 時間のつまみで隠れている点は、外した人と同じ扱いで
  // 力学からも外す ── そうしないと、まだ結ばれていない線がばねとして働いてしまう
  let futureNodes = new Set();
  let timePast = false;     // 「いま」以外を見ている（外してみる・つまむ操作を止める）
  const live = i => i !== out && !futureNodes.has(i);

  // ---- 力学。**乱数は使わない** ------------------------------------------
  const K_REP = 1350, K_SPR = 0.055, K_MID = 0.020, DAMP = 0.82;
  let alpha = 0.55, raf = 0;
  const slow = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // **枠に合わせて伸ばす倍率。** 定数を手で当てて広げるのではなく、落ち着いた形を
  // そのまま拡大し、**ばねの自然長も同じ倍率で伸ばす** ── 位置だけ拡大すると
  // ばねが伸びた状態になり、次の瞬間また縮んで元の大きさに戻る
  let mul = 1, fits = 0, packed = false;
  // **割れる様子を見せる時間に上限を置く。** 上限が無いと、力学が落ち着き切るまで
  // 実測で 11 秒かかった ── 押してから答えが出るまで 11 秒待つ操作は、確かめる道具に
  // ならない。1.5 秒だけ動かして、そのあと並べ直して止める
  let hold = 0;
  // 名前を置く優先順を、割れたあとだけ入れ替えるための束の番号（小さい束を先に）
  let rank = N.map(() => 0);
  const MUL_MAX = 2.5;
  // **見えている枠。** 束を横に並べて枠から溢れたとき、点の位置だけを縮めると
  // **半径は縮まないので点が重なる**（半径は作品数なので縮められない）。そこで
  // **枠のほうを広げる** ── SVG は幅 100% で描くので、枠を広げれば点・隙間・文字が
  // すべて同じ割合で小さくなり、重なりが原理的に生まれない。
  let VW = W, VH = H;
  function frame(w, h) {
    VW = Math.max(W, w); VH = Math.max(H, h);
    svg.setAttribute("viewBox", "0 0 " + VW.toFixed(0) + " " + VH.toFixed(0));
  }
  // **束ごとの引き寄せ先。** 人を外して網が割れても、離れた島は辺を持たないので
  // **斥力と中心への引力が釣り合ったところで元の塊に混ざったまま止まる** ── 実測では
  // 2 つの束の囲いがほぼ完全に重なり、「割れた」ことが絵から読めなかった。
  // **束ごとに別の引き寄せ先を与えて、割れた形を場所として見せる。**
  let home = N.map(() => [W / 2, H / 2]);

  function step() {
    for (let i = 0; i < P.length; i++) {
      if (!live(i)) continue;
      const a = P[i];
      for (let j = i + 1; j < P.length; j++) {
        if (!live(j)) continue;
        const b = P[j];
        let dx = a.x - b.x, dy = a.y - b.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 0.01) { dx = (i - j) * 0.01; dy = 0.01; d2 = 0.0002; }
        const d = Math.sqrt(d2), f = K_REP / d2;
        const ux = dx / d, uy = dy / d;
        a.vx += ux * f; a.vy += uy * f;
        b.vx -= ux * f; b.vy -= uy * f;
        // 重なりの解消。**点が重なると大きさ（＝作品数）が読めない**
        const need = a.r + b.r + 3;
        if (d < need) {
          const push = (need - d) * 0.5;
          a.vx += ux * push; a.vy += uy * push;
          b.vx -= ux * push; b.vy -= uy * push;
        }
      }
      a.vx += (home[i][0] - a.x) * K_MID; a.vy += (home[i][1] - a.y) * K_MID;
    }
    for (const [i, j, w] of EG) {
      if (!live(i) || !live(j)) continue;
      const a = P[i], b = P[j];
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.hypot(dx, dy) || 0.01;
      // 一緒に居た作品数が多いほど短く結ぶ（近さがそのまま濃さになる）
      const rest = mul * 128 / (1 + 0.42 * (w - 1));
      const f = (d - rest) * K_SPR;
      const ux = dx / d * f, uy = dy / d * f;
      a.vx += ux; a.vy += uy;
      b.vx -= ux; b.vy -= uy;
    }
    for (let i = 0; i < P.length; i++) {
      const p = P[i];
      if (!live(i)) continue;
      if (p.fix) { p.vx = p.vy = 0; continue; }
      p.vx *= DAMP; p.vy *= DAMP;
      p.x += p.vx * alpha; p.y += p.vy * alpha;
      p.x = Math.min(Math.max(p.x, PAD + p.r), W - PAD - p.r);
      p.y = Math.min(Math.max(p.y, PAD + p.r), H - PAD - p.r);
    }
    alpha *= 0.975;
  }

  // ---- 名前を置く。**重ならない場所にだけ置く** --------------------------
  const tw = new Map();
  function width(i) {
    if (!tw.has(i)) { try { tw.set(i, gT.get(i).getComputedTextLength()); }
                      catch (e) { tw.set(i, N[i].n.length * 11); } }
    return tw.get(i);
  }
  const SPOTS = [[1, 0, "start"], [-1, 0, "end"], [0, -1, "middle"], [0, 1, "middle"],
                 [1, -1, "start"], [-1, -1, "end"], [1, 1, "start"], [-1, 1, "end"]];
  function labels() {
    // **割れたあとは、離れた側の名前を先に置く。** 平常時の優先順（束をつないでいる方 →
    // 作品数の多い方）のままだと、**離れた 4 名に 1 つも名前が付かない** ── 誰が離れたのかを
    // 図から読めないので、答えを文でしか確かめられなくなる
    const order = [...gT.keys()].filter(live).sort((a, b) =>
      (rank[a] - rank[b]) || (N[b].c - N[a].c) || (N[b].w - N[a].w) || (a - b));
    const kept = [];
    for (const i of order) {
      // 文字の幅は 1 度測って覚える。**+2px の余裕を持たせる** ── 端末ごとの丸めで
      // 1px 足りず、名前が 1 組だけ重なることがあった（実測・明るい側だけで再現）
      const t = gT.get(i), p = P[i], w = width(i) + 2, h = 15;
      let ok = null;
      for (const [sx, sy, anc] of SPOTS) {
        const ax = p.x + sx * (p.r + 5), ay = p.y + sy * (p.r + 11);
        const x0 = anc === "start" ? ax : anc === "end" ? ax - w : ax - w / 2;
        const bx = [x0, ay - h / 2, x0 + w, ay + h / 2];
        if (bx[0] < 1 || bx[2] > VW - 1 || bx[1] < 1 || bx[3] > VH - 1) continue;
        if (kept.some(k => k[0] < bx[2] && bx[0] < k[2] && k[1] < bx[3] && bx[1] < k[3]))
          continue;
        ok = [ax, ay, anc, bx]; break;
      }
      if (!ok) { t.setAttribute("visibility", "hidden"); continue; }
      t.setAttribute("visibility", "visible");
      t.setAttribute("x", ok[0].toFixed(1));
      t.setAttribute("y", ok[1].toFixed(1));
      t.setAttribute("text-anchor", ok[2]);
      kept.push(ok[3]);
    }
  }

  function paint() {
    for (const [i, g] of gN) {
      const c = g.firstElementChild.nextElementSibling || g.querySelector("circle");
      c.setAttribute("cx", P[i].x.toFixed(1));
      c.setAttribute("cy", P[i].y.toFixed(1));
    }
    for (const l of ln) {
      const a = P[+l.dataset.a], b = P[+l.dataset.b];
      l.setAttribute("x1", a.x.toFixed(1)); l.setAttribute("y1", a.y.toFixed(1));
      l.setAttribute("x2", b.x.toFixed(1)); l.setAttribute("y2", b.y.toFixed(1));
    }
    labels();
    hulls();
  }

  // **枠を使い切る。** 力学の釣り合いが決める大きさは、枠の大きさとは無関係である ──
  // 実測では 900x620 の枠に対して 356x380 しか使っておらず、点も名前も無駄に小さかった。
  // **一様に拡大するので形は変わらない**（縦横の比も崩さない）。
  // **縮めたあとは、点の重なりだけを解く。** 位置を一様に縮めても半径は縮まない
  // （半径は作品数なので縮められない）ので、**縮めた分だけ点が重なる**（実測で 2 組）。
  // ばねも引き寄せも動かさず、重なりだけを押し離すので**束の並びは崩れない。**
  // **押し離すのは同じ束の中だけにする。** 束をまたいで押すと、隣の束の場所へ点が
  // はみ出し、**離したはずの囲いがまた重なる**（実測）。束の間はすでに隙間で離してある
  function declump(rounds, sameBundleOnly) {
    const ids = [...Array(N.length).keys()].filter(live);
    for (let k = 0; k < rounds; k++) {
      let moved = 0;
      for (let a = 0; a < ids.length; a++) for (let b = a + 1; b < ids.length; b++) {
        if (sameBundleOnly && rank[ids[a]] !== rank[ids[b]]) continue;
        const p = P[ids[a]], q = P[ids[b]];
        let dx = q.x - p.x, dy = q.y - p.y;
        let d = Math.hypot(dx, dy);
        if (d < 0.01) { dx = 0.01; dy = 0.01; d = 0.014; }
        const need = p.r + q.r + 3;
        if (d >= need) continue;
        const push = (need - d) / 2, ux = dx / d, uy = dy / d;
        p.x -= ux * push; p.y -= uy * push;
        q.x += ux * push; q.y += uy * push;
        moved += push;
      }
      for (const i of ids) {
        P[i].x = Math.min(Math.max(P[i].x, P[i].r + 2), VW - P[i].r - 2);
        P[i].y = Math.min(Math.max(P[i].y, P[i].r + 2), VH - P[i].r - 2);
      }
      if (moved < 0.4) break;
    }
  }

  function fit(springs = true, force = false) {
    const ids = [...Array(N.length).keys()].filter(live);
    if (ids.length < 2) return false;
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, rmax = 0;
    for (const i of ids) {
      x0 = Math.min(x0, P[i].x); y0 = Math.min(y0, P[i].y);
      x1 = Math.max(x1, P[i].x); y1 = Math.max(y1, P[i].y);
      rmax = Math.max(rmax, P[i].r);
    }
    const room = m => Math.max(m, 1);
    const s = Math.min((W - 2 * (PAD + rmax)) / room(x1 - x0),
                       (H - 2 * (PAD + rmax)) / room(y1 - y0));
    // **縮めるほうにも効かせる。** 伸ばすだけにしていたため、束を横に並べて枠から
    // はみ出したときに戻せず、**小さいほうの束が枠の外で切れていた**（実測）
    if (!isFinite(s) || (!force && s > 0.98 && s < 1.02)) return false;
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    for (const i of ids) {
      P[i].x = W / 2 + (P[i].x - cx) * s;
      P[i].y = H / 2 + (P[i].y - cy) * s;
      P[i].vx = P[i].vy = 0;
      // **引き寄せ先も一緒に動かす。** 点だけ動かすと、引力が動かす前の場所を指し続ける
      home[i] = [W / 2 + (home[i][0] - cx) * s, H / 2 + (home[i][1] - cy) * s];
    }
    // **ばねの自然長を伸ばしすぎない。** 枠に合わせて何度も伸ばすと自然長が積み上がり、
    // **4 人しかいない島が 436px に広がった**（実測）── 人数の少ない束が、大きな束と
    // 同じ広さを占めて見える。伸ばすのは枠を埋めるまでで足りる
    // **枠に入れるための縮小は、ばねの自然長に持ち込まない。** 持ち込むと次の一手で
    // また縮み、束の中の間隔が回を追うごとに詰まっていく
    if (springs) mul = Math.min(mul * s, MUL_MAX);
    return true;
  }

  // **割れた束を、重ならない場所へ動かす。**
  //
  // 束と束の間には辺が 1 本も無いので、**束をまるごと平行移動しても、束の中の距離は
  // 1 つも変わらない** ── 形を歪めずに離せる。力任せ（斥力と引力の釣り合い）で離そうと
  // すると釣り合った所で混ざったまま止まり、実測では 2 つの囲いがほぼ完全に重なった。
  //
  // **場所は大きい束から順に、左から詰める。** 入りきらなければ次の段へ折り返す。
  function pack2() {
    const cs = comps();
    if (cs.length < 2) return null;
    const bb = cs.map(c => {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const i of c) {
        x0 = Math.min(x0, P[i].x - P[i].r); y0 = Math.min(y0, P[i].y - P[i].r);
        x1 = Math.max(x1, P[i].x + P[i].r); y1 = Math.max(y1, P[i].y + P[i].r);
      }
      return {x0, y0, x1, y1, w: x1 - x0, h: y1 - y0};
    });
    // **横 1 列に並べる。折り返さない。** 折り返すと枠からはみ出した束が切れるうえ、
    // 「いくつに割れたか」が段組みのせいで数えにくくなる。**はみ出す分は下の `fit` が
    // 全体を縮めて収める**（一様な縮小なので、離れている関係は崩れない）
    const GAP = 64;   // 束と束の隙間（囲いの余白より広くとる）
    // **端から余白ぶん離して置く。** 0 から並べると 1 番目の束の囲いが枠の左に食い込み、
    // 縁で切れる（囲いは点の外側に描くので、点が枠の内側にあるだけでは足りない）
    let cx = PAD;
    home = N.map(() => [W / 2, H / 2]);
    // 小さい束を先に（番号が小さいほど先に名前が付く）
    const bySmall = cs.map((c, k) => k).sort((a, b) => cs[a].length - cs[b].length);
    rank = N.map(() => 99);
    bySmall.forEach((k, r) => { for (const i of cs[k]) rank[i] = r; });
    cs.forEach((c, k) => {
      const b = bb[k];
      // 縦は枠の中央にそろえる。**枠より高い束は上に食い込ませず、余白から始める**
      const dx = cx - b.x0, dy = Math.max(PAD, (H - b.h) / 2) - b.y0;
      for (const i of c) { P[i].x += dx; P[i].y += dy; P[i].vx = P[i].vy = 0; }
      const hx = cx + b.w / 2;
      for (const i of c) home[i] = [hx, H / 2];
      cx += b.w + GAP;
    });
    let x1 = 0, y1 = 0;
    for (let i = 0; i < N.length; i++) if (live(i)) {
      x1 = Math.max(x1, P[i].x + P[i].r); y1 = Math.max(y1, P[i].y + P[i].r);
    }
    return [x1, y1];
  }

  function loop() {
    step();
    paint();
    if (hold > 0) hold--;
    if ((alpha > 0.004 && hold > 0) || drag >= 0) { raf = requestAnimationFrame(loop); return; }
    if (alpha > 0.004 && hold === 0 && out >= 0) alpha = 0;   // 上限で切り上げる
    if (alpha > 0.004) { raf = requestAnimationFrame(loop); return; }
    // 3 回で打ち切る ── ばねの自然長も一緒に伸ばしているので、ふつう 1〜2 回で収まる
    if (fits < 3 && fit()) { fits++; alpha = 0.28; raf = requestAnimationFrame(loop); return; }
    // **束を離すのは最後にする。** 離したあとに力学を続けると、束の間の押し合いと
    // 引き寄せが釣り合った所まで戻ってきて、**離した囲いがまた重なる**（実測）。
    // 平行移動は束の中の距離を変えないので、ここで動かして止めてよい。
    // そのあとの一様な拡大は離れている関係を崩さないので、枠合わせだけもう 1 度かける。
    // **順序が要点である。**
    //
    // ① 束を並べて隙間を作る → ② 溢れた分だけ枠を広げる → ③ 点の重なりを束の中で解く。
    //
    // **③ を ② より前に置くと壊れる。** 点を押し離すときは枠の中に押し戻すので、
    // **枠を広げる前に押し戻すと、枠の外に並べた 2 番目の束が 1 番目の上に潰れる**
    // ── 実測で、どの人を外しても囲いが必ず重なった。押し戻す先は「見えている枠」である。
    if (out >= 0 && !packed) {
      const ext = pack2();
      if (ext) {
        packed = true;
        frame(ext[0] + PAD, ext[1] + PAD);
        declump(60, true);
        paint();
      }
    }
    raf = 0;
  }
  function heat(a) {
    alpha = Math.max(alpha, a);
    if (!raf) raf = requestAnimationFrame(loop);
  }

  // ---- 束を数える。**外した人を通る道は数えない** ------------------------
  function comps() {
    const seen = new Set(), cs = [];
    for (let i = 0; i < N.length; i++) {
      if (!live(i) || seen.has(i)) continue;
      const st = [i], c = []; seen.add(i);
      while (st.length) {
        const x = st.pop(); c.push(x);
        for (const q of adj[x]) if (live(q) && !seen.has(q)) { seen.add(q); st.push(q); }
      }
      cs.push(c.sort((a, b) => (N[b].w - N[a].w)));
    }
    return cs.sort((a, b) => b.length - a.length);
  }

  // 割れた束を囲う。**色ではなく囲い**（束の数が数として読めるほうがよい）
  function hulls() {
    hullG.textContent = "";
    if (out < 0) return;
    const cs = comps();
    if (cs.length < 2) return;
    const bs = cs.map(c => {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const i of c) {
        x0 = Math.min(x0, P[i].x - P[i].r); y0 = Math.min(y0, P[i].y - P[i].r);
        x1 = Math.max(x1, P[i].x + P[i].r); y1 = Math.max(y1, P[i].y + P[i].r);
      }
      return [x0, y0, x1, y1];
    });
    // **余白は、束と束の隙間から決める。** 決め打ちの 11px にしていたため、枠に収める
    // 縮小で隙間が 22px を下回ったときに**囲いが重なり、割れて見えなくなった**（実測）。
    // 隙間の半分より狭くしておけば、重なることが原理的に起きない
    let sep = 1e9;
    for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) {
      const a = bs[i], b = bs[j];
      const gx = Math.max(a[0] - b[2], b[0] - a[2]);
      const gy = Math.max(a[1] - b[3], b[1] - a[3]);
      sep = Math.min(sep, Math.max(gx, gy));
    }
    const pad = Math.max(2, Math.min(11, sep / 2 - 1));
    for (const [x0, y0, x1, y1] of bs) {
      const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      r.setAttribute("class", "hull");
      r.setAttribute("x", (x0 - pad).toFixed(1)); r.setAttribute("y", (y0 - pad).toFixed(1));
      r.setAttribute("width", (x1 - x0 + 2 * pad).toFixed(1));
      r.setAttribute("height", (y1 - y0 + 2 * pad).toFixed(1));
      r.setAttribute("rx", Math.min(14, pad + 6).toFixed(1));
      hullG.append(r);
    }
  }

  // ---- 浮かせる。**下げることで浮かせる** --------------------------------
  function light(i) {
    lit = i;
    box.classList.toggle("lit", i >= 0);
    const near = i >= 0 ? new Set(adj[i].filter(live)) : new Set();
    for (const [k, g] of gN) {
      g.classList.toggle("on", k === i);
      g.classList.toggle("near", near.has(k));
    }
    for (const [k, t] of gT) {
      t.classList.toggle("on", k === i);
      t.classList.toggle("near", near.has(k));
    }
    for (const l of ln) {
      const a = +l.dataset.a, b = +l.dataset.b;
      l.classList.toggle("on", i >= 0 && (a === i || b === i));
    }
    if (i >= 0) labels();
  }

  function showTip(i, ev) {
    const n = N[i];
    // **吹き出しは小さく保つ。** 題名を 5 本ぶん全文で出すと図の半分を覆い、
    // **確かめようとしている形そのものが見えなくなる**（実測）。全文は下の表にある
    const cut = t => t.length > 26 ? t.slice(0, 26) + "…" : t;
    const ts = n.t.slice(0, 3).map(t => cut(t[0])).join("／");
    const more = n.t.length > 3 ? `ほか ${n.t.length - 3} 本` : "";
    tip.innerHTML = `<b>${esc(n.n)}</b>（${n.m ? "作り手" : "出演"}）`
      + `<span class="tw">観た作品 ${n.w} 本・一緒に居た方 ${n.d} 名`
      + (n.c ? "・この方を外すと網が割れます" : "") + `</span>`
      + `<span class="tw">${esc(ts)}${esc(more)}</span>`;
    tip.hidden = false;
    // **枠の中に収める。** 下端・右端で出すと吹き出しが切れて読めない
    const b = box.getBoundingClientRect();
    tip.style.left = "0px"; tip.style.top = "0px";
    const tw2 = tip.offsetWidth, th = tip.offsetHeight;
    const x = ev.clientX - b.left + box.scrollLeft + 14;
    const y = ev.clientY - b.top + 12;
    tip.style.left = Math.max(0, Math.min(x, box.scrollLeft + box.clientWidth - tw2 - 4)) + "px";
    tip.style.top = Math.max(0, Math.min(y, b.height - th - 4)) + "px";
  }
  const esc = s => String(s).replace(/[&<>"]/g, c =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

  // ---- つまんで動かす ----------------------------------------------------
  function toSvg(ev) {
    const b = svg.getBoundingClientRect();
    return [(ev.clientX - b.left) / b.width * W, (ev.clientY - b.top) / b.height * H];
  }
  let dragStart = null;   // つまんだ瞬間の位置。**動いていなければクリックと見なす**
  svg.addEventListener("pointerdown", ev => {
    const g = ev.target.closest(".nd");
    if (!g) return;
    const i = +g.dataset.i;
    if (!live(i) || timePast) return;
    drag = i; P[i].fix = true;
    dragStart = {x: P[i].x, y: P[i].y};
    svg.setPointerCapture(ev.pointerId);
    heat(0.35);
    ev.preventDefault();
  });
  svg.addEventListener("pointermove", ev => {
    const g = ev.target.closest(".nd");
    if (drag < 0) {
      if (g && live(+g.dataset.i)) {
        const i = +g.dataset.i;
        if (i !== lit) light(i);
        showTip(i, ev);
      } else if (lit >= 0) { light(-1); tip.hidden = true; }
      return;
    }
    const [x, y] = toSvg(ev);
    P[drag].x = Math.min(Math.max(x, PAD), W - PAD);
    P[drag].y = Math.min(Math.max(y, PAD), H - PAD);
    P[drag].vx = P[drag].vy = 0;
    heat(0.30);
  });
  // ---- クリックで中心へ固定・もう一度で解除 -------------------------------
  // 起案者の指示（2026-08-26）──「クリックしたら、その人を中心にネットワーク図が
  // 動くようにしてほしい」。続く指示 ──「できれば1回クリックで中心に固定されて、
  // また その人物選んだら解除される感じ」。**動いた距離で区別する** ── つまんで
  // 動かす操作と同じ pointerdown/pointerup を使うので、新しい押し口を増やさずに済む。
  //
  // **固定している間は `P[i].fix = true` のままにする。** 前回はアニメーションの
  // 終わりで手を離していたため、力学が再び働いて中心から離れていった ──
  // 「固定される」という指示に応えていなかった。
  let centered = -1;      // 中心に固定している人（-1 は誰も固定していない）
  function centerOn(i) {
    if (!live(i)) return;
    if (centered === i) {
      // **同じ人をもう一度選んだ ── 解除する。**
      P[i].fix = false;
      centered = -1;
      light(-1);
      heat(0.4);
      return;
    }
    if (centered >= 0) P[centered].fix = false;   // 別の人を固定していたら、先に外す
    centered = i;
    const start = {x: P[i].x, y: P[i].y};
    const cx0 = W / 2, cy0 = H / 2;
    P[i].fix = true;
    light(i);
    if (slow) { P[i].x = cx0; P[i].y = cy0; paint(); heat(0.5); return; }
    const t0 = performance.now(), dur = 480;
    const step2 = now => {
      if (centered !== i) return;    // 動いている途中で解除・乗り換えたら打ち切る
      const t = Math.min(1, (now - t0) / dur);
      const e = 1 - (1 - t) ** 3;             // ease-out。急に動いて急に止まる
      P[i].x = start.x + (cx0 - start.x) * e;
      P[i].y = start.y + (cy0 - start.y) * e;
      paint();
      if (t < 1) { requestAnimationFrame(step2); return; }
      heat(0.55);           // `fix` は立てたまま ── 中心に留まり、周りだけが寄ってくる
    };
    requestAnimationFrame(step2);
  }
  const release = () => {
    if (drag < 0) return;
    if (drag !== centered) P[drag].fix = false;   // 固定中の人は、離しても外さない
    drag = -1; dragStart = null; heat(0.25);
  };
  svg.addEventListener("pointerup", () => {
    if (drag < 0) return;
    const moved = dragStart ? Math.hypot(P[drag].x - dragStart.x, P[drag].y - dragStart.y) : 999;
    const clicked = drag;
    drag = -1; dragStart = null;
    if (moved < 4) {
      centerOn(clicked);
    } else {
      // **つまんで動かしたなら、固定はそこで終わる。** 中心に置いたままにする指示は
      // 「クリックで選ぶ」ほうの話であって、つまんで動かした先に固定する話ではない
      if (clicked === centered) centered = -1;
      P[clicked].fix = false;
      heat(0.25);
    }
  });
  svg.addEventListener("pointercancel", release);
  svg.addEventListener("pointerleave", () => { if (drag < 0) { light(-1); tip.hidden = true; } });

  // ---- 外してみる。**この図の見出しの問いに答える操作** ------------------
  const btns = [...document.querySelectorAll(".pcut button")];
  const rst = document.querySelector(".pcut .rst");
  function tell() {
    if (out < 0) {
      said.innerHTML = "";
      return;
    }
    const cs = comps();
    const sizes = cs.map(c => c.length);
    const parts = cs.slice(1).map(c =>
      c.slice(0, 6).map(i => esc(N[i].n)).join("、")
      + (c.length > 6 ? ` ほか ${c.length - 6} 名` : ""));
    said.innerHTML = cs.length < 2
      ? `<b>${esc(N[out].n)} を外しても、残りはつながったままです。</b>`
      : `<b>${esc(N[out].n)} を外すと、残り ${sizes.reduce((a, b) => a + b, 0)} 名が `
        + `${cs.length} つの束に分かれます</b>（${sizes.join(" 名・")} 名）。`
        + `離れるのは ${parts.map(p => "「" + p + "」").join("と")} です。`;
  }
  for (const b of btns) {
    b.addEventListener("click", () => {
      const v = b.dataset.cut;
      const i = v === "reset" ? -1 : +v;
      out = (i === out) ? -1 : i;
      for (const x of btns) x.classList.toggle("on",
        x.dataset.cut !== "reset" && +x.dataset.cut === out);
      rst.hidden = out < 0;
      for (const [k, g] of gN) g.classList.toggle("out", k === out);
      for (const [k, t] of gT) t.classList.toggle("out", k === out);
      for (const l of ln) l.classList.toggle("out",
        out >= 0 && (+l.dataset.a === out || +l.dataset.b === out));
      light(-1); tip.hidden = true;
      tell();
      // **枠に合わせ直す計算は挟まない。** 大きさはもう決まっているので、ここでかけると
      // 落ち着くまでに 3 巡（実測 8 秒）増えるだけで、絵は変わらない
      fits = 3; packed = false;
      hold = out >= 0 ? 90 : 0;
      if (out < 0) { rank = N.map(() => 0); frame(W, H); fits = 0; }  // 戻したら枠も優先順も戻す            // 島が離れると枠の使い方が変わるので、伸ばし直す
      // **ここは動く様子を見せる。** 割れていく動きそのものが答えの確認である
      heat(0.42);
    });
  }

  // ---- 表の行から人を引く。**56 個の点を目で探させない** -----------------
  const sec = box.closest("section");
  const byName = new Map(N.map((n, i) => [n.n, i]));
  for (const tr of sec.querySelectorAll("tbody tr")) {
    const name = (tr.firstElementChild.textContent || "").trim();
    const i = byName.get(name);
    if (i === undefined) continue;
    tr.classList.add("pnl");
    tr.addEventListener("pointerenter", () => { if (live(i)) light(i); });
    tr.addEventListener("pointerleave", () => light(-1));
  }

  // ---- 初回 --------------------------------------------------------------
  //
  // **最初の絵は、動かす前に正しくしておく。** 円周から 300 回ぶん動く様子を見せても、
  // 読み手が知りたいこと（束の形）は何も増えない ── むしろ 5 秒間、まだ正しくない形を
  // 見せることになる。そこで**画面に出す前に力学をまとめて解き、枠に合わせて伸ばす。**
  //
  // **そのあと弱く動かす。** つまめること・触れると反応することが、静止画では伝わらない。
  function settle(n) {
    const a = alpha;
    alpha = 0.6;
    for (let k = 0; k < n; k++) { step(); alpha = Math.max(alpha * 0.985, 0.12); }
    alpha = a;
    for (let k = 0; k < 3 && fit(); k++) { for (let j = 0; j < 90; j++) step(); }
  }
  settle(320);
  paint();
  // **字体が読み込まれてから測り直す。** 幅を字体の到着前に測ると、その値で置き場所を
  // 決めてしまう ── 名前が 1 組だけ重なる不具合が、明るい側だけで出ていた
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => { tw.clear(); labels(); });
  }
  if (!slow) heat(0.16);

  // ---- 時間のつまみ。**配置は変えず、まだ出ていない点と線を隠すだけ** -----
  //
  // 力学を解き直さない ── 解き直すと、増えたのか点が動いただけなのかが読めなくなる
  // （docs/000007-records-network-time-spec.md 4 章）。「外してみる」・つまんで動かす
  // 操作は「いま」だけに残す（過去は読むだけの見え方にする）。
  const tsrc = document.querySelector("[data-pnet-time]");
  let T = null;
  try { if (tsrc) T = JSON.parse(tsrc.textContent); } catch (e) { T = null; }
  if (T && T.stages && T.stages.length) {
    const sl = document.querySelector("[data-psl]");
    const play = document.querySelector("[data-pplay]");
    const note = document.querySelector("[data-pnstage]");
    const gap = document.querySelector("[data-pgap]");
    const pcutBox = document.querySelector(".pcut");
    if (sl) {
      const last = T.stages.length - 1;
      // 累積の可視集合を先に作る（毎回全段をなめ直さない）
      const nodeAt = [], edgeAt = [];
      let vn = new Set(), ve = new Set();
      for (const s of T.stages) {
        for (const i of s.n) vn.add(i);
        for (const [a, b] of s.e) ve.add(a + "_" + b);
        nodeAt.push(new Set(vn));
        edgeAt.push(new Set(ve));
      }
      const apply = k => {
        const visN = nodeAt[k], visE = edgeAt[k];
        futureNodes = new Set();
        for (let i = 0; i < N.length; i++) if (!visN.has(i)) futureNodes.add(i);
        for (const [i, g] of gN) g.classList.toggle("future", futureNodes.has(i));
        for (const [i, t] of gT) t.classList.toggle("future", futureNodes.has(i));
        for (const l of ln) l.classList.toggle("future",
          !visE.has(+l.dataset.a + "_" + +l.dataset.b));
        timePast = k < last;
        if (pcutBox) pcutBox.hidden = timePast;
        if (timePast && out >= 0) {
          const r = document.querySelector(".pcut .rst");
          if (r) r.click();
        }
        if (gap) gap.hidden = !timePast;
        if (note) note.innerHTML = T.stages[k].note
          || '<p class="pnstage"><b>いま</b>です。すべての記録が出ています。</p>';
        light(-1); tip.hidden = true;
        labels();
      };
      sl.addEventListener("input", () => apply(+sl.value));
      let playTimer = 0;
      if (play) play.addEventListener("click", () => {
        clearTimeout(playTimer);
        if (slow) { sl.value = last; apply(last); return; }
        let k = 0;
        const step2 = () => {
          sl.value = k; apply(k);
          if (k >= last) return;
          k++;
          playTimer = setTimeout(step2, 420);
        };
        step2();
      });
      apply(last);
    }
  }
})();

// **この図から分かる文章を作る／作り直す。**（`chronicle.py` の「年表の文を作る」と同じ形）
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest("[data-pread]");
  if (!b) return;
  const box = b.closest(".pread");
  box.querySelector(".said").textContent = "書いています…（1 分ほどかかります）";
  post("/api/people_read", {}, box, null).then(r => {
    box.querySelector(".said").textContent =
      r ? (r.line || "作りました") + "　画面を読み込み直すと出ます" : "";
  });
});

// === ported: tools/taguri/prefmap.py の PM.JS(地図パネル) ===

// **地図と地方の札は、チェックを反転させるだけである。**（`prefmap.py` の説明）
// 塗りは CSS が `:checked` から決めるので、ここでは見た目に触らない ──
// **状態を 2 つ持つと、ずれたときにどちらが本当か決められない。**
(() => {
  // **`.pfil`（場所の絞り込みの form）だけを見る。** `.pbox` は畳んである道具の枠
  // として使い回している名前なので、最初の 1 つが場所の箱とはかぎらない
  const box = document.querySelector("form.pfil");
  if (!box) return;
  const cb = v => box.querySelector('input[name="pref"][value="' + CSS.escape(v) + '"]');
  // 地方の札は「その地方の県が全部入っているか」で光る。全部入っていれば外す側に働く
  const marks = () => box.querySelectorAll(".prg[data-prefs]").forEach(b => {
    const ps = b.dataset.prefs.split(" ");
    b.classList.toggle("on", ps.every(p => cb(p) && cb(p).checked));
  });
  box.addEventListener("click", ev => {
    const pf = ev.target.closest && ev.target.closest(".pmap .pf");
    if (pf) {
      const c = cb(pf.dataset.pref);
      if (c) { c.checked = !c.checked; marks(); }
      return;
    }
    const rg = ev.target.closest && ev.target.closest(".prg");
    if (!rg) return;
    if (rg.classList.contains("clr")) {
      box.querySelectorAll('input[name="pref"]').forEach(c => { c.checked = false; });
      marks();
      return;
    }
    const ps = rg.dataset.prefs.split(" ");
    // **全部入っているときは外す。** 同じ札を 2 度押して何も起きないのは、
    // 押し口として壊れている
    const all = ps.every(p => cb(p) && cb(p).checked);
    ps.forEach(p => { const c = cb(p); if (c) c.checked = !all; });
    marks();
  });
  marks();
})();

// === ported: tools/taguri/stage_calendar.py の JS(カレンダーの「行く日を追加」ダイアログ) ===

// **元は読み込み時に1度だけ走る処理だったが、SPAではフラグメントを
// 差し込むたびに呼び直す必要がある**(#000009)。呼び出しはrenderScreen()。
function fixupMonthScroll(root) {
  (root || document).querySelectorAll(".mscroll .now").forEach(n => {
    const s = n.closest(".mscroll");
    s.scrollLeft = Math.max(0, n.offsetLeft - s.clientWidth * 0.35);
  });
}

// ---- 「観劇日を追加する」ポップアップ ---------------------------------------
// 起案者の指示（2026-08-26）──「日程を追加する、があるなら『行く日を入れる』は
// 不要です。あと名前を『観劇日を追加する』にして」。**行く日を入れる口はここ
// 1 つにまとめた** ── 券を足す・確定する・取り消すのすべてがこのポップアップの
// 中で完結する。**外部のライブラリは使わない**（`<dialog>` は素の HTML で
// 開閉できる）。

// **選んだ公演に合わせて、日付の範囲と「地方の日程／入れてある日」を切り替える。**
// 起案者の指示 ──「『公演』を選んだら各地方日程の日付が表示されるようになって
// いて、次の『行く日』入力を支援するように」。中身は `add_ticket_button_html` が
// 選択肢ごとに埋め込み済みなので、ここでは表示・非表示を切り替えるだけでよい
// （画面から外部・API を叩かない）。
function tkdSync(dlg) {
  const sel = dlg.querySelector(".tkd-work"), d = dlg.querySelector(".tkd-date");
  const opt = sel && sel.selectedOptions[0];
  if (opt) { d.min = opt.dataset.lo; d.max = opt.dataset.hi; }
  dlg.querySelectorAll(".tkinfo").forEach(e => {
    e.hidden = !sel || e.dataset.for !== sel.value;
  });
}
document.addEventListener("click", ev => {
  const open = ev.target.closest && ev.target.closest("[data-open-dialog]");
  if (open) {
    const dlg = document.getElementById(open.dataset.openDialog);
    if (dlg) { tkdSync(dlg); dlg.showModal(); }
    return;
  }
  const close = ev.target.closest && ev.target.closest("[data-dlg-close]");
  if (close) { close.closest("dialog").close(); return; }
  const add = ev.target.closest && ev.target.closest("[data-dlg-add]");
  if (add) {
    const dlg = add.closest("dialog"), sel = dlg.querySelector(".tkd-work");
    const dd = dlg.querySelector(".tkd-date").value, tt = dlg.querySelector(".tkd-time").value;
    const said = dlg.querySelector(".said");
    if (!dd) { said.textContent = "行く日を入れてください"; return; }
    post("/api/ticket", {stage_id: sel.value, date: dd, time: tt}, dlg, "記録しました")
      .then(r => { if (r) setTimeout(() => location.reload(), 500); });
    return;
  }
  // **すでに入れてある券の「確定」「取り消し」。** ポップアップの中の一覧
  // （`.tkinfo .tklist`）にだけ出る。**押した券自身の会場（`data-stage`）を使う**
  // ── 1 つの公演が複数の会場をまとめて持つことがあるので、選んでいる公演の
  // 代表会場に頼ると、他の会場の券まで代表会場のものとして操作してしまう
  const b = ev.target.closest && ev.target.closest(".tkinfo .tklist button");
  if (!b) return;
  const dlg = b.closest("dialog");
  const body = {stage_id: b.dataset.stage, date: b.dataset.date, time: b.dataset.time,
                action: b.dataset.ok ? "confirm" : "del"};
  const said = {del: "取り消しました", confirm: "確定しました"}[body.action];
  post("/api/ticket", body, dlg, said).then(r => {
    if (r) setTimeout(() => location.reload(), 500);
  });
});
document.addEventListener("change", ev => {
  const sel = ev.target.closest && ev.target.closest(".tkd-work");
  if (sel) tkdSync(sel.closest("dialog"));
});
