r"""たぐりの管理画面を、このパソコンだけで開く（127.0.0.1 にだけ開く・起動のたびに変わる鍵付き）。

    python3 tools/admin/serve_admin.py            # ブラウザが開く（Windows は py tools\admin\serve_admin.py）
    python3 tools/admin/serve_admin.py --no-open  # URL を出すだけ
    ダブルクリックで開くなら tools/admin/open-admin.command（Mac）・open-admin.bat（Windows）

URL はいつも http://127.0.0.1:8770/?t=<鍵>。鍵は data/admin/token に控え、次に起動しても同じなので、
ブックマークしておけます（動いているあいだだけ開けます）。8770 がふさがっていれば空いている番号で開きます。

要るもの: wrangler にログイン済み（`cd cloudflare && npx wrangler login`）。ポスターを入れるときは
環境変数 CLOUDFLARE_ACCOUNT_ID と CLOUDFLARE_API_TOKEN（R2 の書き込み権限）と Pillow。
読み取り（あらすじ → 題材）に手元の Claude Code（`claude`）を使う。無くても積んでおける。
"""
from __future__ import annotations

import argparse
import base64
import json
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import admin as A  # noqa: E402

PAGE = HERE / "admin.html"
MAX_BODY = 30 * 1024 * 1024
PORT = 8770
NO_KEY = """<!doctype html><meta charset="utf-8"><title>たぐり 管理画面</title>
<body style="font:15px/1.7 system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px">
<h1 style="font-size:20px">鍵の付いた URL から開いてください</h1>
<p>管理画面を起動したときに、黒い画面（ターミナル）に <b>http://127.0.0.1:8770/?t=…</b> と出ます。その URL をそのまま開いてください。
鍵は data/admin/token に控えてあり、起動し直しても変わりません。</p></body>"""
LOCK = threading.Lock()          # D1 と記録への書き込みは 1 つずつ


def make_handler(token: str, db: A.D1, data: Path):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):   # noqa: D401 - quiet
            pass

        def _ok_origin(self) -> bool:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got = self.headers.get("X-Admin-Token") or (q.get("t") or [""])[0]
            host = (self.headers.get("Host") or "").split(":")[0]
            return secrets.compare_digest(got, token) and host in ("127.0.0.1", "localhost")

        def _send(self, code: int, body, ctype="application/json; charset=utf-8"):
            raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            if not self._ok_origin():
                if u.path == "/":
                    return self._send(403, NO_KEY.encode("utf-8"), "text/html; charset=utf-8")
                return self._send(403, {"ok": False, "error": "鍵が違います（起動したときに出た URL から開いてください）"})
            try:
                if u.path == "/":
                    return self._send(200, PAGE.read_bytes().replace(b"__TOKEN__", token.encode()), "text/html; charset=utf-8")
                if u.path == "/api/search":
                    return self._send(200, {"ok": True, "rows": A.search(db, q.get("q", ""))})
                if u.path == "/api/stage":
                    sid = q.get("id", "")
                    return self._send(200, {"ok": True, "stage": A.stage(db, sid), "log": A.read_log(data, sid),
                                            "queued": any(t["stage_id"] == sid for t in A.queue_list(data))})
                if u.path == "/api/queue":
                    return self._send(200, {"ok": True, "tasks": A.queue_list(data), "claude": bool(A.claude_cli())})
                if u.path == "/api/log":
                    return self._send(200, {"ok": True, "log": A.read_log(data, limit=100)})
                return self._send(404, {"ok": False, "error": "ありません"})
            except A.AdminError as e:
                return self._send(400, {"ok": False, "error": str(e)})
            except Exception as e:                                   # noqa: BLE001
                return self._send(500, {"ok": False, "error": f"うまくいきませんでした（{type(e).__name__}: {e}）"})

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if not self._ok_origin() or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self._send(403, {"ok": False, "error": "鍵が違います"})
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"ok": False, "error": "大きすぎます"})
            try:
                b = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, {"ok": False, "error": "JSON が読めません"})
            sid = str(b.get("stage_id") or "")
            try:
                with LOCK:
                    if u.path == "/api/save":
                        r = A.save(db, data, sid, synopsis=b.get("synopsis"), themes=b.get("themes"), info=b.get("info"))
                        # あらすじを入れて題材を入れていなければ、題材の読み取りを積む（Claude Code が読む）
                        syn = (b.get("synopsis") or "").strip()
                        if syn and not A.norm_words(b.get("themes") or []):
                            r["queued"] = A.queue_add(data, sid, syn, str(b.get("title") or ""))
                        return self._send(200, {"ok": True, **r})
                    if u.path == "/api/poster":
                        body = base64.b64decode(str(b.get("data") or "").split(",")[-1] or b"")
                        return self._send(200, {"ok": True, **A.add_poster(db, data, sid, body, ended=bool(b.get("ended")))})
                    if u.path == "/api/analyze":
                        return self._send(200, {"ok": True, "done": A.analyze_now(db, data, [sid] if sid else None)})
                    if u.path == "/api/queue_drop":
                        A.queue_drop(data, {sid})
                        return self._send(200, {"ok": True})
                return self._send(404, {"ok": False, "error": "ありません"})
            except A.AdminError as e:
                return self._send(400, {"ok": False, "error": str(e)})
            except (ValueError, TypeError) as e:
                return self._send(400, {"ok": False, "error": f"入力がおかしい（{type(e).__name__}）"})
            except Exception as e:                                   # noqa: BLE001
                return self._send(500, {"ok": False, "error": f"うまくいきませんでした（{type(e).__name__}: {e}）"})

    return H


def load_token(data: Path) -> str:
    """鍵は data/admin/token に控える（本人だけが読める権限）。起動し直しても同じ URL で開ける。"""
    p = data / "token"
    if p.exists() and len(p.read_text(encoding="utf-8").strip()) >= 24:
        return p.read_text(encoding="utf-8").strip()
    data.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_urlsafe(24)
    p.write_text(tok + "\n", encoding="utf-8")
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return tok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    token = load_token(A.DATA)
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(token, A.D1(), A.DATA))
    except OSError:
        print(f"{a.port} 番がふさがっているので、空いている番号で開きます（管理画面がもう動いているなら、そちらを開いてください）", flush=True)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(token, A.D1(), A.DATA))
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={token}"
    print(f"たぐりの管理画面: {url}\n（このパソコンだけで開けます。止めるには Ctrl-C）", flush=True)
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
