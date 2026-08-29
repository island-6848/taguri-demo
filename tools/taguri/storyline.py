#!/usr/bin/env python3
"""年表を storyline で描く。**同じ作品に出たことを「セッション」として束ねる。**

起案者の指示（2026-08-24）──「年表を storyline visualization で可視化できませんか」
「同じ作品に出たことをセッションとして描画してみて」。

## 形

xkcd の映画の図が原型である。**横が時間、1 本の線が 1 人、同じ作品に出た人の線が
その日に束になって近づく。** 研究では線の交差・線の上下動・余白の 3 つを最小化する問題として
定式化されており、**最小化そのものは NP 困難**である（Tanahashi & Ma ほか）。

**重い解き方は要らない。** 実測でこの記録は線 28 本・セッション 29 個なので、
**セッションを日付順に見て、そこに居る人の直前の位置の平均に束を置く**という 1 回の走査で
足りる。交差の数は下の `crossings()` で数えられるようにしてある。

## セッションに出す人を絞る

**絞らないと描けない。** 実測（2026-08-24）── のべ 969 人、1 回の観劇に出てくる人は
中央値 19 人・最大 57 人である。研究例で読める図は 10〜25 人程度なので、
**4 回以上出てくる人（28 本）を既定にし、3 回以上（54 本)まで増やせるようにした。**

## 世界ごとに帯を分ける

**この記録は 2 つの世界に分かれており、4 年間で作り手が 1 人も重なっていない**
（実測 ── ミュージカル系 24 セッション・29 人／現代演劇系 14 セッション・20 人）。
別の世界の線を同じ帯に混ぜると、**交わらないものが交差して見える。** そこで
**世界（セッションの連結成分）ごとに帯を分ける** ── 帯が分かれていること自体が、
この図がいちばん最初に見せる事実である。

## この図が言えて、ほかの図が言えないこと

**「観る世界が乗り換わっている」。** 実測では 2022〜2023 はほぼミュージカル系だけで、
2024 から現代演劇系が増え、**2025 年後半はミュージカル系が 0 になっている。**
両方観た四半期は 16 期のうち 5 期だけである。

- 「人の網」は**塊が分かれていること**を言えるが、時間を持たないので乗り換わりは言えない
- 「作り手の再会」は**1 人ずつの続き方**を言えるが、世界ごとの入れ替わりは言えない
- 「観劇の年輪」は**いつ観たか**しか言えない

## 参照実装（yjm12321/storyflow-d3）との違い

起案者の指示で clone して読み、描き方を合わせた（2026-08-25）。**そろえたところと、
あえて変えたところを残しておく。**

| | 参照実装 | こちら | なぜ |
|---|---|---|---|
| 場所 | 背景の面・面に沿う名前 | **同じ** | 帯に切ると、分けたのがこちらの都合か性質かが読めない |
| 遠い点で面を切る | `splitLength`（px） | **同じ**（日で測る） | 横軸が日付なので px は縮尺で変わる |
| 名前 | 線に沿わせる（textPath） | **同じ** | 線が上下に動くので左端に固定できない |
| 強調 | 押して選ぶ・複数可・背景で解除 | **同じ** | 触れるだけでは 2 人を見比べられない |
| 曲線 | monotone | **同じ** | |
| 交差の数え方 | 実現行列 | 転倒数（同値） | 行列は人数の 2 乗のメモリを使うが得るものが無い |
| 並べ替えの締め | 束の中だけ・悪くなったら戻す | **同じ** | |
| 掃きの回数 | 3 | 20（最良を保持） | 実測では 3 で足りるが、増えても害が無い |
| ②整列 | **無い** | 論文どおり入れた | 参照実装は partial である |
| ③詰め込み | 束の平均へ固定倍率で寄せる | 論文の制約つき二次計画 | 論文に近いほうを採った |
| 横軸 | 場面の並び（等間隔） | **実際の日付** | 等間隔だと乗り換わりがいつ起きたか読めない |
| 場面 | 期間を持つ | 1 日（描くときだけ幅を持たせる） | 観劇は 1 日の出来事である |
| 場所の並べ替え | 場面ごとに大きさ順 | **しない**（固定） | こちらの世界は交わらない固定の集合なので、動かすと線が跳ねるだけ |

**参照実装の不具合は写していない。** `.sort` に渡している比較関数が 4 か所とも真偽値を
返しており（`return xWeight > yWeight` の形）、V8 では**並べ替えが起きない**ことを
実際に動かして確かめた。並べ直しの比較関数には `indexOf(x)` を 2 回書いている取り違えも
ある。**ただし「だから並べ替えが丸ごと効いていない」とまでは確かめていない** ──
レポートに入っている 3 回版と 300 回版の図は中身が違うので、どこかは効いている。

## 横軸は実際の日付にする

研究例は「観た順」（等間隔）を使うことが多いが、**乗り換わりを見せるのが狙いなので
実際の日付にした。** 等間隔にすると、2025 年後半にミュージカル系が消えたことが
「並びの中の位置」になってしまい、いつ消えたのかが読めない。

**同じ日に複数観た日は、束が重ならない最小の間隔まで押し広げる**（実測で 3 日ある）。
押し広げた分は数十日の空白の中に収まるので、時間の読みは壊れない。
"""

from __future__ import annotations

import collections
import datetime
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
for _p in ("review",):
    _s = str(ROOT / "tools" / _p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
import charts as CH                                                  # noqa: E402
import icons as IC                                                   # noqa: E402

E = lambda s: html.escape(str(s))                                   # noqa: E731

MIN_TIMES = 4        # 何回以上出てくる人を線にするか
GAP = 13.0           # 束の中で線と線をどれだけ離すか（px）
BAND_PAD = 34.0      # 世界と世界のあいだ（px）


def _d(s: str):
    try:
        return datetime.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def sessions_of(rated: list[dict], min_times: int = MIN_TIMES) -> tuple[list[dict], set]:
    """セッションの並びと、線にする人。

    **セッションは「1 回の観劇」である。** 同じ作品を別の日に観たら別のセッションになる ──
    束が近づくのは「その日、その作品で一緒だった」ことなので、日をまたいでまとめると
    いつ一緒だったのかが消える。
    """
    dated = [r for r in rated if _d(r.get("date") or "") and r.get("people")]
    n = collections.Counter()
    for r in dated:
        for p in {b for _a, b in r["people"]}:
            n[p] += 1
    keep = {p for p, v in n.items() if v >= min_times}
    out = []
    for r in sorted(dated, key=lambda x: x["date"]):
        ms = sorted({b for _a, b in r["people"]} & keep)
        if ms:
            out.append({"date": r["date"], "titles": [r["title"]],
                        "anchors": [CH._anchor(r["key"])], "members": ms})
    return _merge_same_day(out), keep


def _merge_same_day(sessions: list[dict]) -> list[dict]:
    """**同じ日に観た、座組を共有する公演を 1 つのセッションにまとめる。**

    実測で 2 組あった ── デカローグは 1 日に 2 演目を続けて観ており（2024-04-21 の
    1 と 3、2024-05-23 の 5 と 6）、どちらも座組を 17 人共有している。**その日 1 回の来場
    なので、セッションも 1 つである。**

    **まとめないと、同じ位置に同じ束が二重に描かれる。** 横に押し広げて分ける案は捨てた ──
    この記録の期間は約 4.5 年で 1 日あたり 0.55px しかないので、束が離れて見えるまで
    押すと **29 日ぶんずれる。** 日付を歪めてまで分ける価値は無い。

    **人を共有しないときはまとめない。** 同じ日に別の世界の公演を観ることはありうるので、
    共有が無いものをまとめると**繋がっていない世界を繋げてしまう。**
    """
    out: list[dict] = []
    for s in sessions:
        for t in out:
            if t["date"] == s["date"] and set(t["members"]) & set(s["members"]):
                t["titles"] += s["titles"]
                t["anchors"] += s["anchors"]
                t["members"] = sorted(set(t["members"]) | set(s["members"]))
                break
        else:
            out.append(dict(s))
    return out


def worlds_of(sessions: list[dict]) -> list[list[int]]:
    """**人を共有しないセッションの塊に分ける。** 大きい順。

    別の世界の線を同じ帯に置くと、交わらないものが交差して見える。
    """
    par = list(range(len(sessions)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            if set(sessions[i]["members"]) & set(sessions[j]["members"]):
                par[find(i)] = find(j)
    g = collections.defaultdict(list)
    for i in range(len(sessions)):
        g[find(i)].append(i)
    return sorted(g.values(), key=lambda idx: (-len(idx), sessions[idx[0]]["date"]))


# ---------------------------------------------------------------- StoryFlow の 3 段
#
# 起案者の指示（2026-08-24）──「Storyline の StoryFlow の描画を論文を参照して改めて
# 書き直して」。
#
# 参照 ── Liu, Wu, Wei, Liu, Liu「StoryFlow: Tracking the Evolution of Stories」
# (IEEE InfoVis / TVCG 19(12): 2436-2445, 2013)。**配置を 3 段に分ける**設計である。
#
# | 段 | 何を小さくするか | 論文の手 |
# |---|---|---|
# | ① ordering | **線の交差の数**（いちばん大事） | 重心法（barycenter）で前後に掃く |
# | ② alignment | **折れの数**（まっすぐな線を増やす） | 重み付き最長共通部分列（LCS） |
# | ③ compaction | **折れの大きさと余白** | 線形制約つき二次計画 |
#
# **前の実装は 1 段しか無かった。** 日付順に 1 回走査して「そこに居る人の直前の高さの平均に
# 束を置く」だけで、①の掃き戻しも②③も無かった。論文が段を分ける理由は
# **大事な指標を先に決め、後段が前段を壊さないようにする**ことで、論文自身が
# 「交差を減らすのがいちばん大事で、折れの数と対称性はそれより弱い」と書いている。
#
# ## この記録に当てると、論文の問題が 2 つ落ちる
#
# 論文は 1 つの場面に複数のセッションが並ぶ場合を扱うが、**この記録は 1 つの帯の 1 つの
# 日付にセッションが 1 つしか無い**（同じ日で座組を共有するものは `_merge_same_day` で
# まとめてある）。そのため
#
# - **セッションどうしの上下の並べ替えが要らない。** ①で決まるのは「束の中の人の並び」だけ
# - **同じ場面での間隔の制約（論文 5a・5d）が空になる。** ③は制約なしの凸二次計画になり、
#   ガウス・ザイデル反復で解ける ── **この環境には numpy も scipy も無い**ので、
#   論文が使っている内点法の既製品（Mosek）は使えない。制約が落ちたおかげで自前で解ける
#
# 論文は場所の階層（location tree）も扱うが、**この記録に階層は無い。** 交わらない世界を
# 帯として別々に配置しているので、関係木は「根 → セッション → 人」の 2 段である。
ALPHA = 0.1          # 論文 (3) の a ── まっすぐさと左右の対称さの釣り合い
BETA = 1.0           # 論文 (5) の b ── 折れの大きさと余白の釣り合い
SWEEPS = 20          # 論文 5.2 の掃きの上限（論文の実装も 20）
LINE_W = 2.8         # 線の太さ相当。論文は d_in・d_out をこれの倍数で決めている。
                     # **参照実装は 4px と太い** ── storyline は線が帯に見えるほうが
                     # 追いやすいので、間隔が許す範囲で太くした
D_IN = 3 * LINE_W    # 論文 (5c) ── 同じ束の中で隣り合う線の間隔（固定）
D_OUT = 9 * LINE_W   # 論文 (5d) ── 束に入っていない線との最小の間隔


def frames_of(sessions: list[dict], world: list[int]) -> list[dict]:
    """**場面ごとに「いま生きている線」を出す。**（論文の前提に合わせる）

    ## なぜ要るのか ── これが無いと束を貫く線が出る

    はじめは「人はその人が出たセッションにだけ点を持つ」形で描いていた。**その形では
    論文の hard constraint が効かない** ── 論文 4.2 は

        line adjacency: if entities are interacting, their lines must be placed
        adjacently. Otherwise, they must be separate.

    と定めているが、間の場面に位置を持たない線は、離すべき相手がそこに居ないので離せない。
    実測で **束に入っていない線が束を貫いている箇所が 20 か所**あった（作り手12の線が
    「ダブル・トラブル」の束の中を通っており、**出ていない公演に出ているように見える**）。
    これは見た目の粗さではなく、**図が嘘を描いている。**

    論文の図では、人の線は登場から退場まで途切れずに存在し、場面ごとに順番と高さを持つ。
    **そこに合わせる** ── はじめて出た場面から最後に出た場面までを「生きている」とし、
    出ていない場面でも順番と高さを与える（束には入れない）。
    """
    idx = sorted(world, key=lambda i: sessions[i]["date"])
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    for t, i in enumerate(idx):
        for m in sessions[i]["members"]:
            first.setdefault(m, t)
            last[m] = t
    out = []
    for t, i in enumerate(idx):
        members = set(sessions[i]["members"])
        live = {m for m in first if first[m] <= t <= last[m]}
        out.append({"i": i, "t": t, "date": sessions[i]["date"],
                    "members": sorted(members), "live": sorted(live),
                    "transit": sorted(live - members)})
    return out


def count_crossings(frames: list[dict], order: dict[int, list[str]]) -> int:
    """並びだけから交差の数を数える（論文 5.2 が最小化する量）。

    **生きている線すべてを見る。** 出ていない場面でも順番を持つので、**場面を飛ばした線の
    交差もここで数えられる** ── 前の実装は出た場面だけを見ており、並びが名前順でも
    必ず 0 になって**何も測っていなかった。**
    """
    n = 0
    for a, b in zip(frames, frames[1:]):
        ra = {m: r for r, m in enumerate(order[a["t"]])}
        rb = {m: r for r, m in enumerate(order[b["t"]])}
        both = sorted(set(ra) & set(rb))
        for x in range(len(both)):
            for y in range(x + 1, len(both)):
                p, q = both[x], both[y]
                if (ra[p] - ra[q]) * (rb[p] - rb[q]) < 0:
                    n += 1
    return n


def _pair_crossings(ref: list[str], cur: list[str]) -> int:
    """隣り合う 2 つの場面のあいだの交差の数。

    参考実装（yjm12321/storyflow-d3）は Sugiyama の「実現行列」で数えている ──
    行列の (上の行, 右の列) と (下の行, 左の列) の積を足す形である。**同じ値になるので
    転倒数で数える**（行列を組むと人数の 2 乗のメモリを使うが、得るものが無い）。
    """
    ra = {m: r for r, m in enumerate(ref)}
    both = [m for m in cur if m in ra]
    n = 0
    for i in range(len(both)):
        for j in range(i + 1, len(both)):
            if ra[both[i]] > ra[both[j]]:
                n += 1
    return n


def _reorder(frame: dict, ref: list[str]) -> list[str]:
    """1 つの場面の並びを、直前の場面の並びを基準に決める。

    ## 束の中だけを並べ替える（参考実装の sortRestrictions）

    参考実装は**並べ替えを束の中に閉じ込めている** ── 重心で並べ替える二重ループを
    `offset` から `offset + （束の人数）` の範囲で回し、束をまたいだ入れ替えを起こさない。
    これが論文の line adjacency（同じセッションの線は隣に並べる）の実装である。

    **前の実装はここが緩かった。** 束に入っていない線を「重みが束の平均より上か下か」で
    振り分けていたので、**同じ線が場面ごとに束の上と下を行き来し、そのたびに交差が生まれて
    いた。** 参考実装に合わせ、

    - 束の中は基準の順で並べる（重心法）
    - **束の外の線は基準の相対順をそのまま保つ**
    - **束を差し込む位置だけを選ぶ** ── 候補は「外の線の間」すべてで、交差がいちばん
      少ない位置を採る（外の線は 20 本ほどなので全部試せる）

    という形にした。参考実装には束の外に居る線が存在しない（登場人物は常にどこかの
    セッションに属する作りである）ため、差し込む位置を選ぶ部分はこちらで足した分である。
    """
    rank = {m: r for r, m in enumerate(ref)}
    inf = float("inf")
    blk = sorted(frame["members"], key=lambda m: (rank.get(m, inf), m))
    out = [m for m in frame["transit"] if m in rank]
    out.sort(key=lambda m: rank[m])
    out += sorted(m for m in frame["transit"] if m not in rank)
    best, best_n = None, None
    for k in range(len(out) + 1):
        cand = out[:k] + blk + out[k:]
        n = _pair_crossings(ref, cand)
        if best_n is None or n < best_n:
            best_n, best = n, cand
    return best


def order_sweep(frames: list[dict]) -> tuple[dict[int, list[str]], int, int]:
    """① ordering ── **交差をいちばん先に減らす**（論文 5.2）。

    **重心法で前後に掃く。** 直前に見た場面の並びを基準に、次の場面の並びを決める。
    最初から最後まで送ったら、最後を基準に戻る。

    ## 参考実装から取り込んだ 2 つ

    1. **悪くなったら戻す。** 参考実装は場面ごとに並べ替えの前後で交差を数え、
       **減らなかったら元の並びを返す**（`if (crossingsBefore <= crossingsAfter) return
       backupMapping`）。前の実装は掃き全体の合計でしか比べていなかったので、
       **ある場面だけが悪くなっても、合計が下がれば通っていた。**
    2. **並べ替えを束の中に閉じ込める**（`sortRestrictions`）── `_reorder` の注記に書いた。

    ## 掃きの回数 ── 参考実装の 3 回で足りていた

    掃きの上限は論文どおり 20 にしてあるが、**実測では 3 回で最小に達した**（参考実装の
    `sweepingMaxIterations: 3` と同じ）。それ以降は減らない。

    | 掃きの回数 | 0 | 1 | 2 | **3** | 4 | 5 | 6 |
    |---|---|---|---|---|---|---|---|
    | 帯 0 の交差 | 108 | 9 | 9 | **2** | 9 | 2 | 9 |
    | 帯 1 の交差 | 23 | 6 | 4 | **0** | 0 | 0 | 0 |

    **帯 0 は 9 と 2 を往復し、収束しない。** 重心法にはよくある振動で、
    **だから「いちばん少なかった並びを採る」ことが要る** ── 最後の掃きの結果を使うと、
    2 で済むところを 9 で描くことになる。上限を 20 のままにしてあるのは、
    往復しても最良を持っているので害が無く、記録が増えて 3 回で足りなくなったときに
    自動で拾えるからである。
    """
    order: dict[int, list[str]] = {}
    for f in frames:
        order[f["t"]] = list(f["members"]) + list(f["transit"])
    first = count_crossings(frames, order)
    best, best_n = {t: list(v) for t, v in order.items()}, first

    def sweep(seq: list[dict]) -> None:
        for k in range(1, len(seq)):
            ref = order[seq[k - 1]["t"]]
            f = seq[k]
            cand = _reorder(f, ref)
            # **悪くなったら戻す**（参考実装の crossingsBefore <= crossingsAfter）
            if _pair_crossings(ref, cand) < _pair_crossings(ref, order[f["t"]]):
                order[f["t"]] = cand

    for k in range(SWEEPS):
        sweep(frames if k % 2 == 0 else frames[::-1])
        n = count_crossings(frames, order)
        if n < best_n:
            best_n, best = n, {t: list(v) for t, v in order.items()}
        if best_n == 0:
            break
    return best, best_n, first


def align_frames(frames: list[dict], order: dict[int, list[str]]) -> list[tuple[int, int, str]]:
    """② alignment ── **まっすぐな線を増やす**（論文 5.3）。

    論文は隣り合う場面のセッション列を**重み付きの最長共通部分列**で対応づける。
    似ている度合いは論文 (3) の

        sim(l, r) =（両方に居る人の数）+ ALPHA ×（相対位置の近さ）

    である。**この記録は 1 つの場面にセッションが 1 つしか無いので、LCS の表が 1×1 になる**
    （同じ日で座組を共有するものは `_merge_same_day` でまとめてある）。表を組まずに同じ
    判定を 1 対 1 で行い、共有した人のうち**相対位置がいちばん近い人**を軸にする。

    軸の線は③で高さを等しくする（論文の制約 (5b)）ので、**その線がまっすぐになる。**
    """
    out = []
    for a, b in zip(frames, frames[1:]):
        sa, sb = set(a["members"]), set(b["members"])
        both = sa & sb
        if not both:
            continue
        oa, ob = order[a["t"]], order[b["t"]]
        na, nb = len(oa), len(ob)
        best, best_s = None, -1.0
        for m in sorted(both):
            ra = oa.index(m) / max(na - 1, 1)
            rb = ob.index(m) / max(nb - 1, 1)
            sc = len(both) + ALPHA * (1.0 - abs(ra - rb))
            if sc > best_s:
                best_s, best = sc, m
        out.append((a["t"], b["t"], best))
    return out


def _gaps(frame: dict, order: list[str]) -> list[float]:
    """並びの隣どうしに要る最小の間隔（論文 (5c)(5d)）。

    **同じ束の中は D_IN、それ以外は D_OUT。** これが「束に入っていない線を束から離す」
    という hard constraint そのものである。
    """
    mem = set(frame["members"])
    return [D_IN if (order[k] in mem and order[k + 1] in mem) else D_OUT
            for k in range(len(order) - 1)]


def _project(want: list[float], gaps: list[float]) -> list[float]:
    """**並びと最小間隔を守りながら、望みの高さにいちばん近い配置を返す。**

    z[k] = y[k] − Σgap を置くと「z が単調非減少」に化けるので、**隣接違反プーリング
    （pool adjacent violators）で厳密に解ける** ── 近似ではない。

    論文は制約つき二次計画を内点法の既製品（Mosek）で解いているが、**この環境には
    numpy も scipy も無い。** 制約が「並び順」と「最小間隔」だけなので、③の 1 反復を
    「制約を無視した更新 → この射影」に分けて交互に回す形にした。
    """
    cum, acc = [0.0], 0.0
    for g in gaps:
        acc += g
        cum.append(acc)
    z = [want[k] - cum[k] for k in range(len(want))]
    # プーリング ── 平均と重みの塊にまとめる
    stack: list[list[float]] = []                 # [値, 重み]
    for v in z:
        stack.append([v, 1.0])
        while len(stack) > 1 and stack[-2][0] > stack[-1][0] - 1e-12:
            v2, w2 = stack.pop()
            v1, w1 = stack.pop()
            stack.append([(v1 * w1 + v2 * w2) / (w1 + w2), w1 + w2])
    zz: list[float] = []
    for v, w in stack:
        zz += [v] * int(round(w))
    return [zz[k] + cum[k] for k in range(len(want))]


def compact(frames: list[dict], order: dict[int, list[str]],
            aligns: list[tuple[int, int, str]]) -> tuple[dict[int, dict[str, float]], int]:
    """③ compaction ── **折れの大きさと余白を小さくする**（論文 5.4）。

    論文 (5) は

        min Σ (y[i,j] − y[i,j+1])² + BETA × Σ y[i,j]²

    を (5a) 並び順・(5b) 整列の等式・(5c) 同じ束の間隔・(5d) 束の外との間隔のもとで解く。
    第 1 項が折れの大きさ、第 2 項が余白である。

    ## 起案者の実装の余白の項を試して、採らなかった

    起案者の実装（on6848/storyline_b4）は余白の項が論文と違い、**隣り合う束の境目
    そのもの**を見ている ── `λ × Σ（境目）（（下の線 − 上の線）− d_out）²`（λ = 0.2）。
    束と束の隙間を d_out ちょうどへ引くので、論文の「原点からの距離」より余白が直接縮む。
    **考え方としてはこちらのほうが良い。**

    **入れて測ったところ、この記録では悪くなった。**

    | | 論文の項 | 起案者の項 |
    |---|---|---|
    | 図の高さ | **583px** | 948px |
    | 収束 | 15〜16 反復 | 上限 600 に達して収束せず |

    理由は 2 つある。

    1. **この記録はほとんどが独りの線である。** ある場面で束に入っているのは数人で、
       残りは通っているだけなので、**隣り合う組のほぼ全部がすでに d_out の境目**である。
       隙間は制約だけで決まってしまい、罰の項は縮める余地をほとんど持たない。
    2. **解き方が違う。** 起案者の実装は OSQP を WebAssembly にして**全体を 1 つの
       二次計画として解いている**ので、場面の中で鎖のようにつながるこの項を正しく扱える。
       こちらは「制約を無視した 1 手 → 射影」を交互に回す形なので、**同じ場面の中で
       互いを引き合う項を入れると釣り合いが取れず、配置が流れる。**

    項だけを移しても解き方が追いつかない、というのが実測の結論である。**入れるなら
    二次計画の求解ごと持ってくることになる**（この環境には numpy も scipy も無いので、
    ADMM を自前で書くことになる）。

    **交互に回して解く。** 制約を無視した 1 手（隣の場面と原点へ引く平均）を取り、
    そのあと場面ごとに `_project` で並び順と最小間隔へ落とす。②で結んだ組は、軸の線の
    高さを両側で揃えてから射影する（論文 (5b)）。

    収束したかどうかを返り値の反復回数で確かめられるようにした。
    """
    y: dict[int, dict[str, float]] = {}
    for f in frames:
        o = order[f["t"]]
        g = _gaps(f, o)
        pos, acc = [0.0], 0.0
        for gg in g:
            acc += gg
            pos.append(acc)
        mid = sum(pos) / len(pos)
        y[f["t"]] = {m: pos[k] - mid for k, m in enumerate(o)}

    anchor = {(a, b): m for a, b, m in aligns}
    it = 0
    for it in range(1, 601):
        moved = 0.0
        for f in frames:
            t, o = f["t"], order[f["t"]]
            gaps = _gaps(f, o)
            want = []
            for m in o:
                nb = [y[s["t"]][m] for s in frames
                      if abs(s["t"] - t) == 1 and m in y[s["t"]]]
                # 折れの大きさ（隣の場面へ）と余白（原点へ）の釣り合い ── 論文 (5)
                want.append(sum(nb) / (len(nb) + BETA) if nb else 0.0)
            # (5b) 軸の線は隣の場面と同じ高さに寄せる
            for (a, b), m in anchor.items():
                if b == t and m in o:
                    want[o.index(m)] = y[a][m]
                elif a == t and m in o and (b, t) not in anchor:
                    pass
            new = _project(want, gaps)
            for k, m in enumerate(o):
                moved = max(moved, abs(new[k] - y[t][m]))
                y[t][m] = new[k]
        if moved < 1e-4:
            break
    _hold(frames, order, y)
    return y, it


SNAP = 4.0           # これ未満の高さの差は「動かなかった」ことにする


def _hold(frames: list[dict], order: dict[int, list[str]],
          y: dict[int, dict[str, float]], rounds: int = 12) -> None:
    """**わずかな差は「動かなかった」ことにする。**（起案者の指摘・2026-08-25）

    ## なぜ要るのか

    実測（2026-08-25）── 高さが変わる 176 箇所のうち **57 箇所（32%）は 3px 未満**で、
    詰め込みの計算結果が場面ごとにわずかに違うだけだった。**線は 0.4px の差でも S 字を
    描くので、この微動が全部「波」として見えていた。**（起案者の画面で確認）

    ## 描き方でごまかさない

    「小さい差は平らに描く」だけでは、**● や隣の線との間隔と線の位置がずれる。**
    そこで**配置の側で高さを揃え、そのあと制約を掛け直す。**

    揃えると並び順や最小間隔を破ることがあるが、**`_project` がその場で押し戻す**ので、
    破れたままにはならない ── 揃えられるところだけが揃う。何度か繰り返して、
    もう動かなくなったら終わる。
    """
    seq: dict[str, list[int]] = collections.defaultdict(list)
    for f in frames:
        for m in order[f["t"]]:
            seq[m].append(f["t"])
    for _ in range(rounds):
        changed = False
        for m, ts in seq.items():
            for a, b in zip(ts, ts[1:]):
                d = y[b][m] - y[a][m]
                if 0.0 < abs(d) < SNAP:
                    y[b][m] = y[a][m]
                    changed = True
        # 揃えたせいで並び順や間隔が壊れていたら押し戻す
        for f in frames:
            o = order[f["t"]]
            cur = [y[f["t"]][m] for m in o]
            fixed = _project(cur, _gaps(f, o))
            for k, m in enumerate(o):
                y[f["t"]][m] = fixed[k]
        if not changed:
            break


def layout(sessions: list[dict], world: list[int]) -> dict:
    """3 段を順に走らせて、線の高さを返す（① → ② → ③）。"""
    frames = frames_of(sessions, world)
    order, n_cross, n_first = order_sweep(frames)
    aligns = align_frames(frames, order)
    y, n_iter = compact(frames, order, aligns)
    lo = min(v for f in frames for v in y[f["t"]].values())
    placed = []
    for f in frames:
        pos = {m: y[f["t"]][m] - lo for m in order[f["t"]]}
        placed.append({"i": f["i"], "t": f["t"], "date": f["date"],
                       "members": f["members"], "transit": f["transit"],
                       "order": order[f["t"]],
                       # **束の高さは束に入っている人だけで測る。** 通っている線を
                       # 入れると、囲いが出ていない人まで囲うことになる
                       "pos": pos,
                       "bundle": {m: pos[m] for m in f["members"]},
                       "center": sum(pos[m] for m in f["members"]) / len(f["members"])})
    hi = max(v for p in placed for v in p["pos"].values())
    return {"placed": placed, "height": hi - lo,
            "people": sorted({m for p in placed for m in p["pos"]}),
            "cross_before": n_first, "cross_after": n_cross,
            "n_aligned": len(aligns), "compact_iters": n_iter}


def crossings(sessions: list[dict], placed: list[dict]) -> int:
    """**線と線が実際に交わる回数を数える。**

    **はじめは隣り合うセッションだけを見ていた。それでは何も測れない** ── 束の中は
    「直前の高さの順」に並べているので、隣り合う 2 つのセッションで順が入れ替わることは
    構造上ありえず、**どんな配置でも 0 になった。**

    線は自分が出ているセッションの点を順につないで描かれるので、**間のセッションを
    飛ばして引かれる区間がある。** そこで両方の線を全セッションの位置で補間し、
    **上下の差の符号が変わった回数**を数える。これが図の上で見える交差である。
    """
    xs = [sessions[p["i"]]["date"] for p in placed]
    order = {d: k for k, d in enumerate(xs)}
    # 1 人ずつの (位置, 高さ) の並び
    line: dict[str, list[tuple[int, float]]] = collections.defaultdict(list)
    for p in placed:
        k = order[sessions[p["i"]]["date"]]
        for m, yy in p["pos"].items():
            line[m].append((k, yy))
    for m in line:
        line[m].sort()

    def at(m: str, k: int):
        """位置 k での高さ。**自分の点の外側では引かない**（線が無い区間である）。"""
        pts = line[m]
        if k < pts[0][0] or k > pts[-1][0]:
            return None
        for (k0, y0), (k1, y1) in zip(pts, pts[1:]):
            if k0 <= k <= k1:
                return y0 if k1 == k0 else y0 + (y1 - y0) * (k - k0) / (k1 - k0)
        return pts[-1][1]

    names = sorted(line)
    n = 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            prev = None
            for k in range(len(xs)):
                ya, yb = at(a, k), at(b, k)
                if ya is None or yb is None:
                    prev = None
                    continue
                d = ya - yb
                if prev is not None and d != 0 and prev * d < 0:
                    n += 1
                if d != 0:
                    prev = d
    return n


MIN_GAP = 54.0       # 束と束のあいだに最低これだけ px を空ける（水平区間を作るため）
PX_PER_DAY = 0.8     # 空いているところの縮尺（日あたり px）
LEFT_PX = 84.0       # 左の名前の欄


def _xmap(dates: list[str]) -> tuple[dict[str, float], float]:
    """**束のある日付を横の位置に写す。**（順は日付どおり、詰まるところは広げる）

    ## なぜ実際の日付の比例では描けないのか

    実測（2026-08-25）── 束のある日付は 29 種類で全体は 1365 日。幅 1100px に比例で
    割ると **1 束あたり 25px、いちばん詰まったところは 0.8px** しか無い。
    storyline の線は「水平に走り、変わるときだけ S 字で移る」形なので、
    1 束につき最低でも **水平 7×2 ＋ S 字 26 = 40px** 要る。**入り切らないので、
    前半が折れ線の塊になっていた。**

    ## 順は保ち、詰まったところだけ広げる

    参照実装と論文は横軸を「場面の並び」（等間隔）にしている。**それだと乗り換わりが
    いつ起きたかが読めない**ので、こちらは**日付の順と大小関係は保ったまま、隣り合う束の
    間隔に下限を置く**（下限より広いところは実際の日数に比例する）。

    **空白は縮まない。** 下限を割るところだけが広がるので、9 か月空いた区間は
    ちゃんと長いままである ── 「いつ乗り換わったか」は読める。

    図は下限を満たすところまで横に伸びる（入れ物が横に流れる）。参照実装も同じ考えで、
    幅を 16000px に取っている。
    """
    xs: dict[str, float] = {}
    if not dates:
        return xs, LEFT_PX
    ds = sorted(set(dates))
    cur = LEFT_PX
    xs[ds[0]] = cur
    for a, b in zip(ds, ds[1:]):
        days = (_d(b) - _d(a)).days
        cur += max(MIN_GAP, days * PX_PER_DAY)
        xs[b] = cur
    return xs, cur + LEFT_PX / 2


RUN_PX = 7.0         # 束のところで線を少し水平に走らせる幅（px）


def build(rated: list[dict], min_times: int = MIN_TIMES) -> dict:
    """描くのに要るものを全部組む。**世界は帯に分けず、1 つの座標系に積む。**

    参照実装は場所を「背景の面」として描き、線と名前をその上に重ねる。**帯に切って別々に
    置くより、場所どうしの含み・隣り合いがそのまま形で出る** ── 論文が場所の階層を
    layout に入れている理由もそこにある。こちらの場所は交わらない 2 つの世界なので階層は
    無いが、**面にすると「この面とこの面は一度も重ならない」ことが図の地の部分で読める。**
    """
    sessions, keep = sessions_of(rated, min_times)
    if not sessions:
        return {"locations": [], "lines": [], "sessions": [], "from": "", "to": ""}
    locations, lines, ses, top = [], [], [], 0.0
    for wi, w in enumerate(worlds_of(sessions)):
        lay = layout(sessions, w)
        placed = lay["placed"]
        # --- 線（1 人 1 本）。**生きている場面すべてを通る**
        per: dict[str, list[dict]] = collections.defaultdict(list)
        for p in placed:
            for m, yy in p["pos"].items():
                per[m].append({"date": p["date"], "y": yy + top,
                               "on": m in p["members"]})
        for m, pts in sorted(per.items()):
            pts.sort(key=lambda x: x["date"])
            lines.append({"name": m, "loc": wi, "pts": pts,
                          "n": sum(1 for x in pts if x["on"]),
                          "from": pts[0]["date"], "to": pts[-1]["date"]})
        # --- 束（セッション）
        for p in placed:
            s = sessions[p["i"]]
            ses.append({"date": p["date"], "loc": wi, "titles": s["titles"],
                        "anchors": s["anchors"],
                        "y0": min(p["bundle"].values()) + top,
                        "y1": max(p["bundle"].values()) + top,
                        "n": len(p["members"])})
        # --- 世界ごとの覚え書き。**背景の面はもう描かない**（起案者の指示・2026-08-25）
        ds = sorted(p["date"] for p in placed)
        locations.append({
            "loc": wi,
            # 名札を置く場所 ── その世界のいちばん早い束の、いちばん上
            "lx": ds[0], "ly": min(v for p in placed for v in p["pos"].values()) + top,
            "n_people": len(lay["people"]), "n_sessions": len(placed),
            "from": ds[0], "to": ds[-1],
            "crossings": lay["cross_after"], "cross_before": lay["cross_before"],
            "n_aligned": lay["n_aligned"], "compact_iters": lay["compact_iters"],
            "examples": [t for p in placed[:3] for t in sessions[p["i"]]["titles"]][:3]})
        top += lay["height"] + BAND_PAD
    allds = sorted(s["date"] for s in sessions)
    n_all_people = len({b for r in rated if r.get("people") and _d(r.get("date") or "")
                        for _a, b in r["people"]})
    # 世界ごとのまとめ（説明文と表が読む）
    worlds = sorted(locations, key=lambda x: x["loc"])
    mx = max(s["date"] for s in ses)
    cut = (datetime.date.fromisoformat(mx) - datetime.timedelta(days=365)).isoformat()
    for wd in worlds:
        wd["recent"] = sum(1 for x in ses if x["loc"] == wd["loc"] and x["date"] >= cut)
    return {"lines": lines, "sessions": ses, "worlds": worlds,
            "height": top - BAND_PAD, "from": allds[0], "to": allds[-1],
            "min_times": min_times, "n_lines": len(keep),
            "n_people_all": n_all_people,
            "n_dated": len([r for r in rated if _d(r.get("date") or "")]),
            "n_credited": len([r for r in rated
                               if r.get("people") and _d(r.get("date") or "")])}


def _recent_line(worlds: list[dict]) -> str:
    """直近 1 年にどちらを観ているか。**言い過ぎない。**

    はじめは「まったく交わらない流れを並行して観ています」と書いたが、**自分で測った値と
    矛盾していた** ── 四半期ごとに数えると 2022〜2023 はほぼ一方だけで、2024 から
    もう一方が増えている。「並行」ではない。

    かといって「乗り換えた」とも書かない ── **直近 1 年でも少ないほうが 0 ではない。**
    書けるのは**どちらを何回観たか**までである。
    """
    act = [w for w in worlds if w["recent"]]
    if not act:
        return ""
    if len(act) == 1:
        w = act[0]
        return (f'<b>直近 1 年に束があるのは {w["loc"] + 1} つめだけで、'
                f'{w["recent"]} 回です。</b>ほかの流れは、この 1 年は観ていらっしゃいません。')
    top = max(act, key=lambda w: w["recent"])
    parts = "、".join(f'{w["loc"] + 1} つめが {w["recent"]} 回' for w in act)
    return (f'<b>直近 1 年は{parts}です</b> ── '
            f'いまは {top["loc"] + 1} つめのほうを多く観ていらっしゃいます。')


def panel(rated: list[dict], min_times: int = MIN_TIMES) -> str:
    """図とその説明。**載らなかった件数と、絞った人数を必ず書く。**"""
    d = build(rated, min_times)
    if not d.get("worlds"):
        return ""
    ws = d["worlds"]
    tbl = CH._table(
        ["いくつめの世界", "人数", "観に行った回数", "はじめ", "おわり", "作品の例"],
        [[f'{w["loc"] + 1} つめ', f'{w["n_people"]} 人', f'{w["n_sessions"]} 回',
          w["from"], w["to"], "、".join(t[:18] for t in w["examples"])] for w in ws])
    xs, width = _xmap([x["date"] for x in d["sessions"]])
    # **年の変わり目に目盛りを置く。** 位置を歪めてあるので普通の軸は引けない ──
    # その年の最初の束のところに年を出す（「この図ではここから 2024 年」と読める）
    ticks, seen_y = [], set()
    for dt in sorted(xs):
        if dt[:4] not in seen_y:
            seen_y.add(dt[:4])
            ticks.append({"x": xs[dt], "label": dt[:4] + " 年"})
    payload = json.dumps({"lines": d["lines"], "worlds": ws,
                          "sessions": d["sessions"], "height": d["height"],
                          "from": d["from"], "to": d["to"], "runPx": RUN_PX,
                          "X": xs, "width": width, "ticks": ticks,
                          "rowHref": CH.ROW_HREF}, ensure_ascii=False)
    return f"""<div class="card wide">{IC.h2("light", "同じ作品で一緒だった人の流れ")}
<p class="lead"><b>1 本の線が 1 人、横が時間です。同じ作品に出た方の線は、その日に束になります。</b>
<b>● が「その日その作品に出ていた」印です。</b>束が 1 つの公演で、押すとその記録へ移動します。<br>
<b>線の色は {len(ws)} つに分かれています</b> ──
{"、".join(f'{w["n_people"]} 人（{w["from"]} 〜 {w["to"]}）' for w in ws)}で、
<b>この {len(ws)} つのあいだで一緒に出た方は 1 人もいません。</b>
{_recent_line(ws)}<br>
線にしているのは <b>{min_times} 回以上観た {d["n_lines"]} 名</b>です
（作り手が分かっている {d["n_credited"]} 件の記録には、のべ {d["n_people_all"]} 名が出てきます）。
横に引っぱると時間を伸ばせます。<b>線を押すと、その方の流れだけが浮き上がります</b> ──
何人でも選べます。背景を押すと戻ります。</p>
<div class="sl-legend">{"".join(
    f'<span class="sl-k sl-w{w["loc"]}">{w["loc"] + 1} つめの世界 ── '
    f'{w["n_people"]} 人・{w["n_sessions"]} 回</span>' for w in ws)}
 <span class="sl-hint">（{d["from"]} 〜 {d["to"]}）</span></div>
<div id="sl" class="sl"></div>
<p class="sl-fallback">{tbl}</p>
</div>
<script id="sl-data" type="application/json">{payload}</script>""" + f"<script>{SCRIPT}</script>"


STYLE = """
/* ---- 同じ作品で一緒だった人の流れ（storyline） ------------------------------- */
.sl{margin:10px 0 2px;overflow-x:auto}
.sl svg{display:block}
.sl .ln{fill:none;stroke-width:2.6;stroke-linecap:round;stroke-opacity:.7}
.sl .ln.w0{stroke:var(--pos)}
.sl .ln.w1{stroke:var(--neg)}
.sl .ln.w2{stroke:var(--mute)}
.sl .ln.hot{stroke-opacity:1;stroke-width:4.4}
.sl .ln.dim{stroke-opacity:.10}
/* 束（セッション）。**面で示す。** 線と同じ描き方にすると束が読めない */
.sl .ses{fill:var(--ink2);fill-opacity:.09;stroke:none;cursor:pointer}
.sl .ses:hover{fill-opacity:.2}
.sl .st{font-size:10px;fill:var(--mute);pointer-events:none}
/* **束に入った日の印。** 線と同じ色にし、白で縁を取って重なっても数えられるようにする */
.sl .dot{pointer-events:none;stroke:var(--plane);stroke-width:1.1}
.sl .dot.w0{fill:var(--pos)}
.sl .dot.w1{fill:var(--neg)}
.sl .dot.w2{fill:var(--mute)}
.sl .dot.dim{opacity:.12}
/* **名前は線に沿わせる**（参照実装の textPath）。線が動くので左端に固定はできない */
.sl .nm{font-size:10.5px;pointer-events:none;font-weight:600}
.sl .nm.w0{fill:var(--pos)}
.sl .nm.w1{fill:var(--neg)}
.sl .nm.w2{fill:var(--mute)}
.sl .nm.dim{opacity:.12}
.sl .ax text{font-size:11px;fill:var(--mute)}
.sl .ax line,.sl .ax path{stroke:var(--grid)}
.sl-legend{display:flex;gap:14px;align-items:center;flex-wrap:wrap;font-size:12px;
 color:var(--mute);margin:6px 0 0}
.sl-k{display:inline-flex;align-items:center;gap:5px}
.sl-k::before{content:"";width:16px;height:3px;border-radius:2px;background:var(--ink2)}
.sl-k.sl-w0::before{background:var(--pos)}
.sl-k.sl-w1::before{background:var(--neg)}
.sl-k.sl-w2::before{background:var(--mute)}
.sl-hint{margin-left:auto}
.sl-fallback{font-size:12.5px;color:var(--mute);margin:8px 0 0}
.sl-tip{position:fixed;z-index:40;pointer-events:none;max-width:300px;
 background:var(--plane);border:1px solid var(--ring);border-radius:8px;
 padding:7px 10px;font-size:12.5px;line-height:1.6;color:var(--ink2);
 box-shadow:0 6px 20px rgba(0,0,0,.18)}
"""


# **描くのは d3 だが、配置は Python 側で決めてある。** 参照実装（yjm12321/storyflow-d3）の
# 描き方に合わせた ── 場所を背景の面にし、名前を線に沿わせ、遠く離れたところで面を切る。
SCRIPT = """
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

  root.call(d3.zoom().scaleExtent([1, 30])
    .translateExtent([[left, 0], [w - padR, h]])
    .extent([[left, 0], [w - padR, h]])
    // **位置はもう決まっているので、拡大縮小は写した px の上に掛ける**
    .on("zoom", ev => { tr = ev.transform; draw(); }));
})();
"""
