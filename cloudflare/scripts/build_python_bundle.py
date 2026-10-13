#!/usr/bin/env python3
"""Vendor source only. Never recursively copy data, credentials or databases."""
import argparse
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def build(output):
    output = Path(output)
    project = output / 'taguri_project'
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)
    (project / '__init__.py').write_text('from pathlib import Path\nPROJECT_ROOT = Path(__file__).resolve().parent\n',encoding='utf-8')
    count = 0
    for section in ('taguri','review','tickets','credits','mail','lib','corich','stages'):
        source = ROOT / 'tools' / section
        for file in sorted(source.glob('*.py')):
            if file.name.startswith('test_'):
                continue
            destination = project / 'tools' / section / file.name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(file.read_bytes())
            count += 1
    for file in sorted((ROOT / 'tools').glob('*.py')):
        if file.name.startswith('test_'):
            continue
        destination = project / 'tools' / file.name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(file.read_bytes())
        count += 1
    # This selected purchase fixture is already tracked and publicly approved.
    # Its .json source cannot be bundled as Python module data automatically.
    # Encode only this exact file into a module, then install at startup.
    fixture = ROOT / 'tools' / 'taguri' / 'demo_purchase_works.json'
    data = json.loads(fixture.read_text(encoding='utf-8'))
    (project / 'approved_fixture.py').write_text('FIXTURE = ' + repr(data) + '\n',encoding='utf-8')
    for source in (ROOT / 'cloudflare' / 'python').glob('*.py'):
        if source.name in {'entry.py','public_snapshot.py'}:
            continue
        (output / source.name).write_bytes(source.read_bytes())
    print(f'Vendored {count} Python source modules. No source data directory was copied.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT / 'cloudflare' / 'python' / 'python_modules')
    args = parser.parse_args()
    build(args.output)
