---
id: q-theme-preference
type: question
status: open
date: 2026-10-13
title: 観劇でジャンルにあたる手がかり（テーマ語・劇団・会場など）をどう取り、本人の好みとして足すか
links:
  - affects: comp-recommender
---
映画ではジャンルの好みが効いた（eval-genre-preference）。観劇の公演情報にはテーマ語（themes）・劇団・会場・料金がある。テーマ語の付き方がジャンルよりばらつくかは未確認。足す場合は docs/research/reco-without-reputation.md の優先順位 1・2 の形（本人基準で平均し、記録が増えるほど重く）。

定義の案（2026-10-13）: 公式のジャンル分けが見つからないので（theatre-genre-sources）、公演情報から機械的に決まるものを使う。公演の形（題名の「ミュージカル」「朗読劇」、作曲・歌唱指導の有無など）、原作・翻訳の有無（クレジットの欄）、劇団・主催、会場の規模、料金帯。あらすじの題材は戯曲デジタルアーカイブ由来の項目（net_c_axes.py）で推定できるが、推定の誤りと語の重なりにくさ（theme-words-sparse-past）に注意。
