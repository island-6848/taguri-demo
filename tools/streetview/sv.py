#!/usr/bin/env python3
"""Street View Static API CLI.

Google マップの Web 版は JavaScript で地図を描画するため、テキスト取得しかできない
環境（Claude Code の WebFetch など）ではストリートビュー画像を見られない。
このスクリプトは Street View **Static** API を叩いて JPEG を直接ファイルに落とす。
JS もブラウザも要らないので、curl が通る環境ならそれだけで画像が手に入る。

依存: Python 標準ライブラリのみ（pip install 不要）。

使い方の要約:
    ./sv.py meta   "35.65,139.55"        # 撮影の有無・撮影年月・パノラマ ID を確認（無料）
    ./sv.py shot   "35.65,139.55" --heading 0,90,180,270
    ./sv.py around "35.65,139.55"        # 8 方位を一括取得
    ./sv.py look-at 35.65,139.55 35.66,139.56   # A から B を向く方位角を計算して撮影

API キーは次の順で探す:
    1. 環境変数 GOOGLE_MAPS_API_KEY
    2. ~/.config/streetview/api_key （1 行目をキーとして読む）
キーは標準出力・ログ・manifest には一切書き出さない。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

META_ENDPOINT = "https://maps.googleapis.com/maps/api/streetview/metadata"
IMAGE_ENDPOINT = "https://maps.googleapis.com/maps/api/streetview"

KEY_FILE = Path.home() / ".config" / "streetview" / "api_key"
DEFAULT_OUT = Path.cwd() / "sv-out"

# 8 方位。around サブコマンドの既定値。
COMPASS = [0, 45, 90, 135, 180, 225, 270, 315]


# --------------------------------------------------------------------------
# 基盤
# --------------------------------------------------------------------------


class SvError(Exception):
    """利用者に見せる想定のエラー。トレースバックなしで終了する。"""


def load_api_key() -> str:
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if key:
        return key
    if KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()
        if key:
            return key
    raise SvError(
        "API キーが見つかりません。次のどちらかで設定してください:\n"
        f"  echo 'YOUR_KEY' > {KEY_FILE}  (先に mkdir -p {KEY_FILE.parent})\n"
        "  export GOOGLE_MAPS_API_KEY=YOUR_KEY\n"
        "キーの取り方は同じディレクトリの README.md を参照。"
    )


def redact(text: str, key: str) -> str:
    """URL などに混ざったキーを隠す。エラーメッセージを出す前に必ず通す。"""
    return text.replace(key, "<API_KEY>") if key else text


def http_get(endpoint: str, params: dict, key: str) -> tuple[bytes, str]:
    """GET して (body, content_type) を返す。"""
    query = {k: v for k, v in params.items() if v is not None and v != ""}
    query["key"] = key
    url = f"{endpoint}?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "sv.py/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:600]
        raise SvError(
            f"HTTP {exc.code} {exc.reason}\n{redact(body, key)}\n" + hint_for_http(exc.code)
        ) from None
    except urllib.error.URLError as exc:
        raise SvError(f"ネットワークに到達できません: {exc.reason}") from None


def hint_for_http(code: int) -> str:
    if code == 403:
        return (
            "→ キーが Street View Static API に対して有効か、"
            "API 制限 / リファラ制限で弾かれていないか確認してください。"
        )
    if code == 400:
        return "→ パラメータの形式（location / heading / size など）を確認してください。"
    if code == 429:
        return "→ レート制限。少し待って再実行してください。"
    return ""


def parse_latlng(text: str) -> tuple[float, float]:
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", text)
    if not m:
        raise SvError(f"緯度経度として解釈できません: {text!r}（例: 35.681236,139.767125）")
    return float(m.group(1)), float(m.group(2))


def is_latlng(text: str) -> bool:
    try:
        parse_latlng(text)
        return True
    except SvError:
        return False


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    """a から b を見たときの方位角（真北 0、時計回り、0-360）。"""
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def slugify(text: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z.\-]+", "_", text).strip("_")
    return (slug or "loc")[:60]


def parse_headings(text: str) -> list[float]:
    if text.strip().lower() in {"all", "around"}:
        return [float(h) for h in COMPASS]
    out = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(float(part) % 360.0)
        except ValueError:
            raise SvError(f"heading として解釈できません: {part!r}") from None
    if not out:
        raise SvError("heading が空です。")
    return out


# --------------------------------------------------------------------------
# メタデータ（無料・課金対象外。撮影の有無と撮影年月をここで確認する）
# --------------------------------------------------------------------------


def fetch_meta(location: str, key: str, radius: int, source: str, pano: str | None) -> dict:
    params = {"radius": radius, "source": source}
    if pano:
        params["pano"] = pano
    else:
        params["location"] = location
    body, _ = http_get(META_ENDPOINT, params, key)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise SvError("メタデータの JSON を解釈できませんでした。") from None

    status = data.get("status")
    if status == "OK":
        return data
    if status == "ZERO_RESULTS":
        raise SvError(
            f"この地点には radius={radius}m 以内にストリートビューのパノラマがありません。\n"
            "→ --radius を広げる、または撮影されている道路上の座標を指定してください。"
        )
    msg = data.get("error_message", "")
    raise SvError(f"メタデータ取得に失敗: status={status}\n{redact(msg, key)}\n{hint_for_status(status)}")


def hint_for_status(status: str | None) -> str:
    if status == "REQUEST_DENIED":
        return (
            "→ Google Cloud のプロジェクトで 'Street View Static API' を有効化し、"
            "課金アカウントを紐づけ、キーの API 制限にこの API を含めてください。"
        )
    if status == "OVER_QUERY_LIMIT":
        return "→ 無料枠 / 上限を超えています。Cloud コンソールで割当を確認してください。"
    if status == "INVALID_REQUEST":
        return "→ location か pano のどちらかが必要です。値の形式を確認してください。"
    return ""


def describe_meta(data: dict) -> str:
    loc = data.get("location") or {}
    lines = [
        f"  pano_id   : {data.get('pano_id', '-')}",
        f"  撮影年月  : {data.get('date', '不明')}",
        f"  実際の位置: {loc.get('lat', '-')},{loc.get('lng', '-')}",
        f"  著作権    : {data.get('copyright', '-')}",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 画像取得
# --------------------------------------------------------------------------


def fetch_image(
    key: str,
    out_path: Path,
    *,
    pano: str | None = None,
    location: str | None = None,
    heading: float | None = None,
    pitch: float = 0.0,
    fov: float = 90.0,
    size: str = "640x640",
    radius: int = 50,
    source: str = "default",
) -> int:
    params = {
        "size": size,
        "pitch": pitch,
        "fov": fov,
        "radius": radius,
        "source": source,
        # 取得失敗を灰色画像で誤魔化さず HTTP エラーとして返させる
        "return_error_code": "true",
    }
    if heading is not None:
        params["heading"] = heading
    if pano:
        params["pano"] = pano
    else:
        params["location"] = location

    body, ctype = http_get(IMAGE_ENDPOINT, params, key)
    if "image" not in ctype:
        raise SvError(
            f"画像ではないレスポンスが返りました (Content-Type: {ctype})\n"
            + redact(body[:500].decode("utf-8", "replace"), key)
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(body)
    return len(body)


# --------------------------------------------------------------------------
# サブコマンド
# --------------------------------------------------------------------------


def cmd_meta(args) -> int:
    key = load_api_key()
    data = fetch_meta(args.location, key, args.radius, args.source, args.pano)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"ストリートビューあり: {args.location or args.pano}")
        print(describe_meta(data))
    return 0


def shoot_set(args, key: str, headings: list[float], label: str) -> int:
    """メタデータで存在確認 → pano_id 固定で複数方位を撮る。"""
    meta = fetch_meta(args.location, key, args.radius, args.source, args.pano)
    pano_id = meta.get("pano_id")
    loc = meta.get("location") or {}

    out_dir = Path(args.out).expanduser() / slugify(label)
    files = []
    print(f"pano_id={pano_id}  撮影年月={meta.get('date', '不明')}  "
          f"位置={loc.get('lat')},{loc.get('lng')}")
    for h in headings:
        name = f"h{int(round(h)):03d}_p{int(round(args.pitch)):+03d}_f{int(round(args.fov)):03d}.jpg"
        path = out_dir / name
        size = fetch_image(
            key,
            path,
            pano=pano_id,
            heading=h,
            pitch=args.pitch,
            fov=args.fov,
            size=args.size,
            radius=args.radius,
            source=args.source,
        )
        files.append({"heading": h, "pitch": args.pitch, "fov": args.fov, "path": str(path)})
        print(f"  保存: {path}  ({size:,} bytes)")

    manifest = {
        "query": args.location or args.pano,
        "pano_id": pano_id,
        "date": meta.get("date"),
        "location": loc,
        "copyright": meta.get("copyright"),
        "size": args.size,
        "images": files,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{len(files)} 枚を {out_dir} に保存しました（manifest.json 付き）。")
    return 0


def cmd_shot(args) -> int:
    key = load_api_key()
    headings = parse_headings(args.heading)
    return shoot_set(args, key, headings, args.label or (args.location or args.pano or "pano"))


def cmd_around(args) -> int:
    key = load_api_key()
    headings = [float(h) for h in COMPASS] if args.steps == 8 else [
        i * (360.0 / args.steps) for i in range(args.steps)
    ]
    label = args.label or f"around_{args.location or args.pano}"
    return shoot_set(args, key, headings, label)


def cmd_look_at(args) -> int:
    """撮影地点 from から対象 to を向く方位角を求め、その向きで撮る。

    「道路上のこの位置から、この建物を見たときどう見えるか」を再現するための機能。
    """
    a = parse_latlng(args.frm)
    b = parse_latlng(args.to)
    h = bearing(a, b)
    dist = haversine(a, b)
    print(f"{args.frm} から {args.to} を見る方位角: {h:.1f}°（距離 約 {dist:.0f} m）")
    # 方位角の計算だけならキーは不要なので、--dry-run はキー読み込みの前に返す
    if args.dry_run:
        return 0
    key = load_api_key()
    args.location = args.frm
    args.pano = None
    label = args.label or f"lookat_{args.frm}_to_{args.to}"
    return shoot_set(args, key, [h], label)


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371000.0
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat = lat2 - lat1
    dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def cmd_check(args) -> int:
    """キーと API 有効化の状態を確認する。画像は取らない（メタデータは無料）。"""
    try:
        key = load_api_key()
    except SvError as exc:
        print(f"NG: {exc}")
        return 1
    src = "環境変数 GOOGLE_MAPS_API_KEY" if os.environ.get("GOOGLE_MAPS_API_KEY") else str(KEY_FILE)
    print(f"キーの読み込み元: {src}（末尾 4 文字: ...{key[-4:]}）")
    # 東京駅。確実にストリートビューがある地点で疎通確認する。
    data = fetch_meta("35.681236,139.767125", key, 50, "default", None)
    print("OK: Street View Static API に到達し、メタデータを取得できました。")
    print(describe_meta(data))
    return 0


# --------------------------------------------------------------------------
# 引数
# --------------------------------------------------------------------------


def add_common_shot_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--pitch", type=float, default=0.0, help="上下角 -90..90（既定 0）")
    p.add_argument("--fov", type=float, default=90.0, help="視野角 10..120。小さいほど望遠（既定 90）")
    p.add_argument("--size", default="640x640", help="画素数。無料枠の上限は 640x640（既定）")
    p.add_argument("--radius", type=int, default=50, help="パノラマ探索半径 m（既定 50）")
    p.add_argument(
        "--source",
        choices=["default", "outdoor"],
        default="default",
        help="outdoor にすると屋内パノラマを除外する",
    )
    p.add_argument("--out", default=str(DEFAULT_OUT), help=f"出力先ディレクトリ（既定 {DEFAULT_OUT}）")
    p.add_argument("--label", help="出力サブディレクトリ名（既定は地点から自動生成）")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sv.py",
        description="Street View Static API から JPEG を直接取得する（ブラウザ不要）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="キーと API 有効化の疎通確認（無料）")
    c.set_defaults(func=cmd_check)

    m = sub.add_parser("meta", help="撮影の有無・撮影年月・pano_id を確認（無料）")
    m.add_argument("location", nargs="?", help="'緯度,経度' または住所")
    m.add_argument("--pano", help="location の代わりにパノラマ ID を指定")
    m.add_argument("--radius", type=int, default=50)
    m.add_argument("--source", choices=["default", "outdoor"], default="default")
    m.add_argument("--json", action="store_true", help="生の JSON を出力")
    m.set_defaults(func=cmd_meta)

    s = sub.add_parser("shot", help="指定方位の画像を取得")
    s.add_argument("location", nargs="?", help="'緯度,経度' または住所")
    s.add_argument("--pano", help="location の代わりにパノラマ ID を指定")
    s.add_argument(
        "--heading",
        default="0",
        help="方位角。カンマ区切り可（例 0,90,180,270）。'all' で 8 方位",
    )
    add_common_shot_args(s)
    s.set_defaults(func=cmd_shot)

    a = sub.add_parser("around", help="全方位を等間隔で一括取得")
    a.add_argument("location", nargs="?", help="'緯度,経度' または住所")
    a.add_argument("--pano", help="location の代わりにパノラマ ID を指定")
    a.add_argument("--steps", type=int, default=8, help="分割数（既定 8 = 45 度刻み）")
    add_common_shot_args(a)
    a.set_defaults(func=cmd_around)

    l = sub.add_parser("look-at", help="地点 A から地点 B を向いた画像を取得")
    l.add_argument("frm", metavar="FROM", help="撮影地点 '緯度,経度'")
    l.add_argument("to", metavar="TO", help="見たい対象 '緯度,経度'")
    l.add_argument("--dry-run", action="store_true", help="方位角の計算だけして終了")
    add_common_shot_args(l)
    l.set_defaults(func=cmd_look_at)

    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "cmd", None) in {"meta", "shot", "around"}:
        if not args.location and not args.pano:
            print("エラー: location か --pano のどちらかを指定してください。", file=sys.stderr)
            return 2
    try:
        return args.func(args)
    except SvError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
