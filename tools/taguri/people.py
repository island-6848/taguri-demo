#!/usr/bin/env python3
"""観た公演の「人の網」。**同じ作品に一緒に居た人を線で結ぶ。**

起案者の提案（2026-08-24）── D3 の `mobile-patent-suits`（力学配置の有向グラフ）を
挙げて「公演記録を可視化するページで以下のような可視化があっても面白いかも」。
**範囲は「2 作品以上に出てくる人だけ」を選んでもらった**（全員だと 514 名・毛玉になる）。

## なぜ網の形か ── 棒でも散布図でも答えられない問いがある

データの仕事は**量でも順位でもなく、関係の構造**である。

| 問い | 答えられる形 |
|---|---|
| 誰を何本観たか | **横棒**（既にある「よく行く劇場」と同じ形）。網は要らない |
| 何人と何回すれ違ったか | 集計の数字 1 つ。網は要らない |
| **束はいくつあって、どれとどれが別々なのか** | **網だけ** |
| **別々の束をつないでいるのは誰か** | **網だけ**（しかも計算で名指しできる） |

**上の 2 つは本人が既に知っていることなので、可視化の値打ちには数えない**
（企画書 2 章・`own-behavior-aggregates-are-not-insight`）。この図が受け持つのは下の 2 つ
だけである。だから**見出しに「束をつないでいるのは誰か」と書き、その人を計算して名指しする。**

## 名指しは人手に残さない

**探す仕事はシステムがやる。** 図を出して「よく見ると誰かが橋になっています」と書くのは、
読み手に探索を投げているのと同じである。**外すと網が割れる人（関節点）は計算で決まる**ので、
先に計算して文に書く。図はその答えを確かめるためにある。

## 色と大きさに何を載せるか ── 評価は載せない

**人を ◎ 率で塗らない。** 作品の ◎ は内容への評価であって、関わった個人への評価ではない
（`work-verdict-is-not-a-person-label`。個人への関心は「お気に入り」で本人に名指しで聞く）。
色で「当たりの人／外れの人」を作ると、作品への評価を人物の評点に読み替えることになる。

載せるのは**事実だけ**である。

| 見た目 | 載せるもの | 仕事 |
|---|---|---|
| 点の大きさ | その人が出てくる作品数 | 量 |
| 点の色 | 出演／作り手（演出・脚本ほか） | **識別（2 枠・固定の順）** |
| 線の太さ | 一緒に居た作品数 | 量 |
| 太い輪 | 外すと網が割れる人 | 状態（形でも分かるので色だけに頼らない） |

**配色は検証済みの既定パレットの 1 枠目と 2 枠目**（`#2a78d6` / `#eb6834`、暗い側は
`#3987e5` / `#d95926`）。`validate_palette.js` は**明暗どちらも全項目 PASS**
（CVD の隔たり ΔE 24.7／26.8、通常視 33.6／31.8、地とのコントラストも 3:1 以上）。
それでも**直接ラベルと凡例と表の姿を必ず添える** ── 色だけで意味を運ばないためである。

## 配置は毎回同じにする

力学配置は初期値で絵が変わる。**乱数を使わず、名前の順に円周へ並べてから始める**ので、
同じデータなら同じ絵になる。**絵が毎回変わると、前に見た形と見比べられない。**
つまんで動かした分だけが変わる。

## 描画は自前のコードで行う

この図に描画ライブラリは使っていない。**点は 57・線は 207 なので、総当たりの斥力でも
1 フレーム 1,596 組**しかなく、近似（Barnes-Hut）を持ち込む必要が無い。加えて、この図の
要点である**「人を外して束を並べ直す」動きは、既製の力学配置にそのまま無い**
（`pack2` の注記 ── 束をまるごと平行移動して離す）。

**外部サイトからは読み込まない**（画面から外部を叩かない ── 企画書 5 章の 5）。
なお同じ画面の別の図（`timeline.py`）は端末内に置いた d3 を使っている。**守りに触るのは
「外から読むか」であって「ライブラリを使うか」ではない**ので、この図を将来 d3 で書き直す
選択肢は残っている ── いま書き直さないのは、上の 2 つ目の理由（外して並べ直す動き）を
自前で持っているためである。
"""

from __future__ import annotations

import collections
import datetime as dt
import html
import itertools
import json
import math
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import charts as CH                                                  # noqa: E402
import icons as IC                                                   # noqa: E402
import llm_gemini as LLM                                             # noqa: E402

E = lambda s: html.escape(str(s))                                   # noqa: E731

# **作り手として数える役職。** 裏方は入れない ── 30 名を超える欄があり、
# 選ぶ理由として現れないことを実測してある（検証 018）。推薦の理由欄と同じ範囲にそろえる
MAKER_ROLES = ("演出", "脚本", "作", "原作", "翻訳", "音楽", "作曲", "振付")
KEEP_ROLES = ("出演",) + MAKER_ROLES
MIN_WORKS = 2            # 網に出す下限（1 作品だけの人を出すと 514 名の毛玉になる）
LABEL_MIN = 4            # 名前を図に書く下限（すべてに書くと文字が重なって読めない）

# 図の座標系。**枠の形は、この網が落ち着く形に合わせてある。**
# 一様に拡大して枠へ収める（形を崩さない）ので、枠の縦横比が中身とずれた分は
# そのまま余白になる ── 900x620 では横に 31% の死んだ帯ができていた（実測）。
W, H = 740.0, 620.0
PAD = 26.0               # 枠の余白（名前は当たり判定で置くので、余白では逃がさない）
LABEL_MAX = 16           # 図に置く名前の上限（残りは表と、点に触れたときの吹き出しで読む）


# ---------------------------------------------------------------- 網を組む
def build(rated: list[dict]) -> dict:
    """評価済みの記録から網を組む。`rated` は `measure_nets.load_rated()` の行。

    **人物が引けなかった作品は網に入らない。** 件数を返すので、図に必ず書く
    （`limits-must-fix-the-numbers` ── 限界は注記に逃がさず数字の側に出す）。
    """
    per_work, roles, cnt = {}, collections.defaultdict(set), collections.Counter()
    titles = collections.defaultdict(list)
    for r in rated:
        ps = set()
        for role, person in r.get("people") or []:
            if role in KEEP_ROLES:
                ps.add(person)
                roles[person].add(role)
        if ps:
            per_work[r["key"]] = ps
            for p in ps:
                cnt[p] += 1
                titles[p].append((r.get("title") or "", r["key"]))
    nodes = sorted({p for p, n in cnt.items() if n >= MIN_WORKS})
    edges: collections.Counter = collections.Counter()
    adj: dict[str, set] = {p: set() for p in nodes}
    for ps in per_work.values():
        for a, b in itertools.combinations(sorted(ps & set(nodes)), 2):
            edges[(a, b)] += 1
            adj[a].add(b)
            adj[b].add(a)
    # **線を 1 本も持たない人を、網の枠から出す。**
    #
    # 2 作品以上に出てくるが、**同じく 2 作品以上に出てくる誰とも一緒になっていない**人が
    # いる（実データで 2 名）。この人たちを網と同じ枠に置くと、**力学配置は互いの斥力だけで
    # この人たちを隅へ飛ばし、枠に収める計算がその隅までを含めてしまう** ── 結果、
    # つながっている 54 名が枠の 1/4 に潰れて線が読めなくなっていた（実測）。
    #
    # **消すのではなく、枠の外に出して文で数える。** 網の問いは「束をつないでいるのは誰か」
    # なので、線を持たない人はその問いの外側にいる ── ただし居なかったことにはしない。
    core = [p for p in nodes if adj[p]]
    return {"nodes": nodes, "core": core,
            "isolated": [p for p in nodes if not adj[p]],
            "edges": edges, "adj": adj, "cnt": cnt, "roles": roles,
            "titles": titles, "n_works": len(per_work), "n_rated": len(rated),
            "n_people": len(cnt), "cuts": _cuts(core, adj)}


def _n_comp(nodes: list[str], adj: dict, skip: set) -> int:
    seen, k = set(skip), 0
    for p in nodes:
        if p in seen:
            continue
        k += 1
        st = [p]
        seen.add(p)
        while st:
            for q in adj[st.pop()]:
                if q not in seen:
                    seen.add(q)
                    st.append(q)
        # 深さ優先の続きは上の while で回している
    return k


def _cuts(nodes: list[str], adj: dict) -> list[str]:
    """**外すとこの網が割れる人**（関節点）。

    孤立した点と、端の点は割らない ── 外しても束の数は増えないので、この条件で除ける。
    """
    base = _n_comp(nodes, adj, set())
    return [p for p in nodes if _n_comp(nodes, adj, {p}) > base]


def components(g: dict, skip=()) -> list[list[str]]:
    """束（連結成分）。大きい順。中は作品数の多い順。

    `skip` に人を渡すと、**その人を外した網**の束を返す ── 図の「外してみる」で
    何束に割れるかを、押す前に文にして出すために要る（探す仕事は人手に残さない）。
    """
    skip = set(skip)
    seen, out = set(skip), []
    for p in g["core"]:
        if p in seen:
            continue
        st, c = [p], []
        seen.add(p)
        while st:
            x = st.pop()
            c.append(x)
            for q in g["adj"][x]:
                if q not in seen:
                    seen.add(q)
                    st.append(q)
        out.append(sorted(c, key=lambda q: (-g["cnt"][q], q)))
    return sorted(out, key=len, reverse=True)


# ---------------------------------------------------------------- 時間の軸
#
# 仕様は docs/000007-records-network-time-spec.md。**新しい図は作らない。**
# `build()` を、上演日順に積んだ記録の頭から少しずつ渡して呼び直すだけである
# （点の集合が入れ子であることは実測で確かめた ── 一度 2 作品以上に出た人は、以後の
# どの時点でも core から外れない）。配置（座標）は「いま」の網で 1 度だけ解き、
# 画面側は時点ごとに出ていない点と線を隠すだけにする（配置を解き直さない）。
def _fmt_date(d: str) -> str:
    y, m, day = d.split("-")
    return f"{y}年{int(m)}月{int(day)}日"


def _people_join(names: list[str], limit: int = 4) -> str:
    if len(names) <= limit:
        return "、".join(E(n) for n in names)
    return "、".join(E(n) for n in names[:limit]) + f" ほか {len(names) - limit} 名"


def _stage_note(r: dict, added_nodes: list[str], added_edges: list,
                cut_added: list[str], cut_removed: list[str],
                merged: list | None, first: bool, new_cluster: bool) -> str:
    """**この 1 本が網にしたことを、先に文で言い切る**（探す仕事を読み手に投げない）。"""
    a = CH._anchor(r.get("key") or "")
    href = f'{CH.ROW_HREF}&amp;w={E(a)}#w-{E(a)}'
    head = f'<a href="{href}">{_fmt_date(r["date"])} ── {E(r.get("title") or "")}</a>'
    bits = []
    if added_nodes:
        bits.append(f"網に{_people_join(added_nodes)}が加わりました")
    if merged:
        sizes = "、".join(f"{len(o)}名" for o in merged)
        bits.append(f"<b>それまで別々だった {len(merged)} つの束（{sizes}）が、"
                    "この 1 本で 1 つになりました</b>")
    elif first:
        bits.append("<b>ここから網ができました</b>")
    elif new_cluster:
        bits.append("<b>ほかとまだつながらない、新しい束ができました</b>")
    if cut_added:
        bits.append(f"<b>{_people_join(cut_added)}を外すと、網が割れるようになりました</b>")
    if cut_removed:
        bits.append(f"<b>{_people_join(cut_removed)}を外しても、網が割れなくなりました</b>")
    if not bits:
        bits.append(f"線が {len(added_edges)} 本増えました")
    return f'<p class="pnstage">{head}<br>{"。".join(bits)}。</p>'


def timeline(rated: list[dict], g: dict, idx: dict) -> dict:
    """網が変わった段だけを、日付順に積む。

    `g`・`idx` は「いま」の網（`build(rated)` と、そこから作った点の番号）を渡す。
    段の点・線は、この番号で返す ── 画面側の点・線の要素と、番号だけで結び付くようにする。
    """
    dated = sorted((r for r in rated if r.get("date")), key=lambda r: (r["date"], r["key"]))
    prev = build([])
    prev_comps: list[frozenset] = []
    stages = []
    unchanged = {"no_credit": 0, "repeat": 0, "not_yet": 0}
    for i, r in enumerate(dated, 1):
        gi = build(dated[:i])
        added_nodes = sorted(set(gi["core"]) - set(prev["core"]), key=lambda p: -gi["cnt"][p])
        added_edges = [e for e in gi["edges"] if e not in prev["edges"]]
        cuts_now, cuts_prev = set(gi["cuts"]), set(prev["cuts"])
        cut_added = sorted(cuts_now - cuts_prev)
        cut_removed = sorted(cuts_prev - cuts_now)
        comps_now = [frozenset(c) for c in components(gi)]
        changed = bool(added_nodes or added_edges or cut_added or cut_removed
                       or len(comps_now) != len(prev_comps))
        if not changed:
            ps = {p for role, p in (r.get("people") or []) if role in KEEP_ROLES}
            if not ps:
                unchanged["no_credit"] += 1
            elif len(ps & set(gi["core"])) >= 2:
                unchanged["repeat"] += 1
            else:
                unchanged["not_yet"] += 1
            prev, prev_comps = gi, comps_now
            continue
        merged = None
        for new in comps_now:
            olds = [o for o in prev_comps if o & new]
            if len(olds) > 1:
                merged = sorted(olds, key=len, reverse=True)
                break
        new_cluster = merged is None and len(comps_now) > len(prev_comps)
        first = new_cluster and not prev_comps
        note = _stage_note(r, added_nodes, added_edges, cut_added, cut_removed,
                           merged, first, new_cluster and not first)
        stages.append({
            "n": [idx[p] for p in added_nodes if p in idx],
            "e": [[idx[a], idx[b]] for a, b in added_edges if a in idx and b in idx],
            "note": note,
            # **`facts()` の材料。** 画面（JS）はこの下の 3 つを読まない ──
            # LLM に渡す構造化した事実だけを、文（`note`）と別に持たせるためである
            "date": r["date"], "title": r.get("title") or "",
            "merged": [len(o) for o in merged] if merged else [],
        })
        prev, prev_comps = gi, comps_now
    # **「いま」── 上演日を持たない記録の分まで、まとめて最後の段に足す。**
    rest_nodes = sorted(set(g["core"]) - set(prev["core"]), key=lambda p: -g["cnt"][p])
    rest_edges = [e for e in g["edges"] if e not in prev["edges"]]
    stages.append({
        "n": [idx[p] for p in rest_nodes if p in idx],
        "e": [[idx[a], idx[b]] for a, b in rest_edges if a in idx and b in idx],
        "note": "", "date": "", "title": "", "merged": [],
    })
    return {"stages": stages, "unchanged": unchanged, "n_dated": len(dated),
            "n_undated": len(rated) - len(dated), "gap_people": len(rest_nodes)}


def _time_payload(tl: dict) -> str:
    raw = json.dumps({"stages": tl["stages"]}, ensure_ascii=False, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace("&", "\\u0026")


# ---------------------------------------------------------------- 読み（LLM）
#
# 起案者の指示（2026-08-27）── 「図から読み取れることを LLM で分析し、実際に
# 文章で記載してユーザーを支援して」。**やり方は `chronicle.py` と同じにする**
# （事実は規則で作り、読みだけを LLM に書かせる。渡すのは集計だけで、記録の本文は
# 渡さない。LLM が挙げた名前が事実に無ければその行を落とす）。
#
# **束の数・関節点・段ごとに何が起きたかは、この図では既にすべて文で言い切って
# ある**（`cut_txt`・`_stage_note`）。LLM に書かせるのは、**それらの事実を
# 1 つの読み物としてつなぐ段落だけ**である ── 個々の事実の発見や、関係の種類の
# 推測はさせない（データに無く、書けば作り話になる）。
MODEL = LLM.MODEL
PROMPT_VERSION = "p1"
NET_OUT = Path(__file__).resolve().parents[2] / "data" / "review" / "people_read.json"


def facts(g: dict, comps: list[list[str]], tl: dict) -> dict:
    """この網の集計。**LLM に渡すのはこれだけである**（`chronicle.facts` と同じ役目）。"""
    bridges = [{"name": p, "role": "作り手" if _is_maker(g, p) else "出演",
               "works": g["cnt"][p], "people": len(g["adj"][p]),
               "splits": len(components(g, {p}))}
              for p in sorted(g["cuts"], key=lambda q: -len(g["adj"][q]))]
    top = [{"name": p, "role": "作り手" if _is_maker(g, p) else "出演",
           "works": g["cnt"][p], "people": len(g["adj"][p])}
          for p in sorted(g["core"], key=lambda q: -g["cnt"][q])[:6]]
    merges = [{"date": s["date"], "title": s["title"], "sizes": s["merged"]}
             for s in tl["stages"] if s.get("merged")]
    started = ({"date": tl["stages"][0]["date"], "title": tl["stages"][0]["title"]}
              if tl["stages"] and tl["stages"][0].get("date") else None)
    return {
        "n_people": g["n_people"], "n_core": len(g["core"]),
        "n_isolated": len(g["isolated"]), "n_works": g["n_works"],
        "bundles": sorted((len(c) for c in comps), reverse=True),
        "bridges": bridges, "top_people": top, "merges": merges, "started": started,
        "n_stage_changes": len(tl["stages"]) - 1,
        "n_unchanged": sum(tl["unchanged"].values()),
    }


def fingerprint(f: dict) -> str:
    """網が変わったかどうかの印。**変わっていなければ LLM を呼ばない**（`minimize-llm-calls`）。"""
    return json.dumps([f["bundles"], f["bridges"], f["merges"], f["n_people"],
                       PROMPT_VERSION], ensure_ascii=False)


PROMPT = """あなたは、ある人の観劇記録から組んだ「一緒に出てくる人の網」を読み解く部品である。

入力は JSON で、**集計した事実だけ**が入っている（本文や記録そのものは渡していない）。

n_people=2 作品以上に出てくる人の総数、n_core=そのうち誰かと共演があり網に出ている人数、
n_isolated=2 作品以上出ているが誰とも共演していない人数、n_works=作品数、
bundles=いまの束（共演のつながりで分かれたかたまり）の人数を大きい順に並べたもの、
bridges=外すと束が割れる人（関節点）。name・role（作り手／出演）・works（観た作品数）・
people（一緒に居た人数）・splits（外したら何束に割れるか）、
top_people=いちばんよく名前が出てくる人（上位 6 名。bridges と重なることがある）、
merges=別々だった束が 1 つになった出来事。date・title（公演名）・sizes（合流した束の
それぞれの人数）、started=網が最初にできたきっかけの公演（date・title）、
n_stage_changes=観た日のうち網が変わった件数、n_unchanged=変わらなかった件数。

次の 1 つだけを JSON で返す。**説明や前置きを書かず、JSON だけを返すこと。**

{"read": {"body": "…", "evidence": ["…", "…"]}}

- body ── **120〜220 字、1 段落。** データの可視化やネットワーク図に詳しくない人が
  読む前提で、この網から何が言えるかを **語って** 聞かせる。含めること ──
  ① 束がいくつあり、どのくらいの大きさに分かれているか（数字は input の値をそのまま
  使う）。② bridges・top_people の中から**もっとも重要な 1〜2 名**を選び、
  その人がどういう位置にいるか（例:「○○さんを通してこの2つの輪がつながっています」）。
  ③ merges・started に手がかりがあれば、**いつ・どの公演をきっかけに輪が広がった／
  つながったか**に 1 文だけ触れる（無理に全部の出来事を挙げない。いちばん大きな
  合流か、最初のきっかけのどちらかを選ぶ）。
- evidence ── body の根拠にした、**input に実在する**人名・公演名を 2〜5 個。

守ること。

- **入力に無い名前・公演名を書かない。** 「おそらく」「〜かもしれません」で補わない。
- **関係の種類を書かない**（同僚・友人・上司など）。入力に無いので作り話になる。
  分かるのは「同じ束にいる／束をつないでいる」という構造だけである。
- **人物の評価・優劣を書かない**（「この人が重要」であって「この人が良い」ではない）。
- 用語は画面と同じ言葉を使う ──「束」「外すと割れる人」。「クラスタ」「ノード」
  「エッジ」のような分析の言葉は使わない。
- **「ですます」で書く。** 読み手は記録の本人である。

入力:
"""


READ_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "read": {
            "type": "OBJECT",
            "properties": {
                "body": {"type": "STRING"},
                "evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["body", "evidence"],
        },
    },
    "required": ["read"],
}


def ask(f: dict, model: str = MODEL, timeout: int = 300) -> dict:
    """LLM に読みを書かせる。**返らなかったときは空を返す**（事実の図はそのまま出る）。"""
    body = json.dumps(f, ensure_ascii=False)
    try:
        got, _meta = LLM.ask(PROMPT + body, schema=READ_SCHEMA, model=model, timeout=timeout)
    except (LLM.LLMError, LLM.SafetyBlocked):
        return {}
    return got if isinstance(got, dict) else {}


def _have_names(f: dict) -> set:
    """事実に実在する固有名の一覧。**照合はこれとしか行わない。**"""
    out = {b["name"] for b in f["bridges"]} | {p["name"] for p in f["top_people"]}
    out |= {m["title"] for m in f["merges"] if m["title"]}
    if f["started"] and f["started"]["title"]:
        out.add(f["started"]["title"])
    return out


def _check(got: dict, f: dict) -> tuple[str, bool]:
    """**事実に無い固有名を挙げていたら、丸ごと落とす。**"""
    read = got.get("read") or {}
    body = read.get("body") if isinstance(read, dict) else None
    ev = ([x for x in (read.get("evidence") or []) if isinstance(x, str)]
         if isinstance(read, dict) else [])
    if not isinstance(body, str) or not body.strip():
        return "", bool(read)
    have = _have_names(f)
    if [x for x in ev if x not in have]:
        return "", True
    return body.strip()[:400], False


def write(model: str = MODEL, force: bool = False) -> dict:
    """読みを作って保存する。**網が変わっていなければ何もしない。**"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import app                                                        # noqa: PLC0415
    rated = app._records_base()["rated_rows"]
    g = build(rated)
    if len(g["core"]) < 3:
        return {"ok": False, "line": "この図はまだ読みを作れるだけの網がありません"}
    idx = {p: i for i, p in enumerate(g["core"])}
    f = facts(g, components(g), timeline(rated, g, idx))
    fp = fingerprint(f)
    old = load()
    if not force and old.get("fingerprint") == fp and old.get("body"):
        return {"ok": True, "skipped": True, "line": "網は変わっていません"}
    body, dropped = _check(ask(f, model), f)
    if not body:
        return {"ok": False, "line": "読みを作れませんでした（LLM から返りませんでした）"}
    NET_OUT.parent.mkdir(parents=True, exist_ok=True)
    NET_OUT.write_text(json.dumps(
        {"body": body, "fingerprint": fp, "dropped": dropped, "model": model,
         "prompt_version": PROMPT_VERSION, "at": dt.date.today().isoformat()},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "line": "この図から分かる文章を作りました"}


def load() -> dict:
    if not NET_OUT.exists():
        return {}
    try:
        return json.loads(NET_OUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------- 配置
def layout(g: dict, *, iters: int = 460) -> dict[str, tuple[float, float]]:
    """力学配置（Fruchterman-Reingold）＋**重なりの解消**。**乱数を使わない。**

    初期値は名前の順に円周へ置く ── **同じデータなら毎回同じ絵になる。**
    **中心へ引く力を弱く入れてある** ── 入れないと、つながっていない束が
    互いの斥力だけで無限に遠ざかり、枠の外へ出る。

    **力学だけでは足りない。** この網は 56 節点に 207 辺あり、1 人あたり平均 7.4 人と
    つながっている ── **密な網は引力が勝って毛玉に潰れる**（最初に組んだときは点が
    完全に重なった組が 162 組あった）。そこで力学のあとに、**近すぎる点を押し離す掃除**を
    かける。これは絵の都合ではなく、**点が重なると大きさ（＝作品数）が読めなくなる**
    ためである。
    """
    ns = g["core"]
    n = len(ns)
    if not n:
        return {}
    cx, cy = W / 2, H / 2
    r0 = min(W, H) / 2.4
    pos = {p: [cx + r0 * math.cos(math.tau * i / n),
               cy + r0 * math.sin(math.tau * i / n)] for i, p in enumerate(ns)}
    k = 1.15 * math.sqrt(W * H / n)
    t0 = W / 8.0
    for it in range(iters):
        t = t0 * (1.0 - it / iters) + 0.4
        disp = {p: [0.0, 0.0] for p in ns}
        for a, b in itertools.combinations(ns, 2):
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.sqrt(dx * dx + dy * dy) or 0.01
            f = k * k / d
            disp[a][0] += dx / d * f
            disp[a][1] += dy / d * f
            disp[b][0] -= dx / d * f
            disp[b][1] -= dy / d * f
        for (a, b), wgt in g["edges"].items():
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.sqrt(dx * dx + dy * dy) or 0.01
            f = d * d / k * (1.0 + 0.30 * (wgt - 1))
            disp[a][0] -= dx / d * f
            disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f
            disp[b][1] += dy / d * f
        for p in ns:
            # **中心へ引く力。** つながっていない束を枠の中に留める
            disp[p][0] += (cx - pos[p][0]) * 0.016
            disp[p][1] += (cy - pos[p][1]) * 0.016
            dx, dy = disp[p]
            d = math.sqrt(dx * dx + dy * dy) or 0.01
            step = min(d, t)
            pos[p][0] += dx / d * step
            pos[p][1] += dy / d * step
    out = _fit(pos, ns)
    return _separate(out, g)


def _fit(pos: dict, ns: list[str]) -> dict[str, list[float]]:
    """枠に収める。**縦横の比は崩さない** ── 崩すと束の形そのものが変わる。"""
    xs = [pos[p][0] for p in ns]
    ys = [pos[p][1] for p in ns]
    s = min((W - 2 * PAD) / max(max(xs) - min(xs), 1.0),
            (H - 2 * PAD) / max(max(ys) - min(ys), 1.0))
    ox = PAD + ((W - 2 * PAD) - (max(xs) - min(xs)) * s) / 2
    oy = PAD + ((H - 2 * PAD) - (max(ys) - min(ys)) * s) / 2
    return {p: [ox + (pos[p][0] - min(xs)) * s, oy + (pos[p][1] - min(ys)) * s] for p in ns}


def _separate(pos: dict, g: dict, *, rounds: int = 220, gap: float = 3.0) -> dict:
    """**近すぎる点を押し離す。** 点が重なると、大きさ（＝作品数）が読めない。

    辺は動かさないので、押し離した分だけ線が伸びる ── **束の形は保たれる**（同じ束の
    点どうしは引力で近く、別の束との距離のほうが大きいままである）。
    """
    ns = g["core"]
    mx = max(g["cnt"][p] for p in g["nodes"])
    rad = {p: _radius(g["cnt"][p], mx) for p in ns}
    for _ in range(rounds):
        moved = 0.0
        for a, b in itertools.combinations(ns, 2):
            dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
            d = math.sqrt(dx * dx + dy * dy) or 0.01
            need = rad[a] + rad[b] + gap
            if d >= need:
                continue
            push = (need - d) / 2
            ux, uy = dx / d, dy / d
            pos[a][0] -= ux * push
            pos[a][1] -= uy * push
            pos[b][0] += ux * push
            pos[b][1] += uy * push
            moved += push
        for p in ns:
            pos[p][0] = min(max(pos[p][0], rad[p] + 2), W - rad[p] - 2)
            pos[p][1] = min(max(pos[p][1], rad[p] + 2), H - rad[p] - 2)
        if moved < 0.4:
            break
    return {p: (pos[p][0], pos[p][1]) for p in ns}


def _text_w(s: str, fs: float = 11.5) -> float:
    """文字の幅の見積もり。**全角は 1 文字ぶん、半角は約 0.52 文字ぶん。**"""
    return sum(fs if unicodedata.east_asian_width(c) in "WF" else fs * 0.52 for c in s)


def place_labels(g: dict, pos: dict) -> list[tuple[str, float, float, str]]:
    """**名前を、重ならない場所にだけ置く。**

    起案者に見せる図なので、**名前が重なって読めないのは形が崩れているのと同じ**である。
    すべての点に名前を書くと 56 個の文字列が団子になるので、次の順で置く場所を探す。

    1. **束をつないでいる方**（この図の答えなので、必ず置く）
    2. 作品数の多い方

    置き場所は点の右・左・上・下と斜めの 8 通りを順に試し、**すでに置いた名前や
    どの点にも当たらない場所**を採る。どこにも入らなければ**その名前は書かない** ──
    重ねて出すより、表と吹き出しに任せるほうが読める。
    """
    ns = g["core"]
    mx = max(g["cnt"][p] for p in g["nodes"])
    rad = {p: _radius(g["cnt"][p], mx) for p in ns}
    cuts = set(g["cuts"])
    order = sorted(ns, key=lambda p: (p not in cuts, -g["cnt"][p], p))
    placed: list[tuple[float, float, float, float]] = []
    out = []
    for p in order:
        if len(out) >= LABEL_MAX and p not in cuts:
            break
        x, y = pos[p]
        r, w = rad[p], _text_w(p)
        h = 15.0
        cands = [(r + 5, 0, "start"), (-(r + 5), 0, "end"),
                 (0, -(r + 11), "middle"), (0, r + 11, "middle"),
                 (r + 4, -(r + 8), "start"), (-(r + 4), -(r + 8), "end"),
                 (r + 4, r + 8, "start"), (-(r + 4), r + 8, "end")]
        for ox, oy, anc in cands:
            ax = x + ox
            x0 = ax if anc == "start" else (ax - w if anc == "end" else ax - w / 2)
            box = (x0, y + oy - h / 2, x0 + w, y + oy + h / 2)
            if box[0] < 1 or box[2] > W - 1 or box[1] < 1 or box[3] > H - 1:
                continue
            if any(b[0] < box[2] and box[0] < b[2] and b[1] < box[3] and box[1] < b[3]
                   for b in placed):
                continue
            # 他の点の丸に当たらないこと（自分の丸は除く）
            if any(q != p and abs(pos[q][0] - (box[0] + box[2]) / 2) < (box[2] - box[0]) / 2 + rad[q]
                   and abs(pos[q][1] - y - oy) < h / 2 + rad[q] for q in ns):
                continue
            placed.append(box)
            out.append((p, ax, y + oy, anc))
            break
    return out


def _radius(n_works: int, mx: int) -> float:
    """点の大きさ。**面積を作品数に比例させる**（半径に比例させると差が誇張される）。"""
    return 5.0 + 6.0 * math.sqrt(n_works / max(mx, 1))


def _is_maker(g: dict, p: str) -> bool:
    return bool(g["roles"][p] & set(MAKER_ROLES))




# ---------------------------------------------------------------- 図
def panel(rated: list[dict]) -> str:
    """1 枚のパネル。**答えを文で先に書き、図はそれを確かめるために置く。**

    ## 動かす理由 ── 答えを確かめる操作が要るから（2026-08-24・起案者の指示）

    起案者の指摘 ──「一緒に出てくる人の網、束をつないでいるのは誰か、の可視化が
    不十分なのでちゃんと動的に動くように調整して」。

    **止まった絵では、この図の見出しの問いに答えられていなかった。** 見出しは
    「束をつないでいるのは誰か」で、本文は関節点 6 名を名指ししていたが、**読み手には
    その 6 名を外した網がどう割れるのかが見えない。** 名前を読んで信じるしかない図だった。

    **動かす先は「外してみる」である。** 名前を押すとその人が網から抜け、**残りが本当に
    別々の束に分かれるところがその場で見える。** 動きは飾りではなく、
    **主張（この人が橋である）を読み手が反証できるようにする道具**である。

    | 操作 | 何が分かるか |
    |---|---|
    | **人を外す** | その人が橋だという主張が正しいか。割れた束それぞれの人数と顔ぶれ |
    | 点をつまんで動かす | 重なって隠れていた点と線。密な所をほどける |
    | **点を（動かさずに）クリックする** | その人を中心に、周りがどう寄ってくるか |
    | 点・表の行に触れる | その人の線だけが浮く（平均 7.4 本の線に埋もれた 1 人を追える） |

    ## クリックで中心へ（2026-08-26・起案者の指示）

    起案者の指示 ──「クリックしたら、その人を中心にネットワーク図が動くようにして
    ほしい」。**つまんで動かす操作と同じ押し口（`pointerdown`/`pointerup`）を使う** ──
    離すまでに動いた距離で「つまんで動かした」のか「クリックした」のかを区別する
    （4px 未満なら、動かしていないとみなす）。新しい押し口を増やさずに済む。

    **中心へは、アニメーションで動かす。** 瞬間移動だと、その人が「もともとどこに
    いたか」が読み手から消える ── ゆっくり動くことで、離れていた人が寄ってくる
    ことが見える。**動きを切っている端末では、瞬時に中心へ置く**
    （`prefers-reduced-motion`）。

    **中心へ着いたら、そこに固定する。** 続く指示（2026-08-26）──「できれば 1 回
    クリックで中心に固定されて、また その人物選んだら解除される感じ」。**最初の
    実装は、アニメーションの終わりで手を離していたため、力学がまた働いて中心から
    離れていった** ── 「固定される」という言葉に応えていなかった。`P[i].fix` を
    立てたままにして直した。**同じ人をもう一度選ぶと解除する**（トグル）。別の人を
    選んだときは、先に固定していた人を自動で解除してから、新しい人を固定する ──
    同時に 2 人を固定する状態は作らない。

    ## 止まった絵の何が壊れていたか（実測して直した 3 件）

    1. **線が 1 本も見えていなかった。** 207 本あるのに、点が重なった塊の下に隠れていた
    2. **図が枠の 1/4 に潰れていた。** 線を持たない 2 名が隅へ飛び、枠に収める計算が
       その隅までを含めていた（`build` の注記）
    3. **名前が重なって読めなかった。** 重ならない場所を探す `place_labels` を書いてあった
       のに、`panel` がそれを呼ばず、点の左右に決め打ちで置いていた

    ## 動いても絵は毎回同じところに落ちる

    **乱数を使わない。** 初期の位置は上の力学配置（名前の順に円周から始める）を
    そのまま渡し、画面側はそこから続きを解く ── **同じデータなら毎回同じ形に落ちる。**
    つまんで動かした分だけが変わる。外部の描画ライブラリは読まない（守り 5）。
    """
    if not rated:
        return ""
    g = build(rated)
    if len(g["core"]) < 3:
        return ""
    pos = layout(g)
    comps = components(g)
    mx = max(g["cnt"][p] for p in g["nodes"])
    cuts = set(g["cuts"])
    ns = g["core"]
    idx = {p: i for i, p in enumerate(ns)}
    rad = {p: _radius(g["cnt"][p], mx) for p in ns}

    # 線。**太いものを先に描く**（細い線が上に来て、束の濃さが読めるようにする）
    lines = []
    for (a, b), wgt in sorted(g["edges"].items(), key=lambda kv: -kv[1]):
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        lines.append(
            f'<line data-a="{idx[a]}" data-b="{idx[b]}"'
            f' x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
            f' stroke-width="{0.9 + 0.85 * (wgt - 1):.2f}"'
            # **濃さも一緒に居た作品数に載せる。** 太さだけだと、1 本で一緒だっただけの
            # 77 本と、6 本一緒だった 21 本が同じ濃さの網になり、**密な所が一様な霞に
            # 見えて束の濃淡が読めない**（実測 ── 重みは 1〜7 で、1 が 77 本ある）
            f' stroke-opacity="{min(0.13 + 0.15 * wgt, 0.80):.2f}">'
            f'<title>{E(a)} と {E(b)} ── 同じ作品 {wgt} 本で一緒でした</title></line>')

    dots = []
    for p in sorted(ns, key=lambda q: g["cnt"][q]):
        x, y = pos[p]
        r = rad[p]
        maker = _is_maker(g, p)
        ts = "／".join(t for t, _k in g["titles"][p][:4])
        more = f" ほか {len(g['titles'][p]) - 4} 本" if len(g["titles"][p]) > 4 else ""
        dots.append(
            f'<g class="nd{" cut" if p in cuts else ""}" data-i="{idx[p]}">'
            f'<title>{E(p)}（{"作り手" if maker else "出演"}）── 観た作品 {g["cnt"][p]} 本・'
            f'一緒に居た人 {len(g["adj"][p])} 名／{E(ts)}{E(more)}</title>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"'
            f' fill="var(--{"s2" if maker else "s1"})"/></g>')

    # **名前は、重ならない場所にだけ置く。** 書いてあったのに呼んでいなかった
    labs = "".join(
        f'<text class="nl" data-i="{idx[p]}" x="{x:.1f}" y="{y:.1f}"'
        f' text-anchor="{anc}">{E(p)}</text>'
        for p, x, y, anc in place_labels(g, pos))

    # **外すと何束に割れるかは、押す前に計算して書く**（探す仕事を読み手に投げない）
    cut_btns = "".join(
        f'<button data-cut="{idx[p]}">{E(p)}<span class="cn">'
        f'{len(components(g, {p}))} つに割れる</span></button>'
        for p in sorted(g["cuts"], key=lambda q: -len(g["adj"][q])))
    cut_txt = ("この網には、外すと束が割れる人がいません。" if not g["cuts"] else
               f'<b>外すと網が割れるのは、この {len(g["cuts"])} 名です。</b>'
               "名前を押すと、その方を網から外したときに残りがどう分かれるかが出ます。")

    iso_txt = ("" if not g["isolated"] else
               f'<br>2 作品以上に出てきますが、<b>ほかの誰とも一緒になっていない方が '
               f'{len(g["isolated"])} 名います</b>（'
               + "、".join(E(p) for p in g["isolated"]) + "）── 線が無いので図には出ません。")

    rows = [[p, "作り手" if _is_maker(g, p) else "出演", g["cnt"][p], len(g["adj"][p]),
             "／".join(t for t, _k in g["titles"][p])] for p in
            sorted(g["nodes"], key=lambda q: (-g["cnt"][q], q))]
    table = CH._table(["人", "役", "観た作品", "一緒に居た人", "作品名"], rows)

    data = _payload(g, pos, rad, idx)
    tl = timeline(rated, g, idx)
    net_facts = facts(g, comps, tl)
    read = load()
    if read.get("body"):
        stale = read.get("fingerprint") != fingerprint(net_facts)
        read_block = (
            '<div class="pread"><h3>この図から分かること</h3>'
            f'<p>{E(read["body"])}</p>'
            f'<p class="pnote">この文章は、上の束の形と数字だけを材料に、'
            f'{E(read.get("at") or "")} に作りました。'
            + ("<b>そのあとで網が変わっていますので、作り直せます。</b>" if stale
               else "網が変わったら作り直せます。") + "</p>"
            '<button data-pread="1">この図から分かる文章を作り直す</button>'
            '<span class="said"></span></div>')
    else:
        read_block = (
            '<div class="pread"><p class="pnote"><b>この図から分かる文章はまだ'
            '作っていません。</b>押すと、上の束の形と数字だけを材料に、'
            'この図で言えることを 1 段落にまとめます（1 分ほどかかります）。</p>'
            '<button data-pread="1">この図から分かる文章を作る</button>'
            '<span class="said"></span></div>')
    tdata = _time_payload(tl)
    n_stages = len(tl["stages"]) - 1          # 「いま」を除いた、実際に網が変わった段の数
    u = tl["unchanged"]
    n_unchanged = sum(u.values())
    gap_txt = (
        f'上演日が分からない記録が {tl["n_undated"]} 件あります。時間の上に置けないので、'
        f'さかのぼるとこの分（{tl["gap_people"]} 名）は網から外れます。'
        f'<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>の「公演詳細を直す」から'
        '日付を入れると載ります。')
    unchanged_txt = (
        f'このつまみに出るのは、網が変わった {n_stages} 件です。<b>残り {n_unchanged} 件は、'
        '観た日には網が変わりませんでした</b> ── '
        f'{u["not_yet"]} 件は、そのときまだ 1 回しか観ていない方ばかりの公演です'
        '（同じ方をもう 1 本観た日に、網に入りました）。'
        f'{u["repeat"]} 件は同じ顔ぶれをもう一度観た公演、{u["no_credit"]} 件は出演者が'
        '取れていない公演です。'
        f'1 件ずつは<a href="/records/works?t=__TAGURI_TOKEN__">日記帳</a>で読めます。')
    time_block = f"""<div class="ptime">
<div class="ptrow">
<button type="button" class="ptplay" data-pplay>▶ はじめから見る</button>
<input type="range" class="ptsl" data-psl min="0" max="{n_stages}" value="{n_stages}"
 aria-label="観た順に、網がどう育ったかを見る">
</div>
<div data-pnstage aria-live="polite"></div>
<p class="lead ptgap" data-pgap hidden>{gap_txt}</p>
<p class="lead">{unchanged_txt}</p>
<script type="application/json" data-pnet-time>{tdata}</script>
</div>""" if n_stages else ""
    # **横幅いっぱいに 1 つずつ置く**（起案者の指示・2026-08-24）。2 列に詰めると
    # 名前が重なって読めない ── 図の中身は名前そのものである
    return f"""<section class="card wide">
{IC.h2("user", "一緒に出てくる人の網 ── 束をつないでいるのは誰か",
       f'<span class="badge part">{len(ns)} 名・クレジットを取れた {g["n_works"]} 作品</span>')}
<p class="lead">同じ作品に一緒に居た方どうしを線で結んでいます。<b>2 作品以上で出てきた
{len(g["nodes"])} 名のうち、線を持つ {len(ns)} 名</b>を出しています
（全員は {g["n_people"]} 名です）。{iso_txt}</p>
<p class="lead">この図で分かるのは、<b>束がいくつあるか</b>と、
<b>どの方が束をつないでいるか</b>です。
いまは、線を持つ {len(ns)} 名が
<b>{"ひと続きの束です" if len(comps) == 1 else f"{len(comps)} 個の束に分かれています"}</b>。
{cut_txt}</p>
{read_block}
{time_block}
<div class="pcut">{cut_btns}
<button data-cut="reset" class="rst" hidden>全員を戻す</button></div>
<p class="psaid" data-psaid aria-live="polite"></p>
<div class="pnet" data-pnet>
<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" role="img"
 aria-label="一緒に出てくる人の網">
<g class="ed" stroke="var(--base)">{"".join(lines)}</g>
<g class="nds">{"".join(dots)}</g>
<g class="nls">{labs}</g></svg>
<div class="ptip" data-ptip hidden></div>
<script type="application/json" data-pnet-data>{data}</script></div>
<p class="pkey"><span class="ky"><span class="sw s1"></span>出演</span>
<span class="ky"><span class="sw s2"></span>作り手（演出・脚本ほか）</span>
<span class="ky"><span class="sw ring"></span>外すと束が割れる方</span>
<span class="ky">点の大きさ ＝ 観た作品数</span>
<span class="ky">線の太さ ＝ 一緒に居た作品数</span></p>
<p class="lead"><b>点はつまんで動かせます。</b>触れるとその方の線だけが浮きます
（下の表の行に触れても同じところが浮きます）。評価は色にも大きさにも入れていません。
気になる方がいたら、<a href="/recommend/favourites?t=__TAGURI_TOKEN__">お気に入り</a>に
名前で登録してください。<br>
<b>作り手が分かったのは、評価済み {g["n_rated"]} 作品のうち {g["n_works"]} 件です</b> ──
残り {g["n_rated"] - g["n_works"]} 件はこの図に入っていません。出演者と作り手（演出・脚本ほか）
だけを数え、制作・宣伝などの役職は入れていません。図に名前を書いたのは
{LABEL_MIN} 作品以上の方と、束をつないでいる方だけです。ほかの方は点に触れると名前が出ます。</p>
{table}</section>"""


def _payload(g: dict, pos: dict, rad: dict, idx: dict) -> str:
    """画面側に渡す網の中身。

    **`<script type="application/json">` に入れる。** 属性に詰めると読めない大きさになり、
    JavaScript の literal に書くと引用符の逃がし忘れが 1 か所で画面ごと壊れる。
    **`<` と `&` は必ず `\\u` に逃がす** ── 名前に `<` が入っていなくても、
    `</script` の並びが 1 度でも出れば、そこでこのタグが閉じてしまう。
    """
    ns = g["core"]
    nodes = [{"n": p, "w": g["cnt"][p], "d": len(g["adj"][p]),
              "m": 1 if _is_maker(g, p) else 0, "c": 1 if p in set(g["cuts"]) else 0,
              "x": round(pos[p][0], 1), "y": round(pos[p][1], 1), "r": round(rad[p], 1),
              "t": [[t, CH._anchor(k)] for t, k in g["titles"][p]]} for p in ns]
    edges = [[idx[a], idx[b], w] for (a, b), w in g["edges"].items()]
    raw = json.dumps({"w": W, "h": H, "pad": PAD, "nodes": nodes, "edges": edges},
                     ensure_ascii=False, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace("&", "\\u0026")


CSS = """
/* ---- 一緒に出てくる人の網 --------------------------------------------------
   地（線）は退かせ、点と名前を前に出す。**重なった点は地の色の輪で分ける**
   （2px の隙間を作る規則）。名前は点の上に来ても読めるように縁を先に塗る。 */
.pnet{position:relative;margin:12px 0 4px;overflow-x:auto}
.pnet svg{display:block;min-width:520px;touch-action:none}
.pnet .nd circle{stroke:var(--surf);stroke-width:2;paint-order:stroke;cursor:grab}
.pnet .nd.cut circle{stroke:var(--ink);stroke-width:2.4}
.pnet .nd:hover circle,.pnet .nd.on circle{stroke:var(--ink);stroke-width:2.6}
.pnet .nl{font-size:11.5px;fill:var(--ink2);dominant-baseline:middle;
 paint-order:stroke;stroke:var(--surf);stroke-width:3.4;stroke-linejoin:round;
 pointer-events:none}
/* **浮かせるのは、下げることで作る。** 触れた 1 人の線を太くするのではなく、
   関係の無い線と点を退かせる ── 太くすると「一緒に居た作品数」の意味が壊れる */
.pnet.lit .ed line{stroke-opacity:.07}
.pnet.lit .ed line.on{stroke-opacity:.85;stroke:var(--ink2)}
.pnet.lit .nd{opacity:.22}
.pnet.lit .nd.on,.pnet.lit .nd.near{opacity:1}
.pnet.lit .nl{opacity:.12}
.pnet.lit .nl.on,.pnet.lit .nl.near{opacity:1}
/* 外した人。**消さずに、外れていることが見える形にする** */
.pnet .nd.out{opacity:.28}
.pnet .nd.out circle{fill:none;stroke:var(--mute);stroke-width:2;stroke-dasharray:3 3}
.pnet .ed line.out{display:none}
.pnet .nl.out{display:none}
/* 割れた束の輪。**色ではなく囲いで示す** ── 束の数は色の数ではないので、
   枠が増えたことが数として読めるほうがよい */
.pnet .hull{fill:var(--ink);fill-opacity:.045;stroke:var(--base);stroke-width:1;
 stroke-dasharray:5 4}
.ptip{position:absolute;z-index:3;max-width:268px;background:var(--surf);
 border:1px solid var(--ring);border-radius:10px;padding:9px 12px;font-size:12.5px;
 color:var(--ink2);box-shadow:0 6px 22px rgba(0,0,0,.14);pointer-events:none}
.ptip b{color:var(--ink)}
.ptip .tw{display:block;margin:5px 0 0;color:var(--mute);font-size:11.5px}
.pcut{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px;align-items:center}
/* **`hidden` 属性は、同じ強さの `display` 指定に負ける。** 時間のつまみで過去を
   見ているあいだ、この帯を消すために要る（`display:flex` が UA の既定を上書きする） */
.pcut[hidden]{display:none}
.pcut button{font:inherit;font-size:12.5px;padding:5px 13px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer}
.pcut button:hover{border-color:var(--acc);color:var(--acc)}
.pcut button.on{border-color:var(--acc);color:var(--acc);font-weight:600}
.pcut button .cn{color:var(--mute);font-size:11px;margin-left:7px}
.pcut button.rst{border-style:dashed}
/* `ch`→`em`（render_recommend.py の `.lead` と同じ理由） */
.psaid{margin:0 0 8px;font-size:13px;color:var(--ink2);min-height:1.3em;max-width:74em}
.psaid b{color:var(--ink)}
.pkey{display:flex;gap:16px;flex-wrap:wrap;margin:2px 0 12px;font-size:12px;
 color:var(--mute)}
.pkey .ky{display:inline-flex;gap:6px;align-items:center}
.pkey .sw{width:11px;height:11px;border-radius:50%;flex:none}
.pkey .sw.s1{background:var(--s1)}
.pkey .sw.s2{background:var(--s2)}
.pkey .sw.ring{background:transparent;border:2.4px solid var(--ink)}
/* ---- 時間のつまみ。**配置は変えず、隠すだけ**（`.future` は物理からも隠される） */
.pnet .nd.future,.pnet .ed line.future,.pnet .nl.future{display:none}
.ptime{margin:2px 0 10px}
.ptrow{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 8px}
.ptrow .ptplay{font:inherit;font-size:12.5px;padding:5px 13px;border-radius:99px;
 border:1px solid var(--ring);background:var(--surf);color:var(--ink2);cursor:pointer;
 flex:none}
.ptrow .ptplay:hover{border-color:var(--acc);color:var(--acc)}
.ptrow .ptsl{flex:1 1 220px;min-width:160px;accent-color:var(--acc);cursor:pointer;margin:0}
.pnstage{margin:0 0 6px;font-size:13px;color:var(--ink2);max-width:74em}
.pnstage b{color:var(--ink)}
.pnstage a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--ring)}
/* ---- この図から分かること（LLM の読み。`chronicle.py` の `.chprofile` と同じ形） -------- */
.pread{background:var(--surf);border:1px solid var(--grid);border-left:3px solid var(--curtain);
 border-radius:0 8px 8px 0;padding:14px 16px;margin:2px 0 14px}
.pread h3{font-size:12.5px;margin:0 0 6px;color:var(--curtain);font-weight:600}
.pread p{margin:0 0 8px;font-size:14px;line-height:1.75;color:var(--ink);max-width:74em}
.pread .pnote{font-size:11.5px;color:var(--mute);line-height:1.7;max-width:74em;margin:0 0 8px}
.pread button{font:inherit;font-size:12.5px;padding:6px 14px;border-radius:6px;
 border:1px solid var(--acc);background:var(--acc);color:var(--surf);cursor:pointer}
.pread .said{margin-left:10px;font-size:11.5px;color:var(--mute)}
@media (prefers-reduced-motion:reduce){
 /* **動きを減らす設定を尊重する。** 力学は 1 回だけ解いて止める（絵は同じ所に落ちる） */
 .pnet svg{transition:none}
}
"""

# ---------------------------------------------------------------------------- 画面側
#
# **外部の描画ライブラリは読まない**（画面から外部サイトを叩かないという守り・企画書 5 章
# の 5）。力学は 54 点・207 辺なので、総当たりの斥力でも 1 フレーム 1,431 組しかない ──
# 近似（Barnes-Hut）を持ち込む必要が無い。
#
# **乱数を使わない。** 初期の位置は Python の力学配置をそのまま受け取り、画面側はそこから
# 続きを解く。**同じデータなら毎回同じ形に落ちる**ので、前に見た絵と見比べられる。
JS = r"""
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
"""


def main() -> int:
    import argparse                                                   # noqa: PLC0415
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="この図から分かる文章を作って保存する")
    ap.add_argument("--force", action="store_true", help="網が変わっていなくても作り直す")
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()
    if a.write:
        r = write(a.model, a.force)
        print(r.get("line", ""))
        return 0 if r.get("ok") else 1
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import app                                                         # noqa: PLC0415
    rated = app._records_base()["rated_rows"]
    g = build(rated)
    idx = {p: i for i, p in enumerate(g["core"])}
    print(json.dumps(facts(g, components(g), timeline(rated, g, idx)),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
