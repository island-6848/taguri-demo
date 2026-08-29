#!/usr/bin/env python3
"""KartaView（旧 OpenStreetCam）の街路画像を座標周辺から取得する。

KartaView はコミュニティ投稿のドライブレコーダー画像を公開しており、
**API キーが不要**なため追加の契約なしに実行できる。Google ストリートビューが
API キーを要求するのに対し、こちらは即座に動かせるのが利点。

制約:
  - 撮影は原則として日中。**夜間の見え方は判定できない。**
  - 投稿ベースなので撮影年が古いことがある（調布市菊野台周辺は 2017 年）。
    道幅・街灯ポールの有無・駐輪場・見通しといった「変わりにくい要素」の
    判定には使えるが、店舗の看板や外観の現況には使えない。
  - 顔とナンバープレートは自動ぼかし処理済み。

使い方:
    python3 tools/geo/fetch_kartaview.py --lat 35.65455 --lng 139.56629 \
        --radius 120 --limit 12 --label jindaiyu --outdir data/streetview

標準ライブラリのみで動作する（この環境には pip が無いため）。
"""

import argparse
import json
import os
import urllib.parse
import urllib.request

API = "https://api.openstreetcam.org/2.0/photo/"
UA = "mayoi-research/1.0 (+task #000001)"
# 画像 URL はレコードが直接持っている。th=サムネイル / lth=中サイズ / proc=フルサイズ。
# 旧 storage.openstreetcam.org は DNS が引けないため、cdn.kartaview.org 経由の
# imageProcUrl 系を使う（fileurl* 系はレガシーホストでフォールバック用）。
URL_FIELDS = {
    "th": ("imageThUrl", "fileurlTh"),
    "lth": ("imageLthUrl", "fileurlLTh"),
    "proc": ("imageProcUrl", "fileurlProc"),
}


def fetch_metadata(lat, lng, radius, limit):
    query = urllib.parse.urlencode(
        {"lat": lat, "lng": lng, "radius": radius, "itemsPerPage": limit, "page": 1}
    )
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def photo_url(photo, size="proc"):
    for field in URL_FIELDS[size]:
        url = photo.get(field)
        if url and "{{sizeprefix}}" not in url:
            return url
    raise KeyError(f"画像 URL が見つからない: {photo.get('id')}")


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lng", type=float, required=True)
    ap.add_argument("--radius", type=int, default=100, help="メートル")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--label", required=True, help="出力ファイル名の接頭辞")
    ap.add_argument("--outdir", default="data/streetview")
    ap.add_argument("--size", default="proc", choices=["th", "lth", "proc"])
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    payload = fetch_metadata(args.lat, args.lng, args.radius, args.limit)
    photos = payload.get("result", {}).get("data", [])
    if not photos:
        print("画像なし（この座標周辺に KartaView のカバレッジがない）")
        return

    index = []
    for i, p in enumerate(photos):
        url = photo_url(p, args.size)
        dest = os.path.join(args.outdir, f"{args.label}-{i:02d}.jpg")
        try:
            size = download(url, dest)
        except Exception as exc:  # カバレッジの穴や欠損画像を飛ばす
            print(f"[skip] {url}: {exc}")
            continue
        meta = {
            "file": dest,
            "date": p.get("shotDate") or p.get("dateAdded"),
            "distance_m": p.get("distance"),
            "heading": p.get("heading"),
            "lat": p.get("lat"),
            "lng": p.get("lng"),
            "bytes": size,
        }
        index.append(meta)
        print(
            f"{dest}  撮影={meta['date']}  距離={meta['distance_m']}m  "
            f"方位={meta['heading']}  {size // 1024}KB"
        )

    with open(os.path.join(args.outdir, f"{args.label}-index.json"), "w") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
