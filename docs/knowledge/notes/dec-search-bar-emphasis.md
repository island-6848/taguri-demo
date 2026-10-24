---
id: dec-search-bar-emphasis
type: decision
status: adopted
date: 2026-10-21
title: 探すの画面の検索欄を目立たせる（幕の色を薄く敷いた帯・大きな丸い入力欄・幕の色で塗った「探す」）。CSS だけで、画面の HTML は変えない
sources:
  - web/theme.css
links:
  - affects: dec-search-tour-one-card
---
起案者の指示（2026-10-21）「『探す』のページ内にある検索バー強調して」。

- 欄の帯: 幕の色を 8% 敷き、縁を幕の色寄りにした角丸の枠
- 入力欄: 高さ 50px・文字 17px（電話の幅は 16px）・幕の色の 2px の丸い縁。入力中は幕の色の薄い輪を出す
- 「探す」: 幕の色で塗った丸いボタン（白い字）
- 印は .fav-add:has(#search-q) と #search-q だけで、お気に入りの追加など同じ .fav-add の欄は変えない
- 明るい表示・暗い表示・電話の幅（390px）・広い幅で写しを撮って確かめた
