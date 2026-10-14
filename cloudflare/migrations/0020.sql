-- 0020: the original demo's cap of 100 users (0001.sql) would refuse every sign-up
-- after the 100th. New accounts are bounded per day instead (NEW_ACCOUNTS_PER_DAY,
-- src/rate-limit.js), within the free tier.
DROP TRIGGER IF EXISTS account_limit;
