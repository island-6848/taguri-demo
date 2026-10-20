---
id: dec-split-pieces
type: decision
status: adopted
date: 2026-10-19
title: 1 回の公演で観た複数の作品は、利用者が望めば作品ごとに分けて評価・感想・出演者を持つ。記録は 1 件のまま。推薦は人ごとに「出た作品の評価の平均 × 縮めた件数 m/(1+(m−1)·0.4)」を 1 回だけ足す
sources:
  - cloudflare/migrations/0042.sql
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/src/screens/diary.js
  - cloudflare/src/screens/row.js
  - cloudflare/test/pieces.test.js
  - cloudflare/test/pieces-screen.test.js
links:
  - answers: q-split-pieces-1019
  - depends_on: f-multi-piece-handling-1019
  - affects: comp-cf-worker
---
起案者の指示（2026-10-19）「1 公演を 1 件として表示しつつ、評価や推薦、感想やあらすじの抽出の仕組みなどは作品数分分けられる？ただしユーザーが分けたいとしたときの任意」→ 人物が跳ね上がらないか・平均は適切かの検討〔q-split-pieces-1019〕→「0.4にしたい」（ρ の値）。

- 保存: work_piece（0042）。記録（works）1 行に、作品ごとの作品名・評価・気になった所・感想・その作品に出ていた出演者（cast_in。'' は全員）。1 記録 20 作品・1 人 2,000 行まで。書くたびに rec_rev・works_rev を進める。記録の改名（moveKey）・削除（deleteWorks）・アカウントの削除・書き出し（schema_version 2）に入れた。公演の結び付けを変えると cast_in は全員に戻す
- 画面: 記録を直す欄の「作品ごとに分ける」（/api/pieces）。2〜20 作品。日記帳などの行に作品ごとの評価と感想を並べる。「分けるのをやめる」で行を消す（記録は残る）
- 推薦（recommend.personValues）: 評価した作品があれば、記録そのものの評価の代わりに作品ごとの行を使う。人ごとに、出た作品の z の平均を、件数 m を m/(1+(m−1)ρ)（ρ=PIECE_RHO=0.4）に縮めた重みで 1 回だけ足す。10 本すべてに出た人も 2.17 件ぶん（上限 2.5）。順位（z）の分母では作品ごとの評価を 1/k の重みで数える。種の薄まり（SEED_K）も観劇 1 件で数える。作品に評価が 1 つも無ければ、記録そのものの評価を使う
- 裏の答え合わせ（chooseVariant）は、分ける前の 1 公演の行で行う（記録の評価がある観劇だけ）。同じ晩の作品を別の件にすると、作品どうしで答えが漏れる。感想の好み（impressionAdjust）も 1 公演 1 件にまとめ、作品ごとの感想をつなげて読む
- まだやっていないこと: 作品ごとの「気になった所」の画面（列はある）。あらすじからの題材の読み取りを作品ごとにすること（いまは公演全体の題材のまま）。Python の参照実装・メール取り込みの splits とはつないでいない
- 無料枠: 読みは記録を読むたびに本人の work_piece の行だけ（ふつう 0〜数十行。上限 2,000）。書き込みは保存 1 回で「消す n＋入れる n＋users の更新 2n＋控えの削除」、6 作品で約 25 行。保存は 1 行 4,000 字まで × 2,000 行 = 1 人最大約 8 MB で、D1 の 4 GB の止め〔dec-account-cap-counted〕の内側。新しいサービス・定期実行は無い
