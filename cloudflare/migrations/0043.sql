-- 形式の札「朗読」を「朗読劇」に改めた（起案者の指示 2026-10-19「『朗読劇』に名前変えて」、user_recommender._FORM_TITLE）。
-- 「この種類を理由に出さない」（app_setting の kind_off、"#形式\t朗読" の JSON 配列）で外していた人は、新しい名前でも外れたままにする。
-- 索引（rec_people・rec_credit）の札は、次の取得で作り直したときに差分で入れ替わる。書き込みは kind_off に「朗読」がある人の 1 行だけ
UPDATE app_setting SET value=replace(value, '"#形式\t朗読"', '"#形式\t朗読劇"')
WHERE key='kind_off' AND instr(value, '"#形式\t朗読"') > 0;
