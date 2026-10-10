"""Create an account-scoped migration file, without modifying the old database.

Never upload the output to GitHub: it may contain private impressions.
The original database remains the authoritative complete backup.
"""
import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path


def convert(rows):
    records = []
    for row in rows:
        date = row.get('date') or row.get('first_date') or ''
        title = row.get('title') or ''
        if not title or not date:
            raise ValueError('作品名・日付がない記録があります。原本を確認してください。')
        identity = row.get('work_key') or json.dumps([title, date, row.get('time', '')], ensure_ascii=False)
        records.append({
            'id': 'legacy-' + hashlib.sha256(identity.encode()).hexdigest()[:32],
            'title': title, 'date': date, 'time': row.get('time') or '',
            'venue': row.get('venue') or '', 'rating': row.get('verdict') or '',
            'note': row.get('note_impression') or '',
        })
    return {'version': 2, 'records': records, 'favourites': [], 'reactions': []}


def account_preferences(con, user_id):
    """Select only this account. Legacy files must be explicitly supplied."""
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    favourites = []
    if 'app_setting' in tables:
        row = con.execute('SELECT value FROM app_setting WHERE user_id=? AND key=?', (user_id, 'declared')).fetchone()
        if row:
            declared = json.loads(row[0])
            favourites = [{'kind':kind,'name':name} for kind, names in declared.items()
                          if kind in ('人','団体','主催','作品','題材','原作者') for name in names if isinstance(name,str) and name.strip()]
    signals = {}
    if 'reaction' in tables:
        for row in con.execute('SELECT * FROM reaction WHERE user_id=? ORDER BY updated_at', (user_id,)):
            value = dict(row)
            signal = 'owned' if value.get('owned') else 'interest' if value.get('interest') == 1 else 'no' if value.get('interest') == 0 else None
            if signal:
                signals[str(value['stage_id'])] = {'stage_id':str(value['stage_id']),'status':signal}
    return favourites, list(signals.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--database', type=Path)
    source.add_argument('--purchases', type=Path, help='selected title/date/time/venue JSON list, not email bodies')
    parser.add_argument('--user-id', help='required for database input; never export all users')
    parser.add_argument('--declared', type=Path, help='optional account-specific favourites JSON; only supply the file belonging to this account')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    favourites, reactions = [], []
    if args.database:
        if not args.user_id:
            parser.error('--database requires --user-id')
        with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as con:
            con.row_factory = sqlite3.Row
            rows = [dict(row) for row in con.execute('SELECT * FROM works WHERE user_id=? ORDER BY first_date,work_key', (args.user_id,))]
            favourites, reactions = account_preferences(con, args.user_id)
    else:
        rows = json.loads(args.purchases.read_text(encoding='utf8'))
        if not isinstance(rows, list):
            parser.error('purchase input must be a JSON list')
    payload = convert(rows)
    if args.declared:
        declared = json.loads(args.declared.read_text())
        favourites = [{'kind':kind,'name':name} for kind,names in declared.items()
                      if kind in ('人','団体','主催','作品','題材','原作者') for name in names if isinstance(name,str) and name.strip()]
    payload['favourites'] = list({(f['kind'],f['name']):f for f in favourites}.values())
    payload['reactions'] = reactions
    if len(payload['records']) > 500 or len(payload['favourites']) > 200 or len(reactions) > 500:
        parser.error('preview supports 500 records, 200 favourites and 500 reactions per account')
    # Exclusive creation prevents accidentally overwriting a backup.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf8') as out:
        json.dump(payload, out, ensure_ascii=False, indent=2)
    print(f"{len(payload['records'])} records written. Keep the original database/archive.")


if __name__ == '__main__':
    main()
