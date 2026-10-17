---
id: impl-admin-tool
type: decision
status: adopted
date: 2026-10-17
title: 手元で開く管理画面（tools/admin）を作った。手で直した分は D1 の stage_override に置き、Worker が画面に出すときに重ねる。読み取りは Claude Code
sources:
  - tools/admin/admin.py
  - tools/admin/serve_admin.py
  - tools/admin/admin.html
  - cloudflare/migrations/0028.sql
  - cloudflare/src/screens/override.js
  - cloudflare/test/override.test.js
  - cloudflare/test/test_admin_tool.py
  - .claude/skills/taguri-admin-queue/SKILL.md
links:
  - depends_on: dec-synopsis-reader-claude
  - raises: q-admin-override-in-index
---
起案者「管理者画面を作成して。あくまでこのパソコンとかで開く用。どうしてもポスターがない画像に自分で足したり、詳細を編集したり、あらすじを追加したりする。個人で手動で追加したものは、LLM解析が必要なものはこのclaudeを呼び出して行ったり、自動的にデータベースやログに書き込まれるようになってほしい」（2026-10-17）。
- 開き方: `python3 tools/admin/serve_admin.py`。127.0.0.1 だけに開き、起動のたびに変わる鍵（URL の t、以降は X-Admin-Token）が無いと何も返さない。Host も 127.0.0.1/localhost に限る
- 置き場所の決め方: カード（rec_card）は取得のたびに全部作り直され（build_cards の to_sql が新しい版に入れ替える）、取得は非公開の taguri-crawler の Actions で動くので、手元のファイル（hand_themes.json）に置いても本番に届かない。そこで本番の D1 に stage_override（migration 0028）を作り、Worker が cards.cardTemplates（あらすじ・題材・料金と data-yen）と fallback.stageInfo（会場・期間・料金・タイムテーブル・出演などの欄）で重ねる。取得し直しても消えない
- ポスター: deliver_posters.encode で WebP に縮め、R2 の REST API で入れ、poster の行を INSERT OR REPLACE。名前は版付き（<id>-a<UTC 時刻>.webp）。Worker はポスターを 7 日間 immutable で控えるので、同じ名前で差し替えると古い絵が残るため。原本は data/admin/posters に残す
- 記録: 直すたびに data/admin/log.jsonl と D1 の admin_log に同じ中身（前の値・新しい値・誰が）を書く。同じ中身の保存は書かない
- 読み取り（あらすじを入れて題材を空にしたとき）: data/admin/llm_queue.jsonl に積む。① 画面の「Claude で題材を読み取る」は手元の `claude -p` を呼ぶ（ANTHROPIC_API_KEY・ANTHROPIC_AUTH_TOKEN を外して渡す ── 入っていると従量課金の API になる）。② claude が無い・動かないときは積んだまま。Claude Code のセッションで skill taguri-admin-queue（`admin.py queue` → 答えを JSON に → `admin.py answer`）。Gemini は使わない〔dec-synopsis-reader-claude〕
- 無料枠: 書く前に数える。CAPS に admin_d1_writes_day（1,000）・admin_posters_month（300）を足し、取得と共通の D1・R2 の上限も見る（控えは手元の data/admin/free_tier/usage.json。取得の控えとは別なので、R2 の保存の合計は取得の控えと Worker の点検で見る）
- 確かめたこと: Worker のテスト（override.test.js、全 224 件）、Python のテスト（test_admin_tool.py: 偽の D1 に migration を当てて、検索・保存・記録・上限で止まる・ポスター・読み取り・SQL の引用）、ブラウザで管理画面（偽の D1）を動かし、保存・記録・読み取り待ち・鍵が違うと 403 を確かめた。本番の D1・R2 にはまだ書いていない（手元のパソコンで wrangler にログインして使う）
- まだのこと: おすすめの計算に使う題材（rec_credit の #題材）と、探す・出さない語が引く rec_card の ws/synz は、手で直した分をまだ使わない〔q-admin-override-in-index〕
