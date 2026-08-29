#!/usr/bin/env python3
"""観劇のチケット購入確認メールを Gmail から探す。

## なぜメールなのか

観劇履歴（いつ・何を・いくらで・どの席で観たか）を集める手段のうち、
**購入確認メールが最も網羅的で、かつ他人のサイトを 1 件も見に行かない。**
チケットを買えば事業者は必ず確認メールを送るため、購入履歴は既に自分の
メールボックスの中にある。詳細は #000005 を参照。

## Gmail API + OAuth（個人の Gmail）

以前は IMAP + アプリパスワードで接続していたが、2026-08-28 に OAuth へ切り替えた
（詳しい理由は下の「なぜ IMAP + アプリパスワードをやめたのか」）。

- **画面の「取り込みを始める」を押したときに、必要なら同意画面が開く。** 読み取り
  専用（`gmail.readonly`）の権限だけを渡すので、押すたびに何を渡しているかが本人に
  見える形にした
- トークンは `~/.config/nau-mail/google_token_tickets.json` に、送信用（日報）の
  `google_token.json` とは**別ファイル**で保存する。送信用は `gmail.send` のままなので、
  片方が漏れてももう片方の権限は及ばない
- クライアント設定（`~/.config/nau-mail/google_client.json`）は送信用と共用する。
  クライアントは「誰が Google に許可を求めているか」を表すだけで、実際にどの
  Google アカウントで許可するかは同意画面でその都度選ぶため、共用しても支障はない

## なぜ IMAP + アプリパスワードをやめたのか

アプリパスワードは有効期限の無い恒久的な鍵で、発行後は 2 段階認証を素通りしてメール
ボックス全体（読み取り専用の運用はコード側の作法でしかない）へのアクセスを許してしまう。
利用者からは「メールから何が抜かれているか分からない」という不安のほうが大きく、**同意画面
に毎回スコープが出る OAuth のほうが、渡している権限が見える**（起案者の判断・2026-08-28）。

個人アカウントの OAuth は「外部」（テストモード）でしか動かせず、審査を受けていない
クライアントは発行したトークンが 7 日で失効するが、**取り込みは「取り込みを始める」を
押したときにしか走らないので、そのたびに同意し直す形で支障は無い。**

## 使い方

    # 差出人の実態を調べる（何がどれだけ届いているか）
    python3 tools/tickets/scan_ticket_mail.py --probe

    # 特定の検索クエリの件数と見出しを確認する
    python3 tools/tickets/scan_ticket_mail.py --query "from:eplus.jp" --show 20

    # 先に同意だけ済ませておきたいとき（無くても --probe 等の中で自動的に開く）
    python3 tools/tickets/scan_ticket_mail.py --login
"""

from __future__ import annotations

import argparse
import base64
import collections
import email
import email.utils
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from email.header import decode_header, make_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from google_oauth import GoogleOAuth  # noqa: E402

API = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_NAME = "google_token_tickets.json"

# 観劇のチケットを扱っていそうな差出人の候補。実態は --probe で確かめる。
#
# **2026-08-20 の実測で分かったこと（検証 004）**
#   - 発行元はチケット事業者だけではない。**劇場・製作会社・ファンクラブからも購入確認が届く。**
#     事業者だけを候補にすると、申告した対象（劇場3主催・作品1）の履歴が丸ごと落ちる
#   - **ドメインを間違えると 0 通に見える。** イープラスは eplus.jp では 0 通だが
#     eplus.co.jp で 1,216 通あった。0 通は「使っていない」ではなく「ドメインが違う」かもしれない
CANDIDATE_DOMAINS = [
    # チケット事業者
    ("イープラス", "eplus.co.jp"),
    ("イープラス(旧候補)", "eplus.jp"),
    ("チケットぴあ", "pia.jp"),
    ("ローソンチケット", "l-tike.com"),
    ("カンフェティ", "confetti-web.com"),
    ("CoRich チケット", "corich.jp"),
    ("カルテットオンライン", "quartet-online.net"),
    ("teket", "teket.jp"),
    ("Peatix", "peatix.com"),
    ("ZAIKO", "zaiko.io"),
    ("楽天チケット", "ticket.rakuten.co.jp"),
    ("チケットステーション", "ticket-station.jp"),
    ("Stores 予約", "stores.jp"),
    ("Livepocket", "livepocket.jp"),
    # 劇場・製作会社・ファンクラブ（実測で見つかった分）
    ("劇場3", "nntt.jac.go.jp"),
    ("松竹", "shochiku.co.jp"),
    ("東宝", "toho.co.jp"),
    ("ホリプロ", "horipro.co.jp"),
    ("ジャニーズ／STARTO", "johnnys-net.jp"),
    ("劇団6", "bungakuza.com"),
    ("劇団7", "seinenza.com"),
    ("劇団4", "haiyuza.net"),
]

# 差出人が分からない分を拾うためのキーワード掃き出し
SWEEP_QUERY = (
    '{チケット 公演 観劇 開演 座席 ご予約 ご来場 引換 半券} '
    '-in:chats -from:me'
)


class Gmail:
    def __init__(self):
        self.oauth = GoogleOAuth(scopes=SCOPES, token_name=TOKEN_NAME)

    def _get(self, path: str, params: dict) -> dict:
        url = f"{API}{path}?{urllib.parse.urlencode(params, doseq=True)}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.oauth.access_token()}",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:500]
            if exc.code == 403 and "insufficient" in body.lower():
                raise SystemExit(
                    "権限が足りません。gmail.readonly を付けて認証し直してください:\n"
                    "    python3 tools/tickets/scan_ticket_mail.py --login"
                )
            raise SystemExit(f"Gmail API がエラーを返しました: HTTP {exc.code}\n{body}")

    def ids(self, query: str, cap: int = 4000) -> list[str]:
        """検索に一致するメッセージ ID を集める。ID のみなので 1 回 500 件と軽い。"""
        out, page = [], None
        while len(out) < cap:
            params = {"q": query, "maxResults": 500}
            if page:
                params["pageToken"] = page
            data = self._get("/messages", params)
            out += [m["id"] for m in data.get("messages", [])]
            page = data.get("nextPageToken")
            if not page:
                break
        return out[:cap]

    def headers(self, msg_id: str) -> dict:
        data = self._get(f"/messages/{msg_id}", {
            "format": "metadata",
            "metadataHeaders": ["From", "Subject", "Date"],
        })
        h = {x["name"]: x["value"] for x in data.get("payload", {}).get("headers", [])}
        return {
            "id": msg_id,
            "from": h.get("From", ""),
            "subject": _decode(h.get("Subject", "")),
            "date": h.get("Date", ""),
        }

    def headers_many(self, ids: list[str], workers: int = 8) -> list[dict]:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(self.headers, ids))

    def body_text(self, msg_id: str) -> str:
        """メール本文を取ってくる。**呼ぶたびに読みに行き、端末には残さない**（本文を
        保存しないという企画書の約束を守るため）。"""
        data = self._get(f"/messages/{msg_id}", {"format": "raw"})
        raw = data.get("raw")
        if not raw:
            return ""
        raw += "=" * (-len(raw) % 4)   # Gmail API はパディングを省くので、長さに合わせて補う
        msg = email.message_from_bytes(base64.urlsafe_b64decode(raw))
        text = ""
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    text = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", "replace")
                    break
                except Exception:
                    pass
        if not text:
            try:
                text = msg.get_payload(decode=True).decode("utf-8", "replace")
            except Exception:
                text = ""
        return text


def _decode(raw: str) -> str:
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return raw


def _domain(from_header: str) -> str:
    addr = email.utils.parseaddr(from_header)[1]
    return addr.split("@")[-1].lower() if "@" in addr else "(不明)"


def probe(gm: Gmail, sweep_sample: int) -> None:
    print("=" * 72)
    print("1. 候補にしていた差出人ドメインの実績")
    print("=" * 72)
    found = []
    for label, dom in CANDIDATE_DOMAINS:
        n = len(gm.ids(f"from:{dom}", cap=4000))
        mark = "●" if n else "・"
        print(f"  {mark} {label:<22} from:{dom:<24} {n:>5} 通")
        if n:
            found.append((label, dom, n))

    print()
    print("=" * 72)
    print(f"2. キーワード掃き出しで見つかる差出人（上位 40・最大 {sweep_sample} 通を確認）")
    print("=" * 72)
    ids = gm.ids(SWEEP_QUERY, cap=sweep_sample)
    print(f"  一致: {len(ids)} 通（上限 {sweep_sample}）。差出人を集計します…", flush=True)
    if not ids:
        print("  一致なし")
        return
    rows = gm.headers_many(ids)
    counter = collections.Counter(_domain(r["from"]) for r in rows)
    known = {d for _, d, _ in found}
    for dom, n in counter.most_common(40):
        new = "" if any(dom.endswith(k) for k in known) else "  ← 候補に無かった"
        print(f"  {n:>4} 通  {dom}{new}")

    print()
    print("=" * 72)
    print("3. 見出しの例（各ドメイン 2 件まで）")
    print("=" * 72)
    seen: dict[str, int] = collections.defaultdict(int)
    for r in sorted(rows, key=lambda x: x["date"], reverse=True):
        d = _domain(r["from"])
        if seen[d] >= 2:
            continue
        seen[d] += 1
        print(f"  [{d}] {r['subject'][:70]}")


def show(gm: Gmail, query: str, limit: int) -> None:
    ids = gm.ids(query, cap=4000)
    print(f"クエリ: {query}")
    print(f"一致: {len(ids)} 通")
    for r in gm.headers_many(ids[:limit]):
        print(f"  {r['date'][:16]:<18} {_decode(r['from'])[:34]:<36} {r['subject'][:60]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--login", action="store_true",
                    help="先に同意だけ済ませる（無くても他の操作の中で自動的に開く）")
    ap.add_argument("--probe", action="store_true", help="差出人の実態を調べる")
    ap.add_argument("--query", help="任意の Gmail 検索クエリ")
    ap.add_argument("--show", type=int, default=20, help="--query で表示する件数")
    ap.add_argument("--sweep-sample", type=int, default=400,
                    help="--probe のキーワード掃き出しで見出しを取る上限")
    args = ap.parse_args()

    if args.login:
        Gmail().oauth.login()
        return
    gm = Gmail()
    if args.probe:
        probe(gm, args.sweep_sample)
        return
    if args.query:
        show(gm, args.query, args.show)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
