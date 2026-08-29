#!/usr/bin/env python3
"""網 C の抽出の**適合率**を目視で測るための標本を作る（V6c の残り半分）。

## なぜ必要か

[検証 033](../../docs/verification/033-net-c-on-candidates.md) は「あらすじが候補 818 件のうち
522 件で取れた」と測ったが、そこに **「これは V6c の合格判定ではない ── 適合率はまだ測っていない」**
と書いてある。V6c の基準は**目視の正解 50 件に対する適合率 9 割・再現率 7 割**である。
再現率の側は [検証 042](../../docs/verification/042-synopsis-prompt.md) で 6/6 まで来たが、
**適合率は 1 度も測っていない。**

**急ぐ理由は件数である。** 網 C を足すとスコアの付く候補が 29 件 → 136 件になり、
増えた 107 件は**すべて網 C だけで拾ったもの**である（検証 033）。中身が違っていれば、
増えた分はそのまま外れになる。さらに検証 042 で「取れた件数が上がった理由の一部は
精度の向上ではなく**境界の移動**（宣伝文と地続きでも取る）だった」と分かっている。

## この道具がすること

`themes.jsonl` の**要素が入っている行**から標本を取り、**LLM に実際に渡した本文を再現して**
1 行ずつの判定票を作る。判定は人が付ける（`--judged` で集計する）。

- 標本は `random.Random(seed).sample()` で取る。**seed を記録するので同じ標本を作り直せる。**
- 本文は `extract_theme_llm` の `targets()` をそのまま呼んで再現する。**取得は発生しない**
  （キャッシュのみ。`fetch=False`）。
- 機械で決まる検査は先に付ける ── ①あらすじが本文に実在するか（`verbatim`）、
  ②要素の語が本文に出てくるか、③宣伝の語か、④固有名詞らしいか。
  **これらは適合率そのものではない**（本文に無い語でも内容として正しいことがある）が、
  目で見る順番を決めるのに使う。

    python3 tools/review/sample_theme_precision.py --side candidate --n 50
    python3 tools/review/sample_theme_precision.py --judged docs/verification/data-045-theme-precision.json
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "credits"))
import extract_theme_llm as E  # noqa: E402

THEMES = ROOT / "data" / "credits" / "themes.jsonl"

# 宣伝の語 ── プロンプトが「出さない」と書いている語（c2 の指示）
AD_WORDS = {"感動", "衝撃", "話題", "必見", "圧巻", "傑作", "名作", "話題作", "大人気", "豪華"}


def load_themes(side: str) -> list[dict]:
    rows = [json.loads(l) for l in THEMES.read_text(encoding="utf-8").split("\n") if l.strip()]
    return [r for r in rows if r.get("elements") and (side == "both" or r["side"] == side)]


def proper_noun_like(word: str) -> bool:
    """固有名詞らしいか（片仮名 4 字以上・漢字 1〜3 字＋「氏」など、の粗い目印）。
    **判定ではなく目印である。** kind が「原作」のときは固有名詞でよい。"""
    return bool(re.fullmatch(r"[ァ-ー]{4,}", word))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", default="candidate", choices=["candidate", "rated", "both"])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260824)
    ap.add_argument("--body-limit", type=int, default=3200)
    ap.add_argument("--out", type=Path,
                    default=ROOT / "docs" / "verification" / "data-045-theme-precision.json")
    ap.add_argument("--judged", type=Path, help="判定済みの票を集計する")
    a = ap.parse_args()

    if a.judged:
        return report(a.judged)

    rows = load_themes(a.side)
    by_id = {r["id"]: r for r in rows}
    picked = random.Random(a.seed).sample(sorted(by_id), min(a.n, len(by_id)))

    # 本文を再現する（キャッシュのみ・取得なし）
    bodies = {t["id"]: t for t in E.targets(a.side if a.side != "both" else "candidate", fetch=False)}

    out = {"seed": a.seed, "side": a.side, "n": len(picked),
           "母数": {"要素が入っている行": len(rows)}, "rows": []}
    for i, sid in enumerate(picked, 1):
        r = by_id[sid]
        t = bodies.get(sid, {})
        body = (t.get("text") or "")[:a.body_limit]
        out["rows"].append({
            "i": i, "id": sid, "title": r["title"], "url": r.get("url", ""),
            "prompt_version": r.get("prompt_version"), "synopsis": r["synopsis"],
            "あらすじが本文に実在": E.verbatim(r["synopsis"], t.get("text") or ""),
            "本文の長さ": len(t.get("text") or ""),
            "elements": [{
                "kind": e["kind"], "word": e["word"],
                "語が本文にある": bool(t.get("text")) and e["word"] in (t.get("text") or ""),
                "宣伝の語": e["word"] in AD_WORDS,
                "固有名詞らしい": proper_noun_like(e["word"]),
                "判定": None,      # 正／誤／判定不能 を人が入れる
                "誤りの型": None,  # 別公演／本文に無い／宣伝文／粒度／固有名詞
            } for e in r["elements"]],
            "body": body,
        })
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"標本 {len(picked)} 行・要素 {sum(len(r['elements']) for r in out['rows'])} 個 → {a.out}")
    print(f"本文が再現できなかった行: {sum(1 for r in out['rows'] if not r['body'])}")
    return 0


def report(path: Path) -> int:
    d = json.loads(path.read_text(encoding="utf-8"))
    els = [e for r in d["rows"] for e in r["elements"]]
    judged = [e for e in els if e["判定"]]
    ok = [e for e in judged if e["判定"] == "正"]
    ng = [e for e in judged if e["判定"] == "誤"]
    unk = [e for e in judged if e["判定"] == "判定不能"]
    # **分母から判定不能を外す。** 正誤を決められなかったものを誤に数えると、
    # 弱い推定と事実の誤りが同じ扱いになる（件数は別に書く）。
    den = len(ok) + len(ng)
    print(f"標本 {d['n']} 行／要素 {len(els)} 個／判定済み {len(judged)} 個／判定不能 {len(unk)} 個")
    if den:
        print(f"**適合率（要素）= {len(ok)}/{den} = {len(ok) / den:.1%}**")
    rows_ok = [r for r in d["rows"] if r["elements"] and
               all(e["判定"] == "正" for e in r["elements"] if e["判定"])]
    print(f"行の単位で全要素が正しい行 = {len(rows_ok)}/{d['n']} = {len(rows_ok) / d['n']:.1%}")
    syn = [r for r in d["rows"] if r["あらすじが本文に実在"]]
    print(f"あらすじが本文に実在した行 = {len(syn)}/{d['n']}")
    kinds: dict[str, int] = {}
    for e in ng:
        kinds[e["誤りの型"] or "不明"] = kinds.get(e["誤りの型"] or "不明", 0) + 1
    for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f"  誤りの型 {k}: {v} 個")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
