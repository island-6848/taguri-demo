#!/usr/bin/env python3
"""D1 の利用者の記録を、Time Travel（無料で 7 日）より長く残す（S31、q-d1-backup・q-offsite-backup）。

    python3 cloudflare/scripts/backup_d1.py backup --data data     # 書き出し → 確かめる → 暗号化 → R2 → 古い分を消す
    python3 cloudflare/scripts/backup_d1.py drill  --data tmp      # いちばん新しい控えを新しい D1 に戻して数を比べる（予行）

取得の機械（非公開の taguri-crawler の GitHub Actions）で毎日動かす。公開のリポジトリでは動かさない
（ログに利用者の数などが出るため）。要るもの: 環境変数 CLOUDFLARE_API_TOKEN・CLOUDFLARE_ACCOUNT_ID
（取得と同じもの）と BACKUP_PASSPHRASE（暗号化の合言葉。起案者が作り、別の場所にも控える。
無くすと控えは二度と読めない）。

- 書き出すのは利用者の記録の表だけ。公演カタログ・推薦の索引など毎日作り直せる表（DERIVED）と、
  ログインのセッション・パスキーの一時的な問い（戻したあとは入り直してもらう）は書き出さない。
  新しい表は自動で「書き出す側」に入る（入れ忘れで記録が控えから漏れないように）
- 書き出した SQL を手元の SQLite に読み込んで、表ごとの行数を D1 と比べてから暗号化する
- 暗号化は gpg の合言葉方式（AES-256）。R2 には暗号化したものだけを置く（控え専用の入れ物 taguri-backup の
  backup/d1/ の下。2026-10-18 まではポスターと同じ入れ物だった。Worker にはこの入れ物の結び付けが無い）
- 置くのは 30 日分。それより古いものは消す。消した人の記録も、この 30 日のあいだは控えに残る
  （説明と削除の画面に書く）
- R2 の保存量と書き込み回数は free_tier.py の数えに足す（無料枠の上限の手前で止まるのは取得と同じ）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import free_tier as FT                                             # noqa: E402
import wrangler_pin                                                # noqa: E402

DB_NAME = "taguri-demo"
# 控えは専用の入れ物に置く（起案者の指示 2026-10-18「分けましょう」、issue #73）。Worker にはこの入れ物の
# 結び付け（binding）が無いので、画面の側からは読めも消せもしない。無ければ最初の控えのときに作る（ensure_bucket）
BUCKET = "taguri-backup"
LIFECYCLE_DAYS = 35            # 入れ物の決まりでも消す（本体は KEEP_DAYS の 30 日で消す。消し損ねの二重の守り）
PREFIX = "backup/d1/"
KEEP_DAYS = 30
# 毎日作り直せる表と、控えに入れない一時的な表。これ以外はすべて書き出す。
DERIVED = {
    "catalogue", "rec_meta", "rec_stage", "rec_credit", "rec_people", "rec_cache", "rec_gram",
    "stage_label", "past_stage", "poster", "usage", "sessions", "webauthn_challenges", "_cf_KV", "_cf_METADATA",
}
DRILL_DB = "taguri-restore-drill"
# ensure_bucket が毎回使う R2 の操作（数えに足す。issue #139）。作る（PutBucket）と決まりを付ける（PutBucketLifecycleConfiguration）は
# Class A、あるかを見る GET は Class B として数える（公式の分類は確かめきれていないので、多めの側に数える）
ENSURE_CLASS_A = 2
ENSURE_CLASS_B = 1


def wrangler(*args: str, capture: bool = True) -> str:
    cmd = [*wrangler_pin.wrangler_cmd(), *args]      # lockfile の版（issue #131）
    r = subprocess.run(cmd, cwd=HERE.parent, capture_output=capture, text=True, check=False)
    if r.returncode != 0:
        # 中身（SQL や行）は出さない。wrangler のエラーの最後だけ。失敗した SQL 文を wrangler が引用することがあるので、
        # SQL の文らしい行は落とす（Actions のログに利用者の記録が残らないように）
        # --json のときの wrangler は、失敗の説明を stdout に出す
        tail = "\n".join(l for l in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines()
                         if not re.search(r"\b(INSERT|UPDATE|DELETE|CREATE|VALUES)\b", l, re.I))
        raise RuntimeError(f"wrangler {args[0]} {args[1] if len(args) > 1 else ''} が失敗した: {tail[-400:]}")
    return r.stdout or ""


def remote_json(db: str, sql: str) -> list[dict]:
    out = wrangler("d1", "execute", db, "--remote", "--json", "--command", sql)
    return json.loads(out)[0]["results"]


def user_tables(names: list[str]) -> list[str]:
    # _cf_ で始まる表は D1 自身のもので、読めない（_cf_KV・_cf_METADATA のほかにも増えることがある）
    return sorted(n for n in names if n not in DERIVED and not n.startswith(("sqlite_", "_cf_")))


def remote_tables(db: str) -> list[str]:
    return [r["name"] for r in remote_json(db, "SELECT name FROM sqlite_master WHERE type='table'")]


def remote_counts(db: str, tables: list[str]) -> dict[str, int]:
    # D1 は UNION ALL でつなげる数に上限がある（too many terms in compound SELECT）。1 行の列として数える
    sql = "SELECT " + ", ".join(f'(SELECT count(*) FROM "{t}") AS "{t}"' for t in tables)
    row = remote_json(db, sql)[0]
    return {t: int(row[t]) for t in tables}


def local_counts(sql_text: str, tables: list[str]) -> dict[str, int]:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(sql_text)
        return {t: con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
    finally:
        con.close()


def local_tables(sql_text: str) -> list[str]:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(sql_text)
        return [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    finally:
        con.close()


def drill_writes(sql_text: str) -> int:
    """控えを新しい D1 に入れたときの書き込みの行数の見込み。D1 は表の行と索引の行を 1 つずつ数えるので
    （d1-free-limits）、表ごとに 行数 × (1 + 索引の数) を足す（主キー・UNIQUE の自動の索引も入れる。多めの側）。"""
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(sql_text)
        total = 0
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
            rows = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
            idx = con.execute("SELECT count(*) FROM sqlite_master WHERE type='index' AND tbl_name=?", (t,)).fetchone()[0]
            total += rows * (1 + idx)
        return total
    finally:
        con.close()


def compare(want: dict[str, int], got: dict[str, int]) -> list[str]:
    """数が合わない表の説明（合っていれば空）。書き出しのあいだに増えた行は許す（減るのは許さない）。"""
    return [f"{t}: D1 {want[t]} 行・控え {got.get(t, 0)} 行" for t in sorted(want) if got.get(t, 0) < want[t]]


def gpg(args: list[str], data: bytes, passphrase: str) -> bytes:
    # 合言葉は標準入力の 1 行目で渡す（コマンドの引数やファイルに書かない）
    r = subprocess.run(["gpg", "--batch", "--yes", "--quiet", "--pinentry-mode", "loopback", "--passphrase-fd", "0", *args],
                       input=passphrase.encode() + b"\n" + data, capture_output=True, check=False)
    if r.returncode != 0:
        raise RuntimeError("gpg が失敗した（合言葉が違う・壊れた控えなど）")
    return r.stdout


def encrypt(data: bytes, passphrase: str) -> bytes:
    return gpg(["--symmetric", "--cipher-algo", "AES256", "--s2k-digest-algo", "SHA512", "--s2k-count", "65011712",
                "--compress-algo", "zlib", "-o", "-"], data, passphrase)


def decrypt(data: bytes, passphrase: str) -> bytes:
    return gpg(["--decrypt", "-o", "-"], data, passphrase)


def _url(account: str, key: str) -> str:
    return f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/buckets/{BUCKET}/objects/" + urllib.parse.quote(key)


def _api(account: str, token: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/buckets{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def ensure_bucket(account: str, token: str) -> dict:
    """控えの入れ物が無ければ作り、LIFECYCLE_DAYS 日で消す決まりを付ける。何をしたかを返す。
    決まりを付けられなくても控えは続ける（本体が 30 日で消す）。"""
    done = {}
    try:
        _api(account, token, f"/{BUCKET}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        _api(account, token, "", "POST", {"name": BUCKET})
        done["created"] = BUCKET
    try:
        rule = {"id": "expire-backups", "enabled": True, "conditions": {"prefix": PREFIX},
                "deleteObjectsTransition": {"condition": {"type": "Age", "maxAge": LIFECYCLE_DAYS * 86400}}}
        _api(account, token, f"/{BUCKET}/lifecycle", "PUT", {"rules": [rule]})
        done["lifecycle_days"] = LIFECYCLE_DAYS
    except urllib.error.HTTPError as e:
        done["lifecycle_error"] = e.code
    return done


def r2_put(account: str, token: str, key: str, body: bytes) -> None:
    req = urllib.request.Request(_url(account, key), data=body, method="PUT",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()


def r2_get(account: str, token: str, key: str) -> bytes:
    req = urllib.request.Request(_url(account, key), headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def r2_delete(account: str, token: str, key: str) -> None:
    req = urllib.request.Request(_url(account, key), method="DELETE", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        r.read()


def backup_keys(u: dict) -> list[str]:
    return sorted(k for k in u["r2"]["sizes"] if k.startswith(PREFIX))


def to_drop(keys: list[str], today: str, keep_days: int = KEEP_DAYS) -> list[str]:
    """保存の期間を過ぎた控えの名前（backup/d1/YYYY-MM-DD.sql.gpg）。"""
    edge = (dt.date.fromisoformat(today) - dt.timedelta(days=keep_days)).isoformat()
    return [k for k in keys if k[len(PREFIX):len(PREFIX) + 10] < edge]


def backup(data: Path, *, export=None, counts=None, put=r2_put, delete=r2_delete, ensure=ensure_bucket,
           now: dt.datetime | None = None) -> dict:
    account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    passphrase = os.environ.get("BACKUP_PASSPHRASE", "")
    if not passphrase:
        return {"skipped": "BACKUP_PASSPHRASE が無いので控えを作らない"}
    now = now or FT.utc_now()
    u = FT.load(data)
    if FT.r2_class_a(u, now) + 1 + ENSURE_CLASS_A + len(to_drop(backup_keys(u), FT.today(now))) > FT.CAPS["r2_class_a_month"]:
        return {"skipped": "R2 の書き込み回数が今月の上限に近いので控えを作らない"}
    if export is None:
        tables = user_tables(remote_tables(DB_NAME))
        want = remote_counts(DB_NAME, tables)
        # 暗号化する前の SQL は data/ の外（一時ディレクトリ）に書き、失敗しても必ず消す。
        # data/ は取得の state ブランチに丸ごと保存されるので、途中で落ちると平文が git に残る（安全の点検 2026-10-17）
        flags = [x for t in tables for x in ("--table", t)]
        with tempfile.TemporaryDirectory(prefix="taguri-backup-") as tmp:
            out = Path(tmp) / "backup.sql"
            wrangler("d1", "export", DB_NAME, "--remote", "--output", str(out), *flags)
            sql_text = out.read_text(encoding="utf-8")
    else:
        tables, want, sql_text = export()
    got = (counts or local_counts)(sql_text, tables)
    bad = compare(want, got)
    if bad:
        raise RuntimeError("控えの行数が D1 と合わない: " + "、".join(bad))
    body = encrypt(sql_text.encode("utf-8"), passphrase)
    if FT.r2_bytes(u) + len(body) > FT.CAPS["r2_bytes"]:
        return {"skipped": "R2 の保存量が上限に近いので控えを作らない"}
    key = f"{PREFIX}{FT.today(now)}.sql.gpg"
    m = FT.month(now)
    # 送る前に数える: 控えの PUT 1 回と、入れ物の確かめ（ensure_bucket）の分。入れ物の決まり（lifecycle）は毎日付け直すので
    # Class A 2 回（作る・決まりを付ける。作らない日も多めに数える）と、入れ物があるかの GET を Class B 1 回（issue #139）
    u["r2"]["class_a"][m] = FT.r2_class_a(u, now) + 1 + ENSURE_CLASS_A
    u["r2"].setdefault("class_b", {})[m] = FT.r2_class_b(u, now) + ENSURE_CLASS_B
    bucket = ensure(account, token)
    try:
        put(account, token, key, body)
        u["r2"]["sizes"][key] = len(body)
        dropped = []
        for old in to_drop(backup_keys(u), FT.today(now)):
            try:
                delete(account, token, old)
            except Exception:                                    # noqa: BLE001
                continue        # 消せなかったものは保存の数えに残す（少なく数えない）
            u["r2"]["sizes"].pop(old, None)
            dropped.append(old)
    finally:
        FT.save(data, u)
    return {"key": key, "bucket": BUCKET, **bucket, "bytes": len(body), "tables": len(tables), "rows": sum(want.values()),
            "dropped": len(dropped), "kept": len(backup_keys(u))}


def drill(data: Path, get=r2_get) -> dict:
    """いちばん新しい控えを取り出し、合言葉で開き、新しい D1 に入れて、表ごとの行数を本番と比べる。
    終わったら（失敗しても）その D1 を消す。かかった時間を返す（復元の手順書に書く数字）。"""
    account, token = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    passphrase = os.environ.get("BACKUP_PASSPHRASE", "")
    if not passphrase:
        return {"skipped": "BACKUP_PASSPHRASE が無い"}
    # 取得の作業データを使わずに、今日から 3 日前までの控えを新しい順に探す
    t0 = time.monotonic()
    key, body = None, b""
    for back in range(4):
        key = f"{PREFIX}{(FT.utc_now().date() - dt.timedelta(days=back)).isoformat()}.sql.gpg"
        try:
            body = get(account, token, key)
            break
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    if not body:
        return {"ok": False, "mismatch": ["この 4 日の控えが R2 に無い"]}
    sql_text = decrypt(body, passphrase).decode("utf-8")
    t_open = time.monotonic() - t0
    # D1 の 1 日の書き込み（10 万行）は口座全体で、予行の新しい D1 への書き込みも同じ枠から出る（issue #139）。
    # 入れる前に手元の SQLite で数え、上限を越える控えは D1 に入れず、手元で開けて数が合うかだけを確かめる
    est = drill_writes(sql_text)
    if est > FT.CAPS["drill_d1_writes"]:
        tables = user_tables(local_tables(sql_text))
        backed = local_counts(sql_text, tables)
        return {"key": key, "ok": True, "d1_skipped": f"D1 への書き込みが {est:,} 行の見込みで、上限 {FT.CAPS['drill_d1_writes']:,} 行を越える"
                "ので、新しい D1 には入れず手元の SQLite で開けるかだけを確かめた",
                "estimated_writes": est, "tables": len(tables), "rows": sum(backed.values()), "seconds_open": round(t_open, 1)}
    # 復号した平文は data/ の外に置く（backup と同じ）。消すのは下の finally
    tmp = Path(tempfile.mkdtemp(prefix="taguri-drill-"))
    path = tmp / "drill.sql"
    path.write_text(sql_text, encoding="utf-8")
    try:
        try:
            wrangler("d1", "delete", DRILL_DB, "--skip-confirmation")
        except RuntimeError:
            pass
        wrangler("d1", "create", DRILL_DB)
        t1 = time.monotonic()
        wrangler("d1", "execute", DRILL_DB, "--remote", "--yes", "--file", str(path))
        t_load = time.monotonic() - t1
        tables = user_tables(remote_tables(DRILL_DB))
        restored = remote_counts(DRILL_DB, tables)
        backed = local_counts(sql_text, tables)
    finally:
        path.unlink(missing_ok=True)
        tmp.rmdir()
        try:
            wrangler("d1", "delete", DRILL_DB, "--skip-confirmation")
        except RuntimeError:
            pass
    bad = compare(backed, restored)
    return {"key": key, "ok": not bad, "mismatch": bad, "tables": len(tables), "rows": sum(restored.values()),
            "seconds_open": round(t_open, 1), "seconds_load": round(t_load, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("what", choices=("backup", "drill"))
    ap.add_argument("--data", type=Path, required=True)
    a = ap.parse_args()
    got = backup(a.data) if a.what == "backup" else drill(a.data)
    print(json.dumps(got, ensure_ascii=False))
    if got.get("d1_skipped"):
        print(f"::warning::{got['d1_skipped']}")
    return 1 if got.get("ok") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
