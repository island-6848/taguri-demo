#!/usr/bin/env python3
"""候補の公演から、あらすじ（100 字以上）が取れるかを測る（V6）。

## 経路が変わっている

V6 は起票時「**カレンダーのリンクから辿って**」と書いてあるが、
[検証 017](../../docs/verification/017-recommendation-with-roster.md) で候補の取得先を
CoRich に変えた。CoRich の公演ページには**あらすじの欄が無い**
（100 字以上の説明があるのは 17%、`meta description` は定型文）ため、
**CoRich の「公式／劇場サイト」欄にある URL を辿って測る。**

## あらすじをどう見分けるか

**「長い文章が取れた」を「あらすじが取れた」と数えない。** 次の順で探す。

1. **見出しで探す** ── 「あらすじ」「STORY」「物語」「ストーリー」「概要」の直後
2. 見つからなければ、**最長の段落**（クレジット行・日程・料金・ナビを除いたもの）

**どちらで取れたかを分けて数える。** 見出し由来のほうが確度が高い。

    python3 tools/credits/fetch_synopsis.py --sample 100
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_official_credits import get, to_text          # noqa: E402

CAND = ROOT / "data" / "review" / "candidates.jsonl"
OUT = ROOT / "data" / "review" / "synopsis.jsonl"

HEAD = r"(?:あらすじ|ストーリー|STORY|Story|物語|概要|作品について|イントロダクション|INTRODUCTION)"
# あらすじではない行（日程・料金・クレジット・案内）
NOT_STORY = re.compile(r"(円|チケット|発売|予約|開場|開演|受付|全席|問い合わせ|"
                       r"当日券|割引|会員|주|Copyright|©|上演時間|休演|席\b)")
CREDIT_LINE = re.compile(r"^[^\s　]{1,10}[:：＝＿]|^[【［].{1,10}[】］]")


def pick(text: str) -> tuple[str, str]:
    """(あらすじ, どうやって取れたか) を返す。"""
    # 1. 見出しの直後
    m = re.search(HEAD + r"[\s　:：]*\n?", text)
    if m:
        tail = text[m.end():m.end() + 1500]
        buf = []
        for line in tail.split("\n"):
            s = line.strip()
            if not s:
                if buf:
                    break
                continue
            if NOT_STORY.search(s) or CREDIT_LINE.match(s):
                break
            buf.append(s)
            if sum(len(x) for x in buf) >= 400:
                break
        got = "".join(buf)
        if len(got) >= 100:
            return got, "見出し"
    # 2. 最長の段落
    best = ""
    for para in re.split(r"\n\s*\n", text):
        s = re.sub(r"\s+", "", para)
        if len(s) < 100 or NOT_STORY.search(s) or CREDIT_LINE.match(para.strip()):
            continue
        if len(s) > len(best):
            best = s
    return (best[:600], "最長の段落") if len(best) >= 100 else ("", "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=100)
    a = ap.parse_args()
    cands = [json.loads(l) for l in CAND.read_text(encoding="utf-8").split("\n") if l.strip()]
    step = max(1, len(cands) // a.sample)
    picked = cands[::step][:a.sample]          # **等間隔で抜く**
    print(f"候補 {len(cands)} 件から等間隔で {len(picked)} 件（{step} 件ごと）", flush=True)

    rows = []
    for n, c in enumerate(picked, 1):
        m = re.search(r'https?://[^\s"<>）)]+', c["fields"].get("公式／劇場サイト", ""))
        url = m.group(0).rstrip("。、") if m else ""
        syn, how, err = "", "", "URL 無し" if not url else ""
        if url:
            html, err = get(url)
            if html:
                syn, how = pick(unicodedata.normalize("NFKC", to_text(html)))
        rows.append({"stage_id": c["stage_id"], "title": c["title"][:60], "url": url,
                     "error": err, "how": how, "len": len(syn), "synopsis": syn[:400]})
        print(f"  {n}/{len(picked)}", end="\r", flush=True)

    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    n = len(rows)
    ok = [r for r in rows if r["len"] >= 100]
    head = [r for r in ok if r["how"] == "見出し"]
    dead = [r for r in rows if r["error"]]
    print(f"\n\n■ V6 ── 候補 {n} 件（等間隔）")
    print(f"   URL に到達できない            {len(dead):>4} 件（{len(dead)/n*100:>3.0f}%）")
    print(f"   **100 字以上のあらすじが取れた {len(ok):>4} 件（{len(ok)/n*100:>3.0f}%）** ← V6 の判定（閾値 7 割）")
    print(f"     うち見出しから取れた         {len(head):>4} 件（{len(head)/n*100:>3.0f}%）")
    print(f"     うち最長の段落から           {len(ok)-len(head):>4} 件")
    if ok:
        L = sorted(r["len"] for r in ok)
        print(f"   取れた文字数の中央値          {L[len(L)//2]} 字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
