---
id: react-slow-cause
type: finding
status: confirmed
date: 2026-10-14
title: 興味あり・なしの記録が遅かったのは、1 回押すごとに本人の推薦を 2 回まるごと計算し直していたため
sources:
  - tools/taguri/serve.py
  - tools/taguri/app.py
links:
  - supports: dec-recommend-ui-1014b
---
コードを読んで確かめた（実測はしていない。本番の Render の無料プランは CPU が小さく、眠りからの起動にも約 1 分かかる〔render-free-spin-down〕）。`serve.on_react` は、反応を DB に書いたあと
1) `_siblings` ── 同じ作品のツアーの他会場を探すために `APP._load(user_id)` を呼び、
2) `fill_slot` ── 答えた枠に入れる次の候補を選ぶためにもう一度 `APP._load(user_id)` を呼んでいた。
`_load` は本人の評価・クレジット・反応・題材・感想の好みを全部読み直して推薦を作り直す重い処理で、これが返事の前に 2 回走っていた。持ち主の操作では、手元に無い公演を控えに足す `_pick` も走る（こちらは列に積むだけ）。
直したこと（dec-recommend-ui-1014b）: 券に他会場の id（data-tours）を載せて画面から送り、記録の要求では `_load` を呼ばない。入れ替わりの 1 枚は、記録の返事のあとに別の要求（fill_only）で頼む。眠りからの起動の待ちは、この変更では縮まない。
