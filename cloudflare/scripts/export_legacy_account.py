#!/usr/bin/env python3
"""Read-only, lossless account snapshot. Operator tool; never expose as HTTP.

Every user-scoped table is exported with every column. Shared tables are
inventoried, not silently copied to an account. Authentication databases and
pepper files are deliberately excluded and need a separate protected backup.
This is a staging snapshot, not a native-D1 application import.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def value(v):
    return {'$sqlite_blob': base64.b64encode(v).decode('ascii')} if isinstance(v, bytes) else v


def snapshot(database, user_id):
    path = Path(database).resolve(strict=True)
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('BEGIN')  # Consistent read snapshot while the old server writes.
        tables, inventory = {}, []
        for row in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
            name, schema = row['name'], row['sql']
            info = list(conn.execute(f'PRAGMA table_info({quoted(name)})'))
            columns = [r['name'] for r in info]
            primary_key = [r['name'] for r in sorted(info,key=lambda r:r['pk']) if r['pk']]
            if 'user_id' not in columns:
                inventory.append({'table': name, 'columns': columns, 'reason': 'no-user-id-column'})
                continue
            rows = [dict((k, value(v)) for k, v in dict(r).items()) for r in conn.execute(f'SELECT * FROM {quoted(name)} WHERE user_id=?', (user_id,))]
            # Stable ordering makes comparison independent of SQLite query plans.
            rows.sort(key=lambda r: json.dumps(r, ensure_ascii=False, sort_keys=True))
            encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
            tables[name] = {'schema': schema, 'columns': columns, 'primary_key': primary_key, 'count': len(rows), 'sha256': hashlib.sha256(encoded).hexdigest(), 'rows': rows}
        conn.rollback()
        if not tables:
            raise ValueError('No user-scoped tables found; refusing an empty migration snapshot.')
        if not any(t['count'] for t in tables.values()):
            raise ValueError('No rows found for this account; verify the source database and user ID.')
        return {'format': 'taguri-legacy-account', 'version': 1, 'user_id': user_id, 'tables': tables, 'shared_tables_not_exported': inventory, 'authentication_not_exported': True}
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--user-id', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not args.user_id or len(args.user_id) > 200:
        parser.error('Invalid account identifier.')
    try:
        result = snapshot(args.db, args.user_id)
        # Never overwrite an existing backup, and protect it from other users.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(result, out, ensure_ascii=False, indent=2)
            out.write('\n')
    except (ValueError, sqlite3.Error, OSError) as error:
        parser.exit(1, f'Snapshot failed: {type(error).__name__}. No source data was modified.\n')


if __name__ == '__main__':
    main()
