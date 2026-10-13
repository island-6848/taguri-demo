---
id: lit-scale-change
type: finding
status: confirmed
date: 2026-10-13
title: 評価の段階を途中で変えたときの扱い：直接の研究は少なく、段階どうしを決まった式で写すのは最善ではないとされる
sources:
  - https://cris.bgu.ac.il/en/publications/how-scales-influence-user-rating-behaviour-in-recommender-systems-2/
  - https://www.springerprofessional.de/towards-a-customization-of-rating-scales-in-adaptive-systems/3302784
  - https://measuringu.com/do-people-use-all-response-options/
  - https://metatoc.com/papers/118081-binary-binning-examining-the-mapping-between-continuous-and-binary-review-scales
  - https://brainstation.io/magazine/netflix-officially-replaces-five-star-rating-system-with-thumbs-up-or-down
links:
  - affects: q-user-chosen-scale
---
Cena・Gena・Grillo・Kuflik・Vernero・Wecker（Behaviour & Information Technology 2017）: 3 つの領域の実験で、段階は中立ではなく、違う段階どうしを決まった数式で写すのは最善ではない。線形の写し方が使える条件も示している（条件の中身は原文未確認）。Cena・Vernero（2010）は 3 段の正規化を提案。Dawes（International Journal of Market Research 2008）: 5・7・10 段階の回答は 10 段階に引き伸ばすと平均・ばらつき・形がほぼ同じ（アンケート）。Binary Binning（Journal of Behavioral Decision Making 2026）: 5 段階を 2 択に分けると、同じ商品が高く見える（要約のみ）。Netflix は 2017 年に 5 つ星から 2 択に変え、古い星も推薦に使い続けると発表したが、写し方は公表していない（報道のみ）。利用者 1 人が途中で段階を変えた場合を扱った研究は見つけていない。
