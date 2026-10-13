"""Lossless D1 persistence for request-scoped legacy SQLite.

No shared global SQLite connection or writable global filesystem is used here.
The caller must complete all legacy synchronous work without awaiting and close
its request-local connection before the next request enters legacy code.
"""
import base64
import hashlib
import json
import sqlite3
import uuid


class ConcurrentWrite(Exception):
    pass


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def encode(value):
    return {'$sqlite_blob': base64.b64encode(value).decode()} if isinstance(value, bytes) else value


def decode(value):
    return base64.b64decode(value['$sqlite_blob'], validate=True) if isinstance(value, dict) and set(value) == {'$sqlite_blob'} else value


def materialize(tables, user_id):
    """Return a new private in-memory DB; reject any cross-account input."""
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    try:
        for name, table in tables.items():
            # Schemas originate from the operator's protected migration snapshot,
            # never from an unauthenticated HTTP request.
            con.execute(table['schema'])
            columns = [r['name'] for r in con.execute(f'PRAGMA table_info({quote(name)})')]
            if 'user_id' not in columns:
                raise ValueError('Private table has no ownership column')
            for row in table['rows']:
                if row.get('user_id') != user_id or set(row) != set(columns):
                    raise ValueError('Account snapshot ownership or schema mismatch')
                con.execute(f'INSERT INTO {quote(name)} ({",".join(quote(c) for c in columns)}) VALUES ({",".join("?" for _ in columns)})', [decode(row[c]) for c in columns])
        con.commit()
        return con
    except Exception:
        con.close()
        raise


def capture(con, user_id):
    """Capture every column from every user-scoped table, including new tables."""
    result = {}
    for name, schema in con.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        info = list(con.execute(f'PRAGMA table_info({quote(name)})'))
        columns = [r[1] for r in info]
        primary_key = [r[1] for r in sorted(info, key=lambda r: r[5]) if r[5]]
        if 'user_id' not in columns:
            continue
        rows = []
        for row in con.execute(f'SELECT * FROM {quote(name)}'):
            item = dict(zip(columns, row))
            if item['user_id'] != user_id:
                raise ValueError('Legacy operation wrote a different account')
            rows.append({k: encode(v) for k, v in item.items()})
        rows.sort(key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
        result[name] = {'schema': schema, 'columns': columns, 'primary_key': primary_key, 'rows': rows}
    return result


async def load(db, user_id):
    # Batch reads give a consistent transaction snapshot across revision and rows.
    results = await db.batch([
        db.prepare('SELECT revision FROM legacy_accounts WHERE user_id=?').bind(user_id),
        db.prepare('SELECT table_name, schema_sql,columns_json,primary_key_json FROM legacy_schemas WHERE user_id=?').bind(user_id),
        db.prepare('SELECT table_name, row_json FROM legacy_rows WHERE user_id=? ORDER BY table_name,row_key').bind(user_id),
    ])
    # Python Workers JS proxies need to_py() at the binding boundary.
    results = results.to_py() if hasattr(results, 'to_py') else results
    accounts = results[0]['results']
    if not accounts:
        raise KeyError('Account snapshot has not been provisioned')
    tables = {r['table_name']: {'schema': r['schema_sql'], 'columns':json.loads(r['columns_json']), 'primary_key':json.loads(r['primary_key_json']), 'rows': []} for r in results[1]['results']}
    for row in results[2]['results']:
        tables[row['table_name']]['rows'].append(json.loads(row['row_json']))
    for table in tables.values():
        table['rows'].sort(key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
    return accounts[0]['revision'], tables


def keyed_rows(table):
    result, counts = {}, {}
    for row in table['rows']:
        keys = table.get('primary_key') or []
        identity = [row[k] for k in keys] if keys else row
        encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        key = hashlib.sha256(encoded.encode()).hexdigest()
        if not keys:
            counts[key] = counts.get(key, 0) + 1
            key += ':' + str(counts[key])
        if key in result:
            raise ValueError('Duplicate primary key in snapshot')
        result[key] = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return result


def chunks(items, limit=900000):
    block = []
    size = 2
    for item in items:
        encoded = json.dumps(item, ensure_ascii=False, separators=(',', ':'))
        addition = len(encoded.encode()) + 1
        if addition > limit:
            raise ValueError('Migration row exceeds binding size budget')
        if block and size + addition > limit:
            yield json.dumps(block, ensure_ascii=False, separators=(',', ':'))
            block, size = [], 2
        block.append(item)
        size += addition
    if block:
        yield json.dumps(block, ensure_ascii=False, separators=(',', ':'))


async def save(db, user_id, revision, tables, before):
    """Atomic dirty-row CAS, bounded to 40 queries including arbitrarily many rows.

    JSON_each groups changed rows into <=900KB parameters. A normal 96-record
    migration needs 5 queries, not 96. The caller's auth/load budget is 4 queries.
    Oversize operations fail before executing any mutations.
    """
    if tables == before:
        return revision
    marker = str(uuid.uuid4())
    guard = 'EXISTS (SELECT 1 FROM legacy_accounts WHERE user_id=? AND write_token=?)'
    commands = [db.prepare('UPDATE legacy_accounts SET revision=revision+1,write_token=? WHERE user_id=? AND revision=?').bind(marker,user_id,revision)]
    schema_deletes, schema_inserts, deletes, inserts = [], [], [], []
    for name in sorted(set(tables) | set(before)):
        new, old = tables.get(name), before.get(name)
        if new == old:
            continue
        if new is None or old is None or any(new.get(k) != old.get(k) for k in ('schema','columns','primary_key')):
            schema_deletes.append(name)
            if new is not None:
                schema_inserts.append({'table':name,'schema':new['schema'],'columns':json.dumps(new['columns']),'pk':json.dumps(new.get('primary_key',[]))})
        old_rows, new_rows = keyed_rows(old) if old else {}, keyed_rows(new) if new else {}
        for key in sorted(set(old_rows) | set(new_rows)):
            if old_rows.get(key) == new_rows.get(key):
                continue
            deletes.append({'table':name,'key':key})
            if key in new_rows:
                payload = new_rows[key]
                if json.loads(payload).get('user_id') != user_id:
                    raise ValueError('Cross-account write rejected')
                inserts.append({'table':name,'key':key,'row':payload})
    for block in chunks(schema_deletes):
        commands.append(db.prepare(f'DELETE FROM legacy_schemas WHERE user_id=? AND table_name IN (SELECT value FROM json_each(?)) AND {guard}').bind(user_id,block,user_id,marker))
    for block in chunks(schema_inserts):
        commands.append(db.prepare(f"INSERT INTO legacy_schemas(user_id,table_name,schema_sql,columns_json,primary_key_json) SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.schema'),json_extract(value,'$.columns'),json_extract(value,'$.pk') FROM json_each(?) WHERE {guard}").bind(user_id,block,user_id,marker))
    for block in chunks(deletes):
        commands.append(db.prepare(f"DELETE FROM legacy_rows WHERE user_id=? AND EXISTS (SELECT 1 FROM json_each(?) AS item WHERE json_extract(item.value,'$.table')=legacy_rows.table_name AND json_extract(item.value,'$.key')=legacy_rows.row_key) AND {guard}").bind(user_id,block,user_id,marker))
    for block in chunks(inserts):
        commands.append(db.prepare(f"INSERT INTO legacy_rows(user_id,table_name,row_key,row_json) SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.key'),json_extract(value,'$.row') FROM json_each(?) WHERE {guard}").bind(user_id,block,user_id,marker))
    if len(commands) > 40:
        raise ValueError('Operation exceeds free-tier query budget; no changes saved')
    results = await db.batch(commands)
    results = results.to_py() if hasattr(results,'to_py') else results
    if results[0]['meta']['changes'] != 1:
        raise ConcurrentWrite('Record changed in another request; reload and retry')
    return revision + 1
