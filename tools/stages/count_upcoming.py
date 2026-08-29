#!/usr/bin/env python3
"""ステイジーズカレンダーから「これから開催される公演」の母数を実測する。

企画書に「公演が膨大にある」と書くための数字を、推測ではなく実測で出す。
出典: ネビュラエンタープライズ「ステイジーズカレンダー」
      https://note.com/nevula_prise/n/n7434cc371ef0
公開の Google スプレッドシートを CSV でエクスポートして数えるだけ。
商用利用は不可（本システムは利用者 1 名の個人利用なので範囲内）。

  python3 tools/stages/count_upcoming.py
"""
import collections
import csv
import datetime
import io
import urllib.request

SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"
CAPITAL = ("東京", "神奈川", "埼玉", "千葉")


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
    col = {n: hdr.index(n) for n in
           ("都道府県", "劇場名", "公演団体名", "初日", "楽日", "リンク")}
    data = [r for r in rows[2:] if r and r[0].strip().isdigit()]

    # 収録期間は日付列の見出し（7/31 … 12/4）から取る
    days = [d for d in (parse_date(f"2026/{c}") for c in hdr[13:]) if d]
    lo, hi = min(days), max(days)
    weeks = (hi - lo).days / 7

    opens = [d for d in (parse_date(r[col["初日"]]) for r in data)
             if d and lo <= d <= hi]
    per_week = collections.Counter(d.isocalendar()[:2] for d in opens)
    counts = sorted(per_week.values())
    pref = collections.Counter(r[col["都道府県"]].strip() for r in data)
    cap = sum(v for k, v in pref.items() if k in CAPITAL)

    print(f"収録期間        {lo} 〜 {hi}（約 {weeks:.0f} 週）")
    print(f"掲載公演        {len(data):,} 件")
    # 団体名・劇場名が空欄の行が 2 件ある（URL だけの行）。空欄を 1 種類として
    # 数えると 1 多く出るため、除いて数える。
    teams = {r[col["公演団体名"]].strip() for r in data} - {""}
    halls = {r[col["劇場名"]].strip() for r in data} - {""}
    print(f"公演団体        {len(teams):,} 団体")
    print(f"劇場            {len(halls):,} 会場")
    print(f"首都圏 1 都 3 県 {cap:,} 件（{cap / len(data) * 100:.0f}%）")
    print(f"期間内に初日     {len(opens):,} 件"
          f" → 週あたり {len(opens) / weeks:.0f} 件が新たに始まる")
    print(f"  週別の中央値   {counts[len(counts) // 2]} 件"
          f"（最小 {min(counts)} / 最大 {max(counts)}）")
    print(f"公式サイトのリンクあり {sum(1 for r in data if r[col['リンク']].strip().startswith('http')):,} 件"
          f" → あらすじ・クレジットの取得元を確保できる")


if __name__ == "__main__":
    main()
