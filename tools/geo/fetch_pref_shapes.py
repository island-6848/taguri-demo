#!/usr/bin/env python3
"""都道府県の輪郭を 1 度だけ引き、端末内に置く（地図から選ぶための材料）。

    python3 tools/geo/fetch_pref_shapes.py            # 足りないものだけ引く
    python3 tools/geo/fetch_pref_shapes.py --refresh  # 全部引き直す
    python3 tools/geo/fetch_pref_shapes.py --report   # 何が埋まっているかを見る

## なぜ引くのか ── 手で書き起こさない

起案者の指示（2026-08-25）──「『観に行ける場所で絞り込む』のところ、地図上で選択
できるものも追加して」。**押せる地図には、県ごとの形が要る。**

すでにある `japan_outline.json` は**国の外周だけ**なので、県の境目を持っていない。
**手で多角形を書き起こすことはしない** ── それは根拠の無い形を地図として出すことに
なる（`fetch_venue_coords.py` と同じ判断）。OSM の行政境界を粗く間引いたものを使う。

## 守りの上での位置づけ ── 何が外に出るのか

**出るのは都道府県の名前 47 個だけである。** 観劇の履歴は 1 文字も通らない ──
劇場の座標を引くとき（`fetch_venue_coords.py`）は劇場名が出るので履歴の一部だったが、
こちらは**誰が使っても同じ 47 語**で、本人について何も述べていない。

**画面からは 1 度も外を叩かない**（企画書 5 章の守り 5）。取得はこの処理でだけ行い、
画面は保存した JSON を読むだけである。**地図のタイル画像も読まない。**

## 間引きの粗さ

`polygon_threshold` は 0.01 度（およそ 1km）である。国の外周（0.02）より細かいのは、
**県の境目は内陸を通るので、2km で間引くと隣どうしの境が合わなくなる**ためである。
出す地図は幅 460px なので、1km はおよそ 0.4px に当たる ── これ以上細かくしても
画面には出ない。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import render_recommend as RR                                       # noqa: E402

OUT = ROOT / "data" / "review" / "japan_prefs.json"
API = "https://nominatim.openstreetmap.org/search"
# **作法。** Nominatim は 1 秒 1 要求までで、名前のある User-Agent を求めている
UA = "taguri-personal/1.0 (theatre records, local use)"
WAIT = 1.2
THRESHOLD = 0.01
# **座標は小数 3 桁で置く。** およそ 100m で、幅 460px の地図では 0.04px に当たる ──
# それ以上の桁は画面に出ないまま、そのままファイルの大きさになる
ND = 3


def _load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}


def _fetch(name: str) -> list | None:
    """1 県ぶんの外周。**行政境界に当たったものだけ採る。**

    県名で引くと、同じ名前の駅や施設が先に返ることがある。`class` と `type` を見て
    **行政境界でなければ採らない** ── 違うものの形を県として出すと、押した先が
    地図と合わなくなる。
    """
    u = API + "?" + urllib.parse.urlencode(
        {"q": name, "format": "json", "limit": 3, "polygon_geojson": 1,
         "polygon_threshold": THRESHOLD, "countrycodes": "jp"})
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=120) as r:
        got = json.load(r)
    for g in got:
        if g.get("class") != "boundary" or g.get("type") != "administrative":
            continue
        geo = g.get("geojson") or {}
        if geo.get("type") == "MultiPolygon":
            rings = [poly[0] for poly in geo["coordinates"]]
        elif geo.get("type") == "Polygon":
            rings = [geo["coordinates"][0]]
        else:
            continue
        # **点が 6 個に満たない環は島にもならない**（`fetch_venue_coords.py` と同じ）
        out = [[[round(x, ND), round(y, ND)] for x, y in ring]
               for ring in rings if len(ring) >= 6]
        if out:
            return out
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    have = {} if a.refresh else _load().get("prefs") or {}
    if a.report:
        miss = [p for p in RR.PREFS if p not in have]
        n_pt = sum(len(r) for v in have.values() for r in v)
        print(f"{len(have)} / {len(RR.PREFS)} 県・環 {sum(len(v) for v in have.values())}"
              f"・点 {n_pt}・{OUT.stat().st_size // 1024 if OUT.exists() else 0}KB")
        if miss:
            print("取れていない:", "・".join(miss))
        return 0
    todo = [p for p in RR.PREFS if p not in have]
    if not todo:
        print(f"すでに 47 県そろっている（{OUT}）")
        return 0
    for i, p in enumerate(todo, 1):
        try:
            rings = _fetch(p)
        except Exception as e:                                      # noqa: BLE001
            print(f"  ! {p}: {e}")
            rings = None
        if rings:
            have[p] = rings
            print(f"  {i}/{len(todo)} {p} ── 環 {len(rings)}・点 "
                  f"{sum(len(r) for r in rings)}")
        else:
            # **黙って落とさない。** 取れなかった県は名前を出す ── 1 県だけなら
            # 人が座標を書けば済む（`fetch_venue_coords.py` と同じ構え）
            print(f"  {i}/{len(todo)} {p} ── 取れなかった")
        OUT.write_text(json.dumps({"source": "OpenStreetMap / Nominatim",
                                   "threshold": THRESHOLD, "prefs": have},
                                  ensure_ascii=False), encoding="utf-8")
        time.sleep(WAIT)
    miss = [p for p in RR.PREFS if p not in have]
    print(f"{len(have)} / {len(RR.PREFS)} 県・{OUT.stat().st_size // 1024}KB")
    if miss:
        print("取れていない:", "・".join(miss))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
