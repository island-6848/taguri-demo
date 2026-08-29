#!/usr/bin/env python3
"""観た作品に ◎○△× を付ける画面（「たぐり」の評価入力）。

企画書 5 章「画面をどう動かすか」で決めた形の実装である。静的 HTML では SQLite に
書き戻せないため、127.0.0.1 に一時プロセスを立て、画面を閉じたら落とす。守りは
5 章の 6 点をそのまま実装している。

  1. API キーは画面に渡さない ── この画面は Claude API を呼ばない
  2. 待ち受けは 127.0.0.1 に固定する（同一 LAN から観劇記録を読めないようにする）
  3. 起動ごとに乱数のトークンを作り、すべての要求で必須にする
  4. 受け付ける操作は列挙したものだけ
  5. 外部への取得は、押した本人が明示的に求めた 1 件だけ行う（`mail_hints` ──
     題名を直すための手がかりを、押したメール 1 通ぶんだけ Gmail へ読みに行く。
     本文は保存しないと決めているため、キャッシュを持たずその場で読む。
     それ以外の場面でこの過程が外部へ取得することはない）
  6. 常駐しない（画面を閉じるか、無操作が続いたら落ちる）

**評価の単位は「作品」であって「観た回」ではない。** 同じ作品を 5 回観たとき、回ごとに
◎○△× を付けさせると、評価の中身が「その日の演者の演技の質」になってしまう。作品との
相性を聞きたいので、**同じ上演期間の複数回は 1 つの作品として束ね、評価は 1 回だけ**
付ける。**観た回数それ自体は、宣言より強い行動の証拠として別に数える。**

**「観た／観ていない」は回ごとに持つ。** 買ったが行けなかった回があるためで、実データにも
「2 公演買って 1 回は行かなかった」例がある。作品への評価（◎○△×）と同じ列に混ぜない。

**逆に、1 回の購入が複数の演目にまたがることもある。** セット券と交互上演のプログラムで、
実データに 5 件あった（〈セット券〉「20の物語」の「ナディラ」「煙草のハイ…」、デカローグの
プログラム A〜E）。**演目ごとに別の作品として評価を付けられるようにする。** ただし
「空想題材3劇『Kappa』〜題材5『河童』より〜」のように引用が原作の表記である場合は
分けてはいけないので、**機械は候補を出すだけにして、画面で直せるようにする。**

**クレジット（人名一覧）は絶対に表示しない。** #000006 の V24（理由に出た作り手名のうち
本人が「知らなかった」と答えるものが 2 割以上あるか）は、当事者が人名一覧を読んだ時点で
永久に測れなくなる。この画面が出すのは題名・日付・劇場だけである。

使い方:
    python3 tools/review/rate_performances.py

保存先は data/review/ratings.db（端末内のみ。リポジトリには入れない）。
"""
from __future__ import annotations

import argparse
import collections
import http.server
import json
import platform
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import webbrowser
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "tickets"))
import corrections as CX                                           # noqa: E402
from extract_performances import (NOT_A_TITLE, NOT_A_TITLE_PARTS,  # noqa: E402
                                  body_text, is_theater)  # 判定は 1 か所に置く
from scan_ticket_mail import Gmail                                  # noqa: E402

SRC = ROOT / "data" / "tickets" / "performances.jsonl"
DB = ROOT / "data" / "review" / "ratings.db"

# 段階（◎○△×）と、段階でないもの。企画書 4 章のとおり「まだ判断できない」は
# 段階の隣に並べず、集計では欠測として扱う。
GRADES = ["◎", "○", "△", "×"]
UNDECIDED = "まだ判断できない"
VERDICTS = GRADES + [UNDECIDED]
CHOSEN = ["自分で選んだ", "人に誘われた"]

# 同じ題名でも、これ以上日が離れていれば別の公演として扱う。企画書 3 章に
# 「再演されても演出や配役が変わって別の作品になる」と書いてあるので、
# 毎年上演される定番（作品1 など）を 1 つに束ねてはいけない。
RUN_GAP_DAYS = 90
# 題名の鍵が一方に含まれるだけの組は、**上演日がこれ以内なら同じ作品**として束ねる。
# 実データの 13 組で判定した結果から決めた ── 「unrato#13『受取人不明 ADDRESS UNKNOWN』」と
# 「受取人不明」は 3 日差で同じ公演、「Song Show「Ivory」」と「Ivory」は 1 日差で同じ公演。
# 一方「作品1」と「作品1 Eternal」は 71 日差で**別の演目**なので、
# 90 日では束ねてしまう。**冠と副題の違いか、別演目かを題名から判別できないため、
# 日数で切る。** この 7 日はその 13 組に合わせて決めた数字である（V16）。
CONTAIN_GAP_DAYS = 7

IDLE_LIMIT = 120.0  # 秒。この間まったく要求が来なければ落ちる


# ---------------------------------------------------------------- 題名の束ね方

def norm(s: str) -> str:
    """表示用に全角英数を半角へ寄せる。保存する題名は元のままにする。"""
    return unicodedata.normalize("NFKC", s or "").strip()


_CROWN = re.compile(r"^[〈<（(【\[].{0,12}?[〉>）)】\]]\s*")
_DROP = re.compile(r"[『』「」【】〈〉\[\]（）()・･,，\.。\s\-−–—~〜/／:：!！?？'\"“”’]")


def title_key(title: str) -> str:
    """同じ作品かどうかを見るための鍵。

    〈セット券〉【Premium限定】のような冠と、記号・空白を落として比べる。
    **完全ではない** ── 「unrato#13『受取人不明 ADDRESS UNKNOWN』」と「受取人不明」は
    同じ作品だが、この鍵では別になる。束ね方は画面に日付ごと出すので、誤りは目で分かる。
    """
    return _DROP.sub("", _CROWN.sub("", norm(title))).lower()


def is_work(title: str) -> bool:
    """評価を聞ける題名か。

    `NOT_A_TITLE` は「汎用の規則が題名として拾ってしまう、題名でない語」で、
    **抽出の失敗**である（extract_performances.py のコメント）。実データでは
    「決済完了の」が 18 通あり、束ねると 18 回観た作品のように見えてしまう。
    **評価を聞く画面に抽出の失敗を並べない。**
    """
    t = norm(title)
    # **正規化してから判定する。** 語のリストは半角で書かれているので、
    # 全角の題名（「Ｚｅｐｐ」）が素通りしていた。実データで 1 件効いた。
    return bool(t) and t not in {norm(x) for x in NOT_A_TITLE} and is_theater(t)


# セット券・交互上演のプログラムを、演目ごとに分けるための規則。
# 「〜◯◯より〜」は原作の表記なので分けない（実データの Kappa・ピーチ）。
_ORIGINAL = re.compile(r"[〜~～]\s*[^〜~～]{0,30}(?:より|原作)[^〜~～]{0,10}[〜~～]?\s*$")
_PROGRAM = re.compile(r"プログラム[A-Za-z0-9]\s*[（(]([^）)]+)[）)]\s*$")
_QUOTED = re.compile(r"[「『]([^」』]{2,60})[」』]")


def detect_programs(title: str) -> list[str]:
    """1 回の購入に複数の演目が含まれていそうなら、その並びを返す。空なら分けない。

    **候補を出すだけである。** 題名から演目を切り出すのは確実にはできないので、
    誤りは画面から直せるようにしてある（探すのは機械、確定は人）。実データ 261 件で
    誤検出なし・5 件を分割した。
    """
    n = norm(title)
    if _ORIGINAL.search(n):
        return []                      # 「〜題材5『河童』より〜」は原作の表記
    m = _PROGRAM.search(n)
    if m:                              # 「プログラムA(デカローグ1「…」、デカローグ3「…」)」
        parts = [p.strip() for p in re.split(r"[、,]", m.group(1)) if p.strip()]
        return parts if len(parts) >= 2 else []
    q = _QUOTED.findall(n)
    if "セット" in n and len(q) >= 2:   # 「〈セット券〉…「企画名」 「演目A」「演目B」」
        return q[1:] if len(q) >= 3 else q
    return []


def programs_of(r: dict, splits: dict[str, list[str]]) -> list[str]:
    """この購入が指す演目の並び。人が直したものがあれば、それを優先する。

    優先の順は **① 2 つ以上に分けた指定 → ② 題名の直し → ③ 自動の分割 → ④ 抽出の題名。**

    ②は `fixes` 表が受け持つ（`tools/tickets/corrections.py`）。**`splits` に 1 行だけ
    書く形も「題名の直し」として残す** ── 旧い画面がその形で保存しており、消すと
    それまでに直した分が抽出結果に戻ってしまう。新しい画面は `fixes` に書くので、
    同じ回に両方あることはない（題名を保存するときに 1 行の `splits` を消している）。
    """
    sp = splits.get(r["uid"]) or []
    if len(sp) >= 2:
        return sp
    title = r.get("title_eff") or r["title"]
    if len(sp) == 1 and not (r.get("fixed") or {}).get("title"):
        title = sp[0]
    auto = detect_programs(title)
    return auto if auto else [title]


# 抽出が題名として拾ってしまった、題名でない語。**本来は
# extract_performances.py の NOT_A_TITLE に入るべきもので、ここは暫定の置き場である。**
# 消さずに「題名を確かめてほしいもの」として出す ── 実データでは、この語が付いた 4 件の
# うち 1 件は本物の演劇（劇団劇団4）だった。黙って落とすと、その 1 件が消える。
SUSPECT_TITLES = {
    "マルチコピー機", "買うだけ", "チケットを表示する", "チケットを表示",
    "予約/購入履歴", "払込・引換票番号(13桁)", "引換票番号(13桁)",
}


# 案内文から拾った題名は、**語の一覧ではなく部分一致で落とす。** 決め打ちの一覧は
# 次の発行元で必ず漏れる。語は抽出側（NOT_A_TITLE_PARTS）と同じものを使う。
SUSPECT_PARTS = NOT_A_TITLE_PARTS + ("チケットを表示", "買うだけ")


def is_suspect(title: str, rows: list[dict] | None = None) -> bool:
    """本人が直す必要がある行か。**題名だけでなく、抽出の印と日付でも判定する。**

    - 案内文の語を含む／決め打ちの一覧に当たる
    - 上演日を決められず、受信日をそのまま置いている（`date_unsure`、または受信日と同じ）
    - **括弧が閉じていない**（行の折り返しで題名が切れている）

    **人が直した項目については、印を付けない。** 直した後も「確かめてほしい」に
    残り続けると、直したことが画面に反映されていないように見える。
    """
    t = norm(title)
    fixed_t = any((r.get("fixed") or {}).get("title") for r in rows or [])
    if not fixed_t and (t in {norm(x) for x in SUSPECT_TITLES}
                        or any(w in t for w in SUSPECT_PARTS) or unbalanced(t)):
        return True
    for r in rows or []:
        if (r.get("fixed") or {}).get("date"):
            continue
        if r.get("date_unsure"):
            return True
        if r.get("date_eff", r.get("date")) and r.get("date_eff", r.get("date")) == _mail_date(r):
            return True
    return False


# 題名を囲む括弧の対。**閉じていない題名は、抽出が途中で切ったものである** ──
# メール本文の行の折り返しで題名が切れる形で、実データ 129 作品のうち 24 件がこれだった
# （「NODA・MAP第28回公演『華氏マイナス320°」「ファーム・ホール』」）。
# `SUSPECT_TITLES` の決め打ちの一覧では 5 件しか拾えていなかった。
_PAIRS = (("『", "』"), ("「", "」"), ("【", "】"), ("〈", "〉"), ("（", "）"), ("(", ")"),
          ("[", "]"))


def unbalanced(title: str) -> bool:
    return any(title.count(a) != title.count(b) for a, b in _PAIRS)


def _pdate(r: dict) -> str:
    """この購入の上演日。**人が直していればその日付。** 抽出した `date` は残してある。"""
    return r.get("date_eff") or r.get("date") or ""


def _pvenue(r: dict) -> str:
    return r.get("venue_eff") or r.get("venue") or ""


def _ptime(r: dict) -> str:
    """この購入の開演時刻。**人が直していればその時刻。** 抽出した `time` は残してある。"""
    return r.get("time_eff") or r.get("time") or ""


def _mail_date(r: dict) -> str:
    try:
        return parsedate_to_datetime(r["mail_date"]).date().isoformat()
    except (KeyError, TypeError, ValueError):
        return ""


def _days(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


# ---------------------------------------------------------------- 作品の一覧

def load_purchases(fixes: dict | None = None) -> list[dict]:
    """performances.jsonl から、評価の対象になる購入（＝観た回）を作る。

    同じ日・同じ時刻の購入は同一の回とみなす（extract_performances --list と同じ）。
    公演日が本文に無いもの（ファンクラブ経由）は、黙って落とさず別枠で持つ。

    **人が直した公演詳細をここで重ねる**（`tools/tickets/corrections.py`）。
    重ねるのは `title_eff` / `date_eff` / `venue_eff` の側だけで、`title` と `date` は
    抽出した値のまま残す ── `data/credits/credits.jsonl` は `(date, mail_title)` を鍵に
    公演ページと結び付いており、**上書きすると直した公演のクレジットが引けなくなる。**

    **人が確定した項目には、機械の除外判定を当てない。** `is_work`（題名でない語・
    演劇でない語の除外）は抽出の失敗を落とすための網であって、当事者が自分で
    書いた題名を却下する道具ではない（探すのは機械、確定は人）。
    """
    if not SRC.exists():
        # **1 件も取り込んでいないのは、初めて使う人の正常な状態である。**
        # ここで止めると `run.py` が 2 段目で終わり、**画面が 1 度も開かない**
        # （2026-08-24、記録を空にして起動して確かめた）。購入確認メールを持って
        # いないことが、システムを使えない理由になってはいけない。
        return []
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").split("\n") if l.strip()]
    if fixes is None:
        # **保存先はこのモジュールの `DB` から開く。** `corrections` 側の既定に任せると、
        # 検査が `R.DB` を一時ディレクトリへ差し替えても本物の DB を読んでしまう
        con = connect()
        try:
            fx = CX.read(con)
        finally:
            con.close()
    else:
        fx = fixes
    gen = CX.title_by_extracted(fx)
    rows = [CX.effective(r, fx, gen) for r in rows]

    def keep(r: dict) -> bool:
        return bool(r["title_eff"]) and (bool(r["fixed"].get("title"))
                                         or is_work(r["title_eff"]))

    best: dict[tuple[str, str], tuple[int, dict]] = {}
    for r in rows:
        if not (r["date_eff"] and keep(r)):
            continue
        k = (r["date_eff"], r.get("time", ""))
        score = len(r["title_eff"]) + (30 if r["venue_eff"] else 0)
        if k not in best or score > best[k][0]:
            best[k] = (score, r)

    out = [dict(r, dated=True) for _, r in best.values()]
    for r in rows:
        # **上演日を人が入れたら、日付不明の枠から出す。** 入れた日付が使われないなら、
        # 入れる意味が無い（`date_eff` があるものは上の枠に入っている）
        if r.get("date_unknown") and not r["date_eff"] and keep(r):
            out.append(dict(r, dated=False))
    return out


def load_works(purchases: list[dict], splits: dict[str, list[str]],
               excluded: set[tuple[str, str]] | None = None,
               merges: dict[str, str] | None = None) -> list[dict]:
    """購入の並びを「作品」に組み替える。

    (1) 人が「舞台ではない」として外した（回, 演目）は、候補に出さない
    (2) 1 つの購入は、演目ごとに複数の作品に属しうる（セット券・交互上演）
    (3) 題名の鍵が同じ回を、上演日が RUN_GAP_DAYS 以内で連なる塊ごとに束ねる
    (4) 公演日が本文に無いものは、題名ごとに別枠で束ねる
    (5) **人が「同じ公演だ」と答えた束ね直しを、最後に当てる**（merges）
    """
    skip = excluded or set()
    dated: dict[str, list[tuple[dict, str]]] = collections.defaultdict(list)
    undated: dict[str, list[tuple[dict, str]]] = collections.defaultdict(list)
    for r in purchases:
        for program in programs_of(r, splits):
            if (r["uid"], program) in skip:
                continue
            (dated if r["dated"] else undated)[title_key(program)].append((r, program))

    works: list[dict] = []
    today = date.today().isoformat()
    for key, members in dated.items():
        members.sort(key=lambda m: _pdate(m[0]))
        run: list[tuple[dict, str]] = []
        for m in members:
            if run and _days(_pdate(run[-1][0]), _pdate(m[0])) > RUN_GAP_DAYS:
                works.append(_work(key, run, today))
                run = []
            run.append(m)
        works.append(_work(key, run, today))
    for key, members in undated.items():
        members.sort(key=lambda m: _mail_date(m[0]))
        works.append(_work(key, members, today, dated=False))

    works = _merge_contained(works)
    works = _apply_merges(works, merges or {})
    works.sort(key=lambda w: (w["bucket"] != "past", w["last_date"] or ""), reverse=True)
    works.sort(key=lambda w: {"past": 0, "undated": 1, "upcoming": 2}[w["bucket"]])
    return works


def _merge_contained(works: list[dict]) -> list[dict]:
    """題名の鍵が一方に含まれ、上演日が近い作品を 1 つにまとめる。

    同じ公演でも、メールによって冠（団体名・企画名）や副題が付く／付かないがある。
    鍵が違うので通常の束ねでは別作品になる ── 実データで
    「unrato#13『受取人不明 ADDRESS UNKNOWN』」と「受取人不明」が 3 日差で
    別作品に分かれ、**どちらにも ◎ が付いていた。**
    """
    out = list(works)
    merged = True
    while merged:
        merged = False
        for i, a in enumerate(out):
            for j, b in enumerate(out):
                if i >= j or not (a["first_date"] and b["first_date"]):
                    continue
                ka, kb = a["work_key"].rsplit("#", 1)[0], b["work_key"].rsplit("#", 1)[0]
                short, long_ = sorted((ka, kb), key=len)
                if len(short) < 4 or short not in long_ or short == long_:
                    continue
                if _days(a["first_date"], b["first_date"]) > CONTAIN_GAP_DAYS:
                    continue
                keep, drop = (a, b) if len(ka) >= len(kb) else (b, a)
                keep["shows"] = sorted(keep["shows"] + drop["shows"],
                                       key=lambda s: (s["date"], s["time"]))
                keep["times"] = len(keep["shows"])
                ds = [s["date"] for s in keep["shows"] if s["date"]]
                keep["first_date"], keep["last_date"] = (ds[0], ds[-1]) if ds else ("", "")
                out.remove(drop)
                merged = True
                break
            if merged:
                break
    return out


def _apply_merges(works: list[dict], merges: dict[str, str]) -> list[dict]:
    """人が「これは同じ公演だ」と答えた束ね直しを当てる。

    **機械には分からないから人に聞いている。** 鍵が一致するか一方が他方を含む場合は
    `_merge_contained` が自動で束ねるが、表記が違う同じ公演（「ハムレット」と「HAMLET」、
    抽出が途中で切れた題名、副題だけが違うもの）は当たらない。

    **残る側の work_key は変えない。** 束ねると初日が変わりうるが、work_key は
    「題名の鍵＋初日」なので、ここで作り直すと**評価と感想の置き場所が宙に浮く**
    （`_merge_contained` が work_key を作り直していないのと同じ理由）。

    **鎖をたどる。** A を B に、B を C に束ねたときは A も C に入る。**輪になっていたら
    その組だけ諦める** ── 無限に回るより、束ねずに 2 件出したほうが直せる。
    """
    if not merges:
        return works
    by = {w["work_key"]: w for w in works}

    def target(k: str) -> str:
        seen = {k}
        while k in merges:
            k = merges[k]
            if k in seen:
                return ""
            seen.add(k)
        return k

    out = list(works)
    for src_key in list(merges):
        src, dst_key = by.get(src_key), target(src_key)
        dst = by.get(dst_key)
        if src is None or dst is None or src is dst:
            continue
        dst["shows"] = sorted(dst["shows"] + src["shows"],
                              key=lambda s: (s["date"], s["time"]))
        dst["times"] = len(dst["shows"])
        ds = [s["date"] for s in dst["shows"] if s["date"]]
        if ds:
            dst["first_date"], dst["last_date"] = ds[0], ds[-1]
        # **束ねた元の鍵を残す。** 取り消す画面に「何を束ねたか」を出せないと、
        # 押した本人が後から確かめられない
        dst["merged"] = (dst.get("merged") or []) + [
            {"work_key": src_key, "title": src["title_display"]}] + (src.get("merged") or [])
        if src in out:
            out.remove(src)
    return out


def _work(key: str, members: list[tuple[dict, str]], today: str, *,
          dated: bool = True) -> dict:
    """1 作品ぶんの行。members は (購入, 演目名) の並び。"""
    # 演目名は、いちばん情報が多いものを代表にする。**人が直した題名は必ず代表にする** ──
    # 束ねた別の回の抽出結果のほうが長いことがあり、直したのに画面に出ないことになる
    fixed = [p for r, p in members if (r.get("fixed") or {}).get("title") == p]
    label = fixed[0] if fixed else max((p for _, p in members), key=len)
    dates = [_pdate(r) for r, _ in members if _pdate(r)]
    first, last = (dates[0], dates[-1]) if dates else ("", "")
    if not dated:
        bucket = "undated"
    elif last and last <= today:
        bucket = "past"
    elif first and first > today:
        bucket = "upcoming"
    else:
        bucket = "past"  # 上演中（初日を過ぎて楽日が来ていない）は評価を聞ける
    return {
        "work_key": f"{key}#{first or 'undated'}",
        "suspect": is_suspect(label, [r for r, _ in members]),
        "title": label,
        "title_display": norm(label),
        "first_date": first,
        "last_date": last,
        "bucket": bucket,
        "times": len(members),
        # **回ごとに、直す画面が要る情報まで持たせる。** 差出人と件名を出さないと、
        # 当事者は「どのメールを見て直しているのか」が分からない（`app.py` の編集欄）
        "shows": [{
            "uid": r["uid"],
            "program": p,
            "date": _pdate(r),
            "time": _ptime(r),
            "venue": norm(_pvenue(r)),
            "bought_on": _mail_date(r),
            "past": bool(_pdate(r)) and _pdate(r) <= today,
            "subject": r.get("subject") or "",
            "sender": r.get("from") or "",
            "extracted": {"title": r.get("title") or "",
                          "date": r.get("date") or "",
                          "venue": norm(r.get("venue") or ""),
                          "time": r.get("time") or ""},
            "fixed": dict(r.get("fixed") or {}),
        } for r, p in members],
    }


def bought_after_seeing(work: dict, attended: dict[str, int]) -> bool:
    """観たあとに、同じ作品の別の回を買っているか。

    企画書 4 章は「その場で次の回を買った」をチェックで取る設計にしていたが、
    **購入確認メールの受信日と上演日を比べれば分かる。** 新しい入力操作を作る前に、
    その情報を運んでいる経路が既に無いかを見る（2 章の原則）。宣言ではなく
    証拠なので、そのまま強い正の信号として使える。
    """
    seen = sorted(s["date"] for s in work["shows"]
                  if s["date"] and s["past"]
                  and attended.get(f"{s['uid']}|{work['work_key']}", 1))
    if not seen:
        return False
    return any(s["bought_on"] and s["bought_on"] > seen[0] for s in work["shows"])


# ---------------------------------------------------------------- メールの手がかり

_HINT = re.compile(r"(公演名|演目|イベント名|チケット名|作品名|タイトル|title"
                   r"|開演|開場|上演|会場|劇場|ホール|シアター)")
_NOISE = re.compile(r"(番号|決済|クレジット|パスワード|ログイン|様$|^[A-Za-z0-9\-]+$)")


def mail_hints(uid: str, limit: int = 10) -> list[str]:
    """題名を直すための手がかりを、メール本文から拾って返す。

    **抽出が題名を取れなかったとき、正体はほぼ本文に書いてある** ── 実データでは
    「イベント名:しんじゅく酒井祭」「2025/11/8(土) 19:00開演」がそうだった。
    画面に出さないと当事者は直せないので、必要になったときだけ読んで渡す。

    **本文は保存しない**（企画書 2 章）。**2026-08-27 まではここが `data/tickets/bodies/`
    のキャッシュを読むだけの処理だったが、そのキャッシュ自体が本文を無期限に平文で
    残していて約束と食い違っていた**（[000007-taguri-security-review.md]
    (../../docs/000007-taguri-security-review.md)）。キャッシュを廃止したので、
    ここで毎回 Gmail から読みに行く。この操作は「直したい 1 通」を押したときにしか
    起きないので、都度ログインしても実用上の遅さにはならない。
    """
    try:
        gm = Gmail()
        body = body_text(gm, uid)
    except (Exception, SystemExit):
        # 認証やネットワークの失敗は `SystemExit`（`google_oauth.py`）で来ることがあり、
        # `Exception` だけでは拾えない。**読めなかった 1 通のために画面全体を
        # 止めない**という設計（`extract_performances.reparse` と同じ）をここでも守る
        return []
    if not body:
        return []
    text = unicodedata.normalize("NFKC", body)
    lines: list[str] = []
    for raw in text.splitlines():
        ln = re.sub(r"\s+", " ", raw).strip(" >　")
        if 3 <= len(ln) <= 120 and ln not in lines:
            lines.append(ln)
    keyed = [ln for ln in lines if _HINT.search(ln)][:limit]
    if len(keyed) >= 3:
        return keyed
    rest = [ln for ln in lines if ln not in keyed and len(ln) >= 6
            and not _NOISE.search(ln)]
    return (keyed + rest)[:limit]


# ---------------------------------------------------------------- 保存

SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    work_key         TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    first_date       TEXT,
    last_date        TEXT,
    times            INTEGER NOT NULL DEFAULT 1,
    verdict          TEXT,
    chosen           TEXT,
    note_impression  TEXT NOT NULL DEFAULT '',
    note_motive      TEXT NOT NULL DEFAULT '',
    updated_at       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attendance (
    uid              TEXT NOT NULL,
    work_key         TEXT NOT NULL,
    attended         INTEGER NOT NULL DEFAULT 1,
    updated_at       TEXT NOT NULL,
    PRIMARY KEY (uid, work_key)
);
CREATE TABLE IF NOT EXISTS splits (
    uid              TEXT PRIMARY KEY,
    programs         TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS excluded (
    uid              TEXT NOT NULL,
    program          TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    PRIMARY KEY (uid, program)
);
-- **人が「これは同じ公演だ」と確定した束ね直し。**
--
-- 題名の鍵が一致するか、一方が他方を含む場合は `_merge_contained` が自動で束ねるが、
-- **表記が違う同じ公演は機械には分からない**（「ハムレット」と「HAMLET」、
-- 抽出が途中で切れた題名、副題だけが違うもの）。**同じかどうかを知っているのは本人だけ**
-- なので、本人が答えたことを残す。
--
-- **消える側の work_key を鍵にする。** 残る側の work_key は変えない ── work_key は
-- 「題名の鍵＋初日」でできており、束ねて初日が変わるたびに鍵が変わると、
-- **評価と感想の置き場所（works 表）が宙に浮く。**
CREATE TABLE IF NOT EXISTS merges (
    work_key         TEXT PRIMARY KEY,   -- 束ねられて消える側
    into_key         TEXT NOT NULL,      -- 残る側
    updated_at       TEXT NOT NULL
);
-- **公演ページが無い公演のために、人が直に入れた出演者・作り手とポスター。**
--
-- 起案者の報告（2026-08-24）──「どれだけ試してもポスターが違ったり、出演者が取得
-- できなかったりした」。**出演者とポスターは公演ページからしか来ない作りだったので、
-- ページが無い公演では取りようが無かった。** 実測で、材料の無い記録 48 件のうち
-- 15 件を外の公演情報から探して当たったのは 6 件で、「ナディラ」のように
-- **ページ自体が存在しない公演が残る。** そこだけは本人しか知らない。
--
-- **形は公演ページの欄と同じにする**（出演／演出／脚本／スタッフ）。同じ形にしておけば
-- 名簿を作る処理（`measure_nets.parse_credits`）をそのまま通せる ── **手で入れた分に
-- だけ別の読み取り規則を作ると、役職の丸め方が 2 通りになる。**
--
-- **公演ページの分を置き換えるのではなく、足す。** 手で入れたものは本人が確定した
-- 事実だが、ページから取れている分を消す理由にはならない（消したいときは結び付けを外す）。
CREATE TABLE IF NOT EXISTS hand_credits (
    work_key         TEXT PRIMARY KEY,
    fields           TEXT NOT NULL DEFAULT '{}',  -- 役職 → 名前。公演ページの欄と同じ形
    poster           TEXT NOT NULL DEFAULT '',    -- data/review/img の中のファイル名
    updated_at       TEXT NOT NULL
);
-- **回ごとの、推薦には使わないメモ。**（起案者の指示・2026-08-26）
--
-- `works.note_impression`（感想）は作品単位の 1 つの値で、複数回観ていても
-- どの回にも同じ文が出る。「回ごとに書きたい」という話が出たが、感想の欄そのものを
-- 回ごとに分けることはしなかった ── **感想は「今後の推薦の理由」にもつながる材料
-- なので、回ごとに割ると同じ理由が薄まる**（`rating-unit-is-the-object` と同じ判断）。
--
-- 代わりに、**この表は独立させ、推薦の計算（`recommend2.py`・`measure_nets.py`）の
-- どこからも読まない。** 「その日は雨で開演が遅れた」「隣の人が知り合いだった」の
-- ような、その回だけの覚え書きを残す場所である。**「すべて表示」でしか出さない**
-- （`app.page_works` の `group=="visit"` のときだけ）── 作品でまとめた 1 行には、
-- どの回のことかが決まらない。
--
-- 実は昔、回ごとに評価を付けていた `ratings` 表があった（`migrate()` 参照）。
-- **あれは作品ごとの評価に統合して捨てた設計であり、この表はそれの再来ではない。**
-- `ratings` は評価そのもの（推薦に使う）を回ごとに割っていたが、この表は
-- **推薦とは無関係な私的なメモだけ**を持つ。
CREATE TABLE IF NOT EXISTS visit_note (
    uid              TEXT PRIMARY KEY,
    note             TEXT NOT NULL DEFAULT '',
    updated_at       TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    _widen_attendance_key(con)
    con.executescript(SCHEMA)
    con.executescript(CX.SCHEMA)      # 人が直した公演詳細（表の定義は 1 か所に置く）
    _add_stage_id(con)
    _add_venue(con)
    _add_time(con)
    return con


def _add_stage_id(con: sqlite3.Connection) -> None:
    """`works` に公演ページの id を持たせる。**既存の DB には IF NOT EXISTS が効かない。**

    手で足した記録は、これまで題名と日付しか持っていなかった。**同じ公演が手元のデータに
    あるのに、それと結び付いていない** ── ポスターは日付から当て推量で引くしかなく、
    どの公演のことなのかを機械が確かめる術が無かった。**本人が候補から選んだときに、
    どれを選んだのかを残す。**
    """
    have = {r["name"] for r in con.execute("PRAGMA table_info(works)")}
    if "stage_id" not in have:
        with con:
            con.execute("ALTER TABLE works ADD COLUMN stage_id TEXT")


def _add_venue(con: sqlite3.Connection) -> None:
    """`works` に会場を持たせ、**感想の欄に紛れ込んだ会場を移す。**

    ## 何が起きていたか（起案者の報告 2026-08-24）

    ──「手入力で公演を追加した際に、感想の欄に『劇場: 自由劇場』と入ってしまうのはなぜ？」

    **`works` に会場の列が無かったので、手で足すときの会場が感想の列に入れられていた**
    （`app.add_work` が `"劇場: " + 会場` を `note_impression` に書いていた）。
    **しかもその値を読み戻す所はどこにも無い** ── 書くだけで誰も使わない値が、
    本人が読み書きする自由記述の欄を占めていた。

    ## なぜ放置できないか

    **感想の件数が狂う。** 感想が書かれた作品として数えられるので、実データでは
    12 件のうち 2 件がこれだった（本当は 10 件）。

    **推薦の理由に出る。** ◎ を付けた作品の感想は「あなたの言葉」として推薦の理由に
    引用されるので（`impressions.quote_row`）、**「劇場: 自由劇場」が本人の言葉として
    出る。** 実データでは 10 名の作り手がこの引用を持ちうる状態だった。

    ## 直し方

    **会場の列を足して、そこへ移す。** 会場は本人が入力した事実なので捨てない ──
    捨てると、手で足した記録からどこで観たかが失われる。**移したあとの感想は空にする**
    （本人が書いていないものを、書いたことにしない）。
    """
    have = {r["name"] for r in con.execute("PRAGMA table_info(works)")}
    if "venue" not in have:
        with con:
            con.execute("ALTER TABLE works ADD COLUMN venue TEXT NOT NULL DEFAULT ''")
    # **移すのは 1 度だけでよいが、毎回確かめて構わない。** 前置きが付いた行だけを見るので、
    # 本人が書いた感想には触れない（「劇場: 」で始まる感想を人が書く筋はない）
    rows = [dict(r) for r in con.execute(
        "SELECT work_key, note_impression FROM works"
        " WHERE note_impression LIKE '劇場: %'")]
    if not rows:
        return
    with con:
        for r in rows:
            v = r["note_impression"][len("劇場: "):].strip()
            con.execute("UPDATE works SET venue = CASE WHEN trim(venue)='' THEN ? ELSE venue END,"
                        " note_impression='', updated_at=datetime('now','localtime')"
                        " WHERE work_key=?", (v, r["work_key"]))


def _add_time(con: sqlite3.Connection) -> None:
    """`works` に開演時刻を持たせる。

    購入の控えから来る記録は `fixes` 表（`corrections.py`）の "time" で時刻を直せるが、
    **手で足した記録（`add_work`）は購入の控えを持たないので、その仕組みに乗れない。**
    `venue` と同じ理由（`_add_venue` 参照）で、`works` に直接持たせる。
    """
    have = {r["name"] for r in con.execute("PRAGMA table_info(works)")}
    if "time" not in have:
        with con:
            con.execute("ALTER TABLE works ADD COLUMN time TEXT NOT NULL DEFAULT ''")


def _widen_attendance_key(con: sqlite3.Connection) -> None:
    """attendance の主キーを uid から (uid, work_key) へ広げる。

    1 回の購入が複数の演目に属しうるので、uid だけでは足りなくなった。
    既にある行は作品ごとの行として持ち越す（消さない）。
    """
    have = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'").fetchone()
    if not have or "PRIMARY KEY (uid, work_key)" in have["sql"]:
        return
    old = [dict(r) for r in con.execute("SELECT * FROM attendance")]
    with con:
        con.execute("DROP TABLE attendance")
        con.execute("CREATE TABLE attendance (uid TEXT NOT NULL, work_key TEXT NOT NULL,"
                    " attended INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,"
                    " PRIMARY KEY (uid, work_key))")
        con.executemany("INSERT INTO attendance (uid, work_key, attended, updated_at)"
                        " VALUES (:uid, :work_key, :attended, :updated_at)", old)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_works(con: sqlite3.Connection) -> dict[str, dict]:
    return {r["work_key"]: dict(r) for r in con.execute("SELECT * FROM works")}


def read_attendance(con: sqlite3.Connection) -> dict[str, int]:
    """鍵は「回 uid ｜ 作品 work_key」。1 回が 2 演目に属しうるため両方が要る。"""
    return {f"{r['uid']}|{r['work_key']}": r["attended"]
            for r in con.execute("SELECT uid, work_key, attended FROM attendance")}


def read_splits(con: sqlite3.Connection) -> dict[str, list[str]]:
    return {r["uid"]: json.loads(r["programs"])
            for r in con.execute("SELECT uid, programs FROM splits")}


def read_excluded(con: sqlite3.Connection) -> set[tuple[str, str]]:
    """候補から外した（回, 演目）。舞台でないものを機械が拾ったとき人が外す。

    **回ではなく演目の単位で持つ。** セット券で 2 演目のうち片方だけが舞台でない
    ことがあり、回で外すと相方まで消えてしまう。
    """
    return {(r["uid"], r["program"])
            for r in con.execute("SELECT uid, program FROM excluded")}


def save_excluded(con: sqlite3.Connection, pairs: list[tuple[str, str]],
                  excluded: bool) -> None:
    """外す／戻すを（回, 演目）ごとに書く。

    **消さずに残す** ── 戻せなければ誤操作が取り返せない。
    """
    with con:
        if excluded:
            con.executemany(
                "INSERT INTO excluded (uid, program, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(uid, program) DO UPDATE SET updated_at=excluded.updated_at",
                [(u, p, now()) for u, p in pairs])
        else:
            con.executemany("DELETE FROM excluded WHERE uid = ? AND program = ?", pairs)


def read_hand(con: sqlite3.Connection) -> dict[str, dict]:
    """人が手で入れた公演情報（work_key → {"fields": {...}, "poster": "..."}）。

    **壊れた JSON で全体を落とさない。** 1 行が読めなくても、他の記録の学習と表示は
    続けられるべきなので、その行だけ空として扱う。
    """
    out = {}
    for r in con.execute("SELECT work_key, fields, poster FROM hand_credits"):
        try:
            f = json.loads(r["fields"] or "{}")
        except ValueError:
            f = {}
        out[r["work_key"]] = {"fields": f if isinstance(f, dict) else {},
                              "poster": r["poster"] or ""}
    return out


def save_hand(con: sqlite3.Connection, work_key: str, *,
              fields: dict | None = None, poster: str | None = None) -> None:
    """手で入れた公演情報を書く。**渡さなかった側は触らない。**

    ポスターと出演者は別々に直すものなので（絵だけ差し替えたい・名前だけ足したい）、
    **片方を書くともう片方が消える形にしない。**
    """
    if not work_key:
        raise ValueError("work_key が要る")
    with con:
        con.execute("INSERT INTO hand_credits (work_key, fields, poster, updated_at)"
                    " VALUES (?, '{}', '', ?) ON CONFLICT(work_key) DO NOTHING",
                    (work_key, now()))
        if fields is not None:
            con.execute("UPDATE hand_credits SET fields = ?, updated_at = ?"
                        " WHERE work_key = ?",
                        (json.dumps(fields, ensure_ascii=False), now(), work_key))
        if poster is not None:
            con.execute("UPDATE hand_credits SET poster = ?, updated_at = ?"
                        " WHERE work_key = ?", (poster, now(), work_key))
        # **中身が空になった行は残さない。** 消したのに行が残ると、
        # 「手で入れてある」と読める印が画面に出続ける
        con.execute("DELETE FROM hand_credits WHERE work_key = ?"
                    " AND poster = '' AND fields IN ('{}', '')", (work_key,))


def read_merges(con: sqlite3.Connection) -> dict[str, str]:
    """人が確定した束ね直し（消える側の work_key → 残る側の work_key）。"""
    return {r["work_key"]: r["into_key"]
            for r in con.execute("SELECT work_key, into_key FROM merges")}


def save_merge(con: sqlite3.Connection, work_key: str, into_key: str) -> None:
    """「これは同じ公演だ」を残す。**押し直せる**（あとから取り消せる）。"""
    if work_key == into_key:
        raise ValueError("同じ記録どうしは束ねられない")
    with con:
        con.execute("INSERT INTO merges (work_key, into_key, updated_at) VALUES (?,?,?)"
                    " ON CONFLICT(work_key) DO UPDATE SET"
                    " into_key=excluded.into_key, updated_at=excluded.updated_at",
                    (work_key, into_key, now()))


def delete_merges(con: sqlite3.Connection, *, into_key: str = "",
                  work_key: str = "") -> int:
    """束ね直しを取り消す。**戻せなければ誤操作が取り返せない**（除外と同じ扱い）。"""
    with con:
        if work_key:
            return con.execute("DELETE FROM merges WHERE work_key=?", (work_key,)).rowcount
        return con.execute("DELETE FROM merges WHERE into_key=?", (into_key,)).rowcount


def save_split(con: sqlite3.Connection, uid: str, programs: list[str]) -> list[str]:
    """1 回の購入を、どの演目に分けるかを人が確定する。

    2 つ以上ならその分け方を使い、1 つ以下なら「分けない」として題名のまま扱う。
    """
    clean = [str(p).strip()[:200] for p in programs if str(p).strip()][:12]
    with con:
        con.execute("INSERT INTO splits (uid, programs, updated_at) VALUES (?, ?, ?)"
                    " ON CONFLICT(uid) DO UPDATE SET"
                    " programs=excluded.programs, updated_at=excluded.updated_at",
                    (uid, json.dumps(clean, ensure_ascii=False), now()))
    return clean


def save_work(con: sqlite3.Connection, work: dict, payload: dict) -> dict:
    """1 作品ぶんの評価を書く。受け付ける項目は列挙したものだけにする（守り 4）。"""
    if work["bucket"] == "upcoming":
        raise ValueError("まだ上演していない作品には評価を付けない")
    verdict = payload.get("verdict") or None
    if verdict is not None and verdict not in VERDICTS:
        raise ValueError(f"verdict が候補にない: {verdict!r}")
    chosen = payload.get("chosen") or None
    if chosen is not None and chosen not in CHOSEN:
        raise ValueError(f"chosen が候補にない: {chosen!r}")
    row = {
        "work_key": work["work_key"], "title": work["title"],
        "first_date": work["first_date"], "last_date": work["last_date"],
        "times": work["times"], "verdict": verdict, "chosen": chosen,
        "note_impression": str(payload.get("note_impression") or "")[:4000],
        "note_motive": str(payload.get("note_motive") or "")[:4000],
        "updated_at": now(),
    }
    with con:
        con.execute(
            "INSERT INTO works (work_key, title, first_date, last_date, times, verdict,"
            " chosen, note_impression, note_motive, updated_at)"
            " VALUES (:work_key, :title, :first_date, :last_date, :times, :verdict,"
            " :chosen, :note_impression, :note_motive, :updated_at)"
            " ON CONFLICT(work_key) DO UPDATE SET"
            " times=:times, verdict=:verdict, chosen=:chosen,"
            " note_impression=:note_impression, note_motive=:note_motive,"
            " updated_at=:updated_at", row)
    return row


def save_attendance(con: sqlite3.Connection, work: dict, uid: str, attended: bool) -> dict:
    """観た／行かなかったを、作品ごと・回ごとに書く。

    セット券で 2 演目を観たとき、片方だけ席を立った場合もありうるので、
    作品ごとに別に持つ。
    """
    if uid not in {s["uid"] for s in work["shows"]}:
        raise ValueError(f"この作品の回ではない: {uid!r}")
    with con:
        con.execute(
            "INSERT INTO attendance (uid, work_key, attended, updated_at)"
            " VALUES (?, ?, ?, ?) ON CONFLICT(uid, work_key) DO UPDATE SET"
            " attended=excluded.attended, updated_at=excluded.updated_at",
            (uid, work["work_key"], 1 if attended else 0, now()))
    return {"uid": uid, "work_key": work["work_key"], "attended": 1 if attended else 0}


def read_visit_notes(con: sqlite3.Connection) -> dict[str, str]:
    """回ごとのメモを、uid → 文で返す。**推薦の計算はこれを読まない**（`visit_note`
    表の注記を見る）。空文字は返り値に含めない ── 呼ぶ側は `dict.get(uid, "")` で
    「書いていない」と区別なく扱える。
    """
    return {r["uid"]: r["note"] for r in con.execute(
        "SELECT uid, note FROM visit_note WHERE note <> ''")}


def save_visit_note(con: sqlite3.Connection, uid: str, note: str) -> dict:
    """回ごとのメモを書く。**`work_key` を持たない** ── uid だけで 1 回が決まるので、
    どの作品かは呼ぶ側（`app.py`）がすでに知っている。
    """
    with con:
        con.execute(
            "INSERT INTO visit_note (uid, note, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(uid) DO UPDATE SET note=excluded.note, updated_at=excluded.updated_at",
            (uid, note, now()))
    return {"uid": uid, "len": len(note)}


def stats(con: sqlite3.Connection) -> dict:
    """付けた件数の内訳。V26（△・× が 2 割以上あるか）をその場で見せる。"""
    c = {v: 0 for v in VERDICTS}
    for r in con.execute("SELECT verdict, COUNT(*) n FROM works"
                         " WHERE verdict IS NOT NULL GROUP BY verdict"):
        c[r["verdict"]] = r["n"]
    graded = sum(c[g] for g in GRADES)
    low = c["△"] + c["×"]
    skipped = con.execute(
        "SELECT COUNT(*) n FROM attendance WHERE attended = 0").fetchone()["n"]
    return {"counts": c, "graded": graded, "low": low, "skipped": skipped,
            "low_ratio": (low / graded) if graded else 0.0}


def reconcile(con: sqlite3.Connection, works: list[dict]) -> str:
    """束ね方が変わって宙に浮いた評価を、束ねた先へ引き継ぐ。

    題名の鍵が変わると work_key も変わる。**評価が消えたように見えるのがいちばん困る**ので、
    浮いた行の初日を含む作品が 1 つに決まり、その作品にまだ評価が無いときだけ移す。
    **元の行は消さない** ── 引き継ぎ先が違っていたときに戻せなくなる。
    """
    live = {w["work_key"]: w for w in works}
    moved = []
    for row in list(read_works(con).values()):
        if row["work_key"] in live or not row["verdict"]:
            continue
        ok = row["work_key"].rsplit("#", 1)[0]
        cands = [w for w in works
                 if any(sh["date"] == row["first_date"] for sh in w["shows"])
                 and (ok in w["work_key"].rsplit("#", 1)[0]
                      or w["work_key"].rsplit("#", 1)[0] in ok)]
        cands = [w for w in cands if not (read_works(con).get(w["work_key"]) or {}).get("verdict")]
        if len(cands) != 1:
            continue
        save_work(con, cands[0], {
            "verdict": row["verdict"], "chosen": row["chosen"],
            "note_impression": row["note_impression"], "note_motive": row["note_motive"]})
        moved.append((row["title"], cands[0]["title_display"], row["verdict"]))
    if not moved:
        return ""
    lines = [f"束ね方が変わって浮いた評価 {len(moved)} 件を引き継いだ（元の行は残してある）:"]
    for a, b, v in moved:
        lines.append(f"    {v}  「{norm(a)[:26]}」 → 「{b[:26]}」")
    return "\n".join(lines)


# ---------------------------------------------------------------- 旧形式からの移行

def migrate(con: sqlite3.Connection, works: list[dict]) -> str:
    """回ごとに付けていた古い ratings 表を、作品ごとの評価に移す。

    **古い表は消さない。** 束ね方を間違えた場合に戻せなくなるためで、
    移行は works が空のときに 1 度だけ行う。
    """
    have = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ratings'")
    if not have.fetchone():
        return ""
    if con.execute("SELECT COUNT(*) n FROM works").fetchone()["n"]:
        return ""
    old = {r["uid"]: dict(r) for r in con.execute("SELECT * FROM ratings")}
    if not old:
        return ""

    moved = skipped = 0
    for w in works:
        mine = [old[s["uid"]] for s in w["shows"] if s["uid"] in old]
        if not mine:
            continue
        # 「観ていない」は回ごとの情報なので attendance へ移す
        for s in w["shows"]:
            r = old.get(s["uid"])
            if r and r["verdict"] == "観ていない":
                save_attendance(con, w, s["uid"], False)
                skipped += 1  # 1 回が 2 演目に属していれば、作品ごとに 1 件ずつ入る
        grades = [r["verdict"] for r in mine if r["verdict"] in VERDICTS]
        verdict = collections.Counter(grades).most_common(1)[0][0] if grades else None
        payload = {
            "verdict": verdict,
            "chosen": next((r["chosen"] for r in mine if r["chosen"]), None),
            "note_impression": "\n".join(
                dict.fromkeys(r["note_impression"] for r in mine if r["note_impression"])),
            "note_motive": "\n".join(
                dict.fromkeys(r["note_motive"] for r in mine if r["note_motive"])),
        }
        if verdict or payload["chosen"] or payload["note_impression"] or payload["note_motive"]:
            save_work(con, w, payload)
            moved += 1
    return (f"旧形式の {len(old)} 件を移した ── 作品 {moved} 件に評価が付き、"
            f"「観ていない」{skipped} 回を回ごとの記録に移した（ratings 表は残してある）")


# ---------------------------------------------------------------- 画面

PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>観た作品に ◎○△× を付ける</title>
<style>
  :root { --bg:#faf9f7; --fg:#1c1a17; --muted:#6b6660; --line:#ddd8d1;
          --card:#fff; --accent:#8a5a2b; --ok:#2f6f4f; --off:#b04a3a; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#17181a; --fg:#e9e6e1; --muted:#9a948c; --line:#33353a;
            --card:#1f2124; --accent:#d3a06a; --ok:#7fc0a0; --off:#e08b7c; }
  }
  * { box-sizing:border-box }
  body { margin:0; background:var(--bg); color:var(--fg); line-height:1.7;
         font-family:system-ui,"Hiragino Sans","Noto Sans JP",sans-serif }
  header { position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line);
           padding:14px 20px; z-index:10 }
  .wrap { max-width:840px; margin:0 auto; padding:0 20px 80px }
  h1 { font-size:1.05rem; margin:0 0 4px }
  .sub { color:var(--muted); font-size:.82rem; margin:0 }
  .bar { display:flex; gap:14px; align-items:center; flex-wrap:wrap; margin-top:8px;
         font-size:.82rem; color:var(--muted) }
  .bar strong { color:var(--fg) }
  label.filter { cursor:pointer; user-select:none }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin:12px 0 }
  .card.done { opacity:.62 }
  .ttl { font-weight:600; font-size:1rem }
  .meta { color:var(--muted); font-size:.82rem; margin-top:2px }
  .times { display:inline-block; margin-left:6px; padding:0 7px; border-radius:999px;
           border:1px solid var(--accent); color:var(--accent); font-size:.75rem }
  .fact { color:var(--ok); font-size:.78rem; margin-top:4px }
  .grades { display:flex; gap:6px; flex-wrap:wrap; margin-top:10px; align-items:center }
  button.g { font:inherit; font-size:1.15rem; min-width:46px; padding:5px 10px;
             border:1px solid var(--line); border-radius:8px; background:transparent;
             color:var(--fg); cursor:pointer }
  button.g.small { font-size:.82rem; min-width:auto }
  button.g[aria-pressed="true"] { border-color:var(--accent); color:var(--accent);
                                  box-shadow:inset 0 0 0 1px var(--accent) }
  .shows { margin-top:10px; font-size:.85rem }
  .shows summary { cursor:pointer; color:var(--muted) }
  .show { display:flex; gap:10px; align-items:center; padding:3px 0; flex-wrap:wrap }
  .show .when { min-width:15em; color:var(--muted) }
  .show.off .when { color:var(--off); text-decoration:line-through }
  button.att { font:inherit; font-size:.76rem; padding:1px 8px; border-radius:999px;
               border:1px solid var(--line); background:transparent; color:var(--muted);
               cursor:pointer }
  button.att[aria-pressed="true"] { border-color:var(--off); color:var(--off) }
  .set { color:var(--accent); font-size:.78rem; margin-top:4px }
  .warn { color:var(--off); font-size:.8rem; margin-top:4px }
  .card.suspect { border-color:var(--off) }
  .mail { color:var(--muted); font-size:.78rem; margin:2px 0 }
  .editor { margin:6px 0 2px; padding:8px 10px; border:1px dashed var(--line);
            border-radius:8px }
  .editor[hidden] { display:none }
  .more { margin-top:8px; font-size:.85rem }
  .more summary { cursor:pointer; color:var(--muted) }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:8px }
  textarea { width:100%; min-height:56px; font:inherit; font-size:.88rem; padding:8px;
             border:1px solid var(--line); border-radius:8px; background:var(--bg);
             color:var(--fg); resize:vertical }
  .hint { color:var(--muted); font-size:.78rem; margin:2px 0 0 }
  .saved { color:var(--ok); font-size:.78rem; visibility:hidden }
  .saved.on { visibility:visible }
  .note { border-left:3px solid var(--line); padding:2px 0 2px 12px; color:var(--muted);
          font-size:.82rem; margin:14px 0 }
  h2 { font-size:.9rem; margin:28px 0 4px; color:var(--muted) }
</style>
<header>
  <h1>観た作品に ◎○△× を付ける</h1>
  <p class="sub">聞いているのは作品の出来ではなく、<strong>自分に合っていたか</strong>です。<strong>同じ作品を何回観ても評価は 1 つ</strong>。迷ったら △。途中でやめてよく、後から変えられます。</p>
  <div class="bar">
    <span>付けた <strong id="n-graded">0</strong> 作品</span>
    <span>△・× <strong id="n-low">0</strong> 件（<strong id="r-low">0</strong>%）</span>
    <span id="n-left"></span>
    <label class="filter"><input type="checkbox" id="only" checked> 未評価だけ表示</label>
  </div>
</header>
<div class="wrap">
  <p class="note">同じ上演期間の複数回は 1 作品に束ねています（<strong>回ごとに聞くと、評価がその日の演者の出来になってしまう</strong>ため）。年をまたぐ再演は別の作品として分けています。束ね方が違っていたら「観た回」を開けば分かります。<br>舞台ではないものを機械が拾ったときは「舞台ではない」で外せます（下に一覧が残り、戻せます）。<br>この画面は題名・日付・劇場しか出しません。<strong>クレジット（作り手の人名一覧）は表示しません</strong> ── 「知らなかった名前がどれだけあるか」は、知る前にしか測れないためです。</p>
  <h2 id="h-suspect" hidden>題名を確かめてほしいもの（受取方法の案内文などを題名として拾っている）</h2>
  <div id="list-suspect"></div>
  <div id="list-past"></div>
  <h2 id="h-undated" hidden>公演日が本文に無いもの（ファンクラブ経由。日付が無いので観た回を区別できない）</h2>
  <div id="list-undated"></div>
  <h2 id="h-skipped" hidden>買ったが行かなかったもの（評価は聞きません。間違いなら「行かなかった」を押して戻せます）</h2>
  <div id="list-skipped"></div>
  <h2 id="h-upcoming" hidden>まだ上演していない（観る予定。評価は聞かない）</h2>
  <div id="list-upcoming"></div>
  <h2 id="h-excluded" hidden>候補から外したもの（舞台ではないと判断した分。戻せます）</h2>
  <div id="list-excluded"></div>
</div>
<script>
const T = new URLSearchParams(location.search).get("t");
// 経路に既に ? が付いていることがある（/api/mail?uid=...）。
// そこへ ?t= を足すとトークンが読めず 403 になるので、区切りを見て決める。
function apiUrl(p, t){
  return p + (p.includes("?") ? "&" : "?") + "t=" + encodeURIComponent(t);
}
const api = (p, body) => fetch(apiUrl(p, T), body
  ? {method:"POST", headers:{"content-type":"application/json"}, body:JSON.stringify(body)}
  : {}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });

let data = null;
const esc = s => (s||"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const att = (uid, wk) => {
  const v = data.attendance[uid + "|" + wk];
  return v === undefined ? 1 : v;
};
// 同じ回に上演された「別の演目」。**分けた回だけ**を対象にする ──
// 分けていない回で題名のゆれを別演目として出すと、嘘の情報になる。
const others = (uid, self) => {
  const p = data.purchases[uid];
  return p && p.split ? p.programs.filter(x => x !== self) : [];
};

function span(w){
  if (!w.first_date) return "日付不明";
  if (w.first_date === w.last_date) return w.first_date;
  return `${w.first_date} 〜 ${w.last_date}`;
}

function card(w){
  const r = data.works[w.work_key] || {};
  const A = uid => att(uid, w.work_key);
  const seen = w.shows.filter(s => s.past && A(s.uid)).length;
  const el = document.createElement("div");
  el.className = "card" + (r.verdict ? " done" : "") + (w.suspect ? " suspect" : "");
  const venues = [...new Set(w.shows.map(s => s.venue).filter(Boolean))];
  const sets = [...new Set(w.shows.flatMap(s => others(s.uid, w.title)))];
  el.innerHTML = `
    <div class="ttl">${esc(w.title_display)}${w.times > 1
      ? `<span class="times">観た回 ${seen} / 買った回 ${w.times}</span>` : ""}</div>
    <div class="meta">${esc(span(w))}${venues.length ? " ／ " + esc(venues.join("・")) : ""}</div>
    ${sets.length ? `<div class="set">同じ回に上演された別の演目: ${
      sets.map(p => "「" + esc(p) + "」").join("")}（1 回の購入を演目ごとに分けています）</div>` : ""}
    ${w.suspect ? `<div class="warn">これは公演名ではなく、メールの案内文を拾ったものです。下の「観た回」で件名を見て、<strong>正しい題名に直す</strong>か、舞台でなければ<strong>外して</strong>ください。</div>` : ""}
    ${w.bought_after_seeing ? '<div class="fact">観たあとに、同じ作品の別の回を買っている（強い正の信号として数えます）</div>' : ""}
    <div class="grades">
      ${data.grades.map(g => `<button class="g" data-v="${g}" aria-pressed="${r.verdict===g}">${g}</button>`).join("")}
      <button class="g small" data-v="${data.undecided}" aria-pressed="${r.verdict===data.undecided}">${data.undecided}</button>
      <span class="saved">保存しました</span>
      <button class="att drop" title="舞台ではないものを機械が拾ったときに外す">舞台ではない</button>
    </div>
    <details class="shows"${w.shows.some(s => !A(s.uid)) ? " open" : ""}>
      <summary>観た回 ${w.times} 件（行かなかった回を外す／題名を直す／演目ごとに分ける）</summary>
      ${w.shows.map(s => `<div class="show${A(s.uid) ? "" : " off"}" data-uid="${s.uid}">
        <span class="when">${esc(s.date || "日付不明")} ${esc(s.time)} ${esc(s.venue)}</span>
        <button class="att" aria-pressed="${!A(s.uid)}">行かなかった</button>
        <button class="att ed">題名・演目を直す</button>
      </div>
      <div class="editor" data-ed="${s.uid}"${w.suspect ? "" : " hidden"}>
        <p class="mail">メールの件名: ${esc(data.purchases[s.uid]?.subject || "（無し）")}</p>
        <p class="mail">差出人: ${esc(data.purchases[s.uid]?.sender || "（無し）")}</p>
        <p class="mail">抽出が拾った題名: ${esc(data.purchases[s.uid]?.title_display || "")}</p>
        <div class="mail" data-hints="${s.uid}">メール本文の手がかりを読み込んでいます…</div>
        <p class="hint">演目を 1 行に 1 つ書く。<strong>1 行だけ書けば題名の直しになり、複数行なら演目ごとに分かれる。</strong>空にすると抽出結果に戻る。</p>
        <textarea data-progs="${s.uid}">${esc((data.purchases[s.uid]?.programs || []).join("\n"))}</textarea>
        <div class="row">
          <button class="g small" data-savesplit="${s.uid}">これで保存</button>
          <button class="g small" data-nosplit="${s.uid}">抽出結果に戻す</button>
        </div>
      </div>`).join("")}
    </details>
    <details class="more">
      <summary>きっかけと感想を足す（どれも任意）</summary>
      <div class="row">
        ${data.chosen.map(c => `<button class="g small" data-c="${c}" aria-pressed="${r.chosen===c}">${c}</button>`).join("")}
      </div>
      <p class="hint">作品の感想（観た後に思ったこと。空でよい）</p>
      <textarea data-f="note_impression">${esc(r.note_impression)}</textarea>
      <p class="hint">観に行くきっかけ（なぜ行こうと思ったか。覚えている範囲で。空でよい）</p>
      <textarea data-f="note_motive">${esc(r.note_motive)}</textarea>
    </details>`;

  const flash = () => { const s = el.querySelector(".saved");
    s.classList.add("on"); setTimeout(() => s.classList.remove("on"), 1200); };

  const put = async (patch) => {
    const cur = data.works[w.work_key] || {verdict:null, chosen:null,
                                           note_impression:"", note_motive:""};
    const res = await api("/api/work", {work_key:w.work_key, verdict:cur.verdict,
      chosen:cur.chosen, note_impression:cur.note_impression || "",
      note_motive:cur.note_motive || "", ...patch});
    data.works[w.work_key] = res.work; data.stats = res.stats;
    paintBar(); flash(); repaintCard();
  };

  const toggleAtt = async (uid, off) => {
    const res = await api("/api/attendance", {work_key:w.work_key, uid, attended: !off});
    data.attendance[uid + "|" + w.work_key] = res.attendance.attended;
    w.bought_after_seeing = res.bought_after_seeing;
    data.stats = res.stats;
    paint();   // 全部行かなかったものは下の束へ移るので、描き直す
  };

  const setSplit = async (uid, programs) => {
    data = await api("/api/split", {uid, programs});   // 作品が組み替わるので全部描き直す
    paint();
  };

  function repaintCard(){ el.replaceWith(card(w)); }

  el.querySelectorAll("[data-v]").forEach(b => b.onclick = () =>
    put({verdict: (data.works[w.work_key]||{}).verdict === b.dataset.v ? null : b.dataset.v}));
  el.querySelectorAll("[data-c]").forEach(b => b.onclick = () =>
    put({chosen: (data.works[w.work_key]||{}).chosen === b.dataset.c ? null : b.dataset.c}));
  el.querySelectorAll(".show").forEach(row => {
    const uid = row.dataset.uid;
    row.querySelector(".att").onclick = () => toggleAtt(uid, A(uid) === 1);
    row.querySelector(".ed").onclick = () => {
      const ed = el.querySelector(`[data-ed="${uid}"]`);
      ed.hidden = !ed.hidden;
      if (!ed.hidden) loadHints(uid, el);
    };
    if (w.suspect) loadHints(uid, el);   // 印が付いたものは開いた状態なので先に読む
  });
  el.querySelectorAll("[data-savesplit]").forEach(b => b.onclick = () => {
    const uid = b.dataset.savesplit;
    const lines = el.querySelector(`[data-progs="${uid}"]`).value
      .split("\n").map(x => x.trim()).filter(Boolean);
    setSplit(uid, lines);
  });
  el.querySelectorAll("[data-nosplit]").forEach(b => b.onclick = () =>
    setSplit(b.dataset.nosplit, []));
  el.querySelector(".drop").onclick = async () => {
    data = await api("/api/exclude", {work_key:w.work_key, excluded:true});
    paint();
  };
  el.querySelectorAll("textarea").forEach(t => t.onchange = () => put({[t.dataset.f]: t.value}));
  return el;
}

function excludedRow(x){
  const el = document.createElement("div");
  el.className = "card done";
  el.innerHTML = `<div class="show">
    <span class="when">${esc(x.date || "日付不明")}</span>
    <span>${esc(x.title_display)}</span>
    <button class="att">候補に戻す</button></div>`;
  el.querySelector(".att").onclick = async () => {
    data = await api("/api/exclude", {uid:x.uid, program:x.program, excluded:false});
    paint();
  };
  return el;
}

const hintCache = {};
async function loadHints(uid, el){
  const box = el.querySelector(`[data-hints="${uid}"]`);
  if (!box || box.dataset.done) return;
  box.dataset.done = "1";
  try {
    if (!hintCache[uid]) hintCache[uid] = await api("/api/mail?uid=" + encodeURIComponent(uid));
    const h = hintCache[uid].hints || [];
    box.innerHTML = h.length
      ? "メール本文の手がかり:<br>" + h.map(x => "・" + esc(x)).join("<br>")
      : "メール本文に手がかりは見つかりませんでした。";
  } catch (e) {
    box.dataset.done = "";   // 次に開いたときに読み直せるようにする
    box.textContent = "メール本文を読めませんでした（" + e.message + "）。"
      + "件名と差出人は上に出ています。";
  }
}

function upcomingCard(w){
  const el = document.createElement("div");
  el.className = "card done";
  el.innerHTML = `<div class="ttl">${esc(w.title_display)}</div>
    <div class="meta">${esc(span(w))}</div>
    <div class="hint">上演日を過ぎたら、評価待ちとしてここに出ます</div>`;
  return el;
}

function paintBar(){
  const s = data.stats;
  document.getElementById("n-graded").textContent = s.graded;
  document.getElementById("n-low").textContent = s.low;
  document.getElementById("r-low").textContent = Math.round(s.low_ratio * 100);
  const left = data.works_list.filter(
    w => w.bucket !== "upcoming" && !(data.works[w.work_key]||{}).verdict
      && !(w.shows.length > 0 && w.shows.every(s => !att(s.uid, w.work_key)))).length;
  document.getElementById("n-left").textContent = "未評価 " + left + " 作品";
}

function paint(){
  const only = document.getElementById("only").checked;
  const pick = w => !only || !(data.works[w.work_key]||{}).verdict;
  const of = b => data.works_list.filter(w => w.bucket === b);
  // 買ったが行かなかったもの（残っている回が 1 つも無いもの）は下へ下げる
  const skippedWork = w => w.shows.length > 0 && w.shows.every(s => !att(s.uid, w.work_key));
  const live = b => of(b).filter(pick).filter(w => !skippedWork(w));
  const suspect = live("past").concat(live("undated")).filter(w => w.suspect);
  const past = live("past").filter(w => !w.suspect);
  const und = live("undated").filter(w => !w.suspect);
  const skipped = of("past").concat(of("undated")).filter(pick).filter(skippedWork);
  const up = of("upcoming");
  document.getElementById("list-suspect").replaceChildren(...suspect.map(card));
  document.getElementById("h-suspect").hidden = suspect.length === 0;
  document.getElementById("list-past").replaceChildren(...past.map(card));
  document.getElementById("list-undated").replaceChildren(...und.map(card));
  document.getElementById("list-skipped").replaceChildren(...skipped.map(card));
  document.getElementById("h-skipped").hidden = skipped.length === 0;
  document.getElementById("list-upcoming").replaceChildren(...up.map(upcomingCard));
  document.getElementById("list-excluded").replaceChildren(
    ...(data.excluded || []).map(excludedRow));
  document.getElementById("h-undated").hidden = und.length === 0;
  document.getElementById("h-upcoming").hidden = up.length === 0;
  document.getElementById("h-excluded").hidden = (data.excluded || []).length === 0;
  paintBar();
}

document.getElementById("only").onchange = paint;
api("/api/list").then(d => { data = d; paint(); });
setInterval(() => api("/api/heartbeat", {}).catch(() => {}), 30000);
addEventListener("pagehide", () => navigator.sendBeacon(apiUrl("/api/bye", T), "{}"));
</script>
"""


# ---------------------------------------------------------------- ブラウザを開く

def is_wsl() -> bool:
    return "microsoft" in platform.uname().release.lower()


def open_in_browser(url: str) -> str:
    """既定のブラウザで開く。開けたら手段の名前、開けなかったら空文字を返す。

    WSL には xdg-open も wslview も無いことがあり、**webbrowser.open は失敗しても
    例外を出さずに True を返すことがある。** 黙って開かないのが最も困るので、
    WSL では Windows 側の既定ブラウザに直接渡す。
    """
    if is_wsl():
        exe = shutil.which("wslview") or shutil.which("explorer.exe")
        if not exe:
            return ""
        # explorer.exe は成功しても終了コード 1 を返すので、結果は見ない
        subprocess.Popen([exe, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return Path(exe).name
    try:
        if webbrowser.open(url):
            return "既定のブラウザ"
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------- 待ち受け

class State:
    def __init__(self, token: str, con: sqlite3.Connection, purchases: list[dict]) -> None:
        self.token = token
        self.con = con
        self.purchases = purchases
        self.by_uid = {r["uid"]: r for r in purchases}
        self.last_seen = time.monotonic()
        self.stop = threading.Event()
        self.rebuild()

    def rebuild(self) -> None:
        """分け方・除外・束ね直しが変わったら作品を組み直す。

        **束ね直し（merges）もここで当てる。** 画面の側だけで当てると、
        **同じ公演を 2 件として学習する** ── 人が「同じ公演だ」と答えたことが、
        推薦の材料に届かない。
        """
        self.splits = read_splits(self.con)
        self.excluded = read_excluded(self.con)
        self.merges = read_merges(self.con)
        self.works = load_works(self.purchases, self.splits, self.excluded, self.merges)
        self.by_key = {w["work_key"]: w for w in self.works}

    def payload(self) -> dict:
        attendance = read_attendance(self.con)
        for w in self.works:
            w["bought_after_seeing"] = bought_after_seeing(w, attendance)
        return {
            "works_list": self.works,
            "works": read_works(self.con),
            "attendance": attendance,
            "purchases": {r["uid"]: {
                "title": r["title"], "title_display": norm(r["title"]),
                "subject": norm(r.get("subject") or ""),
                "sender": r.get("from") or "",
                "programs": programs_of(r, self.splits),
                "split": len(programs_of(r, self.splits)) > 1,
                "renamed": bool(self.splits.get(r["uid"])),
            } for r in self.purchases},
            "excluded": [{
                "uid": u, "program": p, "title_display": norm(p),
                "date": (self.by_uid.get(u) or {}).get("date") or "",
            } for u, p in sorted(self.excluded,
                                 key=lambda kv: (self.by_uid.get(kv[0]) or {}).get("date") or "",
                                 reverse=True)],
            "stats": stats(self.con),
            "grades": GRADES, "undecided": UNDECIDED, "chosen": CHOSEN,
        }


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "taguri-rate"
    state: State

    def log_message(self, fmt, *args):  # 端末を要求ログで埋めない
        pass

    # --- 守り 3: すべての要求でトークンを要求する
    def _authed(self) -> bool:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        return secrets.compare_digest((q.get("t") or [""])[0], self.state.token)

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if not self._authed():
            self._send(403, b"403", "text/plain; charset=utf-8")
            return
        self.state.last_seen = time.monotonic()
        if path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif path == "/api/list":
            self._json(self.state.payload())
        elif path == "/api/mail":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            uid = (q.get("uid") or [""])[0]
            if uid not in self.state.by_uid:   # 既知の回だけ。パスは組み立てさせない
                self._json({"error": "知らない回"}, 400)
                return
            r = self.state.by_uid[uid]
            self._json({"uid": uid, "subject": norm(r.get("subject") or ""),
                        "sender": r.get("from") or "", "hints": mail_hints(uid)})
        else:
            self._send(404, b"404", "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if not self._authed():
            self._send(403, b"403", "text/plain; charset=utf-8")
            return
        st = self.state
        st.last_seen = time.monotonic()
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        # --- 守り 4: 受け付ける操作は、この 6 つだけ
        try:
            if path == "/api/heartbeat":
                self._json({"ok": True})
            elif path == "/api/bye":
                self._json({"ok": True})
                st.stop.set()
            elif path == "/api/work":
                p = json.loads(raw or b"{}")
                w = st.by_key[str(p.get("work_key"))]
                self._json({"work": save_work(st.con, w, p), "stats": stats(st.con)})
            elif path == "/api/attendance":
                p = json.loads(raw or b"{}")
                w = st.by_key[str(p.get("work_key"))]
                a = save_attendance(st.con, w, str(p.get("uid")), bool(p.get("attended")))
                self._json({"attendance": a, "stats": stats(st.con),
                            "bought_after_seeing": bought_after_seeing(
                                w, read_attendance(st.con))})
            elif path == "/api/exclude":
                p = json.loads(raw or b"{}")
                flag = bool(p.get("excluded"))
                if p.get("work_key"):
                    w = st.by_key[str(p["work_key"])]
                    pairs = [(s["uid"], s["program"]) for s in w["shows"]]
                elif p.get("uid") and p.get("program"):
                    uid = str(p["uid"])
                    if uid not in st.by_uid:
                        raise KeyError(f"知らない回: {uid!r}")
                    pairs = [(uid, str(p["program"]))]
                else:
                    raise ValueError("work_key か、(uid, program) の組が要る")
                save_excluded(st.con, pairs, flag)
                st.rebuild()
                self._json(st.payload())
            elif path == "/api/split":
                p = json.loads(raw or b"{}")
                uid = str(p.get("uid"))
                if uid not in st.by_uid:
                    raise KeyError(f"知らない回: {uid!r}")
                progs = p.get("programs")
                if not isinstance(progs, list):
                    raise ValueError("programs は並びで渡す")
                save_split(st.con, uid, progs)
                st.rebuild()
                self._json(st.payload())
            else:
                self._send(404, b"404", "text/plain; charset=utf-8")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            self._json({"error": str(e)}, 400)


def serve(open_browser: bool = True) -> None:
    purchases = load_purchases()
    con = connect()
    token = secrets.token_urlsafe(24)
    state = State(token, con, purchases)
    works = state.works
    msg = migrate(con, works)
    fixed = reconcile(con, works)
    Handler.state = state

    # --- 守り 2: 127.0.0.1 に固定する。ポートは空いているものを使う
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/?t={token}"

    n = collections.Counter(w["bucket"] for w in works)
    saved = read_works(con)
    done = sum(1 for r in saved.values() if r["verdict"])
    split = sum(1 for r in purchases if len(programs_of(r, state.splits)) > 1)
    if msg:
        print(msg)
    if fixed:
        print(fixed)
    print(f"買った回 {len(purchases)} 件 → 作品 {len(works)} 件"
          f"（上演済み {n['past']} / 公演日が不明 {n['undated']}"
          f" / まだ上演していない {n['upcoming']}）、評価済み {done} 作品")
    if split:
        print(f"複数の演目に分けた回 {split} 件（セット券・交互上演。画面で直せる）")
    suspect = [w for w in works if w["suspect"]]
    if suspect:
        print(f"**題名を確かめてほしい作品 {len(suspect)} 件**"
              "（受取方法の案内文などを題名として拾っている。画面の先頭に出る）:")
        for w in suspect:
            print(f"    {w['first_date'] or '日付不明'}  {w['title_display'][:40]}")
    if state.excluded:
        print(f"候補から外した演目 {len(state.excluded)} 件（舞台ではないと判断した分）"
              " ── extract_performances.py の語のリストに反映する材料になる:")
        for t in sorted({p for _, p in state.excluded})[:12]:
            print(f"    {norm(t)[:70]}")
    orphan = [k for k in saved if k not in state.by_key]
    if orphan:
        print(f"**いま作品に結び付いていない評価 {len(orphan)} 件**（題名の束ね方が"
              f"変わったため。消していないので、分け方を直せば戻る）")
    print(f"保存先 {DB}")
    print(f"\n  {url}\n")

    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    how = open_in_browser(url) if open_browser else ""
    if open_browser and not how:
        print("ブラウザを自動で開けなかった。上の URL をブラウザに貼ること。")
    elif how:
        print(f"{how} で開いた。開かない場合は上の URL を貼ること。")
    if is_wsl():
        print("（WSL のため、Windows 側のブラウザから WSL の 127.0.0.1 へ転送される"
              "仕組みに頼っている。届かない場合は WSL 内の curl で確かめること）")
    print("画面を閉じるか、Ctrl+C で終了する。"
          f"無操作が {IDLE_LIMIT:.0f} 秒続いた場合も落ちる。")

    try:
        # --- 守り 6: 常駐しない
        while not state.stop.wait(1.0):
            if time.monotonic() - state.last_seen > IDLE_LIMIT:
                print("無操作が続いたので終了する。")
                break
    except KeyboardInterrupt:
        print()
    httpd.shutdown()
    s = stats(con)
    print(f"付けた {s['graded']} 作品（△・× {s['low']} 件・{s['low_ratio'] * 100:.0f}%）"
          f"／行かなかった回 {s['skipped']} 件")
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-browser", action="store_true", help="ブラウザを自動で開かない")
    a = ap.parse_args()
    serve(open_browser=not a.no_browser)


if __name__ == "__main__":
    main()
