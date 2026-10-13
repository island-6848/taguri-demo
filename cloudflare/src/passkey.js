// Passkey (WebAuthn) sign-in. Verification is done by @simplewebauthn/server;
// this module only decides who may register/sign in and keeps the records.
//
// - Sign up with a passkey alone (no email, no Google). A recovery code is
//   issued once as the backup for a lost device, as in the original design.
// - A signed-in account (Google, email link or recovery code) can add passkeys.
// - User verification (biometrics / device PIN) is required.
// - Challenges are one-time (deleted when used) and expire after 5 minutes.
// - The signature counter is checked by the library to detect cloned keys.
import {generateRegistrationOptions, verifyRegistrationResponse,
        generateAuthenticationOptions, verifyAuthenticationResponse} from '@simplewebauthn/server';
import {isoBase64URL} from '@simplewebauthn/server/helpers';

const CHALLENGE_TTL = 300;
const MAX_CHALLENGES = 1000;     // pending challenges overall; bounds unauthenticated writes
const MAX_RESPONSE = 16384;      // bytes of a WebAuthn response we accept

export function passkeyRoutes(h) {
  const {fail, json, token, hash, now} = h;
  const rp = (request, env) => {
    const url = new URL(request.url);
    return {rpID: env.WEBAUTHN_RP_ID || url.hostname, origin: url.origin};
  };

  async function newChallenge(db, purpose, challenge, extra = {}) {
    await db.prepare('DELETE FROM webauthn_challenges WHERE expires_at<=?').bind(now()).run();
    const pending = (await db.prepare('SELECT count(*) AS n FROM webauthn_challenges').first()).n;
    if (pending >= MAX_CHALLENGES) fail(429, '混み合っています。少し待ってから試してください。');
    const id = token();
    await db.prepare('INSERT INTO webauthn_challenges(id,challenge,purpose,user_id,user_handle,expires_at) VALUES(?,?,?,?,?,?)')
      .bind(id, challenge, purpose, extra.user_id ?? null, extra.user_handle ?? null, now() + CHALLENGE_TTL).run();
    return id;
  }
  // One-time: the row is deleted whether or not the response then verifies.
  async function takeChallenge(db, id, purpose) {
    if (typeof id !== 'string' || !/^[a-f0-9]{64}$/.test(id)) fail(400, 'もう一度最初からやり直してください。');
    const row = await db.prepare('DELETE FROM webauthn_challenges WHERE id=? AND purpose=? RETURNING challenge,user_id,user_handle,expires_at').bind(id, purpose).first();
    if (!row || row.expires_at <= now()) fail(400, '時間切れです。もう一度最初からやり直してください。');
    return row;
  }
  function credentialResponse(value) {
    if (!value || typeof value !== 'object' || typeof value.id !== 'string' || JSON.stringify(value).length > MAX_RESPONSE) fail(400, 'パスキーの応答を読み取れませんでした。');
    return value;
  }
  const rejected = () => fail(401, 'パスキーを確認できませんでした。もう一度お試しください。');

  return {
    // POST /api/auth/passkey/register/options
    async registerOptions(request, env) {
      const {rpID} = rp(request, env);
      const uid = await h.currentUser(request, env.DB);
      if (!uid && env.ALLOW_REGISTRATION !== 'true') fail(503, '新規登録を一時停止しています。');
      const existing = uid ? (await env.DB.prepare('SELECT id,user_handle,transports FROM passkeys WHERE user_id=?').bind(uid).all()).results : [];
      if (existing.length >= 10) fail(409, 'パスキーは10個まで登録できます。');
      const userHandle = existing[0]?.user_handle ?? isoBase64URL.fromBuffer(crypto.getRandomValues(new Uint8Array(32)));
      const options = await generateRegistrationOptions({
        rpName: 'たぐり', rpID, userName: 'たぐり', userDisplayName: 'たぐりの記録',
        userID: isoBase64URL.toBuffer(userHandle), attestationType: 'none',
        authenticatorSelection: {residentKey: 'required', userVerification: 'required'},
        excludeCredentials: existing.map(p => ({id: p.id, transports: JSON.parse(p.transports)})),
        timeout: CHALLENGE_TTL * 1000,
      });
      const challenge_id = await newChallenge(env.DB, 'register', options.challenge, {user_id: uid, user_handle: userHandle});
      return json({challenge_id, options});
    },

    // POST /api/auth/passkey/register/verify
    async registerVerify(request, env) {
      const input = await h.body(request);
      const response = credentialResponse(input.response);
      const ch = await takeChallenge(env.DB, input.challenge_id, 'register');
      const {rpID, origin} = rp(request, env);
      const uid = await h.currentUser(request, env.DB);
      // Adding to an account: the same account must still be signed in.
      if (ch.user_id && ch.user_id !== uid) fail(401, 'ログインし直してから、もう一度追加してください。');
      if (!ch.user_id && env.ALLOW_REGISTRATION !== 'true') fail(503, '新規登録を一時停止しています。');
      let result;
      try {
        result = await verifyRegistrationResponse({response, expectedChallenge: ch.challenge, expectedOrigin: origin,
          expectedRPID: rpID, requireUserVerification: true});
      } catch { rejected(); }
      if (!result?.verified) rejected();
      const {credential, credentialBackedUp} = result.registrationInfo;
      const insert = owner => env.DB.prepare('INSERT INTO passkeys(id,user_id,user_handle,public_key,counter,transports,backed_up,created_at) VALUES(?,?,?,?,?,?,?,?)')
        .bind(credential.id, owner, ch.user_handle, isoBase64URL.fromBuffer(credential.publicKey), credential.counter,
              JSON.stringify(credential.transports ?? []), credentialBackedUp ? 1 : 0, now());
      if (await env.DB.prepare('SELECT 1 FROM passkeys WHERE id=?').bind(credential.id).first()) fail(409, 'このパスキーは登録済みです。');
      if (ch.user_id) {
        await env.DB.batch([insert(ch.user_id)]);
        return json({added: true});
      }
      // New account with this passkey. The recovery code is shown once and
      // only its hash is kept, as for recovery-code accounts.
      const newUid = crypto.randomUUID(), recovery = token();
      const session = await h.startSession(env.DB, newUid, [
        env.DB.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').bind(newUid, await hash(recovery), now()),
        insert(newUid)], h.sessionCookie(request));
      return json({created: true, recovery_code: recovery}, 200, {'Set-Cookie': h.cookie(session)});
    },

    // POST /api/auth/passkey/login/options
    async loginOptions(request, env) {
      const {rpID} = rp(request, env);
      // Discoverable credentials: no account name is asked for or revealed.
      const options = await generateAuthenticationOptions({rpID, userVerification: 'required', timeout: CHALLENGE_TTL * 1000});
      const challenge_id = await newChallenge(env.DB, 'login', options.challenge);
      return json({challenge_id, options});
    },

    // POST /api/auth/passkey/login/verify
    async loginVerify(request, env) {
      const input = await h.body(request);
      const response = credentialResponse(input.response);
      const ch = await takeChallenge(env.DB, input.challenge_id, 'login');
      const {rpID, origin} = rp(request, env);
      const key = await env.DB.prepare('SELECT id,user_id,user_handle,public_key,counter,transports FROM passkeys WHERE id=?').bind(response.id).first();
      if (!key) rejected();
      // The authenticator's user handle, when sent, must be the one we issued.
      const handle = response.response?.userHandle;
      if (handle && handle !== key.user_handle) rejected();
      let result;
      try {
        result = await verifyAuthenticationResponse({response, expectedChallenge: ch.challenge, expectedOrigin: origin,
          expectedRPID: rpID, requireUserVerification: true,
          credential: {id: key.id, publicKey: isoBase64URL.toBuffer(key.public_key), counter: key.counter, transports: JSON.parse(key.transports)}});
      } catch { rejected(); }
      if (!result?.verified) rejected();
      const session = await h.startSession(env.DB, key.user_id, [
        env.DB.prepare('UPDATE passkeys SET counter=?,last_used_at=? WHERE id=?').bind(result.authenticationInfo.newCounter, now(), key.id)],
        h.sessionCookie(request));
      return json({ok: true}, 200, {'Set-Cookie': h.cookie(session)});
    },

    // GET /api/auth/passkeys (signed in): what is registered, without the keys
    async list(request, env, uid) {
      const rows = (await env.DB.prepare('SELECT id,backed_up,created_at,last_used_at FROM passkeys WHERE user_id=? ORDER BY created_at').bind(uid).all()).results;
      return json({passkeys: rows.map(r => ({id: r.id, synced: !!r.backed_up, created_at: r.created_at, last_used_at: r.last_used_at}))});
    },

    // POST /api/auth/passkeys/delete (signed in): e.g. after losing a device
    async remove(request, env, uid) {
      const input = await h.body(request);
      if (typeof input.id !== 'string' || input.id.length > 1024) fail(400, '入力を確認してください。');
      await env.DB.prepare('DELETE FROM passkeys WHERE id=? AND user_id=?').bind(input.id, uid).run();
      return json({ok: true});
    },
  };
}
