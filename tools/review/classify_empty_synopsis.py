#!/usr/bin/env python3
"""あらすじが取れなかった候補は、**なぜ取れなかったのか**を本文に照らして分類する（V72 の段 1）。

## なぜ要るのか

`themes.jsonl` は「取れなかった」としか書かない。**取れなかった理由は 1 つではない。**

- ページに物語が**書かれていない**（日程・料金・出演者だけ） ── 直しようがない
- **そもそも筋書きを持たない催し**（フェス・オムニバス・落語会・ダンス・レビュー） ── 物語が無いのが当然
- 物語ではないが、**内容の分かる説明はある**（題材・企画意図・宣伝文） ── **要素だけなら作れる**
- **本文に物語があるのに空を返した**（取りこぼし） ── 抽出の側の問題

**この 4 つを分けないと、直す先が決まらない。** 取りこぼしが多ければ抽出を直す話になり、
書かれていないものが多ければ**取りに行く先**（公式サイトの URL の質）の話になる。

## 誰が分類するか

**渡した本文に何が書いてあるかの判定なので、抽出と同じ担い手（LLM）に投げる。**
規則で「物語かどうか」を見分けられないことは [検証 020](../../docs/verification/020-synopsis-extraction-quality.md)
で実証済みで、そこが抽出を LLM に替えた理由そのものである。**出た分類は目視で抜き取り確認する。**

**新しい取得は 1 回も発生しない**（キャッシュにあるページだけを読む）。
`themes.jsonl` には書かない ── 確定した抽出を測定で触らないためである。

    python3 tools/review/classify_empty_synopsis.py --n 40
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
sys.path.insert(0, str(ROOT / "tools"))
import extract_theme_llm as E                                    # noqa: E402
import llm_gemini as LLM                                         # noqa: E402

THEMES = ROOT / "data" / "credits" / "themes.jsonl"
OUT = ROOT / "docs" / "verification" / "data-048-empty-causes.json"

CLASSES = {
    "A": "本文に物語がある（取りこぼし）",
    "B": "物語がどこにも無い",
    "C": "別公演の物語しか無い",
    "D": "筋書きを持たない催し",
    "E": "物語ではないが内容の説明はある",
}

PROMPT = """あなたは、演劇の公演ページの本文を読んで「その公演の物語の説明が本文にあるか」を分類する部品である。
入力は複数の公演で、それぞれ「### id: <id>」「題名: <題名>」の行に続けて本文が並ぶ。

各公演を次のいずれかに分類する。

- "A" ── **題名の公演の物語・内容の説明が本文にある**（60 字以上抜き出せる）。
- "B" ── 物語の説明はどこにも無い。日程・料金・出演者・劇場や団体の案内・SNS の投稿しか無い。
- "C" ── 物語の説明はあるが、**別の公演のもの**しかない（過去公演・他団体・劇場の他の演目）。
- "D" ── **そもそも筋書きを持たない催し**である（フェスティバル・複数団体のオムニバス・落語会・
         ダンス／レビュー／音楽の公演・ワークショップなど）。物語が無いのが当然のもの。
- "E" ── 物語ではないが、**作品の内容が分かる説明**はある（題材・世界観・企画意図の紹介、宣伝文）。

判断に迷うときは、A と E の境目では E、B と D の境目では D を選ぶ。

出力は JSON 配列だけを返す。前後に説明や```を書かない。
[{"id":"<id>","cls":"A","why":"20字程度の理由","quote":"A か E のときだけ、本文から該当箇所を40字"}]

入力:

"""


def empty_rows() -> list[dict]:
    """**同じ id の最後の行を採る。** 引き直した行が前の行を上書きするため（`net_c.load_themes` と同じ）。"""
    last: dict[tuple[str, str], dict] = {}
    for l in THEMES.read_text(encoding="utf-8").split("\n"):
        if l.strip():
            r = json.loads(l)
            last[(r["side"], str(r["id"]))] = r
    return [r for r in last.values()
            if r["side"] == "candidate" and not r["synopsis"] and not r.get("reason")]


CLASSIFY_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING"},
            "cls": {"type": "STRING"},
            "why": {"type": "STRING"},
            "quote": {"type": "STRING"},
        },
        "required": ["id", "cls", "why"],
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--batch", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()

    rows = empty_rows()
    bodies = {t["id"]: t for t in E.targets("candidate", fetch=False) if t["text"]}
    pool = [r for r in rows if r["id"] in bodies]
    print(f"あらすじが空の候補 {len(rows)} 件／うち本文を再現できる {len(pool)} 件")
    rnd = random.Random(a.seed)
    sel = rnd.sample(pool, min(a.n, len(pool)))

    def ask(batch: list[dict]) -> list[dict]:
        body = "".join(f"### id: {r['id']}\n題名: {r['title']}\n{bodies[r['id']]['text'][:4000]}\n\n"
                       for r in batch)
        try:
            got, _meta = LLM.ask(PROMPT + body, schema=CLASSIFY_SCHEMA, model=E.MODEL, timeout=900)
        except (LLM.LLMError, LLM.SafetyBlocked) as e:
            print(f"  {e}", file=sys.stderr, flush=True)
            return []
        return got if isinstance(got, list) else []

    batches = [sel[i:i + a.batch] for i in range(0, len(sel), a.batch)]
    got: list[dict] = []
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for part in ex.map(ask, batches):
            got.extend(part)

    meta = {r["id"]: r for r in sel}
    out = [{**g, "title": meta.get(str(g.get("id")), {}).get("title", ""),
            "url": meta.get(str(g.get("id")), {}).get("url", ""),
            "本文の長さ": len(bodies.get(str(g.get("id")), {}).get("text", ""))}
           for g in got if isinstance(g, dict)]
    OUT.write_text(json.dumps({"seed": a.seed, "n": len(sel), "母数": len(pool),
                               "分類": CLASSES, "rows": out}, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    c = collections.Counter(g["cls"] for g in out)
    print(f"\n■ 分類 {len(out)} 件")
    for k, name in CLASSES.items():
        if c.get(k):
            print(f"  {k} {name:<28} {c[k]:>3} 件（{c[k] / len(out) * 100:.0f}%）")
    print(f"\n1 件ずつを {OUT.relative_to(ROOT)} に残した")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
