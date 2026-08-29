#!/usr/bin/env python3
"""「全部の公演を自分で確かめる」のに何時間かかるかを実測から見積もる。

企画書に書く削減時間を推測で出さないため、ステイジーズカレンダーの
公演ページを標本抽出して本文量を測り、読字速度から所要時間を出す。

  python3 tools/stages/estimate_search_time.py [標本数]
"""
import csv
import io
import re
import sys
import time
import urllib.error
import urllib.request

SHEET = "1OtXzChuCUfy2AnyuRW5ZgnMbsKHUwlCEF9keTA0Gb8c"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid=0"
UA = "Mozilla/5.0 (compatible; taguri-research/1.0)"

# 日本語の黙読速度。一般に 400〜600 字/分とされるので中央の 500 を採る
CPM = 500
# ページを開く・戻る・判断する操作の分（1 件あたり秒）
OVERHEAD_SEC = 20


def text_len(html):
    """スクリプト・スタイルを除いた可視テキストの文字数。"""
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;|&#\d+;", " ", text)
    return len(re.sub(r"\s+", "", text))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    with urllib.request.urlopen(URL, timeout=60) as r:
        rows = list(csv.reader(io.StringIO(r.read().decode("utf-8"))))
    hdr = rows[1]
    li, ti = hdr.index("リンク"), hdr.index("公演タイトル")
    data = [r for r in rows[2:]
            if r and r[0].strip().isdigit() and r[li].strip().startswith("http")]
    total = len(data)
    step = max(1, total // n)          # 等間隔で抜く（先頭に偏らせない）
    sample = data[::step][:n]

    lens = []
    for r in sample:
        url = r[li].strip()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read(600_000).decode(resp.headers.get_content_charset()
                                                 or "utf-8", "ignore")
            c = text_len(body)
            lens.append(c)
            print(f"  {c:>6,} 字  {r[ti][:28]}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"  ------ 取得できず  {r[ti][:28]}（{type(e).__name__}）")
        time.sleep(1.0)                # 1 リクエスト／秒以下

    if not lens:
        print("標本が取れなかった")
        return
    lens.sort()
    med = lens[len(lens) // 2]
    print(f"\n標本 {len(lens)} 件 / 母集団 {total:,} 件")
    print(f"1 ページの文字数  中央値 {med:,} 字（最小 {min(lens):,} / 最大 {max(lens):,}）")

    read_min = med / CPM
    per_item = read_min + OVERHEAD_SEC / 60
    print(f"1 件あたり  読む {read_min:.1f} 分 ＋ 操作 {OVERHEAD_SEC/60:.1f} 分"
          f" = {per_item:.1f} 分")
    hours = total * per_item / 60
    print(f"\n全 {total:,} 件を自分で確かめると  {hours:.0f} 時間"
          f"（1 日 8 時間なら {hours/8:.1f} 日ぶん）")
    print(f"  週あたり（新規 55 件）        {55 * per_item / 60:.1f} 時間")
    sys_h = (30 + 3 * 18) / 60
    print(f"たぐりを使うと  導入 30 分 ＋ 週 3 分 × 18 週 = {sys_h:.1f} 時間")
    print(f"  削減  {hours - sys_h:.0f} 時間（{(1 - sys_h / hours) * 100:.0f}%）")


if __name__ == "__main__":
    main()
