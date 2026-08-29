#!/usr/bin/env python3
"""公演の公式サイトのページから、あらすじの区間を切り出す（V6b の前半）。

網 C（内容の傾向）はあらすじの要素から作る。**要素を取り出す前に、
「あらすじがページのどこにあるか」を機械的に決められるかを確かめる必要がある。**
ページ全体の本文（中央値 2,640 字、最大は百万字超）をそのまま渡すと、
公演情報でもチケット案内でもない文まで要素として拾ってしまう。

    python3 tools/stages/extract_synopsis.py            # キャッシュ済みのページで測る
    python3 tools/stages/extract_synopsis.py --dump 5   # 切り出した中身を 5 件見る

**取得はしない。** すでに `data/credits/official_pages/` にあるものだけを読む。

**この道具で測れるのは下限である。** 見出しの語で切り出す方式なので、
**見出しを持たないページのあらすじは拾えない。** 実データで確認した例 ──
「被告人の佐瀬研一は、借金に追われ…」（リーガルパーク）、
「現代にあらわれた鬼と、渡辺綱、桃太郎に金太郎…」（一糸座）はどちらも
本文にあらすじがあるのに見出しが無い。**切り出しは規則では決まらないので、
本来は LLM の仕事である**（企画書 5 章の「境界の決まった変換」）。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "data" / "credits" / "official_pages"
UPCOMING = ROOT / "data" / "credits" / "upcoming.jsonl"
OFFICIAL = ROOT / "data" / "credits" / "official.jsonl"

# あらすじの始まりを示す語。**「概要」「公演情報」は入れない**
# ── 日程と料金の表が続くことが多く、内容の説明ではない。
MARKERS = ("あらすじ", "ストーリー", "STORY", "Story", "物語", "INTRODUCTION",
           "Introduction", "イントロダクション", "作品について", "作品紹介",
           "みどころ", "見どころ", "解説", "SYNOPSIS", "Synopsis")
# あらすじの終わりを示す語（次の節の見出し）。
STOPS = ("キャスト", "CAST", "出演", "スタッフ", "STAFF", "公演日程", "日程",
         "チケット", "TICKET", "料金", "座席", "アクセス", "会場", "お問い合わせ",
         "上演時間", "公演情報", "スケジュール", "グッズ", "関連")

_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_BR = re.compile(r"<(br|/p|/div|/li|/h[1-6]|/td|/tr)[^>]*>", re.I)
_ANY = re.compile(r"<[^>]+>")


def to_text(raw: str) -> str:
    t = _TAG.sub(" ", raw)
    t = _BR.sub("\n", t)
    t = _ANY.sub(" ", t)
    t = html.unescape(t)
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[ \t　]+", " ", t)
    return re.sub(r"\n{2,}", "\n", t).strip()


def slug(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", url) + ".html"


def cut_synopsis(text: str, limit: int = 1200) -> tuple[str, str]:
    """(切り出したあらすじ, 使った目印) を返す。見つからなければ ("", "")。"""
    for m in MARKERS:
        i = text.find(m)
        if i < 0:
            continue
        body = text[i + len(m):i + len(m) + limit]
        # 次の節の見出しで打ち切る
        ends = [body.find(s) for s in STOPS if 20 < body.find(s)]
        if ends:
            body = body[:min(ends)]
        body = re.sub(r"^[\s:：|/／\-—─】\]]+", "", body).strip()
        if len(body) >= 40:
            return body, m
    return "", ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", type=int, default=0, help="切り出した中身を N 件表示する")
    a = ap.parse_args()

    groups = {}
    for label, path, url_key in (("これから観られる公演", UPCOMING, "url"),
                                 ("観た公演", OFFICIAL, "url")):
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]
        groups[label] = [r for r in rows if r.get(url_key) and not r.get("error")]

    out = []
    for label, rows in groups.items():
        found, missing, lens, samples = 0, [], [], []
        cached = 0
        for r in rows:
            p = PAGES / slug(r["url"])
            if not p.exists():
                continue
            cached += 1
            text = to_text(p.read_text(encoding="utf-8", errors="replace"))
            body, marker = cut_synopsis(text)
            if body:
                found += 1
                lens.append(len(body))
                samples.append((r.get("troupe") or r.get("title") or "", marker, body))
            else:
                missing.append((r.get("troupe") or r.get("title") or "", r["url"]))
        print(f"■ {label}")
        print(f"    取得成功 {len(rows)} 件 / キャッシュがある {cached} 件")
        if cached:
            print(f"    あらすじの区間を切り出せた {found} 件（{found / cached * 100:.0f}%）")
        if lens:
            lens.sort()
            print(f"    切り出した長さ: 中央値 {statistics.median(lens):.0f} 字 / "
                  f"最小 {lens[0]} / 最大 {lens[-1]}")
            print(f"      100 字以上 {sum(1 for x in lens if x >= 100)}/{len(lens)}")
        if missing:
            print(f"    切り出せなかった {len(missing)} 件（先頭 6 件）:")
            for t, u in missing[:6]:
                print(f"      {t[:24]:<26} {u[:52]}")
        print()
        out.append((label, cached, found, samples))

    if a.dump:
        for label, _, _, samples in out:
            print(f"■ 切り出した中身（{label}・先頭 {a.dump} 件）")
            for t, marker, body in samples[:a.dump]:
                print(f"  ── {t[:30]}  目印「{marker}」")
                print(f"     {body[:200]}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
