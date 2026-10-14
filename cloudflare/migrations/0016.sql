-- Tour grouping (user_recommender.tour_key): venues of one tour share this key
-- (same title, producer and set of credits), so the Worker shows one slot per
-- production with its other venues, as the Python screen does (collapse_tours).
-- Written by scripts/build_recommend_index.py; '' until the index is rebuilt.
ALTER TABLE rec_stage ADD COLUMN tour TEXT NOT NULL DEFAULT '';
