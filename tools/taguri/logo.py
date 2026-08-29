#!/usr/bin/env python3
"""「たぐり」の標章。**自前の inline SVG で、外部から 1 枚も読み込まない**（`icons.py` と同じ約束）。

## 何を描いてあるか

**縦に並んだ 4 本の糸の束と、その左端から抜け出た 1 本。抜けた糸の先に玉が付いている。**

束が「これから観られる公演」で、引き出された 1 本が「たぐり寄せた次の 1 本」、
玉がその行き着いた先である。**名称の由来をそのまま形にした** ── 企画書「名称について」に
「糸をたぐるように、自分の記録から手がかりを引き寄せて次の 1 本にたどり着く」と書いてある。

**「1 本」は公演の数え方でもあり、糸の数え方でもある。** 出す答えが 1 本だけである
（企画書 1 章「システムが出す答えは 1 つである」）ことが、引き出した糸が 1 本であることで
出ている。束のほうを何本にするかは意味を持たないので、20px で潰れない上限に置いた。

## なぜこの形にしたか（捨てた案）

渦・コイル・波の 3 方向を先に描いて捨てた。**渦は読み込み中の印に見え、コイルは `w` や
`www` の字に見え、波は玉が線に溶けて端が読めない。** どれも「たぐる」より先に別のものに
見えてしまい、20px では区別が付かなかった。

縦の束を採ったのは 2 つの理由である。**① 20px でも「何本かの束」と「離れた 1 本」の区別が
残る**（縦線は互いに平行なので、太さと間隔だけで数が読める）。**② この画面がすでに持って
いる幕の襞（`.curtain` の縦縞）と同じ向きである** ── 新しい意匠を持ち込まずに済む。

## 色を持たせない

線と玉は `currentColor` を継ぐので、標章は置いた場所の文字と同じ色になる ── 幕の帯では
生成りの `--curtain-w`、白地では `--ink` である。**標章に固有の色を与えていない。**
意匠を 2 本のインクに割った時点で、**藍（`--acc`）は「押せる」、えんじ（`--curtain`）は
「識別」**という役が付いた ── 標章をどちらかで描くと、その意味を背負ってしまう。
色で意味を運ばないという `icons.py` の方針も、そのまま当てはまる。

**ファビコンだけは色を持つ**（`FAVICON_COLOR`）。タブの地色はページの明暗に従わないので
`currentColor` が使えない。**明暗の切り替えは SVG の中の `prefers-color-scheme` で行う** ──
タブは `data-theme` を知らないので、媒体問い合わせしか手が無い。**暗いタブでえんじが
地に沈むため、暗い側は意匠の暗い側と同じ明るいえんじに替える。** 対応していない
ブラウザでは明るい側の値になる（読めない色ではなく、沈むだけである）。

**ファビコンは形も簡略にする。** 16px で描かれると 4 本の束は 1 つの塊に潰れるので、
2 本＋引き出した 1 本まで減らし、線を太くした（`FAVICON_SVG`）。
"""

from __future__ import annotations

from urllib.parse import quote

# 24×24。**引き出した 1 本は、束の左端と同じ位置から始めて外へ抜ける。**
# 離れた場所から始めると、束から出てきた 1 本ではなく、隣にある別の糸に見える。
# 引き出した糸を太くしてあるのは、束と主役を太さで分けるためである（色は使えない）。
STRANDS = (11.0, 14.5, 18.0, 21.5)
PULL = "M11 4.5C10.4 12 8.6 16 4.4 17.6"      # 束の上端から左下へ抜ける 1 本
BEAD = (4.4, 17.6, 2.15)                       # 引き出した先の玉（cx, cy, r）


def mark(size: int = 23, cls: str = "") -> str:
    """標章の絵だけ。**読み上げからは外す** ── 隣に「たぐり」の文字が必ず並ぶ。"""
    st = "".join(f'<path d="M{x} 4.5V19.5" stroke-width="1.6"/>' for x in STRANDS)
    cx, cy, r = BEAD
    return (f'<svg class="tgm {cls}" viewBox="0 0 24 24" width="{size}" height="{size}"'
            f' fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true">'
            f'{st}<path d="{PULL}" stroke-width="2.45"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="currentColor" stroke="none"/></svg>')


def lockup(cls: str = "") -> str:
    """絵と文字の組。**文字は画像にしない** ── 選択もコピーも読み上げもできる文である。

    **大きさは 1 つしか持たない。** 標章が出る場所は帯の頭 1 か所だけなので、
    大小を作る必要が無い ── はじめる画面の見出しの上にも大きく置いてみたが、
    **帯の標章とほぼ同じ高さに 2 つ並ぶ**ので取り消した。
    """
    return (f'<span class="tglock{" " + cls if cls else ""}">'
            f'{mark()}<span class="tgw">たぐり</span></span>')


CSS = """
/* ---- 標章 -----------------------------------------------------------------
   **字の大きさ・太さ・色は帯の側（`.side .brand`）が決める。** ここで持つのは組み方
   （絵と文字を横に並べて中心を揃える）だけである ── 意匠の色を変えるときに、
   標章の側を直さなくて済む。                                                  */
.tglock{display:inline-flex;align-items:center;gap:9px;line-height:1;white-space:nowrap}
.tglock .tgm{flex:none}
.tglock .tgw{letter-spacing:.1em}
"""

# ------------------------------------------------------------------ ファビコン
#
# **16px 用の簡略形。** 束を 2 本に減らし、線と玉を太くしてある。
# 色は固定する（タブの地色はページの明暗と一致しないので `currentColor` が使えない）。
# **タブの中の色は識別の色にする。** 以前は `--acc` と同じ青を置いていたが、意匠を
# 2 色に割った時点で青は「押せる」の色になった ── **タブの絵は押せないので、幕のえんじ
# （`--curtain` の明るい側）を置く。**ここは `currentColor` が使えない唯一の場所なので、
# 意匠の色を変えるときに手で直す 1 か所である。
FAVICON_COLOR = "#9b2b3a"                        # 明るいタブ（`--curtain` の明るい側）
FAVICON_COLOR_DARK = "#b03a4a"                   # 暗いタブ（意匠の暗い側の `--curtain`）
FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    f'<style>.s{{stroke:{FAVICON_COLOR};fill:none;stroke-linecap:round}}'
    f'.b{{fill:{FAVICON_COLOR}}}'
    f'@media(prefers-color-scheme:dark){{.s{{stroke:{FAVICON_COLOR_DARK}}}'
    f'.b{{fill:{FAVICON_COLOR_DARK}}}}}</style>'
    '<path class="s" d="M14 4V20" stroke-width="2.3"/>'
    '<path class="s" d="M19.5 4V20" stroke-width="2.3"/>'
    '<path class="s" d="M14 4C13.2 11.6 11.4 15.8 5.4 17.6" stroke-width="3"/>'
    '<circle class="b" cx="5.4" cy="17.6" r="2.9"/></svg>')

# **data: で埋め込む。** 静的ファイルは配らない約束（`serve.py`）があるので、
# ファビコンもファイルとして置けない ── HTML の中で完結させる
FAVICON_HREF = "data:image/svg+xml," + quote(FAVICON_SVG, safe="")


def favicon_tag() -> str:
    return f'<link rel="icon" href="{FAVICON_HREF}">'


if __name__ == "__main__":                       # 資料に貼るための 1 枚を書き出す
    import sys
    from pathlib import Path
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("taguri-mark.svg")
    svg = mark(96).replace('class="tgm "', "").replace(
        "<svg ", '<svg xmlns="http://www.w3.org/2000/svg" style="color:#0b0b0b" ')
    out.write_text(svg + "\n", encoding="utf-8")
    print(out)
