#!/usr/bin/env python3
"""Protected operator-only auth import; never exports raw session tokens.

Requires an explicit one-to-one old-user-ID -> provisioned-D1-user-ID mapping.
Does not create accounts, reset codes, or copy pepper. Complete account snapshots
and auth migrations must already exist. JSON is the preferred atomic-runner input.
SQL has NO BEGIN/COMMIT (D1 forbids imported transaction statements): each guarded
statement is idempotent, rejects missing target/snapshot or conflicting identity,
and a partial failure can be rerun after diagnosis. Operator must verify all
mapping/session counts and snapshot correlation; file execution alone is not a
migration-success assertion. Never expose these files as an HTTP public upload.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

TTL = 365 * 86400

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def auth_manifest(database, mapping, now=None):
    now = int(time.time()) if now is None else now
    if not isinstance(mapping,dict) or not mapping or len(mapping)>100:
        raise ValueError('An explicit nonempty identity mapping of at most 100 accounts is required')
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Identity mappings must be one-to-one; implicit account merging is forbidden')
    con = sqlite3.connect(Path(database).resolve(strict=True).as_uri()+'?mode=ro',uri=True)
    try:
        con.execute('BEGIN')  # Read-only SQLite source snapshot, not emitted D1 SQL.
        users = {row[0] for row in con.execute('SELECT user_id FROM users')}
        if any(not isinstance(old,str) or not re.fullmatch('[a-f0-9]{32}',old) or old not in users or not isinstance(new,str) or not new or len(new)>100 or new=='local' for old,new in mapping.items()):
            raise ValueError('Mapping includes an unknown source or invalid target identity')
        sessions=[]
        for token,old,created in con.execute('SELECT session_token,user_id,created_at FROM sessions ORDER BY user_id,created_at'):
            if old not in mapping or int(created+TTL)<=now:
                continue
            if not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]{43}',token):
                raise ValueError('Invalid original session format')
            sessions.append({'user_id':mapping[old],'token_hash':hashlib.sha256(token.encode()).hexdigest(),'expires_at':int(created+TTL)})
        con.rollback()
        return {'format':'taguri-legacy-auth','version':1,'mappings':[{'old_user_id':old,'user_id':new} for old,new in sorted(mapping.items())],'sessions':sessions}
    finally:
        con.close()

def auth_sql(database,mapping,now=None):
    data=auth_manifest(database,mapping,now)
    statements=['-- Protected auth migration: SHA256 session digests only.',
                '-- D1-compatible: no BEGIN/COMMIT. Guard failure aborts a statement.',
                '-- Partial failures require diagnosis and idempotent rerun; verify counts.']
    for row in data['mappings']:
        old,new=quote(row['old_user_id']),quote(row['user_id'])
        # Scalar subquery returns NULL on missing users/snapshot, causing NOT NULL
        # failure instead of a silently skipped insertion. Collision also fails.
        statements.append('INSERT INTO legacy_user_map(old_user_id,user_id) VALUES('+old+', (SELECT u.id FROM users u JOIN legacy_accounts a ON a.user_id=u.id WHERE u.id='+new+')) ON CONFLICT(old_user_id) DO UPDATE SET user_id=CASE WHEN legacy_user_map.user_id=excluded.user_id THEN legacy_user_map.user_id ELSE NULL END;')
    for row in data['sessions']:
        old_id=next(item['old_user_id'] for item in data['mappings'] if item['user_id']==row['user_id'])
        old,new,token=quote(old_id),quote(row['user_id']),quote(row['token_hash'])
        expiry=str(row['expires_at'])
        statements.append('INSERT INTO legacy_sessions(token_hash,user_id,expires_at) VALUES('+token+', (SELECT m.user_id FROM legacy_user_map m JOIN users u ON u.id=m.user_id JOIN legacy_accounts a ON a.user_id=m.user_id WHERE m.old_user_id='+old+' AND m.user_id='+new+'), '+expiry+') ON CONFLICT(token_hash) DO UPDATE SET user_id=CASE WHEN legacy_sessions.user_id=excluded.user_id AND legacy_sessions.expires_at=excluded.expires_at THEN legacy_sessions.user_id ELSE NULL END;')
    return '\n'.join(statements)+'\n'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auth-db',required=True)
    parser.add_argument('--identity-map',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--format',choices=('json','sql'),default='json')
    args=parser.parse_args()
    mapping=json.loads(Path(args.identity_map).read_text())
    content=json.dumps(auth_manifest(args.auth_db,mapping),ensure_ascii=False,indent=2)+'\n' if args.format=='json' else auth_sql(args.auth_db,mapping)
    descriptor=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as output:
        output.write(content)
    print('Protected auth import written. No raw session or pepper exported.')

if __name__=='__main__':
    main()
