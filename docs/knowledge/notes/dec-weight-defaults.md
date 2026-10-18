---
id: dec-weight-defaults
type: decision
status: adopted
date: 2026-10-18
title: 効かせ方の初めの設定を群ごとに: 出演者・作品の内容は「少し強く」、制作・宣伝・その他の役職は「あまり効かせない」、ほかは「ふつう」。保存してある人の値は変えない
sources:
  - cloudflare/src/screens/weights.js
  - cloudflare/src/screens/recommend.js
  - web/app.js
  - tools/taguri/app.py
  - cloudflare/test/fav-reco.test.js
  - cloudflare/test/recommend-screen.test.js
  - cloudflare/test/e2e-walk.js
links:
  - depends_on: dec-recommend-weights-worker
---
起案者の指示（2026-10-18）「効かせ方のデフォルトを設定する。出演者、作品の内容︰少し強く／制作・宣伝、その他の役職(上のどれにも入らないもの)︰あまり効かせない／それ以外はふつう。」

決めたこと:
- weights.GROUP_DEFAULT = {cast: strong, theme: strong, produce: weak, other: weak}、ほか（author・craft・stage）は mid（app.GROUP_DEFAULT・default_step も同じ）。段の倍率は前のまま（少し強く 2.0、あまり効かせない 0.5）
- 保存していない群はこの段で計算し、つまみもこの段を指す（readWeights・read_weights）。保存してある段（rank_weight の行）はそのまま。すべて「ふつう」で保存した人は「ふつう」のまま
- 順位に掛ける倍率は「倍率が 1.0 でない群」だけ（multipliersOf・_apply_weights）。前は「mid でない群」だった
- 「すべて『ふつう』に戻す」は「すべて初めの設定に戻す」に。押すと、つまみの data-default（群ごとの既定）を保存する（web/app.js・app.py の画面スクリプト）
- 使い始めの判定（screens/recommend の starting、選び方を出さない条件）は、新しい既定と比べる（weights.tunedWeights）
- 推薦の控え（rec_cache）は版 screen-v33 で作り直す（既定が変わると保存していない人の順位が変わるため）。D1 の読み書きは増えない（読むのは前と同じ rank_weight の行だけで、既定は保存しない）

試験: recommend-screen の効かせ方の期待を新しい既定に変えた（理由をコメントに書いた）。weights_fixture は保存していない群を app.default_step で埋める。e2e-walk でつまみの初めの位置（3・2・2・2・1・1・3）と「すべて初めの設定に戻す」の戻り先を確かめる。
