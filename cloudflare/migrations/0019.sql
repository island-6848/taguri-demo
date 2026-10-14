-- 0019: 開幕リマインド reads the stages opening in the next two weeks by their first day.
CREATE INDEX rec_stage_start ON rec_stage(ver, start);
