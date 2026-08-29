#!/usr/bin/env python3
"""行った劇場を、建物の単位にまとめて数える。**地図の点は建物 1 つである。**

## なぜホール名を落とすのか

購入確認メールに書かれているのは**ホールの名前**である ── 「劇場3 小劇場」
「劇場3 中劇場」「東京芸術劇場 シアターイースト」。**同じ建物なので座標は 1 つ**で、
地図に別の点として置くと、同じ場所に点が重なって回数が読めない。

一方、**頻度の横棒はホールの単位でよい** ── 小劇場と中劇場では観る演目の性質が違う。
**軸が違うので、まとめる単位も違う。**（既にある「よく行く劇場」はホールの単位のまま）

## 表記のゆれは、規則と一覧の両方で寄せる

規則で寄せられるのは全角と半角・空白・ホール名の接尾である（「紀伊國屋サザンシアター
TAKASHIMAYA」と「紀伊國屋サザンシアターTAKASHIMAYA」）。**規則で寄せられないものは
一覧に書く** ── 「IMM THEATER」のように略称と正式名が違うものは、次に別の劇場が
出てきたときに規則を足しても当たらない。**列挙できるものは列挙する。**
"""

from __future__ import annotations

import collections
import html
import json
import re
import unicodedata

# ホールの名前。**建物の名前の後ろに付く語なので、後方一致で落とす。**
HALLS = ("小劇場", "中劇場", "大劇場", "THE PIT", "プレイハウス",
         "シアターイースト", "シアターウエスト", "シアターサウス",
         "シアター・ドラマシティ", "シアタードラマシティ",
         "メインホール", "中ホール", "大ホール", "小ホール", "大スタジオ",
         "小スタジオ", "ホールA", "ホールB")

# 規則で寄せられない表記。**画面に出す名前と、座標を引くための検索語（複数）を持つ。**
#
# **検索語を複数持つのは、地図に載る館の数がここで決まるからである。** OSM は施設名で
# 引けないことがあり（別名で登録されている・そもそも無い）、1 語だけ試して落とすと
# 「行った劇場」が地図から消える。実測では「豊島区立芸術文化劇場」で引くと
# 「東京建物 Brillia HALL」が当たり、「KAAT神奈川芸術劇場」は「神奈川芸術劇場」で当たった。
#
# **無い館の座標を書き足すことはしない。** 帝国劇場・紀伊國屋サザンシアター・IMM THEATER・
# ヒューリックホール東京・恵比寿エコー劇場・BLOCH・高輪プリンセスガルテンは、名前の
# 言い換えを 3 通りずつ試しても OSM に無かった。**思い出しで座標を書くと、根拠の無い
# 具体が地図の上で事実のように見える。** 画面には「座標が取れていない館」として名前と
# 回数を出し、埋めるかどうかは本人が決める。
ALIAS = {
    "IMMTHEATER": ("IMM THEATER", ["IMM THEATER", "IMM THEATER 東京"]),
    "COOLJAPANPARKOSAKATTホール": ("COOL JAPAN PARK OSAKA TTホール",
                                   ["COOL JAPAN PARK OSAKA"]),
    "EXTHEATERROPPONGI": ("EX THEATER ROPPONGI", ["EX THEATER ROPPONGI"]),
    "赤坂RED/THEATER": ("赤坂RED/THEATER", ["赤坂RED/THEATER"]),
    "高輪プリンセスガルテン/アンビエンテ": ("高輪プリンセスガルテン",
                                  ["高輪プリンセスガルテン", "プリンセスガルテン 高輪"]),
    "座・高円寺1": ("座・高円寺", ["座・高円寺"]),
    "紀伊國屋サザンシアターTAKASHIMAYA": ("紀伊國屋サザンシアター TAKASHIMAYA",
                                        ["紀伊國屋サザンシアター", "紀伊国屋サザンシアター"]),
    "BLOCH": ("BLOCH", ["BLOCH 札幌", "BLOCH 北海道"]),
    "東京建物ブリリアホール": ("東京建物 Brillia HALL",
                        ["豊島区立芸術文化劇場", "Brillia HALL"]),
    "ヒューリックホール東京": ("ヒューリックホール東京",
                       ["ヒューリックホール東京", "ヒューリックホール"]),
    "有楽町よみうりホール": ("よみうりホール", ["よみうりホール"]),
    "KAAT神奈川芸術劇場": ("KAAT 神奈川芸術劇場", ["神奈川芸術劇場"]),
    "帝国劇場": ("帝国劇場", ["帝国劇場", "帝国劇場 千代田区"]),
}

# ISO 3166-2:JP → 都道府県名。**Nominatim が返す `ISO3166-2-lvl4` から引く** ──
# `state` は東京では空で、`province` は県によって有無が違う。**符号だけが必ず入っている。**
PREF = {
    1: "北海道", 2: "青森県", 3: "岩手県", 4: "宮城県", 5: "秋田県", 6: "山形県",
    7: "福島県", 8: "茨城県", 9: "栃木県", 10: "群馬県", 11: "埼玉県", 12: "千葉県",
    13: "東京都", 14: "神奈川県", 15: "新潟県", 16: "富山県", 17: "石川県",
    18: "福井県", 19: "山梨県", 20: "長野県", 21: "岐阜県", 22: "静岡県",
    23: "愛知県", 24: "三重県", 25: "滋賀県", 26: "京都府", 27: "大阪府",
    28: "兵庫県", 29: "奈良県", 30: "和歌山県", 31: "鳥取県", 32: "島根県",
    33: "岡山県", 34: "広島県", 35: "山口県", 36: "徳島県", 37: "香川県",
    38: "愛媛県", 39: "高知県", 40: "福岡県", 41: "佐賀県", 42: "長崎県",
    43: "熊本県", 44: "大分県", 45: "宮崎県", 46: "鹿児島県", 47: "沖縄県",
}


def key(venue: str) -> str:
    """建物を指す鍵。空白と全角半角を寄せ、ホール名を落とす。"""
    v = unicodedata.normalize("NFKC", venue or "").strip()
    v = re.sub(r"\s+", "", v)
    for _ in range(2):                     # 「東京芸術劇場シアターイースト」など 1 段だけ
        for h in HALLS:
            hh = re.sub(r"\s+", "", unicodedata.normalize("NFKC", h))
            if v.endswith(hh) and len(v) > len(hh):
                v = v[: -len(hh)]
                break
    return v.strip("　 ・-")


def hall(venue: str) -> str:
    """ホールを指す名前。**建物にまとめない。**

    規模（座席数）を軸にするときは、ホールが単位である ── 劇場3は小劇場 440 席・
    中劇場 1,038 席で、建物にまとめると規模という属性そのものが消える。
    寄せるのは表記のゆれだけにする（「紀伊國屋サザンシアター TAKASHIMAYA」と
    「紀伊國屋サザンシアターTAKASHIMAYA」は同じホールで、空白の有無しか違わない）。
    """
    v = unicodedata.normalize("NFKC", venue or "").strip()
    return re.sub(r"\s+", "", v).strip("　 ・-")


def label(k: str) -> str:
    """画面に出す名前。一覧にあればそれ、無ければ鍵そのもの。"""
    return ALIAS.get(k, (k, [k]))[0]


def queries(k: str) -> list[str]:
    """座標を引くための検索語を、試す順に返す。**略称のままでは当たらない館がある。**"""
    return list(ALIAS.get(k, (k, [k]))[1])


def visits(works: list[dict]) -> collections.Counter:
    """建物ごとの観た回数。**回の単位で数える**（1 作品を 3 回観れば 3 回）。

    地図の点の大きさは「何回足を運んだか」であって作品数ではない ── 同じ劇場に
    3 回通ったことは、3 回ぶんの記憶である。
    """
    c: collections.Counter = collections.Counter()
    for w in works:
        for s in w.get("shows") or []:
            if s.get("venue"):
                c[key(s["venue"])] += 1
    return c


def works_at(works: list[dict]) -> dict[str, list[dict]]:
    """建物ごとに、そこで観た作品を返す。**点を押したときに出す中身である。**"""
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for w in works:
        for k in {key(s["venue"]) for s in (w.get("shows") or []) if s.get("venue")}:
            out[k].append(w)
    for k in out:
        out[k].sort(key=lambda w: w.get("first_date") or "", reverse=True)
    return dict(out)


# ---------------------------------------------------------------- 行っていない劇場
#
# 起案者の言葉（2026-08-24）──「よく行く劇場の情報がせっかくまとまっているので、
# それに関する分析なんかも見られたらいい気がする。」
#
# **案を 3 つ出して選んでもらった。** 出さないと決めたものが 2 つある。
#
# - **劇場ごとの当たり率は出さない。** 検証 019 で落とした判定である（劇場だけで ◎ を
#   当てようとすると当てずっぽうより悪くなる）。**実装の都合で落とした判定を戻さない。**
# - **「この劇場で新しい作り手に出会えた」は出さない。** 計算はできるが、**上位が
#   「出演者の多い劇場」と「もともとよく舞台に出ている人」で説明できてしまう** ──
#   実測で博多座 33% と出たが分母は 9 名しかなく、帝国劇場 26% は出演者 85 名ぶんである。
#   下位の要因で説明できる分を引かずに出すと、劇場の手柄として読ませることになる。
#
# **出すのは「行っていない劇場」である。** これは自分について新しく分かることではなく、
# **見逃しを減らす側**である（世界側の事実）。それでも価値があるのは、**公演を選ぶのとは
# 別の判断ができる**からである ── その公演自体はすでに推薦にも出ているが、
# 「行ったことのない劇場を開拓するか」は劇場の単位でしか決められない。

KANTO = ("東京都", "神奈川県", "千葉県", "埼玉県")
MIN_SHOWS = 1            # 該当が 1 件でも出す（館の数が少ないので絞る必要が無い）
SHOWN_NEAR = 8           # 首都圏で名前を出す館の数
SHOWN_FAR = 6            # そのほかで名前を出す館の数


def _first_day(period: str):
    import datetime
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    try:
        return datetime.date(*map(int, ms[0]))
    except ValueError:
        return None


def unvisited(rated: list[dict], cand_path, keep_roles, parse_credits) -> dict:
    """行ったことのない劇場のうち、**◎ を付けた作品の出演者・作り手が出る公演がある**館。

    ## 数える範囲を、ほかの画面とそろえる

    **役職は「出演」と作り手（演出・脚本ほか）だけにする**（`people.KEEP_ROLES`）。
    最初に測ったときは裏方も数えており、**名簿が 533 名に膨らんで上位が遠方の劇場ばかりに
    なった** ── 制作・宣伝・票券まで一致に数えると、ツアーで回る座組の裏方が全国の館に
    当たる。出演と作り手に絞ると名簿は 295 名になり、**首都圏の館が 21 館出てきた。**

    **まだ初日を迎えていない公演だけを見る**（企画書 4 章の推薦枠と同じ）── 終わった公演を
    見せても「行くかどうか」を決められない。

    ## 判定の限界を返り値に入れる

    **行った／行っていないは、劇場名の一致で決めている。** 表記が違えば「行っていない」に
    入る ── 寄せられるのは全角半角と空白と一覧にある略称だけである（`ALIAS`）。
    件数を返すので、画面に必ず書く。
    """
    keep = set(keep_roles)
    roster = {p for r in rated if r.get("verdict") == "◎"
              for role, p in (r.get("people") or []) if role in keep}
    been = {hall(v) for r in rated if r.get("venues") for v in r["venues"]}
    halls: dict[str, dict] = {}
    n_all = n_up = 0
    lines = (cand_path.read_text(encoding="utf-8").split("\n")
             if cand_path.exists() else [])
    for line in lines:
        if not line.strip():
            continue
        c = json.loads(line)
        n_all += 1
        fd = _first_day(c.get("period"))
        import datetime
        if not fd or fd < datetime.date.today():
            continue
        n_up += 1
        raw = (c.get("fields") or {}).get("劇場") or c.get("theater") or ""
        if not raw:
            continue
        h = hall(raw)
        d = halls.setdefault(h, {"hall": h, "label": raw, "pref": "", "n": 0,
                                 "hit": 0, "shows": []})
        d["n"] += 1
        d["pref"] = c.get("pref") or d["pref"]
        who = sorted({p for role, p in parse_credits(c.get("fields") or {})
                      if role in keep} & roster)
        if who:
            d["hit"] += 1
            d["shows"].append({"stage_id": str(c.get("stage_id") or ""),
                               "title": c.get("title") or "",
                               "period": c.get("period") or "",
                               "price": c.get("price") or "", "who": who})
    # **重なったものを先に出す** ── 該当した公演の本数が根拠の重なりである
    rank = sorted((d for d in halls.values() if d["hall"] not in been
                   and d["hit"] >= MIN_SHOWS),
                  key=lambda d: (-d["hit"], -d["n"], d["label"]))
    for d in rank:
        d["shows"].sort(key=lambda s: (-len(s["who"]), s["period"]))
    return {"near": [d for d in rank if d["pref"] in KANTO],
            "far": [d for d in rank if d["pref"] not in KANTO],
            "roster": len(roster), "been": len(been),
            "halls": len(halls), "n_all": n_all, "n_up": n_up}


def open_panel(rated: list[dict], cand_path, keep_roles, parse_credits,
               buttons=None, h2=None, table=None) -> str:
    """「まだ行っていない劇場」の 1 枚。**押す口をその場に置く。**

    **一覧を見せて終わりにしない。** 劇場の名前だけ並べても、次にすることが決まらない ──
    その館でこれからかかる公演と、「興味あり」を押す口を同じ場所に置く。

    **首都圏とそのほかを分ける。** 名簿は ◎ を付けた作品の出演者から作るので、
    **ツアーで回る座組が入ると全国の館が上位に来る** ── 行ける範囲を先に出さないと、
    行動できない館の一覧になる（行けない館も落とさず、畳んで残す）。
    """
    d = unvisited(rated, cand_path, keep_roles, parse_credits)
    if not d["near"] and not d["far"]:
        return ""
    h2 = h2 or (lambda *a, **k: "")
    esc = html.escape

    def rows(items: list[dict], limit: int) -> str:
        out = []
        for v in items[:limit]:
            shows = "".join(
                f'<div class="vs"><span class="vst">{esc(s["title"])}</span>'
                f'<span class="vsm">{esc(s["period"])}'
                + (f'・{esc(s["price"])}' if s["price"] else "") + "</span>"
                f'<span class="vsw">◎ を付けた作品の'
                f'{esc("・".join(s["who"][:4]))}'
                + (f' ほか {len(s["who"]) - 4} 名' if len(s["who"]) > 4 else "")
                + "さんが出ます</span>"
                + (buttons(s["stage_id"]) if buttons else "") + "</div>"
                for s in v["shows"])
            out.append(
                # **画面に出すのは寄せる前の表記である。** 鍵は空白を落として作るので、
                # 鍵をそのまま出すと「シアターグリーンBOXinBOXTHEATER」になる ──
                # **突き合わせのために作った形を、人が読む名前として出さない**
                f'<details class="vh"><summary><b>{esc(v["label"])}</b>'
                f'<span class="vhm">{esc(v["pref"])}・これからの公演 {v["n"]} 件のうち '
                f'<b>{v["hit"]} 件</b>に出ます</span></summary>{shows}</details>')
        more = len(items) - limit
        if more > 0:
            out.append(f'<p class="hint">ほかに {more} 館あります。'
                       f'下の表にすべて出しています。</p>')
        return "".join(out)

    tbl = ""
    if table:
        tbl = table(["劇場", "都道府県", "これからの公演", "うち該当"],
                    [[v["label"], v["pref"], v["n"], v["hit"]]
                     for v in d["near"] + d["far"]])
    far = ""
    if d["far"]:
        far = (f'<details class="more"><summary>首都圏以外の {len(d["far"])} 館を見る'
               f'</summary><p class="lead">ツアーで回る座組も数えているので、'
               f'<b>遠方の館が上位に来ます。</b></p>'
               f'{rows(d["far"], SHOWN_FAR)}</details>')
    return f"""<section class="card">
{h2("building", "まだ行っていない劇場",
    f'<span class="badge part">{len(d["near"]) + len(d["far"])} 館</span>')}
<p class="lead"><b>行ったことのない劇場のうち、◎ を付けた作品に出ていた方が
これから出る館です。</b>これまでに行ったのは {d["been"]} 館、これから公演があるのは
{d["halls"]} 館です。館ごとの公演は、おすすめや探す画面にも出てきます。</p>
<details class="nn"><summary>数え方</summary>
<p class="lead">数えたのは出演者と作り手（演出・脚本ほか）だけです。
制作・宣伝まで数えると、ツアーの裏方が全国の館に当たってしまいます。<br>
<b>行った・行っていないは劇場名の一致で決めています</b> ── 表記が違う館は
「行っていない」側に入ります。</p></details>
<div class="vhs">{rows(d["near"], SHOWN_NEAR)}</div>
{far}
{tbl}</section>"""


CSS = """
/* ---- まだ行っていない劇場 ------------------------------------------------- */
.vhs{margin:0 0 10px}
.vh{border:1px solid var(--ring);border-radius:10px;background:var(--surf);
 padding:0;margin:0 0 8px}
.vh>summary{cursor:pointer;padding:11px 16px;font-size:13.5px;display:flex;gap:12px;
 align-items:baseline;flex-wrap:wrap;list-style:none}
.vh>summary::-webkit-details-marker{display:none}
.vh>summary::before{content:"▸";color:var(--mute);margin-right:2px}
.vh[open]>summary::before{content:"▾"}
.vh .vhm{color:var(--mute);font-size:12.5px}
.vs{border-top:1px solid var(--grid);padding:11px 16px;display:flex;gap:10px;
 flex-wrap:wrap;align-items:baseline}
.vs .vst{font-weight:600;font-size:13.5px}
.vs .vsm{color:var(--mute);font-size:12.5px}
.vs .vsw{flex:1 0 100%;color:var(--ink2);font-size:12.5px}
"""
