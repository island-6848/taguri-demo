// 「眺める」の storyline の図を描く（app.js の fixupStoryline が、画面に #sl-data が来るたびに読み込み直す）。
// 前は app.js の中の文字列を <script> に入れて動かしていたが、それには CSP の 'unsafe-inline' が要る（#155）。
// storyline.py の SCRIPT を scripts/write_icons.py が書き出したもの（手で直さない）。

(function () {
  const host = document.getElementById("sl");
  const src = document.getElementById("sl-data");
  if (!host || !src || typeof d3 === "undefined") return;
  const D = JSON.parse(src.textContent);
  // **左に名前のための余白を取る。**（正解の図も左端が名前の欄になっている）
  // padT は世界の名札を置くぶん取る（名札は先頭の線の 16px 上に出る）
  const left = 84, padR = 18, padT = 30, axisH = 26;
  const h = D.height + padT + axisH + 26;
  // **横幅は「束が入り切る幅」で決める。** 入れ物に合わせて縮めると、束が詰まった
  // ところで水平区間が消える（入れ物は横に流れる）
  const w = Math.max(D.width, host.clientWidth || 900);
  // 位置は Python 側で決めてある（日付の順は保ち、詰まるところだけ広げてある）
  let tr = d3.zoomIdentity;
  const px = dt => D.X[dt];
  const xz = dt => tr.applyX(px(dt));
  const cls = d => "w" + Math.min(d.loc, 2);

  // **viewBox で縮めない。** 縮めると幅を広げた意味が消える（入れ物を横に流す）
  const root = d3.select(host).append("svg")
    .attr("width", w).attr("height", h);
  const svg = root.append("g").attr("transform", "translate(0," + padT + ")");
  const clip = svg.append("clipPath").attr("id", "sl-clip");
  clip.append("rect").attr("x", 0).attr("y", -padT)
    .attr("width", w).attr("height", h);
  const plot = svg.append("g").attr("clip-path", "url(#sl-clip)");
  const gLb = plot.append("g");        // 場所の名前（面の縁に沿う）
  const gSes = plot.append("g");       // 束
  const gLine = plot.append("g");      // 線
  // **名前は切り取る層の外に置く。** 中に置くと、左の余白へはみ出した名前が切れる
  const gName = svg.append("g");
  const gDot = plot.append("g");       // 束に入っている印（線の上）
  const gSt = plot.append("g");        // 作品名
  const ax = svg.append("g").attr("class", "ax")
    .attr("transform", "translate(0," + (D.height + 12) + ")");
  const tip = d3.select("body").append("div").attr("class", "sl-tip")
    .style("display", "none");

  // **線は水平に走り、高さが変わるところだけ S 字で移る。**（起案者の指摘・2026-08-25）
  //
  // 前は各場面の点を `curveMonotoneX` で結んでいたので、**点ごとに高さが違うぶん
  // 線がずっと斜めに流れていた。** storyline の図は地下鉄の路線図に近く、
  // **平らに走っている時間があって、移るときだけ短く上下する。** 平らな区間があるから
  // 「この人とこの人がしばらく一緒だった」が読めるので、これは見た目の好みではない。
  //
  // 移り変わりは横に TW px だけ使い、両端で水平に接する 3 次ベジエにする
  // （制御点を同じ高さに置くと、接続部が折れずに滑らかにつながる）。
  const TW = 26;
  function pathOf(l) {
    const P = l.pts.map(p => ({ x: xz(p.date), y: p.y }));
    if (!P.length) return "";
    // 束に居るあいだは少し前後へ伸ばす（一緒に居た幅を見せる）
    let d = "M" + (P[0].x - D.runPx).toFixed(1) + "," + P[0].y.toFixed(1);
    for (let i = 0; i < P.length; i++) {
      const cur = P[i], nxt = P[i + 1];
      d += "L" + (cur.x + D.runPx).toFixed(1) + "," + cur.y.toFixed(1);
      if (!nxt) break;
      const gap = (nxt.x - D.runPx) - (cur.x + D.runPx);
      const tw = Math.max(Math.min(TW, gap), 0);
      const x0 = (nxt.x - D.runPx) - tw;
      if (x0 > cur.x + D.runPx) d += "L" + x0.toFixed(1) + "," + cur.y.toFixed(1);
      if (Math.abs(nxt.y - cur.y) < 0.4) {
        d += "L" + (nxt.x - D.runPx).toFixed(1) + "," + nxt.y.toFixed(1);
      } else {
        const xm = (x0 + (nxt.x - D.runPx)) / 2;
        d += "C" + xm.toFixed(1) + "," + cur.y.toFixed(1)
           + " " + xm.toFixed(1) + "," + nxt.y.toFixed(1)
           + " " + (nxt.x - D.runPx).toFixed(1) + "," + nxt.y.toFixed(1);
      }
    }
    return d;
  }
  const lines = D.lines.map(l => ({ ...l }));

  // 選んだ人の集合。**`draw()` より前に置く** ── `draw()` の最後で `paint()` を
  // 呼ぶので、後ろに置くと初回の描画で ReferenceError になる（`const` は
  // 初期化より前に触れない）。`node --check` は構文しか見ないので通ってしまう
  // 選んだ人の集合。**空なら全部ふつうに描く**
  const chosen = new Set();
  function paint() {
    const on = chosen.size > 0;
    gLine.selectAll("path")
      .classed("hot", d => on && chosen.has(d.name))
      .classed("dim", d => on && !chosen.has(d.name));
    gName.selectAll("text").classed("dim", d => on && !chosen.has(d.l ? d.l.name : d.name));
    gDot.selectAll("circle").classed("dim", d => on && !chosen.has(d.name));
  }
  function pick(name) {
    if (chosen.has(name)) chosen.delete(name); else chosen.add(name);
    paint();
  }
  // **背景を押すと解除する**（参照実装と同じ）
  root.on("click", () => { chosen.clear(); paint(); });

  function draw() {
    // **年の変わり目だけを置く。** 位置を歪めてあるので普通の軸は引けない
    ax.selectAll("text").data(D.ticks).join("text")
      .attr("x", t => tr.applyX(t.x)).attr("y", 14).attr("text-anchor", "start")
      .text(t => t.label);
    ax.selectAll("line").data(D.ticks).join("line")
      .attr("x1", t => tr.applyX(t.x)).attr("x2", t => tr.applyX(t.x))
      .attr("y1", -D.height - 8).attr("y2", 4);
    // **世界の名札は水平に、その世界の左上へ置く。**
    // 背景の帯はやめたので（起案者の指示・2026-08-25）、どの線がどの世界かを示すのは
    // **線の色とこの名札だけ**である。帯は線の色と並びで既に読めることを塗り直して
    // いただけで、しかも論文で背景が指すのは「場所」なので、
    // **「この人たちはこの場所に居た」と誤読される**ほうが大きかった
    gLb.selectAll("text").data(D.worlds).join("text")
      .attr("class", d => "loclb " + cls(d))
      .attr("x", d => tr.applyX(px(d.lx)) - D.runPx)
      .attr("y", d => d.ly - 16)
      .text(d => (d.loc + 1) + " つめの世界 ── " + d.n_people + " 人");
    // **束はやわらかい影にする。** 正解の図は角のある枠ではなく、束の後ろにぼんやりした
    // 影を敷いている ── 枠で囲うと「囲われた集合」に見え、線が主役でなくなる
    gSes.selectAll("ellipse").data(D.sessions).join("ellipse")
      .attr("class", "ses")
      .attr("cx", s => xz(s.date))
      .attr("cy", s => (s.y0 + s.y1) / 2)
      .attr("rx", D.runPx + 11)
      .attr("ry", s => (s.y1 - s.y0) / 2 + 11)
      .on("mouseenter", (ev, s) => tip.style("display", "block")
        .text(s.date + "｜" + s.titles.join(" / ") + "｜この日に一緒だった " + s.n + " 名"))
      .on("mousemove", ev => tip.style("left", (ev.clientX + 14) + "px")
        .style("top", (ev.clientY + 14) + "px"))
      .on("mouseleave", () => tip.style("display", "none"))
      .on("click", (ev, s) => {
        const a = s.anchors[0];
        location.href = D.rowHref + "&w=" + encodeURIComponent(a) + "#w-" + a;
      });
    // **名札は近すぎるものを出さない。** 前半は束が詰まっているので、全部出すと
    // 名前が重なって読めない（束に触れれば作品名は出る）
    let lastX = -1e9;
    const shown = D.sessions.slice().sort((a, b) => px(a.date) - px(b.date))
      .filter(sx => { const X = tr.applyX(px(sx.date));
                      if (X - lastX < 64) return false; lastX = X; return true; });
    gSt.selectAll("text").data(shown).join("text")
      .attr("class", "st").attr("text-anchor", "middle")
      .attr("x", s => xz(s.date))
      .attr("y", s => s.y0 - 15)
      .text(s => s.titles[0].length > 13 ? s.titles[0].slice(0, 12) + "…" : s.titles[0]);
    gLine.selectAll("path").data(lines).join("path")
      .attr("class", d => "ln " + cls(d))
      .attr("id", (d, i) => "slln" + i)
      .attr("d", d => pathOf(d))
      .on("mouseenter", (ev, l) => tip.style("display", "block")
        .text(l.name + "｜" + l.n + " 回、" + l.from + " から " + l.to + " まで"))
      .on("mousemove", ev => tip.style("left", (ev.clientX + 14) + "px")
        .style("top", (ev.clientY + 14) + "px"))
      .on("mouseleave", () => tip.style("display", "none"))
      // **押して選ぶ**（参照実装の toggleCharacterHighlight）。触れるだけの強調は
      // **2 人を見比べられない** ── 手を離すと消えるので、追いたい線を並べて見られない。
      // 複数選べて、背景を押すと解除する（参照実装と同じ約束）
      .on("click", (ev, l) => { ev.stopPropagation(); pick(l.name); });
    // **束に入った日に ● を打つ。**（起案者の指示・2026-08-25）
    //
    // 線が水平に走る形にしたので、**どこが「一緒に出た日」でどこが「通り過ぎただけ」
    // なのかが線の形からは分からない** ── 束の影は重なった塊にしか見えず、1 人ずつでは
    // 読めない。**点を打つと、その人がその日に出ていたことが 1 本ずつ分かる。**
    //
    // 通っているだけの点には打たない（`on` が偽）。打つと、居なかった日にも
    // 居たように見える
    const dots = [];
    lines.forEach(l => l.pts.forEach(p => {
      if (p.on) dots.push({ name: l.name, loc: l.loc, date: p.date, y: p.y });
    }));
    gDot.selectAll("circle").data(dots).join("circle")
      .attr("class", d => "dot " + cls(d))
      .attr("cx", d => xz(d.date)).attr("cy", d => d.y).attr("r", 3.1);

    // **名前は線の始まりの左に置く。**（起案者の指摘・2026-08-25）
    //
    // 線に沿わせる（textPath）のをやめた ── 正解の図は**左端に名前を縦に並べ、線の
    // 高さに合わせている。** 線に沿わせると、線が動くたびに名前の位置も動いて追えず、
    // **どの高さが誰なのかを最初に掴めない。** 線が平らに走る形にしたので、始まりの
    // 高さがそのままその人の「持ち場」になる。
    // **名前がぶつかるので、ぶつかる分だけ左へ段をずらす。**
    // 束の中は 8.4px 間隔で文字は 10.5px あるため、同じ束から始まる線の名前は必ず重なる。
    // **高さは動かさない** ── 名前の高さがその人の線の高さであることが、この図で
    // 名前と線を結びつける唯一の手がかりだからである。段は 3 つまでで、
    // それでも収まらない分は出さない（線に触れれば名前は出る）
    const COLW = 46, VMIN = 11.5, COLS = 3;
    const taken = [[], [], []];
    const labelled = [];
    lines.slice().sort((a, b) => a.pts[0].y - b.pts[0].y).forEach(l => {
      const y = l.pts[0].y, x0 = xz(l.pts[0].date) - D.runPx - 5;
      for (let c = 0; c < COLS; c++) {
        if (taken[c].every(v => Math.abs(v - y) >= VMIN)) {
          taken[c].push(y);
          // **画面の外へは出さない。** 段をずらしても左端より外なら、そこで留める
          labelled.push({ l: l, x: Math.max(x0 - c * COLW, 38), y: y });
          break;
        }
      }
    });
    gName.selectAll("text").data(labelled, d => d.l.name).join("text")
      .attr("class", d => "nm " + cls(d.l))
      .attr("text-anchor", "end").attr("dy", 3.5)
      .attr("x", d => d.x).attr("y", d => d.y)
      .text(d => d.l.name.length > 9 ? d.l.name.slice(0, 8) + "…" : d.l.name);
    if (typeof paint === "function") paint();   // 拡大縮小で描き直しても選択を保つ
  }
  draw();

  // **指の操作は d3 に渡さない。** 渡すと図の上で横にも縦にも動かせなくなる（起案者の指摘 2026-10-24「図をスマホでもスクロール
  // できるようにして」）。スマホは入れ物（.sl）の横のスクロールで時間をたどり、拡大縮小はマウスのドラッグとホイールだけにする
  root.call(d3.zoom().scaleExtent([1, 30]).touchable(() => false)
    .translateExtent([[left, 0], [w - padR, h]])
    .extent([[left, 0], [w - padR, h]])
    // **位置はもう決まっているので、拡大縮小は写した px の上に掛ける**
    .on("zoom", ev => { tr = ev.transform; draw(); }));
})();
