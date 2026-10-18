#!/usr/bin/env python3
"""題材の語彙表（cloudflare/src/vocab/concepts.json）を、起案者が見直せる木の形で書き出す。

    python3 tools/taguri/vocab_tree.py [--themes credits/themes.jsonl] [--unplaced N]

--themes を渡すと、概念ごとに当たる公演の数と、表のどこにも入っていない多い言葉を添える
（次に足す枝を選ぶため）。照合は Worker（src/vocab.js）と同じく、正規化した言葉の丸ごと一致。
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import unicodedata

VOCAB = pathlib.Path(__file__).resolve().parents[2] / "cloudflare/src/vocab/concepts.json"


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "").lower()


def load(path: pathlib.Path = VOCAB) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8"))["concepts"]


def words_of(concepts: dict[str, dict], name: str) -> set[str]:
    c = concepts[name]
    return {nz(w) for w in [name, *c.get("same", []), *c.get("words", [])]}


def tree(concepts: dict[str, dict], counts: dict[str, int] | None = None) -> list[str]:
    children = collections.defaultdict(list)
    for name, c in concepts.items():
        for b in c.get("broader", []):
            children[b].append(name)
    lines = []

    def walk(name: str, depth: int, parent: str = "") -> None:
        c = concepts[name]
        rel = "".join(f"〔関連〕{r}" for r in c.get("related", []))
        # 上位が複数ある概念は、それぞれの上位の下に出し、ほかの上位を添える
        also = "".join(f"〔上位にも〕{b}" for b in c.get("broader", []) if b != parent)
        n = f"（{counts[name]} 公演）" if counts is not None else ""
        same = "".join(f"＝{w}" for w in c.get("same", []))
        words = "／".join(c.get("words", []))
        lines.append(f"{'  ' * depth}- **{name}**{same}（{c.get('axis', '')}）{n} {rel}{also} {words}".rstrip())
        for ch in children[name]:
            walk(ch, depth + 1, name)

    for name, c in concepts.items():
        if not c.get("broader"):
            walk(name, 0)
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--themes", type=pathlib.Path)
    ap.add_argument("--unplaced", type=int, default=40)
    a = ap.parse_args()
    concepts = load()
    counts = None
    if a.themes:
        stages = [{nz(e.get("word", "")) for e in json.loads(l).get("elements") or []}
                  for l in a.themes.read_text(encoding="utf-8").splitlines() if l.strip()]
        counts = {n: sum(1 for ws in stages if ws & words_of(concepts, n)) for n in concepts}
    print("\n".join(tree(concepts, counts)))
    if counts is not None:
        placed = set().union(*(words_of(concepts, n) for n in concepts))
        rest = collections.Counter(w for ws in stages for w in ws if w and w not in placed)
        print(f"\n表に入っていない言葉（多い順 {a.unplaced} 件）: "
              + "、".join(f"{w}({n})" for w, n in rest.most_common(a.unplaced)))


if __name__ == "__main__":
    main()
