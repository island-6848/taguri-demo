---
id: impl-origin-korea-tag
type: decision
status: adopted
date: 2026-10-16
title: 種類「原作の国 韓国」を、作り手のクレジットの韓国人名とハングルから自動で付ける（案 A）
sources:
  - tools/review/user_recommender.py
  - tools/review/test_origin_country.py
  - cloudflare/src/screens/recommend.js
  - cloudflare/test/kind-off.test.js
links:
  - answers: q-origin-country-how
  - depends_on: origin-korea-in-catalogue
---
起案者「A」（2026-10-16、q-origin-country-how）。
- user_recommender.korean_origin: 題名にハングル、または 原作・原案・脚本・作曲・作詞・台本・脚色・作・音楽 のクレジットに「韓国の姓・名（片仮名 2〜5 字）」かハングルがあれば ("#原作の国", "韓国")。出演者は見ない（韓国の俳優が出る日本の公演を韓国原作にしない）。姓からアン・ジョンを外し、名に ッ・ー・ヴ があるものは外す（Anne Chislett・John Du Prez・Harvey Fierstein を誤って拾わない）
- stage_tags に足したので、索引を作るとき（これからの公演の postings と、評価した公演の rec_people）の両方に入る。Worker は索引を読むだけなので、次に索引を配った日から効く。CONTENT_AXES に入れたので、それだけで理由になれる。詳細の「話・脚本・構成」の重み 0.5 は #原作 と同じ
- 理由の見出しは「原作の国 韓国」、出典は「クレジットの作り手の名前」。✕ で「使わない」にもできる（impl-kind-reason-off）
- 今の公演（2026-10-16 の作業データ）で 6 題に付く: 韓国原作と確かめた 3 題と、たぶん韓国のもの 3 題。手で見た 8 題のうち違った 2 題（カナダの作家・韓国の出演者だけのフェスティバル）は付かない。見落としは数えていない
- 無料枠: 索引の行が増えるのは付いた公演の分だけ（数十行）。D1 の書き込みの予算の中で差分として送られる
