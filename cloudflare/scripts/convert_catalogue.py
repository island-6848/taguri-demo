"""Build D1 SQL from public candidate JSONL; omit owner rankings and notes."""
import argparse
import datetime
import json
import os
import re
from pathlib import Path


def public_candidate(value):
    sid = str(value.get('stage_id') or value.get('id') or '')
    title = str(value.get('title') or '')
    date = str(value.get('date') or '')
    if not date:
        match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', str(value.get('period') or ''))
        if match:
            date = datetime.date(*map(int, match.groups())).isoformat()
    if not sid or not title or not date:
        raise ValueError('stage_id/title/date or period required; no invented dates')
    datetime.date.fromisoformat(date)
    url = str(value.get('url') or '')
    if url and not url.startswith('https://'):
        url = ''
    # Only public source material. Do not copy a/why_b/why_c or private notes.
    metadata = {k: value.get(k) for k in ('group', 'fields', 'synopsis', 'words') if value.get(k)}
    dates = re.findall(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', str(value.get('period') or ''))
    metadata['end_date'] = str(value.get('end_date') or (datetime.date(*map(int, dates[-1])).isoformat() if dates else date))
    datetime.date.fromisoformat(metadata['end_date'])
    if not isinstance(metadata.get('fields', {}), dict) or not isinstance(metadata.get('words', []), list):
        raise ValueError('fields must be an object and words a list')
    return [sid, title, date, str(value.get('venue') or ''), url, json.dumps(metadata, ensure_ascii=False)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    rows = [public_candidate(json.loads(line)) for line in a.input.read_text().splitlines() if line.strip()]
    if len(rows) > 1000:
        p.error('preview catalogue supports 1000 candidates; select the current public candidates first')
    quote = lambda v: "'" + v.replace("'", "''") + "'"
    # Upsert only; never destroy the existing catalogue as a side effect of a partial input.
    statements = ['INSERT INTO catalogue(id,title,date,venue,url,metadata) VALUES(' + ','.join(map(quote,row)) + ') ON CONFLICT(id) DO UPDATE SET title=excluded.title,date=excluded.date,venue=excluded.venue,url=excluded.url,metadata=excluded.metadata;' for row in rows]
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
        out.write('\n'.join(statements)+'\n')
    print(f'{len(rows)} public candidates converted; verify rights and contents before upload.')


if __name__ == '__main__':
    main()
