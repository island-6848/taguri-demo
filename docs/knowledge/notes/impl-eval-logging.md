---
id: impl-eval-logging
type: decision
status: adopted
date: 2026-10-17
title: 推薦を本番で測るための記録を入れた。答えの行に順位・点・版、1 人 1 日 1 画面 1 行の rec_shown（書き直しは 6 回まで・180 日で消す）、設定の「推薦の改善の分析に使わない」。規約の文面は草案
sources:
  - cloudflare/migrations/0029.sql
  - cloudflare/src/screens/evalrec.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/reminder.js
  - cloudflare/src/screens/settings.js
  - cloudflare/src/recommend.js
  - cloudflare/test/evalrec.test.js
  - tools/review/replay_eval.py
  - cloudflare/test/test_replay_eval.py
  - docs/000007-taguri-terms-of-use.md
  - docs/service-privacy-draft.md
links:
  - depends_on: plan-real-data-eval
  - depends_on: dec-no-n1-evidence
---
起案者「1も2もお願い」（2026-10-17）。plan-real-data-eval の §8 の段 1。

- **答えの行（reaction）に rank・score・ver・arm。**
  - 答えたときに、おすすめの控え（rec_cache）の並びから引く。理由（why）と同じ 1 回の読み出しで済む。
  - どの画面で答えても残す。開幕リマインドの答えにも、そのときの点が要るため。
  - 書き込みは増えない。arm は 2 つの並べ方を混ぜるとき（方法 B）用で、今は NULL。
- **rec_shown（利用者 × 日 × 画面）。** おすすめは絞った後に出した分、開幕リマインドは出した全部。
  - 新しく出した公演があるときだけ書き直す。1 日 6 回まで（1 人 1 日 12 行、300 人で 3,600 行）。
  - 設計では「1 人 1 日 1 行」としていたが、答えるたびにカードが入れ替わる分を数えていなかったため直した。
  - その日の最初の行を書くときに、その人の 180 日より古い行を消す。cron は使わない。
  - アカウントの削除で消す。毎日の控えには自動で入る（DERIVED ではない）。
- **設定の「推薦の改善の分析に使わない」**（app_setting の analysis_optout）。
  - 選ぶと、どちらの記録も書かない。それまでの rec_shown も消す。
  - 集計の script でも、その人を外す。
- **部品を外す旗。** `scoreFromIndex({ablate: {split, expand}})`。既定の動きは変えない（試験で確かめた）。
- **手元の集計。** `tools/review/replay_eval.py` の counts と logged。
  - 持ち主は別の行に出す。
  - 人数がそろうまで、判定は出さない。
  - 日 t の索引を組み直して再生する橋は、まだ作っていない。
- **規約・プライバシー。** 第 5 条 4 項を直し、7 項（分析）を足した。どちらも「草案・起案者の確認待ち」。
  - アプリの中には規約の画面がまだ無い。そのため、設定のカードに同じ中身を短く書いた。
