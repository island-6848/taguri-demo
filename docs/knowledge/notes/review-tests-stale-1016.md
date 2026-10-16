---
id: review-tests-stale-1016
type: finding
status: confirmed
date: 2026-10-16
title: tools/review の 3 つの検査が落ちていたのは、検査のほうが古かった（仮の名前「作り手N」・画面の作り替え・持ち主の手元のデータ）。1 か所だけ本物のコードの規則違反（hook.py の splitlines）
sources:
  - tools/review/test_measure_nets.py
  - tools/review/test_interest_roster.py
  - tools/review/test_rate_performances.py
  - tools/review/measure_nets.py
  - tools/taguri/app.py
  - tools/knowledge/hook.py
links:
  - affects: dec-credit-part-names
  - raises: q-role-prefix-bare-saku
---
master（5b4de56）と 51173cb の両方で同じ件数落ちる。原作の国の変更（5b4de56）とも、コロンの後ろだけ読む変更（a09e2a3、dec-credit-part-names）とも関係ない。リポジトリの最初のコミット（e203d51）からある `_ROLE_PREFIX`（行頭の「作」「演出」などを剥がす）は変わっていない。

**test_measure_nets（1 件）と test_interest_roster（3 件）── 検査の仮の名前が古い。** 人名を「作り手14」「作り手24」のような仮の名前に置き換えたとき、行頭の「作」が役職として剥がれて「り手14」になった。3 件の失敗（「り手14」が入る・同じ人が 3 回数えられない（0）・既存の名簿に足されない（(3, 2.0) のまま））は、どれもこの 1 つが原因。検査の仮の名前を「俳優14」「俳優24」「俳優25」に変えて、10 件・11 件すべて通る。起案者の指示（2026-08-26 の「4 人書いたのに 3 人」、「観ればよかった＝興味あり」）が求める動きは、コードのとおりで変えていない。

**test_rate_performances ── 持ち主の手元のデータが無いと、何も試さずに失敗していた。** `data/tickets/performances.jsonl`（購入確認メールから作る）は .gitignore の `data/` にあり、新しい作業環境や CI には無い。作った材料で動かすと、残りの失敗は次のとおりだった。
- 検査が古い（画面を変えた後に検査を直していない）:
  - 段の帯（`.sub`）の CSS 3 件。起案者の指摘で 2026-08-25 に帯を全画面から消している（`APP_CSS` のコメント）。「戻していない」ことを確かめる 1 件に置き換えた
  - 「やはり観た」の戻す口。起案者の指示（2026-08-26）で日記帳から「設定」へ移している（`page_works` の説明・`_skipped_html`）。設定に出て、日記帳に出ないことを確かめるようにした
  - 候補の欄の説明の文言。「名簿に入ります」が「おすすめの材料に入ってしまいます」に言い換わっていた。意味は同じなので、検査を今の文に合わせた
- 持ち主の手元にしか無いファイルが要るもの（館の座標・区の境界・推薦の控え・観た公演のクレジットの控え・購入確認メールの本文）: 材料が無いときは名前を出して飛ばす（8 件）
- **コードのほうが規則に反していた 1 件:** `tools/knowledge/hook.py` が JSONL を `splitlines()` で読んでいた。U+2028 で 1 件が割れる（検査 check_jsonl_reading の規則）。`split("\n")` に直した

作った材料（`tools/review/fixtures/performances.jsonl`、題名・劇場は仮の名前）で 78 件通り、8 件飛ばす。持ち主の端末では今までどおり本物の控えを読む。持ち主のデータでの結果は、この作業環境からは確かめていない。
