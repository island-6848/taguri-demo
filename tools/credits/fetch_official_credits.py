#!/usr/bin/env python3
"""公演の公式サイトから、裏方のクレジットを取れるか測る（V27）。

## なぜこれを測るのか

[検証 006](../../docs/verification/006-credits-and-name-density.md) で、CoRich からは
**出演 88%・演出 88%・脚本 82% が取れる一方、裏方（美術・照明・音響・衣裳・舞台監督）は
16〜20% しか取れない**ことが分かった。企画の中核は「気づいていなかった裏方の名前」なので、
**取得先を広げないと中核が成立しない。** CoRich の公演ページには公式サイトの URL が
入っている（実測で 130／130）ので、そこを辿って裏方が取れるかを測る。

## 辿る処理を含めて測る

[検証 002](../../docs/verification/002-first-seven-records.md) で、**カレンダーや一覧の
リンク先が公演の個別ページとは限らない**ことが分かっている（劇団4はトップページ、
劇団7は年間ラインナップの一覧）。**リンクを 1 段辿る処理まで含めて測らないと、
実運用の取得率にならない。**

## 測る値

- 到達できた URL の割合（**消えている公演サイトが何件あるか**）
- 裏方（美術・照明・音響・衣裳・舞台監督）が 1 つ以上取れた公演の割合 ← **V27 の判定**
- 役職別の取得率

**人名は表示しない。** V24 を測れなくしないため、集計値だけを出す。

    python3 tools/credits/fetch_official_credits.py --run
"""

from __future__ import annotations

import argparse
import atexit
import collections
import datetime
import gzip
import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "data" / "credits" / "credits.jsonl"
OUT = ROOT / "data" / "credits" / "official.jsonl"
CACHE = ROOT / "data" / "credits" / "official_pages"
UA = "Mozilla/5.0 (compatible; taguri-verify/1.0; personal use)"

BACKSTAGE = ["美術", "照明", "音響", "衣裳", "衣装", "舞台監督"]
ALL_ROLES = BACKSTAGE + ["演出", "脚本", "作", "出演", "音楽", "振付", "制作", "宣伝美術"]
# **出演の名簿が終わり、ページの次の節に移ったことを見分ける言葉。** 「出演」欄の
# 複数行を拾う探し方は、行にこの言葉を含んだところで打ち切る（実測で名前の直後に
# 続いていた見出し。「開演日時」のように他の語とくっついた形でも出るので、
# 完全一致ではなく部分一致で見る）
CAST_STOP = ("日時", "会場", "公演日", "スタッフ", "問い合わせ", "スケジュール",
             "チケット", "料金", "配信", "主催", "後援", "協賛", "上演時間",
             "開場", "開演", "公式サイト", "プロフィール", "Show more", "詳細",
             "グッズ", "予約", "日程", "コメント", "記事")

# 個別ページへ辿るときに手がかりにする語
FOLLOW_WORDS = ("スタッフ", "STAFF", "Staff", "キャスト", "CAST", "Cast",
                "公演情報", "作品情報", "公演詳細", "上演", "詳細")

# **間隔はホストごとに空ける。** 以前は全体で 1 件 1.1 秒にしていたが、**辿る先は
# 相手のサイトであって 1 つのサーバーではない。** カレンダーの 470 件は 313 ホストに
# 散っており（1 ホストあたり平均 1.5 件）、**全体で 1 秒に 1 件に絞ると、無関係な相手を
# 待つために 313 倍きつい制限を自分に掛けている**ことになる。
#
# **礼儀の単位は相手のサーバーである。** 1 つの相手には 1.1 秒に 1 回までを守り、
# 別の相手へは同時に行く。x.com のように 1 ホストに 74 件が集まっている先は、
# ここで自然に直列になる（それが正しい）。
INTERVAL = 1.1
# **到達を諦めるまでの秒数。** 25 秒から縮めた（起案者の指摘・2026-08-24 ──
# 「ステイジーズカレンダーの取り込みに時間がかかっている。短縮して」）。**返事の無い
# 相手 1 件が、そのまま 1 本の並列枠を 25 秒占める。** 実測で、到達できた先の中央値は
# 1 秒ほどなので、8 秒待って返らない先から取れる見込みは薄い。**諦めたことは控える**
# ので、次の実行で取り直しにはならない
TIMEOUT = 8
# **到達できなかった先を控えておく日数。** 控えていなかったため、**毎月の実行が
# 毎回すべての失敗を取り直していた**（470 件のうち 305 件が控えに無く、その多くは
# 前の月にも落ちた先である）。次の更新（月 1 回）までは再挑戦しない
FAIL_DAYS = 30
FAILS = ROOT / "data" / "credits" / "official_fail.json"
_last: dict[str, float] = {}
_lock = threading.Lock()
_fails: dict[str, str] | None = None
_fail_dirty = False
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _wait_turn(url: str) -> None:
    """このホストの順番が来るまで待つ。**待っている間、他のホストは止めない。**"""
    h = _host(url)
    while True:
        with _lock:
            now = time.monotonic()
            due = _last.get(h, 0.0) + INTERVAL
            if now >= due:
                _last[h] = now            # 枠を取ってから抜ける（同じホストで二重取りしない）
                return
        time.sleep(min(due - now, INTERVAL))


def _load_fails() -> dict:
    """到達できなかった先の控え。**無ければ空**（初めての実行では何も飛ばさない）。"""
    global _fails
    if _fails is None:
        try:
            _fails = json.loads(FAILS.read_text(encoding="utf-8"))
        except Exception:                                           # noqa: BLE001
            _fails = {}
    return _fails


def save_fails() -> int:
    """控えを書き出す。**終わりに 1 回だけ書く**（1 件ごとに書かない）。

    **`atexit` で自分から呼ぶ。** この道具は 4 つの実行から使われるので、
    **呼ぶ側に書き出しを覚えさせると、忘れた側だけ毎回取り直しに戻る。**
    """
    global _fail_dirty
    if not _fail_dirty or _fails is None:
        return 0
    FAILS.parent.mkdir(parents=True, exist_ok=True)
    # **書きかけを控えとして読ませない**（並行して走る実行がある）
    tmp = FAILS.with_suffix(f".{os.getpid()}.part")
    tmp.write_text(json.dumps(_fails, ensure_ascii=False, indent=0), encoding="utf-8")
    tmp.replace(FAILS)
    _fail_dirty = False
    return len(_fails)


atexit.register(save_fails)


def _skip_failed(url: str) -> str:
    """前に落ちた先なら、その理由を返す（まだ日が浅いあいだだけ）。"""
    ent = _load_fails().get(url)
    if not ent:
        return ""
    try:
        at = datetime.date.fromisoformat(str(ent).split("|", 1)[0])
    except ValueError:
        return ""
    if (datetime.date.today() - at).days >= FAIL_DAYS:
        return ""
    return str(ent).split("|", 1)[-1] or "前に到達できなかった先"


def get(url: str, *, retry_failed: bool = False) -> tuple[str, str]:
    """(html, error) を返す。**落ちても止めない。到達できなかったことも測定値である。**

    **控えにあれば待たない。** 以前は呼ぶ側が 1 件ごとに眠っていたため、**通信が 1 回も
    起きない実行でも件数ぶんの時間がかかっていた**（470 件で 7.8 分）。
    """
    key = CACHE / (re.sub(r"[^A-Za-z0-9]", "_", url)[-120:] + ".html")
    if key.exists():
        return key.read_text(encoding="utf-8"), ""
    if not retry_failed:
        why = _skip_failed(url)
        if why:
            return "", f"前に落ちた先なので飛ばした（{why}）"
    _wait_turn(url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ctx) as r:
            raw = r.read(3_000_000)
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            enc = "utf-8"
            m = re.search(rb'charset=["\']?([\w-]+)', raw[:3000], re.I)
            if m:
                enc = m.group(1).decode("ascii", "replace")
            html = raw.decode(enc, "replace")
    except Exception as exc:
        # **落ちたことを控える。** 控えないと、毎月の実行が毎回すべての失敗を
        # 取り直す（1 件あたり最大 TIMEOUT 秒）
        global _fail_dirty
        why = f"{type(exc).__name__}: {str(exc)[:60]}"
        with _lock:
            _load_fails()[url] = f"{datetime.date.today().isoformat()}|{why}"
            _fail_dirty = True
        return "", why
    CACHE.mkdir(parents=True, exist_ok=True)
    # **書き込みは不可分にする。** 並行して走るので、途中まで書かれたファイルを別の
    # 実行が控えとして読むと、黙って中身の欠けたページを使うことになる
    tmp = key.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(key)
    return html, ""


def to_text(html: str) -> str:
    import html as _html
    t = re.sub(r"<(script|style|noscript).*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|dd|dt|tr|td|th|h\d)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    # **`&nbsp;` だけでなく、名前付き実体参照は全部戻す。** `&ensp;` などが素の
    # 文字のまま残ると、役職の次の行を拾う処理がそれを「名前」と誤って拾う（実測）
    t = _html.unescape(t).replace("\xa0", " ")
    t = re.sub(r"[ \t　]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    # **役職・コロン・名前が改行で分かれている**サイトがある（松竹など）。
    #   演出 \n ： \n 滝○○○
    # 1 行に戻さないと「役職：名前」として拾えない。実測でこれが最大の取りこぼしだった。
    t = re.sub(r"\n\s*[:：＝=＿_]\s*\n?", "：", t)
    return t


def roles_in(text: str) -> dict:
    """「役職：名前」の形を拾う。**役職と名前が対で取れたものだけ数える。**

    名前だけが並んでいても、誰が何をしたか分からなければ名簿に使えない。
    """
    found: dict = {}
    # **【役職】名前 という記法がある。** 劇場3がこれで、コロンを使わない。
    # 「リンク先が個別ページでないから取れない」と読みかけたが、実際には個別ページに
    # クレジットが載っており、**こちらが記法を 1 つ取りこぼしていただけ**だった。
    for m in re.finditer(r"[【［\[《〈]\s*([^】］\]》〉]{1,12})\s*[】］\]》〉]\s*([^【［\[《〈\n]{2,60})",
                         text):
        role = m.group(1).strip().replace("デザイン", "").replace("プラン", "").strip()
        people = m.group(2).strip(" 　・、,")
        if not people:
            continue
        for key in ALL_ROLES:
            if role == key or role.startswith(key):
                found.setdefault(key, people)
                break
    for line in text.split("\n"):
        line = line.strip()
        if not (3 <= len(line) <= 120):
            continue
        m = re.match(r"([^:：\s]{1,12})\s*[:：]\s*(.+)", line)
        if not m:
            continue
        role, people = m.group(1).strip(), m.group(2).strip()
        role = re.sub(r"^[■●◆・\-\s]+", "", role)
        base = role.replace("デザイン", "").replace("プラン", "").strip()
        for key in ALL_ROLES:
            if base == key or base.startswith(key):
                if 2 <= len(people) <= 80:
                    found.setdefault(key, people)
                break
    # **役職と名前を空白で区切って 1 行に置く記法**もある（東宝など）。
    #   美術 田○○○
    #   照明 加○○○
    # 記法はこれで 3 つ目（役職：名前／【役職】名前／役職 名前）。
    # **抽出できない原因を情報源に帰属する前に、記法を数え上げる。**
    for line in text.split("\n"):
        line = line.strip(" 　■●◆・-")
        m = re.match(r"([一-龥ァ-ヶА-Яa-zA-Z]{2,8})[ 　＝=＿_]+([^ 　:：].{1,58})$", line)
        if not m:
            continue
        role = m.group(1).replace("デザイン", "").replace("プラン", "").strip()
        people = m.group(2).strip()
        if role in ALL_ROLES and not re.search(r"[:：]|http|\d{4}年", people):
            found.setdefault(role, people)

    # コロンを使わず、役職の**次の行**に名前を置く書式もある。
    # 役職名だけの行を見つけたら、直後の行を名前とみなす。
    #
    # **出演だけは 1 人とは限らないので、複数行を拾う。** 名前が 1 行に 1 人ずつ、
    # 何行も続く書式がある（実測 ── コンプソンズ公式サイトは「出演」の下に 9 名が
    # 1 行 1 名で続き、途中に空行を 1 つ挟む。次の 1 行しか見ていなかったので
    # 9 名中 1 名しか拾えていなかった）。**空行 1 つまでは同じ欄が続くとみなし、
    # 2 つ続いたら欄が終わったとみなす。** 役職名の行・コロンを含む行・URL・年号に
    # 当たったら、そこで打ち切る。**ほかの役職（演出・音楽など）は 1 人がほとんど**
    # なので、複数行を拾う欲張りな探し方に変えると、次に来る別の役職（実測で
    # 「殺陣指導」「ヘアメイク」など `ALL_ROLES` に無い役職名）まで同じ欄として
    # 拾い込んでしまう。出演だけに絞る。
    lines = [x.strip() for x in text.split("\n")]
    for i, line in enumerate(lines):
        base = line.replace("デザイン", "").replace("プラン", "").strip("■●◆・- 　")
        if base not in ALL_ROLES or base in found:
            continue
        if base == "出演":
            names: list[str] = []
            blanks = 0
            for nxt in lines[i + 1:i + 30]:
                nxt = nxt.strip()
                if not nxt:
                    blanks += 1
                    if blanks >= 2:
                        break
                    continue
                blanks = 0
                if re.search(r"[:：@]|https?://|\d{4}年", nxt):
                    break
                cand = nxt.strip("■●◆・- 　○⚪︎")
                if (cand in ALL_ROLES or any(w in nxt for w in CAST_STOP)
                        or not (2 <= len(nxt) <= 60)):
                    break
                names.append(nxt)
            if names:
                found.setdefault(base, "、".join(names))
            continue
        for j in range(i + 1, min(i + 3, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            if 2 <= len(nxt) <= 60 and not re.search(r"[:：]|http|\d{4}", nxt) \
                    and nxt.strip("■●◆・- 　") not in ALL_ROLES:
                found.setdefault(base, nxt)
            break
    return found


def links(html: str, base: str) -> list[str]:
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"#]+)"[^>]*>(.{0,80}?)</a>', html, re.S | re.I):
        href, label = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        if any(w in label for w in FOLLOW_WORDS) or any(w in href for w in
                                                        ("staff", "cast", "stage", "info")):
            u = urllib.parse.urljoin(base, href)
            if u.startswith("http") and u != base and u not in out:
                out.append(u)
    return out[:2]


def run(limit: int) -> None:
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").split("\n") if l.strip()]
    hit = [r for r in rows if r.get("matched")]
    targets = []
    for r in hit:
        f = r.get("fields") or {}
        if any(f.get(k) for k in BACKSTAGE):
            continue          # CoRich で既に裏方が取れている公演は対象外
        m = re.search(r'https?://[^\s"<>）)]+', f.get("公式／劇場サイト", ""))
        if m:
            targets.append((r, m.group(0).rstrip("。、")))
    if limit:
        targets = targets[:limit]
    print(f"裏方が取れていない {len(targets)} 公演について、公式サイトを辿ります…", flush=True)

    results = []
    for n, (r, url) in enumerate(targets, 1):
        html, err = get(url)
        got, depth = ({}, 0)
        if html:
            got = roles_in(to_text(html))
            if not any(k in got for k in BACKSTAGE):
                for u2 in links(html, url):
                    h2, _ = get(u2)
                    if not h2:
                        continue
                    g2 = roles_in(to_text(h2))
                    if any(k in g2 for k in BACKSTAGE):
                        got, depth = g2, 1
                        break
        results.append({"date": r["date"], "title": r["mail_title"][:60], "url": url,
                        "error": err, "depth": depth, "roles": got})
        print(f"  {n}/{len(targets)}", end="\r", flush=True)

    OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in results),
                   encoding="utf-8")
    report(results)


def report(results=None) -> None:
    if results is None:
        results = [json.loads(l) for l in OUT.read_text(encoding="utf-8").split("\n") if l.strip()]
    n = len(results)
    dead = [r for r in results if r["error"]]
    back = [r for r in results if any(k in r["roles"] for k in BACKSTAGE)]
    any_role = [r for r in results if r["roles"]]
    print(f"\n■ 対象 {n} 公演（CoRich で裏方が取れなかったもの）")
    print(f"   到達できなかった URL      {len(dead):>4} 件（{len(dead)/n*100:.0f}%）")
    print(f"   何らかの役職が取れた       {len(any_role):>4} 件（{len(any_role)/n*100:.0f}%）")
    print(f"   **裏方が 1 つ以上取れた**  {len(back):>4} 件（{len(back)/n*100:.0f}%） ← V27 の判定")
    print(f"   うちリンクを 1 段辿って取れた {sum(1 for r in back if r['depth']):>3} 件")
    print("\n■ 役職別（対象 {} 公演に対する割合）".format(n))
    for k in ALL_ROLES:
        c = sum(1 for r in results if k in r["roles"])
        if c:
            print(f"   {k:<8} {c:>4} 件  {c/n*100:>3.0f}%")
    print("\n■ 到達できなかった理由")
    for e, c in collections.Counter(r["error"].split(":")[0] for r in dead).most_common():
        print(f"   {c:>4}  {e}")
    print("\n※ 人名は表示しない（V24 を測れなくしないため）")


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
