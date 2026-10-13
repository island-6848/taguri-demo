---
id: likert-diverging-bars
type: finding
status: unverified
date: 2026-10-13
title: 評定（◎○△×）の分布は、0 を中心に左右へ分ける積み上げ棒がよい ── 可視化の論文から
sources:
  - https://www.jstatsoft.org/v57/i05
  - https://ww2.amstat.org/meetings/proceedings/2012/data/assets/pdf/305235_74490.pdf
  - https://blog.datawrapper.de/divergingbars
  - https://info3312.infosci.cornell.edu/ae/graphical-perception-A.html
links:
  - supports: dec-verdict-diverging
---
起案者の指示（2026-10-13）「評価の分布、もうちょっといい可視化方法を可視化分野の論文読んで実装」。
- Heiberger, R. & Robbins, N. (2014). Design of Diverging Stacked Bar Charts for Likert Scales and Other Applications. Journal of Statistical Software 57(5), 1–32. doi:10.18637/jss.v057.i05。評定尺度の主な図として、肯定側と否定側を 0 の基線から左右に伸ばす「発散型の積み上げ棒」を勧める。主に比べるもの（肯定と否定の合計）が共通の基線 0 を持つから。先行は同じ著者の JSM 2011 の Plotting Likert and Other Rating Scales
- Cleveland, W. S. & McGill, R. (1984). Graphical Perception: Theory, Experimentation, and Application to the Development of Graphical Methods. JASA 79(387), 531–554。量の読み取りは、共通の目盛りの上の位置 > そろっていない目盛りの上の位置 > 長さ > 角度・傾き > 面積 の順に正確（Heer & Bostock 2010 が追試）
- 批判（Datawrapper のブログ）: 中立の答えを真ん中で割って左右に置く形は、両側の合計が読みにくい。中立は帯の外に置くのがよい
**一次情報は読めていない。** jstatsoft.org・ideas.repec.org はここから繋がらず（DNS が引けない）、上の内容は検索結果の抜き書きと講義資料の要約による。paper-trail（論文の足あと）の道具もこのセッションには無く、search_papers・add_papers で記録できなかった。
