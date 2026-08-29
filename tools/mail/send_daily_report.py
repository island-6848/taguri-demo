#!/usr/bin/env python3
"""日報を添付して Gmail API 経由でメール送信する。

## なぜこの方法なのか

送信手段を順に検証し、この環境で動くのがこれだった。

| 方法 | 結果 |
|------|------|
| `mail` / `mailx` / `sendmail` / `msmtp` / `mutt` / `swaks` | いずれも未インストール |
| `git send-email` | 使用不可 |
| SMTP + アプリパスワード | **会社アカウントの設定で不可**（発行できない） |
| Outlook の COM 自動化 | **不可**。クラシック Outlook 非搭載で `Outlook.Application` が未登録。導入済みは新しい Outlook（`Microsoft.OutlookForWindows`）で COM 非対応 |
| Microsoft Graph API | **対象外**。メールは Google Workspace で管理されており Microsoft アカウントは使えない |
| `mailto:` / Gmail の作成 URL | 宛先・件名・本文は渡せるが**添付ができない** |
| **Gmail API + OAuth 2.0** | **これを採用** |

Gmail API を選んだ理由は、アプリパスワードが使えなくても OAuth なら通ること、
そして権限を `gmail.send`（**送信のみ**）に絞れること。メールの閲覧・削除の
権限は要求しないので、万一トークンが漏れても読み取り被害は生じない。

## 初回の設定（一度だけ・所要 5 分程度）

OAuth クライアントを 1 つ作る必要がある。**管理者権限は不要**（同一組織内の
「内部」アプリなので Google の審査も不要）。

  1. https://console.cloud.google.com/ で会社アカウントにログインし、
     プロジェクトを作成する（既存のものでもよい）
  2. 「API とサービス」→「ライブラリ」→ **Gmail API** を検索して有効化
  3. 「API とサービス」→「OAuth 同意画面」→ User Type は **内部**（Internal）
     を選ぶ。内部にすると審査が不要になる
  4. 「API とサービス」→「認証情報」→「認証情報を作成」→
     **OAuth クライアント ID** →アプリケーションの種類は **デスクトップアプリ**
  5. 作成後に JSON をダウンロードし、次の場所に置く:

         mkdir -p ~/.config/nau-mail
         cp ~/ダウンロード先/client_secret_*.json ~/.config/nau-mail/google_client.json

  6. 認証する（ブラウザが開く）:

         python3 tools/mail/send_daily_report.py --login

トークンは `~/.config/nau-mail/google_token.json` に権限 600 で保存される
（**リポジトリには入れない**。パスワード同等の機密情報）。以降は無操作で送信できる。

## 使い方

    # 送信内容を確認するだけ（送信しない・認証も不要）
    python3 tools/mail/send_daily_report.py --dry-run

    # 当日の日報を送信
    python3 tools/mail/send_daily_report.py

    # 日付を指定して送信
    python3 tools/mail/send_daily_report.py --date 2026-08-17

    # 宛先を変える
    python3 tools/mail/send_daily_report.py --to someone@example.com

標準ライブラリのみで動作する。
"""

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SEND_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

# 送信のみ。閲覧・削除の権限は要求しない
SCOPE = "https://www.googleapis.com/auth/gmail.send"

CONFIG_DIR = Path.home() / ".config" / "nau-mail"
CLIENT_PATH = CONFIG_DIR / "google_client.json"
TOKEN_PATH = CONFIG_DIR / "google_token.json"
REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "daily"

DEFAULT_RECIPIENTS = ["yamaguchi@nau.co.jp", "turusaki@nau.co.jp"]
SENDER_NAME = "仲谷"


# --------------------------------------------------------------------------
# 認証
# --------------------------------------------------------------------------

def load_client() -> tuple[str, str]:
    if not CLIENT_PATH.exists():
        raise SystemExit(
            f"OAuth クライアントの設定が見つかりません: {CLIENT_PATH}\n"
            "このファイル冒頭の「初回の設定」に従って Google Cloud Console で\n"
            "デスクトップアプリの OAuth クライアントを作成し、JSON を上記に置いてください。"
        )
    data = json.loads(CLIENT_PATH.read_text(encoding="utf-8"))
    # デスクトップアプリのクライアントは "installed" キーに入る
    node = data.get("installed") or data.get("web") or data
    return node["client_id"], node["client_secret"]


def _post_form(url: str, fields: dict) -> dict:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"トークンエンドポイントがエラーを返しました: HTTP {exc.code}\n"
            f"{exc.read().decode('utf-8', 'replace')[:600]}"
        )


def _save_token(payload: dict, keep_refresh: str | None = None) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    # 更新時のレスポンスには refresh_token が含まれないため引き継ぐ
    if keep_refresh and "refresh_token" not in payload:
        payload["refresh_token"] = keep_refresh
    payload["obtained_at"] = int(time.time())
    TOKEN_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    TOKEN_PATH.chmod(0o600)


def _open_browser(url: str) -> Path:
    """Windows 側の既定ブラウザで認可画面を開き、経由した HTML のパスを返す。

    URL を `explorer.exe` に直接渡したり、利用者に手で貼り付けてもらったりすると、
    クエリ文字列が長いために途中で切れて Google が「400 リクエストの形式が
    正しくありません」を返すことがある。そこで**転送用の HTML を書き出して
    ファイルパスで開く**。パスは短く特殊文字を含まないので壊れようがない。
    """
    page = CONFIG_DIR / "auth.html"
    page.write_text(
        "<!doctype html><meta charset='utf-8'>"
        f"<meta http-equiv='refresh' content='0;url={url}'>"
        "<title>Gmail の認証</title>"
        "<body style='font-family:sans-serif;padding:2rem'>"
        "<p>Google の認証画面へ移動しています…</p>"
        f"<p>切り替わらない場合は <a href='{url}'>こちらをクリック</a>してください。</p>"
        "</body>",
        encoding="utf-8",
    )
    try:
        win = subprocess.run(["wslpath", "-w", str(page)],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        win = None

    for cmd in ([["explorer.exe", win]] if win else []) + [["xdg-open", str(page)]]:
        try:
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=10)
            break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return page


class _CallbackHandler(BaseHTTPRequestHandler):
    """ブラウザからのリダイレクトを 1 回だけ受け取る。"""

    code: str | None = None
    error: str | None = None

    def do_GET(self):  # noqa: N802
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CallbackHandler.code = params.get("code", [None])[0]
        _CallbackHandler.error = params.get("error", [None])[0]
        body = ("認証が完了しました。このタブを閉じてターミナルに戻ってください。"
                if _CallbackHandler.code else
                f"認証に失敗しました: {_CallbackHandler.error}")
        payload = f"<html><meta charset='utf-8'><body><p>{body}</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))

    def log_message(self, *_args):  # サーバのアクセスログを抑制
        pass


def login() -> None:
    client_id, client_secret = load_client()

    # PKCE。デスクトップアプリのクライアントシークレットは秘密にできないため、
    # 認可コードの横取りを防ぐのに PKCE を併用する
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")

    # ループバックリダイレクト。0 を指定して空きポートを取る。
    # ホストは必ず 127.0.0.1 を使う（localhost ではない）。Google が
    # 「ポートは可変でよい」として照合するのはループバック IP リテラルの方で、
    # http://localhost:<ポート> は登録値 http://localhost と一致せず
    # redirect_uri_mismatch（ブラウザ上では「不正なリクエスト」）になる。
    server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",   # リフレッシュトークンを得る
        "prompt": "consent",        # 再認証でも確実に refresh_token を受け取る
    }
    url = f"{AUTH_URI}?{urllib.parse.urlencode(params)}"

    page = _open_browser(url)
    print("=" * 60)
    print("ブラウザで Google の認証画面を開きました。会社アカウントで許可してください。")
    print()
    print("切り替わらない場合は、次のファイルをダブルクリックしてください:")
    print(f"    {page}")
    print("=" * 60)
    print("認証を待っています…", flush=True)
    server.timeout = 300
    server.handle_request()   # リダイレクトを 1 回受け取る
    server.server_close()

    if _CallbackHandler.error:
        raise SystemExit(f"認証に失敗しました: {_CallbackHandler.error}")
    if not _CallbackHandler.code:
        raise SystemExit("時間内に認証が完了しませんでした。--login をやり直してください。")

    tok = _post_form(TOKEN_URI, {
        "grant_type": "authorization_code",
        "code": _CallbackHandler.code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    })
    if "refresh_token" not in tok:
        raise SystemExit(
            "リフレッシュトークンが取得できませんでした。"
            "Google Cloud Console でクライアントの種類が「デスクトップアプリ」に"
            "なっているかを確認してください。"
        )
    _save_token(tok)
    print(f"認証に成功しました。トークンを {TOKEN_PATH} に保存しました。")


def access_token() -> str:
    if not TOKEN_PATH.exists():
        raise SystemExit(
            "未認証です。先に次を実行してください:\n"
            "    python3 tools/mail/send_daily_report.py --login"
        )
    tok = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))

    # 期限に 5 分の余裕を持たせて判定する
    expires_at = tok.get("obtained_at", 0) + int(tok.get("expires_in", 0))
    if time.time() < expires_at - 300:
        return tok["access_token"]

    client_id, client_secret = load_client()
    refreshed = _post_form(TOKEN_URI, {
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "client_id": client_id,
        "client_secret": client_secret,
    })
    _save_token(refreshed, keep_refresh=tok["refresh_token"])
    return refreshed["access_token"]


# --------------------------------------------------------------------------
# メールの組み立て
# --------------------------------------------------------------------------

def load_report(date: str) -> tuple[Path, str]:
    path = REPORT_DIR / f"{date}.md"
    if not path.exists():
        raise SystemExit(f"日報が見つかりません: {path}\n先に日報を作成してください。")
    return path, path.read_text(encoding="utf-8")


def _inline(text: str) -> str:
    """行内の Markdown 記法を落とす。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)          # 強調
    text = re.sub(r"`(.+?)`", r"\1", text)                  # コード
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1（\2）", text)  # リンク
    return text


def _is_row(line: str) -> bool:
    t = line.strip()
    return t.startswith("|") and t.endswith("|") and len(t) > 2


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def to_plain_text(md: str) -> str:
    """メール本文は平文なので、Markdown の記法を落として読める形にする。

    表は「見出し: 値」を並べた行に開く。列見出しが空や「#」の列は見出しを付けない。
    """
    lines = md.split("\n")
    out: list[str] = []
    n = len(lines)
    k = 0
    while k < n:
        line = lines[k].rstrip()
        # 表のかたまり（見出し行・区切り行・データ行）をまとめて処理する
        if (_is_row(line) and k + 1 < n
                and re.fullmatch(r"\s*\|[\s:|-]+\|\s*", lines[k + 1])):
            header = [_inline(c) for c in _cells(line)]
            k += 2
            while k < n and _is_row(lines[k]):
                cells = [_inline(c) for c in _cells(lines[k])]
                parts = []
                for idx, c in enumerate(cells):
                    if not c:
                        continue
                    h = header[idx] if idx < len(header) else ""
                    parts.append(f"{h}: {c}" if h and h != "#" else c)
                if parts:
                    out.append("  ・" + " ／ ".join(parts))
                k += 1
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)   # 見出し記号
        line = re.sub(r"^-\s+", "・", line)       # 箇条書き
        out.append(_inline(line))
        k += 1
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def extract_section(markdown: str, heading: str) -> str:
    """`## <heading>` から次の `## ` までを抜き出し、平文に直して返す。"""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, markdown, re.MULTILINE | re.DOTALL)
    return to_plain_text(m.group(1)) if m else ""


def build_message(date: str, recipients: list[str]) -> tuple[EmailMessage, Path, int]:
    path, markdown = load_report(date)
    msg = EmailMessage()
    msg["Subject"] = f"【日報】{date} {SENDER_NAME}"
    msg["To"] = ", ".join(recipients)
    msg.set_content(f"""お世話になっております。{SENDER_NAME}です。

{date} の日報をお送りします。詳細は添付のファイルをご確認ください。

────────────────────────────
■ 本日の業務実績
────────────────────────────
{extract_section(markdown, "本日の業務実績")}

────────────────────────────
■ 明日の業務予定
────────────────────────────
{extract_section(markdown, "明日の業務予定")}

────────────────────────────

気付いたこと・疑問点・課題および備考は、添付ファイルに記載しております。
ご確認のほどよろしくお願いいたします。

{SENDER_NAME}
""")
    raw = markdown.encode("utf-8")
    msg.add_attachment(raw, maintype="text", subtype="markdown", filename=path.name)
    return msg, path, len(raw)


def send(msg: EmailMessage) -> None:
    body = json.dumps({
        "raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()
    }).encode()
    req = urllib.request.Request(
        SEND_URI, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {access_token()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"送信に失敗: HTTP {exc.code}\n{detail}")


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat(),
                    help="日報の日付 (YYYY-MM-DD)。既定は当日")
    ap.add_argument("--to", action="append", dest="recipients",
                    help="宛先。複数指定可。既定は山口様・津留崎様")
    ap.add_argument("--login", action="store_true",
                    help="初回の認証を行う（ブラウザでの許可が必要）")
    ap.add_argument("--dry-run", action="store_true",
                    help="送信せず、件名・宛先・本文・添付を表示するだけ")
    args = ap.parse_args()

    if args.login:
        login()
        return

    recipients = args.recipients or DEFAULT_RECIPIENTS
    msg, path, size = build_message(args.date, recipients)

    if args.dry_run:
        print(f"件名: {msg['Subject']}")
        print(f"To:   {msg['To']}")
        print(f"添付: {path.name} ({size} バイト)")
        print("\n--- 本文 ---")
        print(msg.get_body(preferencelist=("plain",)).get_content())
        return

    send(msg)
    print(f"送信しました: {msg['Subject']} → {msg['To']}", file=sys.stderr)


if __name__ == "__main__":
    main()
