#!/usr/bin/env python3
"""方法 B: ヘッドレス Chromium で Google マップのストリートビューを撮る。

API キーを使わずに済むが、Playwright と Chromium の導入に sudo が必要。
導入手順は README.md の「方法 B」を参照。

    python browser_shot.py 35.6512,139.5545 --heading 45 --out shot.png

方法 A（sv.py）と違い地図 UI や周辺の店名ラベルも一緒に写る。
一方で Google 側の UI 変更・同意ダイアログで壊れやすいので、
繰り返し使うなら sv.py を使うこと。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit(
        "playwright が入っていません。README.md の「方法 B」の手順で導入してください。\n"
        "  python3 -m venv ~/.venv/sv && ~/.venv/sv/bin/pip install playwright"
    )

# Google Maps URLs の公式スキーム。API キー不要でパノラマを直接開ける。
PANO_URL = (
    "https://www.google.com/maps/@?api=1&map_action=pano"
    "&viewpoint={lat},{lng}&heading={heading}&pitch={pitch}&fov={fov}"
)

# 同意ダイアログのボタン。国・言語で文言が変わるため複数当てる。
CONSENT_SELECTORS = [
    'button[aria-label*="同意"]',
    'button[aria-label*="Accept"]',
    'button:has-text("すべて受け入れる")',
    'button:has-text("Accept all")',
    'form[action*="consent"] button',
]


def parse_latlng(text: str) -> tuple[float, float]:
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", text)
    if not m:
        sys.exit(f"緯度経度として解釈できません: {text!r}（例: 35.681236,139.767125）")
    return float(m.group(1)), float(m.group(2))


def dismiss_consent(page) -> None:
    for sel in CONSENT_SELECTORS:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1500):
                btn.click(timeout=3000)
                page.wait_for_timeout(1500)
                return
        except Exception:
            continue


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="ヘッドレスブラウザでストリートビューを撮影")
    p.add_argument("location", help="'緯度,経度'")
    p.add_argument("--heading", type=float, default=0.0, help="方位角 0-360")
    p.add_argument("--pitch", type=float, default=0.0, help="上下角 -90..90")
    p.add_argument("--fov", type=float, default=90.0, help="視野角 10..120")
    p.add_argument("--out", default="streetview.png", help="出力 PNG パス")
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--wait", type=int, default=6000, help="描画待ち時間 ms（既定 6000）")
    p.add_argument("--lang", default="ja", help="表示言語（既定 ja）")
    args = p.parse_args(argv)

    lat, lng = parse_latlng(args.location)
    url = PANO_URL.format(
        lat=lat, lng=lng, heading=args.heading, pitch=args.pitch, fov=args.fov
    )
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-gl=swiftshader", "--no-sandbox"])
        ctx = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            locale=args.lang,
            device_scale_factor=2,
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except PWTimeout:
            browser.close()
            return exit_with("ページ読み込みがタイムアウトしました。")

        dismiss_consent(page)
        # WebGL のタイル読み込みは networkidle では終わらないので固定待ち
        page.wait_for_timeout(args.wait)
        page.screenshot(path=str(out))
        browser.close()

    print(f"保存: {out}")
    print("※ パノラマが存在しない座標では、地図画面のまま撮れることがあります。")
    print("　 撮影の有無は sv.py meta で先に確認するのが確実です。")
    return 0


def exit_with(msg: str) -> int:
    print(f"エラー: {msg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
