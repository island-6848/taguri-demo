#!/usr/bin/env python3
"""Instagram の公開アカウントから全投稿の画像とキャプションを取得する。

## 匿名アクセスが不可能であることの実測結果（2026-08-17）

以下をすべて試し、いずれも失敗した。

| 方法 | 結果 |
|------|------|
| プロフィール HTML を直接取得 | HTTP 200 だが JS シェルのみ。投稿データ・画像 URL を一切含まない |
| `i.instagram.com/api/v1/users/web_profile_info/`（`X-IG-App-ID` 付き） | HTTP 400 |
| `?__a=1&__d=dis` | HTTP 201 / 本文 0 バイト |
| 投稿の `/embed/captioned/` | JS シェルが返り画像 URL なし |

したがって**セッション Cookie（`sessionid`）が必須**である。ヘッドレス
ブラウザによる代替もこの環境では不可（pip / npm / sudo が使えず
Playwright や Chromium を導入できない）。

## 2 つの取得モード

1. `--sessionid`（推奨・手軽）
   ブラウザで Instagram にログインし、Cookie `sessionid` の値を渡す。
   自分または店舗のアカウントのものを使う。**Cookie はパスワードと同等の
   機密情報**なので、引数ではなく環境変数 `IG_SESSIONID` で渡すこと
   （引数はプロセス一覧に見えてしまう）。取得後は Instagram の
   「すべてのセッションからログアウト」で無効化できる。

2. `--graph-token`（公式・恒久運用向け）
   Instagram Graph API を使う。アカウントがプロフェッショナル
   （ビジネス / クリエイター）で Facebook ページに紐づいている必要がある。
   Meta for Developers でアプリを作成しアクセストークンを発行する。
   規約上こちらが正式な経路で、Cookie の共有が不要という利点がある。

## 使い方

    export IG_SESSIONID='...'
    python3 tools/instagram/fetch_posts.py --user yorucafe_mayoi \
        --outdir data/instagram --max-posts 300

    # 公式 API の場合
    export IG_GRAPH_TOKEN='...'
    python3 tools/instagram/fetch_posts.py --graph --ig-user-id 1784... \
        --outdir data/instagram

出力:
  data/instagram/posts.json      投稿メタデータ（キャプション・日時・いいね数）
  data/instagram/img/NNN-*.jpg   画像本体（Read ツールで視覚的に解析できる）

標準ライブラリのみで動作する。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
IG_APP_ID = "936619743392459"  # Instagram Web の公開 App ID
PROFILE_API = "https://www.instagram.com/api/v1/users/web_profile_info/"
FEED_API = "https://www.instagram.com/api/v1/feed/user/{user_id}/"
GRAPH_API = "https://graph.facebook.com/v21.0"


def request_json(url, sessionid=None, params=None, retries=3):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": UA,
        "X-IG-App-ID": IG_APP_ID,
        "Accept": "*/*",
        "Referer": "https://www.instagram.com/",
    }
    if sessionid:
        headers["Cookie"] = f"sessionid={sessionid}"
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            # 429（レート制限）は待って再試行。それ以外は即座に上げる。
            if exc.code == 429 and attempt < retries - 1:
                wait = 30 * (attempt + 1)
                print(f"[429] レート制限。{wait}s 待機", file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)


def best_image(node):
    """最も解像度の高い画像 URL を選ぶ。メニュー画像は文字が小さいため重要。"""
    candidates = node.get("image_versions2", {}).get("candidates", [])
    if candidates:
        return max(candidates, key=lambda c: c.get("width", 0))["url"]
    return node.get("display_url") or node.get("thumbnail_url")


def collect_media(item):
    """単体投稿・カルーセル・動画のサムネイルを一律に画像 URL のリストへ。"""
    if item.get("carousel_media"):
        return [best_image(m) for m in item["carousel_media"]]
    return [best_image(item)]


def caption_of(item):
    cap = item.get("caption")
    if isinstance(cap, dict):
        return cap.get("text", "")
    return cap or ""


def fetch_via_session(username, sessionid, max_posts):
    profile = request_json(
        PROFILE_API, sessionid=sessionid, params={"username": username}
    )
    user = profile["data"]["user"]
    user_id = user["id"]
    print(
        f"@{username} id={user_id} "
        f"投稿={user.get('edge_owner_to_timeline_media', {}).get('count')} "
        f"フォロワー={user.get('edge_followed_by', {}).get('count')}"
    )
    print(f"bio: {user.get('biography', '')!r}\n")

    items, max_id = [], None
    while len(items) < max_posts:
        params = {"count": 33}
        if max_id:
            params["max_id"] = max_id
        page = request_json(
            FEED_API.format(user_id=user_id), sessionid=sessionid, params=params
        )
        batch = page.get("items", [])
        if not batch:
            break
        items.extend(batch)
        print(f"  取得 {len(items)} 件")
        if not page.get("more_available"):
            break
        max_id = page.get("next_max_id")
        time.sleep(2)  # 連続取得は 429 を招くため間隔を置く
    return items[:max_posts]


def fetch_via_graph(ig_user_id, token, max_posts):
    fields = (
        "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,"
        "like_count,comments_count,children{media_url,media_type}"
    )
    url = f"{GRAPH_API}/{ig_user_id}/media"
    params = {"fields": fields, "access_token": token, "limit": 50}
    items = []
    while url and len(items) < max_posts:
        req = urllib.request.Request(
            f"{url}?{urllib.parse.urlencode(params)}" if params else url,
            headers={"User-Agent": UA},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = json.load(resp)
        items.extend(page.get("data", []))
        print(f"  取得 {len(items)} 件")
        url = page.get("paging", {}).get("next")
        params = None
    return items[:max_posts]


def normalize_graph(item):
    urls = []
    if item.get("children"):
        urls = [c.get("media_url") for c in item["children"]["data"] if c.get("media_url")]
    elif item.get("media_url"):
        urls = [item["media_url"]]
    elif item.get("thumbnail_url"):
        urls = [item["thumbnail_url"]]
    return {
        "id": item.get("id"),
        "caption": item.get("caption", ""),
        "timestamp": item.get("timestamp"),
        "permalink": item.get("permalink"),
        "like_count": item.get("like_count"),
        "images": urls,
    }


def normalize_session(item):
    return {
        "id": item.get("code") or item.get("pk"),
        "caption": caption_of(item),
        "timestamp": item.get("taken_at"),
        "permalink": f"https://www.instagram.com/p/{item.get('code')}/",
        "like_count": item.get("like_count"),
        "images": [u for u in collect_media(item) if u],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", help="ユーザー名（セッション方式）")
    ap.add_argument("--graph", action="store_true", help="公式 Graph API を使う")
    ap.add_argument("--ig-user-id", help="Graph API の Instagram ユーザー ID")
    ap.add_argument("--outdir", default="data/instagram")
    ap.add_argument("--max-posts", type=int, default=300)
    ap.add_argument("--no-images", action="store_true", help="メタデータのみ取得")
    args = ap.parse_args()

    imgdir = os.path.join(args.outdir, "img")
    os.makedirs(imgdir, exist_ok=True)

    if args.graph:
        token = os.environ.get("IG_GRAPH_TOKEN")
        if not token or not args.ig_user_id:
            raise SystemExit("IG_GRAPH_TOKEN と --ig-user-id が必要")
        raw = fetch_via_graph(args.ig_user_id, token, args.max_posts)
        posts = [normalize_graph(x) for x in raw]
    else:
        sessionid = os.environ.get("IG_SESSIONID")
        if not sessionid:
            raise SystemExit(
                "IG_SESSIONID が未設定。匿名アクセスは Instagram 側で\n"
                "封じられているため（詳細はこのファイル冒頭の実測表を参照）、\n"
                "ログイン済みブラウザの Cookie `sessionid` が必要。"
            )
        if not args.user:
            raise SystemExit("--user が必要")
        raw = fetch_via_session(args.user, sessionid, args.max_posts)
        posts = [normalize_session(x) for x in raw]

    for i, post in enumerate(posts):
        post["local_images"] = []
        if args.no_images:
            continue
        for j, url in enumerate(post["images"]):
            dest = os.path.join(imgdir, f"{i:03d}-{j}.jpg")
            try:
                download(url, dest)
                post["local_images"].append(dest)
            except Exception as exc:
                print(f"[skip] {dest}: {exc}", file=sys.stderr)
        print(f"{i:03d} {post['timestamp']} 画像{len(post['local_images'])}枚 "
              f"{post['caption'][:40]!r}")

    out = os.path.join(args.outdir, "posts.json")
    with open(out, "w") as fh:
        json.dump(posts, fh, ensure_ascii=False, indent=2)
    print(f"\n{len(posts)} 件を {out} に保存")


if __name__ == "__main__":
    main()
