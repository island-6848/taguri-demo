---
id: q-webfont-local
type: question
status: open
date: 2026-10-13
title: 調整室で選んだ書体（Zen Old Mincho など）を、外部から読み込まずに全員の画面で出すには
sources:
  - web/style.css
links:
  - depends_on: design-studio
---
web/style.css の --mincho の注記に「外部からフォントを読み込むと、端末内のデータだけで作るという守り（企画書 5 章）が 1 か所破れる」とあり、書体は端末にあるものだけを並べている。調整室の見本は Google Fonts を使っているので、実際の画面では Zen Old Mincho・Zen Kaku Gothic New が入っている端末でしか同じ見え方にならない（無い端末では ヒラギノ明朝・游明朝 に落ちる）。
選択肢: (1) いまのまま端末の書体に任せる、(2) 書体のファイル（どちらも SIL Open Font License）を自分のサイトに置いて配る ── 外部へは通信しないので守りは破れないが、日本語の書体は 1 本数 MB あるので、使う文字だけに絞る（サブセット）手間と読み込みの重さを測る必要がある。起案者の判断待ち。
