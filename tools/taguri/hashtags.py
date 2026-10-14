"""感想のハッシュタグ（起案者の指示 2026-10-14「感想を書くとき、ハッシュタグをユーザーが独自で作って
検索できるようにして」）。

タグは感想の文に `#タグ` と書くだけで作られる（別の表は持たない ── 文を直せばタグも直る）。
「＃」（全角）でも書ける。タグの終わりは空白・句読点・括弧・次の「#」。30 字まで。
"""
from __future__ import annotations

import re
import unicodedata

_TAG = re.compile(r"[#＃]([^\s#＃、。，,．.!！?？「」『』（）()\[\]【】<>＜＞]{1,30})")


def tags_in(text: str) -> list[str]:
    """文に出てくるタグ（出てきた順・重複なし）。比べやすいよう NFKC で正規化する（全角英数を半角に）。"""
    out: list[str] = []
    for m in _TAG.finditer(text or ""):
        t = unicodedata.normalize("NFKC", m.group(1))
        if t and t not in out:
            out.append(t)
    return out


def counts(texts) -> list[tuple[str, int]]:
    """タグと、それが付いている感想の数。多い順、同じ数なら名前の順。"""
    n: dict[str, int] = {}
    for t in texts:
        for tag in tags_in(t):
            n[tag] = n.get(tag, 0) + 1
    return sorted(n.items(), key=lambda kv: (-kv[1], kv[0]))
