"""D1 auth shared with native preview; account claims never create identities.

No secrets/code/IP/SQL are logged. Legacy Base32 recovery requires an operator
provisioned identity map and secret pepper; scrypt is only enabled in the
protected Python Durable Object compute path.
"""
import hashlib
import json
import re
import secrets
import time
import uuid
from urllib.parse import urlsplit, parse_qs

TTL = 30 * 86400

class AuthError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def py(value):
    return value.to_py() if hasattr(value, 'to_py') else value

def cookie(token='', clear=False):
    return f'taguri_session={token}; Path=/; Max-Age={0 if clear else TTL}; HttpOnly; Secure; SameSite=Strict'

def raw_session(request):
    match = re.search(r'(?:^|;\s*)taguri_session=([a-f0-9]{64})(?:;|$)', request.headers.get('Cookie') or '')
    return match[1] if match else None

async def current(request, env):
    token = raw_session(request)
    if not token:
        return None
    row = py(await env.DB.prepare('SELECT user_id FROM sessions WHERE hash=? AND expires_at>?').bind(digest(token),int(time.time())).first())
    return row['user_id'] if row else None

async def throttle(request, env, action, maximum):
    now = int(time.time())
    # Trusted Cloudflare header, stored only as a one-way hash. Fall back to one
    # shared bucket rather than trusting client-supplied forwarded headers.
    actor = digest(request.headers.get('CF-Connecting-IP') or 'unknown')
    row = py(await env.DB.prepare('INSERT INTO auth_attempts(action,actor_hash,window,attempts) VALUES(?,?,?,1) ON CONFLICT(action,actor_hash,window) DO UPDATE SET attempts=attempts+1 RETURNING attempts').bind(action,actor,now//600).first())
    if row['attempts'] > maximum:
        raise AuthError(429,'しばらく待ってからお試しください。')
    # Bounded retention; cleanup only once per action/window actor's first try.
    if row['attempts'] == 1:
        await env.DB.prepare('DELETE FROM auth_attempts WHERE window<?').bind(now//600-2).run()

async def new_session(env, user_id):
    token = secrets.token_hex(32)
    now = int(time.time())
    await env.DB.batch([
        env.DB.prepare('DELETE FROM sessions WHERE user_id=? AND (expires_at<=? OR hash NOT IN (SELECT hash FROM sessions WHERE user_id=? ORDER BY expires_at DESC LIMIT 9))').bind(user_id,now,user_id),
        env.DB.prepare('INSERT INTO sessions(hash,user_id,expires_at) VALUES(?,?,?)').bind(digest(token),user_id,now+TTL),
    ])
    return cookie(token)

async def resolve_account(request, env):
    uid = await current(request,env)
    if uid:
        await provision_native(env.DB,uid)
        return {'user_id':uid}
    if raw_session(request):
        raise AuthError(401,'セッションの期限が切れました。復旧コードでログインしてください。')
    # Only operator-imported hashed original sessions can claim a legacy user.
    legacy = re.search(r'(?:^|;\s*)tg_session=([A-Za-z0-9_-]{43})(?:;|$)',request.headers.get('Cookie') or '')
    if legacy:
        await throttle(request,env,'legacy_session',20)
        row = py(await env.DB.prepare('SELECT user_id FROM legacy_sessions WHERE token_hash=? AND expires_at>?').bind(digest(legacy[1]),int(time.time())).first())
        if not row:
            raise AuthError(503,'既存アカウントの移行が必要です。復旧コードで接続してください。')
        uid = row['user_id']
        if not py(await env.DB.prepare('SELECT user_id FROM legacy_accounts WHERE user_id=?').bind(uid).first()):
            raise AuthError(503,'元の記録の移行が未準備です。')
        code = secrets.token_hex(32)
        # Add an alternate recovery credential; never invalidate existing codes.
        await env.DB.prepare('INSERT INTO legacy_recovery(recovery_hash,user_id) VALUES(?,?)').bind(digest(code),uid).run()
        return {'user_id':uid,'welcome_code':code,'set_cookie':await new_session(env,uid)}
    if re.search(r'(?:^|;\s*)tg_session=',request.headers.get('Cookie') or ''):
        raise AuthError(503,'既存アカウントの移行が必要です。復旧コードで接続してください。')
    if request.method != 'GET':
        raise AuthError(401,'復旧コードでログインしてください。')
    if getattr(env,'ALLOW_REGISTRATION','false') != 'true':
        raise AuthError(503,'新規登録を一時停止しています。')
    await throttle(request,env,'register',20)
    uid, code, session_token = str(uuid.uuid4()), secrets.token_hex(32), secrets.token_hex(32)
    try:
        await env.DB.batch([
            env.DB.prepare('INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)').bind(uid,digest(code),int(time.time())),
            env.DB.prepare('INSERT INTO legacy_accounts(user_id,revision,write_token) VALUES(?,0,\'\')').bind(uid),
            env.DB.prepare('INSERT INTO sessions(hash,user_id,expires_at) VALUES(?,?,?)').bind(digest(session_token),uid,int(time.time())+TTL),
        ])
    except Exception:
        raise AuthError(503,'登録できませんでした。プレビューの利用者上限は100人です。') from None
    return {'user_id':uid,'welcome_code':code,'set_cookie':cookie(session_token)}

async def read_input(request):
    # Content length is only an early check; stream actual bytes with strict cap.
    reader = request.body.getReader() if request.body else None
    data = bytearray()
    if reader:
        while True:
            item = await reader.read()
            if item.done:
                break
            data.extend(bytes(py(item.value)))
            if len(data)>8192:
                await reader.cancel()
                raise AuthError(413,'入力が長すぎます。')
    ctype = request.headers.get('Content-Type') or ''
    try:
        if ctype.startswith('application/json'):
            value = json.loads(data or b'{}')
            if not isinstance(value,dict):
                raise ValueError()
            return value
        if ctype.startswith('application/x-www-form-urlencoded'):
            return {k:v[0] for k,v in parse_qs(data.decode(),keep_blank_values=True,max_num_fields=10).items()}
    except (ValueError,UnicodeError):
        raise AuthError(400,'入力を確認してください。') from None
    raise AuthError(415,'対応していない入力形式です。')

async def handle_auth(request, env):
    """Return (status, JSON dict, headers), or None for ordinary routes.

    Caller renders existing auth pages/form success and attaches headers. JSON
    callers receive dict unchanged. POST CSRF must remain checked on all routes.
    """
    path = urlsplit(request.url).path
    routes = {'/api/recover','/api/logout','/api/link/create','/api/link/redeem','/api/delete_account'}
    if path not in routes:
        return None
    if request.method != 'POST':
        raise AuthError(405,'POSTが必要です。')
    url = urlsplit(request.url)
    if request.headers.get('Origin') != f'{url.scheme}://{url.netloc}':
        raise AuthError(403,'同じサイトから操作してください。')
    values = await read_input(request)
    uid = await current(request,env)
    if path == '/api/recover':
        await throttle(request,env,'recover',10)
        code = str(values.get('code','')).strip().lower().replace('-','').replace(' ','')
        if re.fullmatch('[a-f0-9]{64}',code):
            row = py(await env.DB.prepare('SELECT id AS user_id FROM users WHERE recovery_hash=? UNION ALL SELECT user_id FROM legacy_recovery WHERE recovery_hash=? LIMIT 1').bind(digest(code),digest(code)).first())
        elif re.fullmatch('[a-z2-7]{26}',code):
            row = py(await env.DB.prepare('SELECT user_id FROM legacy_recovery WHERE recovery_hash=?').bind(digest(code)).first())
            if not row:
                pepper = getattr(env,'LEGACY_AUTH_PEPPER',None)
                if not pepper or getattr(env,'LEGACY_SCRYPT_ENABLED','false') != 'true':
                    raise AuthError(503,'既存アカウントの復旧コード移行が未準備です。管理者に確認してください。')
                try:
                    salt = bytes.fromhex(str(pepper))
                    if len(salt) != 32:
                        raise ValueError()
                    old_id = hashlib.scrypt(code.encode('ascii'),salt=salt,n=16384,r=8,p=1,dklen=16).hex()
                except Exception:
                    raise AuthError(503,'既存アカウントの認証設定が未準備です。') from None
                row = py(await env.DB.prepare('SELECT m.user_id FROM legacy_user_map m JOIN legacy_accounts a ON a.user_id=m.user_id JOIN users u ON u.id=m.user_id WHERE m.old_user_id=?').bind(old_id).first())
                if not row:
                    raise AuthError(401,'復旧コードを確認してください。')
                # Cache only the authenticated credential digest, never raw code.
                await env.DB.prepare('INSERT INTO legacy_recovery(recovery_hash,user_id) VALUES(?,?) ON CONFLICT(recovery_hash) DO NOTHING').bind(digest(code),row['user_id']).run()
        else:
            row = None
        if not row:
            raise AuthError(401,'復旧コードを確認してください。')
        uid = row['user_id']
        await provision_native(env.DB,uid)
        return 200, {'ok':True}, {'Set-Cookie':await new_session(env,uid)}
    if path == '/api/link/redeem':
        await throttle(request,env,'link_redeem',10)
        code = str(values.get('code','')).strip()
        if not re.fullmatch('[0-9]{6}',code):
            raise AuthError(400,'6桁のコードを確認してください。')
        # UPDATE..RETURNING is atomic: only one request can redeem a live code.
        # All unsuccessful guesses are capped by the trusted-IP throttle above.
        marker = secrets.token_hex(32)
        row = py(await env.DB.prepare("UPDATE device_links SET used_token=?,attempts=attempts+1 WHERE code_hash=? AND expires_at>? AND attempts<5 AND used_token='' RETURNING user_id").bind(marker,digest(code),int(time.time())).first())
        if not row:
            raise AuthError(401,'コードが無効または期限切れです。')
        uid = row['user_id']
        await provision_native(env.DB,uid)
        return 200, {'ok':True}, {'Set-Cookie':await new_session(env,uid)}
    if not uid:
        raise AuthError(401,'ログインしてください。')
    if path == '/api/link/create':
        await throttle(request,env,'link_create',10)
        code = f'{secrets.randbelow(1000000):06d}'
        now = int(time.time())
        # Replace expired collisions only; live codes must never change owner.
        await env.DB.batch([
            env.DB.prepare('DELETE FROM device_links WHERE user_id=? OR expires_at<=?').bind(uid,now),
            env.DB.prepare('INSERT INTO device_links(code_hash,user_id,expires_at) VALUES(?,?,?)').bind(digest(code),uid,now+600),
        ])
        return 200, {'code':code,'expires_in_sec':600}, {}
    if path == '/api/logout':
        commands=[env.DB.prepare('DELETE FROM sessions WHERE hash=? AND user_id=?').bind(digest(raw_session(request)),uid)]
        legacy = re.search(r'(?:^|;\s*)tg_session=([A-Za-z0-9_-]{43})(?:;|$)',request.headers.get('Cookie') or '')
        if legacy:
            commands.append(env.DB.prepare('DELETE FROM legacy_sessions WHERE token_hash=? AND user_id=?').bind(digest(legacy[1]),uid))
        await env.DB.batch(commands)
        return 200, {'ok':True}, {'Set-Cookie':cookie(clear=True)}
    if values.get('confirm') != 'DELETE':
        raise AuthError(400,'削除の確認が必要です。')
    # Explicit scoped deletes cover prototypes without FK from legacy_accounts.
    await env.DB.batch([env.DB.prepare(f'DELETE FROM {table} WHERE {key}=?').bind(uid) for table,key in [
        ('legacy_rows','user_id'),('legacy_schemas','user_id'),('legacy_accounts','user_id'),('legacy_recovery','user_id'),('legacy_sessions','user_id'),('legacy_user_map','user_id'),('device_links','user_id'),('sessions','user_id'),('records','user_id'),('favourites','user_id'),('reactions','user_id'),('users','id')]])
    return 200, {'ok':True}, {'Set-Cookie':cookie(clear=True)}

async def provision_native(db, uid):
    """Idempotent additive conversion. Original native records are never removed."""
    row = py(await db.prepare('SELECT revision FROM legacy_accounts WHERE user_id=?').bind(uid).first())
    if row:
        return
    from native_provision import build_snapshot
    tables = await build_snapshot(db,uid)
    from snapshot_store import chunks, keyed_rows
    schemas, rows = [], []
    for name,table in tables.items():
        schemas.append({'table':name,'schema':table['schema'],'columns':json.dumps(table['columns']),'pk':json.dumps(table['primary_key'])})
        rows.extend({'table':name,'key':key,'row':value} for key,value in keyed_rows(table).items())
    marker = secrets.token_hex(32)
    guard = 'EXISTS(SELECT 1 FROM legacy_accounts WHERE user_id=? AND write_token=?)'
    commands=[db.prepare('INSERT INTO legacy_accounts(user_id,revision,write_token) VALUES(?,0,?) ON CONFLICT(user_id) DO NOTHING').bind(uid,marker)]
    for block in chunks(schemas):
        commands.append(db.prepare(f"INSERT INTO legacy_schemas SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.schema'),json_extract(value,'$.columns'),json_extract(value,'$.pk') FROM json_each(?) WHERE {guard}").bind(uid,block,uid,marker))
    for block in chunks(rows):
        commands.append(db.prepare(f"INSERT INTO legacy_rows SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.key'),json_extract(value,'$.row') FROM json_each(?) WHERE {guard}").bind(uid,block,uid,marker))
    if len(commands)>40:
        raise AuthError(503,'移行データが大きいため管理者による取り込みが必要です。')
    await db.batch(commands)
