-- Tour grouping (user_recommender.tour_key): venues of one tour share this key
-- (same title, producer and set of credits), so the Worker shows one slot per
-- production with its other venues, as the Python screen does (collapse_tours).
-- Written by scripts/build_recommend_index.py; '' until the index is rebuilt.
ALTER TABLE rec_stage ADD COLUMN tour TEXT NOT NULL DEFAULT '';
-- Favourite troupes / producers (団体・主催) are matched against the producing
-- company as recommend2.nz normalises it (NFKC, no spaces, lower case).
ALTER TABLE rec_stage ADD COLUMN gkey TEXT NOT NULL DEFAULT '';
