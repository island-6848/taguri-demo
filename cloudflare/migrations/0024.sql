-- 劇場名 → 都道府県（起案者の指摘 2026-10-15「都道府県がわからない作品しかない」）。
-- 一覧（catalogue）には都道府県が無い（convert_catalogue が候補の pref を metadata に残していなかった）。
-- 一覧を全部書き直すと 1 日の書き込み予算を食うので、劇場ごとに 1 行（数百行）を別に持ち、
-- 画面は catalogue.venue で引く（screens/fallback.js・reminder.js）。毎日の取得が、変わった行だけ書く
-- （scripts/deliver_catalogue.py）。同じ劇場名で都道府県が 1 つに決まるものだけを入れる。
CREATE TABLE venue_pref (
 venue TEXT PRIMARY KEY,
 pref TEXT NOT NULL
);
