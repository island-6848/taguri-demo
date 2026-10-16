-- 劇場制覇マップの分母（起案者の指示 2026-10-16「同じ建物の別ホールは分けたほうがいいな。…組み込んで」、
-- mock-theater-conquest）。取得した公演（これからの公演と 2019 年以降の過去の公演）に 2 回以上出てきた会場を、
-- 名前を揃えて（NFKC・空白を除く）1 行ずつ。同じ建物のホールはまとめない。「配信」「某所」のような会場でないものは除く。
-- 県ごとの数は rec_meta 'venue_counts'（JSON）に置き、画面はこの表を本人が行った会場の分だけ引く。
-- 1 行は行＋主キーの索引で 2 書き込み。変わった行だけ送る（deliver_catalogue.py venue_census）。
CREATE TABLE venue_census (
  venue TEXT PRIMARY KEY,
  pref TEXT NOT NULL
);
