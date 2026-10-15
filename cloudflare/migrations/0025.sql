-- 興味ありを押した画面（reaction.source）の付け直し（起案者の指示 2026-10-15「既存の3件も開幕リマインドからの追加にして」）。
-- 押した画面を 'reminder'・'search' として残すようになったのは PR #28（2026-10-15 23:39 UTC マージ）から。それより前の
-- 興味ありは source が 'screen'（ツアーのほかの会場は 'screen_tour'）で、どの画面か分からない。
-- 本番では推薦の索引が届いておらず（rec_meta 'current' が無い）、おすすめの画面にはカードが出ていなかった。
-- そのため、それまでの興味ありは開幕リマインドか探すから押したものになる。起案者の 3 件は開幕リマインドからなので、
-- 開幕リマインドからとして付け直す。#28 より後に 'screen' で入った行はおすすめから押したものなので触らない。
-- （前のコードは、理由を書くと同じ行の updated_at と source も書き換えていたので、区切りは #28 のマージの時刻にする）
UPDATE reaction SET source = CASE WHEN source = 'screen_tour' THEN 'reminder_tour' ELSE 'reminder' END
 WHERE interest = 1 AND source IN ('screen', 'screen_tour') AND updated_at < '2026-10-15T23:39:00';
