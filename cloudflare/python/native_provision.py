"""Convert native preview data additively into the original user-scoped schema.

A native_source archive retains every source column/ID and timestamp. Original
native tables remain untouched; this is a one-time cutover, not bidirectional sync.
"""
import json
import sqlite3
from datetime import datetime, timezone
from snapshot_store import capture

async def build_snapshot(db, uid):
    results = await db.batch([
        db.prepare('SELECT * FROM records WHERE user_id=? ORDER BY id').bind(uid),
        db.prepare('SELECT * FROM favourites WHERE user_id=? ORDER BY kind,name').bind(uid),
        db.prepare('SELECT * FROM reactions WHERE user_id=? ORDER BY stage_id').bind(uid),
    ])
    results = results.to_py() if hasattr(results,'to_py') else results
    records,favourites,reactions = [item['results'] for item in results]
    # Loading legacy_runtime only changes import paths, never accesses private
    # filesystem DBs. Its synchronous adapter creates schema in request-local DB.
    import legacy_runtime
    serve = legacy_runtime.serve
    con = sqlite3.connect(':memory:')
    try:
        import rate_performances as rate
        con.executescript(rate.SCHEMA)
        con.executescript(serve.FB.SCHEMA)
        con.executescript(serve.APP.SETTING_SCHEMA)
        con.executescript(serve.MISSED_SCHEMA)
        # Original schema creates these columns lazily in app rendering.
        columns = {row[1] for row in con.execute('PRAGMA table_info(works)')}
        for name in ('stage_id','venue','time'):
            if name not in columns:
                con.execute(f'ALTER TABLE works ADD COLUMN {name} TEXT')
        con.execute('CREATE TABLE native_source(user_id TEXT NOT NULL,source_table TEXT NOT NULL,source_key TEXT NOT NULL,row_json TEXT NOT NULL,PRIMARY KEY(user_id,source_table,source_key))')
        for source,items in [('records',records),('favourites',favourites),('reactions',reactions)]:
            for item in items:
                key = item.get('id') or item.get('stage_id') or json.dumps([item['name'],item['kind']],ensure_ascii=False)
                con.execute('INSERT INTO native_source VALUES(?,?,?,?)',(uid,source,key,json.dumps(item,ensure_ascii=False,sort_keys=True)))
        for row in records:
            # Stable ID keeps multiple performances of one title/date independent.
            key = 'native:' + row['id']
            updated = datetime.fromtimestamp(row['updated_at'],timezone.utc).isoformat()
            con.execute('INSERT INTO works(user_id,work_key,title,first_date,last_date,times,verdict,note_impression,note_motive,stage_id,venue,time,updated_at) VALUES(?,?,?,?,?,1,?,?,\'\',\'\',?,?,?)',(uid,key,row['title'],row['date'],row['date'],row['rating'] or None,row['note'],row['venue'],row['time'],updated))
        if favourites:
            declared = {}
            for row in favourites:
                declared.setdefault(row['kind'], []).append(row['name'])
            con.execute('INSERT INTO app_setting VALUES(?,?,?,?)',(uid,'declared',json.dumps(declared,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
        for row in reactions:
            updated = datetime.fromtimestamp(row['updated_at'],timezone.utc).isoformat()
            status = row['status']
            con.execute('INSERT INTO reaction(user_id,label,stage_id,interest,owned,source,updated_at) VALUES(?,?,?,?,?,?,?)',(uid,updated[:10],row['stage_id'],1 if status=='interest' else 0 if status=='no' else None,1 if status=='owned' else None,'native_migration',updated))
        # presented has historically been shared; in snapshots it is scoped.
        columns = {row[1] for row in con.execute('PRAGMA table_info(presented)')}
        if 'user_id' not in columns:
            con.execute('ALTER TABLE presented ADD COLUMN user_id TEXT NOT NULL DEFAULT \'' + uid.replace("'","''") + "'")
        con.commit()
        return capture(con,uid)
    finally:
        con.close()
