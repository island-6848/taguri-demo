---
id: q-admin-override-in-index
type: question
status: open
date: 2026-10-17
title: 管理画面で手で直した題材・あらすじを、おすすめの計算（rec_credit の #題材）と検索（rec_card の ws/synz）にも効かせるには、取得の側（taguri-crawler）が D1 の stage_override を読む必要があるか
sources:
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/scripts/build_cards.py
links:
  - affects: impl-admin-tool
---
いまは画面に出すとき（カード・日程・料金）だけ重ねている〔impl-admin-tool〕。#題材の行は build_recommend_index が themes.jsonl から作り、rec_card の ws/synz は build_cards が作る。どちらも非公開の taguri-crawler の Actions で動き、手元の data/admin は見えない。
- 案: 取得の作業の始めに D1 から stage_override を読み（読み出しは無料枠が大きい）、themes.jsonl に「手入力」として重ねる（hand_themes.apply と同じ形）。taguri-crawler はこのセッションから見えないので、確かめていない
- あわせて: 取得の側があとでその公演のポスターを見つけたとき、手で入れたポスターを上書きしてよいか（いまは deliver_posters の INSERT OR REPLACE で上書きされうる）
