"""Build the D1 stage_label table (migration 0011) from the public catalogue.

    python3 cloudflare/scripts/build_stage_labels.py --output /tmp/labels.sql

`app.stage_label(user_id, stage_id)` names a linked stage "題名／劇場／日付",
built from the stage rows of `app._suggest_pool` (candidates.jsonl and
picked.jsonl, merged per stage by `app._merge_by_stage`). The Worker reads the
precomputed label instead of the catalogue files.

data/credits/{credits,linked}.jsonl are also read by the Python function, but
they are the owner's mail-derived batch output and are not part of the public
catalogue, so they are not uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "review"))
sys.path.insert(0, str(ROOT / "tools" / "taguri"))

_spec = importlib.util.spec_from_file_location("build_recommend_index", HERE / "build_recommend_index.py")
BI = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(BI)

import rate_performances as R                                       # noqa: E402
import render_recommend as RR                                       # noqa: E402


def stage_rows(candidates: list[dict], picked: list[dict]) -> list[dict]:
    """The "stage" rows of app._suggest_pool for these catalogue entries."""
    rows = []
    for c in candidates:
        one = RR.short_period(c.get("period") or "")
        rows.append({"kind": "stage", "src": 0, "key": str(c.get("stage_id") or ""),
                     "title": c.get("title") or "",
                     "date": RR._start(c.get("period") or "") if "〜" not in one else "",
                     "venue": c.get("theater") or "", "group": c.get("group") or "", "note": "",
                     "stage_id": str(c.get("stage_id") or "")})
    for c in picked:
        one = RR.short_period(c.get("period") or "")
        rows.append({"kind": "stage", "src": 0, "key": str(c.get("stage_id") or ""),
                     "title": c.get("title") or "",
                     "date": RR._start(c.get("period") or "") if "〜" not in one else "",
                     "venue": c.get("theater") or c.get("venue") or "", "group": c.get("group") or "", "note": "",
                     "stage_id": str(c.get("stage_id") or "")})
    for r in rows:
        r["k"] = R.title_key(r["title"])
    return [r for r in rows if r["k"]]


def build(candidates: list[dict], picked: list[dict]) -> dict[str, tuple[str, str]]:
    """stage_id -> (label as app.stage_label returns it, title as app.link_stage returns it)."""
    import app as APP
    ix: dict[str, tuple[str, str]] = {}
    for r in APP._merge_by_stage(stage_rows(candidates, picked)):
        if r["kind"] == "stage" and r["key"] and r["key"] not in ix:
            ix[r["key"]] = ("／".join(x for x in (r["title"], r.get("venue") or "", r.get("date") or "") if x),
                            r["title"])
    return ix


def to_sql(labels: dict[str, tuple[str, str]]) -> list[str]:
    """Insert a version, switch rec_meta 'stage_label' to it, drop the others."""
    ver = hashlib.sha256(json.dumps(labels, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    stmts = [f"DELETE FROM stage_label WHERE ver={BI._q(ver)};"]
    stmts += BI._inserts("stage_label", "ver,stage_id,label,title",
                         [(ver, sid, lab, title) for sid, (lab, title) in sorted(labels.items())])
    stmts.append(f"INSERT INTO rec_meta(k,v) VALUES('stage_label',{BI._q(ver)}) "
                 "ON CONFLICT(k) DO UPDATE SET v=excluded.v;")
    stmts.append(f"DELETE FROM stage_label WHERE ver<>{BI._q(ver)};")
    return stmts


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--output", required=True, type=Path, help="SQL for wrangler d1 execute --file")
    a = p.parse_args()
    base = ROOT / "data" / "review"
    labels = build(_jsonl(base / "candidates.jsonl"), _jsonl(base / "picked.jsonl"))
    if not labels:
        p.error("no candidates under data/review; fetch the catalogue first")
    body = "\n".join(to_sql(labels)) + "\n"
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(body)
    print(json.dumps({"stages": len(labels), "sql_bytes": len(body.encode())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
