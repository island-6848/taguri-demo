"use strict";
/* たぐり ── どちらの版の画面か（デモ版・サービス版）を決める。
 *
 * デモ版とサービス版は**別のAPIサーバー（別の Render サービス・別の保存先）**に
 * つながる（docs/editions.md）。画面のファイルは同じものを使い回し、
 * 開いたURLで行き先を決める:
 *   /taguri-demo/       … デモ版（見本の記録入り。入力は消えてよい）
 *   /taguri-demo/app/   … サービス版（記録が残る）
 * サーバーが違うので Cookie も別になり、デモで作った記録がサービス版に混ざることはない。
 *
 * サービス版の api は Pages の公開時に、リポジトリの変数 TAGURI_SERVICE_API で
 * 埋める（.github/workflows/pages.yml）。空のあいだは「準備中」を出す。 */
(function () {
  const EDITIONS = {
    service: {base: "/taguri-demo/app", api: "__TAGURI_SERVICE_API__"},
    demo: {base: "/taguri-demo", api: "https://taguri-demo.onrender.com"},
  };
  const p = location.pathname;
  const name = (p === EDITIONS.service.base || p.indexOf(EDITIONS.service.base + "/") === 0)
    ? "service" : "demo";
  const ed = EDITIONS[name];
  // 置き換えられていない（変数が未設定）ときは空にする
  const api = /^https:\/\//.test(ed.api) ? ed.api.replace(/\/+$/, "") : "";
  window.TAGURI = {edition: name, api: api, base: ed.base, demoBase: EDITIONS.demo.base};
})();
