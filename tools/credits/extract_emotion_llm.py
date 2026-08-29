#!/usr/bin/env python3
"""あらすじから「感情の軸」を判定させる（検証 040 追記 4・版 e1）。

## なぜ聞き直すのか

網 C の項目は**日本劇作家協会の戯曲デジタルアーカイブの 34 ジャンル**から借りている。そのうち
感情の軸（悲劇・喜劇・人情劇・ホラー・泣ける・ナンセンス・お茶の間）は、既存の抽出
（題材・トーン・舞台設定・原作）では **7 項目のうち 3 項目が 0 件**だった。
**聞いていないものは出てこない。** そこで感情だけを聞き直す。

## 根拠の一文を必ず引かせる

感情のラベルそれ自体は判断で、本文に「泣ける」とは書いていない。**そこでラベルと同時に、
判断の元になったあらすじの一文を引かせる。** 引用が本文に実在するかは機械で検査できる
（[検証 034](../../docs/verification/034-net-c-discrimination.md) の実在検査）。
**ラベルは判断だが、引用は事実である。** 推薦の理由は
「あらすじに『◯◯』と書いてある → だからこう判定した」の形で書ける。

## 学習側だけを聞く

①（差が立つか）と②（判別力）は学習側だけで測れる。候補側が要るのは③（件数）だけで、
そちらは `themes.jsonl` の引き直しが止まっているので測れない（起案者の判断で再開しない）。

    python3 tools/credits/extract_emotion_llm.py --limit 31
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import llm_gemini as LLM                                    # noqa: E402

THEMES = ROOT / "data" / "credits" / "themes.jsonl"
OUT = ROOT / "data" / "credits" / "emotions.jsonl"
MODEL = LLM.MODEL
VERSION = "e1"

GENRES = ["悲劇", "喜劇", "人情劇", "ホラー", "泣ける", "ナンセンス", "お茶の間"]

PROMPT = """あなたは演劇の公演情報を分類する部品です。以下の「あらすじ」を読み、
**観客がどう感じる作品か**を判定してください。

判定に使える項目は次の 7 つだけです（日本劇作家協会・戯曲デジタルアーカイブのジャンル名）。

- 悲劇 ── 主要な人物が不幸な結末を迎える。取り返しのつかない喪失が起きる
- 喜劇 ── 笑わせることを狙っている。滑稽な行き違いや軽妙なやりとりが中心
- 人情劇 ── 人と人の情愛や善意があたたかく描かれ、救いのある結末に向かう
- ホラー ── 観客を怖がらせることを狙っている。恐怖・怪異・不気味さが中心
- 泣ける ── 涙を誘うことを狙っている。別れ・献身・和解などで感情を揺らす
- ナンセンス ── 筋の通らないこと・不条理をそのまま見せる。意味の解決を放棄している
- お茶の間 ── 家族そろって安心して観られる。毒がなく、日常のほのぼのした話

**規則**

1. あてはまる項目だけを挙げる。あてはまらなければ空の配列にする。**無理に埋めない。**
2. 項目 1 つにつき、**判断の元になった一文を、渡されたあらすじから一字一句そのまま引き写す。**
   要約・言い換え・自分の知識で補うことは禁止する。引用できないなら、その項目は挙げない。
3. 引用は 20 字以上 80 字以内にする。
4. 1 作品につき項目は最大 3 つまで。

**出力は次の形の JSON 配列だけを返す。前後に説明を書かない。**

[{"id": "<渡された id>", "labels": [{"genre": "<7 項目のどれか>", "quote": "<あらすじからの引用>"}]}]

---

"""


def only(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z぀-ヿ一-鿿]", "",
                  unicodedata.normalize("NFKC", s or ""))


def grounded(quote: str, src: str) -> bool:
    """引用が本文に実在するか。**短い引用は完全一致、長い引用は 12 字の窓 5 つで 3 つ以上。**"""
    a, b = only(quote), only(src)
    if not a or not b:
        return False
    if len(a) < 24:
        return a in b
    win, hit = 12, 0
    for i in range(5):
        s = int(i * (len(a) - win) / 4)
        if a[s:s + win] in b:
            hit += 1
    return hit >= 3


def load_rated() -> list[dict]:
    """**版を 1 つに絞って読む。** 引き直しの途中の版が混ざると再現しない。"""
    out: dict[str, dict] = {}
    for l in THEMES.read_text(encoding="utf-8").split("\n"):
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("side") != "rated" or r.get("prompt_version") != "c2":
            continue
        if r.get("synopsis"):
            out[str(r["id"])] = r
    return list(out.values())


EMOTION_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING"},
            "labels": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"genre": {"type": "STRING"}, "quote": {"type": "STRING"}},
                    "required": ["genre", "quote"],
                },
            },
        },
        "required": ["id", "labels"],
    },
}


def ask(batch: list[dict]) -> list[dict]:
    body = "".join(f"### id: {r['id']}\nあらすじ: {r['synopsis']}\n\n" for r in batch)
    try:
        got, _meta = LLM.ask(PROMPT + body, schema=EMOTION_SCHEMA, model=MODEL, timeout=900)
    except (LLM.LLMError, LLM.SafetyBlocked) as e:
        print(f"  {e}", file=sys.stderr, flush=True)
        return []
    return got if isinstance(got, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    rows = load_rated()
    if a.limit:
        rows = rows[:a.limit]
    batches = [rows[i:i + a.batch] for i in range(0, len(rows), a.batch)]
    print(f"学習側 {len(rows)} 作品を {len(batches)} 回に分けて聞く（model={MODEL}・版 {VERSION}）",
          file=sys.stderr)
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(ask, batches))

    by_id = {str(r["id"]): r for r in rows}
    kept, dropped, lines = 0, 0, []
    for got in results:
        for g in got:
            src = by_id.get(str(g.get("id")))
            if not src:
                continue
            labels, bad = [], []
            for lb in (g.get("labels") or []):
                gen, q = lb.get("genre"), lb.get("quote", "")
                if gen not in GENRES:
                    bad.append({"genre": gen, "quote": q, "why": "項目外"})
                    continue
                if not grounded(q, src["synopsis"]):
                    bad.append({"genre": gen, "quote": q, "why": "引用が本文に無い"})
                    continue
                labels.append({"genre": gen, "quote": q})
            kept += len(labels); dropped += len(bad)
            lines.append(json.dumps({"side": "rated", "id": src["id"], "title": src.get("title", ""),
                                     "labels": labels[:3], "dropped": bad,
                                     "model": MODEL, "prompt_version": VERSION,
                                     "at": "2026-08-21"}, ensure_ascii=False))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"書いた {len(lines)} 行／採ったラベル {kept}／落としたラベル {dropped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
