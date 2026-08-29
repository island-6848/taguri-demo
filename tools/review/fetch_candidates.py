#!/usr/bin/env python3
"""これから観られる公演を、公演名とクレジットつきで集める。

## なぜ CoRich から取るのか

ステイジーズカレンダーは母集団として使うが、**公演名の列が無い**（都道府県・劇場名・
公演団体名・初日・楽日・リンクだけ）。そのため候補を人物で照合できず、
[検証 015](../../docs/verification/015-first-real-recommendation.md) では網 B の寄与が 0 件だった。

CoRich は**初日で絞った一覧が引け、各公演のページに公演名とクレジットが載っている。**
1 か所で済むので、カレンダー → リンク先 → 題名 → CoRich と辿るより取得回数が少ない。

**カレンダーを捨てるわけではない。** 母集団の網羅性はカレンダー側が担保し、
CoRich は「クレジットが取れる候補」を供給する役割にする。

## 「初日が今日以降」で引くと、開催中の公演が落ちる

**取ってくる範囲と、推薦に出す範囲は別である。**

推薦に出すのは**まだ初日を迎えていない公演だけ**である（企画書 1 章「初日を過ぎた公演は
出さない ── 上演中の公演について、このシステムは何も言わない」）。**絞り込みは
`recommend2.py` の側で掛ける。**

**それでも上演中の公演は取ってくる。** お気に入り（登録した名前の公演は内容を問わず
知らせる）・追跡（興味ありを押したもの）・観る予定は、上演が始まってからも出る束であり、
**間に合わなかったことを数えるにも、上演中の公演が手元に無いと分からない。**
CoRich の検索条件は初日にしか掛からないので、`start_date = 今日` で引くと
**今まさに上演している公演が全部消える。** そこで**初日をさかのぼって引く。**

## 終わった公演も一定期間は残す（`--keep-days`）

起案者の指示（2026-08-24）──「候補を集めるときに終わった公演も一定期間残すように
してほしい」。

**きっかけは、手で足せなかったことである。** 今年観た『るつぼ The Crucible』
（東京芸術劇場・2026/03/14〜03/29）を手で足そうとしたところ、**候補に 1 件も出なかった。**
手で足す欄の候補は手元の 3 か所（自分の記録・この候補・公演ページの控え）からしか
出さないので、**楽日を過ぎた公演はどこにも無い。** 券を買った記録もメールに無かった
（届いていたのは発売の案内だけで、購入確認ではない）ため、記録の側にも出てこなかった。

**招待・当日券・人に取ってもらった観劇は、購入確認メールに残らない。** その分を手で
足すのは観てから数週間〜数か月後になるので、**候補が「これから」しか持たないと、
いちばん手で足したい公演が候補に出ない。**

| | 何を | どうする |
|---|---|---|
| 楽日が今日以降 | これから／上演中 | 従来どおり。公演ページを取ってクレジットを入れる |
| 楽日が `--keep-days` 日以内 | 終わったが最近 | **候補に残す。ただし公演ページは取りに行かない**（`ended: true`） |
| それより古い | 終わって久しい | 落とす。手で足す欄から題名で探せる（`link_works.search_stages`） |

**終わった公演のページを取りに行かない**のが要点である。手で足す欄が候補に求めるのは
題名・団体・劇場・都道府県・期間で、**これは一覧の行にすべて載っている。** クレジットが
要るのは推薦の側だが、**終わった公演は推薦のどの束にも入らない**（`recommend2.py` が
`end < today` で落とす）ので、取っても使い道が無い。実測では、この判断で
**約 2000 件ぶんの取得（1 リクエスト/秒で 35 分ほど）が要らなくなった。**

**あらすじも取らない**（`extract_theme_llm.py` が `ended` を飛ばす）。LLM を呼ぶ行は、
規則で届かないことを示せる場合だけに置く方針であり、**推薦に出ない公演のあらすじは
どこからも読まれない。**

## 前回の候補を引き継ぐ（取得 0 回）

**書き出しはファイルの入れ替えなので、一覧に出てこなかった公演はその場で消える。**
上演期間の長い公演（実測の最長は 216 日）は初日が `--since-days` より前になり、
**楽日はまだ残っているのに一覧から漏れる。** そこで**前回の候補のうち、まだ残す期間に
入っているものを引き継ぐ** ── 取得は 1 回も増えない。

引き継ぎには副産物がある。**上演中に取った公演は、終わってもクレジットを持ったまま
残る** ── 終わった公演のページを取りに行かなくても、日が経つほど材料の付いた
終演公演が増えていく。

## `--since-days` は `--keep-days` から決める

一覧の条件は**初日**に掛かるので、「楽日が 180 日以内」を拾うには**初日をそれより前まで
さかのぼる**必要がある。上演日数は中央値 2 日・99 パーセンタイル 44 日だったので、
**`--keep-days + 45` を既定にする**（指定すれば上書きできる）。ここから漏れる長期公演は、
上の引き継ぎが受け持つ。

## 一覧の行から先に絞る

一覧ページには公演名・団体・劇場・期間・料金が載っている（クレジットだけが無い）。
**期間は一覧の時点で分かるので、残す期間より古いものはページを取りに行かない。**
1 リクエスト/秒に抑えている以上、取得回数がそのまま所要時間になる。

    python3 tools/review/fetch_candidates.py                    # 既定（残す 180 日／さかのぼる 225 日）
    python3 tools/review/fetch_candidates.py --keep-days 0      # 従来どおり「楽日が今日以降」だけ
"""

from __future__ import annotations

import argparse
import datetime
import html as htmlmod
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools" / "credits"))
from fetch_credits import get, credits_of, BASE      # noqa: E402
import unicodedata                                   # noqa: E402

OUT = ROOT / "data" / "review" / "candidates.jsonl"
SCAN = ROOT / "data" / "review" / "candidates_scan.json"

ROW = re.compile(r'<a href="/stage/(\d+)" class="list-group-item[^"]*">(.*?)</a>', re.S)


def txt(s: str) -> str:
    return unicodedata.normalize("NFKC", htmlmod.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def pick(block: str, cls: str) -> str:
    m = re.search(rf'<p class="{cls}">(.*?)</p>', block, re.S)
    return txt(m.group(1)) if m else ""


def listing(page: int, y: int, m: int, d: int) -> list[dict]:
    q = urllib.parse.urlencode({
        "search": 1, "sort": "start_asc", "page": page,
        "stage[start_date(1i)]": y, "stage[start_date(2i)]": m, "stage[start_date(3i)]": d,
    })
    html = get(f"{BASE}/stage/search?{q}")
    rows, seen = [], set()
    for sid, block in ROW.findall(html):
        if sid in seen:
            continue
        seen.add(sid)
        period = pick(block, "period")
        # **都道府県は劇場名の中の <span class="pref"> にある。** NFKC が全角括弧を
        # 半角に潰すので、剥がす前の HTML から取る
        mp = re.search(r'<span class="pref">(.*?)</span>', block, re.S)
        rows.append({
            "stage_id": sid,
            "title": pick(block, "stage"),
            "group": pick(block, "group"),
            "theater": re.sub(r"\(.*?\)$", "", pick(block, "theater")).strip(),
            "pref": txt(mp.group(1)).strip("()（）") if mp else "",
            "price": pick(block, "price"),
            "period": re.sub(r"(公演)?(開幕前|上演中|終了)$", "", period).strip(),
            "status": (re.search(r"(開幕前|上演中|終了)", period) or [None, ""])[1],
        })
    return rows


def period_end(period: str):
    ms = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ms:
        return None
    y, m, d = ms[-1]
    return datetime.date(int(y), int(m), int(d))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # **一覧のページ数の上限を上げた。** 1 ページ 20 件で、初日を 225 日さかのぼると
    # 実測 5,383 件（270 ページ）になる ── 200 ページで打ち切ると**古い側が丸ごと欠ける。**
    # 欠けても一覧は最後まで読めたように見えるので、上限で落ちたことが出力に出ない
    ap.add_argument("--pages", type=int, default=400)
    ap.add_argument("--today", default="2026-08-20")
    ap.add_argument("--no-synopsis", action="store_true",
                    help="あらすじの抽出を走らせない。**既定では走らせる** ── 取得と加工を"
                         "分けると、片方だけ進んだ状態が出力に出る")
    ap.add_argument("--keep-days", type=int, default=180,
                    help="楽日を過ぎた公演を何日ぶん候補に残すか。0 で従来どおり"
                         "「楽日が今日以降」だけになる")
    ap.add_argument("--since-days", type=int, default=None,
                    help="初日を何日さかのぼって引くか。既定は --keep-days + 45"
                         "（上演日数の 99 パーセンタイルが 44 日）")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)
    # **さかのぼる日数は、残す日数から決める。** 一覧の条件は初日に掛かるので、
    # 「楽日が 180 日以内」を拾うには初日をそれより前まで見に行かないと 1 件も入らない
    since = a.since_days if a.since_days is not None else a.keep_days + 45
    frm = today - datetime.timedelta(days=since)
    keep_from = today - datetime.timedelta(days=max(a.keep_days, 0))
    print(f"初日 {frm} 以降を走査し、楽日 {keep_from} 以降を残します"
          f"（残す {a.keep_days} 日／さかのぼる {since} 日）", flush=True)

    rows: list[dict] = []
    seen: set[str] = set()
    for p in range(1, a.pages + 1):
        got = listing(p, frm.year, frm.month, frm.day)
        if not got:
            break
        for r in got:
            if r["stage_id"] in seen:
                continue
            seen.add(r["stage_id"])
            end = period_end(r["period"])
            # **残す期間より古いものはここで落とす。** ページを取りに行かない。
            # **ただし期間が読めなかった行は落とさない**（[検証 037] の A8 と同じ理由 ──
            # 読めないことは、まだ観られないことの証拠ではない）
            if end is None or end >= keep_from:
                r["period_unparsed"] = end is None
                # **終わった公演には印を付ける。** 推薦・あらすじ・クレジット取得の
                # どれもこの印で分かれるので、読む側が期間を再計算しなくて済む
                r["ended"] = bool(end and end < today)
                rows.append(r)
        print(f"  一覧 {p} ページ目 / 生存 {len(rows)} 件（走査 {len(seen)} 件）",
              end="\r", flush=True)
    if p >= a.pages:
        print(f"\n** 一覧を {a.pages} ページで打ち切った。--pages を上げること **")
    print()

    # **前回の候補を引き継ぐ。** 書き出しはファイルの入れ替えなので、一覧に出てこなかった
    # 公演はここで拾わないと消える ── 上演期間が `--since-days` より長い公演は初日が
    # 走査の外に出るが、**楽日はまだ残す期間の中にある。** 取得は 1 回も増えない。
    #
    # **引き継いだ行のクレジットはそのまま使う。** 上演中に取った公演は、終わっても
    # 材料を持ったまま残る
    #
    # **この読み込みは、引き継ぎだけでなく使い回しにも使う（起案者の指示・2026-08-26 ──
    # 取得にかかる約 15 分を縮めたい、ただし過去に空だった候補がいつまでも空のままには
    # したくない）。** 前回のファイルを 1 度だけ読み、id → 前回の行の対応表を作る
    prev_by_id: dict[str, dict] = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = str(c.get("stage_id") or "")
            if sid:
                prev_by_id[sid] = c

    carried = 0
    for sid, c in prev_by_id.items():
        if sid in seen:
            continue
        end = period_end(c.get("period") or "")
        if end is not None and end < keep_from:
            continue
        seen.add(sid)
        c["ended"] = bool(end and end < today)
        c["carried"] = True
        rows.append(c)
        carried += 1
    if carried:
        print(f"前回の候補から {carried} 件を引き継ぎました（取得はしません）")

    # **前回すでにクレジットが取れている候補は、取り直さない。** もとは「取得済みの
    # 公演も毎回取り直す」だった ── 初報の時点ではあらすじもクレジットも載っていない
    # ことがあり、**「見たことがあるか」で取り直すかどうかを決める（差分だけを取る）
    # 形では、一度空で取れた候補が二度と取り直されない**ため（この判断自体は撤回済み）。
    #
    # **ここでの条件は「見たことがあるか」ではなく「前回の中身が空だったか」である。**
    # 前回すでに役職つきクレジットが取れている候補は取り直さず使い回し、**前回空だった
    # 候補・新しく出た候補だけ、これまでどおり毎回取りに行く。** これなら取得済みの
    # 公演を再取得しない形でも、空のまま取り残される候補は生まれない。
    # **上演中に追加出演が発表される、といった後からの更新までは追わない**
    # （的中させたいのは「クレジットが 1 度も取れていない」の解消であり、
    # 取れたあとの細かな更新はこの一周の対象に入れていない）。
    reused = 0
    for r in rows:
        if r.get("carried") or r.get("ended"):
            continue
        prev = prev_by_id.get(r["stage_id"])
        if prev and prev.get("fields"):
            r["fields"] = prev["fields"]
            r["venue"] = prev.get("venue") or r["theater"]
            # **題名は一覧の行に無いことがある。** そのときだけ公演ページの <title> を
            # 見に行って直す作りだった（`todo` のループにしか無い）。使い回す行が今回の
            # 一覧でも空のままなら、前回そこで直した題名を引き継ぐ（取得はしない）
            if not r.get("title") and prev.get("title"):
                r["title"] = prev["title"]
            r["reused_credits"] = True
            reused += 1

    # **終わった公演は公演ページを取りに行かない。** 手で足す欄が要る項目（題名・団体・
    # 劇場・都道府県・期間）は一覧の行に載っており、クレジットが要る推薦の側は
    # 終わった公演を落とす ── 取っても読む先が無い
    todo = [r for r in rows if not r.get("ended") and not r.get("carried") and not r.get("fields")]
    skipped_ended = sum(1 for r in rows if r.get("ended") and not r.get("carried"))
    if reused:
        print(f"前回すでに取れているクレジットを {reused} 件 使い回しました（取得はしません）")
    print(f"候補 {len(rows)} 件 ── クレジットを取るのは {len(todo)} 件"
          f"（終わった公演 {skipped_ended} 件・使い回し {reused} 件は取りません）", flush=True)

    out, failed = [], []
    for r in rows:
        if r.get("carried"):
            out.append(r)                      # 前回の中身をそのまま持ち越す
        elif r.get("ended"):
            # **一覧から取れた分だけで候補にする。** `fields` が空でも壊れない
            # （`measure_nets` は空の表を飛ばし、`recommend2` は終演で落とす）
            out.append({**r, "venue": r["theater"], "fields": {}})
        elif r.get("fields"):
            out.append(r)                      # 前回のクレジットを使い回した行
    for n, r in enumerate(todo, 1):
        # **1 度だけ取り直す。** [検証 037](../../docs/verification/037-first-day-guarantee.md)
        # で、前日に落ちた 54 件が翌日には問題なく取れた ── その回だけの失敗が混じる
        c, err = None, ""
        for attempt in range(2):
            try:
                c = credits_of(r["stage_id"])
                break
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                if attempt == 0:
                    time.sleep(2.0)
        if c is None:
            # **クレジットが取れないことは、候補から消す理由にならない。**
            # 一覧の行から題名・団体・劇場・期間は取れているので、候補としては残す。
            # 網 B・C の強さは 0 になるが、**初日までに 1 回出す保証の対象には入る**
            out.append({**r, "fields": {}, "credits_error": err})
            failed.append(r["stage_id"])
            continue
        f = c["fields"]
        # **公演名は表（th/td）に無い。** 一覧の行から取る（無ければ <title>）。
        # 最初の実装で空欄のまま推薦を出してしまい、何の公演か分からなかった。
        title = r["title"]
        if not title:
            html = get(f"{BASE}/stage/{r['stage_id']}")
            m = re.search(r"<title[^>]*>(.{2,150}?)</title>", html, re.S)
            if m:
                title = unicodedata.normalize("NFKC", re.sub(r"\s+", " ", m.group(1))).strip()
                title = re.split(r"\s*[|｜]\s*", title)[0].strip()
        out.append({**r, "title": title, "period": c["period"] or r["period"],
                    "venue": f.get("劇場", "") or r["theater"], "fields": f})
        print(f"  {n}/{len(todo)}", end="\r", flush=True)

    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out), encoding="utf-8")
    n_ended = sum(1 for x in out if x.get("ended"))
    print(f"\n{len(out)} 件を {OUT} に書き出しました "
          f"── これから／上演中 {len(out) - n_ended} 件、終わった公演 {n_ended} 件。"
          f"（クレジットが取れなかった {len(failed)} 件も候補に残した）")

    # **走査した id を残し、前回との差分を数える。** [検証 037] では、一覧の走査から
    # 118 件が漏れていたのに、走査の中では気づけなかった。**取りこぼしを検知できる形にする**
    prev = json.loads(SCAN.read_text(encoding="utf-8")) if SCAN.exists() else {}
    now_ids = [r["stage_id"] for r in out]
    if prev.get("ids"):
        gone = sorted(set(prev["ids"]) - set(now_ids))
        added = sorted(set(now_ids) - set(prev["ids"]))
        mx = max((int(i) for i in prev["ids"]), default=0)
        fresh = [i for i in added if int(i) > mx]
        print(f"前回（{prev.get('date')}）との差分: 増えた {len(added)} 件"
              f"（うち新規登録 {len(fresh)} 件）／消えた {len(gone)} 件")
        if len(gone) > len(added):
            print("  ** 消えた件数が増えた件数を上回っている。走査の取りこぼしを疑う **")
    SCAN.write_text(json.dumps({"date": str(today), "ids": now_ids,
                                "credits_failed": failed}, ensure_ascii=False),
                    encoding="utf-8")

    # **候補を取ったら、その場であらすじも取る**（起案者の指示 ──「新しい公演を拾ってくる
    # ときは、あらすじを必ず取得してからにしましょう」）。
    #
    # **分けて走らせると、片方だけ進んだ状態が出力に出る。** 実際に候補が 818 → 863 件に
    # 増えたとき、増えた分のあらすじが無いまま推薦を出し、**192 件があらすじ未取得**のまま
    # 上位に並んだ。欠損は「取れていない」ではなく「その公演には無い」に見えるので、
    # 出力を見ても異常だと分からない。
    #
    # **増えた分だけで済む。** `extract_theme_llm.py` は同じ版・同じモデルの行を済みとして
    # 数えるので、版を上げていなければ新しい公演だけが対象になる。
    if not a.no_synopsis:
        print("\nあらすじの抽出（増えた分だけ・終わった公演は除く）…", flush=True)
        r = subprocess.run([sys.executable, str(ROOT / "tools/credits/extract_theme_llm.py"),
                            "--side", "candidate", "--no-fetch", "--batch", "8", "--jobs", "10"])
        if r.returncode != 0:
            print("  ** あらすじの抽出が失敗した。推薦を出す前に単独で走らせること **")

    # **件数の突き合わせを最後に出す。** ずれた回に気づけるようにする
    have = set()
    tp = ROOT / "data" / "credits" / "themes.jsonl"
    if tp.exists():
        for line in tp.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                d = json.loads(line)
                if d.get("side") == "candidate":
                    have.add(str(d["id"]))
    # **あらすじの検算は、あらすじを取る対象だけで数える。** 終わった公演を分母に
    # 入れると、正しく飛ばした分が毎回「未取得」として出続ける ── 数字が動かない
    # 警告は読まれなくなる
    live_ids = [str(r["stage_id"]) for r in out if not r.get("ended")]
    miss = [i for i in live_ids if i not in have]
    print(f"検算 ── 候補 {len(now_ids)} 件（うち終演 {len(now_ids) - len(live_ids)} 件は対象外）"
          f"／あらすじの行がある {len(live_ids) - len(miss)} 件／**未取得 {len(miss)} 件**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
