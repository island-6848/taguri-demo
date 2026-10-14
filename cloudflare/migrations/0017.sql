-- 0017: recommendation cards rendered once a day by the Python screen
-- (scripts/build_cards.py, render_recommend.ticket). The Worker's recommend
-- screen fills the rank, the user's reasons and the poster into the markers.
-- Versioned like stage_label: rec_meta 'rec_card' names the current version.
CREATE TABLE rec_card (
 ver TEXT NOT NULL, stage_id TEXT NOT NULL, html TEXT NOT NULL,
 PRIMARY KEY(ver, stage_id)
);
