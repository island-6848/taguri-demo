#!/usr/bin/env python3
"""画面を `127.0.0.1` で開き、押された内容を DB に書き戻して落ちる。

## なぜサーバを立てるのか

**当初は「静的 HTML を `file://` で開く」構成だった。これは撤回されている**（企画書 5 章）。
この企画の中核は、興味あり／興味なし・◎○△×・感想・お気に入りの登録を画面から受け取って
次の週の推薦に戻す輪である。**`file://` で開いた HTML は SQLite に 1 文字も書き戻せない。**

**「サーバを立てない」の意味は「公開されたサーバとアカウントを持たない」ことである。**
端末内で完結する一時プロセスは禁じていない。書き分けないと、機密性のための方針が
企画の中核を壊す。

## 入口は 1 つで、画面はナビゲーションで移動する

**画面ごとに HTML を書き出して別々に開かせる形はやめた**（起案者の指摘）。
道の割り方は企画書 1 章に従う（`tools/taguri/app.py` の冒頭）。

| 方式 | 道 |
|---|---|
| GET | `/recommend`（`?pref=` で都道府県を絞る。既定は全国）・`/recommend/interest`・`/recommend/favourites`・`/calendar`（`?kind=`・`?pref=` で束・都道府県を絞る。既定はすべて）・`/rate`・`/rate/unrated`・`/rate/notes`・`/register`・`/records`・`/records/works`・`/search`・`/settings`・`/export.json`・`/data.zip`・`/img/<名前>`・`/api/import_status`・`/api/mail_hints`・`/api/suggest`・`/api/suggest_web` |
| POST | `/api/react`・`/api/rate`・`/api/note`・`/api/favourite`・`/api/missed`・`/api/add_work`・`/api/fix_work`・`/api/merge_work`・`/api/drop_work`・`/api/restore_work`・`/api/purge_work`・`/api/unseen`・`/api/weight`・`/api/link_stage`・`/api/hand_credits`・`/api/hand_theme`・`/api/hand_poster`・`/api/import_mail`・`/api/close` |

**画面を閉じたら自動で終了する仕組みは撤回した**（起案者の指示・2026-08-27 ──「記録を
見返す」のような画面は長時間開いたままにする使い方を想定しており、タブを裏に回した
だけで自動終了することがあってはならないため）。当初は `pagehide`（この事象はページを
移動するときにも発火し、ナビゲーションを 1 回押すだけでシステムが落ちていた）、続けて
15 秒ごとの心拍（ブラウザのタブが裏に回るとブラウザ自身が間隔を間引くことがあり、
長く開いたままにすると落ちることがあった）を試したが、**どちらも「長く開いたままに
する」という実際の使い方と噛み合わなかった。** いまは、押すと終了する「終わる」ボタン
（`/api/close`）と、ターミナルでの `Ctrl-C` だけに絞ってある。**最初の接続が
一定時間（`GRACE_SEC`）来ないときだけは、これまでどおり自動で落ちる**
（ブラウザが自動で開かない環境で、開き忘れたまま待ち受けが残り続けるのを防ぐため）。

**これ以外の道は 404 にする。** 静的ファイルの配信をしないので、`ratings.db` を読ませる道が無い。

## 守り ── 企画書 5 章の 6 項目のうち、この口が受け持つ 4 つ

| | 何をするか | なぜ |
|---|---|---|
| 2 | **待ち受けを `127.0.0.1` に固定する** | `0.0.0.0` で待つと、同じ LAN の他の端末から観劇記録が読める |
| 3 | **起動ごとに乱数のトークンを作り、これを持たない要求を受け付けない** | ローカルでも、同じ端末の別プロセス（他のタブで開いた外部サイトを含む）は `127.0.0.1` に到達できる |
| 4 | **受け付ける操作を列挙したものだけにする** | 任意の SQL も任意のパスも受けない。**操作を数え上げられることが、書き込み口を持つ条件である** |
| 6 | **常駐させない** | 画面を閉じたら落ちる。放置された待ち受け口を残さない |

**トークンは HTML に埋めるが、ファイルには書かない。** 配る直前に `__TAGURI_TOKEN__` を
置き換える。**画面の間を移動するリンクにも同じ鍵が載る。**

**API キーは画面に渡さない**（守り 1）。外部への取得もここでは一切しない（守り 5）
── このプロセスが触るのは `ratings.db` と手元のデータファイルだけである。
"""

from __future__ import annotations

import datetime
import http.cookies
import http.server
import io
import json
import os
import queue
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.parse
import webbrowser
import zipfile
from html import escape as h_esc  # `html` はdo_GET内でページ本体を指すローカル変数名と衝突する
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import app as APP                                                  # noqa: E402
import auth as AU                                                  # noqa: E402
import feedback as FB                                              # noqa: E402
import recommend as RC                                             # noqa: E402
import render_recommend as RR                                       # noqa: E402
import stage_calendar as SC                                        # noqa: E402

# **#000008: 復旧コード認証。既存の「起動ごとの単一トークン」（`srv.token`・
# `_tok`）とは別の、利用者ごとの識別経路として追加する。** 既存の道は
# 今回まだ書き換えない ── `app.py` のページ関数群がまだ「利用者ごとの
# データ」を受け取れる形になっていない（E3、未着手）ため、ここで認証だけ
# 切り替えると、鍵は複数の利用者を区別できるのに中身は 1 人分のまま、
# という食い違った状態になる。**この節が持つのは認証層だけで、まだ
# どの画面もこの鍵に基づいてデータを出し分けてはいない。**
SESSION_COOKIE = "tg_session"

# **評価の段階は列挙したものだけ受ける。**「まだ判断できない」は段階とは別の欄で、
# 集計では欠測として分母から外す（企画書 4 章）。
VERDICTS = ("◎", "○", "△", "×", "まだ判断できない")

# **三択の各値が DB のどの列に入るかを 1 か所に固定する。**
# `owned` と `interest` は別の列である ── 「持っている」は「興味あり」の上位互換ではなく、
# 強さの順序（持っている ＞ 興味あり ＞ 興味なし）が入力の側に入っている。
REACT = {"owned": {"owned": 1}, "interest": {"interest": 1}, "nointerest": {"interest": 0}}

# 「観ればよかった」の申告。**口が無いままだと絞り込みの穴を永久に測れない**（V35）
MISSED_SCHEMA = """
CREATE TABLE IF NOT EXISTS missed (
    title      TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    note       TEXT
);
"""

# **登録した題名から、演者とあらすじを調べて添える列**（起案者の指示・2026-08-25 ──
# 「観ればよかった」で足した公演は、演者やあらすじを調べてまず表示してほしい）。
# `PRAGMA table_info` で無いものだけ足す（既存の DB には `IF NOT EXISTS` が効かない）。
MISSED_LOOKUP_COLUMNS = {
    "stage_id": "TEXT", "venue": "TEXT", "period": "TEXT",
    "fields_json": "TEXT", "synopsis": "TEXT",
    "lookup_note": "TEXT", "looked_up_at": "TEXT",
}


def _migrate_missed(con: sqlite3.Connection) -> None:
    have = {r[1] for r in con.execute("PRAGMA table_info(missed)")}
    with con:
        for col, decl in MISSED_LOOKUP_COLUMNS.items():
            if col not in have:
                con.execute(f"ALTER TABLE missed ADD COLUMN {col} {decl}")


IMG = ROOT / "data" / "review" / "img"
GRACE_SEC = 1800       # 最初の接続が来るまで待つ上限
# 取り込みの進み具合が流れてくる行の目印（`tools/tickets/extract_performances.py`）
MARK = "@@TAGURI "
# **`-u` を付ける。** 溜めて出されると、進み具合が終わったあとにまとめて届く
IMPORT_CMD = [sys.executable, "-u", "tools/tickets/extract_performances.py", "--run"]

# ---- 帯をどこまで伸ばすか ---------------------------------------------------
#
# **段ごとに 0 から数え直すと、段が変わるたびに帯が戻る** ── 差出人を 900 通まで
# 確かめて 99% まで来た帯が、本文の 1 通目で 1% に落ちる。**進んでいるのに戻って
# 見えるのは、進み具合として間違っている。** そこで 3 つの段を 1 本に通し、
# 段ごとに受け持つ区間を決める。
#
# **区間の広さは、かかる時間の比で決める**（通数の比ではない）── 差出人の確認は
# 200 通ずつまとめて 1 回の要求で済むが、本文は 1 通ずつ取りに行く。
# 実測（437 通）では本文の読み取りが全体のほとんどを占める。
#
# **段 1（受信箱を探している間）はここに入れない。** 何通あるかが分かる前なので、
# 割合を出せない ── 帯は伸ばさずに流す（`app._import_bar` の `iwait`）。
SPAN = {2: (0, 12), 3: (12, 100)}


def _pct(step: int, n: int, total: int) -> int:
    """段と通数から、帯をどこまで伸ばすかを出す。**終わる前に 100 にはしない。**"""
    if not total:
        return 0
    lo, hi = SPAN.get(step, (0, 100))
    return max(0, min(99, int(lo + (hi - lo) * n / total)))


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "taguri"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):        # noqa: A003
        pass                                  # 進捗表示を要求ログで埋めない

    def handle_one_request(self) -> None:
        """**相手が先に切った接続を、異常として扱わない。**

        画面の移動・再読み込み・「取りに行っています」の最中の離脱では、こちらが応答を
        書き終える前にブラウザが接続を閉じる。これは正常な出来事であって、直す対象では
        ない ── 黙ってその接続だけ捨てる。
        """
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True

    # ---- 応答の下請け ------------------------------------------------------
    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")   # トークンは起動ごとに変わる
            # **URL にトークンが乗っている（`?t=…`）ので、外部リンクを踏んだ先に
            # Referer で漏れてはいけない**（`rate_performances.py` と同じ守り）。
            # 起動ごとの乱数トークンは「同じ端末の別プロセス（他のタブで開いた外部
            # サイトを含む）」からの要求を防ぐためのものなので、Referer で外部サイトに
            # 渡ってしまうと、その守りの片方が崩れる。
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # 相手がもう聞いていない。**書き込みは済んでいるので、失敗として扱わない**
            self.close_connection = True

    def _json(self, code: int, obj: dict) -> None:
        """JSON で返す。**HTML の断片が混ざっていても、鍵は埋めてから返す。**

        起案者の指摘（2026-08-25）──「『興味ありなし』を押した後、新しく出てくる公演の
        ポスターが画像表示エラーのようになってしまっている」。

        **原因は「読み込み中」ではなく、送っていなかったことである。** 全画面の GET は
        配る直前に `__TAGURI_TOKEN__` を本物の鍵に差し替えるが（`do_GET` 末尾）、
        この関数はそれを通らない。`fill_slot` が返す 1 枚（`RR.card`）にはポスターの
        `src="/img/…?t=__TAGURI_TOKEN__"` が生の文字列のまま入っており、画面に挿した
        瞬間にブラウザがその URL を読みに行って**鍵が合わずに 403 で弾かれていた**
        ── 遅いのではなく、最初から当たらない道を読みに行っていた。

        **直す場所は、断片を作る側ではなく配る側にする。** `fill_slot` のように
        `RR.card()` を呼ぶ場所が増えるたびに置き換えを書き足すのは漏れやすい。
        JSON を返す口をすべて通るここで 1 度だけ置き換えれば、**新しく HTML 断片を
        JSON に混ぜる操作を足しても、この手当てを覚えておく必要が無い。**
        """
        body = json.dumps(obj, ensure_ascii=False).replace(
            "__TAGURI_TOKEN__", self.server.token)                  # type: ignore[attr-defined]
        self._send(code, body.encode(), "application/json")

    def _tok(self, query: str) -> bool:
        if self.server.demo_mode:                                  # type: ignore[attr-defined]
            return True   # デモは公開URLだけで誰でも入れる前提（#000008）
        got = urllib.parse.parse_qs(query).get("t", [""])[0]
        return secrets.compare_digest(got, self.server.token)      # type: ignore[attr-defined]

    # ---- #000008: 復旧コード認証の下請け -----------------------------------
    def _session_user_id(self) -> str | None:
        """CookieヘッダからCookie経由の日常鍵を読み、利用者IDに解決する。"""
        jar = http.cookies.SimpleCookie()
        jar.load(self.headers.get("Cookie", ""))
        morsel = jar.get(SESSION_COOKIE)
        if morsel is None:
            return None
        return AU.resolve_session(morsel.value)

    def _set_session_cookie(self, token: str) -> dict:
        """Set-Cookieヘッダを組み立てる。`_send`のextraにそのまま渡す形。

        HttpOnly・SameSite=Lax（C15の下地）。HTTPS化（E1）が済むまでは
        Secure属性を付けない ── 平文HTTPの現状で付けるとCookie自体が
        機能しなくなる。E1実装時にSecureを足す。
        """
        return {"Set-Cookie": f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; "
                               f"Max-Age={AU.SESSION_TTL_SEC}"}

    def _auth_page(self, body: str) -> bytes:
        return (
            "<!doctype html><html lang=ja><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>たぐり</title>"
            "<style>body{font-family:sans-serif;max-width:32em;margin:2em auto;"
            "padding:0 1em;line-height:1.6}code{font-size:1.2em;background:#f0f0f0;"
            "padding:.5em;display:block;word-break:break-all}"
            ".warn{color:#a00;font-weight:bold}</style></head><body>" + body + "</body></html>"
        ).encode()

    # ---- GET は列挙した道だけ（画面 9 つ・持ち出し 1 つ・読み口 2 つ）--------
    def do_GET(self) -> None:                                      # noqa: N802
        path, _, query = self.path.partition("?")
        srv = self.server                                          # type: ignore[assignment]
        # **`_watchdog`向けに、どの道であれ最初に触られたらここで印を付ける。**
        # 以前は`_tok`を通った後でしか付かず、#000008で追加した新しい道
        # （`/auth/start`等）だけを使う利用者では一度も付かないまま
        # `GRACE_SEC`で落ちる余地があった。
        srv.opened = True

        # **#000008の新しい道はここで先に受ける。** 既存のPAGES一覧・起動ごと
        # トークン（`_tok`）より前 ── これらは「まだ鍵を持っていない人」が
        # 最初に触る道なので、既存の鍵を要求できない。
        if path == "/auth/start":
            user_id = self._session_user_id()
            if user_id is not None:
                body = ("<h1>この端末は認識されています</h1>"
                        f"<p>利用者ID: <code>{h_esc(user_id[:12])}…</code></p>"
                        "<p><a href='/link'>この端末を追加（別の端末で使う）</a></p>")
                self._send(200, self._auth_page(body), "text/html; charset=utf-8")
                return
            try:
                AU.throttle_register(self.client_address[0])
            except AU.AuthError as e:
                self._send(429, self._auth_page(f"<p class=warn>{h_esc(str(e))}</p>"),
                           "text/html; charset=utf-8")
                return
            code = AU.generate_recovery_code()
            new_user_id, _ = AU.access_or_register(code)
            token = AU.create_session(new_user_id)
            # **登録直後の一歩目（#000008・2026-08-29）。** 観劇記録・評価は
            # これから積み上がるものなので、統計的な推薦（網B/C）はまだ空である。
            # **お気に入り（網A）だけは、登録した瞬間から件数に関係なく動く**
            # （`page_recommend`の0件時表示を参照）。「はじめての一歩」を
            # 評価ではなくここに置くのは、必ず何かが出る経路だから。
            body = ("<h1 class=warn>この復旧コードは今だけ表示されます</h1>"
                     "<p>端末を失ったとき、これが無いと記録には二度と戻れません。"
                     "安全な場所に控えてください。</p>"
                     f"<code>{h_esc(code)}</code>"
                     "<p>控えたら、このページを閉じて構いません。</p>"
                     "<hr>"
                     "<h2>まず、好きな劇団・俳優を登録してみませんか</h2>"
                     "<p>観た記録が無くても、登録した名前の公演はすぐに一覧へ出ます。"
                     f"<a href='/recommend/favourites?t={self.server.token}'>"
                     "好きな劇団・俳優を登録する</a></p>")
            self._send(200, self._auth_page(body), "text/html; charset=utf-8",
                       self._set_session_cookie(token))
            return
        if path == "/recover":
            body = ("<h1>復旧コードで戻る</h1>"
                     "<form method=post action=/api/recover>"
                     "<input name=code placeholder='xxxx-xxxx-...' style='width:100%;"
                     "font-size:1.1em;padding:.5em'>"
                     "<button type=submit style='margin-top:1em'>戻る</button></form>")
            self._send(200, self._auth_page(body), "text/html; charset=utf-8")
            return
        if path == "/link":
            body = ("<h1>この端末を追加</h1>"
                     "<p>すでに使っている端末で発行した連携コードを入力してください。</p>"
                     "<form method=post action=/api/link/redeem>"
                     "<input name=code placeholder='6桁のコード' style='width:100%;"
                     "font-size:1.1em;padding:.5em'>"
                     "<button type=submit style='margin-top:1em'>追加</button></form>")
            self._send(200, self._auth_page(body), "text/html; charset=utf-8")
            return

        PAGES = ("/", "/start", "/recommend", "/recommend/reminder", "/recommend/interest",
                 "/recommend/favourites", "/calendar", "/tickets", "/rate", "/register",
                 "/records", "/records/trace",
                 "/records/chronicle", "/records/works", "/rate/unrated", "/rate/notes",
                 "/search", "/settings")
        # **`/export` は道として無くした**（起案者の指示・2026-08-26 で「設定」の中の
        # 1 枚の札に移した）。この道を打っても、他の未知の道と同じく 404 になる。
        # `/export.json`（持ち出しの実体）と `/data.zip`（別の端末に移す道具の実体）は
        # 画面ではないので、この一覧には乗らない ── 下の読み口の並びに入れる
        if path not in PAGES and path not in ("/export.json", "/data.zip",
                                              "/api/import_status",
                                              "/api/mail_hints", "/api/suggest",
                                              "/api/suggest_web", "/vendor/d3.js") \
                and not path.startswith("/img/"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        if not self._tok(query):
            self._send(403, b"token mismatch", "text/plain; charset=utf-8")
            return
        srv.opened = True
        if path.startswith("/img/"):
            # **名前は取り込み済みの一覧と突き合わせる。** パスをそのまま繋ぐと
            # `..` で端末内の任意のファイルを読ませることになる
            name = urllib.parse.unquote(path[5:])
            import posters as PO
            if name not in set(PO.have().values()):
                self._send(404, b"no image", "text/plain; charset=utf-8")
                return
            data = (IMG / name).read_bytes()
            self._send(200, data, "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "image/png")
            return
        if path == "/vendor/d3.js":
            # **同梱した描画ライブラリを、この 1 本だけ名指しで配る。**
            # 「作り手の再会」タイムラインが時間軸の拡大・縮小に使う（`timeline.py`）。
            #
            # **CDN からは読まない。** この画面は「外には何も出していません」と書いており、
            # 外から読むとその記述が嘘になる。出どころと版は `vendor/README.md` にある。
            #
            # **置き場所ごと配らない。** ディレクトリを配ると `ratings.db` を読ませる道が
            # できるので、**このパスだけを通す**（上の一覧にも名指しで入れてある）。
            f = ROOT / "tools" / "taguri" / "vendor" / "d3.v7.min.js"
            if not f.exists():
                self._send(404, b"no d3", "text/plain; charset=utf-8")
                return
            # **版は固定なので長く持たせてよい。** 図を開くたびに 280KB を配り直さない
            self._send(200, f.read_bytes(), "text/javascript; charset=utf-8",
                       {"Cache-Control": "max-age=86400"})
            return
        if path == "/api/import_status":
            self._json(200, srv.import_status())
            return
        if path == "/api/suggest":
            # **手で足す欄の候補。** 手元にあるものだけを引く読み口で、外へは行かない
            # （守り 5）。**打っている最中に走る**ので、外へ行く口と分けてある
            q = urllib.parse.parse_qs(query).get("q", [""])[0]
            self._json(200, APP.suggest(q[:120]))
            return
        if path == "/api/suggest_web":
            # **手で足す欄の「検索」。** ここだけは外の公演情報を見に行く
            # （起案者の指示・2026-08-24）。**押されたときにしか走らない** ので、
            # 打つたびに外へ行くことはない。**書き込みはしない**（読み口のまま）。
            #
            # **待つ時間の上限は取得の側が決めている** ── 1 つの相手には 1.1 秒に 1 回、
            # 1 回の検索で最大 8 要求なので 8 秒ほどである
            q = urllib.parse.parse_qs(query).get("q", [""])[0]
            self._json(200, APP.search_web(q[:120]))
            return
        if path == "/api/mail_hints":
            # **直すための手がかりだけを返す読み口である。** 本文そのものは渡さないし、
            # どこにも保存しない（企画書 2 章）── 端末内のファイルをその場で読むだけ
            uid = urllib.parse.parse_qs(query).get("uid", [""])[0]
            if not re.fullmatch(r"\d{1,12}", uid):
                self._json(400, {"error": "uid"})
                return
            self._json(200, APP.mail_hints(uid))
            return
        if path == "/export.json":
            # **持ち出しはそのまま渡す。** トークンの置き換えはしない（HTML ではない）
            body = json.dumps(APP.export_payload(), ensure_ascii=False, indent=1).encode()
            self._send(200, body, "application/json; charset=utf-8",
                       {"Content-Disposition": 'attachment; filename="taguri-export.json"'})
            return
        if path == "/data.zip":
            # **「別の端末に記録を移す」の実体。** `data/review` 配下（記録・取得物・
            # ポスター）を丸ごと 1 本の ZIP にして渡す ── LAN 越しには送らない
            # （企画書 5 章の守り 2）ので、運ぶのは本人の手段に委ねる（`app.py` の
            # `_data_copy_card_html` の説明）。**ダウンロードして向こうの
            # `data/review` に置き換えれば、そのまま `run.py` が動く形で渡す。**
            base = ROOT / "data" / "review"
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for f in base.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(base))
            self._send(200, buf.getvalue(), "application/zip",
                       {"Content-Disposition": 'attachment; filename="taguri-data.zip"'})
            return
        try:
            if path == "/start" or (path == "/" and APP.is_fresh()):
                # **何も入っていないときは、入口を「はじめる」に差し替える。**
                # ふだんの一覧を出しても 0 件の枠が並ぶだけで、**次に何をすれば
                # よいかがどこにも書かれていない**（`app.page_start` の説明）
                html = APP.page_start()
            elif path in ("/", "/recommend"):
                # **絞り込みは、この起動のあいだ覚えておく。** 記録を見返す画面へ移って
                # 戻ってきたときに全国へ戻ると、選び直しが要る。**この起動が始まった
                # ときの既定は設定画面で決めた都道府県**（`self.prefs` の初期値）で、
                # ここで一時的に別の県へ変えても、次の起動では設定の既定に戻る
                # （2026-08-26 に撤回 ── 以前は「保存はしない・既定は全国」だった）
                q = urllib.parse.parse_qs(query)
                if "f" in q:                       # 絞り込みの form から来た要求だけが変える
                    srv.prefs = [p for p in q.get("pref", []) if p][:47]
                html = APP.page_recommend(srv.prefs)
                # **出した束の名前で印を付ける。** 絞り込んでいるときに出しているのは
                # 全国の 15 件ではないので、`recommend` と混ぜない
                srv.mark_viewed("recommend_pref" if srv.prefs else "recommend")
            elif path == "/recommend/reminder":
                # **絞り込みは `/recommend` と同じ `srv.prefs` を使う**（起案者の指示・
                # 2026-08-26 ──「開幕リマインドも選んだ都道府県だけに絞って」）。
                # 別に持つと、「おすすめ」で選んだ県と「開幕リマインド」で選んだ県が
                # 食い違い、どちらが今の絞り込みか分からなくなる
                q = urllib.parse.parse_qs(query)
                if "f" in q:
                    srv.prefs = [p for p in q.get("pref", []) if p][:47]
                # **週の切り替えは月の絞り込みと同じ規約 ── URL だけで持つ。**
                w = q.get("w", ["this"])[0]
                html = APP.page_reminder(srv.prefs, w if w in ("this", "next") else "this")
            elif path == "/recommend/interest":
                # **月の絞り込みは URL だけで持つ。** 都道府県（`srv.prefs`）のように
                # 起動のあいだ覚える必要が無い ── 札は素のリンクなので、押した先の
                # URL がそのまま「いまどの月を見ているか」である
                html = APP.page_interest(_month(query), _page(query))
            elif path == "/recommend/favourites":
                html = APP.page_favourites(_month(query), _page(query))
                srv.mark_viewed("favourite")
            elif path == "/calendar":
                # **束・都道府県の絞り込みは URL だけで持つ**（月の札と同じ判断）── 押した
                # 先の URL がそのまま絞り込みの内容である。起動のあいだ覚える必要は無い
                # （都道府県の絞り込みと違い、他画面へ移ってまた戻ってくる作りではない）。
                q = urllib.parse.parse_qs(query)
                kinds = ({k for k in q.get("kind", []) if k in SC.KIND_KEYS} or None)
                prefs = ({p for p in q.get("pref", []) if p in RR.PREFS} or None)
                html = APP.page_calendar(kinds, prefs)
            elif path == "/tickets":
                html = APP.page_tickets()
            elif path == "/rate":
                # **どの束を見ているかは URL だけで持つ**（月の札と同じ判断）── 札は
                # 素のリンクなので、押した先の URL がそのまま現在地である
                q = urllib.parse.parse_qs(query)
                v = q.get("v", [""])[0]
                y = q.get("y", [""])[0]
                venues = q.get("venue", [])
                html = APP.page_rate(v, y, venues, _page(query))
            elif path == "/rate/unrated":
                html = APP.page_unrated()
            elif path == "/rate/notes":
                html = APP.page_notes()
            elif path == "/register":
                html = APP.page_register(srv.imp, srv.imported)
            elif path == "/records":
                html = APP.page_records()
            elif path == "/records/trace":
                # **どの名前をたどっているか・どこから来たかは URL だけで持つ**
                # （日記帳の年の耳・評価の耳と同じ判断）
                q = urllib.parse.parse_qs(query)
                html = APP.page_trace(q.get("name", [""])[0], q.get("via", [""])[0])
            elif path == "/records/chronicle":
                html = APP.page_chronicle()
            elif path == "/records/works":
                # **どの年を開いているか・作品ごとか観た回ごとかは URL だけで持つ**
                # （評価の耳と同じ判断）。`g` を読み忘れると、耳を押しても
                # `page_works` には既定の "work" しか渡らず、切り替えたのに
                # 元に戻って見える（押しても効かないのと区別が付かない）
                q = urllib.parse.parse_qs(query)
                y = q.get("y", [""])[0]
                g = q.get("g", ["work"])[0]
                html = APP.page_works(y, _page(query), q.get("w", [""])[0], g)
            elif path == "/search":
                q = urllib.parse.parse_qs(query).get("q", [""])[0]
                # **暦から選んだ月も受け取る。** 形の合わないものは選ばれていない扱い
                ym = urllib.parse.parse_qs(query).get("ym", [""])[0]
                ym = ym if ym == "none" or re.fullmatch(r"20\d\d-\d{2}", ym or "") else ""
                # **外へ探しに行くのは、押したときだけ**（`web=1` はその押し口である）
                web = urllib.parse.parse_qs(query).get("web", [""])[0] == "1"
                # **暦のどちら側を見ているか。** 既定は観た記録
                cal = urllib.parse.parse_qs(query).get("cal", [""])[0]
                html = APP.page_search(q, ym, web, "up" if cal == "up" else "past")
            elif path == "/settings":
                html = APP.page_settings()
            else:
                # **ここには来ない。** 上の `PAGES` に列挙した道はすべて明示の分岐で
                # 受けている ── 食い違いが起きたら、page_export に逃がさず黙って 404 にする
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
        except Exception as e:                                      # noqa: BLE001
            # **画面が組めなかったことを黙って 500 にしない。** 何が足りないのかを画面に出す
            import traceback
            self._send(500, ("<h1>画面が組めなかった</h1><pre>"
                             + traceback.format_exc() + "</pre>").encode(),
                       "text/html; charset=utf-8")
            return
        self._send(200, html.replace("__TAGURI_TOKEN__", srv.token).encode(),
                   "text/html; charset=utf-8")

    # ---- POST は列挙した操作だけ -----------------------------------------
    def _read_form_or_json(self) -> dict:
        """`code`のような1項目だけの投稿を、フォームでもJSONでも受け取る。"""
        n = min(int(self.headers.get("Content-Length") or 0), 8192)
        raw = self.rfile.read(n)
        ctype = self.headers.get("Content-Type", "")
        if "application/json" in ctype:
            try:
                return json.loads(raw or b"{}")
            except ValueError:
                return {}
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode("utf-8", "replace")).items()}

    def do_POST(self) -> None:                                     # noqa: N802
        srv = self.server                                          # type: ignore[assignment]

        # **#000008の新しい道は、既存の起動ごとトークンより前に受ける。**
        # `/api/recover`・`/api/link/redeem`は「まだ鍵を持っていない人」が
        # 使う道なので、既存の鍵を要求できない。`/api/link/create`だけは
        # すでに認識されている端末からの発行なので、新しいCookieの鍵で守る。
        if self.path == "/api/recover":
            body = self._read_form_or_json()
            try:
                user_id = AU.recover(body.get("code", ""), ip=self.client_address[0])
            except AU.AuthError as e:
                self._send(400, self._auth_page(f"<p class=warn>{h_esc(str(e))}</p>"
                                                 "<p><a href='/recover'>戻る</a></p>"),
                           "text/html; charset=utf-8")
                return
            token = AU.create_session(user_id)
            self._send(200, self._auth_page("<h1>戻れました</h1><p><a href='/auth/start'>続ける"
                                             "</a></p>"),
                       "text/html; charset=utf-8", self._set_session_cookie(token))
            return
        if self.path == "/api/link/redeem":
            body = self._read_form_or_json()
            try:
                user_id = AU.redeem_link_code(body.get("code", ""), ip=self.client_address[0])
            except AU.AuthError as e:
                self._send(400, self._auth_page(f"<p class=warn>{h_esc(str(e))}</p>"
                                                 "<p><a href='/link'>戻る</a></p>"),
                           "text/html; charset=utf-8")
                return
            token = AU.create_session(user_id)
            self._send(200, self._auth_page("<h1>追加できました</h1><p><a href='/auth/start'>"
                                             "続ける</a></p>"),
                       "text/html; charset=utf-8", self._set_session_cookie(token))
            return
        if self.path == "/api/link/create":
            user_id = self._session_user_id()
            if user_id is None:
                self._json(403, {"error": "no session"})
                return
            code = AU.create_link_code(user_id)
            self._json(200, {"code": code, "expires_in_sec": AU.LINK_TTL_SEC})
            return

        if not srv.demo_mode and not secrets.compare_digest(
                self.headers.get("X-Taguri-Token", ""), srv.token):
            self._json(403, {"error": "token"})
            return
        op = self.path
        srv.opened = True
        if op == "/api/close":
            if srv.demo_mode:
                # **デモでは、不特定多数の誰でもここに来られる。** 1人がこれを
                # 押すと全員のデモが止まってしまうため、デモモードでは常に拒否する
                # （#000008）。
                self._json(403, {"error": "disabled in demo mode"})
                return
            self._json(200, {"ok": True})
            threading.Thread(target=srv.shutdown, daemon=True).start()
            return
        # **本文の上限は 8KB のままにする。** どの操作も送るのは短い JSON である。
        # **ポスターだけは例外である** ── 画像そのものを渡すので桁が違う
        # （中身は `app.save_hand_poster` が 12MB で切る。base64 は約 1.34 倍になり、
        # ここはその手前の枠なので余裕を持たせてある）
        cap = 24 * 1024 * 1024 if op == "/api/hand_poster" else 8192
        n = min(int(self.headers.get("Content-Length") or 0), cap)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            self._json(400, {"error": "json"})
            return
        fn = {"/api/react": srv.on_react, "/api/rate": srv.on_rate,
              "/api/note": srv.on_note, "/api/favourite": srv.on_favourite,
              "/api/missed": srv.on_missed, "/api/add_work": srv.on_add_work,
              "/api/import_mail": srv.on_import_mail,
              "/api/fix_work": srv.on_fix_work,
              "/api/merge_work": srv.on_merge_work,
              "/api/drop_work": srv.on_drop_work,
              "/api/restore_work": srv.on_restore_work,
              "/api/purge_work": srv.on_purge_work,
              "/api/unseen": srv.on_unseen,
              "/api/ticket": srv.on_ticket,
              "/api/chronicle": srv.on_chronicle,
              "/api/people_read": srv.on_people_read,
              "/api/weight": srv.on_weight,
              "/api/pref_setting": srv.on_pref_setting,
              "/api/hand_credits": srv.on_hand_credits,
              "/api/hand_poster": srv.on_hand_poster,
              "/api/link_stage": srv.on_link_stage,
              "/api/hand_theme": srv.on_hand_theme,
              "/api/hand_theme_refresh": srv.on_hand_theme_refresh,
              "/api/decline": srv.on_decline,
              "/api/visit_note": srv.on_visit_note}.get(op)
        if not fn:
            self._json(404, {"error": "unknown op"})
            return
        try:
            self._json(200, fn(body))
        except ValueError as e:
            self._json(400, {"error": str(e)})


def _month(query: str) -> str:
    """URL から月を読む。**形の合わないものは既定（近い順）に落とす。**

    `2026-09` か `none` だけを通す ── 画面が受け取る値は、外から来る文字列である。
    """
    m = urllib.parse.parse_qs(query).get("m", [""])[0]
    return m if m == "none" or re.fullmatch(r"20\d\d-\d{2}", m or "") else ""


def _page(query: str) -> int:
    """URL から何ページ目かを読む。**数字でなければ 1 ページ目に落とす。**"""
    v = urllib.parse.parse_qs(query).get("p", ["1"])[0]
    return int(v) if re.fullmatch(r"\d{1,3}", v or "") else 1


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        """**接続が切れただけのものは黙って捨てる。**

        既定の実装は traceback を標準エラーに書く。画面を移動するたびに
        `BrokenPipeError` の山が進捗表示に混ざり、本当の失敗が読めなくなっていた。
        **切断以外は今までどおり出す** ── 握り潰すのは相手都合の切断だけである。
        """
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError,
                                          ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)

    def __init__(self, label: str, port: int, *, bind_host: str = "127.0.0.1",
                demo_mode: bool = False) -> None:
        # **既定は`127.0.0.1`に固定する。** ここを`0.0.0.0`にすると同じLANの他端末
        # から観劇記録が読める。**`bind_host`を明示的に変えられるのは、就活デモを
        # Render等のクラウドで動かす`serve_cloud.py`だけ**（#000008・2026-08-29）。
        # ローカル・EC2での`run.py`経由の起動は、今までどおり引数を渡さないので
        # 挙動は変わらない。
        super().__init__((bind_host, port), Handler)
        self.label = label
        self.token = secrets.token_urlsafe(24)
        # **デモモード。** 起動ごとの合言葉（`_tok`・`X-Taguri-Token`）は、就活の
        # リクルーターが知りようがない秘密なので、デモ環境ではこの2つの検査を
        # 迂回する。既存のセキュリティは働かなくなるが、それは想定内 ──
        # デモ用の共有データセットしか置かない前提であり、個人の観劇記録は乗らない
        # （#000008「就活向けデモ公開への方針転換」）。`/api/close`だけは、
        # 迂回すると不特定多数がデモを止められてしまうため、デモモードでは
        # 常に拒否する。
        self.demo_mode = demo_mode
        # **書き込みは 1 本の接続を錠で直列化する。** 要求は別スレッドで来る
        self.con = FB.connect(same_thread=False)
        self.con.executescript(MISSED_SCHEMA)
        self.con.commit()
        _migrate_missed(self.con)
        self.lock = threading.Lock()
        self.n = {"react": 0, "rate": 0, "note": 0, "fav": 0, "missed": 0,
                  "add": 0, "import": 0, "fix": 0}
        # **最初の接続が来るまでは落ちない**（`_watchdog`）
        self.started = time.monotonic()
        self.opened = False
        self.imp = {"running": False, "line": ""}
        # **今回の取り込みで入った公演の題名。`imp` とは別に持つ。**
        # `imp` は押した操作のたびに丸ごと書き換わる場所（お気に入りの登録・公演の追加
        # でも使う）なので、そこに入れると**取り込みのあとに 1 つ何かを押しただけで
        # 題名が消える。** 取り込みの結果は次の取り込みまで残るものである
        self.imported: list[str] = []
        # **押した直後に取りに行く仕事の列**（起案者の指示・2026-08-24 ──「データベース
        # から公演を拾ってくるのは月 1 でいいけど、それ以外はできるだけ即時更新に」）。
        # **1 本の worker で順に走らせる。** 同時に走らせると 1 リクエスト／秒の約束が
        # 守れない ── 取得の間隔を 1 か所で守るのが企画書 5 章の守りの中身である
        self.jobs: queue.Queue = queue.Queue()
        threading.Thread(target=self._jobs, daemon=True).start()
        # **絞り込んだ都道府県。** 起動のたびに、設定画面で決めた既定から始める
        # （起案者の指示・2026-08-26 ── 一括の設定画面。「保存はしない・既定は全国」
        # という以前の判断を撤回する）。この起動のあいだ「観に行ける場所で絞り込む」で
        # 一時的に変えることはできるが、**次の起動ではまた設定の既定に戻る**。
        self.prefs: list[str] = APP.read_pref_setting()
        APP.RECORD = self.record_presented
        # **デモモードでは監視しない。** クラウドの公開デモは「誰かがブラウザを
        # 開くまでの一時プロセス」ではなく、常時稼働のWebサービスとして動かす
        # 前提なので、`GRACE_SEC`で自動終了させると事故る。
        if not self.demo_mode:
            threading.Thread(target=self._watchdog, daemon=True).start()

    def record_presented(self, rows: list, prefs: list,
                         bundle: str = "recommend_pref", start: int = 1) -> None:
        """**絞り込んで出した一覧を、出した記録として残す。**

        **残さないと抑制が壊れる。** 反応は stage_id で保存するが、同じ作品のツアーは
        会場ごとに別の stage_id を持つため、作品単位に畳み直さないと外した公演が別会場として
        戻ってくる（検証 026）。畳み直しは `presented` の題名を引いて行うので、
        **提示の記録が無い公演への「興味なし」は、翌週その作品を全国の枠へ戻す。**

        **全国の上位 15 件とは別の束にする**（`bundle='recommend_pref'`）── 週次の指標の
        分母は「その週に全国で出した 15 件」なので、混ぜると分母が動く。
        **どの都道府県で絞ったかも残す** ── 後から「絞り込んだときの当たり方」を数えられる。
        **同じ公演を 2 度書かない**（`INSERT OR IGNORE`）。順位は最初に出したときのものが残る。

        **束の名前は呼ぶ側が決める。** 絞り込んで出した分（`recommend_pref`）と、三択を
        押した枠を埋めた分（`recommend_fill`）を分けるためである ── どちらも
        「その週に全国で出した 15 件」ではないので、`recommend` に混ぜると分母が動く。
        """
        with self.lock:
            for i, c in enumerate(rows, start):
                self.con.execute(
                    "INSERT OR IGNORE INTO presented"
                    " (label, stage_id, rank, title, score, bundle, reasons, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (self.label, str(c.get("stage_id") or ""), i, c.get("title") or "",
                     float(c.get("total") or 0), bundle,
                     json.dumps({"b": c.get("why_b") or [], "a": c.get("a") or [],
                                 "c": c.get("why_c") or [], "theme": c.get("theme") or [],
                                 "pref_filter": list(prefs)}, ensure_ascii=False),
                     FB.now()))
            self.con.commit()

    def mark_viewed(self, bundle: str) -> None:
        """**この起動の一覧を、画面に出したことを記録する。**

        起案者の指示（2026-08-24）── 提示の記録に、開発中に計算しただけで誰も見ていない
        一覧が混ざっていた（8/24 だけで 37 回・555 行）。**効果の連鎖の分母はこの表で
        決まる**ので、見ていない一覧を数えると興味あり率がその分だけ薄まる。

        **`presented` に書く場所は動かさない。** あの表は「その週にどの順で出す計算に
        なったか」の記録で、計算のたびに残す意味がある（順位の再現・網ごとの理由）。
        **足りなかったのは「実際に出したか」だけ**なので、そこだけを別の表に足す。

        **2 度目は何もしない**（`INSERT OR IGNORE`）。同じ一覧を何度開いても提示は 1 回で、
        画面を行き来した回数は分母ではない。
        """
        with self.lock:
            FB.mark_viewed(self.con, self.label, bundle, "screen")
            self.con.commit()

    # ---- 押した直後に取りに行く -------------------------------------------
    def enqueue(self, label: str, fn) -> None:
        """仕事を列に足す。**押した瞬間に「取りに行っています」を出す。**

        返事を待たせない ── 外への要求は 1 リクエスト／秒なので、押した本人を
        その場で止めると操作が止まる。**画面は `/api/import_status` に聞きに来る。**
        """
        self.imp = {"running": True, "line": label}
        self.jobs.put((label, fn))

    def _jobs(self) -> None:
        """列に入った仕事を、1 つずつ順に走らせる。

        **失敗しても止めない。** 外の都合（相手のサーバ・認証・回線）で失敗するものを
        並べる場所なので、1 件の失敗で以後の仕事が走らなくなってはいけない。
        """
        while True:
            label, fn = self.jobs.get()
            self.imp = {"running": True, "line": label}
            try:
                line = fn() or "終わった"
            except Exception as e:                                  # noqa: BLE001
                line = f"できなかった: {e}"
            self.imp = {"running": False, "line": str(line)[:200]}
            # **取ってきた分を、次に開く画面へ効かせる。** 索引は起動のあいだ作り直さない
            # ので、捨てておかないと探す画面にだけ古い手元が出る
            try:
                APP.reset_caches()
            except Exception:                                       # noqa: BLE001
                pass

    def _sh(self, args: list, done: str) -> str:
        """更新の段の道具を 1 つ走らせる。**画面に出す 1 行を返す。**"""
        import subprocess
        pr = subprocess.run([sys.executable] + args, cwd=ROOT,
                            capture_output=True, text=True, timeout=1800)
        if pr.returncode != 0:
            tail = ((pr.stderr or "").strip().splitlines() or [""])[-1]
            return f"できなかった（{pr.returncode}）: {tail[:150]}"
        return done

    def _watchdog(self) -> None:
        """**ブラウザが一度も開かなかったときだけ、プロセスを落とす。**

        画面を閉じたら自動で終了する仕組み（`pagehide`、続けて心拍）は撤回した
        （起案者の指示・2026-08-27）。**「記録を見返す」のような画面は長時間開いた
        ままにする使い方を想定しており、タブを裏に回しただけで自動終了してはいけない。**
        閉じるのは「終わる」ボタン（`/api/close`）と `Ctrl-C` に一本化した。
        ここで見るのは別の話 ── `webbrowser.open` が失敗するなどしてブラウザが
        一度も開かれなかった場合に、待ち受けが残り続けるのを防ぐことだけである。
        """
        time.sleep(GRACE_SEC)
        if self.opened:
            return
        print("\n  誰も開かなかったので落ちる")
        threading.Thread(target=self.shutdown, daemon=True).start()

    def import_status(self) -> dict:
        return dict(self.imp)

    # ---- 1 三択の反応 ------------------------------------------------------
    def on_react(self, b: dict) -> dict:
        """三択と、**「興味あり」「興味なし」に添える任意の理由。**

        **理由だけを送れるようにしてある** ── 押した後に書くので、三択と同時には来ない。
        `value` を渡さない要求は理由の更新として扱う（`FB.react` は渡さなかった列を消さない）。

        **興味ありの理由（`note`）と見送った理由（`note_no`）は別の列に入れる。**
        `note` からは名前を拾って「お気に入り」への昇格候補を作るので
        （`tools/taguri/reasons.py`）、**同じ列に入れると「これが出ているから観たくない」と
        書いた名前が登録候補として出てくる。**
        """
        stage_id, value = str(b.get("stage_id") or ""), str(b.get("value") or "")
        notes = {k: (str(b[k])[:2000] if b.get(k) is not None else None)
                 for k in ("note", "note_no")}
        given = {k: v for k, v in notes.items() if v is not None}
        if not stage_id or (value not in REACT and not given):
            raise ValueError("stage_id と、value（owned / interest / nointerest）か理由が要る")
        kw = dict(REACT.get(value) or {})
        kw.update(given)
        with self.lock:
            # **押し直しで前の列を消さない。** 興味あり → 持っている、という遷移そのものが
            # 連鎖（提示 → 興味あり → 購入 → ◎）の記録である
            FB.react(self.con, self.label, stage_id, source="screen", **kw)
            # **同じ作品の他会場にも同じ答えを付ける**（起案者の指摘・2026-08-26 ──
            # 「作品自体に『興味あり』を押しているのだから、代表会場にしか効かないのは
            # おかしい。興味ありなしは会場に関わらず親データの作品データに付与される
            # 形である必要がある」）。
            #
            # **理由の文（`given`）は複製しない。** 押した 1 枚にだけ残す ──
            # 「なぜ気になったか」を書いた場所が会場の数だけ増えると、どれが本人の
            # 言葉か分からなくなる。複製するのは三択の答えだけである。
            #
            # **出どころは `screen_tour` にする。** 押した本人の 1 行（`screen`）と
            # 混ぜて数えると、1 回の押しがツアーの会場数ぶんに水増しされる
            # （`feedback.report` の「回答」「興味あり」は `screen_tour` を数えない）。
            if value:
                react_kw = dict(REACT.get(value) or {})
                for sid in self._siblings(stage_id):
                    FB.react(self.con, self.label, sid, source="screen_tour", **react_kw)
            self.n["react"] += 1
        # **手元の候補に無い公演なら、控えに加える**（起案者の指摘・2026-08-24）。
        # **反応は公演の id に保存されるが、一覧は候補の控えから組む** ── 探して見つけた
        # 公演に「興味あり」を押しても、控えに無ければ**押した記録は残るのにどの一覧にも
        # 出てこない。** 押した本人からは消えたように見える
        if value:
            self._pick(stage_id)
        out = {"ok": True, "stage_id": stage_id, "value": value,
               "note": "note" in given, "note_no": "note_no" in given}
        # **三択に答えた枠を、次の候補で埋める**（起案者の指示・2026-08-24）。
        # 理由だけの更新では埋めない ── 枠が空いていないので足す先が無い
        if value:
            out["fill"] = self.fill_slot(
                [str(x)[:20] for x in (b.get("shown") or [])][:120], stage_id)
        return out

    def fill_slot(self, shown: list, pressed: str) -> dict:
        """三択を押した 1 枚の代わりに出す候補を 1 件返す。**在庫が無ければ `html` は空。**

        起案者の指示（2026-08-24）──「すでに持っている・興味あり・興味なしのボタンを
        押したら、まだ在庫があるなら別の候補に入れ替えて表示すべきだね」。

        **在庫は画面の側にしか無い。** 反応を書いたあとに `APP._load()` を呼び直すと、
        押した公演は推薦の枠から抜けている（`_rebucket`）ので、**残っている候補の
        いちばん上が次の 1 件**である。ただし**すでに画面に出ている 15 件は除く** ──
        除かないと、いま並んでいる 1 枚をもう 1 枚足すことになる。だから画面が
        「いま何を出しているか」を送ってくる。

        **作品単位の重複は起きない。** `ranked` は `recommend2.py` が作品ごとに
        1 会場へ畳んであるので、id を突き合わせれば別会場が二重に出ることはない。

        **絞り込みは引き継ぐ。** いま都道府県で絞って見ているなら、足す 1 件も
        その県で観られるものにする（`self.prefs`）── 絞り込みの外から足すと、
        押しただけで絞り込みが破れる。
        """
        if not shown:
            return {"html": "", "left": 0, "said": ""}
        d, _ = APP._load()
        rows, _n = RR.filtered(d, self.prefs, 10 ** 6)
        seen = {str(x) for x in shown} | {str(pressed)}
        rest = [c for c in rows if str(c.get("stage_id") or "") not in seen]
        if not rest:
            return {"html": "", "left": 0,
                    "said": "記録しました。入れ替える候補はもうありません"
                            "（好みに合いそうだと判断できた分は出し切りました）。"}
        c = rest[0]
        # **耳の番号は「何枚目に出したか」にする。** 画面に並んでいる番号を振り直すと、
        # 読んでいる途中の 1 枚の番号が変わる。足した 1 枚に次の番号を与えれば、
        # 点の高い順という並びも番号の意味も壊れない
        rank = len(shown) + 1
        self.record_presented([c], list(self.prefs), "recommend_fill", rank)
        return {"html": RR.card(rank, c), "left": len(rest),
                "said": f"記録しました。入れ替わりに 1 件を下に足しました"
                        f"（まだ出していない候補が {len(rest) - 1} 件あります）。"}

    def _siblings(self, stage_id: str) -> list[str]:
        """同じ作品の、ツアーの他会場の stage_id を全部返す（自分は含めない）。

        起案者の指摘（2026-08-26）── 反応は会場ではなく作品に付くべきものなので、
        押した 1 枚の会場だけでなく、同じ作品の他の会場にも同じ答えを及ぼす。

        **`ranked` の中から探す。** `recommend2.py` が週の計算のときに、同じ作品の
        ツアー日程を代表 1 会場へ畳み、残りを `tours` に持たせている（企画書 2 章の
        「ツアーの他会場の日程」）。押した 1 枚が代表でも他会場でも、`ranked` を
        1 度舐めれば同じ組に行き当たる ── 都道府県で絞り込んだ画面では代表が
        入れ替わるので（`RR.filtered`）、決め打ちで「1 件目が代表」とは読めない。

        **見つからなければ空を返す。** 探して見つけた公演（ツアーの畳みを経ていない）や、
        週の計算が壊れているときに、この関数のせいで反応そのものが書けなくなってはいけない。
        """
        try:
            d, _ = APP._load()
        except Exception:                                            # noqa: BLE001
            return []
        for c in d.get("ranked") or []:
            ids = [str(c.get("stage_id") or "")] + [
                str(t.get("stage_id") or "") for t in (c.get("tours") or [])]
            if stage_id in ids:
                return [x for x in ids if x and x != stage_id]
        return []

    def _pick(self, stage_id: str) -> None:
        """探して見つけた公演を控えに加え、一覧を組み直す。**すでに手元にあれば何もしない。**"""
        import stage_search as SS
        sid = str(stage_id or "")
        if not sid.isdigit():
            return
        try:
            known = set(APP._upcoming_index()["rows"])
        except Exception:                                           # noqa: BLE001
            known = set()
        if sid in known:
            return
        today = datetime.date.today().isoformat()

        def work() -> str:
            r = SS.pick(sid)
            if not r.get("ok"):
                return f"控えに加えられませんでした（{r.get('why', '')[:40]}）"
            if not r.get("wrote"):
                return "もう手元にありました"
            # **一覧を組み直さないと、どの束にも入らない**（`--no-snapshot` は
            # `on_favourite` と同じ理由 ── 週次の指標の分母を動かさない）
            return self._sh(["tools/review/recommend2.py", "--today", today,
                             "--top", "15", "--no-snapshot"],
                            f"「{r.get('title', '')[:24]}」を手元に加えました"
                            " ── 画面を読み込み直してください")

        self.enqueue("この公演を手元に加えています…", work)

    # ---- 2 観たあとの ◎○△× ----------------------------------------------
    def on_chronicle(self, _b: dict) -> dict:
        """年表の文を作り直す（起案者の指示 2026-08-25）。

        **錠は取らない。** 1 分ほどかかる仕事なので、この間ほかの押し口まで止めると
        画面が固まる。**書く先は `chronicle.json` の 1 ファイルだけ**で、記録の DB には
        触らないので、ほかの操作とぶつからない。

        **押されたときだけ走らせる。** 週次の実行に挟むと「数秒で一覧が開く」性質が
        壊れる ── 画面の側には「記録が変わっています」と出しておき、作り直すかどうかは
        本人が決める。
        """
        import chronicle as CR
        r = CR.write(force=True)
        return {"ok": bool(r.get("ok")), "line": r.get("line") or ""}

    def on_people_read(self, _b: dict) -> dict:
        """「一緒に出てくる人の網」の読み（LLM の 1 段落）を作り直す（起案者の指示
        2026-08-27 ──「図から読み取れることを LLM で分析し、文章で記載して」）。

        **`on_chronicle` と同じ形。** 錠は取らず、書く先は `people_read.json` の
        1 ファイルだけなので、ほかの操作とぶつからない。押されたときだけ走らせる。
        """
        import people as PE
        r = PE.write(force=True)
        return {"ok": bool(r.get("ok")), "line": r.get("line") or ""}

    def on_ticket(self, b: dict) -> dict:
        """券の行く日を 1 枚足す・確定する・取り消す（起案者の指示 2026-08-25）。

        **一覧を組み直さない。** 足したのは「いつ行くか」であって、どの束に入るかでも
        順位でもない ── 暦の点が 1 つ増えるだけなので、画面の側で描き足せば足りる。
        """
        with self.lock:
            return APP.save_ticket(str(b.get("stage_id") or ""),
                                   str(b.get("date") or ""), str(b.get("time") or ""),
                                   action=str(b.get("action") or "add"))

    def on_rate(self, b: dict) -> dict:
        work_key, verdict = str(b.get("work_key") or ""), str(b.get("verdict") or "")
        if verdict not in VERDICTS:
            raise ValueError(f"verdict が候補にない: {verdict!r}")
        with self.lock:
            APP.save_work_field(work_key, verdict=verdict)
            self.n["rate"] += 1
        return {"ok": True, "work_key": work_key, "verdict": verdict}

    # ---- 3 感想の自由記述 --------------------------------------------------
    def on_note(self, b: dict) -> dict:
        """**感想は任意で、評価とは別に保存する。**

        書く本人にとっては分析用のデータではなく、残すためのものである（企画書 2 章）。
        **推薦の順位には使わない** ── 記録を見返す画面と理由の文面にだけ出す。
        """
        work_key = str(b.get("work_key") or "")
        note = str(b.get("note_impression") or "")[:4000]
        with self.lock:
            APP.save_work_field(work_key, note=note)
            self.n["note"] += 1
        return {"ok": True, "work_key": work_key, "len": len(note)}

    def on_visit_note(self, b: dict) -> dict:
        """**「すべて表示」だけに出す、回ごとのメモ。**（起案者の指示・2026-08-26）

        `on_note`（作品ごとの感想）とは保存先が別（`visit_note` 表・uid が鍵）。
        **推薦の計算はどこもこの表を読まない** ── 見出しの「推薦には使いません」の
        とおりにするための、いちばん確実な守り方は「そもそも読ませない」である。
        """
        uid = str(b.get("uid") or "")
        note = str(b.get("note") or "")[:4000]
        if not uid:
            raise ValueError("uid が要る")
        with self.lock:
            out = APP.save_visit_note(uid, note)
            self.n["visit_note"] = self.n.get("visit_note", 0) + 1
        return out

    # ---- 4 お気に入りの登録・解除 ------------------------------------------
    def on_favourite(self, b: dict) -> dict:
        """**履歴に無い名前も登録できる。** 名簿は「◎ を付けた公演の作り手」しか材料に
        持てないので、外で知った名前はここが唯一の入口である（企画書の中核）。"""
        action, kind = str(b.get("action") or ""), str(b.get("kind") or "")
        name = str(b.get("name") or "").strip()[:80]
        if action not in ("add", "remove") or kind not in RC.KINDS or not name:
            raise ValueError("action（add / remove）・kind・name が要る")
        with self.lock:
            d = RC.load_declared()
            cur = list(d.get(kind) or [])
            if action == "add":
                if name not in cur:
                    cur.append(name)
            else:
                cur = [x for x in cur if x != name]
            d[kind] = cur
            RC.save_declared(d)
            RC.DECLARED = RC.load_declared()      # 同じ起動の中で照合にも効かせる
            self.n["fav"] += 1
        # **登録した直後に、その名前で公演を引く**（起案者の指示・2026-08-24）。
        # これまでは「次の起動から新着に出る」と画面に書いていたが、**お気に入りは
        # 見逃したくないものなので、次の起動まで待たせる理由が無い。** 引くのは
        # 増えた 1 名ぶんだけである（`favourites.py` は名前ごとに結果を貯める）。
        # **解除のときは引かない** ── 外に用が無く、一覧を組み直すだけで消える
        today = datetime.date.today().isoformat()

        def work() -> str:
            if action == "add":
                line = self._sh(["tools/taguri/favourites.py", "--today", today],
                                "引いた")
                if line != "引いた":
                    return line
            # **一覧を組み直さないと画面に出ない。** お気に入りの新着は
            # `recommend2.json` から読むためである（3 秒ほど）。
            # **`--no-snapshot` を付ける** ── `presented` は「その週に全国で出した
            # 15 件」の記録で、週次の指標の分母である。押すたびに label が増えると
            # 分母が動く（検証 026 と同じ理由でここを汚さない）
            return self._sh(["tools/review/recommend2.py", "--today", today,
                             "--top", "15", "--no-snapshot"],
                            "新着に反映しました ── 画面を読み込み直してください"
                            if action == "add" else
                            "一覧から外しました ── 画面を読み込み直してください")

        self.enqueue("この名前の公演を取りに行っています…" if action == "add"
                     else "一覧を組み直しています…", work)
        return {"ok": True, "kind": kind, "name": name, "n": len(cur)}

    def on_decline(self, b: dict) -> dict:
        """**出さないと決めた語**（お気に入りの裏返し）。

        起案者の指示（2026-08-24）── 見送った理由が推薦に 1 文字も効いていなかったので、
        **理由の文から拾った語を、本人が押して確定する形**にした。

        **機械は決めない。** 文から語を取り出して「これから観られる公演の何件に当たるか」を
        数えるところまでが機械の仕事で、外すかどうかは押した人が決める。

        **消さない。** 当たった公演は推薦枠から外して畳んだ束に置くだけなので、
        語を外せば次の一覧から戻る。
        """
        action = str(b.get("action") or "")
        word = str(b.get("word") or "").strip()[:40]
        if action not in ("add", "remove") or not word:
            raise ValueError("action（add / remove）と word が要る")
        with self.lock:
            cur = RC.load_declined()
            if action == "add":
                if word not in cur:
                    cur.append(word)
            else:
                cur = [w for w in cur if w != word]
            RC.save_declined(cur)
            self.n["decline"] = self.n.get("decline", 0) + 1
        # **一覧を組み直さないと効かない。** 束の割り振りは `recommend2.py` が決める
        # （`--no-snapshot` は `on_favourite` と同じ理由 ── 週次の指標の分母を動かさない）
        today = datetime.date.today().isoformat()

        def work() -> str:
            return self._sh(["tools/review/recommend2.py", "--today", today,
                             "--top", "15", "--no-snapshot"],
                            ("この語に当たる公演を推薦から外しました"
                             if action == "add" else "この語の公演を推薦に戻しました")
                            + " ── 画面を読み込み直してください")

        self.enqueue("一覧を組み直しています…", work)
        return {"ok": True, "word": word, "n": len(cur)}

    # ---- 5「観ればよかった」の登録 ----------------------------------------
    def on_missed(self, b: dict) -> dict:
        """**絞り込みの穴を測る唯一の口である。** 気づかなかった見逃しは原理的に数えられないが、
        あとで気づいたものは本人が申告できる（V35）。

        **登録した直後に、演者とあらすじを調べに行く**（起案者の指示・2026-08-25 ──
        「観ればよかった」で足した公演は、演者やあらすじを調べてまず表示してほしい）。
        手で足す欄と違って**ここには選ぶ本人がいない** ── 見逃した公演なので観劇日が無く、
        同じ題名の公演が複数あっても、どれを観る予定だったのかを決める材料が無い。
        だから機械が題名の当たりがいちばん良い 1 件を選ぶが、**記録には結び付けない**
        （観ていない公演を、観た記録の材料に混ぜないという既定はここでも動かさない）。
        調べるのは押した直後の 1 回だけで、外への要求は 1 リクエスト／秒の同じ経路
        （`enqueue`）を通る。

        **一度この機能を丸ごと失っている**（2026-08-25・別セッションが同じファイルを
        同時に編集し、未コミットのこの変更を上書きした）。ここは書き直したもので、
        設計は変えていない。
        """
        title = str(b.get("title") or "").strip()[:200]
        if not title:
            raise ValueError("title が要る")
        with self.lock:
            self.con.execute(
                "INSERT INTO missed (title, created_at, note) VALUES (?,"
                " datetime('now','localtime'), ?)"
                " ON CONFLICT(title) DO UPDATE SET created_at=excluded.created_at",
                (title, str(b.get("note") or "")[:1000]))
            self.con.commit()
            self.n["missed"] += 1
        self.enqueue("演者とあらすじを調べています…", lambda: self._lookup_missed(title))
        return {"ok": True, "title": title}

    def _lookup_missed(self, title: str) -> str:
        """`on_missed` が登録した題名から、演者とあらすじを調べて書き戻す。

        探し方は手で足す欄の検索と同じもの（`stage_search.py`）を使う ──
        探し方を 2 通り作らない。あらすじは公演ページの本文から LLM に抜き出させる
        （`extract_theme_llm.py`・検証 020 で規則による切り出しは実質 24% しか
        取れないと分かっている）。
        """
        import stage_search as SS
        import extract_theme_llm as TH
        r = SS.lookup_one(title)
        if not r.get("ok"):
            self._save_missed_lookup(title, note=r.get("why") or "見つかりませんでした")
            return "この題名の公演ページが見つかりませんでした"
        sid = str(r["stage_id"])
        f = r.get("fields") or {}
        note = (f"同じ題名の候補が {r['n']} 件見つかりました。表示しているのは最初の 1 件です。"
                if r["n"] > 1 else "")
        try:
            synopsis = TH.synopsis_of(sid, title)
        except Exception:                                            # noqa: BLE001
            synopsis = ""
        self._save_missed_lookup(title, stage_id=sid, venue=r.get("venue", ""),
                                 period=r.get("period", ""), fields=f,
                                 synopsis=synopsis, note=note)
        return "／".join([
            "演者を取り込みました" if f.get("出演") else "演者のクレジットを取れませんでした",
            "あらすじを取り込みました" if synopsis else "あらすじを取れませんでした",
        ])

    def _save_missed_lookup(self, title: str, *, stage_id: str = "", venue: str = "",
                            period: str = "", fields: dict | None = None,
                            synopsis: str = "", note: str = "") -> None:
        with self.lock:
            self.con.execute(
                "UPDATE missed SET stage_id=?, venue=?, period=?, fields_json=?, synopsis=?,"
                " lookup_note=?, looked_up_at=datetime('now','localtime') WHERE title=?",
                (stage_id, venue, period,
                 json.dumps(fields, ensure_ascii=False) if fields else "",
                 synopsis, note, title))
            self.con.commit()


    # ---- 6 公演詳細を直す --------------------------------------------------
    def on_fix_work(self, b: dict) -> dict:
        """題名・上演日・劇場を人が確定する。

        **抽出は題名をよく間違える。** 実データ 129 作品のうち 24 件で括弧が閉じて
        おらず（本文の折り返しで題名が切れている）、販売側の冠が残っているものもある。
        **直す口が無いと、当事者は間違いに気づいていても直せない。**

        直した内容は `fixes` 表に残り、**次の取り込みと次の LLM の情報取得に効く**
        （`tools/tickets/corrections.py`）── 1 回直したことが 1 回しか効かないなら、
        直す手間に見合わない。
        """
        work_key = str(b.get("work_key") or "")
        if not work_key:
            raise ValueError("work_key が要る")
        with self.lock:
            if b.get("clear"):
                out = APP.unfix_work(work_key)
            else:
                title = b.get("title")
                shows = b.get("shows")
                if not isinstance(shows, list):
                    shows = []
                out = APP.fix_work(
                    work_key,
                    title=str(title)[:200] if title is not None else None,
                    shows=[{"uid": str(s.get("uid") or ""),
                            "date": str(s.get("date") or ""),
                            "time": str(s.get("time") or "")[:5],
                            "venue": str(s.get("venue") or "")[:80]}
                           for s in shows if isinstance(s, dict)])
            self.n["fix"] = self.n.get("fix", 0) + 1
        return out

    # ---- 7 手で 1 件足す ---------------------------------------------------
    def on_add_work(self, b: dict) -> dict:
        """**メールに残らない経路を手で足す。** 招待・当日窓口・人に取ってもらった分。"""
        title = str(b.get("title") or "").strip()[:200]
        date = str(b.get("date") or "").strip()[:10]
        venue = str(b.get("venue") or "").strip()[:80]
        time_ = str(b.get("time") or "").strip()[:5]
        if not title:
            raise ValueError("題名が要る")
        if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError("日付は YYYY-MM-DD で入れる")
        if time_ and not re.fullmatch(r"\d{2}:\d{2}", time_):
            raise ValueError("開演時刻は HH:MM で入れる")
        # **候補から選んだときだけ id が付く。** 手で打った分は空のまま
        stage_id = str(b.get("stage_id") or "").strip()[:16]
        if stage_id and not re.fullmatch(r"\d{1,12}", stage_id):
            raise ValueError("公演の id が数字ではない")
        with self.lock:
            out = APP.add_work(title, date, venue, stage_id, time_)
            self.n["add"] += 1
        # **足した直後に材料を取りに行く**（起案者の指示・2026-08-24）。
        # **月 1 回の段では拾われない** ── `link_works.py` が探すのは「評価が付いている
        # のに材料の無い記録」なので、足したばかりで評価の無い記録は対象にならない
        self._enrich(out.get("stage_id") or stage_id, out.get("work_key") or "",
                     title, date)
        return out

    def _enrich(self, stage_id, work_key: str, title: str, date: str) -> None:
        """1 公演ぶんの材料（公演ページ・クレジット・ポスター・あらすじ）を取りに行く。

        **結び付いていなければ、まず自動で探す**（起案者の指示・2026-08-26 ──
        「今人が手動で結びつけているので、できるものは自動で結びつけてほしい」）。
        `link_works.find` は日付と題名の両方が合ったときだけ当たりにする ── 月 1 回の
        バッチ（`link_works.py`）がすでに使っている、当たったときだけ結び付ける規則を
        そのまま流用する（新しい当て方は作らない）。

        **日付が無ければ探さない。** `find` は上演期間の中に観劇日があることを要求する
        ── 日付が無いと安全に当てられない（`on_link_stage` が呼ぶときは日付を渡さない
        ので、そちらでは自動では探さない。「結び付けを外す」を自動で結び直さないためでもある）。
        """
        sid = str(stage_id or "")
        if not sid.isdigit() and not (work_key and date):
            return
        import enrich as EN

        def work() -> str:
            found_sid = sid
            note = ""
            if not found_sid.isdigit() and work_key and date:
                import link_works as LW
                r = LW.find({"title": title, "date": date})
                if r.get("matched"):
                    with self.lock:
                        APP.link_stage(work_key, r["stage_id"])
                    found_sid = r["stage_id"]
                    note = f"公演ページを自動で見つけて結び付けました（{r['page_title'][:30]}）／"
                else:
                    return "公演ページを自動では見つけられませんでした ── " \
                           "「公演詳細を直す」から手で探して結び付けられます"
            return note + EN.stage(found_sid, work_key=work_key, title=title, date=date)

        self.enqueue("公演ページを探し、材料を取りに行っています…", work)

    # ---- 8 同じ公演をまとめる ／ 取り込みを取り消す -------------------------
    def on_merge_work(self, b: dict) -> dict:
        """**2 つの記録が同じ公演だと本人が答えたときにまとめる。**

        `other` を渡さずに `unmerge` を渡すと、この記録にまとめた分を全部もとに戻す。
        **戻せなければ誤操作が取り返せない**（除外と同じ扱い）。
        """
        work_key = str(b.get("work_key") or "")
        if not work_key:
            raise ValueError("work_key が要る")
        with self.lock:
            if b.get("unmerge"):
                out = APP.unmerge_work(work_key)
            else:
                out = APP.merge_works(work_key, str(b.get("other") or ""))
            self.n["fix"] = self.n.get("fix", 0) + 1
        return out

    def on_drop_work(self, b: dict) -> dict:
        """**取り込んだ記録を候補から外す。** 消さずに外すので、いつでも戻せる。"""
        work_key = str(b.get("work_key") or "")
        if not work_key:
            raise ValueError("work_key が要る")
        with self.lock:
            out = APP.drop_work(work_key)
            self.n["drop"] = self.n.get("drop", 0) + 1
        return out

    # ---- 9 公演ページが無い公演を、手で埋める ------------------------------
    def on_hand_credits(self, b: dict) -> dict:
        """出演者・作り手を手で書く。

        起案者の指示（2026-08-24）──「公演ページが無い公演のために、ポスターと
        出演者を手で入れられるようにする」。**書いた分は名簿に入る**
        （`measure_nets.load_rated` が公演ページの分に足して読む）。
        """
        work_key = str(b.get("work_key") or "")
        if not work_key:
            raise ValueError("work_key が要る")
        fields = b.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("欄が要る")
        with self.lock:
            out = APP.save_hand_credits(work_key, fields)
            self.n["fix"] = self.n.get("fix", 0) + 1
        return out

    def on_hand_poster(self, b: dict) -> dict:
        """ポスターを手で入れる（`drop` を渡すと外す）。

        **受け取った画像は端末内に写すだけで、どこへも送らない。** 画面から外部サイトを
        叩かないという守り（企画書 5 章の守り 5）は、こちらの向きでも同じである。
        """
        work_key = str(b.get("work_key") or "")
        if not work_key:
            raise ValueError("work_key が要る")
        with self.lock:
            if b.get("drop"):
                out = APP.drop_hand_poster(work_key)
            else:
                out = APP.save_hand_poster(work_key, str(b.get("image") or ""))
            self.n["fix"] = self.n.get("fix", 0) + 1
        return out

    def on_hand_theme(self, b: dict) -> dict:
        """**公演ページから内容を読み取れなかった公演に、本人が内容を入れる。**

        起案者の問い（2026-08-25）──「『あらすじを取れませんでした』の作品を
        自分で追加することはできる？」

        **読み取りは別のスレッドに出す。** 貼った本文や URL からタグを作るには LLM を
        1 回呼ぶので数十秒かかる ── その間ほかの操作まで止まると、
        **押したら固まったようにしか見えない。** 入れた内容そのものは、その場で画面に出る。
        **タグが届いたかどうかは、画面側が `pollHandTheme` で数秒おきに確かめる**
        （`on_hand_theme_refresh`）ので、開き直す必要はない。
        """
        sid = str(b.get("stage_id") or "").strip()[:16]
        if not sid:
            raise ValueError("どの公演か分かりません")
        fields = b.get("fields")
        if fields is not None and not isinstance(fields, dict):
            raise ValueError("出演者・作り手の欄の形が違う")
        with self.lock:
            out = APP.save_hand_theme(sid, words=str(b.get("words") or ""),
                                      synopsis=str(b.get("synopsis") or ""),
                                      url=str(b.get("url") or ""), fields=fields)
            self.n["fix"] = self.n.get("fix", 0) + 1
        # **`read` は画面にも返す。** ここで pop するだけだと、押した直後に
        # 自動で拾いに行くかどうかを画面側が判断できなくなる（`pollHandTheme`）
        out["read"] = out.pop("read", False)
        if out["read"]:
            threading.Thread(target=self._read_theme, args=(sid,), daemon=True).start()
            out["said"] = ("保存しました。題材はいま読み取っています ── "
                           "少し待つとタグが自動で出ます")
        return out

    def _read_theme(self, sid: str) -> None:
        """**別のスレッドで読み取る。** 失敗しても画面は落とさない ──
        入れた内容は保存済みで、タグが付かなかっただけである。"""
        try:
            APP.read_hand_theme(sid)
        except Exception as e:                                       # noqa: BLE001
            print(f"  題材の読み取りに失敗しました（{sid}）: {e}", flush=True)

    def on_hand_theme_refresh(self, b: dict) -> dict:
        """**読み取り中のタグが届いたかを、画面が数秒おきに確かめる。**

        書く操作ではないので `self.n` は増やさない ── 自動で何度も呼ばれる操作を
        件数に混ぜると、押した回数が水増しされる。
        """
        sid = str(b.get("stage_id") or "").strip()[:16]
        if not sid:
            raise ValueError("どの公演か分かりません")
        return APP.hand_theme_refresh(sid)

    def on_link_stage(self, b: dict) -> dict:
        """**記録を手元の公演データに結び付ける。**

        これが無いと、メールから導けない記録は評価を付けても推薦に効かない ──
        名簿もあらすじの要素も、公演ページから作るためである。空の id を渡すと外す。
        """
        work_key = str(b.get("work_key") or "")
        stage_id = str(b.get("stage_id") or "").strip()[:16]
        if not work_key:
            raise ValueError("work_key が要る")
        if stage_id and not re.fullmatch(r"\d{1,12}", stage_id):
            raise ValueError("公演の id が数字ではない")
        with self.lock:
            out = APP.link_stage(work_key, stage_id)
            self.n["fix"] = self.n.get("fix", 0) + 1
        # **結び付けた直後に取りに行く。** 結び付けは「この公演です」と本人が決めた
        # ことなので、**その場で材料が付かないと、決めた甲斐が次の起動まで出ない**
        self._enrich(stage_id, work_key, str(out.get("title") or ""), "")
        return out

    def on_restore_work(self, b: dict) -> dict:
        """外した記録をもとに戻す。"""
        key = str(b.get("key") or "")
        if not key:
            raise ValueError("key が要る")
        with self.lock:
            out = APP.restore_work(key)
            self.n["drop"] = self.n.get("drop", 0) + 1
        return out

    def on_purge_work(self, b: dict) -> dict:
        """取り消した記録を、戻す口ごと「取り消した記録」の一覧から消す。"""
        key = str(b.get("key") or "")
        if not key:
            raise ValueError("key が要る")
        with self.lock:
            out = APP.purge_work(key)
            self.n["drop"] = self.n.get("drop", 0) + 1
        return out

    def on_weight(self, b: dict) -> dict:
        """**順位付けに、どの情報をどれくらい効かせるかを 1 つ書く。**

        起案者の指示（2026-08-24）──「実際にどの項目をどれくらい推薦に影響させるのか？
        っていうのを各ユーザーがフィルターで調整できるようにしてほしい」。

        受け付けるのは**列挙した項目と段階の組み合わせだけ**である（守り 4）。任意の数値を
        受けない ── 重みを外から入れられる口にすると、**画面に出ていない効き方で
        順位が付いた一覧を作れてしまう。**
        """
        # **確定を押したときに、7 つまとめて 1 回で来る**（起案者の指示・2026-08-24）。
        # つまみを動かすたびに書く形をやめたので、1 件ずつの口は残しつつ束で受ける
        ws = b.get("weights")
        with self.lock:
            if isinstance(ws, dict):
                if not ws or len(ws) > 32:
                    raise ValueError("weights の件数が範囲外")
                out = APP.save_weights({str(k): str(v) for k, v in ws.items()})
            else:
                out = APP.save_weight(str(b.get("group") or ""), str(b.get("step") or ""))
            self.n["weight"] = self.n.get("weight", 0) + 1
        return out

    def on_pref_setting(self, b: dict) -> dict:
        """**「観に行ける場所」の既定を 1 回で書く**（設定画面）。

        起案者の指示（2026-08-26）──「一括の設定画面をつくってほしい。たとえば
        『全部の表示を指定した都道府県のみにする』」。

        **保存に加えて、いま起動中のこのプロセスの絞り込みもその場で当て直す**
        （`self.prefs`）。保存だけでは、この起動のあいだは古い絞り込みのままになる ──
        設定画面で保存した直後に「今週のおすすめ」を開いても、次の起動まで反映されない
        のでは「設定」として機能しない。
        """
        prefs = b.get("prefs")
        with self.lock:
            out = APP.save_pref_setting(prefs if isinstance(prefs, list) else [])
            self.prefs = list(out["prefs"])
            self.n["pref_setting"] = self.n.get("pref_setting", 0) + 1
        return out

    def on_unseen(self, b: dict) -> dict:
        """**券は買ったが観ていない公演を、観た記録から外す**（または戻す）。

        「この記録を取り消す」とは別の口である ── **買った事実は消さず、観た本数と図と
        評価待ちから外すだけ**である。受け付けるのは真偽の 1 つだけで、回の指定は取らない
        （作品ごとに、その作品の回すべてに当てる）。
        """
        work_key = str(b.get("work_key") or "")
        if not work_key:
            raise ValueError("work_key が要る")
        if not isinstance(b.get("unseen"), bool):
            raise ValueError("unseen は真偽で渡す")
        with self.lock:
            out = APP.set_unseen(work_key, b["unseen"])
            self.n["unseen"] = self.n.get("unseen", 0) + 1
        return out

    # ---- 10 購入確認メールの取り込み --------------------------------------
    def on_import_mail(self, _b: dict) -> dict:
        """**画面のボタンから取り込みを始める。**

        企画書 5 章の 1 段目（前回の走査以降に届いたメールだけを取る）を、
        起動のたびの自動実行ではなく**押したときに走らせる形**でも持たせる ──
        `--mail` を付けて起動し直さないと取り込めないのは、入力の画面として不便である。

        **プロセスの中で直に走らせない。** 数分かかることがあるので別のスレッドに出し、
        画面は状態を聞きに来る（`/api/import_status`）。**画面を閉じても取り込みは
        続く** ── 自動終了の仕組みは無いので（`_watchdog`）、取り込み中かどうかを
        気にする必要も無くなった。

        ## 終わるまで待たずに読む（2026-08-25）

        起案者の指示 ──「取り込みの経過が分かるバーがほしい。進行状況を一目で」。
        以前は `subprocess.run` で**終わってから出力をまとめて読んでいた**ので、
        走っている間に画面へ渡せるのは「始めた…」の 1 行しか無かった。**数分から
        数十分かかる処理で動きが何も出ないのは、効かなかったのと見分けが付かない。**

        取り込み側は段と通数を `@@TAGURI {…}` の 1 行で流してくる
        （`tools/tickets/extract_performances.py` の `tick`）ので、**出力を 1 行ずつ
        読みながら `self.imp` を書き換える。** 画面はそれを帯に変える。

        **`@@TAGURI` の行は控えに残さない** ── 終わったときに出す 1 行は
        「〜通を処理し…」という人向けの最後の行であって、進み具合の記録ではない。
        """
        if self.imp["running"]:
            raise ValueError("もう走っている")
        self.imp = {"running": True, "line": "取り込みを始めました",
                    "step": 1, "steps": 3, "name": "購入確認メールを探しています",
                    "n": 0, "total": 0}
        # **前回の題名は、始めた時点で捨てる。** 走っている最中に開き直したときに
        # 前回の分が「今回取り込んだ公演」として出ることになる
        self.imported = []
        self.n["import"] += 1

        threading.Thread(target=self._import_run, args=(IMPORT_CMD,), daemon=True).start()
        return {"ok": True}

    def _import_run(self, cmd: list[str], *, timeout: int = 1800) -> dict:
        """取り込みを走らせ、**出力を 1 行ずつ読みながら状態を書き換える。**

        `subprocess.run` は終わるまで出力を渡さないので、走っている間の
        `@@TAGURI` の行が画面に届かなかった。**進み具合は終わってから来ても意味が無い。**

        戻り値は最後の状態（検査から呼ぶため）。**画面へ渡すのは `self.imp` である。**
        """
        import subprocess
        try:
            pr = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
            # **黙って固まったままにしない。** 相手のサーバや認証の待ちで返ってこない
            # ことがあるので、`subprocess.run` に付けていた上限はそのまま残す
            kill = threading.Timer(timeout, pr.kill)
            kill.daemon = True
            kill.start()
            done, titles = "", []
            try:
                for line in pr.stdout:
                    line = line.rstrip("\n")
                    if not line.startswith(MARK):
                        continue
                    st = self._imp_line(line[len(MARK):])
                    # **終わりの 1 行は取り込む側が名乗る**（`extract_performances.tock`）。
                    # 標準出力の最後の行を拾う形はやめた ── そこに出るのは
                    # 「題名が取れなかった発行元」の集計表の末尾である
                    if st.get("summary"):
                        done, titles = st["summary"], st.get("titles") or []
                        continue
                    if not st:                # 読めなかった行は、前の状態を残す
                        continue
                    self.imp = st
                rc = pr.wait()
                err = (pr.stderr.read() or "").strip()
            finally:
                kill.cancel()
            if rc == 0:
                line = (done or "終わりました")[:200]
            elif rc < 0:
                # 上限で打ち切った場合。**理由の書いていない番号だけを出さない**
                line = (f"{max(1, timeout // 60)} 分たっても終わらなかったので打ち切りました"
                        "（回線か、送り先の返事を待っている間に止まったことがあります）")
            else:
                line = (f"取り込めませんでした（{rc}）: "
                        + ((err.splitlines() or [""])[-1])[:160])
            self.imp = {"running": False, "line": line}
            self.imported = [str(t)[:120] for t in titles][:200]
        except Exception as e:                                      # noqa: BLE001
            self.imp = {"running": False, "line": f"取り込めませんでした: {e}"[:200]}
        return dict(self.imp)

    @staticmethod
    def _imp_line(payload: str) -> dict:
        """取り込み側が流した 1 行を、画面に渡す状態に直す。

        **読めない行が来ても落とさない。** 進み具合は本筋ではないので、
        壊れた 1 行のために取り込みそのものを止める理由が無い。**空を返して、
        直前の状態をそのまま残す** ── 「取り込んでいます」に戻すと、
        壊れた 1 行のたびに帯と段の表示が最初に巻き戻る。
        """
        try:
            d = json.loads(payload)
        except (ValueError, TypeError):
            return {}
        if d.get("summary"):
            return {"summary": str(d["summary"])[:200],
                    "titles": [str(t) for t in (d.get("titles") or [])]}
        n, total = int(d.get("n") or 0), int(d.get("total") or 0)
        step = int(d.get("step") or 1)
        name = str(d.get("name") or "取り込んでいます")[:60]
        return {"running": True,
                "line": name + (f"（{n}/{total} 通）" if total else ""),
                "step": step, "steps": int(d.get("steps") or 3),
                "name": name, "n": n, "total": total,
                "pct": _pct(step, n, total)}


def serve(label: str, *, port: int = 0, open_browser: bool = True) -> dict:
    """画面を開き、閉じられるまで待つ。返すのは操作ごとの件数。"""
    srv = Server(label, port)
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={srv.token}"
    print(f"  一覧: {url}")
    print("  ここから記録・探す・設定へ移動できる（画面を閉じると落ちる。Ctrl-C でも落ちる）")
    if open_browser:
        # **WSL では既定のブラウザが開かないことがある。** URL は出してあるので手で開けばよい
        try:
            webbrowser.open(url)
        except Exception as e:                                      # noqa: BLE001
            print(f"  ブラウザを開けなかった（URL を手で開くこと）: {e}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  中断した")
    srv.server_close()
    srv.con.close()
    return srv.n


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help="反応を紐づける提示の label")
    ap.add_argument("--port", type=int, default=0)
    a = ap.parse_args()
    # **`run.py` を経由せずここを直に起動したときの備え。** 通常は `run.py` の
    # `_harden_permissions()` が先に umask を絞っているが、単独起動ではそれが効いていない
    os.umask(0o077)
    print(serve(a.label, port=a.port))
