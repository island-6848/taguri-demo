#!/usr/bin/env python3
"""検証 031: 名簿の「もうひと段階」を 3 通り測る。

    python3 tools/review/measure_pairs.py            # 件数だけ出す
    python3 tools/review/measure_pairs.py --names    # 人物名も出す（当事者に見せない）

起案者の指摘 ──「ただ同じ人のこれだけ観ているってことがわかっても意味ない。それが
分かったから私にとって何が新しく分かるのか。たとえば、その人同士の組み合わせにも共通して
いる部分があるとか、ただ名簿を出すだけじゃなくてもうひと段階おもしろい機能が必要」。

測るのは 3 つ。
  ① 人の組み合わせ（2 人組）が、単体の名簿より何かを足すか
  ② 人以外の構造（翻訳の有無・原作の有無・出演人数など）で ◎ が偏るか
  ③ 「あなたの 1 本 → 今かかっている 1 本」の対（同じ戯曲・同じ作者）が、候補側に何件あるか
  ④ その対を「好み側の集計」に振ったとき（◎ が誰に集まっているか）、新しいことが言えるか
  ⑤ 名簿から「登録する価値のある名前」を出したとき、いま買える公演に何件届くか

**既定では人物名を出さない。** 推定した括りを推薦以外の経路で当事者に見せると
V22b・V24b の測定を汚すため（タスク 000006 の完了条件）。名前が必要なときだけ --names を付ける。
"""

from __future__ import annotations

import argparse
import collections
import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))

import measure_nets as M  # noqa: E402

CANDS = ROOT / "data" / "review" / "candidates.jsonl"
AUTHOR_ROLES = {"脚本", "原作", "台本", "翻訳", "潤色", "脚色", "原案", "作"}
FRONT_ROLES = {"出演", "演出"} | AUTHOR_ROLES


def load_candidates() -> list[dict]:
    """candidates.jsonl は値の中に改行が入る行があるので、逐次デコードで読む。"""
    txt = CANDS.read_text(encoding="utf-8")
    dec, i, out = json.JSONDecoder(), 0, []
    while i < len(txt):
        while i < len(txt) and txt[i] in "\r\n\t ":
            i += 1
        if i >= len(txt):
            break
        obj, i = dec.raw_decode(txt, i)
        out.append(obj)
    return out


def norm_title(s: str) -> str:
    s = re.sub(r"[『』「」【】\[\]（）()\s　・:：〜~\-−–—!！?？,、。]", "", s or "")
    for w in ("ミュージカル", "舞台", "演劇", "公演", "プロデュース", "上演", "新作", "再演", "版"):
        s = s.replace(w, "")
    return s


def author_names(c: dict) -> set[str]:
    out: set[str] = set()
    for k, v in (c.get("fields") or {}).items():
        if k in AUTHOR_ROLES or M.canon_role(M._clean_role(k)) in AUTHOR_ROLES:
            out |= set(M._names(v))
    return {n for n in out if len(n) >= 2}


# ---------------------------------------------------------------- ① 2 人組
def pairs(rows: list[dict], show_names: bool) -> None:
    hit = lambda r: r["verdict"] == "◎"                      # noqa: E731
    base = sum(hit(r) for r in rows) / len(rows)
    solo: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        for na in {na for _, na in r["people"]}:
            solo[na][0] += 1
            solo[na][1] += hit(r)
    pair: dict[tuple[str, str], list] = collections.defaultdict(lambda: [0, 0, []])
    for r in rows:
        for a, b in itertools.combinations(sorted({na for _, na in r["people"]}), 2):
            e = pair[(a, b)]
            e[0] += 1
            e[1] += hit(r)
            e[2].append(r)

    kept = {k: v for k, v in pair.items() if v[0] >= 3}
    one_venue = sum(1 for _, (n, o, ws) in kept.items()
                    if len({v for w in ws for v in w["venues"]}) <= 1)
    better = []
    for (a, b), (n, o, ws) in kept.items():
        ra, rb = solo[a][1] / solo[a][0], solo[b][1] / solo[b][0]
        if o / n > max(ra, rb) + 1e-9:
            better.append(((a, b), n, o / n, ra, rb, ws))

    print(f"① 2 人組（標本 {len(rows)} 作品・◎ の基準線 {base:.0%}）")
    print(f"   全 {len(pair):,} 種 / n>=3 が {len(kept)} 種")
    print(f"   組の ◎ 率が 2 人それぞれの単体を上回る組: {len(better)} 種")
    print(f"   n>=3 の組のうち、観た公演の劇場が 1 つに収まる（座組の言い換え）: {one_venue} 種")
    if show_names:
        for (a, b), n, rp, ra, rb, ws in sorted(better, key=lambda x: -x[1]):
            print(f"     {a} × {b} n={n} 組◎{rp:.0%} 単体 {ra:.0%}・{rb:.0%}")


# ---------------------------------------------------------------- ② 人以外の構造
def structure(rows: list[dict]) -> None:
    hit = lambda r: r["verdict"] == "◎"                      # noqa: E731
    roles = lambda r: {ro for ro, _ in r["people"]}          # noqa: E731
    print("\n② 人以外の構造（◎ 率）")
    for label, pred in [
        ("翻訳がある", lambda r: "翻訳" in roles(r)),
        ("原作・原案がある", lambda r: {"原作", "原案"} & roles(r) != set()),
        ("音楽・作曲がある", lambda r: {"音楽", "作曲"} & roles(r) != set()),
        ("振付がある", lambda r: "振付" in roles(r)),
    ]:
        a = [r for r in rows if pred(r)]
        b = [r for r in rows if not pred(r)]
        ra = sum(hit(r) for r in a) / len(a) if a else 0
        rb = sum(hit(r) for r in b) / len(b) if b else 0
        print(f"   {label:16s} 該当 {len(a):3d} 件 ◎{ra:4.0%} / 非該当 {len(b):3d} 件 ◎{rb:4.0%}")
    n_cast = lambda r: len({na for ro, na in r["people"] if ro == "出演"})   # noqa: E731
    for lo, hi, label in [(0, 1, "0 名（取得失敗）"), (1, 5, "1〜4 名"),
                          (5, 10, "5〜9 名"), (10, 20, "10〜19 名"), (20, 999, "20 名以上")]:
        a = [r for r in rows if lo <= n_cast(r) < hi]
        if a:
            print(f"   出演 {label:14s} {len(a):3d} 件 ◎{sum(hit(r) for r in a)/len(a):4.0%}")


# ---------------------------------------------------------------- ③ 作品どうしの対
def work_links(rows: list[dict], cands: list[dict], show_names: bool) -> None:
    print(f"\n③ 「あなたの 1 本 → 今かかっている 1 本」の対（候補 {len(cands)} 件に対して）")
    rated = {}
    for r in rows:
        rated.setdefault(norm_title(r["title"]), r)
    same, seen = [], set()
    for c in cands:
        n = norm_title(c["title"])
        for k, r in rated.items():
            if len(k) >= 4 and len(n) >= 4 and (k in n or n in k) and (k, n) not in seen:
                seen.add((k, n))
                same.append((r, c))
                break
    print(f"   同じ題名の別公演（同じ戯曲の別演出）: {len(same)} 件")
    if show_names:
        for r, c in same:
            print(f"     {r['verdict']} 「{r['title'][:26]}」({r['date']}) → 「{c['title'][:26]}」")

    by_author: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        for ro, na in r["people"]:
            if ro in AUTHOR_ROLES:
                by_author[na].append(r)
    good = {n for n, v in by_author.items() if any(x["verdict"] == "◎" for x in v)}
    uniq: dict[str, tuple[dict, set[str]]] = {}
    n_shows = 0
    for c in cands:
        s = author_names(c) & good
        if s:
            n_shows += 1
            uniq.setdefault(norm_title(c["title"]), (c, s))
    print(f"   ◎ を付けた作品の作者による別の作品: {len(uniq)} 作品（延べ {n_shows} 公演）"
          f" ／ 作者は {len(good)} 名が対象")
    filled = sum(1 for c in cands if author_names(c))
    print(f"   候補のうち作者の欄が埋まっているもの: {filled} 件（{filled/len(cands):.0%}）")
    if show_names:
        for _, (c, s) in uniq.items():
            print(f"     {'・'.join(sorted(s))} → 「{c['title'][:30]}」 {c.get('status')}")


# ---------------------------------------------------------------- ④ ◎ の集中
def concentration(rows: list[dict], show_names: bool) -> None:
    """対を「好み側の集計」に振ったときに何が言えるかを数える。

    ◎ が少数の人に集まっていれば「あなたの当たりはこの人に集まっている」と書けるが、
    集まりの中身が連続上演や同じ公演の再訪なら、本人が既に知っていることしか言えない。
    """
    maru = [r for r in rows if r["verdict"] == "◎"]
    print(f"\n④ ◎ の集中（◎ は {len(maru)} 件）")
    for label, pred in [
        ("作者（脚本・原作・翻訳など）", lambda ro: ro in AUTHOR_ROLES),
        ("演出", lambda ro: ro == "演出"),
        ("出演", lambda ro: ro == "出演"),
    ]:
        d: dict[str, set[str]] = collections.defaultdict(set)
        for r in maru:
            for ro, na in r["people"]:
                if pred(ro):
                    d[na].add(r["title"])
        multi = {n: v for n, v in d.items() if len(v) >= 2}
        covered = {t for v in multi.values() for t in v}
        print(f"   {label:22s} ◎ に 2 回以上出る人 {len(multi):3d} 名 / "
              f"その人が関わる ◎ 作品 {len(covered):3d} 件（{len(covered)/len(maru):.0%}）")
        if show_names:
            for n, v in sorted(multi.items(), key=lambda x: -len(x[1]))[:5]:
                print(f"     {n}: {len(v)} 件 ── {'／'.join(sorted(v)[:3])[:60]}")
    print("   ※ 中身は連続上演（デカローグ 1〜10）と同じ公演の再訪（作品1）に偏る。"
          "本人が自覚している集まりしか出ない")


# ---------------------------------------------------------------- ⑤ 登録候補の到達
def promotion_reach(rows: list[dict], cands: list[dict], show_names: bool) -> None:
    """名簿の行を「登録候補」に変えたとき、いま買える公演に何件届くかを数える。

    名簿をそのまま見せると「ふーん」で終わるので、行に次の行動（登録）と、
    登録したら新着枠に入る件数を添えたい。その件数が実際に出るかを測る。
    """
    from measure_own_knowledge import is_declared, nz          # 申告の判定を再利用する

    hit = lambda r: r["verdict"] == "◎"                        # noqa: E731
    base = sum(hit(r) for r in rows) / len(rows)
    tally: dict[tuple[str, str], list[int]] = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        for ro, na in r["people"]:
            tally[(ro, na)][0] += 1
            tally[(ro, na)][1] += hit(r)

    print(f"\n⑤ 登録する価値のある名前が、いま買える公演に届くか（基準線 ◎ {base:.0%}）")
    for label, pred in [("表方（出演・演出・作者）", lambda ro: ro in FRONT_ROLES),
                        ("裏方ほか", lambda ro: ro not in FRONT_ROLES)]:
        n3 = {k: v for k, v in tally.items() if v[0] >= 3 and pred(k[0])}
        und = {k: v for k, v in n3.items() if not is_declared(nz(k[1]))}
        hi = {k: v for k, v in und.items() if v[1] / v[0] > base}
        reach: collections.Counter = collections.Counter()
        for c in cands:
            names = set(M._names(" ".join(str(v) for v in (c.get("fields") or {}).values())))
            for (ro, na), v in hi.items():
                if na in names:
                    reach[(ro, na)] += 1
        print(f"   {label}: n≧3 が {len(n3)} 件 / 申告外 {len(und)} 件 / "
              f"◎ 率が基準線超え {len(hi)} 件 → いま買える公演に {sum(reach.values())} 件"
              f"（届いた名前は {len(reach)} 名、届かない名前は {len(hi)-len(reach)} 名）")
        for (ro, na), cnt in reach.most_common():
            who = na if show_names else "（名前は伏せる）"
            print(f"     役職 {ro} / 観た {hi[(ro, na)][0]} 本・◎ {hi[(ro, na)][1]} 本 "
                  f"→ 候補 {cnt} 件  {who}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", action="store_true",
                    help="人物名も出す（推定した括りなので当事者には見せない）")
    args = ap.parse_args()
    rows = [r for r in M.load_rated() if r["people"]]
    pairs(rows, args.names)
    structure(rows)
    work_links(rows, load_candidates(), args.names)
    concentration(rows, args.names)
    promotion_reach(rows, load_candidates(), args.names)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
