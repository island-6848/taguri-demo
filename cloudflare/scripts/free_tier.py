#!/usr/bin/env python3
"""無料枠の番人。たぐりは有料のものを 1 つも使わない（docs/free-tier-budget.md）。

起案者の指示（2026-10-13）「必ず無料の範囲内にして。絶対超えないで。つねに警戒してチェックして」。
上限の数字は **ここにだけ** 書く（取得の各段・Worker の試験・文書はここを見る）。各上限は無料枠より
低く取り、超えそうなら **使う前に止める**。毎日の更新を止めた日と、上限の 8 割を越えた日は、取得のリポジトリの
issue「無料枠の注意（取得）」で持ち主に知らせる（失敗にはしない。数えが読めないときだけ失敗にする。dec-crawl-tiers）。

    python3 cloudflare/scripts/free_tier.py plan  --data data --mode daily   # Actions の分数を見て、今日の取得の量を決める
    python3 cloudflare/scripts/free_tier.py check --data data [--d1-usage f] [--d1-info f] [--d1-logs …] [--run-mode daily]
                                                     # 使った量と、この実行の段ごとの時間を表にする

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
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ── 上限（無料枠より低く取る。変えるときは docs/free-tier-budget.md と knowledge を直す）──
FREE = {"actions_minutes_month": 2_000, "d1_writes_day": 100_000, "d1_reads_day": 5_000_000, "r2_bytes": 10 * 10**9,
        "r2_class_a_month": 1_000_000, "r2_class_b_month": 10_000_000}
# Actions は一時的に 1,600 分（起案者の判断 2026-10-20「すべてはい」）。1,500 分では、これからの毎日の取得を見込むと上限を越え、
# 計画の段が 10-19・10-20 の取得を始める前に止めていた。無料の 2,000 分までは 400 分残る。31 日の枠に余裕ができたら 1,500 に戻す
CAPS = {"actions_minutes_31d": 1_600, "d1_writes_day": 80_000, "r2_bytes": 8 * 10**9,
        # D1 の読み出し（Worker と取得の合計、直近 24 時間）。無料は 1 日 500 万行で、越えると止まる（2026-10-20 に越えた）。
        # 半分で知らせる（d1-reads-over-1020・f-deliver-past-reads）
        "d1_reads_day": 3_000_000,
        "r2_class_a_month": 300_000, "r2_class_b_month": 3_000_000,
        # 手元の管理画面（tools/admin）の分。取得の分と同じ上限の中で、さらにこれだけに抑える
        "admin_d1_writes_day": 1_000, "admin_posters_month": 300,
        # 管理画面の控え（data/admin/free_tier/usage.json）は取得の控えと別のファイルで、互いの R2 の保存を知らない。
        # だから管理画面が R2 に置く量（ポスター・お試しの文字）に別に上限を置き、取得の 8 GB と足しても 8.5 GB（無料 10 GB の 85%）に収める（issue #139）
        "admin_r2_bytes": 500_000_000,
        # 控えから戻す予行（backup_d1.py drill）が新しい D1 に書く行の上限。D1 の 1 日 10 万行は口座全体なので、
        # 予行の書き込みも同じ日の取得（8 万行）・管理画面（1,000 行）・利用者の操作と同じ枠から出る。
        # 越える大きさの控えは、D1 には入れずに手元の SQLite で開けるかだけを確かめる（issue #139）
        "drill_d1_writes": 10_000}
WARN = 0.8                       # 上限のこの割合を越えたら check が失敗する（通知のため）

# Catalog のジョブ 1 回の分数の見積もり（過去の公演の読み取りを除く）。多めに取る
CATALOG_MINUTES = {"daily": 15, "weekly": 120}
WEEKLY_EXTRA = CATALOG_MINUTES["weekly"] - CATALOG_MINUTES["daily"]
PAST_MAX_MINUTES = 135           # 過去の公演の読み取りは 1 日これまで
PAST_SECONDS_PER_PAGE = 1.15     # polite_http の 1.1 秒の間隔と処理
# 過去の公演のポスター（起案者の指示 2026-10-16「過去の公演の全てのポスターデータも欲しい」、posters.fetch_past）。
# 過去の公演の読み取りと同じ残りから、3 分の 1（1 日 POSTER_MAX_MINUTES まで）を回す。段の時間の上限の余り 5 分も取っておく
POSTER_MAX_MINUTES = 60
POSTER_AFTER_MINUTES = 5
AFTER_PAST_MINUTES = 15          # 読み取りの段の時間の上限の余り（5 分）と、そのあとの D1・書き戻し
# 推薦の再生（replay.yml、replay_job.py）を手で動かすときに取っておく分。準備と計算で 10 分ほど、多めに取る
REPLAY_MINUTES = 20
# 控えから戻す予行（restore-drill.yml、月 1 回と手動）。ジョブの上限 20 分をまるごと取っておく（issue #139）
DRILL_MINUTES = 20
# 過去の公演のあらすじの本文だけを取る実行（stories.yml、起案者の指示 2026-10-18「ページを取る時間を増やして」）。
# 毎日の更新の分を取っておいた残りから、1 回 STORIES_MAX_MINUTES 分まで（ジョブの上限 6 時間の手前）
STORIES_MAX_MINUTES = 300
STORIES_AFTER_MINUTES = 10       # 準備と書き戻し
# ── 取得の優先順位（dec-crawl-tiers、起案者の指示 2026-10-21「下位の処理が大量の実行時間を消費しても、上位の処理が停止しない」）──
#   1 新しい公演の発見と登録  2 これからの公演の情報・出演者・あらすじ  3 持っている公演の変更確認
#   4 過去の公演の補完        5 過去の公演のポスター・あらすじの本文
# 1〜3 は毎日の更新（CATALOG_MINUTES["daily"] の中）で、これからの毎日の分を先に取っておく（worst_window）。
# 4・5 と手で動かすもの（再生・予行・本文）は、その残りから BACKGROUND_MARGIN を引いた分だけを使う。
# 見積もりより長くかかっても、毎日の更新の取り置きを食わないための余白（前は余白が 0 で、ポスターを R2 に入れる段に
# 時間の上限が無く、45 分かかった日もあった。Catalog #5）
BACKGROUND_MARGIN = 30
# 新しい公演の発見（サイトマップの差分と、公演ページの読み直し）の上限。毎日の更新の 15 分の中に入れる。
# 実測（10-14〜10-20 の Catalog）: 準備・取り直し・D1 へ入れる・控え・書き戻しで 4〜5 分。取り直しは 1 分前後
DISCOVER_MINUTES = 5
# ポスターを R2 に入れる段の上限（前は無かった）。入れきれなかった分は次回（deliver_posters.py --max-minutes）
POSTER_UPLOAD_MAX_MINUTES = 30
# 過去の公演の名前の索引を R2 に入れる段（実測 3〜4 分）。過去の公演を読んだ日だけ動かす
PAST_INDEX_MINUTES = 6

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


_ROWS_WRITTEN = re.compile(r'"rows_written"\s*:\s*(\d+)')


def rows_written(text: str) -> int | None:
    """D1 の rows_written（wrangler d1 execute の出力の meta）。1 回の実行に 1 つ。読めなければ None。"""
    got = _ROWS_WRITTEN.findall(text or "")
    return int(got[-1]) if got else None


def d1_settle(data: Path, day: str, estimated: int, measured: int) -> int:
    """書く前に足した見積もりを、入れ終えたあとに D1 が返した数（rows_written）に置き換える。
    書き込みは upsert で既にある行に当たると 1（主キーの索引は書かない）、新しい行は 2 なので、
    見積もり（全部を新しい行として数える）は多めになる（d1-upsert-counts）。少なく数えないよう、
    呼ぶのは全部のファイルを入れ終え、全部の数が読めたときだけ。置き換えた日の値を返す。"""
    u = load(data)
    cur = int(u["d1_writes"].get(day, 0))
    u["d1_writes"][day] = max(0, cur - int(estimated) + int(measured))
    save(data, u)
    return u["d1_writes"][day]


def r2_bytes(u: dict) -> int:
    return sum(int(n) for n in u["r2"]["sizes"].values())


def r2_class_a(u: dict, now: dt.datetime | None = None) -> int:
    return int(u["r2"]["class_a"].get(month(now), 0))


def r2_class_b(u: dict, now: dt.datetime | None = None) -> int:
    """取得の側が R2 から読んだ回数（ポスターの縮め直し）。Worker の読み出しとは別に数え、点検で足す。"""
    return int(u["r2"].get("class_b", {}).get(month(now), 0))


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
    """これからの k 日に Catalog が必ず使う分の見積もり（毎日の更新の分だけ）。

    週 1 の取り直しの上乗せ・過去の公演・ポスターは、その日の plan が残りを見て決め、足りなければ
    毎日の更新に落とす（または 0 分にする）。だから先の日の分として取っておくのは、毎日の更新の分だけでよい。
    前は週 1 の上乗せ（105 分）も先に数えていたため、過去の公演を多く読んだ数日のあとに、
    31 日の見込みが上限を越え、毎日の更新まで止まった（Catalog #11、2026-10-17 21:27 UTC。
    実際に使ったのは 682 分／1,500 分）。どの日も「今日の分＋先の日の毎日の分」が上限に収まるかを
    その日に確かめるので、上限を越えることはない（test_every_31_day_window_stays_under_the_cap）。"""
    return CATALOG_MINUTES["daily"] * k


def worst_window(by_day: list[int]) -> int:
    """今日を含む 31 日の区切りのうち、いちばん使う区切りの分数（これからの Catalog の見積もりを含む）。
    区切りを k 日先へずらすと、過去の (31 - k) 日分とこれからの k 日分が入る。"""
    n = len(by_day)
    return max(sum(by_day[:n - k]) + future_catalog(k) for k in range(n))


def _stopped(mode: str, by_day, worst, note: str) -> dict:
    return {"run": False, "mode": mode, "catalog_minutes": 1, "discover_minutes": 0, "past_minutes": 0, "past_limit": 0,
            "past_timeout": 1, "poster_minutes": 0, "poster_timeout": 1, "upload_minutes": 0, "upload_timeout": 1,
            "past_index": False, "used_31d": sum(by_day) if by_day is not None else None, "worst_31d": worst, "note": note}


def plan(by_day: list[int] | None, mode: str) -> dict:
    """今日の取得を動かしてよいか、どの mode で、下位の処理（過去の公演・ポスター）に何分渡すか（dec-crawl-tiers）。
    分数が読めなかったとき（by_day が None）は、毎日の更新（1〜3）だけにする。"""
    cap = CAPS["actions_minutes_31d"]
    core = CATALOG_MINUTES["daily"]
    if by_day is None and mode in ("index", "replay", "drill", "stories"):
        # 索引だけの手動実行・再生・予行・本文は急がない。分数が読めないなら動かさない（毎日の実行に任せる）
        return _stopped(mode, by_day, None, "Actions の分数が読めなかったので、索引だけ・再生・戻す予行・本文の実行はしない")
    if by_day is None:
        out = _stopped("daily", by_day, None, "Actions の分数が読めなかったので、毎日の更新だけにする")
        return {**out, "run": True, "catalog_minutes": core, "discover_minutes": DISCOVER_MINUTES}
    worst = worst_window(by_day)
    # worst に入っているのは、今日までに使った分と、明日からの毎日の更新の見積もり。今日の毎日の更新の分は、ここで別に取っておく
    room = cap - worst - core
    # 下位の処理と手で動かすものが使ってよい分（毎日の更新の取り置きを食わないよう、余白を残す）
    spare = room - BACKGROUND_MARGIN
    if mode in ("replay", "drill"):
        need = REPLAY_MINUTES if mode == "replay" else DRILL_MINUTES
        what = "再生" if mode == "replay" else "戻す予行"
        if spare < need:
            return _stopped(mode, by_day, worst, f"Actions の分数が上限 {cap} 分に届く見込みなので、{what}はしない"
                            f"（毎日の更新の取り置きと余白 {BACKGROUND_MARGIN} 分を残すと {max(spare, 0)} 分しか無い）")
        return {**_stopped(mode, by_day, worst, ""), "run": True}
    if mode == "stories":
        minutes = min(STORIES_MAX_MINUTES, spare - STORIES_AFTER_MINUTES)
        if minutes < 10:
            return _stopped(mode, by_day, worst, f"Actions の分数が上限 {cap} 分に届く見込みなので、本文は取らない")
        return {**_stopped(mode, by_day, worst, ""), "run": True, "past_minutes": minutes,
                "past_limit": int(minutes * 60 / PAST_SECONDS_PER_PAGE), "past_timeout": minutes + 5}
    if mode == "index":
        # 索引だけの手動実行（q-index-load-now）。取り直しも過去の公演も読まない。毎日の分をまるごと取っておく
        if room < 0:
            return _stopped(mode, by_day, worst, f"Actions の分数が上限 {cap} 分に届く見込みなので、今日は動かさない")
        return {**_stopped(mode, by_day, worst, ""), "run": True}
    if room < 0:
        return _stopped(mode, by_day, worst, f"Actions の分数が上限 {cap} 分に届く見込みなので、今日は動かさない")
    note = ""
    if mode == "weekly" and spare < WEEKLY_EXTRA:
        mode, note = "daily", "週 1 の取り直しの分が無いので、毎日の更新だけにする（新しい公演の発見は毎日の更新でする）"
    if mode == "weekly":
        spare -= WEEKLY_EXTRA
    # 4 過去の公演の補完（読み取り・D1 へ入れる・名前の索引）
    past = min(PAST_MAX_MINUTES, spare - AFTER_PAST_MINUTES - PAST_INDEX_MINUTES)
    if past < 10:
        past = 0
    if past:
        spare -= past + AFTER_PAST_MINUTES + PAST_INDEX_MINUTES
    # 5 過去の公演のポスター（取る分と R2 に入れる分。残りが少なければ取らない）
    poster = min(POSTER_MAX_MINUTES, (spare - POSTER_AFTER_MINUTES) // 2) if spare - POSTER_AFTER_MINUTES >= 20 else 0
    if poster:
        spare -= poster + POSTER_AFTER_MINUTES
    upload = min(POSTER_UPLOAD_MAX_MINUTES, spare) if spare >= 3 else 0
    return {"run": True, "mode": mode,
            # 取り直しの段の時間の上限。毎日は見積もり（15 分）を越えない。週 1 は見積もりの 2 倍まで（最低 10 分）
            "catalog_minutes": core if mode == "daily" else max(10, min(CATALOG_MINUTES[mode] * 2, 240,
                                                                       CATALOG_MINUTES[mode] + spare + WEEKLY_EXTRA)),
            "discover_minutes": DISCOVER_MINUTES,
            "past_minutes": past, "past_limit": int(past * 60 / PAST_SECONDS_PER_PAGE), "past_timeout": past + 5 if past else 1,
            "past_index": bool(past),
            "poster_minutes": poster, "poster_timeout": poster + POSTER_AFTER_MINUTES if poster else 1,
            "upload_minutes": upload, "upload_timeout": upload + 3 if upload else 1,
            "used_31d": sum(by_day), "worst_31d": worst, "note": note}


def planned_minutes(p: dict) -> int:
    """計画どおりに動いたとき、今日のこのジョブが使う分の上限（毎日の更新の見積もり＋下位の処理の上限）。"""
    if not p["run"]:
        return 1
    extra = (WEEKLY_EXTRA if p["mode"] == "weekly" else 0)
    past = p["past_minutes"] + AFTER_PAST_MINUTES + PAST_INDEX_MINUTES if p["past_minutes"] else 0
    poster = p["poster_minutes"] + POSTER_AFTER_MINUTES if p["poster_minutes"] else 0
    return CATALOG_MINUTES["daily"] + extra + past + poster + p["upload_minutes"]


# ── この実行の段ごとの時間（日次更新の 15 分の見積もりを実測で確かめる。dec-crawl-tiers）──
# 下位の処理（4・5）の段。これ以外の段は毎日の更新（1〜3）として数える
BACKGROUND_STEPS = ("Fetch posters of past stages", "Upload posters to R2", "Read past stage pages",
                    "Deliver the new past stages to D1", "Put the name index of the past stages into R2")


def run_steps(repo: str, token: str, run_id: str, get=_get) -> list[tuple[str, int]]:
    """この実行のジョブの段と秒数（終わった段だけ）。"""
    out = []
    for j in get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100", token).get("jobs", []):
        for st in j.get("steps") or []:
            a, b = _ts(st.get("started_at")), _ts(st.get("completed_at"))
            if a and b and st.get("conclusion") != "skipped":
                out.append((st.get("name") or "", max(0, int((b - a).total_seconds()))))
    return out


def record_run(data: Path, run_id: str, mode: str, steps: list[tuple[str, int]], now: dt.datetime | None = None) -> dict:
    """段ごとの秒数を控え（data/free_tier/usage.json の runs）に残し、毎日の更新の分と下位の処理の分に分けて返す。"""
    core = sum(t for n, t in steps if not n.startswith(BACKGROUND_STEPS))
    back = sum(t for n, t in steps if n.startswith(BACKGROUND_STEPS))
    row = {"date": today(now), "mode": mode, "core_seconds": core, "background_seconds": back,
           "steps": {n: t for n, t in steps}}
    u = load(data)
    runs = u.setdefault("runs", {})
    runs[str(run_id)] = row
    for k in sorted(runs, key=lambda k: runs[k].get("date", ""))[:-60]:      # 新しい 60 回だけ残す
        runs.pop(k, None)
    save(data, u)
    return row


def core_minutes_measured(data: Path) -> list[float]:
    """控えにある毎日の更新（mode が daily）の、1〜3 の段の分数（新しい順）。後の書き戻しの段（約 1 分）は入らない。"""
    runs = load(data).get("runs", {})
    rows = sorted((r for r in runs.values() if r.get("mode") == "daily"), key=lambda r: r.get("date", ""), reverse=True)
    return [round(r["core_seconds"] / 60, 1) for r in rows]


_ROWS_READ = re.compile(r'"rows_read"\s*:\s*(\d+)')


def rows_read_in_logs(paths: list[Path]) -> int:
    """取得の段が D1 に送った文の rows_read の合計（wrangler d1 execute の出力を残したログから）。"""
    n = 0
    for p in paths:
        try:
            n += sum(int(x) for x in _ROWS_READ.findall(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return n


def d1_reads_24h(info_path: Path | None) -> int | None:
    """wrangler d1 info --json の rows_read_24h（D1 の分析から、Worker と取得の合計。直近 24 時間）。読めなければ None。"""
    if not info_path or not info_path.exists():
        return None
    try:
        v = json.loads(info_path.read_text(encoding="utf-8")).get("rows_read_24h")
    except (ValueError, AttributeError):
        return None
    return int(v) if isinstance(v, (int, float)) else None


# ── 点検 ──
def check(data: Path, by_day: list[int] | None, worker_usage: dict | None,
          now: dt.datetime | None = None, d1_reads: int | None = None) -> list[dict]:
    """使った量と上限の表。worker_usage は D1 の usage 表（k -> n）。読めなかったものは -1（注意にする）。"""
    u = load(data)
    rows = [
        ("D1 の書き込み（今日・取得の分）", int(u["d1_writes"].get(today(now), 0)), CAPS["d1_writes_day"], FREE["d1_writes_day"]),
        ("R2 の保存（バイト）", r2_bytes(u), CAPS["r2_bytes"], FREE["r2_bytes"]),
        ("R2 の Class A（今月）", r2_class_a(u, now), CAPS["r2_class_a_month"], FREE["r2_class_a_month"]),
        ("R2 の Class B（今月・Worker と取得の合計）",
         -1 if worker_usage is None else int(worker_usage.get(f"r2_get:{month(now)}", 0)) + r2_class_b(u, now),
         CAPS["r2_class_b_month"], FREE["r2_class_b_month"]),
    ]
    rows.insert(1, ("D1 の読み出し（直近 24 時間・Worker と取得の合計）", -2 if d1_reads is None else d1_reads,
                    CAPS["d1_reads_day"], FREE["d1_reads_day"]))
    if by_day is not None:
        rows.insert(0, ("GitHub Actions（直近 31 日・分）", sum(by_day), CAPS["actions_minutes_31d"],
                        FREE["actions_minutes_month"]))
    else:
        rows.insert(0, ("GitHub Actions（直近 31 日・分）", -1, CAPS["actions_minutes_31d"], FREE["actions_minutes_month"]))
    # used: -1 読めなかった（本当のエラー）・-2 読めなかったが、無くても取得の守りは効く（D1 の分析。鍵に権限が無いなど）
    return [{"what": w, "used": n, "cap": c, "free": f, "ok": (n >= 0 and n <= c * WARN) or n == -2,
             "unread": n < 0} for w, n, c, f in rows]


def notify(title: str, body: str, repo: str | None = None, token: str | None = None, get=_get, post=None) -> str:
    """持ち主に知らせる（このリポジトリの issue）。開いている同じ題の issue があればコメントを足す。
    前は段を失敗させて GitHub のメールで知らせていたが、保存まで済んだ実行も失敗に見えた（dec-crawl-tiers）。"""
    repo = repo or os.environ.get("GITHUB_REPOSITORY", "")
    token = token or os.environ.get("GITHUB_TOKEN", "")
    if not repo or not token:
        return "skipped"
    post = post or _post
    api = f"https://api.github.com/repos/{repo}/issues"
    try:
        same = [i for i in get(f"{api}?state=open&per_page=100", token) if i.get("title") == title and "pull_request" not in i]
        if same:
            post(f"{api}/{same[0]['number']}/comments", token, {"body": body})
            return "commented"
        post(api, token, {"title": title, "body": body})
        return "opened"
    except Exception as e:                                          # noqa: BLE001
        print(f"::warning::持ち主に知らせる issue を書けなかった（{type(e).__name__}: {e}）")
        return "failed"


def _post(url: str, token: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


NOTIFY_TITLE = "無料枠の注意（取得）"


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
    ap.add_argument("--mode", default="daily", choices=["daily", "weekly", "index", "replay", "drill", "stories"])
    ap.add_argument("--d1-usage", type=Path, help="wrangler d1 execute --json の出力（usage 表）")
    ap.add_argument("--d1-info", type=Path, help="wrangler d1 info --json の出力（rows_read_24h）")
    ap.add_argument("--d1-logs", type=Path, nargs="*", default=[], help="取得の段が残した wrangler d1 execute の出力")
    ap.add_argument("--run-mode", default="", help="check: この実行の mode（段ごとの時間を控えるとき）")
    a = ap.parse_args()
    now = utc_now()
    by_day = _actions(now)
    if a.action == "plan":
        p = plan(by_day, a.mode)
        print(json.dumps(p, ensure_ascii=False))
        _out({k: v for k, v in p.items() if k in ("run", "mode", "catalog_minutes", "discover_minutes", "past_minutes",
                                                   "past_limit", "past_timeout", "poster_minutes", "poster_timeout",
                                                   "upload_minutes", "upload_timeout", "past_index")})
        if p["note"]:
            print(f"::warning::{p['note']}")
        if not p["run"]:
            # 予算が足りずに止めるのはエラーではない（使う前に止めるのが守り）。失敗にはせず、毎日の更新が止まったときだけ知らせる
            # 失敗にしないのは、あとの段が run を見て止まる新しい catalog.yml（TAGURI_PLAN_SOFT_STOP=1）のときだけ。
            # 古い catalog.yml はこの段の失敗であとの段を止めている
            if a.mode in ("daily", "weekly") and os.environ.get("TAGURI_PLAN_SOFT_STOP") == "1":
                notify(NOTIFY_TITLE, f"{today(now)} の取得（{a.mode}）を動かさなかった: {p['note']}\n\n"
                       f"直近 31 日 {p.get('used_31d')} 分・見込み {p.get('worst_31d')} 分（上限 {CAPS['actions_minutes_31d']} 分）")
                return 0
            # 手で動かすもの（再生・予行・本文・索引だけ）は、動かなかったことが押した人に見えるよう失敗にする
            # （あとの段は、この段の失敗で止まる）
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
    reads24 = d1_reads_24h(a.d1_info)
    rows = check(a.data, by_day, worker, now, reads24)
    lines = ["| 項目 | 使った量 | 上限（たぐり） | 無料枠 | |", "|---|---:|---:|---:|---|"]
    for r in rows:
        used = "読めなかった" if r["used"] < 0 else f"{r['used']:,}"
        lines.append(f"| {r['what']} | {used} | {r['cap']:,} | {r['free']:,} | {'ok' if r['ok'] and not r['unread'] else '**注意**'} |")
    crawl_reads = rows_read_in_logs(a.d1_logs)
    if a.d1_logs:
        u = load(a.data)
        u.setdefault("d1_reads", {})[today(now)] = int(u.get("d1_reads", {}).get(today(now), 0)) + crawl_reads
        save(a.data, u)
        lines.append(f"| D1 の読み出し（この実行の取得の段） | {crawl_reads:,} | | | |")
    # この実行の段ごとの時間（毎日の更新の見積もり 15 分を実測で確かめる）
    timing = []
    repo, token, run_id = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_RUN_ID", "")
    if repo and token and run_id and a.run_mode:
        try:
            row = record_run(a.data, run_id, a.run_mode, run_steps(repo, token, run_id), now)
            past = core_minutes_measured(a.data)
            timing = ["", f"この実行（{a.run_mode}）: 毎日の更新（1〜3）の段 {row['core_seconds'] / 60:.1f} 分・"
                      f"下位の処理（4・5）の段 {row['background_seconds'] / 60:.1f} 分（このあとの書き戻しの約 1 分は入らない）",
                      f"毎日の更新の実測（新しい順、{len(past)} 回）: {', '.join(str(x) for x in past[:10])} 分"
                      f" ── 見積もりは {CATALOG_MINUTES['daily']} 分",
                      "", "| 段 | 秒 |", "|---|---:|", *[f"| {n} | {t} |" for n, t in row["steps"].items()]]
        except Exception as e:                                      # noqa: BLE001
            timing = ["", f"段ごとの時間が読めなかった（{type(e).__name__}）"]
    print("\n".join(lines + timing))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## 無料枠\n\n" + "\n".join(lines + timing) + "\n")
    errors = [r for r in rows if r["used"] == -1]
    warns = [r for r in rows if not r["ok"] and r["used"] != -1]
    for r in rows:
        if r["used"] == -2:
            print(f"::warning::{r['what']} が読めなかった（鍵に D1 の分析を読む権限が無いかもしれない）")
    for r in warns:
        print(f"::warning::無料枠の注意: {r['what']} が上限の {int(WARN * 100)}% を越えた（{r['used']:,} / {r['cap']:,}）")
    if warns:
        notify(NOTIFY_TITLE, f"{today(now)} の点検で、上限の {int(WARN * 100)}% を越えたもの:\n\n"
               + "\n".join(f"- {r['what']}: {r['used']:,} / {r['cap']:,}（無料枠 {r['free']:,}）" for r in warns))
    # 本当のエラー（数えが読めない）は隠さない。上限の手前の注意は、保存まで済ませるために失敗にしない
    for r in errors:
        print(f"::error::無料枠の点検: {r['what']} が読めなかった")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
