"""app.weight_form on given steps and counts: the reference for src/screens/weights.js.

    python3 test/screens/weights_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CASES = [({}, {}, 0),
         ({"cast": "max", "theme": "off", "craft": "weak"}, {"cast": 12, "author": 3, "theme": 7}, 0),
         ({"author": "strong", "produce": "off", "other": "max", "stage": "weak"}, {"produce": 1}, 4)]


def main():
    sys.path[:0] = [str(REPO / "tools" / "taguri"), str(REPO / "tools" / "review")]
    import app as APP
    out = []
    for w, cnt, drop in CASES:
        full = {k: w.get(k, "mid") for k, _l, _r in APP.ROLE_GROUPS}
        out.append({"w": full, "cnt": cnt, "drop": drop,
                    "html": APP.weight_form("nobody", {"weights": full, "w_counts": cnt, "w_dropped": drop})})
    print(json.dumps({"cases": out, "steps": [[k, l, m] for k, l, m in APP.WEIGHT_STEPS],
                      "groups": [[k, l] for k, l, _r in APP.ROLE_GROUPS]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
