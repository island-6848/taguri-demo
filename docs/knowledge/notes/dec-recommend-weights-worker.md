---
id: dec-recommend-weights-worker
type: decision
status: adopted
date: 2026-10-14
title: おすすめの画面の残り（効かせ方のつまみと /api/weight、見た推薦の記録、題材の手入力）を Worker に移した
sources:
  - cloudflare/src/screens/weights.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/weights.test.js
  - cloudflare/test/screens/weights_fixture.py
  - cloudflare/test/recommend-screen.test.js
links:
  - depends_on: dec-recommend-worker-cards
  - depends_on: impl-hidden-gate
---
起案者の指示（2026-10-14）「おすすめの画面を移して」。画面そのものは移してあったので、まだ「移しているところです」（503）を返していた書き込みを移した。
- 効かせ方（app.weight_form・save_weights・read_weights）: つまみの HTML は Python と一字一句同じ（weights.test.js）。保存は rank_weight（0010 の表）に、7 項目×5 段の組み合わせだけを受け、1 つでも違えば何も書かない。保存すると本人の推薦の控え（rec_cache）を消す（印が秒までしか持たないので、同じ秒の 2 回目を取りこぼした）
- 推薦への効かせ方: 本人の段の倍率（効かせない 0・あまり 0.5・ふつう 1・少し強く 2・とても強く 4）を、裏の答え合わせが選んだ倍率に掛け合わせる。「効かせない」の項目は寄与が 0 になり、順位からも理由からも消える。件数（おすすめの候補 N 件で一致）は、点を上げた人物と種類の項目ごとに数える
- /api/recommendation/visit・contact: 公開版は見た推薦を記録しない（カードを出すたびに D1 に書くことになるため）。Python の「記録の口が無い」ときと同じ {ok:false, disabled:true} を返す
- /api/hand_theme: 公開版の Python と同じく「公開版では公演情報の編集はできません」を返す
- まだ移していないもの: 「いまの設定で、おすすめに出なくなった公演が N 件」（w_dropped。計算を 2 回する必要があり、CPU 10 ミリ秒の中では見送った）、感想による並べ替え（impression_preferences。題材の表が D1 に無い）、県の地図（輪郭が D1 に無い）
