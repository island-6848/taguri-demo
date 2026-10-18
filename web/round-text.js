// 丸の中の字は丸ゴシック（起案者の指示 2026-10-18「丸のなかの文字だけ丸ゴシックにできる？」→ 角が丸い押し口・札）。
// 両端が半円の枠（border-radius が高さの半分以上で、枠線か地の色があるもの）に data-round を付け、fonts.css が
// その中の字を Zen丸ゴシックにする。角の丸さは style.css・theme.css が部品ごとに決め、画面の幅でも変わるので、
// クラスの名前を並べず、描かれた形を見て決める（名前の一覧は直すたびに漏れる）。評価の判子（.rb・.stamp）と
// 図（svg）は外す。ログインの画面のように app.js を読まない頁でも動くよう、ひとつのファイルにしてある。
(function () {
  "use strict";
  const PICK = "button,a,span,b,small,label,li,select,input[type=button],input[type=submit],input[type=reset]";
  const SKIP = ".rb, .rb *, .stamp, .stamp *, svg, svg *";
  function boxed(cs) {
    if (parseFloat(cs.borderTopWidth) > 0 && cs.borderTopStyle !== "none") return true;
    const bg = cs.backgroundColor;
    return bg && bg !== "transparent" && !/^rgba\(.*,\s*0\)$/.test(bg);
  }
  function round(el) {
    if (el.matches(SKIP)) return false;
    const cs = getComputedStyle(el);
    if (cs.display === "inline" && el.tagName !== "BUTTON") return false;   // 枠を持たない字の並び
    if (!boxed(cs)) return false;
    const r = cs.borderTopLeftRadius, h = el.getBoundingClientRect().height;
    if (r.endsWith("%")) return parseFloat(r) >= 50;
    const px = parseFloat(r) || 0;
    // 畳んだ欄の中など、まだ描かれていない（高さ 0）ものは、丸ごと丸める指定（99px など）かどうかで見る
    return h > 0 ? px >= h / 2 - 1 : px >= 99;
  }
  function mark(root) {
    const list = root.nodeType === 1 ? [root, ...root.querySelectorAll(PICK)] : [];
    // 先に全部の形を読み、あとでまとめて印を書く（読みと書きを交互にすると、そのたびに組み直しが走る）
    const want = list.filter(el => el.matches(PICK)).map(el => [el, round(el)]);
    for (const [el, on] of want) {
      if (on && !el.hasAttribute("data-round")) el.setAttribute("data-round", "");
      else if (!on && el.hasAttribute("data-round")) el.removeAttribute("data-round");
    }
  }
  let queued = new Set(), timer = 0;
  function flush() {
    timer = 0;
    const roots = [...queued]; queued = new Set();
    for (const r of roots) if (r.isConnected) mark(r);
  }
  function later(node) {
    queued.add(node);
    if (!timer) timer = requestAnimationFrame(flush);
  }
  function start() {
    mark(document.body);
    new MutationObserver(ms => {
      for (const m of ms) {
        if (m.type === "childList") m.addedNodes.forEach(n => n.nodeType === 1 && later(n));
        else if (m.target.nodeType === 1) later(m.target);   // 押した印などで形が変わったとき
      }
    }).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ["class", "open"]});
    let rs = 0;
    addEventListener("resize", () => { clearTimeout(rs); rs = setTimeout(() => mark(document.body), 200); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
