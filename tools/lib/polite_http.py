"""外部サイトへの取得を、攻撃と見なされない作法で行う共通の入口。

**取得先のサーバーから見て「名乗っていて・間隔を守り・断られたら引く」相手であること**を、
各スクリプトの書き方に任せず、この 1 か所で保証する。以前は取得するスクリプトごとに
名乗り（User-Agent）がばらばらで、多くがブラウザ風の `Mozilla/5.0 …` を装い、連絡先も
無かった。robots.txt も読まず、429/503（混んでいる・待ってほしい）にも引かなかった。

## この入口が守ること

| 作法 | どう守るか |
|---|---|
| 名乗る | 決まった名前と、方針を書いたページの URL を User-Agent に入れる（`UA`）。ブラウザを装わない |
| robots.txt に従う | ホストごとに 1 回読み、禁止されたパスへは行かない。`Crawl-delay` があればその秒数に従う |
| 間隔を空ける | **同じホストには 1.1 秒に 1 回まで**（Crawl-delay がそれより長ければそちら）。別のホストへは並行してよい。スレッドをまたいで守る |
| 待ってと言われたら待つ | 429/503 は `Retry-After` の秒数だけ待って 1 回だけ取り直す（上限 `RETRY_AFTER_MAX` 秒） |
| 断られ続けたら引く | 同じホストに 403/429/503 が `REFUSALS_TO_STOP` 回続いたら、**その実行ではもうそのホストへ行かない** |
| 取りすぎない | gzip で受け取り、`max_bytes` を超える分は読まない |

robots.txt を読めなかったとき（5xx・通信失敗）は、**そのホストはその実行では取りに
行かない**（安全側。読めないことを「何でも許された」とは扱わない）。404 など 4xx は
「robots.txt が無い」なので、制限なしとして扱う（一般的なクローラーと同じ）。

## 使い方

    import polite_http as PH
    body = PH.fetch("https://stage.corich.jp/stage/12345")      # bytes
    text = PH.fetch_text(url)                                   # 文字コードを推して str

失敗は例外で返す（呼ぶ側の既存の `except Exception` がそのまま効く）。robots.txt で
禁止・ホストから手を引いた場合は `Skipped` を投げ、**通信は 1 回も起きない。**

標準ライブラリだけで書く（`tools/README.md` の方針）。
"""
from __future__ import annotations

import atexit
import gzip
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from email.utils import parsedate_to_datetime

# **名乗り。** ボット名＋方針ページの URL（連絡先を兼ねる）。ブラウザを装わない
POLICY_URL = "https://github.com/island-6848/taguri-demo/blob/master/docs/crawler-policy.md"
BOT_NAME = "taguri-bot"
UA = f"{BOT_NAME}/1.0 (+{POLICY_URL})"

INTERVAL = 1.1                 # 同じホストへの最短間隔（秒）
CRAWL_DELAY_MAX = 60.0         # robots.txt の Crawl-delay はこの秒数まで従う（それ以上はそのホストを諦める）
RETRY_AFTER_MAX = 120.0        # Retry-After がこれより長ければ待たずに引く
REFUSALS_TO_STOP = 2           # 403/429/503 がこの回数続いたら、その実行ではそのホストへ行かない
ROBOTS_TIMEOUT = 10


class Skipped(Exception):
    """robots.txt の禁止・ホストから手を引いたなどで、**通信せずに**取りやめたこと。"""


_lock = threading.Lock()
_next_at: dict[str, float] = {}           # ホスト → 次に送ってよい時刻
_delay: dict[str, float] = {}             # ホスト → 間隔（Crawl-delay を反映）
_robots: dict[str, object] = {}           # ホスト → RobotFileParser / None（制限なし）/ str（読めなかった理由）
_robots_lock: dict[str, threading.Lock] = {}
_refusals: dict[str, int] = {}            # ホスト → 続けて断られた回数
_stopped: dict[str, str] = {}             # ホスト → 手を引いた理由
_count: dict[str, int] = {}               # ホスト → 送った要求の数（終わりに要約を出す）


def _origin(url: str) -> tuple[str, str]:
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    if p.port:
        host = f"{host}:{p.port}"
    return f"{p.scheme}://{host}", host


def _wait_turn(host: str) -> None:
    """このホストの順番が来るまで待つ。**待っている間、他のホストは止めない。**"""
    while True:
        with _lock:
            now = time.monotonic()
            due = _next_at.get(host, 0.0)
            if now >= due:
                _next_at[host] = now + _delay.get(host, INTERVAL)
                _count[host] = _count.get(host, 0) + 1
                return
        time.sleep(min(due - now, 1.0))


def _open(url: str, *, timeout: float, headers: dict | None, context):
    h = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(req, timeout=timeout, context=context)


def _robots_for(origin: str, host: str, context):
    """ホストの robots.txt を 1 回だけ読む（並行して呼ばれても読むのは 1 回）。"""
    with _lock:
        if host in _robots:
            return _robots[host]
        lk = _robots_lock.setdefault(host, threading.Lock())
    with lk:
        with _lock:
            if host in _robots:
                return _robots[host]
        _wait_turn(host)
        result: object
        try:
            with _open(origin + "/robots.txt", timeout=ROBOTS_TIMEOUT, headers=None,
                       context=context) as r:
                raw = r.read(500_000)
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            text = raw.decode("utf-8", "replace")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(text.splitlines())
            result = rp
            cd = _crawl_delay(text)
            if cd:
                cd = float(cd)
                if cd > CRAWL_DELAY_MAX:
                    _stop(host, f"Crawl-delay {cd:g} 秒は長すぎるので取りに行かない")
                else:
                    with _lock:
                        _delay[host] = max(INTERVAL, cd)
        except urllib.error.HTTPError as e:
            # 4xx は「robots.txt が無い」= 制限なし。429 と 5xx は読めなかった扱い（安全側）
            result = None if (400 <= e.code < 500 and e.code != 429) else f"robots.txt が {e.code}"
        except Exception as e:                                          # noqa: BLE001
            result = f"robots.txt を読めなかった（{type(e).__name__}）"
        with _lock:
            _robots[host] = result
        return result


def _crawl_delay(text: str) -> float | None:
    """`Crawl-delay` を読む。**標準の robotparser は整数しか受け付けず、`0.5` のような
    小数を黙って捨てる**ので、ここだけ自前で読む。自分の名前の組を優先し、無ければ `*`。"""
    found: dict[str, float] = {}
    agents: list[str] = []
    in_rules = False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (x.strip() for x in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(v.lower())
        elif k in ("allow", "disallow", "crawl-delay"):
            in_rules = True
            if k == "crawl-delay":
                try:
                    d = float(v)
                except ValueError:
                    continue
                for a in agents:
                    found.setdefault(a, d)
    for a in (BOT_NAME.lower(), "*"):
        if a in found:
            return found[a]
    return None


def _stop(host: str, why: str) -> None:
    with _lock:
        if host not in _stopped:
            _stopped[host] = why


def _retry_after(e: urllib.error.HTTPError) -> float | None:
    v = (e.headers or {}).get("Retry-After") if e.headers else None
    if not v:
        return 60.0
    v = v.strip()
    if v.isdigit():
        return float(v)
    try:
        return max(0.0, parsedate_to_datetime(v).timestamp() - time.time())
    except Exception:                                                   # noqa: BLE001
        return None


def allowed(url: str, *, context=None) -> bool:
    """robots.txt がこの URL を許しているか（読めなければ False）。"""
    origin, host = _origin(url)
    rp = _robots_for(origin, host, context)
    if isinstance(rp, str):
        return False
    return rp is None or rp.can_fetch(UA, url)


def fetch(url: str, *, timeout: float = 30, max_bytes: int | None = None,
          headers: dict | None = None, robots: bool = True, context=None) -> bytes:
    """URL を作法どおりに取って、本文（gzip は展開済み）を返す。

    `robots=False` は、**巡回ではなく、公開者が機械的な取得のために出している 1 つの
    出口**（Google スプレッドシートの CSV 書き出しなど）に限って使う。間隔・名乗り・
    断られたら引くは、その場合も守る。
    """
    origin, host = _origin(url)
    if not host:
        raise Skipped(f"URL が読めない: {url[:80]}")
    with _lock:
        why = _stopped.get(host)
    if why:
        raise Skipped(f"{host} からは手を引いた（{why}）")
    if robots:
        rp = _robots_for(origin, host, context)
        if isinstance(rp, str):
            _stop(host, rp)
            raise Skipped(f"{host}: {rp}。この実行では取りに行かない")
        if rp is not None and not rp.can_fetch(UA, url):
            raise Skipped(f"robots.txt が禁止している: {url[:80]}")
        with _lock:
            why = _stopped.get(host)
        if why:
            raise Skipped(f"{host} からは手を引いた（{why}）")
    for attempt in range(2):
        _wait_turn(host)
        try:
            with _open(url, timeout=timeout, headers=headers, context=context) as r:
                raw = r.read(max_bytes) if max_bytes else r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            with _lock:
                _refusals[host] = 0
            return raw
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503):
                with _lock:
                    _refusals[host] = _refusals.get(host, 0) + 1
                    n = _refusals[host]
                if n >= REFUSALS_TO_STOP:
                    _stop(host, f"{e.code} が {n} 回続いた")
                    raise
                if e.code in (429, 503) and attempt == 0:
                    wait = _retry_after(e)
                    if wait is None or wait > RETRY_AFTER_MAX:
                        _stop(host, f"{e.code}（Retry-After が長い）")
                        raise
                    # **待ってと言われた分は、そのホスト全体で待つ**（他のスレッドも含めて）
                    with _lock:
                        _next_at[host] = max(_next_at.get(host, 0.0), time.monotonic() + wait)
                    continue
            raise
    raise RuntimeError("unreachable")


def fetch_text(url: str, **kw) -> str:
    """`fetch` の結果を文字列にする。文字コードはヘッダか本文の meta から推す。"""
    raw = fetch(url, **kw)
    enc = "utf-8"
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
    if m:
        enc = m.group(1).decode("ascii", "replace")
    try:
        return raw.decode(enc, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def summary() -> str:
    """送った要求の数と、手を引いたホストの一覧（実行の終わりにログへ出す）。"""
    with _lock:
        if not _count and not _stopped:
            return ""
        top = sorted(_count.items(), key=lambda kv: -kv[1])[:5]
        lines = [f"[polite_http] 要求 {sum(_count.values())} 件／{len(_count)} ホスト（多い順: "
                 + "、".join(f"{h} {n}" for h, n in top) + "）"]
        for h, why in sorted(_stopped.items()):
            lines.append(f"[polite_http] 手を引いた: {h} ── {why}")
    return "\n".join(lines)


@atexit.register
def _print_summary() -> None:
    s = summary()
    if s:
        try:
            print(s, file=sys.stderr, flush=True)
        except OSError:
            pass
