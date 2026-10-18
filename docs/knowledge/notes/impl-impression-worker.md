---
id: impl-impression-worker
type: decision
status: adopted
date: 2026-10-18
title: 感想で書いた特徴への好みを、サービス版（Worker）の推薦の順位と理由に効かせた（規則だけ、LLM なし、#104）
sources:
  - https://github.com/island-6848/taguri-demo/issues/104
  - cloudflare/src/impression.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/impression.test.js
  - cloudflare/test/impression-recommend.test.js
  - cloudflare/scripts/measure_worker_replay.mjs
  - docs/impression-preferences.md
links:
  - answers: q-impression-not-in-service
  - affects: dec-reco-on-worker
---
起案者の指示（2026-10-18）「感想で書いた内容を推薦に反映させるところまで踏まえて」。q-impression-not-in-service の案 1 を採った（推しは案 2 だったが、起案者が反映までを指示した）。
- 規則は tools/review/impression_preferences.py の移植（PRIOR 3・WEIGHT 0.75・上位 3 特徴）。Python と同じ感想に同じ好みを返すことを試験で突き合わせる。利用者が増えても費用が増えないよう、LLM は呼ばない（dec-no-llm-per-user）
- 特徴は観た公演の種類の言葉（#題材など 6 軸）に限る。好みのある表記だけを、その特徴が付いていた軸で索引から引く。候補全部の言葉は読まない（#138 の CPU の注意）
- 点の付いた候補は上げ下げし、点の無い公演は好みが正のときだけ、補正の大きい順に 40 件まで加える。Python の rerank は全部を加えるが、Worker では後の束ねる計算が数百件ぶん重くなるので絞った
- 効かせ方は「作品の内容」（theme）の段を掛ける。0 なら補正しない
- CPU（手元、最悪の場合＝全記録に感想）: 評価 100 件で +9 ms。正規化の結果を覚え、評価の言葉の無い節を先に捨てて、最初の版の +30 ms から下げた。控えが当たる表示では増えない
- まだのこと: 当たりが良くなるかは手元の再生（replay、H1）でまだ測っていない。感想を書いていない利用者には何も変わらない。評価が多い人では、好みの作り直しを裏の答え合わせ（gate）と同じく控えから使い回す余地がある
