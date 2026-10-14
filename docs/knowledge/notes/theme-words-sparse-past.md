---
id: theme-words-sparse-past
type: finding
status: unverified
date: 2026-10-13
title: 持ち主の過去の検証では、あらすじのテーマ語は作品間で重なりにくく、一般的な語（家族・恋愛・コメディ・友情）に偏っていた
sources:
  - https://github.com/island-6848/taguri-demo/blob/master/tools/review/recommend2.py
links:
  - affects: q-theme-preference
---
recommend2.py の注記（検証 022）: 学習側 31 作品に出た 95 語のうち 3 作品以上に出るのは 9 語だけ。n=1 の結果なので効果の根拠にはしないが、テーマ語をジャンルの代わりに使うときに「語が重ならず点が付かない」おそれを示す。
