#!/usr/bin/env python3
"""行った劇場の座標を 1 度だけ引き、端末内に保存する（地図の材料）。

## 守りの上での位置づけ ── 何が外に出るのか

**劇場の名前が OpenStreetMap の geocoder（Nominatim）に出る。** これは観劇の履歴の
一部なので、企画書 5 章のデータの境界に数える必要がある（保存の境界と処理の境界を
分けて書く、という原則）。**出るものと出ないものを数え上げる。**

| | 外に出るか |
|---|---|
| 劇場の名前（31 件） | **出る。** 1 度だけ、この処理でだけ |
| 観た日・評価・感想・題名 | 出ない |
| 何回行ったか | 出ない（名前だけを引く。回数は端末内で数える） |

**画面からは 1 度も外を叩かない**（守り 5）── ポスターと同じで、取得は更新の段でだけ
行い、画面は保存した JSON を読むだけである。**1 度引いた劇場は二度と引かない**
（`--refresh` を付けたときだけ引き直す）。

## 探すのは機械、確定するのは人

geocoder は劇場名で当たらないことがある（略称・改称・建物の中の小屋）。**当たらな
かったものは黙って落とさず、名前を並べて出す** ── その 1 件だけ人が座標を書けば済む。
`data/review/venue_geo.json` を直に書いてよい形にしてある。

    python3 tools/geo/fetch_venue_coords.py            # 足りないものだけ引く
    python3 tools/geo/fetch_venue_coords.py --refresh  # 全部引き直す
    python3 tools/geo/fetch_venue_coords.py --report   # 何が埋まっているかを見る
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
import sys
import time
import gzip
import html as HTML
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import venues as V                                                  # noqa: E402

OUT = ROOT / "data" / "review" / "venue_geo.json"
SHAPE = ROOT / "data" / "review" / "japan_outline.json"
WARDS = ROOT / "data" / "review" / "tokyo_wards.json"

# 東京の拡大図の地。**23 区の境界を敷く。**
# 全国の輪郭（2km まで間引いたもの）を東京の枠に写しても、枠いっぱいが 1 色に塗られる
# だけで**地図にならない** ── 実際にそれを出してしまい、「都内の地図が表示されていない」
# という指摘を受けた（起案者）。区の境界なら枠を埋めつつ、どこなのかが分かる。
TOKYO_WARDS = ("千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区",
               "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区",
               "杉並区", "豊島区", "北区", "荒川区", "板橋区", "練馬区", "足立区",
               "葛飾区", "江戸川区", "武蔵野市", "三鷹市")
API = "https://nominatim.openstreetmap.org/search"
# **作法。** Nominatim は 1 秒 1 要求までで、名前のある User-Agent を求めている
UA = "taguri-personal/1.0 (theatre records, local use)"
WAIT = 1.2


def outline() -> int:
    """日本の輪郭を 1 度だけ取り、端末内に置く。**地図の地は自分で描かない。**

    輪郭が無いと、点は枠の中に浮いているだけで「どこに行ったか」が読めない。
    **手で多角形を書き起こすことはしない** ── それは根拠の無い形を地図として出す
    ことになる。OSM の行政境界を粗く間引いたもの（`polygon_threshold`）を使う。

    **地図のタイル画像は読まない。** 画面から外部を叩かないという守り（企画書 5 章の 5）
    を、地図 1 枚で破ることになる。輪郭は 1 つの JSON なので端末内に置ける。
    """
    if SHAPE.exists():
        return 0
    u = API + "?" + urllib.parse.urlencode(
        {"q": "日本", "format": "json", "limit": 1, "polygon_geojson": 1,
         "polygon_threshold": 0.02})
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=120) as r:
        got = json.load(r)
    g = got[0]["geojson"]
    rings = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    # **外周だけ持つ**（内側の穴は湖などで、この地図では意味を持たない）。
    # 点が 6 個未満の環は島にもならないので落とす
    keep = [[[round(x, 4), round(y, 4)] for x, y in ring[0]]
            for ring in rings if len(ring[0]) >= 6]
    SHAPE.parent.mkdir(parents=True, exist_ok=True)
    SHAPE.write_text(json.dumps({"source": "OpenStreetMap / Nominatim",
                                 "threshold": 0.02, "rings": keep},
                                ensure_ascii=False), encoding="utf-8")
    print(f"日本の輪郭（{len(keep)} 島・{sum(len(r) for r in keep)} 点）を"
          f" {SHAPE} に置きました。")
    time.sleep(WAIT)
    return len(keep)


def wards() -> int:
    """東京 23 区（＋隣接 2 市）の境界を 1 度だけ取り、端末内に置く。

    **外に出るのは行政区の名前だけである。** どの区に行ったかは渡さない ── 全部の区を
    等しく引くので、この問い合わせからは観劇の履歴が読めない。
    """
    if WARDS.exists():
        return 0
    out = {}
    print(f"東京の区市 {len(TOKYO_WARDS)} 件の境界を引きます（地の絵に使う）", flush=True)
    for i, w in enumerate(TOKYO_WARDS, 1):
        u = API + "?" + urllib.parse.urlencode(
            {"q": "東京都" + w, "format": "json", "limit": 1,
             "polygon_geojson": 1, "polygon_threshold": 0.0006})
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ja"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                got = json.load(r)
        except Exception as e:                                       # noqa: BLE001
            print(f"  {i}/{len(TOKYO_WARDS)}  {w} ── 引けなかった（{e}）")
            time.sleep(WAIT)
            continue
        time.sleep(WAIT)
        if not got or "geojson" not in got[0]:
            print(f"  {i}/{len(TOKYO_WARDS)}  {w} ── 境界が無い")
            continue
        g = got[0]["geojson"]
        rings = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out[w] = [[[round(x, 5), round(y, 5)] for x, y in ring[0]]
                  for ring in rings if len(ring[0]) >= 6]
        print(f"  {i}/{len(TOKYO_WARDS)}  {w} ({sum(len(r) for r in out[w])} 点)")
    WARDS.parent.mkdir(parents=True, exist_ok=True)
    WARDS.write_text(json.dumps({"source": "OpenStreetMap / Nominatim", "wards": out},
                                ensure_ascii=False), encoding="utf-8")
    print(f"{len(out)} 区市を {WARDS} に置きました。")
    return len(out)


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


# ---------------------------------------------------------------- 住所から引く
CORICH = "https://stage.corich.jp"
UA_C = "Mozilla/5.0 (compatible; taguri-verify/1.0; personal use)"
_ADDR = re.compile(r"((?:北海道|東京都|大阪府|京都府|.{2,3}県)[^\s　]{4,40})")


def _get(url: str, ua: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def corich_address(name: str) -> tuple[str, str, str]:
    """CoRich の劇場ページから住所を取る。**名前で引けない館の второй の道である。**

    geocoder が施設名で当たらないのは、その名前が OSM に無いからで、**住所は別の
    情報源が持っている。** CoRich には劇場のページがあり、住所が書かれている
    （実測で 7 館のうち 5 館で取れた）。**思い出しで座標を書く代わりに、出典のある
    住所を引いてから座標にする。**
    """
    t = _get(CORICH + "/theater/search?"
             + urllib.parse.urlencode({"search": 1, "freeword": name}), UA_C)
    ids = re.findall(r'href="/theater/(\d+)"', t)
    time.sleep(1.2)
    for sid in ids[:2]:
        page = _get(f"{CORICH}/theater/{sid}", UA_C)
        time.sleep(1.2)
        title = re.search(r"<title>(.*?)</title>", page, re.S)
        head = HTML.unescape(re.sub(r"<[^>]+>", " ", title.group(1))).split("|")[0].strip() \
            if title else ""
        txt = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
        txt = HTML.unescape(re.sub(r"<[^>]+>", "\n", txt))
        for m in _ADDR.finditer(txt):
            a = re.sub(r"\s+", "", m.group(1))
            if re.search(r"\d", a):
                return sid, head, a
    return "", "", ""


def chome(addr: str) -> list[str]:
    """住所を、geocoder が引ける形に直した候補を返す。

    **番地まで入った住所は Nominatim では 0 件になる**（「東京都千代田区丸の内3-1-1」）。
    **丁目までに切ると当たる**（「東京都千代田区丸の内3丁目」→ 35.6770,139.7635）。
    実測で 5 館すべてがこの形で引けた。

    **精度は丁目の中心（およそ 100〜300m）である。** 建物の位置ではないので、
    保存するときに出典と精度を書き残す ── 地図の縮尺（1px ≒ 50m）では数 px ずれる。
    """
    a = re.sub(r"\s+", "", addr)
    out = []
    for cand in (re.sub(r"(\d+)丁目.*$", r"\1丁目", a),
                 re.sub(r"(\d+)[-−‐–]\d+.*$", r"\1丁目", a),
                 a):
        cand = cand.replace("ケ谷", "ヶ谷")
        if cand and cand not in out:
            out.append(cand)
    return out


def looks_right(names: list[str], display: str) -> float:
    """引けた場所が、探していた劇場かどうかを 0〜1 で返す。

    **検索語ではなく、その館の呼び名すべてと比べる。** 別名で引いて当てることがあり
    （「豊島区立芸術文化劇場」で引くと「東京建物 Brillia HALL」が返る）、**検索語だけと
    比べると、正しい一致を「別の場所」として捨ててしまう。**

    **名前で引くと、まったく別の場所が返ることがある。** 実測では「帝国劇場」で
    栃木県佐野市の田畑（「駒場, 国道293号, 赤見町」）が返った ── **地図に置くと、
    行ったことのない県に点が立つ。**

    **完全一致は求められない。** 「浅草九劇」は OSM では旧字の「淺草九劇」で登録されて
    いて、含まれるかどうかで見ると正しい一致を捨てることになる。**似ている度合いで見る。**
    """
    def nm(s: str) -> str:
        return re.sub(r"[\s・･/／\-−ー]", "", unicodedata.normalize("NFKC", s or "")).lower()
    head = nm((display or "").split(",")[0])
    return max((difflib.SequenceMatcher(None, nm(w), head).ratio() for w in names),
               default=0.0)


MATCH_MIN = 0.5      # 「帝国劇場」対「駒場」は 0.33、「浅草九劇」対「淺草九劇」は 0.75


def ask(word: str, names: list[str]) -> dict | None:
    u = API + "?" + urllib.parse.urlencode(
        {"q": word, "format": "json", "limit": 1, "addressdetails": 1,
         "countrycodes": "jp"})
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=45) as r:
        got = json.load(r)
    if not got:
        return None
    g = got[0]
    ad = g.get("address") or {}
    # **都道府県は符号から引く。** `state` は東京都で空になり、`province` は県によって
    # 有無が違う。`ISO3166-2-lvl4`（JP-13 など）だけが必ず入っている
    m = re.fullmatch(r"JP-(\d{1,2})", str(ad.get("ISO3166-2-lvl4") or ""))
    return {"lat": round(float(g["lat"]), 6), "lon": round(float(g["lon"]), 6),
            "pref": V.PREF.get(int(m.group(1))) if m else "",
            "found": g.get("display_name", "")[:120], "query": word,
            "match": round(looks_right(names, g.get("display_name", "")), 2),
            "source": "nominatim"}


def by_address(name: str, label: str) -> dict | None:
    """名前で引けなかった館を、住所を経由して引く。"""
    try:
        sid, head, addr = corich_address(name)
    except Exception as e:                                           # noqa: BLE001
        print(f"       （CoRich を引けなかった: {type(e).__name__}）")
        return None
    if not addr:
        print(f"       （CoRich に「{label}」の住所が無い）")
        return None
    for w in chome(addr):
        try:
            got = ask(w, [w])
        except Exception:                                            # noqa: BLE001
            time.sleep(WAIT)
            continue
        time.sleep(WAIT)
        if got:
            return got | {"source": "corich-address", "address": addr,
                          "corich_id": sid, "corich_name": head,
                          "precision": "丁目の中心（およそ 100〜300m）",
                          "match": 1.0}
    print(f"       （住所「{addr}」からも引けなかった）")
    return None


def targets() -> list[tuple[str, int]]:
    import rate_performances as R
    con = R.connect()
    try:
        works = R.load_works(R.load_purchases(), R.read_splits(con), R.read_excluded(con))
    finally:
        con.close()
    return V.visits(works).most_common()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="保存済みのものも引き直す")
    ap.add_argument("--report", action="store_true", help="引かずに、埋まり方だけ見る")
    ap.add_argument("--addr", action="append", default=[], metavar="劇場名=住所",
                    help="住所を手で渡して引く。**座標ではなく住所で渡せる** ── "
                         "本人が知っているのは住所や最寄り駅で、緯度経度ではない")
    a = ap.parse_args()

    have = load()
    if not a.report:
        # **点と地は同じ 1 回でそろえる。** 片方だけでは地図にならない
        outline()
        wards()
    rows = targets()
    if a.report:
        ok = [k for k, _ in rows if have.get(k, {}).get("lat")]
        print(f"行った劇場 {len(rows)} 館のうち、座標があるのは {len(ok)} 館")
        for k, n in rows:
            g = have.get(k) or {}
            print(f"   {n:>3} 回  {V.label(k):<30} "
                  + (f'{g["lat"]:.4f},{g["lon"]:.4f}  {g.get("pref") or "（県が空）"}'
                     if g.get("lat") else "── 座標なし"))
        return 0

    for one in a.addr:
        name, _, addr = one.partition("=")
        k = V.key(name.strip())
        if not addr.strip():
            print(f"「{name}」に住所が付いていない（劇場名=住所 の形で渡す）")
            continue
        for w in chome(addr.strip()):
            got = ask(w, [w])
            time.sleep(WAIT)
            if got:
                have[k] = got | {"source": "hand-address", "address": addr.strip(),
                                 "precision": "丁目の中心（およそ 100〜300m）",
                                 "label": V.label(k), "match": 1.0}
                print(f"  {V.label(k)} → {got['pref']} {got['lat']:.4f},{got['lon']:.4f}")
                break
        else:
            print(f"  {V.label(k)} ── 住所「{addr.strip()}」から引けなかった")
    if a.addr:
        OUT.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")

    todo = [(k, n) for k, n in rows if a.refresh or not have.get(k, {}).get("lat")]
    if not todo:
        print(f"引くものはありません（{len(rows)} 館ぶんそろっています）。")
        return 0
    print(f"劇場の名前 {len(todo)} 件を OpenStreetMap に問い合わせます"
          f"（1 秒 1 件。名前だけを送り、観た日・評価は送りません）", flush=True)
    miss = []
    for i, (k, n) in enumerate(todo, 1):
        got = None
        names = [V.label(k)] + V.queries(k)
        for word in V.queries(k):
            try:
                cand = ask(word, names)
            except Exception as e:                                   # noqa: BLE001
                print(f"  {i}/{len(todo)}  {V.label(k)} ── 引けなかった"
                      f"（{type(e).__name__}: {e}）")
                cand = None
            time.sleep(WAIT)
            if cand and cand["match"] >= MATCH_MIN:
                got = cand
                break
            if cand:
                # **別の場所が返ったことを黙って捨てない。** 何が返ったのかを出す
                print(f"       （{word} → 「{cand['found'].split(',')[0]}」は"
                      f"別の場所として捨てた・似ている度 {cand['match']}）")
        if got is None:
            # **名前で当たらないことを、諦める理由にしない。** 住所は別の情報源が持つ
            got = by_address(V.queries(k)[0], V.label(k))
        if got:
            have[k] = got | {"visits": n, "label": V.label(k)}
            print(f"  {i}/{len(todo)}  {V.label(k)} → {got['pref'] or '県が空'} "
                  f"{got['lat']:.4f},{got['lon']:.4f}"
                  + (f"（住所から: {got['address']}）" if got.get("address") else ""))
        else:
            miss.append(k)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(have)} 館ぶんを {OUT} に書きました。")
    if miss:
        # **黙って落とさない。** 1 件ずつ人が書けば済む形で出す
        # **座標を書けとは言わない。** 本人が知っているのは住所や最寄り駅である
        print(f"\n■ 当たらなかった {len(miss)} 館 ── 住所が分かれば引けます:")
        for k in miss:
            print(f'   python3 tools/geo/fetch_venue_coords.py'
                  f' --addr "{V.label(k)}=（住所）"')
        print("   （住所は丁目までで足ります。番地まで入っていても切って引きます）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
