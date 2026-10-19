-- 所属の表記ゆれを束ねる（起案者の指示 2026-10-19「表記ゆれをたばねる」、dec-affiliation-table）。
-- rec_affil.affil は束の名前（いちばん多い書き方）になり、その公演に書かれたままの名前を written に残す。
-- 束ね方は measure_nets.affil_key（記号・空白・大小文字・会社の種類・頭の「劇団」などを落とす）
ALTER TABLE rec_affil ADD COLUMN written TEXT NOT NULL DEFAULT '';
