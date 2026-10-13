---
id: dec-synopsis-reader-claude
type: decision
status: adopted
date: 2026-10-13
title: 公演のあらすじは起案者の Claude が一度だけ読み、結果をデータベースに置く。Gemini API は利用者の感想を読むときだけ
sources:
  - tools/credits/extract_theme_llm.py
  - https://claude.ai/code/session_015xXsQ9C4423EMquRbg7m3U （起案者の指示）
links:
  - answers: q-synopsis-reader
  - depends_on: synopsis-llm-history
  - depends_on: dec-crawler-gha-private
  - affects: q-catalog-to-worker
  - raises: q-synopsis-routine-quota
---
起案者の指示（2026-10-13）:「あらすじの情報文章もってきて、解読は一度で済むよね？こっちでそれやって、サイトで動かす情報はデータベースに置くのじゃダメなの？gemini apiは利用者の感想を抽出して推薦の向上に活かすときのみ」。q-synopsis-reader の A を採る。

作り（extract_theme_llm.py）:
- 取得処理（taguri-crawler の GitHub Actions）は `TAGURI_THEME_READER=queue` で動き、LLM を呼ばない。読み取り待ちの本文を `data/credits/synopsis_queue.jsonl`、指示（g2）を `synopsis_prompt.txt` に書き出す。Gemini の鍵は渡さない。
- 起案者の Claude（定期実行）が `--print-queue N` で Gemini に渡していたのと同じ指示・同じ本文を受け取り、答えを JSON で書く。
- `--import-answers FILE` が、待ちの一覧にある本文と突き合わせて同じ検査（本文に実在するか・要素の数の上限）を通し、themes.jsonl に `model: claude-routine` で足す。足した分は待ちから外す。済んだ公演は二度と読まない。
- サイトが使うのは確定した themes.jsonl を D1 に入れたもの（届ける段は q-catalog-to-worker で作る）。

2026-08-27 に claude CLI をやめた理由（対話用と同じ枠・同じログインにバッチの認証を乗せる）のうち、認証の面は定期実行がクラウドのセッションで動くので手元のログインを使わない。使用枠を分け合う面は残る（q-synopsis-routine-quota）。
利用者の感想を読むのは Gemini API に限る（まだ作っていない。利用者の同意が要る）。
