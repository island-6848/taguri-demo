---
id: dec-reco-nightly
type: decision
status: adopted
date: 2026-10-24
title: おすすめは取得の夜の段で全員分を前もって作り、Worker は古い控えを計算し直さずに出す（答えた公演だけ外す。順位は毎朝変わる）
sources:
  - cloudflare/scripts/nightly_reco.mjs
  - cloudflare/src/screens/recommend.js
  - tools/taguri/deploy/github-actions/catalog.yml
  - cloudflare/test/nightly-reco.test.js
  - cloudflare/test/reco-stale.test.js
links:
  - answers: q-reco-cpu-structure
  - depends_on: f-reco-recompute-cpu-1021
  - depends_on: workers-free-cpu-10ms
---
起案者の決定（2026-10-24）「おすすめの計算し直しは A で進めて」。A は「取得の非公開リポジトリの定期実行で全員分を計算し、D1 に入れる。Worker は読むだけ。評価を変えても順位は翌日」（起案者に示した案。利用者の記録が非公開の定期実行を通ることも含めて選んだ）。

理由: 本番の大きさでは、おすすめの計算し直しが評価 10 件で 17 ms・40 件で 37 ms・100 件で 59 ms あり、Workers Free の CPU 10 ms を越えて止められる（「いまは一時的に止めています」の 503 の見込みの原因の一つ）〔f-reco-recompute-cpu-1021〕。どれか 1 か所を軽くしても届かない。

作り:
- **Worker**（screens/recommend.js の rankedGroups）: 控えの印が今と同じなら今までどおり。違っても計算し直さず、控えを作ったあとに答えた公演（reaction）と観劇記録に入れた公演（works.stage_id）を束ごと外して出す（staleGroups）。計算するのは、控えが 1 行も無い人（登録した直後）と、夜の段（ctx.recompute）だけ。画面には「評価や答えは、翌朝のおすすめの順位に反映されます（答えた公演はすぐ外れます）」を 1 行出す
- **控えを消していた所**（記録・答え・お気に入り・効かせ方・作品の分け方・観ていない出演者・感想の AI 読み取りの切り替えと結果）は、DELETE をやめて印を空にする（UPDATE rec_cache SET stamp=''）。消すと、次に開いたとき重い計算に戻るため
- **夜の段**（scripts/nightly_reco.mjs、taguri-crawler の Catalog の「過去の公演を D1 に入れる」段のあと）: おすすめの計算が読む表（TABLES）を D1 の REST API の SELECT で rowid 順に区切って読み、手元のメモリの SQLite に写す（トリガーは外す。写すときに rec_rev が進むと印が本番と違うため）。Worker と同じ rankedGroups を全員に recompute で回し、印か中身が変わった人の rec_cache だけを書き戻す（中身は SQL に埋めず引数で送る。D1 の文の長さの上限 100 KB のため）。読み始めより後に Worker が作り直した控えは上書きしない
- **試験**: 計算の中身を確かめる今までの試験は env.RECO_INLINE='1'（試験の harness だけ）で前のとおりその場で計算する。古い控えを出す動き（reco-stale.test.js）と、夜の段の控えを Worker がそのまま使い、その場で計算したのと同じ並びになること（nightly-reco.test.js）を足した

量（本番の大きさの索引で 20 人・各 40 件を手元で回した）: 計算 0.8 秒、読んだ行 約 6.7 万（本番は catalogue と過去の公演が多いので 10 万行ほどの見込み）。300 人で計算 12 秒ほど。D1 の 1 日 500 万行・書き 10 万行の中。40 万行を越えたら書き戻さずにやめる。

分かっていないこと: 本番の D1 の REST API での実際の rows_read と時間（初回の実行で確かめる）。D1 の export は書き出しのあいだ D1 が答えなくなるので使わない（Cloudflare の API の説明。検索結果の引用で確かめた）。控えの backup_d1.py は export を使っているので、同じ問題がある〔q-backup-export-blocks〕。
