#!/usr/bin/env python3
"""Overpass API で店舗周辺の道路・設備の客観データを取得する。

街路画像が手に入らない場合でも、OSM のタグからは「変わりにくい事実」が取れる。
特にこのタスクで必要なのは次の 3 点。

  - 道路の等級と幅（`highway=residential` か `service` か、`width`）
  - **街灯の有無**（`lit=yes/no` タグ、`highway=street_lamp` ノード）
  - 駐輪場（`amenity=bicycle_parking`）の位置と規模

いずれも「駅を出て左折した薄暗い道」「直進した先の自転車置き場」という
ヒアリング内容を裏付ける／反証するために使う。

API キーは不要。標準ライブラリのみで動作する。

使い方:
    python3 tools/geo/fetch_osm_context.py --lat 35.6540 --lng 139.5664 --radius 250
"""

import argparse
import json
import urllib.parse
import urllib.request

# 本家は混雑時に 504 を返すため、ミラーへ順に fallback する
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]
UA = "mayoi-research/1.0 (+task #000001)"

QUERY = """
[out:json][timeout:60];
(
  way(around:{r},{lat},{lng})[highway];
  node(around:{r},{lat},{lng})[highway=street_lamp];
  node(around:{r},{lat},{lng})[amenity];
  way(around:{r},{lat},{lng})[amenity];
  node(around:{r},{lat},{lng})[shop];
  node(around:{r},{lat},{lng})[leisure];
);
out tags center;
"""


def run(lat, lng, radius):
    body = QUERY.format(r=radius, lat=lat, lng=lng)
    data = urllib.parse.urlencode({"data": body}).encode()
    last = None
    for endpoint in ENDPOINTS:
        req = urllib.request.Request(endpoint, data=data, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except Exception as exc:  # 504 / 429 / タイムアウトは次のミラーへ
            print(f"[retry] {endpoint}: {exc}")
            last = exc
    raise RuntimeError(f"全ミラーで失敗: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lng", type=float, required=True)
    ap.add_argument("--radius", type=int, default=250, help="メートル")
    ap.add_argument("--out", help="生 JSON の保存先（任意）")
    args = ap.parse_args()

    payload = run(args.lat, args.lng, args.radius)
    elements = payload.get("elements", [])
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    lamps = [e for e in elements if e.get("tags", {}).get("highway") == "street_lamp"]
    roads, amenities = [], []
    for e in elements:
        tags = e.get("tags", {})
        if "highway" in tags and tags["highway"] != "street_lamp":
            roads.append(e)
        if "amenity" in tags or "shop" in tags or "leisure" in tags:
            amenities.append(e)

    print(f"# 半径 {args.radius}m / 要素 {len(elements)} 件\n")

    print(f"## 街灯ノード: {len(lamps)} 件")
    print("（0 件は「街灯が無い」証明ではなくマッピングされていないだけの場合もある）\n")

    print("## 道路")
    seen = set()
    for e in sorted(roads, key=lambda x: x.get("tags", {}).get("highway", "")):
        t = e["tags"]
        key = (t.get("name", ""), t.get("highway"), t.get("width", ""), t.get("lit", ""))
        if key in seen:
            continue
        seen.add(key)
        bits = [f"highway={t['highway']}"]
        for k in ("name", "width", "lit", "lanes", "sidewalk", "surface", "oneway"):
            if k in t:
                bits.append(f"{k}={t[k]}")
        print("  - " + "  ".join(bits))

    print("\n## 施設・店舗")
    for e in sorted(amenities, key=lambda x: str(x.get("tags", {}).get("name", ""))):
        t = e["tags"]
        kind = t.get("amenity") or t.get("shop") or t.get("leisure")
        name = t.get("name", "(無名)")
        extra = []
        for k in ("capacity", "covered", "opening_hours", "cuisine", "bicycle_parking"):
            if k in t:
                extra.append(f"{k}={t[k]}")
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        print(
            f"  - {kind}: {name}"
            + (f"  [{', '.join(extra)}]" if extra else "")
            + f"  @{c.get('lat')},{c.get('lon')}"
        )


if __name__ == "__main__":
    main()
