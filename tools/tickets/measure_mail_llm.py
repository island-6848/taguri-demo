#!/usr/bin/env python3
"""購入確認メールの抽出を、規則と LLM で比べる（V74）。

規則の側は `extract_performances.parse`（2026-08-21 に直したもの）、LLM の側は
本文を渡して題名・上演日・劇場を答えさせる。**同じ 1 通に両方をかけて突き合わせる。**

## 当事者が直した内容を指示文に足す

画面（`/records` の「公演詳細を直す」）で直した題名・上演日・劇場は
`fixes` 表に残る。**それを実例として指示文に添える**（`tools/tickets/corrections.py`）。
理由は 2 つある。

1. **抽出の失敗は発行元の書式ごとに決まった形をしている。** 本文の折り返しで題名が
   切れる・雛形の項目名を拾う、といった形なので、**同じ発行元の実例が次の 1 通に
   いちばん効く。** 実例は同じ発行元のものを先に並べる。
2. **直したことが 1 回しか効かないなら、直す手間に見合わない。** 当事者が 24 件の
   題名を直しても、次の取り込みで同じ壊れ方をするなら作業が終わらない。

**渡すのは実例だけで、規則には言い換えない。**「こういう語は題名にしない」と書くと、
当事者が確定していない一般化を機械が言い出すことになる。

指示文が変われば測定の条件も変わるので、**実例の件数を出力の行に書き残す**
（`prompt_version` と `n_examples`）── 前の測定と混ぜて読めないようにするため。

**本文は個人情報を落としてから渡す。** 宛名・座席・金額・電話番号・会員番号・
メールアドレスは抽出に要らないので、送る前に伏せる。

    python3 tools/tickets/measure_mail_llm.py --limit 30      # 試し
    python3 tools/tickets/measure_mail_llm.py                 # 全件

出力は data/verification/mail_llm.jsonl（端末内のみ）。
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "tickets"))
sys.path.insert(0, str(ROOT / "tools"))
import corrections as CX  # noqa: E402
import extract_performances as E  # noqa: E402
import llm_gemini as LLM  # noqa: E402

SRC = ROOT / "data" / "tickets" / "performances.jsonl"
BODIES = ROOT / "data" / "tickets" / "bodies"
OUT = ROOT / "data" / "verification" / "mail_llm.jsonl"
MODEL = LLM.MODEL
PROMPT_VERSION = "m2"      # m1 → m2: 当事者が直した実例を指示文に足した

PROMPT = """あなたはチケットの購入確認メールから、観た公演の情報を取り出す部品である。
メールが複数与えられる。**1 通につき 1 つの JSON** を作り、JSON の配列だけを出力する。

各 JSON の形:
{"id": "<与えられた id>", "title": "<公演・演目の題名。取れなければ null>",
 "date": "<上演日 YYYY-MM-DD。取れなければ null>", "venue": "<劇場名。無ければ null>",
 "kind": "<演劇 | 音楽 | 映画 | その他>", "note": "<判断の根拠を 20 字以内>"}

規則:
- **題名は公演・演目の名前だけ。** 受取方法・支払い・発券の案内文（「マルチコピー機」
  「払込・引換票番号」など）や、サービス名・件名の定型句を題名にしない。
- **日付は上演日**（開演・開場の日）。予約日時・申込日・入金日・発券期限・発売日は取らない。
  年が書いていない場合は、メールの受信日から最も近い将来の日付として補う。
- **観劇と関係のないメール**（映画・コンサート・宿泊・交通・通販）は title を取ったうえで
  kind をそれに合わせる。無理に演劇にしない。
- 分からないものは null にする。**推測で埋めない。**
"""

MASK = [
    (re.compile(r"^[^\n]{1,20}様\s*$", re.M), "（宛名）様"),
    (re.compile(r"\d+列\s*\d+番"), "（座席）"),
    (re.compile(r"[\d,]+円"), "（金額）"),
    (re.compile(r"[\w.+-]+@[\w.-]+"), "（メールアドレス）"),
    (re.compile(r"(Tel|TEL|電話)[:：]?\s*[\d\-()]{8,}"), "（電話）"),
    (re.compile(r"\d{8,}"), "（番号）"),
]


def mask(t: str) -> str:
    for pat, rep in MASK:
        t = pat.sub(rep, t)
    return t


MAIL_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING"},
            "title": {"type": "STRING", "nullable": True},
            "date": {"type": "STRING", "nullable": True},
            "venue": {"type": "STRING", "nullable": True},
            "kind": {"type": "STRING"},
            "note": {"type": "STRING"},
        },
        "required": ["id", "kind", "note"],
    },
}


def ask(batch: list[dict], model: str, fixes: dict | None = None) -> list[dict]:
    body = "".join(f"### id: {r['uid']}\n件名: {r['subject']}\n受信日: {r['mail_date']}\n"
                   f"{r['text']}\n\n" for r in batch)
    # **実例は、この束でいちばん多い発行元のものを先に出す。** 束は発行元ごとに
    # 分けていないので、代表を 1 つ決めて優先の軸にする
    dom = collections.Counter(r["dom"] for r in batch).most_common(1)
    learned = CX.prompt_block(fixes, domain=dom[0][0] if dom else "")
    try:
        got, _meta = LLM.ask(PROMPT + learned + "以下がメールである。\n\n" + body,
                             schema=MAIL_SCHEMA, model=model, timeout=600)
    except (LLM.LLMError, LLM.SafetyBlocked) as e:
        print(f"  {e}", file=sys.stderr, flush=True)
        return []
    return got if isinstance(got, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--chars", type=int, default=1500)
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()

    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").split("\n") if l.strip()]
    todo = []
    for r in rows:
        p = BODIES / f"{r['uid']}.txt"
        if not p.exists() or E.is_pickup(r["subject"]):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        rule, which = E.parse(r["from"], text, r["subject"])
        todo.append({"uid": r["uid"], "dom": r["from"], "subject": r["subject"],
                     "mail_date": r["mail_date"][:31], "which": which, "rule": rule,
                     "text": mask(text)[:a.chars]})
    if a.limit:
        todo = todo[:a.limit]
    batches = [todo[i:i + a.batch] for i in range(0, len(todo), a.batch)]
    fixes = CX.read()
    n_ex = len(CX.examples(fixes, limit=999))
    print(f"LLM に渡すのは {len(todo)} 通（{len(batches)} 回・{a.jobs} 並列・model={a.model}）"
          f"。当事者が直した実例 {n_ex} 件を指示文に添える", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    with OUT.open("w", encoding="utf-8") as f:
        def run(batch):
            nonlocal done
            got = {str(g.get("id")): g for g in ask(batch, a.model, fixes)
                   if isinstance(g, dict)}
            for r in batch:
                g = got.get(r["uid"], {})
                f.write(json.dumps({k: r[k] for k in ("uid", "dom", "subject", "mail_date",
                                                      "which", "rule")}
                                   | {"llm": g, "model": a.model,
                                      "prompt_version": PROMPT_VERSION,
                                      "n_examples": n_ex},
                                   ensure_ascii=False) + "\n")
            f.flush()
            done += len(batch)
            print(f"  {done}/{len(todo)}", end="\r", flush=True)

        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            list(ex.map(run, batches))
    print(f"\n{OUT} に書き出しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
