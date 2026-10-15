---
id: impl-interest-split
type: decision
status: adopted
date: 2026-10-15
title: 興味ありは、1 公演ぶん（評価 1 件と同じ重さ）をその公演の人・種類に割って配る。(1) 人数で割る (2) 好きと分かっている人に多め (3) 興味なしにもいるものは弱める。「なぜ気になったか」に名前があればその人に多め
sources:
  - cloudflare/src/recommend.js
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/recommend-interest.test.js
links:
  - supersedes: impl-interest-seed
  - depends_on: lit-implicit-confidence
  - depends_on: lit-feedback-loop
  - depends_on: lit-bpr-pairwise
  - depends_on: lit-content-overspecialization
---
起案者の指示（2026-10-15）「1+2+3まとめて入れて」。案は記録の取り込みのセッションから（起案者の考え「本当は興味ありで理由を全部書いてもらいたいが、面倒になるので簡素な興味あり・なしにしている」＝押すのは 1 回、理由は推し量る）。
- 前（impl-interest-seed）: 興味ありの公演の全員に、お気に入りと同じ仮の ◎ を丸ごと配っていた。大人数の公演ではアンサンブルの 1 人の別の公演まで上がり、推薦 → 興味あり → 同じ人、の輪で偏る
- いま（recommend.js interestShares・interestContrast・personValues の liked/disliked）: 1 公演の合計 1 を、人に 0.5（INTEREST_PEOPLE_SHARE）・種類（#形式・#原作・#題材など）に 0.5 で割る（どちらかしか無ければ全部）。人の中では、評価・お気に入りから出した値が正の人に 1 + 3 × その値（INTEREST_PRIOR_BOOST）の割合で多めに、「なぜ気になったか」に名前がある人に 5 倍（INTEREST_NOTE_BOOST）、興味なしの公演にもいる人・種類は 興味あり件数 /（興味あり＋興味なし）倍。z は SEED_Z、重みは SEED_K/(SEED_K+評価の数) で、評価が増えるほど薄まるのは前と同じ。お気に入りの名前は除く
- 興味なしの公演も新しい順に 60 件まで人物を読む（D1 の読みは最大で公演 120 件ぶん）。画面の控えは screen-v5
- 劇団・主催は索引の人物（rec_people）に入っていないので、まだ (1) の対象外
- 数（0.5・3・5）は舞台のデータで確かめていない（dec-no-n1-evidence）。試験は性質（合計 1、共通するものが積み上がる、好きな人に多め、興味なしと比べる、名前のある人、薄まり）だけを確かめる

2026-10-15 追記（起案者の指示「単純に人数で割るのよくない。役柄の重要さで割るべき」）: 人の中は等分をやめ、役柄の重さで割る（recommend.castImportance・STAFF_IMPORTANCE）。
- 推薦の索引の人物（rec_people）は名前順に並べ替えて保存されていて、書かれた順が残っていない（build_recommend_index.py の sorted）。そこで公演の情報（rec_stage の entry、無ければ一覧 catalogue）に残る出演欄の文そのものから読む
- 出演: 書かれた順で 1 / (1 + 順位 / 2)（主役が先に書かれる慣行による）。「役名：名前」の人は 1.5 倍、「アンサンブル」の見出しより後は 0.3 倍。出演欄に見つからない人は、見つかった人のいちばん軽い重さ
- 作り手: 演出・脚本 1.0、原作 0.8、作曲 0.7、構成・音楽・振付 0.6、翻訳・潤色・作詞 0.5、ほか 0.3
- 画面の控えは screen-v6。数はどれも舞台のデータで確かめていない。出演欄の書き方は公演ごとにまちまちで、順が主役から並んでいない公演もありうる
