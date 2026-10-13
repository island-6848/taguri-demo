-- Passkeys (WebAuthn) for people who do not want Google sign-in.
-- Only public keys are stored; private keys never leave the user's device.
CREATE TABLE passkeys (
 id TEXT PRIMARY KEY,                          -- credential ID (base64url)
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 user_handle TEXT NOT NULL,                    -- WebAuthn user.id given to the authenticator
 public_key TEXT NOT NULL,                     -- COSE public key (base64url)
 counter INTEGER NOT NULL DEFAULT 0,           -- signature counter, to detect cloned keys
 transports TEXT NOT NULL DEFAULT '[]',
 backed_up INTEGER NOT NULL DEFAULT 0,         -- synced passkey (iCloud, Google Password Manager…)
 created_at INTEGER NOT NULL,
 last_used_at INTEGER
);
CREATE INDEX passkeys_user ON passkeys(user_id);
CREATE TRIGGER passkey_limit BEFORE INSERT ON passkeys
WHEN (SELECT count(*) FROM passkeys WHERE user_id=NEW.user_id)>=10
BEGIN SELECT RAISE(ABORT,'passkey limit'); END;
-- One-time challenges. Consumed (deleted) on first use, valid for 5 minutes.
CREATE TABLE webauthn_challenges (
 id TEXT PRIMARY KEY,
 challenge TEXT NOT NULL,
 purpose TEXT NOT NULL CHECK(purpose IN ('register','login')),
 user_id TEXT,                                 -- set when adding a passkey to a signed-in account
 user_handle TEXT,                             -- for registration
 expires_at INTEGER NOT NULL
);
CREATE INDEX webauthn_challenge_expiry ON webauthn_challenges(expires_at);
