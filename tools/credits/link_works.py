#!/usr/bin/env python3
"""評価が付いているのに材料の無い記録を、題名から公演ページに結び付ける。

    python3 tools/credits/link_works.py            # 更新の段から呼ばれる
    python3 tools/credits/link_works.py --dry-run  # 書かずに当たり方だけ見る
    python3 tools/credits/link_works.py --limit 5  # 件数を切って試す

## なぜ要るのか

**名簿（網 B）とあらすじの要素（網 C）は、公演ページから作る。** 記録がどの公演なのかが
決まっていないと、評価を付けても材料が 1 件も取れない。実測では、**評価済み 92 作品のうち
38 作品が「評価は付いているのに名簿へ 1 人も出していない」**状態だった。

**画面には結び付ける口があるが、それだけでは届かない**（`app.link_stage`）。画面が選べるのは
手元の控えにある公演だけで、**古い公演はどちらの控えにも無い** ── 公演ページの控えは
155 行のうち 25 行が題名だけで id を持たず、候補の一覧は最近の公演しか持たない。
**画面から外へは取りに行かない**（企画書 5 章の守り 5）ので、画面の側では原理的に直せない。

**更新の段は外へ取りに行ってよい。** 取得の範囲と間隔を 1 か所で守るのが守りの中身なので、
ここで探すことは方針に反しない。

## 当てる条件 ── 日付が入っていることを必ず要求する

既存の突き合わせ（`fetch_credits.run`）は「上演期間の文字列に**観劇年**が含まれること」で
当てていた。**同じ年に上演された同名の別公演を当ててしまう。** ここでは条件を 2 つとも
要求する。

| | 条件 | なぜ |
|---|---|---|
| 1 | **観劇日が上演期間の中にある** | 年だけの一致では、同じ戯曲の別の上演に当たる。「ハムレット」は 1 年に何本もある |
| 2 | **公演ページの題名が、記録の題名と重なる** | 検索語は題名の一部から作るので、語だけが同じ別公演が返ることがある |

**当たらなかったことも記録する**（`matched: false`）。次の実行で同じ検索を繰り返さないため
であり、**題名を直したら検索し直す**（記録した検索語と変わったかで判定する）。

## 間違えたときに取り返せるようにする

**結び付けを間違えると、観ていない公演の作り手が名簿に入る。** そこで
`auto: true` を残し、画面の「推薦に使う公演」に**自動で結び付けたことを書く** ── 本人が
見て違うと分かれば、その場で外せる。**黙って結び付けたままにしない。**
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "tickets"))
import fetch_credits as FC                                          # noqa: E402
import measure_nets as M                                            # noqa: E402
import rate_performances as R                                       # noqa: E402

OUT = ROOT / "data" / "credits" / "linked.jsonl"
# **1 記録あたりの要求数に上限を置く。** 1 リクエスト／秒なので、上限が無いと
# 38 件で 25 分かかりうる。**要求数そのもので数える** ── 検索語の数と公演の数で掛け算に
# すると、当たりが早い記録でも遅い記録でも同じだけ枠を使う
MAX_REQ = 18
MAX_IDS = 5


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).replace(" ", "").replace("　", "").lower()


# 販売側・興行側が題名に付ける語。**検索語からは落とす** ── これが付いたままだと
# CoRich の題名検索が 0 件になる（実測 ──「劇壇ガルバ 第7回公演「The Weir~堰~」」は
# 0 件だが、「The Weir」なら当該の公演が 1 件目に出る）
_TRIM = re.compile(r"(第\s*\d+\s*回公演|初座長公演|座長公演|特別公演|凱旋公演|公演|"
                   r"歌舞伎公演|ミュージカル|舞台|朗読劇|コンサート)")


def words_for(title: str) -> list[str]:
    """検索語を作る。**`clean_title` に、短い中核語を足す。**

    `fetch_credits.clean_title` は漢字 3 字以上・カタカナ 4 字以上でしか中核語を切り出さない。
    **実測では、そこで落ちる語こそが当たる語だった** ── 「The Weir」（英字 8 字だが
    `clean_title` の並びでは 4 番目）、「堰」（漢字 1 字）、「純烈」（漢字 2 字）。
    **短い語は当たりが増えるぶん外れも増えるが、日付と題名の二重の条件で落とす**ので、
    誤って結び付くことはない。
    """
    out = list(FC.clean_title(title))
    s = unicodedata.normalize("NFKC", title)
    s = re.sub(r"[【〈\[（(].{0,24}?[】〉\]）)]", " ", s)
    for chunk in re.split(r"[『』「」\s　/／・]+", _TRIM.sub(" ", s)):
        chunk = chunk.strip(" 　-−ー~〜")
        if 2 <= len(chunk) <= 30:
            out.append(chunk)
    seen, res = set(), []
    for w in out:
        k = nz(w)
        if k and k not in seen:
            seen.add(k)
            res.append(w)
    return res


def page_title(stage_id: str) -> str:
    """公演ページの題名。**`<title>` の「|」より前を採る。**"""
    f = FC.CACHE / f"https___stage_corich_jp_stage_{stage_id}.html"
    if not f.exists():
        return ""
    m = re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8", errors="ignore"), re.S)
    return re.sub(r"\s+", " ", m.group(1).split("|")[0]).strip() if m else ""


def span(period: str):
    """上演期間の初日と楽日。**日付で当てるために要る**（年だけでは当たりが緩い）。"""
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    f = lambda t: f"{t[0]}-{int(t[1]):02d}-{int(t[2]):02d}"          # noqa: E731
    return f(ms[0]), f(ms[-1])


def title_ok(mine: str, theirs: str) -> bool:
    """題名が重なるか。**含み合いか、似ている度合いで見る。**

    完全一致は要求しない ── 記録側の題名は購入確認メールから来ており、販売側の冠
    （団体名・回次・セット券）が付いていることが多い。
    """
    a, b = R.title_key(mine), R.title_key(theirs)
    if not a or not b:
        return False
    if len(min(a, b, key=len)) >= 3 and (a in b or b in a):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def load_done() -> dict:
    """これまでの結果。**当たらなかったことも残す**（同じ検索を繰り返さない）。"""
    out: dict = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                out[r["work_key"]] = r                # 後の行が前の行を上書きする
    return out


def targets() -> list[dict]:
    """**評価が付いていて、材料が無い記録。**

    材料が有る記録には触らない ── メールから公演ページを引けているものを探し直すのは、
    要求を使うだけで何も増えない。

    ## id が付いているのに材料が無い記録も拾う

    **以前は「id が付いている記録」を全部飛ばしていた。** 結び付いている＝材料が有る、と
    見なしていたためだが、**その 2 つは別である。**

    `fetch_candidates.py --keep-days` が候補に残す終演公演は、**公演ページを取りに行かない
    ので `fields` が空である。** 本人がその行を手で足す欄から選ぶと、記録に id は付くが
    材料は 1 件も入らない。`measure_nets._fields_by_stage` は空の表を飛ばすので、
    **評価を付けても名簿に 1 人も出ない** ── 結び付けたのに何も起きない状態になる。

    **id が有るときは探さない。取りに行くだけである**(`fetch_one`)。検索は要らないので
    1 要求で済み、日付と題名で当て直す必要もない（本人が選んだ公演だからである）。
    """
    con = R.connect()
    try:
        saved = R.read_works(con)
    finally:
        con.close()
    have = credit_ids()
    out = []
    for r in M.load_rated():
        row = saved.get(r["key"]) or {}
        if r["people"]:
            continue                    # 材料が有る
        sid = str(row.get("stage_id") or "")
        if sid and sid in have:
            continue                    # id も材料も有る（表が空でない）
        out.append({"work_key": r["key"], "title": r["title"], "date": r["date"],
                    "stage_id": sid})
    return out


def credit_ids() -> set[str]:
    """**中身のあるクレジットを持っている公演の id。** 空の表は持っていないと数える。"""
    return {sid for sid, f in M._fields_by_stage().items() if f}


def fetch_one(stage_id: str) -> dict:
    """**id が分かっている公演のページを取る。** 検索しないので 1 要求で済む。

    当て直しはしない ── **どの公演かを決めたのは本人である。** 画面で選んだ id を
    こちらで棄却できる根拠は無い。
    """
    c = FC.credits_of(str(stage_id))
    return {"matched": True, "stage_id": str(stage_id), "page_title": page_title(stage_id),
            "period": c.get("period") or "", "fields": c.get("fields") or {},
            # **「自動で結び付けました」と出さない。** id を決めたのは本人であって、
            # 機械が題名から当てたものではない ── 同じ印を付けると、確かめる対象が増える
            "searched": [], "by_id": True, "auto": False}


# ---------------------------------------------------------------- 画面から題名で探す
#
# 起案者の指示（2026-08-24）──「手で足す欄で題名を打ったときだけ、更新の段と同じ経路で
# 公演ページを探しに行くようにしてほしい」。
#
# ## 日付では当てられない
#
# `find()` は**観劇日が上演期間の中にある**ことを必ず要求する。同じ戯曲の別の上演を
# 当てないための条件だが、**手で足す欄では日付がまだ無い** ── 題名を打っている途中で
# 探しに行くので、観劇日はこれから入る。
#
# **だから機械は決めない。当たった公演を並べて、本人に選ばせる。** 実測でも『るつぼ
# The Crucible』は東京・兵庫・豊橋の 3 件が別の公演として登録されており、**どれを観たのかを
# 知っているのは本人だけである**（`similar_works` と同じ考え方）。
#
# ## 要求数を画面向けに絞る
#
# 更新の段は 1 記録あたり最大 18 要求を使うが、**画面は人が待っている。**
# 1 リクエスト／秒なので、上限がそのまま待ち時間になる。**当たりが出たら早めに切り上げる。**
SCREEN_MAX_REQ = 8


def search_stages(title: str, *, limit: int = 6, max_req: int = SCREEN_MAX_REQ) -> list[dict]:
    """題名で公演ページを探す。**日付で絞らないので、当たりを複数返す。**

    返すのは画面の候補と同じ形（`app.suggest` の行）にそろえた並びである。
    """
    k = R.title_key(title or "")
    if len(k) < 2:
        return []
    req, out, seen_ids = 0, [], set()
    for w in words_for(title):
        if req >= max_req or len(out) >= limit:
            break
        try:
            req += 1
            ids = FC.search(w)[:MAX_IDS]
        except Exception:                                           # noqa: BLE001
            continue
        for sid in ids:
            if sid in seen_ids or req >= max_req or len(out) >= limit:
                continue
            seen_ids.add(sid)
            try:
                req += 1
                c = FC.credits_of(sid)
            except Exception:                                       # noqa: BLE001
                continue
            pt = page_title(sid) or (c.get("fields") or {}).get("題名", "")
            if not title_ok(title, pt):
                continue
            f = c.get("fields") or {}
            sp = span(c.get("period") or "")
            out.append({"stage_id": str(sid), "page_title": pt,
                        "period": c.get("period") or "", "fields": f,
                        "venue": f.get("劇場", ""),
                        # **1 日公演のときだけ日付を入れる。** 期間のある公演で初日を
                        # 勝手に入れると、観ていない日が記録に残る（`app._suggest_pool`
                        # と同じ規則にそろえる）
                        "date": sp[0] if (sp and sp[0] == sp[1]) else "",
                        "searched": w})
    return out


def find(work: dict, *, verbose: bool = False) -> dict:
    """1 件を探す。**日付と題名の両方が合ったときだけ当たりにする。**"""
    tried, req, seen_ids = [], [0], set()
    for w in words_for(work["title"]):
        if req[0] >= MAX_REQ:
            break
        tried.append(w)
        try:
            req[0] += 1
            ids = FC.search(w)[:MAX_IDS]
        except Exception as e:                                      # noqa: BLE001
            if verbose:
                print(f"    検索できなかった（{w}）: {e}")
            continue
        for sid in ids:
            if sid in seen_ids or req[0] >= MAX_REQ:
                continue
            seen_ids.add(sid)
            try:
                req[0] += 1
                c = FC.credits_of(sid)
            except Exception:                                       # noqa: BLE001
                continue
            sp = span(c.get("period") or "")
            if not sp or not (sp[0] <= work["date"] <= sp[1]):
                continue
            pt = page_title(sid)
            if not title_ok(work["title"], pt):
                if verbose:
                    print(f"    日付は合うが題名が違う: {pt[:40]}")
                continue
            return {"matched": True, "stage_id": str(sid), "page_title": pt,
                    "period": c.get("period") or "", "fields": c.get("fields") or {},
                    "searched": tried}
    return {"matched": False, "searched": tried}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="試す件数（0 は全部）")
    ap.add_argument("--dry-run", action="store_true", help="書かずに当たり方だけ見る")
    ap.add_argument("--retry-missed", action="store_true",
                    help="当たらなかった記録も、検索語が同じでも探し直す")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    done = load_done()
    todo = []
    for w in targets():
        prev = done.get(w["work_key"])
        # **id が付いている記録は、済みでも取りに行く。** 材料が空だからこそ `targets()` に
        # 残っている ── ここで飛ばすと、結び付いたまま名簿に 1 人も出ない状態が続く
        if w.get("stage_id"):
            todo.append(w)
            continue
        if prev and prev.get("matched"):
            continue                    # もう結び付いている（画面で外された分は下で拾う）
        if prev and not a.retry_missed:
            # **題名が変わっていたら探し直す。** 直したことが次の実行に効かないなら、
            # 直す手間に見合わない（`corrections` と同じ考え方）
            if prev.get("title") == w["title"]:
                continue
        todo.append(w)
    if a.limit:
        todo = todo[:a.limit]
    n_byid = sum(1 for w in todo if w.get("stage_id"))
    print(f"材料の無い記録 {len(targets())} 件のうち、探すのは {len(todo)} 件"
          f"（1 リクエスト／秒・1 件あたり最大 {MAX_REQ} 要求）"
          f"── うち {n_byid} 件は id が分かっているので取りに行くだけ（1 要求）", flush=True)

    rows, hit = [], 0
    for i, w in enumerate(todo, 1):
        if w.get("stage_id"):
            # **探さない。** 本人が選んだ公演なので、当て直す根拠が無い
            try:
                r = fetch_one(w["stage_id"])
            except Exception as e:                                  # noqa: BLE001
                print(f"  {i}/{len(todo)} {w['title'][:28]} "
                      f"── id {w['stage_id']} を取れなかった（{type(e).__name__}）")
                continue
        else:
            r = find(w, verbose=a.verbose)
        hit += bool(r["matched"])
        rows.append({"work_key": w["work_key"], "title": w["title"], "date": w["date"],
                     "auto": True, **r})
        mark = f'→ {r.get("page_title", "")[:34]}（{r.get("period", "")[:22]}）' \
            if r["matched"] else "見つからなかった"
        print(f"  {i}/{len(todo)} {w['title'][:28]}（{w['date']}） {mark}", flush=True)
    print(f"当たり {hit}/{len(todo)}")
    if a.dry_run or not rows:
        if a.dry_run:
            print("--dry-run なので何も書いていない")
        return 0

    with OUT.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # **記録の側にも書く。** ここに書かないと、名簿を作る側は結び付きを知らない
    con = R.connect()
    try:
        for r in rows:
            if not r["matched"]:
                continue
            con.execute("UPDATE works SET stage_id=?,"
                        " updated_at=datetime('now','localtime')"
                        " WHERE work_key=? AND (stage_id IS NULL OR stage_id='')",
                        (r["stage_id"], r["work_key"]))
        con.commit()
    finally:
        con.close()
    print(f"{len(rows)} 件を {OUT} に書き、うち {hit} 件を記録に結び付けた")
    print("**自動で結び付けた分は画面に「自動で結び付けました」と出る。**"
          " 違っていたら「結び付けを外す」で外せる")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
