// **初期読み込みの短縮(起案者の指摘)。** Renderの無料枠のコールドスタートが
// 支配的なので、CSS/app.jsの読み込みを待たずに、できるだけ早く1回目の
// APIリクエストを飛ばしてコールドスタートの時計を進めておく。app.js側は
// window.__prefetchが自分の見ようとしている画面と一致すれば、これを
// 使い回して二重にフェッチしない(app.js の loadScreen()参照)。
// index.html の中に書いていたが、CSP の 'unsafe-inline' を外すため、ファイルに出した(#155)。
// **画面名の出し方(app.jsのSCREENS/detectRepoBaseと同じ規則の最小限の複製)。**
// 新しい画面をIMPLEMENTEDに足すときも、ここを直す必要は無い ──
// 画面名は常にパスの最後のセグメント(例外は"/"→"recommend")である。
(function () {
  try {
    var TOP = ["recommend", "start", "calendar", "tickets", "rate",
      "register", "records", "search", "settings"];
    // 版ごとの配信先（/taguri-demo か /taguri-demo/app）を外してから画面名を読む
    var T = window.TAGURI || {base: "", api: ""};
    if (!T.api) return;
    var path = location.pathname;
    if (path.indexOf(T.base) === 0) path = path.slice(T.base.length);
    var segs = path.split("/").filter(Boolean);
    if (segs.length && TOP.indexOf(segs[0]) === -1) segs.shift();
    var name = segs.length ? segs[segs.length - 1] : "recommend";
    // 画面名がパスの最後のセグメントと違う画面（app.js の SCREENS。/recommend/tag は tagged）。合わせないと
    // 先に飛ばした取得が /api/screen/tag の 404 になり、コンソールにエラーが出ていた（2026-10-18 に e2e で気づいた）
    if (name === "tag") name = "tagged";
    // **app.jsのDOMContentLoadedが渡すsearchと同じ形にする**
    // (location.search.replace(/^\?/, "")、トークンの除去なし)。
    var qs = location.search.replace(/^\?/, "");
    window.__prefetchKey = name + "?" + qs;
    window.__prefetch = fetch(
      T.api + "/api/screen/" + name + (qs ? "?" + qs : ""),
      {credentials: "include"}
    ).then(function (r) { return r.json(); }).catch(function () { return null; });
  } catch (e) {}
})();
