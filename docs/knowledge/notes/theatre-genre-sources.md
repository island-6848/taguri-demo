---
id: theatre-genre-sources
type: finding
status: unverified
date: 2026-10-13
title: 舞台の公演に業界共通の公式のジャンル分けは見つからない。近いものは日本劇作家協会「戯曲デジタルアーカイブ」のジャンル（戯曲向け）
sources:
  - https://www.j-cast.com/2021/03/20407358.html?p=all
  - https://current.ndl.go.jp/car/43435
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/net_c_axes.py
links:
  - affects: q-theme-preference
---
日本劇作家協会の戯曲デジタルアーカイブ（2021 年公開、戯曲 500 本超）は作品名・上演時間・人数・ジャンルで絞り込める（J-CAST・国立国会図書館カレントアウェアネスの記事による。項目の一覧はこの環境から確かめられない）。リポジトリの tools/review/net_c_axes.py・tools/credits/extract_emotion_llm.py は「34 ジャンル」から事実・感情の項目を借りて、あらすじから推定する仕組みを持つ（持ち主が以前作ったもの）。取得元（CoRich）の公演ページに公式のジャンル欄があるかは確かめられず、検索結果では「大・中劇場」のような会場の区分が見えた。戯曲のジャンルは公演（同じ戯曲の別の上演）のジャンルとは一致しない。
