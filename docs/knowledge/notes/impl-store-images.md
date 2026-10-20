---
id: impl-store-images
type: decision
status: adopted
date: 2026-10-20
title: Google Play の掲載画像（フィーチャーグラフィック 1 枚・電話のスクリーンショット 5 枚）は、本物の画面に架空のデータを入れて写す
sources:
  - cloudflare/scripts/store_images.mjs
  - docs/store/images/
  - docs/store/google-play-listing.md
links:
  - affects: plan-app-release
  - depends_on: impl-android-twa
---
起案者（2026-10-20）「フィーチャーグラフィックとスクリーンショットも作って」。

- スクリーンショット: Worker と web/ の画面を手元で動かし（テストの harness）、360×640 の 3 倍（1080×1920、9:16）で写す。おすすめ・おすすめ理由・興味あり・評価・日記帳の 5 枚
- データ: テストのデータの仮の名前（舞台ひとつめ・俳優甲・劇場A など）を架空の題名・人名・劇場に置き換え、架空の公演を 5 つとあらすじを足す。**実在の公演・人・ポスターは使わない**（権利のため）。ポスターは「now printing」の札のまま
- 初回の案内（tour）と右下の「使い方」のボタンは写さない
- フィーチャーグラフィック: リンクのカード（public/assets/og.png、X で出ると起案者が確かめた）を高さ 500 に縮め、左右を同じ地の色で埋めた。文字は中央に寄っているので、端を切られても欠けない
- 分からないこと: Play の審査で、ポスターが空の画面がどう見られるか（実在のポスターを使うには権利の確認が要る）
