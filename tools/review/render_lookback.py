#!/usr/bin/env python3
"""記録を見返す画面のモック HTML を組む（build_lookback.py の出力を読む）。

  python3 tools/review/build_lookback.py && python3 tools/review/render_lookback.py

出力の data/review/lookback.html は**観劇履歴そのものなので端末内だけに置く**
（data/review/ は .gitignore 済み）。ブラウザで開いて確かめる。

図の形と色は dataviz の手順に従う ── 形を先に決め、色は最後。
配色は検証済みの既定パレット（categorical 4 スロット・両モードで全チェック PASS）。
明モードはコントラストが 3:1 を下回るスロットがあるため、**直接ラベルと表の姿を必ず出す**。
"""
import json, html, collections, sys
from pathlib import Path

# **判子と封蝋の版は `render_recommend` が持っている 1 枚を使う。**
# `filter:url(#…)` は参照先が無いとその要素ごと描かれないので、版を 2 つに分けない
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_recommend as RR                                        # noqa: E402

# **絶対パスを書かない。** 起案者の作業場所を直に書いていたため、コードを別の場所へ
# 写しても本人の `lookback.json` を読み、**記録を空にしても本人の分析が画面に出ていた**
# （2026-08-24 の実測）。**他人の端末には、そもそもこのパスが無い。**
ROOT = Path(__file__).resolve().parents[2]
LOOKBACK = ROOT / "data/review/lookback.json"
D = json.loads(LOOKBACK.read_text("utf-8")) if LOOKBACK.exists() else {}
E = lambda s: html.escape(str(s))

ROLE_ORDER = ["出演", "演出", "脚本", "美術", "照明", "音響", "衣裳", "舞台監督",
              "翻訳", "音楽", "演出助手", "宣伝美術", "映像", "スタッフ"]


# **「上演日数の偏り」「料金」の 2 枚は外した**（起案者の指示・2026-08-26 ──「『比べる』
# の…『上演日数の偏り』『料金』…は消してよい」）。図そのもの（旧 `run_panel`／
# `price_panel`）を削除した ── `cast_rows`（`compare.py`）と違って単体で使う道が
# 無く、`body()` から外すと呼ぶ先が無くなるので、枠だけ残す理由が無い。
# `D["compare"]["runs"]`／`["price"]` の計算自体（`build_lookback.py`）は変えていない
# ── データを取るところと画面に出すところは別の関心である。
#
# ---------------------------------------------------------------- 気づき → 意味 → 行動
def action_panel():
    mixed = sorted((dict(r, role=k) for k, v in D["roster"].items() for r in v
                    if r["faces"] >= 3 and not r["declared"]), key=lambda r: -r["n"])[:3]
    names = "・".join(f"{r['name']}（{r['role']}）" for r in mixed) or "該当なし"
    yr = D["years"]["rows"]
    a24 = next((r for r in yr if r["year"] == "2024"), yr[0])
    last = yr[-1]

    # **材料の無い行は、作らずに飛ばす。**
    #
    # **上演日数・料金から読み取れた 2 行は外した**（起案者の指示・2026-08-26 ──
    # 「『比べる』の…『上演日数の偏り』『料金』…は消してよい」）。その 2 軸の
    # 表そのもの（旧 `run_panel`／`price_panel`）を削除したので、**その表を指す
    # 「気づき」を残すと、根拠の表が無いまま数字だけが出ることになる。**
    #
    # **材料の有無で行を組み立てる。** 帯の切り方は記録が増えれば変わるので、
    # 「この帯がある」と決め打ちしないことが直しである。
    rows = [
        (f"登録していないのに繰り返し観ている名前が {len(D['unspoken']['rows'])} 人いる"
         f"（劇場と座組と業界での出やすさを引いた残り）",
         # **この欄は `E()` で escape して出す。** 文の中に `**` や `<b>` を書いても
         # 記号のまま画面に出る（実際に `**引く前は…**` が星印ごと出ていた）。
         # 強調が要るなら列ごと組み方を変えることになるので、ここは素の文で書く。
         "追っている自覚がないまま、繰り返し出会っている。引く前は 63 人いたが、"
         "いちばん多い劇場を引いた時点で大半が消えた ── 下の 4 節に 1 人ずつ出した",
         "お気に入りに登録する"),
        (f"「難しい」「苦しい」を褒め言葉として使っている（感想 {D['words']['notes']} 件のうち 4 件）",
         "他人のクチコミでは、同じ語が否定として書かれる",
         "クチコミの読み替えに使う"),
    ]
    if a24 and last:
        rows.append(
            (f"再訪率が 2024 年 {a24['rate']:.0%} → {last['year']} 年 {last['rate']:.0%}",
             "同じ座組を繰り返し観ていた時期から、広げている時期に移っている。狭まってはいない",
             None))
    out = []
    for ins, mean, act in rows:
        # **押すものが無い行にも、読む人の言葉で理由を書く。** 以前は「行動なし
        # （監視の指標）」と出していたが、**「指標」も「監視」も作る側の言葉**で、
        # 読む人には「なぜこの行だけ押せないのか」が分からない。
        cell = (f'<button class="btn">{E(act)}</button>' if act
                else '<span class="dim">押すものはありません ── '
                     'せまくなっていないかを、ときどき見るための行です</span>')
        out.append(f'<tr><td class="ins">{E(ins)}</td><td class="mean">{E(mean)}</td>'
                   f'<td class="act">{cell}</td></tr>')
    return f"""<section class="card wide">
<h2>気づきに、次の行動を 1 つ付ける</h2>
<p class="why">上の図から読み取れた偏りを 1 行ずつ並べ、<b>それぞれに次の行動を 1 つ付けています。
押すと、次のおすすめの条件が変わります。</b>押さなくても構いません。</p>
<table class="tbl"><thead><tr><th>気づき（偏り）</th><th>何を意味するか</th><th>取れる行動</th></tr></thead>
<tbody>{''.join(out)}</tbody></table>
<p class="note">押した設定は「おすすめ」の画面にそのまま効きます。
行動の付いていない行は、いまのところ押す口がありません。</p></section>"""


# --------------------------------- まだ言葉になっていない作り手（検証 033 追記 4）
def unspoken_panel():
    """誰のどの問いに答えるか ── 「自分では言えなかった名前を、言葉にして登録できるか」。

    **1 人 1 行にする。** 集計の図にすると 1 件ずつが識別できず、振り返りには使えない。
    **「好み」と書かない** ── 繰り返し観ている裏方の ◎ 率は 0.37 で全体の基準 0.378 と同じで、
    書けるのは「N 本観ている」までです。
    """
    U = D["unspoken"]
    rows = []
    for r in U["rows"]:
        up = r["upcoming"]
        if up:
            act = (f'<button class="btn">お気に入りに登録する</button>'
                   f'<div class="up">これから <b>{len(up)} 件</b> ── '
                   + " ／ ".join(f'{E(u["title"][:22])}（{E(u["role"])}・{E(u["theater"][:14])}）'
                                 for u in up[:3]) + "</div>")
        else:
            act = ('<button class="btn">お気に入りに登録する</button>'
                   '<div class="up dim">いま出ている公演は無い（登録すれば次に出たとき知らせる）</div>')
        ven = " ／ ".join(f'{E(v["venue"][:20])} {v["n"]}' for v in r["venues"][:3])
        rows.append(
            f'<tr><td class="nm"><b>{E(r["name"])}</b><span class="rl">{E(r["role"])}</span></td>'
            f'<td class="num">{r["n"]} 本</td>'
            f'<td class="num dim">{r["maru"]}/{r["graded"]}</td>'
            f'<td class="vn"><span class="main">{E(r["main_venue"][:20])} {r["main_n"]} 本</span>'
            f'<span class="out">ほかの劇場 {r["outside"]} 本</span>'
            f'<div class="note2">{ven}</div></td>'
            f'<td class="act">{act}</td></tr>')
    # 集計して初めて見える示唆を 2 つ。**1 人 1 行では出ない量**である（起案者の指摘）。
    CAUSE = [("同じ座組で説明がつく", "s1"), ("同じ劇場で説明がつく", "s2"),
             ("業界で出やすいだけ", "s-oth"), ("すでに登録している", "s4"),
             ("人そのものが残った", "s3")]
    tot = max(U["n_all"], 1)
    seg = "".join(
        f'<span class="sg {cls}" style="width:{U["by_cause"].get(k, 0) / tot * 100:.1f}%" '
        f'title="{E(k)} {U["by_cause"].get(k, 0)} 人"></span>' for k, cls in CAUSE)
    leg = " ".join(f'<span class="lg"><i class="sw {cls}"></i>{E(k)} '
                   f'<b>{U["by_cause"].get(k, 0)}</b></span>' for k, cls in CAUSE)
    ROLES = ["出演", "作り手（演出・脚本）", "裏方・制作"]
    dec, got = U["declared_roles"], U["found_roles"]
    trs = "".join(
        f'<tr><td class="nm">{E(r)}</td>'
        f'<td class="num">{dec.get(r, 0)} 人</td>'
        f'<td class="num strong">{got.get(r, 0)} 人</td></tr>' for r in ROLES)
    agg = f"""<div class="agg">
<div class="ins2"><b>集計して分かること ①</b> ── あなたの「同じ人に何度も出会う」は、
<b>その人ではなく座組と劇場で起きている。</b>3 本以上観た作り手 {U["n_all"]} 人のうち、
<b>{U["by_cause"].get("同じ座組で説明がつく", 0) + U["by_cause"].get("同じ劇場で説明がつく", 0)} 人
（{(U["by_cause"].get("同じ座組で説明がつく", 0) + U["by_cause"].get("同じ劇場で説明がつく", 0)) / tot * 100:.0f}%）
が同じ顔ぶれか同じ劇場で説明がつきます。</b>人そのものが残るのは {U["by_cause"].get("人そのものが残った", 0)} 人だけです。
<div class="segbar">{seg}</div><div class="legend">{leg}</div></div>
<div class="ins2"><b>集計して分かること ②</b> ── <b>言葉にしている領域と、実際に繰り返し出会っている領域がずれている。</b>
登録した名前 {U["n_declared"]} 人は出演と作り手に寄っているが、<b>残ったのは裏方・制作が最も多い。</b>
<table class="tbl mini"><thead><tr><th>役職</th><th class="num">登録している</th>
<th class="num">繰り返し出会っている</th></tr></thead><tbody>{trs}</tbody></table>
<span class="note2">登録は人物 {U["n_declared"]} 人ぶん（団体・題材は別枠）。右列は上の絞り込みで残った {len(U["rows"])} 人。</span></div>
</div>"""
    f = U["funnel"]
    order = ["対象（3 本以上で観た作り手）", "申告済みなので外した",
             "業界で出やすいだけなので外した", "同じ座組の繰り返しなので外した",
             "いちばん多い劇場で説明がつくので外した"]
    fun = "".join(f'<li><span class="k">{E(k)}</span><span class="v">{f.get(k, 0)}</span></li>'
                  for k in order if k in f)
    return f"""<section class="card wide">
<h2>まだ言葉になっていない作り手</h2>
<p class="why"><b>お気に入りに登録していないのに、繰り返し観ている作り手です。</b>
よく行く劇場の常連や、同じ座組で続けて出ている方、業界全体で出番の多い方を除いた残りを
出しています ── そうしないと、劇場や座組を選んだ結果がそのまま並ぶだけになります。</p>
<p class="why">下の漏斗は、何人がどの段で外れて何人残ったかです。</p>
{agg}
<ul class="funnel">{fun}<li class="last"><span class="k">残った</span>
<span class="v">{len(U["rows"])} 人</span></li></ul>
<table class="tbl"><thead><tr><th>作り手</th><th class="num">観た</th><th class="num">◎/評価済</th>
<th>劇場の散らばり</th><th>取れる行動</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="note">ここに出ているのは「この方の仕事を何本観ているか」までで、
<b>好きかどうかを決めるのはご本人です。</b>
見るだけではおすすめは変わりません ── <b>「お気に入りに登録する」を押すと、
その名前の公演が件数の制限も条件も付けずに新着へ出るようになります。</b><br>
業界での出番の多さは、これから観られる公演 {U["n_cand"]} 件に何回出てくるかで数えています。
</p></section>"""


# ---------------------------------------------------------------- 4. まだ比較できない軸
def rest_panel():
    return f"""<section class="card fail">
<h2>この画面で比べていないもの</h2>
<p class="note">この画面で比べていない軸です。<br>
<b>上演時期（月・季節）</b> ── 比べる相手が先の数か月ぶんの公演しかないので、
月ごとの割合を並べても相手側の偏りが出るだけになります。<br>
<b>客席数</b> ── 比べる相手の側の座席数がそろっていません。<br>
<b>地域・団体</b> ── 数字は出せますが、出していません。</p>
</section>"""

STYLE = """
*{box-sizing:border-box}
:root{color-scheme:light;
 /* ---- 地と紙 ---------------------------------------------------------------
    **読むところだけを紙の色で抜き、その外側は客席の壁の色にする。** 灰に緑を寄せて
    あるのは、紙の白を際立たせるためである（黄を寄せると紙が沈む）。            */
 --plane:#e7eae6;--surf:#f8f9f6;--ink:#191b18;--ink2:#4e534d;--mute:#828880;
 --grid:#dde2d9;--base:#c2c9bd;--ring:rgba(25,27,24,.13);
 /* ---- インクは 2 本だけ ------------------------------------------------------
    **`--acc`（藍）は押せるところと書けるところにしか使わない。**
    **`--curtain`（幕のえんじ）は識別にしか使わない** ── 左の帯・年の耳・評価の印。
    以前は `--acc` の青 1 色が「押せる」「現在地」「見出しの強調」をすべて担っており、
    **青が出てくるたびに押せるかどうかを確かめることになっていた。**             */
 --acc:#26467d;--curtain:#7a1e2b;--curtain-w:#f6efe9;
 /* 封蝋。**約束の印にだけ使う**（お気に入り＝件数も条件も付けずに必ず出す約束） */
 --wax:#8f2b3a;--wax-hi:#c2596a;
 /* ---- 値の色。**意匠の色とは別に持つ** ── ◎ と × は好みの値であって飾りではない */
 --pos:#1e6b48;--neg:#8a3b3b;--good:#1e6b48;--warn:#8a6d2a;
 --s1:#2f5590;--s2:#b1592c;--s3:#1d7d59;--s4:#8a6d2a;
 --oth:#c2c9bd;--unk:#dde2d9;--deemp:#c2c9bd;
 /* ---- 明朝。**端末にあるものだけを並べる** ── 外部からフォントを読み込むと、
    端末内のデータだけで作るという守り（企画書 5 章）が 1 か所破れる。
    **どれも無い端末ではゴシックに落ちる**ので、帳面らしさは書体ではなく
    余白・罫・日付・印で作り、書体は乗ったときに効く上乗せとして扱う。          */
 --mincho:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
 /* 判子の刷り。明るい地では紙に染むように重ね、暗い地では抜くように重ねる */
 --stamp-blend:multiply;--stamp-ink:.88}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){color-scheme:dark;
 --plane:#101210;--surf:#191c18;--ink:#eef0ec;--ink2:#b6bbb2;--mute:#7f857c;
 --grid:#2c302b;--base:#3c423b;--ring:rgba(238,240,236,.12);
 /* **暗い地では幕のえんじが沈むので明るい側へ振る。**紙も白くしない（暗い部屋で読めない） */
 --acc:#86aae8;--curtain:#b03a4a;--curtain-w:#fbf1ef;
 --wax:#b8404f;--wax-hi:#e0808c;
 --pos:#3f9a6f;--neg:#c86a6a;--good:#3f9a6f;--warn:#c9a552;
 --s1:#6f9ad8;--s2:#d07a4a;--s3:#3f9a6f;--s4:#c9a552;
 --oth:#4e534d;--unk:#2c302b;--deemp:#4e534d;
 --stamp-blend:screen;--stamp-ink:.94}}
:root[data-theme=dark]{color-scheme:dark;
 --plane:#101210;--surf:#191c18;--ink:#eef0ec;--ink2:#b6bbb2;--mute:#7f857c;
 --grid:#2c302b;--base:#3c423b;--ring:rgba(238,240,236,.12);
 /* **暗い地では幕のえんじが沈むので明るい側へ振る。**紙も白くしない（暗い部屋で読めない） */
 --acc:#86aae8;--curtain:#b03a4a;--curtain-w:#fbf1ef;
 --wax:#b8404f;--wax-hi:#e0808c;
 --pos:#3f9a6f;--neg:#c86a6a;--good:#3f9a6f;--warn:#c9a552;
 --s1:#6f9ad8;--s2:#d07a4a;--s3:#3f9a6f;--s4:#c9a552;
 --oth:#4e534d;--unk:#2c302b;--deemp:#4e534d;
 --stamp-blend:screen;--stamp-ink:.94}
body{margin:0;padding:32px 20px 72px;background:var(--plane);color:var(--ink);
 font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.7;font-size:15px}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:24px;margin:0 0 4px;letter-spacing:.01em}
.sub{color:var(--ink2);margin:0 0 28px;font-size:14px}
.card{background:var(--surf);border:1px solid var(--ring);border-radius:14px;
 padding:24px 26px 20px;margin:0 0 20px}
h2{font-size:17px;margin:0 0 10px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.badge{font-size:11px;font-weight:600;padding:2px 9px;border-radius:99px;border:1px solid var(--ring);color:var(--ink2)}
.badge.ok{color:var(--good);border-color:#0ca30c55}
.badge.part{color:var(--ink2)}
.badge.no{color:#d03b3b;border-color:#d03b3b55}
.lead{margin:0 0 14px;color:var(--ink2);font-size:14px}
.agg{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:0 0 18px}
@media(max-width:720px){.agg{grid-template-columns:1fr}}
.ins2{background:var(--plane);border:1px solid var(--ring);border-radius:12px;
 padding:14px 16px;font-size:13px;line-height:1.7;color:var(--ink2)}
.segbar{display:flex;height:12px;border-radius:6px;overflow:hidden;margin:10px 0 8px;background:var(--grid)}
.tbl.mini{margin:8px 0 4px;font-size:12.5px}
.tbl.mini th,.tbl.mini td{padding:3px 8px}
.funnel{list-style:none;margin:0 0 16px;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.funnel li{display:flex;gap:8px;align-items:baseline;border:1px solid var(--ring);
 border-radius:99px;padding:3px 12px;font-size:12.5px;color:var(--ink2)}
.funnel li.last{border-color:var(--acc);color:var(--ink)}
.funnel .v{font-weight:600;color:var(--ink)}
.nm .rl{font-size:11.5px;color:var(--mute);margin-left:8px}
.vn .main{font-size:12.5px;color:var(--ink2)}
.vn .out{font-size:12.5px;color:var(--acc);margin-left:10px;font-weight:600}
.vn .note2{font-size:11.5px;color:var(--mute);margin-top:2px}
.up{font-size:12px;color:var(--ink2);margin-top:6px;line-height:1.5}
.up.dim{color:var(--mute)}
.note{margin:12px 0 0;color:var(--mute);font-size:12.5px;line-height:1.65}
b{color:var(--ink);font-weight:600}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:0 0 12px;font-size:12.5px;color:var(--ink2)}
.lg{display:inline-flex;align-items:center;gap:6px}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.sw.s-in{background:var(--deemp)}.sw.s-ac{background:var(--acc)}
.sw.s1{background:var(--s1)}.sw.s2{background:var(--s2)}.sw.s3{background:var(--s3)}
.sw.s4{background:var(--s4)}.sw.s-oth{background:var(--oth)}
.sw.s-unk{background:var(--unk);border:1px solid var(--base)}
/* tabs */
.tabs{display:flex;gap:4px;flex-wrap:wrap;margin:0 0 14px;border-bottom:1px solid var(--grid);padding-bottom:8px}
.tab{font:inherit;font-size:13px;color:var(--ink2);background:none;border:1px solid transparent;
 border-radius:8px;padding:4px 10px;cursor:pointer}
.tab:hover{background:var(--grid)}
.tab.is-on{background:var(--acc);color:#fff;border-color:transparent}
.tab-n{font-size:11px;opacity:.7;margin-left:5px;font-variant-numeric:tabular-nums}
.pane{display:none}.pane.is-on{display:block}
/* table */
.tbl{width:100%;border-collapse:collapse;font-size:13.5px}
.tbl th{text-align:left;font-weight:600;font-size:11.5px;color:var(--mute);
 border-bottom:1px solid var(--grid);padding:0 8px 6px;white-space:nowrap}
.tbl td{padding:5px 8px;border-bottom:1px solid var(--grid)}
.tbl tr:last-child td{border-bottom:none}
.num{text-align:right;font-variant-numeric:tabular-nums;width:76px;white-space:nowrap}
.num.strong{color:var(--acc);font-weight:600}
.dim{color:var(--mute)}
.nm{white-space:nowrap}
.th-bar{width:44%}
.bar{padding-right:14px!important}
.seg{display:inline-block;height:11px;vertical-align:middle}
.s-in{background:var(--deemp);border-radius:3px 0 0 3px}
.s-ac{background:var(--acc);border-radius:0 4px 4px 0;margin-left:2px}
.bar .s-in:only-child{border-radius:3px}
.bar .s-ac:only-child{border-radius:3px;margin-left:0}
.mk{font-size:10.5px;padding:1px 6px;border-radius:99px;margin-left:8px;white-space:nowrap;
 border:1px solid var(--ring);color:var(--mute)}
.mk-y{color:var(--ink2)}
.mk-n{color:var(--acc);border-color:var(--acc)}
/* year chart */
.chart{display:flex;gap:14px;align-items:flex-end;height:210px;
 border-bottom:1px solid var(--base);padding:0 4px;margin:0 0 6px}
.col{flex:1;display:flex;flex-direction:column;justify-content:flex-end;height:100%;min-width:0}
.stack{display:flex;flex-direction:column-reverse;border-radius:4px 4px 0 0;overflow:hidden;
 min-height:6px;gap:2px}
.stack.thin{opacity:.5}
.sg{min-height:3px;display:flex;align-items:center;justify-content:center;position:relative}
.sg.s1{background:var(--s1)}.sg.s2{background:var(--s2)}.sg.s3{background:var(--s3)}
.sg.s4{background:var(--s4)}.sg.s-oth{background:var(--oth)}
.sg.s-unk{background:repeating-linear-gradient(45deg,var(--unk),var(--unk) 4px,var(--surf) 4px,var(--surf) 5px)}
.dl{font-size:10.5px;color:#fff;font-variant-numeric:tabular-nums;text-shadow:0 0 3px rgba(0,0,0,.35)}
.dl.dim,.dl.ink{color:var(--ink2);text-shadow:none}
.xl{font-size:12px;color:var(--ink2);text-align:center;padding-top:6px;white-space:nowrap}
.xn{display:block;font-size:10.5px;color:var(--mute);font-variant-numeric:tabular-nums}
.warn{display:block;font-size:9.5px;color:var(--mute);line-height:1.25}
details{margin-top:12px}
summary{font-size:12.5px;color:var(--acc);cursor:pointer}
/* timeline */
.ctrl{display:flex;align-items:center;gap:12px;margin:0 0 12px}
#q{font:inherit;font-size:13px;padding:6px 11px;border:1px solid var(--base);border-radius:8px;
 background:var(--plane);color:var(--ink);width:min(420px,100%)}
.qn{font-size:12px;color:var(--mute);font-variant-numeric:tabular-nums}
.rails{border-top:1px solid var(--grid)}
.strip{display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--grid);padding:3px 0}
.yl{font-size:11.5px;color:var(--ink2);width:52px;flex:none;font-variant-numeric:tabular-nums;line-height:1.25}
.yl .xn{display:inline;margin-left:5px;color:var(--mute)}
.rail{position:relative;flex:1;height:22px}
.dot{position:absolute;top:7px;width:8px;height:8px;margin-left:-4px;border-radius:50%;
 background:var(--acc);box-shadow:0 0 0 2px var(--surf)}
.dot.mult{width:10px;height:10px;top:6px;margin-left:-5px;background:transparent;
 border:2.5px solid var(--acc)}
.dot.off{background:var(--deemp);border-color:var(--deemp);opacity:.45}
.months{display:flex;margin-left:62px;font-size:10px;color:var(--mute)}
.months span{flex:1;text-align:left}
/* fail panels */

.why{margin:0 0 10px;padding:9px 12px;border-left:3px solid var(--acc);background:var(--plane);
 border-radius:0 8px 8px 0;font-size:13px;color:var(--ink2)}
h3{font-size:13.5px;margin:18px 0 8px;color:var(--ink)}
.sub-block{margin-top:22px;padding-top:4px;border-top:1px solid var(--grid)}
.rl{font-size:10.5px;color:var(--mute);margin-left:7px}
.rate{font-size:12px;color:var(--acc);text-align:center;font-variant-numeric:tabular-nums;
 padding-bottom:3px;font-weight:600}
.sg.s-acc{background:var(--acc)}
.sw.s-acc{background:var(--acc)}
.vd{width:38px;text-align:center;font-size:15px}
.wd{width:150px}
.chip{font-size:10.5px;border:1px solid var(--acc);color:var(--acc);border-radius:99px;
 padding:1px 7px;margin-right:4px;white-space:nowrap}
.tx{color:var(--ink2);font-size:12.5px}

.th-dv{width:38%}
.dv,.db{position:relative;height:16px;padding:0 8px!important}
.axis{position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--base)}
/* **これからの公演との差の棒は、藍と朱で分ける。** 以前は `--pos`（緑）と `--neg`（赤）
   だったが、2 つの理由で替えた（2026-08-25）。
   ⑴ **色覚の型によってはほぼ同じ色に見える。** 検証にかけると deutan での隔たりが
      ΔE 2.3 しかなく、下限（8）を大きく下回っていた。藍と朱は ΔE 18.4 で全項目 PASS。
   ⑵ **緑と赤は良し悪しの色である。** この図が出しているのは偏りであって優劣ではない
      ── 「自分のほうが多い」は良いことでも悪いことでもない。 */
.dvbar{position:absolute;top:3px;height:10px}
.dvbar.pos{background:var(--s1);border-radius:0 4px 4px 0}
.dvbar.neg{background:var(--s2);border-radius:4px 0 0 4px}
.sw.s-pos{background:var(--s1)}.sw.s-neg{background:var(--s2)}
.up{color:var(--s1);font-weight:600}
.dn{color:var(--s2);font-weight:600}
.dbline{position:absolute;top:7px;height:2px;background:var(--base)}
.dot-a,.dot-b{position:absolute;top:3px;width:10px;height:10px;margin-left:-5px;border-radius:50%;
 box-shadow:0 0 0 2px var(--surf)}
.dot-a{background:var(--deemp)}
.dot-b{background:var(--acc)}
.sw.sw-a{background:var(--deemp);border-radius:50%}
.sw.sw-b{background:var(--acc);border-radius:50%}
.ins{width:34%;font-size:13px}
.mean{width:33%;font-size:12.5px;color:var(--ink2)}
/* **行動の欄は、押し口が 1 行で収まる幅を必ず取る。** `width` は自動割付では
   ただの希望なので、中身が折り返せる限りブラウザは列を詰める ── 実際に
   「1 日公演は発表された時点で知らせる」が 1 文字ずつ 5 行に割れていた。
   **下限を px で置き、押し口は折り返さないと決める** ── 行動の文は「押すと何が
   起きるか」の一文なので、途中で切れると押す前に読めない。添える公演名（`.up`）は
   折り返してよい。 */
.act{width:33%;min-width:210px}
.act .btn{white-space:nowrap}
.btn{font:inherit;font-size:12px;padding:5px 11px;border-radius:8px;cursor:pointer;
 background:var(--acc);color:#fff;border:none;text-align:left}
.btn.on{background:var(--good)}
.card.fail .big{display:flex;align-items:baseline;gap:10px;margin:6px 0 2px}
.hero{font-size:46px;font-weight:600;letter-spacing:-.02em;color:#d03b3b;line-height:1.1}
.hu{font-size:13px;color:var(--ink2)}
"""



SCRIPT = """
document.querySelectorAll('.btn').forEach(function(b){
 b.onclick=function(){ b.classList.toggle('on'); };
});
"""


def body(extra: str = "", head: str = "") -> str:
    """パネルだけを返す。**1 つのシステムの中の 1 画面として組み込むため**
    （`tools/taguri/app.py` の「眺める」── もとは独立した `/records/compare` だったが、
    起案者の指示・2026-08-26 ──「比べると眺めるを統合して」で 1 枚に統合した）。
    単体の HTML として開く形は撤回した。

    `extra` は**「まだ比較できない軸」の直前**に差し込む。ここに置くのは順序の都合ではない
    ── **できないことの説明は、できることを全部並べたあとに来なければ読めない。**
    後ろに足すと「比べられません」と書いたあとに比べた図が続くことになる。

    `head` は**すべての図より前**に置く。比べる相手が何なのかは、どの図にも同じように
    掛かるので、**図の途中に置くとそこから下だけの断りに見える。**
    """
    return head + action_panel() + unspoken_panel() + extra + rest_panel()


def main():
    body_ = body()
    doc = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>記録を見返す画面（モック・実データ）</title><style>{STYLE}</style></head><body>{RR.FILTERS}
<div class="wrap">
<h1>記録を見返す ── これから上演される公演と比べた自分の偏り</h1>
<p class="sub">出どころ: 観劇履歴 {D["works"]} 作品と、これから観られる公演 {D["compare"]["pop_n"]} 件（母集団）。
お使いの端末内のデータだけで作っており、外へは何も出していません。
<b>◎○△× を使わずに出せる図だけを並べています</b> ── 記録だけを残したい方にも成立させるためです。</p>
{body_}
<p class="note" style="max-width:760px">配色は検証済みの既定パレット（発散の対 blue↔red）で、
明るい配色と暗い配色の両方で、色の見分けやすさを確かめてあります。
すべての図に名前と数値を直接添えています。点数や平均★は出しません。</p>
</div><script>{SCRIPT}</script></body></html>"""
    out = ROOT / "data/review/lookback.html"
    out.write_text(doc, encoding="utf-8")
    print("wrote", out, len(doc), "chars")


if __name__ == "__main__":
    main()
