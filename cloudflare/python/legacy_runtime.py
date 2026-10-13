"""Reuse original renderer/controller synchronously; no network HTTP server.

Prototype gate: deployment requires Python Workers runtime, full public assets,
per-account D1 authentication and successful original-screen CPU measurements.
Do not enable the production bridge switch merely because this imports locally.
"""
from contextlib import nullcontext
from email.message import Message
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from urllib.parse import urlsplit

try:
    from taguri_project import PROJECT_ROOT as ROOT
    from taguri_project.approved_fixture import FIXTURE
    fixture = ROOT / 'tools' / 'taguri' / 'demo_purchase_works.json'
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(FIXTURE, ensure_ascii=False), encoding='utf-8')
    try:
        from public_snapshot import PUBLIC_FILES, POSTER_NAMES
        allowed_files = {'data/review/candidates.jsonl','data/review/recommend2.json','data/credits/credits.jsonl','data/credits/themes.jsonl'}
        if set(PUBLIC_FILES) - allowed_files:
            raise ValueError('Public snapshot contains an unapproved file')
        for relative, content in PUBLIC_FILES.items():
            destination = ROOT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding='utf-8')
        image_dir = ROOT / 'data' / 'review' / 'img'
        image_dir.mkdir(parents=True,exist_ok=True)
        for name in POSTER_NAMES:
            (image_dir / name).touch()
    except ImportError:
        pass
except ImportError:
    raise RuntimeError('Build the source-only Python bundle before loading the migration runtime') from None
for path in (ROOT / 'tools' / 'taguri', ROOT / 'tools' / 'review'):
    sys.path.insert(0, str(path))
import serve
serve.APP.RR.NOTES_BY_PERSON = {}
from snapshot_store import capture, materialize

SCREENS = {'recommend','reminder','interest','favourites','calendar','tickets','rate','unrated','notes','register','records','trace','chronicle','works','search','settings','start'}
POSTS = {'react','rate','note','favourite','missed','add_work','fix_work','merge_work','drop_work','restore_work','purge_work','unseen','ticket','weight','pref_setting','hand_credits','link_stage','decline','visit_note','close','import_mail','chronicle','people_read','hand_poster','hand_theme','hand_theme_refresh'}
_active = False


class CapturedHandler(serve.Handler):
    def __init__(self, server, account, path, method, payload, origin):
        self.server, self.user_id, self.path = server, account, path
        self.command = method
        self.headers = Message()
        self.headers['Host'] = urlsplit(origin).netloc
        self.headers['Origin'] = origin
        self.headers['Content-Type'] = 'application/json'
        self.headers['Content-Length'] = str(len(payload))
        self.rfile = io.BytesIO(payload)
        self.client_address = ('worker-internal', 0)
        self.response = None
        self.close_connection = False

    def _resolve_user(self):
        # Authentication is resolved by the D1 adapter before reaching this code.
        return self.user_id, None

    def _send(self, code, body, ctype='text/html; charset=utf-8', extra=None):
        if code >= 500:
            body = json.dumps({'ok': False, 'error': '処理できませんでした。記録は変更されていません。'}, ensure_ascii=False).encode()
            ctype = 'application/json'
        self.response = (code, body, {'Content-Type': ctype, 'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', **(extra or {})})


class SynchronousServer(serve.Server):
    def __init__(self, connection, origin):
        # Never initialize ThreadingHTTPServer, bind sockets, spawn background
        # threads, run watchdogs or owner subprocesses in a Worker.
        self.con, self.lock = connection, nullcontext()
        self.label = __import__('datetime').date.today().isoformat()
        self.token, self.cors_origin, self.demo_mode = '', origin, True
        self.n = {key: 0 for key in ('react','rate','note','fav','missed','add','import','fix')}
        self.screen_cache, self.prefs_by_user = {}, {}
        self.imp, self.imported = {'running': False, 'line': ''}, []
        self.opened = True

    def get_prefs(self, user_id):
        # The old server cached runtime filters for its process lifetime. Each
        # Worker execution has a fresh server, so persist this separate setting.
        self.con.executescript(serve.APP.SETTING_SCHEMA)
        row = self.con.execute('SELECT value FROM app_setting WHERE user_id=? AND key=?',
                               (user_id, 'runtime_pref_filter')).fetchone()
        self.con.commit()
        if row:
            try:
                value = json.loads(row[0])
                if isinstance(value, list):
                    return [p for p in serve.APP.RR.PREFS if p in value]
            except (ValueError, TypeError):
                pass
        return serve.APP.read_pref_setting(user_id)

    def set_prefs(self, user_id, prefs):
        if not isinstance(prefs, list) or len(prefs) > 47:
            raise ValueError('都道府県の並びがおかしい')
        keep = [p for p in serve.APP.RR.PREFS if p in prefs]
        self.con.executescript(serve.APP.SETTING_SCHEMA)
        self.con.execute("INSERT INTO app_setting(user_id,key,value,updated_at) VALUES(?,?,?,datetime('now')) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                         (user_id, 'runtime_pref_filter', json.dumps(keep, ensure_ascii=False)))
        self.con.commit()
        self.prefs_by_user[user_id] = keep
        # Original on_pref_setting calls this after saving its default setting,
        # so defaults and current runtime filters switch together immediately.

    def enqueue(self, label, fn):
        raise ValueError('この更新には管理者のバッチ処理が必要です。')

    def _sh(self, args, done):
        raise ValueError('Workerから外部プログラムは実行しません。')


def execute(account, tables, path, method='GET', payload=b'', origin='https://taguri.invalid'):
    """No await allowed here: module path/cache changes cannot interleave users."""
    global _active
    if _active:
        raise RuntimeError('Legacy execution must not reenter')
    if not account or account == serve.AU.LOCAL_USER_ID:
        raise ValueError('Owner identity requires a separate protected migration')
    route = urlsplit(path).path
    if not ((method == 'GET' and (route.startswith('/api/screen/') and route.rsplit('/',1)[-1] in SCREENS or route in {'/api/suggest','/api/suggest_web','/api/mail_hints','/api/import_status','/export.json'})) or (method == 'POST' and route.startswith('/api/') and route[5:] in POSTS)):
        return 404, b'{"ok":false,"error":"unknown route"}', {'Content-Type':'application/json'} , tables
    if len(payload) > 8192:
        return 413, b'{"ok":false,"error":"body too large"}', {'Content-Type':'application/json'}, tables
    _active = True
    changed = []
    original_record = serve.APP.RECORD
    connection = None
    try:
        with tempfile.TemporaryDirectory(prefix='taguri-request-') as folder:
            database = Path(folder) / 'ratings.db'
            source = materialize(tables, account)
            connection = sqlite3.connect(database)
            source.backup(connection)
            source.close()
            # All original modules share the same ratings database path; redirect
            # only DB values with that exact basename, and restore in finally.
            for module in list(sys.modules.values()):
                old = getattr(module, 'DB', None)
                if isinstance(old, Path) and old.name == 'ratings.db':
                    changed.append((module, old))
                    module.DB = database
            serve.APP.reset_caches()
            # Schema creation/migrations are reused, without global HTTP startup.
            bootstrap = serve.FB.connect()
            bootstrap.executescript(serve.MISSED_SCHEMA)
            bootstrap.commit()
            bootstrap.close()
            # presented was historically global. In this isolated snapshot it is
            # account-private, and must be persisted rather than silently dropped.
            cols = [r[1] for r in connection.execute('PRAGMA table_info(presented)')]
            if cols and 'user_id' not in cols:
                quoted_account = "'" + account.replace("'", "''") + "'"
                connection.execute('ALTER TABLE presented ADD COLUMN user_id TEXT NOT NULL DEFAULT ' + quoted_account)
                connection.commit()
            server = SynchronousServer(connection, origin)
            serve.APP.RECORD = server.record_presented
            handler = CapturedHandler(server, account, path, method, payload, origin)
            if route == '/export.json':
                body = json.dumps({'format':'taguri-legacy-account','version':1,'tables':capture(connection, account)}, ensure_ascii=False).encode()
                handler._send(200,body,'application/json',{'Content-Disposition':'attachment; filename="taguri-export.json"'})
            elif method == 'GET':
                handler.do_GET()
            else:
                handler.do_POST()
            result = handler.response or (500,b'{"ok":false,"error":"no response"}',{'Content-Type':'application/json'})
            # Failed operations never flush any partially mutated database.
            updated = capture(connection,account) if result[0] < 400 else tables
            connection.close()
            connection = None
            return (*result, updated)
    finally:
        if connection is not None:
            connection.close()
        serve.APP.RECORD = original_record
        for module, original in changed:
            module.DB = original
        serve.APP.reset_caches()
        _active = False
