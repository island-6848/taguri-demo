---
id: dec-reason-two-works
type: decision
status: adopted
date: 2026-10-18
title: 理由の作品名はいちばん新しい公演といちばん古い公演の 2 つまで。お気に入りから引いた公演の題名も書き、札は「人物」「形式」
sources:
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/recommend-screen.test.js
  - cloudflare/test/kind-off.test.js
  - tools/review/render_recommend.py
  - tools/review/measure_nets.py
  - tools/review/test_reason_works.py
links:
  - supersedes: dec-reason-work-titles
---
起案者の指示（2026-10-18）「おすすめ理由に『（お気に入り・興味ありの公演から）』って書くのやめて。ちゃんと公演タイトル書いて。あと公演タイトルすでに書けているものも、最大2件だけ表示。一番最近の公演と一番古い公演から計2個」「『種類』ってよりは形式？って表現近いと思う」。

分かったこと（コード）: 「（お気に入り・興味ありの公演から）」は、作品名が引けず評価の本数も 0 の人に出していた（screens/recommend.js worksText）。作品名の材料（personTitles）は評価した記録と興味ありの公演だけで、お気に入りの名前から引いた公演（seedsFromFavourites の seeds）を入れていなかった。お気に入りの人と同じ公演に出た人は、お気に入りの公演のおかげで上がっているのに題名を書けなかった。

決めたこと:
- personTitles に、お気に入りの名前から引いた公演（題名と初日を stageInfo で読む）を足した。並びは日付の新しい順（評価した記録は観た日、興味ありとお気に入りの公演は初日。同じ日は印の順、日付の無いものは後ろ）
- 理由には先頭（いちばん新しい）と末尾（いちばん古い）の 2 つだけを書き、残りは「ほか N 本」と本数だけ（WORKS_SHOWN = 2）。作品名も本数も無い人には何も添えない
- おすすめのカードでは、理由の作品名からその公演自身の題名を除く（お気に入りの公演にその公演が入ることがある）
- 種類の理由の札の表示を「形式」に（データの鍵 #形式・#原作 などは変えない）。札と同じ見出し（#形式）は重ねて書かない（「形式 形式 ミュージカル」にしない）
- 古い Python 版（render_recommend.works_text・measure_nets.person_titles・reason_rows）も同じ決まりにした
- 計算の控え（rec_cache）の版を screen-v32 にした（前の控えは作り直す）

無料枠: お気に入りの公演の題名を読むのは、控えが古いときの計算だけ（公演は MAX_SEED_STAGES = 60 まで、rec_stage と catalogue を 1 回ずつ、読み取りは多くて 120 行）。D1 の無料枠（1 日 500 万行の読み取り）に対して小さい。

確かめたこと: recommend-screen.test.js（作品名は新しいものと古いものの 2 つ・お気に入りの共演者が『舞台ふたつめ』で書かれる・「（お気に入り・興味ありの公演から）」が出ない）、kind-off.test.js（札が「形式」）、test_reason_works.py。e2e-walk の理由「人物 出演 俳優甲（『終わった舞台』・『旅の芝居』）」「形式 原作 オリジナル（『終わった舞台』）」。

決めきれていないこと: 「最大2件だけ表示」に「ほか N 本」の本数を残してよいか（作品名は 2 つまでにしたが、本数は残した）。起案者に確かめる。
