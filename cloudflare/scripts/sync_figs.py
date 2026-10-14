"""Copy the figures that run in the browser (src/screens/figs.js and what it imports)
to public/figs/, so the static assets serve them (no Worker request, no Worker CPU).

    python3 cloudflare/scripts/sync_figs.py           # rewrite the copies
    python3 cloudflare/scripts/sync_figs.py --check   # exit 1 if out of date

Only modules reached from figs.js are copied. A module that reads D1 or the Worker's
environment must never be among them: the check fails if one is.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SRC, OUT = HERE / "src" / "screens", HERE / "public" / "figs"
ENTRY = "figs.js"
# Modules that touch D1, the request or the Worker: they cannot run in the browser.
SERVER_ONLY = {"autolink.js", "credits.js", "row.js", "works.js", "diary.js", "records.js", "index.js",
               "lists.js", "recommend.js", "compare.js"}
IMPORT = re.compile(r"""^\s*(?:import|export)\s[^'"]*?from\s+['"]\./([A-Za-z0-9_]+\.js)['"]""", re.M)


def closure() -> list[str]:
    seen, todo = [], [ENTRY]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.append(name)
        todo += IMPORT.findall((SRC / name).read_text(encoding="utf-8"))
    return sorted(seen)


def main() -> int:
    check = "--check" in sys.argv[1:]
    names = closure()
    bad = [n for n in names if n in SERVER_ONLY]
    if bad:
        print(f"figs.js reaches server-only modules: {', '.join(bad)}")
        return 1
    want = {n: (SRC / n).read_text(encoding="utf-8") for n in names}
    have = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("*.js")} if OUT.exists() else {}
    stale = sorted(n for n in set(want) | set(have) if want.get(n) != have.get(n))
    if check:
        if stale:
            print("public/figs/ is out of date: " + ", ".join(stale) + " (run python3 cloudflare/scripts/sync_figs.py)")
            return 1
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for n in stale:
        if n in want:
            (OUT / n).write_text(want[n], encoding="utf-8")
        else:
            (OUT / n).unlink()
    print(f"public/figs/: {len(names)} modules" + (f", rewrote {', '.join(stale)}" if stale else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
