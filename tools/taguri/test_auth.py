#!/usr/bin/env python3
"""復旧コード認証（auth.py）の検査。

    python3 tools/taguri/test_auth.py

DBとpepperを一時ディレクトリに差し替えて実行する（本物の`data/auth/`・
`~/.config/taguri/auth_pepper.txt`には触れない）。
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))

ok = fail = 0


def check(name: str, cond: bool, got=None) -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  NG  {name}" + (f"  ← {got!r}" if got is not None else ""))


_tmpdir = tempfile.TemporaryDirectory()
_tmp = Path(_tmpdir.name)

import auth as AU                                                  # noqa: E402
AU.DB_PATH = _tmp / "auth.db"
AU.PEPPER_PATH = _tmp / "auth_pepper.txt"

# --- 復旧コードの生成 ---
code1 = AU.generate_recovery_code()
code2 = AU.generate_recovery_code()
check("復旧コードは毎回違う", code1 != code2)
check("復旧コードはダッシュ区切り", "-" in code1)

# --- 登録・解決 ---
uid1, is_new1 = AU.access_or_register(code1)
check("初回はis_new=True", is_new1)
uid1_again, is_new1_again = AU.access_or_register(code1)
check("同じコードなら同じ利用者ID", uid1 == uid1_again)
check("2回目はis_new=False", not is_new1_again)

uid2, _ = AU.access_or_register(code2)
check("別のコードなら別の利用者ID", uid1 != uid2)

# 表記ゆれ（大文字・ダッシュの有無）を吸収する
uid1_upper, _ = AU.access_or_register(code1.upper())
check("大文字で打っても同じ利用者ID", uid1 == uid1_upper)
uid1_nodash, _ = AU.access_or_register(code1.replace("-", ""))
check("ダッシュを抜いても同じ利用者ID", uid1 == uid1_nodash)

# --- セッション ---
token = AU.create_session(uid1)
check("発行直後のセッションは解決できる", AU.resolve_session(token) == uid1)
AU.revoke_session(token)
check("失効させたセッションは解決できない", AU.resolve_session(token) is None)
check("存在しないトークンはNone", AU.resolve_session("no-such-token") is None)

# --- /recover ---
recovered_uid = AU.recover(code1, ip="127.0.0.1")
check("正しいコードでrecoverできる", recovered_uid == uid1)

try:
    AU.recover("zzzz-zzzz-zzzz-zzzz-zzzz-zzzz-zzzz", ip="127.0.0.2")
    check("存在しないコードはAuthErrorになるはず", False)
except AU.AuthError:
    check("存在しないコードはAuthError", True)

# 試行回数の上限（同一IPからの連打）
hit_limit = False
for _ in range(AU.RECOVER_MAX_ATTEMPTS + 2):
    try:
        AU.recover("aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-aaaa", ip="203.0.113.9")
    except AU.AuthError as e:
        if "試行回数" in str(e):
            hit_limit = True
            break
check("recoverの連打は試行回数の上限に当たる", hit_limit)

# --- 連携コード（端末追加） ---
link = AU.create_link_code(uid1)
check("連携コードは6桁の数字", link.isdigit() and len(link) == 6)
linked_uid = AU.redeem_link_code(link, ip="198.51.100.10")
check("連携コードで同じ利用者IDに到達する", linked_uid == uid1)

try:
    AU.redeem_link_code(link, ip="198.51.100.10")
    check("使い切った連携コードは再利用できないはず", False)
except AU.AuthError:
    check("使い切った連携コードは再利用できない", True)

# 期限切れ
link2 = AU.create_link_code(uid1)
conn = AU._db()
conn.execute("UPDATE link_codes SET expires_at = ? WHERE code = ?", (time.time() - 1, link2))
conn.commit()
conn.close()
try:
    AU.redeem_link_code(link2, ip="198.51.100.11")
    check("期限切れの連携コードは使えないはず", False)
except AU.AuthError:
    check("期限切れの連携コードは使えない", True)

try:
    AU.redeem_link_code("000000", ip="198.51.100.12")
    check("存在しない連携コードはAuthErrorになるはず", False)
except AU.AuthError:
    check("存在しない連携コードはAuthError", True)

# --- セキュリティレビュー2026-08-28 指摘①への回帰テスト ---
# 「外れの推測は該当コードのattemptsに触れない」ことを利用して総当たりしても、
# IPベースのレート制限で止まることを確認する。
link3 = AU.create_link_code(uid1)
brute_ip = "198.51.100.20"
blocked = False
for i in range(AU.LINK_REDEEM_MAX_ATTEMPTS + 3):
    guess = f"{(int(link3) + 1 + i) % 1_000_000:06d}"  # 正解は絶対に踏まない外れ値
    try:
        AU.redeem_link_code(guess, ip=brute_ip)
    except AU.AuthError as e:
        if "試行回数" in str(e):
            blocked = True
            break
check("連携コードの総当たりはレート制限で止まる（指摘①の修正）", blocked)
# レート制限に引っかかった後は、正しいコードを打っても弾かれる（IP単位で止めているため）
try:
    AU.redeem_link_code(link3, ip=brute_ip)
    check("レート制限中は正しいコードも通らないはず", False)
except AU.AuthError:
    check("レート制限中は正しいコードも通らない", True)
# 別のIPからなら、まだ有効な同じコードで正常に連携できる
still_valid = AU.redeem_link_code(link3, ip="198.51.100.21")
check("レート制限は他のIPには影響しない", still_valid == uid1)

# --- セキュリティレビュー2026-08-28 指摘②への回帰テスト ---
# `/auth/start`の新規登録連打がレート制限で止まることを確認する。
register_ip = "198.51.100.30"
register_blocked = False
for _ in range(AU.REGISTER_MAX_ATTEMPTS + 3):
    try:
        AU.throttle_register(register_ip)
    except AU.AuthError:
        register_blocked = True
        break
check("新規登録の連打はレート制限で止まる（指摘②の修正）", register_blocked)

# --- 削除 ---
AU.delete_user(uid2)
try:
    AU.recover(code2, ip="127.0.0.3")
    check("削除した利用者はrecoverできないはず", False)
except AU.AuthError:
    check("削除した利用者はrecoverできない", True)

_tmpdir.cleanup()

print(f"{ok} 件通過・{fail} 件失敗")
sys.exit(1 if fail else 0)
