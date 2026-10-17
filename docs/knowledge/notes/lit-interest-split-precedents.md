---
id: lit-interest-split-precedents
type: finding
status: unverified
date: 2026-10-17
title: 興味ありの配り分け（式 10–11）の 4 つの手がかりは、どれも先行研究に近い形がある。まとめて学習なしの閉じた式で配る形は見つからなかったが、新しさは「組み合わせと場面」にとどまる
sources:
  - https://ir.webis.de/anthology/2017.sigirconf_conference-2017.36/
  - https://arxiv.org/pdf/1908.05928
  - https://ir.webis.de/anthology/2018.cikm_conference-2018.45
  - https://arxiv.org/pdf/1510.07545
  - https://khoury.northeastern.edu/home/vip/teach/DMcourse/6_graph_analysis/notes_slides/collab_filter/Aggrawal_recomm_systems/Recommender_Systems_An_Introduction_Chapter03_Content-based_recommendation.pdf
  - https://cs.fit.edu/~pkc/apweb/related/pazzani-mlj97.pdf
  - https://neo4j.com/graphgists/movie-recommendation-based-on-user-preferences-and-actor-weights/
  - https://link.springer.com/article/10.1007/s10489-005-5602-z
  - https://dl.acm.org/doi/10.1145/3477495.3531844
links:
  - affects: q-academic-novelty
  - affects: impl-interest-split
---
起案者の指示（2026-10-17）「興味ありの配り分けの先行研究をもっと調べて」。どれも検索結果と書誌で見ただけで、本文は読めていない（arxiv.org・出版社のページはこの環境から開けない）。

式 10–11 の部品と、いちばん近い先行研究:
- **1 件ぶんを手がかりに割って足す（合計 1）。** 内容に基づく推薦の利用者像を作る Rocchio の更新に近い。好きな品の平均を足し、嫌いな品の平均を引いて、品の特徴の重みで本人の像を作る（Jannach ほか『Recommender Systems: An Introduction』3 章の講義資料、関連の特許）。品のベクトルを長さで割れば、1 件の寄与の合計は 1 になる。
- **好きと分かっている手がかりに多め（1＋λ v⁰）。** 本人の今の像を使って、品の中のどの部品に注意を向けるかを決める注意（attention）の推薦に近い。
  - ACF（Chen ほか, SIGIR 2017）: 品の中の部品（画像の領域・動画のこま）への好みは分からない、という「部品の水準の暗黙さ」を、部品ごとの注意で扱う。
  - eRAN（arXiv 1908.05928）: 俳優・監督・ジャンルへの利用者ごとの注意を、そのまま理由として出す。
  - たぐりはこれを、学習なしの閉じた式で、本人の値の正の部分に比例させて行う。
- **公演の中で大きい人に多め（役の格 ι）。** 映画の推薦で、上映時間の割合で俳優に重みを付ける実装例がある（neo4j の例）。クレジットの順・役名つきかで重みを付ける研究は見つからなかった。
- **興味なしにもある手がかりは弱める（y/(y+n)）。** Rocchio の負の項や、好きな品と嫌いな品での特徴の出かたの比（Syskill & Webert の naive Bayes, Pazzani ほか 1997）に近い。
- **メモに名前があれば多め（η）。** 会話型推薦で、属性への反応から暗黙の好みを推し量る CRIF（SIGIR 2022）や、critiquing に近い。たぐりのメモは自由記述で、名前が書いてあるかどうかだけを見る。
- **「1 件のうち、どの部品が好かれた理由か」という見方そのもの。** multiple-instance learning（品＝部品の袋。好かれた袋には好かれた部品が少なくとも 1 つある）が同じ問題を扱う。web の目次ページの推薦に使った例がある（Applied Intelligence 2005）。
- **知識グラフの上で好みを広げる。** RippleNet（Wang ほか, CIKM 2018）は、クリックした品から、つながる実体（俳優・監督など）へ好みを広げる。学習ありで、たぐりの式 12（1 段広げる）にも近い。
- **「気になる」を消費とは別の信号として使うこと。** 候補の一覧に入れる操作（shortlist）を別の暗黙の信号として足すと、推薦の質がほぼ 2 倍になった（Schnabel ほか, WWW 2016）。たぐりの興味ありはこの種の信号にあたる。

見立て:
- 部品はどれも既存の考え方の言い換えである。
  - 割って足す → Rocchio・特徴の長さでの正規化。
  - 本人の好みに比例 → 注意・EM。
  - 興味なしとの比べ → 負の項・naive Bayes。
  - メモ → critiquing。
- 見つからなかったのは、次の条件をまとめて満たす例だけである。
  - 押すだけの 1 件を、役職つきのクレジット（出演の役名・アンサンブル・トメ）と種類のタグに、学習なしの閉じた式で配る。
  - 1 人あたり数十件のまばらな記録で、他の利用者のデータを使わない。
- 学術的な新しさとしては弱い。言えるとすれば、「学習データが無い状況で、注意の推薦の考え方を説明できる閉じた式に落とした、舞台のクレジットへの応用」である。
