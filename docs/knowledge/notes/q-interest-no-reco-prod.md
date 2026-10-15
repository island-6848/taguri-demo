---
id: q-interest-no-reco-prod
type: question
status: answered
date: 2026-10-15
title: 本番で「興味ありが何件もあるのに、おすすめが出ない」のはなぜか
sources:
  - https://api.github.com/repos/island-6848/taguri-demo/commits/655221b/check-runs?filter=all
links:
  - affects: impl-interest-seed
---
起案者の指摘（2026-10-15、記録の取り込みのセッション経由）。分かったこと:
- 配信はされている: 興味ありの種を入れた master の 655221b 以降、各コミットに Workers Builds の成功が 1 回ずつある（filter=all。失敗はブランチのプレビューの組み立て〔workers-builds-branch-fail〕）
- 考えられる原因（コードから）: (a) 興味ありの公演の人物が分からない（索引に無く、一覧の出演欄も空）、(b) その人たちの「これからの、まだ始まっていない」公演が索引に無い（始まっている公演はおすすめに出さない）、(c) その人がお気に入りに登録した名前だと、種から外れ（skip）、その人の公演は「お気に入り」の方に出る、(d) 効かせ方で「出演」を「効かせない」にしている
- 見分け方: /api/screen/recommend の JSON に diag（rated・rated_linked・interest・interest_with_people・favourite_seeds・ranked・after_answered）を足した。起案者にログインしたブラウザで https://app.taguri.workers.dev/api/screen/recommend を開いて diag を見てもらう。interest_with_people が 0 なら (a)、ranked が 0 なら (b)(c)(d)、after_answered が 0 なら答え済み・お気に入り・出さない語で全部外れている
