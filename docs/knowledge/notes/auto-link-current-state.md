---
id: auto-link-current-state
type: finding
status: confirmed
date: 2026-10-13
title: 記録と公演ページの自動の結び付けは、いまは持ち主の手元でしか動かない
sources:
  - tools/credits/link_works.py
  - tools/taguri/serve.py
  - tools/taguri/app.py
  - tools/credits/fetch_credits.py
  - cloudflare/src/screens/diary.js
  - cloudflare/src/stage-search.js
  - tools/review/build_recommend_index.py
links:
  - raises: q-auto-link-past
  - affects: q-past-stage-catalogue
---
起案者の指示（2026-10-13）「いちいち結びつけなくても、過去の公演の情報紐づいてほしい」を受けて、コードを読んで確かめた（リポジトリのコードなので confirmed）。
自動で結び付ける仕組みは 3 つあるが、どれも一般の利用者には効いていない:
- `serve._enrich`（serve.py 1854-1890）: 記録を足したとき `link_works.find`（観た日が会期の中＋題名が合う）で CoRich の検索から探して結び付ける。**持ち主の手元だけ**（`self.public` なら何もしない）。しかも CoRich の検索は止めている（TAGURI_CORICH_SEARCH=off、WAF の 403）ので、今は手元でも見つからない
- `link_works.py`（毎週の run.py の 3 段目）: 同じ照合を持ち主の記録にまとめて掛ける。GitHub Actions には利用者の記録が無く、検索も止めているので何もしない。`UPDATE works SET stage_id=? WHERE work_key=?` に user_id の条件が無い（直すべき不具合）
- `app.demo_seed_links`: デモの見本の記録だけ、(日付, 題名) の完全一致で結び付ける（約 6 割）
Worker（D1）の `linkStageAction` は手で選んだ公演を書くだけで、自動の照合は無い。`works.js` は `auto_linked:false` 固定。
照合に使える過去の公演の手元の一覧:
- `candidates.jsonl`／D1 の `rec_stage`・`rec_gram`: これからの公演と、終わって 180 日以内の公演だけ。それより古い公演の題名の索引はどこにも無い
- `picked.jsonl`: 探してほしいと頼まれて見つかった公演（検索が止まっているので今は増えない）
- `credits.jsonl`・`linked.jsonl`: 持ち主のメールから作った過去の公演（dec-search-public-only により、他の利用者の照合には使わない）
- CoRich のサイトマップには約 14 万の公演ページの番号がある（corich-sitemap-stage-ids）が、題名・会期は載っていない ── 照合するには各ページを読む必要がある
照合の規則として再利用できるもの: `link_works.find`（会期の中＋題名）、`fetch_credits.rank_candidate`（題名・日付・会場で 0〜5 点）、`stage-search.js` の `searchIndex`（観た日に上演中のものを先に）。
分からないこと: 起案者の記録（2021〜2025 年が多い）のうち、180 日以内の一覧で結び付くものが何件あるかは数えていない（手元に利用者の記録が無い）。
