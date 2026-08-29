#!/usr/bin/env python3
"""ステイジーズカレンダーから「1 つの公演が何日間で終わるのか」を実測する。

企画書の「クチコミを待つと間に合わない」を、推測ではなく実測で言うための数字。
クチコミが付くのは初日以降なので、上演日数が短いほど、待った時点で手遅れになる。
出典: ネビュラエンタープライズ「ステイジーズカレンダー」
      https://note.com/nevula_prise/n/n7434cc371ef0
公開の Google スプレッドシートを CSV でエクスポートして数えるだけ。
商用利用は不可（本システムは利用者 1 名の個人利用なので範囲内）。

  python3 tools/stages/run_length.py
"""
import collections
import csv
import datetime
import io
import statistics
import urllib.request

SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"

# 図に出す区切り。初日にクチコミが付いてから動けるかどうかで切っている。
BUCKETS = [(1, 1, "1 日だけ"), (2, 3, "2〜3 日"), (4, 7, "4〜7 日"), (8, None, "8 日以上")]


def parse_date(s):
    for f in ("%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    return None


def main():
    with urllib.request.urlopen(URL, timeout=60) as r:
        rows = list(csv.reader(io.StringIO(r.read().decode("utf-8"))))

    hdr = rows[1]  # 1 行目は更新日のみ
    col = {n: hdr.index(n) for n in ("公演団体名", "初日", "楽日")}
    data = [r for r in rows[2:] if r and r[0].strip().isdigit()]

    days = []
    for r in data:
        first, last = parse_date(r[col["初日"]]), parse_date(r[col["楽日"]])
        if first and last and last >= first:
            days.append((last - first).days + 1)  # 初日と楽日の両方を数える

    n = len(days)
    print(f"上演日数が取れた公演: {n} 件 / 掲載 {len(data)} 件")
    print(f"中央値 {statistics.median(days):.0f} 日、平均 {statistics.mean(days):.1f} 日")
    print()
    for lo, hi, label in BUCKETS:
        c = sum(1 for d in days if d >= lo and (hi is None or d <= hi))
        print(f"  {label:8} {c:5} 件  {c / n:4.0%}  {'█' * round(c / n * 60)}")
    print()
    for hi in (3, 7, 14):
        c = sum(1 for d in days if d <= hi)
        print(f"  {hi:2} 日以内に終わる: {c} 件（{c / n:.0%}）")

    # 1 団体が期間内に打つ公演の数。人手で追える団体数から、目に入る件数を出すのに使う。
    teams = collections.Counter(
        r[col["公演団体名"]].strip() for r in data if r[col["公演団体名"]].strip())
    print()
    print(f"公演団体: {len(teams)} 団体、1 団体あたり "
          f"中央値 {statistics.median(teams.values()):.0f} 件・"
          f"平均 {statistics.mean(teams.values()):.2f} 件")


if __name__ == "__main__":
    main()
