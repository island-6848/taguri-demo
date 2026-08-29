#!/usr/bin/env python3
"""「興味あり」に添えた理由の文を読み、次の推薦に返す道を作る。

## なぜ理由を聞くのか ── 返りがあるから

**測るためだけの入力は設計しない**（企画書 2 章・検証 021 で 1 度取り下げた）。
理由欄が成立するのは、**書いた内容が本人に返るとき**である。

**返りはこれである** ── 理由に名前を書くと、**その名前が「お気に入り」への昇格候補として
出てくる。** 登録すれば、その人・その団体の公演は**件数の制限も条件も付けずに新着として
出るようになる**（企画書 1 章）。

**これは企画の中核に直に効く。** 名簿（網 B）は「◎ を付けた公演の作り手」しか材料に
持てないので、**外で知った名前は待っていても入ってこない** ── 実測でも、決め手になった
名前 9 件のうち 2 件は履歴に 1 度も出てこない名前だった。**理由の文は、その 2 件を
拾える唯一の経路である。**

## 担い手はコードにする

**規則で足りる。** 理由の文から名前を「推測」する必要はない ── **その公演のクレジットと
あらすじの要素という正解の一覧が手元にある**ので、**そのどれが文に出ているかを見るだけ**で
決まる。LLM に渡すのは、規則が届かないことを実測で示せた場合だけにする。

**限界を先に書く。**

- **姓だけ・愛称・略称は拾えない。** クレジットの表記と文字が一致することを条件にしている
- **「〜が出ていないから興味がない」のような否定は読み分けない。** 拾うのは興味ありに
  添えた理由だけなので、否定の文が入るのは書き手が意図した場合に限られる
- **一致が無いことは失敗ではない。** 日程・値段・劇場が理由なら名前は出てこない。
  その場合は文をそのまま記録に残す（推薦には効かない）
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import measure_nets as M                                           # noqa: E402
import recommend as RC                                             # noqa: E402
import hand_themes as HT                                           # noqa: E402

CAND = ROOT / "data" / "review" / "candidates.jsonl"
THEMES = ROOT / "data" / "credits" / "themes.jsonl"
DB = ROOT / "data" / "review" / "ratings.db"

# 昇格の宛先。**役職ではなく「何として登録するか」で分ける**（申告の種類に合わせる）
KIND_PERSON, KIND_GROUP, KIND_THEME, KIND_WORK = "人", "団体", "題材", "作品"
MIN_LEN = 2      # 1 文字の語は拾わない（どの文にも当たる）


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).replace(" ", "").replace("　", "").lower()


def _cands() -> dict[str, dict]:
    if not CAND.exists():
        return {}
    out = {}
    for line in CAND.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            c = json.loads(line)
            out[str(c["stage_id"])] = c
    return out


def _themes() -> dict[str, list[str]]:
    """公演の id → あらすじから抽出した要素の語。

    **要素は `{"kind": …, "word": …}` の形で保存されている。** ここは文字列だけを
    拾っていたため、**題材の語が 1 つも語彙に入っていなかった** ── 実データで
    候補側 678 件・学習側 36 件に要素があるのに、昇格候補 7 件はすべて人物で、
    **題材の候補は 1 度も出たことがない。** 題材は申告できる種類の 1 つで、
    すでに 3 件（題材1・題材2・題材3）登録されているので、出るべきものが出ていなかった。
    """
    out: dict[str, list[str]] = {}
    if not THEMES.exists():
        return out
    for line in THEMES.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        t = json.loads(line)
        if t.get("side") != "candidate":
            continue
        el = t.get("elements") or []
        if isinstance(el, str):
            try:
                el = json.loads(el or "[]")
            except ValueError:
                el = []
        out[str(t.get("id"))] = [w for w in (_word(e) for e in el) if w]
    # **手で入れた札も語彙に入れる。** 入れた本人が「なぜ出てきたか」で自分の語を
    # 見つけられないと、入れたことが効いているのか分からない（`hand_themes`）。
    for sid, h in HT.load().items():
        if not out.get(str(sid)):
            out[str(sid)] = [w for w in (_word(e) for e in (h.get("elements") or [])) if w]
    return out


def _word(e) -> str:
    """要素 1 つから語を取り出す。**古い形（文字列）も読む** ──
    保存の形が変わっても、過去に書いた行を落とさない。"""
    if isinstance(e, str):
        return e
    if isinstance(e, dict):
        w = e.get("word")
        return w if isinstance(w, str) else ""
    return ""


def vocabulary(stage_id: str, cands: dict, themes: dict) -> list[tuple[str, str, str]]:
    """その公演について照合できる語の一覧。(種類, 語, どこから来たか)。"""
    c = cands.get(str(stage_id))
    if not c:
        return []
    out: list[tuple[str, str, str]] = []
    # **手で入れた出演者・作り手も足す。** 公演ページの抽出は役職ごとに 1 行しか
    # 拾えない書式があり（実測）、取れている役職でも全員は取れていないことがある。
    # `HT.merge_fields` は消さずに足すので、公演ページの分はそのまま残る
    machine_fields = c.get("fields") or {}
    hand_fields = (HT.load().get(str(stage_id)) or {}).get("fields") or {}
    merged_fields = HT.merge_fields(machine_fields, hand_fields)
    machine_people = set(M.parse_credits(machine_fields))
    for role, person in M.parse_credits(merged_fields):
        src = (f"{role}（公演ページのクレジット）" if (role, person) in machine_people
               else f"{role}（自分で入れた分）")
        out.append((KIND_PERSON, person, src))
    if c.get("group"):
        out.append((KIND_GROUP, c["group"], "公演団体"))
    if c.get("title"):
        out.append((KIND_WORK, c["title"], "題名"))
    for w in themes.get(str(stage_id), []):
        out.append((KIND_THEME, w, "公演ページから読み取った題材"))
    return out


def terms_in(text: str, vocab: list[tuple[str, str, str]]) -> list[dict]:
    """理由の文に出ている語だけを返す。**手元の正解の一覧との照合であって、推測ではない。**"""
    t = nz(text)
    if not t:
        return []
    seen, out = set(), []
    for kind, word, src in vocab:
        w = nz(word)
        if len(w) < MIN_LEN or w not in t or (kind, w) in seen:
            continue
        seen.add((kind, w))
        out.append({"kind": kind, "word": word, "source": src})
    # **長い語を先に出す。**「作り手17」と「作り手17（劇団6）」の両方が当たったとき、
    # 短いほうだけを登録すると別人まで拾う
    out.sort(key=lambda d: -len(d["word"]))
    return out


def promotions() -> list[dict]:
    """理由の文から拾った、**まだ申告に無い**語の一覧。

    **押した本人に返る形で出す** ── ここから登録すれば、その名前の公演は次から
    件数の制限なしに新着に出る（企画書 1 章の「お気に入り」）。
    """
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT r.stage_id, r.note, r.updated_at, r.interest,"
        " (SELECT p.title FROM presented p WHERE p.stage_id = r.stage_id LIMIT 1) AS title"
        " FROM reaction r WHERE r.note IS NOT NULL AND TRIM(r.note) <> ''"
        " ORDER BY r.updated_at DESC")]
    con.close()
    if not rows:
        return []
    cands, themes = _cands(), _themes()
    dec = RC.load_declared()
    # **種類をまたいで、すでに追っている語は出さない。** 種類ごとに見ていたため、
    # 原作者として登録済みの「作品3」が題材の候補として出ていた ── **すでに
    # 新着が届く名前を「追いますか？」と聞くことになる。** 種類は提案の文に添える
    # ものであって、追っているかどうかの判定は語で決まる
    already = {nz(w) for v in dec.values() for w in v}
    agg: dict[tuple[str, str], dict] = {}
    for r in rows:
        for hit in terms_in(r["note"], vocabulary(r["stage_id"], cands, themes)):
            key = (hit["kind"], nz(hit["word"]))
            if key[1] in already:
                continue
            d = agg.setdefault(key, {**hit, "n": 0, "notes": [], "titles": []})
            d["n"] += 1
            if r["note"] not in d["notes"]:
                d["notes"].append(r["note"])
            if r["title"] and r["title"] not in d["titles"]:
                d["titles"].append(r["title"])
    # 何度も書かれた語を先に出す（**重なったものを先に出す** ── 根拠の重なりが順位である）
    return sorted(agg.values(), key=lambda d: (-d["n"], -len(d["word"])))


# ---------------------------------------------------------------- 見送った理由
#
# 起案者の指摘（2026-08-24）──「今なぜ興味ないのかで入力した理由は今後の推薦には
# 反映されていますか」。**反映していなかった。**
#
# ## 拾い方が、興味ありの側とは逆になる
#
# 興味ありの理由は**名前**が書かれるので、その公演のクレジットという正解の一覧と
# 突き合わせれば足りた（`terms_in`）。**見送った理由に書かれるのは、その公演の
# クレジットに無い言葉である** ── 実データの 5 件は「バレエ」「オペラ」「2.5舞台」
# 「ファンタジー」で、**そのうち 4 件はその公演の語彙に 1 つも当たらなかった。**
# 「お気に入り76」は語彙にあるが、**文に書かれた「バレエ」はその部分文字列**なので、
# 語彙の側から文を探す向きでは当たらない。
#
# ## だから、文から語を取り出して、これから観られる公演に当ててみる
#
# **当たる件数がそのまま、その語を出さないことの意味である。** 手元の 1,301 件に
# 1 件も当たらない語（「話題」「興味」）は候補にしない ── **押しても何も変わらない
# 選択肢を並べない**（都道府県・月の札と同じ規則）。
#
# **広すぎる語は候補にしない。** 「舞台」は 51 件に当たるが、それを外すのは
# 「演劇を観ない」と言っているのに近い。**この仕組みそのものを否定する語**は、
# 拾わないほうが親切である。
TOKEN = __import__("re").compile(r"[ァ-ヶー]{3,}|[一-龥]{2,}|[A-Za-z0-9][A-Za-z0-9.]{2,}")
# **この仕組みの前提そのものを指す語。** 拾っても外す意味が無い
STOP = ("舞台", "公演", "演劇", "観劇", "興味", "作品", "劇場", "話題", "内容")
MAX_SHARE = 0.15     # これから観られる公演の 15% を超えて当たる語は広すぎる


def _pool() -> list[str]:
    """これから観られる公演を、照合できる 1 本の文字列にして返す。

    **題名・団体・劇場・出演・題材を全部入れる。** 「オペラ」は題名に出ないことがあり
    （「イタリアのトルコ人」）、**劇場名（劇場3 オペラ劇場）で分かる。**
    """
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "tools" / "taguri"))
    import app as APP
    up = APP._upcoming_index()
    out = []
    for sid, c in up["rows"].items():
        f = c.get("fields") or {}
        out.append(nz(" ".join([c.get("title") or "", c.get("group") or "",
                                c.get("theater") or "", f.get("出演", "") or "",
                                " ".join(up["themes"].get(str(sid)) or [])])))
    return out


def pool_hits(word: str, pool: list[str] | None = None) -> int:
    """その語が、これから観られる公演の何件に当たるか。"""
    w = nz(word)
    if len(w) < MIN_LEN:
        return 0
    return sum(1 for b in (pool if pool is not None else _pool()) if w in b)


def demotions() -> list[dict]:
    """見送った理由の文から拾った、**出さない語の候補**。

    **決めるのは本人である。** 機械がやるのは「文から語を取り出し、何件に当たるかを
    数える」ところまでで、外すかどうかは押して確定していただく ── 候補を消す判断を
    代理の指標で行わない、というこれまでの方針と同じである。
    """
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT r.stage_id, r.note_no, r.updated_at,"
        " (SELECT p.title FROM presented p WHERE p.stage_id = r.stage_id LIMIT 1) AS title"
        " FROM reaction r WHERE r.note_no IS NOT NULL AND TRIM(r.note_no) <> ''"
        " ORDER BY r.updated_at DESC")]
    con.close()
    if not rows:
        return []
    pool = _pool()
    already = {nz(w) for w in RC.load_declined()}
    cap = max(1, int(len(pool) * MAX_SHARE))
    agg: dict[str, dict] = {}
    for r in rows:
        for w in dict.fromkeys(TOKEN.findall(r["note_no"] or "")):
            if w in STOP or nz(w) in already:
                continue
            n_hit = pool_hits(w, pool)
            if not n_hit or n_hit > cap:
                continue
            d = agg.setdefault(nz(w), {"word": w, "n": 0, "hits": n_hit,
                                       "notes": [], "titles": []})
            d["n"] += 1
            if r["note_no"] not in d["notes"]:
                d["notes"].append(r["note_no"])
            if r["title"] and r["title"] not in d["titles"]:
                d["titles"].append(r["title"])
    # **何度も書かれた語を先に出す**（重なった根拠を先に出す、と同じ規則）
    return sorted(agg.values(), key=lambda d: (-d["n"], -d["hits"]))


def stats() -> dict:
    con = sqlite3.connect(DB)
    n_note = con.execute("SELECT COUNT(*) FROM reaction"
                         " WHERE note IS NOT NULL AND TRIM(note) <> ''").fetchone()[0]
    # **`screen_tour`（同じ作品の他会場へ広げた行）は数えない**（起案者の指摘・
    # 2026-08-26 で `on_react` が反応を作品単位に広げるようになった分）。1 回押すと
    # ツアーの会場数ぶん行が増えるので、そのまま数えると押した回数より多く出る
    # （`feedback._interest` と同じ理由）
    n_int = con.execute("SELECT COUNT(*) FROM reaction"
                        " WHERE interest=1 AND source != 'screen_tour'").fetchone()[0]
    con.close()
    return {"理由が書かれた反応": n_note, "興味ありの反応": n_int,
            "昇格候補": len(promotions())}


if __name__ == "__main__":
    print(stats())
    for p in promotions()[:20]:
        print(f"  {p['kind']}「{p['word']}」 ×{p['n']}  ← {p['source']}"
              f"  ／理由: {p['notes'][0][:40]}")
