#!/usr/bin/env python3
"""Build an atomic D1 batch manifest from a protected, read-only account DB.

No HTTP access, no source mutation, no existing account merge/overwrite. Target
identity equals the explicit old non-owner identity. Owner local transfer needs
explicit operator opt-in and a fresh non-owner target, never account merging.
"""
import argparse
import hashlib
import re
import json
import os
from pathlib import Path
import secrets
import sys
import time
from export_legacy_account import snapshot

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'cloudflare'/'python'))
from snapshot_store import chunks,keyed_rows

INSERT_ACCOUNT='INSERT INTO users(id,recovery_hash,created_at) VALUES(?,?,?)'
INSERT_SNAPSHOT="INSERT INTO legacy_accounts(user_id,revision,write_token) VALUES(?,0,'')"
INSERT_SCHEMAS="INSERT INTO legacy_schemas(user_id,table_name,schema_sql,columns_json,primary_key_json) SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.schema'),json_extract(value,'$.columns'),json_extract(value,'$.pk') FROM json_each(?)"
INSERT_ROWS="INSERT INTO legacy_rows(user_id,table_name,row_key,row_json) SELECT ?,json_extract(value,'$.table'),json_extract(value,'$.key'),json_extract(value,'$.row') FROM json_each(?)"


def prepare(database,user_id,target_user_id,owner_transfer=False,recovery_code=None):
    if not isinstance(user_id,str) or not user_id or len(user_id)>200:
        raise ValueError('Explicit source identity is required')
    if owner_transfer:
        if user_id!='local' or not isinstance(target_user_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',target_user_id) or target_user_id=='local':
            raise ValueError('Owner transfer requires local source and explicit fresh non-owner target')
        if not isinstance(recovery_code,str) or not re.fullmatch('[a-f0-9]{64}',recovery_code):
            raise ValueError('Owner transfer requires a protected new recovery credential')
    elif user_id=='local' or target_user_id!=user_id or recovery_code is not None:
        raise ValueError('Ordinary migration must preserve the non-owner identity; merges are not supported')
    data=snapshot(database,user_id)
    source_sha256={name:table['sha256'] for name,table in data['tables'].items()}
    if owner_transfer:
        for table in data['tables'].values():
            for row in table['rows']:
                if row.get('user_id')!='local':
                    raise ValueError('Source owner snapshot includes another identity')
                row['user_id']=target_user_id
            table['rows'].sort(key=lambda row:json.dumps(row,sort_keys=True,ensure_ascii=False))
            encoded=json.dumps(table['rows'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            table['sha256']=hashlib.sha256(encoded).hexdigest()
        # Schemas/PK columns stay exactly original; keyed_rows below recomputes
        # composite primary-key identities from rewritten ownership values.
    uid=target_user_id
    schemas,rows=[],[]
    for name,table in data['tables'].items():
        schemas.append({'table':name,'schema':table['schema'],'columns':json.dumps(table['columns']),'pk':json.dumps(table['primary_key'])})
        rows.extend({'table':name,'key':key,'row':value} for key,value in keyed_rows(table).items())
    # A random unknown hash does not issue a public recovery credential. Original
    # protected auth migration subsequently enables recovery/old-cookie access.
    recovery_hash=hashlib.sha256(recovery_code.encode()).hexdigest() if owner_transfer else secrets.token_hex(32)
    commands=[{'sql':INSERT_ACCOUNT,'params':[uid,recovery_hash,int(time.time())]}, {'sql':INSERT_SNAPSHOT,'params':[uid]}]
    commands += [{'sql':INSERT_SCHEMAS,'params':[uid,block]} for block in chunks(schemas)]
    commands += [{'sql':INSERT_ROWS,'params':[uid,block]} for block in chunks(rows)]
    if len(commands)>40:
        raise ValueError('Account exceeds atomic free-tier query budget')
    return {'format':'taguri-protected-d1-batch','version':1,'user_id':uid,'source_user_id':user_id,'owner_identity_transfer':owner_transfer,'owner_recovery_issued':owner_transfer,'source_sha256':source_sha256,'commands':commands,'counts':{name:table['count'] for name,table in data['tables'].items()},'sha256':{name:table['sha256'] for name,table in data['tables'].items()},'shared_tables_not_imported':data['shared_tables_not_exported'],'authentication_not_imported':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--user-id',required=True)
    parser.add_argument('--target-user-id',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--owner-transfer',action='store_true',help='Operator-only local to fresh non-owner target transfer; no shared tables copied')
    parser.add_argument('--owner-recovery-output',help='Required with owner-transfer: protected new credential file, never stdout/manifest')
    args=parser.parse_args()
    try:
        if bool(args.owner_recovery_output)!=args.owner_transfer:
            raise ValueError('Owner transfer requires a separate protected recovery output')
        code=secrets.token_hex(32) if args.owner_transfer else None
        result=prepare(args.db,args.user_id,args.target_user_id,args.owner_transfer,code)
        if args.owner_recovery_output and Path(args.owner_recovery_output).resolve()==Path(args.output).resolve():
            raise ValueError('Credential and manifest paths must differ')
        descriptor=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        credential=None
        try:
            if args.owner_transfer:
                credential=os.open(args.owner_recovery_output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except OSError:
            os.close(descriptor)
            Path(args.output).unlink()  # Only the newly-created, still-empty file.
            raise
        with os.fdopen(descriptor,'w',encoding='utf-8') as output:
            json.dump(result,output,ensure_ascii=False,indent=2)
            output.write('\n')
        if credential is not None:
            with os.fdopen(credential,'w',encoding='utf-8') as output:
                json.dump({'format':'taguri-owner-recovery','version':1,'user_id':args.target_user_id,'recovery_code':code},output,ensure_ascii=False)
                output.write('\n')
    except (ValueError,OSError):
        parser.exit(1,'Account migration could not be prepared. Source data was not modified.\n')
    print('Protected atomic-batch manifest written. Shared data still requires separate inventory and reconciliation.')


if __name__=='__main__':
    main()
