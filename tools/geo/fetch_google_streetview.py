#!/usr/bin/env python3
"""Google ストリートビュー Static API で指定座標のパノラマ画像を取得する。

**API キーが必須。** キー無しのリクエストは `REQUEST_DENIED` で拒否される
（実測済み）。キーの取得手順は tools/README.md を参照。

このスクリプトは 1 地点について複数の方位（heading）を撮り分ける。
「駅を出て左折」「駐輪場の手前を右折」のような経路上の判断地点では、
進行方向だけでなく左右も撮らないと看板の見え方が評価できないため。

重要な制約:
  **ストリートビューの撮影は原則として日中である。** したがって
  「夜に看板がどう見えるか」「ギャラリーの窓が暗いかどうか」は
  この API では判定できない。判定できるのは道幅・見通し・街灯ポールの有無・
  建物の外観・看板の設置位置といった昼間に確認できる要素に限られる。
  夜間の見え方は現地で撮影した写真でしか確認できない。

使い方:
    export GOOGLE_MAPS_API_KEY=...
    python3 tools/geo/fetch_google_streetview.py \
        --lat 35.654551 --lng 139.5662897 --label jindaiyu \
        --headings 0,90,180,270 --outdir data/streetview

標準ライブラリのみで動作する。
"""

import argparse
import json
import os
import urllib.parse
import urllib.request

META = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMAGE = "https://maps.googleapis.com/maps/api/streetview"
UA = "mayoi-research/1.0 (+task #000001)"


def get(url, params):
    req = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lng", type=float, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--headings", default="0,90,180,270", help="カンマ区切りの方位角")
    ap.add_argument("--fov", type=int, default=90, help="画角。小さいほど望遠")
    ap.add_argument("--pitch", type=int, default=0)
    ap.add_argument("--size", default="640x640")
    ap.add_argument("--outdir", default="data/streetview")
    ap.add_argument("--radius", type=int, default=50, help="パノラマ探索半径(m)")
    args = ap.parse_args()

    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise SystemExit(
            "GOOGLE_MAPS_API_KEY が未設定。取得手順は tools/README.md を参照。\n"
            "キー無しでは Google が REQUEST_DENIED を返すため取得できない。"
        )

    os.makedirs(args.outdir, exist_ok=True)
    loc = f"{args.lat},{args.lng}"

    # まずメタデータで、その座標にパノラマが存在するか・撮影年月を確認する。
    # 画像リクエストは存在しなくても課金対象になるため先に確認する。
    meta = json.loads(
        get(META, {"location": loc, "radius": args.radius, "key": key}).decode()
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if meta.get("status") != "OK":
        raise SystemExit(f"パノラマなし: status={meta.get('status')}")
    print(f"\n撮影年月: {meta.get('date')}  pano_id={meta.get('pano_id')}")
    print("※ 撮影は日中。夜間の見え方はこの画像では判定できない。\n")

    for heading in [h.strip() for h in args.headings.split(",") if h.strip()]:
        params = {
            "location": loc,
            "size": args.size,
            "heading": heading,
            "fov": args.fov,
            "pitch": args.pitch,
            "radius": args.radius,
            "return_error_code": "true",
            "key": key,
        }
        dest = os.path.join(args.outdir, f"{args.label}-h{heading}.jpg")
        try:
            data = get(IMAGE, params)
        except Exception as exc:
            print(f"[skip] heading={heading}: {exc}")
            continue
        with open(dest, "wb") as fh:
            fh.write(data)
        print(f"{dest}  heading={heading}  {len(data) // 1024}KB")


if __name__ == "__main__":
    main()
