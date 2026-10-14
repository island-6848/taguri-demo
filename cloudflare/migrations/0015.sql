-- 気になった所 (q-rating-aspects): what a rating marks as the trouble
-- (story, direction, acting, music, dance, design, price, venue), as
-- comma-separated codes of user_recommender.ASPECTS. A low rating then lands
-- mainly on the roles the aspects point at. '' = none marked (as before).
ALTER TABLE records ADD COLUMN aspects TEXT NOT NULL DEFAULT '';
ALTER TABLE works ADD COLUMN aspects TEXT NOT NULL DEFAULT '';
