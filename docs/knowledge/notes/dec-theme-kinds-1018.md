---
id: dec-theme-kinds-1018
type: decision
status: superseded
date: 2026-10-18
title: あらすじの言葉を 8 種類に分け、種類ごとに上限と推薦の重さ、根拠ごとに重さを持たせる（g5）
sources:
  - tools/credits/extract_theme_llm.py
  - cloudflare/scripts/build_recommend_index.py
  - tools/credits/test_theme_queue.py
  - cloudflare/test/test_recommend_index.py
links:
  - affects: eval-g5-trial-1018
  - affects: impl-theme-vocab
  - affects: q-theme-kinds-count
---
起案者の判断（2026-10-18）「まずそれでやってみる」。g5 の 8 種類それぞれの役割を、試し（eval-g5-trial-1018）の数を見ながら決めた。

| 種類 | 1 公演の上限 | 推薦の重さ | 索引 |
|---|---|---|---|
| 題材 | 4 | 1.0 | 入れる |
| 関係・感情 | 3 | 1.0 | 入れる |
| ジャンル | 2 | 1.0 | 入れる |
| 原作 | 2 | 1.0 | 入れる（「原作者」のお気に入りが #題材 の言葉で当てている） |
| 味わい | 2 | 0.7 | 入れる |
| 構造 | 2 | 0.7 | 入れる |
| 舞台設定 | 2 | 0.5 | 入れる |
| モチーフ | 3 | — | 入れない（カードの言葉には残す） |

- 根拠の重さを掛ける。本文 1.0／推定 0.7／作風 0.5。例: 推定の構造は 0.49
- 重さは索引の rec_credit.role_w（#題材の行）に入れる。Worker の計算はこれまでも role_w を掛けているので、Worker のコードは変えない
- 上限は全体で 14 語（モチーフを除く種類の合計）。g4 までは 6 語で切っていて、トーンの言葉などが落ちていた
- g4 までの行（種類は題材・舞台設定・トーン・原作）も、同じ表で切って重さを付ける。トーンは味わいと同じ扱い。種類の無い言葉（手で入れた題材）は全体の上限まで重さ 1
- 読み取りの検査（import_answers）: 推定は引用（from）が本文に無ければ落とす。作風は手がかりに無ければ落とす。種類ごとの上限で切る。ハッシュタグは 3〜6 個まで残す（カードに出すかは起案者の確認待ち）
- Gemini で直接読む経路（ask・enrich_one）は g4 のまま。根拠の検査は運営者の Claude の待ち（--print-queue・--import-answers）でしか行わないため
- 書き込みの増え方: 候補 1 公演あたり #題材 の行が最大 6 → 14。読み取り済みの約 1,400 公演がすべて上限まで付いても約 1.1 万行の追加で、毎日の索引の差分の枠（deliver_catalogue の上限）の中で数日に分かれて入る
- 種類の数そのものは、調べた結果（q-theme-kinds-count）で見直す余地がある。大量の読み取りを始める前に決める
