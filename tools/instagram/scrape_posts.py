#!/usr/bin/env python3
"""ヘッドレス Chromium で Instagram の投稿を取得する（匿名で動作）。

## なぜブラウザが必要か

HTTP レベルの匿名アクセスはすべて封じられている（`fetch_posts.py` 冒頭の
実測表を参照）。プロフィール HTML は JavaScript のシェルしか返さないため、
**JS を実行しないと投稿データが存在しない**。実際にヘッドレス Chromium で
開くと匿名のままプロフィールと投稿一覧が描画される。

## 取得できるもの / できないもの

- 匿名では**プロフィール画面に出る投稿（概ね最新 12 件）まで**。それ以上を
  スクロールで読み込もうとするとログイン要求が出る。全件が必要なら
  `--sessionid` でログイン状態を渡す
- 各投稿ページから画像 URL・alt テキスト・キャプション本文・投稿日時を取得する。
  Instagram の alt テキストは画像の内容を機械的に説明しており
  （例「ハープ、クラリネット、ポスター、夜、テキストの画像のようです」）、
  画像そのものと併せて読むと投稿の性質を判別しやすい
- カルーセル投稿は左右送りをたどって全枚数を取得する

## 使い方

    source tools/lib/env.sh   # LD_LIBRARY_PATH の設定（必須）
    python3 tools/instagram/scrape_posts.py --user yorucafe_mayoi \\
        --outdir data/instagram

    # ログイン状態で全件取得する場合
    export IG_SESSIONID='...'
    python3 tools/instagram/scrape_posts.py --user yorucafe_mayoi --sessionid --scrolls 20
"""

import argparse
import json
import os
import re
import urllib.request

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)


def best_from_srcset(srcset, fallback):
    """srcset から最大幅の URL を選ぶ。メニュー画像は文字が小さいため重要。"""
    if not srcset:
        return fallback
    best, best_w = fallback, 0
    for part in srcset.split(","):
        bits = part.strip().rsplit(" ", 1)
        if len(bits) != 2:
            continue
        url, w = bits[0], bits[1].rstrip("w")
        try:
            w = int(w)
        except ValueError:
            continue
        if w > best_w:
            best, best_w = url, w
    return best


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)


def collect_shortcodes(page, scrolls):
    codes, stalled = [], 0
    for _ in range(scrolls + 1):
        found = page.eval_on_selector_all(
            'a[href*="/p/"]', "els => els.map(e => e.getAttribute('href'))"
        )
        new = [
            m.group(1)
            for href in found
            if (m := re.search(r"/p/([A-Za-z0-9_-]+)", href or ""))
            and m.group(1) not in codes
        ]
        codes.extend(new)
        if not new:
            stalled += 1
            # 2 回続けて増えなければ、匿名の上限かログイン要求に達したと判断する
            if stalled >= 2:
                break
        else:
            stalled = 0
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(2500)
    return codes


def scrape_post(page, code):
    page.goto(
        f"https://www.instagram.com/p/{code}/",
        wait_until="domcontentloaded",
        timeout=90000,
    )
    page.wait_for_timeout(3500)

    post = {"shortcode": code, "permalink": f"https://www.instagram.com/p/{code}/"}
    post["timestamp"] = page.eval_on_selector_all(
        "time[datetime]", "els => els.length ? els[0].getAttribute('datetime') : null"
    )
    # キャプション本文は og:description メタタグに完全な形で入っている。
    # DOM 側（h1 等）は匿名だとログイン誘導に差し替えられて取れないことがある。
    post["caption"] = page.eval_on_selector_all(
        'meta[property="og:description"]',
        "els => els.length ? els[0].content : ''",
    )

    # 投稿ページ下部には「他の投稿」のサムネイル群も描画されるため、
    # 素朴に img を集めると無関係な過去投稿まで拾ってしまう。
    # alt テキストには撮影日（例 "July 31, 2026"）が入るので、
    # **この投稿自身の日付を含む alt、または alt が空のもの**だけを採る。
    own_date = ""
    if post["timestamp"]:
        import datetime

        dt = datetime.datetime.fromisoformat(post["timestamp"].replace("Z", "+00:00"))
        own_date = dt.strftime("%B %d, %Y")

    images, alts = [], []
    # カルーセルは「次へ」を押しながら 1 枚ずつ集める
    for _ in range(12):
        shots = page.eval_on_selector_all(
            'img[alt]:not([alt*="プロフィール写真"]):not([alt*="ハイライト"])',
            "els => els.map(e => ({src: e.src, srcset: e.srcset, alt: e.alt}))",
        )
        for s in shots:
            alt = s.get("alt") or ""
            if own_date and alt and own_date not in alt:
                continue  # 「他の投稿」のサムネイル
            url = best_from_srcset(s.get("srcset"), s.get("src"))
            if url and url not in images and "cdninstagram" in url:
                images.append(url)
                alts.append(alt)
        nxt = page.query_selector('button[aria-label="次へ"], button[aria-label="Next"]')
        if not nxt:
            break
        try:
            nxt.click(timeout=3000)
        except Exception:
            break
        page.wait_for_timeout(1800)

    post["images"] = images
    post["alts"] = alts
    return post


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--outdir", default="data/instagram")
    ap.add_argument("--scrolls", type=int, default=6)
    ap.add_argument(
        "--sessionid",
        action="store_true",
        help="環境変数 IG_SESSIONID の Cookie を使う（匿名の 12 件上限を超える）",
    )
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()

    imgdir = os.path.join(args.outdir, "img")
    os.makedirs(imgdir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 1000}, locale="ja-JP", user_agent=UA
        )
        if args.sessionid:
            sid = os.environ.get("IG_SESSIONID")
            if not sid:
                raise SystemExit("IG_SESSIONID が未設定")
            ctx.add_cookies(
                [
                    {
                        "name": "sessionid",
                        "value": sid,
                        "domain": ".instagram.com",
                        "path": "/",
                    }
                ]
            )
        page = ctx.new_page()
        page.goto(
            f"https://www.instagram.com/{args.user}/",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        page.wait_for_timeout(7000)

        profile = {
            "username": args.user,
            "title": page.title(),
            "header_text": page.inner_text("header") if page.query_selector("header") else "",
        }
        print(f"プロフィール: {profile['title']}")

        codes = collect_shortcodes(page, args.scrolls)
        print(f"投稿 {len(codes)} 件を検出\n")

        posts = []
        for i, code in enumerate(codes):
            try:
                post = scrape_post(page, code)
            except Exception as exc:
                print(f"[skip] {code}: {str(exc).splitlines()[0]}")
                continue
            post["local_images"] = []
            if not args.no_images:
                for j, url in enumerate(post["images"]):
                    dest = os.path.join(imgdir, f"{i:03d}-{j}.jpg")
                    try:
                        download(url, dest)
                        post["local_images"].append(dest)
                    except Exception as exc:
                        print(f"[skip] {dest}: {exc}")
            posts.append(post)
            print(
                f"{i:03d} {code} {post['timestamp']} 画像{len(post['local_images'])}枚"
                f"  alt={post['alts'][0][:60] if post['alts'] else ''!r}"
            )

        browser.close()

    out = os.path.join(args.outdir, "posts.json")
    with open(out, "w") as fh:
        json.dump({"profile": profile, "posts": posts}, fh, ensure_ascii=False, indent=2)
    print(f"\n{len(posts)} 件を {out} に保存")


if __name__ == "__main__":
    main()
