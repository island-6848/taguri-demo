# 同梱しているもの

**画面から外のサイトを読み込まない。** 「記録を見返す」画面は「このページの数字はすべて
お使いの端末内のデータだけで作っており、外には何も出していません」と書いている。
**CDN から読むとこの記述が嘘になる**ので、使うものはここに置いて自分で配る。

| ファイル | 版 | 出どころ | sha256 |
|---|---|---|---|
| `d3.v7.min.js` | d3 7.9.0 | `https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js`（2026-08-24 に取得） | `f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539` |

## 何に使っているか

作り手の再会タイムライン（`tools/taguri/timeline.py`）だけである。**時間軸の拡大・縮小に
使う** ── レーンが 54 行・横が 5 年あるので、混んでいる時期を見るには軸を伸ばせる必要が
ある。図そのものの骨（軸の目盛り・レーンの並び）は Python 側で決めてある。

## 配り方

`serve.py` の `/vendor/d3.js` から配る。**この 1 本だけを名指しで通す** ── 置き場所ごと
配ると `ratings.db` を読ませる道ができる。

## 版を上げるとき

上の表の版・出どころ・sha256 を必ず一緒に書き換える。**どこから来たものか分からない
ファイルをリポジトリに置かない。**

    curl -sSL "https://cdn.jsdelivr.net/npm/d3@<版>/dist/d3.min.js" -o tools/taguri/vendor/d3.v7.min.js
    sha256sum tools/taguri/vendor/d3.v7.min.js

## ライセンス

**d3 は ISC ライセンスである。** 「著作権表示とこの許諾表示を、すべての複製に載せること」が
条件なので、**`d3.LICENSE` を同じ場所に置いてある。** 縮めた版のファイル冒頭には
`Copyright 2010-2023 Mike Bostock` の 1 行しか入っておらず、許諾表示が落ちている ──
**同梱するときは許諾表示のほうも一緒に置く。**

版を上げるときは `d3.LICENSE` も取り直す。

    curl -sSL "https://cdn.jsdelivr.net/npm/d3@<版>/LICENSE" -o tools/taguri/vendor/d3.LICENSE
