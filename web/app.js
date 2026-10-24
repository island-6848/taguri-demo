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
 *  - X-Taguri-Tokenヘッダは送らない(公開版では検査されない)
 *  - .syn .mrb のクランプ調整を、フラグメント差し込みのたびに呼べる関数に分離
 */

// **デモ版かサービス版か**(config.js が開いたURLから決める)。2つは別のAPIサーバーに
// つながるので、記録も Cookie も混ざらない(docs/editions.md)
const EDITION = window.TAGURI || {edition: "demo", api: "https://taguri-demo.onrender.com",
  base: "/taguri-demo", demoBase: "/taguri-demo"};
const IS_DEMO = EDITION.edition === "demo";
const API_BASE = EDITION.api;
// 探す先の呼び名。デモは見本の公演、サービス版は毎日更新する公演一覧から探す
const CATALOG_NAME = IS_DEMO ? "デモに用意されている公演" : "たぐりの公演一覧";

// --- 画面パス -> APIのスクリーン名。実装済みのものだけ IMPLEMENTED に入れる ---
const SCREENS = {
  "/": "recommend", "/recommend": "recommend",
  "/start": "start",
  "/recommend/reminder": "reminder",
  "/recommend/interest": "interest",
  "/recommend/favourites": "favourites",
  // あらすじのハッシュタグ（題材）の公演の一覧（起案者の指示 2026-10-18）。Worker だけが答える画面
  "/recommend/tag": "tagged",
  // おすすめ理由の太字（人物・形式）の個別の画面（起案者の指示 2026-10-19。src/screens/entity.js）。Worker だけが答える画面
  "/recommend/person": "person", "/recommend/kind": "kind",
  "/calendar": "calendar",
  "/tickets": "tickets",
  "/rate": "rate", "/rate/unrated": "unrated", "/rate/notes": "notes",
  "/register": "register",
  "/records": "records",
  "/records/chronicle": "chronicle", "/records/works": "works",
  "/search": "search", "/settings": "settings",
  // アカウント（本人だけが見る。起案者の指示 2026-10-14）。Worker だけが答える画面なので、
  // デモ版（Render）には入り口を出さない（下の NAV・renderPNav）
  "/account": "account",
};
// 全17画面を実装済み(#000009)。「準備中」プレースホルダは段階移行の
// 名残りとして残してある(未知のIMPLEMENTED外の画面名が来た場合の保険)。
const IMPLEMENTED = new Set(["recommend", "interest", "reminder", "favourites", "calendar",
  "rate", "unrated", "notes", "tickets", "records", "chronicle", "works",
  "start", "register", "settings", "search", "account", "tagged", "person", "kind"]);

// --- NAV(app.py の NAV表と同じデータ) -------------------------------------
// ページの地図（起案者の指摘 2026-10-14「リマインドはおすすめの下？違和感ある」で見直した）:
// おすすめ＝これから観るものを選ぶ（今週のおすすめ・興味あり・お気に入り）／予定＝観に行く日を確かめる
// （公演カレンダー・開幕リマインド・購入済み公演）。開幕リマインドは「初日が近い公演の知らせ」で、選ぶ画面
// ではなく日程を見る画面なので、予定に移した。URL（/recommend/reminder）は変えない（覚えた道を壊さない）
// 左の帯とすだれの「今週のおすすめ」は短い名前にする（起案者の指示 2026-10-19「『今週のあなたへのおすすめ』っていうボタンの文字列は長すぎる」）。画面の見出しはそのまま
const NAV = [[null, "おすすめ", "ticket", [["/recommend", "今週のおすすめ", "ticket"], ["/recommend/interest", "興味あり", "flag"], ["/recommend/favourites", "お気に入り", "star"]]], [null, "予定", "calendar", [["/calendar", "公演カレンダー", "calendar"], ["/recommend/reminder", "開幕リマインド", "inbox"], ["/tickets", "購入済の公演", "ticket"]]], [null, "観た公演の評価", "check", [["/rate", "評価一覧", "check"], ["/rate/unrated", "未評価", "clock"], ["/rate/notes", "感想", "pencil"], ["/register", "観劇記録を追加", "plus"]]], [null, "記録を見返す", "chart", [["/records", "眺める", "chart"], ["/records/chronicle", "観劇史年表", "calendar"], ["/records/works", "日記帳", "book"]]], ["/search", "探す", "search", []], ["/settings", "設定", "gear", []]];
// 左の帯でも、設定はアカウントの小窓に入れる（起案者の指示 2026-10-19）。デモ版はアカウントが無いので設定のまま
if (!IS_DEMO) NAV.splice(NAV.findIndex(n => n[0] === "/settings"), 1);
if (!IS_DEMO) NAV.push(["/account", "アカウント", "user", []]);

// --- 絵記号(icons.py の P/ALIAS をそのまま) --------------------------------
const ICON_P = {"ticket": "M3 9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2 2 2 0 0 0 0 6 2 2 0 0 1-2 2H5a2 2 0 0 1-2-2 2 2 0 0 0 0-6zM11 7v10", "star": "M12 3.8l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z", "inbox": "M3 12h5l1.5 2.5h5L16 12h5M3 12l3-7h12l3 7v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z", "chart": "M3 20h18M6.5 20v-5M11.5 20V6M16.5 20v-9", "search": "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM16.2 16.2 21 21", "download": "M12 3v12m0 0 4-4m-4 4-4-4M4 20h16", "mail": "M3 6h18v12H3zM3 6.5l9 6.5 9-6.5", "plus": "M12 5v14M5 12h14", "clock": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7.5V12l3.5 2", "pencil": "M4 20h4L18 10l-4-4L4 16zM13.5 6.5l4 4", "tag": "M4 12.5 12.5 4H20v7.5L11.5 20zM16.4 7.6h.01", "image": "M3 5h18v14H3zM3 15.5l5-4 4 3 3-2.5 6 4.5M8 9.5h.01", "user": "M12 4a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM4 20c0-3.3 3.6-5 8-5s8 1.7 8 5", "building": "M4 20V6l6-2.5V20M10 20h10V10.5L10 7M13.5 12h.01M13.5 16h.01M17 12h.01M17 16h.01", "book": "M4 5h7v15H4zM13 5h7v15h-7M11 5v15", "light": "M12 3v3.5M12 17.5V21M3 12h3.5M17.5 12H21M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18", "eye": "M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6zM12 9.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z", "check": "M4.5 12.5 9.5 18 20 6", "flag": "M5 21V4h13l-2.5 4.5L18 13H5", "calendar": "M4 6.5h16V20H4zM4 10.5h16M8.5 3.5v4M15.5 3.5v4", "chevron": "M9.5 5.5 16 12l-6.5 6.5", "network": "M6 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM12 8a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM6.9 15.3 10.6 9M17.1 15.3 13.4 9M8 17.3h8", "gear": "M10.6 3.1 13.4 3.1 15.2 6.5 19.0 6.3 20.4 8.8 18.4 12.0 20.4 15.2 19.0 17.7 15.2 17.5 13.4 20.9 10.6 20.9 8.8 17.5 5.0 17.7 3.6 15.2 5.6 12.0 3.6 8.8 5.0 6.3 8.8 6.5ZM12 9.8a2.2 2.2 0 1 0 0 4.4 2.2 2.2 0 0 0 0-4.4z", "link": "M14 4h6v6M20 4 10 14M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h5", "logout": "M10 4H5v16h5M15 8l4 4-4 4M19 12H9"};
// スマホ幅の 4 つの大メニューの絵記号（dec-phone-nav-four）: 毛糸玉・判子・帳面
Object.assign(ICON_P, {"yen": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8.6 7.4 12 12l3.4-4.6M12 12v5.2M9.2 12.6h5.6M9.2 15.2h5.6", "building": "M4 20.5h16M6.5 20.5V4.5h8v16M14.5 9.5h3.5v11M9 8h2.5M9 11.5h2.5M9 15h2.5", "info": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v5.5M12 7.6h.01", "yarn": "M11 4a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15zM5.2 7.6c4.6.8 8.6 4.6 9.6 10.6M3.7 11.3c4.4.4 7.7 3.4 8.4 7.6M8.6 4.4c4.6 1.4 8.3 5.4 9.5 10M16.3 16.3c1.8 1.6 3.4 2.6 5.2 2.9", "stamp": "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM12 7.8a4.2 4.2 0 1 0 0 8.4 4.2 4.2 0 0 0 0-8.4z", "notebook": "M5 4.5h11.5a2 2 0 0 1 2 2V20H7a2 2 0 0 1-2-2zM5 17.5a2 2 0 0 1 2-2h11.5M9 8.5h6"});
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
  const p = location.pathname;
  if (EDITION.base && (p === EDITION.base || p.indexOf(EDITION.base + "/") === 0)) return EDITION.base;
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
  return '<div class="navrow">' + NAV.map(([p, t, k, kids]) => p === null
    ? navGroupHtml(t, k, kids)
    : navItemHtml(p, t, k, false) + kids.map(c => navItemHtml(c[0], c[1], c[2], true)).join("")
  ).join("") + "</div>";
}
// 左の帯の「アカウント」は、押すとアカウント・設定・ログアウトの小窓を開く（起案者の指示 2026-10-19。openAcctMenu）
function markAcctNav(root) {
  if (IS_DEMO) return;
  root.querySelectorAll('a[data-path="/account"]:not(.acctpop a)').forEach(a => {
    if (a.closest(".acctpop")) return;
    a.setAttribute("data-acct-menu", ""); a.setAttribute("aria-haspopup", "menu"); a.setAttribute("aria-expanded", "false");
  });
}

// **スマホ幅の行き先 ── 4 つの大メニューを均等に並べて常に出し、子はその下にすだれで下ろす。**
// （起案者の指示 2026-10-13「スマホ版はメインの４つの大きいメニューは固定で表示して、それより子の
// メニューは各メニューの下にすだれで出てくるように」「大きい４つのメニューは均等割り付け」
// 「４つの大きいメニューにアイコンをつけて」）。パソコン幅では今までどおり左の帯（NAV）を使う。
// 探すは帯の検索窓、設定は右上の歯車、公演情報の登録はその左の「＋」から入る。
const PNAV = [
  ["rec", "おすすめ", "yarn", [["/recommend", "今週のおすすめ"], ["/recommend/interest", "興味あり"]]],
  // お気に入りは、おすすめの子から出して、おすすめの右に 1 つのボタンとして置く（起案者の指示 2026-10-24「おすすめの下にある
  // 『お気に入り』を独立させて、おすすめタブの右側に置いてほしい（スマホ）」）。子が無いので、押すとそのまま移る
  ["fav", "お気に入り", "star", [], "/recommend/favourites"],
  ["plan", "予定", "calendar", [["/calendar", "公演カレンダー"], ["/recommend/reminder", "開幕リマインド"], ["/tickets", "購入済の公演"]]],
  ["rate", "評価", "stamp", [["/rate", "評価一覧"], ["/rate/unrated", "未評価"], ["/rate/notes", "感想"], ["/register", "観劇記録を追加"]]],
  ["rec2", "記録", "notebook", [["/records/works", "日記帳"], ["/records", "眺める"], ["/records/chronicle", "観劇史年表"]]],
];
function renderPNav() {
  // 公演情報の登録は「記録」の子から外し、歯車の左の「＋」から入る（起案者の指示 2026-10-13「スマホ版のみ」）。
  // 押したら登録の画面へそのまま移る。3 つの入口を選ぶ札は出さない（起案者の指示 2026-10-17「ポップアップ消して」）
  return '<a class="padd" href="/register" data-path="/register" aria-label="観劇記録を追加" title="観劇記録を追加"'
    + '>' + ico("plus", 22) + "</a>"
    // アカウントのアイコンは、押すとアカウント・設定・ログアウトの小窓を開く。歯車（設定）は小窓に入れたので外した
    // （起案者の指示 2026-10-19「現在のアカウントアイコンを押したら…ポップアップ…設定のアイコンは消して」）。デモ版は歯車のまま
    + (IS_DEMO ? '<a class="pset" href="/settings" data-path="/settings" aria-label="設定">' + ico("gear", 20) + "</a>"
      : '<button type="button" class="pacct" data-acct-menu aria-haspopup="menu" aria-expanded="false" aria-label="アカウント" title="アカウント">' + ico("user", 20) + "</button>")
    + '<div class="pnav">' + PNAV.map(([id, label, icon, kids, path]) => (kids.length
      ? '<button type="button" class="pm" data-pm="' + id + '" aria-expanded="false">' + ico(icon, 22)
        + '<span class="pl">' + E(label) + ico("chevron", 9, "cv") + "</span></button>"
      : '<a class="pm" data-pm="' + id + '" href="' + path + '" data-path="' + path + '">' + ico(icon, 22)
        + '<span class="pl">' + E(label) + "</span></a>")).join("") + "</div>"
    + PNAV.filter(m => m[3].length).map(([id, , , kids]) => '<div class="psud' + (kids.length === 3 ? " three" : "") + '" data-psud="' + id + '" hidden>'
      + kids.map(([p, t]) => '<a href="' + p + '" data-path="' + p + '"><i aria-hidden="true"></i>' + E(t) + "</a>").join("")
      + "</div>").join("");
}
function openPSud(id) {
  document.querySelectorAll(".side .pm").forEach(b => b.setAttribute("aria-expanded", b.dataset.pm === id ? "true" : "false"));
  document.querySelectorAll(".side .psud").forEach(d => { d.hidden = d.dataset.psud !== id; });
}
document.addEventListener("click", ev => {
  const b = ev.target.closest(".side .pm");
  if (b) openPSud(b.getAttribute("aria-expanded") === "true" ? null : b.dataset.pm);
});

// **開閉状態はlocalStorageに覚える**(元のNAV_FOLD_JSと同じ挙動)。
// **ただしスマホ幅では「開いた」を覚えから戻さない**(起案者の指摘・2026-10-07
// 「スマホから見たらメニューが幅取ってる」)。帯が本文の上に載る幅では、開いた束が
// そのまま本文を下へ押し出す ── いま居る束だけを開き(updateNavActive)、ほかは畳む。
function restoreNavFold() {
  try {
    const narrow = window.matchMedia("(max-width:820px)").matches;
    document.querySelectorAll(".side .grp").forEach(g => {
      const v = localStorage.getItem("taguri.fold." + g.dataset.grp);
      if (v === "1") g.open = false; else if (v === "0" && !narrow) g.open = true;
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
  // スマホ幅の大メニュー: いまいる組を塗り、開いていたすだれは画面を移ったら閉じる
  const here = PNAV.find(m => m[4] === path || m[3].some(k => k[0] === path));
  document.querySelectorAll(".side .pm").forEach(b => b.classList.toggle("on", !!here && b.dataset.pm === here[0]));
  openPSud(null);
  document.querySelectorAll(".side a[data-path]").forEach(a => {
    const on = a.dataset.path === path;
    a.classList.toggle("on", on);
    if (on) {
      const grp = a.closest(".grp");
      if (grp) grp.open = true;
      // **スマホ幅の横1行の帯では、現在地を見える位置まで送る。** 右へ送った先の
      // 画面を開いたとき、現在地の印が帯の外に隠れたままになるのを避ける
      const row = a.closest(".navrow");
      if (row && row.scrollWidth > row.clientWidth) {
        const x = a.offsetLeft - row.offsetLeft;
        if (x < row.scrollLeft || x + a.offsetWidth > row.scrollLeft + row.clientWidth - 24)
          row.scrollLeft = Math.max(0, x - 40);
      }
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

// **読み込み中は、毛糸玉が転がって糸をたぐる。**（起案者の指示 2026-10-13
// 「読み込み画面もデザインに合わせてスタイリッシュに。でもかわいく」）
// 前の「幕と、舞台を歩き回る人型のピクトグラム」は、えんじで塗った幕や道具が多く、
// 今の見た目（うすい灰の地・白い紙・差し色はえんじだけ）の中では重かった。
// ロゴの下の毛糸の線と同じ波の線を、うすい灰の「これから引く糸」として先に敷き、
// 毛糸玉がその上を転がって、通ったあとをえんじの糸にしていく ── 引いた糸の長さが
// そのまま進み具合になる（棒の進捗の代わり）。かわいさは毛糸玉の弾みとつぶれ、
// 転がるぶんだけの回転、ほどけた糸の端の揺れで出す。顔は描かない。
const YARN_W = 240, YARN_H = 40;
// ロゴの毛糸の線（M1 4 C 16 1, 26 6, 41 3 S 66 1, 81 4）と同じ波を、横に 3 回つなぐ
const YARN_PATH = "M8 30 C 24 26, 34 33, 50 29 S 76 25, 88 30 S 112 34, 128 29 S 154 25, 166 30 S 190 34, 206 29 S 226 26, 232 30";
const YARN_BALL = '<svg class="tg-ball" viewBox="-14 -14 28 28" aria-hidden="true">'
  + '<g class="tg-ball-spin">'
  + '<circle r="11" class="tg-ball-body"/>'
  + '<g class="tg-ball-wrap">'
  + '<path d="M-9.5 -4.5c6 1 13 5.5 15.5 13"/>'
  + '<path d="M-10.8 1c5 .4 9.6 3.4 11 8.8"/>'
  + '<path d="M-5.8 -9.4c6 2 11 7.8 12.6 14"/>'
  + '<path d="M2 -10.8c4 2.2 7.2 6 8.4 10.6"/>'
  + '</g></g></svg>';
const COLD_START_NOTE = "サーバーを起動しています。無料枠のため、少し時間がかかることがあります…";

function loadingHtml() {
  return '<div class="tg-loading" role="status" aria-label="読み込み中">'
    + '<div class="tg-yarn">'
    + '<svg class="tg-thread" viewBox="0 0 ' + YARN_W + ' ' + YARN_H + '" aria-hidden="true">'
    + '<path class="tg-thread-ahead" d="' + YARN_PATH + '" pathLength="100"/>'
    + '<path class="tg-thread-done" d="' + YARN_PATH + '" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/>'
    + '</svg>'
    + '<div class="tg-ball-pos"><div class="tg-ball-hop">' + YARN_BALL + '</div></div>'
    + '</div>'
    + '<p class="tg-load-say">公演の糸をたぐっています<span class="tg-dots" aria-hidden="true"><i>.</i><i>.</i><i>.</i></span></p>'
    + '<p class="tg-load-note" hidden>' + COLD_START_NOTE + '</p>'
    + '</div>';
}

// **毛糸玉を、糸の上の p% の位置に置く。** 位置は糸の形そのもの（getPointAtLength）
// から取るので、波の山と谷を玉がなぞる。回した角度は進んだ道のり ÷ 半径で出す
// （滑らずに転がっているように見える）。
function placeYarn(el, p) {
  const done = el.querySelector(".tg-thread-done");
  const pos = el.querySelector(".tg-ball-pos");
  const spin = el.querySelector(".tg-ball-spin");
  const svg = el.querySelector(".tg-thread");
  if (!done || !pos || !svg) return;
  done.setAttribute("stroke-dashoffset", String(100 - p));
  let x = 8 + (232 - 8) * p / 100, y = 30;
  try {
    const len = done.getTotalLength();
    const pt = done.getPointAtLength(len * p / 100);
    x = pt.x; y = pt.y;
  } catch (e) {}
  const k = svg.clientWidth ? svg.clientWidth / YARN_W : 1;
  pos.style.transform = "translate(" + (x * k).toFixed(1) + "px," + (y * k).toFixed(1) + "px)";
  if (spin) spin.style.transform = "rotate(" + Math.round((x - 8) * k / 11 * 57.3) + "deg)";
}

// **表示 → 糸をたぐる → 呼び出し側が止める、までを1つにまとめる。**
// 本当の進み具合は分からないので、糸は経過時間から95%まで滑らかに近づける演出にとどめ、
// 数字（%）は出さない。数字は「何割終わったか」と読めてしまう（#151）。
// 5秒以上かかっていたら、コールドスタートの案内をそっと添える(待たされる理由が
// 分からないと不安になるため)。
function startLoading(el) {
  el.innerHTML = loadingHtml();
  const t0 = performance.now();
  const box = el.querySelector(".tg-loading");
  const note = el.querySelector(".tg-load-note");

  const tick = () => {
    if (!box || !box.isConnected) return;
    const elapsed = performance.now() - t0;
    const p = Math.min(95, Math.round(95 * (1 - Math.exp(-elapsed / 6000))));
    placeYarn(box, p);
  };
  tick();
  const progressTimer = setInterval(tick, 150);
  const noteTimer = setTimeout(() => { if (note && note.isConnected) note.hidden = false; }, 5000);

  return () => {
    clearInterval(progressTimer);
    clearTimeout(noteTimer);
    if (box && box.isConnected) {
      placeYarn(box, 100);
      box.classList.add("done");
    }
  };
}

// Navigation reuses fragments for 45 seconds. Successful mutations invalidate
// this browser's saved fragments, without reloading the current screen.
const fragmentCache = new Map();
const FRAGMENT_CACHE_TTL_MS = 45000;
function fragmentCacheGet(key) {
  const hit = fragmentCache.get(key);
  if (!hit) return null;
  if (Date.now() >= hit.expires) { fragmentCache.delete(key); return null; }
  return hit.data;
}
function fragmentCacheSet(key, data) {
  fragmentCache.set(key, {expires: Date.now() + FRAGMENT_CACHE_TTL_MS, data});
}

// **初めての訪問者を、その場で自動的にゲスト登録する（利用者ごとのデータ分離・
// E3）。** サーバ側(`serve.Handler._resolve_user`)がセッションCookieを持たない
// 要求を受けると、その場で復旧コードを発行してCookieを返す。**生の復旧コードは
// この応答に一度だけ乗る**（サーバは以後これを二度と持たない）ので、ここで
// 受け取ったらその場で見せて控えてもらう。二度と同じコードは見せられない。
let welcomeShown = false;
function showWelcomeCode(code) {
  if (!code || welcomeShown) return;
  welcomeShown = true;
  const wrap = document.createElement("div");
  wrap.className = "tg-welcome";
  wrap.innerHTML =
    '<div class="tg-welcome-box">'
    + (IS_DEMO ? '<h2>デモ用の復旧コードです</h2>' : '<h2>あなたの復旧コードです</h2>')
    + '<p>他の端末でも同じ記録を使いたいときや、Cookieを消してしまったときには、'
    + 'このコードが必要になります。<b>表示するのは今だけで、二度と表示できません。</b>'
    + (IS_DEMO ? 'デモの再起動で記録がリセットされると、このコードも使えなくなります。'
               : 'このコードがあれば、別の端末からも同じ記録に戻れます。大切に控えてください。')
    + '</p>'
    + '<code class="tg-welcome-code">' + E(code) + '</code>'
    + '<div class="tg-welcome-btns">'
    + '<button type="button" data-wc-copy>コピーする</button>'
    + '<button type="button" data-wc-ok>控えました</button>'
    + '</div></div>';
  document.body.appendChild(wrap);
  wrap.querySelector("[data-wc-copy]").addEventListener("click", () => {
    const said = wrap.querySelector("[data-wc-copy]");
    (navigator.clipboard && navigator.clipboard.writeText(code)
      .then(() => { said.textContent = "コピーしました"; })
      .catch(() => { said.textContent = "コピーできませんでした。手で選んでコピーしてください"; }))
      || (said.textContent = "コピーできませんでした。手で選んでコピーしてください");
  });
  wrap.querySelector("[data-wc-ok]").addEventListener("click", () => wrap.remove());
}

// **d3を遅延読み込みする。** 220KB超あり、使うのは「眺める」(storyline)
// だけなので、常に読み込まずに使うときだけ取りに行く。自前で同梱した
// vendor/d3.v7.min.js を使う(Render経由の配信には頼らない、Phase 0参照)。
// 一度読み込んだら使い回す。
let d3LoadPromise = null;
function ensureD3() {
  if (!d3LoadPromise) {
    d3LoadPromise = new Promise(resolve => {
      const s = document.createElement("script");
      s.src = "/taguri-demo/vendor/d3.v7.min.js";
      s.onload = resolve;
      s.onerror = resolve;
      document.body.appendChild(s);
    });
  }
  return d3LoadPromise;
}

// **storyline.py(観る世界の乗り換わりを見る図)が埋め込むJS。**
// `<script>`タグとして本文(body_html)の中に来るが、innerHTML経由では
// 実行されない ── 同じ中身を storyline-draw.js に置き、`#sl-data`(材料のJSON)が
// 画面に来るたびに読み込み直す(新しいデータで描き直すため、
// chronicle.pyのJS(委譲登録・1回きりでよい)とは事情が違う)。
// 同じファイルでも、新しい <script src> を足すたびに動き直す（2 回目からはブラウザの控えから読む）
function runStorylineScript() {
  const s = document.createElement("script");
  s.src = "/taguri-demo/storyline-draw.js";
  s.onload = s.onerror = () => s.remove();
  document.body.appendChild(s);
}
function fixupStoryline(root) {
  if (!root.querySelector("#sl-data")) return;
  ensureD3().then(runStorylineScript);
}

// **重い図はブラウザで組み立てる**(Cloudflare 版の「眺める」)。Worker は 1 回に CPU を
// 10 ミリ秒しか使えないので、人の流れ・相関図は記録(`#figs-src`)と置き場所
// (`[data-fig]`)だけを返し、同じ組み立て(/figs/figs.js、Python と同じ HTML)をここで
// 動かす。組み上がってから、上の2つの図の動き(storyline・相関図)を付け直す。
function fixupFigs(root) {
  const src = root.querySelector("#figs-src");
  if (!src) return;
  import("/figs/figs.js").then(m => {
    if (!src.isConnected) return;   // 組み上がる前に別の画面へ移った
    m.fill(root);
    fixupStoryline(root);
    fixupPeopleNet(root);
  }).catch(() => {
    root.querySelectorAll("[data-fig]").forEach(box => {
      box.outerHTML = '<p class="empty">この図は読み込めませんでした。ページを開き直すと出ることがあります。</p>';
    });
  });
}

// **公開版(デモ・サービスとも)の制限。** 公演情報と画像は全員で共有するので編集させず、
// 外部サイトもその場では検索しない(探す先は手元の公演一覧)。文言だけ版で変える
const WEB_BUTTON = IS_DEMO ? "デモの公演から探す" : "公演一覧から探す";
// ---- 公演修正依頼（起案者の指示 2026-10-17。届くと起案者にメールが行き、手元の管理画面で直す）。
// カードの右上（枠の外）のヘルプの印（？）を押すと、ポップアップで送れる（起案者の指示 2026-10-17「ヘルプマークアイコンを
// 押したらポップアップでメール送信できるようにして」。src/screens/fixrequest.js）
const FIX_KINDS = ["日程", "料金", "会場", "あらすじ", "出演・スタッフ", "ポスター", "その他"];
const HELP_ICON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
  + '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8 1c0 1.7-2.4 2.2-2.4 3.7"/><path d="M12 17.2h.01"/></svg>';
// 発売の札の文言を「発売済」「未確認」「10/25発売」にそろえる（起案者の指示 2026-10-19「『発売済』『未確認』『◎/◎発売』に文言を揃えて」）。
// 札はデータの取得のときに作ってデータベースに置いてあるので、前の版の文言（発売済み・確認できず・発売日不明・「10/25 発売」）の
// カードは、作り直されるまでここで読み替える（render_recommend.sale_label と同じ）
function saleLabel(v) {
  v = String(v || "").trim();
  v = ({"確認できず": "未確認", "発売日不明": "未確認", "発売済み": "発売済", "": "未確認"})[v] ?? v;
  return v.replace(/\s+発売$/, "発売");
}
function saleLabels(root) {
  root.querySelectorAll(".sale .pill").forEach(p => {
    const t = [...p.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
    if (!t) return;
    const was = t.textContent.trim(), next = saleLabel(was);
    if (next !== was) t.textContent = t.textContent.replace(was, next);   // ↗ との間の空白は残す
    if (next === "未確認") { p.classList.remove("ok", "soon"); p.classList.add("warn"); }
  });
}
function fixLinks(root) {
  if (IS_DEMO || !API_BASE) return;
  root.querySelectorAll("article.ticket[data-stage]").forEach(t => {
    if (t.querySelector(".fixq")) return;
    const box = document.createElement("div");
    box.className = "fixq";
    box.innerHTML = '<button type="button" class="fixq-open" aria-label="公演情報の誤りを知らせる" title="公演情報の誤りを知らせる">' + HELP_ICON + '</button>';
    // カードの枠の内側の右下の角に小さく出す（起案者の指示 2026-10-18「ヘルプマークやっぱりカード内の右下角において」。
    // その前の同じ日の指示で枠の外の右上に置いていた。そこには候補から消す ✕ を置く）。枠（article）の直下に置き、
    // 位置は theme.css の「カードの見た目（作業 A）」の塊
    t.appendChild(box);
    dismissButton(t);
  });
}
// ---- 候補から消す ✕（起案者の指示 2026-10-18「逆に今ヘルプマークがあるとこには取り消しの✕をつけて。たとえばお気に入りとか、
// これいらんなってときがある。その時候補から消したい。興味の画面でバツを押された場合は、興味なしか視界にも入れたくないから
// 結構マイナスと判断できる」）。カードの枠の外の右上。押すと /api/react に value 'dismiss'（興味ありの一覧では 'dismiss_strong'）を
// 三択のボタンと同じ形（shown・siblings・from）で送り、カードを消す。購入済の公演（持っている券）のカードには出さない
const DISMISS_ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/></svg>';
// 購入済の公演の画面では、もう行った・券を買い足さない公演を一覧から外す口として出す（起案者の指示 2026-10-24「購入済に
// ある公演、もう1回行ったし今後もチケット買い足さなさそうなやつはカード右上の✕ボタンを押して画面から消せるようにしたい」）。
// 送るのはほかの画面と同じ 'dismiss'。観た記録と入れた行く日は消えない。ほかの画面の購入済のカードには、これまでどおり出さない
function dismissButton(t) {
  const here = location.pathname.slice(REPO_BASE.length) || "/";
  if (t.querySelector(":scope > .dismissq") || (t.classList.contains("owned") && here !== "/tickets")) return;
  const box = document.createElement("div");
  box.className = "dismissq";
  const label = here === "/tickets" ? "この公演を購入済の一覧から外す（観た記録と行く日は残ります）"
    : here === "/recommend/interest" ? "この公演を一覧から外し、今後のおすすめを減らす"
    : "この公演を候補に表示しない（好みには反映しません）";
  box.innerHTML = '<button type="button" class="dismissq-open" aria-label="' + E(label) + '" title="' + E(label) + '">' + DISMISS_ICON + "</button>";
  t.appendChild(box);
}
function openFixPopup(t) {
  const title = ((t.querySelector("h3") || {}).textContent || "").trim();
  const pop = document.createElement("div");
  pop.className = "fixpop";
  pop.innerHTML = '<div class="fixpop-box" role="dialog" aria-modal="true" aria-labelledby="fixpop-h">'
    + '<button type="button" class="fixpop-x" aria-label="閉じる">×</button>'
    + '<h2 id="fixpop-h">公演情報の誤りを知らせる</h2>'
    + '<p class="fixpop-t">' + E(title) + '</p>'
    + '<label>どこが違いますか <select class="fixq-kind">' + FIX_KINDS.map(k => '<option>' + E(k) + '</option>').join("") + '</select></label>'
    + '<textarea class="fixq-msg" rows="4" maxlength="1000" placeholder="正しい情報や、それが載っているページの URL を書いてください"></textarea>'
    + '<div class="fixq-foot"><button type="button" class="fixq-send">送る</button><span class="said" role="status"></span></div>'
    + '<p class="note">知らせた内容は、たぐりの運営者にメールで届きます。あなたの名前やアドレスは運営者への知らせに入れません。</p></div>';
  const close = () => { pop.remove(); document.removeEventListener("keydown", esc); };
  const esc = e => { if (e.key === "Escape") close(); };
  pop.addEventListener("click", async ev => {
    if (ev.target === pop || ev.target.closest(".fixpop-x")) return close();
    const b = ev.target.closest(".fixq-send");
    if (!b) return;
    const msg = pop.querySelector(".fixq-msg").value.trim(), said = pop.querySelector(".said");
    if (!msg) { said.textContent = "どう違うかを書いてください"; return; }
    b.disabled = true;
    const d = await post("/api/fix_request", {stage_id: t.dataset.stage, kind: pop.querySelector(".fixq-kind").value, message: msg},
      pop.querySelector(".fixpop-box"), "送りました。ありがとうございます。運営者が確かめて直します");
    if (d) setTimeout(close, 2200); else b.disabled = false;
  });
  document.addEventListener("keydown", esc);
  document.body.appendChild(pop);
  pop.querySelector(".fixq-msg").focus();
}
// カードの「ほか n 会場」: 押すと、ほかの会場の一覧を開く・閉じる（起案者の指示 2026-10-18）
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest(".mvmore");
  if (!b) return;
  const ul = b.closest(".meta")?.querySelector(".mvlist");
  if (!ul) return;
  ul.hidden = !ul.hidden;
  b.setAttribute("aria-expanded", String(!ul.hidden));
});
// あらすじの「続きを読む」で続きを開き、「折りたたむ」で閉じる（起案者の指示 2026-10-18）
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest(".lsynopen, .lsynfold");
  if (!b) return;
  const m = b.closest(".lsynmore"), rest = m && m.querySelector(".lsynrest"), open = m && m.querySelector(".lsynopen");
  if (!rest || !open) return;
  const on = b.classList.contains("lsynopen");
  rest.hidden = !on;
  open.hidden = on;
  open.setAttribute("aria-expanded", String(on));
  m.classList.toggle("open", on);
  (on ? rest.querySelector(".lsynfold") : open).focus({preventScroll: true});
});
// 候補から消す ✕ を押したとき（dismissButton）。記録できたらカードを「候補から消しました」の 1 行に置き換え、おすすめの画面なら
// 三択のボタンと同じく、空いた枠を次の候補で埋める（fill_only）。記録できなかったらカードは残し、帯の欄に理由を出す
document.addEventListener("click", async ev => {
  const b = ev.target.closest && ev.target.closest(".dismissq-open");
  if (!b || b.disabled) return;
  const t = b.closest("article.ticket[data-stage]");
  if (!t) return;
  const here = location.pathname.slice(REPO_BASE.length) || "/";
  // 興味ありの一覧で消すのは、興味なしより強い「見たくない」（起案者の指示 2026-10-18）
  const body = {stage_id: t.dataset.stage, value: here === "/recommend/interest" ? "dismiss_strong" : "dismiss", nofill: true};
  const from = {"/recommend/reminder": "reminder", "/search": "search", "/recommend/tag": "search", "/recommend/person": "search", "/recommend/kind": "search", "/recommend/favourites": "favourites"}[here];
  if (from) body.from = from;
  if (t.closest(".rfind")) body.from = "search";
  if (t.dataset.tours !== undefined) body.siblings = t.dataset.tours.split(",").filter(Boolean);
  const onRecommend = ["/", "/recommend"].includes(here);
  const slot = onRecommend && !t.closest(".rfind") && t.classList.contains("recommend");
  const shown = slot ? [...document.querySelectorAll(".ticket.recommend")].filter(a => !a.closest(".rfind")).map(a => a.dataset.stage).filter(Boolean) : null;
  const g = t.querySelector(".btns[data-stage]") || t;
  b.disabled = true;
  const done = here === "/tickets" ? "購入済の一覧から外しました（観た記録と行く日は残ります）" : "候補から消しました";
  const d = await post("/api/react", body, g, done);
  if (!d) { b.disabled = false; return; }
  const title = ((t.querySelector("h3") || {}).textContent || "").trim();
  const note = document.createElement("p");
  note.className = "dismissed";
  note.setAttribute("role", "status");
  note.innerHTML = (title ? "「" + E(title) + "」を" : "この公演を") + E(done) + '。<span class="said"></span>';
  t.replaceWith(note);
  if (!shown) return;
  const f = await fetch(API_BASE + "/api/react", {method: "POST", credentials: "include",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({stage_id: body.stage_id, fill_only: true, shown, ...pagePrefs()})})
    .then(r => r.ok ? r.json() : null).catch(() => null);
  if (f && f.fill) applyFill(f.fill, note);
});
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest(".fixq-open");
  if (!b) return;
  const t = b.closest("article.ticket[data-stage]");
  if (t) openFixPopup(t);
});

function applyDemoRestrictions(root) {
  root.querySelectorAll(".handt").forEach(editor => {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = IS_DEMO ? "デモでは公演情報の編集はできません。"
      : "公演情報は全員で共有しているため、ここでは編集できません。誤りはカードの右下の「？」から知らせてください。";
    editor.replaceWith(note);
  });
  root.querySelectorAll("[data-hand-img], [data-hand-off]").forEach(control => {
    control.disabled = true;
    control.title = IS_DEMO ? "デモでは画像の編集はできません" : "画像は全員で共有しているため編集できません";
  });
  root.querySelectorAll("[data-sug-web], [data-lk-web]").forEach(button => {
    if (button.textContent !== WEB_BUTTON) button.textContent = WEB_BUTTON;
  });
}

// 規約の版が上がったとき、登録済みの人に同意し直してもらう（サーバーが画面の答えに terms_update を付ける。
// src/terms.js agreeAction）。同意するまで画面の上に出し続ける。読むための規約・説明へのリンクと、
// 同意しない人のためにアカウントの画面（退会・ログアウト）へのリンクを置く
function agreeAgain(version) {
  if (!version || document.querySelector(".agreepop")) return;
  const pop = document.createElement("div");
  pop.className = "agreepop";
  pop.innerHTML = '<div class="agreepop-box" role="dialog" aria-modal="true" aria-labelledby="agreepop-h">'
    + '<h2 id="agreepop-h">利用規約とプライバシーポリシーを改定しました</h2>'
    + '<p>文言を読みやすく書き直しました。権利・義務・条件・数値は変えていません。'
    + '引き続きたぐりを使うには、改定後の内容に同意してください。</p>'
    + '<p class="agreepop-links"><a href="/terms" target="_blank" rel="noopener">利用規約を読む</a>'
    + '<a href="/privacy" target="_blank" rel="noopener">プライバシーポリシーを読む</a></p>'
    + '<label class="agreepop-check"><input type="checkbox"> 改定後の利用規約とプライバシーポリシーに同意します</label>'
    + '<div class="agreepop-foot"><button type="button" class="agreepop-ok" disabled>同意して続ける</button><span class="said" role="status"></span></div>'
    + '<p class="note">同意しない場合は、<a href="/account">アカウント</a>の画面からログアウトや退会ができます。</p></div>';
  const box = pop.querySelector(".agreepop-box"), ok = pop.querySelector(".agreepop-ok");
  // **キーボードでも、この窓の中だけを動く**（#87）。開いたら窓へ焦点を移し、Tab は窓の中で回し、
  // 後ろの画面は inert で触れなくする（後から足された帯にも付ける）。閉じたら元の場所へ焦点を戻す。
  // 同意しない人も、Tab で「アカウント」のリンクまで行ける
  const prev = document.activeElement, made = new Set();
  const inertRest = () => [...document.body.children].forEach(n => {
    if (n !== pop && !n.inert) { n.inert = true; made.add(n); }
  });
  const mo = new MutationObserver(inertRest);
  const close = () => {
    mo.disconnect();
    made.forEach(n => { n.inert = false; });
    pop.remove();
    if (prev && prev.isConnected && prev.focus) prev.focus();
  };
  pop.addEventListener("keydown", ev => {
    if (ev.key !== "Tab") return;
    const f = [...box.querySelectorAll("a[href], input, button")].filter(n => !n.disabled);
    if (!f.length) return;
    const i = f.indexOf(document.activeElement);
    if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
    else if (!ev.shiftKey && (i < 0 || i === f.length - 1)) { ev.preventDefault(); f[0].focus(); }
  });
  pop.querySelector("input").addEventListener("change", ev => { ok.disabled = !ev.target.checked; });
  // アカウントの画面へ行くときは閉じる（その画面でログアウト・退会できるように。ほかの画面を開くとまた出る）
  pop.querySelector('.note a[href="/account"]').addEventListener("click", close);
  ok.addEventListener("click", async () => {
    ok.disabled = true;
    const d = await post("/api/agree", {agree: version}, box, "ありがとうございます");
    if (d) setTimeout(close, 600); else ok.disabled = false;
  });
  document.body.appendChild(pop);
  inertRest();
  mo.observe(document.body, {childList: true});
  box.tabIndex = -1;
  box.focus();
}

function renderScreen(el, activePath, d, exposureSource) {
  el.innerHTML = d.body_html;
  el.dataset.route = activePath;   // 画面ごとの見た目（日記帳のノートの形など。theme.css の [data-route]）
  if (d.terms_update) agreeAgain(d.terms_update);
  // 推薦の理由に引いていた本人の感想（「あなたの言葉」）は出さない。個人の文がそのまま画面に出るため
  // （起案者の指示 2026-10-13「あなたの言葉は個人情報すぎるので表示しないで。サービス版もデモ版も」）。
  // サーバー（render_recommend.reason_rows）も出さないようにしたが、古いサーバーの HTML にも効かせる
  decorateCards(el);
  if (activePath === "/settings") { aspectsSetting(el); creditSetting(el); }
  if (window.TaguriExposure) TaguriExposure.start(el, exposureSource || "network", async (path, body) => {
    const r = await fetch(API_BASE + path, {method: "POST", credentials: "include", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    const result = await r.json(); return r.ok && result.ok === true;
  });
  if (d.demo_mode) {
    el.insertAdjacentHTML("afterbegin", '<p class="note">操作を試せるデモです。入力した内容は、デモの再起動時にリセットされます。'
      + '記録を残して使うときは<a href="' + EDITION.demoBase + '/app/">サービス版</a>をお使いください。</p>');
  }
  if (d.public) applyDemoRestrictions(el);
  renderCrumbBar(activePath, d.title || "");
  if (Array.isArray(d.note_tags)) NOTE_TAGS = d.note_tags;
  infoFromLede(el);
  if (activePath === "/recommend" && Array.isArray(d.unrated_ends)) unratedNudge(d.unrated_ends);
  priceFilter(el);
  filterRow(el);
  fixLinks(el);
  saleLabels(el);
  updateNavActive(activePath);
  fixupSynClamp(el);
  fixupMonthScroll(el);
  fixupStoryline(el);
  fixupFigs(el);
  fixupShare(el, activePath);
  fixupImportBar(el);
  fixupPeopleNet(el);
  fixupPrefMap(el);
  fixupConquest(el);
  fixupWeightHash(el);
  bindNotes(el);
  if (live) sugWatch();
  el.querySelectorAll('img[src^="/img/"]').forEach(img => {
    img.src = API_BASE + img.getAttribute("src");
  });
}

// 札・行の見た目と押し口を整える。画面を描いたときと、一覧だけを差し替えたとき（hitPartPage）に使う
function decorateCards(el) {
  el.querySelectorAll("li.rs.q").forEach(n => n.remove());
  compactTickets(el);
  compactRows(el);
  penNotes(el);
  el.querySelectorAll(".rb").forEach(starValue);
  el.querySelectorAll(".btns,.rb[data-work]").forEach(g => pickChoice(g, savedChoice(g)));
  shortAddButtons(el);
  divergeVerdicts(el);
  reminderPrices(el);
  stampRerate(el);
  aspectsPanel(el);
}

// **「次の 5 件」は、その一覧（.hitpart）だけを取り直して差し替える**（起案者の指摘 2026-10-19「いちいち画面全部を
// 再読込する必要ある？その部分だけ読み込めないの？ロード時間が長い」）。サーバーは part= のときその一覧だけを作る
// （screens/search.js）。読めなかったときは、これまでどおり画面ごと読み直す
async function hitPartPage(box, path, search, hash) {
  const qs = stripToken(new URLSearchParams(search || "")).toString();
  const usp = new URLSearchParams(qs);
  usp.set("part", box.dataset.part);
  box.classList.add("hp-loading");
  box.setAttribute("aria-busy", "true");
  let d = null;
  try {
    const r = await fetch(API_BASE + "/api/screen/" + SCREENS[path] + "?" + usp, {credentials: "include"});
    d = r.ok ? await r.json().catch(() => null) : null;
  } catch (e) { d = null; }
  if (!box.isConnected) return;
  const tmp = document.createElement("div");
  if (d && d.ok) tmp.innerHTML = d.body_html;
  const next = tmp.querySelector(".hitpart");
  if (!next) { navigate(path, search, true, hash); return; }
  box.replaceWith(next);
  decorateCards(next);
  fixLinks(next);
  saleLabels(next);
  fixupSynClamp(next);
  bindNotes(next);
  next.querySelectorAll('img[src^="/img/"]').forEach(img => { img.src = API_BASE + img.getAttribute("src"); });
  // 料金の絞り込みを、差し替えた札にも効かせる
  const ysl = contentEl().querySelector(".yfil .ysl");
  if (ysl) ysl.dispatchEvent(new Event("input"));
  history.pushState(null, "", REPO_BASE + path + (qs ? "?" + qs : "") + (hash || ""));
  shownKey = path + "?" + qs;
  next.scrollIntoView({block: "start"});
}

// **後から押した画面が、先に押した(だが遅く返ってきた)画面に上書きされない
// ようにする。** 例: 「今週のおすすめ」の初期読み込みがまだ終わらないうちに
// 「開幕リマインド」へ移ると、開幕リマインドのfetchのほうが早く返ってきても、
// あとから解決した「今週のおすすめ」の結果でDOMが上書きされてしまっていた
// (実機の実データで確認した不具合)。**呼ぶたびに番号を進め、自分の番号が
// 最新でなくなっていたら画面には反映しない**(読み込み中の表示は消す)。
let loadSeq = 0, shownKey = null;

// **リンクの「#」の先へ移る**（#102。検索の月のカレンダーの「#cal」など）。画面を描いたあとに探す。
// 見つからなければ画面の先頭のまま（navigate で先頭へ戻してある）
function scrollToHash(hash) {
  if (!hash || hash.length < 2) return;
  let id = hash.slice(1);
  try { id = decodeURIComponent(id); } catch (e) { /* そのままの名前で探す */ }
  const t = document.getElementById(id);
  // 指された道具（<details>）は開く。足したあと読み込み直したとき（waitJob が #names などを付ける）に、
  // 開いていた枠を開いたままにするため。読み込みのときの同じ処理は、画面の中身が入る前に走るので効かない（#134）
  if (t && t.tagName === "DETAILS") t.open = true;
  if (t) t.scrollIntoView();
}

async function loadScreen(path, search, hash) {
  // 「たどる」の画面は外した（起案者の指示 2026-10-19。糸の図は人物のページへ）。前の道は、名前があればその人のページ、
  // 無ければ「眺める」へ
  if (path === "/records/trace") {
    const n = new URLSearchParams(search || "").get("name");
    const to = n ? "/recommend/person" : "/records", qs = n ? "n=" + encodeURIComponent(n) : "";
    history.replaceState(null, "", REPO_BASE + to + (qs ? "?" + qs : ""));
    return loadScreen(to, qs, "");
  }
  if (window.TaguriExposure) TaguriExposure.stop();
  const seq = ++loadSeq;
  shownKey = path + "?" + (search || "");
  const name = SCREENS[path];
  const el = contentEl();
  const stale = () => seq !== loadSeq;
  if (!name) {
    if (stale()) return;
    el.innerHTML = "<h1>見つかりません</h1><p>このページはありません。"
      + '<a href="/" data-path="/">おすすめへ戻る</a></p>';
    renderCrumbBar("/", "見つかりません");
    updateNavActive("");
    return;
  }
  if (!IMPLEMENTED.has(name)) {
    if (stale()) return;
    el.innerHTML = "<h1>この画面は準備中です</h1>"
      + "<p>GitHub Pagesへの移行で対応しているのは、Phase 0(今週のおすすめ)のみです。"
      + "現行の全画面版は <a href=\"" + API_BASE + path + "\">Renderの旧UI</a> で見られます。</p>";
    renderCrumbBar(path, "準備中");
    updateNavActive(path);
    return;
  }
  // `/` は「今週のおすすめ」と同じ画面の別入口(app.pyのpage_recommendが
  // active_sub="/recommend"を返すのと同じ扱いにする)。
  const activePath = path === "/" ? "/recommend" : path;
  const cacheKey = name + "?" + search;
  const cached = fragmentCacheGet(cacheKey);
  if (cached) {
    if (stale()) return;
    renderScreen(el, activePath, cached, "cache");
    scrollToHash(hash);
    return;
  }
  const stopLoading = startLoading(el);
  let d;
  try {
    // **index.html/404.htmlが<head>で先に飛ばしておいたfetchがあれば使い回す。**
    // CSS・app.js本体の読み込みを待たずにコールドスタートの時計を進めておく
    // ための仕掛け(起案者の指摘 ──「初期読み込みの時間もうちょっと短縮
    // できない?」)。1回使ったら消す ── 2回目のナビゲーションでは効かない。
    if (window.__prefetch && window.__prefetchKey === cacheKey) {
      const pf = window.__prefetch;
      window.__prefetch = null;
      d = await pf;
    }
    // 先に飛ばした分が読めなかったときは、もう 1 回だけ取り直す
    if (!d || !d.ok) {
      const url = API_BASE + "/api/screen/" + name + (search ? "?" + search : "");
      const r = await fetch(url, {credentials: "include"}).catch(() => null);
      if (!r) throw {status: 0};
      // サーバーが途中で止まると（処理の上限を越えたときなど）、JSON ではなく Cloudflare のエラーのページが返る。
      // そのまま JSON として読むと「SyntaxError: Unexpected token '<'」としか出ず、何が起きたか分からない（起案者の報告 2026-10-18）
      d = await r.json().catch(() => null);
      if (!r.ok || !d || !d.ok) throw {status: r.ok && d ? 500 : r.status, error: d && d.error};
    }
  } catch (e) {
    stopLoading();
    if (stale()) return;
    loadFailed(el, e, () => loadScreen(path, search, hash));
    return;
  }
  showWelcomeCode(d.welcome_code);
  fragmentCacheSet(cacheKey, d);
  stopLoading();
  if (stale()) return;
  renderScreen(el, activePath, d);
  scrollToHash(hash);
}

// **読み込めなかったわけを、使う人の言葉で言う**（#96）。通信できない・ログインの期限切れ・一時的に止めている
// （503）を分け、生の例外（SyntaxError など）は出さない。「再試行」は同じ画面（同じ条件）をもう 1 度取りに行く。
// 画面の取得は読むだけなので取り直してよい。保存（post）は、届いたか分からないときに勝手に送り直さない
const LOGIN_URL = (API_BASE || "") + "/login";   // 「http…」で始めて、SPA の切り替えに取られないようにする
function failWords(status, error) {
  if (!status) return ["通信できませんでした", "インターネットにつながっているか確かめて、もう一度試してください。"];
  if (status === 401) return ["ログインの期限が切れました", "もう一度ログインしてください。"];
  if (status === 503) return ["いまは一時的に止めています", error ? String(error) : "少し時間をおいてから、もう一度試してください。"];
  if (error) return ["うまくいきませんでした", String(error)];
  return ["サーバーの処理が途中で止まりました", "少し待ってから、もう一度試してください（" + status + "）。"];
}
function loadFailed(el, e, retry) {
  const status = e && typeof e.status === "number" ? e.status : 0;
  const [head, body] = failWords(status, e && e.error);
  el.innerHTML = "<h1>読み込めませんでした</h1><p><b>" + E(head) + "</b>。" + E(body) + "</p>"
    + '<p class="loadfail">' + (status === 401 ? '<a class="loadbtn" href="' + E(LOGIN_URL) + '">ログインし直す</a>'
      : '<button type="button" class="loadbtn" data-reload-screen>再試行</button>') + "</p>";
  const b = el.querySelector("[data-reload-screen]");
  if (b) b.addEventListener("click", retry);
}

// --- SPAルーター:内部リンク・GETフォームをその場遷移に変える ----------------
function stripToken(usp) { usp.delete("t"); return usp; }

function navigate(path, search, push, hash) {
  const usp = stripToken(new URLSearchParams(search || ""));
  const qs = usp.toString();
  const display = REPO_BASE + path + (qs ? "?" + qs : "") + (hash || "");
  if (push !== false) history.pushState(null, "", display);
  window.scrollTo(0, 0);
  loadScreen(path, qs, hash);
}

// 画面の中で描かない、サーバーの別のページ（ログイン・規約・説明・記録の保存先・カレンダーの戻り先）。
// ここへのリンクを画面の中で開くと「見つかりません」になっていた（#134 の通し検証。アカウントの画面の
// 「アカウントを削除する」「Google・メールを結び付ける」「パスキーを追加・削除する」、設定の利用規約へのリンク）
const PAGE_PATHS = /^\/(login|terms|privacy|about|migration-data|oauth)(\/|$)/;
function isInternalPath(p) {
  return p.startsWith("/") && !p.startsWith("/img/") && !p.startsWith("/vendor")
    && !p.startsWith("/api/") && !p.startsWith("/export.json") && !p.startsWith("/data.zip")
    && !PAGE_PATHS.test(p);
}

document.addEventListener("click", ev => {
  // **ふつうの左クリックで、同じタブに開くリンクだけを引き受ける**（#86）。Ctrl・⌘ で新しいタブ、Shift で新しい窓、
  // Alt で保存、中ボタン、target="_blank"・download のリンク、ほかの処理が止めた押下は、ブラウザに任せる
  if (ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
  const a = ev.target.closest && ev.target.closest("a[href]");
  if (!a) return;
  if (a.hasAttribute("data-acct-menu")) return;   // 左の帯の「アカウント」は小窓を開く（openAcctMenu）
  if (a.hasAttribute("download") || (a.getAttribute("target") || "_self").toLowerCase() !== "_self") return;
  const href = a.getAttribute("href");
  if (!href || /^[a-z]+:/i.test(href) || href.startsWith("#")) return;
  // 「#」の先は捨てずに持っていく（#102）。画面を描いたあと、その場所へ移る
  const hi = href.indexOf("#"), hash = hi >= 0 ? href.slice(hi) : "";
  let path = hi >= 0 ? href.slice(0, hi) : href, search = "";
  const qi = path.indexOf("?");
  if (qi >= 0) { search = path.slice(qi + 1); path = path.slice(0, qi); }
  if (!path || !isInternalPath(path)) return;
  ev.preventDefault();
  const part = a.classList.contains("mpage") && a.closest(".hitpart");
  if (part && SCREENS[path]) { hitPartPage(part, path, search, hash); return; }
  navigate(path, search, true, hash);
}, true);

document.addEventListener("submit", ev => {
  const f = ev.target.closest("form");
  if (!f) return;
  // 送らない入れ物（設定の画面の絞り込みなど。前は onsubmit="return false"。CSP の 'unsafe-inline' を外すため、#155）
  if (f.hasAttribute("data-nosubmit")) { ev.preventDefault(); return; }
  const method = (f.getAttribute("method") || "get").toLowerCase();
  if (method !== "get") return;
  const action = f.getAttribute("action") || location.pathname;
  if (!isInternalPath(action)) return;
  ev.preventDefault();
  // 検索の結果を出す前に、入力欄から焦点を外してスマホのキーボードを閉じる（起案者の指示 2026-10-17）。
  // ページを移らずに中身だけ差し替えるので、閉じないとキーボードが結果の上に残る
  if (document.activeElement && f.contains(document.activeElement)) document.activeElement.blur();
  const usp = new URLSearchParams(new FormData(f));
  navigate(action, usp.toString());
});

// **選んだらすぐ送る選択肢**（並べ替え。前は onchange="this.form.requestSubmit()"、#155）。送ると上の submit が受け取る
document.addEventListener("change", ev => {
  const sel = ev.target.closest && ev.target.closest("select[data-autosubmit]");
  if (sel && sel.form) sel.form.requestSubmit ? sel.form.requestSubmit() : sel.form.submit();
});
// **ポスターの読めた・読めなかった**（前は img の onload・onerror、#155）。load と error は泡立たないので、捕まえる側（true）で聞く
document.addEventListener("load", ev => {
  const img = ev.target;
  if (img && img.matches && img.matches("img[data-poster]")) img.parentElement.classList.add("ld");
}, true);
document.addEventListener("error", ev => {
  const img = ev.target;
  if (!img || !img.matches || !img.matches("img[data-poster]")) return;
  img.parentElement.classList.add("pe");
  if (img.nextElementSibling) img.nextElementSibling.textContent = "読み込めませんでした";
}, true);

window.addEventListener("popstate", () => {
  const path = (location.pathname.slice(REPO_BASE.length) || "/");
  const search = location.search.replace(/^\?/, "");
  // 「#」の先だけが変わった戻る・進むは、描き直さない（同じ画面の中で動くだけ。ブラウザが位置を戻す）
  if (path + "?" + search === shownKey) return;
  loadScreen(path, search, location.hash);
});

// **戻ってきたページを、そのまま信じない**（起案者の指摘 2026-10-14「取り消したのに、リロードせずに
// 再度未評価ページを開いたら復活していた」）。記録を取り消すとページごと読み込み直すが、そのあと
// 「戻る」で前の画面へ行くと、ブラウザは**読み込み直す前のページを保存したまま（bfcache）**見せる
// ことがある ── 取り消す前の一覧である。保存から戻ったとき（persisted）は、控えを捨てて取り直す。
window.addEventListener("pageshow", ev => {
  if (!ev.persisted || !API_BASE) return;
  fragmentCache.clear();
  const path = (location.pathname.slice(REPO_BASE.length) || "/");
  loadScreen(path, location.search.replace(/^\?/, ""), location.hash);
});
// **別のタブで書いたら、このタブの控えも捨てる。** タブごとに 45 秒の控えを持つので、
// 片方で取り消した記録が、もう片方では控えのまま出ていた
const MUTATED_KEY = "taguri-mutated";
window.addEventListener("storage", ev => { if (ev.key === MUTATED_KEY) fragmentCache.clear(); });
function markMutated() {
  fragmentCache.clear();
  try { sessionStorage.removeItem("taguri-ticker"); } catch (e) { /* 控えが無ければ何もしない */ }
  try { localStorage.setItem(MUTATED_KEY, String(Date.now())); } catch (e) { /* 使えない端末では、このタブだけ */ }
}

// **アプリ（ホーム画面に入れたとき）の service worker**（起案者 2026-10-20「アプリにしたい」、impl-pwa-base）。
// サービス版だけ（デモの GitHub Pages では入れない）。控えるのは画面の部品だけ（cloudflare/public/sw.js）
if (EDITION.edition === "service" && "serviceWorker" in navigator && location.origin === API_BASE) {
  window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => { /* 入れられなくても画面はそのまま動く */ }); });
}

document.addEventListener("DOMContentLoaded", () => {
  if (!API_BASE) {
    contentEl().innerHTML = "<h1>サービス版は準備中です</h1>"
      + '<p class="lead">記録を残して使えるサービス版は、まだ公開していません。'
      + '見本の記録で操作を試せる<a href="' + EDITION.demoBase + '/">デモ版</a>をご覧ください。</p>';
    return;
  }
  new MutationObserver(() => applyDemoRestrictions(contentEl()))
    .observe(contentEl(), {childList: true, subtree: true});
  document.querySelector(".side").insertAdjacentHTML("beforeend", renderNav() + renderPNav());
  markAcctNav(document.querySelector(".side"));
  restoreNavFold();
  const path = (location.pathname.slice(REPO_BASE.length) || "/");
  loadScreen(path, location.search.replace(/^\?/, ""), location.hash);
  if (!IS_DEMO) loadTicker();
});

// ---- 電光掲示板（起案者の指示 2026-10-15「今週開幕する公演を電車の電光掲示板みたいにメニューに流すのはどう？
// あと今週のおすすめ上位3件とな」）。画面の上に 1 行で流す。中身は /api/screen/ticker（screens/ticker.js）。
// - 10 分は sessionStorage の控えを使う（どの画面でも出すので、開くたびに取りに行かない）。記録を書いたら捨てる
// - 指・マウスを乗せる／焦点が入ると止まる。「止める」ボタンでも止まる（WCAG 2.2.2）。
//   端末で動きを減らす設定の人には流さず、横に並べて出す（CSS の prefers-reduced-motion）
// - 開幕もおすすめも無ければ、帯そのものを出さない
const TICKER_KEY = "taguri-ticker", TICKER_TTL_MS = 10 * 60 * 1000;
async function loadTicker() {
  let data = null;
  try {
    const c = JSON.parse(sessionStorage.getItem(TICKER_KEY) || "null");
    if (c && Date.now() - c.at < TICKER_TTL_MS) data = c.data;
  } catch (e) { /* 控えが読めなければ取りに行く */ }
  if (!data) {
    const r = await fetch(API_BASE + "/api/screen/ticker", {credentials: "include"}).catch(() => null);
    const d = r && r.ok ? await r.json().catch(() => null) : null;
    if (!d || !d.ticker) return;
    data = d.ticker;
    try { sessionStorage.setItem(TICKER_KEY, JSON.stringify({at: Date.now(), data})); } catch (e) { /* 控えなしで動く */ }
  }
  renderTicker(data);
}
function renderTicker(data) {
  document.querySelectorAll(".ticker").forEach(x => x.remove());
  const open = (data.open || []).map(o => '<a class="tki" href="/recommend/reminder" data-path="/recommend/reminder">'
    + '<b class="tkk open">開幕</b>' + E(o.label) + " " + E(o.title) + (o.venue ? "（" + E(o.venue) + "）" : "") + "</a>");
  const recs = (data.recs || []).map((o, i) => '<a class="tki" href="/recommend" data-path="/recommend">'
    + '<b class="tkk rec">おすすめ ' + (i + 1) + "</b>" + E(o.title) + "</a>");
  const items = open.concat(recs);
  if (!items.length) return;
  const line = items.join('<span class="tksep" aria-hidden="true">◆</span>');
  const wrap = document.createElement("div");
  wrap.className = "ticker";
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", "今週開幕する公演と、今週のおすすめ");
  // 同じ並びを 2 回続けて、半分流れたところで最初に戻すと切れ目なく回る（2 回目は読み上げない）
  wrap.innerHTML = '<button type="button" class="tkstop" aria-pressed="false" aria-label="流れを止める">'
    + '<span aria-hidden="true">❚❚</span></button>'
    + '<div class="tkview"><div class="tktrack" style="--tkdur:' + Math.max(20, items.length * 7) + 's">'
    + '<span class="tkrun">' + line + '<span class="tksep" aria-hidden="true">◆</span></span>'
    + '<span class="tkrun" aria-hidden="true">' + line.replace(/<a /g, '<a tabindex="-1" ') + '<span class="tksep">◆</span></span>'
    + "</div></div>";
  wrap.querySelector(".tkstop").addEventListener("click", ev => {
    const on = wrap.classList.toggle("paused");
    ev.currentTarget.setAttribute("aria-pressed", on ? "true" : "false");
    ev.currentTarget.setAttribute("aria-label", on ? "流れを再開する" : "流れを止める");
    ev.currentTarget.querySelector("span").textContent = on ? "▶" : "❚❚";
  });
  const main = document.querySelector(".main");
  if (main) main.insertBefore(wrap, main.querySelector(".crumbbar") || main.firstChild);
}

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

// **おすすめの 1 枚を詰める**（起案者の指示 2026-10-13「縦スクロールになりすぎないように」
// 「折りたたむとき、出演者順に５人とあらすじ（最初の１文くらい）が表示されるように」
// 「おすすめ理由は全部表示（ただし多すぎるときは折りたためるように）」・dec-recommend-compact-poster）。
// 閉じた 1 枚に出すのは ポスター・初日・公演名・団体と劇場・発売・出演 5 人・あらすじの最初の 1 文・
// おすすめ理由の全部（4 本目からは畳む）・回答の帯。会期と料金・日程・出演と作り手の全員・
// あらすじの全文と入れ口・公式サイトは「くわしく」の中へ移す。**画面の HTML は Render の
// Python が組むので、ここで組み替える**（Render を起こし直さずにデモとサービスの両方へ届く）。
const CAST_LEAD = 5, SYN_LEAD = 100;
// 「12,000円 ~ 12,000円」のように両端が同じ額の幅は「12,000円」と 1 つだけ書く（起案者の指示 2026-10-18
// 「値段帯が12000円〜12000円って同一金額になってるときは、簡潔に12000円と明記して」。screens/schedule.js sameYen と同じ）
const sameYen = line => line.replace(/([\d,]+)円\s*[~〜～\-－]\s*([\d,]+)円/g, (all, a, b) => (a.replace(/,/g, "") === b.replace(/,/g, "") ? a + "円" : all));
const PRICE_BULLET = /^(?:[・･•●○◆◇■□▪▫]|[-*]\s)\s*/;
/** 料金の欄の文から、金額の行を [券種, 金額] か [文] にして返す（screens/schedule.js priceRows と同じ決まり） */
function priceRowsOf(text) {
  const out = [];
  for (const raw of String(text || "").normalize("NFKC").split(/\n+/)) {
    // 行頭の「・」「◆」などの印は落とす（箇条書きの ◆ と重なる。起案者の指摘 2026-10-18「価格帯の展開したところ、◆があるのに
    // 重複して箇条書きの・がのこっているところがある」。screens/schedule.js priceRows と同じ）
    const line = sameYen(raw.replace(/\s+/g, " ").trim().replace(PRICE_BULLET, ""));
    if (!/円|無料/.test(line) || /発売|受付|抽選|開始|販売/.test(line)) continue;
    const m = /^【?([^:：】]{1,24})】?\s*[:：]\s*(.+)$/.exec(line);
    const r = m ? [m[1].trim(), m[2].trim()] : [line];
    if (!out.some(x => x.join("\t") === r.join("\t"))) out.push(r);
  }
  // 金額だけの行（「7,000円」、幅を 1 つの額にした「12,000円」）は、同じ額が券種つきの行（「全席指定 7,000円」）にもあれば
  // 出さない（起案者の指示 2026-10-18「『7,000円\n全席指定 7,000円』ってなってる公演があるけど『全席指定 7,000円』でよい」）。
  // 券種つきの行に無い額を含む幅（「2,750円 ~ 7,150円」で 2,750円の券が明細に無い）は残す
  const yens = r => (r.join(" ").match(/[\d,]+(?=円)/g) || []).map(a => a.replace(/,/g, ""));
  const bare = r => r.length === 1 && /^[\d,]+円(?:\s*[~〜～\-－]\s*[\d,]+円)?$/.test(r[0]);
  const named = out.filter(r => !bare(r));
  return out.filter(r => !bare(r) || !named.length || !yens(r).every(y => named.some(o => yens(o).includes(y))));
}
// 料金の欄の座席の決まり（全席指定・全席自由・指定席・自由席など）。書いてあれば必ず出す（起案者の指示 2026-10-19
// 「座席に『指定』とか『自由』が書いてあるならそれも必ず明記してほしい」）
const SEATING = /全席指定|全席自由|座席指定|日時指定|指定席|自由席|整理番号付き?自由|立見/;
/**
 * 料金の明細の形（起案者の指示 2026-10-19「折りたたむ前は『min円～max円』（min=maxならばmax円）。展開したら『S席 max円 / A席 min円』」）:
 * 閉じた 1 行は座席の決まりと金額の幅（「全席指定 6,000円〜12,000円」）、開くと券種ごとの行を高い順に。座席の決まりが券種の名前に無ければ
 * 「S席(指定)」のように添える。返すのは {open: 開いた中身の行（無ければ空）, head: 閉じた 1 行}
 */
function priceSummary(text) {
  const rows = priceRowsOf(text);
  const nums = r => (r.join(" ").match(/[\d,]+(?=円)/g) || []).map(a => Number(a.replace(/,/g, ""))).filter(n => n > 0);
  const all = rows.flatMap(nums);
  const src = String(text || "").normalize("NFKC");
  const seat = (src.match(SEATING) || [""])[0];
  const kind = /自由/.test(seat) ? "自由" : /指定/.test(seat) ? "指定" : "";
  if (!all.length) return {head: rows.length ? rows[0] : ["料金", "不明"], open: rows.slice(1)};
  const f = n => n.toLocaleString("ja-JP") + "円";
  const lo = Math.min(...all), hi = Math.max(...all);
  // 座席の決まりは金額の前（起案者の指示 2026-10-19「全席指定（または自由席） 〇円〜〇円のほうがいいな」）
  const head = [(seat ? seat + " " : "") + (lo === hi ? f(hi) : f(lo) + "〜" + f(hi))];
  const named = rows.filter(r => !(r.length === 1 && /^[\d,]+円(?:\s*[~〜～\-－]\s*[\d,]+円)?$/.test(r[0])));
  const open = named.map(r => {
    if (!kind || /指定|自由/.test(r.join(" "))) return r;
    return r.length > 1 ? [r[0] + "(" + kind + ")", r[1]] : [r[0].replace(/^(\S+?)(\s*[\d,]+円)/, "$1(" + kind + ")$2")];
  }).sort((a, b) => Math.max(0, ...nums(b)) - Math.max(0, ...nums(a)));
  // 券種が 1 つで、閉じた 1 行と同じ金額だけなら、開く中身は無い（「全席指定 7,000円」の 1 行）
  const same = open.length === 1 && nums(open[0]).every(n => n === hi) && (open[0].length === 1 || SEATING.test(open[0][0]) || !/\S/.test(open[0][0].replace(/券|一般|料金|チケット/g, "")));
  return {head, open: same ? [] : open};
}
function firstSentence(t) {
  t = (t || "").replace(/\s+/g, " ").trim();
  const m = t.match(/^.*?[。！？!?][」』）)]*/);
  let s = m ? m[0] : t;
  if (s.length > 90) s = s.slice(0, 88) + "…";
  return s.length < t.length && !s.endsWith("…") ? s + "…" : s;
}
// ---- 料金 ── 表示と絞り込み（起案者の指示 2026-10-14「金額での絞り込みもできるように」
// 「選択肢で選ぶんじゃなくて、スライダーで調節できるように」）
// 金額は券ごとの data-yen="最安-最高"（円）。絞り込みは「いちばん安い券がこの金額以下」の公演を残す
// （学生券など安い券がある公演を消さない）。料金の分からない公演は消さずに残す。選んだ上限はこの端末に覚える。
// つまみは動かしたその場で効く（画面の中の券を隠すだけで、サーバーには何も送らない）
const YEN_KEY = "taguri.yenMax";
const YEN_STEPS = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 10000, 12000, 15000, 0];   // 0 は上限なし
function yenOf(t) {
  const m = /^(\d+)-(\d+)$/.exec(t.dataset.yen || "");
  return m ? [Number(m[1]), Number(m[2])] : null;
}
function yenLabel([lo, hi]) {
  const f = n => n.toLocaleString("ja-JP");
  if (hi === 0) return "無料";
  return lo === hi ? f(lo) + "円" : (lo === 0 ? "無料" : f(lo)) + "〜" + f(hi) + "円";
}
const yenStepLabel = v => v ? v.toLocaleString("ja-JP") + "円まで" : "上限なし";
function priceFilter(el) {
  if (!el.querySelector("article.ticket[data-yen]") || el.querySelector(".yfil")) return;
  let cur = 0;
  try { cur = Number(localStorage.getItem(YEN_KEY) || 0) || 0; } catch (e) { cur = 0; }
  let idx = YEN_STEPS.indexOf(cur);
  if (idx < 0) idx = YEN_STEPS.length - 1;
  const box = document.createElement("div");
  box.className = "yfil";
  box.innerHTML = '<details class="pbox ybox"><summary>' + ico("ticket", 15) + '料金で絞り込む ── いまは<b class="ynow"></b></summary>'
    + '<p class="lead">いちばん安い券の料金がこの金額までの公演を出します。料金の分からない公演は出したままにします。</p>'
    + '<div class="yrow"><span class="wl">1 枚の料金</span>'
    + '<input class="ysl" type="range" min="0" max="' + (YEN_STEPS.length - 1) + '" step="1" value="' + idx + '" aria-label="1 枚の料金の上限">'
    + '<span class="wv yv"></span>'
    // 目盛りの言葉はつまみの真下の列だけに（起案者の指摘 2026-10-17「関係ないところまで幅広く広げすぎてる」）
    + '<span class="ysc" aria-hidden="true"><span>← ' + yenStepLabel(YEN_STEPS[0]) + '</span><span>' + yenStepLabel(0) + ' →</span></span></div>'
    + '<p class="yenn" role="status"></p></details>';
  // 料金は結果の絞り込みなので「表示の絞り込み」の段へ（起案者の指摘 2026-10-17。効かせ方・出さない語とは分ける）
  let fil = el.querySelector(".fil2.narrow") || el.querySelector(".fil2");
  if (!fil) {
    // 絞り込みの欄が無い画面（興味あり・購入済み公演など）でも、同じ「表示の絞り込み」の見出しの下に置く
    const h1 = el.querySelector("h1"); if (!h1) return;
    const lede = h1.nextElementSibling && h1.nextElementSibling.matches(".lede, .pnow, .hsub") ? h1.nextElementSibling : h1;
    const head = document.createElement("p");
    head.className = "fgh";
    head.innerHTML = ico("search", 15) + "<b>表示の絞り込み</b><span>並んでいる公演のうち、見る分だけに絞ります</span>";
    fil = document.createElement("div");
    fil.className = "fil2 narrow";
    lede.after(head, fil);
  }
  fil.appendChild(box);
  const sl = box.querySelector(".ysl");
  // **隠しているときは、一覧の場所にも言う**（#97）。上限はこの端末に覚えるので、別の画面でも効いたままになる ──
  // 畳んだ箱の中だけで言うと、全件が隠れたとき「公演が無い」としか見えない。外す押し口もここに置く
  const bar = document.createElement("p");
  bar.className = "yall";
  bar.setAttribute("role", "status");
  bar.hidden = true;
  const first = el.querySelector("article.ticket");
  (first.closest(".tickets") || first).before(bar);
  const apply = () => {
    const max = YEN_STEPS[Number(sl.value)] || 0;
    let hidden = 0, total = 0;
    el.querySelectorAll("article.ticket").forEach(t => {
      const y = yenOf(t);
      const hide = Boolean(max && y && y[0] > max);
      t.classList.toggle("yenout", hide);
      total++;
      if (hide) hidden++;
    });
    const label = yenStepLabel(max);
    box.querySelector(".yv").textContent = label;
    // 見出しは filterRow が「▶料金 … いまの値」の形に作り直すので、どちらの形でも書く
    const now = box.querySelector(".ynow") || box.querySelector("summary .fv");
    if (now) now.textContent = label;
    sl.setAttribute("aria-valuetext", label);
    box.querySelector(".yenn").textContent = hidden ? hidden + " 件を隠しています" : "";
    bar.hidden = !hidden;
    bar.innerHTML = !hidden ? "" : (hidden === total ? "<b>料金の条件（" + E(label) + "）で全件が非表示です。</b>"
      : "料金の条件（" + E(label) + "）で " + hidden + " 件を隠しています。")
      + '<button type="button" class="yclear">料金の上限を外す</button>';
    const tab = el.querySelector('.ftab[data-for="ybox"] .fv');
    if (tab) tab.textContent = yenStepLabel(max);
    const budget = el.querySelector(".rec-controls .rec-budget");
    if (budget) budget.textContent = max ? "／料金 " + label : "";
    try { localStorage.setItem(YEN_KEY, String(max)); } catch (e) { /* 覚えられなくても絞り込みは効く */ }
  };
  sl.addEventListener("input", apply);
  bar.addEventListener("click", ev => {
    if (!ev.target.closest(".yclear")) return;
    sl.value = String(YEN_STEPS.length - 1);   // いちばん右が「上限なし」
    apply();
    // 押した押し口は消えるので、焦点は料金の札（無ければ箱の見出し）へ移す
    const to = el.querySelector('.rec-controls:not([open]) > summary')
      || el.querySelector('.ftab[data-for="ybox"]') || box.querySelector("summary");
    if (to) to.focus({preventScroll: true});
  });
  apply();
}

// ---- 絞り込みを横 1 列に並べる（起案者の指示 2026-10-14「場所、効かせ方、料金などの絞り込み、横1列に3つ
// 並べてほしい」）。3 つの見出しを札として 1 行に並べ、押した 1 つだけを下に全幅で開く（ほかは閉じる）。
// 中身（都道府県の札・効かせ方のつまみ・料金のつまみ）はそれぞれの details のまま使う
// おすすめの画面は「おすすめの選び方」（効かせ方・出さない語）と「表示の絞り込み」（場所・料金）の 2 段に分かれ、
// 段ごとに札を並べる（起案者の指摘 2026-10-17「4 つを並列に並べるのはおかしい」）
// 札・箱の名前は箱ごとに決める。お気に入りの画面の 2 つ（登録した名前・出さない語）まで「場所」と
// 出ていた（起案者の指摘 2026-10-14「『お気に入り』画面の『場所』ってなに？」）
const boxName = d => d.classList.contains("wbox") ? ["効かせ方", "light"] : d.classList.contains("ybox") ? ["料金", "ticket"]
// お気に入りの名前の箱は「要素を登録」（起案者の指示 2026-10-18「『登録した名前』→『要素を登録』」）
  : d.id === "names" ? ["要素を登録", "star"] : d.id === "declined" ? ["使わない言葉", "flag"]
  : d.id === "kind-off" ? ["使わない理由", "flag"] : ["場所", "search"];
function filterRow(el) {
  el.querySelectorAll(".fil2").forEach(filterRowOf);
  // 折りたたみの見出しは、どれも「▶効かせ方」「▶場所」の形にし、いまの値・件数は右に寄せる（起案者の指示 2026-10-18
  // 「折りたたんでいるところは、全て『▶効かせ方』や『▶場所』などで表記」）。札に並べなかった 1 つだけの箱もそろえる
  el.querySelectorAll("details.pbox").forEach(d => {
    const sm = d.querySelector(":scope > summary");
    if (!sm || sm.dataset.fold) return;
    sm.dataset.fold = "1";
    const v = sm.querySelector("b")?.textContent || "";
    sm.innerHTML = '<span class="fl">' + E(boxName(d)[0]) + '</span><span class="fv">' + E(v) + "</span>";
  });
}
function filterRowOf(fil) {
  if (fil.querySelector(".ftabs")) return;
  const boxes = [...fil.querySelectorAll("details.pbox")];
  if (boxes.length < 2) return;
  const name = boxName;
  const tabs = document.createElement("div");
  tabs.className = "ftabs";
  tabs.setAttribute("role", "group");
  tabs.setAttribute("aria-label", "絞り込み");
  boxes.forEach((d, i) => {
    const key = d.classList.contains("wbox") ? "wbox" : d.classList.contains("ybox") ? "ybox" : "pbox" + i;
    d.dataset.tab = key;
    const [label] = name(d);
    const b = document.createElement("button");
    b.type = "button";
    b.className = "ftab";
    b.dataset.for = key;
    b.setAttribute("aria-expanded", d.open ? "true" : "false");
    b.innerHTML = '<span class="fl">' + label + '</span><span class="fv">'
      + E(d.querySelector("summary b")?.textContent || "") + "</span>";
    b.addEventListener("click", () => {
      const open = !d.open;
      boxes.forEach(x => { x.open = false; });
      tabs.querySelectorAll(".ftab").forEach(x => x.setAttribute("aria-expanded", "false"));
      d.open = open;
      b.setAttribute("aria-expanded", open ? "true" : "false");
    });
    tabs.appendChild(b);
  });
  tabs.style.gridTemplateColumns = "repeat(" + boxes.length + ",minmax(0,1fr))";
  fil.prepend(tabs);
  fil.classList.add("tabbed");
}

// カードに出す作り手の名前（compactTickets）。作・原作・脚本・演出はいつも出す。ほかは設定（creditSetting）で選ぶ。
// 選んだものはこの端末に覚える（観点の設定と同じ）。既定は出演だけ足す（これまでどおり出演も出る）
const CREDIT_BASE = ["作", "原作", "脚本", "演出"];
const CREDIT_OPTIONS = [["cast", "出演"], ["trans", "翻訳"], ["music", "音楽・作曲"], ["choreo", "振付"]];
const CREDIT_KEY = "taguri_credit_roles_v1";
function creditChoice() {
  try { const v = JSON.parse(localStorage.getItem(CREDIT_KEY) || "null"); if (Array.isArray(v)) return new Set(v); } catch (e) { /* 既定 */ }
  return new Set(["cast"]);
}
const creditParts = label => label.split(/[・／/、\s]+/).filter(Boolean);
function creditGroup(label) {
  const parts = creditParts(label);
  if (parts.some(p => CREDIT_BASE.includes(p))) return "base";
  if (parts.includes("出演")) return "cast";
  if (parts.includes("翻訳")) return "trans";
  if (parts.some(p => p === "音楽" || p === "作曲")) return "music";
  if (parts.includes("振付")) return "choreo";
  return "other";
}
function creditRank(x) {
  if (x.g !== "base") return 10 + CREDIT_OPTIONS.findIndex(o => o[0] === x.g);
  return Math.min(...creditParts(x.label).map(p => CREDIT_BASE.indexOf(p)).filter(i => i >= 0));
}

// 日記帳などの行の出演が 3 行を越えるときは、3 行に収まる人までを出し、残りは「ほか N 名」で開く（起案者の指示 2026-10-18
// 「日記帳ページ、出演者が3行以上になりそうなら折りたたんでほかN名表記で構わない」）。行の数は画面の幅で変わるので、出したあとに測る
const CAST_LINES = 3;
function foldCastLines(lead) {
  const p = [...lead.querySelectorAll(".lcast")].find(x => (x.querySelector(".cl")?.textContent || "").trim() === "出演");
  const lv = p && p.querySelector(".lv");
  if (!lv) return;
  const lh = parseFloat(getComputedStyle(lv).lineHeight) || 20;
  const fits = () => lv.getBoundingClientRect().height <= lh * CAST_LINES + 2;
  if (!lv.getBoundingClientRect().height || fits()) return;
  const names = lv.textContent.split("、").map(x => x.trim()).filter(Boolean);
  const tail = k => "　ほか " + (names.length - k) + " 名";
  let lo = 1, hi = names.length - 1, best = 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    lv.textContent = names.slice(0, mid).join("、") + tail(mid);
    if (fits()) { best = mid; lo = mid + 1; } else hi = mid - 1;
  }
  lv.innerHTML = E(names.slice(0, best).join("、")) + '<span class="lrest">、' + E(names.slice(best).join("、")) + "</span>"
    + '<button type="button" class="lcmore" aria-expanded="false">' + E(tail(best).trim()) + "</button>";
}
document.addEventListener("click", ev => {
  const b = ev.target.closest(".lcast .lcmore");
  if (!b) return;
  const p = b.closest(".lcast"), open = !p.classList.contains("open");
  p.classList.toggle("open", open);
  b.setAttribute("aria-expanded", String(open));
  if (!b.dataset.less) b.dataset.less = b.textContent;
  b.textContent = open ? "閉じる" : b.dataset.less;
});

// 作り手の名前の行（compactTickets・compactRows）。作・原作・脚本・演出はいつも出し、ほかは設定で選んだ役職だけ
function leadCredits(t, lead, noMore) {
    const choice = creditChoice();
    const credits = [...t.querySelectorAll(".cast .cr")].map(row => {
      const label = (row.querySelector(".cl")?.textContent || "").trim();
      return {row, label, g: creditGroup(label)};
    }).filter(x => x.g === "base" || choice.has(x.g)).sort((x, y) => creditRank(x) - creditRank(y));
    for (const {row, label, g} of credits) {
      const c = row.querySelector(".cv")?.cloneNode(true);
      if (!c) continue;
      c.querySelectorAll("button").forEach(b => b.remove());
      const p = document.createElement("p");
      p.className = "lcast";
      if (g === "cast") {
        // 出演は出演順。6 人目からは隠しておき、「くわしく」を開いたらこの行のまま続きを出す（起案者の指示 2026-10-13）
        const names = c.textContent.split("、").map(x => x.trim()).filter(Boolean);
        const lead0 = noMore ? names.length : CAST_LEAD;   // おすすめ・興味あり・お気に入りでは「ほか」で省かない
        p.innerHTML = '<span class="cl">出演</span><span class="lv">' + E(names.slice(0, lead0).join("、"))
          + (names.length > lead0 ? '<span class="lrest">、' + E(names.slice(CAST_LEAD).join("、")) + "</span>"
            + '<span class="n">　ほか ' + (names.length - CAST_LEAD) + " 名</span>" : "") + "</span>";
      } else {
        p.innerHTML = '<span class="cl">' + E(label) + '</span><span class="lv">' + E(c.textContent.trim()) + "</span>";
      }
      lead.appendChild(p);
      const cast = row.closest(".cast");
      row.remove();
      if (cast && !cast.querySelector(".cr")) cast.remove();
    }
}

// あらすじの見出し付きの行（compactTickets・compactRows）
// 書式つきのあらすじの畳み（起案者の指示 2026-10-19）: 畳んだ高さからはみ出すときだけ「続きを読む」を出し、押すと全部を開く
function richFold(p) {
  const box = p.querySelector(".lsynrich"), b = p.querySelector(".lsynrichmore");
  if (!box || !b) return;
  b.hidden = box.scrollHeight <= box.clientHeight + 2;
}
document.addEventListener("click", ev => {
  const b = ev.target.closest(".lsynrichmore");
  if (!b) return;
  const p = b.closest(".lsyn-rich"), open = !p.classList.contains("open");
  p.classList.toggle("open", open);
  b.setAttribute("aria-expanded", String(open));
  b.textContent = open ? "折りたたむ" : "続きを読む";
});
function leadSynopsis(t, lead, noMore) {
    // あらすじ: 最初の 1 文
    // 閉じていても、あらすじの最初の 1 文は必ず出す。本文の枠（.txt）が無い古い形の HTML でも、
    // 出典・タグ・押し口・入れ口を除いた残りから拾う。あらすじが無い公演（.no・.part）は出さない
    const syn = t.querySelector(".syn");
    if (syn && !syn.classList.contains("no") && !syn.classList.contains("part")) {
      let text = syn.querySelector(".txt")?.textContent || "";
      if (!text.trim()) {
        const c = syn.cloneNode(true);
        c.querySelectorAll(".tags, .src, button, form, details, label, textarea, input, .hand").forEach(n => n.remove());
        text = c.textContent;
      }
      // 管理者が書式つきで入れたあらすじ（.txt.rich。中央寄せ・書体など。起案者の指示 2026-10-19）は、文字だけにせず書式を保って出す。
      // 中身はサーバー（screens/override.js richHtml）が決まった札と class だけに絞ってある
      const rich = noMore ? syn.querySelector(".txt.rich") : null;
      if (text.trim()) {
        const p = document.createElement(rich ? "div" : "p");
        p.className = "lsyn";
        // 「出演」と同じく見出しを付ける ── 無いと出演の続きと区別が付かない（起案者の指摘 2026-10-13
        // 「どこからがあらすじの1文目なのかわかりにくい」）
        if (noMore) {
          // 100 字ほどを出し、続きは畳む（文の切れ目が 80〜120 字にあればそこで切る）
          const full = text.replace(/\s+/g, " ").trim();
          let cut = SYN_LEAD;
          const m = full.slice(80, 121).search(/[。！？!?]/);
          if (m >= 0) cut = 80 + m + 1;
          // 続きは、畳む前の最後の字のすぐ次の字から同じ段落の続きとして書く（起案者の指示 2026-10-18「続きを読むを押したときに、
          // ちゃんとたたむ前の次の文字から書かれるようにして。いま展開したら変な改行から始まってる」）。文の切れ目で切ったときに
          // 続きの頭に残る空白（元は段落の改行）は落とす
          const head = full.slice(0, cut);
          const rest = /[。！？!?」』）)]$/.test(head) ? full.slice(cut).replace(/^\s+/, "") : full.slice(cut);
          // あらすじから読み取った題材（render_recommend.syn_block の .tags .tag「#ワード」。手で入れた印の札は除く）を、
          // 開いたあらすじの下にハッシュタグで並べる（起案者の指示 2026-10-18「取得したワードをハッシュタグっぽく記載して」）。
          // 続きの無い短いあらすじは、本文のすぐ下に出す
          const words = [...new Set([...syn.querySelectorAll(".tags .tag:not(.mine)")].map(n => n.textContent.trim().replace(/^#/, "")).filter(Boolean))];
          // 押すと、その題材の付いた、これから観られる公演の一覧へ（起案者の指示 2026-10-18「あらすじのハッシュタグ押したら
          // それがついてる公演一覧が出るようにして」。src/screens/tagged.js）。デモ版（Render）にはその画面が無いので押せない札のまま
          const tag = w => IS_DEMO ? '<span class="lsyntag">#' + E(w) + "</span>"
            : '<a class="lsyntag" href="/recommend/tag?w=' + encodeURIComponent(w) + '">#' + E(w) + "</a>";
          const tags = words.length ? '<span class="lsyntags">' + words.map(tag).join("") + "</span>" : "";
          // ハッシュタグは折りたたみの外に出して、閉じていても見せる（起案者の指示 2026-10-18「あらすじのハッシュタグは常に表示。
          // あらすじの本文で長いところだけ折りたたんで」）。続きは details をやめ、同じ行の中の span を開け閉めする
          // （details の中身は段落の箱になり、開くと続きが新しい行から始まっていた）
          if (rich) {
            // 書式つき: 高さで畳み（3 行ほど）、はみ出すときだけ「続きを読む」を出す（richFold）
            p.classList.add("lsyn-rich");
            p.innerHTML = '<span class="cl">あらすじ</span><div class="lv"><div class="lsynrich">' + rich.innerHTML + "</div>"
              + '<button type="button" class="lsynrichmore" aria-expanded="false" hidden>続きを読む</button>' + tags + "</div>";
            requestAnimationFrame(() => richFold(p));
          } else
          p.innerHTML = '<span class="cl">あらすじ</span><span class="lv">' + E(head)
            + (rest ? '<span class="lsynmore"><button type="button" class="lsynopen" aria-expanded="false">続きを読む</button>'
              + '<span class="lsynrest" hidden>' + E(rest) + '<button type="button" class="lsynfold">折りたたむ</button></span></span>' : "")
            + tags + "</span>";
        } else {
          p.innerHTML = '<span class="cl">あらすじ</span><span class="lv">' + E(firstSentence(text)) + "</span>";
        }
        lead.appendChild(p);
      }
    }
}

// 評価一覧・未評価・日記帳の 1 件（.rec-row）を、おすすめのカードと同じ形にそろえる（起案者の指示 2026-10-18
// 「評価一覧や日記帳のカードもおすすめと揃えて」）。サーバーが付けた .rinfo（rowinfo.js）から、団体と会場の絵記号付きの行、
// 作り手の名前（作・原作・脚本・演出＋設定で選んだ役職）、囲んだあらすじ（100 字ほど・続きは畳む）を作る。
// ポスターの無い記録は、おすすめと同じく灰の地に白い字で「now printing...」を置く（起案者の指示 2026-10-18。前は題名と「ポスターなし」）
const NO_POSTER_TEXT = "<span>now printing...</span>";
function compactRows(root) {
  root.querySelectorAll("article.rec-row").forEach(r => {
    if (r.classList.contains("cmp")) return;
    r.classList.add("cmp");
    const np = r.querySelector(".pin > .noposter");
    if (np && !np.textContent.trim()) {
      np.innerHTML = NO_POSTER_TEXT;
    }
    const info = r.querySelector(".rinfo");
    if (!info) return;
    const {grp = "", venue = "", times = ""} = info.dataset;
    const where = r.querySelector(".where");
    const meta = document.createElement("div");
    meta.className = "where meta";
    meta.innerHTML = (grp ? '<span class="mg">' + ico("user", 13) + "<span>" + E(grp) + "</span></span>" : "")
      + (venue ? '<span class="mv">' + ico("building", 13) + "<span>" + E(venue) + "</span></span>" : "")
      + (times ? '<span class="mt">' + E(times) + "</span>" : "");
    if (meta.children.length) {
      if (where) where.replaceWith(meta); else r.querySelector(".ttl")?.after(meta);
    }
    // 公式サイトへの道はポスターの真下（おすすめのカードと同じ）。公式サイトの URL が無い公演は、情報を取った公演ページ
    const href = info.dataset.url || info.dataset.page;
    const pin = r.querySelector(".pin");
    if (href && pin && !pin.querySelector(".sitelink")) {
      const a = document.createElement("a");
      a.className = "sitelink";
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.innerHTML = ico("link", 13) + (info.dataset.url ? "公式サイト" : "公演ページ");
      pin.appendChild(a);
    }
    const lead = document.createElement("div");
    lead.className = "leadbox";
    leadCredits(info, lead, true);
    leadSynopsis(info, lead, true);
    // 作り手の行に出なかった役職（設定で選んでいないもの）は、カードと同じく出さない
    info.replaceWith(lead);
    if (!lead.children.length) lead.remove();
    else foldCastLines(lead);
  });
}

// 料金の箇条書き（起案者の指示 2026-10-18「料金の書き方を統一。箇条書きにする」）。rows: [[券種, 金額] | [文]]。
// お金の絵記号は頭に 1 つ（icon=false で、その幅だけあけてそろえる）。cloudflare/src/screens/schedule.js priceList と同じ形
function priceListHtml(rows, tail = "", icon = true) {
  const cell = r => r.length > 1 ? '<span class="lp-k">' + E(r[0]) + '</span><span class="lp-v">' + E(r[1]) + "</span>"
    : '<span class="lp-v lp-all">' + E(r[0]) + "</span>";
  return '<div class="pblock"><span class="lp-ico">' + (icon ? ico("yen", 13) : "") + '</span><ul class="plist">'
    + rows.map((r, i) => '<li class="lp-row">' + cell(r) + (i === 0 ? tail : "") + "</li>").join("") + "</ul></div>";
}

// 開幕リマインドの開いた中身の料金を、おすすめのカードと同じ形にする（起案者の指示 2026-10-20「開幕リマインドの料金の表示を、
// おすすめ画面と同じにして」）。前は料金の欄の文をそのまま日程の行の後ろに続けて書いていた。おすすめと同じく、閉じた 1 行に
// 金額の幅（座席の決まりつき）、「詳細」を開くと券種ごとの行（priceSummary・priceListHtml）を、日程のすぐ下に置き、
// 発売の札はその後ろに並べる。料金の欄が無い公演は「料金 不明」
function reminderPrices(root) {
  root.querySelectorAll(".dgdetail .dginfo").forEach(info => {
    if (info.dataset.priced) return;
    const when = info.querySelector(":scope > .when");
    if (!when) return;
    info.dataset.priced = "1";
    const priceEl = when.querySelector(".price");
    const {head, open} = priceSummary(priceEl ? sameYen(priceEl.textContent) : "");
    if (priceEl) priceEl.remove();
    const box = document.createElement(open.length ? "details" : "div");
    box.className = "lprice";
    box.innerHTML = open.length ? "<summary>" + priceListHtml([head], '<span class="lp-more">詳細</span>') + '</summary><div class="lp-body">' + priceListHtml(open, "", false) + "</div>"
      : priceListHtml([head]);
    when.after(box);
    const sale = info.querySelector(":scope > .sale");
    if (sale) box.after(sale);
  });
}

// **開幕リマインドの行の中身は、開いたときに読む**（/api/reminder_detail、screens/reminder.reminderDetails）。前は 1 週ぶん
// 全部（数百件）の中身を画面と一緒に組み、Worker が無料の CPU 10 ミリ秒を越えて「一時的に止めています」が出ていた。
// 開いた行と、同じ日に並ぶ閉じた行を合わせて 20 件までまとめて読み、入れたら料金の行を整える（reminderPrices）
document.addEventListener("toggle", async ev => {
  const d = ev.target;
  if (!d.open || !d.matches || !d.matches("details.dgopen")) return;
  const lazy = d.querySelector(".dglazy[data-detail]:not([data-loading])");
  if (!lazy) return;
  const list = d.closest(".dglist") || d;
  const boxes = [lazy, ...[...list.querySelectorAll(".dglazy[data-detail]:not([data-loading])")].filter(b => b !== lazy)].slice(0, 20);
  boxes.forEach(b => { b.dataset.loading = "1"; });
  lazy.textContent = "読み込んでいます…";
  try {
    const r = await fetch(API_BASE + "/api/reminder_detail?sids=" + boxes.map(b => encodeURIComponent(b.dataset.detail)).join(","), {credentials: "same-origin"});
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error();
    boxes.forEach(b => {
      const info = b.parentElement;
      b.outerHTML = j.html[b.dataset.detail] || "";
      if (info) reminderPrices(info.closest(".dgdetail") || info);
    });
  } catch (e) {
    boxes.forEach(b => { delete b.dataset.loading; });
    lazy.textContent = "くわしい情報を読めませんでした。閉じて、もう一度開いてください。";
  }
}, true);

function compactTickets(root) {
  // おすすめの画面の一覧のカードには「くわしく」の折りたたみを付けない（起案者の指示 2026-10-17「おすすめページには
  // 『くわしく』の折りたたみなくして」）。閉じた 1 枚に出す分（日程・出演 5 人・あらすじの 1 文・料金・公式サイト）だけにする
  const here = location.pathname.slice(REPO_BASE.length) || "/";
  const recPage = ["/", "/recommend"].includes(here);
  const interestPage = here === "/recommend/interest";   // 興味ありの一覧もおすすめと同じ表示（起案者の指示 2026-10-17）
  const favPage = here === "/recommend/favourites";       // お気に入りも同じ表示（起案者の指示 2026-10-17）
  const tagPage = here === "/recommend/tag";              // あらすじのハッシュタグの公演の一覧も同じ表示（起案者の指示 2026-10-18）
  const ticketsPage = here === "/tickets";                // 購入済の公演も同じ表示（起案者の指示 2026-10-20「購入済み画面のカードの構成、おすすめのと揃えて」）
  const searchPage = here === "/search" || here === "/recommend/person" || here === "/recommend/kind";   // 人物・形式の画面も同じ表示                  // 「探す」の公演のカードも同じ表示（起案者の指示 2026-10-19「『検索』で出てくる公演カードも他ページのレイアウトと統一して」）
  // お気に入りも同じ形にする（起案者の指示 2026-10-15「お気に入りのページのレイアウト変更して。購入済み公演と似た感じ」）
  root.querySelectorAll("article.ticket.recommend, article.ticket.interest, article.ticket.owned, article.ticket.favourite").forEach(t => {
    if (t.classList.contains("cmp")) return;
    const main = t.querySelector(".main");
    if (!main) return;
    t.classList.add("cmp");
    // 「探す」の「ヒットした箇所」は、ほかの画面の「おすすめ理由」と同じ所（回答の押し口のすぐ上）に同じ見た目で置く
    // （起案者の指示 2026-10-19「『検索』で出てくる公演カードも他ページのレイアウトと統一して」）
    if (searchPage) {
      const wt = main.querySelector(":scope > .whyh.top"), ut = main.querySelector(":scope > ul.why.top"), act = main.querySelector(":scope > .act");
      if (wt && ut && act) { act.before(wt); wt.after(ut); wt.classList.remove("top"); ut.classList.remove("top"); }
    }
    t.querySelectorAll('button[data-v="nointerest"]').forEach(b => {
      b.title = "好みではないとして、今後のおすすめに反映します";
    });
    // おすすめの画面の一覧のカード: 折りたたみを付けず、料金の明細・出演の全員・あらすじの 100 字ほどを出す
    // （起案者の指示 2026-10-17。あらすじの続きだけ畳む）
    const noMore = (recPage && t.classList.contains("recommend") && !t.closest(".rfind"))
      || (interestPage && t.classList.contains("interest"))
      || (favPage && t.classList.contains("favourite"))
      || (ticketsPage && t.classList.contains("owned"))
      || ((tagPage || searchPage) && (t.classList.contains("recommend") || t.classList.contains("interest")));
    const more = document.createElement("details");
    more.className = "more";
    more.innerHTML = "<summary><b>くわしく</b><span>会期・料金・出演の全員・あらすじの全文</span></summary>";
    const box = document.createElement("div");
    box.className = "morebody";
    more.appendChild(box);
    more.addEventListener("toggle", () => t.classList.toggle("moreopen", more.open));
    const lead = document.createElement("div");
    lead.className = "leadbox";
    // 作り手と出演の名前。作・原作・脚本・演出はどの画面でも必ず出し、ほかは設定で選んだ役職だけ出す
    // （起案者の指示 2026-10-18「全画面、最低限（詳細じゃなくてあっさり表示の場合でも）作、（原作）、脚本、演出くらいまでは
    // 名前載せて。あとは設定でどこの名前まで表示するかにしてチェックリストで選べるようにして」）。出した行は「くわしく」から外す
    leadCredits(t, lead, noMore);
    // あらすじ: 最初の 1 文
    leadSynopsis(t, lead, noMore);
    // 主催（団体）と会場は別の行に分ける。ツアーで会場が複数あるときは「ほか n 会場」を添える
    // （一覧は「くわしく」の中）（起案者の指摘 2026-10-13「タイトル、主催団体、会場の文字サイズが同じで
    // わかりにくい…主催団体と会場は改行して表示（ツアー公演で複数会場ある場合も考えて）」）
    const meta = main.querySelector(":scope > .meta");
    if (meta && !meta.querySelector(".mg, .mv")) {
      const grp = meta.querySelector(".grp")?.textContent.trim() || "";
      const v = meta.cloneNode(true);
      v.querySelectorAll(".grp, .sep").forEach(n => n.remove());
      const venue = v.textContent.trim();
      const stops = t.querySelectorAll(".tourfull .tf-row").length;
      // 団体の前に人の絵記号、会場の前に建物の絵記号（起案者の指示 2026-10-14）
      // 「ほか n 会場」は押すと、ほかの会場（会場と日付）がその下に開く（起案者の指示 2026-10-18「劇場で『ほかN会場』と
      // 表記されているとき、押したら他の会場も展開して表示されるようにしてほしい」）
      meta.innerHTML = (grp ? '<span class="mg">' + ico("user", 13) + "<span>" + E(grp) + "</span></span>" : "")
        + (venue ? '<span class="mv">' + ico("building", 13) + "<span>" + E(venue)
          + (stops > 1 ? '<button type="button" class="mt mvmore" aria-expanded="false">ほか ' + (stops - 1) + " 会場</button>" : "") + "</span></span>" : "");
      if (stops > 1) {
        const key = x => x.normalize("NFKC").replace(/\s+/g, "");
        // 本文の会場の行: 同じ名前の最初の 1 つ。名前で見つからない（カードに劇場名が無い）ときは、開いてある行（このカードの会場。
        // 県で絞っていて ★ の行があるときは決められないので除かない）
        const rows = [...t.querySelectorAll(".tourfull .tf-row")];
        const byName = rows.find(row => key((row.querySelector(".tf-loc")?.textContent || "").trim()) === key(venue));
        const me = byName || (t.querySelector(".tourfull .tf-star") ? null : rows.find(row => row.matches("details[open]")));
        const items = rows.map(row => {
          const loc = (row.querySelector(".tf-loc")?.textContent || "").trim();
          if (row === me) return "";
          // 開いた中身は会場名だけ（起案者の指示 2026-10-18「「ほかN会場」を押したら出てくるのは会場名だけでよい。背景色も不要」）
          return loc ? '<li><span class="mvl">' + E(loc) + "</span></li>" : "";
        }).filter(Boolean);
        const ul = document.createElement("ul");
        ul.className = "mvlist";
        ul.hidden = true;
        ul.innerHTML = items.join("");
        meta.querySelector(".mv")?.after(ul);
      }
    }
    const sale = main.querySelector(".sale");
    // 料金の欄の文も、両端が同じ額の幅は 1 つの額に（くわしくの中・購入済みなどの画面。起案者の指示 2026-10-18）
    const priceEl = main.querySelector(".when .price");
    if (priceEl) { const pt = sameYen(priceEl.textContent); if (pt !== priceEl.textContent) priceEl.textContent = pt; }
    // 料金の明細（おすすめの画面。値段の幅ではなく券種ごとの金額を、販売の札の下に書く。発売日などの行は除く。
    // 3 行以上は最初の 1 行だけ出して残りを畳む）（起案者の指示 2026-10-17）。会場ごとに料金が違うカードは
    // 日程の各行に表があるので、ここには出さない（data-tourprice）
    let priced = false;
    if (noMore && !t.dataset.tourprice) {
      // 料金は、どこでも同じ箇条書きの形（お金の絵記号を頭に 1 つ、券種と金額を 1 行ずつ）にする（起案者の指示 2026-10-18
      // 「料金の書き方を統一。箇条書きにする。できれば各行が改行されないように」。schedule.js priceList と同じ形）。
      // 閉じた 1 行は金額の幅、開くと券種ごとの行（priceSummary、起案者の指示 2026-10-19）
      const {head, open} = priceSummary(main.querySelector(".when .price")?.textContent || "");
      const box = document.createElement(open.length ? "details" : "div");
      box.className = "lprice";
      // 1 行目の金額のすぐ横に「▼詳細」。開いた中身は一段右へ。料金を読めない公演は「不明」（起案者の指示 2026-10-17）
      box.innerHTML = open.length ? "<summary>" + priceListHtml([head], '<span class="lp-more">詳細</span>') + '</summary><div class="lp-body">' + priceListHtml(open, "", false) + "</div>"
        : priceListHtml([head]);
      (sale || main.querySelector(".when") || main.querySelector(".meta")).after(box);
      priced = box;
    }
    // 料金（1 枚あたり）を発売の札の隣に出す（起案者の指示 2026-10-14「チケット代金も…おすすめ画面において」）。
    // 金額はサーバーが料金の欄から読んだもの（render_recommend.price_range）。読めなかった公演には出さない
    const yen = yenOf(t);
    if (yen && sale && !priced) {   // 明細を出したカードには、幅（〜円）を重ねて出さない
      // 明細を出さないカード（会場ごとに料金が違う・くわしくの付く画面）も、値段は本文の列に、明細と同じ形の 1 行で出す
      // （起案者の指示 2026-10-18「値段と発売済みが左寄りにあるときがあるから修正して」。前は発売の札の横に付け、
      // 札ごとポスターの下の列に落ちていた）。金額にはお金の絵記号（起案者の指示 2026-10-17）
      const pr = document.createElement("div");
      pr.className = "lprice lyen";
      pr.innerHTML = priceListHtml([[yenLabel(yen)]]);
      sale.before(pr);
      priced = pr;
    }
    (sale || main.querySelector(".meta")).after(lead);
    // 発売の札（発売済み など）は、値段帯（料金の明細の、畳む前に見えている行）のすぐ下に置く（起案者の指示 2026-10-18
    // 「チケット発売日のボタンは、値段帯の折りたたむ前の下に置いて」）。どのカードでも本文の列（題名・団体・会場の下）に置き、
    // ポスターの下の列には落とさない（起案者の指示 2026-10-18「値段と発売済みが左寄りにあるときがあるから修正して」。
    // 前は明細を出さないカードだけ公式サイトのボタンの下に置いていた）
    // 2026-10-18 の後の指示「発売済みなどのマークは価格帯の詳細の隣に置くようにして」: 並びは値段帯のすぐ後のまま、
    // theme.css（カードの見た目（作業 A）の塊）で値段帯と同じ行の右隣に並べる
    if (sale && priced) priced.after(sale);
    // おすすめ理由は畳まず、いつも全部出す（起案者の指示 2026-10-18「おすすめ理由は常に折りたたまず、全部表示」）
    // ツアーの日程は、閉じていても全部出す（起案者の指示 2026-10-14「おすすめ欄にはつねにツアー日程を全部書いて
    // （土地で絞り込んでたとしても）」）。出演・あらすじと同じ形で「日程」の見出しを付けて先頭に置く
    const tf = main.querySelector(".tourfull");
    if (tf) {
      const row = document.createElement("div");
      row.className = "ltour";
      row.innerHTML = '<span class="cl">日程</span>';
      row.appendChild(tf);
      lead.prepend(row);
      // おすすめの画面では、会場ごとの公演日時（暦）を初めは閉じておく（起案者の指示 2026-10-18「おすすめ画面では日程を基本的に
      // 折りたたむ。なぜなら、おすすめは内容だけで選んでほしいから（それじゃないと推薦の精度にかかわる）」）。会場と期間の行は出す
      if (recPage && t.classList.contains("recommend") && !t.closest(".rfind")) tf.querySelectorAll("details[open]").forEach(d => { d.open = false; });
    }
    // くわしく: 会期と料金・出演と作り手・あらすじ（全文と入れ口）・公式サイト
    [".when", ".cast", ".syn", ".nolink"].forEach(sel => {
      const n = main.querySelector(":scope > " + sel) || main.querySelector(sel);
      if (n && !n.closest(".leadbox")) box.appendChild(n);
    });
    // 「くわしく」の中は全部を読む場所なので、あらすじと出演者は最初から開いておく
    box.querySelectorAll(".syn, .cast").forEach(n => n.classList.add("open"));
    const site = t.querySelector(".pcol .sitebtn");
    if (site) {
      box.appendChild(site);
      // 公式サイトへの道はポスターの真下に出す（起案者の指示 2026-10-13「やっぱ公式サイトのボタンはポスターの下に」。
      // スマホもパソコンも同じ）
      const a = document.createElement("a");
      a.className = "sitelink";
      a.href = site.getAttribute("href");
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.innerHTML = ico("link", 13) + "公式サイト";
      const pc = t.querySelector(".body > .pcol");
      if (pc) pc.appendChild(a); else if (sale) sale.appendChild(a); else main.querySelector(".meta")?.after(a);
    }
    // 「くわしく」は「おすすめ理由」の上に置く（起案者の指示 2026-10-15「「くわしく」は「おすすめ理由」の上にして」）
    const act = main.querySelector(".act"), why0 = main.querySelector(":scope > .whyh:not(.top)");
    if (noMore) { /* 折りたたみを置かない */ }
    else if (why0) why0.before(more); else if (act) act.after(more); else main.appendChild(more);
    // 耳（日付の札）の代わりに、ポスターを切り取り線の左に立てる。順位はポスターの左上、
    // 日付は公演名の上に移す。ポスターの無い公演は、灰の地に白い字で「now printing...」を置く
    const stub = t.querySelector(".stub"), perf = t.querySelector(".perf");
    let pcol = t.querySelector(".body > .pcol");
    if (!pcol) { pcol = document.createElement("div"); pcol.className = "pcol"; }
    if (!pcol.querySelector(".pwrap")) {
      const np = document.createElement("div");
      np.className = "noposter";
      np.innerHTML = NO_POSTER_TEXT;
      pcol.prepend(np);
    }
    if (stub) {
      const mark = stub.querySelector(".sn, .wax");
      if (mark) { const rk = mark.cloneNode(true); rk.classList.add("rk"); pcol.prepend(rk); }
      const sd = stub.querySelector(".sd");
      // おすすめ・興味ありの一覧では、題名の上の日付は出さない（日程の欄にあるため。起案者の指示 2026-10-17）
      if (sd && !noMore) {
        const cd = document.createElement("div");
        cd.className = "cdate";
        // 期間（「10/24〜10/31」）と、上演中・終了の別。ツアーなら、どの会場の日程かを添える
        // （起案者の指示 2026-10-14。サーバーが data-range・data-state・data-tour を付ける。古い HTML は今までどおり）
        if (sd.dataset.range) {
          cd.innerHTML = "<b>" + E(sd.dataset.range) + "</b>"
            + (sd.dataset.state ? '<span class="cst">' + E(sd.dataset.state) + "</span>" : "")
            + (sd.dataset.tour ? '<span class="ctour">' + E(sd.dataset.tour) + "の日程</span>" : "");
        } else {
          cd.innerHTML = "<b>" + E(sd.querySelector("b")?.textContent || "") + "</b>" + E(sd.querySelector(".sk")?.textContent || "");
        }
        main.prepend(cd);
      }
    }
    if (perf) perf.before(pcol); else t.prepend(pcol);
    // 出演・あらすじ・理由・回答の帯・くわしくは、ポスターの下に全幅で並べる（電話の幅でも 1 行に収める）
    const foot = document.createElement("div");
    foot.className = "cfoot";
    foot.appendChild(lead);
    // 購入済み公演の「行く日」は、出演・あらすじの下に全幅で置く（おすすめと同じ並び）
    const mytix = main.querySelector(":scope > .mytix");
    if (mytix) foot.appendChild(mytix);
    let n = main.querySelector(":scope > details.more") || main.querySelector(":scope > .whyh:not(.top)") || main.querySelector(":scope > .act");
    while (n) { const nx = n.nextSibling; foot.appendChild(n); n = nx; }
    t.appendChild(foot);
    fixupSynClamp(box);
  });
}

// 作品ごとに分ける欄の 1 作品ぶん（作品名・評価・感想・出ていた人）。中身は文字として入れる（textContent・value）
function pieceRow(list, p) {
  const row = document.createElement("fieldset");
  row.className = "pc-row";
  const title = document.createElement("input");
  title.type = "text"; title.dataset.pcTitle = "1"; title.maxLength = 80; title.size = 28; title.value = p.title || "";
  title.placeholder = "作品名（例：かもめ）"; title.setAttribute("aria-label", "作品名");
  const verdict = document.createElement("select");
  verdict.dataset.pcVerdict = "1"; verdict.setAttribute("aria-label", "この作品の評価");
  for (const [v, text] of [["", "未評価"], ...(list._grades || [])]) {
    const o = document.createElement("option");
    o.value = v; o.textContent = text; o.selected = v === (p.verdict || "");
    verdict.append(o);
  }
  const del = document.createElement("button");
  del.type = "button"; del.dataset.pieceDel = "1"; del.textContent = "この作品を外す";
  const head = document.createElement("div");
  head.className = "pc-head";
  head.append(title, verdict, del);
  const note = document.createElement("textarea");
  note.dataset.pcNote = "1"; note.rows = 2; note.maxLength = 4000; note.value = p.note || "";
  note.placeholder = "この作品の感想（書かなくてもかまいません）"; note.setAttribute("aria-label", "この作品の感想");
  row.append(head, note);
  const cast = list._cast || [];
  if (cast.length) {
    const det = document.createElement("details"), sum = document.createElement("summary"), names = document.createElement("div");
    const chosen = new Set(p.cast && p.cast.length ? p.cast : cast);
    sum.textContent = "この作品に出ていた人" + (p.cast && p.cast.length ? "（" + p.cast.length + " 人）" : "（全員）");
    names.className = "pc-cast";
    for (const name of cast) {
      const lab = document.createElement("label"), cb = document.createElement("input");
      cb.type = "checkbox"; cb.checked = chosen.has(name); cb.dataset.pcCast = name;
      lab.append(cb, " " + name);
      names.append(lab);
    }
    det.append(sum, names);
    row.append(det);
  }
  return row;
}

async function post(path, body, group, done) {
  const said = group ? group.querySelector(".said") : null;
  // 押した直後に「書き込み中…」を出す。返事が来るまで何も出ないと、反映されたか不安になる
  // （起案者の指摘 2026-10-14「『記録しました。』までの文言が出る時間が長い…『書き込み中…』など表示するかにして」）
  if (said && done !== null) { said.textContent = "書き込み中…"; said.classList.add("saving"); }
  const settle = () => { if (said) said.classList.remove("saving"); };
  // 失敗は使う人の言葉で出す（#96）。届いたか分からない失敗（通信が切れた・途中で止まった）は、そう言う ──
  // 送り直しは押した人に任せ、ここでは勝手に送り直さない
  const fail = (status, error) => {
    settle();
    if (!said) return null;
    const [head, body] = failWords(status, error);
    const unknown = !status || (status >= 500 && status !== 503 && !error);
    said.textContent = "できませんでした: " + head + "。" + (unknown ? "記録できたかは確かめられていません。" : "") + body;
    if (status === 401) said.insertAdjacentHTML("beforeend", ' <a href="' + E(LOGIN_URL) + '">ログインし直す</a>');
    return null;
  };
  let r;
  try {
    r = await fetch(API_BASE + path, {method: "POST", credentials: "include",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body)});
  } catch (e) { return fail(0); }
  const d = await r.json().catch(() => null);
  if (!r.ok || !d) return fail(r.ok ? 500 : r.status, d && d.error);
  settle();
  showWelcomeCode(d.welcome_code);
  if (d.ok !== false && path !== "/api/hand_theme_refresh" && !path.startsWith("/api/recommendation/")) markMutated();
  if (said && done !== null) said.textContent = done || "記録しました";
  return d;
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

// つまみを動かしている間は画面の上だけ。一覧に効くのは確定の押し口を押してから（保存は離したとき。下の change）
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
// **つまみを離したら、その時点でアカウントに保存する**（起案者の指摘 2026-10-18「前設定した『効かせ方』が次起動したら
// 消えていた。アカウントに紐づいて設定できるようにして」── 確定の押し口を押さずに離れると残らなかった）。
// 一覧の作り直し（読み込み直し）は、これまでどおり確定の押し口で行う。書くのは動かした 1 項目だけ（D1 は 1〜2 行）
document.addEventListener("change", ev => {
  const sl = ev.target.closest && ev.target.closest(".wsl");
  if (!sl) return;
  const box = sl.closest(".wbox"), said = box.querySelector(".wsaid");
  post("/api/weight", {weights: {[sl.dataset.weight]: WSTEPS[+sl.value]}}, null, null).then(d => {
    if (said) said.textContent = d ? "保存しました。「この効かせ方でおすすめを読み込む」を押すと一覧を作り直します" : "保存できませんでした";
  });
});

// **探す画面の過去の公演の「観た」: 劇場 → その劇場の日付だけのカレンダー → 開演**（起案者の指示 2026-10-21「観た→劇場選択→
// その劇場日付しか選べないカレンダーから日付を追加→時間追加」。前は日付を先に入れ、そこから劇場を選び直していた）。
// ツアーは劇場を選ぶまで観た日を選べない。開演の時刻が分かる日（/api/stage_times）は、その時刻だけのプルダウンにする
function pastTimes(form, times) {
  const cur = form.querySelector("[name=time]");
  if (!cur) return;
  const want = times && times.length ? "SELECT" : "INPUT";
  let el = cur;
  if (cur.tagName !== want) {
    el = document.createElement(want === "SELECT" ? "select" : "input");
    el.name = "time";
    if (want === "INPUT") { el.type = "time"; el.step = "60"; }
    cur.replaceWith(el);
  }
  if (want === "SELECT") {
    const keep = cur.value;
    el.innerHTML = (times.length > 1 ? '<option value="">選んでください</option>' : "") + times.map(t => '<option value="' + E(t) + '">' + E(t) + "</option>").join("");
    if (times.includes(keep)) el.value = keep;
  }
}
function pastTimesForDate(form) {
  const d = form.querySelector("input[name=date]");
  let all = {};
  try { all = JSON.parse(form.dataset.times || "{}") || {}; } catch (e) { all = {}; }
  pastTimes(form, d && d.value ? all[d.value] || null : null);
}
async function pastLoadTimes(form, sid) {
  delete form.dataset.times;
  form.dataset.timesFor = sid || "";
  pastTimesForDate(form);
  if (!sid || IS_DEMO) return;
  try {
    const r = await fetch(API_BASE + "/api/stage_times?stage_id=" + encodeURIComponent(sid), {credentials: "include"});
    const d = r.ok ? await r.json() : {};
    if (form.dataset.timesFor !== sid) return;   // 待つ間に劇場を選び直した
    form.dataset.times = JSON.stringify(d.times || {});
    pastTimesForDate(form);
  } catch (e) { /* 分からなければ自由に入れる欄のまま */ }
}
document.addEventListener("change", ev => {
  const sel = ev.target.closest && ev.target.closest(".past-seen select[name=stage]");
  if (sel) {
    const form = sel.closest(".past-seen"), d = form.querySelector("input[name=date]"), opt = sel.selectedOptions[0];
    const said = form.closest(".pastrow").querySelector(":scope > .said");
    if (!opt || !opt.value) return;
    d.min = opt.dataset.start || ""; d.max = opt.dataset.end || opt.dataset.start || "";
    d.disabled = false;
    if (opt.dataset.start && opt.dataset.start === opt.dataset.end) d.value = opt.dataset.start;
    else if (d.value && !(d.min <= d.value && d.value <= d.max)) d.value = "";
    if (said) said.textContent = "";
    pastLoadTimes(form, opt.value);
    d.focus();
    return;
  }
  const d = ev.target.closest && ev.target.closest(".past-seen input[name=date]");
  if (d) pastTimesForDate(d.closest(".past-seen"));
});

// **前におすすめを開いた日から今日までに終わった公演があり、未評価が残っていたら知らせる**
// （起案者の指示 2026-10-14「以前開いたときから今日開くまでに終わった公演があって未評価があるときは、
// おすすめを開いた際にポップアップで『未評価が◯件あります』などで促すように」）。
// 前に開いた日はこの端末に覚える（覚えられない環境では出さないだけ）。同じ日に 2 度は出さない
const SEEN_KEY = "taguri.recommendSeen";
function unratedNudge(ends) {
  const today = new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
  let last = null;
  try { last = localStorage.getItem(SEEN_KEY); localStorage.setItem(SEEN_KEY, today); } catch (e) { return; }
  if (!last || last >= today || !ends.length) return;
  if (!ends.some(d => d > last && d <= today)) return;
  const old = document.querySelector(".nudge");
  if (old) old.remove();
  const box = document.createElement("div");
  box.className = "nudge";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-labelledby", "nudge-t");
  box.innerHTML = '<p id="nudge-t"><b>未評価が ' + ends.length + ' 件あります</b></p>'
    + '<p class="nudge-s">前に開いてから終わった公演があります。観た印象を忘れないうちに評価しませんか。</p>'
    + '<div class="nudge-b"><button type="button" class="go">評価する</button>'
    + '<button type="button" class="later">あとで</button></div>';
  const close = () => { box.remove(); document.removeEventListener("keydown", onKey); };
  const onKey = ev => { if (ev.key === "Escape") close(); };
  box.querySelector(".later").addEventListener("click", close);
  box.querySelector(".go").addEventListener("click", () => { close(); navigate("/rate/unrated", ""); });
  document.addEventListener("keydown", onKey);
  document.body.append(box);
  box.querySelector(".go").focus();
}

// ポスターを押すと、画面いっぱいに拡大して出す（起案者の指示 2026-10-17）。外側・×・Esc で閉じる。
// ポスターが出るすべての画面で（おすすめ・興味あり・お気に入り・購入済み・探す・開幕リマインド・評価・日記帳。
// 起案者の指示 2026-10-17「ポスターが出る全ページこれにして」）。読み込めた画像だけ
document.addEventListener("click", ev => {
  const img = ev.target.closest && ev.target.closest("img.poster");
  if (!img || !img.complete || !img.naturalWidth || img.closest(".pzoom")) return;
  ev.preventDefault();
  ev.stopPropagation();
  const box = document.createElement("div");
  box.className = "pzoom";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-label", "ポスターの拡大");
  const big = document.createElement("img");
  big.src = img.currentSrc || img.src;
  big.alt = (img.closest(".ticket")?.querySelector("h3")?.textContent || "") + "のポスター";
  // 「×」はポスターに重ねず、ポスターの右上の角の上に置く（起案者の指示 2026-10-17「閉じる×はポスターに被せず、
  // ポスターの右上の角の上に置いて」。その前は「画面の中の右上ではなくポスター画像の右上に」）
  const frame = document.createElement("div");
  frame.className = "pz-in";
  const close = document.createElement("button");
  close.type = "button";
  close.className = "pz-x";
  close.setAttribute("aria-label", "閉じる");
  close.textContent = "×";
  frame.append(big, close);
  box.append(frame);
  const done = () => { box.remove(); document.removeEventListener("keydown", esc); };
  const esc = e => { if (e.key === "Escape") done(); };
  box.addEventListener("click", done);
  document.addEventListener("keydown", esc);
  document.body.appendChild(box);
  close.focus();
});

// このページで絞った都道府県（URL の f=1&pref=…）。絞っていなければ空（サーバーが設定の県を使う）
function pagePrefs() {
  const usp = new URLSearchParams(location.search);
  return usp.has("f") ? {prefs: usp.getAll("pref")} : {};
}

// 回答済みカードは残し、題名と保存できた回答に縮める。展開すると元のカードで回答・理由を直せる。
// 保存に成功してから呼ぶ。理由の欄を DOM から外さないので、入力途中の文も残る。
function compactAnswered(t, value) {
  let summary = t.querySelector(":scope > .answered-summary");
  if (!summary) {
    summary = document.createElement("div");
    summary.className = "answered-summary";
    const title = t.querySelector("h3")?.textContent.trim() || "この公演";
    summary.innerHTML = '<span class="answered-title">' + E(title) + '</span>'
      + '<span class="answered-value" role="status"></span>'
      + '<button type="button" data-answer-expand="1" aria-expanded="false">回答を直す</button>';
    t.prepend(summary);
  }
  summary.querySelector(".answered-value").textContent = {interest: "興味あり", nointerest: "興味なし", owned: "購入済"}[value] || value;
  const focused = t.contains(document.activeElement);
  t.classList.add("answered-compact");
  t.classList.remove("answer-editing");
  const b = summary.querySelector("button");
  b.textContent = "回答を直す";
  b.setAttribute("aria-expanded", "false");
  if (focused) b.focus({preventScroll: true});
}
document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest("[data-answer-expand]");
  if (!b) return;
  const t = b.closest(".answered-compact");
  if (!t) return;
  const open = t.classList.toggle("answer-editing");
  b.setAttribute("aria-expanded", String(open));
  b.textContent = open ? "閉じる" : "回答を直す";
  if (open && t.querySelector('button[data-v="interest"].picked')) {
    const note = t.querySelector(".why-note");
    if (note) note.hidden = false;
  }
});

// 答えた枠を、次の候補で埋める（三択のボタンと、候補から消す ✕ の両方から使う）。fill: /api/react の fill_only の返事
function applyFill(fill, g) {
  const d = {fill};
  if (d.fill) {
    const said = g && g.querySelector(".said");
    if (d.fill.said && said) said.textContent = d.fill.said;
    if (d.fill.html) {
      const all = [...document.querySelectorAll(".ticket.recommend")].filter(a => !a.closest(".rfind"));
      const box = document.createElement("div");
      box.innerHTML = d.fill.html;
      box.querySelectorAll("li.rs.q").forEach(n => n.remove());
      compactTickets(box);
      fixLinks(box);
      const fresh = box.firstElementChild;
      // 続けて 2 枚に答えると、2 つの入れ替えが同じ候補を返すことがある。もう出ている公演（どの会場の番号でも）は足さない
      const ids = a => [a.dataset.stage, ...(a.dataset.tours || "").split(/[\s,]+/)].filter(Boolean);
      const here = new Set(all.flatMap(ids));
      const dup = fresh && ids(fresh).some(x => here.has(x));
      if (fresh && all.length && !dup) {
        fresh.classList.add("filled");
        // **押したカードのすぐ下に出す**（起案者の指示 2026-10-20「押したら新しい候補を下に出してほしい。いちいち画面全体が
        // 読み込まれるとうるさいので、その部分だけ出てくるように」）。前は一覧のいちばん下に足していたので、押した所からは
        // 見えず、押したカードが縮んで下が詰まる動きだけが目に入った。✕ で消したときは「候補から消しました」の行の下
        const at = g && (g.closest(".ticket.recommend") || (g.classList && g.classList.contains("dismissed") ? g : null));
        (at && at.isConnected && !at.closest(".rfind") ? at : all[all.length - 1]).after(fresh);
        if (window.TaguriExposure) TaguriExposure.refresh(contentEl(), "fill");
        bindNotes(fresh);          // 足した 1 枚の入力欄にも動きを付ける
        const ys = document.querySelector(".yfil .ysl");   // 料金の絞り込みを足した 1 枚にも効かせる
        if (ys) ys.dispatchEvent(new Event("input"));
      }
    }
  }
  // 入れ替える候補が尽きて、一覧の全部に答えたら「回答ありがとうございました」を出す（起案者の指示 2026-10-17。
  // 中身はサーバーが <template id="rec-thanks-t"> で置く。都道府県で絞っているときは置かない）
  if (d.fill && !d.fill.html) showThanks();
}
function showThanks() {
  const t = document.getElementById("rec-thanks-t");
  if (!t || document.getElementById("rec-thanks")) return;
  const all = [...document.querySelectorAll(".ticket.recommend")].filter(a => !a.closest(".rfind"));
  if (!all.length || !all.every(a => a.querySelector(".btns.done"))) return;
  const sec = t.content.firstElementChild.cloneNode(true);
  sec.classList.add("filled");
  all[all.length - 1].after(sec);
}

// 購入済みを押したカードの帯の下に、入った先（購入済み公演）への道を添える。カードはそのまま残す
function ownedNote(g) {
  const said = g.querySelector(".said");
  if (!said) return;
  said.textContent = "購入済みにしました。";
  const a = document.createElement("a");
  a.setAttribute("href", "/tickets");
  a.textContent = "購入済の公演を見る";
  said.append(a);
}

// 評価の段階（screens/grade.js と同じ読み方）: ◎○△× と "n/L"（L = 2 ○×・3 ○△×・5 ★・11 ★ 0.5 きざみ）。
// 表示は ○ / ★4 / ★3.5。サービス版の初期設定は星 5 段階で、設定の「評価の付け方」で選べる
const gradeParts = v => { const m = /^(\d{1,2})\/(2|3|5|11)$/.exec(v || ""); return m && +m[1] >= 1 && +m[1] <= +m[2] ? [+m[1], +m[2]] : null; };
const isGrade = v => "◎○△×".indexOf(v) >= 0 && v.length === 1 || Boolean(gradeParts(v));
const gradeText = v => {
  const p = gradeParts(v);
  if (!p) return v;
  const [n, L] = p;
  return L === 2 ? {2: "○", 1: "×"}[n] : L === 3 ? {3: "○", 2: "△", 1: "×"}[n] : "★" + (L === 11 ? (n - 1) / 2 : n);
};
const isTopGrade = v => v === "◎" || (gradeParts(v) || [0, -1])[0] === (gradeParts(v) || [0, -1])[1];
// 星を押した所まで塗る（5 段階は 1 つずつ、0.5 きざみは半分ずつ）。戻すための前の状態を返す
function fillStars(g, b) {
  const items = [...g.querySelectorAll("button.star, button.star0, .hs")];
  const was = items.map(x => x.className);
  const p = gradeParts(b.dataset.v);
  // 星の右端の ✕（評価を消す。screens/grade.js の clearButton）: 押したら星を消して ✕ を隠し、星を押したら ✕ を出す
  const clr = g.querySelector("button.gclr");
  const clrWas = clr ? clr.hidden : null;
  if (clr) clr.hidden = b === clr;
  if (b === clr) g.querySelectorAll("button.star, button.star0, .hs").forEach(x => x.classList.remove("on", "h"));
  if (p && p[1] === 5) g.querySelectorAll("button.star").forEach((x, i) => x.classList.toggle("on", i < p[0]));
  if (p && p[1] === 11) {
    const v = (p[0] - 1) / 2;
    const z = g.querySelector("button.star0");
    if (z) z.classList.toggle("on", v === 0);
    g.querySelectorAll(".hs").forEach((x, i) => { x.classList.toggle("on", v >= i + 1); x.classList.toggle("h", v === i + 0.5); });
  }
  const undo = () => { items.forEach((x, i) => { x.className = was[i]; }); if (clr) clr.hidden = clrWas; starValue(g); };
  starValue(g);
  return undo;
}
// いまの星の数を星の右に出す（起案者の指摘 2026-10-16「選んでも評価が0のまま」── 左端の「0」は
// 星 0 を選ぶ押し口で、いまの値ではない）。まだ付けていなければ何も出さない
function starValue(g) {
  if (!g.querySelector("button.star, .hs")) return;
  let v = null;
  const st = g.querySelectorAll("button.star");
  if (st.length) { const n = g.querySelectorAll("button.star.on").length; v = n ? n : null; }
  else {
    const z = g.querySelector("button.star0.on");
    const on = g.querySelectorAll(".hs.on").length, h = g.querySelector(".hs.h") ? 0.5 : 0;
    v = z ? 0 : (on + h) || null;
  }
  let out = g.querySelector(":scope > .stv");
  if (!out) {
    out = document.createElement("span");
    out.className = "stv";
    // 星のすぐ右（✕ より前）
    const last = [...g.querySelectorAll(":scope > button.star, :scope > .hs")].pop();
    last.after(out);
  }
  out.textContent = v === null ? "" : "★" + v;
}
function savedChoice(g) {
  if (g.dataset.current !== undefined) return g.dataset.current;
  const picked = g.querySelector("button[data-v].picked");
  if (picked) return picked.dataset.v;
  const stars = g.querySelectorAll("button.star.on").length;
  if (stars) return stars + "/5";
  if (g.querySelector(".star0.on")) return "1/11";
  const halves = g.querySelectorAll(".hs.on").length, half = g.querySelector(".hs.h") ? .5 : 0;
  if (halves || half) return (2 * (halves + half) + 1) + "/11";
  const stamp = g.closest(".rec-row, .wait")?.querySelector("[data-stamp]")?.textContent.trim();
  return [...g.querySelectorAll("button[data-v]")].find(b => gradeText(b.dataset.v) === stamp)?.dataset.v || "";
}
function pickChoice(g, value) {
  g.dataset.current = value || "";
  g.querySelectorAll("button[data-v]").forEach(b => {
    const picked = b.dataset.v === value;
    b.classList.toggle("picked", picked);
    b.setAttribute("aria-pressed", String(picked));
  });
}
function reactionState(g, value) {
  const t = g.closest(".ticket, .dgli");
  if (!t) return;
  if (value !== "owned") t.querySelector(".owned-mark")?.remove();
  let status = t.querySelector(".answer-state");
  if (!status) { status = document.createElement("p"); status.className = "answer-state"; status.setAttribute("role", "status"); g.after(status); }
  const label = {interest: "興味あり", nointerest: "興味なし", owned: "購入済", cantgo: "行けない"}[value];
  status.textContent = label ? label + "として保存済み。" : "回答を解除しました（未回答）。";
  const here = location.pathname.slice(REPO_BASE.length) || "/";
  if (here === "/recommend/interest" && value !== "interest") status.append(" この画面を開き直すと一覧から外れます。");
}
async function clearChoice(g) {
  if (g.dataset.saving) return;
  g.dataset.saving = "1";
  g.setAttribute("aria-busy", "true");
  const stage = g.dataset.stage, t = g.closest(".ticket");
  const body = stage ? {stage_id: stage, clear: true, siblings: (t?.dataset.tours || "").split(",").filter(Boolean)}
    : {work_key: g.dataset.work, clear: true};
  try {
    const d = await post(stage ? "/api/react" : "/api/rate", body, g, stage ? "回答を解除しました" : "未評価に戻しました");
    if (!d || d.ok === false) return;
    pickChoice(g, "");
    g.classList.remove("done");
    if (stage) {
      reactionState(g, "");
      if (t) {
        t.classList.remove("answered-compact", "answer-editing", "torn");
        t.querySelector(":scope > .answered-summary")?.remove();
      }
      document.getElementById("rec-thanks")?.remove();
    } else {
      g.querySelectorAll(".star, .star0, .hs").forEach(x => x.classList.remove("on", "h"));
      const clr = g.querySelector(".gclr"); if (clr) clr.hidden = true;
      starValue(g);
      const row = g.closest(".rec-row, .wait");
      const stamp = row?.querySelector("[data-stamp]");
      if (stamp) { stamp.textContent = "未評価"; stamp.className = "stamp hold"; stamp.setAttribute("aria-label", "評価を選び直す（いまは 未評価）"); }
      row?.classList.remove("torn");
      const asp = row?.querySelector(".asp"); if (asp) asp.hidden = true;
    }
  } finally { delete g.dataset.saving; g.removeAttribute("aria-busy"); }
}
// 星の右端の ✕: 評価を消して未評価に戻す（起案者の指示 2026-10-18「『評価しない』のボタンじゃなくて、星の右端に✕ボタンを
// つけることでnullにできるようにして」）。POST /api/rate {work_key, clear: true}。記録できなかったら星を戻す
document.addEventListener("click", ev => {
  if (!live) return;
  const b = ev.target.closest("button.gclr[data-clear]");
  if (!b) return;
  const g = b.closest(".rb[data-work]");
  if (!g) return;
  clearChoice(g);
});
document.addEventListener("click", ev => {
  if (!live) return;
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.v) {
    const g = b.closest(".btns,.rb");
    if (!g || g.dataset.saving) return;
    const current = savedChoice(g);
    // 公開デモの旧APIは公演の回答解除をまだ受け付けない。サービス版の全画面と評価で揃える。
    if (current === b.dataset.v && (!g.dataset.stage || !IS_DEMO)) { clearChoice(g); return; }
    g.dataset.saving = "1";
    g.setAttribute("aria-busy", "true");
    const path = g.dataset.stage ? "/api/react" : "/api/rate";
    const body = g.dataset.stage ? {stage_id: g.dataset.stage, value: b.dataset.v}
                                 : {work_key: g.dataset.work, verdict: b.dataset.v};
    // **答えた枠を次の候補で埋めるために、いま出している分を送る**（起案者の指示・
    // 2026-08-24 ──「三択のボタンを押したら、まだ在庫があるなら別の候補に入れ替えて
    // 表示すべきだね」）。**在庫は画面の側にしか無い** ── 何を出しているかを知って
    // いるのは画面だけなので、除く分を送らないと、いま並んでいる 1 枚がもう 1 枚増える。
    // **推薦の枠だけが対象である** ── 興味あり・お気に入りは順位で切った枠ではないので、
    // 埋める先が無い
    // **おすすめの画面の一覧だけ。** 探す画面と、おすすめ画面の「おすすめに出てこない公演を探す」の結果も
    // 同じ形のカード（.ticket.recommend）なので、形では見分けられない。そこで答えると、言葉と関係のない
    // おすすめが足されていた（起案者の指摘 2026-10-17）
    const onRecommend = ["/", "/recommend"].includes(location.pathname.slice(REPO_BASE.length) || "/");
    const slot = onRecommend && !b.closest(".rfind") ? b.closest(".ticket.recommend") : null;
    // 記録だけを先に送り、入れ替わりの 1 枚はあとで別に頼む（fill_only）。同じ要求でしていると、
    // 次の候補を選ぶ重い計算が終わるまで「記録しました」が出なかった（起案者の指摘 2026-10-14）
    const shown = slot ? [...document.querySelectorAll(".ticket.recommend")].filter(a => !a.closest(".rfind")).map(a => a.dataset.stage).filter(Boolean) : null;
    if (g.dataset.stage) {
      body.nofill = true;
      // どの画面で答えたか（興味ありの一覧で「開幕リマインドからの追加」などと出すため。起案者の指示 2026-10-15）
      const here = (location.pathname.slice(REPO_BASE.length) || "/");
      // ハッシュタグ（題材）の公演の一覧で答えたものは、探すから足したものとして扱う（screens/tagged.js）
      const from = {"/recommend/reminder": "reminder", "/search": "search", "/recommend/tag": "search", "/recommend/person": "search", "/recommend/kind": "search", "/recommend/favourites": "favourites"}[here];
      if (from) body.from = from;
      if (b.closest(".rfind")) body.from = "search";     // おすすめ画面の「出てこない公演を探す」で答えた
      const tk0 = b.closest(".ticket");
      if (tk0 && tk0.dataset.tours !== undefined) body.siblings = tk0.dataset.tours.split(",").filter(Boolean);
    }
    // **もぎれる。** 押した結果が形で分かる（記録できなかったら元に戻す）。
    // **評価待ちの行は ◎○△× を押したときに外れる**（起案者の指示・2026-08-24）──
    // 半券がもぎられるのは劇場に入るときなので、観終わった 1 枚が外れる形にする。
    // 「まだ判断できない」では外さない ── 評価し終わっていない
    const tk = b.closest(".ticket");
    const wt = b.closest(".wait");
    const row = tk || wt;
    const tear = (tk && b.dataset.v === "interest")
              || (wt && isGrade(b.dataset.v));
    if (tear) row.classList.add("torn");
    else if (tk) tk.classList.remove("torn");   // 押し直し（興味あり→興味なし など）では、もいだ印を戻す
    // 押した 1 つだけに印を付ける（色が変わって弾む・theme.css の .picked）。記録できなかったら外す
    // （起案者の指摘 2026-10-13「興味ありだけ黒いのなぜ？押したら色変わるとかなにかしらのアニメーション」）
    const previousPick = g.querySelector("button[data-v].picked");
    g.querySelectorAll("button[data-v]").forEach(x => x.classList.toggle("picked", x === b));
    // 星は押した所までを ★ にする（記録できなかったら元に戻す）
    const unfill = fillStars(g, b);
    // お気に入りの「購入済みにする」は、入った先を言う（起案者の指示 2026-10-15。お気に入りには残る）
    const said0 = tk && tk.classList.contains("favourite") && b.dataset.v === "owned" ? "購入済みにしました（購入済の公演にも入りました）" : undefined;
    post(path, body, g, said0).then(async d => {
      if (!d || d.ok === false) {
        if (tear) row.classList.remove("torn");
        g.querySelectorAll("button[data-v]").forEach(x => x.classList.toggle("picked", x === previousPick));
        unfill();
        return;
      }
      g.classList.add("done");
      pickChoice(g, b.dataset.v);
      if (g.dataset.stage) reactionState(g, b.dataset.v);
      if (slot) compactAnswered(slot, b.dataset.v);
      // 入れ替わりの 1 枚は、その 1 枚で初めて答えたときだけ足す（押し直すたびに増やさない）
      if (shown && g.dataset.stage && !slot.dataset.filled) {
        slot.dataset.filled = "1";
        const f = await fetch(API_BASE + "/api/react", {method: "POST", credentials: "include",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({stage_id: g.dataset.stage, fill_only: true, shown, ...pagePrefs()})})
          .then(r => r.ok ? r.json() : null).catch(() => null);
        if (f && f.fill) d.fill = f.fill;
      }
      // **押した評価を、その場で余白に押す**（起案者の指示 ──「一個操作したら適宜
      // リロードしてほしい」の趣旨。ここは読み込み直さずに済む）。**判子が出ないと、
      // 押したのに何も起きていないように見える** ── 以前は評価の字が出るのは次に
      // 開いたときだった。**感想の欄も同時に開く** ── 観た帰りに ◎ を押す瞬間が、
      // いちばん言葉の出てくる瞬間である（焦点を移すのは ◎ のときだけ）
      const rr = b.closest(".rec-row");
      if (rr && rr.querySelector("[data-stamp]")) {
        const st = rr.querySelector("[data-stamp]");
        st.className = "stamp" + (!isGrade(b.dataset.v) ? " hold" : gradeText(b.dataset.v).length > 2 ? " sm" : "");
        st.textContent = gradeText(b.dataset.v);
        st.removeAttribute("aria-label");
        const box = rr.querySelector(".inote");
        if (box && !rr.querySelector(".inr")) {
          box.hidden = false;
          if (isTopGrade(b.dataset.v)) box.querySelector("textarea").focus();
        }
      }
      if (tk && !slot && b.dataset.v === "interest") {
        const wn = tk.querySelector(".why-note");
        if (wn) { wn.hidden = false; wn.querySelector("textarea").focus(); }
      }
      // **評価を押した直後に、感想の欄を開く。** 観た帰りに ◎ を押す瞬間が、いちばん
      // 言葉が出てくる瞬間である。**焦点を移すのは ◎ のときだけ** ── 引用が返るのは
      // ◎ の作品だけなので、× や △ で書くよう促すと返りの無い入力になる
      const wn2 = g.parentElement && g.parentElement.querySelector(".wnote");
      if (wn2) {
        wn2.hidden = false;
        if (isTopGrade(b.dataset.v)) wn2.querySelector("textarea").focus();
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
      applyFill(d.fill, g);
      // **「すでに持っている」を押した 1 枚は、この一覧から外して「購入済み公演」へ送る**
      // （起案者の指示 2026-10-14「押したら、持ってる公演のところだけに表示されて」）。
      // 外したあとに 1 行だけ残し、行き先へ飛べるようにする（どこへ行ったか分からなくしない）
      // 2026-10-18 から: 押したカードは消さずにそのまま置き、入った先だけ添える（起案者の指示「対象全ページに対して、
      // 購入済押しても、勝手に消さないで。そのままカード表示していて」）。以前は一覧から外して 1 行だけ残していた
      if (b.dataset.v === "owned" && tk && !tk.classList.contains("owned") && !tk.classList.contains("favourite")) ownedNote(g);
      // **見送った理由は出すだけで、開かない。** 書く頻度が低い入力なので、
      // 焦点まで移すと「書かないと進めない」ように見える
      if (b.dataset.v === "nointerest") {
        const row = b.closest(".ticket, .fav");
        const nn = row && row.querySelector(".nn");
        if (nn) nn.hidden = false;
      }
    }).finally(() => { delete g.dataset.saving; g.removeAttribute("aria-busy"); });
  } else if (b.dataset.fav === "add") {
    const g = b.closest(".fav-add"), i = g.querySelector("#fav-name");
    if (!i.value.trim()) return;
    // 人を選んだときだけ、任意の「役職で絞る」の札も送る（起案者の指示 2026-10-18、q-favourite-homonym）
    const kind = g.querySelector("#fav-kind").value;
    const boxes = [...g.querySelectorAll(".fav-roles input:checked")];
    post("/api/favourite", {action: "add", kind,
      name: i.value.trim(), ...(kind === "人" && boxes.length ? {roles: boxes.map(x => x.value)} : {})}, g, "登録しました")
      .then(d => { if (d) { i.value = ""; boxes.forEach(x => { x.checked = false; }); waitJob(g, true); } });
  } else if (b.dataset.fav === "promote") {
    const r = b.closest(".prom");
    post("/api/favourite", {action: "add", kind: b.dataset.kind, name: b.dataset.name}, r,
      "登録しました（この名前の公演は、件数の制限なしに新着に出ます）")
      .then(d => { if (d) { r.classList.add("done"); b.disabled = true; waitJob(r, true); } });
  } else if (b.dataset.fav === "remove") {
    const t = b.closest(".tag");
    post("/api/favourite", {action: "remove", kind: t.dataset.kind, name: t.dataset.name},
      t.parentElement).then(d => { if (d) { t.remove(); waitJob(t.parentElement, true); } });
  } else if (b.dataset.searchRequest) {
    const g = b.closest(".webq, .sug-head") || b.parentElement;
    post("/api/search_request", {q: b.dataset.searchRequest, source: b.dataset.source || "search"},
      g, null).then(d => {
        if (!d) return;
        b.disabled = true;
        const said = g.querySelector(".said");
        if (said) said.textContent = d.message || "頼みました";
      });
  } else if (b.dataset.dec === "add") {
    // **出さない語を確定する。** 候補の札から押す道と、自分で打つ道の 2 つがある
    const r = b.closest(".prom"), box = b.closest(".pbox");
    const w = b.dataset.word || (box.querySelector("#dec-word") || {}).value || "";
    if (!w.trim()) return;
    const kind = b.dataset.word ? "" : ((box && box.querySelector("#dec-kind")) || {}).value || "";
    post("/api/decline", {action: "add", word: w.trim(), kind}, r || b.parentElement,
      "出さないことにしました")
      .then(d => { if (d) { if (r) { r.classList.add("done"); b.disabled = true; }
                            waitJob(r || b.parentElement, true); } });
  } else if (b.dataset.kindoffRemove) {
    const t = b.closest(".tag");
    post("/api/kind_off", {action: "remove", key: t.dataset.kindkey}, t.parentElement, "戻しました")
      .then(d => { if (d) { t.remove(); waitJob(null, true); } });
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
    // 種類の理由（原作「オリジナル」など）は語として外すと公演ごと消えるので、
    // 「この理由を使わない」として別に控える（起案者の指示 2026-10-16、q-kind-reason-off）
    const req = b.dataset.kindoff
      ? post("/api/kind_off", {action: "add", key: b.dataset.kindoff}, null, null)
      : b.dataset.kind
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
    post("/api/missed", {title: i.value.trim(), ...(i.dataset.stage ? {stage_id: i.dataset.stage} : {})}, g,
         "登録しました。出演者とあらすじを調べています…")
      .then(d => { if (d) { i.value = ""; delete i.dataset.stage; g.querySelector(".miss-sug")?.replaceChildren(); waitJob(g, true); } });
  } else if (b.dataset.past) {
    // **探す画面の過去の公演**（起案者の指示 2026-10-17「ボタン 2 つで入れて」「観たならば、日時を入れて
    // 観劇記録に追加できるようにして」）。観た＝観た日（と開演）を入れる欄を開き、追加でその公演に結び付ける。
    // 観ればよかった＝見逃した公演の一覧へ。押した行はそのまま残し、結果を書く
    const li = b.closest(".pastrow"), said = li.querySelector(":scope > .said");
    const form = li.querySelector(".past-seen");
    const body = {title: li.dataset.title, stage_id: li.dataset.stage};
    if (b.dataset.past === "seen") {
      form.hidden = !form.hidden;
      b.classList.toggle("picked", !form.hidden);
      // ツアーは劇場から、1 会場の公演は観た日から（劇場の時刻はそのときに読む）
      const sel0 = form.querySelector("select[name=stage]");
      if (!form.hidden && !sel0 && form.dataset.stage && form.dataset.timesFor !== form.dataset.stage) pastLoadTimes(form, form.dataset.stage);
      if (!form.hidden) (sel0 && !sel0.value ? sel0 : form.querySelector("input[name=date]")).focus();
    } else if (b.dataset.past === "seen-save") {
      const d = form.querySelector("input[name=date]"), t = form.querySelector("[name=time]");
      const sel = form.querySelector("select[name=stage]"), opt = sel && sel.selectedOptions[0];
      if (sel && !sel.value) { if (said) said.textContent = "先に劇場を選んでください"; sel.focus(); return; }
      if (!d.value) { if (said) said.textContent = "観た日を入れてください"; d.focus(); return; }
      if (!d.checkValidity()) { if (said) said.textContent = "観た日は上演期間の中から選んでください"; d.focus(); return; }
      const prev = li.querySelector(".past-done");
      if (prev && !t.value && (prev.dataset.days || "").split(",").includes(d.value)) {
        if (said) said.textContent = "その日はもう追加しました。同じ日にもう一度観たときは、開演の時刻も入れてください"; t.focus(); return;
      }
      // ツアーは選んだ劇場の公演に結び付ける
      if (opt) {
        if (!(opt.dataset.start <= d.value && d.value <= opt.dataset.end)) {
          // どの劇場の期間にも入らない日（ツアーの合間）なら、日を入れたときと同じ言い方にする（#134 の通しで食い違っていた）
          const anyLeg = [...sel.options].some(o => o.dataset.start <= d.value && d.value <= o.dataset.end);
          if (said) said.textContent = anyLeg ? `${opt.dataset.venue || "選んだ劇場"}はその日に上演していません。劇場か観た日を選び直してください`
            : "その日はどの劇場でも上演していません。観た日を確かめてください";
          (anyLeg ? sel : d).focus(); return;
        }
        body.stage_id = opt.value; body.venue = opt.dataset.venue || "";
      }
      // **同じ公演を続けて何回でも足せる**（起案者の指摘 2026-10-18「連続で何回も同じ公演を追加したい場合に対処して」）。
      // 足したあとも欄は開いたまま、日付と時刻だけ空にする。足した回は行の下に並べる。同じ日の昼・夜は開演の時刻で分ける（サーバー）
      // 足した回の一覧には劇場も添える（ツアーのどの劇場の回か分かるように。起案者の問い 2026-10-21）
      const when = `${+d.value.slice(5, 7)}/${+d.value.slice(8, 10)}${t.value ? " " + t.value : ""}${opt && opt.dataset.venue ? " " + opt.dataset.venue : ""}`;
      post("/api/add_work", {...body, date: d.value, time: t.value || ""}, li, `${when} を観劇記録に追加しました。続けて別の回も追加できます`)
        .then(r => {
          if (!r) return;
          let done = li.querySelector(".past-done");
          if (!done) { done = document.createElement("p"); done.className = "past-done"; form.after(done); }
          done.dataset.n = String(+(done.dataset.n || 0) + 1);
          done.dataset.list = (done.dataset.list ? done.dataset.list + "、" : "") + when;
          done.dataset.days = (done.dataset.days ? done.dataset.days + "," : "") + d.value;
          done.textContent = `追加した回（${done.dataset.n}）: ${done.dataset.list}`;
          // 劇場は選んだまま、日付と時刻だけ空にする（同じ劇場の別の回を続けて足せる）
          d.value = ""; t.value = ""; pastTimesForDate(form); d.focus();
          const seen = li.querySelector("[data-past=seen]");
          seen.textContent = "観た（もう 1 回追加）";
        });
    } else {
      post("/api/missed", body, li, "行けばよかったに入れました")
        .then(r => { if (r) { b.disabled = true; b.textContent = "行けばよかったに入っています"; } });
    }
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
    if (!t.value.trim()) {
      g.querySelector(".said").textContent = "公演の題名を入れてください。";
      t.focus();
      return;
    }
    const title = t.value.trim(), date = dt.value;
    const repeat = !!g.dataset.registerSingle;
    const savedTime = g.querySelector('#w-time').value;
    b.disabled = true;
    post("/api/add_work", {title: t.value.trim(), date: dt.value,
      venue: g.querySelector("#w-venue").value,
      time: g.querySelector("#w-time").value,
      stage_id: g.querySelector("#w-stage").value, repeat}, g, "登録しました（評価待ちに並びます）")
      .then(d => {
        if (!d) return;
        clearTimeout(sugTimer); ++sugSeq;
        if (!repeat) { t.value = ""; g.querySelector("#w-stage").value = ""; runDates(dt, "", ""); }
        else if (d.stage_id) g.querySelector("#w-stage").value = d.stage_id;
        // 観た日から別の劇場の公演に結び付け直したときは、劇場の欄もその劇場にする（起案者の問い 2026-10-21。rate.addWorkAction の venue）
        if (repeat && typeof d.venue === "string") g.querySelector("#w-venue").value = d.venue;
        document.getElementById("sug").replaceChildren();
        // これからの公演は購入済に入った（rate.addWorkAction の owned。起案者の指示 2026-10-24）
        if (d.owned && g.dataset.registerSingle) {
          const result = g.parentElement.querySelector("[data-register-result]");
          const message = document.createElement("p");
          message.textContent = "「" + title + "」" + (date ? "（" + date + (savedTime ? " " + savedTime : "") + "）" : "")
            + "を購入済の公演に追加しました。" + (date ? "行く日を過ぎると、評価待ちに移ります。" : "行く日は、購入済の公演の画面から入れられます。");
          const link = document.createElement("a");
          link.href = "/tickets";
          link.textContent = "購入済の公演を見る";
          result.replaceChildren(message, link);
          result.hidden = false;
          g.querySelector(".said").textContent = "購入済に追加しました。";
          dt.focus();
          return;
        }
        if (g.dataset.registerSingle) {
          const result = g.parentElement.querySelector("[data-register-result]");
          const message = document.createElement("p");
          message.textContent = "「" + title + "」" + (date ? "（" + date + (savedTime ? " " + savedTime : "") + "）" : "")
            + "を保存しました。公演日時を変えて保存すると、次の回を追加できます。";
          const link = document.createElement("a");
          const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
          link.href = date && date <= today ? "/rate/unrated" : "/records/works";
          link.textContent = date && date <= today ? "続けて評価する" : "保存した記録を確認する";
          result.replaceChildren(message, link);
          result.hidden = false;
          g.querySelector(".said").textContent = "保存しました。";
          dt.focus();
          g.parentElement.querySelectorAll('.mergeq').forEach(el => el.remove());
          askMerge(g.parentElement, d.work_key, d.similar);
          // Worker saves synchronously. Keep the result and next action visible.
          return;
        }
        if (askMerge(g.parentElement, d.work_key, d.similar)) return;
        // **材料を取り終えてから作り直す。** すぐ読み込み直すと、取りに行っている
        // 最中の画面（ポスターの無い行）が出て、押した結果が見えない
        waitJob(g, true);
      }).finally(() => { b.disabled = false; });
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
  } else if (b.dataset.registerSearch) {
    registerSearchDialog(b);
  } else if (b.dataset.pick && b.closest(".miss-add")) {
    // 行けばよかったの題名の欄の候補を選んだら、題名を欄に入れ、その公演を指して足す（同じ題名の別の公演に取り違えない）
    const g = b.closest(".miss-add"), r = b.closest(".sug-row"), i = g.querySelector("#miss-title");
    clearTimeout(missTimer); ++missSeq;
    i.value = r.dataset.title;
    i.dataset.stage = r.dataset.stage || "";
    g.querySelector(".miss-sug")?.replaceChildren();
    i.focus();
  } else if (b.dataset.pick) {
    // **候補を選んだら、そのまま欄に入れる。** 打ち直させない
    const r = b.closest(".sug-row"), g = document.querySelector(".add-work");
    clearTimeout(sugTimer); ++sugSeq;
    g.querySelector("#w-title").value = r.dataset.title;
    g.querySelector("#w-date").value = r.dataset.date || "";
    runDates(g.querySelector("#w-date"), r.dataset.start, r.dataset.end);
    loadStageTimes(r.dataset.stage || "");
    g.querySelector("#w-venue").value = r.dataset.venue || "";
    g.querySelector("#w-stage").value = r.dataset.stage || "";
    document.getElementById("sug").replaceChildren();
    g.querySelector(".said").textContent = "候補から入れました。内容を確かめて登録してください";
    const dialog = r.closest('dialog.register-search-dialog');
    if (dialog) { dialog.dataset.picked = '1'; dialog.close(); }
  } else if (b.dataset.merge) {
    const g = b.closest(".mergeq");
    post("/api/merge_work", {work_key: b.dataset.mergeWork, other: b.dataset.merge}, g,
      null).then(d => {
      if (!d) return;
      g.querySelector(".said").textContent =
        "「" + d.kept_title + "」にまとめました"
        + (d.moved.length ? "（" + d.moved.join("と") + "も移しました）" : "")
        + "。画面を読み込み直します";
      setTimeout(() => location.reload(), 1400);
    });
  } else if (b.dataset.mergeNo) {
    const g = b.closest(".mergeq");
    g.querySelector(".said").textContent = "別の公演として、そのままにします";
    g.querySelectorAll("button").forEach(x => x.disabled = true);
    setTimeout(() => location.reload(), 1200);
  } else if (b.dataset.unmergeOne) {
    // まとめた記録の 1 回だけを別の記録に分ける（起案者の問い 2026-10-21。row.js visitsHtml）
    const g = b.closest("details.visits") || b.parentElement;
    b.disabled = true;
    post("/api/merge_work", {work_key: b.dataset.unmergeOne, one: b.dataset.one, unmerge: true}, g,
      "この回を別の記録に分けました。画面を読み込み直します")
      .then(d => { if (d) setTimeout(() => location.reload(), 1000); else b.disabled = false; });
  } else if (b.dataset.unmerge) {
    const g = b.closest(".ed-btns") || b.parentElement;
    post("/api/merge_work", {work_key: b.dataset.unmerge, unmerge: true}, g,
      "まとめた回をすべて別の記録に分けました。画面を読み込み直します")
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
      if (!d) { if (said) said.textContent = "できませんでした"; return; }
      box.classList.remove("dirty");
      if (said) said.textContent = "この効かせ方で読み込み直します…";
      // **押した直後だけは開いたまま戻る。** 「推薦に出なくなった公演が N 件」の
      // 知らせはこの欄の中にあるので、畳んで戻すと押した結果が見えない
      location.hash = "weights";
      setTimeout(() => location.reload(), 500);
    });
  } else if (b.dataset.wreset) {
    const box = b.closest(".wbox"), w = {};
    // 「すべて初めの設定に戻す」: 群ごとの既定（つまみの data-default、起案者の指示 2026-10-18）
    box.querySelectorAll(".wsl").forEach(sl => { w[sl.dataset.weight] = sl.dataset.default || "mid"; });
    post("/api/weight", {weights: w}, null, null).then(d => {
      if (!d) return;
      location.hash = "weights";
      setTimeout(() => location.reload(), 400);
    });
  } else if (b.dataset.setScale) {
    // 評価の付け方（設定）。選んだ形を 1 回だけ書き、次に開いた画面から効く
    const card = b.closest("#scale-setting"), on = card.querySelector('input[name="rscale"]:checked');
    if (!on) return;
    post("/api/rating_scale", {scale: on.value}, card, "保存しました。次に評価するときから、この形で出ます").then(d => {
      if (d) setTimeout(() => location.reload(), 700);
    });
  } else if (b.dataset.setAnalysis) {
    // 推薦の改善の分析から外れる（設定）。押したときに 1 回だけ書く
    const card = b.closest("#analysis-setting"), on = card.querySelector('input[name="analysis"]:checked');
    if (!on) return;
    post("/api/analysis_optout", {off: on.value === "1"}, card,
      on.value === "1" ? "保存しました。分析から外します" : "保存しました").then(d => {
      if (d) setTimeout(() => location.reload(), 700);
    });
  } else if (b.dataset.setNoteAi) {
    // 感想の AI 読み取りへの同意（設定、note-ai.js）。押したときに 1 回だけ書く
    const card = b.closest("#note-ai-setting"), on = card.querySelector('input[name="note_ai"]:checked');
    if (!on) return;
    post("/api/note_ai", {on: on.value === "1"}, card,
      on.value === "1" ? "保存しました。今夜から感想を読み取ります" : "保存しました。感想を AI に送りません").then(d => {
      if (d) setTimeout(() => location.reload(), 700);
    });
  } else if (b.dataset.setPref || b.dataset.setPrefAll) {
    // **設定は「押したときに 1 回だけ書く」**（効かせ方と同じ規約）。チェックの
    // 並びは `.pfil` の form が持っているので、そこから読む ── 別の場所に状態を
    // 二重に持たない
    const card = b.closest("#pref-setting");
    const prefs = b.dataset.setPrefAll ? [] :
      [...card.querySelectorAll('input[name="pref"]:checked')].map(i => i.value);
    post("/api/pref_setting", {prefs}, card,
      "保存しました。次に開いたときから反映されます").then(d => {
      if (d) setTimeout(() => location.reload(), 700);
    });
  } else if (b.dataset.linkCreate) {
    // **「この端末を追加」用の一時コードを発行する**（利用者ごとのデータ分離・E3）。
    // `auth.create_link_code`はすでに実装済みだったが、呼び出すUIがどこにも
    // 無かった(`_account_card_html`参照)。10分で失効・1回限り
    const box = b.closest(".link-add").querySelector(".link-out");
    b.disabled = true;
    post("/api/link/create", {}, null, null).then(d => {
      b.disabled = false;
      if (!d) { box.hidden = false; box.textContent = "発行できませんでした"; return; }
      box.hidden = false;
      box.innerHTML = '<p class="lead">別の端末で <code>' + E(API_BASE) + '/link</code> '
        + 'を開き、この6桁を10分以内に入力してください。</p>'
        + '<code class="tg-welcome-code">' + E(d.code) + '</code>';
    });
  } else if (b.dataset.unseen) {
    // **押したら一覧から外れる**（起案者の指示・2026-08-24）。評価待ちを開くたびに
    // 作り直すようにしたので、読み込み直せば実際に消える。**書く欄は開かない操作なので、
    // ここで読み込み直しても入力が消えることはない**
    const g = b.closest(".ns-body") || b.parentElement;
    post("/api/unseen", {work_key: b.dataset.unseen, unseen: true}, g,
      "「行かなかった」と記録しました。一覧から外します")
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
      "観た公演に戻しました。画面を読み込み直します")
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
      "取り消しました。「取り消した記録」から戻せます")
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
      "手で入れたポスターを外しました。画面を読み込み直します")
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
      "結び付けました。公演の情報を取得しています")
      .then(d => { if (d) waitJob(g, true); });
  } else if (b.dataset.castOpen) {
    // **観た回の出演者**（起案者の指示 2026-10-15「Wキャストの出演者を選べるようにして」）。押したときに
    // 公演の出演者を読み、観た回に出ていた人にチェックを付けて並べる。外した人はおすすめの材料にしない
    const g = b.closest(".ed-cast"), list = g.querySelector(".ed-castl");
    post("/api/cast_seen", {work_key: b.dataset.castOpen}, g, null).then(d => {
      if (!d) return;
      list.textContent = "";
      if (!d.cast.length) { list.textContent = "この公演の出演者はまだ手元にありません。"; return; }
      const off = new Set(d.off);
      for (const name of d.cast) {
        const lab = document.createElement("label"), cb = document.createElement("input");
        cb.type = "checkbox"; cb.checked = !off.has(name); cb.dataset.castName = name;
        lab.append(cb, " " + name);
        list.append(lab);
      }
      const save = document.createElement("button");
      save.dataset.castSave = b.dataset.castOpen;
      save.textContent = "観た回の出演者を保存する";
      const row = document.createElement("div");
      row.className = "ed-btns";
      row.append(save);
      list.append(row);
      b.hidden = true;
    });
  } else if (b.dataset.castSave) {
    const g = b.closest(".ed-cast");
    const off = [...g.querySelectorAll("input[data-cast-name]")].filter(c => !c.checked).map(c => c.dataset.castName);
    post("/api/cast_seen", {work_key: b.dataset.castSave, off}, g, off.length
      ? `${off.length} 人を「観た回に出ていなかった」にしました` : "全員を「観た回に出ていた」にしました");
  } else if (b.dataset.piecesOpen) {
    // **作品ごとに分ける**（起案者の指示 2026-10-19、dec-split-pieces）。押したときに中身・出演者・評価の選択肢を読み、
    // 作品ごとに作品名・評価・感想・出ていた人の欄を並べる。記録は 1 件のまま、推薦は作品ごとの評価を使う
    const g = b.closest(".ed-pieces"), list = g.querySelector(".ed-piecel");
    post("/api/pieces", {work_key: b.dataset.piecesOpen}, g, null).then(d => {
      if (!d) return;
      list.textContent = "";
      list.dataset.work = d.work_key;
      list.dataset.max = d.max;
      list._cast = d.cast; list._grades = d.grades;
      const rows = d.pieces.length ? d.pieces : [{title: "", verdict: "", note: "", cast: []}, {title: "", verdict: "", note: "", cast: []}];
      const box = document.createElement("div");
      box.className = "pc-rows";
      for (const p of rows) box.append(pieceRow(list, p));
      list.append(box);
      const btns = document.createElement("div");
      btns.className = "ed-btns";
      const add = document.createElement("button"), save = document.createElement("button");
      add.dataset.pieceAdd = "1"; add.textContent = "作品を足す";
      save.dataset.piecesSave = "1"; save.textContent = "作品ごとの評価・感想を保存する";
      btns.append(add, save);
      if (d.pieces.length) {
        const stop = document.createElement("button");
        stop.dataset.piecesStop = "1"; stop.textContent = "分けるのをやめる";
        btns.append(stop);
      }
      list.append(btns);
      b.hidden = true;
    });
  } else if (b.dataset.pieceAdd) {
    const list = b.closest(".ed-piecel"), box = list.querySelector(".pc-rows");
    if (box.children.length >= Number(list.dataset.max || 20)) { b.closest(".ed-pieces").querySelector(".said").textContent = "作品は " + list.dataset.max + " までです"; return; }
    box.append(pieceRow(list, {title: "", verdict: "", note: "", cast: []}));
  } else if (b.dataset.pieceDel) {
    const box = b.closest(".pc-rows");
    b.closest(".pc-row").remove();
    if (!box.children.length) box.append(pieceRow(box.closest(".ed-piecel"), {title: "", verdict: "", note: "", cast: []}));
  } else if (b.dataset.piecesSave || b.dataset.piecesStop) {
    const g = b.closest(".ed-pieces"), list = g.querySelector(".ed-piecel"), said = g.querySelector(".said");
    let pieces = [];
    if (b.dataset.piecesSave) {
      for (const r of list.querySelectorAll(".pc-row")) {
        const title = r.querySelector("[data-pc-title]").value.trim();
        const verdict = r.querySelector("[data-pc-verdict]").value, note = r.querySelector("[data-pc-note]").value;
        const boxes = [...r.querySelectorAll("input[data-pc-cast]")], cast = boxes.filter(c => c.checked).map(c => c.dataset.pcCast);
        if (!title && !verdict && !note.trim()) continue;           // 何も入れていない欄は数えない
        if (boxes.length && !cast.length) { said.textContent = "「" + (title || "作品") + "」に出ていた人を 1 人以上選んでください"; return; }
        pieces.push({title, verdict, note, cast: cast.length === boxes.length ? [] : cast});
      }
      if (pieces.length < 2) { said.textContent = "作品を 2 つ以上入れてください（分けるのをやめるときは「分けるのをやめる」）"; return; }
    }
    post("/api/pieces", {work_key: list.dataset.work, pieces}, g,
      pieces.length ? pieces.length + " 作品に分けて保存しました" : "分けるのをやめました（記録は残っています）")
      .then(d => { if (d) setTimeout(() => location.reload(), 1000); });
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
      b.textContent = "本当に消す（もう戻せません）";
      return;
    }
    post("/api/purge_work", {key: b.dataset.purge}, g,
      "完全に取り消しました。この一覧から消えます")
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
        ? (d.gone ? "直しました。この題名は演劇ではないものとして、候補から外れます"
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
         g.querySelector(".ed-btns"), "抽出結果に戻しました。画面を読み込み直します").then(d => {
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
    // **書いてある感想は、その文をそのまま書き直す**（起案者の指示 2026-10-13「書き直す押したら下に
    // テキストボックス出すのではなく、そのうえに書いてある斜体の文章直接編集できるようにして」）
    if (r && r.querySelector(".int")) {
      const el = r.querySelector(".int");
      editInPlace(b, el, box.querySelector("textarea"), r, "/api/note",
                  t => ({work_key: t.dataset.note, note_impression: t.value}), "感想を保存しました");
      // 書き直しているあいだだけ、タグの札を文の下に出す。書き終えたら札を外し、タグをリンクに戻す
      if (el.isContentEditable && !r.querySelector(".htchips")) {
        const chips = tagChips(tag => {
          el.textContent = addTag(el.textContent, tag);
          const sel = getSelection(), rg = document.createRange();
          rg.selectNodeContents(el); rg.collapse(false); sel.removeAllRanges(); sel.addRange(rg);
        });
        r.after(chips);
        el.addEventListener("blur", () => setTimeout(() => { chips.remove(); linkTags(r); }, 50), {once: true});
      }
      return;
    }
    if (r) r.hidden = true; else b.hidden = true;
    box.hidden = false;
    box.querySelector("textarea").focus();
  } else if (b.dataset.vnoteOpen) {
    // **「この回のメモ」も、感想と同じ「押してから開く」形にそろえる**（`data-note-open`
    // と同じ判断）
    const w = b.closest(".vnw") || b.closest(".rec-row");
    const box = w.querySelector(".vnote"), r = w.querySelector(".vnr");
    if (r && r.querySelector(".vnt")) {
      editInPlace(b, r.querySelector(".vnt"), box.querySelector("textarea"), r, "/api/visit_note",
                  t => ({uid: t.dataset.vnote, note: t.value}), "メモを保存しました");
      return;
    }
    if (r) r.hidden = true; else b.hidden = true;
    box.hidden = false;
    box.querySelector("textarea").focus();
  } else if (b.dataset.rateOpen) {
    // **押してから開く。** 感想の欄と同じ形（`data-note-open`）にそろえてある
    const row = b.closest(".rec-row"), g = row.querySelector(".rb");
    if (g) { g.hidden = false; b.hidden = true; }
  } else if (b.dataset.btnsOpen) {
    // **答えた公演の三択は「回答を直す」を押してから開く**（「評価を押し直す」と同じ形。カードも開幕リマインドの行も）
    const row = b.closest(".ticket, .dgli"), g = row && row.querySelector(".btns");
    if (g) { g.hidden = false; b.hidden = true; }
    // 興味ありの「なぜ気になったか」も、ここで開いて直せるようにする（起案者の指示 2026-10-15。ふだんは畳んである）
    const wn = row && row.querySelector(".wnw[hidden]");
    if (wn) wn.hidden = false;
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
    // あらすじの続きと、出演者の残り。**同じ押し口で開く**。開いたら「折りたたむ」で閉じられる（起案者の指示 2026-10-18）
    const box = b.closest(".syn") || b.closest(".cast");
    const open = box.classList.toggle("open");
    if (!b.dataset.label) b.dataset.label = b.textContent;
    b.textContent = open ? "折りたたむ" : b.dataset.label;
  } else if (b.dataset.close) {
    fetch(API_BASE + "/api/close", {method: "POST", keepalive: true, credentials: "include"});
    b.textContent = "閉じて大丈夫です";
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
// **見つからなかった題名を、次の更新で探すよう頼むボタン。** 公開版はその場で外部を
// 検索しないので、代わりに依頼として控え、毎日の更新でまとめて探す（`/api/search_request`）
function requestButton(box, q, source) {
  // **デモは依頼を受け付けない**(本番の取得に関わらない)。サーバー側でも断る
  if (IS_DEMO) return;
  const wrap = document.createElement("p");
  wrap.className = "sug-head";
  const b = document.createElement("button");
  b.type = "button";
  b.dataset.searchRequest = q;
  b.dataset.source = source;
  b.textContent = "「" + q + "」を次の更新で探してもらう";
  const said = document.createElement("span");
  said.className = "said";
  wrap.append(b, " ", said);
  box.append(wrap);
}

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
    lkSay(box, CATALOG_NAME + "を探しています…");
    if (btn) btn.disabled = true;
  }
  let d;
  try {
    const r = await fetch(API_BASE + (web ? "/api/suggest_web?t=" : "/api/suggest?t=")
      + encodeURIComponent(T) + "&q=" + encodeURIComponent(q),
      {headers: {"X-Taguri-Token": T}, credentials: "include"});
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
      ? "「" + q + "」に一致する公演は見つかりませんでした。副題や団体名を外して"
        + "短くすると見つかることがあります"
      : "手元のデータには見つかりませんでした。「" + WEB_BUTTON + "」を押してください"
        + "（月 1 回の取得に含まれていない公演や、古い公演は手元にありません）");
    if (web) requestButton(box, q, "hand");
    return;
  }
  if (web) lkSay(box, CATALOG_NAME + "から " + rows.length
    + " 件見つかりました。観た公演を選んでください。見つからない場合は下の"
    + "「ポスター・クレジットを手入力する」から追加してください。");
  lkRender(box, rows);
}

document.addEventListener("input", ev => {
  const i = ev.target.closest("[data-lk-q]");
  if (!i || !live) return;
  clearTimeout(i._t);
  i._t = setTimeout(() => lkSearch(i, false, null), 220);
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
      sm.textContent = xs[0].title + "（" + xs.length + " 会場の上演"
        + (mine ? "、うち " + mine + " 回の記録があります" : "") + "）";
      d.append(sm);
      const p = document.createElement("p");
      p.className = "sug-head";
      p.textContent = "観に行った会場と日程を選んでください。"
        + "会場ごとに出演者や座組が違うことがあるので、"
        + "別の上演を選ぶと、観ていない公演の作り手がおすすめの材料に入ってしまいます。";
      d.append(p);
      xs.forEach(x => d.append(stageRow(x)));
      if (mine) d.open = true;
      box.append(d);
    });
}

// **手で足す欄の候補。** すでにある情報を、打っている最中に出す
let sugTimer = null;
let sugSeq = 0;

// **行けばよかったの題名の欄も、2 文字以上打つと候補を出す**（起案者の指示 2026-10-20「行けばよかったの検索欄、探すのページと
// 同じで2文字以上入れたら候補出るようにして」）。候補は観劇記録を追加の題名の欄と同じ（/api/suggest・sugRender）。
// 選ぶとその公演を指して足す。打ち直したら指した公演は外す
let missTimer = null, missSeq = 0;
document.addEventListener("input", ev => {
  const i = ev.target.closest && ev.target.closest("#miss-title");
  if (!i) return;
  delete i.dataset.stage;
  clearTimeout(missTimer);
  const seq = ++missSeq;
  missTimer = setTimeout(async () => {
    const box = i.closest(".miss-add")?.querySelector(".miss-sug");
    if (!box) return;
    const q = i.value.trim();
    if (Array.from(q).length < 2) { box.replaceChildren(); return; }
    let d;
    try {
      const r = await fetch(API_BASE + "/api/suggest?t=" + encodeURIComponent(T) + "&q=" + encodeURIComponent(q),
        {headers: {"X-Taguri-Token": T}, credentials: "include"});
      d = await r.json();
    } catch (e) { return; }
    if (seq !== missSeq || !box.isConnected) return;
    sugRender(box, d.rows, "すでにある公演から選べます（" + ((d.rows || []).length) + " 件）");
  }, 220);
});

// Native dialog supplies Escape handling, modal focus and focus restoration.
function registerSearchDialog(trigger) {
  const dialog = document.getElementById('register-search-dialog');
  if (!dialog) return;
  const form = dialog.querySelector('form'), status = dialog.querySelector('.rs-status'), box = dialog.querySelector('.rs-results');
  const title = document.getElementById('w-title').value;
  if (form.elements.q.value !== title) {
    form.elements.q.value = title; box.replaceChildren();
    status.textContent = '条件を入れて「検索する」を押してください。';
  }
  if (dialog.dataset.rsBound) { dialog.showModal(); return; }
  dialog.dataset.rsBound = '1';
  dialog.querySelector('[data-rs-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    const picked = dialog.dataset.picked;
    delete dialog.dataset.picked;
    if (picked) document.getElementById('w-date')?.focus();
    else if (trigger.isConnected) trigger.focus();
  });
  dialog.addEventListener('click', ev => { if (ev.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) dialog.close();
  }});
  form.addEventListener('submit', async ev => {
    ev.preventDefault(); ev.stopPropagation();
    const q = form.elements.q.value.trim();
    if (Array.from(q).length < 2) { status.textContent = '公演名を2文字以上入力してください。'; form.elements.q.focus(); return; }
    const params = new URLSearchParams({q, advanced: '1', t: T,
      group: form.elements.group.value.trim(), venue: form.elements.venue.value.trim()});
    for (const part of ['year', 'month', 'day']) {
      const field = form.elements['schedule_' + part];
      const value = field.value.trim();
      if (value) params.set('schedule_' + part, value);
    }
    const button = form.querySelector('button[type=submit]');
    button.disabled = true; box.replaceChildren(); status.textContent = '検索中…';
    try {
      const response = await fetch(API_BASE + '/api/suggest?' + params, {credentials: 'include'});
      const data = await response.json();
      if (!response.ok || data.error) throw Error(data.error || '検索できませんでした。もう一度お試しください。');
      if (!dialog.isConnected) return;
      const rows = (data.rows || []).filter(row => row.kind === 'stage');
      status.textContent = rows.length ? rows.length + '件の候補が見つかりました。観た公演を選んでください。'
        : '条件に合う公演が見つかりませんでした。公演名を詳しく入力するか、ほかの条件を減らしてください。閉じて手入力で記録することもできます。';
      sugRender(box, rows, '保存済みの公演から、最大8作品の候補を表示します。');
    } catch (error) { if (dialog.isConnected) status.textContent = error.message; }
    finally { button.disabled = false; }
  });
  dialog.showModal();
}
// **画面を差し込むたびに呼ぶ**（renderScreen）。画面の中身は読み込んだあとに fetch で入るので、
// 読み込みのときに 1 度だけ呼んでいた頃は欄がまだ無く、打っても候補が出なかった（#134 の通し検証）。
// 2 度結ばないように印を付ける
function sugWatch() {
  const t = document.getElementById("w-title"), box = document.getElementById("sug");
  if (!t || !box || t.dataset.sugBound) return;
  t.dataset.sugBound = "1";
  t.addEventListener("input", () => {
    document.getElementById("w-stage").value = "";   // 打ち直したら結び付きを外す
    runDates(document.getElementById("w-date"), "", "");
    clearTimeout(sugTimer);
    ++sugSeq;
    sugTimer = setTimeout(() => sugFetch(t.value, box), 220);
  });
}

async function sugFetch(q, box) {
  const seq = ++sugSeq;
  if (q.trim().length < 2) { box.replaceChildren(); return; }
  let d;
  try {
    const r = await fetch(API_BASE + "/api/suggest?t=" + encodeURIComponent(T)
      + "&q=" + encodeURIComponent(q), {headers: {"X-Taguri-Token": T}, credentials: "include"});
    d = await r.json();
  } catch (e) { return; }
  if (seq !== sugSeq || !box.isConnected) return;
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
  sugSay(box, CATALOG_NAME + "を探しています…", true);
  if (btn) btn.disabled = true;
  let d = null;
  try {
    const r = await fetch(API_BASE + "/api/suggest_web?t=" + encodeURIComponent(T)
      + "&q=" + encodeURIComponent(q), {headers: {"X-Taguri-Token": T}, credentials: "include"});
    d = await r.json();
  } catch (e) { d = null; }
  if (btn) btn.disabled = false;
  if (!d) {
    sugSay(box, "探せませんでした。お手数ですが、手で入力してください", true);
    return;
  }
  if (d.error) { sugSay(box, d.error, true); return; }
  if (!d.rows || !d.rows.length) {
    // **見つからなかったことを、次に何をすればよいかと一緒に出す。**
    // 「0 件」だけでは、打ち間違いなのか無い公演なのか分からない
    sugSay(box, "「" + q + "」に一致する公演は見つかりませんでした。副題や団体名を外して"
      + "短くすると見つかることがあります。見つからないときは、そのまま手で入れてください", true);
    requestButton(box, q, "hand");
    return;
  }
  sugRender(box, d.rows,
    CATALOG_NAME + "から " + d.rows.length + " 件見つかりました。観た公演を選んでください");
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
// 「これを使う」で選んだ公演の上演期間を、観た日の欄の選べる範囲にする（起案者の指示 2026-10-19「選んだ公演があるなら、観た日の
// カレンダーの表示を最初からその年月にして表示してほしい」）。日付の欄（type=date）のカレンダーは、空のときは今日を選べる範囲に寄せた
// 年月で開くので、範囲を上演期間にすると、その公演の年月から開く。選び直す・題名を打ち直すと範囲を外す
function runDates(dt, start, end) {
  if (!dt) return;
  if (!start && !end) { delete dt.dataset.times; setTimeChoices(null); }
  const ok = v => /^\d{4}-\d{2}-\d{2}$/.test(v || "");
  if (ok(start)) dt.min = start; else dt.removeAttribute("min");
  if (ok(end || start)) dt.max = ok(end) ? end : start; else dt.removeAttribute("max");
}
// 選んだ公演の開演時刻（/api/stage_times）が分かる日は、開演時刻の欄をその時刻だけのプルダウンにする（起案者の指示 2026-10-19
// 「観た日の時間、も最初からわかってるならその時間しか選べないようにプルダウン化してよい」）。分からない日は、これまでどおり自由に入れる欄
function setTimeChoices(times) {
  const cur = document.getElementById("w-time");
  if (!cur) return;
  const want = times && times.length ? "SELECT" : "INPUT";
  let el = cur;
  if (cur.tagName !== want) {
    el = document.createElement(want === "SELECT" ? "select" : "input");
    el.id = "w-time";
    if (want === "INPUT") el.type = "time";
    cur.replaceWith(el);
  }
  if (want === "SELECT") {
    const keep = cur.value;
    el.innerHTML = (times.length > 1 ? '<option value="">選んでください</option>' : "") + times.map(t => '<option value="' + E(t) + '">' + E(t) + "</option>").join("");
    if (times.includes(keep)) el.value = keep;
  }
}
function timesForDate() {
  const dt = document.getElementById("w-date");
  let all = {};
  try { all = JSON.parse(dt?.dataset.times || "{}") || {}; } catch (e) { all = {}; }
  setTimeChoices(dt && dt.value ? all[dt.value] || null : null);
}
document.addEventListener("change", ev => { if (ev.target.id === "w-date") timesForDate(); });
async function loadStageTimes(sid) {
  const dt = document.getElementById("w-date");
  if (!dt) return;
  delete dt.dataset.times;
  setTimeChoices(null);
  if (!sid || IS_DEMO) return;
  try {
    const r = await fetch(API_BASE + "/api/stage_times?stage_id=" + encodeURIComponent(sid), {credentials: "include"});
    const d = r.ok ? await r.json() : {};
    if (document.getElementById("w-stage")?.value !== sid) return;   // 待つ間に選び直した
    dt.dataset.times = JSON.stringify(d.times || {});
    timesForDate();
  } catch (e) { /* 分からなければ自由に入れる欄のまま */ }
}
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
    r.dataset.start = x.start || ""; r.dataset.end = x.end || "";
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
      + "&uid=" + encodeURIComponent(box.dataset.hints),
      {headers: {"X-Taguri-Token": T}, credentials: "include"});
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
                            {headers: {"X-Taguri-Token": T}, credentials: "include"});
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
  if (sec < 60) return "あと 1 分もかかりません";
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
                            {headers: {"X-Taguri-Token": T}, credentials: "include"});
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

// 走っている最中に開き直したときは、そのまま続きから見せる（`app._import_bar`）。
// **元は読み込み時に1度だけ走る処理だったが、SPAでは「公演情報の登録」の
// フラグメントを差し込むたびに呼び直す必要がある**(#000009)。呼び出しは
// renderScreen()。
function fixupImportBar(root) {
  const bar = live && (root || document).querySelector("[data-ibar][data-run]");
  if (bar) {
    const g = (root || document).querySelector(".imp");
    if (g) poll(g, g.querySelector("button"));
  }
}
fixupImportBar(document);

// **入力欄の動きは、後から足した 1 枚にも付ける。**
//
// **「行く日を追加」は、時刻の欄の右に「追加」だけを置き、日付・時刻・押し口を 1 行に収める**
// （起案者の指示 2026-10-13「時刻入力フォームの右に『追加』だけ表示して。同じ行に表示して改行されないように」）
function shortAddButtons(root) {
  root.querySelectorAll(".mt-add button[data-mt-add]").forEach(b => {
    b.innerHTML = ico("plus", 13) + "追加";
    b.setAttribute("aria-label", "行く日を追加");
  });
}

// **評価の分布は、1 本の横向きの 100% 積み上げ帯にする。**
// 起案者の指示 2026-10-20「評価一覧の分布、横向きの１００％積み上げ帯グラフにして」。全体のうち各段階が占める割合を 1 本の帯で見る。
// 2026-10-19 の指示（「合っていた」を判定しない）は守る: 帯は「合っていた／合わなかった」の 2 色に分けず、段階の順（低い段階が左）に
// 1 色の濃淡で塗る。評価でない行（未評価）は灰色の斜線。
// 帯の中には、幅が足りる段階（9% 以上）だけ割合を書き、段階の名前と件数は下の凡例に書く（帯の中に名前まで書くと、狭い段階で切れる）。数字は「数字で見る」の表にもある
function divergeVerdicts(root) {
  root.querySelectorAll(".card .dbar").forEach(bar => {
    const card = bar.closest(".card");
    if (!card || card.dataset.diverged) return;
    const rows = [];
    card.querySelectorAll("table tr").forEach(tr => {
      const td = tr.querySelectorAll("td");
      if (td.length < 2) return;
      const g = td[0].textContent.trim(), v = parseInt(td[1].textContent, 10) || 0;
      if (v) rows.push([g, v]);
    });
    if (!rows.length) return;
    card.dataset.diverged = "1";
    const all = rows.reduce((t, r) => t + r[1], 0);
    const graded = rows.filter(([g]) => g !== "未評価").length;
    let k = 0;
    // 左がいちばん低い段階、右がいちばん高い段階（起案者の指示 2026-10-20「左が一番評価低くて一番右が評価高いで統一して」）。
    // 表は高い段階から並ぶので、評価の段階を逆にし、評価でない「未評価」はいちばん左に置く（右端はいちばん高い段階のまま）
    const segs = [...rows.filter(([g]) => g === "未評価"), ...rows.filter(([g]) => g !== "未評価").reverse()].map(([g, v]) => {
      const p = v / all * 100, none = g === "未評価";
      // 濃さ: 最も低い段階（左）を 28%、最も高い段階（右）を 100% にし、そのあいだを等分する（段階が 1 つなら 100%）
      const shade = none ? 0 : graded > 1 ? Math.round(28 + 72 * (k++) / (graded - 1)) : (k++, 100);
      return {g, v, p, none, shade};
    });
    const pctText = p => (p < 1 ? "1%未満" : Math.round(p) + "%");
    const html = '<div class="vstack" role="img" aria-label="' + E("評価の割合: " + segs.map(x => x.g + " " + pctText(x.p)).join("、")) + '">'
      + '<div class="vs-bar">' + segs.map(x => '<span class="vs-seg' + (x.none ? " none" : "") + (x.shade >= 60 ? " dark" : "") + '" style="width:'
        + x.p.toFixed(2) + "%" + (x.none ? "" : ";--vs-shade:" + x.shade + "%") + '" title="' + E(x.g + " " + x.v + " 件（" + pctText(x.p) + "）") + '">'
        + (x.p >= 9 ? '<span class="vs-in">' + pctText(x.p) + "</span>" : "") + "</span>").join("") + "</div>"
      + '<ul class="vs-leg">' + segs.map(x => '<li><i class="vs-sw' + (x.none ? " none" : "") + '"' + (x.none ? "" : ' style="--vs-shade:' + x.shade + '%"')
        + "></i>" + E(x.g) + ' <b>' + x.v + "</b> 件<small>（" + pctText(x.p) + "）</small></li>").join("") + "</ul></div>";
    bar.insertAdjacentHTML("afterend", html);
    bar.remove();
  });
}

// **評価を押し直すのは、判子の丸から。**（起案者の指示 2026-10-13「『評価を押し直す』ってボタンは消して、
// 各ハンコの丸を押したらポップアップで選びなおしできるのがでて、押し直せるようにして」）。
// 判子を押すと、その横に ◎○△× の小さな札が開く。押すと今までどおり記録し（同じ押し口 data-v）、判子が
// 押し直され、札は閉じる。札の外を押すか Esc で閉じる
// ---- 評価の「詳細」（起案者の指示 2026-10-14「詳細の画面を作って」・q-pr13-aspects-screen）。
// 評価を付けた記録に「詳細」を出し、8 項目それぞれを 5 段階（好みではない／やや好みではない／ふつう／やや好き／好き）で
// 選ぶ（起案者の指示 2026-10-18「評価の詳細を 5 段階（好みではない〜好き）に変えて」）。項目ごとの ✕ で「この作品には無い」（歌・ダンスの無い作品など）にでき、外した項目は下の「＋」でもう一度足せる
// （起案者の指示 2026-10-18「評価の詳細、今3段階で設定してるけど適切？最低限5段階くらいほしい。あと作品によっては歌ダンスが
// ないこともあるので、なかったときは✕で要素を消せるようにしてほしい」、dec-aspects-five-levels）。
// 保存の形は works.aspects（カンマ区切り。やや好みではない＝コード、やや好き＝+コード、好みではない＝--コード、好き＝
// ++コード、この作品には無い＝~コード。「ふつう」は書かない。recommend.ASPECT_MARKS）で、POST /api/rate {work_key, aspects}。
// 前の 3 段階の「良かった」「気になった」は やや好き・やや好みではない として読む。推薦は付いた印だけを見て、好き・好みではない は
// その項目の人に少し重く効かせ（recommend.ASPECT_STRONG）、無い項目は使わない。
// 出し方は人ごとに選べる: 「あっさり」（既定。詳細は閉じておく）と「詳しく」（開いた状態で出す）。画面だけの設定
const ASPECTS = [["story", "話・脚本・構成"], ["direction", "演出・見せ方"], ["acting", "演技・出演"], ["music", "歌・音楽"],
  ["dance", "ダンス"], ["design", "美術・衣裳"], ["price", "値段"], ["venue", "会場・座席"]];
// 印と段階（recommend.ASPECT_MARKS と同じ。並びは保存の順）。"na" = この作品には無い
const ASPECT_MARK = [["", -1], ["+", 1], ["--", -2], ["++", 2], ["~", "na"]];
const ASPECT_WORD = {"-2": "好みではない", "-1": "やや好みではない", "0": "ふつう", "1": "やや好き", "2": "好き"};
const ASPECT_MODE_KEY = "taguri.aspectsMode";       // "plain"（あっさり・既定）か "full"（詳しく）
function aspectsMode() { try { return localStorage.getItem(ASPECT_MODE_KEY) === "full" ? "full" : "plain"; } catch (e) { return "plain"; } }
function aspectToken(x) { for (const m of ["++", "--", "+", "~"]) if (x.startsWith(m)) return [m, x.slice(m.length)]; return ["", x]; }
// 見出しの横の要約: 「好き: 演技・出演／やや好みではない: 値段」（好き → 好みではない の順。ふつう・無い項目は出さない）
function aspectsSummary(state) {
  return [2, 1, -1, -2].map(v => {
    const ls = ASPECTS.filter(([c]) => state[c] === v).map(x => x[1]);
    return ls.length ? ASPECT_WORD[v] + ": " + ls.join("・") : "";
  }).filter(Boolean).join("／") || "まだ選んでいません";
}
function aspectsPanel(root) {
  // 項目ごとのつまみ: 左端＝好みではない、まん中＝ふつう、右端＝好き（起案者の指示 2026-10-14「よかったはボタンじゃなくて
  // スライダーで」、2026-10-18 に 5 段階）。離したときに保存する（動かしている途中では送らない）
  root.querySelectorAll(".rec-row[data-aspects]").forEach(row => {
    if (row.querySelector(".asp")) return;
    const rb = row.querySelector(".rb[data-work]"), st = row.querySelector("[data-stamp]");
    if (!rb) return;
    // 星の行には判子が無い（星の列が評価を見せる）ので、塗った星で見る
    const rated = () => {
      if (!st) return Boolean(rb.querySelector(".star.on, .star0.on, .hs.on, .hs.h"));
      const t = st.textContent.trim(); return t !== "" && ("◎○△×".includes(t) || /^★\d(\.5)?$/.test(t));
    };
    const state = {};
    const read = text => {
      Object.keys(state).forEach(k => delete state[k]);
      (text || "").split(",").filter(Boolean).forEach(x => {
        const [m, c] = aspectToken(x), hit = ASPECT_MARK.find(([k]) => k === m);
        if (hit && !(c in state)) state[c] = hit[1];
      });
    };
    read(row.dataset.aspects);
    const box = document.createElement("details");
    box.className = "asp";
    if (aspectsMode() === "full") box.open = true;
    const id = c => "asp-" + c + "-" + E(rb.dataset.work);
    const items = ASPECTS.map(([c, label]) => '<div class="aspr" data-a="' + c + '"><label class="aspl" for="' + id(c) + '">' + E(label) + "</label>"
      + '<input class="aspsl" type="range" min="-2" max="2" step="1" id="' + id(c) + '" data-a="' + c + '" value="0"><span class="aspv"></span>'
      + '<button type="button" class="aspx" data-na="' + c + '" aria-label="「' + E(label) + '」はこの作品に無い（項目を外す）" title="この作品には無い">✕</button></div>').join("");
    box.innerHTML = '<summary><span class="aspt">詳細</span><span class="asps"></span></summary>'
      + '<p class="asph">項目ごとに、つまみを 5 段階（左端 好みではない ～ まん中 ふつう ～ 右端 好き）で動かします（任意）。'
      + 'その作品に無い項目（歌・ダンスの無い芝居など）は右の ✕ で外せます。'
      + '選んだ印は次のおすすめで「どの人のおかげ・せいだったか」を分けるのに使います。外した項目は使いません。</p>'
      + '<div class="aspscale" aria-hidden="true"><span></span><span class="asc"><span>← 好みではない</span><span>ふつう</span><span>好き →</span></span><span></span><span></span></div>'
      + '<div class="aspg">' + items + '</div>'
      + '<p class="aspna" hidden><span class="aspnl">この作品に無い項目（押すと戻します）:</span></p>'
      + '<p class="said" role="status"></p>';
    const mark = sl => { const v = +sl.value; sl.dataset.m = v > 0 ? "good" : v < 0 ? "bad" : "mid"; sl.dataset.lv = String(v); };
    const paint = () => {
      box.querySelector(".asps").textContent = aspectsSummary(state);
      box.querySelectorAll(".aspr").forEach(r => {
        const c = r.dataset.a, na = state[c] === "na", sl = r.querySelector(".aspsl");
        r.hidden = na;
        const v = typeof state[c] === "number" ? state[c] : 0;
        sl.value = v;
        mark(sl);
        sl.setAttribute("aria-valuetext", ASPECT_WORD[v]);
        r.querySelector(".aspv").textContent = ASPECT_WORD[v];
      });
      const na = box.querySelector(".aspna");
      na.querySelectorAll(".aspadd").forEach(x => x.remove());
      const gone = ASPECTS.filter(([c]) => state[c] === "na");
      gone.forEach(([c, label]) => na.insertAdjacentHTML("beforeend", '<button type="button" class="aspadd" data-add="' + c + '" aria-label="「' + E(label) + '」を戻す">＋ ' + E(label) + "</button>"));
      na.hidden = !gone.length;
    };
    const save = async (before, focus) => {
      paint();
      const aspects = ASPECT_MARK.flatMap(([m, lv]) => ASPECTS.filter(([c]) => state[c] === lv).map(([c]) => m + c));
      const d = await post("/api/rate", {work_key: rb.dataset.work, aspects}, box, "詳細を保存しました");
      if (!d) { Object.keys(state).forEach(k => delete state[k]); Object.assign(state, before); paint(); }
      else row.dataset.aspects = d.aspects ?? aspects.join(",");
      if (focus) { const f = box.querySelector(focus); if (f && !f.closest("[hidden]")) f.focus(); }
    };
    box.addEventListener("input", ev => {
      const sl = ev.target.closest(".aspsl");
      if (!sl) return;
      sl.nextElementSibling.textContent = ASPECT_WORD[+sl.value];
      mark(sl);
    });
    box.addEventListener("change", ev => {
      const sl = ev.target.closest(".aspsl");
      if (!sl) return;
      const before = {...state};
      const v = +sl.value;
      if (v) state[sl.dataset.a] = v; else delete state[sl.dataset.a];
      save(before);
    });
    box.addEventListener("click", ev => {
      const x = ev.target.closest("button.aspx, button.aspadd");
      if (!x) return;
      const before = {...state};
      if (x.dataset.na) { state[x.dataset.na] = "na"; save(before, ".aspadd[data-add='" + x.dataset.na + "']"); }
      else { delete state[x.dataset.add]; save(before, ".aspr[data-a='" + x.dataset.add + "'] .aspsl"); }
    });
    paint();
    box.hidden = !rated();
    // 評価を付けた（押し直した・✕ で消した）あとに出す・隠す
    rb.addEventListener("click", () => setTimeout(() => { box.hidden = !rated(); }, 600));
    (row.querySelector(".page") || row).appendChild(box);
  });
}
// 設定の画面に「評価の詳細の出し方」を足す（この端末に覚える。画面だけの設定）
function aspectsSetting(el) {
  if (el.querySelector(".aspset")) return;
  const h1 = el.querySelector("h1");
  if (!h1) return;
  const cur = aspectsMode();
  // ほかの設定と同じ折りたたみ（details.card）にする（起案者の指示 2026-10-19「『カードに出す名前』『評価の詳細の出し方』も他と同じ様に折りたたみにして」）
  const sec = document.createElement("details");
  sec.className = "aspset card";
  sec.innerHTML = '<summary><h2>評価の詳細の出し方</h2></summary><p class="lead">評価を付けた記録の「詳細」（話・演出・演技などを 好き〜好みではない の 5 段階で）を、'
    + 'ふだん閉じておくか、開いて出すかを選べます。表示だけの設定で、おすすめの計算は変わりません。</p>'
    + '<div class="aspmode" role="radiogroup" aria-label="評価の詳細の出し方">'
    + [["plain", "あっさり", "詳細は閉じておく（押すと開く）"], ["full", "詳しく", "詳細を開いた状態で出す"]].map(([v, t, d]) =>
      '<label class="aspm"><input type="radio" name="aspmode" value="' + v + '"' + (v === cur ? " checked" : "") + '><b>' + t + "</b><span>" + d + "</span></label>").join("")
    + '</div><p class="said" role="status"></p>';
  sec.addEventListener("change", ev => {
    try { localStorage.setItem(ASPECT_MODE_KEY, ev.target.value); } catch (e) { /* 覚えられなくても既定で動く */ }
    sec.querySelector(".said").textContent = "保存しました（この端末で有効です）";
  });
  const last = [...el.querySelectorAll("section, .pbox, details")].filter(n => n.parentElement === el).pop();
  (last || h1).after(sec);
}

// カードに出す作り手の名前を選ぶ（設定。起案者の指示 2026-10-18「設定でどこの名前まで表示するかにしてチェックリストで選べるように」）
function creditSetting(el) {
  if (el.querySelector(".credset")) return;
  const h1 = el.querySelector("h1");
  if (!h1) return;
  const cur = creditChoice();
  const sec = document.createElement("details");   // ほかの設定と同じ折りたたみ（起案者の指示 2026-10-19）
  sec.className = "credset card";
  sec.innerHTML = '<summary><h2>カードに出す名前</h2></summary><p class="lead">公演のカードに、どの役職の名前まで出すかを選べます。'
    + '<b>作・原作・脚本・演出は、いつも出します。</b>表示だけの設定で、おすすめの計算は変わりません。</p>'
    + '<div class="credlist">'
    + '<label class="credi"><input type="checkbox" checked disabled><span>作・原作・脚本・演出（いつも出します）</span></label>'
    + CREDIT_OPTIONS.map(([k, t]) => '<label class="credi"><input type="checkbox" value="' + k + '"' + (cur.has(k) ? " checked" : "") + "><span>" + E(t) + "</span></label>").join("")
    + '</div><p class="said" role="status"></p>';
  sec.addEventListener("change", () => {
    const v = [...sec.querySelectorAll("input[value]:checked")].map(i => i.value);
    try { localStorage.setItem(CREDIT_KEY, JSON.stringify(v)); } catch (e) { /* 覚えられなくても既定で動く */ }
    sec.querySelector(".said").textContent = "保存しました（この端末で有効です。次に開いたカードから反映されます）";
  });
  const last = [...el.querySelectorAll("section, .pbox, details")].filter(n => n.parentElement === el).pop();
  (last || h1).after(sec);
}

// 文字の形の設定は外した（起案者の指示 2026-10-19「設定にある『文字の形』を消して」）。前に「規定の文字」を選んだ端末も、決まりの文字に戻す
try { localStorage.removeItem("taguri_font_v1"); } catch (e) { /* 消せなくても下で決まりの文字にする */ }
document.documentElement.dataset.font = "trial";

function stampRerate(root) {
  root.querySelectorAll(".rec-row").forEach(row => {
    const open = row.querySelector("button[data-rate-open]"), rb = row.querySelector(".rb:not(.notseen)");
    const st = row.querySelector("[data-stamp]");
    if (!open || !rb || !st || st.dataset.rerate) return;
    st.dataset.rerate = "1";
    open.remove();
    st.setAttribute("role", "button");
    st.setAttribute("tabindex", "0");
    st.setAttribute("aria-label", "評価を選び直す（いまは " + (st.textContent.trim() || "未評価") + "）");
    st.setAttribute("aria-haspopup", "true");
    st.setAttribute("aria-expanded", "false");
    rb.classList.add("rbpop");
    rb.setAttribute("role", "group");
    rb.setAttribute("aria-label", "評価を選び直す");
    const place = () => {
      const r = row.getBoundingClientRect(), s = st.getBoundingClientRect();
      rb.style.left = Math.max(8, s.left - r.left) + "px";
      rb.style.top = (s.bottom - r.top + 6) + "px";
    };
    const close = () => { rb.hidden = true; st.setAttribute("aria-expanded", "false"); };
    rb._close = close;   // 外を押したら閉じる（下の 1 つの受け口から呼ぶ）
    const toggle = () => {
      if (!rb.hidden) { close(); return; }
      rb.classList.remove("done");
      rb.hidden = false;
      place();
      st.setAttribute("aria-expanded", "true");
      rb.querySelector("button[data-v]")?.focus();
    };
    st.addEventListener("click", ev => { ev.stopPropagation(); toggle(); });
    st.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); toggle(); } });
    rb.addEventListener("keydown", ev => { if (ev.key === "Escape") { close(); st.focus(); } });
    // 押して記録できたら（押し口の列に done が付いたら）閉じる
    new MutationObserver(() => { if (rb.classList.contains("done")) setTimeout(close, 450); })
      .observe(rb, {attributes: true, attributeFilter: ["class"]});
  });
}
// **外を押したら閉じる受け口は、画面全体で 1 つだけにする**（#85）。行ごと・画面ごとに document へ足していくと、
// 画面を移るたびに増え、外した画面の分まで残り続けていた。開いている札を、押したときに探して閉じる
document.addEventListener("click", ev => {
  document.querySelectorAll(".rb.rbpop:not([hidden])").forEach(rb => {
    const st = rb.closest(".rec-row")?.querySelector("[data-stamp]");
    if (rb._close && !rb.contains(ev.target) && !(st && st.contains(ev.target))) rb._close();
  });
  const pop = document.getElementById("infopop");
  if (pop && !pop.hidden && !pop.contains(ev.target) && !ev.target.closest?.(".crumbinfo")) {
    pop.hidden = true;
    document.querySelectorAll(".crumbinfo").forEach(b => b.setAttribute("aria-expanded", "false"));
  }
});

// **画面の説明文は、パンくずの右端の「ⓘ」から開く。**（起案者の指示 2026-10-13「こういう文章はパンくずリストの
// 一番右にあるやつの右に、インフォーメーションマークつけて、押したらポップアップで説明出るように（パソコンも）。
// それでこの文は消して。全ページに適用」）。題字（最初の h1）のすぐ後に続く説明の段落（p.lede・p.lead・p.note）を
// 本文から外し、説明の札に移す。リンクや強調はそのまま動く（押すと移動する）。説明が無い画面には ⓘ を出さない
function infoFromLede(root) {
  const bar = document.getElementById("crumbbar"), nav = document.getElementById("crumbnav");
  if (!bar || !nav) return;
  bar.querySelectorAll(".infopop").forEach(n => n.remove());
  const h1 = root.querySelector("h1");
  if (!h1) return;
  const isLede = n => n && n.nodeType === 1 && n.matches("p.lede, p.lead, p.note");
  let n = h1.nextElementSibling;
  if (!n && h1.parentElement && h1.parentElement !== root) n = h1.parentElement.nextElementSibling;
  const take = [];
  while (isLede(n)) { take.push(n); n = n.nextElementSibling; }
  // 画面の下のほうにある説明でも、サーバーが .toinfo を付けたものはここに入れる
  // （「この 15 件で、出せていない情報です。」・起案者の指示 2026-10-14）
  root.querySelectorAll(".toinfo").forEach(p => { if (!take.includes(p)) take.push(p); });
  if (!take.length) return;
  const pop = document.createElement("div");
  pop.className = "infopop";
  pop.id = "infopop";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", "この画面の説明");
  pop.hidden = true;
  take.forEach(p => pop.appendChild(p));
  bar.appendChild(pop);
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "crumbinfo";
  btn.setAttribute("aria-label", "この画面の説明");
  btn.setAttribute("aria-expanded", "false");
  btn.setAttribute("aria-controls", "infopop");
  btn.title = "この画面の説明";
  btn.innerHTML = ico("info", 18);
  nav.appendChild(btn);
  const close = () => { pop.hidden = true; btn.setAttribute("aria-expanded", "false"); };
  btn.addEventListener("click", ev => {
    ev.stopPropagation();
    if (!pop.hidden) { close(); return; }
    const b = bar.getBoundingClientRect(), r = btn.getBoundingClientRect();
    pop.style.top = (r.bottom - b.top + 8) + "px";
    pop.hidden = false;
    btn.setAttribute("aria-expanded", "true");
  });
  pop.addEventListener("keydown", ev => { if (ev.key === "Escape") { close(); btn.focus(); } });
  btn.addEventListener("keydown", ev => { if (ev.key === "Escape") close(); });
  // 外を押したら閉じるのは、stampRerate の下の 1 つの受け口（#85）
}

// **書いてある感想・回のメモの「書き直す」を、文の末尾の鉛筆にする。**（起案者の指摘 2026-10-13
// 「『書き直す』のボタンがあるせいで文字の折り返しが多くて感想が縦に伸びてる…鉛筆のアイコンボタンを
// 感想の末尾につけるとかだけでも伝わる」）。文と鉛筆を 1 つの箱に入れ、鉛筆は文の最後の行に続けて置く
function penNotes(root) {
  // 「なぜ気になったか」（.wnr）も同じ鉛筆にする（起案者の指示 2026-10-14「『書き直す』はすべて鉛筆アイコンにして」）
  root.querySelectorAll(".inr, .vnr, .wnr").forEach(r => {
    const t = r.querySelector(":scope > .int, :scope > .vnt, :scope > .wnt"), b = r.querySelector(":scope > .wnb");
    if (!t || !b) return;
    const box = document.createElement("span");
    box.className = "inb";
    t.before(box);
    box.append(t, b);
    b.classList.add("pen");
    setPen(b, false);
  });
}
function setPen(b, editing) {
  if (!b.classList.contains("pen")) { b.textContent = editing ? "書き終える" : "書き直す"; return; }
  b.innerHTML = ico(editing ? "check" : "pencil", 15);
  b.setAttribute("aria-label", editing ? "書き終える" : "書き直す");
  b.title = editing ? "書き終える" : "書き直す";
}
// 日記帳の「感想」の欄は、地の色を付けた所のどこを押しても書き始められる（鉛筆を押したのと同じ）
// （起案者の指示 2026-10-18「『感想』の右に背景色つけて記入欄がここにありますよってわかりやすくして。」）。
// 書いている最中・リンク（タグ）・ボタン・文を選んでいるときは何もしない
document.addEventListener("click", ev => {
  const box = ev.target.closest && ev.target.closest('[data-route="/records/works"] .inr>.inb');
  if (!box || ev.target.closest("button, a, [contenteditable]") || box.querySelector("[contenteditable]")) return;
  if (String(window.getSelection ? getSelection() : "")) return;
  const pen = box.querySelector("[data-note-open]");
  if (pen) pen.click();
});

// **X のポストの URL を貼ると、その本文を感想に入れる**（起案者の指示 2026-10-21「Xと連携して、ツイートを感想として
// 紐付けられると便利そう」「リンク貼る方式にしましょう」）。本文は Worker が X の埋め込み用の口（oEmbed、無料・鍵なし）で
// 読む（/api/x_post、cloudflare/src/x-post.js）。感想の最後の行に「[X 日付] URL」を残し、画面ではそれを
// 「日付 の X のポストから · X で見る ↗」の行にする。読めなかったときは URL をそのまま入れる
const X_POST_URL = /^https?:\/\/(?:www\.|mobile\.)?(?:x|twitter)\.com\/[A-Za-z0-9_]{1,15}\/status(?:es)?\/\d{1,25}(?:[/?#]\S*)?$/;
const X_MARK_LINE = /\n*\[X (?:\d{4}-\d{2}-\d{2})?\] https:\/\/x\.com\/[A-Za-z0-9_]{1,15}\/status\/\d{1,25}\s*$/;
function insertAtCaret(el, text) {
  el.focus();
  let ok = false;
  try { ok = document.execCommand("insertText", false, text); } catch (e) {}
  if (ok) return;
  if ("value" in el) {
    const a = el.selectionStart ?? el.value.length, b = el.selectionEnd ?? a;
    el.value = el.value.slice(0, a) + text + el.value.slice(b);
  } else el.textContent += text;
}
async function pasteXPost(ev, el, said, onMark) {
  const text = ((ev.clipboardData && ev.clipboardData.getData("text/plain")) || "").trim();
  if (!X_POST_URL.test(text)) return;
  ev.preventDefault();
  if (said) said.textContent = "X のポストを読んでいます…";
  let d;
  try {
    const r = await fetch("/api/x_post?url=" + encodeURIComponent(text), {credentials: "same-origin"});
    d = await r.json().catch(() => ({}));
    if (!r.ok || !d.ok) throw new Error(d.error || "このポストは読めませんでした。");
  } catch (e) {
    if (said) said.textContent = e.message;
    insertAtCaret(el, text);
    return;
  }
  insertAtCaret(el, d.text);
  onMark(d.mark);
  if (said) said.textContent = "X のポストの文を入れました。離れると保存します。";
}
// 出どころの行（row.xSource と同じ形）を、感想の行（.inr）の中に出し直す。m が空なら外す
function showXSource(row, m) {
  let x = row.querySelector(":scope > .xsrc");
  const g = /^\[X (\d{4}-\d{2}-\d{2})?\] (\S+)$/.exec(m || "");
  if (!g) { if (x) x.remove(); return; }
  if (!x) { x = document.createElement("span"); x.className = "xsrc"; (row.querySelector(":scope > .said") || row.appendChild(document.createTextNode(""))).before(x); }
  x.textContent = (g[1] ? g[1].replaceAll("-", "/") + " の " : "") + "X のポストから · ";
  const a = document.createElement("a");
  a.href = g[2]; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = "X で見る ↗";
  x.append(a);
}

// **書いてある文を、その場で書き直せる欄にする。** 下に入力欄を開くのではなく、読んでいた文の上で
// そのまま書く。離れたら（または「書き終える」を押したら）保存し、Esc で元に戻す。保存は今までと
// 同じ口（感想は /api/note、回のメモは /api/visit_note）。隠れている textarea も同じ値にそろえておく
function editInPlace(btn, el, ta, row, path, bodyOf, okMsg) {
  if (el.isContentEditable) { el.blur(); return; }
  // 「書き終える」を押すと、先に文から離れた（blur）ことで保存が済む。そのあとに届く押下で
  // また書き始めないようにする
  if (btn._finishedAt && Date.now() - btn._finishedAt < 600) return;
  const before = el.textContent, xsrc0 = el.dataset.xsrc || "";
  // 文と、X のポストから取り込んだときの出どころの行（data-xsrc）を合わせたものが保存する感想になる
  const full = () => { const b = el.textContent.trim(); return b && el.dataset.xsrc ? b + "\n\n" + el.dataset.xsrc : b; };
  const onPaste = ev => pasteXPost(ev, el, row.querySelector(":scope > .said"), m => { el.dataset.xsrc = m; showXSource(row, m); });
  if (path === "/api/note") el.addEventListener("paste", onPaste);
  try { el.contentEditable = "plaintext-only"; } catch (e) {}
  if (!el.isContentEditable) el.contentEditable = "true";
  el.setAttribute("role", "textbox");
  el.setAttribute("aria-multiline", "true");
  setPen(btn, true);
  let said = row.querySelector(":scope > .said");
  if (!said) { said = document.createElement("span"); said.className = "said"; row.appendChild(said); }
  said.textContent = "";
  el.focus();
  const sel = window.getSelection(), range = document.createRange();
  range.selectNodeContents(el); range.collapse(false); sel.removeAllRanges(); sel.addRange(range);
  const finish = save => {
    el.removeEventListener("blur", onBlur);
    el.removeEventListener("keydown", onKey);
    el.removeEventListener("paste", onPaste);
    el.removeAttribute("contenteditable");
    el.removeAttribute("role");
    el.removeAttribute("aria-multiline");
    setPen(btn, false);
    const body = el.textContent.trim(), text = full();
    const was = before.trim() && xsrc0 ? before.trim() + "\n\n" + xsrc0 : before.trim();
    // 前に保存できなかった文（unsaved）は、書き直さずに離れても送り直す（#83）
    if (!save || (text === was && !el.dataset.unsaved)) {
      el.textContent = before;
      if (xsrc0) el.dataset.xsrc = xsrc0; else delete el.dataset.xsrc;
      showXSource(row, xsrc0);
      return;
    }
    el.textContent = body;
    if (!body) { delete el.dataset.xsrc; showXSource(row, ""); }
    if (ta) ta.value = text;
    if (!live) return;
    // 送るのは隠れている欄と同じ順番待ち（#84）。失敗しても文は巻き戻さない ── 巻き戻すと、
    // 返ってくるまでに書いた新しい文まで消える。保存できなかった印だけ付けておく
    const holder = ta || el;
    if (holder.dataset.was === undefined) holder.dataset.was = was;
    saveQueued(holder, text, row, t => post(path, bodyOf({dataset: ta ? ta.dataset : {}, value: t}), row, okMsg).then(d => {
      if (d && full() === t) delete el.dataset.unsaved;
      if (!d) el.dataset.unsaved = "1";
      return d;
    }));
  };
  const onBlur = () => { btn._finishedAt = Date.now(); finish(true); };
  const onKey = ev => {
    if (ev.key === "Escape") { ev.preventDefault(); el.removeEventListener("blur", onBlur); finish(false); el.blur(); }
  };
  el.addEventListener("blur", onBlur);
  el.addEventListener("keydown", onKey);
}

// ボタンは `document` で受けているので足した 1 枚でも効くが、**入力欄は読み込みのときに
// 1 度だけ結んでいた** ── 入れ替わりに差し込んだカードの欄は、書けるのに保存されない
// 欄になる。**2 度結ばないように印を付ける**（同じ blur で 2 回送ることになる）。
// 「なぜ気になったか」に、その公演の人の名前を札で並べ、押すだけで書き入れられるようにする
// （起案者の指示 2026-10-14「出演者や作り手で選んでることが多いけど、いちいち名前入力するの面倒」）。
// 名前は券に出ている出演（出演順に 8 人まで）・作り手（演出・脚本など 4 人まで）・団体。押すと欄の文に
// 「、」で足し、もう一度押すと外す。押すたびに保存する（文に出た名前はお気に入りの候補になる・reasons.py）
const TAG_ROLES = ["作・演出", "作・演出・振付", "演出", "脚本", "作", "脚本・演出", "原作", "振付", "音楽", "作曲"];
// 出演欄の名前を切り出す。**括弧の中の注記は、区切る前に外す**（起案者の指摘 2026-10-14 ──
// ミス・サイゴンの「…桐山照史（以上、交互出演）」が「桐山照史（以上」と「交互出演）」に割れていた）。
// 閉じていない括弧の残り（「（以上」）は捨て、開きの無い「…）」だけの切れ端は名前にしない
function splitCast(text) {
  return text.replace(/[（(][^（()）]*[）)]/g, "").split("、")
    .map(n => n.replace(/[（(].*$/, "").trim()).filter(n => n && !/[）)]/.test(n));
}
function noteNames(tk) {
  const out = [], add = (name, kind) => {
    name = name.replace(/\s*ほか\s*\d+\s*名\s*$/, "").trim();
    if (name && name.length <= 30 && !out.some(x => x.name === name)) out.push({name, kind});
  };
  const lv = tk.querySelector(".lcast .lv");
  if (lv) {
    const c = lv.cloneNode(true);
    c.querySelectorAll(".n").forEach(n => n.remove());
    splitCast(c.textContent).slice(0, 8).forEach(n => add(n, "出演"));
  }
  let makers = 0;
  tk.querySelectorAll(".cast .cr").forEach(r => {
    const role = (r.querySelector(".cl")?.textContent || "").trim(), v = r.querySelector(".cv");
    if (!v || (role === "出演" && lv)) return;
    if (role !== "出演" && !TAG_ROLES.includes(role)) return;
    splitCast(v.textContent).forEach(n => { if (role === "出演" || makers++ < 4) add(n, role); });
  });
  const grp = tk.querySelector(".meta .mg")?.textContent.trim();
  if (grp) add(grp, "団体");
  return out;
}
function noteTags(t) {
  const g = t.closest(".why-note"), tk = t.closest("article.ticket");
  if (!g || !tk || g.querySelector(".wtags")) return;
  const names = noteNames(tk);
  if (!names.length) return;
  const box = document.createElement("div");
  box.className = "wtags";
  box.innerHTML = '<span class="wtl">名前から選ぶ</span>' + names.map(x =>
    '<button type="button" class="wtag" data-name="' + E(x.name) + '" title="' + E(x.kind) + '" aria-pressed="false">'
    + E(x.name) + "</button>").join("");
  const parts = () => t.value.split(/[、,，\n]/).map(x => x.trim()).filter(Boolean);
  const sync = () => box.querySelectorAll(".wtag").forEach(b =>
    b.setAttribute("aria-pressed", parts().includes(b.dataset.name) ? "true" : "false"));
  box.addEventListener("click", ev => {
    const b = ev.target.closest(".wtag");
    if (!b) return;
    const name = b.dataset.name, have = parts();
    if (have.includes(name)) {
      t.value = t.value.split(/(、|,|，|\n)/).filter(x => x.trim() !== name).join("")
        .replace(/^(、|,|，)+|(、|,|，)+$/g, "").replace(/(、){2,}/g, "、");
    } else {
      t.value = (t.value.trim() ? t.value.trim().replace(/[、,，]$/, "") + "、" : "") + name;
    }
    sync();
    t.dispatchEvent(new Event("blur"));       // 押すたびに保存する（下の blur の処理）
  });
  t.addEventListener("input", sync);
  t.before(box);
  sync();
}

// ---- おすすめの券からお気に入りに足す（起案者の指示 2026-10-14「おすすめのページからお気に入りに追加できる
// ようにしてほしい」）。券の右上の ☆ を押すと、その券の 作品・団体・出演・作り手 の名前が並び、押した名前を
// お気に入りに登録する（/api/favourite、設定の画面で足すのと同じ）。登録した名前の公演は件数の制限なしに新着に出る
function favButton(tk) {
  const h3 = tk.querySelector(".main h3");
  if (!h3 || tk.querySelector(".favbtn")) return;
  const b = document.createElement("button");
  b.type = "button";
  b.className = "favbtn";
  b.setAttribute("aria-haspopup", "true");
  b.setAttribute("aria-expanded", "false");
  b.title = "お気に入りに追加";
  b.setAttribute("aria-label", "この公演の名前をお気に入りに追加");
  b.innerHTML = ico("star", 18);
  h3.after(b);
  b.addEventListener("click", ev => {
    ev.stopPropagation();
    const old = tk.querySelector(".favpop");
    if (old) { old.remove(); b.setAttribute("aria-expanded", "false"); return; }
    const title = h3.textContent.trim();
    // あらすじの題材の札（#家族 など）も「題材」として選べる（推薦側 9bd0922: お気に入りの題材が推薦に効く）
    const themes = [...tk.querySelectorAll(".syn .tags .tag:not(.mine)")].map(t => t.textContent.replace(/^#/, "").trim())
      .filter((t, i, a) => Array.from(t).length >= 2 && a.indexOf(t) === i).slice(0, 8);
    const items = [{kind: "作品", name: title}].concat(noteNames(tk).map(x => ({kind: x.kind === "団体" ? "団体" : "人", name: x.name, role: x.kind})))
      .concat(themes.map(t => ({kind: "題材", name: t})));
    const pop = document.createElement("div");
    pop.className = "favpop";
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-label", "お気に入りに追加");
    pop.innerHTML = '<p class="fpt"><b>お気に入りに追加</b><span>登録した名前の公演は、件数の制限なしに新着に出ます</span></p>'
      + '<div class="fpl">' + items.map(x => '<button type="button" class="fpi" data-kind="' + E(x.kind) + '" data-name="' + E(x.name) + '">'
        + '<span class="fk">' + E(x.role && x.role !== x.kind ? x.role : x.kind) + "</span>" + E(x.name) + "</button>").join("") + "</div>"
      + '<p class="said" role="status"></p>';
    b.after(pop);
    b.setAttribute("aria-expanded", "true");
    pop.addEventListener("click", async e => {
      const it = e.target.closest(".fpi");
      if (!it || it.disabled) return;
      it.disabled = true;
      const d = await post("/api/favourite", {action: "add", kind: it.dataset.kind, name: it.dataset.name}, pop,
        "「" + it.dataset.name + "」を登録しました");
      if (d) it.classList.add("added"); else it.disabled = false;
    });
    const close = e => {
      if (e.type === "keydown" && e.key !== "Escape") return;
      if (e.type === "click" && pop.contains(e.target)) return;
      pop.remove(); b.setAttribute("aria-expanded", "false");
      document.removeEventListener("click", close); document.removeEventListener("keydown", close);
      if (e.type === "keydown") b.focus();
    };
    setTimeout(() => { document.addEventListener("click", close); document.addEventListener("keydown", close); }, 0);
    pop.querySelector(".fpi")?.focus();
  });
}

// ---- 感想のハッシュタグ（起案者の指示 2026-10-14「感想を書くとき、ハッシュタグをユーザーが独自で作って検索
// できるようにして」）。#タグ と書けばタグになる（サーバーの hashtags.py と同じ区切り）。書いてある感想の中の
// タグは「感想」の画面のそのタグへのリンクにし、感想を書く欄の上には、今まで使ったタグを札で並べる
let NOTE_TAGS = [];
const TAG_RE = /[#＃]([^\s#＃、。，,．.!！?？「」『』（）()\[\]【】<>＜＞]{1,30})/g;
function linkTags(root) {
  root.querySelectorAll(".int").forEach(el => {
    if (el.isContentEditable || el.querySelector("a.htag-in") || !TAG_RE.test(el.textContent)) return;
    TAG_RE.lastIndex = 0;
    const text = el.textContent;
    let html = "", at = 0;
    for (const m of text.matchAll(TAG_RE)) {
      const tag = m[1].normalize("NFKC");
      html += E(text.slice(at, m.index)) + '<a class="htag-in" href="/rate/notes?tag=' + encodeURIComponent(tag) + '">' + E(m[0]) + "</a>";
      at = m.index + m[0].length;
    }
    el.innerHTML = html + E(text.slice(at));
  });
}
function tagChips(onPick) {
  const box = document.createElement("div");
  box.className = "htchips";
  box.innerHTML = '<span class="htl2"># を付けるとタグになります' + (NOTE_TAGS.length ? "。使ったタグ:" : "") + "</span>"
    + NOTE_TAGS.slice(0, 20).map(t => '<button type="button" class="htc" data-tag="' + E(t) + '">#' + E(t) + "</button>").join("");
  box.addEventListener("mousedown", e => { if (e.target.closest(".htc")) e.preventDefault(); });   // 書いている欄から焦点を外さない
  box.addEventListener("click", e => { const c = e.target.closest(".htc"); if (c) onPick("#" + c.dataset.tag); });
  return box;
}
const addTag = (text, tag) => (text.includes(tag) ? text : (text.trim() ? text.replace(/\s*$/, " ") : "") + tag);

// **離れたときに保存する欄の送り方**（#83・#84）。
// - 「保存済みの文」（dataset.was）は、保存できたときだけ進める。失敗したら書いた文は欄に残し、
//   もう一度離れれば送り直す（前は送る前に進めていたので、同じ文のままでは二度と送られなかった）
// - 同じ欄の保存は 1 本ずつ送る。送っている間に書き直されたら、返ってから最新の文を送る ──
//   先に送った分が後から返って、新しい文を上書き・巻き戻すことがない
// - 届いたか分からない失敗でも、同じ文を勝手に送り直さない（#96）。送り直すのは、書いた人が離れたとき
function saveQueued(holder, text, group, send) {
  if (holder._busy) { holder._next = text; return; }
  if (text === holder.dataset.was) return;
  holder._busy = true;
  send(text).then(d => {
    holder._busy = false;
    if (d) holder.dataset.was = text;
    const next = holder._next;
    holder._next = undefined;
    if (next !== undefined && next !== text) { saveQueued(holder, next, group, send); return; }
    const said = group && group.querySelector(".said");
    if (!d && said) said.append("（書いた文は残しています。もう一度欄から離れると送り直します）");
  });
}

function bindNotes(root) {
root.querySelectorAll("article.ticket.cmp").forEach(favButton);
linkTags(root);
root.querySelectorAll("textarea[data-note]").forEach(t => {
  if (t.previousElementSibling && t.previousElementSibling.classList.contains("htchips")) return;
  t.before(tagChips(tag => { t.value = addTag(t.value, tag); t.focus(); }));
});
// 「興味あり」に添えた理由。**離れたときに保存する**（書いている途中で送らない）
root.querySelectorAll(".why-note textarea").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  noteTags(t);
  t.addEventListener("blur", () => {
    const g = t.closest(".why-note");
    if (!live) return;
    saveQueued(t, t.value, g, text => post("/api/react", {stage_id: g.dataset.stage, note: text}, g,
         "理由を保存しました（お気に入りに加える候補に出ます）").then(d => {
      const memo = t.closest(".why-memo"), preview = memo?.querySelector("summary .wnt");
      if (d && d.ok !== false && preview) preview.textContent = text || "メモを書く（任意）";
      if ((!d || d.ok === false) && memo) memo.open = true;
      return d;
    }));
  });
});

// 購入済み公演の「観る前のメモ」。見送った理由と同じく、離れたときに保存し、畳んだ見出しに文を出す
root.querySelectorAll("textarea[data-prenote]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    const g = t.closest(".nn");
    if (!live) return;
    saveQueued(t, t.value, g, text => post("/api/react", {stage_id: g.dataset.stage, note_pre: text}, g, "メモを保存しました").then(d => {
      if (!d) return d;
      const s = g.querySelector("summary");
      if (!text.trim()) { s.innerHTML = '観る前のメモを書く<span class="opt">任意</span>'; return d; }
      s.textContent = "観る前のメモ";
      const v = document.createElement("span");
      v.className = "nnv";
      v.textContent = text;
      s.append(v);
      return d;
    }));
  });
});

// 「興味なし」に添えた見送った理由。**離れたときに保存する**
root.querySelectorAll("textarea[data-nono]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    const g = t.closest(".nn");
    if (!live) return;
    saveQueued(t, t.value, g, text => post("/api/react", {stage_id: g.dataset.stage, note_no: text}, g,
         "理由を保存しました").then(d => {
      if (!d || !text.trim()) return d;
      // **畳んだ見出しに書いた文を出す。** 閉じても読めることが、この欄の返りである
      const s = g.querySelector("summary");
      s.textContent = "見送った理由";
      const v = document.createElement("span");
      v.className = "nnv";
      v.textContent = text;
      s.append(v);
      return d;
    }));
  });
});

root.querySelectorAll("textarea[data-note]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("paste", ev => pasteXPost(ev, t, (t.closest(".inote, .wnote, .wait, .rec-row") || document).querySelector(".said"),
    m => { t.value = t.value.replace(X_MARK_LINE, "").trimEnd() + "\n\n" + m; }));
  t.addEventListener("blur", () => {
    if (!live) return;
    // **保存できたことを、書いた欄のそばに出す。** `.rec-row` しか見ていなかったため、
    // 評価待ちの行と溜まった分の束に置いた欄では**保存の合図がどこにも出なかった**
    // （消えたのか保存されたのか分からない入力になる）
    const g = t.closest(".inote, .wnote, .wait, .rec-row");
    saveQueued(t, t.value, g, text => post("/api/note", {work_key: t.dataset.note, note_impression: text}, g, "感想を保存しました"));
  });
});

// **「この回のメモ」も、離れたときに保存する**（感想と同じ形）。推薦には使わない
// 欄なので、送り先も別の口（`/api/visit_note`）にする
root.querySelectorAll("textarea[data-vnote]").forEach(t => {
  if (t.dataset.bound) return;
  t.dataset.bound = "1";
  t.dataset.was = t.value;
  t.addEventListener("blur", () => {
    if (!live) return;
    const g = t.closest(".vnote, .rec-row");
    saveQueued(t, t.value, g, text => post("/api/visit_note", {uid: t.dataset.vnote, note: text}, g, "メモを保存しました"));
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
  if (said) said.textContent = "保存しています…";
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
// **元は読み込み時に1度だけ走る処理だったが、SPAではフラグメントを差し込む
// たびに呼び直す必要がある**(#000009、location.reload()の直後にここへ来る)。
function fixupWeightHash(root) {
  const wb = (root || document).querySelector("#weights");
  if (wb && location.hash === "#weights") wb.open = true;
}
fixupWeightHash(document);

// **画面を閉じたら自動で終了する仕組みは撤回した**（起案者の指示・2026-08-27）。
// 「記録を見返す」のような画面を長時間開いたままにする使い方と噛み合わなかった
// （タブを裏に回すとブラウザが定期送信を間引き、まだ見ているのに落ちることがあった）。
// 閉じるのはフッターの「終わる」ボタン（`/api/close`）と `Ctrl-C` に一本化した。
if (live) sugWatch();

// === ported: tools/taguri/people.py の PE.JS(相関図パネル) ===

function fixupPeopleNet(root) {
  root = root || document;
  const box = root.querySelector("[data-pnet]");
  if (!box) return;
  const src = box.querySelector("[data-pnet-data]");
  let D;
  try { D = JSON.parse(src.textContent); } catch (e) { return; }
  const svg = box.querySelector("svg"), tip = box.querySelector("[data-ptip]");
  const said = root.querySelector("[data-psaid]");
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
  const slow = typeof matchMedia === "function"
    && matchMedia("(prefers-reduced-motion: reduce)").matches;
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
      + `<span class="tw">観た作品 ${n.w} 本・共演した人 ${n.d} 名`
      + (n.c ? "・この人を外すとグループが分かれます" : "") + `</span>`
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
  const btns = [...root.querySelectorAll(".pcut button")];
  const rst = root.querySelector(".pcut .rst");
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
        + `${cs.length} つのグループに分かれます</b>（${sizes.join(" 名・")} 名）。`
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
  const tsrc = root.querySelector("[data-pnet-time]");
  let T = null;
  try { if (tsrc) T = JSON.parse(tsrc.textContent); } catch (e) { T = null; }
  if (T && T.stages && T.stages.length) {
    const sl = root.querySelector("[data-psl]");
    const play = root.querySelector("[data-pplay]");
    const note = root.querySelector("[data-pnstage]");
    const gap = root.querySelector("[data-pgap]");
    const pcutBox = root.querySelector(".pcut");
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
          const r = root.querySelector(".pcut .rst");
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
}

// === 劇場制覇マップ(cloudflare/src/screens/conquest.js) ===
// マスを押すと、その県で行った劇場を地図の下に出す(起案者の指示 2026-10-16「地方のマス押したら行った劇場の
// 名前が出るようにデモと同じようにして」)。一覧はサーバーが県ごとに隠して描いてあり、ここでは出し分けるだけ
function fixupConquest(root) {
  (root || document).querySelectorAll("section.cq").forEach(sec => {
    const pick = p => {
      sec.querySelectorAll(".cq-tile").forEach(t => t.classList.toggle("sel", t.dataset.p === p));
      sec.querySelectorAll(".cq-pick").forEach(d => { d.hidden = d.dataset.p !== p; });
      const hint = sec.querySelector(".cq-hint");
      if (hint) hint.hidden = true;
    };
    sec.querySelectorAll(".cq-tile[data-p]").forEach(t => {
      t.addEventListener("click", () => pick(t.dataset.p));
      t.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(t.dataset.p); } });
    });
  });
}

// === ported: tools/taguri/prefmap.py の PM.JS(地図パネル) ===

// **地図と地方の札は、チェックを反転させるだけである。**（`prefmap.py` の説明）
// 塗りは CSS が `:checked` から決めるので、ここでは見た目に触らない ──
// **状態を 2 つ持つと、ずれたときにどちらが本当か決められない。**
function fixupPrefMap(root) {
  root = root || document;
  // **`.pfil`（場所の絞り込みの form）だけを見る。** `.pbox` は畳んである道具の枠
  // として使い回している名前なので、最初の 1 つが場所の箱とはかぎらない
  const box = root.querySelector("form.pfil");
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
}

// === ported: tools/taguri/stage_calendar.py の JS(カレンダーの「行く日を追加」ダイアログ) ===

// **元は読み込み時に1度だけ走る処理だったが、SPAではフラグメントを
// 差し込むたびに呼び直す必要がある**(#000009)。呼び出しはrenderScreen()。
// **行く日を入れた月は、その日が見える所まで送る**（起案者の指摘 2026-10-14「公演カレンダーのページから
// 観劇日を追加してもカレンダーに反映されない」── スマホでは今日の位置に送るので、先の行く日が右に隠れていた）。
// 題名の列は左に留めてある（style.css の .mgrid .nm）ので、その幅を除いた所に置く
// 2026-10-15 から格子は月ごとでなく 1 枚に続く（stage_calendar._timeline）。行く日が今日から
// 画面 1 枚ぶん（題名の列を除いた幅の 6 割）より先なら今日の位置に、近ければ行く日が入る位置に送る
function fixupMonthScroll(root) {
  (root || document).querySelectorAll(".mscroll").forEach(s => {
    const now = s.querySelector(".now"), pts = [...s.querySelectorAll(".mgrid .pt")];
    const nmW = (s.querySelector(".mgrid .nm") || {offsetWidth: 0}).offsetWidth;
    const from = now ? now.offsetLeft : 0;
    const go = pts.find(p => p.offsetLeft >= from && p.offsetLeft - from < (s.clientWidth - nmW) * 0.6);
    const at = go || now || pts[0];
    if (!at) return;
    s.scrollLeft = Math.max(0, at.offsetLeft - nmW - (s.clientWidth - nmW) * 0.35);
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
  // 削除は、何を消して何が残るかをサーバーがボタンに書いておく（data-done・#100）。読めるように少し待ってから読み込み直す
  const said = body.action === "del" ? (b.dataset.done || "削除しました") : "確定しました";
  post("/api/ticket", body, dlg, said).then(r => {
    if (r) setTimeout(() => location.reload(), body.action === "del" ? 2500 : 500);
  });
});
document.addEventListener("change", ev => {
  const sel = ev.target.closest && ev.target.closest(".tkd-work");
  if (sel) tkdSync(sel.closest("dialog"));
});

// === ported: tools/taguri/chronicle.py の JS(年表の「読みを作り直す」ボタン) ===
// **1回だけグローバルに登録する。** chronicle.pyのpanel()はこのJSを呼び出しの
// たびに<script>タグごと埋め込むが、innerHTML経由では実行されない(想定どおり
// 無害)。document.addEventListenerでの委譲なので、ここで1回登録しておけば
// /records/chronicleを何度開いても効く。

document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest("[data-chron]");
  if (!b) return;
  const box = b.closest(".chfoot");
  box.querySelector(".said").textContent = "書いています…（1 分ほどかかります）";
  post("/api/chronicle", {}, box, null).then(r => {
    box.querySelector(".said").textContent =
      r ? (r.line || "作りました") + "　画面を読み込み直すと出ます" : "";
  });
});

// --- アカウントの小窓（起案者の指示 2026-10-19「現在のアカウントアイコンを押したら、現在開いている画面の上にポップアップが出るように
// して。ポップアップの中にアカウントと設定とログアウト（この端末でログイン）を入れて、それぞれ押したらページに飛ぶように」）。
// 電話の幅は右上のアイコン（.pacct）、パソコンの幅は左の帯の「アカウント」から開く
function closeAcctMenu() {
  document.querySelectorAll(".acctpop").forEach(p => p.remove());
  document.querySelectorAll("[data-acct-menu]").forEach(b => b.setAttribute("aria-expanded", "false"));
}
function openAcctMenu(btn) {
  closeAcctMenu();
  const pop = document.createElement("div");
  pop.className = "acctpop";
  pop.setAttribute("role", "menu");
  pop.innerHTML = '<a role="menuitem" href="/account" data-path="/account">' + ico("user", 16) + "アカウント</a>"
    + '<a role="menuitem" href="/settings" data-path="/settings">' + ico("gear", 16) + "設定</a>"
    + '<button type="button" role="menuitem" data-acct-logout>' + ico("logout", 16) + "ログアウト<small>（この端末で）</small></button>";
  document.body.appendChild(pop);
  const r = btn.getBoundingClientRect(), w = pop.offsetWidth;
  pop.style.top = Math.round(Math.min(r.bottom + 6, window.innerHeight - pop.offsetHeight - 8)) + "px";
  pop.style.left = Math.round(Math.max(8, Math.min(r.right - w, window.innerWidth - w - 8, r.left < window.innerWidth / 2 ? r.left : r.right - w))) + "px";
  btn.setAttribute("aria-expanded", "true");
  pop.querySelector("a,button").focus();
}
document.addEventListener("click", async ev => {
  const btn = ev.target.closest("[data-acct-menu]");
  if (btn) {
    ev.preventDefault(); ev.stopImmediatePropagation();
    if (btn.getAttribute("aria-expanded") === "true") closeAcctMenu(); else openAcctMenu(btn);
    return;
  }
  const pop = ev.target.closest(".acctpop");
  if (!pop) { closeAcctMenu(); return; }
  if (ev.target.closest("a")) { setTimeout(closeAcctMenu, 0); return; }   // 画面の移動は、ふだんのリンクと同じ道で
  if (ev.target.closest("[data-acct-logout]")) {
    const d = await post("/api/logout", {}, pop, "ログアウトしました");
    if (d) try { for (const k of ["taguri_login_email", "taguri_login_agree", "taguri_login_intent", "taguri_login_saved_at"]) localStorage.removeItem(k); } catch {}
    if (d) location.href = "/login";
  }
}, true);
document.addEventListener("keydown", ev => { if (ev.key === "Escape" && document.querySelector(".acctpop")) closeAcctMenu(); });
window.addEventListener("resize", closeAcctMenu);

// --- アカウント（Worker の screens/account.js。本人だけが見るページ） ---------------
// 表示名の保存と、ログアウト。ログアウトは Worker の /api/logout（この端末）・/api/logout/all（すべて）
document.addEventListener("submit", async ev => {
  const f = ev.target.closest("form[data-account-name]");
  if (!f) return;
  ev.preventDefault();
  const d = await post("/api/account", {display_name: f.elements.display_name.value}, f, "保存しました");
  if (d) {
    const n = document.querySelector(".acname .acname-t") || document.querySelector(".acname");
    if (n) n.textContent = d.display_name || "たぐりの利用者";
    f.elements.display_name.defaultValue = d.display_name || "";
    setTimeout(() => showNameForm(false), 900);
  }
}, true);
// 表示名は名前の右のえんぴつを押すと直す欄が開く（起案者の指示 2026-10-19）。「やめる」で閉じて、打ちかけた名前は元に戻す
function showNameForm(open) {
  const f = document.querySelector("form[data-account-name]"), b = document.querySelector("[data-account-name-edit]");
  if (!f) return;
  f.hidden = !open;
  if (b) { b.hidden = open; b.setAttribute("aria-expanded", String(open)); }
  if (open) { f.elements.display_name.focus(); f.elements.display_name.select(); }
  else { f.elements.display_name.value = f.elements.display_name.defaultValue; const said = f.querySelector(".said"); if (said) said.textContent = ""; if (b) b.focus(); }
}
document.addEventListener("click", ev => {
  if (ev.target.closest("[data-account-name-edit]")) showNameForm(true);
  else if (ev.target.closest("[data-account-name-cancel]")) showNameForm(false);
});
// アイコン画像（起案者の指示 2026-10-14）。**ブラウザで小さくしてから送る**: まん中を正方形に
// 切り抜いて 160×160 にし、WebP（書けない端末では JPEG）にする。元の写真は送らない（数 MB の写真を
// そのまま保存すると D1 の無料枠を食う。上限はサーバーが 60,000 文字で確かめる）
// 選んだ画像は FileReader で data: URL にしてから読む（起案者の指摘 2026-10-18「どのアイコン画像選んでも選べない」）。
// 前は URL.createObjectURL の blob: URL で読んでいたが、サイトの CSP（public/_headers の img-src 'self' data:）が
// blob: を許していないため、どの画像も読み込みに失敗していた。CSP は緩めず、許されている data: で読む
function avatarDataUrl(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader(), img = new Image();
    img.onload = () => {
      const side = Math.min(img.naturalWidth, img.naturalHeight), S = 160;
      const c = document.createElement("canvas");
      c.width = S; c.height = S;
      c.getContext("2d").drawImage(img, (img.naturalWidth - side) / 2, (img.naturalHeight - side) / 2, side, side, 0, 0, S, S);
      let out = c.toDataURL("image/webp", 0.82);
      if (!out.startsWith("data:image/webp")) out = c.toDataURL("image/jpeg", 0.85);
      resolve(out);
    };
    img.onerror = () => reject(new Error("画像を読めませんでした"));
    fr.onload = () => { img.src = String(fr.result || ""); };
    fr.onerror = () => reject(new Error("画像を読めませんでした"));
    fr.readAsDataURL(file);
  });
}
function showAvatar(src) {
  const av = document.querySelector(".acav"), clear = document.querySelector("[data-account-avatar-clear]");
  if (av) av.innerHTML = src ? '<img src="' + E(src) + '" alt="">' : ico("user", 30);
  if (clear) clear.hidden = !src;
}
document.addEventListener("change", async ev => {
  const input = ev.target.closest("input[data-account-avatar]");
  if (!input || !input.files || !input.files[0]) return;
  const said = document.querySelector("[data-account-avatar-said]"), box = input.closest(".acpic");
  if (said) said.textContent = "小さくしています…";
  let url;
  try { url = await avatarDataUrl(input.files[0]); }
  catch (e) { if (said) said.textContent = "この画像は読めませんでした。別の画像を選んでください"; return; }
  finally { input.value = ""; }
  const d = await post("/api/account", {avatar: url}, box, "アイコンを保存しました");
  if (d) showAvatar(d.avatar);
}, true);
document.addEventListener("click", async ev => {
  const b = ev.target.closest("[data-account-avatar-clear]");
  if (!b) return;
  const d = await post("/api/account", {avatar: ""}, b.closest(".acpic"), "アイコンを外しました");
  if (d) showAvatar("");
});
document.addEventListener("click", async ev => {
  const b = ev.target.closest("[data-account-logout]");
  if (!b) return;
  const all = b.dataset.accountLogout === "all";
  if (all && !confirm("ほかの端末も含めて、すべてログアウトします。よろしいですか？")) return;
  const card = b.closest(".acct-card");
  const d = await post(all ? "/api/logout/all" : "/api/logout", {}, card, "ログアウトしました");
  // ログインの画面がメールのリンク用に控えたアドレスなども消す（#132、cloudflare/src/client/login.js）
  if (d) try { for (const k of ["taguri_login_email", "taguri_login_agree", "taguri_login_intent", "taguri_login_saved_at"]) localStorage.removeItem(k); } catch {}
  if (d) location.href = "/login";
});

// **共有リンク**（起案者の指示 2026-10-21「共有できるようにしたい。公演単体か、または指定のページをパブリックで公開するか選べるように」、
// cloudflare/src/share.js、dec-share-links）。「共有」を押すと、評価・感想・名前を出すかを選ぶ小窓を開き、リンクを作る。
// リンクを知っている人はログインなしで見られる（検索エンジンには載らない）。設定の「共有中のリンク」から取り消せる
const SHARE_HEAD = {stage: "この公演を共有する", works: "観劇記録の一覧を共有する", records: "眺めるを共有する",
  favourites: "お気に入りを共有する", chronicle: "観劇史年表を共有する"};
function shareDialog() {
  let d = document.getElementById("share-dlg");
  if (!d) {
    d = document.createElement("dialog");
    d.id = "share-dlg";
    d.className = "share-dlg";
    document.body.appendChild(d);
  }
  return d;
}
// 日記帳の共有の押し口（ページと、各行の「観ました」）。日記帳の HTML は Python 版と同じ形に保つので（screens.test.js）、
// 押し口はここで足す。行は記録の鍵（data-work）で送り、公演に結び付いていない記録はサーバーが断る
const SHARE_ICON_SVG = '<svg class="ico" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.7" '
  + 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 15V4M8 8l4-4 4 4M5 13v6h14v-6"/></svg>';
function fixupShare(el, path) {
  if (EDITION.edition !== "service" || path !== "/records/works") return;
  const h1 = el.querySelector("h1");
  if (h1 && !el.querySelector('[data-share-kind="works"]')) {
    h1.insertAdjacentHTML("beforeend", '<button type="button" class="share-open share-page-btn" data-share-kind="works" aria-label="このページを共有" title="このページを共有">'
      + SHARE_ICON_SVG + "</button>");
  }
  el.querySelectorAll("article.rec-row").forEach(a => {
    const key = a.querySelector("[data-work]");
    if (!key || a.querySelector("[data-share-kind]")) return;
    a.insertAdjacentHTML("beforeend", '<button type="button" class="share-open" data-share-kind="stage" data-share-label="watched" data-share-work="'
      + E(key.dataset.work) + '" aria-label="この公演を共有" title="共有">' + SHARE_ICON_SVG + "</button>");
  });
}
function openShare(btn) {
  const kind = btn.dataset.shareKind, label = btn.dataset.shareLabel || "";
  // 評価・感想を出せるのは、記録のあるもの（購入済・興味ありのカードと、お気に入りには無い）
  const record = kind !== "favourites" && !(kind === "stage" && label !== "watched");
  const box = (k, text) => '<label class="share-opt"><input type="checkbox" data-share-opt="' + k + '"> ' + E(text) + "</label>";
  const d = shareDialog();
  d.dataset.kind = kind;
  d.dataset.stage = btn.dataset.shareStage || "";
  d.dataset.work = btn.dataset.shareWork || "";
  d.dataset.label = label;
  d.innerHTML = "<h2>" + E(SHARE_HEAD[kind] || "共有する") + "</h2>"
    + '<p class="share-lead">リンクを知っている人は、ログインしなくても見られます。検索エンジンには載りません。あとで設定の「共有中のリンク」から取り消せます。</p>'
    + '<fieldset class="share-opts"><legend>いっしょに出すもの（選ばなければ出しません）</legend>'
    + (record ? box("verdict", "評価") + box("note", "感想") : "") + box("name", "表示名とアイコン") + "</fieldset>"
    + '<div class="share-out" hidden><input class="share-url" readonly aria-label="共有のリンク">'
    + '<button type="button" data-share-copy-out="1">コピー</button>'
    + (navigator.share ? '<button type="button" data-share-send="1">ほかのアプリで送る</button>' : "") + "</div>"
    + '<div class="share-foot"><button type="button" class="primary" data-share-make="1">リンクを作る</button>'
    + '<button type="button" data-share-close="1">閉じる</button><span class="said"></span></div>';
  d.showModal();
}
async function copyText(text, said) {
  try { await navigator.clipboard.writeText(text); if (said) said.textContent = "コピーしました"; }
  catch (e) { if (said) said.textContent = "コピーできませんでした。リンクを長押ししてコピーしてください"; }
}
document.addEventListener("click", async ev => {
  const t = ev.target.closest ? ev.target : null;
  if (!t) return;
  const open = t.closest("[data-share-kind]");
  if (open) { ev.preventDefault(); openShare(open); return; }
  const d = t.closest("#share-dlg");
  if (d && t.closest("[data-share-close]")) { d.close(); return; }
  if (d && t.closest("[data-share-make]")) {
    const opt = k => !!d.querySelector('[data-share-opt="' + k + '"]:checked');
    const body = {action: "create", kind: d.dataset.kind, stage_id: d.dataset.stage, work_key: d.dataset.work, label: d.dataset.label,
      verdict: opt("verdict"), note: opt("note"), name: opt("name")};
    const r = await post("/api/share", body, d.querySelector(".share-foot"), null);
    if (!r || !r.path) return;
    const url = location.origin + r.path;
    const out = d.querySelector(".share-out");
    out.hidden = false;
    out.querySelector(".share-url").value = url;
    d.querySelector("[data-share-make]").hidden = true;
    d.querySelectorAll("[data-share-opt]").forEach(x => { x.disabled = true; });
    d.querySelector(".said").textContent = r.said || "リンクを作りました";
    markMutated();
    return;
  }
  if (d && t.closest("[data-share-copy-out]")) { await copyText(d.querySelector(".share-url").value, d.querySelector(".said")); return; }
  if (d && t.closest("[data-share-send]")) {
    try { await navigator.share({title: "たぐり", url: d.querySelector(".share-url").value}); } catch (e) { /* 送るのをやめた */ }
    return;
  }
  const copy = t.closest("[data-share-copy]");
  if (copy) { await copyText(location.origin + copy.dataset.shareCopy, copy.parentElement.querySelector(".said")); return; }
  const rev = t.closest("[data-share-revoke]");
  if (rev) {
    if (!confirm("このリンクを取り消しますか？ 取り消すと、このリンクはもう開けません")) return;
    const li = rev.closest("li");
    const r = await post("/api/share", {action: "revoke", token: rev.dataset.shareRevoke}, li, "取り消しました");
    if (r && li) { li.classList.add("gone"); rev.disabled = true; }
    if (r) markMutated();
  }
});
