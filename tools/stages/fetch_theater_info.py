#!/usr/bin/env python3
"""劇場そのものの情報（座席数・住所・公式サイト）を CoRich の劇場ページから集める。

## 何のために集めるのか

**会場ごとの当たり率は、すでに測って落としてある**（[検証 019](../../docs/verification/019-scoring-fixes.md)）
── 基準より低い会場は 0 件、高い 3 件はいずれも n=2 の偶然だった。さらに
[検証 002](../../docs/verification/002-first-seven-records.md) で、会場への不満は公演の
評価が ○ でも書かれていた（会場の評価と公演の評価は独立している）。**だから
「この劇場は当たる」は作らない。**

**ここで集めるのは、会場そのものではなく会場の属性である。**
[検証 001](../../docs/verification/001-theater-capacity.md) で「客席数は単一の値に
ならないので**規模の段階**（小・中・大）で持つ」と設計したが、**段階で測ってはいない。**
粒度を上げたまとめ方は、会場を 1 つずつ数えるのとは別の操作なので、ここは未検証である。

## 単位はホールである（建物ではない）

**規模を測るならホール単位にする。** 劇場3は小劇場 440 席・中劇場 1,038 席で、
建物にまとめると規模という属性が消える。地図の点は建物 1 つだが（同じ座標に重なる）、
**軸が違うので、まとめる単位も違う**（`tools/taguri/venues.py` と同じ理由）。

## 名前の一致を必ず検査する

CoRich の劇場検索は**近くの別の劇場を返す**ことがある ── 「本多劇場」で引くと
下北沢の「シアター711」（80 席）が先に返った。**そのまま採ると本多劇場が 80 席として
測定に入る。** 検索結果を 1 つずつ見て、**劇場ページの題名がどれだけ似ているか**で選ぶ。

    python3 tools/stages/fetch_theater_info.py            # 観た会場ぶんを集める
    python3 tools/stages/fetch_theater_info.py --report   # 集まり方を見る

出力は `data/stages/theaters.json`（端末内のみ）。
"""

from __future__ import annotations

import argparse
import difflib
import gzip
import html as HTML
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))

OUT = ROOT / "data" / "stages" / "theaters.json"
BASE = "https://stage.corich.jp"
UA = "Mozilla/5.0 (compatible; taguri-verify/1.0; personal use)"
WAIT = 1.2                     # 1 リクエスト/秒以下（既存の作法に合わせる）
MATCH_MIN = 0.55

_SEAT = re.compile(r"座席数[：:]\s*([\d,]+)\s*席")
_ADDR = re.compile(r"((?:北海道|東京都|大阪府|京都府|.{2,3}県)[^\s　]{4,40})")
_SITE = re.compile(r"(https?://[^\s\"'<>]{8,120})")

# 規模の段階。**閾値は検証 001 で決めたものをそのまま使う。**
# 可変幅は段階の中に収まることが多く（新国立小劇場の 358〜468 はどちらも「中」）、
# 単一値で持とうとすると可変の劇場で必ず破綻する
BANDS = ((150, "小"), (500, "中"))


def band(seats: int | None) -> str:
    if not seats:
        return "不明"
    for lim, name in BANDS:
        if seats < lim:
            return name
    return "大"


def _nm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return re.sub(r"[\s　・･/／\-−ー’'\"、,。.]", "", s)


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def page(stage_id: str) -> dict:
    """劇場ページ 1 枚から、座席数・住所・公式サイト・題名を取る。"""
    p = _get(f"{BASE}/theater/{stage_id}")
    ttl = re.search(r"<title>(.*?)</title>", p, re.S)
    name = (HTML.unescape(re.sub(r"<[^>]+>", "", ttl.group(1))).split("|")[0].strip()
            if ttl else "")
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", p, flags=re.S)
    text = HTML.unescape(re.sub(r"<[^>]+>", "\n", body))
    flat = re.sub(r"[ \t　]+", "", text)
    seat = _SEAT.search(flat)
    addr = _ADDR.search(flat)
    site = [u for u in _SITE.findall(text) if "corich" not in u and "google" not in u]
    return {"corich_id": stage_id, "corich_name": name,
            "seats": int(seat.group(1).replace(",", "")) if seat else None,
            "address": re.sub(r"\s+", "", addr.group(1)) if addr else "",
            "site": site[0] if site else ""}


def find(name: str, tries: int = 3) -> dict | None:
    """劇場名から劇場ページを引く。**題名が似ているものを選ぶ。**

    先に見つかったものを採ると、近所の別の劇場が入る（「本多劇場」→「シアター711」）。

    **検索結果の一覧には劇場名が載っていない**ので、候補ごとにページを 1 枚ずつ開いて
    題名を見るしかない。1 件あたり 3 枚までにしてある（1 枚 4 秒かかる）。
    """
    t = _get(f"{BASE}/theater/search?"
             + urllib.parse.urlencode({"search": 1, "freeword": name}))
    time.sleep(WAIT)
    ids = []
    for sid in re.findall(r'href="/theater/(\d+)"', t):
        if sid not in ids:
            ids.append(sid)
    best = None
    for sid in ids[:tries]:
        try:
            got = page(sid)
        except Exception:                                            # noqa: BLE001
            time.sleep(WAIT)
            continue
        time.sleep(WAIT)
        got["match"] = round(difflib.SequenceMatcher(
            None, _nm(name), _nm(got["corich_name"])).ratio(), 2)
        if best is None or got["match"] > best["match"]:
            best = got
        if got["match"] >= 0.95:
            break
    if best and best["match"] >= MATCH_MIN:
        return best
    if best:
        print(f'       （「{best["corich_name"]}」は別の劇場として捨てた'
              f'・似ている度 {best["match"]}）')
    return None


def halls() -> list[tuple[str, str, int]]:
    """観た会場を**ホールの単位**で、(鍵, 検索に使う名前, 回数) にして返す。

    **鍵と検索語を分ける。** 鍵は空白を落とした形（表記のゆれを寄せるため）だが、
    **空白を落とした名前では劇場検索が 0 件になる**（「劇場3小劇場」）── 検索には
    メールに書かれていた形をそのまま渡す。
    """
    import collections

    import venues as V                                               # noqa: E402
    sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP                                                # noqa: E402
    c: collections.Counter = collections.Counter()
    raw: dict[str, collections.Counter] = {}
    for w in APP._works():
        for s in w.get("shows") or []:
            if s.get("venue"):
                k = V.hall(s["venue"])
                c[k] += 1
                raw.setdefault(k, collections.Counter())[s["venue"].strip()] += 1
    return [(k, raw[k].most_common(1)[0][0], n) for k, n in c.most_common()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    have = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    rows = halls()
    if a.report:
        ok = [h for h, _, _ in rows if have.get(h, {}).get("seats")]
        print(f"観た会場 {len(rows)} ホールのうち、座席数があるのは {len(ok)} ホール")
        import collections
        bb: collections.Counter = collections.Counter()
        for h, _q, n in rows:
            g = have.get(h) or {}
            bb[band(g.get("seats"))] += n
            print(f"   {n:>3} 回  {h[:30]:<30} "
                  + (f'{g["seats"]:>5} 席  {band(g.get("seats"))}' if g.get("seats")
                     else "──"))
        print("\n■ 規模の段階ごとの回数:", dict(bb))
        return 0

    todo = [(h, q, n) for h, q, n in rows
            if a.refresh or not have.get(h, {}).get("seats")]
    if a.limit:
        todo = todo[:a.limit]
    if not todo:
        print("引くものはありません。")
        return 0
    print(f"劇場ページを {len(todo)} 件引きます（1 秒 1 件・CoRich）", flush=True)
    miss = []
    for i, (h, q, n) in enumerate(todo, 1):
        try:
            got = find(q)
        except Exception as e:                                        # noqa: BLE001
            print(f"  {i}/{len(todo)}  {h} ── 引けなかった（{type(e).__name__}）")
            got = None
        if got:
            have[h] = got | {"visits": n, "band": band(got["seats"]), "asked": q}
            print(f'  {i}/{len(todo)}  {h[:26]:<26} → 「{got["corich_name"][:22]}」'
                  f' {got["seats"] or "席数なし"} 席・{band(got["seats"])}')
        else:
            miss.append(h)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(have)} ホールぶんを {OUT} に書きました。")
    if miss:
        # **黙って落とさない。** 席数が取れないホールは段階が「不明」になる
        print(f"\n■ 劇場ページが見つからなかった {len(miss)} ホール"
              f"（規模は「不明」として扱い、集計の分母から外す）:")
        for h in miss:
            print(f"   {h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
