#!/usr/bin/env python3
"""Dependency sync -> approved source/public build -> direct Wrangler, in order.

Do not replace the final Wrangler invocation with pywrangler dev/deploy: those
commands may sync again and remove the source modules we just explicitly built.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'cloudflare' / 'python'


def run(arguments, cwd=PROJECT):
    subprocess.run(arguments, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('build','dev','deploy'), default='build')
    parser.add_argument('--catalogue', required=True, type=Path)
    parser.add_argument('--approved-base-recommendation', required=True, type=Path)
    parser.add_argument('--poster-dir', type=Path)
    parser.add_argument('--assets-dir', type=Path, default=ROOT/'cloudflare'/'public')
    args = parser.parse_args()
    # Resolve source paths before changing working directories. Fail before any
    # dependency/network operation if approved inputs are unavailable.
    catalogue = args.catalogue.resolve(strict=True)
    base = args.approved_base_recommendation.resolve(strict=True)
    posters = args.poster_dir.resolve(strict=True) if args.poster_dir else None
    if args.mode == 'deploy' and 'REPLACE_WITH_' in (PROJECT/'wrangler.jsonc').read_text():
        parser.error('Set a separate preview database ID before deployment.')
    run(['uv','sync','--locked'])
    # uv.lock pins workers-py 1.17.7; refuse silently changed tooling semantics.
    run(['uv','run','--no-sync','python','-c',"import importlib.metadata; assert importlib.metadata.version('workers-py') == '1.17.7', 'Review dependency sync behavior before upgrading workers-py'"])
    run(['uv','run','--no-sync','pywrangler','sync','--force'])
    run([sys.executable,str(ROOT/'cloudflare/scripts/build_python_bundle.py')])
    public = [sys.executable,str(ROOT/'cloudflare/scripts/build_public_snapshot.py'),
              '--catalogue',str(catalogue),'--approved-base-recommendation',str(base),
              '--output',str(PROJECT/'python_modules/public_snapshot.py')]
    if posters:
        public += ['--poster-dir',str(posters),'--assets-dir',str(args.assets_dir.resolve())]
    run(public)
    for path in ('snapshot_store.py','cloud_auth.py','legacy_runtime.py','native_provision.py','public_snapshot.py','taguri_project/__init__.py'):
        if not (PROJECT/'python_modules'/path).is_file():
            raise RuntimeError('Build did not produce the required preview modules')
    if args.mode != 'build':
        # Direct Wrangler does not execute pywrangler's deleting dependency sync.
        run(['npx','--no-install','wrangler',args.mode,'--config','wrangler.jsonc'])
    else:
        print('Dependencies and approved modules built. Use direct Wrangler without another pywrangler sync.')


if __name__ == '__main__':
    try:
        main()
    except (OSError,subprocess.CalledProcessError,RuntimeError):
        raise SystemExit('Python preview preparation failed; no automatic production switch was performed.') from None
