---
id: q-synopsis-reader
type: question
status: open
date: 2026-10-13
title: あらすじの読み取りを誰が担うか（Claude の定期実行・Gemini API・当面読まない）
links:
  - depends_on: synopsis-llm-history
  - depends_on: dec-crawler-gha-private
---
起案者の問い（2026-10-13）: 自分の Claude で読んでサイトに上げられるか。
A: Claude Code の定期実行（Routine）が、非公開リポジトリの新しいあらすじを読み、同じ形の themes.jsonl を書き戻す。API キー不要・鍵をどこにも置かない。ただし起案者の使用枠を分け合う（2026-08-27 に見送った理由の一つは残る）。
B: Gemini API の鍵を taguri-crawler の秘密に入れる（今の作りのまま動く）。
C: 当面読まない（推薦は人物の一致だけ）。
利用者の感想を AI で読むなら API と利用者の同意が要る（プランは他人向けのサービスの裏側には使えない）。
