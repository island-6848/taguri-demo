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
    return {'version': 1, 'records': records, 'favourites': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--database', type=Path)
    source.add_argument('--purchases', type=Path, help='selected title/date/time/venue JSON list, not email bodies')
    parser.add_argument('--user-id', help='required for database input; never export all users')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.database:
        if not args.user_id:
            parser.error('--database requires --user-id')
        with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as con:
            con.row_factory = sqlite3.Row
            rows = [dict(row) for row in con.execute('SELECT * FROM works WHERE user_id=? ORDER BY first_date,work_key', (args.user_id,))]
    else:
        rows = json.loads(args.purchases.read_text(encoding='utf8'))
        if not isinstance(rows, list):
            parser.error('purchase input must be a JSON list')
    payload = convert(rows)
    if len(payload['records']) > 500:
        parser.error('migration preview supports at most 500 records per account')
    # Exclusive creation prevents accidentally overwriting a backup.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf8') as out:
        json.dump(payload, out, ensure_ascii=False, indent=2)
    print(f"{len(payload['records'])} records written. Keep the original database/archive.")


if __name__ == '__main__':
    main()
