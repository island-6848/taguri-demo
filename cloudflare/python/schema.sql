-- Prototype only: not included in production migrations until runtime tests pass.
CREATE TABLE legacy_accounts (
 user_id TEXT PRIMARY KEY,
 revision INTEGER NOT NULL DEFAULT 0,
 write_token TEXT NOT NULL DEFAULT ''
);
CREATE TABLE legacy_schemas (
 user_id TEXT NOT NULL REFERENCES legacy_accounts(user_id) ON DELETE CASCADE,
 table_name TEXT NOT NULL,
 schema_sql TEXT NOT NULL,
 columns_json TEXT NOT NULL,
 primary_key_json TEXT NOT NULL,
 PRIMARY KEY(user_id,table_name)
);
CREATE TABLE legacy_rows (
 user_id TEXT NOT NULL REFERENCES legacy_accounts(user_id) ON DELETE CASCADE,
 table_name TEXT NOT NULL,
 row_key TEXT NOT NULL,
 row_json TEXT NOT NULL,
 PRIMARY KEY(user_id,table_name,row_key)
);
