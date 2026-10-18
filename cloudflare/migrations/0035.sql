-- 推薦の材料が変わった合図（issue #189）。前は件数と更新時刻の最大（秒）から控え（rec_cache）の印を作っていたので、
-- 同じ秒の付け直し（◎ を × に）では印が変わらず、古いおすすめが残った。材料の表に書くたびに、同じ文の中で
-- users.rec_rev を 1 進める（トリガーなので、どの画面・API から書いても漏れない）。works だけは works_rev も進め、
-- 裏の答え合わせ（評価だけで決まる、gateKey）の使い回しはそちらで見る。
-- 書き込みは材料の表への 1 回の書き込みにつき users の 1 行（索引の無い列）。
ALTER TABLE users ADD COLUMN rec_rev INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN works_rev INTEGER NOT NULL DEFAULT 0;
CREATE TRIGGER rec_rev_works_insert AFTER INSERT ON works BEGIN UPDATE users SET rec_rev=rec_rev+1, works_rev=works_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_works_update AFTER UPDATE ON works BEGIN UPDATE users SET rec_rev=rec_rev+1, works_rev=works_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_works_delete AFTER DELETE ON works BEGIN UPDATE users SET rec_rev=rec_rev+1, works_rev=works_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_hand_credits_insert AFTER INSERT ON hand_credits BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_hand_credits_update AFTER UPDATE ON hand_credits BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_hand_credits_delete AFTER DELETE ON hand_credits BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_reaction_insert AFTER INSERT ON reaction BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_reaction_update AFTER UPDATE ON reaction BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_reaction_delete AFTER DELETE ON reaction BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_favourites_insert AFTER INSERT ON favourites BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_favourites_update AFTER UPDATE ON favourites BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_favourites_delete AFTER DELETE ON favourites BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_merges_insert AFTER INSERT ON merges BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_merges_update AFTER UPDATE ON merges BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_merges_delete AFTER DELETE ON merges BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_excluded_insert AFTER INSERT ON excluded BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_excluded_update AFTER UPDATE ON excluded BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_excluded_delete AFTER DELETE ON excluded BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_app_setting_insert AFTER INSERT ON app_setting BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_app_setting_update AFTER UPDATE ON app_setting BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_app_setting_delete AFTER DELETE ON app_setting BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
CREATE TRIGGER rec_rev_rank_weight_insert AFTER INSERT ON rank_weight BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_rank_weight_update AFTER UPDATE ON rank_weight BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=NEW.user_id; END;
CREATE TRIGGER rec_rev_rank_weight_delete AFTER DELETE ON rank_weight BEGIN UPDATE users SET rec_rev=rec_rev+1 WHERE id=OLD.user_id; END;
