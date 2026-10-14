-- 0018: what the Worker needs besides the card itself, written by scripts/build_cards.py
-- with each card: the tour key (one row per production in 興味あり), the run dates
-- (order, months, the end of an owned stage), the title (an owned stage becomes a work
-- when it ends), and the texts favourite names are matched against
-- (recommend2.declared_hits, normalised with recommend2.nz):
--   gnz  the producing company        -> 団体・主催
--   blob title, company and credits   -> 人・作品・原作者
--   ws   subject words, one per line  -> 題材・原作者
--   synz the synopsis                 -> 題材・原作者
-- Matching runs in SQL (instr) so the Worker does not scan every stage itself.
ALTER TABLE rec_card ADD COLUMN title TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN tour TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN start TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN end TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN pref TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN gnz TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN blob TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN ws TEXT NOT NULL DEFAULT '';
ALTER TABLE rec_card ADD COLUMN synz TEXT NOT NULL DEFAULT '';
