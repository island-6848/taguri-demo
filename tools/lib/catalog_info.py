"""公演カタログがいつのものかを、日付と件数だけで答える（中身は出さない）。

公開版のサーバーは S3 から公演カタログを取り込んで動く。**EC2 が無く、毎日の作り直しが
止まっているかもしれない**（docs/knowledge の no-ec2・q-catalog-source）。S3 に入れない人でも、
公開の `/api/health` を開けばカタログの古さが分かるように、次の手がかりを残して返す。

- `uploaded_at`   … S3 にカタログが置かれた時刻（取り込むときに S3 から読む）
- `newest_file`   … カタログの中でいちばん新しいファイルの更新時刻（tar に残る時刻）
- `scan_date`     … 公演一覧を最後に取り直した日（`candidates_scan.json`）
- `upcoming`      … 楽日が今日以降の公演の件数（古いカタログほど減っていく）

返すのは日付と件数だけ。題名・人名・利用者に関わる値は返さない。
"""
from __future__ import annotations

import datetime
import json
import tarfile
import threading
import time
from pathlib import Path

INFO_NAME = ".catalog-info.json"
JST = datetime.timezone(datetime.timedelta(hours=9))
_CACHE: dict = {"at": 0.0, "key": None, "value": None}
_LOCK = threading.Lock()
CACHE_SEC = 600


def _iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(timespec="seconds")


def archive_info(archive: Path) -> dict:
    """tar の中でいちばん新しいファイルの時刻と、ファイルの数。"""
    newest = 0.0
    n = 0
    with tarfile.open(archive) as tf:
        for m in tf.getmembers():
            if m.isfile():
                n += 1
                newest = max(newest, float(m.mtime or 0))
    return {"newest_file": _iso(newest), "files": n}


def write_info(data_dir: Path, info: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / INFO_NAME).write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")


def _period_end(period: str) -> datetime.date | None:
    """`2026/03/14〜2026/03/29` や `2026/03/14 - 2026/03/29` の楽日。読めなければ None。"""
    import re
    dates = re.findall(r"(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})", period or "")
    if not dates:
        return None
    y, m, d = (int(x) for x in dates[-1])
    try:
        return datetime.date(y, m, d)
    except ValueError:
        return None


def _upcoming(review: Path, today: datetime.date) -> dict:
    out = {}
    for name in ("candidates", "calendar", "favourites"):
        f = review / f"{name}.jsonl"
        n = 0
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    end = _period_end(json.loads(line).get("period") or "")
                except (json.JSONDecodeError, AttributeError):
                    continue
                if end and end >= today:
                    n += 1
        out[name] = n
    return out


def describe(data_dir: Path, today: datetime.date | None = None) -> dict:
    """カタログの日付と件数。**10 分は使い回す**（ヘルスチェックは頻繁に来る）。"""
    today = today or datetime.datetime.now(JST).date()
    info_file = data_dir / INFO_NAME
    key = (str(data_dir), today.isoformat(), info_file.stat().st_mtime if info_file.exists() else None)
    with _LOCK:
        if _CACHE["key"] == key and time.monotonic() - _CACHE["at"] < CACHE_SEC:
            return dict(_CACHE["value"])
    review = data_dir / "review"
    out: dict = {"present": (review / "candidates.jsonl").is_file()}
    try:
        stored = json.loads(info_file.read_text(encoding="utf-8")) if info_file.exists() else {}
    except (OSError, json.JSONDecodeError):
        stored = {}
    for k in ("uploaded_at", "newest_file", "installed_at"):
        if isinstance(stored.get(k), str):
            out[k] = stored[k]
    try:
        scan = json.loads((review / "candidates_scan.json").read_text(encoding="utf-8"))
        if isinstance(scan.get("date"), str):
            out["scan_date"] = scan["date"][:10]
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    out["upcoming"] = _upcoming(review, today) if out["present"] else {}
    newest = max((v for k, v in out.items() if k in ("uploaded_at", "newest_file", "scan_date")), default=None)
    if newest:
        try:
            day = datetime.date.fromisoformat(newest[:10])
            out["age_days"] = (today - day).days
        except ValueError:
            pass
    with _LOCK:
        _CACHE.update(at=time.monotonic(), key=key, value=dict(out))
    return out


def clear_cache() -> None:
    with _LOCK:
        _CACHE.update(at=0.0, key=None, value=None)
