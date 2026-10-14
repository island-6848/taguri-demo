-- Free-tier counters kept by the Worker (docs/free-tier-budget.md).
-- `r2_get:<YYYY-MM>`: R2 reads (Class B operations) for /img/<file>, counted by
-- sampling in worker.js r2ReadAllowed. R2 bills reads beyond the free 10 million
-- a month, so the Worker stops reading R2 at R2_READS_CAP (3 million) and the
-- crawler's Free-tier check reports this table every day.
CREATE TABLE usage (k TEXT PRIMARY KEY, n INTEGER NOT NULL DEFAULT 0);
