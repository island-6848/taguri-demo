#!/usr/bin/env python3
"""「たぐり」のロゴ。**自前の inline SVG で、外部から 1 枚も読み込まない**（`icons.py` と同じ約束）。

## 何を描いてあるか（2026-10-18 からの形）

**幕の開いた丸い舞台に「たぐり」が立ち、外の丸の糸が右下でほどけて結び目をつくる。**
字はひな明朝（Hina Mincho、OFL）の字形を図形にしたもの。「ぐ」の濁点は 2 つの星（スポットライト）、
「り」の払いの先から糸がのびて舞台の床の線になる。外の丸は下ほど太く上ほど細い。
決めるまでの経緯は docs/knowledge/notes/dec-ui-1018b.md、絵の作り方は docs/design/logo/make_type.py。

サービス版（web/index.html）と同じ絵を使う（起案者 2026-10-18「古いPython版のロゴも揃えて」）。
**絵の本体は `logo_art.py`**（make_type.py --python が書き出す。手で直さない）。

- パソコンの幅: 丸い紋章（`EMBLEM`）
- 電話の幅（820px 以下）: オペラグラスのアイコンと「たぐり」の横組み（`ROW`）。紋章を帯の高さまで縮めると字が読めない
- タブの絵: オペラグラスの小さい版（`FAVICON_HREF`）

## 色を持たせない

ロゴは `currentColor` を継ぐので、置いた場所の文字と同じ色になる（暗い表示でも読める）。
**タブの絵だけは色を持つ** ── タブの地色はページの明暗に従わないので、SVG の中の
`prefers-color-scheme` で明るい色に替える。

以前の標章（縦の糸の束から 1 本を引き出し、先に玉）は 2026-10-18 に置き換えた。
"""

from __future__ import annotations

from logo_art import EMBLEM, FAVICON_HREF, ROW


def mark() -> str:
    """丸い紋章だけ（資料に貼るときなど）。"""
    return EMBLEM


def lockup(cls: str = "") -> str:
    """帯の頭に置くロゴ。**読み上げは「たぐり」** ── 字は絵に組み込んだので、SVG の aria-label で読ませる。"""
    return f'<span class="tglock{" " + cls if cls else ""}">{EMBLEM}{ROW}</span>'


CSS = """
/* ---- ロゴ（サービス版の theme.css と同じ組み方） ------------------------------ */
.tglock{display:block;line-height:1}
.side .brand.tglock{padding:14px 12px 10px;text-align:center}
.tglock .tgl-full{display:block;width:168px;height:auto;aspect-ratio:300/312;margin:0 auto}
.tglock .tgl-row{display:none;height:30px;width:auto;aspect-ratio:168/64}
@media(max-width:820px){
 .side .brand.tglock{display:flex;align-items:center;padding:0 6px 0 4px}
 .tglock .tgl-full{display:none}
 .tglock .tgl-row{display:block}}
"""


def favicon_tag() -> str:
    # **data: で埋め込む。** 静的ファイルは配らない約束（`serve.py`）なので、ファビコンもファイルとして置けない
    return f'<link rel="icon" href="{FAVICON_HREF}">'


if __name__ == "__main__":                       # 資料に貼るための 1 枚を書き出す
    import sys
    from pathlib import Path
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("taguri-logo.svg")
    svg = EMBLEM.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" style="color:#1d1d1f" ', 1)
    out.write_text(svg + "\n", encoding="utf-8")
    print(out)
