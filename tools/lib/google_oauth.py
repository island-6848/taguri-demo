#!/usr/bin/env python3
"""Google の OAuth 2.0（デスクトップアプリ + PKCE）。標準ライブラリのみ。

`tools/mail/send_daily_report.py` に書かれていた認証部分を切り出したもの。
**スコープごとにトークンファイルを分ける**のが要点で、送信用のトークンには
送信の権限しか持たせない。読み取りの権限が要る用途は別のトークンを取る。
こうしておくと、片方のトークンが漏れてももう片方の権限は及ばず、
不要になった方だけを個別に失効できる。

クライアント（client_id / client_secret）は用途をまたいで共用する。
設定手順は `tools/mail/send_daily_report.py` の冒頭を参照。

`access_token()` は、未認証のとき・トークンが失効しているときのどちらも、
既定でその場でブラウザを開いて同意を求める（`auto_consent=True`）。
「操作を押したときに同意する」設計に合わせたもので、事前の `--login` は
必須ではない。個人アカウントは同意画面が「外部」（テストモード）にしかならず、
審査を受けていないと発行したトークンが 7 日で切れるが、取り込みのような
「押したときにしか走らない」操作ではそのたびに同意し直す形で支障が無い。

使い方:

    from google_oauth import GoogleOAuth

    oauth = GoogleOAuth(
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        token_name="google_token_tickets.json",
    )
    token = oauth.access_token()   # 未認証・失効時はブラウザで同意してから返る
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

CONFIG_DIR = Path.home() / ".config" / "nau-mail"
CLIENT_PATH = CONFIG_DIR / "google_client.json"


def _load_client() -> tuple[str, str]:
    if not CLIENT_PATH.exists():
        raise SystemExit(
            f"OAuth クライアントの設定が見つかりません: {CLIENT_PATH}\n"
            "tools/mail/send_daily_report.py 冒頭の「初回の設定」に従って\n"
            "デスクトップアプリの OAuth クライアントを作成し、JSON を上記に置いてください。"
        )
    data = json.loads(CLIENT_PATH.read_text(encoding="utf-8"))
    node = data.get("installed") or data.get("web") or data
    return node["client_id"], node["client_secret"]


def _post_form(url: str, fields: dict, *, raise_on_error: bool = True) -> dict | None:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if not raise_on_error:
            return None
        raise SystemExit(
            f"トークンエンドポイントがエラーを返しました: HTTP {exc.code}\n"
            f"{exc.read().decode('utf-8', 'replace')[:600]}"
        )


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

    def log_message(self, *_args):
        pass


def _open_browser(url: str, page: Path) -> Path:
    """Windows 側の既定ブラウザで認可画面を開き、経由した HTML のパスを返す。

    URL を `explorer.exe` に直接渡すとクエリ文字列が長くて途中で切れ、Google が
    「400 リクエストの形式が正しくありません」を返すことがある。転送用の HTML を
    書き出してファイルパスで開けば、パスが短いので壊れない。
    """
    page.write_text(
        "<!doctype html><meta charset='utf-8'>"
        f"<meta http-equiv='refresh' content='0;url={url}'>"
        "<title>Google の認証</title>"
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


class GoogleOAuth:
    def __init__(self, scopes: list[str], token_name: str):
        self.scopes = scopes
        self.token_path = CONFIG_DIR / token_name

    # -- トークンの保存 ---------------------------------------------------

    def _save(self, payload: dict, keep_refresh: str | None = None) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = dict(payload)
        # 更新時のレスポンスには refresh_token が含まれないため引き継ぐ
        if keep_refresh and "refresh_token" not in payload:
            payload["refresh_token"] = keep_refresh
        payload["obtained_at"] = int(time.time())
        self.token_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.token_path.chmod(0o600)

    # -- 認証 -------------------------------------------------------------

    def login(self) -> None:
        client_id, client_secret = _load_client()

        # PKCE。デスクトップアプリのクライアントシークレットは秘密にできないため、
        # 認可コードの横取りを防ぐのに PKCE を併用する
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")

        # ループバックリダイレクト。ホストは必ず 127.0.0.1 を使う（localhost ではない）。
        # Google が「ポートは可変でよい」として照合するのはループバック IP リテラルの方で、
        # http://localhost:<ポート> は登録値と一致せず redirect_uri_mismatch になる。
        server = HTTPServer(("127.0.0.1", 0), _CallbackHandler)
        redirect_uri = f"http://127.0.0.1:{server.server_port}"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",   # リフレッシュトークンを得る
            "prompt": "consent",        # 再認証でも確実に refresh_token を受け取る
        }
        url = f"{AUTH_URI}?{urllib.parse.urlencode(params)}"

        page = _open_browser(url, CONFIG_DIR / f"auth-{self.token_path.stem}.html")
        print("=" * 64)
        print("ブラウザで Google の認証画面を開きました。会社アカウントで許可してください。")
        print()
        print("要求するスコープ:")
        for sc in self.scopes:
            print(f"    {sc}")
        print()
        print("切り替わらない場合は、次のファイルをダブルクリックしてください:")
        print(f"    {page}")
        print("=" * 64)
        print("認証を待っています…", flush=True)
        server.timeout = 300
        server.handle_request()
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
        self._save(tok)
        print(f"認証に成功しました。トークンを {self.token_path} に保存しました。")

    def access_token(self, *, auto_consent: bool = True) -> str:
        """有効なアクセストークンを返す。

        **同意画面が要るときは、ここでブラウザを開いて待つ**（`auto_consent` が
        既定で真のとき）。初回で未認証のとき、あるいはリフレッシュトークンが
        失効しているとき（個人アカウントは「外部」の同意画面しか選べず、審査を
        受けていないと発行したトークンが 7 日で切れる）のどちらも同じ扱いにする。
        これは「押した操作の中で同意する」設計に合わせたもので、裏で黙って
        Gmail へ接続するのではなく、取得のたびに何を渡しているかが本人に見える。
        """
        if not self.token_path.exists():
            if not auto_consent:
                raise SystemExit(
                    f"未認証です（{self.token_path} が無い）。先に --login を実行してください。"
                )
            self.login()
        tok = json.loads(self.token_path.read_text(encoding="utf-8"))

        # 期限に 5 分の余裕を持たせて判定する
        expires_at = tok.get("obtained_at", 0) + int(tok.get("expires_in", 0))
        if time.time() < expires_at - 300:
            return tok["access_token"]

        client_id, client_secret = _load_client()
        refreshed = _post_form(TOKEN_URI, {
            "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"],
            "client_id": client_id,
            "client_secret": client_secret,
        }, raise_on_error=auto_consent)
        if refreshed is None:
            # リフレッシュトークンが失効している（7 日制限、または本人が取り消した）。
            # 同意をやり直せば済むので、ここで止めずにブラウザを開く。
            self.login()
            tok = json.loads(self.token_path.read_text(encoding="utf-8"))
            return tok["access_token"]
        self._save(refreshed, keep_refresh=tok["refresh_token"])
        return refreshed["access_token"]
