#!/usr/bin/env python3
"""ステイジーズカレンダーを母集団に足す。**CoRich に載らない公演を拾うため。**

## なぜ要るのか ── 2 つの情報源はほとんど重なっていない

**CoRich だけでは大きく抜ける。**（2026-08-24 の実測）

| | 件数 |
|---|---|
| カレンダーの、まだ初日を迎えていない公演 | 686 件 |
| **そのうち、CoRich から集めた候補に見当たらないもの** | **444 件**（東京 350） |

**劇団6の本公演もここにしか無い** ── 「あしあと」10/16〜28（劇団6アトリエ）、
「みつ豆」11/28〜12/5（紀伊國屋サザンシアター）。CoRich では 0 件だった。

**企画書 5 章はもともとこの役割分担を書いている** ──「母集団の網羅性はカレンダー側が
担保し、CoRich は『クレジットが取れる候補』を供給する役割にする」。**実装が
CoRich だけになっていた。**

## 「公演名の列が無い」は古い

[検証 015](../../docs/verification/015-first-real-recommendation.md) は
「カレンダーには公演名の列が無いので人物で照合できない」と判定して CoRich に移ったが、
**いま引くと `公演タイトル` の列がある。** ほかに `公演団体名`・`劇場名`・`都道府県`・
`初日`・`楽日`・`リンク` があるので、**団体の照合はこれだけでできる。**

## クレジットは別の段で取る

**既定ではクレジットを取りに行かない。**

- **既定** ── 一覧の情報だけで候補にする。作り手の名簿（網 B）とあらすじ（網 C）の点は
  0 になるが、**候補としては生きている**。お気に入りの団体照合と、「初日までに 1 回出す」の
  対象には入る（クレジットが取れないことは候補から消す理由にならない ── 検証 037）
- **`--credits`** ── リンク先の公式サイトを辿ってクレジットを取る（`--fetch` の段で走らせる）

## 2 度目の短縮 ── 毎月、同じ失敗を取り直していた（2026-08-24）

起案者の指摘 ──「[5] ステイジーズカレンダーの取り込みに時間がかかっている。短縮して」。
下の並列化のあとも、**`--fetch` のときの段 5 は分単位でかかっていた。** 測って分かったのは、
遅さの中身が 3 つに分かれることだった。

| 直したこと | なぜ |
|---|---|
| **到達できなかった先を 30 日控える** | 控えていなかったので、**毎月の実行が毎回すべての失敗を取り直していた。** 成功だけを控えていては、落ちる先は永久に毎回 1 件ずつ待つ相手になる（`fetch_official_credits.FAILS`） |
| **諦めるまでを 25 秒 → 8 秒に** | **返事の無い相手 1 件が、そのまま 1 本の並列枠を 25 秒占める。** 到達できた先の中央値は 1 秒ほどなので、8 秒待って返らない先から取れる見込みは薄い |
| 同時に辿る本数を 8 → 12 に | 上の 2 つで枠が空くようになったので、増やした分がそのまま効く |

**実測（2026-08-24）**

| | 時間 |
|---|---|
| `--credits` 無し（毎回の実行） | **1.6 秒** |
| `--credits` あり・控えが揃っている | **3.5 秒** |
| `--credits` あり・控えの無い 305 件を全部取りに行く | **63 秒** |

## これ以上は縮められない ── 下限は x.com の 56 件である

**並べ方を変える案は、測って落とした。** 辿る先 470 件のうち **56 件が x.com に集まって
おり**、同じ相手には 1.1 秒に 1 回を守るので、**その鎖だけで 62 秒**かかる。ホストごとに
鎖を組んで並べ替えても 67 秒 → 62 秒にしかならない（実測のシミュレーション）。
**x.com を飛ばせば速くなるが、控え 18 件のうち 4 件でクレジットが取れている**ので、
候補を消す側には倒さない（下の判断と同じである）。

## 遅かったのは通信ではなく、直列にしていたことだった

起案者の指摘（2026-08-24）──「ステイジーズカレンダーの取り込みに時間がかかってる」。
**25 分ほどかかっていた。** 原因を測ったところ、通信そのものは速かった。

| 測ったこと | 実測 |
|---|---|
| 辿る先の件数 | 470 件 |
| **その先のホストの種類** | **313 個**（1 ホストあたり平均 1.5 件） |
| 1 件の到達にかかる時間 | 0.4〜2.6 秒（中央値 1 秒ほど） |
| 到達できなかった先 | 14 件試して **0 件** |

**直列にしていた理由が 2 つあり、どちらも要らなかった。**

1. **呼ぶ側が 1 件ごとに 1 秒眠っていた。** `OF.get` は控えがあれば通信せずに返すのに、
   眠るほうは通信したかどうかを見ていない ── **通信が 1 回も起きない実行でも
   470 秒（7.8 分）かかっていた。** 眠るのをやめた（間隔は `OF.get` が 1 か所で守る）
2. **間隔が全体に掛かっていた。** 辿る先は相手のサイトであって 1 つのサーバーではない。
   313 ホストに散っているのに全体で 1 秒に 1 件に絞るのは、**無関係な相手を待つために
   313 倍きつい制限を自分に掛けている。** ホストごとの間隔に変え、別の相手へは同時に行く

**礼儀は落としていない。** 1 つの相手には 1.1 秒に 1 回までを守る。同じホストに集まって
いる先（x.com に 74 件）は `OF.get` の側で直列になる ── それが礼儀の単位である。

**x.com を飛ばす案は落とした。** 74 件が 1 ホストに集まっており、飛ばせば目に見えて速く
なるが、**控え 104 件を数えたら 25 件（24%）でクレジットが取れていた。**
候補を消す側には倒さない。

## 制約

- **更新は月末ごろ。** 月の途中で発表された公演は次の更新まで載らない
- **首都圏中心。** 拾える 444 件のうち東京が 350 件
- **商用利用はご遠慮ください**とされている。利用者 1 名の個人利用なので範囲内だが、配布はしない
"""

from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import re
import sys
import threading
import time
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "credits"))
CAND = ROOT / "data" / "review" / "candidates.jsonl"
FAV = ROOT / "data" / "review" / "favourites.jsonl"
OUT = ROOT / "data" / "review" / "calendar.jsonl"

SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"
UA = "taguri/1.0 (personal, 1req/sec)"
# 都道府県の書き方を候補側に揃える（カレンダーは「東京」、CoRich は「東京都」）
SUFFIX = {"東京": "東京都", "大阪": "大阪府", "京都": "京都府", "北海道": "北海道"}


def key(s: str) -> str:
    """題名を突き合わせる鍵。**記号を落として比べる** ── 同じ公演が「―」と「~」で
    書き分けられていて、別物と数えたことがある。"""
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ン一-龥ー]", "", s).lower()


def pref_of(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if s in SUFFIX:
        return SUFFIX[s]
    return s if s[-1] in "都道府県" else s + "県"


def fetch_rows() -> tuple[list[dict], str]:
    """カレンダーを 1 回のダウンロードで読む。**1 件ずつ巡回しない。**"""
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(body)))
    updated = next((c for r in rows[:3] for c in r if "更新" in c), "")
    hi = next(i for i, r in enumerate(rows) if any("都道府県" in c for c in r))
    head = [c.strip() for c in rows[hi]]
    col = {c: i for i, c in enumerate(head) if c}
    need = ("公演タイトル", "公演団体名", "劇場名", "都道府県", "初日", "楽日", "リンク")
    missing = [c for c in need if c not in col]
    if missing:
        raise SystemExit(f"カレンダーの列が変わっています（無い列: {missing}）")
    out = []
    for r in rows[hi + 1:]:
        if len(r) <= col["楽日"] or not r[col["公演タイトル"]].strip():
            continue
        out.append({c: r[col[c]].strip() for c in need}
                   | {"ID": r[col["ID"]].strip() if "ID" in col else ""})
    return out, updated


def as_date(s: str):
    m = re.match(r"(20\d\d)/(\d{1,2})/(\d{1,2})", (s or "").strip())
    return datetime.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def known_keys() -> set[str]:
    """すでに手元にある公演の題名の鍵。

    **終わった公演は数えない。** `fetch_candidates.py --keep-days` は手で足す欄の候補として
    終演した公演も残すが、**この集合は「もう手元にあるから足さなくてよい」の判定に使う。**
    `already()` は頭 8 文字の一致と含み合いでも同じものとして扱うので、**終演した公演の
    題名が入っていると、同じ戯曲の新しい上演がカレンダーから足されなくなる**
    （「ハムレット」は 1 年に何本もある）。**候補を消す側に倒さない。**
    """
    out = set()
    for f in (CAND, FAV):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("ended"):
                continue
            out.add(key(r["title"]))
    return out


def already(k: str, known: set[str], heads: set[str]) -> bool:
    """同じ公演が手元にあるか。**完全一致では足りない。**

    実測 ── CoRich は「イタリアのトルコ人」、カレンダーは「イタリアのトルコ人<新制作>」で、
    **同じ公演が 2 件並んだ。** 副題・<新制作>・全角括弧の付き方が情報源で違うので、
    **頭 8 文字の一致と、片方がもう片方を含む場合も同じものとして扱う。**
    """
    if not k:
        return True
    if k in known:
        return True
    if len(k) >= 8 and k[:8] in heads:
        return True
    return any(len(x) >= 6 and (k in x or x in k) for x in known)


def to_candidate(r: dict) -> dict:
    """候補の形にそろえる。**同じ形にしないと、下流が別扱いになる。**"""
    period = f"{r['初日']} ~ {r['楽日']}" if r["楽日"] else r["初日"]
    return {
        # **鍵は分けておく。** CoRich の stage_id と混ざると、別の公演を同じものとして
        # 抑制してしまう（反応・提示の記録はこの鍵で引く）
        "stage_id": f"cal{r['ID'] or key(r['公演タイトル'])[:12]}",
        "title": r["公演タイトル"], "group": r["公演団体名"],
        "theater": r["劇場名"], "pref": pref_of(r["都道府県"]),
        "price": "", "period": period, "status": "",
        "source": "ステイジーズカレンダー",
        # **公式サイトの URL は候補と同じ欄に入れる。** 画面の「公式サイトを開く」は
        # ここを読む（欄名を変えると、この 1 群だけリンクが出なくなる）
        "fields": {"公式／劇場サイト": r["リンク"], "劇場": r["劇場名"], "期間": period},
        "venue": r["劇場名"]}


def add_credits(rows: list[dict], jobs: int, limit: int) -> None:
    """リンク先の公式サイトからクレジットを取る。**相手のサイトごとに 1.1 秒に 1 回。**

    ## 以前は、通信が 1 回も起きない実行でも件数ぶん眠っていた

    `OF.get` は控えがあれば通信せずに返し、通信するときは自分で間隔を空ける。
    **そこへ重ねて 1 件ごとに `time.sleep(1.0)` していた** ので、470 件を全部控えから
    読むだけの実行でも 7.8 分かかっていた。**眠るのをやめた** ── 間隔は `OF.get` が
    1 か所で守る。

    ## 別の相手へは同時に行く

    実測（2026-08-24）── **470 件のリンク先は 313 ホストに散っており、1 ホストあたり
    平均 1.5 件しかない。** 到達にかかるのは 1 件あたり 0.4〜2.6 秒（中央値 1 秒ほど）で、
    落ちた先は 14 件試して 0 件だった。**遅いのは通信ではなく、直列にしていたことである。**

    | | 470 件を辿るのにかかる時間 |
    |---|---|
    | 以前（全体で 1 秒に 1 件＋1 件ごとに 1 秒眠る） | **25 分ほど** |
    | 眠るのをやめる | 17 分ほど |
    | ホストごとの間隔にする | 9 分ほど |
    | **さらに別の相手へ同時に行く（既定 8 並列）** | **2 分ほど** |

    **1 つの相手を速く叩くわけではない。** 同じホストに集まっている先（x.com に 74 件）は
    `OF.get` の側で直列になる ── それが礼儀の単位である。
    """
    import fetch_official_credits as OF
    from concurrent.futures import ThreadPoolExecutor
    todo = [r for r in rows if r["fields"].get("公式／劇場サイト", "").startswith("http")]
    todo = todo[:limit] if limit else todo
    if not todo:
        print("  辿る先がありません")
        return
    n_ok, n_done = 0, 0
    lock = threading.Lock()

    def one(r: dict) -> None:
        nonlocal n_ok, n_done
        try:
            html, _ = OF.get(r["fields"]["公式／劇場サイト"])
            got = OF.roles_in(OF.to_text(html))
        except Exception:                                            # noqa: BLE001
            got = {}
        with lock:
            n_done += 1
            if got:
                # **書き込む先は行ごとに違う**ので、ここで直列にしても待ちは増えない
                r["fields"].update({k: v for k, v in got.items() if v})
                n_ok += 1
            if n_done % 40 == 0 or n_done == len(todo):
                print(f"    クレジット {n_done}/{len(todo)}（取れた {n_ok}）", flush=True)

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(jobs, 1)) as ex:
        list(ex.map(one, todo))
    n_skip = OF.save_fails()
    print(f"  クレジットが取れたのは {n_ok}/{len(todo)} 件"
          f"（{time.monotonic() - t0:.0f} 秒・{jobs} 並列）"
          + (f"／到達できなかった先 {n_skip} 件は控えたので、次からは飛ばします"
             if n_skip else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--credits", action="store_true",
                    help="リンク先の公式サイトからクレジットも取る（同じ相手へは 1.1 秒に 1 回）")
    ap.add_argument("--limit", type=int, default=0, help="--credits で辿る件数の上限")
    ap.add_argument("--jobs", type=int, default=12,
                    help="同時に辿る本数。**同じ相手へは 1.1 秒に 1 回を守る**ので、"
                         "増やしても 1 つのサイトを速く叩くことにはならない")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)

    rows, updated = fetch_rows()
    print(f"カレンダー {len(rows)} 件を読みました（{updated}）")
    # **楽日を過ぎたものは落とす。初日で切らない** ── 上演中の公演は、お気に入り・追跡・
    # 観る予定と「間に合わなかった」の数え上げに要る（推薦枠から外すのは recommend2 の側）
    alive = [r for r in rows if (e := as_date(r["楽日"] or r["初日"])) and e >= today]
    known = known_keys()
    heads = {x[:8] for x in known if len(x) >= 8}
    fresh = [r for r in alive if not already(key(r["公演タイトル"]), known, heads)]
    print(f"  楽日が今日以降 {len(alive)} 件／**手元の候補に無い {len(fresh)} 件**")
    out = [to_candidate(r) for r in fresh]
    if a.credits:
        print(f"  リンク先の公式サイトを辿ります"
              f"（同じ相手へは 1.1 秒に 1 回・{a.jobs} 並列）…")
        add_credits(out, a.jobs, a.limit)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                   encoding="utf-8")
    print(f"書き出し: {OUT}（{len(out)} 件）")
    if not a.credits:
        print("  **クレジットは取っていません**（`--credits` で取ります）。"
              "名簿とあらすじの点は 0 になりますが、候補としては生きています ── "
              "お気に入りの団体照合と「初日までに 1 回出す」の対象には入ります。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
