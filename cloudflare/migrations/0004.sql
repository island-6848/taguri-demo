-- Sign-in with Firebase Authentication. Only the Firebase UID is stored: no
-- email address, name or photo. Recovery-code users can link a Firebase
-- account later (firebase_uid stays NULL until then).
--
-- users.recovery_hash is NOT NULL UNIQUE. Accounts created by Firebase sign-in
-- get 'firebase:<random>' there, which can never equal a SHA-256 hex digest,
-- so no recovery code can resolve to them.
ALTER TABLE users ADD COLUMN firebase_uid TEXT;
CREATE UNIQUE INDEX users_firebase_uid ON users(firebase_uid);
