#!/usr/bin/env python3
"""観た公演のクレジットを CoRich から取り、V3 と V21 を測る。

## 何を測るか

- **V3** 公演ページの 7 割以上から、**役職つきで**作り手の名前が取れるか（役職別に測る）
- **V21** 人物ごとの観劇本数 n の分布。**n ≥ 2 の人物が何人いるか**で、
  網 B の当たり率を人物単独で推定できるか、団体・役職へ縮約する必要があるかが決まる

**評価（◎○△×）は要らない。** クレジットさえ取れれば測れるので、V1 の履歴だけで先に測れる。

## 人名を画面に出さない

**V24（推薦の理由に出た名前のうち「知らなかった」が 2 割以上あるか）は、
当事者が人名の一覧を見た時点で測れなくなる。** 後から取り直せないので、
このスクリプトは**集計値しか表示しない。** 名前は `data/credits/` に書くだけにする。

## 直した題名で検索する

**抽出が題名を切っていると、公演ページは引けない。** 実データでは 129 作品のうち
24 件で括弧が閉じておらず、過去の公演ページに辿り着けたのは 27% だった。画面
（`/records` の「公演詳細を直す」）で直した題名があれば**それを最初の検索語にする**
（`tools/tickets/corrections.py`）── ここが埋まると、この後で LLM に読ませる本文が
**正しい公演のもの**になる（`tools/credits/extract_theme_llm.py`）。

**書き出す `mail_title` は抽出した題名のままにする。** この列は
`(date, mail_title)` として 8 か所から公演ページを引く鍵になっており、直した値で
上書きすると、直した公演のクレジットが引けなくなる。直した題名は `fixed_title`
として別に書く。

## 取得元と作法

CoRich 舞台芸術!（https://stage.corich.jp）の公演ページ。1 リクエスト/秒以下に抑え、
取得結果はファイルにキャッシュして再取得しない。

    python3 tools/credits/fetch_credits.py --run
    python3 tools/credits/fetch_credits.py --report
"""

from __future__ import annotations

import argparse
import collections
import datetime
import difflib
import gzip
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PERF = ROOT / "data" / "tickets" / "performances.jsonl"
OUT = ROOT / "data" / "credits" / "credits.jsonl"
CACHE = ROOT / "data" / "credits" / "pages"
BASE = "https://stage.corich.jp"
UA = "Mozilla/5.0 (compatible; taguri-verify/1.0; personal use)"

# クレジットの役職。**役職別に取得率を測る**ため、まとめずに持つ
ROLE_KEYS = ["出演", "脚本", "作", "演出", "翻訳", "原作", "音楽", "振付",
             "美術", "照明", "音響", "衣裳", "衣装", "舞台監督", "制作", "宣伝美術"]

_last = [0.0]


def get(url: str) -> str:
    key = CACHE / (re.sub(r"[^A-Za-z0-9]", "_", url)[-120:] + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8")
    wait = 1.1 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        html = raw.decode("utf-8", "replace")
    CACHE.mkdir(parents=True, exist_ok=True)
    key.write_text(html, encoding="utf-8")
    return html


def clean_title(t: str) -> list[str]:
    """メールの題名を検索語の候補に直す。**短いものから複数試す。**

    メールの題名には販売側の都合が付いている（〈セット券〉【Premium限定】★受付1★、
    団体名や公演回次の前置き）。**そのまま検索すると 0 件になる。**
    """
    s = unicodedata.normalize("NFKC", t)
    s = re.sub(r"[【〈\[（(].{0,24}?[】〉\]）)]", " ", s)
    s = re.sub(r"★.*?★", " ", s)
    # 販売側が付ける「4月」「7月」のような月の前置きを落とす。
    # 東宝ナビザーブなどが公演月を頭に付けるので、そのままでは 0 件になる
    s = re.sub(r"^\s*\d{1,2}\s*月\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    cands = []
    # 鉤括弧の中身がいちばん題名らしい
    for m in re.finditer(r"[『「\"]([^』」\"]{2,60})[』」\"]", s):
        cands.append(m.group(1).strip())
    cands.append(s)
    # 前置きを落とした後半
    if m := re.search(r"(?:vol\.?\s*\d+|第\d+回公演|公演)\s*(.{2,60})$", s):
        cands.append(m.group(1).strip())
    # **中核語を候補に足す。** 「KOKAMI@network vol.19『ウィングレス（wingless）−翼を持たぬ天使−』」
    # のような題名は、飾りを落とした「ウィングレス」でしか引けないことが実測で分かった。
    for c in list(cands):
        for m in re.finditer(r"[ァ-ヶー・]{4,}|[一-龥]{3,}|[A-Za-z][A-Za-z ]{3,}", c):
            cands.append(m.group(0).strip(" ・ー"))
    out = []
    for c in cands:
        c = c.strip(" 　-−ー~〜・")
        if len(c) >= 3 and c not in out:
            out.append(c)
    return out[:5]


# ================================================================ 突き合わせの規則
#
# **年が一致すればよい、という条件を撤回した**（2026-08-24 の指示）。
# もとは `if r["date"][:4] in c["period"]` の 1 行で、**題名で検索して返ってきたページの
# うち、同じ年のものなら最初の 1 件を採っていた。** 題名が合っているかも、観た日が
# 上演期間に入っているかも見ていない。
#
# 実測（2026-08-24、控え 130 件）── **観た日が結び付いたページの上演期間の外にあるのは
# 80 件（62%）。** うち明らかに別の公演だったのは 11 通り・17 行で、**のべ 117 名を名簿に
# 入れていた**（「ENTA！8」→『甘梨 Accidental Offside』、『ポルノ』→『音楽劇 ポルノスター』、
# 「ハムレット」→『少女ハムレット』など）。**「Camp」「BANG」「トラベル」のような 1 語が
# 一致しただけで通っていた。**
#
# **落とすだけにはしない。** CoRich のページは会場ごとに分かれているので、ツアーや
# 別クールでは**同じ演目の別の上演**のページに当たる。この場合、出演者はおおむね同じ
# なので名簿の材料としては生きている ── **一律に落とすと、評価済み 96 作品のうち
# 56 件しかないクレジットがさらに減る。** そこで確からしさを 2 段に分けて記録し、
# **落とすのは題名が合わないものだけにする。**

_BRACKET = re.compile(r"[【〈\[（(].*?[】〉\]）)]")


def _tkey(s: str) -> str:
    """題名を比べるための形にする。**売り方と表記の違いだけを落とす。**"""
    s = unicodedata.normalize("NFKC", s or "").replace("&#39;", "'")
    s = _BRACKET.sub("", s)
    s = re.sub(r"(ミュージカル|Musical|音楽劇|朗読劇|舞台)", "", s, flags=re.I)
    s = re.sub(r"[\s　『』「」\"'’·・~〜\-−ー!！?？,、。.]", "", s)
    return s.lower()


def _tsep(s: str) -> str:
    """区切りを残したまま、売り方と表記の違いだけを落とす。

    **前方一致を「副題が足された」と読んでよいのは、足された分が区切りで始まるときだけ
    である。** 「受取人不明」→「受取人不明 ADDRESS UNKNOWN」は副題だが、
    「ポルノ」→「ポルノスター」と「ゴドーを待ちながら」→「ゴドーを待ちながらを待ちながら」は
    語が続いているだけで、別の公演である。**区切りを消してから比べると、この 3 つが
    同じ形になってしまう。**
    """
    s = unicodedata.normalize("NFKC", s or "").replace("&#39;", "'")
    s = _BRACKET.sub(" ", s)
    s = re.sub(r"(ミュージカル|Musical|音楽劇|朗読劇|舞台)", " ", s, flags=re.I)
    s = re.sub(r"[『』「」\"'’]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


_SEP = " 　:：〜~-−ー・/|,、."


def title_agrees(mail_title: str, page_title: str) -> bool:
    """メールの題名と、ページの題名が同じ公演を指しているか。

    **前に付く飾りと、後ろに付く副題は別に扱う。** 「受取人不明」と
    「受取人不明 ADDRESS UNKNOWN」は同じ公演で、**副題が後ろに足されているだけ**である。
    いっぽう「ハムレット」と「少女ハムレット〜茜色の事件簿〜」は別の公演で、
    **こちらは前に語が足されている。** 長さの比だけで見ると前者を落として後者を通すので、
    **どちら側に足されたかを見る。**
    """
    a, b = _tkey(mail_title), _tkey(page_title)
    if len(a) < 2 or len(b) < 2:
        return False
    if a == b:
        return True
    # **副題が後ろに足されただけなら同じ公演。** ただし足された分が区切りで始まるとき
    # だけである（`_tsep` の注記 ── 「ポルノ」と「ポルノスター」を分けるため）
    x, y = _tsep(mail_title), _tsep(page_title)
    for s, l in ((x, y), (y, x)):
        # **短い語の前方一致は通さない。** 「TEAM」は「TEAM NANOSQUARE IN CONCERT」の
        # 前方一致になるが、別の公演である（実測でここだけ残った）── 飾りを落として
        # 作った検索語には 4 文字程度のものが混ざるので、下限を置く
        if len(s) >= 5 and l.startswith(s) and len(l) > len(s) and l[len(s)] in _SEP:
            return True
    # **題名の中の数字が違えば、別の公演である。** 「デカローグ 1−4」と「デカローグ 7〜10」、
    # 「vol.19」と「vol.22」は、文字としてはほとんど同じなのに中身が違う ──
    # 似ている度合いだけで見ると通ってしまう（実測でデカローグの 3 件がこれで誤った）
    da, db = tuple(re.findall(r"\d+", a)), tuple(re.findall(r"\d+", b))
    if da and db and da != db:
        return False
    # 前に語が足されているもの（「ハムレット」と「少女ハムレット〜」）は別の公演の
    # ことが多い ── 足された分がわずかなときだけ通す
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b)) >= 0.8
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.72


def title_agrees_any(words: list[str], page_title: str) -> bool:
    """**検索に使った語のどれかが一致すればよい。**

    メールの題名には団体名や公演回次が前に付く（「柿喰う客 20 周年記念公演『サバンナの掟』」）。
    **飾りを落とした語は `clean_title` がすでに作っている**ので、突き合わせも同じ語で行う。
    """
    return any(title_agrees(w, page_title) for w in words if w)


def title_close(words: list[str], page_title: str) -> bool:
    """題名の書き方は違うが、語としては重なっている。**単独では採らない。**"""
    b = _tkey(page_title)
    return any(len(k) >= 3 and (k in b or b in k) for k in (_tkey(w) for w in words if w))


def _in_period(date: str, period: str) -> bool:
    """観た日が上演期間の中にあるか。"""
    ds = re.findall(r"(20\d\d)/(\d{1,2})/(\d{1,2})", period or "")
    if not ds or not date:
        return False
    try:
        d = datetime.date.fromisoformat(date)
    except ValueError:
        return False
    first = datetime.date(*map(int, ds[0]))
    last = datetime.date(*map(int, ds[-1]))
    return first - datetime.timedelta(days=1) <= d <= last + datetime.timedelta(days=1)


def _venue_agrees(mail_venue: str, fields: dict) -> bool:
    v, w = _tkey(mail_venue), _tkey((fields or {}).get("劇場", ""))
    return bool(v) and bool(w) and (v in w or w in v)


def rank_candidate(r: dict, c: dict, words: list[str]) -> tuple[int, str]:
    """1 つの候補ページに点を付ける。返すのは (点, 確からしさ)。0 点なら結び付けない。

    **題名で通すのが基本だが、日程が一致していれば題名の書き方の違いは許す。**
    「ＡＢＣ座 ジャニーズ伝説 ２０２２」と「ABC座 10th ANNIVERSARY ジャニーズ伝説 2022
    at IMPERIAL」は同じ公演だが、飾りが多くて題名の比較では通らない ── **観た日が
    上演期間に入っていることが、題名とは別の証拠になる。**
    """
    ws = list(words) + [r.get("title") or ""]
    date_ok = _in_period(r.get("date") or "", c.get("period") or "")
    venue_ok = _venue_agrees(r.get("venue") or "", c.get("fields") or {})
    if title_agrees_any(ws, c.get("page_title") or ""):
        if date_ok and venue_ok:
            return 5, "会場と日程まで一致"
        if date_ok:
            return 4, "日程まで一致"
        if venue_ok:
            return 3, "会場まで一致"
        # **題名だけが一致した場合も残す。** ツアーや別クールで、同じ演目の別の上演の
        # ページに当たっている ── 出演者はおおむね同じなので材料としては生きているが、
        # **ポスターと日程は別の上演のものである。**
        return 1, "同じ演目の別の上演"
    # 題名では通らないが、日程という別の証拠がある場合
    if date_ok and venue_ok:
        return 4, "会場と日程が一致（題名の書き方は違う）"
    if date_ok and title_close(ws, c.get("page_title") or ""):
        return 2, "日程が一致（題名の書き方は違う）"
    return 0, ""


def best_match(r: dict, words: list[str], seen: set) -> dict | None:
    """検索語を順に試し、**いちばん点の高い候補を採る。**

    **最初に当たったものを採らない。** もとの実装は年が一致した時点で `break` して
    いたため、**より確からしい候補がその後ろにいても見に行かなかった。**
    """
    best = None
    for w in words:
        for sid in search(w):
            if sid in seen:
                continue
            seen.add(sid)
            c = credits_of(sid)
            score, why = rank_candidate(r, c, words)
            if score and (best is None or score > best[0]):
                best = (score, dict(c, match_level=why))
            if best and best[0] == 5:                # これ以上は良くならない
                return best[1]
    return best[1] if best else None


def search(word: str) -> list[str]:
    q = urllib.parse.urlencode({"search": 1, "freeword": word,
                                "freeword_type": "title", "sort": "start_desc"})
    html = get(f"{BASE}/stage/search?{q}")
    ids = []
    for m in re.finditer(r'href="/stage/(\d+)"', html):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return ids[:8]


def credits_of(stage_id: str) -> dict:
    html = get(f"{BASE}/stage/{stage_id}")
    out: dict = {}
    # **ラベルは <th>/<td> にある。** <dt>/<dd> は画面下部の案内メニューで、
    # そちらだけを拾うと「公演情報・クチコミ・団体／劇場…」が取れて中身が空になる。
    for m in re.finditer(r"<(th|dt)[^>]*>\s*([^<]{1,20}?)\s*</\1>\s*<(?:td|dd)[^>]*>(.*?)</(?:td|dd)>",
                         html, re.S):
        label = m.group(2).strip()
        body = re.sub(r"<br\s*/?>", "\n", m.group(3))
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"[ \t]+", " ", body).strip()
        if label:
            out[label] = body
    period = out.get("期間", "")
    # **ページの題名を持ち帰る。** これが無いと、検索が返した公演が本当に同じ題名の
    # 公演なのかを確かめられない ── 年だけで採っていた頃はここを見ていなかった
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    ptitle = re.split(r"[|｜]", re.sub(r"\s+", " ", m.group(1)).strip())[0].strip() if m else ""
    return {"stage_id": stage_id, "period": period, "page_title": ptitle,
            "fields": expand_staff(out)}


def expand_staff(fields: dict) -> dict:
    """「スタッフ」欄を役職ごとにばらす。

    CoRich はスタッフを 1 つの欄にまとめて入れており、中身は
    「照明：○○」「舞台監督：○○」のような行の並びになっている。
    **役職別に取得率を測る（V3）には、ここをばらさないと測れない。**
    """
    out = dict(fields)
    staff = fields.get("スタッフ", "")
    for line in staff.split("\n"):
        if m := re.match(r"\s*([^:：]{1,12})[:：]\s*(.+)", line):
            role, people = m.group(1).strip(), m.group(2).strip()
            if role and people:
                out[role] = (out.get(role, "") + "、" + people).strip("、")
    return out


def split_people(text: str) -> list[str]:
    parts = re.split(r"[、,／/\n・]+", text)
    out = []
    for p in parts:
        p = re.sub(r"[（(].*?[）)]", "", p).strip(" 　:：")
        if 2 <= len(p) <= 20 and not re.search(r"[0-9a-zA-Z]{6,}|http", p):
            out.append(p)
    return out


def run(limit: int) -> None:
    rows = [json.loads(l) for l in PERF.read_text(encoding="utf-8").split("\n") if l.strip()]
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "tickets"))
    import corrections as CX  # noqa
    from extract_performances import is_theater, norm_title  # noqa

    fixed = CX.search_titles()          # uid → 当事者が直した題名

    dated = [r for r in rows if r.get("date") and r.get("title") and is_theater(r["title"])]
    best: dict = {}
    for r in dated:
        k = (r["date"], r.get("time", ""))
        sc = len(r["title"]) + (30 if r.get("venue") else 0)
        if k not in best or sc > best[k][0]:
            best[k] = (sc, r)
    targets = sorted((v[1] for v in best.values()), key=lambda x: x["date"])
    if limit:
        targets = targets[-limit:]
    print(f"対象 {len(targets)} 公演。CoRich から取得します（1 リクエスト/秒）…", flush=True)

    results = []
    n_fixed = sum(1 for r in targets if fixed.get(str(r["uid"])))
    if n_fixed:
        print(f"  うち {n_fixed} 件は、当事者が直した題名で検索します", flush=True)
    for n, r in enumerate(targets, 1):
        # **直した題名を先頭に置く。** 飾りを落とす規則（clean_title）は抽出の失敗を
        # 直せない ── 切れた題名からは、切れた候補しか作れない
        fx = fixed.get(str(r["uid"]))
        words = ([fx] if fx else []) + [w for w in clean_title(fx or r["title"])]
        # **題名で照らし合わせてから採る**（`rank_candidate`）。当たらなければ結び付けない
        found = best_match(dict(r, title=fx or r["title"]), words, set())
        results.append({"date": r["date"], "mail_title": r["title"],
                        "fixed_title": fx or "",
                        "matched": bool(found), **(found or {})})
        print(f"  {n}/{len(targets)}  一致 {sum(1 for x in results if x['matched'])}",
              end="\r", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for x in results:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(f"\n{len(results)} 件を {OUT} に書き出しました。")
    report()


def report() -> None:
    rows = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    hit = [r for r in rows if r.get("matched")]
    print(f"\n■ V3 ── 公演ページが見つかった: {len(hit)}/{len(rows)} "
          f"（{len(hit) / max(len(rows), 1) * 100:.0f}%）")
    print("\n■ V3 ── 役職別の取得率（見つかった公演のうち、その役職が取れた割合）")
    for key in ROLE_KEYS:
        n = sum(1 for r in hit if r.get("fields", {}).get(key))
        if n:
            print(f"   {key:<8} {n:>4}/{len(hit)}  {n / len(hit) * 100:>3.0f}%")

    counts: collections.Counter = collections.Counter()
    by_role: dict = collections.defaultdict(collections.Counter)
    for r in hit:
        for key, text in (r.get("fields") or {}).items():
            if key not in ROLE_KEYS:
                continue
            for p in set(split_people(text)):
                counts[p] += 1
                by_role[key][p] += 1
    print(f"\n■ V21 ── 人物の延べ数 {sum(counts.values())} / ユニーク {len(counts)} 人")
    dist = collections.Counter(min(v, 6) for v in counts.values())
    for k in sorted(dist):
        label = f"n={k}" if k < 6 else "n≥6"
        print(f"   {label:<5} {dist[k]:>5} 人")
    for th in (2, 3, 5):
        m = sum(1 for v in counts.values() if v >= th)
        print(f"   n ≥ {th} の人物: {m} 人（{m / max(len(counts), 1) * 100:.0f}%）")
    print("\n■ V21 ── 役職別に見た n ≥ 2 の人数")
    for key in ROLE_KEYS:
        c = by_role.get(key)
        if not c:
            continue
        m = sum(1 for v in c.values() if v >= 2)
        print(f"   {key:<8} ユニーク {len(c):>4} 人 / n ≥ 2 は {m:>3} 人 "
              f"（{m / len(c) * 100:>3.0f}%）")
    print("\n※ 人名は表示しない（V24 を測れなくしないため）。名前は data/credits/ にのみ置く。")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.run:
        run(a.limit)
    elif a.report:
        report()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
