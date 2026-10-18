#!/usr/bin/env python3
"""polite_http の作法を、手元に立てた仮のサーバーで確かめる（外部へは通信しない）。

    python3 tools/lib/test_polite_http.py
"""
from __future__ import annotations

import gzip
import http.server
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import polite_http as PH                                            # noqa: E402

PH.INTERVAL = 0.3              # 試験を速くする（本番は 1.1 秒）
PH.RETRY_AFTER_MAX = 2.0

ok = ng = 0
# 高圧縮の gzip（展開すると 2,000,000 バイト・圧縮後は 2 KB ほど）
BOMB = gzip.compress(b"\0" * 2_000_000)


def check(name: str, cond: bool, detail="") -> None:
    global ok, ng
    if cond:
        ok += 1
        print(f"  OK  {name}")
    else:
        ng += 1
        print(f"  NG  {name}  ← {detail}")


class H(http.server.BaseHTTPRequestHandler):
    hits: list[tuple[float, str, str]] = []
    state = {"429": 0, "503": 0}

    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        H.hits.append((time.monotonic(), self.path, self.headers.get("User-Agent", "")))
        port = self.server.server_address[1]
        kind = self.server.kind
        if self.path == "/robots.txt":
            if kind == "robots404":
                return self._send(404)
            if kind == "robots500":
                return self._send(500)
            if kind == "robotsbomb":
                return self._send(200, BOMB, {"Content-Encoding": "gzip"})
            if kind == "size":
                return self._send(404)
            return self._send(200, b"User-agent: *\nDisallow: /private\nCrawl-delay: 0.6\n")
        if self.path.startswith("/429"):
            H.state["429"] += 1
            if H.state["429"] == 1:
                return self._send(429, headers={"Retry-After": "1"})
            return self._send(200, b"after-wait")
        if self.path.startswith("/503"):
            return self._send(503, headers={"Retry-After": "1"})
        if self.path.startswith("/bomb"):
            return self._send(200, BOMB, {"Content-Encoding": "gzip"})
        if self.path.startswith("/gz"):
            return self._send(200, gzip.compress(b"small page"), {"Content-Encoding": "gzip"})
        if self.path.startswith("/big"):
            return self._send(200, b"x" * 5000)
        if self.path.startswith("/403"):
            return self._send(403)
        return self._send(200, f"page {self.path} on {port}".encode())


def serve(kind: str):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    srv.kind = kind
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


print("名乗り")
srv, base = serve("normal")
body = PH.fetch(base + "/a")
check("本文が取れる", body.startswith(b"page /a"), body[:40])
ua = [h[2] for h in H.hits if h[1] == "/a"][0]
check("User-Agent はボット名と方針ページの URL", ua == PH.UA and "taguri-bot" in ua and PH.POLICY_URL in ua, ua)
check("ブラウザを装わない", "Mozilla" not in ua, ua)
check("最初に robots.txt を読む", H.hits[0][1] == "/robots.txt", [h[1] for h in H.hits])

print("robots.txt")
try:
    PH.fetch(base + "/private/x")
    check("禁止されたパスは取らない", False, "取れてしまった")
except PH.Skipped:
    check("禁止されたパスは取らない（Skipped・通信なし）", not any(h[1].startswith("/private") for h in H.hits))
n_robots = sum(1 for h in H.hits if h[1] == "/robots.txt")
PH.fetch(base + "/b")
check("robots.txt はホストごとに 1 回だけ読む", sum(1 for h in H.hits if h[1] == "/robots.txt") == n_robots == 1)

print("間隔")
H.hits.clear()
threads = [threading.Thread(target=PH.fetch, args=(base + f"/p{i}",)) for i in range(4)]
[t.start() for t in threads]
[t.join() for t in threads]
ts = sorted(h[0] for h in H.hits)
gaps = [b - a for a, b in zip(ts, ts[1:])]
check("Crawl-delay（0.6 秒）を、スレッドをまたいで守る", len(ts) == 4 and min(gaps) >= 0.55, [round(g, 2) for g in gaps])

print("待ってと言われたら待つ")
H.hits.clear()
t0 = time.monotonic()
body = PH.fetch(base + "/429")
check("429 は Retry-After だけ待って 1 回だけ取り直す", body == b"after-wait" and time.monotonic() - t0 >= 0.95,
      (body, round(time.monotonic() - t0, 2)))

print("断られ続けたら引く")
srv2, base2 = serve("normal")
try:
    PH.fetch(base2 + "/503")
except Exception as e:                                              # noqa: BLE001
    check("503 が続くと例外で返す", "503" in str(e), e)
before = len(H.hits)
try:
    PH.fetch(base2 + "/fine")
    check("手を引いたホストへは行かない", False, "取れてしまった")
except PH.Skipped:
    check("手を引いたホストへは、その実行では行かない（通信なし）", len(H.hits) == before)

srv3, base3 = serve("normal")
for p in ("/403a", "/403b"):
    try:
        PH.fetch(base3 + p)
    except Exception:                                                # noqa: BLE001
        pass
try:
    PH.fetch(base3 + "/ok")
    check("403 が 2 回続いたら引く", False, "取れてしまった")
except PH.Skipped:
    check("403 が 2 回続いたら引く", True)

print("robots.txt が無い・読めない")
srv4, base4 = serve("robots404")
check("robots.txt が 404 なら制限なしで取る", PH.fetch(base4 + "/x").startswith(b"page"))
srv5, base5 = serve("robots500")
try:
    PH.fetch(base5 + "/x")
    check("robots.txt が 500 なら取りに行かない", False, "取れてしまった")
except PH.Skipped:
    check("robots.txt が 500 なら取りに行かない（安全側）", True)
srv6, base6 = serve("robots500")
check("robots=False（公開者の書き出し口）は robots.txt を見ない", PH.fetch(base6 + "/csv", robots=False).startswith(b"page"))

print("取りすぎない")
srv7, base7 = serve("size")
check("上限内の gzip は展開して返す", PH.fetch(base7 + "/gz", max_bytes=3000) == b"small page")
try:
    body = PH.fetch(base7 + "/bomb", max_bytes=3000)
    check("展開後に上限を超える gzip は断る", False, f"{len(body)} バイト返った")
except PH.TooLarge:
    check("展開後に上限を超える gzip は断る（TooLarge）", True)
try:
    body = PH.fetch(base7 + "/big", max_bytes=3000)
    check("上限を超える非圧縮の本文は、切って成功にせず断る", False, f"{len(body)} バイト返った")
except PH.TooLarge:
    check("上限を超える非圧縮の本文は、切って成功にせず断る（TooLarge）", True)
check("上限ちょうどまでは取れる", PH.fetch(base7 + "/big", max_bytes=5000) == b"x" * 5000)
srv8, base8 = serve("robotsbomb")
H.hits.clear()
try:
    PH.fetch(base8 + "/x")
    check("展開すると大きすぎる robots.txt は読めなかった扱い", False, "取れてしまった")
except PH.Skipped as e:
    check("展開すると大きすぎる robots.txt は読めなかった扱い（取りに行かない）",
          "TooLarge" in str(e) and not any(h[1] == "/x" for h in H.hits), e)

print(f"\n{ok} 件通過・{ng} 件失敗")
sys.exit(1 if ng else 0)
