"""people.panel(rated, owner=False) on hand-made rated rows: the reference for
src/screens/people.js (test/people.test.js).

    python3 test/screens/people_fixture.py

**同点の並びを作らない。** `people.timeline` は段で加わった人を
`sorted(set(...), key=-作品数)` で並べるので、作品数が同じ人が同じ段で加わると、
その順は Python の文字列ハッシュ（起動ごとに乱数）で決まる ── Python 自身の出力が
起動ごとに変わる。そこで下の記録は「1 本で網に加わる人は 1 人まで」（最初の線だけは
作品数の違う 2 人）になるように組み、`--check-seeds` で別のハッシュの種でも同じ出力に
なることを確かめる（JS 側は同点を名前の順で並べる）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CAST, DIR, PLAY, AUTH, TR, MUS, LIGHT = "出演", "演出", "脚本", "作", "翻訳", "音楽", "照明"


def row(key, title, date, people, venues=()):
    return {"key": key, "title": title, "date": date, "verdict": "◎",
            "people": sorted({tuple(p) for p in people}), "venues": list(venues)}


class Book:
    """記録を順に積む。`once` は 1 回だけ出る人（網に入らない）を毎回新しく作る。"""

    def __init__(self):
        self.rows, self.n, self.once = [], 0, 0

    def add(self, date, people, title=None, venues=("劇場A",)):
        self.n += 1
        self.once += 1
        title = title or f"公演{self.n:03d}"
        people = list(people) + [(CAST, f"一度きり{self.once}"), (LIGHT, f"照明係{self.once % 3}")]
        self.rows.append(row(f"{title}#{date}", title, date, people, venues))


def bunch(book, names, roles, year, month0, extra=()):
    """1 つの束を育てる。1 本ごとに網へ加わるのは 1 人だけ（最初の 2 人は作品数が違う）。"""
    m = names
    rl = lambda i: (roles[i % len(roles)], m[i])                      # noqa: E731
    d = lambda j: f"{year}-{month0 + j // 4:02d}-{1 + (j % 4) * 7:02d}"  # noqa: E731
    book.add(d(0), [rl(0)])
    book.add(d(1), [rl(0), rl(1)])
    book.add(d(2), [rl(0), rl(1), rl(2)])
    for j in range(3, len(m)):
        core = [rl(i) for i in range(j - 1) if (i * 7 + j) % 3 == 0 or i == j - 2]
        book.add(d(j), core + [rl(j - 1), rl(j)] + list(extra))
    # 最後の人も網に入れる（それまでの誰か 2 人と）
    book.add(d(len(m)), [rl(len(m) - 1), rl(0), rl(len(m) // 2)])


def main_case():
    b = Book()
    A = ["山田 太郎", "佐藤花子", "鈴木一郎", "高橋 &lt;健&gt;", "田中みどり", "伊藤ゆう", "渡辺精一",
         "中村 Ken", "小林あや", "加藤 <B>", "吉田＝", "山本１２３", "Anna O'Neil", "松本　清",
         "井上ひかる", "木村拓"]
    B = ["ｶﾀｶﾅ太郎", "森 \"守\"", "池田恵", "橋本 J", "山崎ゆり", "石川遼", "前田敦", "藤田まこと",
         "後藤久美", "岡田准", "長谷川♪", "村上春"]
    C = ["近藤勇", "坂本龍", "遠藤周", "青木", "藤井聡", "西村京", "福田", "太田光", "三浦按針",
         "𠮷野家"]
    bunch(b, A, [CAST, CAST, DIR, CAST, PLAY, CAST, MUS], 2019, 1)
    bunch(b, B, [CAST, AUTH, CAST, CAST, TR], 2020, 1)
    bunch(b, C, [CAST, CAST, CAST, DIR], 2021, 1)
    # 同じ顔ぶれをもう一度（つながりは変わらない）
    b.add("2021-06-01", [(CAST, A[0]), (CAST, A[1])], title="再演 & <再び>")
    # 出演者が取れていない公演
    b.rows.append(row("取れない#2021-06-02", "取れない", "2021-06-02", [(LIGHT, "照明係1")]))
    b.rows.append(row("空#2021-06-03", "空", "2021-06-03", []))
    # 2 作品以上だが誰とも一緒になっていない 2 名（日付順で、ほかの人と同時に加わらない）
    b.add("2021-07-01", [(CAST, "ひとり甲")])
    b.add("2021-07-02", [(CAST, "ひとり甲")])
    b.add("2021-07-03", [(DIR, "ひとり乙")])
    b.add("2021-07-04", [(DIR, "ひとり乙")])
    # 束 A と B を 1 人でつなぐ（関節点）→ 合流
    b.add("2022-01-10", [(CAST, A[3]), (CAST, B[2])], title="橋の公演")
    # 束 B と C を 1 人でつなぐ → 合流
    b.add("2022-02-10", [(CAST, B[5]), (CAST, C[4])], title="もう一つの橋")
    # B と C を別の人でもつなぐ（B[5] は外しても分かれなくなる）
    b.add("2022-03-10", [(CAST, B[7]), (DIR, C[1])], title="二本目の道")
    # 端に 1 人だけぶら下がる人（つないでいる人が関節点になる）
    b.add("2022-04-01", [(CAST, C[6]), (CAST, "端っこ")])
    b.add("2022-04-08", [(CAST, C[6]), (CAST, "端っこ")])
    # 上演日の分からない記録（最後の段に入る ── 加わるのは 1 人だけ）
    b.rows.append(row("日付なし一#", "日付なし一", "", [(CAST, A[5]), (CAST, "日付なし役者")]))
    b.rows.append(row("日付なし二#", "日付なし二", "", [(CAST, A[6]), (CAST, "日付なし役者")]))
    return b.rows


def tiny_case():
    b = Book()
    b.add("2023-01-01", [(CAST, "甲")])
    b.add("2023-02-01", [(CAST, "甲"), (DIR, "乙")])
    b.add("2023-03-01", [(CAST, "甲"), (DIR, "乙"), (CAST, "丙")])
    b.add("2023-04-01", [(DIR, "乙"), (CAST, "丙")])
    return b.rows


def split_case():
    """2 つの三角（関節点なし・2 つのグループ）。"""
    b = Book()
    for y, (p, q, r) in ((2018, ("あ", "い", "う")), (2019, ("か", "き", "く"))):
        b.add(f"{y}-01-01", [(CAST, p)])
        b.add(f"{y}-02-01", [(CAST, p), (CAST, q)])
        b.add(f"{y}-03-01", [(CAST, p), (CAST, q), (CAST, r)])
        b.add(f"{y}-04-01", [(CAST, q), (CAST, r)])
    return b.rows


def undated_case():
    """上演日が 1 件も無い（時間のつまみを出さない）。"""
    rows = tiny_case()
    for r in rows:
        r["date"] = ""
    return rows


def too_small_case():
    b = Book()
    b.add("2023-01-01", [(CAST, "甲"), (CAST, "乙")])
    b.add("2023-02-01", [(CAST, "甲"), (CAST, "乙")])
    return b.rows


TEXT_W = ["", "abc", "Anna O'Neil", "カタカナ", "ｶﾀｶﾅ", "漢字", "１２３", "123", "𠮷野家", "♪・ー",
          "가나", "😀x", "　", "〜～"]


def wf_ranges():
    """east_asian_width が W か F の範囲（JS の表と同じであることを確かめる）。"""
    import unicodedata
    out, start = [], None
    for cp in range(0x110000 + 1):
        on = cp < 0x110000 and unicodedata.east_asian_width(chr(cp)) in "WF"
        if on and start is None:
            start = cp
        elif not on and start is not None:
            out.append([start, cp - 1])
            start = None
    return out


def trig(limit=512):
    """math.sin / math.cos of math.tau * i / n for n < limit (little-endian doubles, base64)."""
    import base64
    import math
    import struct
    b = bytearray()
    for n in range(1, limit):
        for i in range(n):
            a = math.tau * i / n
            b += struct.pack("<dd", math.sin(a), math.cos(a))
    return base64.b64encode(bytes(b)).decode()


def build():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import unicodedata
    import people as PE
    cases = []
    for name, rated in (("main", main_case()), ("tiny", tiny_case()), ("split", split_case()),
                        ("undated", undated_case()), ("too_small", too_small_case()), ("empty", [])):
        cases.append({"name": name, "rated": rated, "html": PE.panel(rated, owner=False)})
    return {"cases": cases, "text_w": [[s, PE._text_w(s)] for s in TEXT_W],
            "unidata": unicodedata.unidata_version, "wf": wf_ranges(), "trig": trig()}


def main():
    if "--one" in sys.argv:
        print(json.dumps(build(), ensure_ascii=False))
        return
    outs = []
    for seed in ("0", "1", "12345"):
        outs.append(subprocess.run([sys.executable, __file__, "--one"], check=True, text=True,
                                   capture_output=True, env={**os.environ, "PYTHONHASHSEED": seed}).stdout)
    if len(set(outs)) != 1:
        sys.exit("people.panel の出力がハッシュの種で変わる（同点の並びがある）")
    sys.stdout.write(outs[0])


if __name__ == "__main__":
    main()
