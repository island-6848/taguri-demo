// 画面に出す全角のカッコ（ ）を、半角の ( ) にそろえる（起案者の指示 2026-10-18「サイト全体で全角のカッコを使ってる
// ところは、半角に変えて」）。
// 文言は画面のコード（cloudflare/src・web/app.js）・作り置きのカード（Python）・取得した公演名などあちこちから来るうえ、
// 公演名や予約メールを読む正規表現は全角と半角の両方に当たるよう全角のカッコを使っている。ソースを一括で置き換えると
// 読み取りが壊れるので、表示する直前に 1 か所で変える。変えないもの: 文字を書く欄（input・textarea）と、本人が書いた
// 感想・メモの表示（.int・.wnt・.nnv）、コード（script・style・code・pre）。ログインの頁など app.js を読まない頁でも
// 同じに動くよう、ひとつのファイルにしてどの頁からも読む。
(function () {
  "use strict";
  const RE = /[（）]/g, MAP = {"（": "(", "）": ")"};
  const SKIP = "script,style,code,pre,textarea,input,[contenteditable],.int,.wnt,.nnv";
  const ATTRS = ["title", "aria-label", "placeholder", "alt"];
  const swap = s => s.replace(RE, c => MAP[c]);
  const HAS = /[（）]/;
  function text(node) {
    const p = node.parentElement;
    if (!p || p.closest(SKIP)) return;
    const v = node.nodeValue;
    if (v && HAS.test(v)) node.nodeValue = swap(v);
  }
  function attrs(el) {
    if (el.closest(SKIP) && !el.matches("input,textarea")) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (v && /[（）]/.test(v)) el.setAttribute(a, swap(v));
    }
  }
  function walk(root) {
    if (root.nodeType === 3) return text(root);
    if (root.nodeType !== 1) return;
    attrs(root);
    root.querySelectorAll("[title],[aria-label],[placeholder],[alt]").forEach(attrs);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) text(n);
  }
  function start() {
    if (/[（）]/.test(document.title)) document.title = swap(document.title);
    walk(document.body);
    // 画面の書き換え（app.js が描く画面・ログインの案内の文）にも当てる。変えた字はもう全角を含まないので、
    // 自分の書き換えでまた呼ばれても何もしない
    new MutationObserver(ms => {
      for (const m of ms) {
        if (m.type === "characterData") text(m.target);
        else if (m.type === "attributes") attrs(m.target);
        else m.addedNodes.forEach(walk);
      }
      if (/[（）]/.test(document.title)) document.title = swap(document.title);
    }).observe(document.documentElement, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
})();
