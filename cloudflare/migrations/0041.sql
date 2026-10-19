-- 所属の表を人から引く索引（dec-affil-reco）。裏の答え合わせが、評価した公演の出演者の劇団を読む
-- （recommend.d1Access.affilMembers の 1 つめの問い合わせ）。足す書き込みは rec_affil の 1 行につき 1
CREATE INDEX rec_affil_person ON rec_affil(ver, person);
