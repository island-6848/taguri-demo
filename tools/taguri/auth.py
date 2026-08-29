#!/usr/bin/env python3
"""アカウント登録なしの認証（#000008・[セキュリティ規約](../../docs/000007-taguri-security-rules.md) C13〜C15）。標準ライブラリのみ。

## 全体の形

利用者を識別する秘密は**復旧コード** 1 つだけである。メールアドレスもパスワードも
無い。初めて訪れた端末には、その場でランダムな復旧コードを生成して 1 回だけ見せ、
以後は Cookie に載る**セッショントークン**（復旧コードとは別の乱数）だけで日常の
利用が続く。

- `generate_recovery_code()` ── 128bit の乱数を読める形式で 1 回だけ発行する
- `access_or_register(code)` ── コードから利用者 ID を導出し、無ければ作る
  （登録も復旧も同じ経路。「初めて見るコードか」の違いでしかない）
- `create_session` / `resolve_session` ── 日常用の Cookie を発行・検証する
- `create_link_code` / `redeem_link_code` ── 別端末を追加するための、短命の連携コード

## なぜ「12 単語」ではなくこの形式か

セキュリティ規約 C13 は「BIP39 のシードフレーズと同じ考え方」と書いたが、実装は
2048 語の単語リストを持つ代わりに、**128bit の乱数を Base32 で読める文字列にした
もの**を採用した。単語リストを手で用意すると欠落・重複の検査ができず、標準ライブラリ
だけでは正しさを確かめる辞書も無い（`tools/README.md` の「標準ライブラリだけで動かす」
方針）。Base32 は `base64.b32encode` で標準ライブラリから直接得られ、128bit の強度は
単語方式と変わらない。**セキュリティ規約が約束しているのは強度であって具体的な符号化
方式ではない**ため、この置き換えは規約に反しない。

## 利用者 ID の作り方 ── パスワード方式との違い

通常のパスワード認証は「利用者ごとの salt を先に引いて、それと入力を照合する」が、
ここには「利用者ごと」を引く手がかり（ユーザー名）が無い。**復旧コードそのものが
唯一の手がかりである。** そこで、salt は利用者ごとではなく**アプリ全体で 1 つの
固定値（pepper）**にし、`user_id = scrypt(code, pepper)` を毎回同じ入力から同じ
出力になる形で計算する。これで「そのコードを持つ人がどの利用者か」を、登録時も
復旧時も同じ 1 行の計算で解決できる。

**pepper を固定にしても弱くならない。** salt を利用者ごとに変える理由は、同じ
パスワードが使い回されたときにレインボーテーブル（辞書の総当たり結果の使い回し）を
防ぐためだが、**復旧コードは 128bit の乱数で、使い回しも推測も現実的に起こらない。**
pepper はコードそのものではなく `~/.config/taguri/auth_pepper.txt`（権限 600）に
保管し、コードとは別に守る。

## 連携コードとの強度の違い

復旧コード（128bit）は総当たりが現実的に不可能なので、遅いハッシュ（scrypt）を
かけても実害は薄いが、**連携コード（6 桁・約 20bit）はそうではない。** ここは強度
ではなく、**短い有効期限（`LINK_TTL_SEC`）・1 回限り・試行回数の上限**の 3 つで
守る（C14）。
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "auth" / "auth.db"
PEPPER_PATH = Path.home() / ".config" / "taguri" / "auth_pepper.txt"

RECOVERY_CODE_BYTES = 16          # 128bit
SESSION_TTL_SEC = 60 * 60 * 24 * 365   # 日常鍵は長期間有効（毎回打ち直させない）
LINK_TTL_SEC = 10 * 60            # 連携コードは10分で失効
LINK_MAX_ATTEMPTS = 5             # 1コードあたりの成功後は即失効するため、実質は
                                   # 「発行から失効までに何度アクセスされたか」の記録用
RECOVER_MAX_ATTEMPTS = 10
RECOVER_WINDOW_SEC = 10 * 60
# **連携コードは6桁(100万通り)しかない。** 復旧コード(128bit)と違い、レート制限
# だけが総当たりを止める唯一の壁なので、復旧コードより厳しく絞る（セキュリティ
# レビュー2026-08-28の指摘①への対応）。
LINK_REDEEM_MAX_ATTEMPTS = 10
LINK_REDEEM_WINDOW_SEC = 10 * 60
# **`/auth/start`（新規登録）にもレート制限を足す。** 無いと、Cookie無しで
# 叩くたびに重いscrypt計算とDB行作成が走り、CPU枯渇・DB肥大化の両方に
# 悪用できてしまう（同レビューの指摘②への対応）。
REGISTER_MAX_ATTEMPTS = 20
REGISTER_WINDOW_SEC = 10 * 60

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


class AuthError(Exception):
    """認証まわりの失敗（試行回数超過・無効なコード等）。"""


def _pepper() -> bytes:
    """アプリ全体で共有する固定saltを読む。無ければ作る（初回起動時のみ）。"""
    if PEPPER_PATH.exists():
        return bytes.fromhex(PEPPER_PATH.read_text().strip())
    PEPPER_PATH.parent.mkdir(parents=True, exist_ok=True)
    value = secrets.token_bytes(32)
    PEPPER_PATH.write_text(value.hex())
    PEPPER_PATH.chmod(0o600)
    return value


def generate_recovery_code() -> str:
    """128bitの乱数を、4文字ごとに区切ったBase32文字列として返す。"""
    raw = secrets.token_bytes(RECOVERY_CODE_BYTES)
    b32 = base64.b32encode(raw).decode("ascii").rstrip("=").lower()
    return "-".join(b32[i:i + 4] for i in range(0, len(b32), 4))


def _normalize_code(code: str) -> str:
    return code.strip().lower().replace("-", "").replace(" ", "")


def derive_user_id(code: str) -> str:
    """復旧コードから、決定的に（毎回同じ入力→同じ出力で）利用者IDを作る。"""
    normalized = _normalize_code(code)
    digest = hashlib.scrypt(
        normalized.encode("ascii", errors="ignore"),
        salt=_pepper(),
        n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=16,
    )
    return digest.hex()


def _db() -> sqlite3.Connection:
    is_new_dir = not DB_PATH.parent.exists()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if is_new_dir:
        # **ディレクトリ自体も締める。** ファイルを600にしても、ディレクトリが
        # 既定のumask任せ（他ユーザーから一覧できる）では中途半端になる
        # （セキュリティレビュー2026-08-28の指摘⑤への対応）。
        DB_PATH.parent.chmod(0o700)
    is_new = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at REAL NOT NULL,
            last_seen_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS link_codes (
            code TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0
        );
        -- **利用場面ごとに`bucket`で分けた、汎用のレート制限記録。**
        -- 元は`recover_attempts`という/recover専用のテーブルだったが、
        -- 連携コード総当たり(指摘①)・新規登録連打(指摘②)にも同じ仕組みが
        -- 要ることが分かったため、bucket列を足して使い回す形にした。
        CREATE TABLE IF NOT EXISTS rate_limit_attempts (
            bucket TEXT NOT NULL,
            ip TEXT NOT NULL,
            at REAL NOT NULL
        );
        """
    )
    conn.commit()
    if is_new:
        DB_PATH.chmod(0o600)
    return conn


def access_or_register(code: str) -> tuple[str, bool]:
    """復旧コードから利用者IDを解決する。初めてのコードならその場で登録する。

    戻り値: (user_id, is_new)
    """
    user_id = derive_user_id(code)
    conn = _db()
    try:
        cur = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        is_new = cur.fetchone() is None
        if is_new:
            conn.execute(
                "INSERT INTO users (user_id, created_at) VALUES (?, ?)",
                (user_id, time.time()),
            )
            conn.commit()
        return user_id, is_new
    finally:
        conn.close()


def create_session(user_id: str) -> str:
    """日常用のセッショントークンを発行する（Cookieに載せる値）。"""
    token = secrets.token_urlsafe(32)
    conn = _db()
    try:
        now = time.time()
        conn.execute(
            "INSERT INTO sessions (session_token, user_id, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?)",
            (token, user_id, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def resolve_session(session_token: str) -> str | None:
    """セッショントークンから利用者IDを引く。期限切れ・存在しなければNone。"""
    if not session_token:
        return None
    conn = _db()
    try:
        cur = conn.execute(
            "SELECT user_id, created_at FROM sessions WHERE session_token = ?",
            (session_token,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        user_id, created_at = row
        if time.time() - created_at > SESSION_TTL_SEC:
            conn.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
            conn.commit()
            return None
        conn.execute(
            "UPDATE sessions SET last_seen_at = ? WHERE session_token = ?",
            (time.time(), session_token),
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def revoke_session(session_token: str) -> None:
    conn = _db()
    try:
        conn.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
        conn.commit()
    finally:
        conn.close()


def _throttle(bucket: str, ip: str, max_attempts: int, window_sec: int) -> None:
    """`bucket`ごとに、同一IPからの試行を数える。超えていればAuthErrorを投げる。

    **呼び出し側は、重い処理（scryptの計算等）より先にこれを呼ぶこと。** 先に
    弾くことで、レート制限自体を回避する目的でのDoS（重い処理を無制限に
    起こさせる）も防げる。

    **`BEGIN IMMEDIATE`で書き込みロックを先に取る。** 「件数を数えてから
    足す」を2つの別トランザクションのままにすると、同時多発リクエストが
    同じ「まだ上限未満」を読んでしまい、上限をわずかに超えられる
    （セキュリティレビュー2026-08-28の指摘④）。
    """
    conn = _db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        now = time.time()
        conn.execute(
            "DELETE FROM rate_limit_attempts WHERE bucket = ? AND ip = ? AND at < ?",
            (bucket, ip, now - window_sec),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limit_attempts WHERE bucket = ? AND ip = ?",
            (bucket, ip),
        ).fetchone()[0]
        if count >= max_attempts:
            conn.rollback()
            raise AuthError("試行回数の上限を超えました。しばらく待ってから試してください。")
        conn.execute(
            "INSERT INTO rate_limit_attempts (bucket, ip, at) VALUES (?, ?, ?)",
            (bucket, ip, now),
        )
        conn.commit()
    finally:
        conn.close()


def throttle_register(ip: str) -> None:
    """`/auth/start`の新規登録用。呼び出し側（serve.py）が、コード生成の前に呼ぶ。"""
    _throttle("register", ip, REGISTER_MAX_ATTEMPTS, REGISTER_WINDOW_SEC)


def recover(code: str, ip: str) -> str:
    """`/recover`の実装本体。試行回数を超えていればAuthErrorを投げる（C14）。

    見つからないコードでも「無効」とだけ返し、存在するかどうかを区別しない
    （利用者IDの存在を外部から探れないようにする）。
    """
    _throttle("recover", ip, RECOVER_MAX_ATTEMPTS, RECOVER_WINDOW_SEC)

    user_id = derive_user_id(code)
    conn = _db()
    try:
        row = conn.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise AuthError("復旧コードが正しくありません。")
    return user_id


def create_link_code(user_id: str) -> str:
    """既存端末で「この端末を追加」を押したときの、6桁の一時コードを発行する。"""
    conn = _db()
    try:
        now = time.time()
        conn.execute(
            "DELETE FROM link_codes WHERE expires_at < ?", (now,)
        )
        for _ in range(10):
            code = f"{secrets.randbelow(1_000_000):06d}"
            exists = conn.execute(
                "SELECT 1 FROM link_codes WHERE code = ? AND used = 0 AND expires_at >= ?",
                (code, now),
            ).fetchone()
            if exists is None:
                break
        else:
            raise AuthError("一時コードの発行に失敗しました。もう一度お試しください。")
        conn.execute(
            "INSERT INTO link_codes (code, user_id, created_at, expires_at, used, attempts) "
            "VALUES (?, ?, ?, ?, 0, 0)",
            (code, user_id, now, now + LINK_TTL_SEC),
        )
        conn.commit()
    finally:
        conn.close()
    return code


def redeem_link_code(code: str, ip: str) -> str:
    """新しい端末でコードを入力したときの検証。成功したら使い切りにする（C14）。

    **`ip`は必須。** 連携コードは6桁(100万通り)しかなく、`code`列は主キーの
    完全一致検索なので、外れを引いた推測は該当コードの行に一切触れない
    （`attempts`列はコードを知っている前提の記録にしかならず、総当たり対策
    にはならない）。**総当たりを止めているのはこのIPベースのレート制限だけ**
    である（セキュリティレビュー2026-08-28の指摘①への対応）。
    """
    _throttle("link_redeem", ip, LINK_REDEEM_MAX_ATTEMPTS, LINK_REDEEM_WINDOW_SEC)
    conn = _db()
    try:
        row = conn.execute(
            "SELECT user_id, expires_at, used, attempts FROM link_codes WHERE code = ?",
            (code,),
        ).fetchone()
        if row is None:
            raise AuthError("連携コードが正しくありません。")
        user_id, expires_at, used, attempts = row
        if used or time.time() > expires_at or attempts >= LINK_MAX_ATTEMPTS:
            raise AuthError("連携コードの有効期限が切れているか、無効化されています。")
        conn.execute(
            "UPDATE link_codes SET attempts = attempts + 1 WHERE code = ?", (code,)
        )
        conn.execute(
            "UPDATE link_codes SET used = 1 WHERE code = ?", (code,)
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def delete_user(user_id: str) -> None:
    """復旧コードによる本人確認のあとに呼ぶ、完全削除（R7）。

    このモジュールが持つ認証情報（users/sessions/link_codes）のみを消す。
    利用者本体のデータ（観劇記録等、別モジュールが持つ）はここでは扱わない。
    """
    conn = _db()
    try:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM link_codes WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
