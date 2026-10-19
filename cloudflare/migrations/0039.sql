-- 所属の表（起案者の指示 2026-10-19「劇団名が（）で人名の後ろについてる人とかは、ツリーの親が劇団で子が各個人」
-- 「所属の表をつくって」、dec-affiliation-table）。出演欄の「名前（所属）」を scripts/build_recommend_index.py が
-- measure_nets.affiliations で読み、推薦の索引と同じ差分の配送（ver = 'live'）で入れる。
-- 所属は時期で変わるので、公演ごとに「この公演ではこう書かれていた」を 1 行にする（start = その公演の初日）。
-- kind は目安（劇団・事務所・グループ・空）。木の親（所属）から子（人）を引くのは主キーの前の方（ver, affil）で足りる。
-- 人から所属を引く索引は、Worker が読むようになったときに足す（いまは書き込みを増やさない）
CREATE TABLE rec_affil (
 ver TEXT NOT NULL, affil TEXT NOT NULL, person TEXT NOT NULL, stage_id TEXT NOT NULL,
 start TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(ver, affil, person, stage_id)
);
