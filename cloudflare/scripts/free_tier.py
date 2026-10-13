#!/usr/bin/env python3
"""無料枠の番人。たぐりは有料のものを 1 つも使わない（docs/free-tier-budget.md）。

起案者の指示（2026-10-13）「必ず無料の範囲内にして。絶対超えないで。つねに警戒してチェックして」。
上限の数字は **ここにだけ** 書く（取得の各段・Worker の試験・文書はここを見る）。各上限は無料枠より
低く取り、超えそうなら **使う前に止める**。止めたら失敗の印を出して、持ち主に GitHub から通知が届くようにする。

    python3 cloudflare/scripts/free_tier.py plan  --data data --mode daily   # Actions の分数を見て、今日の取得の量を決める
    python3 cloudflare/scripts/free_tier.py check --data data [--d1-usage f]  # 使った量を数え、8 割を越えたら失敗する

## 数えているもの

- **GitHub Actions（非公開の taguri-crawler）**: 無料は月 2,000 分。GitHub の API で、この
  リポジトリのジョブの分数（ジョブごとに分へ切り上げ）を直近 31 日分たし、上限 1,500 分の中に
  **これからの 31 日のどの区切り方でも** 収まるときだけ動かす（請求の月の区切りがどこでも越えない）
- **D1 の書き込み**: 無料は 1 日（UTC）10 万行。取得の各段が書く行を、書く前に作業データの控え
  （data/free_tier/usage.json）に足す。1 日 8 万行まで（残りは利用者の操作と Worker の数え）
- **R2**: 無料は保存 10 GB・書き込み系（Class A）月 100 万回・読み出し系（Class B）月 1,000 万回。
  **超えると請求が来る**（D1・Workers は止まるだけ）。入れたポスターの大きさと PUT の回数を
  控えに足し、保存 8 GB・Class A 月 30 万回で止める。読み出しは Worker が D1 の usage 表に数え、
  月 300 万回で R2 から返すのをやめる（cloudflare/src/worker.js の R2_READS_CAP）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ── 上限（無料枠より低く取る。変えるときは docs/free-tier-budget.md と knowledge を直す）──
FREE = {"actions_minutes_month": 2_000, "d1_writes_day": 100_000, "r2_bytes": 10 * 10**9,
        "r2_class_a_month": 1_000_000, "r2_class_b_month": 10_000_000}
CAPS = {"actions_minutes_31d": 1_500, "d1_writes_day": 80_000, "r2_bytes": 8 * 10**9,
        "r2_class_a_month": 300_000, "r2_class_b_month": 3_000_000}
WARN = 0.8                       # 上限のこの割合を越えたら check が失敗する（通知のため）

# Catalog のジョブ 1 回の分数の見積もり（過去の公演の読み取りを除く）。多めに取る
CATALOG_MINUTES = {"daily": 15, "weekly": 120}
WEEKLY_EXTRA = CATALOG_MINUTES["weekly"] - CATALOG_MINUTES["daily"]
PAST_MAX_MINUTES = 135           # 過去の公演の読み取りは 1 日これまで
PAST_SECONDS_PER_PAGE = 1.15     # polite_http の 1.1 秒の間隔と処理
AFTER_PAST_MINUTES = 15          # 読み取りの段の時間の上限の余り（5 分）と、そのあとの D1・書き戻し

LEDGER = Path("free_tier") / "usage.json"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ── 控え（作業データの state ブランチに残る）──
def load(data: Path) -> dict:
    p = data / LEDGER
    u = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    u.setdefault("d1_writes", {})
    u.setdefault("r2", {})
    u["r2"].setdefault("sizes", {})
    u["r2"].setdefault("class_a", {})
    return u


def save(data: Path, u: dict) -> None:
    keep = (utc_now().date() - dt.timedelta(days=40)).isoformat()
    u["d1_writes"] = {d: n for d, n in u["d1_writes"].items() if d >= keep}
    p = data / LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".part")
    tmp.write_text(json.dumps(u, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)


def today(now: dt.datetime | None = None) -> str:
    return (now or utc_now()).date().isoformat()


def month(now: dt.datetime | None = None) -> str:
    return (now or utc_now()).strftime("%Y-%m")


def d1_left(data: Path, now: dt.datetime | None = None) -> int:
    """今日（UTC）まだ書いてよい D1 の行数。"""
    return max(0, CAPS["d1_writes_day"] - int(load(data)["d1_writes"].get(today(now), 0)))


def d1_spend(data: Path, writes: int, now: dt.datetime | None = None) -> None:
    """書く前に足す（失敗して書かなかった分も数える。少なく数えることはない）。"""
    if writes <= 0:
        return
    u = load(data)
    d = today(now)
    u["d1_writes"][d] = int(u["d1_writes"].get(d, 0)) + int(writes)
    save(data, u)


def r2_bytes(u: dict) -> int:
    return sum(int(n) for n in u["r2"]["sizes"].values())


def r2_class_a(u: dict, now: dt.datetime | None = None) -> int:
    return int(u["r2"]["class_a"].get(month(now), 0))


# ── GitHub Actions の分数 ──
def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _ts(s: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def job_minutes_by_day(repo: str, token: str, now: dt.datetime, days: int = 31,
                       get=_get) -> list[int]:
    """直近 `days` 日の、このリポジトリのジョブの分数。[今日, 1 日前, …]。
    請求と同じく、ジョブごとに分へ切り上げる。走っているジョブは今までの分を数える。"""
    out = [0] * days
    since = (now - dt.timedelta(days=days)).date().isoformat()
    api = f"https://api.github.com/repos/{repo}/actions/runs"
    page = 1
    while True:
        q = urllib.parse.urlencode({"created": f">={since}", "per_page": 100, "page": page})
        runs = get(f"{api}?{q}", token).get("workflow_runs", [])
        for run in runs:
            jobs = get(f"{api}/{run['id']}/jobs?per_page=100&filter=all", token).get("jobs", [])
            for j in jobs:
                start = _ts(j.get("started_at"))
                if not start:
                    continue
                end = _ts(j.get("completed_at")) or now
                if end < start:
                    end = now
                ago = (now.date() - start.date()).days
                if 0 <= ago < days:
                    out[ago] += max(1, math.ceil((end - start).total_seconds() / 60))
        if len(runs) < 100:
            return out
        page += 1


def future_catalog(k: int) -> int:
    """これからの k 日に Catalog が使う分の見積もり（毎日の分 + 週 1 の上乗せ）。"""
    return CATALOG_MINUTES["daily"] * k + WEEKLY_EXTRA * math.ceil(k / 7)


def worst_window(by_day: list[int]) -> int:
    """今日を含む 31 日の区切りのうち、いちばん使う区切りの分数（これからの Catalog の見積もりを含む）。
    区切りを k 日先へずらすと、過去の (31 - k) 日分とこれからの k 日分が入る。"""
    n = len(by_day)
    return max(sum(by_day[:n - k]) + future_catalog(k) for k in range(n))


def plan(by_day: list[int] | None, mode: str) -> dict:
    """今日の Catalog を動かしてよいか、どの mode で、過去の公演を何分読むか。
    分数が読めなかったとき（by_day が None）は、過去の公演は読まず、毎日の更新だけにする。"""
    cap = CAPS["actions_minutes_31d"]
    if by_day is None:
        return {"run": True, "mode": "daily", "catalog_minutes": 45, "past_minutes": 0, "past_limit": 0,
                "past_timeout": 5,
                "used_31d": None, "note": "Actions の分数が読めなかったので、毎日の更新だけにする"}
    worst = worst_window(by_day)
    # worst に入っているのは、今日までに使った分と、明日からの Catalog の見積もり。
    # 今日のこの実行の Catalog の分（週 1 なら上乗せも）は、ここで別に取っておく
    room = cap - worst - CATALOG_MINUTES["daily"]
    note = ""
    if mode == "weekly" and room < WEEKLY_EXTRA:
        mode, note = "daily", "週 1 の取り直しの分が無いので、毎日の更新だけにする"
    if room < 0:
        return {"run": False, "mode": mode, "catalog_minutes": 1, "past_minutes": 0, "past_limit": 0,
                "past_timeout": 1,
                "used_31d": sum(by_day), "worst_31d": worst,
                "note": f"Actions の分数が上限 {cap} 分に届く見込みなので、今日は動かさない"}
    if mode == "weekly":
        room -= WEEKLY_EXTRA
    past = min(PAST_MAX_MINUTES, room - AFTER_PAST_MINUTES)
    if past < 10:
        past = 0
    return {"run": True, "mode": mode,
            # 取り直しの段の時間の上限。見積もりの 3 倍か、残りのどちらか小さいほう（最低 10 分）
            "catalog_minutes": max(10, min(CATALOG_MINUTES[mode] * 3, 240, room + CATALOG_MINUTES[mode])),
            "past_minutes": past, "past_limit": int(past * 60 / PAST_SECONDS_PER_PAGE),
            "past_timeout": past + 5, "used_31d": sum(by_day), "worst_31d": worst, "note": note}


# ── 点検 ──
def check(data: Path, by_day: list[int] | None, worker_usage: dict | None,
          now: dt.datetime | None = None) -> list[dict]:
    """使った量と上限の表。worker_usage は D1 の usage 表（k -> n）。読めなかったものは -1（注意にする）。"""
    u = load(data)
    rows = [
        ("D1 の書き込み（今日・取得の分）", int(u["d1_writes"].get(today(now), 0)), CAPS["d1_writes_day"], FREE["d1_writes_day"]),
        ("R2 の保存（バイト）", r2_bytes(u), CAPS["r2_bytes"], FREE["r2_bytes"]),
        ("R2 の Class A（今月）", r2_class_a(u, now), CAPS["r2_class_a_month"], FREE["r2_class_a_month"]),
        ("R2 の Class B（今月・Worker）",
         -1 if worker_usage is None else int(worker_usage.get(f"r2_get:{month(now)}", 0)),
         CAPS["r2_class_b_month"], FREE["r2_class_b_month"]),
    ]
    if by_day is not None:
        rows.insert(0, ("GitHub Actions（直近 31 日・分）", sum(by_day), CAPS["actions_minutes_31d"],
                        FREE["actions_minutes_month"]))
    else:
        rows.insert(0, ("GitHub Actions（直近 31 日・分）", -1, CAPS["actions_minutes_31d"], FREE["actions_minutes_month"]))
    return [{"what": w, "used": n, "cap": c, "free": f,
             "ok": n >= 0 and n <= c * WARN} for w, n, c, f in rows]


def _actions(now: dt.datetime) -> list[int] | None:
    repo, token = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_TOKEN", "")
    if not repo or not token:
        return None
    try:
        return job_minutes_by_day(repo, token, now)
    except Exception as e:                                          # noqa: BLE001
        print(f"::warning::Actions の分数が読めなかった（{type(e).__name__}: {e}）")
        return None


def _out(pairs: dict) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={str(v).lower() if isinstance(v, bool) else v}\n" for k, v in pairs.items())
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["plan", "check"])
    ap.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[2] / "data")
    ap.add_argument("--mode", default="daily", choices=["daily", "weekly"])
    ap.add_argument("--d1-usage", type=Path, help="wrangler d1 execute --json の出力（usage 表）")
    a = ap.parse_args()
    now = utc_now()
    by_day = _actions(now)
    if a.action == "plan":
        p = plan(by_day, a.mode)
        print(json.dumps(p, ensure_ascii=False))
        _out({k: v for k, v in p.items() if k in ("run", "mode", "catalog_minutes", "past_minutes", "past_limit", "past_timeout")})
        if p["note"]:
            print(f"::warning::{p['note']}")
        if not p["run"]:
            print(f"::error::{p['note']}")
            return 1
        return 0
    worker = None
    if a.d1_usage and a.d1_usage.exists():
        try:
            res = json.loads(a.d1_usage.read_text(encoding="utf-8"))
            worker = {r["k"]: r["n"] for r in res[0]["results"]}
        except (ValueError, KeyError, IndexError, TypeError):
            worker = None
    rows = check(a.data, by_day, worker, now)
    lines = ["| 項目 | 使った量 | 上限（たぐり） | 無料枠 | |", "|---|---:|---:|---:|---|"]
    for r in rows:
        used = "読めなかった" if r["used"] < 0 else f"{r['used']:,}"
        lines.append(f"| {r['what']} | {used} | {r['cap']:,} | {r['free']:,} | {'ok' if r['ok'] else '**注意**'} |")
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## 無料枠\n\n" + "\n".join(lines) + "\n")
    bad = [r for r in rows if not r["ok"]]
    for r in bad:
        print(f"::error::無料枠の注意: {r['what']} が上限の {int(WARN * 100)}% を越えたか、読めなかった")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
