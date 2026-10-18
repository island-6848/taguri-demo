-- 評価を付けた（直した）時刻（issue #112）。updated_at は感想・日付などの編集でも進むので、裏の答え合わせ
-- （reco-gate.chooseVariant）の「評価した順」に使うと、感想を直しただけで順が変わり、選ぶ方式まで変わった。
-- 評価（verdict）と詳細（aspects）を書いたときだけ進める（screens/rate.js）。いまある評価は updated_at から始める
-- （書き込みは評価のある記録の行数だけ、1 回きり）。
ALTER TABLE works ADD COLUMN rated_at TEXT;
UPDATE works SET rated_at=updated_at WHERE verdict IS NOT NULL AND verdict<>'';
