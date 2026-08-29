#!/usr/bin/env python3
"""お気に入りに登録した名前で、公演を**直接**引いてくる。

## なぜ要るのか ── 一覧を走査するだけでは拾えない

**これまで、お気に入りの照合先は「一覧を走査して集めた候補」だけだった。**
つまり **母集団に入っていない公演は、名前が一致するかどうかを見る機会すら無かった。**

企画書 4 章は最初からこう決めている ──「**無条件で出すと決めた対象なのだから、母集団の
制約を受ける理由がない。登録した団体・個人については、公式サイトを直接見に行く。**」
**設計にはあったが、実装が無かった。**

## 何が拾えていなかったか（2026-08-24 の実測）

登録した 13 名・団体で引くと、**手元の候補 818 件に無い公演が 19 件出てきた。**

| 登録名 | 候補に無かった公演 |
|---|---|
| 劇場3 | 6 件（『蝶々夫人』10/26、朗読会『葉葉葉』9/11 ほか） |
| 作品3 | 6 件（『お気に入り79』9/22 ほか） |
| 作り手3 | 3 件（『お気に入り59』10/6・11/27・12/3） |
| 劇団4 | 2 件（『走れメロス』10/16、『ベルト・モリゾ』11/7） |
| 劇場2 | 1 件（『イェルマ』9/21） |
| 劇団3 | 1 件 |

**表記ゆれで結果が変わることも分かった** ── 「劇団1」は 0 件、「劇団2」は 3 件。
「作り手2」は 0 件、「作り手3」は 6 件。
**登録は両方の表記を並べてあるので、引くときも全部の表記で引く。**

## 団体は「主催公演」だけを拾う

**起案者の指摘 ──「劇団4とか劇団7とか言ってるのは、客演まで興味がある人とない人がいる。
団体名を検索したときは原則主催公演の情報を拾うだけでよい。客演まで追いたい人は人名で
指定するので」。**

そこで **`団体`・`主催` で登録した名前は、公演団体名が一致するものだけ**を残す。
「劇団6の俳優が他団体の公演に出る」ものは落ちる ── 追いたい人は**その俳優の名前を
登録する**ことで拾える。**軸を分けると、登録した本人が範囲を決められる。**

実測（2026-08-24）── 「劇団6」で引ける 8 件は**すべて他団体への客演**だったので、
この規則では 0 件になる。「劇場3」の 13 件のうち、**貸館（スクールアイドル
ミュージカルなど）が落ちて主催公演だけが残る。**

## 速さ

**毎週押す処理なので、待たせない方を選ぶ。**

- **名前ごとに結果を貯める。** 同じ名前を 3 日（72 時間）以内に引いていたら、貯めた結果を
  使う（`--ttl-hours`）。**押し直しても待たされない。**

  **20 時間だった期限を 3 日に伸ばした**（2026-08-27・起案者の指示）。`run.py` は
  週 1 回のペースで使う想定なので、20 時間では次に押すころには必ず切れており、
  毎回 49 語（実測）を検索し直すぶんの待ち時間（1 語 1 秒＋新しく見つかった公演の
  クレジット取得）が、初回と同じ重さで**ほぼ毎回**かかっていた。「初回だけ約 1 分」
  という当初の想定（`run.py` 冒頭の表）に対して、実際には初回でない回もほぼ毎回
  同じだけかかっていたことになる。**週 1 回のペースなら、期限を延ばしても見逃しは
  増えない** ── どのみち次に押すまでは新着に気づけないので、押す間隔より短い期限で
  あれば十分である。**3 日にしたのは、週の途中でもう一度押す場合に備えた余白**
  （20 時間ではその余白が無く、押し直すたびに全部を引き直していた）。
- **クレジットは新しい公演の分だけ取る。** 前に取った分は貯めた結果から持ち越す
- 取得は **1 リクエスト／秒**を守る（企画書 5 章）。ここは短くしない

## 引き方

CoRich の検索には **`freeword`（「公演・団体・出演者名などを入力」）** があり、
**出演者名でも当たる。** ここに `初日が今日以降` を掛けると、その名前の今後の公演だけが出る。

**並べ替えを間違えると全部「終了」になる。** `sort=start_asc` だけを付けて初日の下限を
付けないと、**10 年前の公演から順に 20 件**返ってくる（1 度これで「0 件」と読み誤った）。

## これで拾えないもの

**CoRich に登録されていない公演は、この経路でも拾えない。**

実測（2026-08-24）── 「劇団6」で引くと **8 件**出てくるが、**そのすべてが他団体の公演に
劇団6の俳優が出るもの**（Pカンパニー・劇団1980・NLT ほか）である。**劇団6自身の本公演は
1 件も無い** ── 公式サイトには 4 本載っている（10/16〜28 アトリエの会、11/28〜12/5 本公演
『みつ豆』、地方公演 2 本）。**団体の公式サイトを直接見る経路は、まだ無い。**
"""

from __future__ import annotations

import argparse
import datetime
import html as htmlmod
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import recommend as RC                                             # noqa: E402
from fetch_credits import credits_of                               # noqa: E402

BASE = "https://stage.corich.jp"
UA = "taguri/1.0 (personal, 1req/sec)"
CAND = ROOT / "data" / "review" / "candidates.jsonl"
OUT = ROOT / "data" / "review" / "favourites.jsonl"
CACHE = ROOT / "data" / "review" / "favourites_cache.json"
# **公演団体名の一致だけを残す種類。** 客演は人名で追う（上記）
GROUP_ONLY = ("団体", "主催")
ROW = re.compile(r'<a href="/stage/(\d+)" class="list-group-item[^"]*">(.*?)</a>', re.S)


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def txt(s: str) -> str:
    return unicodedata.normalize("NFKC", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def pick(block: str, cls: str) -> str:
    m = re.search(rf'<p class="{cls}">(.*?)</p>', block, re.S)
    return txt(m.group(1)) if m else ""


def search(word: str, today: datetime.date, page: int = 1) -> list[dict]:
    """名前で引く。**初日が今日以降のものだけ**を、初日の近い順で返す。"""
    q = urllib.parse.urlencode({
        "utf8": "✓", "search": 1, "freeword": word, "freeword_type": "all",
        "sort": "start_asc", "page": page,
        "stage[start_date(1i)]": today.year, "stage[start_date(2i)]": today.month,
        "stage[start_date(3i)]": today.day})
    h = get(f"{BASE}/stage/search?{q}")
    out = []
    for sid, b in ROW.findall(h):
        period = pick(b, "period")
        mp = re.search(r'<span class="pref">(.*?)</span>', b, re.S)
        out.append({
            "stage_id": sid, "title": pick(b, "stage"), "group": pick(b, "group"),
            "theater": re.sub(r"\(.*?\)$", "", pick(b, "theater")).strip(),
            "pref": txt(mp.group(1)).strip("()（）") if mp else "",
            "price": pick(b, "price"),
            "period": re.sub(r"(公演)?(開幕前|上演中|終了)$", "", period).strip(),
            "status": (re.search(r"(開幕前|上演中|終了)", period) or [None, ""])[1]})
    return out


def nz(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").replace(" ", "").replace("　", "").lower()


def is_host(row: dict, word: str) -> bool:
    """**その団体の主催公演か。** 公演団体名に登録名が入っているかで見る。

    **劇場名では見ない** ── 「劇団6アトリエ」で上演する他団体の公演を、劇団6の主催と
    数えてしまう。**題名でも見ない** ── 題名に団体名が入るのは客演の告知に多い。
    """
    return nz(word) in nz(row.get("group") or "")


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def known_ids() -> set[str]:
    if not CAND.exists():
        return set()
    return {str(json.loads(l)["stage_id"]) for l in
            CAND.read_text(encoding="utf-8").split("\n") if l.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--pages", type=int, default=1,
                    help="1 名につき何ページまで見るか。**既定は 1** ── 1 ページ 20 件に対し"
                         "実測の最大は 13 件（劇場3）だった")
    ap.add_argument("--sleep", type=float, default=1.0, help="取得の間隔（秒）。短くしない")
    ap.add_argument("--ttl-hours", type=float, default=72.0,
                    help="同じ名前をこの時間内に引いていたら、貯めた結果を使う"
                         "（既定は 3 日 ── `run.py` の週 1 回のペースに合わせてある）")
    ap.add_argument("--force", action="store_true", help="貯めた結果を使わず全部引き直す")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)
    t0 = time.monotonic()

    dec = RC.load_declared()
    # **題材は名前ではないので引かない。** あらすじの要素と照合する軸であり、
    # 検索語にすると題名にその字が入っただけの公演を大量に拾う
    words = [(k, w) for k in ("人", "団体", "主催", "作品", "原作者") for w in dec.get(k, [])]
    cache = {} if a.force else load_cache()
    now = datetime.datetime.now()
    fresh_cut = now - datetime.timedelta(hours=a.ttl_hours)

    known = known_ids()
    found: dict[str, dict] = {}
    n_web = n_cached = 0
    for i, (kind, w) in enumerate(words, 1):
        key = f"{kind}|{w}"
        ent = cache.get(key)
        if ent and datetime.datetime.fromisoformat(ent["at"]) > fresh_cut:
            rows, how = ent["rows"], "貯めた分"
            n_cached += 1
        else:
            rows = []
            for p in range(1, a.pages + 1):
                try:
                    got = search(w, today, p)
                except Exception as e:                              # noqa: BLE001
                    print(f"  {w}: 引けなかった（{type(e).__name__}）")
                    break
                rows += got
                time.sleep(a.sleep)
                if len(got) < 20:
                    break
            cache[key] = {"at": now.isoformat(timespec="seconds"), "rows": rows}
            how = "引いた"
            n_web += 1
        # **団体・主催は主催公演だけ**（客演は人名で追う）
        if kind in GROUP_ONLY:
            keep = [r for r in rows if is_host(r, w)]
        else:
            keep = rows
        for r in keep:
            d = found.setdefault(r["stage_id"], {**r, "matched": []})
            if f"{kind}「{w}」" not in d["matched"]:
                d["matched"].append(f"{kind}「{w}」")
        drop = len(rows) - len(keep)
        print(f"  [{i}/{len(words)}] {kind}「{w}」 {how} {len(rows)} 件"
              + (f"／主催公演でない {drop} 件を落とした" if drop else "")
              + (f"／**母集団に無い {sum(1 for r in keep if r['stage_id'] not in known)} 件**"
                 if any(r["stage_id"] not in known for r in keep) else ""))

    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"\n{n_web} 件を引き、{n_cached} 件は貯めた結果を使いました（{time.monotonic() - t0:.0f} 秒）")

    # **クレジットは新しい公演の分だけ取る。** 前に取った分は持ち越す
    prev = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                r = json.loads(line)
                prev[str(r["stage_id"])] = r
    new = {k: v for k, v in found.items() if k not in known}
    todo = [(k, v) for k, v in new.items() if k not in prev or "fields" not in prev[k]]
    print(f"引けた公演 {len(found)} 件。母集団に無いのは {len(new)} 件で、"
          f"うちクレジットを取るのは {len(todo)} 件です。")
    out = []
    for k, v in new.items():
        if k in prev and "fields" in prev[k]:
            out.append({**prev[k], **{x: y for x, y in v.items() if x != "fields"}})
            continue
        try:
            c = credits_of(k)
            v = {**v, "period": c["period"] or v["period"], "fields": c["fields"],
                 "venue": (c["fields"] or {}).get("劇場", "") or v["theater"]}
        except Exception as e:                                      # noqa: BLE001
            # **クレジットが取れなくても落とさない。** お気に入りは無条件で出す束である
            v = {**v, "fields": {}, "credits_error": f"{type(e).__name__}: {e}"}
        out.append(v)
        print(f"    {len(out)}/{len(todo)} {v['title'][:26]}", flush=True)
        time.sleep(a.sleep)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
                   encoding="utf-8")
    print(f"\n書き出し: {OUT}（{len(out)} 件・全体で {time.monotonic() - t0:.0f} 秒）")
    print("**この経路で拾えないもの** ── CoRich に登録されていない公演。"
          "お気に入り82「お気に入り58」（2026/10/3-4・三重県文化会館・作り手9が出演）は"
          "題名でも団体名でも CoRich に 0 件で、公式の Tumblr にだけ載っています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
