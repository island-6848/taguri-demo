---
id: dec-member-affil-tag
type: decision
status: adopted
date: 2026-10-24
title: 出演者の出身・所属の札（#出身・所属 宝塚歌劇団 / STARTO ENTERTAINMENT）を作り、宝塚の公演と OG の出る公演、STARTO の人が出る公演どうしをつなぐ。一覧は手元のデータに、Wikipedia と公式サイトを足す
sources:
  - tools/review/user_recommender.py
  - tools/review/measure_nets.py
  - cloudflare/scripts/build_recommend_index.py
  - cloudflare/src/recommend.js
  - cloudflare/test/test_recommend_index.py
links:
  - depends_on: find-takarazuka-starto-coverage-1024
  - depends_on: dec-takarazuka-genre-1024
  - answers: q-affil-external-list
  - affects: comp-recommender
---
起案者の指示（2026-10-24）「推薦の特例で、宝塚歌劇団の作品を好む人には、宝塚OGが出ている舞台を勧めたい。宝塚歌劇団の所属者（現・退団済み）をつくる必要がある。同様にSTARTO ENTERTAINMENT（旧ジャニーズ事務所）も同じようにしたい。」
外の一覧について、起案者の答え（同じ日）は「b,c でお願い」。b は Wikipedia の退団者一覧、c は公式サイト〔q-affil-external-list〕。

**仕組み**
- 公演の種類の札に新しい軸 `#出身・所属` を足した（UR.MEMBER_AXIS、CONTENT_AXES に入れた）。
- 札の付け方（build_recommend_index.member_list・member_tags）:
  - 宝塚歌劇団の公演（UR.is_takarazuka）そのものに「宝塚歌劇団」を付ける。
  - 出演者が宝塚歌劇団の人なら、どの公演にも「宝塚歌劇団」を付ける。
  - 出演者が STARTO の人なら「STARTO ENTERTAINMENT」を付ける。
- 好みは札ごとに学ぶ。宝塚の公演を高く評価した人には「#出身・所属 宝塚歌劇団」の値が付き、OG の出る外の公演が上がる。
- 理由の行は「出身・所属 宝塚歌劇団」。人の名前は出さない。
  - 起案者は書き方を決めていないので、ほかの種類（ジャンル・形式）の行とそろえた。
  - 名前を出す形（「宝塚歌劇団出身の〇〇が出演」）にするなら、理由の作り方を変える必要がある。
- ✕ で外すと、その札だけが効かなくなる。ジャンルの ✕ のように公演ごと外すことはしない。

**一覧の作り方**
- 宝塚歌劇団の人:
  - 宝塚歌劇団の公演の出演者。在団と退団を分けない。
  - 出演欄の括弧に「宝塚」とある人。「元宝塚歌劇団雪組」も入れる。そのため measure_nets.affiliations に former=True を足した。所属の表（rec_affil）には、これまでどおり前の所属を入れない。
- STARTO の人: 括弧の所属が STARTO の書き方（UR.STARTO_AFFIL）。社名、Jr.、グループ名。
- 外の一覧: `data/affil/members.json`（札の名前 → 人の名前の並び）を置けば足す。
- 作業データで数えると、宝塚歌劇団 279 人、STARTO 104 人。これからの候補 4,766 件のうち、宝塚歌劇団の札が 74 件、STARTO の札が 26 件に付く。

**まだのこと**
- b と c の取り込み。このセッションからは ja.wikipedia.org・kageki.hankyu.co.jp・starto.jp に通じない（通信の許可の一覧に無い）。起案者のやることに足した。
  - 通じたら、使ってよい条件を確かめてから members.json を作る。
  - Wikipedia（CC BY-SA）は、使う形に合わせて出典の書き方を決める。
- 本番に効くのは、次に索引を作り直して届けたとき。

**無料枠**
- 札の行は約 100 行増えるだけ。D1 の書き込みは、索引を届ける日の差分に入る程度。
