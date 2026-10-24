-- ジャンルの名前「宝塚」を「宝塚歌劇団」にした（起案者の指示 2026-10-24「東京宝塚劇場と兵庫の宝塚劇場でやってる演目の
-- ジャンルは『宝塚歌劇団』として」、user_recommender.TAKARAZUKA_GENRE）。理由の ✕ で「使わない理由」にした鍵
-- （app_setting の kind_off、JSON の文字列 "#ジャンル<TAB>宝塚"）も新しい名前に移す。行は増えない（書き込みは当たった行だけ）。
-- JSON の中のタブは \t（バックスラッシュと t）で入っているので、SQL の文字列もそのまま \t と書く
UPDATE app_setting
   SET value = replace(value, '"#ジャンル\t宝塚"', '"#ジャンル\t宝塚歌劇団"')
 WHERE key = 'kind_off' AND instr(value, '"#ジャンル\t宝塚"') > 0;
