---
id: f-multi-piece-handling-1019
type: finding
status: confirmed
date: 2026-10-19
title: 1 回の公演に複数の演目がある場合、本番（Worker）では 1 公演 = 1 記録・評価 1 つ。演目ごとに分ける仕組みは Render 時代の Python（メール取り込み）にしか無い
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/rate_performances.py
  - https://github.com/island-6848/taguri-demo/blob/master/cloudflare/src/screens/works.js
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/render_recommend.py
links:
  - affects: dec-noh-program
  - affects: q-nonplay-in-reco
---
起案者の問い（2026-10-19）「1 回の公演で複数話を上演してるものの扱いどうしてる？」に、master のコードを読んで答えた。

- Python（rate_performances.detect_programs・programs_of）: 起案者のメール取り込みで、セット券・交互上演（「プログラムA（デカローグ1…、3…）」「〈セット券〉「A」「B」」）を演目ごとの作品に分ける候補を出し、画面で直せる。「〜◯◯より〜」は原作の表記として分けない。splits の指定は D1 に移していない（0010.sql）
- Worker（本番）: works.js の冒頭のとおり、一般の利用者はメールを取り込まないので splits の道は移植していない。記録は題名ごとに 1 行（work_key = title_key）で、評価は 1 つ。演目ごとに評価したいときは、題名を変えて別の記録として足すしかない（同じ公演に結び付けられる）
- 結び付けた公演の出演・スタッフは全部その記録の材料になる。観た回に出ていない人は cast_off で外せるが、「どの演目が良かったか」は持てない
- 表示: 能・狂言・歌舞伎・文楽・落語・寄席はスタッフ欄の演目をあらすじの枠に出す〔dec-noh-program〕。ただしこれらは題名で推薦の候補から外している〔q-nonplay-in-reco〕
- 推薦の索引（rec_stage）も 1 公演 1 行で、演目単位の行は無い

分からなかったこと: 本番の利用者が、複数演目の公演をどう記録しているか（行数を数えていない）。
