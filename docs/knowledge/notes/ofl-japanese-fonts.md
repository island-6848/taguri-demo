---
id: ofl-japanese-fonts
type: finding
status: confirmed
date: 2026-10-13
title: 商用でも無料の日本語書体（SIL OFL）と、自分のサイトで配るときの重さ
sources:
  - https://raw.githubusercontent.com/google/fonts/main/ofl/zenoldmincho/OFL.txt
  - https://raw.githubusercontent.com/google/fonts/main/ofl/zenoldmincho/METADATA.pb
  - https://raw.githubusercontent.com/google/fonts/main/ofl/zenkakugothicnew/METADATA.pb
  - https://raw.githubusercontent.com/google/fonts/main/ofl/lineseedjp/METADATA.pb
  - https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsansjp/METADATA.pb
  - https://forest.watch.impress.co.jp/category/offc/font/index2.html
links:
  - answers: q-webfont-local
---
起案者の指示（2026-10-13）「書体は商用利用可な無料のものを使いたいね」。
Google Fonts の公式リポジトリ（google/fonts）の ofl/ に、Zen Old Mincho・Zen Kaku Gothic New・BIZ UDPGothic・Noto Serif JP・Noto Sans JP・Shippori Mincho B1・IBM Plex Sans JP・LINE Seed JP の OFL.txt があることを 2026-10-13 に確かめた（Zen Old Mincho の OFL.txt の冒頭は「licensed under the SIL Open Font License, Version 1.1」）。SIL OFL は使用・埋め込み・改変・再配布が商用でも無料で、禁じているのは書体ファイルだけを売ること（OFL の一般的な条件は二次情報の要約から）。
重さ（2026-10-13 に実際に測った）: 1 本（1 つの太さ）の woff2 が、全文字で Zen Kaku Gothic New 1.04 MB・Zen Old Mincho 1.99 MB。かな・英数・JIS 第 1 水準漢字（約 3,560 字）に絞ると 0.45 MB・0.85 MB。第 2 水準の漢字（人名に多い）は端末の書体で出る。
自分のサイトから配るなら外部へは通信しないので、style.css の「外部から読み込まない」守りは破れない。
